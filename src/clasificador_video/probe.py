import json
import subprocess
from pathlib import Path
from typing import Callable

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

    width = int(video_stream["width"])
    height = int(video_stream["height"])
    if _rotation_degrees(video_stream) % 180 == 90:
        width, height = height, width

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": has_audio,
        "duration_frames": round(duration_seconds * fps),
    }
