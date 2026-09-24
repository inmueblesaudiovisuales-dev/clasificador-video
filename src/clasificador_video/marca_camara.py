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

import re


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


_MARCAS = (("SONY", "bin_sony"), ("POCKET", "bin_pocket"), ("DRONE", "bin_dron"))
_MARCA_CONOCIDA = r"(?:SONY|POCKET|DRONE)(?:\+(?:SONY|POCKET|DRONE))*"
_PREFIJO_MARCA = re.compile(r"^\[" + _MARCA_CONOCIDA + r"\] ")
_SUFIJO_MARCA = re.compile(r" \[" + _MARCA_CONOCIDA + r"\]$")


def sin_marca_de_camara(nombre: str) -> str:
    """Quita una única marca conocida, no texto escrito por Bruno."""
    texto = str(nombre or "")
    return _SUFIJO_MARCA.sub("", _PREFIJO_MARCA.sub("", texto))


def _algun_clip_empieza_con(clips, prefijo, campo) -> bool:
    for clip in clips or []:
        categoria = clip.get("categoria_path") if isinstance(clip, dict) else None
        if categoria is None or not clip.get(campo) or len(categoria) < len(prefijo):
            continue
        if categoria[:len(prefijo)] == prefijo:
            return True
    return False


def marca_de_camara_del_prefijo(clips, prefijo) -> str:
    return "+".join(palabra for palabra, campo in _MARCAS if _algun_clip_empieza_con(clips, prefijo, campo))


def nombre_del_cuarto_con_marca(nombre_con_numero, nombre_sin_numero, clips, prefijo_de_categoria=None) -> str:
    marca = marca_de_camara_del_prefijo(clips, prefijo_de_categoria or [nombre_sin_numero])
    return f"{nombre_con_numero} [{marca}]" if marca else nombre_con_numero
