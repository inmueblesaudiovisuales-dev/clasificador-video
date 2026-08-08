# src/clasificador_video/app.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication, QMessageBox

from clasificador_video.autosave import load_session
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow
from clasificador_video.ui.theme import build_stylesheet

SESSION_PATH = Path.home() / ".clasificador_video" / "sesion.json"


def configure_gl_surface_format() -> None:
    """El API de render de mpv (ui/video_widget.py) necesita un contexto
    OpenGL Core >= 3.3 -- el perfil de compatibilidad que Qt usa por
    default en macOS no alcanza (mpv registra "need >= OpenGL 3.0 for
    core rectangle texture support" y no dibuja nada). Debe llamarse
    antes de crear la QApplication: PySide6 usa este formato como
    default para todo QOpenGLWidget creado despues.
    """
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
    QSurfaceFormat.setDefaultFormat(fmt)


def _rebuild_room_selection(rooms: list[str]) -> RoomSelection:
    sel = RoomSelection()
    for room in rooms:
        sel.add(room)
    return sel


def _aplanar_categoria(path: list) -> list[str]:
    """Sesiones guardadas antes de la F3 pueden traer `["Recámara 1", "Baño"]`.

    Se conserva el CUARTO PADRE, que sigue existiendo en el rail, y se
    descarta el subcuarto, que ya no es representable. Tirar el clip entero
    o dejarlo sin clasificar seria peor: el editor ya tomo esa decision.
    """
    return [str(path[0])] if path else []


def _clip_from_dict(d: dict) -> Clip:
    return Clip(
        orden=d["orden"],
        ruta=Path(d["ruta"]),
        categoria_path=_aplanar_categoria(list(d.get("categoria_path") or [])),
        fps=d["fps"],
        in_frame=d.get("in_frame"),
        out_frame=d.get("out_frame"),
        flag=d.get("flag", "none"),
        ruta_proxy=Path(d["ruta_proxy"]) if d.get("ruta_proxy") else None,
    )


def _restore_session(window: MainWindow, session_path: Path) -> None:
    data = load_session(session_path)
    if data is None:
        return
    if (
        QMessageBox.question(
            None, "Sesión guardada",
            "Se encontró una sesión sin terminar. ¿Recuperarla?",
        )
        != QMessageBox.Yes
    ):
        return
    window.room_selection = _rebuild_room_selection(data.get("rooms", []))
    # `category_tree` de sesiones viejas se ignora a proposito: los
    # subcuartos murieron en la F3 y los paths se aplanan al cuarto padre.
    window._router = KeyboardRouter(active_rooms=window.room_selection.active_rooms())
    window.load_clips([_clip_from_dict(d) for d in data.get("clips", [])])
    window._schedule_thumbnails()


def arrancar(
    video_factory: Callable[..., object] | None = None,
    session_path: Path | None = None,
) -> MainWindow:
    """Construye la ventana principal, lista para trabajar.

    Ya no hay paso previo de "elige los cuartos": la app abre con el rail
    vacio y los cuartos se crean sobre la marcha (DECISIONES.md, "Cuartos:
    planos, sin techo, sin configuracion inicial"). Por eso tampoco puede
    devolver None: no hay nada que cancelar.
    """
    if session_path is None:
        session_path = SESSION_PATH
    window = MainWindow(
        project_name="Shooting sin nombre",
        room_selection=RoomSelection(),
        video_factory=video_factory,
    )
    window.session_path = session_path
    _restore_session(window, session_path)
    window.resize(1100, 700)
    return window


def main() -> None:
    if QApplication.instance() is None:
        configure_gl_surface_format()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    window = arrancar()
    window.show()
    if window.clips:
        window.video_widget.open_clip(window.clips[0].ruta)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
