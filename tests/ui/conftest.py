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
