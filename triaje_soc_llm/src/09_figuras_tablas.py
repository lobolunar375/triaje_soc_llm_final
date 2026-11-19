"""Paso 09. Figuras y tablas del artículo.

Genera, con los datos disponibles en cada momento:
  * fig_distribucion_clases.png: clases en la población elegible y en los conjuntos de desarrollo y evaluación.
  * fig_alertas_por_incidente.png: número de alertas por incidente en la población elegible (si existe
    data/interim/incidentes.parquet, que no se versiona).
  * fig_matrices_confusion.png: regla del historial, C1 y C2 (cuando existen corridas).
  * fig_exactitud_subgrupos.png: exactitud de la regla, C1 y C2 en todos los incidentes y según el historial.
  * fig_confianza.png: exactitud por intervalo de confianza declarada en C1 y C2.
  * fig_tiempos.png: tiempo por incidente en C1 y C2 y tiempo medio de cada agente de C2.
  * results/tablas/*.csv: tablas listas para el artículo.

Las figuras usan escala de grises con tramas y etiquetas directas, para que se lean igual impresas en blanco
y negro; la identidad de cada serie no depende solo del tono.
"""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from comunes import Bitacora, ruta

plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Liberation Serif', 'DejaVu Serif'], 'font.size': 9,
                     'axes.spines.top': False, 'axes.spines.right': False, 'savefig.dpi': 300, 'hatch.linewidth': 0.5,
                     'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6})
CLASES = ['TruePositive', 'BenignPositive', 'FalsePositive']
ET = {'TruePositive': 'TP', 'BenignPositive': 'BP', 'FalsePositive': 'FP', 'NP': 'NP'}
GRIS = ['#2b2b2b', '#8a8a8a', '#d4d4d4']
TRAMA = ['', '///', '']
BORDE = dict(edgecolor='black', linewidth=0.5)
coma = lambda v, d=1: f'{v:.{d}f}'.replace('.', ',')


def barras_clases(b):
    comp = pd.read_csv(ruta('results', 'muestra', 'composicion_muestra.csv'))
    comp = comp[comp.conjunto.isin(['Población elegible', 'Desarrollo', 'Evaluación'])].reset_index(drop=True)
    nombres = {'Población elegible': 'Población elegible', 'Desarrollo': 'Muestra de desarrollo', 'Evaluación': 'Muestra de evaluación'}
    # la población se grafica con los conteos exactos, para que el redondeo a un decimal coincida con el del texto
    pob = json.loads(ruta('results', 'limpieza', 'reporte_limpieza.json').read_text(encoding='utf-8'))['poblacion_elegible']
    for c in CLASES:
        comp.loc[comp.conjunto == 'Población elegible', c] = 100 * pob['clases'][c] / pob['incidentes']
    b.paso('Figura de distribución de clases', 'Compara la muestra con la población de la que proviene.')
    fig, ax = plt.subplots(figsize=(6.0, 2.5))
    x = np.arange(len(comp))
    for k, c in enumerate(CLASES):
        r = ax.bar(x + (k - 1) * 0.27, comp[c], 0.25, label=ET[c], color=GRIS[k], hatch=TRAMA[k], **BORDE)
        ax.bar_label(r, labels=[coma(v) for v in comp[c]], fontsize=7, padding=1.5)
    ax.set_xticks(x, [f'{nombres[a]}\n(n = {n:,})'.replace(',', ' ') for a, n in zip(comp.conjunto, comp.incidentes)])
    ax.set_ylabel('Incidentes (%)')
    ax.set_ylim(0, 62)
    ax.legend(frameon=False, ncol=3, loc='upper right', handlelength=1.4, columnspacing=1.2)
    fig.tight_layout()
    fig.savefig(ruta('results', 'figuras', 'fig_distribucion_clases.png'))
    plt.close(fig)


def alertas_por_incidente(b):
    arch = ruta('data', 'interim', 'incidentes.parquet')
    if not arch.exists():
        b.info('No está data/interim/incidentes.parquet (no se versiona): se conserva la figura de alertas por incidente ya generada.')
        return
    inc = pd.read_parquet(arch, columns=['n_alertas'])
    b.paso('Figura de alertas por incidente', 'Justifica el resumen del expediente y el umbral de exclusión.')
    fig, ax = plt.subplots(figsize=(3.2, 2.3))
    v = inc.n_alertas.clip(upper=11).value_counts().sort_index()
    ax.bar([str(i) if i < 11 else '>10' for i in v.index], 100 * v / v.sum(), color=GRIS[1], **BORDE)
    ax.set_yscale('log')
    ax.set_xlabel('Alertas por incidente')
    ax.set_ylabel('Incidentes (%, escala log.)')
    fig.tight_layout()
    fig.savefig(ruta('results', 'figuras', 'fig_alertas_por_incidente.png'))
    plt.close(fig)


def matrices(b, comp):
    b.paso('Matrices de confusión de la regla del historial, C1 y C2', 'Muestran qué errores predominan en cada condición.')
    orden = ['Regla del historial', 'C1 (un solo LLM)', 'C2 (multiagente)']
    fig, axs = plt.subplots(1, 3, figsize=(6.3, 2.35), gridspec_kw={'width_ratios': [3, 3, 4]})
    for ax, k in zip(axs, orden):
        m = comp['matrices_confusion'][k]
        cols = list(m['TP'].keys())
        a = np.array([[m[r][c] for c in cols] for r in ('TP', 'BP', 'FP')])
        ax.imshow(a, cmap='Greys', vmin=0, vmax=95, aspect='auto')
        for i in range(a.shape[0]):
            for j in range(a.shape[1]):
                ax.text(j, i, a[i, j], ha='center', va='center', color='white' if a[i, j] > 48 else 'black', fontsize=9)
        ax.set_xticks(range(len(cols)), cols)
        ax.set_yticks(range(3), ['TP', 'BP', 'FP'])
        ax.set_xlabel('Clase asignada')
        ax.set_title(k, fontsize=9)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(True)
    axs[0].set_ylabel('Clase real')
    fig.tight_layout(w_pad=0.8)
    fig.savefig(ruta('results', 'figuras', 'fig_matrices_confusion.png'))
    plt.close(fig)


def subgrupos(b, comp):
    b.paso('Exactitud por subgrupo según el historial', 'Localiza en qué incidentes se produce la diferencia entre C1 y C2.')
    sg = comp['subgrupos_historial']
    series = [('regla', 'Regla del historial'), ('C1', 'C1 (un solo LLM)'), ('C2', 'C2 (multiagente)')]
    fig, ax = plt.subplots(figsize=(6.0, 2.6))
    x = np.arange(len(sg))
    for k, (clave, nombre) in enumerate(series):
        val = np.array([g[f'{clave}_%'] for g in sg])
        ic = np.array([g[f'{clave}_IC95_%'] for g in sg])
        r = ax.bar(x + (k - 1) * 0.27, val, 0.25, label=nombre, color=GRIS[k], hatch=TRAMA[k], **BORDE)
        ax.errorbar(x + (k - 1) * 0.27, val, yerr=[val - ic[:, 0], ic[:, 1] - val], fmt='none', ecolor='black', elinewidth=0.6, capsize=2)
        for xi, v, hi in zip(x + (k - 1) * 0.27, val, ic[:, 1]):
            ax.text(xi, hi + 1.5, coma(v), ha='center', va='bottom', fontsize=7)
    ax.axhline(100 / 3, color='black', lw=0.7, ls=':', label='Azar uniforme (33,3 %)', zorder=0)
    ax.set_xticks(x, [f"{g['subgrupo']}\n(n = {g['n']})" for g in sg])
    ax.set_ylabel('Exactitud (%)')
    ax.set_ylim(0, 98)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[1:] + h[:1], l[1:] + l[:1], frameon=False, ncol=4, loc='upper left', handlelength=1.4, columnspacing=1.0, fontsize=7.5,
              borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(ruta('results', 'figuras', 'fig_exactitud_subgrupos.png'))
    plt.close(fig)


def confianza(b, comp):
    b.paso('Exactitud por intervalo de confianza declarada', 'Una confianza útil crece con la exactitud.')
    t = pd.read_csv(ruta('results', 'tablas', 'tabla_confianza.csv'))
    fig, axs = plt.subplots(1, 2, figsize=(6.0, 2.5), sharey=True)
    for ax, (c, nombre) in zip(axs, (('C1', 'C1 (un solo LLM)'), ('C2', 'C2 (multiagente)'))):
        d = t[t.condicion == c].reset_index(drop=True)
        v = d['exactitud_%'].fillna(0)
        r = ax.bar(range(len(d)), v, 0.62, color=GRIS[1], **BORDE)
        for xi, (val, n) in enumerate(zip(d['exactitud_%'], d.corridas)):
            if n:
                ax.text(xi, val + 2, f'{coma(val)}\nn = {n}', ha='center', va='bottom', fontsize=6.8, linespacing=1.05,
                        bbox=dict(fc='white', ec='none', pad=0.6))
        gl = comp['confianza'][c]['exactitud_por_corrida_procesada_%']
        ax.axhline(gl, color='black', lw=0.7, ls='--', label=f'Exactitud de la condición: {coma(gl)} %', zorder=0)
        ax.legend(frameon=False, loc='upper left', fontsize=7, handlelength=1.8, borderaxespad=0.2)
        ax.set_xticks(range(len(d)), d.confianza, fontsize=7.5)
        ax.set_xlabel('Confianza declarada')
        ax.set_title(f"{nombre}: AUC = {coma(comp['confianza'][c]['AUC_confianza_acierto'], 2)}", fontsize=9)
        ax.set_ylim(0, 118)
        ax.set_yticks(range(0, 101, 20))
    axs[0].set_ylabel('Exactitud de las corridas (%)')
    fig.tight_layout(w_pad=1.0)
    fig.savefig(ruta('results', 'figuras', 'fig_confianza.png'))
    plt.close(fig)


def tiempos(b):
    b.paso('Tiempo de triaje por incidente y por agente', 'Muestra el costo temporal de dividir el triaje en etapas.')
    agg = pd.read_csv(ruta('results', 'metricas', 'registro_incidente.csv'))
    ta = pd.read_csv(ruta('results', 'metricas', 'tiempo_por_agente.csv'), index_col=0)
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 2.3), gridspec_kw={'width_ratios': [2.2, 3]})
    datos = [agg[agg.condicion == c].t_total_s.dropna() for c in ('C1', 'C2')]
    bp = axs[0].boxplot(datos, tick_labels=['C1\n(un solo LLM)', 'C2\n(multiagente)'], widths=0.5, patch_artist=True,
                        medianprops=dict(color='black', lw=1.0), flierprops=dict(marker='o', ms=2.5, mfc='none', mew=0.5),
                        boxprops=dict(lw=0.6), whiskerprops=dict(lw=0.6), capprops=dict(lw=0.6))
    for p, g in zip(bp['boxes'], (GRIS[2], GRIS[1])):
        p.set_facecolor(g)
    for k, d in enumerate(datos):
        axs[0].text(k + 1.32, d.median(), f'{coma(d.median(), 2)} s', va='center', fontsize=7)
    axs[0].set_ylabel('Segundos por incidente')
    axs[0].set_xlim(0.5, 2.9)
    axs[0].set_title('(a) Tiempo por incidente', fontsize=9)
    orden = [('contextualizacion', 'Contextualización'), ('clasificacion', 'Clasificación'), ('priorizacion', 'Priorización')]
    izq = 0
    tot = sum(ta.loc[k, 'media_s'] for k, _ in orden)
    for (k, nombre), g, h in zip(orden, GRIS, TRAMA):
        v = ta.loc[k, 'media_s']
        axs[1].barh([0], [v], left=izq, height=0.5, color=g, hatch=h, **BORDE)
        axs[1].text(izq + v / 2, 0.36, f'{nombre}\n{coma(v, 2)} s ({coma(100 * v / tot, 0)} %)', ha='center', va='bottom', fontsize=7, linespacing=1.1)
        izq += v
    axs[1].set_ylim(-0.5, 1.15)
    axs[1].set_yticks([])
    axs[1].spines['left'].set_visible(False)
    axs[1].set_xlabel('Segundos por incidente (media de las corridas procesadas)')
    axs[1].set_title('(b) Tiempo de C2 por agente', fontsize=9)
    fig.tight_layout(w_pad=1.2)
    fig.savefig(ruta('results', 'figuras', 'fig_tiempos.png'))
    plt.close(fig)


def main():
    b = Bitacora('09_figuras_tablas')
    barras_clases(b)
    alertas_por_incidente(b)
    pd.read_csv(ruta('results', 'limpieza', 'embudo_limpieza.csv')).to_csv(ruta('results', 'tablas', 'tabla_embudo_limpieza.csv'), index=False)
    pd.read_csv(ruta('results', 'limpieza', 'decisiones_columnas.csv')).to_csv(ruta('results', 'tablas', 'tabla_decisiones_columnas.csv'), index=False)
    arch = ruta('results', 'estadistica', 'complementario.json')
    if not arch.exists():
        b.info('Todavía no hay resultados del triaje (pasos 05, 07, 08 y 10): se omiten las figuras de resultados.')
        b.fin()
        return
    comp = json.loads(arch.read_text(encoding='utf-8'))
    matrices(b, comp)
    subgrupos(b, comp)
    confianza(b, comp)
    tiempos(b)
    for origen, destino in (('metricas/indicadores_vd.csv', 'tabla_indicadores_vd.csv'), ('metricas/indicadores_vi.csv', 'tabla_indicadores_vi.csv'),
                            ('metricas/por_corrida.csv', 'tabla_por_corrida.csv')):
        pd.read_csv(ruta('results', *origen.split('/'))).to_csv(ruta('results', 'tablas', destino), index=False)
    b.fin()


if __name__ == '__main__':
    main()
