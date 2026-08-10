# src/clasificador_video/autosave.py
"""Leer la sesión escondida de la versión anterior.

Aquí vivía también `save_session`, la escritura atómica. Murió cuando el
proyecto pasó a ser un archivo con nombre: quien escribe ahora es
`proyecto.guardar`, que hace lo mismo y además limpia su temporal si la
escritura falla a medias. Dos escritores para el mismo archivo eran dos
cuidados que había que acordarse de aplicar en los dos lados —y el que se
usaba el 99% del tiempo era justo el que no los tenía—.

Lo que queda es la lectura, y solo la usa la migración de la sesión vieja.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_session(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, ValueError):
        return None
