# src/clasificador_video/ui/main_window.py
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.autosave import save_session
from clasificador_video.category_path import CategoryTree
from clasificador_video.ingest import IngestTree
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip, Manifest
from clasificador_video.player import QUALITY_PROFILES
from clasificador_video.probe import probe_clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.thumbnails import extract_thumbnail
from clasificador_video.ui import theme
from clasificador_video.ui.filmstrip import ClipThumbnail, Filmstrip
from clasificador_video.ui.video_widget import VideoWidget

SUBROOM_CANDIDATES = ["Baño", "Closet", "Terraza"]


def _build_legend_text(active_rooms: list[str]) -> str:
    """Leyenda de teclado con el cuarto real que le toca a cada numero de
    la sesion activa -- bug real de v1: mostraba '1-9 cuartos' generico
    sin decir a que cuarto corresponde cada tecla.
    """
    room_keys = "  ".join(f"{i} {room}" for i, room in enumerate(active_rooms[:9], start=1))
    return (
        f"{room_keys}  |  Espacio play/pause  |  I/O in/out  |  P/X/U pick/reject/ninguno  "
        "|  ← → clip anterior/siguiente  |  Ctrl+Z deshacer"
    )


def _es_room_numerado(room: str) -> bool:
    partes = room.split()
    return bool(partes) and partes[-1].isdigit()


def _build_room_row_widget(key_number: int, room: str, count: int, max_count: int, color: str) -> QWidget:
    """Fila de la lista de cuartos: tecla + nombre + conteo + barra
    proporcional al cuarto con mas clips -- de un vistazo se ve que
    cuarto esta "lleno" y cual falta cubrir todavia."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(2)
    top = QHBoxLayout()
    keycap = QLabel(str(key_number)) if key_number else QLabel("")
    keycap.setObjectName("roomKeycap")
    keycap.setFixedWidth(16)
    keycap.setAlignment(Qt.AlignCenter)
    dot = QLabel("●")
    dot.setStyleSheet(f"color: {color}; font-size: 9px;")
    name_label = QLabel(f"{room} ({count})")
    top.addWidget(keycap)
    top.addWidget(dot)
    top.addWidget(name_label, stretch=1)
    layout.addLayout(top)
    bar = QProgressBar()
    bar.setObjectName("roomCountBar")
    bar.setRange(0, max(max_count, 1))
    bar.setValue(count)
    bar.setTextVisible(False)
    bar.setFixedHeight(3)
    layout.addWidget(bar)
    widget.setFixedHeight(36)
    return widget


class _ThumbnailJob(QRunnable):
    """Extrae la miniatura de un clip fuera del hilo de la UI."""

    class Signals(QWidget):
        done = Signal(int, int, object)  # generation, indice, Path del jpg

    def __init__(self, generation: int, index: int, video: Path, outdir: Path):
        super().__init__()
        self._generation = generation
        self.index = index
        self.video = video
        self.outdir = outdir
        self.signals = _ThumbnailJob.Signals()

    def run(self) -> None:
        try:
            frame = extract_thumbnail(self.video, 0.5, self.outdir)
        except Exception:
            frame = None
        try:
            self.signals.done.emit(self._generation, self.index, frame)
        except RuntimeError:
            # la ventana dueña (y su Signals) ya se destruyo mientras este
            # job corria en su propio hilo -- no hay nadie escuchando.
            pass


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
        self.selected_indices: list[int] = []
        self._router = KeyboardRouter(active_rooms=room_selection.active_rooms())
        self._probe_clip = probe_clip          # inyectable para tests
        self._thread_pool = QThreadPool(self)
        # una sola miniatura a la vez: varios decodificadores videotoolbox en
        # paralelo saturan VideoToolbox y bloquean al reproductor embebido
        self._thread_pool.setMaxThreadCount(1)
        self._thumb_dir: Path | None = None
        self._thumb_generation = 0
        self.session_path: Path | None = None
        self._last_saved_at: float | None = None

        self.room_list_widget = QListWidget()
        self.room_list_widget.addItems(room_selection.active_rooms())

        self.ingest_tree = IngestTree()
        self.import_button = QPushButton("Importar carpetas…")
        self.import_button.setObjectName("importButton")
        self.import_button.clicked.connect(self._on_import_folders)
        self.ingest_title_label = QLabel("Material importado")
        self.ingest_title_label.setObjectName("panelTitle")
        self.ingest_list = QListWidget()

        self.filmstrip = Filmstrip()
        self.filmstrip.setObjectName("filmstripPanel")
        self.filmstrip.clip_clicked.connect(self.select_clip)
        self.filmstrip.selection_changed.connect(self._on_selection_changed)

        self.video_widget = VideoWidget(mpv_factory=video_factory) if video_factory else VideoWidget()
        self.video_widget.setObjectName("videoWidget")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(list(QUALITY_PROFILES))
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        self.legend_label = QLabel(_build_legend_text(room_selection.active_rooms()))
        self.legend_label.setObjectName("legendLabel")
        self.export_button = QPushButton("Exportar manifest…")
        self.export_button.setObjectName("exportButton")
        self.export_button.clicked.connect(self._on_export_manifest)
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")

        # posicion "clip N/total" + resumen pick/reject/pendiente -- datos
        # que ya se calculan de siempre, solo que antes no se mostraban
        self.position_label = QLabel("")
        self.position_label.setObjectName("positionLabel")
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("legendLabel")
        self.unclassified_badge = QLabel("")
        self.unclassified_badge.setObjectName("unclassifiedBadge")
        self.saved_indicator = QLabel("")
        self.saved_indicator.setObjectName("savedIndicator")
        self._saved_timer = QTimer(self)
        self._saved_timer.setInterval(1000)
        self._saved_timer.timeout.connect(self._tick_saved_indicator)
        self._saved_timer.start()

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Calidad:"))
        top_bar.addWidget(self.quality_combo)
        top_bar.addWidget(self.position_label)
        top_bar.addWidget(self.progress_label)
        top_bar.addStretch(1)
        top_bar.addWidget(self.unclassified_badge)
        top_bar.addWidget(self.saved_indicator)
        top_bar.addWidget(self.status_label)
        top_bar.addWidget(self.export_button)

        column = QVBoxLayout()
        self.room_title_label = QLabel("Cuartos")
        self.room_title_label.setObjectName("panelTitle")
        column.addWidget(self.room_title_label)
        column.addWidget(self.room_list_widget, stretch=1)
        column.addWidget(self.import_button)
        column.addWidget(self.ingest_title_label)
        column.addWidget(self.ingest_list, stretch=1)

        room_column_widget = QWidget()
        room_column_widget.setObjectName("roomColumn")
        room_column_widget.setLayout(column)

        # banner de modo subcuarto: solo visible mientras el router esta
        # esperando la tecla de subcuarto (_router.pending_parent) -- antes
        # ese estado era invisible para el editor
        self.subroom_banner = QLabel("")
        self.subroom_banner.setObjectName("subroomBanner")
        self.subroom_banner.hide()

        video_column = QVBoxLayout()
        video_column.addWidget(self.subroom_banner)
        video_column.addWidget(self.video_widget, stretch=1)

        # inspector de metadata del clip actual: antes solo se leia
        # (parcialmente) en el filmstrip, ahora vive junto al video
        self.inspector_panel = QWidget()
        self.inspector_panel.setObjectName("inspectorPanel")
        self.inspector_panel.setFixedWidth(200)
        inspector_layout = QVBoxLayout(self.inspector_panel)
        self.inspector_file_label = QLabel("")
        self.inspector_file_label.setObjectName("clipRoomLabel")
        self.inspector_room_label = QLabel("")
        self.inspector_room_label.setObjectName("inspectorRoomLabel")
        self.inspector_state_label = QLabel("")
        self.inspector_state_label.setObjectName("clipRoomLabel")
        inspector_layout.addWidget(self.inspector_file_label)
        inspector_layout.addWidget(self.inspector_room_label)
        inspector_layout.addWidget(self.inspector_state_label)
        inspector_layout.addStretch(1)

        center = QHBoxLayout()
        center.addWidget(room_column_widget, stretch=0)
        center.addLayout(video_column, stretch=1)
        center.addWidget(self.inspector_panel, stretch=0)

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

    def closeEvent(self, event) -> None:
        # esperar a que terminen los jobs de miniaturas antes de destruir la UI
        self._thread_pool.waitForDone(5000)
        self._cleanup_thumb_dir()
        super().closeEvent(event)

    def _cleanup_thumb_dir(self) -> None:
        if self._thumb_dir is not None and self._thumb_dir.exists():
            shutil.rmtree(self._thumb_dir, ignore_errors=True)

    @property
    def current_clip(self) -> Clip | None:
        if not self.clips:
            return None
        return self.clips[self.current_index]

    def _on_selection_changed(self, indices: list[int]) -> None:
        self.selected_indices = list(indices)

    def _bulk_targets(self) -> list[Clip]:
        """Clips a los que aplicar una asignacion de cuarto: si hay mas de
        un clip seleccionado en el filmstrip (Shift/Ctrl+click), todos
        ellos; si no, solo el clip actual (comportamiento de siempre)."""
        if len(self.selected_indices) > 1:
            return [self.clips[i] for i in self.selected_indices if 0 <= i < len(self.clips)]
        if self.current_clip is not None:
            return [self.current_clip]
        return []

    def _apply_categoria_to_targets(self, path: list[str]) -> None:
        for clip in self._bulk_targets():
            clip.categoria_path = list(path)

    def _update_toolbar_stats(self) -> None:
        total = len(self.clips)
        position = self.current_index + 1 if self.clips else 0
        self.position_label.setText(f"Clip {position:02d} / {total}")
        picks = sum(1 for c in self.clips if c.flag == "pick")
        rejects = sum(1 for c in self.clips if c.flag == "reject")
        pending = total - picks - rejects
        self.progress_label.setText(f"{picks} pick · {rejects} reject · {pending} pend.")
        unclassified = sum(1 for c in self.clips if not c.categoria_path)
        self.unclassified_badge.setText(f"{unclassified} sin clasificar" if unclassified else "")

    def _update_inspector(self) -> None:
        clip = self.current_clip
        if clip is None:
            self.inspector_file_label.setText("")
            self.inspector_room_label.setText("")
            self.inspector_state_label.setText("")
            return
        self.inspector_file_label.setText(Path(clip.ruta).name)
        self.inspector_room_label.setText(
            " › ".join(clip.categoria_path) if clip.categoria_path else "Sin clasificar"
        )
        estado = {"pick": "✓ Pick", "reject": "✕ Reject"}.get(clip.flag, "—")
        self.inspector_state_label.setText(estado)

    def _update_subroom_banner(self) -> None:
        parent = self._router.pending_parent
        if parent is None:
            self.subroom_banner.hide()
            return
        options = "   ".join(f"{i} {name}" for i, name in enumerate(SUBROOM_CANDIDATES, start=1))
        self.subroom_banner.setText(f"Elegí subcuarto: {options}")
        self.subroom_banner.show()

    def _tick_saved_indicator(self) -> None:
        if self._last_saved_at is None:
            return
        elapsed = int(time.monotonic() - self._last_saved_at)
        self.saved_indicator.setText(f"Guardado hace {elapsed}s")

    def load_clips(self, clips: list[Clip]) -> None:
        self.clips = clips
        self.current_index = 0
        self._refresh_filmstrip()
        if clips:
            self.video_widget.open_clip(clips[0].ruta)
        self._autosave()

    def _autosave(self) -> None:
        if self.session_path is None:
            return
        try:
            tree = {}
            for parent in self.room_selection.active_rooms():
                known = self.category_tree.known_subrooms_for(parent)
                if known:
                    tree[parent] = known
            data = {
                "proyecto": self.project_name,
                "rooms": self.room_selection.active_rooms(),
                "category_tree": tree,
                "clips": [c.to_dict() for c in self.clips],
            }
            save_session(self.session_path, data)
            self._last_saved_at = time.monotonic()
            self._tick_saved_indicator()
        except OSError:
            pass

    def _load_clips_from_ingest(self) -> None:
        clips: list[Clip] = []
        orden = 1
        for folder in self.ingest_tree.top_level_folders():
            for video in folder.files:
                try:
                    info = self._probe_clip(video)
                except Exception:
                    continue
                clips.append(Clip(orden=orden, ruta=video, categoria_path=[], fps=info["fps"]))
                orden += 1
        self.load_clips(clips)
        self._schedule_thumbnails()

    def _schedule_thumbnails(self) -> None:
        if not self.clips:
            return
        import tempfile

        # una importacion nueva invalida los jobs viejos: limpia el dir
        # temporal anterior y avanza la generacion para que las senales
        # stale de la importacion anterior no escriban sobre el filmstrip nuevo
        self._cleanup_thumb_dir()
        self._thumb_dir = Path(tempfile.mkdtemp(prefix="clasificador-thumbs-"))
        self._thumb_generation += 1
        generation = self._thumb_generation
        for index, clip in enumerate(self.clips):
            job = _ThumbnailJob(generation, index, clip.ruta, self._thumb_dir / str(index))
            job.signals.done.connect(self._on_thumbnail_ready)
            self._thread_pool.start(job)

    def _on_thumbnail_ready(self, generation: int, index: int, frame: Path | None) -> None:
        if generation != self._thumb_generation:
            return  # senal de una importacion ya descartada
        if frame is None or index >= self.filmstrip.count():
            return
        self.filmstrip.item_widgets[index].set_pixmap(QPixmap(str(frame)))

    def handle_key_press(self, key: str) -> None:
        if self.current_clip is None:
            return
        if self._router.pending_parent is not None:
            self._handle_subroom_key(key)
            self._autosave()
            return
        if key == "i":
            self.current_clip.in_frame = self.video_widget.player.mark_in(self.current_clip.fps)
            self._refresh_filmstrip()
            self._autosave()
            return
        if key == "o":
            self.current_clip.out_frame = self.video_widget.player.mark_out(self.current_clip.fps)
            self._refresh_filmstrip()
            self._autosave()
            return
        if key == "u":
            self.current_clip.in_frame = None
            self.current_clip.out_frame = None
            self._refresh_filmstrip()
            self._autosave()
            return
        if key.isdigit() and self._router.pending_parent is None:
            index = int(key) - 1
            if 0 <= index < len(self._router.active_rooms):
                room = self._router.active_rooms[index]
                if _es_room_numerado(room) and not self._router.subrooms.get(room):
                    self._router.pending_parent = room
                    self._update_subroom_banner()
                    return  # la tecla siguiente elige el subcuarto
        room_path = self._router.resolve_room_key(key)
        if room_path is not None:
            self._apply_categoria_to_targets(room_path)
            self._refresh_filmstrip()
            self._autosave()
            return
        action = self._router.resolve_action_key(key)
        if action is not None:
            self.current_clip.flag = action
            self._refresh_filmstrip()
            self._autosave()

    def _handle_subroom_key(self, key: str) -> None:
        sub_path = self._router.resolve_subroom_key(key)
        if sub_path is not None:
            self._apply_categoria_to_targets(sub_path)
            self._refresh_filmstrip()
            self._autosave()
            self._update_subroom_banner()
            return
        if key.isdigit():
            index = int(key) - 1
            if 0 <= index < len(SUBROOM_CANDIDATES):
                self.attach_subroom_or_resolve(SUBROOM_CANDIDATES[index])
                self._update_subroom_banner()
                return
        self._router.pending_parent = None  # la tecla no era de subcuarto: salir del modo
        self._update_subroom_banner()

    def handle_arrow(self, direction: str) -> None:
        if not self.clips:
            return
        if direction == "next":
            self.current_index = min(self.current_index + 1, len(self.clips) - 1)
        else:
            self.current_index = max(self.current_index - 1, 0)
        clip = self.current_clip
        if clip is not None:
            self.video_widget.open_clip(clip.ruta)
        self._refresh_filmstrip()
        self._update_inspector()
        self._autosave()

    def select_clip(self, index: int) -> None:
        if not (0 <= index < len(self.clips)):
            return
        self.current_index = index
        clip = self.current_clip
        if clip is not None:
            self.video_widget.open_clip(clip.ruta)
        # No reconstruir el filmstrip aqui (no llamar a _refresh_filmstrip):
        # la seleccion solo cambia el clip actual (borde azul), no los datos
        # de ningun clip, asi que basta con set_current. Reconstruir llamaba
        # a Filmstrip.set_clips, que destruye (setParent None) y reemplaza a
        # TODOS los _ClipItemWidget --incluyendo el propio widget que esta
        # dentro de su propio mousePressEvent (el click que origino esta
        # llamada). Qt aun lo referencia internamente en sendMouseEvent al
        # volver del despacho anidado, y en el run loop nativo de cocoa eso
        # termina en SIGSEGV (KERN_INVALID_ADDRESS 0xc). Reconstruir ademas
        # borraba todos los pixmaps ya cargados por los _ThumbnailJob.
        self.filmstrip.set_current(self.current_index)
        self._update_toolbar_stats()
        self._update_inspector()
        self._autosave()

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
                self._apply_categoria_to_targets(path)
                self._refresh_filmstrip()
                return path
        parent = self._ask_parent_room(subroom)
        if parent is None:
            return None
        self.category_tree.attach_subroom(parent, subroom)
        self._router.subrooms[parent] = self.category_tree.known_subrooms_for(parent)
        path = self.category_tree.path_for(parent, subroom=subroom)
        self._apply_categoria_to_targets(path)
        self._refresh_filmstrip()
        self._autosave()
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
        self.video_widget.player.set_quality(profile_name)

    def _on_export_manifest(self) -> None:
        unclassified = [c for c in self.clips if not c.categoria_path]
        if unclassified:
            QMessageBox.warning(
                self, "Clips sin clasificar",
                f"{len(unclassified)} clip(s) no tienen cuarto y entrarán en 'Sin clasificar'. "
                "Puedes seguir y corregir después.",
            )
        path, _ = QFileDialog.getSaveFileName(self, "Guardar manifest", "manifest.json", "JSON (*.json)")
        if not path:
            return
        manifest = Manifest(
            proyecto=self.project_name,
            orientacion="horizontal",  # TODO fase 3: detectar del material predominante
            clips=self.clips,
        )
        manifest.write_json(Path(path))
        self.status_label.setText(f"Manifest exportado: {path}")

    def _on_import_folders(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta de material")
        if not folder:
            return
        self.ingest_tree.import_folder(Path(folder))
        self._refresh_ingest_list()
        self._load_clips_from_ingest()

    def _refresh_ingest_list(self) -> None:
        self.ingest_list.clear()
        for f in self.ingest_tree.top_level_folders():
            self.ingest_list.addItem(f.display_name)

    def _refresh_filmstrip(self) -> None:
        active_rooms = self.room_selection.active_rooms()
        self.filmstrip.set_clips([
            ClipThumbnail(
                path=clip.ruta,
                thumbnail_path=None,
                room_label=clip.categoria_path[-1] if clip.categoria_path else "Sin clasificar",
                flag=clip.flag,
                room_color=(
                    theme.room_color(active_rooms.index(clip.categoria_path[0]))
                    if clip.categoria_path and clip.categoria_path[0] in active_rooms
                    else None
                ),
            )
            for clip in self.clips
        ])
        self.filmstrip.set_current(self.current_index)
        self._refresh_room_counts()
        self._update_toolbar_stats()
        self._update_inspector()

    def _refresh_room_counts(self) -> None:
        from collections import Counter

        counts: Counter[str] = Counter()
        for clip in self.clips:
            if clip.categoria_path:
                counts[clip.categoria_path[0]] += 1
        active_rooms = self.room_selection.active_rooms()
        max_count = max(counts.values(), default=0)
        self.room_list_widget.clear()
        for index, room in enumerate(active_rooms):
            item = QListWidgetItem(f"{room} ({counts[room]})")
            self.room_list_widget.addItem(item)
            key_number = index + 1 if index < 9 else 0
            row_widget = _build_room_row_widget(
                key_number, room, counts[room], max_count, theme.room_color(index)
            )
            item.setSizeHint(row_widget.sizeHint())
            self.room_list_widget.setItemWidget(item, row_widget)
