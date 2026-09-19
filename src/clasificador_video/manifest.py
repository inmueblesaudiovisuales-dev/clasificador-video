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
    # Si el BIN de importacion del que salio este clip tenia "dron" en su
    # nombre. Señal aparte de `camara` (esa mira el nombre del archivo, esta
    # el nombre del bin) y solo sirve para la marca [DRONE] de la carpeta de
    # su cuarto en Premiere. Ver `marca_dron.py` y
    # docs/superpowers/specs/2026-09-18-marca-drone-en-carpetas-design.md.
    bin_dron: bool = False
    # Igual que `bin_dron`, pero para las otras dos cámaras que el sistema
    # de marcas reconoce. Ver `marca_camara.py`.
    bin_sony: bool = False
    bin_pocket: bool = False
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
            "bin_dron": self.bin_dron,
            "bin_sony": self.bin_sony,
            "bin_pocket": self.bin_pocket,
            "ruta_proxy": str(self.ruta_proxy) if self.ruta_proxy is not None else None,
        }


@dataclass
class RenglonDeGuia:
    cuarto: str
    porque: str = ""
    # Que el modelo se apartó del patrón de Bruno en ESTE cuarto. Viaja
    # porque es lo que el panel de Premiere marca: es información que solo
    # tenía la IA. Los avisos de la revisión --«le falta la cocina»-- NO
    # viajan: ésos Bruno ya los vio en Clipify y decidió.
    fuera_del_patron: bool = False

    def to_dict(self) -> dict:
        return {
            "cuarto": self.cuarto,
            "porque": self.porque,
            "fuera_del_patron": self.fuera_del_patron,
        }


@dataclass
class Guia:
    """La guía de edición, congelada. El plugin la LEE y nunca la pide."""

    recorrido: str = ""
    orden: list[RenglonDeGuia] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "recorrido": self.recorrido,
            "orden": [r.to_dict() for r in self.orden],
        }


@dataclass
class Manifest:
    proyecto: str
    orientacion: str
    clips: list[Clip] = field(default_factory=list)
    # `None` es un proyecto sin guía, y es un caso normal: Bruno nunca
    # apretó el botón, o se cayó la red. Todo lo demás funciona igual.
    guia: Guia | None = None
    formato_secuencia: str | None = None
    # Solo los JSON exportados desde este flujo piden el nuevo conjunto de
    # cinco secuencias. Un JSON anterior conserva su comportamiento.
    crear_secuencias: bool = False

    def to_dict(self) -> dict:
        datos = {
            "proyecto": self.proyecto,
            "orientacion": self.orientacion,
            "clips": [c.to_dict() for c in self.clips],
            "guia": self.guia.to_dict() if self.guia is not None else None,
            "formato_secuencia": self.formato_secuencia,
        }
        if self.crear_secuencias:
            datos.pop("formato_secuencia")
            datos["crear_secuencias"] = True
        return datos

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
