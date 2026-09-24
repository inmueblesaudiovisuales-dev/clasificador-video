"""Leer y escribir un .prproj real (gzip + XML)."""
import xml.etree.ElementTree as ET

from clasificador_video import prproj_xml, recursos


def test_leer_prproj_devuelve_un_elemento_premieredata():
    raiz = prproj_xml.leer_prproj(recursos.template_color_luts())
    assert raiz.tag == "PremiereData"


def test_escribir_y_releer_prproj_da_el_mismo_xml(tmp_path):
    raiz = prproj_xml.leer_prproj(recursos.template_color_luts())
    destino = tmp_path / "copia.prproj"

    prproj_xml.escribir_prproj(raiz, destino)
    releido = prproj_xml.leer_prproj(destino)

    assert ET.tostring(releido) == ET.tostring(raiz)
