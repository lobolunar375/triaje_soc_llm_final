# Documentación de los scripts

Cada script lee `config/config.yaml`, imprime en pantalla y guarda en `logs/<script>.log` una bitácora con el formato:

```
[PASO n] Qué se hace
  Por qué: la razón metodológica
  Resultado: cuántas filas, incidentes o columnas afecta
```

La bitácora de la ejecución con el dataset completo está en `logs/`. La tabla siguiente relaciona cada script con la sección del artículo y del registro de observación que alimenta.

| Script | Sección del artículo | Registro de observación (sistematización) |
|:--|:--|:--|
| 00, 01, 02 | 3.3, 3.5, 4.1, 4.2 | Preparación de los datos; selección de características |
| 03 | 3.4, 4.3 | Preparación de los datos (pasos 8 y 9); composición de la muestra |
| 04 | 3.5, 3.7, 4.4, 5.1 | Preparación de los datos (pasos 10 y 11); referencia sin LLM de los totales |
| 05 | 3.6, 3.7, 4.5 | Matriz por incidente (C1 y C2) |
| 07 | 3.8, 5.2 a 5.4 | Matriz por incidente; registro consolidado; registro global de la VI |
| 08 | 3.10, 5.5, 5.6 | Totales consolidados (pruebas y decisión) |
| 10 | 3.10, 5.2, 5.7, 6 | Registro global de la VI (indicadores complementarios) |
| 09, 09b | Figuras 1 a 6 | — |

---

## 00_descargar_datos.py

**Qué hace.** Descarga el zip de GUIDE con la API de Kaggle (o usa un zip ya copiado en `data/raw`), lo descomprime y calcula el SHA-256 de cada archivo.

**Por qué.** El SHA-256 permite que cualquier réplica verifique que trabaja con los mismos datos. El archivo de prueba de Kaggle se conserva, pero no se usa: queda reservado para una validación externa posterior.

**Salidas.** `data/raw/GUIDE_Train.csv` (2,43 GB), `GUIDE_Test.csv` (1,09 GB), `GUIDE_Test_Queue_Rankings.csv` y `results/exploracion/integridad.json`.

## 01_explorar_dataset.py

**Qué hace.** Convierte el CSV a Parquet (una sola lectura) y, con DuckDB, mide para cada una de las 45 columnas el porcentaje de nulos, la cardinalidad, si los valores son texto o códigos numéricos y su asociación con la etiqueta (V de Cramér sobre los 50 valores más frecuentes). También mide la distribución de clases por evidencia y por incidente, la consistencia de la etiqueta, el tamaño de los incidentes y la concentración por organización.

**Por qué.** El agente es un modelo de lenguaje: una columna solo le sirve si su contenido es interpretable o si puede resumirse. Estas mediciones son la evidencia empírica de la selección de características del paso 02.

**Hallazgos principales.** 9 516 837 evidencias, 1 265 644 alertas, 730 778 incidentes y 5 769 organizaciones. Ningún incidente tiene más de una calificación. El 87,6 % de los incidentes tiene una sola alerta. Las columnas más asociadas con la etiqueta son OrgId (V = 0,67), DetectorId (0,57) y AlertTitle (0,52), lo que justifica la partición por organización y la base de conocimiento por detector. Las acciones de remediación están vacías en el 99,4 % de las filas.

**Salidas.** `results/exploracion/perfil_columnas.csv`, `resumen_exploracion.json` y `.md`.

## 02_limpiar_datos.py

**Qué hace, paso por paso.**

1. Verifica que el archivo tenga las 45 columnas esperadas.
2. Elimina las filas duplicadas exactas (22 559; 0,24 %), que inflaban los conteos.
3. Convierte en nulos los valores vacíos y, en las 13 columnas de entidades, el código que aparece en más del 50 % de las filas, porque representa la ausencia de entidad (por ejemplo, el mismo DeviceId en el 96,2 % de las filas).
4. Convierte Timestamp a fecha y hora (0 marcas inválidas).
5. Excluye los incidentes sin calificación (23 670) o con más de una (0).
6. Excluye los incidentes con más de 50 alertas (1 200; el 44,7 % son TP), porque el expediente solo muestra 25 alertas en detalle y no los representaría fielmente; el criterio se aplica antes del muestreo.
7. Aplica `config/seleccion_caracteristicas.yaml` (rol y motivo de cada columna) y verifica sus supuestos con los datos: ninguna columna de entrada es un código numérico y ninguna tiene una asociación con la etiqueta cercana a 1.
8. Construye la tabla de incidentes (unidad de análisis).

**Resultado.** Población elegible de 705 908 incidentes de 5 339 organizaciones: 49,0 % BP, 30,4 % FP y 20,5 % TP. La tabla de incidentes se guarda ordenada por organización e incidente, para que el muestreo del paso 03 sea reproducible.

**Salidas.** `data/interim/evidencias_limpias.parquet`, `data/interim/incidentes.parquet`, `results/limpieza/decisiones_columnas.csv`, `embudo_limpieza.csv` y `reporte_limpieza.json` y `.md`.

### Roles de las columnas

| Rol | Columnas | Uso |
|:--|:--|:--|
| clave | OrgId, IncidentId, AlertId | Agrupación y partición; no llegan al modelo |
| entrada | Timestamp, Category, MitreTechniques, EntityType, EvidenceRole, SuspicionLevel, LastVerdict | Texto interpretable en el expediente |
| historial | DetectorId, AlertTitle | Código más tasas históricas de TP, BP y FP |
| conteo | DeviceId, Sha256, IpAddress, Url, AccountSid, AccountUpn, AccountObjectId, AccountName, DeviceName, NetworkMessageId, RegistryKey, ApplicationId, FileName | Número de entidades distintas por incidente |
| etiqueta | IncidentGrade | Solo para las métricas |
| eliminada | Id, ActionGrouped, ActionGranular, EmailClusterId, RegistryValueName, RegistryValueData, ApplicationName, OAuthApplicationId, ThreatFamily, FolderPath, ResourceIdName, ResourceType, Roles, OSFamily, OSVersion, AntispamDirection, CountryCode, State, City | Fuga de la etiqueta, casi vacías, redundantes o códigos sin significado |

## 03_muestrear_particionar.py

**Qué hace.** Calcula el tamaño mínimo de muestra para la prueba de McNemar (259 incidentes para δ = 0,10, ψ = 0,25, α = 0,05/3 y potencia de 0,80), ordena los incidentes de forma determinista, asigna las organizaciones al azar a desarrollo (20 %) o evaluación (80 %) y extrae por muestreo aleatorio simple 75 incidentes de desarrollo y 300 de evaluación. Compara la distribución de clases de cada conjunto con la de la población y con la de su grupo de organizaciones (chi-cuadrado). Reserva además, dentro de la muestra de evaluación, dos submuestras (40 y 60 incidentes) para una extensión con triaje manual y auditoría humana que no forma parte del estudio.

**Por qué.** La partición por organización evita que el sistema reciba, a través de la base de conocimiento, información de las organizaciones que luego se evalúan. El muestreo no usa la etiqueta.

**Resultado.** 1 068 organizaciones de desarrollo y 4 271 de evaluación. La muestra de evaluación (193 organizaciones) no difiere de su grupo (*p* = 0,407); sí difiere ligeramente de la población (*p* = 0,044), porque la partición por organización dejó en desarrollo organizaciones grandes con muchos FP.

**Salidas.** `data/processed/muestra.csv`, `organizaciones_desarrollo.csv`, `results/muestra/composicion_muestra.csv` y `resumen_muestra.json`.

## 04_construir_expedientes.py

**Qué hace.**

1. Calcula la base de conocimiento: para cada detector, título y categoría, el número de alertas calificadas y el porcentaje que terminó en TP, BP o FP, solo con las organizaciones de desarrollo y excluidas las 37 organizaciones de la muestra de desarrollo, para que el ajuste de los prompts se haga en la misma situación que la evaluación. Solo informa porcentajes con al menos 20 alertas calificadas.
2. Traduce las técnicas de MITRE ATT&CK con `config/mitre_tecnicas.csv` (867 técnicas, generada desde la colección oficial `mitre/cti`).
3. Construye un expediente JSON por incidente, con identificadores citables (A1, A1-E1) para alertas y grupos de evidencias.
4. Calcula la referencia estadística: la clase con mayor porcentaje histórico sumado sobre las alertas del incidente; si ningún detector tiene historial, asigna BP.

**Resultado.** 79 806 alertas calificadas de 59 409 incidentes; 246 detectores y 366 títulos con soporte suficiente. Expedientes con una mediana de 248 tokens (máximo 3 124). La referencia estadística alcanza un 50,0 % de exactitud y un 47,7 % de F1 macro en evaluación (asignar siempre BP: 50,3 % y 22,3 %) y omite 45 de los 75 TP.

**Salidas.** `data/processed/base_conocimiento.parquet`, `data/processed/expedientes/INC-xxxx.json`, `expedientes.jsonl`, `results/expedientes/referencia_estadistica.csv` y `resumen_expedientes.json`.

## 05_triaje_llm.py

**Qué hace.** Ejecuta C1 y C2 sobre el conjunto elegido, con R = 3 corridas (semillas 1, 2 y 3), intercalando las condiciones por incidente en orden aleatorio. Registra por cada triaje la clase, la confianza, la prioridad, el escalamiento, la justificación, las evidencias, el tiempo total y por agente, las llamadas, los tokens, los reintentos y la huella de configuración. Es reanudable.

**Diseño de C2.** El orquestador (código) entrega el expediente y las salidas de las herramientas, valida cada salida con `jsonschema` (hasta 3 reintentos) y escala si la confianza es menor que 0,60 o si el agente de priorización lo decide. Contextualización, clasificación y priorización son agentes LLM con los prompts de `src/agentes/prompts`. Trazabilidad es un verificador que contrasta las evidencias citadas con los identificadores citables del expediente (alertas, grupos de evidencias y técnicas de ATT&CK) y pide una única corrección si alguna no figura entre ellos. Si un agente no entrega una salida válida tras los reintentos, el triaje se registra como no procesado.

**Backends.** `openai` (cualquier API compatible con la de OpenAI; es el que usó el estudio, con `gpt-4o-mini`), `ollama` (modelo local) y `simulado` (solo para la prueba de humo). La clave de la API se lee de la variable de entorno `LLM_API_KEY` y nunca se guarda en el repositorio; la huella de configuración no la incluye.

**Comportamiento observado en el estudio.** En 70 de los 900 triajes de C2 el agente de clasificación citó claves de la herramienta de historial (detector, título o categoría), que el verificador no acepta; en 64 de esas 70 correcciones la respuesta expresó la confianza en escala porcentual, incumplió el esquema en los cuatro intentos y el triaje quedó como no procesado. El código se conserva tal como se ejecutó; las recomendaciones para corregirlo están en la sección 6.3 del artículo.

**Salidas.** `results/corridas/corridas_<conjunto>.jsonl`.

## 07_calcular_metricas.py

**Qué hace.** Construye el registro de observación (una fila por incidente, condición y corrida), lo agrega por incidente (moda de la clase, mayoría de los indicadores binarios y mediana del tiempo), calcula los indicadores de la VD (PC, F1 macro, TOA, ET, TH y TD, con su nivel según la matriz de operacionalización) y de la VI (SV, EV, AC, TR, RI, TH y TK), y los indicadores por corrida.

**Triajes no procesados.** Cuentan como error: no aciertan la clase y no son trazables. Sus contadores de llamadas, tokens y tiempo no se conservaron, por lo que quedan vacíos y los promedios se calculan con los triajes procesados. El indicador SV se informa con las salidas registradas y con una reconstrucción que añade las salidas que con seguridad se emitieron en cada triaje no procesado (dos válidas y cuatro inválidas).

**Salidas.** `results/metricas/registro_observacion.csv`, `registro_incidente.csv`, `indicadores_vd.csv`, `indicadores_vi.csv`, `por_corrida.csv`, `tiempo_por_agente.csv` y `resumen_metricas.json`.

## 08_analisis_estadistico.py

**Qué hace.** Contrasta las tres hipótesis con C2 frente a C1: McNemar para H.E.1 (acierto) y H.E.3 (decisión trazable), en su versión asintótica sin corrección o *mid-p* si hay menos de 25 pares discordantes, y Wilcoxon con la correlación biserial de rangos para H.E.2 (tiempo por incidente). Aplica la corrección de Holm; una hipótesis se acepta solo si su valor *p* ajustado es menor que 0,05 y el efecto tiene la dirección planteada. Calcula intervalos por bootstrap pareado y el análisis de sensibilidad: por corrida, sin los incidentes con triajes no procesados, solo con las decisiones no escaladas, por subgrupo según el historial y con bootstrap por organización.

**Salidas.** `results/estadistica/contrastes.json` y `decision_hipotesis.md`.

## 10_analisis_complementario.py

**Qué hace.** Responde a preguntas que el contraste de C2 frente a C1 no cubre: compara cada condición con la regla del historial y con asignar siempre BP (McNemar); separa los incidentes según tengan o no historial del detector; mide si la confianza declarada distingue aciertos de errores (área bajo la curva ROC e intervalos) y si coincide con un porcentaje del historial; analiza el escalamiento y la prioridad; mide la consistencia entre corridas; reconstruye el desenlace del ciclo de verificación y corrección, y resume las justificaciones y el costo.

**Por qué.** Una mejora sobre el control no implica superar una regla simple, y los fallos del sistema deben poder explicarse con el registro.

**Salidas.** `results/estadistica/complementario.json` y `results/tablas/tabla_desempeno.csv`, `tabla_matrices_confusion.csv`, `tabla_subgrupos_historial.csv` y `tabla_confianza.csv`.

## 09_figuras_tablas.py y 09b_figura_arquitectura.py

**Qué hacen.** Generan las figuras del artículo (arquitectura, distribución de clases, matrices de confusión, exactitud por subgrupo, confianza y tiempos) y copian las tablas a `results/tablas`. Las figuras usan escala de grises con tramas y etiquetas directas para que se lean igual impresas en blanco y negro.

## 06_triaje_manual.py y 07b_consolidar_auditoria.py (extensión no ejecutada)

No forman parte del estudio. El 06 es un formulario de terminal para medir una referencia de triaje manual con analistas (registra el tiempo y la decisión de cada uno), y el 07b consolida una auditoría ciega de la coherencia entre justificación, evidencias y clase hecha por dos revisores (`07_calcular_metricas.py --plantilla-auditoria` prepara la plantilla). Quedan disponibles para un trabajo posterior; sus datos deben provenir siempre de personas que realicen el triaje o la revisión, nunca de una simulación.

## tests/prueba_humo.py

Copia el repositorio a una carpeta temporal y ejecuta los pasos 05, 07, 08, 10 y 09 con el backend simulado. Comprueba que el código funciona de punta a punta antes de las corridas reales; sus salidas no son resultados del estudio y se borran al terminar.
