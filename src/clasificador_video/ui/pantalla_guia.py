"""La pantalla de la guía de edición.

Solo dibuja y conecta. Todo lo que decide algo vive en `guia.py` --armar la
pregunta, leer la respuesta, revisarla-- y todo lo que habla con el mundo en
`ia.py`, `llave.py` y `patron.py`. Si algún día hay que arreglar POR QUÉ una
lista salió mal, no se busca aquí.

Spec: docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from clasificador_video import guia as logica
from clasificador_video.ui.segmented import SegmentedControl

# Los seis que de verdad salieron en los entregables de 2026 de Bruno. No son
# los cuatro de antes ni los doce del rubro: se le ofreció la lista larga
# --oficina, bodega, edificio, penthouse, loft, rancho-- y escogió los suyos.
TIPOS_DE_PROPIEDAD = [
    "Casa",
    "Departamento",
    "Terreno",
    "Local",
    "Quinta de campo",
    "Hospedaje",
]


class PantallaGuia(QWidget):
    """Dos preguntas, el resultado, y «Usar este orden»."""

    guia_pedida = Signal(dict)   # {"lucir": str, "propiedad": str}
    orden_aceptado = Signal(list)  # los cuartos, en el orden aceptado

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaGuia")
        # Sin esta bandera un QWidget puro ignora el `background-color` del
        # QSS y la pantalla sale transparente encima de la ventana. Mismo
        # caso que `SegmentedControl`.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._respuesta: logica.Respuesta | None = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.setSpacing(14)

        # LA PREGUNTA PRINCIPAL VA PRIMERO. Es lo que Bruno pidió: «sí es
        # importante poder describirle qué quiero lucir de cada propiedad».
        self.titulo_lucir = QLabel("¿Qué quieres lucir?")
        self.titulo_lucir.setObjectName("guiaTitulo")
        self.caja_lucir = QTextEdit()
        self.caja_lucir.setObjectName("guiaLucir")
        self.caja_lucir.setPlaceholderText(
            "La alberca y la terraza. La cocina quedó chica, no la luzcas."
        )
        self.caja_lucir.setFixedHeight(96)
        raiz.addWidget(self.titulo_lucir)
        raiz.addWidget(self.caja_lucir)

        self.titulo_tipo = QLabel("¿Qué tipo de propiedad es?")
        self.titulo_tipo.setObjectName("guiaTitulo")
        self.fila_tipos = SegmentedControl(TIPOS_DE_PROPIEDAD)
        raiz.addWidget(self.titulo_tipo)
        raiz.addWidget(self.fila_tipos)

        self.armar_button = QPushButton("Armar la guía")
        self.armar_button.setObjectName("guiaArmar")
        self.armar_button.clicked.connect(self._al_armar)

        self.usar_button = QPushButton("Usar este orden")
        self.usar_button.setObjectName("guiaUsar")
        self.usar_button.setEnabled(False)
        self.usar_button.clicked.connect(self._al_usar)

        fila = QHBoxLayout()
        fila.addWidget(self.armar_button)
        fila.addWidget(self.usar_button)
        fila.addStretch(1)
        raiz.addLayout(fila)

        # Los avisos van ARRIBA del resultado: son lo que hay que leer antes
        # de creerle a la lista.
        self.avisos_label = QLabel("")
        self.avisos_label.setObjectName("guiaAvisos")
        self.avisos_label.setWordWrap(True)
        raiz.addWidget(self.avisos_label)

        self.resultado = QTextEdit()
        self.resultado.setObjectName("guiaResultado")
        self.resultado.setReadOnly(True)
        raiz.addWidget(self.resultado, stretch=1)

    # --- lo que contestó Bruno ---------------------------------------

    def respuestas(self) -> dict:
        return {
            "lucir": self.caja_lucir.toPlainText().strip(),
            "propiedad": self.fila_tipos.current(),
        }

    def _al_armar(self) -> None:
        self.guia_pedida.emit(self.respuestas())

    def _al_usar(self) -> None:
        if self._respuesta and self._respuesta.ok:
            self.orden_aceptado.emit([r.cuarto for r in self._respuesta.lista])

    # --- lo que llegó -------------------------------------------------

    def mostrar_respuesta(self, respuesta: logica.Respuesta,
                          revision: logica.Revision) -> None:
        """Enseña la guía, o el error. **Nunca media lista.**"""
        self._respuesta = respuesta if respuesta.ok else None

        if not respuesta.ok:
            self.avisos_label.setText(respuesta.error)
            self.resultado.setPlainText("")
            self.usar_button.setEnabled(False)
            return

        self.avisos_label.setText("\n".join(logica.avisos_de_la_revision(revision)))
        self.resultado.setPlainText(self._texto(respuesta, revision))
        self.usar_button.setEnabled(True)

    def texto_del_resultado(self) -> str:
        return self.resultado.toPlainText()

    @staticmethod
    def _texto(respuesta: logica.Respuesta, revision: logica.Revision) -> str:
        renglones = []
        for i, r in enumerate(respuesta.lista, start=1):
            marca = "  (este no es tuyo)" if r.cuarto in revision.inventados else ""
            porque = (" — " + r.porque) if r.porque else ""
            renglones.append(f"{i}. {r.cuarto}{porque}{marca}")
        partes = []
        if respuesta.recorrido:
            partes.append(respuesta.recorrido)
        partes.append("\n".join(renglones))
        return "\n\n".join(partes)
