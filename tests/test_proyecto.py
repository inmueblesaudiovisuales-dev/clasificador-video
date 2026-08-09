from pathlib import Path

from clasificador_video.bins import BinTree
from clasificador_video.manifest import Clip
from clasificador_video.proyecto import a_dict, rutas_relativas


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


def test_la_ruta_relativa_se_calcula_contra_la_carpeta_del_bin():
    bins = BinTree()
    bins.agregar("Sony", Path("/Volumes/CARD_A/01. VIDEO CAMARA"), [0, 1])
    clips = [
        _clip(0, "/Volumes/CARD_A/01. VIDEO CAMARA/C0001.MP4"),
        _clip(1, "/Volumes/CARD_A/01. VIDEO CAMARA/sub/C0002.MP4"),
    ]

    assert rutas_relativas(clips, bins) == {0: "C0001.MP4", 1: "sub/C0002.MP4"}


def test_un_clip_suelto_no_tiene_ruta_relativa():
    """Sin bin no hay raiz contra la cual ser relativo. Es un caso menor a
    proposito: los sueltos son la cola de trabajo, no el material ya
    acomodado."""
    bins = BinTree()
    clips = [_clip(0, "/algun/lado/X.MP4")]

    assert rutas_relativas(clips, bins) == {}


def test_un_clip_fuera_de_la_carpeta_de_su_bin_tampoco():
    """Puede pasar si alguien movio un archivo a mano. No se inventa una
    relativa con `..`: se guarda solo la absoluta y se reencuentra suelto."""
    bins = BinTree()
    bins.agregar("Sony", Path("/Volumes/CARD_A/CAM"), [0])
    clips = [_clip(0, "/otro/disco/C0001.MP4")]

    assert rutas_relativas(clips, bins) == {}


def test_el_dict_del_proyecto_lleva_todo_lo_de_la_sesion_mas_las_relativas():
    bins = BinTree()
    bins.agregar("Sony", Path("/cam"), [0])
    clips = [_clip(0, "/cam/C0001.MP4")]

    data = a_dict(
        proyecto="Casa Lomas",
        rooms=["Cocina"],
        clips=clips,
        bins=bins,
        tamanos={0: (1080, 1920)},
        duraciones={0: 10.0},
        rotaciones={0: 0},
    )

    assert data["proyecto"] == "Casa Lomas"
    assert data["rooms"] == ["Cocina"]
    assert data["clips"][0]["ruta"] == "/cam/C0001.MP4"
    assert data["bins"][0]["nombre"] == "Sony"
    assert data["tamanos"] == {"0": [1080, 1920]}
    assert data["duraciones"] == {"0": 10.0}
    assert data["rotaciones"] == {"0": 0}
    assert data["relativas"] == {"0": "C0001.MP4"}
    assert data["version"] == 1
