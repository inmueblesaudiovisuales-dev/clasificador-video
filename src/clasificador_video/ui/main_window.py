# src/clasificador_video/ui/main_window.py
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
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
from clasificador_video.player import SPEED_PROFILES
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
from clasificador_video.ui.room_palette import RoomPalette
from clasificador_video.ui.room_rail import RoomRail
from clasificador_video.ui.status_bar import StatusBar
from clasificador_video.ui.title_bar import TitleBar
from clasificador_video.ui.tool_column import ToolColumn
from clasificador_video.ui.video_stage import VideoStage, etiqueta_de_velocidad
from clasificador_video.ui.video_widget import format_timecode

# Donde arranca cada clip. El principio de un recorrido siempre es la camara
# acomodandose, y el frame de portada de la hoja sale del mismo punto
# (DECISIONES.md): al llegar al clip ves lo mismo que viste en la miniatura.
START_PERCENT = 25

# Como se nombra y se pinta cada estado en el historial. Un solo lugar: la F2
# los tenia repartidos en dos diccionarios en linea, y agregar `destacado`
# habria que acordarse de hacerlo en los dos.
ETIQUETAS_DE_ESTADO = {
    "pick": "Pick", "reject": "Reject",
    "destacado": "Destacado", "none": "Sin marcar",
}
COLORES_DE_ESTADO = {
    "pick": theme.PICK_COLOR, "reject": theme.REJECT_COLOR,
    "destacado": theme.STAR_COLOR, "none": theme.TEXT_3,
}


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
        # el clip actual arranco solo (y el badge `▶ auto` esta prendido).
        # Se apaga en cuanto pausas y no vuelve hasta el siguiente clip.
        self._auto_reproduciendo = False
        # solo video: los paneles escondidos y el video con todo el ancho
        self._solo_video = False
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
        self.video_stage.speed.selected.connect(self._on_speed_changed)
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

        # La paleta flota sobre el video: hija de la ventana y NO un QDialog
        # modal, porque un modal roba el teclado y hay que cerrarlo para
        # seguir clasificando.
        self.room_palette = RoomPalette(self)
        self.room_palette.room_chosen.connect(self._on_room_elegido_en_paleta)
        self.room_palette.room_created.connect(self._on_room_creado_en_paleta)

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
        # en solo video no hay barras que restar: estan escondidas, y seguir
        # restandolas dejaba el video 33 px mas angosto de lo que cabe
        alto_cuerpo = self.height()
        if not self._solo_video:
            alto_cuerpo -= theme.TITLEBAR_HEIGHT + theme.STATUSBAR_HEIGHT
        ancho = VideoStage.width_for(alto_cuerpo, self.aspect_ratio_for(self.current_index))
        # El minimo REAL de la hoja, no la constante: su encabezado --titulo,
        # buscador, chip de cola y las dos filas de filtros-- pide bastante mas
        # que `SHEET_MIN_WIDTH`. Usar la constante creaba un lazo: el video
        # pedia mas ancho del que habia, la ventana crecia, eso agrandaba el
        # maximo, el video crecia otra vez... con un clip horizontal la ventana
        # se inflaba de 1600 a 2653 px.
        if self._solo_video:
            # sin paneles no hay nada que restarle: el video se lleva la
            # ventana entera
            maximo = self.width()
        else:
            minimo_hoja = max(
                theme.SHEET_MIN_WIDTH, self.clip_sheet.minimumSizeHint().width()
            )
            maximo = (self.width() - theme.RAIL_WIDTH - theme.TOOLCOL_WIDTH
                      - minimo_hoja)
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
            # `⇧P`: el cuarto estado, destacado
            ("Shift+P", lambda: self.handle_key_press("shift+p")),
            ("U", lambda: self.handle_key_press("u")),
            # `S`: el mismo cuarto que el clip anterior
            ("S", lambda: self.handle_key_press("s")),
            # `⏎`: la paleta de cuartos. Comparte tecla con renombrar en el
            # rail, y por eso el handler mira quien tiene el foco.
            ("F", lambda: self.handle_key_press("f")),
            ("Esc", lambda: self.handle_key_press("escape")),
            ("Return", self._on_enter),
            ("Enter", self._on_enter),
            # `J K L`: la convencion de Premiere, Avid y Resolve
            ("L", lambda: self.handle_key_press("l")),
            ("K", lambda: self.handle_key_press("k")),
            ("J", lambda: self.handle_key_press("j")),
            # cuadro a cuadro, tambien como en Premiere
            (",", lambda: self.handle_key_press(",")),
            (".", lambda: self.handle_key_press(".")),
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

        # Los de arriba son teclas SUELTAS --letras, digitos, espacio, flechas,
        # coma y punto-- y un `QShortcut` de contexto `WindowShortcut` se
        # resuelve ANTES de entregarle la tecla al widget con foco. Sin esta
        # guarda, escribir "cocina" en el buscador de la hoja dispararia la
        # velocidad con la `c`... perdon, con la `i` el marcado de in, con la
        # `o` el de out, y "1" asignaria un cuarto -- mientras el texto ni
        # siquiera llega al campo.
        #
        # No se pudo comprobar en esta maquina: los atajos solo se disparan con
        # la ventana ACTIVA, y un proceso lanzado desde la terminal no logra
        # activarse en macOS. Por eso se blinda por construccion en vez de
        # apostar a que Qt haga lo que uno espera. Los de modificador (⌘Z, ⌘E,
        # ⌘R, ⌘A) NO se guardan: no chocan con escribir.
        self._shortcuts = []
        self._atajos_de_tecla_suelta = []
        for sequence, handler in shortcuts:
            con_modificador = (
                isinstance(sequence, QKeySequence.StandardKey)
                or (isinstance(sequence, str) and "Ctrl" in sequence)
            )
            atajo = QShortcut(
                QKeySequence(sequence), self,
                activated=(handler if con_modificador
                           else self._solo_si_no_escribes(handler)),
            )
            self._shortcuts.append(atajo)
            if not con_modificador:
                self._atajos_de_tecla_suelta.append(atajo)

        # Se DESACTIVAN mientras escribes, no basta con ignorarlos: un atajo
        # que se dispara CONSUME la tecla, asi que con solo ignorarla el
        # buscador se quedaria mudo --ni cambia la velocidad ni aparece la
        # letra--. Un atajo desactivado no compite, y la tecla llega al campo.
        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._al_cambiar_el_foco)

    def _al_cambiar_el_foco(self, _viejo, nuevo) -> None:
        escribiendo = self._es_campo_de_texto(nuevo)
        for atajo in self._atajos_de_tecla_suelta:
            atajo.setEnabled(not escribiendo)

    def _solo_si_no_escribes(self, handler: Callable[[], None]) -> Callable[[], None]:
        """Segunda linea de defensa, por si el foco cambio sin avisar."""
        def envuelto() -> None:
            if self.escribiendo_texto():
                return
            handler()
        return envuelto

    @staticmethod
    def _es_campo_de_texto(widget) -> bool:
        """Se pregunta por el TIPO y no por cual widget es, para que un campo
        nuevo quede cubierto sin que nadie se acuerde de venir a agregarlo.
        Hoy son el buscador de la hoja y el renombrado de cuartos del rail.
        """
        from PySide6.QtWidgets import QAbstractSpinBox, QLineEdit, QTextEdit

        return isinstance(widget, (QLineEdit, QTextEdit, QAbstractSpinBox))

    @classmethod
    def escribiendo_texto(cls) -> bool:
        """¿El foco esta en un campo donde se escribe?"""
        return cls._es_campo_de_texto(QApplication.focusWidget())

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

    # ------------------------------------------------------------------
    # la paleta de cuartos (`⏎`)
    # ------------------------------------------------------------------

    def _on_enter(self) -> None:
        """`⏎` abre la paleta, salvo cuando la tecla ya significa otra cosa.

        Con una fila del rail enfocada, `⏎` renombra ese cuarto; dentro de un
        campo de texto, confirma lo que escribiste. Un `QShortcut` normal se
        dispara sin importar quien tiene el foco, asi que sin esta comprobacion
        la paleta se robaria las dos cosas y nadie sabria por que dejaron de
        funcionar.
        """
        if self.escribiendo_texto() or self._foco_en_el_rail():
            return
        self.room_palette.abrir(
            self.room_selection.active_rooms(),
            self._conteos_por_cuarto(),
            len(self._bulk_target_indices()),
        )
        self._colocar_paleta()

    def _foco_en_el_rail(self) -> bool:
        foco = QApplication.focusWidget()
        return foco is not None and self.room_rail.isAncestorOf(foco)

    def _conteos_por_cuarto(self) -> dict[str, int]:
        from collections import Counter

        cuenta: Counter[str] = Counter()
        for clip in self.clips:
            if clip.categoria_path:
                cuenta[clip.categoria_path[0]] += 1
        return dict(cuenta)

    def _colocar_paleta(self) -> None:
        """Centrada sobre el video, no sobre la ventana: es donde estas
        mirando, y sobre la hoja taparia justo los clips que quieres juzgar."""
        etapa = self.video_stage
        origen = etapa.mapTo(self, etapa.rect().topLeft())
        x = origen.x() + (etapa.width() - self.room_palette.width()) // 2
        self.room_palette.move(max(0, x), origen.y() + 90)

    def _on_room_elegido_en_paleta(self, nombre: str) -> None:
        self._asignar_cuarto([nombre])

    def _on_room_creado_en_paleta(self, nombre: str) -> None:
        """Crear y asignar de una: crear y volver a apuntar serian dos pasos
        para una sola intencion."""
        self.room_selection.add(nombre)
        self._sync_rooms()
        self._asignar_cuarto([nombre])

    def _asignar_cuarto(self, room_path: list[str]) -> None:
        """Un solo camino para asignar cuarto, lo pida un digito o la `S`.

        Con dos caminos, `S` seria una asignacion de segunda: no registraria
        en el historial, o no avanzaria, y eso no se ve hasta usarla.
        """
        self._apply_categoria_to_targets(room_path)
        self._refresh_sheet()
        self._autosave()
        # «asignar cuarto y avanzar»: el clip recien resuelto suele salir de
        # la cola, y quedarse en el obligaria a apretar la flecha 128 veces
        # de mas
        self._avanzar_en_la_cola()

    def _cuarto_del_clip_anterior(self) -> str | None:
        """El cuarto del clip CON CUARTO mas cercano hacia atras.

        No es `clips[actual - 1]` a secas: si el anterior quedo sin clasificar
        se sigue buscando hacia atras, o la tecla se volveria inutil apenas te
        saltas uno. Y se mira el orden de RODAJE, no la cola filtrada: las
        rachas son consecutivas en el tiempo, y un filtro puede dejar juntos
        dos clips de cuartos distintos.
        """
        for indice in range(self.current_index - 1, -1, -1):
            categoria = self.clips[indice].categoria_path
            if categoria:
                return categoria[0]
        return None

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
                   cuarto_borrado: tuple[str, int] | None = None) -> None:
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
        self.history.push(HistoryEntry(etiqueta, detalle, color, antes, cuarto_borrado))
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
        if entrada.cuarto_borrado is not None:
            # se REINSERTA en su posicion, que es lo que le da la tecla.
            # Restaurar la lista entera --como hacia antes-- se llevaba puesto
            # todo lo creado despues del borrado.
            nombre, posicion = entrada.cuarto_borrado
            self.room_selection.insert_at(posicion, nombre)
            self._router.active_rooms = self.room_selection.active_rooms()
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
        destacados = sum(1 for c in self.clips if c.flag == "destacado")
        self.room_rail.set_flags(picks, rejects, sin_clasificar, destacados)
        clip = self.current_clip
        self.room_rail.set_current_room(
            clip.categoria_path[0] if clip and clip.categoria_path else None
        )
        anterior = self._cuarto_del_clip_anterior()
        self.room_rail.set_same_room(
            anterior,
            theme.room_color(rooms.index(anterior)) if anterior in rooms else None,
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
        rooms = self.room_selection.active_rooms()
        self._registrar(
            etiqueta=nombre,
            detalle="cuarto borrado",
            color=self._color_de_cuarto(nombre),
            clips=afectados,
            campos=("categoria_path",),
            cuarto_borrado=(nombre, rooms.index(nombre)) if nombre in rooms else None,
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
        exige mirar imagen y numero sin saltar la vista.

        Desde la F6 el pie son tres piezas y no una etiqueta con todo pegado:
        el timecode grande, el numero de cuadro al lado, y la pastilla con el
        resumen del rango. El IN/OUT en texto se fue con la pastilla: es el
        mismo dato dicho dos veces, y la barra ya lo muestra con sus manijas.
        """
        clip = self.current_clip
        stage = self.video_stage
        if clip is None:
            stage.set_timecode("", None)
            stage.set_in_out_labels(None, None)
            stage.set_range_pill(None, None, 0.0)
            return
        fps = clip.fps
        pos_frame = round(self.video_widget.player.position * fps) if fps > 0 else 0
        stage.set_timecode(format_timecode(pos_frame, fps), pos_frame)
        stage.set_in_out_labels(
            format_timecode(clip.in_frame, fps) if clip.in_frame is not None else None,
            format_timecode(clip.out_frame, fps) if clip.out_frame is not None else None,
        )

        total = self.video_widget.player.duration or self._clip_durations.get(
            self.current_index, 0.0
        )
        if clip.in_frame is not None and clip.out_frame is not None and fps > 0:
            # `abs`: marcar `O` antes que `I` deja out < in, y un rango de
            # "-212 cuadros" no significa nada
            cuadros = abs(clip.out_frame - clip.in_frame)
            stage.set_range_pill(cuadros / fps, cuadros, total, fps)
        else:
            stage.set_range_pill(None, None, total, fps)

    def _tick_playhead(self) -> None:
        if self.current_clip is None:
            return
        # mpv reporta la duracion de forma ASINCRONA: cuando se abrio el clip
        # todavia no existia, asi que hay que volver a pedirsela. Sin esto la
        # barra se queda en 0 y no dibuja playhead, marcas ni rango -- estuvo
        # muerta en la app real y el arnes no lo mostraba, porque sus datos de
        # ejemplo traen la duracion escrita a mano.
        duracion = self.video_widget.player.duration or self._clip_durations.get(
            self.current_index, 0.0
        )
        if duracion and duracion != self.scrub_bar.duration:
            self.scrub_bar.set_duration(duracion)
        self.scrub_bar.set_position(self.video_widget.player.position)
        self._update_timecode()
        # El badge `▶ auto` miente en cuanto pausas: lo que arranco solo ya no
        # esta corriendo. Y no vuelve al reanudar a mano -- eso ya lo
        # arrancaste tu. Se apaga hasta el proximo cambio de clip.
        if self._auto_reproduciendo and self.video_widget.player.is_paused:
            self._auto_reproduciendo = False
            self.video_stage.badges.set_auto(False)

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
        self._abrir_clip_actual()
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

    # ------------------------------------------------------------------
    # velocidad: `J K L`, la convencion de Premiere
    # ------------------------------------------------------------------

    def _acelerar(self) -> None:
        """`L`: cicla 1× → 2× → 4× → 1× y arranca si estaba pausado.

        Arrancar es parte de lo que hace `L` en Premiere, Avid y Resolve: si
        solo cambiara el numero, apretarla sobre un video pausado no haria
        nada visible.
        """
        actual = self.video_widget.player.speed
        perfiles = SPEED_PROFILES
        siguiente = perfiles[(perfiles.index(actual) + 1) % len(perfiles)] \
            if actual in perfiles else perfiles[0]
        self._aplicar_velocidad(siguiente)
        self.video_widget.player.play()

    def _frenar(self) -> None:
        """`K`: vuelve a 1× y pausa de un golpe, sin importar donde estabas.

        No es un interruptor: sobre un video ya pausado lo deja pausado.
        """
        self._aplicar_velocidad(SPEED_PROFILES[0])
        self.video_widget.player.pause()

    def alternar_solo_video(self) -> None:
        """`F`: esconde todo menos el video, y lo vuelve a traer.

        No es un modo aparte: las teclas siguen funcionando, asi que se puede
        seguir clasificando sin la hoja a la vista. Y se recalcula el ancho,
        porque esconder los paneles sin recalcular dejaria el mismo video con
        franjas negras al costado -- justo lo que este rediseño evita.
        """
        self._solo_video = not self._solo_video
        for panel in (self.title_bar, self.room_rail, self.tool_column,
                      self.clip_sheet, self.status_bar):
            panel.setVisible(not self._solo_video)
        self._resize_video_stage()

    def _pasar_cuadro(self, delta: int) -> None:
        """`.` adelante, `,` atras. La convencion de Premiere, y la unica
        forma de marcar in/out en el cuadro exacto.

        Refresca el pie a mano en vez de esperar al tick del playhead: el
        tick corre cada 100 ms y el cuadro a cuadro se usa apretando la tecla
        varias veces seguidas -- con el retardo, el numero va siempre un
        cuadro atras de lo que ves.
        """
        if self.current_clip is None:
            return
        self.video_widget.player.step_frame(delta, self.current_clip.fps)
        self._tick_playhead()

    def _aplicar_velocidad(self, velocidad: float) -> None:
        """Un solo lugar mueve las DOS vistas del mismo dato -- el
        reproductor y el control segmentado. Que se contradigan es un bug que
        este proyecto ya tuvo dos veces (la tarjeta y la barra de rango)."""
        self.video_widget.player.set_speed(velocidad)
        self.video_stage.speed.set_current(etiqueta_de_velocidad(velocidad))

    def _on_speed_changed(self, etiqueta: str) -> None:
        """Del control segmentado al reproductor. La etiqueta se traduce
        buscando en los perfiles, no parseando el texto.

        Pasa por `_aplicar_velocidad` --que tambien sincroniza el control--
        aunque venga del control mismo: al hacer click Qt ya lo dejo marcado
        y volver a marcarlo no cuesta nada, pero asi las dos vistas convergen
        venga el cambio de donde venga.
        """
        for velocidad in SPEED_PROFILES:
            if etiqueta_de_velocidad(velocidad) == etiqueta:
                self._aplicar_velocidad(velocidad)
                return

    def handle_key_press(self, key: str) -> None:
        # `L` y `K` van ANTES del corte por clip nulo: la app abre sin
        # material y apretarlas no puede depender de que ya hayas importado.
        if key == "l":
            self._acelerar()
            return
        if key == "k":
            self._frenar()
            return
        if key == "j":
            # reservada para reproducir hacia atras. No se construye --en
            # recorridos de inmuebles no aporta-- pero tampoco se le da otro
            # significado, o el dia que sirva ya estaria ocupada.
            return
        if key in (",", "."):
            self._pasar_cuadro(1 if key == "." else -1)
            return
        if key == "f":
            self.alternar_solo_video()
            return
        if key == "escape":
            # `esc` es la salida universal: si de solo video solo se saliera
            # con `F`, quien entro sin querer no sabe como volver
            if self._solo_video:
                self.alternar_solo_video()
            return
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
        if key == "s":
            cuarto = self._cuarto_del_clip_anterior()
            if cuarto is not None:
                self._asignar_cuarto([cuarto])
            return
        room_path = self._router.resolve_room_key(key)
        if room_path is not None:
            self._asignar_cuarto(room_path)
            return
        action = self._router.resolve_action_key(key)
        if action is not None:
            # repetir la tecla sobre el estado que ya tiene lo apaga: sin esto
            # no habria forma de volver a neutral con el teclado. `⇧P` sobre un
            # destacado tambien apaga; `P` sobre un destacado lo BAJA a pick,
            # que es el escalon de abajo de la misma escalera.
            actual = self.current_clip.flag
            if actual == action:
                nuevo = "none"
            elif action == "pick" and actual == "destacado":
                nuevo = "pick"
            else:
                nuevo = action
            self._registrar(
                etiqueta=ETIQUETAS_DE_ESTADO.get(nuevo, nuevo.title()),
                detalle=self._detalle([self.current_index]),
                color=COLORES_DE_ESTADO.get(nuevo, theme.TEXT_3),
                clips=[self.current_index],
                campos=("flag",),
            )
            self.current_clip.flag = nuevo
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
        self._abrir_clip_actual()
        self._refresh_sheet()
        self._resize_video_stage()
        self._autosave()

    def _abrir_clip_actual(self) -> None:
        """El unico camino por el que se abre un clip.

        Los tres lugares que abren clip --`load_clips`, `select_clip` y
        `handle_arrow`-- pasan por aqui a proposito: si el autoplay se
        agregara en dos de los tres, el tercero quedaria mudo sin dar ningun
        sintoma visible. Hay un test que lo vigila.

        El arranque al 25% se pide ANTES de abrir: `start` la resuelve mpv al
        cargar el archivo. Un seek despues llegaria antes de que mpv reporte
        la duracion, que es asincrona.
        """
        clip = self.current_clip
        if clip is None:
            return
        player = self.video_widget.player
        player.set_start_percent(START_PERCENT)
        self.video_widget.open_clip(clip.ruta)
        player.play()
        self._auto_reproduciendo = True
        self.video_stage.badges.set_auto(True)

    def select_clip(self, index: int) -> None:
        if not (0 <= index < len(self.clips)):
            return
        self.current_index = index
        self._abrir_clip_actual()
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
