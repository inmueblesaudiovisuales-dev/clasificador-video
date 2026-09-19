from pathlib import Path

import pytest

from clasificador_video import preferencias as mod


@pytest.fixture(autouse=True)
def sin_el_parche_global(monkeypatch):
    """Este archivo prueba `modo_economico` DE VERDAD: el autouse de
    `conftest.py` la reemplaza por un `lambda: False` para el resto de la
    suite, y aqui es justo lo que se quiere probar."""
    monkeypatch.undo()
    yield


def test_sin_archivo_modo_economico_es_verdadero(tmp_path: Path):
    # La primera vez no hay preferencias guardadas, y eso no es un error:
    # el default es economico, porque la app no sabe en que Mac corre.
    assert mod.modo_economico(tmp_path / "no-existe.json") is True


def test_guardar_y_leer_modo_economico(tmp_path: Path):
    destino = tmp_path / "preferencias.json"
    mod.guardar_modo_economico(True, destino)
    assert mod.modo_economico(destino) is True


def test_guardar_false_tambien_se_lee(tmp_path: Path):
    destino = tmp_path / "preferencias.json"
    mod.guardar_modo_economico(True, destino)
    mod.guardar_modo_economico(False, destino)
    assert mod.modo_economico(destino) is False


def test_un_archivo_roto_devuelve_el_default(tmp_path: Path):
    destino = tmp_path / "preferencias.json"
    destino.write_text("{esto no es json", encoding="utf-8")
    assert mod.modo_economico(destino) is True


def test_carpeta_de_proyectos_premiere_vacia_por_defecto(tmp_path):
    ruta = tmp_path / "preferencias.json"
    assert mod.carpeta_de_proyectos_premiere(ruta) is None


def test_guardar_y_leer_carpeta_de_proyectos_premiere(tmp_path):
    ruta = tmp_path / "preferencias.json"
    carpeta = tmp_path / "IAV"

    mod.guardar_carpeta_de_proyectos_premiere(carpeta, ruta)

    assert mod.carpeta_de_proyectos_premiere(ruta) == carpeta
