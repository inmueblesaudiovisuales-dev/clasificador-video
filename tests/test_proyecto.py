from pathlib import Path

import pytest

from clasificador_video.bins import BinTree
from clasificador_video.manifest import Clip
from clasificador_video.proyecto import (
    a_dict,
    abrir,
    con_pesos_medidos,
    guardar,
    rutas_relativas,
)


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


def test_una_relativa_que_ya_no_se_puede_calcular_no_se_tira():
    """Reconectar a medias deja al bin colgando de la carpeta NUEVA y al
    clip que sigue perdido apuntando a la vieja, así que `relative_to`
    falla. Si esa relativa desapareciera del documento, ese clip se quedaría
    sin con qué reencontrarse nunca más — y es lo único que no se puede
    volver a deducir cuando el archivo no está en disco."""
    bins = BinTree()
    bins.agregar("Sony", Path("/nueva"), [0, 1])
    clips = [_clip(0, "/nueva/C0001.MP4"), _clip(1, "/vieja/C0002.MP4")]

    data = a_dict(proyecto="P", rooms=[], clips=clips, bins=bins,
                  tamanos={}, duraciones={}, rotaciones={},
                  relativas_conocidas={0: "C0001.MP4", 1: "C0002.MP4"})

    assert data["relativas"] == {"0": "C0001.MP4", "1": "C0002.MP4"}


def test_lo_calculado_le_gana_a_la_relativa_vieja():
    """La calculada dice dónde está el archivo AHORA. La guardada es un
    respaldo, no una fuente que compita."""
    bins = BinTree()
    bins.agregar("Sony", Path("/cam"), [0])
    clips = [_clip(0, "/cam/sub/C0001.MP4")]

    data = a_dict(proyecto="P", rooms=[], clips=clips, bins=bins,
                  tamanos={}, duraciones={}, rotaciones={},
                  relativas_conocidas={0: "C0001.MP4"})

    assert data["relativas"] == {"0": "sub/C0001.MP4"}


def test_la_relativa_de_un_clip_que_ya_no_esta_no_sobrevive():
    """El respaldo puede venir de un proyecto con más clips de los que hay
    ahora — quitar un bin es exactamente ese caso."""
    bins = BinTree()
    bins.agregar("Sony", Path("/cam"), [0])
    clips = [_clip(0, "/cam/C0001.MP4")]

    data = a_dict(proyecto="P", rooms=[], clips=clips, bins=bins,
                  tamanos={}, duraciones={}, rotaciones={},
                  relativas_conocidas={0: "C0001.MP4", 7: "C0008.MP4"})

    assert data["relativas"] == {"0": "C0001.MP4"}


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
    """Temporal + rename, como cualquier escritura que no se puede partir. Si la
    app muere a medio escribir, el archivo queda con lo viejo completo o
    con lo nuevo completo, nunca a medias."""
    ruta = tmp_path / "p.cvproj"
    guardar(ruta, {"version": 1, "proyecto": "A"})
    guardar(ruta, {"version": 1, "proyecto": "B"})

    assert abrir(ruta)["proyecto"] == "B"
    assert not (tmp_path / "p.cvproj.tmp").exists()


def test_una_escritura_fallida_no_deja_basura_en_la_carpeta(tmp_path, monkeypatch):
    """Con el disco lleno el temporal quedaba a la vista en la carpeta de
    Bruno, como un `Casa Lomas.cvproj.tmp` que nadie sabe que es."""
    ruta = tmp_path / "Casa Lomas.cvproj"
    original = Path.write_text

    def se_llena_el_disco(self, texto, *args, **kwargs):
        original(self, texto[:5])          # alcanzo a escribir un pedazo
        raise OSError("No space left on device")

    monkeypatch.setattr(Path, "write_text", se_llena_el_disco)

    with pytest.raises(OSError):
        guardar(ruta, {"version": 1, "proyecto": "Casa Lomas"})

    monkeypatch.undo()
    assert list(tmp_path.iterdir()) == []


def test_armar_el_documento_no_toca_el_disco(tmp_path):
    """`a_dict` es puro: no mide nada.

    El medido vive en `con_pesos_medidos`, que corre en el hilo del guardado.
    En el de la interfaz un `stat` por clip se traba hasta el timeout si el
    volumen esta montado pero incomunicado --109 en serie-- y la app se
    congela. Esa es justo la razon por la que el guardado se saco de ahi.
    """
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 700)
    bins = BinTree()
    bins.agregar("Sony", tmp_path, [0])

    data = a_dict(proyecto="P", rooms=[], clips=[_clip(0, str(archivo))],
                  bins=bins, tamanos={}, duraciones={}, rotaciones={})

    assert data["bytes"] == {}


def test_el_proyecto_guarda_el_tamano_de_cada_archivo(tmp_path):
    """Sin esto no hay como confirmar que un archivo reencontrado es el que
    era: el nombre lo repiten las camaras y la duracion sola no distingue
    dos tomas iguales."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 700)
    bins = BinTree()
    bins.agregar("Sony", tmp_path, [0])

    data = con_pesos_medidos(
        a_dict(proyecto="P", rooms=[], clips=[_clip(0, str(archivo))],
               bins=bins, tamanos={}, duraciones={}, rotaciones={})
    )

    assert data["bytes"] == {"0": 700}


def test_un_archivo_que_ya_no_esta_no_impide_guardar(tmp_path):
    """Guardar tiene que funcionar con el disco desconectado: si no, se
    pierde el trabajo justo cuando mas duele."""
    bins = BinTree()
    bins.agregar("Sony", Path("/no/existe"), [0])

    data = con_pesos_medidos(
        a_dict(proyecto="P", rooms=[], clips=[_clip(0, "/no/existe/X.MP4")],
               bins=bins, tamanos={}, duraciones={}, rotaciones={})
    )

    assert data["bytes"] == {}


def test_guardar_sin_la_media_conserva_los_bytes_que_ya_se_sabian(tmp_path):
    """EL bug: abres el proyecto en otra computadora, el autoguardado se
    dispara solo a los pocos segundos, y como ningun archivo se puede medir
    reescribia `bytes: {}`. Cuando Bruno aprieta «Buscar…» ya no queda con
    que confirmar nada, y el que confirma es el que engancha material
    equivocado. Lo que no se puede medir se conserva."""
    bins = BinTree()
    bins.agregar("Sony", Path("/no/existe"), [0])

    data = con_pesos_medidos(
        a_dict(proyecto="P", rooms=[], clips=[_clip(0, "/no/existe/X.MP4")],
               bins=bins, tamanos={}, duraciones={}, rotaciones={},
               bytes_conocidos={0: 700})
    )

    assert data["bytes"] == {"0": 700}


def test_los_bytes_conocidos_llegan_con_la_llave_en_texto(tmp_path):
    """Vienen de vuelta del JSON, donde toda llave es texto. Si no se
    normalizan, `0` y `"0"` no se cruzan nunca y el dato se pierde igual que
    si no se hubiera guardado -- en silencio, que es lo peor."""
    bins = BinTree()
    bins.agregar("Sony", Path("/no/existe"), [0])

    data = con_pesos_medidos(
        a_dict(proyecto="P", rooms=[], clips=[_clip(0, "/no/existe/X.MP4")],
               bins=bins, tamanos={}, duraciones={}, rotaciones={},
               bytes_conocidos={"0": 700})
    )

    assert data["bytes"] == {"0": 700}


def test_el_disco_manda_cuando_el_archivo_si_se_puede_medir(tmp_path):
    """Conservar es para cuando no hay con que medir. Si el archivo esta
    ahi, el peso de hoy es el bueno: pudo haberse reemplazado por otra
    toma."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 700)
    bins = BinTree()
    bins.agregar("Sony", tmp_path, [0])

    data = con_pesos_medidos(
        a_dict(proyecto="P", rooms=[], clips=[_clip(0, str(archivo))],
               bins=bins, tamanos={}, duraciones={}, rotaciones={},
               bytes_conocidos={0: 111})
    )

    assert data["bytes"] == {"0": 700}


def test_los_pesos_de_antes_se_arrastran_aunque_la_ventana_no_los_sepa(tmp_path):
    """El archivo es el que acumula.

    Mides un clip con la tarjeta puesta, la desconectas y sigues trabajando:
    la ventana nunca supo ese peso --lo midio el hilo del guardado-- asi que
    si el guardado de despues no mirara lo que ya habia en el archivo, ese
    peso se perderia igual que antes.
    """
    bins = BinTree()
    bins.agregar("Sony", Path("/no/existe"), [0])
    documento = a_dict(proyecto="P", rooms=[], clips=[_clip(0, "/no/existe/X.MP4")],
                       bins=bins, tamanos={}, duraciones={}, rotaciones={})

    data = con_pesos_medidos(documento, previos={"0": 700})

    assert data["bytes"] == {"0": 700}


def test_medir_no_ensucia_el_documento_original(tmp_path):
    """Se devuelve una copia: el que llama sigue siendo dueño del suyo."""
    bins = BinTree()
    documento = a_dict(proyecto="P", rooms=[], clips=[], bins=bins,
                       tamanos={}, duraciones={}, rotaciones={})

    con_pesos_medidos(documento, previos={"0": 700})

    assert documento["bytes"] == {}
