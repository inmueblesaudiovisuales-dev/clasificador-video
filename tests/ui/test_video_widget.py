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


def test_video_widget_crea_un_player_con_wid_del_widget(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    assert widget.player._mpv.init_kwargs["hwdec"] == "videotoolbox"
    assert widget.player._mpv.init_kwargs["wid"] == int(widget.winId())


def test_open_carga_el_clip_en_el_player(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    widget.open_clip(Path("/shooting/C0012.MP4"))
    assert widget.player._mpv.loaded_path == "/shooting/C0012.MP4"


def test_play_pause_toggle_se_reenvia_al_player(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    widget.toggle_play()
    assert widget.player._mpv.pause is False
    widget.toggle_play()
    assert widget.player._mpv.pause is True
