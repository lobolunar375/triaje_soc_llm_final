"""Normaliza la tipografía del texto: espacio de no separación entre miles, antes de % y de unidades,
y entre una abreviatura y su número (Tabla 2, Figura 3, sección 3.5), para que no se partan entre líneas."""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
NB = ' '
partes = re.split(r'(\$\$.*?\$\$|\$[^$\n]+\$|`[^`\n]+`|<https?://[^>]+>|!\[.*?\]\(.*?\)\{.*?\})', t, flags=re.S)
out = []
for k, p in enumerate(partes):
    if k % 2 == 1 and not p.startswith('!['):
        out.append(p)
        continue
    for _ in range(3):
        p = re.sub(r'(\d) (\d{3})(?!\d)', r'\1' + NB + r'\2', p)
    p = re.sub(r'(\d) %', r'\1' + NB + '%', p)
    p = re.sub(r'(\d) (s|min|h|GB|pp)\b', r'\1' + NB + r'\2', p)
    p = re.sub(r'\b(Tabla|Figura|Tablas|Figuras|sección|secciones|Corrida|corrida) (\d)', r'\1' + NB + r'\2', p)
    p = re.sub(r'\b(n|p|b|c|V|k) = ', r'\1' + NB + '=' + NB, p)
    p = re.sub(r'\*(p|b|c)\* (=|<|>) ', r'*\1*' + NB + r'\2' + NB, p)
    p = re.sub(r'(H\.E\.\d|IC) (\d)', r'\1' + NB + r'\2', p)
    p = re.sub(r'IC 95', 'IC' + NB + '95', p)
    p = re.sub(r'([<>]) (\d)', r'\1' + NB + r'\2', p)
    out.append(p)
open(dst, 'w', encoding='utf-8').write(''.join(out))
