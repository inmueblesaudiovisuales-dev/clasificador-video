# src/clasificador_video/ui/room_palette.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from clasificador_video.filters import _sin_acentos
from clasificador_video.ui import theme
from clasificador_video.ui.text import ElidedLabel

ANCHO = 330        # el del mockup
MAX_OPCIONES = 6   # mas filas y la paleta tapa media pantalla


class _Opcion(QWidget):
    """Una fila de la paleta: tecla + color + nombre + conteo.

    Las mismas señas que la fila del rail a proposito: la paleta no es otra
    lista de cuartos, es la misma vista de otra forma. Si aqui el color o la
    tecla fueran distintos, habria que volver a aprender cual es cual.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("palOption")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.nombre = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(9)
        self.key_cap = QLabel("")
        self.key_cap.setObjectName("keyCap")
        self.key_cap.setFixedSize(18, 18)
        self.key_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.swatch = QLabel("")
        self.swatch.setFixedSize(3, 13)
        self.swatch.setAttribute(Qt.WA_StyledBackground, True)
        self.name_label = ElidedLabel("")
        self.name_label.setObjectName("palName")
        self.count_label = QLabel("")
        self.count_label.setObjectName("roomCount")
        layout.addWidget(self.key_cap)
        layout.addWidget(self.swatch)
        layout.addWidget(self.name_label, stretch=1)
        layout.addWidget(self.count_label)

    def poner(self, nombre: str, numero: int | None, color: str, cuantos: int) -> None:
        self.nombre = nombre
        self.name_label.setText(nombre)
        self.key_cap.setText("" if numero is None else str(numero))
        self.key_cap.setProperty("sin_tecla", numero is None)
        self.swatch.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        self.count_label.setText(str(cuantos))

    def marcar_activa(self, activa: bool) -> None:
        self.setProperty("activa", activa)
        self.style().unpolish(self)
        self.style().polish(self)


class RoomPalette(QWidget):
    """Buscar y crear cuartos escribiendo, sin soltar el teclado.

    Un solo mecanismo cubre tres necesidades: los cuartos que pasan de nueve
    --donde ya no hay tecla--, crear uno al vuelo, y asignar en lote
    respetando la seleccion.

    **No es un QDialog modal**: un modal roba el teclado y hay que cerrarlo
    para seguir clasificando. Es un hijo de la ventana que se muestra encima
    del video.
    """

    room_chosen = Signal(str)
    room_created = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("roomPalette")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(ANCHO)
        self._cuartos: list[str] = []
        self._conteos: dict[str, int] = {}
        self._activa = 0

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        fila = QWidget()
        fila.setObjectName("palInput")
        fl = QHBoxLayout(fila)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(9)
        self.input = QLineEdit()
        self.input.setObjectName("palQuery")
        self.input.setPlaceholderText("Buscar o crear cuarto…")
        self.input.textChanged.connect(self._al_escribir)
        self.alcance_label = QLabel("")
        self.alcance_label.setObjectName("palScope")
        fl.addWidget(self.input, stretch=1)
        fl.addWidget(self.alcance_label)
        raiz.addWidget(fila)

        self.opciones = [_Opcion(self) for _ in range(MAX_OPCIONES)]
        for opcion in self.opciones:
            raiz.addWidget(opcion)

        self.crear_label = QLabel("")
        self.crear_label.setObjectName("palCreate")
        raiz.addWidget(self.crear_label)

        self.foot_label = QLabel("↑ ↓ elegir     ⏎ asignar     esc cancelar")
        self.foot_label.setObjectName("palFoot")
        raiz.addWidget(self.foot_label)

        self.hide()

    # --- apertura y cierre ------------------------------------------------

    def abrir(self, cuartos: list[str], conteos: dict[str, int],
              seleccionados: int = 1) -> None:
        self._cuartos = list(cuartos)
        self._conteos = dict(conteos)
        self.alcance_label.setText(
            f"a {seleccionados} clips" if seleccionados > 1 else ""
        )
        self.input.clear()          # dispara `_al_escribir`, que repuebla
        self._refrescar()
        self.show()
        self.raise_()
        self.input.setFocus()

    def cerrar(self) -> None:
        self.hide()

    # --- lo que se ve -----------------------------------------------------

    def _coincidencias(self) -> list[str]:
        texto = self.input.text().strip()
        if not texto:
            return self._cuartos[:MAX_OPCIONES]
        aguja = _sin_acentos(texto)
        return [c for c in self._cuartos if aguja in _sin_acentos(c)][:MAX_OPCIONES]

    def opciones_visibles(self) -> list[str]:
        return [o.nombre for o in self.filas_visibles()]

    def filas_visibles(self) -> list[_Opcion]:
        return [o for o in self.opciones if not o.isHidden()]

    def opcion_activa(self) -> str | None:
        visibles = self.opciones_visibles()
        if not visibles:
            return None
        return visibles[min(self._activa, len(visibles) - 1)]

    def opcion_de_crear(self) -> str | None:
        """El nombre que se crearia, o None.

        Convive con las coincidencias --el mockup las muestra juntas--: que
        `rec` encuentre «Recámara 1» no quiere decir que no quieras un cuarto
        nuevo llamado `rec`. Lo unico que no se ofrece es un nombre que YA
        existe igual, que partiria el cuarto en dos con el mismo nombre.
        """
        texto = self.input.text().strip()
        if not texto:
            return None
        if any(_sin_acentos(c) == _sin_acentos(texto) for c in self._cuartos):
            return None
        return texto

    def _al_escribir(self, _texto: str) -> None:
        # la seleccion vuelve arriba: si se quedara en la fila 2 mientras la
        # lista cambia debajo, `⏎` asignaria un cuarto distinto del que estas
        # viendo en primer lugar
        self._activa = 0
        self._refrescar()

    def _refrescar(self) -> None:
        coincidencias = self._coincidencias()
        for opcion in self.opciones:
            opcion.hide()
        for fila, nombre in zip(self.opciones, coincidencias):
            indice = self._cuartos.index(nombre)
            # a partir del decimo no hay atajo numerico: el hueco queda vacio
            # en vez de mentir con un numero que no funciona. Son justamente
            # los cuartos por los que esta paleta existe.
            numero = indice + 1 if indice < 9 else None
            fila.poner(nombre, numero, theme.room_color(indice),
                       self._conteos.get(nombre, 0))
            fila.show()
        crear = self.opcion_de_crear()
        self.crear_label.setText(f"+  Crear cuarto «{crear}»" if crear else "")
        self.crear_label.setVisible(bool(crear))
        self._marcar_activa()
        self.adjustSize()

    def _marcar_activa(self) -> None:
        visibles = self.filas_visibles()
        for indice, fila in enumerate(visibles):
            fila.marcar_activa(indice == min(self._activa, len(visibles) - 1))

    # --- teclado ----------------------------------------------------------

    def mover(self, delta: int) -> None:
        visibles = self.opciones_visibles()
        if not visibles:
            return
        self._activa = max(0, min(self._activa + delta, len(visibles) - 1))
        self._marcar_activa()

    def confirmar(self) -> None:
        """`⏎`: asigna el cuarto activo, o crea el que escribiste.

        Elegir gana sobre crear: si hay una coincidencia a la vista, `⏎` la
        asigna. Crear un cuarto por accidente cuesta mas que asignarlo mal
        --el rail queda con basura-- y la opcion de crear siempre esta a una
        flecha de distancia.
        """
        activa = self.opcion_activa()
        if activa is not None:
            self.room_chosen.emit(activa)
        else:
            crear = self.opcion_de_crear()
            if crear is None:
                return
            self.room_created.emit(crear)
        self.cerrar()

    def keyPressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        tecla = event.key()
        if tecla == Qt.Key.Key_Escape:
            self.cerrar()
            return
        if tecla in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            self.mover(1 if tecla == Qt.Key.Key_Down else -1)
            return
        if tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirmar()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):  # noqa: N802 -- override de Qt
        return super().eventFilter(obj, event)
