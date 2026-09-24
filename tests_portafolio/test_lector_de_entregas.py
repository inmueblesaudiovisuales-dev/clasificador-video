"""Leer un .prproj hacia atrás: clips usados y sus rangos.

La lectura junta todas las secuencias, como define la spec de Portafolio.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video_portafolio import lector_de_entregas as lector


FIXTURES = Path(__file__).parent / "fixtures"


def test_junta_clips_de_dos_secuencias_distintas():
    usados = lector.clips_usados_en(FIXTURES / "entrega_dos_secuencias.prproj")

    nombres = {u.ruta_origen.name for u in usados}
    assert nombres == {"clip_014.mov", "clip_016.mov", "clip_031.mov"}


def test_un_clip_usado_en_dos_secuencias_no_se_duplica_pero_junta_rangos():
    usados = lector.clips_usados_en(FIXTURES / "entrega_dos_secuencias.prproj")

    compartido = next(u for u in usados if u.ruta_origen.name == "clip_014.mov")
    assert len(compartido.rangos) == 2


def test_rango_trae_in_y_out_en_ticks_de_premiere():
    usados = lector.clips_usados_en(FIXTURES / "entrega_dos_secuencias.prproj")

    clip = next(u for u in usados if u.ruta_origen.name == "clip_016.mov")
    rango = clip.rangos[0]
    assert rango.entra_en == 254016000000
    assert rango.sale_en == 762048000000


def test_prproj_sin_secuencias_da_lista_vacia(tmp_path):
    from clasificador_video import prproj_xml

    ruta = tmp_path / "vacio.prproj"
    prproj_xml.escribir_prproj(ET.Element("PremiereData"), ruta)

    assert lector.clips_usados_en(ruta) == []
