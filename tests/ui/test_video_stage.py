from PySide6.QtCore import Qt

from clasificador_video.ui import theme
from clasificador_video.ui.video_stage import VideoStage


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
