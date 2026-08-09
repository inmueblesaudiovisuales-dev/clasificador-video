# src/clasificador_video/ui/clip_sheet.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QRubberBand,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
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
# La marca de camara del encabezado de bin. Un solo glifo para todos: ver
# el comentario en `_BinHeader.__init__`. Vive en el tema porque el visor
# usa la misma.
MARCA_DE_BIN = theme.MARCA_DE_BIN
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
    # De que bin salio el clip. Vacio significa «todavia no hay bins»: una
    # hoja suelta en un test, o el instante entre cargar los clips y
    # refrescar los bins. La hoja lo trata como un bin sin nombre y no
    # revienta.
    bin_nombre: str = ""


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
        # el ultimo, encima de todo: es lo que hay que ver aunque la
        # miniatura sea clara y el tinte del pincel este puesto
        if plan["borde"]:
            self._pintar_borde(pintor, plan["borde"], ancho, alto)
        pintor.end()

    # --- piezas ----------------------------------------------------------

    def _pintar_borde(self, pintor: QPainter, color: str, ancho: int, alto: int) -> None:
        lapiz = QPen(QColor(color))
        lapiz.setWidth(theme.CARD_STATE_BORDER)
        # el trazo se centra en la linea, asi que sin el medio pixel de
        # adentro la mitad del borde cae fuera del widget y se ve la mitad
        # de grueso
        pintor.setPen(lapiz)
        pintor.setBrush(Qt.BrushStyle.NoBrush)
        mitad = theme.CARD_STATE_BORDER / 2
        pintor.drawRect(QRectF(mitad, mitad, ancho - theme.CARD_STATE_BORDER, alto - theme.CARD_STATE_BORDER))


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


# Cuanto texto de un nombre de bin entra en su chip. El chip mas ancho de una
# fila ES su ancho minimo, y ese minimo se propaga hasta la ventana: un bin
# llamado «01. VIDEO CARD A SONY FX30» --que es como se llaman las carpetas de
# verdad-- le robaria ancho al video, que es lo que el rediseño existe para
# proteger. El nombre completo se sigue leyendo en el encabezado del bin.
LARGO_DE_CHIP_DE_BIN = 18


def _etiqueta_de_chip(nombre: str) -> str:
    if len(nombre) <= LARGO_DE_CHIP_DE_BIN:
        return nombre
    return nombre[:LARGO_DE_CHIP_DE_BIN - 1] + "…"


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

    def set_chips(self, chips: list[_Chip]) -> None:
        """Cambia los chips de la fila. Solo la de bins la usa: sus chips
        son los bins que hay, y esos aparecen y desaparecen con cada
        importacion.

        Los que salen se ESCONDEN, no se destruyen. Destruir widgets que
        estan colgados de la hoja mientras Qt puede estar repoliendola es
        justo la familia de segfaults que ya costo dos arreglos en este
        archivo (el QMenu del encabezado y la sombra del encabezado
        pegado). Quien llama reusa los mismos objetos.
        """
        for viejo in self.chips:
            if viejo not in chips:
                viejo.hide()
        self.chips = chips
        for chip in chips:
            chip.setParent(self)
            chip.show()
        self.setFixedHeight(self._acomodar(self.width()))
        self.updateGeometry()

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
        # El BORDE es el canal de estado del clip, y se pinta ACA -- no con
        # QSS. La regla de QSS existia desde la F5 y nunca llego al pixel: la
        # miniatura ocupa toda la tarjeta y tapa el borde del padre. Bruno lo
        # reporto como «no se marca en cual clip estoy».
        #
        # El orden es el de la atencion: donde estas parado gana sobre lo que
        # tienes seleccionado, y eso sobre el estado del clip.
        if getattr(self, "_is_current", False):
            borde = theme.CURRENT_COLOR
        elif getattr(self, "_is_selected", False):
            borde = theme.SELECTION_BORDER
        else:
            borde = {"pick": theme.PICK_COLOR,
                     "reject": theme.REJECT_COLOR,
                     "destacado": theme.STAR_COLOR}.get(clip.flag)
        return {
            "borde": borde,
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


class _BinHeader(QWidget):
    """El encabezado de un bin: lo que el mockup pone arriba de sus grupos.

    Es tambien el menu de clic derecho -- ahi vive todo lo que aplica a una
    camara entera (enlazar proxies, renombrar, quitar del proyecto). El bin
    es la unidad con la que se piensan esas tres cosas, porque el proxy y el
    LUT son propiedades de la CAMARA y no del clip suelto.
    """

    collapse_toggled = Signal(str)        # nombre del bin
    rename_requested = Signal(str, str)   # nombre viejo, nombre nuevo
    proxies_requested = Signal(str)
    proxies_cleared = Signal(str)
    select_all_requested = Signal(str)
    remove_requested = Signal(str)

    # los mismos tres canales de estado de la tarjeta, en el mismo orden que
    # el mockup: pick, destacado, reject
    MARCAS = (("pick", theme.PICK_COLOR), ("destacado", theme.STAR_COLOR),
              ("reject", theme.REJECT_COLOR))

    def __init__(self, nombre: str, parent=None):
        super().__init__(parent)
        self.nombre = nombre
        self.setObjectName("binHeader")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._colapsado = False
        self._cuantos = 0
        self._renombrando = False
        # el menu se guarda como atributo porque `popup()` NO bloquea: si el
        # QMenu fuera local, Python lo recolectaria antes de que se dibuje.
        # `exec()` si bloquearia, y esta app no abre nada modal desde la F3.
        self._menu: QMenu | None = None

        fila = QHBoxLayout(self)
        fila.setContentsMargins(9, 9, 9, 9)
        fila.setSpacing(9)
        self.chevron = QLabel("▾")
        self.chevron.setObjectName("binChevron")
        # La marca de camara del mockup. Un SOLO glifo para todos los bins:
        # el mockup ponia `▲` al dron y `■` a la Sony porque sabia que era
        # cada uno, y la app no lo sabe -- lee una carpeta, no un modelo de
        # camara. Lo que distingue un bin de otro es el COLOR, que se pone
        # con `set_posicion`.
        self.cam_mark = QLabel(MARCA_DE_BIN)
        self.cam_mark.setObjectName("binCam")
        self.cam_mark.setAttribute(Qt.WA_StyledBackground, True)
        self.cam_mark.setFixedSize(14, 14)
        self.cam_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_posicion(0)
        self.name_label = QLabel(nombre)
        self.name_label.setObjectName("binName")
        self.name_edit = QLineEdit(nombre)
        self.name_edit.setObjectName("binNameEdit")
        self.name_edit.hide()
        self.name_edit.returnPressed.connect(self._confirmar_nombre)
        # `editingFinished` cubre el clic afuera; `returnPressed` ya paso por
        # aqui, y por eso `_renombrando` hace de guarda para no avisar dos
        # veces del mismo cambio.
        self.name_edit.editingFinished.connect(self._confirmar_nombre)
        self.source_label = QLabel("")
        self.source_label.setObjectName("binSource")
        self.count_label = QLabel("0 clips")
        self.count_label.setObjectName("binCount")
        for w in (self.chevron, self.cam_mark, self.name_label, self.name_edit,
                  self.source_label, self.count_label):
            fila.addWidget(w)

        # los puntos de color con su numero. Se arman una vez y se esconden
        # cuando valen cero: un «0 rejects» no es informacion, es ruido.
        self._marcas: dict[str, tuple[QLabel, QLabel]] = {}
        for flag, color in self.MARCAS:
            punto = QLabel("")
            punto.setObjectName("binDot")
            punto.setFixedSize(6, 6)
            punto.setAttribute(Qt.WA_StyledBackground, True)
            punto.setStyleSheet(
                f"background-color: {color}; border-radius: 2px;"
            )
            numero = QLabel("0")
            numero.setObjectName("binCount")
            fila.addWidget(punto)
            fila.addWidget(numero)
            self._marcas[flag] = (punto, numero)

        fila.addStretch(1)
        # el cartel de arrastre vive DENTRO del encabezado y no en una banda
        # aparte: la banda del mockup empujaba las tarjetas hacia abajo justo
        # cuando estas apuntando con el mouse, y el destino se te movia solo.
        self.drop_label = QLabel("")
        self.drop_label.setObjectName("binDropHint")
        self.drop_label.hide()
        fila.addWidget(self.drop_label)
        self.proxy_badge = QLabel("sin proxies")
        self.proxy_badge.setObjectName("binProxyBadge")
        self.proxy_badge.setProperty("estado", "ninguno")
        self.more_button = QPushButton("⋯")
        self.more_button.setObjectName("binMore")
        self.more_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.more_button.setFixedSize(22, 20)
        self.more_button.clicked.connect(self._abrir_menu_del_boton)
        fila.addWidget(self.proxy_badge)
        fila.addWidget(self.more_button)

    # --- datos -----------------------------------------------------------

    def set_posicion(self, posicion: int) -> None:
        """Tiñe la marca segun el lugar del bin en el orden de importacion.

        Por posicion y no por nombre, igual que los cuartos: renombrar un
        bin no lo mueve de lugar, asi que tampoco puede cambiarle el color
        con el que ya lo reconoces.
        """
        # `setStyleSheet` obliga a repolir el widget y es de lo mas caro que
        # hay en Qt: sin la guarda, cada reagrupada lo llamaria por bin.
        if getattr(self, "_posicion", None) == posicion:
            return
        self._posicion = posicion
        color = theme.bin_color(posicion)
        # 18% de tinte detras de un glifo aclarado, como el mockup. A plena
        # tinta la marca competiria con la franja de cuarto de la miniatura,
        # que es otro dato.
        self.cam_mark.setStyleSheet(
            f"background-color: {theme.con_alfa_qss(color, theme.BIN_TINT_ALPHA)};"
            f" color: {theme.aclarar(color, theme.BIN_INK_LIGHTEN)};"
            f" border-radius: 3px; font-size: {theme.FONT_MICRO}px;"
        )

    def set_counts(self, cuantos: int, por_flag: dict[str, int]) -> None:
        self._cuantos = cuantos
        self.count_label.setText(f"{cuantos} clips")
        for flag, _ in self.MARCAS:
            punto, numero = self._marcas[flag]
            tiene = por_flag.get(flag, 0)
            numero.setText(str(tiene))
            punto.setVisible(bool(tiene))
            numero.setVisible(bool(tiene))

    def copiar_de(self, otro: "_BinHeader") -> None:
        """Se vuelve un clon visual de `otro`. Lo usa el encabezado pegado:
        es el MISMO encabezado, dibujado flotando -- si copiara solo el
        nombre, la insignia de proxies y los puntos de estado quedarian
        diciendo lo del bin anterior."""
        self.nombre = otro.nombre
        self.name_label.setText(otro.nombre)
        self.source_label.setText(otro.source_label.text())
        self.count_label.setText(otro.count_label.text())
        self._cuantos = otro._cuantos
        for flag, _ in self.MARCAS:
            punto, numero = self._marcas[flag]
            punto_otro, numero_otro = otro._marcas[flag]
            numero.setText(numero_otro.text())
            punto.setVisible(not punto_otro.isHidden())
            numero.setVisible(not numero_otro.isHidden())
        self.proxy_badge.setText(otro.proxy_badge.text())
        estado = otro.proxy_badge.property("estado")
        if self.proxy_badge.property("estado") != estado:
            self.proxy_badge.setProperty("estado", estado)
            self.proxy_badge.style().unpolish(self.proxy_badge)
            self.proxy_badge.style().polish(self.proxy_badge)
        self.set_posicion(otro._posicion)
        self.set_collapsed(otro._colapsado)

    def marcas_texto(self) -> list[str]:
        """Los tres numeros de los puntos, en el orden del mockup."""
        return [self._marcas[flag][1].text() for flag, _ in self.MARCAS]

    def set_source(self, texto: str) -> None:
        self.source_label.setText(texto)

    def set_proxies(self, enganchados: int, total: int,
                    resolucion: str = "") -> None:
        """La insignia del mockup: `proxy 1080p · 23/23`.

        El «21/23» es a proposito visible: dos archivos no calzaron cuadro a
        cuadro y NO se engancharon, que es mejor que enganchar un proxy
        corrido y poner el in en el cuadro equivocado.

        `resolucion` viene vacia cuando en el bin hay mas de una --mismo
        criterio que `_resumen_de_proxies`--: decir una de las dos seria
        mentir sobre la otra mitad.
        """
        marca = f"proxy {resolucion}" if resolucion else "proxy"
        if not enganchados:
            texto, estado = "sin proxies", "ninguno"
        elif enganchados < total:
            texto, estado = f"{marca} · {enganchados}/{total}", "parcial"
        else:
            texto, estado = f"{marca} · {enganchados}/{total}", "completo"
        self.proxy_badge.setText(texto)
        if self.proxy_badge.property("estado") != estado:
            self.proxy_badge.setProperty("estado", estado)
            self.proxy_badge.style().unpolish(self.proxy_badge)
            self.proxy_badge.style().polish(self.proxy_badge)

    def set_soltando(self, activo: bool, cuantos: int = 0) -> None:
        """El resaltado de «suelta aquí y va a este bin» (pantalla 4).

        Es una propiedad y no un `setStyleSheet` por bin: el arrastre manda
        un evento por cada movimiento del mouse, y repolir un widget entero
        en cada uno seria repintar la hoja sesenta veces por segundo.
        """
        activo = bool(activo)
        self.drop_label.setVisible(activo)
        if activo:
            # cuantos archivos traes es lo que el mockup pone en la zona: sin
            # el numero no sabes si soltaste la carpeta o un archivo suelto
            self.drop_label.setText(
                f"＋ soltar aquí · {cuantos} archivos" if cuantos != 1
                else "＋ soltar aquí · 1 archivo"
            )
        if self.property("soltando") != activo:
            self.setProperty("soltando", activo)
            self.style().unpolish(self)
            self.style().polish(self)

    def set_collapsed(self, colapsado: bool) -> None:
        self._colapsado = bool(colapsado)
        self.chevron.setText("▸" if colapsado else "▾")
        if self.property("colapsado") != self._colapsado:
            self.setProperty("colapsado", self._colapsado)
            self.style().unpolish(self)
            self.style().polish(self)

    # --- interaccion -----------------------------------------------------

    def alternar_colapso(self) -> None:
        self.collapse_toggled.emit(self.nombre)

    def mousePressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self.alternar_colapso()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Doble clic renombra, como en el rail de cuartos. El clic simple ya
        colapso y expandio de vuelta: es visual y no cuesta nada."""
        self.empezar_a_renombrar()

    def empezar_a_renombrar(self) -> None:
        """En el LUGAR, con un `QLineEdit`. Nada de `QInputDialog`: es modal,
        y la F3 mato el ultimo diálogo modal justo porque colgaba la suite
        bajo `offscreen`."""
        self._renombrando = True
        self.name_edit.setText(self.nombre)
        self.name_label.hide()
        self.name_edit.show()
        self.name_edit.selectAll()
        self.name_edit.setFocus()

    def _confirmar_nombre(self) -> None:
        if not self._renombrando:
            return
        self._renombrando = False
        nuevo = self.name_edit.text().strip()
        self.name_edit.hide()
        self.name_label.show()
        # el mismo nombre no es un cambio: avisar igual haria que la ventana
        # reconstruyera la hoja para nada
        if nuevo and nuevo != self.nombre:
            self.rename_requested.emit(self.nombre, nuevo)

    def construir_menu(self) -> QMenu:
        """El menu del spec §4.2, tal cual la pantalla 3 del mockup.

        Devuelve el `QMenu` en vez de abrirlo para poder probar los renglones
        sin abrir nada: un menu abierto en un test es un ciclo de eventos
        esperando un clic que nunca llega.
        """
        # SIN padre a proposito. Colgandolo del encabezado, cada apertura
        # dejaba un QMenu mas como hijo en C++ con su objeto de Python ya
        # muerto, y al repolir el encabezado `ensurePolished` recorre a los
        # hijos y busca el override de Python de cada uno: sobre un
        # envoltorio muerto eso es un segfault. Aqui el dueño es Python --
        # `_menu` lo sostiene mientras esta abierto y lo suelta despues.
        menu = QMenu()
        renombrar = QAction("Renombrar bin…", menu)
        renombrar.setShortcut("F2")
        renombrar.triggered.connect(self.empezar_a_renombrar)
        menu.addAction(renombrar)

        enlazar = QAction("Enlazar proxies…", menu)
        enlazar.triggered.connect(lambda: self.proxies_requested.emit(self.nombre))
        menu.addAction(enlazar)

        quitar_proxies = QAction("Quitar proxies de este bin", menu)
        quitar_proxies.triggered.connect(lambda: self.proxies_cleared.emit(self.nombre))
        menu.addAction(quitar_proxies)
        menu.addSeparator()

        seleccionar = QAction(f"Seleccionar los {self._cuantos} clips", menu)
        seleccionar.setShortcut("Ctrl+A")
        seleccionar.triggered.connect(
            lambda: self.select_all_requested.emit(self.nombre)
        )
        menu.addAction(seleccionar)

        colapsar = QAction("Expandir" if self._colapsado else "Colapsar", menu)
        colapsar.triggered.connect(self.alternar_colapso)
        menu.addAction(colapsar)
        menu.addSeparator()

        quitar = QAction("Quitar del proyecto", menu)
        quitar.triggered.connect(lambda: self.remove_requested.emit(self.nombre))
        menu.addAction(quitar)
        return menu

    def contextMenuEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self._abrir_menu_en(event.globalPos())

    def _abrir_menu_del_boton(self) -> None:
        self._abrir_menu_en(self.more_button.mapToGlobal(
            self.more_button.rect().bottomLeft()
        ))

    def _abrir_menu_en(self, punto) -> None:
        # `popup` y no `exec`: `exec` abre un ciclo de eventos propio, que es
        # exactamente lo que colgaba la suite bajo `offscreen`.
        self.soltar_menu()
        self._menu = self.construir_menu()
        self._menu.popup(punto)

    def soltar_menu(self) -> None:
        """Suelta el menu SIN destruirlo en el acto.

        `self._menu = otra_cosa` --o que muera el encabezado entero-- borra
        el `QMenu` por cuenta de referencias, y eso puede pasar DENTRO del
        `triggered` de una de sus propias acciones: «Quitar del proyecto» y
        «Renombrar» rehacen la hoja, y rehacer la hoja se lleva puesto este
        encabezado. `deleteLater` lo difiere al ciclo de eventos, que es
        cuando ya no queda ningun frame de C++ apoyado en el menu.
        """
        if self._menu is not None:
            self._menu.deleteLater()
            self._menu = None


class _ZonaDeBinNuevo(QWidget):
    """El `.dropnew` del mockup: soltar aquí crea un bin.

    Solo existe mientras hay un arrastre encima de la hoja. Un recuadro
    punteado permanente al pie seria un cartel que no hace nada el 99% del
    tiempo, y ademas le comeria alto a las tarjetas.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropNew")
        self.setAttribute(Qt.WA_StyledBackground, True)
        columna = QVBoxLayout(self)
        columna.setContentsMargins(11, 16, 11, 16)
        columna.setSpacing(4)
        columna.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = QLabel("＋ Bin nuevo")
        self.title_label.setObjectName("dropNewTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label = QLabel(
            "suelta aquí y se crea un bin con el nombre de la carpeta · "
            "lo renombras con doble clic"
        )
        self.hint_label.setObjectName("dropNewHint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(self.title_label)
        columna.addWidget(self.hint_label)
        self.hide()

    def set_carpeta(self, nombre: str) -> None:
        """El nombre que va a tener el bin, que es el de la carpeta que
        traes. Con varias carpetas o archivos sueltos se queda generico:
        adivinar cual manda seria decir un nombre que no va a salir."""
        self.title_label.setText(
            f"＋ Bin nuevo: «{nombre}»" if nombre else "＋ Bin nuevo"
        )

    def set_activa(self, activa: bool) -> None:
        """Encendida = el cursor esta sobre ella, no sobre un bin. Las dos
        zonas nunca pueden prometer a la vez."""
        activa = bool(activa)
        if self.property("activa") != activa:
            self.setProperty("activa", activa)
            self.style().unpolish(self)
            self.style().polish(self)


class _GroupBlock(QWidget):
    """Encabezado de cuarto mas su grilla propia.

    Un bloque por grupo, no una sola grilla gigante: con una sola habria
    que llevar la cuenta de en que fila arranca cada cuarto, y esa
    aritmetica se rompe apenas un grupo se vacia.

    Desde la F4 el grupo es `(bin, cuarto)` --la propuesta A del mockup--
    pero el bloque solo escribe el CUARTO: el bin ya lo dice su encabezado
    unas lineas mas arriba, y repetirlo en cada subgrupo seria ruido.
    """

    def __init__(self, clave: tuple[str, str], parent=None):
        super().__init__(parent)
        self.titulo = clave
        self.bin_nombre, self.cuarto = clave
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP)

        cabecera = QHBoxLayout()
        cabecera.setSpacing(8)
        self.title_label = ElidedLabel(self.cuarto.upper())
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
    # nacio un encabezado de bin. La ventana lo escucha para enchufarle sus
    # señales: los bins aparecen y desaparecen con las importaciones, asi
    # que no alcanza con conectarlos una vez al arrancar.
    bin_header_created = Signal(object)
    # arrastre (F5). La hoja avisa QUE se solto y DONDE; quien lee disco y
    # decide que es material es la ventana, no ella.
    soltado_en_bin = Signal(str, list)      # nombre del bin, rutas
    soltado_en_nuevo_bin = Signal(list)     # rutas

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
        self._blocks: dict[tuple[str, str], _GroupBlock] = {}
        # el orden de los bins es el de IMPORTACION, no el alfabetico: es el
        # orden en que entro el material y el que siguen las flechas.
        self._bin_order: list[str] = []
        self._bin_headers: dict[str, _BinHeader] = {}
        # carpeta de origen y conteo de proxies por bin. Viven aqui y no en
        # el encabezado porque los encabezados nacen y mueren con cada
        # reagrupada, y este dato no.
        self._bin_meta: dict[str, dict] = {}
        self._colapsados: set[str] = set()
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

        # UN encabezado flotante, no uno por bin: es la misma idea de
        # `batch_bar`, que ya flota sobre la hoja. Se dibuja encima del
        # viewport en vez de ocupar alto en el contenido; con un widget
        # pegado por bin habria N peleando por la misma franja.
        self._pegado = _BinHeader("", self._scroll.viewport())
        self._pegado.hide()
        # El `.bin.stuck` del mockup, por propiedad y QSS.
        #
        # Antes era un `QGraphicsDropShadowEffect` --QSS no tiene
        # `box-shadow`-- y SEGFAUTEO la suite: el efecto queda con dos
        # dueños, el padre que se le pasa y el `setGraphicsEffect` que se lo
        # queda, y eso termina en doble liberacion. Salio una vez cada
        # ~20 corridas completas, siempre en la linea que lo construye.
        # El mockup, ademas de la sombra, le sube el borde al `.bin.stuck`,
        # asi que el estado se sigue leyendo sin ella -- y una caida
        # intermitente no se cambia por una sombra.
        self._pegado.setProperty("pegado", True)
        # el flotante es una COPIA del encabezado del bin en el que estas,
        # asi que lo que le hagas tiene que pasarle al de verdad: si no,
        # el menu del encabezado pegado seria decorativo.
        self._pegado.collapse_toggled.connect(self._on_colapso_pedido)
        self._pegado.rename_requested.connect(
            lambda viejo, nuevo: self._reenviar_del_pegado(
                "rename_requested", viejo, nuevo)
        )
        for senal in ("proxies_requested", "proxies_cleared",
                      "select_all_requested", "remove_requested"):
            getattr(self._pegado, senal).connect(
                lambda nombre, s=senal: self._reenviar_del_pegado(s, nombre)
            )
        self._scroll.verticalScrollBar().valueChanged.connect(
            lambda _: self._actualizar_encabezado_pegado()
        )

        # --- arrastrar material a la hoja (F5) ---
        # La hoja entera acepta: el area de scroll y sus hijos no aceptan
        # drops, asi que Qt propaga el evento hasta aqui y con un solo lugar
        # alcanza para las dos zonas.
        self.setAcceptDrops(True)
        self._zona_nueva = _ZonaDeBinNuevo()

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

        # La fila de bins nace VACIA y escondida: sus chips son los bins que
        # hay, y al construir la hoja todavia no hay ninguno. Se llena en
        # `set_bin_order`.
        self._grupo_de_bins = QButtonGroup(self)
        self._grupo_de_bins.setExclusive(True)
        self._chips_de_bin: list[_Chip] = []
        self._pool_de_bins: list[_Chip] = []
        self.fila_bins = _FilaDeChips("BIN", [])
        self.fila_bins.hide()
        filas.append(self.fila_bins)
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
        # el chip «Todos» de la fila de bins tambien lleva la clave "todos",
        # asi que no hace falta un caso aparte para «sin filtrar»
        bin_activo = next(
            (c.clave for c in self._chips_de_bin if c.isChecked()), "todos"
        )
        return FilterState(mostrar=mostrar, estado=estado, bin=bin_activo,
                           busqueda=self.search_input.text())

    # --- los chips de bin -------------------------------------------------

    def fila_de_bins(self) -> "_FilaDeChips":
        return self.fila_bins

    def chips_de_bin(self) -> list[str]:
        """Lo que dice cada chip, sin el conteo: `["Todos", "Dron", …]`."""
        return [c._etiqueta for c in self._chips_de_bin]

    def chip_de_bin(self, nombre: str) -> _Chip | None:
        """`"todos"` devuelve el chip que quita el filtro."""
        return next((c for c in self._chips_de_bin if c.clave == nombre), None)

    def _reconstruir_chips_de_bin(self) -> None:
        """Un chip por bin, en el orden de importacion, mas «Todos».

        Con menos de dos bins la fila se esconde entera: filtrar por el
        unico bin que hay no filtra nada, y seria un renglon mas en una
        barra que ya lleva dos grupos y siete chips.
        """
        antes = self.filter_state().bin
        claves = ["todos"] + list(self._bin_order)
        # el pool solo CRECE: los chips se reusan cambiandoles la clave y la
        # etiqueta, nunca se destruyen (ver `_FilaDeChips.set_chips`)
        while len(self._pool_de_bins) < len(claves):
            chip = _Chip("todos", "Todos", self.fila_bins)
            chip.clicked.connect(self._on_filters_changed)
            self._grupo_de_bins.addButton(chip)
            self._pool_de_bins.append(chip)
        for chip, clave in zip(self._pool_de_bins, claves):
            chip.clave = clave
            chip._etiqueta = "Todos" if clave == "todos" else _etiqueta_de_chip(clave)
            chip.set_count(None)
        self._chips_de_bin = self._pool_de_bins[:len(claves)]
        self.fila_bins.set_chips(self._chips_de_bin)
        self.fila_bins.setVisible(len(self._bin_order) > 1)
        # el bin que estabas filtrando puede haberse ido --lo quitaste o lo
        # renombraste--, y ahi la hoja se quedaba vacia sin ningun chip
        # encendido que explicara por que
        elegido = self.chip_de_bin(antes) or self._chips_de_bin[0]
        # primero se prende el que queda: el grupo es exclusivo, asi que
        # prenderlo es lo que apaga a los sobrantes escondidos
        elegido.setChecked(True)
        self._marcar_chips_de_cola()
        if elegido.clave != antes:
            self.filters_changed.emit(self.filter_state())

    def set_bin_counts(self, conteos: dict[str, int]) -> None:
        for chip in self._chips_de_bin:
            if chip.clave != "todos":
                chip.set_count(conteos.get(chip.clave, 0))

    def _on_filters_changed(self) -> None:
        self._marcar_chips_de_cola()
        self.filters_changed.emit(self.filter_state())

    def _marcar_chips_de_cola(self) -> None:
        """El chip activo que SI filtra se tiñe de ámbar, como en el mockup.

        No es decoración: el ámbar es el color de la cola en toda la app --el
        chip `cola de ←→`, el playhead, el clip actual-- y verlo en el chip es
        lo que dice «por aquí se mueven las flechas ahora».
        """
        for chip in list(self.chips.values()) + self._chips_de_bin:
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

    def group_titles(self) -> list[tuple[str, str]]:
        """Las claves `(bin, cuarto)` en el orden en que se dibujan."""
        return [b.titulo for b in self._ordered_blocks()]

    def set_bin_order(self, nombres: list[str]) -> None:
        """El orden de los bins es el de importacion, no el alfabetico: es el
        orden en que Bruno metio el material y por el que se mueven las
        flechas."""
        self._bin_order = list(nombres)
        self._reconstruir_chips_de_bin()
        self._firma = None
        self._regroup()

    def set_bin_meta(self, nombre: str, origen: str = "",
                     proxies: tuple[int, int] | None = None,
                     resolucion: str | None = None) -> None:
        """La carpeta de origen y cuantos proxies engancharon.

        Los dos son datos de la VENTANA --la hoja no lee disco ni sondea
        proxies--, asi que entran por aqui y se guardan aparte del
        encabezado, que se rehace en cada reagrupada.
        """
        meta = self._bin_meta.setdefault(nombre, {})
        if origen:
            meta["origen"] = origen
        if proxies is not None:
            meta["proxies"] = proxies
        if resolucion is not None:
            meta["resolucion"] = resolucion
        cabecera = self._bin_headers.get(nombre)
        if cabecera is not None:
            self._aplicar_meta(cabecera)

    def _aplicar_meta(self, cabecera: _BinHeader) -> None:
        meta = self._bin_meta.get(cabecera.nombre, {})
        cabecera.set_source(meta.get("origen", ""))
        enganchados, total = meta.get("proxies", (0, 0))
        cabecera.set_proxies(enganchados, total, meta.get("resolucion", ""))

    def bin_headers(self) -> list[str]:
        """Los bins que hoy tienen encabezado, en el orden en que se ven."""
        return [
            w.nombre for w in self._widgets_del_contenido()
            if isinstance(w, _BinHeader)
        ]

    def bin_header_widget(self, nombre: str) -> _BinHeader | None:
        return self._bin_headers.get(nombre)

    def set_bin_collapsed(self, nombre: str, colapsado: bool) -> None:
        """Colapsar es VISUAL: los clips siguen contando en los totales y
        siguen en la cola de las flechas. Si sacara clips de la cola seria un
        filtro escondido, y la flecha se saltaria material sin decir por que.
        """
        if colapsado:
            self._colapsados.add(nombre)
        else:
            self._colapsados.discard(nombre)
        cabecera = self._bin_headers.get(nombre)
        if cabecera is not None:
            cabecera.set_collapsed(colapsado)
        self._aplicar_visibilidad()
        self._firma = None
        self._relayout()
        # el flotante es una copia, y si se quedara con el chevron viejo el
        # UNICO encabezado que estas viendo estaria mintiendo
        self._actualizar_encabezado_pegado()

    def bin_collapsed(self, nombre: str) -> bool:
        return nombre in self._colapsados

    def renombrar_bin(self, viejo: str, nuevo: str) -> None:
        """Le lleva al nombre nuevo lo que la hoja guarda POR NOMBRE.

        Son dos cosas y las dos se notan: la meta --carpeta de origen y
        conteo de proxies-- y el colapso. Sin esto, cambiarle el nombre a un
        bin cerrado lo abria solo y le borraba la carpeta de origen de la
        vista.
        """
        if viejo == nuevo:
            return
        if viejo in self._bin_meta:
            self._bin_meta[nuevo] = self._bin_meta.pop(viejo)
        if viejo in self._colapsados:
            self._colapsados.discard(viejo)
            self._colapsados.add(nuevo)

    def set_clips(self, clips: list[ClipThumbnail]) -> None:
        for card in self.item_widgets:
            self._desechar(card)
        for block in self._blocks.values():
            self._desechar(block)
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

    def append_clips(self, clips: list[ClipThumbnail]) -> None:
        """Como `update_clips`, pero cuando la lista CRECIO.

        `update_clips` cae en `set_clips` si cambia el largo, y `set_clips`
        destruye todas las tarjetas -- con sus miniaturas adentro. Agregar
        material no puede costar las portadas de lo que ya estaba: eso es
        justo lo que Bruno vio al importar una segunda carpeta.

        Las tarjetas nuevas se agregan al FINAL de `item_widgets`, que es
        donde caen sus indices de clip. La Regla 1 de la clase sigue en pie:
        esta lista va por indice de clip, no por posicion visual.
        """
        viejas = len(self.item_widgets)
        if len(clips) < viejas:
            self.set_clips(clips)
            return
        for card, clip in zip(self.item_widgets, clips):
            card.update_content(clip)
        for index in range(viejas, len(clips)):
            card = ClipCard(clips[index])
            # `i=index` captura el indice POR VALOR. Sin eso, todas las
            # tarjetas nuevas comparten la misma variable y avisan del
            # ultimo clip -- mismo cuidado que en `set_clips`.
            card.clicked.connect(lambda mods, i=index: self._on_card_clicked(i, mods))
            card.doble_click.connect(lambda i=index: self.clip_activated.emit(i))
            self.item_widgets.append(card)
        # el filtro guarda INDICES y los nuevos no estaban cuando se calculo:
        # quien filtre vuelve a llamar a set_visible_indices.
        self._visible = None
        # hay tarjetas que antes no existian: la firma anterior no las cuenta
        self._firma = None
        self._regroup()
        self.title_label.setText(f"CLIPS · {len(clips)}")
        self._redraw()

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
        self._aplicar_visibilidad()
        # esconder NO alcanza: el QGridLayout deja el hueco donde estaba la
        # tarjeta. Verificado contra Qt -- hay que re-colocar salteandolas.
        self._regroup()

    def _es_visible(self, indice: int) -> bool:
        return self._visible is None or indice in self._visible

    def _aplicar_visibilidad(self) -> None:
        """Una tarjeta se ve si la deja pasar el filtro Y su bin no esta
        colapsado. Son dos cosas distintas sobre la misma tarjeta, y por eso
        se deciden juntas y en un solo lugar: puestas en dos lados, la
        segunda le devuelve la vida a lo que escondio la primera."""
        for i, card in enumerate(self.item_widgets):
            card.setVisible(
                self._es_visible(i) and card.clip.bin_nombre not in self._colapsados
            )

    def _group_of(self, clip: ClipThumbnail) -> tuple[str, str]:
        return (clip.bin_nombre, clip.room_label or SIN_CLASIFICAR)

    def _widgets_del_contenido(self) -> list[QWidget]:
        """Todo lo que hay en la columna, encabezados de bin incluidos y en
        el orden en que se dibujan."""
        return [
            self._content_layout.itemAt(i).widget()
            for i in range(self._content_layout.count())
            if self._content_layout.itemAt(i).widget() is not None
        ]

    def _ordered_blocks(self) -> list[_GroupBlock]:
        return [
            w for w in self._widgets_del_contenido() if isinstance(w, _GroupBlock)
        ]

    def _posicion_de_bin(self, nombre: str) -> int:
        return (self._bin_order.index(nombre)
                if nombre in self._bin_order else len(self._bin_order))

    def _orden_de_grupo(self, clave: tuple[str, str]) -> tuple:
        """Primero el bin --por su posicion de importacion-- y adentro los
        cuartos, con «Sin clasificar» arriba porque es la cola de trabajo."""
        bin_nombre, cuarto = clave
        pos = (self._bin_order.index(bin_nombre)
               if bin_nombre in self._bin_order else len(self._bin_order))
        return (pos, bin_nombre, cuarto != SIN_CLASIFICAR, cuarto)

    def _regroup(self) -> None:
        titulos: list[tuple[str, str]] = []
        for card in self.item_widgets:
            titulo = self._group_of(card.clip)
            if titulo not in titulos:
                titulos.append(titulo)
        titulos.sort(key=self._orden_de_grupo)

        for titulo in titulos:
            if titulo not in self._blocks:
                self._blocks[titulo] = _GroupBlock(titulo)

        # las tarjetas de un bin colapsado se esconden aqui y no solo en
        # `set_bin_collapsed`: `set_clips` las vuelve a crear visibles, y sin
        # esto un bin cerrado se abria solo apenas se refrescaba la hoja.
        self._aplicar_visibilidad()

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
                self._desechar(self._blocks.pop(titulo))

        self._sincronizar_encabezados([b for b, _ in titulos])

        while self._content_layout.count():
            self._content_layout.takeAt(0)
        ultimo_bin = None
        for titulo in titulos:
            bin_nombre = titulo[0]
            if bin_nombre != ultimo_bin:
                # el encabezado va ARRIBA de los grupos de su bin: debajo
                # diria que el material de la Sony es del dron
                self._content_layout.addWidget(self._bin_headers[bin_nombre])
                ultimo_bin = bin_nombre
            self._content_layout.addWidget(self._blocks[titulo])
        # al final de todo y escondida: solo se muestra mientras hay un
        # arrastre encima (ver `_marcar_zona`). Se re-agrega aqui porque este
        # bucle vacia el layout entero en cada reagrupada.
        self._content_layout.addWidget(self._zona_nueva)
        self._refrescar_encabezados()

    def _sincronizar_encabezados(self, presentes: list[str]) -> None:
        """Crea el encabezado de cada bin que tiene clips y tira el de los
        que se quedaron sin ninguno."""
        for nombre in presentes:
            if nombre not in self._bin_headers:
                cabecera = _BinHeader(nombre)
                cabecera.collapse_toggled.connect(self._on_colapso_pedido)
                self._bin_headers[nombre] = cabecera
                cabecera.set_collapsed(nombre in self._colapsados)
                cabecera.set_posicion(self._posicion_de_bin(nombre))
                self._aplicar_meta(cabecera)
                self.bin_header_created.emit(cabecera)
        for nombre in list(self._bin_headers):
            if nombre not in presentes:
                self._desechar(self._bin_headers.pop(nombre))
        # la meta y el colapso van por NOMBRE y no se podaban solos: la
        # carpeta de origen de un bin que ya no existe se quedaba en memoria
        # para siempre, y un bin nuevo con el mismo nombre la heredaba.
        #
        # Vale tambien el orden declarado, no solo los bins con tarjetas:
        # entre `set_bin_order` y `set_clips` hay un instante en que el orden
        # ya trae el nombre nuevo y las tarjetas todavia el viejo, y podar
        # ahi contra las tarjetas tiraba justo lo que se acababa de renombrar.
        vivos = set(presentes) | set(self._bin_order)
        for nombre in list(self._bin_meta):
            if nombre not in vivos:
                self._bin_meta.pop(nombre)
        self._colapsados &= vivos

    def _reenviar_del_pegado(self, senal: str, *args) -> None:
        real = self._bin_headers.get(self._pegado.nombre)
        if real is not None:
            getattr(real, senal).emit(*args)

    def _on_colapso_pedido(self, nombre: str) -> None:
        self.set_bin_collapsed(nombre, nombre not in self._colapsados)

    def _refrescar_encabezados(self) -> None:
        """Los conteos del encabezado salen de las TARJETAS, no de un dato
        aparte: dos vistas del mismo numero se contradicen solas."""
        totales: dict[str, int] = {}
        por_flag: dict[str, dict[str, int]] = {}
        for card in self.item_widgets:
            nombre = card.clip.bin_nombre
            totales[nombre] = totales.get(nombre, 0) + 1
            marcas = por_flag.setdefault(nombre, {})
            marcas[card.clip.flag] = marcas.get(card.clip.flag, 0) + 1
        # el mismo numero alimenta el encabezado y el chip del filtro: dos
        # cuentas del mismo dato se contradicen solas
        self.set_bin_counts(totales)
        for nombre, cabecera in self._bin_headers.items():
            cabecera.set_counts(totales.get(nombre, 0), por_flag.get(nombre, {}))
            cabecera.set_posicion(self._posicion_de_bin(nombre))
        self._actualizar_encabezado_pegado()

    def _actualizar_encabezado_pegado(self) -> None:
        """UN encabezado flotante para todos los bins.

        Se busca el ultimo encabezado que ya paso por arriba del borde del
        viewport: ese es el bin en el que estas parado. En el tope no hay
        ninguno y el flotante se esconde, porque el encabezado de verdad ya
        se ve.
        """
        y = self._scroll.verticalScrollBar().value()
        arriba = None
        for widget in self._widgets_del_contenido():
            # ESTRICTO: con `<=`, el primer encabezado --que arranca en y=0--
            # se daria por pegado ya en el tope, y el flotante taparia al de
            # verdad sin que hayas movido nada.
            if isinstance(widget, _BinHeader) and widget.y() < y:
                arriba = widget
        if arriba is None:
            self._pegado.hide()
            return
        self._pegado.copiar_de(arriba)
        # alineado con el contenido, no con el viewport: el contenido lleva
        # 13 px de margen a cada lado, y sin descontarlos el flotante queda
        # corrido respecto del encabezado que esta imitando.
        margenes = self._content_layout.contentsMargins()
        self._pegado.setGeometry(
            margenes.left(), 0,
            max(1, self._scroll.viewport().width()
                - margenes.left() - margenes.right()),
            self._pegado.sizeHint().height(),
        )
        self._pegado.show()
        self._pegado.raise_()

    # --- arrastrar material a la hoja (F5) --------------------------------

    def _desechar(self, widget: QWidget) -> None:
        """Saca un widget de la vista sin destruirlo AHORA.

        `self._blocks.pop(t).setParent(None)` destruia el objeto de C++ en
        esa misma linea: `pop` devuelve un temporal, quitarle el padre le
        devuelve la propiedad a Python, y al morir la ultima referencia
        --que es el temporal-- shiboken lo borra en el acto.

        El problema no es borrarlo, es CUANDO. Estas podas corren dentro de
        `_regroup`, y `_regroup` corre dentro del evento que las provoco:
        renombrar un bin destruia el encabezado viejo --con su `QLineEdit`
        adentro-- mientras el stack seguia dentro del `keyPressEvent` de ese
        mismo `QLineEdit`. Use-after-free, la misma familia de los tres
        segfaults que ya costaron arreglos en este archivo.

        `deleteLater` lo difiere al ciclo de eventos, que es cuando ya no
        queda ningun frame de C++ apoyado en el widget. Es el patron que ya
        usan `room_rail.py` y `transicion.py`.
        """
        if isinstance(widget, _BinHeader):
            # su menu de clic derecho se va con el, y puede estar corriendo
            # una de sus acciones justo ahora
            widget.soltar_menu()
        widget.hide()
        widget.setParent(None)
        widget.deleteLater()

    def zona_de_bin_nuevo(self) -> "_ZonaDeBinNuevo":
        return self._zona_nueva

    @staticmethod
    def _rutas_de(mime) -> list[Path]:
        """Solo archivos locales. Un arrastre desde el navegador trae URLs
        http, y esas no son material que la app pueda abrir."""
        return [Path(u.toLocalFile()) for u in mime.urls() if u.isLocalFile()]

    def dragEnterEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Solo archivos. Aceptar texto o cualquier otro mime haria que el
        cursor prometa algo que al soltar no pasa."""
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        event.acceptProposedAction()
        self._marcar_zona(event.position().toPoint(), event.mimeData())

    def dragMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        event.acceptProposedAction()
        self._marcar_zona(event.position().toPoint(), event.mimeData())

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self._marcar_zona(None, None)

    def dropEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self._marcar_zona(None, None)
        if not event.mimeData().hasUrls():
            return
        rutas = self._rutas_de(event.mimeData())
        if not rutas:
            return
        destino = self._bin_bajo(event.position().toPoint())
        if destino is None:
            self.soltado_en_nuevo_bin.emit(rutas)
        else:
            self.soltado_en_bin.emit(destino, rutas)
        event.acceptProposedAction()

    def _marcar_zona(self, punto, mime) -> None:
        """Enciende UNA de las dos zonas: la del bin de destino o la de bin
        nuevo. Nunca las dos, que seria prometer dos cosas distintas."""
        destino = None if punto is None else self._bin_bajo(punto)
        rutas = self._rutas_de(mime) if mime is not None else []
        for nombre, cabecera in self._bin_headers.items():
            cabecera.set_soltando(nombre == destino, len(rutas))
        # el flotante tapa al encabezado de verdad: si no se marcara tambien,
        # el unico encabezado que estas viendo se quedaria apagado
        if not self._pegado.isHidden():
            self._pegado.set_soltando(self._pegado.nombre == destino, len(rutas))
        if punto is None:
            self._zona_nueva.hide()
            return
        self._zona_nueva.set_carpeta(self._nombre_probable(rutas))
        self._zona_nueva.set_activa(destino is None)
        self._zona_nueva.show()

    @staticmethod
    def _nombre_probable(rutas: list[Path]) -> str:
        """El nombre que va a tener el bin si sueltas aquí.

        Es la misma regla que usa `MainWindow.importar_rutas` --la carpeta
        de donde sale el material--, escrita aparte porque la hoja no lee
        disco. Con carpetas mezcladas se queda vacio: adivinar cual manda
        seria prometer un nombre que no va a salir.
        """
        if not rutas:
            return ""
        if len(rutas) == 1:
            ruta = rutas[0]
            return ruta.name if ruta.is_dir() else ruta.parent.name
        padres = {r.parent for r in rutas}
        return rutas[0].parent.name if len(padres) == 1 else ""

    def _regiones_de_bin(self) -> list[list]:
        """La franja vertical que ocupa cada bin, en coordenadas de la hoja.

        Va del tope de su encabezado al pie de su ultimo grupo: apuntarle al
        encabezado exacto seria una mira de 30 px de alto sobre una columna
        de 700.
        """
        regiones: list[list] = []
        for widget in self._widgets_del_contenido():
            if isinstance(widget, _BinHeader):
                y = widget.mapTo(self, QPoint(0, 0)).y()
                regiones.append([widget.nombre, y, y + widget.height()])
            elif regiones and isinstance(widget, _GroupBlock):
                # los ESCONDIDOS no cuentan. Un widget invisible conserva la
                # geometria que tenia, muy abajo: con un bin colapsado --que
                # es justo lo que haces con la camara que no estas
                # trabajando-- su franja seguia llegando hasta donde llegaba
                # antes y se tragaba entera la del bin de abajo, asi que el
                # material caia en la camara equivocada.
                if widget.isHidden():
                    continue
                y = widget.mapTo(self, QPoint(0, 0)).y()
                regiones[-1][2] = max(regiones[-1][2], y + widget.height())
        return regiones

    def _bin_bajo(self, punto) -> str | None:
        """Sobre que bin se esta soltando, o `None` si es el vacio."""
        # el encabezado de la hoja --busqueda y chips-- no es material: sin
        # esta guarda, lo que cayera ahi arriba se lo comia el primer bin,
        # porque su franja arranca justo debajo.
        if not self._scroll.geometry().contains(punto):
            return None
        for nombre, arriba, abajo in self._regiones_de_bin():
            if arriba <= punto.y() <= abajo:
                return nombre
        return None

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
            frozenset(self._colapsados),
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
        por_grupo: dict[tuple[str, str], list[ClipCard]] = {}
        for indice, card in enumerate(self.item_widgets):
            if self._es_visible(indice):
                por_grupo.setdefault(self._group_of(card.clip), []).append(card)

        for titulo, block in self._blocks.items():
            while block.grid.count():
                block.grid.takeAt(0)
            tarjetas = por_grupo.get(titulo, [])
            block.set_count(len(tarjetas))
            # un grupo del que el filtro no dejo pasar nada no tiene por que
            # ocupar su encabezado y su linea. Un bin colapsado esconde los
            # suyos por lo mismo: si no, el bin cerrado seguiria dejando las
            # lineas de sus cuartos, que es un hueco que no dice nada.
            block.setVisible(bool(tarjetas) and titulo[0] not in self._colapsados)
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
        # el flotante se coloca al hacer scroll, y sin esto cambiar el ancho
        # lo dejaba con el de antes hasta el proximo scroll -- colgando
        # fuera de la hoja.
        self._actualizar_encabezado_pegado()

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
