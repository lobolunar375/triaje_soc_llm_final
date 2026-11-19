"""Añade a la sistematización el REGISTRO DE OBSERVACIÓN ESTRUCTURADA, después de la matriz de consistencia y antes
de la sección 'Revista', con el formato de la sistematización de referencia, y lo llena con los resultados del
repositorio (results/). También completa los dos campos de la metodología que estaban pendientes de definir (grupo
de control y tamaño de muestra). No cambia el formato ni el resto del contenido.

Uso: python paso2_registro.py <entrada.docx> <salida.docx> <carpeta del repositorio>
"""
import json
import sys
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

SRC, OUT, REPO = sys.argv[1], sys.argv[2], sys.argv[3]
d = Document(SRC)
VERDE = '84E290'
GRIS = 'E7E6E6'
ANCHO = 15.9
ancla = [p for p in d.paragraphs if p.text.strip() == 'Revista' and p.style.name == 'Heading 1'][0]


def leer(*p):
    return f'{REPO}/' + '/'.join(p)


def fmt(n, dec=0):
    """Número con coma decimal y espacio de miles; redondeo aritmético."""
    if isinstance(n, str):
        return n
    q = Decimal(repr(float(n))).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP)
    s = f'{q:,.{dec}f}'
    return s.replace(',', ' ').replace('.', ',')


def signo(n, dec=1):
    return ('+' if n > 0 else ('−' if n < 0 else '')) + fmt(abs(n), dec)


def run_tnr(r, size, bold=False, italic=False):
    r.font.name = 'Times New Roman'
    rpr = r._r.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.insert(0, rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), 'Times New Roman')
    r.font.size = Pt(size)
    r.bold, r.italic = bold, italic


def parrafo(texto, size=11, bold=False, centro=False, antes=6, despues=6, salto=False, italic=False):
    p = ancla.insert_paragraph_before()
    p.style = d.styles['Normal']
    if salto:
        p.add_run().add_break(WD_BREAK.PAGE)
    segs = texto if isinstance(texto, list) else [(texto, bold)]
    for t, b in segs:
        run_tnr(p.add_run(t), size, b, italic)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centro else WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(antes), Pt(despues)
    p.paragraph_format.keep_with_next = bold or centro
    return p


def sombra(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement('w:shd')
    for k, v in (('val', 'clear'), ('color', 'auto'), ('fill', fill)):
        s.set(qn(f'w:{k}'), v)
    tcPr.append(s)


def tabla(filas, anchos, encabezado=True, size=9, filas_grupo=(), negrita_col0=False, repetir_encabezado=False, centrar_desde=None):
    t = d.add_table(rows=len(filas), cols=len(filas[0]))
    ancla._p.addprevious(t._tbl)
    tblPr = t._tbl.tblPr
    b = OxmlElement('w:tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{side}')
        for k, v in (('val', 'single'), ('sz', '4'), ('space', '0'), ('color', '000000')):
            e.set(qn(f'w:{k}'), v)
        b.append(e)
    tblPr.append(b)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    k = ANCHO / sum(anchos)
    anchos = [a * k for a in anchos]
    lay = OxmlElement('w:tblLayout')
    lay.set(qn('w:type'), 'fixed')
    tblPr.append(lay)
    tw = tblPr.find(qn('w:tblW'))
    if tw is None:
        tw = OxmlElement('w:tblW')
        tblPr.append(tw)
    tw.set(qn('w:type'), 'dxa')
    tw.set(qn('w:w'), str(int(Cm(ANCHO).twips)))
    for j, gc in enumerate(t._tbl.tblGrid.findall(qn('w:gridCol'))):
        gc.set(qn('w:w'), str(int(Cm(anchos[j]).twips)))
    for i, (fila_t, fila) in enumerate(zip(t.rows, filas)):
        celdas = fila_t.cells          # una sola lectura por fila: t.cell(i, j) recorre toda la tabla en cada llamada
        for j, val in enumerate(fila):
            c = celdas[j]
            c.width = Cm(anchos[j])
            p = c.paragraphs[0]
            segs = val if isinstance(val, list) else [(str(val), False)]
            for txt, bb in segs:
                run_tnr(p.add_run(txt), size, bb or (encabezado and i == 0) or (negrita_col0 and j == 0) or i in filas_grupo)
            p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(1)
            if encabezado and i == 0:
                sombra(c, VERDE)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif centrar_desde is not None and j >= centrar_desde:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if i in filas_grupo:
                sombra(c, GRIS)
    if repetir_encabezado:
        trPr = t.rows[0]._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:tblHeader'))
    for i in filas_grupo:
        fila = t.rows[i]
        c = fila.cells[0].merge(fila.cells[-1])
        for q in c.paragraphs[1:]:
            q._p.getparent().remove(q._p)
    parrafo('', 4, antes=0, despues=0)
    return t


# ----------------------------------------------------------------------------- campos pendientes de la metodología
REEMPLAZOS = {
    'Línea base de triaje [definir: clasificador de ML o un solo LLM sin agentes].':
        'Línea base de triaje: un solo LLM sin agentes (C1), con el mismo modelo, el mismo expediente y las mismas herramientas que el sistema multiagente.',
    'n = Z²·p·q / e², con 95 % de confianza y 5 % de error: n ≈ 385. Ajustable según el costo de ejecutar los LLM [completar n definitivo].':
        'n = Z²·p·q / e², con 95 % de confianza y 5 % de error: n ≈ 385. Ajustado según el costo de ejecutar los LLM: n = 375 incidentes '
        '(75 de desarrollo y 300 de evaluación); los 300 de evaluación superan el mínimo de 259 que requiere la prueba de McNemar.',
    'Tamaño de muestra n por calcular': 'Tamaño de muestra: n = 375 incidentes (75 de desarrollo y 300 de evaluación)',
    ' Ajustar por el costo de ejecutar los LLM.': ' Ajustado por el costo de ejecutar los LLM.',
}
hechos = set()
for t in d.element.body.iter(qn('w:t')):
    if t.text in REEMPLAZOS:
        hechos.add(t.text)
        t.text = REEMPLAZOS[t.text]
assert len(hechos) == len(REEMPLAZOS), f'campos no encontrados: {set(REEMPLAZOS) - hechos}'

# ----------------------------------------------------------------------------- datos del repositorio
emb = pd.read_csv(leer('results', 'limpieza', 'embudo_limpieza.csv'))
rep = json.load(open(leer('results', 'limpieza', 'reporte_limpieza.json'), encoding='utf-8'))
dec = pd.read_csv(leer('results', 'limpieza', 'decisiones_columnas.csv'))
comp = pd.read_csv(leer('results', 'muestra', 'composicion_muestra.csv'))
rmu = json.load(open(leer('results', 'muestra', 'resumen_muestra.json'), encoding='utf-8'))
rexp = json.load(open(leer('results', 'expedientes', 'resumen_expedientes.json'), encoding='utf-8'))
con = json.load(open(leer('results', 'estadistica', 'contrastes.json'), encoding='utf-8'))
com = json.load(open(leer('results', 'estadistica', 'complementario.json'), encoding='utf-8'))
reg = pd.read_csv(leer('results', 'metricas', 'registro_observacion.csv'))
agg = pd.read_csv(leer('results', 'metricas', 'registro_incidente.csv'))
vd = pd.read_csv(leer('results', 'metricas', 'indicadores_vd.csv')).set_index('condicion')
vi = pd.read_csv(leer('results', 'metricas', 'indicadores_vi.csv')).set_index('condicion')
mu = pd.read_csv(leer('data', 'processed', 'muestra.csv'))
EJ = 'INC-0141'
exp = json.load(open(leer('data', 'processed', 'expedientes', f'{EJ}.json'), encoding='utf-8'))
ej = mu[mu.incidente == EJ].iloc[0]
C = comp.set_index('conjunto')
pob = rep['poblacion_elegible']
D = com['desempeno']
rg, d1, d2 = D['Regla del historial'], D['C1 (un solo LLM)'], D['C2 (multiagente)']
h1, h2, h3 = con['HE1'], con['HE2'], con['HE3']
dec_h = con['decisiones']
eje = com['ejecucion']
CORTO = {'TruePositive': 'TP', 'BenignPositive': 'BP', 'FalsePositive': 'FP', 'NP': 'NP'}
acepta = lambda h: 'se acepta' if dec_h[h]['se_acepta'] else 'no se acepta'
fp = lambda p: f'p = {fmt(p, 3)}' if p >= 0.001 else 'p < 0,001'

# ----------------------------------------------------------------------------- título y ficha técnica
parrafo('REGISTRO DE OBSERVACIÓN ESTRUCTURADA', 13, True, True, salto=True)
parrafo('FICHA TÉCNICA DEL INSTRUMENTO DE INVESTIGACIÓN', 11, True, True)
tabla([
    ['Campo', 'Descripción'],
    ['Variable evaluada', 'Variable dependiente: rendimiento del triaje de alertas de seguridad (cuantitativa, escala de razón), en tres dimensiones: precisión de clasificación, eficiencia temporal del triaje y trazabilidad de las decisiones. Los indicadores de la variable independiente (sistema multiagente basado en modelos largos de lenguaje) se registran en el «Registro global de la variable independiente».'],
    ['Objetivo del instrumento', 'Medir y comparar, para cada incidente, el rendimiento del triaje sin el sistema multiagente (pre-test: línea base de un solo LLM, C1) y con el sistema multiagente (post-test: C2).'],
    ['Diseño metodológico', 'Cuantitativo, aplicado, correlacional-causal, cuasi-experimental, transversal y de medidas pareadas: cada incidente se procesa en las dos condiciones.'],
    ['Técnica e instrumento', 'Observación estructurada mediante experimentación computacional (simulación sobre el dataset GUIDE) y minería de datos; registro de observación estructurada automatizado.'],
    ['Herramientas de registro', 'Programas en Python del repositorio del estudio (DuckDB, pandas, scikit-learn, SciPy y statsmodels), que guardan cada triaje y exportan el registro a CSV; API de OpenAI para consultar el modelo de lenguaje.'],
    ['Unidad de análisis / observación', 'Incidente del dataset GUIDE (Microsoft): conjunto de alertas y evidencias con una calificación de triaje asignada por el analista del cliente (TP, BP o FP).'],
    ['Población y muestra', f'{fmt(pob["incidentes"])} incidentes elegibles de {fmt(pob["organizaciones"])} organizaciones del archivo GUIDE_Train.csv. Muestreo aleatorio simple con partición por organización: {fmt(int(C.loc["Desarrollo"].incidentes))} incidentes de desarrollo y {fmt(int(C.loc["Evaluación"].incidentes))} de evaluación (de {fmt(int(C.loc["Evaluación"].organizaciones))} organizaciones).'],
    ['Condiciones comparadas', 'C1 (pre-test, control): un solo LLM con el mismo expediente y las mismas herramientas. C2 (post-test, experimental): sistema multiagente (orquestador, contextualización, clasificación, priorización y trazabilidad). Referencias sin LLM: regla del historial de los detectores y asignación de la clase mayoritaria (BP).'],
    ['Parámetros fijos', 'Modelo GPT-4o mini (identificador gpt-4o-mini, API de OpenAI), temperatura 0,2, top-p 1,0 y 600 tokens de salida; R = 3 corridas (semillas 1, 2 y 3); hasta 3 reintentos por esquema; umbral de escalamiento: confianza < 0,60; semilla de partición y muestreo: 42.'],
    ['Aplicación', f'5 de noviembre de 2026, de {eje["inicio"][11:16]} a {eje["fin"][11:16]} h: {fmt(eje["triajes"])} triajes (300 incidentes × 2 condiciones × 3 corridas), todos con la huella de configuración {eje["huella_configuracion"][0]}.'],
    ['Aplicadores', 'Registro automático de los programas del estudio. Responsables: Berrocal Barrientos, Jorge Luis; Neira Herrera, Jhojan.'],
], [4.2, 11.7], negrita_col0=True)

# ----------------------------------------------------------------------------- preparación de los datos
parrafo('REGISTRO DE PREPARACIÓN DE LOS DATOS (SCRIPTS 00 A 04)', 11, True, True)
parrafo('Instrucciones de llenado: cada fila corresponde a un paso del tratamiento del dataset. La columna Resultado se llena con la salida del script (archivos de results/exploracion, results/limpieza, results/muestra y results/expedientes del repositorio).', 9.5, italic=True)
e = {r.etapa[:1]: r for r in emb.itertuples()}
cent = rep['centinelas']
tabla([
    ['Paso', 'Acción', 'Justificación', 'Resultado'],
    ['1. Descarga e integridad', 'Descarga del zip de Kaggle y cálculo del SHA-256 de cada archivo.', 'Permite verificar que una réplica usa los mismos datos.', 'GUIDE_Train.csv: 2,43 GB (población del estudio); GUIDE_Test.csv: 1,09 GB (no se usa).'],
    ['2. Exploración', 'Perfil de las 45 columnas: nulos, cardinalidad, tipo de valor y V de Cramér con la etiqueta.', 'Identifica qué columnas puede interpretar un LLM y cuáles filtran la etiqueta.', f'{fmt(int(e["0"].evidencias))} evidencias, 1 265 644 alertas, {fmt(int(e["0"].incidentes))} incidentes y 5 769 organizaciones.'],
    ['3. Duplicados', 'Eliminación de filas duplicadas exactas.', 'Una evidencia repetida infla los conteos del incidente.', f'{fmt(rep["duplicados"])} filas eliminadas (0,24 %).'],
    ['4. Valores centinela', 'En las 13 columnas de entidades, el código presente en más del 50 % de las filas se trata como nulo.', 'Ese código representa «sin entidad» en el archivo seudonimizado.', f'Ejemplos: DeviceId {fmt(cent["DeviceId"]["pct_filas"], 1)} %, IpAddress {fmt(cent["IpAddress"]["pct_filas"], 1)} %, AccountUpn {fmt(cent["AccountUpn"]["pct_filas"], 1)} %.'],
    ['5. Marca de tiempo', 'Conversión de Timestamp a fecha y hora.', 'Ordena las alertas y mide la duración del incidente.', '0 marcas inválidas.'],
    ['6. Etiqueta', 'Exclusión de incidentes sin calificación o con más de una.', 'Sin verdad terreno no se mide la precisión.', f'{fmt(rep["incidentes_sin_calificacion"])} sin calificación; 0 con calificación múltiple; quedan {fmt(int(e["3"].incidentes))}.'],
    ['7. Tamaño', 'Exclusión de incidentes con más de 50 alertas.', 'El expediente detalla solo 25 alertas y no representaría el incidente; se aplica antes del muestreo.', f'{fmt(rep["incidentes_excluidos_tamano"])} excluidos; población elegible: {fmt(pob["incidentes"])} incidentes y {fmt(pob["organizaciones"])} organizaciones.'],
    ['8. Partición', 'Asignación aleatoria de organizaciones a desarrollo (20 %) y evaluación (80 %).', 'Evita la fuga de información entre conjuntos.', f'{fmt(rmu["organizaciones_desarrollo"])} organizaciones de desarrollo ({fmt(rmu["incidentes_por_grupo"]["desarrollo"])} incidentes) y {fmt(rmu["organizaciones_evaluacion"])} de evaluación ({fmt(rmu["incidentes_por_grupo"]["evaluacion"])}).'],
    ['9. Muestreo', 'Muestreo aleatorio simple sin usar la etiqueta; tamaño calculado para la prueba de McNemar.', f'n mínimo de {rmu["n_minimo_mcnemar"]} (δ = 0,10; ψ = 0,25; α = 0,05/3; potencia 0,80).', '75 incidentes de desarrollo y 300 de evaluación.'],
    ['10. Base de conocimiento', 'Tasas de TP, BP y FP por detector, título y categoría, con las organizaciones de desarrollo que no aportan incidentes a la muestra.', 'Aporta la experiencia previa sin información de las organizaciones evaluadas.', f'{fmt(rexp["alertas_historicas_kb"])} alertas calificadas; {rexp["codigos_kb_con_soporte"]["detector"]} detectores y {rexp["codigos_kb_con_soporte"]["titulo"]} títulos con al menos 20 alertas.'],
    ['11. Expedientes', 'JSON por incidente con alertas, evidencias agrupadas e identificadores citables, más MITRE ATT&CK e historial.', 'Entrada común de C1 y C2; permite verificar las evidencias citadas.', f'375 expedientes; mediana de {round(rexp["tokens_estimados"]["50%"])} tokens y máximo de {fmt(rexp["tokens_estimados"]["max"])}; 216 de los 300 incidentes de evaluación tienen un detector con historial.'],
], [2.6, 4.6, 4.2, 4.5], size=8.5)

# ----------------------------------------------------------------------------- selección de características
parrafo('REGISTRO DE SELECCIÓN DE CARACTERÍSTICAS DEL DATASET', 11, True, True)
parrafo('Cada columna de GUIDE recibió un rol según si su contenido es interpretable por un modelo de lenguaje, si puede resumirse o si filtra la etiqueta. La evidencia se obtuvo con el script 01 (perfil de columnas) y el 02 (verificación de supuestos).', 9.5, italic=True)
nombre_rol = {'entrada': 'Entrada (llega al expediente)', 'historial': 'Historial (código + tasas históricas)', 'clave': 'Clave (agrupación y partición)',
              'conteo': 'Conteo (n.º de entidades distintas)', 'etiqueta': 'Etiqueta (solo métricas)', 'eliminada': 'Eliminada'}
just_rol = {'entrada': 'Texto con significado para el LLM.', 'historial': 'Códigos sin significado, pero su historial de calificaciones es la experiencia que usa un analista.',
            'clave': 'Agrupan evidencias en alertas e incidentes y definen la partición; no se muestran al modelo.',
            'conteo': 'Identificadores seudonimizados; solo aporta cuántas entidades distintas involucra el incidente.',
            'etiqueta': 'Verdad terreno; nunca se muestra a los agentes.',
            'eliminada': 'Fuga de la etiqueta (acciones de remediación), casi vacías, redundantes o códigos sin significado.'}
filas = [['Rol', 'Columnas', 'Justificación', 'Evidencia empírica (nulos; V de Cramér)']]
for rol in ('entrada', 'historial', 'clave', 'conteo', 'etiqueta', 'eliminada'):
    g = dec[dec.rol == rol]
    evid = '; '.join(f'{r.columna}: {fmt(r.pct_nulos, 1)} %; V = {fmt(r.v_cramer_etiqueta, 2) if pd.notna(r.v_cramer_etiqueta) else "—"}' for r in g.itertuples()
                     if rol in ('entrada', 'historial', 'clave', 'etiqueta') or r.columna in ('ActionGrouped', 'ActionGranular', 'ThreatFamily', 'ResourceType', 'Roles', 'EmailClusterId', 'AntispamDirection'))
    if rol == 'conteo':
        evid = 'Valor dominante = ausencia de entidad en ' + ', '.join(f'{r.columna} ({fmt(r.pct_centinela, 1)} %)' for r in g.itertuples() if pd.notna(r.pct_centinela))
    filas.append([nombre_rol[rol], ', '.join(g.columna), just_rol[rol], evid])
tabla(filas, [2.6, 4.4, 4.0, 4.9], size=8)

# ----------------------------------------------------------------------------- composición de la muestra
parrafo('REGISTRO DE LA COMPOSICIÓN DE LA MUESTRA', 11, True, True)
filas = [['Conjunto', 'Organizaciones', 'Incidentes', 'TP (%)', 'BP (%)', 'FP (%)', 'p (χ²) frente a la población', 'p (χ²) frente a su grupo']]
nombres = {'Población elegible': 'Población elegible', 'Grupo de organizaciones de desarrollo': 'Grupo de organizaciones de desarrollo',
           'Grupo de organizaciones de evaluación': 'Grupo de organizaciones de evaluación', 'Desarrollo': 'Muestra de desarrollo', 'Evaluación': 'Muestra de evaluación'}
for r in comp.itertuples():
    if r.conjunto not in nombres:
        continue
    tp, bp_, fp_ = r.TruePositive, r.BenignPositive, r.FalsePositive
    if r.conjunto == 'Población elegible':   # con los conteos exactos, para que el redondeo coincida con el del artículo
        tp, bp_, fp_ = (100 * pob['clases'][k] / pob['incidentes'] for k in ('TruePositive', 'BenignPositive', 'FalsePositive'))
    filas.append([nombres[r.conjunto], fmt(int(r.organizaciones)), fmt(int(r.incidentes)), fmt(tp, 1), fmt(bp_, 1),
                  fmt(fp_, 1), '—' if pd.isna(r.p_chi2) else fmt(r.p_chi2, 3), '—' if pd.isna(r.p_chi2_grupo) else fmt(r.p_chi2_grupo, 3)])
tabla(filas, [4.2, 2.1, 1.9, 1.3, 1.3, 1.3, 1.9, 1.9], centrar_desde=1)

# ----------------------------------------------------------------------------- matriz por incidente (ejemplo lleno)
parrafo('MATRIZ DEL REGISTRO DE OBSERVACIÓN ESTRUCTURADA (PRE-TEST VS. POST-TEST)', 11, True, True, salto=True)
parrafo(f'Instrucciones de llenado: esta ficha se aplica individualmente a cada incidente del conjunto de evaluación. En la columna Pre-test se registran las métricas del triaje sin sistema multiagente (línea base de un solo LLM, C1) y en la columna Post-test, las del sistema multiagente (C2). La clase es la moda de las tres corridas, los indicadores binarios se asignan por mayoría y el tiempo, las llamadas y los tokens son la mediana de las corridas. La clase real se copia del dataset al final y nunca se muestra a los agentes. Los valores provienen de results/metricas/registro_observacion.csv (una fila por incidente, condición y corrida) y registro_incidente.csv. Se muestra el incidente {EJ}; el registro de los 300 incidentes se presenta más abajo.', 9.5, italic=True)
tecs = ', '.join(f'{t["tecnica"]} ({t["nombre"]})' for t in exp['herramientas']['mitre'])
tabla([
    ['Código del incidente:', EJ, 'Organización (OrgId):', str(ej.OrgId)],
    ['N.º de alertas / evidencias:', f'{exp["resumen"]["alertas"]} / {exp["resumen"]["evidencias"]}', 'Clase real (IncidentGrade):', 'FP (FalsePositive)'],
    ['Categoría / técnicas MITRE:', f'Exfiltration / {tecs}', 'Corridas / semillas:', '3 / 1, 2 y 3'],
    ['Responsables:', 'Berrocal Barrientos, Jorge Luis; Neira Herrera, Jhojan', 'Fecha de aplicación:', '5 de noviembre de 2026'],
], [3.6, 4.4, 3.6, 4.3], encabezado=False, size=8.5)
a1 = agg[(agg.incidente == EJ) & (agg.condicion == 'C1')].iloc[0]
a2 = agg[(agg.incidente == EJ) & (agg.condicion == 'C2')].iloc[0]
r1 = reg[(reg.incidente == EJ) & (reg.condicion == 'C1')]
r2 = reg[(reg.incidente == EJ) & (reg.condicion == 'C2')]
PRI = {4: 'P1', 3: 'P2', 2: 'P3', 1: 'P4'}
sn = lambda v: 'sí' if v else 'no'


def var(x1, x2, dec=1):
    return signo(100 * (x2 - x1) / x1, dec) if x1 else '—'


filas = [['Dimensión / indicador observado', 'PRE-TEST (C1: un solo LLM)', 'POST-TEST (C2: multiagente)', 'DIFERENCIA (Δ C2 − C1)', 'VARIACIÓN RELATIVA (%)'],
         ['DIMENSIÓN 1: PRECISIÓN DE CLASIFICACIÓN', '', '', '', ''],
         ['• Clase asignada (TP / BP / FP)', CORTO[a1.clase_asignada], CORTO[a2.clase_asignada], '—', '—'],
         ['• Acierto (1 = coincide con la clase real)', int(a1.acierto), int(a2.acierto), signo(a2.acierto - a1.acierto, 0) or '0', '—'],
         ['• Omisión de amenaza (1 = TP real asignado a BP o FP)', int(a1.omision_amenaza), int(a2.omision_amenaza), '0', '—'],
         ['• Corridas con la misma clase (de 3)', int(r1.clase_asignada.value_counts().iloc[0]), int(r2.clase_asignada.value_counts().iloc[0]), '0', '—'],
         ['• Confianza declarada (0-1), media de las corridas', fmt(a1.confianza, 2), fmt(a2.confianza, 2), signo(a2.confianza - a1.confianza, 2), var(a1.confianza, a2.confianza)],
         ['• Prioridad (P1-P4) / escalamiento', f'{PRI[int(a1.puntaje_prioridad)]} / {sn(a1.escalado)}', f'{PRI[int(a2.puntaje_prioridad)]} / {sn(a2.escalado)}', '—', '—'],
         ['DIMENSIÓN 2: EFICIENCIA TEMPORAL DEL TRIAJE', '', '', '', ''],
         ['• Tiempo de triaje tᵢ (s)', fmt(a1.t_total_s, 2), fmt(a2.t_total_s, 2), signo(a2.t_total_s - a1.t_total_s, 2), var(a1.t_total_s, a2.t_total_s)],
         ['• Tiempo de triaje tᵢ (min)', fmt(a1.t_total_s / 60, 3), fmt(a2.t_total_s / 60, 3), signo((a2.t_total_s - a1.t_total_s) / 60, 3), var(a1.t_total_s, a2.t_total_s)],
         ['• Tiempo por agente (s): contextualización / clasificación / priorización', '—',
          f'{fmt(r2.t_contextualizacion_s.mean(), 2)} / {fmt(r2.t_clasificacion_s.mean(), 2)} / {fmt(r2.t_priorizacion_s.mean(), 2)}', '—', '—'],
         ['• Llamadas al modelo', int(a1.llamadas), int(a2.llamadas), signo(a2.llamadas - a1.llamadas, 0), var(a1.llamadas, a2.llamadas)],
         ['• Tokens (entrada + salida)', fmt(a1.tokens), fmt(a2.tokens), signo(a2.tokens - a1.tokens, 0), var(a1.tokens, a2.tokens)],
         ['DIMENSIÓN 3: TRAZABILIDAD DE LAS DECISIONES', '', '', '', ''],
         ['• Criterio 1: justificación de al menos 20 palabras que nombra la clase (1/0)', int(a1.crit1), int(a2.crit1), '0', '—'],
         ['• Criterio 2: cita al menos una evidencia (1/0)', int(a1.crit2), int(a2.crit2), '0', '—'],
         ['• Criterio 3: todas las evidencias citadas son verificables (1/0)', int(a1.crit3), int(a2.crit3), '0', '—'],
         ['• Decisión trazable Tᵢ (criterios 1 a 3)', int(a1.trazable), int(a2.trazable), '0', '—'],
         ['• Evidencias citadas / no verificables (n.º)', f'{int(a1.ev_citadas)} / {int(a1.ev_no_verificables)}', f'{int(a2.ev_citadas)} / {int(a2.ev_no_verificables)}', '—', '—'],
         ['• Triajes no procesados (de 3)', int(a1.corridas_no_procesadas), int(a2.corridas_no_procesadas), '0', '—']]
filas = [[str(c) for c in f] for f in filas]
tabla(filas, [6.3, 2.3, 2.4, 2.4, 2.5], size=8, filas_grupo=(1, 8, 14), centrar_desde=1)
hist = exp['herramientas']['historial']
cat = hist.get('categoria Exfiltration', {})
parrafo([('Nota. ', True), (f'En el incidente {EJ} ninguna condición acierta: el analista del cliente lo calificó como FP, el LLM único lo asignó a TP y el sistema multiagente, a BP. El detector del incidente no tiene historial suficiente en las organizaciones de desarrollo; la categoría Exfiltration registra {fmt(cat.get("TP_%", 0), 1)} % de TP, {fmt(cat.get("BP_%", 0), 1)} % de BP y {fmt(cat.get("FP_%", 0), 1)} % de FP en {fmt(cat.get("alertas_calificadas", 0))} alertas calificadas, y la regla del historial asigna BP. Ambas decisiones son trazables y ambas escalan el incidente. «—»: no aplica.', False)], 9)

# ----------------------------------------------------------------------------- registro por incidente (300)
parrafo('REGISTRO CONSOLIDADO POR INCIDENTE (CONJUNTO DE EVALUACIÓN, n = 300)', 11, True, True, antes=12)
parrafo('Una fila por incidente. Clase: moda de las tres corridas (NP: no procesado en al menos dos corridas). Ac.: acierto (1/0). t: tiempo de triaje en segundos (mediana de las corridas procesadas). T: decisión trazable (1/0). Esc.: escalado a revisión humana (1/0). Fuente: results/metricas/registro_incidente.csv; el detalle por corrida (1 800 filas) está en results/metricas/registro_observacion.csv.', 9, italic=True)
c1 = agg[agg.condicion == 'C1'].set_index('incidente')
c2 = agg[agg.condicion == 'C2'].set_index('incidente')
filas = [['N.º', 'Incidente', 'Clase real', 'C1: clase', 'C1: Ac.', 'C1: t (s)', 'C1: T', 'C1: Esc.', 'C2: clase', 'C2: Ac.', 'C2: t (s)', 'C2: T', 'C2: Esc.']]
for k, inc in enumerate(sorted(c1.index), start=1):
    x, y = c1.loc[inc], c2.loc[inc]
    filas.append([k, inc, CORTO[x.clase_real], CORTO[x.clase_asignada], int(x.acierto), fmt(x.t_total_s, 2), int(x.trazable), int(x.escalado),
                  CORTO[y.clase_asignada], int(y.acierto), '—' if pd.isna(y.t_total_s) else fmt(y.t_total_s, 2), int(y.trazable), int(y.escalado)])
filas.append(['', 'Total / media', '', '', int(c1.acierto.sum()), fmt(c1.t_total_s.mean(), 2), int(c1.trazable.sum()), int(c1.escalado.sum()),
              '', int(c2.acierto.sum()), fmt(c2.t_total_s.mean(), 2), int(c2.trazable.sum()), int(c2.escalado.sum())])
filas = [[str(c) for c in f] for f in filas]
tabla(filas, [0.9, 1.9, 1.4, 1.3, 1.0, 1.3, 0.8, 1.0, 1.3, 1.0, 1.3, 0.8, 1.0], size=7.5, repetir_encabezado=True, centrar_desde=0)

# ----------------------------------------------------------------------------- registro global de la VI
parrafo('REGISTRO GLOBAL DE LOS INDICADORES DE LA VARIABLE INDEPENDIENTE', 11, True, True, salto=True)
v1, v2 = vi.loc['C1'], vi.loc['C2']
co, cor, esc = com['consistencia'], com['correccion'], com['escalamiento']


def nivel3(v, bajo, alto, mayor=True):
    if mayor:
        return 'Bajo' if v < bajo else ('Alto' if v > alto else 'Medio')
    return 'Bajo' if v > bajo else ('Alto' if v < alto else 'Medio')


tabla([['Dimensión / indicador', 'C1: un solo LLM (referencia)', 'C2: multiagente', 'Índice alcanzado (C2)', 'Observación'],
       ['1. PRECISIÓN DEL SISTEMA MULTIAGENTE', '', '', '', ''],
       ['• Salidas válidas al esquema, SV (%)', fmt(v1['SV_registrada_%'], 1), f'{fmt(v2["SV_registrada_%"], 1)} ({fmt(v2["SV_reconstruida_%"], 1)} con los triajes no procesados)',
        f'{nivel3(v2["SV_registrada_%"], 90, 98)} ({nivel3(v2["SV_reconstruida_%"], 90, 98)} con los no procesados)', f'Las {cor["correcciones_fallidas_no_procesadas"]} correcciones fallidas emitieron la confianza en escala porcentual.'],
       ['• Evidencias verificables, EV (%)', fmt(v1['EV_%'], 1), fmt(v2['EV_%'], 1), nivel3(v2['EV_%'], 90, 98), 'Ningún identificador inventado en las decisiones finales.'],
       ['• Acuerdo entre corridas, AC (%)', fmt(v1['AC_%'], 1), fmt(v2['AC_%'], 1), nivel3(v2['AC_%'], 80, 95), f'C1 alcanza el nivel {nivel3(v1["AC_%"], 80, 95).lower()}; C2 es menos estable.'],
       ['2. EFICIENCIA TEMPORAL DE RESPUESTA', '', '', '', ''],
       ['• Tiempo medio de respuesta, TR (s)', fmt(v1['TR_media_s'], 2), fmt(v2['TR_media_s'], 2), nivel3(v2['TR_media_s'], 300, 60, False), 'C2 tarda 3,2 veces más que C1.'],
       ['• Reintentos por incidente, RI', fmt(v1['RI'], 3), fmt(v2['RI'], 3), nivel3(v2['RI'], 0.5, 0.1, False), 'Sin contar los reintentos de los triajes no procesados.'],
       ['3. CAPACIDAD DE PROCESAMIENTO (THROUGHPUT)', '', '', '', ''],
       ['• Incidentes por hora, TH', fmt(round(v1['TH_inc_h'])), fmt(round(v2['TH_inc_h'])), nivel3(v2['TH_inc_h'], 12, 60), 'Ejecución secuencial.'],
       ['• Tokens por incidente, TK', fmt(v1['TK']), fmt(v2['TK']), 'Bajo consumo (óptimo)' if v2['TK'] < 8000 else ('Medio' if v2['TK'] <= 20000 else 'Alto consumo'), 'C2 usa 2,9 veces más tokens y 3 llamadas por incidente.'],
       ['INDICADORES COMPLEMENTARIOS', '', '', '', ''],
       ['• Triajes no procesados (%)', fmt(v1['no_procesadas_%'], 1), fmt(v2['no_procesadas_%'], 1), '—', f'{cor["correcciones_fallidas_no_procesadas"]} de 900 triajes de C2, en {cor["incidentes_con_alguna_corrida_no_procesada"]} incidentes.'],
       ['• Tasa de escalamiento a revisión humana (%)', fmt(esc['C1']['escalados_%'], 1), fmt(esc['C2']['escalados_%'], 1), '—', f'Exactitud de lo no escalado: {fmt(esc["C1"]["exactitud_no_escalados_%"], 1)} % (C1) y {fmt(esc["C2"]["exactitud_no_escalados_%"], 1)} % (C2).'],
       ['• Correcciones solicitadas por trazabilidad (%)', '—', fmt(cor['correccion_activada_%'], 1), '—', f'{cor["correccion_activada"]} activaciones: {cor["correcciones_concluidas"]} concluidas y {cor["correcciones_fallidas_no_procesadas"]} fallidas.'],
       ['• AUC de la confianza frente al acierto', fmt(com['confianza']['C1']['AUC_confianza_acierto'], 2), fmt(com['confianza']['C2']['AUC_confianza_acierto'], 2), '—', 'La confianza de C2 no distingue aciertos de errores.'],
       ['• AUC de la prioridad frente a la clase TP', fmt(esc['C1']['AUC_prioridad_TP_por_corrida'], 2), fmt(esc['C2']['AUC_prioridad_TP_por_corrida'], 2), '—', 'La prioridad no separa los TP en ninguna condición.']],
      [5.0, 2.2, 2.6, 2.6, 3.5], size=8, filas_grupo=(1, 5, 8, 11))

# ----------------------------------------------------------------------------- totales consolidados
parrafo('TOTALES CONSOLIDADOS DE LA MUESTRA DE EVALUACIÓN (VARIABLE DEPENDIENTE)', 11, True, True, salto=True)
ic = lambda v: f'[{signo(100 * v[0], 1)}; {signo(100 * v[1], 1)}]'
tabla([['Indicador', 'Referencia sin LLM (regla del historial)', 'PRE-TEST C1 (n = 300)', 'POST-TEST C2 (n = 300)', 'Diferencia C2 − C1 [IC 95 %]', 'Prueba / p (Holm)', 'Decisión'],
       ['1. Exactitud, PC (%)', fmt(rg['exactitud_%'], 1), fmt(d1['exactitud_%'], 1), fmt(d2['exactitud_%'], 1),
        f'{signo(d2["exactitud_%"] - d1["exactitud_%"], 1)} {ic(h1["IC95_dif_exactitud"])}', f'McNemar (b = {h1["b"]}, c = {h1["c"]}); {fp(h1["p_holm"])}', f'H.E.1: {acepta("HE1")}'],
       ['1. F1 macro (%)', fmt(rg['F1_macro_%'], 1), fmt(d1['F1_macro_%'], 1), fmt(d2['F1_macro_%'], 1),
        f'{signo(d2["F1_macro_%"] - d1["F1_macro_%"], 1)} {ic(h1["IC95_dif_f1"])}', 'IC 95 % por bootstrap', 'Favorable a C2'],
       ['1. Omisión de amenazas, TOA (%)', fmt(rg['TOA_%'], 1), fmt(d1['TOA_%'], 1), fmt(d2['TOA_%'], 1), signo(d2['TOA_%'] - d1['TOA_%'], 1), '—', 'Descriptivo'],
       ['2. Tiempo por incidente, ET (s, mediana)', '—', fmt(h2['mediana_y_s'], 2), fmt(h2['mediana_x_s'], 2),
        f'{signo(h2["mediana_dif_s"], 2)} [{signo(h2["IC95_mediana_dif_s"][0], 2)}; {signo(h2["IC95_mediana_dif_s"][1], 2)}]', f'Wilcoxon (r = {signo(h2["r_rb"], 2)}); {fp(h2["p_holm"])}', f'H.E.2: {acepta("HE2")}'],
       ['2. Tiempo medio por incidente, ET (min)', '—', fmt(vd.loc['C1', 'ET_media_min'], 2), fmt(vd.loc['C2', 'ET_media_min'], 2),
        signo(vd.loc['C2', 'ET_media_min'] - vd.loc['C1', 'ET_media_min'], 2), '—', 'Descriptivo'],
       ['3. Decisiones trazables, TD (%)', '—', fmt(100 * h3['TD_C1'], 1), fmt(100 * h3['TD_C2'], 1),
        f'{signo(100 * (h3["TD_C2"] - h3["TD_C1"]), 1)} {ic(h3["IC95_dif_TD"])}', f'McNemar mid-p (b = {h3["b"]}, c = {h3["c"]}); {fp(h3["p_holm"])}', f'H.E.3: {acepta("HE3")}'],
       ['Nivel según la matriz: PC / ET / TD', '—', f'{vd.loc["C1", "nivel_PC"]} / {vd.loc["C1", "nivel_ET"]} / {vd.loc["C1", "nivel_TD"]}',
        f'{vd.loc["C2", "nivel_PC"]} / {vd.loc["C2", "nivel_ET"]} / {vd.loc["C2", "nivel_TD"]}', 'Sin cambio de nivel', '—', 'Descriptivo']],
      [3.4, 2.0, 1.7, 1.7, 2.7, 2.7, 1.7], size=8)
parrafo([('Hipótesis general: ', True), (f'{dec_h["HG"]}. Solo H.E.1 se acepta: el sistema multiagente mejora la precisión de clasificación respecto de un solo LLM, pero tarda más y produce menos decisiones trazables. Una hipótesis se acepta si su valor p con la corrección de Holm es menor que 0,05 y el efecto tiene la dirección planteada. Ambas condiciones quedan por debajo de la regla del historial (exactitud del {fmt(rg["exactitud_%"], 1)} %).', False)], 9.5)

# ----------------------------------------------------------------------------- protocolo
parrafo('PROTOCOLO METODOLÓGICO', 11, True, True)
pasos = [
    ('1. Preparación de los datos: ', 'descarga de GUIDE desde Kaggle (licencia CDLA-Permissive-2.0) y verificación SHA-256; exploración del archivo GUIDE_Train.csv; eliminación de duplicados; tratamiento de valores centinela; exclusión de incidentes sin calificación o con más de 50 alertas; selección de características; partición por organización y muestreo aleatorio simple; construcción de la base de conocimiento y de los expedientes (scripts 00 a 04).'),
    ('2. Piloto y congelación: ', 'piloto de funcionamiento con cinco incidentes de desarrollo (16 triajes) para comprobar la integración con el modelo; los prompts no se modificaron y la configuración quedó registrada con una huella SHA-256 de prompts, esquemas y parámetros antes de procesar el conjunto de evaluación.'),
    ('3. Fase pre-test (línea de base): ', 'triaje de los 300 incidentes de evaluación con un solo LLM, en tres corridas (C1, script 05).'),
    ('4. Aplicación del estímulo (tratamiento): ', 'ejecución del sistema multiagente (orquestador, contextualización, clasificación, priorización y trazabilidad) sobre los mismos 300 incidentes, en tres corridas intercaladas con C1 por incidente y en orden aleatorio (C2, script 05).'),
    ('5. Fase post-test: ', 'cálculo de los indicadores de la VD y de la VI y llenado automático del registro (script 07).'),
    ('6. Análisis: ', 'McNemar (H.E.1 y H.E.3), Wilcoxon (H.E.2), corrección de Holm, intervalos por bootstrap y análisis de sensibilidad (script 08); análisis complementario frente a las reglas de referencia, por subgrupos, de la confianza y del ciclo de corrección (script 10); figuras y tablas (script 09).'),
]
for a, b in pasos:
    parrafo([(a, True), (b, False)], 10, antes=2, despues=2)
d.save(OUT)
print('ok', OUT)
