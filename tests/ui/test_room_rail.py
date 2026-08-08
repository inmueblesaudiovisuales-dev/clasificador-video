from clasificador_video.ui import theme
from clasificador_video.ui.room_rail import MAX_TECLAS, RoomRail


def _rail(qtbot) -> RoomRail:
    rail = RoomRail()
    qtbot.addWidget(rail)
    return rail


def test_ancho_fijo_del_mockup(qtbot):
    assert _rail(qtbot).width() == theme.RAIL_WIDTH


def test_una_fila_por_cuarto(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {"Cocina": 24, "Sala": 16})
    assert [f.nombre for f in rail.rows] == ["Cocina", "Sala"]
    assert rail.rows[0].count_label.text() == "24"


def test_los_primeros_nueve_cuartos_tienen_tecla(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms([f"C{i}" for i in range(9)], {})
    assert [f.key_cap.text() for f in rail.rows] == [str(i) for i in range(1, 10)]


def test_del_decimo_en_adelante_no_hay_tecla(qtbot):
    """Los atajos numericos llegan hasta el noveno: el badge queda vacio
    en vez de mentir con un numero que no funciona."""
    rail = _rail(qtbot)
    rail.set_rooms([f"C{i}" for i in range(11)], {})
    assert rail.rows[MAX_TECLAS].key_cap.text() == ""
    assert rail.rows[MAX_TECLAS].key_cap.property("sin_tecla") is True
    assert rail.rows[0].key_cap.property("sin_tecla") is False


def test_cada_cuarto_lleva_su_color_de_identidad(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    assert theme.room_color(0) in rail.rows[0].swatch.styleSheet()
    assert theme.room_color(1) in rail.rows[1].swatch.styleSheet()


def test_repoblar_no_acumula_filas(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    rail.set_rooms(["Cocina"], {})
    assert len(rail.rows) == 1


def test_progreso_muestra_clasificados_sobre_total(qtbot):
    rail = _rail(qtbot)
    rail.set_progress(116, 128, pendientes=12)
    assert rail.progress_big.text() == "116"
    assert rail.progress_total.text() == "/128"


def test_la_leyenda_usa_etiquetas_cortas_que_entran_en_200px(qtbot):
    """`● 41 picks ● 9 rejects ● 12 sin clasificar` no entra en el rail y se
    cortaba a la mitad. El mockup se apoya en el color, no en el texto."""
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    assert [p.text() for p in rail.leyenda.puntos] == ["41", "9", "12"]
    assert rail.leyenda.sizeHint().width() <= theme.RAIL_WIDTH


def test_cada_punto_de_la_leyenda_lleva_el_color_de_su_estado(qtbot):
    """Todos grises es informacion tirada a la basura."""
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    assert rail.leyenda.colores() == [
        theme.PICK_COLOR, theme.REJECT_COLOR, theme.PENDING_COLOR,
    ]


def test_la_leyenda_dice_que_es_cada_numero_al_pasar_el_mouse(qtbot):
    """El numero pelado es criptico: el color desambigua de un vistazo y el
    tooltip lo confirma sin gastar ancho."""
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    assert "picks" in rail.leyenda.puntos[0].toolTip()
    assert "rejects" in rail.leyenda.puntos[1].toolTip()
    assert "sin clasificar" in rail.leyenda.puntos[2].toolTip()


def test_el_enter_de_buscar_va_dentro_de_un_keycap(qtbot):
    """Igual que las teclas de cuarto: si es una tecla, se ve como tecla."""
    rail = _rail(qtbot)
    assert rail.find_key.text() == "⏎"
    assert rail.find_key.objectName() == "keyCap"
    assert rail.find_hint.text() == "buscar"


def test_solo_los_tramos_de_los_extremos_van_redondeados(qtbot):
    """Nueve pildoras separadas no se leen como una sola barra de progreso.
    Redondear el contenedor no sirve: verificado contra Qt, el border-radius
    de un padre NO recorta a sus hijos."""
    rail = _rail(qtbot)
    rail.set_progress(116, 128, 12)
    rail.set_rooms(["Cocina", "Sala", "Baño"], {"Cocina": 24, "Sala": 16, "Baño": 8})
    tramos = rail.progress_bar._tramos
    assert len(tramos) == 4  # tres cuartos mas el tramo de lo que falta
    assert "border-top-left-radius" in tramos[0].styleSheet()
    assert "border-top-right-radius" in tramos[-1].styleSheet()
    assert all("radius" not in t.styleSheet() for t in tramos[1:-1])


def test_el_tramo_de_lo_que_falta_usa_el_color_de_pendiente(qtbot):
    rail = _rail(qtbot)
    rail.set_progress(116, 128, 12)
    rail.set_rooms(["Cocina"], {"Cocina": 24})
    assert theme.PENDING_COLOR in rail.progress_bar._tramos[-1].styleSheet()


def test_el_cuarto_actual_queda_marcado(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    rail.set_current_room("Sala")
    assert rail.rows[1].property("actual") is True
    assert rail.rows[0].property("actual") is False


def test_el_boton_de_importar_emite_su_senal(qtbot):
    rail = _rail(qtbot)
    with qtbot.waitSignal(rail.import_requested):
        rail.import_button.click()


def test_un_nombre_largo_se_elide_en_vez_de_desbordar(qtbot):
    """QSS no tiene text-overflow: sin elidir, un nombre largo estira el
    rail y el layout deja de parecerse al mockup."""
    rail = _rail(qtbot)
    rail.set_rooms(["Recámara principal con vestidor y terraza"], {})
    rail.show()
    qtbot.waitExposed(rail)
    etiqueta = rail.rows[0].name_label
    assert etiqueta.full_text() == "Recámara principal con vestidor y terraza"
    assert etiqueta.text() != etiqueta.full_text()
    assert etiqueta.text().endswith("…")


def test_no_hay_panel_de_material_importado(qtbot):
    """Ocupaba media columna para listar nombres de carpetas y no existe
    en el mockup."""
    rail = _rail(qtbot)
    assert not hasattr(rail, "ingest_list")
