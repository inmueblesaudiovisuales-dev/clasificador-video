# src/clasificador_video/thumbnails.py
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

MPV_BIN = shutil.which("mpv") or "/opt/homebrew/bin/mpv"


def build_thumbnail_command(video: Path, at_seconds: float, outdir: Path) -> list[str]:
    """Comando validado en vivo el 2026-08-06 contra clips reales de la
    Sony FX30: respeta la rotacion del clip sin flags adicionales, y no
    tiene el problema de extraccion por seek que si afecta a ffmpeg en
    algunos casos limite (ver spec 2026-08-06, §2).
    """
    return [
        MPV_BIN,
        "--no-config",
        "--vo=image",
        f"--vo-image-outdir={outdir}",
        f"--start={at_seconds}",
        "--frames=1",
        "--hwdec=videotoolbox",
        str(video),
    ]


def extract_thumbnail(
    video: Path,
    at_seconds: float,
    outdir: Path,
    runner: Callable[[list[str]], None] = lambda cmd: subprocess.run(cmd, capture_output=True, check=False),
) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = build_thumbnail_command(video, at_seconds, outdir)
    runner(cmd)
    frame = outdir / "00000001.jpg"
    if not frame.exists():
        raise RuntimeError(f"mpv no genero ninguna miniatura para {video} en el segundo {at_seconds}")
    return frame
