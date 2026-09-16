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

    def to_dict(self) -> dict:
        return {
            "proyecto": self.proyecto,
            "orientacion": self.orientacion,
            "clips": [c.to_dict() for c in self.clips],
            "guia": self.guia.to_dict() if self.guia is not None else None,
            "formato_secuencia": self.formato_secuencia,
        }

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
