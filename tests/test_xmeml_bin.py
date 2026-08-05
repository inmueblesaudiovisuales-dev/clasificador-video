import xml.etree.ElementTree as ET

from clasificador_video.xmeml import _bin_xml, _group_by_category
from clasificador_video.models import ClipSpec
from pathlib import Path


def _clip(category_path, name) -> ClipSpec:
    return ClipSpec(
        file_path=Path(f"/shooting/{name}"),
        category_path=category_path,
        width=1920,
        height=1080,
        fps=25.0,
        has_audio=False,
        duration_frames=100,
    )


def test_bin_anidado_contiene_subbin_y_clip():
    clips = [
        _clip(["Recamara 2", "Bano"], "C0003.MP4"),
        _clip(["Recamara 2"], "C0004.MP4"),
    ]
    tree = _group_by_category(clips)
    counter = [0]
    xml_str = _bin_xml("Recamara 2", tree["Recamara 2"], counter)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    outer_bin = root.find("bin")
    assert outer_bin.find("name").text == "Recamara 2"

    names_in_children = [child.tag for child in outer_bin.find("children")]
    assert "bin" in names_in_children  # el subbin Bano
    assert "clip" in names_in_children  # el clip suelto de Recamara 2 (sin subcuarto)

    inner_bin = outer_bin.find("children/bin")
    assert inner_bin.find("name").text == "Bano"
    assert inner_bin.find("children/clip") is not None


def test_counter_incrementa_por_cada_clip():
    clips = [_clip(["Cocina"], "C0001.MP4"), _clip(["Cocina"], "C0002.MP4")]
    tree = _group_by_category(clips)
    counter = [0]
    _bin_xml("Cocina", tree["Cocina"], counter)
    assert counter[0] == 2
