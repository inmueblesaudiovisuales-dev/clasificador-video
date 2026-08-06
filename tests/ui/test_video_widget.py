# tests/ui/test_video_widget.py
from pathlib import Path

from clasificador_video.ui.video_widget import ScrubBar, VideoWidget, format_timecode


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
    assert color.name() == "#4fd1e8"  # TRIM_COLOR


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
    assert color.name() == "#4fd1e8"


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
    assert color.name() != "#4fd1e8"


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
