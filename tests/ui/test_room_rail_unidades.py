# tests/ui/test_room_rail_unidades.py
"""El rail agrupa por unidad. Sin ninguna unidad en el proyecto, se ve
exactamente como siempre -- una sola banda implicita, sin encabezado."""
import pytest

from clasificador_video.ui.room_rail import RoomRail


@pytest.fixture
def rail(qtbot):
    r = RoomRail()
    qtbot.addWidget(r)
    return r


def _mismos_argumentos():
    return dict(
        unidades=["Casa A", "Casa B"],
        rooms_por_unidad={
            "": ["Sin migrar"],
            "Casa A": ["Cocina"],
            "Casa B": ["Cocina", "Baño"],
        },
    )


def test_sin_unidades_se_comporta_como_antes(rail):
    rail.set_rooms_agrupados(
        unidades=[], rooms_por_unidad={"": ["Cocina", "Baño"]},
        counts={("", "Cocina"): 3, ("", "Baño"): 1},
    )
    assert [f.nombre for f in rail.rows] == ["Cocina", "Baño"]


def test_con_unidades_hay_una_banda_por_unidad(rail):
    rail.set_rooms_agrupados(
        unidades=["Casa A", "Casa B"],
        rooms_por_unidad={
            "": ["Sin migrar"],
            "Casa A": ["Cocina"],
            "Casa B": ["Cocina", "Baño"],
        },
        counts={},
    )
    assert [b.nombre for b in rail.unit_bands] == ["Sin unidad", "Casa A", "Casa B"]
    assert [f.nombre for f in rail.rows_por_unidad["Casa A"]] == ["Cocina"]
    assert [f.nombre for f in rail.rows_por_unidad["Casa B"]] == ["Cocina", "Baño"]


def test_bloque_sin_unidad_no_aparece_si_esta_vacio(rail):
    rail.set_rooms_agrupados(
        unidades=["Casa A"], rooms_por_unidad={"": [], "Casa A": ["Cocina"]},
        counts={},
    )
    assert [b.nombre for b in rail.unit_bands] == ["Casa A"]


# --- problema 1: reusar la optimizacion de `set_rooms` (widgets huerfanos) --


def test_llamar_dos_veces_igual_no_recrea_widgets(rail):
    """El mismo bug que ya resolvio `set_rooms`: reconstruir en cada tecla
    aunque nada cambio deja widgets huerfanos (1237 tras 60 teclas, medido
    en la F3). `set_rooms_agrupados` corre en cada tecla via
    `MainWindow._refresh_rail`, asi que necesita el mismo criterio."""
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={("Casa A", "Cocina"): 1})

    bandas_antes = list(rail.unit_bands)
    filas_antes = {llave: list(filas) for llave, filas in rail.rows_por_unidad.items()}

    # solo cambian los conteos, la estructura es identica
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={("Casa A", "Cocina"): 7})

    assert rail.unit_bands == bandas_antes
    for llave, filas in filas_antes.items():
        assert rail.rows_por_unidad[llave] == filas
    fila_cocina_a = rail.rows_por_unidad["Casa A"][0]
    assert fila_cocina_a.count_label.text() == "7"


def test_cambiar_la_estructura_si_reconstruye(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    bandas_antes = list(rail.unit_bands)

    otros_argumentos = dict(
        unidades=["Casa A", "Casa B", "Casa C"],
        rooms_por_unidad={
            "": ["Sin migrar"],
            "Casa A": ["Cocina"],
            "Casa B": ["Cocina", "Baño"],
            "Casa C": ["Recamara"],
        },
    )
    rail.set_rooms_agrupados(**otros_argumentos, counts={})

    assert rail.unit_bands != bandas_antes
    assert [b.nombre for b in rail.unit_bands] == [
        "Sin unidad", "Casa A", "Casa B", "Casa C",
    ]


# --- problema 2: mover/arrastrar un cuarto no debe tocar la unidad ---------
# ---              equivocada cuando dos unidades repiten un nombre --------


def test_mover_un_cuarto_de_una_banda_avisa_con_SU_unidad(rail):
    """`Cocina` existe en Casa A y en Casa B: el aviso tiene que decir de
    cual banda salio, para que quien lo consuma no adivine con la unidad
    activa (que puede ser la otra)."""
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    avisos = []
    rail.room_moved_en_unidad.connect(lambda n, d, u: avisos.append((n, d, u)))

    fila_cocina_b = rail.rows_por_unidad["Casa B"][0]
    assert fila_cocina_b.nombre == "Cocina"
    fila_cocina_b.pedir_mover(+1)

    assert avisos == [("Cocina", 1, "Casa B")]


def test_soltar_un_cuarto_dentro_de_SU_PROPIA_banda_avisa_con_su_unidad(qtbot, rail):
    rail.resize(200, 700)
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail.show()
    qtbot.waitExposed(rail)

    avisos = []
    rail.room_reordered_en_unidad.connect(lambda n, p, u: avisos.append((n, p, u)))

    fila_cocina_b = rail.rows_por_unidad["Casa B"][0]   # Casa B: [Cocina, Baño]
    # posicion 4 = el final de la lista PLANA ("Sin migrar", Cocina@A,
    # Cocina@B, Baño@B), que es tambien el final de la banda de Casa B --
    # despues de "Baño"
    rail.soltar_cuarto("Cocina", 4, origen=fila_cocina_b)

    assert avisos == [("Cocina", 1, "Casa B")]


def test_soltar_un_cuarto_en_OTRA_banda_se_ignora(qtbot, rail):
    """Arrastrar el `Cocina` de Casa B hasta la banda de Casa A no puede
    reordenar el `Cocina` de Casa A en silencio -- son cuartos distintos que
    comparten nombre."""
    rail.resize(200, 700)
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail.show()
    qtbot.waitExposed(rail)

    avisos_unidad = []
    avisos_planos = []
    rail.room_reordered_en_unidad.connect(lambda n, p, u: avisos_unidad.append((n, p, u)))
    rail.room_reordered.connect(lambda n, p: avisos_planos.append((n, p)))

    fila_cocina_b = rail.rows_por_unidad["Casa B"][0]
    # posicion 1: dentro de la banda de "Casa A" ("Sin migrar" ocupa 0,
    # "Cocina" de Casa A ocupa 1) -- no es la banda de origen
    rail.soltar_cuarto("Cocina", 1, origen=fila_cocina_b)

    assert avisos_unidad == []
    assert avisos_planos == []


def test_soltar_sin_saber_de_donde_salio_se_ignora_si_hay_bandas(qtbot, rail):
    """Sin el origen (`event.source()` no era la fila que esperabamos) no
    hay forma segura de saber a que catalogo pertenece -- mejor no tocar
    nada que adivinar mal."""
    rail.resize(200, 700)
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail.show()
    qtbot.waitExposed(rail)

    avisos = []
    rail.room_reordered_en_unidad.connect(lambda n, p, u: avisos.append((n, p, u)))

    rail.soltar_cuarto("Cocina", 2, origen=None)

    assert avisos == []


def test_sin_bandas_soltar_cuarto_se_comporta_exactamente_como_antes(qtbot, rail):
    """Cero regresion para el 90% de los proyectos, que no usan unidades."""
    rail.resize(200, 700)
    rail.set_rooms(["Fachada", "Sala", "Alberca"], {})
    rail.show()
    qtbot.waitExposed(rail)

    avisos = []
    rail.room_reordered.connect(lambda n, p: avisos.append((n, p)))

    rail.soltar_cuarto("Alberca", 0)

    assert avisos == [("Alberca", 0)]


def test_boton_nueva_unidad_emite_unit_created(rail):
    emitidos = []
    rail.unit_created.connect(emitidos.append)
    rail._crear_unidad("Casa C")
    assert emitidos == ["Casa C"]


def test_boton_nueva_unidad_ignora_nombre_vacio(rail):
    emitidos = []
    rail.unit_created.connect(emitidos.append)
    rail._crear_unidad("   ")
    assert emitidos == []


# --- bandas colapsables -----------------------------------------------------


def test_banda_de_unidad_arranca_expandida(qtbot, rail):
    # `isVisible()` de Qt solo dice la verdad con la ventana MOSTRADA -- sin
    # `show()`, cualquier hijo reporta `False` aunque nunca se haya
    # escondido (mismo motivo por el que los tests de arrastre de mas
    # arriba en este archivo llaman `rail.show()` antes de mirar geometria).
    rail.resize(200, 700)
    rail.show()
    qtbot.waitExposed(rail)
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    qtbot.wait(50)
    banda_casa_a = next(b for b in rail.unit_bands if b.nombre == "Casa A")
    assert banda_casa_a.chevron.text() == "▾"
    assert all(f.isVisible() for f in rail.rows_por_unidad["Casa A"])


def test_banda_sin_unidad_no_tiene_flecha(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    banda_sin_unidad = next(b for b in rail.unit_bands if b.nombre == "Sin unidad")
    assert banda_sin_unidad.chevron.text() == ""


def test_clic_en_la_banda_colapsa_y_esconde_sus_filas(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")

    rail._on_toggle_de_banda("Casa B")

    assert banda_casa_b.chevron.text() == "▸"
    assert all(not f.isVisible() for f in rail.rows_por_unidad["Casa B"])
    assert "Casa B" in rail.unidades_colapsadas()


def test_clic_dos_veces_la_vuelve_a_expandir(qtbot, rail):
    rail.show()
    qtbot.waitExposed(rail)
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    qtbot.wait(50)
    rail._on_toggle_de_banda("Casa B")
    rail._on_toggle_de_banda("Casa B")

    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_casa_b.chevron.text() == "▾"
    assert all(f.isVisible() for f in rail.rows_por_unidad["Casa B"])
    assert "Casa B" not in rail.unidades_colapsadas()


def test_colapsar_emite_unidad_colapso_cambiado(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    avisos = []
    rail.unidad_colapso_cambiado.connect(lambda u, c: avisos.append((u, c)))
    rail._on_toggle_de_banda("Casa B")
    assert avisos == [("Casa B", True)]


def test_set_unidades_colapsadas_aplica_a_bandas_existentes(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail.set_unidades_colapsadas(["Casa A"])

    banda_casa_a = next(b for b in rail.unit_bands if b.nombre == "Casa A")
    assert banda_casa_a.chevron.text() == "▸"
    assert all(not f.isVisible() for f in rail.rows_por_unidad["Casa A"])


def test_set_unidades_colapsadas_antes_de_poblar_se_aplica_al_construir(rail):
    rail.set_unidades_colapsadas(["Casa B"])
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})

    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_casa_b.chevron.text() == "▸"
    assert all(not f.isVisible() for f in rail.rows_por_unidad["Casa B"])


def test_expandir_unidad_la_abre_y_avisa(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail._on_toggle_de_banda("Casa B")
    avisos = []
    rail.unidad_colapso_cambiado.connect(lambda u, c: avisos.append((u, c)))

    rail.expandir_unidad("Casa B")

    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_casa_b.chevron.text() == "▾"
    assert avisos == [("Casa B", False)]


def test_expandir_unidad_ya_abierta_no_hace_nada(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    avisos = []
    rail.unidad_colapso_cambiado.connect(lambda u, c: avisos.append((u, c)))
    rail.expandir_unidad("Casa A")
    assert avisos == []


def test_conteo_de_la_banda_suma_sus_cuartos(rail):
    rail.set_rooms_agrupados(
        **_mismos_argumentos(),
        counts={("Casa B", "Cocina"): 3, ("Casa B", "Baño"): 2},
    )
    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_casa_b.contador.text() == "5"


def test_conteo_de_la_banda_se_actualiza_sin_reconstruir(rail):
    rail.set_rooms_agrupados(
        **_mismos_argumentos(),
        counts={("Casa B", "Cocina"): 3, ("Casa B", "Baño"): 2},
    )
    banda_antes = next(b for b in rail.unit_bands if b.nombre == "Casa B")

    rail.set_rooms_agrupados(
        **_mismos_argumentos(),
        counts={("Casa B", "Cocina"): 4, ("Casa B", "Baño"): 2},
    )

    banda_despues = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_despues is banda_antes
    assert banda_despues.contador.text() == "6"


# --- seleccion multiple con Cmd-clic (spec 2026-09-21, tarea 7) -------------


def test_clic_simple_selecciona_solo_esa_fila(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    fila_cocina = rail.rows_por_unidad["Casa B"][0]
    rail._on_clic_en_fila(fila_cocina.nombre, False, "Casa B")
    assert fila_cocina.property("seleccionada") is True


def test_cmd_clic_suma_a_la_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")
    assert cocina.property("seleccionada") is True
    assert banio.property("seleccionada") is True


def test_cmd_clic_en_otra_unidad_reemplaza_la_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina_a = rail.rows_por_unidad["Casa A"][0]
    cocina_b = rail.rows_por_unidad["Casa B"][0]
    rail._on_clic_en_fila(cocina_a.nombre, True, "Casa A")
    rail._on_clic_en_fila(cocina_b.nombre, True, "Casa B")
    assert cocina_a.property("seleccionada") is False
    assert cocina_b.property("seleccionada") is True


def test_cmd_clic_de_nuevo_la_quita_de_la_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    assert cocina.property("seleccionada") is False
    assert banio.property("seleccionada") is True


def test_clic_simple_sobre_fila_ya_en_grupo_no_limpia_la_seleccion(rail):
    """Para poder agarrar cualquiera de las filas seleccionadas y
    arrastrar el grupo entero -- si el clic limpiara de una, arrancar el
    arrastre desde ahi solo llevaria esa fila."""
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")
    rail._on_clic_en_fila(cocina.nombre, False, "Casa B")
    assert cocina.property("seleccionada") is True
    assert banio.property("seleccionada") is True


def test_soltar_sin_arrastre_sobre_fila_del_grupo_si_limpia_la_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")

    rail._on_release_sin_arrastre(cocina.nombre, "Casa B")

    assert cocina.property("seleccionada") is True
    assert banio.property("seleccionada") is False


def test_grupo_para_arrastrar_una_sola_fila_sin_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina = rail.rows_por_unidad["Casa B"][0]
    assert rail._grupo_para_arrastrar(cocina.nombre, "Casa B") == ["Cocina"]


def test_grupo_para_arrastrar_el_grupo_completo_en_orden_del_rail(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    # aunque "Baño" se marco primero, el orden que devuelve es el del rail
    assert rail._grupo_para_arrastrar(cocina.nombre, "Casa B") == ["Cocina", "Baño"]
