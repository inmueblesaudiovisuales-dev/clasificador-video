# src/clasificador_video/ui/title_bar.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from clasificador_video.ui import theme


def _boton(texto: str, atajo: str, object_name: str) -> QPushButton:
    boton = QPushButton(f"{texto}  {atajo}")
    boton.setObjectName(object_name)
    # sin esto, la tecla Espacio activaria el boton enfocado en vez de
    # reproducir el clip
    boton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return boton


class TitleBar(QWidget):
    """Barra superior de 36 px: proyecto, guardado y las dos acciones que
    no son de clasificacion.

    Es una de las dos unicas bandas horizontales que el diseño admite (la
    otra es la barra de estado). Todo lo demas vive en columnas o flotando
    sobre el video.
    """

    export_requested = Signal()
    rooms_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(theme.TITLEBAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 0, 13, 0)
        layout.setSpacing(13)

        self.mark = QLabel("")
        self.mark.setObjectName("appMark")
        self.mark.setFixedSize(17, 17)

        self.project_label = QLabel("")
        self.project_label.setObjectName("projectLabel")
        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("projectSubtitle")

        self.saved_led = QLabel("")
        self.saved_led.setObjectName("savedLed")
        self.saved_led.setFixedSize(6, 6)
        self.saved_label = QLabel("")
        self.saved_label.setObjectName("savedIndicator")

        self.rooms_button = _boton("Cuartos", "⌘R", "railButton")
        self.export_button = _boton("Exportar a Premiere", "⌘E", "exportButton")
        self.rooms_button.clicked.connect(self.rooms_requested.emit)
        self.export_button.clicked.connect(self.export_requested.emit)

        layout.addWidget(self.mark)
        layout.addWidget(self.project_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch(1)
        layout.addWidget(self.saved_led)
        layout.addWidget(self.saved_label)
        layout.addWidget(self.rooms_button)
        layout.addWidget(self.export_button)

    def set_project(self, nombre: str, total_clips: int) -> None:
        self.project_label.setText(nombre)
        self.subtitle_label.setText(f"{total_clips} clips · Sony FX30")

    def set_saved_seconds(self, segundos: int | None) -> None:
        self.saved_label.setText("" if segundos is None else f"Guardado hace {segundos} s")
        self.saved_led.setVisible(segundos is not None)
