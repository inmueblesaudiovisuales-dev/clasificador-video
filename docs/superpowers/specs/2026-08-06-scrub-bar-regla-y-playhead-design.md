# Spec — Regla de tiempo (ticks) y playhead tipo Premiere en la ScrubBar

## 0. Contexto

Bruno vio la `ScrubBar` funcionando (seek con mouse, brackets de IN/OUT, timecode
visible — sesión anterior) y pidió acercarla más visualmente a la línea de tiempo de
Premiere Pro, mostrando como referencia la regla de marcas y el playhead con forma de
bandera del Source Monitor real. Se exploraron opciones con mockups HTML usando la
paleta real de la app (`theme.py`) y se aprobó una dirección concreta.

Esto es una mejora puramente visual sobre `ScrubBar.paintEvent` — no cambia seek,
brackets de IN/OUT, ni el label de timecode (`scrub_time_label` en `main_window.py`),
que ya existen y se mantienen tal cual.

## 1. Regla de marcas (ticks)

Reemplaza la línea plana de fondo del track por una regla con marcas verticales, como
la de Premiere. Las marcas representan tiempo real del clip, no son decorativas.

### 1.1 Elegir el intervalo

Función nueva `_tick_interval_seconds(duration: float, usable_width: int) -> float`:
recorre una lista fija de intervalos "prolijos", de menor a mayor —
`[1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600]` segundos — y devuelve el
primero para el que `usable_width * (intervalo / duration) >= 48` (es decir, que dos
marcas mayores consecutivas queden a 48px o más de distancia, legible sin amontonarse).
Si ningún intervalo de la lista alcanza esa separación (clips muy largos), usa el
último (3600s). Si `duration <= 0`, no se dibuja ninguna marca.

### 1.2 Marcas mayores y menores

- Marca **mayor** en cada múltiplo del intervalo elegido (`0, intervalo, 2*intervalo, ...`
  hasta `duration`), altura 9px, color `#55555c`.
- 4 marcas **menores** repartidas en partes iguales entre cada par de marcas mayores
  consecutivas (es decir, en 1/5, 2/5, 3/5, 4/5 del intervalo), altura 5px, color
  `#3a3a40`.
- Todas las marcas nacen desde `track_y` hacia arriba (no hacia abajo, para dejar
  espacio al playhead que ahora vive mayormente por debajo de `track_y`).
- Sin números/texto en la regla — el timecode ya se lee en `scrub_time_label` arriba
  de la barra.

### 1.3 Altura del widget

`ScrubBar.setFixedHeight(26)` pasa a `34` — el espacio actual no alcanza para regla +
track + la cabeza del playhead sin que se pisen. `track_y` se recalcula como una
posición fija cerca de la parte superior (no `height() // 2`), dejando más aire abajo
para el trazo del playhead. Los brackets de IN/OUT y el tramo resaltado (`TRIM_COLOR`)
no cambian de lógica, solo se re-anclan a la nueva `track_y`.

## 2. Playhead tipo "casita" (variante C de los mockups)

Reemplaza la línea recta vertical que hoy representa el playhead por una forma de
bandera/pin, apoyada sobre la regla, con la punta hacia abajo tocando exactamente la
posición actual:

- **Cuerpo**: rectángulo de 13px de ancho x 7px de alto, esquinas superiores
  redondeadas (~2.5px), centrado horizontalmente en la posición del playhead, apoyado
  justo arriba de `track_y`.
- **Punta**: triángulo de 13px de base x 6px de alto, debajo del cuerpo, terminando
  exactamente en `track_y` (el punto que indica la posición exacta).
- **Relleno**: gradiente vertical sutil de `#ff9d5c` (arriba) a `ACCENT` (`#ff8a3d`,
  abajo) — el brillo que se veía en el mockup C, usando `QLinearGradient` (ya es un
  patrón disponible en `QPainter`, no requiere dependencias nuevas).
- **Línea del track**: se mantiene una línea vertical fina (1px, color `ACCENT`) desde
  la base de la punta del playhead hasta el final del widget, para que el playhead
  siga siendo visible incluso mientras se mira el resto del track.

Implementación con `QPainter`: `QPolygon` (o `QPainterPath`) para el cuerpo+punta
combinados en una sola forma rellena, más `drawLine` para la línea fina inferior —
mismo patrón ya usado en el resto de `paintEvent` (nada de QSS, sigue siendo pintura
custom, consistente con la decisión ya tomada en sesiones anteriores).

## 3. Qué NO cambia

- Seek con mouse (`seek_started`/`seek_requested`), pausa al arrastrar — sin cambios.
- Brackets de IN/OUT y tramo resaltado (`TRIM_COLOR`) — misma lógica, solo se
  reposicionan verticalmente respecto al nuevo `track_y`.
- `scrub_time_label` (texto de IN/OUT/dur/pos arriba de la barra) — sin cambios.
- `_x_for` / `_seconds_for_x` (conversión posición↔segundos) — sin cambios, la regla
  visual no altera la geometría de mapeo tiempo→pixel.

## 4. Testing

Actualizar `tests/ui/test_video_widget.py`:

- `_tick_interval_seconds`: casos con duraciones cortas (10s → intervalo chico, ej. 1s
  o 2s), medias (90s), largas (600s+ → intervalos grandes), y el caso límite donde
  ningún intervalo de la lista alcanza 48px (duración extrema) para confirmar que cae
  al último de la lista sin crashear.
- Marcas mayores: para una duración y ancho conocidos, verificar que se dibuja el
  número esperado de marcas mayores (`grab()` + conteo de pixeles del color de marca
  mayor a lo largo de una fila horizontal fija, o exponer la lista de posiciones de
  marcas mayores como método auxiliar testeable si el conteo por pixel resulta frágil).
- Playhead: confirmar que ya no se dibuja como una línea recta de punta a punta (no
  debe haber píxeles `ACCENT` en la fila superior del widget fuera del área del cuerpo
  de la casita) y que la punta toca `track_y` en el x correcto para una posición dada.
- Regresión: correr toda la suite existente de `ScrubBar` (brackets IN/OUT, seek con
  mouse) para confirmar que el cambio de `track_y` y altura del widget no rompió nada
  de lo ya implementado.

### Verificación visual

Igual que en la sesión anterior: construir `MainWindow` con clips de prueba, distintas
duraciones (para ver la regla adaptarse — un clip corto vs uno largo), `grab()`, y leer
los PNG generados antes de dar por terminado. Cubrir al menos: clip corto (~10s), clip
de duración media (~90s), y confirmar que el playhead con forma de casita se ve
correctamente en los tres casos de IN/OUT ya cubiertos en la sesión anterior (sin
marcar, solo IN, IN+OUT).

## 5. Commits

Mensajes en español, un commit por unidad lógica (sugerido: 1. regla de ticks +
recálculo de `track_y`/altura, 2. playhead tipo casita), terminan con
`Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. Directo en `master`, sin
branches nuevas — mismo criterio que las sesiones anteriores.
