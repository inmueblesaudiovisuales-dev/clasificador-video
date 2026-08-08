# src/clasificador_video/keyboard.py
from __future__ import annotations

# Sin `"u": "none"`: era inalcanzable. `MainWindow.handle_key_press`
# intercepta la `u` antes que el router --ahi limpia el in/out del clip-- y
# hace return, asi que el router nunca la veia. El estado neutral se va a
# alcanzar repitiendo `P` o `X` sobre un clip que ya lo tiene (F7).
ACTION_KEYS = {"p": "pick", "x": "reject"}


class KeyboardRouter:
    """Traduce teclas 1-9 y P/X/U a acciones.

    **Una tecla, un cuarto, sin estado intermedio.** Hasta la F3 la primera
    tecla podia no resolver nada y quedarse esperando una segunda para elegir
    un subcuarto (`Recamara 1` → `Baño`), sin limite de tiempo entre ambas.
    Eso se fue con los subcuartos: son cuartos planos y `Baño 1` es un cuarto
    como cualquier otro (ver DECISIONES.md, "Cuartos: planos, sin techo, sin
    configuracion inicial").

    `active_rooms` es la lista viva de la sesion: su ORDEN es el que asigna
    las teclas, asi que cada vez que el rail crea, mueve o borra un cuarto
    hay que volver a pasarla.
    """

    def __init__(self, active_rooms: list[str]):
        self.active_rooms = active_rooms

    def resolve_room_key(self, key: str) -> list[str] | None:
        """Devuelve el `categoria_path` del cuarto, o None si la tecla no es
        de cuarto.

        Sigue siendo una LISTA aunque los cuartos sean planos: es el contrato
        del manifest con el plugin de Premiere, que ya maneja el caso de un
        solo elemento, y no hay ninguna razon para tocarlo.
        """
        if not key.isdigit():
            return None
        index = int(key) - 1
        if index < 0 or index >= len(self.active_rooms):
            return None
        return [self.active_rooms[index]]

    def resolve_action_key(self, key: str) -> str | None:
        return ACTION_KEYS.get(key.lower())
