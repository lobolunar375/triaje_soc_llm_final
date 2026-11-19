"""Paso 02. Limpieza de GUIDE_Train y selección de características.

Cada paso imprime qué hace, por qué y cuántas filas o incidentes afecta. El resultado es:
  data/interim/evidencias_limpias.parquet   evidencias de los incidentes elegibles, solo columnas conservadas
  data/interim/incidentes.parquet           una fila por incidente elegible (unidad de análisis)
  results/limpieza/decisiones_columnas.csv  decisión, motivo y evidencia empírica de cada columna
  results/limpieza/embudo_limpieza.csv      filas e incidentes que quedan después de cada paso
  results/limpieza/reporte_limpieza.{json,md}

Pasos:
  1. Verificar el esquema publicado (45 columnas con los nombres esperados).
  2. Eliminar filas duplicadas exactas: una evidencia repetida no aporta información y sesga los conteos.
  3. Normalizar valores vacíos y valores centinela. En las columnas de entidades seudonimizadas, el valor
     más frecuente (presente en más del 50 % de las filas) codifica "sin entidad"; se convierte en nulo para
     no contar como entidad real algo que es ausencia de entidad.
  4. Convertir Timestamp a fecha y hora y descartar marcas inválidas.
  5. Excluir los incidentes sin calificación (IncidentGrade nula) o con más de una calificación: no tienen
     verdad terreno utilizable.
  6. Excluir los incidentes con más alertas que el umbral configurado: el expediente solo muestra 25 alertas
     en detalle, de modo que con más de 50 no representaría fielmente el incidente; se aplica antes del muestreo.
  7. Aplicar la selección de características (config/seleccion_caracteristicas.yaml) y comprobar sus
     supuestos con los datos (porcentaje de nulos, tipo de valor y asociación con la etiqueta).
  8. Construir la tabla de incidentes.
"""
import duckdb
import pandas as pd
import yaml

from comunes import Bitacora, RAIZ, cargar_config, guardar_json, pct, ruta

ESPERADAS = ['Id', 'OrgId', 'IncidentId', 'AlertId', 'Timestamp', 'DetectorId', 'AlertTitle', 'Category',
             'MitreTechniques', 'IncidentGrade', 'ActionGrouped', 'ActionGranular', 'EntityType', 'EvidenceRole',
             'DeviceId', 'Sha256', 'IpAddress', 'Url', 'AccountSid', 'AccountUpn', 'AccountObjectId', 'AccountName',
             'DeviceName', 'NetworkMessageId', 'EmailClusterId', 'RegistryKey', 'RegistryValueName',
             'RegistryValueData', 'ApplicationId', 'ApplicationName', 'OAuthApplicationId', 'ThreatFamily',
             'FileName', 'FolderPath', 'ResourceIdName', 'ResourceType', 'Roles', 'OSFamily', 'OSVersion',
             'AntispamDirection', 'SuspicionLevel', 'LastVerdict', 'CountryCode', 'State', 'City']


def main():
    cfg = cargar_config()
    b = Bitacora('02_limpiar_datos')
    sel = yaml.safe_load(open(RAIZ / 'config' / 'seleccion_caracteristicas.yaml', encoding='utf-8'))
    perfil = pd.read_csv(ruta('results', 'exploracion', 'perfil_columnas.csv'))
    pq = ruta('data', 'interim', 'guide_train_texto.parquet')
    bd = ruta('data', 'interim', 'trabajo_limpieza.duckdb')
    bd.unlink(missing_ok=True)
    con = duckdb.connect(str(bd))  # base en disco: permite procesar 9,5 M de filas con poca RAM
    con.execute("SET memory_limit='4GB'")
    con.execute(f"SET temp_directory='{ruta('data', 'interim', 'tmp', 'x').parent.as_posix()}'")
    con.execute('PRAGMA threads=2')
    con.execute(f"CREATE VIEW g0 AS SELECT * FROM read_parquet('{pq.as_posix()}')")
    embudo = []

    def registrar(etapa, tabla):
        f, i = con.execute(f'SELECT COUNT(*), COUNT(DISTINCT (OrgId, IncidentId)) FROM {tabla}').fetchone()
        embudo.append({'etapa': etapa, 'evidencias': f, 'incidentes': i})
        b.info(f'Quedan {f:,} evidencias y {i:,} incidentes.')

    b.paso('Verificar el esquema', 'El resto del pipeline asume las 45 columnas publicadas por Microsoft.')
    cols = [r[0] for r in con.execute('DESCRIBE g0').fetchall()]
    faltan, sobran = set(ESPERADAS) - set(cols), set(cols) - set(ESPERADAS)
    b.info(f'Columnas: {len(cols)}. Faltan: {sorted(faltan) or "ninguna"}. Sobran: {sorted(sobran) or "ninguna"}.')
    assert not faltan, 'El archivo no tiene el esquema esperado'
    registrar('0. Archivo original', 'g0')

    b.paso('Eliminar filas duplicadas exactas', 'Una evidencia repetida infla los conteos del incidente sin aportar información.')
    con.execute('CREATE TABLE g1 AS SELECT DISTINCT * FROM g0')
    dup = embudo[0]['evidencias'] - con.execute('SELECT COUNT(*) FROM g1').fetchone()[0]
    b.info(f'Duplicados eliminados: {dup:,} ({pct(dup, embudo[0]["evidencias"])} %).')
    registrar('1. Sin duplicados exactos', 'g1')

    b.paso('Normalizar vacíos y valores centinela',
           'En las columnas de entidades seudonimizadas el valor dominante significa "sin entidad"; '
           'contarlo como entidad haría que todos los incidentes parezcan tener el mismo dispositivo o cuenta.')
    centinelas = {}
    for c in cols:
        con.execute(f"""UPDATE g1 SET "{c}" = NULL WHERE trim("{c}") = '' """)
    for c, d in sel.items():
        if c in cols and d['rol'] == 'conteo':
            v, k = con.execute(f'SELECT "{c}", COUNT(*) FROM g1 GROUP BY 1 ORDER BY 2 DESC LIMIT 1').fetchone()
            n = embudo[-1]['evidencias']
            if k / n > 0.5:
                centinelas[c] = {'valor': v, 'pct_filas': pct(k, n)}
                con.execute(f'''UPDATE g1 SET "{c}" = NULL WHERE "{c}" = '{v}' ''')
                b.info(f'{c}: el código {v} aparece en {pct(k, n)} % de las filas; se trata como "sin entidad".')

    b.paso('Convertir Timestamp a fecha y hora', 'Se usa para ordenar las alertas y medir la duración del incidente.')
    con.execute("ALTER TABLE g1 ADD COLUMN ts TIMESTAMP")
    con.execute("UPDATE g1 SET ts = TRY_CAST(replace(replace(Timestamp, 'T', ' '), 'Z', '') AS TIMESTAMP)")
    inval = con.execute('SELECT COUNT(*) FROM g1 WHERE ts IS NULL').fetchone()[0]
    rango = con.execute('SELECT MIN(ts), MAX(ts) FROM g1').fetchone()
    b.info(f'Marcas inválidas: {inval:,}. Rango temporal: {rango[0]} a {rango[1]}.')
    con.execute('DELETE FROM g1 WHERE ts IS NULL')
    registrar('2. Marca de tiempo válida', 'g1')

    b.paso('Excluir incidentes sin calificación o con calificación múltiple',
           'Sin verdad terreno no se puede medir la precisión del triaje.')
    con.execute('''CREATE TABLE inc0 AS SELECT OrgId, IncidentId, COUNT(DISTINCT IncidentGrade) n_grados,
                   COUNT(*) FILTER (WHERE IncidentGrade IS NULL) n_nulos, COUNT(*) n_evid,
                   COUNT(DISTINCT AlertId) n_alertas FROM g1 GROUP BY 1, 2''')
    sin = con.execute('SELECT COUNT(*) FROM inc0 WHERE n_grados = 0').fetchone()[0]
    mult = con.execute('SELECT COUNT(*) FROM inc0 WHERE n_grados > 1').fetchone()[0]
    parc = con.execute('SELECT COUNT(*) FROM inc0 WHERE n_grados = 1 AND n_nulos > 0').fetchone()[0]
    b.info(f'Sin calificación: {sin:,}. Con más de una calificación: {mult:,}. Con calificación y filas nulas: {parc:,}.')
    con.execute('''CREATE TABLE g2 AS SELECT g1.* FROM g1 JOIN inc0 USING (OrgId, IncidentId)
                   WHERE inc0.n_grados = 1''')
    # en incidentes con una sola calificación, las filas nulas heredan la del incidente
    con.execute('''UPDATE g2 SET IncidentGrade = x.gr FROM (SELECT OrgId, IncidentId, MAX(IncidentGrade) gr FROM g2
                   GROUP BY 1, 2) x WHERE g2.OrgId = x.OrgId AND g2.IncidentId = x.IncidentId AND g2.IncidentGrade IS NULL''')
    registrar('3. Con una sola calificación de triaje', 'g2')

    umbral = cfg['limpieza']['max_alertas_incidente']
    b.paso(f'Excluir incidentes con más de {umbral} alertas distintas',
           'En ellos el expediente mostraría en detalle menos de la mitad de las alertas (límite de 25) y no representaría '
           'fielmente el incidente; el criterio se aplica antes del muestreo para que la muestra represente a la población elegible.')
    grandes = con.execute(f'SELECT COUNT(*) FROM inc0 WHERE n_grados = 1 AND n_alertas > {umbral}').fetchone()[0]
    con.execute(f'''CREATE TABLE g3 AS SELECT g2.* FROM g2 JOIN inc0 USING (OrgId, IncidentId)
                    WHERE inc0.n_alertas <= {umbral}''')
    dist_gr = dict(con.execute(f'''SELECT x.gr, COUNT(*) FROM (SELECT OrgId, IncidentId, MAX(IncidentGrade) gr FROM g2 GROUP BY 1, 2) x
                     JOIN inc0 USING (OrgId, IncidentId) WHERE inc0.n_alertas > {umbral} GROUP BY 1''').fetchall())
    b.info(f'Incidentes excluidos por tamaño: {grandes:,}. Clases de los excluidos: {dist_gr}.')
    registrar(f'4. Con a lo sumo {umbral} alertas', 'g3')

    b.paso('Aplicar la selección de características y verificar sus supuestos con los datos',
           'Cada columna tiene un rol (clave, entrada, historial, conteo, etiqueta o eliminada); la tabla final '
           'deja constancia de la evidencia empírica que respalda cada decisión.')
    filas = []
    for c in cols:
        d = sel.get(c, {'rol': 'eliminada', 'motivo': 'No documentada.'})
        p = perfil.set_index('columna').loc[c]
        filas.append({'columna': c, 'rol': d['rol'], 'motivo': d['motivo'], 'pct_nulos': p.pct_nulos,
                      'tipo_valor': p.tipo_valor, 'distintos_aprox': int(p.distintos_aprox),
                      'v_cramer_etiqueta': p.v_cramer if pd.notna(p.v_cramer) else None,
                      'centinela': centinelas.get(c, {}).get('valor'),
                      'pct_centinela': centinelas.get(c, {}).get('pct_filas')})
    dec = pd.DataFrame(filas)
    dec.to_csv(ruta('results', 'limpieza', 'decisiones_columnas.csv'), index=False, encoding='utf-8')
    for rol, grupo in dec.groupby('rol'):
        b.info(f'{rol:>10}: {", ".join(grupo.columna)}')
    avisos = []
    for _, r in dec.iterrows():
        if r.rol == 'entrada' and r.tipo_valor == 'código numérico' and r.columna not in ('Timestamp',):
            avisos.append(f'{r.columna} llega al LLM pero es un código numérico.')
        if r.rol in ('entrada', 'historial') and r.v_cramer_etiqueta and r.v_cramer_etiqueta > 0.9:
            avisos.append(f'{r.columna} tiene V de Cramér {r.v_cramer_etiqueta} con la etiqueta: posible fuga.')
    b.info('Verificación de supuestos: ' + ('; '.join(avisos) if avisos else 'todos se cumplen.'))
    conservar = [c for c in cols if sel.get(c, {}).get('rol') in ('clave', 'entrada', 'historial', 'conteo', 'etiqueta')]
    lista = ', '.join(f'"{c}"' for c in conservar)
    salida_ev = ruta('data', 'interim', 'evidencias_limpias.parquet')
    con.execute(f"COPY (SELECT {lista}, ts FROM g3 ORDER BY OrgId, IncidentId, ts) TO '{salida_ev.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")

    b.paso('Construir la tabla de incidentes', 'El incidente es la unidad de análisis del estudio.')
    conteos = [c for c in conservar if sel[c]['rol'] == 'conteo']
    expr = ', '.join(f'COUNT(DISTINCT "{c}") AS "n_{c}"' for c in conteos)
    con.execute(f'''CREATE TABLE inc AS SELECT OrgId, IncidentId, MAX(IncidentGrade) AS IncidentGrade,
                    COUNT(DISTINCT AlertId) n_alertas, COUNT(*) n_evidencias, COUNT(DISTINCT DetectorId) n_detectores,
                    COUNT(DISTINCT Category) n_categorias, MIN(ts) t_inicio, MAX(ts) t_fin,
                    date_diff('second', MIN(ts), MAX(ts)) / 60.0 AS duracion_min,
                    COUNT(*) FILTER (WHERE MitreTechniques IS NOT NULL) n_con_mitre,
                    COUNT(*) FILTER (WHERE LastVerdict IS NOT NULL) n_con_veredicto, {expr}
                    FROM g3 GROUP BY 1, 2''')
    salida_inc = ruta('data', 'interim', 'incidentes.parquet')
    con.execute(f"COPY (SELECT * FROM inc ORDER BY CAST(OrgId AS BIGINT), CAST(IncidentId AS BIGINT)) TO '{salida_inc.as_posix()}' (FORMAT parquet)")
    dist = con.execute('SELECT IncidentGrade, COUNT(*) FROM inc GROUP BY 1 ORDER BY 2 DESC').fetchall()
    n_inc = sum(k for _, k in dist)
    b.info('Distribución de clases de la población elegible: ' + ', '.join(f'{g} {k:,} ({pct(k, n_inc)} %)' for g, k in dist))
    n_org = con.execute('SELECT COUNT(DISTINCT OrgId) FROM inc').fetchone()[0]
    b.info(f'Organizaciones con al menos un incidente elegible: {n_org:,}.')

    pd.DataFrame(embudo).to_csv(ruta('results', 'limpieza', 'embudo_limpieza.csv'), index=False)
    rep = {'embudo': embudo, 'duplicados': dup, 'centinelas': centinelas, 'timestamps_invalidos': inval,
           'rango_temporal': [str(rango[0]), str(rango[1])], 'incidentes_sin_calificacion': sin,
           'incidentes_calificacion_multiple': mult, 'incidentes_excluidos_tamano': grandes, 'clases_excluidos_tamano': dist_gr, 'umbral_alertas': umbral,
           'poblacion_elegible': {'incidentes': n_inc, 'organizaciones': n_org,
                                  'clases': {g: k for g, k in dist}, 'clases_pct': {g: pct(k, n_inc) for g, k in dist}},
           'columnas_por_rol': {r: list(gr.columna) for r, gr in dec.groupby('rol')}, 'avisos': avisos}
    guardar_json(rep, ruta('results', 'limpieza', 'reporte_limpieza.json'))
    with open(ruta('results', 'limpieza', 'reporte_limpieza.md'), 'w', encoding='utf-8') as f:
        f.write('# Reporte de limpieza de GUIDE_Train\n\n## Embudo\n\n')
        f.write(pd.DataFrame(embudo).to_markdown(index=False))
        f.write('\n\n## Decisiones por columna\n\n')
        f.write(dec.to_markdown(index=False))
        f.write('\n\n## Otros datos\n\n')
        for k in ('duplicados', 'timestamps_invalidos', 'rango_temporal', 'incidentes_sin_calificacion',
                  'incidentes_calificacion_multiple', 'incidentes_excluidos_tamano', 'poblacion_elegible', 'avisos'):
            f.write(f'- **{k}**: {rep[k]}\n')
    con.close()
    bd.unlink(missing_ok=True)
    b.fin()


if __name__ == '__main__':
    main()
