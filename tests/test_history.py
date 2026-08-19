# tests/test_history.py
from clasificador_video.history import History, HistoryEntry


def _entrada(etiqueta="Cocina", detalle="→ 1 clip", color="#c0885a", antes=None):
    return HistoryEntry(
        etiqueta=etiqueta, detalle=detalle, color=color,
        antes=antes if antes is not None else {0: {"categoria_path": []}},
    )


def test_la_entrada_mas_reciente_va_primera():
    """El historial se lee de arriba hacia abajo, como el del mockup."""
    h = History()
    h.push(_entrada("Cocina"))
    h.push(_entrada("Sala"))
    assert [e.etiqueta for e in h.entries()] == ["Sala", "Cocina"]


def test_deshacer_devuelve_la_ultima_y_la_saca():
    h = History()
    h.push(_entrada("Cocina"))
    h.push(_entrada("Sala"))
    assert h.undo_last().etiqueta == "Sala"
    assert [e.etiqueta for e in h.entries()] == ["Cocina"]


def test_deshacer_con_el_historial_vacio_no_revienta():
    assert History().undo_last() is None


def test_renombrar_un_cuarto_lo_renombra_tambien_en_lo_ya_registrado():
    """Renombrar no crea un cuarto nuevo: es el mismo con otro nombre.

    El «antes» de cada entrada guarda el NOMBRE, asi que sin mover esto,
    deshacer una accion anterior al renombrado devolvia un cuarto que ya no
    existe en el rail.
    """
    h = History()
    h.push(_entrada("Sala", antes={0: {"categoria_path": ["Cocina"]},
                                   1: {"categoria_path": []}}))
    h.push(_entrada("Cocina", antes={2: {"flag": "none"}}))

    h.renombrar_cuarto("Cocina", "Cocina principal")

    entradas = h.entries()
    # la etiqueta de la fila, que es como se llama la accion en el rail
    assert entradas[0].etiqueta == "Cocina principal"
    assert entradas[1].etiqueta == "Sala"
    # y el estado guardado de cada clip
    assert entradas[1].antes[0]["categoria_path"] == ["Cocina principal"]
    assert entradas[1].antes[1]["categoria_path"] == []
    # lo que no es un cuarto no se toca
    assert entradas[0].antes[2] == {"flag": "none"}


def test_renombrar_un_cuarto_que_no_esta_en_el_historial_no_hace_nada():
    h = History()
    h.push(_entrada("Sala", antes={0: {"categoria_path": ["Sala"]}}))

    h.renombrar_cuarto("Cocina", "Cocina principal")

    assert h.entries()[0].antes[0]["categoria_path"] == ["Sala"]


def test_revertir_una_entrada_del_medio_la_saca_y_deja_el_resto():
    """DECISIONES.md: el resto se revierte con un click, no solo la de arriba."""
    h = History()
    a, b, c = _entrada("A"), _entrada("B"), _entrada("C")
    for e in (a, b, c):
        h.push(e)
    assert h.revert(b.id) is b
    assert [e.etiqueta for e in h.entries()] == ["C", "A"]


def test_revertir_una_entrada_que_ya_no_esta_devuelve_none():
    """Doble click en el mismo boton de revertir: la segunda no hace nada."""
    h = History()
    e = _entrada()
    h.push(e)
    h.revert(e.id)
    assert h.revert(e.id) is None


def test_cada_entrada_tiene_id_propio():
    a, b = _entrada(), _entrada()
    assert a.id != b.id


def test_una_accion_en_lote_es_UNA_entrada():
    """Deshacer seis clips asignados de una tiene que costar un ⌘Z, no seis:
    si costara seis, asignar en lote seria una trampa."""
    h = History()
    h.push(_entrada("Baño 1", "→ 6 clips",
                    antes={i: {"categoria_path": []} for i in range(6)}))
    assert len(h.entries()) == 1
    assert len(h.entries()[0].antes) == 6


def test_la_pila_tiene_techo_y_tira_lo_mas_viejo():
    """Sin techo, una sesion larga acumula memoria sin que nadie mire mas
    alla de las ultimas cinco filas."""
    h = History(limite=3)
    for i in range(5):
        h.push(_entrada(str(i)))
    assert [e.etiqueta for e in h.entries()] == ["4", "3", "2"]


def test_la_entrada_sabe_que_campos_restaurar():
    """Guardar el clip ENTERO haria que revertir 'Cocina -> 6 clips' borrara
    tambien el pick que marcaste despues sobre uno de esos seis."""
    e = _entrada(antes={3: {"flag": "none"}})
    assert e.antes == {3: {"flag": "none"}}


def test_una_entrada_puede_recordar_el_cuarto_borrado_y_su_posicion():
    """Borrar un cuarto desde el rail hay que poder deshacerlo entero: el
    cuarto vuelve a la lista Y sus clips vuelven a tenerlo.

    Se guarda `(nombre, posicion)` y no la lista entera: restaurar la lista
    completa se llevaba puesto todo lo creado despues del borrado. Y la
    posicion importa porque es lo que le da la tecla al cuarto.
    """
    e = HistoryEntry(etiqueta="Cocina", detalle="cuarto borrado", color="#c0885a",
                     antes={0: {"categoria_path": ["Cocina"]}},
                     cuarto_borrado=("Cocina", 0))
    assert e.cuarto_borrado == ("Cocina", 0)
    assert _entrada().cuarto_borrado is None


def test_vaciar_el_historial():
    """Al importar material nuevo, lo de antes ya no aplica a nada."""
    h = History()
    h.push(_entrada())
    h.clear()
    assert h.entries() == []
    assert h.undo_last() is None


def test_una_entrada_puede_recordar_de_que_bin_venia_cada_clip():
    """El bin no es un campo del clip --vive en `BinTree`-- asi que no puede
    viajar por `antes`, que se aplica con `setattr` sobre el clip."""
    entrada = HistoryEntry(
        etiqueta="Card B", detalle="→ 3 clips", color="#3e9bc0", antes={},
        bins_antes={0: "Card A", 1: None},
    )
    assert entrada.bins_antes == {0: "Card A", 1: None}
    assert entrada.bin_creado is None
    assert entrada.bin_renombrado is None


def test_los_campos_de_bin_nacen_vacios():
    """Una entrada de cuarto o de estado no habla de bins, y no tiene por que
    escribir tres `None` para decirlo."""
    entrada = HistoryEntry(etiqueta="Cocina", detalle="→ 6 clips",
                           color="#c0885a", antes={})
    assert entrada.bins_antes is None
    assert entrada.bin_creado is None
    assert entrada.bin_renombrado is None


def test_renombrar_un_bin_mueve_lo_ya_registrado():
    """Mismo motivo que `renombrar_cuarto`: un renglon que hable de un bin
    que ya no existe promete devolver algo inalcanzable."""
    h = History()
    h.push(HistoryEntry(etiqueta="Card A", detalle="→ 2 clips", color="#3e9bc0",
                        antes={}, bins_antes={0: "Card A", 1: None}))
    h.push(HistoryEntry(etiqueta="Card A", detalle="→ bin nuevo", color="#3e9bc0",
                        antes={}, bin_creado="Card A"))

    h.renombrar_bin("Card A", "Camara 1")

    creado, movido = h.entries()
    assert creado.bin_creado == "Camara 1"
    assert creado.etiqueta == "Camara 1"
    assert movido.bins_antes == {0: "Camara 1", 1: None}
    assert movido.etiqueta == "Camara 1"


def test_renombrar_un_bin_no_toca_un_cuarto_que_se_llame_igual():
    """Un cuarto y un bin pueden llamarse igual --«Cocina» la camara y
    «Cocina» el cuarto-- y la `etiqueta` no distingue cual es cual. Se mira
    si la entrada habla de bins, que es el dato."""
    h = History()
    h.push(HistoryEntry(etiqueta="Cocina", detalle="→ 6 clips", color="#c0885a",
                        antes={0: {"categoria_path": ["Cocina"]}}))

    h.renombrar_bin("Cocina", "Camara 1")

    assert h.entries()[0].etiqueta == "Cocina"
    assert h.entries()[0].antes == {0: {"categoria_path": ["Cocina"]}}


def test_renombrar_un_cuarto_no_toca_un_bin_que_se_llame_igual():
    """El reves del anterior, y hace falta desde hoy: hasta ahora ninguna
    entrada del historial hablaba de bins."""
    h = History()
    h.push(HistoryEntry(etiqueta="Cocina", detalle="→ 2 clips", color="#3e9bc0",
                        antes={}, bins_antes={0: "Cocina"}))

    h.renombrar_cuarto("Cocina", "Cocina chica")

    assert h.entries()[0].etiqueta == "Cocina"
    assert h.entries()[0].bins_antes == {0: "Cocina"}
