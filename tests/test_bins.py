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
