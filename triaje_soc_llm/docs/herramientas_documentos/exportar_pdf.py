"""Exporta el artículo de Word a PDF con LibreOffice y ajusta el tamaño de las fórmulas.

Por qué existe este paso: al convertir un .docx, LibreOffice dibuja todas las fórmulas con su tamaño de letra
predeterminado (12 pt), mayor que el del texto del artículo (10 pt en los párrafos y 9 pt en las tablas). El
resultado son símbolos más grandes que las palabras que los rodean y renglones con separación desigual. Word no
tiene ese problema, porque dibuja cada fórmula con el tamaño del párrafo; por eso el .docx no se modifica y el
ajuste se aplica solo al exportar el PDF.

Qué hace:
  1. Copia el .docx a una carpeta temporal (así no quedan archivos de bloqueo junto al original).
  2. Abre la copia con LibreOffice sin interfaz gráfica, mediante su API (UNO).
  3. Recorre las fórmulas incrustadas y fija su tamaño base: 10 pt en el texto y 9 pt dentro de las tablas.
  4. Exporta el PDF y cierra LibreOffice.

Requiere LibreOffice y su puente de Python (paquete python3-uno). Si no están disponibles, termina con error y
build.sh recurre a la conversión directa de LibreOffice (el PDF es válido, con las fórmulas a 12 pt).

Uso: python3 exportar_pdf.py entrada.docx salida.pdf
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import uno
from com.sun.star.beans import PropertyValue

TAM_TEXTO, TAM_TABLA = 10, 9


def prop(nombre, valor):
    p = PropertyValue()
    p.Name, p.Value = nombre, valor
    return p


def puerto_libre():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def conectar(puerto, espera_s=60):
    """Espera a que LibreOffice acepte la conexión y devuelve el escritorio."""
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
    limite = time.time() + espera_s
    while time.time() < limite:
        try:
            ctx = resolver.resolve(f'uno:socket,host=127.0.0.1,port={puerto};urp;StarOffice.ComponentContext')
            return ctx.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
        except Exception:
            time.sleep(0.5)
    raise RuntimeError('LibreOffice no respondió')


def main(entrada, salida):
    entrada, salida = os.path.abspath(entrada), os.path.abspath(salida)
    trabajo = tempfile.mkdtemp(prefix='exportar_pdf_')
    copia = os.path.join(trabajo, 'articulo.docx')
    shutil.copy(entrada, copia)
    puerto = puerto_libre()
    proc = subprocess.Popen(['soffice', '--headless', '--norestore', '--nologo', '--nodefault',
                             f'-env:UserInstallation=file://{trabajo}/perfil',
                             f'--accept=socket,host=127.0.0.1,port={puerto};urp;'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    escritorio = doc = None
    try:
        escritorio = conectar(puerto)
        doc = escritorio.loadComponentFromURL(uno.systemPathToFileUrl(copia), '_blank', 0, (prop('Hidden', True),))
        if doc is None:
            raise RuntimeError('LibreOffice no pudo abrir el documento')
        # Sin esta pausa de la vista, cada cambio de tamaño recalcula la paginación de todo el documento.
        doc.lockControllers()
        objetos = doc.getEmbeddedObjects()
        n_texto = n_tabla = 0
        for i in range(objetos.getCount()):
            obj = objetos.getByIndex(i)
            modelo = obj.getEmbeddedObject()
            if modelo is None or not modelo.supportsService('com.sun.star.formula.FormulaProperties'):
                continue
            en_tabla = obj.getAnchor().TextTable is not None
            modelo.BaseFontHeight = TAM_TABLA if en_tabla else TAM_TEXTO
            n_tabla += en_tabla
            n_texto += not en_tabla
        doc.unlockControllers()
        doc.storeToURL(uno.systemPathToFileUrl(salida), (prop('FilterName', 'writer_pdf_Export'),))
        print(f'PDF exportado: {n_texto} fórmulas a {TAM_TEXTO} pt en el texto y {n_tabla} a {TAM_TABLA} pt en tablas')
    finally:
        for cerrar in (lambda: doc.close(True), lambda: escritorio.terminate()):
            try:
                cerrar()
            except Exception:
                pass
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()
        shutil.rmtree(trabajo, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
