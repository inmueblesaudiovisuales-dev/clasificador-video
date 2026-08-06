# src/clasificador_video/ui/room_config_dialog.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from clasificador_video.rooms import MASTER_ROOM_LIST, RoomSelection


class RoomConfigDialog(QDialog):
    """Dialogo previo a clasificar (spec app-externa §5): marcar cuartos
    de la lista fija + agregar personalizados. Se hace una vez por
    shooting, no es una pantalla separada del flujo principal.
    """

    def __init__(self, project_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configurar cuartos — {project_name}")
        self.selection = RoomSelection()
        self.chip_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)

        grid = QGridLayout()
        for i, room in enumerate(MASTER_ROOM_LIST):
            button = QPushButton(room)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, r=room: self._on_chip_clicked(r))
            self.chip_buttons[room] = button
            grid.addWidget(button, i // 2, i % 2)
        layout.addLayout(grid)

        custom_row = QHBoxLayout()
        self.custom_room_input = QLineEdit()
        self.custom_room_input.setPlaceholderText("Agregar cuarto personalizado")
        self.add_custom_button = QPushButton("+ Agregar")
        self.add_custom_button.clicked.connect(self._on_add_custom)
        custom_row.addWidget(self.custom_room_input)
        custom_row.addWidget(self.add_custom_button)
        layout.addLayout(custom_row)

        self.start_button = QPushButton("Empezar a clasificar →")
        layout.addWidget(self.start_button)

    def _on_chip_clicked(self, room: str) -> None:
        self.selection.toggle(room)

    def _on_add_custom(self) -> None:
        name = self.custom_room_input.text().strip()
        if name:
            self.selection.add_custom(name)
            self.custom_room_input.clear()
