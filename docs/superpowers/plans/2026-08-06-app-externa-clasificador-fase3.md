# App Externa del Clasificador de Video — Fase 3: pulido y features pendientes — 2026-08-06

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar los 5 features pendientes del informe de fase 2 (§5 "Lo que falta por mejorar") más dos ítems de deuda de UI del spec original: que el usuario pueda ponerle nombre al proyecto desde el diálogo de arranque, que la orientación del manifest se detecte automáticamente del material, que los proxies se vinculen desde la UI con clic derecho, que Ctrl+Z deshaga de verdad (multinivel), que se pueda arrastrar carpetas al panel en vez del botón, y que el filmstrip muestre el punto de color y la barra superior el indicador de autoguardado que pide el spec §3-4.

**Fase 2 produjo** (reusado como está, no se toca salvo lo que cada task indique): `manifest.py`, `autosave.py`, `rooms.py`, `category_path.py`, `ingest.py`, `proxy_match.py`, `thumbnails.py`, `player.py`, `keyboard.py`, `probe.py`, y `ui/` (RoomConfigDialog, Filmstrip, MainWindow, VideoWidget, app.py). Suite: 124 passed, 0 failures.

**Riesgos ya validados en fases anteriores (no re-litigar):**
- mpv embebe en PySide6 vía `wid` en macOS con `hwdec=videotoolbox`.
- Miniaturas en software (sin `--hwdec`) no saturan VideoToolbox y dejan fluir el reproductor.
- El `setter` de `time_pos` de python-mpv se cuelga — la app solo lee `time_pos`, nunca lo escribe.
- `winId()` debe llamarse con el widget ya mostrado.

**Tech notes para esta fase:**
- Los cambios son locales y acotados: cada task toca 1-3 archivos, con tests que prueban el contrato sin mockear la GUI completa.
- El orden de milestones es por dependencia: nombre de proyecto (M1) y orientación (M2) son previos a todo; proxies (M3) depende de tener clips cargados; deshacer (M4) depende de que las acciones existan; drag-and-drop (M5) y deuda UI (M6) son independientes.
- Autosave ya se dispara en cada acción de clasificación — undo también debe dispararlo al restaurar estado.

---

## Milestone 1 — Nombre de proyecto configurable

### Task 1: campo de nombre en el diálogo de cuartos, thread hasta el manifest

El spec §5 dice que al abrir un shooting nuevo se configura el nombre. Hoy `arrancar()` hardcodea `"Shooting sin nombre"` y el diálogo solo lo usa como título de ventana. Hay que agregar un `QLineEdit` al diálogo, exponerlo como `project_name`, y que `arrancar()` y `MainWindow` lo usen.

**Files:**
- Modify: `src/clasificador_video/ui/room_config_dialog.py`
- Modify: `src/clasificador_video/app.py`
- Test: `tests/ui/test_room_config_dialog.py`, `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_room_config_dialog.py
def test_dialogo_tiene_campo_de_nombre_de_proyecto():
    dialog = RoomConfigDialog()
    assert dialog.project_name_input is not None
    assert dialog.project_name_input.text() == "Shooting sin nombre"


def test_dialogo_expone_el_nombre_ingresado():
    dialog = RoomConfigDialog()
    dialog.project_name_input.setText("Casa Jardin")
    assert dialog.project_name == "Casa Jardin"
```

```python
# additions to tests/test_app.py
def test_arrancar_usa_el_nombre_del_dialogo(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog
    from clasificador_video.ui.room_config_dialog import RoomConfigDialog

    def fake_dialog(*args, **kwargs):
        d = RoomConfigDialog(*args, **kwargs)
        d.project_name_input.setText("Casa Playa")
        d.selection.toggle("Sala")
        return d

    monkeypatch.setattr(app_module, "RoomConfigDialog", fake_dialog)
    monkeypatch.setattr(RoomConfigDialog, "exec", lambda self: QDialog.Accepted)
    window = app_module.arrancar(video_factory=None)
    assert window.project_name == "Casa Playa"
    assert window.windowTitle() == "Casa Playa"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_room_config_dialog.py tests/test_app.py -v`
Expected: FAIL — `RoomConfigDialog` no tiene `project_name_input` ni property `project_name`; `arrancar` no lee el nombre del diálogo.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/room_config_dialog.py — changes
# __init__: sin argumento project_name; agrega campo de texto arriba de los chips

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar cuartos")

        layout = QVBoxLayout(self)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Proyecto:"))
        self.project_name_input = QLineEdit("Shooting sin nombre")
        name_row.addWidget(self.project_name_input)
        layout.addLayout(name_row)

        # ...existing grid, custom_row, start_button...

    @property
    def project_name(self) -> str:
        return self.project_name_input.text().strip() or "Shooting sin nombre"
```

```python
# src/clasificador_video/app.py — changes
# arrancar(): usa dialog.project_name en vez de "Shooting sin nombre"

def arrancar(
    video_factory: Callable[..., object] | None = None,
    session_path: Path | None = None,
) -> MainWindow | None:
    if session_path is None:
        session_path = SESSION_PATH
    dialog = RoomConfigDialog()
    if dialog.exec() != QDialog.Accepted:
        return None
    window = MainWindow(
        project_name=dialog.project_name,
        room_selection=dialog.selection,
        category_tree=CategoryTree(),
        video_factory=video_factory,
    )
    window.session_path = session_path
    _restore_session(window, session_path)
    window.resize(1100, 700)
    return window
```

Nota: al cambiar la firma de `RoomConfigDialog.__init__`, hay que actualizar el test `test_arrancar_abre_dialogo_y_construye_ventana_con_cuartos_elegidos` y `test_arrancar_restaura_sesion_si_existe_y_el_usuario_acepta` — esos tests mockean `RoomConfigDialog` completo, así que no les afecta el cambio de firma. Sí afecta si algún otro test construye `RoomConfigDialog(project_name="...")` directamente.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_room_config_dialog.py tests/test_app.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/room_config_dialog.py src/clasificador_video/app.py tests/ui/test_room_config_dialog.py tests/test_app.py
git commit -m "feat: nombre de proyecto configurable desde el dialogo de arranque"
```

---

## Milestone 2 — Orientación automática del manifest

### Task 2: detectar orientación dominante del material y usarla en la exportación

Hoy el manifest sale con `"horizontal"` fijo (línea 352 de `main_window.py`, con un `# TODO fase 3`). El probe ya devuelve `rotation` por clip (0 = horizontal, 90/270 = vertical). Hay que acumular las rotaciones durante el ingest y al exportar decidir la dominante.

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_orientacion_detecta_vertical_cuando_domina_rotacion_90(qtbot):
    from collections import Counter
    window = _window_with_video(qtbot)
    window._rotation_counts = Counter({90: 3, 0: 1})
    assert window._orientacion_dominante() == "vertical"


def test_orientacion_detecta_horizontal_cuando_domina_sin_rotacion(qtbot):
    from collections import Counter
    window = _window_with_video(qtbot)
    window._rotation_counts = Counter({0: 5, 270: 1})
    assert window._orientacion_dominante() == "horizontal"


def test_orientacion_default_horizontal_sin_clips(qtbot):
    from collections import Counter
    window = _window_with_video(qtbot)
    window._rotation_counts = Counter()
    assert window._orientacion_dominante() == "horizontal"


def test_load_clips_from_ingest_acumula_rotaciones(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "C0001.MP4").touch()
    (carpeta / "C0002.MP4").touch()
    monkeypatch.setattr(window, "_probe_clip", lambda path: {
        "width": 1080, "height": 1920, "fps": 59.94, "has_audio": True,
        "duration_frames": 360, "rotation": 90,
    })
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    assert window._rotation_counts[90] == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — `_rotation_counts` y `_orientacion_dominante` no existen.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
from collections import Counter

# in __init__:
        self._rotation_counts: Counter[int] = Counter()

# in _load_clips_from_ingest, after probe_clip:
                info = self._probe_clip(video)
                clips.append(Clip(orden=orden, ruta=video, categoria_path=[], fps=info["fps"]))
                self._rotation_counts[info["rotation"] % 360] += 1
                orden += 1

# in load_clips (for restored sessions), accumulate rotations:
    def load_clips(self, clips: list[Clip]) -> None:
        self.clips = clips
        self.current_index = 0
        self._refresh_filmstrip()
        if clips:
            try:
                self.video_widget.open_clip(clips[0].ruta)
            except RuntimeError:
                pass
        self._autosave()

# new method:
    def _orientacion_dominante(self) -> str:
        if not self._rotation_counts:
            return "horizontal"
        horizontal = self._rotation_counts.get(0, 0) + self._rotation_counts.get(180, 0)
        vertical = self._rotation_counts.get(90, 0) + self._rotation_counts.get(270, 0)
        return "vertical" if vertical > horizontal else "horizontal"

# in _on_export_manifest, replace "horizontal" hardcode:
        manifest = Manifest(
            proyecto=self.project_name,
            orientacion=self._orientacion_dominante(),
            clips=self.clips,
        )
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: orientacion del manifest detectada automaticamente del material"
```

---

## Milestone 3 — UI de proxies (clic derecho en panel de ingest)

### Task 3: "Buscar proxies" desde el menú contextual del panel de ingest

`proxy_match.match_proxies` ya existe y está testeado. Falta la acción de UI: clic derecho sobre una carpeta del panel de ingest → "Buscar proxies…" → elegir carpeta de proxies → emparejar y asignar `ruta_proxy` a los clips que correspondan.

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_context_menu_en_ingest_list_tiene_buscar_proxies(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    carpeta = tmp_path / "FX30"
    carpeta.mkdir()
    (carpeta / "C0001.MP4").touch()
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getExistingDirectory",
        lambda *a, **k: str(carpeta),
    )
    window.ingest_tree.import_folder(carpeta)
    window._refresh_ingest_list()

    from PySide6.QtCore import QPoint
    menu = window.ingest_list.customContextMenuRequested
    assert menu is not None  # la señal está conectada


def test_buscar_proxies_asigna_ruta_proxy_a_clips_emparejados(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    original_dir = tmp_path / "FX30"
    original_dir.mkdir()
    (original_dir / "C0001.MP4").touch()
    proxy_dir = tmp_path / "FX30_proxies"
    proxy_dir.mkdir()
    (proxy_dir / "C0001S03.MP4").touch()

    window.ingest_tree.import_folder(original_dir)
    window._refresh_ingest_list()
    window.load_clips([
        Clip(orden=1, ruta=original_dir / "C0001.MP4", categoria_path=[], fps=30.0),
    ])
    window._assign_proxies_for_folder(window.ingest_tree.top_level_folders()[0], proxy_dir)
    assert window.clips[0].ruta_proxy == proxy_dir / "C0001S03.MP4"


def test_buscar_proxies_sin_match_no_modifica_ruta_proxy(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    original_dir = tmp_path / "FX30"
    original_dir.mkdir()
    (original_dir / "C0001.MP4").touch()
    proxy_dir = tmp_path / "otra_carpeta"
    proxy_dir.mkdir()
    (proxy_dir / "X0001S03.MP4").touch()

    window.ingest_tree.import_folder(original_dir)
    window._refresh_ingest_list()
    window.load_clips([
        Clip(orden=1, ruta=original_dir / "C0001.MP4", categoria_path=[], fps=30.0),
    ])
    window._assign_proxies_for_folder(window.ingest_tree.top_level_folders()[0], proxy_dir)
    assert window.clips[0].ruta_proxy is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — `_assign_proxies_for_folder` no existe, `ingest_list` no tiene menú contextual.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu
from clasificador_video.proxy_match import match_proxies

# in __init__, after creating ingest_list:
        self.ingest_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ingest_list.customContextMenuRequested.connect(self._on_ingest_context_menu)

# new methods:
    def _on_ingest_context_menu(self, pos) -> None:
        item = self.ingest_list.itemAt(pos)
        if item is None:
            return
        idx = self.ingest_list.row(item)
        folders = self.ingest_tree.top_level_folders()
        if idx >= len(folders):
            return
        folder = folders[idx]
        menu = QMenu(self)
        proxy_action = menu.addAction("Buscar proxies…")
        action = menu.exec(self.ingest_list.mapToGlobal(pos))
        if action == proxy_action:
            proxy_dir = QFileDialog.getExistingDirectory(self, "Elegir carpeta de proxies")
            if proxy_dir:
                self._assign_proxies_for_folder(folder, Path(proxy_dir))

    def _assign_proxies_for_folder(self, folder, proxy_dir: Path) -> None:
        proxy_files = list(proxy_dir.glob("*"))
        if not proxy_files:
            return
        matches = match_proxies(folder.files, proxy_files)
        clip_by_path = {c.ruta: c for c in self.clips}
        for original, proxy in matches.items():
            if proxy is not None and original in clip_by_path:
                clip_by_path[original].ruta_proxy = proxy
        self._autosave()
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: menu contextual 'Buscar proxies' en el panel de ingest"
```

---

## Milestone 4 — Deshacer multinivel (Ctrl+Z)

### Task 4: stack de acciones que registra cada cambio de clasificación y lo revierte

La leyenda de teclado ya anuncia `Ctrl+Z deshacer` pero no existe. Se necesita un stack que guarde el estado anterior de cada acción de clasificación (cuarto, flag, in/out) y permita deshacer con Ctrl+Z.

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_deshacer_revierte_ultima_categoria(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.handle_key_press("1")  # asigna primer cuarto (Sala)
    assert window.clips[0].categoria_path == ["Sala"]
    window.handle_undo()
    assert window.clips[0].categoria_path == []


def test_deshacer_revierte_flag(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.handle_key_press("p")
    assert window.clips[0].flag == "pick"
    window.handle_undo()
    assert window.clips[0].flag == "none"


def test_deshacer_revierte_in_out(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=60.0)]
    window.load_clips(clips)
    window.video_widget.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    assert window.clips[0].in_frame == 120
    window.handle_undo()
    assert window.clips[0].in_frame is None


def test_deshacer_multiple_en_orden_inverso(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.handle_key_press("1")  # categoria
    window.handle_key_press("p")  # flag
    assert window.clips[0].categoria_path == ["Sala"]
    assert window.clips[0].flag == "pick"
    window.handle_undo()
    assert window.clips[0].flag == "none"
    assert window.clips[0].categoria_path == ["Sala"]  # categoria intacta
    window.handle_undo()
    assert window.clips[0].categoria_path == []


def test_deshacer_sobre_stack_vacio_no_hace_nada(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.handle_undo()  # no debe tirar error
    assert window.clips[0].categoria_path == []


def test_ctrl_z_shortcut_llama_a_handle_undo(qtbot):
    window = _window_with_video(qtbot)
    called = []
    window.handle_undo = lambda: called.append(1)
    # buscar el shortcut Ctrl+Z entre los shortcuts instalados
    for sc in window._shortcuts:
        if sc.key() == QKeySequence("Ctrl+Z"):
            sc.activated.emit()
            break
    assert called == [1]
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — `handle_undo` no existe, no hay shortcut Ctrl+Z.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
from typing import Any

# in __init__:
        self._undo_stack: list[dict[str, Any]] = []

# new method:
    def handle_undo(self) -> None:
        if not self._undo_stack:
            return
        action = self._undo_stack.pop()
        idx = action["clip_index"]
        if idx >= len(self.clips):
            return
        clip = self.clips[idx]
        kind = action["kind"]
        if kind == "category":
            clip.categoria_path = action["old_value"]
        elif kind == "flag":
            clip.flag = action["old_value"]
        elif kind == "in":
            clip.in_frame = action["old_value"]
        elif kind == "out":
            clip.out_frame = action["old_value"]
        elif kind == "clear_in_out":
            clip.in_frame = action["old_in"]
            clip.out_frame = action["old_out"]
        elif kind == "subroom":
            clip.categoria_path = action["old_value"]
        self._refresh_filmstrip()
        self._autosave()

    def _push_undo(self, kind: str, old_value: Any, **extra) -> None:
        if self.current_clip is None:
            return
        entry: dict[str, Any] = {
            "clip_index": self.current_index,
            "kind": kind,
            "old_value": old_value,
        }
        entry.update(extra)
        self._undo_stack.append(entry)

# modify handle_key_press — each branch pushes to undo before mutating:
    def handle_key_press(self, key: str) -> None:
        if self.current_clip is None:
            return
        # ...existing pending_parent check...
        if key == "i":
            old = self.current_clip.in_frame
            self._push_undo("in", old)
            self.current_clip.in_frame = self.video_widget.player.mark_in(self.current_clip.fps)
            # ...restart refresh+autosave...
        if key == "o":
            old = self.current_clip.out_frame
            self._push_undo("out", old)
            self.current_clip.out_frame = self.video_widget.player.mark_out(self.current_clip.fps)
            # ...restart refresh+autosave...
        if key == "u":
            old_in = self.current_clip.in_frame
            old_out = self.current_clip.out_frame
            self._push_undo("clear_in_out", None, old_in=old_in, old_out=old_out)
            self.current_clip.in_frame = None
            self.current_clip.out_frame = None
            # ...restart refresh+autosave...
        # ...existing room key logic...
        if room_path is not None:
            old = list(self.current_clip.categoria_path)
            self._push_undo("category", old)
            self.current_clip.categoria_path = room_path
            # ...restart refresh+autosave...
        if action is not None:
            old = self.current_clip.flag
            self._push_undo("flag", old)
            self.current_clip.flag = action
            # ...restart refresh+autosave...

# in _handle_subroom_key, also push undo before mutating:
    def _handle_subroom_key(self, key: str) -> None:
        sub_path = self._router.resolve_subroom_key(key)
        if sub_path is not None:
            old = list(self.current_clip.categoria_path)
            self._push_undo("subroom", old)
            self.current_clip.categoria_path = sub_path
            self._refresh_filmstrip()
            return
        # ...rest unchanged...

# in _install_shortcuts, add:
            ("Ctrl+Z", self.handle_undo),
```

**Nota de implementación:** `_push_undo` debe llamarse **antes** de mutar el clip, con el valor viejo. Las ramas de `handle_key_press` que ya existen (i, o, u, room_path, action) deben intercalar `_push_undo` entre el chequeo y la mutación. El implementador debe preservar la estructura existente de `_autosave()` + `_refresh_filmstrip()` que ya está al final de cada rama.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: deshacer multinivel (Ctrl+Z) sobre clasificacion, flag e in/out"
```

---

## Milestone 5 — Drag-and-drop de carpetas al panel de ingest

### Task 5: aceptar carpetas arrastradas al panel de ingest

El spec §3 pide arrastrar carpetas al panel de ingest, no solo usar el botón. Qt lo soporta con `setAcceptDrops(True)` y los eventos `dragEnterEvent`/`dropEvent`.

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_main_window.py
def test_ingest_list_acepta_drops(qtbot):
    window = _window_with_video(qtbot)
    assert window.ingest_list.acceptDrops() is True


def test_drop_de_carpeta_la_importa(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot)
    carpeta = tmp_path / "Dron"
    carpeta.mkdir()
    (carpeta / "D0001.MP4").touch()

    from PySide6.QtCore import QMimeData, QUrl
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(carpeta))])

    window._on_ingest_drop(mime)
    assert window.ingest_list.count() == 1
    assert window.ingest_list.item(0).text() == "Dron"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL — `_on_ingest_drop` no existe, `ingest_list` no acepta drops.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py — additions
from PySide6.QtCore import QMimeData, QUrl

# in __init__, after creating ingest_list:
        self.ingest_list.setAcceptDrops(True)
        self.ingest_list.dragEnterEvent = self._on_ingest_drag_enter
        self.ingest_list.dropEvent = self._on_ingest_drop_event

    def _on_ingest_drag_enter(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _on_ingest_drop_event(self, event) -> None:
        urls = event.mimeData().urls()
        for url in urls:
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.ingest_tree.import_folder(path)
        self._refresh_ingest_list()

    def _on_ingest_drop(self, mime_data: QMimeData) -> None:
        """Entry point inyectable para tests (evita construir QDropEvent)."""
        urls = mime_data.urls()
        for url in urls:
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.ingest_tree.import_folder(path)
        self._refresh_ingest_list()
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: drag-and-drop de carpetas al panel de ingest"
```

---

## Milestone 6 — Deuda de UI: punto de color y autoguardado

### Task 6: punto de color en esquina del filmstrip + indicador "Autoguardado hace Ns"

El spec §4 pide un punto de color en la esquina superior derecha de cada miniatura que refuerce el estado pick/reject. El spec §3 pide un indicador discreto de autoguardado en la barra superior.

**Files:**
- Modify: `src/clasificador_video/ui/filmstrip.py`
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_filmstrip.py`, `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# additions to tests/ui/test_filmstrip.py
def test_item_pick_tiene_punto_verde(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="pick")])
    assert strip.item_widgets[0]._color_dot.isVisible()
    assert "#3bb273" in strip.item_widgets[0]._color_dot.styleSheet()


def test_item_sin_flag_no_tiene_punto_de_color(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])
    assert not strip.item_widgets[0]._color_dot.isVisible()
```

```python
# additions to tests/ui/test_main_window.py
def test_autosave_actualiza_el_indicador(qtbot, monkeypatch):
    from datetime import datetime, timedelta
    window = _window_with_video(qtbot)
    fake_now = datetime(2026, 8, 6, 14, 0, 0)
    monkeypatch.setattr("clasificador_video.ui.main_window.datetime", type("fake_datetime", (), {
        "now": staticmethod(lambda: fake_now),
        "timedelta": datetime.timedelta,
    }))
    window._update_autosave_indicator(fake_now)
    assert "Autoguardado hace" in window.autosave_label.text()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_filmstrip.py tests/ui/test_main_window.py -v`
Expected: FAIL — `_color_dot` y `autosave_label` no existen.

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/filmstrip.py — additions
# in _ClipItemWidget.__init__, after creating the layout:
        self._color_dot = QLabel()
        self._color_dot.setFixedSize(10, 10)
        self._color_dot.setStyleSheet("border-radius: 5px;")
        self._color_dot.hide()
        # posicionar en esquina superior derecha del widget (stacked o absolute)
        # ... agregar al layout o usar un overlay ...

    def _update_color_dot(self, flag: str) -> None:
        if flag == "pick":
            self._color_dot.setStyleSheet("border-radius: 5px; background-color: #3bb273;")
            self._color_dot.show()
        elif flag == "reject":
            self._color_dot.setStyleSheet("border-radius: 5px; background-color: #e0556f;")
            self._color_dot.show()
        else:
            self._color_dot.hide()
```

```python
# src/clasificador_video/ui/main_window.py — additions
from datetime import datetime

# in __init__:
        self.autosave_label = QLabel("")
        top_bar.addWidget(self.autosave_label)

# modify _autosave:
    def _autosave(self) -> None:
        if self.session_path is None:
            return
        tree = {}
        for parent in self.room_selection.active_rooms():
            known = self.category_tree.known_subrooms_for(parent)
            if known:
                tree[parent] = known
        data = {
            "proyecto": self.project_name,
            "rooms": self.room_selection.active_rooms(),
            "category_tree": tree,
            "clips": [c.to_dict() for c in self.clips],
        }
        save_session(self.session_path, data)
        self._update_autosave_indicator()

    def _update_autosave_indicator(self, when: datetime | None = None) -> None:
        now = when or datetime.now()
        self.autosave_label.setText(f"Autoguardado {now.strftime('%H:%M:%S')}")
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_filmstrip.py tests/ui/test_main_window.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/filmstrip.py src/clasificador_video/ui/main_window.py tests/ui/test_filmstrip.py tests/ui/test_main_window.py
git commit -m "feat: punto de color en filmstrip e indicador de autoguardado en barra superior"
```

---

## Milestone 7 — Cierre

### Task 7: full suite green + final smoke

- [ ] **Step 1: Run the complete suite**

Run: `.venv/bin/pytest -v`
Expected: 0 failures. Si algo se rompió, arreglar hacia adelante con un nuevo commit.

- [ ] **Step 2: Final manual smoke — el flujo completo con lo nuevo**

Run `.venv/bin/python -m clasificador_video.app`, luego con material real de `TEST/`:
1. El diálogo ahora pide nombre de proyecto — escribir uno.
2. Configurar cuartos y empezar.
3. Importar carpeta `TEST/` (botón o drag-and-drop).
4. Clasificar 3+ clips: cuarto, P, I/O.
5. Probar Ctrl+Z para deshacer al menos una categoría y un flag.
6. Clic derecho en la carpeta del panel de ingest → "Buscar proxies" (si hay carpeta de proxies a mano).
7. Exportar manifest — verificar que `orientacion` sea correcta (vertical si el material es vertical).
8. Confirmar que el punto de color aparece en clips pick/reject del filmstrip y que el indicador de autoguardado se actualiza.

- [ ] **Step 3: Write the phase-3 closing summary commit**

```bash
git add docs/superpowers/plans/2026-08-06-app-externa-clasificador-fase3.md
git commit -m "docs: plan de fase 3 de la app externa — nombre de proyecto, orientacion, proxies, deshacer, drag-and-drop y deuda UI"
```

---

## What this plan intentionally does not build yet

- **Verificación end-to-end con Premiere real** (punto 6 del informe §5): es una tarea manual para Bruno — abrir Premiere, importar el manifest generado por la app con el plugin UXP, y confirmar que el ciclo completo funciona con material real. El código no se toca para esto.
- **Subcuartos para cuartos simples** (deuda conocida): sigue siendo un recorte de diseño — solo cuartos numerados (Recámara 1, Baño 1) entran en modo subcuarto. Abrirlo a cuartos simples requeriría rediseñar el flujo de teclado.
- **Miniaturas en paralelo con hardware**: la limitación de VideoToolbox sigue vigente; la cola secuencial en software (~1 s/clip) es aceptable para shootings típicos. Si se vuelve cuello de botella en uso real, se evalúa un pool de 1 con hardware compartido.
- **Empaquetado con PyInstaller** (handoff §7.1, §7.3): firmado, notarización y distribución como `.app` — esto es una fase de release, no de features.

## Definición de "terminado"

Todos los tasks commiteados uno por paso, cada uno con sus tests en verde, suite completa (`pytest -v`) pasando con 0 failures, y el smoke manual del Task 7 ejecutado contra material real de `TEST/`. Al terminar, actualizar el informe de la sesión con lo construido, lo que falló (si algo falló) y lo que queda.
