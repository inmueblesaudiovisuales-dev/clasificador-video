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
    bar.set_project("Casa Lomas", 128, bins=2)
    assert bar.project_label.text() == "Casa Lomas"
    assert "128 clips" in bar.subtitle_label.text()


def test_el_subtitulo_dice_cuantos_bins_y_no_una_camara_inventada(qtbot):
    """Decia «Sony FX30» escrito a mano, de cuando todo el material era de
    esa camara. Con los bins eso paso a ser mentira: lo decia igual con
    material del dron, y hasta con el proyecto vacio."""
    bar = _bar(qtbot)
    bar.set_project("Casa Lomas", 128, bins=2)

    assert "Sony" not in bar.subtitle_label.text()
    assert "2 bins" in bar.subtitle_label.text()


def test_con_un_solo_bin_no_dice_1_bins(qtbot):
    bar = _bar(qtbot)
    bar.set_project("Casa Lomas", 12, bins=1)

    assert "1 bin" in bar.subtitle_label.text()
    assert "1 bins" not in bar.subtitle_label.text()


def test_sin_material_el_subtitulo_no_habla_de_bins(qtbot):
    """Es la pantalla inicial de la app. «0 clips · 0 bins» no le dice nada
    a nadie; el cartel del centro es el que explica que hacer."""
    bar = _bar(qtbot)
    bar.set_project("Casa Lomas", 0, bins=0)

    assert bar.subtitle_label.text() == "sin material"


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


def test_la_barra_dice_cuando_no_se_pudo_guardar(qtbot):
    """El indicador decia «Guardado hace 3 s» toda la sesión aunque la
    escritura estuviera fallando. Con la sesión escondida —un archivo en la
    carpeta del usuario, siempre escribible— casi nunca pasaba; ahora el
    archivo lo elige Bruno y puede estar en un disco que se desconecta."""
    barra = TitleBar()
    qtbot.addWidget(barra)
    barra.set_saved_seconds(3)

    barra.set_no_guardado("Read-only file system")

    assert barra.saved_label.text() == "No se pudo guardar"
    assert not barra.saved_led.isHidden()
    assert "Read-only file system" in barra.saved_label.toolTip()


def test_un_guardado_bueno_borra_el_aviso_de_falla(qtbot):
    barra = TitleBar()
    qtbot.addWidget(barra)
    barra.set_no_guardado("se desconectó")

    barra.set_saved_seconds(0)

    assert barra.saved_label.text() == "Guardado hace 0 s"
    assert barra.saved_label.toolTip() == ""


def test_el_boton_ancho_se_VE_prendido(qtbot):
    """Un interruptor que funciona pero no se nota es un control que miente.

    Con una hoja de estilos puesta, Qt deja de dibujar el hundido nativo del
    sistema: `setCheckable(True)` seguia guardando el estado, pero el boton
    se veia identico prendido que apagado. Medido pixel a pixel el
    2026-08-18, los dos daban el mismo `#1d2128`.

    Se comparan los PIXELES y no la hoja de estilos: lo que hay que
    defender es que se vea distinto, no como se escribio.
    """
    from PySide6.QtWidgets import QApplication

    QApplication.instance().setStyleSheet(theme.build_stylesheet())
    bar = _bar(qtbot)
    bar.resize(900, theme.TITLEBAR_HEIGHT)
    bar.show()
    qtbot.waitExposed(bar)

    apagado = bar.visor_button.grab().toImage()
    bar.set_modo_horizontal(True)
    prendido = bar.visor_button.grab().toImage()

    assert prendido != apagado


def test_el_boton_ancho_no_se_deja_apretar_en_la_hoja(qtbot):
    """El modo ancho solo habla de lo que pasa en modo clip (spec §3), y la
    app abre en la hoja: ahi apretarlo no movia un pixel."""
    bar = _bar(qtbot)

    bar.set_modo_hoja(True)
    assert not bar.visor_button.isEnabled()

    bar.set_modo_hoja(False)
    assert bar.visor_button.isEnabled()
