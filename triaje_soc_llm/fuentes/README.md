# Fuentes del artículo

Esta carpeta reúne las referencias del artículo. Los PDF no se versionan; se obtienen así:

```bash
python fuentes/descargar_fuentes.py
```

El script lee `manifest_fuentes.csv` (código, cita, nombre de archivo, dirección directa del PDF cuando existe,
enlace de la referencia y tipo de acceso), descarga los PDF de acceso abierto que tienen dirección directa y
escribe en `pendientes_descarga_manual.csv` las referencias que deben descargarse a mano desde su enlace, con el
nombre de archivo indicado.

Los enlaces de las referencias [1] a [18], el del conjunto de datos [19] y el del artículo modelo de la revista
[20] son los de la sistematización (`docs/curso/Sistematizacion_v3.docx`). La correspondencia entre cada sección
del artículo, sus referencias y los archivos del repositorio está en `docs/trazabilidad.md` y en
`docs/Matriz_trazabilidad_paper.xlsx`.
