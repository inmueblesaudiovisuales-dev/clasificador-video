# tests/test_app.py
import json

from PySide6.QtWidgets import QDialog, QMessageBox

from clasificador_video import app as app_module
from clasificador_video.ui.room_config_dialog import RoomConfigDialog


class _FakeMpv:
    """Evita abrir un mpv real en pruebas que no verifican video.

    MpvPlayer crea el reproductor en el constructor (ya no al mostrarse el
    widget), y VideoWidget.player lo crea perezosamente al primer acceso.
    `arrancar()` accede a `video_widget.open_clip(...)` al restaurar una
    sesion con clips -- sin este doble, cada prueba de app.py abriria un
    mpv real y su hilo de eventos, acumulando hilos reales entre pruebas
    hasta comprometer el proceso (crash nativo documentado en el handoff).
    """

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.pause = True
        self.time_pos = 0.0

    def play(self, path):
        pass


def test_arrancar_abre_dialogo_y_construye_ventana_con_cuartos_elegidos(qtbot, monkeypatch):
    def fake_dialog(*args, **kwargs):
        d = RoomConfigDialog(*args, **kwargs)
        d.selection.toggle("Sala")
        d.selection.toggle("Recámara")
        d.selection.set_count("Recámara", 2)
        return d

    monkeypatch.setattr(app_module, "RoomConfigDialog", fake_dialog)
    monkeypatch.setattr(RoomConfigDialog, "exec", lambda self: QDialog.Accepted)

    window = app_module.arrancar(video_factory=_FakeMpv)
    assert window is not None
    assert window.room_list_widget.count() == 3  # Sala, Recámara 1, Recámara 2


def test_arrancar_cancelado_devuelve_none(qtbot, monkeypatch):
    monkeypatch.setattr(RoomConfigDialog, "exec", lambda self: QDialog.Rejected)
    assert app_module.arrancar(video_factory=_FakeMpv) is None


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
    window = app_module.arrancar(video_factory=_FakeMpv, session_path=session)
    assert window is not None
    assert window.clips[0].ruta.name == "a.MP4"


def test_arrancar_restaura_sesion_tambien_programa_miniaturas(qtbot, monkeypatch, tmp_path):
    """Bug real encontrado en uso: restaurar sesion cargaba los clips pero
    nunca llamaba a _schedule_thumbnails, dejando el filmstrip sin
    miniaturas hasta la siguiente importacion manual."""
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
    window = app_module.arrancar(video_factory=_FakeMpv, session_path=session)
    assert window is not None
    assert window._thumb_generation == 1
    assert window._thumb_dir is not None


def test_main_aplica_el_stylesheet_global(qtbot, monkeypatch):
    from PySide6.QtWidgets import QApplication

    QApplication.instance().setStyleSheet("")

    class _Window:
        clips: list = []
        video_widget = None

        def show(self):
            pass

    mock_window = _Window()
    monkeypatch.setattr(app_module, "arrancar", lambda **kw: mock_window)
    monkeypatch.setattr(app_module.QApplication, "exec", lambda self: 0)
    monkeypatch.setattr(app_module.sys, "exit", lambda code=0: None)

    app_module.main()

    app = QApplication.instance()
    assert "background-color: #08080a" in app.styleSheet()
