# Diseño Visual de la App Externa — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Llevar la app del Clasificador de Video (ya funcional, 124 pruebas en verde) del estilo por defecto de Qt (gris claro, sin tema) al diseño oscuro y pulido que Bruno aprobó en la sesión de brainstorming del 2026-08-06 — y corregir un bug real de tamaño de miniaturas que agrava el problema.

**Contexto — por qué existe este plan:** El plan anterior (`docs/superpowers/plans/2026-08-06-app-externa-clasificador.md`, ya ejecutado, ver `docs/superpowers/archive/INFORME-2026-08-06-app-externa-fases-1-2.md`) construyó toda la lógica y la estructura de la ventana correctamente, pero **nunca incluyó una tarea de estilo visual** — ese fue un hueco del plan, no un error de quien lo ejecutó. Bruno vio la app resultante y no le gustó: se ve como una app de Qt genérica (gris por defecto), no como el diseño oscuro que aprobó en los mockups. Este plan cierra ese hueco.

**Arquitectura:** Un solo módulo de tema (`src/clasificador_video/ui/theme.py`) con los colores y una función `build_stylesheet()` que devuelve un QSS (el CSS de Qt) aplicado **una vez, globalmente**, sobre `QApplication` — no estilos dispersos widget por widget. Los widgets existentes solo necesitan `setObjectName(...)` para que el QSS los distinga entre sí (ej. distinguir el botón de exportar del resto de los botones). Además, un bug real de tamaño de miniaturas: las miniaturas se extraen a la resolución nativa del clip (hasta 2160×3840 en vertical) y se ponen en el `QLabel` sin escalar ni limitar tamaño — el filmstrip probablemente se ve roto/gigante por esto, independientemente del tema.

**Tech Stack:** PySide6 (QSS — el subconjunto de CSS que soporta Qt), pytest, pytest-qt.

**Fuente de verdad del diseño (colores, layout, espaciado):** los mockups aprobados por Bruno durante el brainstorming, archivos HTML en `.superpowers/brainstorm/70942-1785996102/content/`:
- `preview-final.html` — pantalla completa combinada (la referencia principal de esta tarea).
- `config-cuartos.html` — diálogo de configurar cuartos.
- `estado-clip.html` — opción A de estado visual del filmstrip (ya implementada en código, ver §4 de abajo).

Ábrelos en un navegador (`open .superpowers/brainstorm/70942-1785996102/content/preview-final.html`) para ver el diseño exacto antes de escribir QSS — los valores de color de este plan ya están extraídos de ahí, pero el mockup te da el contexto visual completo.

---

## Antes de empezar: hay trabajo sin comitear en el repo

Al momento de escribir este plan, `git status` muestra cambios sin comitear en `app.py`, `autosave.py`, `ui/filmstrip.py`, `ui/main_window.py`, `ui/room_config_dialog.py`, `ui/video_widget.py` y sus tests — correcciones reales, ya verificadas (`pytest -v` pasa con ellas aplicadas: 124 passed). Este plan **asume esos cambios ya comiteados** como punto de partida.

### Task 0: Comitear el trabajo pendiente antes de empezar el diseño visual

**Files:** los listados arriba (ya modificados en el working tree, no hay que escribir nada nuevo).

- [ ] **Step 1: Confirmar que la suite pasa con los cambios actuales**

Run: `.venv/bin/pytest -v`
Expected: `124 passed` (o más, si algo se agregó después), 0 failures. Si hay failures, detente y arregla eso antes de seguir — no construyas el diseño visual sobre una base rota.

- [ ] **Step 2: Revisar el diff para confirmar que son correcciones reales, no experimentos a medias**

Run: `git diff`
Expected: cambios como manejo de `OSError` en autoguardado, `mkdir` del directorio padre antes de escribir sesión, conectar el botón de "Empezar a clasificar" del diálogo a `accept()`, ajuste del embedding de mpv por `wid`, y el formato de borde del filmstrip (`border: 2px solid <color>` en vez de `border-color: <color>`). Si ves algo que no reconoces como una corrección intencional, pregúntale a Bruno antes de comitear.

- [ ] **Step 3: Comitear**

```bash
git add src/clasificador_video/app.py src/clasificador_video/autosave.py \
  src/clasificador_video/ui/filmstrip.py src/clasificador_video/ui/main_window.py \
  src/clasificador_video/ui/room_config_dialog.py src/clasificador_video/ui/video_widget.py \
  tests/ui/test_filmstrip.py tests/ui/test_main_window.py
git commit -m "fix: correcciones pendientes de fase 2 (autoguardado, embedding, dialogo, bordes)"
```

---

## Milestone 1 — Módulo de tema y estilo global

### Task 1: `theme.py` con los colores del diseño aprobado y el QSS global

**Files:**
- Create: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_theme.py`

Colores extraídos de los mockups aprobados (`preview-final.html`, `config-cuartos.html`) — no inventar valores nuevos:

| Constante | Valor | Uso en el mockup |
|---|---|---|
| `BG_WINDOW` | `#1a1a1e` | Fondo general de la ventana (`.app`) |
| `BG_PANEL` | `#232327` | Paneles: lista de cuartos, filmstrip, leyenda, ingest |
| `BG_ACTIVE` | `#3a5a8c` | Chip de cuarto activado, ítem de lista seleccionado |
| `BG_HOVER` | `#2c2c32` | Hover de botones (no está en el mockup estático, extrapolado por consistencia) |
| `ACCENT` | `#5b9bff` | Botón principal ("Empezar a clasificar", rango de in/out) |
| `TEXT` | `#dddddd` | Texto principal |
| `TEXT_MUTED` | `#8a8a8a` | Leyenda de teclado, metadatos, nombre de cuarto bajo la miniatura |
| `BORDER` | `#333333` | Bordes sutiles de inputs |
| `PICK_COLOR` | `#3bb273` | Ya existe en `filmstrip.py` — reusar el mismo valor, no redefinir uno nuevo |
| `REJECT_COLOR` | `#e0556f` | Ya existe en `filmstrip.py` — reusar |
| `CURRENT_COLOR` | `#2b7fff` | Ya existe en `filmstrip.py` — reusar |

- [ ] **Step 1: Write the failing tests**

```python
# tests/ui/test_theme.py
from clasificador_video.ui.theme import BG_WINDOW, BG_PANEL, ACCENT, build_stylesheet


def test_build_stylesheet_incluye_el_fondo_oscuro_de_la_ventana():
    qss = build_stylesheet()
    assert f"background-color: {BG_WINDOW}" in qss


def test_build_stylesheet_estiliza_los_paneles():
    qss = build_stylesheet()
    assert f"background-color: {BG_PANEL}" in qss


def test_build_stylesheet_da_estilo_al_boton_principal():
    qss = build_stylesheet()
    assert "QPushButton#startButton" in qss
    assert "QPushButton#exportButton" in qss
    assert ACCENT in qss


def test_build_stylesheet_da_fondo_negro_al_video():
    qss = build_stylesheet()
    assert "QWidget#videoWidget" in qss
    assert "background-color: black" in qss


def test_build_stylesheet_es_una_sola_cadena_no_vacia():
    qss = build_stylesheet()
    assert isinstance(qss, str)
    assert len(qss) > 100
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_theme.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.ui.theme'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/theme.py
from __future__ import annotations

BG_WINDOW = "#1a1a1e"
BG_PANEL = "#232327"
BG_ACTIVE = "#3a5a8c"
BG_HOVER = "#2c2c32"
ACCENT = "#5b9bff"
TEXT = "#dddddd"
TEXT_MUTED = "#8a8a8a"
BORDER = "#333333"

# Reusados tal cual de clasificador_video.ui.filmstrip -- no redefinir con
# otro valor, son el mismo color en dos lugares del codigo.
PICK_COLOR = "#3bb273"
REJECT_COLOR = "#e0556f"
CURRENT_COLOR = "#2b7fff"


def build_stylesheet() -> str:
    """QSS global (diseno aprobado en preview-final.html / config-cuartos.html
    del brainstorming 2026-08-06). Se aplica una sola vez sobre QApplication
    -- los widgets individuales solo necesitan setObjectName() para que los
    selectores de aqui los alcancen.
    """
    return f"""
    QWidget {{
        background-color: {BG_WINDOW};
        color: {TEXT};
        font-size: 13px;
    }}

    QListWidget {{
        background-color: {BG_PANEL};
        border: none;
        border-radius: 6px;
        padding: 6px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: 4px;
        margin-bottom: 2px;
    }}
    QListWidget::item:selected {{
        background-color: {BG_ACTIVE};
    }}

    QPushButton {{
        background-color: {BG_PANEL};
        border: none;
        border-radius: 6px;
        padding: 8px 14px;
        color: {TEXT};
    }}
    QPushButton:hover {{
        background-color: {BG_HOVER};
    }}
    QPushButton:checked {{
        background-color: {BG_ACTIVE};
    }}

    QPushButton#startButton, QPushButton#exportButton {{
        background-color: {ACCENT};
        color: white;
        font-weight: 600;
        padding: 10px 16px;
    }}
    QPushButton#startButton:hover, QPushButton#exportButton:hover {{
        background-color: #4a89e8;
    }}

    QComboBox, QLineEdit {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 5px;
        padding: 4px 8px;
        color: {TEXT};
    }}

    QLabel#legendLabel, QLabel#statusLabel {{
        color: {TEXT_MUTED};
        font-size: 11px;
    }}
    QLabel#clipRoomLabel {{
        color: {TEXT_MUTED};
        font-size: 10px;
    }}
    QLabel#panelTitle {{
        color: {TEXT_MUTED};
        font-size: 11px;
        text-transform: uppercase;
        font-weight: 600;
    }}

    QWidget#videoWidget {{
        background-color: black;
        border-radius: 6px;
    }}

    QWidget#filmstripPanel, QWidget#roomColumn {{
        background-color: {BG_PANEL};
        border-radius: 6px;
    }}
    """
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_theme.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/theme.py tests/ui/test_theme.py
git commit -m "feat: modulo de tema oscuro con los colores del diseno aprobado"
```

### Task 2: Aplicar el stylesheet global y la fuente base en `app.py`

**Files:**
- Modify: `src/clasificador_video/app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing test**

Lee primero `tests/test_app.py` existente para no romper sus pruebas actuales, y agrega esta:

```python
# agregar a tests/test_app.py
def test_main_aplica_el_stylesheet_global(qtbot, monkeypatch):
    from PySide6.QtWidgets import QApplication
    import clasificador_video.app as app_module

    monkeypatch.setattr(app_module, "arrancar", lambda **kw: None)
    monkeypatch.setattr("sys.exit", lambda code=0: None)

    app_module.main()

    app = QApplication.instance()
    assert "background-color: #1a1a1e" in app.styleSheet()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_app.py -v -k stylesheet`
Expected: FAIL — `app.styleSheet()` está vacío (no se aplicó ningún QSS todavía)

- [ ] **Step 3: Implement**

En `src/clasificador_video/app.py`, importa `build_stylesheet` y aplícalo justo después de crear `QApplication`. Usa `QApplication.instance() or QApplication(sys.argv)` en vez de construirlo directo: `pytest-qt` ya deja una instancia de `QApplication` viva durante las pruebas, y Qt no permite crear una segunda en el mismo proceso — sin este guard, el test del Step 1 revienta con `RuntimeError` en vez de fallar limpio por el stylesheet vacío.

```python
from clasificador_video.ui.theme import build_stylesheet

def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    window = arrancar()
    if window is None:
        sys.exit(0)
    window.show()
    if window.clips:
        try:
            window.video_widget.open_clip(window.clips[0].ruta)
        except RuntimeError:
            pass
    sys.exit(app.exec())
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_app.py -v`
Expected: todas las pruebas de `test_app.py` pasan, incluida la nueva.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "feat: aplicar el tema oscuro globalmente a la aplicacion"
```

---

## Milestone 2 — Conectar los widgets reales al tema (`setObjectName`)

El QSS de `theme.py` ya tiene selectores por `objectName` (`#startButton`, `#videoWidget`, etc.) — esta milestone solo pone esos nombres en los widgets reales. Sin esto, el QSS global de todos modos pinta el fondo oscuro y los colores base (porque `QWidget { ... }` alcanza a todo), pero los botones/paneles especiales no se distinguen entre sí.

### Task 3: `objectName` en `MainWindow`

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing test**

```python
# agregar a tests/ui/test_main_window.py
def test_widgets_clave_tienen_objectname_para_el_tema(qtbot):
    window = _window(qtbot)
    assert window.video_widget.objectName() == "videoWidget"
    assert window.export_button.objectName() == "exportButton"
    assert window.legend_label.objectName() == "legendLabel"
    assert window.status_label.objectName() == "statusLabel"
```

(Usa el helper `_window(qtbot)` que ya existe en ese archivo de pruebas — no lo dupliques.)

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v -k objectname`
Expected: FAIL — `objectName()` devuelve cadena vacía

- [ ] **Step 3: Implement**

En `src/clasificador_video/ui/main_window.py`, dentro de `__init__`, justo después de crear cada widget correspondiente, agrega:

```python
self.video_widget.setObjectName("videoWidget")
self.export_button.setObjectName("exportButton")
self.legend_label.setObjectName("legendLabel")
self.status_label.setObjectName("statusLabel")
```

Y para los dos paneles agrupados (columna de cuartos y filmstrip), envuelve el layout de la columna en un `QWidget` con nombre, ya que `theme.py` estiliza `QWidget#roomColumn` y `QWidget#filmstripPanel` (un `QVBoxLayout`/`QHBoxLayout` suelto no tiene `objectName` propio):

```python
from PySide6.QtWidgets import QWidget as _QWidget  # ya esta importado QWidget arriba, usar el mismo

room_column_widget = QWidget()
room_column_widget.setObjectName("roomColumn")
room_column_widget.setLayout(column)  # `column` es el QVBoxLayout ya existente con cuartos+ingest

center = QHBoxLayout()
center.addWidget(room_column_widget, stretch=0)
center.addWidget(self.video_widget, stretch=1)
```

(Ajusta esto al código real que ya existe — la idea es envolver el `QVBoxLayout column` en un `QWidget` nombrado antes de meterlo en `center`, en vez de agregar el layout directo.)

Para el filmstrip, dale el nombre directo al widget `Filmstrip` (ya es un `QWidget`, no hace falta envolverlo):

```python
self.filmstrip.setObjectName("filmstripPanel")
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: todas pasan, incluida la nueva.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: nombrar widgets clave de la ventana principal para el tema"
```

### Task 4: `objectName` en `RoomConfigDialog` y estado visual de los chips

Los chips ya son `QPushButton` con `setCheckable(True)` — Qt aplica el selector `:checked` de forma nativa, no hace falta ninguna propiedad extra. Este task solo nombra el botón principal.

**Files:**
- Modify: `src/clasificador_video/ui/room_config_dialog.py`
- Test: `tests/ui/test_room_config_dialog.py`

- [ ] **Step 1: Write the failing test**

```python
# agregar a tests/ui/test_room_config_dialog.py
def test_boton_de_empezar_tiene_objectname_de_boton_principal(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    assert dialog.start_button.objectName() == "startButton"


def test_chip_se_marca_checked_al_hacer_click(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    dialog.chip_buttons["Cocina"].click()
    assert dialog.chip_buttons["Cocina"].isChecked() is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_room_config_dialog.py -v`
Expected: FAIL en `test_boton_de_empezar_tiene_objectname_de_boton_principal` (objectName vacío). La segunda prueba probablemente ya pasa (los `QPushButton` checkable se marcan solos al hacer click) — si ya pasa, déjala como prueba de regresión, no la borres.

- [ ] **Step 3: Implement**

En `src/clasificador_video/ui/room_config_dialog.py`, justo después de `self.start_button = QPushButton(...)`:

```python
self.start_button.setObjectName("startButton")
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_room_config_dialog.py -v`
Expected: todas pasan.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/room_config_dialog.py tests/ui/test_room_config_dialog.py
git commit -m "feat: nombrar el boton principal del dialogo de cuartos para el tema"
```

---

## Milestone 3 — Corregir el bug real de tamaño de miniaturas

**Este no es un ajuste cosmético — es un bug funcional.** `extract_thumbnail` (del plan anterior) extrae el frame a la resolución nativa del clip (hasta 2160×3840 en vertical). `_ClipItemWidget.set_pixmap` pone ese pixmap directo en un `QLabel` sin escalar ni fijar tamaño — cada miniatura del filmstrip se muestra a tamaño completo. Con clips verticales 4K, cada ítem del filmstrip mide miles de píxeles de alto. Esto probablemente rompe el layout de toda la ventana, independientemente del tema visual.

### Task 5: Escalar las miniaturas a una altura fija, preservando el aspecto

**Files:**
- Modify: `src/clasificador_video/ui/filmstrip.py`
- Test: `tests/ui/test_filmstrip.py`

- [ ] **Step 1: Write the failing test**

```python
# agregar a tests/ui/test_filmstrip.py
from PySide6.QtGui import QPixmap


def test_miniatura_grande_se_escala_a_altura_fija(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])

    pixmap_vertical_4k = QPixmap(2160, 3840)
    strip.item_widgets[0].set_pixmap(pixmap_vertical_4k)

    shown = strip.item_widgets[0]._image_label.pixmap()
    assert shown.height() == 80
    assert shown.width() < 2160  # se escalo, no quedo al tamaño original


def test_miniatura_horizontal_tambien_respeta_la_altura_fija(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="X", flag="none")])

    pixmap_horizontal_4k = QPixmap(3840, 2160)
    strip.item_widgets[0].set_pixmap(pixmap_horizontal_4k)

    shown = strip.item_widgets[0]._image_label.pixmap()
    assert shown.height() == 80
    assert shown.width() <= 140  # tope maximo de ancho, no se deja crecer sin limite
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_filmstrip.py -v -k miniatura`
Expected: FAIL — `shown.height()` es 3840 o 2160 (sin escalar), no 80.

- [ ] **Step 3: Implement**

En `src/clasificador_video/ui/filmstrip.py`, agrega el import de `Qt` y las constantes de tamaño, y reescribe `set_pixmap`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

PICK_COLOR = "#3bb273"
REJECT_COLOR = "#e0556f"
CURRENT_COLOR = "#2b7fff"

THUMB_HEIGHT = 80
THUMB_MAX_WIDTH = 140
```

```python
class _ClipItemWidget(QWidget):
    def __init__(self, clip: ClipThumbnail):
        super().__init__()
        self._flag = clip.flag
        layout = QVBoxLayout(self)
        self._image_label = QLabel()
        self._image_label.setFixedHeight(THUMB_HEIGHT)
        self._image_label.setObjectName("clipThumbnail")
        if clip.thumbnail_path is not None:
            self._image_label.setText("")
        else:
            self._image_label.setText("(sin miniatura)")
        layout.addWidget(self._image_label)
        self._room_label = QLabel(clip.room_label)
        self._room_label.setObjectName("clipRoomLabel")
        layout.addWidget(self._room_label)

    def set_pixmap(self, pixmap) -> None:
        scaled = pixmap.scaled(
            THUMB_MAX_WIDTH, THUMB_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._image_label.setPixmap(scaled)
        self._image_label.setFixedWidth(scaled.width())
```

(El resto de la clase — `has_pixmap`, `set_visual_state` — no cambia.)

**Nota para quien implemente:** no intentes redondear las esquinas de la miniatura con `border-radius` en el `QLabel` — en Qt eso no recorta el pixmap dibujado dentro, solo el fondo del label (que aquí no se ve, porque está cubierto por la imagen). Sería trabajo extra (una máscara o un `QPainterPath` custom) sin el respaldo del spec ni de Bruno para justificarlo — se queda con esquina cuadrada.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_filmstrip.py -v`
Expected: todas pasan, incluidas las nuevas.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/filmstrip.py tests/ui/test_filmstrip.py
git commit -m "fix: escalar miniaturas del filmstrip a altura fija (bug real, no eran solo feas)"
```

---

## Milestone 4 — Detalles finales

### Task 6: Fondo negro del reproductor antes de que mpv dibuje encima

Sin esto, el `VideoWidget` puede mostrar blanco/gris por defecto de Qt en el instante entre que la ventana aparece y mpv termina de adjuntarse a su `wid` — un parpadeo visible.

**Files:**
- Modify: `src/clasificador_video/ui/video_widget.py`
- Test: `tests/ui/test_video_widget.py`

- [ ] **Step 1: Write the failing test**

```python
# agregar a tests/ui/test_video_widget.py
def test_video_widget_tiene_objectname_para_fondo_negro(qtbot):
    widget = VideoWidget(mpv_factory=lambda **kw: object())
    qtbot.addWidget(widget)
    assert widget.objectName() == "videoWidget"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_video_widget.py -v -k objectname`
Expected: FAIL — objectName vacío

- [ ] **Step 3: Implement**

En `src/clasificador_video/ui/video_widget.py`, dentro de `__init__`, después de `super().__init__(parent)`:

```python
self.setObjectName("videoWidget")
```

**Nota:** esto puede parecer redundante con el Task 3 (que ya le pone `objectName("videoWidget")` al `video_widget` desde `MainWindow`) — déjalo en ambos lugares de todas formas: aquí garantiza el fondo negro incluso si alguien crea un `VideoWidget` fuera de `MainWindow` (por ejemplo, en una prueba o en una ventana futura), y no hace daño que `MainWindow` lo repita.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_video_widget.py -v`
Expected: todas pasan.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/video_widget.py tests/ui/test_video_widget.py
git commit -m "fix: fondo negro del VideoWidget desde su propia clase, sin depender de quien lo crea"
```

### Task 7: Título de sección en la columna de cuartos ("Cuartos")

En el mockup (`preview-final.html`), el nombre del proyecto va en una barra superior discreta, no como título gigante. La columna de cuartos ya tiene un `QLabel("Cuartos")` (ver `main_window.py`) — solo falta el estilo de "título de panel" ya definido en `theme.py` (`QLabel#panelTitle`).

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing test**

```python
# agregar a tests/ui/test_main_window.py
def test_titulo_de_la_columna_de_cuartos_tiene_objectname_de_panel(qtbot):
    window = _window(qtbot)
    assert window.room_title_label.objectName() == "panelTitle"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v -k panel_title`
Expected: FAIL — `window` no tiene atributo `room_title_label` (hoy el `QLabel("Cuartos")` se crea inline dentro de `column.addWidget(QLabel("Cuartos"))`, sin guardarse como atributo)

- [ ] **Step 3: Implement**

En `src/clasificador_video/ui/main_window.py`, donde hoy dice:

```python
column.addWidget(QLabel("Cuartos"))
```

cámbialo por:

```python
self.room_title_label = QLabel("Cuartos")
self.room_title_label.setObjectName("panelTitle")
column.addWidget(self.room_title_label)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: todas pasan.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: estilo de titulo de panel para el encabezado de la columna de cuartos"
```

---

## Verificación final (esto sí requiere que Bruno mire la pantalla)

Ninguna prueba automática puede confirmar que el diseño "se ve bien" — las pruebas de este plan solo confirman que el QSS correcto se aplica y que las miniaturas ya no rompen el layout. La confirmación visual final es de Bruno, no de quien ejecuta este plan.

- [ ] **Step 1: Abrir la app con material real**

```bash
.venv/bin/python -m clasificador_video.app
```

Importar una carpeta con clips de `TEST/` (recordando que son de 2-6 segundos, suficiente para ver el filmstrip poblado).

- [ ] **Step 2: Comparar contra el mockup**

Abrir `.superpowers/brainstorm/70942-1785996102/content/preview-final.html` en un navegador al lado de la app. Confirmar: fondo oscuro consistente, columna de cuartos con panel diferenciado, filmstrip con miniaturas de tamaño razonable (no gigantes), botón de exportar/empezar en azul de acento, leyenda de teclado en texto pequeño y discreto.

- [ ] **Step 3: Dejar un mensaje corto para Bruno**

Si algo no coincide con el mockup a pesar de seguir este plan al pie de la letra, documentarlo en un informe corto (mismo formato que `docs/superpowers/archive/INFORME-2026-08-06-app-externa-fases-1-2.md`) en vez de improvisar cambios de diseño no cubiertos aquí — decisiones de diseño nuevas las toma Bruno o una sesión de brainstorming, no se improvisan a mitad de un plan de implementación.
