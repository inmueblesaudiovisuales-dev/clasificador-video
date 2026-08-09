# src/clasificador_video/ui/transicion.py
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
from PySide6.QtWidgets import QLabel, QWidget

DURACION_MS = 500


class TransicionDeTarjeta:
    """La tarjeta crece hasta la posicion del visor al cruzar a modo clip.

    `DECISIONES.md`: «medio segundo que evita el "¿donde estaba?" en cada
    cruce».

    Tres decisiones que salieron del spike, no de suponer:

    1. **Se anima una COPIA, no la tarjeta.** La copia es hija de la
       ventana y no del area con scroll, asi que puede volar por encima de
       todo. Animar la tarjeta de verdad la sacaria de la hoja, que
       ademas se re-acomoda debajo.
    2. **Sobrevive a que la hoja se reconstruya a mitad del camino.** El
       gesto que dispara la animacion tambien cambia el clip actual, y eso
       repinta la hoja: la copia ya no depende de la tarjeta original.
       Medido: reconstruir la hoja con la animacion viva no revienta.
    3. **Una a la vez.** `⇥` repetido rapido cancela la anterior en vez de
       encimarlas. Seis encimadas tampoco revientan --se midio-- pero seis
       tarjetas volando a la vez no significan nada.

    Medido con 128 tarjetas: 0.02 ms por cuadro de mediana, 1.14 ms el
    peor. El presupuesto de un cuadro a 60 fps es 16.7 ms.
    """

    def __init__(self, ventana: QWidget):
        self._ventana = ventana
        self._animacion: QPropertyAnimation | None = None
        self._copia: QLabel | None = None

    def lanzar(self, tarjeta: QWidget, destino: QRect) -> bool:
        """Devuelve si la animacion arranco.

        No arranca si la tarjeta no se ve: dentro del area con scroll, una
        tarjeta que quedo abajo tiene coordenadas de cientos o miles de
        pixeles fuera de la ventana (medido: y = 3596 con 128 clips), y
        animar desde ahi seria una raya cruzando la pantalla en vez de un
        gesto que explica de donde salio el clip.
        """
        self.cancelar()
        if not tarjeta.isVisible() or destino.isEmpty():
            return False
        origen = self._en_la_ventana(tarjeta)
        if not self._ventana.rect().intersects(origen):
            return False

        self._copia = QLabel("", self._ventana)
        self._copia.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._copia.setScaledContents(True)
        self._copia.setPixmap(tarjeta.grab())
        self._copia.setGeometry(origen)
        self._copia.show()
        self._copia.raise_()

        self._animacion = QPropertyAnimation(self._copia, b"geometry", self._ventana)
        self._animacion.setDuration(DURACION_MS)
        self._animacion.setStartValue(origen)
        self._animacion.setEndValue(destino)
        # OutCubic: arranca rapido y frena al llegar. Que frene es lo que
        # hace que el ojo alcance a ver DONDE termino.
        self._animacion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animacion.finished.connect(self._limpiar)
        self._animacion.start()
        return True

    def cancelar(self) -> None:
        if self._animacion is not None:
            self._animacion.stop()
        self._limpiar()

    def corriendo(self) -> bool:
        return (
            self._animacion is not None
            and self._animacion.state() == QPropertyAnimation.State.Running
        )

    def _limpiar(self) -> None:
        if self._copia is not None:
            # `setParent(None)` antes de `deleteLater()`: el borrado es
            # diferido hasta que corra el ciclo de eventos, y con `⇥`
            # repetido rapido las copias viejas seguirian siendo hijas de
            # la ventana --y dibujandose-- hasta entonces.
            self._copia.hide()
            self._copia.setParent(None)
            self._copia.deleteLater()
            self._copia = None
        self._animacion = None

    def _en_la_ventana(self, widget: QWidget) -> QRect:
        esquina = widget.mapTo(self._ventana, widget.rect().topLeft())
        return QRect(esquina, widget.size())
