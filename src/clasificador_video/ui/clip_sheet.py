# src/clasificador_video/ui/clip_sheet.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.ui import theme
from clasificador_video.ui.text import ElidedLabel

SIN_CLASIFICAR = "Sin clasificar"
MIN_TILE_WIDTH = 150
GAP = 9
FADE_HEIGHT = 60


@dataclass
class ClipThumbnail:
    path: Path
    room_label: str
    flag: str  # "none" | "pick" | "reject"
    room_color: str | None = None
    in_frame: int | None = None
    out_frame: int | None = None
    duration_frames: int | None = None
    aspect_ratio: float = 16 / 9


class ClipCard(QWidget):
    """Tarjeta de un clip: miniatura con la proporcion REAL del video.

    QSS no tiene `aspect-ratio`, asi que el alto se calcula del ancho. Sin
    esto, un clip vertical dentro de una tile apaisada de 150x80 queda de
    45 px de ancho -- que es lo que pasa en el diseño viejo.
    """

    clicked = Signal(object)  # Qt.KeyboardModifier vigente al hacer click

    def __init__(self, clip: ClipThumbnail, parent=None):
        super().__init__(parent)
        self.setObjectName("clipCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self._clip = clip
        self._frames: list = []
        self._scaled_cache: dict[int, object] = {}
        self._poster_index = 0
        self._shown_index: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel("")
        self.image_label.setObjectName("clipCardImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMouseTracking(True)
        layout.addWidget(self.image_label)

    # --- contenido -------------------------------------------------------

    @property
    def clip(self) -> ClipThumbnail:
        return self._clip

    def update_content(self, clip: ClipThumbnail) -> None:
        """Actualiza estado sin tocar la miniatura ya cargada. Reconstruir
        la tarjeta borraria los QPixmap que trajeron los _ThumbnailJob."""
        self._clip = clip
        self._apply_state()

    def set_pixmap(self, pixmap) -> None:
        self._frames = [pixmap]
        self._scaled_cache = {}
        self._poster_index = 0
        self._shown_index = None
        self._show_frame(0)

    def set_frames(self, pixmaps: list) -> None:
        """Tira de frames a lo largo del clip: habilita el scrub al pasar
        el mouse, que ya funcionaba en el diseño viejo y se conserva."""
        if not pixmaps:
            return
        self._frames = pixmaps
        self._scaled_cache = {}
        self._poster_index = len(pixmaps) // 2
        self._shown_index = None
        self._show_frame(self._poster_index)

    def has_pixmap(self) -> bool:
        return bool(self._frames)

    # --- geometria -------------------------------------------------------

    def apply_width(self, ancho: int) -> None:
        alto = max(1, round(ancho / max(self._clip.aspect_ratio, 0.01)))
        self.setFixedSize(ancho, alto)
        self._scaled_cache = {}
        indice = self._shown_index
        self._shown_index = None
        if self._frames:
            self._show_frame(indice if indice is not None else self._poster_index)

    def _show_frame(self, index: int) -> None:
        if index == self._shown_index or not self._frames:
            return
        scaled = self._scaled_cache.get(index)
        if scaled is None:
            scaled = self._frames[index].scaled(
                max(self.width(), 1), max(self.height(), 1),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._scaled_cache[index] = scaled
        self.image_label.setPixmap(scaled)
        self._shown_index = index

    # --- interaccion -----------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(event.modifiers())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if len(self._frames) > 1:
            ancho = max(self.width(), 1)
            ratio = max(0.0, min(1.0, event.position().x() / ancho))
            self._show_frame(round(ratio * (len(self._frames) - 1)))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if self._frames:
            self._show_frame(self._poster_index)
        super().leaveEvent(event)

    # --- estado visual ---------------------------------------------------

    def set_visual_state(self, is_current: bool, is_selected: bool = False) -> None:
        self._is_current = is_current
        self._is_selected = is_selected
        self._apply_state()

    def _apply_state(self) -> None:
        partes = []
        color_flag = {"pick": theme.PICK_COLOR, "reject": theme.REJECT_COLOR}.get(
            self._clip.flag
        )
        if getattr(self, "_is_current", False):
            partes.append(f"border: 2px solid {theme.CURRENT_COLOR};")
        elif color_flag:
            partes.append(f"border: 2px solid {color_flag};")
        else:
            partes.append(f"border: 1px solid {theme.LINE_SOFT};")
        if self._clip.room_color:
            partes.append(f"border-left: 3px solid {self._clip.room_color};")
        if getattr(self, "_is_selected", False):
            partes.append(f"background-color: {theme.SELECTION_WASH};")
        self.setStyleSheet(
            "#clipCard { " + " ".join(partes) + " } #clipCard QLabel { border: none; }"
        )


class _GroupBlock(QWidget):
    """Encabezado de cuarto mas su grilla propia.

    Un bloque por grupo, no una sola grilla gigante: con una sola habria
    que llevar la cuenta de en que fila arranca cada cuarto, y esa
    aritmetica se rompe apenas un grupo se vacia.
    """

    def __init__(self, titulo: str, parent=None):
        super().__init__(parent)
        self.titulo = titulo
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP)

        cabecera = QHBoxLayout()
        cabecera.setSpacing(8)
        self.title_label = ElidedLabel(titulo.upper())
        self.title_label.setObjectName("groupTitle")
        theme.apply_letter_spacing(self.title_label)
        self.count_label = QLabel("0")
        self.count_label.setObjectName("groupCount")
        cabecera.addWidget(self.title_label)
        cabecera.addWidget(self.count_label)
        cabecera.addStretch(1)
        layout.addLayout(cabecera)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(GAP)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.grid_host)

    def set_count(self, cuantos: int) -> None:
        self.count_label.setText(str(cuantos))


class ClipSheet(QWidget):
    """Hoja de contactos: los clips agrupados por cuarto.

    Reemplaza al `Filmstrip`, que era una banda de 220 px de alto fija con
    tiles apaisadas. Aca no hay alto fijo -- ocupa la columna entera -- y
    cada tarjeta tiene la proporcion real de su clip.

    TRES REGLAS que no se pueden romper (ver el plan de la F2):

    1. `item_widgets` sigue indexado por INDICE DE CLIP, no por posicion
       visual: `MainWindow._on_thumbnail_ready` entrega las miniaturas con
       `item_widgets[index]`, y reordenar esta lista las haria aterrizar
       en la tarjeta equivocada.
    2. Agrupar es RE-COLOCAR, jamas reconstruir: reconstruir borra los
       QPixmap ya cargados y, dentro de un mousePressEvent, terminó en
       SIGSEGV en macOS (ver el comentario en main_window.py).
    3. Un bloque por grupo, no una grilla gigante.
    """

    clip_clicked = Signal(int)
    selection_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("clipSheet")
        self.item_widgets: list[ClipCard] = []
        self._blocks: dict[str, _GroupBlock] = {}
        self._current = -1
        self._selected: set[int] = set()
        self._anchor: int | None = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        encabezado = QWidget()
        encabezado.setObjectName("sheetHeader")
        el = QHBoxLayout(encabezado)
        el.setContentsMargins(13, 9, 13, 9)
        self.title_label = QLabel("CLIPS · 0")
        self.title_label.setObjectName("railHeader")
        theme.apply_letter_spacing(self.title_label)
        self.hint_label = QLabel(
            "pasa el mouse por una miniatura para escrubearla · ⇧+click rango · ⌘A grupo"
        )
        self.hint_label.setObjectName("sheetHint")
        el.addWidget(self.title_label)
        el.addStretch(1)
        el.addWidget(self.hint_label)
        raiz.addWidget(encabezado)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(13, 0, 13, 10)
        self._content_layout.setSpacing(14)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._content)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        raiz.addWidget(self._scroll, stretch=1)

        # QSS no tiene `mask-image`: el desvanecido al pie se hace con un
        # widget de degradado encima, transparente al mouse.
        self._fade = QLabel("", self._scroll)
        self._fade.setObjectName("sheetFade")
        self._fade.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    # --- datos -----------------------------------------------------------

    def count(self) -> int:
        return len(self.item_widgets)

    def group_titles(self) -> list[str]:
        return [b.titulo for b in self._ordered_blocks()]

    def set_clips(self, clips: list[ClipThumbnail]) -> None:
        for card in self.item_widgets:
            card.setParent(None)
        for block in self._blocks.values():
            block.setParent(None)
        self.item_widgets = []
        self._blocks = {}
        for index, clip in enumerate(clips):
            card = ClipCard(clip)
            card.clicked.connect(lambda mods, i=index: self._on_card_clicked(i, mods))
            self.item_widgets.append(card)
        self._current = -1
        self._anchor = None
        self._regroup()
        self.title_label.setText(f"CLIPS · {len(clips)}")
        self.set_selected(set())

    def update_clips(self, clips: list[ClipThumbnail]) -> None:
        """Actualiza en el lugar. Si un clip cambió de cuarto, su tarjeta se
        MUEVE de grupo reusando el mismo objeto -- nunca se recrea."""
        if len(clips) != len(self.item_widgets):
            self.set_clips(clips)
            return
        for card, clip in zip(self.item_widgets, clips):
            card.update_content(clip)
        self._regroup()
        self._redraw()

    # --- agrupacion ------------------------------------------------------

    def _group_of(self, clip: ClipThumbnail) -> str:
        return clip.room_label or SIN_CLASIFICAR

    def _ordered_blocks(self) -> list[_GroupBlock]:
        return [
            self._content_layout.itemAt(i).widget()
            for i in range(self._content_layout.count())
            if isinstance(self._content_layout.itemAt(i).widget(), _GroupBlock)
        ]

    def _regroup(self) -> None:
        # los sin clasificar primero: es la cola de trabajo
        titulos: list[str] = []
        for card in self.item_widgets:
            titulo = self._group_of(card.clip)
            if titulo not in titulos:
                titulos.append(titulo)
        titulos.sort(key=lambda t: (t != SIN_CLASIFICAR, t))

        for titulo in titulos:
            if titulo not in self._blocks:
                self._blocks[titulo] = _GroupBlock(titulo)

        # RE-COLOCAR PRIMERO. `_relayout` reparenta cada tarjeta al bloque que
        # le toca ahora. Hacerlo antes de sacar los bloques vacios no es un
        # detalle de estilo: un bloque al que se le quita el padre se destruye
        # y se lleva puestas las tarjetas que todavia cuelgan de el -- con su
        # miniatura ya cargada. Verificado: invertir estas dos lineas rompe
        # `test_reclasificar_mueve_la_tarjeta_sin_recrearla` con
        # "Internal C++ object (ClipCard) already deleted".
        self._relayout()

        for titulo in list(self._blocks):
            if titulo not in titulos:
                self._blocks.pop(titulo).setParent(None)

        while self._content_layout.count():
            self._content_layout.takeAt(0)
        for titulo in titulos:
            self._content_layout.addWidget(self._blocks[titulo])

    def _relayout(self) -> None:
        ancho_util = max(self._content.width() or self.width(), MIN_TILE_WIDTH)
        ancho_util -= 26  # margenes del contenido
        columnas = max(1, (ancho_util + GAP) // (MIN_TILE_WIDTH + GAP))
        ancho_tile = max(1, (ancho_util - GAP * (columnas - 1)) // columnas)

        por_grupo: dict[str, list[ClipCard]] = {}
        for card in self.item_widgets:
            por_grupo.setdefault(self._group_of(card.clip), []).append(card)

        for titulo, block in self._blocks.items():
            while block.grid.count():
                block.grid.takeAt(0)
            tarjetas = por_grupo.get(titulo, [])
            block.set_count(len(tarjetas))
            for posicion, card in enumerate(tarjetas):
                fila, columna = divmod(posicion, columnas)
                card.apply_width(ancho_tile)
                # addWidget sobre un widget que ya existe solo lo reubica:
                # no lo destruye ni le borra la miniatura ya cargada
                block.grid.addWidget(card, fila, columna)

    def resizeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        super().resizeEvent(event)
        self._relayout()
        self._fade.setGeometry(
            0, self._scroll.height() - FADE_HEIGHT, self._scroll.width(), FADE_HEIGHT
        )
        self._fade.raise_()

    # --- seleccion -------------------------------------------------------

    def _on_card_clicked(self, index: int, modifiers) -> None:
        self.clip_clicked.emit(index)
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier))
        if shift and self._anchor is not None:
            lo, hi = sorted((self._anchor, index))
            nueva = set(range(lo, hi + 1))
        elif ctrl:
            nueva = set(self._selected)
            nueva.discard(index) if index in nueva else nueva.add(index)
            self._anchor = index
        else:
            nueva = {index}
            self._anchor = index
        self.set_selected(nueva)

    def set_selected(self, indices: set[int]) -> None:
        self._selected = set(indices)
        self._redraw()
        self.selection_changed.emit(self.selected_indices())

    def selected_indices(self) -> list[int]:
        return sorted(self._selected)

    def set_current(self, index: int) -> None:
        """Solo cambia el borde: NO reconstruye. Reconstruir dentro del
        mousePressEvent de la propia tarjeta terminó en SIGSEGV en macOS."""
        self._current = index
        self._redraw()

    def _redraw(self) -> None:
        multi = len(self._selected) > 1
        for i, card in enumerate(self.item_widgets):
            card.set_visual_state(
                is_current=(i == self._current),
                is_selected=multi and i in self._selected,
            )
