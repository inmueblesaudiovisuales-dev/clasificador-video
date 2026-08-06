# src/clasificador_video/app.py
from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtWidgets import QApplication, QDialog

from clasificador_video.category_path import CategoryTree
from clasificador_video.ui.main_window import MainWindow
from clasificador_video.ui.room_config_dialog import RoomConfigDialog


def arrancar(video_factory: Callable[..., object] | None = None) -> MainWindow | None:
    """Abre el dialogo de cuartos; si el usuario acepta, construye la
    ventana principal con esa seleccion. None si cancela.
    """
    dialog = RoomConfigDialog(project_name="Shooting sin nombre")
    if dialog.exec() != QDialog.Accepted:
        return None
    window = MainWindow(
        project_name="Shooting sin nombre",
        room_selection=dialog.selection,
        category_tree=CategoryTree(),
        video_factory=video_factory,
    )
    window.resize(1100, 700)
    return window


def main() -> None:
    app = QApplication(sys.argv)
    window = arrancar()
    if window is None:
        sys.exit(0)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
