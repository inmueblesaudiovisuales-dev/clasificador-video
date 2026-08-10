# src/clasificador_video/app.py
"""El arranque: la pantalla de inicio y los tres caminos que salen de ahí.

Hasta la F4 la app caía directo en la hoja, sobre una sesión escondida que
era siempre la misma. Ahora el proyecto es un archivo con nombre que Bruno
guarda donde quiera, y lo primero que se ve es la lista de los últimos.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from clasificador_video import proyecto
from clasificador_video.autosave import load_session
from clasificador_video.bins import BinTree
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip
from clasificador_video.recientes import Recientes
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow
from clasificador_video.ui.pantalla_inicio import PantallaInicio
from clasificador_video.ui.theme import build_stylesheet

SESSION_PATH = Path.home() / ".clasificador_video" / "sesion.json"
RECIENTES_PATH = Path.home() / ".clasificador_video" / "recientes.json"
# Donde aterriza la sesión vieja al convertirse en proyecto. A la vista y no
# en `~/.clasificador_video/`: la gracia de que el proyecto sea un archivo es
# que Bruno pueda encontrarlo, moverlo y respaldarlo sin nosotros.
CARPETA_DE_MIGRACION = Path.home() / "Documents"


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


def _poblar_ventana(window: MainWindow, data: dict) -> None:
    """Arma la ventana desde el dict de un proyecto.

    Salio de `_restore_session`, que hacia esto Y ademas preguntaba si
    recuperar la sesion escondida. Abrir un proyecto no pregunta nada, asi
    que las dos cosas se separaron en vez de copiarse: dos copias de este
    armado se desincronizan, y la mitad que se quede vieja deja la ventana
    sin la mitad del proyecto.
    """
    window.project_name = str(data.get("proyecto") or "Shooting sin nombre")
    window.room_selection = _rebuild_room_selection(data.get("rooms", []))
    # `category_tree` de proyectos viejos se ignora a proposito: los
    # subcuartos murieron en la F3 y los paths se aplanan al cuarto padre.
    window._router = KeyboardRouter(active_rooms=window.room_selection.active_rooms())
    window.load_clips([_clip_from_dict(d) for d in data.get("clips", [])])
    # un proyecto sin la llave "bins" -- porque es de antes de que
    # existieran -- no se pierde: todo el material cae en un bin unico.
    window.bins = BinTree.desde_sesion(
        data.get("bins"), rutas=[c.ruta for c in window.clips]
    )
    # ANTES de las miniaturas: la duracion decide si se extrae la tira de
    # 12 cuadros o un solo frame, y el tamaño decide la forma de la tarjeta.
    window._clip_sizes = {
        int(i): (int(t[0]), int(t[1])) for i, t in (data.get("tamanos") or {}).items()
    }
    window._clip_durations = {
        int(i): float(s) for i, s in (data.get("duraciones") or {}).items()
    }
    window._clip_rotations = {
        int(i): int(r) for i, r in (data.get("rotaciones") or {}).items()
    }
    # Lo que hace falta para reencontrar el material si el proyecto se abre
    # en otra computadora. Va DESPUES de `load_clips`, que los limpia --van
    # por indice de clip-- y por eso no se puede adelantar. Llega a tiempo
    # igual: el autoguardado que `load_clips` dejo armado tiene 400 ms de
    # debounce y no corre hasta que esta funcion devuelve.
    window._relativas = {
        int(i): str(r) for i, r in (data.get("relativas") or {}).items()
    }
    window._bytes_guardados = {
        int(i): int(b) for i, b in (data.get("bytes") or {}).items()
    }
    window._refresh_sheet(force_rebuild=True)
    window._resize_video_stage()
    window._schedule_thumbnails()


def abrir_proyecto(ruta: Path, video_factory: Callable[..., object] | None = None,
                   recientes_path: Path | None = None) -> MainWindow | None:
    """Abre un `.cvproj`. `None` si el archivo no se pudo leer o no es uno."""
    data = proyecto.abrir(ruta)
    if not proyecto.es_proyecto(data):
        return None
    window = MainWindow(
        project_name=str(data.get("proyecto") or ruta.stem),
        room_selection=RoomSelection(),
        video_factory=video_factory,
    )
    # el autoguardado que ya existe escribe donde diga `session_path`: al
    # apuntarlo al .cvproj, guardar el proyecto es lo que la app ya hacia
    window.session_path = ruta
    _poblar_ventana(window, data)
    window.resize(1100, 700)
    Recientes(recientes_path or RECIENTES_PATH).registrar(ruta, window.project_name)
    return window


def crear_proyecto(ruta: Path, nombre: str,
                   video_factory: Callable[..., object] | None = None,
                   recientes_path: Path | None = None) -> MainWindow:
    """Un proyecto nuevo, vacio y YA guardado.

    Se escribe el archivo antes de devolver la ventana por decision de
    Bruno: nunca existe trabajo sin un archivo donde vivir. Si el disco
    donde lo puso se desconecta despues, el autoguardado fallara --pero al
    menos el proyecto existio.
    """
    window = MainWindow(
        project_name=nombre,
        room_selection=RoomSelection(),
        video_factory=video_factory,
    )
    window.session_path = ruta
    window._write_autosave_now()
    window._autosave_pool.waitForDone(2000)
    window.resize(1100, 700)
    Recientes(recientes_path or RECIENTES_PATH).registrar(ruta, nombre)
    return window


def arrancar_inicio(recientes_path: Path | None = None) -> PantallaInicio:
    pantalla = PantallaInicio()
    pantalla.set_recientes(Recientes(recientes_path or RECIENTES_PATH).lista())
    return pantalla


def migrar_sesion(sesion: Path, destino: Path) -> bool:
    """Convierte la sesion escondida en un proyecto de verdad.

    Bruno tiene material clasificado ahi. La sesion vieja **no se borra**:
    se conserva hasta que el proyecto convertido este a salvo. Borrar lo
    viejo antes de que lo nuevo exista es como se pierden cosas.

    Devuelve False si no habia nada que migrar.
    """
    data = load_session(sesion)
    if not data or not data.get("clips"):
        return False
    data.setdefault("version", proyecto.VERSION)
    # Sin relativas ni pesos: la sesion vieja no los tenia. Los pone el
    # primer autoguardado con la media conectada, que es cuando se pueden
    # medir de verdad.
    data.setdefault("relativas", {})
    data.setdefault("bytes", {})
    proyecto.guardar(destino, data)
    return True


def _destino_libre(carpeta: Path, nombre: str) -> Path:
    """Un `.cvproj` con ese nombre que no pise nada de lo que ya hay."""
    candidato = carpeta / f"{nombre}{proyecto.EXTENSION}"
    intento = 2
    while candidato.exists():
        candidato = carpeta / f"{nombre} ({intento}){proyecto.EXTENSION}"
        intento += 1
    return candidato


def migrar_sesion_vieja(sesion: Path | None = None, carpeta: Path | None = None,
                        recientes_path: Path | None = None) -> Path | None:
    """La sesion escondida se convierte en proyecto, **una sola vez**.

    Devuelve la ruta del proyecto convertido, o `None` si no habia nada que
    convertir. Corre al arrancar, antes de mostrar la pantalla de inicio.

    Despues de guardar lo nuevo, la sesion vieja se APARTA con otro nombre
    --no se borra-- y ese apartado es la marca de que ya se migro. Sin la
    marca, cada arranque volveria a convertirla y el trabajo de hoy quedaria
    pisado por el de antes.
    """
    sesion = sesion or SESSION_PATH
    carpeta = carpeta or CARPETA_DE_MIGRACION
    data = load_session(sesion)
    if not data or not data.get("clips"):
        return None
    nombre = str(data.get("proyecto") or "Proyecto recuperado")
    destino = _destino_libre(carpeta, nombre)
    if not migrar_sesion(sesion, destino):
        return None
    Recientes(recientes_path or RECIENTES_PATH).registrar(destino, nombre)
    # recien ahora, con lo nuevo escrito en disco
    os.replace(sesion, sesion.with_name("sesion.migrada.json"))
    return destino


class Coordinador(QObject):
    """La pantalla de inicio y las ventanas abiertas desde ella.

    Vive aparte de `main()` para poder probar los tres caminos --abrir,
    crear y abrir otro-- sin arrancar la aplicacion entera. No abre ningun
    selector por su cuenta salvo cuando el camino lo pide: la pantalla solo
    avisa con señales y aqui se decide que hacer.
    """

    def __init__(self, recientes_path: Path | None = None,
                 video_factory: Callable[..., object] | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self._recientes_path = recientes_path or RECIENTES_PATH
        self._video_factory = video_factory
        self.ventanas: list[MainWindow] = []
        self.inicio = PantallaInicio()
        self.inicio.resize(560, 480)
        self.inicio.abrir_pedido.connect(self._abrir)
        self.inicio.nuevo_pedido.connect(self._nuevo)
        self.inicio.abrir_otro_pedido.connect(self._abrir_otro)
        self.inicio.quitar_pedido.connect(self._quitar)
        self._refrescar()

    # --- la pantalla ------------------------------------------------------

    def _refrescar(self) -> None:
        self.inicio.set_recientes(Recientes(self._recientes_path).lista())

    def mostrar_inicio(self) -> None:
        self._refrescar()
        self.inicio.show()
        self.inicio.raise_()

    # --- los tres caminos -------------------------------------------------

    def _abrir(self, ruta: Path) -> None:
        ventana = abrir_proyecto(Path(ruta), video_factory=self._video_factory,
                                 recientes_path=self._recientes_path)
        if ventana is None:
            QMessageBox.warning(
                self.inicio, "No se pudo abrir",
                f"No se pudo abrir «{Path(ruta).name}».\n\n"
                "Puede que el archivo no sea un proyecto del clasificador, "
                "o que esté dañado.",
            )
            self._refrescar()
            return
        self._tomar(ventana)

    def _nuevo(self) -> None:
        elegido, _ = QFileDialog.getSaveFileName(
            self.inicio, "Proyecto nuevo", str(Path.home() / "Sin título"),
            f"Proyecto del clasificador (*{proyecto.EXTENSION})",
        )
        if not elegido:
            return
        ruta = Path(elegido)
        if ruta.suffix != proyecto.EXTENSION:
            # el selector de macOS deja borrar la extension, y sin ella el
            # archivo no se reconoce como proyecto la proxima vez
            ruta = ruta.with_name(ruta.name + proyecto.EXTENSION)
        self._tomar(crear_proyecto(ruta, ruta.stem,
                                   video_factory=self._video_factory,
                                   recientes_path=self._recientes_path))

    def _abrir_otro(self) -> None:
        elegido, _ = QFileDialog.getOpenFileName(
            self.inicio, "Abrir proyecto", str(Path.home()),
            f"Proyecto del clasificador (*{proyecto.EXTENSION})",
        )
        if elegido:
            self._abrir(Path(elegido))

    def _quitar(self, ruta: Path) -> None:
        Recientes(self._recientes_path).quitar(Path(ruta))
        self._refrescar()

    # --- el ciclo de vida de las ventanas ---------------------------------

    def _tomar(self, ventana: MainWindow) -> None:
        self.ventanas.append(ventana)
        ventana.cerrada.connect(lambda: self._al_cerrarse(ventana))
        self.inicio.hide()
        ventana.show()
        if ventana.clips:
            ventana.video_widget.open_clip(ventana.clips[0].ruta)

    def _al_cerrarse(self, ventana: MainWindow) -> None:
        if ventana in self.ventanas:
            self.ventanas.remove(ventana)
        # `deleteLater` y no soltar la referencia a secas: esto corre DENTRO
        # del `closeEvent` de la ventana, y destruir ahi el objeto de C++ es
        # de donde salieron varios segfaults de este proyecto. Qt lo borra
        # cuando el evento ya termino.
        ventana.deleteLater()
        self.mostrar_inicio()


def main() -> None:
    if QApplication.instance() is None:
        configure_gl_surface_format()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    # antes de mostrar nada: si Bruno viene de la version anterior, su
    # material clasificado esta en la sesion escondida y tiene que aparecer
    # en la lista como un proyecto mas.
    migrar_sesion_vieja()
    coordinador = Coordinador()
    coordinador.mostrar_inicio()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
