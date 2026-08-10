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


def test_el_peso_se_mide_al_guardar_y_se_arrastra_solo(ventana, tmp_path):
    """Guardar con la media puesta deja el dato listo para el guardado de
    después, que puede ser ya sin ella.

    Lo acumula el ARCHIVO y no la ventana: el peso lo mide el hilo del
    guardado —en el de la interfaz un `stat` por clip congela la app sobre un
    volumen montado e incomunicado— así que la ventana nunca se entera. Por
    eso el guardado relee lo que ya había antes de escribir.
    """
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, str(archivo))])
    assert _guardado(ventana)["bytes"] == {"0": 500}

    archivo.unlink()                       # se desconectó la tarjeta

    assert _guardado(ventana)["bytes"] == {"0": 500}


def test_el_peso_medido_tambien_vuelve_a_la_ventana(ventana, tmp_path, qtbot):
    """El archivo no puede ser el único que se entere.

    En la sesión donde Bruno IMPORTA, `_bytes_guardados` estaba vacío: solo
    se llena al abrir un `.cvproj`. Así que si en esa misma sesión mueve la
    carpeta y da «Buscar…», `calza` recibe `tamano_esperado=None` y confirma
    solo por duración — y dos tomas del mismo largo de dos tarjetas de la
    Sony pasan ese filtro. La defensa principal apagada, en el único caso
    que todo esto existe para evitar.
    """
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, str(archivo))])

    _guardado(ventana)
    qtbot.waitUntil(lambda: ventana._bytes_guardados == {0: 500}, timeout=2000)


def test_los_pesos_de_un_guardado_viejo_no_caen_sobre_otros_clips(ventana, tmp_path):
    """Los pesos van por ÍNDICE. Si entre que arrancó el guardado y que
    llegó su resultado se quitó un bin, los índices ya se corrieron y ese
    peso describiría al clip equivocado — que es justo con lo que después se
    confirma que un archivo reencontrado es el que era."""
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/B.MP4")])
    generacion_vieja = ventana._indices_generation

    ventana.load_clips([_clip(0, "/otro/C.MP4")])
    ventana._on_pesos_medidos(generacion_vieja, {0: 999, 1: 111})

    assert ventana._bytes_guardados == {}


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


def test_armar_el_documento_no_toca_el_disco_en_el_hilo_de_la_interfaz(ventana, tmp_path, monkeypatch):
    """El `stat` de cada clip vive en el hilo del guardado.

    En el de la interfaz se traba hasta el timeout con un volumen montado
    pero incomunicado, y son uno por clip en serie: la app se congela. Sacar
    la escritura de ese hilo fue justo lo que arregló el lag al clasificar
    rápido, y medir ahí es volver a meterlo.
    """
    from pathlib import Path as _Path

    tocados = []
    stat_real = _Path.stat
    monkeypatch.setattr(_Path, "stat",
                        lambda self, *a, **k: (tocados.append(self),
                                               stat_real(self, *a, **k))[1])
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.clips = [_clip(0, "/cam/A.MP4")]

    ventana._write_autosave_now()          # sin esperar al hilo: solo lo de aquí

    assert [t for t in tocados if str(t).startswith("/cam")] == []


def test_si_el_guardado_falla_la_barra_lo_dice(ventana, qtbot, tmp_path):
    """El `except OSError: pass` se tragaba el error y el indicador seguía
    contando «guardado hace 3 s» toda la sesión. Con el proyecto en un disco
    externo que se desconecta a media tarde, eso es prometer lo que no pasó."""
    estorbo = tmp_path / "estorbo"
    estorbo.write_text("no soy una carpeta")
    ventana.session_path = estorbo / "P.cvproj"
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    with qtbot.waitSignal(ventana._señales_de_trabajos.guardado_fallo, timeout=2000):
        ventana._write_autosave_now()

    assert ventana.title_bar.saved_label.text() == "No se pudo guardar"
    assert ventana._last_saved_at is None


def test_el_indicador_solo_cuenta_cuando_de_verdad_se_escribio(ventana, qtbot, tmp_path):
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana._write_autosave_now()
    assert ventana._last_saved_at is None          # todavía nadie escribió nada

    ventana._autosave_pool.waitForDone(2000)
    qtbot.waitUntil(lambda: ventana._last_saved_at is not None, timeout=2000)

    assert "Guardado hace" in ventana.title_bar.saved_label.text()


def test_cerrar_la_ventana_apaga_mpv(ventana, qtbot):
    """Con la pantalla de inicio la ventana se destruye en caliente, y cada
    proyecto que Bruno cierra dejaría atrás un mpv vivo —hilos reales, no
    objetos— si nadie lo apaga."""
    from PySide6.QtGui import QCloseEvent

    ventana.video_widget.player            # lo enciende

    ventana.closeEvent(QCloseEvent())

    assert ventana.video_widget.esta_apagado


def test_el_playhead_se_detiene_antes_de_apagar(ventana, qtbot):
    """El temporizador del playhead corre cada 150 ms y le pregunta la
    posición al reproductor. Uno que llegue después de apagar resucitaría
    mpv sobre una ventana que se está cerrando."""
    from PySide6.QtGui import QCloseEvent

    ventana.closeEvent(QCloseEvent())

    assert not ventana._playhead_timer.isActive()
    assert not ventana._saved_timer.isActive()
