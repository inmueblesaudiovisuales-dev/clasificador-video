# src/clasificador_video/ui/room_rail.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.ui import theme
from clasificador_video.ui.text import ElidedLabel


def _texto_de_estado(cuantos: int, palabra: str) -> str:
    return f"{cuantos} {palabra}" if palabra else str(cuantos)

MAX_TECLAS = 9      # los atajos numericos llegan hasta el noveno cuarto
MAX_HISTORIAL = 4   # el rail mide 200 px: mas filas empujan la lista de cuartos


class _BarraProgreso(QWidget):
    """Barra segmentada por cuarto: un tramo por cuarto con su color de
    identidad, mas un tramo apagado para lo que falta clasificar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(5)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)
        self._tramos: list[QWidget] = []

    _ultimos: tuple | None = None

    def set_counts(self, counts: list[int], pendientes: int) -> None:
        # los tramos solo dependen de estos numeros: si no cambiaron, la barra
        # ya esta dibujada y recrearla deja widgets huerfanos
        if self._ultimos == (tuple(counts), pendientes):
            return
        self._ultimos = (tuple(counts), pendientes)
        for tramo in self._tramos:
            tramo.setParent(None)
            tramo.deleteLater()
        self._tramos = []
        for indice, cuantos in enumerate(counts):
            if cuantos <= 0:
                continue
            self._tramos.append(self._tramo(theme.room_color(indice), cuantos))
        if pendientes > 0:
            self._tramos.append(self._tramo(theme.PENDING_COLOR, pendientes))
        self._redondear_extremos()

    def _tramo(self, color: str, peso: int) -> QWidget:
        tramo = QWidget()
        tramo.setAttribute(Qt.WA_StyledBackground, True)
        tramo.setStyleSheet(f"background-color: {color};")
        self._layout.addWidget(tramo, stretch=peso)
        return tramo

    def _redondear_extremos(self) -> None:
        """El redondeo va en el primer y el ultimo tramo, no en el contenedor:
        verificado contra Qt, el `border-radius` de un padre NO recorta a sus
        hijos, asi que redondearlo no haria nada. Y redondear TODOS los tramos
        --como hacia la F2-- convierte la barra en nueve pildoras sueltas que
        no se leen como una sola barra de progreso.
        """
        if not self._tramos:
            return
        radio = self.height() // 2
        for tramo, lados in (
            (self._tramos[0], "border-top-left-radius: {r}px; border-bottom-left-radius: {r}px;"),
            (self._tramos[-1], "border-top-right-radius: {r}px; border-bottom-right-radius: {r}px;"),
        ):
            tramo.setStyleSheet(tramo.styleSheet() + lados.format(r=radio))


class _Leyenda(QWidget):
    """Los conteos por estado, con el color de cada estado.

    La version de la F2 escribia `● 41 picks  ● 9 rejects  ● 12 sin
    clasificar` en una sola etiqueta: no entra en 200 px y se cortaba a la
    mitad. El mockup usa el numero pelado y deja que el color diga cual es
    cual; el tooltip lo confirma sin gastar ancho.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(11)
        self.puntos: list[QLabel] = []
        self._cuadros: list[QLabel] = []

    def set_estados(self, estados: list[tuple[int, str, str, str]]) -> None:
        # si la estructura es la misma --y lo es siempre, salvo cuando la F7
        # agregue el chip de destacados-- basta con cambiar textos y colores.
        # Recrear los widgets en cada tecla los dejaba huerfanos.
        if len(estados) == len(self.puntos):
            for punto, cuadro, (cuantos, color, que_es, palabra) in zip(
                self.puntos, self._cuadros, estados
            ):
                punto.setText(_texto_de_estado(cuantos, palabra))
                punto.setToolTip(f"{cuantos} {que_es}")
                cuadro.setToolTip(punto.toolTip())
                estilo = f"background-color: {color}; border-radius: 2px;"
                if cuadro.styleSheet() != estilo:
                    cuadro.setStyleSheet(estilo)
            return

        for widget in self.puntos + self._cuadros:
            widget.setParent(None)
            widget.deleteLater()
        self.puntos = []
        self._cuadros = []
        while self._layout.count():
            self._layout.takeAt(0)
        for cuantos, color, que_es, palabra in estados:
            cuadro = QLabel("")
            cuadro.setFixedSize(6, 6)
            cuadro.setAttribute(Qt.WA_StyledBackground, True)
            cuadro.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            numero = QLabel(_texto_de_estado(cuantos, palabra))
            # objectName propio: el mockup escribe la leyenda en la fuente de
            # interfaz, no en la monoespaciada de los conteos por cuarto.
            # Con `dest.` adentro, la mono se nota -- las letras salen
            # separadas como en una terminal.
            numero.setObjectName("legendCount")
            numero.setToolTip(f"{cuantos} {que_es}")
            cuadro.setToolTip(numero.toolTip())
            fila = QHBoxLayout()
            fila.setContentsMargins(0, 0, 0, 0)
            fila.setSpacing(5)
            fila.addWidget(cuadro)
            fila.addWidget(numero)
            self._layout.addLayout(fila)
            self.puntos.append(numero)
            self._cuadros.append(cuadro)
        self._layout.addStretch(1)

    def colores(self) -> list[str]:
        """El color de cada punto, para que un test pueda comprobar que la
        leyenda no perdio el canal semantico."""
        return [
            c.styleSheet().split("background-color: ")[1].split(";")[0]
            for c in self._cuadros
        ]


class _FilaCuarto(QWidget):
    """Tecla + color de identidad + nombre elidido + conteo.

    Se edita EN EL LUGAR: click derecho abre renombrar / subir / bajar /
    eliminar, y doble click renombra. Se eligio menu contextual y no
    arrastrar porque son acciones de una vez por shooting --no merecen
    atajos nuevos ni el riesgo del drag-and-drop dentro de un QVBoxLayout--
    y porque "Subir"/"Bajar" deja explicito que reordenar ES cambiar que
    tecla le toca a cada cuarto. Decidido con Bruno el 2026-08-08.
    """

    rename_requested = Signal(str, str)   # nombre viejo, nombre nuevo
    move_requested = Signal(str, int)     # nombre, -1 arriba / +1 abajo
    remove_requested = Signal(str)
    mover_foco_requested = Signal(object, int)   # fila, direccion

    def __init__(self, numero: int | None, nombre: str, color: str, cuantos: int, parent=None):
        super().__init__(parent)
        self.setObjectName("roomRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(29)
        self.nombre = nombre
        # enfocable para poder manejar los cuartos sin mouse (`⌘R`). Es un
        # QWidget y no un boton, asi que la barra espaciadora no lo "activa":
        # sigue reproduciendo el video aunque el rail tenga el foco.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(8)

        self.key_cap = QLabel("" if numero is None else str(numero))
        self.key_cap.setObjectName("keyCap")
        self.key_cap.setFixedSize(18, 18)
        self.key_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # los cuartos a partir del decimo no tienen atajo numerico: el badge
        # queda vacio en vez de mentir con un numero que no funciona
        self.key_cap.setProperty("sin_tecla", numero is None)

        self.swatch = QLabel("")
        self.swatch.setFixedSize(3, 14)
        self.swatch.setAttribute(Qt.WA_StyledBackground, True)
        self.swatch.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

        self.name_label = ElidedLabel(nombre)
        self.name_label.setObjectName("roomName")
        self.count_label = QLabel(str(cuantos))
        self.count_label.setObjectName("roomCount")

        layout.addWidget(self.key_cap)
        layout.addWidget(self.swatch)
        layout.addWidget(self.name_label, stretch=1)
        layout.addWidget(self.count_label)

    # --- edicion en el lugar ---------------------------------------------

    def contextMenuEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        menu = QMenu(self)
        acciones = [
            (menu.addAction("Renombrar…"), self._pedir_nombre),
            (menu.addAction("Subir"), lambda: self.pedir_mover(-1)),
            (menu.addAction("Bajar"), lambda: self.pedir_mover(+1)),
            (menu.addAction("Eliminar"), self.pedir_eliminar),
        ]
        elegida = menu.exec(event.globalPos())
        for accion, handler in acciones:
            if elegida is accion:
                handler()
                return

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self._pedir_nombre()

    def keyPressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Manejar los cuartos sin mouse, con la fila enfocada.

        Reordenar lleva modificador porque **cambia la tecla del cuarto**: una
        flecha sola solo mueve el foco, que no cambia nada.
        """
        tecla = event.key()
        con_alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        if tecla in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            delta = -1 if tecla == Qt.Key.Key_Up else 1
            if con_alt:
                self.pedir_mover(delta)
            else:
                self.mover_foco_requested.emit(self, delta)
            event.accept()
            return
        if tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._pedir_nombre()
            event.accept()
            return
        if tecla in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.pedir_eliminar()
            event.accept()
            return
        super().keyPressEvent(event)

    # La marca visual del foco la pone QSS con el pseudo-estado `:focus` (ver
    # `theme.build_stylesheet`). Se probo con una propiedad dinamica y
    # `focusInEvent`, y no sirve: ese evento solo se entrega cuando la ventana
    # esta ACTIVA, asi que bajo `offscreen` nunca llegaba y el estilo quedaba
    # sin aplicar en los tests. Con `:focus` lo maneja Qt y sobra el codigo.

    def _pedir_nombre(self) -> None:
        nuevo, ok = QInputDialog.getText(
            self, "Renombrar cuarto", "Nuevo nombre:", text=self.nombre
        )
        if ok:
            self.pedir_renombrar(nuevo)

    # Los tres `pedir_*` existen aparte de los dialogos para poder probar la
    # decision sin abrir una ventana modal, que en un test cuelga.
    def pedir_renombrar(self, nuevo: str) -> None:
        nuevo = nuevo.strip()
        if nuevo and nuevo != self.nombre:
            self.rename_requested.emit(self.nombre, nuevo)

    def pedir_mover(self, delta: int) -> None:
        self.move_requested.emit(self.nombre, delta)

    def pedir_eliminar(self) -> None:
        self.remove_requested.emit(self.nombre)


class _FilaHistorial(QWidget):
    """Una accion deshecha: color de lo que paso, que paso, y el boton.

    El mockup resalta la primera fila --tinte ambar y borde izquierdo-- porque
    es la que deshace `⌘Z`: sin eso, la lista no dice cual de las cuatro se va
    a ir si aprietas la tecla.
    """

    revert_requested = Signal(int)

    def __init__(self, entry, es_primera: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("histRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("top", es_primera)
        self.etiqueta = entry.etiqueta
        self.entry_id = entry.id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10 if es_primera else 12, 6, 12, 6)
        layout.setSpacing(8)

        self.swatch = QLabel("")
        self.swatch.setFixedSize(3, 12)
        self.swatch.setAttribute(Qt.WA_StyledBackground, True)
        self.swatch.setStyleSheet(
            f"background-color: {entry.color}; border-radius: 2px;"
        )

        # dos etiquetas y no una: el mockup pone QUE paso en negritas y claro,
        # y sobre que en gris. Elide la primera --el nombre del cuarto es lo
        # que puede ser largo-- y deja el detalle entero, que es lo corto.
        self.what_label = ElidedLabel(entry.etiqueta)
        self.what_label.setObjectName("histWhat")
        self.detail_label = QLabel(entry.detalle)
        self.detail_label.setObjectName("histDetail")

        self.undo_button = QPushButton("↺")
        self.undo_button.setObjectName("histUndo")
        self.undo_button.setFixedSize(18, 18)
        # sin esto, la barra espaciadora activa el boton enfocado en vez de
        # reproducir el video
        self.undo_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.undo_button.setToolTip(f"Revertir: {entry.etiqueta} {entry.detalle}")
        self.undo_button.clicked.connect(
            lambda: self.revert_requested.emit(self.entry_id)
        )

        # `Maximum` deja que la etiqueta se ENCOJA y elida cuando el nombre del
        # cuarto es largo, pero nunca que crezca mas alla de su texto: con
        # stretch normal se comeria el espacio libre y empujaria el detalle
        # contra el boton, en vez de dejarlo pegado como el mockup.
        self.what_label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.swatch)
        layout.addWidget(self.what_label, stretch=1)
        layout.addWidget(self.detail_label)
        layout.addStretch(1)
        layout.addWidget(self.undo_button)


class RoomRail(QWidget):
    """Columna izquierda de 200 px: progreso y cuartos.

    Reemplaza a la columna vieja, al boton de importar suelto y al panel
    "Material importado", que ocupaba media columna para listar nombres de
    carpetas y no existe en el mockup.
    """

    import_requested = Signal()
    room_created = Signal(str)
    room_renamed = Signal(str, str)
    room_moved = Signal(str, int)
    room_removed = Signal(str)
    revert_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("roomRail")
        self.setFixedWidth(theme.RAIL_WIDTH)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # --- bloque de progreso ---
        progreso = QWidget()
        pl = QVBoxLayout(progreso)
        pl.setContentsMargins(12, 13, 12, 12)
        pl.setSpacing(9)

        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.progress_big = QLabel("0")
        self.progress_big.setObjectName("progressBig")
        self.progress_total = QLabel("/0")
        self.progress_total.setObjectName("progressTotal")
        self.progress_caption = QLabel("CLASIFICADOS")
        self.progress_caption.setObjectName("railHeader")
        theme.apply_letter_spacing(self.progress_caption)
        fila.addWidget(self.progress_big)
        fila.addWidget(self.progress_total, alignment=Qt.AlignmentFlag.AlignBottom)
        fila.addStretch(1)
        fila.addWidget(self.progress_caption, alignment=Qt.AlignmentFlag.AlignBottom)
        pl.addLayout(fila)

        self.progress_bar = _BarraProgreso()
        pl.addWidget(self.progress_bar)

        self.leyenda = _Leyenda()
        pl.addWidget(self.leyenda)
        progreso.setObjectName("railProgress")
        raiz.addWidget(progreso)

        # --- encabezado de cuartos ---
        encabezado = QWidget()
        encabezado.setObjectName("railSectionHeader")
        el = QHBoxLayout(encabezado)
        el.setContentsMargins(12, 0, 12, 0)
        el.setSpacing(5)
        cabecera = QLabel("CUARTOS")
        cabecera.setObjectName("railHeader")
        theme.apply_letter_spacing(cabecera)
        # el ⏎ va dentro de un keycap, igual que las teclas de cuarto: si es
        # una tecla, se ve como tecla
        self.find_key = QLabel("⏎")
        self.find_key.setObjectName("keyCap")
        self.find_key.setFixedSize(17, 15)
        self.find_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.find_key.setProperty("sin_tecla", False)
        self.find_hint = QLabel("buscar")
        self.find_hint.setObjectName("roomCount")
        el.addWidget(cabecera)
        el.addStretch(1)
        el.addWidget(self.find_key)
        el.addWidget(self.find_hint)
        encabezado.setFixedHeight(30)
        raiz.addWidget(encabezado)

        # --- lista de cuartos ---
        self._rooms_container = QWidget()
        self._rooms_layout = QVBoxLayout(self._rooms_container)
        self._rooms_layout.setContentsMargins(7, 6, 7, 6)
        self._rooms_layout.setSpacing(0)
        self._rooms_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.rows: list[_FilaCuarto] = []

        # --- la fila fija de `S`: repetir el cuarto del clip anterior ---
        # Va arriba de los cuartos y FUERA de `self.rows`: `set_rooms`
        # reconstruye esa lista entera, y si viviera dentro se la llevaria
        # puesta cada vez que cambia un cuarto.
        self.same_caption = QLabel("IGUAL AL CLIP ANTERIOR")
        self.same_caption.setObjectName("sameCaption")
        theme.apply_letter_spacing(self.same_caption)
        self.same_row = _FilaCuarto(None, "", theme.CURRENT_COLOR, 0)
        self.same_row.setObjectName("sameRow")
        self.same_row.key_cap.setText("S")
        self.same_row.key_cap.setProperty("sin_tecla", False)
        self.same_row.count_label.setText("↩")   # `↩` del mockup: aplica y avanza
        self.same_row.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.same_caption.hide()
        self.same_row.hide()
        self._rooms_layout.addWidget(self.same_caption)
        self._rooms_layout.addWidget(self.same_row)

        # La app abre con el rail VACIO: no hay paso previo de configuracion
        # y los cuartos se crean sobre la marcha desde aca (DECISIONES.md).
        self.new_room_row = QPushButton("+  Nuevo cuarto")
        self.new_room_row.setObjectName("newRoomRow")
        self.new_room_row.setFixedHeight(29)
        self.new_room_row.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.new_room_row.clicked.connect(self._pedir_cuarto_nuevo)
        self._rooms_layout.addWidget(self.new_room_row)
        raiz.addWidget(self._rooms_container, stretch=1)

        # --- historial, entre los cuartos y el pie ---
        self.history_panel = QWidget()
        self.history_panel.setObjectName("historyPanel")
        self._history_layout = QVBoxLayout(self.history_panel)
        self._history_layout.setContentsMargins(0, 0, 0, 6)
        self._history_layout.setSpacing(0)

        cabecera_hist = QWidget()
        cabecera_hist.setFixedHeight(30)
        chl = QHBoxLayout(cabecera_hist)
        chl.setContentsMargins(12, 0, 12, 0)
        self.history_caption = QLabel("HISTORIAL")
        self.history_caption.setObjectName("railHeader")
        theme.apply_letter_spacing(self.history_caption)
        self.history_key = QLabel("⌘Z")
        self.history_key.setObjectName("keyCap")
        self.history_key.setFixedSize(24, 15)
        self.history_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_key.setProperty("sin_tecla", False)
        chl.addWidget(self.history_caption)
        chl.addStretch(1)
        chl.addWidget(self.history_key)
        self._history_layout.addWidget(cabecera_hist)
        self.history_panel.hide()  # al abrir la app no hay nada que deshacer
        self.history_rows: list[_FilaHistorial] = []
        raiz.addWidget(self.history_panel)

        # --- importar, al pie ---
        self.import_button = QPushButton("Importar carpetas…")
        self.import_button.setObjectName("importButton")
        self.import_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.import_button.clicked.connect(self.import_requested.emit)
        pie = QWidget()
        fl = QVBoxLayout(pie)
        fl.setContentsMargins(9, 6, 9, 10)
        fl.addWidget(self.import_button)
        raiz.addWidget(pie)

    def set_rooms(self, rooms: list[str], counts: dict[str, int]) -> None:
        """Repuebla el rail. Si la LISTA no cambió, solo refresca conteos.

        `MainWindow._refresh_rail` corre en cada tecla. Reconstruir las filas
        cada vez tiraba widgets huerfanos que no se liberaban: medido, 1237 de
        mas tras 60 teclas. Y lo que cambia al clasificar es el conteo, no la
        lista de cuartos.
        """
        if [f.nombre for f in self.rows] == list(rooms):
            for fila in self.rows:
                fila.count_label.setText(str(counts.get(fila.nombre, 0)))
            self.progress_bar.set_counts(
                [counts.get(c, 0) for c in rooms], self._pendientes
            )
            return

        for fila in self.rows:
            fila.setParent(None)
            fila.deleteLater()
        self.rows = []
        # la fila de "nuevo cuarto" se saca y se vuelve a poner al final, para
        # que siempre quede debajo del ultimo cuarto
        self._rooms_layout.removeWidget(self.new_room_row)
        for indice, cuarto in enumerate(rooms):
            numero = indice + 1 if indice < MAX_TECLAS else None
            fila = _FilaCuarto(numero, cuarto, theme.room_color(indice), counts.get(cuarto, 0))
            fila.rename_requested.connect(self.room_renamed.emit)
            fila.move_requested.connect(self.room_moved.emit)
            fila.remove_requested.connect(self.room_removed.emit)
            fila.mover_foco_requested.connect(self._mover_foco)
            self._rooms_layout.addWidget(fila)
            self.rows.append(fila)
        self._rooms_layout.addWidget(self.new_room_row)
        self.progress_bar.set_counts(
            [counts.get(c, 0) for c in rooms], self._pendientes
        )

    def set_same_room(self, nombre: str | None, color: str | None) -> None:
        """El cuarto que aplicaria `S`, o `None` si no hay ninguno atras.

        Es una confirmacion, no un acto de memoria: la fila muestra siempre a
        que cuarto va a ir la tecla ANTES de apretarla.
        """
        if not nombre or not color:
            self.same_row.hide()
            self.same_caption.hide()
            return
        self.same_row.nombre = nombre
        self.same_row.name_label.setText(nombre)
        self.same_row.swatch.setStyleSheet(
            f"background-color: {color}; border-radius: 2px;"
        )
        self.same_row.show()
        self.same_caption.show()

    def focus_rooms(self) -> None:
        """`⌘R`: manejar los cuartos sin tocar el mouse.

        Con la fila enfocada: `↑`/`↓` mueven el foco, `⌥↑`/`⌥↓` reordenan
        --que es cambiar la tecla--, `⏎` renombra y `⌫` elimina.

        Con el rail vacio no tiene sentido enfocar nada: lo unico que se puede
        hacer es crear el primero, asi que se abre ese dialogo directo.
        """
        if not self.rows:
            self._pedir_cuarto_nuevo()
            return
        self.rows[0].setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _mover_foco(self, fila, delta: int) -> None:
        if fila not in self.rows:
            return
        destino = self.rows.index(fila) + delta
        if 0 <= destino < len(self.rows):   # en los extremos no se sale
            self.rows[destino].setFocus(Qt.FocusReason.OtherFocusReason)

    def _pedir_cuarto_nuevo(self) -> None:
        nombre, ok = QInputDialog.getText(self, "Nuevo cuarto", "Nombre del cuarto:")
        if ok:
            self._crear_cuarto(nombre)

    def _crear_cuarto(self, nombre: str) -> None:
        """Aparte del dialogo para poder probarlo sin abrir una ventana
        modal, que en un test cuelga."""
        if nombre.strip():
            self.room_created.emit(nombre.strip())

    def set_history(self, entries: list) -> None:
        """Las ultimas acciones, la mas reciente arriba. Se le pasa la lista
        completa del `History`; aca se recorta a lo que entra en el rail."""
        # mismas entradas, mismas filas: `_refresh_history` corre en cada
        # accion y casi siempre el historial no cambio
        ids = [e.id for e in entries[:MAX_HISTORIAL]]
        if ids == [f.entry_id for f in self.history_rows]:
            return
        for fila in self.history_rows:
            fila.setParent(None)
            fila.deleteLater()
        self.history_rows = []
        for posicion, entrada in enumerate(entries[:MAX_HISTORIAL]):
            fila = _FilaHistorial(entrada, es_primera=(posicion == 0))
            fila.revert_requested.connect(self.revert_requested.emit)
            self._history_layout.addWidget(fila)
            self.history_rows.append(fila)
        self.history_panel.setVisible(bool(self.history_rows))

    def set_progress(self, clasificados: int, total: int, pendientes: int = 0) -> None:
        self.progress_big.setText(str(clasificados))
        self.progress_total.setText(f"/{total}")
        self._pendientes = pendientes

    def set_flags(self, picks: int, rejects: int, sin_clasificar: int,
                  destacados: int = 0) -> None:
        # el `dest.` va primero, como en el mockup: es el estado mas alto de
        # la escalera y el que menos clips tiene, asi que leerlo de un vistazo
        # es lo que mas aporta
        # Solo el primero lleva palabra (`6 dest.`), como el mockup: es el
        # estado con menos clips y el mas facil de confundir con un conteo de
        # picks si va pelado. Los otros tres se apoyan en el color, que es de
        # lo que se trata la leyenda.
        self.leyenda.set_estados([
            (destacados, theme.STAR_COLOR, "destacados", "dest."),
            (picks, theme.PICK_COLOR, "picks", ""),
            (rejects, theme.REJECT_COLOR, "rejects", ""),
            (sin_clasificar, theme.PENDING_COLOR, "sin clasificar", ""),
        ])

    def set_current_room(self, cuarto: str | None) -> None:
        for fila in self.rows:
            fila.setProperty("actual", fila.nombre == cuarto)
            fila.style().unpolish(fila)
            fila.style().polish(fila)

    _pendientes = 0
