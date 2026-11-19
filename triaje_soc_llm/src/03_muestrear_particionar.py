"""Paso 03. Partición por organización y muestreo aleatorio simple.

Qué hace y por qué:
  1. Asigna cada organización, al azar y con semilla fija, al grupo de desarrollo (20 %) o de evaluación
     (80 %). La partición es por organización y no por incidente porque los incidentes de una misma
     organización comparten detectores, entidades y criterios de calificación (la organización es la
     columna más asociada con la etiqueta en la exploración); repartirlos entre ambos grupos filtraría
     información hacia la evaluación.
  2. Extrae por muestreo aleatorio simple n_desarrollo incidentes de las organizaciones de desarrollo y
     n_evaluacion de las de evaluación, sin usar la etiqueta.
  3. Reserva en la muestra de evaluación dos submuestras aleatorias simples (para una referencia de triaje manual
     y para una auditoría humana de la trazabilidad), también sin usar la etiqueta. Son una extensión prevista
     que no forma parte del estudio: sus columnas quedan en muestra.csv, pero ningún resultado las usa.
  4. Compara la distribución de clases de cada conjunto con la de la población (prueba chi-cuadrado de
     bondad de ajuste) y lo informa.
  5. Calcula el tamaño de muestra mínimo para McNemar (aproximación de Connor) con los supuestos de config.

Salidas: data/processed/muestra.csv (incidente, conjunto, submuestras), results/muestra/*.
"""
import math

import numpy as np
import pandas as pd
from scipy.stats import chisquare, norm

from comunes import Bitacora, cargar_config, guardar_json, pct, ruta

CLASES = ['TruePositive', 'BenignPositive', 'FalsePositive']


def n_mcnemar(delta, psi, alfa, potencia):
    za, zb = norm.ppf(1 - alfa / 2), norm.ppf(potencia)
    return math.ceil((za * math.sqrt(psi) + zb * math.sqrt(psi - delta ** 2)) ** 2 / delta ** 2)


def main():
    cfg = cargar_config()
    m = cfg['muestra']
    b = Bitacora('03_muestrear_particionar')
    rng = np.random.default_rng(cfg['semilla'])
    inc = pd.read_parquet(ruta('data', 'interim', 'incidentes.parquet'))
    # orden determinista antes de muestrear: DuckDB no garantiza el orden de las filas al agrupar
    inc = inc.assign(_o=inc.OrgId.astype(int), _i=inc.IncidentId.astype(int)).sort_values(['_o', '_i']) \
             .drop(columns=['_o', '_i']).reset_index(drop=True)
    b.info(f'Población elegible: {len(inc):,} incidentes de {inc.OrgId.nunique():,} organizaciones.')

    b.paso('Tamaño de muestra para McNemar (Connor, 1987)',
           'H.E.1 y H.E.3 se contrastan con McNemar; se usa el nivel más exigente de Holm para tres hipótesis.')
    e = cfg['estadistica']
    alfa_holm = e['alfa'] / 3
    n_min = n_mcnemar(e['delta_mcnemar'], e['psi_mcnemar'], alfa_holm, e['potencia'])
    b.info(f'delta = {e["delta_mcnemar"]}, psi = {e["psi_mcnemar"]}, alfa = {alfa_holm:.4f}, potencia = {e["potencia"]} '
           f'-> n mínimo = {n_min}. Muestra de evaluación fijada: {m["n_evaluacion"]}.')
    sens = {f'psi={p}': n_mcnemar(e['delta_mcnemar'], p, alfa_holm, e['potencia']) for p in (0.15, 0.20, 0.25, 0.30)}
    b.info(f'Sensibilidad al supuesto de psi: {sens}')

    from statsmodels.stats.power import TTestPower
    n_t = math.ceil(TTestPower().solve_power(effect_size=0.6, alpha=alfa_holm, power=e['potencia'], alternative='two-sided'))
    n_c0_min = math.ceil(n_t / 0.864)
    b.info(f'Submuestra C0 (Wilcoxon, eficiencia relativa asintótica 0,864): t pareada con d_z = 0,6 -> {n_t}; '
           f'Wilcoxon -> {n_c0_min}. Submuestra fijada: {m["n_c0"]}.')

    b.paso('Asignar organizaciones a desarrollo y evaluación con semilla fija',
           'La organización es la unidad de partición para evitar fuga entre conjuntos.')
    orgs = np.array(sorted(inc.OrgId.unique(), key=lambda x: int(x)))
    rng.shuffle(orgs)
    n_dev = int(round(len(orgs) * m['frac_org_desarrollo']))
    org_dev = set(orgs[:n_dev])
    inc['grupo_org'] = np.where(inc.OrgId.isin(org_dev), 'desarrollo', 'evaluacion')
    b.info(f'Organizaciones de desarrollo: {n_dev:,}; de evaluación: {len(orgs) - n_dev:,}.')
    b.info('Incidentes por grupo: ' + str(inc.grupo_org.value_counts().to_dict()))

    b.paso('Muestreo aleatorio simple dentro de cada grupo', 'Cada incidente del grupo tiene la misma probabilidad de ser elegido.')
    dev = inc[inc.grupo_org == 'desarrollo'].sample(n=m['n_desarrollo'], random_state=cfg['semilla'])
    ev = inc[inc.grupo_org == 'evaluacion'].sample(n=m['n_evaluacion'], random_state=cfg['semilla'])
    dev = dev.assign(conjunto='desarrollo')
    ev = ev.assign(conjunto='evaluacion')
    ev['submuestra_c0'] = ev.index.isin(ev.sample(n=m['n_c0'], random_state=cfg['semilla'] + 1).index)
    ev['auditoria'] = ev.index.isin(ev.sample(n=m['n_auditoria'], random_state=cfg['semilla'] + 2).index)
    dev['submuestra_c0'] = False
    dev['auditoria'] = False
    mu = pd.concat([dev, ev]).reset_index(drop=True)
    mu.insert(0, 'incidente', [f'INC-{k + 1:04d}' for k in range(len(mu))])
    mu.to_csv(ruta('data', 'processed', 'muestra.csv'), index=False)
    pd.DataFrame({'OrgId': sorted(org_dev, key=int)}).to_csv(ruta('data', 'processed', 'organizaciones_desarrollo.csv'), index=False)

    b.paso('Comparar la distribución de clases de cada conjunto con la población',
           'El muestreo aleatorio simple debe reproducir la distribución poblacional salvo variación aleatoria.')
    pob = inc.IncidentGrade.value_counts(normalize=True).reindex(CLASES)
    filas = [{'conjunto': 'Población elegible', 'organizaciones': inc.OrgId.nunique(), 'incidentes': len(inc),
              **{c: pct((inc.IncidentGrade == c).sum(), len(inc)) for c in CLASES}, 'p_chi2': None}]
    grupo = {g: inc[inc.grupo_org == g].IncidentGrade.value_counts(normalize=True).reindex(CLASES) for g in ('desarrollo', 'evaluacion')}
    for g, nombre in (('desarrollo', 'Grupo de organizaciones de desarrollo'), ('evaluacion', 'Grupo de organizaciones de evaluación')):
        d_ = inc[inc.grupo_org == g]
        filas.append({'conjunto': nombre, 'organizaciones': d_.OrgId.nunique(), 'incidentes': len(d_),
                      **{c: pct((d_.IncidentGrade == c).sum(), len(d_)) for c in CLASES}, 'p_chi2': None})
    for nombre, df, gr in [('Desarrollo', dev, 'desarrollo'), ('Evaluación', ev, 'evaluacion'),
                           ('Submuestra C0', ev[ev.submuestra_c0], 'evaluacion'), ('Auditoría', ev[ev.auditoria], 'evaluacion')]:
        obs = df.IncidentGrade.value_counts().reindex(CLASES, fill_value=0)
        p = chisquare(obs.values, f_exp=pob.values * len(df)).pvalue
        pg = chisquare(obs.values, f_exp=grupo[gr].values * len(df)).pvalue
        filas.append({'conjunto': nombre, 'organizaciones': df.OrgId.nunique(), 'incidentes': len(df),
                      **{c: pct(obs[c], len(df)) for c in CLASES}, 'p_chi2': round(float(p), 3), 'p_chi2_grupo': round(float(pg), 3),
                      'alertas_media': round(df.n_alertas.mean(), 2), 'evidencias_media': round(df.n_evidencias.mean(), 2)})
    comp = pd.DataFrame(filas)
    b.tabla(comp)
    comp.to_csv(ruta('results', 'muestra', 'composicion_muestra.csv'), index=False)
    guardar_json({'n_minimo_mcnemar': n_min, 'sensibilidad_psi': sens, 'n_t_pareada_c0': n_t, 'n_minimo_c0': n_c0_min, 'alfa_holm': alfa_holm,
                  'organizaciones_desarrollo': n_dev, 'organizaciones_evaluacion': len(orgs) - n_dev,
                  'incidentes_por_grupo': inc.grupo_org.value_counts().to_dict(),
                  'composicion': comp.to_dict(orient='records')}, ruta('results', 'muestra', 'resumen_muestra.json'))
    b.fin()


if __name__ == '__main__':
    main()
