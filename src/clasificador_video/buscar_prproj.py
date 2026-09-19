"""Encontrar el .prproj de un proyecto por su folio, en la carpeta raíz
donde Bruno guarda todos sus proyectos de Premiere.

El nombre del proyecto de Clipify YA ES el folio de Bruno
(`IAV-2609.10-A`, `2607.09`...), así que no hace falta pedirle la ruta
cada vez que quiere subir a Drive: se busca recursivamente bajo la
carpeta raíz (que sí se pregunta UNA vez, en Configuración) un `.prproj`
cuyo nombre contenga ese folio.

Sin Qt: recorre disco, nada más. El diálogo que MUESTRA el resultado
--y que deja cambiarlo a mano-- vive en la interfaz.
"""
from __future__ import annotations

from pathlib import Path
import re


def buscar_por_folio(carpeta_raiz: Path, folio: str) -> list[Path]:
    """Todas las coincidencias, de más nueva a más vieja por fecha de
    modificación. Vacía si la carpeta no existe, no se puede leer, o
    ningún `.prproj` contiene el folio como substring exacto.
    """
    if not folio:
        return []
    try:
        candidatos = [
            p for p in carpeta_raiz.rglob("*.prproj")
            if re.search(
                rf"(?<![A-Za-z0-9]){re.escape(folio)}(?![A-Za-z0-9])",
                p.stem,
            )
        ]
    except OSError:
        return []
    return sorted(candidatos, key=lambda p: p.stat().st_mtime, reverse=True)
