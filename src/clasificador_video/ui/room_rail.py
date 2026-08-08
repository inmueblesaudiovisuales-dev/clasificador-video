# src/clasificador_video/ui/room_rail.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clasificador_video.ui import theme
from clasificador_video.ui.text import ElidedLabel

MAX_TECLAS = 9  # los atajos numericos llegan hasta el noveno cuarto


class _BarraProgreso(QWidget):
    """Barra segmentada por cuarto: un tramo por cuarto con su color de
    identidad, mas un tramo apagado para lo que falta clasificar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(5)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)
        self._tramos: list[QWidget] = []

    def set_counts(self, counts: list[int], pendientes: int) -> None:
        for tramo in self._tramos:
            tramo.setParent(None)
        self._tramos = []
        for indice, cuantos in enumerate(counts):
            if cuantos <= 0:
                continue
            self._tramos.append(self._tramo(theme.room_color(indice), cuantos))
        if pendientes > 0:
            self._tramos.append(self._tramo(theme.BG_SURFACE_2, pendientes))

    def _tramo(self, color: str, peso: int) -> QWidget:
        tramo = QWidget()
        tramo.setAttribute(Qt.WA_StyledBackground, True)
        tramo.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        self._layout.addWidget(tramo, stretch=peso)
        return tramo


class _FilaCuarto(QWidget):
    """Tecla + color de identidad + nombre elidido + conteo."""

    def __init__(self, numero: int | None, nombre: str, color: str, cuantos: int, parent=None):
        super().__init__(parent)
        self.setObjectName("roomRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(29)
        self.nombre = nombre

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(8)

        self.key_cap = QLabel("" if numero is None else str(numero))
        self.key_cap.setObjectName("keyCap")
        self.key_cap.setFixedSize(18, 18)
        self.key_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # los cuartos a partir del decimo no tienen atajo numerico: el badge
        # queda vacio en vez de mentir con un numero que no funciona
        self.key_cap.setProperty("sin_tecla", numero is None)

        self.swatch = QLabel("")
        self.swatch.setFixedSize(3, 14)
        self.swatch.setAttribute(Qt.WA_StyledBackground, True)
        self.swatch.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

        self.name_label = ElidedLabel(nombre)
        self.name_label.setObjectName("roomName")
        self.count_label = QLabel(str(cuantos))
        self.count_label.setObjectName("roomCount")

        layout.addWidget(self.key_cap)
        layout.addWidget(self.swatch)
        layout.addWidget(self.name_label, stretch=1)
        layout.addWidget(self.count_label)


class RoomRail(QWidget):
    """Columna izquierda de 200 px: progreso y cuartos.

    Reemplaza a la columna vieja, al boton de importar suelto y al panel
    "Material importado", que ocupaba media columna para listar nombres de
    carpetas y no existe en el mockup.
    """

    import_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("roomRail")
        self.setFixedWidth(theme.RAIL_WIDTH)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # --- bloque de progreso ---
        progreso = QWidget()
        pl = QVBoxLayout(progreso)
        pl.setContentsMargins(12, 13, 12, 12)
        pl.setSpacing(9)

        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.progress_big = QLabel("0")
        self.progress_big.setObjectName("progressBig")
        self.progress_total = QLabel("/0")
        self.progress_total.setObjectName("progressTotal")
        self.progress_caption = QLabel("CLASIFICADOS")
        self.progress_caption.setObjectName("railHeader")
        theme.apply_letter_spacing(self.progress_caption)
        fila.addWidget(self.progress_big)
        fila.addWidget(self.progress_total, alignment=Qt.AlignmentFlag.AlignBottom)
        fila.addStretch(1)
        fila.addWidget(self.progress_caption, alignment=Qt.AlignmentFlag.AlignBottom)
        pl.addLayout(fila)

        self.progress_bar = _BarraProgreso()
        pl.addWidget(self.progress_bar)

        self.flags_label = QLabel("")
        self.flags_label.setObjectName("roomCount")
        pl.addWidget(self.flags_label)
        raiz.addWidget(progreso)

        # --- encabezado de cuartos ---
        encabezado = QWidget()
        el = QHBoxLayout(encabezado)
        el.setContentsMargins(12, 0, 12, 0)
        cabecera = QLabel("CUARTOS")
        cabecera.setObjectName("railHeader")
        theme.apply_letter_spacing(cabecera)
        self.find_hint = QLabel("⏎ buscar")
        self.find_hint.setObjectName("roomCount")
        el.addWidget(cabecera)
        el.addStretch(1)
        el.addWidget(self.find_hint)
        encabezado.setFixedHeight(30)
        raiz.addWidget(encabezado)

        # --- banner de subcuarto (temporal: muere en la F3) ---
        self.subroom_banner = QLabel("")
        self.subroom_banner.setObjectName("subroomBanner")
        self.subroom_banner.hide()
        raiz.addWidget(self.subroom_banner)

        # --- lista de cuartos ---
        self._rooms_container = QWidget()
        self._rooms_layout = QVBoxLayout(self._rooms_container)
        self._rooms_layout.setContentsMargins(7, 6, 7, 6)
        self._rooms_layout.setSpacing(0)
        self._rooms_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        raiz.addWidget(self._rooms_container, stretch=1)
        self.rows: list[_FilaCuarto] = []

        # --- importar, al pie ---
        self.import_button = QPushButton("Importar carpetas…")
        self.import_button.setObjectName("importButton")
        self.import_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.import_button.clicked.connect(self.import_requested.emit)
        pie = QWidget()
        fl = QVBoxLayout(pie)
        fl.setContentsMargins(9, 6, 9, 10)
        fl.addWidget(self.import_button)
        raiz.addWidget(pie)

    def set_rooms(self, rooms: list[str], counts: dict[str, int]) -> None:
        for fila in self.rows:
            fila.setParent(None)
        self.rows = []
        for indice, cuarto in enumerate(rooms):
            numero = indice + 1 if indice < MAX_TECLAS else None
            fila = _FilaCuarto(numero, cuarto, theme.room_color(indice), counts.get(cuarto, 0))
            self._rooms_layout.addWidget(fila)
            self.rows.append(fila)
        self.progress_bar.set_counts(
            [counts.get(c, 0) for c in rooms], self._pendientes
        )

    def set_progress(self, clasificados: int, total: int, pendientes: int = 0) -> None:
        self.progress_big.setText(str(clasificados))
        self.progress_total.setText(f"/{total}")
        self._pendientes = pendientes

    def set_flags(self, picks: int, rejects: int, sin_clasificar: int) -> None:
        self.flags_label.setText(
            f"● {picks} picks   ● {rejects} rejects   ● {sin_clasificar} sin clasificar"
        )

    def set_current_room(self, cuarto: str | None) -> None:
        for fila in self.rows:
            fila.setProperty("actual", fila.nombre == cuarto)
            fila.style().unpolish(fila)
            fila.style().polish(fila)

    _pendientes = 0
