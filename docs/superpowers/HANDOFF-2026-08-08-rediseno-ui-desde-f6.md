# Handoff — Rediseño de la UI, continuar desde la F6 — 2026-08-08

Vas a continuar un rediseño completo de la interfaz que ya lleva **siete fases
hechas** (F0, F1, F2, F2.1, F3, F4, F5) y está a mitad de camino.
**Tu primera tarea es implementar la F6**, que ya tiene plan escrito y auditado
cinco veces.

Este documento es autosuficiente para arrancar, pero **no reemplaza la lectura
de los documentos que lista la §3**. Léelos antes de escribir código.

Reemplaza a [`archive/HANDOFF-2026-08-08-rediseno-ui-desde-f2-1.md`](archive/HANDOFF-2026-08-08-rediseno-ui-desde-f2-1.md).

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
la haga más lenta va en contra de su propósito — y eso no es retórica: en esta
sesión una tecla de cuarto pasó de 38 ms a 1.6 ms, y las dos causas eran
trabajo desperdiciado que nadie había medido.

El material real es **HEVC 10-bit de una Sony FX30**, mayoría **vertical**.

## 2. Qué estamos haciendo y por qué

Bruno pidió un rediseño desde cero de la interfaz. El motivo concreto: **el
video vertical se veía chico**, rodeado de franjas negras, y ver el video
grande es *la* razón por la que existe esta app en vez de usar Premiere.

La fuente de verdad visual es
`docs/superpowers/mockups/rediseno-2026-08-08/mockup.html` —tiene las dos
pantallas, clip y hoja— y la del comportamiento es el `DECISIONES.md` que está
a su lado. El material real para probar vive en `sample-media/clips/`.

**La queja de Bruno que ordena todo el trabajo:**

> «Un problema que frecuentemente tengo es que las apps de Claude no quedan
> como los mockups. Quiero que te asegures de que esto vaya a quedar
> visualmente igual que el mockup o incluso mejor, no solo el diseño viejo con
> nuevas funciones a medias y con funciones viejas sin quitar.»

Por eso el plan maestro tiene **cuatro candados anti-deriva** (§6). No son
burocracia: son la respuesta directa a esa queja.

## 3. Qué leer, en este orden

| # | Documento | Qué sacar de ahí |
|---|---|---|
| 1 | `CLAUDE.md` (raíz) | Convenciones obligatorias: **español mexicano**, commits, higiene de archivos, decisiones de arquitectura cerradas |
| 2 | `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md` | **El comportamiento acordado**, con el porqué de cada cosa y lo que se evaluó y descartó |
| 3 | `docs/superpowers/plans/2026-08-08-f6-y-f7-reproduccion-y-teclado.md` | **Tu plan de trabajo.** Tareas numeradas, tests antes que código, y cinco auditorías al final |
| 4 | `docs/superpowers/ANALISIS-2026-08-08-post-f5.md` | El punto de control vigente: qué falta, qué tiene dueño, y las revisiones de la F1 a la F5 |
| 5 | `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md` | El plan maestro: los candados y el porqué del método. **Su numeración de fases quedó vieja — ver el aviso de abajo** |
| 6 | `README.md` y `docs/superpowers/CONTEXTO-Y-METAS.md` | Qué es la app y hacia dónde va |

**No leas** `docs/superpowers/archive/` salvo que busques una decisión
histórica concreta.

### ⚠️ La numeración de fases del plan maestro está vieja

El plan maestro se escribió antes de empezar y **las fases se renumeraron sobre
la marcha**. Ahí adentro «F6» quiere decir *deshacer* (que ya está hecho, y en
esta numeración es la F4) y «F8» quiere decir *reproducción* (que es la F6, la
que vas a hacer). Su lista de ejecución de la §3 también quedó vieja: manda
renglones a fases que ya pasaron.

**La numeración válida es la de este handoff y la del `ANALISIS` post-F5**, que
es el documento más reciente. Del plan maestro, lee los candados y el método —
no los números ni la lista de ejecución.

## 4. Dónde está todo hoy

- Rama `master`, árbol limpio. **476 tests en verde.**
- Último commit: `ce97ae7` (este handoff).
- Fases hechas: **F0** (spike del overlay), **F1** (tokens y arnés), **F2**
  (esqueleto), **F2.1** (tarjetas completas), **F3** (cuartos planos),
  **F4** (deshacer con historial), **F5** (filtros como cola).
- **La lista de ejecución tiene un solo renglón vivo**: `orientacion="horizontal"`
  hardcodeado en `ui/main_window.py`, que muere en la F9.

### La suite corre COMPLETA

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

**Sin `--ignore=tests/test_app.py`.** Ese archivo estuvo excluido meses por un
cuelgue; la F3 lo arregló sin que nadie lo notara —el diálogo que abría con
`exec()` murió con ella— y se comprobó con cinco corridas. Cubre el arranque de
la app, que ningún otro test toca. Si vuelve a colgarse, es un bug a resolver.

### Arquitectura de la UI

```
MainWindow  (ui/main_window.py)   — ensambla y orquesta; TRES filas y ninguna más
├── TitleBar    (ui/title_bar.py)    36 px — proyecto, guardado, Cuartos ⌘R, Exportar ⌘E
├── cuerpo (QHBoxLayout)
│   ├── RoomRail   (ui/room_rail.py)    200 px — progreso, leyenda, cuartos, historial
│   ├── VideoStage (ui/video_stage.py)  ancho calculado — video + overlays
│   ├── ToolColumn (ui/tool_column.py)   56 px — rango, estado, deshacer
│   └── ClipSheet  (ui/clip_sheet.py)   resto — buscador, filtros, hoja agrupada
└── StatusBar   (ui/status_bar.py)   24 px — datos técnicos, aviso clickeable, ruta
```

Lógica pura, sin Qt y con sus propios tests: `history.py` (la pila de deshacer),
`filters.py` (la cola de navegación), `rooms.py`, `keyboard.py`.

## 5. Tu primera tarea: la F6

Está toda en el plan (§3, doc 3). Es **la fase más grande del rediseño**:
catorce renglones. Autoplay, velocidad `J K L`, arranque al 25%, precarga,
`,`/`.` cuadro a cuadro, y **el pie del video entero rehecho** —barra de
reproducción con forma de banda, pastilla de rango, renglón de teclas, contador
de cuadro—.

**Tres cosas que el plan ya resolvió y no hay que volver a investigar:**

1. **mpv acepta todo lo que la F6 necesita.** Verificado contra un HEVC 10-bit
   real: `start = "25%"` funciona (aterriza en 1.5015 s de 6.006 s), `speed` se
   lee y escribe incluso reproduciendo, y `frame-step`/`frame-back-step`
   existen con esos nombres.
2. **La velocidad va con `J K L`**, la convención de Premiere. `L` acelera y
   cicla, `K` frena y pausa, `J` queda reservada.
3. **La precarga se decide con un spike y umbrales fijados de antemano**: gana
   ≥ 150 ms o no se construye, y el `frame-drop-count` del clip que se ve no
   puede subir. Si no cumple, **no se construye y el indicador tampoco**.

**Y una advertencia que costó cara antes:** la Task 4 reescribe
`ScrubBar.paintEvent` entero. El plan trae una tabla de **«lo que no puede
perder»** —riel translúcido, `WA_TranslucentBackground`, seek con mouse, marcas
adaptativas—. Respétala: la barra de rango de las tarjetas «sobrevivió tres
auditorías del plan y murió en la implementación», y se trata del mismo tipo
de widget.

Después de la F6 y la F7 toca **punto de control**: rehacer el análisis contra
el código nuevo antes de planear la F8.

### Lo que viene después — para no construirlo antes de tiempo

Esto **no es trabajo de la F6**. Está aquí para que reconozcas a qué fase
pertenece cada cosa que te encuentres en el mockup, y no la adelantes ni la des
por olvidada. El detalle está en el `ANALISIS` post-F5, §6 y §7.

| Fase | Qué trae |
|---|---|
| **F7 — Resto del teclado** | `S` («igual al anterior») con su fila fija, la paleta `⏎` para buscar y crear cuartos, el estado **destacado** `⇧P` con todas sus caras (badge, indicador, glifo en la tarjeta, chip en la leyenda y en los filtros), `F` para solo video, y que `P`/`X` vuelvan a neutral |
| **F8 — Modo hoja y pincel** | `⇥` para alternar, hoja a pantalla completa, el pincel de cuarto, `+`/`−` para el tamaño de miniatura, marquesina, `esc`, doble click, la barrita al escrubear una miniatura, la barra de selección múltiple y la portada al 25% |
| **F9 — Proxies y orientación** | Aquí muere el `orientacion="horizontal"` hardcodeado, y el badge de proxy muestra datos reales |
| **F10 — Barrido final** | La lista de ejecución vacía, comparación final de las dos pantallas, y toda diferencia contra el mockup arreglada o justificada por escrito |

**Dos cosas con dueño que parecen código muerto y no lo son**:
`theme.STAR_COLOR` (es el destacado de la F7) y los tokens de la hoja completa
(son de la F8). No los borres «limpiando».

## 6. Los cuatro candados anti-deriva

**Aplican a todas las fases.**

**Candado 1 — Ningún color, radio o tamaño fuera de `ui/theme.py`.** Dos tests
lo vigilan: uno recorre `src/` buscando literales, y otro **lee el `:root` del
mockup y compara contra el tema**, para que la fuente de verdad sea el mockup y
no una copia a mano.

**Candado 2 — El arnés de comparación.** Ver §7.

**Candado 3 — Ninguna fase cierra con tests verdes: cierra habiendo mirado la
imagen.** Corres el arnés, **abres el PNG y lo miras**, amplías recortes, y
anotas cada diferencia como *arreglada* o *intencional y por qué*.

**Candado 4 — La lista de ejecución.** Verifícala con `grep`, no de memoria.

## 7. El arnés de comparación

```bash
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/comp.png
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/rec.png --recorte 0,820,205,180 --zoom 4
```

Mockup a la izquierda, app a la derecha, las dos a 1600×1000. `--pantalla 1`
compara contra el modo hoja. **`--recorte X,Y,ANCHO,ALTO` amplía la misma
región de las dos mitades** — la vista general no alcanza: la regresión de las
tarjetas de la F2 era invisible completa y obvia al ampliar.

El mockup se rinde con **Chrome sin cabeza** (QtWebEngine se probó y no carga
el `file://`). Las dos imágenes se normalizan a 1600×1000, o en Retina la app
sale a 2× y la comparación no sirve. Los datos de ejemplo viven en
`scripts/_datos_de_ejemplo.py` y **reproducen los números del mockup**; si los
cambias sin cuidado, la comparación deja de decir nada.

## 8. Cómo encontrar bugs en este proyecto

Lo que funcionó, en orden de rendimiento. **Ninguno de los bugs de esta sesión
lo detectó la suite, y ninguno se ve en una captura.**

| Detector | Qué encontró |
|---|---|
| **Perfilar con cProfile** | `setStyleSheet` llamado 768 veces por tecla: el 84% del tiempo |
| **Señales declaradas contra conectadas** | Un botón de la barra de título muerto por los dos lados desde la F2 |
| **Medir el layout con datos reales** | Un clip horizontal inflaba la ventana de 1600 a 2653 px |
| **Correr los tests del plan antes de implementar** | Cinco tests que fallaban por un helper inexistente, no por la función que faltaba |
| **Textos de la app contra atajos registrados** | `⌘Z`, `⌘A`, `⌘E` y `⌘R` anunciados y ausentes |
| **Campos y métodos que nadie lee** | Los tokens huérfanos que delataron la regresión de las tarjetas |
| **Estados límite y datos degenerados** | El rango invertido cuando marcas `O` antes que `I` |

**Y una trampa de medición:** contar widgets vivos sin procesar los eventos
`DeferredDelete` da falsos positivos de fuga. Reporté una fuga que no existía;
hay que llamar a `sendPostedEvents(None, QEvent.DeferredDelete)` antes de
contar.

## 9. Trampas concretas que ya costaron tiempo

### De Qt

- **`setStyleSheet` es carísimo.** Vuelve a parsear la hoja y repolish el
  widget. Nunca llamarlo si el estilo no cambió — la `ClipCard` compara antes.
- **La regla genérica de `QPushButton` trae `padding: 8px 14px`.** Un botón
  chico lo hereda, su `sizeHint` se va a 38×29 y **el glifo se recorta entero**:
  el botón se ve vacío. Pasó con el `↺` del historial.
- **Un mínimo de layout se propaga hasta la ventana.** El `QScrollArea` de la
  hoja subía el mínimo de las tarjetas al ancho de la ventana: podía crecer y
  nunca encoger. Se arregla con `QSizePolicy.Ignored` en horizontal.
- **`_content.width()` no es el ancho disponible**: su mínimo lo fijan las
  propias tarjetas. Para acomodar hay que medir `_scroll.viewport().width()`.
- **El `border-radius` de un contenedor NO recorta a sus hijos.**
- **Esconder un widget no lo saca de un `QGridLayout`**: queda el hueco. Hay
  que re-colocar salteando los escondidos.
- **`focusInEvent` solo llega con la ventana activa**, así que bajo `offscreen`
  nunca se entrega. Para marcar el foco, usar el pseudo-estado `:focus` de QSS.
- **`isVisible()` exige que toda la cadena de padres esté visible.** En tests
  sin `show()`, el predicado correcto es `isHidden()`.
- **`QColor` no parsea `rgba(...)` de CSS.** Los tokens con alfa se guardan
  como tuplas y se arman con `QColor(*token)`.
- **Un `QShortcut` normal se dispara con cualquier foco de la ventana**
  (`WindowShortcut`). Ojo con `⏎`, que el rail ya usa para renombrar.
- **`QSizePolicy` de un `QButtonGroup` exclusivo**: reclickear el chip activo
  **no** lo apaga. Por eso cada grupo de filtros tiene su chip `Todos`.
- **Un `FlowLayout` a medida segfaultea en PySide** por la propiedad de los
  `QLayoutItem`. No reintentarlo sin saberlo.

### De este proyecto

- **`item_widgets` de `ClipSheet` va por índice de clip, no por posición
  visual**, y agrupar es **re-colocar, jamás reconstruir**. Las tres reglas
  están en el docstring de la clase y cada una tiene un bug real detrás.
- **Los tests también tienen valores escritos a mano**, y **un test puede fijar
  una suposición equivocada**: el de la F2 afirmaba que el video mide
  `ancho − rail − columna − SHEET_MIN_WIDTH`, que era justo la cuenta mal hecha.
  Pasaba en verde mientras la ventana se inflaba.
- **`qtbot.addWidget` no muestra el widget.** Sin `show()` el layout no corre.
- **Todo overlay de dibujo propio necesita `WA_TranslucentBackground`.**
- **Los botones llevan `setFocusPolicy(Qt.NoFocus)`**, o el espacio activa el
  botón enfocado en vez de reproducir.
- **La fuente monoespaciada arranca con Menlo**: «SF Mono» no existe con ese
  nombre en macOS y costaba ~370 ms de arranque.

## 10. Decisiones cerradas — no las reabras sin una razón nueva de Bruno

### De arquitectura

- **mpv se embebe por la API de render** (`vo=libmpv` + `MpvRenderContext`), no
  por `wid`. En macOS `wid` abre una ventana aparte.
- **`hwdec=videotoolbox` fijo**, validado contra HEVC 10-bit real.
- **`QSurfaceFormat` a OpenGL Core 3.3 antes de crear la `QApplication`.**
- **`ScrubBar` usa `QPainter` en `paintEvent`, no QSS dinámico.**
- **El camino `xmeml` está descartado.** La vía de entrega es el plugin UXP.

### De producto, tomadas con Bruno en esta sesión

- **El rail se edita con menú contextual y doble click**, no arrastrando. Y con
  `⌘R` sin mouse: `↑`/`↓` mueven el foco, `⌥↑`/`⌥↓` reordenan, `⏎` renombra,
  `⌫` elimina.
- **La app abre con el rail vacío.** Los cuartos se crean sobre la marcha.
- **La tecla `U` se queda** (borra el in/out) y está escrita en la tabla de
  teclado.
- **La velocidad va con `J K L`**, la convención de Premiere: Bruno ya la tiene
  en los dedos, y eso vale más que cualquier atajo «más lógico».
- **Los dos iconos de vista del mockup se descartan**: no hay ninguna decisión
  detrás de ellos.

### El contrato con Premiere no se toca

`categoria_path` sigue siendo una **lista** aunque los cuartos sean planos. Y
`"destacado"` (F7) es **aditivo**: el plugin mapea `pick→FOREST`,
`reject→ROSE` e **ignora lo que no conoce**. Nada de esto justifica cambiar
`Clip.to_dict()`.

## 11. Lo que quedó pendiente de verificar a mano

**Bruno tiene que probar en su Mac que los atajos con modificador responden a
la tecla física**: `⌘Z`, `⌘A`, `⌘E` y `⌘R`. Los tests solo comprueban que
están registrados; un entorno sin pantalla no recibe pulsaciones reales.

```bash
.venv/bin/python -m clasificador_video.app
```

**Y una observación de uso, no un bug**: como `1`–`9` **asigna y avanza**, si
aprietas `1` y luego `P`, el pick cae en el clip **siguiente**. El orden
natural es al revés —miras, marcas `P`, y asignas el cuarto, que te lleva al
que sigue—. Si al usarlo le resulta incómodo, se cambia.

## 12. Cómo trabajar

- **Español mexicano en todo**: chat, commits, docs, comentarios y **sobre todo
  los textos de la app**. Nada de voseo. Está en `CLAUDE.md` y no es negociable.
- **En el chat, escribe corto y sin lenguaje técnico.** Bruno es editor de
  video, no programador: no quiere leer nombres de clases, métodos, atributos ni
  explicaciones largas de cómo funciona Qt por dentro. Resume en pocas líneas
  **qué cambió y qué va a ver él**, en palabras normales. El detalle técnico va
  en los docs y en los commits, que es donde sirve — no en la conversación.
- **Se trabaja directo sobre `master`.** Sin branches ni PRs salvo que Bruno lo
  pida.
- **Higiene de archivos**: nada suelto en la raíz, y **un archivo nuevo que
  reemplaza a uno viejo se acompaña de borrar el viejo en el mismo commit**.
  Los temporales van al scratchpad de la sesión, nunca al repo.
- **No agregues funciones que no estén en `DECISIONES.md`.** Si se te ocurre
  algo bueno, anótalo y pregúntale a Bruno.
- **No borres tests en bloque para poner la suite en verde.** Clasifica cada
  uno: *se reescribe*, *murió a propósito*, o *se conserva* — y ninguno se
  borra sin escribir en el commit por qué murió.
- **Cada fase deja la app funcionando.** Puedes partirla en commits, pero lo
  que ve el usuario cambia en uno solo.
- **Audita el plan antes de implementarlo, ejecutando.** Y cuando el plan ya
  esté auditado —como el de la F6, cinco veces—, **implementa**: lo que queda
  por descubrir sale de construir, no de leer. Los tres planes anteriores
  terminaron con una sección «lo que se desvió», y ninguno de esos desvíos se
  podría haber previsto auditando.
