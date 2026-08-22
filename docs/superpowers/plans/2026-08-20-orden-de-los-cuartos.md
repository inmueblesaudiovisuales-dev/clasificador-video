# El orden de los cuartos — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la hoja acomode los cuartos en el orden que Bruno eligió, y que ese orden se pueda cambiar arrastrando.

**Architecture:** La hoja recibe el orden de cuartos igual que ya recibe el de bins (`set_bin_order`), y `_orden_de_grupo` deja de ordenar por nombre. El rail gana arrastre entre filas, que termina en una señal con el nombre y la posición destino; `RoomSelection` gana el mover-a-posición que hoy solo existe como `move(delta)`.

**Tech Stack:** Python 3.13, PySide6, pytest + pytest-qt. Suite completa: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

**Spec:** `docs/superpowers/specs/2026-08-20-orden-de-los-cuartos-design.md`

---

## Estructura de archivos

| Archivo | Qué cambia |
|---|---|
| `src/clasificador_video/rooms.py` | `mover_a(room, posicion)` |
| `src/clasificador_video/ui/clip_sheet.py` | `set_room_order`; `_orden_de_grupo` deja de usar el nombre |
| `src/clasificador_video/ui/room_rail.py` | Arrastre entre filas + línea de destino |
| `src/clasificador_video/ui/main_window.py` | Le pasa el orden a la hoja; atiende el arrastre |
| `src/clasificador_video/ui/theme.py` | La línea que marca dónde va a caer |

**Nombres que se usan en todo el plan:**

- `RoomSelection.mover_a(room: str, posicion: int) -> None`
- `ClipSheet.set_room_order(nombres: list[str]) -> None`
- `RoomRail.room_reordered = Signal(str, int)` (nombre, posición destino)

---

### Task 1: `RoomSelection` sabe mover a una posición

**Files:** `src/clasificador_video/rooms.py`, `tests/test_rooms.py`

- [x] **Step 1: Escribe las pruebas que fallan**

```python
def test_mover_a_lleva_el_cuarto_a_esa_posicion():
    """Arrastrar es mover A UN LUGAR, no `move(delta)` repetido: con 13
    cuartos, subir el último hasta arriba serían doce llamadas."""
    seleccion = RoomSelection()
    for cuarto in ["Fachada", "Sala", "Comedor", "Alberca"]:
        seleccion.add(cuarto)

    seleccion.mover_a("Alberca", 0)

    assert seleccion.active_rooms() == ["Alberca", "Fachada", "Sala", "Comedor"]


def test_mover_a_al_final():
    seleccion = RoomSelection()
    for cuarto in ["Fachada", "Sala", "Comedor"]:
        seleccion.add(cuarto)

    seleccion.mover_a("Fachada", 2)

    assert seleccion.active_rooms() == ["Sala", "Comedor", "Fachada"]


def test_mover_a_donde_ya_estaba_no_cambia_nada():
    seleccion = RoomSelection()
    for cuarto in ["Fachada", "Sala"]:
        seleccion.add(cuarto)

    seleccion.mover_a("Fachada", 0)

    assert seleccion.active_rooms() == ["Fachada", "Sala"]


def test_mover_a_recorta_la_posicion_en_vez_de_reventar():
    """La posición viene de un gesto del mouse: soltar debajo del último
    puede dar un número más grande que la lista."""
    seleccion = RoomSelection()
    for cuarto in ["Fachada", "Sala"]:
        seleccion.add(cuarto)

    seleccion.mover_a("Fachada", 99)
    seleccion.mover_a("Sala", -3)

    assert seleccion.active_rooms() == ["Sala", "Fachada"]


def test_mover_a_un_cuarto_que_no_existe_no_hace_nada():
    seleccion = RoomSelection()
    seleccion.add("Fachada")

    seleccion.mover_a("Alberca", 0)

    assert seleccion.active_rooms() == ["Fachada"]
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_rooms.py -q -k mover_a
```

Esperado: `AttributeError: 'RoomSelection' object has no attribute 'mover_a'`.

- [x] **Step 3: Escribe el método**

En `rooms.py`, junto a `move`:

```python
    def mover_a(self, room: str, posicion: int) -> None:
        """Lo lleva a esa posición. El gemelo de `move` para el arrastre.

        `move(delta)` sirve para «Subir» y «Bajar», que son un escalón; el
        arrastre es «ponlo AQUÍ», y con 13 cuartos llevar el último hasta
        arriba serían doce llamadas.

        La posición se RECORTA en vez de reventar: viene de un gesto del
        mouse, y soltar debajo del último da un número más grande que la
        lista. Un cuarto que no está se ignora, con el mismo criterio que el
        resto del módulo: es una entrada inválida, no un error del programa.
        """
        if room not in self._rooms:
            return
        posicion = max(0, min(posicion, len(self._rooms) - 1))
        self._rooms.remove(room)
        self._rooms.insert(posicion, room)
```

Comprueba cómo se llama la lista interna (`grep -n "self\._" src/clasificador_video/rooms.py`) y ajusta el nombre.

- [x] **Step 4: Corre las pruebas y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_rooms.py -q
git add src/clasificador_video/rooms.py tests/test_rooms.py
git commit -m "RoomSelection sabe mover un cuarto a una posicion

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: La hoja sigue el orden del rail

**Files:** `src/clasificador_video/ui/clip_sheet.py`, `tests/ui/test_clip_sheet.py`

- [x] **Step 1: Escribe las pruebas que fallan**

```python
def test_la_hoja_acomoda_los_cuartos_en_el_orden_del_rail(qtbot):
    """El bug que Bruno describió como «no hay una forma de ordenar los
    cuartos». La hoja los ordenaba por ABECEDARIO, así que subirlos en el
    rail no movía un pixel aquí -- y el número de la tecla sale del rail, así
    que su cuarto `1` podía aparecer hasta abajo."""
    rail = ["Fachada", "Sala", "Comedor", "Alberca"]
    sheet = _sheet(qtbot, [_clip(i + 1, c) for i, c in enumerate(rail)])
    sheet.set_room_order(rail)

    assert _cuartos_en_orden(sheet) == rail


def test_sin_clasificar_sigue_arriba_de_todo(qtbot):
    """Es la cola de trabajo: esa regla no la toca el orden nuevo."""
    rail = ["Fachada", "Sala"]
    clips = [_clip(1, "Sala"), _clip(2, None), _clip(3, "Fachada")]
    sheet = _sheet(qtbot, clips)
    sheet.set_room_order(rail)

    assert _cuartos_en_orden(sheet)[0] == SIN_CLASIFICAR


def test_un_cuarto_que_no_esta_en_el_rail_cae_al_final(qtbot):
    """Defensivo: no rompe el orden ni desaparece."""
    sheet = _sheet(qtbot, [_clip(1, "Zulu"), _clip(2, "Sala")])
    sheet.set_room_order(["Sala"])

    assert _cuartos_en_orden(sheet) == ["Sala", "Zulu"]


def test_reordenar_no_recarga_las_portadas(qtbot):
    """Reagrupar re-coloca las tarjetas, no las recrea: recrearlas tira las
    miniaturas ya cargadas, que es lo caro."""
    rail = ["Fachada", "Sala"]
    sheet = _sheet(qtbot, [_clip(1, "Sala"), _clip(2, "Fachada")])
    sheet.set_room_order(rail)
    antes = list(sheet.item_widgets)

    sheet.set_room_order(["Sala", "Fachada"])

    assert list(sheet.item_widgets) == antes
```

Y el helper, junto a los demás:

```python
def _cuartos_en_orden(sheet) -> list[str]:
    """Los cuartos tal como se DIBUJAN, sin repetir."""
    vistos = []
    for i in sheet.indices_en_orden_visual():
        cuarto = sheet.item_widgets[i].clip.room_label
        if cuarto not in vistos:
            vistos.append(cuarto)
    return vistos
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet.py -q -k "orden_del_rail or arriba_de_todo or cae_al_final or no_recarga"
```

Esperado: FAIL con el orden alfabético.

- [x] **Step 3: La hoja recibe el orden**

En `ClipSheet.__init__`, junto a `self._bin_order`:

```python
        # El orden de los cuartos, tal como está en el rail. La hoja no lo
        # adivina --se lo dicen, igual que el de los bins-- porque quien
        # decide es Bruno y quien lo guarda es `RoomSelection`.
        self._room_order: list[str] = []
```

y el método, junto a `set_bin_order`:

```python
    def set_room_order(self, nombres: list[str]) -> None:
        """El orden de los cuartos dentro de cada bin.

        Sale temprano si no cambió, por lo mismo que `set_bin_order`:
        `_refresh_sheet` llama aquí en cada flecha, cada cuarto y cada pick.
        """
        if list(nombres) == self._room_order:
            return
        self._room_order = list(nombres)
        self._firma = None
        self._regroup()
```

Y `_orden_de_grupo` deja de ordenar por el nombre:

```python
    def _orden_de_grupo(self, clave: tuple[str, str]) -> tuple:
        """Primero el bin --por su posicion de importacion-- y adentro los
        cuartos EN EL ORDEN DEL RAIL, con «Sin clasificar» arriba porque es
        la cola de trabajo.

        Antes esto ordenaba por el NOMBRE del cuarto, o sea por abecedario, y
        eso contradecia al rail: subir un cuarto alla no movia un pixel aqui,
        y el numero de la tecla --que sale del rail-- podia quedar hasta
        abajo. Bruno lo vivio como «no hay una forma de ordenar los cuartos».
        """
        bin_nombre, cuarto = clave
        if bin_nombre == SIN_BIN:
            pos = -1
        elif bin_nombre in self._bin_order:
            pos = self._bin_order.index(bin_nombre)
        else:
            pos = len(self._bin_order)
        # un cuarto que no esta en el rail cae al final, en vez de romper el
        # orden o desaparecer
        pos_cuarto = (self._room_order.index(cuarto)
                      if cuarto in self._room_order else len(self._room_order))
        return (pos, bin_nombre, cuarto != SIN_CLASIFICAR, pos_cuarto, cuarto)
```

El `cuarto` al final es el desempate: dos cuartos fuera del rail comparten `pos_cuarto`, y sin él su orden dependería de cómo llegaron.

- [x] **Step 4: La ventana se lo pasa**

En `main_window.py`, donde `_refresh_sheet` ya llama a `set_bin_order`, añade al lado:

```python
        self.clip_sheet.set_room_order(self.room_selection.active_rooms())
```

- [x] **Step 5: Corre la suite completa y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
git add src/clasificador_video/ui/clip_sheet.py src/clasificador_video/ui/main_window.py tests/ui/test_clip_sheet.py
git commit -m "La hoja acomoda los cuartos en el orden del rail, no por abecedario

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Los cuartos se arrastran en el rail

**Files:** `src/clasificador_video/ui/room_rail.py`, `src/clasificador_video/ui/theme.py`, `tests/ui/test_room_rail.py`

- [x] **Step 1: Escribe las pruebas que fallan**

Las pruebas van sobre la DECISIÓN, no sobre el gesto de mouse: simular un
drag-and-drop real bajo `offscreen` es frágil, y lo que importa es a qué
posición se traduce cada punto de caída.

```python
def test_soltar_arriba_del_primero_lo_manda_a_la_posicion_cero(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Fachada", "Sala", "Alberca"], {})

    assert rail.posicion_para_soltar(y=0) == 0


def test_soltar_debajo_del_ultimo_lo_manda_al_final(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Fachada", "Sala", "Alberca"], {})

    assert rail.posicion_para_soltar(y=10_000) == 2


def test_arrastrar_un_cuarto_avisa_con_su_posicion(qtbot):
    """La señal lleva el nombre y a dónde va, no un delta: el arrastre es
    «ponlo AQUÍ»."""
    rail = _rail(qtbot)
    rail.set_rooms(["Fachada", "Sala", "Alberca"], {})
    avisos = []
    rail.room_reordered.connect(lambda n, p: avisos.append((n, p)))

    rail.soltar_cuarto("Alberca", 0)

    assert avisos == [("Alberca", 0)]


def test_soltar_un_cuarto_donde_ya_estaba_no_avisa(qtbot):
    """Sin esto, cada clic-sin-mover metería una acción que no hizo nada."""
    rail = _rail(qtbot)
    rail.set_rooms(["Fachada", "Sala"], {})
    avisos = []
    rail.room_reordered.connect(lambda n, p: avisos.append((n, p)))

    rail.soltar_cuarto("Fachada", 0)

    assert avisos == []
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_room_rail.py -q -k "soltar or arrastrar_un_cuarto"
```

- [x] **Step 3: La decisión, separada del gesto**

En `RoomRail`:

```python
    room_reordered = Signal(str, int)      # nombre, posicion destino
```

```python
    def posicion_para_soltar(self, y: int) -> int:
        """En qué posición cae algo soltado a la altura `y`.

        Vive aparte del gesto a propósito: simular un drag-and-drop real bajo
        `offscreen` es frágil, y lo que hay que defender es la traducción de
        un punto a una posición -- que es donde se equivoca uno.
        """
        if not self.rows:
            return 0
        for indice, fila in enumerate(self.rows):
            centro = fila.y() + fila.height() // 2
            if y < centro:
                return indice
        return len(self.rows) - 1

    def soltar_cuarto(self, nombre: str, posicion: int) -> None:
        """Termina el arrastre. No avisa si el cuarto no se movió: cada
        clic-sin-arrastrar metería una acción que no hizo nada."""
        actual = [f.nombre for f in self.rows]
        if nombre not in actual:
            return
        posicion = max(0, min(posicion, len(actual) - 1))
        if actual.index(nombre) == posicion:
            return
        self.room_reordered.emit(nombre, posicion)
```

En `_FilaCuarto`, el arrastre en sí: `mousePressEvent` guarda el punto de
partida, `mouseMoveEvent` arranca un `QDrag` pasado el umbral
(`QApplication.startDragDistance()`), y el rail acepta el drop. El
`mimeData` lleva el nombre del cuarto con un tipo propio
(`application/x-clasificador-cuarto`) para que no se confunda con el arrastre
de clips, que ya existe y significa otra cosa.

El rail dibuja la línea de destino en `paintEvent` cuando hay un arrastre
encima, con la altura que devuelve `posicion_para_soltar`.

- [x] **Step 4: La línea que marca dónde cae**

En `theme.py`, junto a las reglas del rail:

```python
    # La linea que marca donde va a caer el cuarto que arrastras. Es la
    # misma senal que usa la hoja para el arrastre de clips: si aqui fuera
    # otra, habria que aprender dos veces lo mismo.
    DROP_LINE_COLOR = CURRENT_COLOR
```

Y en el `paintEvent` del rail se dibuja de 2 px de alto, de borde a borde
del rail, a la altura de la posición destino.

- [x] **Step 5: Corre la suite completa y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
git add src/clasificador_video/ui/room_rail.py src/clasificador_video/ui/theme.py tests/ui/test_room_rail.py
git commit -m "Los cuartos se arrastran en el rail

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: La ventana atiende el arrastre

**Files:** `src/clasificador_video/ui/main_window.py`, `tests/ui/test_main_window.py`

- [x] **Step 1: Escribe las pruebas que fallan**

```python
def test_arrastrar_un_cuarto_lo_mueve_de_lugar(qtbot):
    window = _window_con_cuartos(qtbot, ["Fachada", "Sala", "Alberca"], clips=3)

    window.room_rail.room_reordered.emit("Alberca", 0)

    assert window.room_selection.active_rooms() == ["Alberca", "Fachada", "Sala"]


def test_arrastrar_un_cuarto_le_cambia_la_tecla(qtbot):
    """Reordenar ES cambiar qué tecla le toca a cada cuarto -- lo que Bruno
    quiere: poner arriba con lo que va a empezar."""
    window = _window_con_cuartos(qtbot, ["Fachada", "Sala", "Alberca"], clips=3)

    window.room_rail.room_reordered.emit("Alberca", 0)
    window.select_clip(0)
    window.handle_key_press("1")

    assert window.clips[0].categoria_path == ["Alberca"]


def test_arrastrar_un_cuarto_no_le_cambia_el_cuarto_a_ningun_clip(qtbot):
    """El gesto mueve el cuarto de lugar y NADA más. Misma regla que el
    arrastre de clips entre bins, y por el mismo motivo: con dos significados
    en el mismo gesto, un arrastre mal soltado cambia el dato que más trabajo
    cuesta."""
    window = _window_con_cuartos(qtbot, ["Fachada", "Sala", "Alberca"], clips=3)
    window.select_clip(0)
    window.handle_key_press("2")               # Sala
    antes = [list(c.categoria_path) for c in window.clips]

    window.room_rail.room_reordered.emit("Alberca", 0)

    assert [list(c.categoria_path) for c in window.clips] == antes
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -q -k arrastrar_un_cuarto
```

- [x] **Step 3: Conectarla**

Junto a `self.room_rail.room_moved.connect(self._on_room_moved)`:

```python
        self.room_rail.room_reordered.connect(self._on_room_reordered)
```

```python
    def _on_room_reordered(self, nombre: str, posicion: int) -> None:
        """Soltaste un cuarto en otro lugar de la lista.

        Igual que `_on_room_moved`: reordenar cambia la TECLA, no a qué
        cuarto pertenece cada clip. `_sync_rooms` es obligatorio -- el router
        se queda con la lista que le dieron, y sin volver a pasársela las
        teclas clasifican al cuarto equivocado en silencio.
        """
        self.room_selection.mover_a(nombre, posicion)
        self._sync_rooms()
```

- [x] **Step 4: Corre la suite completa y commitea**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "Arrastrar un cuarto lo mueve de lugar y cambia su tecla

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Barrido final — el pixel y la documentación

**Files:** `README.md`, `docs/superpowers/CONTEXTO-Y-METAS.md`

- [x] **Step 1: Comprobación visual**

Arma en el scratchpad (NO en el repo) una ventana con seis cuartos en un orden que no sea alfabético, y guarda `window.grab()` a PNG. Ábrelo con la herramienta de lectura de archivos y confirma que **el rail y la hoja dicen el mismo orden**, y que el cuarto `1` del rail es el primer bloque de la hoja.

- [x] **Step 2: El README**

Donde se explica el rail, añade:

```markdown
**El orden de los cuartos lo decides tú**, y es el mismo en la lista y en la
hoja de contactos. Arrastra un cuarto para moverlo, o usa clic derecho →
Subir / Bajar (`⌥↑` / `⌥↓` con el teclado). Mover un cuarto **cambia su
número**: el que quede arriba es el `1`. Sirve para empezar por el cuarto que
quieras cuando andas repasando picks.
```

- [x] **Step 3: CONTEXTO-Y-METAS**

Añade a lo cerrado el porqué, y sobre todo la lección: la hoja ordenaba por abecedario y el rail por decisión de Bruno, y esa contradicción hacía que reordenar —que sí existía— pareciera no existir. Y deja escrito que el arrastre en el rail se había descartado el 2026-08-08 por «una vez por shooting», supuesto que resultó falso.

- [x] **Step 4: Commit**

```bash
git add README.md docs/superpowers/CONTEXTO-Y-METAS.md
git commit -m "El orden de los cuartos, en la documentacion

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
