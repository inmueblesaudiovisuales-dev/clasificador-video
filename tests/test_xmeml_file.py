from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import _file_xml


def _clip(has_audio: bool) -> ClipSpec:
    return ClipSpec(
        file_path=Path("/shooting/C0012.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=has_audio,
        duration_frames=900,
    )


def test_file_sin_audio_no_declara_bloque_audio():
    xml_str = _file_xml(_clip(has_audio=False), file_id="file-1")
    root = ET.fromstring(f"<root>{xml_str}</root>")
    file_el = root.find("file")
    assert file_el.get("id") == "file-1"
    assert file_el.find("name").text == "C0012.MP4"
    assert file_el.find("media/video") is not None
    assert file_el.find("media/audio") is None


def test_file_con_audio_declara_dos_bloques_audio():
    xml_str = _file_xml(_clip(has_audio=True), file_id="file-2")
    root = ET.fromstring(f"<root>{xml_str}</root>")
    file_el = root.find("file")
    audio_blocks = file_el.findall("media/audio")
    assert len(audio_blocks) == 2
    assert audio_blocks[0].find("audiochannel/channellabel").text == "left"
    assert audio_blocks[1].find("audiochannel/channellabel").text == "right"


def test_file_pathurl_y_duracion():
    xml_str = _file_xml(_clip(has_audio=False), file_id="file-1")
    root = ET.fromstring(f"<root>{xml_str}</root>")
    file_el = root.find("file")
    assert file_el.find("pathurl").text == "file://localhost/shooting/C0012.MP4"
    assert file_el.find("duration").text == "900"


def test_file_con_nombre_conflictivo_produce_xml_valido():
    clip = ClipSpec(
        file_path=Path("/shooting/Casa & Jardin < 2026.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=False,
        duration_frames=900,
    )
    xml_str = _file_xml(clip, file_id="file-3")
    root = ET.fromstring(f"<root>{xml_str}</root>")
    assert root.find("file/name").text == "Casa & Jardin < 2026.MP4"
