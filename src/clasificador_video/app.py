# src/clasificador_video/app.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from clasificador_video.autosave import load_session
from clasificador_video.category_path import CategoryTree
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow
from clasificador_video.ui.room_config_dialog import RoomConfigDialog

SESSION_PATH = Path.home() / ".clasificador_video" / "sesion.json"


def _rebuild_room_selection(rooms: list[str]) -> RoomSelection:
    sel = RoomSelection()
    for room in rooms:
        sel.toggle(room)
    return sel


def _clip_from_dict(d: dict) -> Clip:
    return Clip(
        orden=d["orden"],
        ruta=Path(d["ruta"]),
        categoria_path=list(d.get("categoria_path") or []),
        fps=d["fps"],
        in_frame=d.get("in_frame"),
        out_frame=d.get("out_frame"),
        flag=d.get("flag", "none"),
        ruta_proxy=Path(d["ruta_proxy"]) if d.get("ruta_proxy") else None,
    )


def _restore_session(window: MainWindow, session_path: Path) -> None:
    data = load_session(session_path)
    if data is None:
        return
    if (
        QMessageBox.question(
            None, "Sesión guardada",
            "Se encontró una sesión sin terminar. ¿Recuperarla?",
        )
        != QMessageBox.Yes
    ):
        return
    window.room_selection = _rebuild_room_selection(data.get("rooms", []))
    window.room_list_widget.clear()
    window.room_list_widget.addItems(window.room_selection.active_rooms())
    tree_data = data.get("category_tree", {})
    for parent, subrooms in tree_data.items():
        for subroom in subrooms:
            window.category_tree.attach_subroom(parent, subroom)
    window._router = KeyboardRouter(
        active_rooms=window.room_selection.active_rooms(),
        subrooms=dict(tree_data),
    )
    window.load_clips([_clip_from_dict(d) for d in data.get("clips", [])])


def arrancar(
    video_factory: Callable[..., object] | None = None,
    session_path: Path | None = None,
) -> MainWindow | None:
    """Abre el dialogo de cuartos; si el usuario acepta, construye la
    ventana principal con esa seleccion. None si cancela.
    """
    if session_path is None:
        session_path = SESSION_PATH
    dialog = RoomConfigDialog(project_name="Shooting sin nombre")
    if dialog.exec() != QDialog.Accepted:
        return None
    window = MainWindow(
        project_name="Shooting sin nombre",
        room_selection=dialog.selection,
        category_tree=CategoryTree(),
        video_factory=video_factory,
    )
    window.session_path = session_path
    _restore_session(window, session_path)
    window.resize(1100, 700)
    return window


def main() -> None:
    app = QApplication(sys.argv)
    window = arrancar()
    if window is None:
        sys.exit(0)
    window.show()
    if window.clips:
        try:
            window.video_widget.open_clip(window.clips[0].ruta)
        except RuntimeError:
            pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
