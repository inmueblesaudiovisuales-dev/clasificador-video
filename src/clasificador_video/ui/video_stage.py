# src/clasificador_video/ui/video_stage.py
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from clasificador_video.ui import theme
from clasificador_video.ui.segmented import SegmentedControl
from clasificador_video.ui.video_widget import ScrubBar, VideoWidget

M = theme.OVERLAY_MARGIN
SCRIM_HEIGHT = 150


class VideoStage(QWidget):
    """El video y sus controles flotando encima.

    Ningun control vive en una banda: en un 9:16 cada 16 px de banda
    cuestan 9 px de ancho de video, y ese es el problema que este rediseño
    existe para resolver.

    Que Qt componga widgets normales sobre el contenido de OpenGL de mpv se
    valido en la F0 (ver el plan maestro): el alfa se mezcla contra los
    pixeles del video, no contra negro.
    """

    def __init__(self, mpv_factory=None, parent=None):
        super().__init__(parent)
        self.setObjectName("videoStage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.video = VideoWidget(mpv_factory=mpv_factory) if mpv_factory else VideoWidget()
        layout.addWidget(self.video)

        # --- overlays: hijos del VideoWidget, no hermanos ---
        self.scrim = QLabel("", self.video)
        self.scrim.setObjectName("overlayScrim")
        self.file_label = QLabel("", self.video)
        self.file_label.setObjectName("overlayFile")
        self.badges = QLabel("", self.video)
        self.badges.setObjectName("overlayBadges")
        self.timecode_label = QLabel("", self.video)
        self.timecode_label.setObjectName("overlayTimecode")
        self.quality = SegmentedControl(["Full", "1/2", "1/4", "1/8"], self.video)
        self.scrub_bar = ScrubBar(self.video)
        self.scrub_bar.set_over_video(True)

        for pasivo in (self.file_label, self.badges, self.scrim, self.timecode_label):
            # el click y el arrastre tienen que llegar a la scrub bar y al
            # video, no quedarse en una etiqueta decorativa
            pasivo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # sin esta bandera la barra pinta fondo opaco donde no dibuja y se
        # come una franja del video (hallazgo de la F0)
        self.scrub_bar.setAttribute(Qt.WA_TranslucentBackground, True)

        # El padre recibe resizeEvent ANTES de que el hijo cambie de tamaño:
        # posicionar ahi deja los overlays corridos un cuadro.
        self.video.installEventFilter(self)

    @staticmethod
    def width_for(height: int, aspect_ratio: float) -> int:
        """Ancho que le corresponde al video para no dejar franjas negras."""
        return max(1, round(height * aspect_ratio))

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 -- override de Qt
        if obj is self.video and event.type() == QEvent.Resize:
            self._place_overlays()
        return super().eventFilter(obj, event)

    def _place_overlays(self) -> None:
        ancho, alto = self.video.width(), self.video.height()

        self.scrim.setGeometry(0, alto - SCRIM_HEIGHT, ancho, SCRIM_HEIGHT)

        self.file_label.adjustSize()
        self.file_label.move(M, M)

        self.badges.adjustSize()
        self.badges.move(M, M + self.file_label.height() + 8)

        self.quality.adjustSize()
        self.quality.move(ancho - self.quality.width() - M, M)

        self.scrub_bar.setGeometry(
            M, alto - M - theme.SCRUB_HEIGHT, ancho - 2 * M, theme.SCRUB_HEIGHT
        )

        self.timecode_label.adjustSize()
        self.timecode_label.move(
            M, self.scrub_bar.y() - 8 - self.timecode_label.height()
        )

        self.scrim.lower()
        for encima in (self.file_label, self.badges, self.quality,
                       self.timecode_label, self.scrub_bar):
            encima.raise_()
