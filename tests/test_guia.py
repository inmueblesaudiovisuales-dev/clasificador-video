from clasificador_video import guia


def test_las_columnas_son_las_siete_del_patron_en_orden():
    assert [c.id for c in guia.COLUMNAS] == [
        "apertura", "sociales", "habitaciones", "aerea_media",
        "amenidades", "area_general", "aerea_final",
    ]


def test_la_guia_ya_no_sabe_de_ia_ni_de_modelos():
    # La IA se fue por completo (handoff 2026-09-24): ya no hay proveedor,
    # ni prompt, ni lectura de respuestas, ni columna de inventados.
    for nombre in ("MODELO", "prompt_de_clasificacion",
                   "cuerpo_de_clasificacion", "leer_clasificacion",
                   "_recortar_json"):
        assert not hasattr(guia, nombre), nombre


def test_cuartos_sin_usar_devuelve_los_que_no_aparecen():
    assert guia.cuartos_sin_usar(
        ["Sala", "Cocina", "Roof garden"], ["Sala", "Cocina"]) == ["Roof garden"]


def test_cuartos_sin_usar_vacio_cuando_todos_aparecen():
    assert guia.cuartos_sin_usar(["Sala"], ["Sala", "Sala"]) == []


def test_ya_no_existe_revisar_lista():
    assert not hasattr(guia, "revisar_lista")
    assert not hasattr(guia, "avisos_de_la_revision")
    assert not hasattr(guia, "Revision")


def test_renglon_solo_tiene_cuarto():
    r = guia.Renglon(cuarto="Sala")
    assert r.cuarto == "Sala"
    assert not hasattr(r, "porque") and not hasattr(r, "fuera_del_patron")


def test_respuesta_ya_no_tiene_recorrido():
    r = guia.Respuesta(ok=True, lista=[guia.Renglon(cuarto="Sala")])
    assert r.lista[0].cuarto == "Sala" and not hasattr(r, "recorrido")


# --- clasificar por palabras, sin IA (handoff 2026-09-24) -----------------


def test_clasificar_por_palabras_coloca_cada_termino_canonico():
    casos = {
        "Fachada": "apertura",
        "Aérea": "apertura",
        "Dron": "apertura",
        "Cocina": "sociales",
        "Comedor": "sociales",
        "Recámara 1": "habitaciones",
        "Baño": "habitaciones",
        "Vestidor": "habitaciones",
        "Aérea a media casa": "aerea_media",
        "Alberca": "amenidades",
        "Roof": "amenidades",
        "La propiedad de lejos": "area_general",
        "Aérea final": "aerea_final",
    }
    r = guia.clasificar_por_palabras(list(casos))
    assert r.ok
    assert r.columna_de == casos
    assert r.inventados == []


def test_clasificar_por_palabras_reconoce_sin_acentos_y_en_minusculas():
    r = guia.clasificar_por_palabras(["recamara", "bano", "aerea final"])
    assert r.columna_de == {
        "recamara": "habitaciones",
        "bano": "habitaciones",
        "aerea final": "aerea_final",
    }


def test_clasificar_por_palabras_devuelve_el_nombre_original():
    # Se normaliza una COPIA para buscar el término, pero el nombre que sale
    # es el original, tal cual lo tecleó Bruno.
    r = guia.clasificar_por_palabras(["RECÁMARA Principal"])
    assert list(r.columna_de) == ["RECÁMARA Principal"]
    assert r.columna_de["RECÁMARA Principal"] == "habitaciones"


def test_clasificar_por_palabras_deja_fuera_lo_que_no_reconoce():
    # No se adivina: lo que no trae término se queda en la franja.
    r = guia.clasificar_por_palabras(["Pasillo", "Cocina"])
    assert "Pasillo" not in r.columna_de
    assert r.columna_de == {"Cocina": "sociales"}


def test_clasificar_por_palabras_deja_fuera_un_empate_entre_columnas():
    # «terraza» (sociales) y «alberca» (amenidades) empatan en largo y son
    # columnas distintas: no se adivina.
    r = guia.clasificar_por_palabras(["Terraza con alberca"])
    assert r.columna_de == {}


def test_clasificar_por_palabras_dos_terminos_de_la_misma_columna_no_empatan():
    # «baño» y «recámara» son las dos de habitaciones: no es un empate real.
    r = guia.clasificar_por_palabras(["Baño de la recámara"])
    assert r.columna_de == {"Baño de la recámara": "habitaciones"}


def test_clasificar_por_palabras_gana_el_termino_mas_largo():
    # «aerea final» gana sobre «aerea» a secas, que caería en apertura.
    r = guia.clasificar_por_palabras(["Aérea final"])
    assert r.columna_de == {"Aérea final": "aerea_final"}


def test_clasificar_por_palabras_lista_vacia_no_revienta():
    r = guia.clasificar_por_palabras([])
    assert r.ok and r.columna_de == {} and r.inventados == []


def test_clasificar_por_palabras_inventados_siempre_vacio():
    r = guia.clasificar_por_palabras(["Cocina", "Pasillo", "Terraza con alberca"])
    assert r.inventados == []
