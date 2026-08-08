from PySide6.QtCore import Qt

from clasificador_video.ui import theme
from clasificador_video.ui.title_bar import TitleBar


def _bar(qtbot) -> TitleBar:
    bar = TitleBar()
    qtbot.addWidget(bar)
    return bar


def test_altura_fija_del_mockup(qtbot):
    """Cada pixel de alto de mas aca es un pixel de ancho de menos en un
    clip vertical."""
    assert _bar(qtbot).height() == theme.TITLEBAR_HEIGHT


def test_muestra_el_proyecto_y_el_conteo(qtbot):
    bar = _bar(qtbot)
    bar.set_project("Casa Lomas", 128)
    assert bar.project_label.text() == "Casa Lomas"
    assert "128 clips" in bar.subtitle_label.text()


def test_indicador_de_guardado_con_segundos(qtbot):
    bar = _bar(qtbot)
    bar.set_saved_seconds(12)
    assert bar.saved_label.text() == "Guardado hace 12 s"


def test_indicador_de_guardado_vacio_si_nunca_se_guardo(qtbot):
    bar = _bar(qtbot)
    bar.set_saved_seconds(None)
    assert bar.saved_label.text() == ""


def test_el_boton_de_exportar_emite_su_senal(qtbot):
    bar = _bar(qtbot)
    with qtbot.waitSignal(bar.export_requested):
        bar.export_button.click()


def test_el_boton_de_cuartos_emite_su_senal(qtbot):
    bar = _bar(qtbot)
    with qtbot.waitSignal(bar.rooms_requested):
        bar.rooms_button.click()


def test_los_botones_no_roban_el_foco(qtbot):
    """Con un boton enfocable en el camino, Espacio lo activaria en vez de
    reproducir el clip."""
    bar = _bar(qtbot)
    for boton in (bar.export_button, bar.rooms_button):
        assert boton.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_tiene_objectnames_para_el_tema(qtbot):
    bar = _bar(qtbot)
    assert bar.objectName() == "titleBar"
    assert bar.export_button.objectName() == "exportButton"
