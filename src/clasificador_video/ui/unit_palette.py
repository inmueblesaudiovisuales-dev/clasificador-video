# src/clasificador_video/ui/unit_palette.py
from __future__ import annotations

from PySide6.QtCore import Signal

from clasificador_video.ui import theme
from clasificador_video.ui.room_palette import RoomPalette


class UnitPalette(RoomPalette):
    """Buscar, crear y ACTIVAR unidades, sin soltar el teclado.

    Diferencia clave con `RoomPalette`: elegir una unidad no asigna nada
    y no cierra la paleta -- la deja ACTIVA hasta que se elija otra o se
    cierre con Escape. A partir de ahi, la paleta de cuartos, los digitos
    y `S` siguen actuando sobre el cuarto exactamente igual que siempre,
    pero filtrados al catalogo de la unidad activa (spec 2026-09-20 §3).
    """

    unit_activated = Signal(str)
    unit_created = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            color_fn=theme.unit_color,
            swatch_size=(11, 11),
            swatch_radius=3,
            placeholder="Buscar o crear unidad…",
        )
        self.setObjectName("unitPalette")
        self.foot_label.setText("↑ ↓ elegir     ⏎ activar     esc cerrar")

    def confirmar(self) -> None:
        """`⏎`: activa la unidad elegida, o crea la que escribiste.

        Nunca cierra la paleta -- ese es exactamente el punto: activar una
        unidad es entrar en su contexto, no un gesto de una sola vez.
        """
        activa = self.opcion_activa()
        if activa is not None:
            self.unit_activated.emit(activa)
            return
        crear = self.opcion_de_crear()
        if crear is None:
            return
        self.unit_created.emit(crear)
