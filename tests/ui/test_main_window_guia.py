"""La guía de edición, de punta a punta: se pide, se acepta y viaja al manifest."""
import json
from pathlib import Path

import pytest

from clasificador_video import guia as logica
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow

# Mismo arreglo de ventana que el resto: sin `FakeMpv` cada ventana abre un
# mpv de verdad con sus hilos.
from test_main_window_bins import FakeMpv, _probe_falso


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


@pytest.fixture
def ventana(qtbot):
    window = MainWindow(project_name="Casa Jardin", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    window._probe_clip = _probe_falso
    qtbot.addWidget(window)
    window.load_clips([_clip(0, "/cam/C0001.MP4")])
    return window


def test_pedir_la_guia_manda_los_cuartos_de_la_sesion(ventana, monkeypatch):
    visto = {}

    def falso_preguntar(llave, cuerpo, url=None):
        visto["cuerpo"] = cuerpo
        return '{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}'

    monkeypatch.setattr("clasificador_video.ui.main_window.ia.preguntar", falso_preguntar)
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")

    ventana.room_selection.add("Sala")
    ventana.pedir_guia({"lucir": "la alberca", "propiedad": "Casa"})

    sistema = visto["cuerpo"]["messages"][0]["content"]
    assert "- Sala" in sistema


def test_aceptar_el_orden_reacomoda_los_cuartos(ventana):
    for c in ["Sala", "Cocina"]:
        ventana.room_selection.add(c)
    ventana.aceptar_orden_de_la_guia(["Cocina", "Sala"])
    assert ventana.room_selection.active_rooms() == ["Cocina", "Sala"]


def test_la_guia_aceptada_viaja_al_manifest(ventana, tmp_path):
    ventana.room_selection.add("Sala")
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="Abres por fuera.",
        lista=[logica.Renglon(cuarto="Sala", porque="se entra aquí")],
    )
    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    d = json.loads(destino.read_text())
    assert d["guia"]["recorrido"] == "Abres por fuera."
    assert d["guia"]["orden"][0]["cuarto"] == "Sala"


def test_sin_guia_el_manifest_sale_igual_que_siempre(ventana, tmp_path):
    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["guia"] is None


def test_un_fallo_de_red_no_impide_exportar(ventana, tmp_path, monkeypatch):
    from clasificador_video.ia import ErrorDeIA

    def cae(llave, cuerpo, url=None):
        raise ErrorDeIA("No se pudo armar la guía: no hay internet.")

    monkeypatch.setattr("clasificador_video.ui.main_window.ia.preguntar", cae)
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")

    ventana.room_selection.add("Sala")
    ventana.pedir_guia({"lucir": "", "propiedad": "Casa"})  # no revienta

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)
    assert destino.exists()


def _con_guia(ventana, cuartos):
    """La ventana con una guia ya aceptada sobre esos cuartos."""
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon(cuarto=c) for c in cuartos],
    )
    ventana.aceptar_orden_de_la_guia(list(cuartos))


def test_la_guia_queda_vieja_al_agregar_un_cuarto(ventana):
    ventana.room_selection.add("Sala")
    _con_guia(ventana, ["Sala"])
    assert not ventana.guia_quedo_vieja()

    ventana.room_selection.add("Terraza")
    assert ventana.guia_quedo_vieja()


def test_el_aviso_dice_cual_cuarto_se_agrego(ventana):
    ventana.room_selection.add("Sala")
    _con_guia(ventana, ["Sala"])
    ventana.room_selection.add("Terraza")
    assert "Terraza" in ventana.aviso_de_guia_vieja()


def test_sin_guia_no_hay_nada_que_avisar(ventana):
    ventana.room_selection.add("Sala")
    assert not ventana.guia_quedo_vieja()
    assert ventana.aviso_de_guia_vieja() == ""


def test_reordenar_a_mano_no_deja_vieja_la_guia(ventana):
    # Mover un cuarto de lugar no cambia QUE cuartos hay. Avisar ahi seria
    # una alarma que suena por nada, y las alarmas que suenan por nada se
    # aprenden a ignorar.
    for c in ["Sala", "Cocina"]:
        ventana.room_selection.add(c)
    _con_guia(ventana, ["Sala", "Cocina"])
    ventana.room_selection.move("Cocina", -1)
    assert not ventana.guia_quedo_vieja()


def test_la_guia_se_guarda_en_el_documento_del_proyecto(ventana):
    # El §9 del spec: cerrar Clipify y volver no la pierde.
    ventana.room_selection.add("Sala")
    _con_guia(ventana, ["Sala"])

    guardado = ventana._datos_del_proyecto()["guia"]
    assert guardado["recorrido"] == "x"
    assert guardado["orden"][0]["cuarto"] == "Sala"
    # Y los cuartos que habia entonces, que es lo unico con que se sabe que
    # la guia quedo vieja.
    assert guardado["cuartos_de_entonces"] == ["Sala"]


def test_sin_guia_el_documento_la_trae_en_nulo(ventana):
    assert ventana._datos_del_proyecto()["guia"] is None


def test_la_guia_vuelve_al_abrir_el_proyecto(ventana):
    ventana.restaurar_guia({
        "recorrido": "Abres por fuera.",
        "orden": [{"cuarto": "Sala", "porque": "se entra aquí",
                   "fuera_del_patron": False}],
        "cuartos_de_entonces": ["Sala"],
    })
    ventana.room_selection.add("Sala")

    assert ventana.guia_actual.recorrido == "Abres por fuera."
    assert not ventana.guia_quedo_vieja()
    # Y sigue avisando si despues se agrega un cuarto, que es para lo que
    # `cuartos_de_entonces` viaja.
    ventana.room_selection.add("Terraza")
    assert "Terraza" in ventana.aviso_de_guia_vieja()


def test_un_proyecto_viejo_sin_guia_abre_igual(ventana):
    ventana.restaurar_guia(None)
    assert ventana.guia_actual is None
    assert not ventana.guia_quedo_vieja()
