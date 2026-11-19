"""Paso 09b. Diagrama de la arquitectura del sistema multiagente (Figura del artículo)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from comunes import ruta

plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Liberation Serif', 'DejaVu Serif'], 'font.size': 8})
fig, ax = plt.subplots(figsize=(6.3, 3.0))
ax.set_xlim(0, 100)
ax.set_ylim(0, 48)
ax.axis('off')


def caja(x, y, w, h, titulo, sub, gris='#f2f2f2', borde='black', estilo='-'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.4,rounding_size=1.2', fc=gris, ec=borde, lw=0.8, ls=estilo))
    ax.text(x + w / 2, y + h - 2.6, titulo, ha='center', va='center', fontweight='bold')
    ax.text(x + w / 2, y + h / 2 - 2.2, sub, ha='center', va='center', fontsize=6.5, linespacing=1.1)


def flecha(x1, y1, x2, y2, texto='', dx=0, dy=1.2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=8, lw=0.7, color='black'))
    if texto:
        ax.text((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy, texto, ha='center', fontsize=6.3, style='italic')


caja(1, 18, 14, 13, 'Expediente', 'alertas y\nevidencias con\nIDs citables\n(A1, A1-E1)', '#ffffff')
caja(19, 36, 62, 10.5, 'Orquestador (código)', 'activa a los agentes en orden · valida cada salida contra su esquema JSON (hasta 3 reintentos)\n'
     'invoca las herramientas · mide el tiempo por etapa · escala a revisión humana si confianza < 0,60', '#e6e6e6')
caja(19, 14, 17, 17, 'Contextualización', 'LLM\nresumen, tácticas,\nseñales maliciosas\ny benignas')
caja(41, 14, 17, 17, 'Clasificación', 'LLM\nclase (TP/BP/FP),\nconfianza,\njustificación\ny evidencias')
caja(63, 14, 17, 17, 'Priorización', 'LLM\nprioridad P1-P4\ny escalamiento')
caja(41, 0.5, 39, 10.5, 'Trazabilidad (verificador)', 'contrasta cada evidencia citada con el expediente;\nsi alguna no existe, pide una corrección\na Clasificación y consolida el reporte auditable', '#ffffff')
caja(85, 18, 14, 13, 'Decisión', 'clase, prioridad,\nescalamiento y\nreporte auditable', '#ffffff')
caja(1, 1, 33, 10, 'Herramientas', 'MITRE ATT&CK (nombre y táctica)\nhistorial de calificaciones\n(organizaciones de desarrollo)', '#ffffff', estilo='--')
flecha(15, 24.5, 19, 24.5)
flecha(36, 22.5, 41, 22.5)
flecha(58, 22.5, 63, 22.5)
flecha(80, 24.5, 85, 24.5)
flecha(46, 14, 46, 11.4, 'evidencias', dx=-5.5, dy=-0.6)
flecha(54, 11.4, 54, 14, 'corrección', dx=5.5, dy=-0.6)
flecha(27.5, 11.4, 27.5, 14, '', )
for x in (27.5, 49.5, 71.5):
    ax.plot([x, x], [31.4, 36], color='black', lw=0.5, ls=':')
fig.tight_layout(pad=0.2)
fig.savefig(ruta('results', 'figuras', 'fig_arquitectura.png'), dpi=300)
print('ok')
