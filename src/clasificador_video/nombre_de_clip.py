"""Nombres de clips de Premiere. Sin Qt."""
from __future__ import annotations

import json

_PREFIJO_POR_FLAG = {"destacado": "★ ", "pick": "✓ ", "reject": "✕ "}


def nombre_de_clip(cuarto: str, numero: int, marca_de_camara: str, flag: str) -> str:
    simbolo = _PREFIJO_POR_FLAG.get(flag, "")
    camara = f" [{marca_de_camara}]" if marca_de_camara else ""
    return f"{simbolo}{cuarto or ''} {numero:02d}{camara}"


def numeros_de_clip(clips: list) -> list[int]:
    contador: dict[str, int] = {}
    resultado = []
    for clip in clips or []:
        categoria = clip.get("categoria_path") if isinstance(clip, dict) else None
        llave = json.dumps(categoria or [])
        contador[llave] = contador.get(llave, 0) + 1
        resultado.append(contador[llave])
    return resultado
