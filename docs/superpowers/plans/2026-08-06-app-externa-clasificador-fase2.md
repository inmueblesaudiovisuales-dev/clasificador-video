# App Externa del Clasificador de Video — Fase 2: flujo funcional completo — 2026-08-06

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the Phase 1 foundation (pure logic + thin UI shell, all tested, 95 tests green) into a usable app: the user opens it, configures rooms, imports real folders of footage, sees embedded video playback, classifies with the keyboard, and exports the manifest the UXP plugin consumes. End state: a real shooting classified end-to-end with nothing but this window.

**This plan does not touch** the manifest format (§11 of the 2026-08-05 spec — fixed by the plugin, verified again in analysis: the plugin reads `clips[]`, and per clip `ruta`, `categoria_path`, `flag`, `in_frame`, `out_frame`, `fps`, `ruta_proxy`; `categoria_path: []` lands in a bin named "Sin clasificar"; in/out applies only when both frames are non-null).

**Phase 1 produced** (reused as-is): `manifest.py` (Clip/Manifest + write_json), `autosave.py`, `rooms.py`, `category_path.py`, `ingest.py` (IngestTree), `proxy_match.py` (match_proxies), `thumbnails.py` (extract_thumbnail), `player.py` (MpvPlayer), `keyboard.py` (KeyboardRouter), `probe.py` (probe_clip → fps/duration/rotation — original, reusable per its README), and `ui/` (RoomConfigDialog, Filmstrip, MainWindow, app.py).

**Risks already validated live on 2026-08-06 (do not re-litigate, but use in Tasks 1-3):**
- **mpv embeds inside a PySide6 widget on macOS via `wid`.** Spike run today: `mpv.MPV(wid=int(widget.winId()), hwdec="videotoolbox")` against `TEST/20260804_PIB0589.MP4` played embedded (time_pos advanced past 2.3s while the widget was visible). `winId()` must be called while the widget is shown.
- Thumbnails via `mpv --vo=image` work and respect rotation (Task 8 of Phase 1, smoke-tested: 1.1 MB jpg from `TEST/20260804_PIB0589.MP4` at second 3.0).
- `TEST/` clips are 2-6 s test clips, not real shoots. Always check real duration (`ffprobe -show_entries format=duration`) before extracting frames.

**Tech notes for this phase:**
- `python-mpv` with `wid=` renders into the widget's native surface; no render-API/ctypes needed (validated above). On non-macOS platforms `wid` also works (X11/Win32); the plan targets Bruno's Mac.
- Background work (thumbnails, probes) must not freeze the UI: `QThreadPool` + `QRunnable` with signals, or `QTimer`-driven batches. mpv's own playback thread is internal to libmpv and does not block the UI.
- Every action that changes classification state triggers autosave (§10 spec): room assignment, pick/reject, in/out, navigation. Cheap JSON write, atomic via existing `save_session`.
- Tests stay pure-logic-first; widgets stay thin and smoke-tested with pytest-qt `qtbot`. Real mpv is never instantiated in unit tests — the `MpvPlayer` factory pattern from Phase 1 continues.

---

## Milestone 1 — Reproducción embebida (video visible en la ventana)

### Task 1: `MpvPlayer` gains optional `wid` embedding + `toggle`; `VideoWidget` plays a clip inside a QWidget

**Files:**
- Modify: `src/clasificador_video/player.py`
- Create: `src/clasificador_video/ui/video_widget.py`
- Test: `tests/test_player.py`, `tests/ui/test_video_widget.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/test_player.py
def test_mpv_player_recibe_wid_cuando_se_pasa():
    player = MpvPlayer(mpv_factory=FakeMpv, wid=12345)
    assert player._mpv.init_kwargs["wid"] == 12345

def test_mpv_player_sin_wid_no_lo_pasa():
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert "wid" not in player._mpv.init_kwargs

def test_toggle_alterna_play_y_pause():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.toggle()          # empieza en pause=True (FakeMpv)
    assert player._mpv.pause is False
    player.toggle()
    assert player._mpv.pause is True
```

```python
# tests/ui/test_video_widget.py
from pathlib import Path

from clasificador_video.player import MpvPlayer
from clasificador_video.ui.video_widget import VideoWidget


class FakeMpv:
    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0
        self.vid_scale = None
        self.commands = []

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        self.commands.append(args)


def test_video_widget_crea_un_player_con_wid_del_widget(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    widget.show()
    assert widget.player._mpv.init_kwargs["hwdec"] == "videotoolbox"
    assert widget.player._mpv.init_kwargs["wid"] == int(widget.winId())


def test_open_carga_el_clip_en_el_player(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    widget.open_clip(Path("/shooting/C0012.MP4"))
    assert widget.player._mpv.loaded_path == "/shooting/C0012.MP4"


def test_play_pause_toggle_se_reenvia_al_player(qtbot):
    widget = VideoWidget(mpv_factory=FakeMpv)
    qtbot.addWidget(widget)
    widget.toggle_play()
    assert widget.player._mpv.pause is False
    widget.toggle_play()
    assert widget.player._mpv.pause is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_player.py tests/ui/test_video_widget.py -v`
Expected: FAIL — `MpvPlayer` does not accept `wid`; `clasificador_video.ui.video_widget` does not exist.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/player.py — changes only
    def __init__(self, mpv_factory: Callable[..., object], wid: int | None = None):
        kwargs: dict = {"hwdec": "videotoolbox"}
        if wid is not None:
            kwargs["wid"] = wid
        self._mpv = mpv_factory(**kwargs)
        self.in_frame: int | None = None
        self.out_frame: int | None = None

    def toggle(self) -> None:
        if self._mpv.pause:
            self.play()
        else:
            self.pause()
```

```python
# src/clasificador_video/ui/video_widget.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QWidget

from clasificador_video.player import MpvPlayer


class VideoWidget(QWidget):
    """Widget que embebe libmpv via `wid` (validado en vivo el 2026-08-06
    en macOS: mpv dibuja dentro del NSView del widget). El player se crea
    con el wid del widget ya mostrado -- winId() no es valido antes.
    """

    def __init__(self, mpv_factory: Callable[..., object], parent=None):
        super().__init__(parent)
        self._mpv_factory = mpv_factory
        self._player: MpvPlayer | None = None

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._player is None:
            self._player = MpvPlayer(mpv_factory=self._mpv_factory, wid=int(self.winId()))

    @property
    def player(self) -> MpvPlayer:
        if self._player is None:
            raise RuntimeError("el VideoWidget debe mostrarse antes de usar su player")
        return self._player

    def open_clip(self, path: Path) -> None:
        self.player.open(path)

    def toggle_play(self) -> None:
        self.player.toggle()
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_player.py tests/ui/test_video_widget.py -v`
Expected: 5 new tests pass, existing player tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/player.py src/clasificador_video/ui/video_widget.py tests/test_player.py tests/ui/test_video_widget.py
git commit -m "feat: reproductor embebido en widget via wid de mpv"
```

### Task 2: MainWindow gets the VideoWidget centered + quality selector + legend

The window now matches app-externa spec §3 (option B chosen): player center, rooms column left, filmstrip bottom, quality selector in a top bar, keyboard legend always visible.

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
from clasificador_video.player import QUALITY_PROFILES
from clasificador_video.ui.video_widget import VideoWidget


class FakeMpvForWindow:
    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0
        self.vid_scale = None
        self.commands = []

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        self.commands.append(args)


def _window_with_video(qtbot) -> MainWindow:
    selection = RoomSelection()
    selection.toggle("Sala")
    window = MainWindow(
        project_name="Casa Jardin",
        room_selection=selection,
        category_tree=CategoryTree(),
        video_factory=FakeMpvForWindow,
    )
    qtbot.addWidget(window)
    return window


def test_ventana_tiene_reproductor_embebido_y_selector_de_calidad(qtbot):
    window = _window_with_video(qtbot)
    assert isinstance(window.video_widget, VideoWidget)
    assert window.quality_combo.count() == len(QUALITY_PROFILES)


def test_cambiar_calidad_aplica_el_perfil(qtbot):
    window = _window_with_video(qtbot)
    window.quality_combo.setCurrentText("1/2")
    assert window.video_widget.player._mpv.vid_scale == QUALITY_PROFILES["1/2"]


def test_ventana_muestra_leyenda_de_teclado(qtbot):
    window = _window_with_video(qtbot)
    assert "Espacio" in window.legend_label.text()
    assert "P/X/U" in window.legend_label.text()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — `MainWindow` has no `video_widget`, `quality_combo`, `legend_label`, and its `__init__` does not accept `video_factory`.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — changes
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QListWidget, QVBoxLayout, QWidget

from clasificador_video.player import QUALITY_PROFILES
from clasificador_video.ui.video_widget import VideoWidget

LEGEND_TEXT = (
    "1-9 cuartos  |  Espacio play/pause  |  I/O in/out  |  P pick / X reject / U ninguno  "
    "|  ← → clip anterior/siguiente  |  Ctrl+Z deshacer"
)

class MainWindow(QWidget):
    def __init__(self, project_name, room_selection, category_tree, video_factory=None, parent=None):
        # ...existing setup...
        self.video_widget = VideoWidget(mpv_factory=video_factory) if video_factory else VideoWidget()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(list(QUALITY_PROFILES))
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        self.legend_label = QLabel(LEGEND_TEXT)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Calidad:"))
        top_bar.addWidget(self.quality_combo)
        top_bar.addStretch(1)

        center = QHBoxLayout()
        center.addWidget(self.room_list_widget, stretch=0)
        center.addWidget(self.video_widget, stretch=1)

        root = QVBoxLayout(self)
        root.addLayout(top_bar)
        root.addLayout(center, stretch=1)
        root.addWidget(self.filmstrip, stretch=0)
        root.addWidget(self.legend_label, stretch=0)

    def _on_quality_changed(self, profile_name: str) -> None:
        try:
            self.video_widget.player.set_quality(profile_name)
        except RuntimeError:
            pass  # el player aun no se creo (widget no mostrado); se aplica al abrir
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass (old + new).

- [ ] **Step 5: Manual smoke test — embedded video plays in the window**

Run:
```bash
PYTHONPATH=src .venv/bin/python -c "
import sys
from pathlib import Path
import mpv as real_mpv
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from clasificador_video.rooms import RoomSelection
from clasificador_video.category_path import CategoryTree
from clasificador_video.ui.main_window import MainWindow
from clasificador_video.manifest import Clip

app = QApplication(sys.argv)
sel = RoomSelection(); sel.toggle('Sala')
w = MainWindow('Casa Jardin', sel, CategoryTree(), video_factory=lambda **kw: real_mpv.MPV(**kw))
w.resize(1100, 700); w.show()
w.load_clips([Clip(orden=1, ruta=Path('TEST/20260804_PIB0589.MP4'), categoria_path=[], fps=59.94)])
w.video_widget.open_clip(Path('TEST/20260804_PIB0589.MP4'))
w.video_widget.toggle_play()
def check():
    print('time_pos:', w.video_widget.player._mpv.time_pos)
    app.quit()
QTimer.singleShot(1500, check)
sys.exit(app.exec())
"
```
Expected: a window shows the test clip playing **inside** it; prints a `time_pos` > 0; no traceback.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: reproductor embebido al centro, selector de calidad y leyenda de teclado"
```

---

## Milestone 2 — Arranque real: cuartos configurados antes de clasificar

### Task 3: app entrypoint opens the room config dialog first and feeds the window

`RoomConfigDialog` exists (Phase 1) but nothing opens it. Now: on launch, dialog → if accepted, `MainWindow` with the real `RoomSelection` + `CategoryTree`; if cancelled, app exits quietly.

**Files:**
- Modify: `src/clasificador_video/app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app.py
from PySide6.QtWidgets import QDialog

from clasificador_video import app as app_module
from clasificador_video.rooms import MASTER_ROOM_LIST
from clasificador_video.ui.room_config_dialog import RoomConfigDialog


def test_arrancar_abre_dialogo_y_construye_ventana_con_cuartos_elegidos(qtbot, monkeypatch):
    created = {}

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
    created["window"] = window


def test_arrancar_cancelado_devuelve_none(qtbot, monkeypatch):
    monkeypatch.setattr(RoomConfigDialog, "exec", lambda self: QDialog.Rejected)
    assert app_module.arrancar(video_factory=None) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_app.py -v`
Expected: FAIL — no `tests/test_app.py`, `app_module.arrancar` does not exist.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/app.py — changes
def arrancar(video_factory=None) -> MainWindow | None:
    """Abre el dialogo de cuartos; si el usuario acepta, construye la
    ventana principal con esa seleccion. None si cancela.
    """
    dialog = RoomConfigDialog(project_name="Shooting sin nombre")
    if dialog.exec() != QDialog.Accepted:
        return None
    window = MainWindow(
        project_name="Shooting sin nombre",
        room_selection=dialog.selection,
        category_tree=CategoryTree(),
        video_factory=video_factory,
    )
    window.resize(1100, 700)
    return window


def main() -> None:
    app = QApplication(sys.argv)
    window = arrancar()
    if window is None:
        sys.exit(0)
    window.show()
    sys.exit(app.exec())
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_app.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "feat: al abrir se configuran cuartos y la ventana usa esa seleccion"
```

---

## Milestone 3 — Ingest real a la ventana

### Task 4: "Importar carpetas" button → IngestTree → folders visible in the room panel area

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_boton_importar_carpetas_existe(qtbot):
    window = _window_with_video(qtbot)
    assert window.import_button.text() == "Importar carpetas…"


def test_importar_carpetas_puebla_el_ingest_list(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    carpeta_a = tmp_path / "FX30"
    carpeta_a.mkdir()
    (carpeta_a / "C0001.MP4").touch()
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getExistingDirectory",
        lambda *a, **k: str(carpeta_a),
    )
    window.import_button.click()
    assert window.ingest_list.count() == 1
    assert window.ingest_list.item(0).text() == "FX30"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — no `import_button`, no `ingest_list`.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
from clasificador_video.ingest import IngestTree

# in __init__:
        self.ingest_tree = IngestTree()
        self.import_button = QPushButton("Importar carpetas…")
        self.import_button.clicked.connect(self._on_import_folders)
        self.ingest_list = QListWidget()

# room column becomes a tab-less split: rooms on top, ingest below
        column = QVBoxLayout()
        column.addWidget(QLabel("Cuartos"))
        column.addWidget(self.room_list_widget, stretch=1)
        column.addWidget(self.import_button)
        column.addWidget(self.ingest_list, stretch=1)
        center.addLayout(column, stretch=0)
        # (remove the previous addWidget(room_list_widget))

    def _on_import_folders(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta de material")
        if not folder:
            return
        self.ingest_tree.import_folder(Path(folder))
        self._refresh_ingest_list()

    def _refresh_ingest_list(self) -> None:
        self.ingest_list.clear()
        for f in self.ingest_tree.top_level_folders():
            self.ingest_list.addItem(f.display_name)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: boton importar carpetas que llena el panel de ingest"
```

### Task 5: importing builds real `Clip`s (probe fps) and loads them into the window + real thumbnails in the filmstrip (background thread)

For each imported video: `probe_clip` (reused `probe.py`) for fps/duration, build `Clip(orden, ruta, categoria_path=[], fps)`, then `load_clips`. Thumbnails are extracted in a `QThreadPool` so the UI never freezes; each finished thumbnail lands in the matching filmstrip item.

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Modify: `src/clasificador_video/ui/filmstrip.py` (item exposes `set_pixmap`)
- Test: `tests/ui/test_main_window.py`, `tests/ui/test_filmstrip.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
class FakeProbe:
    def __init__(self):
        self.calls = []

    def __call__(self, path):
        self.calls.append(path)
        return {"width": 1920, "height": 1080, "fps": 59.94005994005994, "has_audio": True, "duration_frames": 360, "rotation": 0}


def test_importar_carpeta_construye_clips_con_fps_de_ffprobe(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "C0001.MP4").touch()
    fake_probe = FakeProbe()
    monkeypatch.setattr(window, "_probe_clip", fake_probe)
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    assert window.current_clip.fps == 59.94005994005994
    assert window.current_clip.ruta.name == "C0001.MP4"
    assert window.filmstrip.count() == 1


def test_load_clips_arranca_el_primer_clip_en_el_reproductor(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    assert window.video_widget.player._mpv.loaded_path == "/a.MP4"
```

```python
# additions to tests/ui/test_filmstrip.py
def test_item_puede_recibir_un_pixmap(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    from PySide6.QtGui import QPixmap
    pm = QPixmap(10, 10)
    pm.fill()
    strip.item_widgets[0].set_pixmap(pm)
    assert strip.item_widgets[0].has_pixmap()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py tests/ui/test_filmstrip.py -v`
Expected: FAIL — `_load_clips_from_ingest` does not exist; loading clips does not open the player; `set_pixmap` missing.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/filmstrip.py — changes
# _ClipItemWidget keeps an image_label reference and offers:
    def set_pixmap(self, pixmap) -> None:
        self._image_label.setPixmap(pixmap)

    def has_pixmap(self) -> bool:
        return self._image_label.pixmap() is not None

# (replace the ephemeral `image_label` local with self._image_label)
```

```python
# src/clasificador_video/ui/main_window.py — additions
from PySide6.QtCore import QRunnable, Signal, QThreadPool

from clasificador_video.probe import probe_clip
from clasificador_video.thumbnails import extract_thumbnail


class _ThumbnailJob(QRunnable):
    """Extrae la miniatura de un clip fuera del hilo de la UI."""

    class Signals(QWidget):
        done = Signal(int, object)  # indice, Path del jpg

    def __init__(self, index: int, video: Path, outdir: Path):
        super().__init__()
        self.index = index
        self.video = video
        self.outdir = outdir
        self.signals = _ThumbnailJob.Signals()

    def run(self) -> None:
        try:
            frame = extract_thumbnail(self.video, 0.5, self.outdir)
        except Exception:
            frame = None
        self.signals.done.emit(self.index, frame)


# MainWindow.__init__ additions:
        self._probe_clip = probe_clip          # inyectable para tests
        self._thread_pool = QThreadPool(self)
        self._thumb_dir = None                 # se fija por sesion de import

# new methods:
    def _load_clips_from_ingest(self) -> None:
        clips: list[Clip] = []
        orden = 1
        for folder in self.ingest_tree.top_level_folders():
            for video in folder.files:
                info = self._probe_clip(video)
                clips.append(Clip(orden=orden, ruta=video, categoria_path=[], fps=info["fps"]))
                orden += 1
        self.load_clips(clips)
        self._schedule_thumbnails()

    def _schedule_thumbnails(self) -> None:
        if not self.clips:
            return
        import tempfile
        self._thumb_dir = Path(tempfile.mkdtemp(prefix="clasificador-thumbs-"))
        for index, clip in enumerate(self.clips):
            job = _ThumbnailJob(index, clip.ruta, self._thumb_dir / str(index))
            job.signals.done.connect(self._on_thumbnail_ready)
            self._thread_pool.start(job)

    def _on_thumbnail_ready(self, index: int, frame: Path | None) -> None:
        if frame is None or index >= self.filmstrip.count():
            return
        self.filmstrip.item_widgets[index].set_pixmap(QPixmap(str(frame)))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py tests/ui/test_filmstrip.py -v`
Expected: all pass. (In the tests the thread pool jobs call the real `extract_thumbnail` against non-existent files and fail safely to `None` — acceptable in tests because `_on_thumbnail_ready` ignores `None`; do not let this mask failures: the smoke test below verifies the real path.)

- [ ] **Step 5: Manual smoke test — import the real TEST folder, see real thumbnails**

Run:
```bash
PYTHONPATH=src .venv/bin/python -c "
import sys, time
from pathlib import Path
import mpv as real_mpv
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from clasificador_video.rooms import RoomSelection
from clasificador_video.category_path import CategoryTree
from clasificador_video.ui.main_window import MainWindow

app = QApplication(sys.argv)
sel = RoomSelection(); sel.toggle('Sala')
w = MainWindow('T', sel, CategoryTree(), video_factory=lambda **kw: real_mpv.MPV(**kw))
w.resize(1100, 700); w.show()
w.ingest_tree.import_folder(Path('TEST'))
w._load_clips_from_ingest()
def check():
    print('clips:', w.filmstrip.count())
    print('thumbnails listos:', [it.has_pixmap() for it in w.filmstrip.item_widgets])
    print('reproduciendo:', w.video_widget.player._mpv.time_pos)
    app.quit()
QTimer.singleShot(4000, check)
sys.exit(app.exec())
"
```
Expected: prints `clips: 4` (the four MP4s in `TEST/`), at least the first thumbnails ready, and a `time_pos` advancing — real footage playing embedded with real thumbnails.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py src/clasificador_video/ui/filmstrip.py tests/ui/test_main_window.py tests/ui/test_filmstrip.py
git commit -m "feat: importar carpetas construye clips reales (ffprobe) y miniaturas en segundo plano"
```

### Task 6: keyboard control wired end-to-end: navigation arrows, space, P/X/U, I/O — and room keys with QShortcut

`handle_key_press` exists but nothing calls it. Now real shortcuts drive it; arrows and space drive the player; in/out goes through the player into the current clip.

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_flecha_derecha_avanza_al_siguiente_clip_y_lo_carga_en_el_player(qtbot):
    window = _window_with_video(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=30.0),
    ]
    window.load_clips(clips)
    window.handle_arrow("next")
    assert window.current_index == 1
    assert window.video_widget.player._mpv.loaded_path == "/b.MP4"


def test_tecla_i_marca_in_en_el_clip_actual_con_el_fps_del_clip(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_widget.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    assert window.current_clip.in_frame == 120


def test_tecla_o_marca_out(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_widget.player._mpv.time_pos = 5.0
    window.handle_key_press("o")
    assert window.current_clip.out_frame == 300


def test_tecla_u_limpia_in_out_del_clip(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_widget.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    window.handle_key_press("u")
    assert window.current_clip.in_frame is None
    assert window.current_clip.out_frame is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — no `handle_arrow`; `handle_key_press` does not handle i/o/u.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
    def handle_arrow(self, direction: str) -> None:
        if not self.clips:
            return
        if direction == "next":
            self.current_index = min(self.current_index + 1, len(self.clips) - 1)
        else:
            self.current_index = max(self.current_index - 1, 0)
        clip = self.current_clip
        if clip is not None:
            self.video_widget.open_clip(clip.ruta)
        self._refresh_filmstrip()

# extend handle_key_press:
    def handle_key_press(self, key: str) -> None:
        if self.current_clip is None:
            return
        if key == "i":
            self.current_clip.in_frame = self.video_widget.player.mark_in(self.current_clip.fps)
            self._refresh_filmstrip()
            return
        if key == "o":
            self.current_clip.out_frame = self.video_widget.player.mark_out(self.current_clip.fps)
            self._refresh_filmstrip()
            return
        if key == "u":
            self.current_clip.in_frame = None
            self.current_clip.out_frame = None
            self._refresh_filmstrip()
            return
        room_path = self._router.resolve_room_key(key)
        if room_path is not None:
            self.current_clip.categoria_path = room_path
            self._refresh_filmstrip()
            return
        action = self._router.resolve_action_key(key)
        if action is not None:
            self.current_clip.flag = action
            self._refresh_filmstrip()
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Manual smoke test — real keyboard control**

Run the Task 5 smoke script again, then press: `Space` (play/pause), `→` (next clip plays), `I`/`O` (marks), `P` (pick), `1` (room). Verify on screen: clip changes and plays, filmstrip border turns green on P, room label updates on a room key. Close manually. No traceback expected.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: teclado real — navegacion, play/pause, in/out y pick-reject sobre el clip"
```

---

## Milestone 4 — Subcuartos y estado visual completo

### Task 7: subroom creation live (spec app-externa §5): first key press on a subroom asks which parent

The spec: subrooms are not configured upfront; standing on a room with known subrooms, the keyboard enters subroom mode (already in `KeyboardRouter`); if a subroom key is pressed but the subroom doesn't exist for the active parent, the app asks once which parent room it hangs from, then attaches it via `CategoryTree.attach_subroom`.

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_subcuarto_desconocido_pide_padre_y_se_cuelga(qtbot, monkeypatch):
    window = _window_with_video(qtbot)
    monkeypatch.setattr(
        window, "_ask_parent_room",
        lambda subroom: "Recámara 1",
    )
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window._router.subrooms = {"Recámara 1": []}   # existe el padre como opcion
    window.attach_subroom_or_resolve("Baño")
    assert window.category_tree.path_for("Recámara 1", subroom="Baño") == ["Recámara 1", "Baño"]
    assert window.current_clip.categoria_path == ["Recámara 1", "Baño"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — `attach_subroom_or_resolve` does not exist.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
    def attach_subroom_or_resolve(self, subroom: str) -> list[str] | None:
        """Resuelve el path completo del subcuarto para el clip actual.

        Si el subcuarto ya cuelga de alguno de los cuartos activos con
        subcuartos conocidos, se usa ese. Si no, se le pregunta al usuario
        una sola vez a que cuarto colgarlo (spec app-externa §5).
        """
        for parent in self.room_selection.active_rooms():
            if subroom in self.category_tree.known_subrooms_for(parent):
                return self.category_tree.path_for(parent, subroom=subroom)
        parent = self._ask_parent_room(subroom)
        if parent is None:
            return None
        self.category_tree.attach_subroom(parent, subroom)
        return self.category_tree.path_for(parent, subroom=subroom)

    def _ask_parent_room(self, subroom: str) -> str | None:
        # UI minima: dialogo con QInputDialog.getItem sobre cuartos activos
        from PySide6.QtWidgets import QInputDialog
        rooms = self.room_selection.active_rooms()
        if not rooms:
            return None
        parent, ok = QInputDialog.getItem(self, "Subcuarto", f"¿A qué cuarto cuelga '{subroom}'?", rooms, 0, False)
        return parent if ok else None
```

Wire into `handle_key_press` so that when the router is in `pending_parent` mode and `resolve_subroom_key` returns `None` (subroom not created yet), the flow calls `attach_subroom_or_resolve(key_text)` against a list of candidate subroom names (start with the three usual ones per app-externa spec: Baño, Closet, Terraza — this list lives here as `SUBROOM_CANDIDATES`).

```python
SUBROOM_CANDIDATES = ["Baño", "Closet", "Terraza"]

# in handle_key_press, after the router room/action handling:
        if self._router.pending_parent is not None:
            self._router.resolve_subroom_key(key)
            parent = self._router.pending_parent
            # la tecla no correspondio a un subcuarto conocido: crear
            self._router.pending_parent = None
            ...
```

(Implementation detail left to the implementer: keep the exact flow consistent with the router's `pending_parent` semantics; the test above pins the contract.)

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Manual smoke test**

With real footage imported, press the key of a room, then a subroom key for a subroom that does not exist yet (e.g. "Baño" under a room with none). Expect: a small dialog asks which room it hangs from; after answering, the clip's filmstrip label shows `Padre > Subcuarto`.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: subcuartos se crean en vivo preguntando a que cuarto cuelgan"
```

### Task 8: current-clip blue border + counters per room (app-externa §4)

**Files:**
- Modify: `src/clasificador_video/ui/filmstrip.py`
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_filmstrip.py`, `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_filmstrip.py
def test_clip_actual_tiene_borde_azul(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    strip.set_current(0)
    assert "border-color: #2b7fff" in strip.item_widgets[0].styleSheet()


def test_pick_sobre_borde_azul_mantiene_ambos_colores(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="pick")])
    strip.set_current(0)
    assert "border-color: #3bb273" in strip.item_widgets[0].styleSheet()
    assert "border-color: #2b7fff" in strip.item_widgets[0].styleSheet()
```

```python
# additions to tests/ui/test_main_window.py
def test_columna_de_cuartos_muestra_contador_de_clips(qtbot):
    window = _window_with_video(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Sala"], fps=30.0),
    ]
    window.load_clips(clips)
    assert window.room_list_widget.item(0).text() == "Sala (2)"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_filmstrip.py tests/ui/test_main_window.py -v`
Expected: FAIL — no `set_current`; room items have no counters.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/filmstrip.py — additions
CURRENT_COLOR = "#2b7fff"

    def set_current(self, index: int) -> None:
        for i, widget in enumerate(self.item_widgets):
            style = widget.styleSheet()
            if "border-color" in style:
                new = style.replace(CURRENT_COLOR + ";", "").rstrip(" ;")
                widget.setStyleSheet(new)
            else:
                widget.setStyleSheet("")
            if i == index:
                current_border = f"border: 2px solid; border-color: {CURRENT_COLOR};"
                widget.setStyleSheet(style + current_border if style else current_border)
```

(Implementer freedom: a cleaner approach is to recompute the stylesheet from the clip's flag + current index inside `set_clips`; the tests only pin the observable behavior. Prefer the clean recompute.)

```python
# src/clasificador_video/ui/main_window.py — additions
    def _refresh_room_counts(self) -> None:
        from collections import Counter
        counts: Counter[str] = Counter()
        for clip in self.clips:
            if clip.categoria_path:
                counts[clip.categoria_path[0]] += 1
        self.room_list_widget.clear()
        for room in self.room_selection.active_rooms():
            self.room_list_widget.addItem(f"{room} ({counts[room]})")

# call _refresh_room_counts() and filmstrip.set_current(self.current_index)
# inside _refresh_filmstrip; call set_current after load_clips/handle_arrow.
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_filmstrip.py tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/filmstrip.py src/clasificador_video/ui/main_window.py tests/ui/test_filmstrip.py tests/ui/test_main_window.py
git commit -m "feat: borde azul del clip actual y contadores por cuarto en la columna"
```

---

## Milestone 5 — Persistencia y export

### Task 9: autosave wiring (spec §10)

Every classification action persists the session (project, rooms, category tree, clips state) via the atomic `save_session`. On startup, if a session file exists, offer to restore it (QMessageBox).

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Modify: `src/clasificador_video/app.py`
- Test: `tests/test_app.py`, `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_cada_accion_dispara_autosave(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    session_path = tmp_path / "sesion.json"
    window.session_path = session_path
    calls = []
    monkeypatch.setattr(window, "_autosave", lambda: calls.append(1))
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    window.handle_key_press("1")
    window.handle_key_press("p")
    assert len(calls) >= 3


def test_autosave_escribe_el_estado_actual(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    session_path = tmp_path / "sesion.json"
    window.session_path = session_path
    window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=30.0)])
    window._autosave()
    import json
    saved = json.loads(session_path.read_text())
    assert saved["clips"][0]["categoria_path"] == ["Sala"]
    assert saved["clips"][0]["flag"] == "none"
```

```python
# additions to tests/test_app.py
def test_arrancar_restaura_sesion_si_existe_y_el_usuario_acepta(qtbot, monkeypatch, tmp_path):
    import json
    from pathlib import Path
    from PySide6.QtWidgets import QMessageBox
    session = tmp_path / "sesion.json"
    session.write_text(json.dumps({"proyecto": "Casa", "clips": [{"orden": 1, "ruta": "/a.MP4", "categoria_path": [], "fps": 30.0, "in_frame": None, "out_frame": None, "flag": "none", "ruta_proxy": None}], "rooms": ["Sala"]}))
    monkeypatch.setattr(app_module, "SESSION_PATH", session)
    monkeypatch.setattr(RoomConfigDialog, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    window = app_module.arrancar(video_factory=None, session_path=session)
    assert window is not None
    assert window.clips[0].ruta.name == "a.MP4"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py tests/test_app.py -v`
Expected: FAIL — `_autosave`, `session_path`, session restore do not exist.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
    def _autosave(self) -> None:
        if self.session_path is None:
            return
        data = {
            "proyecto": self.project_name,
            "rooms": self.room_selection.active_rooms(),
            "rooms_raw": ...(serializable RoomSelection state...),
            "category_tree": ...,  # serializable mapping parent -> [subrooms]
            "clips": [c.to_dict() for c in self.clips],
        }
        save_session(self.session_path, data)

# call self._autosave() at the end of: handle_key_press (each branch),
# handle_arrow, load_clips, attach_subroom_or_resolve.
```

```python
# src/clasificador_video/app.py — additions
SESSION_PATH = Path.home() / ".clasificador_video" / "sesion.json"

def _restore_session(window: MainWindow, session_path: Path) -> None:
    data = load_session(session_path)
    if data is None:
        return
    if QMessageBox.question(None, "Sesión guardada", "Se encontró una sesión sin terminar. ¿Recuperarla?") != QMessageBox.Yes:
        return
    # rebuild clips from dicts, rooms selection, category tree, then window.load_clips(...)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py tests/test_app.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py src/clasificador_video/app.py tests/ui/test_main_window.py tests/test_app.py
git commit -m "feat: autoguardado de sesion en cada accion y restauracion al arrancar"
```

### Task 10: export manifest button (spec §8, §11) with non-blocking unclassified warning

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_exportar_escribe_manifest_con_formato_del_plugin(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    out = tmp_path / "manifest.json"
    window.ingest_tree.import_folder(tmp_path)   # tmp_path como carpeta (vacia)
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Sala"], fps=59.94,
             in_frame=30, out_frame=200, flag="pick"),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=[], fps=29.97, flag="none"),
    ])
    monkeypatch.setattr("clasificador_video.ui.main_window.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(out), ""))
    window.export_button.click()
    import json
    saved = json.loads(out.read_text())
    assert saved["proyecto"] == "Casa Jardin"
    assert saved["clips"][0]["ruta"] == "/a.MP4"
    assert saved["clips"][1]["categoria_path"] == []
    assert saved["clips"][0]["flag"] == "pick"
    assert saved["clips"][0]["in_frame"] == 30


def test_exportar_avisa_si_hay_clips_sin_clasificar_sin_bloquear(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    out = tmp_path / "m.json"
    window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0),
    ])
    warns = []
    monkeypatch.setattr("clasificador_video.ui.main_window.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(out), ""))
    monkeypatch.setattr("clasificador_video.ui.main_window.QMessageBox.warning",
                        lambda *a, **k: warns.append(1) or QMessageBox.Ok)
    window.export_button.click()
    assert warns == [1]
    assert out.exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — no `export_button`.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
        self.export_button = QPushButton("Exportar manifest…")
        self.export_button.clicked.connect(self._on_export_manifest)
        top_bar.addWidget(self.export_button)  # junto al selector de calidad

    def _on_export_manifest(self) -> None:
        unclassified = [c for c in self.clips if not c.categoria_path]
        if unclassified:
            QMessageBox.warning(
                self, "Clips sin clasificar",
                f"{len(unclassified)} clip(s) no tienen cuarto y entrarán en 'Sin clasificar'. "
                "Puedes seguir y corregir después.",
            )
        path, _ = QFileDialog.getSaveFileName(self, "Guardar manifest", "manifest.json", "JSON (*.json)")
        if not path:
            return
        manifest = Manifest(
            proyecto=self.project_name,
            orientacion="horizontal",  # TODO fase 3: detectar del material predominante
            clips=self.clips,
        )
        manifest.write_json(Path(path))
        self.status_label.setText(f"Manifest exportado: {path}")
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Manual smoke test — full end-to-end**

```bash
PYTHONPATH=src .venv/bin/python -c "
import sys
from pathlib import Path
import mpv as real_mpv
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from clasificador_video.rooms import RoomSelection
from clasificador_video.category_path import CategoryTree
from clasificador_video.ui.main_window import MainWindow

app = QApplication(sys.argv)
sel = RoomSelection(); sel.toggle('Sala'); sel.toggle('Cocina')
w = MainWindow('Casa Jardin', sel, CategoryTree(), video_factory=lambda **kw: real_mpv.MPV(**kw))
w.resize(1100, 700); w.show()
w.ingest_tree.import_folder(Path('TEST'))
w._load_clips_from_ingest()
QTimer.singleShot(2500, app.quit)
sys.exit(app.exec())
"
```
Then, manually in the window: import the `TEST/` folder via the button, classify a few clips (room keys, P/X, I/O), export to `/tmp/manifest-e2e.json`, and verify the file:
```bash
.venv/bin/python -c "import json; d=json.load(open('/tmp/manifest-e2e.json')); print(d['proyecto'], len(d['clips']), d['clips'][0].keys())"
```
Expected: valid JSON, `clips` present with the exact Phase-1 keys (`orden ruta categoria_path fps in_frame out_frame flag ruta_proxy`), and the first clip shows the classification made by hand.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: exportar manifest con aviso no bloqueante de clips sin clasificar"
```

---

## Milestone 6 — Cierre

### Task 11: full suite green + final smoke

- [ ] **Step 1: Run the complete suite**

Run: `.venv/bin/pytest -v`
Expected: 0 failures (Phase 1's 95 + this phase's new tests, all passing). If anything broke, fix forward with a new commit — never rewrite history.

- [ ] **Step 2: Final manual smoke — the real workflow**

Run `.venv/bin/python -m clasificador_video.app`, then with the real `TEST/` footage:
1. Configure rooms (pick at least two).
2. Import the `TEST/` folder.
3. Wait for thumbnails; navigate with arrows; play with Space.
4. Classify ≥ 3 clips: room key, P, I/O.
5. Export to `/tmp/manifest-e2e-final.json`.
6. In Premiere (plugin installed and working from Phase 0): press "Importar clasificación", pick the file, verify bins/rooms/labels/in-out appear as classified. (If Premiere is not open, defer this one item to Bruno — the JSON contract is already verified by the plugin's own test fixtures.)

- [ ] **Step 3: Write the phase-2 closing summary commit**

```bash
git add docs/superpowers/plans/2026-08-06-app-externa-clasificador-fase2.md
git commit -m "docs: plan de fase 2 de la app externa — flujo funcional completo"
```

---

## What this plan intentionally does not build yet

- **Proxy UI** ("Buscar proxies" right-click, spec §3): the matching logic (`proxy_match.py`) exists and is tested; the UI action that points a folder at a proxy folder and writes `ruta_proxy` into the clips is a small focused task for phase 3. The manifest exports `ruta_proxy: null` meanwhile — the plugin skips it (verified in analysis).
- **`orientacion` auto-detection**: phase 2 hardcodes `"horizontal"`; detecting the dominant orientation from probes (rotation > 0 → vertical) is a tiny follow-up.
- **Undo (Ctrl+Z multilevel, spec §5)**: the keyboard legend mentions it, but a real undo stack is its own task.
- **Drag-and-drop** of folders/files onto the ingest panel (spec §3): only the button path is built here.
- **`proyecto`/shooting name**: the app still hardcodes "Shooting sin nombre"; naming a project at start (simple dialog field) is a phase-3 nicety.
- **Quality selector applies at open time** — current profile is not persisted across clips.

## Definición de "terminado"

All tasks committed one per step, each with its tests green, full suite (`pytest -v`) passing with 0 failures, the three manual smoke tests in Tasks 2/5/6 run against real `TEST/` footage, and the end-to-end workflow (import → classify → export → manifest verified) confirmed. At that point, summarize what was built, what tests ran, and what remains per the "out of scope" section above.
