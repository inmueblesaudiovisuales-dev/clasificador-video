# tests/ui/test_main_window_proyecto.py
"""El autoguardado escribe **el documento del proyecto**, no una forma propia.

Antes `_write_autosave_now` armaba su dict a mano y `proyecto.a_dict` armaba
otro: dos formas del mismo documento, condenadas a desincronizarse. Aquí se
prueba que hay una sola, y sobre todo que **los pesos guardados sobreviven**
a guardar sin la media conectada — que es como se pierde, en silencio, lo
único que distingue una tarjeta de otra.
"""
import json
from pathlib import Path

import pytest

from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    """Mismo doble que el resto de tests de la ventana: sin él cada ventana
    abre un mpv de verdad, con sus hilos, para nada."""

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        pass


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


@pytest.fixture(autouse=True)
def confirmar_por_defecto(monkeypatch):
    """«Quitar del proyecto» pregunta antes, y un cartel modal cuelga la
    suite bajo `offscreen`."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)


@pytest.fixture
def ventana(qtbot):
    window = MainWindow(project_name="Casa Jardín", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    qtbot.addWidget(window)
    return window


def _guardado(ventana) -> dict:
    ventana._write_autosave_now()
    ventana._autosave_pool.waitForDone(2000)
    return json.loads(ventana.session_path.read_text())


def test_el_autoguardado_escribe_la_forma_del_proyecto(ventana, tmp_path):
    """Una sola forma del documento: la que arma `proyecto.a_dict`."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 700)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, str(archivo))])
    ventana.bins.agregar("Sony", tmp_path, [0])

    data = _guardado(ventana)

    assert data["version"] == 1
    assert data["relativas"] == {"0": "C0001.MP4"}
    assert data["bytes"] == {"0": 700}


def test_el_autoguardado_no_borra_los_pesos_cuando_la_media_no_esta(ventana, tmp_path):
    """El bug que vuelve en silencio.

    Con la media desconectada no hay nada que medir. Si el autoguardado
    escribe los pesos «como están» —o sea, sin ninguno— el archivo pierde
    lo único con que se puede confirmar que un archivo reencontrado es el
    que era, y Bruno se entera cuando ya no hay nada que hacer.
    """
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/disco/que/no/esta/C0001.MP4")])
    ventana._bytes_guardados = {0: 700}

    assert _guardado(ventana)["bytes"] == {"0": 700}


def test_los_pesos_recien_medidos_quedan_como_conocidos(ventana, tmp_path):
    """Guardar con la media puesta tiene que dejar el dato listo para el
    guardado de después, que puede ser ya sin ella."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, str(archivo))])

    _guardado(ventana)

    assert ventana._bytes_guardados == {0: 500}


def test_material_nuevo_no_hereda_los_pesos_del_anterior(ventana, tmp_path):
    """`_bytes_guardados` va por ÍNDICE de clip, igual que los bins y los
    proxies: dejarlo vivo al cargar otro material lo deja describiendo al
    clip equivocado."""
    ventana.session_path = tmp_path / "P.cvproj"
    ventana._bytes_guardados = {0: 700}
    ventana._relativas = {0: "viejo.MP4"}

    ventana.load_clips([_clip(0, "/otro/C0009.MP4")])

    assert ventana._bytes_guardados == {}
    assert ventana._relativas == {}


def test_quitar_un_bin_corre_los_pesos_y_las_relativas(ventana, tmp_path):
    """Todo lo indexado por clip se corre junto o queda describiendo a otro."""
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana._bytes_guardados = {0: 100, 1: 200}
    ventana._relativas = {0: "A.MP4", 1: "B.MP4"}

    ventana._on_bin_quitado("Sony")

    assert ventana._bytes_guardados == {0: 200}
    assert ventana._relativas == {0: "B.MP4"}


def test_la_ventana_avisa_cuando_se_cierra(ventana, qtbot):
    """La pantalla de inicio vuelve al cerrarse la ventana, y para eso
    necesita enterarse."""
    from PySide6.QtGui import QCloseEvent

    avisos = []
    ventana.cerrada.connect(lambda: avisos.append(1))

    ventana.closeEvent(QCloseEvent())

    assert avisos == [1]
