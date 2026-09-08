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
        "camara": "sony",
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


def test_destacado_viaja_en_el_manifest_sin_cambiar_el_contrato():
    """El plugin de Premiere mapea pick→FOREST, reject→ROSE e IGNORA lo que no
    conoce: `destacado` es aditivo y no obliga a tocar `to_dict()` ni el
    formato del manifest."""
    clip = Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Cocina"], fps=30.0)
    clip.flag = "destacado"
    assert clip.to_dict()["flag"] == "destacado"
    assert clip.to_dict()["categoria_path"] == ["Cocina"]


# --- el cuarto es plano: sin subcarpetas de estado ------------------------
#
# Hubo un `con_subcarpeta_de_estado` que colgaba «Picks», «Rejects» y «Sin
# marcar» dentro de cada cuarto. Se fue entero el 2026-09-08: el estado lo
# dicen ahora las marcas del nombre en Premiere (★ destacado, ✓ pick, ✕
# reject, nada = sin ver), y una carpeta que dice lo mismo que una marca solo
# esconde el clip. Ver `nombre.js` y el §9 del spec de ese día.


def test_el_camino_del_clip_es_su_cuarto_y_nada_mas():
    """Sea cual sea su estado. Es lo que lo deja plano dentro del cuarto."""
    for flag in ("pick", "reject", "destacado", "none", "lo-que-sea"):
        clip = Clip(orden=1, ruta=Path("/c/A.MP4"), categoria_path=["Cocina"],
                    fps=30.0, flag=flag)

        assert clip.to_dict()["categoria_path"] == ["Cocina"], flag


def test_un_clip_sin_cuarto_viaja_con_el_camino_vacio():
    """Su camino vacío es lo que hace que el plugin lo mande a «Sin
    clasificar», y esa cadena vive allá: escribirla también aquí serían dos
    lugares diciendo el nombre del mismo bin."""
    clip = Clip(orden=1, ruta=Path("/c/A.MP4"), categoria_path=[], fps=30.0,
                flag="pick")

    assert clip.to_dict()["categoria_path"] == []


def test_el_clip_lleva_su_camara_al_manifiesto():
    clip = Clip(orden=1, ruta=Path("/x/DJI_0001.MP4"), categoria_path=["Cocina"],
                fps=59.94, camara="dji")

    assert clip.to_dict()["camara"] == "dji"


def test_un_clip_sin_camara_dicha_sale_sony():
    """El mismo respaldo que en `Bin`: hace falta UNA respuesta, y es la
    cámara con la que Bruno graba casi todo."""
    clip = Clip(orden=1, ruta=Path("/x/C0001.MP4"), categoria_path=["Cocina"],
                fps=59.94)

    assert clip.to_dict()["camara"] == "sony"
