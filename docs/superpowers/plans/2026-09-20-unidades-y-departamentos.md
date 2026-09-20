# Unidades y departamentos — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** agregar un nivel opcional "unidad" (Casa A / Depto 1) arriba de
cuarto, sin cambiar en nada el comportamiento de un proyecto que nunca crea
una unidad.

**Architecture:** `Clip.categoria_path` ya es una lista; con unidad pasa a
`[unidad, cuarto]`, sin unidad se queda `[cuarto]` (nunca hay un tercer
nivel — los subcuartos murieron en la F3). Todo el código que hoy asume
"la posición 0 es el cuarto" pasa por dos helpers nuevos (`_unidad_de`,
`_cuarto_de`) que miran el LARGO de la lista, no una posición fija — el
mismo patrón que ya usa `room_label=clip.categoria_path[-1]`
(`main_window.py:5571`), que por eso no necesita tocarse.

El catálogo de cuartos deja de ser uno solo: `MainWindow.room_selections:
dict[str, RoomSelection]` tiene una entrada por unidad más una entrada
`""` ("sin unidad" — el catálogo de siempre). `MainWindow.room_selection`
sigue existiendo, pero ahora es un alias al catálogo de la unidad activa
(`self.room_selections[self._unidad_activa or ""]`), que se reasigna al
cambiar de unidad en la paleta. Así, TODO el código que ya opera sobre
`self.room_selection` — paleta de cuartos, rail, router de teclado, `S`,
bulk assign — sigue funcionando sin tocarse: lo único nuevo es cuál
catálogo está detrás del alias en cada momento.

**Tech Stack:** Python 3 / PySide6 (app), JavaScript sin build (plugin UXP
de Premiere), pytest + `QT_QPA_PLATFORM=offscreen`, `node
uxp-plugin/pruebas/correr.js`.

**Spec:** `docs/superpowers/specs/2026-09-20-unidades-y-departamentos-design.md`
(fuente de verdad de las decisiones de producto — no reabrir sin razón
nueva).

**Nota sobre granularidad:** esta es una feature grande. Cada Task de abajo
es una unidad de commit coherente (más que los 2-5 minutos de una tarea
mínima), pero sigue el ciclo rojo→verde→commit puertas adentro. No hay
Task sin código completo ni sin comando de verificación exacto.

---

## Fase 0 — El helper que evita que dos partes del programa lean el mismo dato distinto

### Task 1: `_unidad_de` / `_cuarto_de` en `main_window.py`

Hoy hay **al menos ocho** lugares que leen `clip.categoria_path[0]` asumiendo
que ahí vive el cuarto (líneas 1537, 1789, 1802, 1873-1874, 1933, 1969, 5574,
más `_apply_categoria_to_targets` en 1459 que ya usa `path[0]` para el color
de registro). En cuanto exista una unidad, `categoria_path[0]` puede ser la
unidad y no el cuarto. Centralizar la lectura ANTES de tocar cualquier otra
cosa es lo único que evita que la mitad de esos ocho puntos se actualice y
la otra mitad no — exactamente la familia de bug que costó ocho reportes el
2026-08-22 (ver CLAUDE.md).

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_unidades.py` (nuevo)

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
# tests/ui/test_main_window_unidades.py
"""_unidad_de / _cuarto_de: el largo del categoria_path decide, no una
posicion fija. Sin unidad es [cuarto]; con unidad es [unidad, cuarto] --
nunca hay un tercer nivel, los subcuartos murieron en la F3."""
from clasificador_video.ui.main_window import MainWindow


def test_cuarto_de_sin_unidad():
    assert MainWindow._cuarto_de(["Cocina"]) == "Cocina"


def test_cuarto_de_con_unidad():
    assert MainWindow._cuarto_de(["Casa A", "Cocina"]) == "Cocina"


def test_cuarto_de_vacio():
    assert MainWindow._cuarto_de([]) is None


def test_unidad_de_sin_unidad():
    assert MainWindow._unidad_de(["Cocina"]) is None


def test_unidad_de_con_unidad():
    assert MainWindow._unidad_de(["Casa A", "Cocina"]) == "Casa A"


def test_unidad_de_vacio():
    assert MainWindow._unidad_de([]) is None
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -q`
Expected: FAIL — `AttributeError: type object 'MainWindow' has no attribute '_cuarto_de'`

- [ ] **Step 3: Implementar, como `staticmethod` (no necesitan `self`)**

Agregar cerca de `_color_de_cuarto` (`main_window.py:1657`):

```python
    @staticmethod
    def _cuarto_de(categoria_path: list[str]) -> str | None:
        """El nombre del cuarto, tenga o no unidad delante.

        El largo decide: `[cuarto]` (sin unidad) o `[unidad, cuarto]` (con
        unidad) -- nunca hay un tercer nivel, los subcuartos se fueron en la
        F3. Punto unico de lectura: sin esto, cada sitio que asumia
        `categoria_path[0]` == cuarto se actualiza por su cuenta el dia que
        aparece la primera unidad, y el que se olvida queda leyendo la
        unidad como si fuera el cuarto -- en silencio.
        """
        if not categoria_path:
            return None
        return categoria_path[-1]

    @staticmethod
    def _unidad_de(categoria_path: list[str]) -> str | None:
        """El nombre de la unidad, o `None` si el clip no tiene (proyecto
        sin unidades, o clip en el bloque «Sin unidad»)."""
        if len(categoria_path) > 1:
            return categoria_path[0]
        return None
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -q`
Expected: PASS (6 tests)

- [ ] **Step 5: Reemplazar los ocho sitios que leían `categoria_path[0]` a mano**

En `main_window.py`, reemplazar cada uno (mismo comportamiento hoy porque
`_unidad_de` siempre da `None` sin unidades — el cambio es inerte hasta la
Fase 1):

```python
# línea 1537, dentro de _conteos_por_cuarto
        for clip in self.clips:
            if clip.categoria_path:
                cuenta[self._cuarto_de(clip.categoria_path)] += 1

# línea 1789, dentro de _refresh_rail
        for clip in self.clips:
            if clip.categoria_path:
                counts[self._cuarto_de(clip.categoria_path)] += 1

# línea 1802, dentro de _refresh_rail
        self.room_rail.set_current_room(
            self._cuarto_de(clip.categoria_path) if clip and clip.categoria_path else None
        )

# líneas 1873-1874, dentro de _refresh_overlays
        cuarto_actual = self._cuarto_de(clip.categoria_path) if clip.categoria_path else None
        color = (
            theme.room_color(active_rooms.index(cuarto_actual))
            if cuarto_actual and cuarto_actual in active_rooms
            else None
        )

# línea 1933, dentro de _on_room_renamed
        for clip in self.clips:
            if clip.categoria_path and self._cuarto_de(clip.categoria_path) == viejo:
                clip.categoria_path = clip.categoria_path[:-1] + [nuevo]

# línea 1969, dentro de _on_room_removed
        afectados = [
            i for i, c in enumerate(self.clips)
            if c.categoria_path and self._cuarto_de(c.categoria_path) == nombre
        ]

# líneas 5574-5575, dentro de _refrescar_hoja_de_verdad
                room_color=(
                    theme.room_color(active_rooms.index(self._cuarto_de(clip.categoria_path)))
                    if clip.categoria_path and self._cuarto_de(clip.categoria_path) in active_rooms
                    else None
                ),
```

Nota sobre el de la línea 1933: antes era `clip.categoria_path = [nuevo]`
(machacaba TODA la lista); con unidad hay que conservar el primer elemento
y solo reemplazar el último — `categoria_path[:-1] + [nuevo]` da `[nuevo]`
cuando no hay unidad y `[unidad, nuevo]` cuando sí, sin caso especial.

- [ ] **Step 6: Suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS salvo los 5 fallos preexistentes ya documentados en el
handoff del 2026-09-20 (nada nuevo debe fallar).

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Agregar _unidad_de/_cuarto_de como punto unico de lectura del categoria_path

Antes de sumar el nivel de unidad, los ocho sitios que asumian
categoria_path[0] == cuarto pasan por un solo helper. Sin esto, el dia
que exista la primera unidad cada sitio se actualizaria por su cuenta y
el que se olvidara leeria la unidad como si fuera el cuarto, en
silencio -- la misma familia de bug de los ocho reportes del 2026-08-22.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Fase 1 — El catálogo de unidades y el catálogo de cuartos por unidad

### Task 2: `UnitSelection`

**Files:**
- Create: `src/clasificador_video/units.py`
- Test: `tests/test_units.py`

- [ ] **Step 1: Prueba que falla**

```python
# tests/test_units.py
"""UnitSelection es UnitSelection(RoomSelection): misma forma, mismos
metodos (add/rename/move/mover_a/reordenar/remove/active_rooms) -- el
orden ES la tecla, igual que en RoomSelection. Clase propia y no la misma
RoomSelection reusada para no mezclar en el codigo "una lista de cuartos"
con "una lista de unidades", aunque el cuerpo sea identico (DRY vía
herencia trivial)."""
from clasificador_video.units import UnitSelection
from clasificador_video.rooms import RoomSelection


def test_es_una_room_selection():
    assert isinstance(UnitSelection(), RoomSelection)


def test_add_y_orden():
    sel = UnitSelection()
    sel.add("Casa A")
    sel.add("Casa B")
    assert sel.active_rooms() == ["Casa A", "Casa B"]


def test_no_es_la_misma_clase_que_room_selection():
    # dos catalogos independientes: agregar a uno no toca al otro
    assert UnitSelection is not RoomSelection
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `.venv/bin/pytest tests/test_units.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'clasificador_video.units'`

- [ ] **Step 3: Implementar**

```python
# src/clasificador_video/units.py
from __future__ import annotations

from clasificador_video.rooms import RoomSelection


class UnitSelection(RoomSelection):
    """Las unidades de la sesion (Casa A / Depto 1), planas y en orden.

    Misma forma que `RoomSelection`: el orden ES la tecla (1-9 en la
    paleta de unidades), y `add`/`rename`/`move`/`mover_a`/`reordenar`/
    `remove` significan exactamente lo mismo un nivel arriba. Clase propia
    -- no la misma `RoomSelection` reusada -- para que el codigo diga
    "esto es un catalogo de UNIDADES" en vez de "esto es un catalogo de
    cuartos que uso para otra cosa".
    """
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `.venv/bin/pytest tests/test_units.py -q`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/units.py tests/test_units.py
git commit -m "$(cat <<'EOF'
Agregar UnitSelection, el catalogo de unidades

Hermano de RoomSelection un nivel arriba: mismo orden-es-tecla, misma
interfaz. Sin unidades creadas todavia no lo usa nada -- este commit
por si solo no cambia ningun comportamiento.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### Task 3: Persistencia — `proyecto.a_dict` guarda `units` y `rooms_por_unidad`

**Files:**
- Modify: `src/clasificador_video/proyecto.py`
- Test: `tests/test_proyecto.py` (agregar casos — el archivo ya existe, revisar convención de imports ahí antes de escribir)

- [ ] **Step 1: Prueba que falla**

```python
# agregar a tests/test_proyecto.py
def test_a_dict_guarda_units_y_rooms_por_unidad_vacios_por_default():
    from clasificador_video import proyecto
    from clasificador_video.bins import BinTree

    datos = proyecto.a_dict(
        proyecto="Prueba", rooms=["Cocina"], clips=[], bins=BinTree(),
        tamanos={}, duraciones={}, rotaciones={},
    )
    assert datos["units"] == []
    assert datos["rooms_por_unidad"] == {}


def test_a_dict_guarda_units_y_rooms_por_unidad_con_datos():
    from clasificador_video import proyecto
    from clasificador_video.bins import BinTree

    datos = proyecto.a_dict(
        proyecto="Prueba", rooms=[], clips=[], bins=BinTree(),
        tamanos={}, duraciones={}, rotaciones={},
        units=["Casa A", "Casa B"],
        rooms_por_unidad={"Casa A": ["Cocina"], "Casa B": ["Cocina", "Baño"]},
    )
    assert datos["units"] == ["Casa A", "Casa B"]
    assert datos["rooms_por_unidad"] == {
        "Casa A": ["Cocina"], "Casa B": ["Cocina", "Baño"],
    }
```

(Ajustar el import de `BinTree`/construcción vacía a como ya lo hagan los
demás tests de `test_proyecto.py` — revisar el archivo antes de este paso,
puede que el patrón existente use un helper o fixture distinto.)

- [ ] **Step 2: Correr y confirmar que falla**

Run: `.venv/bin/pytest tests/test_proyecto.py -k units -q`
Expected: FAIL — `TypeError: a_dict() got an unexpected keyword argument 'units'`

- [ ] **Step 3: Implementar — `proyecto.py:128-136` (firma) y dentro del dict devuelto**

```python
def a_dict(proyecto: str, rooms: list[str], clips: list, bins,
           tamanos: dict, duraciones: dict, rotaciones: dict,
           bytes_conocidos: dict | None = None,
           relativas_conocidas: dict | None = None,
           agrupar_por_cuarto: bool = True,
           modo_horizontal: bool = False,
           carpeta_de_proxies: Path | None = None,
           guia: dict | None = None,
           entrega: dict | None = None,
           units: list[str] | None = None,
           rooms_por_unidad: dict[str, list[str]] | None = None) -> dict:
```

Y dentro de `return {...}` (después de `"rooms": list(rooms),`):

```python
        "rooms": list(rooms),
        # Nivel opcional arriba de cuarto. Vacios en todo proyecto que
        # nunca crea una unidad -- ahi el documento sale identico al de
        # siempre salvo por estas dos llaves de mas, que nadie lee.
        "units": list(units) if units else [],
        "rooms_por_unidad": (
            {u: list(r) for u, r in rooms_por_unidad.items()}
            if rooms_por_unidad else {}
        ),
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `.venv/bin/pytest tests/test_proyecto.py -q`
Expected: PASS, incluidos los tests viejos del archivo (la firma nueva es
retro-compatible: los dos parámetros son opcionales).

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proyecto.py tests/test_proyecto.py
git commit -m "$(cat <<'EOF'
Persistir units y rooms_por_unidad en el documento del proyecto

Dos llaves nuevas, ambas opcionales y vacias por default: un proyecto
que nunca crea una unidad guarda exactamente lo mismo que guardaba mas
las dos llaves vacias, que nadie lee todavia.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### Task 4: `_aplanar_categoria` consciente de si el proyecto declara unidades

Este es el punto más delicado de la fase: `app.py:64-71` hoy colapsa
CUALQUIER `categoria_path` de más de un elemento a `[path[0]]`, porque
existía para descartar subcuartos de sesiones pre-F3. Si no se corrige,
el primer proyecto con una unidad perdería el cuarto de cada clip apenas
lo volviera a abrir — el archivo tendría `["Casa A", "Cocina"]` y la app
lo leería como `["Casa A"]`, clasificando todo bajo la unidad y
"perdiendo" el cuarto en silencio. La distinción: si el documento declara
`"units"` no vacío, un `categoria_path` de 2 elementos es `[unidad,
cuarto]` legítimo; si no, es el caso viejo de subcuarto y se aplana.

**Files:**
- Modify: `src/clasificador_video/app.py`
- Test: `tests/test_app.py` (agregar — revisar convención existente del archivo)

- [ ] **Step 1: Prueba que falla**

```python
# agregar a tests/test_app.py
def test_categoria_de_2_niveles_se_conserva_si_el_proyecto_tiene_unidades():
    from clasificador_video.app import _clip_from_dict

    d = {"orden": 0, "ruta": "/x.mp4", "fps": 30.0,
         "categoria_path": ["Casa A", "Cocina"]}
    clip = _clip_from_dict(d, hay_unidades=True)
    assert clip.categoria_path == ["Casa A", "Cocina"]


def test_categoria_de_2_niveles_se_aplana_si_el_proyecto_no_tiene_unidades():
    # sesion pre-F3: subcuarto, se descarta y se conserva el padre
    from clasificador_video.app import _clip_from_dict

    d = {"orden": 0, "ruta": "/x.mp4", "fps": 30.0,
         "categoria_path": ["Recámara 1", "Baño"]}
    clip = _clip_from_dict(d, hay_unidades=False)
    assert clip.categoria_path == ["Recámara 1"]


def test_categoria_de_3_niveles_se_recorta_a_2_aunque_haya_unidades():
    # nunca deberia pasar -- no hay subcuartos-de-unidad -- pero si un
    # archivo viniera corrupto, recortar es mas seguro que reventar
    from clasificador_video.app import _clip_from_dict

    d = {"orden": 0, "ruta": "/x.mp4", "fps": 30.0,
         "categoria_path": ["Casa A", "Cocina", "Extra"]}
    clip = _clip_from_dict(d, hay_unidades=True)
    assert clip.categoria_path == ["Casa A", "Cocina"]
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k categoria_de -q`
Expected: FAIL — `TypeError: _clip_from_dict() got an unexpected keyword argument 'hay_unidades'`

- [ ] **Step 3: Implementar — `app.py:64-91`**

```python
def _aplanar_categoria(path: list, hay_unidades: bool) -> list[str]:
    """Sesiones guardadas antes de la F3 pueden traer `["Recámara 1", "Baño"]`
    -- un subcuarto, que ya no es representable, y se descarta conservando
    el CUARTO PADRE.

    Con unidades, un `categoria_path` de 2 elementos deja de ser ese caso
    viejo: es `[unidad, cuarto]` legitimo, y aplanarlo perderia el cuarto
    de cada clip en silencio apenas se reabriera el proyecto. `hay_unidades`
    -- si el documento declara `"units"` no vacio -- es lo unico que
    distingue un caso del otro: la forma de la lista es identica en los dos.
    """
    if not path:
        return []
    if hay_unidades:
        return [str(elemento) for elemento in path[:2]]
    return [str(path[0])]


def _clip_from_dict(d: dict, hay_unidades: bool) -> Clip:
    """Un clip desde el JSON. **Truena** si el dato no sirve -- ver `_clips_de`,
    que es quien atrapa: aqui adentro no se puede decidir si un proyecto a
    medio corromper se abre igual o no se abre.

    `int` y `float` no son adorno: sin ellos un `"fps": "treinta"` entra sin
    quejarse y revienta mucho despues, al dividir, con la ventana ya armada.
    """
    return Clip(
        orden=int(d["orden"]),
        ruta=Path(d["ruta"]),
        categoria_path=_aplanar_categoria(list(d.get("categoria_path") or []), hay_unidades),
        fps=float(d["fps"]),
        in_frame=d.get("in_frame"),
        out_frame=d.get("out_frame"),
        flag=d.get("flag", "none"),
        ruta_proxy=Path(d["ruta_proxy"]) if d.get("ruta_proxy") else None,
    )
```

Y en `_clips_de` (línea ~94-116), pasar el dato hacia abajo — el
`hay_unidades` se calcula UNA vez, del `data` crudo, antes de tocar ningún
clip:

```python
def _clips_de(data: dict) -> list[Clip] | None:
    """..."""  # docstring sin cambios
    crudos = data.get("clips")
    if crudos is None:
        return []
    if not isinstance(crudos, list):
        return None
    hay_unidades = bool(data.get("units"))
    try:
        return [_clip_from_dict(d, hay_unidades) for d in crudos]
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "$(cat <<'EOF'
No aplanar categoria_path de 2 niveles cuando el proyecto tiene unidades

_aplanar_categoria existia para tirar los subcuartos pre-F3, que traian
2 niveles. Con unidades, 2 niveles pasa a ser [unidad, cuarto] legitimo
-- misma forma, dato distinto -- y aplanarlo sin distinguir perderia el
cuarto de cada clip en silencio apenas se reabriera el proyecto. La
distincion es si el documento declara "units": ahi es lo unico que
separa un caso del otro.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### Task 5: `MainWindow` — catálogo por unidad y unidad activa

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Modify: `src/clasificador_video/app.py`
- Test: `tests/ui/test_main_window_unidades.py` (el mismo del Task 1)

- [ ] **Step 1: Pruebas que fallan**

```python
# agregar a tests/ui/test_main_window_unidades.py
def test_room_selection_es_el_catalogo_sin_unidad_por_default(main_window):
    main_window.room_selections[""].add("Cocina")
    assert main_window.room_selection.active_rooms() == ["Cocina"]


def test_activar_unidad_cambia_el_alias_room_selection(main_window):
    main_window.unit_selection.add("Casa A")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections["Casa A"].add("Cocina A")
    main_window._activar_unidad("Casa A")
    assert main_window.room_selection.active_rooms() == ["Cocina A"]
    assert main_window._unidad_activa == "Casa A"


def test_activar_unidad_crea_el_catalogo_si_no_existia(main_window):
    main_window.unit_selection.add("Casa B")
    main_window._activar_unidad("Casa B")
    assert main_window.room_selections["Casa B"].active_rooms() == []
    assert main_window.room_selection is main_window.room_selections["Casa B"]


def test_desactivar_unidad_vuelve_al_catalogo_sin_unidad(main_window):
    main_window.room_selections[""].add("Cocina")
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window._activar_unidad(None)
    assert main_window.room_selection.active_rooms() == ["Cocina"]
    assert main_window._unidad_activa is None
```

(`main_window` es la fixture que ya usan los demás tests de
`tests/ui/test_main_window*.py` — revisar `conftest.py` de esa carpeta
para reusarla tal cual; si no existe una fixture compartida, seguir el
patrón de construcción que ya use `test_main_window.py`.)

Agregar el import que falte al tope del archivo:

```python
from clasificador_video.rooms import RoomSelection
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -k activar -q`
Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute 'room_selections'`

- [ ] **Step 3: Implementar**

En el constructor de `MainWindow` (donde hoy se guarda `self.room_selection
= room_selection`, línea 709), agregar al lado:

```python
        self.room_selections: dict[str, RoomSelection] = {"": room_selection}
        self.room_selection = room_selection
        self.unit_selection = UnitSelection()
        self._unidad_activa: str | None = None
```

Agregar el import:

```python
from clasificador_video.units import UnitSelection
```

Y el método nuevo, cerca de `_sync_rooms` (`main_window.py:1907`):

```python
    def _activar_unidad(self, nombre: str | None) -> None:
        """Cambia cual catalogo de cuartos esta detras de `room_selection`.

        `None` es "sin unidad activa": el catalogo de siempre (llave `""`),
        que es exactamente lo que hay en un proyecto que nunca creo una
        unidad. Elegir una unidad NO reasigna nada -- solo dice sobre que
        catalogo actuan de ahora en adelante la paleta de cuartos, el rail
        y las teclas 1-9, hasta que se elija otra o se cierre la paleta de
        unidades (spec 2026-09-20 §3).
        """
        llave = nombre or ""
        if llave not in self.room_selections:
            self.room_selections[llave] = RoomSelection()
        self._unidad_activa = nombre
        self.room_selection = self.room_selections[llave]
        self._sync_rooms()
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -q`
Expected: PASS (10 tests: los 6 del Task 1 + los 4 de este)

- [ ] **Step 5: Cargar y guardar los catálogos por unidad — `app.py` y `_datos_del_proyecto`**

En `app.py::_poblar_ventana` (línea ~152-159), reemplazar:

```python
    window.project_name = str(data.get("proyecto") or "Shooting sin nombre")
    rooms = data.get("rooms")
    window.room_selections = {"": _rebuild_room_selection(
        [str(r) for r in rooms] if isinstance(rooms, list) else []
    )}
    units = data.get("units")
    window.unit_selection = _rebuild_unit_selection(
        [str(u) for u in units] if isinstance(units, list) else []
    )
    rooms_por_unidad = data.get("rooms_por_unidad")
    if isinstance(rooms_por_unidad, dict):
        for nombre_unidad in window.unit_selection.active_rooms():
            crudos = rooms_por_unidad.get(nombre_unidad)
            window.room_selections[nombre_unidad] = _rebuild_room_selection(
                [str(r) for r in crudos] if isinstance(crudos, list) else []
            )
    window.room_selection = window.room_selections[""]
    window._unidad_activa = None
    # `category_tree` de proyectos viejos se ignora a proposito: los
    # subcuartos murieron en la F3 y los paths se aplanan al cuarto padre.
    window._router = KeyboardRouter(active_rooms=window.room_selection.active_rooms())
```

Y agregar el helper simétrico a `_rebuild_room_selection` (línea ~57-61):

```python
def _rebuild_unit_selection(units: list[str]) -> UnitSelection:
    sel = UnitSelection()
    for unidad in units:
        sel.add(unidad)
    return sel
```

Con el import correspondiente:

```python
from clasificador_video.units import UnitSelection
```

En `main_window.py::_datos_del_proyecto` (línea ~2320-2339), agregar los
dos argumentos nuevos a la llamada a `proyecto.a_dict`:

```python
        data = proyecto.a_dict(
            proyecto=self.project_name,
            rooms=self.room_selections[""].active_rooms(),
            clips=self.clips,
            bins=self.bins,
            tamanos=self._clip_sizes,
            duraciones=self._clip_durations,
            rotaciones=self._clip_rotations,
            bytes_conocidos=self._bytes_guardados,
            relativas_conocidas=self._relativas,
            agrupar_por_cuarto=self._agrupar_por_cuarto,
            modo_horizontal=self._modo_horizontal,
            carpeta_de_proxies=self._carpeta_de_proxies,
            guia=self._guia_para_la_sesion(),
            entrega=self._entrega.to_dict() if self._entrega is not None else None,
            units=self.unit_selection.active_rooms(),
            rooms_por_unidad={
                nombre: self.room_selections[nombre].active_rooms()
                for nombre in self.unit_selection.active_rooms()
                if nombre in self.room_selections
            },
        )
```

Nótese `rooms=self.room_selections[""].active_rooms()` — ya NO
`self.room_selection.active_rooms()` como antes: la llave `"rooms"` del
documento siempre es el catálogo "sin unidad", sin importar cuál esté
activo en el momento del autoguardado. Si se dejara `self.room_selection`
ahí, autoguardar con una unidad activa escribiría el catálogo de esa
unidad bajo la llave vieja `"rooms"` y el catálogo real "sin unidad" se
perdería.

- [ ] **Step 6: Prueba de round-trip (guardar y volver a abrir)**

```python
# agregar a tests/ui/test_main_window_unidades.py
def test_guardar_y_reabrir_conserva_unidades_y_sus_cuartos(tmp_path, main_window_factory):
    # main_window_factory: usar el helper que ya use test_main_window_proyecto.py
    # para escribir un .cvproj y reabrirlo con abrir_proyecto(); adaptar nombres
    # exactos a como esa suite ya lo hace.
    from clasificador_video.app import abrir_proyecto

    ventana = main_window_factory()
    ventana.unit_selection.add("Casa A")
    ventana.room_selections["Casa A"] = RoomSelection()
    ventana.room_selections["Casa A"].add("Cocina")
    ruta = tmp_path / "prueba.cvproj"
    ventana._datos_del_proyecto()  # sanity: no debe reventar
    import json
    ruta.write_text(json.dumps(ventana._datos_del_proyecto()))

    reabierta = abrir_proyecto(ruta)
    assert reabierta.unit_selection.active_rooms() == ["Casa A"]
    assert reabierta.room_selections["Casa A"].active_rooms() == ["Cocina"]
    assert reabierta.room_selection.active_rooms() == reabierta.room_selections[""].active_rooms()
```

Ajustar esta prueba al patrón EXACTO de fixtures/factories que ya usa
`tests/ui/test_main_window_proyecto.py` (abrir un proyecto real de punta a
punta) — no inventar una factory nueva si ya existe una equivalente ahí.

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -q`
Expected: PASS (11 tests)

- [ ] **Step 7: Suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS salvo los 5 fallos preexistentes.

- [ ] **Step 8: Commit**

```bash
git add src/clasificador_video/ui/main_window.py src/clasificador_video/app.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Un catalogo de cuartos por unidad, con room_selection como alias del activo

MainWindow.room_selections tiene una entrada "" (sin unidad, el
catalogo de siempre) mas una por unidad creada. room_selection sigue
existiendo pero ahora apunta al catalogo de la unidad activa -- asi
toda la maquinaria que ya opera sobre room_selection (paleta de
cuartos, rail, router de teclado, S, bulk assign) sigue funcionando sin
tocarse; lo unico nuevo es cual catalogo esta detras del alias.

Se guarda y se carga junto con el proyecto (units + rooms_por_unidad),
retro-compatible: un proyecto sin unidades guarda las dos llaves vacias.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Fase 2 — Asignar: la paleta de unidades

### Task 6: `UnitPalette` — hermana de `RoomPalette` que no se cierra al elegir

Para no duplicar 295 líneas, `RoomPalette` gana tres parámetros opcionales
con default igual a su comportamiento actual (cero cambio de conducta para
quien ya la usa), y `UnitPalette` los usa para verse distinto (swatch
cuadrado, no franja) y anular `confirmar()` para que elegir una unidad no
cierre la paleta.

**Files:**
- Modify: `src/clasificador_video/ui/room_palette.py`
- Create: `src/clasificador_video/ui/unit_palette.py`
- Test: `tests/ui/test_unit_palette.py` (nuevo)
- Test: `tests/ui/test_room_palette.py` (agregar un caso de no-regresión)

- [ ] **Step 1: Pruebas que fallan**

```python
# tests/ui/test_unit_palette.py
"""La paleta de unidades: misma mecanica de buscar/crear que RoomPalette,
pero elegir NO cierra la paleta -- se queda activa hasta elegir otra o
cerrarla a mano (spec 2026-09-20 §3)."""
import pytest

from clasificador_video.ui.unit_palette import UnitPalette


@pytest.fixture
def paleta(qtbot):
    p = UnitPalette()
    qtbot.addWidget(p)
    return p


def test_elegir_una_unidad_no_cierra_la_paleta(paleta, qtbot):
    paleta.abrir(["Casa A", "Casa B"], {})
    recibidos = []
    paleta.unit_activated.connect(recibidos.append)
    paleta._activa = 0
    paleta.confirmar()
    assert recibidos == ["Casa A"]
    assert not paleta.isHidden()


def test_crear_una_unidad_no_cierra_la_paleta(paleta, qtbot):
    paleta.abrir([], {})
    paleta.input.setText("Casa Nueva")
    recibidos = []
    paleta.unit_created.connect(recibidos.append)
    paleta.confirmar()
    assert recibidos == ["Casa Nueva"]
    assert not paleta.isHidden()


def test_escape_si_cierra(paleta, qtbot):
    from PySide6.QtCore import Qt
    paleta.abrir(["Casa A"], {})
    qtbot.keyClick(paleta, Qt.Key.Key_Escape)
    assert paleta.isHidden()
```

(`qtbot` viene de `pytest-qt`, que ya usa el resto de `tests/ui/` — seguir
el patrón exacto de fixtures de `tests/ui/test_room_palette.py`.)

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_unit_palette.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'clasificador_video.ui.unit_palette'`

- [ ] **Step 3: Parametrizar `RoomPalette` (cambio inerte para quien no pasa los nuevos kwargs)**

En `room_palette.py`, la clase `_Opcion` gana geometría de swatch
configurable:

```python
class _Opcion(QWidget):
    def __init__(self, parent=None, swatch_size: tuple[int, int] = (3, 13),
                 swatch_radius: int = 2):
        super().__init__(parent)
        self.setObjectName("palOption")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.nombre = ""
        self._swatch_radius = swatch_radius

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(9)
        self.key_cap = QLabel("")
        self.key_cap.setObjectName("keyCap")
        self.key_cap.setFixedSize(18, 18)
        self.key_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.swatch = QLabel("")
        self.swatch.setFixedSize(*swatch_size)
        self.swatch.setAttribute(Qt.WA_StyledBackground, True)
        self.name_label = ElidedLabel("")
        self.name_label.setObjectName("palName")
        self.count_label = QLabel("")
        self.count_label.setObjectName("roomCount")
        layout.addWidget(self.key_cap)
        layout.addWidget(self.swatch)
        layout.addWidget(self.name_label, stretch=1)
        layout.addWidget(self.count_label)

    def poner(self, nombre: str, numero: int | None, color: str, cuantos: int) -> None:
        self.nombre = nombre
        self.name_label.setText(nombre)
        self.key_cap.setText("" if numero is None else str(numero))
        self.key_cap.setProperty("sin_tecla", numero is None)
        self.swatch.setStyleSheet(
            f"background-color: {color}; border-radius: {self._swatch_radius}px;"
        )
        self.count_label.setText(str(cuantos))
```

Y `RoomPalette.__init__` gana los kwargs, con el mismo default de siempre:

```python
    def __init__(self, parent=None, color_fn=theme.room_color,
                 swatch_size: tuple[int, int] = (3, 13),
                 swatch_radius: int = 2,
                 placeholder: str = "Buscar o crear cuarto…") -> None:
        super().__init__(parent)
        self.setObjectName("roomPalette")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(ANCHO)
        self._cuartos: list[str] = []
        self._conteos: dict[str, int] = {}
        self._activa = 0
        self._color_fn = color_fn
        self._swatch_size = swatch_size
        self._swatch_radius = swatch_radius
        # ... (el resto del constructor sin cambios, salvo:)
        self.input.setPlaceholderText(placeholder)
```

Y las dos referencias a `theme.room_color(indice)` dentro de `_refrescar`
(línea 229) pasan a `self._color_fn(indice)`; y `_asegurar_filas` (línea
211) crea las filas con la geometría guardada:

```python
    def _asegurar_filas(self, cuantas: int) -> None:
        while len(self.opciones) < cuantas:
            fila = _Opcion(self._contenido, self._swatch_size, self._swatch_radius)
            self._layout_de_opciones.insertWidget(
                self._layout_de_opciones.count() - 1, fila)
            self.opciones.append(fila)
```

- [ ] **Step 4: Confirmar que `RoomPalette` no cambió de comportamiento**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_room_palette.py -q`
Expected: PASS, sin ningún cambio (los defaults reproducen exactamente el
código de antes).

- [ ] **Step 5: Implementar `UnitPalette`**

```python
# src/clasificador_video/ui/unit_palette.py
from __future__ import annotations

from PySide6.QtCore import Signal

from clasificador_video.ui import theme
from clasificador_video.ui.room_palette import RoomPalette


class UnitPalette(RoomPalette):
    """Buscar, crear y ACTIVAR unidades, sin soltar el teclado.

    Diferencia clave con `RoomPalette`: elegir una unidad no asigna nada
    y no cierra la paleta -- la deja ACTIVA hasta que se elija otra o se
    cierre con Escape. A partir de ahi, la paleta de cuartos, los digitos
    y `S` siguen actuando sobre el cuarto exactamente igual que siempre,
    pero filtrados al catalogo de la unidad activa (spec 2026-09-20 §3).
    """

    unit_activated = Signal(str)
    unit_created = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            color_fn=theme.unit_color,
            swatch_size=(11, 11),
            swatch_radius=3,
            placeholder="Buscar o crear unidad…",
        )
        self.setObjectName("unitPalette")
        self.foot_label.setText("↑ ↓ elegir     ⏎ activar     esc cerrar")

    def confirmar(self) -> None:
        """`⏎`: activa la unidad elegida, o crea la que escribiste.

        Nunca cierra la paleta -- ese es exactamente el punto: activar una
        unidad es entrar en su contexto, no un gesto de una sola vez.
        """
        activa = self.opcion_activa()
        if activa is not None:
            self.unit_activated.emit(activa)
            return
        crear = self.opcion_de_crear()
        if crear is None:
            return
        self.unit_created.emit(crear)
```

- [ ] **Step 6: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_unit_palette.py tests/ui/test_room_palette.py -q`
Expected: PASS (3 + los existentes de `test_room_palette.py`)

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/room_palette.py src/clasificador_video/ui/unit_palette.py tests/ui/test_unit_palette.py
git commit -m "$(cat <<'EOF'
Agregar UnitPalette, la paleta de unidades

Hermana de RoomPalette con tres diferencias: swatch cuadrado en vez de
franja, color de theme.unit_color en vez de room_color, y confirmar()
no cierra la paleta -- elegir una unidad la deja activa hasta elegir
otra o cerrarla a mano (spec 2026-09-20 §3). RoomPalette gana tres
kwargs opcionales con el mismo default de siempre para hacer esto sin
duplicar sus 295 lineas.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

*(`theme.unit_color` se implementa en el Task 8 de la Fase 4 — este Task
no corre en verde hasta ese momento si se ejecuta la suite completa; si
`subagent-driven-development` ejecuta los Tasks en orden, para cuando se
llegue aquí Task 8 aún no existe. Reordenar: mover el Task 8 (`theme.py`)
antes de este si se ejecuta estrictamente en el orden del documento, o
crear `theme.unit_color` con un `# TODO` temporal — no, este plan no usa
TODOs. **Ejecutar el Task 8 antes que este Task 6.**)*

---

## Fase 3 — El color de una unidad

### Task 7 (ejecutar ANTES del Task 6): `theme.UNIT_PALETTE` y `theme.unit_color`

**Files:**
- Modify: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_theme.py` (agregar — revisar convención existente)

- [ ] **Step 1: Prueba que falla**

```python
# agregar a tests/ui/test_theme.py
def test_unit_color_es_estable_por_indice():
    from clasificador_video.ui import theme
    assert theme.unit_color(0) == theme.unit_color(0)


def test_unit_color_no_repite_room_color_ni_camara_color():
    from clasificador_video.ui import theme
    # tres canales distintos: unidad, cuarto y camara no pueden compartir
    # paleta o dos identidades se verian iguales sin serlo
    assert set(theme.UNIT_PALETTE).isdisjoint(theme.ROOM_PALETTE)
    assert set(theme.UNIT_PALETTE).isdisjoint(theme.CAMARA_COLORES.values())


def test_unit_color_da_vuelta_igual_que_room_color():
    from clasificador_video.ui import theme
    assert theme.unit_color(len(theme.UNIT_PALETTE)) == theme.unit_color(0)
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_theme.py -k unit_color -q`
Expected: FAIL — `AttributeError: module 'clasificador_video.ui.theme' has no attribute 'UNIT_PALETTE'`

- [ ] **Step 3: Implementar — cerca de `ROOM_PALETTE`/`room_color` (`theme.py:46-49` y `205-210`)**

```python
# Identidad de UNIDAD -- un canal mas, distinto de ROOM_PALETTE (cuarto) y
# de CAMARA_COLORES (camara). Mismo espiritu apagado que ROOM_PALETTE: no
# compite con verde/rojo/ambar de estado. Colores propios, sin repetir los
# de los otros dos canales -- dos identidades que se ven igual no son dos
# identidades.
UNIT_PALETTE = [
    "#a8724f", "#5a8a9e", "#7e6a9e", "#4a8a72", "#8a9e5a",
    "#5a7e9e", "#9e7e6a", "#9e5a72", "#6a7e8a",
]


def unit_color(index: int) -> str:
    """Color de identidad estable para la unidad en la posicion `index` de
    la lista de unidades activas -- mismo criterio que `room_color`."""
    return UNIT_PALETTE[index % len(UNIT_PALETTE)]
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_theme.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/theme.py tests/ui/test_theme.py
git commit -m "$(cat <<'EOF'
Agregar UNIT_PALETTE y unit_color: tercer canal de identidad visual

Cuarto, camara y ahora unidad son tres canales que no pueden compartir
color -- dos identidades que se ven igual no son dos identidades. Misma
paleta apagada que ROOM_PALETTE, colores propios.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

*(Con esto ya resuelto, ejecutar el Task 6 de arriba.)*

---

## Fase 4 — Conectar la paleta de unidades a `MainWindow`

### Task 8: atajo `Ctrl+U`, señales y filtrado de la paleta de cuartos

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_unidades.py`

- [ ] **Step 1: Pruebas que fallan**

```python
# agregar a tests/ui/test_main_window_unidades.py
def test_ctrl_u_abre_la_paleta_de_unidades(main_window, qtbot):
    main_window.unit_selection.add("Casa A")
    main_window._abrir_paleta_de_unidades()
    assert not main_window.unit_palette.isHidden()


def test_elegir_unidad_en_la_paleta_activa_esa_unidad(main_window):
    main_window.unit_selection.add("Casa A")
    main_window._on_unidad_elegida_en_paleta("Casa A")
    assert main_window._unidad_activa == "Casa A"


def test_crear_unidad_en_la_paleta_la_agrega_y_la_activa(main_window):
    main_window._on_unidad_creada_en_paleta("Casa Nueva")
    assert main_window.unit_selection.active_rooms() == ["Casa Nueva"]
    assert main_window._unidad_activa == "Casa Nueva"


def test_on_enter_ofrece_solo_los_cuartos_de_la_unidad_activa(main_window):
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window.room_selection.add("Cocina A")
    main_window._on_enter()
    assert main_window.room_palette.opciones_visibles() == ["Cocina A"]
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -k unidad_elegida -q`
Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute 'unit_palette'`

- [ ] **Step 3: Implementar**

Junto a la construcción de `self.room_palette` (línea ~1084-1086):

```python
        self.unit_palette = UnitPalette(self)
        self.unit_palette.unit_activated.connect(self._on_unidad_elegida_en_paleta)
        self.unit_palette.unit_created.connect(self._on_unidad_creada_en_paleta)
```

Con el import:

```python
from clasificador_video.ui.unit_palette import UnitPalette
```

El atajo, junto a `("Ctrl+R", self.room_rail.focus_rooms)` (línea 1254):

```python
            ("Ctrl+U", self._abrir_paleta_de_unidades),
```

Los métodos nuevos, junto a `_on_room_elegido_en_paleta` (línea ~1548):

```python
    def _abrir_paleta_de_unidades(self) -> None:
        self.unit_palette.abrir(
            self.unit_selection.active_rooms(),
            self._conteos_por_unidad(),
        )
        self._colocar_paleta_de_unidades()

    def _conteos_por_unidad(self) -> dict[str, int]:
        from collections import Counter

        cuenta: Counter[str] = Counter()
        for clip in self.clips:
            unidad = self._unidad_de(clip.categoria_path)
            if unidad is not None:
                cuenta[unidad] += 1
        return dict(cuenta)

    def _on_unidad_elegida_en_paleta(self, nombre: str) -> None:
        self._activar_unidad(nombre)

    def _on_unidad_creada_en_paleta(self, nombre: str) -> None:
        self.unit_selection.add(nombre)
        self._activar_unidad(nombre)

    def _colocar_paleta_de_unidades(self) -> None:
        """Misma logica que `_colocar_paleta` (linea ~1544) pero para
        `unit_palette` -- centrada sobre el video, no sobre la ventana."""
        etapa = self.video_stage
        origen = etapa.mapTo(self, etapa.rect().topLeft())
        x = origen.x() + (etapa.width() - self.unit_palette.width()) // 2
        y = origen.y() + 24
        self.unit_palette.move(x, y)
```

(Revisar el cuerpo exacto de `_colocar_paleta` antes de este paso — el
`y = origen.y() + 24` de arriba es un placeholder razonable, pero debe
copiar el cálculo REAL de esa función, que no vino completo en la
investigación de este plan.)

Y en `_on_enter` (línea ~1509-1525), sin cambios de fondo — ya usa
`self.room_selection.active_rooms()`, que gracias a la Fase 1 ya es el
catálogo de la unidad activa. Este test pasa solo verificando que la
Fase 1 quedó bien conectada; si falla, el bug está en `_activar_unidad`
o en la construcción de `room_palette`, no aquí.

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -q`
Expected: PASS (15 tests acumulados)

- [ ] **Step 5: Verificación visual — `grab()`**

Siguiendo la convención del proyecto (CLAUDE.md, "Verificación visual
real"): construir una `MainWindow` de prueba en un script del scratchpad
de la sesión, crear dos unidades, abrir `unit_palette` con `Ctrl+U`,
`grab()` la ventana a un PNG, y leerlo con la herramienta de lectura de
archivos antes de dar el Task por bueno. El script y el PNG NO se
comitean — van al scratchpad de la sesión (CLAUDE.md, higiene de
archivos).

- [ ] **Step 6: Suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS salvo los 5 fallos preexistentes.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Conectar la paleta de unidades: Ctrl+U, elegir activa, crear activa

Elegir o crear una unidad en la paleta llama _activar_unidad, que ya
existia desde la Fase 1 -- este commit es pura conexion de UI. La
paleta de cuartos (_on_enter) no cambia: ya opera sobre
self.room_selection, que desde la Fase 1 es el catalogo de la unidad
activa.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Fase 5 — Asignar con unidad

### Task 9: `_asignar_cuarto` escribe `[unidad, cuarto]` cuando hay unidad activa

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_unidades.py`

- [ ] **Step 1: Pruebas que fallan**

```python
# agregar a tests/ui/test_main_window_unidades.py
def test_asignar_cuarto_sin_unidad_activa_no_cambia(main_window):
    main_window.load_clips([_clip_de_prueba()])  # usar el helper que ya
    # exista en tests/ui/test_main_window.py para clips de prueba
    main_window._asignar_cuarto(["Cocina"])
    assert main_window.clips[0].categoria_path == ["Cocina"]


def test_asignar_cuarto_con_unidad_activa_prefija_la_unidad(main_window):
    main_window.load_clips([_clip_de_prueba()])
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window._asignar_cuarto(["Cocina"])
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]


def test_ultimo_cuarto_usado_no_lleva_la_unidad(main_window):
    # _ultimo_cuarto_usado es el nombre del CUARTO -- lo que S vuelve a
    # ofrecer -- no el categoria_path completo
    main_window.load_clips([_clip_de_prueba()])
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window._asignar_cuarto(["Cocina"])
    assert main_window._ultimo_cuarto_usado == "Cocina"
```

(Reemplazar `_clip_de_prueba()` por el helper/fixture real que ya use
`test_main_window.py` para construir clips — no inventar uno nuevo.)

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -k asignar_cuarto -q`
Expected: FAIL — el segundo test da `categoria_path == ["Cocina"]` en vez
de `["Casa A", "Cocina"]`.

- [ ] **Step 3: Implementar — `main_window.py:1558-1569`**

```python
    def _asignar_cuarto(self, room_path: list[str]) -> None:
        """Un solo camino para asignar cuarto, lo pida un digito o la `S`.

        Con dos caminos, `S` seria una asignacion de segunda: no registraria
        en el historial, o no avanzaria, y eso no se ve hasta usarla.

        Con una unidad activa, el `categoria_path` que se escribe lleva la
        unidad delante (`[unidad, cuarto]`) -- pero `room_path` que llega
        aqui SIGUE siendo solo el cuarto: quien llama (digitos, `S`, la
        paleta) no necesita saber si hay una unidad activa o no.
        """
        if room_path:
            self._ultimo_cuarto_usado = room_path[0]
        completo = (
            [self._unidad_activa] + room_path if self._unidad_activa else room_path
        )
        self._apply_categoria_to_targets(completo)
        self._refresh_sheet()
        self._autosave()
        self._avanzar_en_la_cola()
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -q`
Expected: PASS (18 tests acumulados)

- [ ] **Step 5: `_apply_categoria_to_targets` — el color de registro usa el cuarto, no `path[0]`**

`_apply_categoria_to_targets` (línea 1451-1464) calcula
`color=self._color_de_cuarto(path[0])` para el historial — con unidad,
`path[0]` es la unidad, no el cuarto, y `_color_de_cuarto` buscaría un
nombre de unidad dentro del catálogo de cuartos sin encontrarlo (cae al
`else theme.TEXT_3` de `_color_de_cuarto`, lo que dejaría el historial sin
color en vez de reventar — no es un crash, pero es un dato incorrecto).
Corregir:

```python
    def _apply_categoria_to_targets(self, path: list[str]) -> None:
        indices = self._bulk_target_indices()
        if not indices:
            return
        cuarto = self._cuarto_de(path)
        self._registrar(
            etiqueta=cuarto,
            detalle=self._detalle(indices),
            color=self._color_de_cuarto(cuarto),
            clips=indices,
            campos=("categoria_path",),
        )
        for indice in indices:
            self.clips[indice].categoria_path = list(path)
```

(`cuarto = path[-1]` de antes y `self._cuarto_de(path)` son equivalentes
hoy — usar el helper igual, por consistencia con el resto del código
tocado en la Fase 0.)

- [ ] **Step 6: Suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS salvo los 5 fallos preexistentes.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Asignar cuarto prefija la unidad activa al categoria_path

_asignar_cuarto sigue recibiendo solo el nombre del cuarto -- quien
llama (digitos, S, la paleta de cuartos) no necesita saber si hay una
unidad activa. La unidad se antepone en un solo lugar antes de escribir
categoria_path, y _ultimo_cuarto_usado (lo que S vuelve a ofrecer)
sigue guardando solo el cuarto.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### Task 10: reasignación en lote de UNIDAD (el camino de migración de Bruno)

Reasignar el cuarto en lote ya funciona sin cambios (Task 9 lo cubre: la
paleta de cuartos + selección múltiple + `_bulk_target_indices` ya
prefijan la unidad activa). Lo que falta es reasignar la UNIDAD misma en
lote — mover clips de "sin unidad" o de otra unidad a la unidad activa,
sin tocar su cuarto. Es el camino de migración de `Cocina-A`/`Cocina-B` a
mano (spec §4) y de los clips del bloque "Sin unidad" tras crear la
primera unidad (spec §4, adenda del 2026-09-20).

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_unidades.py`

- [ ] **Step 1: Pruebas que fallan**

```python
# agregar a tests/ui/test_main_window_unidades.py
def test_asignar_unidad_conserva_el_cuarto_del_clip(main_window):
    main_window.load_clips([_clip_de_prueba()])
    main_window.clips[0].categoria_path = ["Cocina"]
    main_window.unit_selection.add("Casa A")
    main_window._asignar_unidad("Casa A")
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]


def test_asignar_unidad_a_clip_sin_cuarto_lo_deja_sin_cuarto(main_window):
    main_window.load_clips([_clip_de_prueba()])
    main_window.clips[0].categoria_path = []
    main_window.unit_selection.add("Casa A")
    main_window._asignar_unidad("Casa A")
    assert main_window.clips[0].categoria_path == []


def test_asignar_unidad_reemplaza_la_unidad_anterior(main_window):
    main_window.load_clips([_clip_de_prueba()])
    main_window.clips[0].categoria_path = ["Casa A", "Cocina"]
    main_window.unit_selection.add("Casa A")
    main_window.unit_selection.add("Casa B")
    main_window._asignar_unidad("Casa B")
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -k asignar_unidad -q`
Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute '_asignar_unidad'`

- [ ] **Step 3: Implementar — junto a `_asignar_cuarto`**

```python
    def _asignar_unidad(self, unidad: str) -> None:
        """Mueve los clips del alcance actual a `unidad`, SIN tocar su
        cuarto. Es el camino de migracion: crear las unidades y, con la
        seleccion de la hoja, reasignarles la unidad en lote a los clips
        que ya tenian un `Cocina-A`/`Cocina-B` puesto a mano (spec
        2026-09-20 §4). Un clip sin cuarto todavia (categoria_path vacio)
        no gana un cuarto de la nada -- se queda sin cuarto y sin unidad.
        """
        indices = self._bulk_target_indices()
        if not indices:
            return
        nuevos = {}
        for indice in indices:
            actual = self.clips[indice].categoria_path
            cuarto = self._cuarto_de(actual)
            nuevos[indice] = [unidad, cuarto] if cuarto is not None else []
        afectados = [i for i in indices if nuevos[i] != self.clips[i].categoria_path]
        if not afectados:
            return
        self._registrar(
            etiqueta=unidad,
            detalle=self._detalle(afectados),
            color=self._color_de_unidad(unidad),
            clips=afectados,
            campos=("categoria_path",),
        )
        for indice in afectados:
            self.clips[indice].categoria_path = nuevos[indice]
        self._refresh_sheet()
        self._autosave()

    def _color_de_unidad(self, unidad: str) -> str:
        unidades = self.unit_selection.active_rooms()
        return theme.unit_color(unidades.index(unidad)) if unidad in unidades else theme.TEXT_3
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -q`
Expected: PASS (21 tests acumulados)

- [ ] **Step 5: Disparo desde la UI — el mismo patrón que asignar cuarto en lote**

Revisar cómo se dispara HOY `_asignar_cuarto` para lote (selección en la
hoja + `⏎`/dígito) y conectar `_asignar_unidad` al mismo gesto pero con
`unit_palette.unit_activated` cuando hay más de un clip seleccionado — es
decir, si `len(self.selected_indices) > 1` al elegir una unidad en la
paleta, además de activar la unidad (Task 8), también reasigna el lote:

```python
    def _on_unidad_elegida_en_paleta(self, nombre: str) -> None:
        if len(self.selected_indices) > 1:
            self._asignar_unidad(nombre)
        self._activar_unidad(nombre)
```

Prueba correspondiente:

```python
def test_elegir_unidad_con_lote_seleccionado_reasigna_y_activa(main_window):
    main_window.load_clips([_clip_de_prueba(), _clip_de_prueba()])
    main_window.clips[0].categoria_path = ["Cocina"]
    main_window.clips[1].categoria_path = ["Baño"]
    main_window.selected_indices = {0, 1}
    main_window.unit_selection.add("Casa A")
    main_window._on_unidad_elegida_en_paleta("Casa A")
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]
    assert main_window.clips[1].categoria_path == ["Casa A", "Baño"]
    assert main_window._unidad_activa == "Casa A"
```

- [ ] **Step 6: Correr y confirmar que pasa; suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_unidades.py -q`
Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS salvo los 5 fallos preexistentes.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Reasignar unidad en lote: el camino de migracion de Cocina-A/Cocina-B

_asignar_unidad mueve el alcance seleccionado a una unidad SIN tocar su
cuarto. Elegir una unidad en la paleta con mas de un clip seleccionado
reasigna el lote y activa la unidad en el mismo gesto -- es el camino
de migracion manual que el spec §4 decidio para el proyecto actual de
Bruno, y el mismo que resuelve el bloque "Sin unidad" tras crear la
primera unidad.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Fase 6 — La hoja: agrupar por unidad y el bloque "Sin unidad"

### Task 11: `clip_sheet` agrupa por unidad arriba de cuarto

`ClipThumbnail` necesita cargar la unidad del clip además del cuarto, y
`_group_of`/`_orden_de_grupo` (`clip_sheet.py:2598-2701`) necesitan un
nivel más externo. Se sigue el MISMO patrón que ya usa el agrupamiento
por bin (`SIN_BIN`, `_bin_order`), con una constante nueva `SIN_UNIDAD`
para el bloque acordado con Bruno el 2026-09-20 (clips sin unidad
asignada, agrupados aparte mientras dura una migración).

**Files:**
- Modify: `src/clasificador_video/ui/clip_sheet.py`
- Modify: `src/clasificador_video/ui/main_window.py` (arma `ClipThumbnail` con la unidad)
- Test: `tests/ui/test_clip_sheet_unidades.py` (nuevo)

- [ ] **Step 1: Pruebas que fallan**

```python
# tests/ui/test_clip_sheet_unidades.py
"""Agrupar por unidad, arriba de cuarto. Sin ninguna unidad en el
proyecto, el agrupamiento es el de siempre -- sin este nivel extra."""
import pytest

from clasificador_video.ui.clip_sheet import ClipSheet, ClipThumbnail, SIN_UNIDAD


def _thumb(unidad, cuarto, bin_nombre="Sony"):
    return ClipThumbnail(
        path="/x.mp4", room_label=cuarto, flag="none",
        room_color=None, numero=1, in_frame=None, out_frame=None,
        fps=30.0, duration_frames=None, aspect_ratio=16 / 9,
        bin_nombre=bin_nombre, tiene_proxy=False, unit_label=unidad,
    )


@pytest.fixture
def hoja(qtbot):
    h = ClipSheet()
    qtbot.addWidget(h)
    return h


def test_sin_unidades_en_el_proyecto_no_agrupa_por_unidad(hoja):
    hoja.set_thumbnails([_thumb(None, "Cocina")])
    assert hoja._group_of(hoja.item_widgets[0]) == ("Sony", None, "Cocina")


def test_con_unidad_el_grupo_incluye_la_unidad(hoja):
    hoja.set_thumbnails([_thumb("Casa A", "Cocina")])
    assert hoja._group_of(hoja.item_widgets[0]) == ("Sony", "Casa A", "Cocina")


def test_clip_sin_unidad_cae_en_sin_unidad_si_el_proyecto_tiene_unidades(hoja):
    hoja.set_unit_order(["Casa A"])
    hoja.set_thumbnails([_thumb(None, "Cocina")])
    assert hoja._group_of(hoja.item_widgets[0]) == ("Sony", SIN_UNIDAD, "Cocina")
```

(Los nombres exactos de constructor de `ClipThumbnail`/`set_thumbnails` y
la firma real de `_group_of` deben confirmarse leyendo
`clip_sheet.py:2598-2616` antes de escribir esto tal cual — arriba está
el CONTRATO esperado, no necesariamente cada kwarg exacto del
constructor actual. Ajustar a la firma real sin cambiar la intención de
cada prueba.)

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet_unidades.py -q`
Expected: FAIL — `ImportError: cannot import name 'SIN_UNIDAD'`

- [ ] **Step 3: Implementar**

Agregar la constante junto a `SIN_BIN`/`SIN_CLASIFICAR` (cerca de la línea
51-57):

```python
SIN_UNIDAD = "Sin unidad"
```

`ClipThumbnail` gana el campo `unit_label: str | None = None` (buscar su
`@dataclass` y agregarlo con default `None` — retro-compatible con todo
código que lo construya sin este kwarg).

`_group_of` (línea 2598-2616) pasa a devolver una tupla de 3, con la
unidad en el medio:

```python
    def _group_of(self, clip: ClipThumbnail) -> tuple[str, str | None, str]:
        cuarto = (clip.room_label or SIN_CLASIFICAR) if self._agrupar_por_cuarto \
            else SIN_AGRUPAR
        unidad = None
        if self._hay_unidades:
            unidad = clip.unit_label or SIN_UNIDAD
        return (clip.bin_nombre or SIN_BIN, unidad, cuarto)
```

`self._hay_unidades: bool` se fija con un `set_unit_order` nuevo, hermano
de `set_room_order` (línea 2331-2342):

```python
    def set_unit_order(self, units: list[str]) -> None:
        """El orden de unidades del proyecto. Vacio == proyecto sin
        unidades: ahi `_group_of` no agrega el nivel de unidad y todo se
        comporta exactamente como antes de que esto existiera."""
        if units == self._unit_order:
            return
        self._unit_order = list(units)
        self._hay_unidades = bool(units)
        self._regroup()
```

Con `self._unit_order: list[str] = []` y `self._hay_unidades: bool = False`
inicializados en `__init__` junto a `self._room_order`/`self._bin_order`.

`_orden_de_grupo` (línea 2676-2701) gana la unidad como nivel más externo,
DESPUÉS del bin (bin sigue siendo lo más externo, sin cambios ahí —
spec §5 dice "unidad primero, cuarto adentro" refiriéndose al agrupamiento
visual dentro de cada bin, no por encima de él: la hoja ya agrupaba por
bin primero y eso no lo toca esta spec):

```python
    def _orden_de_grupo(self, clave: tuple[str, str | None, str]) -> tuple:
        """Bin primero (por posicion de importacion), unidad despues (por
        el orden de la paleta de unidades, "Sin unidad" arriba porque es
        la cola de trabajo de la migracion), y adentro los cuartos, con
        «Sin clasificar» arriba porque es la cola de trabajo."""
        bin_nombre, unidad, cuarto = clave
        if bin_nombre == SIN_BIN:
            pos_bin = -1
        elif bin_nombre in self._bin_order:
            pos_bin = self._bin_order.index(bin_nombre)
        else:
            pos_bin = len(self._bin_order)

        if unidad is None:
            pos_unidad = -1  # proyecto sin unidades: no hay nivel que ordenar
        elif unidad == SIN_UNIDAD:
            pos_unidad = -1  # el bloque migratorio va arriba, antes que las unidades
        elif unidad in self._unit_order:
            pos_unidad = self._unit_order.index(unidad) + 1
        else:
            pos_unidad = len(self._unit_order) + 1

        pos_cuarto = (self._room_order.index(cuarto)
                      if cuarto in self._room_order else len(self._room_order))
        return (pos_bin, bin_nombre, pos_unidad, unidad, cuarto != SIN_CLASIFICAR,
                pos_cuarto, cuarto)
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet_unidades.py -q`
Expected: PASS (3 tests)

- [ ] **Step 5: `_refrescar_hoja_de_verdad` arma `unit_label` y llama `set_unit_order`**

En `main_window.py:5559-5599`, agregar al `ClipThumbnail(...)`:

```python
                unit_label=self._unidad_de(clip.categoria_path),
```

Y junto a `self.clip_sheet.set_room_order(...)` (línea 5599):

```python
        self.clip_sheet.set_unit_order(self.unit_selection.active_rooms())
```

- [ ] **Step 6: Prueba de no-regresión — un proyecto sin unidades se ve igual**

```python
# agregar a tests/ui/test_clip_sheet_unidades.py
def test_proyecto_sin_unidades_agrupa_exactamente_como_antes(hoja):
    hoja.set_thumbnails([_thumb(None, "Cocina"), _thumb(None, "Baño")])
    grupos = {hoja._group_of(w) for w in hoja.item_widgets}
    assert grupos == {("Sony", None, "Cocina"), ("Sony", None, "Baño")}
```

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet_unidades.py tests/ui/test_clip_sheet.py -q`
Expected: PASS, y CERO cambios en `test_clip_sheet.py` (el archivo
existente no necesita tocarse: la clave de grupo de 2 elementos que esos
tests ya conocen sigue siendo válida en espíritu — si algún test ahí
compara la tupla completa de `_group_of` y ahora falla por el tercer
elemento nuevo, ES una regresión real que hay que arreglar, no ignorar:
revisar caso por caso).

- [ ] **Step 7: Banda visual `.unit-band`, arriba de cada grupo de unidad**

Con el patrón de bloque de grupo ya existente en `_regroup`
(`clip_sheet.py:2703-2757`, que arma `_GroupBlock` por clave), agregar un
encabezado de unidad análogo al de bin. Esto requiere leer
`_GroupBlock`/cómo se pinta el encabezado de bin ANTES de escribir el
código — no viene completo en la investigación de este plan. Sub-pasos:

  1. Leer `clip_sheet.py` alrededor de `_GroupBlock` y del encabezado de
     bin (buscar `class _GroupBlock` y su método de pintar/etiquetar).
  2. Escribir una prueba que verifique que un grupo con unidad muestra un
     `unit-band` widget/label con el nombre de la unidad y su color
     (`theme.unit_color`), y que un grupo sin unidad (proyecto sin
     unidades) NO muestra ninguno.
  3. Implementar siguiendo el mismo mecanismo que ya usa el bin-header,
     con `theme.unit_color(self._unit_order.index(unidad))` para el color
     del swatch cuadrado (mismo criterio visual que en `UnitPalette`,
     Task 6).
  4. Verificación visual con `grab()` (CLAUDE.md): armar una hoja de
     prueba con 2 unidades y clips en cada una, capturar PNG al
     scratchpad, leerlo.

- [ ] **Step 8: Suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS salvo los 5 fallos preexistentes.

- [ ] **Step 9: Commit**

```bash
git add src/clasificador_video/ui/clip_sheet.py src/clasificador_video/ui/main_window.py tests/ui/test_clip_sheet_unidades.py
git commit -m "$(cat <<'EOF'
La hoja agrupa por unidad arriba de cuarto, con banda visual

Mismo patron que ya agrupa por bin: SIN_UNIDAD es el bloque migratorio
para clips todavia sin unidad asignada mientras existe al menos una
unidad en el proyecto, y va arriba porque es cola de trabajo. Un
proyecto sin ninguna unidad no gana este nivel de agrupamiento -- se ve
exactamente igual que antes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### Task 12: el rail agrupa por unidad, con el mismo bloque "Sin unidad"

Este es el componente más grande de la Fase 6: `RoomRail.set_rooms`
(`room_rail.py:587-623`) hoy asume una sola lista plana de cuartos en
`self.rows`, con drag-and-drop de reordenamiento sobre esa lista única.
Con unidades pasa a haber una lista de filas POR unidad (más la lista
"Sin unidad" cuando aplica), cada una con su propio encabezado de banda.

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py`
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_room_rail_unidades.py` (nuevo)

- [ ] **Step 1: Leer antes de escribir**

Leer `room_rail.py` completo (824 líneas) — en particular
`_FilaCuarto`, el resto de `set_rooms`, y TODO el bloque de drag & drop
(líneas 625-717 según la exploración previa) — antes de tocar nada. El
diseño de abajo asume la estructura vista hasta la línea 623; el
mecanismo de arrastre necesita quedar acotado a reordenar SOLO dentro de
la misma unidad (decisión de este plan, consistente con que el spec no
menciona arrastrar un cuarto entre unidades — si Bruno lo pide después,
es una spec aparte).

- [ ] **Step 2: Prueba que falla — API nueva**

```python
# tests/ui/test_room_rail_unidades.py
"""El rail agrupa por unidad. Sin ninguna unidad en el proyecto, se ve
exactamente como siempre -- una sola banda implicita, sin encabezado."""
import pytest

from clasificador_video.ui.room_rail import RoomRail


@pytest.fixture
def rail(qtbot):
    r = RoomRail()
    qtbot.addWidget(r)
    return r


def test_sin_unidades_se_comporta_como_antes(rail):
    rail.set_rooms_agrupados(
        unidades=[], rooms_por_unidad={"": ["Cocina", "Baño"]},
        counts={("", "Cocina"): 3, ("", "Baño"): 1},
    )
    assert [f.nombre for f in rail.rows] == ["Cocina", "Baño"]


def test_con_unidades_hay_una_banda_por_unidad(rail):
    rail.set_rooms_agrupados(
        unidades=["Casa A", "Casa B"],
        rooms_por_unidad={
            "": ["Sin migrar"],
            "Casa A": ["Cocina"],
            "Casa B": ["Cocina", "Baño"],
        },
        counts={},
    )
    assert [b.nombre for b in rail.unit_bands] == ["Sin unidad", "Casa A", "Casa B"]
    assert [f.nombre for f in rail.rows_por_unidad["Casa A"]] == ["Cocina"]
    assert [f.nombre for f in rail.rows_por_unidad["Casa B"]] == ["Cocina", "Baño"]


def test_bloque_sin_unidad_no_aparece_si_esta_vacio(rail):
    rail.set_rooms_agrupados(
        unidades=["Casa A"], rooms_por_unidad={"": [], "Casa A": ["Cocina"]},
        counts={},
    )
    assert [b.nombre for b in rail.unit_bands] == ["Casa A"]
```

- [ ] **Step 3: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_room_rail_unidades.py -q`
Expected: FAIL — `AttributeError: 'RoomRail' object has no attribute 'set_rooms_agrupados'`

- [ ] **Step 4: Implementar `set_rooms_agrupados` reusando `set_rooms` internamente**

La forma más DRY de resolver esto sin reescribir el drag & drop: mantener
`set_rooms` (la API vieja, plana) intacta y usarla como motor por cada
banda, con un contenedor de bandas nuevo por encima.

```python
    def set_rooms_agrupados(self, unidades: list[str],
                             rooms_por_unidad: dict[str, list[str]],
                             counts: dict[tuple[str, str], int]) -> None:
        """Repuebla el rail agrupado por unidad. `unidades` vacia es un
        proyecto sin unidades: ahi se comporta exactamente como
        `set_rooms` de siempre, sin ninguna banda -- el catalogo `""`
        (sin unidad) es el unico que existe.

        `rooms_por_unidad` trae la llave `""` para el bloque "Sin unidad"
        -- migratorio, solo se banda si tiene cuartos Y el proyecto ya
        tiene alguna unidad creada.
        """
        if not unidades:
            self.set_rooms(rooms_por_unidad.get("", []),
                            {c: n for (u, c), n in counts.items() if u == ""})
            self._limpiar_bandas()
            return

        self._limpiar_bandas()
        orden = (["" ] if rooms_por_unidad.get("") else []) + list(unidades)
        for llave in orden:
            nombre_banda = SIN_UNIDAD_ETIQUETA if llave == "" else llave
            banda = self._crear_banda(nombre_banda)
            self.unit_bands.append(banda)
            filas = []
            for indice, cuarto in enumerate(rooms_por_unidad.get(llave, [])):
                numero = indice + 1 if indice < MAX_TECLAS else None
                fila = _FilaCuarto(numero, cuarto, theme.room_color(indice),
                                    counts.get((llave, cuarto), 0))
                fila.assign_requested.connect(self.room_assign_requested.emit)
                fila.rename_requested.connect(self.room_renamed.emit)
                fila.move_requested.connect(self.room_moved.emit)
                fila.remove_requested.connect(self.room_removed.emit)
                fila.mover_foco_requested.connect(self._mover_foco)
                self._rooms_layout.addWidget(fila)
                filas.append(fila)
            self.rows_por_unidad[llave] = filas
        # `self.rows` sigue existiendo como la union de todas -- codigo
        # como `focus_rooms` que navega "la primera fila" no necesita
        # saber de bandas.
        self.rows = [f for filas in self.rows_por_unidad.values() for f in filas]
```

Con `self.unit_bands: list[_BandaDeUnidad] = []`,
`self.rows_por_unidad: dict[str, list[_FilaCuarto]] = {}` inicializados
en `__init__`, `SIN_UNIDAD_ETIQUETA = "Sin unidad"` como constante del
módulo, y helpers:

```python
    def _limpiar_bandas(self) -> None:
        for banda in self.unit_bands:
            banda.setParent(None)
            banda.deleteLater()
        self.unit_bands = []
        for filas in self.rows_por_unidad.values():
            for fila in filas:
                fila.setParent(None)
                fila.deleteLater()
        self.rows_por_unidad = {}

    def _crear_banda(self, nombre: str) -> "_BandaDeUnidad":
        indice = len([b for b in self.unit_bands if b.nombre != SIN_UNIDAD_ETIQUETA])
        color = None if nombre == SIN_UNIDAD_ETIQUETA else theme.unit_color(indice)
        banda = _BandaDeUnidad(nombre, color)
        self._rooms_layout.addWidget(banda)
        return banda
```

Y la clase de la banda, con el mismo swatch cuadrado que `UnitPalette`:

```python
class _BandaDeUnidad(QWidget):
    """El encabezado de un grupo de cuartos por unidad. `color=None` es el
    bloque "Sin unidad" -- sin swatch, solo el rotulo, porque no es una
    identidad de unidad sino la ausencia de una."""

    def __init__(self, nombre: str, color: str | None, parent=None):
        super().__init__(parent)
        self.nombre = nombre
        self.setObjectName("unitBand")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 8, 2, 4)
        layout.setSpacing(6)
        if color is not None:
            swatch = QLabel("")
            swatch.setFixedSize(11, 11)
            swatch.setAttribute(Qt.WA_StyledBackground, True)
            swatch.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
            layout.addWidget(swatch)
        etiqueta = QLabel(nombre.upper())
        etiqueta.setObjectName("unitBandLabel")
        theme.apply_letter_spacing(etiqueta)
        layout.addWidget(etiqueta)
        layout.addStretch(1)
```

- [ ] **Step 5: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_room_rail_unidades.py -q`
Expected: PASS (3 tests)

- [ ] **Step 6: Conectar desde `MainWindow._refresh_rail` (línea 1783-1814)**

Reemplazar la llamada a `self.room_rail.set_rooms(rooms, dict(counts))`
por `set_rooms_agrupados`, construyendo `rooms_por_unidad` y `counts`
por-unidad desde `self.room_selections`:

```python
    def _refresh_rail(self) -> None:
        from collections import Counter

        counts: Counter[tuple[str, str]] = Counter()
        for clip in self.clips:
            cuarto = self._cuarto_de(clip.categoria_path)
            if cuarto is not None:
                unidad = self._unidad_de(clip.categoria_path) or ""
                counts[(unidad, cuarto)] += 1
        unidades = self.unit_selection.active_rooms()
        rooms_por_unidad = {
            llave: self.room_selections[llave].active_rooms()
            for llave in [""] + unidades
            if llave in self.room_selections
        }
        total = len(self.clips)
        sin_clasificar = sum(1 for c in self.clips if not c.categoria_path)
        picks = sum(1 for c in self.clips if c.flag == "pick")
        rejects = sum(1 for c in self.clips if c.flag == "reject")

        self.room_rail.set_progress(total - sin_clasificar, total, sin_clasificar)
        self.room_rail.set_rooms_agrupados(unidades, rooms_por_unidad, dict(counts))
        destacados = sum(1 for c in self.clips if c.flag == "destacado")
        self.room_rail.set_flags(picks, rejects, sin_clasificar, destacados)
        clip = self.current_clip
        self.room_rail.set_current_room(
            self._cuarto_de(clip.categoria_path) if clip and clip.categoria_path else None
        )
        anterior = self._cuarto_para_la_tecla_s()
        self.room_rail.set_same_room(
            anterior,
            theme.room_color(self.room_selection.active_rooms().index(anterior))
            if anterior in self.room_selection.active_rooms() else None,
        )
        self.title_bar.set_project(self.project_name, total,
                                   bins=len(self.bins.nombres()))
        self.status_bar.set_unclassified(sin_clasificar)
        self.status_bar.set_proxies(*self._resumen_de_proxies())
```

Nota: `set_same_room` sigue usando `self.room_selection` (el catálogo de
la unidad ACTIVA, no el global) — `S` opera sobre el contexto activo,
consistente con la Fase 5.

- [ ] **Step 7: Verificación visual con `grab()` (CLAUDE.md)**

Construir un proyecto de prueba con 2 unidades y clips en el bloque "Sin
unidad", tomar `grab()` del rail completo, guardar el PNG en el
scratchpad de la sesión y leerlo antes de continuar.

- [ ] **Step 8: Suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS salvo los 5 fallos preexistentes.

- [ ] **Step 9: Commit**

```bash
git add src/clasificador_video/ui/room_rail.py src/clasificador_video/ui/main_window.py tests/ui/test_room_rail_unidades.py
git commit -m "$(cat <<'EOF'
El rail agrupa por unidad, con banda y el bloque migratorio Sin unidad

set_rooms_agrupados reusa el motor de set_rooms (que sigue existiendo
intacto, y es lo que corre cuando el proyecto no tiene unidades) una
vez por banda. El bloque "Sin unidad" solo aparece si el proyecto ya
tiene alguna unidad Y le quedan clips por migrar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Fase 7 — Plugin UXP: dos niveles en vez de uno

### Task 13: `estructura.js::caminoDelClip` numera el segmento del cuarto, dondequiera que esté

**Decisión de implementación (no reabre el spec):** el spec §7 dice que
`caminoDelClip` numera "segmento 0 (unidad) y segmento 1 (cuarto), cada
uno con el orden de guía que le corresponda". El spec §8 excluye
explícitamente tocar la guía de edición para unidades este round («ahorita
ni jala bien»). No existe hoy, ni se crea en este plan, un "orden de guía
de unidades" — así que la unidad, cuando existe, se crea SIN número (el
mismo comportamiento que ya tiene un cuarto sin guía: "sin numero,
exactamente como antes"). Lo que SÍ se generaliza es CUÁL segmento es el
cuarto: hoy siempre el 0, con unidad pasa a ser el 1.

**Files:**
- Modify: `uxp-plugin/js/estructura.js`
- Create: `uxp-plugin/pruebas/estructura.pruebas.js` (no existe hoy — ver nota del reporte de exploración)
- Modify: `uxp-plugin/pruebas/correr.js` (agregar el archivo nuevo a `ARCHIVOS`)

- [ ] **Step 1: Pruebas que fallan**

```javascript
// uxp-plugin/pruebas/estructura.pruebas.js
// caminoDelClip: numera el CUARTO, sea cual sea su posicion en
// categoryPath -- segmento 0 sin unidad, segmento 1 con unidad. La unidad
// misma no lleva numero: no hay guia de unidades (spec 2026-09-20 §7-§8).
module.exports = function (ctx) {
  return [
    {
      nombre: "sin unidad, el cuarto en 0 se numera con la guia",
      fn: () => {
        const r = ctx.caminoDelClip(["Cocina"], ["Cocina", "Baño"]);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "01. Cocina"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "con unidad, el cuarto en 1 se numera y la unidad no",
      fn: () => {
        const r = ctx.caminoDelClip(["Casa A", "Cocina"], ["Cocina", "Baño"]);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "Casa A", "01. Cocina"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "con unidad y cuarto fuera de la guia, ninguno de los dos se numera",
      fn: () => {
        const r = ctx.caminoDelClip(["Casa A", "Recamara nueva"], ["Cocina"]);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "Casa A", "Recamara nueva"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "sin guia, ninguno de los dos lleva numero",
      fn: () => {
        const r = ctx.caminoDelClip(["Casa A", "Cocina"], []);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "Casa A", "Cocina"]), detalle: r.join(" > ") };
      },
    },
  ];
};
```

- [ ] **Step 2: Agregar el archivo a `correr.js` y correr**

En `uxp-plugin/pruebas/correr.js`, agregar `"pruebas/estructura.pruebas.js"`
a la lista de archivos de prueba (buscar dónde se listan los `.pruebas.js`,
junto a `numeroDeCuarto.pruebas.js` — no es la misma lista `ARCHIVOS` de
líneas 39+, que es la de código fuente del plugin; revisar el resto de
`correr.js` para ubicar la lista de pruebas).

Run: `node uxp-plugin/pruebas/correr.js`
Expected: FAIL en los 4 casos nuevos (comportamiento viejo: solo numera
segmento 0 siempre).

- [ ] **Step 3: Implementar — `estructura.js:53-61`**

```javascript
// El camino completo de un clip: su cuarto (y su unidad, si tiene) colgados
// de «02. Clip». La app manda ["Cocina"] o ["Casa A", "Cocina"] y aqui se
// vuelve ["02. Clip", "03. Cocina"] o ["02. Clip", "Casa A", "03. Cocina"].
//
// El CUARTO es el ultimo segmento (categoryPath.length - 1) y es el unico
// que lleva numero, con el orden de la guia que ya existia. La UNIDAD --
// cuando hay una, el primer segmento -- no lleva numero: no existe todavia
// una guia de unidades (spec 2026-09-20 §7-§8, decidido fuera de alcance).
function caminoDelClip(categoryPath, ordenDeLaGuia) {
  const camino = (categoryPath || []).slice();
  const orden = ordenDeLaGuia || [];
  if (camino.length) {
    const indiceDelCuarto = camino.length - 1;
    const lugar = orden.indexOf(camino[indiceDelCuarto]);
    if (lugar !== -1) camino[indiceDelCuarto] = conNumero(camino[indiceDelCuarto], lugar + 1);
  }
  return [CARPETA_DE_CLIPS].concat(camino);
}
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todos los casos en verde, incluidos los preexistentes.

- [ ] **Step 5: Commit**

```bash
git add uxp-plugin/js/estructura.js uxp-plugin/pruebas/estructura.pruebas.js uxp-plugin/pruebas/correr.js
git commit -m "$(cat <<'EOF'
caminoDelClip numera el cuarto sea cual sea su posicion en categoryPath

Antes asumia que el cuarto era siempre el segmento 0. Con unidades pasa
a ser el ULTIMO segmento (0 sin unidad, 1 con unidad), y sigue siendo
el unico numerado -- la unidad no lleva numero porque no existe una
guia de unidades todavia (spec 2026-09-20 §7-§8, fuera de alcance esta
ronda).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### Task 14: `marcaCamara.js` marca la unidad con la combinación de sus cuartos

**Files:**
- Modify: `uxp-plugin/js/marcaCamara.js`
- Modify: `uxp-plugin/pruebas/marcaCamara.pruebas.js`

- [ ] **Step 1: Pruebas que fallan**

Agregar a `uxp-plugin/pruebas/marcaCamara.pruebas.js` (revisar el formato
exacto de los casos existentes antes de escribir estos, para que
combinen con `module.exports` que ya tiene el archivo):

```javascript
    {
      nombre: "la marca de una unidad combina las camaras de TODOS sus cuartos",
      fn: () => {
        const clips = [
          { categoria_path: ["Casa A", "Cocina"], bin_sony: true },
          { categoria_path: ["Casa A", "Baño"], bin_dron: true },
        ];
        const r = ctx.nombreDelCuartoConMarca("Casa A", "Casa A", clips, ["Casa A"]);
        return { ok: r === "[SONY+DRONE] Casa A", detalle: r };
      },
    },
    {
      nombre: "la marca de un cuarto dentro de una unidad NO mezcla otros cuartos de la misma unidad",
      fn: () => {
        const clips = [
          { categoria_path: ["Casa A", "Cocina"], bin_sony: true },
          { categoria_path: ["Casa A", "Baño"], bin_dron: true },
        ];
        const r = ctx.nombreDelCuartoConMarca("01. Cocina", "Cocina", clips, ["Casa A", "Cocina"]);
        return { ok: r === "01. [SONY] Cocina", detalle: r };
      },
    },
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: FAIL en los 2 casos nuevos — `nombreDelCuartoConMarca` no
acepta un cuarto parámetro de prefijo todavía.

- [ ] **Step 3: Implementar — `marcaCamara.js` completo, generalizando el matcher**

```javascript
// Las marcas de cámara -- "[SONY] ", "[POCKET] ", "[DRONE] "-- en el
// nombre de la carpeta de un cuarto O una unidad en Premiere.
//
// (comentario existente sin cambios hasta la linea 16)

const _MARCAS = [
  { palabra: "SONY", campo: "bin_sony" },
  { palabra: "POCKET", campo: "bin_pocket" },
  { palabra: "DRONE", campo: "bin_dron" },
];

function sinMarcaDeCamara(nombre) {
  const s = String(nombre || "");
  const marca = /^\[(?:SONY|POCKET|DRONE)(?:\+(?:SONY|POCKET|DRONE))*\] /;
  return s.replace(marca, "");
}

// Las marcas que aplican a este PREFIJO de categoria_path -- un cuarto
// (["Cocina"] o ["Casa A", "Cocina"]) o una unidad sola (["Casa A"], que
// agrega la marca de TODOS los cuartos que tiene adentro).
function _marcasDelPrefijo(clipsDelManifest, prefijo) {
  return _MARCAS
    .filter(({ campo }) => _algunClipEmpiezaCon(clipsDelManifest, prefijo, campo))
    .map(({ palabra }) => palabra);
}

function _algunClipEmpiezaCon(clipsDelManifest, prefijo, campo) {
  return (clipsDelManifest || []).some((c) => {
    if (!c || !c.categoria_path || c[campo] !== true) return false;
    if (c.categoria_path.length < prefijo.length) return false;
    return prefijo.every((segmento, indice) => c.categoria_path[indice] === segmento);
  });
}

// Arma el nombre final: numero (si lo hay) + marca(s) (si aplican) + el
// nombre -- EN ESE ORDEN, pegado al nombre nunca antes del numero.
//
// `prefijoDeCategoria` es el categoria_path (crudo, SIN numero ni marca)
// hasta este nivel: `["Cocina"]` para un cuarto sin unidad, `["Casa A",
// "Cocina"]` para un cuarto con unidad, o `["Casa A"]` para marcar la
// UNIDAD misma con la combinacion de todos sus cuartos.
function nombreDelCuartoConMarca(nombreConNumero, nombreSinNumero, clipsDelManifest, prefijoDeCategoria) {
  const prefijo = prefijoDeCategoria || [nombreSinNumero];
  const marcas = _marcasDelPrefijo(clipsDelManifest, prefijo);
  if (!marcas.length) return nombreConNumero;
  const numero = nombreConNumero.slice(
    0, nombreConNumero.length - nombreSinNumero.length);
  return numero + "[" + marcas.join("+") + "] " + nombreSinNumero;
}
```

El cuarto parámetro es opcional con default `[nombreSinNumero]` — el
mismo comportamiento de hoy para cualquier llamador que no lo pase
(retro-compatible con `processManifest.js` hasta que el Task 15 lo
actualice).

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todos los casos en verde, incluidos los once preexistentes de
`autocheck-tests.js` referidos en CLAUDE.md (esos no corren aquí — viven
en el arnés apagado dentro de Premiere — pero revisar que ninguno de los
casos de `marcaCamara.pruebas.js` existentes se haya roto).

- [ ] **Step 5: Commit**

```bash
git add uxp-plugin/js/marcaCamara.js uxp-plugin/pruebas/marcaCamara.pruebas.js
git commit -m "$(cat <<'EOF'
marcaCamara generaliza a un prefijo de categoria_path, no solo categoria_path[0]

nombreDelCuartoConMarca gana un cuarto parametro opcional (prefijo del
categoria_path) para poder marcar tanto un cuarto (con o sin unidad
delante) como una unidad entera con la combinacion de TODOS sus
cuartos -- la carpeta de la unidad tambien lleva la marca de camara,
decision ya tomada en el spec 2026-09-20 §7. Sin el cuarto parametro se
comporta exactamente como antes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### Task 15: `processManifest.js` arma la cadena de bins unidad→cuarto

**Files:**
- Modify: `uxp-plugin/js/processManifest.js`

- [ ] **Step 1: Leer el archivo completo antes de tocarlo**

Ya se leyó hasta la línea 110 durante la investigación de este plan — leer
el resto (110 en adelante) por si hay más referencias a `camino[1]` o
`categoryPath[0]` fuera del rango ya visto.

- [ ] **Step 2: Reescribir el bloque del bucle principal (líneas 43-103)**

No hay un test de node aislado para `processManifest.js` (depende de
`premierepro`, según el runner) — la verificación de este Task es manual,
contra un proyecto de prueba real en Premiere, siguiendo el flujo que ya
usa el resto del plugin (CLAUDE.md: "no confíes en la documentación de
Adobe... imprimir `Object.getOwnPropertyNames`"). Antes de tocar Premiere,
extraer a una función pura y SÍ testeable con node la parte que decide los
índices — eso es lo que se prueba aquí:

```javascript
// uxp-plugin/js/processManifest.js -- agregar antes de processManifest

// Donde vive cada segmento dentro de `camino` (que ya trae CARPETA_DE_CLIPS
// al frente, ver caminoDelClip): sin unidad, camino = [CARPETA_DE_CLIPS,
// cuarto, ...resto]; con unidad, camino = [CARPETA_DE_CLIPS, unidad,
// cuarto, ...resto]. Logica pura, se prueba sin Premiere.
function indicesDelCamino(categoryPath) {
  const hayUnidad = (categoryPath || []).length > 1;
  return {
    indiceUnidad: hayUnidad ? 1 : null,
    indiceCuarto: hayUnidad ? 2 : 1,
  };
}
```

Y dentro del `for (const clipData of manifest.clips)`, reemplazar líneas
57-71:

```javascript
      const camino = caminoDelClip(categoryPath, ordenDeLaGuia);
      const { indiceUnidad, indiceCuarto } = indicesDelCamino(categoryPath);
      const nombreCuartoSinNumero = categoryPath[categoryPath.length - 1];
      camino[indiceCuarto] = nombreDelCuartoConMarca(
        camino[indiceCuarto], nombreCuartoSinNumero, manifest.clips, categoryPath
      );

      let carpetaBase = carpetaDeClips;
      if (indiceUnidad !== null) {
        const nombreUnidad = nombreDelCuartoConMarca(
          camino[indiceUnidad], camino[indiceUnidad], manifest.clips, [categoryPath[0]]
        );
        carpetaBase = await resolveBinChain(project, carpetaDeClips, [nombreUnidad]);
      }
      const carpetaDelCuartoObj = await resolverCuarto(
        project, carpetaBase, camino[indiceCuarto]);
      const targetFolder = camino.length > indiceCuarto + 1
        ? await resolveBinChain(project, carpetaDelCuartoObj, camino.slice(indiceCuarto + 1))
        : carpetaDelCuartoObj;
      const clipItem = await importOrReuseClip(project, targetFolder, clipData.ruta, indiceDeClips);
```

Nota: la carpeta de unidad usa `resolveBinChain` (crea/reusa por nombre
exacto), NO `resolverCuarto` — `resolverCuarto` existe para el caso de
renumerar una carpeta ya numerada cuando la guía cambia de orden entre
pasadas (spec 2026-09-15), y la unidad nunca lleva número (Task 13), así
que ese caso no le aplica.

- [ ] **Step 3: Prueba de la función pura extraída**

```javascript
// agregar a uxp-plugin/pruebas/estructura.pruebas.js (o un archivo nuevo
// processManifest.pruebas.js si el proyecto prefiere separar por
// modulo -- seguir la convencion existente)
    {
      nombre: "indicesDelCamino sin unidad: cuarto en 1 (tras CARPETA_DE_CLIPS)",
      fn: () => {
        const r = ctx.indicesDelCamino(["Cocina"]);
        return { ok: r.indiceUnidad === null && r.indiceCuarto === 1, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "indicesDelCamino con unidad: unidad en 1, cuarto en 2",
      fn: () => {
        const r = ctx.indicesDelCamino(["Casa A", "Cocina"]);
        return { ok: r.indiceUnidad === 1 && r.indiceCuarto === 2, detalle: JSON.stringify(r) };
      },
    },
```

Agregar `js/processManifest.js` a la lista `ARCHIVOS` de `correr.js` SOLO
si no hace `require("premierepro")` a nivel de módulo (la función
`processManifest` en sí lo hace adentro, en tiempo de llamada — revisar
si eso basta para que `vm` pueda cargarlo sin reventar, igual que ya pasa
con otros archivos de la lista que también usan `require("premierepro")`
dentro de sus funciones).

Run: `node uxp-plugin/pruebas/correr.js`
Expected: los 2 casos nuevos en verde.

- [ ] **Step 4: Verificación manual contra Premiere real**

Siguiendo CLAUDE.md ("no confíes en la documentación de Adobe"): importar
un manifest de prueba con clips en 2 unidades y en el bloque "sin unidad",
y confirmar a ojo en Premiere que:
  - se crean las carpetas `Casa A` y `Casa B` sin número, dentro de
    «02. Clip»;
  - dentro de cada una, los cuartos SÍ llevan número si hay guía;
  - un clip sin unidad cae directo bajo «02. Clip», como hoy;
  - la marca de cámara aparece tanto en la carpeta de unidad (combinada)
    como en la de cuarto (la suya propia).

- [ ] **Step 5: Commit**

```bash
git add uxp-plugin/js/processManifest.js uxp-plugin/pruebas/estructura.pruebas.js uxp-plugin/pruebas/correr.js
git commit -m "$(cat <<'EOF'
processManifest arma la cadena de bins unidad -> cuarto en Premiere

indicesDelCamino (logica pura, con prueba de node) decide donde vive
cada segmento segun si categoryPath trae unidad o no. La carpeta de
unidad se resuelve con resolveBinChain (crea o reusa por nombre exacto)
y no con resolverCuarto, porque nunca lleva numero (Task 13) y el caso
que resolverCuarto resuelve -- renumerar entre pasadas -- no le aplica.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review (hecho al escribir este plan)

**Cobertura del spec:**
- §1 (qué es una unidad, opcional) → Tasks 2, 5 (default `""`, cero
  fricción sin crear unidades).
- §2 (modelo de datos, `RoomSelection` por unidad) → Task 5.
- §3 (paleta de unidades, no cierra al elegir) → Tasks 6, 7, 8.
- §4 (reasignar en lote, camino de migración) → Task 9 (cuarto ya
  prefija unidad activa) + Task 10 (`_asignar_unidad` explícito).
- Adenda 2026-09-20 (bloque "Sin unidad" mientras dura la migración) →
  Tasks 11, 12.
- §5 (rail y hoja, orden unidad→cuarto) → Tasks 11, 12.
- §6 (color, swatch cuadrado distinto de franja) → Tasks 6, 7.
- §7 (plugin UXP, dos niveles) → Tasks 13, 14, 15.
- §8 (fuera de alcance: nota, guía por unidad, migración automática de
  sufijo, menú contextual) → ningún Task los toca; Task 13 documenta
  explícitamente por qué la unidad no lleva número (consecuencia directa
  de dejar la guía fuera de alcance).

**Placeholders encontrados y su estado:** el Step 5 del Task 8
(`_colocar_paleta_de_unidades`) y el Step 3 del Task 11 (banda visual de
la hoja) dependen de código que esta investigación no pudo leer completo
(`_colocar_paleta`, `_GroupBlock`/encabezado de bin) — quedaron marcados
explícitamente como "leer antes de escribir" en vez de inventar el
código. No son placeholders de pereza: son los dos puntos donde
completar el plan sin ver el código real habría significado adivinar.
Quien ejecute esos dos pasos debe leer el código señalado primero.

**Consistencia de tipos:** `_cuarto_de`/`_unidad_de` (Task 1) se usan
igual en Tasks 5, 9, 10, 11, 12. `room_selections`/`unit_selection`/
`_unidad_activa` (Task 5) son los mismos nombres en Tasks 6, 8, 9, 10,
11, 12. `theme.unit_color`/`UNIT_PALETTE` (Task 7) son los mismos en
Tasks 6, 10, 12. El orden de ejecución **Task 7 antes que Task 6** está
marcado explícitamente por la dependencia inversa en el documento.

---

## Orden de ejecución recomendado

Fase 0 (Task 1) → Fase 1 (Tasks 2, 3, 4, 5) → Fase 3 (Task 7) → Fase 2
(Task 6, 8) → Fase 5 (Tasks 9, 10) → Fase 6 (Tasks 11, 12) → Fase 7
(Tasks 13, 14, 15).

Cada fase deja la app en un estado funcional y comprobable — se puede
parar entre fases y seguir usando Clipify con normalidad (sin unidades
hasta que exista la UI para crearlas en la Fase 2, y sin verlas en
Premiere hasta la Fase 7).
