from pathlib import Path

from clasificador_video.xmeml import _pathurl, _rate_xml


def test_rate_xml_ntsc():
    xml = _rate_xml(29.97)
    assert "<timebase>30</timebase>" in xml
    assert "<ntsc>TRUE</ntsc>" in xml


def test_rate_xml_no_ntsc():
    xml = _rate_xml(25.0)
    assert "<timebase>25</timebase>" in xml
    assert "<ntsc>FALSE</ntsc>" in xml


def test_pathurl_codifica_espacios():
    url = _pathurl(Path("/Volumes/SHOOTING/Casa con jardin/C0012.MP4"))
    assert url == "file://localhost/Volumes/SHOOTING/Casa%20con%20jardin/C0012.MP4"
