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
from PySide6.QtGui import QLinearGradient, QPainter, QPixmap

from clasificador_video.category_path import CategoryTree
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
        if indice % 3 == 0:
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
        seleccion.toggle(cuarto)

    ventana = MainWindow(
        project_name="Casa Lomas de Chapultepec",
        room_selection=seleccion,
        category_tree=CategoryTree(),
        video_factory=_MpvFalso,
        # nunca tocar el cache real de ~/.cache/clasificador_video
        thumbnail_cache_root=Path(tempfile.mkdtemp()),
    )

    clips, tamanos, duraciones = _clips()
    ventana._clip_durations = duraciones
    # `_clip_sizes` lo introduce la Task 1 de la F2; hasta entonces esto no
    # existe y no pasa nada, el arnés no lo necesita para renderizar.
    if hasattr(ventana, "_clip_sizes"):
        ventana._clip_sizes = tamanos
    ventana.load_clips(clips)
    ventana.current_index = CLIP_ACTUAL
    ventana.select_clip(CLIP_ACTUAL)

    # miniaturas sintéticas, sin lanzar mpv
    for indice, clip in enumerate(clips):
        if indice >= ventana.clip_sheet.count():
            break
        cuarto = clip.categoria_path[0] if clip.categoria_path else None
        color = theme.room_color(CUARTOS.index(cuarto)) if cuarto else theme.TEXT_3
        vertical = tamanos[indice] == VERTICAL
        ventana.clip_sheet.item_widgets[indice].set_pixmap(_miniatura(color, vertical))
    return ventana
