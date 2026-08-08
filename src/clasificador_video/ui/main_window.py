# src/clasificador_video/ui/main_window.py
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.autosave import save_session
from clasificador_video.filters import FilterState, cola, contar
from clasificador_video.history import History, HistoryEntry
from clasificador_video.ingest import IngestTree
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip, Manifest
from clasificador_video.probe import probe_clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.thumbnails import (
    cache_dir_for,
    default_cache_root,
    extract_thumbnail,
    extract_thumbnail_strip,
)
from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import ClipSheet, ClipThumbnail
from clasificador_video.ui.room_rail import RoomRail
from clasificador_video.ui.status_bar import StatusBar
from clasificador_video.ui.title_bar import TitleBar
from clasificador_video.ui.tool_column import ToolColumn
from clasificador_video.ui.video_stage import VideoStage
from clasificador_video.ui.video_widget import format_timecode

def _copiar(valor):
    """Copia los valores mutables que guarda el historial.

    `categoria_path` es una lista: guardar la referencia haria que el
    "antes" mutara junto con el clip y deshacer no hiciera nada.
    """
    return list(valor) if isinstance(valor, list) else valor


class _AutosaveWriteJob(QRunnable):
    """Escribe la sesion a disco fuera del hilo de la UI -- antes
    `_autosave` escribia sincronicamente en cada tecla, lo que con muchas
    sesiones/clips se sentia como lag real al clasificar rapido."""

    def __init__(self, path: Path, data: dict):
        super().__init__()
        self.path = path
        self.data = data

    def run(self) -> None:
        try:
            save_session(self.path, self.data)
        except OSError:
            pass


class _ThumbnailJob(QRunnable):
    """Extrae la miniatura (o la tira de frames para el scrub) de un clip
    fuera del hilo de la UI."""

    STRIP_COUNT = 12

    class Signals(QWidget):
        done = Signal(int, int, object)  # generation, indice, list[Path] | None

    def __init__(self, generation: int, index: int, video: Path, outdir: Path, duration_seconds: float | None):
        super().__init__()
        self._generation = generation
        self.index = index
        self.video = video
        self.outdir = outdir
        self.duration_seconds = duration_seconds
        self.signals = _ThumbnailJob.Signals()

    def run(self) -> None:
        try:
            if self.duration_seconds:
                # tira de frames espaciados a lo largo del clip, un solo
                # proceso de mpv con varios seek+captura por IPC -- medido
                # en vivo el 2026-08-06 con clips reales de la FX30:
                # ~1.8s para 12 frames (ver thumbnails.extract_thumbnail_strip)
                frames = extract_thumbnail_strip(
                    self.video, self.duration_seconds, self.STRIP_COUNT, self.outdir
                )
            else:
                # sin duracion conocida (ej. sesion restaurada sin volver
                # a correr ffprobe): un solo frame, como antes.
                frames = [extract_thumbnail(self.video, 0.5, self.outdir)]
        except Exception:
            frames = None
        try:
            self.signals.done.emit(self._generation, self.index, frames or None)
        except RuntimeError:
            # la ventana dueña (y su Signals) ya se destruyo mientras este
            # job corria en su propio hilo -- no hay nadie escuchando.
            pass


class MainWindow(QWidget):
    """Ventana del clasificador, con la estructura del mockup.

    TRES filas y ninguna mas: barra de titulo, cuerpo y barra de estado.
    Cualquier cuarta fila es una banda horizontal, y en un clip 9:16 cada
    16 px de banda cuestan 9 px de ancho de video. Todo lo demas vive en
    columnas o flotando sobre el video (ver VideoStage).

    El ancho del video lo dicta la relacion de aspecto del clip y los
    paneles absorben el resto: asi no queda ni una franja negra.
    """

    def __init__(
        self,
        project_name: str,
        room_selection: RoomSelection,
        video_factory: Callable[..., object] | None = None,
        parent=None,
        thumbnail_cache_root: Path | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(project_name)
        self.project_name = project_name
        self.room_selection = room_selection
        self.clips: list[Clip] = []
        self.current_index = 0
        self.selected_indices: list[int] = []
        self.history = History()
        self.filters = FilterState()
        self._router = KeyboardRouter(active_rooms=room_selection.active_rooms())
        self._probe_clip = probe_clip          # inyectable para tests
        self._thumbnail_cache_root = thumbnail_cache_root or default_cache_root()
        self._thread_pool = QThreadPool(self)
        # las miniaturas se extraen en software (--hwdec=no, ver
        # thumbnails.py) -- no tocan VideoToolbox, asi que un par en
        # paralelo no compite con el reproductor embebido.
        self._thread_pool.setMaxThreadCount(3)
        self._thumb_generation = 0
        self.session_path: Path | None = None
        self._last_saved_at: float | None = None
        self._clip_durations: dict[int, float] = {}  # indice -> segundos; solo en memoria
        # indice -> (ancho, alto) ya corregidos por rotacion en probe.py.
        # Solo en memoria, igual que las duraciones: meterlo en Clip cambiaria
        # to_dict() y con eso el contrato del manifest con el plugin de Premiere.
        self._clip_sizes: dict[int, tuple[int, int]] = {}
        self._clip_rotations: dict[int, int] = {}

        # autosave con debounce: coalesca ediciones rapidas seguidas en un
        # solo guardado en vez de escribir a disco en cada tecla.
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(400)
        self._autosave_timer.timeout.connect(self._write_autosave_now)
        self._autosave_pool = QThreadPool(self)
        self._autosave_pool.setMaxThreadCount(1)

        self.ingest_tree = IngestTree()

        # ---------------- las tres filas ----------------
        self.title_bar = TitleBar()
        self.title_bar.set_project(project_name, 0)
        self.title_bar.export_requested.connect(self._on_export_manifest)

        self.room_rail = RoomRail()
        self.room_rail.import_requested.connect(self._on_import_folders)
        self.room_rail.room_created.connect(self._on_room_created)
        self.room_rail.room_renamed.connect(self._on_room_renamed)
        self.room_rail.room_moved.connect(self._on_room_moved)
        self.room_rail.room_removed.connect(self._on_room_removed)
        self.room_rail.revert_requested.connect(self.revert)
        # el boton «Cuartos ⌘R» estuvo muerto desde la F2: emitia una señal
        # que nadie escuchaba. Ahora lleva el foco al rail, para renombrar,
        # reordenar y crear cuartos sin tocar el mouse.
        self.title_bar.rooms_requested.connect(self.room_rail.focus_rooms)

        self.video_stage = VideoStage(mpv_factory=video_factory)
        self.video_stage.quality.selected.connect(self._on_quality_changed)
        self.scrub_bar = self.video_stage.scrub_bar
        self.scrub_bar.seek_started.connect(self._on_scrub_seek_started)
        self.scrub_bar.seek_requested.connect(self._on_scrub_seek)

        self.tool_column = ToolColumn()
        self.tool_column.undo_requested.connect(self.undo)

        self.clip_sheet = ClipSheet()
        self.clip_sheet.clip_clicked.connect(self.select_clip)
        self.clip_sheet.selection_changed.connect(self._on_selection_changed)
        self.clip_sheet.filters_changed.connect(self.set_filters)

        self.status_bar = StatusBar()
        self.status_bar.unclassified_clicked.connect(self._filtrar_sin_clasificar)

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(0)
        cuerpo.addWidget(self.room_rail)
        cuerpo.addWidget(self.video_stage)
        cuerpo.addWidget(self.tool_column)
        cuerpo.addWidget(self.clip_sheet, stretch=1)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self.title_bar)
        raiz.addLayout(cuerpo)
        raiz.addWidget(self.status_bar)

        self._playhead_timer = QTimer(self)
        self._playhead_timer.setInterval(150)
        self._playhead_timer.timeout.connect(self._tick_playhead)
        self._playhead_timer.start()
        self._saved_timer = QTimer(self)
        self._saved_timer.setInterval(1000)
        self._saved_timer.timeout.connect(self._tick_saved_indicator)
        self._saved_timer.start()

        self._install_shortcuts()
        self._refresh_rail()

    # ------------------------------------------------------------------
    # video dimensionado por aspecto
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        super().resizeEvent(event)
        self._resize_video_stage()

    def _resize_video_stage(self) -> None:
        """El alto del cuerpo se CALCULA, no se lee de los hijos: durante
        `resizeEvent` los hijos todavia tienen el tamaño anterior."""
        alto_cuerpo = self.height() - theme.TITLEBAR_HEIGHT - theme.STATUSBAR_HEIGHT
        ancho = VideoStage.width_for(alto_cuerpo, self.aspect_ratio_for(self.current_index))
        maximo = (
            self.width() - theme.RAIL_WIDTH - theme.TOOLCOL_WIDTH - theme.SHEET_MIN_WIDTH
        )
        self.video_stage.setFixedWidth(max(1, min(ancho, maximo)))

    def aspect_ratio_for(self, index: int) -> float:
        """Relacion de aspecto real del clip. 16/9 cuando no se conoce --
        pasa con sesiones restauradas de disco, donde no se volvio a correr
        ffprobe (mismo comportamiento que ya tienen las duraciones).
        """
        width, height = self._clip_sizes.get(index, (0, 0))
        if width > 0 and height > 0:
            return width / height
        return 16 / 9

    # ------------------------------------------------------------------
    # teclado
    # ------------------------------------------------------------------

    def _install_shortcuts(self) -> None:
        shortcuts: list[tuple[str, Callable[[], None]]] = [
            ("Space", self.video_stage.video.toggle_play),
            ("Left", lambda: self.handle_arrow("prev")),
            ("Right", lambda: self.handle_arrow("next")),
            ("I", lambda: self.handle_key_press("i")),
            ("O", lambda: self.handle_key_press("o")),
            ("P", lambda: self.handle_key_press("p")),
            ("X", lambda: self.handle_key_press("x")),
            ("U", lambda: self.handle_key_press("u")),
            # la hoja lo anuncia en el encabezado de cada grupo: tiene que
            # existir de verdad. QKeySequence.SelectAll ya es ⌘A en macOS y
            # Ctrl+A en el resto, sin escribir el modificador a mano.
            (QKeySequence.StandardKey.SelectAll, self.select_current_group),
            # StandardKey.Undo ya es ⌘Z en macOS y Ctrl+Z en el resto
            (QKeySequence.StandardKey.Undo, self.undo),
            # la barra de titulo anuncia `⌘E` en el boton de exportar desde la
            # F2 y el atajo no existia
            ("Ctrl+E", self._on_export_manifest),
            ("Ctrl+R", self.room_rail.focus_rooms),
        ]
        for digit in "123456789":
            shortcuts.append((digit, lambda d=digit: self.handle_key_press(d)))
        self._shortcuts = [
            QShortcut(QKeySequence(sequence), self, activated=handler)
            for sequence, handler in shortcuts
        ]

    def closeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self._flush_autosave()
        self._thread_pool.waitForDone(5000)
        super().closeEvent(event)

    @property
    def current_clip(self) -> Clip | None:
        if not self.clips:
            return None
        return self.clips[self.current_index]

    @property
    def video_widget(self):
        """El `VideoWidget` real, ahora dentro del `VideoStage`."""
        return self.video_stage.video

    def _on_selection_changed(self, indices: list[int]) -> None:
        self.selected_indices = list(indices)

    def select_current_group(self) -> None:
        """`⌘A`: selecciona el grupo del clip actual, para asignarle un cuarto
        de una sola tecla. Es lo que anuncia el encabezado de cada grupo."""
        self.clip_sheet.select_current_group()

    def _bulk_target_indices(self) -> list[int]:
        """Clips a los que aplicar una asignacion de cuarto: si hay mas de
        un clip seleccionado, todos ellos; si no, solo el clip actual.

        Los que el filtro esconde NO entran: una seleccion vieja tapada por un
        filtro recibiria la asignacion sin que la veas.
        """
        if len(self.selected_indices) > 1:
            visibles = set(self.queue())
            return [
                i for i in self.selected_indices
                if 0 <= i < len(self.clips) and i in visibles
            ]
        if self.current_clip is not None:
            return [self.current_index]
        return []

    def _bulk_targets(self) -> list[Clip]:
        return [self.clips[i] for i in self._bulk_target_indices()]

    def _apply_categoria_to_targets(self, path: list[str]) -> None:
        indices = self._bulk_target_indices()
        if not indices:
            return
        cuarto = path[-1]
        self._registrar(
            etiqueta=cuarto,
            detalle=self._detalle(indices),
            color=self._color_de_cuarto(path[0]),
            clips=indices,
            campos=("categoria_path",),
        )
        for indice in indices:
            self.clips[indice].categoria_path = list(path)

    # ------------------------------------------------------------------
    # los filtros SON la cola de navegacion
    # ------------------------------------------------------------------

    def queue(self) -> list[int]:
        """Los indices que pasan el filtro, en orden.

        Una sola lista alimenta tres cosas: que se ve en la hoja, por donde
        se mueven las flechas y que dice el contador del visor. Calculadas
        por separado se desincronizan, y ahi aparecen los bugs de «la flecha
        me llevo a un clip que no estoy viendo».
        """
        return cola(self.clips, self.filters)

    def set_filters(self, estado: FilterState) -> None:
        self.filters = estado
        self._refresh_sheet()

    def _filtrar_sin_clasificar(self) -> None:
        """El aviso de la barra de estado: el boton de «sigue trabajando».

        Se usa `click()` y no `setChecked()`: `setChecked` no emite `clicked`,
        asi que la hoja no se enteraba y el chip no se marcaba como el que
        define la cola.
        """
        self.clip_sheet.chips["sin_clasificar"].click()

    def _avanzar_en_la_cola(self) -> None:
        """`1`-`9` es «asignar cuarto y avanzar» (DECISIONES.md).

        Avanza solo cuando se actuo sobre UN clip: con seis seleccionados,
        avanzar es un salto sin sentido.
        """
        if len(self.selected_indices) <= 1:
            self.handle_arrow("next")

    # ------------------------------------------------------------------
    # historial: registrar antes de mutar, deshacer despues
    # ------------------------------------------------------------------

    def _detalle(self, indices: list[int]) -> str:
        """`→ clip 093` o `→ 6 clips`, como las filas del mockup."""
        if len(indices) == 1:
            return f"→ clip {self.clips[indices[0]].orden:03d}"
        return f"→ {len(indices)} clips"

    def _color_de_cuarto(self, cuarto: str) -> str:
        rooms = self.room_selection.active_rooms()
        return theme.room_color(rooms.index(cuarto)) if cuarto in rooms else theme.TEXT_3

    def _registrar(self, etiqueta: str, detalle: str, color: str,
                   clips: list[int], campos: tuple[str, ...],
                   rooms_antes: list[str] | None = None) -> None:
        """Guarda el estado ANTERIOR de `campos` en `clips`.

        Se llama SIEMPRE antes de mutar, nunca despues -- si no, guarda el
        estado nuevo y deshacer no hace nada. Y guarda solo los campos que la
        accion toca: con el clip entero, revertir una asignacion de cuarto se
        llevaria puesto el pick que se marco despues.
        """
        antes = {
            indice: {campo: _copiar(getattr(self.clips[indice], campo)) for campo in campos}
            for indice in clips
            if 0 <= indice < len(self.clips)
        }
        self.history.push(HistoryEntry(etiqueta, detalle, color, antes, rooms_antes))
        self._refresh_history()

    def _refresh_history(self) -> None:
        self.room_rail.set_history(self.history.entries())
        self.tool_column.set_can_undo(self.history.can_undo())

    def undo(self) -> None:
        """`⌘Z`: deshace la accion de arriba del historial."""
        self._aplicar_entrada(self.history.undo_last())

    def revert(self, entry_id: int) -> None:
        """El boton `↺` de una fila cualquiera, no solo la de arriba."""
        self._aplicar_entrada(self.history.revert(entry_id))

    def _aplicar_entrada(self, entrada: HistoryEntry | None) -> None:
        if entrada is None:
            return
        for indice, campos in entrada.antes.items():
            if 0 <= indice < len(self.clips):
                for campo, valor in campos.items():
                    setattr(self.clips[indice], campo, _copiar(valor))
        if entrada.rooms_antes is not None:
            seleccion = RoomSelection()
            for cuarto in entrada.rooms_antes:
                seleccion.add(cuarto)
            self.room_selection = seleccion
            self._router.active_rooms = seleccion.active_rooms()
        self._refresh_sheet()
        self._refresh_history()
        self._autosave()

    # ------------------------------------------------------------------
    # refresco de la UI
    # ------------------------------------------------------------------

    def _refresh_rail(self) -> None:
        from collections import Counter

        counts: Counter[str] = Counter()
        for clip in self.clips:
            if clip.categoria_path:
                counts[clip.categoria_path[0]] += 1
        rooms = self.room_selection.active_rooms()
        total = len(self.clips)
        sin_clasificar = sum(1 for c in self.clips if not c.categoria_path)
        picks = sum(1 for c in self.clips if c.flag == "pick")
        rejects = sum(1 for c in self.clips if c.flag == "reject")

        self.room_rail.set_progress(total - sin_clasificar, total, sin_clasificar)
        self.room_rail.set_rooms(rooms, dict(counts))
        self.room_rail.set_flags(picks, rejects, sin_clasificar)
        clip = self.current_clip
        self.room_rail.set_current_room(
            clip.categoria_path[0] if clip and clip.categoria_path else None
        )
        self.title_bar.set_project(self.project_name, total)
        self.status_bar.set_unclassified(sin_clasificar)

    def _refresh_overlays(self) -> None:
        clip = self.current_clip
        stage = self.video_stage
        if clip is None:
            stage.file_label.setText("")
            stage.badges.set_room(None, None)
            stage.badges.set_flag("none")
            stage.timecode_label.setText("")
            self.status_bar.set_clip_info(None, None, None, None)
            self.tool_column.set_range(None, None)
            self.tool_column.set_flag("none")
            return

        nombre = Path(clip.ruta).name
        # Con filtro, tu posicion en el shooting entero no te sirve de nada:
        # lo que quieres saber es cuanto falta para terminar lo que estas
        # haciendo (DECISIONES.md). Sin filtro, el total si sirve.
        if self.filters.esta_filtrando():
            indices = self.queue()
            if self.current_index in indices:
                posicion = indices.index(self.current_index) + 1
                stage.file_label.setText(
                    f"{nombre}    {posicion} de {len(indices)} en la cola"
                )
            else:
                # el clip actual quedo fuera del filtro -- pasa apenas lo
                # resuelves. Inventarle una posicion ("0 de 12") seria mentir
                stage.file_label.setText(f"{nombre}    {len(indices)} en la cola")
        else:
            stage.file_label.setText(
                f"{nombre}    {self.current_index + 1} / {len(self.clips)}"
            )

        cuarto = " › ".join(clip.categoria_path) if clip.categoria_path else None
        active_rooms = self.room_selection.active_rooms()
        color = (
            theme.room_color(active_rooms.index(clip.categoria_path[0]))
            if clip.categoria_path and clip.categoria_path[0] in active_rooms
            else None
        )
        stage.badges.set_room(cuarto, color)
        stage.badges.set_flag(clip.flag)

        self.status_bar.set_clip_info(
            nombre,
            self._clip_sizes.get(self.current_index),
            clip.fps,
            self._clip_rotations.get(self.current_index, 0),
        )
        self.tool_column.set_range(clip.in_frame, clip.out_frame)
        self.tool_column.set_flag(clip.flag)

    # ------------------------------------------------------------------
    # el rail edita los cuartos en el lugar
    # ------------------------------------------------------------------

    def _sync_rooms(self) -> None:
        """Vuelve a pasarle al router la lista de cuartos.

        Obligatorio despues de CUALQUIER cambio del rail: el router se
        construye una sola vez y se queda con la lista que le dieron. Si no
        se vuelve a pasar, las teclas siguen apuntando a la lista vieja y no
        dan ningun sintoma visible -- clasifican al cuarto equivocado en
        silencio.
        """
        self._router.active_rooms = self.room_selection.active_rooms()
        self._refresh_sheet()
        self._autosave()

    def _on_room_created(self, nombre: str) -> None:
        self.room_selection.add(nombre)
        self._sync_rooms()

    def _on_room_renamed(self, viejo: str, nuevo: str) -> None:
        antes = self.room_selection.active_rooms()
        self.room_selection.rename(viejo, nuevo)
        if self.room_selection.active_rooms() == antes:
            return  # el nombre estaba repetido o vacio: no se toca nada
        # los clips ya clasificados viajan con el nombre: si no, quedarian
        # apuntando a un cuarto que ya no existe y desaparecerian del rail
        # sin haberse movido a ningun lado
        for clip in self.clips:
            if clip.categoria_path and clip.categoria_path[0] == viejo:
                clip.categoria_path = [nuevo]
        self._sync_rooms()

    def _on_room_moved(self, nombre: str, delta: int) -> None:
        # reordenar cambia la TECLA, no a que cuarto pertenece cada clip
        self.room_selection.move(nombre, delta)
        self._sync_rooms()

    def _on_room_removed(self, nombre: str) -> None:
        # la unica operacion del rail que destruye trabajo, y por eso la unica
        # que deja entrada en el historial: crear, renombrar y mover no pierden
        # datos y se revierten a mano en un gesto
        afectados = [
            i for i, c in enumerate(self.clips)
            if c.categoria_path and c.categoria_path[0] == nombre
        ]
        self._registrar(
            etiqueta=nombre,
            detalle="cuarto borrado",
            color=self._color_de_cuarto(nombre),
            clips=afectados,
            campos=("categoria_path",),
            rooms_antes=self.room_selection.active_rooms(),
        )
        self.room_selection.remove(nombre)
        # sus clips vuelven a la cola de trabajo, que es donde tienen que
        # estar: son clips que hay que volver a decidir, no clips perdidos
        for indice in afectados:
            self.clips[indice].categoria_path = []
        self._sync_rooms()

    def _tick_saved_indicator(self) -> None:
        if self._last_saved_at is None:
            return
        self.title_bar.set_saved_seconds(int(time.monotonic() - self._last_saved_at))

    def _update_scrub_bar(self) -> None:
        clip = self.current_clip
        if clip is None:
            self.scrub_bar.set_duration(0.0)
            self.scrub_bar.set_in_out(None, None, 0.0)
            self._update_timecode()
            return
        duration = self.video_widget.player.duration or self._clip_durations.get(
            self.current_index, 0.0
        )
        self.scrub_bar.set_duration(duration)
        self.scrub_bar.set_in_out(clip.in_frame, clip.out_frame, clip.fps)
        self._update_timecode()

    def _update_timecode(self) -> None:
        """El timecode va SOBRE la imagen: marcar in/out por frame exacto
        exige mirar imagen y numero sin saltar la vista."""
        clip = self.current_clip
        if clip is None:
            self.video_stage.timecode_label.setText("")
            return
        fps = clip.fps
        position = self.video_widget.player.position
        pos_frame = round(position * fps) if fps > 0 else 0
        partes = [format_timecode(pos_frame, fps)]
        if clip.in_frame is not None:
            partes.append(f"IN {format_timecode(clip.in_frame, fps)}")
        if clip.out_frame is not None:
            partes.append(f"OUT {format_timecode(clip.out_frame, fps)}")
        if clip.in_frame is not None and clip.out_frame is not None and fps > 0:
            segundos = abs(clip.out_frame - clip.in_frame) / fps
            partes.append(f"rango {round(segundos)}s")
        self.video_stage.timecode_label.setText("   ".join(partes))

    def _tick_playhead(self) -> None:
        if self.current_clip is None:
            return
        self.scrub_bar.set_position(self.video_widget.player.position)
        self._update_timecode()

    def _on_scrub_seek_started(self) -> None:
        self.video_widget.player.pause()

    def _on_scrub_seek(self, seconds: float) -> None:
        self.video_widget.player.seek(seconds)
        self.scrub_bar.set_position(seconds)
        self._update_timecode()

    # ------------------------------------------------------------------
    # carga de clips
    # ------------------------------------------------------------------

    def load_clips(self, clips: list[Clip]) -> None:
        self.clips = clips
        self.current_index = 0
        # el historial guarda INDICES de clip: con material nuevo apuntarian
        # a otros clips, asi que lo de antes ya no aplica a nada
        self.history.clear()
        self._refresh_history()
        self._refresh_sheet(force_rebuild=True)
        if clips:
            self.video_widget.open_clip(clips[0].ruta)
        self._resize_video_stage()
        self._autosave()

    def _autosave(self) -> None:
        if self.session_path is None:
            return
        # no escribe ahora: reinicia el debounce, para escribir una sola vez
        # por rafaga de teclas en vez de una vez por tecla.
        self._autosave_timer.start()

    def _write_autosave_now(self) -> None:
        if self.session_path is None:
            return
        # sin `category_tree`: los subcuartos murieron en la F3. Una sesion
        # vieja que lo traiga se ignora al cargar (ver app.py).
        data = {
            "proyecto": self.project_name,
            "rooms": self.room_selection.active_rooms(),
            "clips": [c.to_dict() for c in self.clips],
        }
        self._autosave_pool.start(_AutosaveWriteJob(self.session_path, data))
        self._last_saved_at = time.monotonic()
        self._tick_saved_indicator()

    def _flush_autosave(self) -> None:
        """Fuerza el guardado pendiente ya mismo -- al cerrar la ventana,
        para no perder la ultima edicion si cae dentro del debounce."""
        if self._autosave_timer.isActive():
            self._autosave_timer.stop()
            self._write_autosave_now()
        self._autosave_pool.waitForDone(2000)

    def _load_clips_from_ingest(self) -> None:
        clips: list[Clip] = []
        durations: dict[int, float] = {}
        sizes: dict[int, tuple[int, int]] = {}
        rotations: dict[int, int] = {}
        orden = 1
        for folder in self.ingest_tree.top_level_folders():
            for video in folder.files:
                try:
                    info = self._probe_clip(video)
                except Exception:
                    continue
                clips.append(Clip(orden=orden, ruta=video, categoria_path=[], fps=info["fps"]))
                index = len(clips) - 1
                fps = info.get("fps") or 0
                duration_frames = info.get("duration_frames")
                if fps and duration_frames:
                    # duracion real del clip, solo en memoria -- no toca el
                    # contrato del manifest.
                    durations[index] = duration_frames / fps
                width = info.get("width") or 0
                height = info.get("height") or 0
                if width and height:
                    # tamaño real ya corregido por rotacion (ver probe.py):
                    # de aqui sale la relacion de aspecto que decide el ancho
                    # del video y la forma de la miniatura.
                    sizes[index] = (int(width), int(height))
                rotations[index] = int(info.get("rotation") or 0)
                orden += 1
        self._clip_durations = durations
        self._clip_sizes = sizes
        self._clip_rotations = rotations
        self.load_clips(clips)
        self._schedule_thumbnails()

    def _schedule_thumbnails(self) -> None:
        if not self.clips:
            return
        # una importacion nueva invalida las señales stale de la anterior
        self._thumb_generation += 1
        generation = self._thumb_generation
        cache_root = self._thumbnail_cache_root
        for index, clip in enumerate(self.clips):
            cache_dir = cache_dir_for(clip.ruta, cache_root)
            cached_frames = sorted(cache_dir.glob("strip_*.jpg")) if cache_dir.exists() else []
            if not cached_frames and cache_dir.exists():
                single = cache_dir / "00000001.jpg"
                if single.exists():
                    cached_frames = [single]
            if cached_frames:
                # cache hit: mismo clip ya procesado en una sesion anterior.
                self._on_thumbnail_ready(generation, index, cached_frames)
                continue
            duration_seconds = self._clip_durations.get(index)
            job = _ThumbnailJob(generation, index, clip.ruta, cache_dir, duration_seconds)
            job.signals.done.connect(self._on_thumbnail_ready)
            self._thread_pool.start(job)

    def _on_thumbnail_ready(self, generation: int, index: int, frames: list[Path] | None) -> None:
        if generation != self._thumb_generation:
            return  # senal de una importacion ya descartada
        if not frames or index >= self.clip_sheet.count():
            return
        pixmaps = [QPixmap(str(f)) for f in frames]
        # `item_widgets` va por INDICE DE CLIP, no por posicion visual: los
        # clips se ven agrupados por cuarto, pero esta lista conserva el
        # orden de `self.clips`. Reordenarla haria que las miniaturas
        # aterricen en la tarjeta equivocada.
        if len(pixmaps) > 1:
            self.clip_sheet.item_widgets[index].set_frames(pixmaps)
        else:
            self.clip_sheet.item_widgets[index].set_pixmap(pixmaps[0])

    # ------------------------------------------------------------------
    # acciones
    # ------------------------------------------------------------------

    def handle_key_press(self, key: str) -> None:
        if self.current_clip is None:
            return
        if key in ("i", "o", "u"):
            campos = {"i": ("in_frame",), "o": ("out_frame",)}.get(
                key, ("in_frame", "out_frame")
            )
            self._registrar(
                etiqueta="IN/OUT",
                detalle=self._detalle([self.current_index]),
                color=theme.TRIM_COLOR,
                clips=[self.current_index],
                campos=campos,
            )
            if key == "i":
                self.current_clip.in_frame = self.video_widget.player.mark_in(
                    self.current_clip.fps
                )
            elif key == "o":
                self.current_clip.out_frame = self.video_widget.player.mark_out(
                    self.current_clip.fps
                )
            else:
                self.current_clip.in_frame = None
                self.current_clip.out_frame = None
            self._refresh_sheet()
            self._autosave()
            return
        room_path = self._router.resolve_room_key(key)
        if room_path is not None:
            self._apply_categoria_to_targets(room_path)
            self._refresh_sheet()
            self._autosave()
            # «asignar cuarto y avanzar»: el clip recien resuelto suele salir
            # de la cola, y quedarse en el obligaria a apretar la flecha
            # 128 veces de mas
            self._avanzar_en_la_cola()
            return
        action = self._router.resolve_action_key(key)
        if action is not None:
            self._registrar(
                etiqueta={"pick": "Pick", "reject": "Reject"}.get(action, action.title()),
                detalle=self._detalle([self.current_index]),
                color={"pick": theme.PICK_COLOR, "reject": theme.REJECT_COLOR}.get(
                    action, theme.TEXT_3
                ),
                clips=[self.current_index],
                campos=("flag",),
            )
            self.current_clip.flag = action
            self._refresh_sheet()
            self._autosave()

    def handle_arrow(self, direction: str) -> None:
        """Se mueve DENTRO de la cola filtrada, no sobre los 128.

        El clip actual puede no estar en la cola --pasa cada vez que resuelves
        uno y sale de ella--, asi que no alcanza con buscar su posicion: se
        busca el siguiente (o el anterior) que si este.
        """
        if not self.clips:
            return
        indices = self.queue()
        if not indices:
            return
        if direction == "next":
            siguientes = [i for i in indices if i > self.current_index]
            self.current_index = siguientes[0] if siguientes else indices[-1]
        else:
            anteriores = [i for i in indices if i < self.current_index]
            self.current_index = anteriores[-1] if anteriores else indices[0]
        clip = self.current_clip
        if clip is not None:
            self.video_widget.open_clip(clip.ruta)
        self._refresh_sheet()
        self._resize_video_stage()
        self._autosave()

    def select_clip(self, index: int) -> None:
        if not (0 <= index < len(self.clips)):
            return
        self.current_index = index
        clip = self.current_clip
        if clip is not None:
            self.video_widget.open_clip(clip.ruta)
        # No reconstruir la hoja aqui: la seleccion solo cambia el clip
        # actual (borde), no los datos de ningun clip. Reconstruir destruye
        # y reemplaza los widgets --incluyendo el que esta dentro de su
        # propio mousePressEvent-- y en el run loop nativo de cocoa eso
        # termina en SIGSEGV. Ademas borraria los pixmaps ya cargados.
        self.clip_sheet.set_current(self.current_index)
        self._refresh_rail()
        self._refresh_overlays()
        self._update_scrub_bar()
        self._resize_video_stage()
        self._autosave()

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
            orientacion="horizontal",  # TODO F9: derivar del material predominante
            clips=self.clips,
        )
        manifest.write_json(Path(path))

    def _on_import_folders(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta de material")
        if not folder:
            return
        self.ingest_tree.import_folder(Path(folder))
        self.status_bar.set_volume(folder)
        self._load_clips_from_ingest()

    def _refresh_sheet(self, force_rebuild: bool = False) -> None:
        active_rooms = self.room_selection.active_rooms()
        thumbs = [
            ClipThumbnail(
                path=clip.ruta,
                room_label=clip.categoria_path[-1] if clip.categoria_path else "Sin clasificar",
                flag=clip.flag,
                room_color=(
                    theme.room_color(active_rooms.index(clip.categoria_path[0]))
                    if clip.categoria_path and clip.categoria_path[0] in active_rooms
                    else None
                ),
                numero=clip.orden,
                in_frame=clip.in_frame,
                out_frame=clip.out_frame,
                fps=clip.fps,
                duration_frames=(
                    round(self._clip_durations[index] * clip.fps)
                    if index in self._clip_durations
                    else None
                ),
                aspect_ratio=self.aspect_ratio_for(index),
            )
            for index, clip in enumerate(self.clips)
        ]
        if force_rebuild:
            self.clip_sheet.set_clips(thumbs)
        else:
            # actualiza en el lugar: eso es lo que preserva las miniaturas ya
            # cargadas por los _ThumbnailJob al navegar o clasificar.
            self.clip_sheet.update_clips(thumbs)
        # la MISMA lista que recorren las flechas: si se calcularan por
        # separado, la hoja y la navegacion se desincronizan
        indices = self.queue()
        filtrando = self.filters.esta_filtrando()
        self.clip_sheet.set_visible_indices(indices if filtrando else None)
        self.clip_sheet.set_counts(contar(self.clips))
        self.clip_sheet.set_queue_size(len(indices), filtrando)
        self.clip_sheet.set_current(self.current_index)
        self._refresh_rail()
        self._refresh_overlays()
        self._update_scrub_bar()
