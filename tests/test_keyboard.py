# tests/test_keyboard.py
from clasificador_video.keyboard import KeyboardRouter


def test_numero_sin_subcuartos_asigna_el_cuarto_directo():
    router = KeyboardRouter(active_rooms=["Sala", "Cocina", "Recámara 1"])
    assert router.resolve_room_key("2") == ["Cocina"]


def test_numero_con_subcuartos_conocidos_entra_en_modo_subcuarto():
    router = KeyboardRouter(active_rooms=["Sala", "Recámara 1"], subrooms={"Recámara 1": ["Baño"]})
    assert router.resolve_room_key("2") is None  # no resuelve todavia, esperando el subcuarto
    assert router.pending_parent == "Recámara 1"
    assert router.resolve_subroom_key("1") == ["Recámara 1", "Baño"]


def test_tecla_fuera_de_rango_no_hace_nada():
    router = KeyboardRouter(active_rooms=["Sala"])
    assert router.resolve_room_key("9") is None
    assert router.pending_parent is None


def test_pick_reject_se_resuelven_directo():
    router = KeyboardRouter(active_rooms=["Sala"])
    assert router.resolve_action_key("p") == "pick"
    assert router.resolve_action_key("x") == "reject"
    assert router.resolve_action_key("u") == "none"
    assert router.resolve_action_key("z") is None
