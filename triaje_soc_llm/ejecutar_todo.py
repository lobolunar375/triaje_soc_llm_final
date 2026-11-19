"""Ejecuta el pipeline en orden. Uso:
    python ejecutar_todo.py                 # pasos 00 a 04 y 09 (preparación de los datos, sin LLM)
    python ejecutar_todo.py --con-llm       # además 05 (C1 y C2; requiere LLM_API_KEY u Ollama), 07, 08, 10 y 09
    python ejecutar_todo.py --analisis      # solo 07, 08, 10 y 09 sobre las corridas ya guardadas en results/corridas
    python ejecutar_todo.py --desde 3       # retoma desde el paso 03
"""
import argparse
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / 'src'
PREP = ['00_descargar_datos.py', '01_explorar_dataset.py', '02_limpiar_datos.py', '03_muestrear_particionar.py',
        '04_construir_expedientes.py']
ANALISIS = ['07_calcular_metricas.py', '08_analisis_estadistico.py', '10_analisis_complementario.py']

ap = argparse.ArgumentParser()
ap.add_argument('--con-llm', action='store_true')
ap.add_argument('--analisis', action='store_true')
ap.add_argument('--desde', type=int, default=0)
a = ap.parse_args()
if a.analisis:
    pasos = ANALISIS + ['09_figuras_tablas.py']
else:
    pasos = PREP + (['05_triaje_llm.py'] + ANALISIS if a.con_llm else []) + ['09_figuras_tablas.py']
for p in pasos:
    if not a.analisis and int(p[:2]) < a.desde:
        continue
    print(f'\n>>> {p}')
    r = subprocess.run([sys.executable, str(SRC / p)], cwd=SRC)
    if r.returncode:
        sys.exit(f'Falló {p}')
