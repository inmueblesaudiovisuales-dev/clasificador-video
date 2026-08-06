# src/clasificador_video/ui/video_widget.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QWidget

from clasificador_video.player import MpvPlayer


def _default_mpv_factory(**kwargs) -> object:
    import mpv

    return mpv.MPV(**kwargs)


class VideoWidget(QWidget):
    """Widget que embebe libmpv via `wid` (validado en vivo el 2026-08-06
    en macOS: mpv dibuja dentro del NSView del widget). El player se crea
    con el wid del widget ya mostrado -- winId() no es valido antes.
    """

    def __init__(self, mpv_factory: Callable[..., object] = _default_mpv_factory, parent=None):
        super().__init__(parent)
        self._mpv_factory = mpv_factory
        self._player: MpvPlayer | None = None

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._player is None:
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
