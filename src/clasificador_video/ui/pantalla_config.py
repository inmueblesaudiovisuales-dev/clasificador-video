"""La pantalla de configuración.

Tiene las carpetas de trabajo y las miniaturas guardadas en disco. Vive
aparte en vez de colgarse de un menú porque un ajuste escondido en un menú es
un ajuste que no se encuentra; la app ya perdió una herramienta así antes.

NO ES UN DIÁLOGO MODAL. Es una pantalla hija de la ventana, como la de la
guía: el diálogo de configuración que abría con `exec()` murió con la F3
porque colgaba la suite bajo `offscreen`, y no se reabre ese camino.

Solo dibuja y avisa. Guardar y leer de disco es de `preferencias.py`, y
quien la llama es la ventana.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _formatear_bytes(bytes_: int) -> str:
    """`1.4 GB`, `240 MB`, `0 B`. Nunca decimales en B: no tienen sentido."""
    valor = float(bytes_)
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if valor < 1024 or unidad == "TB":
            return f"{int(valor)} {unidad}" if unidad == "B" else f"{valor:.1f} {unidad}"
        valor /= 1024
    return f"{valor:.1f} TB"  # inalcanzable, pero sin esto mypy se queja


class PantallaConfig(QWidget):
    """Las carpetas de trabajo y las miniaturas guardadas en disco."""

    importacion_rapida_pregunta_antes_cambiado = Signal(bool)
    carpeta_icloud_guardada = Signal(Path)
    miniaturas_borrar_pedido = Signal()
    cerrada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaConfig")
        # Sin esta bandera un QWidget puro ignora el `background-color` del
        # QSS y la pantalla sale transparente encima de la ventana.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.setSpacing(12)

        titulo = QLabel("Configuración")
        titulo.setObjectName("configTitulo")
        raiz.addWidget(titulo)

        subtitulo = QLabel("Miniaturas y carpetas de trabajo")
        subtitulo.setObjectName("configSubtitulo")
        raiz.addWidget(subtitulo)

        self.cerrar_button = QPushButton("Listo")
        self.cerrar_button.setObjectName("configCerrar")
        self.cerrar_button.clicked.connect(self.cerrada.emit)

        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(self.cerrar_button)
        raiz.addLayout(fila)

        titulo_importacion_rapida = QLabel("Importación rápida")
        titulo_importacion_rapida.setObjectName("configTitulo")
        raiz.addWidget(titulo_importacion_rapida)

        self.importacion_rapida_pregunta_check = QCheckBox(
            "Preguntar antes de crear los proxies"
        )
        self.importacion_rapida_pregunta_check.setObjectName(
            "configImportacionRapidaPregunta")
        self.importacion_rapida_pregunta_check.checkStateChanged.connect(
            lambda estado: self.importacion_rapida_pregunta_antes_cambiado.emit(
                estado == Qt.CheckState.Checked
            )
        )
        raiz.addWidget(self.importacion_rapida_pregunta_check)

        importacion_rapida_label = QLabel(
            "Al darle a Clipify la carpeta de un proyecto (clic derecho "
            "sobre \"Importar carpetas…\"), los proxies que falten arrancan "
            "solos. Prende esto para que primero te pregunte, como en el "
            "resto de la app."
        )
        importacion_rapida_label.setObjectName("configDonde")
        importacion_rapida_label.setWordWrap(True)
        raiz.addWidget(importacion_rapida_label)

        titulo_miniaturas = QLabel("Miniaturas guardadas")
        titulo_miniaturas.setObjectName("configTitulo")
        raiz.addWidget(titulo_miniaturas)
        self.miniaturas_peso_label = QLabel("")
        self.miniaturas_peso_label.setObjectName("configDonde")
        self.miniaturas_peso_label.setWordWrap(True)
        raiz.addWidget(self.miniaturas_peso_label)
        self.miniaturas_borrar_button = QPushButton("Borrar miniaturas guardadas")
        self.miniaturas_borrar_button.setObjectName("configBorrarMiniaturas")
        self.miniaturas_borrar_button.clicked.connect(self.miniaturas_borrar_pedido.emit)
        raiz.addWidget(self.miniaturas_borrar_button)

        titulo_icloud = QLabel("Carpeta de iCloud")
        titulo_icloud.setObjectName("configTitulo")
        raiz.addWidget(titulo_icloud)
        self.carpeta_icloud_label = QLabel(
            "Elige la carpeta donde ya tienes armado 01. IAV, 02. PI y "
            "03. Templates. Ahí es donde \"Proyecto nuevo\" con folio va a "
            "crear cada proyecto."
        )
        self.carpeta_icloud_label.setObjectName("configDonde")
        self.carpeta_icloud_label.setWordWrap(True)
        raiz.addWidget(self.carpeta_icloud_label)
        self.carpeta_icloud_button = QPushButton("Elegir…")
        self.carpeta_icloud_button.setObjectName("configIcloud")
        self.carpeta_icloud_button.clicked.connect(self._al_elegir_carpeta_icloud)
        raiz.addWidget(self.carpeta_icloud_button)

        raiz.addStretch(1)
        self.cargar()

    def mostrar_peso_de_miniaturas(self, bytes_: int) -> None:
        """Lo que ocupan en disco ahora mismo. Sin ninguna significa que ya
        se acaban de borrar, o que no se ha generado ninguna todavia --
        deshabilitar el boton en ese caso evita un «borrar» sobre la nada."""
        self.miniaturas_peso_label.setText(f"Ocupan {_formatear_bytes(bytes_)} en tu disco.")
        self.miniaturas_borrar_button.setEnabled(bytes_ > 0)

    def _al_elegir_carpeta_icloud(self) -> None:
        elegida = QFileDialog.getExistingDirectory(self, "Carpeta de iCloud")
        if elegida:
            self.carpeta_icloud_guardada.emit(Path(elegida))

    def cargar(self, importacion_rapida_pregunta_antes: bool = False) -> None:
        """Enseña qué hay guardado, reflejando las preferencias en sus
        casillas. Se bloquean las señales para no reemitir nada al solo
        reflejar lo guardado."""
        self.importacion_rapida_pregunta_check.blockSignals(True)
        self.importacion_rapida_pregunta_check.setChecked(
            importacion_rapida_pregunta_antes)
        self.importacion_rapida_pregunta_check.blockSignals(False)
