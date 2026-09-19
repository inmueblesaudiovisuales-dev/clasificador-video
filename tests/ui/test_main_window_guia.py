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


def test_pedir_clasificacion_manda_los_cuartos(qtbot, ventana, monkeypatch):
    visto = {}
    def preguntar(llave, cuerpo, url=None):
        visto["cuerpo"] = cuerpo
        return '{"clasificacion": [{"cuarto": "Sala", "columna": "sociales"}]}'
    monkeypatch.setattr("clasificador_video.ui.main_window.ia.preguntar", preguntar)
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk")
    ventana.room_selection.add("Sala")
    with qtbot.waitSignal(ventana._señales_de_trabajos.guia_lista, timeout=3000):
        ventana.pedir_clasificacion()
    assert "Sala" in visto["cuerpo"]["messages"][0]["content"]
