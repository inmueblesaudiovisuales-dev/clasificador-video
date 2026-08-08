# F6 y F7 del rediseño — Reproducción rápida y el resto del teclado — Implementation Plan

> **Para quien lo ejecute:** las tareas van con checkbox (`- [ ]`) y el test se
> escribe **antes** que la implementación, como en los tres planes anteriores.

**Goal:** atacar el cuello de botella real —marcar pick obliga a ver el clip, y
no hay atajo— optimizando el **tiempo de visionado** (F6); y terminar el
teclado para que un shooting se pueda clasificar sin tocar el mouse (F7).

**Architecture:**

- **F6** toca dos capas. En `player.py`, cosas que mpv ya sabe hacer y que solo
  hay que exponer: velocidad, arranque porcentual y avance por cuadro. En la
  UI, se **rehace el pie del video entero** —timecode con contador de frames,
  barra de reproducción con forma de banda, pastilla de rango y renglón de
  teclas—, que en el mockup es una sola pieza y conviene construir de una vez.
- **F7** agrega el cuarto estado (`destacado`) y dos mecanismos de teclado: la
  tecla `S`, que resuelve el caso más frecuente del material real, y la paleta
  `⏎`, que es el único camino a los cuartos que pasan de nueve.

**Tech Stack:** PySide6 6.11, python-mpv, pytest + pytest-qt.

**Referencias:**
- Comportamiento acordado: `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`
- Estado y huérfanos: `docs/superpowers/ANALISIS-2026-08-08-post-f5.md`
- Candados anti-deriva: `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md`

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q
```

Punto de partida: **442 tests en verde**, commit `1327195`.

---

## Advertencias antes de empezar

1. **La F6 es la fase más grande del rediseño.** Trece renglones del registro.
   Se parte en commits: `player.py` primero (sin UI, verde e inofensivo),
   después el pie del video, después el resto.
2. **La precarga del siguiente clip se decide con un spike, no con fe.** Es lo
   único de esta fase cuyo beneficio no está demostrado y cuyo costo puede ser
   alto: son HEVC 10-bit y un segundo decodificador compite con el que estás
   mirando. **Si el spike no muestra una mejora medible, no se construye** — y
   el `siguiente clip precargado ✓` de la barra de estado tampoco, porque sería
   un indicador que miente.
3. **`⏎` va a chocar con el rail.** Desde el punto de control, una fila de
   cuarto enfocada usa `⏎` para renombrar. **Verificado ejecutando**: el
   contexto por defecto de un `QShortcut` es `WindowShortcut`, o sea que se
   dispara con cualquier foco de la ventana. La paleta se lo robaría. Está en
   la Task 11.
4. **Las teclas se pasan a `handle_key_press` como cadena**, y hoy son de un
   solo carácter. `⇧P` entra como el token `"shift+p"`; no existe una `"⇧p"`.
5. **`destacado` es aditivo en el contrato con Premiere.** El plugin mapea
   `pick→FOREST`, `reject→ROSE` e **ignora lo que no conoce**. No hay que tocar
   `Clip.to_dict()` ni el manifest.
6. **Ningún atajo se dibuja sin registrarse.** Ya hay un test que lo vigila
   (`test_los_atajos_anunciados_en_la_interfaz_existen`); las teclas nuevas de
   estas dos fases entran ahí.

---

# FASE 6 — Reproducción rápida

## Task 1: Lo que mpv ya sabe hacer

**Files:**
- Modify: `src/clasificador_video/player.py`
- Test: `tests/test_player.py`

Tres capacidades que mpv tiene y `MpvPlayer` no expone. Van juntas porque son
la misma clase de cambio: propiedades y comandos del reproductor, sin UI.

**Por qué `start` y no un `seek` después de abrir:** mpv reporta la duración de
forma asíncrona, así que un `seek(duration * 0.25)` justo después de abrir
llega antes de que la duración exista y se cae o no hace nada. La opción
`start` la resuelve mpv al cargar el archivo, cuando ya sabe cuánto dura.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_player.py  (agregar)

def test_la_velocidad_se_le_pide_a_mpv():
    """Para juzgar un recorrido no hace falta verlo a velocidad real."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_speed(2.0)
    assert player._mpv.speed == 2.0
    assert player.speed == 2.0


def test_la_velocidad_arranca_en_uno():
    assert MpvPlayer(mpv_factory=FakeMpv).speed == 1.0


def test_una_velocidad_que_no_esta_en_la_lista_se_rechaza():
    """Mismo criterio que el selector de calidad: fallar fuerte y no dejar
    el reproductor en un estado que la UI no sabe mostrar."""
    import pytest
    with pytest.raises(ValueError):
        MpvPlayer(mpv_factory=FakeMpv).set_speed(3.0)


def test_el_arranque_al_25_por_ciento_se_le_pide_a_mpv():
    """El principio de un recorrido siempre es la camara acomodandose. Se usa
    la opcion `start` y no un seek: mpv reporta la duracion de forma
    asincrona, y un seek justo despues de abrir llega antes de que exista."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_start_percent(25)
    assert player._mpv.start == "25%"


def test_arrancar_desde_el_principio_se_puede_pedir_igual():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_start_percent(0)
    assert player._mpv.start == "0%"


def test_avanzar_y_retroceder_un_cuadro():
    """`,` y `.` son la convencion de Premiere y se usan para marcar in/out
    con precision."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.step_frame(1)
    player.step_frame(-1)
    assert player._mpv.commands == [("frame-step",), ("frame-back-step",)]


def test_avanzar_un_cuadro_pausa_la_reproduccion():
    """Avanzar cuadro a cuadro mientras corre no tiene sentido: mpv lo pausa
    solo, y el estado que reporta la app tiene que coincidir."""
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.play()
    player.step_frame(1)
    assert player.is_paused
```

- [ ] **Step 2: Implementar** — `SPEED_PROFILES = (1.0, 2.0, 4.0)`,
  `set_speed`, propiedad `speed`, `set_start_percent`, `step_frame(delta)`.

  > **Ya verificado contra mpv real** (2026-08-08, con
  > `sample-media/clips/20260804_PIB0589.MP4`, HEVC 10-bit de 6 s):
  > `start = "25%"` se escribe antes de cargar **y también con el archivo ya
  > cargado**, y mpv aterriza en 1.5015 s de 6.006 s — el 25% exacto. `speed`
  > se lee y se escribe, incluso reproduciendo. `frame-step` y
  > `frame-back-step` existen con ese nombre, y `frame-step` deja el
  > reproductor pausado. Nada de esto es una apuesta.

- [ ] **Step 3: Verificar** — `pytest tests/test_player.py -q` en verde.

---

## Task 2: Autoplay y arranque al 25%

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Modify: `src/clasificador_video/ui/video_stage.py` (badge `▶ auto`)
- Test: `tests/ui/test_main_window.py`, `tests/ui/test_video_stage.py`

Apretar espacio 128 veces es puro peaje: al llegar a un clip ya está corriendo.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_main_window.py  (agregar)

def test_cambiar_de_clip_lo_deja_reproduciendo(qtbot):
    """Apretar espacio 128 veces es puro peaje."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1), _clip(2)])
    window.handle_arrow("next")
    assert not window.video_widget.player.is_paused


def test_cada_clip_arranca_al_25_por_ciento(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.select_clip(0)
    assert window.video_widget.player._mpv.start == "25%"


def test_el_badge_auto_avisa_que_arranco_solo(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.select_clip(0)
    assert not window.video_stage.badges.auto_badge.isHidden()


def test_el_badge_auto_se_apaga_al_pausar_a_mano(qtbot):
    """Si sigue prendido con el video pausado, miente."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.select_clip(0)
    window.video_widget.toggle_play()
    window._tick_playhead()
    assert window.video_stage.badges.auto_badge.isHidden()
```

- [ ] **Step 2: Implementar** — `select_clip` y `handle_arrow` llaman a
  `player.set_start_percent(25)` antes de `open_clip` y a `player.play()`
  después. El badge `▶ auto` se apaga en `_tick_playhead` cuando el
  reproductor está pausado.

- [ ] **Step 3: Verificar** — y **abrir la app con material real**: el autoplay
  es lo más difícil de juzgar sin verlo, porque depende de cuánto tarda mpv en
  tener el primer cuadro.

---

## Task 3: Velocidad `1× / 2× / 4×`

**Files:**
- Modify: `src/clasificador_video/ui/video_stage.py`
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_video_stage.py`, `tests/ui/test_main_window.py`

Un `SegmentedControl` más, hermano del de calidad, en la misma fila del
mockup. Y las teclas de la convención de la industria.

**`L` acelera, `K` vuelve a 1× y pausa** (decidido con Bruno el 2026-08-08).
Es `J K L`, lo que hacen Premiere, Avid y Resolve: Bruno ya lo tiene en los
dedos de trabajar todos los días, así que no hay nada que aprender. Las tres
teclas están libres en esta app. Se descartó `⇧,`/`⇧.` —que caen al lado de las
teclas de cuadro— porque son dos atajos nuevos que memorizar y hacen algo muy
distinto de las mismas teclas sin `⇧`.

`L` repetida cicla `1× → 2× → 4×` y **arranca la reproducción si estaba
pausada**: es lo que hace en Premiere y lo que uno espera al apretarla. `K` es
el freno — vuelve a 1× y pausa de un golpe, sin importar dónde estabas.

**`J` queda reservada.** Reproducir hacia atrás no aporta nada en recorridos de
inmuebles, así que no se construye; pero tampoco se le da otro significado, o
el día que sirva ya estaría ocupada por algo que no le corresponde.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_video_stage.py  (agregar)

def test_el_control_de_velocidad_tiene_las_tres_del_mockup(qtbot):
    stage = _stage(qtbot)
    assert [b.text() for b in stage.speed.buttons] == ["1×", "2×", "4×"]


def test_el_control_de_velocidad_arranca_en_1x(qtbot):
    assert _stage(qtbot).speed.current() == "1×"
```

```python
# tests/ui/test_main_window.py  (agregar)

def test_L_acelera_y_cicla(qtbot):
    # la convencion de Premiere: repetir `L` va 1x -> 2x -> 4x -> 1x
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    for esperada in (2.0, 4.0, 1.0):
        window.handle_key_press("l")
        assert window.video_widget.player.speed == esperada


def test_L_tambien_arranca_la_reproduccion(qtbot):
    # es lo que hace en Premiere y lo que uno espera al apretarla
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.video_widget.player.pause()
    window.handle_key_press("l")
    assert not window.video_widget.player.is_paused


def test_K_frena_de_un_golpe(qtbot):
    # vuelve a 1x Y pausa, sin importar donde estabas
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("l")
    window.handle_key_press("l")
    window.handle_key_press("k")
    assert window.video_widget.player.speed == 1.0
    assert window.video_widget.player.is_paused
    # y el control tiene que decir lo mismo: dos vistas del mismo dato que se
    # contradicen es el bug que ya aparecio en la tarjeta y la barra de rango
    assert window.video_stage.speed.current() == "1×"


def test_J_no_hace_nada_todavia(qtbot):
    # reservada para reproducir hacia atras: no se construye, pero tampoco se
    # le da otro significado
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("j")
    assert window.video_widget.player.speed == 1.0


def test_el_control_de_velocidad_refleja_la_tecla(qtbot):
    # si el segmento no sigue a `L`, el control y el video dicen cosas
    # distintas
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("l")
    assert window.video_stage.speed.current() == "2×"


def test_tocar_el_control_se_lo_pide_al_reproductor(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.video_stage.speed.selected.emit("2×")
    assert window.video_widget.player.speed == 2.0


def test_la_velocidad_se_conserva_al_cambiar_de_clip(qtbot):
    # si volviera a 1x en cada clip, habria que reelegirla 128 veces
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1), _clip(2)])
    window.video_stage.speed.selected.emit("4×")
    window.handle_arrow("next")
    assert window.video_widget.player.speed == 4.0
```

- [ ] **Step 2: Implementar.**

  > **Registrar los atajos, no solo manejarlos.** Los tests de arriba llaman a
  > `handle_key_press("l")` directo, así que **pasan aunque la tecla no exista
  > para el usuario**. `L`, `K` y —en la Task 5— `,` y `.` tienen que entrar en
  > `_install_shortcuts`. Es la misma clase de agujero que dejó `⌘Z`, `⌘A`,
  > `⌘E` y `⌘R` anunciados y ausentes: cuatro veces en este proyecto.

```python
# tests/ui/test_main_window.py  (agregar)

def test_las_teclas_de_reproduccion_estan_registradas(qtbot):
    """Un test que llama a `handle_key_press` pasa aunque la tecla no exista
    para el usuario: lo que la conecta es `_install_shortcuts`."""
    window = _window_with_video(qtbot)
    registrados = {s.key().toString() for s in window._shortcuts}
    for tecla in ("L", "K", ",", "."):
        assert tecla in registrados, f"{tecla} se maneja pero no está registrada"
```

- [ ] **Step 3: Verificar.**

---

## Task 4: El pie del video, completo

**Files:**
- Modify: `src/clasificador_video/ui/video_widget.py` (`ScrubBar.paintEvent`)
- Modify: `src/clasificador_video/ui/video_stage.py`
- Modify: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_video_widget.py`, `tests/ui/test_video_stage.py`

**La tarea más visual de la fase.** En el mockup, el pie del video es una sola
pieza: timecode con contador de cuadros, barra, pastilla de rango y renglón de
teclas. Se hace de una vez porque hacerlo por partes significa rehacer el
layout tres veces.

**La barra cambia de forma**, no de función:

| | Hoy | Mockup |
|---|---|---|
| Riel | línea de 3 px | **banda de 26 px** |
| Rango in/out | línea azul entre dos marcas | **bloque azul lleno** |
| Fuera del rango | igual que el resto | **oscurecido** |
| Extremos | dos marcas | **manijas con su letra `I` / `O`** |
| Playhead | cuerpo + punta + línea | línea con triángulo arriba |
| Marcas de tiempo | adaptativas | fijas |

### Lo que la barra NO puede perder al reescribirla

**Esto no es una lista de deseos: es la lección más cara de este rediseño.**
La barra de rango de las tarjetas «sobrevivió tres auditorías del plan y murió
en la implementación» (análisis post-F2 §7), porque reescribir un widget pierde
detalles que el viejo tenía y los tests no lo detectan cuando también se
reescriben. Se reescribe **el mismo tipo de widget**. Antes de tocar
`paintEvent`, cada punto de esta lista tiene su test:

| Qué | Por qué importa |
|---|---|
| **El riel translúcido sobre el video** (`set_over_video`, `TRACK_OVER_VIDEO_RGBA`) | La banda del mockup es `rgba(255,255,255,.13)` **porque va encima de la imagen**. Una banda opaca de 26 px tapa una franja del video — que es justo lo que este rediseño existe para no hacer |
| **`WA_TranslucentBackground`** | Hallazgo de la F0: un widget de `QPainter` sobre el `VideoWidget` pinta fondo opaco donde no dibuja. Sin la bandera, la barra se come una franja de video aunque el riel sea translúcido |
| **El seek con mouse** (`seek_started`, `seek_requested`) | Click y arrastre para saltar de posición. No se toca el `paintEvent`, pero sí las coordenadas: `_x_for` y `_seconds_for_x` tienen que seguir siendo inversas exactas |
| **Las marcas de tiempo adaptativas** | Mejores que las del mockup, y el plan maestro lo permite —«mejor que el mockup está permitido, pero se avisa»—. Escalan de 0.2 s a 24 h sin pasar de 25 marcas |
| **El playhead redondeado** | Su cuerpo se agarra mejor con el mouse que la línea de 2 px del mockup |

```python
# tests/ui/test_video_widget.py  (agregar ANTES de tocar paintEvent)

def test_la_banda_sigue_siendo_translucida_sobre_el_video(qtbot):
    """Una banda opaca de 26 px tapa una franja del video: exactamente lo
    que este rediseño existe para no hacer."""
    from clasificador_video.ui.theme import TRACK_OVER_VIDEO_RGBA

    barra = _scrub(qtbot, duracion=20.0)
    barra.set_over_video(True)
    assert barra.track_color().alpha() == TRACK_OVER_VIDEO_RGBA[3]
    assert barra.track_color().alpha() < 255


def test_el_seek_con_mouse_sigue_siendo_exacto(qtbot):
    """`_x_for` y `_seconds_for_x` tienen que quedar inversas: si el playhead
    no cae donde hiciste click, la barra deja de servir para marcar in/out."""
    barra = _scrub(qtbot, duracion=18.37)
    for x in (6, 150, 251, 394):
        assert barra._x_for(barra._seconds_for_x(x), 6, barra.width() - 12) == x
```

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_video_widget.py  (agregar)
#
# El helper NO existe: hoy cada test arma su `ScrubBar()` a mano. Se agrega
# primero, o los cinco de abajo revientan con NameError -- que es rojo, pero
# del rojo equivocado. (Detectado extrayendo los tests del plan y
# corriendolos contra el codigo de hoy.)

def _scrub(qtbot, duracion: float = 0.0, ancho: int = 400) -> ScrubBar:
    barra = ScrubBar()
    qtbot.addWidget(barra)
    barra.resize(ancho, SCRUB_HEIGHT)
    barra.set_duration(duracion)
    return barra


def test_la_barra_dibuja_el_rango_como_bloque_lleno(qtbot):
    """El mockup usa una banda de 26 px, no una linea: el rango marcado se
    tiene que leer como una ZONA, no como un subrayado.

    Se mide a `y = alto - 5`, ABAJO del riel. Ahi hoy no hay nada dibujado ni
    dentro ni fuera del rango, asi que la diferencia solo puede venir de la
    banda nueva. **Ojo con medir cerca del centro**: entre `track_y - 9` y
    `track_y` viven las marcas de tiempo, y ahi dentro y fuera YA se ven
    distintos -- un test puesto en `y = 6` pasa hoy mismo, sin haber
    construido nada. (Comprobado en la auditoria de este plan.)
    """
    barra = _scrub(qtbot, duracion=20.0)
    barra.resize(400, 26)
    barra.set_in_out(150, 450, 30.0)
    imagen = barra.grab().toImage()
    escala = imagen.width() / max(barra.width(), 1)
    y = round((barra.height() - 5) * escala)
    dentro = imagen.pixelColor(round(200 * escala), y).name()
    fuera = imagen.pixelColor(round(20 * escala), y).name()
    assert dentro != fuera, "el rango no se lee como zona abajo del riel"


def test_las_manijas_de_in_y_out_llevan_su_letra(qtbot):
    barra = _scrub(qtbot, duracion=20.0)
    barra.set_in_out(150, 450, 30.0)
    assert barra.etiquetas_de_manija() == ["I", "O"]


def test_sin_rango_no_hay_manijas(qtbot):
    assert _scrub(qtbot, duracion=20.0).etiquetas_de_manija() == []


def test_solo_in_marcado_dibuja_solo_su_manija(qtbot):
    """Cada extremo se dibuja apenas existe, sin esperar al otro: marcar I
    tiene que verse en el momento."""
    barra = _scrub(qtbot, duracion=20.0)
    barra.set_in_out(150, None, 30.0)
    assert barra.etiquetas_de_manija() == ["I"]


def test_las_marcas_de_tiempo_adaptativas_sobreviven(qtbot):
    """Son mejores que las del mockup y el plan maestro permite conservarlas."""
    barra = _scrub(qtbot, duracion=20.0)
    barra.resize(400, 26)
    assert len(barra._major_tick_seconds()) > 1
```

```python
# tests/ui/test_video_stage.py  (agregar)

def test_el_timecode_lleva_el_numero_de_cuadro(qtbot):
    stage = _stage(qtbot)
    stage.set_timecode("00:00:09:23", frame=293)
    assert "f 293" in stage.frame_label.text()


def test_la_pastilla_de_rango_dice_largo_cuadros_y_total(qtbot):
    stage = _stage(qtbot)
    stage.set_range_pill(rango_segundos=7.13, cuadros=212, total_segundos=18.37)
    texto = stage.range_pill.text()
    assert "212 f" in texto and "18:11" in texto


def test_sin_rango_marcado_la_pastilla_no_se_ve(qtbot):
    stage = _stage(qtbot)
    stage.set_range_pill(None, None, total_segundos=18.37)
    assert stage.range_pill.isHidden()


def test_el_renglon_de_teclas_esta_bajo_la_barra(qtbot):
    """El mockup lo pone ahi: es la chuleta de lo que se puede hacer sobre el
    video sin tocar el mouse."""
    stage = _stage_visible(qtbot)
    assert stage.keys_hint.y() > stage.scrub_bar.y()


def test_la_columna_de_herramientas_recuerda_que_el_espacio_reproduce(qtbot):
    """El `.toolhint` del mockup, al pie de la columna. Es la unica pista de
    que la barra espaciadora hace algo: el resto de la columna son estados
    del clip con su tecla al lado, y `espacio` no tiene indicador propio."""
    from clasificador_video.ui.tool_column import ToolColumn

    columna = ToolColumn()
    qtbot.addWidget(columna)
    assert "espacio" in columna.play_hint.text()


def test_el_nombre_de_archivo_va_como_texto_sobre_un_scrim(qtbot):
    """El mockup no lo mete en pastilla: lo pone sobre un degradado que
    arranca en el borde de arriba.

    Se comprueba contra el QSS del tema y no contra `file_label.styleSheet()`,
    que devuelve **cadena vacia**: el fondo lo pone la hoja global. Una
    asercion sobre esa cadena pasa hoy mismo sin haber cambiado nada.
    (Comprobado en la auditoria de este plan.)
    """
    from clasificador_video.ui import theme

    stage = _stage_visible(qtbot)
    assert stage.top_scrim.y() == 0
    bloque = theme.build_stylesheet().split("QLabel#overlayFile")[1].split("}")[0]
    assert "background-color" not in bloque
```

- [ ] **Step 2: Implementar** — `ScrubBar.paintEvent` se reescribe con la
  banda; `etiquetas_de_manija()` expone qué manijas hay para poder probarlo sin
  contar píxeles. En `VideoStage`: `frame_label`, `range_pill`, `keys_hint`,
  `top_scrim`, y `_place_overlays` los ubica. En `ToolColumn`: `play_hint`, al
  pie, con el `espacio ▶ ‖` del mockup.

- [ ] **Step 3: Verificar** — arnés con `--recorte` sobre el pie del video,
  **mirando la imagen**, con in/out puesto y sin él.

---

## Task 5: `,` y `.` cuadro por cuadro

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_coma_y_punto_mueven_un_cuadro(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press(".")
    window.handle_key_press(",")
    assert window.video_widget.player._mpv.commands[-2:] == [
        ("frame-step",), ("frame-back-step",),
    ]


def test_el_timecode_se_actualiza_al_avanzar_un_cuadro(qtbot):
    """Marcar in/out con precision exige ver el numero moverse."""
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.video_widget.player._mpv.time_pos = 1.0
    window.handle_key_press(".")
    assert window.video_stage.timecode_label.text() != ""
```

- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Verificar** — y **probar a mano con material real**: la
  latencia del cuadro a cuadro es una de las metas escritas de Bruno.

---

## Task 6: Precarga del siguiente clip — **spike primero**

**Files:**
- Spike: al scratchpad de la sesión, **no al repo**
- Modify (solo si el spike lo justifica): `player.py`, `main_window.py`,
  `status_bar.py`

`DECISIONES.md` lo pide: «medio segundo de espera por clip son más de un
minuto por shooting, y es lo que hace *sentir* lenta a una app». Pero es lo
único de esta fase cuyo beneficio no está medido, y el costo puede ser real:
son HEVC 10-bit con `hwdec=videotoolbox`, y un segundo decodificador compite
con el que estás mirando.

- [ ] **Step 1: Medir, con material real de `sample-media/`**
  1. Tiempo desde `open_clip` hasta el primer cuadro dibujado, sin precarga.
  2. Lo mismo con el siguiente clip ya abierto en un `MpvPlayer` de reserva.
  3. Y con la reproducción del clip actual **corriendo**, que es el caso real:
     lo que hay que descartar es que la precarga haga tartamudear lo que estás
     mirando.

- [ ] **Step 2: Decidir con el número en la mano**
  - **Si mejora y no tartamudea**: se construye, y la barra de estado muestra
    `siguiente clip precargado ✓`.
  - **Si no**: **no se construye, y el indicador tampoco.** Un `✓` que no
    corresponde a nada es peor que no tenerlo. Se escribe el número medido en
    el análisis de cierre y `DECISIONES.md` se corrige.

- [ ] **Step 3: Verificar** — sea cual sea la decisión, queda escrita.

## Task 7: Cierre de la F6

- [ ] Suite en verde.
- [ ] Campos y métodos que nadie lee, y **señales declaradas sin conectar** —
      el detector que encontró el botón muerto en el punto de control.
- [ ] Arnés corrido, imagen **mirada**, recortes del pie del video y de la
      barra de estado.
- [ ] **Prueba a mano con material real**: autoplay, velocidad, cuadro a
      cuadro. Esta fase es la que menos se puede juzgar sin ver el video.
- [ ] Commit en español mexicano.

---

# FASE 7 — El resto del teclado

## Task 8: `S` — igual al clip anterior

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Modify: `src/clasificador_video/ui/room_rail.py` (la fila fija de arriba)
- Test: `tests/ui/test_main_window.py`, `tests/ui/test_room_rail.py`

**La tecla más valiosa que existe en este material.** En un recorrido las tomas
vienen en rachas: seis de cocina, cuatro de sala. Sobre 128 clips convierte
~110 decisiones en ~110 confirmaciones sin pensar.

**Qué es «el anterior»**: el clip **con cuarto** más cercano hacia atrás en el
orden de rodaje — no `clips[actual - 1]` a secas. Si el anterior quedó sin
clasificar, `S` sigue buscando hacia atrás. Así la tecla no se vuelve inútil en
cuanto te saltas uno.

La fila va **fija arriba del listado de cuartos**, mostrando siempre a qué
cuarto aplicaría: es una confirmación, no un acto de memoria.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_main_window.py  (agregar)

def test_S_asigna_el_cuarto_del_clip_anterior(qtbot):
    window = _window(qtbot, rooms=("Cocina", "Sala"))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.handle_key_press("1")          # el primero a Cocina, y avanza
    window.handle_key_press("s")
    assert window.clips[1].categoria_path == ["Cocina"]


def test_S_salta_los_que_quedaron_sin_clasificar(qtbot):
    """Si mirara solo el inmediatamente anterior, la tecla se volveria
    inutil apenas te saltas uno."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window.select_clip(0)
    window.handle_key_press("1")
    window.select_clip(2)                 # el del medio queda sin cuarto
    window.handle_key_press("s")
    assert window.clips[2].categoria_path == ["Cocina"]


def test_S_sin_ningun_clip_clasificado_antes_no_hace_nada(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("s")
    assert window.clips[0].categoria_path == []


def test_S_tambien_avanza(qtbot):
    """Es una asignacion de cuarto como cualquier otra."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2), _clip(3)])
    window.select_clip(0)
    window.handle_key_press("1")
    window.handle_key_press("s")
    assert window.current_index == 2


def test_S_deja_entrada_en_el_historial(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1), _clip(2)])
    window.select_clip(0)
    window.handle_key_press("1")
    window.handle_key_press("s")
    assert window.history.entries()[0].etiqueta == "Cocina"
```

```python
# tests/ui/test_room_rail.py  (agregar)

def test_la_fila_de_S_dice_a_que_cuarto_aplicaria(qtbot):
    """Es una confirmacion, no un acto de memoria."""
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    rail.set_same_room("Cocina", theme.room_color(0))
    assert "Cocina" in rail.same_row.name_label.full_text()
    assert not rail.same_row.isHidden()


def test_sin_cuarto_anterior_la_fila_de_S_no_se_ve(qtbot):
    rail = _rail(qtbot)
    rail.set_same_room(None, None)
    assert rail.same_row.isHidden()


def test_la_fila_de_S_va_arriba_de_los_cuartos(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {})
    rail.set_same_room("Cocina", theme.room_color(0))
    layout = rail._rooms_layout
    assert layout.indexOf(rail.same_row) < layout.indexOf(rail.rows[0])
```

- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Verificar** — arnés y recorte del rail: el mockup le da a esta
  fila un fondo ámbar tenue y su propio encabezado (`IGUAL AL CLIP ANTERIOR`).

---

## Task 9: El cuarto estado — destacado

**Files:**
- Modify: `src/clasificador_video/manifest.py` (solo la validación, si la hay)
- Modify: `ui/main_window.py`, `ui/tool_column.py`, `ui/clip_sheet.py`,
  `ui/room_rail.py`, `ui/video_stage.py`, `src/clasificador_video/filters.py`
- Test: los suyos, más `tests/test_manifest.py`

`reject` → `neutral` → `pick` → **`destacado`**. Es *la* toma del cuarto, la
que abre la secuencia en el corte final, y es la única gradación con
significado río abajo.

**Toca muchos archivos porque el estado se ve en seis lugares**: glifo `★` en
la tarjeta, indicador en la columna, badge sobre el video, chip `N dest.` en la
leyenda del rail, chip `★ solo destacados` en los filtros, y el manifest.

**No inventa un color nuevo**: es un pick reforzado —misma familia verde,
`STAR_COLOR`, que existe en el tema desde la F1 esperando esta fase—.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_manifest.py  (agregar)

def test_destacado_viaja_en_el_manifest_sin_cambiar_el_contrato():
    """El plugin mapea pick→FOREST, reject→ROSE e IGNORA lo que no conoce:
    `destacado` es aditivo y no obliga a tocar to_dict()."""
    clip = Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=["Cocina"], fps=30.0)
    clip.flag = "destacado"
    assert clip.to_dict()["flag"] == "destacado"
    assert clip.to_dict()["categoria_path"] == ["Cocina"]
```

```python
# tests/ui/test_main_window.py  (agregar)

def test_shift_p_marca_destacado(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("shift+p")
    assert window.clips[0].flag == "destacado"


def test_repetir_shift_p_vuelve_a_neutral(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("shift+p")
    window.handle_key_press("shift+p")
    assert window.clips[0].flag == "none"


def test_destacado_se_ve_en_los_seis_lugares(qtbot):
    """Si falta en uno, el estado existe a medias y no se puede confiar en
    ninguna de las vistas."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1, "Cocina")])
    window.select_clip(0)
    window.handle_key_press("shift+p")
    assert window.clip_sheet.item_widgets[0].plan_de_pintado()["glifo"][0] == "★"
    assert window.tool_column.star_indicator.is_on()
    assert "DESTACADO" in window.video_stage.badges.flag_badge.text()
    assert window.room_rail.leyenda.puntos[0].text() == "1"       # el chip dest.
    assert "solo_destacados" in window.clip_sheet.chips
```

```python
# tests/test_filters.py  (agregar)

def test_solo_destacados():
    clips = [_clip(1, flag="destacado"), _clip(2, flag="pick"), _clip(3)]
    assert cola(clips, FilterState(estado="solo_destacados")) == [0]


def test_ocultar_rejects_no_esconde_destacados():
    clips = [_clip(1, flag="destacado"), _clip(2, flag="reject")]
    assert cola(clips, FilterState(estado="ocultar_rejects")) == [0]


def test_sin_marcar_no_cuenta_a_los_destacados():
    clips = [_clip(1, flag="destacado"), _clip(2)]
    assert cola(clips, FilterState(estado="sin_marcar")) == [1]
```

- [ ] **Step 2: Implementar.** Ojo con `contar()`: `sin_marcar` hoy pregunta
  por `("pick", "reject")` y tiene que pasar a excluir también `destacado`.

- [ ] **Step 3: Verificar** — recortes de la tarjeta, del rail y del badge.

---

## Task 10: `P` y `X` vuelven a neutral

**Files:**
- Modify: `src/clasificador_video/keyboard.py`, `ui/main_window.py`
- Test: `tests/test_keyboard.py`, `tests/ui/test_main_window.py`

`DECISIONES.md`: «repetir la tecla vuelve a neutral». Es lo que evita tener una
tecla de neutral aparte — menos atajos se aprenden más rápido.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_P_sobre_un_pick_lo_devuelve_a_neutral(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("p")
    window.handle_key_press("p")
    assert window.clips[0].flag == "none"


def test_P_sobre_un_reject_lo_convierte_en_pick(qtbot):
    """Solo alterna consigo misma: `P` sobre un reject es «ahora es pick»."""
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("x")
    window.handle_key_press("p")
    assert window.clips[0].flag == "pick"


def test_deshacer_el_regreso_a_neutral(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.handle_key_press("p")
    window.handle_key_press("p")
    window.undo()
    assert window.clips[0].flag == "pick"
```

- [ ] **Step 2: Implementar** — la decisión de alternar necesita el estado
  actual del clip, así que vive en `MainWindow`, no en el router, que no
  conoce clips.

- [ ] **Step 3: Verificar.**

---

## Task 11: La paleta `⏎`

**Files:**
- Create: `src/clasificador_video/ui/room_palette.py`
- Modify: `ui/main_window.py`, `ui/tool_column.py`
- Test: `tests/ui/test_room_palette.py` (nuevo)

Un solo mecanismo cubre tres necesidades: los cuartos que pasan de nueve
—donde ya no hay tecla—, crear uno al vuelo sin soltar el teclado, y asignar en
lote respetando la selección.

**El choque con el rail, que es la trampa de esta tarea:** desde el punto de
control, una fila de cuarto enfocada usa `⏎` para renombrar. Un `QShortcut`
normal se dispara **sin importar quién tiene el foco**, así que la paleta se lo
robaría y renombrar dejaría de funcionar. El handler tiene que revisar
`focusWidget()` y no abrir la paleta cuando el foco está en el rail.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_room_palette.py

def test_filtra_los_cuartos_en_vivo(qtbot):
    paleta = _paleta(qtbot, ["Cocina", "Recámara 1", "Recámara 2"])
    paleta.input.setText("reca")
    assert paleta.opciones_visibles() == ["Recámara 1", "Recámara 2"]


def test_la_busqueda_ignora_acentos(qtbot):
    paleta = _paleta(qtbot, ["Recámara 1"])
    paleta.input.setText("recamara")
    assert paleta.opciones_visibles() == ["Recámara 1"]


def test_enter_asigna_la_primera_opcion(qtbot):
    paleta = _paleta(qtbot, ["Cocina", "Comedor"])
    paleta.input.setText("com")
    with qtbot.waitSignal(paleta.room_chosen) as blocker:
        paleta.confirmar()
    assert blocker.args == ["Comedor"]


def test_sin_coincidencias_ofrece_crear(qtbot):
    paleta = _paleta(qtbot, ["Cocina"])
    paleta.input.setText("Alberca")
    assert paleta.opcion_de_crear() == "Alberca"
    with qtbot.waitSignal(paleta.room_created) as blocker:
        paleta.confirmar()
    assert blocker.args == ["Alberca"]


def test_con_el_campo_vacio_no_ofrece_crear_nada(qtbot):
    paleta = _paleta(qtbot, ["Cocina"])
    assert paleta.opcion_de_crear() is None


def test_las_flechas_mueven_la_seleccion(qtbot):
    from PySide6.QtCore import Qt
    paleta = _paleta(qtbot, ["Cocina", "Comedor"])
    qtbot.keyClick(paleta.input, Qt.Key.Key_Down)
    assert paleta.opcion_activa() == "Comedor"


def test_esc_cierra_sin_asignar(qtbot):
    from PySide6.QtCore import Qt
    paleta = _paleta(qtbot, ["Cocina"])
    with qtbot.assertNotEmitted(paleta.room_chosen):
        qtbot.keyClick(paleta.input, Qt.Key.Key_Escape)
    assert paleta.isHidden()


def test_dice_a_cuantos_clips_va_a_aplicar(qtbot):
    """El mockup dice `a 6 clips`: asignar en lote sin querer es el error mas
    caro de la app."""
    paleta = _paleta(qtbot, ["Cocina"], seleccionados=6)
    assert "6 clips" in paleta.alcance_label.text()
```

```python
# tests/ui/test_main_window.py  (agregar)

def test_enter_abre_la_paleta(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.abrir_paleta()
    assert not window.room_palette.isHidden()


def test_enter_NO_abre_la_paleta_si_el_foco_esta_en_el_rail(qtbot):
    """Con una fila enfocada, `⏎` renombra ese cuarto. Un QShortcut normal se
    dispara sin importar el foco y se lo robaria."""
    window = _window(qtbot, rooms=("Cocina",))
    window.show()
    qtbot.waitExposed(window)
    window.room_rail.focus_rooms()
    window._on_enter()
    assert window.room_palette.isHidden()


def test_la_paleta_crea_el_cuarto_y_lo_asigna_de_una(qtbot):
    window = _window(qtbot, rooms=("Cocina",))
    window.load_clips([_clip(1)])
    window.select_clip(0)
    window.room_palette.room_created.emit("Alberca")
    assert window.room_selection.active_rooms() == ["Cocina", "Alberca"]
    assert window.clips[0].categoria_path == ["Alberca"]
```

- [ ] **Step 2: Implementar** — la paleta es un widget hijo de `MainWindow`
  centrado sobre el video, no un `QDialog` modal: un modal roba el teclado y
  hay que cerrarlo para seguir clasificando.

- [ ] **Step 3: Verificar** — recorte contra el mockup, que la dibuja con el
  campo arriba, las opciones con su tecla y conteo, y el pie con `↑↓ elegir ·
  ⏎ asignar · esc cancelar`.

---

## Task 12: `F` — solo video

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_F_esconde_todo_menos_el_video(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("f")
    for panel in (window.room_rail, window.tool_column, window.clip_sheet,
                  window.title_bar, window.status_bar):
        assert panel.isHidden()
    assert not window.video_stage.isHidden()


def test_F_otra_vez_devuelve_todo(qtbot):
    window = _window_with_video(qtbot)
    window.load_clips([_clip(1)])
    window.handle_key_press("f")
    window.handle_key_press("f")
    assert not window.room_rail.isHidden()


def test_en_solo_video_el_video_usa_todo_el_ancho_que_puede(qtbot):
    """Si escondiera los paneles sin recalcular, quedaria el mismo video con
    franjas negras al costado -- justo lo que este rediseño evita."""
    window = _window_with_video(qtbot)
    window.resize(1600, 1000)
    window.show()
    qtbot.waitExposed(window)
    window.load_clips([_clip(1)])
    antes = window.video_stage.width()
    window.handle_key_press("f")
    assert window.video_stage.width() > antes
```

- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Verificar** — captura del modo solo video.

## Task 13: Cierre de la F7

- [ ] Suite en verde.
- [ ] La tabla de teclado de `DECISIONES.md` queda **completa**: todo lo que
      dice, existe.
- [ ] Campos, métodos y **señales sin conectar**.
- [ ] Arnés, imagen **mirada**, recortes del rail con la fila de `S`, de la
      tarjeta con `★` y de la paleta abierta.
- [ ] Punto de control: rehacer el análisis antes de planear la F8.
- [ ] Commit en español mexicano.

---

# Lo que NO entra en estas dos fases

Mismo registro de siempre, actualizado. **Si una de estas fases se disuelve o
se reordena, estos renglones se reasignan uno por uno, no en bloque.**

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
| Barrita y timecode al escrubear una miniatura | mockup `.hoverbar`, `.hovertc` |
| Barra de acciones de selección múltiple | mockup `.batch` |
| **Portada de la miniatura al 25% del clip** (hoy es el frame del medio) | `DECISIONES.md` |

## F9 — Proxies y orientación

| Qué | De dónde sale |
|---|---|
| Conectar `match_proxies()` a la importación | plan maestro |
| Badge `Proxy 1080p` sobre el video | mockup `.badge` |
| `proxies 1080p · 128/128` en la barra de estado | mockup `.status` |
| `orientacion` del manifest derivada del material | lista de ejecución — **el único renglón vivo** |

## F10 — Barrido final

| Qué |
|---|
| La lista de ejecución tiene que estar vacía |
| Comparación final de las dos pantallas, con recortes |
| Toda diferencia contra el mockup: arreglada, o escrita con su razón |
| **Probar con la tecla física** todos los atajos con modificador |

## Descartado a propósito

| Qué | Por qué |
|---|---|
| Los dos iconos de vista de la hoja (`.viewtoggle`) | No hay ninguna decisión detrás |
| El separador `.fdiv` entre grupos de filtros | Los filtros van en dos renglones; no hay qué separar |
| Forma de onda, recorte automático, modo comparar, cinco estrellas | Evaluados y descartados en `DECISIONES.md` |

---

## Auditoría de este plan — 2026-08-08

Hecha **ejecutando** un spike descartable, no releyendo.

**Confirmado contra Qt** (eran apuestas, ahora son hechos):

| Qué | Resultado |
|---|---|
| El contexto por defecto de un `QShortcut` es `WindowShortcut` | **Sí**: se dispara con cualquier foco de la ventana. El choque de `⏎` con el rail es real, no hipotético |
| ¿`P` se dispara también al pulsar `⇧P`? | **No.** Qt las distingue. `⇧P` no va a marcar pick además de destacado |
| ¿Esconder un panel hace crecer a su hermano? | **Sí**, el layout redistribuye solo |

**Corregido**: los tests usaban `handle_key_press("⇧p")`, un token inventado.
La función recibe cadenas de un carácter; `⇧P` entra como `"shift+p"`.

**Ojo con la Task 12** (`F` solo video): el spike muestra que esconder paneles
hace crecer al hermano **en un layout normal**, pero el video de esta app tiene
**ancho fijo**, puesto por `_resize_video_stage`. Esconder los paneles sin
recalcularlo dejaría el mismo video con franjas negras al costado — justo lo
que este rediseño existe para evitar. Y el máximo se calcula restando rail,
columna y ancho mínimo de la hoja: en modo solo video **no hay que restarlos**.
El test `test_en_solo_video_el_video_usa_todo_el_ancho_que_puede` lo cubre.

**Lo que no se puede verificar desde aquí**: que `start` se pueda escribir como
propiedad de python-mpv después de construir el reproductor, y que
`frame-back-step` exista con ese nombre. Las dos necesitan un mpv real con
material de `sample-media/`, y quedan como primer paso de la Task 1.

---

## Segunda auditoría del plan de la F6 — 2026-08-08

Hecha ejecutando, contra **mpv real** y contra los widgets de verdad.

### Lo que quedó demostrado

Las tres apuestas sobre mpv, probadas con
`sample-media/clips/20260804_PIB0589.MP4` (HEVC 10-bit, 6 s, vertical):

| Apuesta | Resultado |
|---|---|
| `start = "25%"` se puede escribir | **Sí**, antes de cargar y con el archivo ya cargado. mpv aterriza en 1.5015 s de 6.006 s: el 25% exacto |
| `speed` se lee y se escribe | **Sí**, incluso con el video corriendo |
| `frame-step` y `frame-back-step` existen | **Sí**, con esos nombres. Y `frame-step` deja el reproductor pausado |

La Task 1 deja de ser una apuesta.

### Tres fallas del plan, todas de la misma familia

**Tests que pasan sin que la función exista.** Es lo que este proyecto ya
sufrió cuatro veces con atajos anunciados y ausentes.

1. **El test de píxel de la barra medía una marca de tiempo, no la banda.**
   A `y = 6` viven las marcas adaptativas, así que dentro y fuera del rango
   **ya se ven distintos hoy**: el test pasaba sin construir nada. Se mueve a
   `y = alto - 5`, abajo del riel, donde hoy no hay nada dibujado.

2. **`"background" not in file_label.styleSheet()` no prueba nada.** Ese
   método devuelve cadena vacía: el fondo lo pone la hoja de estilos global.
   La aserción pasa hoy mismo. Ahora se comprueba contra el bloque
   `QLabel#overlayFile` del tema.

3. **El plan no decía registrar los atajos nuevos.** Todos los tests llamaban
   a `handle_key_press("l")` directo, que funciona aunque `L` no exista para
   el usuario. Se agrega el paso y un test que lo vigila.

### Lo que enseña

**Un test escrito contra una API que todavía no existe no se puede ejecutar,
pero sí se puede razonar sobre qué mediría.** Las tres fallas se encontraron
preguntando «¿esto pasaría hoy, sin implementar nada?» y comprobándolo. Vale
la pena hacerlo con todo test de píxel y con toda aserción sobre un método de
Qt que uno no usa a diario.

---

## Tercera auditoría del plan de la F6 — 2026-08-08

Ángulo nuevo y mecánico: **se extrajeron los 31 tests de la F6 del propio plan
y se corrieron contra el código de hoy.** Un test que pasa antes de implementar
nada no sirve; uno que falla por el motivo equivocado, tampoco.

**Resultado: los 31 fallan.** Ninguno es vacuo — las dos aserciones huecas que
encontró la segunda auditoría ya estaban corregidas. Pero el *motivo* del fallo
delató dos cosas:

| Motivo del fallo | Cuántos | Qué significa |
|---|---|---|
| `AttributeError` sobre la API que se va a construir | 24 | Rojo correcto: es TDD |
| `assert not True` | 2 | Rojo correcto: la función no existe todavía |
| **`NameError: _scrub`** | **5** | **Rojo equivocado**: el helper no existe |

### Falla 1: cinco tests usaban un helper inexistente

`tests/ui/test_video_widget.py` arma su `ScrubBar()` a mano en cada test; no
hay `_scrub`. Los cinco tests de la barra habrían reventado con `NameError`
—que es rojo, pero del rojo que no enseña nada—. El plan ahora define el
helper antes de usarlo. Es la misma falla que la auditoría de la F3 encontró
con `_window(rooms=)` y `_clip`: **al escribir tests para un archivo que uno no
tiene delante, es fácil inventarle helpers.**

### Falla 2: el `espacio ▶ ‖` no tenía tarea

Existía **solo como un renglón en la lista de cierre de la F7**. Un elemento de
interfaz que aparece únicamente en un checklist termina de dos maneras: se
olvida, o se construye a las apuradas el último día sin test. Ahora tiene su
test y su paso de implementación dentro de la Task 4.

### Lo que enseña

**Los tests de un plan se pueden ejecutar antes de escribir una sola línea de
producción.** Cuesta cinco minutos, y distingue tres cosas que a simple vista
se ven igual: el test que ya pasa (inútil), el que falla porque falta la
función (correcto) y el que falla porque está roto (engañoso).

---

## Cuarta auditoría del plan de la F6 — 2026-08-08

Dos barridos mecánicos nuevos.

**Cobertura contra el registro: limpia.** Los catorce renglones que el análisis
post-F5 le asigna a la F6 tienen tarea y test en el plan. (Eran trece; el
`espacio ▶ ‖` se sumó en la tercera auditoría.)

**Dependencias entre tareas: limpias.** Ninguna tarea usa una API que crea una
tarea posterior, así que el orden 1→7 se puede seguir tal cual.

### Falla 1: la Task 4 reescribía la barra sin decir qué no perder

**La más grave de las cuatro auditorías**, porque ya pasó una vez con este
mismo tipo de widget. El análisis post-F2 lo dejó escrito: la barra de rango de
las tarjetas *«sobrevivió tres auditorías del plan y murió en la
implementación»*, porque reescribir un widget pierde detalles que el viejo
tenía y los tests no lo detectan cuando también se reescriben.

La Task 4 reescribe `ScrubBar.paintEvent` entero y **no mencionaba**:

- el **riel translúcido** sobre el video (`set_over_video`,
  `TRACK_OVER_VIDEO_RGBA`) — la banda del mockup es `rgba(255,255,255,.13)`
  *porque va encima de la imagen*; una banda opaca de 26 px tapa una franja de
  video, que es justo lo que este rediseño existe para no hacer;
- **`WA_TranslucentBackground`**, el hallazgo de la F0, sin el cual la barra se
  come una franja aunque el riel sea translúcido;
- el **seek con mouse**, cuyas coordenadas tienen que seguir siendo inversas
  exactas.

Ahora hay una tabla de «lo que no puede perder» y dos tests que se escriben
**antes** de tocar el `paintEvent`.

### Falla 2: `K` dejaba el control de velocidad mintiendo

`test_K_frena_de_un_golpe` comprobaba que el reproductor vuelve a 1× y pausa,
pero no que el control segmentado lo refleje. Podía quedar mostrando `4×` con
el video a `1×`. **Dos vistas del mismo dato que se contradicen** — exactamente
el bug que la auditoría de la F1-F5 encontró entre la tarjeta y la barra de
rango con el in/out invertido. Agregada la aserción.

### Lo que enseña

Las cuatro auditorías de este plan encontraron, en orden: 4 correcciones, 3
fallas, 2 fallas, 2 fallas. **Lo que cambia no es la cantidad sino el tipo**:
las primeras eran sobre APIs de Qt y mpv; estas dos son sobre *lo que el plan
no dice*. Un plan detallado se audita bien preguntándole qué omite, no solo si
lo que dice es cierto.
