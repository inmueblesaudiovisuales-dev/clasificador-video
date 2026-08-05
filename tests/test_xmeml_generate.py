import xml.etree.ElementTree as ET
from pathlib import Path

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import generate_xmeml


def _clip(category_path, name, flag="none", has_audio=False) -> ClipSpec:
    return ClipSpec(
        file_path=Path(f"/shooting/{name}"),
        category_path=category_path,
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=has_audio,
        duration_frames=900,
        flag=flag,
    )


def test_documento_completo_tiene_doctype_y_version():
    xml_str = generate_xmeml("Casa Jardin", [_clip(["Cocina"], "C0001.MP4")])
    assert "<!DOCTYPE xmeml>" in xml_str
    assert '<xmeml version="4">' in xml_str


def test_documento_parsea_y_tiene_bin_raiz_con_nombre_del_proyecto():
    xml_str = generate_xmeml("Casa Jardin", [_clip(["Cocina"], "C0001.MP4")])
    root = ET.fromstring(xml_str)
    root_bin = root.find("bin")
    assert root_bin.find("name").text == "Casa Jardin"


def test_documento_incluye_bins_anidados_y_secuencia():
    clips = [
        _clip(["Recamara 2", "Bano"], "C0003.MP4"),
        _clip(["Cocina"], "C0001.MP4", flag="pick"),
        _clip(["Cocina"], "C0002.MP4", flag="reject"),
    ]
    xml_str = generate_xmeml("Casa Jardin", clips)
    root = ET.fromstring(xml_str)
    children = root.find("bin/children")

    bin_names = [b.find("name").text for b in children.findall("bin")]
    assert "Recamara 2" in bin_names
    assert "Cocina" in bin_names

    assert children.find("sequence") is not None
    assert children.find("sequence/name").text == "Casa Jardin"

    cocina_bin = next(b for b in children.findall("bin") if b.find("name").text == "Cocina")
    labels = [c.find("labels/label2").text for c in cocina_bin.findall("children/clip")]
    assert "Forest" in labels
    assert "Rose" in labels


def test_documento_con_lista_vacia_no_truena():
    xml_str = generate_xmeml("Vacio", [])
    root = ET.fromstring(xml_str)
    assert root.find("bin/children/sequence") is not None


def test_clip_sin_nivel_de_categoria_no_se_envuelve_en_bin_extra():
    xml_str = generate_xmeml("Casa Jardin", [_clip([], "C0009.MP4")])
    root = ET.fromstring(xml_str)
    children = root.find("bin/children")
    assert children.find("clip") is not None
    assert children.find("bin") is None
