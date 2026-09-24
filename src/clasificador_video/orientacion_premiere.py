"""Mapeo confirmado con los clips Sony y DJI de la plantilla el 2026-09-23."""
from __future__ import annotations


class RotacionNoMapeada(Exception):
    pass


# ffprobe de ambos clips reales: rotation=90; XML guardado por Premiere: 8.
_ROTACION_A_ORIENTACION = {0: 1, 90: 8, 180: 3, 270: 6}


def orientacion_de(rotacion_grados: int) -> int:
    rotacion = rotacion_grados % 360
    if rotacion not in _ROTACION_A_ORIENTACION:
        raise RotacionNoMapeada(f"No hay OriginalImageOrientationType confirmado para {rotacion} grados")
    return _ROTACION_A_ORIENTACION[rotacion]
