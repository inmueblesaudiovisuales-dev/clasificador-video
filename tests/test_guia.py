from clasificador_video import guia


def test_las_columnas_son_las_siete_del_patron_en_orden():
    assert [c.id for c in guia.COLUMNAS] == [
        "apertura", "sociales", "habitaciones", "aerea_media",
        "amenidades", "area_general", "aerea_final",
    ]
