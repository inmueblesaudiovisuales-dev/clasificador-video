from clasificador_video import guia as logica
from clasificador_video.ui.pantalla_guia import TIPOS_DE_PROPIEDAD, PantallaGuia


def _pantalla(qtbot) -> PantallaGuia:
    p = PantallaGuia()
    qtbot.addWidget(p)
    p.resize(640, 560)
    # Sin esto las geometrias salen todas en cero y comparar posiciones no
    # diria nada.
    p.layout().activate()
    return p


def test_los_seis_tipos_de_propiedad(qtbot):
    # Los que de verdad salieron en sus entregables de 2026. Ni cuatro ni
    # los doce del rubro.
    assert TIPOS_DE_PROPIEDAD == [
        "Casa", "Departamento", "Terreno", "Local", "Quinta de campo", "Hospedaje",
    ]


def test_no_pregunta_para_quien_es_el_video(qtbot):
    # Se fue: todo es para redes, era un clic para decir lo de siempre.
    p = _pantalla(qtbot)
    textos = [w.text() for w in p.findChildren(type(p.titulo_lucir))]
    assert not any("para quién" in t.lower() for t in textos)


def test_lo_que_se_quiere_lucir_va_al_frente(qtbot):
    p = _pantalla(qtbot)
    # La caja de «lucir» esta ARRIBA de los chips de tipo: es la pregunta
    # principal.
    assert p.caja_lucir.y() < p.fila_tipos.y()


def test_ensena_la_guia_que_llego(qtbot):
    p = _pantalla(qtbot)
    p.mostrar_respuesta(
        logica.Respuesta(
            ok=True,
            recorrido="Abres por fuera.",
            lista=[
                logica.Renglon(cuarto="Fachada", porque="se entra aquí"),
                logica.Renglon(cuarto="Alberca", porque="la subí", fuera_del_patron=True),
            ],
        ),
        logica.Revision(),
    )
    texto = p.texto_del_resultado()
    assert "Abres por fuera." in texto
    assert "1. Fachada" in texto
    assert "2. Alberca" in texto


def test_marca_el_cuarto_que_se_salio_del_patron(qtbot):
    p = _pantalla(qtbot)
    p.mostrar_respuesta(
        logica.Respuesta(
            ok=True, recorrido="x",
            lista=[logica.Renglon(cuarto="Alberca", porque="la subí", fuera_del_patron=True)],
        ),
        logica.Revision(),
    )
    assert "la subí" in p.texto_del_resultado()


def test_los_avisos_de_la_revision_se_ven_arriba(qtbot):
    p = _pantalla(qtbot)
    p.mostrar_respuesta(
        logica.Respuesta(ok=True, recorrido="x", lista=[logica.Renglon(cuarto="Sala")]),
        logica.Revision(faltan=["Cocina"]),
    )
    assert "Cocina" in p.avisos_label.text()


def test_un_error_se_ve_y_no_deja_lista_a_medias(qtbot):
    p = _pantalla(qtbot)
    p.mostrar_respuesta(
        logica.Respuesta(ok=False, error="No se pudo armar la guía: no hay internet."),
        logica.Revision(),
    )
    assert "internet" in p.avisos_label.text()
    assert p.texto_del_resultado().strip() == ""
    assert not p.usar_button.isEnabled()


def test_usar_este_orden_emite_el_orden(qtbot):
    p = _pantalla(qtbot)
    p.mostrar_respuesta(
        logica.Respuesta(
            ok=True, recorrido="x",
            lista=[logica.Renglon(cuarto="Fachada"), logica.Renglon(cuarto="Sala")],
        ),
        logica.Revision(),
    )
    with qtbot.waitSignal(p.orden_aceptado) as blocker:
        p.usar_button.click()
    assert blocker.args[0] == ["Fachada", "Sala"]
