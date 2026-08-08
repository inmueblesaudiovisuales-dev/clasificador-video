# Instrucciones para Claude Code en este repo

## Idioma: español mexicano, siempre

**Toda la conversación va en español mexicano.** No en español de España ni
sudamericano. Esto aplica a todo lo que se escriba en este proyecto, sin
excepción:

- las respuestas en el chat,
- los mensajes de commit,
- la documentación en `docs/`,
- los comentarios en el código,
- **y sobre todo los textos que ve el usuario dentro de la app** (botones,
  etiquetas, mensajes de error, tooltips), que son los que terminan
  publicados.

En concreto:

- **Usa `tú`, nunca `vos`.** Se dice "arrastra", "mantén presionada",
  "suelta", "puedes", "tienes", "selecciona" — no "arrastrá", "mantené",
  "soltá", "podés", "tenés", "seleccioná".
- **`aquí`, no `acá`.** `computadora`, no `ordenador`. `video`, no `vídeo`.
  `jalar`/`arrastrar`, no `coger`.
- Nada de `che`, `pibe`, `laburo`, `ahorita no` con sentido rioplatense, ni
  otros marcadores regionales de Argentina/Uruguay/España.
- Los términos técnicos que en la industria se usan en inglés se dejan en
  inglés (`pick`, `reject`, `render`, `proxy`, `frame`, `timecode`), porque
  así los usa un editor de video en México. No traducirlos a la fuerza.

Si un texto ya existente en el repo está en otra variante, corregirlo cuando
se toque el archivo.

## En el chat: breve y sin lenguaje técnico

Bruno es editor de video, no programador. **Las respuestas en la conversación
van cortas y en palabras normales**: qué cambió y qué va a ver él al usar la
app. Nada de nombres de clases, métodos o atributos, ni explicaciones de cómo
funciona Qt por dentro, ni muros de texto con todo el razonamiento.

El detalle técnico sí se escribe — pero en los commits, en `docs/` y en los
comentarios del código, que es donde sirve. En el chat, no.

## Flujo de trabajo

- **Sin branches nuevas**: Bruno pidió explícitamente trabajar directo sobre
  `master`. No crear branches ni proponer PRs a menos que lo pida.
- **Commits**: mensajes en español mexicano, un commit por unidad de trabajo
  lógica, terminan con `Co-Authored-By: <modelo> <noreply@anthropic.com>`,
  donde `<modelo>` es el que realmente hizo el trabajo (`Claude Opus 5`,
  `Claude Sonnet 5`, etc.). No dejarlo fijo en un modelo: la atribución tiene
  que ser real.
- **Tests** — la suite corre **completa**:
  ```bash
  QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
  ```
  Hasta agosto de 2026 esto llevaba `--ignore=tests/test_app.py`, porque ese
  archivo colgaba bajo `offscreen`. **Ya no cuelga**: la F3 lo reescribió —el
  diálogo de configuración que abría con `exec()` murió con ella— y desde
  entonces corre en medio segundo. Comprobado con cinco corridas completas el
  2026-08-08. Si alguna vez vuelve a colgarse, es un bug a resolver, no una
  limitación a esquivar.
- **Verificación visual real, no solo tests**: nunca afirmar que algo se ve
  bien sin haber visto el pixel. El medio depende del artefacto:
  - **Widget de PySide6** — construir una `MainWindow`/widget de prueba, usar
    `grab()`, guardar el PNG y leerlo con la herramienta de lectura de
    archivos.
  - **Mockup o documento HTML** — servirlo (`python3 -m http.server` sobre su
    carpeta), abrirlo con una herramienta de navegador, sacar captura y
    leerla.

  En los dos casos vale la misma regla: si no se miró la imagen, no se
  afirma. Y los archivos temporales de esa verificación van al scratchpad de
  la sesión, nunca al repo.
- **Brainstorm antes de features nuevas o cambios visuales** — este proyecto
  usa el flujo de `superpowers:brainstorming` → spec en
  `docs/superpowers/specs/` → plan en `docs/superpowers/plans/` →
  implementación con TDD. Los specs y planes de sesiones anteriores son la
  fuente de verdad de decisiones ya tomadas — revisarlos antes de asumir.

  **Excepción**: si ya existe un brief o spec escrito que cubre el trabajo
  pedido, ese documento *es* el resultado del brainstorm y no hace falta
  repetirlo (por ejemplo `PROMPT-REDISENO-2026-08-08.md`, que originó el
  rediseño de la UI). Rehacer el brainstorm cuando los requisitos ya están
  por escrito solo le hace perder tiempo a Bruno.

## Decisiones de arquitectura ya tomadas (no las reabras sin razón nueva)

- **`ScrubBar` usa `QPainter` custom en `paintEvent`, no QSS dinámico.** QSS
  aplicado por-widget en elementos que se repintan seguido (scrub bar con
  playhead animado) es un antipatrón de performance en Qt — decisión
  deliberada, ver `docs/superpowers/archive/HANDOFF-2026-08-06-arreglar-video-y-diseno.md`.
- **Separación de color por canal semántico** (`src/clasificador_video/ui/theme.py`):
  - `PICK_COLOR`/`REJECT_COLOR`/`CURRENT_COLOR` — estado del clip. Nunca se
    reusan para identidad de cuarto.
  - `ROOM_PALETTE` — identidad de cuarto, paleta apagada a propósito para no
    competir visualmente con los colores de estado.
  - `TRIM_COLOR` — rango in/out marcado. Separado de `ACCENT` (playhead/clip
    actual) para que un thumbnail con ambos no confunda las dos cosas.
- **mpv se embebe vía API de render (`vo=libmpv` + `MpvRenderContext`), no
  `wid`.** En macOS con el backend gráfico actual de mpv, `wid` no es
  confiable — mpv abre su propia ventana en vez de dibujar en el widget.
- **`hwdec=videotoolbox` fijo** — validado en vivo contra HEVC 10-bit real de
  la Sony FX30.
- **`QSurfaceFormat` a OpenGL Core 3.3 antes de crear la `QApplication`** —
  mpv necesita Core >= 3.3; el perfil de compatibilidad default de Qt en
  macOS no alcanza (`ui/app.py::configure_gl_surface_format`).
- **El enfoque `xmeml` (Final Cut Pro 7 XML) está descartado**, no solo
  "obsoleto" — Premiere nunca abre el archivo de video real al importar un
  xmeml, y ese formato no puede declarar rotación. La vía real de entrega es
  el plugin UXP en `uxp-plugin/` vía `project.importFiles()`. No reintentar
  el camino xmeml sin una razón nueva y explícita de Bruno.

## Higiene de archivos — prioridad, no un paso opcional al final

Bruno le da valor real a que el repo se mantenga ordenado (ver la sesión de
limpieza de agosto 2026: se borró código muerto, spikes sueltos, se
renombró `TEST/` → `sample-media/`, se archivaron 13 handoffs históricos a
`docs/superpowers/archive/`, se unificaron dependencias). Esto no es una
tarea aparte — es un criterio a aplicar **cada vez que se crea algo nuevo**:

- **Nunca dejar archivos sueltos en la raíz del repo.** Todo archivo nuevo
  tiene una carpeta lógica a la que pertenece (`src/`, `tests/`, `docs/`,
  `scripts/`, etc.) — si no la tiene, es señal de que hace falta crear una
  carpeta con nombre descriptivo antes de escribir el archivo, no después.
- **Nombra las carpetas por lo que contienen**, no genérico (`output/`,
  `stuff/`, `tmp/`). Un mockup de rediseño va en algo como
  `docs/superpowers/mockups/rediseno-<fecha>/`, no en la raíz ni en un
  nombre ambiguo.
- **No dejar código, docs o scripts de "prueba puntual"/spike sin marcar
  como tal.** Si algo es un experimento descartable, dilo en el nombre o
  en un comentario al tope del archivo — así la próxima limpieza lo
  identifica sin tener que investigar si todavía se usa.
- **Un archivo nuevo reemplaza a uno viejo → borrar el viejo en el mismo
  commit**, no dejarlo "por las dudas". Git ya guarda el historial.
- **Antes de terminar una tarea que generó archivos nuevos**, repasar con
  `git status` que todo lo agregado tiene un lugar que tiene sentido, no
  solo que "funciona".

## Convenciones de nombres

- `TEST/` (mayúsculas) fue renombrado a `sample-media/` — evitar recrear una
  carpeta en mayúsculas para datos de prueba, colisiona en filesystems
  case-insensitive con `tests/`.
- Módulos de `src/clasificador_video/` son 1:1 con `tests/test_<módulo>.py`.
  Los widgets de PySide6 viven en `src/clasificador_video/ui/` y sus tests en
  `tests/ui/`.

## Contexto del producto

Ver `README.md` para qué es la app y cómo correrla, y
`docs/superpowers/CONTEXTO-Y-METAS.md` para el estado actual del proyecto y
hacia dónde va.

## Dirección de diseño de la UI

Antes de tocar cualquier cosa en `src/clasificador_video/ui/`, leer
`docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`. Es la dirección
de diseño acordada con Bruno y explica el porqué de cada decisión, incluidas
las que ya se evaluaron y se descartaron (forma de onda de audio, recorte
automático de in/out, modo comparar de varios clips en paralelo, sistema de 5
estrellas). No reabrirlas sin una razón nueva.

Lo que no está construido todavía no es una invitación a improvisar otra
cosa: si el mockup no cubre un caso, vale la pena preguntarle a Bruno antes
de inventar.
