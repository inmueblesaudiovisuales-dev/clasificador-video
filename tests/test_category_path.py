# tests/test_category_path.py
from clasificador_video.category_path import CategoryTree


def test_cuarto_simple_da_path_de_un_elemento():
    tree = CategoryTree()
    assert tree.path_for("Cocina") == ["Cocina"]


def test_primera_vez_que_se_usa_un_subcuarto_lo_crea():
    tree = CategoryTree()
    tree.attach_subroom(parent="Recámara 2", subroom="Baño")
    assert tree.path_for("Recámara 2", subroom="Baño") == ["Recámara 2", "Baño"]


def test_subcuarto_de_un_padre_no_afecta_a_otro_padre_homonimo():
    tree = CategoryTree()
    tree.attach_subroom(parent="Recámara 1", subroom="Baño")
    tree.attach_subroom(parent="Recámara 2", subroom="Baño")
    assert tree.path_for("Recámara 1", subroom="Baño") == ["Recámara 1", "Baño"]
    assert tree.path_for("Recámara 2", subroom="Baño") == ["Recámara 2", "Baño"]


def test_pedir_subcuarto_no_creado_lanza_error_claro():
    tree = CategoryTree()
    try:
        tree.path_for("Recámara 2", subroom="Closet")
        assert False, "debio lanzar ValueError"
    except ValueError as e:
        assert "Closet" in str(e)
        assert "Recámara 2" in str(e)


def test_known_subrooms_for_lista_los_subcuartos_ya_creados_de_un_padre():
    tree = CategoryTree()
    tree.attach_subroom(parent="Recámara 2", subroom="Baño")
    tree.attach_subroom(parent="Recámara 2", subroom="Closet")
    assert tree.known_subrooms_for("Recámara 2") == ["Baño", "Closet"]
    assert tree.known_subrooms_for("Recámara 1") == []
