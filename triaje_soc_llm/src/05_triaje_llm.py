"""Paso 05. Ejecución del triaje automático: C1 (un solo LLM, control) y C2 (sistema multiagente).

Uso (configuración del estudio: GPT-4o mini por la API de OpenAI; la clave se lee de la variable LLM_API_KEY):
    set LLM_API_KEY=...            (Windows)        export LLM_API_KEY=...        (Linux y macOS)
    python src/05_triaje_llm.py --conjunto desarrollo --limite 5 # piloto de funcionamiento (no cuenta para resultados)
    python src/05_triaje_llm.py --conjunto evaluacion            # medición final, R corridas
Con un modelo local servido por Ollama basta cambiar backend, url y modelo en config/config.yaml.

El script es reanudable: si se interrumpe, al volver a ejecutarlo omite los pares (incidente, condición,
semilla) que ya están en results/corridas/.

Diseño:
  * C1 recibe el expediente completo (con las mismas salidas de herramientas que usa C2) y devuelve en una
    sola llamada la clase, la confianza, la prioridad, el escalamiento, la justificación y las evidencias.
  * C2 ejecuta cinco agentes. El ORQUESTADOR (código) invoca las herramientas, activa a los agentes en orden,
    valida cada salida contra su esquema JSON (hasta 3 reintentos), mide el tiempo de cada etapa y decide el
    escalamiento si la confianza es menor que el umbral. CONTEXTUALIZACIÓN, CLASIFICACIÓN y PRIORIZACIÓN son
    agentes LLM. TRAZABILIDAD es un agente verificador (código) que contrasta cada evidencia citada con el
    expediente; si encuentra evidencias inexistentes, pide una única corrección al agente de clasificación, y
    finalmente consolida el reporte auditable.
  * C1 y C2 se intercalan por incidente, en orden aleatorio, para que la carga del equipo no favorezca a
    ninguna condición; ambas usan el mismo modelo, temperatura, top-p y semilla.
"""
import argparse
import hashlib
import json
import os
import random
import re
import time
from pathlib import Path

import jsonschema
import pandas as pd
import requests

from comunes import RAIZ, Bitacora, cargar_config, ruta

DIR_AG = RAIZ / 'src' / 'agentes'
PROMPT = {p.stem: p.read_text(encoding='utf-8') for p in (DIR_AG / 'prompts').glob('*.md')}
ESQ = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (DIR_AG / 'esquemas').glob('*.json')}
LARGO = {'TP': 'TruePositive', 'BP': 'BenignPositive', 'FP': 'FalsePositive'}


# --------------------------------------------------------------------------- backends del modelo
class Backend:
    def __init__(self, cfg):
        self.c = cfg['llm']

    def llamar(self, sistema, usuario, esquema, semilla):
        """Devuelve (texto, tokens_entrada, tokens_salida, segundos)."""
        raise NotImplementedError


class Ollama(Backend):
    def llamar(self, sistema, usuario, esquema, semilla):
        cuerpo = {'model': self.c['modelo'], 'stream': False, 'format': esquema,
                  'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': usuario}],
                  'options': {'temperature': self.c['temperatura'], 'top_p': self.c['top_p'], 'seed': semilla,
                              'num_predict': self.c['max_tokens_salida'], 'num_ctx': 8192}}
        t = time.perf_counter()
        r = requests.post(f"{self.c['url']}/api/chat", json=cuerpo, timeout=self.c['timeout_s'])
        r.raise_for_status()
        j = r.json()
        return j['message']['content'], j.get('prompt_eval_count', 0), j.get('eval_count', 0), time.perf_counter() - t


class OpenAICompatible(Backend):
    """Cualquier API compatible con OpenAI (OpenAI, Gemini, Groq, vLLM...). La clave se lee de la variable de
    entorno LLM_API_KEY; nunca se guarda en el repositorio ni en la configuración."""

    def __init__(self, cfg):
        super().__init__(cfg)
        self.clave = os.environ.get('LLM_API_KEY', '')
        if not self.clave:
            raise SystemExit('Falta la variable de entorno LLM_API_KEY con la clave de la API.')

    def llamar(self, sistema, usuario, esquema, semilla):
        cuerpo = {'model': self.c['modelo'], 'temperature': self.c['temperatura'], 'top_p': self.c['top_p'],
                  'seed': semilla, 'max_tokens': self.c['max_tokens_salida'],
                  'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': usuario}],
                  'response_format': {'type': 'json_schema', 'json_schema': {'name': 'salida', 'schema': esquema}}}
        t = time.perf_counter()
        r = requests.post(f"{self.c['url']}/v1/chat/completions", json=cuerpo, timeout=self.c['timeout_s'],
                          headers={'Authorization': f'Bearer {self.clave}'})
        r.raise_for_status()
        j = r.json()
        u = j.get('usage', {})
        return (j['choices'][0]['message']['content'], u.get('prompt_tokens', 0), u.get('completion_tokens', 0),
                time.perf_counter() - t)


class Simulado(Backend):
    """SOLO PARA PRUEBAS DEL CÓDIGO: genera salidas válidas al azar. Nunca se usa para resultados."""

    def llamar(self, sistema, usuario, esquema, semilla):
        rnd = random.Random(hash((usuario[:200], semilla)))
        ids = re.findall(r'"id": "(A\d+(?:-E\d+)?)"', usuario) or ['A1']
        props = esquema['properties']
        out = {}
        for k, v in props.items():
            if 'enum' in v:
                out[k] = rnd.choice(v['enum'])
            elif v['type'] == 'number':
                out[k] = round(rnd.uniform(0.4, 0.95), 2)
            elif v['type'] == 'boolean':
                out[k] = rnd.random() < 0.3
            elif v['type'] == 'array':
                out[k] = rnd.sample(ids, min(2, len(ids))) if v['items'].get('type') == 'string' else []
            else:
                out[k] = 'Texto simulado de prueba ' * 6
        if 'justificacion' in out and 'clase' in out:
            out['justificacion'] = f"Clase {out['clase']}. " + out['justificacion']
        time.sleep(0.01)
        return json.dumps(out), len(usuario) // 4, 80, 0.01


BACKENDS = {'ollama': Ollama, 'openai': OpenAICompatible, 'simulado': Simulado}


# --------------------------------------------------------------------------- utilidades
def ids_validos(exp):
    ids = set()
    for a in exp['alertas']:
        ids.add(a['id'])
        ids.update(e['id'] for e in a['evidencias'])
    ids.update(t['tecnica'] for t in exp['herramientas']['mitre'])
    return ids


def vista(exp, incluir_herr=True):
    e = {k: v for k, v in exp.items() if k != 'herramientas'}
    txt = 'EXPEDIENTE DEL INCIDENTE:\n' + json.dumps(e, ensure_ascii=False)
    if incluir_herr:
        txt += '\n\nSALIDA DE LA HERRAMIENTA MITRE ATT&CK:\n' + json.dumps(exp['herramientas']['mitre'], ensure_ascii=False)
        txt += '\n\nSALIDA DE LA HERRAMIENTA HISTORIAL (tasas de calificación en otras organizaciones):\n' + \
               json.dumps(exp['herramientas']['historial'], ensure_ascii=False)
    return txt


class Agente:
    """Llama al modelo y valida la salida contra el esquema; reintenta si no es JSON válido."""

    def __init__(self, nombre, backend, cfg, registro):
        self.nombre, self.backend, self.cfg, self.reg = nombre, backend, cfg, registro
        self.sistema = PROMPT['comun'] + '\n\n' + PROMPT[nombre]
        self.esquema = ESQ['clasificacion' if nombre == 'correccion' else nombre]

    def __call__(self, usuario, semilla, extra_sistema=''):
        ultimo_error = None
        for intento in range(1 + self.cfg['llm']['reintentos_esquema']):
            txt, ti, to, s = self.backend.llamar(self.sistema + extra_sistema, usuario, self.esquema, semilla + 1000 * intento)
            self.reg['llamadas'] += 1
            self.reg['tokens_in'] += ti
            self.reg['tokens_out'] += to
            self.reg['t_agentes'][self.nombre] = self.reg['t_agentes'].get(self.nombre, 0) + s
            try:
                out = json.loads(txt)
                jsonschema.validate(out, self.esquema)
                self.reg['salidas_validas'] += 1
                return out
            except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                self.reg['salidas_invalidas'] += 1
                ultimo_error = str(e)[:200]
                if intento < self.cfg['llm']['reintentos_esquema']:
                    self.reg['reintentos'] += 1
        raise RuntimeError(f'{self.nombre}: salida inválida tras reintentos ({ultimo_error})')


def nuevo_registro():
    return {'llamadas': 0, 'tokens_in': 0, 'tokens_out': 0, 't_agentes': {}, 'reintentos': 0,
            'salidas_validas': 0, 'salidas_invalidas': 0}


def triaje_c1(exp, backend, cfg, semilla):
    reg = nuevo_registro()
    t0 = time.perf_counter()
    out = Agente('linea_base', backend, cfg, reg)(vista(exp), semilla)
    reg['t_total_s'] = time.perf_counter() - t0
    validos = ids_validos(exp)
    return {**reg, 'clase': out['clase'], 'confianza': out['confianza'], 'prioridad': out['prioridad'],
            'escalado': bool(out['escalar'] or out['confianza'] < cfg['llm']['umbral_escalamiento']),
            'justificacion': out['justificacion'], 'evidencias': out['evidencias'],
            'evidencias_invalidas': [e for e in out['evidencias'] if e not in validos], 'correccion': False,
            'salidas': {'linea_base': out}}


def triaje_c2(exp, backend, cfg, semilla):
    reg = nuevo_registro()
    t0 = time.perf_counter()
    base = vista(exp)  # el orquestador invoca las herramientas y entrega sus salidas al agente de contextualización
    ctx = Agente('contextualizacion', backend, cfg, reg)(base, semilla)
    entrada_cls = base + '\n\nCONTEXTO DEL AGENTE DE CONTEXTUALIZACIÓN:\n' + json.dumps(ctx, ensure_ascii=False)
    clasif = Agente('clasificacion', backend, cfg, reg)
    cls = clasif(entrada_cls, semilla)
    # agente de trazabilidad: verificación determinista de evidencias y, si hace falta, una corrección
    t_tr = time.perf_counter()
    validos = ids_validos(exp)
    invalidas = [e for e in cls['evidencias'] if e not in validos]
    reg['t_agentes']['trazabilidad_verificacion'] = time.perf_counter() - t_tr
    correccion = False
    evid_antes = list(cls['evidencias'])
    if invalidas:
        correccion = True
        extra = '\n\n' + PROMPT['correccion'].format(invalidas=', '.join(invalidas), validas=', '.join(sorted(validos)))
        cls = Agente('correccion', backend, cfg, reg)(entrada_cls, semilla + 7, extra_sistema=extra)
        invalidas = [e for e in cls['evidencias'] if e not in validos]
    entrada_pri = ('CLASE ASIGNADA: ' + cls['clase'] + f" (confianza {cls['confianza']})\n\nCONTEXTO:\n" +
                   json.dumps(ctx, ensure_ascii=False) + '\n\nRESUMEN DEL EXPEDIENTE:\n' + json.dumps(exp['resumen'], ensure_ascii=False))
    pri = Agente('priorizacion', backend, cfg, reg)(entrada_pri, semilla)
    t_tr = time.perf_counter()
    reporte = {'entradas': ['expediente', 'mitre', 'historial'], 'contexto': ctx, 'clasificacion': cls, 'priorizacion': pri,
               'evidencias_verificadas': [e for e in cls['evidencias'] if e in validos],
               'evidencias_no_verificadas': invalidas, 'correccion_solicitada': correccion}
    reg['t_agentes']['trazabilidad_verificacion'] += time.perf_counter() - t_tr
    reg['t_total_s'] = time.perf_counter() - t0
    escalado = bool(pri['escalar'] or cls['confianza'] < cfg['llm']['umbral_escalamiento'])
    return {**reg, 'clase': cls['clase'], 'confianza': cls['confianza'], 'prioridad': pri['prioridad'],
            'escalado': escalado, 'justificacion': cls['justificacion'], 'evidencias': cls['evidencias'],
            'evidencias_invalidas': invalidas, 'correccion': correccion, 'evidencias_antes_correccion': evid_antes,
            'salidas': reporte}


def huella_config(cfg):
    """Huella SHA-256 (12 caracteres) de los prompts, los esquemas y los parámetros del modelo. Sirve para
    comprobar que todas las corridas usaron la misma configuración. Nunca incluye credenciales.

    Nota sobre las corridas del estudio: se ejecutaron cuando el archivo de configuración contenía además un
    campo con la clave de la API, y por eso registran la huella 07c6ce608479. Con los mismos prompts, esquemas y
    parámetros, y sin ese campo, esta función devuelve c48ccc624197."""
    h = hashlib.sha256()
    for k in sorted(PROMPT):
        h.update(PROMPT[k].encode())
    for k in sorted(ESQ):
        h.update(json.dumps(ESQ[k], sort_keys=True).encode())
    llm = {k: v for k, v in cfg['llm'].items() if 'key' not in k.lower() and 'clave' not in k.lower()}
    h.update(json.dumps(llm, sort_keys=True).encode())
    return h.hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--conjunto', default='evaluacion', choices=['desarrollo', 'evaluacion'])
    ap.add_argument('--condiciones', default='C1,C2')
    ap.add_argument('--limite', type=int, default=0)
    ap.add_argument('--backend', default=None)
    ap.add_argument('--salida', default=None, help='carpeta de salida (por defecto results/corridas)')
    a = ap.parse_args()
    cfg = cargar_config()
    if a.backend:
        cfg['llm']['backend'] = a.backend
    b = Bitacora(f'05_triaje_llm_{a.conjunto}')
    backend = BACKENDS[cfg['llm']['backend']](cfg)
    version = huella_config(cfg)
    b.info(f"Backend: {cfg['llm']['backend']}  Modelo: {cfg['llm']['modelo']}  Huella de configuración: {version}")
    if cfg['llm']['backend'] == 'ollama':
        try:
            ver = requests.get(f"{cfg['llm']['url']}/api/version", timeout=10).json().get('version')
            tags = requests.get(f"{cfg['llm']['url']}/api/tags", timeout=10).json().get('models', [])
            dig = [m.get('digest') for m in tags if m.get('name', '').startswith(cfg['llm']['modelo'])]
            b.info(f'Ollama {ver}; digest del modelo: {dig[0] if dig else "no encontrado"}')
            (salida_meta := ruta('results', 'corridas', 'entorno_llm.json')).write_text(
                json.dumps({'ollama': ver, 'modelo': cfg['llm']['modelo'], 'digest': dig[0] if dig else None,
                            'huella_config': version}, indent=1), encoding='utf-8')
        except Exception as e:
            b.info(f'No se pudo consultar la versión de Ollama: {e}')
    if cfg['llm']['backend'] == 'simulado':
        b.info('ATENCIÓN: backend simulado, solo para probar el código; sus salidas no son resultados.')
    mu = pd.read_csv(ruta('data', 'processed', 'muestra.csv'))
    ids = mu[mu.conjunto == a.conjunto].incidente.tolist()
    if a.limite:
        ids = ids[:a.limite]
    salida = Path(a.salida) if a.salida else ruta('results', 'corridas', 'x').parent
    salida.mkdir(parents=True, exist_ok=True)
    arch = salida / f'corridas_{a.conjunto}.jsonl'
    hechos = set()
    if arch.exists():
        for linea in arch.read_text(encoding='utf-8').splitlines():
            r = json.loads(linea)
            hechos.add((r['incidente'], r['condicion'], r['semilla']))
    conds = a.condiciones.split(',')
    rng = random.Random(cfg['semilla'])
    total = len(ids) * len(conds) * len(cfg['llm']['semillas'])
    b.paso(f'Ejecutar {total} triajes ({len(ids)} incidentes × {len(conds)} condiciones × {len(cfg["llm"]["semillas"])} corridas)',
           'Ya hechos: %d. Las condiciones se intercalan por incidente en orden aleatorio.' % len(hechos))
    k = 0
    with open(arch, 'a', encoding='utf-8') as f:
        for sem in cfg['llm']['semillas']:
            orden = ids[:]
            rng.shuffle(orden)
            for inc in orden:
                exp = json.loads((RAIZ / 'data' / 'processed' / 'expedientes' / f'{inc}.json').read_text(encoding='utf-8'))
                cs = conds[:]
                rng.shuffle(cs)
                for c in cs:
                    k += 1
                    if (inc, c, sem) in hechos:
                        continue
                    try:
                        r = (triaje_c1 if c == 'C1' else triaje_c2)(exp, backend, cfg, sem)
                        r['no_procesado'] = False
                    except Exception as e:  # el fallo se registra y cuenta como error del sistema
                        r = {**nuevo_registro(), 'no_procesado': True, 'error': str(e)[:300], 'clase': None}
                    r.update({'incidente': inc, 'condicion': c, 'semilla': sem, 'modelo': cfg['llm']['modelo'],
                              'version_config': version, 'fecha': time.strftime('%Y-%m-%d %H:%M:%S')})
                    f.write(json.dumps(r, ensure_ascii=False) + '\n')
                    f.flush()
                    if k % 10 == 0 or k == total:
                        b.info(f'{k}/{total}  {inc} {c} s{sem}: {r.get("clase")} en {r.get("t_total_s", 0):.1f} s')
    b.fin()


if __name__ == '__main__':
    main()
