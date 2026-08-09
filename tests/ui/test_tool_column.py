from clasificador_video.ui import theme
from clasificador_video.ui.tool_column import ToolColumn


def _col(qtbot) -> ToolColumn:
    col = ToolColumn()
    qtbot.addWidget(col)
    return col


def test_ancho_fijo_del_mockup(qtbot):
    assert _col(qtbot).width() == theme.TOOLCOL_WIDTH


def test_arranca_todo_apagado(qtbot):
    col = _col(qtbot)
    for ind in (col.in_indicator, col.out_indicator, col.pick_indicator, col.reject_indicator):
        assert not ind.is_on()


def test_marcar_in_enciende_solo_in(qtbot):
    col = _col(qtbot)
    col.set_range(in_frame=120, out_frame=None)
    assert col.in_indicator.is_on()
    assert not col.out_indicator.is_on()


def test_marcar_ambos_enciende_los_dos(qtbot):
    col = _col(qtbot)
    col.set_range(in_frame=120, out_frame=340)
    assert col.in_indicator.is_on() and col.out_indicator.is_on()


def test_pick_enciende_solo_pick(qtbot):
    col = _col(qtbot)
    col.set_flag("pick")
    assert col.pick_indicator.is_on()
    assert not col.reject_indicator.is_on()


def test_reject_enciende_solo_reject(qtbot):
    col = _col(qtbot)
    col.set_flag("reject")
    assert col.reject_indicator.is_on()
    assert not col.pick_indicator.is_on()


def test_neutral_apaga_los_dos(qtbot):
    col = _col(qtbot)
    col.set_flag("pick")
    col.set_flag("none")
    assert not col.pick_indicator.is_on() and not col.reject_indicator.is_on()


def test_el_encendido_es_propiedad_dinamica_no_estilo_pegado(qtbot):
    """El color sale del QSS con tokens: un hexadecimal pegado aca seria
    justo lo que el Candado 1 prohibe."""
    col = _col(qtbot)
    col.set_flag("pick")
    assert col.pick_indicator.property("on") is True
    assert col.pick_indicator.styleSheet() == ""


def test_cada_indicador_declara_su_canal_semantico(qtbot):
    col = _col(qtbot)
    assert col.in_indicator.property("canal") == "rango"
    assert col.pick_indicator.property("canal") == "pick"
    assert col.reject_indicator.property("canal") == "reject"


# --- F4: el boton de deshacer ------------------------------------------------


def test_la_columna_tiene_boton_de_deshacer(qtbot):
    col = _col(qtbot)
    assert col.undo_button.key.text() == "⌘Z"


def test_el_boton_de_deshacer_emite_su_senal(qtbot):
    col = _col(qtbot)
    col.set_can_undo(True)
    with qtbot.waitSignal(col.undo_requested):
        col.undo_button.click()


def test_deshacer_se_apaga_cuando_no_hay_nada_que_deshacer(qtbot):
    """Un boton que no hace nada y no lo dice es peor que no tenerlo."""
    col = _col(qtbot)
    assert not col.undo_button.isEnabled()   # al abrir no hay nada
    col.set_can_undo(True)
    assert col.undo_button.isEnabled()
    col.set_can_undo(False)
    assert not col.undo_button.isEnabled()


def test_el_boton_no_se_roba_el_foco(qtbot):
    """Con foco, la barra espaciadora activaria el boton en vez de
    reproducir el video."""
    from PySide6.QtCore import Qt
    assert _col(qtbot).undo_button.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_deshacer_es_un_boton_y_no_un_indicador(qtbot):
    """Desviacion consciente del resto de la columna: los demas reflejan el
    estado del clip, este ES una accion."""
    from PySide6.QtWidgets import QAbstractButton
    assert isinstance(_col(qtbot).undo_button, QAbstractButton)


def test_la_columna_recuerda_que_el_espacio_reproduce(qtbot):
    """El `.toolhint` del mockup, al pie de la columna. Es la unica pista de
    que la barra espaciadora hace algo: el resto de la columna son estados del
    clip con su tecla al lado, y `espacio` no tiene indicador propio."""
    columna = ToolColumn()
    qtbot.addWidget(columna)
    assert "espacio" in columna.play_hint.text()


def test_los_indicadores_muestran_su_caja(qtbot):
    """Bug real desde la F2: las QLabel de adentro heredaban el fondo opaco de
    la regla global `QWidget` y tapaban la caja del indicador --fondo, borde y
    esquinas redondeadas--, asi que la columna se veia como texto suelto en vez
    de los cuadros del mockup. Misma trampa que en el pie del video.

    Se mira el pixel del CENTRO, que es justo donde caen las etiquetas: en el
    borde la caja se veia igual y el test pasaria sin arreglar nada.
    """
    from PySide6.QtWidgets import QApplication
    from clasificador_video.ui import theme

    QApplication.instance().setStyleSheet(theme.build_stylesheet())
    columna = ToolColumn()
    qtbot.addWidget(columna)
    columna.resize(56, 420)
    columna.show()
    qtbot.waitExposed(columna)
    imagen = columna.star_indicator.grab().toImage()
    escala = imagen.width() / max(columna.star_indicator.width(), 1)
    centro = imagen.pixelColor(round(20 * escala), round(20 * escala)).name()
    assert centro != theme.BG_APP, "las etiquetas tapan la caja del indicador"
    assert centro == theme.BG_SURFACE_1


def test_un_destacado_enciende_tambien_el_pick(qtbot):
    """Es un pick reforzado, no otra cosa. Asi lo muestra el mockup, y hace
    visible lo que hace `P` sobre un destacado: se apaga la estrella y el pick
    se queda encendido."""
    columna = ToolColumn()
    qtbot.addWidget(columna)
    columna.set_flag("destacado")
    assert columna.star_indicator.is_on()
    assert columna.pick_indicator.is_on()
    columna.set_flag("pick")
    assert not columna.star_indicator.is_on()
    assert columna.pick_indicator.is_on()
