"""Pantalla de revisión de un proyecto importado a la vez."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
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
        layout.addStretch()
        self.nombre = QLabel(clip.ruta_origen.name)
        self.nombre.setObjectName("nombreClip")
        self.nombre.setToolTip(str(clip.ruta_origen))
        layout.addWidget(self.nombre)
        self.actualizar()

    def actualizar(self) -> None:
        etiquetas = {"descartada": "↓ Descartada", "sin_decidir": "— Sin decidir", "elegida": "↑ Elegida"}
        self.estado.setText(etiquetas[self.clip.estado])
        self.estado.setProperty("estado", self.clip.estado)
        self.estado.style().unpolish(self.estado)
        self.estado.style().polish(self.estado)


class PantallaRevisar(QWidget):
    """Rail de proyectos y hoja de clips, sin mezclar proyectos."""

    def __init__(self, portafolio: pf.Portafolio, parent=None):
        super().__init__(parent)
        self.portafolio = portafolio
        self.proyecto_actual: pf.ProyectoImportado | None = None
        self.tarjetas: list[TarjetaClip] = []
        self._filtro = "todos"
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
        layout.addLayout(contenido, 1)
        self.actualizar_rail()

    def actualizar_rail(self) -> None:
        self.rail.blockSignals(True)
        self.rail.clear()
        for proyecto in self.portafolio.proyectos:
            elegidas = sum(clip.estado == "elegida" for clip in proyecto.clips)
            categoria = f" · {proyecto.categoria}" if proyecto.categoria else ""
            item = QListWidgetItem(f"{proyecto.nombre}\n{len(proyecto.clips)} clips · {elegidas} elegidas{categoria}")
            if not self.proyecto_disponible(proyecto):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(Qt.GlobalColor.darkGray)
            self.rail.addItem(item)
        self.rail.blockSignals(False)

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
        self._reconstruir_hoja()

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
            self.tarjetas[0].setFocus()

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
            tarjeta.actualizar()
            self.actualizar_rail()

    def descartar_actual(self) -> None:
        tarjeta = self._tarjeta_actual()
        if tarjeta is not None:
            pf.bajar(tarjeta.clip)
            tarjeta.actualizar()
            self.actualizar_rail()

    def ver_rodaje_completo(self) -> None:
        if self.proyecto_actual is None:
            return
        carpeta = rodaje_completo.deducir_carpeta([clip.ruta_origen for clip in self.proyecto_actual.clips])
        if carpeta is None:
            # Elegir manualmente la carpeta corresponde a la interfaz posterior;
            # aquí no se adivina una ruta para no incorporar clips equivocados.
            return
        conocidas = {clip.ruta_origen for clip in self.proyecto_actual.clips}
        for ruta in rodaje_completo.listar_videos(carpeta):
            if ruta not in conocidas:
                self.proyecto_actual.clips.append(pf.ClipDelPortafolio(ruta, self.proyecto_actual.nombre, fuera_de_secuencia=True))
        self._reconstruir_hoja()
        self.actualizar_rail()

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
        return super().eventFilter(watched, event)
