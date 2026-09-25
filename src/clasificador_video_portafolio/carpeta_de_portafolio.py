"""La carpeta de portafolio: dónde vive cada clip Elegido (como alias
de Finder) y su proxy, organizados en una subcarpeta por proyecto de
origen.

Solo calcula y prepara RUTAS -- no toca ninguna API de macOS. Crear el
alias de Finder de verdad es la Fase 4.5 (requiere macOS). Spec:
docs/superpowers/specs/2026-09-24-modo-portafolio-design.md.
"""
from __future__ import annotations

from pathlib import Path

from clasificador_video import proxy_gen


def asegurar_subcarpeta_de_proyecto(carpeta_raiz: Path, proyecto: str) -> Path:
    """La subcarpeta de `proyecto` dentro de la carpeta de portafolio,
    creándola si falta. Nombre EXACTO del proyecto, mismo criterio que
    ya usa el Clipify normal con material y proxies."""
    destino = carpeta_raiz / proyecto
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def ruta_del_alias(carpeta_raiz: Path, proyecto: str, clip: Path) -> Path:
    """El alias de Finder lleva el nombre del original, dentro de la
    subcarpeta de su proyecto de origen."""
    return carpeta_raiz / proyecto / clip.name


def ruta_de_proxy(carpeta_raiz: Path, proyecto: str, clip: Path) -> Path:
    """El proxy vive junto al alias, con el sufijo `_proxy` del Clipify
    normal para no chocar con el alias (que conserva el nombre original)."""
    return proxy_gen.ruta_de_proxy(clip, carpeta_raiz / proyecto)


def asegurar_proxy(carpeta_raiz: Path, proyecto: str, clip: Path) -> Path:
    """El proxy a usar para un clip Elegido, sin generar de más.

    Orden (spec 2026-09-24, "proxies faltantes"):
    1. Si `proxy_gen` ya encuentra un proxy en alguno de los lugares que
       conoce junto al material, se reusa tal cual -- es el reuso "entre
       entregas" que pide la spec.
    2. Si ya hay uno en la carpeta de portafolio, se reusa.
    3. Si no, se genera uno nuevo dentro de la subcarpeta del proyecto.

    Devuelve la ruta del proxy, o `None` si `proxy_gen.generar` no devuelve
    nada (caso de las pruebas con un generador falso).
    """
    existente = proxy_gen.ruta_de_proxy_existente(clip, clip.parent)
    if existente is not None:
        return existente
    en_portafolio = ruta_de_proxy(carpeta_raiz, proyecto, clip)
    if en_portafolio.exists():
        return en_portafolio
    subcarpeta = asegurar_subcarpeta_de_proyecto(carpeta_raiz, proyecto)
    return proxy_gen.generar(clip, subcarpeta)
