"""Preferencias globales de la app: el modo económico y el modo rápido.

Viven en ``~/.clasificador_video/`` y con un criterio: si el archivo no
existe o está roto, se devuelve el valor por defecto en vez de romper la
app. Son globales a la app, no del proyecto: no viajan con el manifest ni
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


def modo_rapido(ruta: Path | None = None) -> bool:
    """Miniaturas chicas y pocas, como el modo económico, pero SIN su
    freno de paralelismo (ver `preferencias.md` -- spec
    2026-09-20-modo-rapido-de-miniaturas-design.md). Independiente de
    `modo_economico`: los dos se combinan en `main_window.py`.

    Por default apagado -- a diferencia de económico, esto no evita que
    la app se trabe, cambia cómo se ve el escrubeo, así que es Bruno
    quien lo prende cuando lo quiere.
    """
    return bool(_leer_todo(ruta).get("modo_rapido", False))


def guardar_modo_rapido(valor: bool, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = _leer_todo(ruta)
    datos["modo_rapido"] = bool(valor)
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
