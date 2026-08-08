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
    QLabel#unclassifiedBadge {{
        color: {CURRENT_COLOR};
        font-size: {FONT_SMALL}px;
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
    QLabel#subroomBanner {{
        background-color: {BG_SURFACE_2};
        color: {CURRENT_COLOR};
        border: 1px solid {CURRENT_COLOR};
        border-radius: {RADIUS_SM}px;
        padding: 6px 14px;
        font-weight: 600;
    }}

    QWidget#segmentedControl {{
        background-color: {BG_SURFACE_1};
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
    QLabel#roomName {{
        color: {TEXT};
        font-size: {FONT_BODY}px;
    }}
    QLabel#roomCount {{
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

    QWidget#clipSheet {{
        background-color: {BG_SURFACE_0};
    }}
    QWidget#sheetHeader {{
        background-color: {BG_SURFACE_0};
        border-bottom: 1px solid {LINE_SOFT};
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
    QLabel#overlayFile {{
        background-color: {OVERLAY_BG};
        border: 1px solid {OVERLAY_BORDER};
        border-radius: {RADIUS_MD}px;
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
