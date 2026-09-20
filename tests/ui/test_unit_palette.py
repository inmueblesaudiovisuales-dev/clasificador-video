# tests/ui/test_unit_palette.py
"""La paleta de unidades: misma mecanica de buscar/crear que RoomPalette,
pero elegir NO cierra la paleta -- se queda activa hasta elegir otra o
cerrarla a mano (spec 2026-09-20 §3)."""
import pytest

from clasificador_video.ui.unit_palette import UnitPalette


@pytest.fixture
def paleta(qtbot):
    p = UnitPalette()
    qtbot.addWidget(p)
    return p


def test_elegir_una_unidad_no_cierra_la_paleta(paleta, qtbot):
    paleta.abrir(["Casa A", "Casa B"], {})
    recibidos = []
    paleta.unit_activated.connect(recibidos.append)
    paleta._activa = 0
    paleta.confirmar()
    assert recibidos == ["Casa A"]
    assert not paleta.isHidden()


def test_crear_una_unidad_no_cierra_la_paleta(paleta, qtbot):
    paleta.abrir([], {})
    paleta.input.setText("Casa Nueva")
    recibidos = []
    paleta.unit_created.connect(recibidos.append)
    paleta.confirmar()
    assert recibidos == ["Casa Nueva"]
    assert not paleta.isHidden()


def test_escape_si_cierra(paleta, qtbot):
    from PySide6.QtCore import Qt
    paleta.abrir(["Casa A"], {})
    qtbot.keyClick(paleta, Qt.Key.Key_Escape)
    assert paleta.isHidden()
