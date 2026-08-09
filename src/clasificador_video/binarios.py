# src/clasificador_video/binarios.py
from __future__ import annotations

import shutil
import sys
from pathlib import Path


class BinarioFaltante(RuntimeError):
    """No se encontro un programa del que la app depende.

    Se levanta a proposito en vez de devolver `None`: sin `ffprobe` la
    importacion no lee un solo clip, y el bug se manifestaria como «importe
    la carpeta y no aparecio nada», sin ninguna pista.
    """


def ruta_de(nombre: str) -> Path:
    """Donde esta `ffprobe`, `ffmpeg` o `mpv`.

    Dentro de la app empaquetada van ADENTRO del paquete, no en el PATH:
    en la computadora de un compañero no hay Homebrew, y buscarlos por
    nombre encuentra nada. Comprobado con el paquete armado y el PATH
    limpio -- la app abria y no importaba un solo clip.

    Fuera del paquete (corriendo desde el codigo) se usa el del sistema,
    que es lo que hace falta para desarrollar y para los tests.
    """
    empaquetada = getattr(sys, "_MEIPASS", None)
    if empaquetada:
        candidato = Path(empaquetada) / nombre
        if candidato.exists():
            return candidato
    del_sistema = shutil.which(nombre)
    if del_sistema:
        return Path(del_sistema)
    raise BinarioFaltante(
        f"No se encontró «{nombre}», que la app necesita para leer los videos."
    )


def esta_disponible(nombre: str) -> bool:
    try:
        ruta_de(nombre)
    except BinarioFaltante:
        return False
    return True
