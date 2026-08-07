# src/clasificador_video/ui/video_widget.py
from __future__ import annotations

from ctypes import c_char_p, c_void_p
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QOpenGLContext, QPainter, QPen
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from clasificador_video.player import MpvPlayer
from clasificador_video.ui.theme import ACCENT, BORDER, TICK_MAJOR_COLOR, TICK_MINOR_COLOR, TRIM_COLOR


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
    """Linea de tiempo del clip actual, tipo Source Monitor de Premiere:
    un track con el playhead y, cuando hay marca de in/out, brackets en
    los extremos -- cada uno se dibuja apenas su marcador existe, sin
    esperar al otro -- para que marcar in/out (teclas I/O) se vea en el
    momento, no solo se guarde en silencio.

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
        self.setFixedHeight(34)
        self._duration = 0.0
        self._position = 0.0
        self._in_frame: int | None = None
        self._out_frame: int | None = None
        self._fps = 0.0

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

    def paintEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, right = 6, self.width() - 6
        usable_width = max(right - left, 1)
        track_y = self.height() // 2

        painter.setPen(QPen(QColor(BORDER), 3))
        painter.drawLine(left, track_y, right, track_y)

        if self._duration > 0:
            major_ticks = self._major_tick_seconds()
            if len(major_ticks) >= 1:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                minor_pen = QPen(QColor(TICK_MINOR_COLOR), 1)
                major_pen = QPen(QColor(TICK_MAJOR_COLOR), 1)
                for i, t in enumerate(major_ticks):
                    tx = self._x_for(t, left, usable_width)
                    painter.setPen(major_pen)
                    painter.drawLine(tx, track_y - 9, tx, track_y)
                    if i + 1 < len(major_ticks):
                        next_t = major_ticks[i + 1]
                        interval = next_t - t
                        painter.setPen(minor_pen)
                        for frac in (1, 2, 3, 4):
                            minor_t = t + interval * frac / 5
                            mx = self._x_for(minor_t, left, usable_width)
                            painter.drawLine(mx, track_y - 5, mx, track_y)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            in_x = out_x = None
            if self._in_frame is not None and self._fps:
                in_x = self._x_for(self._in_frame / self._fps, left, usable_width)
            if self._out_frame is not None and self._fps:
                out_x = self._x_for(self._out_frame / self._fps, left, usable_width)

            if in_x is not None and out_x is not None:
                x1, x2 = min(in_x, out_x), max(in_x, out_x)
                painter.setPen(QPen(QColor(TRIM_COLOR), 4))
                painter.drawLine(x1, track_y, x2, track_y)

            bracket_pen = QPen(QColor(TRIM_COLOR), 3)
            painter.setPen(bracket_pen)
            if in_x is not None:
                painter.drawLine(in_x, track_y - 8, in_x, track_y + 8)
            if out_x is not None:
                painter.drawLine(out_x, track_y - 8, out_x, track_y + 8)

            x = self._x_for(self._position, left, usable_width)
            painter.setPen(QPen(QColor(ACCENT), 2))
            painter.drawLine(x, 2, x, self.height() - 2)

        painter.end()

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
