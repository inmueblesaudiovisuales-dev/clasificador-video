# tests/ui/test_clip_sheet_drop.py
"""Arrastrar material a la hoja (F5).

Antes de esto no habia drag and drop en ninguna parte de la app, asi que
aqui no hay nada heredado que respetar: son las dos zonas de la pantalla 4
del mockup -- soltar SOBRE un bin y soltar en el VACIO.
"""
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, QPointF, QUrl, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent

from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import SIN_CLASIFICAR, ClipSheet, ClipThumbnail


def _thumb(n: int, bin_nombre: str = "", room_label: str | None = None) -> ClipThumbnail:
    """Igual que el `_clip` de `test_clip_sheet.py`, con el bin al frente:
    en este archivo el bin es el dato del que hablan todos los tests."""
    return ClipThumbnail(
        path=Path(f"/tmp/C{n:04d}.MP4"),
        room_label=room_label or SIN_CLASIFICAR,
        flag="none",
        room_color=theme.room_color(0) if room_label else None,
        numero=n,
        bin_nombre=bin_nombre,
    )


def _hoja(qtbot, clips, bins=()) -> ClipSheet:
    """Una hoja VISIBLE y con tamaño real.

    Sin `show()` los layouts nunca corren y todos los widgets quedan en
    (0, 0) con 100x30: sobre esa geometria, «que bin hay bajo el cursor»
    seria una pregunta sobre una hoja que no existe.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(900, 700)
    hoja.set_bin_order(list(bins))
    hoja.set_clips(clips)
    hoja.show()
    qtbot.waitExposed(hoja)
    # el acomodo de las tarjetas es diferido: sin dejar correr el ciclo de
    # eventos, los bloques de grupo se quedan con el alto que tenian vacios y
    # las tarjetas caen FUERA de la franja de su propio bin.
    qtbot.wait(10)
    return hoja


# El evento NO se queda con el `QMimeData`: guarda un puntero crudo. Si el
# objeto de Python se recolecta apenas se construye el evento, leer
# `event.mimeData()` es un SEGFAULT -- comprobado, la suite se caia entera en
# la primera llamada. Por eso vive aqui, colgado del modulo.
_MIMES: list[QMimeData] = []


def _mime(rutas):
    m = QMimeData()
    m.setUrls([QUrl.fromLocalFile(str(r)) for r in rutas])
    _MIMES.append(m)
    return m


def _soltar(hoja, rutas, punto):
    evento = QDropEvent(QPointF(punto), Qt.DropAction.CopyAction, _mime(rutas),
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    hoja.dropEvent(evento)
    return evento


def _arrastrar_encima(hoja, rutas, punto):
    evento = QDragMoveEvent(punto, Qt.DropAction.CopyAction, _mime(rutas),
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    hoja.dragMoveEvent(evento)
    return evento


def _centro_del_encabezado(hoja, nombre):
    cabecera = hoja.bin_header_widget(nombre)
    return cabecera.mapTo(hoja, cabecera.rect().center())


# --- a que bin va lo que sueltas ------------------------------------------


def test_soltar_sobre_un_encabezado_avisa_a_que_bin_va(qtbot, tmp_path):
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Dron")], bins=["Dron"])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_bin.connect(lambda n, r: recibido.append((n, r)))

    _soltar(hoja, [archivo], _centro_del_encabezado(hoja, "Dron"))

    assert recibido == [("Dron", [archivo])]


def test_soltar_sobre_las_tarjetas_cuenta_como_el_bin_de_esas_tarjetas(qtbot, tmp_path):
    """Apuntarle al encabezado exacto seria una mira de 30 px de alto. La
    franja de un bin llega hasta abajo de su ultima tarjeta."""
    hoja = _hoja(
        qtbot,
        [_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")],
        bins=["Sony", "Dron"],
    )
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_bin.connect(lambda n, r: recibido.append((n, r)))

    tarjeta = hoja.item_widgets[0]
    _soltar(hoja, [archivo], tarjeta.mapTo(hoja, tarjeta.rect().center()))

    assert recibido == [("Sony", [archivo])]


def test_soltar_en_el_vacio_pide_un_bin_nuevo(qtbot, tmp_path):
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Dron")], bins=["Dron"])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_nuevo_bin.connect(recibido.append)

    # bien abajo del contenido: ahi no hay bin ninguno
    _soltar(hoja, [archivo], QPoint(20, hoja.height() - 4))

    assert recibido == [[archivo]]


def test_soltar_sobre_los_filtros_no_es_ningun_bin(qtbot, tmp_path):
    """El encabezado de la hoja --busqueda y chips-- no es material. Sin
    esto, el primer bin se comia todo lo que cayera ahi arriba."""
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Dron")], bins=["Dron"])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_nuevo_bin.connect(recibido.append)

    _soltar(hoja, [archivo], QPoint(4, 4))

    assert recibido == [[archivo]]


# --- lo que no se acepta ---------------------------------------------------


def test_soltar_algo_que_no_son_archivos_no_hace_nada(qtbot):
    """Arrastrar texto seleccionado de otra app no puede aceptarse: el
    cursor diria que si y al soltar no pasaria nada."""
    hoja = _hoja(qtbot, [])
    m = QMimeData()
    m.setText("hola")
    evento = QDragEnterEvent(hoja.rect().center(), Qt.DropAction.CopyAction, m,
                             Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.NoModifier)

    hoja.dragEnterEvent(evento)

    assert not evento.isAccepted()
    assert hoja.zona_de_bin_nuevo().isHidden()


# --- lo que se ve mientras arrastras --------------------------------------


def test_la_zona_de_bin_nuevo_solo_se_ve_mientras_arrastras(qtbot, tmp_path):
    """Un recuadro punteado permanente al pie de la hoja seria un cartel
    que no hace nada el 99% del tiempo."""
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Dron")], bins=["Dron"])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    assert hoja.zona_de_bin_nuevo().isHidden()

    _arrastrar_encima(hoja, [archivo], QPoint(20, hoja.height() - 4))
    assert not hoja.zona_de_bin_nuevo().isHidden()

    hoja.dragLeaveEvent(None)
    assert hoja.zona_de_bin_nuevo().isHidden()


def test_el_encabezado_del_bin_de_destino_se_marca_y_los_otros_no(qtbot, tmp_path):
    hoja = _hoja(
        qtbot,
        [_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")],
        bins=["Sony", "Dron"],
    )
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()

    _arrastrar_encima(hoja, [archivo], _centro_del_encabezado(hoja, "Dron"))

    assert hoja.bin_header_widget("Dron").property("soltando") is True
    assert hoja.bin_header_widget("Sony").property("soltando") is not True
    # y el cartel de bin nuevo no puede prometer lo contrario al mismo tiempo
    assert not hoja.zona_de_bin_nuevo().property("activa")


def test_al_soltar_se_apaga_el_resaltado(qtbot, tmp_path):
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Dron")], bins=["Dron"])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    punto = _centro_del_encabezado(hoja, "Dron")
    _arrastrar_encima(hoja, [archivo], punto)

    _soltar(hoja, [archivo], punto)

    assert hoja.bin_header_widget("Dron").property("soltando") is not True
    assert hoja.zona_de_bin_nuevo().isHidden()


def test_un_bin_colapsado_no_se_traga_la_franja_del_de_abajo(qtbot, tmp_path):
    """Bruno colapsa «Sony FX30» --109 clips, altisimo-- para trabajar el
    dron. Los bloques escondidos CONSERVAN la geometria que tenian, muy
    abajo, asi que la franja de Sony seguia llegando hasta ahi y se tragaba
    entera la del Dron, que ahora esta arriba: el resaltado marcaba Sony y
    los archivos entraban a Sony.
    """
    hoja = _hoja(
        qtbot,
        [_thumb(i, bin_nombre="Sony") for i in range(8)]
        + [_thumb(8, bin_nombre="Dron")],
        bins=["Sony", "Dron"],
    )
    hoja.set_bin_collapsed("Sony", True)
    qtbot.wait(10)
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_bin.connect(lambda n, r: recibido.append((n, r)))

    _soltar(hoja, [archivo], _centro_del_encabezado(hoja, "Dron"))

    assert recibido == [("Dron", [archivo])]


def test_la_franja_de_un_bin_colapsado_es_solo_su_encabezado(qtbot, tmp_path):
    hoja = _hoja(
        qtbot,
        [_thumb(i, bin_nombre="Sony") for i in range(8)],
        bins=["Sony"],
    )
    hoja.set_bin_collapsed("Sony", True)
    qtbot.wait(10)
    cabecera = hoja.bin_header_widget("Sony")
    arriba = cabecera.mapTo(hoja, cabecera.rect().topLeft()).y()

    assert hoja._regiones_de_bin() == [["Sony", arriba, arriba + cabecera.height()]]
