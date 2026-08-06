# src/clasificador_video/app.py
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from clasificador_video.category_path import CategoryTree
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow(
        project_name="Sin proyecto",
        room_selection=RoomSelection(),
        category_tree=CategoryTree(),
    )
    window.resize(1100, 700)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
