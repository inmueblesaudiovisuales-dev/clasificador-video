# Handoff — Rediseño de la UI, continuar desde la F2.1 — 2026-08-08

Vas a continuar un rediseño completo de la interfaz que ya lleva tres fases
hechas (F0, F1, F2) y está a mitad de camino. **Tu primera tarea es la F2.1.**

Este documento es autosuficiente para arrancar, pero **no reemplaza la lectura
de los documentos que lista la §3**. Léelos antes de escribir código.

---

## 1. Qué es el proyecto

Una app de escritorio en **PySide6 + mpv** para que Bruno, editor de video
profesional, clasifique clips de shootings inmobiliarios (recorridos de
propiedades: cocina, recámara, baño, fachada, alberca…) **antes** de editarlos
en Adobe Premiere Pro.

El flujo completo tiene dos piezas:

1. **La app** (`src/clasificador_video/`) — importa carpetas de material,
   reproduce cada clip, y el editor le asigna un **cuarto**, lo marca como
   **pick/reject** y opcionalmente le pone **in/out**. Exporta un
   `manifest.json`.
2. **El plugin UXP** (`uxp-plugin/`) — corre dentro de Premiere, lee ese
   manifest y arma el proyecto solo: bins por cuarto, etiquetas de color por
   flag, proxies enganchados, in/out aplicados.

**La razón de existir de la app es la velocidad.** Clasificar un shooting de
128 clips más rápido de lo que se haría a mano dentro de Premiere. Todo lo que
la haga más lenta va en contra de su propósito.

El material real es **HEVC 10-bit de una Sony FX30**, mayoría **vertical**.

## 2. Qué estamos haciendo y por qué

Bruno pidió un rediseño desde cero de la interfaz. El motivo concreto: **el
video vertical se veía chico**, rodeado de franjas negras, y ver el video
grande es *la* razón por la que existe esta app en vez de usar Premiere.

Se escribió un brief, se le pidió a una IA sin acceso al código que diseñara
la interfaz desde cero, y de ahí salió un **mockup en HTML** que es ahora la
fuente de verdad visual.

**Bruno tiene una queja específica que ordena todo el trabajo:**

> «Un problema que frecuentemente tengo es que las apps de Claude no quedan
> como los mockups. Quiero que te asegures de que esto vaya a quedar
> visualmente igual que el mockup o incluso mejor, no solo el diseño viejo con
> nuevas funciones a medias y con funciones viejas sin quitar.»

Por eso el plan tiene **cuatro candados anti-deriva** (§6). No son burocracia:
son la respuesta directa a esa queja. Respétalos.

## 3. Qué leer, en este orden

| # | Documento | Qué sacar de ahí |
|---|---|---|
| 1 | `CLAUDE.md` (raíz) | Convenciones obligatorias del repo: **español mexicano**, commits, higiene de archivos, decisiones de arquitectura cerradas |
| 2 | `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md` | **El comportamiento acordado.** Por qué cada cosa es como es, y qué se evaluó y se descartó |
| 3 | `docs/superpowers/ANALISIS-2026-08-08-post-f2.md` | **El estado exacto de hoy**: qué quedó bien, la regresión que tienes que arreglar, la lista de ejecución y el orden revisado de las fases |
| 4 | `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md` | El plan maestro: los cuatro candados, la lista de lo viejo que debe morir, y las fases |
| 5 | `docs/superpowers/plans/2026-08-08-f1-f2-tokens-y-esqueleto.md` | Cómo se implementaron la F1 y la F2. Útil como **modelo del nivel de detalle** que se espera de los planes que escribas |
| 6 | `docs/superpowers/CONTEXTO-Y-METAS.md` | Estado general del producto y hacia dónde va |
| 7 | `README.md` | Qué es la app y cómo correrla |

**No leas** `docs/superpowers/archive/` salvo que busques una decisión
histórica concreta. Está archivado por algo.

## 4. El diseño: cómo verlo

El mockup es un HTML autocontenido con **dos pantallas apiladas**:

```
docs/superpowers/mockups/rediseno-2026-08-08/mockup.html
```

- **Pantalla 1 — modo clip**: ver y marcar pick, un clip a la vez. Es la que
  la F2 construyó.
- **Pantalla 2 — modo hoja**: la hoja de contactos a pantalla completa para
  clasificar cuartos en lote. Es la **F8**, no existe todavía.

Ábrelo en un navegador y míralo entero antes de tocar nada. Después usa el
arnés (§7) para compararlo contra la app.

## 5. Dónde está todo hoy

### Fases terminadas

- **F0 — Spike del overlay.** Se comprobó con material real que Qt compone
  widgets encima del `QOpenGLWidget` donde mpv dibuja, y que **el alfa se
  mezcla contra los pixeles del video, no contra negro**. Sin esto el diseño
  entero era inviable.
- **F1 — Tokens y arnés.** `ui/theme.py` es la única fuente de valores
  visuales, con los hexadecimales del `:root` del mockup. Se creó
  `scripts/comparar_con_mockup.py`.
- **F2 — El esqueleto.** Se reconstruyó la ventana con la estructura del
  mockup y se borró la vieja. **El video vertical pasó de 328 a 529 px de
  ancho** en una ventana de 1600×1000.

### Arquitectura de la UI nueva

```
MainWindow  (ui/main_window.py)   — ensambla y orquesta; TRES filas y ninguna más
├── TitleBar    (ui/title_bar.py)    36 px — proyecto, guardado, Cuartos, Exportar
├── cuerpo (QHBoxLayout)
│   ├── RoomRail   (ui/room_rail.py)    200 px — progreso, barra segmentada, cuartos
│   ├── VideoStage (ui/video_stage.py)  ancho calculado — video + overlays
│   ├── ToolColumn (ui/tool_column.py)   56 px — indicadores de estado del clip
│   └── ClipSheet  (ui/clip_sheet.py)   resto — hoja de contactos agrupada
└── StatusBar   (ui/status_bar.py)   24 px — datos técnicos, aviso, ruta
```

Auxiliares: `ui/segmented.py` (control segmentado), `ui/text.py`
(`ElidedLabel`), `ui/video_widget.py` (`VideoWidget` con mpv + `ScrubBar`).

`ui/room_config_dialog.py` **sigue vivo pero está condenado** — muere en la F3.

### Estado del repo

- Rama `master`, árbol limpio.
- **283 tests pasando.**
- Último commit: `1d33781`.

## 6. Los cuatro candados anti-deriva

Esto es lo que impide que el rediseño se convierta en «el diseño viejo con
funciones a medias». **Aplican a todas las fases, no solo a las que ya
pasaron.**

**Candado 1 — Ningún color, radio o tamaño fuera de `ui/theme.py`.**
Un test lo vigila recorriendo `src/`
(`test_ningun_modulo_declara_colores_fuera_del_tema`). Si necesitas un valor
nuevo, va como token, no pegado al widget.

**Candado 2 — El arnés de comparación.** Ver §7.

**Candado 3 — Ninguna fase cierra con tests verdes: cierra habiendo mirado la
imagen.** Corres el arnés, **abres el PNG y lo miras**, y anotas cada
diferencia contra el mockup como *arreglada* o *intencional y por qué*.
«Se ve bien» no cierra nada.

**Candado 4 — La lista de ejecución.** En el análisis post-F2 (§5) está lo que
todavía debe morir, con su fase asignada. **Una fase no está terminada si su
parte de la lista sigue viva.** Verifícalo con `grep`, no de memoria.

## 7. El arnés de comparación

```bash
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/comp.png
```

Escribe un PNG con el mockup a la izquierda y la app real a la derecha, las dos
a 1600×1000. `--pantalla 1` compara contra el modo hoja.

**Cómo funciona y por qué así:**

- El mockup se rinde con **Chrome sin cabeza**. `QtWebEngine` se probó y se
  descartó: no carga el `file://` del mockup (`loadFinished` llega con
  `ok=False` y `grab()` devuelve 0×0).
- Se inyecta estilo y script en una **copia temporal** del HTML para aislar una
  sola pantalla. **El mockup original nunca se modifica.**
- Ambas imágenes se normalizan a 1600×1000. Sin eso, en Retina la app sale a 2×
  y el mockup a 1×, y la comparación no sirve — pasó en la primera corrida.
- Los datos de ejemplo viven en `scripts/_datos_de_ejemplo.py` y **reproducen
  los mismos números que el mockup** (128 clips, 116 clasificados, 41 picks,
  9 rejects, los mismos cuartos con los mismos conteos). Si los cambias sin
  cuidado, la comparación deja de decir nada.

**Lección de la F2: la vista general no alcanza.** La regresión de las
tarjetas era invisible en la comparación completa y obvia al ampliar un
recorte. Recorta regiones equivalentes de las dos mitades y míralas de cerca.
Un modo de recorte en el arnés está pendiente y sería útil que lo agregues.

## 8. Cómo correr las cosas

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q
```

**`tests/test_app.py` está excluido a propósito**: tiene un cuelgue
preexistente en entornos sin pantalla real, por el `QOpenGLWidget` de video
bajo `offscreen`. No lo persigas, no es un bug a resolver. **Pero mantenlo
actualizado igual**: si lo dejas obsoleto, la próxima persona que lo corra no
va a saber si falla por el cuelgue conocido o porque de verdad se rompió algo.
Ya pasó una vez: afirmaba un color que no existía en `theme.py`.

Para ver la app de verdad, con material real en `sample-media/`:

```bash
.venv/bin/python -m clasificador_video.app
```

## 9. TU PRIMERA TAREA: la F2.1

Cierra una **regresión que introdujo la F2**, no una función pendiente. Está
descrita en detalle en la §2 del análisis post-F2.

### El problema

`ClipCard` (en `ui/clip_sheet.py`) muestra **solo la miniatura**. Perdió:

| Elemento | Estaba en |
|---|---|
| Número de clip (`093`) | mockup |
| Duración (`0:19`) | mockup |
| Glifo de pick/reject (`P` / `X`) | mockup |
| **Barra de rango in/out** | mockup **y en el filmstrip viejo** |
| Franja rayada de «sin clasificar» | mockup |
| Palomita de selección | mockup |

**Dos síntomas confirman que fue descuido y no decisión** — y son el método
que deberías reusar al cerrar cada fase:

1. `ClipThumbnail` carga `in_frame`, `out_frame` y `duration_frames`, y
   `clip_sheet.py` **no lee ninguno de los tres**. `MainWindow._refresh_sheet`
   los sigue calculando y pasando; se tiran en silencio.
2. Los tokens `RANGE_TRACK_COLOR` y `FLAG_NONE_COLOR` quedaron **sin usar en
   todo el proyecto** — eran justo los de la barra de rango y el texto «sin
   marca» de la tarjeta vieja.

### Qué más entra en la F2.1

Cinco diferencias menores contra el mockup, todas detectadas al ampliar
recortes (§3 del análisis):

1. La leyenda del rail (`● 41 picks ● 9 rejects ● 12 sin clasificar`) **se
   desborda** en 200 px. El mockup usa etiquetas cortas: `6 dest. · 41 · 9 · 12`.
2. Los puntos de esa leyenda van **todos grises**; en el mockup llevan el color
   de su estado.
3. El `⏎` de «buscar» va como texto plano; en el mockup va dentro de un keycap.
4. Al encabezado de grupo de la hoja le falta la **línea** que lo separa.
5. Los badges sobre el video juntan cuarto y estado en **una sola etiqueta
   gris**; el mockup tiene dos, cada uno con su color.

Y dos mejoras al arnés: que `_datos_de_ejemplo` pinte un **frame sintético**
detrás del video (hoy el área sale negra y no se puede juzgar el contraste de
los overlays) y que la barra de estado muestre una **ruta de ejemplo**.

### Tres reglas de `ClipSheet` que NO puedes romper

Están escritas en el docstring de la clase. Cada una tiene un bug real detrás:

1. **`item_widgets` va indexado por índice de clip, no por posición visual.**
   `MainWindow._on_thumbnail_ready` entrega las miniaturas con
   `item_widgets[index]`. Reordenar esa lista haría que las miniaturas caigan
   en la tarjeta equivocada, **de forma intermitente**, porque llegan de tres
   hilos en desorden.
2. **Agrupar es re-colocar, jamás reconstruir.** Reconstruir borra los
   `QPixmap` ya cargados, y dentro de un `mousePressEvent` terminó en SIGSEGV
   en macOS. Además: en `_regroup()`, **re-colocar va ANTES de sacar los
   bloques vacíos** — al revés, el bloque que se destruye se lleva puestas las
   tarjetas que todavía cuelgan de él. Hay un comentario que lo dice; me pasó.
3. **Un bloque por grupo, no una `QGridLayout` gigante.**

## 10. Cómo planear las fases que siguen

El proceso que funcionó, y que conviene repetir:

1. **Nunca escribas el plan detallado de más de dos fases por delante.** Todo
   lo posterior se engancha a clases que aún no existen; escribirlo es fabricar
   precisión falsa. Un plan desactualizado tiene autoridad y se sigue en vez de
   pensarlo: es peor que no tenerlo.
2. **Escribe el plan al nivel de los otros planes del repo**: tareas numeradas,
   con el test escrito antes y el código de implementación. Usa
   `2026-08-08-f1-f2-tokens-y-esqueleto.md` como modelo.
3. **Audita el plan antes de implementarlo, ejecutando, no releyendo.** Hice
   tres auditorías: la primera encontró cinco problemas de estructura, la
   segunda cuatro que solo aparecieron al correr código, la tercera uno de
   diseño. **Las tres fallas más graves salieron de ejecutar, nunca de releer.**
   Verifica las APIs de Qt contra Qt, no contra tu memoria.
4. **Cada fase deja la app funcionando.** Puedes partirla en commits —los
   widgets nuevos que nadie usa todavía son commits verdes inofensivos— pero lo
   que ve el usuario cambia en un solo commit.
5. **Al cerrar cada fase**: corre el arnés, mira la imagen, amplía recortes,
   revisa la lista de ejecución con `grep`, y **busca campos de datos que nadie
   lee** — es el mejor detector de funciones perdidas.
6. **Punto de control después de cada dos fases**: rehacer el análisis contra
   el código nuevo y revisar el orden de las fases restantes. Este mismo
   ejercicio ya movió cosas de lugar dos veces.

### Orden vigente

**F2.1** (tu tarea) → **F3** cuartos planos → **F4** deshacer con historial →
**F5** filtros como cola → **F6** reproducción rápida → **F7** resto del
teclado → **F8** modo hoja y pincel → **F9** proxies y orientación del
manifest → **F10** barrido final.

El detalle de cada una está en el plan maestro y en la §6 del análisis post-F2.

## 11. Cosas importantes que tienes que tomar en cuenta

### Decisiones cerradas — no las reabras sin una razón nueva de Bruno

- **mpv se embebe por la API de render** (`vo=libmpv` + `MpvRenderContext`), no
  por `wid`. En macOS `wid` abre una ventana aparte.
- **`hwdec=videotoolbox` fijo**, validado contra HEVC 10-bit real.
- **`QSurfaceFormat` a OpenGL Core 3.3 antes de crear la `QApplication`.**
- **`ScrubBar` usa `QPainter` en `paintEvent`, no QSS dinámico.**
- **El camino `xmeml` está descartado**, no «obsoleto». La vía de entrega es el
  plugin UXP.
- **Se descartaron, con motivo escrito en `DECISIONES.md`**: la forma de onda
  de audio (son recorridos, el audio no informa), el recorte automático de
  in/out, el modo comparar de varios clips en paralelo (decodificar varios
  HEVC 10-bit en sincronía es pedir tartamudeo), y el sistema de cinco
  estrellas (obliga a deliberar en cada clip; en su lugar hay un cuarto estado,
  «destacado»).

### El contrato con Premiere no se toca

`categoria_path` sigue siendo una **lista** aunque los cuartos sean planos —
el plugin ya maneja el caso. Y `"destacado"` es **aditivo**: el plugin mapea
`pick→FOREST`, `reject→ROSE` e **ignora lo que no conoce**. Nada de esto
justifica cambiar `Clip.to_dict()`.

Por la misma razón, el tamaño y la rotación de cada clip viven **en memoria**
(`MainWindow._clip_sizes`, `_clip_rotations`), no en `Clip`.

### Trampas concretas que ya costaron tiempo

- **Los tests también tienen valores escritos a mano.** Once tests rompieron al
  cambiar la paleta porque afirmaban `#3ddc84` en vez de importar
  `PICK_COLOR`. Y uno afirmaba una altura de scrub bar de 34 que el tema fija
  en 26. El candado 1 solo vigila `src/`; los tests son tu responsabilidad.
- **`qtbot.addWidget` no muestra el widget.** Sin `show()` previo,
  `waitExposed` espera para siempre, y sin exponer el layout nunca corre y las
  medidas de geometría dan cualquier cosa.
- **`app.py::_restore_session` toca la ventana por atributos.** Cuando borres
  widgets, revísalo: ya reventó una vez, en el camino de recuperar sesión que
  casi no se prueba a mano y que cubre el test excluido.
- **Los overlays se posicionan con un filtro de eventos sobre el
  `VideoWidget`**, no en el `resizeEvent` del padre: ahí el hijo todavía tiene
  el tamaño anterior.
- **Todo overlay de dibujo propio necesita `WA_TranslucentBackground`.** Sin
  esa bandera pinta fondo opaco donde no dibuja y se come una franja del video.
- **Los botones llevan `setFocusPolicy(Qt.NoFocus)`**, o la tecla Espacio
  activa el botón enfocado en vez de reproducir.
- **La fuente monoespaciada arranca con Menlo.** El mockup encabeza con
  «SF Mono», que no existe con ese nombre en macOS y costaba ~370 ms de
  arranque.

### Convenciones del repo

- **Todo en español mexicano**: chat, commits, docs, comentarios y **sobre todo
  los textos de la app**. Nada de voseo. Está detallado en `CLAUDE.md` y no es
  negociable — ya hubo que corregir strings de UI que se habían colado en
  argentino.
- **Se trabaja directo sobre `master`.** Sin branches ni PRs salvo que Bruno lo
  pida.
- **Higiene de archivos**: nada suelto en la raíz, carpetas nombradas por lo
  que contienen, y **un archivo nuevo que reemplaza a uno viejo se acompaña de
  borrar el viejo en el mismo commit**.
- **Los temporales van al scratchpad de la sesión, nunca al repo.** Ojo:
  Playwright y algunas herramientas escriben en la raíz por default.

### Lo que NO debes hacer

- No agregues funciones que no estén en `DECISIONES.md`. Si se te ocurre algo
  bueno, anótalo y pregúntale a Bruno; no lo metas de contrabando.
- No borres tests en bloque para poner la suite en verde. Clasifica cada uno:
  *se reescribe contra el widget nuevo*, *se borra porque el comportamiento
  murió a propósito*, o *se conserva* — y **ninguno se borra sin escribir en el
  commit por qué murió**.
- No dejes el diseño viejo conviviendo con el nuevo «mientras tanto».
- No cierres una fase sin haber mirado una imagen.

## 12. Cómo arrancar

1. Lee los documentos de la §3, en ese orden.
2. Abre el mockup y míralo entero.
3. Corre los tests y confirma que están en verde (283 al cierre de esta sesión).
4. Corre el arnés y **mira la imagen**, para ver con tus ojos de dónde partes.
5. Escribe el plan detallado de la **F2.1** y de la **F3** —solo esas dos—,
   audítalo ejecutando, y recién entonces implementa.
