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


def test_sin_archivo_modo_rapido_es_falso(tmp_path: Path):
    # A diferencia de economico, este SI viene apagado por default: cambia
    # como se ve el escrubeo, no evita que la app se trabe.
    assert mod.modo_rapido(tmp_path / "no-existe.json") is False


def test_guardar_y_leer_modo_rapido(tmp_path: Path):
    destino = tmp_path / "preferencias.json"
    mod.guardar_modo_rapido(True, destino)
    assert mod.modo_rapido(destino) is True


def test_modo_rapido_no_pisa_modo_economico_en_el_mismo_archivo(tmp_path: Path):
    destino = tmp_path / "preferencias.json"
    mod.guardar_modo_economico(True, destino)
    mod.guardar_modo_rapido(True, destino)
    assert mod.modo_economico(destino) is True
    assert mod.modo_rapido(destino) is True


def test_carpeta_raiz_icloud_vacia_por_defecto(tmp_path):
    ruta = tmp_path / "preferencias.json"
    assert mod.carpeta_raiz_icloud(ruta) is None


def test_guardar_y_leer_carpeta_raiz_icloud(tmp_path):
    ruta = tmp_path / "preferencias.json"
    carpeta = tmp_path / "01. Proyectos 2026 IAV y PI"

    mod.guardar_carpeta_raiz_icloud(carpeta, ruta)

    assert mod.carpeta_raiz_icloud(ruta) == carpeta
