# tests/conftest.py
import pytest


@pytest.fixture(autouse=True)
def sin_miniaturas_de_verdad(monkeypatch):
    """Ningún test lanza mpv por accidente.

    La extracción de miniaturas abre un mpv por clip y espera hasta 15 s
    por cada uno de los 12 cuadros. Un solo test que la dispare sin querer
    --restaurar una sesión, importar una carpeta— deja procesos corriendo
    que se llevan la suite de 12 segundos a más de tres minutos. Ya pasó.

    Los tests que SÍ quieren mirar la extracción (`tests/test_thumbnails.py`)
    llaman a las funciones directas del módulo, que esto no toca. Y los que
    necesitan espiar qué archivo se pidió vuelven a parchear encima.
    """
    for nombre in ("extract_thumbnail_strip", "extract_thumbnail"):
        monkeypatch.setattr(
            f"clasificador_video.ui.main_window.{nombre}",
            lambda *a, **k: [],
            raising=False,
        )
    yield
