from __future__ import annotations

from PySide6.QtGui import QFont

# ---------------------------------------------------------------------------
# Tokens de diseño. UNICA fuente de valores visuales de la app.
#
# Los valores salen del bloque `:root` de
# docs/superpowers/mockups/rediseno-2026-08-08/mockup.html -- si hay que
# cambiar un color, se cambia primero ahi y luego aqui, nunca al reves y
# nunca en un widget suelto (ver el Candado 1 en
# docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md).
# ---------------------------------------------------------------------------

# --- superficies (de mas oscuro a mas claro) ---
BG_APP = "#0a0b0d"        # fondo de la ventana
BG_SURFACE_0 = "#101216"  # rails y paneles
BG_SURFACE_1 = "#16191e"  # controles en reposo
BG_SURFACE_2 = "#1d2128"  # chips, teclas, elementos activos
LINE = "#262b33"          # bordes visibles
LINE_SOFT = "#1e222a"     # separadores internos

# --- texto ---
TEXT = "#e6e9ee"
TEXT_2 = "#9aa3b0"
TEXT_3 = "#626b78"

# --- ESTADO del clip. Nunca se reusan para identidad de cuarto, para que
# un borde o badge de este color signifique siempre lo mismo en toda la app.
PICK_COLOR = "#55c08a"
STAR_COLOR = "#7ee6b0"     # destacado = pick reforzado, misma familia
REJECT_COLOR = "#d4696c"
CURRENT_COLOR = "#e8a33d"  # clip actual y playhead
TRIM_COLOR = "#6d8cf5"     # rango in/out marcado

# --- IDENTIDAD DE CUARTO: apagada a proposito (nunca verde, rojo ni ambar)
# para no competir visualmente con los colores de estado de arriba.
ROOM_PALETTE = [
    "#c0885a", "#6d8ca8", "#8b7ca8", "#4f9a8e", "#7e9e5e",
    "#3e9bc0", "#a9836f", "#b26f86", "#7c8794",
]

# lo que falta clasificar: el tramo apagado de la barra de progreso y el
# punto gris de la leyenda son el mismo dato, y por eso el mismo color.
PENDING_COLOR = "#2a2f38"

# --- tarjetas de la hoja de contactos ---
# Los alfas van en tuplas, no en cadenas "rgba(...)": QColor no parsea la
# notacion CSS -- QColor("rgba(255,255,255,26)").isValid() es False -- y
# QPainter necesita componentes. Mismo criterio que TRACK_OVER_VIDEO_RGBA.
CARD_BADGE_BG_RGBA = (4, 5, 7, 165)     # pastilla del numero de clip y la duracion
CARD_BADGE_TEXT = "#e4e8ee"
RANGE_TRACK_RGBA = (255, 255, 255, 26)  # riel de la barra de rango, SOBRE la imagen
UNCLASSIFIED_STRIPE = "#3a4150"         # rayado de "sin clasificar"
SELECTION_BORDER = "#8fb4ff"            # borde y palomita de seleccion multiple
SELECTION_TICK_INK = "#0a1024"
# tinta de los glifos de estado: van oscuros SOBRE el color del estado
PICK_INK = "#07130d"
REJECT_INK = "#1b0708"

# --- colores derivados que antes vivian sueltos en otros modulos ---
SELECTION_WASH = "rgba(109, 140, 245, 60)"  # lavado de seleccion multiple
PLAYHEAD_HIGHLIGHT = "#f2bd72"              # brillo superior del playhead
TICK_MINOR_COLOR = "#2e343d"
TICK_MAJOR_COLOR = "#454d59"
# fondos de los controles que flotan sobre el video. Semitransparentes
# para que la imagen se siga viendo detras -- validado en la F0: el alfa
# se mezcla contra los pixeles del video, no contra negro.
OVERLAY_BG = "rgba(10, 12, 15, 175)"
OVERLAY_BORDER = "rgba(255, 255, 255, 40)"
OVERLAY_SCRIM_FROM = "rgba(0, 0, 0, 0)"
OVERLAY_SCRIM_TO = "rgba(0, 0, 0, 200)"
# riel de la scrub bar cuando va ENCIMA del video: un color solido se veria
# como una banda opaca tapando la imagen (ver ScrubBar.set_over_video).
TRACK_OVER_VIDEO_RGBA = (255, 255, 255, 33)

# --- dimensiones fijas del layout (px) ---
TITLEBAR_HEIGHT = 36
STATUSBAR_HEIGHT = 24
RAIL_WIDTH = 200
TOOLCOL_WIDTH = 56
SHEET_MIN_WIDTH = 340
OVERLAY_MARGIN = 13       # margen de los controles flotantes sobre el video
SCRUB_HEIGHT = 26
# El segmento activo de VELOCIDAD va en ambar, no en el gris del resto de los
# controles segmentados (el mockup los separa: `.seg b.on` contra
# `.seg.speed b.on`). No es decoracion: reproducir a 2x o 4x cambia lo que
# estas viendo y es facil olvidarlo, asi que el estado tiene que gritar.
SPEED_ON_ALPHA = 77       # rgba(232,163,61,.3) del mockup
SPEED_ON_TEXT_MIX = 0.5
# Fondo de los controles que flotan sobre el video. Translucido a proposito,
# como en el mockup (`rgba(10,12,15,.6)`): opaco taparia imagen, y sin fondo
# los numeros claros desaparecen sobre una pared blanca.
OVERLAY_BOX_ALPHA = 153   # 0.6 * 255
# --- la banda de reproduccion (ScrubBar) ---
# Lo que queda FUERA del rango marcado se apaga: el rango no solo se pinta,
# tambien se baja lo que no vas a usar. `rgba(0,0,0,.42)` del mockup.
SCRUB_OUTSIDE_RGBA = (0, 0, 0, 107)
# Relleno de la zona marcada. Translucido a proposito: encima va la imagen.
SCRUB_TRIM_FILL_ALPHA = 107      # rgba(109,140,245,.42)
SCRUB_HANDLE_WIDTH = 2
SCRUB_TICKS_HEIGHT = 6           # las marcas viven abajo, como en el mockup
SCRUB_RADIUS = 4
HANDLE_LABEL_PX = 9        # la letra I/O de las manijas, en pixeles
# Las marcas de tiempo tienen DOS juegos de color, por el mismo motivo que el
# riel: TICK_*_COLOR son grises oscuros pensados para fondo oscuro, y sobre el
# video --donde la banda es translucida y la imagen puede ser una pared
# blanca-- se leen como rayas negras. El mockup las pone claras.
TICK_MAJOR_OVER_VIDEO_RGBA = (255, 255, 255, 36)   # rgba(255,255,255,.14)
TICK_MINOR_OVER_VIDEO_RGBA = (255, 255, 255, 20)

# --- radios ---
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8

# --- tipografia ---
# Enteros a proposito: QSS no interpreta de forma confiable tamaños
# fraccionarios de fuente, y los medios pixeles del mockup no aportan nada.
FONT_MICRO = 9      # etiquetas en mayusculas con tracking
FONT_SMALL = 11     # hints y metadata secundaria
FONT_BODY = 12      # texto normal
FONT_TITLE = 13     # nombre de proyecto
FONT_TIMECODE = 19  # timecode sobre el video
FONT_BIG = 24       # numero grande de progreso

LETTER_SPACING_CAPS = 1.2  # tracking de las etiquetas en mayusculas

# Menlo primero a proposito: viene en toda Mac desde 10.6, asi que resuelve
# de inmediato. El mockup encabeza con "SF Mono", que NO esta expuesta con
# ese nombre en macOS -- Qt la busca, no la encuentra, y paga ~370 ms de
# populacion de alias de fuentes en cada arranque. Medido el 2026-08-08.
MONO_FONT = 'Menlo, "SF Mono", "JetBrains Mono", monospace'



def room_color(index: int) -> str:
    """Color de identidad estable para el cuarto en la posicion `index`
    de la lista de cuartos activos -- mismo indice, mismo color siempre,
    para que la identidad visual de un cuarto no cambie durante la sesion.
    """
    return ROOM_PALETTE[index % len(ROOM_PALETTE)]


def aclarar(color_hex: str, factor: float) -> str:
    """Mezcla un color con blanco. El badge de cuarto sobre el video lleva el
    texto en una version clara del color de ese cuarto: el mockup la eligio a
    mano para el primero (#c0885a -> #e3b98f) y esto la deriva para los nueve.
    Sale un poco menos saturada que la del mockup -- mezclar con blanco baja
    la saturacion -- y es una diferencia asumida a cambio de no escribir nueve
    colores a mano que despues nadie mantiene.
    """
    color_hex = color_hex.lstrip("#")
    canales = [int(color_hex[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(c + (255 - c) * factor):02x}" for c in canales)


def con_alfa(color_hex: str, alfa: int) -> tuple[int, int, int, int]:
    """Color de token mas alfa, listo para `QColor(*...)`."""
    color_hex = color_hex.lstrip("#")
    return (*(int(color_hex[i:i + 2], 16) for i in (0, 2, 4)), alfa)


def con_alfa_qss(color_hex: str, alfa: int) -> str:
    """Lo mismo, pero en la notacion que entiende QSS.

    Vive aca y no en el widget que la usa a proposito: el Candado 1 prohibe
    declarar color fuera de este archivo, y armar la cadena en el widget
    seria exactamente eso aunque los numeros vengan de un token.
    """
    r, g, b, a = con_alfa(color_hex, alfa)
    return f"rgba({r}, {g}, {b}, {a})"


def apply_letter_spacing(widget, px: float = LETTER_SPACING_CAPS) -> None:
    """QSS no tiene `letter-spacing`: el tracking de las etiquetas en
    mayusculas del mockup solo se puede aplicar por QFont desde codigo.
    """
    font = widget.font()
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, px)
    widget.setFont(font)


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {BG_APP};
        color: {TEXT};
        font-size: {FONT_BODY}px;
    }}

    QListWidget {{
        background-color: {BG_SURFACE_0};
        border: 1px solid {LINE};
        border-radius: {RADIUS_SM}px;
        padding: 6px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: 3px;
        margin-bottom: 2px;
    }}
    QListWidget::item:selected {{
        background-color: {BG_SURFACE_2};
        color: {CURRENT_COLOR};
    }}

    QPushButton {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: 3px;
        padding: 8px 14px;
        color: {TEXT};
    }}
    QPushButton:hover {{
        background-color: {BG_SURFACE_0};
    }}
    QPushButton:checked {{
        background-color: {BG_SURFACE_2};
        border-color: {CURRENT_COLOR};
        color: {CURRENT_COLOR};
    }}

    QPushButton#startButton, QPushButton#exportButton {{
        background-color: {CURRENT_COLOR};
        color: {BG_APP};
        font-weight: 700;
        border: none;
        padding: 10px 16px;
    }}
    QPushButton#startButton:hover, QPushButton#exportButton:hover {{
        background-color: {PLAYHEAD_HIGHLIGHT};
    }}

    QPushButton#importButton {{
        background-color: transparent;
        border: 1px dashed {LINE};
        color: {TEXT_2};
    }}
    QPushButton#importButton:hover {{
        background-color: {BG_SURFACE_1};
    }}

    QComboBox, QLineEdit {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: 3px;
        padding: 4px 8px;
        color: {TEXT};
    }}

    QLabel#legendLabel, QLabel#statusLabel, QLabel#scrubTimeLabel {{
        color: {TEXT_2};
        font-size: {FONT_SMALL}px;
        font-family: {MONO_FONT};
    }}
    QLabel#clipRoomLabel {{
        color: {TEXT_2};
        font-size: {FONT_MICRO}px;
        font-family: {MONO_FONT};
    }}
    QLabel#panelTitle {{
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
        text-transform: uppercase;
        font-weight: 700;
    }}
    QPushButton#unclassifiedBadge {{
        background-color: transparent;
        border: none;
        /* la regla generica de QPushButton trae `padding: 8px 14px`: en una
           barra de 24 px eso lo recorta entero */
        padding: 0px;
        color: {CURRENT_COLOR};
        font-size: {FONT_SMALL}px;
        text-align: left;
    }}
    QPushButton#unclassifiedBadge:hover {{
        color: {PLAYHEAD_HIGHLIGHT};
        text-decoration: underline;
    }}
    QLabel#savedIndicator {{
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
    }}
    QLabel#positionLabel {{
        color: {TEXT};
        font-family: {MONO_FONT};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#inspectorRoomLabel {{
        color: {CURRENT_COLOR};
        font-weight: 600;
        font-size: {FONT_TITLE}px;
    }}
    QWidget#clipListRow {{
        border-bottom: 1px solid {LINE};
    }}
    QWidget#clipListRow:hover {{
        background-color: {BG_SURFACE_1};
    }}
    QLabel#clipListName {{
        font-family: {MONO_FONT};
        font-size: {FONT_SMALL}px;
        color: {TEXT};
    }}
    QLabel#roomKeycap {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: 3px;
        color: {TEXT_2};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    QProgressBar#roomCountBar {{
        background-color: {BG_SURFACE_1};
        border: none;
        border-radius: 1px;
    }}
    QProgressBar#roomCountBar::chunk {{
        background-color: {BG_SURFACE_2};
        border-radius: 1px;
    }}
    QWidget#historyPanel {{
        border-top: 1px solid {LINE_SOFT};
    }}
    QWidget#histRow[top="true"] {{
        background-color: {con_alfa_qss(CURRENT_COLOR, 18)};
        border-left: 2px solid {CURRENT_COLOR};
    }}
    QLabel#histWhat {{
        background-color: transparent;
        color: {TEXT};
        font-size: {FONT_SMALL}px;
        font-weight: 600;
    }}
    QLabel#histDetail {{
        background-color: transparent;
        color: {TEXT_2};
        font-size: {FONT_SMALL}px;
    }}
    QPushButton#histUndo {{
        background-color: transparent;
        border: none;
        /* sin esto hereda `padding: 8px 14px` de la regla generica de
           QPushButton: el sizeHint se va a 38x29, el boton esta fijo en
           18x18 y el glifo se recorta entero -- no se ve nada. */
        padding: 0px;
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
    }}
    QPushButton#histUndo:hover {{
        color: {TEXT};
    }}

    QPushButton#newRoomRow {{
        background-color: transparent;
        border: 1px dashed {LINE};
        border-radius: {RADIUS_MD}px;
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
        text-align: left;
        padding: 0 6px;
    }}
    QPushButton#newRoomRow:hover {{
        background-color: {BG_SURFACE_1};
        color: {TEXT_2};
    }}

    /* Los dos nombres comparten la caja: el de velocidad solo se separa en
       el color del segmento activo (ver mas abajo). Si esta regla nombrara
       solo a `segmentedControl`, el de velocidad se quedaria sin su fondo
       oscuro y los numeros flotarian ilegibles sobre el video -- paso al
       construirlo. */
    QWidget#segmentedControl, QWidget#speedSegmented {{
        background-color: {con_alfa_qss(BG_APP, OVERLAY_BOX_ALPHA)};
        border: 1px solid {LINE};
        border-radius: {RADIUS_MD}px;
    }}
    QPushButton#segmentedButton {{
        background-color: transparent;
        border: none;
        border-right: 1px solid {LINE_SOFT};
        border-radius: 0px;
        padding: 4px 9px;
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
        font-weight: 500;
    }}
    QPushButton#segmentedButton:checked {{
        background-color: {BG_SURFACE_2};
        color: {TEXT};
    }}
    /* selector de descendencia: el control de velocidad lleva su propio
       objectName y sus botones siguen siendo `segmentedButton`, asi que
       heredan todo menos el color del segmento activo. */
    QWidget#speedSegmented QPushButton#segmentedButton:checked {{
        background-color: {con_alfa_qss(CURRENT_COLOR, SPEED_ON_ALPHA)};
        color: {aclarar(CURRENT_COLOR, SPEED_ON_TEXT_MIX)};
    }}

    QWidget#titleBar {{
        background-color: {BG_SURFACE_0};
        border-bottom: 1px solid {LINE};
    }}
    QLabel#appMark {{
        background-color: {CURRENT_COLOR};
        border-radius: {RADIUS_SM}px;
    }}
    QLabel#projectLabel {{
        color: {TEXT};
        font-size: {FONT_TITLE}px;
        font-weight: 600;
    }}
    QLabel#projectSubtitle {{
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#savedLed {{
        background-color: {PICK_COLOR};
        border-radius: 3px;
    }}
    QPushButton#railButton {{
        background-color: {BG_SURFACE_2};
        border: 1px solid {LINE};
        border-radius: {RADIUS_MD}px;
        padding: 4px 11px;
        color: {TEXT};
        font-size: {FONT_SMALL}px;
        font-weight: 550;
    }}
    QPushButton#railButton:hover {{
        background-color: {BG_SURFACE_1};
    }}

    QWidget#statusBar {{
        background-color: {BG_SURFACE_0};
        border-top: 1px solid {LINE};
    }}
    QLabel#statusMono {{
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}

    QWidget#roomRail {{
        background-color: {BG_SURFACE_0};
        border-right: 1px solid {LINE};
    }}
    QWidget#railProgress, QWidget#railSectionHeader {{
        border-bottom: 1px solid {LINE_SOFT};
    }}
    QLabel#railHeader {{
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
        font-weight: 650;
    }}
    QLabel#progressBig {{
        color: {TEXT};
        font-family: {MONO_FONT};
        font-size: {FONT_BIG}px;
        font-weight: 600;
    }}
    QLabel#progressTotal {{
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_SMALL}px;
    }}
    QWidget#roomRow {{
        border-radius: {RADIUS_MD}px;
    }}
    QWidget#roomRow[actual="true"] {{
        background-color: {BG_SURFACE_2};
    }}
    /* `⌘R` trae el foco aca: sin marca visible no se sabe sobre que fila
       actuan ⏎, ⌫ y ⌥↑/⌥↓ */
    QWidget#roomRow:focus {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {CURRENT_COLOR};
    }}
    /* transparentes a proposito: la regla global de QWidget les pinta el
       fondo de la app, y sobre la fila resaltada del cuarto actual eso se
       ve como recuadros oscuros alrededor del nombre y del conteo. */
    QLabel#roomName {{
        background-color: transparent;
        color: {TEXT};
        font-size: {FONT_BODY}px;
    }}
    QLabel#roomCount {{
        background-color: transparent;
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    QLabel#keyCap {{
        background-color: {BG_SURFACE_2};
        border: 1px solid {LINE};
        border-radius: {RADIUS_SM}px;
        color: {TEXT_2};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
        font-weight: 600;
    }}
    QLabel#keyCap[sin_tecla="true"] {{
        background-color: transparent;
        color: transparent;
    }}

    QWidget#toolColumn {{
        background-color: {BG_SURFACE_0};
        border-left: 1px solid {LINE};
        border-right: 1px solid {LINE};
    }}
    QLabel#toolCaption {{
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
        font-weight: 650;
    }}
    QLabel#toolHint {{
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    QWidget#toolIndicator {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_LG}px;
    }}
    QWidget#toolIndicator QLabel {{
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
        font-weight: 650;
    }}
    QWidget#toolIndicator[on="true"][canal="rango"] {{
        border-color: {TRIM_COLOR};
    }}
    QWidget#toolIndicator[on="true"][canal="rango"] QLabel {{
        color: {TRIM_COLOR};
    }}
    QWidget#toolIndicator[on="true"][canal="pick"] {{
        border-color: {PICK_COLOR};
    }}
    QWidget#toolIndicator[on="true"][canal="pick"] QLabel {{
        color: {PICK_COLOR};
    }}
    QWidget#toolIndicator[on="true"][canal="reject"] {{
        border-color: {REJECT_COLOR};
    }}
    QWidget#toolIndicator[on="true"][canal="reject"] QLabel {{
        color: {REJECT_COLOR};
    }}

    QWidget#toolDivider {{
        background-color: {LINE};
    }}
    QPushButton#toolButton {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_LG}px;
        padding: 0px;
    }}
    QPushButton#toolButton:hover:enabled {{
        border-color: {CURRENT_COLOR};
    }}
    QPushButton#toolButton QLabel {{
        background-color: transparent;
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
        font-weight: 650;
    }}
    QPushButton#toolButton:enabled QLabel#toolButtonGlyph {{
        color: {TEXT_2};
        font-size: {FONT_BODY}px;
    }}
    QPushButton#toolButton:!enabled {{
        border-color: {LINE_SOFT};
    }}

    QWidget#clipSheet {{
        background-color: {BG_SURFACE_0};
    }}
    QWidget#sheetHeader {{
        background-color: {BG_SURFACE_0};
        border-bottom: 1px solid {LINE_SOFT};
    }}
    QLineEdit#sheetSearch {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_MD}px;
        padding: 0 9px;
        color: {TEXT};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#filterGroupLabel {{
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
        font-weight: 650;
    }}
    QWidget#filterDivider {{
        background-color: {LINE};
    }}
    QPushButton#filterChip {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: 5px;
        padding: 3px 8px;
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
        font-weight: 400;
    }}
    QPushButton#filterChip:hover {{
        color: {TEXT_2};
    }}
    QPushButton#filterChip:checked {{
        background-color: {BG_SURFACE_2};
        border-color: {LINE};
        color: {TEXT};
    }}
    /* el chip activo que SI filtra lleva el color de la cola: es el mismo
       ambar del chip `cola de ←→`, del playhead y del clip actual */
    QPushButton#filterChip:checked[q="true"] {{
        background-color: {con_alfa_qss(CURRENT_COLOR, 33)};
        border-color: {con_alfa_qss(CURRENT_COLOR, 115)};
        color: {PLAYHEAD_HIGHLIGHT};
    }}
    QLabel#queueChip {{
        background-color: {con_alfa_qss(CURRENT_COLOR, 26)};
        border: 1px solid {con_alfa_qss(CURRENT_COLOR, 77)};
        border-radius: 5px;
        padding: 3px 9px;
        color: {PLAYHEAD_HIGHLIGHT};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#sheetHint {{
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
    }}
    QLabel#groupTitle {{
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
        font-weight: 650;
    }}
    QWidget#groupLine {{
        background-color: {LINE_SOFT};
    }}
    QLabel#groupCount {{
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    QLabel#sheetFade {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {OVERLAY_SCRIM_FROM}, stop:1 {BG_SURFACE_0});
        border: none;
    }}
    QWidget#clipCard {{
        background-color: {BG_SURFACE_2};
        border-radius: {RADIUS_MD}px;
    }}
    QLabel#clipCardImage {{
        background-color: {BG_SURFACE_1};
        border: none;
    }}

    QLabel#overlayScrim {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {OVERLAY_SCRIM_FROM}, stop:1 {OVERLAY_SCRIM_TO});
        border: none;
    }}
    /* El de arriba va al reves: opaco en el borde y transparente hacia
       abajo, para que el nombre de archivo y los badges se lean sobre
       cualquier imagen sin meterlos en pastillas. */
    QLabel#overlayTopScrim {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {OVERLAY_SCRIM_TO}, stop:1 {OVERLAY_SCRIM_FROM});
        border: none;
    }}
    /* `background-color: transparent` NO es redundante: la regla global
       `QWidget` de arriba pinta fondo opaco en TODO, incluidas las QLabel.
       Sin esta linea cada etiqueta del pie sale con su propia caja negra
       encima del video -- pasa al construir el pie de la F6. */
    QLabel#overlayFrame {{
        background-color: transparent;
        color: {TEXT_2};
        font-family: {MONO_FONT};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#overlayInOut {{
        background-color: transparent;
        color: {aclarar(TRIM_COLOR, 0.45)};
        font-family: {MONO_FONT};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#overlayKeys {{
        background-color: transparent;
        color: {TEXT_2};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#rangePill {{
        background-color: {con_alfa_qss(TRIM_COLOR, 46)};
        border: 1px solid {con_alfa_qss(TRIM_COLOR, 102)};
        border-radius: {RADIUS_SM}px;
        padding: 3px 7px;
        color: {aclarar(TRIM_COLOR, 0.45)};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    /* Sin pastilla a proposito: el mockup lo pone como texto sobre el
       degradado de arriba (`overlayTopScrim`). Una pastilla mas encima del
       scrim son dos fondos apilados para el mismo texto. */
    QLabel#overlayFile {{
        background-color: transparent;
        padding: 5px 10px;
        color: {TEXT};
        font-family: {MONO_FONT};
        font-size: {FONT_BODY}px;
        font-weight: 600;
    }}
    QLabel#overlayBadges {{
        background-color: {OVERLAY_BG};
        border: 1px solid {OVERLAY_BORDER};
        border-radius: {RADIUS_SM}px;
        padding: 4px 8px;
        color: {TEXT_2};
        font-size: {FONT_MICRO}px;
        font-weight: 700;
    }}
    QLabel#overlayTimecode {{
        background-color: transparent;
        border: none;
        color: white;
        font-family: {MONO_FONT};
        font-size: {FONT_TIMECODE}px;
        font-weight: 700;
    }}

    QWidget#videoWidget {{
        background-color: black;
        border: 1px solid {LINE};
        border-radius: 3px;
    }}

    QWidget#scrubBar {{
        background-color: {BG_SURFACE_0};
        border-radius: 3px;
    }}

    """
