# src/clasificador_video/ui/clip_sheet.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
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
# 140 y no 150: el mockup arma CINCO columnas en la hoja del modo clip, y con
# 150 el ancho util (815 menos margenes y barra de scroll) solo daba para
# cuatro tarjetas de 186 px -- mas gordas y menos densas que las del mockup.
# Medido en la comparacion de cierre de la F2.1.
MIN_TILE_WIDTH = 140
GAP = 9
FADE_HEIGHT = 60

# --- geometria de lo que va encima de la miniatura (del .card del mockup) ---
STRIPE_WIDTH = 3    # franja de cuarto / rayado de sin clasificar
GLYPH_SIZE = 15     # pastilla del glifo de estado y de la palomita
RANGE_HEIGHT = 2    # barra de in/out al pie
BADGE_RADIUS = 3
PAD = 5             # separacion de las pastillas al borde de la tarjeta


@dataclass
class ClipThumbnail:
    # `path` no se dibuja en ningun lado -- el mockup no pone el nombre de
    # archivo en la tarjeta -- pero NO es un campo muerto: es la identidad
    # del clip, y es con lo que los tests comprueban la Regla 1 (que
    # `item_widgets` siga el orden de `self.clips` y no el visual). Esa regla
    # tiene detras un bug real e intermitente de miniaturas aterrizando en la
    # tarjeta equivocada. Si algun dia se va, se va con la regla, no antes.
    path: Path
    room_label: str
    flag: str  # "none" | "pick" | "reject"
    room_color: str | None = None
    numero: int = 0
    in_frame: int | None = None
    out_frame: int | None = None
    duration_frames: int | None = None
    fps: float = 0.0
    aspect_ratio: float = 16 / 9


class _CardOverlay(QWidget):
    """Todo lo que el mockup dibuja ENCIMA de la miniatura, en un solo
    `paintEvent`: numero de clip, duracion, glifo de estado, franja del
    cuarto o rayado de sin clasificar, barra de rango y palomita.

    Por que QPainter y no seis QLabel con QSS:

    - el rayado de "sin clasificar" es un `repeating-linear-gradient` a 135°
      que QSS no sabe expresar;
    - la barra de rango va semitransparente sobre la imagen, y QColor no
      parsea la notacion de color con alfa de CSS (por eso el tema la
      entrega en tuplas);
    - las dos franjas de la izquierda son EXCLUYENTES (o cuarto, o rayado).
      Teniendolas en el mismo paintEvent eso queda garantizado; con dos
      reglas de QSS, la segunda gana en silencio -- verificado en el spike
      de la auditoria del plan, y no da ningun sintoma.
    """

    def __init__(self, parent: ClipCard):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._card = parent

    def paintEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        plan = self._card.plan_de_pintado()
        ancho, alto = self.width(), self.height()
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        self._pintar_franja(pintor, plan["franja"], alto)
        self._pintar_pastilla(pintor, plan["numero"], esquina="arriba-izq")
        if plan["duracion"]:
            self._pintar_pastilla(pintor, plan["duracion"], esquina="abajo-der")
        if plan["glifo"]:
            self._pintar_glifo(pintor, *plan["glifo"])
        if plan["palomita"]:
            self._pintar_palomita(pintor)
        if plan["rango"]:
            self._pintar_rango(pintor, *plan["rango"])
        pintor.end()

    # --- piezas ----------------------------------------------------------

    def _pintar_franja(self, pintor: QPainter, franja: str, alto: int) -> None:
        rect = QRect(0, 0, STRIPE_WIDTH, alto)
        if franja != "rayada":
            pintor.fillRect(rect, QColor(franja))
            return
        pintor.save()
        pintor.setClipRect(rect)
        pintor.fillRect(rect, QColor(theme.LINE))
        lapiz = pintor.pen()
        lapiz.setColor(QColor(theme.UNCLASSIFIED_STRIPE))
        lapiz.setWidth(STRIPE_WIDTH)
        pintor.setPen(lapiz)
        for x in range(-alto, STRIPE_WIDTH + alto, STRIPE_WIDTH * 2):
            pintor.drawLine(x, alto, x + alto, 0)
        pintor.restore()

    def _pintar_pastilla(self, pintor: QPainter, texto: str, esquina: str) -> None:
        pintor.setFont(_fuente_mono())
        metricas = pintor.fontMetrics()
        ancho = metricas.horizontalAdvance(texto) + 8
        alto = metricas.height() + 3
        if esquina == "arriba-izq":
            rect = QRect(PAD + 1, PAD, ancho, alto)
        else:
            rect = QRect(self.width() - ancho - PAD, self.height() - alto - PAD,
                         ancho, alto)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(QColor(*theme.CARD_BADGE_BG_RGBA))
        pintor.drawRoundedRect(rect, BADGE_RADIUS, BADGE_RADIUS)
        pintor.setPen(QColor(theme.CARD_BADGE_TEXT))
        pintor.drawText(rect, Qt.AlignmentFlag.AlignCenter, texto)

    def _pintar_glifo(self, pintor: QPainter, texto: str, fondo: str, tinta: str) -> None:
        rect = QRect(self.width() - GLYPH_SIZE - PAD, PAD, GLYPH_SIZE, GLYPH_SIZE)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(QColor(fondo))
        pintor.drawRoundedRect(rect, theme.RADIUS_SM, theme.RADIUS_SM)
        fuente = _fuente_mono()
        fuente.setBold(True)
        pintor.setFont(fuente)
        pintor.setPen(QColor(tinta))
        pintor.drawText(rect, Qt.AlignmentFlag.AlignCenter, texto)

    def _pintar_palomita(self, pintor: QPainter) -> None:
        rect = QRect(PAD + 1, self.height() - GLYPH_SIZE - PAD - 1,
                     GLYPH_SIZE, GLYPH_SIZE)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(QColor(theme.SELECTION_BORDER))
        pintor.drawRoundedRect(rect, theme.RADIUS_SM, theme.RADIUS_SM)
        fuente = _fuente_mono()
        fuente.setBold(True)
        pintor.setFont(fuente)
        pintor.setPen(QColor(theme.SELECTION_TICK_INK))
        pintor.drawText(rect, Qt.AlignmentFlag.AlignCenter, "✓")

    def _pintar_rango(self, pintor: QPainter, inicio: float, fin: float) -> None:
        y = self.height() - RANGE_HEIGHT
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.fillRect(
            QRect(0, y, self.width(), RANGE_HEIGHT), QColor(*theme.RANGE_TRACK_RGBA)
        )
        izq = round(self.width() * inicio)
        ancho = max(1, round(self.width() * (fin - inicio)))
        pintor.fillRect(QRect(izq, y, ancho, RANGE_HEIGHT), QColor(theme.TRIM_COLOR))


def _fuente_mono() -> QFont:
    """La primera familia de MONO_FONT. QFont no acepta la lista con
    alternativas que si acepta QSS."""
    familia = theme.MONO_FONT.split(",")[0].strip().strip('"')
    return QFont(familia, theme.FONT_MICRO)


class ClipCard(QWidget):
    """Tarjeta de un clip: miniatura con la proporcion REAL del video, y
    encima lo que hace legible su estado de un vistazo.

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

        # se crea DESPUES de la miniatura y se mantiene arriba: es lo que
        # hace que se componga sobre el frame en vez de quedar debajo.
        self._overlay = _CardOverlay(self)

    # --- contenido -------------------------------------------------------

    @property
    def clip(self) -> ClipThumbnail:
        return self._clip

    def texto_duracion(self) -> str:
        """Vacio cuando no se conoce: en una sesion restaurada de disco no se
        volvio a correr ffprobe, y mentir con 0:00 es peor que no decir nada."""
        if not self._clip.duration_frames or not self._clip.fps:
            return ""
        total = round(self._clip.duration_frames / self._clip.fps)
        return f"{total // 60}:{total % 60:02d}"

    def plan_de_pintado(self) -> dict:
        """Que piezas van encima de la miniatura y con que color. Separado
        del paintEvent para poder probarlo sin mirar pixeles -- aunque un
        test si mira uno, porque un plan perfecto y un widget que no dibuja
        nada se ven igual desde aca."""
        clip = self._clip
        glifo = {
            "pick": ("P", theme.PICK_COLOR, theme.PICK_INK),
            "reject": ("X", theme.REJECT_COLOR, theme.REJECT_INK),
        }.get(clip.flag)
        rango = None
        if clip.duration_frames and (clip.in_frame is not None or clip.out_frame is not None):
            total = clip.duration_frames
            inicio = (clip.in_frame or 0) / total
            fin = clip.out_frame / total if clip.out_frame is not None else 1.0
            rango = (max(0.0, min(1.0, inicio)), max(0.0, min(1.0, fin)))
        return {
            "numero": f"{clip.numero:03d}",
            "duracion": self.texto_duracion(),
            "glifo": glifo,
            # excluyentes a proposito: o el color del cuarto, o el rayado
            "franja": clip.room_color or "rayada",
            "rango": rango,
            "palomita": bool(getattr(self, "_is_selected", False)),
        }

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

    def resizeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()

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
        # El BORDE es el canal de estado del clip; la franja del cuarto ya no
        # va aca -- la pinta el overlay, junto con el rayado de sin
        # clasificar, para que las dos sean excluyentes por construccion.
        partes = []
        color_flag = {"pick": theme.PICK_COLOR, "reject": theme.REJECT_COLOR}.get(
            self._clip.flag
        )
        seleccionada = getattr(self, "_is_selected", False)
        if getattr(self, "_is_current", False):
            partes.append(f"border: 2px solid {theme.CURRENT_COLOR};")
        elif seleccionada:
            partes.append(f"border: 2px solid {theme.SELECTION_BORDER};")
        elif color_flag:
            partes.append(f"border: 2px solid {color_flag};")
        else:
            partes.append(f"border: 1px solid {theme.LINE_SOFT};")
        if seleccionada:
            partes.append(f"background-color: {theme.SELECTION_WASH};")
        self.setStyleSheet(
            "#clipCard { " + " ".join(partes) + " } #clipCard QLabel { border: none; }"
        )
        self._overlay.update()  # el estado tambien cambia lo que va encima


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
        # la linea fina que ocupa el ancho sobrante, como en el mockup: sin
        # ella el encabezado flota y no separa un grupo del anterior
        self.line = QWidget()
        self.line.setObjectName("groupLine")
        self.line.setFixedHeight(1)
        self.line.setAttribute(Qt.WA_StyledBackground, True)
        self.hint_label = QLabel("⌘A selecciona el grupo")
        self.hint_label.setObjectName("sheetHint")
        cabecera.addWidget(self.title_label)
        cabecera.addWidget(self.count_label)
        cabecera.addWidget(self.line, stretch=1)
        cabecera.addWidget(self.hint_label)
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
        # el `⌘A` se fue al encabezado de cada grupo, que es a lo que aplica
        self.hint_label = QLabel(
            "pasa el mouse por una miniatura para escrubearla · ⇧+click rango"
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

    def select_current_group(self) -> None:
        """Selecciona todos los clips del grupo del clip actual.

        Es lo que anuncia el encabezado de cada grupo (`⌘A selecciona el
        grupo`). Donde mas rinde es en "Sin clasificar", que es la cola de
        trabajo: seleccionar la racha entera y asignarle un cuarto de una.
        """
        if not 0 <= self._current < len(self.item_widgets):
            return
        grupo = self._group_of(self.item_widgets[self._current].clip)
        self.set_selected({
            i for i, card in enumerate(self.item_widgets)
            if self._group_of(card.clip) == grupo
        })

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
