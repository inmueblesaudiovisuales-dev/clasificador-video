# Handoff — Mejorar la línea de tiempo de in/out (tipo Premiere) — 2026-08-06

## 0. Tarea de esta sesión

Bruno acaba de ver la primera versión de la `ScrubBar` (línea de tiempo con marcadores de in/out debajo del video) y pidió explícitamente sumarle features para que se parezca más a como Premiere Pro maneja el marcado de in/out:

- **Tiempo visible** — mostrar el timecode (no solo la posición geométrica en la barra).
- **Frame visible** — mostrar el número de frame, no solo el tiempo en segundos.
- **Visible desde que se marca IN** — hoy el marcador **no aparece hasta que están IN y OUT los dos puestos**. Esto es un bug de diseño concreto, no una interpretación: ver sección 2.

Esta es la primera tarea nueva de la próxima sesión. No es una sesión de diseño desde cero — es iterar sobre algo que ya existe y funciona parcialmente.

## 1. Qué es esta app (contexto rápido para quien arranque en frío)

App de escritorio (PySide6) para que un editor de video clasifique clips de shootings inmobiliarios por cuarto, marque in/out y bueno/malo, y exporte un manifest que un plugin de Adobe Premiere usa para armar el proyecto de edición solo. La usa un editor trabajando rápido con el teclado, muchas veces junto a Premiere abierto — por eso la comparación constante con Premiere no es casualidad, es el estándar real contra el que Bruno mide la app.

## 2. El bug concreto a resolver primero

Archivo: `src/clasificador_video/ui/video_widget.py`, clase `ScrubBar`, método `paintEvent` (línea ~176-201).

```python
if self._duration > 0:
    if self._in_frame is not None and self._out_frame is not None and self._fps:
        # ... dibuja el tramo resaltado + brackets
    x = self._x_for(self._position, left, usable_width)
    # ... dibuja el playhead
```

La condición `self._in_frame is not None and self._out_frame is not None` exige **ambos** marcadores para dibujar cualquier cosa relacionada al rango. Si el editor presiona `I` pero todavía no `O`, la barra no muestra absolutamente nada del marcado — ni un solo bracket indicando "acá empieza". Esto contradice directamente el pedido de Bruno ("que sea visible desde que pones in").

**Cómo lo resuelve Premiere de verdad:** al marcar solo el IN, aparece un bracket en esa posición inmediatamente, y el tramo "sin cerrar" (desde IN hasta donde sea que esté el playhead, o hasta el final) se sugiere de forma más sutil hasta que se cierra con el OUT. No hace falta copiar el comportamiento exacto pixel por pixel, pero el principio es: **cada marcador se dibuja de forma independiente en cuanto existe**, no como una unidad atómica que exige los dos.

Fix mínimo: separar la lógica en dos partes independientes — dibujar el bracket de IN si `self._in_frame is not None` (sin importar el estado de OUT), dibujar el bracket de OUT si `self._out_frame is not None`, y dibujar el tramo resaltado entre ambos solo si los dos existen. Los tests nuevos deben cubrir explícitamente el caso "solo IN, sin OUT" — hoy no hay ningún test que lo verifique (revisar `tests/ui/test_video_widget.py`, los tests de `ScrubBar` que ya existen solo prueban con ambos seteados o ninguno).

## 3. Features pedidas explícitamente — qué implica cada una

### 3.1 Tiempo visible

Hoy la `ScrubBar` es puramente geométrica: una línea con marcas de posición, sin ningún texto. Bruno pide que se vea el tiempo. Antes de implementar, definir con él (o usar criterio si no está disponible, documentando la decisión):

- ¿Timecode en formato `HH:MM:SS:FF` (frames) o `HH:MM:SS.mmm`? Dado que la app ya piensa todo en frames (`Clip.in_frame`/`out_frame` son frames, no segundos — ver `manifest.py`), probablemente lo más consistente es `MM:SS:FF` o similar, no milisegundos.
- ¿Dónde se muestra? Opciones: como texto flotante junto a cada bracket (aparece/desaparece con el marcador), como texto fijo en una esquina de la barra (ej. "IN 00:00:12 · OUT 00:00:34 · dur 22s"), o ambos.
- Ya existe `MpvPlayer.duration`/`.position` (agregados en la sesión anterior, ver `player.py`) para el tiempo total y la posición actual del playhead — se puede reusar para mostrar el tiempo del playhead también, no solo de los marcadores.

### 3.2 Frame visible

Los marcadores ya se guardan en frames (`clip.in_frame`, `clip.out_frame`, enteros). Mostrar el número de frame es directo — no hace falta ninguna conversión nueva, es literalmente el valor que ya existe en el modelo. La conversión que sí hay que hacer es la inversa: `clip.fps` + tiempo del playhead → frame actual, para mostrar en qué frame está parado el playhead ahora mismo (no solo los marcadores). Fórmula ya usada en otro lado del código para esto: `round(mpv.time_pos * fps)` (ver `MpvPlayer.mark_in`/`mark_out` en `player.py`).

### 3.3 Visible desde que se marca IN

Ver sección 2 — es el fix del bug, no una feature nueva sobre datos que no existen.

## 4. Qué NO asumir sin preguntar primero

- **No agregar interacción de click/drag a la `ScrubBar`** sin confirmar con Bruno. Hoy es deliberadamente solo informativa (el docstring de la clase lo dice explícito: "no reacciona a click ni arrastre, marcar sigue siendo con el teclado"). Si en esta sesión Bruno pide poder hacer click para saltar a una posición, eso es un cambio de alcance real (agregar mouse handling, posiblemente conectar con `mpv.seek`) — confirmar antes de asumir que está incluido en "ponerle features tipo Premiere".
- **No tocar `Clip`/`manifest.py`** — el contrato del manifest con el plugin UXP no es parte de esto, y no hace falta: todo lo que se pide (tiempo, frame) es derivable de datos que ya existen (`in_frame`, `out_frame`, `fps`, `player.position`, `player.duration`), no requiere guardar nada nuevo.
- **Mantener el paintEvent custom con QPainter**, no migrar a QSS dinámico — fue una decisión deliberada de la sesión anterior (ver handoff de rediseño visual y la revisión crítica de arquitectura: QSS dinámico por widget es un anti-patrón de performance en Qt para elementos que se repintan seguido, que es exactamente el caso de una barra con playhead animado).
- **Mantener la separación de colores**: `TRIM_COLOR` (celeste) para el rango in/out marcado, `ACCENT` (naranja) para el playhead — no reusar uno para el otro. Es la misma lógica de separación de canales de color que ya se aplicó en el resto del rediseño (ver `theme.py`, comentarios sobre por qué el color de estado y el de identidad de cuarto no comparten familia).

## 5. Cómo verificar (no des nada por terminado sin esto)

- **Tests**: `cd "ORGANIZADOR VIDEO" && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q`. `tests/test_app.py` tiene un cuelgue preexistente documentado (limitación del entorno sin pantalla real para el `QOpenGLWidget` del video, confirmado que ya existía antes de esta sesión) — no perseguirlo, no es parte de esta tarea.
- **Verificación visual real, no solo tests**: construir una `MainWindow` con un `Clip` de prueba, marcar in/out (o setear `clip.in_frame`/`out_frame` directo si es más simple), llamar `window.grab()`, guardar el PNG, y **leer la imagen con la herramienta de lectura de archivos antes de afirmar que algo se ve bien**. Cubrir al menos: solo IN marcado (sin OUT), IN+OUT marcados, y el estado sin marcar (para confirmar que no se rompió nada). Los scripts de verificación de la sesión anterior (ej. capturas con `FakeMpv` inyectando `time_pos`/`duration`) son un buen punto de partida — ver el patrón en los commits recientes (`git log --oneline -10`).
- **Commits**: mensajes en español, un commit por unidad de trabajo lógica, terminan con `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. Trabajo directo en `master` — Bruno pidió explícitamente no crear branches nuevas.

## 6. Preferencias de Bruno para esta sesión (no son parte del código, pero importan)

- Prefiere que se le hable en español neutro, sin jerga ni modismos argentinos.
- Prefiere que se actúe directamente en vez de preguntar cosas obvias — pero eso no exime de preguntar decisiones de producto genuinas (ej. el formato exacto de timecode de la sección 3.1) si no hay una respuesta obviamente correcta.
- Ya mostró que valora que se investigue/mida antes de implementar cuando hay una decisión técnica no trivial (ver cómo se resolvió la extracción de miniaturas: medición real de tiempos antes de comprometerse a un enfoque). Si alguna de estas features tiene una decisión de implementación no obvia, vale la pena el mismo approach: medir/probar antes de asumir.

## 7. Estado del resto de la app (para contexto, no es parte de esta tarea)

Todo lo demás del rediseño visual + performance ya está commiteado en `master` y funcionando: paleta "Console", selección múltiple con etiquetado en lote, scrub de miniaturas tipo Final Cut (tira de 12 frames vía mpv IPC), cache persistente de miniaturas, autosave asíncrono con debounce. Ver los commits recientes (`git log --oneline -10`) y los handoffs anteriores en esta misma carpeta para el detalle de cada uno si hace falta contexto adicional.
