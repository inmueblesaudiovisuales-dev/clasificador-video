# tests/test_qt_smoke.py
from PySide6.QtWidgets import QLabel


def test_qtbot_puede_crear_un_widget(qtbot):
    label = QLabel("hola")
    qtbot.addWidget(label)
    assert label.text() == "hola"
