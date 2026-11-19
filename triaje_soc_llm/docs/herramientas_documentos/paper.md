---
title: "Sistema multiagente basado en LLM para el triaje de alertas de seguridad en un SOC: evaluación sobre el dataset GUIDE"
---

::: {custom-style="TitleEN"}
LLM-Based Multi-Agent System for Security Alert Triage in a SOC: An Evaluation on the GUIDE Dataset
:::

::: {custom-style="Authorname"}
Jorge Luis Berrocal Barrientos^1^, Jhojan Neira Herrera^1^
:::

::: {custom-style="Authoraffiliation"}
^1^Universidad Nacional de Ingeniería, Facultad de Ingeniería Eléctrica y Electrónica, Lima, Perú
:::

::: {custom-style="Abstract"}
**Abstract** Security operations centers (SOCs) receive more alerts than their analysts can triage, and large language models (LLMs) organized as multi-agent systems have been proposed to automate this task. However, such systems have rarely been compared with a single LLM under the same model and the same information. This paper evaluates a five-agent system (orchestrator, contextualization, classification, prioritization and traceability) against a single-LLM control in a paired quasi-experimental design on 300 real incidents from Microsoft's GUIDE dataset, drawn from organizations unseen by the system and labeled as true positive, benign positive or false positive. Both conditions used GPT-4o mini and were run three times (1,800 triages). The multi-agent system increased accuracy from 34.7% to 42.3% (McNemar test, p = 0.005) and macro-F1 from 31.9% to 38.8%, but it took 3.2 times longer per incident (8.94 s versus 2.79 s) and produced fewer traceable decisions (94.3% versus 100%), because its verification-and-correction loop failed in 7.1% of its triages. Both conditions remained below a simple rule based on detector history (50.0% accuracy) and missed more than 80% of the true threats. The gain was concentrated in incidents without detector history, where the multi-agent system followed historical base rates more closely, whereas its confidence scores became uninformative. With pseudonymized data and no organization-specific context, dividing triage among LLM agents improves a weak baseline but does not yield a system suitable for autonomous triage.
:::

::: {custom-style="Abstract"}
**Resumen** Los centros de operaciones de seguridad (SOC) reciben más alertas de las que sus analistas pueden clasificar, y se ha propuesto automatizar este triaje con modelos de lenguaje de gran tamaño (LLM) organizados como sistemas multiagente. Sin embargo, estos sistemas rara vez se han comparado con un solo LLM que use el mismo modelo y la misma información. Este artículo evalúa un sistema de cinco agentes (orquestador, contextualización, clasificación, priorización y trazabilidad) frente a un control de un solo LLM, con un diseño cuasiexperimental pareado sobre 300 incidentes reales del conjunto de datos GUIDE de Microsoft, de organizaciones desconocidas para el sistema, calificados como verdadero positivo, positivo benigno o falso positivo. Ambas condiciones usaron GPT-4o mini y se ejecutaron tres veces (1 800 triajes). El sistema multiagente elevó la exactitud del 34,7 % al 42,3 % (McNemar, p = 0,005) y el F1 macro del 31,9 % al 38,8 %, pero tardó 3,2 veces más por incidente (8,94 s frente a 2,79 s) y produjo menos decisiones trazables (94,3 % frente a 100 %), porque su ciclo de verificación y corrección falló en el 7,1 % de sus triajes. Ambas condiciones quedaron por debajo de una regla simple basada en el historial de los detectores (50,0 % de exactitud) y omitieron más del 80 % de las amenazas reales. La ganancia se concentró en los incidentes sin historial del detector, en los que el sistema multiagente siguió mejor las frecuencias históricas, pero su confianza dejó de ser informativa. Con datos seudonimizados y sin contexto de la organización, repartir el triaje entre agentes LLM mejora una línea base débil, pero no produce un sistema apto para el triaje autónomo.
:::

::: {custom-style="Abstract"}
**Keywords**: Multi-Agent Systems, Natural Language Processing, Trustworthy and Explainable AI, Applications of AI, Security Operations Center, Alert Triage.
:::

::: {custom-style="Abstract"}
**Palabras clave**: sistemas multiagente, modelos de lenguaje, triaje de alertas, SOC, trazabilidad.
:::

# 1 Introducción

Un centro de operaciones de seguridad (SOC, por sus siglas en inglés) vigila la infraestructura de una organización y debe decidir, para cada alerta, si corresponde a un ataque, cuánta prioridad merece y si debe escalarse. Este triaje enfrenta un problema de escala: el volumen de alertas supera la capacidad de los analistas, lo que produce fatiga de alertas y aumenta el riesgo de pasar por alto amenazas críticas [9]; las alertas sin atender se acumulan y dejan la red expuesta [17]. Una parte considerable de ese volumen corresponde a falsos positivos o a eventos de baja prioridad [10][12][15], y su revisión depende del trabajo manual y repetitivo de analistas especializados, a quienes deja poco tiempo para el análisis en profundidad [13].

La investigación ha respondido con métodos de aprendizaje automático que agrupan, clasifican o priorizan las alertas [1][2][6][14][16]. Estos métodos reducen la carga, pero suelen depender de datos etiquetados o de formatos de alerta específicos [12][16], y rara vez explican sus decisiones en el lenguaje del analista. Los modelos de lenguaje de gran tamaño (LLM) prometen cubrir esa brecha, porque pueden interpretar la alerta con su contexto y justificar la decisión [15][20]. Las evaluaciones disponibles muestran, sin embargo, límites claros: en la clasificación de alertas estructuradas, clasificadores ligeros igualan o superan a los LLM, cuya priorización tiene baja precisión [3]; el contexto mejora los resultados, pero el costo, la fiabilidad y la exposición de datos sensibles dificultan el uso práctico [15], y la robustez y la explicabilidad siguen siendo desafíos abiertos [20].

Una línea reciente propone organizar los LLM como agentes especializados que usan herramientas y se coordinan para investigar cada alerta [8][11][12]. Los resultados publicados son alentadores, como un 94,1 % de acuerdo con analistas sénior y 28 segundos de media por alerta en un SOC en producción [12], pero dejan tres preguntas sin responder. Primero, estos sistemas no se comparan con un solo LLM que disponga del mismo modelo y de la misma información, de modo que no se sabe cuánto aporta la organización multiagente. Segundo, se evalúan en el entorno de una sola organización, o sin métricas de desempeño [11], y sin separar los datos con que se construye el sistema de los datos con que se evalúa, una omisión que puede hacer pasar por buenas soluciones degeneradas [4]. Tercero, la trazabilidad de las decisiones, que es la condición para auditarlas, casi nunca se mide.

Este trabajo aborda esas preguntas con la siguiente pregunta de investigación: ¿en qué medida un sistema multiagente basado en LLM mejora el rendimiento del triaje de alertas de seguridad, es decir, su precisión de clasificación, su eficiencia temporal y la trazabilidad de sus decisiones, respecto de un solo LLM? Para responderla se desarrolló un sistema de cinco agentes y se comparó con un control de un solo LLM en un diseño cuasiexperimental pareado, sobre 300 incidentes reales del conjunto de datos GUIDE de Microsoft [19] que pertenecen a organizaciones de las que el sistema no tiene antecedentes.

Las contribuciones del artículo son cuatro:

- Una comparación controlada entre un solo LLM y un sistema multiagente que comparten el modelo, la información de entrada y la regla de escalamiento, sobre incidentes calificados por los analistas de las organizaciones, con partición por organización y con reglas de referencia sin modelo de lenguaje.
- Una definición de trazabilidad verificable de forma automática y un registro de observación que conserva cada triaje con su justificación, sus evidencias, su tiempo y su costo.
- Evidencia de un resultado mixto: el sistema multiagente mejora la exactitud en 7,7 puntos porcentuales, pero tarda 3,2 veces más, produce menos decisiones trazables y, al igual que el control, queda por debajo de una regla simple basada en el historial de los detectores.
- Un análisis de los mecanismos que explican ese resultado (el uso de las frecuencias históricas, la confianza declarada y la propagación de errores entre agentes) y un repositorio con el código, los *prompts*, la configuración y el registro de los 1 800 triajes.

El resto del artículo se organiza así. La sección 2 revisa los trabajos relacionados. La sección 3 describe los materiales y métodos, y la sección 4, el desarrollo del experimento. La sección 5 presenta los resultados, que se discuten en la sección 6. La sección 7 reúne las conclusiones y el trabajo futuro.

# 2 Trabajos relacionados

**Triaje y priorización con aprendizaje automático.** Una primera familia de trabajos reduce el volumen de alertas o las ordena por riesgo. Zhong et al. [13] registran las operaciones de los analistas durante el triaje y construyen con ellas máquinas de estados que lo automatizan. Vaarandi y Guerra-Manzanares [6] guían un clasificador supervisado de alertas de detección de intrusiones con agrupamiento de flujos de datos. Landauer et al. [16] proponen una agregación independiente del dominio que reduce en torno al 80 % los grupos de alertas que requieren revisión humana, y Ghadermazi et al. [17] combinan aprendizaje automático y optimización para descartar alertas benignas, agrupar las similares y asignarlas a los analistas, con una reducción del 60 % de las alertas pendientes en un turno de ocho horas. AlertPro [2] prioriza las alertas con aprendizaje por refuerzo sensible al contexto para detectar ataques de varios pasos; Alert2Vec [14] las representa mediante aprendizaje de subgrafos sobre un grafo heterogéneo, y CyberShapley [1] explica y prioriza las alertas a partir de una representación en grafo. Okafor [4] advierte que estas evaluaciones son sensibles a la fuga de información: con un protocolo que la impide, varias políticas de aprendizaje por refuerzo degeneran en detectores triviales que las métricas habituales no revelan.

**LLM para clasificar e interpretar alertas.** Rieger et al. [3] evalúan ocho LLM de propósito general en la clasificación y la priorización de 178 alertas etiquetadas manualmente y los comparan con clasificadores tradicionales: una máquina de vectores de soporte lineal obtiene el mayor F1, y la priorización de los LLM muestra baja precisión. Schärmer et al. [15] comparan ChatGPT y Gemini en la interpretación de alertas de sistemas de detección de intrusiones y concluyen que el contexto adicional (registros, configuración y ejemplos seleccionados) mejora la clasificación. Mudzakir et al. [7] evalúan tres LLM de 8 000 millones de parámetros, con recuperación de documentos, en el análisis de registros de ataque. La revisión de Mohammed y Jamali [20] sitúa estos avances en el ciclo de la búsqueda de amenazas y señala como limitaciones la robustez, la explicabilidad, la privacidad de los datos y la vulnerabilidad ante entradas adversarias.

**Agentes y orquestación en el SOC.** Kumar y Khan [12] presentan un agente LLM que investiga cada alerta con herramientas, acumula una memoria institucional de los triajes anteriores y se defiende de la inyección de instrucciones; lo evalúan durante 30 días con 847 alertas de un SOC en producción. Ismail et al. [11] proponen una plataforma de orquestación y respuesta en la que agentes LLM generan el código de las acciones, y la prueban en un piloto de laboratorio sin métricas de desempeño. Simões et al. [8] estudian la seguridad de los sistemas multiagente que automatizan el triaje de primer nivel mediante el protocolo MCP (*Model Context Protocol*): de 35 vectores de ataque, 29 pueden mitigarse con una capa intermedia que controla el acceso y valida entradas y salidas.

**Fatiga de alertas y factor humano.** Baruwal Chhetri et al. [9] proponen que analistas e inteligencia artificial trabajen como un equipo que alterna tres modos de decisión (automatizado, aumentado y colaborativo), y Tariq et al. [5] desarrollan ese marco con un sistema que reconoce su incertidumbre y delega en el experto los casos que no puede resolver. Vermeer et al. [18] entrevistan a 17 profesionales y muestran que la calidad de las alertas depende de cómo se gestionan las reglas de detección y de la transferencia del conocimiento tácito. ExTriage [10] acompaña un clasificador con explicaciones locales y contrafactuales; en un estudio con 24 analistas, el tiempo de triaje bajó de 47 a 8,2 segundos por alerta.

La Tabla 1 resume los estudios más cercanos a este trabajo. Ninguno compara, con el mismo modelo y la misma información, un solo LLM con un sistema multiagente sobre incidentes reales calificados por analistas de muchas organizaciones, ni mide a la vez la exactitud, el tiempo y la trazabilidad con control de la fuga entre organizaciones. Ese es el vacío que aborda este estudio.

: Tabla 1: Estudios más cercanos a este trabajo.

| Estudio | Propuesta | Datos y evaluación | Diferencia con este estudio |
|:--|:--|:--|:--|
| Rieger et al. [3] | Ocho LLM de propósito general para clasificar y priorizar alertas, frente a clasificadores tradicionales | 178 alertas etiquetadas manualmente; la máquina de vectores de soporte lineal obtiene el mayor F1 | Un solo LLM, sin agentes; dos clases |
| Schärmer et al. [15] | ChatGPT y Gemini para interpretar alertas de detección de intrusiones | Alertas de red y de host; el contexto y los ejemplos mejoran la clasificación | Un solo LLM; sin comparación con agentes |
| Kumar y Khan [12] | Agente LLM con herramientas, memoria institucional y defensa ante inyección | 847 alertas de un SOC en producción; 94,1 % de acuerdo con analistas sénior; 28 s por alerta | Una sola organización, con su contexto; sin control de un solo LLM |
| Simões et al. [8] | Marco de seguridad para sistemas multiagente basados en MCP | 600 ejecuciones de ataque en laboratorio; todas bloqueadas | Evalúa la seguridad del sistema, no su exactitud |
| Ismail et al. [11] | Orquestación y respuesta con agentes LLM que generan código | Piloto de laboratorio; sin métricas de desempeño | Sin evaluación cuantitativa del triaje |
| Kazi y Poinkar [10] | Clasificador conjunto con explicaciones locales y contrafactuales | Tres conjuntos de detección de intrusiones; F1 macro del 97,9 %; estudio con 24 analistas | Aprendizaje supervisado; no usa LLM |
| Okafor [4] | Protocolo sin fuga para aprendizaje por refuerzo fuera de línea | Dos conjuntos de detección de intrusiones; varias políticas degeneran en detectores triviales | Motiva la partición sin fuga y las referencias simples |


# 3 Materiales y métodos

Esta sección describe el diseño de la investigación, las variables, el conjunto de datos, la muestra, la representación de los incidentes, el sistema multiagente, las condiciones de comparación, el instrumento de medición, el procedimiento y el análisis estadístico.

## 3.1 Diseño de la investigación

El estudio es cuantitativo y aplicado: desarrolla y evalúa un sistema para un problema operativo del SOC. Su nivel es correlacional-causal, porque se manipula la presencia del sistema multiagente y se estima su efecto sobre el rendimiento del triaje. El diseño es cuasiexperimental, transversal y de medidas pareadas: no hay asignación aleatoria de sujetos, pero cada incidente se procesa en la condición de control y en la experimental y actúa como su propio control, lo que neutraliza la dificultad intrínseca de cada caso. La medición se hace en un único corte sobre un conjunto de datos histórico. La técnica es la observación estructurada mediante experimentación computacional, y el instrumento es un registro de observación estructurada que los programas del estudio completan de forma automática.

## 3.2 Variables e hipótesis

La variable independiente (VI) es el sistema multiagente basado en LLM, con dos valores: ausente (un solo LLM, condición de control) y presente (condición experimental). Se describe con tres dimensiones: la precisión del sistema (salidas que cumplen el esquema, evidencias verificables y acuerdo entre corridas), la eficiencia temporal de respuesta (tiempo de cómputo y reintentos por incidente) y la capacidad de procesamiento (incidentes por hora y *tokens* por incidente). La variable dependiente (VD) es el rendimiento del triaje, entendido como la capacidad de clasificar y priorizar correctamente los incidentes, en poco tiempo y con decisiones trazables. La Tabla 2 resume sus indicadores y los niveles con que se interpretan.

: Tabla 2: Indicadores de la variable dependiente.

| Dimensión | Indicador | Fórmula | Niveles |
|:--|:--|:--|:--|
| Precisión de clasificación | Exactitud y F1 macro (%) | $PC = \frac{1}{N}\sum_{k} n_{kk} \times 100$ | Bajo < 70; Medio 70–85; Alto > 85 |
| Eficiencia temporal del triaje | Tiempo medio por incidente (min) | $ET = \frac{1}{N}\sum_{i} t_i / 60$ | Bajo > 15; Medio 5–15; Alto < 5 |
| Trazabilidad de las decisiones | Decisiones trazables (%) | $TD = \frac{1}{N}\sum_{i} T_i \times 100$ | Bajo < 60; Medio 60–85; Alto > 85 |

En la Tabla 2, $N$ es el número de incidentes evaluados, $n_{kk}$ el número de incidentes de la clase $k$ asignados a esa misma clase, $t_i$ el tiempo de triaje del incidente $i$ en segundos y $T_i$ un indicador que vale 1 si la decisión es trazable. En adelante, «precisión de clasificación» designa la dimensión, que se mide con la exactitud y el F1 macro, y $P_k$ la precisión de cada clase. Como la etiqueta de GUIDE se asigna al incidente, la unidad de análisis es el incidente.

Las hipótesis específicas son tres. Según H.E.1, el sistema multiagente mejora la precisión de clasificación respecto de un solo LLM. Según H.E.2, mejora la eficiencia temporal del triaje. Según H.E.3, mejora la trazabilidad de las decisiones. Cada hipótesis nula sostiene que no hay diferencia entre las dos condiciones. La hipótesis general, según la cual el sistema multiagente mejora el rendimiento del triaje, se considera respaldada si se rechazan las tres hipótesis nulas en la dirección planteada, y parcialmente respaldada si se rechazan una o dos. Los umbrales de eficiencia de la Tabla 2 están definidos en tiempo de analista; por eso H.E.2 se contrasta frente al control y, además, cada condición se sitúa frente a esos umbrales.

## 3.3 Conjunto de datos

Se utiliza GUIDE, publicado por Microsoft en Kaggle con la licencia CDLA-Permissive-2.0 [19]. Reúne más de 13 millones de evidencias de 33 tipos de entidad, 1,6 millones de alertas y un millón de incidentes de unas 6 100 organizaciones, con 441 técnicas de MITRE ATT&CK. Cada incidente lleva la calificación de triaje (*IncidentGrade*) que le asignaron los analistas de la organización cliente: verdadero positivo (TP, actividad maliciosa), positivo benigno (BP, actividad real pero esperada o autorizada) y falso positivo (FP, detección errónea). Los datos se distribuyen en un archivo de entrenamiento (70 %) y otro de prueba (30 %). Los identificadores de organizaciones, detectores, títulos de alerta y entidades están seudonimizados, es decir, reemplazados por códigos.

Este estudio usa el archivo de entrenamiento (GUIDE_Train.csv) como población y no utiliza el de prueba. Se registró el resumen SHA-256 de cada archivo para que una réplica compruebe que usa los mismos datos.

## 3.4 Población, muestra y partición

La población la forman los incidentes del archivo de entrenamiento que tienen una única calificación de triaje y como máximo 50 alertas distintas. El segundo criterio responde a la representación del incidente: el expediente muestra en detalle como máximo 25 alertas (sección 3.5), de modo que con más de 50 mostraría menos de la mitad. Ambos criterios se aplican antes del muestreo, para que la muestra represente a la población elegible.

La partición se hace por organización y no por incidente. Los incidentes de una misma organización comparten detectores, entidades y criterios de calificación, de modo que repartirlos entre los datos que alimentan al sistema y los datos de evaluación filtraría información; este tipo de fuga hace que soluciones degeneradas parezcan aptas para su despliegue [4]. Las organizaciones se asignan al azar, con la semilla 42, al grupo de desarrollo (20 %) o al de evaluación (80 %). Después se extraen por muestreo aleatorio simple, sin usar la etiqueta, 75 incidentes de las organizaciones de desarrollo y 300 de las organizaciones de evaluación. Los primeros se reservan para probar el sistema; los segundos, para la medición. El escenario que resulta es el de una organización nueva: el sistema clasifica incidentes de organizaciones de las que no tiene ningún antecedente.

El tamaño de la muestra de evaluación se calculó para la prueba de McNemar, que contrasta H.E.1 y H.E.3, con la aproximación para proporciones pareadas

$$n = \frac{\left[ z_{1-\alpha/2}\sqrt{\psi} + z_{1-\beta}\sqrt{\psi - \delta^{2}} \right]^{2}}{\delta^{2}}$$

donde $\delta$ es la diferencia mínima relevante en exactitud entre las dos condiciones, $\psi$ la proporción esperada de pares discordantes (incidentes que una condición acierta y la otra no) y $1-\beta$ la potencia. Con $\delta$ = 0,10, $\psi$ = 0,25, una potencia de 0,80 y el nivel más exigente de la corrección de Holm para tres hipótesis ($\alpha$ = 0,05/3), se requieren 259 incidentes; se fijaron 300. Los incidentes que el sistema no logra procesar no reducen la muestra, porque cuentan como error.

## 3.5 Selección de características y representación del incidente

GUIDE tiene 45 columnas por evidencia. La selección de características respondió a un criterio propio de este estudio: el agente es un modelo de lenguaje, por lo que una columna solo aporta si su contenido es interpretable o si puede resumirse en información interpretable. Cada columna recibió uno de seis roles, y la decisión se contrastó con tres mediciones del archivo completo: el porcentaje de valores nulos, el tipo de valor (texto o código seudonimizado) y la asociación con la etiqueta. Esta se midió con la V de Cramér por evidencia, con los 50 valores más frecuentes de cada columna y una categoría para el resto.

- **Clave**: OrgId, IncidentId y AlertId agrupan las evidencias y definen la partición; no se muestran al modelo.
- **Entrada**: Timestamp, Category, MitreTechniques, EntityType, EvidenceRole, SuspicionLevel y LastVerdict conservan texto con significado y llegan al expediente.
- **Historial**: DetectorId y AlertTitle son códigos sin significado para el modelo, pero su historial de calificaciones en otras organizaciones es información que usa un analista con experiencia; se presentan como códigos acompañados de ese historial.
- **Conteo**: las 13 columnas de entidades seudonimizadas (dispositivos, direcciones IP, cuentas, archivos, URL, mensajes, claves de registro y aplicaciones) se resumen como número de entidades distintas por incidente.
- **Etiqueta**: IncidentGrade solo se usa para calcular las métricas.
- **Eliminadas**: las acciones de remediación (ActionGrouped y ActionGranular), que se registran después del triaje y filtrarían la etiqueta; las columnas casi vacías; los códigos sin significado ni utilidad de conteo, y la ubicación geográfica seudonimizada.

Con las columnas conservadas se construye el expediente del incidente, un objeto JSON que es la entrada común de todas las condiciones. Contiene un resumen (número de alertas y evidencias, duración, detectores distintos, categorías y entidades distintas), las alertas en orden temporal con su detector, título, categoría y técnicas, y sus evidencias agrupadas por tipo, rol, nivel de sospecha y veredicto. Cada alerta y cada grupo de evidencias tiene un identificador citable (A1, A1-E1), y también se aceptan como evidencia los identificadores de las técnicas de ATT&CK del expediente; así se puede verificar después qué evidencias citó cada decisión. Cada alerta muestra como máximo sus seis grupos de evidencias más frecuentes, y si un incidente tiene más de 25 alertas, las restantes se resumen en conteos por categoría. Acompañar la alerta con contexto adicional sigue la práctica de los estudios que interpretan alertas con LLM [15].

El expediente se completa con la salida de dos herramientas. La primera traduce cada técnica de MITRE ATT&CK a su nombre y táctica. La segunda, la base de conocimiento, informa para cada detector, título y categoría el número de alertas calificadas en las organizaciones de desarrollo y el porcentaje de ellas que terminó en TP, BP o FP. Aprender de alertas ya calificadas y de la experiencia de los analistas es la base de varios enfoques de triaje [6][13]. Esta base se calcula solo con incidentes de las organizaciones de desarrollo, excluidas las organizaciones de las que proviene la muestra de desarrollo, y solo informa porcentajes cuando hay al menos 20 alertas calificadas. Así, ninguna estadística contiene información de las organizaciones evaluadas. Las entradas de esta herramienta se identifican con el código del detector, del título o de la categoría; esos códigos no forman parte de los identificadores citables.

## 3.6 Sistema multiagente

El sistema divide el triaje en etapas con responsabilidades acotadas, como proponen las arquitecturas de agentes para el SOC [8][11][12]. La especialización reduce la carga de cada *prompt*, permite evaluar cada etapa por separado y deja un registro del razonamiento. La Figura 1 muestra la arquitectura.

![Figura 1. Arquitectura del sistema multiagente. El agente de clasificación recibe también el expediente y las salidas de las herramientas; el orquestador escala el incidente si la confianza es menor que 0,60 o si el agente de priorización lo decide.](fig_arquitectura.png){width=15.5cm}

- **Orquestador.** Es código determinista. Entrega el expediente y las salidas de las herramientas a los agentes, los activa en orden, valida cada salida contra su esquema JSON y, si no lo cumple, pide una nueva generación hasta tres veces; si el fallo persiste, el triaje se registra como no procesado. También mide el tiempo de cada etapa y escala el incidente a revisión humana si el agente de priorización lo decide o si la confianza de la clasificación es menor que 0,60, como en los esquemas de decisión colaborativa en los que el sistema delega en el analista los casos inciertos [5][9]. La misma regla de escalamiento se aplica al control.
- **Contextualización.** Agente LLM que resume el incidente, ordena las tácticas observadas en la cadena de ataque, separa las señales que apoyan una actividad maliciosa de las que apoyan una actividad legítima o una detección errónea, e interpreta el historial de los detectores. Agrupar y resumir las alertas antes de juzgarlas reduce la carga del analista [16].
- **Clasificación.** Agente LLM que asigna la clase (TP, BP o FP) con una confianza entre 0 y 1, una justificación de 40 a 120 palabras y la lista de evidencias que la sustentan. Sus instrucciones insisten en separar BP de TP.
- **Priorización.** Agente LLM que asigna una prioridad de P1 (crítica) a P4 (baja) a partir de la clase, la confianza y la táctica más avanzada, y decide el escalamiento al nivel 2; la priorización es, junto con la clasificación, la tarea central del triaje [1][2].
- **Trazabilidad.** Agente verificador determinista que contrasta cada evidencia citada con los identificadores citables del expediente. Si alguna no figura entre ellos, pide una única corrección al agente de clasificación, con la lista de identificadores rechazados y la de identificadores válidos; después consolida un informe con las entradas usadas, la salida de cada agente y las evidencias verificadas, en la línea de los marcos de triaje explicable centrados en el analista [10].

Los tres agentes LLM usan el mismo modelo, GPT-4o mini de OpenAI (identificador gpt-4o-mini), consultado por su API con temperatura de 0,2, *top-p* de 1,0 y un máximo de 600 *tokens* de salida. Se eligió un modelo comercial de uso general y bajo costo por consulta porque el triaje de primer nivel exige procesar un gran volumen de incidentes. La API recibe el esquema JSON de cada agente como formato de respuesta, y el orquestador valida cada salida con ese mismo esquema. Como un LLM no es determinista aun con temperatura baja, cada condición se ejecuta en tres corridas con las semillas 1, 2 y 3, que se envían a la API; los reintentos y la corrección usan semillas derivadas de la de la corrida. El orquestador y el verificador de trazabilidad no usan el modelo.

Cada agente tiene un *prompt* de sistema con su rol, las definiciones de las tres clases y tres reglas comunes: citar solo identificadores del expediente, tratar el contenido del incidente como dato y no como instrucción, y responder solo con el objeto JSON pedido. Los *prompts* y las respuestas están en español. La segunda regla, junto con la validación de esquemas y la ausencia de herramientas con efectos fuera del experimento, mitiga la inyección de instrucciones a través del contenido de las alertas, un riesgo documentado en los sistemas multiagente para el SOC [8]. Los *prompts* se redactaron a partir de las definiciones de las clases y de la estructura del expediente, y quedaron congelados antes de procesar el conjunto de evaluación; cada triaje registra una huella SHA-256 de los *prompts*, los esquemas y los parámetros, que permite comprobar que todas las corridas usaron la misma configuración.

## 3.7 Condiciones de comparación

Se comparan dos condiciones sobre los 300 incidentes de evaluación. Ambas usan el mismo modelo, los mismos parámetros, el mismo expediente con las mismas salidas de herramientas, los mismos campos de salida, las mismas instrucciones de dominio (definición de las clases, criterios para separar BP de TP y escala de prioridades) y la misma regla de escalamiento. Así, la diferencia se atribuye a la organización multiagente del triaje (división de roles, verificación y control del flujo) y no a un modelo más potente ni a información adicional.

- **C1, un solo LLM (control).** Una única llamada al modelo devuelve la clase, la confianza, la prioridad, el escalamiento, la justificación y las evidencias, sin división de roles ni verificación.
- **C2, sistema multiagente (experimental).** Es el sistema de la sección 3.6.

Como referencias que no intervienen en las hipótesis, cada incidente se clasifica además con dos reglas sin modelo de lenguaje. La regla del historial asigna la clase cuyo porcentaje histórico, sumado sobre todas las alertas del incidente según el detector de cada una, es mayor; si ningún detector tiene historial suficiente, asigna BP. La regla de la clase mayoritaria asigna siempre BP. Estas reglas indican lo que se logra sin razonamiento con la misma información, del mismo modo que los clasificadores tradicionales con los que se comparan los LLM en [3].

## 3.8 Instrumento y métricas

El registro de observación estructurada guarda una fila por incidente, condición y corrida con la clase asignada, la confianza, la prioridad, el escalamiento, los tiempos por etapa, las llamadas al modelo, los *tokens*, los reintentos, la justificación y las evidencias citadas. A partir de él se calculan los indicadores de la VD y los de la VI:

$$P_{k} = \frac{n_{kk}}{\sum_{i} n_{ik}}, \qquad R_{k} = \frac{n_{kk}}{\sum_{j} n_{kj}}, \qquad F1_{\text{macro}} = \frac{1}{3}\sum_{k} \frac{2 P_{k} R_{k}}{P_{k} + R_{k}}, \qquad TH = \frac{3\,600 \cdot N}{\sum_{i} t_i}$$

donde $P_k$ y $R_k$ son la precisión y la exhaustividad de la clase $k$, $n_{kj}$ es el número de incidentes de clase real $k$ asignados a la clase $j$, $TH$ es el número de incidentes por hora y $t_i$ el tiempo en segundos entre la recepción del expediente y la decisión final. Se informa además la tasa de omisión de amenazas (TOA), la proporción de TP reales asignados a BP o FP o no procesados, porque es el error de mayor riesgo operativo.

La clase de cada incidente es la moda de las tres corridas (en caso de empate, la de mayor confianza media), los indicadores binarios se asignan por mayoría y el tiempo es la mediana de las corridas. Un triaje no procesado se conserva en el análisis como un error: no acierta la clase y no es trazable. Este criterio es conservador con la condición que falla y evita que los fallos del sistema mejoren sus indicadores. Se informan también la media y la desviación estándar de cada indicador entre corridas.

La trazabilidad precisa la definición de la Tabla 2 con tres criterios que se verifican de forma automática en todos los triajes: (1) la justificación tiene al menos 20 palabras y nombra la clase asignada; (2) cita al menos una evidencia; y (3) todas las evidencias citadas son identificadores citables del expediente. Una decisión es trazable ($T_i = 1$) si cumple los tres. Estos criterios comprueban que la decisión está documentada y que sus evidencias existen; no juzgan si la justificación es correcta, lo que requeriría una auditoría de expertos. Como la verificación de evidencias forma parte de la intervención, se informa además la trazabilidad de C2 antes de la corrección.

Los indicadores de la VI son la proporción de salidas que cumplen el esquema (SV), la proporción de evidencias citadas que son verificables (EV), el acuerdo de clase entre las tres corridas de un incidente (AC), el tiempo de respuesta (TR), los reintentos por incidente (RI), los incidentes por hora (TH) y los *tokens* por incidente (TK).

## 3.9 Procedimiento

El experimento se implementó en Python, con DuckDB para procesar el archivo completo, y siguió nueve pasos, cada uno en un programa que registra qué hace, por qué y cuántos registros afecta: (1) descarga y verificación de integridad; (2) exploración del archivo; (3) limpieza y selección de características; (4) partición y muestreo; (5) construcción de la base de conocimiento y de los expedientes; (6) piloto de funcionamiento con incidentes de desarrollo; (7) ejecución de C1 y C2 sobre el conjunto de evaluación, intercaladas por incidente en orden aleatorio para que las variaciones de latencia del servicio no favorezcan a ninguna; (8) cálculo de los indicadores; y (9) análisis estadístico.

## 3.10 Análisis estadístico

H.E.1 y H.E.3 se contrastan con la prueba de McNemar, adecuada para comparar dos clasificadores sobre los mismos casos. Sea $b$ el número de incidentes en los que solo C2 acierta (o es trazable) y $c$ el número en los que solo lo hace C1. El estadístico es $\chi^{2} = (b - c)^{2}/(b + c)$, con un grado de libertad; si $b + c < 25$, se usa la versión *mid-p* de la prueba binomial exacta. En H.E.1 la prueba se aplica al acierto por incidente; como el F1 macro no se descompone en aciertos pareados, se informa con su intervalo de confianza, y H.E.1 se considera respaldada solo si la prueba es significativa a favor de C2 y el F1 macro de C2 también supera al de C1. El tamaño del efecto es la razón $b/c$, y las diferencias de exactitud, de F1 macro y de trazabilidad se acompañan de un intervalo de confianza del 95 % por *bootstrap* pareado con 2 000 remuestreos. La exactitud de cada condición se informa con el intervalo de Wilson.

H.E.2 se contrasta con la prueba de rangos con signo de Wilcoxon sobre las diferencias $d_i = t_i^{C2} - t_i^{C1}$, porque los tiempos son asimétricos. El tamaño del efecto es la correlación biserial de rangos $r_{rb} = (W_{p} - W_{n})/(W_{p} + W_{n})$, donde $W_{p}$ y $W_{n}$ son las sumas de los rangos de las diferencias positivas y negativas; un valor negativo indicaría que C2 reduce el tiempo.

Las tres pruebas son bilaterales y el error de tipo I se controla con la corrección de Holm, con un nivel de significación de 0,05. Una hipótesis se acepta solo si su valor *p* ajustado es menor que ese nivel y el efecto tiene la dirección planteada. El análisis de sensibilidad previsto repite los contrastes en cada corrida individual, que representa el despliegue con una sola ejecución, repite el de H.E.1 en los incidentes que ninguna condición escala y calcula los intervalos con *bootstrap* por organización, porque los incidentes de una misma organización no son del todo independientes. Después de observar los resultados se añadieron análisis exploratorios, que se informan como tales: la repetición de H.E.1 sin los incidentes con triajes no procesados, la comparación de cada condición con las reglas de referencia (McNemar), la exactitud según la disponibilidad de historial del detector, la relación entre la confianza declarada y el acierto (área bajo la curva ROC), el efecto del escalamiento y el desenlace del ciclo de verificación y corrección.

## 3.11 Amenazas a la validez

La comparación entre C1 y C2 no separa el efecto de la división de roles del efecto del mayor cómputo de inferencia de C2 ni de la redacción distinta de los *prompts* de cada agente; por eso el costo se informa en llamadas y *tokens*. La verificación de evidencias favorece a C2 en el tercer criterio de trazabilidad por diseño, porque forma parte de la intervención evaluada. El tiempo medido es tiempo de cómputo: depende de la latencia del servicio del modelo en el momento de la ejecución y no incluye el tiempo que un analista dedicaría a revisar la decisión automática.

La selección de características usó mediciones del archivo completo, que incluye las organizaciones de evaluación; como solo se emplearon para decidir qué columnas conservar, el riesgo de fuga es menor. La base de conocimiento usa alertas de todo el periodo del archivo, de modo que el historial de un detector puede incluir calificaciones posteriores al incidente evaluado, información de la que un SOC real no dispondría; la partición por organización evita la fuga entre organizaciones, pero no este sesgo temporal. Las etiquetas de GUIDE reflejan el criterio de cada organización, y la definición de BP no está estandarizada entre ellas [19]. Los datos provienen de clientes de un solo proveedor, lo que limita la validez externa. Por último, GUIDE es público desde 2024 y podría formar parte del preentrenamiento del modelo; el riesgo es bajo porque los campos están seudonimizados y la etiqueta nunca se muestra, pero no puede descartarse. El conjunto de datos es público y está seudonimizado, de modo que el estudio no trata datos personales.


# 4 Desarrollo

## 4.1 Preparación de los datos

El archivo GUIDE_Train.csv tiene 9 516 837 evidencias en 45 columnas, que forman 1 265 644 alertas y 730 778 incidentes de 5 769 organizaciones. Para procesarlo sin cargarlo completo en memoria, se convirtió a formato Parquet y se consultó con DuckDB; los pasos 1 a 5 del procedimiento se ejecutaron en unos cuatro minutos en un equipo de dos núcleos y 7 GB de memoria. La Tabla 3 muestra cuántas evidencias e incidentes quedaron después de cada paso de limpieza.

: Tabla 3: Embudo de limpieza de GUIDE_Train.

| Paso | Criterio | Evidencias | Incidentes |
|:--|:--|--:|--:|
| 0 | Archivo original | 9 516 837 | 730 778 |
| 1 | Sin filas duplicadas exactas | 9 494 278 | 730 778 |
| 2 | Marca de tiempo válida | 9 494 278 | 730 778 |
| 3 | Con una sola calificación de triaje | 9 442 956 | 707 108 |
| 4 | Con 50 alertas o menos | 6 707 032 | 705 908 |

Se eliminaron 22 559 filas duplicadas (0,24 %), que inflaban los conteos de sus incidentes. Todas las marcas de tiempo fueron válidas. Se excluyeron 23 670 incidentes sin calificación (3,2 %); ningún incidente tenía más de una calificación, lo que confirma que la etiqueta pertenece al incidente. El criterio de tamaño excluyó 1 200 incidentes (el 0,17 % de los incidentes, pero el 29 % de las evidencias): el 87,6 % de los incidentes tiene una sola alerta y el 99,8 % tiene 50 o menos, aunque el mayor llega a 5 371. Entre los excluidos predominan los TP (536, el 44,7 %, frente al 20,5 % de la población), de modo que los resultados se refieren a incidentes de hasta 50 alertas. La población elegible quedó formada por 705 908 incidentes de 5 339 organizaciones, con 346 179 BP (49,0 %), 214 679 FP (30,4 %) y 145 050 TP (20,5 %). Este desequilibrio entre clases justifica informar el F1 macro, que pondera por igual a la clase minoritaria TP.

La exploración mostró, además, que en las columnas de entidades el valor más frecuente aparece en la mayoría de las filas (por ejemplo, un mismo código de dispositivo en el 96,2 % y uno de dirección IP en el 77,1 %). Ese código no es una entidad real, sino la forma en que el archivo seudonimizado representa la ausencia de entidad; por eso, en las 13 columnas de conteo, el valor que supera el 50 % de las filas se trató como nulo antes de contar entidades distintas.

## 4.2 Selección de características

La Tabla 4 resume la decisión sobre las 45 columnas y la evidencia que la respalda. De ellas, 3 se conservaron como clave, 7 como entrada, 2 como historial, 13 como conteo y 1 como etiqueta, y se eliminaron 19.

: Tabla 4: Selección de características y evidencia empírica.

| Rol | Columnas | Evidencia |
|:--|:--|:--|
| Entrada | Category, EntityType, EvidenceRole, MitreTechniques, SuspicionLevel, LastVerdict, Timestamp | Texto interpretable. Category (20 valores) y EntityType (33) no tienen nulos y se asocian con la etiqueta (V = 0,31); MitreTechniques está en el 42,5 % de las evidencias (V = 0,36); SuspicionLevel y LastVerdict, en el 15,2 % y el 23,5 % (V = 0,12 y 0,13) |
| Historial | DetectorId, AlertTitle | Códigos seudonimizados (unos 8 900 y 89 000 valores distintos, según un conteo aproximado) con fuerte asociación con la etiqueta (V = 0,57 y 0,52) |
| Clave | OrgId, IncidentId, AlertId | OrgId es la columna más asociada con la etiqueta (V = 0,67): cada organización califica de forma distinta, lo que justifica la partición por organización |
| Conteo | DeviceId, IpAddress, AccountSid, AccountUpn, AccountObjectId, AccountName, DeviceName, Url, Sha256, FileName, NetworkMessageId, RegistryKey, ApplicationId | Códigos seudonimizados cuyo valor dominante (63,6 % a 99,8 % de las filas) representa la ausencia de entidad |
| Etiqueta | IncidentGrade | Nula en el 0,54 % de las evidencias; única por incidente |
| Eliminadas | ActionGrouped, ActionGranular | Acciones posteriores al triaje (fuga de la etiqueta), vacías en el 99,4 % |
| Eliminadas | EmailClusterId, ThreatFamily, ResourceType, Roles, AntispamDirection | Vacías en el 97,7 % al 99,9 % de las evidencias |
| Eliminadas | Id, OSFamily, OSVersion, RegistryValueName, RegistryValueData, ApplicationName, OAuthApplicationId, FolderPath, ResourceIdName, CountryCode, State, City | Códigos sin significado para el modelo o redundantes con una columna de conteo; CountryCode, State y City (V = 0,21 a 0,22) son ubicaciones seudonimizadas cuya asociación probablemente refleja la organización y que aumentarían el riesgo de reidentificación |

Ninguna columna conservada como entrada o historial mostró una asociación con la etiqueta cercana a 1, que habría indicado una fuga. Las acciones de remediación se eliminaron por su naturaleza, aunque su asociación medida es baja (V < 0,01), porque solo existen para incidentes ya calificados. Como la V de Cramér se calculó con los 50 valores más frecuentes de cada columna, subestima la asociación de las columnas de alta cardinalidad, como DetectorId y AlertTitle. La seudonimización tiene una consecuencia directa para este estudio: el modelo no dispone del texto de los títulos de alerta ni de los nombres de los detectores, y la información interpretable del expediente se reduce a la categoría, las técnicas, el tipo y el rol de las entidades, los veredictos y el historial.

## 4.3 Partición y muestra

De las 5 339 organizaciones elegibles, 1 068 se asignaron a desarrollo, con 186 832 incidentes, y 4 271 a evaluación, con 519 076. La Tabla 5 compara la distribución de clases de cada conjunto con la de la población y con la de su grupo de organizaciones; la Figura 2 la muestra de forma gráfica.

: Tabla 5: Composición de la muestra.

| Conjunto | Organizaciones | Incidentes | TP (%) | BP (%) | FP (%) | *p* frente a la población | *p* frente a su grupo |
|:--|--:|--:|--:|--:|--:|--:|--:|
| Población elegible | 5 339 | 705 908 | 20,5 | 49,0 | 30,4 | — | — |
| Grupo de desarrollo | 1 068 | 186 832 | 15,8 | 45,3 | 38,9 | — | — |
| Grupo de evaluación | 4 271 | 519 076 | 22,3 | 50,4 | 27,3 | — | — |
| Muestra de desarrollo | 37 | 75 | 21,3 | 42,7 | 36,0 | 0,493 | 0,421 |
| Muestra de evaluación | 193 | 300 | 25,0 | 50,3 | 24,7 | 0,044 | 0,407 |

![Figura 2. Distribución de clases en la población elegible y en las muestras de desarrollo y de evaluación.](fig_distribucion_clases.png){width=14.5cm}

Ninguna muestra difiere de su grupo de organizaciones (*p* > 0,40, prueba chi-cuadrado). La muestra de evaluación sí difiere de la población (*p* = 0,044) porque la partición por organización dejó en el grupo de evaluación una mezcla de clases distinta: organizaciones grandes con muchos FP quedaron en desarrollo, que tiene un 38,9 % de FP frente al 27,3 % del grupo de evaluación. La muestra de evaluación tiene, por ello, algo más de TP (25,0 %) y menos FP (24,7 %) que la población. La comparación pareada entre condiciones no se ve afectada por esa mezcla, porque ambas se evalúan sobre los mismos incidentes, pero la exactitud y el F1 macro deben leerse con ella. La muestra de evaluación proviene de 193 organizaciones; el 88,0 % de sus incidentes tiene una sola alerta, y la media es de 1,44 alertas y 9,6 evidencias por incidente.

## 4.4 Base de conocimiento y expedientes

La base de conocimiento se calculó con 79 806 alertas de 59 409 incidentes de las organizaciones de desarrollo, excluidas las 37 que aportan incidentes a la muestra de desarrollo. Contiene 1 373 detectores, 6 797 títulos y 19 categorías; de ellos, 246 detectores, 366 títulos y 17 categorías tienen al menos 20 alertas calificadas y, por tanto, informan porcentajes. La tabla de MITRE ATT&CK, generada con la colección oficial de técnicas empresariales, tiene 867 técnicas y cubrió todas las técnicas de la muestra.

Se construyeron 375 expedientes, uno por incidente de la muestra. Su tamaño, estimado como el número de caracteres dividido entre cuatro, tiene una mediana de 248 *tokens*, un percentil 95 de 554 y un máximo de 3 124, muy por debajo de la ventana de contexto del modelo. Ningún incidente de la muestra superó el límite de 25 alertas en detalle (el mayor tiene 22), y el límite de seis grupos de evidencias por alerta afectó a 39 de sus 534 alertas (7,3 %). En 216 de los 300 incidentes de evaluación (72,0 %) al menos un detector tiene historial suficiente; en los 84 restantes (28,0 %), la herramienta de historial solo informa los porcentajes de la categoría de cada alerta.

## 4.5 Implementación y ejecución

El sistema se implementó en un programa de Python que se comunica con el modelo por una API compatible con la de OpenAI, a la que entrega el esquema JSON de cada agente; el mismo programa admite un modelo local servido con Ollama. El orquestador y el verificador de trazabilidad son funciones de ese programa, y el cálculo de indicadores y el análisis estadístico son programas independientes que leen una única configuración. Antes de usar el modelo, una prueba con un generador de respuestas válidas al azar recorrió los pasos de triaje, cálculo de indicadores, análisis estadístico y figuras sin errores; sus salidas no forman parte de los resultados.

El triaje se ejecutó el 5 de noviembre de 2026. Un piloto de 16 triajes sobre cinco incidentes de la muestra de desarrollo comprobó la integración con la API. Los *prompts* no se modificaron después del piloto ni se ajustaron con datos, de modo que la evaluación mide el sistema tal como fue diseñado. A continuación se procesó el conjunto de evaluación: 1 800 triajes (300 incidentes, dos condiciones y tres corridas) en 3 horas y 11 minutos, todos con el mismo modelo y la misma huella de configuración. De ellos, 1 736 concluyeron con una decisión; los 64 no procesados pertenecen a C2 y se analizan en la sección 5.4. El código, los *prompts*, los esquemas, la configuración, los expedientes de la muestra y el registro de los 1 800 triajes se publican en el repositorio del estudio.


# 5 Resultados

## 5.1 Muestra de evaluación y reglas de referencia

Los 300 incidentes de evaluación comprenden 151 BP (50,3 %), 75 TP (25,0 %) y 74 FP (24,7 %). Las categorías presentes en más incidentes son InitialAccess (128 incidentes), SuspiciousActivity (59), CommandAndControl (43) y Exfiltration (32). El 34,7 % de los incidentes tiene al menos una técnica de MITRE ATT&CK y el 29,3 %, al menos una evidencia con veredicto automático; en el 46,0 % no hay técnicas ni veredictos, y la decisión depende de la categoría, del tipo y rol de las entidades y del historial.

La regla del historial alcanzó una exactitud del 50,0 % y un F1 macro del 47,7 %, e identificó 30 de los 75 TP. Su exactitud es similar a la de asignar siempre BP (50,3 %), pero su F1 macro es mucho mayor (47,7 % frente a 22,3 %), porque el historial permite reconocer una parte de los TP y de los FP. En los 216 incidentes con historial de detector la regla acierta el 45,8 %. El historial de otras organizaciones es, por tanto, informativo pero insuficiente para el triaje de una organización nueva, y fija el punto de partida con el que deben compararse las condiciones basadas en LLM.

## 5.2 Precisión de clasificación

La Tabla 6 presenta el desempeño global de las dos condiciones y de las dos reglas de referencia; la Tabla 7, el desempeño por clase, y la Figura 3, las matrices de confusión.

: Tabla 6: Desempeño de clasificación en el conjunto de evaluación (n = 300). Intervalos de confianza del 95 %: de Wilson para la exactitud y por *bootstrap* para el F1 macro.

| Condición | Aciertos | Exactitud (%) | F1 macro (%) | TOA (%) |
|:--|--:|:-:|:-:|--:|
| Siempre BP (referencia) | 151 | 50,3 [44,7; 56,0] | 22,3 [20,6; 23,9] | 100,0 |
| Regla del historial (referencia) | 150 | 50,0 [44,4; 55,6] | 47,7 [41,7; 53,4] | 60,0 |
| C1: un solo LLM (control) | 104 | 34,7 [29,5; 40,2] | 31,9 [27,0; 37,0] | 86,7 |
| C2: sistema multiagente | 127 | 42,3 [36,9; 48,0] | 38,8 [33,1; 44,5] | 82,7 |

: Tabla 7: Precisión (P), exhaustividad (R) y F1 por clase.

| Clase (incidentes) | Regla: P | R | F1 | C1: P | R | F1 | C2: P | R | F1 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| TP (75) | 0,441 | 0,400 | 0,420 | 0,167 | 0,133 | 0,148 | 0,277 | 0,173 | 0,213 |
| BP (151) | 0,600 | 0,556 | 0,577 | 0,526 | 0,338 | 0,411 | 0,537 | 0,530 | 0,533 |
| FP (74) | 0,391 | 0,486 | 0,434 | 0,301 | 0,581 | 0,396 | 0,382 | 0,459 | 0,417 |

![Figura 3. Matrices de confusión de la regla del historial, de C1 y de C2 (n = 300). NP: incidentes no procesados por la mayoría de las corridas.](fig_matrices_confusion.png){width=15.5cm}

El sistema multiagente clasificó correctamente 127 incidentes y el LLM único, 104. La exactitud pasó del 34,7 % al 42,3 %, una diferencia de 7,7 puntos porcentuales (IC 95 %: 2,7 a 13,0), y el F1 macro, del 31,9 % al 38,8 % (diferencia de 6,9 puntos; IC 95 %: 2,1 a 12,0). C2 acertó 45 incidentes en los que C1 falló y falló 22 que C1 acertó, una razón de 2,05 ($\chi^{2}$ = 7,90; *p* = 0,005); la proporción de pares discordantes, 0,22, fue cercana a la supuesta al calcular la muestra. La mejora se concentra en la clase BP, cuya exhaustividad sube de 0,338 a 0,530 (de 51 a 80 de los 151 BP). C1 asignó la clase FP a 143 incidentes (47,7 %), casi el doble de su frecuencia real, mientras que C2 asignó BP a 149 (49,7 %), una proporción cercana a la real.

La mejora es relativa a un control débil. La exactitud de C1 no se distingue de la que daría asignar las clases al azar con igual probabilidad (33,3 %, dentro de su intervalo de confianza). Ambas condiciones quedan en el nivel bajo de la Tabla 2 (menos del 70 %) y por debajo de las dos reglas de referencia: frente a la regla del historial, C1 acierta 25 incidentes que la regla falla y falla 71 que la regla acierta (*p* < 0,001), y C2, 17 y 40 (*p* = 0,002); frente a asignar siempre BP, las diferencias también son significativas (*p* < 0,001 y *p* = 0,027). La detección de amenazas es el punto más débil: C1 reconoce 10 de los 75 TP y C2, 13, lo que equivale a una omisión del 86,7 % y del 82,7 %, frente al 60,0 % de la regla. Los 15 incidentes que C2 no procesó en al menos dos de sus tres corridas (5 TP, 6 BP y 4 FP) cuentan como errores.

## 5.3 Eficiencia temporal

El tiempo de triaje por incidente tuvo una mediana de 2,79 s en C1 (media de 2,85 s; desviación estándar de 0,44 s) y de 8,94 s en C2 (media de 9,06 s; desviación estándar de 1,19 s). C2 fue más lento en los 297 incidentes con tiempo en ambas condiciones, con una mediana de las diferencias de 6,03 s (IC 95 %: 5,90 a 6,17); tardó, por tanto, 3,2 veces más ($W_{n}$ = 0; $r_{rb}$ = +1,00; *p* < 0,001). Tres incidentes no tienen tiempo en C2 porque ninguno de sus tres triajes concluyó. La Figura 4 muestra la distribución del tiempo y su reparto entre los agentes: la contextualización consume el 49 % del tiempo de C2 (4,50 s), la clasificación el 31 % (2,84 s) y la priorización el 20 % (1,82 s); la verificación determinista de evidencias es instantánea.

![Figura 4. (a) Tiempo de triaje por incidente en C1 y C2 (mediana de las tres corridas). (b) Tiempo medio de cada agente de C2 en los triajes procesados.](fig_tiempos.png){width=15.5cm}

Expresado en la unidad de la Tabla 2, el tiempo medio es de 0,05 min por incidente en C1 y de 0,15 min en C2: ambas condiciones quedan en el nivel alto de eficiencia (menos de 5 min). El mayor tiempo de C2 corresponde a sus tres llamadas al modelo por incidente, frente a una de C1, y a un consumo de 4 143 *tokens* por triaje, frente a 1 419. El programa no conservó el tiempo ni los *tokens* de los triajes no procesados, de modo que el costo de C2 está ligeramente subestimado.

## 5.4 Trazabilidad

La Tabla 8 presenta el cumplimiento de los criterios de trazabilidad. En C1 las 300 decisiones son trazables; en C2 lo son 283 (94,3 %). Ningún incidente es trazable solo en C2 y 17 lo son solo en C1 (*p* < 0,001), una diferencia de 5,7 puntos porcentuales en contra del sistema multiagente (IC 95 %: 3,3 a 8,3). Ambas condiciones quedan en el nivel alto de la Tabla 2 (más del 85 %). De los 17 incidentes no trazables de C2, 15 son los no procesados y 2 tienen justificaciones que no nombran la clase asignada.

: Tabla 8: Cumplimiento de los criterios de trazabilidad por incidente (n = 300, mayoría de las corridas) y por triaje (n = 900 por condición).

| Criterio | C1: incidentes (%) | C2: incidentes (%) | C1: triajes | C2: triajes |
|:--|--:|--:|--:|--:|
| 1. Justificación de 20 palabras o más que nombra la clase | 100,0 | 94,3 | 898 | 830 |
| 2. Cita al menos una evidencia | 100,0 | 95,0 | 900 | 836 |
| 3. Todas las evidencias citadas son verificables | 100,0 | 95,0 | 900 | 836 |
| Decisión trazable (criterios 1 a 3) | 100,0 | 94,3 | 898 | 830 |

El registro permite reconstruir el origen de la diferencia, que no está en evidencias inventadas. En los 900 triajes de C1 y en los 836 triajes procesados de C2, todas las evidencias citadas en la decisión final existen en el expediente. El verificador de trazabilidad activó la corrección en 70 de los 900 triajes de C2 (7,8 %). En los seis triajes en los que la corrección concluyó, los diez identificadores rechazados eran claves de la herramienta de historial (el código de un detector, de un título o de una categoría): información que forma parte del expediente y que las instrucciones piden ponderar, pero que no figura en la lista de identificadores citables. El agente de contextualización citó esas claves como evidencia de sus señales en 197 de los 836 triajes procesados (23,6 %); cuando el agente de clasificación las repitió en su propia lista de evidencias, el verificador activó la corrección.

En las otras 64 activaciones, la respuesta corregida expresó la confianza en escala porcentual (por ejemplo, 80,7 en lugar de 0,807), con un valor que coincide con un porcentaje del historial; la salida incumplió el esquema en el intento inicial y en los tres reintentos, y el triaje quedó como no procesado. Esos 64 triajes afectan a 46 incidentes: 31 con un triaje no procesado, 12 con dos y 3 con los tres. La corrección tampoco fue eficaz cuando concluyó: de los seis triajes corregidos, solo uno quedó trazable, porque en los otros cinco la nueva justificación, más breve (38 palabras de media frente a 66), dejó de nombrar la clase. Por eso la trazabilidad de C2 antes de la corrección es la misma que después (94,3 %).

## 5.5 Contraste de las hipótesis

La Tabla 9 resume el contraste. Los tres valores *p* son menores que 0,05 después de la corrección de Holm, pero solo en H.E.1 el efecto tiene la dirección planteada.

: Tabla 9: Contraste de las hipótesis (n = 300 incidentes; pruebas bilaterales con corrección de Holm). En H.E.2, la diferencia es la mediana de las diferencias pareadas (n = 297).

| Hipótesis | Indicador | C1 | C2 | Diferencia [IC 95 %] | Prueba | *p* (Holm) | Decisión |
|:--|:--|--:|--:|:-:|:--|--:|:--|
| H.E.1 | Exactitud (%) | 34,7 | 42,3 | +7,7 [+2,7; +13,0] | McNemar: *b* = 45, *c* = 22 | 0,005 | Se acepta |
| | F1 macro (%) | 31,9 | 38,8 | +6,9 [+2,1; +12,0] | | | |
| H.E.2 | Tiempo por incidente (s, mediana) | 2,79 | 8,94 | +6,03 [+5,90; +6,17] | Wilcoxon: $r_{rb}$ = +1,00 | < 0,001 | No se acepta |
| H.E.3 | Decisiones trazables (%) | 100,0 | 94,3 | −5,7 [−8,3; −3,3] | McNemar *mid-p*: *b* = 0, *c* = 17 | < 0,001 | No se acepta |

Se acepta H.E.1: el sistema multiagente mejora la precisión de clasificación respecto de un solo LLM. No se aceptan H.E.2 ni H.E.3: el sistema multiagente tarda más y produce menos decisiones trazables que el control. La hipótesis general queda, por tanto, parcialmente respaldada. El sistema multiagente no cambió el nivel de ninguna dimensión de la Tabla 2: en ambas condiciones la precisión de clasificación es baja, y la eficiencia temporal y la trazabilidad, altas.

## 5.6 Análisis de sensibilidad

La Tabla 10 repite el contraste de H.E.1 en distintos subconjuntos. En las tres corridas individuales C2 supera a C1 (entre 4,3 y 7,7 puntos), pero la diferencia solo es significativa en la tercera; con una sola ejecución por incidente, la mejora no está garantizada, y es el voto de las tres corridas el que la estabiliza. Entre corridas, la exactitud es de 35,4 ± 1,0 % en C1 y de 41,2 ± 2,1 % en C2 (media ± desviación estándar). El intervalo de la diferencia de exactitud con *bootstrap* por organización (1,8 a 13,2 puntos) también excluye el cero.

: Tabla 10: Sensibilidad del contraste de H.E.1 (exactitud, %). Los análisis marcados con un asterisco son exploratorios.

| Análisis | n | C1 | C2 | *b* | *c* | *p* |
|:--|--:|--:|--:|--:|--:|--:|
| Corrida 1 | 300 | 36,0 | 40,3 | 49 | 36 | 0,159 |
| Corrida 2 | 300 | 34,3 | 39,7 | 42 | 26 | 0,052 |
| Corrida 3 | 300 | 36,0 | 43,7 | 48 | 25 | 0,007 |
| Con decisión no escalada en ambas condiciones | 75 | 62,7 | 61,3 | 1 | 2 | 0,625 |
| Sin incidentes con triajes no procesados* | 254 | 31,9 | 42,9 | 40 | 12 | < 0,001 |
| Con historial de detector* | 216 | 37,5 | 38,0 | 18 | 17 | 0,866 |
| Sin historial de detector* | 84 | 27,4 | 53,6 | 27 | 5 | < 0,001 |

Al retirar los 46 incidentes con algún triaje no procesado, la diferencia a favor de C2 aumenta (31,9 % frente a 42,9 %), lo que confirma que tratar esos triajes como errores es conservador. En los 75 incidentes cuya decisión no se escala en ninguna de las dos condiciones, ambas aciertan por igual (62,7 % y 61,3 %; *p* = 0,625): la ventaja de C2 se produce en los incidentes que alguna de las dos condiciones escala. En H.E.3, la trazabilidad de C2 es menor en las tres corridas (93,0 %, 92,3 % y 91,3 %, frente a 100,0 %, 99,7 % y 99,7 % de C1).

## 5.7 Análisis complementario

**Historial del detector.** La Figura 5 separa los incidentes según tengan o no un detector con historial suficiente. Cuando lo tienen, las dos condiciones son equivalentes (37,5 % y 38,0 %; *p* = 0,866) y quedan por debajo de la regla (45,8 %). Toda la ventaja de C2 proviene de los 84 incidentes sin historial de detector, en los que el expediente solo informa los porcentajes históricos de la categoría de cada alerta. En 76 de esos 84 incidentes la clase más frecuente de la categoría es BP. C2 asignó la clase más frecuente de la categoría en el 85,7 % de ellos y C1, en el 33,3 %; una regla que asignara esa clase acertaría el 53,6 %, lo mismo que C2. En el conjunto de la muestra, la clase de C2 coincide con la de la regla del historial en el 73,0 % de los incidentes (kappa de 0,58), y la de C1, en el 53,3 % (kappa de 0,29). La ganancia del sistema multiagente consiste, por tanto, en seguir con más fidelidad las frecuencias históricas cuando falta información específica; en ningún subgrupo una condición basada en LLM supera a la regla.

![Figura 5. Exactitud de la regla del historial, de C1 y de C2 en todos los incidentes y según la disponibilidad de historial del detector. Las barras de error son intervalos de Wilson del 95 %.](fig_exactitud_subgrupos.png){width=14.5cm}

**Confianza y escalamiento.** La confianza declarada por C1 distingue sus aciertos de sus errores (área bajo la curva ROC de 0,72): la exactitud crece del 18,6 % en los triajes con confianza de 0,50 o menos al 85,4 % en los de confianza mayor que 0,80 (Figura 6). En el 28,9 % de los triajes de C1, la confianza es idéntica a un porcentaje del historial del expediente, lo que indica que el modelo la copia de esa tabla en lugar de estimarla. La confianza de C2 se concentra entre 0,51 y 0,80 (el 91,1 % de los triajes) y no distingue aciertos de errores (área de 0,52).

![Figura 6. Exactitud de los triajes procesados según la confianza declarada por el modelo. AUC: área bajo la curva ROC de la confianza como predictor del acierto.](fig_confianza.png){width=14.5cm}

Esta diferencia se traslada al escalamiento. C1 escaló el 58,0 % de los incidentes, sobre todo por la regla de confianza menor que 0,60, y acertó el 57,1 % de los 126 que no escaló, frente al 18,4 % de los escalados. C2 escaló el 44,7 % y acertó por igual los 151 que decidió sin escalar (45,0 %) y los que escaló (44,0 %): su escalamiento no separa las decisiones dudosas. En ninguna condición el escalamiento protege lo suficiente frente a la omisión de amenazas: de los 75 TP, C1 escaló 42 y cerró 33 como BP o FP sin escalarlos; C2 escaló 40, cerró 30 sin escalarlos y no procesó 5. La prioridad asignada tampoco separa los TP del resto (área bajo la curva ROC de 0,51 en C1 y de 0,56 en C2).

**Consistencia y costo.** La Tabla 11 reúne los indicadores de la variable independiente. C1 asignó la misma clase en las tres corridas al 81,3 % de los incidentes y C2, al 60,7 % (70,5 % en los 254 incidentes sin triajes no procesados); el acuerdo entre pares de corridas, medido con el coeficiente kappa, fue de 0,76 a 0,85 en C1 y de 0,52 a 0,62 en C2. El sistema multiagente es, pues, menos reproducible, además de requerir el triple de llamadas y 2,9 veces más *tokens*.

: Tabla 11: Indicadores de la variable independiente (triajes procesados; 900 triajes por condición).

| Indicador | C1 | C2 |
|:--|--:|--:|
| Triajes procesados | 900 | 836 |
| SV: salidas que cumplen el esquema (%) | 100,0 | 99,8 |
| SV con las salidas de los triajes no procesados (%) | 100,0 | 91,0 |
| EV: evidencias citadas verificables (%) | 100,0 | 100,0 |
| AC: incidentes con la misma clase en las tres corridas (%) | 81,3 | 60,7 |
| TR: tiempo de respuesta por triaje (s), media (desviación estándar) | 2,91 (0,66) | 9,22 (1,83) |
| RI: reintentos por triaje | 0,000 | 0,007 |
| TH: incidentes por hora | 1 237 | 390 |
| TK: *tokens* por triaje (entrada + salida) | 1 419 (1 277 + 142) | 4 143 (3 682 + 462) |
| Llamadas al modelo por triaje | 1,00 | 3,01 |


# 6 Discusión

## 6.1 Qué aporta la organización multiagente

La respuesta a la pregunta de investigación es matizada. Con el mismo modelo y la misma información, repartir el triaje entre agentes especializados mejoró la exactitud en 7,7 puntos y el F1 macro en 6,9. La diferencia es significativa con el voto de tres corridas y se mantiene al cambiar el tratamiento de los triajes no procesados y al agrupar por organización, aunque con una sola corrida no siempre alcanza la significación. Sin embargo, el análisis exploratorio por subgrupos indica de dónde procede esa mejora: no de un mejor razonamiento sobre las evidencias del incidente, sino de un uso más fiel de las frecuencias históricas. Cuando el expediente solo ofrece los porcentajes de la categoría, el sistema multiagente asigna casi siempre la clase más frecuente, mientras que el LLM único se aparta de ella y su exactitud en esos incidentes (27,4 %) no supera la del azar. Una explicación coherente con el diseño es que el agente de contextualización entrega al de clasificación una síntesis explícita del historial, mientras que el LLM único debe extraer esa señal del expediente completo en una sola llamada. Además, el esquema de salida pide la clase antes que la justificación, de modo que el LLM único decide antes de argumentar; en el sistema multiagente, la contextualización cumple la función de un razonamiento previo. Cuando hay historial del detector, las dos condiciones rinden igual.

Ninguna condición basada en LLM alcanza a la regla que elige la clase con mayor porcentaje histórico, y ambas quedan por debajo de asignar siempre la clase mayoritaria. Tres factores lo explican. El primero es la información disponible: la seudonimización de GUIDE elimina el texto de los títulos de alerta y los nombres de los detectores, que es precisamente el material que un LLM sabe interpretar, y en el 46,0 % de los incidentes no hay técnicas ni veredictos. El segundo es la naturaleza de la etiqueta: la calificación depende de la práctica de cada organización (el identificador de la organización es la columna más asociada con la etiqueta), y los autores de GUIDE informan, con datos de varias regiones, un F1 macro medio de 0,87 para un modelo supervisado que incluye entre sus variables el identificador de la organización y el del detector [19], es decir, que aprende cómo califica cada cliente. El escenario de este estudio, una organización nueva sin antecedentes, retira esa información por diseño. El tercero es el modo en que el modelo usa los porcentajes: los menciona en más del 90 % de las justificaciones, pero no siempre elige la clase más probable. En un incidente cuyo detector tenía un historial de 47,1 % de TP, 30,6 % de BP y 22,3 % de FP, por ejemplo, el LLM único asignó FP con una confianza de 0,22 y citó ese 22,3 % como razón.

Estos resultados concuerdan con los de Rieger et al. [3], para quienes los clasificadores ligeros igualan o superan a los LLM en la clasificación de alertas estructuradas, y delimitan el alcance de los resultados favorables de otros estudios. El 94,1 % de acuerdo con analistas que informan Kumar y Khan [12] se obtuvo en una sola organización, con herramientas que consultan sus sistemas y una memoria de sus triajes anteriores, y Schärmer et al. [15] observan que la clasificación mejora cuando el modelo recibe registros, configuración y ejemplos. El presente estudio muestra el caso opuesto: sin texto interpretable ni contexto de la organización, ni un LLM ni un sistema de agentes LLM alcanzan una exactitud útil, por lo que el desempeño de estos sistemas no debe extrapolarse de un entorno a otro.

## 6.2 Tiempo, consistencia y confianza

El sistema multiagente tarda 3,2 veces más que el control y consume 2,9 veces más *tokens*, de modo que la hipótesis de eficiencia no se sostiene frente a un solo LLM. En términos operativos, sin embargo, el tiempo no es el factor limitante: unos 9 segundos por incidente están muy por debajo del umbral de 5 minutos de la Tabla 2 y de los tiempos de triaje manual que informa la literatura, que van de decenas de segundos [10] a decenas de minutos por alerta [12]. La limitación está en la exactitud, no en la velocidad.

La división en agentes tuvo dos costos menos visibles. El primero es la consistencia: el sistema multiagente da la misma clase en las tres corridas solo al 60,7 % de los incidentes, frente al 81,3 % del control, probablemente porque la variación de sus tres llamadas encadenadas se acumula. La mejora de exactitud solo es estable con el voto de tres corridas, lo que en la práctica triplica el costo. El segundo es la confianza. La del LLM único, aunque en parte copiada del historial, ordena razonablemente sus aciertos y sus errores, y permitiría automatizar solo las decisiones seguras. La del sistema multiagente no aporta esa información. Los esquemas de decisión colaborativa en los que el sistema delega en el analista los casos inciertos [5][9] dependen de esa señal, de modo que una arquitectura multiagente puede mejorar la exactitud media y, a la vez, empeorar la condición que hace segura la automatización parcial.

En ambas condiciones, más del 80 % de las amenazas reales se clasificó como benigna o como falso positivo, y entre 30 y 33 de los 75 TP se cerraron sin escalamiento. Ninguna de las dos configuraciones es apta para cerrar incidentes de forma autónoma; su uso razonable es consultivo, con el analista en el circuito y con salvaguardas que impidan descartar automáticamente los incidentes graves, como recomienda Okafor [4].

## 6.3 Trazabilidad y fallos del ciclo de verificación

La trazabilidad formal resultó fácil de obtener: el LLM único documentó todas sus decisiones con justificación y evidencias existentes sin ningún verificador, y en 1 736 triajes no se observó un solo identificador inventado. El agente de trazabilidad atendía, por tanto, un problema que no se presentó, y en cambio introdujo modos de fallo propios. El primero es un desajuste de especificación entre agentes: el de contextualización citó como evidencia claves del historial que el verificador no aceptaba, y esas citas se propagaron al de clasificación. El segundo es la fragilidad del formato: al pedir la corrección, el modelo cambió la escala de la confianza e incumplió el esquema en 64 de 70 ocasiones. El tercero es la ausencia de una degradación controlada: ante la corrección fallida, el sistema descartó la decisión ya emitida en lugar de conservarla y marcarla para revisión.

De aquí se siguen recomendaciones de diseño para los sistemas multiagente de triaje: definir un vocabulario común de identificadores citables que incluya las salidas de las herramientas, validar las salidas intermedias y no solo la final, exigir el formato de salida de manera estricta y prever respaldos que conserven la decisión anterior cuando una etapa falla. La validación de entradas y salidas entre agentes y herramientas ya se propone por razones de seguridad [8]; estos resultados indican que también es una condición de fiabilidad. Cada agente adicional añade interfaces en las que puede fallar la coordinación, y esos fallos pueden anular lo que la especialización aporta.

Conviene, además, no confundir la trazabilidad formal con la corrección. Los criterios empleados comprueban que la decisión está documentada y que sus evidencias existen, no que el razonamiento sea acertado. En el control, 196 de las 300 decisiones trazables (65,3 %) justifican una clase equivocada, y en el sistema multiagente, 157 de 283 (55,5 %). Una justificación bien formada que sostiene una decisión errónea puede inducir al analista a aceptarla, por lo que la trazabilidad solo tiene valor operativo si va acompañada de exactitud y de una confianza informativa.

## 6.4 Limitaciones

Los resultados corresponden a un solo modelo, GPT-4o mini, en una fecha determinada; modelos de mayor capacidad o ajustados al dominio podrían comportarse de otro modo. Los *prompts* se usaron tal como se diseñaron, sin optimizarlos con el conjunto de desarrollo ni añadir ejemplos, de modo que el estudio mide una configuración inicial y no el mejor desempeño alcanzable. El escenario de organización nueva y los datos seudonimizados son condiciones exigentes, que acotan por abajo lo que cabe esperar en un SOC que dispone de su propio contexto; además, los datos provienen de un solo proveedor, y la calificación de BP varía entre organizaciones [19].

El estudio no incluye una referencia de triaje manual, por lo que no cuantifica la ganancia de tiempo frente al analista, y la trazabilidad se midió con criterios formales, sin una auditoría de expertos sobre la coherencia de las justificaciones. El tiempo medido es tiempo de cómputo y depende de la latencia del servicio. El programa no conservó los contadores de los triajes no procesados, lo que subestima ligeramente el costo del sistema multiagente. Con 300 incidentes, los intervalos de confianza de la exactitud tienen una amplitud de unos 11 puntos, y la diferencia observada (7,7 puntos) es menor que la diferencia mínima relevante fijada al calcular la muestra (10 puntos), de modo que la mejora, aunque significativa, es modesta. Por último, el historial de los detectores se calculó con alertas de todo el periodo, lo que favorece por igual a la regla de referencia y a las dos condiciones.

# 7 Conclusiones y trabajo futuro

Este trabajo comparó un sistema de cinco agentes basado en LLM con un solo LLM en el triaje de 300 incidentes reales de GUIDE pertenecientes a organizaciones sin antecedentes para el sistema, con el mismo modelo, la misma información y tres corridas por condición. El sistema multiagente mejoró la precisión de clasificación (exactitud del 34,7 % al 42,3 %; F1 macro del 31,9 % al 38,8 %), por lo que se acepta H.E.1. No mejoró la eficiencia temporal, pues tardó 3,2 veces más que el control, ni la trazabilidad, que bajó del 100 % al 94,3 % por los fallos de su ciclo de verificación y corrección; no se aceptan H.E.2 ni H.E.3. La hipótesis general queda parcialmente respaldada, y el nivel de las tres dimensiones del rendimiento es el mismo con y sin el sistema multiagente: precisión baja, y eficiencia y trazabilidad altas.

El resultado más relevante para la práctica es que ninguna de las dos configuraciones supera a una regla simple basada en el historial de los detectores, y que ambas omiten más del 80 % de las amenazas reales. La ganancia del sistema multiagente se explica, según el análisis exploratorio, por un uso más fiel de las frecuencias históricas cuando falta información específica, y tiene como contrapartida menos consistencia entre corridas, una confianza que deja de distinguir aciertos de errores y nuevos puntos de fallo entre agentes. Con datos seudonimizados y sin contexto de la organización, un sistema multiagente basado en LLM no es todavía un sustituto del analista de primer nivel; puede servir como apoyo que documenta y propone, bajo supervisión humana.

El trabajo futuro seguirá cuatro líneas. La primera es corregir el ciclo de verificación con las recomendaciones de la sección 6.3, pedir el razonamiento antes de la clase y repetir la evaluación. La segunda es dotar al sistema de contexto de la organización, con memoria de los triajes ya calificados y ejemplos seleccionados, y medir cuánto se reduce la brecha con los modelos supervisados. La tercera es evaluar otros modelos, incluidos modelos abiertos ejecutados localmente, que evitan enviar datos del SOC a un servicio externo, y combinar un clasificador supervisado para la clase con agentes LLM para el contexto y la justificación. La cuarta es añadir una referencia de triaje manual y una auditoría de expertos sobre la coherencia de las justificaciones, y calibrar la confianza para que el escalamiento proteja frente a la omisión de amenazas.

# Referencias

::: {custom-style="Reference"}
[1] Malach, A., Wudali, P. N., Momiyama, S., Furukawa, J., Araki, T., Elovici, Y., & Shabtai, A. (2025). CyberShapley: Explanation, prioritization, and triage of cybersecurity alerts using informative graph representation. Computers & Security, 150, 104270. <https://doi.org/10.1016/j.cose.2024.104270>

[2] Wang, X., Yang, X., Liang, X., Zhang, X., Zhang, W., & Gong, X. (2024). Combating alert fatigue with AlertPro: Context-aware alert prioritization using reinforcement learning for multi-step attack detection. Computers & Security, 137, 103583. <https://doi.org/10.1016/j.cose.2023.103583>

[3] Rieger, M., Shah, A., Alam, A., & Hossain, M. J. (2026). Possibilities and limitations of using large language models (LLMs) for alert classification and prioritisation in security operations centers (SOCs). Expert Systems with Applications, 331, 133194. <https://doi.org/10.1016/j.eswa.2026.133194>

[4] Okafor, E. (2026). A leakage-free benchmark of offline policy learning for SOC alert triage. Machine Learning with Applications, 25, 100984. <https://doi.org/10.1016/j.mlwa.2026.100984>

[5] Tariq, S., Baruwal Chhetri, M., Nepal, S., & Paris, C. (2025). A²C: A modular multi-stage collaborative decision framework for human–AI teams. Expert Systems with Applications, 282, 127318. <https://doi.org/10.1016/j.eswa.2025.127318>

[6] Vaarandi, R., & Guerra-Manzanares, A. (2024). Stream clustering guided supervised learning for classifying NIDS alerts. Future Generation Computer Systems, 155, 231–244. <https://doi.org/10.1016/j.future.2024.02.001>

[7] Mudzakir, A., Janaprasetya, J. T. A., Kayowuan, E., Engel, V. J. L., & Saputro, B. (2025). Evaluating three large language models for security incident detection and analysis. Procedia Computer Science, 269, 465–473. <https://doi.org/10.1016/j.procs.2025.08.299>

[8] Simões, R. T. de P., Larriva-Novo, X., Sánchez-Zas, C., Villagrá, V. A., & Marín López, A. I. (2026). Design of a security framework for multi-agent systems based on model context protocol in SOC environments. Applied Sciences, 16(16), 7915. <https://doi.org/10.3390/app16167915>

[9] Baruwal Chhetri, M., Tariq, S., Singh, R., Jalalvand, F., Paris, C., & Nepal, S. (2024). Towards human-AI teaming to mitigate alert fatigue in security operations centres. ACM Transactions on Internet Technology, 24(3), 1–22. <https://doi.org/10.1145/3670009>

[10] Kazi, M., & Poinkar, S. (2026). An explainable AI based alert triage framework for security operations centres: Architecture, evaluation, and analyst centred design. InfoTech Spectrum: Iraqi Journal of Data Science, 3(2), 67–78. <https://doi.org/10.51173/ijds.v3i2.84>

[11] Ismail, Kurnia, R., Brata, Z. A., Nelistiani, G. A., Heo, S., Kim, H., & Kim, H. (2025). Toward robust security orchestration and automated response in security operations centers with a hyper-automation approach using agentic artificial intelligence. Information, 16(5), 365. <https://doi.org/10.3390/info16050365>

[12] Kumar, S., & Khan, I. (2026). Autonomous security alert triage using LLM based agentic investigation with tool augmented reasoning. International Journal of Scientific Research in Computer Science, Engineering and Information Technology, 12(2), 752–765. <https://doi.org/10.32628/CSEIT261213109>

[13] Zhong, C., Yen, J., Liu, P., & Erbacher, R. F. (2019). Learning from experts' experience: Toward automated cyber security data triage. IEEE Systems Journal, 13(1), 603–614. <https://doi.org/10.1109/JSYST.2018.2828832>

[14] Wu, S., Sun, X., Dong, E., Wang, Z., Zhao, C., & Yang, J. (2026). Alert2Vec: Eliminating alert fatigue by embedding security alerts through subgraph learning. IEEE Transactions on Dependable and Secure Computing, 23(1), 655–669. <https://doi.org/10.1109/TDSC.2025.3609834>

[15] Schärmer, A., Landauer, M., Skopik, F., Wurzenberger, M., & Squarcina, M. (2026). Let the alerts speak: LLM-based IDS alert interpretation for SOC triage. In Availability, Reliability and Security. ARES 2026 International Workshops (pp. 346–364). Springer. <https://doi.org/10.1007/978-3-032-35579-9_19>

[16] Landauer, M., Skopik, F., Wurzenberger, M., & Rauber, A. (2022). Dealing with security alert flooding: Using machine learning for domain-independent alert aggregation. ACM Transactions on Privacy and Security, 25(3), 1–36. <https://doi.org/10.1145/3510581>

[17] Ghadermazi, J., Shah, A., & Jajodia, S. (2024). A machine learning and optimization framework for efficient alert management in a cybersecurity operations center. Digital Threats: Research and Practice, 5(2), 1–23. <https://doi.org/10.1145/3644393>

[18] Vermeer, M., Kadenko, N., van Eeten, M., Gañán, C., & Parkin, S. (2023). Alert alchemy: SOC workflows and decisions in the management of NIDS rules. In Proceedings of the 2023 ACM SIGSAC Conference on Computer and Communications Security (pp. 2770–2784). <https://doi.org/10.1145/3576915.3616581>

[19] Freitas, S., Kalajdjieski, J., Gharib, A., & McCann, R. (2025). AI-driven guided response for security operation centers with Microsoft Copilot for Security. In Companion Proceedings of the ACM on Web Conference 2025 (pp. 191–200). Conjunto de datos GUIDE: <https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction>

[20] Mohammed, D., & Jamali, S. (2026). Unveiling the frontiers of cyber threat hunting: A comprehensive review of LLM-based approaches. Inteligencia Artificial, 29(78), 59–83. <https://journal.iberamia.org/index.php/intartif/article/view/2408>
:::


