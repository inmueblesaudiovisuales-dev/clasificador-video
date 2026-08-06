# Informe — Crash SIGSEGV al importar/clickear miniaturas — 2026-08-06

Entrada: `docs/superpowers/HANDOFF-2026-08-06-crash-al-importar.md`.

## Resumen ejecutivo

La hipótesis del handoff (sección 2) quedó **confirmada con evidencia**:
click izquierdo sobre una miniatura del filmstrip disparaba, dentro del
propio `mousePressEvent` del widget clickeado, una reconstrucción
completa del filmstrip (`Filmstrip.set_clips` hace `setParent(None)` y
reemplaza a todos los `_ClipItemWidget`). En el run loop nativo de
cocoa Qt aún referencia al widget internamente en `sendMouseEvent` al
volver del despacho anidado, terminando en
`EXC_BAD_ACCESS (SIGSEGV) — KERN_INVALID_ADDRESS at 0x000000000000000c`
(matches exactos con los dos crash reports reales de Bruno, 09:35:19 y
09:35:56). El fix elimina la reconstrucción: `select_clip` ahora solo
llama a `filmstrip.set_current` (cambia el borde azul sin destruir
widgets). De yapa arregla un segundo bug real confirmado en la misma
cadena (`_refresh_filmstrip` recreaba los widgets con
`thumbnail_path=None`, borrando todos los pixmaps ya cargados por los
`_ThumbnailJob`).

## Bugs encontrados y corregidos en esta sesión

| # | Síntoma | Causa | Archivo:línea | Fix |
|---|---|---|---|---|
| 1 | SIGSEGV (KERN_INVALID_ADDRESS 0xc) en pocos segundos al hacer click en una miniatura del filmstrip después de importar (crashes nativos reales 09:35:19 y 09:35:56 en `~/Library/Logs/DiagnosticReports/`) | `select_clip` llamaba a `_refresh_filmstrip` → `Filmstrip.set_clips`, que destruye y reemplaza a TODOS los `_ClipItemWidget` (incluido el clickeado) **mientras** Qt todavía despacha el `mousePressEvent` de ese widget (`sendMouseEvent` anidado) | `src/clasificador_video/ui/main_window.py:341` (`select_clip`) | `select_clip` ya no reconstruye el filmstrip: solo llama a `filmstrip.set_current(current_index)` (borde azul). La selección no altera datos de ningún clip, así que la reconstrucción era innecesaria. Confirmado vía TDD: `tests/ui/test_main_window.py::test_click_real_en_thumbnail_no_crasha_al_reconstruir_filmstrip`. Ver también `commits 541b4fe, 0d20b11, 6cb8ba6`. |
| 2 (de yapa, mismo fix) | Click en una miniatura borraba TODOS los pixmaps del filmstrip ya cargados en background | `_refresh_filmstrip` recrea los widgets con `thumbnail_path=None`, sin preservar los `set_pixmap` hechos por los `_ThumbnailJob` posteriores a la importación | `src/clasificador_video/ui/main_window.py:341` | El mismo fix del bug #1 (no recrear widgets en `select_clip`) preserva los pixmaps. Aserción explícita en el test nuevo (`widths_despues == pixmap_widths`). |

Otros dos arreglos del handoff se confirmaron **no relacionados** con el
crash y se commitearon por separado (ver sección siguiente):
restaurar sesión que no programaba miniaturas, y `RuntimeError` del job
de miniatura al emitir sobre una señal ya destruida.

## Causa raíz real (confirmada, no hipótesis)

- La cadena **existe** en el código: verificado en código y con
  ejecución instrumentada — tras `QTest.mouseClick` sobre
  `window.filmstrip.item_widgets[2]`, los `id()` de los tres widgets
  **cambiaron** (reconstrucción real, no teórica). Eso es la
  condición previa exacta que produce el SIGSEGV en el QPA nativo de
  cocoa.
- No es el QThreadPool/`_ThumbnailJob` (sospechoso secundario del
  handoff §3.2 punto 3): confirmado distinto — ese hilo emite señales
  tarde contra ventanas destruidas (path distinto); su `try/except
  RuntimeError` se mantiene válido pero es ortogonal. Fix commiteado
  aparte.
- No es `app.py` restore-sesión (handoff §3.2 punto 1): ese path corre
  solo al arranque, no durante clicks. Fix commiteado aparte.

## Fix aplicado (commits, orden cronológico, uno por bug)

1. `541b4fe` `fix: restaurar sesion guardada tambien programa miniaturas`
   — `src/clasificador_video/app.py:85` + test en `tests/test_app.py`.
2. `0d20b11` `fix: job de miniatura no propaga RuntimeError si su senal ya fue destruida`
   — `src/clasificador_video/ui/main_window.py:70` (`_ThumbnailJob.run`)
   + test en `tests/ui/test_main_window.py`.
3. `6cb8ba6` `feat: filmstrip clickeable y fix de crash SIGSEGV al seleccionar`
   — `src/clasificador_video/ui/filmstrip.py` (señal `clicked` +
   `clip_clicked`, cursor mano, `mousePressEvent`),
   `src/clasificador_video/ui/main_window.py` (`clip_clicked.connect` +
   `select_clip` sin reconstruir) + tests en
   `tests/ui/test_filmstrip.py` y `tests/ui/test_main_window.py`.

## Estado de los cambios sin commitear del handoff §3.2

- (punto 1) `app.py` `_schedule_thumbnails` en `_restore_session` — **se mantuvo**, commiteado en `541b4fe`.
- (punto 2) `filmstrip.py` + `main_window.py` filmstrip clickeable — **se mantuvo** (es la feature pedida), pero **se modificó** `select_clip` para que no reconstruya el filmstrip (fix del crash). Commiteado en `6cb8ba6`.
- (punto 3) `main_window.py` `_ThumbnailJob.run` `try/except RuntimeError` — **se mantuvo** sin cambios. Commiteado en `0d20b11`.

Ningún cambio de la sesión previa se revirtió: confirmados los tres
como fixes reales de bugs reales. Solo se corrigió el bug de la
feature (punto 2) añadida en esa misma sesión.

## Evidencia de verificación

- **Reproducción del patron del crash**: test TDD
  `test_click_real_en_thumbnail_no_crasha_al_reconstruir_filmstrip`
  FALLA en rojo antes del fix (los `id()` cambian tras el click →
  reconstrucción dentro del `mousePressEvent` — la condición previa
  exacta del SIGSEGV) y PASA en verde tras el fix (mismos `id()`,
  pixmaps preservados).
- **Nota honesta sobre limitación del entorno**: el QPA `offscreen` de
  los tests no pasa por `processMouseEvent`/`sendMouseEvent` anidado
  de cocoa, así que no reproduce el `SIGSEGV` nativo pixel-a-pixel. La
  verificación se hace sobre la **propiedad estructural que lo
  imposibilita** (no destrucción de widgets durante su propio
  `mousePressEvent`).
- **Repetición del patrón**: harness ad-hoc `stress_crash.py` (en
  `/var/folders/.../T/opencode/`) corrió 30 iteraciones × 6 clicks
  reales cada una (= 180 clicks sobre miniaturas con miniaturas ya
  cargadas, clickeando items distintos), `failures=0`, el proceso no
  murió.
- **DiagnosticReports limpio**: el reporte más nuevo de `Python` sigue
  siendo `Python-2026-08-06-093556.ips` (de Bruno, antes de empezar).
  Ninguno nuevo durante la verificación (ventana 10:13:27 → 10:14:02).
- **Suite completa**: 158/158 (`157` original + `1` test nuevo del
  crash) en **3 corridas seguidas**, sin fallos ni crashes:
  - corrida 1: 158 passed in 0.97s
  - corrida 2: 158 passed in 0.97s
  - corrida 3: 158 passed in 0.96s
- **Aislamiento de cada commit por bug**: se verificó que el test de
  cada fix pasa contra el árbol que tiene solo ese fix staged (sin
  los demás), vía `git stash --keep-index`.

## Hallazgos adicionales (no resueltos, fuera de scope de este crash)

- **Higiene de tests**: `tests/test_app.py::test_arrancar_abre_dialogo_y_
  construye_ventana_con_cuartos_elegidos` cuelga el proceso si
  `~/.clasificador_video/sesion.json` existe (Bruno lo tiene ahora con
  3 clips) porque `_restore_session` abre un `QMessageBox.question`
  modal que en QPA headless bloquea forever. No es un bug de la app
  (es comportamiento esperado al restaurar), pero sí del fixture de
  tests. Workaround durante esta sesión: `HOME=/tmp/fakehome_NOSES`.
  Recomendación: en `arrancar` del test o en conftest, aislar `HOME`
  o mockear el dialogo de "recuperar sesion". No se tocó aquí porque
  no estaba en scope del crash; reportar para un TDD cycle aparte.
- **Bug de UX no resuelto**: `_refresh_filmstrip` reconstruye los
  widgets con `thumbnail_path=None` en **cada** tecla que cambia el
  clip actual (`i`, `o`, `u`, teclas de cuarto, pick/reject, flechas
  usan `_refresh_filmstrip` o `handle_arrow`...). Marcar un clip con
  `p` (pick) **borra todas las miniaturas ya cargadas**. No es
  crash (las teclas se despachan a la ventana principal, no a un item
  del filmstrip), pero es un bug real de UX separado, mismo
  mecanismo. Se deja para un commit de fix aparte (no mezclar bugs).
- **Bug menor en producción**: `_ClipItemWidget.has_pixmap` está roto
  — en PySide6 `QLabel.pixmap()` retorna un `QPixmap(null)` (no
  `None`) para un label sin pixmap, así que `pixmap() is not None` es
  siempre `True`. El método reporta tener pixmap cuando no lo tiene.
  Hoy no hay call-site de `has_pixmap` que dependa de eso para
  comportamiento crítico, pero conviene arreglar (`pixmap().isNull()`
  o `width() > 0`). Detectado durante la depuración del test TDD;
  aparte.

## Archivos tocados en esta sesión

```
src/clasificador_video/app.py                  |  1 +
src/clasificador_video/ui/filmstrip.py         | 15 +++--
src/clasificador_video/ui/main_window.py      | 32 +++++++--
tests/test_app.py                              | 20 +++++
tests/ui/test_filmstrip.py                     | 20 +++++
tests/ui/test_main_window.py                   | 107 +++++++++++++++++++
docs/superpowers/INFORME-2026-08-06-crash-al-importar.md (este archivo)
```