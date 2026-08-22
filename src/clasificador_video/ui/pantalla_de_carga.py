# src/clasificador_video/ui/pantalla_de_carga.py
"""La ventanita que se ve mientras un proyecto abre.

Existe porque abrir un proyecto grande no es instantaneo aunque ya no se
congele: con los 205 clips de Bruno son ~2.8 s de portadas, y con 500 serian
mas. Sin nada en pantalla esos segundos se sienten como un cuelgue -- que es
literalmente lo que Bruno reporto («se pone mi mouse con la bolita de arco
iris»).

NO es un dialogo: no tiene botones ni se puede cerrar, porque no hay ninguna
decision que tomar. Solo dice que esta trabajando y en que va.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from clasificador_video.ui import theme

ANCHO = 380


class PantallaDeCarga(QWidget):
    """Nombre del proyecto, cuantos clips trae, y una barra que avanza."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaDeCarga")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Sin barra de titulo y siempre encima: es un aviso, no una ventana
        # con la que se pueda interactuar.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedWidth(ANCHO)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 22, 24, 22)
        raiz.setSpacing(10)

        self.titulo = QLabel("")
        self.titulo.setObjectName("cargaTitulo")
        self.detalle = QLabel("")
        self.detalle.setObjectName("cargaDetalle")
        self.barra = QProgressBar()
        self.barra.setObjectName("cargaBarra")
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(4)

        raiz.addWidget(self.titulo)
        raiz.addWidget(self.detalle)
        raiz.addWidget(self.barra)
        self.hide()

    def abrir(self, proyecto: str, clips: int) -> None:
        """Muestra la pantalla para ESE proyecto.

        El nombre va aqui y no un «Cargando…» generico para que se vea que
        abrio el que elegiste: con una lista de recientes de diez, picarle al
        renglon equivocado es facil, y enterarse tres segundos despues es
        peor que enterarse ahora.
        """
        self.titulo.setText(proyecto)
        self.detalle.setText(f"Preparando {clips} clips…")
        self.barra.setRange(0, max(1, clips))
        self.barra.setValue(0)
        self.adjustSize()
        self.show()
        self.raise_()

    def avanzar(self, hechos: int) -> None:
        self.barra.setValue(hechos)

    def cerrar(self) -> None:
        self.hide()
