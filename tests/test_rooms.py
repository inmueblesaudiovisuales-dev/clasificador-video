# tests/test_rooms.py
from clasificador_video.rooms import MASTER_ROOM_LIST, RoomSelection


def test_master_room_list_tiene_los_17_cuartos_del_spec():
    assert len(MASTER_ROOM_LIST) == 17
    assert "Cocina" in MASTER_ROOM_LIST
    assert "Dron/Aérea" in MASTER_ROOM_LIST


def test_seleccionar_cuarto_simple_lo_agrega_una_vez():
    sel = RoomSelection()
    sel.toggle("Cocina")
    assert sel.active_rooms() == ["Cocina"]


def test_deseleccionar_lo_quita():
    sel = RoomSelection()
    sel.toggle("Cocina")
    sel.toggle("Cocina")
    assert sel.active_rooms() == []


def test_cuarto_repetible_con_count_2_numera_automatico():
    sel = RoomSelection()
    sel.set_count("Recámara", 2)
    assert sel.active_rooms() == ["Recámara 1", "Recámara 2"]


def test_cuarto_repetible_con_count_0_no_aparece():
    sel = RoomSelection()
    sel.set_count("Recámara", 2)
    sel.set_count("Recámara", 0)
    assert sel.active_rooms() == []


def test_cuarto_personalizado_se_agrega_al_final():
    sel = RoomSelection()
    sel.toggle("Sala")
    sel.add_custom("Bodega")
    assert sel.active_rooms() == ["Sala", "Bodega"]


def test_orden_de_seleccion_se_respeta_en_active_rooms():
    sel = RoomSelection()
    sel.toggle("Alberca")
    sel.toggle("Fachada")
    assert sel.active_rooms() == ["Alberca", "Fachada"]
