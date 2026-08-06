# src/clasificador_video/ui/filmstrip.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

PICK_COLOR = "#3bb273"
REJECT_COLOR = "#e0556f"
CURRENT_COLOR = "#2b7fff"


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
        layout = QVBoxLayout(self)
        self._image_label = QLabel()
        if clip.thumbnail_path is not None:
            self._image_label.setText("")
        else:
            self._image_label.setText("(sin miniatura)")
        layout.addWidget(self._image_label)
        self._room_label = QLabel(clip.room_label)
        layout.addWidget(self._room_label)

    def set_pixmap(self, pixmap) -> None:
        self._image_label.setPixmap(pixmap)

    def has_pixmap(self) -> bool:
        return self._image_label.pixmap() is not None

    def set_visual_state(self, is_current: bool) -> None:
        borders = []
        flag_color = {"pick": PICK_COLOR, "reject": REJECT_COLOR}.get(self._flag)
        if flag_color:
            borders.append(flag_color)
        if is_current:
            borders.append(CURRENT_COLOR)
        if borders:
            self.setStyleSheet(f"border: 2px solid; border-color: {'; border-color: '.join(borders)};")
        else:
            self.setStyleSheet("")


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
