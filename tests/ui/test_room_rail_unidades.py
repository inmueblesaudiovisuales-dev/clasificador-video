# tests/ui/test_room_rail_unidades.py
"""El rail agrupa por unidad. Sin ninguna unidad en el proyecto, se ve
exactamente como siempre -- una sola banda implicita, sin encabezado."""
import pytest

from clasificador_video.ui.room_rail import RoomRail


@pytest.fixture
def rail(qtbot):
    r = RoomRail()
    qtbot.addWidget(r)
    return r


def test_sin_unidades_se_comporta_como_antes(rail):
    rail.set_rooms_agrupados(
        unidades=[], rooms_por_unidad={"": ["Cocina", "Baño"]},
        counts={("", "Cocina"): 3, ("", "Baño"): 1},
    )
    assert [f.nombre for f in rail.rows] == ["Cocina", "Baño"]


def test_con_unidades_hay_una_banda_por_unidad(rail):
    rail.set_rooms_agrupados(
        unidades=["Casa A", "Casa B"],
        rooms_por_unidad={
            "": ["Sin migrar"],
            "Casa A": ["Cocina"],
            "Casa B": ["Cocina", "Baño"],
        },
        counts={},
    )
    assert [b.nombre for b in rail.unit_bands] == ["Sin unidad", "Casa A", "Casa B"]
    assert [f.nombre for f in rail.rows_por_unidad["Casa A"]] == ["Cocina"]
    assert [f.nombre for f in rail.rows_por_unidad["Casa B"]] == ["Cocina", "Baño"]


def test_bloque_sin_unidad_no_aparece_si_esta_vacio(rail):
    rail.set_rooms_agrupados(
        unidades=["Casa A"], rooms_por_unidad={"": [], "Casa A": ["Cocina"]},
        counts={},
    )
    assert [b.nombre for b in rail.unit_bands] == ["Casa A"]
