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


def test_leyenda_muestra_el_cuarto_real_de_cada_numero(qtbot):
    """Bug real de v1: la leyenda mostraba '1-9 cuartos' generico en vez
    de que cuarto real le toca a cada numero en la sesion activa."""
    selection = RoomSelection()
    selection.toggle("Sala")
    selection.toggle("Cocina")
    window = MainWindow(
        project_name="Casa Jardin", room_selection=selection, category_tree=CategoryTree(),
        video_factory=FakeMpvForWindow,
    )
    qtbot.addWidget(window)
    assert "1 Sala" in window.legend_label.text()
    assert "2 Cocina" in window.legend_label.text()
    assert "1-9 cuartos" not in window.legend_label.text()


def test_boton_importar_carpetas_existe(qtbot):
    window = _window_with_video(qtbot)
    assert window.import_button.text() == "Importar carpetas…"


def test_boton_importar_tiene_objectname_para_fondo_distinto_del_panel(qtbot):
    """Bug real de v1: el boton usaba el mismo color de fondo que el
    panel y era invisible como boton."""
    window = _window_with_video(qtbot)
    assert window.import_button.objectName() == "importButton"


def test_material_importado_tiene_encabezado_propio(qtbot):
    """Bug real de v1: la carpeta importada no tenia titulo ni
    separacion visual de la lista de cuartos."""
    window = _window_with_video(qtbot)
    assert window.ingest_title_label.text() == "Material importado"
    assert window.ingest_title_label.objectName() == "panelTitle"


def test_importar_carpetas_puebla_el_ingest_list(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    carpeta_a = tmp_path / "FX30"
    carpeta_a.mkdir()
    (carpeta_a / "C0001.MP4").touch()
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getExistingDirectory",
        lambda *a, **k: str(carpeta_a),
    )
    window._load_clips_from_ingest = lambda: None
    window.import_button.click()
    assert window.ingest_list.count() == 1
    assert window.ingest_list.item(0).text() == "FX30"


class FakeProbe:
    def __init__(self):
        self.calls = []

    def __call__(self, path):
        self.calls.append(path)
        return {"width": 1920, "height": 1080, "fps": 59.94005994005994, "has_audio": True, "duration_frames": 360, "rotation": 0}


def test_importar_carpeta_construye_clips_con_fps_de_ffprobe(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "C0001.MP4").touch()
    fake_probe = FakeProbe()
    monkeypatch.setattr(window, "_probe_clip", fake_probe)
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    assert window.current_clip.fps == 59.94005994005994
    assert window.current_clip.ruta.name == "C0001.MP4"
    assert window.filmstrip.count() == 1


class _FlakyProbe:
    """Probe que falla para ciertas rutas y devuelve info valida para el resto."""

    def __init__(self, fail_on: str):
        self._fail_on = fail_on
        self.calls = []

    def __call__(self, path):
        self.calls.append(path)
        if str(path).endswith(self._fail_on):
            raise RuntimeError("ffprobe no encontro pista de video")
        return {"width": 1920, "height": 1080, "fps": 30.0, "has_audio": True, "duration_frames": 100, "rotation": 0}


def test_import_ignora_clip_cuyo_ffprobe_falla_y_sigue_con_los_demas(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "bueno.MP4").touch()
    (carpeta / "roto.MP4").touch()
    monkeypatch.setattr(window, "_probe_clip", _FlakyProbe(fail_on="roto.MP4"))
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    rutas = [Path(c.ruta).name for c in window.clips]
    assert rutas == ["bueno.MP4"]
    assert window.filmstrip.count() == 1


def _no_mpv_in_test(*a, **k):
    raise RuntimeError("no se ejecuta mpv en tests")


def test_thumbnail_job_no_truena_si_su_signal_ya_fue_destruido(qtbot, monkeypatch, tmp_path):
    """Bug real visto en corridas repetidas de la suite: un job de
    miniatura de una prueba anterior a veces termina su run() (en un
    hilo del QThreadPool) despues de que la ventana dueña ya se
    destruyo junto con el QWidget que carga la senal `done` -- emitir
    sobre un objeto Qt ya borrado truena con RuntimeError dentro del
    hilo. El job debe descartar el resultado en silencio, no propagar."""
    import shiboken6

    from clasificador_video.ui.main_window import _ThumbnailJob

    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail",
        lambda *a, **k: tmp_path / "frame.jpg",
    )
    job = _ThumbnailJob(1, 0, Path("/a.MP4"), tmp_path)
    shiboken6.delete(job.signals)

    job.run()  # no debe lanzar


def test_thumbnail_stale_de_importacion_anterior_se_ignora(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail", _no_mpv_in_test
    )
    window.load_clips([Clip(orden=1, ruta=Path("/a1.MP4"), categoria_path=[], fps=30.0)])
    window._schedule_thumbnails()  # generacion 1
    window.load_clips([Clip(orden=1, ruta=Path("/b1.MP4"), categoria_path=[], fps=30.0)])
    window._schedule_thumbnails()  # generacion 2
    window._thread_pool.waitForDone(5000)

    calls = []
    for w in window.filmstrip.item_widgets:
        monkeypatch.setattr(w, "set_pixmap", lambda pixmap, _w=w: calls.append(_w))

    window._on_thumbnail_ready(1, 0, tmp_path / "stale.jpg")
    assert calls == []
    window._on_thumbnail_ready(2, 0, tmp_path / "fresh.jpg")
    assert len(calls) == 1


def test_close_event_limpia_el_thumb_dir_temporal(qtbot, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    window = _window_with_video(qtbot)
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail", _no_mpv_in_test
    )
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    window._schedule_thumbnails()
    thumb_dir = window._thumb_dir
    assert thumb_dir is not None and thumb_dir.exists()
    window._thread_pool.waitForDone(5000)
    window.closeEvent(QCloseEvent())
    assert not thumb_dir.exists()


def test_load_clips_arranca_el_primer_clip_en_el_reproductor(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    assert window.video_widget.player._mpv.loaded_path == "/a.MP4"


def test_flecha_derecha_avanza_al_siguiente_clip_y_lo_carga_en_el_player(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    window.handle_arrow("next")
    assert window.current_index == 1
    assert window.video_widget.player._mpv.loaded_path == "/b.MP4"


def test_click_en_un_thumbnail_del_filmstrip_carga_ese_clip(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=3, ruta=Path("/c.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    window.filmstrip.clip_clicked.emit(2)
    assert window.current_index == 2
    assert window.video_widget.player._mpv.loaded_path == "/c.MP4"


def test_click_real_en_thumbnail_no_crasha_al_reconstruir_filmstrip(qtbot):
    """Bug real de uso (crash SIGSEGV reportado en vivo, 2026-08-06, ver
    docs/superpowers/HANDOFF-2026-08-06-crash-al-importar.md):

    Click real con el mouse sobre una miniatura del filmstrip dispara
    `select_clip` -> `_refresh_filmstrip` -> `Filmstrip.set_clips`, que
    destruye (setParent(None) + reemplaza) TODOS los `_ClipItemWidget`
    --incluyendo el propio widget que esta dentro de su `mousePressEvent`
    mientras Qt todavia lo referencia internamente en `sendMouseEvent`.
    En el run loop nativo de cocoa (Bruno lo reproduce en vivo) esto
    termina en SIGSEGV (KERN_INVALID_ADDRESS 0xc) al volver del despacho
    anidado del evento de mouse.

    El QPA offscreen de los tests no reproduce el crash nativo (no pasa
    por processMouseEvent/sendMouseEvent anidado de cocoa), asi que este
    test verifica la propiedad estructural que lo imposibilita: el click
    solo cambia el clip actual (bordes) SIN destruir/recrear los widgets
    del filmstrip. Si los widgets se preservan, Qt nunca regresa a un
    widget ya destruido y la condicion de carrera desaparece.

    Bonus de bug confirmado por la misma cadena: `_refresh_filmstrip`
    recrea los widgets con thumbnail_path=None, perdiendo los pixmaps
    ya cargados por los _ThumbnailJob -- hacer click en un clip borraba
    las miniaturas de todos. Preservar los widgets tambien lo arregla.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QPoint

    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=3, ruta=Path("/c.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    # simula miniaturas ya cargadas en background por los _ThumbnailJob
    pixmap_widths = []
    for w in window.filmstrip.item_widgets:
        pm = QPixmap(50, 50)
        pm.fill()
        w.set_pixmap(pm)
        pixmap_widths.append(w._image_label.pixmap().width())
    ids_antes = [id(w) for w in window.filmstrip.item_widgets]
    assert all(pw > 0 for pw in pixmap_widths)

    # click real con QTest (mecanismo interno de qtbot.mouseClick) sobre
    # la tercera miniatura, sin mantener ref python sostenida aparte.
    QTest.mouseClick(
        window.filmstrip.item_widgets[2], Qt.LeftButton, Qt.NoModifier, QPoint(5, 5)
    )

    # la seleccion cambio y el reproductor cargo el clip correcto
    assert window.current_index == 2
    assert window.video_widget.player._mpv.loaded_path == "/c.MP4"
    # no se reconstruyo el filmstrip: mismos widgets (mismos ids) y pixmaps
    # preservados -> imposibilita el crash y la perdida de miniaturas.
    ids_despues = [id(w) for w in window.filmstrip.item_widgets]
    assert ids_despues == ids_antes, (
        "el filmstrip se reconstruyo durante el click -> los widgets se "
        "destruyen dentro de su propio mousePressEvent (crash nativo real)"
    )
    widths_despues = [w._image_label.pixmap().width() for w in window.filmstrip.item_widgets]
    assert widths_despues == pixmap_widths, (
        "los pixmaps ya cargados se perdieron al reconstruir el filmstrip"
    )


def test_tecla_i_marca_in_en_el_clip_actual_con_el_fps_del_clip(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_widget.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    assert window.current_clip.in_frame == 120


def test_tecla_o_marca_out(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_widget.player._mpv.time_pos = 5.0
    window.handle_key_press("o")
    assert window.current_clip.out_frame == 300


def test_tecla_u_limpia_in_out_del_clip(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_widget.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    window.handle_key_press("u")
    assert window.current_clip.in_frame is None
    assert window.current_clip.out_frame is None


def test_subcuarto_desconocido_pide_padre_y_se_cuelga(qtbot, monkeypatch):
    window = _window_with_video(qtbot)
    monkeypatch.setattr(
        window, "_ask_parent_room",
        lambda subroom: "Recámara 1",
    )
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window._router.subrooms = {"Recámara 1": []}   # existe el padre como opcion
    window.attach_subroom_or_resolve("Baño")
    assert window.category_tree.path_for("Recámara 1", subroom="Baño") == ["Recámara 1", "Baño"]
    assert window.current_clip.categoria_path == ["Recámara 1", "Baño"]


def test_columna_de_cuartos_muestra_contador_de_clips(qtbot):
    window = _window_with_video(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Sala"], fps=30.0),
    ]
    window.load_clips(clips)
    assert window.room_list_widget.item(0).text() == "Sala (2)"


def test_cada_accion_dispara_autosave(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    session_path = tmp_path / "sesion.json"
    window.session_path = session_path
    calls = []
    monkeypatch.setattr(window, "_autosave", lambda: calls.append(1))
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    window.handle_key_press("1")
    window.handle_key_press("p")
    assert len(calls) >= 3


def test_autosave_escribe_el_estado_actual(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    session_path = tmp_path / "sesion.json"
    window.session_path = session_path
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0)])
    window._autosave()
    import json
    saved = json.loads(session_path.read_text())
    assert saved["clips"][0]["categoria_path"] == ["Sala"]
    assert saved["clips"][0]["flag"] == "none"


def test_exportar_escribe_manifest_con_formato_del_plugin(qtbot, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QMessageBox
    window = _window_with_video(qtbot)
    out = tmp_path / "manifest.json"
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=59.94,
             in_frame=30, out_frame=200, flag="pick"),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=29.97, flag="none"),
    ])
    monkeypatch.setattr("clasificador_video.ui.main_window.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(out), ""))
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: QMessageBox.Ok)
    window.export_button.click()
    import json
    saved = json.loads(out.read_text())
    assert saved["proyecto"] == "Casa Jardin"
    assert saved["clips"][0]["ruta"] == "/a.MP4"
    assert saved["clips"][1]["categoria_path"] == []
    assert saved["clips"][0]["flag"] == "pick"
    assert saved["clips"][0]["in_frame"] == 30


def test_exportar_avisa_si_hay_clips_sin_clasificar_sin_bloquear(qtbot, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QMessageBox
    window = _window_with_video(qtbot)
    out = tmp_path / "m.json"
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
    ])
    warns = []
    monkeypatch.setattr("clasificador_video.ui.main_window.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(out), ""))
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: warns.append(1) or QMessageBox.Ok)
    window.export_button.click()
    assert warns == [1]
    assert out.exists()


def test_widgets_clave_tienen_objectname_para_el_tema(qtbot):
    window = _window(qtbot)
    assert window.video_widget.objectName() == "videoWidget"
    assert window.export_button.objectName() == "exportButton"
    assert window.legend_label.objectName() == "legendLabel"
    assert window.status_label.objectName() == "statusLabel"


def test_titulo_de_la_columna_de_cuartos_tiene_objectname_de_panel(qtbot):
    window = _window(qtbot)
    assert window.room_title_label.objectName() == "panelTitle"
