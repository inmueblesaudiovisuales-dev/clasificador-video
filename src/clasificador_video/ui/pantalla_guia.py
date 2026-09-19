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
        self.setObjectName("guiaChip"); fila = QHBoxLayout(self)
        fila.setContentsMargins(8, 5, 8, 5); fila.addWidget(QLabel(cuarto), 1)
        if quitable:
            boton = QPushButton("✕"); boton.setFlat(True)
            boton.clicked.connect(self.quitar_pedido); fila.addWidget(boton)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self._inicio = e.position().toPoint()
        super().mousePressEvent(e)
    def mouseMoveEvent(self, e):
        if self._inicio is None or not e.buttons() & Qt.MouseButton.LeftButton: return
        if (e.position().toPoint()-self._inicio).manhattanLength() < QApplication.startDragDistance(): return
        mime = QMimeData(); mime.setData(MIME_PASO, self.cuarto.encode())
        drag = QDrag(self); drag.setMimeData(mime); drag.setPixmap(self.grab())
        self._inicio = None; drag.exec(Qt.DropAction.CopyAction)


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
            if not self.es_franja: chip.quitar_pedido.connect(lambda i=i: self.quitar(i))
            if self.es_franja: self._layout.insertWidget(self._layout.count()-1, chip)
            else: self._layout.addWidget(chip)
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_PASO): e.acceptProposedAction()
    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_PASO): e.acceptProposedAction()
    def dropEvent(self, e):
        if e.mimeData().hasFormat(MIME_PASO) and not self.es_franja:
            self.agregar(bytes(e.mimeData().data(MIME_PASO)).decode()); self.cambio.emit()
        e.acceptProposedAction()


class PantallaGuia(QWidget):
    clasificacion_pedida = Signal(); orden_aceptado = Signal(list); cerrada = Signal()
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("pantallaGuia"); self._cuartos_reales=[]; self._armando=False
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
