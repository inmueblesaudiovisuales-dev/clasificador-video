# tests/test_autosave.py
import json

from clasificador_video.autosave import load_session, save_session


def test_save_session_escribe_json_legible(tmp_path):
    path = tmp_path / "sesion.json"
    save_session(path, {"proyecto": "Casa Jardin", "clips": [{"ruta": "/a.MP4"}]})
    assert json.loads(path.read_text())["proyecto"] == "Casa Jardin"


def test_save_session_no_deja_archivo_temporal_atras(tmp_path):
    path = tmp_path / "sesion.json"
    save_session(path, {"x": 1})
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_save_session_sobrescribe_de_forma_atomica(tmp_path):
    path = tmp_path / "sesion.json"
    save_session(path, {"version": 1})
    save_session(path, {"version": 2})
    assert json.loads(path.read_text())["version"] == 2


def test_load_session_de_archivo_inexistente_devuelve_none(tmp_path):
    assert load_session(tmp_path / "no-existe.json") is None


def test_load_session_lee_lo_que_guardo_save_session(tmp_path):
    path = tmp_path / "sesion.json"
    save_session(path, {"proyecto": "Casa Jardin"})
    assert load_session(path) == {"proyecto": "Casa Jardin"}


def test_load_session_de_json_mal_formado_devuelve_none(tmp_path):
    path = tmp_path / "roto.json"
    path.write_text("{no es json valido<<<")
    assert load_session(path) is None


def test_load_session_de_json_vacio_devuelve_none(tmp_path):
    path = tmp_path / "vacio.json"
    path.write_text("")
    assert load_session(path) is None
