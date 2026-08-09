# src/clasificador_video/ingest.py
from __future__ import annotations

from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mxf", ".lrf"}

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
