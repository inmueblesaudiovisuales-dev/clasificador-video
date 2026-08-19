# Los bins en el deshacer — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `⌘Z` deshaga las acciones de bin —mover clips, crear, renombrar— en vez de revertir en silencio una acción anterior.

**Architecture:** `HistoryEntry` gana tres campos opcionales que describen lo que la acción le hizo a los bins, con la misma forma que el `cuarto_borrado` que ya existe. `History` sigue sin Qt y sin saber qué es un bin: solo los recuerda. Quien aplica sigue siendo `MainWindow._aplicar_entrada`, el único lugar donde el estado guardado se vuelve a poner. Los renglones que ya no se pueden cumplir se apagan, y la razón la calcula la ventana —que es quien conoce los bins— y se la pasa al rail.

**Tech Stack:** Python 3.13, PySide6, pytest + pytest-qt. Suite completa: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

**Spec:** `docs/superpowers/specs/2026-08-18-bins-en-el-deshacer-design.md`

---

## Estructura de archivos

| Archivo | Responsabilidad | Qué cambia |
|---|---|---|
| `src/clasificador_video/history.py` | Recordar acciones. Sin Qt, sin bins. | Tres campos en `HistoryEntry`; `renombrar_bin`; `renombrar_cuarto` deja de tocar entradas de bin |
| `src/clasificador_video/ui/main_window.py` | Registrar y aplicar | Registra en las tres acciones; `_aplicar_entrada` sabe de bins; calcula qué renglón está bloqueado; `undo` no salta uno bloqueado |
| `src/clasificador_video/ui/room_rail.py` | Dibujar los renglones | `set_history` acepta los bloqueados; `_FilaHistorial` se apaga y dice por qué |
| `src/clasificador_video/ui/theme.py` | Color | Estilo del renglón bloqueado |
| `tests/test_history.py` | Lo puro | Tasks 1 |
| `tests/ui/test_main_window_bins.py` | Registrar y deshacer | Tasks 2, 3, 4, 6, 7 |
| `tests/ui/test_room_rail.py` | El renglón apagado | Task 5 |

**Nombres que se usan en todo el plan** (si un task los escribe distinto, es un bug):

- `HistoryEntry.bins_antes: dict[int, str | None] | None`
- `HistoryEntry.bin_creado: str | None`
- `HistoryEntry.bin_renombrado: tuple[str, str] | None`
- `History.renombrar_bin(viejo: str, nuevo: str) -> None`
- `MainWindow._motivo_bloqueado(entrada) -> str | None`
- `RoomRail.set_history(entries: list, bloqueadas: dict[int, str] | None = None) -> None`
- `_FilaHistorial(entry, es_primera: bool, motivo_bloqueado: str | None = None, parent=None)`

---

### Task 1: `HistoryEntry` se acuerda de los bins

**Files:**
- Modify: `src/clasificador_video/history.py`
- Test: `tests/test_history.py`

- [x] **Step 1: Escribe las pruebas que fallan**

Al final de `tests/test_history.py`:

```python
def test_una_entrada_puede_recordar_de_que_bin_venia_cada_clip():
    """El bin no es un campo del clip --vive en `BinTree`-- asi que no puede
    viajar por `antes`, que se aplica con `setattr` sobre el clip."""
    entrada = HistoryEntry(
        etiqueta="Card B", detalle="→ 3 clips", color="#3e9bc0", antes={},
        bins_antes={0: "Card A", 1: None},
    )
    assert entrada.bins_antes == {0: "Card A", 1: None}
    assert entrada.bin_creado is None
    assert entrada.bin_renombrado is None


def test_los_campos_de_bin_nacen_vacios():
    """Una entrada de cuarto o de estado no habla de bins, y no tiene por que
    escribir tres `None` para decirlo."""
    entrada = HistoryEntry(etiqueta="Cocina", detalle="→ 6 clips",
                           color="#c0885a", antes={})
    assert entrada.bins_antes is None
    assert entrada.bin_creado is None
    assert entrada.bin_renombrado is None


def test_renombrar_un_bin_mueve_lo_ya_registrado():
    """Mismo motivo que `renombrar_cuarto`: un renglon que hable de un bin
    que ya no existe promete devolver algo inalcanzable."""
    h = History()
    h.push(HistoryEntry(etiqueta="Card A", detalle="→ 2 clips", color="#3e9bc0",
                        antes={}, bins_antes={0: "Card A", 1: None}))
    h.push(HistoryEntry(etiqueta="Card A", detalle="→ bin nuevo", color="#3e9bc0",
                        antes={}, bin_creado="Card A"))

    h.renombrar_bin("Card A", "Camara 1")

    creado, movido = h.entries()
    assert creado.bin_creado == "Camara 1"
    assert creado.etiqueta == "Camara 1"
    assert movido.bins_antes == {0: "Camara 1", 1: None}
    assert movido.etiqueta == "Camara 1"


def test_renombrar_un_bin_no_toca_un_cuarto_que_se_llame_igual():
    """Un cuarto y un bin pueden llamarse igual --«Cocina» la camara y
    «Cocina» el cuarto-- y la `etiqueta` no distingue cual es cual. Se mira
    si la entrada habla de bins, que es el dato."""
    h = History()
    h.push(HistoryEntry(etiqueta="Cocina", detalle="→ 6 clips", color="#c0885a",
                        antes={0: {"categoria_path": ["Cocina"]}}))

    h.renombrar_bin("Cocina", "Camara 1")

    assert h.entries()[0].etiqueta == "Cocina"
    assert h.entries()[0].antes == {0: {"categoria_path": ["Cocina"]}}


def test_renombrar_un_cuarto_no_toca_un_bin_que_se_llame_igual():
    """El reves del anterior, y hace falta desde hoy: hasta ahora ninguna
    entrada del historial hablaba de bins."""
    h = History()
    h.push(HistoryEntry(etiqueta="Cocina", detalle="→ 2 clips", color="#3e9bc0",
                        antes={}, bins_antes={0: "Cocina"}))

    h.renombrar_cuarto("Cocina", "Cocina chica")

    assert h.entries()[0].etiqueta == "Cocina"
    assert h.entries()[0].bins_antes == {0: "Cocina"}
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_history.py -q -k "bin"
```

Esperado: FAIL con `TypeError: HistoryEntry.__init__() got an unexpected keyword argument 'bins_antes'`.

- [x] **Step 3: Agrega los campos y `renombrar_bin`**

En `src/clasificador_video/history.py`, dentro de `HistoryEntry`, después de `cuarto_borrado`:

```python
    # --- lo que la accion le hizo a los BINS -------------------------------
    # Van aparte de `antes` porque el bin NO es un campo del clip: vive en
    # `BinTree`, que es la unica fuente de verdad. `antes` se aplica con
    # `setattr` sobre el clip, y meter aqui un campo que el clip no tiene
    # seria inventarle uno -- justo la duplicacion que hace que dos copias
    # del mismo dato se contradigan.
    #
    # `bins_antes` es `{indice_de_clip: nombre_del_bin}`, con `None` para
    # «estaba suelto», que es un estado valido y no la ausencia de dato.
    bins_antes: dict[int, str | None] | None = None
    bin_creado: str | None = None
    # `(viejo, nuevo)`. No se deduce del texto del renglon: `etiqueta` y
    # `detalle` son para el ojo, y leerlos como dato hace que cambiar una
    # palabra rompa una funcion.
    bin_renombrado: tuple[str, str] | None = None
```

Colócalos entre `cuarto_borrado` e `id`, para que `id` siga siendo el último campo de la clase.

Añade también, dentro de `HistoryEntry`:

```python
    def habla_de_bins(self) -> bool:
        """Si esta entrada es de un bin o de un cuarto.

        Hace falta porque un cuarto y un bin se pueden llamar IGUAL --«Cocina»
        la camara y «Cocina» el cuarto-- y la `etiqueta` no los distingue.
        Renombrar uno movia el renglon del otro.
        """
        return (self.bins_antes is not None
                or self.bin_creado is not None
                or self.bin_renombrado is not None)
```

En `History.renombrar_cuarto`, cambia el encabezado del bucle:

```python
        for entrada in self._entries:
            if entrada.habla_de_bins():
                continue    # es un bin, no un cuarto (ver `habla_de_bins`)
            if entrada.etiqueta == viejo:
                entrada.etiqueta = nuevo
```

Y agrega el método nuevo justo debajo de `renombrar_cuarto`:

```python
    def renombrar_bin(self, viejo: str, nuevo: str) -> None:
        """El gemelo de `renombrar_cuarto`, para el otro eje.

        Un renglon que siga hablando de un bin que ya no existe promete
        devolverte algo inalcanzable: su `↺` no encontraria a donde regresar
        los clips. Solo toca las entradas que hablan de bins, para no
        confundirse con un cuarto que se llame igual.
        """
        for entrada in self._entries:
            if not entrada.habla_de_bins():
                continue
            if entrada.etiqueta == viejo:
                entrada.etiqueta = nuevo
            if entrada.bin_creado == viejo:
                entrada.bin_creado = nuevo
            if entrada.bins_antes is not None:
                entrada.bins_antes = {
                    i: (nuevo if b == viejo else b)
                    for i, b in entrada.bins_antes.items()
                }
            if entrada.bin_renombrado is not None:
                a, b = entrada.bin_renombrado
                entrada.bin_renombrado = (nuevo if a == viejo else a,
                                          nuevo if b == viejo else b)
```

- [x] **Step 4: Corre las pruebas**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_history.py -q
```

Esperado: PASS, todas.

- [x] **Step 5: Commit**

```bash
git add src/clasificador_video/history.py tests/test_history.py
git commit -m "El historial ya puede acordarse de los bins

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Deshacer un arrastre entre bins

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py` (`_on_clips_movidos`, `_aplicar_entrada`)
- Test: `tests/ui/test_main_window_bins.py`

- [x] **Step 1: Escribe las pruebas que fallan**

Al final de `tests/ui/test_main_window_bins.py`. Usa los helpers que ya hay en ese archivo para armar la ventana; si el helper se llama distinto, ajusta la llamada pero NO el cuerpo de la prueba.

```python
def test_deshacer_un_arrastre_devuelve_el_clip_a_su_bin(qtbot):
    """El bug que originó todo esto, medido el 2026-08-18: arrastras un clip
    a otro bin, aprietas ⌘Z, y el clip se quedaba donde lo soltaste MIENTRAS
    otro clip perdía el cuarto que le habías puesto."""
    window = _ventana_con_bins(qtbot)          # Card A: 0,1,2 · Card B: vacío
    window.select_clip(0)
    window.handle_key_press("1")               # Sala al clip 1
    window.select_clip(2)
    window.handle_key_press("2")               # Cocina al clip 3

    window._on_clips_movidos([0], "Card B")
    window.undo()

    assert window.bins.bin_de(0) == "Card A"
    assert window.clips[2].categoria_path == ["Cocina"]


def test_deshacer_un_arrastre_devuelve_cada_clip_a_SU_bin(qtbot):
    """Varios clips de bins distintos en el mismo gesto: cada uno vuelve a
    donde estaba, no todos al primero."""
    window = _ventana_con_bins(qtbot)
    window.bins.mover([2], "Card B")           # el clip 3 ya vivía en Card B

    window._on_clips_movidos([0, 2], None)     # los dos, a «Sin bin»
    window.undo()

    assert window.bins.bin_de(0) == "Card A"
    assert window.bins.bin_de(2) == "Card B"


def test_deshacer_devuelve_a_sin_bin_al_que_venia_suelto(qtbot):
    """«Suelto» es un estado valido, no la ausencia de dato: devolverlo al
    primer bin seria inventarle una camara."""
    window = _ventana_con_bins(qtbot)
    window.bins.mover([1], None)               # el clip 2 queda suelto

    window._on_clips_movidos([1], "Card B")
    window.undo()

    assert window.bins.bin_de(1) is None


def test_deshacer_un_arrastre_no_toca_el_cuarto_ni_el_estado(qtbot):
    """Arrastrar cambia el bin y nada mas; deshacerlo, tambien. Es lo que
    hace que ⌘Z se pueda apretar sin pensarlo."""
    window = _ventana_con_bins(qtbot)
    window.select_clip(0)
    window.handle_key_press("1")               # Sala
    window.handle_key_press("p")               # pick
    window.select_clip(0)
    window.handle_key_press("i")               # in

    window._on_clips_movidos([0], "Card B")
    window.undo()

    assert window.clips[0].categoria_path == ["Sala"]
    assert window.clips[0].flag == "pick"
    assert window.clips[0].in_frame is not None


def test_el_arrastre_deja_su_renglon_en_el_historial(qtbot):
    window = _ventana_con_bins(qtbot)

    window._on_clips_movidos([0, 1], "Card B")

    entrada = window.history.entries()[0]
    assert entrada.etiqueta == "Card B"
    assert entrada.detalle == "→ 2 clips"
    assert entrada.bins_antes == {0: "Card A", 1: "Card A"}


def test_deshacer_un_arrastre_no_mete_su_propia_entrada(qtbot):
    """Si `_on_clips_movidos` registrara desde adentro, deshacer meteria una
    entrada nueva y ⌘Z se volveria un columpio: dos teclazos y vuelves al
    principio sin haber deshecho nada."""
    window = _ventana_con_bins(qtbot)
    window._on_clips_movidos([0], "Card B")
    cuantas = len(window.history.entries())

    window.undo()

    assert len(window.history.entries()) == cuantas - 1
```

Y arriba, junto a los demás helpers del archivo:

```python
def _ventana_con_bins(qtbot) -> MainWindow:
    """Tres clips en «Card A» y un «Card B» vacío al lado."""
    window = _window(qtbot)                    # helper que ya existe
    window.resize(1500, 900)
    window.load_clips([
        Clip(orden=i + 1, ruta=Path(f"/x/C{i:04d}.MP4"), categoria_path=[], fps=30.0)
        for i in range(3)
    ])
    window.bins.agregar("Card A", Path("/A"), [0, 1, 2])
    window.bins.crear_vacio("Card B")
    window._refresh_sheet(force_rebuild=True)
    window.show()
    qtbot.waitExposed(window)
    if window._modo_hoja:
        window.alternar_modo_hoja()
    return window
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q -k "arrastre or sin_bin or SU_bin"
```

Esperado: FAIL — el clip se queda en `Card B` y el cuarto del otro se pierde.

- [x] **Step 3: Registra el arrastre**

En `main_window.py`, reemplaza el cuerpo de `_on_clips_movidos` (deja el docstring que ya tiene y añádele el párrafo nuevo):

```python
        if not indices:
            return
        # ANTES de mover, como todo lo que entra al historial: despues ya
        # guardaria el estado nuevo y deshacer no haria nada. Se guarda de
        # que bin venia CADA clip --no el destino-- porque el gesto puede
        # juntar clips de bins distintos y cada uno tiene que volver al suyo.
        self._registrar_movimiento_de_bin(indices, destino)
        self.bins.mover(indices, destino)
        self._refresh_sheet()
        self._autosave()

    def _registrar_movimiento_de_bin(self, indices: list[int],
                                     destino: str | None) -> None:
        """La entrada del historial de un arrastre.

        Va aparte de `_registrar` porque aquella guarda CAMPOS del clip y el
        bin no es un campo del clip. La etiqueta es el destino --es lo que
        acabas de hacer, «los mandé a Card B»-- y el color, la identidad de
        camara de ese bin.
        """
        self.history.push(HistoryEntry(
            etiqueta=destino or SIN_BIN,
            detalle=self._detalle(indices),
            color=self._color_de_bin(destino),
            antes={},
            bins_antes={i: self.bins.bin_de(i) for i in indices
                        if 0 <= i < len(self.clips)},
        ))
        self._refresh_history()

    def _color_de_bin(self, nombre: str | None) -> str:
        """El tercer canal de color, ni cuarto ni estado (ver `theme.py`).

        Un bin que no esta en la lista --«Sin bin», o uno que ya se fue-- se
        pinta con el gris apagado: no es una camara, asi que no lleva
        identidad de camara.
        """
        nombres = self.bins.nombres()
        if nombre is None or nombre not in nombres:
            return theme.TEXT_3
        return theme.bin_color(nombres.index(nombre))
```

Comprueba que `SIN_BIN` ya esté importado en `main_window.py` (se usa en `_on_bin_seleccionado`); si no, añádelo al import de `clip_sheet`.

- [x] **Step 4: Aplica el arrastre al deshacer**

En `_aplicar_entrada`, después del bloque de `cuarto_borrado` y antes de `self._refresh_sheet()`:

```python
        if entrada.bins_antes is not None:
            # agrupado por destino porque `mover` recibe una lista por
            # destino, y el gesto pudo juntar clips de bins distintos
            por_bin: dict[str | None, list[int]] = {}
            for indice, bin_nombre in entrada.bins_antes.items():
                if 0 <= indice < len(self.clips):
                    por_bin.setdefault(bin_nombre, []).append(indice)
            for bin_nombre, indices in por_bin.items():
                self.bins.mover(indices, bin_nombre)
```

- [x] **Step 5: Corre las pruebas**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q
```

Esperado: PASS, todas.

- [x] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_bins.py
git commit -m "Deshacer un arrastre devuelve el clip a su bin

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Deshacer «creé un bin»

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py` (`_on_bin_nuevo_pedido`, `_aplicar_entrada`)
- Test: `tests/ui/test_main_window_bins.py`

- [x] **Step 1: Escribe las pruebas que fallan**

```python
def test_deshacer_quita_el_bin_recien_creado(qtbot):
    window = _ventana_con_bins(qtbot)
    antes = window.bins.nombres()

    window._on_bin_nuevo_pedido()
    assert len(window.bins.nombres()) == len(antes) + 1
    window.undo()

    assert window.bins.nombres() == antes


def test_crear_un_bin_deja_su_renglon(qtbot):
    window = _ventana_con_bins(qtbot)

    window._on_bin_nuevo_pedido()

    entrada = window.history.entries()[0]
    assert entrada.bin_creado in window.bins.nombres()
    assert entrada.detalle == "→ bin nuevo"


def test_no_se_borra_un_bin_que_ya_tiene_clips(qtbot):
    """El arrastre fue una decision aparte y mas reciente: borrar el bin se
    llevaria dos cosas de un click. Primero deshaces el arrastre --que desde
    la Task 2 se puede-- y luego el bin."""
    window = _ventana_con_bins(qtbot)
    window._on_bin_nuevo_pedido()
    nuevo = window.history.entries()[0].bin_creado
    window._on_clips_movidos([0], nuevo)

    window.undo()          # deshace el ARRASTRE, que es lo de arriba
    window.undo()          # y ahora si, el bin

    assert nuevo not in window.bins.nombres()
    assert window.bins.bin_de(0) == "Card A"
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q -k "recien_creado or su_renglon or ya_tiene_clips"
```

Esperado: FAIL — no se crea entrada y el bin se queda.

- [x] **Step 3: Registra la creación**

En `_on_bin_nuevo_pedido`, después de `nombre = self.bins.crear_vacio("Bin")`:

```python
        # DESPUES de crearlo, no antes: el nombre lo decide `BinTree` --hay
        # que esquivar los que ya existen-- y sin el nombre real la entrada
        # no sabria cual quitar.
        self.history.push(HistoryEntry(
            etiqueta=nombre,
            detalle="→ bin nuevo",
            color=self._color_de_bin(nombre),
            antes={},
            bin_creado=nombre,
        ))
        self._refresh_history()
```

- [x] **Step 4: Aplica la creación al deshacer**

En `_aplicar_entrada`, después del bloque de `bins_antes`:

```python
        if entrada.bin_creado is not None:
            # solo si sigue vacio: un bin con material no se borra por
            # deshacer (spec §2). El renglon se apaga antes de llegar aqui,
            # y esta guarda es la red de abajo -- el estado pudo cambiar
            # entre que se dibujo el renglon y que lo apretaste.
            if not self.bins.clips_de(entrada.bin_creado):
                self.bins.quitar(entrada.bin_creado)
                self.clip_sheet.set_bin_order(self.bins.nombres())
```

- [x] **Step 5: Corre las pruebas**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q
```

Esperado: PASS.

- [x] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_bins.py
git commit -m "Deshacer quita el bin que acabas de crear

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Deshacer un renombrado

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py` (`_on_bin_renombrado`, `_aplicar_entrada`)
- Test: `tests/ui/test_main_window_bins.py`

- [x] **Step 1: Escribe las pruebas que fallan**

```python
def test_deshacer_un_renombrado_recupera_el_nombre_viejo(qtbot):
    window = _ventana_con_bins(qtbot)

    window._on_bin_renombrado("Card A", "Camara 1")
    assert "Camara 1" in window.bins.nombres()
    window.undo()

    assert "Card A" in window.bins.nombres()
    assert "Camara 1" not in window.bins.nombres()
    assert window.bins.bin_de(0) == "Card A"


def test_renombrar_un_bin_arregla_los_renglones_viejos(qtbot):
    """Un renglon que hable de un bin que ya no existe promete devolver algo
    inalcanzable. Mismo arreglo que ya se le hizo a los cuartos."""
    window = _ventana_con_bins(qtbot)
    window._on_clips_movidos([0], "Card B")

    window._on_bin_renombrado("Card A", "Camara 1")

    movido = [e for e in window.history.entries() if e.bins_antes][0]
    assert movido.bins_antes == {0: "Camara 1"}


def test_renombrar_un_bin_no_toca_el_renglon_de_un_cuarto_que_se_llame_igual(qtbot):
    """Un cuarto «Cocina» y una camara «Cocina» pueden convivir."""
    window = _ventana_con_bins(qtbot)
    window.select_clip(0)
    window.handle_key_press("2")                    # Cocina, el CUARTO
    window._on_bin_renombrado("Card A", "Cocina")   # y ahora el BIN

    window._on_bin_renombrado("Cocina", "Camara 1")

    de_cuarto = [e for e in window.history.entries() if not e.habla_de_bins()][0]
    assert de_cuarto.etiqueta == "Cocina"
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q -k "renombrado or renglones_viejos or se_llame_igual"
```

Esperado: FAIL.

- [x] **Step 3: Extrae el renombrado a su propio método**

Este paso NO cambia comportamiento: mueve código para que deshacer pueda reusarlo. En `main_window.py`, renombra `_on_bin_renombrado` a `_aplicar_renombrado_de_bin`, quítale la última línea (`self._autosave()`), y añádele docstring y la llamada al historial. Queda así, entero:

```python
    def _aplicar_renombrado_de_bin(self, viejo: str, nuevo: str) -> None:
        """Le cambia el nombre al bin y a TODO lo que lo guarda por nombre.

        Vive aparte de `_on_bin_renombrado` porque deshacer un renombrado es
        renombrar al reves, y las dos cosas tienen que mover exactamente las
        mismas llaves. Escrito dos veces, la segunda copia se olvida de una.
        """
        self.bins.renombrar(viejo, nuevo)
        # la hoja guarda por NOMBRE dos cosas suyas que el dato no conoce:
        # si el bin esta colapsado y su carpeta de origen. Se le avisa antes
        # de refrescar, porque el refresco ya trae el nombre nuevo.
        if nuevo in self.bins.nombres():
            self.clip_sheet.renombrar_bin(viejo, nuevo)
            # el aviso de media faltante tambien va por nombre: sin mover la
            # llave, el renglon seguiria hablando de un bin que ya no existe
            if viejo in self._ultimo_reencuentro:
                self._ultimo_reencuentro[nuevo] = self._ultimo_reencuentro.pop(viejo)
            # y la tanda de proxies que estuviera corriendo, que se acuerda del
            # bin POR NOMBRE. Sin mover la llave le seguia hablando a un bin
            # que ya no existe: el «creando proxies · 7/23» dejaba de moverse,
            # el menu volvia a ofrecer «Crear proxies» en vez de cancelar --y
            # al darle contestaba que ya se estaban creando los de un nombre
            # viejo-- y al terminar nadie le pedia las portadas a esos clips,
            # que se quedaban grises.
            if (self._generando_proxies is not None
                    and self._generando_proxies["bin"] == viejo):
                self._generando_proxies["bin"] = nuevo
            self._refrescar_aviso()
            # y los renglones del historial, que guardan el nombre del bin:
            # sin esto prometen devolver los clips a un bin que ya no existe.
            # Mismo arreglo, mismo motivo y mismo lugar que el de los cuartos
            # en `_on_room_renamed`.
            self.history.renombrar_bin(viejo, nuevo)
        # `force_rebuild` no: reconstruir la hoja tiraria las portadas ya
        # cargadas, y aqui no cambio ni un clip -- solo como se llama su bin.
        self._refresh_sheet()
        # DESPUES del refresco: el encabezado con el nombre nuevo nace ahi, y
        # nace sin saber que su bin esta generando proxies.
        self._pintar_avance_de_proxies()
```

- [x] **Step 4: Corre la suite y comprueba que no rompiste nada**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: FAIL solo en las pruebas de la Step 1 y en las que llamen a `_on_bin_renombrado`, que ya no existe. Anota cuáles son: la Step 5 las va a arreglar sola al reponer el método.

- [x] **Step 5: Vuelve a poner `_on_bin_renombrado`, ahora registrando**

Justo encima de `_aplicar_renombrado_de_bin`:

```python
    def _on_bin_renombrado(self, viejo: str, nuevo: str) -> None:
        """Le pusiste otro nombre al bin desde su encabezado.

        Registra PRIMERO y aplica DESPUES no se puede aqui, y es al reves de
        la regla de siempre: `_aplicar_renombrado_de_bin` llama a
        `history.renombrar_bin`, que le pasa por encima a todo lo que hable
        del nombre viejo -- incluida la entrada que se acabara de meter, que
        quedaria diciendo `(nuevo, nuevo)` y no sabria a que volver. Se
        aplica, y luego se registra lo que paso.
        """
        nuevo = nuevo.strip()
        if not nuevo or nuevo == viejo or nuevo in self.bins.nombres():
            # `BinTree.renombrar` ignora en silencio un nombre repetido o
            # vacio, con el mismo criterio que `RoomSelection.rename`. Aqui
            # tampoco se registra: quedaria un renglon de una accion que no
            # paso, y su `↺` prometeria deshacer nada.
            return
        self._aplicar_renombrado_de_bin(viejo, nuevo)
        self.history.push(HistoryEntry(
            etiqueta=nuevo,
            detalle=f"→ antes {viejo}",
            color=self._color_de_bin(nuevo),
            antes={},
            bin_renombrado=(viejo, nuevo),
        ))
        self._refresh_history()
        self._autosave()
```

- [x] **Step 6: Aplica el renombrado al deshacer**

En `_aplicar_entrada`, después del bloque de `bin_creado`:

```python
        if entrada.bin_renombrado is not None:
            viejo, nuevo = entrada.bin_renombrado
            # al reves. Solo si el nombre de hoy sigue siendo el que esta
            # entrada puso: si lo renombraste otra vez, este renglon ya
            # quedo bloqueado y no deberia llegar hasta aqui.
            if nuevo in self.bins.nombres():
                self._aplicar_renombrado_de_bin(nuevo, viejo)
```

- [x] **Step 7: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS, todas. Este task mueve código que ya existía, así que aquí es donde se nota si se quedó algo atrás.

- [x] **Step 8: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_bins.py
git commit -m "Deshacer un renombrado de bin, y los renglones que hablaban del nombre viejo

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: El renglón que ya no se puede cumplir se apaga

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py` (`_FilaHistorial`, `RoomRail.set_history`)
- Modify: `src/clasificador_video/ui/theme.py`
- Modify: `src/clasificador_video/ui/main_window.py` (`_motivo_bloqueado`, `_refresh_history`)
- Test: `tests/ui/test_room_rail.py`, `tests/ui/test_main_window_bins.py`

- [x] **Step 1: Escribe las pruebas que fallan**

En `tests/ui/test_room_rail.py`:

```python
def test_un_renglon_bloqueado_se_apaga_y_dice_por_que(qtbot):
    """No desaparece: Bruno tiene que poder ver que la accion existio, igual
    que un proyecto que no se encuentra se ve apagado en vez de esfumarse."""
    rail = RoomRail()
    qtbot.addWidget(rail)
    entrada = _entrada(etiqueta="Card C", detalle="→ bin nuevo")

    rail.set_history([entrada], {entrada.id: "ya tiene clips"})

    fila = rail.history_rows[0]
    assert not fila.undo_button.isEnabled()
    assert "ya tiene clips" in fila.toolTip()


def test_el_renglon_se_vuelve_a_dibujar_al_cambiar_lo_bloqueado(qtbot):
    """`set_history` se salta el redibujado cuando los ids son los mismos, y
    los ids no cambian al bloquearse: sin mirarlo, el renglon se quedaba
    prendido despues de dejar de poderse."""
    rail = RoomRail()
    qtbot.addWidget(rail)
    entrada = _entrada(etiqueta="Card C", detalle="→ bin nuevo")
    rail.set_history([entrada])
    assert rail.history_rows[0].undo_button.isEnabled()

    rail.set_history([entrada], {entrada.id: "ya tiene clips"})

    assert not rail.history_rows[0].undo_button.isEnabled()
```

Y el helper, junto a los demás del archivo:

```python
def _entrada(etiqueta: str = "Cocina", detalle: str = "→ 2 clips"):
    from clasificador_video.history import HistoryEntry
    return HistoryEntry(etiqueta=etiqueta, detalle=detalle,
                        color=theme.TEXT_3, antes={})
```

En `tests/ui/test_main_window_bins.py`:

```python
def test_el_renglon_del_bin_creado_se_bloquea_al_meterle_clips(qtbot):
    window = _ventana_con_bins(qtbot)
    window._on_bin_nuevo_pedido()
    nuevo = window.history.entries()[0].bin_creado
    entrada = window.history.entries()[0]
    assert window._motivo_bloqueado(entrada) is None

    window._on_clips_movidos([0], nuevo)

    assert window._motivo_bloqueado(entrada) == "ya tiene clips"


def test_se_bloquea_el_arrastre_cuyo_bin_de_origen_ya_no_esta(qtbot):
    window = _ventana_con_bins(qtbot)
    window._on_clips_movidos([0], "Card B")
    entrada = window.history.entries()[0]
    window.bins.quitar("Card A")

    assert window._motivo_bloqueado(entrada) == "ese bin ya no está"
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_room_rail.py tests/ui/test_main_window_bins.py -q -k "bloquea or apaga or dibujar"
```

Esperado: FAIL con `TypeError: set_history() takes 2 positional arguments` y `AttributeError: _motivo_bloqueado`.

- [x] **Step 3: La fila se apaga**

En `room_rail.py`, `_FilaHistorial.__init__` cambia de firma:

```python
    def __init__(self, entry, es_primera: bool, motivo_bloqueado: str | None = None,
                 parent=None):
```

y al final de `__init__`, después de conectar el botón:

```python
        # Un renglon que ya no se puede cumplir se APAGA, no se esconde: hay
        # que poder ver que la accion existio. Se marca por propiedad y no
        # con `setEnabled(False)` sobre la fila entera, porque un widget
        # apagado no recibe eventos de mouse y el tooltip --que es donde vive
        # el porque-- no se veria. Mismo tropiezo que ya tuvo la fila de
        # proyectos recientes.
        self.motivo_bloqueado = motivo_bloqueado
        self.setProperty("bloqueada", "true" if motivo_bloqueado else "false")
        if motivo_bloqueado:
            self.undo_button.setEnabled(False)
            self.setToolTip(f"No se puede deshacer: {motivo_bloqueado}")
```

Y `set_history`:

```python
    def set_history(self, entries: list, bloqueadas: dict[int, str] | None = None) -> None:
        """Las ultimas acciones, la mas reciente arriba. Se le pasa la lista
        completa del `History`; aca se recorta a lo que entra en el rail.

        `bloqueadas` es `{id_de_entrada: por que}`, y lo calcula la VENTANA:
        el rail no sabe que es un bin ni tiene por que saberlo.
        """
        bloqueadas = bloqueadas or {}
        # mismas entradas, mismas filas: `_refresh_history` corre en cada
        # accion y casi siempre el historial no cambio. La firma incluye lo
        # BLOQUEADO porque eso cambia sin que cambien los ids -- meterle
        # clips a un bin no crea ni quita entradas, solo apaga un renglon.
        firma = [(e.id, bloqueadas.get(e.id)) for e in entries[:MAX_HISTORIAL]]
        if firma == [(f.entry_id, f.motivo_bloqueado) for f in self.history_rows]:
            return
        for fila in self.history_rows:
            fila.setParent(None)
            fila.deleteLater()
        self.history_rows = []
        for posicion, entrada in enumerate(entries[:MAX_HISTORIAL]):
            fila = _FilaHistorial(entrada, es_primera=(posicion == 0),
                                  motivo_bloqueado=bloqueadas.get(entrada.id))
            fila.revert_requested.connect(self.revert_requested.emit)
            self._history_layout.addWidget(fila)
            self.history_rows.append(fila)
        self.history_panel.setVisible(bool(self.history_rows))
```

- [x] **Step 4: El estilo del renglón apagado**

En `theme.py`, dentro de `build_stylesheet`, junto a las demás reglas de `#histRow`:

```python
    /* el que ya no se puede cumplir: se hunde al fondo y pierde contraste,
       para que se lea «esta, pero no se puede». Va por PROPIEDAD y no por
       `:disabled` -- la fila NO se apaga entera, o perderia el tooltip que
       explica el porque. */
    QWidget#histRow[bloqueada="true"] QLabel#histWhat,
    QWidget#histRow[bloqueada="true"] QLabel#histDetail {{
        color: {TEXT_3};
    }}
```

- [x] **Step 5: La ventana calcula el motivo**

En `main_window.py`, junto a `_refresh_history`:

```python
    def _motivo_bloqueado(self, entrada: HistoryEntry) -> str | None:
        """Por que ese renglon ya no se puede deshacer, o `None` si si se puede.

        Lo calcula la ventana porque es quien conoce los bins: `History` se
        queda sin saber que es un bin, igual que se quedo sin saber que es un
        cuarto.
        """
        if entrada.bin_creado is not None and self.bins.clips_de(entrada.bin_creado):
            return "ya tiene clips"
        if entrada.bins_antes is not None:
            nombres = self.bins.nombres()
            if any(b is not None and b not in nombres
                   for b in entrada.bins_antes.values()):
                return "ese bin ya no está"
        if entrada.bin_renombrado is not None:
            _, nuevo = entrada.bin_renombrado
            if nuevo not in self.bins.nombres():
                return "ese bin ya no está"
        return None
```

y `_refresh_history` pasa a:

```python
    def _refresh_history(self) -> None:
        entradas = self.history.entries()
        bloqueadas = {}
        for entrada in entradas:
            motivo = self._motivo_bloqueado(entrada)
            if motivo is not None:
                bloqueadas[entrada.id] = motivo
        self.room_rail.set_history(entradas, bloqueadas)
        # `⌘Z` deshace la de arriba: si esa esta bloqueada, no hay nada que
        # deshacer, y el boton tiene que decirlo igual que el renglon
        self.tool_column.set_can_undo(
            bool(entradas) and entradas[0].id not in bloqueadas
        )
```

- [x] **Step 6: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS.

- [x] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/room_rail.py src/clasificador_video/ui/theme.py src/clasificador_video/ui/main_window.py tests/ui/test_room_rail.py tests/ui/test_main_window_bins.py
git commit -m "El renglon que ya no se puede cumplir se apaga y dice por que

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `⌘Z` no se salta un renglón bloqueado

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py` (`undo`, `revert`)
- Test: `tests/ui/test_main_window_bins.py`

- [x] **Step 1: Escribe las pruebas que fallan**

```python
def test_cmd_z_no_salta_al_siguiente_cuando_el_de_arriba_esta_bloqueado(qtbot):
    """Es el bug entero, en chico: si ⌘Z se saltara el renglon bloqueado
    deshariia una accion anterior sin decirlo -- exactamente lo que este
    trabajo existe para quitar."""
    window = _ventana_con_bins(qtbot)
    window.select_clip(0)
    window.handle_key_press("1")                 # Sala, y entra al historial
    window._on_bin_nuevo_pedido()
    nuevo = window.history.entries()[0].bin_creado
    window.bins.mover([1], nuevo)                # a mano: no crea entrada
    window._refresh_history()

    window.undo()

    assert window.clips[0].categoria_path == ["Sala"]
    assert nuevo in window.bins.nombres()


def test_el_boton_de_deshacer_se_apaga_si_el_de_arriba_esta_bloqueado(qtbot):
    window = _ventana_con_bins(qtbot)
    window._on_bin_nuevo_pedido()
    nuevo = window.history.entries()[0].bin_creado
    assert window.tool_column.undo_button.isEnabled()

    window.bins.mover([1], nuevo)
    window._refresh_history()

    assert not window.tool_column.undo_button.isEnabled()
```

- [x] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q -k "no_salta or boton_de_deshacer"
```

Esperado: FAIL — `⌘Z` se lleva el cuarto «Sala».

- [x] **Step 3: `undo` y `revert` respetan el bloqueo**

```python
    def undo(self) -> None:
        """`⌘Z`: deshace la accion de arriba del historial.

        Si esa accion ya no se puede cumplir, NO se salta a la siguiente:
        saltar seria deshacer algo que no pediste sin decirlo, que es el bug
        que este historial existe para no tener. El renglon del rail ya
        explica por que no se puede.
        """
        entradas = self.history.entries()
        if entradas and self._motivo_bloqueado(entradas[0]) is not None:
            return
        self._aplicar_entrada(self.history.undo_last())

    def revert(self, entry_id: int) -> None:
        """El boton `↺` de una fila cualquiera, no solo la de arriba."""
        entrada = next((e for e in self.history.entries() if e.id == entry_id), None)
        if entrada is not None and self._motivo_bloqueado(entrada) is not None:
            return   # el boton ya esta apagado; esta es la red de abajo
        self._aplicar_entrada(self.history.revert(entry_id))
```

- [x] **Step 4: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS.

- [x] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_bins.py
git commit -m "⌘Z no se salta un renglon bloqueado

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Barrido final — el caso del spec, y lo que NO cambia

**Files:**
- Test: `tests/ui/test_main_window_bins.py`
- Modify: `README.md`, `docs/superpowers/CONTEXTO-Y-METAS.md`

- [x] **Step 1: Escribe la prueba del caso completo**

```python
def test_el_caso_del_spec_de_punta_a_punta(qtbot):
    """Lo que Bruno vivió el 2026-08-18, tal cual: clasificar, arrastrar sin
    querer, y apretar ⌘Z. Antes el clip se quedaba en el bin nuevo Y otro
    clip perdía su cuarto."""
    window = _ventana_con_bins(qtbot)
    for indice, tecla in ((0, "1"), (1, "1"), (2, "2")):
        window.select_clip(indice)
        window.handle_key_press(tecla)
    cuartos = [list(c.categoria_path) for c in window.clips]

    window._on_clips_movidos([0], "Card B")
    window.undo()

    assert window.bins.bin_de(0) == "Card A"
    assert [list(c.categoria_path) for c in window.clips] == cuartos


def test_quitar_un_bin_sigue_vaciando_el_historial(qtbot, monkeypatch):
    """No entra en este trabajo y tiene que seguir igual: sacar clips corre
    los numeros de todos los demas, y cada entrada habla por numero de clip.
    """
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)
    window = _ventana_con_bins(qtbot)
    window.select_clip(0)
    window.handle_key_press("1")
    assert window.history.entries()

    window._on_bin_quitado("Card A")

    assert window.history.entries() == []
```

Si el diálogo de confirmación de `_on_bin_quitado` usa otro método de `QMessageBox`, ajusta el `monkeypatch` a ese; búscalo con `grep -n "QMessageBox" src/clasificador_video/ui/main_window.py`.

- [x] **Step 2: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS.

- [x] **Step 3: Comprobación visual del renglón apagado**

No basta con que la prueba pase: hay que ver el pixel. Guarda esto en el scratchpad de la sesión (NO en el repo) y córrelo:

```python
import sys
from PySide6.QtWidgets import QApplication
from clasificador_video.history import HistoryEntry
from clasificador_video.ui import theme
from clasificador_video.ui.room_rail import RoomRail

app = QApplication([])
app.setStyleSheet(theme.build_stylesheet())
normal = HistoryEntry(etiqueta="Sala", detalle="→ 6 clips",
                      color=theme.room_color(0), antes={})
bloqueada = HistoryEntry(etiqueta="Card C", detalle="→ bin nuevo",
                         color=theme.bin_color(0), antes={}, bin_creado="Card C")
otra = HistoryEntry(etiqueta="Card B", detalle="→ 3 clips",
                    color=theme.bin_color(1), antes={}, bins_antes={0: "Card A"})
rail = RoomRail()
rail.resize(theme.RAIL_WIDTH, 600)
rail.set_history([normal, bloqueada, otra], {bloqueada.id: "ya tiene clips"})
rail.show()
for _ in range(8):
    app.processEvents()
rail.grab().save(sys.argv[1] + "/rail-bloqueado.png")
```

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python <ruta>/rail.py <ruta-del-scratchpad>
```

Abre el PNG con la herramienta de lectura de archivos. Confirma tres cosas a simple vista: el renglón de «Card C» se lee más apagado que los otros dos, su `↺` se ve inactivo, y los tres renglones siguen ahí —ninguno desapareció—.

- [x] **Step 4: Actualiza la documentación**

En `README.md`, en la sección de la hoja de contactos, después del párrafo del arrastre entre bins:

```markdown
Mover clips de bin, crear un bin y renombrarlo **se deshacen con `⌘Z`** y
aparecen en la lista del rail como cualquier otra acción. Un renglón que ya
no se puede cumplir —creaste un bin y ya le metiste clips— se ve apagado y
dice por qué, en vez de deshacer otra cosa.
```

En `docs/superpowers/CONTEXTO-Y-METAS.md`, en «Lo que falta», el punto 4 dice hoy que los bins no pasan por el historial. Bórralo de ahí y súbelo a una sección de lo hecho, con el porqué: era un `⌘Z` que revertía en silencio una acción anterior, no una función que faltaba.

- [x] **Step 5: Commit**

```bash
git add tests/ui/test_main_window_bins.py README.md docs/superpowers/CONTEXTO-Y-METAS.md
git commit -m "El caso del spec de punta a punta, y la documentacion al dia

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
