# F8 del rediseño — Modo hoja y pincel — Implementation Plan

> **Para quien lo ejecute:** las tareas van con checkbox (`- [ ]`) y el test se
> escribe **antes** que la implementación, como en los cuatro planes
> anteriores.

**Goal:** que clasificar 128 clips deje de ser «uno por uno» y pase a ser «por
rachas». La hoja a pantalla completa da el contexto, y el pincel convierte
seleccionar-y-asignar en un solo gesto.

**Punto de partida:** 647 tests en verde, F0–F7 hechas. Ver
`docs/superpowers/ANALISIS-2026-08-08-post-f7.md`.

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

**Referencias:**
- Comportamiento acordado: `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`
  («Pincel de cuarto», «Desplazamiento entre modos», «Miniaturas escrubeables»)
- Candados anti-deriva: `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md`

---

## Advertencias antes de empezar

1. **Esta fase toca la hoja, que es donde viven los bugs difíciles de este
   proyecto.** Las tres reglas del docstring de `ClipSheet` --`item_widgets` va
   por índice de clip y no por posición visual; agrupar es re-colocar, jamás
   reconstruir; el ancho disponible se mide en el viewport-- tienen cada una un
   bug real detrás. Releerlas antes de tocar nada.

2. **El pincel arrastra sobre las tarjetas, y ahí ya hubo un SIGSEGV.**
   Reconstruir la hoja dentro del `mousePressEvent` de una tarjeta destruye el
   widget que está manejando el evento, y en el run loop nativo de macOS eso
   revienta. Por eso la Task 14 es un **spike**, no código de producción: si
   arrastrar sobre las tarjetas no se puede hacer estable, el pincel se
   reconsidera antes de construirlo, no después.

3. **Lo que ya existe y NO hay que rehacer**: la tira de frames por clip
   (`ClipCard.set_frames`), el escrubeo al pasar el mouse
   (`mouseMoveEvent` + `_show_frame`), la selección múltiple con `⇧`+click y
   `⌘A`, y el re-acomodo por ancho disponible. La F8 les agrega la barrita de
   progreso y el timecode que el mockup dibuja encima, no el mecanismo.

4. **Dos vistas del mismo estado se contradicen solas.** Ya pasó tres veces
   (la tarjeta y la barra de rango, el control de velocidad, el badge `auto`).
   El modo hoja es una vista más del mismo clip actual: si guarda su propio
   «cuál es el actual», se desincroniza.

5. **Cuidado con el mínimo de la hoja.** A pantalla completa la hoja ya no
   compite con el video, pero al volver al modo clip sí. El test
   `test_la_hoja_puede_encogerse_para_dejarle_ancho_al_video` es el guardián:
   si se pone rojo, algo nuevo está empujando el ancho.

6. **Los tests de abajo usan cosas que todavía no existen.** Se crean primero,
   o los tests revientan con `AttributeError` — que es rojo, pero del rojo
   equivocado, y esconde si la función que sí importa funciona. Pasó al
   auditar el plan de la F6. Lo que hay que crear antes:

   | Qué | Dónde | Para qué |
   |---|---|---|
   | `ClipSheet.columnas_visibles()` | `ui/clip_sheet.py` | contar columnas sin medir píxeles |
   | `ClipSheet.current_index()` | `ui/clip_sheet.py` | el clip actual **leído de la hoja**, no un segundo estado |
   | `ClipSheet.orden_visual()` | `ui/clip_sheet.py` | el orden de las tarjetas, para probar que no se reagrupan mientras pintas |
   | `ClipSheet.agrandar()` / `achicar()` | `ui/clip_sheet.py` | el paso de `+`/`−` |
   | `ClipCard.doble_click` | `ui/clip_sheet.py` | señal nueva; hoy solo existe `clicked` |
   | `ClipCard.escrubear_a(fraccion)` | `ui/clip_sheet.py` | escrubear sin simular un mouse |
   | `_card(qtbot, frames=N)` | `tests/ui/test_clip_sheet.py` | helper: hoy cada test arma su tarjeta a mano |
   | `_thumb(i)` | `tests/ui/test_clip_sheet.py` | comprobar cuál es el nombre real antes de usarlo |

---

## Task 14: Spike del pincel — **antes de cualquier plan de implementación**

**Files:**
- Spike: al scratchpad de la sesión, **no al repo**

**Qué hay que demostrar**, con una hoja de 128 tarjetas reales:

| Pregunta | Cómo se responde |
|---|---|
| ¿Se puede saber qué tarjeta está bajo el cursor mientras arrastras? | `childAt()` sobre el contenedor, o un `eventFilter` en la hoja. Medir cuál da la posición correcta con el scroll movido |
| ¿Sobrevive a pintar 20 tarjetas seguidas sin reconstruir la hoja? | Contar widgets vivos **después de procesar los `DeferredDelete`** y comprobar que no crashea |
| ¿Cuánto cuesta teñir una tarjeta al tocarla? | Debe quedar bajo 16.7 ms por movimiento de mouse, o el rastro se siente pegajoso |
| ¿El cursor puede llevar su carga visible? | `QCursor` con pixmap propio, o un widget que sigue al mouse. El segundo es más flexible y no depende del sistema |

- [ ] **Step 1: Construirlo en el scratchpad** con `_datos_de_ejemplo.py`.
- [ ] **Step 2: Medir las cuatro respuestas y escribirlas.**
- [ ] **Step 3: Decidir.** Si arrastrar sobre las tarjetas no es estable, el
      pincel se reemplaza por el camino ya probado --marquesina y después
      asignar-- y se anota en `DECISIONES.md` con la medición, como se hizo
      con la precarga en la F6.

---

## Task 15: El modo hoja

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`, `ui/clip_sheet.py`
- Test: `tests/ui/test_main_window.py`, `tests/ui/test_clip_sheet.py`

`⇥` alterna. En modo hoja la hoja ocupa la ventana y el video se esconde; en
modo clip, todo como hoy.

**Lo que comparten los dos modos** (DECISIONES.md, «Desplazamiento entre
modos»): el clip actual, la selección y el scroll. Nada se pierde al cruzar —
es lo que Lightroom hace mal y no hay razón para copiarlo.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_tab_alterna_entre_los_dos_modos(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("tab")
    assert window.video_stage.isHidden()
    assert not window.clip_sheet.isHidden()
    window.handle_key_press("tab")
    assert not window.video_stage.isHidden()


def test_el_clip_actual_sobrevive_el_cruce(qtbot):
    """`⇥` lleva SIEMPRE al clip actual, en los dos sentidos."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(i) for i in range(1, 6)])
    window.select_clip(3)
    window.handle_key_press("tab")
    assert window.clip_sheet.current_index() == 3
    window.handle_key_press("tab")
    assert window.current_index == 3


def test_la_seleccion_sobrevive_el_cruce(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(i) for i in range(1, 8)])
    window._on_selection_changed([1, 2, 3])
    window.handle_key_press("tab")
    window.handle_key_press("tab")
    assert window.selected_indices == [1, 2, 3]


def test_esc_vuelve_a_la_hoja_desde_el_modo_clip(qtbot):
    """Salida obvia, sin pensar. Y NO puede pisar el `esc` de solo video, que
    ya existe desde la F7."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("f")            # solo video
    window.handle_key_press("escape")       # sale de solo video...
    assert not window.room_rail.isHidden()
    window.handle_key_press("escape")       # ...y recien ahora va a la hoja
    assert window.video_stage.isHidden()


def test_doble_click_en_una_tarjeta_abre_ese_clip(qtbot):
    """El gesto de Grid → Loupe. No colisiona con nada: `⏎` sigue siendo la
    paleta."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1), _clip(2)])
    window.handle_key_press("tab")
    window.clip_sheet.item_widgets[1].doble_click.emit(1)
    assert window.current_index == 1
    assert not window.video_stage.isHidden()


def test_en_modo_hoja_las_teclas_siguen_clasificando(qtbot):
    """La hoja no es un visor aparte: sigues marcando y asignando."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.handle_key_press("tab")
    window.handle_key_press("1")
    assert window.clips[0].categoria_path == ["Cocina"]
```

```python
# tests/ui/test_clip_sheet.py
def test_a_pantalla_completa_la_hoja_arma_siete_columnas(qtbot):
    """El numero del mockup. Con menos, las tarjetas quedan enormes y se
    pierde el contexto que es la razon de este modo."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(20)])
    hoja.resize(1600, 900)
    qtbot.wait(50)
    assert hoja.columnas_visibles() == 7
```

- [ ] **Step 2: Implementar.** El modo vive en `MainWindow` --es quien conoce
  los dos paneles-- y `ClipSheet` solo recibe el ancho nuevo. `⇥` NO puede
  usarse con `QShortcut` a secas sin comprobar el foco: dentro de un campo de
  texto `⇥` es «pasar al siguiente control» (ver la guarda de la F6).
- [ ] **Step 3: Verificar** — arnés con `--pantalla 1`, que hasta hoy compara
  la hoja del mockup contra el modo clip de la app y por eso no dice nada.

---

## Task 16: `+` / `−` — tamaño de miniatura

**Files:**
- Modify: `ui/clip_sheet.py`, `ui/main_window.py`
- Test: `tests/ui/test_clip_sheet.py`

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_mas_y_menos_cambian_el_tamano_de_las_tarjetas(qtbot):
    hoja = _sheet(qtbot, [_thumb(i) for i in range(12)])
    hoja.resize(1200, 800)
    qtbot.wait(50)
    antes = hoja.item_widgets[0].width()
    hoja.agrandar()
    qtbot.wait(50)
    assert hoja.item_widgets[0].width() > antes


def test_el_tamano_tiene_tope_por_los_dos_lados(qtbot):
    """Sin topes, `−` repetido deja tarjetas de 3 px y `+` una sola tarjeta
    por pantalla: los dos casos son inservibles."""
    hoja = _sheet(qtbot, [_thumb(i) for i in range(12)])
    for _ in range(20):
        hoja.achicar()
    assert hoja.item_widgets[0].width() >= MIN_TILE_WIDTH
    for _ in range(40):
        hoja.agrandar()
    assert hoja.columnas_visibles() >= 2
```

- [ ] **Step 2: Implementar.** El paso de tamaño es un multiplicador sobre
  `MIN_TILE_WIDTH`, no un ancho absoluto: el re-acomodo por viewport ya
  resuelve cuántas columnas caben, y meterle un ancho fijo lo pelearía.
- [ ] **Step 3: Verificar** — capturas en los dos extremos.

---

## Task 17: La barrita de escrubeo sobre la miniatura

**Files:**
- Modify: `ui/clip_sheet.py` (`_CardOverlay`)
- Test: `tests/ui/test_clip_sheet.py`

El escrubeo **ya funciona** desde el diseño viejo. Falta lo que el mockup
dibuja encima: la barrita de progreso (`.hoverbar`) y el timecode
(`.hovertc`), y que la portada sea el frame del 25 % y no el del medio.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_la_portada_es_el_frame_del_25_por_ciento(qtbot):
    """En un recorrido el primer frame suele ser una puerta o movimiento
    borroso, y el del medio puede ser cualquier cosa. El 25% es el mismo punto
    donde arranca el video al abrirlo (F6), asi que la miniatura muestra lo
    que vas a ver."""
    tarjeta = _card(qtbot, frames=12)
    assert tarjeta._poster_index == 3       # 25% de 12


def test_al_escrubear_aparece_la_barrita_y_el_timecode(qtbot):
    tarjeta = _card(qtbot, frames=12)
    tarjeta.escrubear_a(0.5)
    plan = tarjeta.plan_de_pintado()
    assert plan["hover"] is not None
    assert plan["hover"]["progreso"] == pytest.approx(0.5, abs=0.1)


def test_al_salir_el_mouse_la_barrita_desaparece(qtbot):
    """Si se quedara, la tarjeta mentiria: dice que estas escrubeando algo que
    ya no estas tocando."""
    tarjeta = _card(qtbot, frames=12)
    tarjeta.escrubear_a(0.5)
    tarjeta.leaveEvent(None)
    assert tarjeta.plan_de_pintado()["hover"] is None
```

- [ ] **Step 2: Implementar** dentro de `plan_de_pintado` y del `paintEvent`
  que ya existe, **no con widgets nuevos**: son dos piezas más del mismo
  overlay, y meterlas como QLabel repetiría el problema de la F2.
- [ ] **Step 3: Verificar** — recorte de una tarjeta a mitad de escrubeo.

---

## Task 18: El pincel — **solo si la Task 14 lo aprobó**

**Files:**
- Modify: `ui/clip_sheet.py`, `ui/main_window.py`
- Test: `tests/ui/test_clip_sheet.py`, `tests/ui/test_main_window.py`

Los **cinco detalles de los que depende** (DECISIONES.md), cada uno con su
test. No son un adorno: la idea sin ellos no sirve.

| # | Qué | Test |
|---|---|---|
| 1 | Solo pinta con la tecla `1`–`9` abajo; sin tecla, arrastrar hace marquesina | `test_sin_tecla_abajo_arrastrar_no_pinta` |
| 2 | El cursor lleva su carga visible (`5 ▌ Baño 1`) | `test_el_cursor_dice_que_cuarto_esta_pintando` |
| 3 | La tarjeta bajo el cursor se tiñe en el momento | `test_la_tarjeta_se_tiñe_al_tocarla` |
| 4 | **Toda la pincelada es UNA entrada de historial** | `test_la_pincelada_entera_se_deshace_de_una` |
| 5 | Los clips **no se reagrupan hasta soltar la tecla** | `test_no_se_reagrupa_mientras_pintas` |

```python
def test_la_pincelada_entera_se_deshace_de_una(qtbot):
    """Si deshiciera clip por clip, el pincel seria una trampa: un gesto
    rapido que cuesta seis acciones revertir."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 7)])
    window.empezar_pincelada("1")
    for indice in range(6):
        window.pintar(indice)
    window.terminar_pincelada()
    assert len(window.history.entries()) == 1
    window.undo()
    assert all(c.categoria_path == [] for c in window.clips)


def test_no_se_reagrupa_mientras_pintas(qtbot):
    """Si saltaran de grupo mientras pintas, la grilla se reacomodaria bajo el
    cursor y seguirias pintando sobre otra cosa."""
    window = _window_with_video(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(i) for i in range(1, 5)])
    orden = list(window.clip_sheet.orden_visual())
    window.empezar_pincelada("1")
    window.pintar(0)
    assert window.clip_sheet.orden_visual() == orden
    window.terminar_pincelada()
    assert window.clip_sheet.orden_visual() != orden
```

- [ ] **Step 1: Escribir los cinco tests.**
- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Verificar** — **a mano, con el mouse**: es un gesto, y un
      gesto no se juzga desde un test. Pintar seis tarjetas, mirar el rastro,
      y deshacer con `⌘Z`.

---

## Task 19: La barra de selección múltiple

**Files:**
- Modify: `ui/clip_sheet.py`
- Test: `tests/ui/test_clip_sheet.py`

El `.batch` del mockup: `5 clips seleccionados · asignar 1–9 · buscar cuarto ⏎
· marcar P X ⇧P · deshacer ⌘Z · salir esc`. Aparece solo con más de un clip
seleccionado.

- [ ] **Step 1: Escribir los tests que fallan** — que aparezca y desaparezca,
      que diga el número correcto, y **que cada tecla que anuncia exista**
      (el detector que ya encontró cuatro atajos fantasma).
- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Verificar** — recorte contra el mockup.

---

## Task 20: Cierre de la F8

- [ ] Suite en verde.
- [ ] Los detectores: señales sin conectar, métodos y tokens huérfanos,
      widgets huérfanos tras 60 teclas, teclas anunciadas que no existen.
- [ ] **Rendimiento con 128 clips**: la tecla de cuarto sigue bajo 5 ms y el
      pincel bajo 16.7 ms por movimiento.
- [ ] **Los dos anchos**: 1600 px y 1150 px. La F6 tuvo dos bugs que solo se
      veían en el angosto.
- [ ] Arnés en las **dos pantallas**, imagen mirada.
- [ ] Prueba a mano con material real: `⇥`, doble click, pincel, `+`/`−`.
- [ ] Commit en español mexicano.

---

## Lo que NO entra en esta fase

- **Badge `Proxy 1080p` y contador `proxies · 128/128`** → F9.
- **`orientacion="horizontal"` hardcodeado** (`ui/main_window.py:1249`) → F9.
- **Transición animada de tarjeta a visor** (DECISIONES.md la pide, «medio
  segundo que evita el "¿dónde estaba?"») → **F10**, con el barrido final. Es
  lo único de esta fase que se puede dejar para el final sin que nada quede a
  medias: sin ella el cruce funciona, solo que seco.
- **Los dos iconos de vista del mockup** → descartados, no hay decisión detrás.
