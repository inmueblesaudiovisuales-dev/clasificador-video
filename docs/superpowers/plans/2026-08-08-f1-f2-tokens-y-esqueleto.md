# F1 y F2 del rediseño — Tokens y Esqueleto — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar la app con la paleta y la estructura del mockup, sin restos del
diseño viejo y sin perder ninguna función que hoy sirva. Al terminar la F2, un
clip vertical debe medir ~529 px de ancho en una ventana de 1600×1000 (hoy mide
328) y no debe quedar ninguna banda horizontal fuera de la barra de título y la
de estado.

**Architecture:** La F1 convierte `ui/theme.py` en la única fuente de valores
visuales (colores, dimensiones, radios, tipografía) tomados del mockup, y agrega
un arnés de comparación que renderiza mockup y app al mismo tamaño en una sola
imagen. La F2 descompone la ventana monolítica actual (`ui/main_window.py`, 783
renglones) en widgets con una responsabilidad cada uno —`TitleBar`, `RoomRail`,
`VideoStage`, `ToolColumn`, `ClipSheet`, `StatusBar`— y reconstruye
`MainWindow` como ensamblador. Los controles del video pasan a ser hijos del
`VideoWidget`, posicionados por un filtro de eventos, según lo validado en la
F0. El ancho del video lo dicta la relación de aspecto del clip; los paneles
absorben el resto, así que no quedan franjas negras.

**Tech Stack:** PySide6 6.11 (QWidget, QOpenGLWidget, QPainter, QSS, QFont,
QWebEngineView para el arnés), pytest + pytest-qt (`qtbot`), python-mpv (con
`FakeMpv` como doble en tests).

**Referencias:**
- Mockup: `docs/superpowers/mockups/rediseno-2026-08-08/mockup.html`
- Decisiones de diseño: `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`
- Diagnóstico: `docs/superpowers/ANALISIS-2026-08-08-app-actual-vs-mockup.md`
- Plan maestro y mecanismos anti-deriva: `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md`

**Comando de tests** (de `CLAUDE.md`, `tests/test_app.py` se excluye por su
cuelgue preexistente bajo `offscreen`):

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q
```

---

## Advertencias antes de empezar

1. **Al terminar la F1 la app se va a ver peor.** Paleta nueva sobre layout
   viejo. Es esperado, dura una fase y no se "arregla" tocando colores.
2. **La F2 sí se parte en commits; lo que no se parte es lo que ve el
   usuario.** Las Tasks 2 a 8 crean archivos nuevos que todavía nadie usa: cada
   una puede ser su propio commit verde sin cambiar en nada la app que corre.
   La atómica es la **Task 9**, que ensambla la ventana nueva y borra la vieja
   en un solo commit. Así el trabajo queda revisable por partes sin vivir ni un
   día en el híbrido de "mitad viejo, mitad nuevo".
3. **Ningún archivo nuevo va a la raíz.** Widgets a `src/clasificador_video/ui/`,
   el arnés a `scripts/`, temporales al scratchpad de la sesión.
4. **Nada de features nuevas.** La F2 porta lo que ya funciona. Filtros,
   historial, modo hoja, pincel, autoplay y destacado son fases posteriores.
5. Los valores hexadecimales de este plan **se copian tal cual**. Vienen del
   `:root` del mockup y son la definición de "igual al mockup".

---

# FASE 1 — Tokens y arnés

### Task 1: Tokens de diseño en `theme.py`

**Files:**
- Modify: `src/clasificador_video/ui/theme.py:1-56` (bloque de constantes)
- Test: `tests/ui/test_theme.py`

Los nombres que hoy importan otros módulos (`ACCENT`, `BORDER`,
`TICK_MINOR_COLOR`, `TICK_MAJOR_COLOR`, `PICK_COLOR`, `REJECT_COLOR`,
`CURRENT_COLOR`, `TRIM_COLOR`, `ROOM_PALETTE`, `MONO_FONT`, `BG_WINDOW`,
`BG_PANEL`, `BG_RAIL`, `BG_HOVER`, `BG_ACTIVE`, `TEXT`, `TEXT_MUTED`)
**se conservan** para que la app siga corriendo durante la F1. Cambian de valor,
no de nombre. Los alias se borran al final de la F2 (Task 9 de la F2).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_theme.py  (agregar al archivo existente)
from clasificador_video.ui import theme


def test_tokens_de_superficie_son_los_del_mockup():
    assert theme.BG_APP == "#0a0b0d"
    assert theme.BG_SURFACE_0 == "#101216"
    assert theme.BG_SURFACE_1 == "#16191e"
    assert theme.BG_SURFACE_2 == "#1d2128"
    assert theme.LINE == "#262b33"
    assert theme.LINE_SOFT == "#1e222a"


def test_tokens_de_texto_son_los_del_mockup():
    assert theme.TEXT == "#e6e9ee"
    assert theme.TEXT_2 == "#9aa3b0"
    assert theme.TEXT_3 == "#626b78"


def test_tokens_de_estado_son_los_del_mockup():
    assert theme.PICK_COLOR == "#55c08a"
    assert theme.STAR_COLOR == "#7ee6b0"
    assert theme.REJECT_COLOR == "#d4696c"
    assert theme.CURRENT_COLOR == "#e8a33d"
    assert theme.TRIM_COLOR == "#6d8cf5"


def test_accent_sigue_existiendo_y_apunta_al_color_de_clip_actual():
    """`ui/video_widget.py` importa ACCENT; no se rompe durante la F1."""
    assert theme.ACCENT == theme.CURRENT_COLOR


def test_paleta_de_cuartos_tiene_nueve_colores_del_mockup():
    assert theme.ROOM_PALETTE == [
        "#c0885a", "#6d8ca8", "#8b7ca8", "#4f9a8e", "#7e9e5e",
        "#3e9bc0", "#a9836f", "#b26f86", "#7c8794",
    ]


def test_room_color_es_estable_y_da_la_vuelta():
    assert theme.room_color(0) == "#c0885a"
    assert theme.room_color(9) == theme.room_color(0)


def test_dimensiones_fijas_del_mockup():
    assert theme.TITLEBAR_HEIGHT == 36
    assert theme.STATUSBAR_HEIGHT == 24
    assert theme.RAIL_WIDTH == 200
    assert theme.TOOLCOL_WIDTH == 56
    assert theme.SHEET_MIN_WIDTH == 340


def test_escala_tipografica_es_entera():
    """QSS interpreta mal los tamanos fraccionarios de fuente: se fijan
    enteros para que el resultado sea deterministico."""
    for name in ("FONT_MICRO", "FONT_SMALL", "FONT_BODY", "FONT_TITLE",
                 "FONT_TIMECODE", "FONT_BIG"):
        value = getattr(theme, name)
        assert isinstance(value, int), f"{name} debe ser int, es {type(value)}"


def test_los_nombres_viejos_siguen_existiendo_durante_la_f1():
    for name in ("BG_WINDOW", "BG_PANEL", "BG_RAIL", "BG_HOVER", "BG_ACTIVE",
                 "TEXT_MUTED", "BORDER", "TICK_MINOR_COLOR", "TICK_MAJOR_COLOR"):
        assert hasattr(theme, name), f"falta el alias {name}"
```

- [ ] **Step 2: Correr los tests y ver que fallan por el motivo correcto**
  (`AttributeError` en los tokens nuevos, no errores de importación.)

- [ ] **Step 3: Reemplazar el bloque de constantes de `theme.py`**

```python
# src/clasificador_video/ui/theme.py  (renglones 1-56, reemplazo completo)
from __future__ import annotations

from PySide6.QtGui import QFont

# ---------------------------------------------------------------------------
# Tokens de diseño. UNICA fuente de valores visuales de la app.
#
# Los valores salen del bloque `:root` de
# docs/superpowers/mockups/rediseno-2026-08-08/mockup.html -- si hay que
# cambiar un color, se cambia primero ahi y luego aqui, nunca al reves y
# nunca en un widget suelto.
# ---------------------------------------------------------------------------

# --- superficies (de mas oscuro a mas claro) ---
BG_APP = "#0a0b0d"        # fondo de la ventana
BG_SURFACE_0 = "#101216"  # rails y paneles
BG_SURFACE_1 = "#16191e"  # controles en reposo
BG_SURFACE_2 = "#1d2128"  # chips, teclas, elementos activos
LINE = "#262b33"          # bordes visibles
LINE_SOFT = "#1e222a"     # separadores internos

# --- texto ---
TEXT = "#e6e9ee"
TEXT_2 = "#9aa3b0"
TEXT_3 = "#626b78"

# --- ESTADO del clip. Nunca se reusan para identidad de cuarto. ---
PICK_COLOR = "#55c08a"
STAR_COLOR = "#7ee6b0"    # destacado = pick reforzado, misma familia
REJECT_COLOR = "#d4696c"
CURRENT_COLOR = "#e8a33d"  # clip actual y playhead
TRIM_COLOR = "#6d8cf5"     # rango in/out marcado

# --- IDENTIDAD DE CUARTO: apagada a proposito, no compite con el estado ---
ROOM_PALETTE = [
    "#c0885a", "#6d8ca8", "#8b7ca8", "#4f9a8e", "#7e9e5e",
    "#3e9bc0", "#a9836f", "#b26f86", "#7c8794",
]

# --- colores derivados que antes vivian sueltos en otros modulos ---
SELECTION_WASH = "rgba(109, 140, 245, 60)"  # lavado de seleccion multiple
RANGE_TRACK_COLOR = "#2e343d"               # riel de la barra de rango
FLAG_NONE_COLOR = TEXT_3                    # texto de "sin marca"
PLAYHEAD_HIGHLIGHT = "#f2bd72"              # brillo superior del playhead
TICK_MINOR_COLOR = "#2e343d"
TICK_MAJOR_COLOR = "#454d59"

# --- dimensiones fijas del layout (px) ---
TITLEBAR_HEIGHT = 36
STATUSBAR_HEIGHT = 24
RAIL_WIDTH = 200
TOOLCOL_WIDTH = 56
SHEET_MIN_WIDTH = 340
OVERLAY_MARGIN = 13       # margen de los controles flotantes sobre el video
SCRUB_HEIGHT = 26

# --- radios ---
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8

# --- tipografia ---
# Enteros a proposito: QSS no interpreta de forma confiable tamaños
# fraccionarios de fuente, y el mockup usa medios pixeles que no aportan.
FONT_MICRO = 9      # etiquetas en mayusculas con tracking
FONT_SMALL = 11     # hints y metadata secundaria
FONT_BODY = 12      # texto normal
FONT_TITLE = 13     # nombre de proyecto
FONT_TIMECODE = 19  # timecode sobre el video
FONT_BIG = 24       # numero grande de progreso

LETTER_SPACING_CAPS = 1.2  # tracking de las etiquetas en mayusculas

MONO_FONT = '"SF Mono", "JetBrains Mono", Menlo, monospace'

# ---------------------------------------------------------------------------
# Alias de compatibilidad. Existen SOLO para que la app siga corriendo
# durante la F1 con los widgets viejos. Se borran en la Task 9 de la F2.
# ---------------------------------------------------------------------------
ACCENT = CURRENT_COLOR
BG_WINDOW = BG_APP
BG_PANEL = BG_SURFACE_0
BG_RAIL = BG_SURFACE_0
BG_HOVER = BG_SURFACE_1
BG_ACTIVE = BG_SURFACE_2
TEXT_MUTED = TEXT_2
BORDER = LINE


def room_color(index: int) -> str:
    """Color de identidad estable para el cuarto en la posicion `index`
    de la lista de cuartos activos -- mismo indice, mismo color siempre.
    """
    return ROOM_PALETTE[index % len(ROOM_PALETTE)]


def apply_letter_spacing(widget, px: float = LETTER_SPACING_CAPS) -> None:
    """QSS no tiene `letter-spacing`: el tracking de las etiquetas en
    mayusculas del mockup solo se puede aplicar por QFont desde codigo.
    """
    font = widget.font()
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, px)
    widget.setFont(font)
```

- [ ] **Step 4: Correr los tests de `theme` y la suite completa.** La suite
  tiene que seguir verde: solo cambiaron valores, no nombres.

---

### Task 2: `build_stylesheet()` sin colores literales

**Files:**
- Modify: `src/clasificador_video/ui/theme.py:57-211` (`build_stylesheet`)
- Test: `tests/ui/test_theme.py`

Hoy hay **once** hexadecimales escritos a mano dentro de `build_stylesheet`
(renglones 88, 98, 104, 109, 118, 135, 141, 145, 171, 173, 183 del archivo
actual). Cada uno es una oportunidad de deriva.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/ui/test_theme.py
import inspect
import re


def test_build_stylesheet_no_tiene_colores_escritos_a_mano():
    """Todo valor visual sale de un token. Un hexadecimal literal dentro
    de la hoja de estilos es exactamente como empieza la deriva contra el
    mockup."""
    fuente = inspect.getsource(theme.build_stylesheet)
    literales = re.findall(r"#[0-9a-fA-F]{6}\b", fuente)
    assert literales == [], f"colores a mano en build_stylesheet: {literales}"
```

- [ ] **Step 2: Correr y ver que falla** listando los once.

- [ ] **Step 3: Promover cada literal a token y usarlo.** Mapa de reemplazo,
      en orden de aparición:

| Literal actual | Token |
|---|---|
| `#1c1c20` (hover de botón) | `BG_SURFACE_0` |
| `#0a0a0b` (texto del botón principal) | `BG_APP` |
| `#ff9d5c` (hover del botón principal) | `PLAYHEAD_HIGHLIGHT` |
| `#29292d` (borde punteado y de inputs) | `LINE` |
| `#5c5c60` (título de panel) | `TEXT_3` |
| `#ffb15c` (badge sin clasificar) | `CURRENT_COLOR` |
| `#4a4a4e` (indicador de guardado) | `TEXT_3` |
| `#2c2c30` (borde del keycap) | `LINE` |
| `#777777` (texto del keycap) | `TEXT_2` |
| `#3a2c15` (chunk de la barra de conteo) | `BG_SURFACE_2` |

- [ ] **Step 4: Correr los tests.** Verde.

---

### Task 3: Ningún módulo declara colores fuera del tema

**Files:**
- Modify: `src/clasificador_video/ui/filmstrip.py:27,42,258`
- Modify: `src/clasificador_video/ui/video_widget.py:322`
- Test: `tests/ui/test_theme.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/ui/test_theme.py
from pathlib import Path


def test_ningun_modulo_declara_colores_fuera_del_tema():
    """Candado 1 del plan de rediseño: si un widget puede inventar su
    propio gris, la app deja de parecerse al mockup en el primer commit
    apurado."""
    raiz = Path(__file__).resolve().parents[2] / "src" / "clasificador_video"
    patron = re.compile(r"#[0-9a-fA-F]{6}\b|rgba?\(")
    ofensores = []
    for archivo in sorted(raiz.rglob("*.py")):
        if archivo.name == "theme.py" or "__pycache__" in archivo.parts:
            continue
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            if patron.search(linea):
                ofensores.append(f"{archivo.relative_to(raiz)}:{numero}: {linea.strip()}")
    assert ofensores == [], "colores fuera de theme.py:\n" + "\n".join(ofensores)
```

- [ ] **Step 2: Correr y ver los cuatro ofensores** (tres en `filmstrip.py`,
      uno en `video_widget.py`).

- [ ] **Step 3: Arreglar `filmstrip.py`**
  - Borrar `_SELECTION_WASH` y `_RANGE_TRACK_COLOR`.
  - Ampliar el import a
    `from clasificador_video.ui.theme import (CURRENT_COLOR, FLAG_NONE_COLOR, PICK_COLOR, RANGE_TRACK_COLOR, REJECT_COLOR, SELECTION_WASH, TRIM_COLOR)`.
  - Sustituir los usos: `_SELECTION_WASH` → `SELECTION_WASH`,
    `_RANGE_TRACK_COLOR` → `RANGE_TRACK_COLOR`, y el `"#666666"` del
    renglón 258 → `FLAG_NONE_COLOR`.

- [ ] **Step 4: Arreglar `video_widget.py`**
  - Agregar `PLAYHEAD_HIGHLIGHT` al import desde `theme`.
  - Renglón 322: `gradient.setColorAt(0.0, QColor(PLAYHEAD_HIGHLIGHT))`.

- [ ] **Step 5: Correr la suite completa.** Verde.

---

### Task 4: Arnés de comparación con el mockup

**Files:**
- Create: `scripts/comparar_con_mockup.py`
- Test: `tests/test_comparar_con_mockup.py`

**El mockup se renderiza con Chrome sin cabeza, no con `QtWebEngine`.**
Verificado el 2026-08-08 en esta máquina:

- `QWebEngineView` **no carga** el `file://` del mockup — `loadFinished` llega
  con `ok=False` y `grab()` devuelve una imagen de 0×0. Descartado.
- Chrome sin cabeza produce el PNG correcto de 1600×1000, con 507 colores
  distintos y `#101216` (el `--surface-0` del mockup) como color dominante.

Como el mockup tiene dos pantallas apiladas con encabezados, el arnés escribe
una **copia temporal** del HTML con un `<style>` y un `<script>` inyectados que
dejan visible solo la pantalla pedida. **Nunca se modifica el mockup original.**

- [ ] **Step 1: Escribir el test que falla** (solo la parte pura; los renders
      necesitan GUI y se verifican a mano)

```python
# tests/test_comparar_con_mockup.py
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "comparar_con_mockup", RAIZ / "scripts" / "comparar_con_mockup.py"
)
comparar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(comparar)

HTML_MINIMO = "<html><head><title>x</title></head><body></body></html>"


def test_la_inyeccion_deja_visible_solo_la_pantalla_pedida():
    html = comparar.html_aislado(HTML_MINIMO, 0)
    assert ".window.__solo" in html
    assert "querySelectorAll('.window')[0]" in html


def test_la_inyeccion_puede_pedir_la_segunda_pantalla():
    assert "[1]" in comparar.html_aislado(HTML_MINIMO, 1)


def test_la_inyeccion_no_toca_el_cuerpo_del_documento():
    """Se inyecta en <head>: el mockup original nunca se modifica y la
    copia tiene que seguir siendo el mismo documento."""
    html = comparar.html_aislado(HTML_MINIMO, 0)
    assert html.count("<body>") == 1
    assert html.index("__solo") < html.index("</head>")


def test_la_inyeccion_esconde_los_encabezados_y_el_relleno():
    html = comparar.html_aislado(HTML_MINIMO, 0)
    assert ".caption{display:none!important}" in html.replace(" ", "")


def test_geometria_del_lienzo_es_la_suma_mas_la_separacion():
    ancho, alto = comparar.geometria_lienzo(
        (1600, 1000), (1600, 1000), separacion=40
    )
    assert ancho == 1600 + 40 + 1600
    assert alto == 1000


def test_geometria_del_lienzo_usa_el_alto_mayor():
    _, alto = comparar.geometria_lienzo((100, 200), (100, 500), separacion=10)
    assert alto == 500
```

- [ ] **Step 2: Correr y ver que falla** (el script no existe).

- [ ] **Step 3: Escribir `scripts/comparar_con_mockup.py`**

```python
#!/usr/bin/env python3
"""Arnés de comparación mockup ↔ app (Candado 2 del plan de rediseño).

Renderiza el mockup HTML y la ventana real de la app al mismo tamaño y
escribe un PNG con las dos, lado a lado.

    .venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/comp.png

El mockup se rinde con Chrome sin cabeza. QtWebEngine se probó y se
descartó: no carga el file:// del mockup (loadFinished llega con ok=False
y grab() devuelve 0x0). Verificado el 2026-08-08.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MOCKUP = RAIZ / "docs" / "superpowers" / "mockups" / "rediseno-2026-08-08" / "mockup.html"
ANCHO, ALTO = 1600, 1000

CHROME_CANDIDATOS = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]


def buscar_chrome() -> str:
    for ruta in CHROME_CANDIDATOS:
        if ruta and Path(ruta).exists():
            return ruta
    raise SystemExit(
        "No encontré Chrome ni Chromium. Instalá uno o exportá CHROME_BIN."
    )


def html_aislado(html: str, pantalla: int) -> str:
    """Devuelve el HTML del mockup con un <style> y un <script> inyectados
    en el <head> que dejan visible una sola pantalla, pegada a la esquina.

    Se trabaja sobre una COPIA: el mockup original nunca se modifica.
    """
    inyeccion = (
        "<style>"
        "body{padding:0!important;gap:0!important;background:#000!important}"
        ".caption{display:none!important}"
        ".window{display:none!important}"
        ".window.__solo{display:flex!important;border-radius:0!important;"
        "box-shadow:none!important}"
        "</style>"
        "<script>document.addEventListener('DOMContentLoaded',function(){"
        f"document.querySelectorAll('.window')[{pantalla}]"
        ".classList.add('__solo');});</script>"
    )
    return html.replace("</head>", inyeccion + "</head>", 1)


def geometria_lienzo(a: tuple[int, int], b: tuple[int, int], separacion: int) -> tuple[int, int]:
    return a[0] + separacion + b[0], max(a[1], b[1])


def render_mockup(salida: Path, pantalla: int) -> None:
    copia = Path(tempfile.mkdtemp()) / "mockup_solo.html"
    copia.write_text(
        html_aislado(MOCKUP.read_text(encoding="utf-8"), pantalla), encoding="utf-8"
    )
    subprocess.run(
        [
            buscar_chrome(),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--force-device-scale-factor=1",
            f"--window-size={ANCHO},{ALTO}",
            "--virtual-time-budget=3000",
            f"--screenshot={salida}",
            f"file://{copia}",
        ],
        capture_output=True,  # Chrome escupe ruido irrelevante en stderr
        check=False,          # su codigo de salida no es confiable
    )
    if not salida.exists():
        raise SystemExit(f"Chrome no escribió {salida}")


def render_app(salida: Path) -> None:
    from PySide6.QtWidgets import QApplication

    from clasificador_video.app import configure_gl_surface_format
    from clasificador_video.ui.theme import build_stylesheet
    # `scripts/` no es un paquete y al correr `python scripts/x.py` el
    # sys.path[0] es `scripts/`, no la raiz del repo: el import va plano.
    # (`clasificador_video` si resuelve, porque el proyecto esta instalado
    # en modo editable en el venv.)
    from _datos_de_ejemplo import construir_ventana_de_ejemplo

    configure_gl_surface_format()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setStyleSheet(build_stylesheet())
    ventana = construir_ventana_de_ejemplo()
    ventana.resize(ANCHO, ALTO)
    ventana.show()
    app.processEvents()
    ventana.grab().save(str(salida))


def componer(izq: Path, der: Path, salida: Path, separacion: int = 40) -> None:
    from PySide6.QtGui import QColor, QImage, QPainter

    a, b = QImage(str(izq)), QImage(str(der))
    ancho, alto = geometria_lienzo((a.width(), a.height()), (b.width(), b.height()), separacion)
    lienzo = QImage(ancho, alto, QImage.Format_RGB32)
    lienzo.fill(QColor("black"))
    p = QPainter(lienzo)
    p.drawImage(0, 0, a)
    p.drawImage(a.width() + separacion, 0, b)
    p.end()
    lienzo.save(str(salida))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--pantalla", type=int, default=0, help="0 = modo clip, 1 = modo hoja")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp())
    izq, der = tmp / "mockup.png", tmp / "app.png"
    render_mockup(izq, args.pantalla)   # subproceso de Chrome, antes de crear la QApplication
    render_app(der)                     # la QApplication vive solo en este proceso
    componer(izq, der, args.salida)
    print(f"comparación escrita en {args.salida}")


if __name__ == "__main__":
    main()
```

**Orden de las llamadas, no es casual:** `render_mockup` va primero porque
lanza un subproceso externo y no necesita `QApplication`. Después
`render_app` crea la única `QApplication` del proceso, con el
`QSurfaceFormat` Core 3.3 que mpv exige. `componer` reusa esa misma
`QApplication` — por eso ya no crea un `QGuiApplication` propio, que
chocaría con la existente.

- [ ] **Step 4: Crear `scripts/_datos_de_ejemplo.py`** con
      `construir_ventana_de_ejemplo() -> MainWindow`: una `MainWindow` con
      `video_factory` falso, los nueve cuartos del mockup (`Cocina`, `Sala`,
      `Recámara 1`, `Recámara 2`, `Baño 1`, `Baño 2`, `Comedor`, `Terraza`,
      `Fachada`), 128 clips con la misma mezcla de estados que el mockup
      (116 clasificados, 41 pick, 9 reject, 12 sin clasificar) y el clip 87
      como actual. **Los mismos datos que el mockup, o la comparación no
      sirve.**

      Tres cosas que hay que resolver aquí o la imagen sale engañosa:

      1. **Miniaturas sintéticas, no `mpv`.** Extraer miniaturas de verdad
         necesita archivos reales y tarda; sin ellas las tarjetas salen
         vacías y la mitad derecha de la comparación no dice nada. Se pintan
         `QPixmap` con un degradado del color del cuarto —el mismo truco que
         usa el mockup— y se inyectan con `set_frames()`.
      2. **Mezcla de orientaciones**, no todo apaisado: el mockup muestra
         verticales y horizontales conviviendo. Poblar `_clip_sizes` con
         `(2160, 3840)` y `(3840, 2160)` alternados según el mockup.
      3. **Nada de tocar el caché real** de `~/.cache/clasificador_video`:
         pasar un `thumbnail_cache_root` temporal.

- [ ] **Step 5: Correr el arnés a mano y mirar la imagen.**

```bash
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/comp-f1.png
```

- [ ] **Step 6: Correr la suite completa.** Verde.

---

### Task 5: Cierre de la F1

- [ ] **Step 1:** Correr el arnés y **mirar la imagen**.
- [ ] **Step 2:** Anotar en el commit que la app se ve peor que antes y por qué
      (paleta nueva, layout viejo). Es el estado esperado de esta fase.
- [ ] **Step 3:** Verificar los candados:
  - `pytest` verde,
  - `test_ningun_modulo_declara_colores_fuera_del_tema` pasa,
  - el arnés produce imagen.
- [ ] **Step 4:** Commit.

---

# FASE 2 — El esqueleto

### Task 1: Conservar el tamaño real del clip al importar

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py` (`__init__`, `_load_clips_from_ingest`)
- Test: `tests/ui/test_main_window.py`

El ancho del video lo dicta la relación de aspecto del clip, así que la F2
**depende** de este dato. Hoy `_load_clips_from_ingest` llama a `probe_clip` y
tira `width`/`height` (ya corregidos por rotación en `probe.py`).

Se guarda **en memoria, no en `Clip`**: agregar campos a `Clip` cambiaría
`to_dict()` y con eso el contrato del manifest con el plugin de Premiere. Se
sigue el patrón que ya existe para `_clip_durations`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_main_window.py
def test_importar_guarda_el_tamano_real_de_cada_clip(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    carpeta = tmp_path / "tarjeta"
    carpeta.mkdir()
    (carpeta / "a.mp4").write_bytes(b"x")
    monkeypatch.setattr(
        window, "_probe_clip",
        lambda p: {"width": 2160, "height": 3840, "fps": 29.97,
                   "duration_frames": 540, "has_audio": True, "rotation": 90},
    )
    window.ingest_tree.import_folder(carpeta)
    window._load_clips_from_ingest()
    assert window._clip_sizes[0] == (2160, 3840)


def test_aspect_ratio_usa_el_tamano_del_clip(qtbot):
    window = _window(qtbot)
    window._clip_sizes = {0: (2160, 3840)}
    assert window.aspect_ratio_for(0) == 2160 / 3840


def test_aspect_ratio_cae_en_16_9_si_no_se_conoce_el_tamano(qtbot):
    """Sesion restaurada de disco: no se volvio a correr ffprobe."""
    window = _window(qtbot)
    window._clip_sizes = {}
    assert window.aspect_ratio_for(0) == 16 / 9


def test_aspect_ratio_ignora_tamanos_invalidos(qtbot):
    window = _window(qtbot)
    window._clip_sizes = {0: (0, 0)}
    assert window.aspect_ratio_for(0) == 16 / 9
```

- [ ] **Step 2: Correr y ver que fallan.**
- [ ] **Step 3: Implementar**
  - En `__init__`, junto a `self._clip_durations`:
    `self._clip_sizes: dict[int, tuple[int, int]] = {}  # indice -> (ancho, alto) ya rotados; solo en memoria`
  - En `_load_clips_from_ingest`, dentro del bucle, después de `clips.append(...)`:
    guardar `sizes[len(clips) - 1] = (int(info["width"]), int(info["height"]))`
    protegido con `.get()` por si el doble de pruebas no los trae; asignar
    `self._clip_sizes = sizes` junto a `self._clip_durations = durations`.
  - Método nuevo:

```python
    def aspect_ratio_for(self, index: int) -> float:
        """Relacion de aspecto real del clip (ya corregida por rotacion en
        probe.py). 16/9 cuando no se conoce -- pasa con sesiones
        restauradas de disco, donde no se volvio a correr ffprobe."""
        ancho, alto = self._clip_sizes.get(index, (0, 0))
        if ancho > 0 and alto > 0:
            return ancho / alto
        return 16 / 9
```

- [ ] **Step 4: Correr la suite.** Verde.

---

### Task 2: `SegmentedControl` (selector de calidad con la forma del mockup)

**Files:**
- Create: `src/clasificador_video/ui/segmented.py`
- Test: `tests/ui/test_segmented.py`

El `QComboBox` de calidad no existe en el mockup: ahí es un control segmentado
(`Full ½ ¼ ⅛`). Se construye ahora porque la F8 lo va a reusar para la
velocidad.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_segmented.py
from clasificador_video.ui.segmented import SegmentedControl


def test_crea_un_boton_por_opcion(qtbot):
    seg = SegmentedControl(["Full", "1/2", "1/4", "1/8"])
    qtbot.addWidget(seg)
    assert [b.text() for b in seg.buttons] == ["Full", "1/2", "1/4", "1/8"]


def test_la_primera_opcion_queda_activa_por_defecto(qtbot):
    seg = SegmentedControl(["Full", "1/2"])
    qtbot.addWidget(seg)
    assert seg.current() == "Full"
    assert seg.buttons[0].isChecked()


def test_seleccionar_emite_la_senal_con_el_texto(qtbot):
    seg = SegmentedControl(["Full", "1/2"])
    qtbot.addWidget(seg)
    with qtbot.waitSignal(seg.selected) as blocker:
        seg.buttons[1].click()
    assert blocker.args == ["1/2"]
    assert seg.current() == "1/2"


def test_solo_una_opcion_queda_activa_a_la_vez(qtbot):
    seg = SegmentedControl(["a", "b", "c"])
    qtbot.addWidget(seg)
    seg.buttons[2].click()
    assert [b.isChecked() for b in seg.buttons] == [False, False, True]


def test_set_current_no_emite_senal(qtbot):
    """Sincronizar el control desde el estado no debe disparar el handler
    que cambia el perfil del reproductor."""
    seg = SegmentedControl(["a", "b"])
    qtbot.addWidget(seg)
    with qtbot.assertNotEmitted(seg.selected):
        seg.set_current("b")
    assert seg.current() == "b"
```

- [ ] **Step 2: Correr y ver que fallan.**
- [ ] **Step 3: Implementar** `SegmentedControl(QWidget)`:
  - `selected = Signal(str)`.
  - `QHBoxLayout` sin márgenes ni espaciado, botones `QPushButton` checkeables
    en un `QButtonGroup` exclusivo, `objectName` `segmentedButton`, el
    contenedor `segmentedControl`.
  - `current() -> str`, `set_current(texto)` con `blockSignals` alrededor para
    cumplir el último test.

- [ ] **Step 4: Estilar en `build_stylesheet`** con los tokens: fondo
      `BG_SURFACE_1`, borde `LINE`, radio `RADIUS_MD`, activo `BG_SURFACE_2`
      con `TEXT`, inactivo `TEXT_3`, fuente `MONO_FONT` a `FONT_SMALL`.

- [ ] **Step 5: Correr la suite.** Verde.

---

### Task 3: `VideoStage` — video dimensionado por aspecto y controles encima

**Files:**
- Create: `src/clasificador_video/ui/video_stage.py`
- Modify: `src/clasificador_video/ui/video_widget.py` (`ScrubBar`: modo overlay)
- Test: `tests/ui/test_video_stage.py`, `tests/ui/test_video_widget.py`

El widget más delicado de la fase. Tres cosas que se hacen mal por default:

1. **El `VideoWidget` no puede ocupar todo el ancho disponible.** Si lo hace,
   mpv centra el clip vertical y vuelven las franjas negras — el problema que
   este rediseño existe para eliminar. El ancho lo fija `MainWindow` a
   `alto_del_cuerpo × aspecto`.
2. **Los overlays se posicionan con un filtro de eventos sobre el
   `VideoWidget`**, no en el `resizeEvent` del padre: cuando el padre recibe
   `resizeEvent`, el hijo todavía tiene el tamaño viejo, y los overlays
   quedarían corridos un cuadro.
3. **Todo overlay de dibujo propio necesita `WA_TranslucentBackground`**
   (hallazgo de la F0). Sin esa bandera la `ScrubBar` pinta fondo opaco donde
   no dibuja y se come una franja del video. Los overlays que no reciben mouse
   llevan además `WA_TransparentForMouseEvents`, para que el click y el
   arrastre lleguen a la `ScrubBar` y al video.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_video_stage.py
from PySide6.QtCore import Qt

from clasificador_video.ui.video_stage import VideoStage


class FakeMpv:
    def __init__(self, **kwargs):
        self.pause = True
        self.time_pos = 0.0
        self.duration = 0.0
    def play(self, path):
        self.loaded = path


def _stage(qtbot) -> VideoStage:
    stage = VideoStage(mpv_factory=FakeMpv)
    qtbot.addWidget(stage)
    stage.resize(529, 940)
    return stage


def _stage_visible(qtbot) -> VideoStage:
    """`qtbot.addWidget` NO muestra el widget: sin `show()` previo,
    `waitExposed` se queda esperando para siempre. Y sin exponer, el
    layout nunca corre y `stage.video` conserva su tamaño inicial."""
    stage = _stage(qtbot)
    stage.show()
    qtbot.waitExposed(stage)
    return stage


def test_la_scrub_bar_es_hija_del_video_no_hermana(qtbot):
    """Si fuera hermana volveria a ser una banda y le robaria altura."""
    stage = _stage(qtbot)
    assert stage.scrub_bar.parent() is stage.video


def test_la_scrub_bar_es_translucida(qtbot):
    """Hallazgo de la F0: sin esta bandera tapa una franja del video."""
    stage = _stage(qtbot)
    assert stage.scrub_bar.testAttribute(Qt.WA_TranslucentBackground)


def test_los_overlays_pasivos_no_capturan_el_mouse(qtbot):
    stage = _stage(qtbot)
    for widget in (stage.file_label, stage.badges, stage.scrim, stage.timecode_label):
        assert widget.testAttribute(Qt.WA_TransparentForMouseEvents), widget.objectName()


def test_la_scrub_bar_si_recibe_mouse(qtbot):
    stage = _stage(qtbot)
    assert not stage.scrub_bar.testAttribute(Qt.WA_TransparentForMouseEvents)


def test_los_overlays_se_reposicionan_al_cambiar_el_tamano(qtbot):
    from clasificador_video.ui import theme
    stage = _stage_visible(qtbot)
    stage.resize(400, 600)
    qtbot.wait(50)
    esperado = stage.video.width() - 2 * theme.OVERLAY_MARGIN
    assert stage.scrub_bar.width() == esperado


def test_la_scrub_bar_queda_pegada_al_borde_inferior(qtbot):
    from clasificador_video.ui import theme
    stage = _stage_visible(qtbot)
    stage.resize(529, 940)
    qtbot.wait(50)
    borde = stage.scrub_bar.y() + stage.scrub_bar.height()
    assert stage.video.height() - borde == theme.OVERLAY_MARGIN


def test_ancho_para_aspecto_vertical():
    assert VideoStage.width_for(940, 9 / 16) == 529


def test_ancho_para_aspecto_horizontal():
    assert VideoStage.width_for(600, 16 / 9) == 1067


def test_ancho_nunca_es_cero():
    assert VideoStage.width_for(0, 9 / 16) >= 1
```

```python
# tests/ui/test_video_widget.py  (agregar)
def test_scrub_bar_en_modo_overlay_usa_riel_translucido(qtbot):
    """Sobre el video, un riel solido se ve como una banda opaca."""
    from clasificador_video.ui.video_widget import ScrubBar
    bar = ScrubBar()
    qtbot.addWidget(bar)
    assert bar.track_color().alpha() == 255
    bar.set_over_video(True)
    assert bar.track_color().alpha() < 255
```

- [ ] **Step 2: Correr y ver que fallan.**

- [ ] **Step 3: Agregar el modo overlay a `ScrubBar`** en `video_widget.py`:
  - `self._over_video = False` en `__init__`.
  - `def set_over_video(self, activo: bool) -> None:` que guarda la bandera y
    llama `self.update()`.
  - `def track_color(self) -> QColor:` que devuelve `QColor(LINE)` normal y el
    riel translúcido en modo overlay — el `rgba(255,255,255,.13)` del mockup.
    Ese valor va como token en `theme.py`
    (`TRACK_OVER_VIDEO_RGBA = (255, 255, 255, 33)`, una tupla, y el widget hace
    `QColor(*theme.TRACK_OVER_VIDEO_RGBA)`). El test de la Task 3 de la F1 no lo
    atraparía —su expresión regular solo busca hexadecimales y `rgb(`/`rgba(`,
    no `QColor(...)`— así que aquí la disciplina la pone el plan, no el test.
    **Escribirlo suelto en el widget sería exactamente la deriva que el
    Candado 1 quiere evitar.**
  - En `paintEvent`, usar `self.track_color()` donde hoy hay `QColor(BORDER)`.

- [ ] **Step 4: Escribir `video_stage.py`**

```python
# src/clasificador_video/ui/video_stage.py
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from clasificador_video.ui import theme
from clasificador_video.ui.segmented import SegmentedControl
from clasificador_video.ui.video_widget import ScrubBar, VideoWidget

M = theme.OVERLAY_MARGIN


class VideoStage(QWidget):
    """El video y sus controles flotando encima (validado en la F0).

    Ningun control vive en una banda: en un 9:16 cada 16 px de banda
    cuestan 9 px de ancho de video, y ese es el problema que este
    rediseño existe para resolver.
    """

    def __init__(self, mpv_factory=None, parent=None):
        super().__init__(parent)
        self.setObjectName("videoStage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.video = VideoWidget(mpv_factory=mpv_factory) if mpv_factory else VideoWidget()
        layout.addWidget(self.video)

        self.file_label = QLabel("", self.video)
        self.file_label.setObjectName("overlayFile")
        self.badges = QLabel("", self.video)
        self.badges.setObjectName("overlayBadges")
        self.scrim = QLabel("", self.video)
        self.scrim.setObjectName("overlayScrim")
        self.timecode_label = QLabel("", self.video)
        self.timecode_label.setObjectName("overlayTimecode")
        self.quality = SegmentedControl(["Full", "1/2", "1/4", "1/8"], self.video)
        self.scrub_bar = ScrubBar(self.video)
        self.scrub_bar.set_over_video(True)

        for pasivo in (self.file_label, self.badges, self.scrim, self.timecode_label):
            pasivo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.scrub_bar.setAttribute(Qt.WA_TranslucentBackground, True)

        # El padre recibe resizeEvent ANTES de que el hijo cambie de
        # tamaño: posicionar ahi deja los overlays corridos un cuadro.
        self.video.installEventFilter(self)

    @staticmethod
    def width_for(height: int, aspect_ratio: float) -> int:
        """Ancho que le corresponde al video para no dejar franjas negras."""
        return max(1, round(height * aspect_ratio))

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if obj is self.video and event.type() == QEvent.Resize:
            self._place_overlays()
        return super().eventFilter(obj, event)

    def _place_overlays(self) -> None:
        w, h = self.video.width(), self.video.height()
        self.scrim.setGeometry(0, h - 150, w, 150)
        self.file_label.adjustSize()
        self.file_label.move(M, M)
        self.badges.adjustSize()
        self.badges.move(M, M + self.file_label.height() + 8)
        self.quality.adjustSize()
        self.quality.move(w - self.quality.width() - M, M)
        self.timecode_label.adjustSize()
        self.timecode_label.move(
            M, h - M - theme.SCRUB_HEIGHT - 8 - self.timecode_label.height()
        )
        self.scrub_bar.setGeometry(
            M, h - M - theme.SCRUB_HEIGHT, w - 2 * M, theme.SCRUB_HEIGHT
        )
        self.scrim.lower()
        for encima in (self.file_label, self.badges, self.quality,
                       self.timecode_label, self.scrub_bar):
            encima.raise_()
```

- [ ] **Step 5: Estilar los overlays en `build_stylesheet`.** El scrim usa
      `qlineargradient` de `rgba(0,0,0,0)` a `rgba(0,0,0,200)` — validado en la
      F0. Los `QLabel` de overlay usan fondo `rgba` semitransparente y
      `RADIUS_MD`. **Todos los valores como tokens**, no literales.

- [ ] **Step 6: Correr la suite.** Verde.

---

### Task 4: `TitleBar` (36 px)

**Files:**
- Create: `src/clasificador_video/ui/title_bar.py`
- Test: `tests/ui/test_title_bar.py`

Contenido: marca cuadrada, nombre del proyecto (`FONT_TITLE`, 600), subtítulo
`N clips · Sony FX30` (`TEXT_3`), estirador, indicador de guardado con LED,
botón `Cuartos ⌘R`, botón primario `Exportar a Premiere ⌘E`.

**No lleva el conmutador Clip/Hoja**: los modos son la F10.

- [ ] **Step 1: Tests** — altura fija exacta `theme.TITLEBAR_HEIGHT`; señales
      `export_requested` y `rooms_requested` se emiten al hacer click;
      `set_saved_seconds(12)` pone `"Guardado hace 12 s"`;
      `set_saved_seconds(None)` deja el texto vacío; `set_project("X", 128)`
      escribe nombre y subtítulo.
- [ ] **Step 2: Correr y ver que fallan.**
- [ ] **Step 3: Implementar** con `setFixedHeight(theme.TITLEBAR_HEIGHT)` y
      `apply_letter_spacing` en el subtítulo.
- [ ] **Step 4: Estilar.** Fondo `BG_SURFACE_0`, borde inferior `LINE`.
- [ ] **Step 5: Correr la suite.**

---

### Task 5: `StatusBar` (24 px)

**Files:**
- Create: `src/clasificador_video/ui/status_bar.py`
- Test: `tests/ui/test_status_bar.py`

Contenido: datos técnicos del clip actual en monoespaciada
(`C0087.MP4 · 2160×3840 · 29.97 fps · vertical (rot 90°)`), aviso de sin
clasificar en `CURRENT_COLOR`, estirador, ruta del volumen.

El aviso **todavía no es clickeable** — eso es la F7. Aquí solo se muestra.

- [ ] **Step 1: Tests** — altura fija; `set_clip_info(...)` compone la cadena
      con los separadores correctos; `set_unclassified(0)` deja vacío el aviso;
      `set_unclassified(12)` escribe `"12 sin clasificar"`.
- [ ] **Step 2-5:** como arriba.

---

### Task 6: `RoomRail` (200 px)

**Files:**
- Create: `src/clasificador_video/ui/room_rail.py`
- Test: `tests/ui/test_room_rail.py`

Reemplaza la columna de cuartos actual (`room_list_widget` +
`_build_room_row_widget` + `_refresh_room_counts`), el botón de importar y el
panel "Material importado".

Contenido, de arriba abajo:
1. Bloque de progreso: número grande `FONT_BIG` mono, `/total`, etiqueta
   `CLASIFICADOS` en `FONT_MICRO` con tracking; barra segmentada por cuarto;
   leyenda de pick/reject/sin clasificar.
2. Encabezado `CUARTOS` + `⏎ buscar` (la paleta es la F9; aquí el texto es
   informativo).
3. Lista de cuartos: tecla, franja de color, nombre elidido, conteo.
4. Botón de importar carpetas, al pie.

**Sin panel de "Material importado"**: la lista de carpetas importadas no
aparece en el mockup y ocupaba media columna.

- [ ] **Step 1: Tests** — ancho fijo `theme.RAIL_WIDTH`;
      `set_rooms([...], counts)` crea una fila por cuarto con su número 1–9;
      el décimo cuarto en adelante queda sin número; `set_progress(116, 128)`
      escribe `116` y `/128`; nombres largos se eliden en vez de desbordar
      (verificar con `QFontMetrics`); señal `import_requested`.
- [ ] **Step 2-5:** como arriba.

**Nota de traducción CSS→Qt:** el elidido necesita
`QFontMetrics(label.font()).elidedText(texto, Qt.ElideRight, ancho)`. Crear el
helper `ui/text.py::elide(label, texto)` y usarlo aquí y en `ClipSheet`.

---

### Task 7: `ToolColumn` (56 px)

**Files:**
- Create: `src/clasificador_video/ui/tool_column.py`
- Test: `tests/ui/test_tool_column.py`

Columna vertical de indicadores de estado del clip actual: rótulo `RANGO` con
`IN`/`OUT`, rótulo `ESTADO` con `PICK`/`REJ`, y `⌘Z`. Cuestan ancho, no alto:
por eso van en columna.

En la F2 son **indicadores**, no botones: reflejan estado. `★` (destacado)
llega en la F9.

- [ ] **Step 1: Tests** — ancho fijo `theme.TOOLCOL_WIDTH`;
      `set_range(in_frame=120, out_frame=None)` deja `IN` encendido y `OUT`
      apagado; `set_flag("pick")` enciende solo `PICK`; `set_flag("none")`
      apaga los dos. El encendido se comprueba por propiedad dinámica
      (`widget.property("on") is True`), no por hoja de estilo inline.
- [ ] **Step 2-5:** como arriba. Estilar con
      `QWidget#toolIndicator[on="true"]` en el QSS.

---

### Task 8: `ClipSheet` (hoja de contactos)

**Files:**
- Create: `src/clasificador_video/ui/clip_sheet.py`
- Delete: `src/clasificador_video/ui/filmstrip.py`
- Test: `tests/ui/test_clip_sheet.py` (nuevo), borrar `tests/ui/test_filmstrip.py`

Reemplaza `Filmstrip`. Lo que **se conserva** de él, portándolo:

- scrub de la miniatura al pasar el mouse (`mouseMoveEvent` + caché de
  escalados) — ya funciona, no se reescribe desde cero;
- selección múltiple con Shift/Ctrl+click y ancla;
- señales `clip_clicked(int)` y `selection_changed(list)`;
- el truco de no reconstruir en `select_clip` (comentario del renglón 640 de
  `main_window.py`): reconstruir dentro del `mousePressEvent` del propio widget
  provocaba SIGSEGV en macOS. **No perder ese comportamiento.**

Lo que **cambia**:

| Antes | Ahora |
|---|---|
| `setFixedHeight(220)` | sin alto fijo; ocupa la columna completa |
| Tile fija 150×80 apaisada | tile de proporción real del clip |
| Grilla plana | **agrupada por cuarto**, con encabezado por grupo |
| Etiqueta de cuarto bajo la miniatura | franja de color + glifo, como el mockup |

**Por qué la agrupación entra aquí y no más adelante:** el mockup muestra la
hoja agrupada (`SIN CLASIFICAR 12`, `COCINA 24`). Si la F2 entrega una grilla
plana, la comparación lado a lado va a diferir en toda la columna derecha y el
Candado 3 deja de servir para juzgar la fase. Agrupar por `categoria_path[0]`
son unas decenas de renglones y usa datos que ya existen.

Lo que **no** entra aquí es que los encabezados sean **pegajosos** al scroll:
eso necesita un widget que escuche el scroll y rinde de verdad cuando hay
filtros. Queda para la fase de filtros. Al cerrar la F2, los encabezados se
desplazan con el contenido: es una diferencia esperada y anotada.

**La proporción de cada tarjeta se calcula, no se declara**: QSS no tiene
`aspect-ratio`. `ClipCard.setFixedSize(ancho, round(ancho / aspecto))`, con el
ancho de columna derivado del ancho disponible como ya hace
`Filmstrip._relayout_grid`.

- [ ] **Step 1: Tests** — una tarjeta por clip; una tarjeta vertical es más
      alta que ancha y una horizontal al revés; el hover cambia el frame
      mostrado y `leaveEvent` vuelve al póster; Shift+click selecciona el rango;
      Ctrl+click alterna; `set_current` no reconstruye los widgets (comparar
      identidad de objetos antes y después); `update_clips` preserva los
      pixmaps ya cargados.
- [ ] **Step 2-5:** como arriba.

**Nota de traducción CSS→Qt:** el desvanecido al pie de la hoja
(`mask-image`) no existe en QSS. Se resuelve con un `QLabel` hijo, pegado al
borde inferior, con `qlineargradient` de transparente a `BG_SURFACE_0` y
`WA_TransparentForMouseEvents`.

---

### Task 9: La `MainWindow` nueva

**Files:**
- Rewrite: `src/clasificador_video/ui/main_window.py`
- Modify: `src/clasificador_video/ui/theme.py` (borrar los alias de la F1)
- Test: `tests/ui/test_main_window.py`

Estructura exacta:

```
QVBoxLayout(self), márgenes 0, espaciado 0
├── TitleBar                       (fijo 36)
├── QHBoxLayout, márgenes 0, espaciado 0
│   ├── RoomRail                   (fijo 200)
│   ├── VideoStage                 (ancho fijo calculado)
│   ├── ToolColumn                 (fijo 56)
│   └── ClipSheet                  (stretch 1, mínimo 340)
└── StatusBar                      (fijo 24)
```

**Cero `addStretch` verticales y cero widgets sueltos entre esas tres filas.**
Si aparece uno, volvieron las bandas.

Dimensionado del video, en `resizeEvent`:

```python
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._resize_video_stage()

    def _resize_video_stage(self) -> None:
        """El alto del cuerpo se calcula, no se lee de los hijos: durante
        resizeEvent los hijos todavia tienen el tamaño anterior."""
        alto_cuerpo = self.height() - theme.TITLEBAR_HEIGHT - theme.STATUSBAR_HEIGHT
        aspecto = self.aspect_ratio_for(self.current_index)
        ancho = VideoStage.width_for(alto_cuerpo, aspecto)
        maximo = self.width() - theme.RAIL_WIDTH - theme.TOOLCOL_WIDTH - theme.SHEET_MIN_WIDTH
        self.video_stage.setFixedWidth(max(1, min(ancho, maximo)))
```

`_resize_video_stage` se llama también al cambiar de clip (`select_clip`,
`handle_arrow`, `load_clips`), porque el aspecto puede cambiar entre clips.

Lo que se porta sin cambios de comportamiento: `handle_key_press`,
`handle_arrow`, `select_clip`, `_bulk_targets`, `_apply_categoria_to_targets`,
autosave con debounce y su hilo, `_schedule_thumbnails` y el sistema de
generaciones, `_on_export_manifest`, `_on_import_folders`, atajos.

Widgets que **se borran en este mismo commit** (lista de ejecución del plan
maestro): `legend_label`, `ingest_list`, `ingest_title_label`,
`inspector_panel` y sus tres etiquetas, `scrub_time_label`, `top_bar`,
`position_label`, `progress_label`, `unclassified_badge` (su información pasa a
`StatusBar` y `RoomRail`), `quality_combo` (lo reemplaza `SegmentedControl`),
`room_list_widget` y `_build_room_row_widget`, `import_button`,
`_refresh_room_counts`.

`subroom_banner`, `_handle_subroom_key` y `SUBROOM_CANDIDATES` **se quedan**
hasta la F3, que es la que arranca los subcuartos de raíz. Se cuelgan de
`RoomRail` como banner temporal.

#### `app.py` también se rompe — no está solo en `main_window.py`

`_restore_session` (`app.py:70-78`) manipula **dos widgets que esta tarea
borra**:

```python
window.room_list_widget.clear()
window.room_list_widget.addItems(window.room_selection.active_rooms())
window.legend_label.setText(_build_legend_text(...))
```

Con la ventana nueva eso es un `AttributeError` **al recuperar una sesión
guardada**, que es justo el camino que casi nunca se prueba a mano porque hay
que tener una sesión a medias en disco. Y `tests/test_app.py` —que sí lo
cubre— está excluido del comando de tests por su cuelgue preexistente, así que
**nadie se iba a enterar hasta que le pasara a Bruno**.

Reemplazo: `window.room_rail.set_rooms(window.room_selection.active_rooms(), {})`
y borrar la línea de la leyenda junto con el import de `_build_legend_text`.

**Limitación aceptada:** una sesión restaurada no vuelve a correr `ffprobe`,
así que `_clip_sizes` queda vacío y todos los clips se dimensionan como 16:9
hasta reimportar. Es el mismo comportamiento que ya tiene `_clip_durations`
hoy. Se resuelve en la F9, junto con los proxies.

#### Mapa de los métodos de la `MainWindow` vieja

Los 783 renglones actuales tienen métodos que no son widgets y que el plan no
puede dejar sin destino, o sobreviven de contrabando:

| Método actual | Destino |
|---|---|
| `_build_legend_text` | **Se borra.** La leyenda de una línea no existe en el mockup |
| `_build_room_row_widget` | Se muda a `RoomRail` como fila interna |
| `_refresh_room_counts` | Se muda a `RoomRail.set_rooms(rooms, counts)` |
| `_update_toolbar_stats` | Se parte: progreso → `RoomRail`, aviso → `StatusBar` |
| `_update_inspector` | Se parte: nombre y datos técnicos → `StatusBar`, cuarto y estado → badges del `VideoStage` |
| `_update_scrub_time_label` | Se muda a los overlays del `VideoStage` |
| `_update_scrub_bar` | Se queda en `MainWindow`, apuntando a `video_stage.scrub_bar` |
| `_tick_playhead` | Se queda igual |
| `_tick_saved_indicator` | Llama a `title_bar.set_saved_seconds(...)` |
| `_update_subroom_banner` | Se queda hasta la F3, apuntando al banner del `RoomRail` |
| `_on_quality_changed` | Se reconecta a `SegmentedControl.selected` en vez de `QComboBox.currentTextChanged` |
| `_refresh_filmstrip` | Pasa a `_refresh_sheet`, hablándole a `ClipSheet` |
| `_on_import_folders`, `_refresh_ingest_list` | `_on_import_folders` se queda (lo dispara `RoomRail`); `_refresh_ingest_list` **se borra** con el panel |
| `handle_key_press`, `handle_arrow`, `select_clip`, `_bulk_targets`, `_apply_categoria_to_targets`, autosave, `_schedule_thumbnails`, `_on_thumbnail_ready`, `_on_export_manifest`, `attach_subroom_or_resolve`, `_ask_parent_room`, `closeEvent` | Se quedan sin cambios de comportamiento |

**Detalle de foco:** con botones reales en la barra de título y el rail, la
tecla `Espacio` puede activar el botón que tenga el foco en vez de
reproducir. Todo botón decorativo o de acción poco frecuente lleva
`setFocusPolicy(Qt.NoFocus)`. Hoy no pasa porque casi no hay botones enfocables
en el camino del teclado.

- [ ] **Step 1: Correr la suite y capturar la lista exacta de tests rotos.**
      Esperados (conteo de referencias hechas sobre el árbol actual):
      `legend_label` 6, `import_button` 3, `ingest_list` 3,
      `ingest_title_label` 2, `inspector_*` 6, `scrub_time_label` 6,
      `position_label` 1, `progress_label` 2, `unclassified_badge` 2,
      `room_list_widget` 3, `quality_combo` 2, `filmstrip` 34.

- [ ] **Step 2: Decidir test por test, sin borrar en bloque.** Tres categorías:
  - **Se reescribe contra el widget nuevo** — el comportamiento sigue vivo, solo
    cambió de casa. Ej.: `test_toolbar_muestra_posicion_y_resumen_de_estado`
    pasa a interrogar `StatusBar` y `RoomRail`.
  - **Se borra** — el comportamiento murió a propósito. Ej.:
    `test_material_importado_tiene_encabezado_propio`.
  - **Se conserva tal cual** — no toca UI. Ej.: los de autosave y export.

  **Ningún test se borra sin escribir en el commit por qué murió.**

- [ ] **Step 3: Escribir los tests nuevos de estructura**

```python
# tests/ui/test_main_window.py
from clasificador_video.ui import theme


def test_la_ventana_no_tiene_bandas_horizontales(qtbot):
    """El layout raiz solo puede tener tres filas: barra de titulo,
    cuerpo y barra de estado. Cualquier cuarta fila es una banda que le
    roba altura al video."""
    window = _window_with_video(qtbot)
    raiz = window.layout()
    assert raiz.count() == 3


def test_alturas_fijas_de_las_barras(qtbot):
    window = _window_with_video(qtbot)
    assert window.title_bar.height() == theme.TITLEBAR_HEIGHT
    assert window.status_bar.height() == theme.STATUSBAR_HEIGHT


def test_anchos_fijos_de_los_rails(qtbot):
    window = _window_with_video(qtbot)
    assert window.room_rail.width() == theme.RAIL_WIDTH
    assert window.tool_column.width() == theme.TOOLCOL_WIDTH


def test_un_clip_vertical_ocupa_el_ancho_del_mockup(qtbot):
    """La medida objetiva de la F2: 1600x1000, clip 9:16.
    Cuerpo = 1000 - 36 - 24 = 940. Video = 940 * 9/16 = 529."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    qtbot.waitExposed(window)
    window._clip_sizes = {0: (2160, 3840)}
    window.load_clips([Clip(orden=1, ruta=Path("/tmp/a.mp4"), categoria_path=[], fps=29.97)])
    window._resize_video_stage()
    assert window.video_stage.width() == 529


def test_un_clip_horizontal_no_desborda_la_hoja(qtbot):
    """El video crece hasta donde la hoja conserva su minimo."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    qtbot.waitExposed(window)
    window._clip_sizes = {0: (3840, 2160)}
    window.load_clips([Clip(orden=1, ruta=Path("/tmp/a.mp4"), categoria_path=[], fps=29.97)])
    window._resize_video_stage()
    maximo = 1600 - theme.RAIL_WIDTH - theme.TOOLCOL_WIDTH - theme.SHEET_MIN_WIDTH
    assert window.video_stage.width() == maximo


def test_cambiar_de_clip_reajusta_el_ancho_del_video(qtbot):
    """Decision tomada con Bruno: la pantalla salta al cambiar de
    orientacion, priorizando el aprovechamiento sobre la estabilidad."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    qtbot.waitExposed(window)
    window._clip_sizes = {0: (2160, 3840), 1: (3840, 2160)}
    window.load_clips([
        Clip(orden=1, ruta=Path("/tmp/a.mp4"), categoria_path=[], fps=29.97),
        Clip(orden=2, ruta=Path("/tmp/b.mp4"), categoria_path=[], fps=29.97),
    ])
    window._resize_video_stage()
    vertical = window.video_stage.width()
    window.handle_arrow("next")
    horizontal = window.video_stage.width()
    assert horizontal > vertical
```

- [ ] **Step 4: Reescribir `main_window.py`.**
- [ ] **Step 5: Arreglar `app.py::_restore_session`** y actualizar
      `tests/test_app.py` aunque esté excluido del comando: si se deja
      desactualizado, la próxima persona que lo corra no va a saber si falla
      por el cuelgue conocido o porque de verdad se rompió algo.
- [ ] **Step 6: Borrar los alias de compatibilidad de `theme.py`** y ajustar
      los imports que quedaron.
- [ ] **Step 7: Probar a mano el camino de sesión restaurada**, que ningún
      test del comando habitual cubre: abrir la app, clasificar algo, cerrarla,
      volver a abrirla y aceptar la recuperación.
- [ ] **Step 8: Correr la suite completa.** Verde.

---

### Task 10: Verificación visual y cierre de la F2

- [ ] **Step 1: Correr el arnés y mirar la imagen.**

```bash
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/comp-f2.png
```

- [ ] **Step 2: Recorrer la lista de verificación**, anotando cada diferencia
      contra el mockup como *arreglada* o *intencional y por qué*:

  1. proporciones de las cuatro columnas;
  2. alturas de barra de título y barra de estado;
  3. colores de fondo, líneas y texto en los tres niveles;
  4. posición de cada overlay sobre el video;
  5. jerarquía tipográfica (qué se lee primero);
  6. ninguna franja negra alrededor del video.

- [ ] **Step 3: Medidas objetivas.** Todas tienen que dar:

| Comprobación | Cómo |
|---|---|
| Video vertical = 529 px a 1600×1000 | `test_un_clip_vertical_ocupa_el_ancho_del_mockup` |
| Layout raíz con 3 filas | `test_la_ventana_no_tiene_bandas_horizontales` |
| Barras 36 / 24 px | `test_alturas_fijas_de_las_barras` |
| Rails 200 / 56 px | `test_anchos_fijos_de_los_rails` |
| Cero hexadecimales fuera del tema | `test_ningun_modulo_declara_colores_fuera_del_tema` |

- [ ] **Step 4: Confirmar que la app sigue haciendo todo lo de antes**, a mano
      y con material real: importar, clasificar con 1–9, marcar in/out,
      reproducir, cambiar calidad, seleccionar varios y asignar cuarto,
      exportar el manifest.

- [ ] **Step 5: Verificar la lista de ejecución.** Todo lo asignado a la F2 en
      el plan maestro tiene que estar borrado. `grep -rn` de cada nombre en
      `src/` debe dar cero.

- [ ] **Step 6: Commit**, con la imagen de comparación mencionada y las
      diferencias intencionales listadas.

---

## Diferencias esperadas al cerrar la F2

El Candado 3 dice que la fase no cierra hasta haber comparado la imagen contra
el mockup. Para que ese criterio no sea ambiguo, **estas son las únicas
diferencias admisibles**. Cualquier otra es un defecto a arreglar antes de
cerrar la fase.

| Diferencia | Por qué | Se resuelve en |
|---|---|---|
| No hay conmutador Clip/Hoja en la barra de título | El modo hoja no existe todavía | F8 |
| Los encabezados de grupo se van con el scroll en vez de quedarse pegados | Necesita un widget que escuche el scroll; rinde con filtros | F5 |
| No hay barra de filtros ni chip de cola | | F5 |
| No hay historial de deshacer en el rail | El bloque queda reservado en el `RoomRail` | F4 |
| No hay badge de "destacado" ni selector de velocidad | | F6, F7 |
| El póster de la miniatura es el frame del medio, no el del 25% | | F6 |
| El badge de proxy no muestra datos reales | `match_proxies` sigue desconectado | F9 |
| Los badges no tienen desenfoque de fondo | QSS no tiene `backdrop-filter`; se compensa con más opacidad | nunca |
| Sigue existiendo el banner de subcuarto | Los subcuartos mueren en la F3 | F3 |

## Lo que sigue, en breve

Resumen para tener el mapa; **el detalle de cada una se escribe cuando toque**,
no ahora.

- **F3 — Cuartos planos.** Arrancar los subcuartos de `keyboard.py`,
  `rooms.py`, `main_window.py` y borrar `category_path.py` completo. Rail de
  cuartos editable en vivo (renombrar, reordenar, borrar). Quitar el diálogo de
  configuración inicial y su exigencia en `arrancar()`. Terminada cuando
  presionar `3` con "Recámara 1" clasifica y avanza.
- **F4 — Deshacer.** Pila de undo con acciones agrupadas (una asignación en
  lote = una entrada), historial visible en el rail con revertir por fila, y
  `Ctrl+Z` registrado de verdad. Se adelanta respecto del orden anterior
  porque hoy la app **anuncia** deshacer en su leyenda y no lo tiene: es la
  única promesa rota que ve el usuario.
- **F5 — Filtros como cola.** Barra de dos grupos (Mostrar / Estado), `←/→`
  recorriendo solo el conjunto filtrado, indicador "N de M en la cola", badge
  de sin clasificar clickeable, y aquí sí los encabezados pegajosos.
- **F6 — Reproducción rápida.** Autoplay al cambiar de clip, velocidad
  1×/2×/4× reusando `SegmentedControl`, arranque al 25%, póster de miniatura al
  25%, precarga del siguiente clip, `,`/`.` frame por frame.
- **F7 — El resto del teclado.** Flags en lote, `S` igual al anterior, estado
  destacado (`⇧P`), paleta `⏎` para buscar y crear cuartos, `F` solo video.
- **F8 — Modo hoja y pincel.** `⇥` para alternar, hoja a pantalla completa,
  conmutador en la barra de título, pincel de cuarto con los cinco requisitos
  de `DECISIONES.md`, `+`/`−` para el tamaño de miniatura.
- **F9 — Datos que faltan.** Conectar `match_proxies()` a la importación y
  derivar la orientación del manifest del material. Se atrasa a propósito: es
  invisible para el usuario y no bloquea nada.
- **F10 — Barrido final.** Lista de ejecución vacía, comparación final de las
  dos pantallas, diferencias escritas y justificadas.

> El plan maestro tenía once fases y esta revisión las deja en once contando la
> F0 y la F1: se disolvió la vieja F4 ("miniaturas verticales y agrupación")
> porque la F2 se quedó con su contenido, y se adelantó deshacer.

## Pendiente obligatorio: reanalizar al cerrar la F2

**Este plan solo es confiable hasta el final de la F2.** De la F3 en adelante,
todo se engancha a clases, señales y widgets que la F2 inventa, y hoy no
existen. El resumen de arriba es un mapa, no un plan.

Al terminar la F2, antes de escribir una línea de la F3, hay que:

1. **Rehacer el análisis** de la app contra el mockup, como el de
   `ANALISIS-2026-08-08-app-actual-vs-mockup.md`, ahora contra el código nuevo.
2. **Revisar el orden de las fases que quedan** con lo que se haya aprendido —
   esta misma revisión ya movió agrupación y deshacer de lugar, y es probable
   que vuelva a pasar.
3. **Actualizar la lista de ejecución** del plan maestro: tachar lo muerto y
   agregar lo que la F2 haya dejado provisional.
4. **Recién entonces** escribir el plan detallado de la F3 y la F4.

Escribir hoy el detalle de la F3 en adelante sería inventar una API y
descubrir después que no calza. Un plan desactualizado tiene autoridad y se
sigue en vez de pensarlo: es peor que no tenerlo.
