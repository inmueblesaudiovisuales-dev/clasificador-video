# tests/test_marca_camara.py
from clasificador_video.marca_camara import bin_dice_dron, bin_dice_pocket, bin_dice_sony


def test_bin_dice_dron_por_dron_o_drone():
    assert bin_dice_dron("Dron 12 sept")
    assert bin_dice_dron("Drone footage")
    assert bin_dice_dron("tarjeta dron 2")
    assert not bin_dice_dron("Sony tarde")
    assert not bin_dice_dron("Tarjeta 2")


def test_bin_dice_sony():
    assert bin_dice_sony("Sony mañana")
    assert bin_dice_sony("SONY_FX30")
    assert not bin_dice_sony("Pocket 3")


def test_bin_dice_pocket():
    """"pocket" cubre "Osmo Pocket" completo sin tener que buscar "osmo"."""
    assert bin_dice_pocket("Osmo Pocket tarde")
    assert bin_dice_pocket("POCKET")
    assert not bin_dice_pocket("Osmo Action")


def test_ningun_bin_vacio_o_none_dice_ninguna_camara():
    assert not bin_dice_dron("")
    assert not bin_dice_sony(None)
    assert not bin_dice_pocket(None)
