"""Los proyectos abiertos ultimamente, el mas reciente primero.

Vive junto a la sesion, en `~/.clasificador_video/`. Es una comodidad, no un
dato del que dependa nada: si el archivo se corrompe o desaparece, la lista
sale vacia y la app abre igual. Cambiar esa comodidad por un ladrillo --que
un JSON roto impida ABRIR-- seria un mal negocio.

Sin Qt.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAXIMO = 10


@dataclass
class Reciente:
    ruta: Path
    nombre: str
    cuando: str

    @property
    def disponible(self) -> bool:
        """Un proyecto que ya no esta en su lugar NO se poda de la lista: se
        marca como no disponible y se muestra apagado. Bruno tiene que poder
        ver que el proyecto existio y que el disco no esta conectado, en vez
        de que desaparezca sin explicacion."""
        return self.ruta.exists()


class Recientes:
    def __init__(self, archivo: Path) -> None:
        self._archivo = archivo
        self._entradas: list[Reciente] = self._leer()

    def _leer(self) -> list[Reciente]:
        try:
            crudo = json.loads(self._archivo.read_text())
        except (OSError, json.JSONDecodeError, ValueError):
            return []
        if not isinstance(crudo, list):
            return []
        entradas = []
        for d in crudo:
            if not isinstance(d, dict) or not d.get("ruta"):
                continue
            entradas.append(Reciente(
                ruta=Path(str(d["ruta"])),
                nombre=str(d.get("nombre") or Path(str(d["ruta"])).stem),
                cuando=str(d.get("cuando") or ""),
            ))
        return entradas[:MAXIMO]

    def _escribir(self) -> None:
        self._archivo.parent.mkdir(parents=True, exist_ok=True)
        self._archivo.write_text(json.dumps(
            [{"ruta": str(e.ruta), "nombre": e.nombre, "cuando": e.cuando}
             for e in self._entradas],
            indent=2, ensure_ascii=False,
        ))

    def registrar(self, ruta: Path, nombre: str) -> None:
        self._entradas = [e for e in self._entradas if e.ruta != ruta]
        self._entradas.insert(0, Reciente(
            ruta=ruta, nombre=nombre,
            cuando=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        del self._entradas[MAXIMO:]
        self._escribir()

    def quitar(self, ruta: Path) -> None:
        self._entradas = [e for e in self._entradas if e.ruta != ruta]
        self._escribir()

    def lista(self) -> list[Reciente]:
        return list(self._entradas)
