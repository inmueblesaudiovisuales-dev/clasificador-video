from clasificador_video.ui.segmented import SegmentedControl


def test_crea_un_boton_por_opcion(qtbot):
    seg = SegmentedControl(["Full", "1/2", "1/4", "1/8"])
    qtbot.addWidget(seg)
    assert [b.text() for b in seg.buttons] == ["Full", "1/2", "1/4", "1/8"]


def test_la_primera_opcion_queda_activa_por_defecto(qtbot):
    seg = SegmentedControl(["Full", "1/2"])
    qtbot.addWidget(seg)
    assert seg.current() == "Full"
    assert seg.buttons[0].isChecked()


def test_seleccionar_emite_la_senal_con_el_texto(qtbot):
    seg = SegmentedControl(["Full", "1/2"])
    qtbot.addWidget(seg)
    with qtbot.waitSignal(seg.selected) as blocker:
        seg.buttons[1].click()
    assert blocker.args == ["1/2"]
    assert seg.current() == "1/2"


def test_solo_una_opcion_queda_activa_a_la_vez(qtbot):
    seg = SegmentedControl(["a", "b", "c"])
    qtbot.addWidget(seg)
    seg.buttons[2].click()
    assert [b.isChecked() for b in seg.buttons] == [False, False, True]


def test_set_current_no_emite_senal(qtbot):
    """Sincronizar el control desde el estado no debe disparar el handler
    que cambia el perfil del reproductor -- si lo hiciera, refrescar la UI
    reabriria el clip en bucle."""
    seg = SegmentedControl(["a", "b"])
    qtbot.addWidget(seg)
    with qtbot.assertNotEmitted(seg.selected):
        seg.set_current("b")
    assert seg.current() == "b"


def test_set_current_con_valor_desconocido_no_cambia_nada(qtbot):
    seg = SegmentedControl(["a", "b"])
    qtbot.addWidget(seg)
    seg.set_current("no existe")
    assert seg.current() == "a"


def test_los_botones_no_roban_el_foco(qtbot):
    """Con botones enfocables en el camino, la tecla Espacio activaria el
    boton en vez de reproducir el clip."""
    from PySide6.QtCore import Qt

    seg = SegmentedControl(["a", "b"])
    qtbot.addWidget(seg)
    assert all(b.focusPolicy() == Qt.FocusPolicy.NoFocus for b in seg.buttons)


def test_tiene_objectnames_para_el_tema(qtbot):
    seg = SegmentedControl(["a"])
    qtbot.addWidget(seg)
    assert seg.objectName() == "segmentedControl"
    assert seg.buttons[0].objectName() == "segmentedButton"
