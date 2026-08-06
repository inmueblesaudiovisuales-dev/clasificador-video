from __future__ import annotations

# Paleta "Console": fondos casi negros, un solo acento vivido reservado
# para foco/acciones, tipografia monoespaciada para metadata tecnica.
BG_WINDOW = "#08080a"
BG_PANEL = "#0d0d0f"
BG_RAIL = "#0a0a0c"
BG_HOVER = "#17171a"
BG_ACTIVE = "#17130a"
ACCENT = "#ff8a3d"
TEXT = "#e4e4e4"
TEXT_MUTED = "#8a8a8a"
BORDER = "#1e1e21"

MONO_FONT = '"SF Mono", "JetBrains Mono", Menlo, monospace'

# Reservados para ESTADO (pick/reject/actual) -- nunca se usan para
# identidad de cuarto, para que un borde/badge de este color siempre
# signifique lo mismo en toda la app (ver spec de diseno: no compiten
# entre si porque no comparten ni familia de color ni posicion).
PICK_COLOR = "#3ddc84"
REJECT_COLOR = "#ff5566"
CURRENT_COLOR = ACCENT

# Paleta de IDENTIDAD DE CUARTO: apagada/pastel a proposito (nunca verde,
# rojo ni naranja) para no competir visualmente con los colores de estado
# de arriba.
ROOM_PALETTE = [
    "#6f8bb0",  # azul grisaceo
    "#a98f5c",  # ocre
    "#8f7fb8",  # violeta apagado
    "#5c9a9a",  # verde azulado
    "#9c8a6f",  # marron claro
    "#7a8fa6",  # gris azulado
    "#a67a95",  # mauve
    "#8a9b6f",  # oliva
]


def room_color(index: int) -> str:
    """Color de identidad estable para el cuarto en la posicion `index`
    de la lista de cuartos activos -- mismo indice, mismo color siempre,
    para que la identidad visual de un cuarto no cambie durante la sesion.
    """
    return ROOM_PALETTE[index % len(ROOM_PALETTE)]


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {BG_WINDOW};
        color: {TEXT};
        font-size: 13px;
    }}

    QListWidget {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 4px;
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
        background-color: #1c1c20;
    }}
    QPushButton:checked {{
        background-color: {BG_ACTIVE};
        border-color: {ACCENT};
        color: {ACCENT};
    }}

    QPushButton#startButton, QPushButton#exportButton {{
        background-color: {ACCENT};
        color: #0a0a0b;
        font-weight: 700;
        border: none;
        padding: 10px 16px;
    }}
    QPushButton#startButton:hover, QPushButton#exportButton:hover {{
        background-color: #ff9d5c;
    }}

    QPushButton#importButton {{
        background-color: transparent;
        border: 1px dashed #29292d;
        color: {TEXT_MUTED};
    }}
    QPushButton#importButton:hover {{
        background-color: {BG_HOVER};
    }}

    QComboBox, QLineEdit {{
        background-color: {BG_HOVER};
        border: 1px solid #29292d;
        border-radius: 3px;
        padding: 4px 8px;
        color: {TEXT};
    }}

    QLabel#legendLabel, QLabel#statusLabel {{
        color: {TEXT_MUTED};
        font-size: 11px;
        font-family: {MONO_FONT};
    }}
    QLabel#clipRoomLabel {{
        color: {TEXT_MUTED};
        font-size: 10px;
        font-family: {MONO_FONT};
    }}
    QLabel#panelTitle {{
        color: #5c5c60;
        font-size: 11px;
        text-transform: uppercase;
        font-weight: 700;
    }}
    QLabel#unclassifiedBadge {{
        color: #ffb15c;
        font-size: 11px;
    }}
    QLabel#savedIndicator {{
        color: #4a4a4e;
        font-size: 10.5px;
    }}
    QLabel#positionLabel {{
        color: {TEXT};
        font-family: {MONO_FONT};
        font-size: 11.5px;
    }}
    QLabel#inspectorRoomLabel {{
        color: {ACCENT};
        font-weight: 600;
        font-size: 13px;
    }}
    QWidget#clipListRow {{
        border-bottom: 1px solid {BORDER};
    }}
    QWidget#clipListRow:hover {{
        background-color: {BG_HOVER};
    }}
    QLabel#clipListName {{
        font-family: {MONO_FONT};
        font-size: 11.5px;
        color: {TEXT};
    }}
    QLabel#roomKeycap {{
        background-color: {BG_HOVER};
        border: 1px solid #2c2c30;
        border-radius: 3px;
        color: #777777;
        font-family: {MONO_FONT};
        font-size: 10px;
    }}
    QProgressBar#roomCountBar {{
        background-color: {BG_HOVER};
        border: none;
        border-radius: 1px;
    }}
    QProgressBar#roomCountBar::chunk {{
        background-color: #3a2c15;
        border-radius: 1px;
    }}
    QLabel#subroomBanner {{
        background-color: {BG_ACTIVE};
        color: {ACCENT};
        border: 1px solid {ACCENT};
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 600;
    }}

    QWidget#videoWidget {{
        background-color: black;
        border: 1px solid {BORDER};
        border-radius: 3px;
    }}

    QWidget#filmstripPanel, QWidget#roomColumn, QWidget#inspectorPanel {{
        background-color: {BG_RAIL};
        border-radius: 4px;
    }}
    """
