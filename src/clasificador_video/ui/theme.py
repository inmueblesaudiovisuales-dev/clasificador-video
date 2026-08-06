from __future__ import annotations

BG_WINDOW = "#1a1a1e"
BG_PANEL = "#232327"
BG_ACTIVE = "#3a5a8c"
BG_HOVER = "#2c2c32"
ACCENT = "#5b9bff"
TEXT = "#dddddd"
TEXT_MUTED = "#8a8a8a"
BORDER = "#333333"

PICK_COLOR = "#3bb273"
REJECT_COLOR = "#e0556f"
CURRENT_COLOR = "#2b7fff"


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {BG_WINDOW};
        color: {TEXT};
        font-size: 13px;
    }}

    QListWidget {{
        background-color: {BG_PANEL};
        border: none;
        border-radius: 6px;
        padding: 6px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: 4px;
        margin-bottom: 2px;
    }}
    QListWidget::item:selected {{
        background-color: {BG_ACTIVE};
    }}

    QPushButton {{
        background-color: {BG_PANEL};
        border: none;
        border-radius: 6px;
        padding: 8px 14px;
        color: {TEXT};
    }}
    QPushButton:hover {{
        background-color: {BG_HOVER};
    }}
    QPushButton:checked {{
        background-color: {BG_ACTIVE};
    }}

    QPushButton#startButton, QPushButton#exportButton {{
        background-color: {ACCENT};
        color: white;
        font-weight: 600;
        padding: 10px 16px;
    }}
    QPushButton#startButton:hover, QPushButton#exportButton:hover {{
        background-color: #4a89e8;
    }}

    QPushButton#importButton {{
        background-color: {BG_HOVER};
        border: 1px solid {BORDER};
    }}
    QPushButton#importButton:hover {{
        background-color: #38383f;
    }}

    QComboBox, QLineEdit {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 5px;
        padding: 4px 8px;
        color: {TEXT};
    }}

    QLabel#legendLabel, QLabel#statusLabel {{
        color: {TEXT_MUTED};
        font-size: 11px;
    }}
    QLabel#clipRoomLabel {{
        color: {TEXT_MUTED};
        font-size: 10px;
    }}
    QLabel#panelTitle {{
        color: {TEXT_MUTED};
        font-size: 11px;
        text-transform: uppercase;
        font-weight: 600;
    }}

    QWidget#videoWidget {{
        background-color: black;
        border-radius: 6px;
    }}

    QWidget#filmstripPanel, QWidget#roomColumn {{
        background-color: {BG_PANEL};
        border-radius: 6px;
    }}
    """
