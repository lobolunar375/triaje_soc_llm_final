"""Genera docs/trazabilidad.md, docs/Matriz_trazabilidad_paper.xlsx y fuentes/manifest_fuentes.csv a partir de
una única lista, para que los tres documentos coincidan.

Cada fila de la matriz relaciona una parte del artículo con las referencias que la sustentan y con los archivos
del repositorio de los que proceden sus cifras. Los enlaces de las referencias [1] a [18], el del conjunto de
datos y el del artículo modelo de la revista son los de la sistematización.

Uso: python docs/herramientas_documentos/generar_trazabilidad.py
"""
import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

RAIZ = Path(__file__).resolve().parents[2]

# código, cita corta, referencia completa, enlace (sistematización), archivo sugerido, URL directa del PDF (si es abierto), acceso
REFS = [
    ('R01', 'Malach et al., 2025', 'Malach, A., Wudali, P. N., Momiyama, S., Furukawa, J., Araki, T., Elovici, Y., & Shabtai, A. (2025). CyberShapley: Explanation, prioritization, and triage of cybersecurity alerts using informative graph representation. Computers & Security, 150, 104270.',
     'https://doi.org/10.1016/j.cose.2024.104270', 'R01_Malach_2025_ComputersSecurity.pdf', '', 'Suscripción (descarga manual)'),
    ('R02', 'Wang et al., 2024', 'Wang, X., Yang, X., Liang, X., Zhang, X., Zhang, W., & Gong, X. (2024). Combating alert fatigue with AlertPro: Context-aware alert prioritization using reinforcement learning for multi-step attack detection. Computers & Security, 137, 103583.',
     'https://doi.org/10.1016/j.cose.2023.103583', 'R02_Wang_2024_ComputersSecurity.pdf', '', 'Suscripción (descarga manual)'),
    ('R03', 'Rieger et al., 2026', 'Rieger, M., Shah, A., Alam, A., & Hossain, M. J. (2026). Possibilities and limitations of using large language models (LLMs) for alert classification and prioritisation in security operations centers (SOCs). Expert Systems with Applications, 331, 133194.',
     'https://doi.org/10.1016/j.eswa.2026.133194', 'R03_Rieger_2026_ESWA.pdf', '', 'Versión de los autores en el repositorio de su universidad (descarga manual)'),
    ('R04', 'Okafor, 2026', 'Okafor, E. (2026). A leakage-free benchmark of offline policy learning for SOC alert triage. Machine Learning with Applications, 25, 100984.',
     'https://doi.org/10.1016/j.mlwa.2026.100984', 'R04_Okafor_2026_MLWA.pdf', '', 'Abierto (descarga manual desde el enlace)'),
    ('R05', 'Tariq et al., 2025', 'Tariq, S., Baruwal Chhetri, M., Nepal, S., & Paris, C. (2025). A²C: A modular multi-stage collaborative decision framework for human–AI teams. Expert Systems with Applications, 282, 127318.',
     'https://doi.org/10.1016/j.eswa.2025.127318', 'R05_Tariq_2025_ESWA.pdf', '', 'Suscripción (descarga manual)'),
    ('R06', 'Vaarandi & Guerra-Manzanares, 2024', 'Vaarandi, R., & Guerra-Manzanares, A. (2024). Stream clustering guided supervised learning for classifying NIDS alerts. Future Generation Computer Systems, 155, 231–244.',
     'https://doi.org/10.1016/j.future.2024.02.001', 'R06_Vaarandi_2024_FGCS.pdf', '', 'Suscripción (descarga manual)'),
    ('R07', 'Mudzakir et al., 2025', 'Mudzakir, A., Janaprasetya, J. T. A., Kayowuan, E., Engel, V. J. L., & Saputro, B. (2025). Evaluating three large language models for security incident detection and analysis. Procedia Computer Science, 269, 465–473.',
     'https://doi.org/10.1016/j.procs.2025.08.299', 'R07_Mudzakir_2025_ProcediaCS.pdf', '', 'Abierto (descarga manual desde el enlace)'),
    ('R08', 'Simões et al., 2026', 'Simões, R. T. de P., Larriva-Novo, X., Sánchez-Zas, C., Villagrá, V. A., & Marín López, A. I. (2026). Design of a security framework for multi-agent systems based on model context protocol in SOC environments. Applied Sciences, 16(16), 7915.',
     'https://doi.org/10.3390/app16167915', 'R08_Simoes_2026_AppliedSciences.pdf', 'https://www.mdpi.com/2076-3417/16/16/7915/pdf', 'Abierto'),
    ('R09', 'Baruwal Chhetri et al., 2024', 'Baruwal Chhetri, M., Tariq, S., Singh, R., Jalalvand, F., Paris, C., & Nepal, S. (2024). Towards human-AI teaming to mitigate alert fatigue in security operations centres. ACM Transactions on Internet Technology, 24(3), 1–22.',
     'https://doi.org/10.1145/3670009', 'R09_BaruwalChhetri_2024_TOIT.pdf', '', 'Suscripción (descarga manual)'),
    ('R10', 'Kazi & Poinkar, 2026', 'Kazi, M., & Poinkar, S. (2026). An explainable AI based alert triage framework for security operations centres: Architecture, evaluation, and analyst centred design. InfoTech Spectrum: Iraqi Journal of Data Science, 3(2), 67–78.',
     'https://doi.org/10.51173/ijds.v3i2.84', 'R10_Kazi_2026_IJDS.pdf', '', 'Abierto (descarga manual desde el enlace)'),
    ('R11', 'Ismail et al., 2025', 'Ismail, Kurnia, R., Brata, Z. A., Nelistiani, G. A., Heo, S., Kim, H., & Kim, H. (2025). Toward robust security orchestration and automated response in security operations centers with a hyper-automation approach using agentic artificial intelligence. Information, 16(5), 365.',
     'https://doi.org/10.3390/info16050365', 'R11_Ismail_2025_Information.pdf', 'https://www.mdpi.com/2078-2489/16/5/365/pdf', 'Abierto'),
    ('R12', 'Kumar & Khan, 2026', 'Kumar, S., & Khan, I. (2026). Autonomous security alert triage using LLM based agentic investigation with tool augmented reasoning. International Journal of Scientific Research in Computer Science, Engineering and Information Technology, 12(2), 752–765.',
     'https://doi.org/10.32628/CSEIT261213109', 'R12_Kumar_2026_IJSRCSEIT.pdf', '', 'Abierto (descarga manual desde el enlace)'),
    ('R13', 'Zhong et al., 2019', "Zhong, C., Yen, J., Liu, P., & Erbacher, R. F. (2019). Learning from experts' experience: Toward automated cyber security data triage. IEEE Systems Journal, 13(1), 603–614.",
     'https://doi.org/10.1109/JSYST.2018.2828832', 'R13_Zhong_2019_IEEESystemsJournal.pdf', '', 'Suscripción (descarga manual)'),
    ('R14', 'Wu et al., 2026', 'Wu, S., Sun, X., Dong, E., Wang, Z., Zhao, C., & Yang, J. (2026). Alert2Vec: Eliminating alert fatigue by embedding security alerts through subgraph learning. IEEE Transactions on Dependable and Secure Computing, 23(1), 655–669.',
     'https://doi.org/10.1109/TDSC.2025.3609834', 'R14_Wu_2026_IEEETDSC.pdf', '', 'Suscripción (descarga manual)'),
    ('R15', 'Schärmer et al., 2026', 'Schärmer, A., Landauer, M., Skopik, F., Wurzenberger, M., & Squarcina, M. (2026). Let the alerts speak: LLM-based IDS alert interpretation for SOC triage. In Availability, Reliability and Security. ARES 2026 International Workshops (pp. 346–364). Springer.',
     'https://doi.org/10.1007/978-3-032-35579-9_19', 'R15_Scharmer_2026_ARES.pdf', '', 'Suscripción (descarga manual)'),
    ('R16', 'Landauer et al., 2022', 'Landauer, M., Skopik, F., Wurzenberger, M., & Rauber, A. (2022). Dealing with security alert flooding: Using machine learning for domain-independent alert aggregation. ACM Transactions on Privacy and Security, 25(3), 1–36.',
     'https://doi.org/10.1145/3510581', 'R16_Landauer_2022_TOPS.pdf', '', 'Descarga manual desde el enlace'),
    ('R17', 'Ghadermazi et al., 2024', 'Ghadermazi, J., Shah, A., & Jajodia, S. (2024). A machine learning and optimization framework for efficient alert management in a cybersecurity operations center. Digital Threats: Research and Practice, 5(2), 1–23.',
     'https://doi.org/10.1145/3644393', 'R17_Ghadermazi_2024_DTRAP.pdf', '', 'Abierto (descarga manual desde el enlace)'),
    ('R18', 'Vermeer et al., 2023', 'Vermeer, M., Kadenko, N., van Eeten, M., Gañán, C., & Parkin, S. (2023). Alert alchemy: SOC workflows and decisions in the management of NIDS rules. In Proceedings of the 2023 ACM SIGSAC Conference on Computer and Communications Security (pp. 2770–2784).',
     'https://doi.org/10.1145/3576915.3616581', 'R18_Vermeer_2023_CCS.pdf', '', 'Abierto (descarga manual desde el enlace)'),
    ('R19', 'Freitas et al., 2025', 'Freitas, S., Kalajdjieski, J., Gharib, A., & McCann, R. (2025). AI-driven guided response for security operation centers with Microsoft Copilot for Security. In Companion Proceedings of the ACM on Web Conference 2025 (pp. 191–200). Conjunto de datos GUIDE.',
     'https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction', 'R19_Freitas_2025_GUIDE.pdf', 'https://arxiv.org/pdf/2407.09017', 'Abierto (versión previa en arXiv)'),
    ('R20', 'Mohammed & Jamali, 2026', 'Mohammed, D., & Jamali, S. (2026). Unveiling the frontiers of cyber threat hunting: A comprehensive review of LLM-based approaches. Inteligencia Artificial, 29(78), 59–83.',
     'https://journal.iberamia.org/index.php/intartif/article/view/2408', 'R20_Mohammed_2026_InteligenciaArtificial.pdf', '', 'Abierto (descarga manual desde el enlace)'),
]

S = 'docs/curso/Sistematizacion_v3.docx'
E = 'results/estadistica/'
M = 'results/metricas/'
T = 'results/tablas/'
F = 'results/figuras/'
# sección, parte, contenido, referencias (números), archivos del repositorio
FILAS = [
    ('Resumen', 'Abstract y Resumen', 'Síntesis del problema, el método y los resultados', [], [E + 'contrastes.json', E + 'complementario.json', T + 'tabla_desempeno.csv']),
    ('1 Introducción', 'Párrafo 1', 'Volumen de alertas, fatiga de alertas, falsos positivos y trabajo manual de los analistas', [9, 17, 10, 12, 15, 13], []),
    ('1 Introducción', 'Párrafo 2', 'Métodos de aprendizaje automático y sus límites; promesa y límites de los LLM', [1, 2, 6, 14, 16, 12, 15, 20, 3], []),
    ('1 Introducción', 'Párrafo 3', 'Agentes LLM en el SOC y preguntas sin responder (control, fuga y trazabilidad)', [8, 11, 12, 4], []),
    ('1 Introducción', 'Párrafos 4 y 5', 'Pregunta de investigación, diseño y contribuciones', [19], [S, E + 'contrastes.json', E + 'complementario.json']),
    ('2 Trabajos relacionados', 'Triaje y priorización con aprendizaje automático', 'Trazas de analistas, agrupamiento, agregación, optimización, aprendizaje por refuerzo, grafos y fuga de información', [13, 6, 16, 17, 2, 14, 1, 4], []),
    ('2 Trabajos relacionados', 'LLM para clasificar e interpretar alertas', 'Evaluaciones de LLM frente a clasificadores, efecto del contexto y revisión del área', [3, 15, 7, 20], []),
    ('2 Trabajos relacionados', 'Agentes y orquestación en el SOC', 'Agente con herramientas, orquestación con agentes y seguridad de sistemas multiagente', [12, 11, 8], []),
    ('2 Trabajos relacionados', 'Fatiga de alertas y factor humano', 'Equipos humano-IA, gestión de reglas y explicaciones centradas en el analista', [9, 5, 18, 10], []),
    ('2 Trabajos relacionados', 'Tabla 1', 'Estudios más cercanos y diferencia con este trabajo', [3, 15, 12, 8, 11, 10, 4], []),
    ('3.1 Diseño de la investigación', 'Párrafo único', 'Enfoque, tipo, nivel y diseño', [], [S]),
    ('3.2 Variables e hipótesis', 'Texto y Tabla 2', 'Variables, indicadores, niveles e hipótesis', [], [S]),
    ('3.3 Conjunto de datos', 'Dos párrafos', 'Descripción de GUIDE, clases, licencia e integridad de los archivos', [19], ['src/00_descargar_datos.py', 'results/exploracion/integridad.json']),
    ('3.4 Población, muestra y partición', 'Texto y fórmula', 'Criterios de elegibilidad, partición por organización, muestreo y tamaño de muestra', [4], ['src/03_muestrear_particionar.py', 'config/config.yaml', 'results/muestra/resumen_muestra.json']),
    ('3.5 Selección de características y representación del incidente', 'Texto y lista', 'Roles de las 45 columnas, expediente, herramientas y base de conocimiento', [15, 6, 13], ['config/seleccion_caracteristicas.yaml', 'src/02_limpiar_datos.py', 'src/04_construir_expedientes.py', 'config/mitre_tecnicas.csv']),
    ('3.6 Sistema multiagente', 'Texto, lista y Figura 1', 'Arquitectura, agentes, modelo, parámetros, prompts y huella de configuración', [8, 11, 12, 5, 9, 16, 1, 2, 10], ['src/05_triaje_llm.py', 'src/agentes/prompts/', 'src/agentes/esquemas/', 'config/config.yaml', 'src/09b_figura_arquitectura.py', F + 'fig_arquitectura.png']),
    ('3.7 Condiciones de comparación', 'Texto y lista', 'C1, C2 y reglas de referencia sin modelo de lenguaje', [3], ['src/05_triaje_llm.py (triaje_c1 y triaje_c2)', 'src/04_construir_expedientes.py (referencia estadística)']),
    ('3.8 Instrumento y métricas', 'Texto y fórmulas', 'Registro de observación, indicadores de la VD y de la VI, criterios de trazabilidad y reglas de agregación', [], ['src/07_calcular_metricas.py', M + 'registro_observacion.csv']),
    ('3.9 Procedimiento', 'Párrafo único', 'Nueve pasos del experimento', [], ['ejecutar_todo.py', 'logs/']),
    ('3.10 Análisis estadístico', 'Tres párrafos', 'McNemar, Wilcoxon, Holm, bootstrap, sensibilidad y análisis exploratorios', [], ['src/08_analisis_estadistico.py', 'src/10_analisis_complementario.py']),
    ('3.11 Amenazas a la validez', 'Dos párrafos', 'Validez interna, de constructo y externa', [19], []),
    ('4.1 Preparación de los datos', 'Texto y Tabla 3', 'Embudo de limpieza, población elegible y valores centinela', [], ['src/01_explorar_dataset.py', 'src/02_limpiar_datos.py', 'results/limpieza/embudo_limpieza.csv', 'results/limpieza/reporte_limpieza.json', 'logs/02_limpiar_datos.log']),
    ('4.2 Selección de características', 'Texto y Tabla 4', 'Decisión por columna y evidencia empírica', [], ['results/limpieza/decisiones_columnas.csv', 'results/exploracion/perfil_columnas.csv']),
    ('4.3 Partición y muestra', 'Texto, Tabla 5 y Figura 2', 'Composición de la muestra y comparación con la población', [], ['results/muestra/composicion_muestra.csv', 'data/processed/muestra.csv', F + 'fig_distribucion_clases.png']),
    ('4.4 Base de conocimiento y expedientes', 'Dos párrafos', 'Tamaño de la base de conocimiento y de los expedientes', [], ['data/processed/base_conocimiento.parquet', 'data/processed/expedientes/', 'results/expedientes/resumen_expedientes.json']),
    ('4.5 Implementación y ejecución', 'Dos párrafos', 'Programa, prueba previa, piloto y ejecución de los 1 800 triajes', [], ['src/05_triaje_llm.py', 'tests/prueba_humo.py', 'logs/05_triaje_llm_desarrollo.log', 'logs/05_triaje_llm_evaluacion.log', 'results/corridas/corridas_evaluacion.jsonl']),
    ('5.1 Muestra de evaluación y reglas de referencia', 'Dos párrafos', 'Caracterización de la muestra y desempeño de las reglas sin LLM', [], ['results/expedientes/referencia_estadistica.csv', T + 'tabla_desempeno.csv']),
    ('5.2 Precisión de clasificación', 'Texto, Tablas 6 y 7 y Figura 3', 'Exactitud, F1 macro, desempeño por clase, matrices de confusión y comparación con las referencias', [], [T + 'tabla_desempeno.csv', T + 'tabla_matrices_confusion.csv', E + 'contrastes.json (HE1)', E + 'complementario.json (mcnemar_referencias)', F + 'fig_matrices_confusion.png']),
    ('5.3 Eficiencia temporal', 'Texto y Figura 4', 'Tiempo por incidente y por agente, llamadas y tokens', [], [E + 'contrastes.json (HE2)', M + 'tiempo_por_agente.csv', M + 'indicadores_vd.csv', F + 'fig_tiempos.png']),
    ('5.4 Trazabilidad', 'Texto y Tabla 8', 'Criterios de trazabilidad y desenlace del ciclo de verificación y corrección', [], [M + 'indicadores_vd.csv', E + 'contrastes.json (HE3)', E + 'complementario.json (correccion)', M + 'registro_observacion.csv']),
    ('5.5 Contraste de las hipótesis', 'Texto y Tabla 9', 'Pruebas, valores p con la corrección de Holm y decisión', [], [E + 'contrastes.json', E + 'decision_hipotesis.md']),
    ('5.6 Análisis de sensibilidad', 'Texto y Tabla 10', 'Contraste por corrida, sin triajes no procesados, sin escalados y por organización', [], [E + 'contrastes.json (sensibilidad)', M + 'por_corrida.csv']),
    ('5.7 Análisis complementario', 'Texto, Figuras 5 y 6 y Tabla 11', 'Historial del detector, confianza, escalamiento, consistencia y costo', [], [E + 'complementario.json', T + 'tabla_subgrupos_historial.csv', T + 'tabla_confianza.csv', M + 'indicadores_vi.csv', F + 'fig_exactitud_subgrupos.png', F + 'fig_confianza.png']),
    ('6.1 Qué aporta la organización multiagente', 'Tres párrafos', 'Origen de la mejora, comparación con las reglas y con la literatura', [19, 3, 12, 15], [E + 'complementario.json', M + 'registro_observacion.csv (INC-0118, corrida 1)']),
    ('6.2 Tiempo, consistencia y confianza', 'Tres párrafos', 'Costo, estabilidad entre corridas, confianza y uso consultivo', [10, 12, 5, 9, 4], [E + 'complementario.json (consistencia, confianza y escalamiento)']),
    ('6.3 Trazabilidad y fallos del ciclo de verificación', 'Tres párrafos', 'Modos de fallo, recomendaciones de diseño y trazabilidad formal frente a corrección', [8], [E + 'complementario.json (correccion y trazables_con_clase_erronea)']),
    ('6.4 Limitaciones', 'Dos párrafos', 'Alcance del estudio', [19], []),
    ('7 Conclusiones y trabajo futuro', 'Tres párrafos', 'Decisión sobre las hipótesis, implicaciones y líneas futuras', [], [E + 'decision_hipotesis.md', S]),
    ('Referencias', 'Lista [1] a [20]', 'Referencias y enlaces de la sistematización', list(range(1, 21)), ['fuentes/manifest_fuentes.csv']),
]

por_num = {k + 1: r for k, r in enumerate(REFS)}


def ref_txt(nums):
    return [f'[{n}] {por_num[n][1]}' for n in nums]


# ----------------------------------------------------------------------------- Markdown
md = ['# Trazabilidad del artículo', '',
      'Cada parte del artículo con las referencias que la sustentan y los archivos del repositorio de los que proceden sus cifras. '
      'La misma matriz está en `docs/Matriz_trazabilidad_paper.xlsx`. Las cifras del artículo se comprueban contra `results/` con '
      '`docs/herramientas_documentos/verificar_cifras.py`.', '',
      '| Sección | Parte | Contenido | Referencias | Archivos del repositorio |', '|---|---|---|---|---|']
for sec, parte, cont, nums, arch in FILAS:
    md.append(f"| {sec} | {parte} | {cont} | {'<br>'.join(ref_txt(nums)) or '—'} | {'<br>'.join(f'`{a}`' for a in arch) or '—'} |")
md += ['', '## Referencias', '', '| N.º | Referencia | Enlace | Acceso |', '|---|---|---|---|']
for k, (cod, corta, larga, enlace, archivo, pdf, acceso) in enumerate(REFS, start=1):
    md.append(f'| [{k}] | {larga} | <{enlace}> | {acceso} |')
(RAIZ / 'docs' / 'trazabilidad.md').write_text('\n'.join(md) + '\n', encoding='utf-8')

# ----------------------------------------------------------------------------- Excel
wb = Workbook()
borde = Border(*(Side(style='thin', color='808080'),) * 4)
cab = PatternFill('solid', start_color='D9D9D9')


def hoja(ws, titulos, filas, anchos):
    ws.append(titulos)
    for f in filas:
        ws.append(f)
    for j, a in enumerate(anchos, start=1):
        ws.column_dimensions[ws.cell(1, j).column_letter].width = a
    for fila in ws.iter_rows():
        for c in fila:
            c.font = Font(name='Arial', size=10, bold=c.row == 1)
            c.alignment = Alignment(wrap_text=True, vertical='top', horizontal='center' if c.row == 1 else 'left')
            c.border = borde
            if c.row == 1:
                c.fill = cab
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions


ws = wb.active
ws.title = 'Trazabilidad'
hoja(ws, ['Sección', 'Parte', 'Contenido', 'Referencias', 'Archivos del repositorio'],
     [[s, p, c, '\n'.join(ref_txt(n)) or '—', '\n'.join(a) or '—'] for s, p, c, n, a in FILAS], [30, 26, 52, 34, 58])
ws2 = wb.create_sheet('Referencias')
hoja(ws2, ['N.º', 'Código', 'Referencia', 'Enlace (sistematización)', 'Archivo en fuentes/', 'Acceso'],
     [[f'[{k}]', cod, larga, enlace, archivo, acceso] for k, (cod, corta, larga, enlace, archivo, pdf, acceso) in enumerate(REFS, start=1)],
     [7, 9, 90, 46, 40, 34])
wb.save(RAIZ / 'docs' / 'Matriz_trazabilidad_paper.xlsx')

# ----------------------------------------------------------------------------- manifiesto de fuentes
(RAIZ / 'fuentes').mkdir(exist_ok=True)
with open(RAIZ / 'fuentes' / 'manifest_fuentes.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['codigo', 'cita', 'archivo', 'url_pdf', 'doi_o_pagina', 'acceso'])
    for cod, corta, larga, enlace, archivo, pdf, acceso in REFS:
        w.writerow([cod, corta, archivo, pdf, enlace, acceso])
print(f'ok: {len(FILAS)} filas de trazabilidad y {len(REFS)} referencias')
