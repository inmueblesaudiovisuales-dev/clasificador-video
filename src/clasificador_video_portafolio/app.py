"""Punto de entrada de Clipify Portafolio.

Ventana propia, sin heredar ni componer nada de
`clasificador_video.ui.main_window.MainWindow`: son dos apps, un solo
motor. Ver la spec para el porqué de la separación.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class VentanaPortafolio(QWidget):
    """Ventana raíz de la app de Portafolio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clipify Portafolio")
        self.modulo_actual = "importar"
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Clipify Portafolio — módulo Importar"))


def main() -> None:
    app = QApplication(sys.argv)
    ventana = VentanaPortafolio()
    ventana.resize(1200, 800)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
