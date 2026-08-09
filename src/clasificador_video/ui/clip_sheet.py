# src/clasificador_video/ui/clip_sheet.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QRubberBand,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.filters import FilterState
from clasificador_video.ui import theme
from clasificador_video.ui.text import ElidedLabel

SIN_CLASIFICAR = "Sin clasificar"
# 140 y no 150: el mockup arma CINCO columnas en la hoja del modo clip, y con
# 150 el ancho util (815 menos margenes y barra de scroll) solo daba para
# cuatro tarjetas de 186 px -- mas gordas y menos densas que las del mockup.
# Medido en la comparacion de cierre de la F2.1.
MIN_TILE_WIDTH = 140
# Los pasos de `+`/`−`. Son anchos MINIMOS de tarjeta: cuantas columnas caben
# lo sigue decidiendo el viewport, asi que un paso no fija el ancho, fija la
# densidad. El modo clip arranca en el primero --140 da las cinco columnas
# medidas en la F2.1-- y el modo hoja en `PASO_HOJA`, que da las siete del
# mockup a 1600 px.
PASOS_DE_TILE = (140, 170, 210, 260, 320)
# 170 y no 210: medido en la VENTANA real, donde la hoja tiene 1382 px porque
# el rail se queda. Ahi 170 da las siete columnas del mockup y 210 da seis.
# Medirlo sobre una hoja suelta a 1600 px daba otro numero -- el ancho de la
# hoja nunca es el de la ventana.
PASO_HOJA = 1
GAP = 9
FADE_HEIGHT = 60
# Cuanto hay que mover el mouse para que un click pase a ser un arrastre. Sin
# umbral, cada click seleccionaria todo lo que hubiera bajo el cursor y no
# habria forma de elegir un solo clip.
UMBRAL_ARRASTRE = 6

# --- geometria de lo que va encima de la miniatura (del .card del mockup) ---
STRIPE_WIDTH = 3    # franja de cuarto / rayado de sin clasificar
GLYPH_SIZE = 15     # pastilla del glifo de estado y de la palomita
RANGE_HEIGHT = 2    # barra de in/out al pie
HOVER_HEIGHT = 3    # barrita de escrubeo (`.hoverbar` del mockup)
ALTO_PASTILLA = 16  # alto aproximado de las pastillas de numero y duracion
PORTADA = 0.25      # el frame de portada, al 25% del clip
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
        # al escrubear, el timecode REEMPLAZA a la duracion en esa esquina: es
        # el mismo lugar del mockup y dos pastillas encimadas no se leen
        if plan["duracion"] and not plan["hover"]:
            self._pintar_pastilla(pintor, plan["duracion"], esquina="abajo-der")
        if plan["glifo"]:
            self._pintar_glifo(pintor, *plan["glifo"])
        if plan["palomita"]:
            self._pintar_palomita(pintor)
        if plan["rango"]:
            self._pintar_rango(pintor, *plan["rango"])
        if plan["hover"]:
            self._pintar_hover(pintor, plan["hover"])
        if plan["tinte"]:
            pintor.fillRect(self.rect(),
                            QColor(*theme.con_alfa(plan["tinte"], theme.BRUSH_TINT_ALPHA)))
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

    def _pintar_hover(self, pintor: QPainter, hover: dict) -> None:
        """La barrita de escrubeo y su timecode (`.hoverbar`/`.hovertc`).

        Va ARRIBA de la barra de rango, no encima: son dos datos distintos
        --donde estas mirando ahora contra que tramo marcaste-- y encimarlos
        haria que uno tapara al otro justo cuando los dos importan.
        """
        # ARRIBA de la pastilla del timecode, no debajo: si corriera por
        # atras, la pastilla le tapa el tramo final --justo donde estas
        # cuando escrubeas hasta el final-- y la barra deja de decir nada.
        # El mockup la pone a 19 px del borde por lo mismo.
        y = self.height() - RANGE_HEIGHT - HOVER_HEIGHT - ALTO_PASTILLA - PAD
        riel = QRect(PAD, y, self.width() - 2 * PAD, HOVER_HEIGHT)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(QColor(*theme.CARD_BADGE_BG_RGBA))
        pintor.drawRoundedRect(riel, 2, 2)
        avance = QRect(riel.x(), y, round(riel.width() * hover["progreso"]),
                       HOVER_HEIGHT)
        pintor.setBrush(QColor(theme.CARD_BADGE_TEXT))
        pintor.drawRoundedRect(avance, 2, 2)
        # la cabeza, en el color del playhead: es el mismo dato que en el
        # visor --donde estas parado-- y por eso el mismo color
        pintor.setBrush(QColor(theme.CURRENT_COLOR))
        pintor.drawRect(QRect(avance.right() - 1, y - 2, 2, HOVER_HEIGHT + 4))
        if hover["timecode"]:
            self._pintar_pastilla(pintor, hover["timecode"], esquina="abajo-der")

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


class _FilaDeChips(QWidget):
    """Etiqueta del grupo + sus chips, envolviendo a otra linea si no caben.

    El mockup usa `flex-wrap` y por eso los chips bajan de renglon en vez de
    empujar el ancho. En Qt eso seria un `FlowLayout`, que **segfaultea en
    PySide** por la propiedad de los `QLayoutItem` (probado en la F5). Asi
    que se acomoda a mano en `resizeEvent`, la misma tecnica que ya usa la
    hoja para las tarjetas.

    Sin esto, cada chip nuevo empuja el minimo de la hoja y le quita ancho al
    video -- que es justo lo que este rediseño existe para no hacer. Con el
    chip de destacados de la F7 el minimo se fue de 520 a 591 px.
    """

    ESPACIO = 6

    def __init__(self, titulo: str, chips: list[_Chip], parent=None):
        super().__init__(parent)
        self.etiqueta = QLabel(titulo)
        self.etiqueta.setObjectName("filterGroupLabel")
        self.etiqueta.setParent(self)
        self.etiqueta.setFixedWidth(58)
        theme.apply_letter_spacing(self.etiqueta)
        self.chips = chips
        for chip in chips:
            chip.setParent(self)

    def _acomodar(self, ancho: int) -> int:
        """Coloca los chips y devuelve el alto que necesito. Con `ancho`
        chico devuelve mas alto: eso es exactamente lo que se cambia, ancho
        por alto, porque en esta app el alto de la hoja no le cuesta nada al
        video y el ancho si."""
        alto_chip = max((c.sizeHint().height() for c in self.chips), default=0)
        x0 = self.etiqueta.width() + self.ESPACIO
        self.etiqueta.move(0, 0)
        x, y = x0, 0
        for chip in self.chips:
            w = chip.sizeHint().width()
            if x > x0 and x + w > ancho:
                x, y = x0, y + alto_chip + self.ESPACIO
            chip.setGeometry(x, y, w, alto_chip)
            x += w + self.ESPACIO
        return y + alto_chip

    def resizeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        super().resizeEvent(event)
        alto = self._acomodar(self.width())
        if alto != self.height():
            self.setFixedHeight(alto)

    def minimumSizeHint(self):  # noqa: N802 -- override de Qt
        """Lo minimo es la etiqueta mas el chip mas ancho: de ahi para abajo
        no se puede envolver mas."""
        from PySide6.QtCore import QSize
        mas_ancho = max((c.sizeHint().width() for c in self.chips), default=0)
        alto = max((c.sizeHint().height() for c in self.chips), default=0)
        return QSize(self.etiqueta.width() + self.ESPACIO + mas_ancho, alto)


class ClipCard(QWidget):
    """Tarjeta de un clip: miniatura con la proporcion REAL del video, y
    encima lo que hace legible su estado de un vistazo.

    QSS no tiene `aspect-ratio`, asi que el alto se calcula del ancho. Sin
    esto, un clip vertical dentro de una tile apaisada de 150x80 queda de
    45 px de ancho -- que es lo que pasa en el diseño viejo.
    """

    clicked = Signal(object)  # Qt.KeyboardModifier vigente al hacer click
    doble_click = Signal()    # abrir este clip en modo clip (Grid → Loupe)

    def __init__(self, clip: ClipThumbnail, parent=None):
        super().__init__(parent)
        self.setObjectName("clipCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self._clip = clip
        self._frames: list = []
        self._hover: float | None = None   # fraccion escrubeada, o None
        self._tinte: str | None = None     # color del rastro del pincel
        self._scaled_cache: dict[int, object] = {}
        self._poster_index = 0
        self._shown_index: int | None = None
        self._estilo_actual: str | None = None

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
            # misma tinta oscura que el pick: `destacado` es un pick
            # reforzado, no una familia de color nueva
            "destacado": ("★", theme.STAR_COLOR, theme.PICK_INK),
        }.get(clip.flag)
        rango = None
        if clip.duration_frames and (clip.in_frame is not None or clip.out_frame is not None):
            total = clip.duration_frames
            inicio = (clip.in_frame or 0) / total
            fin = clip.out_frame / total if clip.out_frame is not None else 1.0
            inicio = max(0.0, min(1.0, inicio))
            fin = max(0.0, min(1.0, fin))
            # ordenados: marcar `O` y despues `I` mas adelante deja el out
            # ANTES del in, y sin esto salia un rango invertido que se pintaba
            # como una astilla de 1 px. La ScrubBar ya lo resuelve con min/max
            # y las dos vistas del mismo dato tienen que coincidir.
            rango = (min(inicio, fin), max(inicio, fin))
        return {
            "numero": f"{clip.numero:03d}",
            "duracion": self.texto_duracion(),
            "glifo": glifo,
            # excluyentes a proposito: o el color del cuarto, o el rayado
            "franja": clip.room_color or "rayada",
            "rango": rango,
            "palomita": bool(getattr(self, "_is_selected", False)),
            # lo que el mockup dibuja al escrubear: barrita de progreso y
            # timecode. Va en el mismo plan --y en el mismo paintEvent-- que
            # el resto: seis QLabel encima de la miniatura es lo que la F2
            # hizo mal.
            # el rastro de la pincelada: un lavado del color del cuarto sobre
            # la miniatura. Es del GESTO, no del clip -- se va al soltar.
            "tinte": self._tinte,
            "hover": None if self._hover is None else {
                "progreso": self._hover,
                "timecode": self._timecode_de(self._hover),
            },
        }

    def _timecode_de(self, fraccion: float) -> str:
        clip = self._clip
        if not clip.duration_frames or not clip.fps:
            return ""
        from clasificador_video.ui.video_widget import format_timecode

        return format_timecode(round(clip.duration_frames * fraccion), clip.fps)

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
        # 25% y no el del medio: en un recorrido el primer frame suele ser una
        # puerta o movimiento borroso, y el del medio puede ser cualquier cosa.
        # Es el MISMO punto donde el video arranca al abrirlo (F6), asi que la
        # miniatura muestra lo que vas a ver.
        self._poster_index = round((len(pixmaps) - 1) * PORTADA)
        self._shown_index = None
        self._show_frame(self._poster_index)

    def has_pixmap(self) -> bool:
        return bool(self._frames)

    # --- geometria -------------------------------------------------------

    def apply_width(self, ancho: int) -> None:
        alto = max(1, round(ancho / max(self._clip.aspect_ratio, 0.01)))
        # Sale temprano si el tamaño no cambio. Re-colocar la grilla llama a
        # esto en las 128 tarjetas, y sin la guarda cada una tiraba su cache y
        # volvia a escalar su miniatura: medido con cProfile, el 40% del costo
        # de una tecla de cuarto se iba en reescalar imagenes identicas.
        if (ancho, alto) == (self.width(), self.height()) and self._scaled_cache:
            return
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

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Grid → Loupe, el gesto de Lightroom. No colisiona con nada: `⏎`
        sigue siendo la paleta de cuartos."""
        self.doble_click.emit()

    def escrubear_a(self, fraccion: float) -> None:
        """Muestra el frame que corresponde a esa fraccion del clip, y prende
        la barrita de progreso del mockup.

        Separado del evento de mouse para poder probarlo sin simular un
        arrastre: el gesto se prueba aparte, esto se prueba por su efecto.
        """
        if len(self._frames) <= 1:
            return
        self._hover = max(0.0, min(1.0, fraccion))
        self._show_frame(round(self._hover * (len(self._frames) - 1)))
        self._overlay.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self.escrubear_a(event.position().x() / max(self.width(), 1))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        # vuelve a la portada: si cada tarjeta se quedara en el frame por el
        # que pasaste, la hoja terminaria siendo un mosaico de frames al azar
        self._hover = None
        if self._frames:
            self._show_frame(self._poster_index)
        self._overlay.update()
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
        hoja = (
            "#clipCard { " + " ".join(partes) + " } #clipCard QLabel { border: none; }"
        )
        # `setStyleSheet` es carisimo: vuelve a parsear la hoja y repolish el
        # widget. Con 128 clips, UNA tecla de cuarto lo llamaba 768 veces --las
        # 128 tarjetas, seis veces cada una, cambiaran o no-- y se llevaba el
        # 84% del tiempo de la tecla mas frecuente de la app. Medido con
        # cProfile el 2026-08-08.
        if hoja != self._estilo_actual:
            self._estilo_actual = hoja
            self.setStyleSheet(hoja)
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


class _Chip(QPushButton):
    """Un filtro. Chequeable y con su conteo al lado, como el `.fchip` del
    mockup.

    Los chips de un grupo van en un `QButtonGroup` exclusivo. Volver a
    clickear el que esta prendido **no lo apaga** --verificado contra Qt--, y
    por eso cada grupo tiene su chip `Todos`: es la unica forma de quitar el
    filtro, y no hay manera de quedarse sin ninguno prendido.
    """

    def __init__(self, clave: str, etiqueta: str, parent=None):
        super().__init__(parent)
        self.setObjectName("filterChip")
        self.clave = clave
        self._etiqueta = etiqueta
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.set_count(None)

    def set_count(self, cuantos: int | None) -> None:
        if cuantos is None:
            self.setText(self._etiqueta)
        elif self.clave == "ocultar_rejects":
            # cuantos SE VAN, no cuantos quedan: el mockup dice "−9"
            self.setText(f"{self._etiqueta}  −{cuantos}")
        else:
            self.setText(f"{self._etiqueta}  {cuantos}")


class _BarraDeSeleccion(QWidget):
    """El `.batch` del mockup: cuantos clips llevas y que puedes hacerles.

    Aparece SOLO con mas de uno: con un clip seleccionado no hay nada que
    decir, es el flujo normal. Y solo nombra teclas que existen -- una barra
    que promete `⇧P` cuando `⇧P` no hace nada es peor que no ponerla.
    """

    ATAJOS = (
        ("asignar", "1 – 9"),
        ("buscar cuarto", "⏎"),
        ("marcar", "P  X  ⇧P"),
        ("deshacer", "⌘Z"),
        ("salir", "esc"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("batchBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(11)
        self.label = QLabel("")
        self.label.setObjectName("batchCount")
        layout.addWidget(self.label)
        layout.addStretch(1)
        self._hints = []
        for que, teclas in self.ATAJOS:
            hint = QLabel(f"{que}  {teclas}")
            hint.setObjectName("batchHint")
            layout.addWidget(hint)
            self._hints.append(hint)
        self.hide()

    def hints_text(self) -> str:
        return "  ".join(h.text() for h in self._hints)

    def set_count(self, cuantos: int) -> None:
        if cuantos <= 1:
            self.hide()
            return
        self.label.setText(f"{cuantos} clips seleccionados")
        self.show()
        self.raise_()


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
    clip_activated = Signal(int)       # doble click: abrir en modo clip
    brocha_paso_por = Signal(int)      # el arrastre paso por esta tarjeta
    selection_changed = Signal(list)
    filters_changed = Signal(object)   # FilterState

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("clipSheet")
        self.item_widgets: list[ClipCard] = []
        # Tamaño de miniatura: es una preferencia de VISTA, asi que vive aqui
        # y no en `set_clips` -- ahi se reiniciaria con cada shooting que
        # abras, justo despues de que lo hayas ajustado.
        # Un paso por MODO: en la hoja a pantalla completa estas mirando de
        # mas lejos y con mas ancho, asi que la densidad util es otra. Que
        # `+`/`−` se recuerden por separado evita tener que reajustar en cada
        # cruce.
        self._modo_hoja = False
        self._pasos = {False: 0, True: PASO_HOJA}
        self._congelado = False
        self._pincel_activo = False
        self._blocks: dict[str, _GroupBlock] = {}
        self._current = -1
        self._selected: set[int] = set()
        self._anchor: int | None = None
        # None = no hay filtro. Un `set` vacio es distinto: filtro que no deja
        # pasar nada, y la hoja tiene que verse vacia de verdad.
        self._visible: set[int] | None = None
        # ultimo acomodo hecho, para no repetirlo cuando nada cambio
        self._firma: tuple | None = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        encabezado = QWidget()
        encabezado.setObjectName("sheetHeader")
        el = QVBoxLayout(encabezado)
        el.setContentsMargins(13, 9, 13, 9)
        el.setSpacing(7)

        # --- primera fila: titulo, busqueda y hint ---
        fila_arriba = QHBoxLayout()
        fila_arriba.setSpacing(9)
        self.title_label = QLabel("CLIPS · 0")
        self.title_label.setObjectName("railHeader")
        theme.apply_letter_spacing(self.title_label)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("sheetSearch")
        self.search_input.setPlaceholderText("Buscar clip o cuarto…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(26)
        # 230 fijo, el maximo del mockup. Con `stretch` competia con el
        # espaciador por el sobrante y se quedaba en 120 px, donde no cabe
        # ni el placeholder.
        self.search_input.setFixedWidth(230)
        # Solo toma el foco al hacerle click. Siendo el primer widget que lo
        # acepta, se lo quedaba SOLO al abrir la app -- y como las teclas de
        # una letra ceden el paso mientras escribes (MainWindow), eso dejaba
        # muertas P, X, I, O, L, K y los digitos hasta que clickearas en otro
        # lado. Mismo criterio que el `NoFocus` de los botones, que existe
        # para que el espacio reproduzca en vez de activar un boton.
        self.search_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.search_input.textChanged.connect(self._on_filters_changed)
        # el `⌘A` se fue al encabezado de cada grupo, que es a lo que aplica.
        # Va elidido y con minimo cero: es decorativo, y su ancho completo
        # --310 px-- era lo que mas exigia del encabezado. Ese minimo se le
        # resta al video, que es lo que este rediseño existe para agrandar.
        self.hint_label = ElidedLabel(
            "pasa el mouse por una miniatura para escrubearla · ⇧+click rango"
        )
        self.hint_label.setObjectName("sheetHint")
        self.hint_label.setMinimumWidth(0)
        self.hint_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        # El chip de cola va en ESTA fila y no junto a los filtros, donde lo
        # pone el mockup: con los siete chips, sus dos etiquetas de grupo y el
        # chip, la fila de filtros pide 856 px y la hoja en modo clip mide
        # 815. Se salia por 67 px y aparecia scroll horizontal. Aca sobra
        # lugar, el dato se sigue viendo, y no hubo que achicar la tipografia.
        self.queue_chip = QLabel("")
        self.queue_chip.setObjectName("queueChip")
        self.queue_chip.hide()
        fila_arriba.addWidget(self.title_label)
        fila_arriba.addWidget(self.search_input)
        fila_arriba.addWidget(self.queue_chip)
        fila_arriba.addStretch(1)
        fila_arriba.addWidget(self.hint_label)
        el.addLayout(fila_arriba)

        # --- los filtros, que son la cola de navegacion ---
        for fila_filtros in self._construir_filtros():
            el.addWidget(fila_filtros)
        raiz.addWidget(encabezado)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(13, 0, 13, 10)
        self._content_layout.setSpacing(14)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._content)
        self._scroll.viewport().installEventFilter(self)

        # flota sobre la hoja, pegada abajo: no le quita alto a las tarjetas
        # y aparece justo donde estas mirando cuando seleccionas
        self.batch_bar = _BarraDeSeleccion(self)

        # marquesina: el rectangulo de seleccion. `QRubberBand` lo dibuja el
        # estilo del sistema, que es lo que el usuario ya reconoce de Finder.
        self.marquesina = QRubberBand(QRubberBand.Shape.Rectangle,
                                      self._scroll.viewport())
        self._origen_marquesina = None
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        # `Ignored` en horizontal: las tarjetas usan `setFixedSize`, asi que el
        # minimo de la grilla crece con ellas y --a traves del area de scroll--
        # se volvia el minimo de la ventana entera. Resultado: un trinquete.
        # La ventana podia crecer y nunca encoger, y la hoja se llevaba 49 px
        # que le tocaban al video. El ancho de la hoja lo decide el padre: es
        # la que absorbe lo que sobra, no la que lo reclama.
        self._scroll.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding
        )
        raiz.addWidget(self._scroll, stretch=1)

        # QSS no tiene `mask-image`: el desvanecido al pie se hace con un
        # widget de degradado encima, transparente al mouse.
        self._fade = QLabel("", self._scroll)
        self._fade.setObjectName("sheetFade")
        self._fade.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    # --- filtros ---------------------------------------------------------

    def _construir_filtros(self) -> list["_FilaDeChips"]:
        """Los dos grupos del mockup, **uno por renglon**.

        El mockup los pone en una sola fila con `flex-wrap: wrap`. En Qt esa
        fila EXIGE su ancho completo: con los conteos reales pedia 838 px
        contra los 789 que tiene la hoja en modo clip, y ese minimo se
        propagaba hasta la ventana -- que crecia a 1649 px y ya no podia
        encoger. Un trinquete que le robaba ancho al video, que es justo lo
        que este rediseño existe para proteger.

        Dos renglones lo resuelven sin layouts a medida y con holgura de
        sobra para el chip de destacados que agrega la F7. El costo es alto
        del encabezado, y el alto de la hoja no le cuesta nada al video: la
        hoja es una columna.

        No se construyen los iconos de vista: no hay ninguna decision detras
        de ellos. Cada grupo envuelve a otra linea si no cabe (ver
        `_FilaDeChips`).
        """
        filas: list[_FilaDeChips] = []
        self.chips: dict[str, _Chip] = {}

        for titulo, opciones in (
            ("MOSTRAR", [
                ("todos", "Todos"),
                ("sin_clasificar", "Sin clasificar"),
                ("clasificados", "Clasificados"),
            ]),
            ("ESTADO", [
                ("todos_estado", "Todos"),
                ("solo_picks", "Solo picks"),
                ("solo_destacados", "★ Solo destacados"),
                ("ocultar_rejects", "Ocultar rejects"),
                ("sin_marcar", "Sin marcar"),
            ]),
        ):
            botones = QButtonGroup(self)
            botones.setExclusive(True)
            del_grupo = []
            for clave, texto in opciones:
                chip = _Chip(clave, texto)
                chip.clicked.connect(self._on_filters_changed)
                botones.addButton(chip)
                self.chips[clave] = chip
                del_grupo.append(chip)
            filas.append(_FilaDeChips(titulo, del_grupo))

        self.chips["todos"].setChecked(True)
        self.chips["todos_estado"].setChecked(True)
        return filas

    def filter_state(self) -> FilterState:
        mostrar = next(
            (c.clave for c in self.chips.values()
             if c.isChecked() and c.clave in ("sin_clasificar", "clasificados")),
            "todos",
        )
        estado = next(
            (c.clave for c in self.chips.values()
             if c.isChecked() and c.clave in ("solo_picks", "solo_destacados",
                                              "ocultar_rejects", "sin_marcar")),
            "todos",
        )
        return FilterState(mostrar=mostrar, estado=estado,
                           busqueda=self.search_input.text())

    def _on_filters_changed(self) -> None:
        self._marcar_chips_de_cola()
        self.filters_changed.emit(self.filter_state())

    def _marcar_chips_de_cola(self) -> None:
        """El chip activo que SI filtra se tiñe de ámbar, como en el mockup.

        No es decoración: el ámbar es el color de la cola en toda la app --el
        chip `cola de ←→`, el playhead, el clip actual-- y verlo en el chip es
        lo que dice «por aquí se mueven las flechas ahora».
        """
        for chip in self.chips.values():
            define_cola = chip.isChecked() and chip.clave not in ("todos", "todos_estado")
            if chip.property("q") != define_cola:
                chip.setProperty("q", define_cola)
                chip.style().unpolish(chip)
                chip.style().polish(chip)

    def set_counts(self, conteos: dict[str, int]) -> None:
        self.chips["todos"].set_count(conteos.get("todos"))
        for clave in ("sin_clasificar", "clasificados", "solo_picks",
                      "solo_destacados",
                      "ocultar_rejects", "sin_marcar"):
            self.chips[clave].set_count(conteos.get(clave))

    def set_queue_size(self, cuantos: int, filtrando: bool) -> None:
        """Sin filtro las flechas recorren todo y el chip mentiria."""
        self.queue_chip.setVisible(filtrando)
        if filtrando:
            self.queue_chip.setText(f"cola de ←→ · {cuantos} clips")

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
            card.doble_click.connect(lambda i=index: self.clip_activated.emit(i))
            self.item_widgets.append(card)
        self._current = -1
        self._anchor = None
        # el filtro guarda INDICES: con otra lista de clips apuntarian a
        # cualquier cosa. Quien filtre vuelve a llamar a set_visible_indices.
        self._visible = None
        # las tarjetas son OTRAS: la firma anterior no dice nada de estas
        self._firma = None
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

    def set_visible_indices(self, indices) -> None:
        """Filtra la hoja **sin tocar `item_widgets`**.

        La lista va indexada por indice de clip y las miniaturas llegan de
        tres hilos en desorden: reordenarla o rearmarla las haria aterrizar en
        la tarjeta equivocada, y de forma intermitente (Regla 1 de la clase).
        Aca solo se esconde y se vuelve a colocar.

        `None` quita el filtro; un conjunto vacio deja la hoja vacia.
        """
        self._visible = None if indices is None else set(indices)
        for i, card in enumerate(self.item_widgets):
            card.setVisible(self._es_visible(i))
        # esconder NO alcanza: el QGridLayout deja el hueco donde estaba la
        # tarjeta. Verificado contra Qt -- hay que re-colocar salteandolas.
        self._regroup()

    def _es_visible(self, indice: int) -> bool:
        return self._visible is None or indice in self._visible

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

    @property
    def _paso(self) -> int:
        return self._pasos[self._modo_hoja]

    def set_modo_hoja(self, activo: bool) -> None:
        """La hoja a pantalla completa arranca con tarjetas mas grandes: son
        las siete columnas del mockup a 1600 px, contra las cinco del modo
        clip."""
        if activo == self._modo_hoja:
            return
        self._modo_hoja = activo
        self._relayout()

    def _ancho_de_tile(self) -> int:
        """El ancho MINIMO de una tarjeta segun el paso de zoom vigente."""
        return PASOS_DE_TILE[self._paso]

    def agrandar(self) -> None:
        self._set_paso(self._paso + 1)

    def achicar(self) -> None:
        self._set_paso(self._paso - 1)

    def _set_paso(self, paso: int) -> None:
        """Con tope por los dos lados: sin el, `−` repetido deja tarjetas de
        3 px y `+` una sola tarjeta por pantalla. Los dos son inservibles."""
        nuevo = max(0, min(paso, len(PASOS_DE_TILE) - 1))
        if nuevo == self._paso:
            return
        self._pasos[self._modo_hoja] = nuevo
        self._relayout()

    def _ancho_disponible(self) -> int:
        """El ancho REAL para las tarjetas: el viewport del area de scroll.

        No sirve `_content.width()`: su minimo lo fijan las propias tarjetas,
        asi que cuando la hoja se angosta --pasa con un clip horizontal, que
        le da mas ancho al video-- el contenido se queda con el ancho de antes
        y aca se volvian a calcular las mismas columnas. La ultima quedaba
        cortada, y como el scroll horizontal esta apagado, ni siquiera se
        podia llegar a ella.
        """
        return self._scroll.viewport().width() or self._content.width() or self.width()

    def _firma_de_acomodo(self) -> tuple:
        """Todo lo que decide DONDE y de que tamaño va cada tarjeta.

        Si no cambio nada de esto, re-colocar da exactamente el mismo
        resultado y es trabajo tirado.
        """
        return (
            self._ancho_disponible(),
            self._paso,
            self._modo_hoja,
            tuple(
                (self._group_of(card.clip), self._es_visible(i), card.clip.aspect_ratio)
                for i, card in enumerate(self.item_widgets)
            ),
        )

    def set_pincel_activo(self, activo: bool) -> None:
        """Con el pincel cargado la marquesina se cancela: los dos son el
        mismo arrastre y no pueden correr juntos."""
        if activo:
            self.terminar_marquesina()

        # Con el pincel activo el viewport sigue el mouse aunque no haya boton
        # apretado: mantener la tecla YA es el gesto, y pedir ademas apretar el
        # boton seria un dedo mas para lo mismo.
        self._pincel_activo = bool(activo)
        self._scroll.viewport().setMouseTracking(activo)

    def eventFilter(self, obj, event):  # noqa: N802 -- override de Qt
        if obj is self._scroll.viewport():
            tipo = event.type()
            if self._pincel_activo:
                if tipo == QEvent.Type.MouseMove:
                    self.notificar_arrastre(event.position().toPoint())
            elif tipo == QEvent.Type.MouseButtonPress:
                self.empezar_marquesina(event.position().toPoint())
            elif tipo == QEvent.Type.MouseMove:
                self.mover_marquesina(event.position().toPoint())
            elif tipo == QEvent.Type.MouseButtonRelease:
                self.terminar_marquesina()
        return super().eventFilter(obj, event)

    # --- marquesina de seleccion -----------------------------------------

    def empezar_marquesina(self, pos_en_viewport) -> None:
        """Arrastrar SIN tecla de cuarto selecciona. Los dos gestos son el
        mismo arrastre, y por eso este cede cuando el pincel esta cargado:
        pintar y seleccionar a la vez no tendria sentido."""
        if self._pincel_activo:
            return
        self._origen_marquesina = pos_en_viewport

    def mover_marquesina(self, pos_en_viewport) -> None:
        if self._origen_marquesina is None:
            return
        # `normalized()`: arrastrando hacia arriba-izquierda el rectangulo
        # queda de ancho negativo y no intersecta con nada. Es el mismo bug
        # del rango invertido de la tarjeta y de la barra de reproduccion.
        rect = QRect(self._origen_marquesina, pos_en_viewport).normalized()
        if rect.width() < UMBRAL_ARRASTRE and rect.height() < UMBRAL_ARRASTRE:
            return          # todavia es un click, no un arrastre
        self.marquesina.setGeometry(rect)
        self.marquesina.show()
        # la seleccion se ve MIENTRAS arrastras: si apareciera al soltar,
        # estarias arrastrando a ciegas
        self.set_selected(set(self.indices_tocados_por(rect)))

    def terminar_marquesina(self) -> None:
        self._origen_marquesina = None
        self.marquesina.hide()

    def indices_tocados_por(self, rect: QRect) -> list[int]:
        """Los clips VISIBLES cuyas tarjetas toca el rectangulo.

        Las escondidas por el filtro no entran: seleccionar algo que no ves y
        despues asignarle un cuarto en lote es el error mas caro de la app.
        """
        viewport = self._scroll.viewport()
        tocados = []
        for indice, card in enumerate(self.item_widgets):
            if card.isHidden() or not self._es_visible(indice):
                continue
            esquina = card.mapTo(viewport, card.rect().topLeft())
            if rect.intersects(QRect(esquina, card.size())):
                tocados.append(indice)
        return tocados

    def notificar_arrastre(self, pos_en_viewport) -> None:
        """Avisa por que tarjeta paso el cursor. No sabe de cuartos ni de
        historial: eso es de la ventana, que es quien conoce los clips.

        `childAt` va sobre el CONTENIDO --que es lo que se desplaza-- con el
        scroll sumado. Sobre el viewport, con la hoja desplazada, devuelve la
        tarjeta equivocada; medido en el spike de la Task 14.
        """
        punto = pos_en_viewport + QPoint(
            self._scroll.horizontalScrollBar().value(),
            self._scroll.verticalScrollBar().value(),
        )
        hijo = self._content.childAt(punto)
        # el hijo directo suele ser la etiqueta de la imagen o el overlay: se
        # sube hasta dar con la tarjeta
        while hijo is not None and not isinstance(hijo, ClipCard):
            hijo = hijo.parentWidget()
        if hijo is not None and hijo in self.item_widgets:
            self.brocha_paso_por.emit(self.item_widgets.index(hijo))

    def limpiar_tinte(self) -> None:
        """Borra el rastro de la pincelada. Se llama al soltar: el tinte es
        del gesto, no del clip, y dejarlo haria que las pintadas se vieran
        distintas de las demas de su mismo cuarto para siempre."""
        for card in self.item_widgets:
            if card._tinte is not None:
                card._tinte = None
                card._overlay.update()

    def congelar_acomodo(self, congelado: bool) -> None:
        """Mientras dura una pincelada, la grilla NO se re-acomoda.

        Medido en el spike de la Task 14: reagrupando durante el arrastre, la
        tarjeta bajo el cursor cambia y terminas pintando sobre otra cosa. Al
        soltar se descongela y se re-acomoda una sola vez, que cuesta ~20 ms.
        """
        self._congelado = bool(congelado)

    def repintar_uno(self, indice: int, cuarto: str, cuartos: list[str]) -> None:
        """Refresca UNA tarjeta sin tocar la grilla.

        Recibe el cuarto NUEVO: la tarjeta guarda su propia copia del dato
        (`ClipThumbnail`), y leerla aqui devolveria el cuarto viejo -- que es
        justo lo que se esta cambiando.

        `_refresh_sheet` completo re-acomoda, que es lo que no puede pasar
        mientras pintas.
        """
        if not (0 <= indice < len(self.item_widgets)):
            return
        card = self.item_widgets[indice]
        card.clip.room_label = cuarto
        color = theme.room_color(cuartos.index(cuarto)) if cuarto in cuartos else None
        card.clip.room_color = color
        card._tinte = color
        card._overlay.update()

    def _relayout(self) -> None:
        """Punto de entrada barato: si nada cambio, no hace nada.

        Con 128 clips, re-colocar cuesta ~12 ms. Una tecla de cuarto disparaba
        CUATRO re-colocados —dos dentro del refresco de la hoja y dos mas por
        el avance automatico de la F5—, y esta app existe para ser rapida.
        """
        if self._congelado:
            return
        firma = self._firma_de_acomodo()
        if firma == self._firma:
            return
        self._firma = firma
        self._acomodar_de_verdad()

    def _acomodar_de_verdad(self) -> None:
        ancho_util = self._ancho_util()
        columnas = self.columnas_visibles()
        ancho_tile = max(1, (ancho_util - GAP * (columnas - 1)) // columnas)

        # solo lo visible: las escondidas por el filtro no entran a la grilla,
        # porque esconderlas sin sacarlas deja el hueco donde estaban
        por_grupo: dict[str, list[ClipCard]] = {}
        for indice, card in enumerate(self.item_widgets):
            if self._es_visible(indice):
                por_grupo.setdefault(self._group_of(card.clip), []).append(card)

        for titulo, block in self._blocks.items():
            while block.grid.count():
                block.grid.takeAt(0)
            tarjetas = por_grupo.get(titulo, [])
            block.set_count(len(tarjetas))
            # un grupo del que el filtro no dejo pasar nada no tiene por que
            # ocupar su encabezado y su linea
            block.setVisible(bool(tarjetas))
            for posicion, card in enumerate(tarjetas):
                fila, columna = divmod(posicion, columnas)
                card.apply_width(ancho_tile)
                # addWidget sobre un widget que ya existe solo lo reubica:
                # no lo destruye ni le borra la miniatura ya cargada
                block.grid.addWidget(card, fila, columna)

    def _ancho_util(self) -> int:
        """El ancho para tarjetas, ya descontados los margenes del contenido."""
        return max(self._ancho_disponible(), MIN_TILE_WIDTH) - 26

    def columnas_visibles(self) -> int:
        """Cuantas columnas arma la grilla con el ancho de ahora.

        **Es la MISMA cuenta que usa `_acomodar_de_verdad`**, no una copia: al
        construir el zoom estuvieron un rato separadas y el resultado fue que
        este metodo reportaba 6 columnas mientras la grilla seguia armando 8.
        Dos vistas del mismo dato se contradicen solas -- van cuatro veces en
        este proyecto.
        """
        return max(1, (self._ancho_util() + GAP) // (self._ancho_de_tile() + GAP))

    def orden_visual(self) -> list[int]:
        """Los numeros de clip en el orden en que se ven.

        Ojo: NO es el orden de `item_widgets`, que va por indice de clip. Este
        sirve para probar que una pincelada no reacomoda la hoja bajo el
        cursor mientras pintas.
        """
        numeros = []
        for block in self._blocks.values():
            if block.isHidden():
                continue
            for posicion in range(block.grid.count()):
                item = block.grid.itemAt(posicion)
                if item is not None and item.widget() is not None:
                    numeros.append(item.widget()._clip.numero)
        return numeros

    def current_index(self) -> int:
        """El clip actual segun la hoja. La hoja LEE este dato, no guarda una
        segunda copia: dos vistas del mismo estado se contradicen solas."""
        return self._current

    def _colocar_barra_de_seleccion(self) -> None:
        if self.batch_bar.isHidden():
            return
        self.batch_bar.adjustSize()
        margen = 13
        self.batch_bar.setGeometry(
            margen, self.height() - self.batch_bar.height() - 12,
            max(1, self.width() - 2 * margen), self.batch_bar.height(),
        )
        self.batch_bar.raise_()

    def resizeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        super().resizeEvent(event)
        self._relayout()
        self._colocar_barra_de_seleccion()
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
        # solo lo VISIBLE: con un filtro puesto, meter en la seleccion clips
        # que no estas viendo termina en asignarles un cuarto sin querer
        self.set_selected({
            i for i, card in enumerate(self.item_widgets)
            if self._group_of(card.clip) == grupo and self._es_visible(i)
        })

    def set_selected(self, indices: set[int]) -> None:
        self._selected = set(indices)
        self.batch_bar.set_count(len(self._selected))
        self._colocar_barra_de_seleccion()
        self._redraw()
        self.selection_changed.emit(self.selected_indices())

    def selected_indices(self) -> list[int]:
        return sorted(self._selected)

    def centrar_en(self, index: int) -> None:
        """Deja la tarjeta del clip `index` a la vista, centrada.

        `DECISIONES.md` lo pide para el cruce con `⇥`: los dos modos
        comparten el clip actual, asi que entrar a la hoja mirando otra
        parte del shooting es perder el hilo. Con 128 clips y el actual en
        el 87, la hoja se abria en el 117.
        """
        if not (0 <= index < len(self.item_widgets)):
            return
        tarjeta = self.item_widgets[index]
        # el margen vertical es medio viewport: `ensureWidgetVisible` con
        # margen chico solo la asoma por el borde, y lo que se pidio es que
        # quede centrada.
        self._scroll.ensureWidgetVisible(
            tarjeta, 0, max(0, (self._scroll.viewport().height() - tarjeta.height()) // 2)
        )

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
