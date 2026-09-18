from pathlib import Path

from clasificador_video import preferencias as mod


def test_sin_archivo_modo_economico_es_falso(tmp_path: Path):
    # La primera vez no hay preferencias guardadas, y eso no es un error:
    # el valor por defecto es "normal", no economico.
    assert mod.modo_economico(tmp_path / "no-existe.json") is False


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
    assert mod.modo_economico(destino) is False
