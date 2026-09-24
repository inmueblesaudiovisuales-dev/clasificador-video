import pytest

from clasificador_video.orientacion_premiere import RotacionNoMapeada, orientacion_de


def test_rotacion_del_sony_y_dji_real_da_8():
    assert orientacion_de(90) == 8


def test_sin_rotacion_da_orientacion_normal():
    assert orientacion_de(0) == 1


def test_rotacion_no_confirmada_avisa_en_vez_de_adivinar():
    with pytest.raises(RotacionNoMapeada):
        orientacion_de(45)
