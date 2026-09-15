"""La pantalla de la guía de edición.

Solo dibuja y conecta. Todo lo que decide algo vive en `guia.py` --armar la
pregunta, leer la respuesta, revisarla-- y todo lo que habla con el mundo en
`ia.py`, `llave.py` y `patron.py`. Si algún día hay que arreglar POR QUÉ una
lista salió mal, no se busca aquí.

Spec: docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md
"""
from __future__ import annotations

from html import escape

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
from clasificador_video.ui import theme
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
    cerrada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaGuia")
        # Sin esta bandera un QWidget puro ignora el `background-color` del
        # QSS y la pantalla sale transparente encima de la ventana. Mismo
        # caso que `SegmentedControl`.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._respuesta: logica.Respuesta | None = None
        # Mientras el modelo piensa, Esc no cierra: la respuesta llegaria a
        # una pantalla escondida y se veria como si no hubiera pasado nada.
        self._armando = False

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

        # Se abre encima de la ventana, asi que tiene que traer por donde
        # salir. Sin esto la unica salida era cerrar la app.
        self.cerrar_button = QPushButton("Cerrar")
        self.cerrar_button.setObjectName("guiaCerrar")
        self.cerrar_button.clicked.connect(self.cerrada.emit)

        fila = QHBoxLayout()
        fila.addWidget(self.armar_button)
        fila.addWidget(self.usar_button)
        fila.addStretch(1)
        fila.addWidget(self.cerrar_button)
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

    def keyPressEvent(self, event) -> None:
        """Esc cierra, que es lo que uno intenta primero.

        Menos a media llamada: ahi la respuesta llegaria a una pantalla
        escondida y se veria como si nunca hubiera pasado nada.
        """
        if event.key() == Qt.Key.Key_Escape and not self._armando:
            self.cerrada.emit()
            return
        super().keyPressEvent(event)

    def armando(self) -> None:
        """Mientras el modelo piensa. Una espera sin aviso se lee como una
        app trabada, y ésta puede durar veinte segundos."""
        self._armando = True
        self.armar_button.setEnabled(False)
        self.usar_button.setEnabled(False)
        # Tambien el de cerrar: si Esc no cierra mientras arma, este no
        # puede verse apretable. Lo que se ve y lo que se puede hacer tienen
        # que ser la misma cosa.
        self.cerrar_button.setEnabled(False)
        self.avisos_label.setText("Armando la guía…")
        self.resultado.setPlainText("")

    def mostrar_respuesta(self, respuesta: logica.Respuesta,
                          revision: logica.Revision) -> None:
        """Enseña la guía, o el error. **Nunca media lista.**"""
        self._respuesta = respuesta if respuesta.ok else None
        self._armando = False
        self.armar_button.setEnabled(True)
        self.cerrar_button.setEnabled(True)

        if not respuesta.ok:
            self.avisos_label.setText(respuesta.error)
            self.resultado.setPlainText("")
            self.usar_button.setEnabled(False)
            return

        self.avisos_label.setText("\n".join(logica.avisos_de_la_revision(revision)))
        # Va en HTML y no en texto plano por UNA razon: el renglon que se
        # salio del patron tiene que VERSE distinto. En plano los tres
        # renglones salian iguales y el aviso se perdia -- se vio en la
        # captura del 2026-09-14, que es para lo que existe mirar el pixel.
        self.resultado.setHtml(self._html(respuesta, revision))
        self.usar_button.setEnabled(True)

    def texto_del_resultado(self) -> str:
        return self.resultado.toPlainText()

    @staticmethod
    def _html(respuesta: logica.Respuesta, revision: logica.Revision) -> str:
        """La guia dibujada, con el renglon fuera del patron destacado.

        El resto de las razones van apagadas y esa va en claro y en cursiva:
        es informacion que solo tenia la IA, y es lo unico de la lista que
        hay que leer con atencion. Mismo trato que el panel de Premiere le
        da al mismo renglon.
        """
        renglones = []
        vistos = set()
        for i, r in enumerate(respuesta.lista, start=1):
            # El numero va escrito y no en un <ol>: el de la lista se pierde
            # al copiar el texto, y el orden es justo lo que uno copia.
            partes = [f"{i}. <b>{escape(r.cuarto)}</b>"]
            if r.cuarto in vistos:
                # SOLO de la segunda vez en adelante. Marcar tambien la
                # primera diria que algo pasa con ella, y no pasa nada: el
                # que vuelve es el segundo.
                partes.append(
                    f'<span style="color: {theme.TEXT_2};"> (otra vez)</span>'
                )
            vistos.add(r.cuarto)
            if r.porque:
                color = theme.TEXT if r.fuera_del_patron else theme.TEXT_3
                cursiva = " font-style: italic;" if r.fuera_del_patron else ""
                partes.append(
                    f'<span style="color: {color};{cursiva}"> — '
                    f"{escape(r.porque)}</span>"
                )
            if r.cuarto in revision.inventados:
                partes.append(
                    f'<span style="color: {theme.REJECT_COLOR};">'
                    "  (este no es tuyo)</span>"
                )
            renglones.append("".join(partes))

        partes = []
        if respuesta.recorrido:
            partes.append("<p>" + escape(respuesta.recorrido) + "</p>")
        partes.append("<p>" + "<br>".join(renglones) + "</p>")
        return "".join(partes)

    @staticmethod
    def _texto(respuesta: logica.Respuesta, revision: logica.Revision) -> str:
        renglones = []
        vistos = set()
        for i, r in enumerate(respuesta.lista, start=1):
            otra = "  (otra vez)" if r.cuarto in vistos else ""
            vistos.add(r.cuarto)
            marca = "  (este no es tuyo)" if r.cuarto in revision.inventados else ""
            porque = (" — " + r.porque) if r.porque else ""
            renglones.append(f"{i}. {r.cuarto}{otra}{porque}{marca}")
        partes = []
        if respuesta.recorrido:
            partes.append(respuesta.recorrido)
        partes.append("\n".join(renglones))
        return "\n\n".join(partes)
