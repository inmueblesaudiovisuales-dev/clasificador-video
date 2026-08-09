"""Los proyectos abiertos ultimamente, el mas reciente primero.

Vive junto a la sesion, en `~/.clasificador_video/`. Es una comodidad, no un
dato del que dependa nada: si el archivo se corrompe o desaparece, la lista
sale vacia y la app abre igual. Cambiar esa comodidad por un ladrillo --que
un JSON roto impida ABRIR-- seria un mal negocio.

Sin Qt.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAXIMO = 10


@dataclass
class Reciente:
    ruta: Path
    nombre: str
    cuando: str
    # Un proyecto que ya no esta en su lugar NO se poda de la lista: se
    # marca como no disponible y se muestra apagado. Bruno tiene que poder
    # ver que el proyecto existio y que el disco no esta conectado, en vez
    # de que desaparezca sin explicacion.
    #
    # Se averigua UNA vez, al armar la entrada, y no en cada consulta: el
    # caso que motiva todo esto es un disco de red colgado, donde `exists()`
    # puede bloquear segundos -- y esta lista se lee en el hilo de la
    # interfaz, al arrancar. `None` significa «todavia no se miro».
    disponible: bool | None = None

    def __post_init__(self) -> None:
        if self.disponible is None:
            self.disponible = self.ruta.exists()


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
        vistas: set[Path] = set()
        for d in crudo:
            if not isinstance(d, dict) or not d.get("ruta"):
                continue
            ruta = Path(str(d["ruta"]))
            # sin repetidos: el archivo se puede tocar a mano, y dos
            # renglones de la misma ruta se verian como dos proyectos
            if ruta in vistas:
                continue
            vistas.add(ruta)
            entradas.append(Reciente(
                ruta=ruta,
                nombre=str(d.get("nombre") or ruta.stem),
                cuando=str(d.get("cuando") or ""),
            ))
        return entradas[:MAXIMO]

    def _escribir(self) -> None:
        """Temporal + rename, igual que `proyecto.guardar`: `write_text`
        trunca y despues escribe, asi que morir a medio camino perdia la
        lista entera.

        Y no propaga el `OSError`: `registrar` se llama DENTRO de abrir y de
        crear un proyecto, asi que una comodidad rota --la carpeta sin
        permiso-- impediria abrir el proyecto. Perder los recientes es
        molesto; no poder abrir es un ladrillo.
        """
        tmp = self._archivo.with_suffix(self._archivo.suffix + ".tmp")
        try:
            self._archivo.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(
                [{"ruta": str(e.ruta), "nombre": e.nombre, "cuando": e.cuando}
                 for e in self._entradas],
                indent=2, ensure_ascii=False,
            ))
            os.replace(tmp, self._archivo)
        except OSError:
            pass
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def registrar(self, ruta: Path, nombre: str) -> None:
        # se relee antes de mutar: la pantalla de inicio y la ventana
        # abierta tienen su propia instancia, y escribir lo que una tenia en
        # memoria borraria lo que la otra apunto mientras tanto
        self._entradas = self._leer()
        self._entradas = [e for e in self._entradas if e.ruta != ruta]
        self._entradas.insert(0, Reciente(
            ruta=ruta, nombre=nombre,
            cuando=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        del self._entradas[MAXIMO:]
        self._escribir()

    def quitar(self, ruta: Path) -> None:
        self._entradas = self._leer()
        self._entradas = [e for e in self._entradas if e.ruta != ruta]
        self._escribir()

    def lista(self) -> list[Reciente]:
        return list(self._entradas)
