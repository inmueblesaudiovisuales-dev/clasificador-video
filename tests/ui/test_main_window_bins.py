# tests/ui/test_main_window_bins.py
import json
from pathlib import Path

import pytest

from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


def _probe_falso(path):
    """Sondeo que no toca disco ni lanza ffprobe de verdad.

    Las tareas 5, 6 y 7 del plan escriben tests con rutas inventadas
    (`/cam/A.MP4`) que llaman a medir y sondear proxies. Sin este doble,
    esos tests lanzarian ffprobe de verdad contra archivos que no existen.
    """
    return {
        "fps": 30.0,
        "duration_frames": 300,
        "width": 1080,
        "height": 1920,
        "rotation": 0,
    }


@pytest.fixture
def ventana(qtbot):
    """Misma forma que `_window` en test_main_window.py -- no hay una
    fixture equivalente ya declarada en tests/ui/, asi que se copia el
    patron en vez de duplicar la logica en cada archivo nuevo."""
    window = MainWindow(project_name="Casa Jardin", room_selection=RoomSelection())
    window._probe_clip = _probe_falso
    qtbot.addWidget(window)
    return window


def test_el_autosave_escribe_los_bins(qtbot, tmp_path, ventana):
    ventana.session_path = tmp_path / "sesion.json"
    ventana.load_clips([_clip(0, "/dron/A.MP4"), _clip(1, "/dron/B.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0, 1])

    ventana._write_autosave_now()
    # si el trabajo de escritura no termino en el plazo, la aserción de
    # abajo fallaria con FileNotFoundError -- que no dice nada del timeout
    # real. Afirmar esto primero deja el error correcto si algun dia pasa.
    assert ventana._autosave_pool.waitForDone(2000)

    data = json.loads((tmp_path / "sesion.json").read_text())
    assert data["bins"] == [
        {"nombre": "Dron", "origen": "/dron", "clips": [0, 1]}
    ]


def test_cargar_clips_de_nuevo_reinicia_los_bins(qtbot, ventana):
    """`load_clips` ya limpia el historial y los proxies porque van por
    INDICE de clip y una lista nueva vuelve invalidos esos indices. Los
    bins son exactamente el mismo caso y se habian quedado afuera: sin
    esto, restaurar una sesion de 109 clips e importar otra carpeta deja
    bins apuntando a clips que ya no son esos.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])

    ventana.load_clips([_clip(0, "/dron/D.MP4")])

    assert ventana.bins.nombres() == []
