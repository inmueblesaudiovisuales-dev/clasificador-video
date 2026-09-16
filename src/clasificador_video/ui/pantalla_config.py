"""La pantalla de configuración.

Hoy tiene un solo ajuste --la llave de la guía de edición-- y aun así vive
aparte en vez de colgarse de un menú: la llave es lo primero que hay que
poner para que la guía sirva, y un ajuste escondido en un menú es un ajuste
que no se encuentra. La app ya perdió una herramienta así antes.

NO ES UN DIÁLOGO MODAL. Es una pantalla hija de la ventana, como la de la
guía: el diálogo de configuración que abría con `exec()` murió con la F3
porque colgaba la suite bajo `offscreen`, y no se reabre ese camino.

Solo dibuja y avisa. Guardar y leer de disco es de `llave.py`, y quien las
llama es la ventana.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clasificador_video import llave as mod_llave


class PantallaConfig(QWidget):
    """Un ajuste: la llave de la guía de edición."""

    llave_guardada = Signal(str)
    llave_borrada = Signal()
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

        subtitulo = QLabel("La llave para armar la guía de edición")
        subtitulo.setObjectName("configSubtitulo")
        raiz.addWidget(subtitulo)

        # Qué hay guardado AHORA. Es lo primero que uno viene a ver: si ya
        # está puesta o no.
        self.estado_label = QLabel("")
        self.estado_label.setObjectName("configEstado")
        raiz.addWidget(self.estado_label)

        self.caja_llave = QLineEdit()
        self.caja_llave.setObjectName("configLlave")
        # Tapada mientras se escribe, por lo mismo que se enseña tapada:
        # esta pantalla puede quedar abierta con alguien al lado.
        self.caja_llave.setEchoMode(QLineEdit.EchoMode.Password)
        self.caja_llave.setPlaceholderText("Pega aquí tu llave de DeepSeek")
        # Enter guarda: es lo único que se puede hacer con una llave pegada.
        self.caja_llave.returnPressed.connect(self._al_guardar)
        raiz.addWidget(self.caja_llave)

        self.guardar_button = QPushButton("Guardar")
        self.guardar_button.setObjectName("configGuardar")
        self.guardar_button.clicked.connect(self._al_guardar)

        self.quitar_button = QPushButton("Quitarla")
        self.quitar_button.setObjectName("configQuitar")
        self.quitar_button.clicked.connect(self._al_quitar)

        self.cerrar_button = QPushButton("Listo")
        self.cerrar_button.setObjectName("configCerrar")
        self.cerrar_button.clicked.connect(self.cerrada.emit)

        fila = QHBoxLayout()
        fila.addWidget(self.guardar_button)
        fila.addWidget(self.quitar_button)
        fila.addStretch(1)
        fila.addWidget(self.cerrar_button)
        raiz.addLayout(fila)

        # La pregunta que sigue a «pégala aquí»: ¿a dónde se va esto? Se
        # contesta sin que haya que preguntarla, porque una llave es de las
        # cosas que uno quiere saber dónde quedaron.
        self.donde_label = QLabel(
            "Se guarda en tu computadora, en ~/.clasificador_video/. No va en "
            "el proyecto de Premiere ni viaja con el material."
        )
        self.donde_label.setObjectName("configDonde")
        self.donde_label.setWordWrap(True)
        raiz.addWidget(self.donde_label)

        raiz.addStretch(1)
        self.cargar("")

    def cargar(self, llave: str) -> None:
        """Enseña qué hay guardado. La caja se queda VACÍA aunque haya
        llave: precargarla sería enseñarla entera, que es justo lo que
        `tapada` existe para evitar."""
        self.caja_llave.clear()
        if llave:
            self.estado_label.setText("Ya está puesta: " + mod_llave.tapada(llave))
            self.quitar_button.setEnabled(True)
        else:
            self.estado_label.setText(
                "Falta la llave. Sin ella, todo lo demás funciona igual: "
                "lo único que no se puede es armar la guía."
            )
            self.quitar_button.setEnabled(False)

    def _al_guardar(self) -> None:
        # Sin espacios: uno pegado al copiar tumbaba la llamada con un «la
        # llave no sirve» que no decía por qué.
        valor = self.caja_llave.text().strip()
        if not valor:
            return  # apretar Guardar en vacío no borra la que ya está
        self.llave_guardada.emit(valor)
        self.cargar(valor)

    def _al_quitar(self) -> None:
        self.llave_borrada.emit()
        self.cargar("")
