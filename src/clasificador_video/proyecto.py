"""El proyecto como documento: lo que se guarda y lo que se lee.

Hasta ahora esto vivia repartido entre `MainWindow._write_autosave_now` y
`app._restore_session`, y el archivo era uno solo y escondido. Aqui esta la
MISMA forma, con nombre propio y con una cosa mas: la ruta de cada clip
**relativa a la carpeta de su bin**, que es lo unico que permite reencontrar
el material en otra computadora -- las absolutas nunca coinciden ahi.

Sin Qt: esto se prueba sin abrir una ventana.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

VERSION = 1
EXTENSION = ".cvproj"


def rutas_relativas(clips: list, bins) -> dict[int, str]:
    """Por cada clip, su ruta respecto a la carpeta de su bin.

    Los que no tienen bin, o cuyo archivo esta fuera de la carpeta de su
    bin, quedan fuera: inventarles una relativa con `..` seria una ruta
    fragil que al reencontrar apuntaria a cualquier lado.
    """
    relativas: dict[int, str] = {}
    for indice, clip in enumerate(clips):
        nombre = bins.bin_de(indice)
        if nombre is None:
            continue
        origen = bins.origen_de(nombre)
        # Un bin creado vacio tiene `Path("")`, que pathlib normaliza a «.»
        # -- NO a `None`. Se descarta a proposito y no de casualidad (que es
        # lo que pasaba: `relative_to(".")` truena con una ruta absoluta).
        if origen is None or str(origen) in ("", "."):
            continue
        try:
            relativa = Path(clip.ruta).relative_to(origen)
        except ValueError:
            continue  # el archivo no cuelga de la carpeta de su bin
        # `relative_to` es puramente lexico: si la ruta del clip trae un
        # `..`, devuelve una relativa que se sale de la carpeta. Al
        # reencontrar eso se usa como `carpeta / relativa`, o sea que
        # apuntaria fuera de lo que Bruno señalo.
        if ".." in relativa.parts:
            continue
        relativas[indice] = str(relativa)
    return relativas


def a_dict(proyecto: str, rooms: list[str], clips: list, bins,
           tamanos: dict, duraciones: dict, rotaciones: dict) -> dict:
    return {
        "version": VERSION,
        "proyecto": proyecto,
        "rooms": list(rooms),
        "clips": [c.to_dict() for c in clips],
        # Todo esto va AL LADO de los clips y no adentro: `Clip.to_dict()`
        # es el contrato con el plugin de Premiere y no se toca.
        "tamanos": {str(i): [a, h] for i, (a, h) in tamanos.items()},
        "duraciones": {str(i): s for i, s in duraciones.items()},
        "rotaciones": {str(i): r for i, r in rotaciones.items()},
        "bins": bins.to_list(),
        "relativas": {str(i): r for i, r in rutas_relativas(clips, bins).items()},
    }


def guardar(ruta: Path, data: dict) -> None:
    """Escritura atomica, igual que `autosave.save_session`.

    No se reusa aquella funcion a proposito: son dos cosas distintas que hoy
    se escriben igual --el autosave de la sesion y el documento de Bruno-- y
    atarlas obligaria a que cambien juntas.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        os.replace(tmp, ruta)
    finally:
        # Si la escritura falla a medias --el disco lleno es el caso real--
        # el temporal quedaba a la vista en la carpeta de Bruno, como un
        # `Casa Lomas.cvproj.tmp` que nadie sabe que es. Tras el `replace`
        # ya no existe, y por eso el `missing_ok`.
        tmp.unlink(missing_ok=True)


def abrir(ruta: Path) -> dict | None:
    """`None` si no se pudo leer. Esto corre al elegir un archivo, asi que
    reventar aqui dejaria a Bruno sin forma de salir."""
    try:
        data = json.loads(ruta.read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None
