# src/clasificador_video/ui/video_widget.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from clasificador_video.player import MpvPlayer


def _default_mpv_factory(**kwargs) -> object:
    import mpv

    return mpv.MPV(**kwargs)


class VideoWidget(QWidget):
    """Widget que embebe libmpv via `wid` (validado en vivo el 2026-08-06
    en macOS: mpv dibuja dentro del NSView del widget). El player se crea
    una vez que el widget tiene un id de ventana nativa valido.
    """

    def __init__(self, mpv_factory: Callable[..., object] = _default_mpv_factory, parent=None):
        super().__init__(parent)
        self.setObjectName("videoWidget")
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(True)
        self._mpv_factory = mpv_factory
        self._player: MpvPlayer | None = None

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._player is None:
            self.winId()
            self._player = MpvPlayer(mpv_factory=self._mpv_factory, wid=int(self.winId()))

    @property
    def player(self) -> MpvPlayer:
        if self._player is None:
            raise RuntimeError("el VideoWidget debe mostrarse antes de usar su player")
        return self._player

    def open_clip(self, path: Path) -> None:
        self.player.open(path)

    def toggle_play(self) -> None:
        self.player.toggle()
