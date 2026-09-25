from pathlib import Path

import pytest

from clasificador_video import preferencias as mod


@pytest.fixture(autouse=True)
def sin_el_parche_global(monkeypatch):
    """Este archivo prueba `importacion_rapida_pregunta_antes` DE VERDAD: el
    autouse de `conftest.py` la reemplaza por un `lambda: False` para el
    resto de la suite, y aqui es justo lo que se quiere probar."""
    monkeypatch.undo()
    yield


def test_un_archivo_roto_devuelve_el_default(tmp_path: Path):
    destino = tmp_path / "preferencias.json"
    destino.write_text("{esto no es json", encoding="utf-8")
    assert mod.importacion_rapida_pregunta_antes(destino) is False


def test_sin_archivo_importacion_rapida_pregunta_antes_es_falso(tmp_path: Path):
    # Por default arranca sola -- Bruno lo pidió así al construir el flujo.
    assert mod.importacion_rapida_pregunta_antes(tmp_path / "no-existe.json") is False


def test_guardar_y_leer_importacion_rapida_pregunta_antes(tmp_path: Path):
    destino = tmp_path / "preferencias.json"
    mod.guardar_importacion_rapida_pregunta_antes(True, destino)
    assert mod.importacion_rapida_pregunta_antes(destino) is True


def test_carpeta_raiz_icloud_vacia_por_defecto(tmp_path):
    ruta = tmp_path / "preferencias.json"
    assert mod.carpeta_raiz_icloud(ruta) is None


def test_guardar_y_leer_carpeta_raiz_icloud(tmp_path):
    ruta = tmp_path / "preferencias.json"
    carpeta = tmp_path / "01. Proyectos 2026 IAV y PI"

    mod.guardar_carpeta_raiz_icloud(carpeta, ruta)

    assert mod.carpeta_raiz_icloud(ruta) == carpeta
