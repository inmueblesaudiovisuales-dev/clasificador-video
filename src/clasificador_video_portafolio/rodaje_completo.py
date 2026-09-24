"""Ver el rodaje completo de un proyecto importado, más allá de lo que
el .prproj dice que se usó. No depende de un .cvproj: la carpeta se
deduce de los clips ya conocidos.

Spec: docs/superpowers/specs/2026-09-24-modo-portafolio-design.md.
"""
from __future__ import annotations

from pathlib import Path

from clasificador_video.ingest import VIDEO_EXTENSIONS


def deducir_carpeta(rutas: list[Path]) -> Path | None:
    """La carpeta padre común, o ``None`` si las rutas no coinciden."""
    if not rutas:
        return None
    padres = {ruta.parent for ruta in rutas}
    return padres.pop() if len(padres) == 1 else None


def listar_videos(carpeta: Path) -> list[Path]:
    """Videos directos de ``carpeta``, ordenados por nombre."""
    return sorted(
        ruta for ruta in carpeta.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in VIDEO_EXTENSIONS
    )
