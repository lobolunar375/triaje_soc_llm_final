# -*- coding: utf-8 -*-
"""Reordena elementos de WordprocessingML/OMML según el esquema (corrige salidas de pandoc)."""
import re, shutil, zipfile
from lxml import etree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
ORD = {
 (W, 'tblPr'): 'tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc tblCellSpacing tblInd tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription'.split(),
 (W, 'tcPr'): 'cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText vAlign hideMark'.split(),
 (W, 'trPr'): 'cnfStyle divId gridBefore gridAfter wBefore wAfter cantSplit trHeight tblHeader tblCellSpacing jc hidden'.split(),
 (W, 'pPr'): 'pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange'.split(),
 (W, 'rPr'): 'rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof snapToGrid vanish webHidden color spacing w kern position sz szCs highlight u effect bdr shd fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath'.split(),
 (W, 'style'): 'name aliases basedOn next link autoRedefine hidden uiPriority semiHidden unhideWhenUsed qFormat locked personal personalCompose personalReply rsid pPr rPr tblPr trPr tcPr tblStylePr'.split(),
 (M, 'dPr'): 'begChr sepChr endChr grow shp ctrlPr'.split(),
 (M, 'rPr'): 'lit nor scr sty brk aln'.split(),
}


def _reordenar(root):
    for (ns, tag), orden in ORD.items():
        for el in root.iter('{%s}%s' % (ns, tag)):
            kids = list(el)
            def clave(e):
                try:
                    q = ET.QName(e)
                except ValueError:
                    return 999
                return orden.index(q.localname) if q.localname in orden else 998
            kids.sort(key=clave)
            for k in kids:
                el.remove(k)
            for k in kids:
                el.append(k)


def arreglar(path):
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in ('word/document.xml', 'word/styles.xml', 'word/numbering.xml', 'word/comments.xml'):
                root = ET.fromstring(data)
                _reordenar(root)
                if item.filename == 'word/numbering.xml':
                    for el in root.iter('{%s}nsid' % W):
                        v = el.get('{%s}val' % W)
                        if v and len(v) < 8:
                            el.set('{%s}val' % W, v.zfill(8))
                data = ET.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
            zout.writestr(item, data)
    shutil.move(tmp, path)
