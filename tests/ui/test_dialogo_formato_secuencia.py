"""El formato se elige antes de guardar el JSON, no al abrir Premiere."""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QDialog, QFrame, QLabel, QPushButton, QRadioButton, QWidget

from clasificador_video.ui.dialogo_formato_secuencia import DialogoFormatoSecuencia
from clasificador_video.ui.main_window import MainWindow


def test_material_vertical_27k_no_preselecciona_y_pide_elegir(qtbot):
    cuadro = DialogoFormatoSecuencia(None)
    qtbot.addWidget(cuadro)
    radios = {radio.text(): radio for radio in cuadro.findChildren(QRadioButton)}
    exportar = next(b for b in cuadro.findChildren(QPushButton)
                    if b.text() == "Exportar JSON")

    assert set(radios) == {"4K 9:16", "2.7K 9:16", "4K 16:9"}
    assert not any(radio.isChecked() for radio in radios.values())
    assert not exportar.isEnabled()

    fila = next(f for f in cuadro.findChildren(QFrame)
                if radios["2.7K 9:16"].parent() is f)
    qtbot.mouseClick(fila, Qt.LeftButton, pos=QPoint(fila.width() - 20, fila.height() // 2))
    assert exportar.isEnabled()
    assert cuadro.formato_elegido == "2.7K 9:16"


def test_la_sugerencia_se_ve_seleccionada_y_se_puede_cambiar(qtbot):
    cuadro = DialogoFormatoSecuencia("4K 16:9")
    qtbot.addWidget(cuadro)
    radios = {radio.text(): radio for radio in cuadro.findChildren(QRadioButton)}

    assert radios["4K 16:9"].isChecked()
    assert cuadro.formato_elegido == "4K 16:9"
    radios["4K 9:16"].click()
    assert cuadro.formato_elegido == "4K 9:16"
    assert "1080p" in " ".join(label.text() for label in cuadro.findChildren(QLabel))


def test_exportacion_usa_la_eleccion_del_dialogo(qtbot, monkeypatch):
    anfitrion = QWidget()
    qtbot.addWidget(anfitrion)
    anfitrion.clips = [object()]
    anfitrion._clip_sizes = {0: (3840, 2160)}
    monkeypatch.setattr(DialogoFormatoSecuencia, "exec", lambda self: QDialog.Accepted)

    assert MainWindow._elegir_formato_de_secuencia(anfitrion) == "4K 16:9"
