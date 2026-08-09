# src/clasificador_video/ui/video_stage.py
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from clasificador_video.player import SPEED_PROFILES
from clasificador_video.ui import theme
from clasificador_video.ui.segmented import SegmentedControl
from clasificador_video.ui.video_widget import ScrubBar, VideoWidget, format_timecode

M = theme.OVERLAY_MARGIN
SCRIM_HEIGHT = 150
# El texto del badge se aclara para que se lea sobre el fondo oscuro, pero
# el PUNTO va con el color puro del cuarto: aclarar tambien desatura, y si
# todo el badge va aclarado se lee gris -- comprobado contra el mockup, que
# usa exactamente esta division (punto saturado, texto claro).
BADGE_TEXT_MIX = 0.35
BADGE_BORDER_ALPHA = 140


# La chuleta bajo la barra. Solo teclas que EXISTEN: anunciar una que no hace
# nada es el bug que este proyecto ya tuvo cuatro veces. `F` y `esc` entraron
# con la F7, cuando se construyo el modo solo video.
KEYS_HINT_TEXT = "←  →  cola  ·  ,  .  cuadro  ·  L  K  velocidad  ·  F  ·  esc"
TOP_SCRIM_HEIGHT = 90


def formato_corto(segundos: float, fps: float) -> str:
    """`SS:FF` para lo que dura menos de un minuto, `MM:SS:FF` para lo demas.

    El mockup escribe `total 18:11` --18 segundos y 11 cuadros--: un `00:` de
    minutos adelante seria ruido en clips de recorrido, que casi nunca pasan
    del minuto. Pero un clip largo SI necesita los minutos, asi que aparecen
    solos cuando hacen falta.
    """
    if fps <= 0:
        return "--:--"
    completo = format_timecode(round(segundos * fps), fps)
    minutos, resto = completo.split(":", 1)
    return resto if minutos == "00" else completo


def etiqueta_de_velocidad(velocidad: float) -> str:
    """`1.0` → `1×`. El signo es `×` (multiplicacion), no la letra equis:
    asi lo escribe el mockup y asi se lee en cualquier NLE."""
    return f"{velocidad:g}×"


class _BadgeRow(QWidget):
    """Los badges de estado del clip, flotando sobre el video.

    Uno por dato, cada uno con SU color. La F2 los junto en una sola
    etiqueta gris (`▌ COMEDOR    ● PICK`) y con eso tiro el color, que es
    justo el canal que hace legible el estado sin leer.

    El badge `Proxy 1080p` del mockup es de la F9.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.room_badge = QLabel("")
        self.room_badge.setObjectName("overlayBadges")
        self.flag_badge = QLabel("")
        self.flag_badge.setObjectName("overlayBadges")
        self.flag_badge.hide()
        # `▶ auto`: avisa que el clip arranco solo. Va con el color del acento
        # y no con uno de estado -- no dice nada del clip, dice lo que esta
        # haciendo el reproductor (separacion por canal semantico, theme.py).
        # en mayusculas como los otros dos: el mockup las aplica con CSS
        # (`text-transform`), que en QSS no existe -- van escritas asi
        self.auto_badge = QLabel("▶ AUTO")
        self.auto_badge.setObjectName("overlayBadges")
        self.auto_badge.setStyleSheet(
            self._estilo(
                theme.aclarar(theme.CURRENT_COLOR, BADGE_TEXT_MIX),
                theme.CURRENT_COLOR,
            )
        )
        self.auto_badge.hide()
        # el unico badge SIN color: los otros tres dicen algo del clip, y
        # este dice que archivo se esta reproduciendo. Sin estilo propio se
        # queda con el gris neutro de `#overlayBadges`, que es justo lo que
        # el mockup dibuja.
        self.proxy_badge = QLabel("")
        self.proxy_badge.setObjectName("overlayBadges")
        self.proxy_badge.hide()
        layout.addWidget(self.room_badge)
        layout.addWidget(self.flag_badge)
        layout.addWidget(self.auto_badge)
        layout.addWidget(self.proxy_badge)

    def set_room(self, nombre: str | None, color: str | None) -> None:
        if not nombre or not color:
            self.room_badge.setText(nombre.upper() if nombre else "SIN CLASIFICAR")
            self.room_badge.setStyleSheet("")
            return
        # el punto va en el color puro del cuarto y el texto en su version
        # clara: es lo unico que hace que el badge se LEA de color
        self.room_badge.setText(
            f'<span style="color: {color}">▌</span> {nombre.upper()}'
        )
        self.room_badge.setStyleSheet(
            self._estilo(theme.aclarar(color, BADGE_TEXT_MIX), color)
        )

    def set_flag(self, flag: str) -> None:
        datos = {
            "pick": ("● PICK", theme.PICK_COLOR),
            "reject": ("✕ REJECT", theme.REJECT_COLOR),
            "destacado": ("★ DESTACADO", theme.STAR_COLOR),
        }.get(flag)
        if datos is None:
            self.flag_badge.hide()
            return
        texto, color = datos
        self.flag_badge.setText(texto)
        self.flag_badge.setStyleSheet(self._estilo(color, color))
        self.flag_badge.show()

    def set_proxy(self, resolucion: str | None) -> None:
        """`"720p"` → `PROXY 720P`. `None` esconde el badge.

        Con cadena vacia se muestra `PROXY` a secas: pasa en una sesion
        restaurada de disco, donde el clip trae su proxy guardado pero
        nadie volvio a correr ffprobe. Inventarle «1080p» seria mentir;
        callar la resolucion, no.

        En mayusculas escritas a mano: el mockup las aplica con
        `text-transform`, que en QSS no existe (ya paso con `▶ AUTO`).
        """
        if resolucion is None:
            self.proxy_badge.hide()
            return
        self.proxy_badge.setText(f"PROXY {resolucion.upper()}".strip())
        self.proxy_badge.show()

    def set_auto(self, encendido: bool) -> None:
        """Se llama seguido (una vez por tick del playhead), asi que sale
        temprano si no hay nada que cambiar: `show()`/`hide()` sobre un widget
        que ya esta como se pide dispara relayout del renglon de badges."""
        if encendido == (not self.auto_badge.isHidden()):
            return
        self.auto_badge.setVisible(encendido)

    @staticmethod
    def _estilo(texto: str, borde: str) -> str:
        color_borde = theme.con_alfa_qss(borde, BADGE_BORDER_ALPHA)
        return f"#overlayBadges {{ color: {texto}; border: 1px solid {color_borde}; }}"


class VideoStage(QWidget):
    """El video y sus controles flotando encima.

    Ningun control vive en una banda: en un 9:16 cada 16 px de banda
    cuestan 9 px de ancho de video, y ese es el problema que este rediseño
    existe para resolver.

    Que Qt componga widgets normales sobre el contenido de OpenGL de mpv se
    valido en la F0 (ver el plan maestro): el alfa se mezcla contra los
    pixeles del video, no contra negro.
    """

    def __init__(self, mpv_factory=None, parent=None):
        super().__init__(parent)
        self.setObjectName("videoStage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.video = VideoWidget(mpv_factory=mpv_factory) if mpv_factory else VideoWidget()
        layout.addWidget(self.video)

        # --- overlays: hijos del VideoWidget, no hermanos ---
        self.scrim = QLabel("", self.video)
        self.scrim.setObjectName("overlayScrim")
        self._nombre_completo = ""
        self.file_label = QLabel("", self.video)
        self.file_label.setObjectName("overlayFile")
        self.badges = _BadgeRow(self.video)
        self.timecode_label = QLabel("", self.video)
        self.timecode_label.setObjectName("overlayTimecode")
        # Las etiquetas salen de los perfiles del reproductor, no escritas a
        # mano: si alguna vez se agrega una velocidad, el control la muestra
        # sin que haya que acordarse de tocar dos archivos.
        self.speed = SegmentedControl(
            [etiqueta_de_velocidad(v) for v in SPEED_PROFILES],
            self.video,
            object_name="speedSegmented",
        )
        self.quality = SegmentedControl(["Full", "1/2", "1/4", "1/8"], self.video)
        self.scrub_bar = ScrubBar(self.video)
        self.scrub_bar.set_over_video(True)

        # --- el pie del video: una sola pieza en el mockup ---
        # degradado de arriba, para que el nombre de archivo se lea sin
        # meterlo en una pastilla (asi lo hace el mockup)
        self.top_scrim = QLabel("", self.video)
        self.top_scrim.setObjectName("overlayTopScrim")
        self.frame_label = QLabel("", self.video)
        self.frame_label.setObjectName("overlayFrame")
        # IN/OUT en timecode, a la derecha de la misma fila. El mockup los
        # tiene y son OTRO dato que la pastilla: la pastilla dice cuanto dura
        # el rango, esto dice donde empieza y donde termina.
        self.io_label = QLabel("", self.video)
        self.io_label.setObjectName("overlayInOut")
        self.range_pill = QLabel("", self.video)
        self.range_pill.setObjectName("rangePill")
        self.range_pill.hide()          # sin rango marcado no hay nada que decir
        self.keys_hint = QLabel(KEYS_HINT_TEXT, self.video)
        self.keys_hint.setObjectName("overlayKeys")

        for pasivo in (self.file_label, self.badges, self.scrim, self.timecode_label,
                       self.top_scrim, self.frame_label, self.range_pill,
                       self.keys_hint, self.io_label):
            # el click y el arrastre tienen que llegar a la scrub bar y al
            # video, no quedarse en una etiqueta decorativa
            pasivo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # sin esta bandera la barra pinta fondo opaco donde no dibuja y se
        # come una franja del video (hallazgo de la F0)
        self.scrub_bar.setAttribute(Qt.WA_TranslucentBackground, True)

        # El padre recibe resizeEvent ANTES de que el hijo cambie de tamaño:
        # posicionar ahi deja los overlays corridos un cuadro.
        self.video.installEventFilter(self)

    def set_timecode(self, texto: str, frame: int | None) -> None:
        """El timecode grande y su numero de cuadro. Sin clip los dos quedan
        vacios: dejar un `f 293` viejo al lado de un timecode en blanco es
        peor que no mostrar nada."""
        cuadro = f"f {frame}" if frame is not None else ""
        # sale temprano si nada cambio: esto corre en cada tick del playhead
        # (10 veces por segundo) y `setText` dispara relayout del widget
        if texto == self.timecode_label.text() and cuadro == self.frame_label.text():
            return
        self.timecode_label.setText(texto)
        self.frame_label.setText(cuadro)
        self._colocar_textos_del_pie()

    def set_in_out_labels(self, in_tc: str | None, out_tc: str | None) -> None:
        """`IN 00:04:12   OUT 00:11:16` a la derecha de la fila del timecode.
        Cada extremo aparece apenas se marca, sin esperar al otro."""
        partes = []
        if in_tc:
            partes.append(f"IN {in_tc}")
        if out_tc:
            partes.append(f"OUT {out_tc}")
        texto = "   ".join(partes)
        if texto == self.io_label.text():
            return
        self.io_label.setText(texto)
        self._colocar_textos_del_pie()

    def set_range_pill(self, rango_segundos: float | None, cuadros: int | None,
                       total_segundos: float, fps: float | None = None) -> None:
        """`rango 07:04 · 212 f · total 18:11`, o nada si no hay rango.

        `fps` se puede omitir: se deduce de cuadros/segundos. La ventana le
        pasa el real, que es el del clip; la deduccion existe para poder
        probar la pastilla sin armar un clip entero.
        """
        if rango_segundos is None or cuadros is None:
            if not self.range_pill.isHidden():
                self.range_pill.hide()
                # sin pastilla se libera el renglon: la fila de teclas, que
                # quiza se habia escondido para no encimarse, puede volver
                self._colocar_textos_del_pie()
            return
        if not fps:
            fps = cuadros / rango_segundos if rango_segundos > 0 else 0.0
        texto = (
            f"rango {formato_corto(rango_segundos, fps)}"
            f"  ·  {cuadros} f"
            f"  ·  total {formato_corto(total_segundos, fps)}"
        )
        cambio = texto != self.range_pill.text() or self.range_pill.isHidden()
        self.range_pill.setText(texto)
        # `show()` ANTES de re-acomodar: el acomodo decide si la fila de teclas
        # cabe al lado de la pastilla, y con la pastilla todavia escondida
        # concluiria que si -- y se encimarian.
        self.range_pill.show()
        if cambio:
            self._colocar_textos_del_pie()

    @staticmethod
    def width_for(height: int, aspect_ratio: float) -> int:
        """Ancho que le corresponde al video para no dejar franjas negras."""
        return max(1, round(height * aspect_ratio))

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 -- override de Qt
        if obj is self.video and event.type() == QEvent.Resize:
            self._place_overlays()
        return super().eventFilter(obj, event)

    def _colocar_textos_del_pie(self) -> None:
        """Re-acomoda las etiquetas del pie que CAMBIAN DE TEXTO.

        Se llama desde los setters, no solo al cambiar de tamaño: las cuatro
        nacen vacias --7 px de ancho-- y sin esto el texto que se les escribe
        despues no cabe. `f 293`, el IN/OUT y la pastilla se veian cortados
        hasta que redimensionaras la ventana, y en la app real marcar IN no
        mostraba nada. Los arneses lo tapaban porque siempre habia un resize
        despues de poner los datos.

        Las posiciones se derivan de la barra, que ya esta colocada: solo
        cambian los ANCHOS de estas etiquetas, no la altura de las filas, asi
        que no hace falta rehacer el acomodo entero en cada tick.
        """
        ancho = self.video.width()
        self.timecode_label.adjustSize()
        self.frame_label.adjustSize()
        y_timecode = self.scrub_bar.y() - 8 - self.timecode_label.height()
        base = y_timecode + self.timecode_label.height()
        self.timecode_label.move(M, y_timecode)
        # el numero de cuadro se alinea con la BASE del timecode, no con su
        # tope: son dos tamaños muy distintos y alinearlos arriba los deja
        # visualmente flotando
        self.frame_label.move(
            M + self.timecode_label.width() + 9,
            base - self.frame_label.height() - 2,
        )

        # el IN/OUT va pegado al borde derecho: crece hacia la izquierda, o
        # se saldria del video al aparecer el segundo timecode
        self.io_label.adjustSize()
        self.io_label.move(ancho - M - self.io_label.width(),
                           base - self.io_label.height() - 2)
        # y se esconde si choca con el timecode. De los tres datos de la fila
        # es el unico que se ve en otro lado: las manijas de la barra dicen
        # donde empieza y termina el rango, y la pastilla cuanto dura. El
        # numero de cuadro, en cambio, no aparece en ningun otro sitio.
        fin_izquierda = self.frame_label.x() + self.frame_label.width()
        self.io_label.setVisible(
            not self.io_label.text() == "" and self.io_label.x() >= fin_izquierda + 10
        )

        self.range_pill.adjustSize()
        self.range_pill.move(M, self.keys_hint.y())

        # Pastilla y fila de teclas comparten el renglon de abajo, y con un
        # video angosto se encimaban dejando las dos ilegibles. Se esconde la
        # FILA DE TECLAS: la pastilla dice cuanto dura el rango que marcaste,
        # la fila es un recordatorio de teclas que ya te sabes. Vuelve sola en
        # cuanto hay lugar.
        #
        # Va aqui y no solo en `_place_overlays` porque la pastilla aparece
        # DESPUES del ultimo cambio de tamaño --al abrir un clip con rango--,
        # y ahi ya nadie volveria a comprobar el choque.
        if self.range_pill.isHidden():
            estorba = False
        else:
            fin_pastilla = self.range_pill.x() + self.range_pill.width()
            estorba = fin_pastilla + 12 > ancho - M - self.keys_hint.sizeHint().width()
        self.keys_hint.setVisible(not estorba)

    def set_file_label(self, texto: str) -> None:
        """El nombre del clip (y su posicion en la cola) sobre el video.

        Pasa por aca y no por `file_label.setText` porque el texto DECIDE
        el acomodo de la fila de arriba: cuanto queda para el nombre y si
        el control de velocidad entra. En la app los datos llegan DESPUES
        del ultimo resize, asi que colocar solo al redimensionar deja los
        controles donde estaban -- el mismo bug que tuvo el pie en la F7.
        """
        if texto == self._nombre_completo:
            return
        self._nombre_completo = texto
        self._place_overlays()

    def _place_overlays(self) -> None:
        ancho, alto = self.video.width(), self.video.height()

        self.scrim.setGeometry(0, alto - SCRIM_HEIGHT, ancho, SCRIM_HEIGHT)
        self.top_scrim.setGeometry(0, 0, ancho, TOP_SCRIM_HEIGHT)


        self.quality.adjustSize()
        self.quality.move(ancho - self.quality.width() - M, M)

        # a la izquierda del de calidad, en la misma fila -- es su lugar en
        # el mockup, y los dos son controles del reproductor
        self.speed.adjustSize()
        x_velocidad = self.quality.x() - self.speed.width() - 8
        # Si no cabe, la velocidad se esconde: es lo que Bruno eligio que se
        # fuera primero, porque `J K L` la siguen cambiando y el nombre del
        # archivo es lo que te dice que clip estas viendo.
        #
        # El caso no es la ventana angosta sino la ventana BAJA: con un clip
        # vertical el ancho del video sale de la altura, asi que a 800 px de
        # alto el video mide 416 px y ahi el control terminaba en x = -165,
        # fuera de la imagen y encimado con el nombre.
        metricas = QFontMetrics(self.file_label.font())
        entero = metricas.horizontalAdvance(self._nombre_completo)
        # cabe si el nombre ENTERO sigue entrando a su lado. Cuando no,
        # antes de cortar el nombre se va la velocidad: lo eligio Bruno,
        # porque `J K L` la siguen cambiando y el nombre es lo que te dice
        # que clip estas viendo.
        cabe = x_velocidad - M - 8 >= entero
        self.speed.setVisible(cabe)
        if cabe:
            self.speed.move(x_velocidad, M)

        # Y si ni asi entra, se corta con puntos suspensivos. QSS no tiene
        # `text-overflow: ellipsis`: sin cortarlo, un nombre largo seguia
        # de largo POR DEBAJO del selector de calidad y se leia partido a
        # la mitad por una caja translucida encima.
        limite = (x_velocidad if cabe else self.quality.x()) - M - 8
        # `elidedText` mide TEXTO y la etiqueta ademas trae relleno del QSS:
        # cortar a `limite` a secas dejaba la caja ~20 px mas ancha que el
        # hueco, y volvia a meterse debajo del selector.
        self.file_label.setText(self._nombre_completo)
        self.file_label.adjustSize()
        relleno = self.file_label.width() - metricas.horizontalAdvance(self._nombre_completo)
        self.file_label.setText(metricas.elidedText(
            self._nombre_completo, Qt.TextElideMode.ElideMiddle,
            max(0, limite - relleno)))
        self.file_label.adjustSize()
        self.file_label.move(M, M)

        # Los badges van debajo de TODA la fila de arriba, no debajo del
        # nombre. El nombre mide 15 px y los controles 25, asi que
        # colgarlos del nombre los metia 2 px por dentro de la caja de la
        # calidad --que es translucida-- y les comia el borde de arriba.
        # Pasaba en los dos anchos desde la F6.
        self.badges.adjustSize()
        alto_fila = max(self.file_label.height(), self.quality.height())
        self.badges.move(M, M + alto_fila + 8)

        # El pie se arma de ABAJO hacia arriba: la fila de teclas y la
        # pastilla van pegadas al borde inferior, la barra encima, y el
        # timecode arriba de todo. Al reves habria que saber de antemano
        # cuanto mide cada cosa.
        self.keys_hint.adjustSize()
        self.range_pill.adjustSize()
        fila_baja = max(self.keys_hint.height(), self.range_pill.height())
        y_fila_baja = alto - M - fila_baja
        self.keys_hint.move(ancho - M - self.keys_hint.width(), y_fila_baja)
        self.range_pill.move(M, y_fila_baja)

        self.scrub_bar.setGeometry(
            M, y_fila_baja - 7 - theme.SCRUB_HEIGHT,
            ancho - 2 * M, theme.SCRUB_HEIGHT,
        )

        self._colocar_textos_del_pie()

        self.scrim.lower()
        self.top_scrim.lower()
        for encima in (self.file_label, self.badges, self.quality, self.speed,
                       self.timecode_label, self.frame_label, self.io_label,
                       self.range_pill, self.keys_hint, self.scrub_bar):
            encima.raise_()
