# src/clasificador_video/ui/main_window.py
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QVBoxLayout, QWidget

from clasificador_video.category_path import CategoryTree
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.filmstrip import ClipThumbnail, Filmstrip


class MainWindow(QWidget):
    """Ventana unica (app-externa §3, opcion B): reproductor al centro,
    columna de cuartos a un lado, filmstrip abajo. Esta clase es la
    integracion -- toda la logica real vive en los modulos de las
    Milestones 1-4, wireados aqui.
    """

    def __init__(self, project_name: str, room_selection: RoomSelection, category_tree: CategoryTree, parent=None):
        super().__init__(parent)
        self.setWindowTitle(project_name)
        self.room_selection = room_selection
        self.category_tree = category_tree
        self.clips: list[Clip] = []
        self.current_index = 0
        self._router = KeyboardRouter(active_rooms=room_selection.active_rooms())

        self.room_list_widget = QListWidget()
        self.room_list_widget.addItems(room_selection.active_rooms())

        self.filmstrip = Filmstrip()

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(self.room_list_widget, stretch=0)
        root.addLayout(top, stretch=1)
        root.addWidget(self.filmstrip, stretch=0)

    @property
    def current_clip(self) -> Clip | None:
        if not self.clips:
            return None
        return self.clips[self.current_index]

    def load_clips(self, clips: list[Clip]) -> None:
        self.clips = clips
        self.current_index = 0
        self._refresh_filmstrip()

    def handle_key_press(self, key: str) -> None:
        if self.current_clip is None:
            return
        room_path = self._router.resolve_room_key(key)
        if room_path is not None:
            self.current_clip.categoria_path = room_path
            self._refresh_filmstrip()
            return
        action = self._router.resolve_action_key(key)
        if action is not None:
            self.current_clip.flag = action
            self._refresh_filmstrip()

    def _refresh_filmstrip(self) -> None:
        self.filmstrip.set_clips([
            ClipThumbnail(
                path=clip.ruta,
                thumbnail_path=None,
                room_label=clip.categoria_path[-1] if clip.categoria_path else "Sin clasificar",
                flag=clip.flag,
            )
            for clip in self.clips
        ])
