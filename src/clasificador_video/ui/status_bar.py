# src/clasificador_video/ui/status_bar.py
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from clasificador_video.ui import theme


class StatusBar(QWidget):
    """Barra inferior de 24 px: los datos que se CONSULTAN, no los que se
    persiguen.

    Aca van resolucion, fps, orientacion y ruta del volumen -- informacion
    de referencia que en el diseño viejo ocupaba un panel de 200 px al
    costado del video.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(theme.STATUSBAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 0, 13, 0)
        layout.setSpacing(15)

        self.clip_label = QLabel("")
        self.clip_label.setObjectName("statusMono")
        self.unclassified_label = QLabel("")
        self.unclassified_label.setObjectName("unclassifiedBadge")
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
        if not nombre or not tamano:
            self.clip_label.setText("")
            return
        ancho, alto = tamano
        orientacion = "vertical" if alto > ancho else "horizontal"
        partes = [nombre, f"{ancho}×{alto}"]
        if fps:
            partes.append(f"{fps:.2f} fps")
        if rotacion:
            partes.append(f"{orientacion} (rot {rotacion}°)")
        else:
            partes.append(orientacion)
        self.clip_label.setText(" · ".join(partes))

    def set_unclassified(self, cuantos: int) -> None:
        self.unclassified_label.setText(
            f"⚠ {cuantos} sin clasificar" if cuantos else ""
        )

    def set_volume(self, ruta: str) -> None:
        self.volume_label.setText(ruta)
