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

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

from clasificador_video import preferencias, proyecto, proyecto_colaborativo
from clasificador_video.autosave import load_session
from clasificador_video.bins import BinTree
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip
from clasificador_video.recientes import Recientes
from clasificador_video.rooms import RoomSelection
from clasificador_video.units import UnitSelection
from clasificador_video.thumbnails import borrar_cache, default_cache_root, tamano_del_cache
from clasificador_video.ui.main_window import MainWindow
from clasificador_video.ui.pantalla_config import PantallaConfig, _formatear_bytes
from clasificador_video.ui.pantalla_de_carga import PantallaDeCarga
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


def _rebuild_unit_selection(units: list[str]) -> UnitSelection:
    sel = UnitSelection()
    for unidad in units:
        sel.add(unidad)
    return sel


def _aplanar_categoria(path: list, hay_unidades: bool) -> list[str]:
    """Sesiones guardadas antes de la F3 pueden traer `["Recámara 1", "Baño"]`
    -- un subcuarto, que ya no es representable, y se descarta conservando
    el CUARTO PADRE.

    Con unidades, un `categoria_path` de 2 elementos deja de ser ese caso
    viejo: es `[unidad, cuarto]` legitimo, y aplanarlo perderia el cuarto
    de cada clip en silencio apenas se reabriera el proyecto. `hay_unidades`
    -- si el documento declara `"units"` no vacio -- es lo unico que
    distingue un caso del otro: la forma de la lista es identica en los dos.
    """
    if not path:
        return []
    if hay_unidades:
        return [str(elemento) for elemento in path[:2]]
    return [str(path[0])]


def _clip_from_dict(d: dict, hay_unidades: bool) -> Clip:
    """Un clip desde el JSON. **Truena** si el dato no sirve -- ver `_clips_de`,
    que es quien atrapa: aqui adentro no se puede decidir si un proyecto a
    medio corromper se abre igual o no se abre.

    `int` y `float` no son adorno: sin ellos un `"fps": "treinta"` entra sin
    quejarse y revienta mucho despues, al dividir, con la ventana ya armada.
    """
    return Clip(
        orden=int(d["orden"]),
        ruta=Path(d["ruta"]),
        categoria_path=_aplanar_categoria(list(d.get("categoria_path") or []), hay_unidades),
        fps=float(d["fps"]),
        in_frame=d.get("in_frame"),
        out_frame=d.get("out_frame"),
        flag=d.get("flag", "none"),
        ruta_proxy=Path(d["ruta_proxy"]) if d.get("ruta_proxy") else None,
    )


def _clips_de(data: dict) -> list[Clip] | None:
    """Los clips del proyecto, o `None` si alguno no se puede leer.

    Se arman ANTES de construir la ventana, y por eso esto existe: si
    reventaran a mitad del armado, el error saldria dentro de un slot de Qt
    --el clic en una fila de la lista-- y una excepcion sin atrapar ahi
    **aborta el proceso**. Bruno vería la app cerrarse sola por elegir un
    archivo. Devolviendo `None` se toma el mismo camino que un archivo
    ilegible, que ya se dice bien.

    Todo o nada, no clip por clip: un proyecto al que le faltan tres clips en
    silencio es peor que uno que no abre, porque el trabajo de esos tres
    desaparece sin que nadie se entere.
    """
    crudos = data.get("clips")
    if crudos is None:
        return []
    if not isinstance(crudos, list):
        return None
    hay_unidades = bool(data.get("units"))
    try:
        return [_clip_from_dict(d, hay_unidades) for d in crudos]
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def _mapa_por_clip(crudo, convertir) -> dict:
    """Un `{indice: valor}` del JSON, saltándose lo que no se entiende.

    Aqui SI se descarta entrada por entrada, al reves que con los clips. La
    diferencia es qué se pierde: sin el tamaño de un clip su tarjeta cae en
    16:9 y se ve raro --recuperable, y a la vista--, mientras que un clip
    perdido se lleva su clasificacion sin dejar rastro.

    Y no revienta: esto corre dentro de un slot de Qt, donde una excepcion
    sin atrapar aborta el proceso.
    """
    limpio = {}
    for llave, valor in (crudo or {}).items() if isinstance(crudo, dict) else ():
        try:
            limpio[int(llave)] = convertir(valor)
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return limpio


def _guias_por_unidad_de(data: dict) -> dict:
    """Las guias de edicion del documento, por unidad.

    Formato nuevo: `guias_por_unidad` (una entrada por unidad, `""` = «sin
    unidad»). Formato viejo: `guia` a secas, que es la de «sin unidad» de un
    proyecto sin unidades. Un documento sin ninguna de las dos, o con basura,
    da `{}` -- quedarse sin guia es una molestia, no un proyecto que no abre.
    """
    guias = data.get("guias_por_unidad")
    if isinstance(guias, dict) and guias:
        return {str(u): g for u, g in guias.items() if isinstance(g, dict)}
    guia = data.get("guia")
    if isinstance(guia, dict):
        return {"": guia}
    return {}


def _poblar_ventana(window: MainWindow, data: dict, clips: list[Clip]) -> None:
    """Arma la ventana desde el dict de un proyecto.

    Los `clips` llegan ya armados y no se sacan de `data` aqui: armarlos
    puede fallar, y tiene que fallar ANTES de que exista la ventana (ver
    `_clips_de`).

    Salio de `_restore_session`, que hacia esto Y ademas preguntaba si
    recuperar la sesion escondida. Abrir un proyecto no pregunta nada, asi
    que las dos cosas se separaron en vez de copiarse: dos copias de este
    armado se desincronizan, y la mitad que se quede vieja deja la ventana
    sin la mitad del proyecto.
    """
    window.project_name = str(data.get("proyecto") or "Shooting sin nombre")
    rooms = data.get("rooms")
    window.room_selections = {"": _rebuild_room_selection(
        [str(r) for r in rooms] if isinstance(rooms, list) else []
    )}
    units = data.get("units")
    window.unit_selection = _rebuild_unit_selection(
        [str(u) for u in units] if isinstance(units, list) else []
    )
    rooms_por_unidad = data.get("rooms_por_unidad")
    if isinstance(rooms_por_unidad, dict):
        for nombre_unidad in window.unit_selection.active_rooms():
            crudos = rooms_por_unidad.get(nombre_unidad)
            window.room_selections[nombre_unidad] = _rebuild_room_selection(
                [str(r) for r in crudos] if isinstance(crudos, list) else []
            )
    window.room_selection = window.room_selections[""]
    window._unidad_activa = None
    # `category_tree` de proyectos viejos se ignora a proposito: los
    # subcuartos murieron en la F3 y los paths se aplanan al cuarto padre.
    window._router = KeyboardRouter(active_rooms=window.room_selection.active_rooms())
    window.load_clips(clips, construir_hoja=False)
    # un proyecto sin la llave "bins" -- porque es de antes de que
    # existieran -- no se pierde: todo el material cae en un bin unico.
    window.bins = BinTree.desde_sesion(
        data.get("bins"), rutas=[c.ruta for c in window.clips]
    )
    # ANTES de las miniaturas: la duracion decide si se extrae la tira de
    # 12 cuadros o un solo frame, y el tamaño decide la forma de la tarjeta.
    window._clip_sizes = _mapa_por_clip(
        data.get("tamanos"), lambda t: (int(t[0]), int(t[1]))
    )
    window._clip_durations = _mapa_por_clip(data.get("duraciones"), float)
    window._clip_rotations = _mapa_por_clip(data.get("rotaciones"), int)
    # Lo que hace falta para reencontrar el material si el proyecto se abre
    # en otra computadora. Va DESPUES de `load_clips`, que los limpia --van
    # por indice de clip-- y por eso no se puede adelantar. Llega a tiempo
    # igual: el autoguardado que `load_clips` dejo armado tiene 400 ms de
    # debounce y no corre hasta que esta funcion devuelve.
    window._relativas = _mapa_por_clip(data.get("relativas"), str)
    window._bytes_guardados = _mapa_por_clip(data.get("bytes"), int)
    # Como se veia la hoja. Falta en los proyectos de antes de que existiera,
    # y ahi el default es `True`: agrupado por cuarto, que es como se
    # comportaba. `is not False` y no `bool(...)`: un `null` o una cadena
    # rara en el archivo no pueden desagrupar la hoja sin que nadie lo pida.
    window.set_agrupar_por_cuarto(data.get("agrupar_por_cuarto") is not False)
    window.set_modo_horizontal(data.get("modo_horizontal") is True)
    # Y donde van los proxies nuevos. Falta en todo proyecto anterior al
    # 2026-08-25, y ahi `None` significa «nunca me preguntaron»: se escribe
    # donde se escribia y se sigue buscando en los tres lugares.
    guardada = data.get("carpeta_de_proxies")
    window.set_carpeta_de_proxies(Path(guardada) if guardada else None)
    guardada_icloud = data.get("carpeta_de_icloud")
    window.set_carpeta_de_icloud(Path(guardada_icloud) if guardada_icloud else None)
    # Y las guias de edicion, si este proyecto las armo, por unidad. Falta en
    # todo proyecto anterior al 2026-09-14, y ahi `{}` es lo normal: se abre
    # igual y el boton sigue ahi para armarla. La llave vieja `guia` (una
    # sola, sin unidades) se lee como la de «sin unidad».
    window.restaurar_guias(_guias_por_unidad_de(data))
    # Unica construccion de la hoja: load_clips (arriba) la difirio con
    # construir_hoja=False porque todavia no teniamos tamaños/duraciones/
    # rotaciones reales -- ya los tenemos, aqui se construye una vez con
    # los datos correctos desde el principio.
    window._refresh_sheet(force_rebuild=True)
    # Que unidades quedaron colapsadas en el rail (spec 2026-09-21 S3).
    # Falta en todo proyecto de antes de hoy, y ahi el default es "ninguna"
    # -- se abre exactamente como se veia antes de que esto existiera.
    # DESPUES de `_refresh_sheet`, que es lo que arma las bandas del rail:
    # colapsar una banda que todavia no existe no haria nada.
    colapsadas = data.get("unidades_colapsadas")
    window.room_rail.set_unidades_colapsadas(
        [str(u) for u in colapsadas] if isinstance(colapsadas, list) else []
    )
    window._resize_video_stage()
    # Revisar PRIMERO y pedir las portadas cuando se sepa qué hay (spec §5).
    # Al revés --que era como estaba-- pasaban las dos cosas malas juntas: la
    # revisión se encolaba detrás de 132 extracciones y el aviso no llegaba
    # nunca, y esas 132 extracciones eran contra archivos que no existen.
    window.revisar_media(luego_portadas=True)


def abrir_proyecto(ruta: Path, video_factory: Callable[..., object] | None = None,
                   recientes_path: Path | None = None) -> MainWindow | None:
    """Abre un `.cvproj`. `None` si el archivo no se pudo leer o no es uno."""
    data = proyecto.abrir(ruta)
    if not proyecto.es_proyecto(data):
        return None
    if "entrega" in data:
        data.pop("entrega")
        try:
            proyecto.guardar(ruta, data)
        except OSError:
            # El proyecto ya se puede abrir sin ese estado viejo; no se le
            # niega el acceso solo porque el disco no dejó reescribirlo hoy.
            pass
    clips = _clips_de(data)
    if clips is None:
        return None
    window = MainWindow(
        project_name=str(data.get("proyecto") or ruta.stem),
        room_selection=RoomSelection(),
        video_factory=video_factory,
    )
    # el autoguardado que ya existe escribe donde diga `session_path`: al
    # apuntarlo al .cvproj, guardar el proyecto es lo que la app ya hacia
    window.session_path = ruta
    _poblar_ventana(window, data, clips)
    Recientes(recientes_path or RECIENTES_PATH).registrar(ruta, window.project_name)
    return window


def crear_proyecto(ruta: Path, nombre: str,
                   video_factory: Callable[..., object] | None = None,
                   recientes_path: Path | None = None,
                   carpeta_de_icloud: Path | None = None) -> MainWindow | None:
    """Un proyecto nuevo, vacio y YA guardado. `None` si no se pudo escribir.

    Se escribe el archivo antes de devolver la ventana por decision de
    Bruno: nunca existe trabajo sin un archivo donde vivir. Si el disco
    donde lo puso se desconecta despues, el autoguardado avisara --pero al
    menos el proyecto existio.

    Y se COMPRUEBA que exista. Prometer «ya guardado» sin mirar dejaba una
    ventana abierta sobre un archivo que nunca se creo, y un reciente que
    salia apagado desde el primer dia: todo el trabajo de esa tarde vivia
    solo en memoria.

    `carpeta_de_icloud` -- si se pasa -- se guarda con el proyecto antes
    del primer autoguardado (spec 2026-09-23-proyecto-colaborativo-icloud-design.md).
    """
    window = MainWindow(
        project_name=nombre,
        room_selection=RoomSelection(),
        video_factory=video_factory,
    )
    window.session_path = ruta
    if carpeta_de_icloud is not None:
        window.set_carpeta_de_icloud(carpeta_de_icloud)
    window._write_autosave_now()
    window._autosave_pool.waitForDone(2000)
    if not ruta.exists():
        window.deleteLater()
        return None
    Recientes(recientes_path or RECIENTES_PATH).registrar(ruta, nombre)
    return window


def arrancar_inicio(recientes_path: Path | None = None) -> PantallaInicio:
    pantalla = PantallaInicio()
    pantalla.set_recientes(Recientes(recientes_path or RECIENTES_PATH).lista())
    return pantalla


def _migrar_datos(data: dict | None, destino: Path) -> bool:
    """Escribe como proyecto una sesion **ya leida**. `False` si no habia
    nada que migrar, o si sus clips no se pueden leer.

    Existe aparte de `migrar_sesion` para que quien ya tiene el dict no
    tenga que volver a leer el archivo.
    """
    if not data or not data.get("clips"):
        return False
    clips = _clips_de(data)
    if not clips:
        # una sesion cuyos clips no se entienden daria un .cvproj que
        # tampoco se puede abrir: mejor no crearlo y dejar la sesion donde
        # esta, que es donde Bruno la puede rescatar a mano.
        return False
    documento = dict(data)
    documento.setdefault("version", proyecto.VERSION)
    # Las relativas SI se calculan aqui: `rutas_relativas` es lexica, no
    # toca disco, y la sesion vieja trae las rutas y los origenes de sus
    # bins. Dejarlas para «el primer autoguardado con la media conectada»
    # era regalar lo unico que permite reencontrar el material en otra
    # computadora, por un dato que ya estaba ahi.
    bins = BinTree.desde_sesion(data.get("bins"), rutas=[c.ruta for c in clips])
    documento.setdefault("relativas", {
        str(i): r for i, r in proyecto.rutas_relativas(clips, bins).items()
    })
    # Los pesos no: esos si necesitan la media conectada, y los pone el
    # primer autoguardado que la encuentre.
    documento.setdefault("bytes", {})
    proyecto.guardar(destino, documento)
    return True


def migrar_sesion(sesion: Path, destino: Path) -> bool:
    """Convierte la sesion escondida en un proyecto de verdad.

    Bruno tiene material clasificado ahi. La sesion vieja **no se borra**:
    se conserva hasta que el proyecto convertido este a salvo. Borrar lo
    viejo antes de que lo nuevo exista es como se pierden cosas.

    Devuelve False si no habia nada que migrar.
    """
    return _migrar_datos(load_session(sesion), destino)


def _destino_libre(carpeta: Path, nombre: str) -> Path:
    """Un `.cvproj` con ese nombre que no pise nada de lo que ya hay."""
    candidato = carpeta / f"{nombre}{proyecto.EXTENSION}"
    intento = 2
    while candidato.exists():
        candidato = carpeta / f"{nombre} ({intento}){proyecto.EXTENSION}"
        intento += 1
    return candidato


def _hay_sesion_que_migrar(sesion: Path) -> bool:
    """¿Queda material de la version anterior sin convertir?

    Sirve para distinguir «no habia nada» de «habia y no se pudo», que es lo
    unico que decide si hay algo que avisarle a Bruno.
    """
    try:
        data = load_session(sesion)
    except OSError:
        return False
    return bool(data and data.get("clips"))


def _apartado_libre(sesion: Path) -> Path:
    """Donde se guarda la sesion vieja despues de migrarla.

    Sin pisar una anterior: la apartada **es** la copia de respaldo, y hoy
    solo puede haber una, pero eso es una invariante que no esta escrita en
    ningun lado. Si alguna vez hay dos, pisarla borraria la primera.
    """
    candidato = sesion.with_name("sesion.migrada.json")
    intento = 2
    while candidato.exists():
        candidato = sesion.with_name(f"sesion.migrada.{intento}.json")
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
    try:
        data = load_session(sesion)
    except OSError:
        return None
    if not data or not data.get("clips"):
        return None
    nombre = str(data.get("proyecto") or "Proyecto recuperado")
    destino = _destino_libre(carpeta, nombre)
    # TODO ESTO va protegido, y no por prolijidad: corre al arrancar, ANTES
    # de que exista una ventana. Un traceback aqui --`~/Documents` bloqueada
    # por TCC o por iCloud, el disco lleno-- deja a Bruno sin poder entrar a
    # la app, que es infinitamente peor que quedarse sin migrar.
    try:
        if not _migrar_datos(data, destino):
            return None
        # recien ahora, con lo nuevo escrito en disco
        os.replace(sesion, _apartado_libre(sesion))
    except OSError:
        # Si el proyecto se escribio pero la sesion no se pudo apartar, lo
        # escrito se deshace. Sin la marca, cada arranque volveria a
        # convertirla y se acumularian «(2)», «(3)», «(4)»... Deshacerlo no
        # pierde nada --la sesion sigue entera-- y el siguiente arranque lo
        # vuelve a intentar limpio.
        destino.unlink(missing_ok=True)
        return None
    Recientes(recientes_path or RECIENTES_PATH).registrar(destino, nombre)
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
        self.carga = PantallaDeCarga()
        self.inicio.resize(560, 480)
        self.inicio.abrir_pedido.connect(self._abrir)
        self.inicio.nuevo_pedido.connect(self._nuevo)
        self.inicio.abrir_otro_pedido.connect(self._abrir_otro)
        self.inicio.quitar_pedido.connect(self._quitar)
        self.inicio.configuracion_pedida.connect(self._abrir_configuracion)
        self._pantalla_config: PantallaConfig | None = None
        self._inicio_alto_original: int | None = None
        self._refrescar()

    # --- la pantalla ------------------------------------------------------

    def _refrescar(self) -> None:
        self.inicio.set_recientes(Recientes(self._recientes_path).lista())

    def mostrar_inicio(self) -> None:
        self._refrescar()
        self.inicio.show()
        self.inicio.raise_()

    def _abrir_configuracion(self) -> None:
        """La pantalla de configuracion, encima de la pantalla de inicio.

        Copia fiel de `MainWindow._abrir_configuracion`: misma clase, mismas
        señales, no modal por la misma razon (el `exec()` viejo colgaba la
        suite bajo `offscreen`, murio con la F3). Lo unico que cambia es que
        no hay ventana de proyecto de la cual tirar del pool de hilos --
        aqui guardar la preferencia basta, la proxima ventana que se abra ya
        la lee al construirse.
        """
        if self._pantalla_config is None:
            self._pantalla_config = PantallaConfig(self.inicio)
            self._pantalla_config.modo_economico_cambiado.connect(
                preferencias.guardar_modo_economico
            )
            self._pantalla_config.modo_rapido_cambiado.connect(
                preferencias.guardar_modo_rapido
            )
            self._pantalla_config.carpeta_icloud_guardada.connect(
                preferencias.guardar_carpeta_raiz_icloud
            )
            self._pantalla_config.importacion_rapida_pregunta_antes_cambiado.connect(
                preferencias.guardar_importacion_rapida_pregunta_antes
            )
            self._pantalla_config.miniaturas_borrar_pedido.connect(
                self._al_pedir_borrar_miniaturas
            )
            self._pantalla_config.cerrada.connect(self._al_cerrar_configuracion)
        self._pantalla_config.cargar(
            preferencias.modo_economico(), preferencias.modo_rapido(),
            preferencias.importacion_rapida_pregunta_antes(),
        )
        self._pantalla_config.mostrar_peso_de_miniaturas(
            tamano_del_cache(default_cache_root())
        )
        # `PantallaInicio` mide 560x480 -- pensada para la lista de
        # recientes, no para el contenido de configuración, que con sus
        # textos con `wordWrap` pide unos 750px de alto una vez que se le da
        # un ancho razonable (`heightForWidth`, no un tamaño fijo a ojo: si
        # algun dia se le agrega o se le quita una sección, este cálculo se
        # ajusta solo). Los mismos márgenes que usa `MainWindow` (110/80) le
        # quedaban comodos a una ventana maximizada; aquí, sobre una ventana
        # chica, dejaban apenas 340x320 y el contenido se amontonaba encima
        # de sí mismo. Se crece la ventana de inicio lo que haga falta -- y
        # se devuelve a su tamaño de siempre al cerrar Configuración.
        margen = 40
        ancho_contenido = max(self.inicio.width() - 2 * margen, 360)
        alto_contenido = self._pantalla_config.heightForWidth(ancho_contenido) + 20
        alto_necesario = alto_contenido + 2 * margen
        if self.inicio.height() < alto_necesario:
            if self._inicio_alto_original is None:
                self._inicio_alto_original = self.inicio.height()
            self.inicio.resize(self.inicio.width(), alto_necesario)
        self._pantalla_config.setGeometry(
            self.inicio.rect().adjusted(margen, margen, -margen, -margen)
        )
        self._pantalla_config.show()
        self._pantalla_config.raise_()

    def _al_cerrar_configuracion(self) -> None:
        self._pantalla_config.hide()
        if self._inicio_alto_original is not None:
            self.inicio.resize(self.inicio.width(), self._inicio_alto_original)
            self._inicio_alto_original = None

    def _al_pedir_borrar_miniaturas(self) -> None:
        cache_root = default_cache_root()
        peso = _formatear_bytes(tamano_del_cache(cache_root))
        respuesta = QMessageBox.question(
            self.inicio, "Borrar miniaturas",
            f"Vas a borrar {peso} de miniaturas guardadas. Se vuelven a "
            "generar solas la próxima vez que se necesiten -- pero eso "
            "tarda.\n\n¿Borrarlas?",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        borrar_cache(cache_root)
        self._pantalla_config.mostrar_peso_de_miniaturas(0)

    def migrar_lo_viejo(self, sesion: Path | None = None,
                        carpeta: Path | None = None) -> Path | None:
        """Convierte la sesion escondida en proyecto, y lo dice si no pudo.

        Va aqui y no suelto en `main()` porque el aviso necesita una pantalla
        donde ponerse. Que falle no puede impedir entrar a la app: lo peor
        que pasa es que Bruno siga sin migrar, y eso se arregla despues.
        """
        sesion = sesion or SESSION_PATH
        if not _hay_sesion_que_migrar(sesion):
            return None
        destino = migrar_sesion_vieja(sesion=sesion, carpeta=carpeta,
                                      recientes_path=self._recientes_path)
        if destino is None:
            self.inicio.avisar(
                "Tenías material clasificado de la versión anterior y no se "
                "pudo convertir en proyecto. No se perdió nada: sigue "
                f"guardado en {sesion}."
            )
        return destino

    # --- los tres caminos -------------------------------------------------

    def _abrir(self, ruta: Path) -> None:
        self.inicio.callar()
        ventana = abrir_proyecto(Path(ruta), video_factory=self._video_factory,
                                 recientes_path=self._recientes_path)
        if ventana is None:
            self.inicio.avisar(
                f"No se pudo abrir «{Path(ruta).name}». Puede que el archivo "
                "no sea un proyecto del clasificador, o que esté dañado."
            )
            self._refrescar()
            return
        self._tomar(ventana)

    def _nuevo(self) -> None:
        self.inicio.callar()
        eleccion = QMessageBox(self.inicio)
        eleccion.setWindowTitle("Proyecto nuevo")
        eleccion.setText("¿Cómo quieres crear el proyecto?")
        eleccion.setInformativeText(
            "\"Con folio\" arma la carpeta del proyecto sola en iCloud, con "
            "los archivos de Premiere y AE ya listos. \"Usar una carpeta a "
            "mano\" es para pruebas: el cuadro de \"guardar como\" de "
            "siempre."
        )
        con_folio = eleccion.addButton("Con folio…", QMessageBox.ButtonRole.AcceptRole)
        a_mano = eleccion.addButton(
            "Usar una carpeta a mano", QMessageBox.ButtonRole.ActionRole)
        eleccion.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        eleccion.setDefaultButton(con_folio)
        eleccion.exec()
        elegido = eleccion.clickedButton()
        if elegido is a_mano:
            self._nuevo_a_mano()
        elif elegido is con_folio:
            self._nuevo_con_folio()
        # cerrar el cuadro o "Cancelar": no crea nada

    def _nuevo_a_mano(self) -> None:
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
        ventana = crear_proyecto(ruta, ruta.stem,
                                 video_factory=self._video_factory,
                                 recientes_path=self._recientes_path)
        if ventana is None:
            self.inicio.avisar(
                f"No se pudo crear «{ruta.name}» en {ruta.parent}. Elige otra "
                "carpeta, o comprueba que el disco esté conectado."
            )
            return
        self._tomar(ventana)

    def _nuevo_con_folio(self) -> None:
        raiz = preferencias.carpeta_raiz_icloud()
        if raiz is None:
            self.inicio.avisar(
                "Configura primero la carpeta de iCloud, en Configuración."
            )
            return
        folio, ok = QInputDialog.getText(
            self.inicio, "Proyecto nuevo",
            "Folio del proyecto (ej. IAV-2609.10-A):",
        )
        folio = folio.strip()
        if not ok or not folio:
            return
        carpeta_proyecto = proyecto_colaborativo.ruta_del_proyecto(raiz, folio)
        if carpeta_proyecto is None:
            self.inicio.avisar(
                f"«{folio}» no se pudo leer como folio. Revisa el formato "
                "(ej. IAV-2609.10-A) e inténtalo de nuevo."
            )
            return
        confirmar = QMessageBox(self.inicio)
        confirmar.setWindowTitle("Proyecto nuevo")
        confirmar.setText("¿Crear el proyecto aquí?")
        confirmar.setInformativeText(str(carpeta_proyecto))
        crear = confirmar.addButton("Crear aquí", QMessageBox.ButtonRole.AcceptRole)
        confirmar.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        confirmar.setDefaultButton(crear)
        confirmar.exec()
        if confirmar.clickedButton() is not crear:
            return
        carpeta_templates = raiz / proyecto_colaborativo.CARPETA_TEMPLATES
        try:
            resultado = proyecto_colaborativo.crear_carpeta_de_proyecto(
                carpeta_proyecto, carpeta_templates, folio)
        except FileExistsError:
            self.inicio.avisar(
                f"Ya existe una carpeta para «{folio}» en iCloud. Revísala "
                "tú y decide qué hacer -- Clipify no la tocó."
            )
            return
        except FileNotFoundError as exc:
            self.inicio.avisar(f"No se encontró «{exc}». No se creó nada.")
            return
        except OSError:
            self.inicio.avisar(
                f"No se pudo crear «{folio}» en {carpeta_proyecto}. No se creó nada."
            )
            return
        ventana = crear_proyecto(
            resultado.ruta_cvproj, folio, video_factory=self._video_factory,
            recientes_path=self._recientes_path,
            carpeta_de_icloud=resultado.carpeta_proyecto,
        )
        if ventana is None:
            self.inicio.avisar(
                f"No se pudo crear «{folio}» en {resultado.carpeta_proyecto}."
            )
            return
        self._tomar(ventana)

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
        ventana.proyecto_renombrado.connect(
            lambda nuevo: self._al_renombrar(ventana, nuevo))
        self.inicio.hide()
        # La pantalla de carga ANTES de mostrar la ventana: abrir un proyecto
        # grande son unos segundos de portadas, y sin nada en pantalla esos
        # segundos se sienten como un cuelgue. Se va sola en cuanto la
        # ventana esta arriba.
        self.carga.abrir(ventana.project_name, len(ventana.clips))
        QApplication.processEvents()
        ventana.abrir_maximizada()
        QApplication.processEvents()
        self.carga.cerrar()
        # Y NADA de abrir el primer clip aqui. `load_clips` ya lo abrio, y lo
        # abrio bien: por `ruta_de_reproduccion` --o sea con su proxy si
        # valido-- y arrancando al 25%. Volver a abrirlo con la ruta en crudo
        # borra las dos cosas en silencio, y deja al clip donde aterrizas
        # cada vez que abres un proyecto a 530 ms por cuadro atras en vez de
        # 22. Era herencia del `main()` viejo, que armaba la ventana sin
        # pasar por aqui.

    def _al_renombrar(self, ventana: MainWindow, nuevo: str) -> None:
        # `registrar` es un upsert por ruta: no duplica el reciente, lo
        # actualiza. Sin esto, la pantalla de inicio se queda mostrando el
        # nombre viejo hasta que cierras la ventana.
        if ventana.session_path is not None:
            Recientes(self._recientes_path).registrar(ventana.session_path, nuevo)

    def _al_cerrarse(self, ventana: MainWindow) -> None:
        if ventana in self.ventanas:
            self.ventanas.remove(ventana)
        # Se vuelve a registrar AL CERRAR, no solo al abrir: la lista se
        # ordena por esa fecha, y la de abrir es la que menos dice. Abres un
        # proyecto a las 9 y trabajas en el toda la tarde; basta con que a
        # mediodia hayas abierto otro un minuto para que ese otro te quede
        # arriba.
        if ventana.session_path is not None:
            Recientes(self._recientes_path).registrar(
                ventana.session_path, ventana.project_name
            )
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
    coordinador = Coordinador()
    # antes de mostrar nada: si Bruno viene de la version anterior, su
    # material clasificado esta en la sesion escondida y tiene que aparecer
    # en la lista como un proyecto mas. Va DESPUES de construir el
    # coordinador porque si falla, el aviso necesita una pantalla donde
    # ponerse -- y porque un fallo aqui no puede impedir entrar.
    coordinador.migrar_lo_viejo()
    coordinador.mostrar_inicio()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
