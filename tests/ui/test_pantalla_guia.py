import pytest
from PySide6.QtWidgets import QMessageBox, QWidget
from clasificador_video import guia as logica
from clasificador_video.ui.pantalla_guia import PantallaGuia


@pytest.fixture
def pantalla(qtbot):
    p = PantallaGuia(); qtbot.addWidget(p); p.resize(900, 600); return p


def test_arranca_con_siete_columnas_vacias(pantalla):
    assert len(pantalla.columnas) == 7
    assert all(c.cuartos() == [] for c in pantalla.columnas.values())


def test_franja_tiene_todos_los_cuartos(pantalla):
    pantalla.poner_cuartos_reales(["Sala", "Cocina"])
    assert pantalla.franja.cuartos() == ["Sala", "Cocina"]


def test_mostrar_clasificacion_coloca_chips(pantalla):
    pantalla.poner_cuartos_reales(["Sala", "Roof garden"])
    pantalla.mostrar_clasificacion(logica.Clasificacion(True, {"Sala": "sociales"}))
    assert pantalla.columnas["sociales"].cuartos() == ["Sala"]


def test_clasificacion_fallida_deja_columnas_vacias_y_avisa(pantalla):
    pantalla.agregar_a_columna("sociales", "Sala")
    pantalla.show()
    pantalla.mostrar_clasificacion(logica.Clasificacion(False, error="no hay red"))
    assert all(c.cuartos() == [] for c in pantalla.columnas.values())
    assert all(not chip.isVisible() for columna in pantalla.columnas.values()
               for chip in columna.findChildren(QWidget))
    assert "no hay red" in pantalla.aviso_label.text().lower()


def test_repetir_y_orden_final(pantalla):
    pantalla.poner_cuartos_reales(["Dron", "Sala"])
    pantalla.agregar_a_columna("apertura", "Dron")
    pantalla.agregar_a_columna("sociales", "Sala")
    pantalla.agregar_a_columna("aerea_final", "Dron")
    assert pantalla.orden_final() == ["Dron", "Sala", "Dron"]


def test_quitar_paso_y_aviso_sin_usar(pantalla):
    pantalla.poner_cuartos_reales(["Sala"])
    pantalla.agregar_a_columna("sociales", "Sala")
    pantalla.columnas["sociales"].quitar(0)
    assert "Sala" in pantalla.aviso_label.text()


def test_usar_emite_lista_plana(pantalla, qtbot):
    pantalla.agregar_a_columna("sociales", "Sala")
    with qtbot.waitSignal(pantalla.orden_aceptado) as señal: pantalla.usar_button.click()
    assert señal.args == [["Sala"]]


def test_reclasificar_confirma_si_hay_trabajo(pantalla, monkeypatch):
    pantalla.agregar_a_columna("sociales", "Sala")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    pedidos = []; pantalla.clasificacion_pedida.connect(lambda: pedidos.append(1))
    pantalla.clasificar_de_nuevo_button.click()
    assert pedidos == []


# --- el arreglo del arrastre que duplicaba en vez de mover --------------


def test_arrastrar_de_una_columna_a_otra_quita_del_origen(pantalla, monkeypatch):
    from PySide6.QtCore import Qt
    pantalla.poner_cuartos_reales(["Sala"])
    pantalla.agregar_a_columna("sociales", "Sala")
    chip = pantalla.columnas["sociales"]._layout.itemAt(0).widget()
    monkeypatch.setattr(
        "clasificador_video.ui.pantalla_guia.QDrag.exec",
        lambda self, *a, **k: Qt.DropAction.MoveAction,
    )

    chip._arrastrar()

    assert pantalla.columnas["sociales"].cuartos() == []


def test_soltar_fuera_de_una_columna_no_quita_del_origen(pantalla, monkeypatch):
    from PySide6.QtCore import Qt
    pantalla.poner_cuartos_reales(["Sala"])
    pantalla.agregar_a_columna("sociales", "Sala")
    chip = pantalla.columnas["sociales"]._layout.itemAt(0).widget()
    monkeypatch.setattr(
        "clasificador_video.ui.pantalla_guia.QDrag.exec",
        lambda self, *a, **k: Qt.DropAction.IgnoreAction,
    )

    chip._arrastrar()

    assert pantalla.columnas["sociales"].cuartos() == ["Sala"]


def test_arrastrar_desde_la_franja_nunca_la_vacia(pantalla, monkeypatch):
    from PySide6.QtCore import Qt
    pantalla.poner_cuartos_reales(["Sala"])
    chip = pantalla.franja._layout.itemAt(0).widget()
    monkeypatch.setattr(
        "clasificador_video.ui.pantalla_guia.QDrag.exec",
        lambda self, *a, **k: Qt.DropAction.MoveAction,
    )

    chip._arrastrar()

    assert pantalla.franja.cuartos() == ["Sala"]


def test_soltar_en_una_columna_de_verdad_deja_moveaction():
    from PySide6.QtCore import QMimeData, QPointF, Qt
    from PySide6.QtGui import QDropEvent
    from clasificador_video.ui.pantalla_guia import MIME_PASO, _CajaDePasos

    caja = _CajaDePasos(es_franja=False)
    mime = QMimeData()
    mime.setData(MIME_PASO, b"Sala")
    evento = QDropEvent(QPointF(0, 0), Qt.DropAction.MoveAction, mime,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)

    caja.dropEvent(evento)

    assert caja.cuartos() == ["Sala"]
    assert evento.isAccepted()
    assert evento.dropAction() == Qt.DropAction.MoveAction


def test_soltar_en_la_franja_no_agrega_y_no_acepta_mover():
    from PySide6.QtCore import QMimeData, QPointF, Qt
    from PySide6.QtGui import QDropEvent
    from clasificador_video.ui.pantalla_guia import MIME_PASO, _CajaDePasos

    franja = _CajaDePasos(es_franja=True)
    mime = QMimeData()
    mime.setData(MIME_PASO, b"Sala")
    evento = QDropEvent(QPointF(0, 0), Qt.DropAction.MoveAction, mime,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)

    franja.dropEvent(evento)

    assert franja.cuartos() == []
    assert not evento.isAccepted()


# --- el aviso de un cuarto que la IA se inventó --------------------------


def test_mostrar_clasificacion_avisa_un_cuarto_inventado(pantalla):
    pantalla.poner_cuartos_reales(["Sala"])

    pantalla.mostrar_clasificacion(logica.Clasificacion(
        ok=True, columna_de={"Sala": "sociales"}, inventados=["Cuarto Fantasma"]))

    assert "Cuarto Fantasma" in pantalla.aviso_label.text()
    assert pantalla.columnas["sociales"].cuartos() == ["Sala"]
