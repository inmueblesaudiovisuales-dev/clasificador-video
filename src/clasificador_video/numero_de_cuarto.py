"""El número de los bins de cuartos en Premiere. Sin Qt."""
from __future__ import annotations

import re

_PREFIJO = re.compile(r"^\d+\.\s")


def con_numero(nombre: str, posicion: int) -> str:
    return f"{posicion:02d}. {nombre or ''}"


def sin_numero(nombre: str) -> str:
    return _PREFIJO.sub("", nombre or "")


def es_el_mismo_cuarto(un_nombre: str, otro_nombre: str) -> bool:
    # Se importa al usarlo para que las utilidades independientes sigan
    # disponibles durante el commit parcial de la Tarea 4.
    from clasificador_video.marca_camara import sin_marca_de_camara

    return sin_marca_de_camara(sin_numero(un_nombre)) == sin_marca_de_camara(sin_numero(otro_nombre))
