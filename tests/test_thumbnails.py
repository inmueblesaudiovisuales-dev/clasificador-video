# tests/test_thumbnails.py
from pathlib import Path

from clasificador_video.thumbnails import build_thumbnail_command, extract_thumbnail


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
