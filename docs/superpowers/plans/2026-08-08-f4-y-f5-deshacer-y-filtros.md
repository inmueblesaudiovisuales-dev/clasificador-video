# F4 y F5 del rediseño — Deshacer y filtros como cola — Implementation Plan

> **Para quien lo ejecute:** las tareas van con checkbox (`- [ ]`) y el test se
> escribe **antes** que la implementación, como en los dos planes anteriores.

**Goal:** cerrar la única promesa rota que le queda a la app —`⌘Z` anunciado y
ausente— con un historial visible y reversible (F4), y convertir los filtros en
la **cola de navegación**, que es lo que cambia de verdad cómo se trabaja un
shooting de 128 clips (F5).

**Architecture:**

- **F4** mete la lógica en un módulo puro, `history.py`, sin nada de Qt: la
  pila, las entradas y qué campo cambió cada acción se pueden probar sin
  `qtbot`. `MainWindow` es quien aplica el estado guardado; el historial solo lo
  recuerda. Cada entrada guarda **únicamente los campos que esa acción tocó**,
  no el clip entero — es lo que hace que revertir una entrada vieja no pise una
  acción posterior sobre el mismo clip.
- **F5** mete la lógica en otro módulo puro, `filters.py`, que decide qué clips
  pasan el filtro y en qué orden. De ahí sale **una sola lista de índices** que
  alimenta tres cosas a la vez: qué se ve en la hoja, por dónde se mueven las
  flechas y qué dice el contador del visor. Que sea una sola lista es el punto:
  si la cola y lo que ves se calcularan por separado, se desincronizan.

**Tech Stack:** PySide6 6.11, pytest + pytest-qt. Los dos módulos nuevos son
Python puro: sus tests no necesitan `qtbot` ni pantalla.

**Referencias:**
- Comportamiento acordado: `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`
- Estado y huérfanos: `docs/superpowers/ANALISIS-2026-08-08-post-f3.md`
- Candados anti-deriva: `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md`

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q
```

Punto de partida: **335 tests en verde**, commit `abb7807`.

---

## Advertencias antes de empezar

1. **Las tres reglas de `ClipSheet` siguen vigentes y la F5 las estresa.**
   Filtrar **no puede** reordenar ni recrear `item_widgets`: va indexada por
   índice de clip porque las miniaturas llegan de tres hilos en desorden. Se
   esconde con `setVisible(False)` y se saltea en `_relayout`; **nunca** se
   arma una lista nueva. Está en el docstring de la clase y tiene un SIGSEGV y
   un bug intermitente de miniaturas detrás.
2. **El historial NO se guarda en disco.** Es de la sesión abierta. Al reabrir
   se recupera el trabajo (eso ya lo hace el autosave) pero no el historial.
   Guardarlo obligaría a versionar el formato del `sesion.json` y no lo pidió
   nadie.
3. **El chip `★ solo destacados` del mockup no se construye en la F5.** El
   estado «destacado» no existe hasta la F7. Se deja el hueco.
4. **Los colores con alfa se piden a `theme.con_alfa_qss`**, nunca se escriben
   en el widget: el Candado 1 corre por expresión regular sobre el texto del
   archivo y falla incluso si el color está en un comentario.
5. **Cada fase deja la app funcionando.** La F4 puede partirse en commits —el
   módulo `history.py` sin conectar es un commit verde inofensivo— pero lo que
   ve el usuario cambia en un solo commit.

---

# FASE 4 — Deshacer, con historial visible

## Task 1: `history.py` — la pila, sin Qt

**Files:**
- Create: `src/clasificador_video/history.py`
- Test: `tests/test_history.py` (nuevo)

**Las tres decisiones de diseño de esta fase, y por qué:**

1. **Cada entrada guarda solo los campos que su acción tocó.** Si guardara el
   clip entero, revertir «Cocina → 6 clips» también borraría el pick que
   marcaste después sobre uno de esos seis. Con campos parciales, revertir una
   asignación de cuarto solo toca `categoria_path`.
2. **Una acción del usuario = una entrada, aunque toque seis clips.** Es lo que
   dice `DECISIONES.md` y es lo que hace que asignar en lote no sea una trampa:
   un gesto rápido que costara seis `⌘Z` sería peor que no tenerlo.
3. **Revertir funciona en cualquier fila, no solo en la de arriba.** También lo
   pide `DECISIONES.md` («`⌘Z` deshace la de arriba; el resto se revierte con
   un click»). Consecuencia asumida: si dos acciones tocaron **el mismo campo
   del mismo clip**, revertir la vieja gana sobre la nueva. Es lo que el usuario
   pidió al hacer click en esa fila; la alternativa —historial lineal, revertir
   solo desde arriba— contradice el documento.

- [x] **Step 1: Escribir los tests que fallan**

```python
# tests/test_history.py
from clasificador_video.history import History, HistoryEntry


def _entrada(etiqueta="Cocina", detalle="→ 1 clip", color="#c0885a", antes=None):
    return HistoryEntry(
        etiqueta=etiqueta, detalle=detalle, color=color,
        antes=antes if antes is not None else {0: {"categoria_path": []}},
    )


def test_la_entrada_mas_reciente_va_primera():
    """El historial se lee de arriba hacia abajo, como el del mockup."""
    h = History()
    h.push(_entrada("Cocina"))
    h.push(_entrada("Sala"))
    assert [e.etiqueta for e in h.entries()] == ["Sala", "Cocina"]


def test_deshacer_devuelve_la_ultima_y_la_saca():
    h = History()
    h.push(_entrada("Cocina"))
    h.push(_entrada("Sala"))
    assert h.undo_last().etiqueta == "Sala"
    assert [e.etiqueta for e in h.entries()] == ["Cocina"]


def test_deshacer_con_el_historial_vacio_no_revienta():
    assert History().undo_last() is None


def test_revertir_una_entrada_del_medio_la_saca_y_deja_el_resto():
    """DECISIONES.md: el resto se revierte con un click, no solo la de arriba."""
    h = History()
    a, b, c = _entrada("A"), _entrada("B"), _entrada("C")
    for e in (a, b, c):
        h.push(e)
    assert h.revert(b.id) is b
    assert [e.etiqueta for e in h.entries()] == ["C", "A"]


def test_revertir_una_entrada_que_ya_no_esta_devuelve_none():
    """Doble click en el mismo boton de revertir: la segunda no hace nada."""
    h = History()
    e = _entrada()
    h.push(e)
    h.revert(e.id)
    assert h.revert(e.id) is None


def test_cada_entrada_tiene_id_propio():
    a, b = _entrada(), _entrada()
    assert a.id != b.id


def test_una_accion_en_lote_es_UNA_entrada():
    """Deshacer seis clips asignados de una tiene que costar un ⌘Z, no seis:
    si costara seis, asignar en lote seria una trampa."""
    h = History()
    h.push(_entrada("Baño 1", "→ 6 clips",
                    antes={i: {"categoria_path": []} for i in range(6)}))
    assert len(h.entries()) == 1
    assert len(h.entries()[0].antes) == 6


def test_la_pila_tiene_techo_y_tira_lo_mas_viejo():
    """Sin techo, una sesion larga acumula memoria sin que nadie mire mas
    alla de las ultimas cinco filas."""
    h = History(limite=3)
    for i in range(5):
        h.push(_entrada(str(i)))
    assert [e.etiqueta for e in h.entries()] == ["4", "3", "2"]


def test_la_entrada_sabe_que_campos_restaurar():
    """Guardar el clip ENTERO haria que revertir 'Cocina -> 6 clips' borrara
    tambien el pick que marcaste despues sobre uno de esos seis."""
    e = _entrada(antes={3: {"flag": "none"}})
    assert e.antes == {3: {"flag": "none"}}
```

- [x] **Step 2: Implementar**

```python
# src/clasificador_video/history.py
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

LIMITE_POR_DEFECTO = 50
_ids = itertools.count(1)


@dataclass
class HistoryEntry:
    """Una acción del usuario, con lo justo para deshacerla.

    `antes` es `{indice_de_clip: {campo: valor_anterior}}` -- SOLO los campos
    que esta acción tocó. Guardar el clip entero haría que revertir una
    asignación de cuarto pisara el pick que se marcó después.
    """

    etiqueta: str          # "Baño 1", "Reject", "IN/OUT"
    detalle: str           # "→ 6 clips", "→ clip 086"
    color: str             # cuadrito de la fila: color de cuarto o de estado
    antes: dict[int, dict]
    rooms_antes: list[str] | None = None   # solo al borrar un cuarto
    id: int = field(default_factory=lambda: next(_ids))


class History:
    def __init__(self, limite: int = LIMITE_POR_DEFECTO):
        self._entries: list[HistoryEntry] = []   # la más reciente, primera
        self._limite = limite

    def push(self, entry: HistoryEntry) -> None:
        self._entries.insert(0, entry)
        del self._entries[self._limite:]

    def undo_last(self) -> HistoryEntry | None:
        return self._entries.pop(0) if self._entries else None

    def revert(self, entry_id: int) -> HistoryEntry | None:
        for i, entrada in enumerate(self._entries):
            if entrada.id == entry_id:
                return self._entries.pop(i)
        return None

    def entries(self) -> list[HistoryEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
```

- [x] **Step 3: Verificar** — `pytest tests/test_history.py -q` en verde.

---

## Task 2: El panel de historial en el rail

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py`
- Modify: `src/clasificador_video/ui/theme.py::build_stylesheet`
- Test: `tests/ui/test_room_rail.py`

Va al pie del rail, entre la lista de cuartos y el botón de importar, con
`border-top` fino — igual que el `.history` del mockup. Cuatro filas visibles;
la de arriba lleva el tinte ámbar y el borde izquierdo del `.hist-row.top`.

Cada fila: cuadrito de color, `**Etiqueta** → detalle` elidido, y `↺`.

- [x] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_room_rail.py  (agregar)

def _entrada(etiqueta="Cocina", detalle="→ 6 clips", color=None):
    from clasificador_video.history import HistoryEntry
    return HistoryEntry(etiqueta=etiqueta, detalle=detalle,
                        color=color or theme.room_color(0), antes={})


def test_el_historial_muestra_lo_ultimo_arriba(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada("Sala"), _entrada("Cocina")])
    assert [f.etiqueta for f in rail.history_rows] == ["Sala", "Cocina"]


def test_la_primera_fila_va_resaltada_porque_es_la_que_deshace_cmd_z(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada("Sala"), _entrada("Cocina")])
    assert rail.history_rows[0].property("top") is True
    assert rail.history_rows[1].property("top") is False


def test_el_historial_no_muestra_mas_de_cuatro_filas(qtbot):
    """El rail mide 200 px: mas filas empujan la lista de cuartos."""
    from clasificador_video.ui.room_rail import MAX_HISTORIAL
    rail = _rail(qtbot)
    rail.set_history([_entrada(str(i)) for i in range(10)])
    assert len(rail.history_rows) == MAX_HISTORIAL


def test_cada_fila_lleva_el_color_de_su_accion(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada(color=theme.REJECT_COLOR)])
    assert theme.REJECT_COLOR in rail.history_rows[0].swatch.styleSheet()


def test_revertir_una_fila_emite_su_id(qtbot):
    rail = _rail(qtbot)
    entrada = _entrada()
    rail.set_history([entrada])
    with qtbot.waitSignal(rail.revert_requested) as blocker:
        rail.history_rows[0].undo_button.click()
    assert blocker.args == [entrada.id]


def test_sin_historial_el_panel_se_esconde_entero(qtbot):
    """Un panel vacio con su linea separadora es ruido: al abrir la app no
    hay nada que deshacer."""
    rail = _rail(qtbot)
    rail.set_history([])
    assert rail.history_panel.isHidden()


def test_un_texto_largo_se_elide_en_vez_de_desbordar(qtbot):
    rail = _rail(qtbot)
    rail.set_history([_entrada("Recámara principal con vestidor")])
    rail.show()
    qtbot.waitExposed(rail)
    assert rail.history_rows[0].what_label.text().endswith("…")
```

- [x] **Step 2: Implementar** — `_FilaHistorial(QWidget)` con `swatch`,
  `what_label` (`ElidedLabel`) y `undo_button` (`QPushButton` con `↺`,
  `setFocusPolicy(Qt.NoFocus)` — o el espacio activa el botón enfocado en vez
  de reproducir). `MAX_HISTORIAL = 4`. `RoomRail.set_history(entries)` y la
  señal `revert_requested = Signal(int)`.

  Tokens nuevos en `theme.py`: el tinte de la fila de arriba sale de
  `con_alfa_qss(CURRENT_COLOR, 18)` y su borde de `con_alfa_qss(CURRENT_COLOR, 255)`;
  **no** se escriben a mano.

- [x] **Step 3: Verificar** — tests en verde y **mirar** el rail con el arnés.

---

## Task 3: `MainWindow` registra y deshace

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

**Qué acciones dejan entrada** (y qué campo guarda cada una):

| Acción | Campo guardado | Etiqueta / color |
|---|---|---|
| Asignar cuarto (1 o N clips) | `categoria_path` | nombre del cuarto / su color |
| `P` / `X` | `flag` | `Pick` / `Reject`, su color de estado |
| `I` / `O` / `U` | `in_frame`, `out_frame` | `IN/OUT` / `TRIM_COLOR` |
| Borrar un cuarto del rail | `categoria_path` **+ `rooms_antes`** | `Cuarto borrado` / su color |

**Qué NO deja entrada, a propósito**: crear, renombrar y mover cuartos. No
pierden datos y se revierten a mano en un gesto (borrar el que creaste,
renombrar de vuelta). Borrar sí entra porque **desclasifica todos sus clips**:
es la única operación del rail que destruye trabajo.

- [x] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_main_window.py  (agregar)

def test_asignar_un_cuarto_deja_entrada_en_el_historial(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    entrada = window.history.entries()[0]
    assert entrada.etiqueta == "Cocina"
    assert "1 clip" in entrada.detalle


def test_deshacer_devuelve_el_clip_a_sin_clasificar(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.undo()
    assert window.clips[0].categoria_path == []
    assert window.history.entries() == []


def test_deshacer_una_asignacion_en_lote_es_UNA_sola_accion(qtbot):
    """Equivocarse asignando seis clips a la vez es un error seis veces mas
    caro: tiene que costar un ⌘Z, no seis."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 7)])
    window.select_clip(0)
    window.select_current_group()
    window.handle_key_press("1")
    assert "6 clips" in window.history.entries()[0].detalle
    window.undo()
    assert [c.categoria_path for c in window.clips] == [[]] * 6


def test_deshacer_un_pick_no_toca_el_cuarto(qtbot):
    """Cada entrada guarda SOLO el campo que su accion cambio."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.handle_key_press("p")
    window.undo()
    assert window.clips[0].flag == "none"
    assert window.clips[0].categoria_path == ["Cocina"]   # sobrevive


def test_revertir_una_entrada_vieja_no_pisa_una_accion_posterior(qtbot):
    """El caso que obliga a guardar campos parciales: asignar cuarto a seis,
    marcar pick en uno, revertir la asignacion -> el pick sigue ahi."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.select_current_group()
    window.handle_key_press("1")            # los dos a Cocina
    asignacion = window.history.entries()[0]
    window.clip_sheet.set_selected({0})
    window.select_clip(0)
    window.handle_key_press("p")            # pick en el primero
    window.revert(asignacion.id)
    assert window.clips[0].categoria_path == []
    assert window.clips[0].flag == "pick"   # NO se lo llevo puesto


def test_deshacer_in_out_restaura_los_dos_extremos(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip()])
    window.video_widget.player._mpv.time_pos = 2.0
    window.handle_key_press("i")
    window.handle_key_press("o")
    window.undo()                            # deshace el OUT
    assert window.clips[0].out_frame is None
    assert window.clips[0].in_frame is not None


def test_borrar_un_cuarto_se_puede_deshacer_entero(qtbot):
    """Es la unica operacion del rail que destruye trabajo: desclasifica
    todos sus clips."""
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    window.room_rail.room_removed.emit("Cocina")
    assert window.clips[0].categoria_path == []
    window.undo()
    assert window.room_selection.active_rooms() == ["Cocina", "Sala"]
    assert window.clips[0].categoria_path == ["Cocina"]


def test_crear_y_renombrar_no_ensucian_el_historial(qtbot):
    """No pierden datos y se revierten a mano en un gesto."""
    window = _window(qtbot, rooms=("Cocina",))
    window.room_rail.room_created.emit("Alberca")
    window.room_rail.room_renamed.emit("Alberca", "Piscina")
    window.room_rail.room_moved.emit("Piscina", -1)
    assert window.history.entries() == []


def test_deshacer_sin_nada_que_deshacer_no_revienta(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.undo()


def test_el_historial_se_ve_en_el_rail(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip()])
    window.handle_key_press("1")
    assert window.room_rail.history_rows[0].etiqueta == "Cocina"
```

- [x] **Step 2: Implementar**

El helper que hace todo el trabajo, para que ninguna acción se olvide de
registrar:

```python
    def _registrar(self, etiqueta: str, detalle: str, color: str,
                   clips: list[int], campos: tuple[str, ...]) -> None:
        """Guarda el estado ANTERIOR de `campos` en `clips`. Se llama SIEMPRE
        antes de mutar, nunca después."""
        antes = {
            i: {campo: _copiar(getattr(self.clips[i], campo)) for campo in campos}
            for i in clips if 0 <= i < len(self.clips)
        }
        self.history.push(HistoryEntry(etiqueta, detalle, color, antes))
        self.room_rail.set_history(self.history.entries())
```

`undo()` y `revert(id)` aplican `entrada.antes` con `setattr`, restauran
`rooms_antes` si lo hay, y refrescan. `⌘Z` se registra en `_install_shortcuts`
con `QKeySequence.StandardKey.Undo`, que ya es `⌘Z` en macOS.

**Ojo con `categoria_path`**: es una lista. Guardar la referencia y no una
copia haría que el "antes" mutara junto con el clip y deshacer no hiciera nada.
De ahí el `_copiar`.

- [x] **Step 3: Verificar** — suite en verde y prueba a mano: asignar seis
  clips, deshacer, comprobar que vuelven los seis.

---

## Task 4: El indicador de deshacer en la columna de herramientas

**Files:**
- Modify: `src/clasificador_video/ui/tool_column.py`
- Modify: `src/clasificador_video/ui/theme.py::build_stylesheet`
- Test: `tests/ui/test_tool_column.py`

El mockup tiene, bajo un separador, dos herramientas más: la de buscar (`⏎`,
que es de la F7) y la de deshacer (`↺ ⌘Z`). La F4 agrega **solo la segunda**.

**Desviación consciente**: el resto de la columna son *indicadores*, no
botones, porque en una app de teclado un botón que nadie clickea es ancho
decorativo. El de deshacer **sí es un botón**: es la única acción de la columna
que no refleja un estado del clip, y tener dónde hacer click cuando dudas de
qué deshace `⌘Z` vale los 40 px.

- [x] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_tool_column.py  (agregar)

def test_la_columna_tiene_boton_de_deshacer(qtbot):
    col = _column(qtbot)
    assert col.undo_button.key.text() == "⌘Z"


def test_el_boton_de_deshacer_emite_su_senal(qtbot):
    col = _column(qtbot)
    with qtbot.waitSignal(col.undo_requested):
        col.undo_button.click()


def test_deshacer_se_apaga_cuando_no_hay_nada_que_deshacer(qtbot):
    """Un boton que no hace nada y no lo dice es peor que no tenerlo."""
    col = _column(qtbot)
    col.set_can_undo(False)
    assert not col.undo_button.isEnabled()
    col.set_can_undo(True)
    assert col.undo_button.isEnabled()


def test_el_boton_no_se_roba_el_foco(qtbot):
    """Con foco, la barra espaciadora activaria el boton en vez de
    reproducir el video."""
    from PySide6.QtCore import Qt
    assert _column(qtbot).undo_button.focusPolicy() == Qt.FocusPolicy.NoFocus
```

- [x] **Step 2: Implementar** — un separador (`toolDivider`) y el botón.
  `MainWindow` conecta `undo_requested` a `undo()` y llama a `set_can_undo`
  cada vez que cambia el historial.

- [x] **Step 3: Verificar.**

## Task 5: Cierre de la F4

- [x] Suite en verde.
- [x] **`grep` del renglón de la lista de ejecución**: «Mención de `Ctrl+Z` sin
      implementación» queda tachado.
- [x] Campos que nadie lee, buscados con `grep`, en `HistoryEntry` y en las
      filas del panel.
- [x] Arnés corrido, imagen **mirada**, y recorte ampliado del rail con
      historial contra el del mockup.
- [x] Commit en español mexicano.

---

# FASE 5 — Los filtros son la cola de navegación

> «Los filtros no cambian solo **lo que ves**: cambian **por dónde te
> mueves**.» — `DECISIONES.md`

## Task 6: `filters.py` — quién pasa el filtro, sin Qt

**Files:**
- Create: `src/clasificador_video/filters.py`
- Test: `tests/test_filters.py` (nuevo)

Dos grupos, como el mockup:

```
MOSTRAR   [todos] [sin clasificar] [clasificados]
ESTADO    [todos] [solo picks] [ocultar rejects] [sin marcar]
```

Más el campo de búsqueda, que filtra por **nombre de archivo o nombre de
cuarto**. La búsqueda **ignora acentos**: escribir `recamara` tiene que
encontrar `Recámara 1`, o en un teclado apurado no sirve para nada.

El chip `★ solo destacados` del mockup **no se construye**: no existe el estado
hasta la F7.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_filters.py
from pathlib import Path

from clasificador_video.filters import FilterState, contar, cola
from clasificador_video.manifest import Clip


def _clip(n, cuarto=None, flag="none"):
    return Clip(orden=n, ruta=Path(f"/tmp/C{n:04d}.MP4"),
                categoria_path=[cuarto] if cuarto else [], fps=30.0, flag=flag)


CLIPS = [
    _clip(1, "Cocina", "pick"),
    _clip(2, "Recámara 1"),
    _clip(3, None, "reject"),
    _clip(4, None),
]


def test_sin_filtros_la_cola_es_todo_en_orden():
    assert cola(CLIPS, FilterState()) == [0, 1, 2, 3]


def test_sin_clasificar_deja_solo_los_que_no_tienen_cuarto():
    assert cola(CLIPS, FilterState(mostrar="sin_clasificar")) == [2, 3]


def test_clasificados_deja_solo_los_que_si():
    assert cola(CLIPS, FilterState(mostrar="clasificados")) == [0, 1]


def test_solo_picks():
    assert cola(CLIPS, FilterState(estado="solo_picks")) == [0]


def test_ocultar_rejects_saca_los_descartados():
    assert cola(CLIPS, FilterState(estado="ocultar_rejects")) == [0, 1, 3]


def test_sin_marcar_deja_los_que_no_son_pick_ni_reject():
    assert cola(CLIPS, FilterState(estado="sin_marcar")) == [1, 3]


def test_los_dos_grupos_se_combinan():
    estado = FilterState(mostrar="sin_clasificar", estado="ocultar_rejects")
    assert cola(CLIPS, estado) == [3]


def test_la_busqueda_encuentra_por_nombre_de_archivo():
    assert cola(CLIPS, FilterState(busqueda="C0002")) == [1]


def test_la_busqueda_encuentra_por_nombre_de_cuarto():
    assert cola(CLIPS, FilterState(busqueda="cocina")) == [0]


def test_la_busqueda_ignora_acentos():
    """En un teclado apurado nadie escribe `Recámara` con acento."""
    assert cola(CLIPS, FilterState(busqueda="recamara")) == [1]
    assert cola(CLIPS, FilterState(busqueda="RECÁMARA")) == [1]


def test_la_busqueda_en_blanco_no_filtra():
    assert cola(CLIPS, FilterState(busqueda="   ")) == [0, 1, 2, 3]


def test_los_conteos_alimentan_los_numeros_de_los_chips():
    c = contar(CLIPS)
    assert c["todos"] == 4
    assert c["sin_clasificar"] == 2
    assert c["clasificados"] == 2
    assert c["solo_picks"] == 1
    assert c["ocultar_rejects"] == 1     # cuantos SE OCULTAN: el chip dice −1
    assert c["sin_marcar"] == 2


def test_un_estado_sin_filtros_lo_dice():
    """De esto depende que el visor diga `87 / 128` o `3 de 12 en la cola`."""
    assert FilterState().esta_filtrando() is False
    assert FilterState(mostrar="sin_clasificar").esta_filtrando() is True
    assert FilterState(busqueda="x").esta_filtrando() is True


def test_la_cola_nunca_reordena_los_clips():
    """Es el orden de rodaje: reordenar romperia la nocion de `el anterior`,
    que es de lo que vive la tecla S de la F7."""
    revueltos = FilterState(mostrar="clasificados")
    assert cola(CLIPS, revueltos) == sorted(cola(CLIPS, revueltos))
```

- [ ] **Step 2: Implementar** — `FilterState` como `dataclass` con
  `mostrar`, `estado`, `busqueda`; `cola(clips, state) -> list[int]`;
  `contar(clips) -> dict[str, int]`. La normalización de acentos con
  `unicodedata.normalize("NFD", …)` y descarte de las marcas diacríticas.

- [ ] **Step 3: Verificar.**

---

## Task 7: La barra de filtros en la hoja

**Files:**
- Modify: `src/clasificador_video/ui/clip_sheet.py`
- Modify: `src/clasificador_video/ui/theme.py::build_stylesheet`
- Test: `tests/ui/test_clip_sheet.py`

El encabezado de la hoja pasa de una fila a dos, como el `.sheet-head` del
mockup: arriba el título, el campo de búsqueda y el hint; abajo la barra de
filtros y el chip de cola.

**No se construyen los dos iconos de vista** del mockup: no hay ninguna
decisión detrás de ellos (ver el análisis post-F3 §1.9).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_clip_sheet.py  (agregar)

def test_los_chips_muestran_su_conteo(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None), _clip(2, None)])
    sheet.set_counts({"todos": 3, "sin_clasificar": 2, "clasificados": 1,
                      "solo_picks": 0, "ocultar_rejects": 0, "sin_marcar": 3})
    assert "2" in sheet.chips["sin_clasificar"].text()


def test_prender_un_chip_emite_el_estado_del_filtro(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    with qtbot.waitSignal(sheet.filters_changed) as blocker:
        sheet.chips["sin_clasificar"].click()
    assert blocker.args[0].mostrar == "sin_clasificar"


def test_los_chips_de_un_grupo_son_excluyentes(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.chips["sin_clasificar"].click()
    sheet.chips["clasificados"].click()
    assert sheet.chips["sin_clasificar"].isChecked() is False
    assert sheet.chips["clasificados"].isChecked() is True


def test_para_apagar_un_filtro_se_clickea_Todos(qtbot):
    """Verificado contra Qt: en un QButtonGroup exclusivo, volver a clickear
    el chip activo NO lo apaga. Por eso cada grupo tiene su chip `Todos` --
    el mockup ya lo trae-- y no hay forma de quedarse sin ninguno prendido."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.chips["sin_clasificar"].click()
    sheet.chips["sin_clasificar"].click()
    assert sheet.chips["sin_clasificar"].isChecked() is True
    sheet.chips["todos"].click()
    assert sheet.chips["sin_clasificar"].isChecked() is False


def test_los_dos_grupos_son_independientes(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    sheet.chips["sin_clasificar"].click()
    sheet.chips["solo_picks"].click()
    assert sheet.chips["sin_clasificar"].isChecked() is True


def test_escribir_en_la_busqueda_emite_el_estado(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    with qtbot.waitSignal(sheet.filters_changed) as blocker:
        sheet.search_input.setText("coci")
    assert blocker.args[0].busqueda == "coci"


def test_el_chip_de_cola_solo_se_ve_cuando_hay_filtro(qtbot):
    """Sin filtro, las flechas recorren todo y el chip mentiria."""
    sheet = _sheet(qtbot, [_clip(0, "Sala")])
    assert sheet.queue_chip.isHidden()
    sheet.set_queue_size(12, filtrando=True)
    assert not sheet.queue_chip.isHidden()
    assert "12" in sheet.queue_chip.text()


def test_no_se_construyen_los_iconos_de_vista(qtbot):
    """El mockup los dibuja pero no hay ninguna decision detras: no existe
    una vista de lista en DECISIONES.md (ver analisis post-F3 §1.9)."""
    assert not hasattr(_sheet(qtbot, []), "view_toggle")
```

- [ ] **Step 2: Implementar** — `_Chip(QPushButton)` chequeable, agrupados en
  dos `QButtonGroup` exclusivos; `search_input` (`QLineEdit` con placeholder
  `Buscar clip o cuarto…`); `queue_chip`; señal
  `filters_changed = Signal(object)` que emite el `FilterState`.

- [ ] **Step 3: Verificar** — tests, arnés y recorte del encabezado.

---

## Task 8: Esconder sin reordenar

**Files:**
- Modify: `src/clasificador_video/ui/clip_sheet.py`
- Test: `tests/ui/test_clip_sheet.py`

**La parte con más riesgo de toda la fase.** `item_widgets` va indexada por
índice de clip; filtrar **no puede** tocar esa lista. Se esconde con
`setVisible(False)` y se saltea en `_relayout`; los bloques que quedan sin
tarjetas visibles se esconden enteros.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_clip_sheet.py  (agregar)

def test_filtrar_esconde_pero_NO_reordena_item_widgets(qtbot):
    """Regla 1: las miniaturas se entregan con item_widgets[indice_de_clip] y
    llegan de tres hilos en desorden. Reordenar la lista las haria aterrizar
    en la tarjeta equivocada, de forma intermitente."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None), _clip(2, "Sala")])
    antes = list(sheet.item_widgets)
    sheet.set_visible_indices([1])
    assert sheet.item_widgets == antes
    assert sheet.item_widgets[1].isVisible()
    assert not sheet.item_widgets[0].isVisible()


def test_filtrar_no_borra_las_miniaturas_ya_cargadas(qtbot):
    """Regla 2: esconder no es reconstruir."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, None)])
    sheet.item_widgets[0].set_pixmap(_pixmap())
    sheet.set_visible_indices([1])
    sheet.set_visible_indices([0, 1])
    assert sheet.item_widgets[0].has_pixmap()


def test_un_grupo_que_queda_vacio_por_el_filtro_se_esconde(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Cocina")])
    sheet.set_visible_indices([1])
    visibles = [b.titulo for b in sheet._ordered_blocks() if not b.isHidden()]
    assert visibles == ["Cocina"]


def test_el_conteo_del_encabezado_cuenta_lo_visible(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala")])
    sheet.set_visible_indices([0])
    bloques = {b.titulo: b for b in sheet._ordered_blocks()}
    assert bloques["Sala"].count_label.text() == "1"


def test_cmd_a_selecciona_solo_lo_visible_del_grupo(qtbot):
    """Con un filtro puesto, seleccionar el grupo entero incluiria clips que
    no estas viendo -- y despues les asignarias un cuarto sin querer."""
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala"), _clip(2, "Sala")])
    sheet.set_visible_indices([0, 2])
    sheet.set_current(0)
    sheet.select_current_group()
    assert sheet.selected_indices() == [0, 2]
```

- [ ] **Step 2: Implementar** — `set_visible_indices(indices)` guarda un
  `set`, esconde las tarjetas que no están **y llama a `_relayout`**;
  `_relayout` saltea las escondidas al asignar fila y columna;
  `select_current_group` lo respeta.

  > **Verificado ejecutando: esconder NO alcanza.** Un `QGridLayout` deja el
  > hueco donde estaba la tarjeta escondida —medido: las posiciones siguen
  > siendo `(0,0) (0,1) (0,2) (0,3)` con un agujero en el medio—. Re-colocar
  > salteando las escondidas sí compacta, y de paso las saca del layout. Por
  > eso `set_visible_indices` **tiene** que disparar `_relayout`; si alguien lo
  > «optimiza» quitándolo, la hoja queda con agujeros.

- [ ] **Step 3: Verificar.**

---

## Task 9: La cola manda en las flechas

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Modify: `src/clasificador_video/ui/status_bar.py`
- Test: `tests/ui/test_main_window.py`, `tests/ui/test_status_bar.py`

Aquí se junta todo. **Una sola lista de índices** alimenta la hoja, las flechas
y el contador del visor.

**Cuatro comportamientos que hay que acertar:**

1. `←/→` se mueven **dentro de la cola**, no sobre los 128.
2. Al resolver un clip, **sale de la cola** — y las flechas tienen que seguir
   funcionando desde donde quedó, aunque el clip actual ya no esté en la cola.
3. El visor dice `3 de 12 en la cola` **cuando hay filtro**; sin filtro sigue
   diciendo `87 / 128`, que es lo que sirve cuando no estás filtrando.
4. El aviso `12 sin clasificar` de la barra de estado es **clickeable**: es,
   literalmente, el botón de «sigue trabajando».

**Y una que estaba perdida** (hallazgo #10 del análisis post-F3): la tabla de
teclado dice **`1`–`9` = «asignar cuarto y avanzar»**, y hoy asigna sin
avanzar. Se implementa aquí porque «avanzar» significa «el siguiente de la
cola», que es justo lo que esta fase construye. **Solo avanza cuando se actúa
sobre un clip**: con seis seleccionados, avanzar sería un salto sin sentido.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_main_window.py  (agregar)

def _cuatro(window):
    window.load_clips([_clip(1, "Cocina"), _clip(2), _clip(3, "Cocina"), _clip(4)])


def test_las_flechas_recorren_solo_la_cola_filtrada(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    window.select_clip(1)
    window.handle_arrow("next")
    assert window.current_index == 3      # se salta el 2, que esta clasificado


def test_al_final_de_la_cola_la_flecha_no_se_va_del_borde(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    window.select_clip(3)
    window.handle_arrow("next")
    assert window.current_index == 3


def test_si_el_clip_actual_no_esta_en_la_cola_la_flecha_va_al_siguiente_que_si(qtbot):
    """Pasa siempre que resuelves un clip: sale de la cola y el «actual» deja
    de pertenecer a ella. La flecha tiene que seguir desde ahi, no trabarse.

    Se prueba con `select_clip` a proposito, y no clasificando: clasificar YA
    avanza solo, y el test pasaria sin que la logica de la flecha exista.
    """
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))   # cola = [1, 3]
    window.select_clip(0)                                       # el 0 no esta
    window.handle_arrow("next")
    assert window.current_index == 1
    window.select_clip(2)                                       # el 2 tampoco
    window.handle_arrow("prev")
    assert window.current_index == 1


def test_asignar_un_cuarto_avanza_al_siguiente(qtbot):
    """DECISIONES.md: `1`-`9` es «asignar cuarto y avanzar»."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)
    window.handle_key_press("1")
    assert window.current_index == 1


def test_asignar_en_lote_NO_avanza(qtbot):
    """Con seis seleccionados, avanzar es un salto sin sentido."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)
    window.select_current_group()
    window.handle_key_press("1")
    assert window.current_index == 0


def test_pick_no_avanza(qtbot):
    """Solo los cuartos avanzan: marcar pick es lo ultimo que haces sobre un
    clip que estas mirando, y avanzar te sacaria de el."""
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)
    window.handle_key_press("p")
    assert window.current_index == 0


def test_el_visor_dice_la_posicion_en_la_cola_cuando_hay_filtro(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    window.select_clip(3)
    assert "2 de 2 en la cola" in window.video_stage.file_label.text()


def test_sin_filtro_el_visor_sigue_diciendo_el_total(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.select_clip(0)
    assert "1 / 4" in window.video_stage.file_label.text()


def test_el_aviso_de_sin_clasificar_aplica_el_filtro_al_clickearlo(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.status_bar.unclassified_clicked.emit()
    assert window.filters.mostrar == "sin_clasificar"


def test_la_hoja_solo_muestra_la_cola(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    _cuatro(window)
    window.set_filters(FilterState(mostrar="sin_clasificar"))
    visibles = [i for i, c in enumerate(window.clip_sheet.item_widgets) if c.isVisible()]
    assert visibles == [1, 3]
```

```python
# tests/ui/test_status_bar.py  (agregar)

def test_el_aviso_de_sin_clasificar_es_clickeable(qtbot):
    """Es, literalmente, el boton de «sigue trabajando»."""
    barra = _status_bar(qtbot)
    barra.set_unclassified(12)
    assert "click para filtrarlos" in barra.unclassified_label.text()
    with qtbot.waitSignal(barra.unclassified_clicked):
        barra.unclassified_label.click()


def test_sin_pendientes_el_aviso_desaparece(qtbot):
    barra = _status_bar(qtbot)
    barra.set_unclassified(0)
    assert barra.unclassified_label.text() == ""
```

- [ ] **Step 2: Implementar** — `MainWindow.filters` (`FilterState`),
  `set_filters()`, y `_queue()` que devuelve `cola(self.clips, self.filters)`.
  `handle_arrow` se mueve sobre esa lista; si el índice actual no está en ella,
  busca el siguiente (o anterior) mayor (o menor) que él. El aviso de la barra
  de estado pasa de `QLabel` a un botón plano con `unclassified_clicked`.

  > **Ojo**: `_bulk_targets` tiene que filtrar por lo visible también, o una
  > selección vieja escondida por un filtro recibiría la asignación sin que la
  > veas.

- [ ] **Step 3: Verificar** — suite en verde y prueba a mano del flujo entero:
  prender «Sin clasificar», recorrer con `→` clasificando, y ver que la cola se
  vacía y el chip llega a cero.

## Task 10: Cierre de la F5

- [ ] Suite en verde.
- [ ] Campos y métodos que nadie lee, buscados con `grep`.
- [ ] Arnés corrido, imagen **mirada**, y recortes del encabezado de la hoja y
      de la barra de estado contra el mockup.
- [ ] Punto de control: rehacer el análisis antes de planear la F6 y la F7.
- [ ] Commit en español mexicano.

---

# Lo que NO entra en estas dos fases

**Este registro existe para que nada se pierda entre fases**, que es
exactamente cómo se perdió la portada al 25% cuando la vieja F4 se disolvió
dentro de la F2. Cada renglón tiene dueño. Si una de estas fases se disuelve o
se reordena, **estos renglones se reasignan uno por uno**, no en bloque.

## F6 — Reproducción rápida *(la fase más grande del rediseño)*

| Qué | De dónde sale |
|---|---|
| Autoplay al cambiar de clip | `DECISIONES.md` |
| Velocidad `1× / 2× / 4×` con tecla, y su control sobre el video | `DECISIONES.md` + mockup `.seg.speed` |
| Arranque de la reproducción al 25% del clip | `DECISIONES.md` |
| Precarga del siguiente clip | `DECISIONES.md` |
| `,` `.` frame por frame | `DECISIONES.md` |
| **La forma de la barra de reproducción** (banda llena, zona de rango, manijas `I`/`O`) | mockup `.scrub` |
| **Pastilla `rango 07:04 · 212 f · total 18:11`** | mockup `.rangepill` |
| **Renglón de teclas bajo la barra** | mockup `.v-keys` |
| **Contador de frame `f 293`** | mockup `.fr` |
| **`espacio ▶ ‖`** al pie de la columna de herramientas | mockup `.toolhint` |
| Badge `▶ auto` sobre el video | mockup `.badge.auto` |
| `siguiente clip precargado ✓` en la barra de estado | mockup `.status` |
| El nombre de archivo como texto plano sobre un scrim, no en pastilla | mockup `.v-top` |

## F7 — El resto del teclado

| Qué | De dónde sale |
|---|---|
| `S` — igual al clip anterior, con su fila fija arriba del rail | `DECISIONES.md` + mockup `.same`, `.samecap` |
| Paleta `⏎` para buscar y crear cuartos | `DECISIONES.md` + mockup `.palette` |
| La herramienta de buscar (`⏎`) en la columna | mockup `.tool` |
| Estado **destacado** `⇧P`: badge, indicador, glifo `★` en la tarjeta, chip `dest.` en la leyenda del rail | `DECISIONES.md` + mockup |
| Chip `★ solo destacados` en la barra de filtros | mockup `.fchip` |
| `F` — solo video, sin chrome | `DECISIONES.md` |
| **Que `P` y `X` vuelvan a neutral al repetirse** | `DECISIONES.md` |

## F8 — Modo hoja y pincel

| Qué | De dónde sale |
|---|---|
| `⇥` alterna modo clip ↔ modo hoja, y el selector `Clip / Hoja` | `DECISIONES.md` + mockup `.modeswitch` |
| Hoja a pantalla completa, siete columnas | `DECISIONES.md` + mockup `.grid.wide` |
| Pincel de cuarto, con sus cinco requisitos | `DECISIONES.md` + mockup `.brush*` |
| `+` `−` tamaño de miniatura | `DECISIONES.md` + mockup `.zoomstep` |
| Marquesina de selección por arrastre | `DECISIONES.md` |
| `esc` vuelve a la hoja / limpia la selección | `DECISIONES.md` |
| Doble click abre el clip | `DECISIONES.md` |
| Transición animada entre modos | `DECISIONES.md` |
| La selección sobrevive el cruce entre modos | `DECISIONES.md` |
| **Barrita y timecode al escrubear una miniatura** | mockup `.hoverbar`, `.hovertc` |
| **Barra de acciones de selección múltiple** | mockup `.batch` |
| **Portada de la miniatura al 25% del clip** (hoy es el frame del medio) | `DECISIONES.md` |

## F9 — Proxies y orientación

| Qué | De dónde sale |
|---|---|
| Conectar `match_proxies()` a la importación | plan maestro |
| Badge `Proxy 1080p` sobre el video | mockup `.badge` |
| `proxies 1080p · 128/128` en la barra de estado | mockup `.status` |
| `orientacion` del manifest derivada del material, no hardcodeada | lista de ejecución — **el único renglón vivo** |

## F10 — Barrido final

| Qué |
|---|
| La lista de ejecución tiene que estar vacía |
| Comparación final de las dos pantallas, con recortes |
| Toda diferencia contra el mockup: arreglada, o escrita con su razón |

## Descartado a propósito

| Qué | Por qué |
|---|---|
| Los dos iconos de vista de la hoja (`.viewtoggle`) | No hay ninguna decisión detrás: `DECISIONES.md` no menciona una vista de lista. Construir un control porque está dibujado es cómo se llega a botones muertos |
| Forma de onda de audio, recorte automático de in/out, modo comparar, cinco estrellas | Evaluados y descartados con motivo escrito en `DECISIONES.md` |

---

## Auditoría de este plan — 2026-08-08

Hecha **ejecutando** un spike descartable (scratchpad de la sesión, no al
repo), no releyendo. Tres cosas cambiaron:

| # | Qué se creyó al escribir | Qué dijo Qt al ejecutarlo |
|---|---|---|
| 1 | Esconder una tarjeta bastaba para sacarla de la grilla | **No**: el `QGridLayout` deja el hueco. Hay que re-colocar salteando las escondidas — `set_visible_indices` tiene que llamar a `_relayout` |
| 2 | Volver a clickear el chip activo lo apagaría | **No**: en un `QButtonGroup` exclusivo el chip activo no se apaga solo. Apagar un filtro es clickear `Todos`, que el mockup ya trae. Se agregó un test que lo fija |
| 3 | Un test podía probar la flecha clasificando primero | **Se conflaban dos cosas**: clasificar ya avanza solo, así que el test pasaba sin que la lógica de la flecha existiera. Se reescribió con `select_clip` |

Lo que la ejecución **confirmó**: `QKeySequence.StandardKey.Undo` y
`SelectAll` existen y resuelven a `Ctrl+Z` / `Ctrl+A` en texto portable —que en
macOS es la tecla **⌘**, no Control—, y la normalización de acentos encuentra
`Recámara 1` escribiendo `recamara` y `Baño 2` escribiendo `bano`.

**Lo único que no se puede verificar desde aquí**: que `⌘Z` y `⌘A` respondan a
una tecla física. Un entorno `offscreen` no recibe pulsaciones reales. Queda
como **prueba a mano en la Mac de Bruno** al cerrar la F4 — y aplica también al
`⌘A` que ya se implementó.

---

## Resultado de la F4 — 2026-08-08

Implementada en el commit `d3c3519`. **377 tests en verde.**

**Lo que se desvió del plan**, para que el documento no mienta:

1. **Faltaba el encabezado `HISTORIAL ⌘Z`.** El plan describía las filas pero
   no la cabecera, que el mockup sí tiene (un `.rail-head` con `border-top`).
   Sin ella, las filas no dicen que la tecla las deshace. Salió de mirar el
   recorte, no de los tests.
2. **La fila necesitó dos etiquetas, no una.** El mockup pone *qué pasó* en
   negritas y claro, y *sobre qué* en gris. Con una sola etiqueta se pierde esa
   jerarquía, que es de lo que vive un panel que se lee de reojo. La etiqueta
   elide —el nombre del cuarto es lo que puede ser largo— y el detalle queda
   entero; la política `Maximum` es lo que impide que la etiqueta se coma el
   espacio libre y empuje el detalle contra el botón.
3. **El botón `↺` no se dibujaba.** La regla genérica de `QPushButton` trae
   `padding: 8px 14px`; heredarlo manda el `sizeHint` a 38×29 contra un botón
   fijo de 18×18 y el glifo se recorta entero. **Los tests no lo detectaban**:
   sin hoja de estilos aplicada, el `sizeHint` no dice nada. El test que quedó
   mira píxeles con el estilo puesto.

**Lo que confirmó la auditoría previa**: las tres correcciones que salieron del
spike seguían siendo ciertas al implementar.

**Pendiente de prueba a mano en la Mac de Bruno**: que `⌘Z` y `⌘A` respondan a
la tecla física. Un entorno `offscreen` no recibe pulsaciones reales.
