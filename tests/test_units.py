"""UnitSelection es UnitSelection(RoomSelection): misma forma, mismos
metodos (add/rename/move/mover_a/reordenar/remove/active_rooms) -- el
orden ES la tecla, igual que en RoomSelection. Clase propia y no la misma
RoomSelection reusada para no mezclar en el codigo "una lista de cuartos"
con "una lista de unidades", aunque el cuerpo sea identico (DRY vía
herencia trivial)."""
from clasificador_video.units import UnitSelection
from clasificador_video.rooms import RoomSelection


def test_es_una_room_selection():
    assert isinstance(UnitSelection(), RoomSelection)


def test_add_y_orden():
    sel = UnitSelection()
    sel.add("Casa A")
    sel.add("Casa B")
    assert sel.active_rooms() == ["Casa A", "Casa B"]


def test_no_es_la_misma_clase_que_room_selection():
    # dos catalogos independientes: agregar a uno no toca al otro
    assert UnitSelection is not RoomSelection
