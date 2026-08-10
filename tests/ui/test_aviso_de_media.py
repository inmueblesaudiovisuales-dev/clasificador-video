# tests/ui/test_aviso_de_media.py
"""La barra de media faltante, por su cuenta: qué dice y qué botones tiene."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from clasificador_video.ui.aviso_de_media import (
    ACCION_PROXIES,
    TONO_ALERTA,
    TONO_OK,
    AvisoDeMedia,
    Renglon,
)


def _por_nombre(widget, nombre):
    return [w for w in widget.findChildren(QWidget) if w.objectName() == nombre]


@pytest.fixture
def aviso(qtbot):
    widget = AvisoDeMedia()
    qtbot.addWidget(widget)
    return widget


def test_sin_renglones_no_hay_nada_que_decir(aviso):
    """La barra NO se esconde sola: esa regla vive entera en la ventana,
    que es la unica que sabe si esta el modo solo video."""
    aviso.poner([])

    assert not aviso.tiene_avisos()
    assert aviso.text() == ""
    assert _por_nombre(aviso, "avisoFila") == []


def test_dice_el_bin_y_lo_que_le_pasa(aviso):
    aviso.poner([Renglon("Dron", "23 clips no se encuentran.", boton="Buscar…")])

    assert aviso.tiene_avisos()
    assert aviso.text() == "Dron — 23 clips no se encuentran."


def test_un_renglon_por_bin(aviso):
    aviso.poner([
        Renglon("Dron", "23 clips no se encuentran.", boton="Buscar…"),
        Renglon("Sony FX30", "109 clips no se encuentran.", boton="Buscar…"),
    ])

    assert aviso.text().splitlines() == [
        "Dron — 23 clips no se encuentran.",
        "Sony FX30 — 109 clips no se encuentran.",
    ]


def test_poner_de_nuevo_no_deja_los_renglones_viejos(aviso):
    """Se cuentan los HIJOS, no el texto: `text()` sale de la lista de
    renglones, asi que con un `_limpiar` que no borrara ni un widget este
    test seguiria verde mientras las filas viejas se apilan a la vista --
    que es justo el fallo que `_limpiar` existe para evitar."""
    aviso.poner([
        Renglon("Dron", "23 clips no se encuentran.", boton="Buscar…"),
        Renglon("Sony", "9 clips no se encuentran.", boton="Buscar…"),
    ])
    assert len(_por_nombre(aviso, "avisoFila")) == 2

    aviso.poner([Renglon("Dron", "23 clips reconectados.", tono=TONO_OK)])

    assert len(_por_nombre(aviso, "avisoFila")) == 1
    assert len(_por_nombre(aviso, "avisoBuscar")) == 0
    assert aviso.text() == "Dron — 23 clips reconectados."


def test_el_boton_dice_de_que_bin_es_y_que_hay_que_buscar(aviso, qtbot):
    aviso.poner([
        Renglon("Dron", "23 clips no se encuentran.", boton="Buscar…"),
        Renglon("Dron", "2 clips quedaron sin proxy.", boton="Buscar proxies…",
                accion=ACCION_PROXIES),
    ])
    botones = _por_nombre(aviso, "avisoBuscar")
    assert [b.text() for b in botones] == ["Buscar…", "Buscar proxies…"]

    with qtbot.waitSignal(aviso.buscar_pedido) as señal:
        qtbot.mouseClick(botones[1], Qt.MouseButton.LeftButton)

    assert señal.args == ["Dron", ACCION_PROXIES]


def test_sin_buscar_no_hay_boton(aviso):
    """El renglón de «ya se reconectaron» no ofrece volver a buscar: no hay
    nada que buscar, y un botón ahí invita a rehacer lo que ya salió bien."""
    aviso.poner([Renglon("Dron", "23 clips reconectados.", tono=TONO_OK)])

    assert _por_nombre(aviso, "avisoBuscar") == []


def test_el_tono_viaja_como_propiedad_para_que_lo_pinte_el_qss(aviso):
    aviso.poner([Renglon("Dron", "2 clips no coinciden.", tono=TONO_ALERTA)])

    textos = _por_nombre(aviso, "avisoTexto")
    assert [t.property("tono") for t in textos] == [TONO_ALERTA]


def test_el_widget_nunca_se_muestra_ni_se_esconde_solo(aviso):
    """La visibilidad NO es del widget: es de la ventana, la única que sabe
    si está el modo solo video, donde la barra no puede aparecer aunque
    tenga mucho que decir. Con la regla partida en dos, poner renglones la
    traía de vuelta encima del video a pantalla completa.
    """
    aviso.hide()

    aviso.poner([Renglon("Dron", "23 clips no se encuentran.", boton="Buscar…")])

    assert aviso.isHidden()

    aviso.show()
    aviso.poner([])

    assert not aviso.isHidden()
