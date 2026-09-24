"""La pantalla de configuración: modos de miniaturas y carpetas."""
from PySide6.QtWidgets import QFileDialog
import pytest
from clasificador_video.ui.pantalla_config import PantallaConfig


def _pantalla(qtbot, modo_economico=False, modo_rapido=False) -> PantallaConfig:
    p = PantallaConfig()
    qtbot.addWidget(p)
    p.resize(520, 300)
    p.cargar(modo_economico, modo_rapido)
    return p


@pytest.fixture
def config_screen(qtbot):
    return _pantalla(qtbot)


def test_la_configuracion_ya_no_tiene_caja_de_llave(qtbot):
    # La guía se clasifica por palabras: no hay llave que poner, así que la
    # caja y sus señales desaparecieron por completo (handoff 2026-09-24).
    p = _pantalla(qtbot)
    assert not hasattr(p, "caja_llave")
    assert not hasattr(p, "llave_guardada")
    assert not hasattr(p, "llave_borrada")


def test_la_configuracion_ya_no_tiene_conexion_de_drive(qtbot):
    p = _pantalla(qtbot)

    assert not hasattr(p, "drive_button")
    assert not hasattr(p, "drive_label")
    assert not hasattr(p, "drive_conectado")
    assert not hasattr(p, "drive_estado_cambiado")


def test_la_configuracion_ya_no_tiene_carpeta_de_proyectos_premiere(qtbot):
    p = _pantalla(qtbot)

    assert not hasattr(p, "carpeta_premiere_label")
    assert not hasattr(p, "carpeta_premiere_button")
    assert not hasattr(p, "carpeta_premiere_guardada")


def test_el_modo_economico_nace_apagado_por_default(qtbot):
    p = _pantalla(qtbot)
    assert not p.economico_check.isChecked()


def test_cargar_refleja_el_modo_economico_guardado(qtbot):
    p = _pantalla(qtbot, modo_economico=True)
    assert p.economico_check.isChecked()


def test_marcar_el_check_emite_true(qtbot):
    p = _pantalla(qtbot)
    with qtbot.waitSignal(p.modo_economico_cambiado) as blocker:
        p.economico_check.setChecked(True)
    assert blocker.args[0] is True


def test_desmarcar_el_check_emite_false(qtbot):
    p = _pantalla(qtbot, modo_economico=True)
    with qtbot.waitSignal(p.modo_economico_cambiado) as blocker:
        p.economico_check.setChecked(False)
    assert blocker.args[0] is False


def test_cargar_no_reemite_la_señal_al_solo_reflejar_lo_guardado(qtbot):
    # `cargar` pone el check para mostrar lo que ya está guardado -- eso no
    # es que Bruno haya tocado el checkbox, y no debe volver a escribir el
    # mismo valor que se acaba de leer.
    p = _pantalla(qtbot)
    disparo = False

    def _marcar(_valor):
        nonlocal disparo
        disparo = True

    p.modo_economico_cambiado.connect(_marcar)
    p.cargar(True)
    assert not disparo
    assert p.economico_check.isChecked()


def test_el_modo_rapido_nace_apagado_por_default(qtbot):
    p = _pantalla(qtbot)
    assert not p.rapido_check.isChecked()


def test_cargar_refleja_el_modo_rapido_guardado(qtbot):
    p = _pantalla(qtbot, modo_rapido=True)
    assert p.rapido_check.isChecked()


def test_marcar_el_check_rapido_emite_true(qtbot):
    p = _pantalla(qtbot)
    with qtbot.waitSignal(p.modo_rapido_cambiado) as blocker:
        p.rapido_check.setChecked(True)
    assert blocker.args[0] is True


def test_desmarcar_el_check_rapido_emite_false(qtbot):
    p = _pantalla(qtbot, modo_rapido=True)
    with qtbot.waitSignal(p.modo_rapido_cambiado) as blocker:
        p.rapido_check.setChecked(False)
    assert blocker.args[0] is False


def test_cargar_no_reemite_la_señal_de_rapido_al_solo_reflejar_lo_guardado(qtbot):
    p = _pantalla(qtbot)
    disparo = False

    def _marcar(_valor):
        nonlocal disparo
        disparo = True

    p.modo_rapido_cambiado.connect(_marcar)
    p.cargar(False, True)
    assert not disparo
    assert p.rapido_check.isChecked()


def test_economico_y_rapido_son_independientes(qtbot):
    p = _pantalla(qtbot, modo_economico=True, modo_rapido=False)
    assert p.economico_check.isChecked()
    assert not p.rapido_check.isChecked()


def test_elegir_carpeta_icloud_emite_la_señal(config_screen, monkeypatch, tmp_path):
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path)))

    recibido = []
    config_screen.carpeta_icloud_guardada.connect(recibido.append)
    config_screen.carpeta_icloud_button.click()

    assert recibido == [tmp_path]


# --- miniaturas guardadas: peso y borrado -------------------------------


def test_mostrar_peso_lo_escribe_en_palabras(config_screen):
    config_screen.mostrar_peso_de_miniaturas(1_500_000_000)
    assert "1.4 GB" in config_screen.miniaturas_peso_label.text()


def test_sin_nada_que_borrar_el_boton_se_deshabilita(config_screen):
    config_screen.mostrar_peso_de_miniaturas(0)
    assert not config_screen.miniaturas_borrar_button.isEnabled()


def test_con_algo_que_borrar_el_boton_se_habilita(config_screen):
    config_screen.mostrar_peso_de_miniaturas(1024)
    assert config_screen.miniaturas_borrar_button.isEnabled()


def test_el_boton_de_borrar_emite_la_señal(config_screen):
    disparo = []
    config_screen.miniaturas_borrar_pedido.connect(lambda: disparo.append(1))
    config_screen.mostrar_peso_de_miniaturas(1024)

    config_screen.miniaturas_borrar_button.click()

    assert disparo == [1]
