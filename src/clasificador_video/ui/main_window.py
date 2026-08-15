# src/clasificador_video/ui/main_window.py
from __future__ import annotations

import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from clasificador_video import proxy_gen, proyecto, revinculo
from clasificador_video.bins import BinTree, raiz_comun_de
from clasificador_video.filters import FilterState, cola, contar
from clasificador_video.history import History, HistoryEntry
from clasificador_video.ingest import archivos_de_video
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip, Manifest
from clasificador_video.player import SPEED_PROFILES
from clasificador_video.probe import (
    orientacion_de,
    orientacion_predominante,
    probe_clip,
)
from clasificador_video.proxy_match import (
    clip_del_proxy,
    emparejar_con_patron,
    etiqueta_de_resolucion,
    patron_de_proxy,
)
from clasificador_video.rooms import RoomSelection
from clasificador_video.thumbnails import (
    MARCA_DE_COMPLETA,
    cache_dir_for,
    default_cache_root,
    extract_thumbnail,
    extract_thumbnail_strip,
)
from clasificador_video.ui import theme
from clasificador_video.ui.aviso_de_media import (
    ACCION_MEDIA,
    ACCION_PROXIES,
    TONO_ALERTA,
    TONO_FALTA,
    TONO_OK,
    AvisoDeMedia,
    Renglon,
)
from clasificador_video.ui.clip_sheet import SIN_BIN, ClipSheet, ClipThumbnail
from clasificador_video.ui.room_palette import RoomPalette
from clasificador_video.ui.room_rail import RoomRail
from clasificador_video.ui.status_bar import StatusBar
from clasificador_video.ui.title_bar import TitleBar
from clasificador_video.ui.transicion import TransicionDeTarjeta
from clasificador_video.ui.tool_column import ToolColumn
from clasificador_video.ui.video_stage import VideoStage, etiqueta_de_velocidad
from clasificador_video.ui.video_widget import format_timecode

# Donde arranca cada clip. El principio de un recorrido siempre es la camara
# acomodandose, y el frame de portada de la hoja sale del mismo punto
# (DECISIONES.md): al llegar al clip ves lo mismo que viste en la miniatura.
START_PERCENT = 25

# Como se nombra y se pinta cada estado en el historial. Un solo lugar: la F2
# los tenia repartidos en dos diccionarios en linea, y agregar `destacado`
# habria que acordarse de hacerlo en los dos.
# La escalera de estados, de abajo hacia arriba. Es la misma que describe
# DECISIONES.md, y por eso `↑`/`↓` la recorren: subir y bajar es la forma
# natural de moverse por ella sin acordarse de que letra es cada estado.
ESCALERA_DE_ESTADO = ("reject", "none", "pick", "destacado")
ETIQUETAS_DE_ESTADO = {
    "pick": "Pick", "reject": "Reject",
    "destacado": "Destacado", "none": "Sin marcar",
}
COLORES_DE_ESTADO = {
    "pick": theme.PICK_COLOR, "reject": theme.REJECT_COLOR,
    "destacado": theme.STAR_COLOR, "none": theme.TEXT_3,
}


# ---------------------------------------------------------------------------
# Lo que dice la barra de media faltante, palabra por palabra.
#
# Los cuatro textos viven juntos porque lo que importa de ellos es que se
# lean DISTINTO entre sí: son cuatro noticias distintas y confundir dos es
# mentirle a Bruno sobre lo que pasó. «No apareció» es que no hay nada;
# «no coincide» es que sí hay un archivo con ese nombre y NO es el mismo
# --la segunda tarjeta de la Sony, que vuelve a numerar desde `C0001.MP4`--.
# ---------------------------------------------------------------------------

def _cuantos_faltan(n: int) -> str:
    return "1 clip no se encuentra." if n == 1 else f"{n} clips no se encuentran."


def _cuantos_reconectados(n: int) -> str:
    return "1 clip reconectado." if n == 1 else f"{n} clips reconectados."


def _cuantos_no_coinciden(n: int) -> str:
    if n == 1:
        return ("1 clip no coincide: hay un archivo con ese nombre, pero no es "
                "el mismo video. No se conectó.")
    return (f"{n} clips no coinciden: hay archivos con esos nombres, pero no "
            "son los mismos videos. No se conectaron.")


def _cuantos_no_aparecieron(n: int) -> str:
    if n == 1:
        return "1 clip no apareció en esa carpeta."
    return f"{n} clips no aparecieron en esa carpeta."


def _cuantos_se_pelean(n: int) -> str:
    """El archivo SI calzaba -- con los dos. Decir «no es el mismo video»
    seria mentira: lo es, y por eso justamente no se sabe de cual."""
    return (f"{n} clips se pelean el mismo archivo: hay uno solo con ese "
            "nombre y los dos lo reclaman. Ninguno se conectó.")


def _cuantos_sin_comprobar(n: int) -> str:
    """Nadie comparo nada. Decir que no coincide seria inventarlo."""
    if n == 1:
        return ("1 clip apareció, pero el proyecto no guardó su peso ni su "
                "duración, así que no hay con qué comprobar que sea el mismo. "
                "No se conectó.")
    return (f"{n} clips aparecieron, pero el proyecto no guardó su peso ni su "
            "duración, así que no hay con qué comprobar que sean los mismos. "
            "No se conectaron.")


def _cuantos_sin_donde_buscar(n: int) -> str:
    """Ni se buscaron. «No apareció en esa carpeta» suena a que basta con
    probar en otra, y a estos no los salva ninguna."""
    if n == 1:
        return ("1 clip no se puede buscar: el proyecto no guardó de dónde "
                "colgaba dentro de su carpeta.")
    return (f"{n} clips no se pueden buscar: el proyecto no guardó de dónde "
            "colgaban dentro de su carpeta.")


def _cuantos_sin_proxy(n: int) -> str:
    """Navegar sin proxy cuesta 530 ms por cuadro contra 22. Callarlo deja
    el proyecto 25 veces mas lento sin decir por que."""
    if n == 1:
        return ("1 clip quedó sin proxy: vas a navegar sobre el original, que "
                "es mucho más lento.")
    return (f"{n} clips quedaron sin proxy: vas a navegar sobre el original, "
            "que es mucho más lento.")


def _copiar(valor):
    """Copia los valores mutables que guarda el historial.

    `categoria_path` es una lista: guardar la referencia haria que el
    "antes" mutara junto con el clip y deshacer no hiciera nada.
    """
    return list(valor) if isinstance(valor, list) else valor


class _AutosaveWriteJob(QRunnable):
    """Escribe el proyecto a disco fuera del hilo de la UI -- antes
    `_autosave` escribia sincronicamente en cada tecla, lo que con muchas
    sesiones/clips se sentia como lag real al clasificar rapido.

    Aqui adentro tambien se MIDE el peso de cada archivo, por lo mismo: un
    `stat` sobre un volumen montado pero incomunicado se traba hasta el
    timeout, y son uno por clip en serie.

    Y aqui se avisa cuando la escritura falla. Antes se tragaba el error, lo
    que en la sesion escondida --un archivo en la carpeta del usuario,
    siempre escribible-- casi nunca pasaba; ahora el archivo lo elige Bruno
    y puede estar en un disco externo que se desconecta a media tarde.
    """

    def __init__(self, path: Path, data: dict, generacion: int,
                 señales: "SeñalesDeTrabajos"):
        super().__init__()
        self.path = path
        self.data = data
        self._generacion = generacion
        self._señales = señales

    def run(self) -> None:
        try:
            # el archivo ACUMULA los pesos: sin releer lo que ya habia se
            # perderia el peso de un clip medido con la tarjeta puesta en
            # cuanto se desconectara.
            previos = (proyecto.abrir(self.path) or {}).get("bytes")
            documento = proyecto.con_pesos_medidos(self.data, previos)
            proyecto.guardar(self.path, documento)
        except OSError as error:
            self._señales.guardado_fallo.emit(str(error))
            return
        # y la VENTANA tambien se entera. Que el archivo fuera el unico que
        # los acumulaba dejaba la defensa principal apagada justo en la
        # sesion donde Bruno importa: ahi `_bytes_guardados` esta vacio --se
        # llena solo al abrir un .cvproj-- y reconectar en esa misma sesion
        # confirmaba solo por duracion, que dos tomas del mismo largo de dos
        # tarjetas de la Sony pasan sin problema.
        self._señales.pesos_medidos.emit(
            self._generacion, proyecto.por_indice_de_clip(documento.get("bytes"))
        )
        self._señales.guardado_listo.emit()


# Cuantos `ffprobe` a la vez al importar. Ocho porque es donde la medicion
# se aplana: con 40 clips reales de la FX30, en serie 1.06 s, con 4 en
# paralelo 0.26 s y con 8 en paralelo 0.14 s. Son procesos aparte esperando
# al disco, no CPU nuestra.
SONDEOS_EN_PARALELO = 8


class SeñalesDeTrabajos(QObject):
    """El UNICO portador de las señales de los trabajos en segundo plano.

    Uno por ventana, creado en el hilo de la UI y vivo mientras vive la
    ventana. Los `QRunnable` no crean el suyo: reciben este y lo usan para
    avisar sus resultados.

    Es asi por un segfault medido (agosto 2026). Antes cada trabajo traia su
    propio portador, y ese portador nacia en el hilo de la UI pero moria en
    un hilo del `QThreadPool` --el pool suelta el `QRunnable` al terminar
    `run()` y con el se iba su unico dueño--. Destruir un objeto de Qt fuera
    de su hilo choca con el hilo de la UI justo cuando este recorre sus
    listas: la suite se caia con SIGSEGV 2 de cada 40 corridas.

    Las tres variantes, medidas con el mismo arnes de estres (400 vueltas de
    polish de estilo contra 3200 trabajos, 15 corridas cada una):

    - portador `QWidget` por trabajo ......... 2 caidas de 15
      (revienta el registro de widgets de `QApplication`)
    - portador `QObject` por trabajo ........ 15 caidas de 15
      (peor: revienta al entregar la señal encolada a un portador que el
       hilo del pool ya borro)
    - portador compartido por la ventana ..... 0 caidas de 15

    O sea que volverlo `QObject` sin quitarle el "por trabajo" NO alcanza:
    lo que cura es que ningun objeto de Qt nazca ni muera por trabajo.

    Quien lo mantiene vivo: la ventana (referencia de Python, no hijo de Qt)
    y ademas cada trabajo en vuelo. Y ninguna señal puede llegar tarde: el
    `QThreadPool` SI es hijo de la ventana, y su destructor espera a que
    todos los trabajos terminen antes de que la ventana suelte nada.
    """

    miniatura_lista = Signal(int, int, object)  # generation, indice, list[Path] | None
    proxy_sondeado = Signal(int, int, object)   # generation, indice, info | None
    guardado_listo = Signal()
    guardado_fallo = Signal(str)                # el motivo, tal como lo dio el SO
    pesos_medidos = Signal(int, object)         # generacion de indices, {clip: bytes}
    # los clips cuyo archivo ya no esta, y los proxies perdidos. Se revisa
    # fuera del hilo de la interfaz: son `stat` uno por clip en serie, y
    # sobre un volumen montado e incomunicado cada uno se traba hasta el
    # timeout -- justo lo que pasa al abrir en otra computadora.
    media_revisada = Signal(int, object, object)  # generacion, faltantes, proxies
    # generacion, indice, ruta del proxy generado (o None), motivo del fallo
    proxy_generado = Signal(int, int, object, str)


class _RevisionDeMediaJob(QRunnable):
    """¿Estan los archivos donde el proyecto dice? Fuera del hilo de la UI.

    La leccion ya estaba escrita en `proyecto.con_pesos_medidos`, y aqui se
    volvio a tropezar con ella: un `stat` cuesta menos de un milisegundo en
    local, pero sobre un volumen montado e incomunicado se traba hasta el
    timeout, y son uno por clip en serie. Y esto corre justo al ABRIR un
    proyecto cuyo material puede estar en un disco de red que ya no
    responde: el peor momento posible para congelar la ventana.

    Revisa los originales y tambien los proxies. Un proxy perdido no se ve
    en `clip.ruta`, pero navegar sin el cuesta 530 ms por cuadro contra 22
    (ver `ruta_de_reproduccion`), asi que callarlo seria dejar el proyecto
    25 veces mas lento sin decir por que.
    """

    def __init__(self, generacion: int, rutas: dict[int, Path],
                 proxies: dict[int, Path], señales: "SeñalesDeTrabajos"):
        super().__init__()
        self._generacion = generacion
        self._rutas = rutas
        self._proxies = proxies
        self._señales = señales

    def run(self) -> None:
        faltantes = revinculo.faltantes_de(self._rutas)
        perdidos = {i: Path(p).name
                    for i, p in self._proxies.items()
                    if not Path(p).is_file()}
        self._señales.media_revisada.emit(self._generacion, faltantes, perdidos)


class _ThumbnailJob(QRunnable):
    """Extrae la miniatura (o la tira de frames para el scrub) de un clip
    fuera del hilo de la UI."""

    STRIP_COUNT = 12

    def __init__(self, generation: int, index: int, video: Path, outdir: Path,
                 duration_seconds: float | None, signals: SeñalesDeTrabajos):
        super().__init__()
        self._generation = generation
        self.index = index
        self.video = video
        self.outdir = outdir
        self.duration_seconds = duration_seconds
        self.signals = signals

    def run(self) -> None:
        try:
            if self.duration_seconds:
                # tira de frames espaciados a lo largo del clip, un solo
                # proceso de mpv con varios seek+captura por IPC -- medido
                # en vivo el 2026-08-06 con clips reales de la FX30:
                # ~1.8s para 12 frames (ver thumbnails.extract_thumbnail_strip)
                frames = extract_thumbnail_strip(
                    self.video, self.duration_seconds, self.STRIP_COUNT, self.outdir
                )
            else:
                # sin duracion conocida (ej. sesion restaurada sin volver
                # a correr ffprobe): un solo frame, como antes.
                frames = [extract_thumbnail(self.video, 0.5, self.outdir)]
        except Exception:
            frames = None
        # Sin guarda de `RuntimeError`: el portador vive mientras viva la
        # ventana, y la ventana no se va sin antes esperar a este trabajo
        # (ver `SeñalesDeTrabajos`). Si la ventana ya murio, Qt deshizo la
        # conexion sola y el `emit` no llama a nadie.
        self.signals.miniatura_lista.emit(self._generation, self.index, frames or None)


def _con_el_rango_en_orden(clip: Clip) -> Clip:
    """Copia del clip con `in_frame <= out_frame`, para el manifest.

    Marcar `O` y despues `I` mas adelante deja out < in. La app ya lo
    MUESTRA en orden --con `abs`, desde la auditoria de la F1-F5-- pero lo
    exportaba tal cual, y el plugin aplica in/out siempre que vengan los
    dos: Premiere recibia un rango al reves.

    Se ordena SOLO al exportar. La sesion guarda lo que el editor marco,
    para que deshacer pueda volver a eso.
    """
    if clip.in_frame is None or clip.out_frame is None:
        return clip
    if clip.in_frame <= clip.out_frame:
        return clip
    return replace(clip, in_frame=clip.out_frame, out_frame=clip.in_frame)


def _gigas_del_volumen(ruta: Path) -> int | None:
    """El `· 214 GB` de la barra de estado. En GB decimales, que es como
    viene etiquetada la tarjeta.

    Devuelve `None` si no se puede leer --volumen de red, carpeta ya
    desmontada--: la barra escribe solo la ruta, porque un `0 GB` se
    leeria como disco lleno.
    """
    try:
        return round(shutil.disk_usage(ruta).total / 1_000_000_000)
    except OSError:
        return None


def _corrido_set(indices: set[int], fuera: set[int]) -> set[int]:
    """`_corrido` para los conjuntos de indices de clip. Mismo motivo: un
    indice que se queda atras deja de hablar del clip que describia."""
    return {
        i - sum(1 for q in fuera if q < i)
        for i in indices
        if i not in fuera
    }


def _corrido(mapa: dict, fuera: set[int]) -> dict:
    """Reindexa un diccionario que va por indice de clip, despues de quitar
    los indices de `fuera`.

    La app tiene OCHO diccionarios asi --duraciones, tamaños, rotaciones,
    tamaños de proxy, candidatos a proxy, generaciones de sondeo, rutas
    relativas y pesos guardados-- y todos tienen que correrse en la misma
    operacion. Cualquiera que se quede
    atras describe a otro clip y no da ningun sintoma hasta que un video se
    dibuja acostado o un proxy ajeno se engancha como bueno.
    """
    return {
        i - sum(1 for q in fuera if q < i): v
        for i, v in mapa.items()
        if i not in fuera
    }


class _ProxyProbeJob(QRunnable):
    """Sondea UN proxy fuera del hilo de la UI.

    Va al thread pool y no en el mismo ciclo del import por una medicion:
    `ffprobe` sobre el proxy cuesta 26.7 ms, o sea **3.42 s** de mas en una
    importacion de 128 clips (task 0 del plan de la F9). Importar ya
    bloquea; no se le suman tres segundos y medio mas.

    Solo LEE el archivo. Quien decide si el proxy sirve es la ventana, en
    el hilo de la UI, que es donde estan los datos del original.
    """

    def __init__(self, generation: int, index: int, proxy: Path, probe,
                 signals: SeñalesDeTrabajos):
        super().__init__()
        self._generation = generation
        self.index = index
        self.proxy = proxy
        self._probe = probe
        self.signals = signals

    def run(self) -> None:
        try:
            info = self._probe(self.proxy)
        except Exception:
            info = None
        # sin guarda, por lo mismo que en `_ThumbnailJob.run`
        self.signals.proxy_sondeado.emit(self._generation, self.index, info)


class _GeneracionDeProxyJob(QRunnable):
    """Genera UN proxy con ffmpeg, fuera del hilo de la UI.

    Cuesta unos 10 s por cada 6 s de video, o sea que con las 23 tomas del
    dron son varios minutos: hacerlo en el hilo de la ventana la congelaria
    todo ese rato. Bruno sigue clasificando mientras corre.

    `cancelado` es un invocable, no un booleano: el valor se lee al empezar
    ESTE clip, ya encolado. Un booleano se copiaria al construir el trabajo
    --o sea, siempre False-- y cancelar no cortaria nada de lo pendiente,
    que es justo para lo que sirve.
    """

    def __init__(self, generacion: int, index: int, original: Path,
                 carpeta: Path, cancelado, señales: SeñalesDeTrabajos):
        super().__init__()
        self._generacion = generacion
        self.index = index
        self._original = original
        self._carpeta = carpeta
        self._cancelado = cancelado
        self.signals = señales

    def run(self) -> None:
        if self._cancelado():
            # se avisa igual, con las manos vacias: quien lleva la cuenta
            # necesita saber que este ya no viene, o el «7 de 23» se queda
            # clavado para siempre
            self.signals.proxy_generado.emit(self._generacion, self.index, None, "")
            return
        try:
            # la bandera va TAMBIEN adentro: sin esto, cancelar solo evitaba
            # los que no habian empezado, y el que ya corria seguia hasta el
            # final -- con una toma de dron de tres minutos y medio, eso es
            # una app congelada varios minutos al cerrarla
            destino = proxy_gen.generar(self._original, self._carpeta,
                                        cancelado=self._cancelado)
        except proxy_gen.Interrumpido:
            self.signals.proxy_generado.emit(self._generacion, self.index, None, "")
            return
        except Exception as e:  # ffmpeg fallo, o el disco se lleno
            self.signals.proxy_generado.emit(self._generacion, self.index, None, str(e))
            return
        self.signals.proxy_generado.emit(self._generacion, self.index, destino, "")


class MainWindow(QWidget):
    """Ventana del clasificador, con la estructura del mockup.

    TRES filas y ninguna mas: barra de titulo, cuerpo y barra de estado.
    Cualquier cuarta fila es una banda horizontal, y en un clip 9:16 cada
    16 px de banda cuestan 9 px de ancho de video. Todo lo demas vive en
    columnas o flotando sobre el video (ver VideoStage).

    El ancho del video lo dicta la relacion de aspecto del clip y los
    paneles absorben el resto: asi no queda ni una franja negra.
    """

    # La pantalla de inicio se esconde mientras hay una ventana abierta y
    # vuelve cuando se cierra. Se avisa con una señal y no mirando
    # `destroyed`: para eso habria que marcar la ventana con
    # `WA_DeleteOnClose`, y destruirla desde el aviso de su propia
    # destruccion es de donde salieron varios segfaults de este proyecto.
    cerrada = Signal()

    def __init__(
        self,
        project_name: str,
        room_selection: RoomSelection,
        video_factory: Callable[..., object] | None = None,
        parent=None,
        thumbnail_cache_root: Path | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(project_name)
        self.project_name = project_name
        self.room_selection = room_selection
        self.clips: list[Clip] = []
        self.current_index = 0
        self.selected_indices: list[int] = []
        self.history = History()
        self.filters = FilterState()
        # el clip actual arranco solo (y el badge `▶ auto` esta prendido).
        # Se apaga en cuanto pausas y no vuelve hasta el siguiente clip.
        self._auto_reproduciendo = False
        # el autoplay que la hoja dejo esperando: en la hoja no hay imagen
        # que acompañe al sonido, asi que se aplaza hasta cruzar al visor.
        # Es un tercer estado y no `_auto_reproduciendo` puesto a la fuerza,
        # porque el tick del playhead apaga ese en cuanto ve el clip pausado.
        self._auto_pendiente = False
        # solo video: los paneles escondidos y el video con todo el ancho
        self._solo_video = False
        # modo hoja: la hoja a pantalla completa, sin video ni columna
        self._modo_hoja = False
        # pincel: (tecla, cuarto) mientras la tecla esta abajo, y los indices
        # ya pintados en ESTA pincelada
        self._pincel: tuple[str, str] | None = None
        # indice -> categoria_path que tenia ANTES de esta pincelada. Se
        # guarda al tocarlo, no al soltar: al soltar ya esta pisado.
        self._antes_de_pintar: dict[int, list[str]] = {}
        self._router = KeyboardRouter(active_rooms=room_selection.active_rooms())
        self._probe_clip = probe_clip          # inyectable para tests
        self._thumbnail_cache_root = thumbnail_cache_root or default_cache_root()
        # el portador de señales de los trabajos: uno solo, de la ventana.
        # Se conecta aqui una vez y no por trabajo (ver SeñalesDeTrabajos).
        self._señales_de_trabajos = SeñalesDeTrabajos()
        self._señales_de_trabajos.miniatura_lista.connect(self._on_thumbnail_ready)
        self._señales_de_trabajos.proxy_sondeado.connect(self._on_proxy_sondeado)
        self._señales_de_trabajos.guardado_listo.connect(self._on_guardado_listo)
        self._señales_de_trabajos.guardado_fallo.connect(self._on_guardado_fallo)
        self._señales_de_trabajos.pesos_medidos.connect(self._on_pesos_medidos)
        self._señales_de_trabajos.media_revisada.connect(self._on_media_revisada)
        self._señales_de_trabajos.proxy_generado.connect(self._on_proxy_generado)
        # hijo de la ventana A PROPOSITO: su destructor espera a los trabajos
        # en vuelo, y esa espera es lo que impide que una señal llegue
        # cuando la ventana ya no puede atenderla.
        self._thread_pool = QThreadPool(self)
        # La revisión de media tiene el SUYO, y no es un lujo: el otro pool
        # se llena con las portadas --tres hilos, un trabajo por clip-- y el
        # aviso que le dice a Bruno «tu material no está» quedaba encolado
        # detrás de la extracción de ese mismo material que no está. Con sus
        # 132 clips eso es no llegar nunca. Hijo de la ventana, igual que el
        # otro: su destructor espera a los trabajos en vuelo, y esa espera es
        # lo que impide que una señal llegue cuando ya no hay quien la atienda.
        self._revision_pool = QThreadPool(self)
        self._revision_pool.setMaxThreadCount(1)
        # Y la generación de proxies tiene el suyo, de UN hilo. Uno solo a
        # propósito: `h264_videotoolbox` usa el codificador del chip, que es
        # una pieza de hardware — dos a la vez no terminan en la mitad del
        # tiempo, se pelean, y además compiten con el reproductor embebido,
        # que usa el MISMO chip para decodificar lo que Bruno está viendo
        # mientras corre.
        self._generacion_pool = QThreadPool(self)
        self._generacion_pool.setMaxThreadCount(1)
        # Estado de la tanda que corre, o None. Lleva su propia generación
        # por la misma razón que los proxies: quitar el bin a media tanda
        # deja trabajos en vuelo cuyos resultados ya no aplican a nada.
        self._generando_proxies: dict | None = None
        self._generacion_de_proxies = 0
        # las miniaturas se extraen en software (--hwdec=no, ver
        # thumbnails.py) -- no tocan VideoToolbox, asi que un par en
        # paralelo no compite con el reproductor embebido.
        self._thread_pool.setMaxThreadCount(3)
        self._thumb_generation = 0
        self.session_path: Path | None = None
        self._last_saved_at: float | None = None
        self._clip_durations: dict[int, float] = {}  # indice -> segundos; solo en memoria
        # indice -> (ancho, alto) ya corregidos por rotacion en probe.py.
        # Solo en memoria, igual que las duraciones: meterlo en Clip cambiaria
        # to_dict() y con eso el contrato del manifest con el plugin de Premiere.
        self._clip_sizes: dict[int, tuple[int, int]] = {}
        self._clip_rotations: dict[int, int] = {}
        # Lo que hace falta para reencontrar el material si el proyecto se
        # abre en otra computadora: la ruta de cada clip relativa a la
        # carpeta de su bin, y su peso en bytes. Los pesos se CONSERVAN
        # aunque la media no este conectada -- son lo unico que distingue
        # una tarjeta de otra cuando dos archivos se llaman igual.
        self._relativas: dict[int, str] = {}
        self._bytes_guardados: dict[int, int] = {}
        # nombre de bin -> el ultimo `Reencuentro` que devolvio buscar ahi.
        # Es lo que permite decir cada final por separado: sin esto, «no
        # coincide» y «no apareció» se verian iguales.
        self._ultimo_reencuentro: dict[str, revinculo.Reencuentro] = {}
        # Lo que la ultima revision encontro. Se GUARDA en vez de volver a
        # preguntarle al disco cada vez que hay que redibujar la barra: cada
        # barrido son `stat` uno por clip en serie, y `_refrescar_aviso`
        # corre en cada renombrado de bin y en cada reconexion.
        self._faltantes: set[int] = set()
        self._proxies_perdidos: dict[int, str] = {}   # clip -> nombre del proxy
        # los que ni se buscaron, por no tener ruta relativa. Aparte de «no
        # apareció»: a estos no los salva ninguna carpeta.
        self._sin_donde_buscar: set[int] = set()
        # (bin, acción) mientras una búsqueda está corriendo. Ver
        # `_mientras_busca`.
        self._buscando: tuple[str, str] | None = None
        # si al terminar la revisión hay que pedir las portadas. Solo al
        # abrir: es el único momento en que hay que esperarla para saber qué
        # archivos existen.
        self._portadas_tras_revisar = False
        self._revision_generation = 0
        # cuántas revisiones entregaron resultado. Solo para poder esperarlas
        # desde los tests sin adivinar con un `sleep`.
        self._revisiones_terminadas = 0
        # Sube cada vez que los indices de clip se mueven. Los resultados que
        # vienen de otro hilo hablan de los indices de CUANDO arrancaron: si
        # entre medio se quito un bin, un peso caeria sobre el clip
        # equivocado -- y con ese peso es con lo que despues se confirma que
        # un archivo reencontrado es el que era.
        self._indices_generation = 0
        # bin -> cuantos se reconectaron, para el renglon verde. Es efimero a
        # proposito (`_olvidar_exitos`): dejarlo fijo le roba alto al video
        # el resto de la sesion por algo que ya salio bien.
        self._exitos: dict[str, int] = {}
        self._timer_de_exito = QTimer(self)
        self._timer_de_exito.setSingleShot(True)
        self._timer_de_exito.setInterval(8000)
        self._timer_de_exito.timeout.connect(self._olvidar_exitos)
        # indice -> tamaño del PROXY, solo de los que ya validaron. El que
        # manda el layout sigue siendo `_clip_sizes`, que es del original:
        # esto es nada mas para escribir «720p» sin inventarlo.
        self._proxy_sizes: dict[int, tuple[int, int]] = {}
        self._proxy_candidatos: dict[int, Path] = {}
        self._miniaturas_pendientes = 0
        self._miniaturas_totales = 0
        # `{indice: archivo del que se esta extrayendo}` de lo que corre
        # ahora. Dos trabajos para el mismo clip comparten carpeta de salida
        # y socket IPC, y el segundo le borra el socket al primero: el primer
        # mpv muere a media tira y esa tarjeta se queda con un solo cuadro,
        # o sea sin escrubeo.
        self._miniaturas_en_vuelo: dict[int, Path] = {}
        # Los que hay que rehacer en cuanto termine lo que corre: pasa cuando
        # se enganchan los proxies a media extraccion y la fuente cambia.
        self._miniaturas_a_rehacer: set[int] = set()
        self._proxy_generation = 0
        # indice -> generacion del sondeo que sigue siendo valido para ese
        # clip. Con bins, cada tanda toca un bin nada mas: el contador
        # global ya no alcanza para saber que resultado sigue vigente.
        self._proxy_generacion_de: dict[int, int] = {}
        self.transicion = TransicionDeTarjeta(self)

        # autosave con debounce: coalesca ediciones rapidas seguidas en un
        # solo guardado en vez de escribir a disco en cada tecla.
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(400)
        self._autosave_timer.timeout.connect(self._write_autosave_now)
        self._autosave_pool = QThreadPool(self)
        self._autosave_pool.setMaxThreadCount(1)

        self.bins = BinTree()
        # guarda de reentrada de `_refresh_sheet` (ver ahi el porque)
        self._refrescando_hoja = False

        # ---------------- las tres filas ----------------
        self.title_bar = TitleBar()
        self.title_bar.set_project(project_name, 0)
        self.title_bar.export_requested.connect(self._on_export_manifest)
        self.title_bar.mode_toggled.connect(self.alternar_modo_hoja)

        self.room_rail = RoomRail()
        self.room_rail.import_requested.connect(self._on_import_folders)
        self.room_rail.room_created.connect(self._on_room_created)
        self.room_rail.room_renamed.connect(self._on_room_renamed)
        self.room_rail.room_moved.connect(self._on_room_moved)
        self.room_rail.room_removed.connect(self._on_room_removed)
        self.room_rail.revert_requested.connect(self.revert)
        # el boton «Cuartos ⌘R» estuvo muerto desde la F2: emitia una señal
        # que nadie escuchaba. Ahora lleva el foco al rail, para renombrar,
        # reordenar y crear cuartos sin tocar el mouse.
        self.title_bar.proxies_requested.connect(self.adjuntar_proxies)

        self.video_stage = VideoStage(mpv_factory=video_factory)
        self.video_stage.speed.selected.connect(self._on_speed_changed)
        self.scrub_bar = self.video_stage.scrub_bar
        self.scrub_bar.seek_started.connect(self._on_scrub_seek_started)
        self.scrub_bar.seek_requested.connect(self._on_scrub_seek)

        self.tool_column = ToolColumn()
        self.tool_column.undo_requested.connect(self.undo)

        self.clip_sheet = ClipSheet()
        self.clip_sheet.clip_clicked.connect(self.select_clip)
        self.clip_sheet.clip_activated.connect(self._on_clip_activado)
        self.clip_sheet.brocha_paso_por.connect(self.pintar)
        self.clip_sheet.selection_changed.connect(self._on_selection_changed)
        self.clip_sheet.filters_changed.connect(self.set_filters)
        # los encabezados de bin nacen y mueren con las importaciones, asi
        # que se enchufan cuando nacen y no una sola vez al arrancar
        # El encabezado PEGADO no se conecta aqui: la hoja ya le reenvia lo
        # suyo al encabezado de verdad del mismo bin. Conectarlo tambien
        # haria que cada renglon de su menu se ejecutara dos veces.
        self.clip_sheet.bin_header_created.connect(self._conectar_bin)
        # arrastrar material (F5). Los dos caminos terminan en el MISMO
        # `importar_rutas` que usa el boton de importar: es el que descarta
        # lo que ya esta, avisa cuando no hay video y mide con ffprobe. Dos
        # puertas de entrada con dos reglas distintas seria un bug esperando.
        self.clip_sheet.soltado_en_bin.connect(
            lambda nombre, rutas: self.importar_rutas(rutas, nombre_de_bin=nombre)
        )
        self.clip_sheet.soltado_en_nuevo_bin.connect(
            lambda rutas: self.importar_rutas(rutas)
        )
        # soltar sobre la seccion de sueltos: entra sin bin. `sueltos=True` y
        # no un nombre, porque «Sin bin» no es un bin (ver `agregar_clips`).
        self.clip_sheet.soltado_sin_bin.connect(
            lambda rutas: self.importar_rutas(rutas, sueltos=True)
        )
        self.clip_sheet.bin_nuevo_pedido.connect(self._on_bin_nuevo_pedido)
        # arrastrar clips que YA estan en la hoja de un bin a otro (F9)
        self.clip_sheet.clips_movidos.connect(self._on_clips_movidos)

        self.status_bar = StatusBar()
        self.status_bar.unclassified_clicked.connect(self._filtrar_sin_clasificar)

        # La barra de media faltante. Nace escondida y solo aparece cuando
        # hay algo que decir (ver `revisar_media`).
        self.aviso_de_media = AvisoDeMedia()
        self.aviso_de_media.buscar_pedido.connect(self._on_buscar_media)

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(0)
        cuerpo.addWidget(self.room_rail)
        cuerpo.addWidget(self.video_stage)
        cuerpo.addWidget(self.tool_column)
        cuerpo.addWidget(self.clip_sheet, stretch=1)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self.title_bar)
        # Debajo del titulo y ENCIMA del cuerpo, ocupando su renglon: asi
        # empuja la hoja hacia abajo en vez de taparle la primera fila de
        # tarjetas, que es lo que haria un cartel flotante.
        raiz.addWidget(self.aviso_de_media)
        raiz.addLayout(cuerpo)
        raiz.addWidget(self.status_bar)

        self._playhead_timer = QTimer(self)
        self._playhead_timer.setInterval(150)
        self._playhead_timer.timeout.connect(self._tick_playhead)
        self._playhead_timer.start()
        self._saved_timer = QTimer(self)
        self._saved_timer.setInterval(1000)
        self._saved_timer.timeout.connect(self._tick_saved_indicator)
        self._saved_timer.start()

        # La paleta flota sobre el video: hija de la ventana y NO un QDialog
        # modal, porque un modal roba el teclado y hay que cerrarlo para
        # seguir clasificando.
        # el chip que sigue al cursor mientras pintas
        self._chip_pincel = QLabel("", self)
        self._chip_pincel.hide()

        self.room_palette = RoomPalette(self)
        self.room_palette.room_chosen.connect(self._on_room_elegido_en_paleta)
        self.room_palette.room_created.connect(self._on_room_creado_en_paleta)

        self._install_shortcuts()
        self._refresh_rail()

        # Arranca en la hoja: es lo primero que Bruno quiere ver. Se hace
        # llamando al mismo metodo que la tecla, y no poniendo el flag a
        # mano, porque el modo tambien esconde el visor y la columna de
        # herramientas; dos caminos para lo mismo se desincronizan. Va al
        # final del constructor porque necesita las tres filas ya armadas.
        self.alternar_modo_hoja()

    # ------------------------------------------------------------------
    # video dimensionado por aspecto
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        super().resizeEvent(event)
        self._resize_video_stage()

    def _resize_video_stage(self) -> None:
        """El alto del cuerpo se CALCULA, no se lee de los hijos: durante
        `resizeEvent` los hijos todavia tienen el tamaño anterior."""
        # en solo video no hay barras que restar: estan escondidas, y seguir
        # restandolas dejaba el video 33 px mas angosto de lo que cabe
        alto_cuerpo = self.height()
        if not self._solo_video:
            alto_cuerpo -= theme.TITLEBAR_HEIGHT + theme.STATUSBAR_HEIGHT
            if not self.aviso_de_media.isHidden():
                # la barra de media faltante ocupa su renglon, asi que le
                # quita alto al cuerpo igual que las otras dos. Su alto se
                # LEE --no hay constante-- porque crece con los renglones.
                alto_cuerpo -= self.aviso_de_media.sizeHint().height()
        ancho = VideoStage.width_for(alto_cuerpo, self.aspect_ratio_for(self.current_index))
        # El minimo REAL de la hoja, no la constante: su encabezado --titulo,
        # buscador, chip de cola y las dos filas de filtros-- pide bastante mas
        # que `SHEET_MIN_WIDTH`. Usar la constante creaba un lazo: el video
        # pedia mas ancho del que habia, la ventana crecia, eso agrandaba el
        # maximo, el video crecia otra vez... con un clip horizontal la ventana
        # se inflaba de 1600 a 2653 px.
        if self._solo_video:
            # sin paneles no hay nada que restarle: el video se lleva la
            # ventana entera
            maximo = self.width()
        else:
            minimo_hoja = max(
                theme.SHEET_MIN_WIDTH, self.clip_sheet.minimumSizeHint().width()
            )
            maximo = (self.width() - theme.RAIL_WIDTH - theme.TOOLCOL_WIDTH
                      - minimo_hoja)
        self.video_stage.setFixedWidth(max(1, min(ancho, maximo)))

    def aspect_ratio_for(self, index: int) -> float:
        """Relacion de aspecto real del clip. 16/9 cuando no se conoce --
        pasa con sesiones restauradas de disco, donde no se volvio a correr
        ffprobe (mismo comportamiento que ya tienen las duraciones).
        """
        width, height = self._clip_sizes.get(index, (0, 0))
        if width > 0 and height > 0:
            return width / height
        return 16 / 9

    def ruta_de_reproduccion(self, index: int) -> Path:
        """Que archivo abre el reproductor: el proxy si validó, el original
        si no.

        Es lo que le da sentido a toda esta fase. Medido contra el material
        real de la FX30 (4K HEVC 10-bit a 268 Mbps), con
        `hwdec=videotoolbox`:

        | | original | proxy |
        |---|---|---|
        | primer cuadro al abrir | 204.5 ms | 8.9 ms |
        | seek exacto | 367.6 ms | 19.0 ms |
        | un cuadro atras (`,`) | 529.9 ms | 22.3 ms |

        Medio segundo por cada `,` era la queja de CONTEXTO-Y-METAS.md
        sobre la navegacion cuadro a cuadro. No era la app: era el
        material.

        No hay interruptor para apagarlo: DECISIONES.md no lo pide y el
        badge sobre el video ya dice que estas viendo el proxy. Y como el
        proxy calza cuadro a cuadro (se valida al importar), el in/out cae
        en el mismo numero de cuadro que sobre el original.
        """
        clip = self.clips[index]
        proxy = clip.ruta_proxy
        # una sesion restaurada trae el proxy que valido en su momento,
        # pero la tarjeta puede estar desmontada: mpv abriria la nada.
        if proxy is not None and proxy.exists():
            return proxy
        return clip.ruta

    def orientacion_del_proyecto(self) -> str:
        """La que declara el manifest, sacada del material -- ver
        `probe.orientacion_predominante`. Solo cuentan los clips que
        siguen en la lista: si Bruno importo y volvio a importar, los
        tamaños de la importacion anterior ya no estan.
        """
        return orientacion_predominante(
            self._clip_sizes.get(index, (0, 0)) for index in range(len(self.clips))
        )

    # ------------------------------------------------------------------
    # teclado
    # ------------------------------------------------------------------

    def _install_shortcuts(self) -> None:
        shortcuts: list[tuple[str, Callable[[], None]]] = [
            ("Space", self.video_stage.video.toggle_play),
            ("Left", lambda: self.handle_arrow("prev")),
            ("Right", lambda: self.handle_arrow("next")),
            # `↑`/`↓` suben y bajan el estado del clip por la escalera
            # reject - sin marca - pick - destacado. Antes no hacian nada.
            ("Up", lambda: self.handle_key_press("arriba")),
            ("Down", lambda: self.handle_key_press("abajo")),
            # `R`: volver al principio del clip. Se eligio una letra y no
            # `Home` porque los teclados de MacBook no traen `Home`.
            ("R", lambda: self.handle_key_press("r")),
            ("I", lambda: self.handle_key_press("i")),
            ("O", lambda: self.handle_key_press("o")),
            ("P", lambda: self.handle_key_press("p")),
            ("X", lambda: self.handle_key_press("x")),
            # `⇧P`: el cuarto estado, destacado
            ("Shift+P", lambda: self.handle_key_press("shift+p")),
            ("U", lambda: self.handle_key_press("u")),
            # `S`: el mismo cuarto que el clip anterior
            ("S", lambda: self.handle_key_press("s")),
            # `⏎`: la paleta de cuartos. Comparte tecla con renombrar en el
            # rail, y por eso el handler mira quien tiene el foco.
            ("F", lambda: self.handle_key_press("f")),
            # modo hoja y tamaño de miniatura
            ("Tab", lambda: self.handle_key_press("tab")),
            ("+", lambda: self.handle_key_press("+")),
            ("-", lambda: self.handle_key_press("-")),
            ("Esc", lambda: self.handle_key_press("escape")),
            ("Return", self._on_enter),
            ("Enter", self._on_enter),
            # `J K L`: la convencion de Premiere, Avid y Resolve
            ("L", lambda: self.handle_key_press("l")),
            ("K", lambda: self.handle_key_press("k")),
            ("J", lambda: self.handle_key_press("j")),
            # cuadro a cuadro, tambien como en Premiere
            (",", lambda: self.handle_key_press(",")),
            (".", lambda: self.handle_key_press(".")),
            # la hoja lo anuncia en el encabezado de cada grupo: tiene que
            # existir de verdad. QKeySequence.SelectAll ya es ⌘A en macOS y
            # Ctrl+A en el resto, sin escribir el modificador a mano.
            (QKeySequence.StandardKey.SelectAll, self.select_current_group),
            # StandardKey.Undo ya es ⌘Z en macOS y Ctrl+Z en el resto
            (QKeySequence.StandardKey.Undo, self.undo),
            # la barra de titulo anuncia `⌘E` en el boton de exportar desde la
            # F2 y el atajo no existia
            ("Ctrl+E", self._on_export_manifest),
            ("Ctrl+R", self.room_rail.focus_rooms),
        ]
        # Los digitos NO van aqui a proposito: ver `keyPressEvent`. Un
        # QShortcut consume la tecla y nunca avisa de que se solto, asi que
        # con ellos registrados el pincel no se armaria nunca -- y los tests
        # no lo verian, porque un atajo solo se dispara con la ventana ACTIVA
        # y en pruebas la tecla llega igual al widget.

        # Los de arriba son teclas SUELTAS --letras, digitos, espacio, flechas,
        # coma y punto-- y un `QShortcut` de contexto `WindowShortcut` se
        # resuelve ANTES de entregarle la tecla al widget con foco. Sin esta
        # guarda, escribir "cocina" en el buscador de la hoja dispararia la
        # velocidad con la `c`... perdon, con la `i` el marcado de in, con la
        # `o` el de out, y "1" asignaria un cuarto -- mientras el texto ni
        # siquiera llega al campo.
        #
        # No se pudo comprobar en esta maquina: los atajos solo se disparan con
        # la ventana ACTIVA, y un proceso lanzado desde la terminal no logra
        # activarse en macOS. Por eso se blinda por construccion en vez de
        # apostar a que Qt haga lo que uno espera. Los de modificador (⌘Z, ⌘E,
        # ⌘R, ⌘A) NO se guardan: no chocan con escribir.
        self._shortcuts = []
        self._atajos_de_tecla_suelta = []
        for sequence, handler in shortcuts:
            con_modificador = (
                isinstance(sequence, QKeySequence.StandardKey)
                or (isinstance(sequence, str) and "Ctrl" in sequence)
            )
            atajo = QShortcut(
                QKeySequence(sequence), self,
                activated=(handler if con_modificador
                           else self._solo_si_no_escribes(handler)),
            )
            self._shortcuts.append(atajo)
            if not con_modificador:
                self._atajos_de_tecla_suelta.append(atajo)

        # Se DESACTIVAN mientras escribes, no basta con ignorarlos: un atajo
        # que se dispara CONSUME la tecla, asi que con solo ignorarla el
        # buscador se quedaria mudo --ni cambia la velocidad ni aparece la
        # letra--. Un atajo desactivado no compite, y la tecla llega al campo.
        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._al_cambiar_el_foco)

    def _al_cambiar_el_foco(self, _viejo, nuevo) -> None:
        escribiendo = self._es_campo_de_texto(nuevo)
        for atajo in self._atajos_de_tecla_suelta:
            atajo.setEnabled(not escribiendo)

    def _solo_si_no_escribes(self, handler: Callable[[], None]) -> Callable[[], None]:
        """Segunda linea de defensa, por si el foco cambio sin avisar."""
        def envuelto() -> None:
            if self.escribiendo_texto():
                return
            handler()
        return envuelto

    @staticmethod
    def _es_campo_de_texto(widget) -> bool:
        """Se pregunta por el TIPO y no por cual widget es, para que un campo
        nuevo quede cubierto sin que nadie se acuerde de venir a agregarlo.
        Hoy son el buscador de la hoja y el renombrado de cuartos del rail.
        """
        from PySide6.QtWidgets import QAbstractSpinBox, QLineEdit, QTextEdit

        return isinstance(widget, (QLineEdit, QTextEdit, QAbstractSpinBox))

    @classmethod
    def escribiendo_texto(cls) -> bool:
        """¿El foco esta en un campo donde se escribe?"""
        return cls._es_campo_de_texto(QApplication.focusWidget())

    def keyPressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Mantener `1`-`9` carga el pincel.

        Va aqui y no en un `QShortcut` porque un atajo solo avisa de la
        PULSACION: nunca dice que se solto la tecla, y el pincel existe
        justamente mientras esta abajo.

        `isAutoRepeat` se ignora: el sistema repite la tecla mientras la
        sostienes, y empezar una pincelada nueva en cada repeticion dejaria
        una entrada de historial por tarjeta -- que es exactamente lo que el
        detalle 4 de DECISIONES.md existe para evitar.
        """
        texto = event.text()
        if (texto.isdigit() and texto != "0" and not event.isAutoRepeat()
                and self._pincel is None and not self.escribiendo_texto()):
            self.empezar_pincelada(texto)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Soltar la tecla cierra el gesto.

        Si no se pinto ninguna tarjeta, fue un TOQUE y no una pincelada: se
        asigna el cuarto al clip actual y se avanza, que es lo que `1`-`9`
        hacen desde la F3. Asi una sola tecla cubre los dos gestos sin que
        haya que aprender nada nuevo.
        """
        if (self._pincel is not None and not event.isAutoRepeat()
                and event.text() == self._pincel[0]):
            tecla = self._pincel[0]
            fue_pincelada = bool(self._antes_de_pintar)
            self.terminar_pincelada()
            if not fue_pincelada:
                self.handle_key_press(tecla)
            return
        super().keyReleaseEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """El apagado ordenado de la ventana. El orden no es casual.

        Los temporizadores PRIMERO: el del playhead corre cada 150 ms y le
        pregunta la posicion al reproductor, asi que uno que llegue despues
        de apagar mpv lo resucitaria --con sus hilos-- sobre una ventana que
        se esta cerrando.

        Despues el guardado y los trabajos en vuelo, y solo entonces mpv:
        hasta la F5 esto no existia porque la ventana vivia hasta que moria
        el proceso. Con la pantalla de inicio se destruye en caliente y cada
        proyecto cerrado dejaria un mpv atras.
        """
        self._playhead_timer.stop()
        self._saved_timer.stop()
        self._flush_autosave()
        # La tanda de proxies PRIMERO, y cancelandola: el pool es hijo de la
        # ventana, asi que su destructor espera a que termine todo lo
        # encolado. Con 23 clips por delante eso son minutos de app
        # congelada al cerrar, sin decir por que. `clear()` tira lo que no
        # arranco y la bandera corta el que si.
        self.cancelar_generacion_de_proxies()
        self._generacion_pool.clear()
        self._generacion_pool.waitForDone(5000)
        self._thread_pool.waitForDone(5000)
        self.video_widget.apagar()
        # al final: quien escucha esto devuelve la pantalla de inicio, y
        # tiene que hacerlo con el proyecto ya a salvo en disco y con la
        # ventana sin nada vivo adentro.
        self.cerrada.emit()
        super().closeEvent(event)

    @property
    def current_clip(self) -> Clip | None:
        if not self.clips:
            return None
        return self.clips[self.current_index]

    @property
    def video_widget(self):
        """El `VideoWidget` real, ahora dentro del `VideoStage`."""
        return self.video_stage.video

    def _on_selection_changed(self, indices: list[int]) -> None:
        self.selected_indices = list(indices)

    def select_current_group(self) -> None:
        """`⌘A`: selecciona el grupo del clip actual, para asignarle un cuarto
        de una sola tecla. Es lo que anuncia el encabezado de cada grupo."""
        self.clip_sheet.select_current_group()

    def _bulk_target_indices(self) -> list[int]:
        """Clips a los que aplicar una asignacion de cuarto: si hay mas de
        un clip seleccionado, todos ellos; si no, solo el clip actual.

        Los que el filtro esconde NO entran: una seleccion vieja tapada por un
        filtro recibiria la asignacion sin que la veas.
        """
        if len(self.selected_indices) > 1:
            visibles = set(self.queue())
            return [
                i for i in self.selected_indices
                if 0 <= i < len(self.clips) and i in visibles
            ]
        if self.current_clip is not None:
            return [self.current_index]
        return []

    def _apply_categoria_to_targets(self, path: list[str]) -> None:
        indices = self._bulk_target_indices()
        if not indices:
            return
        cuarto = path[-1]
        self._registrar(
            etiqueta=cuarto,
            detalle=self._detalle(indices),
            color=self._color_de_cuarto(path[0]),
            clips=indices,
            campos=("categoria_path",),
        )
        for indice in indices:
            self.clips[indice].categoria_path = list(path)

    # ------------------------------------------------------------------
    # los filtros SON la cola de navegacion
    # ------------------------------------------------------------------

    def queue(self) -> list[int]:
        """Los indices que pasan el filtro, en orden.

        Una sola lista alimenta tres cosas: que se ve en la hoja, por donde
        se mueven las flechas y que dice el contador del visor. Calculadas
        por separado se desincronizan, y ahi aparecen los bugs de «la flecha
        me llevo a un clip que no estoy viendo».
        """
        # el bin va aparte y no dentro del clip: `Clip.to_dict()` es el
        # contrato con el plugin de Premiere y no se toca.
        return cola(self.clips, self.filters, bin_de=self.bins.mapa_por_clip())

    def set_filters(self, estado: FilterState) -> None:
        self.filters = estado
        self._refresh_sheet()

    def _filtrar_sin_clasificar(self) -> None:
        """El aviso de la barra de estado: el boton de «sigue trabajando».

        Se usa `click()` y no `setChecked()`: `setChecked` no emite `clicked`,
        asi que la hoja no se enteraba y el chip no se marcaba como el que
        define la cola.
        """
        self.clip_sheet.chips["sin_clasificar"].click()

    # ------------------------------------------------------------------
    # la paleta de cuartos (`⏎`)
    # ------------------------------------------------------------------

    def _on_enter(self) -> None:
        """`⏎` abre la paleta, salvo cuando la tecla ya significa otra cosa.

        Con una fila del rail enfocada, `⏎` renombra ese cuarto; dentro de un
        campo de texto, confirma lo que escribiste. Un `QShortcut` normal se
        dispara sin importar quien tiene el foco, asi que sin esta comprobacion
        la paleta se robaria las dos cosas y nadie sabria por que dejaron de
        funcionar.
        """
        if self.escribiendo_texto() or self._foco_en_el_rail():
            return
        self.room_palette.abrir(
            self.room_selection.active_rooms(),
            self._conteos_por_cuarto(),
            len(self._bulk_target_indices()),
        )
        self._colocar_paleta()

    def _foco_en_el_rail(self) -> bool:
        foco = QApplication.focusWidget()
        return foco is not None and self.room_rail.isAncestorOf(foco)

    def _conteos_por_cuarto(self) -> dict[str, int]:
        from collections import Counter

        cuenta: Counter[str] = Counter()
        for clip in self.clips:
            if clip.categoria_path:
                cuenta[clip.categoria_path[0]] += 1
        return dict(cuenta)

    def _colocar_paleta(self) -> None:
        """Centrada sobre el video, no sobre la ventana: es donde estas
        mirando, y sobre la hoja taparia justo los clips que quieres juzgar."""
        etapa = self.video_stage
        origen = etapa.mapTo(self, etapa.rect().topLeft())
        x = origen.x() + (etapa.width() - self.room_palette.width()) // 2
        self.room_palette.move(max(0, x), origen.y() + 90)

    def _on_room_elegido_en_paleta(self, nombre: str) -> None:
        self._asignar_cuarto([nombre])

    def _on_room_creado_en_paleta(self, nombre: str) -> None:
        """Crear y asignar de una: crear y volver a apuntar serian dos pasos
        para una sola intencion."""
        self.room_selection.add(nombre)
        self._sync_rooms()
        self._asignar_cuarto([nombre])

    def _asignar_cuarto(self, room_path: list[str]) -> None:
        """Un solo camino para asignar cuarto, lo pida un digito o la `S`.

        Con dos caminos, `S` seria una asignacion de segunda: no registraria
        en el historial, o no avanzaria, y eso no se ve hasta usarla.
        """
        self._apply_categoria_to_targets(room_path)
        self._refresh_sheet()
        self._autosave()
        # «asignar cuarto y avanzar»: el clip recien resuelto suele salir de
        # la cola, y quedarse en el obligaria a apretar la flecha 128 veces
        # de mas
        self._avanzar_en_la_cola()

    def _cuarto_del_clip_anterior(self) -> str | None:
        """El cuarto del clip CON CUARTO mas cercano hacia atras.

        No es `clips[actual - 1]` a secas: si el anterior quedo sin clasificar
        se sigue buscando hacia atras, o la tecla se volveria inutil apenas te
        saltas uno. Y se mira el orden de RODAJE, no la cola filtrada: las
        rachas son consecutivas en el tiempo, y un filtro puede dejar juntos
        dos clips de cuartos distintos.
        """
        for indice in range(self.current_index - 1, -1, -1):
            categoria = self.clips[indice].categoria_path
            if categoria:
                return categoria[0]
        return None

    def _avanzar_en_la_cola(self) -> None:
        """`1`-`9` es «asignar cuarto y avanzar» (DECISIONES.md).

        Avanza solo cuando se actuo sobre UN clip: con seis seleccionados,
        avanzar es un salto sin sentido.
        """
        if len(self.selected_indices) <= 1:
            self.handle_arrow("next")

    # ------------------------------------------------------------------
    # historial: registrar antes de mutar, deshacer despues
    # ------------------------------------------------------------------

    def _detalle(self, indices: list[int]) -> str:
        """`→ clip 093` o `→ 6 clips`, como las filas del mockup."""
        if len(indices) == 1:
            return f"→ clip {self.clips[indices[0]].orden:03d}"
        return f"→ {len(indices)} clips"

    def _color_de_cuarto(self, cuarto: str) -> str:
        rooms = self.room_selection.active_rooms()
        return theme.room_color(rooms.index(cuarto)) if cuarto in rooms else theme.TEXT_3

    def _registrar(self, etiqueta: str, detalle: str, color: str,
                   clips: list[int], campos: tuple[str, ...],
                   cuarto_borrado: tuple[str, int] | None = None) -> None:
        """Guarda el estado ANTERIOR de `campos` en `clips`.

        Se llama SIEMPRE antes de mutar, nunca despues -- si no, guarda el
        estado nuevo y deshacer no hace nada. Y guarda solo los campos que la
        accion toca: con el clip entero, revertir una asignacion de cuarto se
        llevaria puesto el pick que se marco despues.
        """
        antes = {
            indice: {campo: _copiar(getattr(self.clips[indice], campo)) for campo in campos}
            for indice in clips
            if 0 <= indice < len(self.clips)
        }
        self.history.push(HistoryEntry(etiqueta, detalle, color, antes, cuarto_borrado))
        self._refresh_history()

    def _refresh_history(self) -> None:
        self.room_rail.set_history(self.history.entries())
        self.tool_column.set_can_undo(self.history.can_undo())

    def undo(self) -> None:
        """`⌘Z`: deshace la accion de arriba del historial."""
        self._aplicar_entrada(self.history.undo_last())

    def revert(self, entry_id: int) -> None:
        """El boton `↺` de una fila cualquiera, no solo la de arriba."""
        self._aplicar_entrada(self.history.revert(entry_id))

    def _aplicar_entrada(self, entrada: HistoryEntry | None) -> None:
        if entrada is None:
            return
        for indice, campos in entrada.antes.items():
            if 0 <= indice < len(self.clips):
                for campo, valor in campos.items():
                    setattr(self.clips[indice], campo, _copiar(valor))
        if entrada.cuarto_borrado is not None:
            # se REINSERTA en su posicion, que es lo que le da la tecla.
            # Restaurar la lista entera --como hacia antes-- se llevaba puesto
            # todo lo creado despues del borrado.
            nombre, posicion = entrada.cuarto_borrado
            self.room_selection.insert_at(posicion, nombre)
            self._router.active_rooms = self.room_selection.active_rooms()
        self._refresh_sheet()
        self._refresh_history()
        self._autosave()

    # ------------------------------------------------------------------
    # refresco de la UI
    # ------------------------------------------------------------------

    def _refresh_rail(self) -> None:
        from collections import Counter

        counts: Counter[str] = Counter()
        for clip in self.clips:
            if clip.categoria_path:
                counts[clip.categoria_path[0]] += 1
        rooms = self.room_selection.active_rooms()
        total = len(self.clips)
        sin_clasificar = sum(1 for c in self.clips if not c.categoria_path)
        picks = sum(1 for c in self.clips if c.flag == "pick")
        rejects = sum(1 for c in self.clips if c.flag == "reject")

        self.room_rail.set_progress(total - sin_clasificar, total, sin_clasificar)
        self.room_rail.set_rooms(rooms, dict(counts))
        destacados = sum(1 for c in self.clips if c.flag == "destacado")
        self.room_rail.set_flags(picks, rejects, sin_clasificar, destacados)
        clip = self.current_clip
        self.room_rail.set_current_room(
            clip.categoria_path[0] if clip and clip.categoria_path else None
        )
        anterior = self._cuarto_del_clip_anterior()
        self.room_rail.set_same_room(
            anterior,
            theme.room_color(rooms.index(anterior)) if anterior in rooms else None,
        )
        self.title_bar.set_project(self.project_name, total,
                                   bins=len(self.bins.nombres()))
        self.status_bar.set_unclassified(sin_clasificar)
        self.status_bar.set_proxies(*self._resumen_de_proxies())

    def _refresh_overlays(self) -> None:
        clip = self.current_clip
        stage = self.video_stage
        if self._modo_hoja:
            # sin visor no hay «clip actual» que describir, pero la forma
            # del shooting entero si importa: es la que decide la
            # orientacion de la secuencia en Premiere.
            verticales = sum(
                1 for i in range(len(self.clips))
                if i in self._clip_sizes
                and orientacion_de(*self._clip_sizes[i]) == "vertical"
            )
            conocidos = sum(1 for i in range(len(self.clips)) if i in self._clip_sizes)
            self.status_bar.set_resumen(
                len(self.clips), verticales, conocidos - verticales
            )
            return
        if clip is None:
            stage.set_file_label("")
            stage.badges.set_room(None, None)
            stage.badges.set_flag("none")
            stage.badges.set_proxy(None)
            stage.timecode_label.setText("")
            self.status_bar.set_clip_info(None, None, None, None)
            self.tool_column.set_range(None, None)
            self.tool_column.set_flag("none")
            return

        nombre = Path(clip.ruta).name
        # de que camara salio, junto al nombre: la respuesta a «¿de donde
        # salio este clip?» sin cambiar de vista
        del_bin = self.bins.bin_de(self.current_index) or ""
        # Con filtro, tu posicion en el shooting entero no te sirve de nada:
        # lo que quieres saber es cuanto falta para terminar lo que estas
        # haciendo (DECISIONES.md). Sin filtro, el total si sirve.
        if self.filters.esta_filtrando():
            indices = self.queue()
            if self.current_index in indices:
                posicion = indices.index(self.current_index) + 1
                stage.set_file_label(
                    f"{nombre}    {posicion} de {len(indices)} en la cola",
                    bin_nombre=del_bin,
                )
            else:
                # el clip actual quedo fuera del filtro -- pasa apenas lo
                # resuelves. Inventarle una posicion ("0 de 12") seria mentir
                stage.set_file_label(f"{nombre}    {len(indices)} en la cola",
                                     bin_nombre=del_bin)
        else:
            stage.set_file_label(
                f"{nombre}    {self.current_index + 1} / {len(self.clips)}",
                bin_nombre=del_bin,
            )

        cuarto = " › ".join(clip.categoria_path) if clip.categoria_path else None
        active_rooms = self.room_selection.active_rooms()
        color = (
            theme.room_color(active_rooms.index(clip.categoria_path[0]))
            if clip.categoria_path and clip.categoria_path[0] in active_rooms
            else None
        )
        stage.badges.set_room(cuarto, color)
        stage.badges.set_flag(clip.flag)

        self.status_bar.set_clip_info(
            nombre,
            self._clip_sizes.get(self.current_index),
            clip.fps,
            self._clip_rotations.get(self.current_index, 0),
        )
        self.tool_column.set_range(clip.in_frame, clip.out_frame)
        self.tool_column.set_flag(clip.flag)
        stage.badges.set_proxy(self.etiqueta_de_proxy(self.current_index))

    def etiqueta_de_proxy(self, index: int) -> str | None:
        """Que dice el badge: `"720p"`, `""` o nada.

        Se cuelga de `ruta_de_reproduccion()` a proposito. El badge no dice
        «este clip TIENE proxy», dice «esto es lo que estas viendo»: si el
        archivo ya no esta en disco se reproduce el original, y el badge se
        apaga solo. Dos vistas del mismo dato no pueden calcularlo aparte.
        """
        clip = self.clips[index]
        if self.ruta_de_reproduccion(index) == clip.ruta:
            return None
        return etiqueta_de_resolucion(*self._proxy_sizes.get(index, (0, 0)))

    # ------------------------------------------------------------------
    # el rail edita los cuartos en el lugar
    # ------------------------------------------------------------------

    def _sync_rooms(self) -> None:
        """Vuelve a pasarle al router la lista de cuartos.

        Obligatorio despues de CUALQUIER cambio del rail: el router se
        construye una sola vez y se queda con la lista que le dieron. Si no
        se vuelve a pasar, las teclas siguen apuntando a la lista vieja y no
        dan ningun sintoma visible -- clasifican al cuarto equivocado en
        silencio.
        """
        self._router.active_rooms = self.room_selection.active_rooms()
        self._refresh_sheet()
        self._autosave()

    def _on_room_created(self, nombre: str) -> None:
        self.room_selection.add(nombre)
        self._sync_rooms()

    def _on_room_renamed(self, viejo: str, nuevo: str) -> None:
        antes = self.room_selection.active_rooms()
        self.room_selection.rename(viejo, nuevo)
        if self.room_selection.active_rooms() == antes:
            return  # el nombre estaba repetido o vacio: no se toca nada
        # los clips ya clasificados viajan con el nombre: si no, quedarian
        # apuntando a un cuarto que ya no existe y desaparecerian del rail
        # sin haberse movido a ningun lado
        for clip in self.clips:
            if clip.categoria_path and clip.categoria_path[0] == viejo:
                clip.categoria_path = [nuevo]
        self._sync_rooms()

    def _on_room_moved(self, nombre: str, delta: int) -> None:
        # reordenar cambia la TECLA, no a que cuarto pertenece cada clip
        self.room_selection.move(nombre, delta)
        self._sync_rooms()

    def _on_room_removed(self, nombre: str) -> None:
        # la unica operacion del rail que destruye trabajo, y por eso la unica
        # que deja entrada en el historial: crear, renombrar y mover no pierden
        # datos y se revierten a mano en un gesto
        afectados = [
            i for i, c in enumerate(self.clips)
            if c.categoria_path and c.categoria_path[0] == nombre
        ]
        rooms = self.room_selection.active_rooms()
        self._registrar(
            etiqueta=nombre,
            detalle="cuarto borrado",
            color=self._color_de_cuarto(nombre),
            clips=afectados,
            campos=("categoria_path",),
            cuarto_borrado=(nombre, rooms.index(nombre)) if nombre in rooms else None,
        )
        self.room_selection.remove(nombre)
        # sus clips vuelven a la cola de trabajo, que es donde tienen que
        # estar: son clips que hay que volver a decidir, no clips perdidos
        for indice in afectados:
            self.clips[indice].categoria_path = []
        self._sync_rooms()

    def _tick_saved_indicator(self) -> None:
        if self._last_saved_at is None:
            return
        self.title_bar.set_saved_seconds(int(time.monotonic() - self._last_saved_at))

    def _update_scrub_bar(self) -> None:
        clip = self.current_clip
        if clip is None:
            self.scrub_bar.set_duration(0.0)
            self.scrub_bar.set_in_out(None, None, 0.0)
            self._update_timecode()
            return
        duration = self.video_widget.player.duration or self._clip_durations.get(
            self.current_index, 0.0
        )
        self.scrub_bar.set_duration(duration)
        self.scrub_bar.set_in_out(clip.in_frame, clip.out_frame, clip.fps)
        self._update_timecode()

    def _update_timecode(self) -> None:
        """El timecode va SOBRE la imagen: marcar in/out por frame exacto
        exige mirar imagen y numero sin saltar la vista.

        Desde la F6 el pie son tres piezas y no una etiqueta con todo pegado:
        el timecode grande, el numero de cuadro al lado, y la pastilla con el
        resumen del rango. El IN/OUT en texto se fue con la pastilla: es el
        mismo dato dicho dos veces, y la barra ya lo muestra con sus manijas.
        """
        clip = self.current_clip
        stage = self.video_stage
        if clip is None:
            stage.set_timecode("", None)
            stage.set_in_out_labels(None, None)
            stage.set_range_pill(None, None, 0.0)
            return
        fps = clip.fps
        pos_frame = round(self.video_widget.player.position * fps) if fps > 0 else 0
        stage.set_timecode(format_timecode(pos_frame, fps), pos_frame)
        stage.set_in_out_labels(
            format_timecode(clip.in_frame, fps) if clip.in_frame is not None else None,
            format_timecode(clip.out_frame, fps) if clip.out_frame is not None else None,
        )

        total = self.video_widget.player.duration or self._clip_durations.get(
            self.current_index, 0.0
        )
        if clip.in_frame is not None and clip.out_frame is not None and fps > 0:
            # `abs`: marcar `O` antes que `I` deja out < in, y un rango de
            # "-212 cuadros" no significa nada
            cuadros = abs(clip.out_frame - clip.in_frame)
            stage.set_range_pill(cuadros / fps, cuadros, total, fps)
        else:
            stage.set_range_pill(None, None, total, fps)

    def _tick_playhead(self) -> None:
        if self.current_clip is None:
            return
        # mpv reporta la duracion de forma ASINCRONA: cuando se abrio el clip
        # todavia no existia, asi que hay que volver a pedirsela. Sin esto la
        # barra se queda en 0 y no dibuja playhead, marcas ni rango -- estuvo
        # muerta en la app real y el arnes no lo mostraba, porque sus datos de
        # ejemplo traen la duracion escrita a mano.
        duracion = self.video_widget.player.duration or self._clip_durations.get(
            self.current_index, 0.0
        )
        if duracion and duracion != self.scrub_bar.duration:
            self.scrub_bar.set_duration(duracion)
        self.scrub_bar.set_position(self.video_widget.player.position)
        self._update_timecode()
        # El badge `▶ auto` miente en cuanto pausas: lo que arranco solo ya no
        # esta corriendo. Y no vuelve al reanudar a mano -- eso ya lo
        # arrancaste tu. Se apaga hasta el proximo cambio de clip.
        if self._auto_reproduciendo and self.video_widget.player.is_paused:
            self._auto_reproduciendo = False
            self.video_stage.badges.set_auto(False)

    def _on_scrub_seek_started(self) -> None:
        self.video_widget.player.pause()

    def _on_scrub_seek(self, seconds: float) -> None:
        self.video_widget.player.seek(seconds)
        self.scrub_bar.set_position(seconds)
        self._update_timecode()

    # ------------------------------------------------------------------
    # carga de clips
    # ------------------------------------------------------------------

    def load_clips(self, clips: list[Clip]) -> None:
        self.clips = clips
        self.current_index = 0
        # el historial guarda INDICES de clip: con material nuevo apuntarian
        # a otros clips, asi que lo de antes ya no aplica a nada
        self.history.clear()
        # y por lo mismo, los proxies: van por INDICE de clip. La ruta la
        # trae cada Clip --sobrevive a una sesion restaurada-- pero el
        # tamaño medido es de ESTE material. La importacion los vuelve a
        # llenar despues de llamar aca.
        self._proxy_sizes = {}
        self._proxy_candidatos = {}
        self._proxy_generacion_de = {}
        # Y la tanda de proxies que estuviera corriendo: engancha con
        # `self.clips[index]` sobre el material que acaba de irse. Abrir otro
        # proyecto con una generacion en curso enganchaba proxies del
        # proyecto viejo a los clips del nuevo.
        self._descartar_generacion_de_proxies()
        # las portadas en vuelo, por lo mismo: sus indices son de otro
        # material y bloquearian la extraccion de los clips nuevos
        self._miniaturas_en_vuelo = {}
        self._miniaturas_a_rehacer = set()
        # y lo que sirve para reencontrar la media, por lo mismo: el peso y
        # la ruta relativa del clip 0 de ANTES describirian al clip 0 de
        # ahora, que es otro archivo. Abrir un proyecto los vuelve a poner
        # despues de llamar aca (ver `app._poblar_ventana`).
        self._relativas = {}
        self._bytes_guardados = {}
        # y los bins: van por INDICE de clip, igual que el historial y los
        # proxies de arriba. Dejarlos vivos aca era el bug real -- una
        # sesion restaurada de 109 clips mas una carpeta importada quedaba
        # con bins apuntando a clips que ya no eran esos, y ese estado
        # corrupto se autosavea y sobrevive a cerrar la app.
        self.bins = BinTree()
        # y lo que se buscó y lo que se revisó: hablan de los bins y los
        # clips de ANTES, que no son estos.
        self._ultimo_reencuentro = {}
        self._faltantes = set()
        self._proxies_perdidos = {}
        self._sin_donde_buscar = set()
        self._exitos = {}
        # los índices se movieron: lo que venga de otro hilo describiendo a
        # los de antes ya no aplica a nadie (ver `_indices_generation`).
        self._indices_generation += 1
        self.aviso_de_media.poner([])
        self._mostrar_aviso_si_toca()
        self._refresh_history()
        self._refresh_sheet(force_rebuild=True)
        self._abrir_clip_actual()
        self._resize_video_stage()
        self._autosave()

    def agregar_clips(self, nuevos: list[Clip], nombre_de_bin: str | None,
                      origen: Path) -> None:
        """Suma material SIN reiniciar el proyecto.

        `nombre_de_bin=None` mete los clips SIN bin: quedan sueltos y la hoja
        los muestra en la seccion «Sin bin». Es un estado valido del dato --un
        clip suelto se representa por AUSENCIA de bin-- y el unico que no
        inventa un bin por el que nadie pidio.

        `load_clips` es para material nuevo y por eso limpia todo: historial,
        proxies, bins, tarjetas. Usarla para agregar es lo que hacia que al
        importar una segunda carpeta se cayeran las portadas ya generadas y
        los proxies ya enganchados.

        Aqui los indices de lo que ya estaba NO se mueven, y por eso todo lo
        que va indexado por clip --`_proxy_sizes`, `_clip_durations`,
        `_clip_sizes`, `_clip_rotations`, el historial-- sigue siendo valido
        sin tocarlo.
        """
        if not nuevos:
            return
        primero = len(self.clips)
        # ¿habia algo abierto antes? Solo si NO lo habia se abre el primero:
        # saltar al material recien importado sacaria a Bruno del clip donde
        # estaba trabajando, y agregar una tarjeta a media clasificacion es
        # justo cuando eso mas molesta.
        estaba_vacio = primero == 0
        for offset, clip in enumerate(nuevos):
            # `orden` es el numero que se ve en la tarjeta y el que viaja al
            # manifest: el que traiga el clip nuevo no sabe de los que ya
            # estaban, asi que se renumera desde el final.
            clip.orden = primero + offset + 1
            self.clips.append(clip)
        indices = list(range(primero, len(self.clips)))
        # sin bin: no se toca `self.bins`. La ausencia ES el dato -- no hay
        # que anotar los sueltos en ningun lado para que la hoja los junte en
        # su seccion.
        if nombre_de_bin is not None:
            if nombre_de_bin in self.bins.nombres():
                # con el origen: el bin tiene que ampliar su carpeta cuando
                # le cae material de otra --la segunda tarjeta de la misma
                # camara-- o esos clips se quedan sin ruta relativa y no hay
                # forma de reencontrarlos en otra computadora
                self.bins.sumar(nombre_de_bin, indices, origen)
            else:
                self.bins.agregar(nombre_de_bin, origen, indices)
        self._refresh_sheet()
        # solo las portadas de los nuevos: las que ya estan no se rehacen.
        # Y si Bruno acepta crear los proxies primero, no se piden todavia:
        # del proxy cuestan 5 veces menos (medido: 5.8 s contra 1.2 s por
        # clip) y hacerlas ahora seria pagar el precio caro justo antes de
        # que exista el barato.
        if not self._ofrecer_proxies_antes(nombre_de_bin, indices):
            self._schedule_thumbnails(indices)
        if estaba_vacio:
            self.current_index = 0
            # por `_abrir_clip_actual` y no abriendo a mano: es el unico
            # camino que abre un clip, a proposito (ver su docstring).
            self._abrir_clip_actual()
            self._resize_video_stage()
        self._autosave()

    def _ofrecer_proxies_antes(self, nombre_de_bin: str | None,
                               indices: list[int]) -> bool:
        """«Este bin no tiene proxies, ¿te los creo primero?»

        Devuelve True si se aceptó, y entonces las portadas de esos clips NO
        se piden ahora: cada una sale sola en cuanto su proxy se engancha
        (`_sondear_proxies` las vuelve a pedir con la fuente nueva).

        Se pregunta en vez de decidirlo la app porque las dos respuestas son
        razonables: generar son minutos, y a veces uno solo quiere ver qué
        trajo la tarjeta. Bruno lo eligió así el 2026-08-10.
        """
        if nombre_de_bin is None or not indices:
            return False
        if self._generando_proxies is not None:
            return False        # ya hay una tanda corriendo; no encimar otra
        if any(self.clips[i].ruta_proxy is not None for i in indices):
            return False        # este bin ya tiene proxies enganchados
        eleccion = self._preguntar_que_hacer_con_proxies(nombre_de_bin, indices)
        if eleccion == "crear":
            self.generar_proxies_de_bin(nombre_de_bin, preguntar=False)
            # si por lo que sea no arrancó, las portadas no se pueden quedar
            # esperando a algo que no va a pasar
            return self._generando_proxies is not None
        if eleccion == "enlazar":
            self.adjuntar_proxies_de_bin(nombre_de_bin)
            # Si enganchó, `_sondear_proxies` ya volvió a pedir las portadas
            # de esos clips —con el proxy como fuente— y no hay que pedirlas
            # otra vez. Si no enganchó nada —cancelaste el diálogo, o ningún
            # archivo calzó— hay que sacarlas del original o esas tarjetas se
            # quedan en gris.
            return any(i in self._proxy_candidatos for i in indices)
        return False

    def _preguntar_que_hacer_con_proxies(self, nombre_de_bin: str,
                                         indices: list[int]) -> str:
        """«enlazar», «crear» o «nada».

        Las dos salidas buenas van juntas en un solo diálogo porque la
        respuesta correcta depende de la cámara y uno no quiere pensarlo dos
        veces: la Sony ya escribe sus proxies —esos se ENLAZAN— y el dron no
        —esos se CREAN—. Ofrecer solo «crear» mandaba a generar de cero
        proxies que ya existían en el disco.

        Va con botones propios y no con `QMessageBox.question`: con los
        botones estándar, «enlazar» tendría que llamarse «No» o «Abrir», y el
        renglón más importante del diálogo se leería al revés.
        """
        minutos = max(1, round(self._segundos_estimados(indices) / 60))
        dialogo = QMessageBox(self)
        dialogo.setWindowTitle("Proxies")
        dialogo.setText(f"«{nombre_de_bin}» no tiene proxies.")
        dialogo.setInformativeText(
            "Con proxies el material se navega fluido y las portadas de la "
            "hoja salen cinco veces más rápido.\n\n"
            "Si esta cámara ya los grabó, enlázalos. Si no, se pueden crear "
            f"desde los originales (unos {minutos} min, en segundo plano)."
        )
        enlazar = dialogo.addButton("Enlazar los que ya tengo…",
                                    QMessageBox.ButtonRole.AcceptRole)
        crear = dialogo.addButton("Crear los proxies",
                                  QMessageBox.ButtonRole.AcceptRole)
        dialogo.addButton("Ahora no", QMessageBox.ButtonRole.RejectRole)
        dialogo.setDefaultButton(enlazar)
        dialogo.exec()
        elegido = dialogo.clickedButton()
        if elegido is enlazar:
            return "enlazar"
        if elegido is crear:
            return "crear"
        return "nada"

    def _autosave(self) -> None:
        if self.session_path is None:
            return
        # no escribe ahora: reinicia el debounce, para escribir una sola vez
        # por rafaga de teclas en vez de una vez por tecla.
        self._autosave_timer.start()

    def _write_autosave_now(self) -> None:
        if self.session_path is None:
            return
        # La forma del documento la arma `proyecto.a_dict` y no esta funcion:
        # antes habia dos --la de aqui y la del modulo-- y dos formas del
        # mismo documento terminan desincronizandose, con la mitad de las
        # llaves escribiendose desde un lado y leyendose desde el otro.
        #
        # `bytes_conocidos` NO es opcional en la practica: sin el, guardar
        # con la media desconectada reescribe el archivo sin un solo peso, y
        # despues ya no hay con que confirmar que un archivo reencontrado es
        # el que era. Pasa solo, a los pocos segundos de abrir el proyecto.
        data = proyecto.a_dict(
            proyecto=self.project_name,
            rooms=self.room_selection.active_rooms(),
            clips=self.clips,
            bins=self.bins,
            tamanos=self._clip_sizes,
            duraciones=self._clip_durations,
            rotaciones=self._clip_rotations,
            bytes_conocidos=self._bytes_guardados,
            # las que ya se sabian, de respaldo: reconectar a medias deja al
            # bin colgando de la carpeta nueva y al clip que sigue perdido
            # apuntando a la vieja, y ahi la relativa ya no se puede
            # calcular. Tirarla lo dejaria sin con que reencontrarse.
            relativas_conocidas=self._relativas,
        )
        self._relativas = {int(i): str(r) for i, r in data["relativas"].items()}
        # El indicador NO se toca aqui. Antes decia «guardado» apenas se
        # encolaba el trabajo, o sea antes de que nadie hubiera escrito nada:
        # con el disco desconectado seguia contando segundos toda la sesion
        # mientras el archivo no se tocaba. Ahora lo mueve el resultado real
        # (`_on_guardado_listo` / `_on_guardado_fallo`).
        self._autosave_pool.start(
            _AutosaveWriteJob(self.session_path, data, self._indices_generation,
                              self._señales_de_trabajos)
        )

    def _on_guardado_listo(self) -> None:
        self._last_saved_at = time.monotonic()
        self._tick_saved_indicator()

    def _on_guardado_fallo(self, motivo: str) -> None:
        """El proyecto no se pudo escribir. Se dice y se deja de contar.

        No hay reintento ni cartel: el autoguardado vuelve a intentarlo a la
        siguiente edicion, y para entonces el disco puede estar de vuelta. Lo
        que no puede pasar es que el indicador siga prometiendo que guardo.
        """
        self._last_saved_at = None
        self.title_bar.set_no_guardado(motivo)

    def _flush_autosave(self) -> None:
        """Fuerza el guardado pendiente ya mismo -- al cerrar la ventana,
        para no perder la ultima edicion si cae dentro del debounce."""
        if self._autosave_timer.isActive():
            self._autosave_timer.stop()
            self._write_autosave_now()
        self._autosave_pool.waitForDone(2000)

    # ------------------------------------------------------------------
    # reencontrar la media (spec §5)
    # ------------------------------------------------------------------

    def revisar_media(self, luego_portadas: bool = False) -> None:
        """¿Están los archivos donde el proyecto dice? Si no, se avisa.

        Se llama al abrir un proyecto. No es una excepción: abrirlo en otra
        computadora quiere decir que **ninguna** ruta va a coincidir, y por
        eso se pregunta de inmediato en vez de esperar a que Bruno haga clic
        en un clip y no pase nada.

        **Corre fuera del hilo de la interfaz** (ver `_RevisionDeMediaJob`).
        Barato no es: son `stat` uno por clip en serie, y sobre un volumen
        montado e incomunicado cada uno se traba hasta el timeout — que es
        exactamente el disco de red del que puede colgar este proyecto.
        """
        # una revisión nueva empieza de cero: lo que se buscó antes hablaba
        # de otras carpetas y otros archivos. Lo que NO se limpia es
        # `_faltantes`: se reemplaza cuando llega el resultado, para que la
        # barra no parpadee a vacío mientras tanto.
        self._ultimo_reencuentro = {}
        self._exitos = {}
        self._portadas_tras_revisar = luego_portadas
        self._revision_generation += 1
        self._revision_pool.start(_RevisionDeMediaJob(
            self._revision_generation,
            {i: c.ruta for i, c in enumerate(self.clips)},
            {i: c.ruta_proxy for i, c in enumerate(self.clips)
             if c.ruta_proxy is not None},
            self._señales_de_trabajos,
        ))

    def _on_media_revisada(self, generacion: int, faltantes: list,
                           proxies_perdidos: dict) -> None:
        if generacion != self._revision_generation:
            return  # una revisión que ya quedó vieja
        self._faltantes = {int(i) for i in faltantes}
        self._proxies_perdidos = {int(i): str(n)
                                  for i, n in proxies_perdidos.items()}
        self._revisiones_terminadas += 1
        self._refrescar_aviso()
        if self._portadas_tras_revisar:
            # Al abrir, las portadas se piden DESPUÉS de saber qué hay: antes
            # se pedían primero, así que `_faltantes` estaba vacío y se
            # encolaba un trabajo por cada archivo inexistente. Una sola
            # tanda completa, igual que antes -- la generación no sube de más.
            self._portadas_tras_revisar = False
            self._schedule_thumbnails()

    def _on_pesos_medidos(self, generacion: int, pesos: dict) -> None:
        """Los pesos que midió el hilo del guardado, de vuelta en la ventana.

        Con la guarda de generación: si entre que arrancó el guardado y que
        llegó esto se quitó un bin, los índices ya se corrieron y el peso
        describiría al clip equivocado — y con ese peso es con lo que
        después se confirma que un archivo reencontrado es el que era.
        """
        if generacion != self._indices_generation:
            return
        self._bytes_guardados.update(
            {int(i): int(t) for i, t in pesos.items()
             if isinstance(t, int) and not isinstance(t, bool)}
        )

    def reconectar_bin(self, nombre: str, carpeta: Path) -> None:
        """Busca bajo `carpeta` los clips que le faltan al bin y los engancha.

        Lo que no se confirma **no se engancha**, y cada motivo se dice
        aparte: las cámaras repiten los nombres --la Sony numera `C0001.MP4`
        en cada tarjeta que formateas-- y enganchar el archivo equivocado
        sería peor que no encontrarlo, porque Bruno no se enteraría.

        Esto NO mueve índices: cambia la ruta de un clip que sigue siendo el
        mismo clip, en el mismo lugar de la lista. Por eso no hay nada
        indexado por clip que correr.
        """
        if self._buscando is not None:
            return          # ya hay una búsqueda corriendo (ver `_mientras_busca`)
        faltantes = self._faltantes_de_bin(nombre)
        if not faltantes:
            return
        # ESTO CORRE EN EL HILO DE LA INTERFAZ, a diferencia de `revisar_media`,
        # y es a propósito: aquí Bruno acaba de dar un clic y de elegir una
        # carpeta, así que una espera se entiende --al abrir un proyecto no
        # entendería nada--, y volverlo asíncrono le cambiaría la forma a todo
        # lo que lo prueba a cambio de un beneficio que nadie midió.
        #
        # Lo que haría cambiar de opinión: que alguien lo MIDA y duela. Recorre
        # el árbol de la carpeta (`indice_de_nombres`) y corre un ffprobe por
        # candidato --26.7 ms cada uno-- así que una tarjeta de 128 GB con los
        # 109 clips de la Sony es el caso donde esto se va a sentir. Si eso
        # pasa, el camino es el mismo que ya tomó `_RevisionDeMediaJob`.
        with self._mientras_busca(nombre, ACCION_MEDIA):
            resultado = revinculo.reencontrar_bin(
                carpeta,
                {i: self._relativas[i] for i in faltantes if i in self._relativas},
                {i: self._bytes_guardados[i] for i in faltantes
                 if i in self._bytes_guardados},
                revinculo.cuadros_esperados_de(
                    self._clip_durations,
                    {i: c.fps for i, c in enumerate(self.clips)},
                ),
                self._probe_clip,
            )
        self._ultimo_reencuentro[nombre] = resultado
        # los que ni se buscaron: sin ruta relativa no hay con qué buscarlos.
        # Van aparte de «no apareció en esa carpeta», que suena a que basta
        # con probar en otra — a estos no los salva ninguna carpeta.
        self._sin_donde_buscar = {
            i for i in faltantes if i not in self._relativas
        } | (self._sin_donde_buscar - set(faltantes))
        if resultado.reconectados:
            reconectados = sorted(resultado.reconectados)
            for indice, ruta in resultado.reconectados.items():
                self.clips[indice].ruta = ruta
            self._faltantes -= set(reconectados)
            self._exitos[nombre] = len(reconectados)
            self._timer_de_exito.start()
            # el bin pasa a colgar de la carpeta nueva, no del ancestro
            # común con la vieja: la vieja no existe en esta computadora.
            # Solo si algo enganchó -- señalar la carpeta equivocada no
            # puede borrar de dónde salió el material.
            self.bins.fijar_origen(nombre, carpeta)
            # ANTES de las portadas: el proxy es de donde se extraen, y
            # dejar el candidato viejo apuntando a una ruta muerta deja la
            # tarjeta sin portada y sin explicación.
            #
            # Y las portadas las pide ÉL, con el mismo alcance: al final de
            # `_sondear_proxies` ya hay una llamada acotada a estos índices.
            # Pedirlas otra vez aquí era el segundo trabajo por clip sobre la
            # misma carpeta de salida y el mismo socket IPC — justo el daño
            # que acotar el alcance existe para evitar.
            self._reenganchar_proxies(reconectados, carpeta)
            self._refresh_sheet()
            # y se guarda, para que la próxima vez abra sin preguntar
            self._autosave()
        self._refrescar_aviso()

    def reconectar_proxies_de_bin(self, nombre: str, carpeta: Path) -> None:
        """El «Buscar proxies…»: solo los proxies, en su propia carpeta.

        Existe aparte porque el proxy vive aparte —`sample-media/` los separa
        en `clips/` y `proxy/`, como llegan de la cámara— así que la carpeta
        que Bruno señaló para los originales muchas veces no los tiene.
        """
        if self._buscando is not None:
            return
        indices = [i for i in self.bins.clips_de(nombre)
                   if i in self._proxies_perdidos]
        if indices:
            with self._mientras_busca(nombre, ACCION_PROXIES):
                self._reenganchar_proxies(indices, carpeta)
            self._refrescar_aviso()

    def _reenganchar_proxies(self, indices: list[int], carpeta: Path) -> None:
        """Busca bajo `carpeta` el proxy de cada clip, por su nombre.

        El proyecto no guarda la ruta relativa del proxy, solo la absoluta
        —que en otra computadora no existe—, así que lo único que queda es
        el nombre del archivo. Se valida como siempre, cuadro a cuadro, por
        `_sondear_proxies`: un proxy corrido pone el in/out en el cuadro
        equivocado.

        Sin esto, después de reconectar todo el proyecto navega sobre el 4K
        HEVC: 530 ms por cuadro contra 22 (ver `ruta_de_reproduccion`).
        """
        # el nombre del proxy, ANTES de que `_sondear_proxies` lo limpie
        nombres = {}
        for i in indices:
            viejo = self.clips[i].ruta_proxy
            nombre = self._proxies_perdidos.get(i)
            if nombre is None and viejo is not None:
                nombre = Path(viejo).name
            if nombre:
                nombres[i] = nombre
        if not nombres:
            # ni un proxy que reenganchar, pero los candidatos viejos siguen
            # apuntando a rutas muertas: hay que limpiarlos igual.
            self._sondear_proxies({}, indices=list(indices))
            return
        indice_de_nombres = revinculo.indice_de_nombres(carpeta)
        emparejados: dict[Path, Path | None] = {}
        for i, nombre in nombres.items():
            hallado = revinculo.buscar_bajo(carpeta, nombre, indice_de_nombres)
            emparejados[self.clips[i].ruta] = hallado
            if hallado is None:
                self._proxies_perdidos[i] = nombre
            else:
                self._proxies_perdidos.pop(i, None)
        self._sondear_proxies(emparejados, indices=list(indices))

    @contextmanager
    def _mientras_busca(self, nombre: str, accion: str):
        """Deja a la vista que está buscando, y no deja lanzar dos búsquedas.

        Buscar corre en el hilo de la interfaz (ver `reconectar_bin`), así
        que durante ese rato la ventana no se redibuja sola: sin esto se
        queda muda y congelada, y una app congelada sin ninguna señal se lee
        como que tronó. Por eso el `repaint()`, que pinta ya mismo en vez de
        anotar un pedido que nadie va a atender hasta que esto termine.

        `repaint()` y no `processEvents()`: lo segundo entrega también los
        clics que estén esperando, y el primero de esos sería otro «Buscar…»
        encima de este. La guarda de reentrada está igual, porque un botón
        apagado es una promesa de la interfaz y no del dato.
        """
        self._buscando = (nombre, accion)
        try:
            self._refrescar_aviso()
            # `activate()` ANTES de repintar, y no es un detalle: los
            # renglones se acaban de crear y todavia no tienen ni posicion ni
            # alto --el layout los coloca cuando corre, y no va a correr
            # hasta que esto termine--. Sin esto, `repaint()` dibujaba una
            # barra en blanco: el hueco estaba, el texto no. Visto en la
            # captura, no en un test.
            self.layout().activate()
            self.aviso_de_media.repaint()
            yield
        finally:
            self._buscando = None

    def _faltantes_de_bin(self, nombre: str) -> list[int]:
        """Qué clips del bin ya no tenían su archivo en la última revisión.

        Del cache y no del disco: esto lo llama `_refrescar_aviso`, que corre
        en cada renombrado de bin y en cada reconexión, y cada barrido son
        `stat` uno por clip en el hilo de la interfaz.
        """
        return [i for i in self.bins.clips_de(nombre) if i in self._faltantes]

    def _olvidar_exitos(self) -> None:
        """Borra los renglones verdes. Los llama un timer: «1 clip
        reconectado» no puede quedarse el resto de la sesión robándole alto
        al video por algo que ya salió bien."""
        if self._exitos:
            self._exitos = {}
            self._refrescar_aviso()

    def _renglones_del_bin(self, nombre: str) -> list[Renglon]:
        """Un renglón por cada final, y cada uno con sus palabras.

        Mezclarlos sería mentirle a Bruno en un momento de confusión: «no
        apareció» es que no hay nada, «no coincide» es que hay un archivo
        con ese nombre que NO es el mismo, «se pelean» es que sí calzaba
        pero lo reclamaron dos, y «no hay con qué comprobar» es que nadie
        comparó nada.
        """
        if self._buscando is not None and self._buscando[0] == nombre:
            # mientras busca, ese bin dice UNA cosa: que está buscando. Lo
            # de antes ya no describe nada -- se está averiguando ahorita.
            _, accion = self._buscando
            de_proxies = accion == ACCION_PROXIES
            return [Renglon(
                nombre,
                "Buscando los proxies en esa carpeta…" if de_proxies
                else "Buscando en esa carpeta…",
                tono=TONO_FALTA,
                boton="Buscar proxies…" if de_proxies else "Buscar…",
                accion=accion,
                boton_activo=False,
            )]
        faltan = set(self._faltantes_de_bin(nombre))
        renglones: list[Renglon] = []
        exito = self._exitos.get(nombre)
        if exito:
            renglones.append(Renglon(nombre, _cuantos_reconectados(exito),
                                     tono=TONO_OK))
        resultado = self._ultimo_reencuentro.get(nombre)
        if resultado is None:
            if faltan:
                renglones.append(Renglon(nombre, _cuantos_faltan(len(faltan)),
                                         tono=TONO_FALTA, quiere_buscar=True))
        else:
            sin_buscar = faltan & self._sin_donde_buscar
            for indices, texto, tono, quiere in (
                (resultado.sin_confirmar, _cuantos_no_coinciden,
                 TONO_ALERTA, True),
                (resultado.disputados, _cuantos_se_pelean, TONO_ALERTA, True),
                (resultado.sin_comprobar, _cuantos_sin_comprobar,
                 TONO_ALERTA, False),
                (resultado.no_encontrados, _cuantos_no_aparecieron,
                 TONO_FALTA, True),
                (sorted(sin_buscar), _cuantos_sin_donde_buscar,
                 TONO_FALTA, False),
            ):
                cuantos = len([i for i in indices if i in faltan])
                if cuantos:
                    renglones.append(Renglon(nombre, texto(cuantos), tono=tono,
                                             quiere_buscar=quiere))
        # el proxy solo se menciona cuando el original YA está: mientras
        # falta el original, el problema grande es ese.
        sin_proxy = [i for i in self.bins.clips_de(nombre)
                     if i in self._proxies_perdidos and i not in faltan]
        if sin_proxy:
            renglones.append(Renglon(
                nombre, _cuantos_sin_proxy(len(sin_proxy)), tono=TONO_FALTA,
                boton="Buscar proxies…", accion=ACCION_PROXIES))
        return renglones

    def _refrescar_aviso(self) -> None:
        """Arma la barra entera y decide si se ve."""
        renglones: list[Renglon] = []
        for nombre in self.bins.nombres():
            del_bin = self._renglones_del_bin(nombre)
            # UN solo «Buscar…» por bin: dos botones idénticos en el mismo
            # bin hacen exactamente lo mismo. Se lo lleva el primer renglón
            # al que le sirva. El de proxies es otra acción y otra etiqueta,
            # así que no compite con este.
            ya_hay = False
            for renglon in del_bin:
                if renglon.quiere_buscar and not ya_hay:
                    renglon.boton = "Buscar…"
                    renglon.accion = ACCION_MEDIA
                    ya_hay = True
                # y mientras una búsqueda corre se apagan TODOS, no solo los
                # de su bin: el hilo de la interfaz está ocupado con esa, y
                # un botón que se ve prendido promete algo que no va a pasar.
                if self._buscando is not None:
                    renglon.boton_activo = False
            renglones.extend(del_bin)
        self.aviso_de_media.poner(renglones)
        self._mostrar_aviso_si_toca()

    def _mostrar_aviso_si_toca(self) -> None:
        """La ÚNICA regla de visibilidad de la barra.

        Vivía repartida entre el widget --que se escondía solo al quedar
        vacío-- y `alternar_solo_video`, y solo una de las dos sabía del
        modo: poner renglones podía hacerla reaparecer encima del video a
        pantalla completa.
        """
        self.aviso_de_media.setVisible(
            self.aviso_de_media.tiene_avisos() and not self._solo_video
        )
        # el aviso ocupa su renglón: sin recalcular, el video se queda con
        # el alto de antes y se sale por abajo de la ventana.
        self._resize_video_stage()

    def _on_buscar_media(self, nombre: str, accion: str) -> None:
        """Los botones de la barra. Selector del sistema, que es el único
        diálogo que el spec §8 deja usar."""
        origen = self.bins.origen_de(nombre)
        arranque = str(origen) if origen is not None else ""
        if accion == ACCION_PROXIES:
            titulo = f"¿Dónde quedaron los proxies de «{nombre}»?"
        else:
            titulo = f"¿Dónde quedó el material de «{nombre}»?"
        carpeta = QFileDialog.getExistingDirectory(self, titulo, arranque)
        if not carpeta:
            return
        if accion == ACCION_PROXIES:
            self.reconectar_proxies_de_bin(nombre, Path(carpeta))
        else:
            self.reconectar_bin(nombre, Path(carpeta))

    def _medir(self, archivos: list[Path],
               desde: int = 0) -> tuple[list[Clip], dict[str, dict]]:
        """Corre `ffprobe` sobre cada archivo y arma los `Clip`.

        Vive aparte de `importar_rutas` para separar leer el disco de
        decidir a que bin va lo leido: la parte cara y la parte con reglas.

        `desde` es el indice del primer clip nuevo: todo lo que la ventana
        guarda por INDICE de clip (duraciones, tamaños, rotaciones) sale de
        aqui ya corrido, para que agregar no pise lo que ya estaba.
        Los archivos que no se pueden leer se saltan, no cortan la tanda.
        """
        clips: list[Clip] = []
        duraciones: dict[int, float] = {}
        tamanos: dict[int, tuple[int, int]] = {}
        rotaciones: dict[int, int] = {}
        # En paralelo, y NO por gusto: `ffprobe` cuesta 25.5 ms por clip y
        # esto corre en el hilo de la interfaz, asi que con los 132 clips de
        # Bruno eran 3.4 s de ventana congelada al importar. Medido sobre 40
        # clips reales suyos: en serie 1.06 s, con 8 en paralelo 0.14 s --
        # siete veces y media--. Cada `ffprobe` es un proceso aparte, o sea
        # que el GIL no estorba: el hilo se pasa la vida esperando.
        #
        # El resultado se recoge EN ORDEN (`map` lo garantiza) porque el
        # orden de los clips es el orden en que se ven y el que viaja al
        # manifest.
        with ThreadPoolExecutor(SONDEOS_EN_PARALELO) as sondeadores:
            infos = list(sondeadores.map(self._sondear_sin_reventar, archivos))
        for video, info in zip(archivos, infos):
            if info is None:
                continue
            index = desde + len(clips)
            clips.append(Clip(orden=index + 1, ruta=video, categoria_path=[],
                              fps=info["fps"]))
            fps = info.get("fps") or 0
            duration_frames = info.get("duration_frames")
            if fps and duration_frames:
                # duracion real del clip, solo en memoria -- no toca el
                # contrato del manifest.
                duraciones[index] = duration_frames / fps
            width = info.get("width") or 0
            height = info.get("height") or 0
            if width and height:
                # tamaño real ya corregido por rotacion (ver probe.py):
                # de aqui sale la relacion de aspecto que decide el ancho
                # del video y la forma de la miniatura.
                tamanos[index] = (int(width), int(height))
            rotaciones[index] = int(info.get("rotation") or 0)
        return clips, {"duraciones": duraciones, "tamanos": tamanos,
                       "rotaciones": rotaciones}

    def _sondear_sin_reventar(self, video: Path) -> dict | None:
        """`None` en vez de excepcion: un archivo ilegible se salta, no
        corta la tanda. Y va aparte para poder mandarlo al pool de hilos --
        una excepcion adentro de `map` si cortaria todo."""
        try:
            return self._probe_clip(video)
        except Exception:
            return None

    def _avisar_que_no_se_pudo_leer_nada(self, cuantos: int) -> None:
        """Si NINGUNO se pudo leer, no es un archivo corrupto: es que falta
        el programa que lee los videos. Sin este aviso el sintoma era una
        carpeta importada con cero clips y ninguna explicacion -- y en la
        computadora de un compañero, sin ffprobe, ese seria el sintoma de
        todo. Encontrado armando el paquete.
        """
        QMessageBox.warning(
            self, "No se pudo leer el material",
            f"Se encontraron {cuantos} archivos de video pero no se pudo leer "
            "ninguno.\n\nSuele significar que falta el programa que la app usa "
            "para leerlos (ffprobe).",
        )

    def importar_rutas(self, rutas: list[Path], nombre_de_bin: str | None = None,
                       origen: Path | None = None, sueltos: bool = False) -> None:
        """El unico camino de entrada de material nuevo.

        Sirve al boton de importar y al arrastre. Si no se dice a que bin
        van, se crea uno con el nombre de la carpeta de donde vienen.

        `sueltos=True` es el tercer destino, y es distinto de no decir nada:
        el material entra SIN bin y cae en la seccion «Sin bin». Lo usa el
        arrastre soltado sobre esa seccion. Va como bandera y no como un
        nombre reservado a proposito -- un nombre se puede escribir a mano en
        el campo de renombrar, y ahi volveria el bug que esto arregla.

        Lo que ya esta en el proyecto se descarta: importar dos veces la
        misma tarjeta no puede dejar cada plano duplicado.
        """
        archivos = archivos_de_video(rutas)
        if not archivos:
            # spec §4.3: los dos casos de «no paso nada» se ven igual y son
            # distintos -- en este elegiste la carpeta equivocada.
            QMessageBox.information(
                self, "Nada que importar",
                "En lo que elegiste no hay archivos de video que la app "
                "reconozca.\n\nSe aceptan .mp4, .mov y .mxf. Los proxies de "
                "cámara (los que terminan en S03 y los .LRF del dron) se "
                "descartan a propósito.",
            )
            return
        ya_estan = {c.ruta for c in self.clips}
        nuevos_archivos = [a for a in archivos if a not in ya_estan]
        if not nuevos_archivos:
            # y en este ya lo habias importado. Un duplicado suelto dentro de
            # una tanda con material nuevo si se ignora en silencio: el aviso
            # es para el gesto que no hizo nada entero.
            QMessageBox.information(
                self, "Ya están en el proyecto",
                f"Los {len(archivos)} clips que elegiste ya están importados, "
                "así que no se agregó nada.",
            )
            return
        archivos = nuevos_archivos
        # La carpeta de la tanda es la que cubre a TODOS los archivos que
        # van a entrar, no la del primero: soltando dos carpetas a la vez,
        # lo demas quedaba colgando de una carpeta que no lo contiene, o
        # sea sin ruta relativa y sin forma de reencontrarlo en otra
        # computadora. Hasta donde subir lo decide `raiz_comun_de`, que es
        # la unica definicion de «demasiado arriba» del repo.
        carpeta = origen or raiz_comun_de([a.parent for a in archivos])
        nuevos, medidas = self._medir(archivos, desde=len(self.clips))
        if not nuevos:
            self._avisar_que_no_se_pudo_leer_nada(len(archivos))
            return
        self._clip_durations.update(medidas["duraciones"])
        self._clip_sizes.update(medidas["tamanos"])
        self._clip_rotations.update(medidas["rotaciones"])
        self.agregar_clips(
            nuevos, None if sueltos else (nombre_de_bin or carpeta.name), carpeta
        )

    def adjuntar_proxies(self) -> None:
        """El boton «Proxies» de la barra: aplica al bin del clip actual.

        Ya no tiene sentido como accion global. El patron de nombre es de
        una CAMARA --la Sony escribe `C0001S03.MP4`, el dron se genera con
        otro nombre-- y aplicarlo a todo el proyecto dejaba siempre a una
        de las dos camaras sin proxy.
        """
        nombre = self.bins.bin_de(self.current_index)
        if nombre is None:
            QMessageBox.warning(self, "Sin material",
                                "Primero importa los clips y luego engancha sus proxies.")
            return
        self.adjuntar_proxies_de_bin(nombre)

    def adjuntar_proxies_de_bin(self, nombre_de_bin: str,
                                elegido: Path | None = None) -> None:
        """El «Enlazar proxies…» del menu del bin.

        Eliges CUALQUIER proxy de ESE bin: la app averigua a que clip
        corresponde por el nombre, y de ese par sale el patron para los
        demas --`C0001.MP4` + `C0001S03.MP4` da el sufijo `S03`--, con el
        que se buscan los otros en esa carpeta. Es a mano y solo a mano, por
        pedido de Bruno.

        Cada uno se valida igual que siempre (mismos cuadros, mismo fps,
        misma orientacion): el que no calce no se engancha, porque un proxy
        corrido pone el in/out en el cuadro equivocado.
        """
        indices = self.bins.clips_de(nombre_de_bin)
        if not indices:
            return
        rutas_del_bin = [self.clips[i].ruta for i in indices]
        # desde donde abre el dialogo: el clip que estabas mirando si es de
        # este bin, y si no el primero. Solo decide la carpeta inicial --a
        # cual clip corresponde el proxy se averigua despues, del nombre.
        arranque = self.clips[
            self.current_index if self.current_index in indices else indices[0]
        ]
        if elegido is None:
            ruta, _ = QFileDialog.getOpenFileName(
                self,
                f"Elige cualquier proxy de «{nombre_de_bin}»",
                str(arranque.ruta.parent),
                "Video (*.mp4 *.MP4 *.mov *.MOV *.mxf *.MXF)",
            )
            if not ruta:
                return
            elegido = Path(ruta)
        # CUALQUIERA de los proxies del bin sirve. Antes tenia que ser el del
        # clip en el que estabas parado, y eso no se ve por ningun lado:
        # abres el dialogo, ves 111 proxies ordenados por nombre y eliges el
        # primero. Bruno se topo justo con eso. El patron sale igual de bien
        # de cualquier par; lo unico que hacia falta era averiguar de que par
        # se trata.
        referencia = clip_del_proxy(rutas_del_bin, elegido)
        patron = patron_de_proxy(referencia, elegido) if referencia else None
        if patron is None:
            QMessageBox.warning(
                self, "Ese archivo no corresponde",
                f"«{elegido.name}» no lleva adentro el nombre de ningún clip "
                f"de «{nombre_de_bin}», así que no se puede deducir cómo se "
                "llaman los demás proxies.\n\nElige un proxy de este bin — "
                "cualquiera sirve, no tiene que ser el del clip que estás "
                "viendo.",
            )
            return
        prefijo, sufijo = patron
        emparejados = emparejar_con_patron(
            [self.clips[i].ruta for i in indices],
            elegido.parent, prefijo, sufijo, elegido.suffix,
        )
        encontrados = sum(1 for v in emparejados.values() if v is not None)
        QMessageBox.information(
            self, "Proxies",
            # contra los clips del BIN, no contra el proyecto entero: «0 de
            # 109» cuando el bin tiene 1 clip seria mentira.
            f"Se encontraron {encontrados} de {len(indices)}.\n\n"
            "Se están comprobando uno por uno: solo se enganchan los que "
            "coinciden cuadro a cuadro con su original.",
        )
        self._sondear_proxies(emparejados, indices=indices)

    # --- crear los proxies (F11) ------------------------------------------

    def generar_proxies_de_bin(self, nombre_de_bin: str,
                               preguntar: bool = True) -> None:
        """El «Crear proxies del bin…» del menu.

        Nace por el dron: la Sony escribe sus proxies sola y el DJI escribe
        un `.LRF` que NO sirve --contenido corrido entre 0 y 5 cuadros,
        variable por toma-- asi que la unica via es generarlos del original.

        Se generan uno por uno, en segundo plano, y **cada uno se engancha
        apenas termina** en vez de esperar a que acabe la tanda: con 23
        tomas son varios minutos, y ver el material aligerarse conforme
        avanza es lo que hace que la espera no se sienta muerta.
        """
        if self._generando_proxies is not None:
            QMessageBox.information(
                self, "Ya se están creando",
                f"Se están creando los proxies de «{self._generando_proxies['bin']}». "
                "Espera a que termine, o cancélalo desde el menú de ese bin.",
            )
            return
        indices = [i for i in self.bins.clips_de(nombre_de_bin)
                   if 0 <= i < len(self.clips)]
        if not indices:
            return
        # La carpeta sale del PRIMER clip del bin. Con un bin que junta dos
        # tarjetas de la misma camara, los proxies de las dos terminan en el
        # mismo lugar --al lado de la primera-- en vez de uno por tarjeta.
        # Es a proposito: `faltantes` mira ahi mismo, asi que sigue sin
        # rehacer lo hecho, y un solo lugar es mas facil de encontrar que dos.
        carpeta = proxy_gen.carpeta_de_proxies(self.clips[indices[0]].ruta.parent)
        # solo los que no tienen proxy YA ENGANCHADO y no tienen archivo en
        # la carpeta de proxies: volver a darle no rehace lo hecho.
        candidatos = [i for i in indices if self.clips[i].ruta_proxy is None]
        pendientes = [
            i for i in candidatos
            if not proxy_gen.ruta_de_proxy(self.clips[i].ruta, carpeta).exists()
        ]
        if not pendientes:
            QMessageBox.information(
                self, "Ya están",
                f"Todos los clips de «{nombre_de_bin}» ya tienen proxy.",
            )
            return
        if preguntar:
            # el tiempo va en el aviso porque es lo unico que uno quiere
            # saber antes de decir que si, y son minutos, no segundos
            minutos = max(1, round(self._segundos_estimados(pendientes) / 60))
            respuesta = QMessageBox.question(
                self, "Crear proxies",
                f"Se van a crear {len(pendientes)} proxies de «{nombre_de_bin}».\n\n"
                f"Tarda unos {minutos} min y se guardan en «{carpeta.name}», "
                f"al lado de tus clips. Puedes seguir clasificando mientras "
                f"corre, y cancelarlo desde el menú del bin.",
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        self._generacion_de_proxies += 1
        self._generando_proxies = {
            "bin": nombre_de_bin,
            "generacion": self._generacion_de_proxies,
            "total": len(pendientes),
            "hechos": 0,
            "fallidos": [],
            "cancelado": False,
            "carpeta": carpeta,
        }
        self._pintar_avance_de_proxies()
        estado = self._generando_proxies
        for i in pendientes:
            self._generacion_pool.start(_GeneracionDeProxyJob(
                estado["generacion"], i, self.clips[i].ruta, carpeta,
                # se lee al empezar ESE clip, no al encolarlo
                lambda e=estado: e["cancelado"],
                self._señales_de_trabajos,
            ))

    def _descartar_generacion_de_proxies(self) -> None:
        """Tira la tanda que corre, sin avisos ni resúmenes.

        Es distinto de cancelar: cancelar es una decisión de Bruno sobre un
        bin que sigue existiendo. Esto es para cuando el bin —o el proyecto
        entero— dejó de ser lo que era, y lo que llegue de esa tanda ya no
        describe a nadie.

        **Por qué hace falta:** `_on_proxy_generado` engancha el proxy con
        `self.clips[index]`, y al quitar un bin los índices se corren. Sin
        esto, un proxy recién generado se enganchaba al clip EQUIVOCADO — y
        entre dos tomas de la misma cámara la validación cuadro a cuadro
        calza, así que pasaba en silencio. Es el mismo modo de fallo que ya
        está documentado para `_proxy_generacion_de`.
        """
        estado = self._generando_proxies
        if estado is None:
            return
        # la bandera corta lo que sigue encolado; la generacion nueva hace
        # que lo que ya venia en camino se ignore al llegar
        estado["cancelado"] = True
        self._generacion_de_proxies += 1
        self._generando_proxies = None
        self.clip_sheet.set_bin_generando(estado["bin"], None)

    def cancelar_generacion_de_proxies(self, nombre_de_bin: str = "") -> None:
        """Lo que ya se generó se queda enganchado; lo que faltaba, no se
        hace. El que esté a medias termina —cortar ffmpeg a la mitad deja un
        archivo truncado— pero es uno solo, no los veintitrés."""
        if self._generando_proxies is None:
            return
        self._generando_proxies["cancelado"] = True

    def _segundos_estimados(self, indices: list[int]) -> float:
        """~10 s de proceso por cada 6 s de video, medido con el material
        real. De los clips sin duracion conocida se supone medio minuto:
        equivocarse por unos segundos en un aviso no le cuesta nada a nadie.
        """
        total = sum(self._clip_durations.get(i, 30.0) for i in indices)
        return total * (10.0 / 6.0)

    def _pintar_avance_de_proxies(self) -> None:
        estado = self._generando_proxies
        if estado is None:
            return
        self.clip_sheet.set_bin_generando(
            estado["bin"], estado["hechos"], estado["total"]
        )

    def _on_proxy_generado(self, generacion: int, index: int,
                           destino, motivo: str) -> None:
        estado = self._generando_proxies
        if estado is None or generacion != estado["generacion"]:
            return  # tanda ya descartada: quitaron el bin, o abriste otro proyecto
        estado["hechos"] += 1
        if motivo:
            estado["fallidos"].append((index, motivo))
        elif destino is not None and index < len(self.clips):
            # engancharlo AHORA, no al final. Pasa por la validacion de
            # siempre: si no calza cuadro a cuadro no se engancha, aunque lo
            # hayamos generado nosotros -- la regla existe para que el in/out
            # no caiga en el cuadro equivocado, y de quien vino el archivo no
            # la cambia.
            self._sondear_proxies({self.clips[index].ruta: Path(destino)},
                                  indices=[index])
        if estado["hechos"] < estado["total"] and not estado["cancelado"]:
            self._pintar_avance_de_proxies()
            return
        if estado["cancelado"] and estado["hechos"] < estado["total"]:
            # los cancelados siguen llegando (cada trabajo avisa con las
            # manos vacias), asi que solo se cierra cuando llegaron todos
            self._pintar_avance_de_proxies()
            return
        self._terminar_generacion_de_proxies()

    def _terminar_generacion_de_proxies(self) -> None:
        estado = self._generando_proxies
        if estado is None:
            return
        self._generando_proxies = None
        # apagar el aviso: la insignia vuelve sola al conteo real
        self.clip_sheet.set_bin_generando(estado["bin"], None)
        # Las portadas que quedaron esperando se piden ahora, salga como
        # salga la generación: al cancelar a la mitad, o si algún proxy
        # falló, esos clips se quedarían en gris para siempre esperando algo
        # que ya no va a llegar.
        self._schedule_thumbnails(self.bins.clips_de(estado["bin"]))
        if estado["cancelado"]:
            return  # cancelar fue decision suya: no hace falta un cartel
        if estado["fallidos"]:
            cuantos = len(estado["fallidos"])
            primero = estado["fallidos"][0][1]
            QMessageBox.warning(
                self, "Algunos no se pudieron crear",
                f"{cuantos} de {estado['total']} fallaron.\n\n{primero}",
            )

    def quitar_proxies_de_bin(self, nombre_de_bin: str) -> None:
        """Desengancha los de ESE bin. Las portadas se vuelven a pedir del
        original, que es lo que hace `_sondear_proxies` al final."""
        self._sondear_proxies({}, indices=self.bins.clips_de(nombre_de_bin))

    # --- el menu del bin -------------------------------------------------

    def _conectar_bin(self, cabecera) -> None:
        """La hoja crea un encabezado por bin; aqui se le enchufa la ventana.

        Se llama cada vez que nace un encabezado, no una sola vez al
        arrancar: los bins aparecen y desaparecen con las importaciones.
        """
        cabecera.rename_requested.connect(self._on_bin_renombrado)
        cabecera.proxies_requested.connect(self.adjuntar_proxies_de_bin)
        cabecera.proxies_cleared.connect(self.quitar_proxies_de_bin)
        cabecera.proxies_generate_requested.connect(self.generar_proxies_de_bin)
        cabecera.proxies_generate_cancelled.connect(self.cancelar_generacion_de_proxies)
        cabecera.select_all_requested.connect(self._on_bin_seleccionado)
        cabecera.remove_requested.connect(self._on_bin_quitado)

    def _on_bin_renombrado(self, viejo: str, nuevo: str) -> None:
        self.bins.renombrar(viejo, nuevo)
        # la hoja guarda por NOMBRE dos cosas suyas que el dato no conoce:
        # si el bin esta colapsado y su carpeta de origen. Se le avisa antes
        # de refrescar, porque el refresco ya trae el nombre nuevo.
        if nuevo in self.bins.nombres():
            self.clip_sheet.renombrar_bin(viejo, nuevo)
            # el aviso de media faltante tambien va por nombre: sin mover la
            # llave, el renglon seguiria hablando de un bin que ya no existe
            if viejo in self._ultimo_reencuentro:
                self._ultimo_reencuentro[nuevo] = self._ultimo_reencuentro.pop(viejo)
            self._refrescar_aviso()
        # `force_rebuild` no: reconstruir la hoja tiraria las portadas ya
        # cargadas, y aqui no cambio ni un clip -- solo como se llama su bin.
        self._refresh_sheet()
        self._autosave()

    def _on_bin_nuevo_pedido(self) -> None:
        """Un bin vacio, listo para que le arrastres clips.

        Nace con un nombre generico y el encabezado entra en modo edicion en
        el acto: ponerle nombre es parte de crearlo, no un segundo paso que
        haya que recordar.

        `_refresh_sheet` sin `force_rebuild`: aqui no cambio ni un clip -- solo
        hay un bin mas-- y reconstruir tiraria las portadas ya cargadas.
        """
        nombre = self.bins.crear_vacio("Bin")
        self._refresh_sheet()
        cabecera = self.clip_sheet.bin_header_widget(nombre)
        if cabecera is not None:
            cabecera.empezar_a_renombrar()
        self._autosave()

    def _on_clips_movidos(self, indices: list[int], destino: str | None) -> None:
        """Soltaste clips en otro bin.

        Es la operacion mas barata de la app y conviene que siga siendolo:
        `mover` no toca el indice de ningun clip, asi que no hay que correr
        `_proxy_sizes`, `_clip_durations` ni el historial -- solo cambia de
        lista quien esta en cual. El proxy viaja con el clip porque es del
        clip, no del bin, y el cuarto ni se mira: arrastrar acomoda por
        camara y nada mas.

        `force_rebuild` no: aqui no cambio ni un clip -- solo en que seccion
        se dibuja-- y reconstruir tiraria las portadas ya cargadas.
        """
        if not indices:
            return
        self.bins.mover(indices, destino)
        self._refresh_sheet()
        self._autosave()

    def _on_bin_seleccionado(self, nombre: str) -> None:
        """«Seleccionar los N clips» del menu del encabezado.

        «Sin bin» no esta en `BinTree` --un clip suelto se representa por
        AUSENCIA de bin-- asi que preguntarle por ese nombre devolvia una
        lista vacia y el renglon terminaba DESELECCIONANDO todo lo que
        tuvieras marcado: prometia N y hacia lo contrario.
        """
        indices = (self._clips_sueltos() if nombre == SIN_BIN
                   else set(self.bins.clips_de(nombre)))
        self.clip_sheet.set_selected(indices)

    def _on_bin_quitado(self, nombre: str) -> None:
        """Saca los clips del proyecto. NO borra nada del disco.

        Todo lo que va indexado por clip tiene que correrse junto, o queda
        describiendo al clip equivocado.
        """
        cuantos = len(self.bins.clips_de(nombre))
        if not cuantos:
            return
        # La UNICA accion destructiva del programa, y en el menu esta pegada
        # a «Colapsar». Se lleva los clips con toda su clasificacion Y el
        # historial --o sea que `⌘Z` tampoco la deshace-- y ademas se
        # guarda. Un clic y no hay vuelta atras: por eso pregunta.
        respuesta = QMessageBox.question(
            self, "Quitar del proyecto",
            f"¿Quitar «{nombre}» del proyecto?\n\n"
            + ("Se va su clip con su clasificación y sus marcas, "
               if cuantos == 1
               else f"Se van sus {cuantos} clips con su clasificación y sus marcas, ")
            + "y esto no se puede deshacer con ⌘Z.\n\n"
            "No se borra nada del disco.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        quitados = self.bins.quitar(nombre)
        if not quitados:
            return
        fuera = set(quitados)
        self.clips = [c for i, c in enumerate(self.clips) if i not in fuera]
        for orden, clip in enumerate(self.clips, start=1):
            clip.orden = orden
        self._clip_durations = _corrido(self._clip_durations, fuera)
        self._clip_sizes = _corrido(self._clip_sizes, fuera)
        self._clip_rotations = _corrido(self._clip_rotations, fuera)
        self._proxy_sizes = _corrido(self._proxy_sizes, fuera)
        self._proxy_candidatos = _corrido(self._proxy_candidatos, fuera)
        self._relativas = _corrido(self._relativas, fuera)
        self._bytes_guardados = _corrido(self._bytes_guardados, fuera)
        # Las portadas en vuelo tambien van por indice. Sin correrlas, un
        # clip que hereda un indice «ocupado» se salta su extraccion porque
        # la app cree que ya se le esta sacando.
        self._miniaturas_en_vuelo = _corrido(self._miniaturas_en_vuelo, fuera)
        self._miniaturas_a_rehacer = _corrido_set(self._miniaturas_a_rehacer, fuera)
        # y el conjunto de «este clip no tiene donde buscarse», que arrastra
        # indices de una revision a la siguiente
        self._sin_donde_buscar = _corrido_set(self._sin_donde_buscar, fuera)
        # Lo que dijo la ULTIMA revision, que tambien va por indice. Se corre
        # aqui aunque mas abajo se pida una revision nueva: esa corre en otro
        # hilo y tarda, y mientras tanto `_schedule_thumbnails` --que se llama
        # unas lineas mas abajo, en el acto-- lee `_faltantes` para saltarse
        # los clips cuyo archivo no esta. Sin correrlo, un clip que hereda un
        # indice «faltante» se queda sin portada y nadie se la vuelve a pedir:
        # la revision nueva llega despues y no pide portadas. Gris hasta
        # cerrar y reabrir el proyecto.
        self._faltantes = _corrido_set(self._faltantes, fuera)
        self._proxies_perdidos = _corrido(self._proxies_perdidos, fuera)
        # La tanda de proxies que estuviera corriendo se tira entera: engancha
        # con `self.clips[index]` y esos indices acaban de correrse.
        self._descartar_generacion_de_proxies()
        # el reencuentro guarda INDICES de clip, y correrlos aqui no alcanza:
        # tambien habla de un bin que acaba de dejar de existir. Se tira
        # entero y la revision se rehace sobre lo que quedo.
        self._ultimo_reencuentro = {}
        self._exitos = {}
        # (`_faltantes` y `_proxies_perdidos` ya se corrieron arriba: la
        # revisión que se pide al final llega tarde para quien los lee ya.)
        self._indices_generation += 1
        # Los sondeos en vuelo NO se corren: se tiran enteros.
        #
        # Correr `_proxy_generacion_de` conserva el VALOR, y todos los clips
        # de una tanda comparten generacion -- asi que un resultado que
        # venia para el indice viejo cae sobre un indice nuevo que tiene esa
        # MISMA generacion y pasa la guarda de `_on_proxy_sondeado`. De ahi
        # en adelante `_el_proxy_calza` compara el candidato de un clip
        # contra la info del archivo de otro, y entre dos tomas de la misma
        # camara y duracion eso calza: se engancha un proxy ajeno y
        # `_proxy_sizes` guarda las medidas del archivo equivocado. La
        # validacion cuadro a cuadro, que es la razon de ser del sondeo, se
        # salta entera.
        self._proxy_generation += 1
        self._proxy_generacion_de = {}
        self.bins.reindexar_tras_quitar(quitados)
        # el historial guarda INDICES de clip: despues de correrlos ya no
        # apunta a lo mismo, y deshacer moveria el clip equivocado.
        self.history.clear()
        self._refresh_history()
        # el clip actual se CORRE, no se recorta: si lo que se fue estaba
        # antes que el, su indice baja tantos lugares como quitados haya por
        # debajo. Con un `min` te quedabas mirando otro clip sin aviso.
        self.current_index = min(
            self.current_index - sum(1 for q in fuera if q < self.current_index),
            max(0, len(self.clips) - 1),
        )
        # `force_rebuild` SI: hay menos tarjetas que antes, y `update_clips`
        # solo sabe actualizar en el lugar cuando el largo no cambio.
        self._refresh_sheet(force_rebuild=True)
        # y las portadas: los trabajos lanzados antes de quitar entregan con
        # su indice VIEJO sobre `item_widgets[index]`, que ahora es otro clip
        # -- exactamente el fallo que la Regla 1 de `ClipSheet` existe para
        # evitar. Esta llamada sube `_thumb_generation`, con lo que esas
        # señales quedan invalidadas, y vuelve a pedir lo que falte con los
        # indices nuevos. Va DESPUES del refresco: los aciertos de cache se
        # entregan en el acto y necesitan la hoja ya reconstruida.
        self._schedule_thumbnails()
        self.revisar_media()
        self._abrir_clip_actual()
        self._autosave()

    def _sondear_proxies(self, emparejados: dict[Path, Path | None],
                         indices: list[int] | None = None) -> None:
        """Manda a comprobar cada proxy en segundo plano.

        Emparejar es barato (mirar nombres); validar cuesta un `ffprobe`
        por archivo --26.7 ms, o sea 3.4 s en 128 clips-- y eso no puede
        bloquear la ventana.

        `indices` acota a los clips de UN bin. Y acotar significa acotar
        tambien lo que se limpia: esta funcion arrancaba con
        `self._proxy_sizes = {}` y reconstruia `_proxy_candidatos` entero,
        y dejarlo asi haria que enganchar los proxies del dron borrara los
        de la Sony.
        """
        crudo = range(len(self.clips)) if indices is None else indices
        # se recortan contra los clips que de verdad hay: `app.py` restaura
        # los bins del JSON sin compararlos con lo que se cargo, asi que una
        # sesion desincronizada traeria indices que ya no existen.
        alcance = [i for i in crudo if 0 <= i < len(self.clips)]
        se_limpio_algo = False
        for i in alcance:
            self._proxy_sizes.pop(i, None)
            self._proxy_candidatos.pop(i, None)
            self._proxy_generacion_de.pop(i, None)
            se_limpio_algo = se_limpio_algo or self.clips[i].ruta_proxy is not None
            self.clips[i].ruta_proxy = None
            # apagar la marca «PROXY» de esa tarjeta. Va aqui, en el bucle
            # que limpia, y no en `_refrescar_indicadores_de_proxy` --que
            # corre por clip cuando un sondeo SALE BIEN--: quitar los proxies
            # no lanza ningun sondeo, asi que por ese camino no llega nada y
            # la tarjeta se quedaba diciendo PROXY sobre un clip que ya no lo
            # tiene. Peor que no decir nada.
            self.clip_sheet.set_proxy_de_clip(i, False)
        if se_limpio_algo:
            # `ruta_proxy` viaja en `Clip.to_dict()`, o sea que se persiste:
            # sin guardar aqui, los proxies que quitaste vuelven al reabrir
            # la app. Y sin refrescar, la barra sigue contando unos que ya
            # no estan. Hasta ahora las dos cosas solo pasaban dentro de
            # `_on_proxy_sondeado`, o sea solo si algun proxy validaba --y
            # quitarlos no lanza ningun sondeo.
            self._refrescar_indicadores_de_proxy(self.current_index)
            self._autosave()
        self._proxy_generation += 1
        generation = self._proxy_generation
        nuevos = {
            i: emparejados[self.clips[i].ruta]
            for i in alcance
            if emparejados.get(self.clips[i].ruta) is not None
        }
        self._proxy_candidatos.update(nuevos)
        for index, proxy in nuevos.items():
            # la generacion se anota POR CLIP: el contador global sube en
            # cada tanda, y compararlo contra el a secas tiraba los
            # resultados en vuelo del OTRO bin, que nadie invalido.
            self._proxy_generacion_de[index] = generation
            self._thread_pool.start(
                _ProxyProbeJob(generation, index, proxy, self._probe_clip,
                               self._señales_de_trabajos)
            )
        # y las miniaturas que falten se vuelven a pedir, ahora desde el
        # proxy: es 5.6 veces mas barato (medido con el material real, 5.90 s
        # contra 1.06 s por clip) y es justo lo que hacia trabajar a los
        # ventiladores con 109 clips. Las que ya estan en cache no se rehacen.
        #
        # CON EL ALCANCE, no sin el: sin indices esta llamada sube la
        # generacion y recorre todos los clips, asi que enganchar los
        # proxies del dron le tiraba a la Sony las señales de las portadas
        # en vuelo y le encolaba un segundo trabajo por clip --misma carpeta
        # de salida, mismo socket IPC, uno borrandole el socket al otro--
        # ademas de reiniciarle la barra de progreso.
        self._schedule_thumbnails(alcance)

    def _on_proxy_sondeado(self, generation: int, index: int, info: dict | None) -> None:
        # contra la generacion de ESTE clip, no contra el contador global:
        # el global sube en cada tanda y con bins las tandas son por bin,
        # asi que enganchar el dron descartaba los resultados de la Sony
        # que seguian en vuelo -- y esos ya no vuelven a pedirse.
        if generation != self._proxy_generacion_de.get(index):
            return  # resultado de una tanda ya descartada para este clip
        if not info or index >= len(self.clips):
            return
        proxy = self._proxy_candidatos.get(index)
        if proxy is None or not self._el_proxy_calza(index, info):
            return
        self.clips[index].ruta_proxy = proxy
        ancho, alto = int(info.get("width") or 0), int(info.get("height") or 0)
        if ancho and alto:
            self._proxy_sizes[index] = (ancho, alto)
        self._refrescar_indicadores_de_proxy(index)
        self._autosave()

    def _el_proxy_calza(self, index: int, info: dict) -> bool:
        """Un proxy que no calza cuadro a cuadro NO es un proxy.

        Si tiene otro fps u otra cantidad de cuadros, el in/out que marques
        cae corrido -- y el plugin lo engancharia igual, sin avisar. Por eso
        el que no valida se descarta en los tres lados: no se reproduce, no
        entra al manifest y no cuenta en el contador.
        """
        clip = self.clips[index]
        if abs(float(info.get("fps") or 0) - clip.fps) >= 0.01:
            return False
        if index not in self._clip_durations or index not in self._clip_sizes:
            return False  # sin original con que comparar, no se valida nada
        cuadros_original = round(self._clip_durations[index] * clip.fps)
        if abs(int(info.get("duration_frames") or 0) - cuadros_original) > 1:
            return False
        ancho, alto = int(info.get("width") or 0), int(info.get("height") or 0)
        if not (ancho and alto):
            return False
        # un proxy sin su matriz de rotacion se veria acostado
        return orientacion_de(ancho, alto) == orientacion_de(*self._clip_sizes[index])

    def _refrescar_indicadores_de_proxy(self, index: int) -> None:
        """Los resultados llegan de a uno, cada uno en su momento: solo se
        repinta lo que ese resultado puede haber cambiado."""
        if index == self.current_index:
            self._refresh_overlays()
        # la marca «PROXY» de la tarjeta, que responde «¿cuales faltaron?» --
        # la insignia del bin solo dice cuantos
        if 0 <= index < len(self.clips):
            self.clip_sheet.set_proxy_de_clip(
                index, self.clips[index].ruta_proxy is not None
            )
        self.status_bar.set_proxies(*self._resumen_de_proxies())
        # y la insignia del encabezado del bin, que dice lo MISMO que la
        # barra de abajo. Se rehacía solo al reconstruir la hoja, y los
        # resultados del sondeo llegan de a uno bastante después: el
        # encabezado se quedaba diciendo «sin proxies» con proxies ya
        # validados. Es barato -- recorre bins en memoria, no toca disco.
        self._refrescar_meta_de_bins()

    def _resumen_de_proxies(self) -> tuple[int, int, str]:
        """Lo que dice el contador: cuantos, de cuantos, y de que tamaño.

        Cuenta los clips que TIENEN proxy emparejado, sin ir al disco a
        confirmar que cada archivo sigue ahi: es un inventario del
        material, no un reporte de lo que se esta reproduciendo ahora
        --eso lo dice el badge-- y hacer 128 consultas al disco en cada
        refresco de la barra seria caro para responder otra pregunta.
        """
        con_proxy = [i for i, c in enumerate(self.clips) if c.ruta_proxy is not None]
        etiquetas = {
            etiqueta_de_resolucion(*self._proxy_sizes[i])
            for i in con_proxy
            if i in self._proxy_sizes
        }
        etiquetas.discard("")
        resolucion = etiquetas.pop() if len(etiquetas) == 1 else ""
        return len(con_proxy), len(self.clips), resolucion

    def _refrescar_progreso(self) -> None:
        self.status_bar.set_progreso_de_miniaturas(
            self._miniaturas_totales - self._miniaturas_pendientes,
            self._miniaturas_totales,
        )

    def _schedule_thumbnails(self, indices: list[int] | None = None) -> None:
        """Pide las portadas que falten.

        `indices` acota a los clips nuevos, que es lo que hace agregar
        material. Y acotar significa tambien NO subir la generacion: subirla
        descarta las señales de los trabajos del lote anterior que siguen en
        vuelo, y ademas los vuelve a encolar -- dos trabajos para el mismo
        clip, compartiendo carpeta de salida y socket IPC, uno borrandole el
        socket al otro. Con los 109 clips de Bruno eso son 109 extracciones
        de mas por cada carpeta que agrega.
        """
        if not self.clips:
            return
        if indices is None:
            # material nuevo: invalida las señales stale de la tanda anterior
            self._thumb_generation += 1
            self._miniaturas_pendientes = 0
            # Lo que sigue corriendo NO se olvida: su resultado se va a
            # descartar por generacion, asi que hay que rehacerlo -- pero
            # DESPUES, cuando su mpv termine. Vaciar el registro aqui era
            # decir «no hay nada corriendo» con tres extracciones vivas, y
            # el barrido de abajo les encolaba un segundo mpv encima.
            self._miniaturas_a_rehacer |= set(self._miniaturas_en_vuelo)
            self._miniaturas_totales = len(self.clips)
            alcance = list(range(len(self.clips)))
        else:
            alcance = [i for i in indices if 0 <= i < len(self.clips)]
            # el total es cuantas portadas tiene el PROYECTO, no cuantas se
            # pidieron. Sumandole el alcance daba lo mismo mientras el unico
            # que acotaba era agregar material --los clips nuevos ya estan
            # en `self.clips`--, pero re-enlazar los proxies de un bin pide
            # otra vez clips que ya estaban contados: «113 de 115» con 109.
            self._miniaturas_totales = len(self.clips)
        generation = self._thumb_generation
        cache_root = self._thumbnail_cache_root
        for index in alcance:
            if index in self._faltantes:
                # el archivo no está: extraerle una portada es lanzar mpv
                # contra la nada. Al abrir en otra computadora no está
                # NINGUNO, así que eran 132 trabajos inútiles ocupando los
                # tres hilos con los ventiladores girando -- la queja que
                # originó todo el trabajo de proxies.
                #
                # Se mira `_faltantes` --lo que dijo la última revisión-- y
                # no el disco: preguntarle aquí serían 132 `stat` en serie
                # en el hilo de la interfaz, que es justo el bug que la
                # revisión fuera de hilo vino a arreglar.
                #
                # Cuando se reconecten se piden con el alcance acotado, que
                # eso ya funciona (ver `reconectar_bin`).
                continue
            clip = self.clips[index]
            cache_dir = cache_dir_for(clip.ruta, cache_root)
            cached_frames = sorted(cache_dir.glob("strip_*.jpg")) if cache_dir.exists() else []
            # Cache hit solo si la extraccion TERMINO. Contar fotos no
            # alcanza: no distingue una tira corta de una tira CORTADA, y con
            # 2 de 12 el escrubeo tiene dos posiciones y se siente roto.
            # Quedan asi los clips que estaban corriendo cuando se cerro la
            # app --medido en el cache de Bruno: 6 de 133, cortados de tres
            # en tres, que es cuantos se extraen a la vez--. Sin esto se
            # quedaban a medias para siempre.
            #
            # `>= CUADROS_DE_LA_TIRA` es por los caches de antes de que la
            # marca existiera: una tira de 12 ya estaba completa y no hay por
            # que rehacerla.
            completa = (cache_dir / MARCA_DE_COMPLETA).exists() if cache_dir.exists() else False
            if cached_frames and (completa or len(cached_frames) >= _ThumbnailJob.STRIP_COUNT):
                # cache hit: mismo clip ya procesado en una sesion anterior.
                self._on_thumbnail_ready(generation, index, cached_frames)
                continue
            # Lo que haya se PINTA igual --mejor una foto que una tarjeta
            # gris mientras se rehace-- pero no cancela la extraccion.
            #
            # Pintar directo y NO por `_on_thumbnail_ready`: ese ademas lleva
            # la contabilidad, y una de las cosas que hace es sacar al clip
            # de «en vuelo». Como las fotos a medias que se ven aqui son
            # justo las que esta escribiendo su propia extraccion mientras
            # corre, pasar por ahi la daba por terminada, la guarda de dos
            # renglones mas abajo no la veia, y se encolaba un segundo mpv
            # sobre el mismo socket. Es exactamente el bug que dejaba las
            # tiras cortadas.
            if cached_frames:
                self._pintar_miniatura(index, cached_frames)
            duration_seconds = self._clip_durations.get(index)
            # La portada suelta de las versiones viejas --`00000001.jpg`, de
            # cuando no existia la tira-- se PINTA pero no cuenta como cache
            # hit. Tratarla como hit dejaba esos clips sin escrubeo PARA
            # SIEMPRE: la unica forma de recuperarlos era borrar el cache a
            # mano, y nadie sabia que hubiera que hacerlo. Bruno lo reporto
            # asi: «¿por que no puedo escrubear en los de la FX30 pero si en
            # los del dron?» -- los del dron se importaron despues, con la
            # tira ya existiendo.
            #
            # Se pinta igual para que la tarjeta no quede gris mientras se
            # extrae la tira, que es justo lo que esa portada ya servia.
            suelta = cache_dir / "00000001.jpg"
            if suelta.exists():
                self._on_thumbnail_ready(generation, index, [suelta])
                if not duration_seconds:
                    # sin duracion no hay tira posible, y volver a pedirla
                    # cada sesion seria extraer de nuevo la misma portada
                    continue
            # del PROXY si lo hay: sacar 12 cuadros de HEVC 10-bit a 268 Mbps
            # es lo que ponia los ventiladores a trabajar con 109 clips. El
            # proxy da la misma imagen ~20 veces mas barato.
            #
            # Se usa el candidato aunque todavia no haya validado: para una
            # miniatura alcanza, y esperar a la validacion --3.4 s de ffprobe
            # en 128 clips-- retrasaria justo lo que se quiere acelerar.
            fuente = self._proxy_candidatos.get(index, clip.ruta)
            corriendo = self._miniaturas_en_vuelo.get(index)
            if corriendo is not None:
                # Ya se le esta sacando la tira a este clip. Encolar otro
                # trabajo no lo acelera: los dos comparten carpeta de salida
                # y socket IPC, y el que arranca segundo le BORRA el socket
                # al primero --`extract_thumbnail_strip` lo hace a
                # proposito, para no heredar uno viejo--. El primer mpv
                # muere a media tira, el trabajo revienta con «el socket se
                # cerro antes de responder», y esa tarjeta se queda con un
                # solo cuadro: sin escrubeo. Bruno lo vio como «sigue sin
                # funcionar el scrubbing en los videos de Sony».
                #
                # Pasa porque `_schedule_thumbnails` se llama varias veces
                # por sesion --al cargar, al terminar la revision de media,
                # al enganchar proxies-- y hasta ahora los clips ya
                # cacheados salian antes por el `continue` del cache hit.
                if corriendo != fuente:
                    # ...pero si la FUENTE cambio --acaban de engancharse los
                    # proxies-- hay que rehacerla: del proxy cuesta 5 veces
                    # menos y es el camino que se quiere. Se anota y se
                    # vuelve a pedir cuando el trabajo de ahora termine, que
                    # es lo unico que evita los dos mpv a la vez.
                    self._miniaturas_a_rehacer.add(index)
                continue
            self._miniaturas_en_vuelo[index] = fuente
            self._miniaturas_pendientes += 1
            self._thread_pool.start(
                _ThumbnailJob(generation, index, fuente, cache_dir, duration_seconds,
                              self._señales_de_trabajos)
            )
        self._refrescar_progreso()

    def _on_thumbnail_ready(self, generation: int, index: int, frames: list[Path] | None) -> None:
        # El registro de «en vuelo» se limpia ANTES de mirar la generacion, y
        # no despues: una señal vencida tambien significa que ese mpv
        # termino. Saliendo antes, el clip se quedaba marcado como corriendo
        # para siempre y no se le volvia a pedir la tira nunca.
        vencida = generation != self._thumb_generation
        self._miniaturas_en_vuelo.pop(index, None)
        if index in self._miniaturas_a_rehacer:
            self._miniaturas_a_rehacer.discard(index)
            # ahora si: con la fuente nueva, o con la tanda nueva, y sin
            # nadie mas usando ese socket
            self._schedule_thumbnails([index])
        if vencida:
            return  # senal de una importacion ya descartada
        self._miniaturas_pendientes = max(0, self._miniaturas_pendientes - 1)
        self._refrescar_progreso()
        self._pintar_miniatura(index, frames)

    def _pintar_miniatura(self, index: int, frames: list[Path] | None) -> None:
        """Solo pinta. Sin contabilidad: hay un camino --las fotos a medias
        que se encuentran en el cache-- que necesita mostrar algo sin decir
        que la extraccion termino."""
        if not frames or index >= self.clip_sheet.count():
            return
        pixmaps = [QPixmap(str(f)) for f in frames]
        # `item_widgets` va por INDICE DE CLIP, no por posicion visual: los
        # clips se ven agrupados por cuarto, pero esta lista conserva el
        # orden de `self.clips`. Reordenarla haria que las miniaturas
        # aterricen en la tarjeta equivocada.
        if len(pixmaps) > 1:
            self.clip_sheet.item_widgets[index].set_frames(pixmaps)
        else:
            self.clip_sheet.item_widgets[index].set_pixmap(pixmaps[0])

    # ------------------------------------------------------------------
    # acciones
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # velocidad: `J K L`, la convencion de Premiere
    # ------------------------------------------------------------------

    def _acelerar(self) -> None:
        """`L`: cicla 1× → 2× → 4× → 1× y arranca si estaba pausado.

        Arrancar es parte de lo que hace `L` en Premiere, Avid y Resolve: si
        solo cambiara el numero, apretarla sobre un video pausado no haria
        nada visible.
        """
        actual = self.video_widget.player.speed
        perfiles = SPEED_PROFILES
        siguiente = perfiles[(perfiles.index(actual) + 1) % len(perfiles)] \
            if actual in perfiles else perfiles[0]
        self._aplicar_velocidad(siguiente)
        self.video_widget.player.play()

    def _frenar(self) -> None:
        """`K`: vuelve a 1× y pausa de un golpe, sin importar donde estabas.

        No es un interruptor: sobre un video ya pausado lo deja pausado.
        """
        self._aplicar_velocidad(SPEED_PROFILES[0])
        self.video_widget.player.pause()

    def alternar_solo_video(self) -> None:
        """`F`: esconde todo menos el video, y lo vuelve a traer.

        No es un modo aparte: las teclas siguen funcionando, asi que se puede
        seguir clasificando sin la hoja a la vista. Y se recalcula el ancho,
        porque esconder los paneles sin recalcular dejaria el mismo video con
        franjas negras al costado -- justo lo que este rediseño evita.
        """
        # Los dos modos que esconden paneles son EXCLUYENTES. La hoja
        # esconde el video y solo video esconde la hoja: combinados no
        # queda un solo panel visible, y las dos teclas estan anunciadas,
        # asi que `⇥` + `F` dejaba la ventana en negro.
        if not self._solo_video and self._modo_hoja:
            self.alternar_modo_hoja()   # sin video no hay nada que dejar solo
        self._solo_video = not self._solo_video
        if self._solo_video:
            self.transicion.cancelar()  # una tarjeta volando sobre nada
        for panel in (self.title_bar, self.room_rail, self.tool_column,
                      self.clip_sheet, self.status_bar):
            panel.setVisible(not self._solo_video)
        # el aviso va aparte, por la MISMA regla que usa `_refrescar_aviso`:
        # una barra vacía no puede reaparecer con su relleno y su borde, y
        # una llena no puede reaparecer encima del video a pantalla completa.
        self._mostrar_aviso_si_toca()

    def _on_clip_activado(self, indice: int) -> None:
        """Doble click en una tarjeta: abre ESE clip en modo clip."""
        self.select_clip(indice)
        if self._modo_hoja:
            self.alternar_modo_hoja()

    # ------------------------------------------------------------------
    # el pincel de cuarto: manten `1`-`9` y arrastra
    # ------------------------------------------------------------------

    def _mostrar_carga_del_pincel(self) -> None:
        """El chip que sigue al cursor: nunca pintas sin saber que pintas.

        Un widget y no un cursor con pixmap: admite el color del cuarto y su
        nombre, y no depende de como el sistema dibuje cursores.
        """
        tecla, cuarto = self._pincel
        self._chip_pincel.setText(f"{tecla}   {cuarto}")
        self._chip_pincel.setStyleSheet(
            f"background-color: {theme.con_alfa_qss(theme.BG_APP, 230)};"
            f"border: 1px solid {self._color_de_cuarto(cuarto)};"
            f"border-radius: {theme.RADIUS_SM}px; padding: 4px 8px;"
            f"color: {theme.TEXT}; font-size: {theme.FONT_SMALL}px;"
        )
        self._chip_pincel.adjustSize()
        self._chip_pincel.show()
        self._chip_pincel.raise_()

    def pincel_cargado(self) -> tuple[str, str] | None:
        """`(tecla, cuarto)` mientras pintas, o None. El cursor lo muestra:
        nunca pintas sin saber que estas pintando."""
        return self._pincel

    def empezar_pincelada(self, tecla: str) -> None:
        """Se mantuvo apretada una tecla de cuarto.

        El pincel solo existe mientras la tecla esta abajo, asi que no se
        puede disparar por accidente. **Sin tecla, arrastrar hoy no hace
        nada**: la marquesina de seleccion todavia no esta construida (ver el
        punto de control post-F8). Cuando exista, este es el lugar que decide
        cual de los dos gestos corre.
        """
        cuarto = self._router.resolve_room_key(tecla)
        if cuarto is None:
            return          # una tecla sin cuarto no carga nada
        self._pincel = (tecla, cuarto[0])
        self._antes_de_pintar = {}
        self.clip_sheet.set_pincel_activo(True)
        self._mostrar_carga_del_pincel()
        # mientras dure la pincelada la hoja NO se reagrupa: si los clips
        # saltaran de grupo, la grilla se reacomodaria bajo el cursor y
        # seguirias pintando sobre otra cosa (medido en el spike de la Task 14)
        self.clip_sheet.congelar_acomodo(True)

    def pintar(self, indice: int) -> None:
        """Pasar por encima de una tarjeta con el pincel cargado."""
        if self._pincel is None or not (0 <= indice < len(self.clips)):
            return
        if indice in self._antes_de_pintar:
            return          # arrastrando se pasa varias veces por la misma
        self._antes_de_pintar[indice] = list(self.clips[indice].categoria_path)
        self.clips[indice].categoria_path = [self._pincel[1]]
        # solo esta tarjeta se repinta: tocar la hoja entera aqui es lo que
        # reacomodaria la grilla bajo el cursor
        self.clip_sheet.repintar_uno(
            indice, self._pincel[1], self.room_selection.active_rooms()
        )

    def terminar_pincelada(self) -> None:
        """Se solto la tecla: entra UNA entrada al historial y recien ahora se
        reagrupa.

        Una sola entrada porque si `⌘Z` deshiciera clip por clip, el pincel
        seria una trampa: un gesto de un segundo que cuesta seis acciones
        revertir.
        """
        if self._pincel is None:
            return
        _, cuarto = self._pincel
        antes = self._antes_de_pintar
        self._pincel, self._antes_de_pintar = None, {}
        pintados = list(antes)
        self.clip_sheet.congelar_acomodo(False)
        self.clip_sheet.set_pincel_activo(False)
        self.clip_sheet.limpiar_tinte()
        self._chip_pincel.hide()
        if not pintados:
            # apretar y soltar sin tocar nada no hizo nada: una fila de
            # historial que no cambio nada es basura que estorba
            self._refresh_sheet()
            return
        # el "antes" se reconstruye del estado que se guardo al empezar
        self.history.push(HistoryEntry(
            cuarto, self._detalle(pintados), self._color_de_cuarto(cuarto),
            {i: {"categoria_path": valor} for i, valor in antes.items()},
        ))
        self._refresh_history()
        self._refresh_sheet()
        self._autosave()

    def alternar_modo_hoja(self) -> None:
        """`⇥`: la hoja a pantalla completa, y de vuelta.

        Los dos modos comparten TODO el estado --el clip actual, la seleccion
        y el scroll-- porque la division es de atencion, no de computo: nada
        se pierde al cruzar (DECISIONES.md). Por eso aqui solo se esconden
        widgets; no hay un segundo "cual es el actual" que pueda desincronizarse.

        La columna de herramientas se va con el video: es el estado del clip
        que estas viendo, y sin visor no tiene de que ser el estado.
        """
        # La tarjeta del clip actual, ANTES de que la hoja cambie de modo:
        # despues del cruce las tarjetas ya se re-acomodaron y su posicion
        # de origen se perdio.
        # ver la nota de `alternar_solo_video`: son excluyentes
        if not self._modo_hoja and self._solo_video:
            self.alternar_solo_video()  # entrar a la hoja devuelve los paneles

        tarjeta = self._tarjeta_actual() if self._modo_hoja else None

        self._modo_hoja = not self._modo_hoja
        for panel in (self.video_stage, self.tool_column):
            panel.setVisible(not self._modo_hoja)
        self.clip_sheet.set_modo_hoja(self._modo_hoja)
        # El sonido sigue a la imagen. Entrar a la hoja calla lo que estaba
        # corriendo solo --si no, el audio se queda sonando sobre una hoja
        # sin visor-- y salir lo reanuda. Lo que pausaste TU no se reanuda:
        # `_auto_pendiente` solo se prende cuando el clip arranco solo.
        if self._modo_hoja and self._auto_reproduciendo:
            self.video_widget.player.pause()
            self._auto_pendiente = True
            self._auto_reproduciendo = False
            self.video_stage.badges.set_auto(False)
        elif not self._modo_hoja and self._auto_pendiente:
            self.video_widget.player.play()
            self._auto_pendiente = False
            self._auto_reproduciendo = True
            self.video_stage.badges.set_auto(True)
        if self._modo_hoja:
            # entrar a la hoja lleva SIEMPRE al clip actual (DECISIONES.md):
            # los dos modos comparten el clip, asi que abrir la hoja mirando
            # otra parte del shooting es perder el hilo. Y de paso es lo que
            # hace posible la transicion de vuelta: una tarjeta fuera de la
            # vista no se puede animar.
            self.clip_sheet.centrar_en(self.current_index)
        # el switch de la barra de titulo es una VISTA de `_modo_hoja`, no
        # una segunda copia: se le avisa desde aca, que es el unico lugar
        # donde el modo cambia.
        self.title_bar.set_modo_hoja(self._modo_hoja)
        self._refresh_overlays()   # la barra de estado cambia de contenido
        self._resize_video_stage()
        if tarjeta is not None:
            # solo de la hoja AL visor: en el otro sentido no hay tarjeta de
            # donde salir, y DECISIONES.md no pide la vuelta.
            self.transicion.lanzar(tarjeta, self.video_stage.geometry())

    def _tarjeta_actual(self):
        widgets = self.clip_sheet.item_widgets
        if 0 <= self.current_index < len(widgets):
            return widgets[self.current_index]
        return None

    def _pasar_cuadro(self, delta: int) -> None:
        """`.` adelante, `,` atras. La convencion de Premiere, y la unica
        forma de marcar in/out en el cuadro exacto.

        Refresca el pie a mano en vez de esperar al tick del playhead: el
        tick corre cada 100 ms y el cuadro a cuadro se usa apretando la tecla
        varias veces seguidas -- con el retardo, el numero va siempre un
        cuadro atras de lo que ves.
        """
        if self.current_clip is None:
            return
        self.video_widget.player.step_frame(delta, self.current_clip.fps)
        self._tick_playhead()

    def _aplicar_velocidad(self, velocidad: float) -> None:
        """Un solo lugar mueve las DOS vistas del mismo dato -- el
        reproductor y el control segmentado. Que se contradigan es un bug que
        este proyecto ya tuvo dos veces (la tarjeta y la barra de rango)."""
        self.video_widget.player.set_speed(velocidad)
        self.video_stage.speed.set_current(etiqueta_de_velocidad(velocidad))

    def _on_speed_changed(self, etiqueta: str) -> None:
        """Del control segmentado al reproductor. La etiqueta se traduce
        buscando en los perfiles, no parseando el texto.

        Pasa por `_aplicar_velocidad` --que tambien sincroniza el control--
        aunque venga del control mismo: al hacer click Qt ya lo dejo marcado
        y volver a marcarlo no cuesta nada, pero asi las dos vistas convergen
        venga el cambio de donde venga.
        """
        for velocidad in SPEED_PROFILES:
            if etiqueta_de_velocidad(velocidad) == etiqueta:
                self._aplicar_velocidad(velocidad)
                return

    def handle_key_press(self, key: str) -> None:
        # `L` y `K` van ANTES del corte por clip nulo: la app abre sin
        # material y apretarlas no puede depender de que ya hayas importado.
        if key == "l":
            self._acelerar()
            return
        if key == "k":
            self._frenar()
            return
        if key == "j":
            # reservada para reproducir hacia atras. No se construye --en
            # recorridos de inmuebles no aporta-- pero tampoco se le da otro
            # significado, o el dia que sirva ya estaria ocupada.
            return
        if key in (",", "."):
            self._pasar_cuadro(1 if key == "." else -1)
            return
        if key == "f":
            self.alternar_solo_video()
            return
        if key == "escape":
            # `esc` es la salida universal, y deshace UNA capa por vez: si se
            # saltara una, saldrias de solo video y de la vista de clip con la
            # misma tecla sin haber visto el paso intermedio.
            if self._solo_video:
                self.alternar_solo_video()
            elif not self._modo_hoja:
                self.alternar_modo_hoja()
            return
        if key == "tab":
            self.alternar_modo_hoja()
            return
        if key in ("+", "-"):
            (self.clip_sheet.agrandar if key == "+" else self.clip_sheet.achicar)()
            return
        if self.current_clip is None:
            return
        if key in ("i", "o", "u"):
            campos = {"i": ("in_frame",), "o": ("out_frame",)}.get(
                key, ("in_frame", "out_frame")
            )
            self._registrar(
                etiqueta="IN/OUT",
                detalle=self._detalle([self.current_index]),
                color=theme.TRIM_COLOR,
                clips=[self.current_index],
                campos=campos,
            )
            if key == "i":
                self.current_clip.in_frame = self.video_widget.player.mark_in(
                    self.current_clip.fps
                )
            elif key == "o":
                self.current_clip.out_frame = self.video_widget.player.mark_out(
                    self.current_clip.fps
                )
            else:
                self.current_clip.in_frame = None
                self.current_clip.out_frame = None
            self._refresh_sheet()
            self._autosave()
            return
        if key in ("arriba", "abajo"):
            self._mover_en_la_escalera(1 if key == "arriba" else -1)
            return
        if key == "r":
            # al principio DEL CLIP, no al 25 % donde arranca solo: lo que se
            # quiere revisar volviendo es la entrada de la toma.
            self.video_widget.player.seek(0.0)
            self._refresh_overlays()
            self._update_scrub_bar()
            return
        if key == "s":
            cuarto = self._cuarto_del_clip_anterior()
            if cuarto is not None:
                self._asignar_cuarto([cuarto])
            return
        room_path = self._router.resolve_room_key(key)
        if room_path is not None:
            self._asignar_cuarto(room_path)
            return
        action = self._router.resolve_action_key(key)
        if action is not None:
            # repetir la tecla sobre el estado que ya tiene lo apaga: sin esto
            # no habria forma de volver a neutral con el teclado. `⇧P` sobre un
            # destacado tambien apaga; `P` sobre un destacado lo BAJA a pick,
            # que es el escalon de abajo de la misma escalera.
            # A TODA la seleccion, igual que los cuartos. Antes solo tocaba
            # el clip actual: seleccionabas seis con la marquesina, apretabas
            # `P`, y se marcaba uno.
            indices = self._bulk_target_indices()
            if not indices:
                return
            estados = [self.clips[i].flag for i in indices]
            # repetir la tecla apaga SOLO si todos lo tienen ya: con la
            # seleccion mezclada, empareja hacia arriba, que es lo que uno
            # espera al pintar un lote. Sin esto no habria forma de volver a
            # neutral con el teclado.
            if all(e == action for e in estados):
                nuevo = "none"
            elif action == "pick" and all(e == "destacado" for e in estados):
                # `P` sobre un destacado lo BAJA a pick, el escalon de abajo
                # de la misma escalera
                nuevo = "pick"
            else:
                nuevo = action
            self._registrar(
                etiqueta=ETIQUETAS_DE_ESTADO.get(nuevo, nuevo.title()),
                detalle=self._detalle(indices),
                color=COLORES_DE_ESTADO.get(nuevo, theme.TEXT_3),
                clips=indices,
                campos=("flag",),
            )
            for i in indices:
                self.clips[i].flag = nuevo
            self._refresh_sheet()
            self._refresh_rail()
            self._refresh_overlays()
            self._autosave()

    def _mover_en_la_escalera(self, paso: int) -> None:
        """`↑` sube un escalon y `↓` baja uno, sobre toda la seleccion.

        Con la seleccion mezclada se empareja: se toma el escalon mas bajo
        (subiendo) o el mas alto (bajando) y se mueve UNO desde ahi. Si cada
        clip subiera el suyo, el lote quedaria igual de disparejo que antes
        -- y lo que uno quiere al pintar un lote es dejarlos iguales.
        """
        indices = self._bulk_target_indices()
        if not indices:
            return
        alturas = [ESCALERA_DE_ESTADO.index(self.clips[i].flag) for i in indices]
        desde = min(alturas) if paso > 0 else max(alturas)
        destino = max(0, min(len(ESCALERA_DE_ESTADO) - 1, desde + paso))
        nuevo = ESCALERA_DE_ESTADO[destino]
        if all(self.clips[i].flag == nuevo for i in indices):
            return  # ya estaban todos ahi: ni historial ni repintado
        self._registrar(
            etiqueta=ETIQUETAS_DE_ESTADO.get(nuevo, nuevo.title()),
            detalle=self._detalle(indices),
            color=COLORES_DE_ESTADO.get(nuevo, theme.TEXT_3),
            clips=indices,
            campos=("flag",),
        )
        for i in indices:
            self.clips[i].flag = nuevo
        self._refresh_sheet()
        self._refresh_rail()
        self._refresh_overlays()
        self._autosave()

    def handle_arrow(self, direction: str) -> None:
        """Se mueve DENTRO de la cola filtrada, no sobre los 128.

        El clip actual puede no estar en la cola --pasa cada vez que resuelves
        uno y sale de ella--, asi que no alcanza con buscar su posicion: se
        busca el siguiente (o el anterior) que si este.
        """
        if not self.clips:
            return
        indices = self.queue()
        if not indices:
            return
        if direction == "next":
            siguientes = [i for i in indices if i > self.current_index]
            self.current_index = siguientes[0] if siguientes else indices[-1]
        else:
            anteriores = [i for i in indices if i < self.current_index]
            self.current_index = anteriores[-1] if anteriores else indices[0]
        self._abrir_clip_actual()
        self._refresh_sheet()
        # y la hoja SIGUE al clip actual. El borde ambar ya se pintaba, pero
        # con 128 clips la tarjeta quedaba fuera de la parte visible: mirabas
        # una hoja donde nada estaba marcado.
        self.clip_sheet.centrar_en(self.current_index)
        self._resize_video_stage()
        self._autosave()

    def _abrir_clip_actual(self) -> None:
        """El unico camino por el que se abre un clip.

        Los tres lugares que abren clip --`load_clips`, `select_clip` y
        `handle_arrow`-- pasan por aqui a proposito: si el autoplay se
        agregara en dos de los tres, el tercero quedaria mudo sin dar ningun
        sintoma visible. Hay un test que lo vigila.

        El arranque al 25% se pide ANTES de abrir: `start` la resuelve mpv al
        cargar el archivo. Un seek despues llegaria antes de que mpv reporte
        la duracion, que es asincrona.
        """
        clip = self.current_clip
        if clip is None:
            # el proyecto se quedo sin clips. Salir de aqui sin mas dejaba
            # al visor reproduciendo el ultimo que hubo, que ya no esta en
            # el proyecto: el video seguia sonando con la hoja vacia.
            self.video_widget.cerrar_clip()
            self._auto_reproduciendo = False
            self.video_stage.badges.set_auto(False)
            return
        player = self.video_widget.player
        player.set_start_percent(START_PERCENT)
        self.video_widget.open_clip(self.ruta_de_reproduccion(self.current_index))
        if self._modo_hoja:
            # En la hoja el visor esta escondido: reproducir seria audio sin
            # imagen, y sin visor a la vista no hay de donde deducir que esta
            # sonando. El clip SI se abre --por eso el cruce al visor es
            # instantaneo-- pero pausado, y el autoplay queda aplazado, no
            # perdido: `alternar_modo_hoja` lo reanuda al cruzar.
            player.pause()
            self._auto_pendiente = True
            self._auto_reproduciendo = False
            self.video_stage.badges.set_auto(False)
            return
        player.play()
        self._auto_pendiente = False
        self._auto_reproduciendo = True
        self.video_stage.badges.set_auto(True)

    def select_clip(self, index: int) -> None:
        if not (0 <= index < len(self.clips)):
            return
        self.current_index = index
        self._abrir_clip_actual()
        # No reconstruir la hoja aqui: la seleccion solo cambia el clip
        # actual (borde), no los datos de ningun clip. Reconstruir destruye
        # y reemplaza los widgets --incluyendo el que esta dentro de su
        # propio mousePressEvent-- y en el run loop nativo de cocoa eso
        # termina en SIGSEGV. Ademas borraria los pixmaps ya cargados.
        self.clip_sheet.set_current(self.current_index)
        self.clip_sheet.centrar_en(self.current_index)
        self._refresh_rail()
        self._refresh_overlays()
        self._update_scrub_bar()
        self._resize_video_stage()
        self._autosave()

    def _on_export_manifest(self) -> None:
        unclassified = [c for c in self.clips if not c.categoria_path]
        if unclassified:
            QMessageBox.warning(
                self, "Clips sin clasificar",
                f"{len(unclassified)} clip(s) no tienen cuarto y entrarán en 'Sin clasificar'. "
                "Puedes seguir y corregir después.",
            )
        path, _ = QFileDialog.getSaveFileName(self, "Guardar manifest", "manifest.json", "JSON (*.json)")
        if not path:
            return
        manifest = Manifest(
            proyecto=self.project_name,
            orientacion=self.orientacion_del_proyecto(),
            clips=[_con_el_rango_en_orden(c) for c in self.clips],
        )
        manifest.write_json(Path(path))

    def _on_import_folders(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta de material")
        if not folder:
            return
        carpeta = Path(folder)
        self.status_bar.set_volume(folder, _gigas_del_volumen(carpeta))
        # AGREGA, no reinicia: hasta la F2 esto reconstruia la lista entera
        # con `load_clips`, que limpia historial y proxies y recrea todas las
        # tarjetas. Por eso a Bruno se le caian las portadas al importar una
        # segunda carpeta.
        self.importar_rutas([carpeta])

    def _refresh_sheet(self, force_rebuild: bool = False) -> None:
        # NO REENTRA. La hoja avisa de un filtro nuevo desde adentro de
        # `set_bin_order` --cuando el bin que estabas filtrando desaparece--
        # y ese aviso vuelve por `set_filters` hasta aqui, antes de que el
        # refresco de afuera haya tocado las tarjetas. Sin esta guarda,
        # quitar un bin hacia DOS `set_clips` seguidos: destruir y recrear
        # las 132 tarjetas dos veces, en la unica operacion destructiva de la
        # app y en el terreno donde ya hubo tres segfaults.
        #
        # Saltarse el de adentro no pierde nada: `self.filters` ya quedo
        # actualizado antes de la llamada, y el de afuera lo lee mas abajo.
        if self._refrescando_hoja:
            return
        self._refrescando_hoja = True
        try:
            self._refrescar_hoja_de_verdad(force_rebuild)
        finally:
            self._refrescando_hoja = False

    def _refrescar_hoja_de_verdad(self, force_rebuild: bool) -> None:
        active_rooms = self.room_selection.active_rooms()
        # el bin de cada clip, de una sola pasada: `bins.bin_de` recorre
        # todos los bins, y llamarlo por clip seria recorrerlos 151 veces
        # en cada refresco -- y esto se refresca en cada tecla.
        bin_de: dict[int, str] = {}
        for nombre in self.bins.nombres():
            for indice in self.bins.clips_de(nombre):
                bin_de[indice] = nombre
        thumbs = [
            ClipThumbnail(
                path=clip.ruta,
                room_label=clip.categoria_path[-1] if clip.categoria_path else "Sin clasificar",
                flag=clip.flag,
                room_color=(
                    theme.room_color(active_rooms.index(clip.categoria_path[0]))
                    if clip.categoria_path and clip.categoria_path[0] in active_rooms
                    else None
                ),
                numero=clip.orden,
                in_frame=clip.in_frame,
                out_frame=clip.out_frame,
                fps=clip.fps,
                duration_frames=(
                    round(self._clip_durations[index] * clip.fps)
                    if index in self._clip_durations
                    else None
                ),
                aspect_ratio=self.aspect_ratio_for(index),
                bin_nombre=bin_de.get(index, ""),
                tiene_proxy=clip.ruta_proxy is not None,
            )
            for index, clip in enumerate(self.clips)
        ]
        # el orden va ANTES de las tarjetas: si llegara despues, la primera
        # agrupada saldria con los bins en el orden equivocado y se veria
        # saltar.
        self.clip_sheet.set_bin_order(self.bins.nombres())
        if force_rebuild:
            self.clip_sheet.set_clips(thumbs)
        elif len(thumbs) > self.clip_sheet.count():
            # crecio: agregar sin destruir las tarjetas que ya tienen portada
            self.clip_sheet.append_clips(thumbs)
        else:
            # actualiza en el lugar: eso es lo que preserva las miniaturas ya
            # cargadas por los _ThumbnailJob al navegar o clasificar.
            self.clip_sheet.update_clips(thumbs)
        self._refrescar_meta_de_bins()
        # la MISMA lista que recorren las flechas: si se calcularan por
        # separado, la hoja y la navegacion se desincronizan
        indices = self.queue()
        filtrando = self.filters.esta_filtrando()
        self.clip_sheet.set_visible_indices(indices if filtrando else None)
        self.clip_sheet.set_counts(contar(self.clips))
        self.clip_sheet.set_queue_size(len(indices), filtrando)
        self.clip_sheet.set_current(self.current_index)
        self.clip_sheet.centrar_en(self.current_index)
        self._refresh_rail()
        self._refresh_overlays()
        self._update_scrub_bar()

    def _refrescar_meta_de_bins(self) -> None:
        """La carpeta de origen y cuantos proxies engancharon, por bin.

        Los proxies se cuentan de `ruta_proxy`, que es el que YA valido
        cuadro a cuadro. Contar los candidatos daria un «23/23» optimista
        justo cuando dos no calzaron -- y ese «21/23» es el dato que la
        insignia existe para mostrar.
        """
        for nombre in self.bins.nombres():
            origen = self.bins.origen_de(nombre)
            self._aplicar_meta_de(
                nombre, self.bins.clips_de(nombre),
                origen.name if origen is not None else "",
            )
        # y la seccion de sueltos. El proxy es del CLIP y no del bin
        # (spec §6.b), asi que un clip sin bin puede tenerlo enganchado --
        # recorriendo solo `bins.nombres()`, «Sin bin» decia siempre «sin
        # proxies» aunque los tuviera. Sin carpeta de origen: no salio de
        # ninguna, son los clips que no pertenecen a nadie.
        sueltos = self._clips_sueltos()
        if sueltos:
            self._aplicar_meta_de(SIN_BIN, sorted(sueltos), "")

    def _clips_sueltos(self) -> set[int]:
        """Los clips que no estan en ningun bin.

        Por `mapa_por_clip` y no preguntando `bin_de` clip por clip: eso
        recorreria todos los bins una vez por clip, y esto corre en cada
        refresco de la hoja, o sea en cada tecla.
        """
        con_bin = self.bins.mapa_por_clip()
        return {i for i in range(len(self.clips)) if i not in con_bin}

    def _aplicar_meta_de(self, nombre: str, indices: list[int],
                         origen: str) -> None:
        """Lo que el encabezado escribe debajo del nombre: de donde salio el
        material y cuantos proxies engancharon.

        Los proxies se cuentan de `ruta_proxy`, que es el que YA valido
        cuadro a cuadro. Contar los candidatos daria un «23/23» optimista
        justo cuando dos no calzaron -- y ese «21/23» es el dato que la
        insignia existe para mostrar.
        """
        con_proxy = [
            i for i in indices
            if i < len(self.clips) and self.clips[i].ruta_proxy is not None
        ]
        # una sola resolucion o ninguna, el mismo criterio que
        # `_resumen_de_proxies`: con dos mezcladas en el mismo bin,
        # escribir una seria mentir sobre la otra mitad.
        etiquetas = {
            etiqueta_de_resolucion(*self._proxy_sizes[i])
            for i in con_proxy if i in self._proxy_sizes
        }
        etiquetas.discard("")
        self.clip_sheet.set_bin_meta(
            nombre,
            origen=origen,
            proxies=(len(con_proxy), len(indices)),
            resolucion=etiquetas.pop() if len(etiquetas) == 1 else "",
        )
