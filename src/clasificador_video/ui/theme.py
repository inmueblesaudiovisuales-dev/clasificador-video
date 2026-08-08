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

# --- colores derivados que antes vivian sueltos en otros modulos ---
SELECTION_WASH = "rgba(109, 140, 245, 60)"  # lavado de seleccion multiple
RANGE_TRACK_COLOR = "#2e343d"               # riel de la barra de rango
FLAG_NONE_COLOR = TEXT_3                    # texto de "sin marca"
PLAYHEAD_HIGHLIGHT = "#f2bd72"              # brillo superior del playhead
TICK_MINOR_COLOR = "#2e343d"
TICK_MAJOR_COLOR = "#454d59"
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

# ---------------------------------------------------------------------------
# Alias de compatibilidad. Existen SOLO para que la app siga corriendo
# durante la F1 con los widgets viejos, que importan estos nombres. Cambian
# de valor, no de nombre. Se borran en la Task 9 de la F2.
# ---------------------------------------------------------------------------
ACCENT = CURRENT_COLOR
BG_WINDOW = BG_APP
BG_PANEL = BG_SURFACE_0
BG_RAIL = BG_SURFACE_0
BG_HOVER = BG_SURFACE_1
BG_ACTIVE = BG_SURFACE_2
TEXT_MUTED = TEXT_2
BORDER = LINE


def room_color(index: int) -> str:
    """Color de identidad estable para el cuarto en la posicion `index`
    de la lista de cuartos activos -- mismo indice, mismo color siempre,
    para que la identidad visual de un cuarto no cambie durante la sesion.
    """
    return ROOM_PALETTE[index % len(ROOM_PALETTE)]


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
        background-color: {BG_WINDOW};
        color: {TEXT};
        font-size: {FONT_BODY}px;
    }}

    QListWidget {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM}px;
        padding: 6px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: 3px;
        margin-bottom: 2px;
    }}
    QListWidget::item:selected {{
        background-color: {BG_ACTIVE};
        color: {ACCENT};
    }}

    QPushButton {{
        background-color: {BG_HOVER};
        border: 1px solid {BORDER};
        border-radius: 3px;
        padding: 8px 14px;
        color: {TEXT};
    }}
    QPushButton:hover {{
        background-color: {BG_SURFACE_0};
    }}
    QPushButton:checked {{
        background-color: {BG_ACTIVE};
        border-color: {ACCENT};
        color: {ACCENT};
    }}

    QPushButton#startButton, QPushButton#exportButton {{
        background-color: {ACCENT};
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
        color: {TEXT_MUTED};
    }}
    QPushButton#importButton:hover {{
        background-color: {BG_HOVER};
    }}

    QComboBox, QLineEdit {{
        background-color: {BG_HOVER};
        border: 1px solid {LINE};
        border-radius: 3px;
        padding: 4px 8px;
        color: {TEXT};
    }}

    QLabel#legendLabel, QLabel#statusLabel, QLabel#scrubTimeLabel {{
        color: {TEXT_MUTED};
        font-size: {FONT_SMALL}px;
        font-family: {MONO_FONT};
    }}
    QLabel#clipRoomLabel {{
        color: {TEXT_MUTED};
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
        color: {ACCENT};
        font-weight: 600;
        font-size: {FONT_TITLE}px;
    }}
    QWidget#clipListRow {{
        border-bottom: 1px solid {BORDER};
    }}
    QWidget#clipListRow:hover {{
        background-color: {BG_HOVER};
    }}
    QLabel#clipListName {{
        font-family: {MONO_FONT};
        font-size: {FONT_SMALL}px;
        color: {TEXT};
    }}
    QLabel#roomKeycap {{
        background-color: {BG_HOVER};
        border: 1px solid {LINE};
        border-radius: 3px;
        color: {TEXT_2};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    QProgressBar#roomCountBar {{
        background-color: {BG_HOVER};
        border: none;
        border-radius: 1px;
    }}
    QProgressBar#roomCountBar::chunk {{
        background-color: {BG_SURFACE_2};
        border-radius: 1px;
    }}
    QLabel#subroomBanner {{
        background-color: {BG_ACTIVE};
        color: {ACCENT};
        border: 1px solid {ACCENT};
        border-radius: {RADIUS_SM}px;
        padding: 6px 14px;
        font-weight: 600;
    }}

    QWidget#videoWidget {{
        background-color: black;
        border: 1px solid {BORDER};
        border-radius: 3px;
    }}

    QWidget#scrubBar {{
        background-color: {BG_RAIL};
        border-radius: 3px;
    }}

    QWidget#filmstripPanel, QWidget#roomColumn, QWidget#inspectorPanel {{
        background-color: {BG_RAIL};
        border-radius: {RADIUS_SM}px;
    }}
    """
