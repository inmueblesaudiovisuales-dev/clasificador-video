# tests/ui/test_main_window.py
from pathlib import Path

from clasificador_video.category_path import CategoryTree
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


def _window(qtbot) -> MainWindow:
    selection = RoomSelection()
    selection.toggle("Sala")
    selection.toggle("Cocina")
    window = MainWindow(project_name="Casa Jardin", room_selection=selection, category_tree=CategoryTree())
    qtbot.addWidget(window)
    return window


def test_ventana_muestra_los_cuartos_activos_en_la_columna(qtbot):
    window = _window(qtbot)
    assert window.room_list_widget.count() == 2


def test_cargar_clips_los_manda_al_filmstrip(qtbot):
    window = _window(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    assert window.filmstrip.count() == 1


def test_presionar_tecla_de_cuarto_asigna_categoria_al_clip_actual(qtbot):
    window = _window(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.handle_key_press("2")  # "Cocina" es el segundo cuarto activo
    assert window.current_clip.categoria_path == ["Cocina"]


def test_presionar_p_marca_pick_en_el_clip_actual(qtbot):
    window = _window(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.handle_key_press("p")
    assert window.current_clip.flag == "pick"
