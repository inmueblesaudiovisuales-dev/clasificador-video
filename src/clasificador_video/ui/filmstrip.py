# src/clasificador_video/ui/filmstrip.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

PICK_COLOR = "#3bb273"
REJECT_COLOR = "#e0556f"
CURRENT_COLOR = "#2b7fff"

THUMB_HEIGHT = 80
THUMB_MAX_WIDTH = 140


@dataclass
class ClipThumbnail:
    path: Path
    thumbnail_path: Path | None
    room_label: str
    flag: str  # "none" | "pick" | "reject"


class _ClipItemWidget(QWidget):
    def __init__(self, clip: ClipThumbnail):
        super().__init__()
        self._flag = clip.flag
        self.setObjectName("clipItem")
        # sin esto, un QWidget plano no pinta su propio fondo/borde por QSS
        # -- la propiedad se hereda a los QLabel hijos, que la pintan cada
        # uno por separado (bug real de v1: dos cajas en vez de una sola
        # envolviendo miniatura + nombre de cuarto).
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        self._image_label = QLabel()
        self._image_label.setFixedHeight(THUMB_HEIGHT)
        self._image_label.setObjectName("clipThumbnail")
        if clip.thumbnail_path is not None:
            self._image_label.setText("")
        else:
            self._image_label.setText("(sin miniatura)")
        layout.addWidget(self._image_label)
        self._room_label = QLabel(clip.room_label)
        self._room_label.setObjectName("clipRoomLabel")
        layout.addWidget(self._room_label)

    def set_pixmap(self, pixmap) -> None:
        scaled = pixmap.scaled(
            THUMB_MAX_WIDTH, THUMB_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._image_label.setPixmap(scaled)
        self._image_label.setFixedWidth(scaled.width())

    def has_pixmap(self) -> bool:
        return self._image_label.pixmap() is not None

    def set_visual_state(self, is_current: bool) -> None:
        parts = []
        flag_color = {"pick": PICK_COLOR, "reject": REJECT_COLOR}.get(self._flag)
        if flag_color:
            parts.append(f"border: 2px solid {flag_color};")
        elif is_current:
            parts.append(f"border: 2px solid {CURRENT_COLOR};")
        if is_current and flag_color:
            parts.append(f"outline: 2px solid {CURRENT_COLOR};")
        if not parts:
            parts.append("border: none;")
        # el borde (o su ausencia) es SOLO del contenedor -- sin esta regla
        # explicita, QSS lo hereda a los QLabel hijos y cada uno lo pinta
        # por su cuenta, dando dos cajas visibles en vez de una.
        parts.append("QLabel { border: none; }")
        self.setStyleSheet(" ".join(parts))


class Filmstrip(QWidget):
    """Fila de miniaturas (app-externa §3-4): borde verde/rosa por
    pick/reject, borde azul para el clip actual, nombre del cuarto debajo.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self.item_widgets: list[_ClipItemWidget] = []

    def set_clips(self, clips: list[ClipThumbnail]) -> None:
        for widget in self.item_widgets:
            widget.setParent(None)
        self.item_widgets = []
        for clip in clips:
            item = _ClipItemWidget(clip)
            self._layout.addWidget(item)
            self.item_widgets.append(item)
        self.set_current(-1)

    def set_current(self, index: int) -> None:
        for i, widget in enumerate(self.item_widgets):
            widget.set_visual_state(is_current=(i == index))

    def count(self) -> int:
        return len(self.item_widgets)
