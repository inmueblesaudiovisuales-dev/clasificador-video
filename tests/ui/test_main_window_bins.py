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


def test_agregar_clips_conserva_los_proxies_ya_enganchados(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)

    ventana.agregar_clips([_clip(1, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert ventana.clips[0].ruta_proxy == Path("/cam/AS03.MP4")
    assert ventana._proxy_sizes[0] == (1080, 1920)
    assert len(ventana.clips) == 2


def test_agregar_clips_conserva_el_historial(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    # el metodo real de clasificar: el plan lo llamaba `clasificar`, que no
    # existe en el codigo.
    ventana._apply_categoria_to_targets(["Cocina"])
    cuantas = len(ventana.history.entries())

    ventana.agregar_clips([_clip(1, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert cuantas == 1
    assert len(ventana.history.entries()) == cuantas


def test_agregar_clips_crea_el_bin_con_los_indices_nuevos(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])

    ventana.agregar_clips([_clip(2, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert ventana.bins.nombres() == ["Sony", "Dron"]
    assert ventana.bins.clips_de("Dron") == [2]


def test_agregar_al_mismo_bin_le_suma_los_indices(qtbot, ventana):
    """Importar dos veces la misma tarjeta no crea «Sony» y «Sony 2»."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])

    ventana.agregar_clips([_clip(1, "/cam/B.MP4")], nombre_de_bin="Sony",
                          origen=Path("/cam"))

    assert ventana.bins.nombres() == ["Sony"]
    assert ventana.bins.clips_de("Sony") == [0, 1]


def test_agregar_clips_renumera_el_orden_de_los_nuevos(qtbot, ventana):
    """`orden` es el numero que se ve en la tarjeta y el que viaja al
    manifest: dos clips con el mismo numero serian dos «clip 001»."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])

    ventana.agregar_clips([_clip(0, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert [c.orden for c in ventana.clips] == [1, 2, 3]


def test_agregar_clips_no_recrea_las_tarjetas_que_ya_estaban(qtbot, ventana):
    """El bug de Bruno visto desde la ventana: la portada vive en la
    tarjeta, y reconstruir la hoja se la lleva."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    antes = ventana.clip_sheet.item_widgets[0]

    ventana.agregar_clips([_clip(1, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert ventana.clip_sheet.item_widgets[0] is antes
    assert ventana.clip_sheet.count() == 2


def _carpeta_con(tmp_path, nombre, *archivos):
    carpeta = tmp_path / nombre
    carpeta.mkdir()
    for a in archivos:
        (carpeta / a).touch()
    return carpeta


def test_importar_una_segunda_carpeta_no_recrea_las_tarjetas(qtbot, tmp_path,
                                                             monkeypatch, ventana):
    """EL bug que Bruno reporto, de punta a punta: la portada vive en la
    tarjeta y la importacion la destruia."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    sony = _carpeta_con(tmp_path, "FX30", "C0001.MP4", "C0002.MP4")
    dron = _carpeta_con(tmp_path, "DRON", "DJI_0001.MP4")

    ventana.importar_rutas([sony])
    antes = list(ventana.clip_sheet.item_widgets)
    ventana.importar_rutas([dron])

    assert ventana.clip_sheet.item_widgets[:2] == antes
    assert ventana.bins.nombres() == ["FX30", "DRON"]
    assert ventana.bins.clips_de("DRON") == [2]
    assert [c.orden for c in ventana.clips] == [1, 2, 3]


def test_importar_la_misma_carpeta_dos_veces_no_duplica(qtbot, tmp_path,
                                                        monkeypatch, ventana):
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    sony = _carpeta_con(tmp_path, "FX30", "C0001.MP4")

    ventana.importar_rutas([sony])
    ventana.importar_rutas([sony])

    assert len(ventana.clips) == 1
    assert ventana.bins.nombres() == ["FX30"]
