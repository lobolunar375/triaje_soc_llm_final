# Sistema multiagente basado en LLM para el triaje de alertas de seguridad en un SOC

Repositorio del experimento del artículo:

> **Sistema multiagente basado en LLM para el triaje de alertas de seguridad en un SOC: evaluación sobre el dataset GUIDE**
> Autores: Jorge Luis Berrocal Barrientos y Jhojan Neira Herrera. Inteligencia Artificial II, Facultad de Ingeniería Eléctrica y Electrónica, Universidad Nacional de Ingeniería (Perú), 2026-2.

El experimento compara, sobre los mismos 300 incidentes reales del dataset **GUIDE** de Microsoft, dos condiciones de triaje que usan el mismo modelo (GPT-4o mini), el mismo expediente y las mismas herramientas:

| Condición | Descripción | Ejecución |
|:--|:--|:--|
| C1 (control) | Un solo LLM: una llamada devuelve clase, confianza, prioridad, escalamiento, justificación y evidencias | 300 incidentes × 3 corridas |
| C2 (experimental) | Sistema multiagente: orquestador, contextualización, clasificación, priorización y trazabilidad | 300 incidentes × 3 corridas |

Mide el rendimiento del triaje (variable dependiente) en tres dimensiones: precisión de clasificación (exactitud y F1 macro), eficiencia temporal (tiempo por incidente) y trazabilidad (decisiones con justificación y evidencias verificables). Contrasta H.E.1 a H.E.3 con las pruebas de McNemar y de Wilcoxon y la corrección de Holm, y sitúa ambas condiciones frente a dos reglas sin modelo de lenguaje.

## Resultados principales

| Indicador (n = 300 incidentes) | Siempre BP | Regla del historial | C1: un solo LLM | C2: multiagente |
|:--|--:|--:|--:|--:|
| Exactitud (%) | 50,3 | 50,0 | 34,7 | **42,3** |
| F1 macro (%) | 22,3 | 47,7 | 31,9 | **38,8** |
| Omisión de amenazas, TOA (%) | 100,0 | 60,0 | 86,7 | 82,7 |
| Tiempo por incidente (s, mediana) | — | — | **2,79** | 8,94 |
| Decisiones trazables (%) | — | — | **100,0** | 94,3 |
| Misma clase en las tres corridas (%) | — | — | **81,3** | 60,7 |
| Tokens por triaje | — | — | **1 419** | 4 143 |

- **H.E.1 (precisión): se acepta.** C2 supera a C1 en exactitud (+7,7 puntos; McNemar, *b* = 45, *c* = 22; *p* = 0,005) y en F1 macro (+6,9 puntos).
- **H.E.2 (eficiencia temporal): no se acepta.** C2 tarda 3,2 veces más que C1 (Wilcoxon, *p* < 0,001). Ambas quedan muy por debajo del umbral de 5 minutos por incidente.
- **H.E.3 (trazabilidad): no se acepta.** C2 produce menos decisiones trazables (McNemar *mid-p*, *b* = 0, *c* = 17; *p* < 0,001), porque su ciclo de verificación y corrección falló en 64 de 900 triajes.
- **Hipótesis general: se acepta parcialmente.** Ninguna condición basada en LLM supera a la regla del historial, y ambas omiten más del 80 % de las amenazas reales.

Detalle: `results/estadistica/decision_hipotesis.md`, `results/estadistica/contrastes.json`, `results/estadistica/complementario.json` y `results/tablas/`.

## Estructura

```
triaje_soc_llm/
├── README.md                     este archivo
├── LICENSE                       licencia MIT del código
├── ejecutar_todo.py              ejecuta los pasos en orden
├── requirements.txt              dependencias de Python
├── requirements-lock.txt         versiones exactas usadas
├── config/
│   ├── config.yaml               parámetros del experimento (semilla, tamaños, modelo, umbrales); no contiene claves
│   ├── seleccion_caracteristicas.yaml   rol y justificación de cada una de las 45 columnas de GUIDE
│   └── mitre_tecnicas.csv        867 técnicas de MITRE ATT&CK (nombre y táctica)
├── src/
│   ├── comunes.py                rutas, configuración y bitácora detallada (qué se hace y por qué)
│   ├── 00_descargar_datos.py     descarga de Kaggle y SHA-256
│   ├── 01_explorar_dataset.py    perfil de columnas, clases, tamaños y asociación con la etiqueta
│   ├── 02_limpiar_datos.py       limpieza y selección de características
│   ├── 03_muestrear_particionar.py  partición por organización, muestreo y tamaño de muestra
│   ├── 04_construir_expedientes.py  base de conocimiento, MITRE ATT&CK, expedientes y regla del historial
│   ├── 05_triaje_llm.py          C1 y C2 (API compatible con OpenAI u Ollama)
│   ├── 07_calcular_metricas.py   registro de observación e indicadores de la VD y la VI
│   ├── 08_analisis_estadistico.py   McNemar, Wilcoxon, Holm, bootstrap y sensibilidad
│   ├── 09_figuras_tablas.py      figuras y tablas del artículo
│   ├── 09b_figura_arquitectura.py   diagrama de la arquitectura
│   ├── 10_analisis_complementario.py  reglas de referencia, subgrupos, confianza, escalamiento y ciclo de corrección
│   ├── 06_triaje_manual.py       extensión no ejecutada: formulario para una referencia de triaje manual
│   ├── 07b_consolidar_auditoria.py  extensión no ejecutada: auditoría humana de la coherencia de las justificaciones
│   └── agentes/
│       ├── prompts/              prompt de cada agente y de la línea base
│       └── esquemas/             esquema JSON de la salida de cada agente
├── data/
│   ├── raw/                      CSV de Kaggle (no se versiona)
│   ├── interim/                  Parquet intermedios (no se versiona)
│   └── processed/                muestra.csv, organizaciones de desarrollo, base de conocimiento y 375 expedientes
├── results/
│   ├── exploracion, limpieza, muestra, expedientes   salidas de los pasos 01 a 04
│   ├── corridas/                 registro crudo de los triajes (1 800 de evaluación y 16 del piloto)
│   ├── metricas/                 registro de observación e indicadores
│   ├── estadistica/              contrastes, decisión y análisis complementario
│   ├── figuras/ y tablas/        figuras y tablas del artículo
├── logs/                         bitácora de la ejecución de cada paso
├── docs/
│   ├── DOCUMENTACION_SCRIPTS.md  qué hace cada script, por qué y qué produce
│   ├── GUIA_EJECUCION.md         cómo ejecutar el triaje y el análisis
│   ├── trazabilidad.md           correspondencia sección → referencias → archivos
│   ├── Matriz_trazabilidad_paper.xlsx   la misma matriz en Excel
│   ├── curso/                    artículo y sistematización (Word y PDF)
│   └── herramientas_documentos/  fuentes del artículo y scripts que generan los documentos
├── fuentes/                      manifiesto de las referencias y script de descarga de los PDF abiertos
└── tests/prueba_humo.py          prueba del código con un backend simulado (no produce resultados)
```

## Cómo reproducir

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux o macOS: source .venv/bin/activate)
pip install -r requirements.txt

# 1. Análisis con los triajes ya guardados en results/corridas (no requiere el dataset ni el modelo)
python ejecutar_todo.py --analisis          # pasos 07, 08, 10 y 09

# 2. Preparación de los datos desde cero (requiere el zip de Kaggle en data/raw o la API de Kaggle)
python ejecutar_todo.py                     # pasos 00 a 04 y 09; unos 4 minutos y 4 GB libres

# 3. Prueba del código de punta a punta con un backend simulado
python tests/prueba_humo.py

# 4. Nueva ejecución del triaje con el modelo (la clave se lee de la variable de entorno LLM_API_KEY)
set LLM_API_KEY=...                         # Windows (en Linux o macOS: export LLM_API_KEY=...)
python src/05_triaje_llm.py --conjunto desarrollo --limite 5    # piloto
python src/05_triaje_llm.py --conjunto evaluacion               # 1 800 triajes; reanudable
python ejecutar_todo.py --analisis
```

Una nueva ejecución del paso 05 no reproduce los resultados cifra por cifra, porque el modelo no es determinista y el servicio puede cambiar; los triajes del estudio se conservan en `results/corridas/` para que el análisis sí sea reproducible. La clave de la API nunca se escribe en el repositorio.

## Configuración con la que se ejecutó el estudio

- Modelo GPT-4o mini (`gpt-4o-mini`) por la API de OpenAI, el 5 de noviembre de 2026 (de 14:51 a 18:02).
- Temperatura 0,2, *top-p* 1,0, 600 tokens de salida, semillas 1, 2 y 3, hasta 3 reintentos por esquema y umbral de escalamiento de 0,60.
- Los 1 800 triajes registran la misma huella de configuración (`07c6ce608479`). Esa huella se calculó cuando el archivo de configuración contenía un campo adicional; con los mismos *prompts*, esquemas y parámetros, el código actual devuelve `c48ccc624197`.
- Los *prompts* no se ajustaron con datos: tras un piloto de 16 triajes, se usaron tal como se diseñaron.

## Dataset

GUIDE (Microsoft Security Incident Prediction): <https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction>, licencia CDLA-Permissive-2.0. Freitas, S., Kalajdjieski, J., Gharib, A., & McCann, R. (2025). AI-driven guided response for security operation centers with Microsoft Copilot for Security. *Companion Proceedings of the ACM on Web Conference 2025*, 191–200.

El estudio usa `GUIDE_Train.csv` (9 516 837 evidencias, 730 778 incidentes y 5 769 organizaciones). El SHA-256 de los archivos está en `results/exploracion/integridad.json`. Los datos crudos no se redistribuyen; sí se incluyen los 375 expedientes derivados de la muestra (`data/processed/expedientes`), necesarios para reproducir el triaje.

## Documentos y trazabilidad

- `docs/curso/Paper_Triaje_SOC_Multiagente_LLM.pdf` y `.docx`: artículo completo, en el formato de la revista *Inteligencia Artificial* (IBERAMIA).
- `docs/curso/Sistematizacion_v3.pdf` y `.docx`: sistematización, con las matrices de operacionalización y el registro de observación estructurada lleno.
- `docs/trazabilidad.md` y `docs/Matriz_trazabilidad_paper.xlsx`: qué referencias y qué archivos respaldan cada parte del artículo.
- `docs/herramientas_documentos/verificar_cifras.py`: comprueba que las cifras del artículo coinciden con `results/`.
- `fuentes/`: `python fuentes/descargar_fuentes.py` descarga los PDF abiertos de las referencias según `manifest_fuentes.csv`.
- `results/metricas/registro_observacion.csv` es el **registro de observación estructurada**: una fila por incidente, condición y corrida.

## Limitaciones conocidas

- Un solo modelo y una sola fecha de ejecución; los *prompts* no se optimizaron.
- GUIDE está seudonimizado: el modelo no ve el texto de los títulos de alerta ni los nombres de los detectores.
- El escenario es el de una organización nueva: el sistema no tiene antecedentes de las organizaciones evaluadas.
- No hay referencia de triaje manual ni auditoría humana de la coherencia de las justificaciones; los scripts 06 y 07b permiten añadirlas en un trabajo posterior, siempre con datos de personas que realicen el triaje.
- El verificador de trazabilidad no acepta como evidencia las claves de la herramienta de historial; cuando el agente de clasificación las cita, se activa una corrección que falló en 64 de 70 ocasiones (la respuesta expresó la confianza en escala porcentual). Los triajes afectados cuentan como errores.
- Los triajes no procesados no conservan su tiempo ni sus tokens, por lo que el costo de C2 está ligeramente subestimado.

## Licencia

Código bajo licencia MIT (`LICENSE`). Los datos pertenecen a Microsoft y se usan según su licencia.
