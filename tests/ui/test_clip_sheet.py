from pathlib import Path

import pytest

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import (
    MIN_TILE_WIDTH,
    GAP,
    SIN_CLASIFICAR,
    ClipCard,
    ClipSheet,
    ClipThumbnail,
)

VERTICAL = 9 / 16
HORIZONTAL = 16 / 9


def _clip(n: int, cuarto: str | None = None, aspect: float = HORIZONTAL,
          flag: str = "none") -> ClipThumbnail:
    return ClipThumbnail(
        path=Path(f"/tmp/C{n:04d}.MP4"),
        room_label=cuarto or SIN_CLASIFICAR,
        flag=flag,
        room_color=theme.room_color(0) if cuarto else None,
        numero=n,
        aspect_ratio=aspect,
    )


def _card(**kwargs) -> ClipCard:
    """Una tarjeta suelta, sin hoja: alcanza para probar lo que dibuja."""
    base = dict(path=Path("/tmp/C0093.MP4"), room_label=SIN_CLASIFICAR,
                flag="none", numero=93)
    return ClipCard(ClipThumbnail(**{**base, **kwargs}))


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
    tarjeta.set_frames([_pixmap() for _ in range(12)])
    assert tarjeta._shown_index == 3   # portada = el 25% (F8)
    tarjeta._show_frame(9)
    assert tarjeta._shown_index == 9


def test_al_salir_vuelve_al_poster(qtbot):
    """La portada se movio del MEDIO al 25% en la F8: en un recorrido el
    frame del medio puede ser cualquier cosa, y el 25% es el mismo punto donde
    arranca el video al abrirlo. Con la tira real de 12 frames, el 3."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    tarjeta = sheet.item_widgets[0]
    tarjeta.set_frames([_pixmap() for _ in range(12)])
    tarjeta._show_frame(9)
    tarjeta.leaveEvent(None)
    assert tarjeta._shown_index == 3


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
    """Canal distinto del estado: posicion, no familia de color.

    La franja se mudo del QSS al overlay en la F2.1 --tiene que ser
    excluyente con el rayado de sin clasificar, y eso solo se garantiza
    pintandolas en el mismo lugar--, pero la regla no cambio: el color del
    cuarto NO puede aparecer en el borde, que es el canal del estado.
    """
    sheet = _sheet(qtbot, [_clip(0, "Cocina")])
    tarjeta = sheet.item_widgets[0]
    assert tarjeta.plan_de_pintado()["franja"] == theme.room_color(0)
    assert theme.room_color(0) not in tarjeta.styleSheet()


# --- lo que la tarjeta dibuja encima de la miniatura (F2.1) -----------------
#
# La F2 dejo la tarjeta con SOLO la miniatura: se perdieron el numero de clip,
# la duracion, el glifo de estado, la barra de rango, el rayado de sin
# clasificar y la palomita. Ver ANALISIS-2026-08-08-post-f2 §2.


def test_la_tarjeta_conoce_su_numero_y_su_duracion(qtbot):
    """Sin numero no se puede hablar de un clip; sin duracion no se sabe
    cual es largo. Los dos estan en el mockup."""
    clip = ClipThumbnail(
        path=Path("/tmp/C0093.MP4"), room_label=SIN_CLASIFICAR, flag="none",
        numero=93, duration_frames=570, fps=30.0,
    )
    sheet = _sheet(qtbot, [clip])
    assert sheet.item_widgets[0].clip.numero == 93
    assert sheet.item_widgets[0].texto_duracion() == "0:19"


def test_la_duracion_no_se_muestra_si_no_se_conoce():
    """Sesion restaurada de disco: no se volvio a correr ffprobe. Mentir con
    0:00 es peor que no decir nada."""
    assert _card().texto_duracion() == ""


def test_la_duracion_pasa_del_minuto():
    assert _card(duration_frames=2400, fps=30.0).texto_duracion() == "1:20"


def test_el_numero_de_clip_va_siempre_y_con_tres_digitos():
    assert _card().plan_de_pintado()["numero"] == "093"


def test_sin_cuarto_lleva_la_franja_rayada_y_no_la_de_color():
    assert _card().plan_de_pintado()["franja"] == "rayada"


def test_con_cuarto_lleva_la_franja_de_color_y_no_la_rayada():
    plan = _card(room_label="Cocina", room_color=theme.room_color(0)).plan_de_pintado()
    assert plan["franja"] == theme.room_color(0)


def test_pick_dibuja_el_glifo_P_en_tinta_oscura():
    assert _card(flag="pick").plan_de_pintado()["glifo"] == (
        "P", theme.PICK_COLOR, theme.PICK_INK,
    )


def test_reject_dibuja_el_glifo_X():
    assert _card(flag="reject").plan_de_pintado()["glifo"][0] == "X"


def test_sin_marca_no_dibuja_glifo():
    """La ausencia de glifo ES la informacion: el mockup no pinta nada."""
    assert _card().plan_de_pintado()["glifo"] is None


def test_la_barra_de_rango_solo_aparece_si_hay_in_o_out():
    """Se perdio en la F2 y la F5 la necesita para el filtro 'sin in/out'."""
    assert _card().plan_de_pintado()["rango"] is None
    plan = _card(in_frame=100, out_frame=400, duration_frames=800).plan_de_pintado()
    assert plan["rango"] == (0.125, 0.5)


def test_un_in_sin_out_marca_hasta_el_final():
    assert _card(in_frame=400, duration_frames=800).plan_de_pintado()["rango"] == (0.5, 1.0)


def test_sin_duracion_conocida_no_hay_barra_de_rango():
    """No se puede ubicar un frame dentro de un clip de largo desconocido."""
    assert _card(in_frame=100, out_frame=400).plan_de_pintado()["rango"] is None


def test_la_palomita_solo_aparece_con_seleccion_multiple(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala")])
    sheet.item_widgets[0].clicked.emit(Qt.KeyboardModifier.NoModifier)
    assert sheet.item_widgets[0].plan_de_pintado()["palomita"] is False
    sheet.item_widgets[1].clicked.emit(Qt.KeyboardModifier.ShiftModifier)
    assert sheet.item_widgets[0].plan_de_pintado()["palomita"] is True


def test_el_overlay_no_se_come_el_scrub_de_la_miniatura(qtbot):
    """Sin WA_TransparentForMouseEvents el overlay se queda con el mouse y el
    scrub al pasar por encima --que ya funcionaba-- deja de andar. Sin
    WA_TranslucentBackground pinta fondo opaco donde no dibuja (hallazgo F0)."""
    tarjeta = _sheet(qtbot, [_clip(0, "Sala")]).item_widgets[0]
    assert tarjeta._overlay.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert tarjeta._overlay.testAttribute(Qt.WA_TranslucentBackground)


def test_el_overlay_pinta_de_verdad_sobre_la_miniatura(qtbot):
    """Candado 3 en chico: el plan de pintado puede estar perfecto y el widget
    no dibujar nada."""
    from PySide6.QtGui import QColor

    sheet = _sheet(qtbot, [_clip(0, "Cocina")])
    sheet.show()
    qtbot.waitExposed(sheet)  # sin show() el layout nunca corre
    tarjeta = sheet.item_widgets[0]
    tarjeta.set_pixmap(_pixmap(Qt.GlobalColor.black))
    imagen = tarjeta.grab().toImage()
    # `grab()` sale a la escala de la pantalla: 1x offscreen, 2x en Retina.
    # Sin normalizar, el test pasa aca y miente en la maquina de Bruno.
    escala = imagen.width() / max(tarjeta.width(), 1)
    assert imagen.pixelColor(round(escala), imagen.height() // 2) == QColor(
        theme.room_color(0)
    )


def test_no_hay_alto_fijo_de_banda(qtbot):
    """El filmstrip viejo tenia setFixedHeight(220) y por eso el video
    perdia 250 px de alto."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    assert sheet.maximumHeight() > 1000


# --- ⌘A selecciona el grupo -------------------------------------------------
#
# La hoja lo ANUNCIA en el encabezado de cada grupo desde la F2.1. Un atajo
# anunciado y ausente es la clase de detalle que hace desconfiar de una
# herramienta (mismo caso que el Ctrl+Z que la F4 va a cerrar).


def test_seleccionar_el_grupo_del_clip_actual(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Cocina"), _clip(2, "Sala")])
    sheet.set_current(0)
    sheet.select_current_group()
    assert sheet.selected_indices() == [0, 2]


def test_seleccionar_el_grupo_de_los_sin_clasificar(qtbot):
    """Es la cola de trabajo: es el grupo donde mas sirve seleccionar todo."""
    sheet = _sheet(qtbot, [_clip(0, None), _clip(1, "Cocina"), _clip(2, None)])
    sheet.set_current(2)
    sheet.select_current_group()
    assert sheet.selected_indices() == [0, 2]


def test_sin_clip_actual_no_selecciona_nada(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.set_current(-1)
    sheet.select_current_group()
    assert sheet.selected_indices() == []


def test_seleccionar_el_grupo_emite_la_seleccion(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala")])
    sheet.set_current(0)
    with qtbot.waitSignal(sheet.selection_changed) as blocker:
        sheet.select_current_group()
    assert blocker.args == [[0, 1]]


# --- F5: filtrar esconde, y NO puede tocar item_widgets ---------------------


def test_filtrar_esconde_pero_NO_reordena_item_widgets(qtbot):
    """Regla 1: las miniaturas se entregan con item_widgets[indice_de_clip] y
    llegan de tres hilos en desorden. Reordenar la lista las haria aterrizar
    en la tarjeta equivocada, de forma intermitente."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None), _clip(2, "Sala")])
    antes = list(sheet.item_widgets)
    sheet.set_visible_indices([1])
    assert sheet.item_widgets == antes
    # `isHidden` y no `isVisible`: el segundo mira toda la cadena de padres y
    # da False con la hoja sin mostrar, que es como corren estos tests
    assert not sheet.item_widgets[1].isHidden()
    assert sheet.item_widgets[0].isHidden()
    assert sheet.item_widgets[2].isHidden()


def test_filtrar_no_borra_las_miniaturas_ya_cargadas(qtbot):
    """Regla 2: esconder no es reconstruir."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None)])
    sheet.item_widgets[0].set_pixmap(_pixmap())
    sheet.set_visible_indices([1])
    sheet.set_visible_indices([0, 1])
    assert sheet.item_widgets[0].has_pixmap()


def test_quitar_el_filtro_vuelve_a_mostrar_todo(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None)])
    sheet.set_visible_indices([1])
    sheet.set_visible_indices(None)
    assert not any(c.isHidden() for c in sheet.item_widgets)


def test_un_grupo_que_queda_vacio_por_el_filtro_se_esconde(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Cocina")])
    sheet.set_visible_indices([1])
    visibles = [b.titulo for b in sheet._ordered_blocks() if not b.isHidden()]
    assert visibles == ["Cocina"]


def test_el_conteo_del_encabezado_cuenta_lo_visible(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala")])
    sheet.set_visible_indices([0])
    bloques = {b.titulo: b for b in sheet._ordered_blocks()}
    assert bloques["Sala"].count_label.text() == "1"


def test_las_tarjetas_visibles_se_recolocan_sin_dejar_huecos(qtbot):
    """Verificado contra Qt: esconder NO alcanza -- el QGridLayout deja el
    hueco donde estaba la tarjeta. Hay que re-colocar salteando las
    escondidas, y por eso set_visible_indices dispara _relayout."""
    sheet = _sheet(qtbot, [_clip(i, "Sala") for i in range(4)])
    sheet.set_visible_indices([1, 3])
    bloque = sheet._ordered_blocks()[0]
    posiciones = [
        bloque.grid.getItemPosition(bloque.grid.indexOf(sheet.item_widgets[i]))[:2]
        for i in (1, 3)
    ]
    assert posiciones == [(0, 0), (0, 1)]
    assert bloque.grid.indexOf(sheet.item_widgets[0]) == -1


def test_cmd_a_selecciona_solo_lo_visible_del_grupo(qtbot):
    """Con un filtro puesto, seleccionar el grupo entero incluiria clips que
    no estas viendo -- y despues les asignarias un cuarto sin querer."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala"), _clip(2, "Sala")])
    sheet.set_visible_indices([0, 2])
    sheet.set_current(0)
    sheet.select_current_group()
    assert sheet.selected_indices() == [0, 2]


# --- F5: la barra de filtros -------------------------------------------------


def test_los_chips_muestran_su_conteo(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None), _clip(2, None)])
    sheet.set_counts({"todos": 3, "sin_clasificar": 2, "clasificados": 1,
                      "solo_picks": 0, "ocultar_rejects": 0, "sin_marcar": 3})
    assert "2" in sheet.chips["sin_clasificar"].text()
    assert "3" in sheet.chips["todos"].text()


def test_ocultar_rejects_muestra_cuantos_esconde_con_signo(qtbot):
    """El mockup dice `−9`: no es cuantos quedan, es cuantos se van."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.set_counts({"todos": 1, "sin_clasificar": 0, "clasificados": 1,
                      "solo_picks": 0, "ocultar_rejects": 9, "sin_marcar": 1})
    assert "−9" in sheet.chips["ocultar_rejects"].text()


def test_prender_un_chip_emite_el_estado_del_filtro(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    with qtbot.waitSignal(sheet.filters_changed) as blocker:
        sheet.chips["sin_clasificar"].click()
    assert blocker.args[0].mostrar == "sin_clasificar"


def test_los_chips_de_un_grupo_son_excluyentes(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.chips["sin_clasificar"].click()
    sheet.chips["clasificados"].click()
    assert sheet.chips["sin_clasificar"].isChecked() is False
    assert sheet.chips["clasificados"].isChecked() is True


def test_para_apagar_un_filtro_se_clickea_Todos(qtbot):
    """Verificado contra Qt: en un QButtonGroup exclusivo, volver a clickear
    el chip activo NO lo apaga. Por eso cada grupo tiene su chip `Todos` --
    el mockup ya lo trae-- y no hay forma de quedarse sin ninguno prendido."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.chips["sin_clasificar"].click()
    sheet.chips["sin_clasificar"].click()
    assert sheet.chips["sin_clasificar"].isChecked() is True
    sheet.chips["todos"].click()
    assert sheet.chips["sin_clasificar"].isChecked() is False


def test_los_dos_grupos_son_independientes(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.chips["sin_clasificar"].click()
    sheet.chips["solo_picks"].click()
    assert sheet.chips["sin_clasificar"].isChecked() is True
    assert sheet.chips["solo_picks"].isChecked() is True


def test_escribir_en_la_busqueda_emite_el_estado(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    with qtbot.waitSignal(sheet.filters_changed) as blocker:
        sheet.search_input.setText("coci")
    assert blocker.args[0].busqueda == "coci"


def test_el_chip_de_cola_solo_se_ve_cuando_hay_filtro(qtbot):
    """Sin filtro, las flechas recorren todo y el chip mentiria."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    assert sheet.queue_chip.isHidden()
    sheet.set_queue_size(12, filtrando=True)
    assert not sheet.queue_chip.isHidden()
    assert "12" in sheet.queue_chip.text()
    sheet.set_queue_size(1, filtrando=False)
    assert sheet.queue_chip.isHidden()


def test_no_se_construyen_los_iconos_de_vista(qtbot):
    """El mockup los dibuja pero no hay ninguna decision detras: no existe
    una vista de lista en DECISIONES.md (ver analisis post-F3 §1.9)."""
    assert not hasattr(_sheet(qtbot, []), "view_toggle")


def test_el_chip_de_destacados_existe_desde_la_F7(qtbot):
    """Hasta la F6 el hueco se dejaba vacio a proposito, para no inventar un
    chip que no filtraria nada. Con el estado construido, el chip entra."""
    # la hoja se guarda en una variable: sin eso Python la libera, Qt destruye
    # a sus hijos y los chips quedan como cascaras muertas
    hoja = _sheet(qtbot, [])
    assert "solo_destacados" in hoja.chips
    assert "★" in hoja.chips["solo_destacados"].text()


def test_el_chip_que_define_la_cola_se_marca_aparte(qtbot):
    """El ambar es el color de la cola en toda la app: verlo en el chip es lo
    que dice «por aqui se mueven las flechas ahora». `Todos` no lo lleva
    porque no filtra nada."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    assert sheet.chips["todos"].property("q") is not True
    sheet.chips["sin_clasificar"].click()
    assert sheet.chips["sin_clasificar"].property("q") is True
    assert sheet.chips["todos"].property("q") is not True
    sheet.chips["todos"].click()
    assert sheet.chips["sin_clasificar"].property("q") is False


def test_recolocar_sin_cambios_no_hace_trabajo(qtbot):
    """Con 128 clips, re-colocar la hoja cuesta ~12 ms. La F5 lo disparaba
    CUATRO veces por cada tecla de cuarto —dos dentro del refresco y dos mas
    por el avance automatico—, y esta app existe para ser rapida.

    Si nada que afecte al acomodo cambio, no hay nada que hacer; si cambia,
    se hace una sola vez.
    """
    sheet = _sheet(qtbot, [_clip(i, "Sala") for i in range(20)])
    sheet.resize(815, 900)
    sheet._relayout()                      # queda al dia

    hechos = []
    original = type(sheet)._acomodar_de_verdad
    type(sheet)._acomodar_de_verdad = lambda s: (hechos.append(1), original(s))[1]
    try:
        sheet._relayout()
        sheet._relayout()
        sheet._relayout()
        assert hechos == [], "recoloco sin que cambiara nada"
        sheet.set_visible_indices([0, 1])   # ahora si cambia
        assert len(hechos) == 1, f"un cambio real recoloco {len(hechos)} veces"
    finally:
        type(sheet)._acomodar_de_verdad = original


def test_un_cambio_de_grupo_si_recoloca(qtbot):
    """El atajo no puede tragarse un cambio real."""
    clips = [_clip(0, "Sala"), _clip(1, "Sala")]
    sheet = _sheet(qtbot, clips)
    sheet.resize(815, 900)
    sheet._relayout()
    clips[0] = _clip(0, "Cocina")
    sheet.update_clips(clips)
    assert set(sheet.group_titles()) == {"Sala", "Cocina"}


def test_esconder_por_filtro_si_recoloca(qtbot):
    sheet = _sheet(qtbot, [_clip(i, "Sala") for i in range(4)])
    sheet.resize(815, 900)
    sheet._relayout()
    sheet.set_visible_indices([0, 1])
    bloque = sheet._ordered_blocks()[0]
    assert bloque.count_label.text() == "2"


def test_cambiar_el_ancho_si_recoloca(qtbot):
    """El area de scroll acomoda su contenido en el ciclo de eventos: sin
    procesarlos, `_content.width()` sigue siendo el de antes y la firma no
    cambiaria."""
    sheet = _sheet(qtbot, [_clip(i, "Sala") for i in range(4)])
    # sin mostrar, el area de scroll nunca acomoda su viewport y
    # `_content.width()` se queda con el valor inicial
    sheet.show()
    qtbot.waitExposed(sheet)
    sheet.resize(815, 900)
    qtbot.wait(10)
    sheet._relayout()
    ancho_antes = sheet.item_widgets[0].width()
    sheet.resize(420, 900)
    qtbot.wait(10)
    sheet._relayout()
    assert sheet.item_widgets[0].width() != ancho_antes


def test_no_se_reestiliza_una_tarjeta_que_no_cambio(qtbot):
    """`setStyleSheet` es carisimo en Qt: vuelve a parsear la hoja y repolish
    el widget. Medido con 128 clips, una sola tecla de cuarto lo llamaba 768
    veces --las 128 tarjetas, seis veces cada una-- y se llevaba el 84% del
    tiempo de la tecla. Es la accion mas frecuente de la app.
    """
    sheet = _sheet(qtbot, [_clip(i, "Sala") for i in range(10)])
    tarjeta = sheet.item_widgets[0]
    llamadas = []
    original = type(tarjeta).setStyleSheet
    type(tarjeta).setStyleSheet = lambda s, hoja: (llamadas.append(hoja), original(s, hoja))[1]
    try:
        tarjeta.set_visual_state(is_current=False, is_selected=False)
        tarjeta.set_visual_state(is_current=False, is_selected=False)
        tarjeta.set_visual_state(is_current=False, is_selected=False)
        assert llamadas == [], "reestilizo sin que cambiara el estado"
        tarjeta.set_visual_state(is_current=True, is_selected=False)
        assert len(llamadas) == 1, "un cambio real tiene que reestilizar una vez"
    finally:
        type(tarjeta).setStyleSheet = original


def test_la_hoja_puede_encogerse_para_dejarle_ancho_al_video(qtbot):
    """El ancho del video sale de lo que la hoja NO necesita. Si el
    encabezado exige 724 px, un clip horizontal se queda sin lugar --y el
    hint, que es decorativo, era el que mas pedia."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.set_queue_size(12, filtrando=True)
    assert sheet.minimumSizeHint().width() <= 520


def test_al_encoger_la_hoja_las_tarjetas_se_reacomodan(qtbot):
    """El widget de contenido NO se encoge solo: su minimo lo fijan las
    propias tarjetas, asi que se queda con el ancho de antes y `_relayout`
    volvia a calcular las mismas columnas. Resultado: con un clip horizontal
    --que angosta la hoja-- la ultima columna quedaba cortada.

    La medida buena es el viewport del area de scroll, que es el espacio que
    de verdad hay.
    """
    sheet = _sheet(qtbot, [_clip(i, "Sala") for i in range(12)])
    sheet.show()
    qtbot.waitExposed(sheet)
    sheet.resize(815, 900)
    qtbot.wait(10)
    sheet._relayout()
    anchas = sheet.item_widgets[0].width()

    sheet.resize(472, 900)
    qtbot.wait(10)
    sheet._relayout()
    bloque = sheet._ordered_blocks()[0]
    columnas = max(
        bloque.grid.getItemPosition(bloque.grid.indexOf(c))[1]
        for c in sheet.item_widgets
    ) + 1
    usado = columnas * sheet.item_widgets[0].width() + (columnas - 1) * GAP
    assert usado <= sheet.width(), (
        f"las tarjetas ocupan {usado} px en una hoja de {sheet.width()}"
    )
    assert sheet.item_widgets[0].width() != anchas or columnas < 5


def test_marcar_OUT_antes_que_IN_dibuja_el_rango_igual(qtbot):
    """Pasa en cuanto marcas `O` y despues `I` mas adelante. La ScrubBar lo
    resuelve con min/max y dibuja el rango bien; la tarjeta calculaba
    (0.5, 0.125) --inicio despues del fin-- y pintaba una astilla de 1 px.
    Dos vistas del mismo dato no pueden decir cosas distintas.
    """
    plan = _card(in_frame=400, out_frame=100, duration_frames=800).plan_de_pintado()
    assert plan["rango"] == (0.125, 0.5)


# --- F8 Task 15: el modo hoja ------------------------------------------------


def _thumb(i: int, cuarto=SIN_CLASIFICAR) -> ClipThumbnail:
    """Un clip de ejemplo para llenar la hoja."""
    return ClipThumbnail(path=Path(f"/tmp/C{i:04d}.MP4"), room_label=cuarto,
                         flag="none", numero=i)


def test_columnas_visibles_cuenta_lo_que_hay_en_la_grilla(qtbot):
    """Existe para poder probar el acomodo sin medir pixeles a mano, que es
    como se colaron los bugs de ancho de la F2."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 21)])
    hoja.resize(815, 900)
    hoja.show()
    qtbot.waitExposed(hoja)
    qtbot.wait(50)
    assert hoja.columnas_visibles() == 5      # la medida de la F2.1


def test_a_pantalla_completa_la_hoja_arma_siete_columnas(qtbot):
    """El numero del mockup. Con menos, las tarjetas quedan enormes y se
    pierde el contexto, que es la razon de este modo."""
    # 1382 px es el ancho REAL de la hoja en modo hoja con la ventana a
    # 1600: el rail de 200 px se queda. Medirlo a 1600 daria otro numero y el
    # test no diria nada del caso que importa.
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 31)])
    hoja.resize(1382, 900)
    hoja.show()
    qtbot.waitExposed(hoja)
    hoja.set_modo_hoja(True)
    qtbot.wait(50)
    assert hoja.columnas_visibles() == 7


def test_cada_modo_recuerda_su_tamano_de_miniatura(qtbot):
    """En la hoja a pantalla completa miras de mas lejos: la densidad util es
    otra, y tener que reajustar en cada cruce seria un peaje."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 13)])
    hoja.show()
    qtbot.waitExposed(hoja)
    en_clip = hoja._paso
    hoja.set_modo_hoja(True)
    assert hoja._paso != en_clip
    hoja.agrandar()
    en_hoja = hoja._paso
    hoja.set_modo_hoja(False)
    assert hoja._paso == en_clip
    hoja.set_modo_hoja(True)
    assert hoja._paso == en_hoja


def test_el_orden_visual_es_el_de_la_grilla(qtbot):
    """Los numeros de clip en el orden en que se ven. Sirve para probar que
    una pincelada no reacomoda la hoja bajo el cursor."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 7)])
    hoja.show()
    qtbot.waitExposed(hoja)
    qtbot.wait(50)
    assert hoja.orden_visual() == [1, 2, 3, 4, 5, 6]


def test_la_hoja_sabe_cual_es_el_clip_actual(qtbot):
    """Un solo estado: la hoja LEE cual es el actual en vez de guardar su
    propia copia. Dos vistas del mismo dato se contradicen solas -- ya paso
    tres veces en este proyecto."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 5)])
    hoja.set_current(2)
    assert hoja.current_index() == 2


def test_doble_click_en_una_tarjeta_avisa_cual_es(qtbot):
    """El gesto de Grid → Loupe. No colisiona con nada: `⏎` sigue siendo la
    paleta."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 5)])
    with qtbot.waitSignal(hoja.clip_activated) as blocker:
        hoja.item_widgets[2].doble_click.emit()
    assert blocker.args == [2]


# --- F8 Task 16: `+` / `−`, tamaño de miniatura ------------------------------


def test_mas_y_menos_cambian_el_tamano_de_las_tarjetas(qtbot):
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 13)])
    hoja.resize(1200, 800)
    hoja.show()
    qtbot.waitExposed(hoja)
    qtbot.wait(50)
    columnas = hoja.columnas_visibles()
    antes = hoja.item_widgets[0].width()

    hoja.agrandar()
    qtbot.wait(50)
    assert hoja.item_widgets[0].width() > antes
    assert hoja.columnas_visibles() < columnas

    hoja.achicar()
    qtbot.wait(50)
    assert hoja.columnas_visibles() == columnas


def test_el_tamano_tiene_tope_por_los_dos_lados(qtbot):
    """Sin topes, `−` repetido deja tarjetas de 3 px y `+` una sola tarjeta
    por pantalla: los dos casos son inservibles."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 13)])
    hoja.resize(1200, 800)
    hoja.show()
    qtbot.waitExposed(hoja)
    qtbot.wait(50)
    for _ in range(20):
        hoja.achicar()
    qtbot.wait(50)
    assert hoja.item_widgets[0].width() >= MIN_TILE_WIDTH
    for _ in range(40):
        hoja.agrandar()
    qtbot.wait(50)
    assert hoja.columnas_visibles() >= 2


def test_el_tamano_sobrevive_a_cargar_otro_shooting(qtbot):
    """Es una preferencia de vista, no un dato del material: si se reiniciara
    con cada `set_clips`, lo ajustarias y se perderia al importar."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 13)])
    hoja.show()
    qtbot.waitExposed(hoja)
    hoja.agrandar()
    hoja.agrandar()
    paso = hoja._paso
    hoja.set_clips([_thumb(i) for i in range(1, 5)])
    assert hoja._paso == paso


# --- F8 Task 17: la barrita de escrubeo sobre la miniatura -------------------


def _card_con_frames(qtbot, cuantos: int = 12) -> ClipCard:
    tarjeta = _card(numero=93, duration_frames=300, fps=30.0)
    qtbot.addWidget(tarjeta)
    tarjeta.resize(180, 320)
    tarjeta.set_frames([_pixmap() for _ in range(cuantos)])
    return tarjeta


def test_la_portada_es_el_frame_del_25_por_ciento(qtbot):
    """En un recorrido el primer frame suele ser una puerta o movimiento
    borroso, y el del medio puede ser cualquier cosa. El 25% es el MISMO punto
    donde arranca el video al abrirlo (F6): la miniatura muestra lo que vas a
    ver, no otra cosa."""
    assert _card_con_frames(qtbot, 12)._poster_index == 3


def test_al_escrubear_aparece_la_barrita_y_el_timecode(qtbot):
    tarjeta = _card_con_frames(qtbot, 12)
    tarjeta.escrubear_a(0.5)
    hover = tarjeta.plan_de_pintado()["hover"]
    assert hover is not None
    assert hover["progreso"] == pytest.approx(0.5, abs=0.1)
    assert hover["timecode"]           # el mockup lo muestra al escrubear


def test_sin_escrubear_no_hay_barrita(qtbot):
    assert _card_con_frames(qtbot, 12).plan_de_pintado()["hover"] is None


def test_al_salir_el_mouse_la_barrita_desaparece(qtbot):
    """Si se quedara, la tarjeta mentiria: dice que estas escrubeando algo que
    ya no estas tocando."""
    tarjeta = _card_con_frames(qtbot, 12)
    tarjeta.escrubear_a(0.5)
    tarjeta.leaveEvent(None)
    assert tarjeta.plan_de_pintado()["hover"] is None


def test_al_salir_el_mouse_vuelve_la_portada(qtbot):
    """La tarjeta tiene que quedar como estaba, o la hoja termina siendo un
    mosaico de frames al azar segun por donde pasaste el mouse."""
    tarjeta = _card_con_frames(qtbot, 12)
    tarjeta.escrubear_a(0.9)
    tarjeta.leaveEvent(None)
    assert tarjeta._shown_index == tarjeta._poster_index


def test_escrubear_una_tarjeta_sin_frames_no_revienta(qtbot):
    """Las miniaturas se extraen en segundo plano: al abrir un shooting las
    tarjetas existen antes que sus frames."""
    tarjeta = _card(numero=1)
    qtbot.addWidget(tarjeta)
    tarjeta.escrubear_a(0.5)
    assert tarjeta.plan_de_pintado()["hover"] is None


def test_al_escrubear_el_timecode_reemplaza_a_la_duracion(qtbot):
    """Van en la misma esquina --la del mockup-- y dos pastillas encimadas no
    se leen. Mientras escrubeas importa donde estas, no cuanto dura."""
    tarjeta = _card_con_frames(qtbot, 12)
    imagen_quieta = tarjeta.grab().toImage()
    tarjeta.escrubear_a(0.5)
    imagen_escrubeando = tarjeta.grab().toImage()
    assert imagen_quieta != imagen_escrubeando


def test_la_barrita_de_escrubeo_no_tapa_la_de_rango(qtbot):
    """Son dos datos distintos --donde miras ahora contra que tramo marcaste--
    y encimarlos haria que uno tape al otro justo cuando los dos importan."""
    tarjeta = _card(numero=93, duration_frames=300, fps=30.0,
                    in_frame=30, out_frame=200)
    qtbot.addWidget(tarjeta)
    tarjeta.resize(180, 320)
    tarjeta.set_frames([_pixmap() for _ in range(12)])
    tarjeta.escrubear_a(0.5)
    imagen = tarjeta.grab().toImage()
    escala = imagen.width() / max(tarjeta.width(), 1)
    # la ultima fila es de la barra de rango: tiene que seguir siendo del
    # color del rango, no del blanco de la barrita de escrubeo
    y = round((tarjeta.height() - 1) * escala)
    assert imagen.pixelColor(round(90 * escala), y).name() == theme.TRIM_COLOR


def test_la_barrita_de_escrubeo_no_pasa_por_detras_de_la_pastilla(qtbot):
    """Si corriera por atras, la pastilla del timecode le tapa el tramo final
    --justo donde estas cuando escrubeas hasta el final-- y la barra deja de
    decir nada."""
    tarjeta = _card_con_frames(qtbot, 12)
    tarjeta.escrubear_a(0.95)
    imagen = tarjeta.grab().toImage()
    escala = imagen.width() / max(tarjeta.width(), 1)
    # la cabeza ambar al 95% tiene que verse: si la pastilla la tapara, ahi
    # habria fondo de pastilla
    x = round(tarjeta.width() * 0.93 * escala)
    columna = [imagen.pixelColor(x, y).name()
               for y in range(imagen.height() // 2, imagen.height())]
    assert theme.CURRENT_COLOR in columna, "la cabeza del escrubeo no se ve"


# --- F8 Task 18: el gesto del pincel -----------------------------------------


def test_la_hoja_avisa_por_que_tarjeta_pasa_el_arrastre(qtbot):
    """La hoja no sabe de cuartos ni de historial: solo dice por donde paso el
    cursor con el boton apretado. Quien pinta es la ventana."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 7)])
    hoja.resize(815, 600)
    hoja.show()
    qtbot.waitExposed(hoja)
    qtbot.wait(50)
    tocadas = []
    hoja.brocha_paso_por.connect(tocadas.append)
    tarjeta = hoja.item_widgets[2]
    centro = tarjeta.mapTo(hoja._scroll.viewport(), tarjeta.rect().center())
    hoja.notificar_arrastre(centro)
    assert tocadas == [2]


def test_el_arrastre_encuentra_la_tarjeta_con_el_scroll_movido(qtbot):
    """Lo que midio el spike: `childAt` va sobre el CONTENIDO --que es lo que
    se desplaza-- sumandole el scroll. Sobre el viewport, con la hoja
    desplazada, devuelve la tarjeta equivocada."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 41)])
    hoja.resize(815, 400)
    hoja.show()
    qtbot.waitExposed(hoja)
    qtbot.wait(50)
    hoja._scroll.verticalScrollBar().setValue(200)
    qtbot.wait(20)
    tocadas = []
    hoja.brocha_paso_por.connect(tocadas.append)
    visibles = [(i, c) for i, c in enumerate(hoja.item_widgets)
                if hoja._scroll.viewport().rect().contains(
                    c.mapTo(hoja._scroll.viewport(), c.rect().center()))]
    assert visibles, "ninguna tarjeta visible tras desplazar"
    indice, tarjeta = visibles[len(visibles) // 2]
    hoja.notificar_arrastre(
        tarjeta.mapTo(hoja._scroll.viewport(), tarjeta.rect().center())
    )
    assert tocadas == [indice]


def test_una_tarjeta_recien_pintada_queda_teñida(qtbot):
    """El detalle 3 del pincel: el rastro de la pincelada se VE. Sin el tinte,
    la unica señal es la franja de 3 px del borde y no se distingue lo que
    acabas de pintar de lo que ya estaba."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 4)])
    tarjeta = hoja.item_widgets[0]
    tarjeta.resize(140, 250)
    sin_pintar = tarjeta.grab().toImage()
    hoja.repintar_uno(0, "Cocina", ["Cocina"])
    pintada = tarjeta.grab().toImage()
    assert sin_pintar != pintada
    assert tarjeta.plan_de_pintado()["tinte"] is not None


def test_el_tinte_se_va_al_terminar_la_pincelada(qtbot):
    """Es el rastro del gesto, no un estado del clip: al soltar, la tarjeta
    queda como cualquier otra de su cuarto."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 4)])
    hoja.repintar_uno(0, "Cocina", ["Cocina"])
    assert hoja.item_widgets[0].plan_de_pintado()["tinte"] is not None
    hoja.congelar_acomodo(False)
    hoja.limpiar_tinte()
    assert hoja.item_widgets[0].plan_de_pintado()["tinte"] is None


# --- F8 Task 19: la barra de seleccion multiple ------------------------------


def test_la_barra_de_seleccion_aparece_con_mas_de_un_clip(qtbot):
    """Con uno solo no hay nada que decir: es el flujo normal."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 8)])
    assert hoja.batch_bar.isHidden()
    hoja.set_selected({1, 2, 3})
    assert not hoja.batch_bar.isHidden()
    assert "3 clips" in hoja.batch_bar.label.text()


def test_con_un_solo_clip_seleccionado_la_barra_no_se_ve(qtbot):
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 5)])
    hoja.set_selected({2})
    assert hoja.batch_bar.isHidden()


def test_al_vaciar_la_seleccion_la_barra_se_va(qtbot):
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 5)])
    hoja.set_selected({1, 2})
    hoja.set_selected(set())
    assert hoja.batch_bar.isHidden()


def test_la_barra_solo_anuncia_teclas_que_existen(qtbot):
    """El detector que ya encontro cuatro atajos fantasma. Aqui se comprueba
    contra la lista de la propia barra; que existan de verdad lo verifica el
    test de la ventana."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, 5)])
    hoja.set_selected({1, 2})
    texto = hoja.batch_bar.hints_text()
    for tecla in ("1", "9", "⏎", "P", "X", "⇧P", "⌘Z", "esc"):
        assert tecla in texto


def test_re_aplicar_el_mismo_ancho_no_reescala_la_miniatura(qtbot):
    """Re-colocar la grilla llama a `apply_width` en las 128 tarjetas. Sin
    esta guarda cada una tiraba su cache y volvia a escalar su miniatura:
    medido con cProfile, el 40% del costo de una tecla de cuarto."""
    tarjeta = _card_con_frames(qtbot, 12)
    tarjeta.apply_width(150)
    cache = tarjeta._scaled_cache
    escalados = dict(cache)
    tarjeta.apply_width(150)
    assert tarjeta._scaled_cache is cache        # ni siquiera se recreo
    assert tarjeta._scaled_cache == escalados
    tarjeta.apply_width(190)                     # otro ancho SI reescala
    assert tarjeta._scaled_cache != escalados


# --- la marquesina de seleccion ----------------------------------------------


def _hoja_visible(qtbot, cuantos=12):
    hoja = _sheet(qtbot, [_thumb(i) for i in range(1, cuantos + 1)])
    hoja.resize(815, 700)
    hoja.show()
    qtbot.waitExposed(hoja)
    qtbot.wait(50)
    return hoja


def _centro(hoja, indice):
    card = hoja.item_widgets[indice]
    return card.mapTo(hoja._scroll.viewport(), card.rect().center())


def test_arrastrar_sobre_varias_tarjetas_las_selecciona(qtbot):
    """El gesto que `DECISIONES.md` nombra primero para seleccion multiple."""
    hoja = _hoja_visible(qtbot)
    hoja.empezar_marquesina(_centro(hoja, 0))
    hoja.mover_marquesina(_centro(hoja, 2))
    hoja.terminar_marquesina()
    assert hoja.selected_indices() == [0, 1, 2]


def test_la_marquesina_se_ve_mientras_arrastras(qtbot):
    """Un rectangulo invisible no dice que estas seleccionando."""
    hoja = _hoja_visible(qtbot)
    assert hoja.marquesina.isHidden()
    hoja.empezar_marquesina(_centro(hoja, 0))
    hoja.mover_marquesina(_centro(hoja, 2))
    assert not hoja.marquesina.isHidden()
    hoja.terminar_marquesina()
    assert hoja.marquesina.isHidden()


def test_la_seleccion_se_ve_mientras_arrastras_no_al_soltar(qtbot):
    """Si solo apareciera al soltar, estarias arrastrando a ciegas."""
    hoja = _hoja_visible(qtbot)
    hoja.empezar_marquesina(_centro(hoja, 0))
    hoja.mover_marquesina(_centro(hoja, 1))
    assert hoja.selected_indices() == [0, 1]
    hoja.terminar_marquesina()


def test_un_click_sin_arrastrar_no_selecciona_todo(qtbot):
    """Presionar y soltar en el mismo punto es un click, no una marquesina:
    si cada click seleccionara, no habria forma de elegir un solo clip."""
    hoja = _hoja_visible(qtbot)
    punto = _centro(hoja, 3)
    hoja.empezar_marquesina(punto)
    hoja.mover_marquesina(punto)
    hoja.terminar_marquesina()
    assert hoja.selected_indices() == []


def test_arrastrar_hacia_atras_tambien_selecciona(qtbot):
    """De abajo-derecha hacia arriba-izquierda: un rectangulo de ancho
    negativo no selecciona nada. Es el mismo bug del rango invertido de la
    tarjeta y de la barra."""
    hoja = _hoja_visible(qtbot)
    hoja.empezar_marquesina(_centro(hoja, 2))
    hoja.mover_marquesina(_centro(hoja, 0))
    hoja.terminar_marquesina()
    assert hoja.selected_indices() == [0, 1, 2]


def test_la_marquesina_no_toca_las_escondidas_por_el_filtro(qtbot):
    """Seleccionar algo que no ves y despues asignarle un cuarto en lote es
    el error mas caro de la app."""
    hoja = _hoja_visible(qtbot)
    hoja.set_visible_indices([0, 1, 2])
    qtbot.wait(30)
    hoja.empezar_marquesina(_centro(hoja, 0))
    hoja.mover_marquesina(_centro(hoja, 2))
    hoja.terminar_marquesina()
    assert all(i in (0, 1, 2) for i in hoja.selected_indices())


def test_con_el_pincel_cargado_no_hay_marquesina(qtbot):
    """Los dos gestos son el mismo arrastre: con la tecla abajo pinta, sin
    ella selecciona. Que corran juntos seria pintar y seleccionar a la vez."""
    hoja = _hoja_visible(qtbot)
    hoja.set_pincel_activo(True)
    hoja.empezar_marquesina(_centro(hoja, 0))
    hoja.mover_marquesina(_centro(hoja, 2))
    assert hoja.marquesina.isHidden()
    assert hoja.selected_indices() == []
