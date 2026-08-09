# tests/test_filters.py
from pathlib import Path

from clasificador_video.filters import FilterState, cola, contar
from clasificador_video.manifest import Clip


def _clip(n, cuarto=None, flag="none"):
    return Clip(orden=n, ruta=Path(f"/tmp/C{n:04d}.MP4"),
                categoria_path=[cuarto] if cuarto else [], fps=30.0, flag=flag)


CLIPS = [
    _clip(1, "Cocina", "pick"),
    _clip(2, "Recámara 1"),
    _clip(3, None, "reject"),
    _clip(4, None),
]


# --- los dos grupos del mockup ---------------------------------------------


def test_sin_filtros_la_cola_es_todo_en_orden():
    assert cola(CLIPS, FilterState()) == [0, 1, 2, 3]


def test_sin_clasificar_deja_solo_los_que_no_tienen_cuarto():
    assert cola(CLIPS, FilterState(mostrar="sin_clasificar")) == [2, 3]


def test_clasificados_deja_solo_los_que_si():
    assert cola(CLIPS, FilterState(mostrar="clasificados")) == [0, 1]


def test_solo_picks():
    assert cola(CLIPS, FilterState(estado="solo_picks")) == [0]


def test_ocultar_rejects_saca_los_descartados():
    assert cola(CLIPS, FilterState(estado="ocultar_rejects")) == [0, 1, 3]


def test_sin_marcar_deja_los_que_no_son_pick_ni_reject():
    assert cola(CLIPS, FilterState(estado="sin_marcar")) == [1, 3]


def test_los_dos_grupos_se_combinan():
    estado = FilterState(mostrar="sin_clasificar", estado="ocultar_rejects")
    assert cola(CLIPS, estado) == [3]


# --- busqueda ---------------------------------------------------------------


def test_la_busqueda_encuentra_por_nombre_de_archivo():
    assert cola(CLIPS, FilterState(busqueda="C0002")) == [1]


def test_la_busqueda_encuentra_por_nombre_de_cuarto():
    assert cola(CLIPS, FilterState(busqueda="cocina")) == [0]


def test_la_busqueda_ignora_acentos():
    """En un teclado apurado nadie escribe `Recámara` con acento."""
    assert cola(CLIPS, FilterState(busqueda="recamara")) == [1]
    assert cola(CLIPS, FilterState(busqueda="RECÁMARA")) == [1]


def test_la_busqueda_en_blanco_no_filtra():
    assert cola(CLIPS, FilterState(busqueda="   ")) == [0, 1, 2, 3]


def test_la_busqueda_se_combina_con_los_chips():
    assert cola(CLIPS, FilterState(mostrar="clasificados", busqueda="reca")) == [1]


# --- conteos y estado -------------------------------------------------------


def test_los_conteos_alimentan_los_numeros_de_los_chips():
    c = contar(CLIPS)
    assert c["todos"] == 4
    assert c["sin_clasificar"] == 2
    assert c["clasificados"] == 2
    assert c["solo_picks"] == 1
    assert c["ocultar_rejects"] == 1     # cuantos SE OCULTAN: el chip dice −1
    assert c["sin_marcar"] == 2


def test_los_conteos_de_una_sesion_vacia_son_cero():
    assert contar([])["todos"] == 0


def test_un_estado_sin_filtros_lo_dice():
    """De esto depende que el visor diga `87 / 128` o `3 de 12 en la cola`."""
    assert FilterState().esta_filtrando() is False
    assert FilterState(mostrar="sin_clasificar").esta_filtrando() is True
    assert FilterState(estado="solo_picks").esta_filtrando() is True
    assert FilterState(busqueda="x").esta_filtrando() is True
    assert FilterState(busqueda="   ").esta_filtrando() is False


def test_la_cola_nunca_reordena_los_clips():
    """Es el orden de rodaje: reordenar romperia la nocion de «el anterior»,
    que es de lo que vive la tecla S de la F7."""
    indices = cola(CLIPS, FilterState(mostrar="clasificados"))
    assert indices == sorted(indices)


def test_un_valor_desconocido_no_filtra_nada_en_silencio():
    """Si un chip nuevo llega con un nombre que el modulo no conoce, es mejor
    no filtrar que esconder clips sin que nadie sepa por que."""
    assert cola(CLIPS, FilterState(mostrar="lo_que_sea")) == [0, 1, 2, 3]


# --- F7 Task 9: el cuarto estado, destacado ---------------------------------


def test_solo_destacados():
    clips = [_clip(1, flag="destacado"), _clip(2, flag="pick"), _clip(3)]
    assert cola(clips, FilterState(estado="solo_destacados")) == [0]


def test_solo_picks_no_incluye_a_los_destacados():
    """Son estados distintos: `destacado` es LA toma del cuarto, y el chip de
    picks dice cuantos picks hay, no cuantos hay marcados de algun modo."""
    clips = [_clip(1, flag="destacado"), _clip(2, flag="pick")]
    assert cola(clips, FilterState(estado="solo_picks")) == [1]


def test_ocultar_rejects_no_esconde_destacados():
    clips = [_clip(1, flag="destacado"), _clip(2, flag="reject")]
    assert cola(clips, FilterState(estado="ocultar_rejects")) == [0]


def test_sin_marcar_no_cuenta_a_los_destacados():
    """`sin_marcar` preguntaba solo por pick y reject: un destacado se colaba
    en «lo que falta juzgar» aunque sea el clip MAS juzgado del cuarto."""
    clips = [_clip(1, flag="destacado"), _clip(2)]
    assert cola(clips, FilterState(estado="sin_marcar")) == [1]


def test_el_conteo_de_destacados_y_el_de_sin_marcar():
    clips = [_clip(1, flag="destacado"), _clip(2, flag="pick"),
             _clip(3, flag="reject"), _clip(4)]
    conteos = contar(clips)
    assert conteos["solo_destacados"] == 1
    assert conteos["solo_picks"] == 1
    assert conteos["sin_marcar"] == 1
