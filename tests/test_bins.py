from pathlib import Path

from clasificador_video.bins import BinTree


def test_un_bin_nuevo_queda_al_final_con_sus_clips():
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0, 1, 2])
    arbol.agregar("Dron", Path("/dron"), [3, 4])

    assert arbol.nombres() == ["Sony FX30", "Dron"]
    assert arbol.clips_de("Dron") == [3, 4]


def test_el_bin_de_un_clip():
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0, 1])
    arbol.agregar("Dron", Path("/dron"), [2])

    assert arbol.bin_de(1) == "Sony FX30"
    assert arbol.bin_de(2) == "Dron"
    assert arbol.bin_de(99) is None


def test_dos_bins_no_pueden_llamarse_igual():
    """Dos con el mismo nombre serian dos encabezados identicos en la hoja
    y un menu de clic derecho que no se sabe a cual aplica."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/a"), [0])
    arbol.agregar("Dron", Path("/b"), [1])

    assert arbol.nombres() == ["Dron", "Dron 2"]


def test_renombrar_conserva_la_posicion():
    """La posicion es el orden en la hoja: renombrar no puede moverlo."""
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0])
    arbol.agregar("Dron", Path("/dron"), [1])

    arbol.renombrar("Sony FX30", "Sony A")

    assert arbol.nombres() == ["Sony A", "Dron"]
    assert arbol.clips_de("Sony A") == [0]


def test_renombrar_a_uno_que_ya_existe_no_hace_nada():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/a"), [0])
    arbol.agregar("Sony", Path("/b"), [1])

    arbol.renombrar("Sony", "Dron")

    assert arbol.nombres() == ["Dron", "Sony"]


def test_sumar_clips_a_un_bin_que_ya_existe():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])

    arbol.sumar("Dron", [2, 3])

    assert arbol.clips_de("Dron") == [0, 1, 2, 3]


def test_quitar_un_bin_devuelve_los_indices_que_se_van():
    """Quien llama tiene que borrar esos clips de la lista y de todo lo que
    va indexado por clip. Si no los devolviera, habria que adivinarlos."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2])

    assert arbol.quitar("Dron") == [0, 1]
    assert arbol.nombres() == ["Sony"]


def test_reindexar_despues_de_quitar_clips():
    """Al borrar los clips 0 y 1, el que era 2 pasa a ser 0. Los bins van
    por INDICE, asi que si no se recorren quedan apuntando a otro clip."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2, 3])

    arbol.reindexar_tras_quitar([0, 1])

    assert arbol.clips_de("Sony") == [0, 1]


def test_ida_y_vuelta_a_json():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2])

    otro = BinTree.from_list(arbol.to_list())

    assert otro.nombres() == ["Dron", "Sony"]
    assert otro.clips_de("Dron") == [0, 1]
    assert otro.clips_de("Sony") == [2]


def test_una_sesion_vieja_sin_bins_cae_en_uno_solo():
    """Nadie pierde una sesion por actualizar la app. Sin la llave `bins`,
    todo el material queda en un bin unico con la carpeta del primer clip.
    """
    arbol = BinTree.desde_sesion(
        None, rutas=[Path("/material/A.MP4"), Path("/material/B.MP4")]
    )

    assert arbol.nombres() == ["material"]
    assert arbol.clips_de("material") == [0, 1]


def test_una_sesion_vieja_sin_clips_no_inventa_un_bin():
    assert BinTree.desde_sesion(None, rutas=[]).nombres() == []
