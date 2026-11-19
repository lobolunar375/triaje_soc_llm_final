"""Paso 07. Cálculo de indicadores y llenado del registro de observación estructurada.

Entradas: results/corridas/corridas_evaluacion.jsonl (C1 y C2), data/processed/muestra.csv y los expedientes.
          Si existen, también results/corridas/corridas_manual.jsonl (extensión con triaje manual, C0) y
          results/auditoria/auditoria_trazabilidad.csv (extensión con auditoría humana del criterio 4).
Salidas:
  results/metricas/registro_observacion.csv  una fila por incidente, condición y corrida (instrumento)
  results/metricas/registro_incidente.csv    una fila por incidente y condición (moda o mayoría de corridas)
  results/metricas/indicadores_vd.csv         PC, F1 macro, TOA, ET, TH y TD por condición
  results/metricas/indicadores_vi.csv         SV, EV, AC, TR, RI, TH, TK y complementarios por condición
  results/metricas/por_corrida.csv            indicadores por corrida (variabilidad entre corridas)
  results/metricas/tiempo_por_agente.csv      tiempo medio y mediano de cada agente de C2

Reglas de agregación entre corridas (R = 3): la clase del incidente es la moda (empate: la de mayor confianza
media; una corrida no procesada cuenta como la clase de error 'NP'); los indicadores binarios se asignan por
mayoría (al menos 2 de 3); el tiempo, los tokens y las llamadas son la mediana de las corridas procesadas.

Corridas no procesadas. Cuando un agente no entrega una salida válida tras los reintentos, el paso 05 registra
la corrida como no procesada y no conserva sus contadores parciales (llamadas, tokens, tiempo). Por eso esos
campos quedan vacíos en el registro y los promedios de tiempo y de tokens se calculan con las corridas
procesadas. La corrida no procesada sí cuenta en los indicadores de la VD: no acierta la clase y no es
trazable. El indicador SV se informa de dos formas: con las salidas registradas y con una reconstrucción que
añade, por cada corrida no procesada, las salidas que con seguridad se emitieron según el mensaje de error
(dos salidas válidas previas y cuatro inválidas del agente que falló: el intento inicial y tres reintentos).
"""
import argparse
import json
import re
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_recall_fscore_support, roc_auc_score

from comunes import RAIZ, Bitacora, cargar_config, guardar_json, ruta

LARGO = {'TP': 'TruePositive', 'BP': 'BenignPositive', 'FP': 'FalsePositive'}
CLASES = ['TruePositive', 'BenignPositive', 'FalsePositive']
NOMBRES = {'TP': r'TP|verdadero positivo|true positive', 'BP': r'BP|positivo benigno|benign positive',
           'FP': r'FP|falso positivo|false positive'}
CONTADORES = ('llamadas', 'tokens_in', 'tokens_out', 'reintentos', 'salidas_validas', 'salidas_invalidas')


def leer_expediente(inc):
    return json.loads((RAIZ / 'data' / 'processed' / 'expedientes' / f'{inc}.json').read_text(encoding='utf-8'))


def ids_validos(exp):
    """Identificadores citables: alertas, grupos de evidencias y técnicas de MITRE ATT&CK del expediente."""
    ids = set()
    for a in exp['alertas']:
        ids.add(a['id'])
        ids.update(e['id'] for e in a['evidencias'])
    ids.update(t['tecnica'] for t in exp['herramientas']['mitre'])
    return ids


def claves_historial(exp):
    """Claves de la herramienta de historial (detector, título y categoría); existen en el expediente, pero
    el verificador de trazabilidad no las acepta como evidencia citable."""
    return set(exp['herramientas']['historial'].keys())


def tasas_historial(exp):
    """Porcentajes históricos del expediente expresados como fracción (para detectar confianzas copiadas)."""
    s = set()
    for v in exp['herramientas']['historial'].values():
        for c in ('TP_%', 'BP_%', 'FP_%'):
            if c in v:
                s.add(round(v[c] / 100, 3))
    return s


def leer(arch):
    return [json.loads(l) for l in arch.read_text(encoding='utf-8').splitlines()] if arch.exists() else []


def fila_registro(r, real, exp):
    validos, hist = ids_validos(exp), claves_historial(exp)
    np_ = bool(r.get('no_procesado'))
    clase = LARGO.get(r.get('clase')) if not np_ else 'NP'
    just = r.get('justificacion') or ''
    ev = r.get('evidencias') or []
    inval = [e for e in ev if e not in validos]
    nombra = bool(re.search(r'\b(' + NOMBRES[r['clase']] + r')\b', just, re.I)) if r.get('clase') in NOMBRES else False
    c1 = int(len(just.split()) >= 20 and nombra) if not np_ else 0
    ev0 = r.get('evidencias_antes_correccion', ev) or []
    inval0 = [e for e in ev0 if e not in validos]
    c2 = int(len(ev) >= 1) if not np_ else 0
    c3 = int(len(ev) >= 1 and not inval) if not np_ else 0
    pr = r.get('prioridad')
    conf = r.get('confianza')
    fila = {'incidente': r['incidente'], 'condicion': r['condicion'], 'corrida': r.get('semilla', 1),
            'analista': r.get('analista'), 'uso': r.get('uso', 'principal'), 'clase_real': real, 'clase_asignada': clase,
            'acierto': int(clase == real), 'omision_amenaza': int(real == 'TruePositive' and clase != 'TruePositive'),
            'confianza': conf, 'prioridad': pr,
            'puntaje_prioridad': {'P1': 4, 'P2': 3, 'P3': 2, 'P4': 1}.get(pr), 'escalado': int(bool(r.get('escalado'))),
            't_total_s': r.get('t_total_s'), **{f't_{k}_s': v for k, v in (r.get('t_agentes') or {}).items()},
            'no_procesado': int(np_), 'correccion': int(bool(r.get('correccion'))),
            'crit1': c1, 'crit2': c2, 'crit3': c3, 'trazable': c1 * c2 * c3,
            'trazable_antes_correccion': c1 * c2 * int(len(ev0) >= 1 and not inval0) if not np_ else 0,
            'palabras_justificacion': len(just.split()) if not np_ else None,
            'ev_citadas': len(ev) if not np_ else None, 'ev_no_verificables': len(inval) if not np_ else None,
            'ev_rechazadas_antes': len(inval0) if not np_ else None,
            'ev_rechazadas_antes_historial': sum(e in hist for e in inval0) if not np_ else None,
            'confianza_igual_tasa': int(conf is not None and round(conf, 3) in tasas_historial(exp)) if not np_ else None,
            'version_config': r.get('version_config'), 'modelo': r.get('modelo'), 'fecha': r.get('fecha')}
    # los contadores de una corrida no procesada no se conservaron: se dejan vacíos, no en cero
    for k in CONTADORES:
        fila[k] = r.get(k) if not np_ else None
    return fila


def moda_clase(g):
    cnt = Counter(g.clase_asignada)
    mx = max(cnt.values())
    emp = [c for c, k in cnt.items() if k == mx]
    if len(emp) == 1:
        return emp[0]
    conf = g[g.clase_asignada.isin(emp)].groupby('clase_asignada').confianza.mean()
    return conf.idxmax() if conf.notna().any() else emp[0]


def agregar(reg):
    filas = []
    for (inc, cond), g in reg.groupby(['incidente', 'condicion']):
        clase = moda_clase(g)
        R = len(g)
        may = lambda c: int(g[c].fillna(0).sum() * 2 > R) if R > 1 else int(g[c].fillna(0).iloc[0])
        filas.append({'incidente': inc, 'condicion': cond, 'corridas': R, 'corridas_no_procesadas': int(g.no_procesado.sum()),
                      'clase_real': g.clase_real.iloc[0],
                      'clase_asignada': clase, 'acierto': int(clase == g.clase_real.iloc[0]),
                      'omision_amenaza': int(g.clase_real.iloc[0] == 'TruePositive' and clase != 'TruePositive'),
                      'acuerdo_corridas': int(g.clase_asignada.nunique() == 1),
                      'confianza': g.confianza.mean(), 'puntaje_prioridad': g.puntaje_prioridad.median(),
                      'escalado': may('escalado'), 't_total_s': g.t_total_s.median(),
                      'llamadas': g.llamadas.median(), 'tokens': (g.tokens_in + g.tokens_out).median(),
                      'reintentos': g.reintentos.median(), 'no_procesado': may('no_procesado'),
                      'crit1': may('crit1'), 'crit2': may('crit2'), 'crit3': may('crit3'), 'trazable': may('trazable'),
                      'trazable_antes_correccion': may('trazable_antes_correccion'),
                      'ev_citadas': g.ev_citadas.median(), 'ev_no_verificables': g.ev_no_verificables.median()})
    return pd.DataFrame(filas)


def nivel(valor, bajo, alto, mayor_es_mejor=True):
    """Nivel de la matriz de operacionalización (Bajo, Medio o Alto)."""
    if valor is None or pd.isna(valor):
        return None
    if mayor_es_mejor:
        return 'Bajo' if valor < bajo else ('Alto' if valor > alto else 'Medio')
    return 'Bajo' if valor > bajo else ('Alto' if valor < alto else 'Medio')


def indicadores_vd(d):
    y, p = d.clase_real, d.clase_asignada
    pr, rc, f1, _ = precision_recall_fscore_support(y, p, labels=CLASES, zero_division=0)
    t = d.t_total_s.dropna()
    pc = 100 * (y == p).mean()
    et = t.mean() / 60 if len(t) else None
    tdv = 100 * d.trazable.mean()
    return {'n': len(d), 'PC_%': round(pc, 2), 'nivel_PC': nivel(pc, 70, 85),
            'F1_macro_%': round(100 * f1_score(y, p, labels=CLASES, average='macro', zero_division=0), 2),
            **{f'P_{c[:2]}': round(pr[i], 3) for i, c in enumerate(CLASES)},
            **{f'R_{c[:2]}': round(rc[i], 3) for i, c in enumerate(CLASES)},
            **{f'F1_{c[:2]}': round(f1[i], 3) for i, c in enumerate(CLASES)},
            'TOA_%': round(100 * d[d.clase_real == 'TruePositive'].omision_amenaza.mean(), 2) if (d.clase_real == 'TruePositive').any() else None,
            'n_con_tiempo': len(t), 'ET_media_s': round(t.mean(), 3) if len(t) else None,
            'ET_mediana_s': round(t.median(), 3) if len(t) else None, 'ET_de_s': round(t.std(), 3) if len(t) > 1 else None,
            'ET_media_min': round(et, 4) if et is not None else None, 'nivel_ET': nivel(et, 15, 5, mayor_es_mejor=False),
            'TH_inc_h': round(3600 * len(t) / t.sum(), 1) if len(t) and t.sum() else None,
            'TD_%': round(tdv, 2), 'nivel_TD': nivel(tdv, 60, 85),
            'TD_antes_correccion_%': round(100 * d.trazable_antes_correccion.mean(), 2), 'crit1_%': round(100 * d.crit1.mean(), 2),
            'crit2_%': round(100 * d.crit2.mean(), 2), 'crit3_%': round(100 * d.crit3.mean(), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plantilla-auditoria', action='store_true',
                    help='prepara la plantilla de la auditoría humana del criterio 4 (extensión no ejecutada en el estudio)')
    a = ap.parse_args()
    cfg = cargar_config()
    b = Bitacora('07_calcular_metricas')
    mu = pd.read_csv(ruta('data', 'processed', 'muestra.csv'))
    real = dict(zip(mu.incidente, mu.IncidentGrade))
    crudos = leer(ruta('results', 'corridas', 'corridas_evaluacion.jsonl')) + leer(ruta('results', 'corridas', 'corridas_manual.jsonl'))
    if not crudos:
        b.info('No hay corridas todavía. Ejecute 05_triaje_llm.py.')
        return
    b.paso('Construir el registro de observación (una fila por incidente, condición y corrida)',
           'Es el instrumento de recolección; todos los indicadores se calculan a partir de él.')
    cache = {}
    filas = []
    for r in crudos:
        inc = r['incidente']
        if inc not in cache:
            cache[inc] = leer_expediente(inc)
        filas.append(fila_registro(r, real[inc], cache[inc]))
    reg = pd.DataFrame(filas)
    reg.to_csv(ruta('results', 'metricas', 'registro_observacion.csv'), index=False)
    b.info(f'Filas: {len(reg)}. Por condición: {reg.condicion.value_counts().to_dict()}')
    b.info(f'Corridas no procesadas por condición: {reg.groupby("condicion").no_procesado.sum().to_dict()}')
    b.info(f'Modelo: {reg.modelo.dropna().unique().tolist()}. Huella de configuración: {reg.version_config.dropna().unique().tolist()}. '
           f'Fechas: {reg.fecha.min()} a {reg.fecha.max()}')

    b.paso('Agregar las corridas por incidente', 'Moda para la clase, mayoría para los indicadores binarios y mediana para el tiempo.')
    principal = reg[(reg.condicion != 'C0') | (reg.uso == 'principal')]
    agg = agregar(principal)
    aud = RAIZ / 'results' / 'auditoria' / 'auditoria_trazabilidad.csv'   # solo existe si se ejecutó la extensión con auditoría humana
    if aud.exists():
        au = pd.read_csv(aud).dropna(subset=['crit4_consenso'])
        agg = agg.merge(au[['incidente', 'condicion', 'crit4_consenso']], on=['incidente', 'condicion'], how='left')
        # la auditoría revisa la primera corrida: los criterios 1 a 3 se toman de esa misma corrida
        r1 = principal[principal.corrida == principal.groupby('condicion').corrida.transform('min')]
        agg = agg.merge(r1[['incidente', 'condicion', 'trazable']].rename(columns={'trazable': 'trazable_corrida1'}),
                        on=['incidente', 'condicion'], how='left')
        agg['trazable_aud'] = np.where(agg.crit4_consenso.notna(), agg.trazable_corrida1 * agg.crit4_consenso, np.nan)
    agg.to_csv(ruta('results', 'metricas', 'registro_incidente.csv'), index=False)

    b.paso('Indicadores de la VD por condición', 'PC, F1 macro, TOA, ET, TH y TD, con su nivel según la matriz de operacionalización.')
    hay_c0 = (agg.condicion == 'C0').any()
    c0_ids = set(mu[mu.submuestra_c0].incidente) if hay_c0 else set()
    filas = []
    for cond, d in agg.groupby('condicion'):
        filas.append({'condicion': cond, 'conjunto': 'evaluacion' if cond != 'C0' else 'submuestra C0', **indicadores_vd(d)})
        if hay_c0 and cond != 'C0':
            filas.append({'condicion': cond, 'conjunto': 'mismos incidentes de C0', **indicadores_vd(d[d.incidente.isin(c0_ids)])})
    vd = pd.DataFrame(filas)
    b.tabla(vd[['condicion', 'conjunto', 'n', 'PC_%', 'nivel_PC', 'F1_macro_%', 'TOA_%', 'ET_media_s', 'nivel_ET', 'TH_inc_h', 'TD_%', 'nivel_TD']])
    vd.to_csv(ruta('results', 'metricas', 'indicadores_vd.csv'), index=False)

    b.paso('Indicadores de la VI por condición automática',
           'SV, EV, AC, TR, RI, TH y TK, según la matriz de la VI. Los promedios usan las corridas procesadas.')
    filas = []
    for cond, d in reg[reg.condicion != 'C0'].groupby('condicion'):
        ag = agg[agg.condicion == cond]
        ok = d[d.no_procesado == 0]
        n_np = int(d.no_procesado.sum())
        tp = ag.clase_real == 'TruePositive'
        pp = ag.puntaje_prioridad
        auc = roc_auc_score(tp[pp.notna()], pp[pp.notna()]) if tp[pp.notna()].nunique() == 2 else None
        val, inv = ok.salidas_validas.sum(), ok.salidas_invalidas.sum()
        filas.append({'condicion': cond, 'corridas': len(d), 'corridas_procesadas': len(ok),
                      'no_procesadas_%': round(100 * n_np / len(d), 2),
                      'SV_registrada_%': round(100 * val / (val + inv), 2),
                      'SV_reconstruida_%': round(100 * (val + 2 * n_np) / (val + inv + 6 * n_np), 2),
                      'EV_%': round(100 * (1 - ok.ev_no_verificables.sum() / max(ok.ev_citadas.sum(), 1)), 2),
                      'AC_%': round(100 * ag.acuerdo_corridas.mean(), 2),
                      'TR_media_s': round(ok.t_total_s.mean(), 2), 'TR_mediana_s': round(ok.t_total_s.median(), 2),
                      'TR_de_s': round(ok.t_total_s.std(), 2), 'RI': round(ok.reintentos.mean(), 4),
                      'TH_inc_h': round(3600 * len(ok) / ok.t_total_s.sum(), 1),
                      'TK': round((ok.tokens_in + ok.tokens_out).mean(), 0), 'TK_entrada': round(ok.tokens_in.mean(), 0),
                      'TK_salida': round(ok.tokens_out.mean(), 0), 'llamadas': round(ok.llamadas.mean(), 3),
                      'escalados_%': round(100 * ag.escalado.mean(), 2),
                      'correcciones_concluidas': int(ok.correccion.sum()), 'correcciones_fallidas': n_np if cond == 'C2' else 0,
                      'AUC_prioridad_TP': round(auc, 3) if auc is not None else None})
    vi = pd.DataFrame(filas)
    if len(vi):
        b.tabla(vi.T)
    vi.to_csv(ruta('results', 'metricas', 'indicadores_vi.csv'), index=False)
    tcols = [c for c in reg.columns if c.startswith('t_') and c.endswith('_s') and c != 't_total_s']
    if tcols:
        t2 = reg[(reg.condicion == 'C2') & (reg.no_procesado == 0)][tcols]
        ta = pd.DataFrame({'media_s': t2.mean().round(3), 'mediana_s': t2.median().round(3), 'corridas': t2.notna().sum()})
        ta.index = [i[2:-2] for i in ta.index]
        ta.index.name = 'agente'
        ta.to_csv(ruta('results', 'metricas', 'tiempo_por_agente.csv'))

    b.paso('Indicadores por corrida', 'Muestra la variabilidad entre corridas del modelo.')
    pc = [{'condicion': c, 'corrida': s, **indicadores_vd(d)} for (c, s), d in reg[reg.condicion != 'C0'].groupby(['condicion', 'corrida'])]
    pc = pd.DataFrame(pc)
    pc.to_csv(ruta('results', 'metricas', 'por_corrida.csv'), index=False)
    b.tabla(pc[['condicion', 'corrida', 'PC_%', 'F1_macro_%', 'TOA_%', 'ET_media_s', 'TD_%']])

    if a.plantilla_auditoria:
        b.paso('Preparar la plantilla de auditoría ciega del criterio 4 (extensión)',
               'Las decisiones se normalizan (clase, justificación, evidencias) y se mezclan para ocultar su condición.')
        aud_ids = set(mu[mu.auditoria].incidente)
        cand = []
        for r in crudos:
            if r.get('no_procesado'):
                continue
            if (r['condicion'] != 'C0' and r['incidente'] in aud_ids and r.get('semilla') == cfg['llm']['semillas'][0]) or \
               (r['condicion'] == 'C0' and r.get('uso') == 'principal'):
                cand.append({'incidente': r['incidente'], 'condicion': r['condicion'], 'clase': r['clase'],
                             'justificacion': r['justificacion'], 'evidencias': ', '.join(r['evidencias'])})
        if cand:
            pa = pd.DataFrame(cand).sample(frac=1, random_state=cfg['semilla']).reset_index(drop=True)
            pa.insert(0, 'decision', [f'DEC-{k + 1:03d}' for k in range(len(pa))])
            pa[['decision', 'incidente', 'condicion']].to_csv(ruta('results', 'auditoria', 'clave_auditoria_NO_ABRIR.csv'), index=False)
            vis = pa[['decision', 'incidente', 'clase', 'justificacion', 'evidencias']].copy()
            for c in ('explica_clase_A', 'sostiene_clase_A', 'explica_clase_B', 'sostiene_clase_B'):
                vis[c] = ''
            vis.to_csv(ruta('results', 'auditoria', 'plantilla_auditoria.csv'), index=False)
            b.info(f'Decisiones para auditar: {len(pa)}.')
    guardar_json({'vd': vd.to_dict(orient='records'), 'vi': vi.to_dict(orient='records')},
                 ruta('results', 'metricas', 'resumen_metricas.json'))
    b.fin()


if __name__ == '__main__':
    main()
