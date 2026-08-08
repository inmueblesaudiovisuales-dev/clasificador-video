# Spec — ScrubBar interactiva: seek con mouse, fix IN-sin-OUT, timecode visible

## 0. Contexto y alcance

Handoff previo (`docs/superpowers/archive/HANDOFF-2026-08-06-mejorar-scrub-bar-in-out.md`) pedía
tres cosas sobre la `ScrubBar` (línea de tiempo bajo el video): timecode visible, frame
visible, y que el marcador de IN aparezca sin esperar al OUT. Ese handoff marcaba
explícitamente **no agregar interacción de click/drag sin confirmar con Bruno primero**.

En esta sesión Bruno pidió explícitamente esa interacción: poder adelantar/retrasar el
video con el mouse sobre la barra, como un reproductor real. Se decidió resolver las
cuatro cosas juntas porque todas tocan el mismo archivo (`video_widget.py`) y la misma
sesión de trabajo.

## 1. Seek con mouse en la ScrubBar

### 1.1 Comportamiento acordado

- **Click simple** en cualquier punto de la barra salta el video a esa posición.
- **Arrastre** hace seek continuo: el video va saltando en vivo a cada posición mientras
  se mueve el mouse con el botón apretado (no se espera a soltar).
- Al **empezar** el gesto (mouse press), si el video estaba reproduciendo, se pausa. Queda
  pausado al soltar, mostrando el frame exacto donde se soltó — no vuelve a reproducir
  solo.

### 1.2 División de responsabilidades

`ScrubBar` sigue sin conocer a `MpvPlayer` — mantiene la separación actual. Su única
responsabilidad nueva es traducir eventos de mouse a una posición en segundos y emitir
una señal Qt:

```python
seek_requested = Signal(float)  # segundos, ya clampeado a [0, duration]
```

Implementación en `ScrubBar`:

- `mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent` — todos calculan la posición
  en segundos a partir de `event.position().x()` (inverso de `_x_for`, clampeado a
  `[0, self._duration]`) y emiten `seek_requested`.
- `mouseMoveEvent` solo emite si el botón izquierdo está apretado (`event.buttons() &
  Qt.MouseButton.LeftButton`) — evita emitir en hover.
- No hace falta distinguir press/move/release en la señal misma (un solo tipo de evento,
  `float`); quien necesite saber "es el inicio del gesto" es `MainWindow`, que sí sabe
  distinguir `mousePressEvent` porque conecta un slot distinto para ese caso (ver 1.3).

### 1.3 Wiring en MainWindow

`MainWindow` conecta la señal y agrega el manejo de pausa-al-empezar-arrastre. Como
`ScrubBar` emite un único tipo de señal para press/move/release, `MainWindow` necesita
saber cuándo un gesto *empieza* para decidir si pausar. Opción más simple sin acoplar
`ScrubBar` a `MpvPlayer`: agregar una segunda señal booleana o reusar el flag interno.

Diseño elegido: `ScrubBar` emite dos señales:

```python
seek_started = Signal()        # mousePressEvent, antes de emitir la posición
seek_requested = Signal(float) # en press, move (con botón apretado) y release
```

`MainWindow`:

```python
self.scrub_bar.seek_started.connect(self._on_scrub_seek_started)
self.scrub_bar.seek_requested.connect(self._on_scrub_seek)

def _on_scrub_seek_started(self) -> None:
    self.video_widget.player.pause()

def _on_scrub_seek(self, seconds: float) -> None:
    self.video_widget.player.seek(seconds)
    self.scrub_bar.set_position(seconds)  # feedback inmediato, sin esperar el timer de 150ms
```

No se retoma reproducción automáticamente al soltar (decisión explícita: queda pausado,
ver 1.1). No hace falta guardar el estado de reproducción previo porque no se restaura.

### 1.4 Cambios en `MpvPlayer`

Agregar método nuevo (no existe hoy):

```python
def seek(self, seconds: float) -> None:
    self._mpv.time_pos = max(0.0, min(seconds, self.duration))
```

Agregar también `is_paused` como property de solo lectura (`return self._mpv.pause`) —
hoy `MainWindow` no tiene forma de preguntar el estado sin tocar `_mpv` directo.

## 2. Fix: marcador de IN visible sin OUT

En `ScrubBar.paintEvent`, reemplazar la condición atómica actual (exige IN y OUT) por
tres bloques independientes:

1. Si `self._in_frame is not None`: dibujar el bracket de IN en su posición.
2. Si `self._out_frame is not None`: dibujar el bracket de OUT en su posición.
3. Si **ambos** existen: dibujar además el tramo resaltado entre los dos (como ya se
   hacía).

Los tres bloques comparten el mismo `TRIM_COLOR` y grosor de pen que ya existen.

## 3. Timecode y frame visibles

### 3.1 Formato

`MM:SS:FF` (minutos:segundos:frame), sin horas — los clips de este flujo (shootings
inmobiliarios) no superan los 10 minutos. Frame es el resto de dividir por fps, igual
que ya calcula `MpvPlayer.mark_in`/`mark_out` (`round(time_pos * fps)`), pero a la
inversa.

Nueva función en `video_widget.py`:

```python
def format_timecode(frame: int, fps: float) -> str:
    """MM:SS:FF a partir de un numero de frame absoluto."""
    if fps <= 0:
        return "00:00:00"
    total_seconds = frame / fps
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    remaining_frames = round(frame - (minutes * 60 + seconds) * fps)
    return f"{minutes:02d}:{seconds:02d}:{remaining_frames:02d}"
```

### 3.2 Dónde se muestra

Nuevo `QLabel` (`scrubTimeLabel`), estilo mono/muted (mismo patrón que `legendLabel` en
`theme.py`), ubicado en `video_column` entre `video_widget` y `scrub_bar`. Texto:

```
IN 00:12:03 · OUT 00:34:10 · dur 22s · pos 00:15:02
```

- Segmento `IN ...` solo aparece si `clip.in_frame is not None`.
- Segmento `OUT ...` solo aparece si `clip.out_frame is not None`.
- `dur` se calcula de `out_frame - in_frame` en segundos, solo si ambos existen.
- `pos` siempre aparece si hay un clip cargado — refleja `player.position` actual,
  usando frame = `round(position * fps)`.
- Si no hay clip cargado, el label queda vacío (`""`).

Actualización: se recalcula en `_update_scrub_bar()` (cuando cambian in/out o el clip) y
en `_tick_playhead()` (cuando cambia la posición, cada 150ms via el timer existente, y
también en cada `_on_scrub_seek` para que se sienta responsive durante el arrastre).

## 4. Qué NO cambia

- `Clip`/`manifest.py` no se tocan — todo lo mostrado es derivado de datos existentes.
- Se mantiene `QPainter` custom en `paintEvent`, no se migra a QSS.
- Se mantiene la separación de colores `TRIM_COLOR`/`ACCENT`.
- El playhead sigue dibujándose con `ACCENT`; el seek con mouse no introduce un color
  nuevo, solo hace que el playhead responda también al mouse además del timer.

## 5. Testing

Actualizar `tests/ui/test_video_widget.py`:

- **ScrubBar:**
  - `seek_requested` se emite con la posición correcta en `mousePressEvent`,
    `mouseMoveEvent` (con botón apretado) y `mouseReleaseEvent`.
  - `mouseMoveEvent` sin botón apretado NO emite `seek_requested` (evitar falso positivo
    de hover).
  - `seek_started` se emite una vez por `mousePressEvent`.
  - Posición clampeada a `[0, duration]` si el mouse está fuera de los bordes de la barra.
  - Bracket de IN se dibuja (no truena) con solo `in_frame` seteado y `out_frame is None`
    — verificar con `grab()` que no lanza excepción y opcionalmente que el pixel del
    bracket de IN tiene el color esperado.
  - Igual para solo OUT.
  - `format_timecode` — casos: frame 0, frame exacto en un segundo, fps no entero (ej.
    29.97), fps <= 0 (no debe crashear).

- **MpvPlayer:**
  - `seek(seconds)` setea `time_pos` clampeado a `[0, duration]`.
  - `seek` con `seconds` negativo clampea a 0.
  - `seek` con `seconds` mayor a `duration` clampea a `duration`.
  - `is_paused` refleja `self._mpv.pause`.

- **MainWindow** (si hay tests de integración de wiring, si no, verificación manual):
  - Conectar `seek_started`/`seek_requested` dispara pausa + seek en el player mockeado.

### Verificación visual

Igual que indicaba el handoff original: construir `MainWindow` con un `Clip` de prueba,
usar `qtbot.mousePress`/`mouseMove`/`mouseRelease` sobre `scrub_bar`, llamar
`window.grab()`, guardar el PNG y leerlo antes de afirmar que algo se ve bien. Cubrir:
solo IN, IN+OUT, sin marcar, y el label de timecode con distintos combos de IN/OUT
presentes/ausentes.

## 6. Commits

Mensajes en español, un commit por unidad lógica (sugerido: 1. fix IN-sin-OUT + tests,
2. timecode/frame visible + tests, 3. seek con mouse + tests), terminan con
`Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. Directo en `master`, sin
branches nuevas.
