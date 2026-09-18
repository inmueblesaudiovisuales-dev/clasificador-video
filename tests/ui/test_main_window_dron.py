"""Si el bin de importación dice "dron", de punta a punta: desde el nombre
del bin hasta el campo `bin_dron` del manifiesto."""
import json
from pathlib import Path

import pytest

from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow

# Mismo arreglo que test_main_window_camaras.py: sin FakeMpv cada ventana
# abre un mpv de verdad con sus hilos, y sin _probe_falso estos tests lanzan
# ffprobe contra rutas inventadas.
from test_main_window_bins import FakeMpv, _probe_falso


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


@pytest.fixture
def ventana(qtbot):
    window = MainWindow(project_name="Casa Jardin", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    window._probe_clip = _probe_falso
    qtbot.addWidget(window)
    return window


def test_un_bin_que_dice_dron_marca_sus_clips(ventana, tmp_path):
    ventana.load_clips([_clip(0, "/dron/C0001.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0],
                         rutas=[c.ruta for c in ventana.clips])
    ventana.clips[0].categoria_path = ["Aerea"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["bin_dron"] is True


def test_un_bin_que_no_dice_dron_no_marca(ventana, tmp_path):
    ventana.load_clips([_clip(0, "/cam/C0001.MP4")])
    ventana.bins.agregar("Cámara", Path("/cam"), [0],
                         rutas=[c.ruta for c in ventana.clips])
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["bin_dron"] is False


def test_un_clip_sin_bin_no_cuenta_como_dron(ventana, tmp_path):
    """Un clip suelto no tiene bin del que sacar el dato -- tiene que salir
    con el respaldo (False), igual que un clip suelto sale sony en camara."""
    ventana.load_clips([_clip(0, "/cam/C0001.MP4")])
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["bin_dron"] is False


def test_renombrar_el_bin_para_que_diga_dron_tambien_cuenta(ventana, tmp_path):
    """El nombre se revisa al exportar, no al crear el bin -- si Bruno lo
    renombra despues para que diga "dron", eso tiene que verse en el
    manifiesto siguiente."""
    ventana.load_clips([_clip(0, "/cam/C0001.MP4")])
    ventana.bins.agregar("Tarjeta 2", Path("/cam"), [0],
                         rutas=[c.ruta for c in ventana.clips])
    ventana.bins.renombrar("Tarjeta 2", "Dron 2")
    ventana.clips[0].categoria_path = ["Aerea"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["bin_dron"] is True
