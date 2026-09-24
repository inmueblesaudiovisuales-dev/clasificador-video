"""Nombres de clips de Premiere. Sin Qt."""
from __future__ import annotations

import json

_PREFIJO_POR_FLAG = {"destacado": "★", "pick": "✓", "reject": "✕"}


def nombre_de_clip(cuarto: str, numero: int, marca_de_camara: str, flag: str,
                    ancho: int = 2) -> str:
    base = f"{(cuarto or '').upper()}-{numero:0{ancho}d}"
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


def anchos_de_clip(clips: list) -> list[int]:
    """Cuántos dígitos necesita cada clip para que su cuarto siga ordenando
    bien alfabéticamente aunque pase de 99 tomas.

    Con dos dígitos fijos, el clip 100 de un cuarto queda ANTES que el 99 al
    ordenar por nombre -- "100" es menor que "99" letra por letra. El ancho
    se decide por el TOTAL de clips de ese cuarto, no por el número de cada
    uno: todos los clips de un mismo cuarto necesitan el mismo ancho, o el
    problema se repite entre ellos.
    """
    totales: dict[str, int] = {}
    for clip in clips or []:
        categoria = clip.get("categoria_path") if isinstance(clip, dict) else None
        llave = json.dumps(categoria or [])
        totales[llave] = totales.get(llave, 0) + 1
    resultado = []
    for clip in clips or []:
        categoria = clip.get("categoria_path") if isinstance(clip, dict) else None
        llave = json.dumps(categoria or [])
        resultado.append(max(2, len(str(totales[llave]))))
    return resultado
