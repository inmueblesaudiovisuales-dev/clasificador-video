# tests/ui/test_main_window.py
import threading
import time
from pathlib import Path

import pytest

from PySide6.QtCore import QObject, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from clasificador_video import proxy_gen

from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui import theme
from clasificador_video.ui.main_window import (
    MainWindow,
    _ProxyProbeJob,
    _ThumbnailJob,
)
from clasificador_video.ui.video_stage import VideoStage
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
        # mpv implementa `frame-step` como "despausar, mostrar un cuadro,
        # volver a pausar": queda pausado SOLO. El doble lo imita para que un
        # test no pueda pasar con una implementacion que ademas escribe
        # `pause`, que contra mpv real aborta el paso (medido el 2026-08-08).
        if args and args[0] in ("frame-step", "frame-back-step"):
            self.pause = True


def _seleccion(rooms) -> RoomSelection:
    seleccion = RoomSelection()
    for cuarto in rooms:
        seleccion.add(cuarto)
    return seleccion


def _window(qtbot, rooms=("Sala", "Cocina")) -> MainWindow:
    # con el doble SIEMPRE, aunque el test no hable del reproductor: sin el,
    # cualquier camino que toque `video_widget.player` enciende un mpv de
    # verdad --con sus hilos-- y esos hilos son el segfault intermitente que
    # aparecia en una de cada ocho corridas completas.
    window = MainWindow(project_name="Casa Jardin", room_selection=_seleccion(rooms),
                        video_factory=FakeMpvForWindow)
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


def _a_modo_clip(window: MainWindow) -> MainWindow:
    """Saca a la ventana de la hoja y la deja en el visor.

    Desde la F7 la app ARRANCA en la hoja: es lo primero que Bruno quiere
    ver. Un test que mira el visor --los badges, la etiqueta de archivo, la
    columna de herramientas-- tiene que cruzar a modo clip primero, porque
    en la hoja esos overlays no se refrescan: sin visor no hay un «clip
    actual» que describir.

    Se le da tamaño a la ventana --y se muestra-- antes de cruzar porque el
    cruce esconde y vuelve a mostrar el visor, y eso lo obliga a re-acomodar
    sus hijos: sin un tamaño real, el video queda de 44 px y la etiqueta del
    archivo se elide hasta quedar vacia. En la app eso no pasa nunca; es un
    artefacto de la ventana sin mostrar.
    """
    window.resize(1600, 1000)
    window.show()
    window.alternar_modo_hoja()
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


def test_importar_carpetas_mete_el_material_en_un_bin(qtbot, monkeypatch, tmp_path):
    """Antes esto comprobaba que la carpeta entrara al `ingest_tree`. Ese
    camino reconstruia el proyecto entero --y por eso a Bruno se le caian
    las portadas al importar la segunda carpeta--; ahora importar AGREGA, y
    lo que hay que comprobar es que el material quede en un bin con el
    nombre de la carpeta.
    """
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    carpeta_a = tmp_path / "FX30"
    carpeta_a.mkdir()
    (carpeta_a / "C0001.MP4").touch()
    monkeypatch.setattr(window, "_probe_clip", FakeProbe())
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getExistingDirectory",
        lambda *a, **k: str(carpeta_a),
    )
    window.room_rail.import_button.click()

    assert window.bins.nombres() == ["FX30"]
    assert [c.ruta.name for c in window.clips] == ["C0001.MP4"]
    # la ruta va con el tamaño del volumen desde la F10 (`· 214 GB`)
    assert window.status_bar.volume_label.text().startswith(str(carpeta_a))


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
    window.importar_rutas([carpeta])
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
    window.importar_rutas([carpeta])
    rutas = [Path(c.ruta).name for c in window.clips]
    assert rutas == ["bueno.MP4"]
    assert window.clip_sheet.count() == 1


def _no_mpv_in_test(*a, **k):
    raise RuntimeError("no se ejecuta mpv en tests")


def test_thumbnail_job_no_truena_si_la_ventana_ya_se_destruyo(qtbot, monkeypatch, tmp_path):
    """Un trabajo de miniatura puede terminar su `run()` --en un hilo del
    QThreadPool-- despues de que la ventana que escuchaba ya se destruyo.

    Antes esto se atajaba con un `except RuntimeError` alrededor del `emit`,
    apoyado en la idea de que el portador de la señal moria con la ventana.
    Ya no: el portador es un objeto aparte que el trabajo sostiene, asi que
    el `emit` es valido igual; lo unico que pasa es que Qt ya deshizo la
    conexion con la ventana muerta y el resultado no le llega a nadie."""
    import shiboken6

    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail",
        lambda *a, **k: tmp_path / "frame.jpg",
    )
    # sin `qtbot.addWidget`: esta ventana se destruye a proposito dentro
    # del test, y el teardown de qtbot no sabe manejar una ya borrada.
    window = MainWindow(project_name="Casa Jardin", room_selection=_seleccion(("Sala",)),
                        video_factory=FakeMpvForWindow)
    señales = window._señales_de_trabajos
    recibidos = []
    señales.miniatura_lista.connect(lambda *a: recibidos.append(a))
    job = _ThumbnailJob(1, 0, Path("/a.MP4"), tmp_path, None, señales)
    shiboken6.delete(window)

    job.run()  # no debe lanzar

    assert recibidos == [(1, 0, [tmp_path / "frame.jpg"])]


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
    # una tira ENTERA, no un solo cuadro: desde que las tiras cortadas se
    # vuelven a extraer, un `strip_00.jpg` solo ya no es un cache hit
    for i in range(12):
        (cache_dir / f"strip_{i:02d}.jpg").write_bytes(b"fake-jpeg")

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
    # Se comprueba que las miniaturas SIGAN ahí, no que midan lo mismo: el
    # ancho de la tarjeta depende del acomodo de la ventana, y cualquier
    # cambio de texto en la barra de titulo lo mueve unos pixeles. Comparar
    # anchos exactos hacia que este test --que cuida un crash nativo y la
    # perdida de portadas-- se cayera por un motivo que no tiene nada que ver
    # con ninguna de las dos cosas. Si se recrearan con `thumbnail_path=None`,
    # el pixmap seria nulo y el ancho 0, que es justo lo que esto detecta.
    widths_despues = [w.image_label.pixmap().width() for w in window.clip_sheet.item_widgets]
    assert all(ancho > 0 for ancho in widths_despues), (
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
    # a modo clip: mira la etiqueta del visor, que en la hoja no se refresca
    window = _a_modo_clip(_window(qtbot))
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
    # cuatro numeros desde la F7: destacados, picks, rejects, sin clasificar
    assert [p.text() for p in window.room_rail.leyenda.puntos] == ["0 dest.", "1", "1", "3"]
    assert "destacados" in window.room_rail.leyenda.puntos[0].toolTip()
    assert "picks" in window.room_rail.leyenda.puntos[1].toolTip()
    assert "3 sin clasificar" in window.status_bar.unclassified_label.text()


def test_badge_sin_clasificar_se_vacia_cuando_todo_esta_clasificado(qtbot):
    window = _window(qtbot)
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0)])
    assert window.status_bar.unclassified_label.text() == ""


def test_inspector_muestra_metadata_del_clip_actual(qtbot):
    # a modo clip: los badges de cuarto y estado viven sobre el video
    window = _a_modo_clip(_window(qtbot))
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
    # el estado viaja como subcarpeta DENTRO del cuarto: en Premiere el bin
    # «Sala» tiene adentro «Picks», y ahi cae este clip
    assert saved["clips"][0]["categoria_path"] == ["Sala", "Picks"]


def test_exportar_no_le_cambia_el_cuarto_a_los_clips_de_la_sesion(
        qtbot, monkeypatch, tmp_path):
    """La subcarpeta se agrega SOLO en el archivo que se exporta.

    Si tocara a los clips vivos, marcar un pick se veria en la app como un
    cambio de cuarto: el historial, la hoja, el rail y el autoguardado van
    todos por `categoria_path[0]`. Y exportar dos veces anidaria dos veces.
    """
    from PySide6.QtWidgets import QMessageBox
    window = _window_with_video(qtbot)
    out = tmp_path / "manifest.json"
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0,
             flag="pick"),
    ])
    monkeypatch.setattr("clasificador_video.ui.main_window.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(out), ""))
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: QMessageBox.Ok)

    window.title_bar.export_button.click()
    window.title_bar.export_button.click()      # y otra vez

    assert window.clips[0].categoria_path == ["Sala"]
    import json
    assert json.loads(out.read_text())["clips"][0]["categoria_path"] == [
        "Sala", "Picks"]


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
    # desde la F6 el pie son tres piezas y no una etiqueta con todo pegado:
    # el IN/OUT en timecode arriba a la derecha, y el resumen del rango en su
    # pastilla abajo. Los dos datos siguen visibles, en su lugar del mockup.
    io = window.video_stage.io_label.text()
    assert "IN 00:10:00" in io
    assert "OUT 00:30:00" in io
    pastilla = window.video_stage.range_pill.text()
    assert "600 f" in pastilla        # 900 - 300 cuadros
    assert "rango 20:00" in pastilla  # 20 s justos, sin cuadros sueltos


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
    window.importar_rutas([carpeta])
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
    window.importar_rutas([carpeta])
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
    """Solo tres filas se VEN: barra de titulo, cuerpo y barra de estado.
    Cualquier otra fila a la vista es una banda, y en un clip 9:16 cada
    16 px de banda cuestan 9 px de ancho de video.

    La cuarta fila del layout es la barra de media faltante, que nace
    escondida --y escondida no ocupa ni un pixel-- porque aparece solo
    cuando el proyecto se abre y sus archivos no estan donde decia.
    """
    window = _window_with_video(qtbot)
    raiz = window.layout()
    assert raiz.count() == 4
    assert window.aviso_de_media.isHidden()
    a_la_vista = [i for i in range(raiz.count())
                  if raiz.itemAt(i).widget() is None            # el cuerpo
                  or not raiz.itemAt(i).widget().isHidden()]
    assert len(a_la_vista) == 3


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
    """El video crece hasta donde la hoja conserva su mínimo REAL.

    Antes este test usaba `theme.SHEET_MIN_WIDTH`, que es justo la suposición
    equivocada que inflaba la ventana: el encabezado de la hoja pide bastante
    más que esa constante. Lo que importa no es el número, es que la suma
    cierre y la ventana no crezca.
    """
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    window._clip_sizes = {0: (3840, 2160)}
    window.load_clips([Clip(orden=1, ruta=Path("/tmp/a.mp4"), categoria_path=[], fps=29.97)])
    window._resize_video_stage()
    minimo_real = max(theme.SHEET_MIN_WIDTH,
                      window.clip_sheet.minimumSizeHint().width())
    assert window.video_stage.width() == (
        1600 - theme.RAIL_WIDTH - theme.TOOLCOL_WIDTH - minimo_real
    )
    assert window.width() == 1600



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


def test_deshacer_despues_de_renombrar_no_resucita_el_nombre_viejo(qtbot):
    """El historial guarda el `categoria_path` ANTERIOR, o sea el NOMBRE del
    cuarto. Renombrar no crea un cuarto nuevo -- es el mismo con otro
    nombre-- asi que el nombre tiene que moverse tambien ahi dentro.

    Sin esto, deshacer una accion anterior al renombrado dejaba al clip
    clasificado en un cuarto que ya no existe: contaba como clasificado en
    el progreso del rail, no aparecia en ningun renglon, la hoja le dibujaba
    un grupo fantasma con el nombre viejo, y asi viajaba a Premiere.
    """
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip()])
    window.handle_key_press("1")            # → Cocina
    window.select_clip(0)
    window.handle_key_press("2")            # te corriges: → Sala

    window.room_rail.room_renamed.emit("Cocina", "Cocina principal")
    window.undo()                           # deshaces lo ultimo

    assert window.clips[0].categoria_path == ["Cocina principal"]
    assert window.clips[0].categoria_path[0] in window.room_selection.active_rooms()


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
    # a modo clip: es la etiqueta del visor la que se comprueba
    window = _a_modo_clip(_window(qtbot, rooms=("Cocina",)))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    window.select_clip(3)
    assert "2 de 2 en la cola" in window.video_stage.file_label.text()


def test_sin_filtro_el_visor_sigue_diciendo_el_total(qtbot):
    """Sin filtrar, tu posicion en el shooting entero SI sirve."""
    # a modo clip: es la etiqueta del visor la que se comprueba
    window = _a_modo_clip(_window(qtbot, rooms=("Cocina",)))
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
    # a modo clip: es la etiqueta del visor la que se comprueba
    window = _a_modo_clip(_window(qtbot, rooms=("Cocina",)))
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


def test_los_atajos_anunciados_en_la_interfaz_existen(qtbot):
    """La barra de titulo anuncia `⌘E` y la hoja `⌘A`; el rail, `⌘Z`. Un
    atajo dibujado que no responde es la clase de detalle que hace desconfiar
    de una herramienta -- y ya se coló tres veces en este rediseño."""
    from PySide6.QtGui import QKeySequence

    window = _window(qtbot, rooms=("Cocina",))
    registrados = {s.key().toString() for s in window._shortcuts}
    for anunciado in ("Ctrl+E", "Ctrl+R", "Ctrl+A", "Ctrl+Z"):
        assert anunciado in registrados, f"{anunciado} se anuncia y no existe"
    assert QKeySequence(QKeySequence.StandardKey.SelectAll).toString() == "Ctrl+A"


def test_el_foco_al_rail_sigue_existiendo_sin_boton(qtbot):
    """El boton «Cuartos» murio a proposito: solo movia el foco, y desde
    afuera no se veia pasar nada -- Bruno lo reporto como «no hace nada».
    Su lugar en la barra lo ocupa «Proxies», que si es una accion.

    La funcion sigue: es lo que hace `⌘R`, que esta en DECISIONES.md."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.show()
    qtbot.waitExposed(window)
    window.room_rail.focus_rooms()
    assert window.room_rail.focusWidget() is window.room_rail.rows[0]
    assert not hasattr(window.title_bar, "rooms_button")


def test_deshacer_un_borrado_no_se_lleva_los_cuartos_creados_despues(qtbot):
    """Guardar la lista entera y restaurarla borraba todo lo hecho en el
    medio. Se guarda el cuarto y su posicion, y se reinserta ahi."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1)])
    window.select_clip(0)
    window.handle_key_press("1")
    window.room_rail.room_removed.emit("Cocina")
    window.room_rail.room_created.emit("Alberca")
    window.undo()
    assert window.room_selection.active_rooms() == ["Cocina", "Sala", "Alberca"]
    assert window.clips[0].categoria_path == ["Cocina"]


def test_deshacer_un_borrado_le_devuelve_su_tecla(qtbot):
    """El cuarto vuelve a su POSICION, que es lo que le da la tecla."""
    window = _window(qtbot, rooms=("Cocina", "Sala", "Baño 1"))
    window.load_clips([_clip(1)])
    window.room_rail.room_removed.emit("Sala")
    window.undo()
    assert window.room_selection.active_rooms() == ["Cocina", "Sala", "Baño 1"]
    window.select_clip(0)
    window.handle_key_press("2")
    assert window.clips[0].categoria_path == ["Sala"]


def test_un_clip_horizontal_no_infla_la_ventana(qtbot):
    """Bug real de la F2, agravado por la barra de filtros de la F5: el
    calculo del ancho del video asumia que la hoja mide como minimo
    `SHEET_MIN_WIDTH`, pero mide bastante mas. Cada pasada agrandaba la
    ventana, lo que agrandaba el maximo del video, lo que la agrandaba otra
    vez: con un clip horizontal la ventana se inflaba de 1600 a 2653 px.
    """
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window._clip_sizes = {0: (3840, 2160)}
    window.resize(1600, 1000)
    window.show()
    qtbot.waitExposed(window)
    window.select_clip(0)
    qtbot.wait(10)
    assert window.width() == 1600


def test_el_video_horizontal_crece_hasta_donde_puede(qtbot):
    """Con un clip apaisado el video deja de estar limitado por la altura:
    tiene que ocupar lo que la hoja no necesita."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window._clip_sizes = {0: (3840, 2160)}
    window.resize(1600, 1000)
    window.show()
    qtbot.waitExposed(window)
    window.select_clip(0)
    qtbot.wait(10)
    assert window.video_stage.width() > 700


def test_el_clip_vertical_sigue_midiendo_529(qtbot):
    """La medida objetiva de la F2 no se toca."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window._clip_sizes = {0: (2160, 3840)}
    window.resize(1600, 1000)
    window.show()
    qtbot.waitExposed(window)
    window.select_clip(0)
    qtbot.wait(10)
    assert window.video_stage.width() == 529
    assert window.width() == 1600


# --- F6 Task 2: autoplay y arranque al 25% -----------------------------------


def test_cambiar_de_clip_lo_deja_reproduciendo(qtbot):
    """Apretar espacio 128 veces es puro peaje."""
    # a modo clip: el autoplay es del VISOR -- en la hoja el clip se abre
    # pausado a proposito, porque ahi no hay imagen que acompañe al sonido
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1), _clip(2)])
    window.handle_arrow("next")
    assert not window.video_widget.player.is_paused


def test_seleccionar_un_clip_de_la_hoja_tambien_lo_reproduce(qtbot):
    # a modo clip: el autoplay es del VISOR -- en la hoja el clip se abre
    # pausado a proposito, porque ahi no hay imagen que acompañe al sonido
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1), _clip(2)])
    window.video_widget.player.pause()
    window.select_clip(1)
    assert not window.video_widget.player.is_paused


def test_el_primer_clip_del_shooting_tambien_arranca_solo(qtbot):
    """Si `load_clips` fuera la excepcion, el primer clip de cada shooting
    seria el unico donde hay que apretar espacio -- justo el peaje que esta
    fase existe para quitar."""
    # a modo clip: el autoplay es del VISOR -- en la hoja el clip se abre
    # pausado a proposito, porque ahi no hay imagen que acompañe al sonido
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1)])
    assert not window.video_widget.player.is_paused


def test_cada_clip_arranca_al_25_por_ciento(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.select_clip(0)
    assert window.video_widget.player._mpv.start == "25%"


def test_los_tres_caminos_que_abren_un_clip_hacen_lo_mismo(qtbot):
    """Guarda contra deriva: `load_clips`, `select_clip` y `handle_arrow`
    abren clip cada uno por su lado. Si el autoplay se agrega en dos de los
    tres, el tercero queda muerto sin dar ningun sintoma visible."""
    caminos = {
        "load_clips": lambda w: w.load_clips([_clip(1), _clip(2)]),
        "select_clip": lambda w: w.select_clip(1),
        "handle_arrow": lambda w: w.handle_arrow("next"),
    }
    for nombre, abrir in caminos.items():
        # a modo clip: el autoplay es del visor, no de la hoja
        window = _a_modo_clip(_window_with_video(qtbot))
        window.load_clips([_clip(1), _clip(2)])
        # se deja el reproductor en el estado contrario al esperado, para que
        # el test no pueda pasar por lo que hizo la carga inicial
        window.video_widget.player.pause()
        window.video_widget.player._mpv.start = None
        window.video_stage.badges.set_auto(False)

        abrir(window)

        assert window.video_widget.player._mpv.start == "25%", nombre
        assert not window.video_widget.player.is_paused, nombre
        assert not window.video_stage.badges.auto_badge.isHidden(), nombre


def test_el_badge_auto_avisa_que_arranco_solo(qtbot):
    # a modo clip: el autoplay es del VISOR -- en la hoja el clip se abre
    # pausado a proposito, porque ahi no hay imagen que acompañe al sonido
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1)])
    window.select_clip(0)
    assert not window.video_stage.badges.auto_badge.isHidden()


def test_el_badge_auto_se_apaga_al_pausar_a_mano(qtbot):
    """Si sigue prendido con el video pausado, miente."""
    # a modo clip: el autoplay es del VISOR -- en la hoja el clip se abre
    # pausado a proposito, porque ahi no hay imagen que acompañe al sonido
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1)])
    window.select_clip(0)
    window.video_widget.toggle_play()
    window._tick_playhead()
    assert window.video_stage.badges.auto_badge.isHidden()


def test_el_badge_auto_no_vuelve_al_reanudar_a_mano(qtbot):
    """Una vez que tocaste el espacio, la reproduccion ya no es automatica.
    Si el badge volviera, diria 'arranco solo' de algo que arrancaste tu."""
    # a modo clip: el autoplay es del VISOR -- en la hoja el clip se abre
    # pausado a proposito, porque ahi no hay imagen que acompañe al sonido
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1)])
    window.select_clip(0)
    window.video_widget.toggle_play()   # pausa
    window._tick_playhead()
    window.video_widget.toggle_play()   # reanuda a mano
    window._tick_playhead()
    assert window.video_stage.badges.auto_badge.isHidden()


def test_el_badge_auto_vuelve_al_cambiar_de_clip(qtbot):
    # a modo clip: el autoplay es del VISOR -- en la hoja el clip se abre
    # pausado a proposito, porque ahi no hay imagen que acompañe al sonido
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1), _clip(2)])
    window.video_widget.toggle_play()
    window._tick_playhead()
    window.handle_arrow("next")
    assert not window.video_stage.badges.auto_badge.isHidden()


# --- F6 Task 3: velocidad con `J K L` ----------------------------------------


def test_L_acelera_y_cicla(qtbot):
    """La convencion de Premiere: repetir `L` va 1× → 2× → 4× → 1×."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    for esperada in (2.0, 4.0, 1.0):
        window.handle_key_press("l")
        assert window.video_widget.player.speed == esperada


def test_L_tambien_arranca_la_reproduccion(qtbot):
    """Es lo que hace en Premiere y lo que uno espera al apretarla."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.video_widget.player.pause()
    window.handle_key_press("l")
    assert not window.video_widget.player.is_paused


def test_K_frena_de_un_golpe(qtbot):
    """Vuelve a 1× Y pausa, sin importar donde estabas."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("l")
    window.handle_key_press("l")
    window.handle_key_press("k")
    assert window.video_widget.player.speed == 1.0
    assert window.video_widget.player.is_paused
    # y el control tiene que decir lo mismo: dos vistas del mismo dato que se
    # contradicen es el bug que ya aparecio en la tarjeta y la barra de rango
    assert window.video_stage.speed.current() == "1×"


def test_J_no_hace_nada_todavia(qtbot):
    """Reservada para reproducir hacia atras: no se construye, pero tampoco se
    le da otro significado."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("l")
    window.handle_key_press("j")
    assert window.video_widget.player.speed == 2.0


def test_el_control_de_velocidad_refleja_la_tecla(qtbot):
    """Si el segmento no sigue a `L`, el control y el video dicen cosas
    distintas."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("l")
    assert window.video_stage.speed.current() == "2×"


def test_tocar_el_control_se_lo_pide_al_reproductor(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.video_stage.speed.selected.emit("2×")
    assert window.video_widget.player.speed == 2.0


def test_la_velocidad_se_conserva_al_cambiar_de_clip(qtbot):
    """Si volviera a 1× en cada clip, habria que reelegirla 128 veces."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1), _clip(2)])
    window.video_stage.speed.selected.emit("4×")
    window.handle_arrow("next")
    assert window.video_widget.player.speed == 4.0
    assert window.video_stage.speed.current() == "4×"


def test_K_sobre_un_video_ya_pausado_lo_deja_pausado(qtbot):
    """`K` es el freno, no un interruptor: apretarla dos veces no reproduce."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("k")
    window.handle_key_press("k")
    assert window.video_widget.player.is_paused


def test_las_teclas_de_velocidad_sin_clips_no_revientan(qtbot):
    """La app abre sin material: apretar `L` antes de importar nada no puede
    tirar la ventana."""
    window = _window_with_video(qtbot)
    window.handle_key_press("l")
    window.handle_key_press("k")


def test_las_teclas_de_reproduccion_estan_registradas(qtbot):
    """Un test que llama a `handle_key_press` pasa aunque la tecla no exista
    para el usuario: lo que la conecta es `_install_shortcuts`."""
    window = _window_with_video(qtbot)
    registrados = {s.key().toString() for s in window._shortcuts}
    for tecla in ("L", "K"):
        assert tecla in registrados, f"{tecla} se maneja pero no está registrada"


# --- F6 Task 5: `,` y `.` cuadro por cuadro ----------------------------------


def test_coma_y_punto_mueven_un_cuadro(qtbot):
    """Los dos sentidos no usan el mismo mecanismo, y esta medido contra mpv
    real: adelante `frame-step`, atras un seek exacto (ver player.py)."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press(".")
    window.handle_key_press(",")
    comandos = window.video_widget.player._mpv.commands
    assert comandos[-2] == ("frame-step",)
    assert comandos[-1][0] == "seek" and comandos[-1][1] < 0


def test_retroceder_un_cuadro_usa_los_fps_del_clip(qtbot):
    """Si la ventana no le pasara los fps, el paso saldria del default y en un
    clip a 60 fps retroceder saltaria el doble de lo que deberia."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1, fps=59.94)])
    window.handle_key_press(",")
    salto = window.video_widget.player._mpv.commands[-1][1]
    assert salto == pytest.approx(-1 / 59.94)


def test_el_timecode_se_actualiza_al_avanzar_un_cuadro(qtbot):
    """Marcar in/out con precision exige ver el numero moverse: si el
    timecode se quedara donde estaba, el cuadro a cuadro seria a ciegas."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.video_widget.player._mpv.time_pos = 1.0
    window.handle_key_press(".")
    assert window.video_stage.timecode_label.text() != ""
    assert window.video_stage.frame_label.text() == "f 30"   # 1.0 s a 30 fps


def test_avanzar_un_cuadro_apaga_el_badge_auto(qtbot):
    """`.` pausa el video (lo hace mpv solo). Si el badge siguiera prendido
    diria que esta corriendo solo algo que esta detenido."""
    # a modo clip: el autoplay es del VISOR -- en la hoja el clip se abre
    # pausado a proposito, porque ahi no hay imagen que acompañe al sonido
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1)])
    window.handle_key_press(".")
    assert window.video_stage.badges.auto_badge.isHidden()


def test_las_teclas_de_cuadro_sin_clips_no_revientan(qtbot):
    window = _window_with_video(qtbot)
    window.handle_key_press(".")
    window.handle_key_press(",")


def test_las_teclas_de_cuadro_estan_registradas(qtbot):
    """La fila de teclas del video las anuncia: tienen que existir."""
    window = _window_with_video(qtbot)
    registrados = {s.key().toString() for s in window._shortcuts}
    for tecla in (",", "."):
        assert tecla in registrados, f"{tecla} se maneja pero no está registrada"


def test_la_barra_se_entera_de_la_duracion_cuando_mpv_la_reporta(qtbot):
    """Bug real encontrado con material de la FX30 al cerrar la F6: mpv
    reporta la duracion de forma ASINCRONA, y `_update_scrub_bar` corre al
    abrir el clip, cuando todavia no existe. Nadie la volvia a pedir, asi que
    la barra se quedaba en 0 para siempre: sin playhead, sin marcas de tiempo
    y sin zona de rango. En la app real la barra estaba muerta; el arnes lo
    tapaba porque sus datos de ejemplo traen la duracion escrita a mano.
    """
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    assert window.scrub_bar.duration == 0.0        # mpv todavia no la sabe
    window.video_widget.player._mpv.duration = 4.004   # ahora si
    window._tick_playhead()
    assert window.scrub_bar.duration == pytest.approx(4.004)


def test_la_duracion_se_actualiza_al_cambiar_de_clip(qtbot):
    """Y no se queda con la del clip anterior, que dibujaria el playhead en
    el lugar equivocado."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1), _clip(2)])
    window.video_widget.player._mpv.duration = 4.0
    window._tick_playhead()
    window.handle_arrow("next")
    window.video_widget.player._mpv.duration = 12.0
    window._tick_playhead()
    assert window.scrub_bar.duration == pytest.approx(12.0)


def test_todas_las_teclas_que_dibuja_la_interfaz_existen(qtbot):
    """El detector que ya encontro CUATRO atajos anunciados y ausentes, ahora
    tambien sobre los textos nuevos de la F6: la fila de teclas del video y el
    recordatorio de la columna. Un texto que promete una tecla que no hace
    nada es peor que no ponerlo."""
    from clasificador_video.ui.video_stage import KEYS_HINT_TEXT

    window = _window_with_video(qtbot)
    registrados = {s.key().toString() for s in window._shortcuts}
    dibujadas = KEYS_HINT_TEXT + " " + window.tool_column.play_hint.text()
    # como los escribe la interfaz -> como los nombra Qt
    equivalencias = {
        "←": "Left", "→": "Right", ",": ",", ".": ".",
        "L": "L", "K": "K", "espacio": "Space", "F": "F", "esc": "Esc",
    }
    for simbolo, secuencia in equivalencias.items():
        if simbolo in dibujadas:
            assert secuencia in registrados, f"la interfaz dibuja {simbolo} y no existe"


def test_la_fila_de_teclas_anuncia_F_y_esc_ahora_que_existen(qtbot):
    """Hasta la F6 esta guarda exigia lo CONTRARIO --que no aparecieran--,
    porque anunciar una tecla que no hace nada es el bug que este proyecto ya
    tuvo cuatro veces. La F7 construyo el modo solo video, asi que ahora
    tienen que estar: la guarda cambio de lado, no se borro."""
    from clasificador_video.ui.video_stage import KEYS_HINT_TEXT

    window = _window_with_video(qtbot)
    registrados = {s.key().toString() for s in window._shortcuts}
    assert "F" in KEYS_HINT_TEXT and "F" in registrados
    assert "esc" in KEYS_HINT_TEXT and "Esc" in registrados


# --- las teclas sueltas no pueden robarle lo que escribes al buscador --------


def test_una_tecla_suelta_no_actua_mientras_escribes(qtbot):
    """Un `QShortcut` de contexto `WindowShortcut` se resuelve ANTES de
    entregarle la tecla al widget con foco. Sin guarda, escribir "cocina" en
    el buscador de la hoja marcaria in con la `i`, out con la `o`, y un "1"
    asignaria un cuarto -- todo sin que el texto llegue al campo.

    No se pudo comprobar contra el teclado real: los atajos solo se disparan
    con la ventana ACTIVA, y un proceso lanzado desde la terminal no logra
    activarse en macOS. Por eso la guarda se prueba por su efecto.
    """
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1, cuarto=None)])
    window.show()
    qtbot.waitExposed(window)
    window.clip_sheet.search_input.setFocus()
    qtbot.wait(20)

    por_atajo = {s.key().toString(): s for s in window._shortcuts}
    for tecla in ("L", "K", "I", "O", "P", "X", ",", "."):
        por_atajo[tecla].activated.emit()
    # los digitos ya no son atajos (matan el pincel): se prueban por su
    # camino real, el evento de teclado
    from PySide6.QtCore import Qt as _Qt
    qtbot.keyPress(window, _Qt.Key.Key_1)
    qtbot.keyRelease(window, _Qt.Key.Key_1)
    qtbot.wait(20)

    clip = window.clips[0]
    assert clip.categoria_path == [], "un digito asigno cuarto mientras escribias"
    assert clip.flag == "none", "P o X marcaron el clip mientras escribias"
    assert clip.in_frame is None and clip.out_frame is None
    assert window.video_widget.player.speed == 1.0
    assert window.video_widget.player._mpv.commands == []


def test_sin_foco_en_un_campo_las_teclas_si_actuan(qtbot):
    """La guarda no puede apagar los atajos: solo cede cuando escribes."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.show()
    qtbot.waitExposed(window)
    window.clip_sheet.search_input.clearFocus()
    qtbot.wait(20)

    por_atajo = {s.key().toString(): s for s in window._shortcuts}
    por_atajo["L"].activated.emit()
    assert window.video_widget.player.speed == 2.0


def test_los_atajos_con_modificador_no_llevan_guarda(qtbot):
    """`⌘Z`, `⌘E` y compañia no chocan con escribir, y guardarlos haria que
    deshacer dejara de funcionar apenas tocaras el buscador."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.show()
    qtbot.waitExposed(window)
    window.handle_key_press("p")            # algo que deshacer
    window.clip_sheet.search_input.setFocus()
    qtbot.wait(20)

    por_atajo = {s.key().toString(): s for s in window._shortcuts}
    por_atajo["Ctrl+Z"].activated.emit()
    assert window.clips[0].flag == "none", "⌘Z no deshizo por estar escribiendo"


def test_al_abrir_la_app_ninguna_tecla_esta_bloqueada(qtbot):
    """El buscador de la hoja era el primer widget que aceptaba foco, asi que
    se lo quedaba SOLO al abrir. Con las teclas sueltas cediendo el paso
    mientras escribes, eso dejaba muertas P, X, I, O, L, K y los digitos hasta
    que clickearas en otro lado -- la app abria sin teclado."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(20)
    assert not window.escribiendo_texto(), "el foco arranca en un campo de texto"

    por_atajo = {s.key().toString(): s for s in window._shortcuts}
    por_atajo["P"].activated.emit()
    assert window.clips[0].flag == "pick"


def test_al_escribir_los_atajos_de_una_tecla_se_DESACTIVAN(qtbot):
    """No alcanza con que el handler se abstenga: un atajo que se dispara
    CONSUME la tecla, asi que ignorarla dejaria el buscador mudo --ni cambia
    la velocidad ni aparece la letra--. Desactivado no compite, y la tecla
    llega al campo."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.show()
    qtbot.waitExposed(window)
    sueltos = window._atajos_de_tecla_suelta
    assert all(a.isEnabled() for a in sueltos)

    window.clip_sheet.search_input.setFocus()
    qtbot.wait(20)
    assert not any(a.isEnabled() for a in sueltos), "siguen compitiendo con el campo"

    window.clip_sheet.search_input.clearFocus()
    qtbot.wait(20)
    assert all(a.isEnabled() for a in sueltos), "no volvieron al salir del campo"


def test_los_de_modificador_nunca_se_desactivan(qtbot):
    window = _window_with_video(qtbot)
    window.show()
    qtbot.waitExposed(window)
    window.clip_sheet.search_input.setFocus()
    qtbot.wait(20)
    con_modificador = [s for s in window._shortcuts
                       if s not in window._atajos_de_tecla_suelta]
    assert con_modificador and all(s.isEnabled() for s in con_modificador)


def test_el_texto_llega_al_buscador_mientras_esta_enfocado(qtbot):
    """La prueba de que el campo sigue sirviendo para lo suyo."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.show()
    qtbot.waitExposed(window)
    window.clip_sheet.search_input.setFocus()
    qtbot.wait(20)
    qtbot.keyClicks(window.clip_sheet.search_input, "cocina 1")
    assert window.clip_sheet.search_input.text() == "cocina 1"
    assert window.clips[0].categoria_path == []
    assert window.clips[0].in_frame is None


# --- F7 Task 8: `S` -- igual al clip anterior --------------------------------


def test_S_asigna_el_cuarto_del_clip_anterior(qtbot):
    """La tecla mas valiosa de este material: en un recorrido las tomas vienen
    en rachas, y sobre 128 clips convierte ~110 decisiones en confirmaciones."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.handle_key_press("1")          # el primero a Cocina, y avanza
    window.handle_key_press("s")
    assert window.clips[1].categoria_path == ["Cocina"]


def test_S_salta_los_que_quedaron_sin_clasificar(qtbot):
    """Si mirara solo el inmediatamente anterior, la tecla se volveria inutil
    apenas te saltas uno."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window.select_clip(0)
    window.handle_key_press("1")
    window.select_clip(2)                 # el del medio queda sin cuarto
    window.handle_key_press("s")
    assert window.clips[2].categoria_path == ["Cocina"]


def test_S_mira_hacia_atras_en_el_orden_de_rodaje_no_en_la_cola(qtbot):
    """El «anterior» es el de antes en el ROLLO, no el anterior de la cola
    filtrada: en el rodaje las rachas son consecutivas en el tiempo, y un
    filtro puede dejar al lado dos clips de cuartos distintos."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window.select_clip(0)
    window.handle_key_press("2")          # clip 1 -> Sala
    window.select_clip(1)
    window.handle_key_press("1")          # clip 2 -> Cocina
    window.select_clip(2)
    window.handle_key_press("s")
    assert window.clips[2].categoria_path == ["Cocina"]   # el mas cercano


def test_S_sin_ningun_clip_clasificado_antes_no_hace_nada(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("s")
    assert window.clips[0].categoria_path == []


def test_S_sin_clips_no_revienta(qtbot):
    _window(qtbot, rooms=("Cocina",)).handle_key_press("s")


def test_S_copia_el_ultimo_usado_aunque_este_mas_adelante(qtbot):
    """Cambio del 2026-08-20. Este test defendia lo contrario --«el anterior
    es hacia atras»-- y esa regla es la que le daba a Bruno un cuarto viejo:
    con material clasificado de una pasada anterior, «el clip de al lado
    hacia atras» no es el ultimo que usaste.

    Copiar de un clip mas adelante ya no es copiar de uno «que todavia no
    juzgaste»: lo juzgaste tu, hace un segundo, y por eso es el que `S`
    tiene en la mano."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(1)
    window.handle_key_press("1")          # el SEGUNDO a Cocina
    window.select_clip(0)
    window.handle_key_press("s")
    assert window.clips[0].categoria_path == ["Cocina"]


def test_S_no_inventa_cuando_no_hay_de_donde_copiar(qtbot):
    """Lo que el test de arriba SI tenia que defender y se conserva: sin
    ningun cuarto usado y sin nada clasificado atras, `S` no hace nada."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.handle_key_press("s")
    assert window.clips[0].categoria_path == []


def test_S_tambien_avanza(qtbot):
    """Es una asignacion de cuarto como cualquier otra."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window.select_clip(0)
    window.handle_key_press("1")
    window.handle_key_press("s")
    assert window.current_index == 2


def test_S_deja_entrada_en_el_historial(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.handle_key_press("1")
    window.handle_key_press("s")
    assert window.history.entries()[0].etiqueta == "Cocina"


def test_S_se_puede_deshacer(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.handle_key_press("1")
    window.handle_key_press("s")
    window.undo()
    assert window.clips[1].categoria_path == []


def test_la_fila_de_S_del_rail_dice_lo_que_la_tecla_va_a_poner(qtbot):
    """La pista y la tecla salen de la MISMA fuente, o se contradicen.

    Antes decia «a que cuarto aplicaria segun donde estas parado»; desde el
    2026-08-20 `S` es «el ultimo que usaste», asi que la pista lo sigue a el
    y no se apaga al moverte."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window.select_clip(0)
    window.handle_key_press("1")          # clip 1 -> Cocina, y avanza al 2
    assert "Cocina" in window.room_rail.same_row.name_label.full_text()

    window.select_clip(0)                 # me muevo: la pista NO cambia

    assert "Cocina" in window.room_rail.same_row.name_label.full_text()


def test_la_fila_de_S_se_esconde_cuando_no_hay_nada_que_sugerir(qtbot):
    """Recien abierto y sin nada clasificado: la fila no puede ofrecer un
    cuarto que no existe."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    assert window.room_rail.same_row.isHidden()


def test_la_tecla_S_esta_registrada(qtbot):
    window = _window_with_video(qtbot)
    assert "S" in {s.key().toString() for s in window._shortcuts}


# --- F7 Task 9: el cuarto estado, destacado ----------------------------------


def test_shift_p_marca_destacado(qtbot):
    """`reject` → neutral → `pick` → `destacado`: es LA toma del cuarto, la
    que abre la secuencia en el corte final."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("shift+p")
    assert window.clips[0].flag == "destacado"


def test_repetir_shift_p_vuelve_a_neutral(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("shift+p")
    window.handle_key_press("shift+p")
    assert window.clips[0].flag == "none"


def test_shift_p_sobre_un_pick_lo_asciende(qtbot):
    """Sin perder el pick por el camino: destacar es reforzarlo."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("p")
    window.handle_key_press("shift+p")
    assert window.clips[0].flag == "destacado"


def test_P_sobre_un_destacado_lo_baja_a_pick(qtbot):
    """`P` es el escalon de abajo: apretarla sobre un destacado no puede
    dejarlo igual, o la tecla no haria nada visible."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("shift+p")
    window.handle_key_press("p")
    assert window.clips[0].flag == "pick"


def test_destacado_se_puede_deshacer(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("shift+p")
    window.undo()
    assert window.clips[0].flag == "none"


def test_destacado_se_ve_en_todos_lados(qtbot):
    """Si falta en uno, el estado existe a medias y no se puede confiar en
    ninguna de las vistas."""
    # a modo clip: uno de los «todos lados» es el badge sobre el video
    window = _a_modo_clip(_window(qtbot, rooms=("Cocina",)))
    window.load_clips([_clip(1, "Cocina")])
    window.select_clip(0)
    window.handle_key_press("shift+p")
    assert window.clip_sheet.item_widgets[0].plan_de_pintado()["glifo"][0] == "★"
    assert window.tool_column.star_indicator.is_on()
    assert "DESTACADO" in window.video_stage.badges.flag_badge.text()
    assert "solo_destacados" in window.clip_sheet.chips
    assert window.room_rail.leyenda.puntos[0].text() == "1 dest."


def test_el_atajo_de_destacado_esta_registrado(qtbot):
    window = _window_with_video(qtbot)
    assert "Shift+P" in {s.key().toString() for s in window._shortcuts}


# --- F7 Task 10: `P` y `X` vuelven a neutral ---------------------------------


def test_P_sobre_un_pick_lo_devuelve_a_neutral(qtbot):
    """Repetir la tecla vuelve a neutral (DECISIONES.md): eso evita tener una
    tecla de neutral aparte, y menos atajos se aprenden mas rapido."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("p")
    window.handle_key_press("p")
    assert window.clips[0].flag == "none"


def test_X_sobre_un_reject_lo_devuelve_a_neutral(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("x")
    window.handle_key_press("x")
    assert window.clips[0].flag == "none"


def test_P_sobre_un_reject_lo_convierte_en_pick(qtbot):
    """Solo alterna consigo misma: `P` sobre un reject es «ahora es pick»."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("x")
    window.handle_key_press("p")
    assert window.clips[0].flag == "pick"


def test_deshacer_el_regreso_a_neutral(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("p")
    window.handle_key_press("p")
    window.undo()
    assert window.clips[0].flag == "pick"


def test_el_historial_nombra_el_regreso_a_neutral(qtbot):
    """`Pick → Pick` en el historial no diria nada: la fila tiene que decir a
    donde fue el clip, no que tecla apretaste."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("p")
    window.handle_key_press("p")
    assert window.history.entries()[0].etiqueta == "Sin marcar"


# --- F7 Task 11: la paleta `⏎` -----------------------------------------------


def test_enter_abre_la_paleta(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window._on_enter()
    assert not window.room_palette.isHidden()


def test_enter_NO_abre_la_paleta_si_el_foco_esta_en_el_rail(qtbot):
    """Con una fila enfocada, `⏎` renombra ese cuarto. Un QShortcut normal se
    dispara sin importar quien tiene el foco y se lo robaria: renombrar
    dejaria de funcionar y nadie sabria por que."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.show()
    qtbot.waitExposed(window)
    window.room_rail.focus_rooms()
    qtbot.wait(20)
    window._on_enter()
    assert window.room_palette.isHidden()


def test_enter_NO_abre_la_paleta_mientras_escribes_en_el_buscador(qtbot):
    """En un campo de texto `⏎` es confirmar lo que escribiste."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.show()
    qtbot.waitExposed(window)
    window.clip_sheet.search_input.setFocus()
    qtbot.wait(20)
    window._on_enter()
    assert window.room_palette.isHidden()


def test_la_paleta_asigna_el_cuarto_elegido(qtbot):
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.room_palette.room_chosen.emit("Sala")
    assert window.clips[0].categoria_path == ["Sala"]


def test_la_paleta_crea_el_cuarto_y_lo_asigna_de_una(qtbot):
    """Crear y volver a apuntar es dos pasos para una sola intencion."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.select_clip(0)
    window.room_palette.room_created.emit("Alberca")
    assert window.room_selection.active_rooms() == ["Cocina", "Alberca"]
    assert window.clips[0].categoria_path == ["Alberca"]


def test_lo_que_asigna_la_paleta_tambien_avanza_y_se_deshace(qtbot):
    """Es una asignacion de cuarto como cualquier otra: mismo camino que los
    digitos y que `S`."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window.select_clip(0)
    window.room_palette.room_chosen.emit("Sala")
    assert window.current_index == 1
    window.undo()
    assert window.clips[0].categoria_path == []


def test_la_paleta_sabe_a_cuantos_clips_va(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 8)])
    window._on_selection_changed([0, 1, 2, 3])
    window._on_enter()
    assert "4 clips" in window.room_palette.alcance_label.text()


def test_la_paleta_muestra_los_cuartos_con_sus_conteos(qtbot):
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1, "Cocina"), _clip(2, "Cocina")])
    window._on_enter()
    assert window.room_palette.opciones_visibles() == ["Cocina", "Sala"]
    assert window.room_palette.filas_visibles()[0].count_label.text() == "2"


def test_el_enter_esta_registrado(qtbot):
    window = _window_with_video(qtbot)
    assert "Return" in {s.key().toString() for s in window._shortcuts}


# --- F7 Task 12: `F` -- solo video -------------------------------------------


def test_F_esconde_todo_menos_el_video(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("f")
    for panel in (window.room_rail, window.tool_column, window.clip_sheet,
                  window.title_bar, window.status_bar):
        assert panel.isHidden(), panel.objectName()
    assert not window.video_stage.isHidden()


def test_F_otra_vez_devuelve_todo(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("f")
    window.handle_key_press("f")
    assert not window.room_rail.isHidden()
    assert not window.clip_sheet.isHidden()


def test_en_solo_video_el_video_usa_todo_el_ancho_que_puede(qtbot):
    """Si escondiera los paneles sin recalcular, quedaria el mismo video con
    franjas negras al costado -- justo lo que este rediseño evita."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    window.show()
    qtbot.waitExposed(window)
    window.load_clips([_clip(1)])
    qtbot.wait(20)
    antes = window.video_stage.width()
    window.handle_key_press("f")
    qtbot.wait(20)
    assert window.video_stage.width() > antes


def test_en_solo_video_las_teclas_siguen_funcionando(qtbot):
    """Es una vista, no un modo aparte: sigues clasificando sin ver la hoja."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.handle_key_press("f")
    window.handle_key_press("p")
    assert window.clips[0].flag == "pick"
    window.handle_key_press("1")
    assert window.clips[0].categoria_path == ["Cocina"]


def test_esc_sale_de_solo_video(qtbot):
    """`esc` es la salida universal: si solo saliera con `F`, quien entro sin
    querer no sabe como volver."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("f")
    window.handle_key_press("escape")
    assert not window.room_rail.isHidden()


def test_esc_sin_estar_en_solo_video_no_hace_nada(qtbot):
    # a modo clip: es la rama que el nombre promete. Arrancando en la hoja,
    # `esc` no entraba a ninguna de las dos ramas y el test pasaba sin
    # ejercitar nada.
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1)])
    window.handle_key_press("escape")
    assert not window.room_rail.isHidden()
    assert not window._solo_video


def test_las_teclas_de_solo_video_estan_registradas(qtbot):
    window = _window_with_video(qtbot)
    registrados = {s.key().toString() for s in window._shortcuts}
    assert "F" in registrados
    assert "Esc" in registrados


def test_en_solo_video_tambien_se_usa_el_alto_de_las_barras_escondidas(qtbot):
    """La barra de titulo y la de estado ya no estan: seguir restando su alto
    dejaba el video mas chico de lo que cabe. Con un clip vertical, que es
    donde el alto manda, eso son 33 px de ancho perdidos."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    window.show()
    qtbot.waitExposed(window)
    window.load_clips([_clip(1)])
    window._clip_sizes = {0: (2160, 3840)}
    window.select_clip(0)
    qtbot.wait(20)
    window.handle_key_press("f")
    qtbot.wait(20)
    assert window.video_stage.height() == 1000
    assert window.video_stage.width() == VideoStage.width_for(1000, 9 / 16)


# --- F8 Task 15: el modo hoja ------------------------------------------------


def test_tab_alterna_entre_los_dos_modos(qtbot):
    # se arranca cruzando al visor: desde la F7 la app abre en la hoja, y
    # lo que este test comprueba es que `⇥` va y vuelve
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1)])
    window.handle_key_press("tab")
    assert window.video_stage.isHidden()
    assert not window.clip_sheet.isHidden()
    window.handle_key_press("tab")
    assert not window.video_stage.isHidden()


def test_en_modo_hoja_la_columna_de_herramientas_se_va_con_el_video(qtbot):
    """La columna es del visor: sin video no tiene de que ser el estado."""
    # se arranca cruzando al visor: la app abre en la hoja desde la F7
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(1)])
    window.handle_key_press("tab")
    assert window.tool_column.isHidden()
    assert not window.room_rail.isHidden()      # el rail SI se queda


def test_el_clip_actual_sobrevive_el_cruce(qtbot):
    """`⇥` lleva SIEMPRE al clip actual, en los dos sentidos."""
    # desde el visor: el orden importa, porque llevar al clip actual es lo
    # que corre al ENTRAR a la hoja. Arrancando en la hoja el primer `⇥`
    # salia, y el test comprobaba los dos sentidos al reves.
    window = _a_modo_clip(_window_with_video(qtbot))
    window.load_clips([_clip(i) for i in range(1, 6)])
    window.select_clip(3)
    window.handle_key_press("tab")
    assert window.clip_sheet.current_index() == 3
    window.handle_key_press("tab")
    assert window.current_index == 3


def test_la_seleccion_sobrevive_el_cruce(qtbot):
    """Es lo que Lightroom hace mal y no hay razon para copiarlo."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(i) for i in range(1, 8)])
    window._on_selection_changed([1, 2, 3])
    window.handle_key_press("tab")
    window.handle_key_press("tab")
    assert window.selected_indices == [1, 2, 3]


def test_esc_sale_primero_de_solo_video_y_despues_a_la_hoja(qtbot):
    """`esc` es la salida universal y ya la usaba solo video (F7): tiene que
    deshacer una capa por vez, no saltarse una."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("f")
    window.handle_key_press("escape")
    assert not window.room_rail.isHidden()          # salio de solo video
    assert not window.video_stage.isHidden()        # sigue en modo clip
    window.handle_key_press("escape")
    assert window.video_stage.isHidden()            # ahora si, a la hoja


def test_doble_click_en_una_tarjeta_abre_ese_clip(qtbot):
    """El gesto de Grid → Loupe."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1), _clip(2)])
    window.handle_key_press("tab")
    window.clip_sheet.clip_activated.emit(1)
    assert window.current_index == 1
    assert not window.video_stage.isHidden()


def test_en_modo_hoja_las_teclas_siguen_clasificando(qtbot):
    """La hoja no es un visor aparte: sigues marcando y asignando."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.handle_key_press("tab")
    window.handle_key_press("1")
    assert window.clips[0].categoria_path == ["Cocina"]


def test_mas_y_menos_llegan_a_la_hoja(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(i) for i in range(1, 13)])
    window.show()
    qtbot.waitExposed(window)
    paso = window.clip_sheet._paso
    window.handle_key_press("+")
    assert window.clip_sheet._paso > paso
    window.handle_key_press("-")
    assert window.clip_sheet._paso == paso


def test_las_teclas_del_modo_hoja_estan_registradas(qtbot):
    window = _window_with_video(qtbot)
    registrados = {s.key().toString() for s in window._shortcuts}
    for tecla in ("Tab", "+", "-"):
        assert tecla in registrados, f"{tecla} se maneja pero no está registrada"


# --- F8 Task 18: el pincel de cuarto -----------------------------------------
#
# Los cinco detalles de los que depende que sirva (DECISIONES.md). No son
# adornos: la idea sin ellos no funciona.


def test_1_sin_tecla_abajo_arrastrar_no_pinta(qtbot):
    """El pincel solo existe mientras la tecla esta abajo, asi que no se puede
    disparar por accidente: sin tecla, arrastrar es marquesina."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.pintar(0)                    # sin empezar_pincelada
    assert window.clips[0].categoria_path == []


def test_2_el_pincel_sabe_que_cuarto_lleva_cargado(qtbot):
    """El cursor lleva su carga visible: nunca pintas sin saber que pintas."""
    window = _window_with_video(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1)])
    window.empezar_pincelada("2")
    assert window.pincel_cargado() == ("2", "Sala")
    window.terminar_pincelada()
    assert window.pincel_cargado() is None


def test_3_la_tarjeta_se_tiñe_al_tocarla(qtbot):
    """El rastro de la pincelada se ve en el momento, no al soltar."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.empezar_pincelada("1")
    window.pintar(0)
    assert window.clips[0].categoria_path == ["Cocina"]
    assert window.clip_sheet.item_widgets[0].clip.room_color is not None


def test_4_la_pincelada_entera_se_deshace_de_una(qtbot):
    """Si deshiciera clip por clip, el pincel seria una trampa: un gesto
    rapido que cuesta seis acciones revertir."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 7)])
    window.empezar_pincelada("1")
    for indice in range(6):
        window.pintar(indice)
    window.terminar_pincelada()
    assert len(window.history.entries()) == 1
    window.undo()
    assert all(c.categoria_path == [] for c in window.clips)


def test_4b_la_entrada_dice_cuantos_clips_pinto(qtbot):
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 5)])
    window.empezar_pincelada("1")
    for indice in range(3):
        window.pintar(indice)
    window.terminar_pincelada()
    entrada = window.history.entries()[0]
    assert entrada.etiqueta == "Cocina"
    assert "3 clips" in entrada.detalle


def test_5_no_se_reagrupa_mientras_pintas(qtbot):
    """Si saltaran de grupo mientras pintas, la grilla se reacomodaria bajo el
    cursor y seguirias pintando sobre otra cosa. Medido en el spike: sin esto
    la tarjeta bajo el cursor cambia."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 5)])
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(20)
    orden = window.clip_sheet.orden_visual()
    window.empezar_pincelada("1")
    window.pintar(0)
    window.pintar(1)
    qtbot.wait(20)
    assert window.clip_sheet.orden_visual() == orden, "se reagrupo mientras pintabas"
    window.terminar_pincelada()
    qtbot.wait(20)
    assert window.clip_sheet.orden_visual() != orden, "no se reagrupo al soltar"


def test_pintar_el_mismo_clip_dos_veces_no_lo_duplica(qtbot):
    """Arrastrando se pasa varias veces por la misma tarjeta: la entrada de
    historial tiene que contarlo una vez."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.empezar_pincelada("1")
    window.pintar(0)
    window.pintar(0)
    window.pintar(0)
    window.terminar_pincelada()
    # con un solo clip el historial usa el formato del mockup, `→ clip 001`
    assert window.history.entries()[0].detalle == "→ clip 001"


def test_una_pincelada_vacia_no_deja_entrada(qtbot):
    """Apretar la tecla y soltarla sin tocar ninguna tarjeta no hizo nada:
    una fila de historial que no cambio nada es basura que estorba."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.empezar_pincelada("1")
    window.terminar_pincelada()
    assert window.history.entries() == []


def test_el_pincel_con_una_tecla_sin_cuarto_no_hace_nada(qtbot):
    """Con dos cuartos, mantener `7` no carga nada: pintar con un pincel vacio
    borraria el cuarto de lo que toques."""
    window = _window_with_video(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1)])
    window.empezar_pincelada("7")
    assert window.pincel_cargado() is None
    window.pintar(0)
    assert window.clips[0].categoria_path == []


def test_mantener_una_tecla_de_cuarto_carga_el_pincel(qtbot):
    """El gesto: `1`-`9` sostenida carga, y soltarla cierra la pincelada. Un
    `QShortcut` solo avisa de la pulsacion, nunca de que se solto -- por eso
    la ventana mira los eventos de teclado."""
    from PySide6.QtCore import Qt as _Qt

    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.show()
    qtbot.waitExposed(window)
    qtbot.keyPress(window, _Qt.Key.Key_1)
    assert window.pincel_cargado() == ("1", "Cocina")
    qtbot.keyRelease(window, _Qt.Key.Key_1)
    assert window.pincel_cargado() is None


def test_una_tecla_repetida_por_el_sistema_no_reinicia_la_pincelada(qtbot):
    """Mantener una tecla dispara auto-repeticion: si cada repeticion empezara
    una pincelada nueva, cada tarjeta seria su propia entrada de historial y
    `⌘Z` deshacería una sola."""
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtGui import QKeyEvent

    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 5)])
    window.show()
    qtbot.waitExposed(window)
    qtbot.keyPress(window, _Qt.Key.Key_1)
    window.pintar(0)
    for _ in range(5):      # el sistema repite mientras la sostienes
        window.keyPressEvent(QKeyEvent(
            QKeyEvent.Type.KeyPress, _Qt.Key.Key_1, _Qt.NoModifier, "1", True
        ))
    window.pintar(1)
    qtbot.keyRelease(window, _Qt.Key.Key_1)
    assert len(window.history.entries()) == 1
    assert window.history.entries()[0].detalle == "→ 2 clips"


def test_un_toque_de_tecla_asigna_y_avanza_como_siempre(qtbot):
    """Soltar sin haber pintado nada es un TOQUE: asigna al clip actual y
    avanza, que es lo que `1`-`9` hacen desde la F3. Una sola tecla cubre los
    dos gestos sin aprender nada nuevo."""
    from PySide6.QtCore import Qt as _Qt

    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.show()
    qtbot.waitExposed(window)
    qtbot.keyPress(window, _Qt.Key.Key_1)
    qtbot.keyRelease(window, _Qt.Key.Key_1)
    assert window.clips[0].categoria_path == ["Cocina"]
    assert window.current_index == 1


def test_los_digitos_NO_pueden_ser_atajos(qtbot):
    """Guarda contra reponerlos: un `QShortcut` consume la tecla y nunca avisa
    de que se solto, asi que con los digitos registrados el pincel no se
    armaria nunca. Y no se veria en los tests --un atajo solo se dispara con
    la ventana ACTIVA, y en pruebas la tecla llega igual al widget--, que es
    como este bug se colo la primera vez."""
    window = _window_with_video(qtbot)
    registrados = {s.key().toString() for s in window._shortcuts}
    for digito in "123456789":
        assert digito not in registrados, f"{digito} como atajo mata el pincel"


def test_todas_las_teclas_de_la_barra_de_seleccion_existen(qtbot):
    """Misma guarda que la fila de teclas del video: una barra que promete
    `⇧P` cuando `⇧P` no hace nada es peor que no ponerla."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 6)])
    window._on_selection_changed([1, 2, 3])
    texto = window.clip_sheet.batch_bar.hints_text()
    registrados = {s.key().toString() for s in window._shortcuts}
    equivalencias = {"⏎": "Return", "P": "P", "X": "X", "⇧P": "Shift+P",
                     "⌘Z": "Ctrl+Z", "esc": "Esc"}
    for simbolo, secuencia in equivalencias.items():
        if simbolo in texto:
            assert secuencia in registrados, f"la barra promete {simbolo}"
    # los digitos no son atajos (matarian el pincel): se comprueban por su
    # camino real
    assert window.clips[1].categoria_path == []


# --- la orientacion del manifest sale del material (F9) -----------------


def _exportar(window, monkeypatch, out):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("clasificador_video.ui.main_window.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(out), ""))
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: QMessageBox.Ok)
    window.title_bar.export_button.click()
    import json
    return json.loads(out.read_text())


def test_el_manifest_declara_vertical_si_el_material_es_vertical(qtbot, monkeypatch, tmp_path):
    """Era el ultimo renglon vivo de la lista de ejecucion: hasta la F9
    esto decia `"horizontal"` escrito a mano, y el material de Bruno es
    mayoria vertical -- Premiere armaba la secuencia con la forma
    equivocada."""
    window = _window_with_video(qtbot)
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=59.94),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Sala"], fps=59.94),
    ])
    window._clip_sizes = {0: (2160, 3840), 1: (2160, 3840)}

    assert _exportar(window, monkeypatch, tmp_path / "m.json")["orientacion"] == "vertical"


def test_el_manifest_declara_horizontal_si_el_material_es_horizontal(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=59.94)])
    window._clip_sizes = {0: (3840, 2160)}

    assert _exportar(window, monkeypatch, tmp_path / "m.json")["orientacion"] == "horizontal"


def test_sin_tamanos_el_manifest_conserva_el_default_de_siempre(qtbot, monkeypatch, tmp_path):
    """Sesion restaurada de disco: no se volvio a correr ffprobe."""
    window = _window_with_video(qtbot)
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=59.94)])
    window._clip_sizes = {}

    assert _exportar(window, monkeypatch, tmp_path / "m.json")["orientacion"] == "horizontal"


# --- proxies: emparejar, validar y usar (F9) ---------------------------
#
# El proxy real de Bruno mide 1280x720 y calza cuadro a cuadro con el
# original (medido en la task 0 del plan de la F9). Estos dobles imitan
# eso: el original vertical de _ProbeVertical (2160x3840, 29.97, 540
# cuadros) y un proxy con LOS MISMOS cuadros y fps.


class _ProbeConProxy:
    """Devuelve datos de original o de proxy segun el nombre del archivo,
    para poder importar los dos con un solo doble."""

    def __init__(self, fps_proxy=29.97, cuadros_proxy=540, proxy_vertical=True):
        self.fps_proxy = fps_proxy
        self.cuadros_proxy = cuadros_proxy
        self.proxy_vertical = proxy_vertical

    def __call__(self, path):
        if path.stem.endswith("S03"):
            ancho, alto = (720, 1280) if self.proxy_vertical else (1280, 720)
            return {"width": ancho, "height": alto, "fps": self.fps_proxy,
                    "has_audio": True, "duration_frames": self.cuadros_proxy,
                    "rotation": 90}
        return {"width": 2160, "height": 3840, "fps": 29.97,
                "has_audio": True, "duration_frames": 540, "rotation": 90}


def _importar_con_proxy(window, monkeypatch, tmp_path, con_proxy=True,
                        parchear_miniaturas=True, enganchar=True):
    if parchear_miniaturas:
        monkeypatch.setattr(
            "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
        )
    carpeta = tmp_path / "tarjeta" / "clips"
    carpeta.mkdir(parents=True)
    (carpeta / "C0001.MP4").touch()
    if con_proxy:
        proxies = tmp_path / "tarjeta" / "proxy"
        proxies.mkdir()
        (proxies / "C0001S03.MP4").touch()
    window.importar_rutas([carpeta])
    # y se enganchan A MANO, que es el unico camino desde que Bruno lo
    # pidio: importar ya no busca proxies solo.
    if con_proxy and enganchar:
        _enganchar_a_mano(window, monkeypatch, tmp_path)
    return carpeta


def _enganchar_a_mano(window, monkeypatch, tmp_path, nombre="C0001S03.MP4"):
    """El camino nuevo: los proxies se enganchan a mano, eligiendo el de un
    clip. Antes esto pasaba solo al importar."""
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(tmp_path / "tarjeta" / "proxy" / nombre), ""),
    )
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.information",
                        lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: QMessageBox.Ok)
    window.adjuntar_proxies()


def _esperar_a_los_proxies(window):
    from PySide6.QtWidgets import QApplication
    window._thread_pool.waitForDone(5000)
    QApplication.processEvents()


def test_importar_engancha_el_proxy_de_la_carpeta_hermana(qtbot, monkeypatch, tmp_path):
    """De punta a punta: buscar, emparejar, sondear y validar. Hasta la F9
    `ruta_proxy` salia SIEMPRE en null y Premiere nunca recibia un proxy,
    aunque el plugin ya sabia engancharlo."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)

    assert window.clips[0].ruta_proxy is not None
    assert window.clips[0].ruta_proxy.name == "C0001S03.MP4"
    assert window._proxy_sizes[0] == (720, 1280)


def test_un_clip_sin_proxy_queda_en_none(qtbot, monkeypatch, tmp_path):
    """El caso normal del dron -- no es un error."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path, con_proxy=False)
    _esperar_a_los_proxies(window)

    assert window.clips[0].ruta_proxy is None


def test_un_proxy_con_otro_fps_se_descarta(qtbot, monkeypatch, tmp_path):
    """Si no calza cuadro a cuadro, el in/out cae corrido -- y Premiere lo
    engancharia igual, sin avisar."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy(fps_proxy=25.0))
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)

    assert window.clips[0].ruta_proxy is None


def test_un_proxy_con_otra_cantidad_de_cuadros_se_descarta(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy(cuadros_proxy=530))
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)

    assert window.clips[0].ruta_proxy is None


def test_un_proxy_acostado_se_descarta(qtbot, monkeypatch, tmp_path):
    """Un proxy sin su matriz de rotacion se veria acostado contra un
    original vertical."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy(proxy_vertical=False))
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)

    assert window.clips[0].ruta_proxy is None


def test_el_tamano_del_clip_lo_sigue_mandando_el_original(qtbot, monkeypatch, tmp_path):
    """Si el layout empezara a salir del proxy, la pantalla cambiaria de
    forma sola y la barra de estado mentiria sobre la resolucion."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)

    assert window._clip_sizes[0] == (2160, 3840)
    assert window.aspect_ratio_for(0) == 2160 / 3840


def test_un_resultado_de_una_importacion_vieja_se_ignora(qtbot, monkeypatch, tmp_path):
    """Misma guarda que las miniaturas: importar de nuevo invalida lo que
    quedo corriendo de la importacion anterior."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)
    window.clips[0].ruta_proxy = None

    window._on_proxy_sondeado(
        window._proxy_generation - 1, 0,
        {"width": 720, "height": 1280, "fps": 29.97, "duration_frames": 540},
    )

    assert window.clips[0].ruta_proxy is None


def test_abrir_un_clip_antes_de_que_su_proxy_valide_usa_el_original(qtbot, monkeypatch, tmp_path):
    """El sondeo es asincrono (26.7 ms por archivo, 3.42 s en 128 clips):
    Bruno empieza a trabajar antes de que terminen."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    abiertos = []
    monkeypatch.setattr(window.video_widget, "open_clip", lambda p: abiertos.append(p))
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    window.select_clip(0)

    assert abiertos and abiertos[-1].name == "C0001.MP4"


# --- reproducir el proxy (F9) ------------------------------------------
#
# Medido en la task 0 del plan contra el material real: un cuadro atras
# cuesta 530 ms sobre el original (4K HEVC 10-bit a 268 Mbps) y 22 ms
# sobre el proxy. No era la app: era el material.


def test_se_reproduce_el_proxy_cuando_valido(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    abiertos = []
    monkeypatch.setattr(window.video_widget, "open_clip", lambda p: abiertos.append(p))
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)
    window.select_clip(0)

    assert abiertos[-1].name == "C0001S03.MP4"


def test_sin_proxy_se_reproduce_el_original(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    abiertos = []
    monkeypatch.setattr(window.video_widget, "open_clip", lambda p: abiertos.append(p))
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path, con_proxy=False)
    _esperar_a_los_proxies(window)
    window.select_clip(0)

    assert abiertos[-1].name == "C0001.MP4"


def test_si_el_proxy_ya_no_esta_se_cae_al_original(qtbot, monkeypatch, tmp_path):
    """Sesion restaurada de disco con la tarjeta desmontada, o el proxy
    borrado despues de importar: mpv abriria la nada."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    abiertos = []
    monkeypatch.setattr(window.video_widget, "open_clip", lambda p: abiertos.append(p))
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)
    window.clips[0].ruta_proxy.unlink()
    window.select_clip(0)

    assert abiertos[-1].name == "C0001.MP4"


def test_el_manifest_no_cruza_el_original_con_el_proxy(qtbot, monkeypatch, tmp_path):
    """Si se cruzan, Premiere arma el proyecto con el material de 720p y
    nadie lo nota hasta exportar."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)
    window._asignar_cuarto(["Sala"])

    saved = _exportar(window, monkeypatch, tmp_path / "m.json")

    assert saved["clips"][0]["ruta"].endswith("C0001.MP4")
    assert saved["clips"][0]["ruta_proxy"].endswith("C0001S03.MP4")


def test_el_badge_de_proxy_aparece_cuando_se_esta_viendo_el_proxy(qtbot, monkeypatch, tmp_path):
    # a modo clip: el badge de proxy vive sobre el video, y en la hoja los
    # overlays no se refrescan
    window = _a_modo_clip(_window_with_video(qtbot, cache_root=tmp_path / "cache"))
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)
    window.select_clip(0)

    assert window.video_stage.badges.proxy_badge.text() == "PROXY 720P"


def test_el_badge_no_aparece_si_se_esta_viendo_el_original(qtbot, monkeypatch, tmp_path):
    """El badge dice QUE ESTAS VIENDO. Si el proxy ya no esta en disco se
    reproduce el original, y entonces el badge no puede seguir prendido."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)
    window.clips[0].ruta_proxy.unlink()
    window.select_clip(0)

    assert window.video_stage.badges.proxy_badge.isHidden()


def test_el_contador_de_proxies_se_llena_al_importar(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)

    assert window.status_bar.proxy_label.text() == "proxies 720p · 1/1"


def test_sin_proxies_la_barra_lo_dice(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path, con_proxy=False)
    _esperar_a_los_proxies(window)

    assert window.status_bar.proxy_label.text() == "sin proxies"


# --- switch Clip | Hoja en la barra de titulo (F10) --------------------


def test_el_switch_de_la_barra_sigue_al_modo(qtbot):
    """Una sola vista del mismo estado: alternar con ⇥ tiene que dejar el
    switch como corresponde, sin un segundo «en que modo estoy»."""
    window = _window(qtbot)
    # arranca en «Hoja» desde la F7: el switch tiene que nacer siguiendo al
    # modo real, no puesto en «Clip» de fabrica
    assert window.title_bar.mode_switch.current() == "Hoja"
    window.alternar_modo_hoja()
    assert window.title_bar.mode_switch.current() == "Clip"
    window.alternar_modo_hoja()
    assert window.title_bar.mode_switch.current() == "Hoja"


def test_clickear_el_switch_cambia_de_modo(qtbot):
    window = _window(qtbot)
    window.title_bar.mode_switch.buttons[1].click()
    assert window._modo_hoja
    window.title_bar.mode_switch.buttons[0].click()
    assert not window._modo_hoja


def test_el_switch_no_le_quita_ancho_al_video(qtbot):
    """Un minimo de layout se propaga hasta la ventana. Los chips de filtro
    ya empujaron el minimo de la hoja de 520 a 591 px en la F7."""
    window = _window(qtbot)
    window.resize(1150, 800)
    window.show()
    assert window.title_bar.minimumSizeHint().width() <= 1150


def test_al_entrar_a_la_hoja_la_barra_resume_el_shooting(qtbot):
    # se arranca en el visor para poder ENTRAR a la hoja, que es lo que el
    # test mide: desde la F7 la app ya abre en la hoja
    window = _a_modo_clip(_window(qtbot))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window._clip_sizes = {0: (2160, 3840), 1: (2160, 3840), 2: (3840, 2160)}

    window.alternar_modo_hoja()
    assert window.status_bar.clip_label.text() == "3 clips · 2 verticales · 1 horizontales"

    window.alternar_modo_hoja()
    assert "C0001.MP4" in window.status_bar.clip_label.text()


# --- transicion de la tarjeta al visor (F10) ---------------------------


def test_volver_al_visor_anima_la_tarjeta(qtbot):
    """`DECISIONES.md`: la tarjeta crece hasta la posicion del visor,
    medio segundo que evita el «¿donde estaba?» en cada cruce."""
    # Desde el visor. Arrancando en la hoja los dos comentarios quedaban
    # invertidos --el primer `⇥` iba AL visor y el segundo a la hoja-- y el
    # test pasaba porque la animacion de medio segundo de la primera
    # llamada seguia viva, no porque la transicion al visor funcionara.
    window = _a_modo_clip(_window(qtbot))
    window.load_clips([_clip(i) for i in range(1, 6)])
    window.alternar_modo_hoja()          # a la hoja
    qtbot.wait(10)
    assert not window.transicion.corriendo(), "entrar a la hoja no anima"

    window.alternar_modo_hoja()          # y de vuelta al visor
    assert window.transicion.corriendo()


def test_entrar_a_la_hoja_no_anima(qtbot):
    """La transicion es de la tarjeta AL visor. En el otro sentido no hay
    tarjeta de donde salir, y `DECISIONES.md` no la pide."""
    # al visor primero: hay que estar fuera de la hoja para poder entrar
    window = _a_modo_clip(_window(qtbot))
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(i) for i in range(1, 6)])

    window.alternar_modo_hoja()
    assert not window.transicion.corriendo()


def test_sin_clips_el_cruce_no_truena(qtbot):
    window = _window(qtbot)
    window.resize(1600, 1000)
    window.show()
    window.alternar_modo_hoja()
    window.alternar_modo_hoja()
    assert not window.transicion.corriendo()


def test_entrar_a_la_hoja_lleva_al_clip_actual(qtbot):
    """Con 128 clips y el actual en el 87, la hoja se abria en el 117."""
    # al visor primero: hay que estar fuera de la hoja para poder entrar
    window = _a_modo_clip(_window(qtbot))
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(i) for i in range(1, 129)])
    window.select_clip(86)
    qtbot.wait(10)

    window.alternar_modo_hoja()
    qtbot.wait(10)

    from PySide6.QtCore import QRect
    tarjeta = window.clip_sheet.item_widgets[86]
    viewport = window.clip_sheet._scroll.viewport()
    arriba = tarjeta.mapTo(viewport, tarjeta.rect().topLeft())
    assert viewport.rect().intersects(QRect(arriba, tarjeta.size()))


@pytest.mark.parametrize("indice", [0, 12, 32, 60, 86, 100, 127])
def test_entrar_a_la_hoja_lleva_al_clip_actual_este_donde_este(qtbot, indice):
    """El de arriba probaba UN solo clip -- y pasaba por casualidad.

    Al cruzar, el visor se esconde y la hoja se ensancha de 376 px a 1398,
    de dos columnas a siete. Pero Qt no re-acomoda en el acto: postea el
    pedido y lo atiende despues. `centrar_en` media antes de eso, sobre la
    hoja angosta de 7117 px de alto, y mandaba el scroll a una posicion de
    un contenido que estaba por dejar de existir. Al re-acomodarse a 2262 px
    ese scroll quedaba recortado al maximo: la hoja se abria en el FINAL.

    Con el clip 87 de 128 eso se veia bien de pura coincidencia --el final
    de la hoja es justo donde cae--, asi que el test de arriba pasaba. De 32
    posiciones medidas, 17 NO mostraban el clip. Este barre la hoja entera
    para que la coincidencia no vuelva a tapar el bug.
    """
    window = _a_modo_clip(_window(qtbot))
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(i) for i in range(1, 129)])
    window.select_clip(indice)
    qtbot.wait(10)

    window.alternar_modo_hoja()
    qtbot.wait(10)

    from PySide6.QtCore import QRect
    tarjeta = window.clip_sheet.item_widgets[indice]
    viewport = window.clip_sheet._scroll.viewport()
    arriba = tarjeta.mapTo(viewport, tarjeta.rect().topLeft())
    assert viewport.rect().intersects(QRect(arriba, tarjeta.size())), (
        f"el clip {indice} no se ve al entrar a la hoja"
    )


# --- solo video y modo hoja no pueden convivir (auditoria F10) ---------
#
# Los dos esconden paneles, y nadie impedia combinarlos: `⇥` y luego `F`
# --dos teclas que la app anuncia-- dejaban la ventana COMPLETAMENTE
# VACIA. La hoja esconde el video; solo video esconde la hoja; juntos no
# queda nada que ver.


def _paneles_visibles(window):
    return [
        nombre for nombre in
        ("title_bar", "room_rail", "tool_column", "clip_sheet", "status_bar", "video_stage")
        if not getattr(window, nombre).isHidden()
    ]


def test_solo_video_desde_la_hoja_no_deja_la_ventana_vacia(qtbot):
    window = _window(qtbot)
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(1), _clip(2)])
    # sin `alternar_modo_hoja`: la ventana YA arranca en la hoja desde la
    # F7, y llamarlo aqui la sacaba -- la rama que este test cuida, la que
    # impide que `⇥`+`F` deje la ventana en negro, no llegaba a correr y la
    # asercion pasaba por trivialidad.
    assert window._modo_hoja

    window.alternar_solo_video()

    assert _paneles_visibles(window), "la ventana quedo sin un solo panel visible"
    assert "video_stage" in _paneles_visibles(window)
    assert not window._modo_hoja, "solo video sale de la hoja: sin video no hay nada que dejar solo"


def test_la_hoja_desde_solo_video_no_deja_la_ventana_vacia(qtbot):
    window = _window(qtbot)
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(1), _clip(2)])
    window.alternar_solo_video()

    window.alternar_modo_hoja()

    assert "clip_sheet" in _paneles_visibles(window)
    assert not window._solo_video, "entrar a la hoja devuelve los paneles"


def test_los_dos_modos_siguen_funcionando_por_separado(qtbot):
    """El arreglo no puede romper cada modo por su cuenta."""
    window = _window(qtbot)
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(1), _clip(2)])

    window.alternar_solo_video()
    assert _paneles_visibles(window) == ["video_stage"]
    window.alternar_solo_video()
    assert "clip_sheet" in _paneles_visibles(window)

    window.alternar_modo_hoja()
    assert "video_stage" not in _paneles_visibles(window)
    window.alternar_modo_hoja()
    assert "video_stage" in _paneles_visibles(window)


def test_cargar_material_nuevo_no_arrastra_los_proxies_del_anterior(qtbot, monkeypatch, tmp_path):
    """Mismo motivo por el que `load_clips` limpia el historial: los
    tamaños de proxy van por INDICE de clip, y con material nuevo el
    indice 0 es otro clip. Arrastrarlos haria que el badge anuncie una
    resolucion que no es la de ese archivo."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)
    _esperar_a_los_proxies(window)
    assert window._proxy_sizes

    window.load_clips([_clip(1), _clip(2)])

    assert window._proxy_sizes == {}
    assert window.etiqueta_de_proxy(0) is None


def test_el_manifest_no_exporta_un_rango_invertido(qtbot, monkeypatch, tmp_path):
    """Marcar `O` y despues `I` mas adelante deja out < in. La app ya lo
    MUESTRA en orden --se arreglo en la auditoria de la F1-F5, con `abs`--
    pero lo exportaba tal cual, y el plugin aplica in/out siempre que
    vengan los dos. Premiere recibia un rango al reves.
    """
    window = _window_with_video(qtbot)
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=59.94,
             in_frame=90, out_frame=10),
    ])

    saved = _exportar(window, monkeypatch, tmp_path / "m.json")

    assert saved["clips"][0]["in_frame"] == 10
    assert saved["clips"][0]["out_frame"] == 90


def test_exportar_no_toca_lo_que_esta_en_pantalla(qtbot, monkeypatch, tmp_path):
    """Ordenar es para el manifest: la sesion guarda lo que el editor
    marco, y deshacer tiene que poder volver a eso."""
    window = _window_with_video(qtbot)
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=59.94,
             in_frame=90, out_frame=10),
    ])

    _exportar(window, monkeypatch, tmp_path / "m.json")

    assert window.clips[0].in_frame == 90
    assert window.clips[0].out_frame == 10


# --- pick/reject sobre la seleccion (reporte de Bruno) -----------------
#
# Los cuartos (1-9) ya se aplicaban a todos los clips seleccionados, pero
# `P`, `X` y `⇧P` solo tocaban el clip actual: seleccionabas seis con la
# marquesina, apretabas P, y se marcaba uno.


def test_pick_se_aplica_a_toda_la_seleccion(qtbot):
    window = _window(qtbot)
    window.load_clips([_clip(i) for i in range(1, 7)])
    window.clip_sheet.set_selected({1, 2, 3})

    window.handle_key_press("p")

    assert [c.flag for c in window.clips] == ["none", "pick", "pick", "pick", "none", "none"]


def test_reject_y_destacado_tambien(qtbot):
    window = _window(qtbot)
    window.load_clips([_clip(i) for i in range(1, 5)])
    window.clip_sheet.set_selected({0, 1})
    window.handle_key_press("x")
    assert [c.flag for c in window.clips] == ["reject", "reject", "none", "none"]

    window.handle_key_press("shift+p")
    assert [c.flag for c in window.clips] == ["destacado", "destacado", "none", "none"]


def test_repetir_la_tecla_apaga_solo_si_TODOS_lo_tienen(qtbot):
    """Con la seleccion mezclada, `P` empareja hacia arriba en vez de
    apagar: es lo que uno espera al pintar un lote."""
    window = _window(qtbot)
    window.load_clips([_clip(i) for i in range(1, 4)])
    window.clips[0].flag = "pick"
    window.clip_sheet.set_selected({0, 1})

    window.handle_key_press("p")
    assert [c.flag for c in window.clips] == ["pick", "pick", "none"]

    window.handle_key_press("p")   # ahora si, los dos lo tienen
    assert [c.flag for c in window.clips] == ["none", "none", "none"]


def test_deshacer_devuelve_todo_el_lote(qtbot):
    window = _window(qtbot)
    window.load_clips([_clip(i) for i in range(1, 5)])
    window.clip_sheet.set_selected({0, 1, 2})
    window.handle_key_press("p")

    window.undo()

    assert [c.flag for c in window.clips] == ["none"] * 4


def test_el_historial_dice_cuantos_clips_se_marcaron(qtbot):
    window = _window(qtbot)
    window.load_clips([_clip(i) for i in range(1, 5)])
    window.clip_sheet.set_selected({0, 1, 2})
    window.handle_key_press("p")

    assert "3 clips" in window.history.entries()[0].detalle


# --- la hoja sigue al clip actual (reporte de Bruno) -------------------


def _tarjeta_a_la_vista(window, indice):
    from PySide6.QtCore import QRect
    tarjeta = window.clip_sheet.item_widgets[indice]
    viewport = window.clip_sheet._scroll.viewport()
    arriba = tarjeta.mapTo(viewport, tarjeta.rect().topLeft())
    return viewport.rect().intersects(QRect(arriba, tarjeta.size()))


def test_navegar_con_flechas_trae_la_tarjeta_a_la_vista(qtbot):
    """«En el modo clip no se marca en cual clip estoy cuando voy
    navegando con la flecha»: el borde ambar SI se pintaba, pero la
    tarjeta quedaba fuera de la parte visible de la hoja."""
    window = _window(qtbot)
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(i) for i in range(1, 129)])
    qtbot.wait(10)

    for _ in range(40):
        window.handle_arrow("next")
    qtbot.wait(10)

    assert _tarjeta_a_la_vista(window, window.current_index)


def test_volver_con_la_flecha_izquierda_tambien(qtbot):
    window = _window(qtbot)
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(i) for i in range(1, 129)])
    window.select_clip(100)
    qtbot.wait(10)

    for _ in range(30):
        window.handle_arrow("prev")
    qtbot.wait(10)

    assert _tarjeta_a_la_vista(window, window.current_index)


def test_elegir_un_clip_de_lejos_tambien_lo_trae_a_la_vista(qtbot):
    window = _window(qtbot)
    window.resize(1600, 1000)
    window.show()
    window.load_clips([_clip(i) for i in range(1, 129)])
    qtbot.wait(10)

    window.select_clip(120)
    qtbot.wait(10)

    assert _tarjeta_a_la_vista(window, 120)


def test_la_sesion_guarda_el_tamano_de_cada_clip(qtbot, tmp_path):
    """«Los videos estan en cuadriculas horizontales pero son
    verticales»: al recuperar una sesion no se volvia a correr ffprobe,
    asi que no se sabia el tamaño de nada y TODAS las tarjetas caian en
    16:9 -- material vertical dibujado en cajas horizontales."""
    window = _window(qtbot)
    window.session_path = tmp_path / "s.json"
    window.load_clips([_clip(1), _clip(2)])
    window._clip_sizes = {0: (2160, 3840), 1: (3840, 2160)}
    window._clip_durations = {0: 18.4, 1: 7.2}
    window._clip_rotations = {0: 90, 1: 0}

    window._write_autosave_now()
    window._autosave_pool.waitForDone(4000)

    import json
    guardado = json.loads(window.session_path.read_text())
    assert guardado["tamanos"] == {"0": [2160, 3840], "1": [3840, 2160]}
    assert guardado["duraciones"] == {"0": 18.4, "1": 7.2}
    assert guardado["rotaciones"] == {"0": 90, "1": 0}


# --- miniaturas: del proxy, y avisando (reporte de Bruno) --------------


def test_las_miniaturas_salen_del_proxy_cuando_hay(qtbot, monkeypatch, tmp_path):
    """«Mi computadora empezo a usar los abanicos y no habia hecho nada»:
    eran 109 procesos de mpv sacando 12 cuadros cada uno de HEVC 10-bit a
    268 Mbps. Del proxy, el mismo trabajo cuesta ~20 veces menos
    (medido en la task 0 de la F9: 204 ms contra 9 ms por apertura).
    """
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    pedidos = []
    monkeypatch.setattr("clasificador_video.ui.main_window.extract_thumbnail_strip",
                        lambda video, *a, **k: pedidos.append(video) or [])
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path, parchear_miniaturas=False)
    window._thread_pool.waitForDone(5000)
    # Pedir la tira DEL PROXY cuando ya hay una extraccion corriendo para ese
    # clip no encola un segundo mpv --se pisarian el socket-- sino que la
    # difiere hasta que la primera termina. Esa segunda vuelta llega por
    # señal, asi que hay que dejar correr el ciclo de eventos.
    QApplication.processEvents()
    window._thread_pool.waitForDone(5000)
    QApplication.processEvents()

    # la primera pasada sale del original --al importar todavia no hay
    # proxies-- y al engancharlos a mano se vuelven a pedir desde el proxy
    assert pedidos[0].name == "C0001.MP4"
    assert pedidos[-1].name == "C0001S03.MP4"


def test_sin_proxy_las_miniaturas_salen_del_original(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    pedidos = []
    monkeypatch.setattr("clasificador_video.ui.main_window.extract_thumbnail_strip",
                        lambda video, *a, **k: pedidos.append(video) or [])
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path, con_proxy=False,
                        parchear_miniaturas=False)
    window._thread_pool.waitForDone(5000)

    assert pedidos and pedidos[0].name == "C0001.MP4"


def test_la_barra_avisa_mientras_se_generan_las_miniaturas(qtbot, monkeypatch, tmp_path):
    """«Los videos no se veian la primera vez que los importe»: si se
    veian, tardaban un minuto y la app no decia nada."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr("clasificador_video.ui.main_window.extract_thumbnail_strip",
                        lambda *a, **k: [])
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    _importar_con_proxy(window, monkeypatch, tmp_path)

    assert "miniatura" in window.status_bar.progress_label.text().lower()

    # Dos vueltas: al enganchar los proxies se vuelve a pedir la tira desde
    # el proxy, y esa segunda pasada se difiere hasta que termina la primera
    # --dos mpv sobre el mismo clip se pisan el socket--, asi que llega por
    # señal y necesita otro giro del ciclo de eventos.
    from PySide6.QtWidgets import QApplication
    for _ in range(2):
        window._thread_pool.waitForDone(5000)
        QApplication.processEvents()
    assert window.status_bar.progress_label.isHidden()


# --- enganche MANUAL de proxies, como en Premiere (pedido de Bruno) ----


def _material_con_proxies(tmp_path, cuantos=3, sufijo="S03", con_proxy=(0, 1, 2)):
    clips = tmp_path / "clips"
    proxies = tmp_path / "proxy"
    clips.mkdir(parents=True, exist_ok=True)
    proxies.mkdir(parents=True, exist_ok=True)
    for i in range(cuantos):
        (clips / f"C{i:04d}.MP4").touch()
        if i in con_proxy:
            (proxies / f"C{i:04d}{sufijo}.MP4").touch()
    return clips, proxies


def _ventana_con_material(qtbot, monkeypatch, tmp_path, **kwargs):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    clips, proxies = _material_con_proxies(tmp_path, **kwargs)
    window.importar_rutas([clips])
    window._thread_pool.waitForDone(5000)
    return window, clips, proxies


def _elegir(monkeypatch, ruta):
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(ruta), ""),
    )


def _sin_avisos(monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.information",
                        lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: QMessageBox.Ok)


def test_al_importar_ya_NO_se_buscan_proxies_solos(qtbot, monkeypatch, tmp_path):
    """«Necesito que los proxies los ponga manualmente siempre»."""
    window, _, _ = _ventana_con_material(qtbot, monkeypatch, tmp_path)

    assert all(c.ruta_proxy is None for c in window.clips)


def test_elegir_el_proxy_de_un_clip_engancha_todos(qtbot, monkeypatch, tmp_path):
    window, _, proxies = _ventana_con_material(qtbot, monkeypatch, tmp_path)
    _elegir(monkeypatch, proxies / "C0000S03.MP4")
    _sin_avisos(monkeypatch)

    window.adjuntar_proxies()
    window._thread_pool.waitForDone(5000)
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()

    assert [c.ruta_proxy.name for c in window.clips] == [
        "C0000S03.MP4", "C0001S03.MP4", "C0002S03.MP4"
    ]


def test_los_clips_sin_proxy_quedan_como_estaban(qtbot, monkeypatch, tmp_path):
    window, _, proxies = _ventana_con_material(
        qtbot, monkeypatch, tmp_path, con_proxy=(0, 2))
    _elegir(monkeypatch, proxies / "C0000S03.MP4")
    _sin_avisos(monkeypatch)

    window.adjuntar_proxies()
    window._thread_pool.waitForDone(5000)
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()

    assert window.clips[1].ruta_proxy is None
    assert window.clips[2].ruta_proxy is not None


def test_elegir_un_archivo_que_no_corresponde_avisa_y_no_toca_nada(qtbot, monkeypatch, tmp_path):
    """Si el nombre no tiene nada que ver con el clip, emparejar 128
    clips con un patron inventado seria peor que no hacer nada."""
    window, _, proxies = _ventana_con_material(qtbot, monkeypatch, tmp_path)
    ajeno = proxies / "cualquier_otra_cosa.MP4"
    ajeno.touch()
    _elegir(monkeypatch, ajeno)
    avisos = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: avisos.append(a) or QMessageBox.Ok)

    window.adjuntar_proxies()

    assert avisos, "no aviso de que el archivo no corresponde"
    assert all(c.ruta_proxy is None for c in window.clips)


def test_cancelar_el_dialogo_no_hace_nada(qtbot, monkeypatch, tmp_path):
    window, _, _ = _ventana_con_material(qtbot, monkeypatch, tmp_path)
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: ("", ""),
    )

    window.adjuntar_proxies()

    assert all(c.ruta_proxy is None for c in window.clips)


def test_sin_clips_importados_no_se_puede_enganchar_nada(qtbot, monkeypatch):
    window = _window_with_video(qtbot)
    avisos = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: avisos.append(a) or QMessageBox.Ok)

    window.adjuntar_proxies()

    assert avisos


def test_el_boton_de_la_barra_de_titulo_abre_el_dialogo(qtbot, monkeypatch, tmp_path):
    window, _, proxies = _ventana_con_material(qtbot, monkeypatch, tmp_path)
    _elegir(monkeypatch, proxies / "C0000S03.MP4")
    _sin_avisos(monkeypatch)

    window.title_bar.proxies_button.click()
    window._thread_pool.waitForDone(5000)
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()

    assert window.clips[0].ruta_proxy is not None


def test_si_no_se_pudo_leer_ningun_video_lo_dice(qtbot, monkeypatch, tmp_path):
    """Encontrado armando el paquete: sin `ffprobe`, la importacion
    fallaba clip por clip --cada fallo se traga en silencio-- y el
    resultado era una carpeta importada con CERO clips y ninguna
    explicacion. En otra computadora ese seria el sintoma de todo.
    """
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    for i in range(3):
        (carpeta / f"C{i:04d}.MP4").touch()

    def revienta(_):
        raise RuntimeError("no se encontró ffprobe")
    monkeypatch.setattr(window, "_probe_clip", revienta)
    avisos = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: avisos.append(a[2]) or QMessageBox.Ok)

    window.importar_rutas([carpeta])

    assert avisos, "importo 0 clips sin decir nada"
    assert "3" in avisos[0]


def test_si_solo_falla_uno_no_molesta(qtbot, monkeypatch, tmp_path):
    """Un archivo corrupto entre 128 no puede convertirse en un diálogo:
    se salta y ya, como siempre."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    for i in range(3):
        (carpeta / f"C{i:04d}.MP4").touch()

    def a_veces(ruta):
        if ruta.name == "C0001.MP4":
            raise RuntimeError("corrupto")
        return {"width": 2160, "height": 3840, "fps": 29.97,
                "duration_frames": 540, "rotation": 90}
    monkeypatch.setattr(window, "_probe_clip", a_veces)
    monkeypatch.setattr("clasificador_video.ui.main_window.extract_thumbnail_strip",
                        lambda *a, **k: [])
    avisos = []
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: avisos.append(a) or None)

    window.importar_rutas([carpeta])

    assert len(window.clips) == 2
    assert not avisos


# --- ↑ y ↓ suben y bajan el estado (pedido de Bruno) -------------------
#
# «Quiero que los botones de arriba y abajo tengan una funcion mas util»:
# no hacian nada mientras clasificas. La escalera es la que ya usa
# DECISIONES.md -- reject, sin marca, pick, destacado -- asi que subir y
# bajar es la forma natural de recorrerla sin acordarse de que letra es
# cada estado.


def test_la_flecha_arriba_sube_un_escalon(qtbot):
    window = _window(qtbot)
    window.load_clips([_clip(1)])

    for esperado in ("pick", "destacado", "destacado"):
        window.handle_key_press("arriba")
        assert window.clips[0].flag == esperado


def test_la_flecha_abajo_baja_un_escalon(qtbot):
    window = _window(qtbot)
    window.load_clips([_clip(1)])
    window.clips[0].flag = "destacado"

    for esperado in ("pick", "none", "reject", "reject"):
        window.handle_key_press("abajo")
        assert window.clips[0].flag == esperado


def test_suben_y_bajan_toda_la_seleccion(qtbot):
    window = _window(qtbot)
    window.load_clips([_clip(i) for i in range(1, 5)])
    window.clip_sheet.set_selected({0, 1, 2})

    window.handle_key_press("arriba")

    assert [c.flag for c in window.clips] == ["pick", "pick", "pick", "none"]


def test_con_la_seleccion_mezclada_se_empareja_hacia_arriba(qtbot):
    """Sube UN escalon desde el mas bajo, y los deja a todos ahi.

    Si cada uno subiera el suyo, el lote quedaria igual de disparejo que
    antes -- y lo que uno quiere al pintar un lote es dejarlos iguales.
    Con un pick y uno sin marca, `↑` deja los dos en pick; otro `↑` los
    sube a destacado."""
    window = _window(qtbot)
    window.load_clips([_clip(i) for i in range(1, 4)])
    window.clips[0].flag = "pick"
    window.clip_sheet.set_selected({0, 1})

    window.handle_key_press("arriba")
    assert [c.flag for c in window.clips] == ["pick", "pick", "none"]

    window.handle_key_press("arriba")
    assert [c.flag for c in window.clips] == ["destacado", "destacado", "none"]


def test_deshacer_devuelve_el_escalon(qtbot):
    window = _window(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("arriba")

    window.undo()

    assert window.clips[0].flag == "none"


def test_sin_clips_las_flechas_no_truenan(qtbot):
    window = _window(qtbot)
    window.handle_key_press("arriba")
    window.handle_key_press("abajo")


# --- R reinicia el clip (pedido de Bruno) ------------------------------


def test_la_tecla_r_vuelve_al_inicio_del_clip(qtbot):
    """«Quiero que sea mas facil reiniciar el video»: no habia forma de
    volver al principio salvo arrastrar la barra hasta el borde."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    reproductor = window.video_widget.player
    reproductor._mpv.duration = 18.0
    reproductor._mpv.time_pos = 8.0

    window.handle_key_press("r")

    assert reproductor.position == 0.0


def test_reiniciar_sin_clip_no_truena(qtbot):
    window = _window_with_video(qtbot)
    window.handle_key_press("r")


# --- los portadores de señales de los trabajos en segundo plano --------
#
# Ver el comentario largo en `SeñalesDeTrabajos`: cuando cada trabajo traia
# su propio portador, ese portador moria en un hilo del QThreadPool y la
# suite se caia con SIGSEGV cada tantas corridas. Lo que cura es que ningun
# objeto de Qt nazca ni muera por trabajo.


def test_el_portador_de_señales_no_es_un_widget(qtbot):
    window = _window(qtbot)

    assert isinstance(window._señales_de_trabajos, QObject)
    assert not isinstance(window._señales_de_trabajos, QWidget)


def test_los_trabajos_no_traen_su_propio_portador(qtbot, tmp_path):
    """Todos usan el de la ventana, y ninguno crea uno."""
    window = _window(qtbot)
    señales = window._señales_de_trabajos
    trabajos = [
        _ThumbnailJob(0, 0, Path("v.mp4"), tmp_path, 3.0, señales),
        _ProxyProbeJob(0, 0, Path("v.mp4"), lambda ruta: None, señales),
    ]

    assert all(t.signals is señales for t in trabajos)


def test_los_trabajos_que_lanza_la_ventana_usan_su_portador(qtbot, tmp_path):
    """Este es el que atrapa una regresion de verdad: que alguien vuelva a
    crear un portador por trabajo dentro de la ventana."""
    window = _window(qtbot)
    lanzados = []

    class PoolFalso:
        def start(self, job):
            lanzados.append(job)

        def waitForDone(self, ms):  # noqa: N802 -- lo llama el closeEvent
            return True

    window._thread_pool = PoolFalso()
    window.load_clips([_clip(1), _clip(2)])

    window._schedule_thumbnails()

    assert lanzados
    assert all(t.signals is window._señales_de_trabajos for t in lanzados)


def test_el_portador_no_muere_en_un_hilo_del_pool(qtbot, tmp_path):
    """El trabajo corre en un hilo del pool y ahi se destruye; el portador
    tiene que seguir vivo, porque es de la ventana."""
    # con `threading.get_ident()` y NO con `QThread.currentThread()`: ese
    # devuelve un objeto de Qt del hilo del pool, y guardarlo en una lista
    # lo deja vivo en Python despues de que el hilo murio. Shiboken se queda
    # entonces con una direccion vieja apuntada, y cuando Qt reusa esa
    # memoria para otro widget, el objeto nuevo se lee como un QThread.
    # Paso de verdad: una corrida de 38 murio con «QRubberBand(Shape,
    # QThread)» en un test de otro archivo.
    hilo_de_la_ui = threading.get_ident()
    hilos = []
    señales = _window(qtbot)._señales_de_trabajos
    pool = QThreadPool()
    pool.setMaxThreadCount(2)

    class _Espia(_ProxyProbeJob):
        def run(self):
            super().run()
            hilos.append(threading.get_ident())

    for _ in range(20):
        pool.start(_Espia(0, 0, Path("v.mp4"), lambda ruta: None, señales))
    pool.waitForDone(5000)

    # los trabajos si murieron fuera del hilo de la UI...
    assert hilos and all(h != hilo_de_la_ui for h in hilos)
    # ...y el portador sigue en pie
    señales.proxy_sondeado.emit(0, 0, None)  # no truena: el objeto de C++ vive


def test_la_app_arranca_en_la_hoja(qtbot):
    """Lo primero que Bruno ve es el material, no un visor vacio.

    Pedido suyo, textual: «quiero que la parte de hoja sea lo primero que se
    vea». Antes arrancaba en modo clip, o sea con un visor negro hasta que
    importaras algo.
    """
    window = _window(qtbot)

    assert window._modo_hoja is True
    assert window.clip_sheet.isVisible() or not window.video_stage.isVisible()


# --- el audio no suena sin imagen (revision F7) -------------------------


def test_arrancar_en_la_hoja_no_reproduce_el_clip(qtbot):
    """El bug que Bruno oiria en el primer minuto: la app abre en la hoja,
    restaura su sesion, y empieza a sonar el audio de un clip que no ve --
    sin visor ni indicador a la vista para entender de donde sale.
    """
    window = _window(qtbot)
    window.load_clips([_clip(1)])

    assert window.video_widget.player.is_paused
    assert not window._auto_reproduciendo
    # el clip SI se abrio: cruzar al visor tiene que ser instantaneo
    assert window.video_widget.player._mpv.loaded_path is not None


def test_cruzar_al_visor_reanuda_lo_que_la_hoja_dejo_pausado(qtbot):
    """El autoplay no se pierde, se aplaza: en cuanto hay imagen, corre."""
    window = _window(qtbot)
    window.load_clips([_clip(1)])

    window.alternar_modo_hoja()          # a modo clip

    assert not window.video_widget.player.is_paused
    assert window._auto_reproduciendo


def test_volver_a_la_hoja_calla_el_video(qtbot):
    """El mismo bug, alcanzable con una tecla: `⇥` desde el visor con el
    clip corriendo dejaba el audio sonando sobre la hoja."""
    window = _a_modo_clip(_window(qtbot))
    window.load_clips([_clip(1)])
    assert not window.video_widget.player.is_paused

    window.alternar_modo_hoja()          # de vuelta a la hoja

    assert window.video_widget.player.is_paused


def test_si_pausaste_a_mano_cruzar_a_la_hoja_y_volver_no_lo_reanuda(qtbot):
    """Lo que se aplaza es el AUTOPLAY, no una orden tuya: si pausaste,
    sigue pausado al volver."""
    window = _a_modo_clip(_window(qtbot))
    window.load_clips([_clip(1)])
    window.video_widget.player.pause()
    window._tick_playhead()              # apaga el badge `▶ auto`

    window.alternar_modo_hoja()
    window.alternar_modo_hoja()

    assert window.video_widget.player.is_paused


# --- crear los proxies (F11) -------------------------------------------
#
# Nace por el dron: la Sony escribe sus proxies sola y el `.LRF` del DJI no
# sirve (contenido corrido entre 0 y 5 cuadros, variable por toma), asi que
# la unica via es generarlos del original.


def _bin_para_generar(qtbot, monkeypatch, tmp_path, cuantos=3):
    """Un bin con `cuantos` clips y ningun proxy, listo para generar."""
    window, clips, _ = _ventana_con_material(
        qtbot, monkeypatch, tmp_path, cuantos=cuantos, con_proxy=()
    )
    _sin_avisos(monkeypatch)
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QMessageBox.question",
        lambda *a, **k: QMessageBox.StandardButton.Yes,
    )
    return window, clips


def _generados(window, monkeypatch, falla_en=()):
    """Sustituye ffmpeg: anota a quien le tocaba y escribe el archivo."""
    hechos = []

    def falso_generar(original, carpeta, **kwargs):
        if original.name in falla_en:
            raise RuntimeError("ffmpeg no pudo con " + original.name)
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = proxy_gen.ruta_de_proxy(original, carpeta)
        destino.write_bytes(b"proxy")
        hechos.append(original.name)
        return destino

    monkeypatch.setattr(proxy_gen, "generar", falso_generar)
    return hechos


def _esperar_generacion(window):
    window._generacion_pool.waitForDone(5000)
    QApplication.processEvents()
    window._thread_pool.waitForDone(5000)
    QApplication.processEvents()


def test_crear_proxies_los_genera_y_los_engancha_solos(qtbot, monkeypatch, tmp_path):
    """Se enganchan apenas terminan, no al final de la tanda: con 23 tomas
    son varios minutos, y ver el material aligerarse conforme avanza es lo
    que hace que la espera no se sienta muerta."""
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path)
    hechos = _generados(window, monkeypatch)
    nombre = window.bins.to_list()[0]["nombre"]

    window.generar_proxies_de_bin(nombre)
    _esperar_generacion(window)

    assert hechos == ["C0000.MP4", "C0001.MP4", "C0002.MP4"]
    assert [c.ruta_proxy.name for c in window.clips] == [
        "C0000S03.mp4", "C0001S03.mp4", "C0002S03.mp4"
    ]


def test_los_proxies_van_a_la_carpeta_de_al_lado(qtbot, monkeypatch, tmp_path):
    """Adentro ensuciaria la copia de la tarjeta. Bruno lo eligio asi."""
    window, clips = _bin_para_generar(qtbot, monkeypatch, tmp_path)
    _generados(window, monkeypatch)
    nombre = window.bins.to_list()[0]["nombre"]

    window.generar_proxies_de_bin(nombre)
    _esperar_generacion(window)

    assert (clips.parent / "Proxies" / "C0000S03.mp4").exists()
    assert not (clips / "Proxies").exists()


def test_volver_a_darle_no_rehace_los_que_ya_estan(qtbot, monkeypatch, tmp_path):
    """Es el caso normal despues de cancelar a la mitad. Con 23 tomas,
    rehacerlas son minutos tirados."""
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path)
    hechos = _generados(window, monkeypatch)
    nombre = window.bins.to_list()[0]["nombre"]
    window.generar_proxies_de_bin(nombre)
    _esperar_generacion(window)
    hechos.clear()

    window.generar_proxies_de_bin(nombre)
    _esperar_generacion(window)

    assert hechos == []


def test_cancelar_deja_lo_hecho_y_no_hace_lo_que_faltaba(qtbot, monkeypatch, tmp_path):
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path, cuantos=3)
    hechos = []

    def generar_y_cancelar(original, carpeta, **kwargs):
        # cancela DURANTE el primero, con los otros dos ya encolados: es el
        # caso que importa, porque el trabajo lee la bandera al empezar
        window.cancelar_generacion_de_proxies()
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = proxy_gen.ruta_de_proxy(original, carpeta)
        destino.write_bytes(b"proxy")
        hechos.append(original.name)
        return destino

    monkeypatch.setattr(proxy_gen, "generar", generar_y_cancelar)
    nombre = window.bins.to_list()[0]["nombre"]

    window.generar_proxies_de_bin(nombre)
    _esperar_generacion(window)

    assert hechos == ["C0000.MP4"]           # el que ya corria termina
    assert window._generando_proxies is None  # y la tanda se cierra sola


def test_un_proxy_que_falla_no_tumba_los_demas(qtbot, monkeypatch, tmp_path):
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path)
    hechos = _generados(window, monkeypatch, falla_en=("C0001.MP4",))
    nombre = window.bins.to_list()[0]["nombre"]

    window.generar_proxies_de_bin(nombre)
    _esperar_generacion(window)

    assert hechos == ["C0000.MP4", "C0002.MP4"]
    assert window._generando_proxies is None


def test_no_se_encima_una_segunda_tanda(qtbot, monkeypatch, tmp_path):
    """Dos tandas a la vez pelearian por el codificador del chip y ademas
    dejarian el contador del encabezado diciendo cualquier cosa."""
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path)
    hechos = _generados(window, monkeypatch)
    nombre = window.bins.to_list()[0]["nombre"]
    window._generando_proxies = {"bin": "otro", "generacion": 99, "total": 5,
                                 "hechos": 0, "fallidos": [], "cancelado": False,
                                 "carpeta": tmp_path}

    window.generar_proxies_de_bin(nombre)
    _esperar_generacion(window)

    assert hechos == []


def test_una_portada_vieja_no_impide_sacar_la_tira_de_escrubeo(qtbot, monkeypatch, tmp_path):
    """El bug que Bruno reporto con su material: «¿por que no puedo
    escrubear en los de la FX30 pero si en los del dron?».

    Los clips importados ANTES de que existiera la tira dejaron en el cache
    una sola portada, `00000001.jpg`. El codigo la tomaba como cache hit, o
    sea que esos clips se quedaban con un solo cuadro PARA SIEMPRE --el
    escrubeo necesita mas de uno-- y la unica forma de recuperarlos era
    borrar el cache a mano, que nadie sabia que hubiera que hacer. Los del
    dron se importaron despues y por eso si tenian tira.

    La portada vieja se sigue pintando (para que la tarjeta no quede gris
    mientras se extrae), pero ya no cancela la extraccion.
    """
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)
    from clasificador_video.thumbnails import cache_dir_for
    cache_dir = cache_dir_for(clip_path, cache_root)
    cache_dir.mkdir(parents=True)
    (cache_dir / "00000001.jpg").write_bytes(b"portada vieja")

    pedidos = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: pedidos.append(1) or [],
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations[0] = 4.0
    window._schedule_thumbnails()
    window._thread_pool.waitForDone(3000)

    assert pedidos == [1]


def test_sin_duracion_la_portada_vieja_no_se_re_extrae_cada_sesion(qtbot, monkeypatch, tmp_path):
    """Sin duracion no hay tira posible, asi que volver a pedirla seria
    extraer otra vez la misma portada suelta en cada arranque."""
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)
    from clasificador_video.thumbnails import cache_dir_for
    cache_dir = cache_dir_for(clip_path, cache_root)
    cache_dir.mkdir(parents=True)
    (cache_dir / "00000001.jpg").write_bytes(b"portada vieja")

    pedidos = []
    for nombre in ("extract_thumbnail_strip", "extract_thumbnail"):
        monkeypatch.setattr(
            f"clasificador_video.ui.main_window.{nombre}",
            lambda *a, **k: pedidos.append(1) or [],
        )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations.pop(0, None)
    window._schedule_thumbnails()
    window._thread_pool.waitForDone(3000)

    assert pedidos == []


def test_engancha_aunque_elijas_el_proxy_de_otro_clip_del_bin(qtbot, monkeypatch, tmp_path):
    """El caso de Bruno, tal como lo reporto: estas parado en un clip y en
    el dialogo eliges el PRIMERO de la carpeta de proxies, que es de otro
    clip. Antes eso era un error con un cartel que no ayudaba; ahora
    engancha, porque el patron sale igual de bien de cualquier par."""
    window, _, proxies = _ventana_con_material(qtbot, monkeypatch, tmp_path)
    window.current_index = 2                      # parado en el ultimo clip
    _elegir(monkeypatch, proxies / "C0000S03.MP4")  # y eligiendo el del primero
    _sin_avisos(monkeypatch)

    window.adjuntar_proxies()
    window._thread_pool.waitForDone(5000)
    QApplication.processEvents()

    assert [c.ruta_proxy.name for c in window.clips] == [
        "C0000S03.MP4", "C0001S03.MP4", "C0002S03.MP4"
    ]


def test_no_se_encolan_dos_extracciones_para_el_mismo_clip(qtbot, monkeypatch, tmp_path):
    """Bruno: «sigue sin funcionar el scrubbing en los videos de sony».

    `_schedule_thumbnails` se llama varias veces por sesion --al cargar, al
    terminar la revision de media, al enganchar proxies--. Con dos trabajos
    vivos para el mismo clip, los dos comparten carpeta de salida y socket
    IPC, y el segundo le BORRA el socket al primero (lo hace a proposito,
    para no heredar uno viejo). El primer mpv muere a media tira y esa
    tarjeta se queda con UN cuadro, o sea sin escrubeo.

    Se vio en su cache real: carpetas con `strip_00.jpg` y nada mas.
    """
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)

    arrancadas = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: arrancadas.append(1) or [],
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations[0] = 4.0

    window._schedule_thumbnails([0])
    window._schedule_thumbnails([0])   # la segunda no debe encolar nada
    window._thread_pool.waitForDone(3000)

    assert arrancadas == [1]


def test_cuando_termina_se_puede_volver_a_pedir(qtbot, monkeypatch, tmp_path):
    """La guarda es «hay uno corriendo», no «ya se pidio una vez»: si no,
    reconectar la media de un bin nunca volveria a pedir sus portadas."""
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)

    arrancadas = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: arrancadas.append(1) or [],
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations[0] = 4.0

    window._schedule_thumbnails([0])
    window._thread_pool.waitForDone(3000)
    QApplication.processEvents()       # llega la señal y lo saca de «en vuelo»
    window._schedule_thumbnails([0])
    window._thread_pool.waitForDone(3000)

    assert arrancadas == [1, 1]


def test_una_tira_cortada_a_la_mitad_se_vuelve_a_extraer(qtbot, monkeypatch, tmp_path):
    """Quedaron asi los clips a los que dos extracciones se les pisaron el
    socket: `strip_00.jpg` y nada mas. Con una sola foto no hay escrubeo, y
    darla por buena los dejaba en el mismo callejon sin salida del que se
    acaba de salir con la portada suelta."""
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)
    from clasificador_video.thumbnails import cache_dir_for
    cache_dir = cache_dir_for(clip_path, cache_root)
    cache_dir.mkdir(parents=True)
    (cache_dir / "strip_00.jpg").write_bytes(b"la unica que alcanzo a salir")

    pedidos = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: pedidos.append(1) or [],
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations[0] = 4.0
    window._schedule_thumbnails()
    window._thread_pool.waitForDone(3000)

    assert pedidos == [1]


def _eligiendo(window, monkeypatch, que: str):
    """Responde el diálogo de «enlazar o crear proxies» sin abrirlo.

    Se parchea el método y no `QMessageBox`: el diálogo tiene botones
    propios, así que la respuesta no es un valor estándar sino cuál botón se
    apretó, y simularlo desde afuera sería reconstruir el diálogo entero.
    """
    monkeypatch.setattr(window, "_preguntar_que_hacer_con_proxies",
                        lambda *a, **k: que)


def test_si_aceptas_crear_proxies_las_portadas_esperan(qtbot, monkeypatch, tmp_path):
    """Del proxy la portada cuesta 5 veces menos --5.8 s contra 1.2 s por
    clip, medido con material real--, asi que sacarlas del original justo
    antes de generar los proxies es pagar el precio caro por nada. Con 132
    clips son 4 minutos contra 1."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    pedidas = []
    monkeypatch.setattr(window, "_schedule_thumbnails",
                        lambda indices=None: pedidas.append(indices))
    monkeypatch.setattr(proxy_gen, "generar", lambda *a, **k: Path("/p/x.mp4"))
    _eligiendo(window, monkeypatch, "crear")
    clips, _ = _material_con_proxies(tmp_path, con_proxy=())

    window.importar_rutas([clips])

    assert pedidas == []                        # no se pidio ni una portada
    assert window._generando_proxies is not None  # y los proxies ya corren


def test_si_dices_que_no_las_portadas_salen_como_siempre(qtbot, monkeypatch, tmp_path):
    """El `question` por defecto de la suite responde No."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    pedidas = []
    monkeypatch.setattr(window, "_schedule_thumbnails",
                        lambda indices=None: pedidas.append(indices))
    clips, _ = _material_con_proxies(tmp_path, con_proxy=())

    window.importar_rutas([clips])

    assert pedidas == [[0, 1, 2]]
    assert window._generando_proxies is None


def test_al_terminar_los_proxies_se_piden_las_portadas_que_falten(qtbot, monkeypatch, tmp_path):
    """Salga como salga la generacion. Si cancelas a la mitad, o si algun
    proxy falla, esos clips se quedarian en gris para siempre esperando algo
    que ya no va a llegar."""
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path)
    _generados(window, monkeypatch)
    nombre = window.bins.to_list()[0]["nombre"]
    pedidas = []
    window.generar_proxies_de_bin(nombre)
    monkeypatch.setattr(window, "_schedule_thumbnails",
                        lambda indices=None: pedidas.append(indices))
    window.cancelar_generacion_de_proxies()
    _esperar_generacion(window)

    assert pedidas and pedidas[-1] == [0, 1, 2]


def test_al_importar_tambien_se_pueden_enlazar_los_proxies_que_ya_existen(qtbot, monkeypatch, tmp_path):
    """La Sony YA graba sus proxies: esos se enlazan, no se generan. Ofrecer
    solo «crear» mandaba a transcodificar de cero archivos que ya estaban en
    el disco -- minutos tirados y un duplicado de cada proxy."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    generados = []
    monkeypatch.setattr(proxy_gen, "generar",
                        lambda *a, **k: generados.append(1) or Path("/p/x.mp4"))
    clips, proxies = _material_con_proxies(tmp_path)
    _elegir(monkeypatch, proxies / "C0000S03.MP4")
    _eligiendo(window, monkeypatch, "enlazar")

    window.importar_rutas([clips])
    window._thread_pool.waitForDone(5000)
    QApplication.processEvents()

    assert generados == []                       # no se transcodifico nada
    assert [c.ruta_proxy.name for c in window.clips] == [
        "C0000S03.MP4", "C0001S03.MP4", "C0002S03.MP4"
    ]


def test_si_cancelas_el_enlace_las_portadas_salen_del_original(qtbot, monkeypatch, tmp_path):
    """O esas tarjetas se quedan en gris esperando un proxy que nunca
    elegiste."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    monkeypatch.setattr(window, "_probe_clip", _ProbeConProxy())
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    pedidas = []
    monkeypatch.setattr(window, "_schedule_thumbnails",
                        lambda indices=None: pedidas.append(indices))
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: ("", ""),        # le diste a Cancelar
    )
    _eligiendo(window, monkeypatch, "enlazar")
    clips, _ = _material_con_proxies(tmp_path, con_proxy=())

    window.importar_rutas([clips])

    assert pedidas == [[0, 1, 2]]


def test_la_hoja_recibe_cuales_clips_tienen_proxy(qtbot, monkeypatch, tmp_path):
    """El dato tiene que llegar del clip a la tarjeta: sin este cableado la
    marca existe y nunca se enciende."""
    window, _, proxies = _ventana_con_material(qtbot, monkeypatch, tmp_path,
                                               con_proxy=(0, 2))
    _elegir(monkeypatch, proxies / "C0000S03.MP4")
    window.adjuntar_proxies()
    window._thread_pool.waitForDone(5000)
    QApplication.processEvents()

    marcados = [w.plan_de_pintado()["proxy"] for w in window.clip_sheet.item_widgets]
    assert marcados == [True, False, True]


def test_quitar_los_proxies_apaga_la_marca(qtbot, monkeypatch, tmp_path):
    """El otro sentido. Sin esto la tarjeta seguiria diciendo PROXY sobre un
    clip que ya no lo tiene, que es peor que no decir nada."""
    window, _, proxies = _ventana_con_material(qtbot, monkeypatch, tmp_path)
    _elegir(monkeypatch, proxies / "C0000S03.MP4")
    window.adjuntar_proxies()
    window._thread_pool.waitForDone(5000)
    QApplication.processEvents()
    nombre = window.bins.to_list()[0]["nombre"]

    window.quitar_proxies_de_bin(nombre)
    window._thread_pool.waitForDone(5000)
    QApplication.processEvents()

    assert not any(w.plan_de_pintado()["proxy"] for w in window.clip_sheet.item_widgets)


def test_una_tira_a_medias_sin_marca_se_vuelve_a_extraer(qtbot, monkeypatch, tmp_path):
    """El caso de Bruno: «a veces no jala el escrubeo en los primeros
    clips». Eran los que estaban corriendo al cerrar la app -- medido en su
    cache: 6 de 133, cortados de tres en tres, que es cuantos se extraen a
    la vez. Contar fotos no alcanza para distinguirlos: una tira de 2 se ve
    igual de «cacheada» que una entera, y con dos posiciones el escrubeo se
    siente roto."""
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)
    from clasificador_video.thumbnails import cache_dir_for
    cache_dir = cache_dir_for(clip_path, cache_root)
    cache_dir.mkdir(parents=True)
    for i in range(2):                       # se corto en la segunda foto
        (cache_dir / f"strip_{i:02d}.jpg").write_bytes(b"fake-jpeg")

    pedidos = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: pedidos.append(1) or [],
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations[0] = 4.0
    window._schedule_thumbnails()
    window._thread_pool.waitForDone(3000)

    assert pedidos == [1]


def test_una_tira_con_marca_no_se_rehace_aunque_tenga_pocas_fotos(qtbot, monkeypatch, tmp_path):
    """La marca dice «esto TERMINO», no «esto tiene doce». Un clip que solo
    dio 9 cuadros es valido, y rehacerlo cada sesion seria pagar la
    extraccion completa para siempre."""
    from clasificador_video.thumbnails import cache_dir_for, MARCA_DE_COMPLETA
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)
    cache_dir = cache_dir_for(clip_path, cache_root)
    cache_dir.mkdir(parents=True)
    for i in range(9):
        (cache_dir / f"strip_{i:02d}.jpg").write_bytes(b"fake-jpeg")
    (cache_dir / MARCA_DE_COMPLETA).write_text("9")

    pedidos = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: pedidos.append(1) or [],
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations[0] = 4.0
    window._schedule_thumbnails()
    window._thread_pool.waitForDone(3000)

    assert pedidos == []


def test_las_fotos_a_medias_de_una_extraccion_viva_no_encolan_otra(qtbot, monkeypatch, tmp_path):
    """La trampa: las fotos incompletas que se ven en el cache son, muchas
    veces, las que esta escribiendo AHORA MISMO la extraccion de ese clip.
    Pintarlas pasando por `_on_thumbnail_ready` la daba por terminada --ese
    metodo lleva la contabilidad-- y el barrido encolaba un segundo mpv
    sobre el mismo socket. Es el bug que dejaba las tiras cortadas."""
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)
    from clasificador_video.thumbnails import cache_dir_for
    cache_dir = cache_dir_for(clip_path, cache_root)

    arrancadas = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: arrancadas.append(1) or [],
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations[0] = 4.0
    window._schedule_thumbnails([0])
    # el mpv de esa extraccion ya escribio dos fotos y sigue trabajando
    cache_dir.mkdir(parents=True, exist_ok=True)
    for i in range(2):
        (cache_dir / f"strip_{i:02d}.jpg").write_bytes(b"a medias")

    window._schedule_thumbnails([0])
    window._thread_pool.waitForDone(3000)

    assert arrancadas == [1]


def test_una_tanda_nueva_no_encima_mpv_sobre_los_que_siguen_corriendo(qtbot, monkeypatch, tmp_path):
    """Quitar un bin --o cualquier cosa que pida las portadas de cero--
    sube la generacion. Vaciar ahi el registro de «en vuelo» era decir que
    no hay nada corriendo con tres extracciones vivas, y encolarles un
    segundo mpv encima. Ahora se anotan para rehacerse cuando terminen."""
    cache_root = tmp_path / "cache"
    clip_path = tmp_path / "a.MP4"
    clip_path.write_bytes(b"contenido de prueba")
    window = _window_with_video(qtbot, cache_root=cache_root)

    arrancadas = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: arrancadas.append(1) or [],
    )
    window.load_clips([Clip(orden=1, ruta=clip_path, categoria_path=[], fps=30.0)])
    window._clip_durations[0] = 4.0
    window._schedule_thumbnails([0])
    # La extraccion corre en el pool de hilos, asi que `arrancadas` se llena
    # cuando ESE hilo llegue, no al volver de la llamada. Sin esta espera el
    # test es una carrera: contaba 0 corriendo el archivo solo y 1 en la suite
    # completa, donde lo de antes le habia dado tiempo al pool. Un test que
    # depende del orden no dice la verdad (ver tests/ui/conftest.py).
    assert window._thread_pool.waitForDone(2000)
    window._miniaturas_en_vuelo[0] = clip_path      # sigue corriendo

    window._schedule_thumbnails()                   # tanda nueva, generacion nueva

    assert len(arrancadas) == 1                     # no se encimo un segundo
    assert 0 in window._miniaturas_a_rehacer        # pero queda anotado


def test_una_senal_vencida_no_deja_al_clip_marcado_como_corriendo(qtbot, monkeypatch, tmp_path):
    """Si el registro se limpiara solo con las señales vigentes, un clip
    cuya tanda quedo vieja se quedaria marcado como «en vuelo» para
    siempre, y no se le volveria a pedir la tira nunca."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    window.load_clips([Clip(orden=1, ruta=tmp_path / "a.MP4", categoria_path=[], fps=30.0)])
    window._miniaturas_en_vuelo[0] = tmp_path / "a.MP4"

    window._on_thumbnail_ready(window._thumb_generation - 1, 0, None)

    assert 0 not in window._miniaturas_en_vuelo


# --- lo que se corre (o se tira) al quitar un bin ----------------------


def test_quitar_un_bin_tira_la_generacion_de_proxies_en_curso(qtbot, monkeypatch, tmp_path):
    """`_on_proxy_generado` engancha con `self.clips[index]`, y quitar un bin
    corre los indices. Sin tirar la tanda, un proxy recien generado se
    enganchaba al clip EQUIVOCADO -- y entre dos tomas de la misma camara la
    validacion cuadro a cuadro calza, asi que pasaba en silencio. Es el mismo
    modo de fallo que ya estaba documentado para `_proxy_generacion_de`."""
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path)
    # ffmpeg se queda trabado a proposito: sin esto los tres trabajos
    # terminan antes de que se quite el bin, la tanda se cierra sola y el
    # test pasa con o sin el arreglo. (Paso: la primera version de este test
    # no probaba nada.)
    suelta = threading.Event()

    def generar_lento(original, carpeta, **kwargs):
        suelta.wait(5)
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = proxy_gen.ruta_de_proxy(original, carpeta)
        destino.write_bytes(b"proxy")
        return destino

    monkeypatch.setattr(proxy_gen, "generar", generar_lento)
    nombre = window.bins.to_list()[0]["nombre"]
    window.generar_proxies_de_bin(nombre)
    assert window._generando_proxies is not None
    generacion_vieja = window._generacion_de_proxies

    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QMessageBox.question",
        lambda *a, **k: QMessageBox.StandardButton.Yes,
    )
    try:
        window._on_bin_quitado(nombre)

        assert window._generando_proxies is None
        assert window._generacion_de_proxies != generacion_vieja
    finally:
        suelta.set()
        _esperar_generacion(window)


def test_quitar_un_bin_corre_las_portadas_en_vuelo(qtbot, monkeypatch, tmp_path):
    """Van por indice igual que todo lo demas. Sin correrlas, el clip que
    hereda un indice «ocupado» se salta su extraccion: la app cree que ya se
    le esta sacando la tira."""
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path, cuantos=3)
    nombre = window.bins.to_list()[0]["nombre"]
    # se quita el bin entero, asi que lo que quede tiene que quedar limpio
    window._miniaturas_en_vuelo = {0: Path("/a.MP4"), 2: Path("/c.MP4")}
    window._miniaturas_a_rehacer = {2}
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QMessageBox.question",
        lambda *a, **k: QMessageBox.StandardButton.Yes,
    )

    window._on_bin_quitado(nombre)

    assert window._miniaturas_en_vuelo == {}
    assert window._miniaturas_a_rehacer == set()


def test_cerrar_la_ventana_corta_la_generacion_en_vez_de_esperarla(qtbot, monkeypatch, tmp_path):
    """El pool es hijo de la ventana, asi que su destructor espera a que
    termine TODO lo encolado. Con 23 clips por delante eso son minutos de app
    congelada al cerrar, sin decir por que."""
    from PySide6.QtGui import QCloseEvent
    window, _ = _bin_para_generar(qtbot, monkeypatch, tmp_path, cuantos=3)
    arrancadas = []
    suelta = threading.Event()

    def generar_lento(original, carpeta, cancelado=None, **kwargs):
        arrancadas.append(original.name)
        while not suelta.wait(0.01):
            if cancelado is not None and cancelado():
                raise proxy_gen.Interrumpido("cancelado")
        return proxy_gen.ruta_de_proxy(original, carpeta)

    monkeypatch.setattr(proxy_gen, "generar", generar_lento)
    nombre = window.bins.to_list()[0]["nombre"]
    window.generar_proxies_de_bin(nombre)
    qtbot.waitUntil(lambda: bool(arrancadas), timeout=3000)

    window.closeEvent(QCloseEvent())     # no se debe quedar colgado aqui
    suelta.set()

    assert window._generando_proxies is None or window._generando_proxies["cancelado"]
    assert len(arrancadas) == 1          # los otros dos ni empezaron


def test_deshacer_todo_devuelve_el_proyecto_a_como_estaba(qtbot):
    """De la auditoria del 2026-08-10: 40 secuencias al azar de clasificar,
    marcar estado y poner in/out, deshechas hasta el fondo.

    `HistoryEntry` guarda solo los CAMPOS que cada accion toco, y esa
    decision es la que hace que revertir «Cocina → 6 clips» no se lleve
    puesto el pick que se marco despues. Una regresion ahi no se nota
    clip por clip: se nota cuando `⌘Z` deja el proyecto en un estado que
    nunca existio.
    """
    import random
    aleatorio = random.Random(11)

    def foto(ventana):
        return [(list(c.categoria_path), c.flag, c.in_frame, c.out_frame)
                for c in ventana.clips]

    for _ in range(40):
        window = _window_with_video(qtbot, rooms=("Sala", "Cocina", "Bano"))
        window.load_clips([
            Clip(orden=i + 1, ruta=Path(f"/m/C{i}.MP4"), categoria_path=[], fps=30.0)
            for i in range(6)
        ])
        inicial = foto(window)

        for _ in range(aleatorio.randint(1, 12)):
            window.current_index = aleatorio.randrange(len(window.clips))
            accion = aleatorio.choice(["cuarto", "estado", "inout", "escalera"])
            if accion == "cuarto":
                window._apply_categoria_to_targets(
                    [aleatorio.choice(["Sala", "Cocina", "Bano"])]
                )
            elif accion == "estado":
                window.handle_key_press(aleatorio.choice(["p", "x", "s"]))
            elif accion == "inout":
                window.handle_key_press(aleatorio.choice(["i", "o", "u"]))
            else:
                window._mover_en_la_escalera(aleatorio.choice([1, -1]))

        while window.history.can_undo():
            window.undo()

        assert foto(window) == inicial


def test_los_clips_conservan_su_orden_aunque_se_sondeen_en_paralelo(qtbot, monkeypatch, tmp_path):
    """`ffprobe` corre en varios hilos para no congelar la ventana al
    importar, pero el orden de los clips es el que se ve en la hoja y el que
    viaja al manifest: si llegaran en el orden en que terminan, el clip 001
    seria cualquiera."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    import random as _random

    def sondeo_desordenado(video):
        # los ultimos terminan primero, que es el peor caso para el orden
        time.sleep(0.02 * (1 - int(video.stem[-2:]) / 20))
        return {"fps": 30.0, "duration_frames": 60, "width": 1920, "height": 1080,
                "rotation": 0, "has_audio": True}

    monkeypatch.setattr(window, "_probe_clip", sondeo_desordenado)
    archivos = [tmp_path / f"C{i:04d}.MP4" for i in range(20)]
    for a in archivos:
        a.write_bytes(b"x")

    clips, _ = window._medir(archivos)

    assert [c.ruta.name for c in clips] == [a.name for a in archivos]
    assert [c.orden for c in clips] == list(range(1, 21))


def test_un_archivo_ilegible_no_corta_la_tanda_ni_corre_los_indices(qtbot, monkeypatch, tmp_path):
    """Con el sondeo en paralelo, una excepcion adentro del pool cortaria
    TODA la importacion. Se atrapa por archivo."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")

    def a_veces_revienta(video):
        if video.stem.endswith("1"):
            raise RuntimeError("este no se puede leer")
        return {"fps": 30.0, "duration_frames": 60, "width": 1920, "height": 1080,
                "rotation": 0, "has_audio": True}

    monkeypatch.setattr(window, "_probe_clip", a_veces_revienta)
    archivos = [tmp_path / f"C{i:04d}.MP4" for i in range(4)]
    for a in archivos:
        a.write_bytes(b"x")

    clips, medidas = window._medir(archivos)

    assert [c.ruta.name for c in clips] == ["C0000.MP4", "C0002.MP4", "C0003.MP4"]
    # y las medidas van por el indice NUEVO, sin huecos del que se salto
    assert sorted(medidas["duraciones"]) == [0, 1, 2]


# --- modo horizontal: el visor sin la hoja al lado -----------------------
#
# Ver `docs/superpowers/specs/2026-08-15-modo-horizontal-design.md`.


def _ventana_con_clip_horizontal(qtbot, ancho=1600, alto=900):
    window = _window_with_video(qtbot)
    window.resize(ancho, alto)
    window.load_clips([Clip(orden=1, ruta=Path("/c/H.MP4"), categoria_path=[],
                            fps=30.0)])
    window._clip_sizes = {0: (3840, 2160)}
    window.show()
    qtbot.waitExposed(window)
    if window._modo_hoja:
        window.alternar_modo_hoja()       # a modo clip, que es donde aplica
    window._resize_video_stage()
    return window


def test_el_modo_horizontal_esconde_la_hoja_y_le_da_su_ancho_al_video(qtbot):
    """Lo que el modo existe para hacer, en numeros.

    Un 16:9 a toda altura pide 1493 px de ancho y solo hay 939 con la hoja
    al lado, asi que el visor queda alto y angosto y mpv rellena con negro.
    Sin la hoja son 1344 -- el doble de area de imagen.
    """
    window = _ventana_con_clip_horizontal(qtbot)
    antes = window.video_stage.width()

    window.set_modo_horizontal(True)

    assert window.clip_sheet.isHidden()
    assert window.video_stage.width() > antes
    # el ancho es exactamente lo que dejan el rail y la columna de estado
    assert window.video_stage.width() == (
        window.width() - theme.RAIL_WIDTH - theme.TOOLCOL_WIDTH
    )


def test_el_modo_horizontal_deja_el_rail_y_el_estado_del_clip(qtbot):
    """Es el punto medio entre la hoja al lado y `F`: lo unico que se va son
    las miniaturas, que es lo que no estas mirando toma por toma."""
    window = _ventana_con_clip_horizontal(qtbot)

    window.set_modo_horizontal(True)

    assert not window.room_rail.isHidden()
    assert not window.tool_column.isHidden()
    assert not window.title_bar.isHidden()
    assert not window.status_bar.isHidden()


def test_en_modo_hoja_la_hoja_se_ve_aunque_el_visor_vaya_ancho(qtbot):
    """Sin hoja no hay modo hoja. El modo horizontal solo habla de lo que
    pasa en modo clip."""
    window = _ventana_con_clip_horizontal(qtbot)
    window.set_modo_horizontal(True)
    assert window.clip_sheet.isHidden()

    window.alternar_modo_hoja()

    assert not window.clip_sheet.isHidden()


def test_salir_de_solo_video_no_devuelve_la_hoja_que_el_modo_escondio(qtbot):
    """La regla de visibilidad vivia repartida entre los dos modos que
    esconden paneles. Con un tercero en la mezcla, `F` y de vuelta traia la
    hoja que el modo horizontal acababa de esconder.

    Se comprueba la HOJA y no el ancho del visor: el ancho despues de un ida
    y vuelta de `F` con un clip horizontal esta contaminado por un trinquete
    que ya existe en master --la ventana crece de 1600 a 1800 px y no
    encoge-- y que no es de este modo. Va anotado aparte.
    """
    window = _ventana_con_clip_horizontal(qtbot)
    window.set_modo_horizontal(True)

    window.alternar_solo_video()          # F
    window.alternar_solo_video()          # y de vuelta

    assert window.clip_sheet.isHidden()
    assert window.modo_horizontal() is True


def test_solo_video_sigue_ganandole_al_modo_horizontal(qtbot):
    window = _ventana_con_clip_horizontal(qtbot)
    window.set_modo_horizontal(True)

    window.alternar_solo_video()

    assert window.clip_sheet.isHidden()
    assert window.room_rail.isHidden()
    assert window.video_stage.width() == window.width()


def test_apagar_el_modo_horizontal_devuelve_la_hoja(qtbot):
    window = _ventana_con_clip_horizontal(qtbot)
    window.set_modo_horizontal(True)

    window.set_modo_horizontal(False)

    assert not window.clip_sheet.isHidden()


def test_el_interruptor_de_la_barra_avisa_y_restaurar_no(qtbot):
    """Restaurar un proyecto no puede disparar el guardado que lo puso."""
    window = _ventana_con_clip_horizontal(qtbot)
    avisos = []
    window.title_bar.modo_horizontal_cambiado.connect(avisos.append)

    window.set_modo_horizontal(True)       # como al restaurar
    assert avisos == []
    assert window.title_bar.visor_button.isChecked()

    window.title_bar.visor_button.click()              # como el usuario
    assert avisos == [False]
    assert window.modo_horizontal() is False


def test_solo_video_y_volver_no_infla_la_ventana(qtbot):
    """El trinquete: `setFixedWidth` fija tambien el MINIMO.

    Saliendo de `F`, el visor venia anclado al ancho de la ventana entera y
    apenas volvian el rail y la columna ese ancho se sumaba al minimo de
    ellos: la ventana crecia de 1600 a 1800 px y no encogia nunca. Cada `F`
    le comia un pedazo mas.

    Con material VERTICAL no se veia --el visor ya es angosto y nunca llega
    a ser el piso-- asi que solo aparece con material horizontal, que es
    justo donde el ancho ya escaseaba.
    """
    window = _ventana_con_clip_horizontal(qtbot)
    antes = window.width()

    window.alternar_solo_video()          # F
    window.alternar_solo_video()          # y de vuelta

    assert window.width() == antes


def test_el_trinquete_tampoco_aparece_con_un_clip_vertical(qtbot):
    window = _ventana_con_clip_horizontal(qtbot)
    window._clip_sizes = {0: (2160, 3840)}
    window._resize_video_stage()
    antes = window.width()

    window.alternar_solo_video()
    window.alternar_solo_video()

    assert window.width() == antes


def test_apagar_el_modo_ancho_no_infla_la_ventana(qtbot):
    """El MISMO trinquete de `F`, en el camino que se quedó sin el arreglo.

    Con el modo ancho puesto el visor queda anclado a 1344 px, y ese ancho
    es tambien su MINIMO. Al apagarlo la hoja vuelve ANTES de que se
    recalcule, asi que por un instante el minimo de la ventana es
    `rail + columna + 1344 + minimo de la hoja` -- y Qt la crece hasta ahi y
    no la vuelve a encoger. Cada vuelta la crece otro tanto: medido en Mac,
    1512 -> 1878 -> 1982 px, o sea mas ancha que la pantalla.
    """
    window = _ventana_con_clip_horizontal(qtbot)
    antes = window.width()

    window.set_modo_horizontal(True)
    window.set_modo_horizontal(False)

    assert window.width() == antes


def test_el_modo_ancho_no_infla_ni_dando_varias_vueltas(qtbot):
    """El trinquete se acumula: una vuelta sola podria pasar por casualidad."""
    window = _ventana_con_clip_horizontal(qtbot)
    antes = window.width()

    for _ in range(3):
        window.set_modo_horizontal(True)
        window.set_modo_horizontal(False)

    assert window.width() == antes


def test_apagar_el_modo_ancho_sin_clips_tampoco_infla(qtbot):
    """Sin material el aspecto se supone 16:9, o sea que el visor pide igual
    de ancho -- y la app abre sin clips."""
    window = _window_with_video(qtbot)
    window.resize(1600, 900)
    window.show()
    qtbot.waitExposed(window)
    if window._modo_hoja:
        window.alternar_modo_hoja()
    window._resize_video_stage()
    antes = window.width()

    window.set_modo_horizontal(True)
    window.set_modo_horizontal(False)

    assert window.width() == antes


def test_la_ventana_se_puede_achicar_con_material_horizontal(qtbot):
    """Agrandar la ventana no puede ser de un solo sentido.

    `setFixedWidth` fija el minimo del visor, y con material horizontal ese
    minimo es casi toda la ventana: agrandabas a 1500 y ya no podias volver
    a 1200 -- el minimo de la ventana se habia quedado en el ancho de antes.
    Con material vertical no pasaba, porque ahi el visor nunca es el piso, y
    por eso el bug vivio sin que nadie lo viera.
    """
    window = _ventana_con_clip_horizontal(qtbot, ancho=1200)

    window.resize(1500, 900)
    window.resize(1000, 900)

    assert window.width() == 1000


def test_la_ventana_se_puede_achicar_con_el_modo_ancho_puesto(qtbot):
    window = _ventana_con_clip_horizontal(qtbot, ancho=1200)
    window.set_modo_horizontal(True)

    window.resize(1500, 900)
    window.resize(1000, 900)

    assert window.width() == 1000


def test_el_boton_ancho_no_se_ofrece_en_la_hoja(qtbot):
    """Un control que no puede hacer nada no se deja apretable.

    El modo ancho solo habla de lo que pasa en modo CLIP (spec §3), y la app
    ABRE en la hoja: apretarlo ahi no movia un pixel. Y como el boton
    tampoco se veia hundido, dos clics lo dejaban apagado mientras Bruno
    creia haberlo prendido.
    """
    window = _ventana_con_clip_horizontal(qtbot)
    assert window.title_bar.visor_button.isEnabled()

    window.alternar_modo_hoja()          # ⇥, a la hoja
    assert not window.title_bar.visor_button.isEnabled()

    window.alternar_modo_hoja()          # y de vuelta al visor
    assert window.title_bar.visor_button.isEnabled()


# ---------------------------------------------------------------------------
# Los cuartos más allá del nueve
# (spec 2026-08-20-cuartos-mas-alla-del-nueve-design.md)
# ---------------------------------------------------------------------------


def _window_con_cuartos(qtbot, cuartos, clips=4) -> MainWindow:
    window = _window(qtbot, rooms=tuple(cuartos))
    window.resize(1400, 900)
    window.load_clips([
        Clip(orden=i + 1, ruta=Path(f"/tmp/C{i:04d}.MP4"), categoria_path=[], fps=30.0)
        for i in range(clips)
    ])
    return window


def test_la_s_pone_el_ultimo_cuarto_que_usaste(qtbot):
    """El caso que Bruno reprodujo el 2026-08-20: le pones «Alberca» al clip
    2, te mueves al clip 7, aprietas `S`, y te ponía «Cocina» -- lo que tenía
    el clip 6 de una pasada anterior. `S` copiaba el cuarto del clip de al
    lado hacia atrás, no el último que usaste."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina", "Alberca"], clips=8)
    window.select_clip(5)
    window.handle_key_press("2")              # el clip 6 queda en Cocina
    window.select_clip(1)
    window.handle_key_press("3")              # y ahora uso Alberca

    window.select_clip(6)
    window.handle_key_press("s")

    assert window.clips[6].categoria_path == ["Alberca"]


def test_la_s_sin_haber_usado_ninguno_cae_en_el_clip_anterior(qtbot):
    """Recién abres el proyecto: `S` tiene que servir desde el primer teclazo
    y no quedarse muerta esperando a que uses uno."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.clips[0].categoria_path = ["Cocina"]

    window.select_clip(1)
    window.handle_key_press("s")

    assert window.clips[1].categoria_path == ["Cocina"]


def test_deshacer_no_mueve_lo_que_la_s_va_a_poner(qtbot):
    """`⌘Z` revierte el dato, no tu intención. Si deshacer lo moviera,
    cambiaría en silencio lo que la siguiente tecla va a hacer."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)
    window.handle_key_press("2")              # Cocina
    window.undo()

    window.select_clip(2)
    window.handle_key_press("s")

    assert window.clips[2].categoria_path == ["Cocina"]


def test_renombrar_el_cuarto_que_la_s_tiene_en_la_mano_lo_sigue(qtbot):
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)
    window.handle_key_press("2")              # Cocina

    window._on_room_renamed("Cocina", "Cocina chica")
    window.select_clip(2)
    window.handle_key_press("s")

    assert window.clips[2].categoria_path == ["Cocina chica"]


def test_borrar_el_cuarto_que_la_s_tiene_en_la_mano_lo_suelta(qtbot):
    """Y `S` vuelve al respaldo, en vez de poner un cuarto que ya no existe
    -- que quedaría clasificado en un cuarto fantasma, como ya pasó con el
    historial."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)
    window.handle_key_press("2")              # Cocina

    window._on_room_removed("Cocina")

    assert window._ultimo_cuarto_usado is None


def test_el_rail_asigna_al_clip_actual(qtbot):
    """`⏎` con una fila del rail enfocada le pone ese cuarto al clip."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(2)

    window.room_rail.room_assign_requested.emit("Cocina")

    assert window.clips[2].categoria_path == ["Cocina"]


def test_asignar_desde_el_rail_cuenta_para_la_s(qtbot):
    """Pasa por el mismo camino que todo lo demás: lo que `S` recuerda es «el
    último que usaste», no por dónde entró."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)

    window.room_rail.room_assign_requested.emit("Cocina")

    assert window._ultimo_cuarto_usado == "Cocina"


def test_asignar_desde_el_rail_entra_al_historial(qtbot):
    """Un segundo camino para asignar seria una asignacion de segunda: no
    registraria, o no avanzaria, y eso no se ve hasta usarla."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)

    window.room_rail.room_assign_requested.emit("Cocina")
    window.undo()

    assert window.clips[0].categoria_path == []


def test_arrastrar_un_cuarto_lo_mueve_de_lugar(qtbot):
    window = _window_con_cuartos(qtbot, ["Fachada", "Sala", "Alberca"], clips=3)

    window.room_rail.room_reordered.emit("Alberca", 0)

    assert window.room_selection.active_rooms() == ["Alberca", "Fachada", "Sala"]


def test_arrastrar_un_cuarto_le_cambia_la_tecla(qtbot):
    """Reordenar ES cambiar qué tecla le toca a cada cuarto -- lo que Bruno
    quiere: poner arriba con lo que va a empezar."""
    window = _window_con_cuartos(qtbot, ["Fachada", "Sala", "Alberca"], clips=3)

    window.room_rail.room_reordered.emit("Alberca", 0)
    window.select_clip(0)
    window.handle_key_press("1")

    assert window.clips[0].categoria_path == ["Alberca"]


def test_arrastrar_un_cuarto_no_le_cambia_el_cuarto_a_ningun_clip(qtbot):
    """El gesto mueve el cuarto de lugar y NADA más. Misma regla que el
    arrastre de clips entre bins, y por el mismo motivo: con dos significados
    en el mismo gesto, un arrastre mal soltado cambia el dato que más trabajo
    cuesta."""
    window = _window_con_cuartos(qtbot, ["Fachada", "Sala", "Alberca"], clips=3)
    window.select_clip(0)
    window.handle_key_press("2")               # Sala
    antes = [list(c.categoria_path) for c in window.clips]

    window.room_rail.room_reordered.emit("Alberca", 0)

    assert [list(c.categoria_path) for c in window.clips] == antes


def test_arrastrar_un_cuarto_reacomoda_la_hoja(qtbot):
    """Un solo orden en toda la app: el rail y la hoja no pueden decir cosas
    distintas."""
    window = _window_con_cuartos(qtbot, ["Fachada", "Sala", "Alberca"], clips=3)

    window.room_rail.room_reordered.emit("Alberca", 0)

    assert window.clip_sheet._room_order == ["Alberca", "Fachada", "Sala"]
