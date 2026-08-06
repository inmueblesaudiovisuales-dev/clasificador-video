from clasificador_video.ui.theme import BG_WINDOW, BG_PANEL, ACCENT, build_stylesheet


def test_build_stylesheet_incluye_el_fondo_oscuro_de_la_ventana():
    qss = build_stylesheet()
    assert f"background-color: {BG_WINDOW}" in qss


def test_build_stylesheet_estiliza_los_paneles():
    qss = build_stylesheet()
    assert f"background-color: {BG_PANEL}" in qss


def test_build_stylesheet_da_estilo_al_boton_principal():
    qss = build_stylesheet()
    assert "QPushButton#startButton" in qss
    assert "QPushButton#exportButton" in qss
    assert ACCENT in qss


def test_build_stylesheet_da_fondo_negro_al_video():
    qss = build_stylesheet()
    assert "QWidget#videoWidget" in qss
    assert "background-color: black" in qss


def test_build_stylesheet_da_fondo_distinto_al_boton_importar():
    """Bug real de v1: el boton 'Importar carpetas...' usaba el mismo
    color de fondo que el panel donde vive y era invisible como boton.
    """
    qss = build_stylesheet()
    assert "QPushButton#importButton" in qss


def test_build_stylesheet_es_una_sola_cadena_no_vacia():
    qss = build_stylesheet()
    assert isinstance(qss, str)
    assert len(qss) > 100
