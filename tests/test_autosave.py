# tests/test_autosave.py
#
# Aquí también se probaba `save_session`. Murió con la F5: el que escribe el
# proyecto es `proyecto.guardar`, y sus tests viven en `test_proyecto.py`.
# Lo que queda es la lectura de la sesión vieja, que solo usa la migración.
import json

from clasificador_video.autosave import load_session


def test_load_session_de_archivo_inexistente_devuelve_none(tmp_path):
    assert load_session(tmp_path / "no-existe.json") is None


def test_load_session_lee_el_json_de_la_sesion(tmp_path):
    path = tmp_path / "sesion.json"
    path.write_text(json.dumps({"proyecto": "Casa Jardin"}))
    assert load_session(path) == {"proyecto": "Casa Jardin"}


def test_load_session_de_json_mal_formado_devuelve_none(tmp_path):
    """Un JSON roto no puede impedir arrancar: esto corre al abrir la app."""
    path = tmp_path / "roto.json"
    path.write_text("{no es json valido<<<")
    assert load_session(path) is None


def test_load_session_de_json_vacio_devuelve_none(tmp_path):
    path = tmp_path / "vacio.json"
    path.write_text("")
    assert load_session(path) is None
