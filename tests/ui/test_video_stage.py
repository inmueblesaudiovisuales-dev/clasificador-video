from PySide6.QtCore import Qt

from clasificador_video.ui import theme
from clasificador_video.ui.video_stage import BADGE_TEXT_MIX, VideoStage


class FakeMpv:
    def __init__(self, **kwargs):
        self.pause = True
        self.time_pos = 0.0
        self.duration = 0.0

    def play(self, path):
        self.loaded = path


def _stage(qtbot) -> VideoStage:
    stage = VideoStage(mpv_factory=FakeMpv)
    qtbot.addWidget(stage)
    stage.resize(529, 940)
    return stage


def _stage_visible(qtbot) -> VideoStage:
    """`qtbot.addWidget` NO muestra el widget: sin `show()` previo,
    `waitExposed` se queda esperando para siempre. Y sin exponer, el layout
    nunca corre y `stage.video` conserva su tamaño inicial."""
    stage = _stage(qtbot)
    stage.show()
    qtbot.waitExposed(stage)
    return stage


def test_el_badge_de_cuarto_lleva_el_color_de_su_cuarto(qtbot):
    """El punto va con el color PURO del cuarto y el texto con su version
    clara: aclarar tambien desatura, y un badge todo aclarado se lee gris."""
    stage = _stage(qtbot)
    stage.badges.set_room("Cocina", theme.room_color(0))
    texto = stage.badges.room_badge.text()
    assert texto.endswith("COCINA")
    assert theme.room_color(0) in texto            # el punto, sin aclarar
    estilo = stage.badges.room_badge.styleSheet()
    assert theme.aclarar(theme.room_color(0), 0.35) in estilo


def test_el_badge_de_estado_es_otro_badge_y_no_texto_pegado(qtbot):
    """Juntar cuarto y estado en una sola etiqueta gris tira el color, que
    es lo que hace legible el estado de un vistazo."""
    stage = _stage(qtbot)
    stage.badges.set_flag("pick")
    assert "PICK" in stage.badges.flag_badge.text()
    assert theme.PICK_COLOR in stage.badges.flag_badge.styleSheet()
    assert not stage.badges.flag_badge.isHidden()


def test_reject_pinta_el_badge_con_su_color(qtbot):
    stage = _stage(qtbot)
    stage.badges.set_flag("reject")
    assert theme.REJECT_COLOR in stage.badges.flag_badge.styleSheet()


def test_sin_marca_no_hay_badge_de_estado(qtbot):
    stage = _stage(qtbot)
    stage.badges.set_flag("none")
    assert stage.badges.flag_badge.isHidden()


def test_sin_cuarto_el_badge_lo_dice_y_no_inventa_color(qtbot):
    stage = _stage(qtbot)
    stage.badges.set_room(None, None)
    assert "SIN CLASIFICAR" in stage.badges.room_badge.text()


def test_la_scrub_bar_es_hija_del_video_no_hermana(qtbot):
    """Si fuera hermana volveria a ser una banda y le robaria altura al
    video, que es el problema que este rediseño existe para resolver."""
    stage = _stage(qtbot)
    assert stage.scrub_bar.parent() is stage.video


def test_todos_los_overlays_son_hijos_del_video(qtbot):
    stage = _stage(qtbot)
    for widget in (stage.file_label, stage.badges, stage.scrim,
                   stage.timecode_label, stage.quality):
        assert widget.parent() is stage.video, widget.objectName()


def test_la_scrub_bar_es_translucida(qtbot):
    """Hallazgo de la F0: sin esta bandera un widget de QPainter sobre el
    video pinta fondo opaco donde no dibuja y tapa una franja."""
    stage = _stage(qtbot)
    assert stage.scrub_bar.testAttribute(Qt.WA_TranslucentBackground)


def test_la_scrub_bar_va_en_modo_overlay(qtbot):
    stage = _stage(qtbot)
    assert stage.scrub_bar.track_color().alpha() < 255


def test_los_overlays_pasivos_no_capturan_el_mouse(qtbot):
    stage = _stage(qtbot)
    for widget in (stage.file_label, stage.badges, stage.scrim, stage.timecode_label):
        assert widget.testAttribute(Qt.WA_TransparentForMouseEvents), widget.objectName()


def test_la_scrub_bar_si_recibe_mouse(qtbot):
    """Es el unico overlay interactivo: click y arrastre hacen seek."""
    stage = _stage(qtbot)
    assert not stage.scrub_bar.testAttribute(Qt.WA_TransparentForMouseEvents)


def test_el_selector_de_calidad_si_recibe_mouse(qtbot):
    stage = _stage(qtbot)
    assert not stage.quality.testAttribute(Qt.WA_TransparentForMouseEvents)


def test_los_overlays_se_reposicionan_al_cambiar_el_tamano(qtbot):
    stage = _stage_visible(qtbot)
    stage.resize(400, 600)
    qtbot.wait(50)
    esperado = stage.video.width() - 2 * theme.OVERLAY_MARGIN
    assert stage.scrub_bar.width() == esperado


def test_el_pie_del_video_queda_pegado_al_borde_inferior(qtbot):
    """Hasta la F6 la barra era lo ultimo del pie. Ahora abajo van la pastilla
    de rango y la fila de teclas, como en el mockup, asi que quien tiene que
    respetar el margen es la fila de abajo -- no la barra."""
    stage = _stage_visible(qtbot)
    stage.resize(529, 940)
    qtbot.wait(50)
    borde = max(stage.keys_hint.y() + stage.keys_hint.height(),
                stage.range_pill.y() + stage.range_pill.height())
    assert stage.video.height() - borde == theme.OVERLAY_MARGIN
    assert stage.scrub_bar.y() + stage.scrub_bar.height() < borde


def test_el_nombre_de_archivo_va_arriba_a_la_izquierda(qtbot):
    stage = _stage_visible(qtbot)
    qtbot.wait(50)
    assert stage.file_label.x() == theme.OVERLAY_MARGIN
    assert stage.file_label.y() == theme.OVERLAY_MARGIN


def test_el_selector_de_calidad_va_arriba_a_la_derecha(qtbot):
    stage = _stage_visible(qtbot)
    qtbot.wait(50)
    derecha = stage.quality.x() + stage.quality.width()
    assert stage.video.width() - derecha == theme.OVERLAY_MARGIN


def test_el_scrim_cubre_el_ancho_completo_del_borde_inferior(qtbot):
    stage = _stage_visible(qtbot)
    qtbot.wait(50)
    assert stage.scrim.width() == stage.video.width()
    assert stage.scrim.y() + stage.scrim.height() == stage.video.height()


def test_ancho_para_aspecto_vertical():
    """La medida objetiva de la F2: cuerpo de 940 px con un clip 9:16."""
    assert VideoStage.width_for(940, 9 / 16) == 529


def test_ancho_para_aspecto_horizontal():
    assert VideoStage.width_for(600, 16 / 9) == 1067


def test_ancho_nunca_es_cero():
    assert VideoStage.width_for(0, 9 / 16) >= 1


# --- F6 Task 2: el badge `▶ auto` --------------------------------------------


def test_el_badge_auto_arranca_apagado(qtbot):
    """Nace escondido: hasta que un clip no arranque solo, no hay nada que
    anunciar."""
    stage = _stage(qtbot)
    assert stage.badges.auto_badge.isHidden()


def test_el_badge_auto_se_prende_y_se_apaga(qtbot):
    stage = _stage(qtbot)
    stage.badges.set_auto(True)
    assert not stage.badges.auto_badge.isHidden()
    stage.badges.set_auto(False)
    assert stage.badges.auto_badge.isHidden()


def test_el_badge_auto_dice_lo_mismo_que_el_mockup(qtbot):
    """En mayusculas: el mockup lo escribe en minusculas pero lo pinta con
    `text-transform: uppercase`, y QSS no tiene esa propiedad. Comparado
    contra el pixel del arnes, no contra el HTML."""
    stage = _stage(qtbot)
    stage.badges.set_auto(True)
    assert stage.badges.auto_badge.text() == "▶ AUTO"


def test_el_badge_auto_usa_el_color_del_acento_y_no_el_de_un_estado(qtbot):
    """No es pick ni reject: es un aviso de lo que hace el reproductor. Con
    PICK_COLOR se leeria como un estado del clip (theme.py, separacion por
    canal semantico)."""
    stage = _stage(qtbot)
    stage.badges.set_auto(True)
    hoja = stage.badges.auto_badge.styleSheet()
    # el borde sale como `rgba(r, g, b, a)`, no en hexadecimal: se compara
    # contra los componentes, no contra el token escrito
    r, g, b = (int(theme.CURRENT_COLOR[i:i + 2], 16) for i in (1, 3, 5))
    assert f"rgba({r}, {g}, {b}," in hoja
    assert theme.aclarar(theme.CURRENT_COLOR, BADGE_TEXT_MIX) in hoja
    assert theme.PICK_COLOR not in hoja
    assert theme.REJECT_COLOR not in hoja


# --- F6 Task 3: el control de velocidad --------------------------------------


def test_el_control_de_velocidad_tiene_las_tres_del_mockup(qtbot):
    stage = _stage(qtbot)
    assert [b.text() for b in stage.speed.buttons] == ["1×", "2×", "4×"]


def test_el_control_de_velocidad_arranca_en_1x(qtbot):
    assert _stage(qtbot).speed.current() == "1×"


def test_el_control_de_velocidad_recibe_mouse(qtbot):
    """Es interactivo como el de calidad: si fuera transparente al mouse, se
    veria y no se podria tocar."""
    stage = _stage(qtbot)
    assert not stage.speed.testAttribute(Qt.WA_TransparentForMouseEvents)


def test_el_control_de_velocidad_va_a_la_izquierda_del_de_calidad(qtbot):
    """Ese es su lugar en el mockup, y los dos viven en la misma fila."""
    stage = _stage_visible(qtbot)
    qtbot.wait(50)
    assert stage.speed.x() + stage.speed.width() <= stage.quality.x()
    assert stage.speed.y() == stage.quality.y()


def test_el_segmento_activo_de_velocidad_va_en_ambar_y_no_en_gris(qtbot):
    """El mockup los separa a proposito (`.seg b.on` contra `.seg.speed
    b.on`): estar en 2× o 4× cambia lo que ves y es facil olvidarlo, asi que
    el estado tiene que gritar. Si el control perdiera su objectName, la
    regla de descendencia deja de aplicar sin ningun otro sintoma."""
    from clasificador_video.ui.theme import build_stylesheet
    stage = _stage(qtbot)
    assert stage.speed.objectName() == "speedSegmented"
    regla = "QWidget#speedSegmented QPushButton#segmentedButton:checked"
    hoja = build_stylesheet()
    assert regla in hoja
    assert theme.aclarar(theme.CURRENT_COLOR, theme.SPEED_ON_TEXT_MIX) in hoja


def test_el_control_de_velocidad_conserva_su_caja(qtbot):
    """Regresion real al construirlo: darle objectName propio lo saco de la
    regla del contenedor y los numeros quedaron flotando sobre el video, sin
    fondo oscuro ni borde. Un control que se ve bien sobre un video oscuro y
    desaparece sobre uno claro."""
    from clasificador_video.ui.theme import build_stylesheet
    stage = _stage(qtbot)
    hoja = build_stylesheet()
    caja = [linea for linea in hoja.splitlines()
            if "QWidget#speedSegmented {" in linea
            or ("speedSegmented" in linea and "segmentedControl" in linea)]
    assert caja, "el control de velocidad no hereda la caja del segmentado"
    assert stage.speed.objectName() == "speedSegmented"


# --- F6 Task 4: el pie del video, completo -----------------------------------


def test_el_timecode_lleva_el_numero_de_cuadro(qtbot):
    """El mockup pone `f 293` al lado del timecode: marcar in/out por cuadro
    exacto exige ver el numero de cuadro, no solo el tiempo."""
    stage = _stage(qtbot)
    stage.set_timecode("00:00:09:23", frame=293)
    assert "f 293" in stage.frame_label.text()


def test_sin_clip_el_timecode_y_el_cuadro_quedan_vacios(qtbot):
    stage = _stage(qtbot)
    stage.set_timecode("00:00:09:23", frame=293)
    stage.set_timecode("", frame=None)
    assert stage.timecode_label.text() == ""
    assert stage.frame_label.text() == ""


def test_la_pastilla_de_rango_dice_largo_cuadros_y_total(qtbot):
    stage = _stage(qtbot)
    stage.set_range_pill(rango_segundos=7.13, cuadros=212, total_segundos=18.37)
    texto = stage.range_pill.text()
    assert "212 f" in texto and "18:11" in texto


def test_sin_rango_marcado_la_pastilla_no_se_ve(qtbot):
    stage = _stage(qtbot)
    stage.set_range_pill(None, None, total_segundos=18.37)
    assert stage.range_pill.isHidden()


def test_la_pastilla_de_rango_reaparece_al_volver_a_marcar(qtbot):
    """Esconder y mostrar es un camino de ida y vuelta: si solo se escondiera,
    marcar in/out despues de borrarlo no mostraria nada."""
    stage = _stage(qtbot)
    stage.set_range_pill(None, None, total_segundos=18.37)
    stage.set_range_pill(7.13, 212, total_segundos=18.37)
    assert not stage.range_pill.isHidden()


def test_el_renglon_de_teclas_esta_bajo_la_barra(qtbot):
    """El mockup lo pone ahi: es la chuleta de lo que se puede hacer sobre el
    video sin tocar el mouse."""
    stage = _stage_visible(qtbot)
    qtbot.wait(50)
    assert stage.keys_hint.y() > stage.scrub_bar.y()


def test_el_renglon_de_teclas_nombra_las_teclas_que_existen(qtbot):
    """Anunciar una tecla que no hace nada es el bug que este proyecto ya
    tuvo cuatro veces. Las de esta fila son de la F6."""
    stage = _stage(qtbot)
    texto = stage.keys_hint.text()
    for tecla in ("←", "→", ",", "."):
        assert tecla in texto


def test_el_scrim_de_arriba_arranca_en_el_borde(qtbot):
    stage = _stage_visible(qtbot)
    qtbot.wait(50)
    assert stage.top_scrim.y() == 0
    assert stage.top_scrim.width() == stage.video.width()


def test_el_nombre_de_archivo_va_como_texto_sobre_un_scrim(qtbot):
    """El mockup no lo mete en pastilla: lo pone sobre un degradado que
    arranca en el borde de arriba.

    Se comprueba contra el QSS del tema y no contra `file_label.styleSheet()`,
    que devuelve cadena vacia --el fondo lo pone la hoja global--: una
    asercion sobre esa cadena pasaria sin haber cambiado nada.

    El plan pedia que la regla NO tuviera `background-color`. Resulto al
    reves: sin esa propiedad la etiqueta hereda la global `QWidget`, que es
    opaca, y sale con una caja negra peor que la pastilla que se le quito.
    Lo que hay que exigir es que sea TRANSPARENTE.
    """
    stage = _stage_visible(qtbot)
    bloque = theme.build_stylesheet().split("QLabel#overlayFile {")[1].split("}")[0]
    assert "background-color: transparent" in bloque
    assert theme.OVERLAY_BG not in bloque      # ni pastilla ni borde
    assert "border:" not in bloque


def test_el_pie_no_captura_el_mouse(qtbot):
    """Todo lo del pie es informativo menos la barra: si capturaran el mouse,
    el click para hacer seek se quedaria en una etiqueta."""
    stage = _stage(qtbot)
    for widget in (stage.frame_label, stage.range_pill, stage.keys_hint,
                   stage.top_scrim):
        assert widget.testAttribute(Qt.WA_TransparentForMouseEvents), \
            widget.objectName()


def test_las_etiquetas_del_pie_declaran_fondo_transparente(qtbot):
    """La hoja global tiene `QWidget { background-color: ... }`, que alcanza
    tambien a las QLabel. Una etiqueta del pie que no declare transparente
    sale con su propia caja negra encima del video -- se ve feo y tapa
    imagen. Ya paso al construir el pie: `f 293` e `IN 00:04:12` aparecieron
    dentro de cajas que el mockup no tiene."""
    hoja = theme.build_stylesheet()
    for nombre in ("overlayFile", "overlayFrame", "overlayInOut",
                   "overlayKeys", "overlayTimecode"):
        bloque = hoja.split(f"QLabel#{nombre} {{")[1].split("}")[0]
        assert "background-color: transparent" in bloque, nombre


def test_un_clip_de_mas_de_un_minuto_muestra_los_minutos_en_la_pastilla(qtbot):
    """`SS:FF` alcanza para un recorrido, que casi nunca pasa del minuto, pero
    un clip largo sin minutos mentiria: `total 05:12` para algo de 1m05s."""
    from clasificador_video.ui.video_stage import formato_corto
    assert formato_corto(18.37, 30.0) == "18:11"      # corto: sin minutos
    assert formato_corto(65.0, 30.0) == "01:05:00"    # largo: con minutos


def test_la_pastilla_sin_fps_no_divide_entre_cero(qtbot):
    """Sesion restaurada sin fps: mejor `--:--` que reventar."""
    from clasificador_video.ui.video_stage import formato_corto
    assert formato_corto(18.37, 0.0) == "--:--"


def test_las_etiquetas_del_pie_se_reacomodan_al_cambiar_el_texto(qtbot):
    """Bug real encontrado revisando la F6: las etiquetas se colocaban solo
    en `_place_overlays`, que corre al cambiar de TAMAÑO. Como nacen vacias,
    quedaban de 7 px de ancho, y al escribirles `f 293` o `IN 00:04:12` el
    texto no cabia: se veian cortadas hasta que redimensionaras la ventana.

    Los arneses lo tapaban porque siempre habia un resize despues de poner
    los datos. En la app real, marcar IN no mostraba nada.
    """
    stage = _stage_visible(qtbot)
    qtbot.wait(50)
    stage.set_timecode("00:00:09:23", frame=293)
    stage.set_in_out_labels("00:04:12", "00:11:16")
    stage.set_range_pill(7.13, 212, 18.37)
    qtbot.wait(20)
    for nombre in ("timecode_label", "frame_label", "io_label", "range_pill"):
        widget = getattr(stage, nombre)
        assert widget.width() >= widget.sizeHint().width(), nombre


def test_el_in_out_sigue_pegado_al_borde_derecho_al_crecer(qtbot):
    """Va alineado a la derecha: si solo creciera hacia la derecha se saldria
    del video en vez de estirarse hacia la izquierda."""
    stage = _stage_visible(qtbot)
    qtbot.wait(50)
    stage.set_in_out_labels("00:04:12", "00:11:16")
    qtbot.wait(20)
    derecha = stage.io_label.x() + stage.io_label.width()
    assert stage.video.width() - derecha == theme.OVERLAY_MARGIN
