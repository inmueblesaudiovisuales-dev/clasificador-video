# src/clasificador_video/units.py
from __future__ import annotations

from clasificador_video.rooms import RoomSelection


class UnitSelection(RoomSelection):
    """Las unidades de la sesion (Casa A / Depto 1), planas y en orden.

    Misma forma que `RoomSelection`: el orden ES la tecla (1-9 en la
    paleta de unidades), y `add`/`rename`/`move`/`mover_a`/`reordenar`/
    `remove` significan exactamente lo mismo un nivel arriba. Clase propia
    -- no la misma `RoomSelection` reusada -- para que el codigo diga
    "esto es un catalogo de UNIDADES" en vez de "esto es un catalogo de
    cuartos que uso para otra cosa".
    """
