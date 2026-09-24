"""Puerto de uxp-plugin/js/numeroDeCuarto.js."""
from clasificador_video.numero_de_cuarto import con_numero, es_el_mismo_cuarto, sin_numero


def test_con_numero_rellena_a_dos_digitos():
    assert con_numero("Cocina", 3) == "03. Cocina"
    assert con_numero("Cocina", 12) == "12. Cocina"


def test_sin_numero_quita_un_prefijo():
    assert sin_numero("03. Cocina") == "Cocina"
    assert sin_numero("01. 2 Recamaras") == "2 Recamaras"


def test_sin_numero_no_toca_lo_que_bruno_escribio():
    assert sin_numero("2 Recamaras") == "2 Recamaras"


def test_es_el_mismo_cuarto_ignora_numero_y_marca_de_camara():
    assert es_el_mismo_cuarto("03. Cocina", "Cocina")
    assert es_el_mismo_cuarto("03. Cocina [SONY]", "07. Cocina [SONY+DRONE]")


def test_es_el_mismo_cuarto_distingue_acentos():
    assert not es_el_mismo_cuarto("Recamara 1", "Recámara 1")
