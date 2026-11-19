"""Paso 07b (extensión, no ejecutada en el estudio). Consolida la auditoría ciega del criterio 4 de
trazabilidad (coherencia entre la justificación, las evidencias y la clase), que requiere revisores humanos.

Flujo:
  1. 07_calcular_metricas.py --plantilla-auditoria genera results/auditoria/plantilla_auditoria.csv (decisiones
     mezcladas, sin condición).
  2. Cada revisor llena, de forma independiente, sus columnas con 1 o 0:
       explica_clase_X: ¿la justificación explica la clase asignada?
       sostiene_clase_X: ¿las evidencias citadas sostienen la clase?
  3. Este script calcula crit4_A y crit4_B (1 si ambas respuestas son 1), el kappa de Cohen entre revisores y
     el consenso. Las discrepancias se listan en discrepancias.csv para resolverlas en una reunión; el valor
     acordado se escribe en la columna crit4_consenso de ese archivo y se vuelve a ejecutar este script.
  4. Guarda results/auditoria/auditoria_trazabilidad.csv, que lee 07_calcular_metricas.py.
"""
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from comunes import Bitacora, guardar_json, ruta


def main():
    b = Bitacora('07b_consolidar_auditoria')
    p = pd.read_csv(ruta('results', 'auditoria', 'plantilla_auditoria.csv'))
    clave = pd.read_csv(ruta('results', 'auditoria', 'clave_auditoria_NO_ABRIR.csv'))
    for r in 'AB':
        p[f'crit4_{r}'] = (p[f'explica_clase_{r}'] * p[f'sostiene_clase_{r}']).astype('Int64')
    llenas = p.dropna(subset=['crit4_A', 'crit4_B'])
    k = cohen_kappa_score(llenas.crit4_A, llenas.crit4_B) if len(llenas) else None
    b.info(f'Decisiones revisadas por ambos: {len(llenas)}. Kappa de Cohen: {k}')
    p['crit4_consenso'] = p.crit4_A.where(p.crit4_A == p.crit4_B)
    disc = ruta('results', 'auditoria', 'discrepancias.csv')
    if disc.exists():
        acordadas = pd.read_csv(disc).dropna(subset=['crit4_consenso']).set_index('decision').crit4_consenso
        p.loc[p.decision.isin(acordadas.index), 'crit4_consenso'] = p.decision.map(acordadas)
    else:
        p[p.crit4_A != p.crit4_B][['decision', 'clase', 'justificacion', 'evidencias', 'crit4_A', 'crit4_B']] \
            .assign(crit4_consenso='').to_csv(disc, index=False)
    out = p.merge(clave, on=['decision', 'incidente'])
    out[['decision', 'incidente', 'condicion', 'crit4_A', 'crit4_B', 'crit4_consenso']].to_csv(
        ruta('results', 'auditoria', 'auditoria_trazabilidad.csv'), index=False)
    guardar_json({'n_revisadas': len(llenas), 'kappa_revisores': k,
                  'discrepancias': int((p.crit4_A != p.crit4_B).sum())}, ruta('results', 'auditoria', 'resumen_auditoria.json'))
    b.fin()


if __name__ == '__main__':
    main()
