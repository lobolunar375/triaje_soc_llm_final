"""Paso 00. Descarga de GUIDE desde Kaggle y verificación de integridad.

Qué hace:
  1. Descarga el zip del dataset con la API oficial de Kaggle (requiere ~/.kaggle/kaggle.json o las
     variables KAGGLE_USERNAME y KAGGLE_KEY). Si el zip ya está en data/raw, no lo vuelve a descargar.
  2. Descomprime GUIDE_Train.csv y GUIDE_Test.csv en data/raw.
  3. Calcula el SHA-256 de cada archivo y lo guarda en results/exploracion/integridad.json, para que
     cualquier réplica pueda comprobar que trabaja con los mismos datos.

Alternativa sin API: descargar el zip desde la página del dataset (botón Download) y copiarlo a
data/raw con cualquier nombre terminado en .zip; el script lo detecta y lo descomprime.
"""
import hashlib
import zipfile

from comunes import Bitacora, cargar_config, guardar_json, ruta


def sha256(path, bloque=1 << 24):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(bloque)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    cfg = cargar_config()
    b = Bitacora('00_descargar_datos')
    raw = ruta(cfg['datos']['dir_raw'], 'x').parent
    train = raw / cfg['datos']['archivo_train']
    test = raw / cfg['datos']['archivo_test']

    b.paso('Buscar los CSV o un zip ya descargado en data/raw',
           'Evita descargar 538 MB cada vez que se reproduce el experimento.')
    if not (train.exists() and test.exists()):
        zips = sorted(raw.glob('*.zip'))
        if not zips:
            b.paso('Descargar el zip con la API de Kaggle', 'Es la vía oficial y deja constancia de la versión del dataset.')
            from kaggle.api.kaggle_api_extended import KaggleApi
            api = KaggleApi()
            api.authenticate()
            api.dataset_download_files(cfg['datos']['kaggle_dataset'], path=str(raw), quiet=False, unzip=False)
            zips = sorted(raw.glob('*.zip'))
        b.paso(f'Descomprimir {zips[0].name}', 'Los scripts leen los CSV directamente con DuckDB, sin cargarlos completos en memoria.')
        with zipfile.ZipFile(zips[0]) as z:
            for info in z.infolist():
                b.info(f'{info.filename}: {info.file_size / 1e9:.2f} GB')
                z.extract(info, raw)
    else:
        b.info('Los CSV ya existen; no se descarga nada.')

    b.paso('Calcular SHA-256 de cada archivo', 'Permite verificar que una réplica usa exactamente los mismos datos.')
    integ = {}
    for p in sorted(raw.glob('*.csv')):
        integ[p.name] = {'bytes': p.stat().st_size, 'sha256': sha256(p)}
        b.info(f'{p.name}: {integ[p.name]["bytes"]:,} bytes  sha256={integ[p.name]["sha256"][:16]}...')
    guardar_json(integ, ruta('results', 'exploracion', 'integridad.json'))
    b.fin()


if __name__ == '__main__':
    main()
