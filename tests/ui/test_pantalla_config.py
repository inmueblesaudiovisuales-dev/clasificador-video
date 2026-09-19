"""La pantalla de configuración: la llave de la guía y el modo económico."""
from PySide6.QtWidgets import QFileDialog
import pytest
from clasificador_video.ui.pantalla_config import PantallaConfig


def _pantalla(qtbot, llave="", modo_economico=False) -> PantallaConfig:
    p = PantallaConfig()
    qtbot.addWidget(p)
    p.resize(520, 300)
    p.cargar(llave, modo_economico)
    return p


@pytest.fixture
def config_screen(qtbot):
    return _pantalla(qtbot)


def test_sin_llave_lo_dice_y_no_hay_nada_que_quitar(qtbot):
    p = _pantalla(qtbot)
    assert "falta" in p.estado_label.text().lower()
    assert not p.quitar_button.isEnabled()


def test_con_llave_la_ensena_TAPADA(qtbot):
    # Alguien puede estar viendo la pantalla de Bruno, o puede acabar en una
    # captura: nunca se ensena entera.
    p = _pantalla(qtbot, "sk-123456789abcd")
    texto = p.estado_label.text()
    assert "abcd" in texto
    assert "sk-123456789abcd" not in texto
    assert p.quitar_button.isEnabled()


def test_la_caja_nace_vacia_aunque_ya_haya_llave(qtbot):
    # No se precarga la llave en la caja: seria ensenarla entera, que es
    # justo lo que `tapada` existe para evitar.
    p = _pantalla(qtbot, "sk-123456789abcd")
    assert p.caja_llave.text() == ""


def test_guardar_emite_la_llave_y_limpia_la_caja(qtbot):
    p = _pantalla(qtbot)
    p.caja_llave.setText("  sk-nueva-999999  ")
    with qtbot.waitSignal(p.llave_guardada) as blocker:
        p.guardar_button.click()
    # Sin espacios: un espacio pegado al copiar tumbaba la llamada con un
    # «la llave no sirve» que no decia por que.
    assert blocker.args[0] == "sk-nueva-999999"
    assert p.caja_llave.text() == ""


def test_guardar_con_la_caja_vacia_no_hace_nada(qtbot):
    # Apretar Guardar sin escribir nada NO debe borrar la que ya esta.
    p = _pantalla(qtbot, "sk-123456789abcd")
    p.guardar_button.click()
    assert "abcd" in p.estado_label.text()


def test_quitar_emite_y_deja_la_pantalla_sin_llave(qtbot):
    p = _pantalla(qtbot, "sk-123456789abcd")
    with qtbot.waitSignal(p.llave_borrada):
        p.quitar_button.click()
    assert "falta" in p.estado_label.text().lower()
    assert not p.quitar_button.isEnabled()


def test_la_pantalla_dice_donde_se_guarda(qtbot):
    # Es la pregunta que sigue a «pégala aquí»: ¿a dónde se va esto?
    p = _pantalla(qtbot)
    assert ".clasificador_video" in p.donde_label.text()


def test_la_llave_no_se_ve_mientras_se_escribe(qtbot):
    from PySide6.QtWidgets import QLineEdit

    p = _pantalla(qtbot)
    assert p.caja_llave.echoMode() == QLineEdit.EchoMode.Password


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
    p.cargar("", True)
    assert not disparo
    assert p.economico_check.isChecked()


def test_elegir_carpeta_premiere_emite_la_señal(config_screen, monkeypatch, tmp_path):
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path)))

    recibido = []
    config_screen.carpeta_premiere_guardada.connect(recibido.append)
    config_screen.carpeta_premiere_button.click()

    assert recibido == [tmp_path]
