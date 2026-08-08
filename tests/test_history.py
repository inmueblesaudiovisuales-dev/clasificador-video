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


def test_una_entrada_puede_recordar_la_lista_de_cuartos():
    """Borrar un cuarto desde el rail hay que poder deshacerlo entero: el
    cuarto vuelve a la lista Y sus clips vuelven a tenerlo."""
    e = HistoryEntry(etiqueta="Cocina", detalle="cuarto borrado", color="#c0885a",
                     antes={0: {"categoria_path": ["Cocina"]}},
                     rooms_antes=["Cocina", "Sala"])
    assert e.rooms_antes == ["Cocina", "Sala"]
    assert _entrada().rooms_antes is None


def test_vaciar_el_historial():
    """Al importar material nuevo, lo de antes ya no aplica a nada."""
    h = History()
    h.push(_entrada())
    h.clear()
    assert h.entries() == []
    assert h.undo_last() is None
