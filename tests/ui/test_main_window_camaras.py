"""La cámara, de punta a punta: se adivina al importar y llega al manifiesto."""
import json
from pathlib import Path

import pytest

from clasificador_video.camaras import DJI, OTRA, SONY
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow

# El arreglo de ventana se comparte con test_main_window_bins.py en vez de
# copiarlo: sin `FakeMpv` cada ventana abre un mpv de verdad con sus hilos, y
# sin `_probe_falso` estos tests lanzan ffprobe contra rutas inventadas.
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


def test_un_bin_importado_del_dron_queda_marcado_como_dron(ventana):
    ventana.load_clips([_clip(0, "/dron/DJI_0001.MP4"),
                        _clip(1, "/dron/DJI_0002.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0, 1],
                         rutas=[c.ruta for c in ventana.clips])

    assert ventana.bins.camara_de("Dron") == DJI


def test_un_bin_de_la_sony_queda_como_sony(ventana):
    ventana.load_clips([_clip(0, "/cam/20260817_PIB0016.MP4")])
    ventana.bins.agregar("Cámara", Path("/cam"), [0],
                         rutas=[c.ruta for c in ventana.clips])

    assert ventana.bins.camara_de("Cámara") == SONY


def test_la_camara_del_bin_llega_al_manifiesto(ventana, tmp_path):
    ventana.load_clips([_clip(0, "/dron/DJI_0001.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0],
                         rutas=[c.ruta for c in ventana.clips])
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["camara"] == "dji"


def test_un_clip_sin_bin_sale_sony(ventana, tmp_path):
    """Un clip suelto no tiene de dónde sacar la cámara del bin, y tiene que
    llegar con una: sale con el respaldo, no sin campo."""
    ventana.load_clips([_clip(0, "/cam/C0001.MP4")])
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["camara"] == "sony"


def test_la_correccion_a_mano_es_la_que_viaja(ventana, tmp_path):
    """Lo que Bruno eligió le gana a lo que la app adivinó. Si no, corregir
    no serviría de nada donde único importa."""
    ventana.load_clips([_clip(0, "/dron/DJI_0001.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0],
                         rutas=[c.ruta for c in ventana.clips])
    ventana.bins.fijar_camara("Dron", OTRA)
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["camara"] == "otra"
