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


def _pedir_y_esperar(qtbot, ventana, respuestas):
    """Pide la guía y espera a que conteste el hilo.

    La llamada corre FUERA del hilo de la interfaz desde el 2026-09-15, así
    que la respuesta ya no llega dentro de `pedir_guia`: llega por señal.
    """
    with qtbot.waitSignal(ventana._señales_de_trabajos.guia_lista, timeout=3000):
        ventana.pedir_guia(respuestas)


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


def test_pedir_la_guia_manda_los_cuartos_de_la_sesion(qtbot, ventana, monkeypatch):
    visto = {}

    def falso_preguntar(llave, cuerpo, url=None):
        visto["cuerpo"] = cuerpo
        return '{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}'

    monkeypatch.setattr("clasificador_video.ui.main_window.ia.preguntar", falso_preguntar)
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")

    ventana.room_selection.add("Sala")
    _pedir_y_esperar(qtbot, ventana, {"lucir": "la alberca", "propiedad": "Casa"})

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


def test_un_fallo_de_red_no_impide_exportar(qtbot, ventana, tmp_path, monkeypatch):
    from clasificador_video.ia import ErrorDeIA

    def cae(llave, cuerpo, url=None):
        raise ErrorDeIA("No se pudo armar la guía: no hay internet.")

    monkeypatch.setattr("clasificador_video.ui.main_window.ia.preguntar", cae)
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")

    ventana.room_selection.add("Sala")
    _pedir_y_esperar(qtbot, ventana, {"lucir": "", "propiedad": "Casa"})  # no revienta

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


def test_abrir_la_pantalla_ensena_la_guia_que_traia_el_proyecto(ventana):
    # `restaurar_guia` deja la guia en `guia_actual` (§9 del spec), pero la
    # pantalla nacia en blanco de todos modos: `_abrir_pantalla_de_guia`
    # nunca la empujaba a la pantalla, asi que Bruno la veia vacia y volvia
    # a apretar "Armar la guia" -- pagando una llamada por algo que ya tenia.
    ventana.restaurar_guia({
        "recorrido": "Abres por fuera.",
        "orden": [{"cuarto": "Sala", "porque": "se entra aquí",
                   "fuera_del_patron": False}],
        "cuartos_de_entonces": ["Sala"],
    })
    ventana.room_selection.add("Sala")

    ventana._abrir_pantalla_de_guia()

    assert "Sala" in ventana._pantalla_guia.texto_del_resultado()
    assert ventana._pantalla_guia.usar_button.isEnabled()


def test_abrir_la_pantalla_sin_guia_restaurada_sigue_en_blanco(ventana):
    ventana.room_selection.add("Sala")

    ventana._abrir_pantalla_de_guia()

    assert ventana._pantalla_guia.texto_del_resultado() == ""
    assert not ventana._pantalla_guia.usar_button.isEnabled()


def test_guardar_la_llave_desde_configuracion(ventana, tmp_path, monkeypatch):
    destino = tmp_path / "llave.json"
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.RUTA", destino)

    ventana.guardar_llave("sk-1234abcd")
    from clasificador_video import llave as mod

    assert mod.leer(destino) == "sk-1234abcd"


def test_quitar_la_llave_desde_configuracion(ventana, tmp_path, monkeypatch):
    destino = tmp_path / "llave.json"
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.RUTA", destino)

    ventana.guardar_llave("sk-1234abcd")
    ventana.borrar_llave()
    from clasificador_video import llave as mod

    assert mod.leer(destino) == ""


def test_sin_llave_la_guia_manda_a_configuracion(qtbot, ventana, monkeypatch):
    # El mensaje tiene que decir QUE HACER, no solo que falta algo.
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "")
    ventana.room_selection.add("Sala")
    ventana._abrir_pantalla_de_guia()
    _pedir_y_esperar(qtbot, ventana, {"lucir": "", "propiedad": "Casa"})

    aviso = ventana._pantalla_guia.avisos_label.text()
    assert "onfiguración" in aviso


# --- El rail y la guía tienen que decir lo MISMO ----------------------
# Bug del 2026-09-15: si la lista se saltaba un cuarto y Bruno la aceptaba,
# el rail se quedaba con los tres y al manifest viajaban dos. Dos partes del
# programa diciendo cosas distintas del mismo dato.

def test_el_cuarto_que_la_guia_se_salto_igual_viaja(ventana):
    for c in ["Fachada", "Cocina", "Terraza"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Fachada", "se entra aquí"), logica.Renglon("Cocina")],
    )
    ventana.aceptar_orden_de_la_guia(["Fachada", "Cocina"])

    viaja = [r.cuarto for r in ventana._guia_para_el_manifest().orden]
    assert viaja == ventana.room_selection.active_rooms()
    assert viaja == ["Fachada", "Cocina", "Terraza"]


def test_el_cuarto_agregado_no_pierde_su_razon(ventana):
    # El que SÍ traía razón la conserva; el que se agregó al final no
    # estrena una inventada.
    for c in ["Fachada", "Terraza"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x", lista=[logica.Renglon("Fachada", "se entra aquí")],
    )
    ventana.aceptar_orden_de_la_guia(["Fachada"])

    renglones = ventana._guia_para_el_manifest().orden
    assert renglones[0].porque == "se entra aquí"
    assert renglones[1].cuarto == "Terraza"
    assert renglones[1].porque == ""


def test_un_cuarto_inventado_no_viaja_al_manifest(ventana):
    # No está en el rail, así que no puede estar en la guía que se exporta:
    # en Premiere sería una carpeta de un cuarto que no existe.
    ventana.room_selection.add("Fachada")
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Fachada"), logica.Renglon("Bodega", "me la inventé")],
    )
    ventana.aceptar_orden_de_la_guia(["Fachada", "Bodega"])

    viaja = [r.cuarto for r in ventana._guia_para_el_manifest().orden]
    assert viaja == ["Fachada"]


def test_el_rail_pone_el_cuarto_repetido_donde_sale_la_PRIMERA_vez(ventana):
    for c in ["Sala", "Aérea", "Cocina"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Aérea"), logica.Renglon("Cocina"),
               logica.Renglon("Sala"), logica.Renglon("Aérea")],
    )
    ventana.aceptar_orden_de_la_guia(
        ["Aérea", "Cocina", "Sala", "Aérea"]
    )
    # Una sola vez, y en el lugar de la primera: es el mismo criterio con el
    # que el plugin numera su carpeta.
    assert ventana.room_selection.active_rooms() == ["Aérea", "Cocina", "Sala"]


def test_el_guion_que_viaja_CONSERVA_las_repeticiones(ventana):
    for c in ["Sala", "Aérea"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Aérea", "abres"), logica.Renglon("Sala"),
               logica.Renglon("Aérea", "cierras, más larga")],
    )
    ventana.aceptar_orden_de_la_guia(["Aérea", "Sala", "Aérea"])

    pasos = ventana._guia_para_el_manifest().orden
    assert [r.cuarto for r in pasos] == ["Aérea", "Sala", "Aérea"]
    # Y cada paso conserva SU razón: la de abrir no es la de cerrar.
    assert pasos[0].porque == "abres"
    assert pasos[2].porque == "cierras, más larga"


def test_un_cuarto_que_el_guion_no_menciona_sigue_entrando_al_final(ventana):
    for c in ["Aérea", "Terraza"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Aérea"), logica.Renglon("Aérea")],
    )
    ventana.aceptar_orden_de_la_guia(["Aérea", "Aérea"])

    pasos = [r.cuarto for r in ventana._guia_para_el_manifest().orden]
    assert pasos == ["Aérea", "Aérea", "Terraza"]


def test_repetido_inventado_y_faltante_todo_junto(ventana):
    # Lo que llega de verdad: la pantalla emite la lista tal cual la devolvió
    # el modelo, sin filtrar nada. Las tres reglas tienen que convivir en una
    # sola llamada, que es donde se romperían sin que nadie lo note.
    for c in ["Aérea", "Sala", "Terraza"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Aérea", "abres"),
               logica.Renglon("Bodega", "me la inventé"),
               logica.Renglon("Sala"),
               logica.Renglon("Aérea", "cierras")],
    )
    ventana.aceptar_orden_de_la_guia(
        ["Aérea", "Bodega", "Sala", "Aérea"]
    )

    # El rail: sin el inventado, sin repetir, y la Terraza --que el guion se
    # saltó-- no se pierde.
    assert ventana.room_selection.active_rooms() == ["Aérea", "Sala", "Terraza"]
    # El guion que viaja: conserva las dos aéreas con SU razón cada una, tira
    # el inventado y mete la Terraza al final sin razón inventada.
    pasos = ventana._guia_para_el_manifest().orden
    assert [r.cuarto for r in pasos] == ["Aérea", "Sala", "Aérea", "Terraza"]
    assert pasos[0].porque == "abres"
    assert pasos[2].porque == "cierras"
    assert pasos[3].porque == ""


# --- El aviso de la guía vieja tiene que saltar SIEMPRE ---------------
# Bug del 2026-09-15: solo funcionaba si le dabas a «Usar este orden». Si te
# gustaba el orden como estaba y no le picabas, el aviso no salía nunca.

def test_avisa_aunque_no_se_haya_apretado_usar_este_orden(qtbot, ventana, monkeypatch):
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.ia.preguntar",
        lambda llave, cuerpo, url=None: '{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}',
    )
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")

    ventana.room_selection.add("Sala")
    _pedir_y_esperar(qtbot, ventana, {"lucir": "", "propiedad": "Casa"})  # NO se acepta
    assert not ventana.guia_quedo_vieja()

    ventana.room_selection.add("Terraza")
    assert ventana.guia_quedo_vieja()
    assert "Terraza" in ventana.aviso_de_guia_vieja()


def test_la_guia_se_guarda_sin_esperar_a_que_la_aceptes(qtbot, ventana, monkeypatch):
    # Armarla y cerrar Clipify no la puede perder: pedirla cuesta una
    # llamada, y volver y no encontrarla es pagarla dos veces.
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.ia.preguntar",
        lambda llave, cuerpo, url=None: '{"recorrido": "Abres por fuera.", "orden": [{"cuarto": "Sala"}]}',
    )
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")

    ventana.room_selection.add("Sala")
    _pedir_y_esperar(qtbot, ventana, {"lucir": "", "propiedad": "Casa"})

    guardado = ventana._datos_del_proyecto()["guia"]
    assert guardado["recorrido"] == "Abres por fuera."
    assert guardado["cuartos_de_entonces"] == ["Sala"]


# --- La llamada NO puede congelar la ventana -------------------------
# Bug del 2026-09-15: `ia.preguntar` corría en el hilo de la interfaz, con
# 60 segundos de espera. Desde que le dabas a «Armar la guía» hasta que
# contestaba, Clipify se quedaba tieso; y sin internet, hasta un minuto.

def test_pedir_la_guia_devuelve_de_inmediato(qtbot, ventana, monkeypatch):
    import threading
    import time

    hilos = {}
    suelta = threading.Event()

    def lenta(llave, cuerpo, url=None):
        hilos["trabajo"] = threading.current_thread().name
        suelta.wait(3)
        return '{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}'

    monkeypatch.setattr("clasificador_video.ui.main_window.ia.preguntar", lenta)
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")
    ventana.room_selection.add("Sala")

    arranque = time.monotonic()
    ventana.pedir_guia({"lucir": "", "propiedad": "Casa"})
    # La ventana sigue suya: `pedir_guia` no espera a nadie.
    assert time.monotonic() - arranque < 0.5

    suelta.set()
    qtbot.waitSignal(ventana._señales_de_trabajos.guia_lista, timeout=3000).wait()
    assert hilos["trabajo"] != threading.current_thread().name


def test_mientras_arma_la_pantalla_lo_dice(qtbot, ventana, monkeypatch):
    # Una espera sin aviso se lee como una app trabada.
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.ia.preguntar",
        lambda llave, cuerpo, url=None: '{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}',
    )
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")
    ventana.room_selection.add("Sala")
    ventana._abrir_pantalla_de_guia()

    with qtbot.waitSignal(ventana._señales_de_trabajos.guia_lista, timeout=3000):
        ventana.pedir_guia({"lucir": "", "propiedad": "Casa"})
        assert not ventana._pantalla_guia.armar_button.isEnabled()
        assert "rmando" in ventana._pantalla_guia.avisos_label.text()

    assert ventana._pantalla_guia.armar_button.isEnabled()
