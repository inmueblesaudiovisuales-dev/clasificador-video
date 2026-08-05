from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import _clipitem_xml, _file_xml


def _clip(in_frame=None, out_frame=None, rotation=0) -> ClipSpec:
    return ClipSpec(
        file_path=Path("/shooting/C0012.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=False,
        duration_frames=900,
        in_frame=in_frame,
        out_frame=out_frame,
        rotation=rotation,
    )


def test_clipitem_sin_in_out_usa_clip_completo():
    clip = _clip()
    file_xml = _file_xml(clip, "file-1")
    xml_str = _clipitem_xml(clip, "clipitem-1", "masterclip-1", file_xml)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clipitem = root.find("clipitem")
    assert clipitem.get("id") == "clipitem-1"
    assert clipitem.find("masterclipid").text == "masterclip-1"
    assert clipitem.find("in").text == "0"
    assert clipitem.find("out").text == "900"
    assert clipitem.find("file") is not None


def test_clipitem_con_in_out_marcados():
    clip = _clip(in_frame=120, out_frame=600)
    file_xml = _file_xml(clip, "file-1")
    xml_str = _clipitem_xml(clip, "clipitem-1", "masterclip-1", file_xml)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clipitem = root.find("clipitem")
    assert clipitem.find("in").text == "120"
    assert clipitem.find("out").text == "600"


def test_clipitem_sin_rotacion_no_tiene_filtro():
    clip = _clip(rotation=0)
    file_xml = _file_xml(clip, "file-1")
    xml_str = _clipitem_xml(clip, "clipitem-1", "masterclip-1", file_xml)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    assert root.find("clipitem/filter") is None


def test_clipitem_con_rotacion_90_agrega_filtro_basic_motion():
    clip = _clip(rotation=90)
    file_xml = _file_xml(clip, "file-1")
    xml_str = _clipitem_xml(clip, "clipitem-1", "masterclip-1", file_xml)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    filter_el = root.find("clipitem/filter")
    assert filter_el is not None
    assert filter_el.find("effect/effectid").text == "basic"
    assert filter_el.find("effect/parameter/parameterid").text == "rotation"
    assert filter_el.find("effect/parameter/value").text == "-90"
