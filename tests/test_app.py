# tests/test_app.py
#
# Este archivo estuvo EXCLUIDO de la corrida durante meses por un cuelgue
# bajo `offscreen`. **Ya no cuelga**: la F3 lo reescribió —el diálogo de
# configuración de cuartos, que abría con `exec()` y bloqueaba, murió con
# ella— y desde entonces corre en medio segundo. Comprobado con cinco
# corridas de la suite completa el 2026-08-08.
#
#     QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
#
# Si alguna vez vuelve a colgarse, es un bug a resolver, no una limitación a
# esquivar. Cubre el arranque de la app, que ningún otro test toca.
import json

from PySide6.QtWidgets import QMessageBox

from clasificador_video import app as app_module
from clasificador_video.ui import theme


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


def _sesion(tmp_path, categoria_path=None, extra=None):
    session = tmp_path / "sesion.json"
    data = {
        "proyecto": "Casa",
        "rooms": ["Sala"],
        "clips": [{
            "orden": 1, "ruta": "/a.MP4", "fps": 30.0,
            "categoria_path": categoria_path if categoria_path is not None else [],
            "in_frame": None, "out_frame": None, "flag": "none", "ruta_proxy": None,
        }],
    }
    data.update(extra or {})
    session.write_text(json.dumps(data))
    return session


# --- F3: se abre directo, sin configurar nada ------------------------------


def test_arrancar_abre_directo_y_con_el_rail_vacio(qtbot, tmp_path):
    """No hay paso previo de 'elige los cuartos': la app abre lista para
    trabajar y los cuartos se crean sobre la marcha (DECISIONES.md)."""
    window = app_module.arrancar(
        video_factory=_FakeMpv, session_path=tmp_path / "sesion.json"
    )
    assert window is not None
    assert window.room_selection.active_rooms() == []
    assert window.room_rail.rows == []


def test_arrancar_ya_no_puede_devolver_none(qtbot, tmp_path):
    """Antes devolvia None si el usuario cancelaba el dialogo. Sin dialogo
    no hay nada que cancelar, y `main()` ya no comprueba el caso."""
    assert app_module.arrancar(
        video_factory=_FakeMpv, session_path=tmp_path / "x.json"
    ) is not None


def test_el_dialogo_de_configuracion_ya_no_existe():
    assert not hasattr(app_module, "RoomConfigDialog")


# --- sesiones guardadas -----------------------------------------------------


def test_arrancar_restaura_sesion_si_existe_y_el_usuario_acepta(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    window = app_module.arrancar(video_factory=_FakeMpv, session_path=_sesion(tmp_path))
    assert window.clips[0].ruta.name == "a.MP4"
    assert window.room_selection.active_rooms() == ["Sala"]


def test_arrancar_restaura_sesion_tambien_programa_miniaturas(qtbot, monkeypatch, tmp_path):
    """Bug real encontrado en uso: restaurar sesion cargaba los clips pero
    nunca llamaba a _schedule_thumbnails, dejando la hoja de contactos sin
    miniaturas hasta la siguiente importacion manual."""
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    window = app_module.arrancar(video_factory=_FakeMpv, session_path=_sesion(tmp_path))
    assert window._thumb_generation == 1


def test_una_sesion_vieja_con_subcuartos_se_aplana_al_cuarto_padre(tmp_path):
    """Se conserva el cuarto, que sigue existiendo; se descarta el subcuarto,
    que ya no es representable. Tirar el clip entero seria peor: el editor ya
    tomo esa decision."""
    clip = app_module._clip_from_dict({
        "orden": 1, "ruta": "/x.MP4", "fps": 30.0,
        "categoria_path": ["Recámara 1", "Baño"],
    })
    assert clip.categoria_path == ["Recámara 1"]


def test_una_sesion_vieja_con_arbol_de_subcuartos_se_carga_igual(qtbot, monkeypatch, tmp_path):
    """`category_tree` ya no se escribe, pero una sesion anterior a la F3 lo
    trae: se ignora en vez de reventar."""
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    session = _sesion(tmp_path, extra={"category_tree": {"Recámara 1": ["Baño"]}})
    window = app_module.arrancar(video_factory=_FakeMpv, session_path=session)
    assert window.clips[0].ruta.name == "a.MP4"
    assert not hasattr(window, "category_tree")


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
    # el color exacto sale del tema, no se escribe a mano: si se fija un
    # hexadecimal aqui, la asercion queda obsoleta en silencio (paso: este
    # test afirmaba #08080a, un color que ya no existia en theme.py).
    assert f"background-color: {theme.BG_APP}" in app.styleSheet()
