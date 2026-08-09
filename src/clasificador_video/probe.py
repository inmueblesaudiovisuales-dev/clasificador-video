import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

ORIENTACION_SIN_DATOS = "horizontal"

FFPROBE_ARGS = ["-v", "quiet", "-print_format", "json", "-show_format", "-show_streams"]


def _run_ffprobe(path: Path) -> str:
    result = subprocess.run(
        ["ffprobe", *FFPROBE_ARGS, str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _rotation_degrees(video_stream: dict) -> int:
    """Lee la rotacion de despliegue del stream (0 si no trae ninguna).

    Camaras que graban en vertical (o con la camara girada) guardan el frame
    "acostado" en el sensor y una matriz de rotacion para desplegarlo derecho.
    ffprobe reporta esto en side_data_list (formato moderno) o en tags.rotate
    (formato viejo) -- sin leer esto, width/height quedan al reves para un
    clip vertical.
    """
    for side_data in video_stream.get("side_data_list", []):
        if "rotation" in side_data:
            return int(side_data["rotation"])
    rotate_tag = video_stream.get("tags", {}).get("rotate")
    if rotate_tag is not None:
        return int(rotate_tag)
    return 0


def probe_clip(path: Path, runner: Callable[[Path], str] = _run_ffprobe) -> dict:
    """Sondea un archivo de video y devuelve width/height/fps/has_audio/duration_frames.

    `runner` es inyectable para pruebas: recibe la ruta y debe devolver el
    stdout de ffprobe (JSON) como string. width/height ya vienen ajustados
    a la orientacion real de despliegue (ver _rotation_degrees).
    """
    data = json.loads(runner(path))
    video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if video_stream is None:
        raise ValueError(f"ffprobe no encontro pista de video en: {path}")
    audio_streams = [s for s in data["streams"] if s["codec_type"] == "audio"]

    num, den = video_stream["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    duration_seconds = float(data["format"]["duration"])

    has_audio = any(int(s.get("channels", 0)) > 0 for s in audio_streams)

    rotation = _rotation_degrees(video_stream) % 360

    width = int(video_stream["width"])
    height = int(video_stream["height"])
    if rotation % 180 == 90:
        width, height = height, width

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": has_audio,
        "duration_frames": round(duration_seconds * fps),
        "rotation": rotation,
    }


def orientacion_de(ancho: int, alto: int) -> str:
    """`"vertical"` o `"horizontal"` para UN tamaño, ya corregido por
    rotacion (ver `_rotation_degrees`).

    Un clip cuadrado cuenta como horizontal: no es vertical, y hay que
    elegir uno.
    """
    return "vertical" if alto > ancho else "horizontal"


def orientacion_predominante(tamanos: Iterable[tuple[int, int]]) -> str:
    """La orientacion que declara el manifest, sacada del material.

    Hasta la F9 estaba escrita a mano como `"horizontal"` y el material de
    Bruno es mayoria vertical, asi que Premiere armaba la secuencia con la
    forma equivocada.

    Dos reglas que valen la pena escribir:

    - **El empate se va a vertical.** Una secuencia vertical con un clip
      horizontal adentro se arregla en Premiere; al reves, el vertical se
      recorta.
    - **Sin ningun tamaño conocido se deja `"horizontal"`**, el default de
      siempre. No es lo mismo «empataron» que «no sabemos»: una sesion
      restaurada de disco no vuelve a correr ffprobe y no tiene un solo
      tamaño. Ahi no se adivina.
    """
    conocidos = [(a, h) for a, h in tamanos if a > 0 and h > 0]
    if not conocidos:
        return ORIENTACION_SIN_DATOS
    verticales = sum(1 for a, h in conocidos if orientacion_de(a, h) == "vertical")
    return "vertical" if verticales * 2 >= len(conocidos) else "horizontal"
