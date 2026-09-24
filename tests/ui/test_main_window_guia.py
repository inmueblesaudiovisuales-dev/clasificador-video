import pytest

from clasificador_video import guia as logica
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    def __init__(self, **kwargs): self.pause = True; self.time_pos = 0.0
    def play(self, path): pass
    def command(self, *args): pass


@pytest.fixture
def ventana(qtbot):
    w = MainWindow("Casa", RoomSelection(), video_factory=FakeMpv)
    qtbot.addWidget(w)
    return w


def test_restaurar_guia_nueva(ventana):
    ventana.restaurar_guia({"orden": ["Sala", "Cocina"],
                            "cuartos_de_entonces": ["Sala", "Cocina"]})
    assert [r.cuarto for r in ventana.guia_actual.lista] == ["Sala", "Cocina"]


def test_restaurar_guia_vieja_se_trata_como_invalida(ventana):
    ventana.restaurar_guia({"recorrido": "x", "orden": [{"cuarto": "Sala"}]})
    assert ventana.guia_actual is None


def test_guia_para_manifest_es_lista_de_nombres(ventana):
    ventana.guia_actual = logica.Respuesta(
        ok=True, lista=[logica.Renglon("Fachada"), logica.Renglon("Sala")])
    assert ventana._guia_para_el_manifest().orden == ["Fachada", "Sala"]


def test_aceptar_orden_conserva_repetidos_en_la_guia(ventana):
    for cuarto in ("Aérea", "Sala"):
        ventana.room_selection.add(cuarto)
    ventana.guia_actual = logica.Respuesta(
        ok=True, lista=[logica.Renglon("Aérea"), logica.Renglon("Sala"),
                       logica.Renglon("Aérea")])
    ventana.aceptar_orden_de_la_guia(["Aérea", "Sala", "Aérea"])
    assert ventana._guia_para_el_manifest().orden == ["Aérea", "Sala", "Aérea"]


def test_pedir_clasificacion_pre_ordena_por_palabras_sin_llave(ventana):
    """Sin llave configurada, «Pre-ordenar» llena el tablero al instante
    reconociendo los nombres de los cuartos (handoff 2026-09-24)."""
    for cuarto in ("Cocina", "Recámara 1", "Pasillo"):
        ventana.room_selection.add(cuarto)
    ventana._abrir_pantalla_de_guia()

    ventana.pedir_clasificacion()

    pantalla = ventana._pantalla_guia
    assert pantalla.columnas["sociales"].cuartos() == ["Cocina"]
    assert pantalla.columnas["habitaciones"].cuartos() == ["Recámara 1"]
    # «Pasillo» no trae término: se queda en la franja, no se adivina.
    assert all("Pasillo" not in c.cuartos() for c in pantalla.columnas.values())


def test_abrir_la_guia_le_pasa_los_cuartos_reales(ventana):
    ventana.room_selection.add("Sala"); ventana.room_selection.add("Cocina")
    ventana._abrir_pantalla_de_guia()
    assert ventana._pantalla_guia.franja.cuartos() == ["Sala", "Cocina"]


def test_mostrar_guia_guarda_la_clasificacion_aunque_no_se_acepte(ventana):
    """Si a Bruno le gusta el tablero y no aprieta "Usar este orden" (o
    cierra Clipify), la clasificación que acaba de costar una llamada a
    la API no se debe perder."""
    ventana.room_selection.add("Sala")
    ventana._abrir_pantalla_de_guia()
    ventana._mostrar_guia(logica.Clasificacion(ok=True, columna_de={"Sala": "sociales"}))
    assert ventana.guia_actual is not None
    assert [r.cuarto for r in ventana.guia_actual.lista] == ["Sala"]
    assert ventana._cuartos_de_la_guia == ["Sala"]


def test_mostrar_guia_fallida_no_guarda_nada(ventana):
    ventana.room_selection.add("Sala")
    ventana._abrir_pantalla_de_guia()
    ventana._mostrar_guia(logica.Clasificacion(ok=False, error="sin red"))
    assert ventana.guia_actual is None


def test_abrir_la_guia_no_borra_una_guia_ya_aceptada(ventana):
    ventana.room_selection.add("Sala")
    ventana.guia_actual = logica.Respuesta(ok=True, lista=[logica.Renglon("Sala")])
    ventana._abrir_pantalla_de_guia()
    assert ventana._pantalla_guia.orden_final() == ["Sala"]
