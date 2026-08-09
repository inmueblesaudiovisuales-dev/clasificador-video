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


def test_el_boton_de_proxies_emite_su_senal(qtbot):
    """Ocupa el lugar del de «Cuartos», que solo movia el foco y desde
    afuera parecia no hacer nada."""
    bar = _bar(qtbot)
    with qtbot.waitSignal(bar.proxies_requested):
        bar.proxies_button.click()


def test_los_botones_no_roban_el_foco(qtbot):
    """Con un boton enfocable en el camino, Espacio lo activaria en vez de
    reproducir el clip."""
    bar = _bar(qtbot)
    for boton in (bar.export_button, bar.proxies_button):
        assert boton.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_tiene_objectnames_para_el_tema(qtbot):
    bar = _bar(qtbot)
    assert bar.objectName() == "titleBar"
    assert bar.export_button.objectName() == "exportButton"


# --- switch Clip | Hoja (F10) ------------------------------------------


def test_el_switch_arranca_en_clip(qtbot):
    bar = _bar(qtbot)
    assert bar.mode_switch.current() == "Clip"


def test_la_tecla_se_dibuja_del_lado_al_que_te_lleva(qtbot):
    """Detalle del mockup que vale la pena copiar: el `⇥` se dibuja sobre
    la opcion INACTIVA, porque anuncia a donde vas, no donde estas."""
    bar = _bar(qtbot)
    textos = [b.text() for b in bar.mode_switch.buttons]
    assert textos == ["Clip", "Hoja  ⇥"]

    bar.set_modo_hoja(True)
    textos = [b.text() for b in bar.mode_switch.buttons]
    assert textos == ["Clip  ⇥", "Hoja"]


def test_set_modo_hoja_marca_la_opcion_correcta(qtbot):
    bar = _bar(qtbot)
    bar.set_modo_hoja(True)
    assert bar.mode_switch.current().startswith("Hoja")
    bar.set_modo_hoja(False)
    assert bar.mode_switch.current().startswith("Clip")


def test_clickear_el_switch_pide_cambiar_de_modo(qtbot):
    bar = _bar(qtbot)
    pedidos = []
    bar.mode_toggled.connect(lambda: pedidos.append(1))
    bar.mode_switch.buttons[1].click()
    assert pedidos == [1]


def test_clickear_el_modo_en_el_que_ya_estas_no_hace_nada(qtbot):
    """Si emitiera igual, el ⇥ y el click se contradirian: clickear `Clip`
    estando en clip te sacaria a la hoja."""
    bar = _bar(qtbot)
    pedidos = []
    bar.mode_toggled.connect(lambda: pedidos.append(1))
    bar.mode_switch.buttons[0].click()
    assert pedidos == []


def test_los_botones_del_switch_no_toman_el_foco(qtbot):
    """O el espacio activa el boton enfocado en vez de reproducir."""
    bar = _bar(qtbot)
    for boton in bar.mode_switch.buttons:
        assert boton.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_el_icono_de_la_app_lleva_el_triangulo_de_play(qtbot):
    """El mockup dibuja un play adentro del cuadro ambar; la app tenia el
    cuadro liso. Va como pixmap pintado y no como caracter `▶`: un glifo
    de fuente no cae igual en todas las maquinas."""
    bar = _bar(qtbot)
    pixmap = bar.mark.pixmap()
    assert pixmap is not None and not pixmap.isNull()
    assert pixmap.deviceIndependentSize().toSize() == bar.mark.size()
