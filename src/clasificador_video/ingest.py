# src/clasificador_video/ingest.py
from __future__ import annotations

from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mxf"}

# El `.LRF` del dron NO esta en la lista, y no es un olvido.
#
# DJI escribe uno junto a cada `.MP4`, en la misma carpeta: es su proxy. Con
# el adentro, arrastrar la tarjeta del dron metia cada toma DOS veces --el
# mismo problema que los `S03` de la Sony, que se descartan por sufijo.
#
# Tampoco se queda como proxy: se midio contra las 23 tomas reales de Bruno y
# el `.LRF` no calza cuadro a cuadro con el original (el contenido va corrido
# entre 0 y 5 cuadros, y el desfase cambia de toma en toma), asi que la
# validacion de proxies lo rechazaria igual. Los proxies del dron se generan
# del original. Ver el handoff de los bins, §4.b.

# Como nombra la camara a los proxies: `C0001.MP4` -> `C0001S03.MP4`. Vive
# aca, junto a las extensiones, porque las dos son lo mismo -- hechos sobre
# COMO SE LLAMAN los archivos que salen de la tarjeta. Emparejarlos ya es
# otro problema y vive en `proxy_match.py`, que importa de aca.
SUFIJO_PROXY = "S03"


def es_archivo_de_proxy(ruta: Path) -> bool:
    return ruta.stem.endswith(SUFIJO_PROXY)


def archivos_de_video(rutas: list[Path]) -> list[Path]:
    """De una mezcla de carpetas y archivos, los videos que son material.

    De una carpeta se toman sus archivos directos, sin bajar a las
    subcarpetas: arrastrar una tarjeta de camara no puede traerse tambien
    sus carpetas de sistema.
    """
    encontrados: list[Path] = []
    for ruta in rutas:
        if ruta.is_dir():
            candidatos = sorted(p for p in ruta.iterdir() if p.is_file())
        elif ruta.is_file():
            candidatos = [ruta]
        else:
            # ni carpeta ni archivo: no existe. Dejarla pasar por el sufijo
            # terminaba en el aviso de «falta ffprobe», que es el
            # diagnostico equivocado.
            continue
        for p in candidatos:
            if (p.suffix.lower() in VIDEO_EXTENSIONS
                    and not es_archivo_de_proxy(p)
                    and p not in encontrados):
                encontrados.append(p)
    return encontrados
