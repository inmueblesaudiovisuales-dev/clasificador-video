"""El proyecto como documento: lo que se guarda y lo que se lee.

Hasta ahora esto vivia repartido entre `MainWindow._write_autosave_now` y
`app._restore_session`, y el archivo era uno solo y escondido. Aqui esta la
MISMA forma, con nombre propio y con una cosa mas: la ruta de cada clip
**relativa a la carpeta de su bin**, que es lo unico que permite reencontrar
el material en otra computadora -- las absolutas nunca coinciden ahi.

Sin Qt: esto se prueba sin abrir una ventana.
"""
from __future__ import annotations

from pathlib import Path

VERSION = 1


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
        if origen is None:
            continue
        try:
            relativas[indice] = str(Path(clip.ruta).relative_to(origen))
        except ValueError:
            continue  # el archivo no cuelga de la carpeta de su bin
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
