# Bins arrastrables — plan de implementación

> **Para quien ejecute esto:** SUB-SKILL REQUERIDA: usar
> `superpowers:subagent-driven-development` (recomendado) o
> `superpowers:executing-plans`, tarea por tarea. Los pasos llevan casilla.

**Meta:** que el bin sea una cosa propia y no un subproducto de importar — se
crea vacío, sobrevive vacío, y los clips se mueven entre bins arrastrando.

**Por qué existe este plan:** Bruno usó la primera entrega y dijo «yo te dije
que lo quería como Premiere. Quiero poder arrastrar los archivos a un bin». Y
tenía razón: el plan anterior interpretó «drag and drop en bins» como *arrastrar
carpetas desde el Finder*, y dejó fuera lo que hace que un bin sea un bin. Ver
la **§6.b del spec**, que corrige el alcance y deja escrito el error.

**Arquitectura:** nada nuevo. `BinTree` gana crear-vacío y mover; la hoja deja
de deducir qué bins existen a partir de las tarjetas y pasa a que se lo digan;
el arrastre de clips usa un mime propio y entra por el único gesto de mouse que
la hoja tenía libre.

**Spec:** `docs/superpowers/specs/2026-08-09-bins-por-camara-design.md`, **§6.b**

**Suite completa:**
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Hoy: **1007 tests en ~12 s**, verde. Tiene que seguir verde.

**Y córrela muchas veces.** En la entrega anterior hubo cuatro segfaults
intermitentes, y el último sobrevivió a decenas de corridas limpias. Contra un
fallo del 5 %, veinte corridas limpias salen por azar el 36 % de las veces. Al
cerrar cada fase: **contar fallos sobre 40 corridas**, no «corrió bien».

---

## El nudo del asunto, antes de las tareas

Hay **dos** cosas que hoy están enredadas y que este plan desenreda. Quien
ejecute esto tiene que entenderlas antes de escribir la primera línea.

### 1. La hoja deduce los bins de las tarjetas

`ClipSheet._regroup` recorre `self.item_widgets`, saca de cada tarjeta su
`(bin, cuarto)` y de ahí arma la lista de bins. Consecuencia directa:
**un bin sin clips no existe para la hoja.** Y esa es exactamente la cosa que
hay que poder crear.

El cambio: los bins **se declaran** con `set_bin_order`, y `_regroup` recorre
esa lista —no las tarjetas— para decidir qué encabezados van y en qué orden.
Los bloques de cuarto se siguen deduciendo de las tarjetas.

### 2. «Sin bin» tiene que ir primero, y hoy va último

`_orden_de_grupo` da a un bin desconocido la posición `len(self._bin_order)`,
o sea el final. Los clips sin bin tienen `bin_nombre == ""` y caen ahí. El spec
§6.b los quiere **arriba de todo**: son la cola de trabajo, igual que «Sin
clasificar» dentro de un bin.

### 3. El gesto de arrastre no choca con nada — y eso hay que conservarlo

Medido leyendo el código, no supuesto:

| Gesto | Qué hace hoy |
|---|---|
| Mouse **sin apretar** sobre una tarjeta | escrubea la miniatura (`ClipCard` tiene `setMouseTracking(True)`, línea ~371) |
| Arrastrar en el **vacío** del viewport | marquesina (`eventFilter`, ~2156) |
| Mantener `1`–`9` y mover | pincel (`_pincel_activo`) |
| **Botón izquierdo apretado + mover sobre una tarjeta** | **nada** |

El arrastre de clips va en ese último hueco. **No es casualidad, es la razón de
elegirlo.**

---

## Estructura de archivos

| Archivo | Qué cambia |
|---|---|
| `src/clasificador_video/bins.py` | `crear_vacio`, `mover`, y que un bin vacío no se pode |
| `src/clasificador_video/ui/clip_sheet.py` | bins declarados; sección «Sin bin»; botón «+ Bin nuevo»; iniciar y recibir el arrastre de clips |
| `src/clasificador_video/ui/main_window.py` | arrancar en hoja; crear bin; mover clips; guardar |
| `src/clasificador_video/ui/theme.py` | QSS del botón y del resaltado de destino |
| `tests/test_bins.py`, `tests/ui/test_clip_sheet*.py`, `tests/ui/test_main_window_bins.py` | lo suyo |

---

# FASE 7 — La hoja es lo primero que se ve

### Tarea 1: arrancar en modo hoja

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py` (`__init__`, ~296)
- Test: `tests/ui/test_main_window.py`

- [ ] **Paso 1: escribir el test que falla**

```python
def test_la_app_arranca_en_la_hoja(qtbot):
    """Lo primero que Bruno ve es el material, no un visor vacio.

    Pedido suyo, textual: «quiero que la parte de hoja sea lo primero que se
    vea». Antes arrancaba en modo clip, o sea con un visor negro hasta que
    importaras algo.
    """
    window = _window(qtbot)

    assert window._modo_hoja is True
    assert window.clip_sheet.isVisible() or not window.video_stage.isVisible()
```

> Comprobar el nombre real del ayudante (`_window`) en ese archivo y usarlo.

- [ ] **Paso 2: correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -q -k arranca
```
Esperado: `assert False is True`

- [ ] **Paso 3: implementar**

En `__init__`, después de armar las tres filas y **antes** de mostrar nada,
entrar al modo hoja por el mismo camino que usa `⇥` — no duplicando su lógica:

```python
        # Arranca en la hoja: es lo primero que Bruno quiere ver. Se hace
        # llamando al mismo metodo que la tecla, y no poniendo el flag a
        # mano, porque el modo tambien esconde el visor y la columna de
        # herramientas; dos caminos para lo mismo se desincronizan.
        self.alternar_modo_hoja()
```

> **Cuidado:** `alternar_modo_hoja` toca `_solo_video` y mueve el foco. Si al
> llamarlo en el constructor algo todavía no existe, **no lo adelantes con un
> flag**: mueve la llamada al final del constructor. Si aun así no se puede,
> repórtalo en vez de improvisar un tercer camino.

- [ ] **Paso 4: correr la suite completa**

Varios tests dan por hecho que se arranca en modo clip. **Ajústalos** — el
comportamiento nuevo es el correcto — y deja en cada uno un comentario de por
qué se tocó.

- [ ] **Paso 5: commit**

```bash
git add -A
git commit -m "feat: la app abre en la hoja de contactos

Pedido de Bruno: lo primero que ve tiene que ser el material, no un
visor vacio.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# FASE 8 — El bin existe aunque esté vacío

### Tarea 2: `BinTree.crear_vacio` y `BinTree.mover`

**Archivos:**
- Modificar: `src/clasificador_video/bins.py`
- Test: `tests/test_bins.py`

- [ ] **Paso 1: escribir los tests que fallan**

```python
def test_un_bin_vacio_existe_y_se_queda():
    """Si un bin sin clips desapareciera, no se podria crear primero y
    llenar despues -- que es justo el gesto que se esta agregando."""
    arbol = BinTree()
    arbol.crear_vacio("Dron")

    assert arbol.nombres() == ["Dron"]
    assert arbol.clips_de("Dron") == []


def test_crear_vacio_no_repite_nombres():
    arbol = BinTree()
    arbol.crear_vacio("Dron")

    assert arbol.crear_vacio("Dron") == "Dron 2"


def test_mover_saca_del_bin_viejo_y_mete_en_el_nuevo():
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [0, 1, 2])
    arbol.crear_vacio("Dron")

    arbol.mover([0, 2], "Dron")

    assert arbol.clips_de("Sony") == [1]
    assert arbol.clips_de("Dron") == [0, 2]


def test_mover_a_ningun_bin_los_deja_sueltos():
    """`None` es «sacalo de donde este»: los clips sueltos son un estado
    valido, no un error. Van a la seccion «Sin bin»."""
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [0, 1])

    arbol.mover([0], None)

    assert arbol.clips_de("Sony") == [1]
    assert arbol.bin_de(0) is None


def test_mover_a_su_propio_bin_no_hace_nada():
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [0, 1])

    arbol.mover([0], "Sony")

    assert arbol.clips_de("Sony") == [0, 1]


def test_mover_conserva_el_orden_de_llegada():
    """El orden dentro del bin es el orden de rodaje, no el de arrastre:
    de el vive la nocion de «el clip anterior»."""
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [5])
    arbol.crear_vacio("Dron")

    arbol.mover([3, 1], "Dron")

    assert arbol.clips_de("Dron") == [1, 3]
```

- [ ] **Paso 2: correr y ver que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
```
Esperado: `AttributeError: 'BinTree' object has no attribute 'crear_vacio'`

- [ ] **Paso 3: implementar**

```python
    def crear_vacio(self, nombre: str) -> str:
        """Un bin sin clips todavia.

        Existe porque el gesto que Bruno pidio es el de Premiere: creas el
        bin y luego le arrastras material. Nada lo poda cuando se queda sin
        clips -- si se podara, el bin desapareceria en el instante entre
        crearlo y soltarle el primer clip.
        """
        return self.agregar(nombre or "Bin", Path(""), [])

    def mover(self, indices: list[int], destino: str | None) -> None:
        """Cambia de bin a esos clips y NADA mas.

        No toca el indice de ningun clip, y por eso no hay que correr
        `_proxy_sizes`, `_clip_durations` ni el historial: mover entre bins
        es solo cambiar de lista quien esta en cual. Ese es el motivo de que
        esta operacion sea barata, y conviene que siga siendolo.

        `destino=None` los deja sueltos, que es un estado valido: caen en la
        seccion «Sin bin».
        """
        moviendo = set(indices)
        for b in self._bins:
            if b.nombre != destino:
                b.clips = [i for i in b.clips if i not in moviendo]
        if destino is None:
            return
        for b in self._bins:
            if b.nombre == destino:
                ya = set(b.clips)
                # ordenados: el orden dentro del bin es el de rodaje, no el
                # del arrastre
                b.clips = sorted(ya | moviendo)
                return
```

- [ ] **Paso 4: correr y ver que pasan** — 6 passed

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/bins.py tests/test_bins.py
git commit -m "feat: bins vacios, y mover clips de un bin a otro

Mover no toca el indice de ningun clip: por eso no hay que correr nada
de lo que va indexado por clip. Es lo que hace barata la operacion.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 3: la hoja deja de deducir los bins y pasa a que se los digan

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (`_regroup` ~1775,
  `_sincronizar_encabezados` ~1826, `_orden_de_grupo`)
- Test: `tests/ui/test_clip_sheet.py`

> **Esta es la tarea con más radio de impacto del plan.** Léela entera antes de
> tocar nada.

- [ ] **Paso 1: escribir los tests que fallan**

```python
def test_un_bin_sin_clips_igual_aparece(qtbot):
    """El gesto de Premiere es crear el bin y despues llenarlo. Si el bin
    vacio no se dibuja, no hay a donde arrastrar."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert hoja.bin_headers() == ["Sony", "Dron"]
    assert hoja.bin_header_widget("Dron") is not None


def test_los_clips_sin_bin_van_primero_y_en_su_seccion(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="")])

    assert hoja.bin_headers() == [SIN_BIN, "Sony"]


def test_la_seccion_sin_bin_se_esconde_cuando_no_hay_sueltos(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    assert hoja.bin_headers() == ["Sony"]


def test_un_bin_vacio_no_desaparece_al_refrescar(qtbot):
    """`_regroup` corre en cada tecla. Si el bin vacio solo sobreviviera a
    la primera pasada, se iria al primer pick."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    hoja.update_clips([_thumb(0, bin_nombre="Sony", flag="pick")])

    assert hoja.bin_headers() == ["Sony", "Dron"]
```

- [ ] **Paso 2: correr y ver que fallan**

- [ ] **Paso 3: implementar**

Una constante al lado de `SIN_CLASIFICAR`:

```python
SIN_BIN = "Sin bin"
```

`_group_of` mapea el vacío a esa constante:

```python
    def _group_of(self, clip: ClipThumbnail) -> tuple[str, str]:
        return (clip.bin_nombre or SIN_BIN,
                clip.room_label or SIN_CLASIFICAR)
```

`_orden_de_grupo` pone «Sin bin» primero:

```python
    def _orden_de_grupo(self, clave: tuple[str, str]) -> tuple:
        bin_nombre, cuarto = clave
        if bin_nombre == SIN_BIN:
            pos = -1          # la cola de trabajo va arriba, como «Sin clasificar»
        elif bin_nombre in self._bin_order:
            pos = self._bin_order.index(bin_nombre)
        else:
            pos = len(self._bin_order)
        return (pos, bin_nombre, cuarto != SIN_CLASIFICAR, cuarto)
```

Y en `_regroup`, la lista de bins presentes deja de salir de las tarjetas:

```python
        # Los bins los DECLARA quien llama, no se deducen de las tarjetas:
        # un bin recien creado no tiene ninguna, y es justo el que hay que
        # dibujar para poder arrastrarle clips.
        con_clips = {b for b, _ in titulos}
        bins_presentes = ([SIN_BIN] if SIN_BIN in con_clips else []) + list(self._bin_order)
        self._sincronizar_encabezados(bins_presentes)
```

Y el bucle que llena el layout recorre `bins_presentes`, poniendo el encabezado
de cada uno y después **los bloques que le toquen, si tiene**:

```python
        while self._content_layout.count():
            self._content_layout.takeAt(0)
        for bin_nombre in bins_presentes:
            self._content_layout.addWidget(self._bin_headers[bin_nombre])
            for titulo in titulos:
                if titulo[0] == bin_nombre:
                    self._content_layout.addWidget(self._blocks[titulo])
        self._content_layout.addWidget(self._zona_nueva)
        self._refrescar_encabezados()
```

> **Tres cosas que NO se pueden romper aquí**, las tres con test propio ya
> existente en el repo:
> 1. `_relayout()` va **antes** de sacar los bloques vacíos. Un bloque sin
>    padre se destruye y se lleva las tarjetas con su miniatura ya cargada
>    (rompe `test_reclasificar_mueve_la_tarjeta_sin_recrearla`).
> 2. Sacar un widget del layout se hace con `takeAt`, que no reparenta.
>    Desecharlo es `_desechar` (`hide` + `setParent(None)` + `deleteLater`),
>    nunca `setParent(None)` a secas: eso lo destruye en el acto y ya costó un
>    segfault.
> 3. La Regla 1 de `ClipSheet`: `item_widgets` sigue el orden de `self.clips`,
>    no el visual.

- [ ] **Paso 4: correr la suite completa y arreglar lo que caiga**

- [ ] **Paso 5: verificación visual — obligatoria**

`grab()` de la hoja con: un bin con clips, un bin **vacío**, y la sección «Sin
bin» arriba. Guardar el PNG **en el scratchpad, nunca en el repo**, y abrirlo
para mirarlo. Comprobar que el encabezado de un bin vacío no queda desalineado
ni deja un hueco raro donde irían sus tarjetas.

- [ ] **Paso 6: commit**

---

### Tarea 4: el botón «+ Bin nuevo»

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (la barra de la hoja),
  `src/clasificador_video/ui/theme.py`, `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_clip_sheet.py`, `tests/ui/test_main_window_bins.py`

- [ ] **Paso 1: tests**

```python
def test_el_boton_pide_un_bin_nuevo(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    pedidos = []
    hoja.bin_nuevo_pedido.connect(lambda: pedidos.append(1))

    hoja.boton_bin_nuevo.click()

    assert pedidos == [1]
```

```python
def test_crear_un_bin_lo_deja_listo_para_recibir_clips(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana._on_bin_nuevo_pedido()

    assert "Bin" in ventana.bins.nombres()[-1]
    assert ventana.clip_sheet.bin_headers()[-1] == ventana.bins.nombres()[-1]


def test_el_bin_nuevo_se_guarda(qtbot, tmp_path, ventana):
    ventana.session_path = tmp_path / "sesion.json"
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana._on_bin_nuevo_pedido()
    ventana._write_autosave_now()
    assert ventana._autosave_pool.waitForDone(2000)

    data = json.loads((ventana.session_path).read_text())
    assert data["bins"][-1]["clips"] == []
```

- [ ] **Paso 2: correr y ver que fallan**

- [ ] **Paso 3: implementar**

En la barra de la hoja (donde ya viven el título `CLIPS · N` y el buscador), un
botón con señal `bin_nuevo_pedido`. En `MainWindow`:

```python
    def _on_bin_nuevo_pedido(self) -> None:
        """Un bin vacio, listo para que le arrastres clips.

        Nace con un nombre generico y el encabezado entra en modo edicion en
        el acto: ponerle nombre es parte de crearlo, no un segundo paso que
        haya que recordar.
        """
        nombre = self.bins.crear_vacio("Bin")
        self._refresh_sheet()
        cabecera = self.clip_sheet.bin_header_widget(nombre)
        if cabecera is not None:
            cabecera.empezar_a_renombrar()
        self._autosave()
```

> `empezar_a_renombrar` ya existe en `_BinHeader` como parte del doble clic —
> **reúsala, no escribas otra**. Si tiene otro nombre en el código, usa el del
> código.

QSS del botón en `theme.py`, siguiendo la forma exacta de `build_stylesheet`.

- [ ] **Paso 4: correr, verificación visual del botón en la barra, commit**

La barra ya lleva título, buscador y una pista de texto. Comprobar con `grab()`
a **1027 px** —el mínimo real de la ventana— que el botón no empuja nada fuera.

---

# FASE 9 — Arrastrar clips

### Tarea 5: iniciar el arrastre desde una tarjeta

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (`ClipCard`, ~547-575)
- Test: `tests/ui/test_clip_sheet_drop.py`

- [ ] **Paso 1: tests**

```python
MIME_CLIPS = "application/x-clasificador-clips"


def test_mover_con_el_boton_apretado_arranca_un_arrastre(qtbot):
    """El hueco libre de la hoja: escrubear es AL PASAR sin apretar, la
    marquesina es en el vacio, y el pincel pide una tecla de cuarto.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0), _thumb(1)])
    tarjeta = hoja.item_widgets[0]
    arrastres = []
    tarjeta.arrastre_pedido.connect(arrastres.append)

    tarjeta.mousePressEvent(_press(QPoint(5, 5)))
    tarjeta.mouseMoveEvent(_move(QPoint(60, 60), boton=True))

    assert arrastres == [0]


def test_un_temblor_no_arranca_un_arrastre(qtbot):
    """Un clic con la mano temblorosa sigue siendo un clic: el arrastre
    arranca al superar la distancia estandar de Qt, no al primer pixel."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    tarjeta = hoja.item_widgets[0]
    arrastres = []
    tarjeta.arrastre_pedido.connect(arrastres.append)

    tarjeta.mousePressEvent(_press(QPoint(5, 5)))
    tarjeta.mouseMoveEvent(_move(QPoint(7, 6), boton=True))

    assert arrastres == []


def test_pasar_sin_apretar_sigue_escrubeando(qtbot):
    """La regresion que este plan no puede causar: el escrubeo al pasar el
    mouse es de lo que Bruno mas usa."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    tarjeta = hoja.item_widgets[0]
    tarjeta._frames = [_pixmap(), _pixmap(), _pixmap()]
    arrastres = []
    tarjeta.arrastre_pedido.connect(arrastres.append)

    tarjeta.mouseMoveEvent(_move(QPoint(60, 60), boton=False))

    assert arrastres == []
    assert tarjeta._hover is not None


def test_con_el_pincel_activo_no_hay_arrastre(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0)])
    hoja.set_pincel_activo(True)
    tarjeta = hoja.item_widgets[0]
    arrastres = []
    tarjeta.arrastre_pedido.connect(arrastres.append)

    tarjeta.mousePressEvent(_press(QPoint(5, 5)))
    tarjeta.mouseMoveEvent(_move(QPoint(60, 60), boton=True))

    assert arrastres == []
```

> `_press` y `_move` son ayudantes que construyen `QMouseEvent`. Escríbelos una
> vez arriba del archivo. Los nombres reales ya están comprobados contra el
> código: `set_pincel_activo`, `set_selected`, `bin_headers`,
> `bin_header_widget` y `empezar_a_renombrar` existen tal cual.

- [ ] **Paso 2: correr y ver que fallan**

- [ ] **Paso 3: implementar en `ClipCard`**

```python
    arrastre_pedido = Signal(int)   # indice de clip
```

```python
    def mousePressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._origen_arrastre = event.position().toPoint()
            self.clicked.emit(event.modifiers())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Dos gestos en el mismo evento, separados por si hay boton apretado.

        SIN boton (que llega porque la tarjeta tiene `setMouseTracking`):
        escrubea la miniatura, como siempre. CON boton: arrastra el clip.
        Son excluyentes por construccion, que es lo que evita que arrastrar
        deje la miniatura en un cuadro al azar.
        """
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self._puede_arrastrar(event.position().toPoint()):
                self.arrastre_pedido.emit(self.indice)
            return
        self.escrubear_a(event.position().x() / max(self.width(), 1))
        super().mouseMoveEvent(event)

    def _puede_arrastrar(self, punto) -> bool:
        if self._origen_arrastre is None:
            return False
        distancia = (punto - self._origen_arrastre).manhattanLength()
        return distancia >= QApplication.startDragDistance()
```

> `ClipCard` hoy **no conoce su índice**. Pasárselo es parte de esta tarea:
> `set_clips` y `append_clips` ya lo tienen a la mano cuando conectan las
> señales. No lo deduzcas buscándolo en la lista en cada evento.
>
> El pincel: la tarjeta pregunta a la hoja, o la hoja ignora la señal mientras
> `_pincel_activo`. **Prefiere lo segundo** — la tarjeta no tiene por qué
> conocer los modos de la hoja.

- [ ] **Paso 4: correr, commit**

---

### Tarea 6: soltar clips en un bin

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (arrastre), `main_window.py`
- Test: `tests/ui/test_clip_sheet_drop.py`, `tests/ui/test_main_window_bins.py`

- [ ] **Paso 1: tests**

```python
def test_soltar_clips_sobre_un_bin_avisa_a_cual(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Sony")])
    recibido = []
    hoja.clips_movidos.connect(lambda idx, destino: recibido.append((idx, destino)))

    cabecera = hoja.bin_header_widget("Dron")
    centro = cabecera.mapTo(hoja, cabecera.rect().center())
    _soltar_clips(hoja, [0, 1], centro)

    assert recibido == [([0, 1], "Dron")]


def test_soltar_clips_en_sin_bin_los_deja_sueltos(qtbot):
    ...
    assert recibido == [([0], None)]


def test_se_va_toda_la_seleccion_no_solo_el_que_arrastraste(qtbot):
    """Arrastrar uno de tres seleccionados se lleva los tres: es lo que hace
    Finder y lo que hace Premiere."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([_thumb(i, bin_nombre="Sony") for i in range(3)])
    hoja.set_selected({0, 1, 2})

    assert hoja.indices_a_arrastrar(1) == [0, 1, 2]


def test_arrastrar_uno_no_seleccionado_se_lleva_solo_ese(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(i) for i in range(3)])
    hoja.set_selected({0, 1})

    assert hoja.indices_a_arrastrar(2) == [2]
```

```python
def test_mover_clips_cambia_el_bin_y_nada_mas(qtbot, ventana):
    """Lo que hace barata esta operacion: no toca indices, asi que no hay
    que correr proxies, duraciones ni historial.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.crear_vacio("Dron")
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)
    ventana.clips[0].categoria_path = ["Cocina"]

    ventana._on_clips_movidos([0], "Dron")

    assert ventana.bins.bin_de(0) == "Dron"
    assert ventana.clips[0].ruta_proxy == Path("/cam/AS03.MP4")   # se lo lleva
    assert ventana._proxy_sizes[0] == (1080, 1920)
    assert ventana.clips[0].categoria_path == ["Cocina"]          # el cuarto no se toca
    assert ventana.clips[0].orden == 1                             # ni el orden


def test_soltar_en_el_cuarto_de_otro_bin_no_reclasifica(qtbot, ventana):
    """Decision de Bruno: arrastrar es para acomodar por camara. El cuarto
    se sigue poniendo con el teclado -- un arrastre mal soltado no puede
    cambiarte el dato que mas trabajo cuesta.
    """
    ...
```

- [ ] **Paso 2: correr y ver que fallan**

- [ ] **Paso 3: implementar**

- `ClipSheet` gana `clips_movidos = Signal(list, object)` y
  `indices_a_arrastrar(indice)`.
- `arrastre_pedido` arma un `QDrag` con un `QMimeData` que lleva los índices
  bajo `application/x-clasificador-clips`, y una imagen de arrastre con la
  miniatura del clip y, si son varios, la cuenta.
- `dragEnterEvent`/`dragMoveEvent`/`dropEvent` **distinguen los dos mimes**:
  URLs de archivo (material nuevo, lo de la fase 5 anterior) contra el mime
  interno (mover clips). El resaltado del bin de destino se reusa; el texto
  cambia a «mover N clips aquí».
- Soltar sobre la sección «Sin bin» manda `destino=None`.
- En `MainWindow`:

```python
    def _on_clips_movidos(self, indices: list[int], destino: str | None) -> None:
        self.bins.mover(indices, destino)
        self._refresh_sheet()
        self._autosave()
```

> **Soltar un clip en su propio bin no debe hacer nada** — ni refrescar, ni
> guardar, ni mover el scroll. Es el caso más común de arrastre fallido.

- [ ] **Paso 4: correr la suite, contar fallos sobre 40 corridas**

- [ ] **Paso 5: verificación visual — obligatoria**

`grab()` de: el arrastre en curso con el bin de destino resaltado, y la imagen
de arrastre con tres clips. **Mirar los PNG.**

- [ ] **Paso 6: commit**

---

# FASE 10 — Cierre

### Tarea 7: barrido y documentación

- [ ] La suite completa, **40 corridas contadas**, cero fallos. Si aparece uno,
      es un bug a resolver, no ruido a promediar: la entrega anterior enseñó
      que «corrió limpio veinte veces» no prueba nada contra un fallo del 5 %.
- [ ] `git status` limpio, nada suelto en la raíz, ningún PNG del scratchpad
      dentro del repo.
- [ ] Recorrido completo a mano, con `grab()` en cada paso y **mirando** los
      PNG: abrir → la hoja es lo primero → crear un bin vacío → arrastrarle
      clips desde otro bin → sacar uno a «Sin bin» → cerrar y reabrir, y que
      todo siga donde lo dejaste.
- [ ] Actualizar el handoff: qué quedó **medido** y qué **supuesto**, con el
      mismo criterio de siempre. Y decir explícitamente lo que sigue sin
      probarse: **nadie ha usado esto con material real**.
- [ ] **NO reconstruir la `.app`** — Bruno pidió expresamente abrirla desde la
      terminal con `.venv/bin/clasificador`.

## Lo que este plan NO hace

- **Arrastrar para cambiar de cuarto.** Decisión de Bruno: los cuartos van con
  el teclado. Si algún día se quiere, se diseña aparte.
- **Bins anidados.**
- **Reordenar los bins arrastrando sus encabezados.**
- **Que el bin viaje a Premiere como carpeta del proyecto.**
- **LUT por bin** y **generar los proxies del dron** — siguen pendientes, de
  antes.
