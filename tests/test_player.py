# tests/test_player.py
from pathlib import Path

from clasificador_video.player import MpvPlayer, QUALITY_PROFILES


class FakeMpv:
    """Sustituto de mpv.MPV para probar MpvPlayer sin abrir un reproductor real."""

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


def test_mpv_player_se_inicializa_con_hwdec_videotoolbox():
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert player._mpv.init_kwargs["hwdec"] == "videotoolbox"


def test_open_carga_el_archivo():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.open(Path("/shooting/C0012.MP4"))
    assert player._mpv.loaded_path == "/shooting/C0012.MP4"


def test_play_pause_alterna_el_estado():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.play()
    assert player._mpv.pause is False
    player.pause()
    assert player._mpv.pause is True


def test_set_quality_aplica_el_perfil_conocido():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_quality("1/2")
    assert player._mpv.vid_scale == QUALITY_PROFILES["1/2"]


def test_set_quality_perfil_desconocido_lanza_error_claro():
    player = MpvPlayer(mpv_factory=FakeMpv)
    try:
        player.set_quality("1/16")
        assert False, "debio lanzar ValueError"
    except ValueError as e:
        assert "1/16" in str(e)


def test_mark_in_guarda_el_frame_actual_en_segundos_convertido_por_fps():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = 2.0
    player.mark_in(fps=60.0)
    assert player.in_frame == 120


def test_mark_out_guarda_el_frame_actual():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = 5.0
    player.mark_out(fps=60.0)
    assert player.out_frame == 300


def test_clear_in_out_resetea_ambos():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = 2.0
    player.mark_in(fps=60.0)
    player.mark_out(fps=60.0)
    player.clear_in_out()
    assert player.in_frame is None
    assert player.out_frame is None
