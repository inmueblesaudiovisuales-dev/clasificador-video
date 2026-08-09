# src/clasificador_video/thumbnails.py
from __future__ import annotations

import hashlib
import json
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Callable

from clasificador_video.binarios import ruta_de


def _mpv() -> str:
    """La ruta de mpv, resuelta CADA VEZ y no al importar.

    Antes era `shutil.which("mpv") or "/opt/homebrew/bin/mpv"`: una ruta de
    Homebrew escrita a mano, que en la computadora de un compañero no
    existe. Y calculada al importar el modulo, asi que ni siquiera se podia
    corregir despues.
    """
    return str(ruta_de("mpv"))


def default_cache_root() -> Path:
    return Path.home() / ".cache" / "clasificador_video" / "thumbnails"


def cache_dir_for(video: Path, cache_root: Path) -> Path:
    """Directorio de cache estable para este clip especifico -- la key
    incluye tamaño y fecha de modificacion ademas de la ruta, asi que si
    el archivo se reemplaza (mismo nombre, contenido distinto) el cache
    se invalida solo, sin lógica de invalidacion aparte.

    Antes las miniaturas se generaban en un directorio temporal que se
    borraba al cerrar la app -- cada sesion volvia a pagar el costo real
    de extraccion (varios segundos por clip) aunque el material fuera el
    mismo de la sesion anterior."""
    try:
        stat = video.stat()
        key_source = f"{video.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    except OSError:
        key_source = str(video)
    digest = hashlib.sha1(key_source.encode()).hexdigest()
    return cache_root / digest


def build_thumbnail_command(video: Path, at_seconds: float, outdir: Path) -> list[str]:
    """Comando validado en vivo el 2026-08-06 contra clips reales de la
    Sony FX30: respeta la rotacion del clip sin flags adicionales.

    Sin `hwdec`: las miniaturas se decodifican en software a proposito --
    un frame por clip no necesita aceleracion, y se evita que los
    decodificadores videotoolbox en paralelo (o contra el reproductor
    embebido) saturen VideoToolbox y bloqueen la reproduccion (verificado
    en vivo el 2026-08-06 con material real).
    """
    return [
        _mpv(),
        "--no-config",
        "--vo=image",
        f"--vo-image-outdir={outdir}",
        f"--start={at_seconds}",
        "--frames=1",
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


def build_strip_ipc_args(video: Path, socket_path: Path) -> list[str]:
    """mpv en modo idle, sin salida de video (--vo=null) ni hwdec, con un
    socket de control IPC -- una sola sesion sobre la que se mandan varios
    seek + captura, en vez de relanzar mpv por cada frame de la tira.

    Medido en vivo el 2026-08-06 con clips reales de la Sony FX30 (4K
    HEVC): ~1.8s para una tira de 12 frames por esta via, contra ~10.8s
    lanzando mpv una vez por frame (el arranque de mpv, no el seek, es el
    costo dominante -- seekear casi al final de un clip de 6s costo casi
    lo mismo que no seekear nada) y contra ~6s+ decodificando el clip
    entero de corrido con un filtro fps (que ademas escala con la
    duracion del clip, mal sintoma para clips largos reales).
    """
    return [
        _mpv(),
        "--no-config",
        "--idle=yes",
        "--hwdec=no",
        "--vo=null",
        f"--input-ipc-server={socket_path}",
        str(video),
    ]


class MpvIpcConnection:
    """Envoltorio del socket IPC de mpv: lee linea por linea y distingue
    respuestas de comando (objetos con "error") de eventos asincronos
    (objetos con "event") que mpv manda por el mismo socket sin que se
    los pidan -- sin esto, un `recv()` crudo puede devolver un evento en
    vez de la respuesta esperada, o mezclar los dos, y el comando
    siguiente (la captura) se manda antes de que el seek anterior haya
    terminado de aplicarse de verdad."""

    def __init__(self, sock: socket.socket):
        self._sock = sock
        self._reader = sock.makefile("rb")

    def command(self, command: list) -> dict:
        payload = json.dumps({"command": command}) + "\n"
        self._sock.sendall(payload.encode())
        while True:
            line = self._reader.readline()
            if not line:
                raise RuntimeError("el socket IPC de mpv se cerro antes de responder")
            msg = json.loads(line)
            if "event" in msg:
                continue  # notificacion asincrona, no es la respuesta a este comando
            return msg

    def wait_for_event(self, event_name: str, timeout: float = 1.0) -> bool:
        deadline = time.monotonic() + timeout
        self._sock.settimeout(timeout)
        try:
            while time.monotonic() < deadline:
                line = self._reader.readline()
                if not line:
                    return False
                msg = json.loads(line)
                if msg.get("event") == event_name:
                    return True
            return False
        except (socket.timeout, TimeoutError):
            return False
        finally:
            self._sock.settimeout(None)

    def close(self) -> None:
        self._reader.close()
        self._sock.close()


def _connect_ipc(socket_path: Path, timeout: float = 2.0) -> MpvIpcConnection:
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(str(socket_path))
            return MpvIpcConnection(sock)
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    raise RuntimeError(f"no se pudo conectar al socket IPC de mpv en {socket_path}: {last_error}")


def _popen_silent(cmd: list[str]) -> subprocess.Popen:
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def extract_thumbnail_strip(
    video: Path,
    duration_seconds: float,
    count: int,
    outdir: Path,
    popen: Callable[[list[str]], subprocess.Popen] = _popen_silent,
    connect: Callable[[Path], MpvIpcConnection] = _connect_ipc,
) -> list[Path]:
    """Extrae `count` frames espaciados a lo largo del clip, para el scrub
    tipo Final Cut sobre la miniatura de la hoja de contactos. Un solo proceso de
    mpv, varios seek+captura dentro de la misma sesion IPC (ver
    build_strip_ipc_args) -- espera el evento `playback-restart` despues
    de cada seek antes de capturar, que es como mpv avisa que el frame
    nuevo ya esta listo para mostrarse (sin esto: capturas del frame
    viejo, o el comando de captura falla porque el seek todavia no
    termino de aplicarse -- medido en vivo el 2026-08-06)."""
    outdir.mkdir(parents=True, exist_ok=True)
    socket_path = outdir / "mpv.sock"
    if socket_path.exists():
        socket_path.unlink()
    proc = popen(build_strip_ipc_args(video, socket_path))
    frames: list[Path] = []
    try:
        conn = connect(socket_path)
        try:
            step = duration_seconds / count if count > 0 else 0.0
            for i in range(count):
                at_seconds = min(i * step, max(duration_seconds - 0.05, 0.0))
                conn.command(["seek", at_seconds, "absolute"])
                conn.wait_for_event("playback-restart", timeout=1.0)
                frame_path = outdir / f"strip_{i:02d}.jpg"
                conn.command(["screenshot-to-file", str(frame_path), "video"])
                if frame_path.exists():
                    frames.append(frame_path)
        finally:
            conn.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
    return frames
