# tests/test_manifest.py
import json
from pathlib import Path

from clasificador_video.manifest import Clip, Manifest


def _clip(**overrides) -> Clip:
    base = dict(
        orden=1,
        ruta=Path("/shooting/C0012.MP4"),
        categoria_path=["Cocina"],
        fps=59.94005994005994,
        in_frame=None,
        out_frame=None,
        flag="none",
        ruta_proxy=None,
    )
    base.update(overrides)
    return Clip(**base)


def test_clip_to_dict_usa_las_llaves_exactas_del_manifest():
    clip = _clip(in_frame=30, out_frame=200, flag="pick", ruta_proxy=Path("/shooting/C0012S03.MP4"))
    assert clip.to_dict() == {
        "orden": 1,
        "ruta": "/shooting/C0012.MP4",
        "categoria_path": ["Cocina"],
        "fps": 59.94005994005994,
        "in_frame": 30,
        "out_frame": 200,
        "flag": "pick",
        "ruta_proxy": "/shooting/C0012S03.MP4",
    }


def test_clip_to_dict_sin_in_out_ni_proxy_usa_null():
    clip = _clip()
    d = clip.to_dict()
    assert d["in_frame"] is None
    assert d["out_frame"] is None
    assert d["ruta_proxy"] is None


def test_clip_flag_por_defecto_es_none():
    assert _clip().flag == "none"


def test_manifest_to_dict_incluye_proyecto_orientacion_y_clips_en_orden():
    m = Manifest(
        proyecto="Casa Jardin",
        orientacion="vertical",
        clips=[_clip(orden=2), _clip(orden=1)],
    )
    d = m.to_dict()
    assert d["proyecto"] == "Casa Jardin"
    assert d["orientacion"] == "vertical"
    assert [c["orden"] for c in d["clips"]] == [2, 1]  # respeta el orden de la lista, no reordena


def test_manifest_write_json_escribe_archivo_legible(tmp_path):
    m = Manifest(proyecto="Casa Jardin", orientacion="vertical", clips=[_clip()])
    out = tmp_path / "manifest.json"
    m.write_json(out)
    loaded = json.loads(out.read_text())
    assert loaded["proyecto"] == "Casa Jardin"
    assert loaded["clips"][0]["ruta"] == "/shooting/C0012.MP4"
