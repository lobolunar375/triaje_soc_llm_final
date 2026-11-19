"""Paso 01. Exploración del dataset GUIDE (archivo de entrenamiento).

Qué mide y por qué:
  * Filas, columnas y tipos: confirman el esquema publicado (45 columnas) antes de limpiar.
  * Porcentaje de nulos, cardinalidad y si los valores son texto o códigos numéricos: GUIDE seudonimiza
    los identificadores (los reemplaza por números aleatorios), y un modelo de lenguaje solo puede
    interpretar las columnas que conservan texto con significado. Esta medición sustenta la elección de
    características del paso 02.
  * Distribución de IncidentGrade por evidencia, alerta e incidente: la unidad de análisis es el
    incidente, y el desbalance de clases justifica el F1 macro.
  * Consistencia de la etiqueta dentro de cada incidente: un incidente debe tener una sola calificación.
  * Asociación de cada columna con la etiqueta (V de Cramér) y su cobertura por clase: detecta columnas
    que filtran la etiqueta (por ejemplo, acciones de remediación registradas después del triaje).
  * Alertas por incidente e incidentes por organización: definen el criterio de exclusión por tamaño
    y la partición por organización.

Salidas: results/exploracion/perfil_columnas.csv, resumen_exploracion.json y resumen_exploracion.md.
"""
import duckdb
import numpy as np
import pandas as pd

from comunes import Bitacora, cargar_config, guardar_json, pct, ruta


def cramer_v(tabla: pd.DataFrame) -> float:
    from scipy.stats import chi2_contingency
    t = tabla.values
    if t.shape[0] < 2 or t.shape[1] < 2:
        return 0.0
    chi2 = chi2_contingency(t, correction=False)[0]
    n = t.sum()
    r, k = t.shape
    return float(np.sqrt(chi2 / (n * (min(r, k) - 1))))


def main():
    cfg = cargar_config()
    b = Bitacora('01_explorar_dataset')
    csv = ruta(cfg['datos']['dir_raw'], cfg['datos']['archivo_train'])
    con = duckdb.connect()
    con.execute('PRAGMA threads=4')

    b.paso('Registrar el CSV como vista de DuckDB con todas las columnas como texto',
           'Leer todo como texto evita que DuckDB convierta en número códigos que son identificadores y '
           'permite contar nulos y valores tal como vienen en el archivo.')
    pq = ruta('data', 'interim', 'guide_train_texto.parquet')
    if not pq.exists():
        b.info('Convirtiendo el CSV a Parquet (una sola lectura del CSV; las consultas siguientes son columnares).')
        con.execute(f"""COPY (SELECT * FROM read_csv('{csv.as_posix()}', header=true, all_varchar=true))
                       TO '{pq.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    con.execute(f"CREATE VIEW g AS SELECT * FROM read_parquet('{pq.as_posix()}')")
    cols = [r[0] for r in con.execute('DESCRIBE g').fetchall()]
    n = con.execute('SELECT COUNT(*) FROM g').fetchone()[0]
    b.info(f'Filas (evidencias): {n:,}   Columnas: {len(cols)}')
    b.info('Columnas: ' + ', '.join(cols))

    b.paso('Perfil de cada columna: nulos, cardinalidad, tipo de valor y ejemplos',
           'Distingue columnas interpretables por un LLM (texto con significado) de códigos seudonimizados.')
    filas = []
    for c in cols:
        q = f'''SELECT COUNT(*) FILTER (WHERE "{c}" IS NULL OR "{c}"='') AS nulos,
                       approx_count_distinct("{c}") AS distintos,
                       COUNT(*) FILTER (WHERE regexp_full_match("{c}", '-?[0-9]+(\\.[0-9]+)?')) AS numericos
                FROM g'''
        nulos, dist, num = con.execute(q).fetchone()
        top = con.execute(f'SELECT "{c}" v, COUNT(*) k FROM g WHERE "{c}" IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 3').fetchall()
        no_nulos = n - nulos
        tipo = 'código numérico' if no_nulos and num / no_nulos > 0.99 else 'texto'
        moda_pct = pct(top[0][1], n) if top else 0
        filas.append({'columna': c, 'pct_nulos': pct(nulos, n), 'distintos_aprox': dist, 'tipo_valor': tipo,
                      'pct_valor_mas_frecuente': moda_pct,
                      'ejemplos': ' | '.join(f'{str(v)[:40]} ({k:,})' for v, k in top)})
    perfil = pd.DataFrame(filas)
    b.tabla(perfil[['columna', 'pct_nulos', 'distintos_aprox', 'tipo_valor', 'pct_valor_mas_frecuente']], 60)

    b.paso('Distribución de IncidentGrade por evidencia, por alerta y por incidente',
           'La etiqueta se asigna al incidente; contar por evidencia sobrerrepresenta los incidentes grandes.')
    dist_ev = dict(con.execute('SELECT COALESCE(IncidentGrade,\'(nulo)\'), COUNT(*) FROM g GROUP BY 1').fetchall())
    con.execute('''CREATE TABLE inc AS SELECT OrgId, IncidentId, COUNT(*) n_evid, COUNT(DISTINCT AlertId) n_alert,
                   COUNT(DISTINCT IncidentGrade) n_grados, MIN(IncidentGrade) grado,
                   COUNT(*) FILTER (WHERE IncidentGrade IS NULL) n_grado_nulo
                   FROM g GROUP BY 1, 2''')
    n_inc = con.execute('SELECT COUNT(*) FROM inc').fetchone()[0]
    dist_inc = dict(con.execute("SELECT COALESCE(grado,'(nulo)'), COUNT(*) FROM inc WHERE n_grados<=1 GROUP BY 1").fetchall())
    inconsist = con.execute('SELECT COUNT(*) FROM inc WHERE n_grados>1').fetchone()[0]
    n_alert = con.execute('SELECT COUNT(DISTINCT AlertId) FROM g').fetchone()[0]
    n_org = con.execute('SELECT COUNT(DISTINCT OrgId) FROM g').fetchone()[0]
    b.info(f'Alertas distintas: {n_alert:,}   Incidentes (OrgId, IncidentId): {n_inc:,}   Organizaciones: {n_org:,}')
    b.info(f'Por evidencia: {dist_ev}')
    b.info(f'Por incidente (con una sola etiqueta): {dist_inc}')
    b.info(f'Incidentes con más de una etiqueta distinta: {inconsist:,}')

    b.paso('Tamaño de los incidentes y de las organizaciones',
           'Sustenta el umbral de exclusión por tamaño y muestra la concentración de incidentes por organización.')
    q = lambda col, tab: con.execute(f'''SELECT quantile_cont({col}, [0.5, 0.75, 0.9, 0.95, 0.99]), MAX({col}), AVG({col}) FROM {tab}''').fetchone()
    al = q('n_alert', 'inc')
    ev = q('n_evid', 'inc')
    con.execute('CREATE TABLE org AS SELECT OrgId, COUNT(*) n_inc FROM inc GROUP BY 1')
    og = q('n_inc', 'org')
    pct_le = {k: pct(con.execute(f'SELECT COUNT(*) FROM inc WHERE n_alert<={k}').fetchone()[0], n_inc) for k in (1, 5, 10, 25, 50, 100)}
    b.info(f'Alertas por incidente: p50/p75/p90/p95/p99 = {al[0]}, máx = {al[1]}, media = {al[2]:.2f}')
    b.info(f'Evidencias por incidente: p50/p75/p90/p95/p99 = {ev[0]}, máx = {ev[1]}, media = {ev[2]:.2f}')
    b.info(f'Incidentes por organización: p50/p75/p90/p95/p99 = {og[0]}, máx = {og[1]}, media = {og[2]:.2f}')
    b.info(f'% de incidentes con a lo sumo k alertas: {pct_le}')
    top_org = con.execute('SELECT OrgId, n_inc FROM org ORDER BY 2 DESC LIMIT 5').fetchall()
    b.info(f'Cinco organizaciones con más incidentes: {top_org}')

    b.paso('Asociación de cada columna con la etiqueta (V de Cramér, 50 valores más frecuentes + resto)',
           'Una asociación casi perfecta indica fuga de la etiqueta; también orienta qué información es útil.')
    asoc = []
    for c in cols:
        if c in ('IncidentGrade', 'Id'):
            continue
        t = con.execute(f'''WITH top AS (SELECT "{c}" v FROM g WHERE "{c}" IS NOT NULL GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 50)
                SELECT CASE WHEN "{c}" IS NULL THEN '(nulo)' WHEN "{c}" IN (SELECT v FROM top) THEN "{c}" ELSE '(otro)' END v,
                       IncidentGrade, COUNT(*) k FROM g WHERE IncidentGrade IS NOT NULL GROUP BY 1, 2''').df()
        tab = t.pivot_table(index='v', columns='IncidentGrade', values='k', aggfunc='sum', fill_value=0)
        # cobertura: % de evidencias de cada clase con valor no nulo en la columna
        nn = t[t.v != '(nulo)'].groupby('IncidentGrade').k.sum()
        tt = t.groupby('IncidentGrade').k.sum()
        cobertura = {g: pct(nn.get(g, 0), tt.get(g, 0)) for g in tt.index}
        asoc.append({'columna': c, 'v_cramer': round(cramer_v(tab), 3),
                     'cobertura_TP': cobertura.get('TruePositive'), 'cobertura_BP': cobertura.get('BenignPositive'),
                     'cobertura_FP': cobertura.get('FalsePositive')})
    asoc = pd.DataFrame(asoc).sort_values('v_cramer', ascending=False)
    b.tabla(asoc, 60)
    perfil = perfil.merge(asoc, on='columna', how='left')
    perfil.to_csv(ruta('results', 'exploracion', 'perfil_columnas.csv'), index=False, encoding='utf-8')

    resumen = {
        'archivo': csv.name, 'filas_evidencias': n, 'columnas': len(cols), 'alertas': n_alert, 'incidentes': n_inc,
        'organizaciones': n_org, 'distribucion_evidencias': dist_ev, 'distribucion_incidentes': dist_inc,
        'incidentes_etiqueta_inconsistente': inconsist,
        'alertas_por_incidente': {'p50_p75_p90_p95_p99': al[0], 'max': al[1], 'media': round(al[2], 3)},
        'evidencias_por_incidente': {'p50_p75_p90_p95_p99': ev[0], 'max': ev[1], 'media': round(ev[2], 3)},
        'incidentes_por_org': {'p50_p75_p90_p95_p99': og[0], 'max': og[1], 'media': round(og[2], 3)},
        'pct_incidentes_hasta_k_alertas': pct_le, 'top5_org': top_org,
    }
    guardar_json(resumen, ruta('results', 'exploracion', 'resumen_exploracion.json'))
    with open(ruta('results', 'exploracion', 'resumen_exploracion.md'), 'w', encoding='utf-8') as f:
        f.write('# Exploración de GUIDE_Train.csv\n\n')
        for k, v in resumen.items():
            f.write(f'- **{k}**: {v}\n')
        f.write('\n## Perfil de columnas\n\n')
        f.write(perfil.to_markdown(index=False))
    b.fin()


if __name__ == '__main__':
    main()
