# tests/ui/conftest.py
import pytest

from clasificador_video.ui.theme import build_stylesheet


@pytest.fixture(scope="session", autouse=True)
def hoja_de_estilos(qapp):
    """Aplica la hoja de estilos de la app a TODOS los tests de interfaz.

    No es cosmetica: el QSS cambia los tamaños. Sin el, Qt le da a cada
    QPushButton el ancho minimo de plataforma --80 px en macOS-- y el
    selector de calidad pasa de 149 a 320 px. O sea que un test que mide
    posiciones sin la hoja puesta esta midiendo una app que no existe.

    Costo real de no tenerlo: `pytest tests/ui/test_video_stage.py` a solas
    daba DOS tests en rojo, y en la suite completa pasaban -- porque algun
    otro archivo habia aplicado la hoja antes. Un test que depende del
    orden es un test que no dice la verdad.

    Peor todavia: midiendo sin la hoja se «encontro» que el control de
    velocidad quedaba en x = -165, y era un espejismo del arnes.
    """
    # de sesion, no por test: `setStyleSheet` obliga a repolir todos los
    # widgets vivos y es de lo mas caro que hay en Qt (por eso el codigo de
    # la app nunca lo llama si el estilo no cambio). Por test, la suite
    # pasaba de 8 s a mas de dos minutos.
    qapp.setStyleSheet(build_stylesheet())
    yield

@pytest.fixture(autouse=True)
def sin_dialogos_que_bloqueen(monkeypatch):
    """Ningun `QMessageBox` modal detiene la suite.

    Hizo falta cuando la app empezo a preguntar «este bin no tiene proxies,
    ¿te los creo primero?» al importar: `QMessageBox.question` abre un
    dialogo modal y espera una respuesta que en una corrida sin pantalla no
    llega nunca. La suite se colgaba a la mitad, sin decir en que test.

    La respuesta por defecto es **No**: es la que deja el comportamiento de
    siempre --las portadas se piden al importar-- para los ~300 tests que no
    vienen a probar esto. El que SI lo prueba vuelve a parchear `question`
    con un `Yes`.

    `information` y `warning` tambien: varios tests ya los parcheaban uno por
    uno, y el que se olvidaba colgaba la suite igual.
    """
    from PySide6.QtWidgets import QMessageBox
    # `exec()` es el de los dialogos con botones propios --el de «enlazar o
    # crear proxies»--, que no pasan por los estaticos de abajo. Devolver
    # sin abrir deja `clickedButton()` en None, y la app lo lee como «ahora
    # no»: el default correcto para un test que no vino a probar el dialogo.
    monkeypatch.setattr(QMessageBox, "exec", lambda self, *a, **k: 0)
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    yield
