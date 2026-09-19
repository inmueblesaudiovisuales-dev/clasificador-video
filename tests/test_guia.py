from clasificador_video import guia


def test_las_columnas_son_las_siete_del_patron_en_orden():
    assert [c.id for c in guia.COLUMNAS] == [
        "apertura", "sociales", "habitaciones", "aerea_media",
        "amenidades", "area_general", "aerea_final",
    ]


def test_el_prompt_de_clasificacion_lista_las_siete_columnas():
    texto = guia.prompt_de_clasificacion(["Recámara 1", "Alberca"])
    for c in guia.COLUMNAS:
        assert c.titulo in texto or c.id in texto
        assert c.pista in texto


def test_el_prompt_de_clasificacion_lleva_los_cuartos_tal_cual():
    texto = guia.prompt_de_clasificacion(["Recámara 1", "Baño"])
    assert "Recámara 1" in texto and "Baño" in texto


def test_el_prompt_de_clasificacion_no_pide_prosa():
    texto = guia.prompt_de_clasificacion(["Sala"])
    assert "recorrido" not in texto.lower() and "párrafo" not in texto.lower()


def test_cuerpo_de_clasificacion_arma_el_mensaje():
    cuerpo = guia.cuerpo_de_clasificacion(["Sala", "Cocina"])
    assert cuerpo["model"] == guia.MODELO
    assert cuerpo["messages"][0]["role"] == "system"
    assert "Sala" in cuerpo["messages"][0]["content"]
