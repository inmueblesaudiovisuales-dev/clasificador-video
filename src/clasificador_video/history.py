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

    # --- lo que la accion le hizo a los BINS -------------------------------
    # Van aparte de `antes` porque el bin NO es un campo del clip: vive en
    # `BinTree`, que es la unica fuente de verdad. `antes` se aplica con
    # `setattr` sobre el clip, y meter aqui un campo que el clip no tiene
    # seria inventarle uno -- justo la duplicacion que hace que dos copias
    # del mismo dato se contradigan.
    #
    # `bins_antes` es `{indice_de_clip: nombre_del_bin}`, con `None` para
    # «estaba suelto», que es un estado valido y no la ausencia de dato.
    bins_antes: dict[int, str | None] | None = None
    bin_creado: str | None = None
    # `(viejo, nuevo)`. No se deduce del texto del renglon: `etiqueta` y
    # `detalle` son para el ojo, y leerlos como dato hace que cambiar una
    # palabra rompa una funcion.
    bin_renombrado: tuple[str, str] | None = None

    id: int = field(default_factory=lambda: next(_ids))

    def habla_de_bins(self) -> bool:
        """Si esta entrada es de un bin o de un cuarto.

        Hace falta porque un cuarto y un bin se pueden llamar IGUAL --«Cocina»
        la camara y «Cocina» el cuarto-- y la `etiqueta` no los distingue.
        Renombrar uno movia el renglon del otro.
        """
        return (self.bins_antes is not None
                or self.bin_creado is not None
                or self.bin_renombrado is not None)


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

    def renombrar_cuarto(self, viejo: str, nuevo: str) -> None:
        """Le cambia el nombre a un cuarto DENTRO de lo ya registrado.

        El historial guarda el `categoria_path` que cada clip tenia antes, o
        sea el NOMBRE del cuarto -- y renombrar no crea un cuarto nuevo, es
        el mismo con otro nombre. Sin esto, deshacer una accion anterior al
        renombrado devolvia el nombre viejo, que ya no existe en el rail: el
        clip quedaba clasificado en un cuarto fantasma, contando como
        clasificado en el progreso pero sin aparecer en ningun renglon, y
        viajando asi a Premiere.

        Tambien se mueve la `etiqueta`, que es como se llama la fila del
        historial: la fila diria «Cocina» de un cuarto que ahora se llama
        de otra forma, y su boton `↺` promete devolverte algo que no existe.
        """
        for entrada in self._entries:
            if entrada.habla_de_bins():
                continue    # es un bin, no un cuarto (ver `habla_de_bins`)
            if entrada.etiqueta == viejo:
                entrada.etiqueta = nuevo
            for campos in entrada.antes.values():
                camino = campos.get("categoria_path")
                if isinstance(camino, list) and camino and camino[0] == viejo:
                    campos["categoria_path"] = [nuevo, *camino[1:]]

    def renombrar_bin(self, viejo: str, nuevo: str) -> None:
        """El gemelo de `renombrar_cuarto`, para el otro eje.

        Un renglon que siga hablando de un bin que ya no existe promete
        devolverte algo inalcanzable: su `↺` no encontraria a donde regresar
        los clips. Solo toca las entradas que hablan de bins, para no
        confundirse con un cuarto que se llame igual.
        """
        for entrada in self._entries:
            if not entrada.habla_de_bins():
                continue
            if entrada.etiqueta == viejo:
                entrada.etiqueta = nuevo
            if entrada.bin_creado == viejo:
                entrada.bin_creado = nuevo
            if entrada.bins_antes is not None:
                entrada.bins_antes = {
                    i: (nuevo if b == viejo else b)
                    for i, b in entrada.bins_antes.items()
                }
            if entrada.bin_renombrado is not None:
                a, b = entrada.bin_renombrado
                entrada.bin_renombrado = (nuevo if a == viejo else a,
                                          nuevo if b == viejo else b)

    def entries(self) -> list[HistoryEntry]:
        return list(self._entries)

    def can_undo(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        """Al importar material nuevo: lo de antes ya no aplica a nada."""
        self._entries.clear()
