"""Sesión de ejemplo para el arnés de comparación con el mockup.

Reproduce los MISMOS datos que muestra
docs/superpowers/mockups/rediseno-2026-08-08/mockup.html -- mismos cuartos,
mismos conteos, mismo clip actual. Si los datos no coinciden, la comparación
lado a lado no dice nada.

No es parte de la app: solo lo usa scripts/comparar_con_mockup.py.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QLabel

from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui import theme
from clasificador_video.ui.main_window import MainWindow

# Los nueve cuartos del mockup, en su orden (la tecla 1-9 sale de la posicion).
CUARTOS = [
    "Cocina", "Sala", "Recámara 1", "Recámara 2", "Baño 1",
    "Baño 2", "Comedor", "Terraza", "Fachada",
    # decimo cuarto: en el mockup aparece SIN tecla, porque los atajos
    # numericos solo llegan hasta el noveno. Ejercita ese caso.
    "Estudio",
]
# Conteo por cuarto tal como aparece en el rail del mockup. Suman 116,
# los clasificados; los 12 restantes de los 128 quedan sin cuarto.
CONTEOS = [24, 16, 14, 11, 9, 8, 14, 9, 6, 5]
TOTAL = 128
SIN_CLASIFICAR = 12
PICKS = 41
REJECTS = 9
CLIP_ACTUAL = 86  # el mockup muestra el clip 087, que es el indice 86

VERTICAL = (2160, 3840)
HORIZONTAL = (3840, 2160)
VOLUMEN = "/Volumes/FX30/CasaLomas"  # la misma ruta que muestra el mockup


class _MpvFalso:
    """Doble de mpv: el arnés no reproduce nada, solo necesita una ventana
    que se pueda dibujar. Sin esto habría que abrir VideoToolbox de verdad."""

    def __init__(self, **kwargs):
        self.pause = True
        self.time_pos = 9.77
        self.duration = 18.37
        self.vid_scale = 1.0

    def play(self, path):
        self.loaded = path

    def command(self, *args):
        pass


def _miniatura(color_hex: str, vertical: bool) -> QPixmap:
    """Miniatura sintética con un degradado del color del cuarto -- el
    mismo truco que usa el mockup.

    Extraer miniaturas reales necesita archivos de video y tarda; sin
    ellas las tarjetas salen vacías y la mitad derecha de la comparación
    no dice nada.
    """
    ancho, alto = (90, 160) if vertical else (160, 90)
    pixmap = QPixmap(ancho, alto)
    gradiente = QLinearGradient(QPointF(0, 0), QPointF(ancho, alto))
    gradiente.setColorAt(0.0, Qt.GlobalColor.white)
    gradiente.setColorAt(0.45, color_hex)
    gradiente.setColorAt(1.0, Qt.GlobalColor.black)
    pintor = QPainter(pixmap)
    pintor.fillRect(pixmap.rect(), gradiente)
    pintor.end()
    return pixmap


def pintar_frame_de_ejemplo(ventana: MainWindow) -> None:
    """Pone una imagen sintética detrás del video.

    El doble de mpv no dibuja nada, así que el área del video salía negra y
    la comparación no permitía juzgar el contraste de los overlays contra
    una imagen real —que es justo lo que la F0 validó y lo que más riesgo
    tiene de verse mal en uso—.

    Se llama DESPUÉS de `show()` y del resize: `VideoStage._place_overlays`
    corre en cada resize del video y baja el scrim al fondo, así que un
    frame agregado antes quedaría por encima de él.
    """
    video = ventana.video_stage.video
    lienzo = QLabel("", video)
    lienzo.setGeometry(0, 0, video.width(), video.height())
    pixmap = QPixmap(video.width(), video.height())
    gradiente = QLinearGradient(QPointF(0, 0), QPointF(0, video.height()))
    # una habitación de día: claro arriba, sombra abajo. Lo que importa no es
    # que sea bonito, es que tenga zonas claras Y oscuras bajo los overlays.
    gradiente.setColorAt(0.0, QColor("#d9d2c4"))
    gradiente.setColorAt(0.55, QColor("#8d8578"))
    gradiente.setColorAt(1.0, QColor("#2b2823"))
    pintor = QPainter(pixmap)
    pintor.fillRect(pixmap.rect(), gradiente)
    pintor.end()
    lienzo.setPixmap(pixmap)
    lienzo.show()
    lienzo.lower()  # debajo del scrim y de todos los controles flotantes


def _historial_de_ejemplo(ventana: MainWindow) -> None:
    """Las mismas filas que el rail del mockup, salvo la de «Destacado», que
    es un estado que no existe hasta la F7.

    Se empujan a mano en vez de simular las acciones: `load_clips` limpia el
    historial, así que cualquier cosa hecha antes se perdería.
    """
    from clasificador_video.history import HistoryEntry

    for etiqueta, detalle, color in (
        ("IN/OUT", "→ clip 085", theme.TRIM_COLOR),
        ("Reject", "→ clip 084", theme.REJECT_COLOR),
        ("Comedor", "→ 4 clips", theme.room_color(CUARTOS.index("Comedor"))),
        ("Recámara 1", "→ 5 clips", theme.room_color(CUARTOS.index("Recámara 1"))),
    ):
        ventana.history.push(HistoryEntry(etiqueta, detalle, color, antes={}))
    ventana._refresh_history()


def _clips() -> tuple[list[Clip], dict[int, tuple[int, int]], dict[int, float]]:
    clips: list[Clip] = []
    tamanos: dict[int, tuple[int, int]] = {}
    duraciones: dict[int, float] = {}

    # Los clasificados se reparten por cuarto respetando los conteos del
    # mockup; los ultimos SIN_CLASIFICAR quedan sin cuarto.
    asignaciones: list[str | None] = []
    for cuarto, cuantos in zip(CUARTOS, CONTEOS):
        asignaciones.extend([cuarto] * cuantos)
    asignaciones = asignaciones[: TOTAL - SIN_CLASIFICAR]
    asignaciones.extend([None] * (TOTAL - len(asignaciones)))

    for indice, cuarto in enumerate(asignaciones):
        clip = Clip(
            orden=indice + 1,
            ruta=Path(f"/Volumes/FX30/CasaLomas/C{indice + 1:04d}.MP4"),
            categoria_path=[cuarto] if cuarto else [],
            fps=29.97,
        )
        if indice < PICKS:
            clip.flag = "pick"
        elif indice < PICKS + REJECTS:
            clip.flag = "reject"
        # 132 y 344 a 29.97 fps son IN 00:00:04:12 y OUT 00:00:11:16, los dos
        # timecodes que muestra el mockup. El clip ACTUAL tiene que ser uno de
        # los que lo llevan, o el arnes compara un pie con rango marcado
        # (izquierda) contra uno sin nada (derecha) -- y la zona de rango, las
        # manijas y la pastilla quedan sin comparar.
        if indice % 3 == 0 or indice == CLIP_ACTUAL:
            clip.in_frame, clip.out_frame = 132, 344
        clips.append(clip)
        # mayoria verticales, como el material real de la FX30, e
        # intercalando horizontales para ver los dos casos conviviendo.
        # El clip actual TIENE que ser vertical: es el caso que el
        # rediseño existe para resolver y el que muestra el mockup.
        tamanos[indice] = HORIZONTAL if indice % 5 == 4 else VERTICAL
        duraciones[indice] = 18.37
    return clips, tamanos, duraciones


def construir_ventana_de_ejemplo() -> MainWindow:
    seleccion = RoomSelection()
    for cuarto in CUARTOS:
        seleccion.add(cuarto)

    ventana = MainWindow(
        project_name="Casa Lomas de Chapultepec",
        room_selection=seleccion,
        video_factory=_MpvFalso,
        # nunca tocar el cache real de ~/.cache/clasificador_video
        thumbnail_cache_root=Path(tempfile.mkdtemp()),
    )

    clips, tamanos, duraciones = _clips()
    ventana._clip_durations = duraciones
    ventana._clip_sizes = tamanos
    ventana.load_clips(clips)
    ventana.current_index = CLIP_ACTUAL
    ventana.select_clip(CLIP_ACTUAL)
    # sin importación real la barra de estado sale sin ruta y no se puede
    # comparar contra el mockup, que sí muestra una
    ventana.status_bar.set_volume(VOLUMEN)
    _historial_de_ejemplo(ventana)

    # miniaturas sintéticas, sin lanzar mpv
    for indice, clip in enumerate(clips):
        if indice >= ventana.clip_sheet.count():
            break
        cuarto = clip.categoria_path[0] if clip.categoria_path else None
        color = theme.room_color(CUARTOS.index(cuarto)) if cuarto else theme.TEXT_3
        vertical = tamanos[indice] == VERTICAL
        ventana.clip_sheet.item_widgets[indice].set_pixmap(_miniatura(color, vertical))
    return ventana
