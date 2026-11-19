"""Funciones comunes: rutas, configuración, registro detallado (verbose) y utilidades de E/S.

Cada script del pipeline usa `Bitacora` para imprimir en pantalla y guardar en logs/ lo que hace
en cada paso y por qué lo hace. Así el registro de la ejecución sirve también como documentación
del tratamiento de los datos.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]


def cargar_config(ruta: str | Path | None = None) -> dict:
    ruta = Path(ruta) if ruta else RAIZ / 'config' / 'config.yaml'
    with open(ruta, encoding='utf-8') as f:
        return yaml.safe_load(f)


def ruta(*partes: str) -> Path:
    p = RAIZ.joinpath(*partes)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


class Bitacora:
    """Registro verboso: cada paso dice QUÉ se hace y POR QUÉ, y guarda una copia en logs/."""

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.t0 = time.time()
        self.n = 0
        archivo = ruta('logs', f'{nombre}.log')
        self.log = logging.getLogger(nombre)
        self.log.setLevel(logging.INFO)
        self.log.handlers.clear()
        fmt = logging.Formatter('%(message)s')
        for h in (logging.StreamHandler(sys.stdout), logging.FileHandler(archivo, mode='w', encoding='utf-8')):
            h.setFormatter(fmt)
            self.log.addHandler(h)
        self.log.info('=' * 100)
        self.log.info(f'{nombre}  |  inicio {time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.log.info('=' * 100)

    def paso(self, titulo: str, porque: str = ''):
        self.n += 1
        self.log.info('')
        self.log.info(f'[PASO {self.n}] {titulo}')
        if porque:
            self.log.info(f'  Por qué: {porque}')

    def info(self, msg: str):
        self.log.info(f'  {msg}')

    def tabla(self, df, max_filas: int = 30):
        texto = df.head(max_filas).to_string()
        for linea in texto.splitlines():
            self.log.info(f'    {linea}')

    def fin(self):
        self.log.info('')
        self.log.info(f'Fin de {self.nombre}: {time.time() - self.t0:.1f} s')


def guardar_json(obj, archivo: Path):
    archivo.parent.mkdir(parents=True, exist_ok=True)
    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)


def leer_json(archivo: Path):
    with open(archivo, encoding='utf-8') as f:
        return json.load(f)


def pct(a, b) -> float:
    return round(100.0 * a / b, 2) if b else 0.0
