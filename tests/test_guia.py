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
