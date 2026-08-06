# src/clasificador_video/ui/filmstrip.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

PICK_COLOR = "#3bb273"
REJECT_COLOR = "#e0556f"


@dataclass
class ClipThumbnail:
    path: Path
    thumbnail_path: Path | None
    room_label: str
    flag: str  # "none" | "pick" | "reject"


class _ClipItemWidget(QWidget):
    def __init__(self, clip: ClipThumbnail):
        super().__init__()
        layout = QVBoxLayout(self)
        self._image_label = QLabel()
        if clip.thumbnail_path is not None:
            self._image_label.setText("")
        else:
            self._image_label.setText("(sin miniatura)")
        layout.addWidget(self._image_label)
        self._room_label = QLabel(clip.room_label)
        layout.addWidget(self._room_label)

        border_color = {"pick": PICK_COLOR, "reject": REJECT_COLOR}.get(clip.flag)
        if border_color:
            self.setStyleSheet(f"border: 2px solid; border-color: {border_color};")

    def set_pixmap(self, pixmap) -> None:
        self._image_label.setPixmap(pixmap)

    def has_pixmap(self) -> bool:
        return self._image_label.pixmap() is not None


class Filmstrip(QWidget):
    """Fila de miniaturas (app-externa §3-4): borde verde/rosa por
    pick/reject, nombre del cuarto debajo, opcion A elegida sobre la B.
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

    def count(self) -> int:
        return len(self.item_widgets)
