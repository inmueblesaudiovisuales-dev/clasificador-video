# src/clasificador_video/manifest.py
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path


@dataclass
class Clip:
    orden: int
    ruta: Path
    categoria_path: list[str]
    fps: float
    in_frame: int | None = None
    out_frame: int | None = None
    flag: str = "none"  # "none" | "pick" | "reject"
    # De que camara salio. Decide su ETIQUETA DE COLOR en Premiere -- la
    # traduccion camara→color vive del otro lado, en `label.js`, igual que
    # la de flag→carpeta. Aqui viaja el dato, no la presentacion.
    camara: str = "sony"
    ruta_proxy: Path | None = None

    def to_dict(self) -> dict:
        return {
            "orden": self.orden,
            "ruta": str(self.ruta),
            "categoria_path": self.categoria_path,
            "fps": self.fps,
            "in_frame": self.in_frame,
            "out_frame": self.out_frame,
            "flag": self.flag,
            "camara": self.camara,
            "ruta_proxy": str(self.ruta_proxy) if self.ruta_proxy is not None else None,
        }


@dataclass
class Manifest:
    proyecto: str
    orientacion: str
    clips: list[Clip] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proyecto": self.proyecto,
            "orientacion": self.orientacion,
            "clips": [c.to_dict() for c in self.clips],
        }

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


# Cómo se llama, dentro del bin del cuarto, la subcarpeta de cada estado.
#
# Los nombres son los MISMOS que la app usa en sus badges y en el rail
# (`ETIQUETAS_DE_ESTADO`): al cruzar a Premiere no hay que traducir nada
# mentalmente. `pick` y `reject` se quedan en inglés porque así los dice un
# editor en México, igual que en el resto de la app.
#
# **Los destacados van con los picks**, no en carpeta aparte. Decision de
# Bruno el 2026-08-22: un destacado ES un pick, reforzado, y partirlos en dos
# carpetas obligaba a mirar en dos lados para armar la secuencia -- cuando lo
# que uno quiere ahi son «los buenos», todos juntos.
#
# **Y los rejects ya no van a ninguna**: se quedan sueltos en su cuarto.
# Decision de Bruno el 2026-09-08.
#
# Las dos decisiones son la misma, tomada dos veces: una marca en el clip
# vale mas que una carpeta, porque la carpeta esconde y la marca se ve.
# Hasta el 2026-09-08 esa marca era la etiqueta de color; ahora el color dice
# la CAMARA y lo que distingue el estado es el nombre -- «★» al destacado y
# «✕» al reject (ver `nombre.js`). Lo que queda de este diccionario son las
# dos carpetas que si dicen algo que ninguna marca dice: «Picks», que junta
# los buenos para armar, y «Sin marcar», que es la cola de trabajo.
SUBCARPETA_POR_FLAG = {
    "destacado": "Picks",
    "pick": "Picks",
    # `None` a proposito, y NO una llave ausente: el reject se queda SUELTO
    # en la carpeta de su cuarto. Decision de Bruno el 2026-09-08, cuando el
    # reject estreno su «✕» al inicio del nombre en Premiere (`nombre.js`):
    # una carpeta «Rejects» y una tacha son dos formas de decir lo mismo, y
    # de las dos la tacha es la que deja ver el clip sin abrir nada. Escrito
    # aqui como valor y no borrado de la tabla para que se lea que es una
    # decision y no un olvido.
    "reject": None,
    "none": "Sin marcar",
}


def con_subcarpeta_de_estado(clip: Clip) -> Clip:
    """Copia del clip con la subcarpeta de su estado al final del camino.

    `["Cocina"]` + un pick da `["Cocina", "Picks"]`, y de ahí el plugin arma
    la carpeta dentro de la carpeta -- `resolveBinChain` ya sabe anidar, y lo
    tiene probado dentro de Premiere de verdad.

    Se hace SOLO al exportar, con el mismo criterio que
    `_con_el_rango_en_orden`: la sesión guarda el cuarto que el editor marcó,
    y el estado es un campo aparte. Mezclarlos en el dato guardado haría que
    marcar un pick pareciera un cambio de cuarto -- y el historial, la hoja y
    el rail van todos por `categoria_path[0]`.

    **Un clip sin cuarto se deja tal cual.** Su `categoria_path` vacío es lo
    que hace que el plugin lo mande a «Sin clasificar», y esa cadena vive
    allá: escribirla también aquí serían dos lugares diciendo el nombre de
    un mismo bin, que es como se desincronizan.
    """
    if not clip.categoria_path:
        return clip
    subcarpeta = SUBCARPETA_POR_FLAG.get(clip.flag)
    if subcarpeta is None:
        return clip
    return replace(clip, categoria_path=[*clip.categoria_path, subcarpeta])
