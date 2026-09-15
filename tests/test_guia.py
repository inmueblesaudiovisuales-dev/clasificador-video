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
