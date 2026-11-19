# Herramientas de los documentos

Scripts con los que se generan el artículo y la sistematización a partir de los resultados del repositorio.

| Archivo | Qué hace |
|:--|:--|
| `paper.md` | Fuente del artículo (Markdown con fórmulas), con las referencias [1] a [20] |
| `build.sh` | Construye `docs/curso/Paper_Triaje_SOC_Multiagente_LLM.docx` y `.pdf` con el formato de la revista y verifica las cifras |
| `mkref_revista.py` | Plantilla de estilos según las pautas de *Inteligencia Artificial* (A4, Times New Roman de 10 pt, títulos numerados, bloque de título) |
| `tipografia.py` | Espacios de no separación en miles, porcentajes, unidades y rótulos (Tabla 2, Figura 3) |
| `post_revista.py` | Bordes y anchos de las tablas, tablas sin cortes entre páginas, numeración de títulos, figuras centradas y encabezado de página |
| `exportar_pdf.py` | Exporta el PDF con LibreOffice y ajusta las fórmulas al tamaño del texto (10 pt; 9 pt en tablas) |
| `docx_fix.py` | Ordena los elementos del Word según su esquema para que abra sin avisos |
| `verificar_cifras.py` | Recalcula 114 cifras desde `results/` y comprueba que aparecen en el artículo |
| `paso1_vi.py` | Añade a la sistematización la matriz de operacionalización de la variable independiente |
| `paso2_registro.py` | Añade a la sistematización el registro de observación estructurada y lo llena con `results/` |
| `generar_trazabilidad.py` | Genera `docs/trazabilidad.md`, `docs/Matriz_trazabilidad_paper.xlsx` y `fuentes/manifest_fuentes.csv` |

```bash
bash docs/herramientas_documentos/build.sh
python docs/herramientas_documentos/verificar_cifras.py docs/herramientas_documentos/paper.md .
python docs/herramientas_documentos/generar_trazabilidad.py
# sistematización: se aplica sobre el documento original (sin el registro)
python docs/herramientas_documentos/paso1_vi.py sistematizacion.docx s1.docx
python docs/herramientas_documentos/paso2_registro.py s1.docx Sistematizacion_v3.docx .
```
