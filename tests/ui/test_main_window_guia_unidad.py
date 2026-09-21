"""La guía por unidad (spec 2026-09-21): la pantalla ordena una unidad a la
vez y el orden aceptado se aplica a SU catálogo, no al activo del rail."""
import pytest

from clasificador_video import guia as logica
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    def __init__(self, **kwargs):
        self.pause = True
        self.time_pos = 0.0

    def play(self, path):
        pass

    def command(self, *args):
        pass


@pytest.fixture
def ventana(qtbot):
    w = MainWindow("Casa", RoomSelection(), video_factory=FakeMpv)
    qtbot.addWidget(w)
    w.unit_selection.add("Casa A")
    w.unit_selection.add("Casa B")
    w.room_selections["Casa A"] = RoomSelection()
    w.room_selections["Casa A"].add("Cocina")
    w.room_selections["Casa A"].add("Baño")
    w.room_selections["Casa B"] = RoomSelection()
    w.room_selections["Casa B"].add("Fachada")
    return w


def test_abrir_la_guia_lista_los_cuartos_de_cada_unidad(ventana):
    ventana._abrir_pantalla_de_guia()
    pantalla = ventana._pantalla_guia
    assert pantalla.unidad_actual() == "Casa A"
    assert pantalla.franja.cuartos() == ["Cocina", "Baño"]
    pantalla.seleccionar_unidad("Casa B")
    assert pantalla.franja.cuartos() == ["Fachada"]


def test_aceptar_orden_reordena_el_catalogo_de_esa_unidad(ventana):
    ventana._abrir_pantalla_de_guia()
    pantalla = ventana._pantalla_guia
    pantalla.seleccionar_unidad("Casa A")
    pantalla.agregar_a_columna("sociales", "Baño")
    pantalla.agregar_a_columna("sociales", "Cocina")
    pantalla.orden_aceptado.emit(pantalla.orden_final())

    assert ventana.room_selections["Casa A"].active_rooms() == ["Baño", "Cocina"]
    assert ventana.room_selections["Casa B"].active_rooms() == ["Fachada"]


def test_aceptar_sin_pre_ordenar_igual_guarda_la_guia(ventana):
    ventana._abrir_pantalla_de_guia()
    pantalla = ventana._pantalla_guia
    pantalla.agregar_a_columna("sociales", "Cocina")
    pantalla.orden_aceptado.emit(pantalla.orden_final())

    assert ventana._guias_por_unidad["Casa A"] is not None
    assert [r.cuarto for r in ventana._guias_por_unidad["Casa A"].lista] == [
        "Cocina", "Baño"]


def test_el_manifest_lleva_las_unidades_y_sus_ordenes(ventana):
    ventana._abrir_pantalla_de_guia()
    pantalla = ventana._pantalla_guia
    pantalla.seleccionar_unidad("Casa A")
    pantalla.agregar_a_columna("sociales", "Baño")
    pantalla.orden_aceptado.emit(pantalla.orden_final())

    guia = ventana._guia_para_el_manifest()
    assert guia.orden == []
    assert guia.unidades == [{"nombre": "Casa A", "orden": ["Baño", "Cocina"]}]


def test_guardar_y_reabrir_conserva_las_guias_por_unidad(ventana):
    ventana._abrir_pantalla_de_guia()
    pantalla = ventana._pantalla_guia
    pantalla.agregar_a_columna("sociales", "Baño")
    pantalla.orden_aceptado.emit(pantalla.orden_final())

    datos = ventana._guias_por_unidad_para_la_sesion()
    otra = MainWindow("Casa", RoomSelection(), video_factory=FakeMpv)
    otra.restaurar_guias(datos)
    assert [r.cuarto for r in otra._guias_por_unidad["Casa A"].lista] == [
        "Baño", "Cocina"]


def test_guia_vieja_se_revisa_por_unidad(ventana):
    ventana.restaurar_guias({
        "Casa A": {"orden": ["Cocina"], "cuartos_de_entonces": ["Cocina"]},
    })
    assert ventana.guia_quedo_vieja("Casa A")
    assert "Casa A" in ventana.aviso_de_guia_vieja()
    assert not ventana.guia_quedo_vieja("Casa B")


def test_sin_unidades_el_manifest_es_la_lista_plana_de_siempre(ventana):
    ventana.restaurar_guias({"": {"orden": ["Sala"], "cuartos_de_entonces": ["Sala"]}})
    guia = ventana._guia_para_el_manifest()
    assert guia.orden == ["Sala"]
    assert guia.unidades == []
