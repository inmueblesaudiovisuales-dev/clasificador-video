# tests/ui/test_clip_sheet_drop.py
"""Arrastrar material a la hoja (F5) y arrastrar clips entre bins (F9).

Antes de esto no habia drag and drop en ninguna parte de la app, asi que
aqui no hay nada heredado que respetar: son las dos zonas de la pantalla 4
del mockup -- soltar SOBRE un bin y soltar en el VACIO.

La segunda mitad del archivo es el otro arrastre, el de adentro: agarrar
clips que ya estan en la hoja y soltarlos en otro bin. Los dos comparten las
zonas de destino y se distinguen por el mime.
"""
from pathlib import Path

from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, QUrl, Qt
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
    QPixmap,
)
from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import (
    MIME_CLIPS,
    SIN_BIN,
    SIN_CLASIFICAR,
    ClipSheet,
    ClipThumbnail,
)


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


# --- lo que dice el cartel es lo que va a entrar (revision final) ----------


def test_el_cartel_cuenta_los_videos_de_la_carpeta_no_la_carpeta(qtbot, tmp_path):
    """Soltar una carpeta de 23 clips decia «1 archivo»: se contaban las
    URLs crudas. Lo que importa es lo que VA A ENTRAR."""
    carpeta = tmp_path / "02. VIDEO DRONE"
    carpeta.mkdir()
    for i in range(3):
        (carpeta / f"DJI_{i}.MP4").touch()
    (carpeta / "notas.txt").touch()
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Dron")], bins=["Dron"])

    _arrastrar_encima(hoja, [carpeta], _centro_del_encabezado(hoja, "Dron"))

    assert "3" in hoja.bin_header_widget("Dron").drop_label.text()


def test_el_cartel_dice_a_cuantos_se_suman(qtbot, tmp_path):
    """«se suman a los 23 que ya tiene», como el mockup: el dato lo
    tenemos y es lo que responde «¿voy a duplicar la tarjeta?»."""
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    hoja = _hoja(
        qtbot,
        [_thumb(0, bin_nombre="Dron"), _thumb(1, bin_nombre="Dron")],
        bins=["Dron", "Sony"],
    )

    _arrastrar_encima(hoja, [archivo], _centro_del_encabezado(hoja, "Dron"))

    assert "2" in hoja.bin_header_widget("Dron").drop_label.text()


def test_soltar_algo_que_no_es_video_lo_dice_en_vez_de_prometer_uno(
        qtbot, tmp_path):
    notas = tmp_path / "notas.txt"
    notas.touch()
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Dron")], bins=["Dron"])

    _arrastrar_encima(hoja, [notas], _centro_del_encabezado(hoja, "Dron"))

    texto = hoja.bin_header_widget("Dron").drop_label.text()
    assert "1 archivo" not in texto
    assert "ningún video" in texto


def test_la_zona_de_bin_nuevo_tampoco_promete_un_bin_vacio(qtbot, tmp_path):
    notas = tmp_path / "notas.txt"
    notas.touch()
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Dron")], bins=["Dron"])

    _arrastrar_encima(hoja, [notas], QPoint(20, hoja.height() - 4))

    assert "ningún video" in hoja.zona_de_bin_nuevo().title_label.text()
    assert not hoja.zona_de_bin_nuevo().property("activa")


# --- soltar sobre la seccion de sueltos ------------------------------------
#
# «Sin bin» no es un bin: es la VISTA de los clips que no pertenecen a
# ninguno. Soltar material encima tiene que importarlo suelto, que es lo que
# la seccion significa. Antes de esto el nombre de la seccion viajaba como
# nombre de bin y terminaba en `bins.agregar("Sin bin", ...)`: nacia un bin
# de verdad llamado asi, se mezclaba con los sueltos en la misma seccion, se
# guardaba, y «Quitar del proyecto» sobre ese encabezado empezaba a borrar
# clips.


def test_soltar_sobre_sin_bin_importa_suelto_y_no_a_un_bin(qtbot, tmp_path):
    hoja = _hoja(qtbot, [_thumb(0)], bins=[])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    sueltos, en_bin = [], []
    hoja.soltado_sin_bin.connect(sueltos.append)
    hoja.soltado_en_bin.connect(lambda n, r: en_bin.append((n, r)))

    _soltar(hoja, [archivo], _centro_del_encabezado(hoja, SIN_BIN))

    assert sueltos == [[archivo]]
    assert en_bin == []


def test_soltar_sobre_las_tarjetas_sueltas_tambien_va_sin_bin(qtbot, tmp_path):
    """La franja de la seccion llega hasta abajo de su ultima tarjeta, igual
    que la de un bin: apuntarle al encabezado exacto seria una mira de 30 px
    sobre una columna de 700."""
    hoja = _hoja(qtbot, [_thumb(0), _thumb(1, bin_nombre="Dron")], bins=["Dron"])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    sueltos, en_bin = [], []
    hoja.soltado_sin_bin.connect(sueltos.append)
    hoja.soltado_en_bin.connect(lambda n, r: en_bin.append((n, r)))

    tarjeta = hoja.item_widgets[0]
    _soltar(hoja, [archivo], tarjeta.mapTo(hoja, tarjeta.rect().center()))

    assert sueltos == [[archivo]]
    assert en_bin == []


def test_soltar_sobre_sin_bin_no_promete_un_bin_nuevo(qtbot, tmp_path):
    """Las dos zonas nunca prometen a la vez: si la de «bin nuevo» se
    encendiera encima de la seccion de sueltos, el cartel diria que va a
    nacer un bin que no nace."""
    hoja = _hoja(qtbot, [_thumb(0)], bins=[])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()

    _arrastrar_encima(hoja, [archivo], _centro_del_encabezado(hoja, SIN_BIN))

    assert hoja.bin_header_widget(SIN_BIN).property("soltando") is True
    assert hoja.zona_de_bin_nuevo().property("activa") is not True


# =========================================================================
# F9 -- arrastrar clips que YA estan en la hoja, de un bin a otro
# =========================================================================
#
# El gesto entra en el unico hueco que quedaba libre del mouse sobre una
# tarjeta: boton izquierdo APRETADO y mover. Pasar sin apretar escrubea, el
# vacio es la marquesina y con una tecla de cuarto manda el pincel.


def _pixmap() -> QPixmap:
    pm = QPixmap(40, 24)
    pm.fill(Qt.GlobalColor.darkGray)
    return pm


def _press(punto: QPoint, cmd: bool = False) -> QMouseEvent:
    # con la posicion global explicita: la sobrecarga sin ella esta marcada
    # como deprecada y llena la corrida de avisos
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(punto),
        QPointF(punto),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        (Qt.KeyboardModifier.MetaModifier if cmd
         else Qt.KeyboardModifier.NoModifier),
    )


def _release(punto: QPoint) -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(punto),
        QPointF(punto),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )


def _move(punto: QPoint, boton: bool) -> QMouseEvent:
    apretados = (Qt.MouseButton.LeftButton if boton
                 else Qt.MouseButton.NoButton)
    return QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(punto),
        QPointF(punto),
        Qt.MouseButton.NoButton,
        apretados,
        Qt.KeyboardModifier.NoModifier,
    )


# --- iniciar el arrastre desde una tarjeta (tarea 5) -----------------------


def test_mover_con_el_boton_apretado_arranca_un_arrastre(qtbot):
    """El hueco libre de la hoja: escrubear es AL PASAR sin apretar, la
    marquesina es en el vacio, y el pincel pide una tecla de cuarto.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0), _thumb(1)])
    tarjeta = hoja.item_widgets[0]
    arrastres = []
    tarjeta.arrastre_pedido.connect(arrastres.append)

    tarjeta.mousePressEvent(_press(QPoint(5, 5)))
    tarjeta.mouseMoveEvent(_move(QPoint(60, 60), boton=True))

    assert arrastres == [0]


def test_cada_tarjeta_avisa_de_SU_indice(qtbot):
    """La tarjeta no busca su indice en la lista en cada evento: se lo dice
    la hoja al crearla. Con la captura por referencia, todas avisarian del
    ultimo clip."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0), _thumb(1), _thumb(2)])

    assert [c.indice for c in hoja.item_widgets] == [0, 1, 2]


def test_las_tarjetas_agregadas_despues_tambien_saben_su_indice(qtbot):
    """`append_clips` es el camino de importar una segunda carpeta. Sin
    indice, las tarjetas nuevas arrastrarian el clip 0."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    hoja.append_clips([_thumb(0), _thumb(1), _thumb(2)])

    assert [c.indice for c in hoja.item_widgets] == [0, 1, 2]


def test_un_temblor_no_arranca_un_arrastre(qtbot):
    """Un clic con la mano temblorosa sigue siendo un clic: el arrastre
    arranca al superar la distancia estandar de Qt, no al primer pixel."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    tarjeta = hoja.item_widgets[0]
    arrastres = []
    tarjeta.arrastre_pedido.connect(arrastres.append)

    tarjeta.mousePressEvent(_press(QPoint(5, 5)))
    tarjeta.mouseMoveEvent(_move(QPoint(7, 6), boton=True))

    assert arrastres == []


def test_pasar_sin_apretar_sigue_escrubeando(qtbot):
    """La regresion que este plan no puede causar: el escrubeo al pasar el
    mouse es de lo que Bruno mas usa."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    tarjeta = hoja.item_widgets[0]
    tarjeta._frames = [_pixmap(), _pixmap(), _pixmap()]
    arrastres = []
    tarjeta.arrastre_pedido.connect(arrastres.append)

    tarjeta.mouseMoveEvent(_move(QPoint(60, 60), boton=False))

    assert arrastres == []
    assert tarjeta._hover is not None


def test_mientras_arrastras_la_miniatura_no_escrubea(qtbot):
    """Los dos gestos son excluyentes por construccion: si el arrastre
    tambien escrubeara, cada clip que movieras quedaria mostrando un cuadro
    al azar."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    tarjeta = hoja.item_widgets[0]
    tarjeta._frames = [_pixmap(), _pixmap(), _pixmap()]

    tarjeta.mousePressEvent(_press(QPoint(5, 5)))
    tarjeta.mouseMoveEvent(_move(QPoint(60, 60), boton=True))

    assert tarjeta._hover is None


def test_con_el_pincel_activo_no_hay_arrastre(qtbot):
    """Con una tecla de cuarto apretada manda el pincel.

    Quien lo corta es la HOJA, no la tarjeta: los modos de la hoja son de la
    hoja, y una tarjeta que tuviera que preguntar por ellos sabria de mas. Por
    eso esto se mira por lo que la hoja hace con la señal --armar la imagen que
    cuelga del cursor es lo primero de un arrastre-- y no por si la tarjeta
    avisa.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    pedidas = []
    hoja.imagen_de_arrastre = lambda indices: (pedidas.append(indices)
                                               or QPixmap(4, 4))

    hoja._on_arrastre_pedido(0)
    assert pedidas == [[0]]        # sin pincel, el arrastre arranca

    hoja.set_pincel_activo(True)
    hoja._on_arrastre_pedido(0)
    assert pedidas == [[0]]        # con pincel, no arranco otro


# --- que se lleva el arrastre ---------------------------------------------


def test_se_va_toda_la_seleccion_no_solo_el_que_arrastraste(qtbot):
    """Arrastrar uno de tres seleccionados se lleva los tres: es lo que hace
    Finder y lo que hace Premiere."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(i, bin_nombre="Sony") for i in range(3)])
    hoja.set_selected({0, 1, 2})

    assert hoja.indices_a_arrastrar(1) == [0, 1, 2]


def test_arrastrar_uno_no_seleccionado_se_lleva_solo_ese(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(i) for i in range(3)])
    hoja.set_selected({0, 1})

    assert hoja.indices_a_arrastrar(2) == [2]


# --- soltar los clips ------------------------------------------------------


def _mime_clips(indices):
    m = QMimeData()
    m.setData(MIME_CLIPS, ",".join(str(i) for i in indices).encode())
    _MIMES.append(m)          # el evento guarda un puntero crudo, ver arriba
    return m


def _soltar_clips(hoja, indices, punto):
    evento = QDropEvent(QPointF(punto), Qt.DropAction.MoveAction,
                        _mime_clips(indices), Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier)
    hoja.dropEvent(evento)
    return evento


def _arrastrar_clips_encima(hoja, indices, punto):
    evento = QDragMoveEvent(punto, Qt.DropAction.MoveAction,
                            _mime_clips(indices), Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
    hoja.dragMoveEvent(evento)
    return evento


def test_soltar_clips_sobre_un_bin_avisa_a_cual(qtbot):
    hoja = _hoja(
        qtbot,
        [_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Sony")],
        bins=["Sony", "Dron"],
    )
    recibido = []
    hoja.clips_movidos.connect(lambda idx, destino: recibido.append((idx, destino)))

    _soltar_clips(hoja, [0, 1], _centro_del_encabezado(hoja, "Dron"))

    assert recibido == [([0, 1], "Dron")]


def test_soltar_clips_en_sin_bin_los_deja_sueltos(qtbot):
    """«Sin bin» no es un bin: es la vista de los sueltos. El destino que
    viaja es `None`, no su nombre."""
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Sony"), _thumb(1)],
                 bins=["Sony"])
    recibido = []
    hoja.clips_movidos.connect(lambda idx, destino: recibido.append((idx, destino)))

    _soltar_clips(hoja, [0], _centro_del_encabezado(hoja, SIN_BIN))

    assert recibido == [([0], None)]


def test_soltar_un_clip_en_su_propio_bin_no_hace_nada(qtbot):
    """El arrastre fallido mas comun. Avisar igual costaria un refresco, un
    guardado y el scroll de vuelta arriba, para no cambiar nada."""
    hoja = _hoja(
        qtbot,
        [_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")],
        bins=["Sony", "Dron"],
    )
    recibido = []
    hoja.clips_movidos.connect(lambda idx, destino: recibido.append((idx, destino)))

    _soltar_clips(hoja, [0], _centro_del_encabezado(hoja, "Sony"))

    assert recibido == []


def test_soltar_un_suelto_en_sin_bin_tampoco_hace_nada(qtbot):
    hoja = _hoja(qtbot, [_thumb(0), _thumb(1, bin_nombre="Dron")], bins=["Dron"])
    recibido = []
    hoja.clips_movidos.connect(lambda idx, destino: recibido.append((idx, destino)))

    _soltar_clips(hoja, [0], _centro_del_encabezado(hoja, SIN_BIN))

    assert recibido == []


def test_soltar_clips_en_el_vacio_no_crea_un_bin(qtbot):
    """Soltar ARCHIVOS en el vacio pide un bin nuevo. Soltar clips que ya
    estan en la hoja, no: no hay carpeta de origen de la que sacarle nombre,
    y un bin «Bin 2» sorpresa no es lo que pediste."""
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Sony")], bins=["Sony"])
    movidos, nuevos = [], []
    hoja.clips_movidos.connect(lambda idx, destino: movidos.append((idx, destino)))
    hoja.soltado_en_nuevo_bin.connect(nuevos.append)

    _soltar_clips(hoja, [0], QPoint(20, hoja.height() - 4))

    assert movidos == []
    assert nuevos == []


def test_soltar_sobre_el_subgrupo_de_un_cuarto_va_al_bin_no_al_cuarto(qtbot):
    """Decision de Bruno: arrastrar es para acomodar por camara. El cuarto se
    sigue poniendo con el teclado."""
    hoja = _hoja(
        qtbot,
        [_thumb(0, bin_nombre="Sony"),
         _thumb(1, bin_nombre="Dron", room_label="Cocina")],
        bins=["Sony", "Dron"],
    )
    recibido = []
    hoja.clips_movidos.connect(lambda idx, destino: recibido.append((idx, destino)))

    tarjeta = hoja.item_widgets[1]      # la que vive bajo «Cocina» del Dron
    _soltar_clips(hoja, [0], tarjeta.mapTo(hoja, tarjeta.rect().center()))

    assert recibido == [([0], "Dron")]


# --- lo que se ve mientras arrastras clips ---------------------------------


def test_el_bin_de_destino_se_resalta_y_dice_que_va_a_mover(qtbot):
    hoja = _hoja(
        qtbot,
        [_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Sony")],
        bins=["Sony", "Dron"],
    )

    _arrastrar_clips_encima(hoja, [0, 1], _centro_del_encabezado(hoja, "Dron"))

    cabecera = hoja.bin_header_widget("Dron")
    assert cabecera.property("soltando") is True
    assert "mover" in cabecera.drop_label.text()
    assert "2" in cabecera.drop_label.text()
    assert hoja.bin_header_widget("Sony").property("soltando") is not True


def test_arrastrando_clips_no_se_ofrece_un_bin_nuevo(qtbot):
    """La zona de «bin nuevo» es de los archivos. Encenderla aqui prometeria
    un bin que no va a nacer."""
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Sony")], bins=["Sony"])

    _arrastrar_clips_encima(hoja, [0], QPoint(20, hoja.height() - 4))

    assert hoja.zona_de_bin_nuevo().isHidden()


def test_el_bin_propio_no_se_resalta_al_pasarle_los_clips_encima(qtbot):
    """El resaltado es una promesa: si el bin de origen se encendiera, el
    cursor diria que soltar ahi hace algo, y no hace nada."""
    hoja = _hoja(
        qtbot,
        [_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Dron")],
        bins=["Sony", "Dron"],
    )

    _arrastrar_clips_encima(hoja, [0], _centro_del_encabezado(hoja, "Sony"))

    assert hoja.bin_header_widget("Sony").property("soltando") is not True


def test_arrastrar_clips_no_se_confunde_con_arrastrar_archivos(qtbot, tmp_path):
    """Los dos mimes viajan por los mismos eventos. Este es el test de que
    el camino viejo --material del Finder-- sigue entero."""
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Sony")], bins=["Sony"])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    en_bin, movidos = [], []
    hoja.soltado_en_bin.connect(lambda n, r: en_bin.append((n, r)))
    hoja.clips_movidos.connect(lambda idx, d: movidos.append((idx, d)))

    _soltar(hoja, [archivo], _centro_del_encabezado(hoja, "Sony"))

    assert en_bin == [("Sony", [archivo])]
    assert movidos == []


def test_al_soltar_clips_se_apaga_el_resaltado(qtbot):
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Sony")], bins=["Sony", "Dron"])
    punto = _centro_del_encabezado(hoja, "Dron")
    _arrastrar_clips_encima(hoja, [0], punto)

    _soltar_clips(hoja, [0], punto)

    assert hoja.bin_header_widget("Dron").property("soltando") is not True


# --- la imagen que va colgada del cursor -----------------------------------


def test_la_imagen_de_arrastre_no_esta_vacia(qtbot):
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Sony")], bins=["Sony"])

    imagen = hoja.imagen_de_arrastre([0])

    assert not imagen.isNull()


def test_con_varios_clips_la_imagen_dice_cuantos(qtbot):
    """Arrastrando 12 clips el cursor tiene que decir 12, o estarias
    moviendo a ciegas todo lo que no cabe en la miniatura."""
    hoja = _hoja(qtbot, [_thumb(i, bin_nombre="Sony") for i in range(3)],
                 bins=["Sony"])

    una = hoja.imagen_de_arrastre([0])
    tres = hoja.imagen_de_arrastre([0, 1, 2])

    # la insignia con la cuenta se dibuja ENCIMA y la hace mas alta
    assert tres.height() > una.height()


# --- que el PRESS no te deshaga la seleccion antes de arrastrarla ----------
#
# `clicked` sale en el press, y sin modificadores eso colapsaba la seleccion a
# la tarjeta apretada. Para cuando el mouse se movia, los otros dos ya no
# estaban seleccionados: agarrabas tres clips y se movia uno. Los tests que
# preguntan `indices_a_arrastrar` directo pasaban en verde con el gesto roto,
# asi que estos van POR EL PRESS, que es donde vivia el bug.


def _arrastrar_de_verdad(hoja, tarjeta, desde=QPoint(5, 5), hasta=QPoint(60, 60)):
    """El gesto completo, cortado justo antes de `QDrag.exec()`.

    Devuelve los indices que iban en el mime. No se entra al `exec()` de Qt:
    es un bucle de eventos anidado dentro de la suite, que es justo lo que
    colgaba `test_app.py` antes de la F3.
    """
    llevados = []
    hoja._ejecutar_arrastre = lambda drag: llevados.append(
        hoja._indices_de(drag.mimeData())
    )
    tarjeta.mousePressEvent(_press(desde))
    tarjeta.mouseMoveEvent(_move(hasta, boton=True))
    return llevados


def test_arrastrar_uno_de_varios_seleccionados_se_los_lleva_todos(qtbot):
    """§6.b, punto 4: «uno o varios a la vez, lo que este seleccionado se va
    junto». El gesto entero, no `indices_a_arrastrar` a solas."""
    hoja = _hoja(qtbot, [_thumb(i, bin_nombre="Sony") for i in range(3)],
                 bins=["Sony"])
    hoja.set_selected({0, 1, 2})

    assert _arrastrar_de_verdad(hoja, hoja.item_widgets[1]) == [[0, 1, 2]]


def test_apretar_una_tarjeta_ya_seleccionada_no_colapsa_la_seleccion(qtbot):
    hoja = _hoja(qtbot, [_thumb(i) for i in range(3)])
    hoja.set_selected({0, 1, 2})

    hoja.item_widgets[1].mousePressEvent(_press(QPoint(5, 5)))

    assert hoja.selected_indices() == [0, 1, 2]


def test_si_no_arrastraste_el_click_si_colapsa_al_soltar(qtbot):
    """Lo que se difiere es el COLAPSO, no se cancela: un click normal sobre
    una tarjeta ya seleccionada sigue dejando solo esa."""
    hoja = _hoja(qtbot, [_thumb(i) for i in range(3)])
    hoja.set_selected({0, 1, 2})
    tarjeta = hoja.item_widgets[1]

    tarjeta.mousePressEvent(_press(QPoint(5, 5)))
    tarjeta.mouseReleaseEvent(_release(QPoint(5, 5)))

    assert hoja.selected_indices() == [1]


def test_apretar_una_tarjeta_NO_seleccionada_colapsa_en_el_acto(qtbot):
    """Aqui no hay nada que proteger: la seleccion vieja no es lo que estas
    agarrando, y esperar al release haria que el borde azul llegara tarde."""
    hoja = _hoja(qtbot, [_thumb(i) for i in range(3)])
    hoja.set_selected({0, 1})

    hoja.item_widgets[2].mousePressEvent(_press(QPoint(5, 5)))

    assert hoja.selected_indices() == [2]


def test_con_cmd_apretar_una_seleccionada_no_la_saca_antes_de_arrastrar(qtbot):
    """Peor que el caso sin modificadores: ⌘ sobre una tarjeta seleccionada la
    QUITA de la seleccion en el press, asi que arrastrabas justo la que
    acababas de sacar, sola."""
    hoja = _hoja(qtbot, [_thumb(i, bin_nombre="Sony") for i in range(3)],
                 bins=["Sony"])
    hoja.set_selected({0, 1, 2})

    assert _arrastrar_de_verdad(hoja, hoja.item_widgets[1]) == [[0, 1, 2]]
    assert hoja.selected_indices() == [0, 1, 2]


def test_con_cmd_un_click_sin_arrastre_si_quita_la_tarjeta(qtbot):
    hoja = _hoja(qtbot, [_thumb(i) for i in range(3)])
    hoja.set_selected({0, 1, 2})
    tarjeta = hoja.item_widgets[1]

    tarjeta.mousePressEvent(_press(QPoint(5, 5), cmd=True))
    tarjeta.mouseReleaseEvent(_release(QPoint(5, 5)))

    assert hoja.selected_indices() == [0, 2]


def test_arrastrar_cancela_el_colapso_diferido(qtbot):
    """Si el colapso siguiera pendiente despues del arrastre, el release --que
    `QDrag.exec()` se traga-- lo aplicaria en cualquier momento posterior y te
    dejaria seleccionado un solo clip de los tres que moviste."""
    hoja = _hoja(qtbot, [_thumb(i, bin_nombre="Sony") for i in range(3)],
                 bins=["Sony"])
    hoja.set_selected({0, 1, 2})
    tarjeta = hoja.item_widgets[1]

    _arrastrar_de_verdad(hoja, tarjeta)
    tarjeta.mouseReleaseEvent(_release(QPoint(60, 60)))

    assert hoja.selected_indices() == [0, 1, 2]


# --- la marquesina no puede sobrevivir al arrastre -------------------------


def test_arrastrar_desarma_la_marquesina(qtbot):
    """`ClipCard.mousePressEvent` termina en `super()`, que IGNORA el evento:
    sube al viewport y arma la marquesina. Despues `QDrag.exec()` se traga el
    release, asi que `terminar_marquesina` no corre nunca y el origen
    sobrevive al arrastre.
    """
    hoja = _hoja(qtbot, [_thumb(i, bin_nombre="Sony") for i in range(3)],
                 bins=["Sony"])
    hoja.empezar_marquesina(QPoint(5, 5))      # lo que hace el press de verdad

    _arrastrar_de_verdad(hoja, hoja.item_widgets[0])

    assert hoja._origen_marquesina is None
    assert hoja.marquesina.isHidden()


def test_despues_de_arrastrar_mover_el_mouse_no_selecciona_solo(qtbot):
    """El sintoma: sueltas un clip en otro bin, mueves el mouse sin apretar
    nada, y la hoja se pone a dibujar una banda azul y a reemplazarte la
    seleccion. Los eventos de movimiento llegan al viewport porque las
    tarjetas tienen `setMouseTracking` y los dejan subir.
    """
    hoja = _hoja(qtbot, [_thumb(i, bin_nombre="Sony") for i in range(3)],
                 bins=["Sony"])
    hoja.set_selected({0})
    hoja.empezar_marquesina(QPoint(5, 5))
    _arrastrar_de_verdad(hoja, hoja.item_widgets[0])

    hoja.mover_marquesina(QPoint(400, 400))

    assert hoja.selected_indices() == [0]
    assert hoja.marquesina.isHidden()


# --- el evento tiene que seguir su camino ---------------------------------
#
# Qt propaga un evento de mouse al widget padre solo si el hijo lo IGNORA, y
# `QWidget.mouseMoveEvent` lo ignora por default. O sea que llamar a `super()`
# es literalmente «dejalo subir al viewport», que es donde viven el pincel y
# la marquesina. Devolverse sin llamarlo lo mata ahi mismo.


def test_con_el_pincel_activo_el_movimiento_sigue_llegando_al_viewport(qtbot):
    """Con el pincel cargado Y el boton apretado --gesto natural, y que
    funcionaba antes de la F9-- el pincel dejaba de pintar: el arrastre
    cortaba por `_pincel_activo` y el evento ya no subia. No pasaba nada en
    absoluto. «Gana el pincel» tiene que significar que el pincel PINTA, no
    solo que el arrastre no arranca.
    """
    hoja = _hoja(qtbot, [_thumb(0)])
    hoja.set_pincel_activo(True)
    tarjeta = hoja.item_widgets[0]
    tarjeta.mousePressEvent(_press(QPoint(5, 5)))

    evento = _move(QPoint(60, 60), boton=True)
    tarjeta.mouseMoveEvent(evento)

    assert not evento.isAccepted()


def test_antes_del_umbral_el_movimiento_tambien_sigue_su_camino(qtbot):
    """Mientras el gesto todavia puede ser un click, nadie se lo queda."""
    hoja = _hoja(qtbot, [_thumb(0)])
    tarjeta = hoja.item_widgets[0]
    tarjeta.mousePressEvent(_press(QPoint(5, 5)))

    evento = _move(QPoint(7, 6), boton=True)
    tarjeta.mouseMoveEvent(evento)

    assert not evento.isAccepted()


def test_pasar_sin_boton_sigue_su_camino_como_siempre(qtbot):
    """La rama del escrubeo ya lo hacia y tiene que seguir haciendolo: de ahi
    salen los eventos que el viewport usa para el pincel sin boton."""
    hoja = _hoja(qtbot, [_thumb(0)])
    tarjeta = hoja.item_widgets[0]

    evento = _move(QPoint(60, 60), boton=False)
    tarjeta.mouseMoveEvent(evento)

    assert not evento.isAccepted()


# --- la miniatura no puede quedarse clavada -------------------------------


def test_al_arrastrar_la_miniatura_vuelve_a_la_portada(qtbot):
    """Para llegar a arrastrar una tarjeta tuviste que pasarle el mouse por
    encima, o sea escrubearla. Y el reset vive en `leaveEvent`, que durante el
    arrastre no llega --el mouse esta tomado-- y al soltar tampoco, porque el
    cursor termina sobre el encabezado de destino y no sobre la tarjeta. El
    clip que acabas de mover se quedaba mostrando el cuadro por el que ibas
    pasando, con su barrita de escrubeo y su timecode encima.

    Que la rama del arrastre no escrubee impide ENSUCIAR mas; no limpia lo que
    el hover ya habia dejado.
    """
    hoja = _hoja(qtbot, [_thumb(0, bin_nombre="Sony")], bins=["Sony"])
    tarjeta = hoja.item_widgets[0]
    tarjeta.set_frames([_pixmap() for _ in range(8)])
    tarjeta.escrubear_a(0.9)
    assert tarjeta._hover is not None
    assert tarjeta._shown_index != tarjeta._poster_index

    _arrastrar_de_verdad(hoja, tarjeta)

    assert tarjeta._hover is None
    assert tarjeta._shown_index == tarjeta._poster_index


def test_reponer_la_portada_es_lo_mismo_que_salir_de_la_tarjeta(qtbot):
    """Un solo camino para volver a la portada: si fueran dos, uno de los dos
    se iba a olvidar de apagar la barrita del escrubeo."""
    hoja = _hoja(qtbot, [_thumb(0)])
    tarjeta = hoja.item_widgets[0]
    tarjeta.set_frames([_pixmap() for _ in range(8)])

    tarjeta.escrubear_a(0.9)
    tarjeta.leaveEvent(QEvent(QEvent.Type.Leave))
    por_salir = (tarjeta._hover, tarjeta._shown_index)

    tarjeta.escrubear_a(0.9)
    tarjeta.reponer_portada()

    assert (tarjeta._hover, tarjeta._shown_index) == por_salir
