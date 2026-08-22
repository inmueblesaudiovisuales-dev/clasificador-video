from PySide6.QtCore import Qt

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
    rail.set_flags(41, 9, 12, destacados=6)
    # cuatro estados desde la F7: el `dest.` va primero, como en el mockup.
    # Y solo el primero lleva palabra --`6 dest.`--, tambien como el mockup:
    # es el estado que menos clips tiene y el mas facil de confundir con un
    # conteo de picks si va pelado. La F10 le devolvio la palabra.
    assert [p.text() for p in rail.leyenda.puntos] == ["6 dest.", "41", "9", "12"]
    assert rail.leyenda.sizeHint().width() <= theme.RAIL_WIDTH


def test_cada_punto_de_la_leyenda_lleva_el_color_de_su_estado(qtbot):
    """Todos grises es informacion tirada a la basura."""
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12, destacados=6)
    assert rail.leyenda.colores() == [
        theme.STAR_COLOR, theme.PICK_COLOR, theme.REJECT_COLOR,
        theme.PENDING_COLOR,
    ]


def test_la_leyenda_dice_que_es_cada_numero_al_pasar_el_mouse(qtbot):
    """El numero pelado es criptico: el color desambigua de un vistazo y el
    tooltip lo confirma sin gastar ancho."""
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12, destacados=6)
    assert "destacados" in rail.leyenda.puntos[0].toolTip()
    assert "picks" in rail.leyenda.puntos[1].toolTip()
    assert "rejects" in rail.leyenda.puntos[2].toolTip()
    assert "sin clasificar" in rail.leyenda.puntos[3].toolTip()


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


# --- F3: el rail se edita en el lugar ---------------------------------------
#
# Menu contextual y doble click, no arrastrar: son acciones de una vez por
# shooting. Decidido con Bruno el 2026-08-08.


def test_el_rail_arranca_vacio_y_no_pretende_que_haya_cuartos(qtbot):
    """La app abre lista para trabajar: sin paso previo de configuracion."""
    rail = _rail(qtbot)
    assert rail.rows == []
    assert not rail.new_room_row.isHidden()


def test_crear_un_cuarto_emite_su_nombre(qtbot):
    rail = _rail(qtbot)
    with qtbot.waitSignal(rail.room_created) as blocker:
        rail._crear_cuarto("Alberca")
    assert blocker.args == ["Alberca"]


def test_crear_un_cuarto_con_nombre_vacio_no_emite_nada(qtbot):
    rail = _rail(qtbot)
    with qtbot.assertNotEmitted(rail.room_created):
        rail._crear_cuarto("   ")


def test_renombrar_emite_el_nombre_viejo_y_el_nuevo(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    with qtbot.waitSignal(rail.room_renamed) as blocker:
        rail.rows[0].pedir_renombrar("Cocina chica")
    assert blocker.args == ["Cocina", "Cocina chica"]


def test_renombrar_al_mismo_nombre_no_emite_nada(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {})
    with qtbot.assertNotEmitted(rail.room_renamed):
        rail.rows[0].pedir_renombrar("Cocina")
        rail.rows[0].pedir_renombrar("  ")


def test_mover_emite_el_cuarto_y_la_direccion(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    with qtbot.waitSignal(rail.room_moved) as blocker:
        rail.rows[1].pedir_mover(-1)
    assert blocker.args == ["Sala", -1]


def test_eliminar_emite_el_cuarto(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    with qtbot.waitSignal(rail.room_removed) as blocker:
        rail.rows[0].pedir_eliminar()
    assert blocker.args == ["Cocina"]


def test_la_fila_de_nuevo_cuarto_queda_siempre_al_pie_de_la_lista(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    layout = rail._rooms_layout
    assert layout.itemAt(layout.count() - 1).widget() is rail.new_room_row
    rail.set_rooms(["Cocina", "Sala", "Baño"], {})
    assert layout.itemAt(layout.count() - 1).widget() is rail.new_room_row


def test_el_banner_de_subcuarto_ya_no_existe(qtbot):
    """Murio con los subcuartos en la F3."""
    assert not hasattr(_rail(qtbot), "subroom_banner")


# --- F4: el historial al pie del rail ---------------------------------------


def _entrada(etiqueta="Cocina", detalle="→ 6 clips", color=None):
    from clasificador_video.history import HistoryEntry
    return HistoryEntry(etiqueta=etiqueta, detalle=detalle,
                        color=color or theme.room_color(0), antes={})


def test_el_historial_muestra_lo_ultimo_arriba(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada("Sala"), _entrada("Cocina")])
    assert [f.etiqueta for f in rail.history_rows] == ["Sala", "Cocina"]


def test_la_primera_fila_va_resaltada_porque_es_la_que_deshace_cmd_z(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada("Sala"), _entrada("Cocina")])
    assert rail.history_rows[0].property("top") is True
    assert rail.history_rows[1].property("top") is False


def test_el_historial_no_muestra_mas_de_cuatro_filas(qtbot):
    """El rail mide 200 px: mas filas empujan la lista de cuartos."""
    from clasificador_video.ui.room_rail import MAX_HISTORIAL
    rail = _rail(qtbot)
    rail.set_history([_entrada(str(i)) for i in range(10)])
    assert len(rail.history_rows) == MAX_HISTORIAL


def test_cada_fila_lleva_el_color_de_su_accion(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada(color=theme.REJECT_COLOR)])
    assert theme.REJECT_COLOR in rail.history_rows[0].swatch.styleSheet()


def test_la_fila_dice_que_paso_y_sobre_cuantos_clips(qtbot):
    """Dos etiquetas: QUE paso va en negritas y claro, sobre QUE en gris."""
    rail = _rail(qtbot)
    rail.set_history([_entrada("Baño 1", "→ 6 clips")])
    fila = rail.history_rows[0]
    assert fila.what_label.full_text() == "Baño 1"
    assert fila.detail_label.text() == "→ 6 clips"


def test_revertir_una_fila_emite_su_id(qtbot):
    rail = _rail(qtbot)
    entrada = _entrada()
    rail.set_history([entrada])
    with qtbot.waitSignal(rail.revert_requested) as blocker:
        rail.history_rows[0].undo_button.click()
    assert blocker.args == [entrada.id]


def test_sin_historial_el_panel_se_esconde_entero(qtbot):
    """Un panel vacio con su linea separadora es ruido: al abrir la app no
    hay nada que deshacer."""
    rail = _rail(qtbot)
    rail.set_history([])
    assert rail.history_panel.isHidden()
    rail.set_history([_entrada()])
    assert not rail.history_panel.isHidden()


def test_repoblar_el_historial_no_acumula_filas(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada("A"), _entrada("B")])
    rail.set_history([_entrada("C")])
    assert [f.etiqueta for f in rail.history_rows] == ["C"]


def test_un_texto_largo_se_elide_en_vez_de_desbordar(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada("Recámara principal con vestidor y terraza")])
    rail.show()
    qtbot.waitExposed(rail)
    assert rail.history_rows[0].what_label.text().endswith("…")


def test_los_botones_de_revertir_no_se_roban_el_foco(qtbot):
    """Con foco, la barra espaciadora los activaria en vez de reproducir."""
    from PySide6.QtCore import Qt
    rail = _rail(qtbot)
    rail.set_history([_entrada()])
    assert rail.history_rows[0].undo_button.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_el_historial_lleva_su_encabezado_con_la_tecla(qtbot):
    """El mockup lo encabeza con `Historial` y un keycap `⌘Z`: sin eso, las
    filas no dicen que la tecla las deshace."""
    rail = _rail(qtbot)
    rail.set_history([_entrada()])
    assert rail.history_caption.text() == "HISTORIAL"
    assert rail.history_key.text() == "⌘Z"
    assert rail.history_key.objectName() == "keyCap"


def test_el_glifo_de_revertir_se_dibuja_de_verdad(qtbot):
    """La regla generica de QPushButton trae `padding: 8px 14px`. Heredarlo
    manda el sizeHint del boton a 38x29 contra un tamaño fijo de 18x18, y el
    glifo `↺` se recorta ENTERO: la fila se veia sin boton. Solo se detecta
    mirando pixeles con la hoja de estilos puesta -- el sizeHint sin estilos
    no dice nada.
    """
    from PySide6.QtWidgets import QApplication

    QApplication.instance().setStyleSheet(theme.build_stylesheet())
    rail = _rail(qtbot)
    rail.set_history([_entrada()])
    rail.show()
    qtbot.waitExposed(rail)
    imagen = rail.history_rows[0].undo_button.grab().toImage()
    colores = {imagen.pixelColor(x, y).name()
               for x in range(imagen.width()) for y in range(imagen.height())}
    assert len(colores) > 1, "el boton salio de un solo color: el glifo no se dibujo"


# --- ⌘R: manejar los cuartos sin mouse --------------------------------------


def test_enfocar_el_rail_pone_el_foco_en_el_primer_cuarto(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    rail.show()
    qtbot.waitExposed(rail)
    rail.focus_rooms()
    assert rail.focusWidget() is rail.rows[0]


def test_sin_cuartos_enfocar_el_rail_abre_el_dialogo_de_crear(qtbot, monkeypatch):
    """Enfocar una lista vacia no sirve de nada: lo unico que se puede hacer
    ahi es crear el primero."""
    rail = _rail(qtbot)
    llamado = []
    monkeypatch.setattr(rail, "_pedir_cuarto_nuevo", lambda: llamado.append(True))
    rail.focus_rooms()
    assert llamado == [True]


def test_las_flechas_mueven_el_foco_entre_cuartos(qtbot):
    from PySide6.QtCore import Qt

    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala", "Baño"], {})
    rail.show()
    qtbot.waitExposed(rail)
    rail.focus_rooms()
    qtbot.keyClick(rail.rows[0], Qt.Key.Key_Down)
    assert rail.focusWidget() is rail.rows[1]
    qtbot.keyClick(rail.rows[1], Qt.Key.Key_Up)
    assert rail.focusWidget() is rail.rows[0]


def test_el_foco_no_se_sale_por_los_extremos(qtbot):
    from PySide6.QtCore import Qt

    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    rail.show()
    qtbot.waitExposed(rail)
    rail.focus_rooms()
    qtbot.keyClick(rail.rows[0], Qt.Key.Key_Up)
    assert rail.focusWidget() is rail.rows[0]


def test_borrar_pide_eliminar_el_cuarto_enfocado(qtbot):
    from PySide6.QtCore import Qt

    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    rail.show()
    qtbot.waitExposed(rail)
    rail.focus_rooms()
    with qtbot.waitSignal(rail.room_removed) as blocker:
        qtbot.keyClick(rail.rows[0], Qt.Key.Key_Backspace)
    assert blocker.args == ["Cocina"]


def test_alt_con_flecha_reordena_el_cuarto_enfocado(qtbot):
    """Reordenar ES cambiar la tecla, asi que va con modificador: una flecha
    sola solo mueve el foco."""
    from PySide6.QtCore import Qt

    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    rail.show()
    qtbot.waitExposed(rail)
    rail.focus_rooms()
    with qtbot.waitSignal(rail.room_moved) as blocker:
        qtbot.keyClick(rail.rows[0], Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
    assert blocker.args == ["Cocina", 1]


def test_la_fila_enfocada_se_ve(qtbot):
    """Un foco invisible es peor que no tenerlo: no sabes sobre que fila
    actuan ⏎, ⌫ y ⌥↑/⌥↓.

    Se comprueba la REGLA de estilo y no el pixel: el pseudo-estado `:focus`
    solo se pinta con la ventana activa, y bajo `offscreen` no la hay. Que la
    fila se vea distinta al enfocarla queda como prueba a mano.
    """
    hoja = theme.build_stylesheet()
    assert "QWidget#roomRow:focus" in hoja
    assert theme.CURRENT_COLOR in hoja.split("QWidget#roomRow:focus")[1][:200]


def test_las_filas_de_cuarto_se_pueden_enfocar(qtbot):
    from PySide6.QtCore import Qt

    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {})
    assert rail.rows[0].focusPolicy() == Qt.FocusPolicy.StrongFocus


# --- no reconstruir lo que no cambió ----------------------------------------
#
# `_refresh_rail` corre en CADA tecla. Reconstruir filas, leyenda, barra e
# historial en cada una tiraba ~21 widgets por tecla que nunca se liberaban:
# medido, 1237 widgets de más tras 60 teclas.


def test_repoblar_con_los_mismos_cuartos_no_recrea_las_filas(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {"Cocina": 1, "Sala": 2})
    antes = list(rail.rows)
    rail.set_rooms(["Cocina", "Sala"], {"Cocina": 5, "Sala": 2})
    assert rail.rows == antes, "recreo las filas sin que cambiara la lista"
    assert rail.rows[0].count_label.text() == "5", "pero el conteo sí se actualiza"


def test_cambiar_la_lista_de_cuartos_si_reconstruye(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {})
    rail.set_rooms(["Cocina", "Sala"], {})
    assert [f.nombre for f in rail.rows] == ["Cocina", "Sala"]


def test_renombrar_un_cuarto_si_reconstruye(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {})
    rail.set_rooms(["Cocineta"], {})
    assert [f.nombre for f in rail.rows] == ["Cocineta"]


def test_la_leyenda_no_se_recrea_si_los_numeros_no_cambian(qtbot):
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    antes = list(rail.leyenda.puntos)
    rail.set_flags(41, 9, 12)
    assert rail.leyenda.puntos == antes


def test_la_leyenda_se_actualiza_sin_recrearse(qtbot):
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    antes = list(rail.leyenda.puntos)
    rail.set_flags(42, 9, 11)
    assert rail.leyenda.puntos == antes, "recrear no hace falta: cambia el texto"
    assert [p.text() for p in rail.leyenda.puntos] == ["0 dest.", "42", "9", "11"]


def test_la_barra_de_progreso_no_se_recrea_si_no_cambio(qtbot):
    rail = _rail(qtbot)
    rail.set_progress(10, 20, 10)
    rail.set_rooms(["Cocina"], {"Cocina": 10})
    antes = list(rail.progress_bar._tramos)
    rail.set_rooms(["Cocina"], {"Cocina": 10})
    assert rail.progress_bar._tramos == antes


def test_el_historial_no_se_recrea_si_son_las_mismas_entradas(qtbot):
    rail = _rail(qtbot)
    entradas = [_entrada("Cocina"), _entrada("Sala")]
    rail.set_history(entradas)
    antes = list(rail.history_rows)
    rail.set_history(entradas)
    assert rail.history_rows == antes


def test_el_historial_si_se_rehace_cuando_cambia(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada("Cocina")])
    rail.set_history([_entrada("Sala"), _entrada("Cocina")])
    assert [f.etiqueta for f in rail.history_rows] == ["Sala", "Cocina"]


# --- F7 Task 8: la fila fija de `S` ------------------------------------------


def test_la_fila_de_S_dice_a_que_cuarto_aplicaria(qtbot):
    """Es una confirmacion, no un acto de memoria."""
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    rail.set_same_room("Cocina", theme.room_color(0))
    assert "Cocina" in rail.same_row.name_label.full_text()
    assert not rail.same_row.isHidden()


def test_sin_cuarto_anterior_la_fila_de_S_no_se_ve(qtbot):
    rail = _rail(qtbot)
    rail.set_same_room(None, None)
    assert rail.same_row.isHidden()
    assert rail.same_caption.isHidden()


def test_la_fila_de_S_va_arriba_de_los_cuartos(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {})
    rail.set_same_room("Cocina", theme.room_color(0))
    layout = rail._rooms_layout
    assert layout.indexOf(rail.same_caption) < layout.indexOf(rail.same_row)
    assert layout.indexOf(rail.same_row) < layout.indexOf(rail.rows[0])


def test_la_fila_de_S_lleva_su_tecla_y_el_color_del_cuarto(qtbot):
    rail = _rail(qtbot)
    rail.set_same_room("Sala", theme.room_color(1))
    assert rail.same_row.key_cap.text() == "S"
    assert theme.room_color(1) in rail.same_row.swatch.styleSheet()


def test_la_fila_de_S_sobrevive_a_reconstruir_los_cuartos(qtbot):
    """`set_rooms` reconstruye las filas: si la de `S` viviera entre ellas se
    la llevaria puesta, y la tecla quedaria anunciada sin fila."""
    rail = _rail(qtbot)
    rail.set_same_room("Cocina", theme.room_color(0))
    rail.set_rooms(["Cocina", "Sala"], {"Cocina": 3})
    assert not rail.same_row.isHidden()
    assert "Cocina" in rail.same_row.name_label.full_text()


def test_un_renglon_bloqueado_se_apaga_y_dice_por_que(qtbot):
    """No desaparece: Bruno tiene que poder ver que la accion existio, igual
    que un proyecto que no se encuentra se ve apagado en vez de esfumarse."""
    rail = _rail(qtbot)
    entrada = _entrada(etiqueta="Card C", detalle="→ bin nuevo")

    rail.set_history([entrada], {entrada.id: "ya tiene clips"})

    fila = rail.history_rows[0]
    assert not fila.undo_button.isEnabled()
    assert "ya tiene clips" in fila.toolTip()


def test_el_renglon_se_vuelve_a_dibujar_al_cambiar_lo_bloqueado(qtbot):
    """`set_history` se salta el redibujado cuando los ids son los mismos, y
    los ids NO cambian al bloquearse: sin mirarlo, el renglon se quedaba
    prendido despues de dejar de poderse."""
    rail = _rail(qtbot)
    entrada = _entrada(etiqueta="Card C", detalle="→ bin nuevo")
    rail.set_history([entrada])
    assert rail.history_rows[0].undo_button.isEnabled()

    rail.set_history([entrada], {entrada.id: "ya tiene clips"})

    assert not rail.history_rows[0].undo_button.isEnabled()


def _espiar_renombrado(monkeypatch):
    """Renombrar abre un `QInputDialog` modal, que en un test cuelga. Se
    espía en vez de abrirlo."""
    from PySide6.QtWidgets import QInputDialog
    abiertos = []
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: abiertos.append(True) or ("", False))
    return abiertos


def test_enter_en_una_fila_del_rail_pide_asignar(qtbot, monkeypatch):
    """Lo que Bruno encontró el 2026-08-20: `⏎` con una fila enfocada abría
    el renombrado, así que «poner enter no me deja seleccionar cuartos, solo
    hacer nuevos». Lo que uno quiere hacer con un cuarto mientras clasifica
    es ponérselo a un clip; renombrar es mantenimiento."""
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {"Cocina": 3, "Sala": 2})
    abiertos = _espiar_renombrado(monkeypatch)
    pedidos = []
    rail.room_assign_requested.connect(pedidos.append)

    qtbot.keyClick(rail.rows[0], Qt.Key.Key_Return)

    assert pedidos == ["Cocina"]
    assert abiertos == []


def test_f2_sigue_renombrando(qtbot, monkeypatch):
    """Renombrar no se pierde: se cambia de tecla."""
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {"Cocina": 3})
    abiertos = _espiar_renombrado(monkeypatch)

    qtbot.keyClick(rail.rows[0], Qt.Key.Key_F2)

    assert abiertos == [True]


def test_el_doble_click_sigue_renombrando(qtbot, monkeypatch):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {"Cocina": 3})
    abiertos = _espiar_renombrado(monkeypatch)

    qtbot.mouseDClick(rail.rows[0], Qt.MouseButton.LeftButton)

    assert abiertos == [True]
