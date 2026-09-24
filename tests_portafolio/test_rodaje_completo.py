"""Ver más allá de lo usado en el .prproj: deducir la carpeta del
rodaje y listar sus videos -- spec 2026-09-24-modo-portafolio-design.md
("no depende de tener un .cvproj")."""
from pathlib import Path

from clasificador_video_portafolio import rodaje_completo as rc


def test_deduce_la_carpeta_comun_de_varios_clips(tmp_path):
    carpeta = tmp_path / "Casa Reforma" / "01. VIDEOS SONY"
    carpeta.mkdir(parents=True)
    rutas = [carpeta / "clip_014.mov", carpeta / "clip_016.mov"]

    assert rc.deducir_carpeta(rutas) == carpeta


def test_deduce_none_si_los_clips_no_comparten_carpeta(tmp_path):
    a = tmp_path / "sony" / "clip_014.mov"
    b = tmp_path / "dron" / "clip_016.mov"

    assert rc.deducir_carpeta([a, b]) is None


def test_listar_videos_de_la_carpeta(tmp_path):
    carpeta = tmp_path / "material"
    carpeta.mkdir()
    (carpeta / "clip_001.mov").write_text("x")
    (carpeta / "clip_002.mp4").write_text("x")
    (carpeta / "notas.txt").write_text("x")

    videos = rc.listar_videos(carpeta)

    assert {v.name for v in videos} == {"clip_001.mov", "clip_002.mp4"}
