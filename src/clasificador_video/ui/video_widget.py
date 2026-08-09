# src/clasificador_video/ui/video_widget.py
from __future__ import annotations

from ctypes import c_char_p, c_void_p
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QOpenGLContext, QPainter, QPainterPath, QPen
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from clasificador_video.player import MpvPlayer
from clasificador_video.ui.theme import (
    BG_APP,
    con_alfa,
    CURRENT_COLOR,
    LINE,
    PLAYHEAD_HIGHLIGHT,
    TICK_MAJOR_COLOR,
    TICK_MAJOR_OVER_VIDEO_RGBA,
    TICK_MINOR_COLOR,
    TICK_MINOR_OVER_VIDEO_RGBA,
    HANDLE_LABEL_PX,
    SCRUB_HANDLE_WIDTH,
    SCRUB_HEIGHT,
    SCRUB_OUTSIDE_RGBA,
    SCRUB_RADIUS,
    SCRUB_TICKS_HEIGHT,
    SCRUB_TRIM_FILL_ALPHA,
    TRACK_OVER_VIDEO_RGBA,
    TRIM_COLOR,
)


class _FrameReadySignal(QObject):
    """Duena de la señal de "hay un frame nuevo", en una clase auxiliar
    separada de VideoWidget (QOpenGLWidget) a proposito: declarar un
    `Signal()` a nivel de clase directamente en un QOpenGLWidget, cuando
    se crean y destruyen muchas instancias de MainWindow/QShortcut reales
    en una sola sesion, interactuo mal con el manejo de meta-objetos de
    PySide6/shiboken y produjo un crash nativo (Bus error / Segfault
    dentro de MetaObjectBuilder) -- ver
    docs/superpowers/HANDOFF-2026-08-06-arreglar-video-y-diseno.md §3.2.
    Aislar la señal en un QObject simple, sin la complejidad de metaclase
    de QOpenGLWidget, elimina la interaccion.
    """

    frame_ready = Signal()


def _default_mpv_factory(**kwargs) -> object:
    import mpv

    return mpv.MPV(**kwargs)


def _get_proc_address(_ctx: c_void_p, name: c_char_p) -> int:
    """Puente entre el pedido de mpv de una funcion de OpenGL y el contexto
    real que Qt ya abrio para este widget -- mpv nunca crea su propio
    contexto GL, dibuja dentro del que ya existe (API de render).
    """
    glctx = QOpenGLContext.currentContext()
    if glctx is None:
        return 0
    address = glctx.getProcAddress(bytes(name).decode("utf-8"))
    return int(address) if address else 0


class VideoWidget(QOpenGLWidget):
    """Widget que embebe mpv via su API de render (`vo=libmpv`), la via
    soportada oficialmente por python-mpv/libmpv para toolkits como Qt.

    Reemplaza el intento anterior por `wid` (el handle de ventana nativo):
    en macOS, con el backend grafico actual de mpv (gpu-next / Vulkan via
    MoltenVK), `wid` no es confiable -- mpv abre su propia ventana de
    Cocoa en vez de dibujar dentro del NSView que se le da. Verificado en
    vivo el 2026-08-06 con `grab()` + inspeccion real de la imagen (no
    solo logs): con `wid` el widget quedaba negro y aparecia una ventana
    de mpv aparte; con el API de render el frame decodificado aparece
    dentro del widget y no se abre ninguna ventana adicional.

    mpv entrega cada frame nuevo por un callback (`update_cb`) que corre
    en un hilo de mpv, no el de Qt -- por eso ese callback solo emite una
    señal Qt (`_frame_ready`); Qt encola la llamada a `update()` de vuelta
    al hilo principal de forma segura (conexion en cola por default entre
    hilos distintos).
    """

    def __init__(self, mpv_factory: Callable[..., object] = _default_mpv_factory, parent=None):
        super().__init__(parent)
        self.setObjectName("videoWidget")
        self._mpv_factory = mpv_factory
        self._player: MpvPlayer | None = None
        self._render_ctx = None
        self._proc_addr_fn = None  # mantener viva la referencia -- ctypes no lo hace por nosotros
        self._frame_signal = _FrameReadySignal()
        self._frame_signal.frame_ready.connect(self.update)

    @property
    def player(self) -> MpvPlayer:
        """Creado perezosamente: construir `mpv.MPV` abre hilos reales de
        inmediato. Sin esta pereza, cada VideoWidget creado en una prueba
        (aunque nunca toque video) abriria un mpv real de mas, acumulando
        hilos hasta comprometer el proceso.
        """
        if self._player is None:
            self._player = MpvPlayer(mpv_factory=self._mpv_factory)
        return self._player

    def initializeGL(self) -> None:
        import mpv

        proc_addr_fn = mpv.MpvGlGetProcAddressFn(_get_proc_address)
        self._proc_addr_fn = proc_addr_fn
        try:
            self._render_ctx = mpv.MpvRenderContext(
                self.player.mpv_handle, "opengl",
                opengl_init_params={"get_proc_address": proc_addr_fn},
            )
        except AttributeError:
            # el handle de mpv usado no es un mpv.MPV real (p. ej. un doble
            # de pruebas) -- no hay contexto de render que crear.
            return
        self._render_ctx.update_cb = self._on_mpv_update

    def _on_mpv_update(self) -> None:
        # corre en un hilo de mpv: solo señalizar, nunca pintar aqui.
        self._frame_signal.frame_ready.emit()

    def paintGL(self) -> None:
        if self._render_ctx is None:
            return
        # defaultFramebufferObject() esta en pixeles fisicos; width()/height()
        # son logicos. En pantallas Retina (devicePixelRatio > 1) sin este
        # factor mpv solo pinta la esquina inferior izquierda del widget --
        # encontrado en vivo el 2026-08-06 verificando con grab().
        ratio = self.devicePixelRatioF()
        self._render_ctx.render(
            flip_y=True,
            opengl_fbo={
                "w": round(self.width() * ratio),
                "h": round(self.height() * ratio),
                "fbo": self.defaultFramebufferObject(),
            },
        )

    def open_clip(self, path: Path) -> None:
        self.player.open(path)

    def cerrar_clip(self) -> None:
        """Deja el visor sin nada. Se usa cuando el proyecto se queda sin
        clips: no hay a que volver, y seguir mostrando el ultimo seria
        mostrar material que ya no esta en el proyecto."""
        self.player.cerrar()

    def toggle_play(self) -> None:
        self.player.toggle()


def format_timecode(frame: int, fps: float) -> str:
    """Convierte un numero de frame absoluto a MM:SS:FF -- consistente con
    que el modelo de datos ya guarda todo en frames (Clip.in_frame/out_frame),
    no en milisegundos.
    """
    if fps <= 0:
        return "00:00:00"
    total_seconds = frame / fps
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    remaining_frames = round(frame - (minutes * 60 + seconds) * fps)
    return f"{minutes:02d}:{seconds:02d}:{remaining_frames:02d}"


_TICK_INTERVALS_SECONDS = (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600)
_MIN_MAJOR_TICK_SPACING_PX = 48


def tick_interval_seconds(duration: float, usable_width: int) -> float:
    """Elige el intervalo 'prolijo' (1s, 2s, 5s...) mas chico tal que dos
    marcas mayores consecutivas de la regla queden separadas al menos
    _MIN_MAJOR_TICK_SPACING_PX -- para que no se amontonen en clips
    largos ni queden ridiculamente separadas en clips cortos.
    """
    if duration <= 0:
        return 0.0
    for interval in _TICK_INTERVALS_SECONDS:
        if usable_width * (interval / duration) >= _MIN_MAJOR_TICK_SPACING_PX:
            return float(interval)
    return float(_TICK_INTERVALS_SECONDS[-1])


class ScrubBar(QWidget):
    """Linea de tiempo del clip actual, tipo Source Monitor de Premiere.

    Desde la F6 es una BANDA de 26 px, no una linea: el rango marcado se lee
    como una zona llena, lo que queda fuera se oscurece, y cada extremo lleva
    una manija con su letra (`I` / `O`). Cada manija se dibuja apenas su
    marcador existe, sin esperar al otro, para que marcar in/out (teclas I/O)
    se vea en el momento y no solo se guarde en silencio.

    Responde a click y arrastre con el mouse (emite `seek_started` al
    empezar el gesto y `seek_requested(seconds)` en cada evento) para
    saltar de posicion como un scrubber real -- pero no conoce a
    MpvPlayer: quien escucha la señal decide que hacer con el player
    (ver MainWindow._on_scrub_seek*). Marcar in/out sigue siendo solo
    con el teclado (I/O/U).
    """

    seek_started = Signal()
    seek_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("scrubBar")
        # la altura sale del tema, no de un numero suelto: el mockup la
        # fija en 26 px y el VideoStage la usa para posicionar el overlay.
        self.setFixedHeight(SCRUB_HEIGHT)
        self._duration = 0.0
        self._position = 0.0
        self._in_frame: int | None = None
        self._out_frame: int | None = None
        self._fps = 0.0
        self._over_video = False

    def set_over_video(self, activo: bool) -> None:
        """Modo overlay: la barra va ENCIMA del video, asi que el riel
        tiene que ser translucido. Un color solido se veria como una
        banda opaca tapando la imagen."""
        self._over_video = activo
        self.update()

    def track_color(self) -> QColor:
        if self._over_video:
            return QColor(*TRACK_OVER_VIDEO_RGBA)
        return QColor(LINE)

    def tick_colors(self) -> tuple[QColor, QColor]:
        """(mayor, menor). Mismo motivo que `track_color`: los grises oscuros
        del tema estan pensados para fondo oscuro y sobre el video se leen
        como rayas negras -- peor todavia sobre una pared blanca."""
        if self._over_video:
            return (QColor(*TICK_MAJOR_OVER_VIDEO_RGBA),
                    QColor(*TICK_MINOR_OVER_VIDEO_RGBA))
        return (QColor(TICK_MAJOR_COLOR), QColor(TICK_MINOR_COLOR))

    @property
    def duration(self) -> float:
        """Lo que la barra cree que dura el clip. Publico porque la ventana
        tiene que poder comparar: mpv reporta la duracion tarde y hay que
        volver a pedirsela hasta que exista."""
        return self._duration

    def set_duration(self, seconds: float) -> None:
        self._duration = max(seconds, 0.0)
        self.update()

    def set_position(self, seconds: float) -> None:
        self._position = max(seconds, 0.0)
        self.update()

    def set_in_out(self, in_frame: int | None, out_frame: int | None, fps: float) -> None:
        self._in_frame = in_frame
        self._out_frame = out_frame
        self._fps = fps
        self.update()

    def _x_for(self, seconds: float, left: int, usable_width: int) -> int:
        if self._duration <= 0:
            return left
        ratio = max(0.0, min(1.0, seconds / self._duration))
        return left + round(ratio * usable_width)

    def _seconds_for_x(self, x: int) -> float:
        if self._duration <= 0:
            return 0.0
        left, right = 6, self.width() - 6
        usable_width = max(right - left, 1)
        ratio = max(0.0, min(1.0, (x - left) / usable_width))
        return ratio * self._duration

    def _major_tick_seconds(self) -> list[float]:
        if self._duration <= 0:
            return []
        left, right = 6, self.width() - 6
        usable_width = max(right - left, 1)
        interval = tick_interval_seconds(self._duration, usable_width)
        if interval <= 0:
            return []
        ticks = []
        n = 0
        t = 0.0
        while t <= self._duration + 1e-9:
            ticks.append(t)
            n += 1
            t = interval * n
        return ticks

    def _x_de_marca(self, frame: int | None) -> int | None:
        """Posicion horizontal de un extremo del rango, o None si no se puede
        calcular. Sin `fps` no hay conversion posible: pasa con una sesion
        restaurada de disco donde no se volvio a correr ffprobe.
        """
        if frame is None or not self._fps or self._duration <= 0:
            return None
        left, right = 6, self.width() - 6
        return self._x_for(frame / self._fps, left, max(right - left, 1))

    def _manijas(self) -> list[tuple[int, str]]:
        """`(x, letra)` de cada manija a dibujar, en orden.

        Va por marca EXISTENTE, no por rango completo: cada extremo se dibuja
        apenas se marca, sin esperar al otro, para que apretar `I` se vea en
        el momento y no solo se guarde en silencio.

        **`paintEvent` dibuja desde aqui**, no repitiendo la condicion por su
        cuenta: si fueran dos codigos distintos, `etiquetas_de_manija` podria
        decir que hay manija mientras el pintado no dibuja ninguna, y el test
        seguiria en verde.
        """
        marcas = ((self._in_frame, "I"), (self._out_frame, "O"))
        return [(x, letra) for x, letra in
                ((self._x_de_marca(f), letra) for f, letra in marcas)
                if x is not None]

    def etiquetas_de_manija(self) -> list[str]:
        """Que manijas hay, en orden: `["I"]`, `["O"]`, `["I", "O"]` o `[]`.
        Existe para poder probar la barra sin contar pixeles."""
        return [letra for _, letra in self._manijas()]

    def _playhead_body_path(self, x: float, track_y: int) -> QPainterPath:
        half = 6.5
        body_h = 7
        point_h = 6
        r = 2.5
        body_bottom = track_y - point_h
        body_top = body_bottom - body_h
        path = QPainterPath()
        path.moveTo(x - half + r, body_top)
        path.lineTo(x + half - r, body_top)
        path.quadTo(x + half, body_top, x + half, body_top + r)
        path.lineTo(x + half, body_bottom)
        path.lineTo(x - half, body_bottom)
        path.lineTo(x - half, body_top + r)
        path.quadTo(x - half, body_top, x - half + r, body_top)
        path.closeSubpath()
        return path

    def _playhead_point_path(self, x: float, track_y: int) -> QPainterPath:
        half = 6.5
        point_h = 6
        body_bottom = track_y - point_h
        path = QPainterPath()
        path.moveTo(x - half, body_bottom)
        path.lineTo(x + half, body_bottom)
        path.lineTo(x, track_y)
        path.closeSubpath()
        return path

    def paintEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """La banda del mockup: 26 px de alto, translucida sobre el video.

        Cambia la FORMA, no la funcion. Lo que se conserva a proposito y esta
        cubierto por tests escritos antes de esta reescritura: el riel
        translucido (una banda opaca taparia una franja de imagen, que es el
        problema que este rediseño existe para resolver), el seek con mouse,
        las marcas de tiempo adaptativas --mejores que las fijas del mockup--
        y el playhead con cuerpo redondeado, que se agarra mejor con el mouse
        que la linea de 2 px del diseño.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, right = 6, self.width() - 6
        usable_width = max(right - left, 1)
        alto = self.height()
        track_y = alto // 2
        # la banda ocupa el widget completo entre los margenes laterales; el
        # recorte redondeado hace que nada de lo de adentro se salga
        banda = QRectF(left, 0, usable_width, alto)
        camino_banda = QPainterPath()
        camino_banda.addRoundedRect(banda, SCRUB_RADIUS, SCRUB_RADIUS)

        painter.save()
        painter.setClipPath(camino_banda)
        painter.fillPath(camino_banda, self.track_color())

        if self._duration > 0:
            in_x = self._x_de_marca(self._in_frame)
            out_x = self._x_de_marca(self._out_frame)
            # invertido (marcaste O antes que I) se normaliza aqui: pintar un
            # ancho negativo hace desaparecer la zona -- la tarjeta ya tuvo
            # exactamente este bug
            if in_x is not None and out_x is not None:
                x1, x2 = min(in_x, out_x), max(in_x, out_x)
                painter.fillRect(
                    QRectF(x1, 0, x2 - x1, alto),
                    QColor(*con_alfa(TRIM_COLOR, SCRUB_TRIM_FILL_ALPHA)),
                )
                # y lo de afuera se apaga: el rango no solo se pinta, tambien
                # se baja lo que no vas a usar
                fuera = QColor(*SCRUB_OUTSIDE_RGBA)
                painter.fillRect(QRectF(left, 0, x1 - left, alto), fuera)
                painter.fillRect(QRectF(x2, 0, right - x2, alto), fuera)

            major_ticks = self._major_tick_seconds()
            if len(major_ticks) >= 1:
                # las marcas van ABAJO de la banda, como en el mockup, pero el
                # intervalo lo sigue eligiendo `tick_interval_seconds`
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                base = alto
                color_mayor, color_menor = self.tick_colors()
                minor_pen = QPen(color_menor, 1)
                major_pen = QPen(color_mayor, 1)
                for i, t in enumerate(major_ticks):
                    tx = self._x_for(t, left, usable_width)
                    painter.setPen(major_pen)
                    painter.drawLine(tx, base - SCRUB_TICKS_HEIGHT, tx, base)
                    if i + 1 < len(major_ticks):
                        interval = major_ticks[i + 1] - t
                        painter.setPen(minor_pen)
                        for frac in (1, 2, 3, 4):
                            mx = self._x_for(t + interval * frac / 5, left, usable_width)
                            painter.drawLine(mx, base - SCRUB_TICKS_HEIGHT // 2, mx, base)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # manijas: una barrita del color del rango con su letra arriba
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            for x_manija, letra in self._manijas():
                painter.fillRect(
                    QRectF(x_manija - SCRUB_HANDLE_WIDTH / 2, 0,
                           SCRUB_HANDLE_WIDTH, alto),
                    QColor(TRIM_COLOR),
                )
                self._dibujar_letra_de_manija(painter, x_manija, letra, right)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            x = self._x_for(self._position, left, usable_width)
            body_path = self._playhead_body_path(x, track_y)
            point_path = self._playhead_point_path(x, track_y)
            gradient = QLinearGradient(0, track_y - 13, 0, track_y - 6)
            gradient.setColorAt(0.0, QColor(PLAYHEAD_HIGHLIGHT))
            gradient.setColorAt(1.0, QColor(CURRENT_COLOR))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawPath(body_path)
            painter.setBrush(QColor(CURRENT_COLOR))
            painter.drawPath(point_path)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(CURRENT_COLOR), 2))
            painter.drawLine(round(x), track_y, round(x), alto)

        painter.restore()
        painter.end()

    def _dibujar_letra_de_manija(self, painter: QPainter, x: int, letra: str,
                                 right: int) -> None:
        """La `I` / `O` del mockup: fondo del color del rango y letra oscura.

        Va pegada al lado de ADENTRO del rango. Puesta siempre a la derecha,
        la `O` de un rango que llega al final del clip quedaria cortada por el
        borde de la banda.
        """
        ancho, alto_caja = 11, 10
        hacia_la_izquierda = letra == "O" or x + ancho > right
        x0 = x - ancho if hacia_la_izquierda else x
        caja = QRectF(x0, 0, ancho, alto_caja)
        painter.fillRect(caja, QColor(TRIM_COLOR))
        # se guarda y restaura la fuente ENTERA, no su tamaño: una fuente
        # definida en pixeles reporta `pointSize() == -1`, y devolverle ese
        # -1 es un valor invalido que Qt rechaza con una advertencia.
        fuente_previa = painter.font()
        fuente = QFont(fuente_previa)
        fuente.setPixelSize(HANDLE_LABEL_PX)
        fuente.setBold(True)
        painter.setFont(fuente)
        painter.setPen(QColor(BG_APP))
        painter.drawText(caja, Qt.AlignmentFlag.AlignCenter, letra)
        painter.setFont(fuente_previa)

    def mousePressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.button() != Qt.MouseButton.LeftButton or self._duration <= 0:
            return
        self.seek_started.emit()
        self.seek_requested.emit(self._seconds_for_x(round(event.position().x())))

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._duration <= 0:
            return
        self.seek_requested.emit(self._seconds_for_x(round(event.position().x())))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.button() != Qt.MouseButton.LeftButton or self._duration <= 0:
            return
        self.seek_requested.emit(self._seconds_for_x(round(event.position().x())))
