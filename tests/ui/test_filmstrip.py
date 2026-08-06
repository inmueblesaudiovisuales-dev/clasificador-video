# tests/ui/test_filmstrip.py
from pathlib import Path

from clasificador_video.ui.filmstrip import ClipThumbnail, Filmstrip


def test_filmstrip_agrega_un_thumbnail_por_clip(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="Sin clasificar", flag="none"),
        ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="pick"),
    ])
    assert strip.count() == 2


def test_estilo_de_pick_aplica_borde_verde(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="pick")])
    item = strip.item_widgets[0]
    assert "border-color: #3bb273" in item.styleSheet()


def test_estilo_de_reject_aplica_borde_rosa(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="reject")])
    item = strip.item_widgets[0]
    assert "border-color: #e0556f" in item.styleSheet()


def test_sin_flag_no_aplica_borde_de_color(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Sin clasificar", flag="none")])
    item = strip.item_widgets[0]
    assert "#3bb273" not in item.styleSheet()
    assert "#e0556f" not in item.styleSheet()


def test_item_puede_recibir_un_pixmap(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    from PySide6.QtGui import QPixmap
    pm = QPixmap(10, 10)
    pm.fill()
    strip.item_widgets[0].set_pixmap(pm)
    assert strip.item_widgets[0].has_pixmap()
