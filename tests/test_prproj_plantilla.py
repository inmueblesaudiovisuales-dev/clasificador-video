"""Localizar arquetipos dentro de la plantilla real."""
import pytest

from clasificador_video import prproj_plantilla, prproj_xml, recursos


@pytest.fixture
def raiz():
    return prproj_xml.leer_prproj(recursos.template_color_luts())


def test_archetipos_de_clip_encuentra_sony_y_dji(raiz):
    assert set(prproj_plantilla.archetipos_de_clip(raiz)) == {"sony", "dji", "otra"}


def test_archetipo_sony_tiene_el_lut_correcto(raiz):
    assert prproj_plantilla.archetipos_de_clip(raiz)["sony"].ruta_lut.endswith("SONY-SLOG3.cube")


def test_archetipo_dji_tiene_el_lut_correcto(raiz):
    assert prproj_plantilla.archetipos_de_clip(raiz)["dji"].ruta_lut.endswith("DJI-DLOGM.cube")


def test_archetipo_otra_no_tiene_lut(raiz):
    assert prproj_plantilla.archetipos_de_clip(raiz)["otra"].ruta_lut is None


def test_archetipo_de_bin_existe(raiz):
    assert prproj_plantilla.archetipo_de_bin(raiz) is not None


@pytest.mark.skip(reason="se implementa en la Tarea 11")
def test_archetipos_de_secuencia_encuentra_las_2_reales(raiz):
    assert set(prproj_plantilla.archetipos_de_secuencia(raiz)) == {"4k_9x16", "2_7k_9x16"}


def test_plantilla_incompleta_avisa_en_vez_de_adivinar():
    raiz = prproj_xml.leer_prproj(recursos.template_color_luts())
    for elemento in list(raiz):
        if elemento.tag in ("VideoClip", "AudioClip", "ClipProjectItem"):
            raiz.remove(elemento)
    with pytest.raises(prproj_plantilla.PlantillaIncompleta):
        prproj_plantilla.archetipos_de_clip(raiz)
