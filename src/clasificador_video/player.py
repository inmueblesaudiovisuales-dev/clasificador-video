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

# Las tres del mockup. `L` cicla entre ellas en este orden y vuelve al inicio.
SPEED_PROFILES: tuple[float, ...] = (1.0, 2.0, 4.0)


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

    @property
    def speed(self) -> float:
        """Velocidad de reproduccion. 1.0 si mpv todavia no la reporta o si el
        doble de pruebas no la define -- es el default real de mpv."""
        return getattr(self._mpv, "speed", None) or 1.0

    def set_speed(self, speed: float) -> None:
        """Verificado contra mpv real (2026-08-08): `speed` se escribe incluso
        reproduciendo, y se conserva al cargar otro archivo -- por eso la
        velocidad no se reaplica en cada cambio de clip."""
        if speed not in SPEED_PROFILES:
            raise ValueError(f"velocidad desconocida: {speed}")
        self._mpv.speed = speed

    def set_start_percent(self, percent: int) -> None:
        """Donde arranca cada clip al abrirse. Se usa la opcion `start` y no un
        `seek` posterior: mpv reporta la duracion de forma asincrona, asi que
        un seek justo despues de abrir llega antes de que la duracion exista.
        `start` la resuelve mpv al cargar, cuando ya sabe cuanto dura.
        """
        if not 0 <= percent <= 100:
            raise ValueError(f"porcentaje de arranque fuera de rango: {percent}")
        self._mpv.start = f"{percent}%"

    def step_frame(self, delta: int) -> None:
        """Un cuadro adelante (`delta > 0`) o atras. mpv pausa solo al hacerlo,
        y el estado que reporta la app tiene que coincidir o el boton de play
        muestra lo contrario de lo que hace el video.
        """
        if delta == 0:
            return
        self._mpv.command("frame-step" if delta > 0 else "frame-back-step")
        self._mpv.pause = True

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
