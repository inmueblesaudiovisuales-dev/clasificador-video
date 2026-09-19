"""Preferencias globales de la app: hoy, un solo ajuste (modo económico).

Mismo lugar que la llave --``~/.clasificador_video/``-- y mismo criterio:
si el archivo no existe o está roto, se devuelve el valor por defecto en
vez de romper la app. Es global a la app, no del proyecto: no viaja con el
manifest ni con el material.

Sin Qt.
"""
from __future__ import annotations

import json
from pathlib import Path

RUTA = Path.home() / ".clasificador_video" / "preferencias.json"


def _destino(ruta: Path | None) -> Path:
    return RUTA if ruta is None else ruta


def _leer_todo(ruta: Path | None) -> dict:
    try:
        datos = json.loads(_destino(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def modo_economico(ruta: Path | None = None) -> bool:
    """Menos miniaturas a la vez, para computadoras con menos RAM o CPU.

    Por default viene PRENDIDO: la app no sabe en que Mac va a correr la
    primera vez, y economizar de mas solo cuesta un poco de tiempo --
    economizar de menos en una Mac chica se siente como que la app se
    congela. Quien tiene de sobra lo apaga una vez en Configuracion y se
    queda apagado.
    """
    return bool(_leer_todo(ruta).get("modo_economico", True))


def guardar_modo_economico(valor: bool, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = _leer_todo(ruta)
    datos["modo_economico"] = bool(valor)
    destino.write_text(json.dumps(datos), encoding="utf-8")


def carpeta_de_proyectos_premiere(ruta: Path | None = None) -> Path | None:
    """Dónde busca `buscar_prproj.buscar_por_folio`. `None` hasta que
    Bruno la ponga en Configuración -- sin ella, "Subir a Drive" cae
    directo al selector manual."""
    valor = _leer_todo(ruta).get("carpeta_de_proyectos_premiere")
    return Path(valor) if valor else None


def guardar_carpeta_de_proyectos_premiere(carpeta: Path, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = _leer_todo(ruta)
    datos["carpeta_de_proyectos_premiere"] = str(carpeta)
    destino.write_text(json.dumps(datos), encoding="utf-8")
