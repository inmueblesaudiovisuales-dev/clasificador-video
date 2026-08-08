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


def test_leyenda_de_estados(qtbot):
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    texto = rail.flags_label.text()
    assert "41 picks" in texto and "9 rejects" in texto and "12 sin clasificar" in texto


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
