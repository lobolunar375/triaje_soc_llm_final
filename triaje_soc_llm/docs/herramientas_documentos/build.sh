#!/usr/bin/env bash
# Construye el artículo (Word y PDF) a partir de paper.md con el formato de la revista Inteligencia Artificial.
# Requiere pandoc, LibreOffice (soffice, con python3-uno para ajustar las fórmulas del PDF) y python-docx.
# Uso: bash docs/herramientas_documentos/build.sh
set -e
cd "$(dirname "$0")"
SALIDA=../curso/Paper_Triaje_SOC_Multiagente_LLM
pandoc -o ref0.docx --print-default-data-file reference.docx      # plantilla base de pandoc
python3 mkref_revista.py                                           # estilos de la revista -> ref_revista.docx
python3 tipografia.py paper.md _paper.md                           # espacios de no separación
pandoc _paper.md -f markdown+tex_math_dollars -o _raw.docx --reference-doc=ref_revista.docx --resource-path=../../results/figuras
python3 post_revista.py _raw.docx "$SALIDA.docx"                   # tablas, encabezado y figuras
python3 -c "from docx_fix import arreglar; arreglar('$SALIDA.docx')"
# PDF con las fórmulas al tamaño del texto; si falta el puente de Python de LibreOffice, conversión directa
python3 exportar_pdf.py "$SALIDA.docx" "$SALIDA.pdf" || soffice --headless --convert-to pdf --outdir ../curso "$SALIDA.docx" >/dev/null 2>&1
python3 verificar_cifras.py paper.md ../..                         # las cifras del texto coinciden con results/
for f in ref0.docx ref_revista.docx _paper.md _raw.docx; do [ -f "$f" ] && rm "$f"; done
echo "Artículo generado en docs/curso/"
