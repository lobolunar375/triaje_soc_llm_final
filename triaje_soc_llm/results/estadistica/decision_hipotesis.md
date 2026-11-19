# Decisión sobre las hipótesis

Diseño pareado, n = 300 incidentes de evaluación; C1 (un solo LLM, control) frente a C2 (sistema multiagente).

| Hipótesis | Prueba | Resultado | p | p (Holm) | Dirección | Decisión |
|:--|:--|:--|--:|--:|:--|:--|
| H.E.1 precisión | McNemar (asintótico sin corrección) | exactitud 34.67 % → 42.33 %; b = 45, c = 22 | 0.0050 | 0.0050 | favorable a C2 | se acepta |
| H.E.2 eficiencia temporal | Wilcoxon | mediana 2.79 s → 8.94 s; r_rb = 1.0 (n = 297) | 1.88e-50 | 5.65e-50 | contraria (C2 tarda más) | no se acepta |
| H.E.3 trazabilidad | McNemar (mid-p) | TD 100.00 % → 94.33 %; b = 0, c = 17 | 7.63e-06 | 1.53e-05 | contraria (C2 es menor) | no se acepta |

**Hipótesis general**: se acepta parcialmente.
