# tests/test_rooms.py
from clasificador_video.rooms import RoomSelection


def test_agregar_un_cuarto_lo_pone_al_final():
    sel = RoomSelection()
    sel.add("Alberca")
    sel.add("Fachada")
    assert sel.active_rooms() == ["Alberca", "Fachada"]


def test_no_se_puede_crear_dos_veces_el_mismo_cuarto():
    """La tecla la da la posicion: dos cuartos con el mismo nombre serian
    dos teclas que hacen lo mismo y un grupo partido en la hoja."""
    sel = RoomSelection()
    sel.add("Cocina")
    sel.add("Cocina")
    assert sel.active_rooms() == ["Cocina"]


def test_un_nombre_en_blanco_no_crea_nada():
    sel = RoomSelection()
    sel.add("   ")
    assert sel.active_rooms() == []


def test_renombrar_conserva_la_posicion_y_por_lo_tanto_la_tecla():
    sel = RoomSelection()
    for cuarto in ("Cocina", "Sala", "Baño"):
        sel.add(cuarto)
    sel.rename("Sala", "Sala de TV")
    assert sel.active_rooms() == ["Cocina", "Sala de TV", "Baño"]


def test_renombrar_a_un_nombre_que_ya_existe_no_hace_nada():
    sel = RoomSelection()
    sel.add("Cocina")
    sel.add("Sala")
    sel.rename("Sala", "Cocina")
    assert sel.active_rooms() == ["Cocina", "Sala"]


def test_mover_un_cuarto_cambia_su_tecla():
    """Reordenar ES cambiar la tecla: no hay otra cosa que reordenar."""
    sel = RoomSelection()
    for cuarto in ("Cocina", "Sala", "Baño"):
        sel.add(cuarto)
    sel.move("Baño", -1)
    assert sel.active_rooms() == ["Cocina", "Baño", "Sala"]


def test_mover_en_los_extremos_no_hace_nada_y_no_revienta():
    sel = RoomSelection()
    sel.add("Cocina")
    sel.move("Cocina", -1)
    sel.move("Cocina", +1)
    assert sel.active_rooms() == ["Cocina"]


def test_eliminar_saca_el_cuarto_y_corre_las_teclas():
    sel = RoomSelection()
    for cuarto in ("Cocina", "Sala", "Baño"):
        sel.add(cuarto)
    sel.remove("Cocina")
    assert sel.active_rooms() == ["Sala", "Baño"]


def test_operar_sobre_un_cuarto_que_no_existe_no_revienta():
    sel = RoomSelection()
    sel.add("Cocina")
    sel.rename("Fantasma", "Otro")
    sel.move("Fantasma", 1)
    sel.remove("Fantasma")
    assert sel.active_rooms() == ["Cocina"]


def test_ya_no_hay_cuartos_repetibles_ni_catalogo_maestro():
    """Los cuartos son planos y se crean sobre la marcha: 'Recámara 1' es un
    nombre, no una instancia numerada de un cuarto plantilla. Y no hay
    catalogo previo porque no hay paso previo (DECISIONES.md, 'Cuartos:
    planos, sin techo, sin configuracion inicial')."""
    import clasificador_video.rooms as rooms

    assert not hasattr(rooms, "REPEATABLE_ROOMS")
    assert not hasattr(rooms, "MASTER_ROOM_LIST")
    assert not hasattr(RoomSelection, "set_count")
    assert not hasattr(RoomSelection, "toggle")


def test_insertar_un_cuarto_en_una_posicion():
    """Deshacer un borrado tiene que devolver el cuarto A SU LUGAR, para que
    recupere su tecla, sin tocar los demas."""
    sel = RoomSelection()
    for cuarto in ("Cocina", "Sala", "Baño"):
        sel.add(cuarto)
    sel.remove("Sala")
    sel.insert_at(1, "Sala")
    assert sel.active_rooms() == ["Cocina", "Sala", "Baño"]


def test_insertar_fuera_de_rango_lo_pone_al_final():
    sel = RoomSelection()
    sel.add("Cocina")
    sel.insert_at(99, "Alberca")
    assert sel.active_rooms() == ["Cocina", "Alberca"]


def test_insertar_uno_que_ya_existe_no_lo_duplica():
    sel = RoomSelection()
    sel.add("Cocina")
    sel.insert_at(0, "Cocina")
    assert sel.active_rooms() == ["Cocina"]


def test_mover_a_lleva_el_cuarto_a_esa_posicion():
    """Arrastrar es mover A UN LUGAR, no `move(delta)` repetido: con 13
    cuartos, subir el ultimo hasta arriba serian doce llamadas."""
    seleccion = RoomSelection()
    for cuarto in ["Fachada", "Sala", "Comedor", "Alberca"]:
        seleccion.add(cuarto)

    seleccion.mover_a("Alberca", 0)

    assert seleccion.active_rooms() == ["Alberca", "Fachada", "Sala", "Comedor"]


def test_mover_a_al_final():
    seleccion = RoomSelection()
    for cuarto in ["Fachada", "Sala", "Comedor"]:
        seleccion.add(cuarto)

    seleccion.mover_a("Fachada", 2)

    assert seleccion.active_rooms() == ["Sala", "Comedor", "Fachada"]


def test_mover_a_donde_ya_estaba_no_cambia_nada():
    seleccion = RoomSelection()
    for cuarto in ["Fachada", "Sala"]:
        seleccion.add(cuarto)

    seleccion.mover_a("Fachada", 0)

    assert seleccion.active_rooms() == ["Fachada", "Sala"]


def test_mover_a_recorta_la_posicion_en_vez_de_reventar():
    """La posicion viene de un gesto del mouse: soltar debajo del ultimo
    puede dar un numero mas grande que la lista."""
    seleccion = RoomSelection()
    for cuarto in ["Fachada", "Sala"]:
        seleccion.add(cuarto)

    seleccion.mover_a("Fachada", 99)
    seleccion.mover_a("Sala", -3)

    assert seleccion.active_rooms() == ["Sala", "Fachada"]


def test_mover_a_un_cuarto_que_no_existe_no_hace_nada():
    seleccion = RoomSelection()
    seleccion.add("Fachada")

    seleccion.mover_a("Alberca", 0)

    assert seleccion.active_rooms() == ["Fachada"]
