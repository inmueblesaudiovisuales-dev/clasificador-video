# Handoff — Auditoría de crash real al importar/clasificar — 2026-08-06 tarde

## 0. Contexto para la IA que reciba esto

Bruno reportó: **la app se crashea en pocos segundos al importar carpetas o cargar clips.** Esto pasó probando la app de verdad, no en tests (la suite automatizada pasa 157/157, cinco corridas seguidas, sin fallos — ver sección 4). Es un bug real de uso, no cubierto por los tests actuales.

**Impotante — el estado del repo NO es solo el último commit.** Hay cambios sin commitear en el working tree (ver `git status` / `git diff`) hechos en esta misma sesión, minutos antes del crash reportado. Es muy probable que el crash venga de ahí — no lo descartes, pero tampoco lo asumas a ciegas: confírmalo reproduciendo con y sin esos cambios (sección 3).

No pidas permiso para investigar, reproducir, escribir tests, corregir código ni commitear fixes reales (TDD: test que falla → fix → test que pasa → commit, un commit por bug, mensajes en español). Si necesitas revertir el trabajo sin commitear porque resulta ser la causa y no lo puedes arreglar rápido, coméntalo en el informe final en vez de descartarlo en silencio — es trabajo real que resolvió otros dos bugs reales (sección 3.2).

## 1. Evidencia ya recolectada — no la vuelvas a buscar, arranca de aquí

Bruno probó la app por su cuenta en Terminal (`cd "ORGANIZADOR VIDEO" && .venv/bin/python -m clasificador_video.app`) y crasheó dos veces seguidas en menos de dos minutos. macOS generó reportes de crash reales:

- `~/Library/Logs/DiagnosticReports/Python-2026-08-06-093519.ips`
- `~/Library/Logs/DiagnosticReports/Python-2026-08-06-093556.ips`

Ambos, **idénticos en tipo y ubicación**:

```
exception: EXC_BAD_ACCESS (SIGSEGV) — KERN_INVALID_ADDRESS at 0x000000000000000c
faultingThread: 0 (com.apple.main-thread)
```

Stack del hilo que truena (top del segundo crash, `093556`, el más completo):

```
QtWidgets QApplication::notify(QObject*, QEvent*)
QtWidgets QApplication::notify(QObject*, QEvent*)
QtWidgets.abi3.so QApplicationWrapper::notify(QObject*, QEvent*)
QtCore QCoreApplication::sendSpontaneousEvent(QObject*, QEvent*)
QtWidgets QApplicationPrivate::sendMouseEvent(QWidget*, QMouseEvent*, QWidget*, QWidget*, QWidget**, QPointer<QWidget>&, bool, bool)
QtWidgets  (frame interno, sin símbolo)
QtWidgets  (frame interno, sin símbolo)
QtWidgets QApplicationPrivate::notify_helper(QObject*, QEvent*)
QtWidgets QApplication::notify(QObject*, QEvent*)
... (mismo patrón notify/sendSpontaneousEvent otra vez, es un evento anidado)
QtGui QGuiApplicationPrivate::processMouseEvent(...)
QtGui QWindowSystemInterface::sendWindowSystemEvents(...)
libqcocoa.dylib
CoreFoundation __CFRUNLOOP_IS_CALLING_OUT_TO_A_SOURCE0_PERFORM_FUNCTION__
... (run loop de Cocoa/AppKit hasta el arranque de QCoreApplication::exec())
```

**Lectura de esto:** dirección `0xc` es prácticamente un null-pointer-plus-offset — típico de invocar un método virtual sobre un objeto C++ (QWidget) ya destruido o inválido. Pasa **dentro del despacho de un evento de mouse** (`sendMouseEvent`), en el hilo principal, con eventos anidados (un `notify` dentro de otro `notify` — algo disparó un segundo evento mientras el primero seguía en curso). Esto es compatible con: **un widget que se destruye a sí mismo (o a un ancestro/hermano en el mismo árbol) mientras todavía está procesando el evento de mouse que lo originó.**

Para leer el JSON completo tú mismo (los `.ips` tienen una línea de metadata antes del JSON real):
```bash
tail -n +2 ~/Library/Logs/DiagnosticReports/Python-2026-08-06-093556.ips > /tmp/crash.json
python3 -c "
import json
d = json.load(open('/tmp/crash.json'))
threads = d['threads']; images = d['usedImages']
t = threads[d['faultingThread']]
for f in t['frames']:
    idx = f.get('imageIndex')
    name = images[idx]['name'] if idx is not None else '?'
    print(name, f.get('symbol',''))
"
```

Puede haber reportes de crash más nuevos si el crash se reproduce de nuevo — revisa `ls -t ~/Library/Logs/DiagnosticReports/ | grep -i python` por fecha antes de asumir que estos dos son los últimos.

## 2. Hipótesis principal — verifícala, no la des por buena a ciegas

En esta misma sesión, minutos antes del crash, se agregó la función de **filmstrip clickeable**: cada miniatura (`_ClipItemWidget` en `src/clasificador_video/ui/filmstrip.py`) ahora tiene `mousePressEvent` que emite una señal `clicked`, conectada (vía `Filmstrip.clip_clicked`) a `MainWindow.select_clip(index)`.

`select_clip` llama a `_refresh_filmstrip()`, que en algún punto de la cadena termina en `Filmstrip.set_clips(...)`:

```python
def set_clips(self, clips: list[ClipThumbnail]) -> None:
    for widget in self.item_widgets:
        widget.setParent(None)   # <-- reconstruye TODO el filmstrip, incluyendo
    self.item_widgets = []       #     el widget que originó el click
    ...
```

**La hipótesis:** el click en una miniatura dispara, de forma síncrona y dentro de su propio `mousePressEvent`, la reconstrucción completa del filmstrip — lo que destruye (o reemplaza) el propio widget que está siendo clickeado, mientras Qt todavía tiene ese widget referenciado en su maquinaria interna de despacho de eventos de mouse (`qt_button_down` y similares, internos a `QApplicationPrivate`). Es un patrón clásico y bien documentado de Qt: **no destruyas un widget desde dentro de su propio manejador de evento** — el crash de arriba (SIGSEGV en `sendMouseEvent`, con eventos anidados) encaja con esto casi a la perfección.

Verifícalo así:
1. Confirma primero con `git stash` (o `git diff` + revertir manualmente) que el crash **no** ocurre con el estado del último commit (`1662865`) — solo con material de `TEST/clips/`, sin tocar el filmstrip. Deja pasar unos segundos, importa, espera miniaturas, cierra. Si no truena, ya acotaste el bug a los cambios sin commitear.
2. Reaplica los cambios (`git stash pop`), reproduce el crash de verdad: importa `TEST/clips/`, espera a que aparezcan las miniaturas, haz click rápido sobre una miniatura (o varios clicks seguidos sobre distintas miniaturas). Si el crash reaparece con ese patrón, la hipótesis queda confirmada.
3. Si se confirma, el fix correcto es **no reconstruir el filmstrip de forma síncrona dentro del manejador de click del propio filmstrip**. Opciones a evaluar (elige la más limpia, no la más rápida):
   - Diferir la actualización visual con `QTimer.singleShot(0, self._refresh_filmstrip)` para que ocurra después de que el evento de mouse actual termine de despacharse por completo.
   - Evitar destruir/recrear los widgets del filmstrip en cada `_refresh_filmstrip()` cuando la lista de clips no cambió — solo actualizar `set_current()` y flags, sin pasar por `set_clips()` (esto además sería más eficiente). Repasa todos los call-sites de `_refresh_filmstrip()` en `main_window.py` para ver si ya existe esa distinción o si conviene separarla en dos métodos (`_refresh_filmstrip()` reconstruye todo; algo como `_update_filmstrip_state()` solo actualiza bordes/flags sin destruir widgets).
4. Si la hipótesis NO se confirma (el crash reaparece incluso sin los cambios del filmstrip, o no reaparece ni con clicks), documenta lo que sí reproduce el crash y sigue investigando por ese camino — no fuerces esta hipótesis si la evidencia real la contradice.

## 3. Qué NO tocar y qué sí revisar de lo ya hecho hoy

### 3.1 Commits ya en `master` (no son sospechosos del crash, son de la reconstrucción v2 completada horas antes)

Ver `git log --oneline -8` y el informe en `docs/superpowers/HANDOFF-2026-08-06-informe-v2.md` para contexto completo de la reconstrucción v2 (embedding de video vía API de render de mpv, 4 bugs de diseño visual, un crash nativo distinto ya resuelto ahí). No repitas esa investigación, ya está documentada.

### 3.2 Cambios sin commitear en el working tree — revísalos con cuidado, son el sospechoso principal

```
 src/clasificador_video/app.py            |  1 +
 src/clasificador_video/ui/filmstrip.py   | 15 +++++++++++--
 src/clasificador_video/ui/main_window.py | 18 +++++++++++++++-
 tests/test_app.py                        | 20 ++++++++++++++++++
 tests/ui/test_filmstrip.py               | 20 ++++++++++++++++++
 tests/ui/test_main_window.py             | 36 ++++++++++++++++++++++++++++++++
```

Son tres arreglos distintos, hechos con TDD, cada uno con su test:

1. **`app.py`** — restaurar sesión guardada no programaba miniaturas (`_restore_session` cargaba los clips pero nunca llamaba a `_schedule_thumbnails()`). Fix de una línea. Bug real, confirmado por Bruno en vivo. Bajo riesgo, probablemente no relacionado al crash.
2. **`filmstrip.py` + `main_window.py`** — **filmstrip clickeable** (el sospechoso principal, sección 2 de este documento). Pedido explícito de Bruno.
3. **`main_window.py`** (`_ThumbnailJob.run`) — un `try/except RuntimeError` alrededor de `self.signals.done.emit(...)`, porque en corridas repetidas de la suite completa apareció una condición de carrera real: un hilo de miniatura de una prueba anterior a veces emitía su señal después de que la ventana dueña (y el `QWidget` que carga la señal) ya se había destruido. Esto es un fix defensivo válido en general, pero **repásalo con la hipótesis de la sección 2 en mente** — no debería estar relacionado (es sobre hilos de background terminando tarde, no sobre el hilo principal despachando un evento de mouse), pero confírmalo, no lo descartes solo porque "no debería estar relacionado".

Todos los tests nuevos pasan, y la suite completa (157 tests) pasó **cinco veces seguidas sin fallos ni crashes** — pero la suite usa `_FakeMpv`/dobles y no reproduce interacción real de mouse sobre widgets reales del filmstrip con miniaturas reales cargándose en paralelo, que es exactamente el escenario donde Bruno vio el crash. Esa es la brecha real entre "los tests pasan" y "la app truena" — no la ignores, ya la señalamos, corrígela si aplica (agrega un test con `qtbot.mouseClick` real sobre un filmstrip con varios clips y miniaturas cargando de fondo, si la hipótesis se confirma).

## 4. Cómo verificar sin asumir

Sigue el mismo estándar que ya se estableció en `HANDOFF-2026-08-06-arreglar-video-y-diseno.md` (sección 5 de ese documento): no te conformes con "no truena" tras una corrida corta. Específicamente para este bug:

1. Reproduce el crash primero, de forma confiable, ANTES de tocar código — si no puedes reproducirlo tú mismo con material real de `TEST/clips/`, dilo explícitamente en el informe final en vez de "arreglar" algo que no confirmaste.
2. Una vez que tengas un fix candidato, reproduce el MISMO patrón de interacción que causó el crash (importar, esperar miniaturas, clicks rápidos y repetidos sobre distintas miniaturas, incluyendo mientras las miniaturas siguen cargando de fondo) al menos 10-15 veces seguidas sin crash antes de darlo por resuelto. Un crash de null-pointer por condición de carrera no siempre reproduce en el primer intento tras el fix.
3. Corre la suite completa (`~/.venv/bin/pytest tests/ -q`) al menos 3 veces seguidas — recuerda que ya hay antecedente de una condición de carrera real detectada solo por correr la suite repetidamente (sección 3.2, punto 3).
4. Revisa `~/Library/Logs/DiagnosticReports/` por nuevos crash reports de `Python` después de cada intento de reproducción — es evidencia real, no asumas por la ausencia de excepción visible en consola que no crasheó (un `SIGSEGV` no siempre imprime traceback de Python).

## 5. Definición de "terminado"

- El crash se reprodujo de forma confiable con evidencia real (crash report nuevo o comportamiento observado), no solo se infirió.
- La causa raíz está identificada con evidencia (no solo la hipótesis de la sección 2 sin confirmar).
- El fix está aplicado con TDD (test que falla reproduciendo el escenario → fix → test pasa), commiteado.
- Al menos 10-15 repeticiones del patrón de interacción que causaba el crash, sin crash ni nuevo reporte en `DiagnosticReports`.
- Suite completa corrida 3+ veces seguidas, 0 fallos.
- Informe corto al final (mismo formato que la sección 8 de `HANDOFF-2026-08-06-auditoria-bugs.md`) documentando: causa raíz real (confirmada, no solo hipótesis), fix aplicado, evidencia de verificación, y si los cambios sin commitear de la sección 3.2 se mantuvieron, se modificaron o se revirtieron.
