# Análisis: la app actual contra el mockup de rediseño — 2026-08-08

Comparación exhaustiva entre el estado del código en `src/clasificador_video/`
y la dirección de diseño de
[`mockups/rediseno-2026-08-08/`](mockups/rediseno-2026-08-08/DECISIONES.md).

Sirve de base para el plan de implementación: dice qué ya está hecho, qué está
roto, qué falta, y qué se rompe al implementar el rediseño.

**Cómo se produjo**: lectura completa de los ~2,600 renglones de
`src/clasificador_video/` y del plugin en `uxp-plugin/js/`, más una captura
real de `MainWindow` a 1600×1000 —el mismo tamaño del mockup— con un doble de
mpv, bajo `QT_QPA_PLATFORM=offscreen`. Las medidas de layout de la §4 salen de
esa captura, no de estimaciones. Para regenerarla: construir una `MainWindow`
con `video_factory` falso, `resize(1600, 1000)`, `show()`, `grab().save(...)`.

---

## 1. Lo que la app YA hace y el mockup daba por nuevo

Lo más importante del análisis, porque evita trabajo duplicado.

| Función | Dónde vive | Nota |
|---|---|---|
| **Scrub de la miniatura con el mouse** | `ui/filmstrip.py:165` | **Ya implementado.** 12 frames por clip en una sola sesión IPC de mpv, cacheados en disco. El mockup lo presentaba como novedad. |
| Selección múltiple Shift/Ctrl+click | `ui/filmstrip.py:380` | Con anchor y rango |
| Asignación de cuarto en lote | `ui/main_window.py:355` `_bulk_targets` | Ligada a la selección múltiple |
| Vista grilla / lista | `ui/filmstrip.py:320` | El toggle del mockup ya existe |
| Autoguardado con debounce + "Guardado hace Xs" | `ui/main_window.py:195` | Hilo aparte, rename atómico |
| Scrub bar con click y arrastre, ticks adaptativos, in/out, playhead | `ui/video_widget.py:168` | Más pulida que la del mockup |
| Selector de calidad Full / ½ / ¼ / ⅛ | `player.py:7` | Idéntico al mockup |
| Conteo por cuarto con barra proporcional | `ui/main_window.py:62` | El rail izquierdo del mockup, ya hecho |
| Separación de color por canal semántico | `ui/theme.py:24` | El mockup usa exactamente este esquema |
| Caché de miniaturas invalidado por tamaño+mtime | `thumbnails.py:20` | |
| Aviso de clips sin clasificar al exportar | `ui/main_window.py:698` | Advierte sin bloquear, como pide el mockup |
| `probe_clip` lee rotación y corrige width/height | `probe.py:19` | La app **sabe** cuáles clips son verticales |

## 2. Tres cosas rotas o muertas hoy

### Ctrl+Z no existe

La leyenda al pie dice `Ctrl+Z deshacer` (`ui/main_window.py:53`), pero no hay
atajo registrado ni pila de undo en ningún módulo. `_install_shortcuts` solo
registra Espacio, ←, →, I, O, P, X, U y 1–9. **La app anuncia una función que
no tiene**, y deshacer es de lo más pedido en el rediseño.

### La cadena de proxies está desconectada

`match_proxies()` existe y está probado, `ruta_proxy` viaja en el manifest y el
plugin lo consume (`uxp-plugin/js/processManifest.js:32`). Pero **nada en la UI
llama nunca a `match_proxies`**: `_load_clips_from_ingest` crea cada `Clip` sin
`ruta_proxy`. Hoy los proxies solo funcionan editando el JSON de sesión a mano.

### La orientación del manifest está hardcodeada

`Manifest(orientacion="horizontal")` con un `# TODO fase 3`
(`ui/main_window.py:710`). Y peor: `_load_clips_from_ingest` llama a
`probe_clip` y **descarta `width`, `height` y `rotation`**, quedándose solo con
`fps` y `duration_frames`.

O sea que el dato que el mockup necesita para las miniaturas verticales, el
filtro "Verticales" y el badge de rotación **ya se calcula y se tira**.

## 3. El choque directo: con los cuartos del mockup, la app no clasifica

El hallazgo más serio. En `ui/main_window.py:585`:

```python
if _es_room_numerado(room) and not self._router.subrooms.get(room):
    self._router.pending_parent = room
    return  # la tecla siguiente elige el subcuarto
```

**Cualquier cuarto cuyo nombre termine en número entra en modo subcuarto.** Y
`RoomSelection.set_count` genera exactamente `Recámara 1`, `Recámara 2`,
`Baño 1`, `Baño 2` — los nombres planos que acordamos en el mockup.

Hoy, presionar `3` con "Recámara 1" no asigna nada: abre un banner que dice
`Elegí subcuarto: 1 Baño 2 Closet 3 Terraza` y se queda esperando.

El esquema plano del mockup no es un cambio cosmético: **está activamente
bloqueado por el código actual.**

(Ese banner es además el único string de la app en argentino: "Elegí" → "Elige".)

## 4. El problema de layout, con números medidos

De la captura real a 1600×1000:

| | App actual | Mockup |
|---|---|---|
| Alto disponible para el video | **583 px** | **940 px** |
| Ancho de un clip vertical 9:16 | **328 px** | **529 px** |
| Negro desperdiciado a los lados | **777 px** | **0** |

La app gasta ~376 px de alto en cinco bandas horizontales: barra superior (45),
etiqueta de tiempo (22), scrub bar (34), filmstrip (250, con
`setFixedHeight(220)` en `ui/filmstrip.py:314`) y leyenda (25). Cada 16 px de
esos cuestan 9 px de ancho de video. **El mockup da 61% más ancho de video sin
cambiar de monitor.**

Segundo problema de layout, no detectado antes: **las tiles del filmstrip son
apaisadas y fijas** — `THUMB_HEIGHT = 80`, `THUMB_MAX_WIDTH = 140`
(`ui/filmstrip.py:21`). Un clip vertical escalado con `KeepAspectRatio` dentro
de esa caja queda de **45 × 80 px**. El modo hoja del mockup depende por
completo de miniaturas verticales legibles; con esta tile no funciona.

Tercero: el panel "Material importado" ocupa la mitad inferior del rail
izquierdo para listar nombres de carpetas.

## 5. Lo que no existe

| Función del mockup | Estado |
|---|---|
| Deshacer + historial visible | No existe (§2) |
| Filtros de cualquier tipo | No existe |
| Filtro como cola de `←/→` | No existe |
| Modo hoja (`⇥`) | No existe |
| Pincel de cuarto | No existe |
| `S` igual al clip anterior | No existe |
| Cuarto estado "destacado" | No existe |
| Paleta `⏎` buscar/crear cuarto | No existe |
| Crear o editar cuartos sin el diálogo inicial | No existe — solo `RoomConfigDialog` al arrancar |
| Autoplay al cambiar de clip | No existe (`player.py`: `pause = True` fijo) |
| Velocidad 1×/2×/4× | No existe |
| Precarga del siguiente clip | No existe |
| Frame por frame (`,` `.`) | No existe |
| Agrupación por cuarto en el panel de clips | No existe |
| Flags en lote (`P`/`X` a varios) | **No** — `handle_key_press` hace `self.current_clip.flag = action`. Solo el cuarto es masivo |
| Aviso "sin clasificar" clickeable | Existe el badge, no el click |
| Timecode sobre el video | Existe abajo, en banda propia |

## 6. Qué se rompe al implementar el mockup

- **Subcuartos**: quitarlos toca `keyboard.py` (`pending_parent`,
  `resolve_subroom_key`), `category_path.py` entero, `rooms.py`
  (`REPEATABLE_ROOMS`, `set_count`), `ui/main_window.py`
  (`_handle_subroom_key`, `SUBROOM_CANDIDATES`, el banner),
  `ui/room_config_dialog.py`, y sus tests. Es la cirugía más grande.
- **Pero el manifest no se rompe**: `categoria_path: list[str]` puede quedarse
  como lista de un elemento, y el plugin ya maneja ese caso
  (`processManifest.js:15`). **No hay que tocar el contrato con Premiere.**
- **"Destacado" es aditivo**: `flag` es un string libre y el plugin mapea
  `pick→FOREST`, `reject→ROSE` e **ignora lo que no conoce**
  (`uxp-plugin/js/label.js`: `if (!labelName) return`). Agregar `"destacado"`
  no rompe nada; solo falta decidir su color de etiqueta en Premiere.
- **`arrancar()` exige el diálogo** para devolver ventana (`app.py:95`). Quitar
  la configuración inicial es un cambio en ese flujo.

## 7. El riesgo técnico real

Todo el diseño depende de **poner controles flotando encima del video**, que es
un `QOpenGLWidget` con mpv dibujando por la API de render. Superponer widgets
normales sobre OpenGL en macOS es históricamente problemático.

A favor: `QOpenGLWidget` (a diferencia de `QOpenGLWindow` o de una ventana
nativa) renderiza a un FBO y **sí compone con hermanos e hijos** en la escena
de Qt, así que en principio funciona.

**Recomendación: un spike corto antes de comprometerse con el layout** — un
`QLabel` semitransparente encima del `VideoWidget`, verificado con `grab()`. Si
falla, el plan B es dibujar los overlays dentro del propio `paintGL` con
`QPainter`.

Fuera de eso, **el mockup no reabre ninguna decisión de arquitectura de
`CLAUDE.md`**: mpv por API de render, `hwdec=videotoolbox`, `QSurfaceFormat`
Core 3.3, `ScrubBar` con `QPainter`, la separación de canales de color y el
descarte de xmeml siguen intactos. La scrub bar se muda encima del video, pero
sigue siendo `QPainter` en `paintEvent`.

## 8. Orden sugerido por relación valor/costo

1. **Arreglar lo roto**: implementar Ctrl+Z de verdad (o quitar la mentira de
   la leyenda), conectar `match_proxies`, y dejar de descartar
   `width`/`height`/`rotation` en `_load_clips_from_ingest`. Barato y
   desbloquea lo demás.
2. **Quitar subcuartos** y pasar a cuartos planos. Sin esto, el resto del
   mockup no se puede probar con nombres reales (§3).
3. **Eliminar las bandas horizontales** y mudar el chrome a overlay + columna
   vertical. Es el cambio que da el video grande; el spike de la §7 va aquí.
4. **Tiles verticales en el filmstrip** y agrupación por cuarto.
5. **Filtros como cola de navegación** + badge clickeable.
6. Flags en lote, `S`, destacado, autoplay/velocidad/precarga.
7. Modo hoja y pincel — los más grandes, y los que más se benefician de que
   todo lo anterior ya esté.
