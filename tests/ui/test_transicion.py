# tests/ui/test_transicion.py
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QLabel, QWidget

from clasificador_video.ui.transicion import TransicionDeTarjeta


def _ventana_con_tarjeta(qtbot):
    ventana = QWidget()
    ventana.resize(800, 600)
    tarjeta = QLabel("tarjeta", ventana)
    tarjeta.setGeometry(500, 400, 150, 267)
    qtbot.addWidget(ventana)
    ventana.show()
    return ventana, tarjeta


def _copias(ventana, tarjeta):
    return [
        h for h in ventana.findChildren(QLabel)
        if h is not tarjeta and h.pixmap() is not None and not h.pixmap().isNull()
    ]


def test_anima_una_copia_y_no_la_tarjeta(qtbot):
    """Animar la tarjeta de verdad la sacaria de la hoja, que ademas se
    re-acomoda debajo."""
    ventana, tarjeta = _ventana_con_tarjeta(qtbot)
    antes = tarjeta.geometry()

    transicion = TransicionDeTarjeta(ventana)
    assert transicion.lanzar(tarjeta, QRect(10, 10, 400, 500))

    assert transicion.corriendo()
    assert tarjeta.geometry() == antes
    assert len(_copias(ventana, tarjeta)) == 1


def test_una_tarjeta_fuera_de_la_vista_no_se_anima(qtbot):
    """Dentro del area con scroll, una tarjeta que quedo abajo esta a
    cientos de pixeles fuera de la ventana --medido: y = 3596 con 128
    clips-- y animar desde ahi seria una raya cruzando la pantalla."""
    ventana, tarjeta = _ventana_con_tarjeta(qtbot)
    tarjeta.move(500, 3596)

    transicion = TransicionDeTarjeta(ventana)
    assert not transicion.lanzar(tarjeta, QRect(10, 10, 400, 500))
    assert not transicion.corriendo()
    assert _copias(ventana, tarjeta) == []


def test_sin_destino_no_se_anima(qtbot):
    """Pasa si el visor todavia no tiene tamaño."""
    ventana, tarjeta = _ventana_con_tarjeta(qtbot)
    transicion = TransicionDeTarjeta(ventana)
    assert not transicion.lanzar(tarjeta, QRect())


def test_una_transicion_nueva_cancela_la_anterior(qtbot):
    """`⇥` repetido rapido: seis tarjetas volando a la vez no significan
    nada."""
    ventana, tarjeta = _ventana_con_tarjeta(qtbot)
    transicion = TransicionDeTarjeta(ventana)

    for _ in range(6):
        transicion.lanzar(tarjeta, QRect(10, 10, 400, 500))

    assert len(_copias(ventana, tarjeta)) == 1


def test_al_terminar_no_queda_nada_colgando(qtbot):
    ventana, tarjeta = _ventana_con_tarjeta(qtbot)
    transicion = TransicionDeTarjeta(ventana)
    transicion.lanzar(tarjeta, QRect(10, 10, 400, 500))

    qtbot.waitUntil(lambda: not transicion.corriendo(), timeout=3000)
    qtbot.wait(50)

    assert _copias(ventana, tarjeta) == []


def test_cancelar_sin_nada_corriendo_no_truena(qtbot):
    ventana, _ = _ventana_con_tarjeta(qtbot)
    TransicionDeTarjeta(ventana).cancelar()
