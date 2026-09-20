"""_unidad_de / _cuarto_de: el largo del categoria_path decide, no una
posicion fija. Sin unidad es [cuarto]; con unidad es [unidad, cuarto] --
nunca hay un tercer nivel, los subcuartos murieron en la F3."""
import json

import pytest

from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    """Mismo doble que el resto de tests de la ventana: sin el, cada
    ventana enciende un mpv de verdad, con sus hilos, para nada."""

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        pass


@pytest.fixture
def main_window(qtbot):
    window = MainWindow(project_name="Casa Jardin", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    qtbot.addWidget(window)
    return window


def test_cuarto_de_sin_unidad():
    assert MainWindow._cuarto_de(["Cocina"]) == "Cocina"


def test_cuarto_de_con_unidad():
    assert MainWindow._cuarto_de(["Casa A", "Cocina"]) == "Cocina"


def test_cuarto_de_vacio():
    assert MainWindow._cuarto_de([]) is None


def test_unidad_de_sin_unidad():
    assert MainWindow._unidad_de(["Cocina"]) is None


def test_unidad_de_con_unidad():
    assert MainWindow._unidad_de(["Casa A", "Cocina"]) == "Casa A"


def test_unidad_de_vacio():
    assert MainWindow._unidad_de([]) is None


def test_room_selection_es_el_catalogo_sin_unidad_por_default(main_window):
    main_window.room_selections[""].add("Cocina")
    assert main_window.room_selection.active_rooms() == ["Cocina"]


def test_activar_unidad_cambia_el_alias_room_selection(main_window):
    main_window.unit_selection.add("Casa A")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections["Casa A"].add("Cocina A")
    main_window._activar_unidad("Casa A")
    assert main_window.room_selection.active_rooms() == ["Cocina A"]
    assert main_window._unidad_activa == "Casa A"


def test_activar_unidad_crea_el_catalogo_si_no_existia(main_window):
    main_window.unit_selection.add("Casa B")
    main_window._activar_unidad("Casa B")
    assert main_window.room_selections["Casa B"].active_rooms() == []
    assert main_window.room_selection is main_window.room_selections["Casa B"]


def test_desactivar_unidad_vuelve_al_catalogo_sin_unidad(main_window):
    main_window.room_selections[""].add("Cocina")
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window._activar_unidad(None)
    assert main_window.room_selection.active_rooms() == ["Cocina"]
    assert main_window._unidad_activa is None


def test_guardar_y_reabrir_conserva_unidades_y_sus_cuartos(qtbot, tmp_path, main_window):
    from clasificador_video.app import abrir_proyecto

    main_window.session_path = tmp_path / "p.cvproj"
    main_window.unit_selection.add("Casa A")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections["Casa A"].add("Cocina")
    main_window._write_autosave_now()
    assert main_window._autosave_pool.waitForDone(2000)

    reabierta = abrir_proyecto(main_window.session_path, video_factory=FakeMpv,
                               recientes_path=tmp_path / "r.json")
    qtbot.addWidget(reabierta)

    assert reabierta.unit_selection.active_rooms() == ["Casa A"]
    assert reabierta.room_selections["Casa A"].active_rooms() == ["Cocina"]
    assert (reabierta.room_selection.active_rooms()
            == reabierta.room_selections[""].active_rooms())
