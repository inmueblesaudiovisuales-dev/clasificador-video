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

    def __init__(self, mpv_factory: Callable[..., object]):
        # vo=libmpv habilita el modo render-API (MpvRenderContext), la via
        # soportada oficialmente para embeber mpv en Qt -- ver ui/video_widget.py.
        # keep_open=always conserva el ultimo frame decodificado al llegar a
        # EOF en vez de descargar el archivo (los clips de prueba duran
        # pocos segundos; sin esto el widget queda negro tras el primer EOF).
        self._mpv = mpv_factory(hwdec="videotoolbox", vo="libmpv", keep_open="always")
        self._mpv.pause = True  # estado inicial definido: nunca reproducir solo
        self.in_frame: int | None = None
        self.out_frame: int | None = None

    @property
    def mpv_handle(self) -> object:
        """La instancia real de mpv, para quien necesite conectar el API de
        render (`ui/video_widget.py`). No exponer mas superficie que esto.
        """
        return self._mpv

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

    @property
    def position(self) -> float:
        """Segundo actual de reproduccion -- 0.0 si mpv todavia no lo
        reporta (recien abierto) o si el doble de pruebas no lo define."""
        return getattr(self._mpv, "time_pos", None) or 0.0

    @property
    def duration(self) -> float:
        """Duracion real del clip segun mpv (mas confiable que la
        calculada de ffprobe al importar) -- 0.0 si todavia no se conoce."""
        return getattr(self._mpv, "duration", None) or 0.0

    @property
    def is_paused(self) -> bool:
        return bool(self._mpv.pause)

    def seek(self, seconds: float) -> None:
        """Salta a una posicion absoluta, clampeada a [0, duration] -- usado
        por el seek con mouse de la ScrubBar (ver ui/video_widget.py)."""
        target = max(0.0, min(seconds, self.duration))
        self._mpv.time_pos = target

    def set_quality(self, profile_name: str) -> None:
        if profile_name not in QUALITY_PROFILES:
            raise ValueError(f"perfil de calidad desconocido: '{profile_name}'")
        self._mpv.vid_scale = QUALITY_PROFILES[profile_name]

    # Los dos pasan por `self.position`, no por `self._mpv.time_pos`: mpv no
    # reporta la posicion apenas se abre el clip, y leerla cruda hacia que
    # apretar `I` en ese momento tirara un TypeError contra None.
    def mark_in(self, fps: float) -> int:
        self.in_frame = round(self.position * fps)
        return self.in_frame

    def mark_out(self, fps: float) -> int:
        self.out_frame = round(self.position * fps)
        return self.out_frame

    def clear_in_out(self) -> None:
        self.in_frame = None
        self.out_frame = None
