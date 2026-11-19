"""Verifica que las cifras del artículo coinciden con los archivos de results/.

Uso: python verificar_cifras.py <paper.md> <carpeta del repositorio>
Recalcula cada cifra a partir de los resultados, la formatea como en el texto (coma decimal) y comprueba que
aparece en el artículo. Termina con error si alguna falta.
"""
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

paper, repo = Path(sys.argv[1]), Path(sys.argv[2])
t = paper.read_text(encoding='utf-8').replace(' ', ' ')
R = repo / 'results'
con = json.loads((R / 'estadistica' / 'contrastes.json').read_text(encoding='utf-8'))
com = json.loads((R / 'estadistica' / 'complementario.json').read_text(encoding='utf-8'))
vd = pd.read_csv(R / 'metricas' / 'indicadores_vd.csv').set_index('condicion')
vi = pd.read_csv(R / 'metricas' / 'indicadores_vi.csv').set_index('condicion')
pc = pd.read_csv(R / 'metricas' / 'por_corrida.csv')
ta = pd.read_csv(R / 'metricas' / 'tiempo_por_agente.csv', index_col=0)
lim = json.loads((R / 'limpieza' / 'reporte_limpieza.json').read_text(encoding='utf-8'))
mue = json.loads((R / 'muestra' / 'resumen_muestra.json').read_text(encoding='utf-8'))
exp = json.loads((R / 'expedientes' / 'resumen_expedientes.json').read_text(encoding='utf-8'))


def f(x, d=1):
    # redondeo aritmético (mitad hacia arriba) sobre la representación decimal del valor
    q = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    return f'{q:.{d}f}'.replace('.', ',')


def miles(n):
    return f'{int(n):,}'.replace(',', ' ')


D = com['desempeno']
c1, c2, rg, bp = D['C1 (un solo LLM)'], D['C2 (multiagente)'], D['Regla del historial'], D['Siempre BP']
h1, h2, h3 = con['HE1'], con['HE2'], con['HE3']
sen = {s['analisis']: s for s in con['sensibilidad']}
esc, cf, cor, co = com['escalamiento'], com['confianza'], com['correccion'], com['consistencia']
sg = {g['subgrupo']: g for g in com['subgrupos_historial']}
cat = com['sin_historial_de_detector_tasas_de_categoria']
tz = com['trazables_con_clase_erronea']
checks = []


def chk(nombre, texto):
    checks.append((nombre, texto, texto in t))


# --- desempeño (Tabla 6 y texto)
for nom, d in (('C1', c1), ('C2', c2), ('regla', rg), ('siempre BP', bp)):
    chk(f'exactitud {nom}', f"{f(d['exactitud_%'])} [{f(d['IC95_exactitud_%'][0])}; {f(d['IC95_exactitud_%'][1])}]")
    chk(f'F1 macro {nom}', f"{f(d['F1_macro_%'])} [{f(d['IC95_F1_macro_%'][0])}; {f(d['IC95_F1_macro_%'][1])}]")
    chk(f'aciertos {nom}', f"| {d['aciertos']} |")
    chk(f'TOA {nom}', f"{f(d['TOA_%'])} |")
for nom, d in (('regla', rg), ('C1', c1), ('C2', c2)):
    for cl in ('TP', 'BP', 'FP'):
        for m in ('P', 'R', 'F1'):
            chk(f'{m}_{cl} {nom}', f(d[f'{m}_{cl}'], 3))
# --- H.E.1
chk('HE1 b y c', f"*b* = {h1['b']}, *c* = {h1['c']}")
chk('HE1 chi2', f"= {f(h1['estadistico'], 2)}")
chk('HE1 p', f"*p* = {f(h1['p'], 3)}")
chk('HE1 dif exactitud IC', f"+{f(100 * (h1['exactitud_C2'] - h1['exactitud_C1']))} [+{f(100 * h1['IC95_dif_exactitud'][0])}; +{f(100 * h1['IC95_dif_exactitud'][1])}]")
chk('HE1 dif F1 IC', f"+{f(100 * (h1['f1_C2'] - h1['f1_C1']))} [+{f(100 * h1['IC95_dif_f1'][0])}; +{f(100 * h1['IC95_dif_f1'][1])}]")
chk('HE1 razón b/c', f"razón de {f(h1['b'] / h1['c'], 2)}")
chk('proporción discordante', f"{f((h1['b'] + h1['c']) / con['n_incidentes'], 2)}, fue cercana")
# --- H.E.2
chk('HE2 mediana C1', f"mediana de {f(h2['mediana_y_s'], 2)} s en C1")
chk('HE2 mediana C2', f"de {f(h2['mediana_x_s'], 2)} s en C2")
chk('HE2 medias', f"media de {f(h2['media_C1_s'], 2)} s; desviación estándar de {f(h2['de_C1_s'], 2)} s")
chk('HE2 medias C2', f"media de {f(h2['media_C2_s'], 2)} s; desviación estándar de {f(h2['de_C2_s'], 2)} s")
chk('HE2 pares', f"en los {h2['n_pares']} incidentes")
chk('HE2 mediana dif', f"{f(h2['mediana_dif_s'], 2)} s (IC 95 %: {f(h2['IC95_mediana_dif_s'][0], 2)} a {f(h2['IC95_mediana_dif_s'][1], 2)})")
chk('HE2 tabla', f"+{f(h2['mediana_dif_s'], 2)} [+{f(h2['IC95_mediana_dif_s'][0], 2)}; +{f(h2['IC95_mediana_dif_s'][1], 2)}]")
chk('HE2 razón', f"{f(h2['razon_medianas'], 1)} veces más")
chk('ET min', f"{f(vd.loc['C1', 'ET_media_min'], 2)} min por incidente en C1 y de {f(vd.loc['C2', 'ET_media_min'], 2)} min en C2")
tot = sum(ta.loc[k, 'media_s'] for k in ('contextualizacion', 'clasificacion', 'priorizacion'))
for k, nom in (('contextualizacion', 'contextualización'), ('clasificacion', 'clasificación'), ('priorizacion', 'priorización')):
    chk(f'tiempo {nom}', f"{f(100 * ta.loc[k, 'media_s'] / tot, 0)} % del tiempo de C2 ({f(ta.loc[k, 'media_s'], 2)} s)" if k == 'contextualizacion'
        else f"{f(100 * ta.loc[k, 'media_s'] / tot, 0)} % ({f(ta.loc[k, 'media_s'], 2)} s)")
# --- H.E.3
chk('HE3 b y c', f"*b* = {h3['b']}, *c* = {h3['c']}")
chk('HE3 TD C2', f"lo son {round(h3['TD_C2'] * con['n_incidentes'])} ({f(100 * h3['TD_C2'])} %)")
chk('HE3 dif IC', f"−{f(-100 * (h3['TD_C2'] - h3['TD_C1']))} [−{f(-100 * h3['IC95_dif_TD'][0])}; −{f(-100 * h3['IC95_dif_TD'][1])}]")
chk('crit C2', f"| {f(vd.loc['C2', 'crit2_%'])} | 900 | {vi.loc['C2', 'corridas_procesadas']} |")
chk('corrección activada', f"{cor['correccion_activada']} de los {cor['corridas_C2']} triajes de C2 ({f(cor['correccion_activada_%'])} %)")
chk('contexto cita historial', f"{cor['contexto_cita_claves_del_historial_corridas']} de los {vi.loc['C2', 'corridas_procesadas']} triajes procesados ({f(cor['contexto_cita_claves_del_historial_%'])} %)")
chk('NP por incidente', f"afectan a {cor['incidentes_con_alguna_corrida_no_procesada']} incidentes: {cor['incidentes_segun_corridas_no_procesadas']['1']} con un triaje no procesado, {cor['incidentes_segun_corridas_no_procesadas']['2']} con dos y {cor['incidentes_segun_corridas_no_procesadas']['3']} con los tres")
# --- sensibilidad (Tabla 10)
for k in (1, 2, 3):
    s = sen[f'H.E.1, corrida {k}']
    chk(f'corrida {k}', f"| Corrida {k} | {s['n']} | {f(100 * s['exactitud_C1'])} | {f(100 * s['exactitud_C2'])} | {s['b']} | {s['c']} | {f(s['p'], 3)} |")
for clave, etiqueta in (('H.E.1, incidentes con decisión no escalada en ambas condiciones', 'Con decisión no escalada en ambas condiciones'),
                        ('H.E.1, incidentes con historial de detector', 'Con historial de detector*')):
    s = sen[clave]
    chk(etiqueta, f"| {etiqueta} | {s['n']} | {f(100 * s['exactitud_C1'])} | {f(100 * s['exactitud_C2'])} | {s['b']} | {s['c']} | {f(s['p'], 3)} |")
for clave, etiqueta in (('H.E.1, incidentes sin corridas no procesadas en C2', 'Sin incidentes con triajes no procesados*'),
                        ('H.E.1, incidentes sin historial de detector', 'Sin historial de detector*')):
    s = sen[clave]
    chk(etiqueta, f"| {etiqueta} | {s['n']} | {f(100 * s['exactitud_C1'])} | {f(100 * s['exactitud_C2'])} | {s['b']} | {s['c']} | < 0,001 |")
    assert s['p'] < 0.001
ic = sen['IC95 dif. exactitud, bootstrap por organización']['ic']
chk('bootstrap por organización', f"({f(100 * ic[0])} a {f(100 * ic[1])} puntos)")
m = pc.groupby('condicion')['PC_%'].agg(['mean', 'std'])
chk('media ± DE por corrida', f"{f(m.loc['C1', 'mean'])} ± {f(m.loc['C1', 'std'])} % en C1 y de {f(m.loc['C2', 'mean'])} ± {f(m.loc['C2', 'std'])} % en C2")
td = pc.pivot(index='corrida', columns='condicion', values='TD_%')
chk('TD por corrida C2', f"({f(td.loc[1, 'C2'])} %, {f(td.loc[2, 'C2'])} % y {f(td.loc[3, 'C2'])} %")
# --- referencias
mr = com['mcnemar_referencias']
chk('C1 vs regla', f"acierta {mr['C1 (un solo LLM) vs Regla del historial']['b']} incidentes que la regla falla y falla {mr['C1 (un solo LLM) vs Regla del historial']['c']}")
chk('C2 vs regla', f"C2, {mr['C2 (multiagente) vs Regla del historial']['b']} y {mr['C2 (multiagente) vs Regla del historial']['c']} (*p* = {f(mr['C2 (multiagente) vs Regla del historial']['p'], 3)})")
chk('C2 vs siempre BP p', f"*p* = {f(mr['C2 (multiagente) vs Siempre BP']['p'], 3)}")
cc = com['coincidencia_de_clase']
chk('coincidencia con la regla', f"en el {f(cc['C2 = regla_%'])} % de los incidentes (kappa de {f(cc['kappa C2-regla'], 2)}), y la de C1, en el {f(cc['C1 = regla_%'])} % (kappa de {f(cc['kappa C1-regla'], 2)})")
# --- subgrupos
g = sg['Con historial de detector']
chk('con historial', f"({f(g['C1_%'])} % y {f(g['C2_%'])} %; *p* = {f(g['mcnemar_C2_vs_C1']['p'], 3)})")
chk('regla con historial', f"({f(g['regla_%'])} %)")
chk('categoría', f"En {cat['clase_mas_frecuente_de_la_categoria']['BP']} de esos {cat['incidentes']} incidentes")
chk('categoría coincide', f"en el {f(cat['C2_coincide_%'])} % de ellos y C1, en el {f(cat['C1_coincide_%'])} %")
chk('categoría exactitud', f"acertaría el {f(cat['exactitud_de_la_clase_de_la_categoria_%'])} %")
# --- confianza y escalamiento
chk('AUC C1', f"área bajo la curva ROC de {f(cf['C1']['AUC_confianza_acierto'], 2)}")
chk('AUC C2', f"(área de {f(cf['C2']['AUC_confianza_acierto'], 2)})")
chk('confianza copiada', f"En el {f(cf['C1']['igual_a_una_tasa_del_historial_%'])} % de los triajes de C1")
chk('escalado C1', f"C1 escaló el {f(esc['C1']['escalados_%'])} % de los incidentes")
chk('no escalados C1', f"acertó el {f(esc['C1']['exactitud_no_escalados_%'])} % de los {esc['C1']['no_escalados_n']} que no escaló, frente al {f(esc['C1']['exactitud_escalados_%'])} % de los escalados")
chk('escalado C2', f"C2 escaló el {f(esc['C2']['escalados_%'])} % y acertó por igual los {esc['C2']['no_escalados_n']} que decidió sin escalar ({f(esc['C2']['exactitud_no_escalados_%'])} %) y los que escaló ({f(esc['C2']['exactitud_escalados_%'])} %)")
chk('TP y escalamiento', f"C1 escaló {esc['C1']['TP_escalados_n']} y cerró {esc['C1']['TP_cerrados_como_BP_o_FP_sin_escalar_n']} como BP o FP sin escalarlos; C2 escaló {esc['C2']['TP_escalados_n']}, cerró {esc['C2']['TP_cerrados_como_BP_o_FP_sin_escalar_n']} sin escalarlos y no procesó {esc['C2']['TP_no_procesados_n']}")
chk('AUC prioridad', f"de {f(esc['C1']['AUC_prioridad_TP_por_corrida'], 2)} en C1 y de {f(esc['C2']['AUC_prioridad_TP_por_corrida'], 2)} en C2")
# --- consistencia y VI (Tabla 11)
chk('AC', f"al {f(co['C1']['unanimes_%'])} % de los incidentes y C2, al {f(co['C2']['unanimes_%'])} % ({f(co['C2']['unanimes_sin_NP_%'])} % en los {co['C2']['incidentes_sin_corridas_NP']} incidentes")
chk('kappa corridas', f"de {f(min(co['C1']['kappa_entre_corridas']), 2)} a {f(max(co['C1']['kappa_entre_corridas']), 2)} en C1 y de {f(min(co['C2']['kappa_entre_corridas']), 2)} a {f(max(co['C2']['kappa_entre_corridas']), 2)} en C2")
chk('SV', f"| {f(vi.loc['C1', 'SV_registrada_%'])} | {f(vi.loc['C2', 'SV_registrada_%'])} |")
chk('SV reconstruida', f"| {f(vi.loc['C1', 'SV_reconstruida_%'])} | {f(vi.loc['C2', 'SV_reconstruida_%'])} |")
chk('TR', f"| {f(vi.loc['C1', 'TR_media_s'], 2)} ({f(vi.loc['C1', 'TR_de_s'], 2)}) | {f(vi.loc['C2', 'TR_media_s'], 2)} ({f(vi.loc['C2', 'TR_de_s'], 2)}) |")
chk('TH', f"| {miles(round(vi.loc['C1', 'TH_inc_h']))} | {miles(round(vi.loc['C2', 'TH_inc_h']))} |")
chk('TK', f"| {miles(vi.loc['C1', 'TK'])} ({miles(vi.loc['C1', 'TK_entrada'])} + {miles(vi.loc['C1', 'TK_salida'])}) | {miles(vi.loc['C2', 'TK'])} ({miles(vi.loc['C2', 'TK_entrada'])} + {miles(vi.loc['C2', 'TK_salida'])}) |")
chk('llamadas', f"| {f(vi.loc['C1', 'llamadas'], 2)} | {f(vi.loc['C2', 'llamadas'], 2)} |")
chk('trazables erradas', f"{tz['C1']['trazables_con_clase_erronea']} de las {tz['C1']['trazables']} decisiones trazables ({f(tz['C1']['%'])} %) justifican una clase equivocada, y en el sistema multiagente, {tz['C2']['trazables_con_clase_erronea']} de {tz['C2']['trazables']} ({f(tz['C2']['%'])} %)")
# --- datos
pob = lim['poblacion_elegible']
chk('población', f"{miles(pob['incidentes'])} incidentes de {miles(pob['organizaciones'])} organizaciones")
for cl, ab in (('BenignPositive', 'BP'), ('FalsePositive', 'FP'), ('TruePositive', 'TP')):
    chk(f'población {ab}', f"{miles(pob['clases'][cl])} {ab} ({f(100 * pob['clases'][cl] / pob['incidentes'])} %)")
chk('duplicados', f"{miles(lim['duplicados'])} filas duplicadas")
chk('sin calificación', f"{miles(lim['incidentes_sin_calificacion'])} incidentes sin calificación")
chk('tamaño de muestra', f"se requieren {mue['n_minimo_mcnemar']} incidentes")
chk('base de conocimiento', f"{miles(exp['alertas_historicas_kb'])} alertas de {miles(exp['incidentes_historicos_kb'])} incidentes")
chk('ejecución', f"{miles(com['ejecucion']['triajes'])} triajes")

mal = [c for c in checks if not c[2]]
print(f'Comprobaciones: {len(checks)}; correctas: {len(checks) - len(mal)}; con diferencias: {len(mal)}')
for nombre, texto, _ in mal:
    print('  FALTA:', nombre, '->', texto)
sys.exit(1 if mal else 0)
