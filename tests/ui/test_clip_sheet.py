from pathlib import Path

import pytest

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPixmap

from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import (
    MIN_TILE_WIDTH,
    GAP,
    SIN_BIN,
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
    assert set(sheet.group_titles()) == {(SIN_BIN, "Sala"), (SIN_BIN, "Cocina")}


def test_los_sin_clasificar_van_primero(qtbot):
    """Es la cola de trabajo: lo que falta va arriba."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None)])
    assert sheet.group_titles()[0] == (SIN_BIN, SIN_CLASIFICAR)


def test_un_grupo_que_se_vacia_desaparece(qtbot):
    clips = [_clip(0, "Sala"), _clip(1, "Cocina")]
    sheet = _sheet(qtbot, clips)
    assert len(sheet.group_titles()) == 2
    clips[0] = _clip(0, "Cocina")
    sheet.update_clips(clips)
    assert sheet.group_titles() == [(SIN_BIN, "Cocina")]


def test_el_encabezado_de_grupo_lleva_su_conteo(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala"), _clip(2, "Cocina")])
    bloques = {b.cuarto: b for b in sheet._ordered_blocks()}
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
    visibles = [b.cuarto for b in sheet._ordered_blocks() if not b.isHidden()]
    assert visibles == ["Cocina"]


def test_el_conteo_del_encabezado_cuenta_lo_visible(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala")])
    sheet.set_visible_indices([0])
    bloques = {b.cuarto: b for b in sheet._ordered_blocks()}
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
    assert set(sheet.group_titles()) == {(SIN_BIN, "Sala"), (SIN_BIN, "Cocina")}


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


def _thumb(i: int, cuarto=SIN_CLASIFICAR, **extra) -> ClipThumbnail:
    """Un clip de ejemplo para llenar la hoja.

    `extra` deja pasar cualquier campo del `ClipThumbnail` --`bin_nombre`,
    `room_label`, `flag`-- sin tener que agregar un parametro por cada uno
    que nazca.
    """
    campos = dict(path=Path(f"/tmp/C{i:04d}.MP4"), room_label=cuarto,
                  flag="none", numero=i)
    campos.update(extra)
    return ClipThumbnail(**campos)


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


# --- la hoja lleva al clip actual (F10) --------------------------------


def test_centrar_en_deja_la_tarjeta_a_la_vista(qtbot):
    """`DECISIONES.md`: «⇥ alterna llevando siempre al clip actual, en los
    dos sentidos. Al volver a la hoja, esa tarjeta queda centrada».

    Sin esto la hoja se quedaba donde estuviera el scroll: con 128 clips y
    el actual en el 87, entrabas a la hoja mirando el 117.
    """
    sheet = _sheet(qtbot, [_clip(i) for i in range(128)])
    sheet.resize(800, 600)
    sheet.show()
    qtbot.wait(10)

    sheet.centrar_en(86)
    qtbot.wait(10)

    tarjeta = sheet.item_widgets[86]
    viewport = sheet._scroll.viewport()
    arriba = tarjeta.mapTo(viewport, tarjeta.rect().topLeft())
    assert viewport.rect().intersects(QRect(arriba, tarjeta.size()))


def test_centrar_en_un_indice_que_no_existe_no_truena(qtbot):
    sheet = _sheet(qtbot, [_clip(0)])
    sheet.show()
    sheet.centrar_en(50)
    sheet.centrar_en(-1)


# --- el borde de estado se PINTA (reporte de Bruno) --------------------


def _color_del_borde_arriba(card):
    img = card.grab().toImage()
    return img.pixelColor(img.width() // 2, 0).name()


def test_la_tarjeta_actual_se_marca_con_pixeles_de_verdad(qtbot):
    """«En el modo clip no se marca en cual clip estoy»: la hoja de
    estilos decia `border: 2px solid ambar`, pero la miniatura tapa el
    borde y el QSS nunca llegaba al pixel. El estado se pinta ahora en el
    mismo `paintEvent` que el resto de lo que va encima.

    Este test mira el PIXEL a proposito: el plan de pintado y un widget
    que no dibuja nada se ven igual desde el otro lado.
    """
    card = _card()
    qtbot.addWidget(card)
    card.resize(150, 267)
    card.set_pixmap(_pixmap())
    card.show()
    qtbot.wait(10)

    normal = _color_del_borde_arriba(card)
    card.set_visual_state(is_current=True)
    qtbot.wait(10)

    assert _color_del_borde_arriba(card) == theme.CURRENT_COLOR
    assert normal != theme.CURRENT_COLOR


def test_el_pick_y_el_reject_tambien_se_ven_en_el_borde(qtbot):
    for flag, color in (("pick", theme.PICK_COLOR), ("reject", theme.REJECT_COLOR)):
        card = _card(flag=flag)
        qtbot.addWidget(card)
        card.resize(150, 267)
        card.set_pixmap(_pixmap())
        card.show()
        qtbot.wait(10)
        assert _color_del_borde_arriba(card) == color, flag


def test_la_seleccion_gana_al_estado_pero_no_al_actual(qtbot):
    card = _card(flag="pick")
    qtbot.addWidget(card)
    card.resize(150, 267)
    card.set_pixmap(_pixmap())
    card.show()
    card.set_visual_state(is_current=False, is_selected=True)
    qtbot.wait(10)
    assert _color_del_borde_arriba(card) == theme.SELECTION_BORDER

    card.set_visual_state(is_current=True, is_selected=True)
    qtbot.wait(10)
    assert _color_del_borde_arriba(card) == theme.CURRENT_COLOR


def test_agregar_clips_no_recrea_las_tarjetas_de_antes(qtbot):
    """La miniatura ya cargada vive en el widget. Si la tarjeta se recrea,
    la portada se pierde -- que es exactamente lo que Bruno vio al importar
    una segunda carpeta.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0), _thumb(1)])
    antes = list(hoja.item_widgets)

    hoja.append_clips([_thumb(0), _thumb(1), _thumb(2)])

    assert hoja.item_widgets[0] is antes[0]
    assert hoja.item_widgets[1] is antes[1]
    assert hoja.count() == 3


def test_agregar_clips_conecta_cada_tarjeta_nueva_a_SU_indice(qtbot):
    """El `lambda i=index` de `set_clips` existe por esto: sin capturar el
    indice por valor, todas las tarjetas nuevas terminan avisando del
    ultimo clip."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    hoja.append_clips([_thumb(0), _thumb(1), _thumb(2)])
    avisados = []
    hoja.clip_clicked.connect(avisados.append)

    hoja.item_widgets[1].clicked.emit(Qt.KeyboardModifier.NoModifier)
    hoja.item_widgets[2].clicked.emit(Qt.KeyboardModifier.NoModifier)

    assert avisados == [1, 2]


# --- F4 Task 8: la hoja agrupa por (bin, cuarto) ------------------------------


def test_los_bins_van_en_orden_de_importacion_y_los_cuartos_adentro(qtbot):
    """Propuesta A del mockup: el bin manda arriba, el cuarto baja a
    subgrupo. El orden de los bins es el de importacion, no el alfabetico."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Dron", room_label="Exteriores"),
        _thumb(1, bin_nombre="Sony", room_label="Cocina"),
        _thumb(2, bin_nombre="Sony", room_label=SIN_CLASIFICAR),
    ])

    assert hoja.group_titles() == [
        ("Sony", SIN_CLASIFICAR), ("Sony", "Cocina"), ("Dron", "Exteriores"),
    ]


def test_un_clip_sin_bin_cae_en_uno_solo_y_no_revienta(qtbot):
    """Desde la F8 el clip suelto cae en la seccion «Sin bin». El DATO sigue
    siendo el mismo --`bin_nombre` vacio, o sea sin bin--: «Sin bin» es el
    nombre de la seccion que lo muestra, no un bin al que pertenezca."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0, room_label="Cocina")])

    assert hoja.group_titles() == [(SIN_BIN, "Cocina")]


def test_un_bin_que_no_esta_en_el_orden_va_al_final(qtbot):
    """Puede pasar entre que se agrega material y se refresca el orden: no
    puede reventar ni colarse arriba de los que si estan ordenados.

    Y desde la F8 tambien tiene que llevar encabezado: los bins los declara
    quien llama, y sin este caso las tarjetas de un bin todavia no declarado
    se quedaban sin encabezado Y sin bloque, o sea invisibles.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Recien llegado", room_label="Cocina"),
        _thumb(1, bin_nombre="Sony", room_label="Cocina"),
    ])

    assert hoja.group_titles() == [("Sony", "Cocina"), ("Recien llegado", "Cocina")]
    assert hoja.bin_headers() == ["Sony", "Recien llegado"]


def test_el_mismo_cuarto_en_dos_bins_son_dos_bloques(qtbot):
    """El costo aceptado de la propuesta A: grabaste la cocina con las dos
    camaras, y aparece una vez dentro de cada bin."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Sony", room_label="Cocina"),
        _thumb(1, bin_nombre="Dron", room_label="Cocina"),
    ])

    assert hoja.group_titles() == [("Sony", "Cocina"), ("Dron", "Cocina")]


def test_el_bloque_de_cuarto_solo_muestra_el_cuarto(qtbot):
    """El nombre del bin ya lo dice su encabezado: repetirlo en cada
    subgrupo seria ruido."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony", room_label="Cocina")])

    assert hoja._ordered_blocks()[0].title_label.text() == "COCINA"


# --- F4 Task 9: el encabezado del bin -----------------------------------------


def test_hay_un_encabezado_por_bin_arriba_de_su_primer_grupo(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Sony", room_label="Cocina"),
        _thumb(1, bin_nombre="Sony", room_label="Baño"),
        _thumb(2, bin_nombre="Dron", room_label="Exteriores"),
    ])

    assert hoja.bin_headers() == ["Sony", "Dron"]


def test_el_encabezado_va_antes_que_los_bloques_de_su_bin(qtbot):
    """No alcanza con que exista: si quedara debajo de sus grupos diria que
    la Sony es del dron."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Sony", room_label="Cocina"),
        _thumb(1, bin_nombre="Dron", room_label="Exteriores"),
    ])

    # la zona de «bin nuevo» del arrastre (F5) tambien vive en la columna,
    # al final y escondida: aqui se habla del orden de bins y grupos.
    orden = [
        getattr(w, "nombre", None) or getattr(w, "titulo", None)
        for w in hoja._widgets_del_contenido()
        if hasattr(w, "nombre") or hasattr(w, "titulo")
    ]
    assert orden == ["Sony", ("Sony", "Cocina"), "Dron", ("Dron", "Exteriores")]


def test_el_encabezado_dice_cuantos_clips_tiene_su_bin(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Sony")])

    assert "2" in hoja.bin_header_widget("Sony").count_label.text()


def test_el_encabezado_cuenta_picks_destacados_y_rejects(qtbot):
    """Los puntos de color del mockup. Salen de las tarjetas, no de un dato
    aparte: dos vistas del mismo numero se contradicen solas."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Sony", flag="pick"),
        _thumb(1, bin_nombre="Sony", flag="pick"),
        _thumb(2, bin_nombre="Sony", flag="destacado"),
        _thumb(3, bin_nombre="Sony", flag="reject"),
    ])

    cabecera = hoja.bin_header_widget("Sony")
    assert cabecera.marcas_texto() == ["2", "1", "1"]


def test_un_bin_que_SE_VA_DEL_ORDEN_pierde_su_encabezado(qtbot):
    """Lo que tira el encabezado es dejar de estar declarado, no quedarse sin
    clips.

    Hasta la F8 era al reves --los bins se deducian de las tarjetas-- y por
    eso un bin vacio no existia para la hoja. Ahora el bin desaparece cuando
    de verdad lo quitaste del proyecto, que es cuando sale de `set_bin_order`.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron"),
    ])
    assert hoja.bin_headers() == ["Sony", "Dron"]

    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert hoja.bin_headers() == ["Sony"]
    assert hoja.bin_header_widget("Dron") is None


def test_colapsar_esconde_las_tarjetas_pero_no_las_saca_de_la_cola(qtbot):
    """Colapsar es visual. Si sacara los clips de la cola seria un filtro
    escondido, y la flecha se saltaria clips sin decir por que."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    hoja.set_bin_collapsed("Sony", True)

    assert hoja.item_widgets[0].isHidden()
    assert hoja.count() == 1


def test_colapsar_no_esconde_las_tarjetas_del_otro_bin(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])

    hoja.set_bin_collapsed("Sony", True)

    assert hoja.item_widgets[0].isHidden()
    assert not hoja.item_widgets[1].isHidden()


def test_expandir_devuelve_las_tarjetas(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])
    hoja.set_bin_collapsed("Sony", True)

    hoja.set_bin_collapsed("Sony", False)

    assert not hoja.item_widgets[0].isHidden()
    assert hoja.bin_header_widget("Sony").chevron.text() == "▾"


def test_un_bin_colapsado_no_deja_sus_bloques_ocupando_lugar(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony", room_label="Cocina")])

    hoja.set_bin_collapsed("Sony", True)

    assert hoja._ordered_blocks()[0].isHidden()
    assert hoja.bin_header_widget("Sony").chevron.text() == "▸"


def test_el_filtro_no_resucita_las_tarjetas_de_un_bin_colapsado(qtbot):
    """Colapsar y filtrar son dos cosas distintas sobre la misma tarjeta:
    la que las dos esconden tiene que quedarse escondida."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Sony")])
    hoja.set_bin_collapsed("Sony", True)

    hoja.set_visible_indices([0, 1])

    assert hoja.item_widgets[0].isHidden()


def test_click_en_el_encabezado_pide_colapsar(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])
    cabecera = hoja.bin_header_widget("Sony")

    with qtbot.waitSignal(cabecera.collapse_toggled) as blocker:
        cabecera.alternar_colapso()

    assert blocker.args == ["Sony"]
    assert hoja.item_widgets[0].isHidden()


def test_renombrar_en_el_lugar_con_un_campo_de_texto_no_un_dialogo(qtbot):
    """Nada de `QInputDialog`: es modal y cuelga la suite bajo offscreen."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])
    cabecera = hoja.bin_header_widget("Sony")

    cabecera.empezar_a_renombrar()
    assert not cabecera.name_edit.isHidden() and cabecera.name_label.isHidden()
    cabecera.name_edit.setText("Sony FX30")

    with qtbot.waitSignal(cabecera.rename_requested) as blocker:
        cabecera.name_edit.returnPressed.emit()

    assert blocker.args == ["Sony", "Sony FX30"]


def test_renombrar_con_el_mismo_nombre_no_avisa_a_nadie(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])
    cabecera = hoja.bin_header_widget("Sony")
    avisos = []
    cabecera.rename_requested.connect(lambda *a: avisos.append(a))

    cabecera.empezar_a_renombrar()
    cabecera.name_edit.returnPressed.emit()

    assert avisos == []


def test_el_menu_del_bin_trae_lo_que_dibujo_el_mockup(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(i, bin_nombre="Dron") for i in range(3)])
    menu = hoja.bin_header_widget("Dron").construir_menu()

    textos = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert textos == [
        "Renombrar bin…",
        "Enlazar proxies…",
        "Quitar proxies de este bin",
        "Seleccionar los 3 clips",
        "Colapsar",
        "Quitar del proyecto",
    ]


@pytest.mark.parametrize("titulo, senal", [
    ("Enlazar proxies…", "proxies_requested"),
    ("Quitar proxies de este bin", "proxies_cleared"),
    ("Seleccionar los 1 clips", "select_all_requested"),
    ("Quitar del proyecto", "remove_requested"),
])
def test_cada_renglon_del_menu_avisa_con_el_nombre_del_bin(qtbot, titulo, senal):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])
    cabecera = hoja.bin_header_widget("Dron")
    menu = cabecera.construir_menu()
    accion = next(a for a in menu.actions() if a.text() == titulo)

    with qtbot.waitSignal(getattr(cabecera, senal)) as blocker:
        accion.trigger()

    assert blocker.args == ["Dron"]


def test_el_menu_dice_expandir_cuando_el_bin_esta_colapsado(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])
    hoja.set_bin_collapsed("Dron", True)

    menu = hoja.bin_header_widget("Dron").construir_menu()

    assert "Expandir" in [a.text() for a in menu.actions()]


def test_la_insignia_de_proxies_dice_cuantos_calzaron(qtbot):
    """«21/23» es a proposito visible: dos no calzaron cuadro a cuadro y no
    se engancharon, que es mejor que enganchar un proxy corrido."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(i, bin_nombre="Dron") for i in range(3)])

    hoja.set_bin_meta("Dron", origen="02. VIDEO DRONE", proxies=(2, 3))

    cabecera = hoja.bin_header_widget("Dron")
    assert cabecera.source_label.text() == "02. VIDEO DRONE"
    assert cabecera.proxy_badge.text() == "proxy · 2/3"


def test_sin_proxies_lo_dice_con_todas_las_letras(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])

    hoja.set_bin_meta("Dron", origen="/dron", proxies=(0, 1))

    assert hoja.bin_header_widget("Dron").proxy_badge.text() == "sin proxies"


def test_con_todos_los_proxies_no_muestra_la_fraccion(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])

    hoja.set_bin_meta("Dron", origen="/dron", proxies=(1, 1))

    assert hoja.bin_header_widget("Dron").proxy_badge.text() == "proxy · 1/1"


def test_la_meta_del_bin_sobrevive_a_que_se_rehaga_el_encabezado(qtbot):
    """Los encabezados nacen y mueren con cada reagrupada; la carpeta de
    origen no."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])
    hoja.set_bin_meta("Dron", origen="02. VIDEO DRONE", proxies=(0, 1))

    hoja.set_clips([_thumb(0, bin_nombre="Dron"), _thumb(1, bin_nombre="Dron")])

    assert hoja.bin_header_widget("Dron").source_label.text() == "02. VIDEO DRONE"


def test_la_hoja_avisa_de_cada_encabezado_nuevo(qtbot):
    """Es como la ventana le enchufa sus señales: los bins aparecen y
    desaparecen con las importaciones, no una sola vez al arrancar."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    nacidos = []
    hoja.bin_header_created.connect(lambda c: nacidos.append(c.nombre))

    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])

    assert nacidos == ["Sony", "Dron"]


# --- F4 Task 9 paso 5: el encabezado pegado arriba ----------------------------


def test_el_encabezado_pegado_sigue_al_bin_en_el_que_estas(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(815, 300)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips(
        [_thumb(i, bin_nombre="Sony") for i in range(12)]
        + [_thumb(i, bin_nombre="Dron") for i in range(12, 24)]
    )
    hoja.show()
    # el area de scroll acomoda su contenido en el ciclo de eventos: hasta
    # que no corre, la barra no tiene recorrido y `setValue` se recorta a 0.
    barra = hoja._scroll.verticalScrollBar()
    qtbot.waitUntil(lambda: barra.maximum() > 0, timeout=2000)

    barra.setValue(hoja.bin_header_widget("Sony").y() + 1)
    assert hoja._pegado.nombre == "Sony"

    barra.setValue(hoja.bin_header_widget("Dron").y() + 1)
    assert hoja._pegado.nombre == "Dron"


def test_en_el_tope_no_hay_encabezado_pegado(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(815, 300)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(i, bin_nombre="Sony") for i in range(12)])
    hoja.show()

    hoja._scroll.verticalScrollBar().setValue(0)

    assert hoja._pegado.isHidden()


def test_la_insignia_dice_la_resolucion_del_proxy(qtbot):
    """`proxy 1080p · 23/23`, como el mockup. La resolucion es el dato que
    dice si el proxy sirve para trabajar o es una estampilla."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(i, bin_nombre="Dron") for i in range(3)])

    hoja.set_bin_meta("Dron", origen="/dron", proxies=(3, 3), resolucion="1080p")

    assert hoja.bin_header_widget("Dron").proxy_badge.text() == "proxy 1080p · 3/3"


def test_sin_resolucion_conocida_la_insignia_no_la_inventa(qtbot):
    """Con dos resoluciones mezcladas en el mismo bin se colapsa a vacio,
    igual que hace `_resumen_de_proxies`: decir una de las dos seria
    mentir sobre la otra mitad."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(i, bin_nombre="Dron") for i in range(3)])

    hoja.set_bin_meta("Dron", origen="/dron", proxies=(2, 3), resolucion="")

    assert hoja.bin_header_widget("Dron").proxy_badge.text() == "proxy · 2/3"


# --- la marca de camara del encabezado (`.bin .cam` del mockup) ---------------


def test_el_encabezado_lleva_la_marca_de_camara(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])

    assert hoja.bin_header_widget("Sony").cam_mark.text()


def test_la_marca_es_EL_MISMO_glifo_en_todos_los_bins(qtbot):
    """El mockup ponia `▲` al dron y `■` a la Sony porque sabia que era
    cada uno. La app no lo sabe, y adivinarlo seria peor que no decirlo."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])

    assert (hoja.bin_header_widget("Sony").cam_mark.text()
            == hoja.bin_header_widget("Dron").cam_mark.text())


def test_la_marca_se_tiñe_segun_la_posicion_del_bin(qtbot):
    """Lo que distingue un bin de otro es el COLOR, no el glifo -- y va por
    posicion, como los cuartos: mismo lugar, mismo color toda la sesion."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])

    primera = hoja.bin_header_widget("Sony").cam_mark.styleSheet()
    segunda = hoja.bin_header_widget("Dron").cam_mark.styleSheet()
    assert primera != segunda
    assert theme.bin_color(0) != theme.bin_color(1)


def test_la_marca_va_teñida_y_no_a_plena_tinta(qtbot):
    """La marca comparte tinta con la paleta de cuartos --el mockup uso
    esos mismos colores-- y lo que la distingue es el TRATAMIENTO: el
    cuarto va a plena saturacion en la franja de la miniatura, el bin va
    al 18% detras de un glifo aclarado. Si el bin fuera solido, la hoja
    tendria dos azules distintos diciendo cosas distintas."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    hoja_de_estilo = hoja.bin_header_widget("Sony").cam_mark.styleSheet()
    assert f"rgba(" in hoja_de_estilo
    assert theme.bin_color(0) not in hoja_de_estilo


def test_renombrar_el_bin_no_le_cambia_el_color(qtbot):
    """El color va por posicion, y renombrar no mueve al bin de lugar."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])
    antes = hoja.bin_header_widget("Dron").cam_mark.styleSheet()

    hoja.set_bin_order(["Sony", "Dron DJI"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron DJI")])

    assert hoja.bin_header_widget("Dron DJI").cam_mark.styleSheet() == antes


# --- los cuatro cabos sueltos del encabezado ---------------------------------


def test_el_encabezado_pegado_se_reajusta_al_cambiar_el_ancho(qtbot):
    """Se re-geometriza al hacer scroll, y si eso fuera todo, cambiar el
    ancho de la ventana lo dejaba con el ancho viejo hasta el proximo
    scroll -- o sea colgando fuera de la hoja."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(815, 300)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(i, bin_nombre="Sony") for i in range(12)])
    hoja.show()
    barra = hoja._scroll.verticalScrollBar()
    qtbot.waitUntil(lambda: barra.maximum() > 0, timeout=2000)
    # un valor chico, que no se recorte al cambiar el ancho: si el scroll
    # saltara, `valueChanged` re-geometrizaria el flotante de rebote y el
    # test no probaria nada.
    barra.setValue(1)
    assert not hoja._pegado.isHidden()

    hoja.resize(1100, 300)
    qtbot.wait(10)

    margenes = hoja._content_layout.contentsMargins()
    esperado = (hoja._scroll.viewport().width()
                - margenes.left() - margenes.right())
    assert hoja._pegado.width() == esperado


def test_colapsar_desde_el_flotante_actualiza_el_flotante(qtbot):
    """Si no, el chevron del pegado se queda en `▾` con el bin ya
    colapsado: el unico encabezado que estas viendo miente."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(815, 300)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(i, bin_nombre="Sony") for i in range(12)])
    hoja.show()
    barra = hoja._scroll.verticalScrollBar()
    qtbot.waitUntil(lambda: barra.maximum() > 0, timeout=2000)
    barra.setValue(barra.maximum())
    assert hoja._pegado.nombre == "Sony"

    hoja._pegado.alternar_colapso()

    assert hoja.bin_collapsed("Sony")
    assert hoja._pegado.chevron.text() == "▸"


def test_quitar_un_bin_se_lleva_su_meta(qtbot):
    """`_bin_meta` va por nombre y no se podaba: la carpeta de origen de un
    bin que ya no existe se quedaba en memoria para siempre, y un bin nuevo
    con el mismo nombre la heredaba."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])
    hoja.set_bin_meta("Dron", origen="02. VIDEO DRONE", proxies=(1, 1))

    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert "Dron" not in hoja._bin_meta


def test_renombrar_un_bin_se_lleva_su_meta_al_nombre_nuevo(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])
    hoja.set_bin_meta("Dron", origen="02. VIDEO DRONE", proxies=(1, 1))

    hoja.renombrar_bin("Dron", "Dron DJI")
    hoja.set_bin_order(["Dron DJI"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron DJI")])

    assert "Dron" not in hoja._bin_meta
    cabecera = hoja.bin_header_widget("Dron DJI")
    assert cabecera.source_label.text() == "02. VIDEO DRONE"


def test_un_bin_colapsado_sigue_colapsado_despues_de_renombrarlo(qtbot):
    """`_colapsados` va por nombre: sin migrarlo, cambiarle el nombre a un
    bin cerrado lo abria solo."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])
    hoja.set_bin_collapsed("Dron", True)

    hoja.renombrar_bin("Dron", "Dron DJI")
    hoja.set_bin_order(["Dron DJI"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron DJI")])

    assert hoja.bin_collapsed("Dron DJI")
    assert hoja.item_widgets[0].isHidden()


def test_el_encabezado_pegado_se_distingue_del_que_va_en_el_flujo(qtbot):
    """El `.bin.stuck` del mockup. Va por propiedad y QSS, no con un
    `QGraphicsDropShadowEffect`: ese efecto segfauteo en la suite --
    doble propiedad entre el padre y `setGraphicsEffect`-- y una sombra no
    vale una caida intermitente.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)

    assert hoja._pegado.property("pegado") is True
    assert hoja.bin_header_widget("Sony") is None


def test_construir_el_menu_no_deja_menus_colgados_del_encabezado(qtbot):
    """El menu NO se cuelga del encabezado.

    Colgandolo, cada apertura dejaba un `QMenu` mas como hijo en C++ con su
    objeto de Python ya muerto -- 51 menus vivos despues de 50 aperturas.
    Y cuando Qt repole al encabezado, `ensurePolished` recorre a los hijos
    y busca el override de Python de cada uno: sobre un envoltorio muerto
    eso es una caida, y asi cayo la suite.
    """
    from PySide6.QtWidgets import QMenu

    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])
    cabecera = hoja.bin_header_widget("Sony")

    for _ in range(5):
        cabecera.construir_menu()

    assert cabecera.findChildren(QMenu) == []


# --- la fila de chips de bin (F6) ------------------------------------------


def test_hay_un_chip_por_bin_mas_el_de_todos(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony FX30", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony FX30"),
                    _thumb(1, bin_nombre="Dron")])

    assert hoja.chips_de_bin() == ["Todos", "Sony FX30", "Dron"]


def test_el_chip_de_bin_escribe_el_filtro(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony FX30", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony FX30"),
                    _thumb(1, bin_nombre="Dron")])
    estados = []
    hoja.filters_changed.connect(estados.append)

    hoja.chip_de_bin("Dron").click()

    assert estados[-1].bin == "Dron"

    hoja.chip_de_bin("todos").click()

    assert estados[-1].bin == "todos"


def test_el_chip_de_bin_dice_cuantos_clips_tiene(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron"), _thumb(1, bin_nombre="Dron")])

    assert "2" in hoja.chip_de_bin("Dron").text()


def test_con_un_solo_bin_la_fila_no_aparece(qtbot):
    """Filtrar por el unico bin que hay no filtra nada: seria una fila mas
    en una barra que ya lleva dos grupos y siete chips."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])

    assert hoja.fila_de_bins().isHidden()

    hoja.set_bin_order(["Dron", "Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron"), _thumb(1, bin_nombre="Sony")])

    assert not hoja.fila_de_bins().isHidden()


def test_si_el_bin_filtrado_desaparece_el_filtro_vuelve_a_todos(qtbot):
    """Quitar un bin mientras lo estabas filtrando dejaba la hoja vacia sin
    ningun chip encendido que explicara por que."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])
    hoja.chip_de_bin("Dron").click()
    estados = []
    hoja.filters_changed.connect(estados.append)

    hoja.set_bin_order(["Sony"])

    assert hoja.filter_state().bin == "todos"
    assert estados[-1].bin == "todos"


def test_un_bin_de_nombre_larguisimo_no_empuja_el_minimo_de_la_hoja(qtbot):
    """El chip mas ancho de una fila ES su ancho minimo, y ese minimo se
    propaga hasta la ventana. Las carpetas de verdad se llaman «01. VIDEO
    CARD A SONY FX30», asi que sin cortar el nombre esto le comeria ancho
    al video."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])
    corto = hoja.minimumSizeHint().width()

    largo = "01. VIDEO CARD A SONY FX30 SEGUNDA TARJETA"
    hoja.set_bin_order(["Sony", largo])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre=largo)])

    assert hoja.minimumSizeHint().width() <= corto
    # y el nombre completo se sigue leyendo en el encabezado del bin
    assert hoja.bin_header_widget(largo).name_label.text() == largo


# --- lo que se saca de la vista no se destruye AHORA (revision final) ------


def test_el_encabezado_que_se_va_no_se_destruye_en_el_acto(qtbot):
    """`pop(nombre).setParent(None)` destruia el widget de C++ EN ESA LINEA:
    `pop` devuelve un temporal, PySide le devuelve la propiedad a Python al
    quitarle el padre, y al morir la ultima referencia se borra.

    El camino que lo dispara es renombrar: el encabezado viejo se destruye
    --con su `QLineEdit` adentro-- mientras el stack sigue dentro del evento
    de teclado de ese mismo `QLineEdit`. Use-after-free, la misma familia de
    los tres segfaults que ya costaron arreglos en este archivo.

    El test NO puede quedarse con una referencia al encabezado: teniendola,
    el envoltorio de Python no muere y el bug no aparece. Por eso se escucha
    `destroyed`, que es una conexion de C++, y se suelta la referencia antes
    de disparar.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])
    destruido = []
    hoja.bin_header_widget("Dron").destroyed.connect(lambda *_: destruido.append(1))

    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert hoja.bin_headers() == ["Sony"]
    # todavia no: lo mata el ciclo de eventos, no la linea que lo saco
    assert destruido == []


def test_el_bloque_de_grupo_que_se_vacia_tampoco(qtbot):
    """Mismo patron, mismo riesgo: los bloques se sacan desde `_regroup`,
    que corre dentro del click que reclasifico el clip."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0, room_label="Cocina")])
    destruido = []
    hoja._blocks[(SIN_BIN, "Cocina")].destroyed.connect(lambda *_: destruido.append(1))

    hoja.set_clips([_thumb(0, room_label="Baño")])

    assert destruido == []


def test_el_menu_del_bin_que_se_va_tampoco_se_destruye_en_el_acto(qtbot):
    """«Quitar del proyecto» y «Renombrar» rehacen la hoja desde adentro del
    `triggered` de su propia accion, y rehacer la hoja se lleva puesto el
    encabezado -- con su menu."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])
    cabecera = hoja.bin_header_widget("Dron")
    cabecera._menu = cabecera.construir_menu()
    destruido = []
    cabecera._menu.destroyed.connect(lambda *_: destruido.append(1))
    del cabecera

    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert destruido == []


def test_pedir_el_mismo_orden_de_bins_no_reacomoda_nada(qtbot):
    """`_refresh_sheet` llama a `set_bin_order` SIEMPRE, y corre en cada
    flecha, cada cuarto y cada pick. Poner `_firma = None` a ciegas anulaba
    justo la guarda que evita re-colocar cuando nada cambio -- son ~12 ms
    por tecla con 132 clips, en la app que existe para ser rapida.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(815, 900)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])
    firma = hoja._firma
    assert firma is not None      # ya se acomodo una vez

    hoja.set_bin_order(["Sony", "Dron"])

    assert hoja._firma is firma


# --- la flecha que cae dentro de un bin colapsado (revision final) ---------


def test_llegar_con_la_flecha_a_un_bin_cerrado_lo_abre(qtbot):
    """Colapsar es VISUAL y no saca clips de la cola de las flechas
    (spec §4.1), asi que la flecha SI llega a un bin cerrado. Dejarla
    llegar sin abrirlo deja el clip actual invisible y el scroll apuntando
    a la geometria vieja de una tarjeta escondida.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(815, 900)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")])
    hoja.centrar_en(0)
    hoja.set_bin_collapsed("Dron", True)

    hoja.centrar_en(1)

    assert not hoja.bin_collapsed("Dron")
    assert not hoja.item_widgets[1].isHidden()


def test_llegar_con_la_flecha_a_SIN_BIN_cerrado_tambien_lo_abre(qtbot):
    """La seccion de sueltos esta arriba de todo y estorba, asi que
    colapsarla es el gesto obvio. Leyendo `clip.bin_nombre` crudo esto no
    funcionaba: un clip suelto trae la cadena vacia, y la vacia nunca esta
    en `_colapsados`, donde lo que vive es «Sin bin». Sintoma: avanzas con
    las flechas, el video cambia, la seccion no se abre y la tarjeta sigue
    escondida -- no ves donde estas parado.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(815, 900)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="")])
    hoja.centrar_en(0)
    hoja.set_bin_collapsed(SIN_BIN, True)

    hoja.centrar_en(1)

    assert not hoja.bin_collapsed(SIN_BIN)
    assert not hoja.item_widgets[1].isHidden()


def test_colapsar_el_bin_del_clip_actual_no_lo_reabre_solo(qtbot):
    """Lo abre la flecha que te LLEVA ahi, no cualquier refresco: la hoja
    se refresca en cada tecla, y con eso el bin que acabas de cerrar se
    reabriria solo al primer pick.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(815, 900)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])
    hoja.centrar_en(0)
    hoja.set_bin_collapsed("Sony", True)

    hoja.centrar_en(0)

    assert hoja.bin_collapsed("Sony")


# --- F8 Tarea 3: los bins se DECLARAN, no se deducen -------------------------


def test_un_bin_sin_clips_igual_aparece(qtbot):
    """El gesto de Premiere es crear el bin y despues llenarlo. Si el bin
    vacio no se dibuja, no hay a donde arrastrar."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert hoja.bin_headers() == ["Sony", "Dron"]
    assert hoja.bin_header_widget("Dron") is not None


def test_los_clips_sin_bin_van_primero_y_en_su_seccion(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="")])

    assert hoja.bin_headers() == [SIN_BIN, "Sony"]


def test_la_seccion_sin_bin_se_esconde_cuando_no_hay_sueltos(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert hoja.bin_headers() == ["Sony"]


def test_un_bin_vacio_no_desaparece_al_refrescar(qtbot):
    """`_regroup` corre en cada tecla. Si el bin vacio solo sobreviviera a
    la primera pasada, se iria al primer pick."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    hoja.update_clips([_thumb(0, bin_nombre="Sony", flag="pick")])

    assert hoja.bin_headers() == ["Sony", "Dron"]


def test_el_encabezado_de_un_bin_vacio_dice_cero_clips(qtbot):
    """El conteo sale de las tarjetas, y un bin vacio no tiene ninguna: sin
    esto se quedaba con el numero del bin que ocupo ese encabezado antes."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert hoja.bin_header_widget("Dron").count_label.text() == "0 clips"


def test_la_seccion_sin_bin_cuenta_sus_clips(qtbot):
    """Los sueltos tienen `bin_nombre` vacio y el conteo va por nombre de
    seccion: sin traducirlo, «Sin bin» decia siempre 0."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0), _thumb(1)])

    assert hoja.bin_header_widget(SIN_BIN).count_label.text() == "2 clips"


def test_colapsar_sin_bin_esconde_sus_tarjetas(qtbot):
    """El colapso va por nombre de SECCION. Con el nombre crudo del clip
    --que en los sueltos es la cadena vacia-- cerrar «Sin bin» no escondia
    nada."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])

    hoja.set_bin_collapsed(SIN_BIN, True)

    assert hoja.item_widgets[0].isHidden()


# --- F8 Tarea 4: el boton «+ Bin nuevo» --------------------------------------


def test_el_boton_pide_un_bin_nuevo(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    pedidos = []
    hoja.bin_nuevo_pedido.connect(lambda: pedidos.append(1))

    hoja.boton_bin_nuevo.click()

    assert pedidos == [1]


def test_el_boton_no_se_roba_el_foco(qtbot):
    """Mismo criterio que el resto de la barra: con el foco puesto, el
    espacio activaria el boton en vez de reproducir."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)

    assert hoja.boton_bin_nuevo.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_el_boton_se_queda_en_el_glifo_cuando_no_cabe(qtbot):
    """Un QPushButton no elide, RECORTA: con el texto largo a 30 px se veia
    media letra partida, que parece un error de dibujo. Y tiene que VOLVER al
    texto completo cuando hay lugar -- si el ancho que pide saliera del texto
    de ahora, al encogerse pediria el del glifo y se quedaria corto para
    siempre.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.show()
    qtbot.waitExposed(hoja)

    hoja.resize(400, 300)
    qtbot.wait(10)
    assert hoja.boton_bin_nuevo.text() == "＋"

    hoja.resize(900, 300)
    qtbot.wait(10)
    assert hoja.boton_bin_nuevo.text() == "＋ Bin nuevo"


# --- el menu de «Sin bin»: solo lo que aplica a una vista --------------------


def test_el_menu_de_sin_bin_no_ofrece_lo_que_es_de_un_bin(qtbot):
    """«Sin bin» no es un bin: renombrarlo, enlazarle proxies o quitarlo del
    proyecto no significan nada ahi. Hoy tres de esos renglones son
    inofensivos por accidente --`BinTree` no encuentra el nombre y no hace
    nada-- y eso no es una razon para dejarlos.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0), _thumb(1)])

    menu = hoja.bin_header_widget(SIN_BIN).construir_menu()

    textos = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert textos == ["Seleccionar los 2 clips", "Colapsar"]


def test_el_menu_de_un_bin_de_verdad_no_perdio_nada(qtbot):
    """La contracara: recortar el de «Sin bin» no puede recortar el otro."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])

    menu = hoja.bin_header_widget("Dron").construir_menu()

    assert "Quitar del proyecto" in [a.text() for a in menu.actions()]


def test_el_doble_click_no_renombra_la_seccion_de_sueltos(qtbot):
    """La otra puerta al mismo renombrado. Dejarla abierta movia la meta y el
    colapso de «Sin bin» a un nombre inventado, y la seccion perdia en
    silencio el estado de colapsado."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    cabecera = hoja.bin_header_widget(SIN_BIN)

    cabecera.empezar_a_renombrar()

    assert cabecera.name_edit.isHidden()
    assert not cabecera.name_label.isHidden()


def test_el_encabezado_pegado_copia_si_es_un_bin_de_verdad(qtbot):
    """El flotante es una COPIA y arma su propio menu: si no copiara este
    dato, el menu recortado volveria completo apenas te desplazas."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])

    hoja._pegado.copiar_de(hoja.bin_header_widget(SIN_BIN))

    # el menu se guarda en una variable: sus `QAction` cuelgan de el, y un
    # `QMenu` temporal muere antes de que termine de leerse la lista
    menu = hoja._pegado.construir_menu()
    textos = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert textos == ["Seleccionar los 1 clips", "Colapsar"]
