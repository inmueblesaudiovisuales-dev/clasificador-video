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


from clasificador_video.marca_camara import marca_de_camara_del_prefijo, nombre_del_cuarto_con_marca, sin_marca_de_camara


def _clip(categoria_path, **flags):
    base = {"categoria_path": categoria_path, "bin_sony": False, "bin_pocket": False, "bin_dron": False}
    base.update(flags)
    return base


def test_marca_de_camara_del_prefijo_una_sola_camara():
    assert marca_de_camara_del_prefijo([_clip(["Cocina"], bin_sony=True)], ["Cocina"]) == "SONY"


def test_marca_de_camara_del_prefijo_combinada_en_orden_fijo():
    assert marca_de_camara_del_prefijo([_clip(["Cocina"], bin_dron=True, bin_sony=True)], ["Cocina"]) == "SONY+DRONE"


def test_marca_de_camara_del_prefijo_sin_camara_reconocible():
    assert marca_de_camara_del_prefijo([_clip(["Cocina"])], ["Cocina"]) == ""


def test_sin_marca_de_camara_quita_al_inicio_o_al_final():
    assert sin_marca_de_camara("[SONY+DRONE] Cocina") == "Cocina"
    assert sin_marca_de_camara("Cocina [SONY+DRONE]") == "Cocina"


def test_sin_marca_de_camara_no_toca_texto_de_bruno():
    assert sin_marca_de_camara("Cocina [ideas]") == "Cocina [ideas]"


def test_nombre_del_cuarto_con_marca():
    assert nombre_del_cuarto_con_marca("03. Cocina", "Cocina", [_clip(["Cocina"], bin_sony=True)], ["Cocina"]) == "03. Cocina [SONY]"


def test_nombre_del_cuarto_con_marca_sin_camara_no_agrega_nada():
    assert nombre_del_cuarto_con_marca("03. Cocina", "Cocina", [_clip(["Cocina"])], ["Cocina"]) == "03. Cocina"
