# tests/test_player.py
from pathlib import Path

import pytest

from clasificador_video.player import MpvPlayer, SPEED_PROFILES


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
        # mpv implementa `frame-step` como "despausar, mostrar un cuadro,
        # volver a pausar": queda pausado SOLO. El doble lo imita para que un
        # test no pueda pasar con una implementacion que ademas escribe
        # `pause`, que contra mpv real aborta el paso (medido el 2026-08-08).
        if args and args[0] in ("frame-step", "frame-back-step"):
            self.pause = True


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


def test_avanzar_un_cuadro_usa_frame_step():
    """`.` es la convencion de Premiere y se usa para marcar in/out con
    precision. Adelante mpv es exacto y barato."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.step_frame(1)
    assert player._mpv.commands == [("frame-step",)]


def test_retroceder_un_cuadro_usa_un_seek_exacto_y_no_frame_back_step():
    """Medido contra mpv real (2026-08-08, FX30 a 59.94 fps):
    `frame-back-step` obliga a retroceder y redecodificar, y tarda ~0.25 s.
    A ritmo humano --una pulsacion cada 0.2 s-- CINCO pulsaciones
    retrocedieron UN cuadro: las que llegan mientras la anterior sigue en
    vuelo se pierden. Con el seek exacto, las mismas cinco dan cinco cuadros.
    """
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.step_frame(-1, fps=30.0)
    comando = player._mpv.commands[-1]
    assert comando[0] == "seek"
    assert comando[1] == pytest.approx(-1 / 30.0)
    assert comando[2:] == ("relative", "exact")
    assert not any(c[0] == "frame-back-step" for c in player._mpv.commands)


def test_retroceder_prefiere_los_fps_que_reporta_mpv():
    """El archivo manda: la app trae los fps de ffprobe al importar, pero el
    que decodifica es mpv. Un clip a 59.94 con la sesion diciendo 30 dejaria
    el paso al doble de largo."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.container_fps = 59.94
    player.step_frame(-1, fps=30.0)
    assert player._mpv.commands[-1][1] == pytest.approx(-1 / 59.94)


def test_retroceder_sin_fps_por_ningun_lado_no_divide_entre_cero():
    """Sesion restaurada sin fps y mpv que todavia no reporta el archivo."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.step_frame(-1, fps=None)
    assert player._mpv.commands[-1][1] < 0


def test_retroceder_pausa_ANTES_del_salto():
    """Al reves que `frame-step`: pausar antes de un seek es seguro --no lo
    aborta-- y evita que retroceder deje el video corriendo."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.play()
    player.step_frame(-1, fps=30.0)
    assert player.is_paused


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


def test_pasar_de_cuadro_no_le_escribe_pause_a_mpv():
    """Contra mpv real, escribir `pause = True` justo despues de `frame-step`
    ABORTA el paso: el cuadro no avanza. mpv implementa el comando como
    "despausar, mostrar un cuadro, volver a pausar", asi que la escritura le
    cae encima. Medido el 2026-08-08 con un clip de la FX30 a 59.94 fps: con
    la linea, tres pasos seguidos quedaron los tres en el mismo cuadro.

    Este test existe para que nadie la reponga "para que el estado quede
    consistente": el doble de pruebas ya imita a mpv y pausa solo.
    """
    escrituras = []

    class MpvQueRegistraPause(FakeMpv):
        # sin la emulacion de `command`: aqui se mide lo que escribe
        # MpvPlayer, no lo que haria mpv por su cuenta
        def command(self, *args):
            self.commands.append(args)

        @property
        def pause(self):
            return self._pause

        @pause.setter
        def pause(self, valor):
            self._pause = valor
            escrituras.append(valor)

    player = MpvPlayer(mpv_factory=MpvQueRegistraPause)
    escrituras.clear()          # el constructor escribe pause = True a proposito
    player.step_frame(1)
    assert escrituras == [], "step_frame no debe escribirle `pause` a mpv"
