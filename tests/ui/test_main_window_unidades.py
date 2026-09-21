"""_unidad_de / _cuarto_de: el largo del categoria_path decide, no una
posicion fija. Sin unidad es [cuarto]; con unidad es [unidad, cuarto] --
nunca hay un tercer nivel, los subcuartos murieron en la F3."""
import json
from pathlib import Path

import pytest

from clasificador_video.history import CuartoMovido
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    """Mismo doble que el resto de tests de la ventana: sin el, cada
    ventana enciende un mpv de verdad, con sus hilos, para nada."""

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        pass


@pytest.fixture
def main_window(qtbot):
    window = MainWindow(project_name="Casa Jardin", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    qtbot.addWidget(window)
    return window


def test_cuarto_de_sin_unidad():
    assert MainWindow._cuarto_de(["Cocina"]) == "Cocina"


def test_cuarto_de_con_unidad():
    assert MainWindow._cuarto_de(["Casa A", "Cocina"]) == "Cocina"


def test_cuarto_de_vacio():
    assert MainWindow._cuarto_de([]) is None


def test_unidad_de_sin_unidad():
    assert MainWindow._unidad_de(["Cocina"]) is None


def test_unidad_de_con_unidad():
    assert MainWindow._unidad_de(["Casa A", "Cocina"]) == "Casa A"


def test_unidad_de_vacio():
    assert MainWindow._unidad_de([]) is None


def test_room_selection_es_el_catalogo_sin_unidad_por_default(main_window):
    main_window.room_selections[""].add("Cocina")
    assert main_window.room_selection.active_rooms() == ["Cocina"]


def test_activar_unidad_cambia_el_alias_room_selection(main_window):
    main_window.unit_selection.add("Casa A")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections["Casa A"].add("Cocina A")
    main_window._activar_unidad("Casa A")
    assert main_window.room_selection.active_rooms() == ["Cocina A"]
    assert main_window._unidad_activa == "Casa A"


def test_activar_unidad_crea_el_catalogo_si_no_existia(main_window):
    main_window.unit_selection.add("Casa B")
    main_window._activar_unidad("Casa B")
    assert main_window.room_selections["Casa B"].active_rooms() == []
    assert main_window.room_selection is main_window.room_selections["Casa B"]


def test_desactivar_unidad_vuelve_al_catalogo_sin_unidad(main_window):
    main_window.room_selections[""].add("Cocina")
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window._activar_unidad(None)
    assert main_window.room_selection.active_rooms() == ["Cocina"]
    assert main_window._unidad_activa is None


def test_guardar_y_reabrir_conserva_unidades_y_sus_cuartos(qtbot, tmp_path, main_window):
    from clasificador_video.app import abrir_proyecto

    main_window.session_path = tmp_path / "p.cvproj"
    main_window.unit_selection.add("Casa A")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections["Casa A"].add("Cocina")
    main_window._write_autosave_now()
    assert main_window._autosave_pool.waitForDone(2000)

    reabierta = abrir_proyecto(main_window.session_path, video_factory=FakeMpv,
                               recientes_path=tmp_path / "r.json")
    qtbot.addWidget(reabierta)

    assert reabierta.unit_selection.active_rooms() == ["Casa A"]
    assert reabierta.room_selections["Casa A"].active_rooms() == ["Cocina"]
    assert (reabierta.room_selection.active_rooms()
            == reabierta.room_selections[""].active_rooms())


def test_ctrl_u_abre_la_paleta_de_unidades(main_window, qtbot):
    main_window.unit_selection.add("Casa A")
    main_window._abrir_paleta_de_unidades()
    assert not main_window.unit_palette.isHidden()


def test_elegir_unidad_en_la_paleta_activa_esa_unidad(main_window):
    main_window.unit_selection.add("Casa A")
    main_window._on_unidad_elegida_en_paleta("Casa A")
    assert main_window._unidad_activa == "Casa A"


def test_crear_unidad_en_la_paleta_la_agrega_y_la_activa(main_window):
    main_window._on_unidad_creada_en_paleta("Casa Nueva")
    assert main_window.unit_selection.active_rooms() == ["Casa Nueva"]
    assert main_window._unidad_activa == "Casa Nueva"


def test_on_enter_ofrece_solo_los_cuartos_de_la_unidad_activa(main_window):
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window.room_selection.add("Cocina A")
    main_window._on_enter()
    assert main_window.room_palette.opciones_visibles() == ["Cocina A"]


def test_asignar_cuarto_sin_unidad_activa_no_cambia(main_window):
    main_window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    main_window._asignar_cuarto(["Cocina"])
    assert main_window.clips[0].categoria_path == ["Cocina"]


def test_asignar_cuarto_con_unidad_activa_prefija_la_unidad(main_window):
    main_window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window._asignar_cuarto(["Cocina"])
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]


def test_ultimo_cuarto_usado_no_lleva_la_unidad(main_window):
    # _ultimo_cuarto_usado es el nombre del CUARTO -- lo que S vuelve a
    # ofrecer -- no el categoria_path completo
    main_window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window._asignar_cuarto(["Cocina"])
    assert main_window._ultimo_cuarto_usado == "Cocina"


def test_asignar_unidad_conserva_el_cuarto_del_clip(main_window):
    main_window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    main_window.clips[0].categoria_path = ["Cocina"]
    main_window.unit_selection.add("Casa A")
    main_window._asignar_unidad("Casa A")
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]


def test_asignar_unidad_a_clip_sin_cuarto_lo_deja_sin_cuarto(main_window):
    main_window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    main_window.clips[0].categoria_path = []
    main_window.unit_selection.add("Casa A")
    main_window._asignar_unidad("Casa A")
    assert main_window.clips[0].categoria_path == []


def test_asignar_unidad_reemplaza_la_unidad_anterior(main_window):
    main_window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    main_window.clips[0].categoria_path = ["Casa A", "Cocina"]
    main_window.unit_selection.add("Casa A")
    main_window.unit_selection.add("Casa B")
    main_window._asignar_unidad("Casa B")
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]


def test_elegir_unidad_con_lote_seleccionado_reasigna_y_activa(main_window):
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
    ])
    main_window.clips[0].categoria_path = ["Cocina"]
    main_window.clips[1].categoria_path = ["Baño"]
    main_window.selected_indices = [0, 1]
    main_window.unit_selection.add("Casa A")
    main_window._on_unidad_elegida_en_paleta("Casa A")
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]
    assert main_window.clips[1].categoria_path == ["Casa A", "Baño"]
    assert main_window._unidad_activa == "Casa A"


# --- mover/reordenar por unidad: mismo nombre repetido entre unidades -----
# --- (hallazgo de revision sobre "El rail agrupa por unidad") -------------


def _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window):
    """Casa A y Casa B, cada una con su propia `Cocina` -- el uso normal
    segun el spec: un cuarto existe una vez POR unidad."""
    main_window.unit_selection.add("Casa A")
    main_window.unit_selection.add("Casa B")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections["Casa A"].add("Cocina")
    main_window.room_selections["Casa B"] = RoomSelection()
    main_window.room_selections["Casa B"].add("Cocina")
    main_window.room_selections["Casa B"].add("Baño")
    return main_window


def test_mover_un_cuarto_de_una_unidad_NO_activa_no_toca_la_activa(main_window):
    """Casa A esta activa; mover el `Cocina` de Casa B no puede tocar el
    `Cocina` de Casa A -- son cuartos distintos con el mismo nombre."""
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")

    main_window.room_rail.room_moved_en_unidad.emit("Cocina", 1, "Casa B")

    assert main_window.room_selections["Casa A"].active_rooms() == ["Cocina"]
    assert main_window.room_selections["Casa B"].active_rooms() == ["Baño", "Cocina"]


def test_reordenar_un_cuarto_de_una_unidad_NO_activa_no_toca_la_activa(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")

    main_window.room_rail.room_reordered_en_unidad.emit("Cocina", 1, "Casa B")

    assert main_window.room_selections["Casa A"].active_rooms() == ["Cocina"]
    assert main_window.room_selections["Casa B"].active_rooms() == ["Baño", "Cocina"]


def test_mover_un_cuarto_de_la_unidad_activa_si_la_aplica(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa B")

    main_window.room_rail.room_moved_en_unidad.emit("Cocina", 1, "Casa B")

    assert main_window.room_selections["Casa B"].active_rooms() == ["Baño", "Cocina"]
    assert main_window.room_selection is main_window.room_selections["Casa B"]


def test_mover_una_unidad_inexistente_no_revienta(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")

    main_window.room_rail.room_moved_en_unidad.emit("Cocina", 1, "Casa Z")

    assert main_window.room_selections["Casa A"].active_rooms() == ["Cocina"]


# --- renombrar/borrar por unidad: mismo riesgo que mover/reordenar --------


def test_renombrar_un_cuarto_de_una_unidad_NO_activa_no_toca_la_activa(main_window):
    """Casa A esta activa; renombrar el `Cocina` de Casa B no puede tocar el
    `Cocina` de Casa A -- son cuartos distintos con el mismo nombre."""
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")

    main_window.room_rail.room_renamed_en_unidad.emit("Cocina", "Cocina grande", "Casa B")

    assert main_window.room_selections["Casa A"].active_rooms() == ["Cocina"]
    assert main_window.room_selections["Casa B"].active_rooms() == ["Cocina grande", "Baño"]


def test_renombrar_un_cuarto_de_otra_unidad_solo_mueve_los_clips_de_esa_unidad(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Casa B", "Cocina"], fps=30.0),
    ])

    main_window.room_rail.room_renamed_en_unidad.emit("Cocina", "Cocina grande", "Casa B")

    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]
    assert main_window.clips[1].categoria_path == ["Casa B", "Cocina grande"]


def test_renombrar_un_cuarto_de_la_unidad_activa_si_la_aplica(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa B")

    main_window.room_rail.room_renamed_en_unidad.emit("Cocina", "Cocina grande", "Casa B")

    assert main_window.room_selections["Casa B"].active_rooms() == ["Cocina grande", "Baño"]
    assert main_window.room_selection is main_window.room_selections["Casa B"]


def test_renombrar_en_una_unidad_inexistente_no_revienta(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")

    main_window.room_rail.room_renamed_en_unidad.emit("Cocina", "Cocina grande", "Casa Z")

    assert main_window.room_selections["Casa A"].active_rooms() == ["Cocina"]


def test_borrar_un_cuarto_de_una_unidad_NO_activa_no_toca_la_activa(main_window):
    """Casa A esta activa; borrar el `Cocina` de Casa B no puede tocar el
    `Cocina` de Casa A -- son cuartos distintos con el mismo nombre."""
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")

    main_window.room_rail.room_removed_en_unidad.emit("Cocina", "Casa B")

    assert main_window.room_selections["Casa A"].active_rooms() == ["Cocina"]
    assert main_window.room_selections["Casa B"].active_rooms() == ["Baño"]


def test_borrar_un_cuarto_de_otra_unidad_solo_suelta_los_clips_de_esa_unidad(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Casa B", "Cocina"], fps=30.0),
    ])

    main_window.room_rail.room_removed_en_unidad.emit("Cocina", "Casa B")

    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]
    assert main_window.clips[1].categoria_path == []


def test_borrar_un_cuarto_de_la_unidad_activa_si_la_aplica(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa B")

    main_window.room_rail.room_removed_en_unidad.emit("Cocina", "Casa B")

    assert main_window.room_selections["Casa B"].active_rooms() == ["Baño"]
    assert main_window.room_selection is main_window.room_selections["Casa B"]


def test_borrar_en_una_unidad_inexistente_no_revienta(main_window):
    _con_dos_unidades_y_mismo_nombre_de_cuarto(main_window)
    main_window._activar_unidad("Casa A")

    main_window.room_rail.room_removed_en_unidad.emit("Cocina", "Casa Z")

    assert main_window.room_selections["Casa A"].active_rooms() == ["Cocina"]


def test_crear_unidad_desde_el_boton_del_rail_no_la_activa(main_window):
    main_window._on_unit_created_en_rail("Casa C")
    assert "Casa C" in main_window.unit_selection.active_rooms()
    assert main_window._unidad_activa is None


# --- que unidades quedaron colapsadas en el rail: se guarda y se restaura -


def test_autosave_incluye_unidades_colapsadas(main_window):
    main_window.room_rail.set_rooms_agrupados(
        unidades=["Casa A", "Casa B"],
        rooms_por_unidad={"Casa A": [], "Casa B": []}, counts={},
    )
    main_window.room_rail._on_toggle_de_banda("Casa B")
    data = main_window._datos_del_proyecto()
    assert data["unidades_colapsadas"] == ["Casa B"]


def test_asignar_cuarto_con_unidad_activa_la_expande_si_estaba_colapsada(main_window):
    main_window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window.room_rail.set_rooms_agrupados(
        unidades=["Casa A"], rooms_por_unidad={"Casa A": []}, counts={},
    )
    main_window.room_rail._on_toggle_de_banda("Casa A")

    main_window._asignar_cuarto(["Cocina"])

    assert "Casa A" not in main_window.room_rail.unidades_colapsadas()


# --- mover un cuarto completo a otra unidad (spec 2026-09-21, tarea 9) -----


def _con_dos_unidades(main_window):
    main_window.unit_selection.add("Casa A")
    main_window.unit_selection.add("Casa B")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections["Casa A"].add("Cocina")
    main_window.room_selections["Casa B"] = RoomSelection()


def test_mover_cuarto_a_unidad_mueve_los_clips(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=3, ruta=Path("/c.MP4"), categoria_path=["Casa A", "Comedor"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina", fue_fusion=False,
    )
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]
    assert main_window.clips[1].categoria_path == ["Casa B", "Cocina"]
    assert main_window.clips[2].categoria_path == ["Casa A", "Comedor"]  # no se toca


def test_mover_cuarto_a_unidad_actualiza_los_catalogos(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina", fue_fusion=False,
    )
    assert "Cocina" not in main_window.room_selections["Casa A"].active_rooms()
    assert "Cocina" in main_window.room_selections["Casa B"].active_rooms()


def test_mover_cuarto_a_unidad_con_nombre_distinto_renombra_al_llegar(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina 2", fue_fusion=False,
    )
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina 2"]
    assert "Cocina 2" in main_window.room_selections["Casa B"].active_rooms()


def test_mover_cuarto_registra_en_el_historial(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina", fue_fusion=False,
    )
    entrada = main_window.history.entries()[0]
    assert entrada.cuarto_movido == CuartoMovido(
        nombre_origen="Cocina", posicion_origen=0, unidad_origen="Casa A",
        nombre_destino="Cocina", unidad_destino="Casa B", fue_fusion=False,
    )


def test_deshacer_mover_cuarto_regresa_clips_y_catalogos(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina", fue_fusion=False,
    )
    main_window.undo()
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]
    assert "Cocina" in main_window.room_selections["Casa A"].active_rooms()
    assert "Cocina" not in main_window.room_selections["Casa B"].active_rooms()


def test_mover_desde_sin_unidad_a_una_unidad(main_window):
    """El camino real de migracion de Bruno: Cocina-A vive hoy sin unidad,
    y se arrastra directo a Casa A."""
    main_window.unit_selection.add("Casa A")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections[""].add("Cocina-A")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Cocina-A"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina-A", "", "Casa A", nombre_destino="Cocina-A", fue_fusion=False,
    )
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina-A"]
    assert "Cocina-A" not in main_window.room_selections[""].active_rooms()


# --- choque de nombre al mover entre unidades (spec 2026-09-21, tarea 10) ---


def test_nombre_libre_en_prueba_sufijos_hasta_encontrar_uno(main_window):
    catalogo = RoomSelection()
    catalogo.add("Cocina")
    catalogo.add("Cocina 2")
    assert main_window._nombre_libre_en(catalogo, "Cocina") == "Cocina 3"


def test_nombre_libre_en_sin_choque_da_el_primer_sufijo(main_window):
    catalogo = RoomSelection()
    catalogo.add("Cocina")
    assert main_window._nombre_libre_en(catalogo, "Cocina") == "Cocina 2"


def test_on_rooms_movidos_sin_choque_mueve_directo(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    llamado = []
    monkeypatch.setattr(main_window, "_preguntar_por_el_choque",
                         lambda *a: llamado.append(a) or "cancelar")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert llamado == []   # no habia choque, no se pregunto nada
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]


def test_on_rooms_movidos_con_choque_pregunta_y_fusiona(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.room_selections["Casa B"].add("Cocina")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Casa B", "Cocina"], fps=30.0),
    ])
    monkeypatch.setattr(main_window, "_preguntar_por_el_choque", lambda *a: "fusionar")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]
    assert main_window.clips[1].categoria_path == ["Casa B", "Cocina"]  # no se toco
    assert main_window.room_selections["Casa B"].active_rooms().count("Cocina") == 1


def test_on_rooms_movidos_con_choque_renombra(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.room_selections["Casa B"].add("Cocina")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    monkeypatch.setattr(main_window, "_preguntar_por_el_choque", lambda *a: "renombrar")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina 2"]
    assert "Cocina" in main_window.room_selections["Casa B"].active_rooms()
    assert "Cocina 2" in main_window.room_selections["Casa B"].active_rooms()


def test_on_rooms_movidos_con_choque_cancelar_no_mueve_nada(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.room_selections["Casa B"].add("Cocina")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    monkeypatch.setattr(main_window, "_preguntar_por_el_choque", lambda *a: "cancelar")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]


def test_on_rooms_movidos_grupo_mixto_mueve_los_que_no_chocan_y_pregunta_por_el_resto(
    main_window, monkeypatch,
):
    _con_dos_unidades(main_window)
    main_window.room_selections["Casa A"].add("Comedor")
    main_window.room_selections["Casa B"].add("Cocina")   # choca
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Casa A", "Comedor"], fps=30.0),
    ])
    preguntas = []

    def espia(nombre, unidad_origen, unidad_destino):
        preguntas.append(nombre)
        return "renombrar"

    monkeypatch.setattr(main_window, "_preguntar_por_el_choque", espia)

    main_window._on_rooms_movidos_a_unidad(["Cocina", "Comedor"], "Casa A", "Casa B")

    assert preguntas == ["Cocina"]   # Comedor no chocaba, no se pregunto por el
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina 2"]
    assert main_window.clips[1].categoria_path == ["Casa B", "Comedor"]


def test_on_rooms_movidos_expande_la_unidad_destino(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window.room_rail.set_rooms_agrupados(
        unidades=["Casa A", "Casa B"],
        rooms_por_unidad={"Casa A": ["Cocina"], "Casa B": []}, counts={},
    )
    main_window.room_rail._on_toggle_de_banda("Casa B")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert "Casa B" not in main_window.room_rail.unidades_colapsadas()


# --- ultima conexion: la senal del rail hasta MainWindow (tarea 11) --------


def test_arrastrar_grupo_en_el_rail_llega_hasta_mover_cuarto(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window.room_rail.mover_grupo_a_unidad(["Cocina"], "Casa A", "Casa B")
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]
