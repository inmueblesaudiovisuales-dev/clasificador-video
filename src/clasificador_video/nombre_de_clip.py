"""Nombres de clips de Premiere. Sin Qt."""
from __future__ import annotations

import json

_PREFIJO_POR_FLAG = {"destacado": "★", "pick": "✓", "reject": "✕"}


def nombre_de_clip(cuarto: str, numero: int, marca_de_camara: str, flag: str) -> str:
    base = f"{(cuarto or '').upper()}-{numero:02d}"
    marca = _PREFIJO_POR_FLAG.get(flag, "")
    partes = [base] + ([marca] if marca else [])
    if marca_de_camara:
        partes.append(f"[{marca_de_camara}]")
    return " ".join(partes)


def numeros_de_clip(clips: list) -> list[int]:
    contador: dict[str, int] = {}
    resultado = []
    for clip in clips or []:
        categoria = clip.get("categoria_path") if isinstance(clip, dict) else None
        llave = json.dumps(categoria or [])
        contador[llave] = contador.get(llave, 0) + 1
        resultado.append(contador[llave])
    return resultado
