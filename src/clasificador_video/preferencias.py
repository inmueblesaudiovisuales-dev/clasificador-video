"""Preferencias globales de la app: importación rápida, carpeta de iCloud.

Viven en ``~/.clasificador_video/`` y con un criterio: si el archivo no
existe o está roto, se devuelve el valor por defecto en vez de romper la
app. Son globales a la app, no del proyecto: no viajan con el proyecto exportado ni
con el material.

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


def importacion_rapida_pregunta_antes(ruta: Path | None = None) -> bool:
    """Si la importación rápida por carpeta (spec
    2026-09-24-importacion-rapida-por-carpeta-design.md) debe preguntar
    antes de generar los proxies que falten, en vez de arrancar sola.

    Por default viene APAGADO -- arranca sola -- porque así lo pidió Bruno
    al construir el flujo. Quien quiere que pregunte lo prende una vez en
    Configuración."""
    return bool(_leer_todo(ruta).get("importacion_rapida_pregunta_antes", False))


def guardar_importacion_rapida_pregunta_antes(valor: bool, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = _leer_todo(ruta)
    datos["importacion_rapida_pregunta_antes"] = bool(valor)
    destino.write_text(json.dumps(datos), encoding="utf-8")


def carpeta_raiz_icloud(ruta: Path | None = None) -> Path | None:
    """La carpeta raíz de iCloud donde Bruno ya tiene armado
    `01. IAV/`, `02. PI/` y `03. Templates/` (spec
    2026-09-23-proyecto-colaborativo-icloud-design.md). `None` hasta que
    la configure -- sin ella, "Proyecto nuevo" con folio no puede armar
    la ruta y avisa que hace falta ponerla en Configuración."""
    valor = _leer_todo(ruta).get("carpeta_raiz_icloud")
    return Path(valor) if valor else None


def guardar_carpeta_raiz_icloud(carpeta: Path, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = _leer_todo(ruta)
    datos["carpeta_raiz_icloud"] = str(carpeta)
    destino.write_text(json.dumps(datos), encoding="utf-8")
