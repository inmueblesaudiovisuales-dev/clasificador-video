from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import _clip_xml


def _clip(flag="none") -> ClipSpec:
    return ClipSpec(
        file_path=Path("/shooting/C0012.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=False,
        duration_frames=900,
        flag=flag,
    )


def test_clip_sin_flag_no_tiene_labels():
    xml_str = _clip_xml(_clip(flag="none"), index=1)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clip_el = root.find("clip")
    assert clip_el.get("id") == "masterclip-1"
    assert clip_el.get("explodedTracks") == "true"
    assert clip_el.find("ismasterclip").text == "TRUE"
    assert clip_el.find("labels") is None


def test_clip_pick_tiene_label_forest():
    xml_str = _clip_xml(_clip(flag="pick"), index=2)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clip_el = root.find("clip")
    assert clip_el.find("labels/label2").text == "Forest"


def test_clip_reject_tiene_label_rose():
    xml_str = _clip_xml(_clip(flag="reject"), index=3)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clip_el = root.find("clip")
    assert clip_el.find("labels/label2").text == "Rose"
