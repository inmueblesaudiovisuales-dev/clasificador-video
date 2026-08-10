# src/clasificador_video/ui/pantalla_inicio.py
"""Lo primero que se ve al abrir: los proyectos de Bruno.

Antes la app caia directo en la hoja, con una sesion escondida que era
siempre la misma. Aqui se elige con cual trabajar --«eliges un proyecto pero
te enseña los ultimos, como Premiere»--, y por eso la lista pesa mas que los
dos botones que la acompañan.

Un proyecto que ya no esta en su lugar **no se poda**: se muestra apagado y
dice que no se encuentra. Que desaparezca sin explicacion es peor que verlo
gris, porque Bruno no puede distinguir «se perdio» de «falta conectar el
disco».
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.ui.text import ElidedLabel

FILA_ALTO = 54          # dos renglones cortos, del alto de una fila de lista
MARGEN = 28


def _etiqueta(object_name: str, apagado: bool) -> ElidedLabel:
    """Una etiqueta que se corta sola y no le pasa el clic al mouse.

    `Ignored` en horizontal no es un detalle: sin eso el `sizeHint` de la
    etiqueta es el del texto COMPLETO, y una carpeta con nombre largo
    empujaria el ancho de la ventana en vez de elidirse.
    """
    etiqueta = ElidedLabel()
    etiqueta.setObjectName(object_name)
    # el clic tiene que llegar al boton de abajo, que es lo que se puede
    # apretar: la fila entera es el control, no solo su borde
    etiqueta.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    etiqueta.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    # el color apagado viaja por propiedad y no por el `:disabled` del padre:
    # en QSS de Qt el pseudo-estado de un ancestro no llega a los hijos de
    # forma confiable, y la fila quedaria gris con el texto a plena luz
    etiqueta.setProperty("apagado", "true" if apagado else "false")
    return etiqueta


class _FilaReciente(QPushButton):
    """Un proyecto de la lista. Es un boton y no un renglon decorado porque
    la accion principal es abrirlo: que se vea clickeable no es adorno.

    El texto va en dos `ElidedLabel` adentro y no en el `text()` del boton
    porque un QPushButton no elide: la ruta larga estiraria la ventana.
    """

    quitar_pedido = Signal(Path)

    def __init__(self, entrada, parent=None):
        super().__init__(parent)
        self.setObjectName("filaReciente")
        self.entrada = entrada
        disponible = bool(entrada.disponible)
        self.setEnabled(disponible)
        self.setFixedHeight(FILA_ALTO)
        self.setCursor(Qt.PointingHandCursor)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(12, 8, 12, 8)
        caja.setSpacing(2)
        self.nombre = _etiqueta("recienteNombre", apagado=not disponible)
        self.nombre.setText(entrada.nombre)
        self.detalle = _etiqueta("recienteDetalle", apagado=not disponible)
        self.detalle.setText(self._detalle(entrada, disponible))
        caja.addWidget(self.nombre)
        caja.addWidget(self.detalle)
        # la ruta completa, para cuando la elidida no alcanza
        self.setToolTip(str(entrada.ruta))

    @staticmethod
    def _detalle(entrada, disponible: bool) -> str:
        carpeta = str(entrada.ruta.parent)
        if not disponible:
            # el «cuando» se cede a proposito: lo que hay que leer aqui es
            # que el archivo no esta, y tres datos en un renglon que ademas
            # se elide dejarian el importante fuera de cuadro
            return f"No se encuentra  ·  {carpeta}"
        cuando = entrada.cuando or "sin fecha"
        return f"{cuando}  ·  {carpeta}"

    def menu_de_contexto(self) -> QMenu:
        """El menu, armado pero sin mostrar.

        Separado de `contextMenuEvent` para poder probarlo sin abrir nada:
        mostrar menus en los tests es justo lo que cuelga bajo `offscreen`.
        """
        menu = QMenu(self)
        menu.addAction("Quitar de la lista").triggered.connect(
            lambda: self.quitar_pedido.emit(self.entrada.ruta)
        )
        return menu

    def contextMenuEvent(self, event):  # noqa: N802 -- override de Qt
        # popup, no exec: `exec` bloquea y cuelga la suite bajo offscreen
        self.menu_de_contexto().popup(event.globalPos())


class PantallaInicio(QWidget):
    """La lista de recientes, «Proyecto nuevo» y «Abrir otro…».

    No abre ni crea nada por su cuenta: avisa con una señal y quien la usa
    decide. Asi se puede probar sin tocar disco ni abrir selectores.
    """

    abrir_pedido = Signal(Path)
    nuevo_pedido = Signal()
    abrir_otro_pedido = Signal()
    quitar_pedido = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaInicio")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.filas: list[_FilaReciente] = []

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(MARGEN, MARGEN, MARGEN, MARGEN)
        raiz.setSpacing(14)

        self.titulo = QLabel("Tus proyectos")
        self.titulo.setObjectName("inicioTitulo")
        raiz.addWidget(self.titulo)

        self.lista_host = QWidget()
        self.lista = QVBoxLayout(self.lista_host)
        self.lista.setContentsMargins(0, 0, 0, 0)
        self.lista.setSpacing(6)
        raiz.addWidget(self.lista_host)

        # El estado vacio es un widget aparte y no una fila mas: se esconde y
        # se muestra, en vez de crearse y destruirse con cada `set_recientes`.
        self.vacio = QWidget()
        self.vacio.setObjectName("inicioVacio")
        vacio_caja = QVBoxLayout(self.vacio)
        vacio_caja.setContentsMargins(0, 10, 0, 10)
        vacio_caja.setSpacing(4)
        self.vacio_titulo = QLabel("Todavía no tienes proyectos")
        self.vacio_titulo.setObjectName("inicioVacioTitulo")
        self.vacio_hint = QLabel(
            "Crea uno nuevo y arrastra ahí tus carpetas de material."
        )
        self.vacio_hint.setObjectName("inicioVacioHint")
        vacio_caja.addWidget(self.vacio_titulo)
        vacio_caja.addWidget(self.vacio_hint)
        raiz.addWidget(self.vacio)

        raiz.addStretch(1)

        botones = QHBoxLayout()
        botones.setSpacing(8)
        self.boton_nuevo = QPushButton("Proyecto nuevo")
        self.boton_nuevo.setObjectName("inicioPrimario")
        self.boton_abrir_otro = QPushButton("Abrir otro…")
        self.boton_nuevo.clicked.connect(self.nuevo_pedido.emit)
        self.boton_abrir_otro.clicked.connect(self.abrir_otro_pedido.emit)
        botones.addWidget(self.boton_nuevo)
        botones.addWidget(self.boton_abrir_otro)
        botones.addStretch(1)
        raiz.addLayout(botones)

        self.set_recientes([])

    def set_recientes(self, entradas: list) -> None:
        for fila in self.filas:
            # los tres pasos, en este orden. `setParent(None)` a secas
            # destruye el objeto de C++ en el acto y ya costo varios
            # segfaults en este proyecto.
            fila.hide()
            fila.setParent(None)
            fila.deleteLater()
        self.filas = []
        for entrada in entradas:
            fila = _FilaReciente(entrada, self.lista_host)
            fila.clicked.connect(
                lambda _=False, e=entrada: self.abrir_pedido.emit(e.ruta)
            )
            fila.quitar_pedido.connect(self.quitar_pedido.emit)
            self.lista.addWidget(fila)
            self.filas.append(fila)
        self.lista_host.setVisible(bool(entradas))
        self.vacio.setVisible(not entradas)

    def nombres_visibles(self) -> list[str]:
        return [f.entrada.nombre for f in self.filas]
