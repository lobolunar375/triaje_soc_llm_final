"""Prueba de humo del código (no produce resultados del estudio).

Copia el repositorio a una carpeta temporal y ejecuta los pasos 05, 07, 08, 10 y 09 con el backend 'simulado',
que genera salidas JSON válidas al azar en lugar de llamar a un modelo. Sirve para comprobar que los scripts
funcionan de punta a punta antes de lanzar las corridas reales. Requiere haber ejecutado antes los pasos 00 a 04
(o disponer de data/processed, que sí se versiona). Las salidas de esta prueba se borran al terminar.

Uso: python tests/prueba_humo.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def correr(dir_, script, *args):
    r = subprocess.run([sys.executable, str(dir_ / 'src' / script), *args], cwd=dir_ / 'src', capture_output=True, text=True)
    print(f'{script}: {"OK" if r.returncode == 0 else "FALLÓ"}')
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        sys.exit(1)


def main():
    tmp = Path(tempfile.mkdtemp(prefix='humo_'))
    for d in ('src', 'config'):
        shutil.copytree(RAIZ / d, tmp / d, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(RAIZ / 'data' / 'processed', tmp / 'data' / 'processed')
    shutil.copytree(RAIZ / 'results', tmp / 'results', ignore=shutil.ignore_patterns('corridas', 'metricas', 'estadistica', 'auditoria'))
    correr(tmp, '05_triaje_llm.py', '--backend', 'simulado', '--limite', '60')
    correr(tmp, '07_calcular_metricas.py')
    correr(tmp, '08_analisis_estadistico.py')
    correr(tmp, '10_analisis_complementario.py')
    correr(tmp, '09_figuras_tablas.py')
    print('Prueba de humo superada.')
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
