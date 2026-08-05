from pathlib import Path

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import _group_by_category


def _clip(category_path, name="C0001.MP4") -> ClipSpec:
    return ClipSpec(
        file_path=Path(f"/shooting/{name}"),
        category_path=category_path,
        width=1920,
        height=1080,
        fps=25.0,
        has_audio=False,
        duration_frames=100,
    )


def test_agrupa_cuartos_sin_subcuarto():
    clips = [_clip(["Cocina"], "C0001.MP4"), _clip(["Sala"], "C0002.MP4")]
    tree = _group_by_category(clips)
    assert list(tree.keys()) == ["Cocina", "Sala"]
    assert tree["Cocina"]["__clips__"][0].file_path.name == "C0001.MP4"


def test_agrupa_subcuartos_anidados():
    clips = [
        _clip(["Recamara 2", "Bano"], "C0003.MP4"),
        _clip(["Recamara 2"], "C0004.MP4"),
    ]
    tree = _group_by_category(clips)
    assert "Recamara 2" in tree
    assert "Bano" in tree["Recamara 2"]
    assert tree["Recamara 2"]["Bano"]["__clips__"][0].file_path.name == "C0003.MP4"
    assert tree["Recamara 2"]["__clips__"][0].file_path.name == "C0004.MP4"


def test_clip_sin_categoria_cae_en_sin_clasificar():
    clips = [_clip(["Sin clasificar"], "C0005.MP4")]
    tree = _group_by_category(clips)
    assert tree["Sin clasificar"]["__clips__"][0].file_path.name == "C0005.MP4"
