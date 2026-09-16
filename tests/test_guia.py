from clasificador_video import guia


def test_los_cuartos_van_en_el_prompt_tal_cual():
    texto = guia.prompt_de_sistema(["Recámara 1", "Baño"], patron="")
    assert "- Recámara 1" in texto
    assert "- Baño" in texto


def test_el_patron_entra_como_base_y_no_como_regla():
    texto = guia.prompt_de_sistema(["Sala"], patron="Abres por fuera.")
    assert "Abres por fuera." in texto
    # La instruccion del §5.1 del spec del patron: base, no regla.
    assert "punto de partida" in texto
    assert "no es una regla" in texto


def test_sin_patron_el_prompt_no_habla_de_uno():
    texto = guia.prompt_de_sistema(["Sala"], patron="")
    assert "punto de partida" not in texto


def test_el_contexto_lleva_lo_que_bruno_contesto():
    texto = guia.contexto_de_respuestas(
        {"propiedad": "Quinta de campo", "lucir": "la alberca"}
    )
    assert "Quinta de campo" in texto
    assert "la alberca" in texto


def test_el_prompt_deja_repetir_un_cuarto():
    # En los 15 entregables de Bruno siempre se repite alguno, y en 14 de 15
    # el cuarto con el que abre vuelve a salir.
    texto = guia.prompt_de_sistema(["Aérea", "Sala"], patron="")
    assert "las veces que haga falta" in texto
    assert "ninguno de más" not in texto


def test_el_prompt_pide_decir_por_que_se_repite():
    texto = guia.prompt_de_sistema(["Aérea"], patron="")
    assert "otra vez" in texto


def test_el_prompt_sigue_pidiendo_que_esten_todos():
    # Repetir es libre; saltarse un cuarto no. Un cuarto que no sale ni una
    # vez es material que se te olvida al editar.
    texto = guia.prompt_de_sistema(["Aérea", "Sala"], patron="")
    assert "al menos una vez" in texto


def test_el_prompt_pide_pasos_y_no_cuartos():
    texto = guia.prompt_de_sistema(["Sala"], patron="")
    assert "paso" in texto.lower()


def test_el_contexto_sirve_aunque_no_conteste_nada():
    # El boton esta activo desde el primer momento: un cuerpo roto aqui
    # seria un boton que no funciona.
    assert guia.contexto_de_respuestas({}).strip() != ""


def test_el_cuerpo_trae_sistema_y_usuario():
    cuerpo = guia.cuerpo_del_request(["Sala"], {"lucir": "el jardín"}, patron="")
    roles = [m["role"] for m in cuerpo["messages"]]
    assert roles == ["system", "user"]
    assert cuerpo["model"]


def test_lee_una_respuesta_limpia():
    r = guia.leer_respuesta(
        '{"recorrido": "Abres por fuera.",'
        ' "orden": [{"cuarto": "Sala", "porque": "se entra aquí"}]}'
    )
    assert r.ok
    assert r.recorrido == "Abres por fuera."
    assert r.lista[0].cuarto == "Sala"
    assert r.lista[0].porque == "se entra aquí"
    assert r.lista[0].fuera_del_patron is False


def test_rescata_el_json_envuelto_en_backticks():
    # Los modelos lo hacen aunque se les pida que no. Tratarlo como error
    # seria fallar por una formalidad con la respuesta buena adentro.
    r = guia.leer_respuesta(
        'Claro:\n```json\n{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}\n```\nlisto'
    )
    assert r.ok
    assert r.lista[0].cuarto == "Sala"


def test_un_cuarto_con_llaves_en_el_nombre_no_rompe_el_recorte():
    r = guia.leer_respuesta(
        '{"recorrido": "x", "orden": [{"cuarto": "Sala {grande}"}]}'
    )
    assert r.ok
    assert r.lista[0].cuarto == "Sala {grande}"


def test_marca_el_cuarto_que_se_salio_del_patron():
    r = guia.leer_respuesta(
        '{"recorrido": "x", "orden": [{"cuarto": "Alberca",'
        ' "porque": "la subí porque dijiste que hay que lucirla",'
        ' "fuera_del_patron": true}]}'
    )
    assert r.lista[0].fuera_del_patron is True


def test_el_porque_puede_faltar_sin_tumbar_la_respuesta():
    # Bruno lo pidio, pero si el modelo no lo manda, el ORDEN --que es lo
    # que vino a ver-- sigue sirviendo.
    r = guia.leer_respuesta('{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}')
    assert r.ok
    assert r.lista[0].porque == ""


def test_prosa_en_vez_de_json_es_un_error_con_nombre():
    r = guia.leer_respuesta("Yo creo que primero la sala y luego la cocina.")
    assert not r.ok
    assert not r.lista
    assert "texto" in r.error


def test_json_roto_no_ensena_media_lista():
    r = guia.leer_respuesta('{"orden": [{"cuarto": ')
    assert not r.ok
    assert not r.lista


def test_una_lista_vacia_es_un_error():
    r = guia.leer_respuesta('{"recorrido": "x", "orden": []}')
    assert not r.ok


def test_un_renglon_sin_nombre_de_cuarto_es_un_error():
    r = guia.leer_respuesta('{"recorrido": "x", "orden": [{"porque": "…"}]}')
    assert not r.ok


def test_no_contestar_nada_es_un_error_con_nombre():
    r = guia.leer_respuesta("")
    assert not r.ok
    assert r.error


def _renglones(*nombres):
    return [guia.Renglon(cuarto=n) for n in nombres]


def test_una_lista_que_cuadra_no_marca_nada():
    r = guia.revisar_lista(_renglones("Fachada", "Sala"), ["Sala", "Fachada"])
    assert not r.faltan and not r.inventados


def test_un_cuarto_que_el_modelo_se_salto_sale_como_faltante():
    # El caso que le da razon de ser a todo esto.
    r = guia.revisar_lista(_renglones("Fachada"), ["Fachada", "Cocina"])
    assert r.faltan == ["Cocina"]
    assert not r.inventados


def test_un_cuarto_inventado_sale_marcado():
    r = guia.revisar_lista(_renglones("Fachada", "Bodega"), ["Fachada"])
    assert r.inventados == ["Bodega"]


def test_el_acento_no_se_perdona():
    # Un `.strip().lower()` de mas esconderia justo esto.
    r = guia.revisar_lista(_renglones("Recamara 1"), ["Recámara 1"])
    assert r.faltan == ["Recámara 1"]
    assert r.inventados == ["Recamara 1"]


def test_repetir_un_cuarto_ya_no_es_un_aviso():
    # Abre con la aérea y cierra con la aérea: es cómo edita, no un error.
    r = guia.revisar_lista(
        _renglones("Aérea", "Sala", "Aérea"), ["Aérea", "Sala"]
    )
    assert r.limpia()
    assert guia.avisos_de_la_revision(r) == []


def test_la_revision_ya_no_sabe_de_repetidos():
    # El campo se fue entero: dejarlo vacío «por si acaso» invita a que
    # alguien lo vuelva a llenar.
    assert not hasattr(guia.Revision(), "repetidos")


def test_un_faltante_sigue_avisando_aunque_haya_repetidos():
    r = guia.revisar_lista(
        _renglones("Aérea", "Aérea"), ["Aérea", "Cocina"]
    )
    assert r.faltan == ["Cocina"]
    assert any("Cocina" in a for a in guia.avisos_de_la_revision(r))


def test_un_inventado_sigue_avisando_aunque_haya_repetidos():
    r = guia.revisar_lista(
        _renglones("Aérea", "Bodega", "Aérea"), ["Aérea"]
    )
    assert r.inventados == ["Bodega"]


def test_los_avisos_estan_en_palabras_de_bruno():
    r = guia.revisar_lista(_renglones("Fachada", "Bodega"), ["Fachada", "Cocina"])
    avisos = guia.avisos_de_la_revision(r)
    assert any("Cocina" in a for a in avisos)
    assert any("Bodega" in a for a in avisos)
    assert not any("null" in a or "None" in a for a in avisos)


def test_sin_nada_que_decir_no_hay_avisos():
    r = guia.revisar_lista(_renglones("Sala"), ["Sala"])
    assert guia.avisos_de_la_revision(r) == []
