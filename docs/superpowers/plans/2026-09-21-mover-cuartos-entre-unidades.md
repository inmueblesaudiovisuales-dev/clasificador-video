# Mover cuartos entre unidades — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Arrastrar uno o varios cuartos ya clasificados del rail a la banda de OTRA unidad, moviéndolos con todos sus clips — reemplaza el camino actual, indirecto, de seleccionar clips uno por uno en la hoja con `⌘U`.

**Architecture:** El estado de "qué cuarto pertenece a qué unidad" ya vive en `MainWindow.room_selections: dict[str, RoomSelection]`, uno por unidad — este plan solo le suma un camino nuevo para moverse entre esos catálogos (hoy solo se puede crear/renombrar/borrar/reordenar dentro de uno). `RoomRail` gana selección múltiple, un botón para crear unidad y bandas colapsables — todo eso es estado de VISTA que vive en el propio widget, igual que ya vive el colapso de bins en `ClipSheet`. El choque de nombre y el deshacer se resuelven en `MainWindow`, reusando `History`/`HistoryEntry` (`⌘Z` ya existe, esto solo le agrega un tipo de entrada más).

**Tech Stack:** Python 3, PySide6 (Qt Widgets), pytest + pytest-qt (`qtbot`), `QT_QPA_PLATFORM=offscreen`.

**Spec:** `docs/superpowers/specs/2026-09-21-mover-cuartos-entre-unidades-design.md`

---

## Antes de empezar

Correr la suite completa una vez para tener una línea base:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Todos los comandos `pytest` de este plan asumen `QT_QPA_PLATFORM=offscreen` en el entorno — expórtalo una vez al arrancar la sesión:

```bash
export QT_QPA_PLATFORM=offscreen
```

---

### Task 1: `CuartoMovido` — el dato que hace falta para deshacer un move

**Files:**
- Modify: `src/clasificador_video/history.py`
- Test: `tests/test_history.py`

Antes de tocar `MainWindow`, `HistoryEntry` necesita un campo nuevo para recordar de dónde salió un cuarto movido entre unidades — el mismo criterio que ya usa `cuarto_borrado` para el borrado (`history.py:24-28`), pero con más datos: además de dónde reinsertarlo si deshaces, hace falta saber si el destino ya existía ahí (una fusión) para no borrarlo de más al deshacer.

- [ ] **Step 1: Leer el `HistoryEntry` actual para no romper su forma**

Ya lo tienes leído en esta conversación (`src/clasificador_video/history.py`). `cuarto_borrado: tuple[str, int] | None = None` es el precedente directo — mismo patrón, un campo nuevo con default `None`.

- [ ] **Step 2: Escribir el test que falla**

Agrega al final de `tests/test_history.py`:

```python
def test_cuarto_movido_por_default_es_none():
    from clasificador_video.history import HistoryEntry

    entrada = HistoryEntry("Cocina", "→ 6 clips", "#fff", {})
    assert entrada.cuarto_movido is None


def test_cuarto_movido_se_guarda_completo():
    from clasificador_video.history import CuartoMovido, HistoryEntry

    movimiento = CuartoMovido(
        nombre_origen="Cocina", posicion_origen=0, unidad_origen="Casa A",
        nombre_destino="Cocina 2", unidad_destino="Casa B", fue_fusion=False,
    )
    entrada = HistoryEntry("Cocina 2", "→ 6 clips", "#fff", {},
                            cuarto_movido=movimiento)
    assert entrada.cuarto_movido == movimiento
    assert entrada.cuarto_movido.fue_fusion is False
```

- [ ] **Step 3: Correr y confirmar que falla**

```bash
.venv/bin/pytest tests/test_history.py -k cuarto_movido -v
```
Expected: FAIL — `CuartoMovido` no existe todavía.

- [ ] **Step 4: Implementar**

En `src/clasificador_video/history.py`, justo antes de `@dataclass` / `class HistoryEntry:`, agrega:

```python
@dataclass(frozen=True)
class CuartoMovido:
    """Lo que hace falta para deshacer mover un cuarto a otra unidad.

    `nombre_destino` puede diferir de `nombre_origen`: si el choque de
    nombre se resolvio "renombrando", el cuarto viajo como "Cocina 2" (spec
    2026-09-21 S6). `fue_fusion` distingue el otro caso de choque: si el
    destino YA tenia un cuarto con ese nombre y la resolucion fue
    "fusionar", deshacer NO debe borrar ese nombre del catalogo destino --
    ya estaba ahi antes del move y sigue teniendo clips propios despues de
    deshacer. Sin fusion, el nombre en destino lo creo este move y deshacer
    si lo quita.
    """

    nombre_origen: str
    posicion_origen: int
    unidad_origen: str
    nombre_destino: str
    unidad_destino: str
    fue_fusion: bool
```

Y en `HistoryEntry`, junto a `cuarto_borrado`:

```python
    cuarto_borrado: tuple[str, int] | None = None
    # Mover un cuarto a otra unidad (spec 2026-09-21). Va aparte de
    # `cuarto_borrado`: mover no destruye nada -- solo un borrado deja
    # clips sin cuarto -- pero SI necesita, ademas de reinsertar el nombre
    # en su catalogo de origen, saber si hay que retirarlo del catalogo
    # destino al deshacer.
    cuarto_movido: "CuartoMovido | None" = None
```

- [ ] **Step 5: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/test_history.py -v
```
Expected: PASS, toda la suite de `test_history.py` sigue en verde.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/history.py tests/test_history.py
git commit -m "$(cat <<'EOF'
Sumar CuartoMovido a HistoryEntry para deshacer mover cuartos de unidad

Es el dato que hace falta para el spec 2026-09-21: ademas de donde
reinsertar el cuarto en su unidad de origen, guarda si el move fue una
fusion, porque ahi deshacer no debe borrar el nombre del catalogo
destino -- ya estaba ahi antes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Persistir qué unidades están colapsadas

**Files:**
- Modify: `src/clasificador_video/proyecto.py`
- Test: `tests/test_proyecto.py`

Mismo criterio que `agrupar_por_cuarto`/`modo_horizontal` (`proyecto.py:171-182`): una preferencia de vista que depende del shooting, no del día — se guarda en el documento del proyecto.

- [ ] **Step 1: Escribir el test que falla**

Agrega a `tests/test_proyecto.py`:

```python
def test_a_dict_guarda_unidades_colapsadas():
    from clasificador_video import proyecto

    data = proyecto.a_dict(
        proyecto="Casa Jardín", rooms=[], clips=[], bins=_bins_vacio(),
        tamanos={}, duraciones={}, rotaciones={},
        unidades_colapsadas=["Casa B"],
    )
    assert data["unidades_colapsadas"] == ["Casa B"]


def test_a_dict_unidades_colapsadas_por_default_vacio():
    from clasificador_video import proyecto

    data = proyecto.a_dict(
        proyecto="Casa Jardín", rooms=[], clips=[], bins=_bins_vacio(),
        tamanos={}, duraciones={}, rotaciones={},
    )
    assert data["unidades_colapsadas"] == []
```

Revisa el principio del archivo: si ya existe un helper `_bins_vacio()` (o equivalente, p. ej. `BinTree()` directo) para los tests de `a_dict`, reusa ese en vez de inventar uno nuevo — sigue el mismo patrón que los demás tests de `a_dict` en ese archivo.

- [ ] **Step 2: Correr y confirmar que falla**

```bash
.venv/bin/pytest tests/test_proyecto.py -k unidades_colapsadas -v
```
Expected: FAIL — `TypeError: a_dict() got an unexpected keyword argument 'unidades_colapsadas'`.

- [ ] **Step 3: Implementar**

En `src/clasificador_video/proyecto.py`, en la firma de `a_dict` (línea 128-138), agrega el parámetro junto a `rooms_por_unidad`:

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
           rooms_por_unidad: dict[str, list[str]] | None = None,
           unidades_colapsadas: list[str] | None = None) -> dict:
```

Y en el `return {...}`, junto a `"rooms_por_unidad"`:

```python
        "rooms_por_unidad": (
            {u: list(r) for u, r in rooms_por_unidad.items()}
            if rooms_por_unidad else {}
        ),
        # Que unidades estan colapsadas en el rail (spec 2026-09-21 S3).
        # Vista, no dato del clip -- mismo criterio que `agrupar_por_cuarto`
        # de arriba: vacio en todo proyecto que nunca colapsa nada.
        "unidades_colapsadas": list(unidades_colapsadas) if unidades_colapsadas else [],
```

- [ ] **Step 4: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/test_proyecto.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proyecto.py tests/test_proyecto.py
git commit -m "$(cat <<'EOF'
Persistir que unidades quedaron colapsadas en el rail

Mismo criterio que agrupar_por_cuarto: una preferencia de vista que
depende del shooting, no del dia. Vacio en todo proyecto que nunca
colapsa nada -- cero cambio para el resto.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `RoomRail` — botón "+" para crear unidad sin atajo

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py`
- Modify: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_room_rail_unidades.py`

- [ ] **Step 1: Escribir el test que falla**

Agrega a `tests/ui/test_room_rail_unidades.py`:

```python
def test_boton_nueva_unidad_emite_unit_created(rail):
    emitidos = []
    rail.unit_created.connect(emitidos.append)
    rail._crear_unidad("Casa C")
    assert emitidos == ["Casa C"]


def test_boton_nueva_unidad_ignora_nombre_vacio(rail):
    emitidos = []
    rail.unit_created.connect(emitidos.append)
    rail._crear_unidad("   ")
    assert emitidos == []
```

- [ ] **Step 2: Correr y confirmar que falla**

```bash
.venv/bin/pytest tests/ui/test_room_rail_unidades.py -k nueva_unidad -v
```
Expected: FAIL — `AttributeError: 'RoomRail' object has no attribute 'unit_created'`.

- [ ] **Step 3: Implementar**

En `src/clasificador_video/ui/room_rail.py`, en `RoomRail`, junto a los demás `Signal` (después de `room_created = Signal(str)`):

```python
    unit_created = Signal(str)
```

En `RoomRail.__init__`, dentro del bloque `# --- encabezado de cuartos ---` (línea ~538-561), agrega el botón al final de `el` (el `QHBoxLayout` del encabezado), después de `el.addWidget(self.find_hint)`:

```python
        self.new_unit_button = QPushButton("+")
        self.new_unit_button.setObjectName("newUnitButton")
        self.new_unit_button.setFixedSize(18, 18)
        self.new_unit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.new_unit_button.setToolTip("Nueva unidad")
        self.new_unit_button.clicked.connect(self._pedir_unidad_nueva)
        el.addWidget(self.new_unit_button)
```

Y junto a `_pedir_cuarto_nuevo`/`_crear_cuarto` (línea ~949-958), agrega el par gemelo:

```python
    def _pedir_unidad_nueva(self) -> None:
        nombre, ok = QInputDialog.getText(self, "Nueva unidad", "Nombre de la unidad:")
        if ok:
            self._crear_unidad(nombre)

    def _crear_unidad(self, nombre: str) -> None:
        """Aparte del dialogo, mismo criterio que `_crear_cuarto`: se puede
        probar sin abrir una ventana modal."""
        if nombre.strip():
            self.unit_created.emit(nombre.strip())
```

En `src/clasificador_video/ui/theme.py`, junto a la regla `QPushButton#newRoomRow` (línea ~488-500), agrega:

```python
    QPushButton#newUnitButton {{
        background-color: transparent;
        border: 1px solid {LINE};
        border-radius: {RADIUS_SM}px;
        color: {TEXT_3};
        font-size: {FONT_SMALL}px;
        font-weight: 600;
        padding: 0px;
    }}
    QPushButton#newUnitButton:hover {{
        background-color: {BG_SURFACE_1};
        color: {TEXT_2};
    }}
```

- [ ] **Step 4: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/ui/test_room_rail_unidades.py -v
```
Expected: PASS.

- [ ] **Step 5: Verificación visual**

Construye una `RoomRail` de prueba, `grab()`, guarda el PNG en el scratchpad de la sesión y léelo con la herramienta de lectura de archivos — confirma que el "+" se ve alineado con "⏎ buscar" en el encabezado de CUARTOS, sin desbordar el ancho de 200px del rail.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/room_rail.py src/clasificador_video/ui/theme.py tests/ui/test_room_rail_unidades.py
git commit -m "$(cat <<'EOF'
Sumar boton + para crear unidad sin depender de Ctrl+U

Bruno pidio poder crear unidades sin memorizarse un atajo. El boton
vive en el encabezado de CUARTOS, mismo criterio que "+ Nuevo cuarto"
de abajo -- solo crea, no activa la unidad.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `main_window.py` — wiring del botón "+"

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_unidades.py`

- [ ] **Step 1: Escribir el test que falla**

Agrega a `tests/ui/test_main_window_unidades.py`:

```python
def test_crear_unidad_desde_el_boton_del_rail_no_la_activa(main_window):
    main_window._on_unit_created_en_rail("Casa C")
    assert "Casa C" in main_window.unit_selection.active_rooms()
    assert main_window._unidad_activa is None
```

- [ ] **Step 2: Correr y confirmar que falla**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -k boton_del_rail -v
```
Expected: FAIL — `AttributeError`.

- [ ] **Step 3: Implementar**

En `src/clasificador_video/ui/main_window.py`, junto a `_on_unidad_creada_en_paleta` (línea ~1604-1606):

```python
    def _on_unidad_creada_en_paleta(self, nombre: str) -> None:
        self.unit_selection.add(nombre)
        self._activar_unidad(nombre)

    def _on_unit_created_en_rail(self, nombre: str) -> None:
        """El boton "+" del rail: crea SIN activar. A diferencia de la
        paleta (que crea Y activa, porque uno la abrio para seguir
        clasificando ya mismo), el boton es para el caso "quiero armar mis
        unidades antes de empezar" -- activar de mas aqui obligaria a
        desactivar despues de crear cada una."""
        self.unit_selection.add(nombre)
        self._refresh_rail()
        self._autosave()
```

Y en el bloque de conexiones del rail (línea ~985-994), agrega:

```python
        self.room_rail.unit_created.connect(self._on_unit_created_en_rail)
```

- [ ] **Step 4: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Conectar el boton + del rail para crear unidades

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `RoomRail` — bandas colapsables, con conteo

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py`
- Modify: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_room_rail_unidades.py`

`_BandaDeUnidad` gana una flecha (solo en unidades de verdad, no en el bloque migratorio "Sin unidad"), un conteo, y un clic que la colapsa/expande. El colapso vive DENTRO de `RoomRail` — mismo criterio que ya usa `ClipSheet._colapsados` para los bins (`clip_sheet.py:1970`): es estado de vista del widget, y `MainWindow` solo lo lee/escribe para guardar/restaurar (Task 6).

- [ ] **Step 1: Escribir los tests que fallan**

Agrega a `tests/ui/test_room_rail_unidades.py`:

```python
def test_banda_de_unidad_arranca_expandida(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    banda_casa_a = next(b for b in rail.unit_bands if b.nombre == "Casa A")
    assert banda_casa_a.chevron.text() == "▾"
    assert all(f.isVisible() for f in rail.rows_por_unidad["Casa A"])


def test_banda_sin_unidad_no_tiene_flecha(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    banda_sin_unidad = next(b for b in rail.unit_bands if b.nombre == "Sin unidad")
    assert banda_sin_unidad.chevron.text() == ""


def test_clic_en_la_banda_colapsa_y_esconde_sus_filas(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")

    banda_casa_b._crear_unidad if False else None  # no-op, deja el nombre visible en el diff
    rail._on_toggle_de_banda("Casa B")

    assert banda_casa_b.chevron.text() == "▸"
    assert all(not f.isVisible() for f in rail.rows_por_unidad["Casa B"])
    assert "Casa B" in rail.unidades_colapsadas()


def test_clic_dos_veces_la_vuelve_a_expandir(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail._on_toggle_de_banda("Casa B")
    rail._on_toggle_de_banda("Casa B")

    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_casa_b.chevron.text() == "▾"
    assert all(f.isVisible() for f in rail.rows_por_unidad["Casa B"])
    assert "Casa B" not in rail.unidades_colapsadas()


def test_colapsar_emite_unidad_colapso_cambiado(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    avisos = []
    rail.unidad_colapso_cambiado.connect(lambda u, c: avisos.append((u, c)))
    rail._on_toggle_de_banda("Casa B")
    assert avisos == [("Casa B", True)]


def test_set_unidades_colapsadas_aplica_a_bandas_existentes(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail.set_unidades_colapsadas(["Casa A"])

    banda_casa_a = next(b for b in rail.unit_bands if b.nombre == "Casa A")
    assert banda_casa_a.chevron.text() == "▸"
    assert all(not f.isVisible() for f in rail.rows_por_unidad["Casa A"])


def test_set_unidades_colapsadas_antes_de_poblar_se_aplica_al_construir(rail):
    rail.set_unidades_colapsadas(["Casa B"])
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})

    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_casa_b.chevron.text() == "▸"
    assert all(not f.isVisible() for f in rail.rows_por_unidad["Casa B"])


def test_expandir_unidad_la_abre_y_avisa(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail._on_toggle_de_banda("Casa B")
    avisos = []
    rail.unidad_colapso_cambiado.connect(lambda u, c: avisos.append((u, c)))

    rail.expandir_unidad("Casa B")

    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_casa_b.chevron.text() == "▾"
    assert avisos == [("Casa B", False)]


def test_expandir_unidad_ya_abierta_no_hace_nada(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    avisos = []
    rail.unidad_colapso_cambiado.connect(lambda u, c: avisos.append((u, c)))
    rail.expandir_unidad("Casa A")
    assert avisos == []


def test_conteo_de_la_banda_suma_sus_cuartos(rail):
    rail.set_rooms_agrupados(
        **_mismos_argumentos(),
        counts={("Casa B", "Cocina"): 3, ("Casa B", "Baño"): 2},
    )
    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_casa_b.contador.text() == "5"


def test_conteo_de_la_banda_se_actualiza_sin_reconstruir(rail):
    rail.set_rooms_agrupados(
        **_mismos_argumentos(),
        counts={("Casa B", "Cocina"): 3, ("Casa B", "Baño"): 2},
    )
    banda_antes = next(b for b in rail.unit_bands if b.nombre == "Casa B")

    rail.set_rooms_agrupados(
        **_mismos_argumentos(),
        counts={("Casa B", "Cocina"): 4, ("Casa B", "Baño"): 2},
    )

    banda_despues = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    assert banda_despues is banda_antes
    assert banda_despues.contador.text() == "6"
```

(Borra la línea `banda_casa_b._crear_unidad if False else None` del primer borrador arriba — quedó de un copy-paste, no la incluyas.)

- [ ] **Step 2: Correr y confirmar que fallan**

```bash
.venv/bin/pytest tests/ui/test_room_rail_unidades.py -v
```
Expected: varios FAIL — `AttributeError: 'RoomRail' object has no attribute 'unidades_colapsadas'`, `_BandaDeUnidad.chevron` no existe, etc.

- [ ] **Step 3: Implementar `_BandaDeUnidad`**

Reemplaza la clase completa (`src/clasificador_video/ui/room_rail.py:424-446`):

```python
class _BandaDeUnidad(QWidget):
    """El encabezado de un grupo de cuartos por unidad. `color=None` es el
    bloque "Sin unidad" -- sin swatch y sin flecha de colapsar, porque no
    es una unidad de verdad sino un bloque migratorio (spec 2026-09-21 S3:
    colapsar aplica a unidades, no a este bloque)."""

    toggle_solicitado = Signal(str)   # llave

    def __init__(self, nombre: str, color: str | None, llave: str,
                 conteo: int, colapsado: bool, parent=None):
        super().__init__(parent)
        self.nombre = nombre
        self.llave = llave
        self._colapsable = color is not None
        self.setObjectName("unitBand")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 8, 2, 4)
        layout.setSpacing(6)

        self.chevron = QLabel("")
        self.chevron.setObjectName("unitBandChevron")
        self.chevron.setFixedWidth(12)
        layout.addWidget(self.chevron)

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

        self.contador = QLabel(str(conteo))
        self.contador.setObjectName("unitBandCount")
        layout.addWidget(self.contador)

        self.set_colapsado(colapsado)

    def set_colapsado(self, colapsado: bool) -> None:
        self._colapsado = colapsado
        if not self._colapsable:
            return
        self.chevron.setText("▸" if colapsado else "▾")

    def set_destino_de_arrastre(self, activo: bool) -> None:
        """Resalte de "aqui se suelta" mientras arrastras un cuarto sobre
        esta banda (Task 9). Aparte de `setStyleSheet` a mano: usa la
        propiedad dinamica + QSS, mismo mecanismo que `roomRow[actual]`."""
        if self.property("arrastreDestino") == activo:
            return
        self.setProperty("arrastreDestino", activo)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if self._colapsable and event.button() == Qt.MouseButton.LeftButton:
            self.toggle_solicitado.emit(self.llave)
        super().mousePressEvent(event)
```

- [ ] **Step 4: Implementar el estado de colapso y `_crear_banda` en `RoomRail`**

En `RoomRail`, junto a los `Signal` existentes:

```python
    unidad_colapso_cambiado = Signal(str, bool)   # llave, colapsada
```

En `__init__`, junto a `self.rows_por_unidad: dict[str, list[_FilaCuarto]] = {}` (línea ~574):

```python
        self._banda_por_unidad: dict[str, "_BandaDeUnidad"] = {}
        # Que unidades estan colapsadas. Vive ACA, no en MainWindow -- mismo
        # criterio que `ClipSheet._colapsados` para los bins: es estado de
        # vista del widget. MainWindow solo lo lee al autoguardar y lo
        # escribe al restaurar (spec 2026-09-21 S3).
        self._colapsadas: set[str] = set()
```

Reemplaza `_crear_banda` (línea ~767-772):

```python
    def _crear_banda(self, nombre: str, llave: str, conteo: int) -> "_BandaDeUnidad":
        indice = len([b for b in self.unit_bands if b.nombre != SIN_UNIDAD_ETIQUETA])
        color = None if nombre == SIN_UNIDAD_ETIQUETA else theme.unit_color(indice)
        banda = _BandaDeUnidad(nombre, color, llave, conteo, llave in self._colapsadas)
        banda.toggle_solicitado.connect(self._on_toggle_de_banda)
        self._rooms_layout.addWidget(banda)
        return banda
```

En `_limpiar_bandas` (línea ~756-764), suma la limpieza del nuevo dict:

```python
    def _limpiar_bandas(self) -> None:
        for banda in self.unit_bands:
            banda.setParent(None)
            banda.deleteLater()
        self.unit_bands = []
        self._banda_por_unidad = {}
        for filas in self.rows_por_unidad.values():
            for fila in filas:
                fila.setParent(None)
                fila.deleteLater()
        self.rows_por_unidad = {}
```

En el bucle de reconstrucción de `set_rooms_agrupados` (línea ~722-753), donde hoy dice:

```python
        for llave in orden:
            nombre_banda = SIN_UNIDAD_ETIQUETA if llave == "" else llave
            banda = self._crear_banda(nombre_banda)
            self.unit_bands.append(banda)
            filas = []
            for indice, cuarto in enumerate(rooms_por_unidad.get(llave, [])):
                numero = indice + 1 if indice < MAX_TECLAS else None
                fila = _FilaCuarto(numero, cuarto, theme.room_color(indice),
                                    counts.get((llave, cuarto), 0))
                fila.unidad = llave
```

cámbialo por:

```python
        for llave in orden:
            nombre_banda = SIN_UNIDAD_ETIQUETA if llave == "" else llave
            cuartos_de_la_unidad = rooms_por_unidad.get(llave, [])
            conteo_unidad = sum(counts.get((llave, c), 0) for c in cuartos_de_la_unidad)
            banda = self._crear_banda(nombre_banda, llave, conteo_unidad)
            self.unit_bands.append(banda)
            self._banda_por_unidad[llave] = banda
            filas = []
            for indice, cuarto in enumerate(cuartos_de_la_unidad):
                numero = indice + 1 if indice < MAX_TECLAS else None
                fila = _FilaCuarto(numero, cuarto, theme.room_color(indice),
                                    counts.get((llave, cuarto), 0))
                fila.unidad = llave
                fila.setVisible(llave not in self._colapsadas)
```

(El resto del cuerpo del `for indice, cuarto in ...` — las conexiones de señales — sigue exactamente igual, no lo repitas distinto.)

Y en el camino rápido (misma función, donde la firma no cambió — línea ~715-719):

```python
        if firma == self._ultimo_agrupado:
            for llave, filas in self.rows_por_unidad.items():
                for fila in filas:
                    fila.count_label.setText(str(counts.get((llave, fila.nombre), 0)))
                banda = self._banda_por_unidad.get(llave)
                if banda is not None:
                    banda.contador.setText(
                        str(sum(counts.get((llave, f.nombre), 0) for f in filas))
                    )
            return
```

- [ ] **Step 5: Implementar el toggle, `unidades_colapsadas()`, `set_unidades_colapsadas()` y `expandir_unidad()`**

Junto a `_crear_banda`, agrega:

```python
    def _on_toggle_de_banda(self, llave: str) -> None:
        if llave in self._colapsadas:
            self._colapsadas.discard(llave)
        else:
            self._colapsadas.add(llave)
        colapsada = llave in self._colapsadas
        banda = self._banda_por_unidad.get(llave)
        if banda is not None:
            banda.set_colapsado(colapsada)
        for fila in self.rows_por_unidad.get(llave, []):
            fila.setVisible(not colapsada)
        self.unidad_colapso_cambiado.emit(llave, colapsada)

    def unidades_colapsadas(self) -> set[str]:
        return set(self._colapsadas)

    def set_unidades_colapsadas(self, nombres) -> None:
        """Lo pone quien restaura el proyecto (`app._poblar_ventana`). No
        emite `unidad_colapso_cambiado`: restaurar no es una accion del
        usuario, y emitirla dispararia un autoguardado sin que nada haya
        cambiado de verdad."""
        self._colapsadas = set(nombres)
        for llave, banda in self._banda_por_unidad.items():
            banda.set_colapsado(llave in self._colapsadas)
        for llave, filas in self.rows_por_unidad.items():
            for fila in filas:
                fila.setVisible(llave not in self._colapsadas)

    def expandir_unidad(self, llave: str) -> None:
        """La abre si estaba colapsada -- para cuando le llega un cuarto
        nuevo (arrastre o `⌘U` con unidad activa, spec S3) y hace falta
        verlo. No hace nada si ya estaba abierta: no hay nada que avisar."""
        if llave not in self._colapsadas:
            return
        self._colapsadas.discard(llave)
        banda = self._banda_por_unidad.get(llave)
        if banda is not None:
            banda.set_colapsado(False)
        for fila in self.rows_por_unidad.get(llave, []):
            fila.setVisible(True)
        self.unidad_colapso_cambiado.emit(llave, False)
```

- [ ] **Step 6: Añadir el QSS**

En `src/clasificador_video/ui/theme.py`, junto a `QLabel#unitBandLabel` (línea ~1114-1118):

```python
    QLabel#unitBandChevron {{
        color: {TEXT_3};
        font-size: {FONT_MICRO}px;
    }}
    QLabel#unitBandCount {{
        color: {TEXT_3};
        font-family: {MONO_FONT};
        font-size: {FONT_MICRO}px;
    }}
    /* Se resalta mientras arrastras un cuarto encima (Task 9) -- mismo
       ambar de "aqui es donde apuntas" que ya usa `lineaDeDestino`. */
    QWidget#unitBand[arrastreDestino="true"] {{
        background-color: {con_alfa_qss(CURRENT_COLOR, 0.12)};
        border: 1px dashed {CURRENT_COLOR};
        border-radius: {RADIUS_SM}px;
    }}
```

- [ ] **Step 7: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/ui/test_room_rail_unidades.py -v
```
Expected: PASS — incluidos todos los tests viejos del archivo (nada de esto tocó `set_rooms`, el camino sin unidades).

```bash
.venv/bin/pytest tests/ui/ -v
```
Expected: PASS completo (esto tocó `_crear_banda`, hay que confirmar que ningún otro test lo llamaba con la firma vieja).

- [ ] **Step 8: Verificación visual**

Arma una `RoomRail` con `set_rooms_agrupados` (dos unidades, una colapsada vía `set_unidades_colapsadas`), `grab()`, guarda el PNG en el scratchpad y léelo — confirma que la banda colapsada no muestra sus filas y que la flecha apunta a la derecha (▸) en esa banda y hacia abajo (▾) en la otra, y que "Sin unidad" no tiene flecha.

- [ ] **Step 9: Commit**

```bash
git add src/clasificador_video/ui/room_rail.py src/clasificador_video/ui/theme.py tests/ui/test_room_rail_unidades.py
git commit -m "$(cat <<'EOF'
Sumar bandas de unidad colapsables al rail, con conteo

Bruno pidio ver las unidades pero poder colapsarlas. El estado vive en
el propio RoomRail -- mismo criterio que ClipSheet ya usa para
colapsar bins -- y expone unidades_colapsadas()/set_unidades_colapsadas()
para que MainWindow lo guarde y lo restaure (Task 6).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `MainWindow`/`app.py` — guardar y restaurar el colapso, y auto-abrir al recibir un cuarto

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Modify: `src/clasificador_video/app.py`
- Test: `tests/ui/test_main_window_unidades.py`
- Test: `tests/test_app.py` (o el archivo de tests que cubra `_poblar_ventana` — revisa `grep -rn "_poblar_ventana" tests/` si el nombre difiere)

- [ ] **Step 1: Ubicar dónde testear la restauración**

```bash
grep -rln "_poblar_ventana\|agrupar_por_cuarto" tests/
```

Usa el archivo que ya prueba `_poblar_ventana`/`abrir_proyecto` con `agrupar_por_cuarto`/`modo_horizontal` como modelo exacto para el test de restauración de este task — mismo fixture, mismo patrón de "escribir un dict de proyecto a mano y pasarlo por la función que puebla la ventana".

- [ ] **Step 2: Escribir los tests que fallan**

En `tests/ui/test_main_window_unidades.py`:

```python
def test_autosave_incluye_unidades_colapsadas(main_window):
    main_window.room_rail.set_rooms_agrupados(
        unidades=["Casa A", "Casa B"],
        rooms_por_unidad={"Casa A": [], "Casa B": []}, counts={},
    )
    main_window.room_rail._on_toggle_de_banda("Casa B")
    data = main_window._datos_del_proyecto()
    assert data["unidades_colapsadas"] == ["Casa B"]


def test_asignar_cuarto_con_unidad_activa_la_expande_si_estaba_colapsada(main_window):
    main_window.load_clips([Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)])
    main_window.unit_selection.add("Casa A")
    main_window._activar_unidad("Casa A")
    main_window.room_rail.set_rooms_agrupados(
        unidades=["Casa A"], rooms_por_unidad={"Casa A": []}, counts={},
    )
    main_window.room_rail._on_toggle_de_banda("Casa A")

    main_window._asignar_cuarto(["Cocina"])

    assert "Casa A" not in main_window.room_rail.unidades_colapsadas()
```

Añade el test de restauración en el archivo que identificaste en el Step 1, siguiendo su patrón existente para `agrupar_por_cuarto` pero con la llave `"unidades_colapsadas"` y comprobando `window.room_rail.unidades_colapsadas() == {"Casa B"}` (ajusta nombres de fixtures/funciones al archivo real).

- [ ] **Step 3: Correr y confirmar que fallan**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -k "colapsad" -v
```
Expected: FAIL.

- [ ] **Step 4: Implementar en `main_window.py`**

En `_datos_del_proyecto` (línea ~2566-2602), agrega el argumento a la llamada de `proyecto.a_dict`:

```python
            rooms_por_unidad={
                nombre: self.room_selections[nombre].active_rooms()
                for nombre in self.unit_selection.active_rooms()
                if nombre in self.room_selections
            },
            unidades_colapsadas=sorted(self.room_rail.unidades_colapsadas()),
        )
        return data
```

En `_asignar_cuarto` (línea ~1615-1641), justo después de `self._apply_categoria_to_targets(completo)`:

```python
        self._apply_categoria_to_targets(completo)
        if self._unidad_activa:
            self.room_rail.expandir_unidad(self._unidad_activa)
        self._refresh_sheet()
```

- [ ] **Step 5: Implementar en `app.py`**

En `_poblar_ventana` (línea ~156 en adelante), junto a `window.set_modo_horizontal(...)`:

```python
    window.set_modo_horizontal(data.get("modo_horizontal") is True)
    # Que unidades quedaron colapsadas en el rail (spec 2026-09-21 S3).
    # Falta en todo proyecto de antes de hoy, y ahi el default es "ninguna"
    # -- se abre exactamente como se veia antes de que esto existiera.
    colapsadas = data.get("unidades_colapsadas")
    window.room_rail.set_unidades_colapsadas(
        [str(u) for u in colapsadas] if isinstance(colapsadas, list) else []
    )
```

Ojo con el ORDEN: esta línea tiene que ir DESPUÉS de que el rail ya tenga sus bandas construidas (después de `window._refresh_sheet(force_rebuild=True)`, que es lo que dispara `_refresh_rail`/`set_rooms_agrupados` por primera vez) — si se llama antes, `set_unidades_colapsadas` no encuentra bandas que colapsar todavía, aunque el Step 4 de la Task 5 ya cubre ese caso (`self._colapsadas` se guarda igual y se aplica al construir). Colócala de todas formas después de `_refresh_sheet` para que quede junto al resto del bloque de restauración de vista, no antes.

- [ ] **Step 6: Correr y confirmar que pasan**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -v
.venv/bin/pytest tests/ -k "poblar_ventana or restaur" -v
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/main_window.py src/clasificador_video/app.py tests/
git commit -m "$(cat <<'EOF'
Guardar y restaurar que unidades quedaron colapsadas

Y auto-expandir la unidad activa al asignarle un cuarto (Ctrl+U):
Bruno pidio confirmar de un vistazo que el cuarto llego a donde
queria, sin tener que abrir la banda a mano.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `RoomRail` — seleccionar varios cuartos con ⌘-clic

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py`
- Modify: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_room_rail_unidades.py`

Solo aplica en el camino agrupado (`set_rooms_agrupados`): sin unidades no hay a dónde arrastrar un grupo, así que `set_rooms` (camino sin bandas) se queda exactamente igual — cero fricción nueva para el 90% de los proyectos.

- [ ] **Step 1: Escribir los tests que fallan**

Agrega a `tests/ui/test_room_rail_unidades.py`:

```python
from PySide6.QtCore import Qt


def test_clic_simple_selecciona_solo_esa_fila(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    fila_cocina = rail.rows_por_unidad["Casa B"][0]
    rail._on_clic_en_fila(fila_cocina.nombre, False, "Casa B")
    assert fila_cocina.property("seleccionada") is True


def test_cmd_clic_suma_a_la_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")
    assert cocina.property("seleccionada") is True
    assert banio.property("seleccionada") is True


def test_cmd_clic_en_otra_unidad_reemplaza_la_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina_a = rail.rows_por_unidad["Casa A"][0]
    cocina_b = rail.rows_por_unidad["Casa B"][0]
    rail._on_clic_en_fila(cocina_a.nombre, True, "Casa A")
    rail._on_clic_en_fila(cocina_b.nombre, True, "Casa B")
    assert cocina_a.property("seleccionada") is False
    assert cocina_b.property("seleccionada") is True


def test_cmd_clic_de_nuevo_la_quita_de_la_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    assert cocina.property("seleccionada") is False
    assert banio.property("seleccionada") is True


def test_clic_simple_sobre_fila_ya_en_grupo_no_limpia_la_seleccion(rail):
    """Para poder agarrar cualquiera de las filas seleccionadas y
    arrastrar el grupo entero -- si el clic limpiara de una, arrancar el
    arrastre desde ahi solo llevaria esa fila."""
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")
    rail._on_clic_en_fila(cocina.nombre, False, "Casa B")
    assert cocina.property("seleccionada") is True
    assert banio.property("seleccionada") is True


def test_soltar_sin_arrastre_sobre_fila_del_grupo_si_limpia_la_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")

    rail._on_release_sin_arrastre(cocina.nombre, "Casa B")

    assert cocina.property("seleccionada") is True
    assert banio.property("seleccionada") is False


def test_grupo_para_arrastrar_una_sola_fila_sin_seleccion(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina = rail.rows_por_unidad["Casa B"][0]
    assert rail._grupo_para_arrastrar(cocina.nombre, "Casa B") == ["Cocina"]


def test_grupo_para_arrastrar_el_grupo_completo_en_orden_del_rail(rail):
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    cocina, banio = rail.rows_por_unidad["Casa B"]
    rail._on_clic_en_fila(banio.nombre, True, "Casa B")
    rail._on_clic_en_fila(cocina.nombre, True, "Casa B")
    # aunque "Baño" se marco primero, el orden que devuelve es el del rail
    assert rail._grupo_para_arrastrar(cocina.nombre, "Casa B") == ["Cocina", "Baño"]
```

- [ ] **Step 2: Correr y confirmar que fallan**

```bash
.venv/bin/pytest tests/ui/test_room_rail_unidades.py -k "clic or grupo_para_arrastrar or soltar_sin_arrastre" -v
```
Expected: FAIL — nada de esto existe todavía.

- [ ] **Step 3: Implementar la señal y el estado de selección en `_FilaCuarto`**

En `_FilaCuarto`, junto a los `Signal` existentes:

```python
    clic_solicitado = Signal(str, bool)          # nombre, con_modificador
    clic_soltado_sin_arrastre = Signal(str)       # nombre
```

En `__init__`, tras `self._inicio_del_arrastre: QPoint | None = None`:

```python
        self.obtener_grupo = None   # lo pone RoomRail en el camino agrupado
```

Reemplaza `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` (línea ~247-282):

```python
    def mousePressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        # se guarda de donde salio para medir el umbral de arrastre; el click
        # normal --enfocar la fila-- lo sigue haciendo Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._inicio_del_arrastre = event.position().toPoint()
            con_modificador = bool(
                event.modifiers() & (Qt.KeyboardModifier.ControlModifier
                                      | Qt.KeyboardModifier.MetaModifier)
            )
            self.clic_solicitado.emit(self.nombre, con_modificador)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Arranca el arrastre pasado el umbral del sistema.

        Con el umbral y no al primer pixel: sin el, enfocar una fila con un
        click que tiembla arrancaria un arrastre, y reordenar cambia la tecla
        de los cuartos -- no es un gesto que uno quiera disparar sin querer.
        """
        if self._inicio_del_arrastre is None:
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        recorrido = (event.position().toPoint() - self._inicio_del_arrastre)
        if recorrido.manhattanLength() < QApplication.startDragDistance():
            return
        self._inicio_del_arrastre = None
        nombres = self.obtener_grupo() if self.obtener_grupo else [self.nombre]
        mime = QMimeData()
        mime.setData(MIME_CUARTO, "\n".join(nombres).encode())
        arrastre = QDrag(self)
        arrastre.setMimeData(mime)
        if len(nombres) > 1:
            arrastre.setPixmap(_pixmap_de_grupo(nombres, self.font()))
        else:
            arrastre.setPixmap(self.grab())
        arrastre.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        # `_inicio_del_arrastre` sigue puesto solo si mouseMoveEvent NUNCA
        # arranco un arrastre con este click -- osea, fue un clic simple.
        if (self._inicio_del_arrastre is not None
                and event.button() == Qt.MouseButton.LeftButton):
            self.clic_soltado_sin_arrastre.emit(self.nombre)
        self._inicio_del_arrastre = None
        super().mouseReleaseEvent(event)
```

Y agrega el setter de estado visual, junto a `pedir_eliminar`:

```python
    def set_seleccionada(self, seleccionada: bool) -> None:
        if self.property("seleccionada") == seleccionada:
            return
        self.setProperty("seleccionada", seleccionada)
        self.style().unpolish(self)
        self.style().polish(self)
```

- [ ] **Step 4: La función que arma el pixmap del grupo**

Cerca del principio del archivo, junto a `_texto_de_estado`:

```python
def _pixmap_de_grupo(nombres: list[str], fuente) -> "QPixmap":
    """El globo que sigue al mouse mientras arrastras varios cuartos --
    dice que llevas, en vez de mostrar solo la fila de la que agarraste
    (mockup `rail-arrastre.html`, spec 2026-09-21 S5)."""
    texto = ", ".join(nombres) if len(nombres) <= 2 else f"{nombres[0]} +{len(nombres) - 1}"
    metrica = QFontMetrics(fuente)
    ancho = metrica.horizontalAdvance(texto) + 20
    pixmap = QPixmap(ancho, 22)
    pixmap.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(pixmap)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    pintor.setPen(QColor(theme.CURRENT_COLOR))
    pintor.setBrush(QColor(theme.BG_SURFACE_2))
    pintor.drawRoundedRect(0, 0, ancho - 1, 21, 6, 6)
    pintor.setPen(QColor(theme.TEXT))
    pintor.setFont(fuente)
    pintor.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, texto)
    pintor.end()
    return pixmap
```

Agrega los imports que faltan al principio del archivo:

```python
from PySide6.QtGui import QColor, QDrag, QFontMetrics, QPainter, QPixmap
```

- [ ] **Step 5: Implementar el estado de selección y el grupo en `RoomRail`**

Junto a `self._colapsadas: set[str] = set()`:

```python
        self._seleccion: set[str] = set()
        self._unidad_de_seleccion: str | None = None
```

En el bucle de `set_rooms_agrupados` que crea cada `fila` (dentro del `for indice, cuarto in ...`), después de `fila.remove_requested.connect(...)`:

```python
                fila.clic_solicitado.connect(
                    lambda nombre, mod, u=llave: self._on_clic_en_fila(nombre, mod, u)
                )
                fila.clic_soltado_sin_arrastre.connect(
                    lambda nombre, u=llave: self._on_release_sin_arrastre(nombre, u)
                )
                fila.obtener_grupo = (
                    lambda n=cuarto, u=llave: self._grupo_para_arrastrar(n, u)
                )
```

Y agrega los métodos, junto a `_on_toggle_de_banda`:

```python
    def _on_clic_en_fila(self, nombre: str, con_modificador: bool, unidad: str) -> None:
        if con_modificador:
            if unidad != self._unidad_de_seleccion:
                # la seleccion no cruza unidades (spec S4): dos unidades
                # pueden repetir un nombre de cuarto, y mezclarlas no tiene
                # un destino que tenga sentido
                self._seleccion = {nombre}
                self._unidad_de_seleccion = unidad
            elif nombre in self._seleccion:
                self._seleccion.discard(nombre)
            else:
                self._seleccion.add(nombre)
        elif not (nombre in self._seleccion and unidad == self._unidad_de_seleccion):
            self._seleccion = {nombre}
            self._unidad_de_seleccion = unidad
            # si YA estaba en una seleccion de 2+, un clic simple no la
            # limpia aqui todavia -- se decide en el release, para poder
            # agarrar cualquiera de las filas seleccionadas y arrastrar el
            # grupo completo (igual que en Finder)
        self._repintar_seleccion()

    def _on_release_sin_arrastre(self, nombre: str, unidad: str) -> None:
        if (unidad == self._unidad_de_seleccion and nombre in self._seleccion
                and len(self._seleccion) > 1):
            self._seleccion = {nombre}
            self._repintar_seleccion()

    def _repintar_seleccion(self) -> None:
        for llave, filas in self.rows_por_unidad.items():
            for fila in filas:
                fila.set_seleccionada(
                    llave == self._unidad_de_seleccion and fila.nombre in self._seleccion
                )

    def _grupo_para_arrastrar(self, nombre: str, unidad: str) -> list[str]:
        """Los nombres que viajan juntos si arrancas el arrastre desde
        `nombre`: el grupo completo si es parte de una seleccion de 2+, o
        solo el mismo si no."""
        if (unidad == self._unidad_de_seleccion and nombre in self._seleccion
                and len(self._seleccion) > 1):
            # en el orden del rail, no en el orden en que se fueron marcando
            # -- para que el globo que sigue al mouse lea igual que la lista
            return [f.nombre for f in self.rows_por_unidad[unidad]
                    if f.nombre in self._seleccion]
        return [nombre]
```

- [ ] **Step 6: QSS para la fila seleccionada**

En `src/clasificador_video/ui/theme.py`, junto a `QWidget#roomRow[actual="true"]`:

```python
    /* Seleccion multiple (Cmd-clic), distinta del foco de teclado: el
       foco dice "aqui actuan Enter/Backspace/Alt-flechas", la seleccion
       dice "esto es lo que arrastro". Pueden coincidir en la misma fila y
       tienen que leerse distinto. */
    QWidget#roomRow[seleccionada="true"] {{
        background-color: {BG_SURFACE_2};
        border: 1px solid {CURRENT_COLOR};
    }}
```

- [ ] **Step 7: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/ui/test_room_rail_unidades.py -v
.venv/bin/pytest tests/ui/test_room_rail.py -v
```
Expected: PASS completo en los dos archivos — `test_room_rail.py` prueba el camino sin bandas, que no debería haber cambiado de comportamiento (los `Signal` nuevos existen pero nada los conecta ahí).

- [ ] **Step 8: Commit**

```bash
git add src/clasificador_video/ui/room_rail.py src/clasificador_video/ui/theme.py tests/ui/test_room_rail_unidades.py
git commit -m "$(cat <<'EOF'
Sumar seleccion multiple de cuartos con Cmd-clic en el rail

Solo dentro de una misma unidad -- dos unidades pueden repetir un
nombre de cuarto, y mezclar la seleccion entre ellas no tiene un
destino que tenga sentido. Un clic simple sobre una fila ya
seleccionada no limpia el grupo hasta soltar sin arrastre, para poder
agarrar cualquiera de las filas marcadas y arrastrarlas juntas.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: `RoomRail` — soltar el grupo sobre la banda de OTRA unidad

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py`
- Test: `tests/ui/test_room_rail_unidades.py`

Esto reemplaza el límite de `soltar_cuarto` que hoy ignora en silencio un drop fuera de la banda de origen (`room_rail.py:850-898`) — pero `soltar_cuarto` en sí **no se toca**: sigue siendo el camino de REORDENAR dentro de una banda, y su guarda "banda ajena → no hacer nada" se queda como red de seguridad para quien lo llame directo (el test `test_soltar_un_cuarto_en_OTRA_banda_se_ignora` no cambia). Lo nuevo vive en `dropEvent`, que decide ANTES de llamar a `soltar_cuarto` si el punto donde soltaste cae en la banda de origen (reordenar, camino de siempre) o en la de otra unidad (mover, camino nuevo).

- [ ] **Step 1: Escribir los tests que fallan**

Agrega a `tests/ui/test_room_rail_unidades.py`:

```python
def test_unidad_bajo_identifica_la_banda_en_esa_altura(qtbot, rail):
    rail.resize(200, 700)
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail.show()
    qtbot.waitExposed(rail)

    banda_casa_b = next(b for b in rail.unit_bands if b.nombre == "Casa B")
    y_dentro_de_casa_b = banda_casa_b.mapTo(rail, banda_casa_b.rect().topLeft()).y() + 5

    assert rail._unidad_bajo(y_dentro_de_casa_b) == "Casa B"


def test_unidad_bajo_fuera_de_toda_banda_es_none(qtbot, rail):
    rail.resize(200, 700)
    rail.set_rooms_agrupados(**_mismos_argumentos(), counts={})
    rail.show()
    qtbot.waitExposed(rail)

    assert rail._unidad_bajo(-50) is None


def test_mover_grupo_a_unidad_emite_la_senal(rail):
    avisos = []
    rail.rooms_movidos_a_unidad.connect(
        lambda nombres, origen, destino: avisos.append((nombres, origen, destino))
    )
    rail.mover_grupo_a_unidad(["Cocina", "Comedor"], "Casa A", "Casa B")
    assert avisos == [(["Cocina", "Comedor"], "Casa A", "Casa B")]
```

- [ ] **Step 2: Correr y confirmar que fallan**

```bash
.venv/bin/pytest tests/ui/test_room_rail_unidades.py -k "unidad_bajo or mover_grupo" -v
```
Expected: FAIL.

- [ ] **Step 3: Implementar**

En `RoomRail`, junto a `unidad_colapso_cambiado`:

```python
    rooms_movidos_a_unidad = Signal(list, str, str)   # nombres, unidad_origen, unidad_destino
```

Junto a `posicion_para_soltar`, agrega:

```python
    def _unidad_bajo(self, y: int) -> str | None:
        """La llave de la banda que ocupa esa altura, o `None` si no hay
        bandas o el punto cae fuera de todas.

        Calculado con la geometria REAL de las bandas -- no con el indice
        de insercion entre filas que usa `posicion_para_soltar` -- porque
        aqui no hace falta saber DONDE dentro de la banda, solo CUAL
        banda: soltar en cualquier parte de ella alcanza (spec S5).
        """
        if not self.unit_bands:
            return None
        llaves = list(self.rows_por_unidad.keys())
        techos = [b.mapTo(self, b.rect().topLeft()).y() for b in self.unit_bands]
        for indice, (llave, techo) in enumerate(zip(llaves, techos)):
            piso = techos[indice + 1] if indice + 1 < len(techos) else self.height()
            if techo <= y < piso:
                return llave
        return None

    def mover_grupo_a_unidad(self, nombres: list[str], unidad_origen: str,
                              unidad_destino: str) -> None:
        """Aparte de `dropEvent` para poder probarlo sin fabricar un
        QDropEvent de verdad (mismo criterio que `soltar_cuarto`)."""
        self.rooms_movidos_a_unidad.emit(list(nombres), unidad_origen, unidad_destino)
```

Reemplaza `dragMoveEvent`/`dragLeaveEvent`/`dropEvent` (línea ~774-798):

```python
    def dragMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if not event.mimeData().hasFormat(MIME_CUARTO):
            return
        y = event.position().toPoint().y()
        origen_unidad = getattr(event.source(), "unidad", None)
        unidad_bajo = self._unidad_bajo(y)
        # "" (Sin unidad) no es un destino valido -- es el bloque
        # migratorio, no una unidad de verdad (spec S8 por omision: este
        # spec no diseño que significa "quitarle la unidad a un cuarto").
        if unidad_bajo and unidad_bajo != (origen_unidad or ""):
            self.esconder_linea_de_destino()
            self._resaltar_banda(unidad_bajo)
            event.acceptProposedAction()
            return
        self._resaltar_banda(None)
        self.mostrar_linea_de_destino(self.posicion_para_soltar(y))
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self.esconder_linea_de_destino()
        self._resaltar_banda(None)

    def dropEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        mime = event.mimeData()
        self.esconder_linea_de_destino()
        self._resaltar_banda(None)
        if not mime.hasFormat(MIME_CUARTO):
            return
        nombres = bytes(mime.data(MIME_CUARTO)).decode(errors="ignore").split("\n")
        y = event.position().toPoint().y()
        origen = event.source()
        origen_unidad = getattr(origen, "unidad", None)
        unidad_bajo = self._unidad_bajo(y)
        if unidad_bajo and origen_unidad is not None and unidad_bajo != origen_unidad:
            self.mover_grupo_a_unidad(nombres, origen_unidad, unidad_bajo)
            event.acceptProposedAction()
            return
        # `event.source()` es la `_FilaCuarto` que arranco el arrastre (la
        # crea con `QDrag(self)`): de ahi sale la unidad de origen SIN
        # ambiguedad, incluso si otra unidad tiene un cuarto con el mismo
        # nombre. El nombre solo no alcanza para eso.
        self.soltar_cuarto(nombres[0], self.posicion_para_soltar(y), origen=origen)
        event.acceptProposedAction()

    def _resaltar_banda(self, llave: str | None) -> None:
        for esa_llave, banda in self._banda_por_unidad.items():
            banda.set_destino_de_arrastre(esa_llave == llave)
```

`dragEnterEvent` se queda exactamente igual — sigue mostrando la línea de inserción al entrar, y el primer `dragMoveEvent` la corrige a resaltado de banda si hace falta.

- [ ] **Step 4: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/ui/test_room_rail_unidades.py -v
```
Expected: PASS — incluido `test_soltar_un_cuarto_en_OTRA_banda_se_ignora`, que sigue llamando `soltar_cuarto` DIRECTO y por lo tanto nunca pasa por `dropEvent`/`_unidad_bajo`.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/room_rail.py tests/ui/test_room_rail_unidades.py
git commit -m "$(cat <<'EOF'
Soltar un cuarto sobre la banda de OTRA unidad ya no se ignora

Antes dropEvent llamaba siempre a soltar_cuarto, que ignoraba en
silencio un drop fuera de la banda de origen. Ahora dropEvent decide
ANTES, con la geometria real de las bandas: dentro de la propia banda
sigue siendo reordenar (soltar_cuarto, sin cambios); en la banda de
OTRA unidad emite rooms_movidos_a_unidad. Sin bandas, comportamiento
identico a siempre.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: `MainWindow` — mover el cuarto completo, sin choque

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_unidades.py`

El núcleo del spec: mover un cuarto con todos sus clips de una unidad a otra, con su entrada de historial. Este task cubre el camino SIN choque de nombre — el choque es el Task 10.

- [ ] **Step 1: Escribir los tests que fallan**

Agrega a `tests/ui/test_main_window_unidades.py`:

```python
from clasificador_video.history import CuartoMovido


def _con_dos_unidades(main_window):
    main_window.unit_selection.add("Casa A")
    main_window.unit_selection.add("Casa B")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections["Casa A"].add("Cocina")
    main_window.room_selections["Casa B"] = RoomSelection()


def test_mover_cuarto_a_unidad_mueve_los_clips(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=3, ruta=Path("/c.MP4"), categoria_path=["Casa A", "Comedor"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina", fue_fusion=False,
    )
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]
    assert main_window.clips[1].categoria_path == ["Casa B", "Cocina"]
    assert main_window.clips[2].categoria_path == ["Casa A", "Comedor"]  # no se toca


def test_mover_cuarto_a_unidad_actualiza_los_catalogos(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina", fue_fusion=False,
    )
    assert "Cocina" not in main_window.room_selections["Casa A"].active_rooms()
    assert "Cocina" in main_window.room_selections["Casa B"].active_rooms()


def test_mover_cuarto_a_unidad_con_nombre_distinto_renombra_al_llegar(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina 2", fue_fusion=False,
    )
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina 2"]
    assert "Cocina 2" in main_window.room_selections["Casa B"].active_rooms()


def test_mover_cuarto_registra_en_el_historial(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina", fue_fusion=False,
    )
    entrada = main_window.history.entries()[0]
    assert entrada.cuarto_movido == CuartoMovido(
        nombre_origen="Cocina", posicion_origen=0, unidad_origen="Casa A",
        nombre_destino="Cocina", unidad_destino="Casa B", fue_fusion=False,
    )


def test_deshacer_mover_cuarto_regresa_clips_y_catalogos(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina", "Casa A", "Casa B", nombre_destino="Cocina", fue_fusion=False,
    )
    main_window.undo()
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]
    assert "Cocina" in main_window.room_selections["Casa A"].active_rooms()
    assert "Cocina" not in main_window.room_selections["Casa B"].active_rooms()


def test_mover_desde_sin_unidad_a_una_unidad(main_window):
    """El camino real de migracion de Bruno: Cocina-A vive hoy sin unidad,
    y se arrastra directo a Casa A."""
    main_window.unit_selection.add("Casa A")
    main_window.room_selections["Casa A"] = RoomSelection()
    main_window.room_selections[""].add("Cocina-A")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Cocina-A"], fps=30.0),
    ])
    main_window._mover_cuarto_a_unidad(
        "Cocina-A", "", "Casa A", nombre_destino="Cocina-A", fue_fusion=False,
    )
    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina-A"]
    assert "Cocina-A" not in main_window.room_selections[""].active_rooms()
```

- [ ] **Step 2: Correr y confirmar que fallan**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -k "mover_cuarto or deshacer_mover" -v
```
Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute '_mover_cuarto_a_unidad'`.

- [ ] **Step 3: Implementar `_mover_cuarto_a_unidad`**

Junto a `_asignar_unidad` (línea ~1643-1672):

```python
    def _mover_cuarto_a_unidad(self, nombre: str, unidad_origen: str, unidad_destino: str,
                                nombre_destino: str, fue_fusion: bool) -> None:
        """Mueve un cuarto COMPLETO -- con sus clips ya clasificados -- de
        una unidad a otra (spec 2026-09-21 S5). Sin choque de nombre esto
        es todo el trabajo; con choque, quien llama (Task 10) ya resolvio
        `nombre_destino`/`fue_fusion` antes de venir aqui.

        `unidad_origen` puede ser "" (el bloque migratorio "Sin unidad"),
        pero `unidad_destino` nunca -- soltar en ese bloque no es un
        destino valido (`RoomRail._unidad_bajo` ya lo filtra).
        """
        catalogo_origen = self.room_selections.setdefault(unidad_origen, RoomSelection())
        catalogo_destino = self.room_selections.setdefault(unidad_destino, RoomSelection())
        afectados = [
            i for i, c in enumerate(self.clips)
            if c.categoria_path and self._cuarto_de(c.categoria_path) == nombre
            and (self._unidad_de(c.categoria_path) or "") == unidad_origen
        ]
        posicion_origen = (
            catalogo_origen.active_rooms().index(nombre)
            if nombre in catalogo_origen.active_rooms() else 0
        )
        self._registrar(
            etiqueta=nombre_destino,
            detalle=self._detalle(afectados) if afectados else "0 clips",
            color=self._color_de_unidad(unidad_destino),
            clips=afectados,
            campos=("categoria_path",),
            cuarto_movido=CuartoMovido(
                nombre_origen=nombre, posicion_origen=posicion_origen,
                unidad_origen=unidad_origen, nombre_destino=nombre_destino,
                unidad_destino=unidad_destino, fue_fusion=fue_fusion,
            ),
        )
        for indice in afectados:
            self.clips[indice].categoria_path = [unidad_destino, nombre_destino]
        catalogo_origen.remove(nombre)
        catalogo_destino.add(nombre_destino)
        if self._ultimo_cuarto_usado == nombre:
            self._ultimo_cuarto_usado = nombre_destino
        activa = self._unidad_activa or ""
        if unidad_origen == activa or unidad_destino == activa:
            self._sync_rooms()
        else:
            self._refresh_rail()
            self._autosave()
```

Agrega el import de `CuartoMovido` junto al de `HistoryEntry`/`History` al principio de `main_window.py`:

```python
from clasificador_video.history import CuartoMovido, History, HistoryEntry
```

(Ajusta la línea exacta al import real que ya existe — solo agrega `CuartoMovido` a la lista.)

- [ ] **Step 4: Extender `_registrar` para aceptar `cuarto_movido`**

En `_registrar` (línea ~1784-1800):

```python
    def _registrar(self, etiqueta: str, detalle: str, color: str,
                   clips: list[int], campos: tuple[str, ...],
                   cuarto_borrado: tuple[str, int] | None = None,
                   cuarto_movido: CuartoMovido | None = None) -> None:
        """Guarda el estado ANTERIOR de `campos` en `clips`.

        Se llama SIEMPRE antes de mutar, nunca despues -- si no, guarda el
        estado nuevo y deshacer no hace nada. Y guarda solo los campos que la
        accion toca: con el clip entero, revertir una asignacion de cuarto se
        llevaria puesto el pick que se marco despues.
        """
        antes = {
            indice: {campo: _copiar(getattr(self.clips[indice], campo)) for campo in campos}
            for indice in clips
            if 0 <= indice < len(self.clips)
        }
        self.history.push(HistoryEntry(etiqueta, detalle, color, antes, cuarto_borrado,
                                        cuarto_movido=cuarto_movido))
        self._refresh_history()
```

- [ ] **Step 5: Implementar el deshacer en `_aplicar_entrada`**

En `_aplicar_entrada` (línea ~1860-1900), justo después del bloque `if entrada.cuarto_borrado is not None:`:

```python
        if entrada.cuarto_movido is not None:
            cm = entrada.cuarto_movido
            catalogo_origen = self.room_selections.setdefault(cm.unidad_origen, RoomSelection())
            # se REINSERTA en su posicion, mismo criterio que `cuarto_borrado`
            catalogo_origen.insert_at(cm.posicion_origen, cm.nombre_origen)
            if not cm.fue_fusion:
                # si fue fusion, el nombre YA existia en destino antes del
                # move y sigue teniendo clips propios despues de deshacer --
                # quitarlo de ahi seria borrar un cuarto que no se creo aqui
                catalogo_destino = self.room_selections.get(cm.unidad_destino)
                if catalogo_destino is not None:
                    catalogo_destino.remove(cm.nombre_destino)
            self._router.active_rooms = self.room_selection.active_rooms()
```

- [ ] **Step 6: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -v
```
Expected: PASS.

```bash
.venv/bin/pytest tests/ -q
```
Expected: PASS completo (esto tocó `_registrar`, que usan varias otras funciones con la firma vieja — confirma que los kwargs nuevos con default no rompen nada).

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Mover un cuarto completo (con sus clips) de una unidad a otra

El nucleo del spec 2026-09-21: _mover_cuarto_a_unidad reescribe el
categoria_path de todos los clips del cuarto, actualiza los dos
catalogos de RoomSelection y registra un CuartoMovido para poder
deshacerlo con Cmd+Z -- incluida la fusion, que no debe borrar del
catalogo destino un nombre que ya estaba ahi antes del move. Cubre
mover desde el bloque "Sin unidad", que es el camino real de
migracion de Bruno. El choque de nombre lo resuelve quien llama
(Task 10).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: `MainWindow` — el diálogo de choque de nombre

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_unidades.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agrega a `tests/ui/test_main_window_unidades.py`:

```python
def test_nombre_libre_en_prueba_sufijos_hasta_encontrar_uno(main_window):
    catalogo = RoomSelection()
    catalogo.add("Cocina")
    catalogo.add("Cocina 2")
    assert main_window._nombre_libre_en(catalogo, "Cocina") == "Cocina 3"


def test_nombre_libre_en_sin_choque_da_el_primer_sufijo(main_window):
    catalogo = RoomSelection()
    catalogo.add("Cocina")
    assert main_window._nombre_libre_en(catalogo, "Cocina") == "Cocina 2"


def test_on_rooms_movidos_sin_choque_mueve_directo(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    llamado = []
    monkeypatch.setattr(main_window, "_preguntar_por_el_choque",
                         lambda *a: llamado.append(a) or "cancelar")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert llamado == []   # no habia choque, no se pregunto nada
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]


def test_on_rooms_movidos_con_choque_pregunta_y_fusiona(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.room_selections["Casa B"].add("Cocina")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Casa B", "Cocina"], fps=30.0),
    ])
    monkeypatch.setattr(main_window, "_preguntar_por_el_choque", lambda *a: "fusionar")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]
    assert main_window.clips[1].categoria_path == ["Casa B", "Cocina"]  # no se toco
    assert main_window.room_selections["Casa B"].active_rooms().count("Cocina") == 1


def test_on_rooms_movidos_con_choque_renombra(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.room_selections["Casa B"].add("Cocina")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    monkeypatch.setattr(main_window, "_preguntar_por_el_choque", lambda *a: "renombrar")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina 2"]
    assert "Cocina" in main_window.room_selections["Casa B"].active_rooms()
    assert "Cocina 2" in main_window.room_selections["Casa B"].active_rooms()


def test_on_rooms_movidos_con_choque_cancelar_no_mueve_nada(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.room_selections["Casa B"].add("Cocina")
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    monkeypatch.setattr(main_window, "_preguntar_por_el_choque", lambda *a: "cancelar")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert main_window.clips[0].categoria_path == ["Casa A", "Cocina"]


def test_on_rooms_movidos_grupo_mixto_mueve_los_que_no_chocan_y_pregunta_por_el_resto(
    main_window, monkeypatch,
):
    _con_dos_unidades(main_window)
    main_window.room_selections["Casa A"].add("Comedor")
    main_window.room_selections["Casa B"].add("Cocina")   # choca
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
        Clip(orden=2, ruta=Path("/b.MP4"), categoria_path=["Casa A", "Comedor"], fps=30.0),
    ])
    preguntas = []

    def espia(nombre, unidad_origen, unidad_destino):
        preguntas.append(nombre)
        return "renombrar"

    monkeypatch.setattr(main_window, "_preguntar_por_el_choque", espia)

    main_window._on_rooms_movidos_a_unidad(["Cocina", "Comedor"], "Casa A", "Casa B")

    assert preguntas == ["Cocina"]   # Comedor no chocaba, no se pregunto por el
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina 2"]
    assert main_window.clips[1].categoria_path == ["Casa B", "Comedor"]


def test_on_rooms_movidos_expande_la_unidad_destino(main_window, monkeypatch):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window.room_rail.set_rooms_agrupados(
        unidades=["Casa A", "Casa B"],
        rooms_por_unidad={"Casa A": ["Cocina"], "Casa B": []}, counts={},
    )
    main_window.room_rail._on_toggle_de_banda("Casa B")

    main_window._on_rooms_movidos_a_unidad(["Cocina"], "Casa A", "Casa B")

    assert "Casa B" not in main_window.room_rail.unidades_colapsadas()
```

- [ ] **Step 2: Correr y confirmar que fallan**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -k "choque or on_rooms_movidos or nombre_libre" -v
```
Expected: FAIL.

- [ ] **Step 3: Implementar**

Junto a `_mover_cuarto_a_unidad`:

```python
    def _nombre_libre_en(self, catalogo: RoomSelection, base: str) -> str:
        existentes = set(catalogo.active_rooms())
        numero = 2
        candidato = f"{base} {numero}"
        while candidato in existentes:
            numero += 1
            candidato = f"{base} {numero}"
        return candidato

    def _conteo_de_cuarto(self, unidad: str, nombre: str) -> int:
        return sum(
            1 for c in self.clips
            if c.categoria_path and self._cuarto_de(c.categoria_path) == nombre
            and (self._unidad_de(c.categoria_path) or "") == unidad
        )

    def _preguntar_por_el_choque(self, nombre: str, unidad_origen: str,
                                  unidad_destino: str) -> str:
        """"fusionar" / "renombrar" / "cancelar" (spec 2026-09-21 S6).

        Aparte del `QMessageBox` para poder probar la decision sin abrir
        una ventana modal -- mismo criterio que `room_rail._crear_cuarto`.
        """
        conteo_origen = self._conteo_de_cuarto(unidad_origen, nombre)
        conteo_destino = self._conteo_de_cuarto(unidad_destino, nombre)
        etiqueta_origen = unidad_origen or SIN_UNIDAD_ETIQUETA
        renombrado = self._nombre_libre_en(self.room_selections[unidad_destino], nombre)
        cuadro = QMessageBox(self)
        cuadro.setWindowTitle(f'"{nombre}" ya existe en {unidad_destino}')
        cuadro.setText(f'"{nombre}" ya existe en {unidad_destino}')
        cuadro.setInformativeText(
            f'{etiqueta_origen} tiene {conteo_origen} clips en "{nombre}". '
            f'{unidad_destino} ya tiene su propia "{nombre}" con {conteo_destino} '
            "clips. ¿Qué quieres hacer?"
        )
        fusionar = cuadro.addButton("Fusionar", QMessageBox.ButtonRole.AcceptRole)
        renombrar = cuadro.addButton(f'Renombrar a "{renombrado}"',
                                      QMessageBox.ButtonRole.AcceptRole)
        cuadro.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        cuadro.setDefaultButton(renombrar)
        cuadro.exec()
        elegido = cuadro.clickedButton()
        if elegido is fusionar:
            return "fusionar"
        if elegido is renombrar:
            return "renombrar"
        return "cancelar"

    def _on_rooms_movidos_a_unidad(self, nombres: list[str], unidad_origen: str,
                                    unidad_destino: str) -> None:
        """El rail solto un grupo de cuartos sobre la banda de OTRA unidad.

        Mueve los que no chocan de una; por cada uno que si choca, abre SU
        PROPIO dialogo -- uno a la vez, no una lista (spec S6). Un nombre
        que ya no esta en el catalogo de origen (se movio o se borro entre
        el arrastre y ahora) se salta en silencio: ya no hay nada que
        mover.
        """
        catalogo_origen = self.room_selections.get(unidad_origen)
        if catalogo_origen is None:
            return
        catalogo_destino = self.room_selections.setdefault(unidad_destino, RoomSelection())
        for nombre in nombres:
            if nombre not in catalogo_origen.active_rooms():
                continue
            if nombre in catalogo_destino.active_rooms():
                resolucion = self._preguntar_por_el_choque(nombre, unidad_origen, unidad_destino)
                if resolucion == "cancelar":
                    continue
                nombre_destino = (
                    nombre if resolucion == "fusionar"
                    else self._nombre_libre_en(catalogo_destino, nombre)
                )
                self._mover_cuarto_a_unidad(
                    nombre, unidad_origen, unidad_destino,
                    nombre_destino=nombre_destino, fue_fusion=(resolucion == "fusionar"),
                )
            else:
                self._mover_cuarto_a_unidad(
                    nombre, unidad_origen, unidad_destino,
                    nombre_destino=nombre, fue_fusion=False,
                )
        self.room_rail.expandir_unidad(unidad_destino)
```

Agrega el import de `SIN_UNIDAD_ETIQUETA` (ya existe en `room_rail.py`) junto a los demás imports de `room_rail` en `main_window.py`:

```python
from clasificador_video.ui.room_rail import RoomRail, SIN_UNIDAD_ETIQUETA
```

(Ajusta a como ya esté escrito el import de `RoomRail` — solo agrega el nombre a la lista.)

- [ ] **Step 4: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Resolver el choque de nombre al mover un cuarto entre unidades

Tres salidas (spec S6): fusionar, renombrar a "Cocina 2" (default,
para no mezclar datos sin que Bruno lo pida) o cancelar. Con varios
cuartos arrastrados a la vez, los que no chocan se mueven de
inmediato y solo se pregunta uno por uno por los que si chocan. La
unidad destino se expande sola al terminar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Conectar todo — la señal del rail hasta `MainWindow`

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_unidades.py`

Los tasks 3-10 ya conectaron `unit_created` y probaron cada pieza por separado, invocando los métodos directo. Falta la última conexión: la señal real que sale de un arrastre de verdad.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_arrastrar_grupo_en_el_rail_llega_hasta_mover_cuarto(main_window):
    _con_dos_unidades(main_window)
    main_window.load_clips([
        Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Casa A", "Cocina"], fps=30.0),
    ])
    main_window.room_rail.mover_grupo_a_unidad(["Cocina"], "Casa A", "Casa B")
    assert main_window.clips[0].categoria_path == ["Casa B", "Cocina"]
```

- [ ] **Step 2: Correr y confirmar que falla**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -k arrastrar_grupo -v
```
Expected: FAIL — la señal no está conectada, no pasa nada.

- [ ] **Step 3: Conectar**

En el bloque de conexiones del rail (línea ~985-994, junto a `self.room_rail.unit_created.connect(...)` del Task 4):

```python
        self.room_rail.rooms_movidos_a_unidad.connect(self._on_rooms_movidos_a_unidad)
        self.room_rail.unidad_colapso_cambiado.connect(lambda *_: self._autosave())
```

- [ ] **Step 4: Correr y confirmar que pasa**

```bash
.venv/bin/pytest tests/ui/test_main_window_unidades.py -v
```
Expected: PASS.

- [ ] **Step 5: Correr TODA la suite**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Expected: PASS completo, sin excepciones. Si algo falla, es una interacción entre tasks que no se vio en aislamiento — para antes de seguir y arréglalo.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_unidades.py
git commit -m "$(cat <<'EOF'
Conectar el arrastre de cuartos entre unidades de punta a punta

Ultima conexion del spec 2026-09-21: rooms_movidos_a_unidad del rail
hasta _on_rooms_movidos_a_unidad, y unidad_colapso_cambiado hasta
autoguardar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Verificación manual con la app corriendo

No hay steps de TDD aquí — es la comprobación de que las piezas, ya integradas, se sienten como el mockup aprobado. Usa la skill `run` si el proyecto tiene una configurada, o arranca la app directo:

```bash
.venv/bin/python -m clasificador_video
```

- [ ] Crear un proyecto de prueba con 2-3 clips, crear dos unidades con el botón "+" del rail.
- [ ] Clasificar un par de cuartos en cada unidad.
- [ ] Colapsar una unidad con la flecha, confirmar que se esconden sus cuartos y el contador se queda visible.
- [ ] ⌘-clic en dos cuartos de la misma unidad, arrastrar uno de los dos hasta la banda de la otra unidad — confirmar que se mueven los DOS, con sus clips.
- [ ] Repetir el arrastre soltando en una unidad que YA tiene un cuarto con ese nombre — confirmar que aparece el diálogo con los tres conteos correctos, y probar las tres salidas por separado (en tres intentos, deshaciendo con ⌘Z entre cada uno).
- [ ] ⌘Z después de un move simple y después de una fusión — confirmar que cada uno regresa exactamente lo que movió.
- [ ] Cerrar y volver a abrir el proyecto — confirmar que la unidad que quedó colapsada sigue colapsada.
- [ ] Captura de pantalla del rail con el globo de arrastre a medio gesto (mockup `rail-arrastre.html`) para comparar contra el mockup aprobado — guárdala en el scratchpad de la sesión, no en el repo.

- [ ] **Commit final si hubo ajustes**

Si la verificación manual encuentra algo que corregir, arréglalo con su propio ciclo TDD (test que falla → implementación → test que pasa) y su propio commit — no lo dejes sin probar solo porque "ya se vio bien a simple vista".

---

## Resumen de archivos tocados

- `src/clasificador_video/history.py` — `CuartoMovido`, `HistoryEntry.cuarto_movido`.
- `src/clasificador_video/proyecto.py` — `unidades_colapsadas` en `a_dict`.
- `src/clasificador_video/app.py` — restaurar `unidades_colapsadas` en `_poblar_ventana`.
- `src/clasificador_video/ui/room_rail.py` — botón "+", bandas colapsables, selección múltiple, arrastre de grupo, drop entre unidades.
- `src/clasificador_video/ui/theme.py` — QSS de lo nuevo.
- `src/clasificador_video/ui/main_window.py` — `_mover_cuarto_a_unidad`, diálogo de choque, `_on_rooms_movidos_a_unidad`, wiring.
- `tests/test_history.py`, `tests/test_proyecto.py`, `tests/ui/test_room_rail_unidades.py`, `tests/ui/test_main_window_unidades.py`, y el archivo que cubre `_poblar_ventana` (Task 6).
