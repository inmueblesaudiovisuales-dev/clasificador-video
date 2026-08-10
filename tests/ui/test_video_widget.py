# tests/ui/test_video_widget.py
from pathlib import Path

from PySide6.QtCore import QPoint, Qt

from clasificador_video.ui.theme import (
    CURRENT_COLOR,
    SCRUB_HEIGHT,
    TICK_MAJOR_COLOR,
    TRIM_COLOR,
)
from clasificador_video.ui.video_widget import (
    ScrubBar,
    VideoWidget,
    format_timecode,
    tick_interval_seconds,
)


class FakeMpv:
    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0
        self.vid_scale = None
        self.commands = []

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        self.commands.append(args)
        # mpv implementa `frame-step` como "despausar, mostrar un cuadro,
        # volver a pausar": queda pausado SOLO. El doble lo imita para que un
        # test no pueda pasar con una implementacion que ademas escribe
        # `pause`, que contra mpv real aborta el paso (medido el 2026-08-08).
        if args and args[0] in ("frame-step", "frame-back-step"):
            self.pause = True


def test_video_widget_crea_el_player_con_hwdec_y_vo_libmpv(qtbot):
    """El player se crea perezosamente al primer acceso (no en __init__ ni
    en show()) -- construir mpv.MPV real abre hilos de inmediato, y crear
    muchas ventanas en pruebas sin este delay acumula mpv reales de mas.
    """
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    assert widget.player._mpv.init_kwargs["hwdec"] == "videotoolbox"
    assert widget.player._mpv.init_kwargs["vo"] == "libmpv"


def test_open_carga_el_clip_en_el_player(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    widget.open_clip(Path("/shooting/C0012.MP4"))
    assert widget.player._mpv.loaded_path == "/shooting/C0012.MP4"


def test_play_pause_toggle_se_reenvia_al_player(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    widget.toggle_play()
    assert widget.player._mpv.pause is False
    widget.toggle_play()
    assert widget.player._mpv.pause is True


def test_video_widget_tiene_objectname_para_fondo_negro(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    assert widget.objectName() == "videoWidget"


def test_el_player_no_se_crea_hasta_que_se_accede_por_primera_vez(qtbot):
    """Sin esta pereza, cada VideoWidget creado en pruebas (aunque nunca
    toque video) abriria un mpv real de mas, acumulando hilos entre
    pruebas hasta comprometer el proceso.
    """
    calls = []

    def counting_factory(**kwargs):
        calls.append(kwargs)
        return FakeMpv(**kwargs)

    widget = VideoWidget(mpv_factory=counting_factory)
    qtbot.addWidget(widget)
    assert calls == []  # construir el widget solo no debe abrir mpv
    widget.toggle_play()
    assert len(calls) == 1


def test_render_context_no_se_crea_hasta_que_el_widget_se_muestra(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    assert widget._render_ctx is None


def test_video_widget_es_qopenglwidget(qtbot):
    """El embedding via API de render exige una superficie GL real -- un
    QWidget plano (usado en v1 con wid) no sirve.
    """
    from PySide6.QtOpenGLWidgets import QOpenGLWidget

    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    assert isinstance(widget, QOpenGLWidget)


def test_scrub_bar_tiene_objectname_para_el_tema(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    assert bar.objectName() == "scrubBar"


def test_scrub_bar_guarda_duracion_posicion_e_in_out(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.set_duration(10.0)
    bar.set_position(3.0)
    bar.set_in_out(60, 180, 30.0)  # 2s a 6s, a 30fps
    assert bar._duration == 10.0
    assert bar._position == 3.0
    assert bar._in_frame == 60
    assert bar._out_frame == 180
    assert bar._fps == 30.0


def test_scrub_bar_x_for_es_proporcional_a_la_duracion(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(206, 26)
    bar.set_duration(10.0)
    left, usable = 6, 206 - 12
    assert bar._x_for(0.0, left, usable) == left
    assert bar._x_for(10.0, left, usable) == left + usable
    assert bar._x_for(5.0, left, usable) == left + usable // 2


def test_scrub_bar_sin_duracion_no_truena_al_pintar(qtbot):
    """Antes de que mpv reporte la duracion real (clip recien abierto) no
    debe haber division por cero ni excepcion al repintar."""
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.show()
    bar.set_position(1.0)  # sin set_duration -- queda en 0
    bar.repaint()  # no debe lanzar


def test_scrub_bar_dibuja_bracket_de_in_sin_out(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.set_in_out(300, None, 30.0)  # in=10s, sin out
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    assert not pixmap.toImage().isNull()
    expected_x = 6 + round((10.0 / 60.0) * 188)
    img = pixmap.toImage()
    track_y = bar.height() // 2
    color = img.pixelColor(expected_x, track_y - 6)
    assert color.name() == TRIM_COLOR


def test_scrub_bar_dibuja_bracket_de_out_sin_in(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.set_in_out(None, 900, 30.0)  # out=30s, sin in
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    assert not pixmap.toImage().isNull()
    expected_x = 6 + round((30.0 / 60.0) * 188)
    img = pixmap.toImage()
    track_y = bar.height() // 2
    color = img.pixelColor(expected_x, track_y - 6)
    assert color.name() == TRIM_COLOR


def test_scrub_bar_solo_in_no_dibuja_tramo_resaltado(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.set_in_out(300, None, 30.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    track_y = bar.height() // 2
    mid_x = 6 + round((35.0 / 60.0) * 188)
    color = img.pixelColor(mid_x, track_y)
    assert color.name() != TRIM_COLOR


def test_format_timecode_frame_cero():
    assert format_timecode(0, 30.0) == "00:00:00"


def test_format_timecode_un_segundo_exacto():
    assert format_timecode(30, 30.0) == "00:01:00"


def test_format_timecode_minutos_y_frames():
    assert format_timecode(2707, 30.0) == "01:30:07"


def test_format_timecode_fps_no_entero():
    assert format_timecode(30, 29.97) == "00:01:00"


def test_format_timecode_fps_invalido_no_crashea():
    assert format_timecode(100, 0.0) == "00:00:00"


def test_scrub_bar_click_emite_seek_started_y_seek_requested(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.show()
    qtbot.waitExposed(bar)

    with qtbot.waitSignal(bar.seek_started, timeout=1000):
        with qtbot.waitSignal(bar.seek_requested, timeout=1000) as blocker:
            qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(100, 13))
    assert 25.0 < blocker.args[0] < 35.0


def test_scrub_bar_arrastre_con_boton_apretado_emite_seek_requested(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.show()
    qtbot.waitExposed(bar)
    qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(20, 13))

    with qtbot.waitSignal(bar.seek_requested, timeout=1000) as blocker:
        qtbot.mouseMove(bar, pos=QPoint(180, 13))
    assert blocker.args[0] > 40.0

    qtbot.mouseRelease(bar, Qt.MouseButton.LeftButton, pos=QPoint(180, 13))


def test_scrub_bar_move_sin_boton_no_emite_seek(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.show()
    qtbot.waitExposed(bar)

    received = []
    bar.seek_requested.connect(received.append)
    qtbot.mouseMove(bar, pos=QPoint(100, 13))
    assert received == []


def test_scrub_bar_click_fuera_de_los_bordes_clampea(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.show()
    qtbot.waitExposed(bar)

    with qtbot.waitSignal(bar.seek_requested, timeout=1000) as blocker:
        qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(-50, 13))
    assert blocker.args[0] == 0.0


def test_tick_interval_duracion_corta_usa_intervalo_chico():
    assert tick_interval_seconds(10.0, 188) == 5.0


def test_tick_interval_duracion_media_usa_intervalo_mayor():
    assert tick_interval_seconds(90.0, 188) == 30.0


def test_tick_interval_duracion_muy_larga_cae_al_ultimo_intervalo():
    assert tick_interval_seconds(18000.0, 188) == 3600.0


def test_tick_interval_sin_duracion_devuelve_cero():
    assert tick_interval_seconds(0.0, 188) == 0.0


def test_major_tick_seconds_duracion_corta(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(10.0)
    assert bar._major_tick_seconds() == [0.0, 5.0, 10.0]


def test_major_tick_seconds_duracion_media(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(90.0)
    assert bar._major_tick_seconds() == [0.0, 30.0, 60.0, 90.0]


def test_major_tick_seconds_sin_duracion_devuelve_vacio(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    assert bar._major_tick_seconds() == []


def test_scrub_bar_tiene_la_altura_del_tema(qtbot):
    """La altura sale de theme.SCRUB_HEIGHT: el VideoStage la usa para
    posicionar la barra sobre el video, asi que un numero suelto aqui
    dejaria el overlay descolocado."""
    bar = ScrubBar()
    qtbot.addWidget(bar)
    assert bar.height() == SCRUB_HEIGHT


def test_scrub_bar_dibuja_marca_mayor_en_cada_intervalo(qtbot):
    """Las marcas se mudaron al PIE de la banda en la F6 (es donde las pone el
    mockup). Siguen siendo adaptativas: lo que cambio es donde se dibujan, no
    como se calculan -- por eso este test se reescribio en vez de borrarse."""
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(10.0)
    bar.show()
    qtbot.waitExposed(bar)
    img = bar.grab().toImage()
    left, usable = 6, 200 - 12
    x_5s = left + round((5.0 / 10.0) * usable)
    color = img.pixelColor(x_5s, bar.height() - 3)
    assert color.name() == TICK_MAJOR_COLOR


def test_playhead_ya_no_es_linea_recta_de_punta_a_punta(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(60.0)
    bar.set_position(30.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    left, usable = 6, 200 - 12
    x = left + round((30.0 / 60.0) * usable)
    color_arriba = img.pixelColor(x, 2)
    assert color_arriba.name() != CURRENT_COLOR


def test_playhead_tiene_linea_fina_bajando_desde_la_casita(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(60.0)
    bar.set_position(30.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    left, usable = 6, 200 - 12
    x = left + round((30.0 / 60.0) * usable)
    track_y = bar.height() // 2
    color_abajo = img.pixelColor(x, track_y + 10)
    assert color_abajo.name() == CURRENT_COLOR


def test_playhead_punta_toca_track_y_en_la_posicion_correcta(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(60.0)
    bar.set_position(30.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    left, usable = 6, 200 - 12
    x = left + round((30.0 / 60.0) * usable)
    track_y = bar.height() // 2
    color_punta = img.pixelColor(x, track_y - 1)
    assert color_punta.name() == CURRENT_COLOR


# ---------------------------------------------------------------------------
# F2 Task 3: modo overlay de la ScrubBar. Sobre el video, un riel solido se
# ve como una banda opaca tapando la imagen.
# ---------------------------------------------------------------------------


def test_scrub_bar_por_defecto_usa_riel_solido(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    assert bar.track_color().alpha() == 255


def test_scrub_bar_en_modo_overlay_usa_riel_translucido(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.set_over_video(True)
    assert bar.track_color().alpha() < 255


def test_set_over_video_se_puede_apagar(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.set_over_video(True)
    bar.set_over_video(False)
    assert bar.track_color().alpha() == 255


# --- F6 Task 4: lo que la barra NO puede perder al reescribirla ---------------
#
# Estos cinco se escriben ANTES de tocar `paintEvent` y pasan con el codigo
# viejo: son la red que evita repetir lo de la barra de rango de las tarjetas,
# que "sobrevivio tres auditorias del plan y murio en la implementacion".


def _scrub(qtbot, duracion: float = 0.0, ancho: int = 400) -> ScrubBar:
    barra = ScrubBar()
    qtbot.addWidget(barra)
    barra.resize(ancho, SCRUB_HEIGHT)
    barra.set_duration(duracion)
    return barra


def test_la_banda_sigue_siendo_translucida_sobre_el_video(qtbot):
    """Una banda opaca de 26 px tapa una franja del video: exactamente lo
    que este rediseño existe para no hacer."""
    from clasificador_video.ui.theme import TRACK_OVER_VIDEO_RGBA

    barra = _scrub(qtbot, duracion=20.0)
    barra.set_over_video(True)
    assert barra.track_color().alpha() == TRACK_OVER_VIDEO_RGBA[3]
    assert barra.track_color().alpha() < 255


def test_la_barra_sigue_pidiendo_fondo_translucido(qtbot):
    """Hallazgo de la F0: sin `WA_TranslucentBackground` un widget de QPainter
    sobre el video pinta fondo opaco donde no dibuja."""
    from PySide6.QtCore import Qt as _Qt
    from clasificador_video.ui.video_stage import VideoStage

    class _M:
        def __init__(self, **kw):
            self.pause = True
            self.time_pos = 0.0

        def play(self, p):
            pass

    stage = VideoStage(mpv_factory=_M)
    qtbot.addWidget(stage)
    assert stage.scrub_bar.testAttribute(_Qt.WA_TranslucentBackground)


def test_el_seek_con_mouse_sigue_siendo_exacto(qtbot):
    """`_x_for` y `_seconds_for_x` tienen que quedar inversas: si el playhead
    no cae donde hiciste click, la barra deja de servir para marcar in/out."""
    barra = _scrub(qtbot, duracion=18.37)
    for x in (6, 150, 251, 394):
        assert barra._x_for(barra._seconds_for_x(x), 6, barra.width() - 12) == x


def test_las_marcas_de_tiempo_adaptativas_sobreviven(qtbot):
    """Son mejores que las del mockup --escalan de 0.2 s a 24 h sin pasar de
    25 marcas-- y el plan maestro permite conservarlas."""
    barra = _scrub(qtbot, duracion=20.0)
    barra.resize(400, 26)
    assert len(barra._major_tick_seconds()) > 1


def test_las_marcas_siguen_escalando_de_un_clip_corto_a_uno_larguisimo(qtbot):
    barra = _scrub(qtbot, duracion=20.0)
    barra.resize(400, 26)
    for duracion in (0.2, 6.0, 120.0, 3600.0, 86400.0):
        barra.set_duration(duracion)
        assert len(barra._major_tick_seconds()) <= 25, duracion


def test_el_seek_con_mouse_sigue_emitiendo_sus_dos_señales(qtbot):
    """Click y arrastre: `seek_started` abre el gesto y `seek_requested` lleva
    los segundos. Reescribir el pintado no puede llevarselas."""
    barra = _scrub(qtbot, duracion=20.0)
    empezados, pedidos = [], []
    barra.seek_started.connect(lambda: empezados.append(1))
    barra.seek_requested.connect(pedidos.append)
    qtbot.mousePress(barra, Qt.LeftButton, pos=QPoint(200, 13))
    assert empezados == [1]
    assert len(pedidos) == 1 and 0 < pedidos[0] < 20.0


# --- F6 Task 4: la barra cambia de forma, no de funcion ----------------------


def test_la_barra_dibuja_el_rango_como_bloque_lleno(qtbot):
    """El mockup usa una banda de 26 px, no una linea: el rango marcado se
    tiene que leer como una ZONA, no como un subrayado.

    Se mide a `y = alto - 5`, ABAJO del riel viejo. Ahi con el codigo anterior
    no hay nada dibujado ni dentro ni fuera del rango, asi que la diferencia
    solo puede venir de la banda nueva. Medir cerca del centro no sirve: entre
    `track_y - 9` y `track_y` viven las marcas de tiempo, y ahi dentro y fuera
    YA se ven distintos.
    """
    barra = _scrub(qtbot, duracion=20.0)
    barra.resize(400, 26)
    barra.set_in_out(150, 450, 30.0)
    imagen = barra.grab().toImage()
    escala = imagen.width() / max(barra.width(), 1)
    y = round((barra.height() - 5) * escala)
    dentro = imagen.pixelColor(round(200 * escala), y).name()
    fuera = imagen.pixelColor(round(20 * escala), y).name()
    assert dentro != fuera, "el rango no se lee como zona abajo del riel"


def test_lo_que_queda_fuera_del_rango_se_oscurece(qtbot):
    """El mockup tapa lo de afuera con `rgba(0,0,0,.42)`: el rango no solo se
    pinta, tambien se apaga lo que no vas a usar."""
    barra = _scrub(qtbot, duracion=20.0)
    barra.resize(400, 26)
    imagen_sin = barra.grab().toImage()
    barra.set_in_out(150, 450, 30.0)
    imagen_con = barra.grab().toImage()
    escala = imagen_sin.width() / max(barra.width(), 1)
    y = round((barra.height() - 5) * escala)
    x = round(20 * escala)          # bien a la izquierda del IN
    assert imagen_sin.pixelColor(x, y) != imagen_con.pixelColor(x, y)


def test_las_manijas_de_in_y_out_llevan_su_letra(qtbot):
    barra = _scrub(qtbot, duracion=20.0)
    barra.set_in_out(150, 450, 30.0)
    assert barra.etiquetas_de_manija() == ["I", "O"]


def test_sin_rango_no_hay_manijas(qtbot):
    assert _scrub(qtbot, duracion=20.0).etiquetas_de_manija() == []


def test_solo_in_marcado_dibuja_solo_su_manija(qtbot):
    """Cada extremo se dibuja apenas existe, sin esperar al otro: marcar I
    tiene que verse en el momento."""
    barra = _scrub(qtbot, duracion=20.0)
    barra.set_in_out(150, None, 30.0)
    assert barra.etiquetas_de_manija() == ["I"]


def test_solo_out_marcado_dibuja_solo_su_manija(qtbot):
    barra = _scrub(qtbot, duracion=20.0)
    barra.set_in_out(None, 450, 30.0)
    assert barra.etiquetas_de_manija() == ["O"]


def test_un_rango_invertido_no_rompe_las_manijas(qtbot):
    """Marcar `O` antes que `I` deja out < in. La tarjeta ya tuvo este bug:
    pintaba un rango de ancho negativo y desaparecia."""
    barra = _scrub(qtbot, duracion=20.0)
    barra.set_in_out(450, 150, 30.0)
    assert barra.etiquetas_de_manija() == ["I", "O"]
    barra.grab()   # no revienta


def test_sin_fps_no_se_dibujan_manijas(qtbot):
    """Sesion restaurada sin volver a correr ffprobe: hay frames pero no hay
    fps con que convertirlos a segundos."""
    barra = _scrub(qtbot, duracion=20.0)
    barra.set_in_out(150, 450, 0.0)
    assert barra.etiquetas_de_manija() == []


def test_las_marcas_se_aclaran_cuando_van_sobre_el_video(qtbot):
    """Mismo motivo que el riel: los grises del tema estan pensados para fondo
    oscuro. Sobre una pared blanca --la mitad del material de inmuebles-- unas
    marcas #454d59 se leen como rayas negras encima de la imagen."""
    barra = _scrub(qtbot, duracion=20.0)
    mayor_panel, menor_panel = barra.tick_colors()
    barra.set_over_video(True)
    mayor_video, menor_video = barra.tick_colors()
    assert mayor_panel.alpha() == 255 and mayor_video.alpha() < 255
    assert menor_video.alpha() < mayor_video.alpha()


# --- apagar: la ventana ahora se destruye en caliente -----------------------


class _MpvQueSeApaga(FakeMpv):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.terminado = False

    def terminate(self):
        self.terminado = True


class _ContextoDeRenderFalso:
    def __init__(self):
        self.update_cb = None
        self.liberado = False

    def free(self):
        self.liberado = True


def test_apagar_libera_el_contexto_de_render_y_termina_mpv(qtbot):
    """Hasta la F5 la `MainWindow` vivía hasta que moría el proceso, así que
    nadie apagaba nada. Con la pantalla de inicio la ventana se destruye en
    caliente: el contexto de OpenGL se va con el widget y el de mpv se
    liberaría después, sin orden garantizado respecto al callback que corre
    en un hilo de mpv. Es el terreno exacto de los segfaults de este
    proyecto.
    """
    widget = VideoWidget(mpv_factory=_MpvQueSeApaga)
    qtbot.addWidget(widget)
    mpv_falso = widget.player._mpv
    contexto = _ContextoDeRenderFalso()
    widget._render_ctx = contexto

    widget.apagar()

    assert contexto.liberado
    assert contexto.update_cb is None      # y ANTES de liberarlo
    assert mpv_falso.terminado
    assert widget._render_ctx is None


def test_apagar_una_ventana_que_nunca_toco_video_no_enciende_mpv(qtbot):
    """La propiedad `player` CONSTRUYE el reproductor, y construirlo abre
    hilos de mpv de verdad: pedirlo aquí encendería un mpv para apagarlo."""
    creados = []

    def fabrica(**kwargs):
        creados.append(1)
        return _MpvQueSeApaga(**kwargs)

    widget = VideoWidget(mpv_factory=fabrica)
    qtbot.addWidget(widget)

    widget.apagar()

    assert creados == []


def test_apagar_dos_veces_no_revienta(qtbot):
    """`closeEvent` puede llegar más de una vez."""
    widget = VideoWidget(mpv_factory=_MpvQueSeApaga)
    qtbot.addWidget(widget)
    widget.player                          # lo enciende
    widget._render_ctx = _ContextoDeRenderFalso()

    widget.apagar()
    widget.apagar()


def test_despues_de_apagar_no_se_pinta(qtbot):
    """Pintar sin contexto de render es dibujar contra memoria liberada."""
    widget = VideoWidget(mpv_factory=_MpvQueSeApaga)
    qtbot.addWidget(widget)
    widget._render_ctx = _ContextoDeRenderFalso()

    widget.apagar()
    widget.paintGL()                       # no revienta y no dibuja nada


def test_apagar_no_deja_al_reproductor_a_medias(qtbot):
    """Nadie puede volver a hablarle a un mpv terminado: la propiedad
    perezosa devolvería uno nuevo, con sus hilos, sobre una ventana que se
    está cerrando."""
    widget = VideoWidget(mpv_factory=_MpvQueSeApaga)
    qtbot.addWidget(widget)
    widget.player

    widget.apagar()

    assert widget.esta_apagado
