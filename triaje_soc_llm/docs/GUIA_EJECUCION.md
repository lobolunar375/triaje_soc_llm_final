# Guía de ejecución

## 1. Entorno

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux o macOS: source .venv/bin/activate)
pip install -r requirements.txt     # versiones exactas: requirements-lock.txt
```

Requiere Python 3.10 o superior; el análisis del estudio se ejecutó con Python 3.13.

## 2. Repetir el análisis con los triajes del estudio

No requiere el dataset ni el modelo: usa `results/corridas/corridas_evaluacion.jsonl` y `data/processed/`.

```bash
python ejecutar_todo.py --analisis
```

Ejecuta los pasos 07 (indicadores), 08 (contraste de hipótesis), 10 (análisis complementario) y 09 (figuras y tablas), y deja la bitácora de cada uno en `logs/`. Para comprobar que las cifras del artículo coinciden con los resultados:

```bash
python docs/herramientas_documentos/verificar_cifras.py docs/herramientas_documentos/paper.md .
```

## 3. Preparar los datos desde cero

1. Descargue el zip de GUIDE desde Kaggle y cópielo en `data/raw/`, o configure la API de Kaggle (`~/.kaggle/kaggle.json`).
2. Ejecute `python ejecutar_todo.py` (pasos 00 a 04 y 09). Tarda unos 4 minutos en un equipo de 2 núcleos y 7 GB de memoria, y necesita unos 4 GB libres.

El resultado es determinista: la semilla 42 produce la misma partición, la misma muestra y los mismos expedientes.

## 4. Ejecutar de nuevo el triaje con el modelo

La configuración del estudio está en `config/config.yaml` (`backend: openai`, `modelo: gpt-4o-mini`). La clave de la API se entrega por una variable de entorno y **nunca** se escribe en un archivo del repositorio:

```bash
set LLM_API_KEY=...                 # Windows (PowerShell: $env:LLM_API_KEY="...")
export LLM_API_KEY=...              # Linux o macOS

python src/05_triaje_llm.py --conjunto desarrollo --limite 5    # piloto de funcionamiento
python src/05_triaje_llm.py --conjunto evaluacion               # 1 800 triajes (unas 3 horas)
python ejecutar_todo.py --analisis
```

El paso 05 es reanudable: si se interrumpe, al volver a ejecutarlo omite los triajes ya guardados. Para empezar de cero, mueva antes `results/corridas/corridas_evaluacion.jsonl` a otra carpeta. Como el modelo no es determinista y el servicio puede cambiar, una nueva ejecución no reproduce las cifras exactas del artículo.

Para usar un modelo local con Ollama, cambie en `config/config.yaml` `backend: ollama`, `url: http://localhost:11434` y `modelo` (por ejemplo, `qwen2.5:7b`), y descargue el modelo con `ollama pull`.

## 5. Probar el código sin modelo

```bash
python tests/prueba_humo.py
```

Ejecuta los pasos 05, 07, 08, 10 y 09 en una carpeta temporal con un backend que genera respuestas válidas al azar. Solo comprueba que el código funciona; sus salidas no son resultados.

## 6. Extensión: triaje manual y auditoría humana (no ejecutada en el estudio)

Los scripts `src/06_triaje_manual.py` y `src/07b_consolidar_auditoria.py` permiten añadir una referencia de triaje manual y una auditoría de la coherencia de las justificaciones. Si se usan, los datos deben provenir de personas que realicen el triaje o la revisión.

```bash
python src/06_triaje_manual.py --analista A          # y --analista B
python src/07_calcular_metricas.py --plantilla-auditoria
python src/07b_consolidar_auditoria.py               # después de llenar results/auditoria/plantilla_auditoria.csv
```
