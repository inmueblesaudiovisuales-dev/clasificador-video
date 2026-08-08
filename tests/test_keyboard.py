# tests/test_keyboard.py
from clasificador_video.keyboard import KeyboardRouter


def test_una_tecla_un_cuarto_sin_estado_intermedio():
    """Antes, un cuarto con subcuartos conocidos no resolvia con la primera
    tecla: se quedaba esperando una segunda, sin limite de tiempo. Eso se fue
    con los subcuartos en la F3."""
    router = KeyboardRouter(active_rooms=["Sala", "Cocina", "Recámara 1"])
    assert router.resolve_room_key("2") == ["Cocina"]
    assert router.resolve_room_key("3") == ["Recámara 1"]
    assert not hasattr(router, "pending_parent")
    assert not hasattr(router, "resolve_subroom_key")
    assert not hasattr(router, "subrooms")


def test_el_cuarto_se_devuelve_como_lista_aunque_sea_plano():
    """Es el contrato del manifest con el plugin de Premiere: el plugin ya
    maneja la lista de un elemento y no hay razon para tocarlo."""
    assert KeyboardRouter(active_rooms=["Sala"]).resolve_room_key("1") == ["Sala"]


def test_tecla_fuera_de_rango_no_hace_nada():
    router = KeyboardRouter(active_rooms=["Sala"])
    assert router.resolve_room_key("9") is None
    assert router.resolve_room_key("0") is None


def test_una_tecla_que_no_es_numero_no_es_de_cuarto():
    assert KeyboardRouter(active_rooms=["Sala"]).resolve_room_key("p") is None


def test_pick_reject_se_resuelven_directo():
    router = KeyboardRouter(active_rooms=["Sala"])
    assert router.resolve_action_key("p") == "pick"
    assert router.resolve_action_key("x") == "reject"
    assert router.resolve_action_key("z") is None


def test_la_u_no_es_una_accion_del_router():
    """Era `"u": "none"` y estaba muerto: MainWindow.handle_key_press la
    intercepta antes --ahi limpia el in/out-- y hace return, asi que el
    router nunca la veia."""
    assert KeyboardRouter(active_rooms=["Sala"]).resolve_action_key("u") is None
