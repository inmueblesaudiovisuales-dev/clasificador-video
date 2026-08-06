# tests/test_app.py
from PySide6.QtWidgets import QDialog

from clasificador_video import app as app_module
from clasificador_video.ui.room_config_dialog import RoomConfigDialog


def test_arrancar_abre_dialogo_y_construye_ventana_con_cuartos_elegidos(qtbot, monkeypatch):
    def fake_dialog(*args, **kwargs):
        d = RoomConfigDialog(*args, **kwargs)
        d.selection.toggle("Sala")
        d.selection.toggle("Recámara")
        d.selection.set_count("Recámara", 2)
        return d

    monkeypatch.setattr(app_module, "RoomConfigDialog", fake_dialog)
    monkeypatch.setattr(RoomConfigDialog, "exec", lambda self: QDialog.Accepted)

    window = app_module.arrancar(video_factory=None)
    assert window is not None
    assert window.room_list_widget.count() == 3  # Sala, Recámara 1, Recámara 2


def test_arrancar_cancelado_devuelve_none(qtbot, monkeypatch):
    monkeypatch.setattr(RoomConfigDialog, "exec", lambda self: QDialog.Rejected)
    assert app_module.arrancar(video_factory=None) is None
