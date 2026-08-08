# Instrucciones para Claude Code en este repo

## Flujo de trabajo

- **Sin branches nuevas**: Bruno pidió explícitamente trabajar directo sobre
  `master`. No crear branches ni proponer PRs a menos que lo pida.
- **Commits**: mensajes en español, un commit por unidad de trabajo lógica,
  terminan con `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
- **Tests**:
  ```bash
  QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q
  ```
  `tests/test_app.py` tiene un cuelgue preexistente en entornos sin pantalla
  real (limitación del `QOpenGLWidget` de video bajo `offscreen`, confirmada
  en varias sesiones) — no perseguirlo, no es un bug a resolver.
- **Verificación visual real, no solo tests**: para cambios de UI, construir
  una `MainWindow`/widget de prueba, usar `grab()`, guardar el PNG, y leerlo
  con la herramienta de lectura de archivos antes de afirmar que algo se ve
  bien. Patrón ya usado en varias sesiones (ver scripts temporales en el
  historial de `docs/superpowers/plans/`).
- **Brainstorm antes de features nuevas o cambios visuales** — este proyecto
  usa el flujo de `superpowers:brainstorming` → spec en
  `docs/superpowers/specs/` → plan en `docs/superpowers/plans/` →
  implementación con TDD. Los specs y planes de sesiones anteriores son la
  fuente de verdad de decisiones ya tomadas — revisarlos antes de asumir.

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
- **Nombrá las carpetas por lo que contienen**, no genérico (`output/`,
  `stuff/`, `tmp/`). Un mockup de rediseño va en algo como
  `docs/superpowers/mockups/rediseno-<fecha>/`, no en la raíz ni en un
  nombre ambiguo.
- **No dejar código, docs o scripts de "prueba puntual"/spike sin marcar
  como tal.** Si algo es un experimento descartable, decilo en el nombre o
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
