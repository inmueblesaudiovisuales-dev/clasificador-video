"""La pantalla de configuración.

Tiene el modo económico, el modo rápido, las carpetas de trabajo y Google
Drive. Vive aparte en vez de colgarse de un menú porque un ajuste escondido
en un menú es un ajuste que no se encuentra; la app ya perdió una
herramienta así antes.

NO ES UN DIÁLOGO MODAL. Es una pantalla hija de la ventana, como la de la
guía: el diálogo de configuración que abría con `exec()` murió con la F3
porque colgaba la suite bajo `offscreen`, y no se reabre ese camino.

Solo dibuja y avisa. Guardar y leer de disco es de `preferencias.py`, y
quien la llama es la ventana.
"""
from __future__ import annotations

from pathlib import Path
from threading import Thread

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
    """El modo económico, el modo rápido y las miniaturas guardadas en
    disco."""

    modo_economico_cambiado = Signal(bool)
    modo_rapido_cambiado = Signal(bool)
    carpeta_premiere_guardada = Signal(Path)
    carpeta_icloud_guardada = Signal(Path)
    drive_conectado = Signal()
    drive_estado_cambiado = Signal(str)
    miniaturas_borrar_pedido = Signal()
    cerrada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaConfig")
        # Sin esta bandera un QWidget puro ignora el `background-color` del
        # QSS y la pantalla sale transparente encima de la ventana.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.cliente_drive = None
        self.drive_estado_cambiado.connect(self._mostrar_estado_drive)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.setSpacing(12)

        titulo = QLabel("Configuración")
        titulo.setObjectName("configTitulo")
        raiz.addWidget(titulo)

        subtitulo = QLabel("Miniaturas, carpetas de trabajo y Google Drive")
        subtitulo.setObjectName("configSubtitulo")
        raiz.addWidget(subtitulo)

        self.cerrar_button = QPushButton("Listo")
        self.cerrar_button.setObjectName("configCerrar")
        self.cerrar_button.clicked.connect(self.cerrada.emit)

        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(self.cerrar_button)
        raiz.addLayout(fila)

        titulo_economico = QLabel("Modo económico")
        titulo_economico.setObjectName("configTitulo")
        raiz.addWidget(titulo_economico)

        self.economico_check = QCheckBox(
            "Generar menos miniaturas a la vez"
        )
        self.economico_check.setObjectName("configEconomico")
        # `checkStateChanged` y no `stateChanged`: PySide6 >=6.7 (el mínimo
        # del proyecto) lo tiene, y es el que no sale marcado como obsoleto.
        self.economico_check.checkStateChanged.connect(
            lambda estado: self.modo_economico_cambiado.emit(
                estado == Qt.CheckState.Checked
            )
        )
        raiz.addWidget(self.economico_check)

        economico_label = QLabel(
            "Prende esto en una computadora con menos memoria o menos "
            "núcleos, como una MacBook Air: la app saca las miniaturas de "
            "una en una en vez de varias a la vez. Tarda más en terminar, "
            "pero no se traba."
        )
        economico_label.setObjectName("configDonde")
        economico_label.setWordWrap(True)
        raiz.addWidget(economico_label)

        titulo_rapido = QLabel("Modo rápido")
        titulo_rapido.setObjectName("configTitulo")
        raiz.addWidget(titulo_rapido)

        self.rapido_check = QCheckBox(
            "Miniaturas chicas y pocas, todas a la vez"
        )
        self.rapido_check.setObjectName("configRapido")
        self.rapido_check.checkStateChanged.connect(
            lambda estado: self.modo_rapido_cambiado.emit(
                estado == Qt.CheckState.Checked
            )
        )
        raiz.addWidget(self.rapido_check)

        rapido_label = QLabel(
            "Mismas miniaturas chicas que el modo económico (menos fotos "
            "por tira, menos resolución), pero sin el freno de \"una a la "
            "vez\" -- para cuando tu computadora aguanta procesar varias al "
            "mismo tiempo y solo quieres terminar rápido."
        )
        rapido_label.setObjectName("configDonde")
        rapido_label.setWordWrap(True)
        raiz.addWidget(rapido_label)

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

        titulo_premiere = QLabel("Proyectos de Premiere")
        titulo_premiere.setObjectName("configTitulo")
        raiz.addWidget(titulo_premiere)
        self.carpeta_premiere_label = QLabel("Elige la carpeta raíz donde guardas tus proyectos.")
        self.carpeta_premiere_label.setObjectName("configDonde")
        self.carpeta_premiere_label.setWordWrap(True)
        raiz.addWidget(self.carpeta_premiere_label)
        self.carpeta_premiere_button = QPushButton("Elegir…")
        self.carpeta_premiere_button.setObjectName("configPremiere")
        self.carpeta_premiere_button.clicked.connect(self._al_elegir_carpeta_premiere)
        raiz.addWidget(self.carpeta_premiere_button)

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

        self.drive_label = QLabel("Google Drive no está conectado.")
        self.drive_label.setObjectName("configDonde")
        raiz.addWidget(self.drive_label)
        self.drive_button = QPushButton("Conectar Google Drive")
        self.drive_button.setObjectName("configDrive")
        self.drive_button.clicked.connect(self._al_conectar_drive)
        raiz.addWidget(self.drive_button)

        raiz.addStretch(1)
        self.cargar()

    def mostrar_peso_de_miniaturas(self, bytes_: int) -> None:
        """Lo que ocupan en disco ahora mismo. Sin ninguna significa que ya
        se acaban de borrar, o que no se ha generado ninguna todavia --
        deshabilitar el boton en ese caso evita un «borrar» sobre la nada."""
        self.miniaturas_peso_label.setText(f"Ocupan {_formatear_bytes(bytes_)} en tu disco.")
        self.miniaturas_borrar_button.setEnabled(bytes_ > 0)

    def _al_elegir_carpeta_premiere(self) -> None:
        elegida = QFileDialog.getExistingDirectory(self, "Carpeta de proyectos de Premiere")
        if elegida:
            self.carpeta_premiere_guardada.emit(Path(elegida))

    def _al_elegir_carpeta_icloud(self) -> None:
        elegida = QFileDialog.getExistingDirectory(self, "Carpeta de iCloud")
        if elegida:
            self.carpeta_icloud_guardada.emit(Path(elegida))

    def _al_conectar_drive(self) -> None:
        """Abre OAuth fuera del hilo de la interfaz, que sigue respondiendo."""
        self.drive_button.setEnabled(False)
        self.drive_label.setText("Conectando Google Drive…")

        def conectar():
            from clasificador_video import drive
            try:
                self.cliente_drive = drive.cliente_autorizado(
                    Path.home() / ".clasificador_video" / "credenciales_google.json")
            except Exception:
                self.drive_estado_cambiado.emit("No se pudo conectar Google Drive.")
            else:
                self.drive_estado_cambiado.emit("Google Drive está conectado.")
                self.drive_conectado.emit()
            finally:
                self.drive_estado_cambiado.emit("")

        Thread(target=conectar, daemon=True).start()

    def _mostrar_estado_drive(self, texto: str) -> None:
        if texto:
            self.drive_label.setText(texto)
        else:
            self.drive_button.setEnabled(True)

    def cargar(self, modo_economico: bool = False,
              modo_rapido: bool = False) -> None:
        """Enseña qué hay guardado, reflejando las preferencias en sus
        casillas. Se bloquean las señales para no reemitir nada al solo
        reflejar lo guardado."""
        self.economico_check.blockSignals(True)
        self.economico_check.setChecked(modo_economico)
        self.economico_check.blockSignals(False)
        self.rapido_check.blockSignals(True)
        self.rapido_check.setChecked(modo_rapido)
        self.rapido_check.blockSignals(False)
