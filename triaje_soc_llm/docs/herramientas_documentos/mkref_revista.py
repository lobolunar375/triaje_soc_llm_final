"""Plantilla de estilos según las pautas de Inteligencia Artificial (IBERAMIA) y su artículo de ejemplo:
A4; márgenes 3,0 cm (izq.) y 1,75 cm (der.); Times New Roman 10 pt a espacio sencillo, justificado;
sangría de primera línea de 0,5 cm salvo tras un encabezado; títulos 14/12/10 pt en negrita; título 16 pt;
leyendas de 10 pt centradas; referencias numeradas con sangría francesa; estilos del bloque de título
(título en inglés, autores, afiliación y resumen)."""
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

d = Document('ref0.docx')
ST = {s.name: s for s in d.styles}
NEGRO = RGBColor(0, 0, 0)


def fuente(st, size, bold=None, italic=None):
    st.font.name = 'Times New Roman'
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.insert(0, rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), 'Times New Roman')
    for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:cstheme', 'w:eastAsiaTheme'):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    st.font.size = Pt(size)
    st.font.color.rgb = NEGRO
    if bold is not None:
        st.font.bold = bold
    if italic is not None:
        st.font.italic = italic


def parrafo(st, antes=0, despues=0, sangria=None, alin=WD_ALIGN_PARAGRAPH.JUSTIFY):
    pf = st.paragraph_format
    pf.space_before, pf.space_after = Pt(antes), Pt(despues)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.alignment = alin
    if sangria is not None:
        pf.first_line_indent = Cm(sangria)


for n in ('Normal', 'Body Text', 'First Paragraph', 'Compact', 'Block Text'):
    if n in ST:
        fuente(ST[n], 10)
        parrafo(ST[n])
ST['Body Text'].paragraph_format.first_line_indent = Cm(0.5)
ST['First Paragraph'].paragraph_format.first_line_indent = Cm(0)
ST['Compact'].paragraph_format.space_after = Pt(1)
for n, sz, a, b_ in (('Heading 1', 14, 12, 6), ('Heading 2', 12, 9, 5), ('Heading 3', 10, 6, 3)):
    fuente(ST[n], sz, True, False)
    parrafo(ST[n], a, b_, 0, WD_ALIGN_PARAGRAPH.LEFT)
    ST[n].paragraph_format.keep_with_next = True
    ppr = ST[n].element.get_or_add_pPr()
    tabs = OxmlElement('w:tabs')
    tab = OxmlElement('w:tab')
    tab.set(qn('w:val'), 'left')
    tab.set(qn('w:pos'), str(int(Cm(1.0).twips)))
    tabs.append(tab)
    ppr.append(tabs)
fuente(ST['Title'], 16, True, False)
parrafo(ST['Title'], 6, 18, 0, WD_ALIGN_PARAGRAPH.LEFT)
for n in ('Table Caption', 'Image Caption', 'Caption'):
    if n in ST:
        fuente(ST[n], 10, False, False)
        parrafo(ST[n], 6, 6, 0, WD_ALIGN_PARAGRAPH.CENTER)
        ST[n].paragraph_format.keep_with_next = n == 'Table Caption'
if 'Captioned Figure' in ST:
    parrafo(ST['Captioned Figure'], 6, 0, 0, WD_ALIGN_PARAGRAPH.CENTER)
try:
    ref = d.styles['Reference']
except KeyError:
    ref = d.styles.add_style('Reference', WD_STYLE_TYPE.PARAGRAPH)
ref.base_style = ST['Normal']
fuente(ref, 10)
parrafo(ref, 0, 4, None)
ref.paragraph_format.left_indent = Cm(0.55)
ref.paragraph_format.first_line_indent = Cm(-0.55)
for s in d.sections:
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.left_margin, s.right_margin = Cm(3.0), Cm(1.75)
    s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.5)
    s.header_distance, s.footer_distance = Cm(1.6), Cm(1.4)
# ---------------------------------------------------------------- estilos del bloque de título


def estilo(nombre, size, bold=False, italic=False, antes=0, despues=0, alin=WD_ALIGN_PARAGRAPH.LEFT):
    try:
        st = d.styles[nombre]
    except KeyError:
        st = d.styles.add_style(nombre, WD_STYLE_TYPE.PARAGRAPH)
    st.base_style = d.styles['Normal']
    st.font.name = 'Times New Roman'
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), 'Times New Roman')
    st.font.size = Pt(size); st.font.bold = bold; st.font.italic = italic
    st.font.color.rgb = RGBColor(0, 0, 0)
    pf = st.paragraph_format
    pf.space_before, pf.space_after = Pt(antes), Pt(despues)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.alignment = alin
    pf.first_line_indent = Cm(0)
    return st


estilo('TitleEN', 12, bold=True, italic=True, antes=0, despues=12)
estilo('Authorname', 12, antes=0, despues=8)
estilo('Authoraffiliation', 9, antes=0, despues=14)
estilo('Abstract', 10, antes=0, despues=10, alin=WD_ALIGN_PARAGRAPH.JUSTIFY)
# el título: menos espacio posterior porque le sigue el título en inglés
d.styles['Title'].paragraph_format.space_after = Pt(6)
d.styles['Title'].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
# hipervínculos en negro subrayado discreto
if 'Hyperlink' in [s.name for s in d.styles]:
    d.styles['Hyperlink'].font.color.rgb = RGBColor(0, 0, 0)
d.styles['Reference'].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
d.save('ref_revista.docx')
print('estilos de portada ok')

