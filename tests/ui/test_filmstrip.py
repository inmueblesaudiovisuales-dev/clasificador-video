# tests/ui/test_filmstrip.py
from pathlib import Path

from PySide6.QtGui import QPixmap

from clasificador_video.ui.filmstrip import ClipThumbnail, Filmstrip


def test_item_del_filmstrip_pinta_su_propio_fondo_y_borde(qtbot):
    """Bug real de v1 (visto en capturas): un QWidget plano sin
    WA_StyledBackground no pinta su propio borde por QSS -- la propiedad
    se hereda a los QLabel hijos, que la pintan cada uno por separado,
    dando dos cajas en vez de una sola envolviendo miniatura + nombre.
    """
    from PySide6.QtCore import Qt

    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    item = strip.item_widgets[0]
    assert item.testAttribute(Qt.WA_StyledBackground)
    assert item.objectName() == "clipItem"


def test_borde_de_pick_no_se_hereda_a_los_labels_hijos(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="pick")])
    item = strip.item_widgets[0]
    assert "border: none" in item.styleSheet()


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
    assert "border: 2px solid #3bb273" in item.styleSheet()


def test_estilo_de_reject_aplica_borde_rosa(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="reject")])
    item = strip.item_widgets[0]
    assert "border: 2px solid #e0556f" in item.styleSheet()


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
    pm = QPixmap(10, 10)
    pm.fill()
    strip.item_widgets[0].set_pixmap(pm)
    assert strip.item_widgets[0].has_pixmap()


def test_clip_actual_tiene_borde_azul(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    strip.set_current(0)
    assert "border: 2px solid #2b7fff" in strip.item_widgets[0].styleSheet()


def test_pick_sobre_borde_azul_mantiene_ambos_colores(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="pick")])
    strip.set_current(0)
    assert "border: 2px solid #3bb273" in strip.item_widgets[0].styleSheet()
    assert "outline: 2px solid #2b7fff" in strip.item_widgets[0].styleSheet()


def test_miniatura_grande_se_escala_a_altura_fija(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])

    pixmap_vertical_4k = QPixmap(2160, 3840)
    strip.item_widgets[0].set_pixmap(pixmap_vertical_4k)

    shown = strip.item_widgets[0]._image_label.pixmap()
    assert shown.height() == 80
    assert shown.width() < 2160


def test_miniatura_horizontal_tambien_respeta_la_altura_fija(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])

    pixmap_horizontal_4k = QPixmap(3840, 2160)
    strip.item_widgets[0].set_pixmap(pixmap_horizontal_4k)

    shown = strip.item_widgets[0]._image_label.pixmap()
    assert shown.height() <= 80
    assert shown.width() <= 140
