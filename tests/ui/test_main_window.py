# tests/ui/test_main_window.py
from pathlib import Path

from clasificador_video.manifest import Clip
from clasificador_video.player import QUALITY_PROFILES
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui import theme
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


def _seleccion(rooms) -> RoomSelection:
    seleccion = RoomSelection()
    for cuarto in rooms:
        seleccion.add(cuarto)
    return seleccion


def _window(qtbot, rooms=("Sala", "Cocina")) -> MainWindow:
    window = MainWindow(project_name="Casa Jardin", room_selection=_seleccion(rooms))
    qtbot.addWidget(window)
    return window


def _window_with_video(qtbot, cache_root: Path | None = None,
                       rooms=("Sala",)) -> MainWindow:
    window = MainWindow(
        project_name="Casa Jardin",
        room_selection=_seleccion(rooms),
        video_factory=FakeMpvForWindow,
        thumbnail_cache_root=cache_root,
    )
    qtbot.addWidget(window)
    return window


def _clip(numero: int = 1, cuarto: str | None = None, fps: float = 30.0) -> Clip:
    return Clip(
        orden=numero,
        ruta=Path(f"/tmp/C{numero:04d}.MP4"),
        categoria_path=[cuarto] if cuarto else [],
        fps=fps,
    )


def test_ventana_muestra_los_cuartos_activos_en_la_columna(qtbot):
    window = _window(qtbot)
    assert [f.nombre for f in window.room_rail.rows] == ["Sala", "Cocina"]


def test_cargar_clips_los_manda_al_clip_sheet(qtbot):
    window = _window(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    assert window.clip_sheet.count() == 1


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
    assert isinstance(window.video_stage.video, VideoWidget)
    assert len(window.video_stage.quality.buttons) == len(QUALITY_PROFILES)


def test_cambiar_calidad_aplica_el_perfil(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    window.video_stage.quality.selected.emit("1/2")
    assert window.video_stage.video.player._mpv.vid_scale == QUALITY_PROFILES["1/2"]


def test_leyenda_muestra_el_cuarto_real_de_cada_numero(qtbot):
    """Bug real de v1: la leyenda mostraba '1-9 cuartos' generico en vez
    de que cuarto real le toca a cada numero en la sesion activa."""
    window = _window_with_video(qtbot, rooms=("Sala", "Cocina"))
    # la leyenda de una linea murio con el rediseño, pero su intencion
    # sobrevive en el rail: cada numero muestra su cuarto real
    assert window.room_rail.rows[0].key_cap.text() == "1"
    assert window.room_rail.rows[0].nombre == "Sala"
    assert window.room_rail.rows[1].key_cap.text() == "2"
    assert window.room_rail.rows[1].nombre == "Cocina"


def test_boton_importar_carpetas_existe(qtbot):
    window = _window_with_video(qtbot)
    assert window.room_rail.import_button.text() == "Importar carpetas…"


def test_boton_importar_tiene_objectname_para_fondo_distinto_del_panel(qtbot):
    """Bug real de v1: el boton usaba el mismo color de fondo que el
    panel y era invisible como boton."""
    window = _window_with_video(qtbot)
    assert window.room_rail.import_button.objectName() == "importButton"


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
    window.room_rail.import_button.click()
    # el panel de carpetas importadas murio; lo que importa es que la
    # carpeta entro al ingest y que la ruta se ve en la barra de estado
    assert [c.display_name for c in window.ingest_tree.top_level_folders()] == ["FX30"]
    assert window.status_bar.volume_label.text() == str(carpeta_a)


class FakeProbe:
    def __init__(self):
        self.calls = []

    def __call__(self, path):
        self.calls.append(path)
        return {"width": 1920, "height": 1080, "fps": 59.94005994005994, "has_audio": True, "duration_frames": 360, "rotation": 0}


def test_importar_carpeta_construye_clips_con_fps_de_ffprobe(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "C0001.MP4").touch()
    fake_probe = FakeProbe()
    monkeypatch.setattr(window, "_probe_clip", fake_probe)
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    assert window.current_clip.fps == 59.94005994005994
    assert window.current_clip.ruta.name == "C0001.MP4"
    assert window.clip_sheet.count() == 1


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
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "bueno.MP4").touch()
    (carpeta / "roto.MP4").touch()
    monkeypatch.setattr(window, "_probe_clip", _FlakyProbe(fail_on="roto.MP4"))
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    rutas = [Path(c.ruta).name for c in window.clips]
    assert rutas == ["bueno.MP4"]
    assert window.clip_sheet.count() == 1


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
    job = _ThumbnailJob(1, 0, Path("/a.MP4"), tmp_path, None)
    shiboken6.delete(job.signals)

    job.run()  # no debe lanzar


def test_avanzar_de_clip_no_borra_las_miniaturas_ya_cargadas(qtbot):
    """Bug real reportado en uso: al avanzar con las flechas, el filmstrip
    se reconstruia entero (via _refresh_clip_sheet -> Filmstrip.set_clips),
    lo que perdia los pixmaps ya cargados por los _ThumbnailJob y volvia
    a mostrar '(sin miniatura)' en todos los clips."""
    from PySide6.QtGui import QPixmap

    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    pm = QPixmap(20, 20)
    pm.fill()
    for w in window.clip_sheet.item_widgets:
        w.set_pixmap(pm)
    window.handle_arrow("next")
    assert all(w.has_pixmap() for w in window.clip_sheet.item_widgets)


def test_avanzar_de_clip_preserva_los_mismos_widgets_del_clip_sheet(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    ids_antes = [id(w) for w in window.clip_sheet.item_widgets]
    window.handle_arrow("next")
    ids_despues = [id(w) for w in window.clip_sheet.item_widgets]
    assert ids_antes == ids_despues


def test_reimportar_reconstruye_el_clip_sheet_de_verdad(qtbot):
    """update_clips solo actualiza en el lugar si la cantidad de clips no
    cambio -- una reimportacion (aunque coincida en cantidad) debe forzar
    reconstruccion via load_clips, no arrastrar pixmaps del material viejo."""
    from PySide6.QtGui import QPixmap

    window = _window_with_video(qtbot)
    window.load_clips([Clip(orden=1, ruta=Path("/viejo.MP4"), categoria_path=[], fps=30.0)])
    pm = QPixmap(20, 20)
    pm.fill()
    window.clip_sheet.item_widgets[0].set_pixmap(pm)

    window.load_clips([Clip(orden=1, ruta=Path("/nuevo.MP4"), categoria_path=[], fps=30.0)])
    assert not window.clip_sheet.item_widgets[0].has_pixmap()


def test_thumbnail_stale_de_importacion_anterior_se_ignora(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail", _no_mpv_in_test
    )
    window.load_clips([Clip(orden=1, ruta=Path("/a1.MP4"), categoria_path=[], fps=30.0)])
    window._schedule_thumbnails()  # generacion 1
    window.load_clips([Clip(orden=1, ruta=Path("/b1.MP4"), categoria_path=[], fps=30.0)])
    window._schedule_thumbnails()  # generacion 2
    window._thread_pool.waitForDone(5000)

    calls = []
    for w in window.clip_sheet.item_widgets:
        monkeypatch.setattr(w, "set_pixmap", lambda pixmap, _w=w: calls.append(_w))

    window._on_thumbnail_ready(1, 0, [tmp_path / "stale.jpg"])
    assert calls == []
    window._on_thumbnail_ready(2, 0, [tmp_path / "fresh.jpg"])
    assert len(calls) == 1


def test_thumbnails_quedan_en_un_cache_persistente_que_sobrevive_al_cierre(qtbot, tmp_path):
    """Bug de fluidez real: antes las miniaturas vivian en un directorio
    temporal que se borraba al cerrar la app, asi que cada sesion nueva
    volvia a pagar el costo real de extraccion (varios segundos por clip)
    aunque el material fuera el mismo. Ahora el cache es persistente."""
    from PySide6.QtGui import QCloseEvent

    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)
    from clasificador_video.thumbnails import cache_dir_for
    cache_dir = cache_dir_for(clip_path, cache_root)
    cache_dir.mkdir(parents=True)
    (cache_dir / "strip_00.jpg").write_bytes(b"fake-jpeg")

    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._schedule_thumbnails()
    window._thread_pool.waitForDone(2000)
    window.closeEvent(QCloseEvent())

    assert cache_dir.exists()
    assert (cache_dir / "strip_00.jpg").exists()


def test_cache_hit_no_relanza_mpv(qtbot, monkeypatch, tmp_path):
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)
    from clasificador_video.thumbnails import cache_dir_for
    cache_dir = cache_dir_for(clip_path, cache_root)
    cache_dir.mkdir(parents=True)
    (cache_dir / "strip_00.jpg").write_bytes(b"fake-jpeg")

    called = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: called.append(1) or [],
    )
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail",
        lambda *a, **k: called.append(1) or (_ for _ in ()).throw(RuntimeError("no deberia llamarse")),
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._schedule_thumbnails()
    window._thread_pool.waitForDone(2000)
    assert called == []
    assert window.clip_sheet.item_widgets[0].has_pixmap()


def test_load_clips_arranca_el_primer_clip_en_el_reproductor(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    assert window.video_stage.video.player._mpv.loaded_path == "/a.MP4"


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
    assert window.video_stage.video.player._mpv.loaded_path == "/b.MP4"


def test_click_en_un_thumbnail_del_clip_sheet_carga_ese_clip(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=3, ruta=Path("/c.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    window.clip_sheet.clip_clicked.emit(2)
    assert window.current_index == 2
    assert window.video_stage.video.player._mpv.loaded_path == "/c.MP4"


def test_click_real_en_thumbnail_no_crasha_al_reconstruir_clip_sheet(qtbot):
    """Bug real de uso (crash SIGSEGV reportado en vivo, 2026-08-06, ver
    docs/superpowers/HANDOFF-2026-08-06-crash-al-importar.md):

    Click real con el mouse sobre una miniatura de la hoja dispara
    `select_clip` -> `_refresh_clip_sheet` -> `Filmstrip.set_clips`, que
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
    de la hoja. Si los widgets se preservan, Qt nunca regresa a un
    widget ya destruido y la condicion de carrera desaparece.

    Bonus de bug confirmado por la misma cadena: `_refresh_clip_sheet`
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
    for w in window.clip_sheet.item_widgets:
        pm = QPixmap(50, 50)
        pm.fill()
        w.set_pixmap(pm)
        pixmap_widths.append(w.image_label.pixmap().width())
    ids_antes = [id(w) for w in window.clip_sheet.item_widgets]
    assert all(pw > 0 for pw in pixmap_widths)

    # click real con QTest (mecanismo interno de qtbot.mouseClick) sobre
    # la tercera miniatura, sin mantener ref python sostenida aparte.
    QTest.mouseClick(
        window.clip_sheet.item_widgets[2], Qt.LeftButton, Qt.NoModifier, QPoint(5, 5)
    )

    # la seleccion cambio y el reproductor cargo el clip correcto
    assert window.current_index == 2
    assert window.video_stage.video.player._mpv.loaded_path == "/c.MP4"
    # no se reconstruyo el filmstrip: mismos widgets (mismos ids) y pixmaps
    # preservados -> imposibilita el crash y la perdida de miniaturas.
    ids_despues = [id(w) for w in window.clip_sheet.item_widgets]
    assert ids_despues == ids_antes, (
        "el filmstrip se reconstruyo durante el click -> los widgets se "
        "destruyen dentro de su propio mousePressEvent (crash nativo real)"
    )
    widths_despues = [w.image_label.pixmap().width() for w in window.clip_sheet.item_widgets]
    assert widths_despues == pixmap_widths, (
        "los pixmaps ya cargados se perdieron al reconstruir el filmstrip"
    )


def test_marcar_in_actualiza_la_scrub_bar_visiblemente(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_stage.video.player._mpv.time_pos = 2.0
    assert window.scrub_bar._in_frame is None
    window.handle_key_press("i")
    assert window.scrub_bar._in_frame == 120
    assert window.scrub_bar._fps == 60.0


def test_marcar_out_y_deshacer_se_reflejan_en_la_scrub_bar(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.video_stage.video.player._mpv.time_pos = 4.0
    window.handle_key_press("o")
    assert window.scrub_bar._out_frame == 120
    window.handle_key_press("u")
    assert window.scrub_bar._in_frame is None
    assert window.scrub_bar._out_frame is None


def test_cambiar_de_clip_actualiza_el_in_out_de_la_scrub_bar_al_del_nuevo_clip(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0, in_frame=10, out_frame=20),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    assert window.scrub_bar._in_frame == 10
    window.handle_arrow("next")
    assert window.scrub_bar._in_frame is None


def test_tick_playhead_actualiza_la_posicion_de_la_scrub_bar(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    window.video_stage.video.player._mpv.time_pos = 7.0
    window._tick_playhead()
    assert window.scrub_bar._position == 7.0


def test_tecla_i_marca_in_en_el_clip_actual_con_el_fps_del_clip(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_stage.video.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    assert window.current_clip.in_frame == 120


def test_tecla_o_marca_out(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_stage.video.player._mpv.time_pos = 5.0
    window.handle_key_press("o")
    assert window.current_clip.out_frame == 300


def test_tecla_u_limpia_in_out_del_clip(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_stage.video.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    window.handle_key_press("u")
    assert window.current_clip.in_frame is None
    assert window.current_clip.out_frame is None



def test_presionar_tecla_de_cuarto_con_multiseleccion_aplica_a_todos_los_seleccionados(qtbot):
    window = _window(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=3, ruta=Path("/c.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    window.clip_sheet.set_selected({0, 2})
    window.handle_key_press("2")  # "Cocina"
    assert window.clips[0].categoria_path == ["Cocina"]
    assert window.clips[1].categoria_path == []  # no estaba seleccionado
    assert window.clips[2].categoria_path == ["Cocina"]


def test_seleccion_de_un_solo_clip_no_activa_modo_lote(qtbot):
    """Con 0 o 1 clip seleccionado, la tecla de cuarto sigue aplicando
    solo al clip actual -- el comportamiento de siempre."""
    window = _window(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    window.clip_sheet.set_selected({0})
    window.handle_key_press("2")
    assert window.clips[0].categoria_path == ["Cocina"]
    assert window.clips[1].categoria_path == []


def test_toolbar_muestra_posicion_y_resumen_de_estado(qtbot):
    window = _window(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0, flag="pick"),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0, flag="reject"),
        Clip(orden=3, ruta=Path("/c.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    assert "1 / 3" in window.video_stage.file_label.text()
    # la leyenda pasó de una etiqueta de texto a puntos de color con el
    # numero: `● 41 picks ● 9 rejects ● 12 sin clasificar` no entraba en los
    # 200 px del rail y se cortaba (ver ANALISIS-2026-08-08-post-f2 §3)
    assert [p.text() for p in window.room_rail.leyenda.puntos] == ["1", "1", "3"]
    assert "picks" in window.room_rail.leyenda.puntos[0].toolTip()
    assert "3 sin clasificar" in window.status_bar.unclassified_label.text()


def test_badge_sin_clasificar_se_vacia_cuando_todo_esta_clasificado(qtbot):
    window = _window(qtbot)
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0)])
    assert window.status_bar.unclassified_label.text() == ""


def test_inspector_muestra_metadata_del_clip_actual(qtbot):
    window = _window(qtbot)
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Cocina"], fps=30.0, flag="pick"),
    ])
    # el panel inspector de 200 px murio: el nombre y los datos tecnicos
    # van a la barra de estado, y cuarto y estado a los badges sobre el video
    assert "a.MP4" in window.status_bar.clip_label.text()
    # cuarto y estado son DOS badges, cada uno con su color: juntarlos en una
    # etiqueta gris tiraba el color (ver ANALISIS-2026-08-08-post-f2 §3)
    assert "COCINA" in window.video_stage.badges.room_badge.text()
    assert "PICK" in window.video_stage.badges.flag_badge.text()
    assert theme.PICK_COLOR in window.video_stage.badges.flag_badge.styleSheet()



def test_columna_de_cuartos_muestra_contador_de_clips(qtbot):
    window = _window_with_video(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Sala"], fps=30.0),
    ]
    window.load_clips(clips)
    assert window.room_rail.rows[0].nombre == "Sala"
    assert window.room_rail.rows[0].count_label.text() == "2"


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
    window._flush_autosave()  # fuerza el guardado con debounce a que pase ya
    import json
    saved = json.loads(session_path.read_text())
    assert saved["clips"][0]["categoria_path"] == ["Sala"]
    assert saved["clips"][0]["flag"] == "none"


def test_autosave_tiene_debounce_no_escribe_sincronicamente(qtbot, tmp_path):
    """Bug de fluidez real: antes cada tecla escribia la sesion completa
    a disco de forma sincronica en el hilo de la UI. Ahora _autosave()
    solo arranca un debounce -- el guardado real llega despues, en un
    hilo aparte."""
    window = _window_with_video(qtbot)
    session_path = tmp_path / "sesion.json"
    window.session_path = session_path
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0)])
    assert not session_path.exists()  # load_clips ya llamo a _autosave(), pero no escribio todavia


def test_varias_ediciones_seguidas_coalescen_en_un_solo_guardado(qtbot, tmp_path):
    window = _window_with_video(qtbot)
    session_path = tmp_path / "sesion.json"
    window.session_path = session_path
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    window.handle_key_press("1")
    window.handle_key_press("p")
    # tres ediciones seguidas (load_clips, tecla de cuarto, pick) deberian
    # reiniciar el mismo timer de debounce, no encolar tres escrituras
    assert window._autosave_timer.isActive()
    window._flush_autosave()
    import json
    saved = json.loads(session_path.read_text())
    assert saved["clips"][0]["categoria_path"] == ["Sala"]
    assert saved["clips"][0]["flag"] == "pick"


def test_cerrar_la_ventana_no_pierde_la_ultima_edicion_sin_guardar(qtbot, tmp_path):
    from PySide6.QtGui import QCloseEvent

    window = _window_with_video(qtbot)
    session_path = tmp_path / "sesion.json"
    window.session_path = session_path
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0)])
    assert not session_path.exists()  # todavia en la ventana de debounce
    window.closeEvent(QCloseEvent())
    import json
    saved = json.loads(session_path.read_text())
    assert saved["clips"][0]["categoria_path"] == ["Sala"]


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
    window.title_bar.export_button.click()
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
    window.title_bar.export_button.click()
    assert warns == [1]
    assert out.exists()


def test_widgets_clave_tienen_objectname_para_el_tema(qtbot):
    window = _window(qtbot)
    assert window.video_stage.video.objectName() == "videoWidget"
    assert window.title_bar.export_button.objectName() == "exportButton"
    assert window.room_rail.objectName() == "roomRail"
    assert window.clip_sheet.objectName() == "clipSheet"
    assert window.status_bar.objectName() == "statusBar"


def test_timecode_overlay_vacio_sin_clip(qtbot):
    window = _window_with_video(qtbot)
    assert window.video_stage.timecode_label.text() == ""


def test_timecode_overlay_muestra_in_y_out(qtbot):
    window = _window_with_video(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0, in_frame=300, out_frame=900)
    ]
    window.load_clips(clips)
    window._update_scrub_bar()
    text = window.video_stage.timecode_label.text()
    assert "IN 00:10:00" in text
    assert "OUT 00:30:00" in text
    assert "rango 20s" in text


def test_timecode_overlay_sin_in_ni_out_no_muestra_esos_segmentos(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window._update_scrub_bar()
    text = window.video_stage.timecode_label.text()
    assert "IN " not in text
    assert "OUT " not in text


def test_scrub_bar_seek_started_pausa_el_player(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.video_stage.video.player.play()
    assert window.video_stage.video.player.is_paused is False
    window.scrub_bar.seek_started.emit()
    assert window.video_stage.video.player.is_paused is True


def test_scrub_bar_seek_requested_mueve_el_player_y_la_barra(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.video_stage.video.player._mpv.duration = 60.0
    window.scrub_bar.seek_requested.emit(15.0)
    assert window.video_stage.video.player._mpv.time_pos == 15.0
    assert window.scrub_bar._position == 15.0


# ---------------------------------------------------------------------------
# F2 Task 1: el tamaño real del clip. El ancho del video lo dicta la relacion
# de aspecto, asi que la F2 depende de este dato -- que hoy se calcula en
# probe_clip y se tira. Se guarda en memoria y NO en Clip: agregarle campos
# cambiaria to_dict() y con eso el contrato del manifest con el plugin.
# ---------------------------------------------------------------------------


class _ProbeVertical:
    """Clip vertical de la FX30: probe.py ya devuelve width/height
    corregidos por rotacion."""

    def __call__(self, path):
        return {"width": 2160, "height": 3840, "fps": 29.97,
                "has_audio": True, "duration_frames": 540, "rotation": 90}


def test_importar_guarda_el_tamano_real_de_cada_clip(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "C0001.MP4").touch()
    monkeypatch.setattr(window, "_probe_clip", _ProbeVertical())
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    assert window._clip_sizes[0] == (2160, 3840)


def test_importar_no_truena_si_el_probe_no_trae_tamano(qtbot, monkeypatch, tmp_path):
    """Un doble de pruebas viejo puede no traer width/height: el import
    tiene que seguir funcionando y caer en el aspecto por defecto."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "C0001.MP4").touch()
    monkeypatch.setattr(window, "_probe_clip", lambda p: {"fps": 29.97, "duration_frames": 540})
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    assert window.aspect_ratio_for(0) == 16 / 9


def test_aspect_ratio_usa_el_tamano_del_clip(qtbot):
    window = _window(qtbot)
    window._clip_sizes = {0: (2160, 3840)}
    assert window.aspect_ratio_for(0) == 2160 / 3840


def test_aspect_ratio_cae_en_16_9_si_no_se_conoce_el_tamano(qtbot):
    """Sesion restaurada de disco: no se volvio a correr ffprobe."""
    window = _window(qtbot)
    window._clip_sizes = {}
    assert window.aspect_ratio_for(0) == 16 / 9


def test_aspect_ratio_ignora_tamanos_invalidos(qtbot):
    window = _window(qtbot)
    window._clip_sizes = {0: (0, 0)}
    assert window.aspect_ratio_for(0) == 16 / 9


# ---------------------------------------------------------------------------
# F2: estructura. Estas son las medidas OBJETIVAS de la fase -- se verifican
# con una regla, no con una opinion sobre si "se ve bien".
# ---------------------------------------------------------------------------


def test_la_ventana_no_tiene_bandas_horizontales(qtbot):
    """El layout raiz solo puede tener tres filas: barra de titulo, cuerpo
    y barra de estado. Cualquier cuarta fila es una banda, y en un clip
    9:16 cada 16 px de banda cuestan 9 px de ancho de video."""
    window = _window_with_video(qtbot)
    assert window.layout().count() == 3


def test_alturas_fijas_de_las_barras(qtbot):
    window = _window_with_video(qtbot)
    assert window.title_bar.height() == theme.TITLEBAR_HEIGHT
    assert window.status_bar.height() == theme.STATUSBAR_HEIGHT


def test_anchos_fijos_de_los_rails(qtbot):
    window = _window_with_video(qtbot)
    assert window.room_rail.width() == theme.RAIL_WIDTH
    assert window.tool_column.width() == theme.TOOLCOL_WIDTH


def test_un_clip_vertical_ocupa_el_ancho_del_mockup(qtbot):
    """LA medida de la F2. Ventana 1600x1000, clip 9:16:
    cuerpo = 1000 - 36 - 24 = 940, video = 940 * 9/16 = 529.
    El diseño viejo daba 328."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    window._clip_sizes = {0: (2160, 3840)}
    window.load_clips([Clip(orden=1, ruta=Path("/tmp/a.mp4"), categoria_path=[], fps=29.97)])
    window._resize_video_stage()
    assert window.video_stage.width() == 529


def test_un_clip_horizontal_no_desborda_la_hoja(qtbot):
    """El video crece hasta donde la hoja conserva su minimo."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    window._clip_sizes = {0: (3840, 2160)}
    window.load_clips([Clip(orden=1, ruta=Path("/tmp/a.mp4"), categoria_path=[], fps=29.97)])
    window._resize_video_stage()
    maximo = 1600 - theme.RAIL_WIDTH - theme.TOOLCOL_WIDTH - theme.SHEET_MIN_WIDTH
    assert window.video_stage.width() == maximo


def test_cambiar_de_clip_reajusta_el_ancho_del_video(qtbot):
    """Decision tomada con Bruno: la pantalla salta al cambiar de
    orientacion, priorizando el aprovechamiento sobre la estabilidad."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    window._clip_sizes = {0: (2160, 3840), 1: (3840, 2160)}
    window.load_clips([
        Clip(orden=1, ruta=Path("/tmp/a.mp4"), categoria_path=[], fps=29.97),
        Clip(orden=2, ruta=Path("/tmp/b.mp4"), categoria_path=[], fps=29.97),
    ])
    window._resize_video_stage()
    vertical = window.video_stage.width()
    window.handle_arrow("next")
    assert window.video_stage.width() > vertical


def test_los_controles_del_video_no_son_hermanos_del_video(qtbot):
    """Si lo fueran volverian a ser bandas."""
    window = _window_with_video(qtbot)
    assert window.video_stage.scrub_bar.parent() is window.video_stage.video
    assert window.video_stage.timecode_label.parent() is window.video_stage.video


# --- F3: cuartos planos y rail editable en vivo -----------------------------


def test_una_tecla_clasifica_un_cuarto_numerado_de_inmediato(qtbot):
    """Antes, 'Recámara 1' abria el banner de subcuarto y se quedaba
    esperando una segunda tecla, sin limite de tiempo."""
    window = _window(qtbot, rooms=("Cocina", "Recámara 1"))
    window.load_clips([_clip()])
    window.handle_key_press("2")
    assert window.clips[0].categoria_path == ["Recámara 1"]


def test_categoria_path_sigue_siendo_una_lista(qtbot):
    """El contrato con el plugin de Premiere no se toca aunque el cuarto sea
    plano: el plugin ya maneja la lista de un elemento."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    assert window.clips[0].to_dict()["categoria_path"] == ["Cocina"]


def test_crear_un_cuarto_desde_el_rail_le_da_la_siguiente_tecla(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.room_rail.room_created.emit("Alberca")
    window.handle_key_press("2")
    assert window.clips[0].categoria_path == ["Alberca"]


def test_la_fila_de_nuevo_cuarto_queda_debajo_de_los_cuartos(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.room_rail.room_created.emit("Alberca")
    layout = window.room_rail._rooms_layout
    ultimo = layout.itemAt(layout.count() - 1).widget()
    assert ultimo is window.room_rail.new_room_row


def test_renombrar_un_cuarto_renombra_los_clips_ya_clasificados(qtbot):
    """Si no, los clips quedan apuntando a un cuarto que ya no existe y
    desaparecen del rail sin haberse movido a ningun lado."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.room_rail.room_renamed.emit("Cocina", "Cocina chica")
    assert window.clips[0].categoria_path == ["Cocina chica"]
    assert window.room_selection.active_rooms() == ["Cocina chica"]


def test_renombrar_no_le_cambia_la_tecla_al_cuarto(qtbot):
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip()])
    window.room_rail.room_renamed.emit("Cocina", "Cocineta")
    window.handle_key_press("1")
    assert window.clips[0].categoria_path == ["Cocineta"]


def test_borrar_un_cuarto_deja_sus_clips_sin_clasificar(qtbot):
    """Vuelven a la cola de trabajo, que es donde tienen que estar: son
    clips que hay que volver a decidir, no clips perdidos."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.room_rail.room_removed.emit("Cocina")
    assert window.clips[0].categoria_path == []
    assert window.room_selection.active_rooms() == []


def test_reordenar_cambia_la_tecla_y_no_la_clasificacion(qtbot):
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip()])
    window.handle_key_press("2")
    assert window.clips[0].categoria_path == ["Sala"]
    window.room_rail.room_moved.emit("Sala", -1)
    assert window.clips[0].categoria_path == ["Sala"]        # el clip no se movio
    assert window.room_selection.active_rooms() == ["Sala", "Cocina"]
    window.load_clips([_clip(2)])
    window.handle_key_press("1")                             # ahora "1" es Sala
    assert window.clips[0].categoria_path == ["Sala"]


def test_el_router_se_entera_de_cada_cambio_del_rail(qtbot):
    """El router se construye una sola vez y se queda con la lista que le
    dieron: si no se vuelve a pasar, las teclas clasifican al cuarto
    equivocado EN SILENCIO."""
    window = _window(qtbot, rooms=("Cocina",))
    window.room_rail.room_created.emit("Alberca")
    assert window._router.active_rooms == ["Cocina", "Alberca"]
    window.room_rail.room_moved.emit("Alberca", -1)
    assert window._router.active_rooms == ["Alberca", "Cocina"]
    window.room_rail.room_removed.emit("Alberca")
    assert window._router.active_rooms == ["Cocina"]


def test_la_ventana_arranca_sin_cuartos_y_se_puede_trabajar(qtbot):
    """La app abre lista para trabajar: sin paso previo de configuracion."""
    window = _window(qtbot, rooms=())
    window.load_clips([_clip()])
    assert window.room_rail.rows == []
    window.handle_key_press("1")   # no hay cuarto todavia: no pasa nada
    assert window.clips[0].categoria_path == []
    window.room_rail.room_created.emit("Cocina")
    window.handle_key_press("1")
    assert window.clips[0].categoria_path == ["Cocina"]


def test_el_autosave_ya_no_escribe_el_arbol_de_subcuartos(qtbot, tmp_path):
    import json

    window = _window(qtbot, rooms=("Cocina",))
    window.session_path = tmp_path / "sesion.json"
    window.load_clips([_clip()])
    window._write_autosave_now()
    window._autosave_pool.waitForDone(2000)
    data = json.loads((tmp_path / "sesion.json").read_text(encoding="utf-8"))
    assert "category_tree" not in data
    assert data["rooms"] == ["Cocina"]


def test_cmd_a_selecciona_el_grupo_y_permite_asignarlo_de_una(qtbot):
    """La hoja anuncia `⌘A selecciona el grupo` en cada encabezado: el atajo
    tiene que existir de verdad."""
    window = _window(qtbot, rooms=("Sala", "Cocina"))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window.select_clip(0)
    window.select_current_group()
    assert window.selected_indices == [0, 1, 2]   # los tres sin clasificar
    window.handle_key_press("2")
    assert [c.categoria_path for c in window.clips] == [["Cocina"]] * 3


# --- F4: deshacer con historial visible -------------------------------------


def test_asignar_un_cuarto_deja_entrada_en_el_historial(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(93)])
    window.handle_key_press("1")
    entrada = window.history.entries()[0]
    assert entrada.etiqueta == "Cocina"
    assert "clip 093" in entrada.detalle
    assert entrada.color == theme.room_color(0)


def test_deshacer_devuelve_el_clip_a_sin_clasificar(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.undo()
    assert window.clips[0].categoria_path == []
    assert window.history.entries() == []


def test_deshacer_una_asignacion_en_lote_es_UNA_sola_accion(qtbot):
    """Equivocarse asignando seis clips a la vez es un error seis veces mas
    caro: tiene que costar un ⌘Z, no seis."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 7)])
    window.select_clip(0)
    window.select_current_group()
    window.handle_key_press("1")
    assert "6 clips" in window.history.entries()[0].detalle
    window.undo()
    assert [c.categoria_path for c in window.clips] == [[]] * 6


def test_deshacer_un_pick_no_toca_el_cuarto(qtbot):
    """Cada entrada guarda SOLO el campo que su accion cambio."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.handle_key_press("p")
    window.undo()
    assert window.clips[0].flag == "none"
    assert window.clips[0].categoria_path == ["Cocina"]   # sobrevive


def test_revertir_una_entrada_vieja_no_pisa_una_accion_posterior(qtbot):
    """El caso que obliga a guardar campos parciales: asignar cuarto a dos,
    marcar pick en uno, revertir la asignacion -> el pick sigue ahi."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.select_current_group()
    window.handle_key_press("1")            # los dos a Cocina
    asignacion = window.history.entries()[0]
    window.clip_sheet.set_selected({0})
    window.select_clip(0)
    window.handle_key_press("p")            # pick en el primero
    window.revert(asignacion.id)
    assert window.clips[0].categoria_path == []
    assert window.clips[0].flag == "pick"   # NO se lo llevo puesto


def test_deshacer_no_comparte_la_lista_con_el_clip(qtbot):
    """`categoria_path` es una lista: guardar la referencia en vez de una
    copia haria que el «antes» mutara junto con el clip y deshacer no
    hiciera nada."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.handle_key_press("2")
    window.undo()
    assert window.clips[0].categoria_path == ["Cocina"]


def test_deshacer_in_out_restaura_solo_el_extremo_que_se_marco(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip()])
    window.video_widget.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    window.handle_key_press("o")
    window.undo()                            # deshace el OUT
    assert window.clips[0].out_frame is None
    assert window.clips[0].in_frame is not None


def test_deshacer_el_borrado_de_in_out_los_devuelve(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip()])
    window.video_widget.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    window.handle_key_press("o")
    window.handle_key_press("u")
    window.undo()
    assert window.clips[0].in_frame is not None
    assert window.clips[0].out_frame is not None


def test_borrar_un_cuarto_se_puede_deshacer_entero(qtbot):
    """Es la unica operacion del rail que destruye trabajo: desclasifica
    todos sus clips."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.room_rail.room_removed.emit("Cocina")
    assert window.clips[0].categoria_path == []
    window.undo()
    assert window.room_selection.active_rooms() == ["Cocina", "Sala"]
    assert window.clips[0].categoria_path == ["Cocina"]
    assert window._router.active_rooms == ["Cocina", "Sala"]


def test_crear_y_renombrar_no_ensucian_el_historial(qtbot):
    """No pierden datos y se revierten a mano en un gesto."""
    window = _window(qtbot, rooms=("Cocina",))
    window.room_rail.room_created.emit("Alberca")
    window.room_rail.room_renamed.emit("Alberca", "Piscina")
    window.room_rail.room_moved.emit("Piscina", -1)
    assert window.history.entries() == []


def test_deshacer_sin_nada_que_deshacer_no_revienta(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.undo()


def test_el_historial_se_ve_en_el_rail(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    assert window.room_rail.history_rows[0].etiqueta == "Cocina"
    window.undo()
    assert window.room_rail.history_rows == []


def test_el_boton_de_revertir_del_rail_deshace_esa_accion(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.room_rail.history_rows[0].undo_button.click()
    assert window.clips[0].categoria_path == []


def test_importar_material_nuevo_vacia_el_historial(qtbot):
    """Lo de antes ya no aplica a nada: los indices apuntarian a otros
    clips."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.load_clips([_clip(5), _clip(6)])
    assert window.history.entries() == []


# --- F5: los filtros son la cola de navegación ------------------------------

from clasificador_video.filters import FilterState  # noqa: E402


def _cuatro(window):
    window.load_clips([_clip(1, "Cocina"), _clip(2), _clip(3, "Cocina"), _clip(4)])


def test_las_flechas_recorren_solo_la_cola_filtrada(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    window.select_clip(1)
    window.handle_arrow("next")
    assert window.current_index == 3      # se salta el 2, que esta clasificado


def test_al_final_de_la_cola_la_flecha_no_se_va_del_borde(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    window.select_clip(3)
    window.handle_arrow("next")
    assert window.current_index == 3


def test_si_el_clip_actual_no_esta_en_la_cola_la_flecha_va_al_siguiente_que_si(qtbot):
    """Pasa siempre que resuelves un clip: sale de la cola y el «actual» deja
    de pertenecer a ella. La flecha tiene que seguir desde ahi, no trabarse.

    Se prueba con `select_clip` a proposito, y no clasificando: clasificar YA
    avanza solo, y el test pasaria sin que la logica de la flecha exista.
    """
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))   # cola = [1, 3]
    window.select_clip(0)                                       # el 0 no esta
    window.handle_arrow("next")
    assert window.current_index == 1
    window.select_clip(2)                                       # el 2 tampoco
    window.handle_arrow("prev")
    assert window.current_index == 1


def test_con_la_cola_vacia_las_flechas_no_revientan(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(busqueda="no-existe-nada"))
    window.handle_arrow("next")
    window.handle_arrow("prev")


def test_asignar_un_cuarto_avanza_al_siguiente(qtbot):
    """DECISIONES.md: `1`-`9` es «asignar cuarto y avanzar»."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)
    window.handle_key_press("1")
    assert window.current_index == 1


def test_asignar_avanza_dentro_de_la_cola_filtrada(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))   # cola = [1, 3]
    window.select_clip(1)
    window.handle_key_press("1")     # el 1 se clasifica y sale de la cola
    assert window.current_index == 3


def test_asignar_en_lote_NO_avanza(qtbot):
    """Con seis seleccionados, avanzar es un salto sin sentido."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)
    window.select_current_group()
    window.handle_key_press("1")
    assert window.current_index == 0


def test_pick_no_avanza(qtbot):
    """Solo los cuartos avanzan: marcar pick es lo ultimo que haces sobre un
    clip que estas mirando, y avanzar te sacaria de el."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)
    window.handle_key_press("p")
    assert window.current_index == 0


def test_el_visor_dice_la_posicion_en_la_cola_cuando_hay_filtro(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    window.select_clip(3)
    assert "2 de 2 en la cola" in window.video_stage.file_label.text()


def test_sin_filtro_el_visor_sigue_diciendo_el_total(qtbot):
    """Sin filtrar, tu posicion en el shooting entero SI sirve."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)
    assert "1 / 4" in window.video_stage.file_label.text()


def test_el_aviso_de_sin_clasificar_aplica_el_filtro_al_clickearlo(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.status_bar.unclassified_clicked.emit()
    assert window.filters.mostrar == "sin_clasificar"
    assert window.clip_sheet.chips["sin_clasificar"].isChecked()


def test_la_hoja_solo_muestra_la_cola(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    visibles = [i for i, c in enumerate(window.clip_sheet.item_widgets)
                if not c.isHidden()]
    assert visibles == [1, 3]


def test_el_chip_de_cola_dice_cuantos_quedan(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    assert "2 clips" in window.clip_sheet.queue_chip.text()


def test_los_chips_muestran_los_conteos_reales(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    assert "2" in window.clip_sheet.chips["sin_clasificar"].text()
    assert "2" in window.clip_sheet.chips["clasificados"].text()


def test_tocar_un_chip_filtra_de_verdad(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.clip_sheet.chips["sin_clasificar"].click()
    assert window.filters.mostrar == "sin_clasificar"
    assert [i for i, c in enumerate(window.clip_sheet.item_widgets)
            if not c.isHidden()] == [1, 3]


def test_el_lote_no_toca_clips_escondidos_por_el_filtro(qtbot):
    """Una seleccion vieja escondida por un filtro recibiria la asignacion
    sin que la veas."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    _cuatro(window)
    window.clip_sheet.set_selected({0, 1, 2})
    window.set_filters(FilterState(mostrar="sin_clasificar"))   # solo 1 y 3
    window.select_clip(1)
    window.handle_key_press("2")
    assert window.clips[1].categoria_path == ["Sala"]
    assert window.clips[0].categoria_path == ["Cocina"]   # intacto
    assert window.clips[2].categoria_path == ["Cocina"]   # intacto


def test_si_el_clip_actual_quedo_fuera_del_filtro_el_visor_no_inventa_posicion(qtbot):
    """Pasa apenas resuelves un clip: sale de la cola. Decir «0 de 12» seria
    mentir sobre donde estas."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)                                       # clasificado
    window.set_filters(FilterState(mostrar="sin_clasificar"))   # cola = [1, 3]
    texto = window.video_stage.file_label.text()
    assert "2 en la cola" in texto
    assert "0 de" not in texto


def test_el_aviso_tambien_marca_el_chip_como_el_que_define_la_cola(qtbot):
    """`setChecked` no emite `clicked`: por esa via la hoja no se enteraba y
    el chip quedaba sin el ambar de la cola."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.status_bar.unclassified_clicked.emit()
    assert window.clip_sheet.chips["sin_clasificar"].property("q") is True
