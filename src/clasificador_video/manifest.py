# src/clasificador_video/manifest.py
from __future__ import annotations

import json
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
