# src/clasificador_video/ui/filmstrip.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.ui.theme import CURRENT_COLOR, PICK_COLOR, REJECT_COLOR

THUMB_HEIGHT = 80
THUMB_MAX_WIDTH = 140
TILE_WIDTH = 150  # ancho de cada tile de la vista grilla, usado para calcular columnas

# fondo de seleccion multiple: el mismo acento que CURRENT_COLOR pero muy
# translucido, para no competir con los colores de estado (ver theme.py)
_SELECTION_WASH = "rgba(255, 138, 61, 40)"


@dataclass
class ClipThumbnail:
    path: Path
    thumbnail_path: Path | None
    room_label: str
    flag: str  # "none" | "pick" | "reject"
    room_color: str | None = None  # acento de identidad de cuarto (franja superior)


class _ClipItemWidget(QWidget):
    clicked = Signal(object)  # Qt.KeyboardModifier vigente al hacer click

    def __init__(self, clip: ClipThumbnail):
        super().__init__()
        self._flag = clip.flag
        self._room_color = clip.room_color
        self.setObjectName("clipItem")
        # sin esto, un QWidget plano no pinta su propio fondo/borde por QSS
        # -- la propiedad se hereda a los QLabel hijos, que la pintan cada
        # uno por separado (bug real de v1: dos cajas en vez de una sola
        # envolviendo miniatura + nombre de cuarto).
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
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

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(event.modifiers())
        super().mousePressEvent(event)

    def set_visual_state(self, is_current: bool, is_selected: bool = False) -> None:
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
        if self._room_color:
            # franja superior de identidad de cuarto -- canal distinto del
            # borde de estado de arriba (posicion, no familia de color),
            # para que nunca se puedan confundir entre si.
            parts.append(f"border-top: 3px solid {self._room_color};")
        if is_selected:
            parts.append(f"background-color: {_SELECTION_WASH};")
        # Mezclar una regla "sin selector" (implicita para self) con una
        # regla "QLabel {...}" en la misma cadena no se parsea como cabria
        # esperar -- Qt sigue pintando el borde en los QLabel hijos pese a
        # la regla explicita. Usar selectores explicitos por objectName
        # para ambos (contenedor y descendientes) evita la ambiguedad y
        # es la unica forma que produce UNA sola caja verificada con
        # grab() en vez de dos.
        own_rule = "#clipItem { " + " ".join(parts) + " }"
        children_rule = "#clipItem QLabel { border: none; }"
        self.setStyleSheet(f"{own_rule} {children_rule}")


class _ClipListRowWidget(QWidget):
    """Fila compacta para la vista de lista (tipo panel de Proyecto de
    Premiere en modo lista): prioriza metadata escaneable -- nombre,
    cuarto, estado -- sobre la imagen. Pensada para sesiones con muchos
    clips, donde leer una tabla es mas rapido que reconocer miniaturas."""

    clicked = Signal(object)  # Qt.KeyboardModifier vigente al hacer click

    def __init__(self, clip: ClipThumbnail):
        super().__init__()
        self._flag = clip.flag
        self._room_color = clip.room_color
        self.setObjectName("clipListRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self._name_label = QLabel(clip.path.name)
        self._name_label.setObjectName("clipListName")
        self._room_label = QLabel(clip.room_label)
        self._room_label.setObjectName("clipRoomLabel")
        self._flag_label = QLabel(self._flag_text())
        self._flag_label.setObjectName("clipListFlag")
        layout.addWidget(self._name_label, stretch=2)
        layout.addWidget(self._room_label, stretch=1)
        layout.addWidget(self._flag_label, stretch=0)

    def _flag_text(self) -> str:
        return {"pick": "✓ Pick", "reject": "✕ Reject"}.get(self._flag, "—")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(event.modifiers())
        super().mousePressEvent(event)

    def set_visual_state(self, is_current: bool, is_selected: bool = False) -> None:
        parts = []
        room_color = self._room_color or "transparent"
        parts.append(f"border-left: 3px solid {room_color};")
        if is_current or is_selected:
            parts.append(f"background-color: {_SELECTION_WASH};")
        own_rule = "#clipListRow { " + " ".join(parts) + " }"
        self.setStyleSheet(own_rule)
        flag_color = {"pick": PICK_COLOR, "reject": REJECT_COLOR}.get(self._flag, "#666666")
        self._flag_label.setStyleSheet(f"color: {flag_color}; font-weight: 600;")


class Filmstrip(QWidget):
    """Panel de clips (app-externa §3-4): dos vistas intercambiables --
    grilla (miniaturas, envuelve verticalmente) y lista (metadata tipo
    panel de Proyecto de Premiere) -- con borde verde/rosa por
    pick/reject, borde naranja para el clip actual y franja de color por
    cuarto. Soporta seleccion multiple (Shift/Ctrl+click) para aplicar un
    cuarto a varios clips a la vez, sea cual sea la vista activa.
    """

    clip_clicked = Signal(int)  # indice del clip en la lista
    selection_changed = Signal(list)  # indices seleccionados (multiseleccion)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.item_widgets: list[_ClipItemWidget] = []
        self._list_rows: list[_ClipListRowWidget] = []
        self._current = -1
        self._selected: set[int] = set()
        self._anchor: int | None = None
        self._view_mode = "grid"

        self.grid_view_button = QPushButton("▦ Grilla")
        self.grid_view_button.setObjectName("viewToggleButton")
        self.grid_view_button.setCheckable(True)
        self.grid_view_button.setChecked(True)
        self.grid_view_button.clicked.connect(lambda: self.set_view_mode("grid"))
        self.list_view_button = QPushButton("☰ Lista")
        self.list_view_button.setObjectName("viewToggleButton")
        self.list_view_button.setCheckable(True)
        self.list_view_button.clicked.connect(lambda: self.set_view_mode("list"))

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.grid_view_button)
        toolbar.addWidget(self.list_view_button)
        toolbar.addStretch(1)

        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignTop)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._grid_container)
        self._stack.addWidget(self._list_container)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._stack)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setFixedHeight(220)

        root = QVBoxLayout(self)
        root.addLayout(toolbar)
        root.addWidget(self._scroll)

    def set_view_mode(self, mode: str) -> None:
        if mode not in ("grid", "list"):
            return
        self._view_mode = mode
        self.grid_view_button.setChecked(mode == "grid")
        self.list_view_button.setChecked(mode == "list")
        self._stack.setCurrentWidget(self._grid_container if mode == "grid" else self._list_container)
        if mode == "grid":
            self._relayout_grid()

    def set_clips(self, clips: list[ClipThumbnail]) -> None:
        for widget in self.item_widgets:
            widget.setParent(None)
        for row in self._list_rows:
            row.setParent(None)
        self.item_widgets = []
        self._list_rows = []
        for index, clip in enumerate(clips):
            item = _ClipItemWidget(clip)
            item.clicked.connect(lambda mods, i=index: self._on_item_clicked(i, mods))
            self.item_widgets.append(item)

            row = _ClipListRowWidget(clip)
            row.clicked.connect(lambda mods, i=index: self._on_item_clicked(i, mods))
            self._list_layout.addWidget(row)
            self._list_rows.append(row)
        self._relayout_grid()
        self._current = -1
        self._anchor = None
        self.set_selected(set())

    def _relayout_grid(self) -> None:
        while self._grid_layout.count():
            self._grid_layout.takeAt(0)
        width = self._grid_container.width() or self.width() or TILE_WIDTH
        columns = max(1, width // TILE_WIDTH)
        for i, widget in enumerate(self.item_widgets):
            row, col = divmod(i, columns)
            self._grid_layout.addWidget(widget, row, col)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._view_mode == "grid":
            self._relayout_grid()

    def _on_item_clicked(self, index: int, modifiers: Qt.KeyboardModifier) -> None:
        self.clip_clicked.emit(index)
        shift = bool(modifiers & Qt.ShiftModifier)
        ctrl = bool(modifiers & (Qt.ControlModifier | Qt.MetaModifier))
        if shift and self._anchor is not None:
            lo, hi = sorted((self._anchor, index))
            new_selection = set(range(lo, hi + 1))
        elif ctrl:
            new_selection = set(self._selected)
            if index in new_selection:
                new_selection.discard(index)
            else:
                new_selection.add(index)
            self._anchor = index
        else:
            new_selection = {index}
            self._anchor = index
        self.set_selected(new_selection)

    def set_selected(self, indices: set[int]) -> None:
        self._selected = set(indices)
        self._redraw()
        self.selection_changed.emit(self.selected_indices())

    def selected_indices(self) -> list[int]:
        return sorted(self._selected)

    def set_current(self, index: int) -> None:
        self._current = index
        self._redraw()

    def _redraw(self) -> None:
        multi = len(self._selected) > 1
        for i, widget in enumerate(self.item_widgets):
            widget.set_visual_state(
                is_current=(i == self._current),
                is_selected=multi and i in self._selected,
            )
        for i, row in enumerate(self._list_rows):
            row.set_visual_state(
                is_current=(i == self._current),
                is_selected=multi and i in self._selected,
            )

    def count(self) -> int:
        return len(self.item_widgets)
