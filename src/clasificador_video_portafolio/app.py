"""Punto de entrada de Clipify Portafolio.

Ventana propia, sin heredar ni componer nada de
`clasificador_video.ui.main_window.MainWindow`: son dos apps, un solo
motor. Ver la spec para el porqué de la separación.
"""
from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QVBoxLayout, QWidget

from clasificador_video_portafolio.portafolio import Portafolio
from clasificador_video_portafolio.ui.pantalla_importar import PantallaImportar


class VentanaPortafolio(QWidget):
    """Ventana raíz de la app de Portafolio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clipify Portafolio")
        self.modulo_actual = "importar"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.pantalla_importar = PantallaImportar(
            Portafolio(), elegir_ruta=self._elegir_ruta_portafolio
        )
        layout.addWidget(self.pantalla_importar)

    def _elegir_ruta_portafolio(self) -> Path | None:
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Crear portafolio",
            "Mi Portafolio.cvportafolio",
            "Portafolio de Clipify (*.cvportafolio)",
        )
        if not ruta:
            return None
        ruta_portafolio = Path(ruta)
        if ruta_portafolio.suffix != ".cvportafolio":
            ruta_portafolio = ruta_portafolio.with_suffix(".cvportafolio")
        return ruta_portafolio


def main() -> None:
    app = QApplication(sys.argv)
    ventana = VentanaPortafolio()
    ventana.resize(1200, 800)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
