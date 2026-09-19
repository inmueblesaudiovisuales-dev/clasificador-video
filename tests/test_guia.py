import json

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


def test_leer_clasificacion_ok():
    crudo = json.dumps({"clasificacion": [
        {"cuarto": "Sala", "columna": "sociales"},
        {"cuarto": "Dron", "columna": "apertura"}]})
    r = guia.leer_clasificacion(crudo, ["Sala", "Dron"])
    assert r.ok and r.columna_de == {"Sala": "sociales", "Dron": "apertura"}


def test_leer_clasificacion_ignora_datos_invalidos_y_repetidos():
    crudo = json.dumps({"clasificacion": [
        {"cuarto": "Sala", "columna": "sociales"},
        {"cuarto": "Inventado", "columna": "sociales"},
        {"cuarto": "Sala", "columna": "amenidades"},
        {"cuarto": "Cocina", "columna": "inexistente"}]})
    r = guia.leer_clasificacion(crudo, ["Sala", "Cocina"])
    assert r.ok and r.columna_de == {"Sala": "sociales"}


def test_leer_clasificacion_marca_un_cuarto_inventado_en_vez_de_callarlo():
    # El CLAUDE.md del repo es explicito: "si sobra alguno, el panel lo
    # marca en vez de enseñar la lista como si nada". Un cuarto que el
    # modelo se saco de la manga no debe desaparecer sin dejar rastro.
    crudo = json.dumps({"clasificacion": [
        {"cuarto": "Sala", "columna": "sociales"},
        {"cuarto": "Cuarto Inventado", "columna": "amenidades"}]})
    r = guia.leer_clasificacion(crudo, ["Sala"])
    assert r.ok
    assert r.inventados == ["Cuarto Inventado"]


def test_leer_clasificacion_sin_inventados_la_lista_queda_vacia():
    crudo = json.dumps({"clasificacion": [{"cuarto": "Sala", "columna": "sociales"}]})
    r = guia.leer_clasificacion(crudo, ["Sala"])
    assert r.inventados == []


def test_leer_clasificacion_respuesta_vacia():
    r = guia.leer_clasificacion(None, ["Sala"])
    assert not r.ok and r.error


def test_leer_clasificacion_texto_no_json():
    assert not guia.leer_clasificacion("no traigo json", ["Sala"]).ok


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
