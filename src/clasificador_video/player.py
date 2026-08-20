# src/clasificador_video/player.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

# Aqui vivia QUALITY_PROFILES («Full 1/2 1/4 1/8»), que alimentaba a
# `set_quality`. Se quito el 2026-08-10: le asignaba a mpv una propiedad que
# NO EXISTE (`vid-scale` no aparece en `mpv --list-properties`), y python-mpv
# la guardaba como un atributo cualquiera del objeto sin quejarse. O sea que
# el control existia, se movia, y no cambiaba absolutamente nada. Bruno lo
# noto antes que nadie: «el boton de resolucion (por ejemplo, 1/8) si hace
# diferencia? porque yo no lo veo».
#
# Tampoco se reemplazo por algo que si funcione. Bajar la resolucion de
# DECODIFICACION --lo que hace Premiere-- necesita un codec que se pueda leer
# por capas (ProRes, RED). El material de Bruno es H.264/HEVC, donde cada
# cuadro se reconstruye a partir de los anteriores y hay que armarlo entero.
# La version de eso que si sirve aqui es el proxy, y ya existe.

# Las tres del mockup. `L` cicla entre ellas en este orden y vuelve al inicio.
SPEED_PROFILES: tuple[float, ...] = (1.0, 2.0, 4.0)


class MpvPlayer:
    """Envoltura delgada sobre python-mpv (spec §6): hwdec=videotoolbox
    fijo (validado en vivo el 2026-08-06 contra HEVC 10-bit real de la
    FX30) y marcado de in/out sobre el tiempo actual de reproduccion.
    """

    def __init__(self, mpv_factory: Callable[..., object]):
        # vo=libmpv habilita el modo render-API (MpvRenderContext), la via
        # soportada oficialmente para embeber mpv en Qt -- ver ui/video_widget.py.
        # keep_open=always conserva el ultimo frame decodificado al llegar a
        # EOF en vez de descargar el archivo (los clips de prueba duran
        # pocos segundos; sin esto el widget queda negro tras el primer EOF).
        # mute=True: la app NO suena, nunca. Decision de Bruno el 2026-08-20
        # --se le ofrecio una tecla para prenderlo y la descarto--. Se
        # clasifica mirando, y un shooting entero sonando mientras recorres
        # clip por clip es ruido y nada mas. Va aqui, en la creacion, y no
        # como un `mute` que se pone despues de abrir: asi no hay un instante
        # en que el primer clip suene antes de callarse.
        self._mpv = mpv_factory(hwdec="videotoolbox", vo="libmpv",
                                keep_open="always", mute=True)
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

    def cerrar(self) -> None:
        """Descarga el archivo y deja el reproductor callado.

        `pause` sola no alcanza: mpv conserva el ultimo cuadro decodificado
        --`keep_open=always`, que es lo que evita el widget negro tras cada
        EOF-- asi que sin el `stop` el visor se queda mostrando un clip que
        ya no esta en el proyecto.
        """
        self._mpv.pause = True
        self._mpv.command("stop")
        self.in_frame = None
        self.out_frame = None

    def apagar(self) -> None:
        """Termina mpv y sus hilos. Despues de esto no se le habla mas.

        `terminate()` y no dejarlo al recolector de basura: python-mpv lo
        dice en su propio docstring, y aqui importa mas todavia --con la
        pantalla de inicio, cada proyecto que Bruno cierra deja un mpv atras
        si nadie lo apaga, y son hilos reales, no objetos--.
        """
        terminar = getattr(self._mpv, "terminate", None)
        if terminar is None:
            return          # un doble de pruebas: no hay hilos que soltar
        try:
            terminar()
        except Exception:
            # Cerrar la ventana no puede fallar por esto. Lo peor que pasa
            # es que mpv se lleve sus hilos al morir el proceso, que es
            # exactamente lo que pasaba antes de que esto existiera.
            pass

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

    def step_frame(self, delta: int, fps: float | None = None) -> None:
        """Un cuadro adelante (`delta > 0`) o atras.

        Los dos sentidos NO usan el mismo mecanismo, y la asimetria esta
        medida contra mpv real (2026-08-08, clip de la FX30 a 59.94 fps):

        - **Adelante va con `frame-step`**, que es exacto y barato: diez
          pulsaciones seguidas dieron diez cuadros, uno por una.
        - **Atras va con un seek exacto de un cuadro**, no con
          `frame-back-step`. Ese comando obliga a mpv a retroceder y volver a
          decodificar, y tarda ~0.25 s: a ritmo humano (una pulsacion cada
          0.2 s) **cinco pulsaciones retrocedieron UN cuadro**, porque las
          que llegan mientras la anterior sigue en vuelo se pierden. Con el
          seek exacto, las mismas cinco pulsaciones dan cinco cuadros.

        **No se escribe `pause` DESPUES de `frame-step`.** mpv lo implementa
        como "despausar, mostrar un cuadro, volver a pausar", asi que esa
        escritura le cae encima y aborta el paso: el cuadro no avanza. Tampoco
        hace falta -- queda pausado solo. Para el seek es al reves: pausar
        ANTES es seguro y evita que retroceder deje el video corriendo.
        """
        if delta == 0:
            return
        if delta > 0:
            self._mpv.command("frame-step")
            return
        cuadro = 1.0 / self._fps_efectivo(fps)
        self._mpv.pause = True
        self._mpv.command("seek", -cuadro, "relative", "exact")

    def _fps_efectivo(self, fps: float | None) -> float:
        """Los fps con que retroceder un cuadro. Se prefiere lo que reporta
        mpv del archivo abierto: es el dato real, contra el que la app trae
        de ffprobe al importar. 30 solo como ultimo recurso, para no dividir
        entre cero con una sesion restaurada sin fps.
        """
        del_archivo = getattr(self._mpv, "container_fps", None)
        return del_archivo or fps or 30.0

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
