# src/clasificador_video/ui/pantalla_inicio.py
"""Lo primero que se ve al abrir: los proyectos de Bruno.

Antes la app caia directo en la hoja, con una sesion escondida que era
siempre la misma. Aqui se elige con cual trabajar --«eliges un proyecto pero
te enseña los ultimos, como Premiere»--, y por eso la lista pesa mas que los
dos botones que la acompañan.

Un proyecto que ya no esta en su lugar **no se poda**: se muestra apagado y
dice que no se encuentra. Que desaparezca sin explicacion es peor que verlo
gris, porque Bruno no puede distinguir «se perdio» de «falta conectar el
disco».
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clasificador_video import __version__
from clasificador_video.ui.segmented import SegmentedControl
from clasificador_video.ui.text import ElidedLabel

FILA_ALTO = 54          # dos renglones cortos, del alto de una fila de lista
MARGEN = 28


def _etiqueta(object_name: str, apagado: bool,
              modo: Qt.TextElideMode = Qt.TextElideMode.ElideRight) -> ElidedLabel:
    """Una etiqueta que se corta sola y no le pasa el clic al mouse.

    `Ignored` en horizontal no es un detalle: sin eso el `sizeHint` de la
    etiqueta es el del texto COMPLETO, y una carpeta con nombre largo
    empujaria el ancho de la ventana en vez de elidirse.
    """
    etiqueta = ElidedLabel(modo=modo)
    etiqueta.setObjectName(object_name)
    # el clic tiene que llegar al boton de abajo, que es lo que se puede
    # apretar: la fila entera es el control, no solo su borde
    etiqueta.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    etiqueta.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    # el color apagado viaja por propiedad y no por el `:disabled` del padre:
    # en QSS de Qt el pseudo-estado de un ancestro no llega a los hijos de
    # forma confiable, y la fila quedaria gris con el texto a plena luz
    etiqueta.setProperty("apagado", "true" if apagado else "false")
    return etiqueta


class _FilaReciente(QPushButton):
    """Un proyecto de la lista. Es un boton y no un renglon decorado porque
    la accion principal es abrirlo: que se vea clickeable no es adorno.

    El texto va en dos `ElidedLabel` adentro y no en el `text()` del boton
    porque un QPushButton no elide: la ruta larga estiraria la ventana.
    """

    quitar_pedido = Signal(Path)
    # el clic que SI abre. La fila no emite `clicked` a secas hacia afuera:
    # un proyecto que no esta no se abre, y prometerlo seria peor que verlo
    # gris.
    abrir_pedido = Signal(Path)
    refrescar_pedido = Signal(Path)

    def __init__(self, entrada, parent=None):
        super().__init__(parent)
        self.setObjectName("filaReciente")
        self.entrada = entrada
        disponible = bool(entrada.disponible)
        self.disponible = disponible
        # NO se apaga con `setEnabled(False)`, aunque sea lo obvio: un widget
        # apagado no recibe eventos de mouse, y eso incluye el clic DERECHO
        # -- Qt los descarta antes de entregarlos--. O sea que el unico
        # «Quitar de la lista» que existe quedaba fuera de alcance justo en
        # los renglones que uno quiere quitar: los que ya no estan. Se
        # apaga por PROPIEDAD, que es como esta fila ya pintaba su texto
        # (ver `_etiqueta`), y lo que no se puede hacer --abrirlo-- se corta
        # donde de verdad pasa, en `_al_hacer_click`.
        self.setProperty("perdido", "true" if not disponible else "false")
        self.setFixedHeight(FILA_ALTO)
        self.setCursor(Qt.PointingHandCursor if disponible
                       else Qt.ArrowCursor)

        fila_horizontal = QHBoxLayout(self)
        fila_horizontal.setContentsMargins(12, 8, 12, 8)
        fila_horizontal.setSpacing(8)
        caja_host = QWidget()
        caja = QVBoxLayout(caja_host)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(2)
        self.nombre = _etiqueta("recienteNombre", apagado=not disponible)
        self.nombre.setText(entrada.nombre)
        # por el MEDIO: en una ruta, lo que distingue una fila de otra es la
        # carpeta del final. Cortando por el final quedan dos proyectos
        # hermanos con el mismo prefijo largo y sin la unica parte que los
        # separa -- se leen identicos.
        self.detalle = _etiqueta("recienteDetalle", apagado=not disponible,
                                 modo=Qt.TextElideMode.ElideMiddle)
        self.detalle.setText(self._detalle(entrada, disponible))
        caja.addWidget(self.nombre)
        caja.addWidget(self.detalle)
        self.pildora = QLabel("")
        self.pildora.setObjectName("recientePildora")
        self.pildora.hide()
        self.refrescar_button = QPushButton("⟳")
        self.refrescar_button.setObjectName("recienteRefrescar")
        self.refrescar_button.setToolTip("Revisar si el editor ya contestó")
        self.refrescar_button.hide()
        self.refrescar_button.clicked.connect(
            lambda: self.refrescar_pedido.emit(self.entrada.ruta)
        )
        fila_horizontal.addWidget(caja_host, 1)
        fila_horizontal.addWidget(self.pildora)
        fila_horizontal.addWidget(self.refrescar_button)
        # la ruta completa, para cuando la elidida no alcanza
        self.setToolTip(str(entrada.ruta))
        self.clicked.connect(self._al_hacer_click)

    def set_estado_de_entrega(self, estado: str | None, cuando_texto: str = "") -> None:
        """Pinta el estado de entrega sin volver a consultar Drive."""
        from clasificador_video.entrega import EstadoEntrega

        self.pildora.hide()
        self.refrescar_button.hide()
        if estado == EstadoEntrega.CON_EDITOR:
            self.pildora.setText(f"●  Con el editor · {cuando_texto}")
            self.pildora.setProperty("tono", "esperando")
            self.pildora.show()
            self.refrescar_button.show()
        elif estado == EstadoEntrega.EDITOR_CONTESTO:
            self.pildora.setText(f"✓  El editor ya contestó · {cuando_texto}")
            self.pildora.setProperty("tono", "contesto")
            self.pildora.show()
        self.pildora.style().unpolish(self.pildora)
        self.pildora.style().polish(self.pildora)

    def _al_hacer_click(self) -> None:
        """Un proyecto que no esta no se abre.

        El corte vive AQUI y no en `setEnabled(False)`: apagar el widget
        tambien apaga el clic derecho, y con el se iba el unico «Quitar de
        la lista» que tiene la pantalla -- justo en los renglones que uno
        quiere quitar.
        """
        if self.disponible:
            self.abrir_pedido.emit(self.entrada.ruta)

    @staticmethod
    def _detalle(entrada, disponible: bool) -> str:
        carpeta = str(entrada.ruta.parent)
        if not disponible:
            # el «cuando» se cede a proposito: lo que hay que leer aqui es
            # que el archivo no esta, y tres datos en un renglon que ademas
            # se elide dejarian el importante fuera de cuadro
            return f"No se encuentra  ·  {carpeta}"
        cuando = entrada.cuando or "sin fecha"
        return f"{cuando}  ·  {carpeta}"

    def menu_de_contexto(self) -> QMenu:
        """El menu, armado pero sin mostrar.

        Separado de `contextMenuEvent` para poder probarlo sin abrir nada:
        mostrar menus en los tests es justo lo que cuelga bajo `offscreen`.
        """
        menu = QMenu(self)
        menu.addAction("Quitar de la lista").triggered.connect(
            lambda: self.quitar_pedido.emit(self.entrada.ruta)
        )
        return menu

    def contextMenuEvent(self, event):  # noqa: N802 -- override de Qt
        # popup, no exec: `exec` bloquea y cuelga la suite bajo offscreen
        self.menu_de_contexto().popup(event.globalPos())


class _FilaActiva(QPushButton):
    """Una fila de la pestaña "En edición externa": el mismo proyecto que
    ya aparece en "Tus proyectos", pero con las acciones de la entrega a
    la vista -- sin tener que abrirlo primero (spec 2026-09-19 §5).

    Solo se construye para proyectos disponibles con una entrega activa:
    a diferencia de `_FilaReciente`, no conoce el estado "perdido".
    """

    abrir_pedido = Signal(Path)
    refrescar_pedido = Signal(Path)
    traer_de_vuelta_pedido = Signal(Path)
    ya_entregado_pedido = Signal(Path)

    def __init__(self, entrada, estado: str, cuando_texto: str, parent=None):
        super().__init__(parent)
        from clasificador_video.entrega import EstadoEntrega

        self.setObjectName("filaActiva")
        self.entrada = entrada
        self.setFixedHeight(FILA_ALTO)
        self.setCursor(Qt.PointingHandCursor)

        fila_horizontal = QHBoxLayout(self)
        fila_horizontal.setContentsMargins(12, 8, 12, 8)
        fila_horizontal.setSpacing(8)
        caja_host = QWidget()
        caja = QVBoxLayout(caja_host)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(2)
        self.nombre = _etiqueta("recienteNombre", apagado=False)
        self.nombre.setText(entrada.nombre)
        self.detalle = _etiqueta("recienteDetalle", apagado=False,
                                 modo=Qt.TextElideMode.ElideMiddle)
        self.detalle.setText(f"subido {cuando_texto}  ·  {entrada.ruta.parent}")
        caja.addWidget(self.nombre)
        caja.addWidget(self.detalle)

        self.pildora = QLabel("")
        self.pildora.setObjectName("recientePildora")
        es_en_revision = estado == EstadoEntrega.EN_REVISION
        if estado == EstadoEntrega.CON_EDITOR:
            self.pildora.setText("●  Con el editor")
            self.pildora.setProperty("tono", "esperando")
        elif estado == EstadoEntrega.EDITOR_CONTESTO:
            self.pildora.setText("✓  El editor ya contestó")
            self.pildora.setProperty("tono", "contesto")
        else:
            self.pildora.setText("◐  En revisión")
            self.pildora.setProperty("tono", "revision")

        self.refrescar_button = QPushButton("⟳")
        self.refrescar_button.setObjectName("recienteRefrescar")
        self.refrescar_button.setToolTip("Revisar si el editor ya contestó")
        self.refrescar_button.setVisible(not es_en_revision)
        self.refrescar_button.clicked.connect(
            lambda: self.refrescar_pedido.emit(self.entrada.ruta))

        self.traer_button = QPushButton("Traer de vuelta")
        self.traer_button.setObjectName("activaTraer")
        self.traer_button.setVisible(not es_en_revision)
        self.traer_button.clicked.connect(
            lambda: self.traer_de_vuelta_pedido.emit(self.entrada.ruta))

        self.ya_entregado_button = QPushButton("Ya entregado")
        self.ya_entregado_button.setObjectName("activaYaEntregado")
        self.ya_entregado_button.clicked.connect(
            lambda: self.ya_entregado_pedido.emit(self.entrada.ruta))

        fila_horizontal.addWidget(caja_host, 1)
        fila_horizontal.addWidget(self.pildora)
        fila_horizontal.addWidget(self.refrescar_button)
        fila_horizontal.addWidget(self.traer_button)
        fila_horizontal.addWidget(self.ya_entregado_button)
        self.setToolTip(str(entrada.ruta))
        self.clicked.connect(lambda: self.abrir_pedido.emit(self.entrada.ruta))


class PantallaInicio(QWidget):
    """La lista de recientes, «Proyecto nuevo» y «Abrir otro…».

    No abre ni crea nada por su cuenta: avisa con una señal y quien la usa
    decide. Asi se puede probar sin tocar disco ni abrir selectores.
    """

    abrir_pedido = Signal(Path)
    nuevo_pedido = Signal()
    abrir_otro_pedido = Signal()
    quitar_pedido = Signal(Path)
    refrescar_pedido = Signal(Path)
    traer_de_vuelta_pedido = Signal(Path)
    ya_entregado_pedido = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaInicio")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.filas: list[_FilaReciente] = []
        self.filas_activas: list[_FilaActiva] = []

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(MARGEN, MARGEN, MARGEN, MARGEN)
        raiz.setSpacing(14)

        self.titulo = QLabel("Tus proyectos")
        self.titulo.setObjectName("inicioTitulo")
        raiz.addWidget(self.titulo)

        # Un renglon aqui adentro y no un `QMessageBox`: los modales bloquean
        # con `exec` por dentro y esta pantalla es justo donde Bruno esta
        # decidiendo que abrir. Que el aviso viva al lado de la lista le deja
        # seguir eligiendo mientras lo lee.
        self.aviso = QLabel()
        self.aviso.setObjectName("inicioAviso")
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        raiz.addWidget(self.aviso)

        self.switch = SegmentedControl(
            ["Tus proyectos", "En edición externa"], object_name="inicioSwitch"
        )
        self.switch.selected.connect(self._al_cambiar_pestaña)
        raiz.addWidget(self.switch)

        self.lista_host = QWidget()
        self.lista = QVBoxLayout(self.lista_host)
        self.lista.setContentsMargins(0, 0, 0, 0)
        self.lista.setSpacing(6)
        raiz.addWidget(self.lista_host)

        # El estado vacio es un widget aparte y no una fila mas: se esconde y
        # se muestra, en vez de crearse y destruirse con cada `set_recientes`.
        self.vacio = QWidget()
        self.vacio.setObjectName("inicioVacio")
        vacio_caja = QVBoxLayout(self.vacio)
        vacio_caja.setContentsMargins(0, 10, 0, 10)
        vacio_caja.setSpacing(4)
        self.vacio_titulo = QLabel("Todavía no tienes proyectos")
        self.vacio_titulo.setObjectName("inicioVacioTitulo")
        self.vacio_hint = QLabel(
            "Crea uno nuevo y arrastra ahí tus carpetas de material."
        )
        self.vacio_hint.setObjectName("inicioVacioHint")
        vacio_caja.addWidget(self.vacio_titulo)
        vacio_caja.addWidget(self.vacio_hint)
        raiz.addWidget(self.vacio)

        self.activos_host = QWidget()
        self.activos_lista = QVBoxLayout(self.activos_host)
        self.activos_lista.setContentsMargins(0, 0, 0, 0)
        self.activos_lista.setSpacing(6)
        raiz.addWidget(self.activos_host)

        self.activos_vacio = QWidget()
        self.activos_vacio.setObjectName("inicioVacio")
        activos_vacio_caja = QVBoxLayout(self.activos_vacio)
        activos_vacio_caja.setContentsMargins(0, 10, 0, 10)
        activos_vacio_caja.setSpacing(4)
        activos_vacio_titulo = QLabel("No tienes proyectos en edición externa")
        activos_vacio_titulo.setObjectName("inicioVacioTitulo")
        activos_vacio_hint = QLabel(
            "Los que subas a Drive para un editor van a aparecer aquí."
        )
        activos_vacio_hint.setObjectName("inicioVacioHint")
        activos_vacio_caja.addWidget(activos_vacio_titulo)
        activos_vacio_caja.addWidget(activos_vacio_hint)
        raiz.addWidget(self.activos_vacio)

        raiz.addStretch(1)

        botones = QHBoxLayout()
        botones.setSpacing(8)
        self.boton_nuevo = QPushButton("Proyecto nuevo")
        self.boton_nuevo.setObjectName("inicioPrimario")
        self.boton_abrir_otro = QPushButton("Abrir otro…")
        self.boton_nuevo.clicked.connect(self.nuevo_pedido.emit)
        self.boton_abrir_otro.clicked.connect(self.abrir_otro_pedido.emit)
        botones.addWidget(self.boton_nuevo)
        botones.addWidget(self.boton_abrir_otro)
        botones.addStretch(1)
        # La version, apagada y a la derecha del todo. Aqui y no en la barra
        # de titulo: esta pantalla esta vacia de sobra y no le compite el
        # ancho al video, que con material horizontal es lo que escasea.
        # Vive en `clasificador_video.__version__`, el mismo numero que macOS
        # muestra en «Obtener informacion». Y el nombre de la app va aqui
        # porque es el unico lugar de adentro donde se lee: en la barra
        # de titulo el ancho vale mas para el proyecto y sus clips, y el
        # icono ya dice como se llama.
        self.version_label = QLabel(f"Clipify {__version__}")
        self.version_label.setObjectName("versionApp")
        botones.addWidget(self.version_label)
        raiz.addLayout(botones)

        self.set_recientes([])

    def set_recientes(self, entradas: list) -> None:
        for fila in self.filas:
            # los tres pasos, en este orden. `setParent(None)` a secas
            # destruye el objeto de C++ en el acto y ya costo varios
            # segfaults en este proyecto.
            fila.hide()
            fila.setParent(None)
            fila.deleteLater()
        self.filas = []
        for fila in self.filas_activas:
            fila.hide()
            fila.setParent(None)
            fila.deleteLater()
        self.filas_activas = []
        from clasificador_video.entrega import EstadoEntrega

        for entrada in entradas:
            fila = _FilaReciente(entrada, self.lista_host)
            # `abrir_pedido` de la fila y no su `clicked`: la fila decide si
            # se puede abrir (ver `_al_hacer_click`), y esa decision no se
            # copia aqui -- dos lugares diciendo lo mismo se desincronizan.
            fila.abrir_pedido.connect(self.abrir_pedido.emit)
            fila.quitar_pedido.connect(self.quitar_pedido.emit)
            fila.refrescar_pedido.connect(self.refrescar_pedido.emit)
            estado, cuando = self._estado_de_entrega_de(entrada)
            fila.set_estado_de_entrega(estado, cuando)
            self.lista.addWidget(fila)
            self.filas.append(fila)

            if estado is not None and estado != EstadoEntrega.SIN_SUBIR:
                fila_activa = _FilaActiva(entrada, estado, cuando, self.activos_host)
                fila_activa.abrir_pedido.connect(self.abrir_pedido.emit)
                fila_activa.refrescar_pedido.connect(self.refrescar_pedido.emit)
                fila_activa.traer_de_vuelta_pedido.connect(self.traer_de_vuelta_pedido.emit)
                fila_activa.ya_entregado_pedido.connect(self.ya_entregado_pedido.emit)
                self.activos_lista.addWidget(fila_activa)
                self.filas_activas.append(fila_activa)

        self._actualizar_visibilidad()

    def _al_cambiar_pestaña(self, _texto: str) -> None:
        self._actualizar_visibilidad()

    def _actualizar_visibilidad(self) -> None:
        en_activos = self.switch.current() == "En edición externa"
        self.lista_host.setVisible(not en_activos and bool(self.filas))
        self.vacio.setVisible(not en_activos and not self.filas)
        self.activos_host.setVisible(en_activos and bool(self.filas_activas))
        self.activos_vacio.setVisible(en_activos and not self.filas_activas)

    @staticmethod
    def _estado_de_entrega_de(entrada) -> tuple[str | None, str]:
        """Lee el estado guardado de un proyecto disponible, si lo tiene."""
        if not entrada.disponible:
            return None, ""
        from clasificador_video.entrega import EstadoEntrega
        try:
            data = json.loads(entrada.ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, ""
        estado = EstadoEntrega.de_dict(data.get("entrega"))
        if estado is None:
            return None, ""
        return estado.estado, _hace_cuanto(estado.subido_en)

    def avisar(self, texto: str) -> None:
        """Dice algo que salió mal, sin tapar la pantalla."""
        self.aviso.setText(texto)
        self.aviso.show()

    def callar(self) -> None:
        """Quita el aviso. Se llama al intentar otra cosa: dejarlo puesto
        haria que el error de hace tres clics siguiera ahi contradiciendo lo
        que acaba de pasar."""
        self.aviso.hide()
        self.aviso.clear()

    def nombres_visibles(self) -> list[str]:
        return [f.entrada.nombre for f in self.filas]

    def nombres_activos_visibles(self) -> list[str]:
        return [f.entrada.nombre for f in self.filas_activas]


def _hace_cuanto(fecha: str | None) -> str:
    """Una fecha ISO en el texto corto que cabe dentro de una píldora."""
    if not fecha:
        return "sin fecha"
    try:
        entonces = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        ahora = datetime.now(entonces.tzinfo)
    except ValueError:
        return "sin fecha"
    segundos = max(0, int((ahora - entonces).total_seconds()))
    if segundos < 60:
        return "hace un momento"
    if segundos < 3600:
        minutos = segundos // 60
        return f"hace {minutos} minuto" + ("s" if minutos != 1 else "")
    if segundos < 86400:
        horas = segundos // 3600
        return f"hace {horas} hora" + ("s" if horas != 1 else "")
    dias = segundos // 86400
    return f"hace {dias} día" + ("s" if dias != 1 else "")
