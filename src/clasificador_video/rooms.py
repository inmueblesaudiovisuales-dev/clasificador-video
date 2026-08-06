# src/clasificador_video/rooms.py
from __future__ import annotations

MASTER_ROOM_LIST: list[str] = [
    "Fachada",
    "Sala",
    "Comedor",
    "Cocina",
    "Recámara",
    "Baño",
    "Estudio/Oficina",
    "Alberca",
    "Jardín/Patio",
    "Terraza",
    "Roof garden",
    "Garage/Cochera",
    "Vestíbulo/Hall",
    "Área de servicio",
    "Dron/Aérea",
    "Amenidades comunes",
    "B-roll/Detalles",
]

REPEATABLE_ROOMS = {"Recámara", "Baño"}


class RoomSelection:
    """Estado del dialogo 'configurar cuartos' (spec app-externa §5).

    Guarda el orden en que se van activando los cuartos -- ese orden es el
    que se le presenta al usuario despues como columna de cuartos.
    """

    def __init__(self) -> None:
        self._order: list[str] = []
        self._counts: dict[str, int] = {}

    def toggle(self, room: str) -> None:
        if room in self._order:
            self._order.remove(room)
        else:
            self._order.append(room)

    def set_count(self, room: str, count: int) -> None:
        assert room in REPEATABLE_ROOMS, f"'{room}' no es un cuarto repetible"
        self._counts[room] = count
        if room in self._order:
            self._order.remove(room)
        if count > 0:
            self._order.append(room)

    def add_custom(self, name: str) -> None:
        self._order.append(name)

    def active_rooms(self) -> list[str]:
        result = []
        for room in self._order:
            if room in self._counts:
                result.extend(f"{room} {i}" for i in range(1, self._counts[room] + 1))
            else:
                result.append(room)
        return result
