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


def test_mpv_player_se_inicializa_con_vo_libmpv_para_el_api_de_render():
    """vo=libmpv habilita el modo render-API de mpv (MpvRenderContext), la
    via soportada oficialmente para embeber en Qt. El intento anterior con
    `wid` abria una ventana de mpv aparte en vez de embeberse -- MpvPlayer
    ya no acepta `wid`.
    """
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert player._mpv.init_kwargs["vo"] == "libmpv"


def test_mpv_player_se_inicializa_con_keep_open_para_conservar_el_ultimo_frame():
    """Los clips de prueba duran 2-6s; sin keep_open mpv descarga el
    archivo al llegar a EOF y el widget vuelve a quedar negro.
    """
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert player._mpv.init_kwargs["keep_open"] == "always"


def test_mpv_handle_expone_la_instancia_real_de_mpv():
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert player.mpv_handle is player._mpv


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


def test_position_expone_time_pos_del_mpv():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = 3.5
    assert player.position == 3.5


def test_position_sin_time_pos_devuelve_cero():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = None
    assert player.position == 0.0


def test_duration_expone_duration_del_mpv():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.duration = 12.5
    assert player.duration == 12.5


def test_duration_sin_atributo_en_el_doble_devuelve_cero():
    """FakeMpv (y los dobles de pruebas de mas arriba en el archivo) no
    siempre definen `duration` -- no debe lanzar AttributeError."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert player.duration == 0.0


def test_toggle_alterna_play_y_pause():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.toggle()          # empieza en pause=True (FakeMpv)
    assert player._mpv.pause is False
    player.toggle()
    assert player._mpv.pause is True


def test_seek_setea_time_pos():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.duration = 60.0
    player.seek(15.0)
    assert player._mpv.time_pos == 15.0


def test_seek_clampea_a_cero_si_es_negativo():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.duration = 60.0
    player.seek(-5.0)
    assert player._mpv.time_pos == 0.0


def test_seek_clampea_a_duration_si_excede():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.duration = 60.0
    player.seek(999.0)
    assert player._mpv.time_pos == 60.0


def test_is_paused_refleja_estado_del_mpv():
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert player.is_paused is True
    player.play()
    assert player.is_paused is False


def test_marcar_in_recien_abierto_el_clip_no_revienta():
    """Bug real: `position` y `duration` se protegen de que mpv todavia no
    reporte `time_pos` --lo dice su propio comentario-- pero `mark_in` lo
    leia crudo. Apretar `I` apenas abierto el clip tiraba
    `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'`.
    """
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = None
    assert player.mark_in(fps=30.0) == 0
    assert player.mark_out(fps=30.0) == 0
