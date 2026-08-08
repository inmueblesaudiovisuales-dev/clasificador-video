# F2.1 y F3 del rediseño — Tarjetas completas y cuartos planos — Implementation Plan

> **Para quien lo ejecute:** las tareas van con checkbox (`- [ ]`) y el test se
> escribe **antes** que la implementación, como en
> [`2026-08-08-f1-f2-tokens-y-esqueleto.md`](2026-08-08-f1-f2-tokens-y-esqueleto.md).

**Goal:** cerrar la regresión que introdujo la F2 —las tarjetas de la hoja de
contactos perdieron todo menos la miniatura— y las cinco diferencias menores
contra el mockup detectadas en el análisis post-F2 (F2.1); después dejar los
cuartos planos y editables en vivo, sin diálogo de configuración inicial (F3).

**Architecture:**

- **F2.1** devuelve a `ClipCard` la información que el mockup dibuja sobre la
  miniatura. Se hace con **un solo widget hijo que pinta con `QPainter`**
  (`_CardOverlay`), no con seis `QLabel` posicionados: la franja rayada de «sin
  clasificar» es un `repeating-linear-gradient` a 135° que QSS no sabe expresar,
  y la barra de rango tiene que ir semitransparente sobre la imagen. Un solo
  `paintEvent` deja además toda la geometría de la tarjeta en un lugar. Lleva
  `WA_TranslucentBackground` y `WA_TransparentForMouseEvents` — sin la primera
  pinta fondo opaco donde no dibuja (hallazgo de la F0), sin la segunda se come
  el scrub al pasar el mouse.
- **F3** borra la rama entera de subcuartos (`category_path.py`, el estado
  `pending_parent` del router, el banner del rail, `REPEATABLE_ROOMS`) y el
  diálogo previo. `RoomSelection` pasa de «estado de un diálogo» a **el modelo
  de cuartos de la sesión**, con `rename`, `move` y `remove`. El rail lo edita
  en el lugar con menú contextual y doble click.

**Tech Stack:** PySide6 6.11 (`QWidget`, `QPainter`, `QSS`, `QMenu`,
`QInputDialog`), pytest + pytest-qt (`qtbot`).

**Referencias:**
- Mockup (fuente de verdad visual): `docs/superpowers/mockups/rediseno-2026-08-08/mockup.html`
- Comportamiento acordado: `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`
- Estado de hoy y lista de ejecución: `docs/superpowers/ANALISIS-2026-08-08-post-f2.md`
- Candados anti-deriva: `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md`

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q
```

Punto de partida: **283 tests en verde**, commit `e94f3ab`.

---

## Advertencias antes de empezar

1. **Los colores con alfa se pasan como tuplas desde el tema** y se construyen
   con `QColor(*theme.LO_QUE_SEA_RGBA)`, igual que ya hace `ScrubBar` con
   `TRACK_OVER_VIDEO_RGBA`. Razón verificada ejecutando:
   `QColor("rgba(255,255,255,26)").isValid()` devuelve **False** — QColor no
   parsea la notación CSS, así que el token tiene que traer componentes.
   *(El test del Candado 1 sí prohíbe `rgb(`/`rgba(` fuera de `theme.py`, pero
   su regex es sensible a mayúsculas: `QColor.fromRgb(` y `.getRgb()` **no** lo
   hacen fallar. Comprobado; no hace falta evitarlos.)*
2. **Los tests también tienen valores escritos a mano.** Al cambiar
   `set_flags` y los badges del video rompen, como mínimo,
   `tests/ui/test_room_rail.py:61` y `tests/ui/test_main_window.py:598,617,624`.
   Se reescriben contra el widget nuevo; ninguno se borra sin decir por qué en
   el commit.
3. **`tests/test_app.py` está excluido de la corrida pero se mantiene al día.**
   La F3 le cambia la firma a `arrancar()` y ese archivo la prueba: si queda
   obsoleto, la próxima persona no va a saber si falla por el cuelgue conocido o
   porque se rompió algo de verdad. Ya pasó una vez.
4. **`app.py::_restore_session` toca la ventana por atributos.** La F3 le quita
   `category_tree` a `MainWindow`; hay que revisarlo en la misma tarea o el
   camino de recuperar sesión —que casi no se prueba a mano— revienta.
5. **Nada de features que no estén en `DECISIONES.md`.** El estado «destacado»,
   la paleta `⏎`, el pincel y los filtros son fases posteriores. Donde el mockup
   muestra algo de esas fases (el chip `6 dest.` de la leyenda, el badge
   `▶ auto`), la F2.1 deja el hueco y no lo inventa.

---

# FASE 2.1 — Las tarjetas vuelven a decir algo

## Task 1: Tokens que faltan para la tarjeta y la leyenda

**Files:**
- Modify: `src/clasificador_video/ui/theme.py:43-59`
- Test: `tests/ui/test_theme.py`

Dos tokens mueren y varios nacen. Los que mueren:

- **`RANGE_TRACK_COLOR` (`#2e343d`)** — la barra de rango va **encima de la
  miniatura**, y un color sólido ahí se ve como una banda opaca tapando la
  imagen. El mockup usa `rgba(255,255,255,.1)`. Se reemplaza por
  `RANGE_TRACK_RGBA`, en forma de tupla porque `QPainter` la necesita así (mismo
  criterio que `TRACK_OVER_VIDEO_RGBA`).
- **`FLAG_NONE_COLOR`** — era el color del texto «sin marca» de la tarjeta
  vieja. **El mockup no dibuja nada cuando el clip no tiene flag**: la ausencia
  de glifo *es* la información. El token no tiene destinatario en el diseño
  nuevo, así que se borra en vez de buscarle un uso.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_theme.py  (agregar)

def test_la_barra_de_rango_va_semitransparente_sobre_la_miniatura():
    """Un color solido ahi se ve como una banda opaca tapando la imagen."""
    assert theme.RANGE_TRACK_RGBA == (255, 255, 255, 26)


def test_los_tokens_de_la_tarjeta_salen_del_mockup():
    assert theme.CARD_BADGE_BG_RGBA == (4, 5, 7, 165)
    assert theme.CARD_BADGE_TEXT == "#e4e8ee"
    assert theme.UNCLASSIFIED_STRIPE == "#3a4150"
    assert theme.SELECTION_BORDER == "#8fb4ff"
    assert theme.SELECTION_TICK_INK == "#0a1024"


def test_las_tintas_de_los_glifos_contrastan_contra_su_color_de_estado():
    """El glifo `P` va en tinta oscura sobre el verde de pick, no al reves."""
    assert theme.PICK_INK == "#07130d"
    assert theme.REJECT_INK == "#1b0708"


def test_pendiente_tiene_color_propio_y_no_es_una_superficie():
    """El tramo 'lo que falta' de la barra y el punto gris de la leyenda son
    el mismo dato; el mockup les da un gris propio, no un fondo de panel."""
    assert theme.PENDING_COLOR == "#2a2f38"
    assert theme.PENDING_COLOR != theme.BG_SURFACE_2


def test_mezclar_con_blanco_aclara_sin_cambiar_de_tono():
    """De aqui sale el texto del badge de cuarto sobre el video."""
    assert theme.aclarar("#000000", 0.5) == "#808080"
    assert theme.aclarar("#c0885a", 0.0) == "#c0885a"


def test_con_alfa_devuelve_el_color_en_forma_de_tupla_para_QPainter():
    assert theme.con_alfa("#55c08a", 140) == (85, 192, 138, 140)


def test_los_tokens_que_la_f2_dejo_sin_usar_ya_no_existen():
    """Un token sin destinatario es una funcion perdida esperando: los dos
    que quedaron huerfanos en la F2 eran justo los de la barra de rango y el
    texto 'sin marca' de la tarjeta (ver ANALISIS-2026-08-08-post-f2 §2)."""
    assert not hasattr(theme, "RANGE_TRACK_COLOR")
    assert not hasattr(theme, "FLAG_NONE_COLOR")
```

- [ ] **Step 2: Implementar**

```python
# src/clasificador_video/ui/theme.py  (reemplaza RANGE_TRACK_COLOR y FLAG_NONE_COLOR)

PENDING_COLOR = "#2a2f38"   # lo que falta clasificar: barra de progreso y leyenda

# --- tarjetas de la hoja de contactos ---
# Alfas en forma de tupla, no en cadena "rgba(...)": QPainter necesita
# componentes y QColor no parsea la notacion CSS.
CARD_BADGE_BG_RGBA = (4, 5, 7, 165)   # pastilla de numero de clip y duracion
CARD_BADGE_TEXT = "#e4e8ee"
RANGE_TRACK_RGBA = (255, 255, 255, 26)  # riel de la barra de rango, sobre la imagen
UNCLASSIFIED_STRIPE = "#3a4150"       # franja rayada de "sin clasificar"
SELECTION_BORDER = "#8fb4ff"          # borde y palomita de seleccion multiple
SELECTION_TICK_INK = "#0a1024"
# tinta de los glifos de estado: van oscuros SOBRE el color del estado
PICK_INK = "#07130d"
REJECT_INK = "#1b0708"


def aclarar(color_hex: str, factor: float) -> str:
    """Mezcla un color con blanco. El badge de cuarto sobre el video lleva el
    texto en una version clara del color del cuarto: el mockup la eligio a
    mano para `--r1`, y esto la deriva para los nueve."""
    color_hex = color_hex.lstrip("#")
    canales = [int(color_hex[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(c + (255 - c) * factor):02x}" for c in canales)


def con_alfa(color_hex: str, alfa: int) -> tuple[int, int, int, int]:
    """Color de token + alfa, listo para `QColor(*...)`."""
    color_hex = color_hex.lstrip("#")
    return (*(int(color_hex[i:i + 2], 16) for i in (0, 2, 4)), alfa)
```

- [ ] **Step 3: Verificar** — `pytest tests/ui/test_theme.py -q` en verde y
  `grep -rn "RANGE_TRACK_COLOR\|FLAG_NONE_COLOR" src/ tests/ scripts/` vacío.

---

## Task 2: `ClipThumbnail` deja de cargar datos que nadie lee

**Files:**
- Modify: `src/clasificador_video/ui/clip_sheet.py:26-36`
- Modify: `src/clasificador_video/ui/main_window.py:692-714` (`_refresh_sheet`)
- Test: `tests/ui/test_clip_sheet.py`, `tests/ui/test_main_window.py`

`in_frame`, `out_frame` y `duration_frames` ya viajan y se tiran. Faltan dos
datos para poder dibujar lo que el mockup dibuja:

- **`numero`** — el `093` de la esquina. Sale de `clip.orden`, no del índice:
  el orden es lo que el editor va a nombrar cuando hable de un clip.
- **`fps`** — sin fps, `duration_frames` no se puede convertir a `0:19`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_clip_sheet.py  (agregar)

def test_la_tarjeta_conoce_su_numero_y_su_duracion(qtbot):
    """Sin numero no se puede hablar de un clip; sin duracion no se sabe
    cual es largo. Los dos estan en el mockup y la F2 los perdio."""
    clip = ClipThumbnail(
        path=Path("/tmp/C0093.MP4"), room_label=SIN_CLASIFICAR, flag="none",
        numero=93, duration_frames=570, fps=30.0,
    )
    sheet = _sheet(qtbot, [clip])
    assert sheet.item_widgets[0].clip.numero == 93
    assert sheet.item_widgets[0].texto_duracion() == "0:19"


def test_la_duracion_no_se_muestra_si_no_se_conoce():
    """Sesion restaurada de disco: no se volvio a correr ffprobe."""
    from clasificador_video.ui.clip_sheet import ClipCard
    clip = ClipThumbnail(path=Path("/tmp/x.MP4"), room_label="Sala", flag="none")
    assert ClipCard(clip).texto_duracion() == ""


def test_la_duracion_pasa_del_minuto():
    from clasificador_video.ui.clip_sheet import ClipCard
    clip = ClipThumbnail(
        path=Path("/tmp/x.MP4"), room_label="Sala", flag="none",
        duration_frames=2400, fps=30.0,
    )
    assert ClipCard(clip).texto_duracion() == "1:20"
```

```python
# tests/ui/test_main_window.py  (agregar; usa los helpers ya existentes)

def test_la_hoja_recibe_el_numero_de_clip_y_los_fps(qtbot, tmp_path):
    """Los campos que se cargan pero nadie lee son funciones perdidas: este
    test es el que evita que vuelva a pasar (ANALISIS post-F2 §7)."""
    window = _window(qtbot)
    window.load_clips([_clip(tmp_path, orden=93, fps=29.97)])
    tarjeta = window.clip_sheet.item_widgets[0]
    assert tarjeta.clip.numero == 93
    assert tarjeta.clip.fps == 29.97
```

- [ ] **Step 2: Implementar**

```python
# src/clasificador_video/ui/clip_sheet.py
@dataclass
class ClipThumbnail:
    path: Path
    room_label: str
    flag: str  # "none" | "pick" | "reject"
    room_color: str | None = None
    numero: int = 0
    in_frame: int | None = None
    out_frame: int | None = None
    duration_frames: int | None = None
    fps: float = 0.0
    aspect_ratio: float = 16 / 9
```

En `ClipCard`:

```python
    def texto_duracion(self) -> str:
        """Vacio cuando no se conoce: en una sesion restaurada de disco no se
        volvio a correr ffprobe, y mentir con 0:00 es peor que no decir nada."""
        if not self._clip.duration_frames or not self._clip.fps:
            return ""
        total = round(self._clip.duration_frames / self._clip.fps)
        return f"{total // 60}:{total % 60:02d}"
```

En `MainWindow._refresh_sheet`, agregar al `ClipThumbnail(...)`:
`numero=clip.orden,` y `fps=clip.fps,`.

- [ ] **Step 3: Verificar** — la suite completa en verde.

---

## Task 3: `_CardOverlay` — lo que el mockup dibuja sobre la miniatura

**Files:**
- Modify: `src/clasificador_video/ui/clip_sheet.py` (clase nueva + `ClipCard`)
- Modify: `src/clasificador_video/ui/theme.py::build_stylesheet` (borde de selección)
- Test: `tests/ui/test_clip_sheet.py`

Seis elementos, todos del `.card` del mockup (líneas 241-257 del HTML):

| Elemento | Dónde | Regla |
|---|---|---|
| Número de clip | arriba izquierda | siempre, pastilla oscura, mono 9 px |
| Duración | abajo derecha | solo si se conoce |
| Glifo `P` / `X` | arriba derecha | 15×15, tinta oscura sobre el color del estado |
| Franja del cuarto | borde izquierdo, 3 px | color de identidad del cuarto |
| Franja rayada | borde izquierdo, 3 px | **solo** cuando no tiene cuarto |
| Barra de rango | abajo, 2 px de alto | solo si tiene `in` u `out` |
| Palomita | abajo izquierda | solo con selección múltiple |

La franja del cuarto **se muda del QSS al overlay**: hoy es un `border-left` y
la rayada no se puede expresar en QSS. Teniendo las dos en el mismo `paintEvent`
queda garantizado que son excluyentes —o cuarto, o rayado— y no se pueden
solapar por un orden de reglas.

- [ ] **Step 1: Escribir los tests que fallan**

Los tests se escriben contra un método puro `plan_de_pintado()` que devuelve
qué piezas van y con qué color, y **una sola** verificación de píxel real. La
razón: afirmar colores contra un `grab()` píxel por píxel es frágil (antialias,
escala del entorno), pero un plan de pintado que no se prueba contra la pantalla
puede estar mintiendo. Uno de cada uno cubre las dos cosas.

```python
# tests/ui/test_clip_sheet.py  (agregar)

def _card(**kwargs):
    from clasificador_video.ui.clip_sheet import ClipCard
    base = dict(path=Path("/tmp/C0093.MP4"), room_label=SIN_CLASIFICAR,
                flag="none", numero=93)
    return ClipCard(ClipThumbnail(**{**base, **kwargs}))


def test_el_numero_de_clip_va_siempre_y_con_tres_digitos(qtbot):
    assert _card().plan_de_pintado()["numero"] == "093"


def test_sin_cuarto_lleva_la_franja_rayada_y_no_la_de_color(qtbot):
    plan = _card().plan_de_pintado()
    assert plan["franja"] == "rayada"


def test_con_cuarto_lleva_la_franja_de_color_del_cuarto_y_no_la_rayada(qtbot):
    plan = _card(room_label="Cocina", room_color=theme.room_color(0)).plan_de_pintado()
    assert plan["franja"] == theme.room_color(0)


def test_pick_dibuja_el_glifo_P_en_tinta_oscura(qtbot):
    plan = _card(flag="pick").plan_de_pintado()
    assert plan["glifo"] == ("P", theme.PICK_COLOR, theme.PICK_INK)


def test_reject_dibuja_el_glifo_X(qtbot):
    assert _card(flag="reject").plan_de_pintado()["glifo"][0] == "X"


def test_sin_marca_no_dibuja_glifo(qtbot):
    """La ausencia de glifo ES la informacion: el mockup no pinta nada."""
    assert _card().plan_de_pintado()["glifo"] is None


def test_la_barra_de_rango_solo_aparece_si_hay_in_o_out(qtbot):
    """Se perdio en la F2 y la F5 la necesita para el filtro 'sin in/out'."""
    assert _card().plan_de_pintado()["rango"] is None
    plan = _card(in_frame=100, out_frame=400, duration_frames=800).plan_de_pintado()
    assert plan["rango"] == (0.125, 0.5)


def test_un_in_sin_out_marca_hasta_el_final(qtbot):
    plan = _card(in_frame=400, duration_frames=800).plan_de_pintado()
    assert plan["rango"] == (0.5, 1.0)


def test_sin_duracion_conocida_no_hay_barra_de_rango(qtbot):
    """No se puede ubicar un frame dentro de un clip de largo desconocido."""
    assert _card(in_frame=100, out_frame=400).plan_de_pintado()["rango"] is None


def test_la_palomita_solo_aparece_con_seleccion_multiple(qtbot):
    sheet = _sheet(qtbot, [_clip(0, "Sala"), _clip(1, "Sala")])
    sheet.item_widgets[0].clicked.emit(Qt.KeyboardModifier.NoModifier)
    assert sheet.item_widgets[0].plan_de_pintado()["palomita"] is False
    sheet.item_widgets[1].clicked.emit(Qt.KeyboardModifier.ShiftModifier)
    assert sheet.item_widgets[0].plan_de_pintado()["palomita"] is True


def test_el_overlay_no_se_come_el_scrub_de_la_miniatura(qtbot):
    """Sin WA_TransparentForMouseEvents el overlay se queda con el mouse y
    el scrub al pasar por encima —que ya funcionaba— deja de andar."""
    tarjeta = _sheet(qtbot, [_clip(0, "Sala")]).item_widgets[0]
    assert tarjeta._overlay.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert tarjeta._overlay.testAttribute(Qt.WA_TranslucentBackground)


def test_el_overlay_pinta_de_verdad_sobre_la_miniatura(qtbot):
    """Candado 3 en chico: el plan de pintado puede estar perfecto y el
    widget no dibujar nada. Se mira un pixel de la franja del cuarto."""
    from PySide6.QtGui import QColor
    sheet = _sheet(qtbot, [_clip(0, "Cocina")])
    sheet.show()
    qtbot.waitExposed(sheet)          # sin show() el layout no corre nunca
    tarjeta = sheet.item_widgets[0]
    tarjeta.set_pixmap(_pixmap(Qt.GlobalColor.black))
    imagen = tarjeta.grab().toImage()
    # `grab()` devuelve a la escala de la pantalla: 1x bajo offscreen, 2x en
    # una Retina de verdad. Sin normalizar, el test pasa en CI y miente en la
    # maquina de Bruno (es el mismo bug que ya tuvo el arnes).
    escala = imagen.width() / max(tarjeta.width(), 1)
    columna = imagen.pixelColor(round(1 * escala), imagen.height() // 2)
    assert columna == QColor(theme.room_color(0))
```

- [ ] **Step 2: Implementar**

Constantes de geometría al tope de `clip_sheet.py`, junto a `GAP`:

```python
STRIPE_WIDTH = 3      # franja de cuarto / rayado de sin clasificar
GLYPH_SIZE = 15       # pastilla del glifo de estado
RANGE_HEIGHT = 2      # barra de in/out al pie
BADGE_RADIUS = 3
PAD = 5               # separacion de las pastillas al borde de la tarjeta
```

`ClipCard.__init__` crea el overlay **después** de `image_label` y lo mantiene
del tamaño de la tarjeta en `resizeEvent`:

```python
        self._overlay = _CardOverlay(self)
        self._overlay.setAttribute(Qt.WA_TranslucentBackground, True)
        self._overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
```

```python
    def resizeEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()
```

`plan_de_pintado()` en `ClipCard` —puro, sin Qt, por eso se puede probar
directo—:

```python
    def plan_de_pintado(self) -> dict:
        """Que piezas van sobre la miniatura y con que color. Separado del
        paintEvent para poder probarlo sin mirar pixeles."""
        clip = self._clip
        glifo = {
            "pick": ("P", theme.PICK_COLOR, theme.PICK_INK),
            "reject": ("X", theme.REJECT_COLOR, theme.REJECT_INK),
        }.get(clip.flag)
        rango = None
        if clip.duration_frames and (clip.in_frame is not None or clip.out_frame is not None):
            total = clip.duration_frames
            inicio = (clip.in_frame or 0) / total
            fin = (clip.out_frame / total) if clip.out_frame is not None else 1.0
            rango = (max(0.0, min(1.0, inicio)), max(0.0, min(1.0, fin)))
        return {
            "numero": f"{clip.numero:03d}",
            "duracion": self.texto_duracion(),
            "glifo": glifo,
            "franja": clip.room_color or "rayada",
            "rango": rango,
            "palomita": bool(getattr(self, "_is_selected", False)),
        }
```

`_CardOverlay.paintEvent` consume ese plan. La franja rayada se pinta con un
`QBrush` de patrón diagonal entre `UNCLASSIFIED_STRIPE` y `LINE`; las pastillas
con `QColor(*theme.CARD_BADGE_BG_RGBA)`; el riel del rango con
`QColor(*theme.RANGE_TRACK_RGBA)` y el tramo marcado con `theme.TRIM_COLOR`.

En `_apply_state`, el borde de selección múltiple pasa a `SELECTION_BORDER`
(hoy solo hay lavado de fondo; el mockup marca borde **y** lavado **y**
palomita), y **se quita el `border-left` del cuarto**, que ahora lo pinta el
overlay.

- [ ] **Step 3: Verificar** — suite en verde. Correr el arnés con recorte
  (Task 6) sobre la hoja y **mirar la imagen**: número, duración, glifo, franja
  y rayado tienen que leerse a tamaño real, no solo al 300%.

---

## Task 4: La leyenda del rail y el keycap de buscar

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py:19-48,131-133,143-147,195-198`
- Modify: `src/clasificador_video/ui/theme.py::build_stylesheet`
- Test: `tests/ui/test_room_rail.py`

Tres cosas del análisis §3, más dos que aparecieron al ampliar el recorte del
rail durante la lectura de este plan y que van aquí porque son la misma zona y
cuestan dos líneas:

1. La leyenda se desborda en 200 px → etiquetas cortas del mockup (`41 · 9 · 12`),
   con **tooltip** que dice qué es cada número, porque el número pelado es
   críptico y el mockup se apoya en el color para desambiguar.
2. Los puntos van con el color de su estado, no todos grises.
3. `⏎ buscar` con el `⏎` dentro de un keycap.
4. *(extra)* Faltan los separadores finos bajo el bloque de progreso y bajo el
   encabezado `CUARTOS`; el mockup los tiene (`border-bottom: 1px solid
   var(--line-soft)`).
5. *(extra)* Los tramos de la barra de progreso son pastillas con esquinas
   redondas; en el mockup el redondeo es del contenedor y los tramos son
   rectos, así que se ven como una sola barra partida y no como nueve píldoras.

El chip `6 dest.` del mockup **no se agrega**: el estado «destacado» no existe
hasta la F7. `set_flags` recibe hoy tres números y recibirá cuatro entonces.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_room_rail.py  (reemplaza el test de la leyenda de la linea 61)

def test_la_leyenda_usa_etiquetas_cortas_que_entran_en_200px(qtbot):
    """`● 41 picks ● 9 rejects ● 12 sin clasificar` no entra en el rail y se
    cortaba a la mitad. El mockup se apoya en el color, no en el texto."""
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    assert [p.text() for p in rail.leyenda.puntos] == ["41", "9", "12"]
    assert rail.leyenda.sizeHint().width() <= theme.RAIL_WIDTH


def test_cada_punto_de_la_leyenda_lleva_el_color_de_su_estado(qtbot):
    """Todos grises es informacion tirada a la basura."""
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    assert rail.leyenda.colores() == [
        theme.PICK_COLOR, theme.REJECT_COLOR, theme.PENDING_COLOR,
    ]


def test_la_leyenda_dice_que_es_cada_numero_al_pasar_el_mouse(qtbot):
    rail = _rail(qtbot)
    rail.set_flags(41, 9, 12)
    assert "picks" in rail.leyenda.puntos[0].toolTip()
    assert "sin clasificar" in rail.leyenda.puntos[2].toolTip()


def test_el_enter_de_buscar_va_dentro_de_un_keycap(qtbot):
    """Igual que las teclas de cuarto: si es una tecla, se ve como tecla."""
    rail = _rail(qtbot)
    assert rail.find_key.text() == "⏎"
    assert rail.find_key.objectName() == "keyCap"
    assert rail.find_hint.text() == "buscar"


def test_solo_los_tramos_de_los_extremos_van_redondeados(qtbot):
    """Nueve pildoras separadas no se leen como una sola barra de progreso.
    El radio del contenedor no sirve: no recorta a los hijos (verificado)."""
    rail = _rail(qtbot)
    rail.set_progress(116, 128, 12)
    rail.set_rooms(["Cocina", "Sala", "Baño"], {"Cocina": 24, "Sala": 16, "Baño": 8})
    tramos = rail.progress_bar._tramos
    assert "border-radius" in tramos[0].styleSheet()
    assert "border-radius" in tramos[-1].styleSheet()
    assert all("border-radius" not in t.styleSheet() for t in tramos[1:-1])
```

- [ ] **Step 2: Implementar** — `_Leyenda(QWidget)` con una fila de
  `(cuadrito de 6×6, número)` por estado; `set_flags` la alimenta con
  `[(picks, PICK_COLOR, "picks"), (rejects, REJECT_COLOR, "rejects"),
  (sin_clasificar, PENDING_COLOR, "sin clasificar")]`. `find_hint` se parte en
  `find_key` (objectName `keyCap`, 16×14) + `find_hint` (`buscar`). En QSS,
  `#railProgressBlock` y el encabezado de cuartos llevan
  `border-bottom: 1px solid {LINE_SOFT}`.

  > **Verificado ejecutando contra Qt (no de memoria): el `border-radius` de un
  > contenedor NO recorta a sus hijos.** Un hijo llega hasta la esquina cuadrada
  > —medido: el píxel (0,0) del contenedor redondeado devuelve el color del
  > primer tramo, no el del fondo—. Así que redondear el contenedor no sirve:
  > `set_counts` deja los tramos rectos y le pone el radio **solo al primero y
  > al último**, que es información que solo él tiene.

- [ ] **Step 3: Verificar** — suite en verde, y recorte del rail contra el
  mockup mirado de cerca.

---

## Task 5: Dos badges sobre el video, cada uno con su color

**Files:**
- Modify: `src/clasificador_video/ui/video_stage.py:40-41,78-79,94-96`
- Modify: `src/clasificador_video/ui/main_window.py:323-349` (`_refresh_overlays`)
- Modify: `src/clasificador_video/ui/theme.py::build_stylesheet`
- Test: `tests/ui/test_video_stage.py`, `tests/ui/test_main_window.py`

Hoy: una etiqueta gris con `▌ COMEDOR    ● PICK` adentro. El mockup: un badge
de cuarto (punto del color del cuarto, borde y texto derivados de ese color) y
un badge de estado con el color del estado. Con una sola etiqueta gris, el
color —que es el canal que hace legible el estado de un vistazo— se pierde.

Los badges `▶ auto` y `Proxy 1080p` del mockup son de la F6 y la F9: no se
inventan aquí.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_video_stage.py  (agregar)

def test_el_badge_de_cuarto_lleva_el_color_del_cuarto(qtbot):
    stage = _stage(qtbot)
    stage.badges.set_room("Cocina", theme.room_color(0))
    assert stage.badges.room_badge.text().endswith("COCINA")
    assert theme.aclarar(theme.room_color(0), 0.45) in stage.badges.room_badge.styleSheet()


def test_el_badge_de_estado_es_otro_badge_y_no_texto_pegado(qtbot):
    """Juntar cuarto y estado en una etiqueta gris tira el color, que es lo
    que hace legible el estado de un vistazo."""
    stage = _stage(qtbot)
    stage.badges.set_flag("pick")
    assert stage.badges.flag_badge.isVisible() or not stage.badges.flag_badge.isHidden()
    assert theme.PICK_COLOR in stage.badges.flag_badge.styleSheet()


def test_sin_marca_no_hay_badge_de_estado(qtbot):
    stage = _stage(qtbot)
    stage.badges.set_flag("none")
    assert stage.badges.flag_badge.isHidden()


def test_sin_cuarto_el_badge_dice_sin_clasificar_sin_color_de_cuarto(qtbot):
    stage = _stage(qtbot)
    stage.badges.set_room(None, None)
    assert "SIN CLASIFICAR" in stage.badges.room_badge.text()
```

En `tests/ui/test_main_window.py` se reescriben los tres asserts de
`badges.text()` (líneas 617, 618, 624) contra `room_badge.text()` y
`flag_badge.text()`.

- [ ] **Step 2: Implementar** — `_BadgeRow(QWidget)` en `video_stage.py` con
  `room_badge` y `flag_badge` en un `QHBoxLayout`, expuesto como
  `stage.badges`. `set_room(nombre, color)` arma el estilo con
  `theme.aclarar(color, 0.45)` para el texto y `theme.con_alfa(color, 140)`
  para el borde; `set_flag(flag)` esconde el badge cuando es `none`.
  `_place_overlays` sigue igual salvo `adjustSize()` → el layout ya lo hace.

- [ ] **Step 3: Verificar** — suite en verde y **mirar** el recorte del área de
  badges sobre el frame sintético de la Task 6: el punto de esta tarea es el
  contraste, y sin frame detrás no se puede juzgar.

---

## Task 6: El arnés — frame sintético, ruta de ejemplo y modo recorte

**Files:**
- Modify: `scripts/comparar_con_mockup.py`
- Modify: `scripts/_datos_de_ejemplo.py`
- Test: `tests/test_comparar_con_mockup.py`

Tres cosas, las tres del análisis §4 y de la lección de la F2 («la vista general
no alcanza»):

1. **Frame sintético detrás del video.** Hoy el área sale negra porque el doble
   de mpv no dibuja, así que no se puede juzgar el contraste de los overlays —
   que es justo lo que la F0 validó y lo que más riesgo tiene de verse mal.
2. **Ruta de ejemplo en la barra de estado**, que hoy sale vacía porque no hubo
   importación.
3. **`--recorte X,Y,ANCHO,ALTO --zoom N`**: recorta la *misma* región de las dos
   mitades y las pega ampliadas. La regresión de las tarjetas era invisible en
   la vista completa y obvia en el recorte.

El frame se agrega **después** de `show()` y `processEvents()`: `_place_overlays`
corre en cada resize del video y hace `scrim.lower()`, así que un hijo agregado
antes terminaría por encima del scrim. Se agrega al final y se baja al fondo.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_comparar_con_mockup.py  (agregar)

def test_el_recorte_toma_la_misma_region_de_las_dos_mitades():
    """Si las regiones no son equivalentes, el recorte compara peras con
    manzanas y es peor que no tenerlo."""
    izq, der = comparar.regiones_de_recorte((10, 20, 100, 50), ancho_mitad=1600,
                                            separacion=40)
    assert izq == (10, 20, 100, 50)
    assert der == (1650, 20, 100, 50)


def test_el_recorte_se_parsea_de_la_linea_de_comandos():
    assert comparar.parsear_recorte("10,20,100,50") == (10, 20, 100, 50)


def test_un_recorte_mal_escrito_falla_fuerte_y_no_en_silencio():
    import pytest
    with pytest.raises(SystemExit):
        comparar.parsear_recorte("10,20,100")


def test_el_lienzo_del_recorte_crece_con_el_zoom():
    ancho, alto = comparar.geometria_lienzo((200, 100), (200, 100), separacion=20)
    assert (ancho, alto) == (420, 100)
```

- [ ] **Step 2: Implementar** — en `comparar_con_mockup.py`, `parsear_recorte`,
  `regiones_de_recorte` y un paso de recorte+escala antes de `componer`. En
  `_datos_de_ejemplo.py`, `pintar_frame_de_ejemplo(ventana)` (un `QLabel` hijo
  del `VideoWidget` con un degradado sintético, `lower()` al final) y
  `ventana.status_bar.set_volume("/Volumes/FX30/CasaLomas")`, que es la ruta que
  muestra el mockup.

- [ ] **Step 3: Verificar** — correr el arnés completo y con recorte, y mirar
  las dos imágenes.

---

## Task 7: Cierre de la F2.1 — Candados 3 y 4

- [ ] Suite completa en verde (283 + los nuevos).
- [ ] `grep -rn "RANGE_TRACK_COLOR\|FLAG_NONE_COLOR" src/ tests/ scripts/` vacío
      — su renglón de la lista de ejecución se tacha.
- [ ] **Buscar campos que nadie lee** en `ClipThumbnail` y en `ClipCard`:
      es el mejor detector de funciones perdidas y es lo que encontró esta
      regresión. Con `grep` sobre cada nombre de campo, no de memoria.
- [ ] Arnés corrido, imagen completa **mirada**, y al menos tres recortes
      ampliados: tarjetas, rail y badges sobre el video.
- [ ] Cada diferencia contra el mockup queda **arreglada o escrita** en el
      análisis de cierre, con su fase.
- [ ] Commit con mensaje en español mexicano.

**Diferencias que la F2.1 deja a propósito** (ya detectadas, para no volver a
descubrirlas):

| Diferencia | Por qué se deja | Fase |
|---|---|---|
| El visor dice `87 / 128` y el mockup `3 de 12 en la cola` | La cola filtrada no existe todavía | F5 |
| El nombre de archivo va en una pastilla; el mockup lo pone como texto plano sobre un scrim superior | Esa fila del mockup lleva además el control de velocidad, que no existe hasta la F6: se rehace entera una sola vez | F6 |
| No hay barrita ni timecode al escrubear la miniatura | El scrub funciona; falta su indicador | F8 |
| La leyenda no tiene el chip `6 dest.` | No existe el estado «destacado» | F7 |
| No están los badges `▶ auto` ni `Proxy 1080p` | Autoplay y proxies | F6 / F9 |

---

# FASE 3 — Cuartos planos

**Decisiones tomadas con Bruno el 2026-08-08, antes de escribir esta fase:**

- **El rail se edita con menú contextual y doble click.** Click derecho sobre un
  cuarto abre `Renombrar…`, `Subir`, `Bajar`, `Eliminar`; doble click renombra.
  Es lo convencional en macOS, y son acciones de una vez por shooting: no
  merecen atajos nuevos ni el riesgo del drag-and-drop dentro de un
  `QVBoxLayout`. Subir/Bajar además deja explícito que reordenar **es cambiar
  qué tecla le toca a cada cuarto**.
- **La app abre con el rail vacío.** Es la lectura literal de `DECISIONES.md`
  («la app abre lista para trabajar; no hay paso previo de elegir los cuartos»).
  Los cuartos se crean sobre la marcha desde la fila `+ Nuevo cuarto`.

## Task 8: `RoomSelection` deja de ser el estado de un diálogo

**Files:**
- Modify: `src/clasificador_video/rooms.py`
- Test: `tests/test_rooms.py`

Muere `REPEATABLE_ROOMS` y `set_count` —la máquina de `Recámara 1..N` que
existía para generar subcuartos numerados— y nacen las tres operaciones que el
rail necesita. `MASTER_ROOM_LIST` **también muere**: era el catálogo del diálogo
de configuración, y con cuartos creados sobre la marcha no tiene destinatario.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_rooms.py  (agregar; los de set_count se borran)

def test_renombrar_conserva_la_posicion_y_por_lo_tanto_la_tecla():
    sel = RoomSelection()
    for c in ("Cocina", "Sala", "Baño"):
        sel.add(c)
    sel.rename("Sala", "Sala de TV")
    assert sel.active_rooms() == ["Cocina", "Sala de TV", "Baño"]


def test_mover_un_cuarto_cambia_su_tecla():
    """Reordenar ES cambiar la tecla: no hay otra cosa que reordenar."""
    sel = RoomSelection()
    for c in ("Cocina", "Sala", "Baño"):
        sel.add(c)
    sel.move("Baño", -1)
    assert sel.active_rooms() == ["Cocina", "Baño", "Sala"]


def test_mover_en_los_extremos_no_hace_nada_y_no_revienta():
    sel = RoomSelection()
    sel.add("Cocina")
    sel.move("Cocina", -1)
    sel.move("Cocina", +1)
    assert sel.active_rooms() == ["Cocina"]


def test_eliminar_saca_el_cuarto_y_corre_las_teclas():
    sel = RoomSelection()
    for c in ("Cocina", "Sala", "Baño"):
        sel.add(c)
    sel.remove("Cocina")
    assert sel.active_rooms() == ["Sala", "Baño"]


def test_no_se_puede_crear_dos_veces_el_mismo_cuarto():
    sel = RoomSelection()
    sel.add("Cocina")
    sel.add("Cocina")
    assert sel.active_rooms() == ["Cocina"]


def test_ya_no_hay_cuartos_repetibles_ni_catalogo_maestro():
    """Los cuartos son planos y se crean sobre la marcha: 'Recámara 1' es un
    nombre, no una instancia numerada de un cuarto plantilla."""
    import clasificador_video.rooms as rooms
    assert not hasattr(rooms, "REPEATABLE_ROOMS")
    assert not hasattr(rooms, "MASTER_ROOM_LIST")
    assert not hasattr(RoomSelection, "set_count")
```

- [ ] **Step 2: Implementar** — `add`, `rename`, `move(nombre, delta)`,
  `remove`; `toggle` se conserva mientras `app.py::_rebuild_room_selection` la
  use, o se cambia por `add` en la Task 11 (preferible: una sola forma de
  agregar).

- [ ] **Step 3: Verificar.**

> **Antes de las Tasks 9 a 11, arreglar los helpers de los tests.** Verificado
> leyendo el archivo: `tests/ui/test_main_window.py::_window(qtbot)` **no acepta
> `rooms=`** (crea "Sala" y "Cocina" fijos) y **no existe un helper `_clip`**.
> Los tests de esta fase los necesitan. Se agregan como primer paso de la
> Task 9: `_window(qtbot, rooms=("Sala", "Cocina"))` y
> `_clip(tmp_path, orden=1, fps=30.0)`. Es refactor de tests, va en su propio
> commit y no cambia ni una línea de `src/`.

## Task 9: Muere la rama de subcuartos

**Files:**
- Delete: `src/clasificador_video/category_path.py`
- Delete: `tests/test_category_path.py`
- Modify: `src/clasificador_video/keyboard.py` (`pending_parent`, `resolve_subroom_key`, `subrooms`)
- Modify: `src/clasificador_video/ui/main_window.py:40,351-359,540-543,560-567,580-595,630-661`
- Modify: `src/clasificador_video/ui/room_rail.py:151-155` (`subroom_banner`)
- Test: `tests/test_keyboard.py`, `tests/ui/test_main_window.py`, `tests/ui/test_room_rail.py`

Todo lo que muere aquí está en la lista de ejecución del análisis §5:
`SUBROOM_CANDIDATES`, `_handle_subroom_key`, `_update_subroom_banner`,
`attach_subroom_or_resolve`, `_ask_parent_room`, `RoomRail.subroom_banner`,
`CategoryTree` completo y el parámetro `category_tree` de `MainWindow`.

**`categoria_path` se queda como lista**, de un solo elemento. El contrato del
manifest con el plugin de Premiere no se toca — el plugin ya maneja el caso.
Un test lo fija para que nadie «simplifique» el campo a string más adelante.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_keyboard.py  (los de subcuartos se BORRAN, no se adaptan: el
# comportamiento murio a proposito, no cambio de forma)

def test_una_tecla_un_cuarto_sin_estado_intermedio():
    """Nada de esperar una segunda tecla: DECISIONES.md, 'Cuartos planos'."""
    router = KeyboardRouter(active_rooms=["Cocina", "Recámara 1"])
    assert router.resolve_room_key("2") == ["Recámara 1"]
    assert not hasattr(router, "pending_parent")
    assert not hasattr(router, "resolve_subroom_key")
```

```python
# tests/ui/test_main_window.py  (agregar)

def test_una_tecla_clasifica_un_cuarto_numerado_de_inmediato(qtbot, tmp_path):
    """Antes 'Recámara 1' abria el banner de subcuarto y esperaba otra tecla."""
    window = _window(qtbot, rooms=["Cocina", "Recámara 1"])
    window.load_clips([_clip(tmp_path)])
    window.handle_key_press("2")
    assert window.clips[0].categoria_path == ["Recámara 1"]


def test_categoria_path_sigue_siendo_una_lista(qtbot, tmp_path):
    """El contrato con el plugin de Premiere no se toca aunque el cuarto sea
    plano: el plugin ya maneja la lista de un elemento."""
    window = _window(qtbot, rooms=["Cocina"])
    window.load_clips([_clip(tmp_path)])
    window.handle_key_press("1")
    assert window.clips[0].to_dict()["categoria_path"] == ["Cocina"]
```

- [ ] **Step 2: Implementar** — borrar. Cada test borrado se justifica en el
  mensaje del commit: *el comportamiento murió a propósito*.

- [ ] **Step 3: Verificar** — `grep -rn "subroom\|CategoryTree\|category_tree\|pending_parent" src/ tests/ scripts/ uxp-plugin/`
  solo debe devolver, si acaso, algo del plugin (que no se toca).

## Task 10: El rail se edita en el lugar

**Files:**
- Modify: `src/clasificador_video/ui/room_rail.py`
- Modify: `src/clasificador_video/ui/main_window.py` (conectar las señales)
- Modify: `src/clasificador_video/ui/theme.py::build_stylesheet` (fila `+ Nuevo cuarto`)
- Test: `tests/ui/test_room_rail.py`, `tests/ui/test_main_window.py`

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/ui/test_room_rail.py  (agregar)

def test_la_fila_de_nuevo_cuarto_esta_siempre_al_pie_de_la_lista(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina"], {"Cocina": 3})
    assert rail.new_room_row.isVisible() or not rail.new_room_row.isHidden()


def test_crear_un_cuarto_emite_su_nombre(qtbot):
    rail = _rail(qtbot)
    with qtbot.waitSignal(rail.room_created) as blocker:
        rail._crear_cuarto("Alberca")
    assert blocker.args == ["Alberca"]


def test_crear_un_cuarto_con_nombre_vacio_no_emite_nada(qtbot):
    rail = _rail(qtbot)
    with qtbot.assertNotEmitted(rail.room_created):
        rail._crear_cuarto("   ")


def test_renombrar_reordenar_y_borrar_emiten_lo_suyo(qtbot):
    rail = _rail(qtbot)
    rail.set_rooms(["Cocina", "Sala"], {})
    with qtbot.waitSignal(rail.room_renamed) as b:
        rail.rows[0].pedir_renombrar("Cocina chica")
    assert b.args == ["Cocina", "Cocina chica"]
    with qtbot.waitSignal(rail.room_moved) as b:
        rail.rows[1].pedir_mover(-1)
    assert b.args == ["Sala", -1]
    with qtbot.waitSignal(rail.room_removed) as b:
        rail.rows[0].pedir_eliminar()
    assert b.args == ["Cocina"]


def test_el_rail_arranca_vacio_y_no_pretende_que_haya_cuartos(qtbot):
    """La app abre lista para trabajar: sin paso previo de configuracion."""
    rail = _rail(qtbot)
    assert rail.rows == []
```

```python
# tests/ui/test_main_window.py  (agregar)

def test_crear_un_cuarto_desde_el_rail_le_da_la_siguiente_tecla(qtbot, tmp_path):
    window = _window(qtbot, rooms=["Cocina"])
    window.load_clips([_clip(tmp_path)])
    window.room_rail.room_created.emit("Alberca")
    window.handle_key_press("2")
    assert window.clips[0].categoria_path == ["Alberca"]


def test_renombrar_un_cuarto_renombra_los_clips_ya_clasificados(qtbot, tmp_path):
    """Si no, los clips quedan apuntando a un cuarto que ya no existe y
    desaparecen del rail sin haber cambiado de lugar."""
    window = _window(qtbot, rooms=["Cocina"])
    window.load_clips([_clip(tmp_path)])
    window.handle_key_press("1")
    window.room_rail.room_renamed.emit("Cocina", "Cocina chica")
    assert window.clips[0].categoria_path == ["Cocina chica"]


def test_borrar_un_cuarto_deja_sus_clips_sin_clasificar(qtbot, tmp_path):
    """Vuelven a la cola de trabajo, que es donde tienen que estar."""
    window = _window(qtbot, rooms=["Cocina"])
    window.load_clips([_clip(tmp_path)])
    window.handle_key_press("1")
    window.room_rail.room_removed.emit("Cocina")
    assert window.clips[0].categoria_path == []


def test_reordenar_no_toca_la_clasificacion_de_los_clips(qtbot, tmp_path):
    """Cambia la tecla, no a que cuarto pertenece cada clip."""
    window = _window(qtbot, rooms=["Cocina", "Sala"])
    window.load_clips([_clip(tmp_path)])
    window.handle_key_press("2")
    window.room_rail.room_moved.emit("Sala", -1)
    assert window.clips[0].categoria_path == ["Sala"]
    assert window.room_selection.active_rooms() == ["Sala", "Cocina"]
```

- [ ] **Step 2: Implementar** — señales `room_created`, `room_renamed`,
  `room_moved`, `room_removed` en `RoomRail`; `_FilaCuarto` gana
  `contextMenuEvent` (`QMenu` con las cuatro acciones) y `mouseDoubleClickEvent`
  (renombrar). El renombrado usa `QInputDialog.getText`. La fila
  `+ Nuevo cuarto` es un `QPushButton` con estilo punteado —el `.newroom` del
  mockup— que abre el mismo diálogo. `MainWindow` conecta las cuatro y
  reconstruye el `KeyboardRouter` con los cuartos nuevos en cada una.

  > **Ojo con el router:** hoy se construye una sola vez en `__init__`. Cada
  > operación del rail tiene que rehacerlo (o mutar `active_rooms`), o las
  > teclas siguen apuntando a la lista vieja **sin dar ningún síntoma visible**.

- [ ] **Step 3: Verificar.**

## Task 11: Muere el diálogo de configuración inicial

**Files:**
- Delete: `src/clasificador_video/ui/room_config_dialog.py`
- Delete: `tests/ui/test_room_config_dialog.py`
- Modify: `src/clasificador_video/app.py:9,12,17,58-104`
- Test: `tests/test_app.py` (excluido de la corrida, **igual se actualiza**)

`arrancar()` deja de abrir un diálogo y de poder devolver `None`. Se le quita
`category_tree` a `MainWindow` y a `_restore_session`, y el `category_tree` del
autosave deja de escribirse.

**Compatibilidad de sesiones viejas:** una sesión guardada antes de la F3 tiene
`category_tree` y puede tener `categoria_path` de dos elementos. Se ignora el
árbol y se **aplana el path quedándose con el primer elemento** —el cuarto
padre, que es el que existe en el rail—, en vez de tirar el dato o de crear un
cuarto `Recámara 1 › Baño`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_app.py  (actualizar)

def test_arrancar_abre_directo_sin_pedir_configuracion(qtbot):
    """No hay paso previo: la app abre lista para trabajar."""
    window = arrancar(video_factory=FakeMpv, session_path=tmp_session)
    assert window is not None
    assert window.room_selection.active_rooms() == []


def test_una_sesion_vieja_con_subcuartos_se_aplana_al_cuarto_padre(tmp_path):
    """Se conserva el cuarto, que existe; se descarta el subcuarto, que ya
    no es representable. Tirar el clip entero seria peor."""
    assert _clip_from_dict({"orden": 1, "ruta": "/x.MP4", "fps": 30.0,
                            "categoria_path": ["Recámara 1", "Baño"]}
                           ).categoria_path == ["Recámara 1"]
```

- [ ] **Step 2: Implementar.**

- [ ] **Step 3: Verificar** — suite en verde y **abrir la app de verdad**
  (`\.venv/bin/python -m clasificador_video.app`): esta tarea toca el arranque,
  que el test excluido es el único que cubre.

## Task 12: Cierre de la F3

- [ ] Suite en verde.
- [ ] `grep` confirma que los seis renglones de la F3 en la lista de ejecución
      están vacíos: `RoomConfigDialog`, `CategoryTree`, `pending_parent` /
      `resolve_subroom_key`, `SUBROOM_CANDIDATES` / `_handle_subroom_key` /
      `_update_subroom_banner`, `RoomRail.subroom_banner`, `REPEATABLE_ROOMS` /
      `set_count`.
- [ ] Campos y métodos que nadie lee, buscados con `grep`.
- [ ] Arnés corrido y la imagen **mirada**, con recorte del rail.
- [ ] Prueba a mano del arranque en frío: crear tres cuartos, clasificar con
      `1`-`3`, renombrar uno, moverlo, borrarlo, cerrar y reabrir.
- [ ] Commit en español mexicano.

---

## Auditoría de este plan — 2026-08-08

Hecha **ejecutando**, no releyendo: las tres fallas más graves de las auditorías
anteriores salieron de correr código y ninguna de volver a leer. Un spike
descartable (scratchpad de la sesión, no al repo) montó un `ClipCard` de mentira
con el overlay propuesto y lo capturó con `grab()`. Lo que cambió:

| # | Qué se creyó al escribir | Qué dijo Qt al ejecutarlo |
|---|---|---|
| 1 | `QColor.fromRgb(` haría fallar el test del Candado 1 | **Falso**: el regex es sensible a mayúsculas. El motivo real de usar tuplas es otro: `QColor("rgba(...)")` es inválido, QColor no parsea CSS |
| 2 | Redondear el contenedor de la barra recortaría los tramos | **No recorta**: el píxel (0,0) devuelve el color del hijo. Hay que redondear el primer y el último tramo |
| 3 | El test de píxel podía leer una coordenada fija | `grab()` sale a la escala de la pantalla (1× offscreen, 2× en Retina). Se normaliza o miente fuera de CI |
| 4 | Los tests de la F3 podían usar los helpers que ya hay | `_window` no acepta `rooms=` y `_clip` no existe. Se agregan primero |

Lo que la ejecución **confirmó** y ya no es apuesta: el overlay traslúcido
compone sobre el `QPixmap` de la miniatura (la pastilla con alfa 165 sobre negro
da exactamente `#030305`, el valor calculado); la franja rayada a 3 px se lee
como textura diagonal y no como una línea sucia; y las dos franjas —color de
cuarto y rayado— **tienen que ser excluyentes en el mismo `paintEvent`**: el
spike las pintó encima una de la otra y la segunda ganó **sin ningún síntoma**,
que es exactamente el tipo de error que este plan existe para evitar.

## Después de la F3

Al cerrar la F3 toca el **punto de control** del plan maestro: rehacer el
análisis contra el código nuevo antes de escribir el detalle de la F4 y la F5.
Nunca más de dos fases planeadas por delante — todo lo posterior se engancha a
clases que todavía no existen, y un plan desactualizado tiene autoridad y se
sigue en vez de pensarlo.

Orden vigente: **F4** deshacer con historial → **F5** filtros como cola →
**F6** reproducción rápida → **F7** resto del teclado → **F8** modo hoja y
pincel → **F9** proxies y orientación del manifest → **F10** barrido final.
