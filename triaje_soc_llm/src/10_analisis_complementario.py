"""Paso 10. Análisis complementario de los resultados (no interviene en el contraste de las hipótesis).

Responde a preguntas que el contraste de C2 frente a C1 no cubre:
  1. Referencias sin LLM: ¿cómo se comparan C1 y C2 con la regla estadística del historial y con asignar
     siempre la clase mayoritaria (BP)? McNemar de cada condición frente a cada referencia.
  2. Subgrupos según el historial: ¿dónde se produce la diferencia entre C1 y C2?
  3. Confianza: ¿la confianza declarada distingue los aciertos de los errores? ¿Coincide con un porcentaje
     del historial (confianza copiada del historial)?
  4. Escalamiento y prioridad: ¿qué se escala y con qué exactitud queda lo que no se escala?
  5. Consistencia entre corridas del mismo incidente.
  6. Ciclo de verificación y corrección del agente de trazabilidad: activaciones, causa y desenlace.
  7. Costo: llamadas, tokens y tiempo por agente.

Entradas: results/corridas/corridas_evaluacion.jsonl, results/metricas/*.csv, data/processed/*.
Salidas:  results/estadistica/complementario.json y results/tablas/tabla_*.csv.
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix, f1_score, precision_recall_fscore_support, roc_auc_score
from statsmodels.stats.proportion import proportion_confint

from comunes import RAIZ, Bitacora, cargar_config, guardar_json, ruta

CLASES = ['TruePositive', 'BenignPositive', 'FalsePositive']
CORTO = {'TruePositive': 'TP', 'BenignPositive': 'BP', 'FalsePositive': 'FP', 'NP': 'NP'}
R4 = lambda x: None if x is None or pd.isna(x) else round(float(x), 4)


def mcnemar(a, r):
    """a: aciertos de la condición; r: aciertos de la referencia. b = solo acierta la condición."""
    from scipy.stats import binom, chi2
    a, r = np.asarray(a), np.asarray(r)
    b, c = int(((a == 1) & (r == 0)).sum()), int(((a == 0) & (r == 1)).sum())
    n = b + c
    if n == 0:
        return {'b': b, 'c': c, 'p': 1.0}
    if n < 25:
        k = min(b, c)
        return {'b': b, 'c': c, 'p': float(min(1.0, 2 * (binom.cdf(k, n, 0.5) - 0.5 * binom.pmf(k, n, 0.5))))}
    return {'b': b, 'c': c, 'p': float(chi2.sf((b - c) ** 2 / n, 1))}


def desempeno(real, asignada, B, rng):
    real, asignada = np.asarray(real), np.asarray(asignada)
    pr, rc, f1, _ = precision_recall_fscore_support(real, asignada, labels=CLASES, zero_division=0)
    n = len(real)
    f1s = []
    for _ in range(B):
        s = rng.integers(0, n, n)
        f1s.append(f1_score(real[s], asignada[s], labels=CLASES, average='macro', zero_division=0))
    tp = real == 'TruePositive'
    # exactitud: intervalo de Wilson (proporción); F1 macro: bootstrap de percentiles (no es una proporción simple)
    return {'exactitud_%': round(100 * float((real == asignada).mean()), 2),
            'IC95_exactitud_%': [round(100 * float(x), 1) for x in proportion_confint(int((real == asignada).sum()), n, alpha=0.05, method='wilson')],
            'F1_macro_%': round(100 * float(f1.mean()), 2),
            'IC95_F1_macro_%': [round(100 * float(np.percentile(f1s, q)), 1) for q in (2.5, 97.5)],
            **{f'P_{CORTO[c]}': round(float(pr[i]), 3) for i, c in enumerate(CLASES)},
            **{f'R_{CORTO[c]}': round(float(rc[i]), 3) for i, c in enumerate(CLASES)},
            **{f'F1_{CORTO[c]}': round(float(f1[i]), 3) for i, c in enumerate(CLASES)},
            'TOA_%': round(100 * float((asignada[tp] != 'TruePositive').mean()), 2),
            'aciertos': int((real == asignada).sum()), 'n': int(n)}


def ids_validos(exp):
    ids = set()
    for a in exp['alertas']:
        ids.add(a['id'])
        ids.update(e['id'] for e in a['evidencias'])
    ids.update(t['tecnica'] for t in exp['herramientas']['mitre'])
    return ids


def main():
    cfg = cargar_config()
    b = Bitacora('10_analisis_complementario')
    B = cfg['estadistica']['bootstrap_b']
    rng = np.random.default_rng(cfg['semilla'])
    reg = pd.read_csv(ruta('results', 'metricas', 'registro_observacion.csv'))
    agg = pd.read_csv(ruta('results', 'metricas', 'registro_incidente.csv'))
    ref = pd.read_csv(ruta('results', 'expedientes', 'referencia_estadistica.csv')).set_index('incidente')
    crudos = [json.loads(l) for l in ruta('results', 'corridas', 'corridas_evaluacion.jsonl').read_text(encoding='utf-8').splitlines()]
    c1 = agg[agg.condicion == 'C1'].set_index('incidente')
    c2 = agg[agg.condicion == 'C2'].set_index('incidente').loc[c1.index]
    r = ref.loc[c1.index]
    real = c1.clase_real
    res = {}

    b.paso('Referencias sin LLM frente a C1 y C2', 'Sitúa los resultados: una mejora sobre el control no implica superar una regla simple.')
    siempre_bp = pd.Series('BenignPositive', index=c1.index)
    cond = {'Siempre BP': siempre_bp, 'Regla del historial': r.clase_referencia, 'C1 (un solo LLM)': c1.clase_asignada,
            'C2 (multiagente)': c2.clase_asignada}
    des = {k: desempeno(real, v, B, rng) for k, v in cond.items()}
    res['desempeno'] = des
    td = pd.DataFrame(des).T
    td.index.name = 'condicion'
    td.to_csv(ruta('results', 'tablas', 'tabla_desempeno.csv'))
    b.tabla(td[['exactitud_%', 'F1_macro_%', 'R_TP', 'R_BP', 'R_FP', 'TOA_%']])
    ac = {k: (v == real).astype(int) for k, v in cond.items()}
    res['mcnemar_referencias'] = {f'{a} vs {x}': mcnemar(ac[a], ac[x]) for a in ('C1 (un solo LLM)', 'C2 (multiagente)')
                                  for x in ('Regla del historial', 'Siempre BP')}
    res['uniforme_al_azar_%'] = round(100 / 3, 2)
    res['coincidencia_de_clase'] = {
        'C1 = regla_%': round(100 * float((c1.clase_asignada == r.clase_referencia).mean()), 2),
        'C2 = regla_%': round(100 * float((c2.clase_asignada == r.clase_referencia).mean()), 2),
        'C1 = C2_%': round(100 * float((c1.clase_asignada == c2.clase_asignada).mean()), 2),
        'kappa C1-regla': R4(cohen_kappa_score(c1.clase_asignada, r.clase_referencia)),
        'kappa C2-regla': R4(cohen_kappa_score(c2.clase_asignada, r.clase_referencia)),
        'kappa C1-C2': R4(cohen_kappa_score(c1.clase_asignada, c2.clase_asignada))}
    for k, v in res['mcnemar_referencias'].items():
        b.info(f'{k}: {v}')
    b.info(str(res['coincidencia_de_clase']))
    conf = {}
    for k, v in cond.items():
        etiquetas = CLASES + (['NP'] if (v == 'NP').any() else [])
        m = confusion_matrix(real, v, labels=etiquetas)[:3]
        conf[k] = {CORTO[CLASES[i]]: {CORTO[e]: int(m[i, j]) for j, e in enumerate(etiquetas)} for i in range(3)}
    res['matrices_confusion'] = conf
    filas = [{'condicion': k, 'clase_real': rr, **cols} for k, m in conf.items() for rr, cols in m.items()]
    pd.DataFrame(filas).fillna(0).to_csv(ruta('results', 'tablas', 'tabla_matrices_confusion.csv'), index=False)

    b.paso('Subgrupos según el historial del detector', 'Localiza en qué incidentes difieren las condiciones.')
    sg = []
    wilson = lambda k, n: [round(100 * float(x), 1) for x in proportion_confint(k, n, alpha=0.05, method='wilson')]
    for nombre, mask in (('Todos los incidentes', np.ones(len(c1), bool)),
                         ('Con historial de detector', r.con_historial.values.astype(bool)),
                         ('Sin historial de detector', ~r.con_historial.values.astype(bool))):
        ii = c1.index[mask]
        fila = {'subgrupo': nombre, 'n': int(len(ii)),
                **{f'real_{CORTO[c]}_%': round(100 * float((real.loc[ii] == c).mean()), 1) for c in CLASES},
                'regla_%': round(100 * float(ac['Regla del historial'].loc[ii].mean()), 1),
                'C1_%': round(100 * float(c1.loc[ii].acierto.mean()), 1), 'C2_%': round(100 * float(c2.loc[ii].acierto.mean()), 1),
                'regla_IC95_%': wilson(int(ac['Regla del historial'].loc[ii].sum()), len(ii)),
                'C1_IC95_%': wilson(int(c1.loc[ii].acierto.sum()), len(ii)), 'C2_IC95_%': wilson(int(c2.loc[ii].acierto.sum()), len(ii)),
                **{f'C1_asigna_{CORTO[c]}': int((c1.loc[ii].clase_asignada == c).sum()) for c in CLASES},
                **{f'C2_asigna_{CORTO[c]}': int((c2.loc[ii].clase_asignada == c).sum()) for c in CLASES + ['NP']},
                'mcnemar_C2_vs_C1': mcnemar(c2.loc[ii].acierto, c1.loc[ii].acierto)}
        sg.append(fila)
        b.info(str(fila))
    res['subgrupos_historial'] = sg
    # En los incidentes sin historial de detector el expediente sí informa las tasas de la categoría de cada alerta.
    # ¿Siguen C1 y C2 la clase más frecuente de esas tasas?
    sin = c1.index[~r.con_historial.values.astype(bool)]
    top = {}
    for inc in sin:
        h = json.loads((RAIZ / 'data' / 'processed' / 'expedientes' / f'{inc}.json').read_text(encoding='utf-8'))['herramientas']['historial']
        suma = {c: 0.0 for c in CLASES}
        for k, v in h.items():
            if k.startswith('categoria') and 'TP_%' in v:
                for c in CLASES:
                    suma[c] += v[f'{CORTO[c]}_%']
        if any(suma.values()):
            top[inc] = max(suma, key=suma.get)
    top = pd.Series(top)
    res['sin_historial_de_detector_tasas_de_categoria'] = {
        'incidentes': int(len(sin)), 'con_tasas_de_categoria': int(len(top)),
        'clase_mas_frecuente_de_la_categoria': {CORTO[k]: int(v) for k, v in top.value_counts().items()},
        'exactitud_de_la_clase_de_la_categoria_%': round(100 * float((real.loc[top.index] == top).mean()), 1),
        'C1_coincide_%': round(100 * float((c1.loc[top.index].clase_asignada == top).mean()), 1),
        'C2_coincide_%': round(100 * float((c2.loc[top.index].clase_asignada == top).mean()), 1)}
    b.info(str(res['sin_historial_de_detector_tasas_de_categoria']))
    pd.DataFrame([{k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in f.items()} for f in sg]).to_csv(
        ruta('results', 'tablas', 'tabla_subgrupos_historial.csv'), index=False)

    b.paso('Confianza declarada', 'Una confianza útil debe ser mayor en los aciertos; se mide con el AUC y por intervalos.')
    cf = {}
    filas = []
    for c in ('C1', 'C2'):
        d = reg[(reg.condicion == c) & (reg.no_procesado == 0)]
        cortes = pd.cut(d.confianza, [0, 0.5, 0.6, 0.7, 0.8, 1.0], include_lowest=True,
                        labels=['≤ 0,50', '0,51–0,60', '0,61–0,70', '0,71–0,80', '> 0,80'])
        t = d.groupby(cortes, observed=False).acierto.agg(['size', 'mean'])
        for k, row in t.iterrows():
            filas.append({'condicion': c, 'confianza': k, 'corridas': int(row['size']),
                          'exactitud_%': round(100 * row['mean'], 1) if row['size'] else None})
        cf[c] = {'corridas': int(len(d)), 'media': R4(d.confianza.mean()), 'media_en_aciertos': R4(d[d.acierto == 1].confianza.mean()),
                 'media_en_errores': R4(d[d.acierto == 0].confianza.mean()), 'AUC_confianza_acierto': R4(roc_auc_score(d.acierto, d.confianza)),
                 'menor_que_umbral_%': round(100 * float((d.confianza < cfg['llm']['umbral_escalamiento']).mean()), 2),
                 'igual_a_una_tasa_del_historial_%': round(100 * float(d.confianza_igual_tasa.mean()), 2),
                 'exactitud_por_corrida_procesada_%': round(100 * float(d.acierto.mean()), 2)}
        b.info(f'{c}: {cf[c]}')
    res['confianza'] = cf
    pd.DataFrame(filas).to_csv(ruta('results', 'tablas', 'tabla_confianza.csv'), index=False)

    b.paso('Escalamiento y prioridad', 'El escalamiento es la salvaguarda frente a los errores: interesa qué queda sin escalar.')
    es = {}
    for c, d in (('C1', c1), ('C2', c2)):
        tp = d.clase_real == 'TruePositive'
        dr = [x for x in crudos if x['condicion'] == c and not x['no_procesado']]
        pide = np.mean([(x['salidas'].get('linea_base') or x['salidas'].get('priorizacion'))['escalar'] for x in dr])
        rr_ = reg[(reg.condicion == c) & (reg.no_procesado == 0)]
        # un incidente no procesado por mayoría no tiene decisión: no se cuenta como escalado ni como no escalado
        dec = d[d.no_procesado == 0]
        es[c] = {'escalados_n': int(dec.escalado.sum()), 'escalados_%': round(100 * float(dec.escalado.sum() / len(d)), 2),
                 'no_escalados_n': int((dec.escalado == 0).sum()), 'no_procesados_n': int(d.no_procesado.sum()),
                 'exactitud_no_escalados_%': round(100 * float(dec[dec.escalado == 0].acierto.mean()), 2),
                 'exactitud_escalados_%': round(100 * float(dec[dec.escalado == 1].acierto.mean()), 2),
                 'TP_escalados_n': int(dec[tp.loc[dec.index]].escalado.sum()),
                 'TP_escalados_%': round(100 * float(dec[tp.loc[dec.index]].escalado.sum() / tp.sum()), 2),
                 'TP_cerrados_como_BP_o_FP_sin_escalar_n': int(((dec[tp.loc[dec.index]].clase_asignada != 'TruePositive') & (dec[tp.loc[dec.index]].escalado == 0)).sum()),
                 'TP_no_procesados_n': int(d[tp].no_procesado.sum()),
                 'corridas_en_que_el_modelo_pide_escalar_%': round(100 * float(pide), 2),
                 'corridas_escaladas_%': round(100 * float(rr_.escalado.mean()), 2),
                 'prioridad_por_corrida': {k: int(v) for k, v in rr_.prioridad.value_counts().sort_index().items()},
                 'AUC_prioridad_TP_por_corrida': R4(roc_auc_score(rr_.clase_real == 'TruePositive', rr_.puntaje_prioridad))}
        b.info(f'{c}: {es[c]}')
    res['escalamiento'] = es

    b.paso('Consistencia entre corridas', 'Un sistema de apoyo debe dar la misma respuesta al mismo incidente.')
    co = {}
    for c in ('C1', 'C2'):
        p = reg[reg.condicion == c].pivot(index='incidente', columns='corrida', values='clase_asignada')
        sin = p[(p != 'NP').all(axis=1)]
        co[c] = {'unanimes_%': round(100 * float((p.nunique(axis=1) == 1).mean()), 2),
                 'kappa_entre_corridas': [R4(cohen_kappa_score(p[x], p[y])) for x, y in ((1, 2), (1, 3), (2, 3))],
                 'incidentes_sin_corridas_NP': int(len(sin)), 'unanimes_sin_NP_%': round(100 * float((sin.nunique(axis=1) == 1).mean()), 2)}
        b.info(f'{c}: {co[c]}')
    res['consistencia'] = co

    b.paso('Ciclo de verificación y corrección (agente de trazabilidad)',
           'Identifica por qué se activó la corrección y cómo terminó, porque explica las corridas no procesadas.')
    exps = {}
    d2 = [x for x in crudos if x['condicion'] == 'C2']
    proc = [x for x in d2 if not x['no_procesado']]
    npr = [x for x in d2 if x['no_procesado']]
    ctx_hist = 0
    otros = 0
    for x in proc:
        inc = x['incidente']
        if inc not in exps:
            exps[inc] = json.loads((RAIZ / 'data' / 'processed' / 'expedientes' / f'{inc}.json').read_text(encoding='utf-8'))
        v, hk = ids_validos(exps[inc]), set(exps[inc]['herramientas']['historial'].keys())
        ctx = x['salidas']['contexto']
        cit = set(ctx.get('evidencias_clave', []))
        for s in ctx.get('senales_maliciosas', []) + ctx.get('senales_benignas', []):
            cit.update(s.get('evidencias', []))
        inv = [i for i in cit if i not in v]
        ctx_hist += int(any(i in hk for i in inv))
        otros += sum(i not in hk for i in inv)
    corr = reg[(reg.condicion == 'C2') & (reg.correccion == 1)]
    inc_np = pd.Series([x['incidente'] for x in npr]).value_counts()
    res['correccion'] = {
        'corridas_C2': len(d2), 'correccion_activada': len(npr) + int(corr.shape[0]),
        'correccion_activada_%': round(100 * (len(npr) + corr.shape[0]) / len(d2), 2),
        'correcciones_concluidas': int(corr.shape[0]), 'correcciones_fallidas_no_procesadas': len(npr),
        'causa_registrada_de_las_fallidas': sorted({x['error'].split('(')[0].strip() for x in npr}),
        'fallidas_por_confianza_fuera_de_rango': int(sum('greater than the maximum of 1' in x['error'] for x in npr)),
        'concluidas_identificadores_rechazados': int(corr.ev_rechazadas_antes.sum()),
        'concluidas_rechazados_que_son_claves_del_historial': int(corr.ev_rechazadas_antes_historial.sum()),
        'concluidas_trazables_tras_la_correccion': int(corr.trazable.sum()),
        'concluidas_palabras_justificacion_media': R4(corr.palabras_justificacion.mean()),
        'contexto_cita_claves_del_historial_corridas': ctx_hist, 'contexto_cita_claves_del_historial_%': round(100 * ctx_hist / len(proc), 2),
        'contexto_identificadores_inexistentes': otros,
        'incidentes_con_alguna_corrida_no_procesada': int(len(inc_np)),
        'incidentes_segun_corridas_no_procesadas': {int(k): int(v) for k, v in inc_np.value_counts().sort_index().items()},
        'C1_corridas_con_evidencias_rechazadas': int((reg[reg.condicion == 'C1'].ev_no_verificables > 0).sum())}
    b.info(str(res['correccion']))

    # trazabilidad formal frente a corrección: decisiones que cumplen los criterios 1 a 3 pero justifican una clase errónea
    res['trazables_con_clase_erronea'] = {
        c: {'trazables': int((d.trazable == 1).sum()), 'trazables_con_clase_erronea': int(((d.trazable == 1) & (d.acierto == 0)).sum()),
            '%': round(100 * float(((d.trazable == 1) & (d.acierto == 0)).sum() / (d.trazable == 1).sum()), 1)}
        for c, d in (('C1', c1), ('C2', c2))}
    b.info('Decisiones trazables con clase errónea: ' + str(res['trazables_con_clase_erronea']))

    b.paso('Justificaciones y costo', 'Describe el producto documental de cada decisión y lo que cuesta producirlo.')
    ju = {}
    for c in ('C1', 'C2'):
        d = reg[(reg.condicion == c) & (reg.no_procesado == 0)]
        dr = [x for x in crudos if x['condicion'] == c and not x['no_procesado']]
        ju[c] = {'palabras_media': R4(d.palabras_justificacion.mean()), 'palabras_min': int(d.palabras_justificacion.min()),
                 'palabras_max': int(d.palabras_justificacion.max()), 'evidencias_citadas_media': R4(d.ev_citadas.mean()),
                 'mencionan_el_historial_%': round(100 * float(np.mean(['histor' in x['justificacion'].lower() for x in dr])), 2),
                 'tokens_entrada_media': R4(d.tokens_in.mean()), 'tokens_salida_media': R4(d.tokens_out.mean()),
                 'tokens_total_media': R4((d.tokens_in + d.tokens_out).mean()), 'llamadas_media': R4(d.llamadas.mean()),
                 'tiempo_total_h': R4(d.t_total_s.sum() / 3600)}
        b.info(f'{c}: {ju[c]}')
    res['justificaciones_y_costo'] = ju
    fechas = sorted(x['fecha'] for x in crudos)
    res['ejecucion'] = {'inicio': fechas[0], 'fin': fechas[-1], 'modelo': sorted({x['modelo'] for x in crudos}),
                        'huella_configuracion': sorted({x['version_config'] for x in crudos}), 'triajes': len(crudos)}
    guardar_json(res, ruta('results', 'estadistica', 'complementario.json'))
    b.fin()


if __name__ == '__main__':
    main()
