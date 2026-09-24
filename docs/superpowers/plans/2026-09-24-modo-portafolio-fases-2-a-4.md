# Modo Portafolio, fases 2-4: Importar, Revisar, Armar y entregar - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Este plan continúa** `docs/superpowers/plans/2026-09-24-modo-portafolio-fase-1.md`
> (ya construido: el paquete `clasificador_video_portafolio` separado del
> Clipify normal, con su propio entry point, y `lector_de_entregas.py`
> que lee un `.prproj` hacia atrás). Las Tasks de aquí siguen la
> numeración desde el Task 4.
>
> **Está pensado para construirse fase por fase, no de un jalón.** Cada
> fase (② Importar, ③ Revisar, ④ Armar y entregar) es un bloque
> independiente de Tasks que termina en un commit funcional y con su
> propia suite en verde. Al arrancar una sesión de construcción, se le
> puede pedir explícitamente "solo la fase 2" o "solo la fase 3" y las
> demás quedan intactas como Tasks sin marcar.

**Goal:** Completar los tres módulos que le faltan a Clipify Portafolio
para ser usable de principio a fin: soltar `.prproj` y que se sumen al
portafolio (Importar), decidir Elegida/Descartada proyecto por proyecto
(Revisar), y etiquetar + generar el `.prproj` de la entrega (Armar y
entregar).

**Architecture:** Todo lo nuevo vive en `clasificador_video_portafolio/`,
igual que la fase 1. El corazón de datos es un módulo nuevo,
`portafolio.py`, puro (sin Qt): es el modelo del portafolio único que
crece para siempre (proyectos importados, categoría de cada uno, estado
de cada clip en su escalera, etiquetas) y su persistencia a disco. Las
pantallas de cada módulo son capas delgadas de Qt encima de ese modelo —
la lógica de negocio nunca vive en un widget, para poder probarla sin
levantar la UI (mismo criterio que ya sigue `clasificador_video` con
`proyecto.py` vs `main_window.py`).

**Tech Stack:** Python 3, PySide6 (Qt) para las pantallas, JSON para la
persistencia del portafolio (mismo patrón que `.cvproj`), pytest +
pytest-qt, `QT_QPA_PLATFORM=offscreen`.

**Spec:** `docs/superpowers/specs/2026-09-24-modo-portafolio-design.md`

---

## Cómo correr la suite completa

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ -q
```

---

# FASE 2 — Importar

### Task 4: `portafolio.py` — el modelo de datos y su persistencia

**Files:**
- Create: `src/clasificador_video_portafolio/portafolio.py`
- Test: `tests_portafolio/test_portafolio.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
"""El portafolio único que crece para siempre: proyectos importados,
categoría, y sus clips -- spec 2026-09-24-modo-portafolio-design.md."""
from pathlib import Path

from clasificador_video_portafolio import portafolio as pf
from clasificador_video_portafolio.lector_de_entregas import ClipUsado, RangoUsado


def test_portafolio_nuevo_empieza_vacio():
    p = pf.Portafolio()
    assert p.proyectos == []


def test_agregar_proyecto_lo_registra_con_su_prproj_de_origen(tmp_path):
    p = pf.Portafolio()
    ruta_prproj = tmp_path / "Casa Reforma — entrega final.prproj"
    clips = [ClipUsado(ruta_origen=tmp_path / "clip_014.mov",
                       rangos=[RangoUsado(0, 100, "Secuencia 1")])]

    proyecto = p.agregar_proyecto("Casa Reforma", ruta_prproj, clips)

    assert proyecto in p.proyectos
    assert proyecto.nombre == "Casa Reforma"
    assert len(proyecto.clips) == 1
    assert proyecto.categoria is None


def test_guardar_y_cargar_redondo(tmp_path):
    p = pf.Portafolio()
    ruta_prproj = tmp_path / "Casa Reforma.prproj"
    clips = [ClipUsado(ruta_origen=tmp_path / "clip_014.mov",
                       rangos=[RangoUsado(0, 100, "Secuencia 1")])]
    p.agregar_proyecto("Casa Reforma", ruta_prproj, clips)
    destino = tmp_path / "Mi Portafolio.cvportafolio"

    p.guardar(destino)
    cargado = pf.Portafolio.cargar(destino)

    assert len(cargado.proyectos) == 1
    assert cargado.proyectos[0].nombre == "Casa Reforma"
    assert cargado.proyectos[0].clips[0].ruta_origen == tmp_path / "clip_014.mov"


def test_cargar_archivo_que_no_existe_da_portafolio_vacio(tmp_path):
    cargado = pf.Portafolio.cargar(tmp_path / "no existe.cvportafolio")
    assert cargado.proyectos == []
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -q`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Escribir el módulo**

```python
"""El portafolio único que crece para siempre.

Sin Qt: guarda proyectos importados (cada uno de un .prproj), sus
clips y el estado de cada uno. La UI de cada módulo (Importar, Revisar,
Armar y entregar) es una capa encima de esto -- spec
docs/superpowers/specs/2026-09-24-modo-portafolio-design.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from clasificador_video_portafolio.lector_de_entregas import ClipUsado

ESTADOS = ("descartada", "sin_decidir", "elegida")


@dataclass
class ClipDelPortafolio:
    ruta_origen: Path
    proyecto: str            # nombre del proyecto al que pertenece
    estado: str = "sin_decidir"
    etiquetas: list[str] = field(default_factory=list)
    fuera_de_secuencia: bool = False  # True si vino de "ver el rodaje completo"


@dataclass
class ProyectoImportado:
    nombre: str
    ruta_prproj: Path
    categoria: str | None = None
    clips: list[ClipDelPortafolio] = field(default_factory=list)


class Portafolio:
    def __init__(self) -> None:
        self.proyectos: list[ProyectoImportado] = []

    def agregar_proyecto(self, nombre: str, ruta_prproj: Path,
                         clips_usados: list[ClipUsado]) -> ProyectoImportado:
        """Registra un .prproj recién importado. Si YA existe un
        proyecto con esa ruta de .prproj, se actualiza en vez de
        duplicarse (spec: re-soltar el mismo .prproj actualiza)."""
        existente = self._proyecto_por_ruta(ruta_prproj)
        clips = [
            ClipDelPortafolio(ruta_origen=u.ruta_origen, proyecto=nombre)
            for u in clips_usados
        ]
        if existente is not None:
            self._fusionar_clips(existente, clips)
            return existente
        proyecto = ProyectoImportado(nombre=nombre, ruta_prproj=ruta_prproj,
                                     clips=clips)
        self.proyectos.append(proyecto)
        return proyecto

    def _proyecto_por_ruta(self, ruta_prproj: Path) -> ProyectoImportado | None:
        return next((p for p in self.proyectos if p.ruta_prproj == ruta_prproj), None)

    def _fusionar_clips(self, proyecto: ProyectoImportado,
                        nuevos: list[ClipDelPortafolio]) -> None:
        """Un re-import no pisa el estado/etiquetas de clips que ya
        estaban -- solo agrega los que faltan. El caso de "el clip ya no
        aparece en la nueva versión" (huérfano) se resuelve en la fase
        de Revisar, no aquí."""
        rutas_ya = {c.ruta_origen for c in proyecto.clips}
        proyecto.clips.extend(c for c in nuevos if c.ruta_origen not in rutas_ya)

    def guardar(self, destino: Path) -> None:
        datos = {
            "proyectos": [
                {
                    "nombre": p.nombre,
                    "ruta_prproj": str(p.ruta_prproj),
                    "categoria": p.categoria,
                    "clips": [
                        {
                            "ruta_origen": str(c.ruta_origen),
                            "proyecto": c.proyecto,
                            "estado": c.estado,
                            "etiquetas": c.etiquetas,
                            "fuera_de_secuencia": c.fuera_de_secuencia,
                        }
                        for c in p.clips
                    ],
                }
                for p in self.proyectos
            ]
        }
        destino.write_text(json.dumps(datos, indent=2), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta: Path) -> "Portafolio":
        p = cls()
        if not ruta.exists():
            return p
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        for pd in datos.get("proyectos", []):
            proyecto = ProyectoImportado(
                nombre=pd["nombre"], ruta_prproj=Path(pd["ruta_prproj"]),
                categoria=pd.get("categoria"),
            )
            for cd in pd.get("clips", []):
                proyecto.clips.append(ClipDelPortafolio(
                    ruta_origen=Path(cd["ruta_origen"]), proyecto=cd["proyecto"],
                    estado=cd.get("estado", "sin_decidir"),
                    etiquetas=cd.get("etiquetas", []),
                    fuera_de_secuencia=cd.get("fuera_de_secuencia", False),
                ))
            p.proyectos.append(proyecto)
        return p
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/portafolio.py tests_portafolio/test_portafolio.py
git commit -m "$(cat <<'EOF'
portafolio.py: el modelo del portafolio único, con guardar/cargar

Re-soltar el mismo .prproj actualiza el proyecto existente en vez
de duplicarlo; los clips que ya tenían estado/etiquetas no se
pisan.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `portafolio.Portafolio.medios_faltantes_de` — exponer lo que falta vincular

**Files:**
- Modify: `src/clasificador_video_portafolio/portafolio.py`
- Test: `tests_portafolio/test_portafolio.py`

- [ ] **Step 1: Escribir la prueba que falla**

```python
def test_medios_faltantes_de_un_proyecto(tmp_path):
    p = pf.Portafolio()
    ruta_prproj = tmp_path / "Depto Polanco.prproj"
    clips = [
        ClipUsado(ruta_origen=tmp_path / "existe.mov", rangos=[]),
        ClipUsado(ruta_origen=tmp_path / "no_existe.mov", rangos=[]),
    ]
    (tmp_path / "existe.mov").write_text("x")
    proyecto = p.agregar_proyecto("Depto Polanco", ruta_prproj, clips)

    faltantes = p.medios_faltantes_de(proyecto)

    assert [c.ruta_origen.name for c in faltantes] == ["no_existe.mov"]
```

- [ ] **Step 2: Correr la prueba y comprobar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -k medios_faltantes_de -q`
Expected: FAIL con `AttributeError`

- [ ] **Step 3: Agregar el método a `Portafolio`**

```python
    def medios_faltantes_de(self, proyecto: ProyectoImportado) -> list[ClipDelPortafolio]:
        return [c for c in proyecto.clips if not c.ruta_origen.exists()]

    def revincular(self, clip: ClipDelPortafolio, carpeta_nueva: Path) -> bool:
        """Busca el archivo con el mismo nombre dentro de `carpeta_nueva`
        y actualiza la ruta si lo encuentra. `False` si no estaba ahí --
        no se adivina ni se mueve nada más."""
        candidata = carpeta_nueva / clip.ruta_origen.name
        if not candidata.exists():
            return False
        clip.ruta_origen = candidata
        return True
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -q`
Expected: PASS (5 tests). Agregar también un test para `revincular`
siguiendo el mismo patrón antes de dar el Task por cerrado.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/portafolio.py tests_portafolio/test_portafolio.py
git commit -m "$(cat <<'EOF'
portafolio.py: medios_faltantes_de y revincular

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: pantalla Importar — dropzone y lista

**Files:**
- Create: `src/clasificador_video_portafolio/ui/pantalla_importar.py`
- Modify: `src/clasificador_video_portafolio/app.py` (montar la pantalla en `VentanaPortafolio`)
- Test: `tests_portafolio/ui/test_pantalla_importar.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
"""La pantalla Importar: drag&drop de .prproj, lista de proyectos con
su estado de vinculación -- spec 2026-09-24-modo-portafolio-design.md."""
from clasificador_video_portafolio.ui.pantalla_importar import PantallaImportar


def test_arranca_vacia(qtbot):
    pantalla = PantallaImportar()
    qtbot.addWidget(pantalla)
    assert pantalla.filas == []


def test_importar_prproj_agrega_una_fila(qtbot, tmp_path, monkeypatch):
    pantalla = PantallaImportar()
    qtbot.addWidget(pantalla)
    ruta = tmp_path / "Casa Reforma.prproj"
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_importar.lector.clips_usados_en",
        lambda r: [],
    )

    pantalla.importar(ruta)

    assert len(pantalla.filas) == 1
    assert "Casa Reforma" in pantalla.filas[0].nombre_visible()


def test_importar_con_medios_faltantes_lo_señala(qtbot, tmp_path, monkeypatch):
    from clasificador_video_portafolio.lector_de_entregas import ClipUsado

    pantalla = PantallaImportar()
    qtbot.addWidget(pantalla)
    ruta = tmp_path / "Depto Polanco.prproj"
    faltante = ClipUsado(ruta_origen=tmp_path / "no_existe.mov", rangos=[])
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_importar.lector.clips_usados_en",
        lambda r: [faltante],
    )

    pantalla.importar(ruta)

    assert pantalla.filas[0].tiene_faltantes()
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ui/test_pantalla_importar.py -q`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Escribir la pantalla**

Widget mínimo: `QListWidget` (o layout de filas propias, siguiendo el
patrón de `pantalla_inicio._FilaReciente` del Clipify normal como
referencia de estilo, sin copiarlo) con un método `importar(ruta)` que:
1. llama `lector.clips_usados_en(ruta)`,
2. llama `lector.medios_faltantes(usados)`,
3. agrega una fila al `Portafolio` (inyectado o creado internamente —
   decidir en este Task si `PantallaImportar` recibe el `Portafolio`
   por constructor; recomendado que sí, para que sea la misma instancia
   que usan Revisar y Armar/entregar más adelante),
4. guarda el portafolio a disco.

El drag&drop real (`dragEnterEvent`/`dropEvent` de Qt aceptando
`.prproj`) se agrega en este mismo Task, llamando a `importar()` por
cada archivo soltado — no hace falta una prueba de Qt del evento de
drag en sí (es notoriamente frágil de simular), basta con probar
`importar()` directo como arriba.

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ui/test_pantalla_importar.py -q`
Expected: PASS

- [ ] **Step 5: Montarla en `VentanaPortafolio`**

Reemplazar el `QLabel` de placeholder del Task 1 por `PantallaImportar`
real. Actualizar `tests_portafolio/test_app.py` si hace falta.

- [ ] **Step 6: Correr toda la suite de portafolio y comprobar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ -q`

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video_portafolio/ tests_portafolio/
git commit -m "$(cat <<'EOF'
Módulo Importar: pantalla con drag&drop y lista de proyectos

Cierra la fase 2. Soltar un .prproj lo lee con lector_de_entregas,
lo agrega al Portafolio, y señala si algo no vinculó.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

# FASE 3 — Revisar

### Task 7: `portafolio.py` — la escalera de estado

**Files:**
- Modify: `src/clasificador_video_portafolio/portafolio.py`
- Test: `tests_portafolio/test_portafolio.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_subir_de_sin_decidir_a_elegida():
    c = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")
    pf.subir(c)
    assert c.estado == "elegida"


def test_subir_dos_veces_seguidas_se_queda_en_elegida():
    c = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")
    pf.subir(c)
    pf.subir(c)
    assert c.estado == "elegida"


def test_bajar_de_elegida_regresa_a_sin_decidir_primero():
    c = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P",
                             estado="elegida")
    pf.bajar(c)
    assert c.estado == "sin_decidir"


def test_bajar_de_sin_decidir_llega_a_descartada():
    c = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")
    pf.bajar(c)
    assert c.estado == "descartada"


def test_bajar_no_pasa_de_descartada():
    c = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P",
                             estado="descartada")
    pf.bajar(c)
    assert c.estado == "descartada"
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -k "subir or bajar" -q`
Expected: FAIL con `AttributeError`

- [ ] **Step 3: Agregar las funciones**

Al lado de `ESTADOS = ("descartada", "sin_decidir", "elegida")`:

```python
def subir(clip: ClipDelPortafolio) -> None:
    """`↑` -- un peldaño hacia Elegida. Mismo mecanismo que
    ESCALERA_DE_ESTADO en el Clipify normal (main_window.py), con tres
    peldaños en vez de cuatro."""
    indice = min(ESTADOS.index(clip.estado) + 1, len(ESTADOS) - 1)
    clip.estado = ESTADOS[indice]


def bajar(clip: ClipDelPortafolio) -> None:
    """`↓` -- un peldaño hacia Descartada."""
    indice = max(ESTADOS.index(clip.estado) - 1, 0)
    clip.estado = ESTADOS[indice]
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -q`
Expected: PASS (todo el archivo)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/portafolio.py tests_portafolio/test_portafolio.py
git commit -m "$(cat <<'EOF'
portafolio.py: subir/bajar, la escalera Descartada/Sin decidir/Elegida

Mismo mecanismo que ESCALERA_DE_ESTADO del Clipify normal, con tres
peldaños. ↑ sube, ↓ baja, y desde un extremo hay que pasar por "sin
decidir" antes de cruzar al otro lado.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: categoría de proyecto

**Files:**
- Modify: `src/clasificador_video_portafolio/portafolio.py`
- Test: `tests_portafolio/test_portafolio.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_categorias_conocidas_por_defecto():
    p = pf.Portafolio()
    assert "Casa" in p.categorias_conocidas
    assert "Depto" in p.categorias_conocidas


def test_asignar_categoria_nueva_la_agrega_a_las_conocidas(tmp_path):
    p = pf.Portafolio()
    proyecto = p.agregar_proyecto("Rancho", tmp_path / "r.prproj", [])

    p.asignar_categoria(proyecto, "Rancho")

    assert proyecto.categoria == "Rancho"
    assert "Rancho" in p.categorias_conocidas
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -k categoria -q`

- [ ] **Step 3: Agregar a `Portafolio`**

```python
CATEGORIAS_POR_DEFECTO = ["Casa", "Depto", "Terreno", "Oficina"]
```

En `__init__`:

```python
        self.categorias_conocidas: list[str] = list(CATEGORIAS_POR_DEFECTO)
```

Método nuevo:

```python
    def asignar_categoria(self, proyecto: ProyectoImportado, categoria: str) -> None:
        proyecto.categoria = categoria
        if categoria not in self.categorias_conocidas:
            self.categorias_conocidas.append(categoria)
```

Y guardar/cargar `categorias_conocidas` en `guardar`/`cargar` igual que
`proyectos` (agregar la clave al dict y leerla de vuelta con
`.get("categorias_conocidas", list(CATEGORIAS_POR_DEFECTO))`).

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/portafolio.py tests_portafolio/test_portafolio.py
git commit -m "$(cat <<'EOF'
portafolio.py: categoría de proyecto, editable y extensible

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: "ver el rodaje completo" — deducir la carpeta y listar

**Files:**
- Create: `src/clasificador_video_portafolio/rodaje_completo.py`
- Test: `tests_portafolio/test_rodaje_completo.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
"""Ver más allá de lo usado en el .prproj: deducir la carpeta del
rodaje y listar sus videos -- spec 2026-09-24-modo-portafolio-design.md
("no depende de tener un .cvproj")."""
from pathlib import Path

from clasificador_video_portafolio import rodaje_completo as rc


def test_deduce_la_carpeta_comun_de_varios_clips(tmp_path):
    carpeta = tmp_path / "Casa Reforma" / "01. VIDEOS SONY"
    carpeta.mkdir(parents=True)
    rutas = [carpeta / "clip_014.mov", carpeta / "clip_016.mov"]

    assert rc.deducir_carpeta(rutas) == carpeta


def test_deduce_none_si_los_clips_no_comparten_carpeta(tmp_path):
    a = tmp_path / "sony" / "clip_014.mov"
    b = tmp_path / "dron" / "clip_016.mov"

    assert rc.deducir_carpeta([a, b]) is None


def test_listar_videos_de_la_carpeta(tmp_path):
    carpeta = tmp_path / "material"
    carpeta.mkdir()
    (carpeta / "clip_001.mov").write_text("x")
    (carpeta / "clip_002.mp4").write_text("x")
    (carpeta / "notas.txt").write_text("x")

    videos = rc.listar_videos(carpeta)

    assert {v.name for v in videos} == {"clip_001.mov", "clip_002.mp4"}
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_rodaje_completo.py -q`

- [ ] **Step 3: Escribir el módulo**

```python
"""Ver el rodaje completo de un proyecto importado, más allá de lo que
el .prproj dice que se usó. No depende de un .cvproj -- la carpeta se
deduce de los clips ya conocidos.

Spec: docs/superpowers/specs/2026-09-24-modo-portafolio-design.md.
"""
from __future__ import annotations

from pathlib import Path

# Mismo criterio que VIDEO_EXTENSIONS del Clipify normal -- revisar y
# reusar esa constante si ya existe en clasificador_video en vez de
# duplicar la lista aquí.
EXTENSIONES_DE_VIDEO = {".mov", ".mp4", ".mxf"}


def deducir_carpeta(rutas: list[Path]) -> Path | None:
    """La carpeta padre en común de una lista de rutas, o `None` si no
    todas viven en la misma carpeta. No se adivina más allá de esto --
    si no coincide, Revisar le pregunta a Bruno."""
    if not rutas:
        return None
    padres = {r.parent for r in rutas}
    return padres.pop() if len(padres) == 1 else None


def listar_videos(carpeta: Path) -> list[Path]:
    """Todos los archivos de video DIRECTOS de `carpeta` (sin bajar a
    subcarpetas), ordenados por nombre."""
    return sorted(
        p for p in carpeta.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSIONES_DE_VIDEO
    )
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_rodaje_completo.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/rodaje_completo.py tests_portafolio/test_rodaje_completo.py
git commit -m "$(cat <<'EOF'
rodaje_completo.py: deducir la carpeta y listar sus videos

Sin depender de un .cvproj -- la carpeta se deduce de los clips que
ya se conocen por el .prproj importado.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: pantalla Revisar — rail, hoja, escalera con flechas

**Files:**
- Create: `src/clasificador_video_portafolio/ui/pantalla_revisar.py`
- Modify: `src/clasificador_video_portafolio/app.py`
- Test: `tests_portafolio/ui/test_pantalla_revisar.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
from clasificador_video_portafolio import portafolio as pf
from clasificador_video_portafolio.ui.pantalla_revisar import PantallaRevisar


def _con_un_proyecto(tmp_path):
    p = pf.Portafolio()
    proyecto = p.agregar_proyecto("Casa Reforma", tmp_path / "c.prproj", [])
    proyecto.clips.append(pf.ClipDelPortafolio(
        ruta_origen=tmp_path / "clip_014.mov", proyecto="Casa Reforma"))
    return p, proyecto


def test_seleccionar_proyecto_en_el_rail_muestra_sus_clips(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)

    pantalla.mostrar_proyecto(proyecto)

    assert pantalla.proyecto_actual is proyecto
    assert len(pantalla.tarjetas) == 1


def test_flecha_arriba_elige_el_clip_actual(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)

    pantalla.elegir_actual()

    assert proyecto.clips[0].estado == "elegida"


def test_proyecto_sin_disco_conectado_se_ve_apagado(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    # el disco se desconecta: la ruta de origen ya no existe
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)

    assert pantalla.proyecto_disponible(proyecto) is False
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ui/test_pantalla_revisar.py -q`

- [ ] **Step 3: Escribir la pantalla**

Estructura: rail izquierdo (`QListWidget` o layout propio, un renglón
por proyecto, apagado con `proyecto_disponible() is False` — reusar el
patrón visual de `_FilaReciente` de `pantalla_inicio.py` del Clipify
normal como referencia, no como import) + hoja de tarjetas a la derecha
(grid de widgets, reusar `clip_sheet.py` del Clipify normal SOLO como
referencia de cómo se leen miniaturas económicas — el widget en sí es
nuevo, porque las reglas de cuántas miniaturas cargar son distintas acá,
ver la spec).

Métodos mínimos que las pruebas piden:
- `mostrar_proyecto(proyecto)`: guarda `proyecto_actual`, reconstruye
  `tarjetas` (una por clip).
- `elegir_actual()` / `descartar_actual()`: llaman `portafolio.subir`/
  `bajar` sobre el clip de la tarjeta con foco, conectados a `Key_Up`/
  `Key_Down` en `keyPressEvent`.
- `proyecto_disponible(proyecto)`: `True` si al menos uno de sus clips
  tiene `ruta_origen.exists()` (o, más preciso: si la carpeta deducida
  con `rodaje_completo.deducir_carpeta` existe) — decidir el criterio
  exacto en este Task y dejarlo comentado en el código.
- Botón "Ver el rodaje completo": usa `rodaje_completo.deducir_carpeta`
  + `listar_videos`, agrega los que falten como
  `ClipDelPortafolio(fuera_de_secuencia=True)` al proyecto.

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ui/test_pantalla_revisar.py -q`

- [ ] **Step 5: Montarla en `VentanaPortafolio`, con el switcher de módulos**

Agregar el selector Importar/Revisar/Armar y entregar a la ventana
(un widget de tabs o botones simple, ver el mockup
`docs/superpowers/mockups/2026-09-24-modo-portafolio/mockup.html` para
la referencia visual) y conectar `modulo_actual`.

- [ ] **Step 6: Correr toda la suite de portafolio**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ -q`

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video_portafolio/ tests_portafolio/
git commit -m "$(cat <<'EOF'
Módulo Revisar: rail de proyectos, hoja, escalera con ↑/↓

Cierra la fase 3. Un proyecto sin disco conectado se ve apagado sin
perder su progreso. "Ver el rodaje completo" no depende de un
.cvproj.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

# FASE 4 — Armar y entregar

### Task 11: etiquetas de clip

**Files:**
- Modify: `src/clasificador_video_portafolio/portafolio.py`
- Test: `tests_portafolio/test_portafolio.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_alternar_etiqueta_la_agrega():
    c = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")
    pf.alternar_etiqueta(c, "Dron")
    assert c.etiquetas == ["Dron"]


def test_alternar_etiqueta_dos_veces_la_quita():
    c = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")
    pf.alternar_etiqueta(c, "Dron")
    pf.alternar_etiqueta(c, "Dron")
    assert c.etiquetas == []


def test_un_clip_puede_tener_varias_etiquetas():
    c = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")
    pf.alternar_etiqueta(c, "Dron")
    pf.alternar_etiqueta(c, "Exteriores")
    assert set(c.etiquetas) == {"Dron", "Exteriores"}


def test_elegidas_con_etiquetas(tmp_path):
    p = pf.Portafolio()
    proyecto = p.agregar_proyecto("Casa", tmp_path / "c.prproj", [])
    c1 = pf.ClipDelPortafolio(ruta_origen=tmp_path / "a.mov", proyecto="Casa",
                              estado="elegida", etiquetas=["Dron"])
    c2 = pf.ClipDelPortafolio(ruta_origen=tmp_path / "b.mov", proyecto="Casa",
                              estado="elegida", etiquetas=["Cocina"])
    c3 = pf.ClipDelPortafolio(ruta_origen=tmp_path / "c.mov", proyecto="Casa",
                              estado="sin_decidir", etiquetas=["Dron"])
    proyecto.clips.extend([c1, c2, c3])

    filtrados = p.elegidas_con_etiquetas({"Dron"})

    assert filtrados == [c1]  # c3 no cuenta: no está Elegida
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -k "etiqueta or elegidas_con" -q`

- [ ] **Step 3: Agregar las funciones**

```python
def alternar_etiqueta(clip: ClipDelPortafolio, etiqueta: str) -> None:
    if etiqueta in clip.etiquetas:
        clip.etiquetas.remove(etiqueta)
    else:
        clip.etiquetas.append(etiqueta)
```

En `Portafolio`:

```python
    def todas_las_elegidas(self) -> list[ClipDelPortafolio]:
        return [c for p in self.proyectos for c in p.clips if c.estado == "elegida"]

    def elegidas_con_etiquetas(self, etiquetas: set[str]) -> list[ClipDelPortafolio]:
        """Elegidas que tienen AL MENOS una de las etiquetas pedidas.
        Con `etiquetas` vacío, no filtra nada extra: son todas las
        elegidas."""
        if not etiquetas:
            return self.todas_las_elegidas()
        return [c for c in self.todas_las_elegidas()
                if etiquetas & set(c.etiquetas)]
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/test_portafolio.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/portafolio.py tests_portafolio/test_portafolio.py
git commit -m "$(cat <<'EOF'
portafolio.py: etiquetas de clip y filtro de elegidas por etiqueta

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: la carpeta de portafolio — alias por proyecto de origen

**Files:**
- Create: `src/clasificador_video_portafolio/carpeta_de_portafolio.py`
- Test: `tests_portafolio/test_carpeta_de_portafolio.py`

- [ ] **Step 1: Investigar antes de escribir código**

Un alias de Finder **no es un symlink** (`os.symlink`): es un formato
propio de macOS que guarda una referencia al volumen + inodo del
archivo, y sigue funcionando si el archivo se renombra o se mueve
dentro del mismo volumen. Python no lo crea nativo. Investigar, en este
orden:

1. `pyobjc` (`Foundation`/`AppKit`): `NSURL.bookmarkDataWithOptions_...`
   más `NSURL.writeBookmarkData_toURL_options_error_` con
   `NSURLBookmarkCreationSuitableForBookmarkFile` — es el camino
   "correcto" pero depende de que `pyobjc-framework-Cocoa` esté
   disponible como dependencia nueva.
2. Si `pyobjc` no está ya en el proyecto y se prefiere no agregarlo,
   alternativa vía `osascript` (`Finder` scripting, `make alias file to
   ... at ...`), invocado con `subprocess` — más frágil, pero sin
   dependencia nueva.

Decidir cuál se usa ANTES de escribir las pruebas, y dejarlo anotado en
el docstring del módulo con el porqué.

- [ ] **Step 2: Escribir las pruebas que fallan**

```python
"""La carpeta de portafolio: un alias por clip Elegido, en una
subcarpeta por proyecto de origen -- spec
2026-09-24-modo-portafolio-design.md."""
from pathlib import Path

from clasificador_video_portafolio import carpeta_de_portafolio as cp


def test_ruta_del_alias_usa_subcarpeta_del_proyecto(tmp_path):
    carpeta_raiz = tmp_path / "Mi Portafolio"
    original = tmp_path / "material" / "clip_014.mov"

    ruta = cp.ruta_del_alias(carpeta_raiz, proyecto="Casa Reforma",
                             clip=original)

    assert ruta == carpeta_raiz / "Casa Reforma" / "clip_014.mov"


def test_crear_alias_hace_la_subcarpeta_si_falta(tmp_path):
    original = tmp_path / "clip_014.mov"
    original.write_text("contenido")
    carpeta_raiz = tmp_path / "Mi Portafolio"

    destino = cp.crear_alias(carpeta_raiz, proyecto="Casa Reforma", clip=original)

    assert destino.parent.is_dir()
    # verificar que destino ES un alias que resuelve a `original` --
    # el aserto exacto depende de qué camino se eligió en el Step 1
    # (pyobjc vs osascript); acá va la comprobación que corresponda.
```

- [ ] **Step 3: Correr las pruebas y comprobar que fallan**

- [ ] **Step 4: Escribir el módulo** (siguiendo lo decidido en el Step 1)

- [ ] **Step 5: Correr las pruebas y comprobar que pasan**

Estas pruebas **solo pueden correr en macOS de verdad** (crear un alias
real no es simulable bajo `offscreen` de forma significativa) — marcarlas
con `@pytest.mark.skipif(sys.platform != "darwin", ...)`, siguiendo
cualquier patrón similar que ya exista en la suite del Clipify normal
para funciones atadas a macOS (revisar `scripts/hacer_icono.py` y sus
pruebas, si las tiene, antes de inventar el patrón de cero).

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video_portafolio/carpeta_de_portafolio.py tests_portafolio/test_carpeta_de_portafolio.py
git commit -m "$(cat <<'EOF'
carpeta_de_portafolio.py: alias de Finder por proyecto de origen

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: proxies faltantes en la carpeta de portafolio

**Files:**
- Modify: `src/clasificador_video_portafolio/carpeta_de_portafolio.py`
- Test: `tests_portafolio/test_carpeta_de_portafolio.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Antes de escribir, **leer `proxy_gen.py` completo** (funciones
públicas: buscar cómo genera un proxy para UN archivo dado, y cómo
`carpetas_de_proxies` busca en varios lugares) — esta pieza reusa esas
funciones, no las reimplementa.

```python
def test_generar_proxy_faltante_llama_a_proxy_gen(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video_portafolio.carpeta_de_portafolio.proxy_gen.generar",
        lambda origen, destino: llamadas.append((origen, destino)),
    )
    original = tmp_path / "clip_014.mov"
    original.write_text("x")
    carpeta_raiz = tmp_path / "Mi Portafolio"

    cp.asegurar_proxy(carpeta_raiz, proyecto="Casa Reforma", clip=original)

    assert len(llamadas) == 1


def test_no_regenera_si_ya_existe_proxy_en_la_carpeta_de_portafolio(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video_portafolio.carpeta_de_portafolio.proxy_gen.generar",
        lambda origen, destino: llamadas.append((origen, destino)),
    )
    original = tmp_path / "clip_014.mov"
    original.write_text("x")
    carpeta_raiz = tmp_path / "Mi Portafolio"
    ruta_proxy = cp.ruta_de_proxy(carpeta_raiz, proyecto="Casa Reforma", clip=original)
    ruta_proxy.parent.mkdir(parents=True)
    ruta_proxy.write_text("ya existe")

    cp.asegurar_proxy(carpeta_raiz, proyecto="Casa Reforma", clip=original)

    assert llamadas == []
```

- [ ] **Step 2-4: fallar → implementar → pasar**, siguiendo el mismo
ciclo de los tasks anteriores. `asegurar_proxy` debe, en orden: (1)
mirar si `proxy_gen` ya encuentra un proxy en cualquiera de los lugares
que conoce (reusar esa búsqueda existente, no reinventarla — esto es lo
que da el reuso "entre entregas" que pide la spec); (2) si no, buscar
en la carpeta de portafolio misma; (3) si tampoco, generar uno nuevo ahí.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/carpeta_de_portafolio.py tests_portafolio/test_carpeta_de_portafolio.py
git commit -m "$(cat <<'EOF'
carpeta_de_portafolio.py: generar proxies faltantes, sin duplicar

Reusa la búsqueda de proxy_gen antes de generar uno nuevo -- un
proxy ya generado para otra entrega o revisión no se vuelve a
generar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: generar la entrega — `.prproj` con fecha, bins por proyecto+categoría

**Files:**
- Create: `src/clasificador_video_portafolio/generar_entrega.py`
- Test: `tests_portafolio/test_generar_entrega.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Antes de escribir, **leer `prproj_generador.py` completo**, en
particular `generar_prproj`, `crear_bin_hijo`, `clonar_clip` — esta
pieza es la razón de ser de todo ese módulo (que ya lo usa el Clipify
normal para su propia entrega) aplicada a clips que vienen del
portafolio en vez de un `.cvproj` de rodaje.

```python
from datetime import date

from clasificador_video_portafolio import generar_entrega as ge


def test_nombre_de_archivo_lleva_la_fecha():
    nombre = ge.nombre_de_archivo("Mi Portafolio", fecha=date(2026, 9, 24))
    assert nombre == "Mi Portafolio — entrega 2026-09-24.prproj"


def test_bins_agrupan_por_proyecto_con_su_categoria(tmp_path):
    clips = [
        pf.ClipDelPortafolio(ruta_origen=tmp_path / "a.mov", proyecto="Casa Reforma"),
        pf.ClipDelPortafolio(ruta_origen=tmp_path / "b.mov", proyecto="Casa Reforma"),
        pf.ClipDelPortafolio(ruta_origen=tmp_path / "c.mov", proyecto="Torre Insurgentes"),
    ]
    categorias = {"Casa Reforma": "Casa", "Torre Insurgentes": "Depto"}

    bins = ge.agrupar_en_bins(clips, categorias)

    assert bins["Casa Reforma — Casa"] == clips[:2]
    assert bins["Torre Insurgentes — Depto"] == clips[2:]
```

- [ ] **Step 2-4: fallar → implementar → pasar.**

`agrupar_en_bins` es lógica pura, sin Qt ni XML — el Task se detiene
ahí más una prueba de integración liviana de `generar` (la función que
sí llama a `prproj_generador.generar_prproj`, apuntando a la carpeta de
portafolio de cada clip vía `carpeta_de_portafolio.ruta_del_alias` en
vez de la ruta original). No es necesario un fixture de `.prproj`
completo para probar `generar` línea por línea — con que
`prproj_generador.generar_prproj` ya tenga su propia suite (la tiene:
`tests/test_prproj_generador.py`), aquí basta con una prueba que
confirme que se le pasan los bins correctos y que el nombre de archivo
lleva la fecha.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video_portafolio/generar_entrega.py tests_portafolio/test_generar_entrega.py
git commit -m "$(cat <<'EOF'
generar_entrega.py: agrupar en bins por proyecto+categoría, con fecha

Reusa prproj_generador.generar_prproj -- la misma pieza que ya usa
el Clipify normal para su propia entrega.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: pantalla Armar y entregar

**Files:**
- Create: `src/clasificador_video_portafolio/ui/pantalla_armar_y_entregar.py`
- Modify: `src/clasificador_video_portafolio/app.py`
- Test: `tests_portafolio/ui/test_pantalla_armar_y_entregar.py`

- [ ] **Step 1-4:** mismo ciclo TDD que el Task 10 (pantalla Revisar),
adaptado a: rail de etiquetas (en vez de proyectos), grid de tarjetas
agrupadas por proyecto de origen (con su categoría en el encabezado del
grupo), barra fija abajo con el resumen de la entrega
(`portafolio.elegidas_con_etiquetas` + `generar_entrega.nombre_de_archivo`)
y el botón "Generar .prproj" que llama `generar_entrega.generar`.

Referencia visual: `docs/superpowers/mockups/2026-09-24-modo-portafolio/mockup.html`,
tercera pantalla.

- [ ] **Step 5: Montarla en `VentanaPortafolio`**, completando el
switcher de los tres módulos.

- [ ] **Step 6: Correr toda la suite de portafolio**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ -q`

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video_portafolio/ tests_portafolio/
git commit -m "$(cat <<'EOF'
Módulo Armar y entregar: etiquetas, carpeta con alias, generar .prproj

Cierra la fase 4. Con esto Clipify Portafolio queda usable de
principio a fin: Importar, Revisar, Armar y entregar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Después de las cuatro fases

Con esto el modo Portafolio queda funcional de punta a punta, pero
quedan afuera a propósito (spec, sección "Fuera de alcance"):

- Pulir la UI a nivel pixel contra el mockup (colores, tipografía,
  animaciones) — este plan prioriza que la lógica funcione y esté
  probada; el acabado visual final es una pasada aparte, con
  verificación de pixel como pide `CLAUDE.md`.
- Empaquetar `clipify-portafolio` como app de macOS independiente
  (`.app`/`.dmg` propios, ícono propio) — hoy solo existe como comando
  de consola instalado junto al del Clipify normal.
