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


def test_la_fila_de_teclas_se_esconde_si_no_cabe_junto_a_la_pastilla(qtbot):
    """Bug real encontrado revisando la F6: los dos van en la misma fila --la
    pastilla a la izquierda, las teclas a la derecha-- y con un video angosto
    se encimaban, dejando las dos ilegibles.

    Se esconde la FILA DE TECLAS y no la pastilla: la pastilla dice cuanto
    dura el rango que marcaste, la fila es un recordatorio de teclas que ya
    te sabes.
    """
    stage = _stage_visible(qtbot)
    # el orden importa y es el de la app: primero queda el tamaño, y la
    # pastilla aparece DESPUES, al abrir un clip que trae rango marcado. Con
    # la comprobacion solo en el acomodo por tamaño, este test pasaba y la
    # app seguia rota.
    stage.resize(300, 700)
    qtbot.wait(50)
    stage.set_range_pill(7.13, 212, 18.37)
    qtbot.wait(20)
    assert stage.keys_hint.isHidden()

    stage.resize(900, 700)          # con espacio de sobra, vuelve
    qtbot.wait(50)
    assert not stage.keys_hint.isHidden()


def test_sin_pastilla_la_fila_de_teclas_se_queda(qtbot):
    """Sin rango marcado la pastilla no ocupa nada, asi que no hay conflicto
    y el recordatorio se ve completo."""
    stage = _stage_visible(qtbot)
    stage.set_range_pill(None, None, 18.37)
    stage.resize(400, 700)
    qtbot.wait(50)
    assert not stage.keys_hint.isHidden()


def test_la_fila_del_timecode_no_se_encima_con_el_in_out(qtbot):
    """Timecode + numero de cuadro a la izquierda, IN/OUT a la derecha. En un
    video angosto tambien pueden chocar."""
    stage = _stage_visible(qtbot)
    stage.set_timecode("00:00:09:23", frame=293)
    stage.set_in_out_labels("00:04:12", "00:11:16")
    stage.resize(340, 700)
    qtbot.wait(50)
    if not stage.io_label.isHidden():
        izquierda = stage.frame_label.x() + stage.frame_label.width()
        assert stage.io_label.x() >= izquierda


def test_al_borrar_el_rango_vuelve_la_fila_de_teclas(qtbot):
    """`U` borra el in/out: la pastilla desaparece y libera el renglon, asi
    que el recordatorio de teclas tiene que volver. Sin esto se iba con el
    primer rango y no volvia en toda la sesion."""
    stage = _stage_visible(qtbot)
    stage.resize(300, 700)
    qtbot.wait(50)
    stage.set_range_pill(7.13, 212, 18.37)
    qtbot.wait(20)
    assert stage.keys_hint.isHidden()
    stage.set_range_pill(None, None, 18.37)
    qtbot.wait(20)
    assert not stage.keys_hint.isHidden()


# --- badge de proxy (F9) -----------------------------------------------


def test_el_badge_de_proxy_dice_la_resolucion_real(qtbot):
    """El mockup dibuja `Proxy 1080p`, pero el S03 de la FX30 mide
    1280x720: el texto sale del archivo, no del dibujo."""
    stage = _stage(qtbot)
    stage.badges.set_proxy("720p")
    assert stage.badges.proxy_badge.text() == "PROXY 720P"
    assert not stage.badges.proxy_badge.isHidden()


def test_sin_proxy_el_badge_se_esconde(qtbot):
    stage = _stage(qtbot)
    stage.badges.set_proxy("720p")
    stage.badges.set_proxy(None)
    assert stage.badges.proxy_badge.isHidden()


def test_el_badge_de_proxy_sin_resolucion_conocida_dice_solo_proxy(qtbot):
    """Sesion restaurada de disco: el clip trae su proxy guardado pero
    nadie volvio a correr ffprobe, asi que no se sabe cuanto mide.
    Inventar «1080p» seria mentir; callar la resolucion, no."""
    stage = _stage(qtbot)
    stage.badges.set_proxy("")
    assert stage.badges.proxy_badge.text() == "PROXY"
    assert not stage.badges.proxy_badge.isHidden()


def test_el_badge_de_proxy_va_al_final_de_la_fila(qtbot):
    """Como en el mockup: cuarto, estado, auto y al final el proxy."""
    stage = _stage(qtbot)
    fila = stage.badges.layout()
    orden = [fila.itemAt(i).widget() for i in range(fila.count())]
    assert orden[-1] is stage.badges.proxy_badge


def test_los_cuatro_badges_juntos_caben_en_un_video_angosto(qtbot):
    """El badge de proxy le sumo 88 px a la fila (253 -> 341). En una
    laptop de 1150x800 el video baja a 416 px de ancho, y ahi es donde una
    fila de badges que no cabe se sale de la imagen.

    Un solo ancho de ventana no alcanza: ya paso con el pie del video, que
    se encimaba consigo mismo a 1150 px y se veia bien a 1600.
    """
    stage = _stage(qtbot)
    stage.badges.set_room("Recámara 1", theme.room_color(2))
    stage.badges.set_flag("destacado")
    stage.badges.set_auto(True)
    stage.badges.set_proxy("1080p")

    ancho_de_video_en_laptop = 416
    assert stage.badges.sizeHint().width() + 2 * theme.OVERLAY_MARGIN <= ancho_de_video_en_laptop


# --- la fila de arriba cuando el video es angosto (F10) ----------------


def _fila_de_arriba(stage):
    return (stage.file_label, stage.speed, stage.quality)


def test_ningun_control_de_arriba_se_sale_del_video(qtbot):
    """A 1150x800 --una laptop-- el video baja a 416 px de ancho y el
    control de velocidad terminaba en x = -165, o sea fuera de la imagen y
    encimado con el nombre del archivo.

    Ojo con el diagnostico: no es la ventana ANGOSTA, es la ventana BAJA.
    Con un clip vertical el ancho del video sale de la altura, asi que a
    800 px de alto no caben nombre + velocidad + calidad. Por eso las
    revisiones anteriores, hechas a 1000 px de alto, no lo veian.
    """
    # _stage_visible y no _stage: `qtbot.addWidget` NO muestra el widget, y
    # sin mostrarlo el acomodo de overlays no corre nunca -- el test pasaria
    # sin probar nada.
    stage = _stage_visible(qtbot)
    stage.set_file_label("C0087.MP4    87 / 128")
    stage.resize(416, 740)
    qtbot.wait(1)

    for control in _fila_de_arriba(stage):
        if not control.isHidden():
            assert control.x() >= 0, f"{control.objectName()} se sale por la izquierda"


def test_lo_primero_que_se_esconde_es_la_velocidad(qtbot):
    """Decision de Bruno: la velocidad se sigue cambiando con J K L, y el
    nombre del archivo es lo que te dice que clip estas viendo."""
    # _stage_visible y no _stage: `qtbot.addWidget` NO muestra el widget, y
    # sin mostrarlo el acomodo de overlays no corre nunca -- el test pasaria
    # sin probar nada.
    stage = _stage_visible(qtbot)
    stage.set_file_label("C0087.MP4    87 / 128")
    stage.resize(416, 740)
    qtbot.wait(1)

    assert stage.speed.isHidden()
    assert not stage.file_label.isHidden()
    assert not stage.quality.isHidden()


def test_con_ancho_de_sobra_la_velocidad_vuelve(qtbot):
    # _stage_visible y no _stage: `qtbot.addWidget` NO muestra el widget, y
    # sin mostrarlo el acomodo de overlays no corre nunca -- el test pasaria
    # sin probar nada.
    stage = _stage_visible(qtbot)
    stage.set_file_label("C0087.MP4    87 / 128")
    stage.resize(416, 740)
    qtbot.wait(1)
    stage.resize(529, 940)
    qtbot.wait(1)

    assert not stage.speed.isHidden()


def test_los_badges_no_se_encaraman_con_la_fila_de_arriba(qtbot):
    """El nombre del archivo mide 15 px y el selector de calidad 25, y los
    badges se colocaban debajo del NOMBRE -- o sea 2 px por dentro de la
    caja de la calidad, que es translucida y les comia el borde de arriba.

    Pasaba en los dos anchos desde la F6 y no se veia en la comparacion
    general: hay que ampliar para notarlo.
    """
    stage = _stage_visible(qtbot)
    stage.set_file_label("C0087.MP4    87 / 128")
    stage.badges.set_room("Comedor", theme.room_color(0))
    stage.badges.set_proxy("1080p")
    qtbot.wait(1)

    fila_de_arriba = stage.quality.geometry().united(stage.file_label.geometry())
    assert not fila_de_arriba.intersects(stage.badges.geometry())


# --- textos largos sobre el video (auditoria, pasada 3) ----------------


def test_el_nombre_del_archivo_no_se_mete_bajo_los_controles(qtbot):
    """Un nombre largo --y el de la app es `archivo   87 / 128`-- crecia
    hasta pasar POR DEBAJO del selector de calidad: se veia el nombre
    cortado a la mitad por una caja translucida encima.

    QSS no tiene `text-overflow: ellipsis`, asi que hay que cortarlo a
    mano, igual que en el rail (`ui/text.py`).
    """
    stage = _stage_visible(qtbot)
    stage.set_file_label("UN_NOMBRE_DE_ARCHIVO_MUY_LARGO_PARA_UN_CLIP_0001.MP4    87 / 128")
    qtbot.wait(1)

    assert not stage.file_label.geometry().intersects(stage.quality.geometry())
    assert stage.file_label.geometry().right() <= stage.video.width()


def test_poner_el_nombre_reacomoda_la_fila_de_arriba(qtbot):
    """El orden de los eventos otra vez: en la app los datos llegan
    DESPUES del ultimo resize, asi que colocar los controles solo al
    redimensionar los deja donde estaban. Ya paso con el pie en la F7.
    """
    stage = _stage_visible(qtbot)
    stage.set_file_label("corto.MP4")
    qtbot.wait(1)
    assert not stage.speed.isHidden()

    stage.set_file_label("UN_NOMBRE_DE_ARCHIVO_MUY_LARGO_PARA_UN_CLIP_0001.MP4    87 / 128")
    qtbot.wait(1)

    assert stage.speed.isHidden() or stage.speed.geometry().right() <= stage.video.width()


def test_un_cuarto_de_nombre_largo_no_desborda_la_fila_de_badges(qtbot):
    """El badge del cuarto crecia con el nombre y empujaba al de `▶ AUTO`
    fuera de la imagen."""
    stage = _stage_visible(qtbot)
    stage.badges.set_room("Recámara principal con vestidor y baño completo",
                          theme.room_color(0))
    stage.badges.set_flag("destacado")
    stage.badges.set_auto(True)
    stage.badges.set_proxy("720p")
    qtbot.wait(1)

    assert stage.badges.geometry().right() <= stage.video.width()


# --- la chuleta de teclas se adapta (auditoria del pedido de Bruno) ----


def test_la_chuleta_se_ve_en_el_tamano_normal(qtbot):
    """Con la hoja de estilos puesta, la version que habia medía 290 px y
    en el hueco real caben 273: la chuleta que el mockup promete estuvo
    INVISIBLE desde que se construyo. Se descubrio al agregarle `↑↓` y
    `R` y preguntarse por que no aparecian."""
    stage = _stage_visible(qtbot)
    stage.set_range_pill(7.1, 212, 18.4, 29.97)
    qtbot.wait(1)

    assert not stage.keys_hint.isHidden()
    assert stage.keys_hint.geometry().right() <= stage.video.width()


def test_no_se_encima_con_la_pastilla_de_rango(qtbot):
    stage = _stage_visible(qtbot)
    stage.set_range_pill(7.1, 212, 18.4, 29.97)
    qtbot.wait(1)

    assert not stage.keys_hint.geometry().intersects(stage.range_pill.geometry())


def test_al_achicarse_se_acorta_en_vez_de_desaparecer(qtbot):
    stage = _stage_visible(qtbot)
    stage.set_range_pill(7.1, 212, 18.4, 29.97)
    qtbot.wait(1)
    largo = stage.keys_hint.text()

    stage.resize(416, 740)
    qtbot.wait(1)

    assert not stage.keys_hint.isHidden()
    assert len(stage.keys_hint.text()) < len(largo)


def test_lo_ultimo_que_sobrevive_son_las_teclas_menos_obvias(qtbot):
    """`esc` y `F` se adivinan; `↑↓` y `R` no. Cuando queda poco lugar,
    sobrevive lo que cuesta descubrir."""
    stage = _stage_visible(qtbot)
    stage.set_range_pill(7.1, 212, 18.4, 29.97)
    stage.resize(394, 700)
    qtbot.wait(1)

    assert "↑↓" in stage.keys_hint.text()
    assert "R inicio" in stage.keys_hint.text()
