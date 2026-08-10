# tests/ui/test_aviso_de_media.py
"""La barra de media faltante, por su cuenta: qué dice y qué botones tiene."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from clasificador_video.ui.aviso_de_media import (
    TONO_ALERTA,
    TONO_OK,
    AvisoDeMedia,
    Renglon,
)


@pytest.fixture
def aviso(qtbot):
    widget = AvisoDeMedia()
    qtbot.addWidget(widget)
    return widget


def test_sin_renglones_la_barra_no_se_ve(aviso):
    aviso.poner([])

    assert aviso.isHidden()
    assert not aviso.tiene_avisos()
    assert aviso.text() == ""


def test_dice_el_bin_y_lo_que_le_pasa(aviso):
    aviso.poner([Renglon("Dron", "23 clips no se encuentran.", con_buscar=True)])

    assert aviso.tiene_avisos()
    assert aviso.text() == "Dron — 23 clips no se encuentran."


def test_un_renglon_por_bin(aviso):
    aviso.poner([
        Renglon("Dron", "23 clips no se encuentran.", con_buscar=True),
        Renglon("Sony FX30", "109 clips no se encuentran.", con_buscar=True),
    ])

    assert aviso.text().splitlines() == [
        "Dron — 23 clips no se encuentran.",
        "Sony FX30 — 109 clips no se encuentran.",
    ]


def test_poner_de_nuevo_no_deja_los_renglones_viejos(aviso):
    aviso.poner([Renglon("Dron", "23 clips no se encuentran.")])

    aviso.poner([Renglon("Dron", "23 clips reconectados.", tono=TONO_OK)])

    assert aviso.text() == "Dron — 23 clips reconectados."


def _por_nombre(widget, nombre):
    return [w for w in widget.findChildren(QWidget) if w.objectName() == nombre]


def test_el_boton_de_buscar_dice_de_que_bin_es(aviso, qtbot):
    aviso.poner([Renglon("Dron", "23 clips no se encuentran.", con_buscar=True)])
    botones = _por_nombre(aviso, "avisoBuscar")
    assert len(botones) == 1

    with qtbot.waitSignal(aviso.buscar_pedido) as señal:
        qtbot.mouseClick(botones[0], Qt.MouseButton.LeftButton)

    assert señal.args == ["Dron"]


def test_sin_buscar_no_hay_boton(aviso):
    """El renglón de «ya se reconectaron» no ofrece volver a buscar: no hay
    nada que buscar, y un botón ahí invita a rehacer lo que ya salió bien."""
    aviso.poner([Renglon("Dron", "23 clips reconectados.", tono=TONO_OK)])

    assert _por_nombre(aviso, "avisoBuscar") == []


def test_el_tono_viaja_como_propiedad_para_que_lo_pinte_el_qss(aviso):
    aviso.poner([Renglon("Dron", "2 clips no coinciden.", tono=TONO_ALERTA)])

    textos = _por_nombre(aviso, "avisoTexto")
    assert [t.property("tono") for t in textos] == [TONO_ALERTA]
