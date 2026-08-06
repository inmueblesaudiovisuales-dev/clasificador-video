# src/clasificador_video/ingest.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mxf", ".lrf"}


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
                if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
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
