# tests/test_thumbnails.py
from pathlib import Path

from clasificador_video.thumbnails import (
    build_strip_ipc_args,
    build_thumbnail_command,
    extract_thumbnail,
    extract_thumbnail_strip,
)


def test_build_thumbnail_command_incluye_start_y_frames_1():
    cmd = build_thumbnail_command(
        video=Path("/shooting/C0012.MP4"),
        at_seconds=3.0,
        outdir=Path("/tmp/thumbs/xyz"),
    )
    assert cmd[0].endswith("mpv")
    assert "--vo=image" in cmd
    assert "--vo-image-outdir=/tmp/thumbs/xyz" in cmd
    assert "--start=3.0" in cmd
    assert "--frames=1" in cmd
    assert "--hwdec=videotoolbox" not in cmd  # sw: no saturar VideoToolbox del reproductor
    assert cmd[-1] == "/shooting/C0012.MP4"


def test_extract_thumbnail_corre_el_comando_y_devuelve_la_ruta_del_frame(tmp_path):
    calls = []

    def fake_runner(cmd):
        calls.append(cmd)
        outdir = Path(next(c for c in cmd if c.startswith("--vo-image-outdir=")).split("=", 1)[1])
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "00000001.jpg").write_bytes(b"fake-jpeg")

    result = extract_thumbnail(
        video=tmp_path / "C0012.MP4",
        at_seconds=3.0,
        outdir=tmp_path / "thumbs",
        runner=fake_runner,
    )

    assert result == tmp_path / "thumbs" / "00000001.jpg"
    assert result.read_bytes() == b"fake-jpeg"
    assert len(calls) == 1


def test_extract_thumbnail_sin_frame_producido_lanza_error_claro(tmp_path):
    def fake_runner(cmd):
        pass  # no escribe nada, simula un fallo silencioso de mpv

    try:
        extract_thumbnail(video=tmp_path / "C0012.MP4", at_seconds=3.0, outdir=tmp_path / "thumbs", runner=fake_runner)
        assert False, "debio lanzar RuntimeError"
    except RuntimeError as e:
        assert "C0012.MP4" in str(e)


def test_build_strip_ipc_args_usa_vo_null_y_socket_ipc():
    cmd = build_strip_ipc_args(video=Path("/shooting/C0012.MP4"), socket_path=Path("/tmp/x/mpv.sock"))
    assert cmd[0].endswith("mpv")
    assert "--idle=yes" in cmd
    assert "--vo=null" in cmd
    assert "--hwdec=no" in cmd
    assert "--input-ipc-server=/tmp/x/mpv.sock" in cmd
    assert cmd[-1] == "/shooting/C0012.MP4"


class _FakeProc:
    def __init__(self):
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        pass


class _FakeConnection:
    """Doble del MpvIpcConnection real: cada comando se resuelve via el
    callback `on_command`, sin socket real ni espera de eventos."""

    def __init__(self, on_command):
        self._on_command = on_command
        self.closed = False

    def command(self, command):
        self._on_command(command)
        return {"error": "success"}

    def wait_for_event(self, event_name, timeout=1.0):
        return True

    def close(self):
        self.closed = True


def test_extract_thumbnail_strip_pide_un_seek_y_una_captura_por_frame(tmp_path):
    seeks = []
    screenshots = []

    def on_command(command):
        if command[0] == "seek":
            seeks.append(command[1])
        elif command[0] == "screenshot-to-file":
            frame_path = Path(command[1])
            frame_path.write_bytes(b"fake-jpeg")
            screenshots.append(frame_path)

    frames = extract_thumbnail_strip(
        video=tmp_path / "C0012.MP4",
        duration_seconds=6.0,
        count=4,
        outdir=tmp_path / "strip",
        popen=lambda cmd: _FakeProc(),
        connect=lambda socket_path: _FakeConnection(on_command),
    )

    assert len(seeks) == 4
    assert seeks[0] == 0.0
    assert len(frames) == 4
    assert all(f.exists() for f in frames)


def test_extract_thumbnail_strip_cierra_el_proceso_de_mpv_al_terminar(tmp_path):
    proc = _FakeProc()

    def on_command(command):
        if command[0] == "screenshot-to-file":
            Path(command[1]).write_bytes(b"fake-jpeg")

    extract_thumbnail_strip(
        video=tmp_path / "C0012.MP4",
        duration_seconds=2.0,
        count=2,
        outdir=tmp_path / "strip",
        popen=lambda cmd: proc,
        connect=lambda socket_path: _FakeConnection(on_command),
    )
    assert proc.terminated


def test_extract_thumbnail_strip_cierra_la_conexion_ipc_al_terminar(tmp_path):
    conn = _FakeConnection(lambda command: None)
    extract_thumbnail_strip(
        video=tmp_path / "C0012.MP4",
        duration_seconds=2.0,
        count=2,
        outdir=tmp_path / "strip",
        popen=lambda cmd: _FakeProc(),
        connect=lambda socket_path: conn,
    )
    assert conn.closed


def test_extract_thumbnail_strip_frame_que_no_se_genero_se_descarta(tmp_path):
    """Si mpv no logra escribir un frame (ej. seek fuera de rango), la
    tira sigue con los que si se generaron -- no lanza ni rellena huecos."""
    def on_command(command):
        if command[0] == "screenshot-to-file" and "strip_00" in command[1]:
            Path(command[1]).write_bytes(b"fake-jpeg")
        # strip_01 nunca se escribe -- simula el frame que fallo

    frames = extract_thumbnail_strip(
        video=tmp_path / "C0012.MP4",
        duration_seconds=4.0,
        count=2,
        outdir=tmp_path / "strip",
        popen=lambda cmd: _FakeProc(),
        connect=lambda socket_path: _FakeConnection(on_command),
    )
    assert len(frames) == 1
