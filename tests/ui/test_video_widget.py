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
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(10.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    track_y = bar.height() // 2
    left, usable = 6, 200 - 12
    x_5s = left + round((5.0 / 10.0) * usable)
    color = img.pixelColor(x_5s, track_y - 8)
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
