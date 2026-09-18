"""Si el nombre de un bin de importacion dice que es del dron.

Vive aparte de `camaras.py` a proposito: ese modulo mira el nombre de los
ARCHIVOS y decide el COLOR del clip en Premiere. Este mira el nombre del BIN
DE IMPORTACION -- la tanda con la que Bruno arrastro el material, la misma
que se ve como encabezado en la hoja -- y solo sirve para decidir la marca
[DRONE] en la carpeta del cuarto en Premiere. Son dos señales distintas y no
se mezclan (spec 2026-09-18 §2).
"""
from __future__ import annotations

_PALABRA = "dron"


def bin_dice_dron(nombre: str) -> bool:
    """`dron` es substring de `drone` («**dron**e»), asi que una sola
    comparacion, sin distinguir mayusculas, cubre las dos formas de
    escribirlo. Mismo criterio que `_MARCA_DEL_DRON` en `camaras.py`: una
    palabra, buscada como substring, sin adivinar mas de la cuenta."""
    return _PALABRA in (nombre or "").lower()
