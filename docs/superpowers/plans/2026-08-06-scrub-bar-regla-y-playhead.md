# Regla de ticks y playhead tipo Premiere — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar una regla de marcas (ticks) basada en tiempo real y un playhead con forma de "casita" (como el Source Monitor de Premiere) a la `ScrubBar`, reemplazando la línea plana y el playhead de línea recta actuales.

**Architecture:** Todo el cambio vive en `ScrubBar.paintEvent` (`video_widget.py`) y una función pura nueva `tick_interval_seconds()` para elegir el intervalo de la regla. Se agregan dos colores nuevos a `theme.py`. El widget pasa de 26px a 34px de alto para que la regla y la casita entren sin pisarse — el resto de la geometría (`track_y = height() // 2`) no cambia de fórmula, solo el resultado numérico al cambiar la altura.

**Tech Stack:** PySide6 (`QPainter`, `QPainterPath`, `QLinearGradient`, `QBrush`), pytest + pytest-qt.

Spec de referencia: `docs/superpowers/specs/2026-08-06-scrub-bar-regla-y-playhead-design.md`

**Nota de implementación respecto al spec:** el spec describe mover `track_y` a "una posición fija cerca de la parte superior". En la práctica, subir la altura del widget a 34px deja suficiente aire arriba (17px con la fórmula `height() // 2` sin cambios) para la regla (9px) y la casita (13px) sin pisarse, y abajo (17px) para los brackets y la línea del playhead. No hace falta mover `track_y` de fórmula — se mantiene `height() // 2`, solo cambia el resultado al aumentar la altura. Esto evita romper la geometría que ya usan los tests existentes (que calculan `track_y` dinámicamente con `bar.height() // 2`, no un número fijo).

---

### Task 1: `tick_interval_seconds()` — elegir el intervalo de la regla

**Files:**
- Modify: `src/clasificador_video/ui/video_widget.py` (función a nivel de módulo, cerca de `format_timecode`)
- Test: `tests/ui/test_video_widget.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/ui/test_video_widget.py`:

```python
def test_tick_interval_duracion_corta_usa_intervalo_chico():
    # 188px usables, 10s -> 188*(i/10)>=48 => i>=2.55 -> primer intervalo de la lista que alcanza es 5
    assert tick_interval_seconds(10.0, 188) == 5.0


def test_tick_interval_duracion_media_usa_intervalo_mayor():
    # 90s -> 188*(i/90)>=48 => i>=22.98 -> 30
    assert tick_interval_seconds(90.0, 188) == 30.0


def test_tick_interval_duracion_muy_larga_cae_al_ultimo_intervalo():
    # 18000s (5 horas) -> ningun intervalo de la lista alcanza 48px, cae al ultimo (3600)
    assert tick_interval_seconds(18000.0, 188) == 3600.0


def test_tick_interval_sin_duracion_devuelve_cero():
    assert tick_interval_seconds(0.0, 188) == 0.0
```

Y actualizar el import al principio del archivo:

```python
from clasificador_video.ui.video_widget import (
    ScrubBar,
    VideoWidget,
    format_timecode,
    tick_interval_seconds,
)
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -k tick_interval -v`
Expected: FAIL con `ImportError` (la función no existe)

- [ ] **Step 3: Implementar**

Agregar en `src/clasificador_video/ui/video_widget.py`, después de `format_timecode` y antes de `class ScrubBar`:

```python
_TICK_INTERVALS_SECONDS = (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600)
_MIN_MAJOR_TICK_SPACING_PX = 48


def tick_interval_seconds(duration: float, usable_width: int) -> float:
    """Elige el intervalo 'prolijo' (1s, 2s, 5s...) mas chico tal que dos
    marcas mayores consecutivas de la regla queden separadas al menos
    _MIN_MAJOR_TICK_SPACING_PX -- para que no se amontonen en clips
    largos ni queden ridiculamente separadas en clips cortos.
    """
    if duration <= 0:
        return 0.0
    for interval in _TICK_INTERVALS_SECONDS:
        if usable_width * (interval / duration) >= _MIN_MAJOR_TICK_SPACING_PX:
            return float(interval)
    return float(_TICK_INTERVALS_SECONDS[-1])
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/video_widget.py tests/ui/test_video_widget.py
git commit -m "$(cat <<'EOF'
feat: tick_interval_seconds() elige el intervalo de la regla de la scrub bar

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Colores de la regla en `theme.py`

**Files:**
- Modify: `src/clasificador_video/ui/theme.py`

- [ ] **Step 1: Agregar las constantes**

En `src/clasificador_video/ui/theme.py`, después de `BORDER = "#333338"`:

```python
BORDER = "#333338"
TICK_MINOR_COLOR = "#3a3a40"
TICK_MAJOR_COLOR = "#55555c"
```

No requiere test propio — son constantes usadas por `ScrubBar` en el Task 3, cubierto ahí.

- [ ] **Step 2: Commit**

```bash
git add src/clasificador_video/ui/theme.py
git commit -m "$(cat <<'EOF'
feat: colores de la regla de ticks en theme.py

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `_major_tick_seconds()` y dibujado de la regla en `ScrubBar`

**Files:**
- Modify: `src/clasificador_video/ui/video_widget.py`
- Test: `tests/ui/test_video_widget.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/ui/test_video_widget.py`:

```python
def test_major_tick_seconds_duracion_corta(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(10.0)
    assert bar._major_tick_seconds() == [0.0, 5.0, 10.0]


def test_major_tick_seconds_duracion_media(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(90.0)
    assert bar._major_tick_seconds() == [0.0, 30.0, 60.0, 90.0]


def test_major_tick_seconds_sin_duracion_devuelve_vacio(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    assert bar._major_tick_seconds() == []


def test_scrub_bar_altura_fija_34(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    assert bar.height() == 34


def test_scrub_bar_dibuja_marca_mayor_en_cada_intervalo(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(10.0)  # intervalo 5s -> marcas mayores en 0s, 5s, 10s
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    track_y = bar.height() // 2
    left, usable = 6, 200 - 12
    x_5s = left + round((5.0 / 10.0) * usable)
    color = img.pixelColor(x_5s, track_y - 8)
    assert color.name() == "#55555c"  # TICK_MAJOR_COLOR
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -k "major_tick or altura_fija or marca_mayor" -v`
Expected: FAIL (`_major_tick_seconds` no existe, altura sigue en 26, no hay marcas dibujadas)

- [ ] **Step 3: Implementar**

En `src/clasificador_video/ui/video_widget.py`, actualizar el import de `theme`:

```python
from clasificador_video.ui.theme import ACCENT, BORDER, TICK_MAJOR_COLOR, TICK_MINOR_COLOR, TRIM_COLOR
```

Cambiar la altura fija en `__init__`:

```python
        self.setFixedHeight(34)
```

Agregar el método `_major_tick_seconds`, después de `_seconds_for_x`:

```python
    def _major_tick_seconds(self) -> list[float]:
        if self._duration <= 0:
            return []
        left, right = 6, self.width() - 6
        usable_width = max(right - left, 1)
        interval = tick_interval_seconds(self._duration, usable_width)
        if interval <= 0:
            return []
        ticks = []
        n = 0
        t = 0.0
        while t <= self._duration + 1e-9:
            ticks.append(t)
            n += 1
            t = interval * n
        return ticks
```

En `paintEvent`, agregar el dibujado de la regla justo después de la línea base (`painter.drawLine(left, track_y, right, track_y)`) y antes del bloque `if self._duration > 0:` que dibuja brackets/playhead -- en realidad va DENTRO de ese bloque, al principio, porque solo tiene sentido con duración > 0. Reemplazar:

```python
        if self._duration > 0:
            in_x = out_x = None
```

por:

```python
        if self._duration > 0:
            major_ticks = self._major_tick_seconds()
            if len(major_ticks) >= 1:
                minor_pen = QPen(QColor(TICK_MINOR_COLOR), 1)
                major_pen = QPen(QColor(TICK_MAJOR_COLOR), 1)
                for i, t in enumerate(major_ticks):
                    tx = self._x_for(t, left, usable_width)
                    painter.setPen(major_pen)
                    painter.drawLine(tx, track_y - 9, tx, track_y)
                    if i + 1 < len(major_ticks):
                        next_t = major_ticks[i + 1]
                        interval = next_t - t
                        painter.setPen(minor_pen)
                        for frac in (1, 2, 3, 4):
                            minor_t = t + interval * frac / 5
                            mx = self._x_for(minor_t, left, usable_width)
                            painter.drawLine(mx, track_y - 5, mx, track_y)

            in_x = out_x = None
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -v`
Expected: PASS (todos, incluyendo los de sesiones anteriores -- `track_y` sigue siendo `height() // 2`, solo cambia el numero al ser 34 en vez de 26, y esos tests lo recalculan dinamicamente)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/video_widget.py tests/ui/test_video_widget.py
git commit -m "$(cat <<'EOF'
feat: regla de marcas (ticks) en la scrub bar, basada en tiempo real

La barra pasa de 26px a 34px de alto para que la regla entre sin
pisar el resto de los elementos.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Playhead tipo "casita"

**Files:**
- Modify: `src/clasificador_video/ui/video_widget.py`
- Test: `tests/ui/test_video_widget.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/ui/test_video_widget.py`:

```python
def test_playhead_ya_no_es_linea_recta_de_punta_a_punta(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(60.0)
    bar.set_position(30.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    left, usable = 6, 200 - 12
    x = left + round((30.0 / 60.0) * usable)
    # cerca del borde superior del widget (y=2) ya no debe haber color ACCENT:
    # el playhead ahora es una casita mas abajo, no una linea que llega hasta arriba
    color_arriba = img.pixelColor(x, 2)
    assert color_arriba.name() != "#ff8a3d"


def test_playhead_tiene_linea_fina_bajando_desde_la_casita(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(60.0)
    bar.set_position(30.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    left, usable = 6, 200 - 12
    x = left + round((30.0 / 60.0) * usable)
    track_y = bar.height() // 2
    # la linea fina baja desde track_y hasta cerca del final del widget
    color_abajo = img.pixelColor(x, track_y + 10)
    assert color_abajo.name() == "#ff8a3d"


def test_playhead_punta_toca_track_y_en_la_posicion_correcta(qtbot):
    bar = ScrubBar()
    qtbot.addWidget(bar)
    bar.resize(200, 34)
    bar.set_duration(60.0)
    bar.set_position(30.0)
    bar.show()
    qtbot.waitExposed(bar)
    pixmap = bar.grab()
    img = pixmap.toImage()
    left, usable = 6, 200 - 12
    x = left + round((30.0 / 60.0) * usable)
    track_y = bar.height() // 2
    color_punta = img.pixelColor(x, track_y - 1)
    assert color_punta.name() == "#ff8a3d"
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -k playhead -v`
Expected: FAIL (`test_playhead_ya_no_es_linea_recta...` falla porque hoy SI es una linea recta que llega a y=2)

- [ ] **Step 3: Implementar**

En `src/clasificador_video/ui/video_widget.py`, agregar el import de `QPainterPath`, `QLinearGradient`, `QBrush`:

```python
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QOpenGLContext, QPainter, QPainterPath, QPen
```

Agregar el método `_playhead_path`, después de `_major_tick_seconds`:

```python
    def _playhead_path(self, x: float, track_y: int) -> QPainterPath:
        half = 6.5
        body_h = 7
        point_h = 6
        r = 2.5
        body_bottom = track_y - point_h
        body_top = body_bottom - body_h
        path = QPainterPath()
        path.moveTo(x - half + r, body_top)
        path.lineTo(x + half - r, body_top)
        path.quadTo(x + half, body_top, x + half, body_top + r)
        path.lineTo(x + half, body_bottom)
        path.lineTo(x, track_y)
        path.lineTo(x - half, body_bottom)
        path.lineTo(x - half, body_top + r)
        path.quadTo(x - half, body_top, x - half + r, body_top)
        path.closeSubpath()
        return path
```

Reemplazar el bloque final del playhead en `paintEvent`:

```python
            x = self._x_for(self._position, left, usable_width)
            painter.setPen(QPen(QColor(ACCENT), 2))
            painter.drawLine(x, 2, x, self.height() - 2)
```

por:

```python
            x = self._x_for(self._position, left, usable_width)
            playhead_path = self._playhead_path(x, track_y)
            gradient = QLinearGradient(0, track_y - 13, 0, track_y)
            gradient.setColorAt(0.0, QColor("#ff9d5c"))
            gradient.setColorAt(1.0, QColor(ACCENT))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawPath(playhead_path)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(ACCENT), 1))
            painter.drawLine(round(x), track_y, round(x), self.height() - 2)
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_video_widget.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Correr toda la suite**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q`
Expected: PASS, 0 failures

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/video_widget.py tests/ui/test_video_widget.py
git commit -m "$(cat <<'EOF'
feat: playhead con forma de casita, tipo Premiere, con degradado sutil

Reemplaza la linea recta de punta a punta por un marcador apoyado
sobre la regla (cuerpo redondeado + punta exacta en la posicion) mas
una linea fina que baja por el resto del track.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Verificación visual real

**Files:** ninguno nuevo — reusar/extender el script de verificación de la sesión anterior.

- [ ] **Step 1: Adaptar el script de verificación existente**

Reusar `verify_scrub_bar.py` del scratchpad de la sesión anterior (o recrearlo si no existe más) agregando casos con distintas duraciones para ver la regla adaptarse:

```python
cases = [
    ("corta_sin_marcar", 10.0, None, None),
    ("corta_solo_in", 10.0, 30, None),
    ("media_in_y_out", 90.0, 300, 2400),
]
```

Ajustar el script para que `FakeMpv.duration` tome el valor de cada caso (hoy está fijo en 60.0) y que llame `window._tick_playhead()` tras `window._playhead_timer.stop()` como en la sesión anterior, para que el playhead se dibuje en una posición determinística.

- [ ] **Step 2: Correr el script y leer los PNG generados**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/python <path-al-script>`

Leer cada PNG con la herramienta de lectura de archivos. Confirmar: la regla tiene más marcas mayores separadas en el clip corto (10s) que en el medio (90s) — el intervalo elegido debe ser visiblemente distinto; el playhead se ve como una casita con degradado, no como una línea recta; los brackets de IN/OUT siguen viéndose bien con la nueva altura de 34px.

- [ ] **Step 3: Si algo no se ve como se espera, corregir antes de seguir**

No hay commit en este task — es solo verificación. Si aparece un bug, corregirlo en el archivo correspondiente, re-correr los tests de esa task, y commitear el fix aparte.

---

### Task 6: Limpieza final

- [ ] **Step 1: Correr toda la suite**

Run: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q`
Expected: PASS, 0 failures

- [ ] **Step 2: Revisar `git log --oneline -10` y `git status`**

Confirmar que los commits de las tasks anteriores están presentes y que no queda nada sin commitear.
