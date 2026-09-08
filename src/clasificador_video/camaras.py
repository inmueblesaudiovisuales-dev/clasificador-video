"""De qué cámara salió un clip, y por lo tanto de qué color llega a Premiere.

Vive aparte de `bins.py` a proposito: `BinTree` sabe QUE bin tiene que
camara, y este modulo sabe COMO se averigua. Son dos preguntas distintas y
la segunda es la unica que mira nombres de archivo.

Sin Qt y sin tocar disco: se responde con el nombre, no abriendo el video.
Abrir 205 archivos para leerles los metadatos al importar seria pagar
segundos por un dato que el nombre ya trae.
"""
from __future__ import annotations

from pathlib import Path

SONY = "sony"
DJI = "dji"
OTRA = "otra"

# En el orden en que salen en el menu del bin.
CAMARAS = (SONY, DJI, OTRA)

# Lo que Bruno dijo, y es la regla entera: «los de DJI por lo general tienen
# el nombre DJI, los que no por lo general serán sony».
_MARCA_DEL_DRON = "dji"


def camara_de_archivo(ruta: Path) -> str:
    """La camara de UN archivo, por su nombre.

    Solo el nombre del archivo, nunca la carpeta: una carpeta que se llame
    «02. VIDEO DRONE» puede tener material de la Sony adentro --pasa cuando
    se copia una tarjeta al lugar equivocado-- y lo que identifica a una
    camara es como NOMBRA ella sus archivos.

    Nunca devuelve `OTRA`: esa es la valvula para lo que no es ninguna de
    las dos, y solo se pone a mano.
    """
    return DJI if _MARCA_DEL_DRON in ruta.name.lower() else SONY


def camara_de_bin(rutas: list[Path]) -> str:
    """La camara de una tanda: la de la mayoria de sus archivos.

    Por mayoria y no por el primero, porque el primero es un accidente del
    orden en que llegaron. Un bin con 70 del dron y uno de la Sony que se
    colo es del dron, y decirlo al reves pintaria 70 clips mal.

    Un empate --y una lista vacia-- se va a `SONY`: hace falta UNA respuesta,
    y es la camara con la que Bruno graba casi todo. Un bin recien creado con
    «+ Bin nuevo» todavia no tiene archivos y tambien pasa por aqui.
    """
    del_dron = sum(1 for r in rutas if camara_de_archivo(r) == DJI)
    return DJI if del_dron * 2 > len(rutas) else SONY
