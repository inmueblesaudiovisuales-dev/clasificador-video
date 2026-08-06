# tests/ui/test_video_widget.py
from pathlib import Path

from clasificador_video.ui.video_widget import VideoWidget


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
