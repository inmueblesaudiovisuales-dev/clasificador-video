"""Tablero de siete columnas para armar la guía de edición."""
from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget)

from clasificador_video import guia as logica

MIME_PASO = "application/x-clasificador-guia-paso"


class _Chip(QWidget):
    quitar_pedido = Signal()
    def __init__(self, cuarto, quitable=False, parent=None):
        super().__init__(parent); self.cuarto = cuarto; self._inicio = None
        # Puestos por `_CajaDePasos._repintar` solo para los chips que
        # viven en una columna real. `None` para los de la franja: la
        # franja nunca pierde un cuarto por arrastrarlo (es el origen,
        # no un destino), así que nunca hay de dónde quitarlo.
        self.caja_de_origen = None
        self.indice_de_origen = None
        self.setObjectName("guiaChip"); fila = QHBoxLayout(self)
        fila.setContentsMargins(8, 5, 8, 5); fila.addWidget(QLabel(cuarto), 1)
        if quitable:
            boton = QPushButton("✕"); boton.setFlat(True)
            boton.clicked.connect(self.quitar_pedido); fila.addWidget(boton)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self._inicio = e.position().toPoint()
        super().mousePressEvent(e)
    def mouseReleaseEvent(self, e):
        # Sin esto, soltar el botón sin haber cruzado el umbral de
        # arrastre dejaba `_inicio` viejo -- y el siguiente click, aunque
        # empezara en otro lugar, medía el arrastre desde el punto de la
        # vez anterior (mismo cuidado que ya tiene `RoomRail` en el rail).
        self._inicio = None
        super().mouseReleaseEvent(e)
    def mouseMoveEvent(self, e):
        if self._inicio is None or not e.buttons() & Qt.MouseButton.LeftButton: return
        if (e.position().toPoint()-self._inicio).manhattanLength() < QApplication.startDragDistance(): return
        self._inicio = None
        self._arrastrar()
    def _arrastrar(self):
        """Arma el QDrag y decide, con el resultado, si hay que
        desaparecer de la columna de origen.

        Antes esto siempre usaba `CopyAction`: arrastrar de una columna a
        otra dejaba el cuarto en LAS DOS, y `orden_final()` lo mandaba dos
        veces a Premiere como si fueran pasos distintos. Ahora se ofrecen
        las dos acciones y se PIDE `MoveAction` por default -- si el
        destino la acepta (cualquier columna real), es que de verdad hubo
        un movimiento y el origen se vacía; si se suelta sobre la franja
        (que ignora el soltar) o fuera de cualquier caja, el resultado no
        es `MoveAction` y el cuarto se queda donde estaba.
        """
        mime = QMimeData(); mime.setData(MIME_PASO, self.cuarto.encode())
        drag = QDrag(self); drag.setMimeData(mime); drag.setPixmap(self.grab())
        resultado = drag.exec(
            Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
            Qt.DropAction.MoveAction,
        )
        if resultado == Qt.DropAction.MoveAction and self.caja_de_origen is not None:
            self.caja_de_origen.quitar(self.indice_de_origen)


class _CajaDePasos(QWidget):
    cambio = Signal()
    def __init__(self, es_franja=False, parent=None):
        super().__init__(parent); self.es_franja = es_franja; self._orden = []
        self.setAcceptDrops(True); self._layout = QHBoxLayout(self) if es_franja else QVBoxLayout(self)
        if es_franja: self._layout.addStretch(1)
    def cuartos(self): return list(self._orden)
    def poner(self, cuartos): self._orden = list(cuartos); self._repintar()
    def agregar(self, cuarto): self._orden.append(cuarto); self._repintar()
    def quitar(self, i):
        if 0 <= i < len(self._orden): del self._orden[i]; self._repintar(); self.cambio.emit()
    def _repintar(self):
        while self._layout.count() > (1 if self.es_franja else 0):
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        for i, cuarto in enumerate(self._orden):
            chip = _Chip(cuarto, not self.es_franja)
            if not self.es_franja:
                chip.caja_de_origen = self
                chip.indice_de_origen = i
                chip.quitar_pedido.connect(lambda i=i: self.quitar(i))
            if self.es_franja: self._layout.insertWidget(self._layout.count()-1, chip)
            else: self._layout.addWidget(chip)
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_PASO): e.acceptProposedAction()
    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_PASO): e.acceptProposedAction()
    def dropEvent(self, e):
        if not e.mimeData().hasFormat(MIME_PASO):
            return
        if self.es_franja:
            # La franja no es un destino real: soltar aquí no agrega nada,
            # y al NO aceptar `MoveAction` el chip tampoco desaparece de
            # la columna de donde vino (ver `_Chip._arrastrar`).
            e.ignore()
            return
        self.agregar(bytes(e.mimeData().data(MIME_PASO)).decode())
        self.cambio.emit()
        e.setDropAction(Qt.DropAction.MoveAction)
        e.accept()


class PantallaGuia(QWidget):
    clasificacion_pedida = Signal(); orden_aceptado = Signal(list); cerrada = Signal()
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("pantallaGuia"); self._cuartos_reales=[]; self._armando=False
        # `VideoWidget` es un QOpenGLWidget: Qt lo compone en una capa aparte
        # y `raise_()` NO alcanza para taparlo -- sin este atributo, la
        # pantalla se abre pero el video (o su fondo negro) se sigue viendo
        # encima de todo, y eso es lo que se veia como "un cuadro negro".
        # `WA_AlwaysStackOnTop` es el mecanismo que Qt da para overlays
        # sobre un QOpenGLWidget; sin el, ni el orden en el arbol de
        # widgets ni `raise_()` cambian nada.
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        raiz=QVBoxLayout(self); cab=QHBoxLayout(); cab.addWidget(QLabel("Guía de edición")); cab.addStretch()
        cerrar=QPushButton("Cerrar"); cerrar.clicked.connect(self.cerrada); cab.addWidget(cerrar); raiz.addLayout(cab)
        self.aviso_label=QLabel(); self.aviso_label.setWordWrap(True); raiz.addWidget(self.aviso_label)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); tablero=QWidget(); fila=QHBoxLayout(tablero); self.columnas={}
        for dato in logica.COLUMNAS:
            envoltura=QWidget(); col=QVBoxLayout(envoltura); col.addWidget(QLabel(dato.titulo))
            caja=_CajaDePasos(); caja.cambio.connect(self._refrescar_aviso); col.addWidget(caja,1)
            self.columnas[dato.id]=caja; fila.addWidget(envoltura,1)
        scroll.setWidget(tablero); raiz.addWidget(scroll,1)
        raiz.addWidget(QLabel("Tus cuartos — arrastra uno a una columna")); self.franja=_CajaDePasos(True); raiz.addWidget(self.franja)
        botones=QHBoxLayout(); self.clasificar_de_nuevo_button=QPushButton("Clasificar de nuevo")
        self.clasificar_de_nuevo_button.clicked.connect(self._pedir); botones.addWidget(self.clasificar_de_nuevo_button); botones.addStretch()
        self.usar_button=QPushButton("Usar este orden"); self.usar_button.clicked.connect(lambda: self.orden_aceptado.emit(self.orden_final()))
        botones.addWidget(self.usar_button); raiz.addLayout(botones)
    def poner_cuartos_reales(self, cuartos):
        self._cuartos_reales=list(cuartos); self.franja.poner(cuartos)
        for caja in self.columnas.values(): caja.poner([])
        self._refrescar_aviso()
    def mostrar_clasificacion(self, clasificacion):
        self._armando=False
        for caja in self.columnas.values(): caja.poner([])
        if not clasificacion.ok:
            self.aviso_label.setText(f"No se pudo clasificar ({clasificacion.error}). Acomoda los cuartos a mano."); return
        for cuarto, columna in clasificacion.columna_de.items():
            if columna in self.columnas: self.columnas[columna].agregar(cuarto)
        if clasificacion.inventados:
            # Se marca en vez de callarse: un cuarto que el modelo se
            # inventó no es tuyo, y perderlo en silencio es justo el modo
            # de falla que este aviso existe para evitar.
            self.aviso_label.setText(
                "El modelo mencionó algo que no es tuyo: "
                + ", ".join(clasificacion.inventados) + "."
            )
            return
        self._refrescar_aviso()
    def mostrar_guia_aceptada(self, lista):
        self.columnas[logica.COLUMNAS[0].id].poner([r.cuarto for r in lista]); self._refrescar_aviso()
    def armando(self): self._armando=True; self.aviso_label.setText("Clasificando…")
    def agregar_a_columna(self, columna, cuarto): self.columnas[columna].agregar(cuarto); self._refrescar_aviso()
    def orden_final(self):
        return [cuarto for dato in logica.COLUMNAS for cuarto in self.columnas[dato.id].cuartos()]
    def _refrescar_aviso(self):
        faltan=logica.cuartos_sin_usar(self._cuartos_reales, self.orden_final())
        self.aviso_label.setText(("Sin usar: " + ", ".join(faltan) + ".") if faltan else "")
    def _pedir(self):
        if self.orden_final() and QMessageBox.question(self,"Clasificar de nuevo","Vas a perder cómo acomodaste los cuartos. ¿Clasificar de nuevo?") != QMessageBox.StandardButton.Yes: return
        self.clasificacion_pedida.emit()
    def keyPressEvent(self, e):
        if e.key()==Qt.Key.Key_Escape and not self._armando: self.cerrada.emit(); return
        super().keyPressEvent(e)
