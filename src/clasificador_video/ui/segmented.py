# src/clasificador_video/ui/segmented.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QWidget):
    """Control segmentado tipo `Full ½ ¼ ⅛` del mockup: varias opciones
    pegadas, una sola activa.

    Reemplaza al `QComboBox` de calidad, que no existe en el diseño. La F8
    lo reusa para la velocidad de reproduccion.
    """

    selected = Signal(str)

    def __init__(self, options: list[str], parent=None,
                 object_name: str = "segmentedControl"):
        super().__init__(parent)
        # el nombre distingue variantes en la hoja de estilos: el control de
        # velocidad pinta su segmento activo en ambar (ver theme.py), y eso
        # se resuelve con un selector de descendencia, no con QSS por widget.
        self.setObjectName(object_name)
        # Sin esta bandera un QWidget puro IGNORA el `background-color` de
        # QSS: solo pintan los widgets que ya dibujan fondo (QPushButton y
        # compania). El control quedaba sin su caja oscura y sobre una pared
        # blanca --que en fotografia de inmuebles es la mitad del material--
        # los numeros claros se volvian ilegibles. Venia asi desde la F2.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.buttons: list[QPushButton] = []
        for option in options:
            button = QPushButton(option)
            button.setObjectName("segmentedButton")
            button.setCheckable(True)
            # sin esto, la tecla Espacio activaria el boton enfocado en vez
            # de reproducir el clip
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(lambda _checked, text=option: self.selected.emit(text))
            self._group.addButton(button)
            layout.addWidget(button)
            self.buttons.append(button)

        if self.buttons:
            self.buttons[0].setChecked(True)

    def current(self) -> str:
        for button in self.buttons:
            if button.isChecked():
                return button.text()
        return ""

    def set_current(self, option: str) -> None:
        """Sincroniza el control desde el estado, SIN emitir `selected` --
        emitirla haria que refrescar la UI dispare el handler que cambia el
        perfil del reproductor, en bucle."""
        for button in self.buttons:
            if button.text() == option:
                blocked = button.blockSignals(True)
                button.setChecked(True)
                button.blockSignals(blocked)
                return
