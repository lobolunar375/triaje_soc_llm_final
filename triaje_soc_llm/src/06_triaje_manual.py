"""Paso 06 (extensión, no ejecutada en el estudio). Formulario de triaje manual (condición C0) en la terminal.

El estudio publicado compara las dos condiciones automáticas (C1 y C2). Este formulario permite añadir, en un
trabajo posterior, una referencia de triaje manual medida con analistas; sus datos deben provenir siempre de
personas que realicen el triaje, nunca de una simulación.

Uso:
    python src/06_triaje_manual.py --analista A      # o B
    python src/06_triaje_manual.py --analista A --entrenamiento   # 5 incidentes de desarrollo para practicar

Qué hace y por qué:
  * Reparte al azar (semilla fija) los 40 incidentes de la submuestra C0: 20 para el analista A y 20 para el
    B, y además 5 del otro analista para cada uno, que solo sirven para estimar el acuerdo entre analistas.
  * Muestra el mismo expediente y las mismas salidas de herramientas que reciben C1 y C2, nunca la etiqueta
    ni las salidas automáticas.
  * Registra la hora de apertura y de envío: el tiempo de triaje es la diferencia entre ambas.
  * Pide clase, confianza, prioridad, escalamiento, justificación y evidencias citadas, con el mismo formato
    que las condiciones automáticas, para que la trazabilidad se mida igual en las tres condiciones.
  * Es reanudable: cada respuesta se guarda al enviarla.
Límite: 30 minutos por incidente (se avisa, y se registra el tiempo real).
"""
import argparse
import json
import random
import time

import pandas as pd

from comunes import RAIZ, cargar_config, ruta


def asignacion(cfg):
    mu = pd.read_csv(ruta('data', 'processed', 'muestra.csv'))
    c0 = sorted(mu[mu.submuestra_c0].incidente)
    rnd = random.Random(cfg['semilla'] + 10)
    rnd.shuffle(c0)
    mitad = len(c0) // 2
    a, b_ = c0[:mitad], c0[mitad:]
    cruz_a, cruz_b = rnd.sample(b_, 5), rnd.sample(a, 5)
    return {'A': [(i, 'principal') for i in a] + [(i, 'acuerdo') for i in cruz_a],
            'B': [(i, 'principal') for i in b_] + [(i, 'acuerdo') for i in cruz_b]}


def mostrar(exp):
    r = exp['resumen']
    print('\n' + '=' * 90)
    print(f"INCIDENTE {exp['incidente']}: {r['alertas']} alertas, {r['evidencias']} evidencias, "
          f"duración {r['duracion_min']} min, {r['detectores_distintos']} detectores")
    print(f"Categorías: {r['categorias']}   Entidades distintas: {r['entidades_distintas']}")
    for a in exp['alertas']:
        print(f"\n  [{a['id']}] minuto {a['minuto']}  {a['detector']} / {a['titulo']}  categoría={a['categoria']}  técnicas={a['tecnicas']}")
        for e in a['evidencias']:
            extra = ' '.join(f'{k}={e[k]}' for k in ('sospecha', 'veredicto') if k in e)
            print(f"      ({e['id']}) {e['tipo']} rol={e['rol']} n={e['n']} {extra}")
    if 'alertas_resumidas' in exp:
        print(f"\n  Alertas adicionales resumidas: {exp['alertas_resumidas']}")
    print('\n  HERRAMIENTA MITRE ATT&CK:')
    for t in exp['herramientas']['mitre']:
        print(f"      {t['tecnica']}: {t['nombre']} ({t.get('tacticas', '')})")
    print('  HERRAMIENTA HISTORIAL (otras organizaciones):')
    for k, v in exp['herramientas']['historial'].items():
        print(f'      {k}: {v}')
    print('=' * 90)


def preguntar(texto, validos=None, tipo=str):
    while True:
        v = input(f'{texto}: ').strip()
        try:
            v = tipo(v)
        except ValueError:
            continue
        if validos is None or v in validos:
            return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--analista', required=True, choices=['A', 'B'])
    ap.add_argument('--entrenamiento', action='store_true')
    a = ap.parse_args()
    cfg = cargar_config()
    if a.entrenamiento:
        mu = pd.read_csv(ruta('data', 'processed', 'muestra.csv'))
        lista = [(i, 'entrenamiento') for i in sorted(mu[mu.conjunto == 'desarrollo'].incidente)[:5]]
        arch = ruta('results', 'corridas', f'manual_entrenamiento_{a.analista}.jsonl')
    else:
        lista = asignacion(cfg)[a.analista]
        arch = ruta('results', 'corridas', 'corridas_manual.jsonl')
    hechos = set()
    if arch.exists():
        for l in arch.read_text(encoding='utf-8').splitlines():
            r = json.loads(l)
            hechos.add((r['incidente'], r['analista']))
    pend = [x for x in lista if (x[0], a.analista) not in hechos]
    print(f'Analista {a.analista}: {len(lista) - len(pend)} hechos, {len(pend)} pendientes.')
    for inc, uso in pend:
        exp = json.loads((RAIZ / 'data' / 'processed' / 'expedientes' / f'{inc}.json').read_text(encoding='utf-8'))
        input(f'\nPulse Enter para abrir {inc} (el tiempo empieza a correr)...')
        t0 = time.time()
        mostrar(exp)
        clase = preguntar('Clase [TP/BP/FP]', {'TP', 'BP', 'FP'}, str.upper)
        conf = preguntar('Confianza [0-1]', None, float)
        prio = preguntar('Prioridad [P1-P4]', {'P1', 'P2', 'P3', 'P4'}, str.upper)
        esc = preguntar('¿Escalar al nivel 2? [s/n]', {'s', 'n'}, str.lower) == 's'
        just = preguntar('Justificación (una línea, nombre la clase)')
        evid = [e.strip() for e in preguntar('Evidencias citadas (ids separados por comas, p. ej. A1,A1-E2)').split(',') if e.strip()]
        t = time.time() - t0
        if t > 1800:
            print('Aviso: se superó el límite de 30 minutos; se registra el tiempo real.')
        r = {'incidente': inc, 'condicion': 'C0', 'semilla': 1, 'analista': a.analista, 'uso': uso, 'clase': clase,
             'confianza': conf, 'prioridad': prio, 'escalado': esc, 'justificacion': just, 'evidencias': evid,
             't_total_s': round(t, 1), 'no_procesado': False, 'fecha': time.strftime('%Y-%m-%d %H:%M:%S')}
        with open(arch, 'a', encoding='utf-8') as f:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(f'Guardado ({t / 60:.1f} min).')


if __name__ == '__main__':
    main()
