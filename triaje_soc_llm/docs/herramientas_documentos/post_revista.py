"""Post-procesa el docx de pandoc: tablas con bordes, encabezado gris y sin cortes entre páginas, número de sección
separado por tabulación, encabezado de página con numeración y línea, figuras centradas."""
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

src, dst = sys.argv[1], sys.argv[2]
d = Document(src)
ANCHO = 16.25


def bordes(tbl):
    tblPr = tbl._tbl.tblPr
    for v in tblPr.findall(qn('w:tblBorders')):
        tblPr.remove(v)
    b = OxmlElement('w:tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{side}')
        for k, v in (('val', 'single'), ('sz', '4'), ('space', '0'), ('color', '000000')):
            e.set(qn(f'w:{k}'), v)
        b.append(e)
    tblPr.append(b)
    lay = tblPr.find(qn('w:tblLayout')) or OxmlElement('w:tblLayout')
    lay.set(qn('w:type'), 'fixed')
    tblPr.append(lay)


def sombra(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement('w:shd')
    for k, v in (('val', 'clear'), ('color', 'auto'), ('fill', fill)):
        s.set(qn(f'w:{k}'), v)
    tcPr.append(s)


ANCHOS = {1: [2.2, 4.9, 5.2, 3.95], 2: [3.6, 3.6, 4.6, 4.45], 3: [1.4, 8.0, 3.4, 3.45], 4: [2.0, 6.6, 7.65],
          5: [3.6, 2.6, 2.0, 1.2, 1.2, 1.2, 2.3, 2.15], 6: [5.2, 1.7, 3.6, 3.6, 2.15], 7: [2.9] + [1.4833] * 9,
          8: [7.25, 2.4, 2.4, 2.1, 2.1], 9: [1.75, 2.5, 1.25, 1.25, 3.45, 2.7, 1.6, 1.75], 10: [7.6, 1.2, 1.4, 1.4, 1.2, 1.2, 2.25],
          11: [9.0, 3.6, 3.65]}
for num, t in enumerate(d.tables, start=1):
    ncol = len(t.columns)
    largo, palabra = [0] * ncol, [0] * ncol
    for r in t.rows:
        for j, c in enumerate(r.cells[:ncol]):
            largo[j] = max(largo[j], min(len(c.text), 90))
            if c._tc.findall('.//' + qn('m:oMath')):
                largo[j] = max(largo[j], 40)
            for w in c.text.split():
                palabra[j] = max(palabra[j], min(len(w), 16))
    peso = [max(6, l) ** 0.85 for l in largo]
    anchos = [max(1.2, 0.2 * palabra[j] + 0.35, ANCHO * p / sum(peso)) for j, p in enumerate(peso)]
    if num in ANCHOS and len(ANCHOS[num]) == ncol:
        anchos = ANCHOS[num]
    k = ANCHO / sum(anchos)
    anchos = [a * k for a in anchos]
    # un poco de aire entre la tabla y el párrafo que la sigue
    sig = t._tbl.getnext()
    if sig is not None and sig.tag == qn('w:p'):
        from docx.text.paragraph import Paragraph
        Paragraph(sig, t._parent).paragraph_format.space_before = Pt(6)
    bordes(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, gc in enumerate(t._tbl.tblGrid.findall(qn('w:gridCol'))):
        gc.set(qn('w:w'), str(int(Cm(anchos[j]).twips)))
    ultima = len(t.rows) - 1
    for i, r in enumerate(t.rows):
        # Cada tabla se mantiene en una sola página: ninguna fila se parte y cada fila queda unida a la siguiente
        # (Word y LibreOffice unen dos filas cuando los párrafos de la primera tienen «conservar con el siguiente»).
        trPr = r._tr.get_or_add_trPr()
        if trPr.find(qn('w:cantSplit')) is None:
            trPr.append(OxmlElement('w:cantSplit'))
        for j, c in enumerate(r.cells[:ncol]):
            c.width = Cm(anchos[j])
            if i < ultima:
                for p in c.paragraphs:
                    p.paragraph_format.keep_with_next = True
            if i == 0:
                sombra(c, 'D9D9D9')
            for p in c.paragraphs:
                pf = p.paragraph_format
                pf.space_before, pf.space_after, pf.first_line_indent = Pt(1), Pt(1), Cm(0)
                if i == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif p.alignment is None:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.size = Pt(9)
                    run.font.name = 'Times New Roman'

for p in d.paragraphs:
    if p.style.name.startswith('Heading') and p.runs:
        m = re.match(r'^(\d+(?:\.\d+)*) (.*)$', p.text)
        if m:
            primero = p.runs[0]
            primero.text = re.sub(r'^(\d+(?:\.\d+)*) ', r'\1\t', primero.text, count=1)
    if p._p.findall('.//' + qn('w:drawing')):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

# La frase que introduce una fórmula centrada no se separa de ella al cambiar de página
parrafos = d.paragraphs
for k, p in enumerate(parrafos[1:], start=1):
    if p._p.findall('.//' + qn('m:oMathPara')):
        parrafos[k - 1].paragraph_format.keep_with_next = True

# encabezado: número de página a la izquierda, línea inferior
for s in d.sections:
    h = s.header
    h.is_linked_to_previous = False
    p = h.paragraphs[0]
    p.text = ''
    r = p.add_run()
    for tag, txt in (('begin', None), (None, 'PAGE'), ('end', None)):
        if tag:
            f = OxmlElement('w:fldChar')
            f.set(qn('w:fldCharType'), tag)
            r._r.append(f)
        else:
            it = OxmlElement('w:instrText')
            it.set(qn('xml:space'), 'preserve')
            it.text = txt
            r._r.append(it)
    r.font.size = Pt(10)
    r.font.name = 'Times New Roman'
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement('w:pBdr')
    e = OxmlElement('w:bottom')
    for k, v in (('val', 'single'), ('sz', '4'), ('space', '1'), ('color', '000000')):
        e.set(qn(f'w:{k}'), v)
    bdr.append(e)
    pPr.append(bdr)
# propiedades del documento
cp = d.core_properties
cp.author = 'Jorge Luis Berrocal Barrientos; Jhojan Neira Herrera'
cp.last_modified_by = ''
cp.language = 'es-PE'
cp.keywords = 'sistemas multiagente; modelos de lenguaje; triaje de alertas; SOC; trazabilidad'
cp.comments = ''
d.save(dst)
print('ok', len(d.tables), 'tablas')
