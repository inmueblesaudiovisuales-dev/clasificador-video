"""Importación rápida: dado la carpeta raíz de un proyecto local, encontrar
sola las carpetas de cámara que importan y calcular dónde van los proxies
nuevos en iCloud.

Spec: docs/superpowers/specs/2026-09-24-importacion-rapida-por-carpeta-design.md

Sin Qt: esto solo mira el disco y hace cuentas de rutas. Quien conecta esto
a un botón y arranca la generación de proxies vive en `main_window.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from clasificador_video import proyecto_colaborativo
from clasificador_video.ingest import archivos_de_video
from clasificador_video.marca_camara import (
    bin_dice_dron, bin_dice_pocket, bin_dice_sony,
)


def _con_video(carpeta: Path | None) -> Path | None:
    """`carpeta` si de verdad tiene algún video adentro, si no `None`.

    Sin este filtro, una carpeta de cámara creada por la plantilla de Bruno
    pero vacía -- no todos los rodajes usan las tres cámaras -- se contaba
    como «encontrada» aquí y como «nada que importar» un paso después, en
    `importar_rutas`: un aviso de "elegiste la carpeta equivocada" para una
    carpeta que sí era la correcta, simplemente sin material esta vez.
    """
    if carpeta is None or not archivos_de_video([carpeta]):
        return None
    return carpeta


def _primer_hijo_que_contiene(carpeta: Path, *, contiene: str) -> Path | None:
    """El primer subdirectorio DIRECTO de `carpeta` cuyo nombre contiene
    `contiene`, sin distinguir mayúsculas. No baja a subcarpetas -- así
    "07. PROXIES/01. PROXY SONY" nunca se confunde con "01. VIDEOS SONY",
    que vive un nivel arriba."""
    try:
        hijos = sorted((p for p in carpeta.iterdir() if p.is_dir()),
                       key=lambda p: p.name)
    except OSError:
        return None
    return next((h for h in hijos if contiene in h.name.lower()), None)


@dataclass(frozen=True)
class CarpetasDeMaterial:
    """Lo que se encontró dentro de la carpeta del proyecto. `None` en
    cualquier campo significa que esa carpeta no se encontró."""
    assets_video: Path | None
    sony: Path | None
    dron: Path | None
    pocket: Path | None
    faltantes: tuple[str, ...]


def detectar_carpetas_de_material(carpeta_del_proyecto: Path) -> CarpetasDeMaterial:
    """Encuentra `01. ASSETS VIDEO` y, dentro, las carpetas de Sony, dron y
    Pocket. Osmo Action nunca entra: ninguna de las tres búsquedas lo
    reconoce, así que se ignora sin tener que nombrarlo aparte.

    Sony y dron son las cámaras principales -- si falta alguna, se lista en
    `faltantes`. Pocket es opcional: no todos los rodajes la usan, así que
    su ausencia nunca se avisa como problema.
    """
    assets_video = _primer_hijo_que_contiene(
        carpeta_del_proyecto, contiene="video")
    if assets_video is None:
        return CarpetasDeMaterial(
            assets_video=None, sony=None, dron=None, pocket=None,
            faltantes=("01. ASSETS VIDEO",))

    try:
        hijos = [p for p in assets_video.iterdir() if p.is_dir()]
    except OSError:
        hijos = []
    sony = _con_video(next((h for h in hijos if bin_dice_sony(h.name)), None))
    dron = _con_video(next((h for h in hijos if bin_dice_dron(h.name)), None))
    pocket = _con_video(next((h for h in hijos if bin_dice_pocket(h.name)), None))

    faltantes = tuple(
        nombre for nombre, carpeta in (("Sony", sony), ("Drone", dron))
        if carpeta is None)

    return CarpetasDeMaterial(
        assets_video=assets_video, sony=sony, dron=dron, pocket=pocket,
        faltantes=faltantes)


def carpeta_de_proxies_en_icloud(
        carpeta_del_proyecto: Path,
        carpeta_raiz_icloud: Path | None) -> Path | None:
    """A dónde van los proxies nuevos de una importación rápida.

    El folio se saca del NOMBRE de la carpeta del proyecto -- así la nombra
    Bruno siempre, ej. `IAV-2609.10-A` -- y de ahí sale la misma ruta que ya
    usa "Proyecto nuevo con folio" (`proyecto_colaborativo.py`).

    `None` si no hay carpeta raíz de iCloud configurada, o si el nombre de
    la carpeta no es un folio reconocible: no se adivina un destino.
    """
    if carpeta_raiz_icloud is None:
        return None
    ruta_proyecto = proyecto_colaborativo.ruta_del_proyecto(
        carpeta_raiz_icloud, carpeta_del_proyecto.name)
    if ruta_proyecto is None:
        return None
    return ruta_proyecto / proyecto_colaborativo.CARPETA_PROXIES
