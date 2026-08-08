# src/clasificador_video/ui/tool_column.py
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from clasificador_video.ui import theme


class _Indicador(QWidget):
    """Cuadro de estado con su tecla debajo.

    En la F2 son INDICADORES, no botones: reflejan el estado del clip
    actual. En una app que se maneja con teclado, un boton que nadie va a
    clickear seria 56 px de ancho decorativos.
    """

    def __init__(self, etiqueta: str, tecla: str, canal: str, parent=None):
        super().__init__(parent)
        self.setObjectName("toolIndicator")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(40, 40)
        self.setProperty("canal", canal)
        self.setProperty("on", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self.label = QLabel(etiqueta)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key = QLabel(tecla)
        self.key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        layout.addWidget(self.key)

    def set_on(self, encendido: bool) -> None:
        # propiedad dinamica en vez de hoja de estilo inline: el color sale
        # del QSS con tokens, no de un hexadecimal pegado aca
        self.setProperty("on", bool(encendido))
        self.style().unpolish(self)
        self.style().polish(self)

    def is_on(self) -> bool:
        return bool(self.property("on"))


class ToolColumn(QWidget):
    """Columna de 56 px pegada al video con el estado del clip actual.

    Va en vertical a proposito: una columna cuesta ancho, y ancho es
    justo lo que sobra cuando el video es vertical.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolColumn")
        self.setFixedWidth(theme.TOOLCOL_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._caption("RANGO"))
        self.in_indicator = _Indicador("IN", "I", "rango")
        self.out_indicator = _Indicador("OUT", "O", "rango")
        layout.addWidget(self.in_indicator)
        layout.addWidget(self.out_indicator)

        layout.addSpacing(6)
        layout.addWidget(self._caption("ESTADO"))
        self.pick_indicator = _Indicador("PICK", "P", "pick")
        self.reject_indicator = _Indicador("REJ", "X", "reject")
        layout.addWidget(self.pick_indicator)
        layout.addWidget(self.reject_indicator)
        layout.addStretch(1)

    def _caption(self, texto: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setObjectName("toolCaption")
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme.apply_letter_spacing(etiqueta)
        return etiqueta

    def set_range(self, in_frame: int | None, out_frame: int | None) -> None:
        self.in_indicator.set_on(in_frame is not None)
        self.out_indicator.set_on(out_frame is not None)

    def set_flag(self, flag: str) -> None:
        self.pick_indicator.set_on(flag == "pick")
        self.reject_indicator.set_on(flag == "reject")
