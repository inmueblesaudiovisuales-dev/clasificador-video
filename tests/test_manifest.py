# tests/test_manifest.py
import json
from pathlib import Path

from clasificador_video.manifest import Clip, Manifest, con_subcarpeta_de_estado


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


def test_destacado_viaja_en_el_manifest_sin_cambiar_el_contrato():
    """El plugin de Premiere mapea pick→FOREST, reject→ROSE e IGNORA lo que no
    conoce: `destacado` es aditivo y no obliga a tocar `to_dict()` ni el
    formato del manifest."""
    clip = Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Cocina"], fps=30.0)
    clip.flag = "destacado"
    assert clip.to_dict()["flag"] == "destacado"
    assert clip.to_dict()["categoria_path"] == ["Cocina"]


# --- la subcarpeta de estado dentro del bin del cuarto ---------------------


def test_un_pick_cae_en_la_subcarpeta_picks_de_su_cuarto():
    clip = Clip(orden=1, ruta=Path("/c/A.MP4"), categoria_path=["Cocina"],
                fps=30.0, flag="pick")

    assert con_subcarpeta_de_estado(clip).categoria_path == ["Cocina", "Picks"]


def test_cada_estado_tiene_su_subcarpeta():
    def camino(flag):
        return con_subcarpeta_de_estado(
            Clip(orden=1, ruta=Path("/c/A.MP4"), categoria_path=["Cocina"],
                 fps=30.0, flag=flag)
        ).categoria_path[-1]

    assert camino("destacado") == "Destacados"
    assert camino("pick") == "Picks"
    assert camino("reject") == "Rejects"
    assert camino("none") == "Sin marcar"


def test_un_clip_sin_cuarto_se_deja_tal_cual():
    """Su camino vacio es lo que hace que el plugin lo mande a «Sin
    clasificar», y esa cadena vive alla: escribirla tambien aqui serian dos
    lugares diciendo el nombre del mismo bin."""
    clip = Clip(orden=1, ruta=Path("/c/A.MP4"), categoria_path=[], fps=30.0,
                flag="pick")

    assert con_subcarpeta_de_estado(clip).categoria_path == []


def test_no_le_toca_el_camino_al_clip_original():
    """Devuelve una COPIA: el `categoria_path` que se exporta no es el que la
    sesion guarda -- si lo mutara, marcar un pick se veria en la app como un
    cambio de cuarto, y el historial, la hoja y el rail van todos por ahi."""
    clip = Clip(orden=1, ruta=Path("/c/A.MP4"), categoria_path=["Cocina"],
                fps=30.0, flag="pick")

    con_subcarpeta_de_estado(clip)

    assert clip.categoria_path == ["Cocina"]


def test_un_estado_desconocido_no_inventa_subcarpeta():
    """Una sesion tocada a mano puede traer cualquier cosa en `flag`. Un bin
    llamado «None» en el proyecto de Bruno seria peor que no anidar."""
    clip = Clip(orden=1, ruta=Path("/c/A.MP4"), categoria_path=["Cocina"],
                fps=30.0, flag="lo-que-sea")

    assert con_subcarpeta_de_estado(clip).categoria_path == ["Cocina"]
