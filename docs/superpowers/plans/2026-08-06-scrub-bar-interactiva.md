# ScrubBar interactiva — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer la `ScrubBar` interactiva (seek con click/arrastre de mouse), arreglar que el bracket de IN no aparece hasta que también hay OUT, y mostrar timecode/frame (formato `MM:SS:FF`) de IN/OUT/duración/posición.

**Architecture:** `ScrubBar` gana dos señales Qt (`seek_started`, `seek_requested`) que traduce de eventos de mouse a segundos, sin conocer a `MpvPlayer` (mantiene la separación actual). `MainWindow` conecta esas señales y decide pausar + hacer seek real. `MpvPlayer` gana `seek()` e `is_paused`. El `paintEvent` de `ScrubBar` se separa en tres bloques independientes (IN, OUT, tramo entre ambos). Un nuevo `QLabel` (`scrubTimeLabel`) muestra el timecode, alimentado por una función pura `format_timecode()`.

**Tech Stack:** PySide6 (QWidget, Signal, QMouseEvent, QPainter), pytest + pytest-qt (`qtbot`), python-mpv (via `FakeMpv` doble de pruebas en tests).

Spec de referencia: `docs/superpowers/specs/2026-08-06-scrub-bar-interactiva-design.md`

---

### Task 1: Fix del bracket de IN visible sin OUT

**Files:**
- Modify: `src/clasificador_video/ui/video_widget.py:186-197` (método `paintEvent` de `ScrubBar`)
- Test: `tests/ui/test_video_widget.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/ui/test_video_widget.py`:

```python
def test_scrub_bar_dibuja_bracket_de_in_sin_out(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.set_in_out(300, None, 30.0)  # in=10s, sin out
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    assert not pixmap.toImage().isNull()
    # x esperado para in_frame=300 (10s de 60s) sobre ancho util (200-12=188)
    expected_x = 6 + round((10.0 / 60.0) * 188)
    img = pixmap.toImage()
    track_y = bar.height() // 2
    color = img.pixelColor(expected_x, track_y - 6)
    assert color.name() == "#4fd1e8"  # TRIM_COLOR


def test_scrub_bar_dibuja_bracket_de_out_sin_in(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.set_in_out(None, 900, 30.0)  # out=30s, sin in
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    assert not pixmap.toImage().isNull()
    expected_x = 6 + round((30.0 / 60.0) * 188)
    img = pixmap.toImage()
    track_y = bar.height() // 2
    color = img.pixelColor(expected_x, track_y - 6)
    assert color.name() == "#4fd1e8"


def test_scrub_bar_solo_in_no_dibuja_tramo_resaltado(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.set_in_out(300, None, 30.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    track_y = bar.height() // 2
    # a mitad de camino entre in (10s) y el final (60s) no deberia haber
    # tramo resaltado porque no hay out -- el track de fondo (BORDER) debe seguir ahi
    mid_x = 6 + round((35.0 / 60.0) * 188)
    color = img.pixelColor(mid_x, track_y)
    assert color.name() != "#4fd1e8"
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -k "bracket_de_in_sin_out or bracket_de_out_sin_in or solo_in_no_dibuja" -v`
Expected: FAIL (los tres, porque hoy no se dibuja nada con un solo marcador puesto)

- [ ] **Step 3: Implementar el fix mínimo**

Reemplazar en `src/clasificador_video/ui/video_widget.py` el bloque actual (líneas ~186-197):

```python
        if self._duration > 0:
            if self._in_frame is not None and self._out_frame is not None and self._fps:
                in_s = self._in_frame / self._fps
                out_s = self._out_frame / self._fps
                x1 = self._x_for(min(in_s, out_s), left, usable_width)
                x2 = self._x_for(max(in_s, out_s), left, usable_width)
                painter.setPen(QPen(QColor(TRIM_COLOR), 4))
                painter.drawLine(x1, track_y, x2, track_y)
                bracket_pen = QPen(QColor(TRIM_COLOR), 3)
                painter.setPen(bracket_pen)
                painter.drawLine(x1, track_y - 8, x1, track_y + 8)
                painter.drawLine(x2, track_y - 8, x2, track_y + 8)

            x = self._x_for(self._position, left, usable_width)
```

por:

```python
        if self._duration > 0:
            in_x = out_x = None
            if self._in_frame is not None and self._fps:
                in_x = self._x_for(self._in_frame / self._fps, left, usable_width)
            if self._out_frame is not None and self._fps:
                out_x = self._x_for(self._out_frame / self._fps, left, usable_width)

            if in_x is not None and out_x is not None:
                x1, x2 = min(in_x, out_x), max(in_x, out_x)
                painter.setPen(QPen(QColor(TRIM_COLOR), 4))
                painter.drawLine(x1, track_y, x2, track_y)

            bracket_pen = QPen(QColor(TRIM_COLOR), 3)
            painter.setPen(bracket_pen)
            if in_x is not None:
                painter.drawLine(in_x, track_y - 8, in_x, track_y + 8)
            if out_x is not None:
                painter.drawLine(out_x, track_y - 8, out_x, track_y + 8)

            x = self._x_for(self._position, left, usable_width)
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -v`
Expected: PASS (todos, incluyendo los existentes de `ScrubBar`)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/video_widget.py tests/ui/test_video_widget.py
git commit -m "$(cat <<'EOF'
fix: bracket de IN/OUT en la scrub bar se dibuja aunque falte el otro

Antes exigia ambos marcadores para dibujar cualquier cosa -- marcar solo
IN no mostraba nada hasta poner tambien OUT.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `format_timecode()` — formato MM:SS:FF

**Files:**
- Modify: `src/clasificador_video/ui/video_widget.py` (agregar función a nivel de módulo, antes de `class ScrubBar`)
- Test: `tests/ui/test_video_widget.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/ui/test_video_widget.py`:

```python
from clasificador_video.ui.video_widget import ScrubBar, VideoWidget, format_timecode


def test_format_timecode_frame_cero():
    assert format_timecode(0, 30.0) == "00:00:00"


def test_format_timecode_un_segundo_exacto():
    assert format_timecode(30, 30.0) == "00:01:00"


def test_format_timecode_minutos_y_frames():
    # 90 segundos + 7 frames a 30fps = 1min30s7f = frame 90*30+7=2707
    assert format_timecode(2707, 30.0) == "01:30:07"


def test_format_timecode_fps_no_entero():
    # 29.97fps: frame 30 -> ~1.0010s -> 00:01:00
    assert format_timecode(30, 29.97) == "00:01:00"


def test_format_timecode_fps_invalido_no_crashea():
    assert format_timecode(100, 0.0) == "00:00:00"
```

Nota: el import existente `from clasificador_video.ui.video_widget import ScrubBar, VideoWidget` al principio del archivo de test debe actualizarse (agregar `format_timecode`) en vez de duplicar el import.

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -k format_timecode -v`
Expected: FAIL con `ImportError` o `AttributeError` (la función no existe)

- [ ] **Step 3: Implementar**

Agregar en `src/clasificador_video/ui/video_widget.py`, antes de `class ScrubBar` (después de `_get_proc_address`):

```python
def format_timecode(frame: int, fps: float) -> str:
    """Convierte un numero de frame absoluto a MM:SS:FF -- consistente con
    que el modelo de datos ya guarda todo en frames (Clip.in_frame/out_frame),
    no en milisegundos.
    """
    if fps <= 0:
        return "00:00:00"
    total_seconds = frame / fps
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    remaining_frames = round(frame - (minutes * 60 + seconds) * fps)
    return f"{minutes:02d}:{seconds:02d}:{remaining_frames:02d}"
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/video_widget.py tests/ui/test_video_widget.py
git commit -m "$(cat <<'EOF'
feat: format_timecode() para mostrar frames como MM:SS:FF

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Label de timecode en MainWindow (IN/OUT/dur/pos)

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py:218-285` (creación de widgets, `video_column`, `_update_scrub_bar`, `_tick_playhead`)
- Modify: `src/clasificador_video/ui/theme.py` (estilo `scrubTimeLabel`)
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Fixture existente**

`tests/ui/test_main_window.py` ya define `FakeMpvForWindow` y el helper `_window_with_video(qtbot, cache_root=None)`, que construye una `MainWindow` con `video_factory=FakeMpvForWindow`. Se usa tal cual para los tests nuevos.

- [ ] **Step 2: Escribir los tests que fallan**

Agregar a `tests/ui/test_main_window.py`:

```python
def test_scrub_time_label_vacio_sin_clip(qtbot):
    window = _window_with_video(qtbot)
    assert window.scrub_time_label.text() == ""


def test_scrub_time_label_muestra_in_y_out(qtbot):
    window = _window_with_video(qtbot)
    clips = [
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0, in_frame=300, out_frame=900)
    ]
    window.load_clips(clips)
    window._update_scrub_bar()
    text = window.scrub_time_label.text()
    assert "IN 00:00:10" in text
    assert "OUT 00:00:30" in text
    assert "dur 20s" in text


def test_scrub_time_label_sin_in_ni_out_no_muestra_esos_segmentos(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window._update_scrub_bar()
    text = window.scrub_time_label.text()
    assert "IN " not in text
    assert "OUT " not in text
```

- [ ] **Step 3: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -k scrub_time_label -v`
Expected: FAIL con `AttributeError: 'MainWindow' object has no attribute 'scrub_time_label'`

- [ ] **Step 4: Agregar el estilo en `theme.py`**

En `src/clasificador_video/ui/theme.py`, agregar junto a `QLabel#legendLabel, QLabel#statusLabel` (línea ~122):

```python
    QLabel#legendLabel, QLabel#statusLabel, QLabel#scrubTimeLabel {{
        color: {TEXT_MUTED};
        font-size: 11px;
        font-family: {MONO_FONT};
    }}
```

(reemplaza la regla existente `QLabel#legendLabel, QLabel#statusLabel { ... }`, agregando `QLabel#scrubTimeLabel` al selector — no crear una regla nueva separada)

- [ ] **Step 5: Crear el label y ubicarlo en el layout**

En `src/clasificador_video/ui/main_window.py`, después de la línea `self.scrub_bar = ScrubBar()` (línea 220):

```python
        self.scrub_bar = ScrubBar()
        self.scrub_time_label = QLabel("")
        self.scrub_time_label.setObjectName("scrubTimeLabel")
```

En `video_column` (línea ~282-285), agregar el label entre el video y la barra:

```python
        video_column = QVBoxLayout()
        video_column.addWidget(self.subroom_banner)
        video_column.addWidget(self.video_widget, stretch=1)
        video_column.addWidget(self.scrub_time_label)
        video_column.addWidget(self.scrub_bar)
```

- [ ] **Step 6: Implementar el cálculo del texto**

Agregar método nuevo en `main_window.py`, cerca de `_update_scrub_bar` (línea ~404):

```python
    def _update_scrub_time_label(self) -> None:
        clip = self.current_clip
        if clip is None:
            self.scrub_time_label.setText("")
            return
        fps = clip.fps
        parts = []
        if clip.in_frame is not None:
            parts.append(f"IN {format_timecode(clip.in_frame, fps)}")
        if clip.out_frame is not None:
            parts.append(f"OUT {format_timecode(clip.out_frame, fps)}")
        if clip.in_frame is not None and clip.out_frame is not None and fps > 0:
            dur_seconds = abs(clip.out_frame - clip.in_frame) / fps
            parts.append(f"dur {round(dur_seconds)}s")
        position = self.video_widget.player.position
        pos_frame = round(position * fps) if fps > 0 else 0
        parts.append(f"pos {format_timecode(pos_frame, fps)}")
        self.scrub_time_label.setText(" · ".join(parts))
```

Llamarlo desde `_update_scrub_bar` (al final del método, línea ~412) y desde `_tick_playhead` (línea ~417):

```python
    def _update_scrub_bar(self) -> None:
        clip = self.current_clip
        if clip is None:
            self.scrub_bar.set_duration(0.0)
            self.scrub_bar.set_in_out(None, None, 0.0)
            self._update_scrub_time_label()
            return
        duration = self.video_widget.player.duration or self._clip_durations.get(self.current_index, 0.0)
        self.scrub_bar.set_duration(duration)
        self.scrub_bar.set_in_out(clip.in_frame, clip.out_frame, clip.fps)
        self._update_scrub_time_label()

    def _tick_playhead(self) -> None:
        if self.current_clip is None:
            return
        self.scrub_bar.set_position(self.video_widget.player.position)
        self._update_scrub_time_label()
```

Y agregar el import de `format_timecode` en el bloque de imports (línea 40):

```python
from clasificador_video.ui.video_widget import ScrubBar, VideoWidget, format_timecode
```

- [ ] **Step 7: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: PASS (todos, incluyendo los nuevos y los preexistentes)

- [ ] **Step 8: Commit**

```bash
git add src/clasificador_video/ui/main_window.py src/clasificador_video/ui/theme.py tests/ui/test_main_window.py
git commit -m "$(cat <<'EOF'
feat: muestra timecode de IN/OUT/duracion/posicion sobre la scrub bar

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `MpvPlayer.seek()` e `is_paused`

**Files:**
- Modify: `src/clasificador_video/player.py`
- Test: `tests/test_player.py` (ya define `FakeMpv` con `time_pos`, `pause`; no tiene `duration` por defecto, se setea manualmente en el test)

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_player.py`:

```python
def test_seek_setea_time_pos():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.duration = 60.0
    player.seek(15.0)
    assert player._mpv.time_pos == 15.0


def test_seek_clampea_a_cero_si_es_negativo():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.duration = 60.0
    player.seek(-5.0)
    assert player._mpv.time_pos == 0.0


def test_seek_clampea_a_duration_si_excede():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.duration = 60.0
    player.seek(999.0)
    assert player._mpv.time_pos == 60.0


def test_is_paused_refleja_estado_del_mpv():
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert player.is_paused is True  # estado inicial: pause=True
    player.play()
    assert player.is_paused is False
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -k "test_seek_ or is_paused_refleja" -v`
Expected: FAIL con `AttributeError: 'MpvPlayer' object has no attribute 'seek'` (y lo mismo para `is_paused`)

- [ ] **Step 4: Implementar**

En `src/clasificador_video/player.py`, agregar después de `duration` (línea ~65):

```python
    @property
    def is_paused(self) -> bool:
        return bool(self._mpv.pause)

    def seek(self, seconds: float) -> None:
        """Salta a una posicion absoluta, clampeada a [0, duration] -- usado
        por el seek con mouse de la ScrubBar (ver ui/video_widget.py)."""
        target = max(0.0, min(seconds, self.duration))
        self._mpv.time_pos = target
```

- [ ] **Step 5: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -k "test_seek_ or is_paused_refleja or player" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/player.py tests/
git commit -m "$(cat <<'EOF'
feat: MpvPlayer.seek() e is_paused, base para el seek con mouse

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Señales de mouse en ScrubBar

**Files:**
- Modify: `src/clasificador_video/ui/video_widget.py` (clase `ScrubBar`)
- Test: `tests/ui/test_video_widget.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/ui/test_video_widget.py`:

```python
def test_scrub_bar_click_emite_seek_started_y_seek_requested(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.show()
    qtbot.waitExposed(bar)

    with qtbot.waitSignal(bar.seek_started, timeout=1000):
        with qtbot.waitSignal(bar.seek_requested, timeout=1000) as blocker:
            qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(100, 13))
    # x=100 sobre ancho util 188 (left=6, right=194) -> ratio ~0.5 de 60s = ~30s
    assert 25.0 < blocker.args[0] < 35.0


def test_scrub_bar_arrastre_con_boton_apretado_emite_seek_requested(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.show()
    qtbot.waitExposed(bar)
    qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(20, 13))

    with qtbot.waitSignal(bar.seek_requested, timeout=1000) as blocker:
        qtbot.mouseMove(bar, pos=QPoint(180, 13))
    assert blocker.args[0] > 40.0

    qtbot.mouseRelease(bar, Qt.MouseButton.LeftButton, pos=QPoint(180, 13))


def test_scrub_bar_move_sin_boton_no_emite_seek(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.show()
    qtbot.waitExposed(bar)

    received = []
    bar.seek_requested.connect(received.append)
    qtbot.mouseMove(bar, pos=QPoint(100, 13))
    assert received == []


def test_scrub_bar_click_fuera_de_los_bordes_clampea(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 26)
    bar.set_duration(60.0)
    bar.show()
    qtbot.waitExposed(bar)

    with qtbot.waitSignal(bar.seek_requested, timeout=1000) as blocker:
        qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(-50, 13))
    assert blocker.args[0] == 0.0
```

Y agregar los imports necesarios al principio del archivo de test (si no están ya):

```python
from PySide6.QtCore import QPoint, Qt
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -k "seek_started or seek_requested or seek" -v`
Expected: FAIL con `AttributeError: 'ScrubBar' object has no attribute 'seek_started'`

- [ ] **Step 3: Implementar**

En `src/clasificador_video/ui/video_widget.py`, agregar el import de `Qt` (línea 8):

```python
from PySide6.QtCore import QObject, Qt, Signal
```

En la clase `ScrubBar`, agregar las señales a nivel de clase y los handlers de mouse. Agregar después de `class ScrubBar(QWidget):` y su docstring, antes de `__init__` (línea ~146):

```python
    seek_started = Signal()
    seek_requested = Signal(float)

    def __init__(self, parent=None):
```

Agregar un método `_seconds_for_x` (inverso de `_x_for`) después de `_x_for` (línea ~174):

```python
    def _seconds_for_x(self, x: int) -> float:
        if self._duration <= 0:
            return 0.0
        left, right = 6, self.width() - 6
        usable_width = max(right - left, 1)
        ratio = max(0.0, min(1.0, (x - left) / usable_width))
        return ratio * self._duration
```

Agregar los overrides de eventos de mouse, después de `paintEvent` (al final de la clase, línea ~203):

```python
    def mousePressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.button() != Qt.MouseButton.LeftButton or self._duration <= 0:
            return
        self.seek_started.emit()
        self.seek_requested.emit(self._seconds_for_x(round(event.position().x())))

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._duration <= 0:
            return
        self.seek_requested.emit(self._seconds_for_x(round(event.position().x())))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.button() != Qt.MouseButton.LeftButton or self._duration <= 0:
            return
        self.seek_requested.emit(self._seconds_for_x(round(event.position().x())))
```

Actualizar también el docstring de la clase `ScrubBar` (línea ~136-144), que hoy dice explícitamente que no reacciona al mouse:

```python
class ScrubBar(QWidget):
    """Linea de tiempo del clip actual, tipo Source Monitor de Premiere:
    un track con el playhead y, cuando hay marca de in/out, brackets en
    los extremos -- cada uno se dibuja apenas su marcador existe, sin
    esperar al otro -- para que marcar in/out (teclas I/O) se vea en el
    momento, no solo se guarde en silencio.

    Responde a click y arrastre con el mouse (emite `seek_started` al
    empezar el gesto y `seek_requested(seconds)` en cada evento) para
    saltar de posicion como un scrubber real -- pero no conoce a
    MpvPlayer: quien escucha la señal decide que hacer con el player
    (ver MainWindow._on_scrub_seek*). Marcar in/out sigue siendo solo
    con el teclado (I/O/U).
    """
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/video_widget.py tests/ui/test_video_widget.py
git commit -m "$(cat <<'EOF'
feat: ScrubBar emite seek_started/seek_requested con click y arrastre

ScrubBar sigue sin conocer a MpvPlayer -- solo traduce eventos de mouse
a una posicion en segundos. MainWindow decide que hacer con el player
(task siguiente).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Wiring en MainWindow — pausar y hacer seek real

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/ui/test_main_window.py` (usando `_window_with_video` de Task 3):

```python
def test_scrub_bar_seek_started_pausa_el_player(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.video_widget.player.play()
    assert window.video_widget.player.is_paused is False
    window.scrub_bar.seek_started.emit()
    assert window.video_widget.player.is_paused is True


def test_scrub_bar_seek_requested_mueve_el_player_y_la_barra(qtbot):
    window = _window_with_video(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.video_widget.player._mpv.duration = 60.0
    window.scrub_bar.seek_requested.emit(15.0)
    assert window.video_widget.player._mpv.time_pos == 15.0
    assert window.scrub_bar._position == 15.0
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -k "seek_started_pausa or seek_requested_mueve" -v`
Expected: FAIL (la señal no está conectada a nada todavía, `time_pos`/`is_paused` no cambian)

- [ ] **Step 3: Implementar**

En `src/clasificador_video/ui/main_window.py`, después de la línea `self.scrub_bar = ScrubBar()` y la creación de `self.scrub_time_label` (Task 3, línea ~220-222), conectar las señales:

```python
        self.scrub_bar = ScrubBar()
        self.scrub_bar.seek_started.connect(self._on_scrub_seek_started)
        self.scrub_bar.seek_requested.connect(self._on_scrub_seek)
        self.scrub_time_label = QLabel("")
        self.scrub_time_label.setObjectName("scrubTimeLabel")
```

Agregar los métodos nuevos cerca de `_tick_playhead` (línea ~414-418):

```python
    def _on_scrub_seek_started(self) -> None:
        self.video_widget.player.pause()

    def _on_scrub_seek(self, seconds: float) -> None:
        self.video_widget.player.seek(seconds)
        self.scrub_bar.set_position(seconds)
        self._update_scrub_time_label()
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -v`
Expected: PASS (toda la suite, excepto `tests/test_app.py` que se ignora por el cuelgue preexistente documentado)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "$(cat <<'EOF'
feat: seek con mouse funcional -- click/arrastre en la scrub bar mueve el video

Al empezar el gesto se pausa el player; cada movimiento con el boton
apretado hace seek real y actualiza el playhead sin esperar al timer de
150ms.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Verificación visual real

**Files:** ninguno nuevo — usar un script temporal en el scratchpad.

- [ ] **Step 1: Construir un script de verificación**

Crear ``<scratchpad-de-la-sesion>/verify_scrub_bar.py`` (usar el directorio de scratchpad de la sesión activa) que:
1. Construya una `MainWindow` de prueba con un `FakeMpv`/`video_factory` y un `Clip` con `fps=30.0`.
2. Capture y guarde tres PNGs con `window.grab()`:
   - sin in/out marcado,
   - solo `in_frame` marcado (`out_frame=None`),
   - `in_frame` y `out_frame` marcados.
3. Para cada caso, también dejar constancia del texto de `window.scrub_time_label.text()` (imprimirlo a stdout).

- [ ] **Step 2: Correr el script bajo offscreen**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/python /path/al/scratchpad/verify_scrub_bar.py`

- [ ] **Step 3: Leer cada PNG generado con la herramienta de lectura de archivos**

Confirmar visualmente: el bracket de IN aparece solo con `in_frame` puesto (sin esperar OUT), el tramo resaltado solo aparece con ambos, el `scrub_time_label` muestra el texto esperado en cada caso, y nada se ve roto (sin excepciones, sin barra vacía cuando debería tener contenido).

- [ ] **Step 4: Si algo no se ve como se espera, corregir el código de las tasks anteriores antes de seguir**

No hay commit en este task — es solo verificación. Si se encuentra un bug, corregirlo en el archivo correspondiente, volver a correr los tests de esa task, y hacer un commit de fix aparte.

---

### Task 8: Suite completa + limpieza final

**Files:** ninguno nuevo.

- [ ] **Step 1: Correr toda la suite de tests**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q`
Expected: PASS, 0 failures

- [ ] **Step 2: Revisar `git log --oneline -10` y `git status`**

Confirmar que todos los commits de las tasks anteriores están presentes, mensajes en español, y que no queda ningún cambio sin commitear (aparte de este plan y el spec, que ya deberían estar commiteados).

- [ ] **Step 3: Confirmar que no se rompió nada del resto de la app**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q 2>&1 | tail -20`
Expected: el resumen final debe decir "passed" sin "failed" ni "error".
