"""El submenú «Cámara» del encabezado del bin, y el color de su marquita."""
from clasificador_video.camaras import DJI, OTRA, SONY
from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import _BinHeader


def _submenu_de_camara(cabecera):
    """Devuelve `(menu, submenu)`, y el menú de arriba HAY QUE SUJETARLO.

    Sin quedarse con él, Python lo recolecta al salir de aquí y sus acciones
    mueren con él («Internal C++ object already deleted»). En la app no pasa
    porque `_abrir_menu_en` lo guarda en `self._menu` -- ese es justo el
    comentario que ya está al tope de `construir_menu`.
    """
    menu = cabecera.construir_menu()
    for accion in menu.actions():
        if accion.text().startswith("Cámara"):
            return menu, accion.menu()
    return menu, None


def test_el_menu_del_bin_ofrece_las_tres_camaras(qtbot):
    cabecera = _BinHeader("Dron")
    qtbot.addWidget(cabecera)

    _menu, sub = _submenu_de_camara(cabecera)

    assert [a.text() for a in sub.actions()] == ["Sony", "DJI", "Otra"]


def test_la_camara_puesta_sale_palomeada(qtbot):
    cabecera = _BinHeader("Dron")
    qtbot.addWidget(cabecera)
    cabecera.set_camara(DJI)

    _menu, sub = _submenu_de_camara(cabecera)

    palomeadas = [a.text() for a in sub.actions() if a.isChecked()]
    assert palomeadas == ["DJI"]


def test_escoger_una_camara_lo_avisa(qtbot):
    cabecera = _BinHeader("Dron")
    qtbot.addWidget(cabecera)
    avisos = []
    cabecera.camara_changed.connect(lambda n, c: avisos.append((n, c)))

    _menu, sub = _submenu_de_camara(cabecera)
    [a for a in sub.actions() if a.text() == "Otra"][0].trigger()

    assert avisos == [("Dron", OTRA)]


def test_la_seccion_de_sueltos_no_ofrece_camara(qtbot):
    """«Sin bin» no es una cámara: es la vista de los clips que no son de
    nadie. Mismo criterio que renombrar y enlazar proxies, que tampoco
    aparecen ahí."""
    cabecera = _BinHeader("Sin bin", es_bin=False)
    qtbot.addWidget(cabecera)

    _menu, sub = _submenu_de_camara(cabecera)

    assert sub is None


def test_cada_camara_tiene_su_color():
    assert theme.camara_color(SONY) != theme.camara_color(DJI)
    assert theme.camara_color(DJI) != theme.camara_color(OTRA)


def test_una_camara_desconocida_no_truena():
    """El tema no puede reventar la hoja entera por un valor raro que se
    coló del autosave."""
    assert theme.camara_color("🐔") == theme.camara_color(SONY)


def test_dos_bins_de_la_misma_camara_se_ven_igual(qtbot):
    """Y está bien: en Premiere también van a salir del mismo color. Una
    app que muestra una diferencia que su destino no tiene, miente."""
    uno, otro = _BinHeader("Sony A"), _BinHeader("Sony B")
    qtbot.addWidget(uno)
    qtbot.addWidget(otro)

    uno.set_camara(SONY)
    otro.set_camara(SONY)

    assert uno.cam_mark.styleSheet() == otro.cam_mark.styleSheet()


def test_cambiarle_la_camara_le_cambia_el_color(qtbot):
    cabecera = _BinHeader("Dron")
    qtbot.addWidget(cabecera)

    cabecera.set_camara(SONY)
    con_sony = cabecera.cam_mark.styleSheet()
    cabecera.set_camara(DJI)

    assert cabecera.cam_mark.styleSheet() != con_sony


def test_la_seccion_de_sueltos_se_queda_neutra(qtbot):
    """«Sin bin» no es una cámara y no puede pintarse como una."""
    cabecera = _BinHeader("Sin bin", es_bin=False)
    qtbot.addWidget(cabecera)
    neutra = cabecera.cam_mark.styleSheet()

    cabecera.set_camara(DJI)

    assert cabecera.cam_mark.styleSheet() == neutra
