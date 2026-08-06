# tests/ui/test_room_config_dialog.py
from clasificador_video.rooms import MASTER_ROOM_LIST
from clasificador_video.ui.room_config_dialog import RoomConfigDialog


def test_dialog_muestra_un_chip_por_cada_cuarto_maestro(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    assert len(dialog.chip_buttons) == len(MASTER_ROOM_LIST)


def test_click_en_un_chip_lo_activa_y_actualiza_la_seleccion(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    dialog.chip_buttons["Cocina"].click()
    assert dialog.selection.active_rooms() == ["Cocina"]


def test_agregar_cuarto_personalizado_lo_mete_a_la_seleccion(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    dialog.custom_room_input.setText("Bodega")
    dialog.add_custom_button.click()
    assert "Bodega" in dialog.selection.active_rooms()


def test_boton_de_empezar_tiene_objectname_de_boton_principal(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    assert dialog.start_button.objectName() == "startButton"


def test_chip_se_marca_checked_al_hacer_click(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    dialog.chip_buttons["Cocina"].click()
    assert dialog.chip_buttons["Cocina"].isChecked() is True
