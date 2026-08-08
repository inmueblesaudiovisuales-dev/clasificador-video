# src/clasificador_video/history.py
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

LIMITE_POR_DEFECTO = 50

# Contador de proceso: solo tiene que dar ids distintos dentro de una sesion,
# no persistir ni ser adivinable.
_ids = itertools.count(1)


@dataclass
class HistoryEntry:
    """Una accion del usuario, con lo justo para deshacerla.

    `antes` es `{indice_de_clip: {campo: valor_anterior}}` con **solo los
    campos que esta accion toco**. Guardar el clip entero seria mas simple y
    estaria mal: revertir "Cocina -> 6 clips" tambien borraria el pick que se
    marco despues sobre uno de esos seis. Con campos parciales, cada entrada
    solo pisa lo suyo.

    `cuarto_borrado` solo lo usa el borrado de un cuarto, que ademas de
    desclasificar clips lo saca de la lista. Guarda `(nombre, posicion)` y no
    la lista entera: restaurar la lista completa se llevaba puesto todo lo
    creado despues del borrado. La posicion importa porque es lo que le da la
    tecla al cuarto.
    """

    etiqueta: str          # "Baño 1", "Reject", "IN/OUT"
    detalle: str           # "→ 6 clips", "→ clip 086"
    color: str             # cuadrito de la fila: color de cuarto o de estado
    antes: dict[int, dict]
    cuarto_borrado: tuple[str, int] | None = None
    id: int = field(default_factory=lambda: next(_ids))


class History:
    """Pila de acciones deshacibles, sin nada de Qt.

    Vive aparte de la ventana a proposito: la logica de que se deshace y en
    que orden se puede probar entera sin `qtbot` ni pantalla. Quien aplica el
    estado guardado es `MainWindow`; esto solo lo recuerda.

    **No se guarda en disco.** Es de la sesion abierta: al reabrir se recupera
    el trabajo (de eso se encarga el autosave) pero no el historial.
    """

    def __init__(self, limite: int = LIMITE_POR_DEFECTO):
        self._entries: list[HistoryEntry] = []  # la mas reciente, primera
        self._limite = limite

    def push(self, entry: HistoryEntry) -> None:
        self._entries.insert(0, entry)
        # techo duro: una sesion larga acumularia memoria sin que nadie mire
        # mas alla de las ultimas filas del rail
        del self._entries[self._limite:]

    def undo_last(self) -> HistoryEntry | None:
        """La de arriba, que es la que deshace `⌘Z`."""
        return self._entries.pop(0) if self._entries else None

    def revert(self, entry_id: int) -> HistoryEntry | None:
        """Cualquier fila, no solo la de arriba (DECISIONES.md: «el resto se
        revierte con un click»).

        Devuelve None si esa entrada ya no esta -- pasa con un doble click en
        el mismo boton de revertir.
        """
        for i, entrada in enumerate(self._entries):
            if entrada.id == entry_id:
                return self._entries.pop(i)
        return None

    def entries(self) -> list[HistoryEntry]:
        return list(self._entries)

    def can_undo(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        """Al importar material nuevo: lo de antes ya no aplica a nada."""
        self._entries.clear()
