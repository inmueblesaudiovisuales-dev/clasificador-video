# src/clasificador_video/keyboard.py
from __future__ import annotations

ACTION_KEYS = {"p": "pick", "x": "reject", "u": "none"}


class KeyboardRouter:
    """Traduce teclas 1-9 y P/X/U a acciones (spec §5).

    Si el cuarto activo en la tecla presionada tiene subcuartos conocidos,
    la primera tecla NO resuelve un cuarto -- entra en 'pending_parent' y
    espera la siguiente tecla (que elige el subcuarto), sin limite de
    tiempo entre ambas, tal como especifica el spec.
    """

    def __init__(self, active_rooms: list[str], subrooms: dict[str, list[str]] | None = None):
        self.active_rooms = active_rooms
        self.subrooms = subrooms or {}
        self.pending_parent: str | None = None

    def resolve_room_key(self, key: str) -> list[str] | None:
        if not key.isdigit():
            return None
        index = int(key) - 1
        if index < 0 or index >= len(self.active_rooms):
            return None
        room = self.active_rooms[index]
        if room in self.subrooms and self.subrooms[room]:
            self.pending_parent = room
            return None
        return [room]

    def resolve_subroom_key(self, key: str) -> list[str] | None:
        if self.pending_parent is None:
            return None
        options = self.subrooms.get(self.pending_parent, [])
        if not key.isdigit():
            return None
        index = int(key) - 1
        if index < 0 or index >= len(options):
            return None
        parent = self.pending_parent
        self.pending_parent = None
        return [parent, options[index]]

    def resolve_action_key(self, key: str) -> str | None:
        return ACTION_KEYS.get(key.lower())
