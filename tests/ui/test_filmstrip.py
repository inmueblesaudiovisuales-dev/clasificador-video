# tests/ui/test_filmstrip.py
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from clasificador_video.ui.filmstrip import ClipThumbnail, Filmstrip


def test_item_del_filmstrip_pinta_su_propio_fondo_y_borde(qtbot):
    """Bug real de v1 (visto en capturas): un QWidget plano sin
    WA_StyledBackground no pinta su propio borde por QSS -- la propiedad
    se hereda a los QLabel hijos, que la pintan cada uno por separado,
    dando dos cajas en vez de una sola envolviendo miniatura + nombre.
    """
    from PySide6.QtCore import Qt

    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    item = strip.item_widgets[0]
    assert item.testAttribute(Qt.WA_StyledBackground)
    assert item.objectName() == "clipItem"


def test_borde_de_pick_no_se_hereda_a_los_labels_hijos(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="pick")])
    item = strip.item_widgets[0]
    assert "border: none" in item.styleSheet()


def test_filmstrip_agrega_un_thumbnail_por_clip(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="Sin clasificar", flag="none"),
        ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="pick"),
    ])
    assert strip.count() == 2


def test_estilo_de_pick_aplica_borde_verde(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="pick")])
    item = strip.item_widgets[0]
    assert "border: 2px solid #3ddc84" in item.styleSheet()


def test_estilo_de_reject_aplica_borde_rosa(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="reject")])
    item = strip.item_widgets[0]
    assert "border: 2px solid #ff5566" in item.styleSheet()


def test_sin_flag_no_aplica_borde_de_color(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Sin clasificar", flag="none")])
    item = strip.item_widgets[0]
    assert "#3ddc84" not in item.styleSheet()
    assert "#ff5566" not in item.styleSheet()


def test_franja_de_color_de_cuarto_no_pelea_con_colores_de_estado(qtbot):
    """El acento de identidad de cuarto vive en border-top (una posicion
    distinta del borde de estado) y usa la paleta apagada de theme.py,
    nunca las familias de color de pick/reject/actual."""
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="Living",
                      flag="pick", room_color="#6f8bb0"),
    ])
    item = strip.item_widgets[0]
    assert "border-top: 3px solid #6f8bb0" in item.styleSheet()
    assert "border: 2px solid #3ddc84" in item.styleSheet()


def test_item_puede_recibir_un_pixmap(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    pm = QPixmap(10, 10)
    pm.fill()
    strip.item_widgets[0].set_pixmap(pm)
    assert strip.item_widgets[0].has_pixmap()


def test_set_frames_muestra_el_frame_del_medio_como_poster(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    item = strip.item_widgets[0]
    frames = [QPixmap(10, 10) for _ in range(5)]
    for i, pm in enumerate(frames):
        pm.fill(Qt.GlobalColor.black)
    item.set_frames(frames)
    assert item.has_pixmap()
    assert item._poster_index == 2


def test_mouse_move_sobre_la_miniatura_cambia_el_frame_mostrado(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    item = strip.item_widgets[0]
    item.resize(100, 100)
    frames = [QPixmap(10, 10) for _ in range(5)]
    item.set_frames(frames)
    shown_at_poster = item._image_label.pixmap().cacheKey()

    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent

    event = QMouseEvent(
        QMouseEvent.Type.MouseMove, QPointF(99, 10), QPointF(99, 10), Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
    )
    item.mouseMoveEvent(event)
    shown_after_move = item._image_label.pixmap().cacheKey()
    assert shown_after_move != shown_at_poster


def test_leave_event_vuelve_al_poster(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    item = strip.item_widgets[0]
    item.resize(100, 100)
    frames = [QPixmap(10, 10) for _ in range(5)]
    item.set_frames(frames)

    from PySide6.QtCore import QEvent

    calls = []
    item._show_frame = lambda i, _orig=item._show_frame: (calls.append(i), _orig(i))[1]
    item.leaveEvent(QEvent(QEvent.Type.Leave))
    assert calls == [item._poster_index]


def test_barra_de_rango_pinta_el_in_out_marcado(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(
        path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none",
        in_frame=30, out_frame=60, duration_frames=120,
    )])
    style = strip.item_widgets[0]._range_bar.styleSheet()
    assert "qlineargradient" in style


def test_barra_de_rango_sin_marca_queda_neutra(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    style = strip.item_widgets[0]._range_bar.styleSheet()
    assert "qlineargradient" not in style


def test_update_clips_preserva_el_pixmap_si_la_cantidad_no_cambia(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    pm = QPixmap(10, 10)
    pm.fill()
    strip.item_widgets[0].set_pixmap(pm)

    strip.update_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="Y", flag="pick")])
    assert strip.item_widgets[0].has_pixmap()
    assert "border: 2px solid #3ddc84" in strip.item_widgets[0].styleSheet()


def test_update_clips_reconstruye_si_cambia_la_cantidad_de_clips(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    ids_antes = [id(w) for w in strip.item_widgets]
    strip.update_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none"),
        ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Y", flag="none"),
    ])
    assert strip.count() == 2
    assert [id(w) for w in strip.item_widgets][:1] != ids_antes


def test_clip_actual_tiene_borde_de_acento(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    strip.set_current(0)
    assert "border: 2px solid #ff8a3d" in strip.item_widgets[0].styleSheet()


def test_pick_sobre_borde_actual_mantiene_ambos_colores(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="pick")])
    strip.set_current(0)
    assert "border: 2px solid #3ddc84" in strip.item_widgets[0].styleSheet()
    assert "outline: 2px solid #ff8a3d" in strip.item_widgets[0].styleSheet()


def test_miniatura_grande_se_escala_a_altura_fija(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])

    pixmap_vertical_4k = QPixmap(2160, 3840)
    strip.item_widgets[0].set_pixmap(pixmap_vertical_4k)

    shown = strip.item_widgets[0]._image_label.pixmap()
    assert shown.height() == 80
    assert shown.width() < 2160


def test_click_en_un_item_emite_clip_clicked_con_su_indice(qtbot, qapp):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none"),
        ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Y", flag="none"),
    ])
    with qtbot.waitSignal(strip.clip_clicked, timeout=1000) as blocker:
        qtbot.mouseClick(strip.item_widgets[1], Qt.LeftButton)
    assert blocker.args == [1]


def test_item_del_filmstrip_muestra_cursor_de_mano(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    assert strip.item_widgets[0].cursor().shape() == Qt.PointingHandCursor


def test_ctrl_click_suma_clips_a_la_seleccion(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none"),
        ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Y", flag="none"),
        ClipThumbnail(path=Path("/c.MP4"), thumbnail_path=None, room_label="Z", flag="none"),
    ])
    strip._on_item_clicked(0, Qt.NoModifier)
    strip._on_item_clicked(2, Qt.ControlModifier)
    assert strip.selected_indices() == [0, 2]


def test_shift_click_selecciona_un_rango(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")
        for _ in range(5)
    ])
    strip._on_item_clicked(1, Qt.NoModifier)
    strip._on_item_clicked(3, Qt.ShiftModifier)
    assert strip.selected_indices() == [1, 2, 3]


def test_click_simple_reemplaza_la_seleccion_anterior(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")
        for _ in range(3)
    ])
    strip._on_item_clicked(0, Qt.ControlModifier)
    strip._on_item_clicked(1, Qt.ControlModifier)
    strip._on_item_clicked(2, Qt.NoModifier)  # click simple, sin modificadores
    assert strip.selected_indices() == [2]


def test_seleccion_multiple_emite_selection_changed(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")
        for _ in range(3)
    ])
    with qtbot.waitSignal(strip.selection_changed, timeout=1000) as blocker:
        strip._on_item_clicked(1, Qt.ControlModifier)
    assert 1 in blocker.args[0]


def test_vista_grilla_es_la_vista_por_defecto(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    assert strip.grid_view_button.isChecked()
    assert not strip.list_view_button.isChecked()


def test_cambiar_a_vista_lista_crea_una_fila_por_clip(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="Living", flag="pick"),
        ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="none"),
    ])
    strip.set_view_mode("list")
    assert strip.list_view_button.isChecked()
    assert len(strip._list_rows) == 2
    assert strip._list_rows[0]._name_label.text() == "a.MP4"


def test_fila_de_lista_en_pick_muestra_texto_de_estado(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="Living", flag="pick"),
    ])
    assert strip._list_rows[0]._flag_label.text() == "✓ Pick"


def test_click_en_fila_de_lista_tambien_actualiza_la_seleccion(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none"),
        ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Y", flag="none"),
    ])
    with qtbot.waitSignal(strip.clip_clicked, timeout=1000) as blocker:
        strip._list_rows[1].clicked.emit(Qt.NoModifier)
    assert blocker.args == [1]
    assert strip.selected_indices() == [1]


def test_miniatura_horizontal_tambien_respeta_la_altura_fija(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])

    pixmap_horizontal_4k = QPixmap(3840, 2160)
    strip.item_widgets[0].set_pixmap(pixmap_horizontal_4k)

    shown = strip.item_widgets[0]._image_label.pixmap()
    assert shown.height() <= 80
    assert shown.width() <= 140
