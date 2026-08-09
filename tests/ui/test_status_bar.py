from clasificador_video.ui import theme
from clasificador_video.ui.status_bar import StatusBar


def _bar(qtbot) -> StatusBar:
    bar = StatusBar()
    qtbot.addWidget(bar)
    return bar


def test_altura_fija_del_mockup(qtbot):
    assert _bar(qtbot).height() == theme.STATUSBAR_HEIGHT


def test_muestra_los_datos_tecnicos_del_clip(qtbot):
    bar = _bar(qtbot)
    bar.set_clip_info("C0087.MP4", (2160, 3840), 29.97, 90)
    texto = bar.clip_label.text()
    assert "C0087.MP4" in texto
    assert "2160×3840" in texto
    assert "29.97 fps" in texto
    assert "vertical" in texto


def test_reconoce_un_clip_horizontal(qtbot):
    bar = _bar(qtbot)
    bar.set_clip_info("C0001.MP4", (3840, 2160), 29.97, 0)
    assert "horizontal" in bar.clip_label.text()


def test_sin_clip_no_muestra_datos_tecnicos(qtbot):
    bar = _bar(qtbot)
    bar.set_clip_info(None, None, None, None)
    assert bar.clip_label.text() == ""


def test_aviso_de_sin_clasificar(qtbot):
    bar = _bar(qtbot)
    bar.set_unclassified(12)
    assert "12 sin clasificar" in bar.unclassified_label.text()


def test_sin_pendientes_el_aviso_se_vacia(qtbot):
    bar = _bar(qtbot)
    bar.set_unclassified(0)
    assert bar.unclassified_label.text() == ""


def test_muestra_la_ruta_del_volumen(qtbot):
    bar = _bar(qtbot)
    bar.set_volume("/Volumes/FX30/CasaLomas")
    assert bar.volume_label.text() == "/Volumes/FX30/CasaLomas"


def test_tiene_objectnames_para_el_tema(qtbot):
    bar = _bar(qtbot)
    assert bar.objectName() == "statusBar"
    assert bar.unclassified_label.objectName() == "unclassifiedBadge"


# --- F5: el aviso es el botón de «sigue trabajando» -------------------------


def test_el_aviso_de_sin_clasificar_es_clickeable(qtbot):
    """DECISIONES.md: la advertencia es, literalmente, el boton de «segui
    trabajando»."""
    barra = _bar(qtbot)
    barra.set_unclassified(12)
    assert "12 sin clasificar" in barra.unclassified_label.text()
    assert "click para filtrarlos" in barra.unclassified_label.text()
    with qtbot.waitSignal(barra.unclassified_clicked):
        barra.unclassified_label.click()


def test_sin_pendientes_el_aviso_desaparece(qtbot):
    barra = _bar(qtbot)
    barra.set_unclassified(0)
    assert barra.unclassified_label.text() == ""
    assert barra.unclassified_label.isHidden()


# --- contador de proxies (F9) ------------------------------------------


def test_el_contador_dice_cuantos_clips_tienen_proxy(qtbot):
    bar = _bar(qtbot)
    bar.set_proxies(118, 128, "720p")
    assert bar.proxy_label.text() == "proxies 720p · 118/128"
    assert not bar.proxy_label.isHidden()


def test_sin_ningun_proxy_el_contador_no_se_ve(qtbot):
    """Un `· 0/128` seria ruido en cada sesion de dron, que es la mitad
    de los shootings."""
    bar = _bar(qtbot)
    bar.set_proxies(0, 128, "720p")
    assert bar.proxy_label.isHidden()


def test_con_resoluciones_distintas_se_cae_la_palabra(qtbot):
    """Dos camaras con perfiles de proxy distintos: mejor callar la
    resolucion que decir una que no es la de todos."""
    bar = _bar(qtbot)
    bar.set_proxies(118, 128, "")
    assert bar.proxy_label.text() == "proxies · 118/128"


def test_sin_clips_el_contador_no_se_ve(qtbot):
    bar = _bar(qtbot)
    bar.set_proxies(0, 0, "")
    assert bar.proxy_label.isHidden()
