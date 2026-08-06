# tests/ui/test_main_window.py
from pathlib import Path

from clasificador_video.category_path import CategoryTree
from clasificador_video.manifest import Clip
from clasificador_video.player import QUALITY_PROFILES
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow
from clasificador_video.ui.video_widget import VideoWidget


class FakeMpvForWindow:
    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0
        self.vid_scale = None
        self.commands = []

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        self.commands.append(args)


def _window(qtbot) -> MainWindow:
    selection = RoomSelection()
    selection.toggle("Sala")
    selection.toggle("Cocina")
    window = MainWindow(project_name="Casa Jardin", room_selection=selection, category_tree=CategoryTree())
    qtbot.addWidget(window)
    return window


def _window_with_video(qtbot) -> MainWindow:
    selection = RoomSelection()
    selection.toggle("Sala")
    window = MainWindow(
        project_name="Casa Jardin",
        room_selection=selection,
        category_tree=CategoryTree(),
        video_factory=FakeMpvForWindow,
    )
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


def test_ventana_tiene_reproductor_embebido_y_selector_de_calidad(qtbot):
    window = _window_with_video(qtbot)
    assert isinstance(window.video_widget, VideoWidget)
    assert window.quality_combo.count() == len(QUALITY_PROFILES)


def test_cambiar_calidad_aplica_el_perfil(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    window.quality_combo.setCurrentText("1/2")
    assert window.video_widget.player._mpv.vid_scale == QUALITY_PROFILES["1/2"]


def test_ventana_muestra_leyenda_de_teclado(qtbot):
    window = _window_with_video(qtbot)
    assert "Espacio" in window.legend_label.text()
    assert "P/X/U" in window.legend_label.text()
