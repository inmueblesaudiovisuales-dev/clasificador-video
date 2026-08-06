# src/clasificador_video/ui/main_window.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QRunnable, QThreadPool, Signal
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.category_path import CategoryTree
from clasificador_video.ingest import IngestTree
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip
from clasificador_video.player import QUALITY_PROFILES
from clasificador_video.probe import probe_clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.thumbnails import extract_thumbnail
from clasificador_video.ui.filmstrip import ClipThumbnail, Filmstrip
from clasificador_video.ui.video_widget import VideoWidget

LEGEND_TEXT = (
    "1-9 cuartos  |  Espacio play/pause  |  I/O in/out  |  P/X/U pick/reject/ninguno  "
    "|  ← → clip anterior/siguiente  |  Ctrl+Z deshacer"
)

SUBROOM_CANDIDATES = ["Baño", "Closet", "Terraza"]


def _es_room_numerado(room: str) -> bool:
    partes = room.split()
    return bool(partes) and partes[-1].isdigit()


class _ThumbnailJob(QRunnable):
    """Extrae la miniatura de un clip fuera del hilo de la UI."""

    class Signals(QWidget):
        done = Signal(int, object)  # indice, Path del jpg

    def __init__(self, index: int, video: Path, outdir: Path):
        super().__init__()
        self.index = index
        self.video = video
        self.outdir = outdir
        self.signals = _ThumbnailJob.Signals()

    def run(self) -> None:
        try:
            frame = extract_thumbnail(self.video, 0.5, self.outdir)
        except Exception:
            frame = None
        self.signals.done.emit(self.index, frame)


class MainWindow(QWidget):
    """Ventana unica (app-externa §3, opcion B): reproductor al centro,
    columna de cuartos a un lado, filmstrip abajo. Esta clase es la
    integracion -- toda la logica real vive en los modulos de las
    Milestones 1-4, wireados aqui.
    """

    def __init__(
        self,
        project_name: str,
        room_selection: RoomSelection,
        category_tree: CategoryTree,
        video_factory: Callable[..., object] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(project_name)
        self.project_name = project_name
        self.room_selection = room_selection
        self.category_tree = category_tree
        self.clips: list[Clip] = []
        self.current_index = 0
        self._router = KeyboardRouter(active_rooms=room_selection.active_rooms())
        self._probe_clip = probe_clip          # inyectable para tests
        self._thread_pool = QThreadPool(self)
        self._thumb_dir: Path | None = None

        self.room_list_widget = QListWidget()
        self.room_list_widget.addItems(room_selection.active_rooms())

        self.ingest_tree = IngestTree()
        self.import_button = QPushButton("Importar carpetas…")
        self.import_button.clicked.connect(self._on_import_folders)
        self.ingest_list = QListWidget()

        self.filmstrip = Filmstrip()

        self.video_widget = VideoWidget(mpv_factory=video_factory) if video_factory else VideoWidget()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(list(QUALITY_PROFILES))
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        self.legend_label = QLabel(LEGEND_TEXT)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Calidad:"))
        top_bar.addWidget(self.quality_combo)
        top_bar.addStretch(1)

        column = QVBoxLayout()
        column.addWidget(QLabel("Cuartos"))
        column.addWidget(self.room_list_widget, stretch=1)
        column.addWidget(self.import_button)
        column.addWidget(self.ingest_list, stretch=1)

        center = QHBoxLayout()
        center.addLayout(column, stretch=0)
        center.addWidget(self.video_widget, stretch=1)

        root = QVBoxLayout(self)
        root.addLayout(top_bar)
        root.addLayout(center, stretch=1)
        root.addWidget(self.filmstrip, stretch=0)
        root.addWidget(self.legend_label, stretch=0)

        self._install_shortcuts()

    def _install_shortcuts(self) -> None:
        shortcuts: list[tuple[str, Callable[[], None]]] = [
            ("Space", self.video_widget.toggle_play),
            ("Left", lambda: self.handle_arrow("prev")),
            ("Right", lambda: self.handle_arrow("next")),
            ("I", lambda: self.handle_key_press("i")),
            ("O", lambda: self.handle_key_press("o")),
            ("P", lambda: self.handle_key_press("p")),
            ("X", lambda: self.handle_key_press("x")),
            ("U", lambda: self.handle_key_press("u")),
        ]
        for digit in "123456789":
            shortcuts.append((digit, lambda d=digit: self.handle_key_press(d)))
        self._shortcuts = [
            QShortcut(QKeySequence(sequence), self, activated=handler)
            for sequence, handler in shortcuts
        ]

    @property
    def current_clip(self) -> Clip | None:
        if not self.clips:
            return None
        return self.clips[self.current_index]

    def load_clips(self, clips: list[Clip]) -> None:
        self.clips = clips
        self.current_index = 0
        self._refresh_filmstrip()
        if clips:
            try:
                self.video_widget.open_clip(clips[0].ruta)
            except RuntimeError:
                pass  # la ventana aun no se muestra; el clip se abrira en la navegacion

    def _load_clips_from_ingest(self) -> None:
        clips: list[Clip] = []
        orden = 1
        for folder in self.ingest_tree.top_level_folders():
            for video in folder.files:
                info = self._probe_clip(video)
                clips.append(Clip(orden=orden, ruta=video, categoria_path=[], fps=info["fps"]))
                orden += 1
        self.load_clips(clips)
        self._schedule_thumbnails()

    def _schedule_thumbnails(self) -> None:
        if not self.clips:
            return
        import tempfile

        self._thumb_dir = Path(tempfile.mkdtemp(prefix="clasificador-thumbs-"))
        for index, clip in enumerate(self.clips):
            job = _ThumbnailJob(index, clip.ruta, self._thumb_dir / str(index))
            job.signals.done.connect(self._on_thumbnail_ready)
            self._thread_pool.start(job)

    def _on_thumbnail_ready(self, index: int, frame: Path | None) -> None:
        if frame is None or index >= self.filmstrip.count():
            return
        self.filmstrip.item_widgets[index].set_pixmap(QPixmap(str(frame)))

    def handle_key_press(self, key: str) -> None:
        if self.current_clip is None:
            return
        if self._router.pending_parent is not None:
            self._handle_subroom_key(key)
            return
        if key == "i":
            self.current_clip.in_frame = self.video_widget.player.mark_in(self.current_clip.fps)
            self._refresh_filmstrip()
            return
        if key == "o":
            self.current_clip.out_frame = self.video_widget.player.mark_out(self.current_clip.fps)
            self._refresh_filmstrip()
            return
        if key == "u":
            self.current_clip.in_frame = None
            self.current_clip.out_frame = None
            self._refresh_filmstrip()
            return
        if key.isdigit() and self._router.pending_parent is None:
            index = int(key) - 1
            if 0 <= index < len(self._router.active_rooms):
                room = self._router.active_rooms[index]
                if _es_room_numerado(room) and not self._router.subrooms.get(room):
                    self._router.pending_parent = room
                    return  # la tecla siguiente elige el subcuarto
        room_path = self._router.resolve_room_key(key)
        if room_path is not None:
            self.current_clip.categoria_path = room_path
            self._refresh_filmstrip()
            return
        if key.isdigit():
            index = int(key) - 1
            if 0 <= index < len(self._router.active_rooms):
                room = self._router.active_rooms[index]
                if _es_room_numerado(room) and not self._router.subrooms.get(room):
                    self._router.pending_parent = room
                    self._handle_subroom_key(key)
                    return
        action = self._router.resolve_action_key(key)
        if action is not None:
            self.current_clip.flag = action
            self._refresh_filmstrip()

    def _handle_subroom_key(self, key: str) -> None:
        sub_path = self._router.resolve_subroom_key(key)
        if sub_path is not None:
            self.current_clip.categoria_path = sub_path
            self._refresh_filmstrip()
            return
        if key.isdigit():
            index = int(key) - 1
            if 0 <= index < len(SUBROOM_CANDIDATES):
                self.attach_subroom_or_resolve(SUBROOM_CANDIDATES[index])
                return
        self._router.pending_parent = None  # la tecla no era de subcuarto: salir del modo

    def handle_arrow(self, direction: str) -> None:
        if not self.clips:
            return
        if direction == "next":
            self.current_index = min(self.current_index + 1, len(self.clips) - 1)
        else:
            self.current_index = max(self.current_index - 1, 0)
        clip = self.current_clip
        if clip is not None:
            try:
                self.video_widget.open_clip(clip.ruta)
            except RuntimeError:
                pass
        self._refresh_filmstrip()

    def attach_subroom_or_resolve(self, subroom: str) -> list[str] | None:
        """Resuelve el path completo del subcuarto y lo asigna al clip
        actual.

        Si el subcuarto ya cuelga de alguno de los cuartos activos, se usa
        ese. Si no, se le pregunta al usuario una sola vez a que cuarto
        colgarlo (spec app-externa §5).
        """
        if self.current_clip is None:
            return None
        for parent in self.room_selection.active_rooms():
            if subroom in self.category_tree.known_subrooms_for(parent):
                path = self.category_tree.path_for(parent, subroom=subroom)
                self.current_clip.categoria_path = path
                self._refresh_filmstrip()
                return path
        parent = self._ask_parent_room(subroom)
        if parent is None:
            return None
        self.category_tree.attach_subroom(parent, subroom)
        self._router.subrooms[parent] = self.category_tree.known_subrooms_for(parent)
        path = self.category_tree.path_for(parent, subroom=subroom)
        self.current_clip.categoria_path = path
        self._refresh_filmstrip()
        return path

    def _ask_parent_room(self, subroom: str) -> str | None:
        from PySide6.QtWidgets import QInputDialog

        rooms = self.room_selection.active_rooms()
        if not rooms:
            return None
        parent, ok = QInputDialog.getItem(
            self, "Subcuarto", f"¿A qué cuarto cuelga '{subroom}'?", rooms, 0, False
        )
        return parent if ok else None

    def _on_quality_changed(self, profile_name: str) -> None:
        try:
            self.video_widget.player.set_quality(profile_name)
        except RuntimeError:
            pass  # el player aun no se creo (widget no mostrado); se aplica al abrir

    def _on_import_folders(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta de material")
        if not folder:
            return
        self.ingest_tree.import_folder(Path(folder))
        self._refresh_ingest_list()

    def _refresh_ingest_list(self) -> None:
        self.ingest_list.clear()
        for f in self.ingest_tree.top_level_folders():
            self.ingest_list.addItem(f.display_name)

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
