from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import SIN_CLASIFICAR, ClipSheet, ClipThumbnail

VERTICAL = 9 / 16
HORIZONTAL = 16 / 9


def _clip(n: int, cuarto: str | None = None, aspect: float = HORIZONTAL,
          flag: str = "none") -> ClipThumbnail:
    return ClipThumbnail(
        path=Path(f"/tmp/C{n:04d}.MP4"),
        room_label=cuarto or SIN_CLASIFICAR,
        flag=flag,
        room_color=theme.room_color(0) if cuarto else None,
        aspect_ratio=aspect,
    )


def _sheet(qtbot, clips) -> ClipSheet:
    sheet = ClipSheet()
    qtbot.addWidget(sheet)
    sheet.resize(815, 900)
    sheet.set_clips(clips)
    return sheet


def _pixmap(color=Qt.GlobalColor.red) -> QPixmap:
    pm = QPixmap(40, 40)
    pm.fill(color)
    return pm


# --- proporcion real -------------------------------------------------------


def test_una_tarjeta_vertical_es_mas_alta_que_ancha(qtbot):
    """QSS no tiene aspect-ratio: el alto se calcula del ancho. Sin esto
    un clip vertical queda de 45 px en una tile apaisada."""
    sheet = _sheet(qtbot, [_clip(1, "Cocina", VERTICAL)])
    tarjeta = sheet.item_widgets[0]
    assert tarjeta.height() > tarjeta.width()


def test_una_tarjeta_horizontal_es_mas_ancha_que_alta(qtbot):
    sheet = _sheet(qtbot, [_clip(1, "Cocina", HORIZONTAL)])
    tarjeta = sheet.item_widgets[0]
    assert tarjeta.width() > tarjeta.height()


def test_verticales_y_horizontales_conviven(qtbot):
    sheet = _sheet(qtbot, [_clip(1, "Cocina", VERTICAL), _clip(2, "Cocina", HORIZONTAL)])
    assert sheet.item_widgets[0].height() > sheet.item_widgets[1].height()


# --- Regla 1: item_widgets va por indice de clip ---------------------------


def test_las_miniaturas_se_entregan_por_indice_de_clip_no_por_posicion(qtbot):
    """Los clips llegan agrupados, pero item_widgets sigue en el orden de
    self.clips: si no, las miniaturas caen en la tarjeta equivocada, y de
    forma intermitente porque llegan de hilos en desorden."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Cocina"), _clip(2, "Sala")])
    assert sheet.count() == 3
    sheet.item_widgets[1].set_pixmap(_pixmap())
    assert sheet.item_widgets[1].has_pixmap()
    assert not sheet.item_widgets[0].has_pixmap()
    assert not sheet.item_widgets[2].has_pixmap()


def test_el_orden_de_item_widgets_no_depende_del_agrupamiento(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Cocina")])
    assert sheet.item_widgets[0].clip.path.name == "C0000.MP4"
    assert sheet.item_widgets[1].clip.path.name == "C0001.MP4"


# --- Regla 2: agrupar es re-colocar, no reconstruir ------------------------


def test_reclasificar_mueve_la_tarjeta_sin_recrearla(qtbot):
    """Reconstruir borraria los QPixmap que ya trajeron los _ThumbnailJob."""
    clips = [_clip(0, "Sala"), _clip(1, "Cocina")]
    sheet = _sheet(qtbot, clips)
    antes = sheet.item_widgets[0]
    antes.set_pixmap(_pixmap())
    clips[0] = _clip(0, "Cocina")
    sheet.update_clips(clips)
    assert sheet.item_widgets[0] is antes
    assert antes.has_pixmap()


def test_set_current_no_reconstruye_las_tarjetas(qtbot):
    """Reconstruir dentro del mousePressEvent de la propia tarjeta terminó
    en SIGSEGV en macOS."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Cocina")])
    antes = list(sheet.item_widgets)
    sheet.set_current(1)
    assert sheet.item_widgets == antes


def test_update_clips_preserva_la_miniatura_si_no_cambio_nada(qtbot):
    clips = [_clip(0, "Sala")]
    sheet = _sheet(qtbot, clips)
    sheet.item_widgets[0].set_pixmap(_pixmap())
    sheet.update_clips(clips)
    assert sheet.item_widgets[0].has_pixmap()


# --- Regla 3: un bloque por grupo ------------------------------------------


def test_los_clips_se_agrupan_por_cuarto(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Cocina"), _clip(2, "Sala")])
    assert set(sheet.group_titles()) == {"Sala", "Cocina"}


def test_los_sin_clasificar_van_primero(qtbot):
    """Es la cola de trabajo: lo que falta va arriba."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None)])
    assert sheet.group_titles()[0] == SIN_CLASIFICAR


def test_un_grupo_que_se_vacia_desaparece(qtbot):
    clips = [_clip(0, "Sala"), _clip(1, "Cocina")]
    sheet = _sheet(qtbot, clips)
    assert len(sheet.group_titles()) == 2
    clips[0] = _clip(0, "Cocina")
    sheet.update_clips(clips)
    assert sheet.group_titles() == ["Cocina"]


def test_el_encabezado_de_grupo_lleva_su_conteo(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala"), _clip(2, "Cocina")])
    bloques = {b.titulo: b for b in sheet._ordered_blocks()}
    assert bloques["Sala"].count_label.text() == "2"
    assert bloques["Cocina"].count_label.text() == "1"


# --- seleccion (portada del filmstrip) -------------------------------------


def test_click_simple_selecciona_uno_y_emite(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala")])
    with qtbot.waitSignal(sheet.clip_clicked) as blocker:
        sheet.item_widgets[1].clicked.emit(Qt.KeyboardModifier.NoModifier)
    assert blocker.args == [1]
    assert sheet.selected_indices() == [1]


def test_shift_click_selecciona_el_rango(qtbot):
    sheet = _sheet(qtbot, [_clip(i, "Sala") for i in range(4)])
    sheet.item_widgets[0].clicked.emit(Qt.KeyboardModifier.NoModifier)
    sheet.item_widgets[2].clicked.emit(Qt.KeyboardModifier.ShiftModifier)
    assert sheet.selected_indices() == [0, 1, 2]


def test_ctrl_click_alterna(qtbot):
    sheet = _sheet(qtbot, [_clip(i, "Sala") for i in range(3)])
    sheet.item_widgets[0].clicked.emit(Qt.KeyboardModifier.NoModifier)
    sheet.item_widgets[2].clicked.emit(Qt.KeyboardModifier.ControlModifier)
    assert sheet.selected_indices() == [0, 2]
    sheet.item_widgets[2].clicked.emit(Qt.KeyboardModifier.ControlModifier)
    assert sheet.selected_indices() == [0]


# --- scrub con el mouse (ya existia, se conserva) --------------------------


def test_el_hover_cambia_el_frame_mostrado(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    tarjeta = sheet.item_widgets[0]
    tarjeta.set_frames([_pixmap(Qt.GlobalColor.red), _pixmap(Qt.GlobalColor.green),
                        _pixmap(Qt.GlobalColor.blue)])
    assert tarjeta._shown_index == 1  # poster = el del medio
    tarjeta._show_frame(2)
    assert tarjeta._shown_index == 2


def test_al_salir_vuelve_al_poster(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    tarjeta = sheet.item_widgets[0]
    tarjeta.set_frames([_pixmap(), _pixmap(), _pixmap()])
    tarjeta._show_frame(0)
    tarjeta.leaveEvent(None)
    assert tarjeta._shown_index == 1


# --- estado visual ---------------------------------------------------------


def test_el_clip_actual_tiene_borde_de_acento(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.set_current(0)
    assert theme.CURRENT_COLOR in sheet.item_widgets[0].styleSheet()


def test_pick_pinta_el_borde_de_pick(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala", flag="pick")])
    sheet.set_current(-1)
    assert theme.PICK_COLOR in sheet.item_widgets[0].styleSheet()


def test_el_cuarto_va_en_una_franja_lateral_no_en_el_borde(qtbot):
    """Canal distinto del estado: posicion, no familia de color."""
    sheet = _sheet(qtbot, [_clip(0, "Cocina")])
    estilo = sheet.item_widgets[0].styleSheet()
    assert f"border-left: 3px solid {theme.room_color(0)}" in estilo


def test_no_hay_alto_fijo_de_banda(qtbot):
    """El filmstrip viejo tenia setFixedHeight(220) y por eso el video
    perdia 250 px de alto."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    assert sheet.maximumHeight() > 1000
