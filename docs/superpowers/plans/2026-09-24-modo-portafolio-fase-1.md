# Modo Portafolio, fase 1: app separada + lector de `.prproj` - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sentar las bases de Clipify Portafolio como **aplicación
independiente** dentro del mismo repo — su propio punto de entrada, su
propia ventana, sin tocar ni una línea de `MainWindow` del Clipify
normal — y construir la primera pieza funcional de verdad: leer un
`.prproj`, encontrar todas sus secuencias, y sacar de ahí la lista de
clips usados (archivo de origen + rangos in/out). Esto es lo mínimo que
hace falta para que el módulo Importar tenga algo real que mostrar.

**Architecture:**

- **Dos apps, un motor.** `clasificador_video` (el paquete de siempre)
  no cambia su comportamiento en nada. Se agrega un paquete hermano,
  `clasificador_video_portafolio/`, que es la app nueva: tiene su propio
  `main()`, su propia clase de ventana, y ningún import de
  `clasificador_video.ui.*`. Lo que SÍ importa del paquete viejo es
  explícitamente motor sin UI: `prproj_xml`, `proxy_gen`, `probe`,
  `player` (el wrapper de mpv), `thumbnails`. Nunca importa
  `main_window.py`, `room_rail.py`, `clip_sheet.py` ni nada de
  `clasificador_video/ui/`.
- **Entry point propio**, registrado aparte en `pyproject.toml`
  (`clipify-portafolio = "clasificador_video_portafolio.app:main"`), para
  que sea un ejecutable de verdad, no un modo escondido detrás de una
  bandera.
- **Lector de `.prproj` nuevo**, `clasificador_video_portafolio/lector_de_entregas.py`:
  puro (sin Qt), recibe la ruta de un `.prproj`, usa
  `prproj_xml.leer_prproj` para el XML (ya existe, ya sabe descomprimir
  el gzip), camina TODAS las secuencias del proyecto (no una), y para
  cada una recorre sus tracks de video juntando qué archivo de origen
  aparece en pantalla y con qué rango. Un mismo archivo puede aparecer
  con más de un rango (usado dos veces) o en más de una secuencia — se
  juntan sin duplicar.
- Esta fase **no construye ninguna pantalla todavía** — ni Importar, ni
  Revisar, ni Armar/Entregar. Es la base sobre la que esos tres módulos
  se construyen en fases siguientes (ver "Qué sigue" al final). Sí se
  construye la ventana vacía de la app nueva, para que el punto de
  entrada exista y se pueda lanzar, aunque no haga nada visible todavía
  más que confirmar que es una ventana distinta a la del Clipify normal.

**Tech Stack:** Python 3, PySide6 (Qt) para la ventana nueva,
`xml.etree.ElementTree` para el `.prproj` (reusa `prproj_xml.py`), pytest
+ pytest-qt, `QT_QPA_PLATFORM=offscreen`.

**Spec:** `docs/superpowers/specs/2026-09-24-modo-portafolio-design.md`

---

## Cómo correr la suite completa

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Los tests de esta app nueva viven en `tests_portafolio/`, paralelo a
`tests/`, para que quede tan separado en las pruebas como en el código:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ -q
```

---

### Task 1: el paquete nuevo y su punto de entrada

**Files:**
- Create: `src/clasificador_video_portafolio/__init__.py`
- Create: `src/clasificador_video_portafolio/app.py`
- Modify: `pyproject.toml`
- Test: `tests_portafolio/test_app.py`

- [ ] **Step 1: Escribir la prueba que falla**

```python
"""La app de Portafolio abre su propia ventana, separada de MainWindow
del Clipify normal -- spec 2026-09-24-modo-portafolio-design.md."""
from clasificador_video_portafolio.app import VentanaPortafolio


def test_la_ventana_de_portafolio_no_es_la_del_clipify_normal(qtbot):
    from clasificador_video.ui.main_window import MainWindow

    ventana = VentanaPortafolio()
    qtbot.addWidget(ventana)

    assert not isinstance(ventana, MainWindow)
    assert ventana.windowTitle().startswith("Clipify Portafolio")


def test_la_ventana_arranca_en_el_modulo_importar(qtbot):
    ventana = VentanaPortafolio()
    qtbot.addWidget(ventana)

    assert ventana.modulo_actual == "importar"
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_app.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'clasificador_video_portafolio'`

- [ ] **Step 3: Crear el paquete y la ventana mínima**

`src/clasificador_video_portafolio/__init__.py`:

```python
"""Clipify Portafolio: app separada del Clipify normal, para armar
videos de portafolio/anuncios juntando clips de varios proyectos ya
entregados. Comparte MOTOR con clasificador_video (lectura/escritura de
.prproj, proxies, mpv) pero nunca su UI -- spec
docs/superpowers/specs/2026-09-24-modo-portafolio-design.md."""
__version__ = "0.1.0"
```

`src/clasificador_video_portafolio/app.py`:

```python
"""Punto de entrada de Clipify Portafolio.

Ventana propia, sin heredar ni componer nada de
`clasificador_video.ui.main_window.MainWindow` -- son dos apps, un solo
motor. Ver la spec para el porque de la separacion.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class VentanaPortafolio(QWidget):
    """La ventana raiz. Por ahora solo confirma que existe y en que
    modulo esta -- los tres modulos reales (Importar, Revisar, Armar y
    entregar) se construyen en las fases siguientes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clipify Portafolio")
        self.modulo_actual = "importar"
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Clipify Portafolio — módulo Importar"))


def main() -> None:
    app = QApplication(sys.argv)
    ventana = VentanaPortafolio()
    ventana.resize(1200, 800)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Registrar el entry point**

En `pyproject.toml`, junto a `[project.scripts]`:

```toml
[project.scripts]
clasificador = "clasificador_video.app:main"
clipify-portafolio = "clasificador_video_portafolio.app:main"
```

- [ ] **Step 5: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_app.py -q`
Expected: PASS (2 tests)

- [ ] **Step 6: Correr la suite completa y comprobar que nada del Clipify normal se rompió**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS, mismo conteo que antes de este task — este paquete
nuevo no toca ni un archivo de `clasificador_video/`.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video_portafolio/ pyproject.toml tests_portafolio/test_app.py
git commit -m "$(cat <<'EOF'
Crear Clipify Portafolio como app separada del Clipify normal

Primer paso de la fase 1 (spec 2026-09-24): paquete propio,
ventana propia, entry point propio (clipify-portafolio). No
comparte UI con clasificador_video.ui -- solo compartirá motor
(prproj_xml, proxy_gen, player, thumbnails) a medida que las
piezas siguientes lo necesiten.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `lector_de_entregas.clips_usados_en` — un archivo, todas sus secuencias

**Files:**
- Create: `src/clasificador_video_portafolio/lector_de_entregas.py`
- Create: `tests_portafolio/test_lector_de_entregas.py`
- Fixture: `tests_portafolio/fixtures/entrega_dos_secuencias.prproj` (un
  `.prproj` real, chico, con dos secuencias que usan clips distintos y
  uno en común — grabarlo a mano desde Premiere o adaptar uno de los
  fixtures que ya usa `tests/test_prproj_xml.py` / `tests/test_prproj_generador.py`)

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
"""Leer un .prproj hacia atras: que clips se usaron, en que rango,
juntando TODAS las secuencias -- spec
2026-09-24-modo-portafolio-design.md ("se leen todas las secuencias,
no una sola")."""
from pathlib import Path

from clasificador_video_portafolio import lector_de_entregas as lector

FIXTURES = Path(__file__).parent / "fixtures"


def test_junta_clips_de_dos_secuencias_distintas():
    usados = lector.clips_usados_en(FIXTURES / "entrega_dos_secuencias.prproj")

    nombres = {u.ruta_origen.name for u in usados}
    assert nombres == {"clip_014.mov", "clip_016.mov", "clip_031.mov"}


def test_un_clip_usado_en_dos_secuencias_no_se_duplica_pero_junta_rangos():
    usados = lector.clips_usados_en(FIXTURES / "entrega_dos_secuencias.prproj")

    compartido = next(u for u in usados if u.ruta_origen.name == "clip_014.mov")
    assert len(compartido.rangos) == 2  # aparece en las dos secuencias


def test_rango_trae_in_y_out_en_ticks_de_premiere():
    usados = lector.clips_usados_en(FIXTURES / "entrega_dos_secuencias.prproj")

    clip = next(u for u in usados if u.ruta_origen.name == "clip_016.mov")
    rango = clip.rangos[0]
    assert rango.entra_en < rango.sale_en


def test_prproj_sin_secuencias_da_lista_vacia(tmp_path):
    from clasificador_video import prproj_xml
    import xml.etree.ElementTree as ET

    vacio = ET.Element("PremiereData")
    ruta = tmp_path / "vacio.prproj"
    prproj_xml.escribir_prproj(vacio, ruta)

    assert lector.clips_usados_en(ruta) == []
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_lector_de_entregas.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'clasificador_video_portafolio.lector_de_entregas'`

- [ ] **Step 3: Escribir el módulo**

Antes de escribir la implementación real: **leer cómo está armado el
XML de una secuencia** mirando `prproj_generador.py` (funciones
`clonar_secuencia_con_medidas`, `_vaciar_timeline_de_secuencia`,
`crear_bin_hijo`) y un `.prproj` de ejemplo de
`tests/test_prproj_generador.py` — esas funciones ya conocen la
estructura de `Sequence` → `Track` → `ClipItem` → referencia a `Media`,
y hay que caminarla al revés (leer, no escribir). No adivinar la
estructura del XML sin mirarla primero.

```python
"""Leer un .prproj hacia atras: que archivos de origen se usaron, en
que rango, en CUALQUIERA de sus secuencias.

Sin Qt. Es la mitad "lectura" de lo que prproj_generador.py hace en
"escritura" -- mismo formato de archivo, sentido contrario. Spec:
docs/superpowers/specs/2026-09-24-modo-portafolio-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from clasificador_video import prproj_xml


@dataclass(frozen=True)
class RangoUsado:
    entra_en: int   # ticks de Premiere, igual que ClipItem/Start
    sale_en: int
    secuencia: str  # nombre de la secuencia donde aparece


@dataclass
class ClipUsado:
    ruta_origen: Path
    rangos: list[RangoUsado] = field(default_factory=list)


def clips_usados_en(ruta_prproj: Path) -> list[ClipUsado]:
    """Todos los clips usados en CUALQUIER secuencia del .prproj, con
    sus rangos. Un archivo usado en mas de un lugar aparece una sola vez
    en la lista, con varios `RangoUsado`.

    No distingue "la secuencia buena" de un borrador -- se decidio en
    la spec no adivinar eso, y juntar todo.
    """
    raiz = prproj_xml.leer_prproj(ruta_prproj)
    por_ruta: dict[Path, ClipUsado] = {}
    for secuencia in raiz.iter("Sequence"):
        nombre_secuencia = secuencia.get("ObjectID") or secuencia.findtext("Name") or "?"
        for clip_item in secuencia.iter("ClipItem"):
            ruta = _ruta_de_origen(raiz, clip_item)
            if ruta is None:
                continue
            inicio = clip_item.find("Start")
            fin = clip_item.find("End")
            if inicio is None or fin is None:
                continue
            rango = RangoUsado(
                entra_en=int(inicio.text), sale_en=int(fin.text),
                secuencia=nombre_secuencia,
            )
            if ruta not in por_ruta:
                por_ruta[ruta] = ClipUsado(ruta_origen=ruta)
            por_ruta[ruta].rangos.append(rango)
    return list(por_ruta.values())


def _ruta_de_origen(raiz, clip_item) -> Path | None:
    """La ruta de archivo detras de un ClipItem, siguiendo su referencia
    a Media/PathURL. `None` si el ClipItem no aparece resolver (algunos
    son placeholders o clips compuestos que esta fase no cubre)."""
    ref = clip_item.get("ObjectRef")
    if not ref:
        return None
    media = raiz.find(f".//Media[@ObjectID='{ref}']")
    if media is None:
        return None
    ruta = media.findtext("PathURL") or media.findtext("ActualMediaFilePath")
    return Path(ruta) if ruta else None
```

**Nota importante para quien implemente esto:** los nombres de tag
(`ClipItem`, `Start`, `End`, `ObjectRef`, `PathURL`) son un punto de
partida razonable pero **hay que verificarlos contra un `.prproj` real
o contra lo que `prproj_generador.py` ya asume** antes de confiar en
ellos — si no calzan, el fixture del Step 1 no va a servir de nada.
Ajustar el código a lo que el XML realmente dice, nunca al revés.

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_lector_de_entregas.py -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/lector_de_entregas.py tests_portafolio/
git commit -m "$(cat <<'EOF'
Leer un .prproj hacia atrás: clips_usados_en

Camina TODAS las secuencias de un .prproj (no una sola -- decisión
de la spec) y junta, por archivo de origen, los rangos in/out en
los que se usó. Es la base del módulo Importar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `lector_de_entregas.medios_faltantes` — qué no vincula

**Files:**
- Modify: `src/clasificador_video_portafolio/lector_de_entregas.py`
- Test: `tests_portafolio/test_lector_de_entregas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_medios_faltantes_detecta_archivo_que_no_existe(tmp_path):
    usados = [
        lector.ClipUsado(ruta_origen=tmp_path / "no_existe.mov"),
        lector.ClipUsado(ruta_origen=Path(__file__)),  # este sí existe
    ]

    faltantes = lector.medios_faltantes(usados)

    assert faltantes == [usados[0]]


def test_medios_faltantes_vacio_si_todo_vincula():
    usados = [lector.ClipUsado(ruta_origen=Path(__file__))]

    assert lector.medios_faltantes(usados) == []
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_lector_de_entregas.py -k medios_faltantes -q`
Expected: FAIL con `AttributeError: module '...lector_de_entregas' has no attribute 'medios_faltantes'`

- [ ] **Step 3: Agregar la función**

Al final de `lector_de_entregas.py`:

```python
def medios_faltantes(usados: list[ClipUsado]) -> list[ClipUsado]:
    """Los `ClipUsado` cuyo archivo de origen no se encuentra en disco
    ahora mismo -- para que Importar los señale y ofrezca revincular,
    en vez de fallar en silencio."""
    return [u for u in usados if not u.ruta_origen.exists()]
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_lector_de_entregas.py -q`
Expected: PASS (6 tests en total)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/lector_de_entregas.py tests_portafolio/test_lector_de_entregas.py
git commit -m "$(cat <<'EOF'
lector_de_entregas: medios_faltantes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Qué sigue (fuera de esta fase 1)

Con esta fase, `clips_usados_en` + `medios_faltantes` son suficientes
para que el módulo **Importar** tenga datos reales que mostrar, pero la
pantalla de Importar en sí (la lista de `.prproj` soltados, el drag&drop,
el diálogo de revincular) todavía no existe — es la **fase 2**.

Fases siguientes, en el orden en que tiene sentido construirlas (cada
una depende de la anterior):

- **Fase 2 — módulo Importar de verdad:** drag&drop de `.prproj`,
  persistencia del portafolio (el archivo `.cvportafolio` o el nombre
  que se le ponga — pendiente de decidir, ver la spec), diálogo de
  revincular medios, selector de categoría de proyecto.
- **Fase 3 — módulo Revisar:** rail de proyectos, la escalera
  Descartada/Sin decidir/Elegida con `↓`/`↑` (reusar el patrón de
  `ESCALERA_DE_ESTADO` de `main_window.py`, adaptado a tres peldaños),
  estado de proyecto sin disco conectado, "ver el rodaje completo" con
  generación de miniaturas por lo que se ve en pantalla.
- **Fase 4 — módulo Armar y entregar:** etiquetas de clip, carpeta de
  portafolio con alias (investigar la API de macOS para crear alias de
  Finder desde Python — no es un symlink; probablemente vía
  `Foundation`/`pyobjc` o `osascript`), generación de proxies faltantes
  reusando `proxy_gen.py`, filtro por etiqueta, generación del `.prproj`
  final reusando `prproj_generador.py`.

Cada una de estas merece su propio plan de implementación cuando le
toque, con el mismo nivel de detalle que este.
