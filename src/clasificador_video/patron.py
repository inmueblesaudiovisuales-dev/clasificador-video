"""El patrón de recorrido de Bruno, leído del Markdown.

**Un solo dueño: el Markdown.** Es el archivo que Bruno edita a mano cuando
algo no le cuadra, y de ahí sale el texto que viaja en el prompt. No hay
copia en ningún otro lado -- dos copias del mismo dato que se editan por
separado se desincronizan en el primer cambio de opinión.

Sin Qt.
"""
from __future__ import annotations

import sys
from pathlib import Path

RELATIVA = Path("docs") / "patron-de-recorrido" / "MI-PATRON.md"


def _ruta() -> Path:
    """Donde está el documento, corriendo del repo o de la app instalada.

    NO ES LO MISMO, y dar por hecho que sí costó un bug callado: la ruta del
    repo --tres carpetas arriba de este archivo-- no existe dentro del
    paquete, así que en el `.dmg` el patrón no se encontraba y la guía salía
    con el orden de manual en vez del de Bruno. Sin fallar, nada más
    genérica, que es la peor forma de fallar.

    PyInstaller deja lo que copió en `sys._MEIPASS`; la receta de
    `empaque/clipify.spec` mete el documento ahí con esta misma ruta
    relativa, para que las dos formas de correr busquen en el mismo sitio.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / RELATIVA
    return Path(__file__).resolve().parents[2] / RELATIVA


# Se mantiene el nombre de antes: es lo que el resto del repo conoce.
RUTA = Path(__file__).resolve().parents[2] / RELATIVA


def leer(ruta: Path | None = None) -> str:
    """El documento entero, o "" si no está.

    Que no esté no es un error: la guía se arma igual, nada más sin el
    patrón adentro, y entonces lo que sugiere es el orden de manual. Reventar
    aquí dejaría a Bruno sin poder pedir la guía por un archivo de
    documentación.
    """
    destino = _ruta() if ruta is None else ruta
    try:
        return destino.read_text(encoding="utf-8")
    except OSError:
        return ""
