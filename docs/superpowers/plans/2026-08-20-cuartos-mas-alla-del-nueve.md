# Los cuartos más allá del nueve — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `S` ponga el último cuarto que usaste, y que a los cuartos del 10 en adelante se llegue sin pelear.

**Architecture:** La ventana se acuerda del último cuarto asignado en `_ultimo_cuarto_usado`, y `_cuarto_del_clip_anterior` pasa a ser el respaldo y no la regla. El buscador cambia su lista fija de seis filas por una lista que crece, dentro de un área con scroll y tope de altura. La fila del rail deja de tratar `⏎` como renombrar y emite una señal nueva que la ventana convierte en asignación.

**Tech Stack:** Python 3.13, PySide6, pytest + pytest-qt. Suite completa: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

**Spec:** `docs/superpowers/specs/2026-08-20-cuartos-mas-alla-del-nueve-design.md`

---

## Estructura de archivos

| Archivo | Qué cambia |
|---|---|
| `src/clasificador_video/ui/main_window.py` | `_ultimo_cuarto_usado`; `S` lo usa; sigue renombrados y borrados; asigna desde el rail |
| `src/clasificador_video/ui/room_palette.py` | Filas dinámicas + scroll; `↑`/`↓` arrastran el scroll |
| `src/clasificador_video/ui/room_rail.py` | `⏎` en la fila asigna; el hueco sin número muestra `⏎` |
| `src/clasificador_video/ui/theme.py` | Estilo del `⏎` en el hueco |
| `tests/ui/test_main_window.py` | Tasks 1, 4 |
| `tests/ui/test_room_palette.py` | Task 2 |
| `tests/ui/test_room_rail.py` | Tasks 3, 5 |

**Nombres que se usan en todo el plan:**

- `MainWindow._ultimo_cuarto_usado: str | None`
- `MainWindow._cuarto_para_la_tecla_s() -> str | None`
- `RoomRail.room_assign_requested = Signal(str)` (y `_FilaCuarto.assign_requested`)
- `RoomPalette._asegurar_filas(cuantas: int) -> None`

---

### Task 1: `S` pone el último cuarto que usaste

**Files:** `src/clasificador_video/ui/main_window.py`, `tests/ui/test_main_window.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

```python
def test_la_s_pone_el_ultimo_cuarto_que_usaste(qtbot):
    """El caso que Bruno reprodujo el 2026-08-20: le pones «Alberca» al clip
    2, te mueves al clip 7, aprietas `S`, y te ponía «Cocina» -- lo que tenía
    el clip 6 de una pasada anterior. `S` copiaba el cuarto del clip de al
    lado hacia atrás, no el último que usaste."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina", "Alberca"], clips=8)
    window.select_clip(5)
    window.handle_key_press("2")              # el clip 6 queda en Cocina
    window.select_clip(1)
    window.handle_key_press("3")              # y ahora uso Alberca

    window.select_clip(6)
    window.handle_key_press("s")

    assert window.clips[6].categoria_path == ["Alberca"]


def test_la_s_sin_haber_usado_ninguno_cae_en_el_clip_anterior(qtbot):
    """Recién abres el proyecto: `S` tiene que servir desde el primer teclazo
    y no quedarse muerta esperando a que uses uno."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.clips[0].categoria_path = ["Cocina"]

    window.select_clip(1)
    window.handle_key_press("s")

    assert window.clips[1].categoria_path == ["Cocina"]


def test_deshacer_no_mueve_lo_que_la_s_va_a_poner(qtbot):
    """`⌘Z` revierte el dato, no tu intención. Si deshacer lo moviera,
    cambiaría en silencio lo que la siguiente tecla va a hacer."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)
    window.handle_key_press("2")              # Cocina
    window.undo()

    window.select_clip(2)
    window.handle_key_press("s")

    assert window.clips[2].categoria_path == ["Cocina"]


def test_renombrar_el_cuarto_que_la_s_tiene_en_la_mano_lo_sigue(qtbot):
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)
    window.handle_key_press("2")              # Cocina

    window._on_room_renamed("Cocina", "Cocina chica")
    window.select_clip(2)
    window.handle_key_press("s")

    assert window.clips[2].categoria_path == ["Cocina chica"]


def test_borrar_el_cuarto_que_la_s_tiene_en_la_mano_lo_suelta(qtbot):
    """Y `S` vuelve al respaldo, en vez de poner un cuarto que ya no existe
    -- que quedaría clasificado en un cuarto fantasma, como ya pasó con el
    historial."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)
    window.handle_key_press("2")              # Cocina
    window._on_room_removed("Cocina")

    assert window._ultimo_cuarto_usado is None
```

Y el helper, junto a los demás de ese archivo:

```python
def _window_con_cuartos(qtbot, cuartos, clips=4):
    seleccion = RoomSelection()
    for cuarto in cuartos:
        seleccion.add(cuarto)
    window = MainWindow(project_name="Casa", room_selection=seleccion,
                        video_factory=FakeMpv)
    qtbot.addWidget(window)
    window.resize(1400, 900)
    window.load_clips([
        Clip(orden=i + 1, ruta=Path(f"/tmp/C{i:04d}.MP4"), categoria_path=[], fps=30.0)
        for i in range(clips)
    ])
    return window
```

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -q -k "la_s_ o deshacer_no_mueve or tiene_en_la_mano"
```

Esperado: FAIL en la primera con `['Cocina'] != ['Alberca']`, y `AttributeError` en la última.

- [ ] **Step 3: La ventana se acuerda**

En `__init__`, junto al resto del estado de clasificación:

```python
        # El último cuarto que se asignó EN ESTA SESIÓN, que es lo que pone
        # `S`. No se guarda en el proyecto: es el hilo de lo que estás
        # haciendo ahorita, y al reabrir no hay hilo que retomar.
        self._ultimo_cuarto_usado: str | None = None
```

En `_asignar_cuarto`, antes de aplicar:

```python
    def _asignar_cuarto(self, room_path: list[str]) -> None:
        """Un solo camino para asignar cuarto, lo pida un digito o la `S`.

        Con dos caminos, `S` seria una asignacion de segunda: no registraria
        en el historial, o no avanzaria, y eso no se ve hasta usarla.
        """
        # Aqui y no en cada tecla: por esta funcion pasan TODAS las formas de
        # asignar --el digito, la `S`, el buscador, el rail, el pincel y el
        # lote-- y lo que `S` tiene que recordar es «el ultimo que usaste»,
        # no por donde entro.
        if room_path:
            self._ultimo_cuarto_usado = room_path[0]
        self._apply_categoria_to_targets(room_path)
```

Y el respaldo:

```python
    def _cuarto_para_la_tecla_s(self) -> str | None:
        """Lo que pone `S`: el último cuarto que usaste en esta sesión.

        Antes era el cuarto del clip de al lado hacia atrás, y eso se separa
        de lo que uno espera en cuanto te saltas clips o hay material
        clasificado de una pasada anterior: te daba un cuarto viejo. Bruno lo
        describió como «`S` es el cuarto penúltimo en lugar del último».

        El respaldo se queda para el primer teclazo de la sesión, donde
        todavía no hay «último usado» y sin él la tecla no haría nada.
        """
        if self._ultimo_cuarto_usado in self.room_selection.active_rooms():
            return self._ultimo_cuarto_usado
        return self._cuarto_del_clip_anterior()
```

En `handle_key_press`, la rama de `s` pasa a llamar a `_cuarto_para_la_tecla_s()`. Lo mismo el lugar donde el rail pinta la pista de «mismo cuarto» (la llamada a `set_same_room`), para que lo que se ve y lo que hace la tecla no puedan contradecirse.

- [ ] **Step 4: Que siga los renombrados y los borrados**

En `_on_room_renamed`, junto a `self.history.renombrar_cuarto(...)`:

```python
        if self._ultimo_cuarto_usado == viejo:
            self._ultimo_cuarto_usado = nuevo
```

En `_on_room_removed`, después de quitarlo de la selección:

```python
        if self._ultimo_cuarto_usado == nombre:
            # se suelta en vez de quedarse apuntando a un cuarto que ya no
            # existe: `S` pondria un cuarto fantasma, que cuenta como
            # clasificado y no aparece en ningun renglon del rail
            self._ultimo_cuarto_usado = None
```

- [ ] **Step 5: Corre la suite completa y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "La tecla S pone el ultimo cuarto que usaste

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: El buscador muestra todos los cuartos

**Files:** `src/clasificador_video/ui/room_palette.py`, `tests/ui/test_room_palette.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

```python
def test_el_buscador_muestra_todos_los_cuartos(qtbot):
    """Con 13 cuartos mostraba 6, así que siete no aparecían y parecía que no
    estaban -- justo los cuartos por los que este buscador existe."""
    paleta = _paleta(qtbot)
    cuartos = [f"Cuarto {n}" for n in range(1, 14)]

    paleta.abrir(cuartos, {}, 1)

    assert paleta.opciones_visibles() == cuartos


def test_el_buscador_no_crece_sin_limite(qtbot):
    """El tope de altura se queda: la paleta no puede tapar media pantalla.
    Deja de ser un tope de cuántos cuartos EXISTEN y pasa a ser uno de
    cuántos caben a la vez."""
    paleta = _paleta(qtbot)

    paleta.abrir([f"Cuarto {n}" for n in range(1, 40)], {}, 1)

    assert paleta.height() <= ALTO_MAXIMO


def test_bajar_hasta_el_ultimo_cuarto_lo_deja_a_la_vista(qtbot):
    """Una fila marcada que no se ve es lo mismo que no tenerla."""
    paleta = _paleta(qtbot)
    cuartos = [f"Cuarto {n}" for n in range(1, 14)]
    paleta.abrir(cuartos, {}, 1)

    for _ in range(len(cuartos)):
        paleta.mover(1)

    assert paleta.opcion_activa() == "Cuarto 13"
    fila = paleta.filas_visibles()[-1]
    visible = paleta._scroll.viewport().rect()
    punto = fila.mapTo(paleta._scroll.viewport(), fila.rect().topLeft())
    assert visible.contains(punto)
```

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_room_palette.py -q -k "todos_los_cuartos or sin_limite or a_la_vista"
```

Esperado: FAIL — solo devuelve 6.

- [ ] **Step 3: Filas que crecen, dentro de un scroll**

En `room_palette.py`, `MAX_OPCIONES` deja de limitar cuántas hay y pasa a decir cuántas caben:

```python
# Cuantas filas CABEN a la vez. No es un tope de cuantos cuartos existen --
# eso era el bug: con 13 cuartos se veian 6 y parecia que no estaban.
FILAS_VISIBLES = 6
ALTO_MAXIMO = FILAS_VISIBLES * ALTO_DE_FILA
```

La lista fija se cambia por una que crece, dentro de un `QScrollArea` sin
borde y con la barra horizontal apagada:

```python
    def _asegurar_filas(self, cuantas: int) -> None:
        """Crea las filas que falten. Se reusan entre aperturas: destruirlas y
        rehacerlas en cada tecla haria parpadear la paleta."""
        while len(self.opciones) < cuantas:
            fila = _Opcion(self._contenido)
            self._layout_de_opciones.addWidget(fila)
            self.opciones.append(fila)
```

`_refrescar` llama a `_asegurar_filas(len(coincidencias))` antes de repartir, y `_coincidencias` deja de recortar con `[:MAX_OPCIONES]`.

`mover` arrastra el scroll a la fila marcada:

```python
    def mover(self, delta: int) -> None:
        visibles = self.opciones_visibles()
        if not visibles:
            return
        self._activa = max(0, min(self._activa + delta, len(visibles) - 1))
        self._marcar_activa()
        filas = self.filas_visibles()
        if filas:
            # una fila marcada que no se ve es lo mismo que no tenerla
            self._scroll.ensureWidgetVisible(filas[min(self._activa, len(filas) - 1)])
```

- [ ] **Step 4: Corre la suite completa y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
git add src/clasificador_video/ui/room_palette.py tests/ui/test_room_palette.py
git commit -m "El buscador de cuartos los muestra todos, no los primeros seis

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: En el rail, `⏎` asigna

**Files:** `src/clasificador_video/ui/room_rail.py`, `tests/ui/test_room_rail.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

```python
def test_enter_en_una_fila_del_rail_pide_asignar(qtbot):
    """Lo que Bruno encontró: `⏎` con una fila enfocada abría el renombrado,
    así que «poner enter no me deja seleccionar cuartos, solo hacer nuevos».
    Lo que uno quiere hacer con un cuarto mientras clasifica es ponérselo a
    un clip; renombrar es mantenimiento."""
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {"Cocina": 3, "Sala": 2})
    pedidos = []
    rail.room_assign_requested.connect(pedidos.append)

    qtbot.keyClick(rail.rows[0], Qt.Key.Key_Return)

    assert pedidos == ["Cocina"]


def test_enter_en_el_rail_ya_no_abre_el_renombrado(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {"Cocina": 3})

    qtbot.keyClick(rail.rows[0], Qt.Key.Key_Return)

    assert not rail.rows[0].esta_renombrando()


def test_f2_sigue_renombrando(qtbot):
    """Renombrar no se pierde: se cambia de tecla."""
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {"Cocina": 3})

    qtbot.keyClick(rail.rows[0], Qt.Key.Key_F2)

    assert rail.rows[0].esta_renombrando()
```

Si `_FilaCuarto` no tiene todavía una forma de preguntar si está en modo edición, añádele:

```python
    def esta_renombrando(self) -> bool:
        """Si la fila está con el campo de texto abierto. Existe para las
        pruebas: preguntarle a Qt por el widget concreto las ataría a cómo
        está construida la fila por dentro."""
        return self._editor is not None and self._editor.isVisible()
```

y ajusta el nombre del atributo al que de verdad guarda el editor (búscalo con `grep -n "_pedir_nombre" -A 15 src/clasificador_video/ui/room_rail.py`).

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_room_rail.py -q -k "asignar or renombrado or f2_sigue"
```

Esperado: FAIL con `AttributeError: 'RoomRail' object has no attribute 'room_assign_requested'`.

- [ ] **Step 3: La señal nueva y el cambio de tecla**

En `_FilaCuarto`, junto a las demás señales:

```python
    assign_requested = Signal(str)         # nombre del cuarto
```

y en su `keyPressEvent`, la rama de `⏎` pasa de renombrar a asignar, y `F2` toma el renombrado:

```python
        if tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # asignar, no renombrar. El rail es una lista de cuartos junto al
            # video, y lo que uno quiere hacer con un cuarto mientras
            # clasifica es ponerselo a un clip. Renombrar es mantenimiento, y
            # el mantenimiento no se queda con la tecla mas obvia: vive en
            # `F2`, en el doble clic y en el menu contextual.
            self.assign_requested.emit(self.nombre)
            event.accept()
            return
        if tecla == Qt.Key.Key_F2:
            self._pedir_nombre()
            event.accept()
            return
```

En `RoomRail`, la señal que sube y la conexión, junto a `fila.rename_requested.connect(...)`:

```python
    room_assign_requested = Signal(str)
```
```python
            fila.assign_requested.connect(self.room_assign_requested.emit)
```

- [ ] **Step 4: Corre la suite completa y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
git add src/clasificador_video/ui/room_rail.py tests/ui/test_room_rail.py
git commit -m "En el rail, Enter asigna el cuarto; renombrar se va a F2

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: La ventana asigna lo que el rail pide

**Files:** `src/clasificador_video/ui/main_window.py`, `tests/ui/test_main_window.py`

- [ ] **Step 1: Escribe la prueba que falla**

```python
def test_el_rail_asigna_al_clip_actual(qtbot):
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(2)

    window.room_rail.room_assign_requested.emit("Cocina")

    assert window.clips[2].categoria_path == ["Cocina"]


def test_asignar_desde_el_rail_cuenta_para_la_s(qtbot):
    """Pasa por el mismo camino que todo lo demás: lo que `S` recuerda es «el
    último que usaste», no por dónde entró."""
    window = _window_con_cuartos(qtbot, ["Sala", "Cocina"], clips=4)
    window.select_clip(0)

    window.room_rail.room_assign_requested.emit("Cocina")

    assert window._ultimo_cuarto_usado == "Cocina"
```

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -q -k "rail_asigna or cuenta_para_la_s"
```

- [ ] **Step 3: Conectarla**

Donde se conectan las demás señales del rail:

```python
        self.room_rail.room_assign_requested.connect(
            lambda nombre: self._asignar_cuarto([nombre])
        )
```

Por `_asignar_cuarto` y no por un camino propio: es el único lugar que registra en el historial, avanza en la cola y anota el último cuarto usado. Un segundo camino sería una asignación de segunda, y eso no se ve hasta usarla.

- [ ] **Step 4: Corre la suite completa y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "El rail asigna por el mismo camino que el teclado

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: El rail dice `⏎` donde no hay número

**Files:** `src/clasificador_video/ui/room_rail.py`, `src/clasificador_video/ui/theme.py`, `tests/ui/test_room_rail.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

```python
def test_el_decimo_cuarto_muestra_enter_en_vez_de_un_hueco(qtbot):
    """El cuadrito vacío decía «aquí no hay tecla» pero no decía a dónde ir.
    Son justamente los cuartos por los que el buscador existe."""
    rail = _rail(qtbot)
    rail.set_rooms([f"Cuarto {n}" for n in range(1, 12)], {})

    assert rail.rows[9].key_label.text() == "⏎"


def test_los_primeros_nueve_siguen_con_su_numero(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms([f"Cuarto {n}" for n in range(1, 12)], {})

    assert rail.rows[8].key_label.text() == "9"
```

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_room_rail.py -q -k "decimo_cuarto or primeros_nueve"
```

- [ ] **Step 3: Poner el glifo**

Donde hoy se calcula `numero = indice + 1 if indice < MAX_TECLAS else None`, la fila pasa a recibir el texto ya resuelto:

```python
            # del decimo en adelante no hay atajo numerico, y el hueco vacio
            # decia «aqui no hay tecla» sin decir a donde ir. `⏎` abre el
            # buscador, que es exactamente lo que hace falta saber.
            tecla = str(indice + 1) if indice < MAX_TECLAS else "⏎"
```

Ajusta `_FilaCuarto.poner` (o como se llame quien recibe el número) para aceptar el texto en vez del entero, y marca la fila con una propiedad para que el estilo lo distinga:

```python
        self.key_label.setProperty("sinAtajo", tecla == "⏎")
```

- [ ] **Step 4: El estilo**

En `theme.py`, junto a las reglas de la tecla del rail:

```python
    /* el `⏎` de los cuartos sin atajo numerico: mas apagado que un numero,
       porque no es una tecla directa sino el camino al buscador */
    QLabel#roomKey[sinAtajo="true"] {{
        color: {TEXT_3};
    }}
```

- [ ] **Step 5: Corre la suite completa y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
git add src/clasificador_video/ui/room_rail.py src/clasificador_video/ui/theme.py tests/ui/test_room_rail.py
git commit -m "El rail dice Enter donde no hay numero

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Barrido final — el pixel y la documentación

**Files:** `README.md`, `docs/superpowers/CONTEXTO-Y-METAS.md`

- [ ] **Step 1: Comprobación visual**

Arma en el scratchpad (NO en el repo) una ventana con 13 cuartos, abre el buscador con `_on_enter()`, y guarda `window.grab()` a PNG. Ábrelo con la herramienta de lectura de archivos y confirma tres cosas: se ven más de seis cuartos, el rail muestra `⏎` del décimo en adelante, y el `⏎` se lee más apagado que los números.

- [ ] **Step 2: El README**

En la tabla de teclas, añade los renglones que faltaban:

```markdown
| `⏎` | busca un cuarto por nombre y lo asigna — la vía para los que pasan del noveno |
| `F2` | renombra el cuarto seleccionado en el rail |
```

Y corrige el renglón de `S`, que hoy dice «repite el cuarto del clip anterior»:

```markdown
| `S` | repite **el último cuarto que usaste** y avanza |
```

Añade después de la tabla:

```markdown
**Más de nueve cuartos.** Los atajos `1`…`9` llegan al noveno. Del décimo en
adelante el rail muestra `⏎` en lugar del número: aprieta Enter, escribe las
primeras letras y dale Enter otra vez. También puedes elegir el cuarto en el
rail y apretar Enter.
```

- [ ] **Step 3: CONTEXTO-Y-METAS**

Añade a lo cerrado un punto con las dos cosas, y con el porqué: `S` copiaba el cuarto del clip de al lado y eso se separa de «el último que usaste» en cuanto te saltas clips; y el buscador existía desde siempre pero mostraba seis de trece y `⏎` en el rail renombraba, así que parecía que no se podía.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/CONTEXTO-Y-METAS.md
git commit -m "Los cuartos mas alla del nueve, en la documentacion

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
