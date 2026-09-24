"""Pantalla para sumar entregas de Premiere a un portafolio."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from clasificador_video_portafolio import lector_de_entregas as lector
from clasificador_video_portafolio.portafolio import Portafolio, ProyectoImportado


ESTILO_IMPORTAR = """
QWidget#pantallaImportar {
    background: #0a0b0d;
    color: #e6e9ee;
    font-family: -apple-system, "Helvetica Neue", sans-serif;
}
QLabel#dropzoneImportar {
    background: #101216;
    border: 2px dashed #262b33;
    border-radius: 14px;
    color: #9aa3b0;
    font-size: 13px;
    line-height: 1.4;
    padding: 34px;
}
QFrame#filaImportada {
    background: #16191e;
    border: 1px solid #262b33;
    border-radius: 8px;
}
QFrame#rayaProyecto {
    background: #c0885a;
    border: none;
    border-radius: 2px;
}
QLabel#nombreImportado {
    color: #e6e9ee;
    font-size: 12px;
    font-weight: 600;
}
QLabel#detalleImportado {
    color: #626b78;
    font-size: 10px;
}
QLabel#estadoImportado {
    background: rgba(85, 192, 138, 36);
    border: 1px solid rgba(85, 192, 138, 100);
    border-radius: 9px;
    color: #55c08a;
    font-size: 10px;
    padding: 3px 8px;
}
QLabel#estadoImportado[faltantes="true"] {
    background: rgba(212, 105, 108, 36);
    border-color: rgba(212, 105, 108, 100);
    color: #d4696c;
}
"""


class FilaImportada(QFrame):
    """Resumen visible de una entrega que acaba de entrar al portafolio."""

    def __init__(self, proyecto: ProyectoImportado, faltantes: int, parent=None):
        super().__init__(parent)
        self.setObjectName("filaImportada")
        self._proyecto = proyecto
        self._faltantes = faltantes
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        raya = QFrame()
        raya.setObjectName("rayaProyecto")
        raya.setFixedWidth(3)
        layout.addWidget(raya)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        self.nombre = QLabel()
        self.nombre.setObjectName("nombreImportado")
        self.detalle = QLabel()
        self.detalle.setObjectName("detalleImportado")
        textos.addWidget(self.nombre)
        textos.addWidget(self.detalle)
        layout.addLayout(textos, 1)
        self.estado = QLabel()
        self.estado.setObjectName("estadoImportado")
        layout.addWidget(self.estado)
        self.actualizar(proyecto, faltantes)

    def actualizar(self, proyecto: ProyectoImportado, faltantes: int) -> None:
        self._proyecto = proyecto
        self._faltantes = faltantes
        self.nombre.setText(proyecto.ruta_prproj.name)
        clips = len(proyecto.clips)
        if faltantes:
            self.detalle.setText(f"{clips} clips usados · {faltantes} sin vincular")
            self.estado.setText(f"Falta ubicar {faltantes}")
            self.estado.setProperty("faltantes", "true")
        else:
            self.detalle.setText(f"{clips} clips usados · todos vinculados")
            self.estado.setText("✓ listo")
            self.estado.setProperty("faltantes", "false")
        self.estado.style().unpolish(self.estado)
        self.estado.style().polish(self.estado)

    def nombre_visible(self) -> str:
        return self.nombre.text()

    def tiene_faltantes(self) -> bool:
        return self._faltantes > 0


class PantallaImportar(QWidget):
    """Dropzone y lista de entregas importadas.

    El portafolio se inyecta para que las pantallas posteriores compartan la
    misma instancia. La aplicación da un selector para elegir la ruta al
    primer import; los tests y usos embebidos pueden pasarla directamente.
    """

    def __init__(
        self,
        portafolio: Portafolio | None = None,
        ruta_portafolio: Path | None = None,
        elegir_ruta: Callable[[], Path | None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.portafolio = portafolio or Portafolio()
        self.ruta_portafolio = ruta_portafolio
        self._elegir_ruta = elegir_ruta
        self.filas: list[FilaImportada] = []
        self._filas_por_ruta: dict[Path, FilaImportada] = {}
        self.setObjectName("pantallaImportar")
        self.setStyleSheet(ESTILO_IMPORTAR)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(14)
        layout.addStretch()
        self.dropzone = QLabel(
            "⇩\n\nSuelta aquí tus .prproj\n"
            "Cada uno se suma como un proyecto. Se leen todas sus secuencias."
        )
        self.dropzone.setObjectName("dropzoneImportar")
        self.dropzone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dropzone.setMinimumWidth(560)
        self.dropzone.setMinimumHeight(180)
        layout.addWidget(self.dropzone, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.lista = QWidget()
        self.lista.setObjectName("listaImportada")
        self.lista.setFixedWidth(640)
        self._layout_filas = QVBoxLayout(self.lista)
        self._layout_filas.setContentsMargins(0, 0, 0, 0)
        self._layout_filas.setSpacing(8)
        layout.addWidget(self.lista, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

    def importar(self, ruta: Path) -> ProyectoImportado | None:
        """Lee una entrega, actualiza su fila y persiste el portafolio."""
        ruta = Path(ruta)
        if not self._asegurar_ruta_portafolio():
            return None
        usados = lector.clips_usados_en(ruta)
        faltantes = lector.medios_faltantes(usados)
        proyecto = self.portafolio.agregar_proyecto(ruta.stem, ruta, usados)
        fila = self._filas_por_ruta.get(ruta)
        if fila is None:
            fila = FilaImportada(proyecto, len(faltantes))
            self.filas.append(fila)
            self._filas_por_ruta[ruta] = fila
            self._layout_filas.addWidget(fila)
        else:
            fila.actualizar(proyecto, len(faltantes))
        if self.ruta_portafolio is not None:
            self.portafolio.guardar(self.ruta_portafolio)
        return proyecto

    def _asegurar_ruta_portafolio(self) -> bool:
        if self.ruta_portafolio is not None:
            return True
        if self._elegir_ruta is None:
            return True
        self.ruta_portafolio = self._elegir_ruta()
        return self.ruta_portafolio is not None

    def dragEnterEvent(self, event):  # noqa: N802 -- override de Qt
        rutas = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
        if any(ruta.suffix.lower() == ".prproj" for ruta in rutas):
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802 -- override de Qt
        for url in event.mimeData().urls():
            ruta = Path(url.toLocalFile())
            if ruta.suffix.lower() == ".prproj":
                self.importar(ruta)
        event.acceptProposedAction()
