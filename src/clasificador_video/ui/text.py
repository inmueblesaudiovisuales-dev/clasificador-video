# src/clasificador_video/ui/text.py
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLabel


class ElidedLabel(QLabel):
    """QLabel que corta con puntos suspensivos cuando no entra.

    QSS no tiene `text-overflow: ellipsis`: sin esto, un cuarto con nombre
    largo desborda el rail de 200 px o lo estira, y en los dos casos el
    layout deja de parecerse al mockup.
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802 -- override de Qt
        self._full_text = text
        super().setText(self._elided(text))

    def full_text(self) -> str:
        return self._full_text

    def resizeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        super().resizeEvent(event)
        super().setText(self._elided(self._full_text))

    def _elided(self, text: str) -> str:
        ancho = self.width()
        if ancho <= 0:
            return text
        return QFontMetrics(self.font()).elidedText(text, Qt.TextElideMode.ElideRight, ancho)


def plural_clips(cuantos: int) -> str:
    """«1 clip», «3 clips», «0 clips».

    Escrito una sola vez porque el mismo texto aparece en tres lugares --el
    encabezado del bin, su menu y el aviso de quitar del proyecto-- y tres
    copias de la misma regla se desincronizan solas. Bruno lee estos textos:
    «1 clips» se nota.
    """
    return "1 clip" if cuantos == 1 else f"{cuantos} clips"
