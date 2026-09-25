"""Pantalla Armar y entregar: etiquetas de clip, filtro y generar el .prproj.

Universo: solo las Elegidas de todo el portafolio. Hasta la Fase 4.5 NO
crea alias de Finder -- usa las rutas que calcula `carpeta_de_portafolio`.
Spec: docs/superpowers/specs/2026-09-24-modo-portafolio-design.md.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
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

from clasificador_video_portafolio import generar_entrega
from clasificador_video_portafolio import portafolio as pf

ESTILO_ARMAR = """
QWidget#pantallaArmar { background: #0a0b0d; color: #e6e9ee; }
QWidget#pantallaArmar QLabel { color: #e6e9ee; }
QListWidget#railEtiquetas { background: #101216; border: 0; border-right: 1px solid #262b33; padding: 7px; color: #ccd2db; }
QListWidget#railEtiquetas::item { border-radius: 6px; padding: 9px 7px; margin-bottom: 3px; }
QListWidget#railEtiquetas::item:selected { background: #1d2128; }
QLabel#tituloRail { color: #626b78; font-size: 10px; font-weight: 600; letter-spacing: 1px; }
QPushButton { background: #16191e; border: 1px solid #262b33; border-radius: 6px; color: #9aa3b0; padding: 5px 9px; font-size: 11px; }
QPushButton#generar { background: #e6e9ee; color: #0b0d10; border-color: transparent; font-weight: 650; padding: 7px 14px; }
QScrollArea { border: 0; background: #101216; }
QWidget#hoja { background: #101216; }
QLabel#grupoProyecto { color: #e6e9ee; font-size: 11px; font-weight: 650; }
QLabel#grupoCategoria { color: #626b78; font-size: 9px; }
QFrame#tarjetaArmar { background: #1d2128; border: 1px solid #262b33; border-radius: 6px; }
QFrame#tarjetaArmar[actual="true"] { border: 2px solid #e8a33d; }
QLabel#nombreArmar { color: #9aa3b0; font-size: 10px; padding: 3px; }
QLabel#etiquetasArmar { color: #e8a33d; font-size: 9px; padding: 2px 4px; }
QLabel#estadoArmar { border-radius: 4px; font-size: 9px; font-weight: 700; padding: 2px 5px; background: #55c08a; color: #07130d; }
QLabel#barraEntrega { color: #9aa3b0; font-size: 11px; }
QLabel#resumenEntrega { color: #ccd2db; font-size: 12px; font-weight: 600; }
"""


class TarjetaArmar(QFrame):
    """Tarjeta de una Elegida; su estado ya es Elegida por definición."""

    def __init__(self, clip: pf.ClipDelPortafolio, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.setObjectName("tarjetaArmar")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumWidth(150)
        self.setFixedHeight(96)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 7, 7, 7)
        fila = QHBoxLayout()
        self.estado = QLabel("↑ Elegida")
        self.estado.setObjectName("estadoArmar")
        fila.addWidget(self.estado)
        fila.addStretch()
        layout.addLayout(fila)
        self.nombre = QLabel(clip.ruta_origen.name)
        self.nombre.setObjectName("nombreArmar")
        self.nombre.setToolTip(str(clip.ruta_origen))
        layout.addWidget(self.nombre)
        self.etiquetas = QLabel()
        self.etiquetas.setObjectName("etiquetasArmar")
        layout.addWidget(self.etiquetas)
        self.actualizar()

    def actualizar(self) -> None:
        self.etiquetas.setText(" · ".join(self.clip.etiquetas))


class PantallaArmarYEntregar(QWidget):
    """Rail de etiquetas y hoja agrupada por proyecto de origen."""

    def __init__(
        self,
        portafolio: pf.Portafolio,
        carpeta_portafolio: Path | None = None,
        ruta_portafolio: Path | None = None,
        elegir_carpeta: Callable[[], Path | None] | None = None,
        nombre_proyecto: str = "Mi Portafolio",
        parent=None,
    ):
        super().__init__(parent)
        self.portafolio = portafolio
        self.carpeta_portafolio = Path(carpeta_portafolio) if carpeta_portafolio else None
        self.ruta_portafolio = ruta_portafolio
        self.nombre_proyecto = nombre_proyecto
        self._elegir_carpeta = elegir_carpeta or self._pedir_carpeta
        self.etiquetas_activas: set[str] = set()
        self.tarjetas: list[TarjetaArmar] = []
        self.grupos: dict[str, list[TarjetaArmar]] = {}
        self.setObjectName("pantallaArmar")
        self.setStyleSheet(ESTILO_ARMAR)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        rail = QWidget()
        rail.setFixedWidth(230)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(12, 11, 7, 8)
        titulo = QLabel("ETIQUETAS")
        titulo.setObjectName("tituloRail")
        rail_layout.addWidget(titulo)
        self.rail = QListWidget()
        self.rail.setObjectName("railEtiquetas")
        self.rail.itemChanged.connect(self._cambiar_filtro_desde_item)
        rail_layout.addWidget(self.rail, 1)
        layout.addWidget(rail)

        contenido = QVBoxLayout()
        contenido.setContentsMargins(13, 10, 13, 10)
        self.resumen_arriba = QLabel()
        self.resumen_arriba.setObjectName("resumenEntrega")
        contenido.addWidget(self.resumen_arriba)

        carpeta_fila = QHBoxLayout()
        self.etiqueta_carpeta = QLabel("Carpeta de portafolio sin elegir")
        carpeta_fila.addWidget(self.etiqueta_carpeta)
        carpeta_fila.addStretch()
        self.boton_carpeta = QPushButton("Cambiar…")
        self.boton_carpeta.clicked.connect(self.cambiar_carpeta)
        carpeta_fila.addWidget(self.boton_carpeta)
        contenido.addLayout(carpeta_fila)

        self.hoja = QWidget()
        self.hoja.setObjectName("hoja")
        self._contenedor = QVBoxLayout(self.hoja)
        self._contenedor.setContentsMargins(0, 4, 0, 0)
        self._contenedor.setSpacing(14)
        self._contenedor.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.hoja)
        contenido.addWidget(scroll, 1)
        layout.addLayout(contenido, 1)

        barra = QFrame()
        barra_fila = QHBoxLayout(barra)
        barra_fila.setContentsMargins(13, 8, 13, 8)
        self.texto_barra = QLabel()
        self.texto_barra.setObjectName("barraEntrega")
        barra_fila.addWidget(self.texto_barra, 1)
        self.boton_generar = QPushButton("Generar .prproj")
        self.boton_generar.setObjectName("generar")
        self.boton_generar.clicked.connect(self.generar)
        barra_fila.addWidget(self.boton_generar)
        contenido.addWidget(barra)

        self.refrescar()

    # -- datos ------------------------------------------------------------

    def etiquetas_disponibles(self) -> list[str]:
        etiquetas = {etiqueta for clip in self.portafolio.todas_las_elegidas()
                     for etiqueta in clip.etiquetas}
        return sorted(etiquetas)

    def clips_filtrados(self) -> list[pf.ClipDelPortafolio]:
        return self.portafolio.elegidas_con_etiquetas(self.etiquetas_activas)

    def categoria_de(self, proyecto: str) -> str | None:
        return next(
            (p.categoria for p in self.portafolio.proyectos if p.nombre == proyecto),
            None,
        )

    def resumen(self) -> str:
        clips = self.clips_filtrados()
        proyectos = len({clip.proyecto for clip in clips})
        total = len(self.portafolio.todas_las_elegidas())
        if self.etiquetas_activas:
            etiquetas = " + ".join(sorted(self.etiquetas_activas))
            return (f"{len(clips)} clips con estas etiquetas ({etiquetas}), "
                    f"de {proyectos} proyectos · de {total} elegidas en total")
        return f"{total} elegidas · {proyectos} proyectos de origen"

    # -- interacción ------------------------------------------------------

    def refrescar(self) -> None:
        """Reconstruye rail, hoja y barra. NO crea alias de Finder."""
        self._reconstruir_rail()
        self._reconstruir_hoja()
        self.resumen_arriba.setText(self.resumen())
        if self.carpeta_portafolio is not None:
            self.etiqueta_carpeta.setText(str(self.carpeta_portafolio))
        else:
            self.etiqueta_carpeta.setText("Carpeta de portafolio sin elegir")
        self.texto_barra.setText(
            f"Se guarda como {generar_entrega.nombre_de_archivo(self.nombre_proyecto)}")

    def alternar_filtro(self, etiqueta: str) -> None:
        if etiqueta in self.etiquetas_activas:
            self.etiquetas_activas.discard(etiqueta)
        else:
            self.etiquetas_activas.add(etiqueta)
        self.refrescar()

    def alternar_etiqueta_actual(self, etiqueta: str) -> None:
        tarjeta = self._tarjeta_actual()
        if tarjeta is None or not etiqueta:
            return
        pf.alternar_etiqueta(tarjeta.clip, etiqueta)
        self.refrescar()
        self._guardar()

    def cambiar_carpeta(self) -> None:
        elegida = self._elegir_carpeta()
        if elegida:
            self.carpeta_portafolio = Path(elegida)
            self.refrescar()

    def generar(self) -> Path | None:
        clips = self.clips_filtrados()
        if not clips:
            return None
        if self.carpeta_portafolio is None:
            self.cambiar_carpeta()
            if self.carpeta_portafolio is None:
                return None
        self.carpeta_portafolio.mkdir(parents=True, exist_ok=True)
        categorias = {p.nombre: p.categoria for p in self.portafolio.proyectos}
        return generar_entrega.generar(
            clips, categorias, self.carpeta_portafolio,
            proyecto=self.nombre_proyecto)

    # -- construcción -----------------------------------------------------

    def _reconstruir_rail(self) -> None:
        self.rail.blockSignals(True)
        self.rail.clear()
        elegidas = self.portafolio.todas_las_elegidas()
        for etiqueta in self.etiquetas_disponibles():
            cuantas = sum(etiqueta in clip.etiquetas for clip in elegidas)
            item = QListWidgetItem(f"{etiqueta}  ·  {cuantas}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if etiqueta in self.etiquetas_activas
                else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, etiqueta)
            self.rail.addItem(item)
        self.rail.blockSignals(False)

    def _reconstruir_hoja(self) -> None:
        while self._contenedor.count():
            item = self._contenedor.takeAt(0)
            if (widget := item.widget()) is not None:
                widget.deleteLater()
        self.tarjetas = []
        self.grupos = {}
        for clip in self.clips_filtrados():
            self.grupos.setdefault(clip.proyecto, [])
        for proyecto, _ in self.grupos.items():
            encabezado = QWidget()
            fila = QHBoxLayout(encabezado)
            fila.setContentsMargins(0, 0, 0, 0)
            nombre = QLabel(proyecto)
            nombre.setObjectName("grupoProyecto")
            fila.addWidget(nombre)
            categoria = self.categoria_de(proyecto)
            if categoria is not None:
                chip = QLabel(categoria)
                chip.setObjectName("grupoCategoria")
                fila.addWidget(chip)
            fila.addStretch()
            self._contenedor.addWidget(encabezado)

            grid = QGridLayout()
            grid.setSpacing(10)
            grid.setAlignment(Qt.AlignmentFlag.AlignLeft)
            for indice, clip in enumerate(
                    c for c in self.clips_filtrados() if c.proyecto == proyecto):
                tarjeta = TarjetaArmar(clip)
                tarjeta.installEventFilter(self)
                self.tarjetas.append(tarjeta)
                self.grupos[proyecto].append(tarjeta)
                grid.addWidget(tarjeta, indice // 5, indice % 5)
            self._contenedor.addLayout(grid)
        if self.tarjetas:
            self.tarjetas[0].setProperty("actual", True)
            self.tarjetas[0].setFocus()

    # -- internos ---------------------------------------------------------

    def _tarjeta_actual(self) -> TarjetaArmar | None:
        return next(
            (tarjeta for tarjeta in self.tarjetas if tarjeta.hasFocus()),
            self.tarjetas[0] if self.tarjetas else None,
        )

    def _mover_foco(self, paso: int) -> None:
        if not self.tarjetas:
            return
        actual = self._tarjeta_actual()
        indice = self.tarjetas.index(actual) if actual is not None else 0
        destino = max(0, min(len(self.tarjetas) - 1, indice + paso))
        for tarjeta in self.tarjetas:
            tarjeta.setProperty("actual", False)
            tarjeta.style().unpolish(tarjeta)
            tarjeta.style().polish(tarjeta)
        self.tarjetas[destino].setProperty("actual", True)
        self.tarjetas[destino].style().unpolish(self.tarjetas[destino])
        self.tarjetas[destino].style().polish(self.tarjetas[destino])
        self.tarjetas[destino].setFocus()

    def _etiqueta_por_numero(self, tecla) -> str | None:
        disponibles = self.etiquetas_disponibles()
        indice = tecla - Qt.Key.Key_1
        return disponibles[indice] if 0 <= indice < len(disponibles) else None

    def _cambiar_filtro_desde_item(self, item: QListWidgetItem) -> None:
        etiqueta = item.data(Qt.ItemDataRole.UserRole)
        if etiqueta:
            self.alternar_filtro(etiqueta)

    def _guardar(self) -> None:
        if self.ruta_portafolio is not None:
            self.portafolio.guardar(self.ruta_portafolio)

    def _pedir_carpeta(self) -> Path | None:
        ruta = QFileDialog.getExistingDirectory(self, "Elegir carpeta de portafolio")
        return Path(ruta) if ruta else None

    def keyPressEvent(self, event):  # noqa: N802 -- override de Qt
        etiqueta = self._etiqueta_por_numero(event.key())
        if etiqueta is not None:
            self.alternar_etiqueta_actual(etiqueta)
            event.accept()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, watched, event):  # noqa: N802 -- override de Qt
        if watched in self.tarjetas and event.type() == QEvent.Type.KeyPress:
            etiqueta = self._etiqueta_por_numero(event.key())
            if etiqueta is not None:
                self.alternar_etiqueta_actual(etiqueta)
                return True
            if event.key() == Qt.Key.Key_Left:
                self._mover_foco(-1)
                return True
            if event.key() == Qt.Key.Key_Right:
                self._mover_foco(1)
                return True
        return super().eventFilter(watched, event)
