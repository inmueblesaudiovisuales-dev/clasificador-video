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


def test_sin_ningun_proxy_lo_dice_con_palabras(qtbot):
    """Antes se escondia, con el argumento de que un `· 0/128` era ruido.
    Bruno demostro que el silencio era peor: «no entiendo como poner
    proxies». Un `0/128` sigue siendo ruido, pero `sin proxies` informa."""
    bar = _bar(qtbot)
    bar.set_proxies(0, 128, "720p")
    assert bar.proxy_label.text() == "sin proxies"


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


def test_el_volumen_lleva_su_tamano(qtbot):
    """El mockup escribe `/Volumes/FX30/CasaLomas · 214 GB`."""
    bar = _bar(qtbot)
    bar.set_volume("/Volumes/FX30/CasaLomas", 214)
    assert bar.volume_label.text() == "/Volumes/FX30/CasaLomas · 214 GB"


def test_sin_saber_el_tamano_va_solo_la_ruta(qtbot):
    """Un volumen de red o una carpeta que ya no esta: no se inventa un
    `0 GB`, que ademas se leeria como disco lleno."""
    bar = _bar(qtbot)
    bar.set_volume("/Volumes/FX30/CasaLomas")
    assert bar.volume_label.text() == "/Volumes/FX30/CasaLomas"


# --- resumen del shooting en modo hoja (F10) ---------------------------


def test_en_modo_hoja_la_barra_resume_el_shooting(qtbot):
    """El mockup cambia el texto al entrar a la hoja: sin un clip en
    pantalla, los datos de «el clip actual» no vienen al caso."""
    bar = _bar(qtbot)
    bar.set_resumen(128, verticales=74, horizontales=54)
    assert bar.clip_label.text() == "128 clips · 74 verticales · 54 horizontales"


def test_el_resumen_sin_tamanos_conocidos_dice_solo_cuantos_clips(qtbot):
    """Sesion restaurada de disco: no se volvio a correr ffprobe, asi que
    no se sabe la orientacion de ninguno. `0 verticales · 0 horizontales`
    seria una respuesta falsa a una pregunta que no se puede contestar."""
    bar = _bar(qtbot)
    bar.set_resumen(128, verticales=0, horizontales=0)
    assert bar.clip_label.text() == "128 clips"


def test_sin_clips_el_resumen_queda_vacio(qtbot):
    bar = _bar(qtbot)
    bar.set_resumen(0, verticales=0, horizontales=0)
    assert bar.clip_label.text() == ""


def test_sin_proxies_lo_dice_en_vez_de_callarse(qtbot):
    """«No entiendo como poner proxies»: la app los busca sola, pero si no
    encontraba ninguno no decia NADA, asi que no habia forma de saber si
    los estaba buscando siquiera."""
    bar = _bar(qtbot)
    bar.set_proxies(0, 128, "")
    assert bar.proxy_label.text() == "sin proxies"
    assert not bar.proxy_label.isHidden()
    assert "S03" in bar.proxy_label.toolTip()


def test_el_aviso_de_sin_proxies_se_va_cuando_aparece_uno(qtbot):
    bar = _bar(qtbot)
    bar.set_proxies(0, 128, "")
    bar.set_proxies(1, 128, "720p")
    assert bar.proxy_label.text() == "proxies 720p · 1/128"


def test_sin_clips_no_dice_nada_de_proxies(qtbot):
    bar = _bar(qtbot)
    bar.set_proxies(0, 0, "")
    assert bar.proxy_label.isHidden()
