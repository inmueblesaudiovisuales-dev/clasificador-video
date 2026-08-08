# src/clasificador_video/rooms.py
from __future__ import annotations


class RoomSelection:
    """Los cuartos de la sesion, planos y en orden.

    **El orden ES la asignacion de teclas**: el primero contesta a `1`, el
    segundo a `2`, y del decimo en adelante no hay tecla numerica (el rail lo
    muestra con el badge vacio en vez de mentir con un numero que no
    funciona). Por eso `move` no es cosmetico: reordenar es la unica forma de
    cambiar que tecla le toca a cada cuarto.

    Antes de la F3 esto era el estado del dialogo "configurar cuartos", con
    un catalogo fijo de 17 y cuartos "repetibles" que se numeraban solos
    (`Recamara 1`, `Recamara 2`). Los subcuartos se fueron con esa idea: hoy
    `Recamara 1` es un nombre y nada mas, y los cuartos se crean sobre la
    marcha desde el rail, sin paso previo de configuracion
    (ver DECISIONES.md, "Cuartos: planos, sin techo, sin configuracion
    inicial").
    """

    def __init__(self) -> None:
        self._order: list[str] = []

    def add(self, room: str) -> None:
        room = room.strip()
        # dos cuartos con el mismo nombre serian dos teclas que hacen lo
        # mismo y un grupo partido en dos en la hoja de contactos
        if room and room not in self._order:
            self._order.append(room)

    def insert_at(self, posicion: int, room: str) -> None:
        """Mete un cuarto en una posicion concreta.

        Existe para deshacer un borrado: el cuarto tiene que volver A SU
        LUGAR, porque la posicion es lo que le da la tecla. Reagregarlo con
        `add` lo mandaria al final y le cambiaria el atajo por sorpresa.
        """
        room = room.strip()
        if room and room not in self._order:
            self._order.insert(max(0, min(posicion, len(self._order))), room)

    def rename(self, room: str, nuevo: str) -> None:
        """Cambia el nombre SIN cambiar la posicion: renombrar no puede
        cambiarle la tecla a un cuarto por sorpresa."""
        nuevo = nuevo.strip()
        if not nuevo or nuevo in self._order or room not in self._order:
            return
        self._order[self._order.index(room)] = nuevo

    def move(self, room: str, delta: int) -> None:
        if room not in self._order:
            return
        origen = self._order.index(room)
        destino = origen + delta
        if not 0 <= destino < len(self._order):
            return  # en los extremos no pasa nada, no se envuelve
        self._order.insert(destino, self._order.pop(origen))

    def remove(self, room: str) -> None:
        if room in self._order:
            self._order.remove(room)

    def active_rooms(self) -> list[str]:
        return list(self._order)
