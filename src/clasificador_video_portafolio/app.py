"""Punto de entrada de Clipify Portafolio.

Ventana propia, sin heredar ni componer nada de
`clasificador_video.ui.main_window.MainWindow`: son dos apps, un solo
motor. Ver la spec para el porqué de la separación.
"""
from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from clasificador_video_portafolio.portafolio import Portafolio
from clasificador_video_portafolio.ui.pantalla_importar import PantallaImportar
from clasificador_video_portafolio.ui.pantalla_revisar import PantallaRevisar

ESTILO_VENTANA = """
VentanaPortafolio { background: #101216; color: #e6e9ee; font-family: -apple-system, "Helvetica Neue", sans-serif; }
QPushButton { background: #16191e; border: 1px solid #262b33; border-radius: 5px; color: #9aa3b0; padding: 5px 9px; font-size: 11px; }
QPushButton:checked { background: #1d2128; color: #e6e9ee; }
QStackedWidget { background: #0a0b0d; }
"""


class VentanaPortafolio(QWidget):
    """Ventana raíz de la app de Portafolio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clipify Portafolio")
        self.setObjectName("VentanaPortafolio")
        self.setStyleSheet(ESTILO_VENTANA)
        self.modulo_actual = "importar"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.portafolio = Portafolio()
        barra = QHBoxLayout()
        barra.setContentsMargins(12, 7, 12, 7)
        titulo = QLabel("Clipify Portafolio")
        titulo.setStyleSheet("color: #e6e9ee; font-weight: 600;")
        barra.addWidget(titulo)
        barra.addStretch()
        self.botones_modulo: dict[str, QPushButton] = {}
        for clave, texto in (("importar", "① Importar"), ("revisar", "② Revisar"), ("armar", "③ Armar y entregar")):
            boton = QPushButton(texto)
            boton.setCheckable(True)
            boton.clicked.connect(lambda _, c=clave: self.mostrar_modulo(c))
            self.botones_modulo[clave] = boton
            barra.addWidget(boton)
        layout.addLayout(barra)
        self.modulos = QStackedWidget()
        self.pantalla_importar = PantallaImportar(self.portafolio, elegir_ruta=self._elegir_ruta_portafolio)
        self.pantalla_revisar = PantallaRevisar(self.portafolio)
        self.pantalla_armar = QLabel("Armar y entregar estará disponible en una siguiente fase.")
        self.pantalla_armar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.modulos.addWidget(self.pantalla_importar)
        self.modulos.addWidget(self.pantalla_revisar)
        self.modulos.addWidget(self.pantalla_armar)
        layout.addWidget(self.modulos, 1)
        self.mostrar_modulo("importar")

    def mostrar_modulo(self, modulo: str) -> None:
        """Cambia de tarea sin mezclar la lógica de la futura fase Armar."""
        indices = {"importar": 0, "revisar": 1, "armar": 2}
        self.modulo_actual = modulo
        self.modulos.setCurrentIndex(indices[modulo])
        for clave, boton in self.botones_modulo.items():
            boton.setChecked(clave == modulo)
        if modulo == "revisar":
            self.pantalla_revisar.ruta_portafolio = self.pantalla_importar.ruta_portafolio
            self.pantalla_revisar.actualizar_rail()

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
