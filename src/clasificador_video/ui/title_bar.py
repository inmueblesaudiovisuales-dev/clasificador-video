# src/clasificador_video/ui/title_bar.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMenu, QPushButton, QWidget,
)

from clasificador_video.ui import marca, theme
from clasificador_video.ui.segmented import SegmentedControl

MODO_CLIP = "Clip"
MODO_HOJA = "Hoja"
TECLA_MODO = "⇥"
# El boton del visor ancho. NO se llama «horizontal» aunque el modo nazca
# del material horizontal: no describe la forma del clip --que la app ya
# sabe sola-- sino cuanto ancho se le da al video. Con el otro nombre, ver
# un clip vertical con el boton hundido se leeria como un error.
VISOR_ANCHO = "Ancho"


class _ProjectLabel(QLabel):
    """El nombre del proyecto: doble clic para corregirlo.

    Mismo mecanismo que renombrar un cuarto (doble clic en el rail) --
    Bruno ya lo conoce de ahi."""

    doble_clic = Signal()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self.doble_clic.emit()
        super().mouseDoubleClickEvent(event)


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
    export_manifest_requested = Signal()
    rename_requested = Signal()
    guia_requested = Signal()
    config_requested = Signal()
    proxies_requested = Signal()
    subir_a_drive_requested = Signal()
    traer_de_vuelta_requested = Signal()
    abrir_en_finder_requested = Signal()
    mode_toggled = Signal()
    # el visor ancho: la hoja se esconde en modo clip y el video se lleva su
    # ancho. La barra solo avisa; quien lo aplica y lo guarda es la ventana.
    modo_horizontal_cambiado = Signal(bool)

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
        self.mark.setPixmap(marca.glifo(self.mark.size()))
        self.mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.project_label = _ProjectLabel("")
        self.project_label.setObjectName("projectLabel")
        self.project_label.doble_clic.connect(self.rename_requested)
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

        # El ancho del visor. Va pegado al switch de modo porque son la misma
        # familia: las dos deciden que paneles se ven.
        #
        # Es un boton que se queda hundido y NO un control segmentado, y eso
        # se midio: el segmentado dejaba el minimo de esta barra en 1168 px
        # contra los 1150 que el test de la F7 defiende, y ese minimo se
        # propaga hasta la ventana -- o sea que un control para darle ancho
        # al video terminaba quitandoselo. Un boton cuesta la mitad.
        self._modo_horizontal = False
        self.visor_button = QPushButton(VISOR_ANCHO)
        self.visor_button.setObjectName("railButton")
        self.visor_button.setCheckable(True)
        self.visor_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.visor_button.setToolTip(
            "Ancho: esconde la hoja de contactos en modo clip y le da su "
            "espacio al video. El rail y el estado del clip se quedan.\n"
            "Sirve para material horizontal, donde el video no alcanza a "
            "usar el alto de la ventana.\n"
            "En la hoja no se puede: ahí no hay video al que darle espacio."
        )
        self.visor_button.toggled.connect(self._al_elegir_visor)

        # Aca vivia un boton «Cuartos ⌘R» que solo movia el foco a la
        # primera fila del rail: desde afuera no pasaba nada, y Bruno lo
        # reporto como «no hace nada». El atajo ⌘R sigue existiendo para
        # quien maneja el rail sin mouse; el lugar lo ocupa lo que si es una
        # accion: enganchar los proxies.
        # El engrane va a la IZQUIERDA de todo lo demas: no es una accion
        # del trabajo diario, es donde se pone lo que se pone una vez.
        # Con su nombre y no con un engrane. Se probo el glifo solo y a este
        # tamaño se ve como un puntito al lado de «Proxies» -- y seria el
        # unico dibujo en una barra que es toda palabras.
        self.config_button = _boton("Configuración", "", "railButton")
        self.proxies_button = _boton("Proxies", "", "railButton")
        # Solo se ve si el proyecto tiene una carpeta de iCloud vinculada
        # (spec 2026-09-23-abrir-carpeta-icloud-en-finder-design.md) --
        # empieza escondido, igual que `traer_button`.
        self.icloud_button = _boton("Abrir en Finder", "", "railButton")
        self.icloud_button.hide()
        # A la izquierda de exportar: la guia se arma ANTES de exportar.
        self.guia_button = _boton("Guía de edición", "", "railButton")
        self.export_button = _boton("Exportar a Premiere", "⌘E", "exportButton")
        self.export_menu = QMenu(self)
        accion_manifest = self.export_menu.addAction(
            "Exportar manifest para el plugin (respaldo)")
        accion_manifest.triggered.connect(self.export_manifest_requested.emit)
        self.export_button.setToolTip(
            "Generar el proyecto de Premiere. Clic derecho: exportar el "
            "manifest de respaldo para el plugin.")
        self.export_button.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.export_button.customContextMenuRequested.connect(
            lambda posicion: self.export_menu.exec(
                self.export_button.mapToGlobal(posicion)))
        # Al aparecer «Abrir en Finder», el layout puede repartir el ancho
        # faltante sobre este botón primario y cortar su texto. Su acción
        # debe conservar el ancho mínimo que Qt calcula para el rótulo.
        self.export_button.setMinimumWidth(
            self.export_button.minimumSizeHint().width())

        # La cápsula de entrega cambia sin mover el resto de la barra.
        self.entrega_host = QWidget()
        entrega_layout = QHBoxLayout(self.entrega_host)
        entrega_layout.setContentsMargins(0, 0, 0, 0)
        entrega_layout.setSpacing(8)
        self.entrega_pill = QLabel("")
        self.entrega_pill.setObjectName("entregaPill")
        self.entrega_pill.hide()
        self.subir_button = _boton("Subir a Drive", "", "railButton")
        self.subir_button.clicked.connect(self.subir_a_drive_requested.emit)
        self.traer_button = _boton("Traer de vuelta", "", "exportButton")
        self.traer_button.clicked.connect(self.traer_de_vuelta_requested.emit)
        self.traer_button.hide()
        entrega_layout.addWidget(self.entrega_pill)
        entrega_layout.addWidget(self.subir_button)
        entrega_layout.addWidget(self.traer_button)
        self.proxies_button.clicked.connect(self.proxies_requested.emit)
        self.icloud_button.clicked.connect(self.abrir_en_finder_requested.emit)
        self.export_button.clicked.connect(self.export_requested.emit)
        self.guia_button.clicked.connect(self.guia_requested.emit)
        self.config_button.clicked.connect(self.config_requested.emit)

        layout.addWidget(self.mark)
        layout.addWidget(self.project_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.mode_switch)
        layout.addWidget(self.visor_button)
        layout.addStretch(1)
        layout.addWidget(self.saved_led)
        layout.addWidget(self.saved_label)
        layout.addWidget(self.config_button)
        layout.addWidget(self.proxies_button)
        layout.addWidget(self.icloud_button)
        layout.addWidget(self.guia_button)
        layout.addWidget(self.export_button)
        layout.addWidget(self.entrega_host)

    def set_carpeta_de_icloud_disponible(self, disponible: bool) -> None:
        """Muestra u oculta "Abrir en Finder" -- solo existe una carpeta de
        iCloud que abrir en los proyectos creados con "Con folio…" (spec
        2026-09-23-abrir-carpeta-icloud-en-finder-design.md)."""
        self.icloud_button.setVisible(disponible)

    def set_estado_de_entrega(self, estado: str | None, cuando_texto: str = "") -> None:
        """Dibuja el estado de la entrega de este proyecto."""
        from clasificador_video.entrega import EstadoEntrega

        self.subir_button.setText("Subir a Drive")
        self.subir_button.setEnabled(True)
        self.traer_button.hide()
        self.entrega_pill.hide()
        if estado == EstadoEntrega.CON_EDITOR:
            self.subir_button.setText("Subir de nuevo")
            self.entrega_pill.setText(f"●  Con el editor · {cuando_texto}")
            self.entrega_pill.setProperty("tono", "esperando")
            self.entrega_pill.show()
            self.traer_button.show()
        elif estado == EstadoEntrega.EDITOR_CONTESTO:
            self.subir_button.setText("Subir de nuevo")
            self.entrega_pill.setText(f"✓  El editor ya contestó · {cuando_texto}")
            self.entrega_pill.setProperty("tono", "contesto")
            self.entrega_pill.show()
            self.traer_button.show()
        elif estado == EstadoEntrega.EN_REVISION:
            self.subir_button.setText("Subir de nuevo")
            self.entrega_pill.setText(f"◐  En revisión · {cuando_texto}")
            self.entrega_pill.setProperty("tono", "revision")
            self.entrega_pill.show()
        self.entrega_pill.style().unpolish(self.entrega_pill)
        self.entrega_pill.style().polish(self.entrega_pill)

    def set_subiendo(self, porcentaje: int) -> None:
        """Apaga el botón mientras sube y enseña el avance disponible."""
        self.subir_button.setEnabled(False)
        self.subir_button.setText(f"Subiendo… {porcentaje}%")

    def set_project(self, nombre: str, total_clips: int, bins: int = 0) -> None:
        """El subtitulo decia «Sony FX30» escrito a mano, de cuando todo el
        material de Bruno era de esa camara. Con los bins eso paso a ser
        mentira: lo decia igual con material del dron, y hasta con el
        proyecto vacio. Ahora dice cuantos bins hay, que ademas es el dato
        que cambia mientras trabajas.
        """
        self.project_label.setText(nombre)
        if not total_clips:
            # la pantalla inicial de la app: «0 clips · 0 bins» no le dice
            # nada a nadie, y el cartel del centro de la hoja es el que
            # explica que hacer
            self.subtitle_label.setText("sin material")
            return
        cuantos_bins = f"{bins} {'bin' if bins == 1 else 'bins'}"
        self.subtitle_label.setText(f"{total_clips} clips · {cuantos_bins}")

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
        # El «Ancho» solo habla de lo que pasa en modo CLIP (spec §3): en la
        # hoja no puede mover un pixel, asi que en la hoja no se deja
        # apretar. Se apaga en vez de esconderse para que no baile la barra
        # --y para que se siga viendo hundido si quedo prendido--, y sobre
        # todo porque la app ABRE en la hoja: ahi apretarlo no hacia nada, y
        # como tampoco se veia hundido, dos clics lo dejaban apagado
        # mientras uno creia haberlo prendido.
        self.visor_button.setEnabled(not en_hoja)

    def set_modo_horizontal(self, activo: bool) -> None:
        """Sincroniza el interruptor con el estado. NO emite: es una vista
        del dato, y emitiendo, restaurar un proyecto dispararia el guardado
        que lo puso. Mismo criterio que `set_modo_hoja`."""
        self._modo_horizontal = bool(activo)
        bloqueado = self.visor_button.blockSignals(True)
        self.visor_button.setChecked(self._modo_horizontal)
        self.visor_button.blockSignals(bloqueado)

    def _al_elegir_visor(self, activo: bool) -> None:
        if activo == self._modo_horizontal:
            return
        self._modo_horizontal = activo
        self.modo_horizontal_cambiado.emit(activo)

    def _al_elegir_modo(self, etiqueta: str) -> None:
        # clickear el modo en el que ya estas no hace nada: si emitiera, el
        # click y el `⇥` se contradirian -- clickear `Clip` estando en clip
        # te sacaria a la hoja.
        if etiqueta.startswith(MODO_HOJA) != self._modo_hoja:
            self.mode_toggled.emit()

    def set_saved_seconds(self, segundos: int | None) -> None:
        self._marcar_falla(False)
        self.saved_label.setToolTip("")
        self.saved_label.setText("" if segundos is None else f"Guardado hace {segundos} s")
        self.saved_led.setVisible(segundos is not None)

    def set_no_guardado(self, motivo: str) -> None:
        """El proyecto no se pudo escribir.

        Antes esto no existia y el error se tragaba entero: el indicador
        seguia diciendo «Guardado hace 3 s» toda la sesion mientras nada se
        guardaba. Con la sesion escondida --un archivo en la carpeta del
        usuario, siempre escribible-- casi nunca pasaba; ahora el archivo lo
        elige Bruno y puede estar en un disco externo que se desconecta.

        El motivo va en el tooltip y no en la barra: «Read-only file system»
        no le dice nada a un editor de video, pero es lo primero que hace
        falta si algun dia hay que averiguar por que.
        """
        self.saved_label.setText("No se pudo guardar")
        self.saved_label.setToolTip(motivo)
        self.saved_led.setVisible(True)
        self._marcar_falla(True)

    def _marcar_falla(self, falla: bool) -> None:
        # por propiedad + repolish: es como el resto de la app cambia un
        # color desde QSS sin volver a aplicar la hoja entera
        self.saved_led.setProperty("falla", "true" if falla else "false")
        self.saved_led.style().unpolish(self.saved_led)
        self.saved_led.style().polish(self.saved_led)
