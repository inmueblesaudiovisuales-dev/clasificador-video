"""Los bins: de que camara/tarjeta salio cada clip.

Vive APARTE de `Clip` a proposito. `Clip.to_dict()` es el contrato con el
plugin de Premiere y no se toca -- mismo criterio que ya se uso con los
tamaños, las duraciones y las rotaciones, que viajan al lado en el autosave
en vez de meterse dentro del clip.

Este modulo solo conoce indices de clip y nombres. No sabe de Qt, no lee
disco y no decide como se ve nada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Bin:
    nombre: str
    origen: Path
    clips: list[int] = field(default_factory=list)


class BinTree:
    def __init__(self) -> None:
        self._bins: list[Bin] = []

    def agregar(self, nombre: str, origen: Path, clips: list[int]) -> str:
        """Devuelve el nombre con el que quedo, que puede no ser el pedido."""
        nombre = self._nombre_libre(nombre.strip() or origen.name)
        self._bins.append(Bin(nombre=nombre, origen=origen, clips=list(clips)))
        return nombre

    def _nombre_libre(self, nombre: str) -> str:
        usados = self.nombres()
        if nombre not in usados:
            return nombre
        n = 2
        while f"{nombre} {n}" in usados:
            n += 1
        return f"{nombre} {n}"

    def nombres(self) -> list[str]:
        return [b.nombre for b in self._bins]

    def clips_de(self, nombre: str) -> list[int]:
        for b in self._bins:
            if b.nombre == nombre:
                return list(b.clips)
        return []

    def origen_de(self, nombre: str) -> Path | None:
        """La carpeta de la que salio el bin. El encabezado la escribe
        debajo del nombre, en mono y apagada, para responder «¿de que
        tarjeta salio esto?» sin cambiar de vista."""
        for b in self._bins:
            if b.nombre == nombre:
                return b.origen
        return None

    def bin_de(self, indice: int) -> str | None:
        for b in self._bins:
            if indice in b.clips:
                return b.nombre
        return None

    def renombrar(self, nombre: str, nuevo: str) -> None:
        """Cambia el nombre SIN cambiar la posicion.

        Un nombre repetido se ignora en silencio, con el mismo criterio que
        `RoomSelection.rename`: es una entrada invalida del usuario, no un
        error del programa.
        """
        nuevo = nuevo.strip()
        if not nuevo or nuevo in self.nombres():
            return
        for b in self._bins:
            if b.nombre == nombre:
                b.nombre = nuevo
                return

    def sumar(self, nombre: str, clips: list[int]) -> None:
        for b in self._bins:
            if b.nombre == nombre:
                ya = set(b.clips)
                b.clips.extend(i for i in clips if i not in ya)
                return

    def quitar(self, nombre: str) -> list[int]:
        for i, b in enumerate(self._bins):
            if b.nombre == nombre:
                return self._bins.pop(i).clips
        return []

    def reindexar_tras_quitar(self, quitados: list[int]) -> None:
        """Corre los indices que quedan tras borrar `quitados` de la lista
        de clips.

        Es lo mas facil de romper de todo el modulo. Los bins guardan
        INDICES, no referencias al clip -- asi que borrar los clips 0 y 1
        no solo saca esos dos numeros de cada bin, tambien tiene que
        correr TODOS los indices mayores un lugar hacia atras: el que
        era 2 pasa a ser 0, porque en la lista de clips ya no hay nada
        antes de el. Restar solo la cuenta, sin quitar tambien los
        propios `quitados`, dejaria numeros que ya no corresponden a nada.
        """
        fuera = set(quitados)
        for b in self._bins:
            b.clips = [
                i - sum(1 for q in fuera if q < i)
                for i in b.clips
                if i not in fuera
            ]

    def to_list(self) -> list[dict]:
        return [
            {"nombre": b.nombre, "origen": str(b.origen), "clips": list(b.clips)}
            for b in self._bins
        ]

    @classmethod
    def from_list(cls, datos: list[dict]) -> "BinTree":
        """Reconstruye desde lo que escribio `to_list()` -- o desde lo que
        haya en el autosave, que puede venir de una version distinta o de
        un archivo tocado a mano.

        Se blinda igual que `load_session` en autosave.py: lo que no se
        entiende se descarta en silencio, en vez de reventar
        `_restore_session` y dejar la app sin poder abrir. Un bin cuyos
        `clips` no se pueden leer como enteros se descarta entero -- es
        mas facil de razonar que adivinar cuales de sus indices salvar.
        """
        arbol = cls()
        if not isinstance(datos, list):
            return arbol
        for d in datos:
            if not isinstance(d, dict):
                continue
            try:
                clips = [int(i) for i in d.get("clips") or []]
            except (TypeError, ValueError):
                continue
            arbol._bins.append(
                Bin(
                    nombre=str(d.get("nombre") or ""),
                    origen=Path(str(d.get("origen") or "")),
                    clips=clips,
                )
            )
        return arbol

    @classmethod
    def desde_sesion(cls, datos: list[dict] | None, rutas: list[Path]) -> "BinTree":
        """Lo que se usa al restaurar.

        `datos` es `None` solo cuando la sesion es de antes de que
        existieran los bins: ahi se inventa un bin unico con todo el
        material, nombrado con la carpeta del primer clip. `[]` es
        distinto -- es que el usuario se quedo sin bins A PROPOSITO, por
        ejemplo borrando el ultimo -- y no dispara ese invento: hacerlo
        resucitaria justo lo que acaba de borrar.

        Despues de leer `datos`, los indices que ya no caben en `rutas`
        --sesion corrupta, o de un proyecto con menos clips que antes--
        se descartan, y lo que quede sin bin se junta en uno aparte: un
        clip sin bin es un caso que la F4 no contempla, no un estado
        normal de una sesion restaurada.
        """
        if datos is not None:
            arbol = cls.from_list(datos)
            arbol._acotar_a(len(rutas))
            return arbol
        arbol = cls()
        if rutas:
            arbol.agregar(rutas[0].parent.name, rutas[0].parent,
                          list(range(len(rutas))))
        return arbol

    def _acotar_a(self, total_clips: int) -> None:
        asignados: set[int] = set()
        for b in self._bins:
            b.clips = [i for i in b.clips if 0 <= i < total_clips]
            asignados.update(b.clips)
        huerfanos = [i for i in range(total_clips) if i not in asignados]
        if huerfanos:
            self.agregar("Sin bin", Path(), huerfanos)
