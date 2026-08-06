# src/clasificador_video/player.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

QUALITY_PROFILES: dict[str, float] = {
    "Full": 1.0,
    "1/2": 0.5,
    "1/4": 0.25,
    "1/8": 0.125,
}


class MpvPlayer:
    """Envoltura delgada sobre python-mpv (spec §6): hwdec=videotoolbox
    fijo (validado en vivo el 2026-08-06 contra HEVC 10-bit real de la
    FX30), selector de calidad, y marcado de in/out sobre el tiempo
    actual de reproduccion.
    """

    def __init__(self, mpv_factory: Callable[..., object], wid: int | None = None):
        kwargs: dict = {"hwdec": "videotoolbox"}
        if wid is not None:
            kwargs["wid"] = wid
        self._mpv = mpv_factory(**kwargs)
        self._mpv.pause = True  # estado inicial definido: nunca reproducir solo
        self.in_frame: int | None = None
        self.out_frame: int | None = None

    def open(self, path: Path) -> None:
        self._mpv.play(str(path))

    def play(self) -> None:
        self._mpv.pause = False

    def pause(self) -> None:
        self._mpv.pause = True

    def toggle(self) -> None:
        if self._mpv.pause:
            self.play()
        else:
            self.pause()

    def set_quality(self, profile_name: str) -> None:
        if profile_name not in QUALITY_PROFILES:
            raise ValueError(f"perfil de calidad desconocido: '{profile_name}'")
        self._mpv.vid_scale = QUALITY_PROFILES[profile_name]

    def mark_in(self, fps: float) -> int:
        self.in_frame = round(self._mpv.time_pos * fps)
        return self.in_frame

    def mark_out(self, fps: float) -> int:
        self.out_frame = round(self._mpv.time_pos * fps)
        return self.out_frame

    def clear_in_out(self) -> None:
        self.in_frame = None
        self.out_frame = None
