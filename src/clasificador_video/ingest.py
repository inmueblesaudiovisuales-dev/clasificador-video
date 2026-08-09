# src/clasificador_video/ingest.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mxf", ".lrf"}

# Como nombra la camara a los proxies: `C0001.MP4` -> `C0001S03.MP4`. Vive
# aca, junto a las extensiones, porque las dos son lo mismo -- hechos sobre
# COMO SE LLAMAN los archivos que salen de la tarjeta. Emparejarlos ya es
# otro problema y vive en `proxy_match.py`, que importa de aca.
SUFIJO_PROXY = "S03"


def es_archivo_de_proxy(ruta: Path) -> bool:
    return ruta.stem.endswith(SUFIJO_PROXY)


@dataclass
class IngestFolder:
    source_path: Path
    display_name: str
    files: list[Path] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.display_name


class IngestTree:
    """Panel de ingest (spec §3): carpetas de nivel superior, una por
    tarjeta/camara importada, sin interpretar el contenido -- el usuario
    clasifica clip por clip despues.
    """

    def __init__(self) -> None:
        self._folders: list[IngestFolder] = []

    def import_folder(self, path: Path) -> None:
        self.import_folders([path])

    def import_folders(self, paths: list[Path]) -> None:
        for path in paths:
            files = sorted(
                p for p in path.iterdir()
                if p.is_file()
                and p.suffix.lower() in VIDEO_EXTENSIONS
                # un proxy no es material: si entra, Bruno ve 256 clips
                # donde hay 128 y clasifica dos veces el mismo plano.
                and not es_archivo_de_proxy(p)
            )
            self._folders.append(IngestFolder(source_path=path, display_name=path.name, files=files))

    def top_level_folders(self) -> list[IngestFolder]:
        return list(self._folders)

    def rename_folder(self, source_path: Path, new_name: str) -> None:
        for folder in self._folders:
            if folder.source_path == source_path:
                folder.display_name = new_name
                return
        raise ValueError(f"carpeta no encontrada en el ingest: {source_path}")
