"""Pantalla de revisión de un proyecto importado a la vez."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from clasificador_video_portafolio import portafolio as pf
from clasificador_video_portafolio import rodaje_completo
from clasificador_video.thumbnails import cache_dir_for, default_cache_root, extract_thumbnail, extract_thumbnail_strip


ESTILO_REVISAR = """
QWidget#pantallaRevisar { background: #0a0b0d; color: #e6e9ee; }
QWidget#pantallaRevisar QLabel { color: #e6e9ee; }
QListWidget#railProyectos { background: #101216; border: 0; border-right: 1px solid #262b33; padding: 7px; color: #ccd2db; }
QListWidget#railProyectos::item { border-radius: 6px; padding: 9px 7px; margin-bottom: 3px; }
QListWidget#railProyectos::item:selected { background: #1d2128; }
QLabel#tituloRail { color: #626b78; font-size: 10px; font-weight: 600; letter-spacing: 1px; }
QPushButton#filtro, QPushButton#rodajeCompleto { background: #16191e; border: 1px solid #262b33; border-radius: 6px; color: #9aa3b0; padding: 5px 9px; font-size: 11px; }
QPushButton#filtro:checked { background: #1d2128; color: #e6e9ee; }
QPushButton#rodajeCompleto { color: #e6e9ee; }
QComboBox { background: #16191e; border: 1px solid #262b33; border-radius: 5px; color: #e6e9ee; padding: 4px 8px; min-width: 110px; }
QComboBox QAbstractItemView { background: #16191e; color: #e6e9ee; selection-background-color: #1d2128; }
QScrollArea { border: 0; background: #101216; }
QWidget#hoja { background: #101216; }
QFrame#tarjetaClip { background: #1d2128; border: 1px solid #262b33; border-radius: 6px; }
QFrame#tarjetaClip[actual="true"] { border: 2px solid #e8a33d; }
QLabel#nombreClip { color: #9aa3b0; font-size: 10px; padding: 4px; }
QLabel#estadoClip { border-radius: 4px; font-size: 10px; font-weight: 700; padding: 3px 5px; }
QLabel#estadoClip[estado="elegida"] { background: #55c08a; color: #07130d; }
QLabel#estadoClip[estado="descartada"] { background: #d4696c; color: #1b0708; }
QLabel#estadoClip[estado="sin_decidir"] { background: #262b33; color: #9aa3b0; }
"""


class TarjetaClip(QFrame):
    """Tarjeta compacta; sus colores dejan visible el estado de la escalera."""

    def __init__(self, clip: pf.ClipDelPortafolio, parent=None):
        super().__init__(parent)
        self.clip = clip
        # La tira se genera al hacer scrub; por ahora solo se carga portada.
        self.cantidad_miniaturas = 3 if clip.fuera_de_secuencia else 12
        self.tira_scrub: list[Path] = []
        self.setObjectName("tarjetaClip")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumWidth(145)
        self.setFixedHeight(112)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 7, 7, 7)
        fila = QHBoxLayout()
        self.estado = QLabel()
        self.estado.setObjectName("estadoClip")
        fila.addWidget(self.estado)
        fila.addStretch()
        layout.addLayout(fila)
        self.miniatura = QLabel()
        self.miniatura.setFixedHeight(72)
        self.miniatura.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.miniatura)
        self.nombre = QLabel(clip.ruta_origen.name)
        self.nombre.setObjectName("nombreClip")
        self.nombre.setToolTip(str(clip.ruta_origen))
        layout.addWidget(self.nombre)
        self.actualizar()

    def cargar_miniatura(self) -> None:
        """Carga una portada reducida solo cuando esta tarjeta ya es visible."""
        if self.miniatura.pixmap() or not self.clip.ruta_origen.exists():
            return
        try:
            ruta = extract_thumbnail(
                self.clip.ruta_origen, 0.5,
                cache_dir_for(self.clip.ruta_origen, default_cache_root(), economico=True),
                economico=True,
            )
        except RuntimeError:
            return
        pixmap = QPixmap(str(ruta))
        if not pixmap.isNull():
            self.miniatura.setPixmap(pixmap.scaled(128, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def cargar_tira_scrub(self) -> None:
        """Pide la tira una sola vez, al entrar al scrub y solo si es visible."""
        if self.tira_scrub or not self.isVisible() or not self.clip.ruta_origen.exists():
            return
        try:
            cuadros = extract_thumbnail_strip(
                self.clip.ruta_origen, 1.0, self.cantidad_miniaturas,
                cache_dir_for(self.clip.ruta_origen, default_cache_root(), economico=True),
                economico=True,
            )
        except RuntimeError:
            return
        # La portada que ya vio Bruno conserva el primer lugar de la tira.
        self.tira_scrub = cuadros

    def enterEvent(self, event):  # noqa: N802 -- override de Qt
        self.cargar_tira_scrub()
        super().enterEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 -- override de Qt
        self.cargar_tira_scrub()
        super().mouseMoveEvent(event)

    def actualizar(self) -> None:
        etiquetas = {"descartada": "↓ Descartada", "sin_decidir": "— Sin decidir", "elegida": "↑ Elegida"}
        self.estado.setText(etiquetas[self.clip.estado])
        self.estado.setProperty("estado", self.clip.estado)
        self.estado.style().unpolish(self.estado)
        self.estado.style().polish(self.estado)


class PantallaRevisar(QWidget):
    """Rail de proyectos y hoja de clips, sin mezclar proyectos."""

    def __init__(self, portafolio: pf.Portafolio, elegir_carpeta: Callable[[], Path | None] | None = None, ruta_portafolio: Path | None = None, parent=None):
        super().__init__(parent)
        self.portafolio = portafolio
        self.proyecto_actual: pf.ProyectoImportado | None = None
        self.tarjetas: list[TarjetaClip] = []
        self._filtro = "todos"
        self._elegir_carpeta = elegir_carpeta or self._pedir_carpeta
        self.ruta_portafolio = ruta_portafolio
        self.setObjectName("pantallaRevisar")
        self.setStyleSheet(ESTILO_REVISAR)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        rail = QWidget()
        rail.setFixedWidth(230)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(12, 11, 7, 8)
        titulo = QLabel("PROYECTOS")
        titulo.setObjectName("tituloRail")
        rail_layout.addWidget(titulo)
        self.rail = QListWidget()
        self.rail.setObjectName("railProyectos")
        self.rail.currentRowChanged.connect(self._seleccionar_rail)
        rail_layout.addWidget(self.rail, 1)
        layout.addWidget(rail)

        contenido = QVBoxLayout()
        contenido.setContentsMargins(13, 10, 13, 10)
        cabecera = QHBoxLayout()
        self.titulo_proyecto = QLabel("Selecciona un proyecto")
        cabecera.addWidget(self.titulo_proyecto)
        self.selector_categoria = QComboBox()
        self.selector_categoria.setEditable(True)
        # `currentTextChanged` se dispara por cada letra y guardaba prefijos.
        # La categoría nueva solo entra al confirmar la edición o elegirla.
        self.selector_categoria.lineEdit().editingFinished.connect(
            lambda: self.asignar_categoria_actual(self.selector_categoria.currentText())
        )
        self.selector_categoria.textActivated.connect(self.asignar_categoria_actual)
        cabecera.addWidget(self.selector_categoria)
        cabecera.addStretch()
        self.boton_rodaje = QPushButton("Ver el rodaje completo")
        self.boton_rodaje.setObjectName("rodajeCompleto")
        self.boton_rodaje.clicked.connect(self.ver_rodaje_completo)
        cabecera.addWidget(self.boton_rodaje)
        contenido.addLayout(cabecera)
        filtros = QHBoxLayout()
        self.botones_filtro: dict[str, QPushButton] = {}
        for clave, texto in (("todos", "Todos"), ("sin_decidir", "Sin decidir"), ("elegida", "Elegidas"), ("descartada", "Descartadas")):
            boton = QPushButton(texto)
            boton.setObjectName("filtro")
            boton.setCheckable(True)
            boton.setChecked(clave == "todos")
            boton.clicked.connect(lambda _, c=clave: self._cambiar_filtro(c))
            self.botones_filtro[clave] = boton
            filtros.addWidget(boton)
        filtros.addStretch()
        contenido.addLayout(filtros)
        self.hoja = QWidget()
        self.hoja.setObjectName("hoja")
        self._grid = QGridLayout(self.hoja)
        self._grid.setContentsMargins(0, 4, 0, 0)
        self._grid.setSpacing(10)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.hoja)
        contenido.addWidget(scroll, 1)
        self.scroll = scroll
        scroll.verticalScrollBar().valueChanged.connect(self._cargar_miniaturas_visibles)
        layout.addLayout(contenido, 1)
        self.actualizar_rail()

    def actualizar_rail(self) -> None:
        self.rail.blockSignals(True)
        self.rail.clear()
        for proyecto in self.portafolio.proyectos:
            elegidas = sum(clip.estado == "elegida" for clip in proyecto.clips)
            categoria = f" · {proyecto.categoria}" if proyecto.categoria else ""
            item = QListWidgetItem(f"{proyecto.nombre}\n{len(proyecto.clips)} clips · {elegidas} elegidas{categoria}")
            item.setForeground(QColor(self.color_de_proyecto(proyecto)))
            if not self.proyecto_disponible(proyecto):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(Qt.GlobalColor.darkGray)
            self.rail.addItem(item)
        self.rail.blockSignals(False)

    @staticmethod
    def color_de_proyecto(proyecto: pf.ProyectoImportado) -> str:
        """Color determinista por nombre, para que el rail no cambie al recargar."""
        paleta = ("#c0885a", "#6d8ca8", "#8b7ca8", "#4f9a8e", "#7e9e5e")
        return paleta[int(hashlib.sha1(proyecto.nombre.encode()).hexdigest(), 16) % len(paleta)]

    def proyecto_disponible(self, proyecto: pf.ProyectoImportado) -> bool:
        # Un solo clip existente basta: permite avanzar proyecto por proyecto
        # aunque un SSD tenga una vinculación parcial; es fácil de endurecer después.
        return any(clip.ruta_origen.exists() for clip in proyecto.clips)

    def _seleccionar_rail(self, indice: int) -> None:
        if indice >= 0:
            self.mostrar_proyecto(self.portafolio.proyectos[indice])

    def mostrar_proyecto(self, proyecto: pf.ProyectoImportado) -> None:
        self.proyecto_actual = proyecto
        self.titulo_proyecto.setText(proyecto.nombre)
        self.selector_categoria.blockSignals(True)
        self.selector_categoria.clear()
        self.selector_categoria.addItems(self.portafolio.categorias_conocidas)
        self.selector_categoria.setCurrentText(proyecto.categoria or "")
        self.selector_categoria.blockSignals(False)
        self._reconstruir_hoja()

    def asignar_categoria_actual(self, categoria: str) -> None:
        if self.proyecto_actual is not None and categoria:
            self.portafolio.asignar_categoria(self.proyecto_actual, categoria)
            self.actualizar_rail()
            self._guardar()

    def _reconstruir_hoja(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tarjetas = []
        if self.proyecto_actual is None:
            return
        clips = [clip for clip in self.proyecto_actual.clips if self._filtro == "todos" or clip.estado == self._filtro]
        for indice, clip in enumerate(clips):
            tarjeta = TarjetaClip(clip)
            tarjeta.installEventFilter(self)
            self.tarjetas.append(tarjeta)
            self._grid.addWidget(tarjeta, indice // 5, indice % 5)
        if self.tarjetas:
            self.tarjetas[0].setProperty("actual", True)
            self.tarjetas[0].setFocus()
        QTimer.singleShot(0, self._cargar_miniaturas_visibles)

    def _cargar_miniaturas_visibles(self) -> None:
        """No genera portadas fuera del viewport: el rodaje completo puede ser grande."""
        viewport = self.scroll.viewport().rect()
        for tarjeta in self.tarjetas:
            posicion = tarjeta.mapTo(self.scroll.viewport(), tarjeta.rect().topLeft())
            if viewport.intersects(tarjeta.rect().translated(posicion)):
                tarjeta.cargar_miniatura()

    def _cambiar_filtro(self, filtro: str) -> None:
        self._filtro = filtro
        for clave, boton in self.botones_filtro.items():
            boton.setChecked(clave == filtro)
        self._reconstruir_hoja()

    def _tarjeta_actual(self) -> TarjetaClip | None:
        return next((tarjeta for tarjeta in self.tarjetas if tarjeta.hasFocus()), self.tarjetas[0] if self.tarjetas else None)

    def elegir_actual(self) -> None:
        tarjeta = self._tarjeta_actual()
        if tarjeta is not None:
            pf.subir(tarjeta.clip)
            self._reconstruir_hoja()
            self.actualizar_rail()
            self._guardar()

    def descartar_actual(self) -> None:
        tarjeta = self._tarjeta_actual()
        if tarjeta is not None:
            pf.bajar(tarjeta.clip)
            self._reconstruir_hoja()
            self.actualizar_rail()
            self._guardar()

    def ver_rodaje_completo(self) -> None:
        if self.proyecto_actual is None:
            return
        carpeta = rodaje_completo.deducir_carpeta([clip.ruta_origen for clip in self.proyecto_actual.clips])
        if carpeta is None or not carpeta.is_dir():
            carpeta = self._elegir_carpeta()
            if carpeta is None:
                return
        conocidas = {clip.ruta_origen for clip in self.proyecto_actual.clips}
        for ruta in rodaje_completo.listar_videos(carpeta):
            if ruta not in conocidas:
                self.proyecto_actual.clips.append(pf.ClipDelPortafolio(ruta, self.proyecto_actual.nombre, fuera_de_secuencia=True))
        self._reconstruir_hoja()
        self.actualizar_rail()
        self._guardar()

    def _guardar(self) -> None:
        if self.ruta_portafolio is not None:
            self.portafolio.guardar(self.ruta_portafolio)

    def _pedir_carpeta(self) -> Path | None:
        ruta = QFileDialog.getExistingDirectory(self, "Ubica la carpeta del rodaje")
        return Path(ruta) if ruta else None

    def keyPressEvent(self, event):  # noqa: N802 -- override de Qt
        if event.key() == Qt.Key.Key_Up:
            self.elegir_actual()
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self.descartar_actual()
            event.accept()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, watched, event):  # noqa: N802 -- override de Qt
        if watched in self.tarjetas and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self.elegir_actual()
                return True
            if event.key() == Qt.Key.Key_Down:
                self.descartar_actual()
                return True
            if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                indice = self.tarjetas.index(watched)
                paso = -1 if event.key() == Qt.Key.Key_Left else 1
                destino = max(0, min(len(self.tarjetas) - 1, indice + paso))
                for tarjeta in self.tarjetas:
                    tarjeta.setProperty("actual", False)
                    tarjeta.style().unpolish(tarjeta)
                    tarjeta.style().polish(tarjeta)
                self.tarjetas[destino].setProperty("actual", True)
                self.tarjetas[destino].style().unpolish(self.tarjetas[destino])
                self.tarjetas[destino].style().polish(self.tarjetas[destino])
                self.tarjetas[destino].setFocus()
                return True
        return super().eventFilter(watched, event)
