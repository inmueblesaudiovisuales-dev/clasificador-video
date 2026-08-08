# tests/test_player.py
from pathlib import Path

import pytest

from clasificador_video.player import MpvPlayer, QUALITY_PROFILES, SPEED_PROFILES


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


# --- F6 Task 1: lo que mpv ya sabe hacer y MpvPlayer no exponia -------------


def test_la_velocidad_se_le_pide_a_mpv():
    """Para juzgar un recorrido no hace falta verlo a velocidad real."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_speed(2.0)
    assert player._mpv.speed == 2.0
    assert player.speed == 2.0


def test_la_velocidad_arranca_en_uno():
    assert MpvPlayer(mpv_factory=FakeMpv).speed == 1.0


def test_una_velocidad_que_no_esta_en_la_lista_se_rechaza():
    """Mismo criterio que el selector de calidad: fallar fuerte y no dejar
    el reproductor en un estado que la UI no sabe mostrar."""
    with pytest.raises(ValueError):
        MpvPlayer(mpv_factory=FakeMpv).set_speed(3.0)


def test_los_perfiles_de_velocidad_son_los_tres_del_mockup():
    assert SPEED_PROFILES == (1.0, 2.0, 4.0)


def test_el_arranque_al_25_por_ciento_se_le_pide_a_mpv():
    """El principio de un recorrido siempre es la camara acomodandose. Se usa
    la opcion `start` y no un seek: mpv reporta la duracion de forma
    asincrona, y un seek justo despues de abrir llega antes de que exista."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_start_percent(25)
    assert player._mpv.start == "25%"


def test_arrancar_desde_el_principio_se_puede_pedir_igual():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_start_percent(0)
    assert player._mpv.start == "0%"


def test_un_porcentaje_de_arranque_fuera_de_rango_se_rechaza():
    """Un `start` de 120% deja a mpv en un estado que la app no sabe mostrar:
    mejor reventar aqui que abrir un clip en negro sin explicacion."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    with pytest.raises(ValueError):
        player.set_start_percent(120)
    with pytest.raises(ValueError):
        player.set_start_percent(-1)


def test_avanzar_y_retroceder_un_cuadro():
    """`,` y `.` son la convencion de Premiere y se usan para marcar in/out
    con precision."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.step_frame(1)
    player.step_frame(-1)
    assert player._mpv.commands == [("frame-step",), ("frame-back-step",)]


def test_avanzar_un_cuadro_pausa_la_reproduccion():
    """Avanzar cuadro a cuadro mientras corre no tiene sentido: mpv lo pausa
    solo, y el estado que reporta la app tiene que coincidir."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.play()
    player.step_frame(1)
    assert player.is_paused


def test_retroceder_un_cuadro_tambien_pausa():
    """mpv pausa con `frame-back-step` igual que con `frame-step`; si la app
    solo reflejara uno de los dos, el boton de play mostraria lo contrario de
    lo que hace el video."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.play()
    player.step_frame(-1)
    assert player.is_paused


def test_avanzar_cero_cuadros_no_le_manda_nada_a_mpv():
    """Estado limite: `step_frame(0)` no tiene direccion. Sin esta guarda
    caeria en `frame-back-step`, que retrocede -- lo contrario de no moverse."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.play()
    player.step_frame(0)
    assert player._mpv.commands == []
    assert not player.is_paused


def test_la_velocidad_sobrevive_al_cambio_de_clip():
    """Si al abrir el clip siguiente la velocidad volviera a 1x, la tecla `L`
    habria que apretarla en cada clip. Se verifico contra mpv real que la
    propiedad se conserva al cargar otro archivo."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_speed(4.0)
    player.open(Path("/shooting/C0013.MP4"))
    assert player.speed == 4.0
