# Handoff — Rediseño de la UI, continuar desde la F9 — 2026-08-08

Vas a continuar un rediseño de la interfaz que ya lleva **nueve fases hechas**
(F0, F1, F2, F2.1, F3, F4, F5, F6, F7, F8) y le **quedan dos**, las dos
cortas. **Tu primera tarea es la F9**, que no tiene plan escrito todavía —
empieza por escribirlo, con lo que dice la §5.

Este documento es autosuficiente para arrancar, pero **no reemplaza la lectura
de los documentos que lista la §3**. Léelos antes de escribir código.

Reemplaza a [`archive/HANDOFF-2026-08-08-rediseno-ui-desde-f6.md`](archive/HANDOFF-2026-08-08-rediseno-ui-desde-f6.md).

---

## 1. Qué es el proyecto

Una app de escritorio en **PySide6 + mpv** para que Bruno, editor de video
profesional, clasifique clips de shootings inmobiliarios (recorridos de
propiedades: cocina, recámara, baño, fachada, alberca…) **antes** de editarlos
en Adobe Premiere Pro.

1. **La app** (`src/clasificador_video/`) — importa carpetas de material,
   reproduce cada clip, y el editor le asigna un **cuarto**, lo marca como
   **pick/reject/destacado** y opcionalmente le pone **in/out**. Exporta un
   `manifest.json`.
2. **El plugin UXP** (`uxp-plugin/`) — corre dentro de Premiere, lee ese
   manifest y arma el proyecto solo.

**La razón de existir de la app es la velocidad**: clasificar 128 clips más
rápido de lo que se haría a mano dentro de Premiere. El material real es
**HEVC 10-bit de una Sony FX30**, mayoría **vertical**.

## 2. Qué se puede hacer hoy

Un shooting entero, sin tocar el mouse, en dos vistas:

| Vista | Qué tiene |
|---|---|
| **Clip** | video grande sin franjas negras, autoplay al 25 %, `J K L` de velocidad, `,`/`.` cuadro a cuadro, barra con manijas de in/out, pastilla de rango |
| **Hoja** (`⇥`) | siete columnas, `+`/`−` de tamaño, escrubear la miniatura con el mouse, doble click para abrir |

Clasificar: `1`–`9`, `S` (igual al anterior), la paleta `⏎` para buscar o
crear, `P`/`X`/`⇧P`, el **pincel** (mantener `1`–`9` y arrastrar), la
**marquesina** (arrastrar sin tecla), `⌘Z`, y filtros que además son la cola
de navegación.

**La tabla de teclado de `DECISIONES.md` está completa.** No queda ninguna
tecla prometida sin construir, y hay un test que lo vigila.

## 3. Qué leer, en este orden

| # | Documento | Qué sacar de ahí |
|---|---|---|
| 1 | `CLAUDE.md` (raíz) | Convenciones obligatorias: **español mexicano**, chat breve y sin tecnicismos, commits, higiene de archivos |
| 2 | `docs/superpowers/ANALISIS-2026-08-08-post-f8.md` | **El punto de control vigente**: qué falta, qué enseñó la última fase, y qué revisar antes de la F9 |
| 3 | `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md` | El comportamiento acordado, con el porqué y lo que se descartó |
| 4 | `docs/superpowers/plans/2026-08-08-f8-modo-hoja-y-pincel.md` | El plan más reciente: sirve de molde para el de la F9, y su Task 14 muestra cómo se escribe un spike con criterio numérico |
| 5 | `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md` | El plan maestro: los candados y el método. **Su numeración de fases quedó vieja** — la válida es la de este handoff |
| 6 | `README.md` y `docs/superpowers/CONTEXTO-Y-METAS.md` | Qué es la app y hacia dónde va |

**No leas** `docs/superpowers/archive/` salvo que busques una decisión
histórica concreta.

## 4. Dónde está todo hoy

- Rama `master`, árbol limpio. **704 tests en verde** — ese es el número de
  partida; si al empezar no da 704, averigua qué pasó antes de escribir código.

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

**Sin `--ignore`**: la suite corre completa desde la F5.

### Arquitectura de la UI

```
MainWindow  (ui/main_window.py)   — ensambla y orquesta; TRES filas y ninguna más
├── TitleBar    (ui/title_bar.py)    36 px
├── cuerpo (QHBoxLayout)
│   ├── RoomRail   (ui/room_rail.py)    200 px — progreso, leyenda, fila de `S`, cuartos, historial
│   ├── VideoStage (ui/video_stage.py)  ancho calculado — video + overlays + el pie
│   ├── ToolColumn (ui/tool_column.py)   56 px — rango, estado, deshacer
│   └── ClipSheet  (ui/clip_sheet.py)   resto — buscador, filtros, hoja, pincel, marquesina
├── RoomPalette (ui/room_palette.py)  flota sobre el video con `⏎`
└── StatusBar   (ui/status_bar.py)   24 px
```

Lógica pura, sin Qt y con sus propios tests: `history.py`, `filters.py`,
`rooms.py`, `keyboard.py`, `player.py`.

## 5. Tu primera tarea: la F9 — proxies y orientación

**No tiene plan: escríbelo primero**, con el molde del de la F8. Es la fase
más corta que queda y **no toca la interfaz, son datos**. Tres renglones:

| Qué | Dónde está la pieza |
|---|---|
| La orientación del manifest sale del material, no escrita a mano | `ui/main_window.py`: busca `orientacion="horizontal"`, tiene su `TODO F9` al lado |
| Badge `Proxy 1080p` junto al selector de calidad | `_BadgeRow` en `ui/video_stage.py` ya tiene el hueco |
| Contador `proxies 1080p · 128/128` en la barra de estado | `ui/status_bar.py` |

**Las dos piezas de fondo ya existen y nadie las usa:**

- `probe.py` **ya extrae `width`/`height`/`rotation`**, y la ventana los guarda
  en `_clip_sizes`. Falta que la orientación salga de ahí.
- `proxy_match.py::match_proxies()` **está escrita y nadie la llama**.
  Conectarla a la importación es lo que hace que el badge y el contador digan
  algo real en vez de un número inventado.

**Esa es la trampa de esta fase**: es fácil construir el badge y el contador
antes de conectar los datos, y quedan dos indicadores que mienten. Si los
datos no llegan, **no se construye el indicador** — es la misma regla que hizo
descartar la precarga en la F6.

Después viene la **F10**: el barrido final contra el mockup, el selector
`Clip │ Hoja` de la barra de título, y la transición animada de la tarjeta al
visor.

## 6. Los cuatro candados anti-deriva

**Aplican a todas las fases.** Son la respuesta a la queja de Bruno que ordena
todo este trabajo:

> «Un problema que frecuentemente tengo es que las apps de Claude no quedan
> como los mockups. Quiero que te asegures de que esto vaya a quedar
> visualmente igual que el mockup o incluso mejor, no solo el diseño viejo con
> nuevas funciones a medias y con funciones viejas sin quitar.»

**Candado 1 — Ningún color, radio o tamaño fuera de `ui/theme.py`.** Dos tests
lo vigilan; uno **lee el `:root` del mockup y compara contra el tema**. Salta
de verdad: saltó en la F8 al declarar un alfa en `clip_sheet.py`.

**Candado 2 — El arnés de comparación.** Ver §7.

**Candado 3 — Ninguna fase cierra con tests verdes: cierra habiendo mirado la
imagen.**

**Candado 4 — La lista de ejecución.** Verifícala con `grep`, no de memoria.
Hoy tiene **un solo renglón vivo**: la orientación hardcodeada, que muere en
la F9.

## 7. El arnés de comparación

```bash
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/comp.png
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/hoja.png --pantalla 1
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/rec.png --recorte 200,800,420,160 --zoom 3
```

Mockup a la izquierda, app a la derecha, las dos a 1600×1000. **`--pantalla 1`
compara el modo hoja** — hasta la F8 comparaba la hoja del mockup contra el
modo clip de la app, o sea dos cosas distintas, y no decía nada.
**`--recorte X,Y,ANCHO,ALTO` amplía la misma región de las dos mitades**: la
vista general no alcanza.

Los datos de ejemplo viven en `scripts/_datos_de_ejemplo.py` y **reproducen
los números del mockup**. Cuando construyas algo nuevo, revisa que los datos
lo ejerciten: tres veces pasó que el arnés comparaba una función nueva contra
un panel vacío y no decía nada.

## 8. Cómo encontrar bugs en este proyecto

Lo que funcionó, en orden de rendimiento. **Casi ningún bug de las últimas
cuatro fases lo detectó la suite, y ninguno se ve en una captura general.**

| Detector | Qué encontró |
|---|---|
| **Usar la app con material real** | Que `frame-step` no avanzaba, que el retroceso perdía pulsaciones, que la barra estaba muerta |
| **Perfilar con cProfile** | Tres veces trabajo desperdiciado que nadie sospechaba: `setStyleSheet` 768×/tecla, y miniaturas reescalándose idénticas (40 % de una tecla) |
| **Medir en dos anchos de ventana** | El pie del video encimándose consigo mismo a 1150 px |
| **Comparar el orden real de los eventos** | Etiquetas que no se re-acomodaban: en los arneses siempre hay un `resize` DESPUÉS de los datos, y eso lo tapaba |
| **Señales declaradas contra conectadas** | Un botón muerto por los dos lados |
| **Textos de la app contra atajos registrados** | Cuatro atajos anunciados y ausentes |
| **Estados límite y datos degenerados** | El rango invertido, tres veces: la tarjeta, la barra y la marquesina |
| **Comparar la fase contra lo PROMETIDO** | Que la marquesina faltaba: el plan de la F8 recortó el alcance en silencio |

**Y dos trampas de medición:**
- Contar widgets vivos sin procesar los eventos `DeferredDelete` da **falsos
  positivos de fuga**.
- Un **doble de pruebas puede tapar el bug que existe**: `frame-step` pasaba su
  test *por* la línea que rompía el avance, porque el doble no emulaba que mpv
  pausa solo.

## 9. Trampas concretas que ya costaron tiempo

### De Qt

- **La regla global `QWidget { background-color }` alcanza a las QLabel.**
  Cualquier etiqueta sobre algo pintado tiene que declarar `transparent`. Pasó
  dos veces: el pie del video y la columna de estado, que nunca mostró sus
  cuadros desde la F2.
- **Un `QWidget` puro ignora `background-color` de QSS** sin
  `WA_StyledBackground`.
- **Un `QShortcut` consume la tecla y nunca avisa de que se soltó.** Por eso
  `1`–`9` NO son atajos: con ellos el pincel no se arma, y los tests no lo
  ven, porque un atajo solo se dispara con la ventana **activa**.
- **Un atajo de una tecla le roba lo que escribes a un campo de texto.** Los de
  tecla suelta se desactivan mientras el foco está en uno.
- **`setStyleSheet` es carísimo**: nunca llamarlo si el estilo no cambió.
- **La regla genérica de `QPushButton` trae `padding: 8px 14px`**, y un botón
  chico se ve vacío.
- **Un mínimo de layout se propaga hasta la ventana** y le quita ancho al
  video. El test `test_la_hoja_puede_encogerse_para_dejarle_ancho_al_video` es
  el guardián.
- **Un `FlowLayout` a medida segfaultea en PySide.** Los chips que envuelven se
  acomodan a mano, como las tarjetas.
- **`QColor` no parsea `rgba(...)` de CSS.**
- **`focusInEvent` solo llega con la ventana activa**; bajo `offscreen` nunca.
- **`isVisible()` exige toda la cadena de padres visible**; en tests usar
  `isHidden()`.

### De este proyecto

- **`item_widgets` va por índice de clip, no por posición visual**, y agrupar
  es **re-colocar, jamás reconstruir**. Reconstruir dentro del
  `mousePressEvent` de una tarjeta dio un SIGSEGV.
- **Dos vistas del mismo dato se contradicen solas.** Van cinco veces. El
  arreglo siempre es el mismo: una sola función, y la otra vista la llama.
- **Un test puede fijar una suposición equivocada** y pasar en verde mientras
  la ventana se infla.
- **Medir en la ventana, no en el widget suelto**: el ancho de la hoja nunca es
  el de la ventana.
- **`qtbot.addWidget` no muestra el widget.** Sin `show()` el layout no corre.
- **Los botones llevan `setFocusPolicy(NoFocus)`**, o el espacio activa el
  botón enfocado en vez de reproducir.

## 10. Decisiones cerradas — no las reabras sin una razón nueva de Bruno

### De arquitectura

- **mpv se embebe por la API de render** (`vo=libmpv` + `MpvRenderContext`).
- **`hwdec=videotoolbox` fijo**, validado contra HEVC 10-bit real.
- **`QSurfaceFormat` a OpenGL Core 3.3 antes de crear la `QApplication`.**
- **`ScrubBar` usa `QPainter` en `paintEvent`, no QSS dinámico.**
- **El camino `xmeml` está descartado.** La vía de entrega es el plugin UXP.

### De producto

- **El rail se edita con menú contextual y doble click**, y con `⌘R` sin mouse.
- **La app abre con el rail vacío.**
- **La velocidad va con `J K L`**, la convención de Premiere.
- **`P`, `X` y `⇧P` repetidas vuelven a neutral**, para no tener una tecla de
  neutral aparte.
- **El paso atrás de cuadro va con un seek exacto, no con `frame-back-step`**:
  medido, ese comando pierde pulsaciones a ritmo humano.
- **La precarga del siguiente clip se descartó, medida**: ganaba 70 ms de los
  150 exigidos y hacía subir los cuadros perdidos del video que ves.
- **Los dos iconos de vista del mockup se descartan.**

### El contrato con Premiere no se toca

`categoria_path` sigue siendo una **lista** aunque los cuartos sean planos, y
`"destacado"` es **aditivo**: el plugin mapea `pick→FOREST`, `reject→ROSE`,
`destacado→MANGO` —el dorado, elegido por Bruno— e **ignora lo que no
conoce**. Hasta agosto de 2026 `destacado` NO estaba en esa tabla, así que la
estrella se perdía al cruzar a Premiere.

## 11. Lo que quedó pendiente de verificar a mano

Bruno ya confirmó que **escribir en el buscador de la hoja funciona** (el
texto aparece completo y no dispara nada). Falta:

```bash
.venv/bin/python -m clasificador_video.app
```

1. **Los atajos con modificador** (`⌘Z`, `⌘A`, `⌘E`, `⌘R`) contra el teclado
   físico. Los tests solo comprueban que están registrados; un entorno sin
   ventana activa no recibe pulsaciones reales.
2. **`⏎` con una fila del rail enfocada** debe renombrar, no abrir la paleta.
3. **El pincel y la marquesina con el mouse de verdad**, arrastrando. Están
   probados con eventos sintéticos y en un spike, pero un gesto se juzga
   usándolo.
4. **El indicador «Guardado hace N s»** no se compara nunca: el arnés no
   guarda sesión y su texto sale vacío.

**Y una observación de uso, no un bug**: como `1`–`9` **asigna y avanza**, si
aprietas `1` y luego `P`, el pick cae en el clip **siguiente**.

## 12. Cómo trabajar

- **Español mexicano en todo**: chat, commits, docs, comentarios y **sobre todo
  los textos de la app**. Nada de voseo.
- **En el chat, corto y sin lenguaje técnico.** Bruno es editor de video, no
  programador: qué cambió y qué va a ver él. El detalle técnico va en los
  commits y en los docs.
- **Se trabaja directo sobre `master`.** Sin branches ni PRs salvo que lo pida.
- **Higiene de archivos**: nada suelto en la raíz, y un archivo nuevo que
  reemplaza a uno viejo se acompaña de borrar el viejo en el mismo commit. Los
  temporales van al scratchpad de la sesión.
- **No agregues funciones que no estén en `DECISIONES.md`.**
- **No borres tests en bloque para poner la suite en verde.** Clasifica cada
  uno: *se reescribe*, *murió a propósito*, o *se conserva*.
- **Cada fase deja la app funcionando**, y cierra con: suite verde, los
  detectores de la §8, **cProfile** —encontró algo las tres veces que se
  corrió—, los **dos anchos** (1600 y 1150 px), el arnés en las **dos
  pantallas** mirando la imagen, y una prueba a mano con material real.
- **Audita el plan antes de implementarlo, ejecutando.** Pero cuando ya esté
  auditado, **implementa**: lo que queda por descubrir sale de construir. Los
  cinco planes anteriores terminaron con desvíos que ninguna auditoría podría
  haber previsto.
