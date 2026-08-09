# tests/ui/test_clip_sheet_vacio.py
"""Los dos estados vacios de la hoja.

Son dos, y no el mismo dos veces:

- **la hoja entera vacia** es lo PRIMERO que ve alguien que abre la app: no
  hay sesion, no hay clips y no hay bins. Hasta aqui la hoja se quedaba en
  blanco, sin decir que se puede arrastrar ni que se puede crear un bin.
- **un bin vacio** existe desde que se pueden crear bins sin material (F8).
  Un bin recien creado que no dice nada se lee como un error.
"""
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QMimeData, QUrl, Qt
from PySide6.QtGui import QDragMoveEvent, QDropEvent

from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import (
    SIN_BIN,
    SIN_CLASIFICAR,
    ClipSheet,
    ClipThumbnail,
)


def _thumb(n: int, bin_nombre: str = "") -> ClipThumbnail:
    return ClipThumbnail(
        path=Path(f"/tmp/C{n:04d}.MP4"),
        room_label=SIN_CLASIFICAR,
        flag="none",
        room_color=None,
        numero=n,
        bin_nombre=bin_nombre,
    )


def _hoja(qtbot, clips=(), bins=()) -> ClipSheet:
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.resize(900, 700)
    hoja.set_bin_order(list(bins))
    hoja.set_clips(list(clips))
    hoja.show()
    qtbot.waitExposed(hoja)
    qtbot.wait(10)
    return hoja


# el evento de Qt guarda un puntero crudo al mime: si Python lo recolecta,
# leerlo es un segfault. Mismo truco que en `test_clip_sheet_drop.py`.
_MIMES: list[QMimeData] = []


def _mime(rutas):
    m = QMimeData()
    m.setUrls([QUrl.fromLocalFile(str(r)) for r in rutas])
    _MIMES.append(m)
    return m


# --- la hoja entera vacia --------------------------------------------------


def test_una_hoja_sin_nada_invita_a_arrastrar_o_a_crear_un_bin(qtbot):
    hoja = _hoja(qtbot)

    vacio = hoja.estado_vacio()

    assert not vacio.isHidden()
    assert "Arrastra" in vacio.title_label.text()
    assert "bin" in vacio.hint_label.text()


def test_con_clips_la_hoja_no_muestra_el_estado_vacio(qtbot):
    hoja = _hoja(qtbot, [_thumb(0)])

    assert hoja.estado_vacio().isHidden()


def test_un_bin_declarado_ya_no_es_una_hoja_vacia(qtbot):
    """Un bin vacio se dibuja con su encabezado y su propio renglon, asi que
    la hoja ya dice algo: el cartel del centro seria un segundo mensaje
    encima del primero."""
    hoja = _hoja(qtbot, bins=["Dron"])

    assert hoja.estado_vacio().isHidden()


def test_quitar_el_ultimo_clip_devuelve_el_estado_vacio(qtbot):
    hoja = _hoja(qtbot, [_thumb(0)])

    hoja.set_clips([])

    assert not hoja.estado_vacio().isHidden()


def test_el_boton_del_estado_vacio_pide_un_bin_nuevo(qtbot):
    """El mismo pedido que el boton de la barra: la hoja no crea el bin, el
    dato vive en la ventana."""
    hoja = _hoja(qtbot)
    pedidos = []
    hoja.bin_nuevo_pedido.connect(lambda: pedidos.append(1))

    hoja.estado_vacio().boton.click()

    assert pedidos == [1]


def test_soltar_encima_del_estado_vacio_sigue_pidiendo_un_bin_nuevo(qtbot, tmp_path):
    """El cartel esta JUSTO donde vas a soltar. Si se comiera el drop,
    arrastrar carpetas a una app recien abierta no funcionaria."""
    hoja = _hoja(qtbot)
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_nuevo_bin.connect(recibido.append)

    vacio = hoja.estado_vacio()
    punto = vacio.mapTo(hoja, vacio.rect().center())
    evento = QDropEvent(QPointF(punto), Qt.DropAction.CopyAction, _mime([archivo]),
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    hoja.dropEvent(evento)

    assert recibido == [[archivo]]


def test_mientras_arrastras_el_cartel_le_deja_el_lugar_a_la_zona_de_bin_nuevo(
        qtbot, tmp_path):
    """Los dos ocupan el centro de una hoja vacia. Con el cartel encima, la
    zona punteada --que es la que promete lo que va a pasar al soltar-- se
    veria tapada."""
    hoja = _hoja(qtbot)
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    evento = QDragMoveEvent(QPoint(20, hoja.height() - 4),
                            Qt.DropAction.CopyAction, _mime([archivo]),
                            Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)

    hoja.dragMoveEvent(evento)
    assert hoja.estado_vacio().isHidden()

    hoja.dragLeaveEvent(None)
    assert not hoja.estado_vacio().isHidden()


def test_el_estado_vacio_no_cuesta_un_acomodo_de_mas(qtbot, monkeypatch):
    """`_regroup` corre en cada tecla. Mostrar o esconder el cartel no puede
    invalidar la firma de acomodo, que es lo que evita re-colocar 128
    tarjetas cuatro veces por pulsacion."""
    hoja = _hoja(qtbot, [_thumb(0, "Dron")], bins=["Dron", "Sony"])
    # que el ancho definitivo ya este medido: el primer acomodo despues de
    # mostrar la hoja es legitimo y no tiene nada que ver con esto
    hoja._relayout()
    veces = []
    monkeypatch.setattr(hoja, "_acomodar_de_verdad",
                        lambda: veces.append(1))

    hoja._regroup()
    hoja._regroup()

    assert veces == []


# --- un bin vacio ----------------------------------------------------------


def test_un_bin_sin_clips_pide_que_le_arrastres(qtbot):
    hoja = _hoja(qtbot, bins=["Dron"])

    renglon = hoja.renglon_de_bin_vacio("Dron")

    assert renglon is not None
    assert not renglon.isHidden()
    assert "arrástrale" in renglon.text()


def test_el_renglon_va_debajo_del_encabezado_de_su_bin(qtbot):
    hoja = _hoja(qtbot, bins=["Dron", "Sony"])

    orden = [
        w.nombre if hasattr(w, "nombre") else w.text()
        for w in hoja._widgets_del_contenido()
        if w is not hoja.zona_de_bin_nuevo()
    ]

    assert orden[0] == "Dron"
    assert "arrástrale" in orden[1]
    assert orden[2] == "Sony"


def test_un_bin_con_clips_no_lleva_renglon(qtbot):
    hoja = _hoja(qtbot, [_thumb(0, "Dron")], bins=["Dron"])

    assert hoja.renglon_de_bin_vacio("Dron").isHidden()


def test_el_renglon_desaparece_cuando_al_bin_le_llega_material(qtbot):
    hoja = _hoja(qtbot, bins=["Dron"])
    assert not hoja.renglon_de_bin_vacio("Dron").isHidden()

    hoja.set_clips([_thumb(0, "Dron")])

    assert hoja.renglon_de_bin_vacio("Dron").isHidden()


def test_un_filtro_que_no_deja_pasar_nada_no_vacia_el_bin(qtbot):
    """Filtrar no es vaciar: el bin tiene material, solo que no lo estas
    viendo. Decirle «arrástrale clips» seria mentirle al filtro."""
    hoja = _hoja(qtbot, [_thumb(0, "Dron")], bins=["Dron"])

    hoja.set_visible_indices(set())

    assert hoja.renglon_de_bin_vacio("Dron").isHidden()


def test_un_bin_colapsado_esconde_su_renglon(qtbot):
    """Colapsar es cerrar el bin entero. Dejar el renglon asomando seria lo
    mismo que dejar las lineas de sus cuartos, que ya se esconden."""
    hoja = _hoja(qtbot, bins=["Dron"])

    hoja.set_bin_collapsed("Dron", True)
    assert hoja.renglon_de_bin_vacio("Dron").isHidden()

    hoja.set_bin_collapsed("Dron", False)
    assert not hoja.renglon_de_bin_vacio("Dron").isHidden()


def test_la_seccion_de_sueltos_no_lleva_renglon(qtbot):
    """«Sin bin» solo aparece cuando hay sueltos, asi que vacia no existe --
    y no es un bin al que se le arrastre nada."""
    hoja = _hoja(qtbot, [_thumb(0)])

    assert hoja.renglon_de_bin_vacio(SIN_BIN) is None


def test_soltar_sobre_el_renglon_cuenta_como_su_bin(qtbot, tmp_path):
    """El renglon es la unica franja que tiene un bin vacio ademas de su
    encabezado: si no contara, apuntarle seria una mira de 30 px."""
    hoja = _hoja(qtbot, bins=["Dron"])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_bin.connect(lambda n, r: recibido.append((n, r)))

    renglon = hoja.renglon_de_bin_vacio("Dron")
    punto = renglon.mapTo(hoja, renglon.rect().center())
    evento = QDropEvent(QPointF(punto), Qt.DropAction.CopyAction, _mime([archivo]),
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    hoja.dropEvent(evento)

    assert recibido == [("Dron", [archivo])]


def test_el_renglon_de_un_bin_que_ya_no_existe_se_va_con_el(qtbot):
    hoja = _hoja(qtbot, bins=["Dron"])
    assert hoja.renglon_de_bin_vacio("Dron") is not None

    hoja.set_bin_order([])

    assert hoja.renglon_de_bin_vacio("Dron") is None


def test_el_renglon_usa_los_colores_del_tema(qtbot):
    """Discreto a proposito: es un aviso, no un cartel. Va en el gris mas
    apagado del tema, el mismo de los hints de la hoja."""
    assert "QLabel#binEmptyHint" in theme.build_stylesheet()
    assert "QWidget#sheetEmpty" in theme.build_stylesheet()
