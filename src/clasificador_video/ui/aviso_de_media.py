# src/clasificador_video/ui/aviso_de_media.py
"""La barra que dice qué material no se encuentra, y deja ir a buscarlo.

Barra y **no** un modal a propósito (spec §8): abrir el proyecto en otra
computadora y no encontrar nada es lo normal, no una excepción, y con un
cartel encima Bruno no podría ver su proyecto mientras decide.

Un renglón por bin, que es la unidad que él reconoce. Y **un renglón por
cada final**: reconectados, sin confirmar y no encontrados no se mezclan en
una sola frase. «No lo encontré» cuando en realidad apareció un archivo con
ese nombre que no es el mismo —la segunda tarjeta de la Sony, que vuelve a
numerar desde `C0001.MP4`— sería mentirle sobre lo que pasó.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

# Los tres tonos del renglón. Van como texto y no como color porque el color
# lo pone la hoja de estilos (Candado 1: ningún color se declara fuera de
# `theme.py`); aquí solo se dice qué clase de noticia es.
TONO_FALTA = "falta"        # no aparece nada
TONO_ALERTA = "alerta"      # apareció algo que no se pudo enganchar
TONO_OK = "ok"              # reconectado

# Qué hace el botón del renglón. Son acciones distintas sobre carpetas
# distintas: el original y su proxy no viven en el mismo lado.
ACCION_MEDIA = "media"
ACCION_PROXIES = "proxies"


@dataclass
class Renglon:
    """Lo que se le dice a Bruno de un bin, y qué botón le toca.

    `quiere_buscar` y `boton` son cosas distintas a propósito: el renglón
    dice si le SERVIRÍA un «Buscar…», y quien arma la barra decide cuál se
    lo lleva — uno solo por bin, porque dos idénticos hacen lo mismo.
    """
    bin: str
    texto: str
    tono: str = TONO_FALTA
    quiere_buscar: bool = False
    boton: str | None = None
    accion: str = ACCION_MEDIA
    # apagado mientras una busqueda esta corriendo: recorrer una tarjeta de
    # 128 GB tarda, y durante ese rato el boton no puede prometer nada.
    boton_activo: bool = True


class AvisoDeMedia(QWidget):
    """La barra completa.

    NO decide si se ve: esa regla vive entera en la ventana, que es la única
    que sabe si está el modo solo video. Con la regla partida en dos, poner
    renglones podía hacerla reaparecer encima del video a pantalla completa.
    """

    buscar_pedido = Signal(str, str)   # nombre del bin, acción

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("avisoDeMedia")
        self._renglones: list[Renglon] = []
        self._filas: list[QWidget] = []
        caja = QVBoxLayout(self)
        caja.setContentsMargins(12, 8, 12, 8)
        caja.setSpacing(4)
        self._caja = caja
        self.hide()

    def poner(self, renglones: list[Renglon]) -> None:
        """Reemplaza lo que dice la barra. No la muestra ni la esconde."""
        self._limpiar()
        self._renglones = list(renglones)
        for renglon in self._renglones:
            fila = self._fila(renglon)
            self._caja.addWidget(fila)
            # `show()` a mano: meter un widget en un layout NO lo muestra
            # ahora, lo deja para la siguiente vuelta del bucle de eventos.
            # Y hay un momento en que esa vuelta no llega: mientras se busca
            # en la carpeta, que corre en el hilo de la interfaz. Ahí la
            # barra se dibujaba en blanco --el hueco estaba, el texto no--,
            # que es peor que no decir nada: parece que la app tronó.
            # Con el padre escondido esto no lo muestra: `isVisible()` sigue
            # siendo falso hasta que el padre aparezca.
            fila.show()

    def tiene_avisos(self) -> bool:
        """Si hay algo que decir. Lo usa `solo video` para no volver a
        mostrar una barra vacía al salir del modo."""
        return bool(self._renglones)

    def text(self) -> str:
        """Todo lo que la barra dice, en un solo texto.

        Existe para poder preguntarle a la barra qué está diciendo sin
        recorrerle los hijos -- y porque lo que importa comprobar es el
        mensaje, no de cuántas etiquetas está hecho.
        """
        return "\n".join(f"{r.bin} — {r.texto}" for r in self._renglones)

    def _fila(self, renglon: Renglon) -> QWidget:
        fila = QWidget(self)
        fila.setObjectName("avisoFila")
        caja = QHBoxLayout(fila)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(8)

        nombre = QLabel(renglon.bin, fila)
        nombre.setObjectName("avisoBin")
        caja.addWidget(nombre)

        texto = QLabel(renglon.texto, fila)
        texto.setObjectName("avisoTexto")
        # el tono viaja como propiedad de Qt para que lo pinte la hoja de
        # estilos, que es donde viven los colores
        texto.setProperty("tono", renglon.tono)
        # que el texto largo del caso «no coincide» se acomode en vez de
        # empujar la ventana a lo ancho
        texto.setWordWrap(True)
        caja.addWidget(texto, stretch=1)

        if renglon.boton:
            boton = QPushButton(renglon.boton, fila)
            boton.setObjectName("avisoBuscar")
            boton.setEnabled(renglon.boton_activo)
            boton.clicked.connect(
                lambda _=False, n=renglon.bin, a=renglon.accion:
                    self.buscar_pedido.emit(n, a)
            )
            caja.addWidget(boton)
        self._filas.append(fila)
        return fila

    def _limpiar(self) -> None:
        """Desecha las filas viejas.

        `hide()` + `setParent(None)` + `deleteLater()`, los tres: soltar el
        padre a secas deja el widget vivo y a la vista como una ventana
        suelta hasta que el recolector pase.
        """
        for fila in self._filas:
            fila.hide()
            fila.setParent(None)
            fila.deleteLater()
        self._filas = []
        self._renglones = []
