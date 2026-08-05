def rate_for_fps(fps: float) -> tuple[int, bool]:
    """Devuelve (timebase, ntsc) para declarar <rate> en xmeml.

    timebase es el fps redondeado al entero mas cercano. ntsc es True
    cuando el fps real no es un entero exacto (29.97, 23.976, 59.94...),
    False cuando si lo es (24, 25, 30, 50, 60).
    """
    timebase = round(fps)
    ntsc = abs(fps - timebase) > 0.001
    return timebase, ntsc
