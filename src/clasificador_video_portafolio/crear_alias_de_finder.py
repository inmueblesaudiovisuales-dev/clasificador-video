"""El alias real de Finder para un clip Elegido en la carpeta de
portafolio -- spec 2026-09-24-modo-portafolio-design.md, Fase 4.5.

Un alias de Finder no es un symlink (`os.symlink`): es un formato propio
de macOS que guarda una referencia al volumen + inodo del archivo, y
sigue resolviendo si el original se renombra o se mueve dentro del
mismo volumen. Se construye con la API nativa de Cocoa vía `pyobjc`
(`NSURL.bookmarkDataWithOptions_...` + `writeBookmarkData_toURL_options_error_`
con `NSURLBookmarkCreationSuitableForBookmarkFile`), decisión tomada con
Bruno en vez de la alternativa por `osascript`/Finder scripting: es la
API "correcta" del sistema y ya se aceptó la dependencia nueva
(`pyobjc-framework-Cocoa`). Solo funciona en macOS.
"""
from __future__ import annotations

from pathlib import Path

from Foundation import NSURL, NSURLBookmarkCreationSuitableForBookmarkFile


def crear(original: Path, destino: Path) -> None:
    """Crea el alias de Finder en `destino`, apuntando a `original`.
    Crea la carpeta contenedora si falta. No hace nada si `destino` ya
    existe -- nunca se pisa un alias ya creado."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        return
    origen_url = NSURL.fileURLWithPath_(str(original))
    datos_bookmark, error = origen_url.bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error_(
        NSURLBookmarkCreationSuitableForBookmarkFile, None, None, None
    )
    if datos_bookmark is None:
        raise OSError(f"no se pudo crear el bookmark para {original}: {error}")
    destino_url = NSURL.fileURLWithPath_(str(destino))
    exito, error = NSURL.writeBookmarkData_toURL_options_error_(
        datos_bookmark, destino_url, 0, None
    )
    if not exito:
        raise OSError(f"no se pudo escribir el alias en {destino}: {error}")


def resolver(alias: Path) -> Path:
    """La ruta actual del archivo al que apunta un alias creado con
    `crear`, siguiendo el volumen + inodo aunque el original se haya
    renombrado o movido dentro del mismo volumen."""
    alias_url = NSURL.fileURLWithPath_(str(alias))
    datos_bookmark, error = NSURL.bookmarkDataWithContentsOfURL_error_(alias_url, None)
    if datos_bookmark is None:
        raise OSError(f"no se pudo leer el alias en {alias}: {error}")
    resuelto, es_obsoleto, error = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
        datos_bookmark, 0, None, None, None
    )
    if resuelto is None:
        raise OSError(f"no se pudo resolver el alias en {alias}: {error}")
    return Path(resuelto.path())
