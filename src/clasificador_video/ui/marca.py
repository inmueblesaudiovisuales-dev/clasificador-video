# src/clasificador_video/ui/marca.py
"""La marca de Clipify: un cuadro de video con una palomita.

Un solo lugar dibuja la marca, y de aqui salen los dos sitios donde se ve:

  - `glifo()`  -> la marquita de la barra de titulo, sin fondo (el ambar y
                  el radio los pone el QSS, `QLabel#appMark`).
  - `icono()`  -> el icono del Finder y del Dock, que si trae su ambar
                  porque ahi no hay QSS que se lo ponga.

Estan juntos a proposito. Antes el triangulo de play vivia adentro de
`title_bar.py` y la app empacada no tenia icono; el dia que existieran los
dos por separado, se irian pareciendo cada vez menos hasta que la marquita
de la ventana y el icono del Dock fueran dos dibujos distintos de la misma
app. El `.icns` se genera de aqui (`scripts/hacer_icono.py`), no de un
archivo dibujado a mano que nadie volveria a tocar.

Todo se traza sobre un lienzo imaginario de 64x64 y se escala al tamaño
pedido. Las proporciones son las del diseño aprobado el 2026-08-27
(`docs/superpowers/specs/2026-08-27-clipify-marca-y-nombre-design.md`).
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from clasificador_video.ui import theme

# El lienzo de referencia. Cambiar este numero no cambia el dibujo: todas
# las medidas de abajo son relativas a el.
LIENZO = 64.0

# El cuadro de video y la palomita, en coordenadas del lienzo.
MARCO = QRectF(14, 16, 36, 32)
MARCO_RADIO = 6.0
MARCO_TRAZO = 5.0
PALOMITA = (QPointF(22, 33), QPointF(29, 40), QPointF(44, 24))
PALOMITA_TRAZO = 5.5

# Cuanto del lienzo ocupa la pastilla ambar del icono. macOS dibuja sombra
# y separacion alrededor de cada icono del Dock, y un icono a sangre se ve
# mas grande que todos sus vecinos aunque mida igual.
ICONO_OCUPACION = 0.82
# Radio de la esquina, como fraccion del lado de la pastilla. El de macOS
# ronda esta proporcion; mas chico se ve cuadrado al lado de los demas.
ICONO_RADIO = 0.225

ESCALA_RETINA = 2  # para que no se vea dentado en pantalla retina


def _lienzo(tamano: QSize) -> QPixmap:
    """Un pixmap transparente del tamaño pedido, listo para retina.

    Mide en PUNTOS lo que se pidio aunque por dentro tenga el doble de
    pixeles: si devolviera el tamaño en pixeles, el `QLabel` lo dibujaria
    al doble de grande.
    """
    pixmap = QPixmap(tamano * ESCALA_RETINA)
    pixmap.setDevicePixelRatio(ESCALA_RETINA)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


def _pintar_glifo(pintor: QPainter, lado: float, color: QColor) -> None:
    """El cuadro de video y la palomita, centrados en un cuadrado de `lado`.

    Recibe el pintor y no crea el suyo para que el icono pueda dibujar
    primero su pastilla ambar y encima esto, sin pixmaps intermedios.
    """
    k = lado / LIENZO
    pluma = QPen(color)
    pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
    pluma.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pintor.setBrush(Qt.BrushStyle.NoBrush)

    pluma.setWidthF(MARCO_TRAZO * k)
    pintor.setPen(pluma)
    marco = QRectF(MARCO.x() * k, MARCO.y() * k,
                   MARCO.width() * k, MARCO.height() * k)
    pintor.drawRoundedRect(marco, MARCO_RADIO * k, MARCO_RADIO * k)

    pluma.setWidthF(PALOMITA_TRAZO * k)
    pintor.setPen(pluma)
    trazo = QPainterPath(QPointF(PALOMITA[0].x() * k, PALOMITA[0].y() * k))
    for punto in PALOMITA[1:]:
        trazo.lineTo(punto.x() * k, punto.y() * k)
    pintor.drawPath(trazo)


def glifo(tamano: QSize, color: str = theme.BG_APP) -> QPixmap:
    """La marca para la barra de titulo: solo el dibujo, sin fondo.

    Pintado y no escrito ni cargado de un PNG. Un caracter de fuente cambia
    de forma, de peso y de alineacion vertical segun la maquina; un PNG a
    17 px se ve suave en una pantalla y dentado en otra segun el
    `devicePixelRatio`. Y este es el primer pixel que se ve al abrir la app.
    """
    pixmap = _lienzo(tamano)
    pintor = QPainter(pixmap)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    _pintar_glifo(pintor, min(tamano.width(), tamano.height()), QColor(color))
    pintor.end()
    return pixmap


def icono(lado: int) -> QPixmap:
    """El icono de la app, con su pastilla ambar y su margen.

    Devuelve un pixmap de `lado` x `lado` PIXELES --sin doblar por retina--
    porque quien lo consume es `iconutil`, que arma el `.icns` con archivos
    de tamaño exacto. La escala retina de macOS se resuelve metiendo al
    `.icns` los dos archivos, el de 32 y el de 64 con nombre `32x32@2x`.
    """
    pixmap = QPixmap(lado, lado)
    pixmap.setDevicePixelRatio(1)
    pixmap.fill(Qt.GlobalColor.transparent)

    pintor = QPainter(pixmap)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    pastilla_lado = lado * ICONO_OCUPACION
    margen = (lado - pastilla_lado) / 2
    pastilla = QRectF(margen, margen, pastilla_lado, pastilla_lado)

    degradado = QLinearGradient(pastilla.topLeft(), pastilla.bottomLeft())
    degradado.setColorAt(0.0, QColor(theme.ICON_AMBER_TOP))
    degradado.setColorAt(1.0, QColor(theme.ICON_AMBER_BOTTOM))
    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(degradado)
    radio = pastilla_lado * ICONO_RADIO
    pintor.drawRoundedRect(pastilla, radio, radio)

    # El glifo se dibuja centrado DENTRO de la pastilla, no del lienzo: si
    # se centrara en el lienzo se saldria por abajo del ambar en cuanto el
    # margen crezca.
    pintor.translate(pastilla.topLeft())
    _pintar_glifo(pintor, pastilla_lado, QColor(theme.BG_APP))
    pintor.end()
    return pixmap
