"""La marca de Clipify: el cuadro de video con la palomita.

Se prueba lo que de verdad se puede romper sin que nadie lo note: que el
glifo tenga tinta —un `QPainter` mal armado devuelve un pixmap vacío sin
quejarse—, que respete el `devicePixelRatio` para no verse dentado en
retina, y que a 16 px la palomita siga siendo palomita y no una mancha.
"""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor

from clasificador_video.ui import marca


def _cuantos_pixeles_con_tinta(pixmap) -> int:
    imagen = pixmap.toImage()
    return sum(
        1
        for y in range(imagen.height())
        for x in range(imagen.width())
        if imagen.pixelColor(x, y).alpha() > 0
    )


def test_el_glifo_pinta_algo(qapp):
    """Un `QPainter` mal armado devuelve un pixmap transparente y no avisa."""
    pixmap = marca.glifo(QSize(64, 64))

    assert not pixmap.isNull()
    assert _cuantos_pixeles_con_tinta(pixmap) > 0


def test_el_glifo_deja_transparente_el_fondo(qapp):
    """El ámbar de la barra de título lo pone el QSS (`QLabel#appMark`), no
    el pixmap. Si el glifo trajera fondo propio, se encimarían dos ámbares
    con radios distintos y se vería un borde."""
    pixmap = marca.glifo(QSize(64, 64))
    imagen = pixmap.toImage()

    assert imagen.pixelColor(0, 0).alpha() == 0


def test_el_glifo_respeta_el_tamano_pedido_en_puntos(qapp):
    """El pixmap se pinta al doble para retina, pero mide lo que se pidió:
    si devolviera el tamaño en pixeles, el `QLabel` lo dibujaría al doble."""
    pixmap = marca.glifo(QSize(17, 17))

    assert pixmap.deviceIndependentSize().toSize() == QSize(17, 17)
    assert pixmap.devicePixelRatio() > 1


def test_el_icono_trae_el_ambar_y_el_glifo(qapp):
    """El icono del Finder sí trae fondo: ahí no hay QSS que se lo ponga."""
    pixmap = marca.icono(512)
    imagen = pixmap.toImage()

    assert imagen.pixelColor(256, 256).alpha() == 255
    colores = {imagen.pixelColor(x, y).name()
               for y in range(0, 512, 4) for x in range(0, 512, 4)}
    # el ámbar del fondo y el casi-negro del glifo, los dos presentes
    assert any(QColor(c).red() > 180 and QColor(c).blue() < 140 for c in colores)
    assert any(QColor(c).lightness() < 40 for c in colores)


def test_el_icono_deja_margen_en_las_esquinas(qapp):
    """macOS espera que el arte no llegue al borde del lienzo: el sistema
    dibuja sombra y separación alrededor, y un icono a sangre se ve más
    grande que todos los demás del Dock."""
    imagen = marca.icono(512).toImage()

    assert imagen.pixelColor(2, 2).alpha() == 0
    assert imagen.pixelColor(509, 509).alpha() == 0


def test_a_16_px_la_palomita_todavia_se_lee(qapp):
    """El tamaño más chico que pide macOS. Si el trazo se adelgaza con el
    lienzo, a 16 px el glifo se borra y queda un cuadro ámbar liso -- que es
    justo el icono anterior, sin marca."""
    imagen = marca.icono(16).toImage()
    oscuros = sum(
        1
        for y in range(16)
        for x in range(16)
        if imagen.pixelColor(x, y).alpha() > 0
        and imagen.pixelColor(x, y).lightness() < 90
    )

    assert oscuros >= 12
