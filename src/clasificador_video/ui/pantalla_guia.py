"""Tablero de siete columnas para armar la guía de edición.

La pantalla sigue el mockup aprobado
(`docs/superpowers/mockups/guia-de-edicion-2026-09-19/mockup.html`): barra
arriba con título, subtítulo y las acciones; el aviso de «sin usar»; las
siete columnas como tarjetas; y abajo la franja con los cuartos reales.

El detalle que hacía que todo se viera transparente: en Qt un `QWidget`
pelón ignora el `background-color` y el `border` de la hoja de estilos. Por
eso el panel, las tarjetas de columna, las envolturas y los chips llevan
`WA_StyledBackground`; sin esa bandera el fondo no se pinta y se ve la
ventana de atrás a través de la guía.
"""
from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter
from PySide6.QtWidgets import (QApplication, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget)

from clasificador_video import guia as logica
from clasificador_video.ui import theme

MIME_PASO = "application/x-clasificador-guia-paso"


def _fondo_estilizado(widget):
    """Sin esta bandera un `QWidget` pelón ignora el `background-color` y el
    `border` de la hoja de estilos: el fondo no se pinta y la guía sale
    transparente, con la ventana de atrás viéndose a través. Es la causa
    raíz del «cuadro negro» que se veía antes.
    """
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class _Chip(QWidget):
    quitar_pedido = Signal()

    def __init__(self, cuarto, quitable=False, repetido=False, usos=0,
                 parent=None):
        super().__init__(parent)
        self.cuarto = cuarto
        self._inicio = None
        # Puestos por `_CajaDePasos._repintar` solo para los chips que
        # viven en una columna real. `None` para los de la franja: la
        # franja nunca pierde un cuarto por arrastrarlo (es el origen,
        # no un destino), así que nunca hay de dónde quitarlo.
        self.caja_de_origen = None
        self.indice_de_origen = None
        self.setObjectName("guiaChip")
        _fondo_estilizado(self)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(8, 7, 8, 7)
        fila.setSpacing(6)
        nombre = QLabel(cuarto)
        nombre.setObjectName("guiaChipNombre")
        fila.addWidget(nombre, 1)
        if repetido:
            # Este cuarto ya salió antes en el guion final (contando las
            # columnas en su orden fijo): se marca en cursiva, como el
            # mockup. No es un error -- la aérea puede abrir y cerrar.
            marca = QLabel("otra vez")
            marca.setObjectName("guiaChipOtraVez")
            fila.addWidget(marca)
        if usos > 0:
            # Solo en la franja: cuántas veces está puesto este cuarto en
            # todo el tablero. Los chips de columna no lo llevan.
            conteo = QLabel(f"×{usos}")
            conteo.setObjectName("guiaFranjaConteo")
            fila.addWidget(conteo)
            self.setProperty("usado", True)
        if quitable:
            boton = QPushButton("✕")
            boton.setFlat(True)
            boton.setToolTip("Quitar")
            boton.clicked.connect(self.quitar_pedido)
            fila.addWidget(boton)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._inicio = e.position().toPoint()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        # Sin esto, soltar el botón sin haber cruzado el umbral de
        # arrastre dejaba `_inicio` viejo -- y el siguiente click, aunque
        # empezara en otro lugar, medía el arrastre desde el punto de la
        # vez anterior (mismo cuidado que ya tiene `RoomRail` en el rail).
        self._inicio = None
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e):
        if self._inicio is None or not e.buttons() & Qt.MouseButton.LeftButton:
            return
        if (e.position().toPoint() - self._inicio).manhattanLength() < QApplication.startDragDistance():
            return
        self._inicio = None
        self._arrastrar()

    def _arrastrar(self):
        """Arma el QDrag y decide, con el resultado, si hay que
        desaparecer de la columna de origen.

        Antes esto siempre usaba `CopyAction`: arrastrar de una columna a
        otra dejaba el cuarto en LAS DOS, y `orden_final()` lo mandaba dos
        veces a Premiere como si fueran pasos distintos. Ahora se ofrecen
        las dos acciones y se PIDE `MoveAction` por default -- si el
        destino la acepta (cualquier columna real), es que de verdad hubo
        un movimiento y el origen se vacía; si se suelta sobre la franja
        (que ignora el soltar) o fuera de cualquier caja, el resultado no
        es `MoveAction` y el cuarto se queda donde estaba.
        """
        mime = QMimeData()
        mime.setData(MIME_PASO, self.cuarto.encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        # El pixmap se toma ANTES de atenuar: si no, la imagen que se ve
        # siguiendo al cursor saldría translúcida también.
        drag.setPixmap(self.grab())
        efecto = QGraphicsOpacityEffect(self)
        efecto.setOpacity(theme.ROOM_DRAG_OPACITY)
        self.setGraphicsEffect(efecto)
        try:
            resultado = drag.exec(
                Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                Qt.DropAction.MoveAction,
            )
        finally:
            self.setGraphicsEffect(None)
        if resultado == Qt.DropAction.MoveAction and self.caja_de_origen is not None:
            self.caja_de_origen.quitar(self.indice_de_origen)


class _CajaDePasos(QWidget):
    """El cuerpo de una columna (o la franja): guarda el orden de sus
    cuartos, acepta lo que se suelte encima y dibuja sus chips."""

    cambio = Signal()

    def __init__(self, es_franja=False, parent=None):
        super().__init__(parent)
        self.es_franja = es_franja
        self._orden = []
        self.setObjectName("guiaFranja" if es_franja else "guiaColumnaCuerpo")
        _fondo_estilizado(self)
        # Los pone `PantallaGuia`: la franja necesita saber cuántas veces
        # está puesto cada cuarto, y una columna si el paso se repite. En
        # las pruebas directas de `_CajaDePasos` van en `None`.
        self.es_repetido = None
        self.usos_de = None
        self.setAcceptDrops(True)
        self._layout = QHBoxLayout(self) if es_franja else QVBoxLayout(self)
        if not es_franja:
            self._layout.setContentsMargins(10, 10, 10, 10)
            self._layout.setSpacing(7)
        else:
            self._layout.setContentsMargins(0, 0, 0, 0)
            self._layout.setSpacing(8)

    def cuartos(self):
        return list(self._orden)

    def poner(self, cuartos):
        self._orden = list(cuartos)
        self._repintar()

    def agregar(self, cuarto):
        self._orden.append(cuarto)
        self._repintar()

    def quitar(self, i):
        if 0 <= i < len(self._orden):
            del self._orden[i]
            self._repintar()
            self.cambio.emit()

    def _repintar(self):
        # Se reconstruye entero en vez de mover chips: así el «otra vez» y
        # el «×N» se recalculan con el estado de TODO el tablero.
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.deleteLater()
        for i, cuarto in enumerate(self._orden):
            repetido = bool(self.es_repetido and self.es_repetido(i))
            usos = self.usos_de(cuarto) if self.usos_de else 0
            chip = _Chip(cuarto, quitable=not self.es_franja,
                         repetido=repetido, usos=usos)
            if not self.es_franja:
                chip.caja_de_origen = self
                chip.indice_de_origen = i
                chip.quitar_pedido.connect(lambda i=i: self.quitar(i))
            self._layout.addWidget(chip)
        # El estirón final deja los chips arriba (columnas) o a la
        # izquierda (franja) y empuja el resto del espacio.
        self._layout.addStretch(1)

    def paintEvent(self, e):
        super().paintEvent(e)
        # «arrastra aquí» en las columnas vacías, en cursiva gris. Se
        # dibuja y no se mete como QLabel a propósito: una etiqueta hija
        # contaría como chip en las pruebas de la columna.
        if self.es_franja or self._orden:
            return
        pintor = QPainter(self)
        fuente = self.font()
        fuente.setItalic(True)
        fuente.setPixelSize(theme.FONT_SMALL)
        pintor.setFont(fuente)
        pintor.setPen(QColor(theme.TEXT_3))
        pintor.drawText(self.rect().adjusted(10, 10, -10, 0),
                        Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                        "arrastra aquí")

    def _marcar_sobre_arrastre(self, activo):
        if self.property("sobreArrastre") == activo:
            return
        self.setProperty("sobreArrastre", activo)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_PASO):
            e.acceptProposedAction()
            if not self.es_franja:
                self._marcar_sobre_arrastre(True)

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_PASO):
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        if not self.es_franja:
            self._marcar_sobre_arrastre(False)
        super().dragLeaveEvent(e)

    def dropEvent(self, e):
        if not e.mimeData().hasFormat(MIME_PASO):
            return
        if self.es_franja:
            # La franja no es un destino real: soltar aquí no agrega nada,
            # y al NO aceptar `MoveAction` el chip tampoco desaparece de
            # la columna de donde vino (ver `_Chip._arrastrar`).
            e.ignore()
            return
        self._marcar_sobre_arrastre(False)
        self.agregar(bytes(e.mimeData().data(MIME_PASO)).decode())
        self.cambio.emit()
        e.setDropAction(Qt.DropAction.MoveAction)
        e.accept()


class _SelectorDeUnidades(QWidget):
    """Los chips para elegir qué unidad se está ordenando (spec 2026-09-21).

    Solo se muestra si el proyecto tiene unidades. La llave `""` es «sin
    unidad» y se enseña como tal; su chip solo aparece si ese catálogo tiene
    cuartos.
    """

    unidad_elegida = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("guiaUnidades")
        _fondo_estilizado(self)
        self._fila = QHBoxLayout(self)
        self._fila.setContentsMargins(20, 8, 20, 0)
        self._fila.setSpacing(6)
        self._botones = {}

    def poner(self, unidades):
        while self._fila.count():
            item = self._fila.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.deleteLater()
        self._botones = {}
        for unidad in unidades:
            boton = QPushButton(unidad or "Sin unidad")
            boton.setObjectName("guiaUnidad")
            boton.setCheckable(True)
            boton.setAutoExclusive(True)
            boton.clicked.connect(
                lambda _=False, u=unidad: self.unidad_elegida.emit(u))
            self._fila.addWidget(boton)
            self._botones[unidad] = boton
        self._fila.addStretch(1)

    def marcar(self, unidad):
        for llave, boton in self._botones.items():
            boton.setChecked(llave == unidad)


class PantallaGuia(QWidget):
    clasificacion_pedida = Signal()
    orden_aceptado = Signal(list)
    cerrada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaGuia")
        _fondo_estilizado(self)
        self._cuartos_reales = []
        self._armando = False
        # Un tablero por unidad (spec 2026-09-21): la llave "" es «sin
        # unidad». Al cambiar de unidad se guarda el vivo y se carga el otro,
        # así no se pierde el acomodo a mano de la que se dejó.
        self._unidades = []
        self._unidad = ""
        self._tableros = {}
        # `VideoWidget` es un QOpenGLWidget: Qt lo compone en una capa aparte
        # y `raise_()` NO alcanza para taparlo -- sin este atributo, la
        # pantalla se abre pero el video (o su fondo negro) se sigue viendo
        # encima de todo, y eso es lo que se veía como "un cuadro negro".
        # `WA_AlwaysStackOnTop` es el mecanismo que Qt da para overlays
        # sobre un QOpenGLWidget; sin él, ni el orden en el árbol de
        # widgets ni `raise_()` cambian nada.
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        raiz.addWidget(self._construir_barra())
        self.selector = _SelectorDeUnidades()
        self.selector.unidad_elegida.connect(self._al_elegir_unidad)
        self.selector.setVisible(False)
        raiz.addWidget(self.selector)
        self.aviso_label = QLabel("")
        self.aviso_label.setObjectName("guiaAviso")
        self.aviso_label.setWordWrap(True)
        # La envoltura se esconde entera --con sus márgenes-- cuando no hay
        # nada que avisar: si solo se escondiera la etiqueta, quedaría un
        # hueco de 12 px entre la barra y el tablero.
        self._aviso_wrap = QWidget()
        self._aviso_wrap.setObjectName("guiaAvisoWrap")
        self._aviso_wrap.setVisible(False)
        aviso_fila = QHBoxLayout(self._aviso_wrap)
        aviso_fila.setContentsMargins(20, 12, 20, 0)
        aviso_fila.addWidget(self.aviso_label)
        raiz.addWidget(self._aviso_wrap)

        raiz.addWidget(self._construir_tablero(), 1)
        raiz.addWidget(self._construir_franja())

    # ------------------------------------------------------------------
    # construcción
    # ------------------------------------------------------------------

    def _construir_barra(self):
        barra = QWidget()
        barra.setObjectName("guiaBarra")
        _fondo_estilizado(barra)
        fila = QHBoxLayout(barra)
        fila.setContentsMargins(20, 14, 20, 14)
        fila.setSpacing(12)

        titulos = QVBoxLayout()
        titulos.setSpacing(2)
        titulo = QLabel("Guía de edición")
        titulo.setObjectName("guiaTitulo")
        subtitulo = QLabel(
            "La IA acomodó tus cuartos como punto de partida — arrastra para cambiarlo"
        )
        subtitulo.setObjectName("guiaSubtitulo")
        titulos.addWidget(titulo)
        titulos.addWidget(subtitulo)
        fila.addLayout(titulos)
        fila.addStretch(1)

        # «Pre-ordenar»: le pide a DeepSeek que acomode los cuartos de la
        # unidad elegida como punto de partida; después Bruno reacomoda a
        # mano. El texto cambia a «de nuevo» cuando ya hay algo acomodado.
        self.pre_ordenar_button = QPushButton("Pre-ordenar")
        self.pre_ordenar_button.setObjectName("guiaBoton")
        self.pre_ordenar_button.clicked.connect(self._pedir)
        fila.addWidget(self.pre_ordenar_button)

        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("guiaBotonFantasma")
        cerrar.clicked.connect(self.cerrada)
        fila.addWidget(cerrar)

        self.usar_button = QPushButton("Usar este orden")
        self.usar_button.setObjectName("guiaBotonPrimario")
        self.usar_button.clicked.connect(
            lambda: self.orden_aceptado.emit(self.orden_final()))
        fila.addWidget(self.usar_button)
        return barra

    def _construir_tablero(self):
        scroll = QScrollArea()
        scroll.setObjectName("guiaScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        tablero = QWidget()
        tablero.setObjectName("guiaTablero")
        _fondo_estilizado(tablero)
        fila = QHBoxLayout(tablero)
        fila.setContentsMargins(20, 16, 20, 16)
        fila.setSpacing(12)
        self.columnas = {}
        self._conteos = {}
        for dato in logica.COLUMNAS:
            envoltura = QWidget()
            envoltura.setObjectName("guiaColumna")
            _fondo_estilizado(envoltura)
            envoltura.setMinimumWidth(180)
            col = QVBoxLayout(envoltura)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(0)

            encabezado = QWidget()
            encabezado.setObjectName("guiaColumnaEncabezado")
            _fondo_estilizado(encabezado)
            eh = QHBoxLayout(encabezado)
            eh.setContentsMargins(12, 10, 12, 8)
            eh.setSpacing(4)
            nombre = QLabel(dato.titulo)
            nombre.setObjectName("guiaColumnaTitulo")
            conteo = QLabel("")
            conteo.setObjectName("guiaColumnaConteo")
            eh.addWidget(nombre)
            eh.addWidget(conteo)
            eh.addStretch(1)
            col.addWidget(encabezado)

            caja = _CajaDePasos()
            caja.es_repetido = lambda i, cid=dato.id: self._es_repetido(cid, i)
            caja.cambio.connect(self._al_cambiar_columna)
            col.addWidget(caja, 1)
            self.columnas[dato.id] = caja
            self._conteos[dato.id] = conteo
            fila.addWidget(envoltura, 1)
        scroll.setWidget(tablero)
        return scroll

    def _construir_franja(self):
        wrap = QWidget()
        wrap.setObjectName("guiaFranjaWrap")
        _fondo_estilizado(wrap)
        col = QVBoxLayout(wrap)
        col.setContentsMargins(20, 12, 20, 16)
        col.setSpacing(8)
        titulo = QLabel(
            "Tus cuartos — arrastra uno a una columna "
            "(lo puedes repetir las veces que haga falta)"
        )
        titulo.setObjectName("guiaFranjaTitulo")
        col.addWidget(titulo)
        self.franja = _CajaDePasos(es_franja=True)
        self.franja.usos_de = self._usos_de
        col.addWidget(self.franja)
        return wrap

    # ------------------------------------------------------------------
    # las unidades
    # ------------------------------------------------------------------

    def configurar_unidades(self, unidades, actual):
        """Arma el selector y deja elegida `actual`.

        `unidades` es la lista de llaves ("" = sin unidad). El selector solo
        se enseña si hay al menos una unidad de verdad: un proyecto sin
        unidades se comporta exactamente como antes.
        """
        self._unidades = list(unidades)
        self.selector.poner(unidades)
        self.selector.setVisible(any(u for u in unidades))
        for unidad in unidades:
            self._tableros.setdefault(unidad, {"reales": [], "columnas": {}})
        self._unidad = actual if actual in unidades else (
            unidades[0] if unidades else "")
        self.selector.marcar(self._unidad)

    def unidad_actual(self) -> str:
        return self._unidad

    def seleccionar_unidad(self, unidad) -> None:
        """Muestra el tablero de esa unidad, guardando el de la anterior."""
        if unidad == self._unidad:
            self.selector.marcar(unidad)
            return
        self._al_elegir_unidad(unidad)

    def _al_elegir_unidad(self, unidad) -> None:
        if unidad == self._unidad:
            return
        self._guardar_tablero()
        self._unidad = unidad
        self.selector.marcar(unidad)
        self._cargar_tablero(unidad)

    def _guardar_tablero(self) -> None:
        self._tableros[self._unidad] = {
            "reales": list(self._cuartos_reales),
            "columnas": {i: caja.cuartos()
                         for i, caja in self.columnas.items()},
        }

    def _cargar_tablero(self, unidad) -> None:
        tablero = self._tableros.get(unidad) or {"reales": [], "columnas": {}}
        self._cuartos_reales = list(tablero["reales"])
        self.franja.poner(self._cuartos_reales)
        for i, caja in self.columnas.items():
            caja.poner(tablero["columnas"].get(i, []))
        self._repintar_todo()
        self._refrescar_aviso()

    # ------------------------------------------------------------------
    # estado
    # ------------------------------------------------------------------

    def poner_cuartos_reales(self, cuartos):
        self._cuartos_reales = list(cuartos)
        self.franja.poner(cuartos)
        for caja in self.columnas.values():
            caja.poner([])
        self._repintar_todo()
        self._refrescar_aviso()

    def mostrar_clasificacion(self, clasificacion, unidad=None):
        """Aplica la clasificación al tablero vivo.

        `unidad` es la unidad a la que pertenece; `main_window` solo llama
        cuando coincide con la elegida, pero se recibe para no aplicar una
        respuesta vieja al tablero equivocado.
        """
        if unidad is not None and unidad != self._unidad:
            return
        self._armando = False
        for caja in self.columnas.values():
            caja.poner([])
        if not clasificacion.ok:
            self._repintar_todo()
            self._poner_aviso(
                f"No se pudo clasificar ({clasificacion.error}). "
                "Acomoda los cuartos a mano.")
            return
        for cuarto, columna in clasificacion.columna_de.items():
            if columna in self.columnas:
                self.columnas[columna].agregar(cuarto)
        self._repintar_todo()
        if clasificacion.inventados:
            # Se marca en vez de callarse: un cuarto que el modelo se
            # inventó no es tuyo, y perderlo en silencio es justo el modo
            # de falla que este aviso existe para evitar.
            self._poner_aviso(
                "El modelo mencionó algo que no es tuyo: "
                + ", ".join(clasificacion.inventados) + ".")
            return
        self._refrescar_aviso()

    def mostrar_guia_aceptada(self, lista):
        self.columnas[logica.COLUMNAS[0].id].poner([r.cuarto for r in lista])
        self._repintar_todo()
        self._refrescar_aviso()

    def armando(self):
        self._armando = True
        self._poner_aviso("Pre-ordenando…")

    def mostrar_falta_llave(self):
        """Sin llave de DeepSeek no hay pre-ordenada posible: se dice y se
        puede acomodar a mano. Mismo trato que un fallo de red."""
        self._armando = False
        self._poner_aviso(
            "Falta la llave de DeepSeek. Ponla en Configuración para "
            "pre-ordenar; mientras, acomoda los cuartos a mano.")

    def agregar_a_columna(self, columna, cuarto):
        self.columnas[columna].agregar(cuarto)
        self._repintar_todo()
        self._refrescar_aviso()

    def orden_final(self):
        return [cuarto for dato in logica.COLUMNAS
                for cuarto in self.columnas[dato.id].cuartos()]

    # ------------------------------------------------------------------
    # ayudantes
    # ------------------------------------------------------------------

    def _es_repetido(self, columna_id, indice):
        """¿Este paso repite un cuarto que ya salió antes? Se recorre el
        guion final en el orden fijo de las columnas, igual que el mockup:
        el paso se marca si su cuarto ya apareció en un paso anterior."""
        vistos = set()
        for dato in logica.COLUMNAS:
            for i, cuarto in enumerate(self.columnas[dato.id].cuartos()):
                if dato.id == columna_id and i == indice:
                    return cuarto in vistos
                vistos.add(cuarto)
        return False

    def _usos_de(self, cuarto):
        return sum(caja.cuartos().count(cuarto)
                   for caja in self.columnas.values())

    def _repintar_todo(self):
        for dato in logica.COLUMNAS:
            caja = self.columnas[dato.id]
            caja._repintar()
            n = len(caja.cuartos())
            self._conteos[dato.id].setText(f"· {n}" if n else "")
        self.franja._repintar()
        self.pre_ordenar_button.setText(
            "Pre-ordenar de nuevo" if self.orden_final() else "Pre-ordenar")

    def _al_cambiar_columna(self):
        self._repintar_todo()
        self._refrescar_aviso()

    def _poner_aviso(self, texto):
        self.aviso_label.setText(texto)
        self._aviso_wrap.setVisible(bool(texto))

    def _refrescar_aviso(self):
        faltan = logica.cuartos_sin_usar(self._cuartos_reales,
                                         self.orden_final())
        self._poner_aviso(("Sin usar: " + ", ".join(faltan) + ".") if faltan else "")

    def _pedir(self):
        if self.orden_final() and QMessageBox.question(
                self, "Pre-ordenar de nuevo",
                "Vas a perder cómo acomodaste los cuartos. "
                "¿Pre-ordenar de nuevo?") != QMessageBox.StandardButton.Yes:
            return
        self.clasificacion_pedida.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape and not self._armando:
            self.cerrada.emit()
            return
        super().keyPressEvent(e)
