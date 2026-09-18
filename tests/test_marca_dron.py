from clasificador_video.marca_dron import bin_dice_dron


def test_un_nombre_con_dron_cuenta():
    assert bin_dice_dron("Dron") is True


def test_un_nombre_con_drone_tambien_cuenta():
    """`dron` es substring de `drone` («**dron**e»), así que una sola regla
    cubre las dos formas de escribirlo."""
    assert bin_dice_dron("DRONE FINAL") is True


def test_no_distingue_mayusculas():
    assert bin_dice_dron("tarjeta dron 2") is True


def test_un_nombre_sin_la_palabra_no_cuenta():
    assert bin_dice_dron("Sony A") is False
    assert bin_dice_dron("Tarjeta 2") is False


def test_un_nombre_vacio_no_cuenta():
    assert bin_dice_dron("") is False
