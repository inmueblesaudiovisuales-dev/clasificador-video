# tests/conftest.py
import pytest


@pytest.fixture(autouse=True)
def sin_log_de_fila_de_proxies(monkeypatch):
    """El registro TEMPORAL de la fila de proxies (main_window.py, ver el
    comentario junto a `_log_fila_de_proxies`) escribe en
    `~/.clasificador_video/`, la carpeta real de Bruno -- sin esto, cada
    corrida de la suite le dejaria ahi un archivo que nadie pidio."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window._preparar_log_de_fila_de_proxies",
        lambda: None,
        raising=False,
    )
    yield


@pytest.fixture(autouse=True)
def preferencias_de_prueba(monkeypatch):
    """Ningun test depende de lo que haya guardado en la maquina real donde
    corre la suite --`preferencias.modo_economico()` sin argumentos lee
    `~/.clasificador_video/preferencias.json`-- y el default de la suite es
    modo NORMAL: la mayoria de los tests de miniaturas datan de antes del
    modo economico y esperan su tamaño de tira y paralelismo de siempre.
    Los tests que SI quieren probar el modo economico lo prenden ellos
    mismos, parchando `preferencias.modo_economico` encima de este.
    """
    from clasificador_video import preferencias
    monkeypatch.setattr(preferencias, "modo_economico", lambda *a, **k: False)
    yield


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
