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

    def bin_de(self, indice: int) -> str | None:
        for b in self._bins:
            if indice in b.clips:
                return b.nombre
        return None
