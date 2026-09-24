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


def _premiere_data_de_prueba():
    return ET.fromstring("""
    <PremiereData Version="3">
        <Project ObjectID="1" ClassID="x"><NextID>1000002</NextID></Project>
        <NodoA ObjectID="10" ClassID="a"><Hijo ObjectRef="11"/><Externo ObjectRef="404"/></NodoA>
        <NodoB ObjectID="11" ClassID="b"><Hijo ObjectURef="dd0e0000-0000-0000-0000-000000000001"/></NodoB>
        <NodoC ObjectUID="dd0e0000-0000-0000-0000-000000000001" ClassID="c"><Nombre>original</Nombre></NodoC>
        <NodoNoTocado ObjectID="99" ClassID="z"><Nombre>no se clona</Nombre></NodoNoTocado>
    </PremiereData>
    """)


def test_clonar_por_cierre_copia_todo_lo_alcanzable():
    raiz = _premiere_data_de_prueba()
    mapa = prproj_xml.clonar_por_cierre(raiz, "ObjectID", "10", prproj_xml.AsignadorDeIds(raiz))
    assert set(mapa) == {("ObjectID", "10"), ("ObjectID", "11"), ("ObjectUID", "dd0e0000-0000-0000-0000-000000000001")}
    assert len(raiz.findall("NodoA")) == 2
    assert len(raiz.findall("NodoNoTocado")) == 1


def test_clonar_por_cierre_da_ids_nuevos_y_unicos():
    raiz = _premiere_data_de_prueba()
    prproj_xml.clonar_por_cierre(raiz, "ObjectID", "10", prproj_xml.AsignadorDeIds(raiz))
    assert int(raiz.findall("NodoA")[1].get("ObjectID")) > 99


def test_clonar_por_cierre_reescribe_refs_internas_y_deja_las_externas():
    raiz = _premiere_data_de_prueba()
    prproj_xml.clonar_por_cierre(raiz, "ObjectID", "10", prproj_xml.AsignadorDeIds(raiz))
    nodo_a = raiz.findall("NodoA")[1]
    original, clon = raiz.findall("NodoB")
    assert nodo_a.find("Hijo").get("ObjectRef") == clon.get("ObjectID")
    assert nodo_a.find("Externo").get("ObjectRef") == "404"
    assert original.get("ObjectID") == "11"


def test_clonar_por_cierre_respeta_fronteras():
    raiz = _premiere_data_de_prueba()
    mapa = prproj_xml.clonar_por_cierre(raiz, "ObjectID", "10", prproj_xml.AsignadorDeIds(raiz), fronteras={("ObjectID", "11")})
    assert ("ObjectID", "11") not in mapa
    assert len(raiz.findall("NodoB")) == 1
    assert raiz.findall("NodoA")[1].find("Hijo").get("ObjectRef") == "11"


def test_asignador_de_ids_nunca_repite():
    raiz = _premiere_data_de_prueba()
    asignador = prproj_xml.AsignadorDeIds(raiz)
    ids = {asignador.nuevo_object_id() for _ in range(50)}
    assert len(ids) == 50
