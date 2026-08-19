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

# --- IDENTIDAD DE BIN: la marca de camara del encabezado de la hoja
# (`.bin .cam` del mockup de bins). Es un canal mas, aparte de los colores
# de estado y de los de cuarto, y se usa SIEMPRE al 18% de opacidad detras
# de un glifo aclarado: asi la marca se lee como pertenencia y no compite
# con la franja del cuarto, que va a plena saturacion sobre la miniatura.
# Los tres primeros son EXACTAMENTE los que el mockup dibujo y Bruno aprobo
# viendolos; los dos ultimos siguen el mismo criterio para cuando haya mas
# de tres bins. Que se parezcan a ROOM_PALETTE no es un descuido: el mockup
# tomo de ahi a proposito, y lo que separa los dos canales es el
# tratamiento, no la tinta.
BIN_PALETTE = ["#3e9bc0", "#c0885a", "#7c8794", "#8b7ca8", "#4f9a8e"]
BIN_TINT_ALPHA = 46          # el .18 del mockup, en 0-255
BIN_INK_LIGHTEN = 0.45       # cuanto se aclara el glifo sobre ese tinte

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
# Grosor del borde de estado de la tarjeta (actual / seleccionada /
# pick / reject). Es el token que faltaba: el valor vivia escrito en la
# regla de QSS que nunca llegaba al pixel.
CARD_STATE_BORDER = 2
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
# El visor mas angosto con el que la ventana todavia sirve. NO es un limite
# del visor --su ancho lo manda la forma del clip-- sino el sumando que le
# toca dentro del ancho MINIMO de la ventana (ver `MainWindow.__init__`).
VIDEO_MIN_WIDTH = 260
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
# La fila fija de `S` en el rail, en ambar tenue (mockup: `.same`).
SAME_ROW_BG_ALPHA = 23      # rgba(232,163,61,.09)
SAME_ROW_BORDER_ALPHA = 71  # rgba(232,163,61,.28)
SAME_ROW_KEY_ALPHA = 46     # rgba(232,163,61,.18)
SAME_ROW_TAG_ALPHA = 204    # rgba(232,163,61,.8)
# El rastro del pincel: un lavado del color del cuarto sobre la miniatura
# (`.card.painted` del mockup, rgba(126,158,94,.2)). Es del GESTO, no del
# clip: se va al soltar la tecla.
BRUSH_TINT_ALPHA = 51
# La barra de seleccion multiple (`.batch` del mockup).
BATCH_BG = "#1a2130"
BATCH_BORDER = "#2e3b57"
# La paleta `⏎` tapa video a proposito: se esta leyendo una lista.
PALETTE_BG = "rgba(20, 23, 28, 247)"     # rgba(20,23,28,.97) del mockup
PALETTE_BORDER = "#333c4a"
# Las marcas de tiempo tienen DOS juegos de color, por el mismo motivo que el
# riel: TICK_*_COLOR son grises oscuros pensados para fondo oscuro, y sobre el
# video --donde la banda es translucida y la imagen puede ser una pared
# blanca-- se leen como rayas negras. El mockup las pone claras.
TICK_MAJOR_OVER_VIDEO_RGBA = (255, 255, 255, 36)   # rgba(255,255,255,.14)
TICK_MINOR_OVER_VIDEO_RGBA = (255, 255, 255, 20)

# La marca de camara del bin. Vive aqui y no en la hoja porque la usan las
# DOS vistas --el encabezado del bin y la etiqueta del visor-- y es el mismo
# dato: si en una fuera un cuadro y en la otra un triangulo, no se
# reconoceria como lo mismo.
MARCA_DE_BIN = "■"

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
# La de interfaz. Solo hace falta declararla donde hay que DESHACER la
# monoespaciada de una regla mas general (el switch de modo, cuyos botones
# son `segmentedButton` y heredan la mono de la velocidad y la calidad).
SANS_FONT = '-apple-system, "Helvetica Neue", sans-serif'



def room_color(index: int) -> str:
    """Color de identidad estable para el cuarto en la posicion `index`
    de la lista de cuartos activos -- mismo indice, mismo color siempre,
    para que la identidad visual de un cuarto no cambie durante la sesion.
    """
    return ROOM_PALETTE[index % len(ROOM_PALETTE)]


def bin_color(index: int) -> str:
    """Color de identidad del bin en la posicion `index`. Ver `BIN_PALETTE`."""
    return BIN_PALETTE[index % len(BIN_PALETTE)]


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

    /* `inicioPrimario` --«Proyecto nuevo»-- comparte la regla en vez de
       tener la suya: es el mismo papel, la accion principal de su pantalla,
       y dos reglas gemelas se despintan una sin la otra. */
    QPushButton#startButton, QPushButton#exportButton, QPushButton#inicioPrimario {{
        background-color: {CURRENT_COLOR};
        color: {BG_APP};
        font-weight: 700;
        border: none;
        padding: 10px 16px;
    }}
    QPushButton#startButton:hover, QPushButton#exportButton:hover,
    QPushButton#inicioPrimario:hover {{
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

    /* el switch `Clip | Hoja` de la barra de titulo: mismo control
       segmentado, pero NO flota sobre el video, asi que su caja es opaca
       --sin el alfa que los otros dos necesitan para leerse contra una
       pared blanca-- y su texto va en la fuente de interfaz, no en la
       monoespaciada de los numeros de velocidad y calidad. */
    QWidget#modeSwitch {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_MD}px;
    }}
    QWidget#modeSwitch QPushButton#segmentedButton {{
        font-family: {SANS_FONT};
        font-size: {FONT_SMALL}px;
        font-weight: 550;
        padding: 4px 10px;
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
    /* el mismo punto, en rojo, cuando el proyecto NO se pudo escribir: verde
       y rojo en el mismo lugar se comparan de un vistazo, que es justo lo
       que hace falta para notar que algo dejo de guardarse */
    QLabel#savedLed[falla="true"] {{
        background-color: {REJECT_COLOR};
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
    QLabel#legendCount {{
        background-color: transparent;
        color: {TEXT_3};
        font-family: {SANS_FONT};
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
    /* La fila fija de `S`. Va en ambar --el color del acento-- y no con el
       color de un cuarto: no es un cuarto mas de la lista, es un atajo a lo
       que hiciste recien. El mockup la separa con la misma intencion. */
    QWidget#sameRow {{
        background-color: {con_alfa_qss(CURRENT_COLOR, SAME_ROW_BG_ALPHA)};
        border: 1px solid {con_alfa_qss(CURRENT_COLOR, SAME_ROW_BORDER_ALPHA)};
        border-radius: {RADIUS_MD}px;
    }}
    QWidget#sameRow QLabel#keyCap {{
        background-color: {con_alfa_qss(CURRENT_COLOR, SAME_ROW_KEY_ALPHA)};
        border: 1px solid {con_alfa_qss(CURRENT_COLOR, SAME_ROW_BORDER_ALPHA)};
        color: {CURRENT_COLOR};
    }}
    QWidget#sameRow QLabel#roomCount {{
        color: {con_alfa_qss(CURRENT_COLOR, SAME_ROW_TAG_ALPHA)};
    }}
    QLabel#sameCaption {{
        color: {con_alfa_qss(CURRENT_COLOR, SAME_ROW_TAG_ALPHA)};
        font-size: {FONT_MICRO}px;
        font-weight: 650;
        padding: 3px 6px 4px;
    }}
    /* La paleta `⏎`. Flota sobre el video, asi que su fondo es casi opaco:
       aqui SI hay que tapar imagen, porque estas leyendo una lista. */
    QWidget#roomPalette {{
        background-color: {PALETTE_BG};
        border: 1px solid {PALETTE_BORDER};
        border-radius: {RADIUS_LG}px;
    }}
    QWidget#palInput {{
        border-bottom: 1px solid {LINE_SOFT};
        background-color: transparent;
    }}
    QLineEdit#palQuery {{
        background-color: transparent;
        border: none;
        color: {TEXT};
        font-family: {MONO_FONT};
        font-size: {FONT_TITLE}px;
    }}
    QLabel#palScope {{
        background-color: transparent;
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
    }}
    QWidget#palOption {{
        background-color: transparent;
    }}
    QWidget#palOption[activa="true"] {{
        background-color: {BG_SURFACE_2};
    }}
    QWidget#palOption QLabel {{
        background-color: transparent;
    }}
    QLabel#palName {{
        color: {TEXT};
        font-size: {FONT_BODY}px;
    }}
    /* crear va en verde --el color de pick-- porque es la accion que SUMA */
    QLabel#palCreate {{
        background-color: transparent;
        border-top: 1px solid {LINE_SOFT};
        color: {PICK_COLOR};
        font-size: {FONT_BODY}px;
        padding: 8px 12px;
    }}
    QLabel#palFoot {{
        background-color: transparent;
        border-top: 1px solid {LINE_SOFT};
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
        padding: 7px 12px;
    }}
    /* La barra de seleccion multiple. Va en el azul del rango --el color de
       "esto es un conjunto marcado"-- y no en el ambar de la cola: son cosas
       distintas y compartir color las haria parecer lo mismo. */
    QWidget#batchBar {{
        background-color: {BATCH_BG};
        border: 1px solid {BATCH_BORDER};
        border-radius: {RADIUS_LG}px;
    }}
    QLabel#batchCount {{
        background-color: transparent;
        color: {aclarar(TRIM_COLOR, 0.55)};
        font-size: {FONT_SMALL}px;
        font-weight: 650;
    }}
    QLabel#batchHint {{
        background-color: transparent;
        color: {TEXT_2};
        font-size: {FONT_MICRO}px;
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
    /* transparente NO es redundante: la regla global `QWidget` de arriba
       pinta fondo opaco en todo, incluidas las QLabel. Estas dos llenan el
       cuadro entero, asi que tapaban su fondo, su borde y sus esquinas
       redondeadas -- la columna se veia como texto suelto en vez de los
       cuadros del mockup. Venia asi desde la F2. */
    QWidget#toolIndicator QLabel {{
        background-color: transparent;
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
    QWidget#toolIndicator[on="true"][canal="star"] {{
        background-color: {con_alfa_qss(STAR_COLOR, 36)};
        border-color: {con_alfa_qss(STAR_COLOR, 153)};
    }}
    QWidget#toolIndicator[on="true"][canal="star"] QLabel {{
        color: {STAR_COLOR};
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
    /* «+ Bin nuevo» (F8). Se ve como el buscador que tiene al lado --mismo
       fondo, mismo borde, mismo radio-- y no como un boton de acento: crear
       un bin es rutina, no la accion principal de la pantalla. */
    QPushButton#sheetNewBin {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_MD}px;
        /* 8 y no 11: al encogerse a un cuadrado, el relleno es lo unico que
           le deja lugar al glifo -- con 11 por lado quedaba una caja vacia */
        padding: 0 8px;
        color: {TEXT_2};
        font-size: {FONT_SMALL}px;
    }}
    QPushButton#sheetNewBin:hover {{
        background-color: {BG_SURFACE_2};
        color: {TEXT};
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
    /* --- el encabezado de bin (F4). La propuesta A del mockup: el bin
       manda arriba y el cuarto baja a subgrupo, asi que este encabezado
       pesa mas que el `groupTitle` de abajo -- fondo, borde y nombre en
       tipografia normal contra las mayusculas apagadas del cuarto. */
    QWidget#binHeader {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_LG}px;
    }}
    /* el encabezado PEGADO arriba: sin sombra --ver el comentario en
       clip_sheet.py-- pero con el borde subido, que es lo otro que el
       mockup le cambia al `.bin.stuck`. */
    QWidget#binHeader[pegado="true"] {{
        background-color: {BG_SURFACE_2};
        border: 1px solid {aclarar(LINE, 0.18)};
    }}
    QWidget#binHeader[colapsado="true"] {{
        background-color: {BG_SURFACE_0};
    }}
    /* `background-color: transparent` NO es redundante: la regla global de
       QWidget le pone BG_APP a todo, y sobre el fondo mas claro del
       encabezado cada etiqueta se dibujaba como una cajita oscura. */
    QLabel#binChevron {{
        background-color: transparent;
        color: {TEXT_2};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#binName {{
        background-color: transparent;
        color: {TEXT};
        font-size: {FONT_SMALL}px;
        font-weight: 650;
    }}
    QLineEdit#binNameEdit {{
        background-color: {BG_SURFACE_2};
        border: 1px solid {CURRENT_COLOR};
        border-radius: {RADIUS_SM}px;
        padding: 0 5px;
        color: {TEXT};
        font-size: {FONT_SMALL}px;
        font-weight: 650;
    }}
    QLabel#binSource {{
        background-color: transparent;
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    QLabel#binCount {{
        background-color: transparent;
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    /* La insignia de proxies cambia de color con lo que dice: verde cuando
       calzaron todos, ambar cuando faltan --el «21/23» del mockup, que es a
       proposito visible-- y apagada cuando no hay ninguno. */
    QLabel#binProxyBadge {{
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
        padding: 2px 7px;
        border-radius: {RADIUS_SM}px;
        border: 1px solid {LINE};
        background-color: {BG_SURFACE_2};
        color: {TEXT_3};
    }}
    QLabel#binProxyBadge[estado="completo"] {{
        border: 1px solid {PICK_COLOR};
        color: {aclarar(PICK_COLOR, 0.35)};
    }}
    QLabel#binProxyBadge[estado="parcial"] {{
        border: 1px solid {CURRENT_COLOR};
        color: {aclarar(CURRENT_COLOR, 0.35)};
    }}
    /* Mientras se generan. Va con el ambar de «esto esta pasando ahora»
       --el mismo canal que el clip actual-- y no con el verde de pick: el
       verde dice «listo», y aqui todavia no. Se distingue de «parcial»
       por el texto, que dice «creando proxies · 7/23». */
    QLabel#binProxyBadge[estado="generando"] {{
        border: 1px solid {CURRENT_COLOR};
        background-color: {BG_SURFACE_2};
        color: {aclarar(CURRENT_COLOR, 0.45)};
    }}
    QPushButton#binMore {{
        background-color: {BG_SURFACE_2};
        border: 1px solid {LINE};
        border-radius: {RADIUS_SM}px;
        color: {TEXT_2};
        font-size: {FONT_SMALL}px;
        padding: 0;
    }}
    QPushButton#binMore:hover {{
        background-color: {BG_SURFACE_1};
        color: {TEXT};
    }}
    /* --- arrastrar material a la hoja (F5), pantalla 4 del mockup ---
       Dos zonas y dos colores, a proposito: VERDE es «se suma a este bin»
       --el mismo verde del pick, o sea «esto ya tiene lugar»-- y AMBAR es
       «nace un bin nuevo», el color con el que la app marca lo que todavia
       no esta resuelto. Con un solo color habria que leer el texto para
       saber que va a pasar al soltar. */
    QWidget#binHeader[soltando="true"] {{
        background-color: {con_alfa_qss(PICK_COLOR, 18)};
        border: 1px dashed {con_alfa_qss(PICK_COLOR, 153)};
    }}
    QLabel#binDropHint {{
        background-color: transparent;
        color: {aclarar(PICK_COLOR, 0.35)};
        font-size: {FONT_SMALL}px;
        font-weight: 650;
    }}
    QWidget#dropNew {{
        background-color: {con_alfa_qss(CURRENT_COLOR, 18)};
        border: 1px dashed {con_alfa_qss(CURRENT_COLOR, 90)};
        border-radius: {RADIUS_LG}px;
    }}
    /* encendida = el cursor esta sobre ella. Sin este segundo estado, la
       zona se veria igual estando el cursor sobre un bin, y prometeria un
       bin nuevo que no se va a crear. */
    QWidget#dropNew[activa="true"] {{
        background-color: {con_alfa_qss(CURRENT_COLOR, 36)};
        border: 1px dashed {con_alfa_qss(CURRENT_COLOR, 165)};
    }}
    QLabel#dropNewTitle {{
        background-color: transparent;
        color: {aclarar(CURRENT_COLOR, 0.35)};
        font-size: {FONT_BODY}px;
        font-weight: 650;
    }}
    QLabel#dropNewHint {{
        background-color: transparent;
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
    }}
    /* --- los dos estados vacios ---
       El cartel del centro es lo PRIMERO que se ve al abrir la app: sin
       sesion no hay ni un clip. Va sobre el fondo de la hoja y sin caja
       propia --nada de recuadro punteado permanente, que es lo que hace la
       zona de arrastre y solo mientras arrastras--: es un texto, no un
       control. */
    QWidget#sheetEmpty {{
        background-color: transparent;
    }}
    QLabel#sheetEmptyTitle {{
        background-color: transparent;
        color: {TEXT_2};
        font-size: {FONT_BODY}px;
        font-weight: 650;
    }}
    QLabel#sheetEmptyHint {{
        background-color: transparent;
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
    }}
    /* El renglon del bin sin clips. En el gris mas apagado y en el tamaño
       mas chico que usa la hoja --el mismo de `sheetHint`--: el bin vacio es
       un estado normal, y un aviso que grita se leeria como un error. */
    QLabel#binEmptyHint {{
        background-color: transparent;
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
        padding: 2px 0 6px 9px;
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
    /* De que camara salio el clip, junto al nombre del archivo. Apagada a
       proposito: es contexto, no estado -- si compitiera con los badges de
       cuarto y marca, le quitaria peso a lo que si estas decidiendo. */
    QLabel#overlayBin {{
        background-color: {OVERLAY_BG};
        border: 1px solid {OVERLAY_BORDER};
        border-radius: {RADIUS_SM}px;
        padding: 3px 7px;
        color: {TEXT_2};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
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

    /* --- la pantalla de inicio (F4 del plan de proyectos) ---
       Sin colores nuevos: las filas son la superficie de un control en
       reposo, el titulo es el numero grande que ya usa el rail y la fila
       apagada baja al gris de lo secundario. */
    QWidget#pantallaInicio {{
        background-color: {BG_APP};
    }}
    QLabel#inicioTitulo {{
        color: {TEXT};
        font-size: {FONT_BIG}px;
        font-weight: 600;
    }}
    /* `text-align: left` y `padding: 0`: la regla generica de QPushButton
       centra y mete 8x14 px, y aqui adentro hay un layout con dos renglones
       --el relleno lo pone la fila, no el estilo del boton. */
    QPushButton#filaReciente {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_LG}px;
        padding: 0px;
        text-align: left;
    }}
    QPushButton#filaReciente:hover {{
        background-color: {BG_SURFACE_2};
        border-color: {CURRENT_COLOR};
    }}
    /* el que ya no esta en su lugar: se hunde al fondo de la app y pierde
       el borde visible, para que se lea como «esta, pero no se puede».
       Va por PROPIEDAD y no por `:disabled` -- la fila ya no se apaga con
       `setEnabled(False)`, porque un widget apagado tampoco recibe el clic
       DERECHO y ahi vive el unico «Quitar de la lista» que tiene. */
    QPushButton#filaReciente[perdido="true"] {{
        background-color: {BG_SURFACE_0};
        border: 1px solid {LINE_SOFT};
    }}
    QPushButton#filaReciente[perdido="true"]:hover {{
        background-color: {BG_SURFACE_0};
        border: 1px solid {LINE_SOFT};
    }}
    /* transparente NO es redundante: la regla global de QWidget le pinta el
       fondo de la app a toda QLabel, y sobre la fila eso se ve como dos
       cajas oscuras encima del nombre y la ruta. */
    QLabel#recienteNombre {{
        background-color: transparent;
        color: {TEXT};
        font-size: {FONT_BODY}px;
        font-weight: 600;
    }}
    QLabel#recienteDetalle {{
        background-color: transparent;
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    QLabel#recienteNombre[apagado="true"] {{
        color: {TEXT_3};
    }}
    /* El aviso de «no se pudo». Usa REJECT_COLOR, que es un color de ESTADO
       de clip, y aqui eso no confunde: en la pantalla de inicio no hay una
       sola tarjeta a la vista, asi que los dos significados nunca comparten
       pantalla. Inventar un color nuevo para un renglon que aparece de vez
       en cuando seria peor. */
    QLabel#inicioAviso {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {REJECT_COLOR};
        border-radius: {RADIUS_MD}px;
        color: {TEXT};
        font-size: {FONT_SMALL}px;
        padding: 8px 12px;
    }}

    /* --- la barra de media faltante (F6 del plan de proyectos) ---
       Es una BARRA, no un cartel: se mete entre la barra de titulo y el
       cuerpo, con el mismo fondo de panel que las otras dos, para que se lea
       como una fila mas de la ventana y no como algo que hay que cerrar.
       El unico color propio es el borde de abajo, en ambar: el mismo con el
       que la app marca lo que todavia no esta resuelto. */
    QWidget#avisoDeMedia {{
        background-color: {BG_SURFACE_0};
        border-bottom: 1px solid {con_alfa_qss(CURRENT_COLOR, 115)};
    }}
    /* transparentes NO es redundante: la regla global de QWidget le pinta el
       fondo de la app a toda QLabel, y sobre la barra eso se ve como cajitas
       oscuras alrededor de cada texto. */
    QWidget#avisoFila {{
        background-color: transparent;
    }}
    QLabel#avisoBin {{
        background-color: transparent;
        color: {TEXT};
        font-size: {FONT_SMALL}px;
        font-weight: 650;
    }}
    /* Los tres finales se distinguen POR COLOR ademas de por texto: verde es
       lo que quedo resuelto, ambar es lo que falta, y el rojo del reject se
       guarda para el unico caso que hay que mirar dos veces --aparecio un
       archivo con ese nombre y NO es el mismo--. Aqui no compite con el
       estado de un clip: la barra vive fuera de la hoja de tarjetas. */
    QLabel#avisoTexto {{
        background-color: transparent;
        color: {TEXT_2};
        font-size: {FONT_SMALL}px;
    }}
    QLabel#avisoTexto[tono="falta"] {{
        color: {aclarar(CURRENT_COLOR, 0.35)};
    }}
    QLabel#avisoTexto[tono="alerta"] {{
        color: {aclarar(REJECT_COLOR, 0.25)};
    }}
    QLabel#avisoTexto[tono="ok"] {{
        color: {aclarar(PICK_COLOR, 0.35)};
    }}
    QPushButton#avisoBuscar {{
        background-color: {BG_SURFACE_2};
        border: 1px solid {LINE};
        border-radius: {RADIUS_MD}px;
        padding: 3px 11px;
        color: {TEXT};
        font-size: {FONT_SMALL}px;
        font-weight: 550;
    }}
    QPushButton#avisoBuscar:hover:enabled {{
        background-color: {BG_SURFACE_1};
        border-color: {CURRENT_COLOR};
    }}
    /* apagado mientras una búsqueda corre. Sin esta regla se veía IGUAL que
       prendido --nuestros colores pisan la paleta de deshabilitado de Qt-- y
       un botón que se ve prendido y no responde se lee como que la app se
       trabó, que es justo lo que el renglón «Buscando…» viene a desmentir. */
    QPushButton#avisoBuscar:disabled {{
        background-color: transparent;
        border: 1px solid {LINE_SOFT};
        color: {TEXT_3};
    }}

    QWidget#inicioVacio {{
        background-color: transparent;
    }}
    QLabel#inicioVacioTitulo {{
        background-color: transparent;
        color: {TEXT_2};
        font-size: {FONT_BODY}px;
        font-weight: 650;
    }}
    QLabel#inicioVacioHint {{
        background-color: transparent;
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
    }}

    """
