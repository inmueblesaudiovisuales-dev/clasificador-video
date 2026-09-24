"""La app de Portafolio abre su propia ventana, separada de MainWindow
del Clipify normal -- spec 2026-09-24-modo-portafolio-design.md."""
from clasificador_video_portafolio.app import VentanaPortafolio


def test_la_ventana_de_portafolio_no_es_la_del_clipify_normal(qtbot):
    from clasificador_video.ui.main_window import MainWindow

    ventana = VentanaPortafolio()
    qtbot.addWidget(ventana)

    assert not isinstance(ventana, MainWindow)
    assert ventana.windowTitle().startswith("Clipify Portafolio")


def test_la_ventana_arranca_en_el_modulo_importar(qtbot):
    ventana = VentanaPortafolio()
    qtbot.addWidget(ventana)

    assert ventana.modulo_actual == "importar"


def test_el_switcher_muestra_revisar_y_arma_sin_funcionalidad(qtbot):
    ventana = VentanaPortafolio()
    qtbot.addWidget(ventana)

    ventana.mostrar_modulo("revisar")

    assert ventana.modulo_actual == "revisar"
    assert ventana.modulos.currentWidget() is ventana.pantalla_revisar

    ventana.mostrar_modulo("armar")

    assert ventana.modulo_actual == "armar"
    assert ventana.modulos.currentWidget() is ventana.pantalla_armar
