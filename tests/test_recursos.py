"""Los recursos empacados existen de verdad y se resuelven bien --
sin esto, un typo en un nombre de archivo solo se nota al abrir Premiere."""
from clasificador_video import recursos


def test_carpeta_premiere_existe():
    assert recursos.carpeta_premiere().is_dir()


def test_template_color_luts_existe():
    assert recursos.template_color_luts().is_file()


def test_cube_de_camara_sony_y_dji_existen():
    assert recursos.cube_de_camara("sony").is_file()
    assert recursos.cube_de_camara("dji").is_file()


def test_cube_de_camara_otra_no_tiene_lut():
    assert recursos.cube_de_camara("otra") is None


def test_cube_de_camara_desconocida_no_tiene_lut():
    assert recursos.cube_de_camara("lo-que-sea") is None
