from pathlib import Path

from clasificador_video.bins import BinTree
from clasificador_video.manifest import Clip
from clasificador_video.proyecto import a_dict, abrir, guardar, rutas_relativas


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


def test_una_relativa_que_se_sale_de_la_carpeta_se_descarta():
    """`relative_to` es puramente lexico: con un `..` en la ruta del clip
    devuelve una relativa que EMPIEZA con `..`. Al reencontrar eso se usa
    como `carpeta / relativa`, o sea que se saldria de la carpeta que Bruno
    señalo -- justo lo que el docstring promete no hacer."""
    bins = BinTree()
    bins.agregar("Sony", Path("/cam"), [0])
    clips = [_clip(0, "/cam/../otro/C0001.MP4")]

    assert rutas_relativas(clips, bins) == {}


def test_un_bin_sin_origen_no_da_relativas():
    """`crear_vacio` deja `Path("")`, que pathlib normaliza a «.» -- no a
    `None`. Hasta hoy esto se salvaba de casualidad, porque `relative_to(".")`
    truena con una ruta absoluta. Se comprueba a proposito."""
    bins = BinTree()
    bins.crear_vacio("Dron")
    bins.sumar("Dron", [0])

    assert rutas_relativas([_clip(0, "/algun/lado/X.MP4")], bins) == {}


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


def test_ida_y_vuelta_a_disco(tmp_path):
    bins = BinTree()
    bins.agregar("Sony", Path("/cam"), [0])
    ruta = tmp_path / "Casa Lomas.cvproj"

    guardar(ruta, a_dict(proyecto="Casa Lomas", rooms=["Cocina"],
                         clips=[_clip(0, "/cam/C0001.MP4")], bins=bins,
                         tamanos={}, duraciones={}, rotaciones={}))

    data = abrir(ruta)
    assert data["proyecto"] == "Casa Lomas"
    assert data["relativas"] == {"0": "C0001.MP4"}


def test_abrir_algo_que_no_es_un_proyecto_no_revienta(tmp_path):
    """Un archivo corrupto o de otra cosa se trata como «no se pudo abrir»,
    igual que hace `load_session`. Reventar aqui deja a Bruno sin forma de
    salir: esto corre al elegir un archivo."""
    malo = tmp_path / "cualquiera.cvproj"
    malo.write_text("esto no es json {")

    assert abrir(malo) is None


def test_abrir_uno_que_no_existe_devuelve_None(tmp_path):
    assert abrir(tmp_path / "no-esta.cvproj") is None


def test_guardar_es_atomico(tmp_path):
    """Mismo criterio que `autosave.save_session`: temporal + rename. Si la
    app muere a medio escribir, el archivo queda con lo viejo completo o
    con lo nuevo completo, nunca a medias."""
    ruta = tmp_path / "p.cvproj"
    guardar(ruta, {"version": 1, "proyecto": "A"})
    guardar(ruta, {"version": 1, "proyecto": "B"})

    assert abrir(ruta)["proyecto"] == "B"
    assert not (tmp_path / "p.cvproj.tmp").exists()
