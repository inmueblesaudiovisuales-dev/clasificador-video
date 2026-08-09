# src/clasificador_video/ui/status_bar.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from clasificador_video.probe import orientacion_de
from clasificador_video.ui import theme


class StatusBar(QWidget):
    """Barra inferior de 24 px: los datos que se CONSULTAN, no los que se
    persiguen.

    Aca van resolucion, fps, orientacion y ruta del volumen -- informacion
    de referencia que en el diseño viejo ocupaba un panel de 200 px al
    costado del video.
    """

    unclassified_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(theme.STATUSBAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 0, 13, 0)
        layout.setSpacing(15)

        self.clip_label = QLabel("")
        self.clip_label.setObjectName("statusMono")
        # es un BOTON, no una etiqueta: DECISIONES.md lo llama «literalmente
        # el boton de segui trabajando» -- clickearlo filtra por lo que falta
        self.unclassified_label = QPushButton("")
        self.unclassified_label.setObjectName("unclassifiedBadge")
        self.unclassified_label.setFlat(True)
        self.unclassified_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.unclassified_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.unclassified_label.hide()
        self.unclassified_label.clicked.connect(self.unclassified_clicked.emit)
        self.volume_label = QLabel("")
        self.volume_label.setObjectName("statusMono")

        layout.addWidget(self.clip_label)
        layout.addWidget(self.unclassified_label)
        layout.addStretch(1)
        layout.addWidget(self.volume_label)

    def set_clip_info(
        self,
        nombre: str | None,
        tamano: tuple[int, int] | None,
        fps: float | None,
        rotacion: int | None,
    ) -> None:
        if not nombre:
            self.clip_label.setText("")
            return
        # se muestra lo que se sabe: en una sesion restaurada de disco no se
        # volvio a correr ffprobe y no hay tamaño, pero el nombre del archivo
        # tiene que verse igual.
        partes = [nombre]
        if tamano:
            ancho, alto = tamano
            partes.append(f"{ancho}×{alto}")
        if fps:
            partes.append(f"{fps:.2f} fps")
        if tamano:
            ancho, alto = tamano
            # la MISMA funcion que decide la orientacion del manifest: si
            # la barra dice «vertical» y el manifest declara «horizontal»,
            # una de las dos miente y nadie se entera hasta Premiere.
            orientacion = orientacion_de(ancho, alto)
            partes.append(
                f"{orientacion} (rot {rotacion}°)" if rotacion else orientacion
            )
        self.clip_label.setText(" · ".join(partes))

    def set_unclassified(self, cuantos: int) -> None:
        self.unclassified_label.setText(
            f"⚠ {cuantos} sin clasificar — click para filtrarlos" if cuantos else ""
        )
        self.unclassified_label.setVisible(bool(cuantos))

    def set_volume(self, ruta: str) -> None:
        self.volume_label.setText(ruta)
