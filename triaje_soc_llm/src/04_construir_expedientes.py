"""Paso 04. Base de conocimiento histórica, traducción de MITRE ATT&CK y expedientes de incidente.

Qué hace y por qué:
  1. Base de conocimiento (herramienta 'historial'): para cada detector, título de alerta y categoría,
     calcula cuántas alertas previas hubo y qué porcentaje terminó en TP, BP o FP. Se calcula SOLO con
     incidentes de las organizaciones de desarrollo y excluyendo los 75 incidentes de la muestra de
     desarrollo, de modo que ninguna estadística contiene información de los incidentes evaluados.
     Es la información que un analista con experiencia usa ("este detector suele dar falsos positivos").
  2. Herramienta 'mitre': traduce cada técnica de ATT&CK a su nombre y táctica con la base oficial de MITRE
     (config/mitre_tecnicas.csv, generada desde mitre/cti enterprise-attack.json).
  3. Expediente: un JSON por incidente con el resumen, las alertas en orden temporal y sus evidencias
     agrupadas por tipo, rol, nivel de sospecha y veredicto. Cada alerta y cada grupo de evidencias tiene
     un identificador citable (A1, A1-E1, ...) que permite verificar después qué evidencias citó cada
     decisión. Es la entrada común de C1 y C2; la etiqueta nunca se incluye.
  4. Referencia estadística: clasifica cada incidente con la clase de mayor porcentaje histórico sumado sobre
     sus detectores (una suma por alerta); si ningún detector tiene historial suficiente, asigna BP, la clase
     mayoritaria. Sirve para controlar la calidad de la base de conocimiento y como
     referencia de lo que se logra sin razonamiento.

Salidas: data/processed/base_conocimiento.parquet, data/processed/expedientes/INC-xxxx.json,
         data/processed/expedientes.jsonl, results/expedientes/*.
"""
import json

import duckdb
import numpy as np
import pandas as pd

from comunes import Bitacora, cargar_config, guardar_json, pct, ruta

CLASES = ['TruePositive', 'BenignPositive', 'FalsePositive']
CORTO = {'TruePositive': 'TP', 'BenignPositive': 'BP', 'FalsePositive': 'FP'}
MIN_SOPORTE = 20  # alertas previas mínimas para informar un porcentaje histórico


def main():
    cfg = cargar_config()
    ce = cfg['expediente']
    b = Bitacora('04_construir_expedientes')
    ev_pq = ruta('data', 'interim', 'evidencias_limpias.parquet')
    mu = pd.read_csv(ruta('data', 'processed', 'muestra.csv'), dtype={'OrgId': str, 'IncidentId': str})
    org_dev = pd.read_csv(ruta('data', 'processed', 'organizaciones_desarrollo.csv'), dtype=str).OrgId
    con = duckdb.connect()
    con.execute(f"CREATE VIEW ev AS SELECT * FROM read_parquet('{ev_pq.as_posix()}')")
    con.register('org_dev', pd.DataFrame({'OrgId': org_dev}))
    con.register('mu', mu[['incidente', 'OrgId', 'IncidentId', 'conjunto']])

    b.paso('Calcular la base de conocimiento con las organizaciones de desarrollo que no aportan incidentes a la muestra',
           'Las estadísticas no deben contener información de las organizaciones evaluadas; además se excluyen las '
           'organizaciones de la muestra de desarrollo, para que los prompts se ajusten en la misma situación que la evaluación '
           '(detectores de organizaciones que la base de conocimiento no ha visto).')
    con.execute('''CREATE TABLE alertas_kb AS SELECT DISTINCT e.OrgId, e.IncidentId, e.AlertId, e.DetectorId, e.AlertTitle,
                   e.Category, e.IncidentGrade FROM ev e JOIN org_dev o USING (OrgId)
                   WHERE NOT EXISTS (SELECT 1 FROM mu WHERE mu.OrgId = e.OrgId AND mu.conjunto = 'desarrollo')''')
    n_kb = con.execute('SELECT COUNT(*), COUNT(DISTINCT (OrgId, IncidentId)) FROM alertas_kb').fetchone()
    b.info(f'Alertas calificadas: {n_kb[0]:,} de {n_kb[1]:,} incidentes de organizaciones de desarrollo (sin las de la muestra).')
    partes = []
    for tipo, col in [('detector', 'DetectorId'), ('titulo', 'AlertTitle'), ('categoria', 'Category')]:
        t = con.execute(f'''SELECT '{tipo}' tipo, {col} codigo, COUNT(*) n,
                    100.0 * COUNT(*) FILTER (WHERE IncidentGrade='TruePositive') / COUNT(*) tp,
                    100.0 * COUNT(*) FILTER (WHERE IncidentGrade='BenignPositive') / COUNT(*) bp,
                    100.0 * COUNT(*) FILTER (WHERE IncidentGrade='FalsePositive') / COUNT(*) fp
                    FROM alertas_kb GROUP BY 2''').df()
        partes.append(t)
        b.info(f'{tipo}: {len(t):,} códigos; con soporte >= {MIN_SOPORTE}: {(t.n >= MIN_SOPORTE).sum():,}.')
    kb = pd.concat(partes)
    kb.to_parquet(ruta('data', 'processed', 'base_conocimiento.parquet'), index=False)
    kbi = {(r.tipo, str(r.codigo)): r for r in kb.itertuples()}

    b.paso('Cargar la tabla de técnicas de MITRE ATT&CK', 'Las técnicas de GUIDE son identificadores (T1078); el nombre y la táctica los hacen interpretables.')
    mitre = pd.read_csv(ruta('config', 'mitre_tecnicas.csv')).set_index('tecnica')
    b.info(f'Técnicas en la tabla: {len(mitre):,}.')

    b.paso('Construir el expediente de cada incidente de la muestra', 'Es la entrada común de las tres condiciones.')
    ev_mu = con.execute('''SELECT mu.incidente, e.* FROM ev e JOIN mu USING (OrgId, IncidentId) ORDER BY mu.incidente, e.ts''').df()
    dir_exp = ruta('data', 'processed', 'expedientes', 'x').parent
    tokens, faltan_mitre, ref = [], set(), []
    with open(ruta('data', 'processed', 'expedientes.jsonl'), 'w', encoding='utf-8') as fj:
        for inc_id, g in ev_mu.groupby('incidente', sort=True):
            t0 = g.ts.min()
            alertas_ord = g.groupby('AlertId', sort=False).ts.min().sort_values().index.tolist()
            detalle = alertas_ord[:ce['max_alertas']]
            alertas, tecnicas_inc, historial = [], set(), {}
            for k, aid in enumerate(detalle, start=1):
                ga = g[g.AlertId == aid]
                fila = ga.iloc[0]
                tecs = sorted({t for v in ga.MitreTechniques.dropna() for t in str(v).split(';') if t})
                tecnicas_inc.update(tecs)
                grupos = (ga.fillna({'SuspicionLevel': '-', 'LastVerdict': '-'})
                          .groupby(['EntityType', 'EvidenceRole', 'SuspicionLevel', 'LastVerdict']).size()
                          .reset_index(name='n').sort_values('n', ascending=False))
                evid = []
                for j, r in enumerate(grupos.head(ce['max_evidencias_por_alerta']).itertuples(), start=1):
                    e = {'id': f'A{k}-E{j}', 'tipo': r.EntityType, 'rol': r.EvidenceRole, 'n': int(r.n)}
                    if r.SuspicionLevel != '-':
                        e['sospecha'] = r.SuspicionLevel
                    if r.LastVerdict != '-':
                        e['veredicto'] = r.LastVerdict
                    evid.append(e)
                alertas.append({'id': f'A{k}', 'minuto': round((ga.ts.min() - t0).total_seconds() / 60, 1),
                                'detector': f'D-{fila.DetectorId}', 'titulo': f'T-{fila.AlertTitle}',
                                'categoria': fila.Category, 'tecnicas': tecs, 'evidencias': evid})
                for tipo, cod, clave in [('detector', fila.DetectorId, f'D-{fila.DetectorId}'),
                                         ('titulo', fila.AlertTitle, f'T-{fila.AlertTitle}'),
                                         ('categoria', fila.Category, f'categoria {fila.Category}')]:
                    r = kbi.get((tipo, str(cod)))
                    historial[clave] = ({'alertas_calificadas': int(r.n), 'TP_%': round(r.tp, 1), 'BP_%': round(r.bp, 1),
                                         'FP_%': round(r.fp, 1)} if r is not None and r.n >= MIN_SOPORTE
                                        else {'alertas_calificadas': int(r.n) if r is not None else 0,
                                              'nota': 'historial insuficiente'})
            ent = {}
            for c, nombre in [('DeviceId', 'dispositivos'), ('IpAddress', 'direcciones_ip'), ('AccountSid', 'cuentas'),
                              ('AccountUpn', 'cuentas_correo'), ('AccountObjectId', 'cuentas_entra_id'),
                              ('AccountName', 'nombres_cuenta'), ('DeviceName', 'nombres_dispositivo'),
                              ('Url', 'urls'), ('Sha256', 'archivos_hash'),
                              ('FileName', 'archivos'), ('NetworkMessageId', 'mensajes_correo'),
                              ('RegistryKey', 'claves_registro'), ('ApplicationId', 'aplicaciones')]:
                v = g[c].nunique()
                if v:
                    ent[nombre] = int(v)
            mit = []
            for t in sorted(tecnicas_inc):
                if t in mitre.index:
                    mit.append({'tecnica': t, 'nombre': mitre.loc[t, 'nombre'], 'tacticas': mitre.loc[t, 'tacticas']})
                else:
                    faltan_mitre.add(t)
                    mit.append({'tecnica': t, 'nombre': 'no encontrada en ATT&CK'})
            exp = {'incidente': inc_id,
                   'resumen': {'alertas': int(g.AlertId.nunique()), 'evidencias': int(len(g)),
                               'duracion_min': round((g.ts.max() - t0).total_seconds() / 60, 1),
                               'detectores_distintos': int(g.DetectorId.nunique()),
                               'categorias': g.drop_duplicates('AlertId').Category.value_counts().to_dict(),
                               'entidades_distintas': ent},
                   'alertas': alertas,
                   'herramientas': {'mitre': mit, 'historial': historial}}
            if len(alertas_ord) > len(detalle):
                resto = g[g.AlertId.isin(alertas_ord[len(detalle):])].drop_duplicates('AlertId')
                exp['alertas_resumidas'] = {'cantidad': len(resto), 'categorias': resto.Category.value_counts().to_dict()}
            txt = json.dumps(exp, ensure_ascii=False)
            tokens.append(len(txt) / 4)
            with open(dir_exp / f'{inc_id}.json', 'w', encoding='utf-8') as f:
                json.dump(exp, f, ensure_ascii=False, indent=1)
            fj.write(txt + '\n')
            # referencia estadística: clase histórica más frecuente de los detectores, ponderada por alertas
            votos = np.zeros(3)
            for a in alertas:
                h = historial[a['detector']]
                if 'TP_%' in h:
                    votos += np.array([h['TP_%'], h['BP_%'], h['FP_%']])
            ref.append({'incidente': inc_id, 'clase_referencia': CLASES[int(np.argmax(votos))] if votos.sum() else 'BenignPositive',
                        'con_historial': bool(votos.sum())})
    tok = pd.Series(tokens)
    b.info(f'Expedientes: {len(tok)}. Tokens estimados: mediana {tok.median():.0f}, p95 {tok.quantile(.95):.0f}, máx {tok.max():.0f}.')
    b.info(f'Técnicas no encontradas en ATT&CK: {sorted(faltan_mitre) or "ninguna"}.')
    exceden = int((tok > ce['max_tokens_estimados']).sum())
    b.info(f'Expedientes que superan el presupuesto de {ce["max_tokens_estimados"]} tokens: {exceden}.')

    b.paso('Referencia estadística de la base de conocimiento',
           'Mide cuánto acierta la regla de la clase con mayor porcentaje histórico, sin razonamiento.')
    ref = pd.DataFrame(ref).merge(mu[['incidente', 'conjunto', 'IncidentGrade']], on='incidente')
    from sklearn.metrics import accuracy_score, f1_score
    res = {}
    for conj, d in ref.groupby('conjunto'):
        res[conj] = {'n': len(d), 'exactitud_%': round(100 * accuracy_score(d.IncidentGrade, d.clase_referencia), 1),
                     'f1_macro_%': round(100 * f1_score(d.IncidentGrade, d.clase_referencia, average='macro', labels=CLASES), 1),
                     'con_historial_%': pct(d.con_historial.sum(), len(d))}
        dh = d[d.con_historial]
        res[conj]['exactitud_con_historial_%'] = round(100 * accuracy_score(dh.IncidentGrade, dh.clase_referencia), 1) if len(dh) else None
        res[conj]['exactitud_todo_BP_%'] = round(100 * (d.IncidentGrade == 'BenignPositive').mean(), 1)
        res[conj]['f1_macro_todo_BP_%'] = round(100 * f1_score(d.IncidentGrade, ['BenignPositive'] * len(d), average='macro', labels=CLASES), 1)
        b.info(f'{conj}: {res[conj]}')
    ref.to_csv(ruta('results', 'expedientes', 'referencia_estadistica.csv'), index=False)
    guardar_json({'tokens_estimados': tok.describe().round(1).to_dict(), 'exceden_presupuesto': exceden,
                  'alertas_historicas_kb': n_kb[0], 'incidentes_historicos_kb': n_kb[1],
                  'codigos_kb': kb.groupby('tipo').size().to_dict(),
                  'codigos_kb_con_soporte': kb[kb.n >= MIN_SOPORTE].groupby('tipo').size().to_dict(),
                  'tecnicas_no_encontradas': sorted(faltan_mitre), 'referencia_estadistica': res},
                 ruta('results', 'expedientes', 'resumen_expedientes.json'))
    b.fin()


if __name__ == '__main__':
    main()
