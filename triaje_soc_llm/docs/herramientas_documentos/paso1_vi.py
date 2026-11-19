"""Añade a la sistematización la matriz de operacionalización de la VI con el mismo formato que la de la VD.

Copia la tabla de la VD (mismos estilos, bordes, anchos y celdas combinadas), la inserta debajo de ella
con su título y reemplaza el contenido de las celdas. No modifica nada del contenido existente.
"""
import copy
import sys

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.text.run import Run

SRC, OUT = sys.argv[1], sys.argv[2]
d = Document(SRC)
GRAY = WD_COLOR_INDEX.GRAY_25

vd = d.tables[0]
assert vd.rows[1].cells[0].text.startswith('VARIABLE DEPENDIENTE')
tit = [p for p in d.paragraphs if p.text.strip() == 'MATRIZ DE OPERACIONALIZACIÓN DE VARIABLES'][0]

# título de la nueva matriz: copia del título existente, con salto de página antes
sep = copy.deepcopy(tit._p)
ppr = sep.find(qn('w:pPr'))
if ppr is None:
    ppr = OxmlElement('w:pPr')
    sep.insert(0, ppr)
if ppr.find(qn('w:pageBreakBefore')) is None:
    ppr.insert(0, OxmlElement('w:pageBreakBefore'))
runs = sep.findall(qn('w:r'))
for r in runs[1:]:
    sep.remove(r)
for t in runs[0].findall(qn('w:t'))[1:]:
    runs[0].remove(t)
runs[0].find(qn('w:t')).text = 'MATRIZ DE OPERACIONALIZACIÓN DE VARIABLES (VARIABLE INDEPENDIENTE)'
for lr in runs[0].findall(qn('w:lastRenderedPageBreak')):
    runs[0].remove(lr)

nuevo = copy.deepcopy(vd._tbl)
vd._tbl.addnext(sep)
sep.addnext(nuevo)
vi = Table(nuevo, vd._parent)

# plantillas de run por tipo de texto, tomadas de la tabla de la VD
R_TIT_VAR = vd.rows[1].cells[0].paragraphs[0].runs[0]._r           # 8 pt negrita
R_DEF = vd.rows[1].cells[1].paragraphs[0].runs[0]._r               # 7,5 pt
R_DIM = vd.rows[1].cells[3].paragraphs[0].runs[0]._r               # 7,5 pt negrita
R_IND = vd.rows[1].cells[4].paragraphs[0].runs[0]._r               # 7 pt negrita
R_IDX = vd.rows[1].cells[5].paragraphs[0].runs[0]._r               # 6,5 pt
R_OPD = [r for p in vd.rows[1].cells[2].paragraphs for r in p.runs]  # dim. (7,5 negrita) y texto (7 pt)
R_OP_T, R_OP_X = R_OPD[0]._r, R_OPD[1]._r


def llenar(tc, parrafos, tpl):
    """parrafos: lista de (segmentos, plantilla); segmentos = [(texto, estilos)] con estilos en {'b','i','g'}."""
    cell = _Cell(tc, vi)
    ps = cell.paragraphs
    tpl_p = copy.deepcopy(ps[0]._p)
    for p in ps:
        p._p.getparent().remove(p._p)
    for segs in parrafos:
        if isinstance(segs, tuple):
            segs, rt = segs
        else:
            rt = tpl
        np_ = copy.deepcopy(tpl_p)
        for r in np_.findall(qn('w:r')):
            np_.remove(r)
        tc.append(np_)
        par = Paragraph(np_, cell)
        for txt, est in segs:
            nr = copy.deepcopy(rt)
            for t in nr.findall(qn('w:t')):
                nr.remove(t)
            np_.append(nr)
            run = Run(nr, par)
            run.text = txt
            run.bold = 'b' in est
            run.italic = 'i' in est
            run.font.highlight_color = GRAY if 'g' in est else None


r1, r2, r3 = (vi.rows[k]._tr.tc_lst for k in (1, 2, 3))
VI = 'Sistema multiagente basado en modelos largos de lenguaje (LLM)'

llenar(r1[0], [[('VARIABLE INDEPENDIENTE (VI): ', 'b'), (VI, 'bg')]], R_TIT_VAR)
llenar(r1[1], [[('Arquitectura de agentes de software especializados, cada uno impulsado por un modelo de lenguaje, '
                 'que cooperan bajo un orquestador, intercambian salidas estructuradas y consultan herramientas '
                 'externas para resolver una tarea compleja por etapas (Simões et al., 2026; Ismail et al., 2025). El ', ''),
                ('sistema multiagente basado en modelos largos de lenguaje', 'g'),
                (' ejecuta el triaje mediante agentes de contextualización, clasificación, priorización y trazabilidad, '
                 'con razonamiento aumentado con herramientas (Kumar & Khan, 2025).', '')]], R_DEF)
llenar(r1[2], [([('1. Precisión del sistema multiagente', 'b')], R_OP_T),
               ([('Grado en que las salidas de los agentes cumplen el esquema estructurado exigido, citan solo evidencias '
                  'presentes en el incidente y se mantienen estables entre corridas repetidas del modelo '
                  '(Rieger et al., 2026; Schärmer et al., 2026).', '')], R_OP_X),
               ([('2. Eficiencia temporal de respuesta', 'b')], R_OP_T),
               ([('Tiempo de cómputo que el sistema necesita para emitir la decisión de triaje de un incidente y número de '
                  'reintentos que exige el orquestador para obtener salidas válidas (Kumar & Khan, 2025).', '')], R_OP_X),
               ([('3. Capacidad de procesamiento (throughput)', 'b')], R_OP_T),
               ([('Volumen de incidentes que el sistema procesa por unidad de tiempo y carga de inferencia que demanda '
                  'cada incidente, en la misma infraestructura (Ismail et al., 2025).', '')], R_OP_X)], R_OP_X)
llenar(r1[3], [[('1. Precisión del sistema multiagente', 'b')]], R_DIM)
llenar(r2[3], [[('2. Eficiencia temporal de respuesta', 'b')]], R_DIM)
llenar(r3[3], [[('3. Capacidad de procesamiento (throughput)', 'b')]], R_DIM)
llenar(r1[4], [([('Tasa de salidas válidas (SV, %)', 'b')], R_IND),
               ([('SV = Salidas que cumplen el esquema / Salidas generadas × 100', 'i')], R_IND),
               ([('Tasa de evidencias verificables (EV, %)', 'b')], R_IND),
               ([('EV = Evidencias citadas presentes en el incidente / Evidencias citadas × 100', 'i')], R_IND),
               ([('Acuerdo entre corridas (AC, %)', 'b')], R_IND),
               ([('AC = Incidentes con la misma clase en las R corridas / N × 100', 'i')], R_IND)], R_IND)
llenar(r2[4], [([('Tiempo medio de respuesta por incidente (TR, s)', 'b')], R_IND),
               ([('TR = Σ tiempo de cómputo de los agentes / N', 'i')], R_IND),
               ([('Reintentos por incidente (RI)', 'b')], R_IND),
               ([('RI = Reintentos por esquema inválido / N', 'i')], R_IND)], R_IND)
llenar(r3[4], [([('Incidentes procesados por hora (TH)', 'b')], R_IND),
               ([('TH = 3 600 · N / Tiempo total de procesamiento (s)', 'i')], R_IND),
               ([('Tokens procesados por incidente (TK)', 'b')], R_IND),
               ([('TK = Σ (tokens de entrada + tokens de salida) / N', 'i')], R_IND)], R_IND)
llenar(r1[5], [[('SV:', 'b')], [('• Bajo (Deficiente): < 90 %.', '')], [('• Medio (Aceptable): 90 % – 98 %.', '')],
               [('• Alto (Óptimo): > 98 %.', '')],
               [('EV:', 'b')], [('• Bajo (Deficiente): < 90 %.', '')], [('• Medio (Aceptable): 90 % – 98 %.', '')],
               [('• Alto (Óptimo): > 98 %.', '')],
               [('AC:', 'b')], [('• Bajo (Inestable): < 80 %.', '')], [('• Medio (Aceptable): 80 % – 95 %.', '')],
               [('• Alto (Estable): > 95 %.', '')]], R_IDX)
llenar(r2[5], [[('TR:', 'b')], [('• Bajo (Lento): > 300 s (más de 5 min por incidente).', '')],
               [('• Medio (Aceptable): 60 – 300 s.', '')], [('• Alto (Óptimo): < 60 s.', '')],
               [('RI:', 'b')], [('• Bajo (Inestable): > 0,5.', '')], [('• Medio (Aceptable): 0,1 – 0,5.', '')],
               [('• Alto (Óptimo): < 0,1.', '')]], R_IDX)
llenar(r3[5], [[('TH:', 'b')], [('• Bajo: < 12 incidentes/h (equivale a más de 5 min por incidente).', '')],
               [('• Medio: 12 – 60 incidentes/h.', '')], [('• Alto (Óptimo): > 60 incidentes/h.', '')],
               [('TK:', 'b')], [('• Alto consumo: > 20 000 tokens/incidente.', '')],
               [('• Medio: 8 000 – 20 000 tokens/incidente.', '')], [('• Bajo consumo (Óptimo): < 8 000 tokens/incidente.', '')]], R_IDX)
llenar(r1[6], [[('Razón', '')]], R_DEF)
d.save(OUT)
print('ok', OUT)
