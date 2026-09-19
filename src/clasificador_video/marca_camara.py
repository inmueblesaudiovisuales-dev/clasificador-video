"""Si el nombre de un bin de importación dice de qué cámara es.

Vive aparte de `camaras.py` a propósito: ese módulo mira el nombre de los
ARCHIVOS y decide el COLOR del clip en Premiere. Este mira el nombre del
BIN DE IMPORTACIÓN -- la tanda con la que Bruno arrastró el material, la
misma que se ve como encabezado en la hoja -- y solo sirve para decidir
las marcas `[SONY]` / `[POCKET]` / `[DRONE]` en la carpeta del cuarto en
Premiere. Son dos señales distintas y no se mezclan.

Nació como `marca_dron.py` (spec 2026-09-18, la de la marca [DRONE]) y se
generalizó a las tres cámaras el mismo día, con la spec de entrega a un
editor externo, §4.
"""
from __future__ import annotations


def _bin_dice(nombre: str, palabra: str) -> bool:
    return palabra in (nombre or "").lower()


def bin_dice_dron(nombre: str) -> bool:
    """`dron` es substring de `drone` («**dron**e»), así que una sola
    comparación cubre las dos formas de escribirlo."""
    return _bin_dice(nombre, "dron")


def bin_dice_sony(nombre: str) -> bool:
    return _bin_dice(nombre, "sony")


def bin_dice_pocket(nombre: str) -> bool:
    """`pocket` cubre "Osmo Pocket" completo sin tener que reconocer
    "osmo" -- que Bruno también usa para el Action, que NO entra en este
    sistema (spec 2026-09-18 §4)."""
    return _bin_dice(nombre, "pocket")
