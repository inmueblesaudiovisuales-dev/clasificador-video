# src/clasificador_video/ui/title_bar.py
from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from clasificador_video.ui import theme
from clasificador_video.ui.segmented import SegmentedControl

MODO_CLIP = "Clip"
MODO_HOJA = "Hoja"
TECLA_MODO = "⇥"


def _marca_de_play(tamano: QSize) -> QPixmap:
    """El triangulo de play del icono de la app.

    Pintado y no escrito: un `▶` de fuente cambia de forma, de peso y de
    alineacion vertical segun la maquina, y este es el primer pixel que se
    ve al abrir la app. El fondo ambar y el radio siguen viniendo del QSS
    (`QLabel#appMark`), asi que aca solo va el triangulo.
    """
    escala = 2  # para que no se vea dentado en pantalla retina
    pixmap = QPixmap(tamano * escala)
    pixmap.setDevicePixelRatio(escala)
    pixmap.fill(Qt.GlobalColor.transparent)
    ancho, alto = tamano.width(), tamano.height()
    # proporciones del mockup: un triangulo de 7x9 en una caja de 9x9
    lado = min(ancho, alto) * 0.52
    izquierda = (ancho - lado * 0.78) / 2
    arriba = (alto - lado) / 2
    triangulo = QPolygonF([
        QPointF(izquierda, arriba),
        QPointF(izquierda, arriba + lado),
        QPointF(izquierda + lado * 0.86, arriba + lado / 2),
    ])
    pintor = QPainter(pixmap)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(QColor(theme.BG_APP))
    pintor.drawPolygon(triangulo)
    pintor.end()
    return pixmap


def _boton(texto: str, atajo: str, object_name: str) -> QPushButton:
    boton = QPushButton(f"{texto}  {atajo}")
    boton.setObjectName(object_name)
    # sin esto, la tecla Espacio activaria el boton enfocado en vez de
    # reproducir el clip
    boton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return boton


class TitleBar(QWidget):
    """Barra superior de 36 px: proyecto, guardado y las dos acciones que
    no son de clasificacion.

    Es una de las dos unicas bandas horizontales que el diseño admite (la
    otra es la barra de estado). Todo lo demas vive en columnas o flotando
    sobre el video.
    """

    export_requested = Signal()
    rooms_requested = Signal()
    mode_toggled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(theme.TITLEBAR_HEIGHT)
        self._modo_hoja = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 0, 13, 0)
        layout.setSpacing(13)

        self.mark = QLabel("")
        self.mark.setObjectName("appMark")
        self.mark.setFixedSize(17, 17)
        self.mark.setPixmap(_marca_de_play(self.mark.size()))
        self.mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.project_label = QLabel("")
        self.project_label.setObjectName("projectLabel")
        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("projectSubtitle")

        self.saved_led = QLabel("")
        self.saved_led.setObjectName("savedLed")
        self.saved_led.setFixedSize(6, 6)
        self.saved_label = QLabel("")
        self.saved_label.setObjectName("savedIndicator")

        # el switch de modo: reusa el control segmentado de la velocidad y la
        # calidad en vez de inventar un widget nuevo. El mockup lo pone
        # despues del subtitulo y antes del espaciador.
        self.mode_switch = SegmentedControl(
            [MODO_CLIP, f"{MODO_HOJA}  {TECLA_MODO}"], object_name="modeSwitch"
        )
        self.mode_switch.selected.connect(self._al_elegir_modo)

        self.rooms_button = _boton("Cuartos", "⌘R", "railButton")
        self.export_button = _boton("Exportar a Premiere", "⌘E", "exportButton")
        self.rooms_button.clicked.connect(self.rooms_requested.emit)
        self.export_button.clicked.connect(self.export_requested.emit)

        layout.addWidget(self.mark)
        layout.addWidget(self.project_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.mode_switch)
        layout.addStretch(1)
        layout.addWidget(self.saved_led)
        layout.addWidget(self.saved_label)
        layout.addWidget(self.rooms_button)
        layout.addWidget(self.export_button)

    def set_project(self, nombre: str, total_clips: int) -> None:
        self.project_label.setText(nombre)
        self.subtitle_label.setText(f"{total_clips} clips · Sony FX30")

    def set_modo_hoja(self, en_hoja: bool) -> None:
        """Sincroniza el switch con el modo. NO emite `mode_toggled`: el
        switch es una vista del estado, no una segunda copia -- si emitiera,
        refrescar la barra dispararia el cambio de modo en bucle.

        La tecla se dibuja del lado INACTIVO, como en el mockup: anuncia a
        donde te lleva, no donde estas.
        """
        self._modo_hoja = en_hoja
        etiquetas = (
            (MODO_CLIP, f"{MODO_HOJA}  {TECLA_MODO}") if not en_hoja
            else (f"{MODO_CLIP}  {TECLA_MODO}", MODO_HOJA)
        )
        for boton, etiqueta in zip(self.mode_switch.buttons, etiquetas):
            boton.setText(etiqueta)
        self.mode_switch.set_current(etiquetas[1 if en_hoja else 0])

    def _al_elegir_modo(self, etiqueta: str) -> None:
        # clickear el modo en el que ya estas no hace nada: si emitiera, el
        # click y el `⇥` se contradirian -- clickear `Clip` estando en clip
        # te sacaria a la hoja.
        if etiqueta.startswith(MODO_HOJA) != self._modo_hoja:
            self.mode_toggled.emit()

    def set_saved_seconds(self, segundos: int | None) -> None:
        self.saved_label.setText("" if segundos is None else f"Guardado hace {segundos} s")
        self.saved_led.setVisible(segundos is not None)
