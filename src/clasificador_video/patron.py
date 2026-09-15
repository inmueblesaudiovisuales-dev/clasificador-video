"""El patrón de recorrido de Bruno, leído del Markdown.

**Un solo dueño: el Markdown.** Es el archivo que Bruno edita a mano cuando
algo no le cuadra, y de ahí sale el texto que viaja en el prompt. No hay
copia en ningún otro lado -- dos copias del mismo dato que se editan por
separado se desincronizan en el primer cambio de opinión.

Sin Qt.
"""
from __future__ import annotations

from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "docs" / "patron-de-recorrido" / "MI-PATRON.md"


def leer(ruta: Path | None = None) -> str:
    """El documento entero, o "" si no está.

    Que no esté no es un error: la guía se arma igual, nada más sin el
    patrón adentro, y entonces lo que sugiere es el orden de manual. Reventar
    aquí dejaría a Bruno sin poder pedir la guía por un archivo de
    documentación.
    """
    destino = RUTA if ruta is None else ruta
    try:
        return destino.read_text(encoding="utf-8")
    except OSError:
        return ""
