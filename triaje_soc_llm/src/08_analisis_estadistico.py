"""Paso 08. Contraste de hipótesis.

Diseño pareado: cada incidente de evaluación se procesa en las dos condiciones (C1, un solo LLM, control;
C2, sistema multiagente, experimental), de modo que actúa como su propio control.

  H.E.1 (precisión):    McNemar C2 frente a C1 sobre el acierto por incidente (n = 300). Estadístico asintótico
                        sin corrección de continuidad; si b + c < 25, versión mid-p de la prueba binomial exacta.
                        Tamaño del efecto: razón b/c y diferencia de exactitud y de F1 macro con IC 95 % por
                        bootstrap pareado.
  H.E.2 (eficiencia):   Wilcoxon de rangos con signo sobre d = t(C2) - t(C1) por incidente; tamaño del efecto:
                        correlación biserial de rangos r = (W+ - W-) / (W+ + W-). Un valor negativo indicaría
                        que C2 reduce el tiempo. Solo entran los incidentes con tiempo registrado en ambas
                        condiciones.
  H.E.3 (trazabilidad): McNemar C2 frente a C1 sobre la decisión trazable (criterios 1 a 3).
  Corrección de Holm sobre los tres valores p. Todas las pruebas son bilaterales; una hipótesis solo se acepta
  si el valor p ajustado es menor que alfa y el efecto tiene la dirección planteada (mejora con C2).
  Sensibilidad: por corrida individual, solo incidentes sin corridas no procesadas, sin incidentes escalados,
  por subgrupo según el historial y con bootstrap por conglomerados (organización).

Si existen corridas del triaje manual (extensión C0), se añade la comparación descriptiva de tiempos con C0.
"""
import numpy as np
import pandas as pd
from scipy.stats import binom, chi2, rankdata, wilcoxon
from sklearn.metrics import f1_score
from statsmodels.stats.multitest import multipletests

from comunes import Bitacora, cargar_config, guardar_json, ruta

CLASES = ['TruePositive', 'BenignPositive', 'FalsePositive']


def mcnemar(a2, a1):
    """a2, a1: indicadores (0/1) pareados de C2 y C1. b = solo C2 cumple; c = solo C1 cumple."""
    a2, a1 = np.asarray(a2), np.asarray(a1)
    b, c = int(((a2 == 1) & (a1 == 0)).sum()), int(((a2 == 0) & (a1 == 1)).sum())
    n = b + c
    if n == 0:
        return {'b': b, 'c': c, 'estadistico': 0.0, 'p': 1.0, 'metodo': 'sin pares discordantes', 'razon_bc': None}
    if n < 25:
        k = min(b, c)
        p = float(min(1.0, 2 * (binom.cdf(k, n, 0.5) - 0.5 * binom.pmf(k, n, 0.5))))
        est, met = None, 'mid-p'
    else:
        est = float((b - c) ** 2 / n)
        p, met = float(chi2.sf(est, 1)), 'asintótico sin corrección'
    return {'b': b, 'c': c, 'estadistico': est, 'p': p, 'metodo': met, 'razon_bc': round(b / c, 3) if c else None}


def wilcoxon_rb(x, y):
    """Wilcoxon de rangos con signo sobre x - y, con la correlación biserial de rangos. Omite pares incompletos."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~np.isnan(x) & ~np.isnan(y)
    x, y = x[ok], y[ok]
    d = x - y
    dn = d[d != 0]
    r = rankdata(np.abs(dn))
    wp, wm = float(r[dn > 0].sum()), float(r[dn < 0].sum())
    res = wilcoxon(x, y, zero_method='wilcox')
    return {'n_pares': int(len(d)), 'W_mas': wp, 'W_menos': wm, 'W': float(res.statistic), 'p': float(res.pvalue),
            'r_rb': round((wp - wm) / (wp + wm), 4), 'mediana_dif_s': round(float(np.median(d)), 4),
            'pares_con_C2_mas_lento': int((d > 0).sum()), 'mediana_x_s': round(float(np.median(x)), 4),
            'mediana_y_s': round(float(np.median(y)), 4), 'razon_medianas': round(float(np.median(x) / np.median(y)), 2)}


def boot(df2, df1, fun, B, seed, grupos=None):
    """IC 95 % por bootstrap pareado de fun(C2) - fun(C1) y de cada condición. grupos: remuestreo por conglomerado."""
    rng = np.random.default_rng(seed)
    n = len(df2)
    dif, v1, v2 = [], [], []
    if grupos is not None:
        g = np.asarray(grupos)
        uniq = np.unique(g)
        idx = {u: np.where(g == u)[0] for u in uniq}
    for _ in range(B):
        s = rng.integers(0, n, n) if grupos is None else np.concatenate([idx[u] for u in rng.choice(uniq, len(uniq))])
        a, c = fun(df2.iloc[s]), fun(df1.iloc[s])
        dif.append(a - c)
        v2.append(a)
        v1.append(c)
    ic = lambda v: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
    return {'dif': ic(dif), 'C1': ic(v1), 'C2': ic(v2)}


f1m = lambda d: f1_score(d.clase_real, d.clase_asignada, labels=CLASES, average='macro', zero_division=0)
acc = lambda d: (d.clase_real == d.clase_asignada).mean()
td = lambda d: d.trazable.mean()


def main():
    cfg = cargar_config()
    e = cfg['estadistica']
    b = Bitacora('08_analisis_estadistico')
    agg = pd.read_csv(ruta('results', 'metricas', 'registro_incidente.csv'))
    reg = pd.read_csv(ruta('results', 'metricas', 'registro_observacion.csv'))
    mu = pd.read_csv(ruta('data', 'processed', 'muestra.csv'))
    ref = pd.read_csv(ruta('results', 'expedientes', 'referencia_estadistica.csv')).set_index('incidente')
    org = dict(zip(mu.incidente, mu.OrgId))
    c1 = agg[agg.condicion == 'C1'].set_index('incidente')
    c2 = agg[agg.condicion == 'C2'].set_index('incidente')
    comunes = c1.index.intersection(c2.index)
    c1, c2 = c1.loc[comunes].reset_index(), c2.loc[comunes].reset_index()
    B, sem = e['bootstrap_b'], cfg['semilla']
    res = {'n_incidentes': int(len(comunes))}

    b.paso('H.E.1: McNemar sobre el acierto, C2 frente a C1', 'Respuesta binaria y pareada por incidente.')
    res['HE1'] = mcnemar(c2.acierto, c1.acierto)
    bo_a, bo_f = boot(c2, c1, acc, B, sem), boot(c2, c1, f1m, B, sem)
    res['HE1'].update({'exactitud_C1': round(float(acc(c1)), 4), 'exactitud_C2': round(float(acc(c2)), 4),
                       'IC95_exactitud_C1': bo_a['C1'], 'IC95_exactitud_C2': bo_a['C2'], 'IC95_dif_exactitud': bo_a['dif'],
                       'f1_C1': round(float(f1m(c1)), 4), 'f1_C2': round(float(f1m(c2)), 4),
                       'IC95_f1_C1': bo_f['C1'], 'IC95_f1_C2': bo_f['C2'], 'IC95_dif_f1': bo_f['dif']})
    b.info(str(res['HE1']))

    b.paso('H.E.2: Wilcoxon sobre el tiempo por incidente, C2 frente a C1',
           'Los tiempos son asimétricos; se comparan las diferencias pareadas. Un incidente sin tiempo en C2 (tres corridas no procesadas) no entra.')
    res['HE2'] = wilcoxon_rb(c2.t_total_s.values, c1.t_total_s.values)
    dif = (c2.t_total_s - c1.t_total_s).dropna().values
    rng = np.random.default_rng(sem)
    meds = [np.median(dif[rng.integers(0, len(dif), len(dif))]) for _ in range(B)]
    res['HE2']['IC95_mediana_dif_s'] = [round(float(np.percentile(meds, 2.5)), 3), round(float(np.percentile(meds, 97.5)), 3)]
    res['HE2'].update({'media_C1_s': round(float(c1.t_total_s.mean()), 4), 'media_C2_s': round(float(c2.t_total_s.mean()), 4),
                       'de_C1_s': round(float(c1.t_total_s.std()), 4), 'de_C2_s': round(float(c2.t_total_s.std()), 4)})
    b.info(str(res['HE2']))
    c0 = agg[agg.condicion == 'C0'].set_index('incidente')
    if len(c0) >= 5:
        par = c0.index.intersection(c2.set_index('incidente').index)
        res['extension_C2_vs_C0'] = wilcoxon_rb(c2.set_index('incidente').loc[par].t_total_s.values, c0.loc[par].t_total_s.values)
        b.info('Extensión con triaje manual (descriptiva): ' + str(res['extension_C2_vs_C0']))

    b.paso('H.E.3: McNemar sobre la decisión trazable (criterios 1 a 3), C2 frente a C1', 'Proporción pareada.')
    res['HE3'] = mcnemar(c2.trazable, c1.trazable)
    bo_t = boot(c2, c1, td, B, sem)
    res['HE3'].update({'TD_C1': round(float(td(c1)), 4), 'TD_C2': round(float(td(c2)), 4), 'IC95_TD_C1': bo_t['C1'],
                       'IC95_TD_C2': bo_t['C2'], 'IC95_dif_TD': bo_t['dif']})
    b.info(str(res['HE3']))

    b.paso('Corrección de Holm y decisión', 'Controla el error de tipo I al contrastar tres hipótesis; además se exige la dirección planteada.')
    ps = [res['HE1']['p'], res['HE2']['p'], res['HE3']['p']]
    aj = multipletests(ps, alpha=e['alfa'], method='holm')[1]
    for h, p in zip(('HE1', 'HE2', 'HE3'), aj):
        res[h]['p_holm'] = float(p)
    favorable = {'HE1': res['HE1']['b'] > res['HE1']['c'] and res['HE1']['f1_C2'] > res['HE1']['f1_C1'],
                 'HE2': res['HE2']['mediana_dif_s'] < 0, 'HE3': res['HE3']['b'] > res['HE3']['c']}
    dec = {}
    for h in ('HE1', 'HE2', 'HE3'):
        sig = res[h]['p_holm'] < e['alfa']
        dec[h] = {'significativa': bool(sig), 'direccion_favorable_a_C2': bool(favorable[h]), 'se_acepta': bool(sig and favorable[h])}
    k = sum(d['se_acepta'] for d in dec.values())
    dec['HG'] = 'se acepta' if k == 3 else ('se acepta parcialmente' if k else 'no se acepta')
    res['decisiones'] = dec
    b.info(str(dec))

    b.paso('Análisis de sensibilidad',
           'Las conclusiones no deben depender de una corrida, de las corridas no procesadas, de los escalados ni de la agrupación por organización.')
    sens = []
    for s, d in reg[reg.condicion != 'C0'].groupby('corrida'):
        d1, d2 = d[d.condicion == 'C1'].set_index('incidente'), d[d.condicion == 'C2'].set_index('incidente')
        ii = d1.index.intersection(d2.index)
        m = mcnemar(d2.loc[ii].acierto, d1.loc[ii].acierto)
        sens.append({'analisis': f'H.E.1, corrida {s}', 'n': len(ii), 'exactitud_C1': round(float(d1.loc[ii].acierto.mean()), 4),
                     'exactitud_C2': round(float(d2.loc[ii].acierto.mean()), 4), 'b': m['b'], 'c': m['c'], 'p': m['p']})
        m = mcnemar(d2.loc[ii].trazable, d1.loc[ii].trazable)
        sens.append({'analisis': f'H.E.3, corrida {s}', 'n': len(ii), 'TD_C1': round(float(d1.loc[ii].trazable.mean()), 4),
                     'TD_C2': round(float(d2.loc[ii].trazable.mean()), 4), 'b': m['b'], 'c': m['c'], 'p': m['p']})

    def sub(nombre, mascara):
        m = mcnemar(c2[mascara].acierto, c1[mascara].acierto)
        sens.append({'analisis': nombre, 'n': int(mascara.sum()), 'exactitud_C1': round(float(c1[mascara].acierto.mean()), 4),
                     'exactitud_C2': round(float(c2[mascara].acierto.mean()), 4), 'b': m['b'], 'c': m['c'], 'p': m['p']})

    sub('H.E.1, incidentes sin corridas no procesadas en C2', (c2.corridas_no_procesadas == 0).values)
    sub('H.E.1, sin los incidentes no procesados por mayoría en C2', (c2.no_procesado == 0).values)
    # un incidente no procesado por mayoría no tiene decisión que escalar: se excluye de este subconjunto
    sub('H.E.1, incidentes con decisión no escalada en ambas condiciones',
        ((c1.escalado == 0) & (c2.escalado == 0) & (c2.no_procesado == 0) & (c1.no_procesado == 0)).values)
    hist = c2.incidente.map(ref.con_historial).values.astype(bool)
    sub('H.E.1, incidentes con historial de detector', hist)
    sub('H.E.1, incidentes sin historial de detector', ~hist)
    grupos = c2.incidente.map(org)
    sens.append({'analisis': 'IC95 dif. exactitud, bootstrap por organización', 'ic': boot(c2, c1, acc, B, sem, grupos=grupos)['dif']})
    sens.append({'analisis': 'IC95 dif. F1 macro, bootstrap por organización', 'ic': boot(c2, c1, f1m, B, sem, grupos=grupos)['dif']})
    sens.append({'analisis': 'IC95 dif. TD, bootstrap por organización', 'ic': boot(c2, c1, td, B, sem, grupos=grupos)['dif']})
    m = mcnemar(c2.trazable_antes_correccion, c1.trazable)
    sens.append({'analisis': 'H.E.3 con C2 antes de la corrección de trazabilidad', 'b': m['b'], 'c': m['c'], 'p': m['p']})
    res['sensibilidad'] = sens
    for s in sens:
        b.info(str(s))

    guardar_json(res, ruta('results', 'estadistica', 'contrastes.json'))
    fp = lambda p: f'{p:.4f}' if p >= 0.0001 else f'{p:.2e}'
    with open(ruta('results', 'estadistica', 'decision_hipotesis.md'), 'w', encoding='utf-8') as f:
        f.write('# Decisión sobre las hipótesis\n\n')
        f.write(f'Diseño pareado, n = {len(comunes)} incidentes de evaluación; C1 (un solo LLM, control) frente a C2 (sistema multiagente).\n\n')
        f.write('| Hipótesis | Prueba | Resultado | p | p (Holm) | Dirección | Decisión |\n|:--|:--|:--|--:|--:|:--|:--|\n')
        h1, h2, h3 = res['HE1'], res['HE2'], res['HE3']
        f.write(f"| H.E.1 precisión | McNemar ({h1['metodo']}) | exactitud {100 * h1['exactitud_C1']:.2f} % → {100 * h1['exactitud_C2']:.2f} %; "
                f"b = {h1['b']}, c = {h1['c']} | {fp(h1['p'])} | {fp(h1['p_holm'])} | favorable a C2 | "
                f"{'se acepta' if dec['HE1']['se_acepta'] else 'no se acepta'} |\n")
        f.write(f"| H.E.2 eficiencia temporal | Wilcoxon | mediana {h2['mediana_y_s']:.2f} s → {h2['mediana_x_s']:.2f} s; "
                f"r_rb = {h2['r_rb']} (n = {h2['n_pares']}) | {fp(h2['p'])} | {fp(h2['p_holm'])} | "
                f"{'favorable a C2' if favorable['HE2'] else 'contraria (C2 tarda más)'} | {'se acepta' if dec['HE2']['se_acepta'] else 'no se acepta'} |\n")
        f.write(f"| H.E.3 trazabilidad | McNemar ({h3['metodo']}) | TD {100 * h3['TD_C1']:.2f} % → {100 * h3['TD_C2']:.2f} %; "
                f"b = {h3['b']}, c = {h3['c']} | {fp(h3['p'])} | {fp(h3['p_holm'])} | "
                f"{'favorable a C2' if favorable['HE3'] else 'contraria (C2 es menor)'} | {'se acepta' if dec['HE3']['se_acepta'] else 'no se acepta'} |\n")
        f.write(f"\n**Hipótesis general**: {dec['HG']}.\n")
    b.fin()


if __name__ == '__main__':
    main()
