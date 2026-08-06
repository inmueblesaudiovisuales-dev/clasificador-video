# tests/test_app.py
import json

from PySide6.QtWidgets import QDialog, QMessageBox

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


def test_arrancar_restaura_sesion_si_existe_y_el_usuario_acepta(qtbot, monkeypatch, tmp_path):
    session = tmp_path / "sesion.json"
    session.write_text(json.dumps({
        "proyecto": "Casa",
        "rooms": ["Sala"],
        "clips": [{"orden": 1, "ruta": "/a.MP4", "categoria_path": [], "fps": 30.0,
                   "in_frame": None, "out_frame": None, "flag": "none", "ruta_proxy": None}],
        "category_tree": {},
    }))
    monkeypatch.setattr(RoomConfigDialog, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    window = app_module.arrancar(video_factory=None, session_path=session)
    assert window is not None
    assert window.clips[0].ruta.name == "a.MP4"
