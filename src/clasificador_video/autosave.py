# src/clasificador_video/autosave.py
from __future__ import annotations

import json
import os
from pathlib import Path


def save_session(path: Path, data: dict) -> None:
    """Escribe `data` como JSON de forma atomica: archivo temporal + rename.

    Si la app se cierra a medio escribir, el rename atomico de POSIX
    garantiza que `path` siempre queda o con el contenido viejo completo,
    o con el nuevo completo -- nunca a medias.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    os.replace(tmp_path, path)


def load_session(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, ValueError):
        return None
