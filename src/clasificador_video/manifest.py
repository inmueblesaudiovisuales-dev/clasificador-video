# src/clasificador_video/manifest.py
from __future__ import annotations

from dataclasses import dataclass, field
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
    # traducción cámara→color vive en el generador de .prproj. Aquí se
    # guarda el dato, no la presentación.
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
class Guia:
    """La guía de edición aceptada para ordenar el proyecto de Premiere.

    `orden` es el guion de un proyecto sin unidades (lista plana de nombres,
    con repetidos). `unidades` es el de un proyecto con unidades: el orden de
    las unidades y, por unidad, el orden de sus cuartos. Un proyecto usa una
    u otra, nunca las dos.
    """

    orden: list[str] = field(default_factory=list)
    unidades: list[dict] = field(default_factory=list)



@dataclass
class Manifest:
    proyecto: str
    orientacion: str
    clips: list[Clip] = field(default_factory=list)
    # `None` es un proyecto sin guía, y es un caso normal: Bruno nunca
    # apretó el botón, o se cayó la red. Todo lo demás funciona igual.
    guia: Guia | None = None
