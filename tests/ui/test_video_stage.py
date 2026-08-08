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


def test_la_scrub_bar_queda_pegada_al_borde_inferior(qtbot):
    stage = _stage_visible(qtbot)
    stage.resize(529, 940)
    qtbot.wait(50)
    borde = stage.scrub_bar.y() + stage.scrub_bar.height()
    assert stage.video.height() - borde == theme.OVERLAY_MARGIN


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
