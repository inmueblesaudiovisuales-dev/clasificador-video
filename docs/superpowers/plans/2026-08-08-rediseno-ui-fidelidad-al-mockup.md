# Plan: llevar la app al mockup sin que se desvíe — 2026-08-08

Objetivo: que la app termine **viéndose como
[el mockup](../mockups/rediseno-2026-08-08/mockup.html) o mejor**, con las
funciones acordadas en [DECISIONES.md](../mockups/rediseno-2026-08-08/DECISIONES.md),
y **sin restos del diseño viejo**.

Punto de partida:
[ANALISIS-2026-08-08-app-actual-vs-mockup.md](../ANALISIS-2026-08-08-app-actual-vs-mockup.md).

Este plan está escrito contra un problema específico que Bruno ha tenido antes:
*las implementaciones terminan siendo el diseño viejo con funciones nuevas a
medias y funciones viejas sin quitar.* La mitad del plan son mecanismos para
que eso no pase; la otra mitad son las fases.

---

## 1. Por qué las implementaciones se desvían del mockup

Seis causas, todas presentes en este proyecto:

1. **Se parcha el layout viejo en vez de reemplazarlo.** Cada tarea dice
   "agregar X a `main_window.py`", así que la estructura vieja sobrevive
   indefinidamente. Nadie la borra porque ninguna tarea dice "borrar".
2. **"Se ve bien" no es un criterio.** Sin un objetivo verificable, la barra la
   pone quien esté cansado a las 11 de la noche.
3. **Los valores visuales se reinventan por widget.** El mockup es CSS con
   variables; la app es QSS. Si cada widget elige su propio gris, la deriva
   empieza en el primer commit y ya no se recupera.
4. **La verificación es por función, no por pantalla.** Se comprueba que "los
   chips de filtro funcionan", nunca que *la pantalla entera se parece al
   mockup*.
5. **Se implementan features antes que el esqueleto.** Cada feature nueva se
   monta sobre la estructura vieja y la consolida.
6. **La migración queda a medias por semanas** y el estado híbrido se vuelve
   la normalidad.

## 2. Los cinco mecanismos anti-deriva

Estos no son pasos: son reglas que aplican a todas las fases.

### M1 — Tokens de diseño extraídos del mockup, primero que nada

Las variables CSS del mockup se vuelven constantes con nombre en
`ui/theme.py`, y **ningún widget escribe un color, radio o tamaño literal**.
Convierte "que se vea igual" de juicio estético a trabajo mecánico.

Esto no es cosmético: **hoy no coincide un solo color.**

| Token | `theme.py` actual | Mockup | Diferencia |
|---|---|---|---|
| Fondo ventana | `#1c1c20` | `#0a0b0d` | mucho más oscuro |
| Fondo panel | `#232327` | `#101216` | |
| Acento / clip actual | `#ff8a3d` | `#e8a33d` | naranja → ámbar |
| Texto | `#e4e4e4` | `#e6e9ee` | neutro → frío |
| Borde | `#333338` | `#262b33` | |
| Pick | `#3ddc84` | `#55c08a` | verde apagado |
| Reject | `#ff5566` | `#d4696c` | rojo apagado |
| Trim | `#4fd1e8` | `#6d8cf5` | cian → azul violeta |
| Destacado | — | `#7ee6b0` | no existe |

La paleta del mockup es **más oscura, más fría y menos saturada** en todo. Con
el layout perfecto y este `theme.py`, la app seguiría sin parecerse. Además
faltan tokens que el mockup usa y la app no tiene nombrados: cuatro niveles de
superficie, tres de texto, dos de línea, los anchos fijos (rail 200 px, columna
de herramientas 56 px, barra de título 36 px, barra de estado 24 px), los
radios (5/6/7/8) y la escala tipográfica (9 / 10.5 / 11 / 12.5 / 19 / 24).

### M2 — Arnés de comparación lado a lado

Un script en `scripts/comparar_con_mockup.py` que:

1. levanta el mockup HTML y lo captura a 1600×1000,
2. construye la `MainWindow` con datos de ejemplo equivalentes y la captura al
   mismo tamaño,
3. escribe un PNG con las dos, una al lado de la otra.

No se checan imágenes de referencia al repo: el mockup HTML ya está versionado
y se re-renderiza cuando haga falta. **La comparación tiene que ser barata para
que de verdad se haga.**

### M3 — Cada fase termina con comparación visual, no con tests verdes

Definición de terminado de toda fase que toque UI:

- los tests pasan, **y**
- se corrió el arnés de M2, **y**
- se miró la imagen resultante y se anotaron las diferencias contra el mockup, **y**
- las diferencias son intencionales y están escritas, o están arregladas.

"Se ve bien" no cierra una fase. La imagen sí.

### M4 — Lista de ejecución explícita

Todo lo del diseño viejo que tiene que morir está listado abajo (§3), cada
cosa asignada a una fase. **Una fase no está terminada si su parte de la lista
sigue viva.** Al final del plan la lista queda vacía; si algo sigue ahí, el
rediseño no terminó.

### M5 — El esqueleto antes que las funciones

El orden natural (arreglar bugs → agregar funciones → acomodar el layout) es
exactamente la trampa: consolida la estructura vieja. Acá va al revés: **la
Fase 2 reconstruye el layout completo y porta lo que ya funciona**, y recién
después se agregan funciones nuevas, ya dentro de la estructura correcta.

Corolario: **cada fase deja la app funcionando.** Nunca se vive en el estado
híbrido.

## 3. Lista de ejecución (lo viejo que debe morir)

| Qué | Dónde | Muere en |
|---|---|---|
| `RoomConfigDialog` y su exigencia en `arrancar()` | `ui/room_config_dialog.py`, `app.py:95` | F3 |
| `CategoryTree` completo | `category_path.py` | F3 |
| `pending_parent`, `resolve_subroom_key` | `keyboard.py` | F3 |
| `SUBROOM_CANDIDATES`, `_handle_subroom_key`, `subroom_banner` | `ui/main_window.py` | F3 |
| `REPEATABLE_ROOMS`, `set_count` | `rooms.py` | F3 |
| `legend_label` (la leyenda de una línea al pie) | `ui/main_window.py:232` | F2 |
| `ingest_list` + `ingest_title_label` ("Material importado") | `ui/main_window.py:209` | F2 |
| `inspector_panel` (los 200 px fijos a la derecha) | `ui/main_window.py:294` | F2 |
| `scrub_time_label` como banda propia | `ui/main_window.py:223` | F2 |
| `top_bar` actual | `ui/main_window.py:255` | F2 |
| `Filmstrip` con `setFixedHeight(220)` y tiles apaisadas | `ui/filmstrip.py:21,314` | F2 / F4 |
| Todos los colores literales fuera de `theme.py` | varios | F1 |
| `orientacion="horizontal"` hardcodeado | `ui/main_window.py:710` | F5 |
| Mención de `Ctrl+Z` sin implementación | `ui/main_window.py:53` | F6 |

## 4. Fases

### F0 — Spike del overlay sobre `QOpenGLWidget` — ✅ HECHO 2026-08-08

**Resultado: funciona. Se sigue el camino cómodo (widgets normales como hijos
del `VideoWidget`); no hace falta el plan B.**

Cómo se probó: `VideoWidget` reproduciendo material real de
`sample-media/clips/` (HEVC 10-bit de la FX30, clip vertical), con cuatro
overlays como hijos directos —un `QLabel` con fondo `rgba(...,60)`, un scrim
con `qlineargradient` de transparente a negro, un timecode con fondo
transparente y una `ScrubBar` completa— capturado con `grab()` dos veces
mientras reproducía (posiciones 2.19 s y 3.69 s).

Lo que quedó demostrado:

- Los widgets se componen **encima** del contenido de OpenGL.
- El alfa se mezcla **contra los pixeles del video**, no contra negro: con
  `rgba(10,12,15,60)` la imagen se ve claramente a través. Esto es lo que
  hace posibles los scrims del mockup.
- Los degradados de QSS funcionan como overlay.
- La `ScrubBar` —widget de `QPainter`— funciona como hijo del `VideoWidget`
  sin tocar su `paintEvent`.
- Dos capturas en momentos distintos con el video corriendo salen ambas
  correctas: no desaparece ni parpadea.

**Receta para la F2, encontrada en el spike:** un widget de `QPainter` puesto
sobre el `VideoWidget` pinta fondo **opaco** en el área que no dibuja, y tapa
el video. Se arregla con
`widget.setAttribute(Qt.WA_TranslucentBackground, True)`. Sin esa bandera la
`ScrubBar` se comía una franja del video; con ella, la imagen se ve entre las
marcas. **Aplicar a todo overlay de dibujo propio.**

Salvedad honesta: la verificación es con `grab()`, que es el composite del
propio Qt, no una foto de la pantalla. `screencapture` falló por falta de
permiso de Grabación de Pantalla. `grab()` ya detectó en este proyecto un
problema real de GL (el caso `wid` de agosto), así que se considera evidencia
suficiente; si más adelante se concede el permiso, conviene repetir la
comprobación contra la pantalla real.

### F1 — Tokens y arnés

- Reescribir `ui/theme.py` con los tokens del mockup (M1): superficies, texto,
  líneas, estado (incluido `STAR_COLOR`), paleta de cuartos de 9, anchos fijos,
  radios, escala tipográfica.
- Barrer los colores literales que hoy viven fuera de `theme.py`.
- Escribir `scripts/comparar_con_mockup.py` (M2).
- **Terminado cuando** el arnés corre y produce la comparación, y `grep` no
  encuentra colores hexadecimales fuera de `theme.py`.

Ojo: al terminar F1 la app se va a ver **peor** que antes — paleta nueva sobre
layout viejo. Es esperado y dura una fase.

### F2 — El esqueleto completo *(la fase decisiva)*

Se reconstruye la ventana con la estructura del mockup y se porta a ella
**todo lo que ya funciona**: clasificación 1–9, in/out, reproducción, calidad,
scrub bar, selección múltiple, asignación en lote, autoguardado, exportar.

- Estructura: barra de título 36 px → cuerpo de tres columnas (rail 200 /
  video / columna de herramientas 56 / hoja de contactos) → barra de estado
  24 px. **Cero bandas horizontales** fuera de esas dos.
- El chrome del video pasa a overlay (nombre, índice en la cola, calidad,
  velocidad, badges, timecode, scrub bar).
- La `ScrubBar` se muda encima del video. **Sigue siendo `QPainter` en
  `paintEvent`** — la decisión de arquitectura de `CLAUDE.md` no se toca —
  y lleva `WA_TranslucentBackground` por lo que encontró la F0.
- Se borra en el mismo commit: `legend_label`, `ingest_list`,
  `inspector_panel`, `scrub_time_label`, `top_bar`, el `Filmstrip` viejo.
- **Terminado cuando** la comparación lado a lado muestra la misma estructura
  y las mismas proporciones que el mockup, y la app hace todo lo que hacía
  antes. Medida objetiva: **el video vertical mide ~529 px de ancho en una
  ventana de 1600×1000** (hoy mide 328).

Es la fase más grande y no se puede partir sin caer en el estado híbrido.

### F3 — Cuartos planos

- Quitar subcuartos de raíz (toda su parte de la lista de ejecución).
- Rail de cuartos editable en vivo: renombrar, reordenar, borrar.
- Quitar el diálogo de configuración inicial; la app abre lista para trabajar.
- `categoria_path` **se queda como lista de un elemento**: el contrato del
  manifest y el plugin no se tocan.
- **Terminado cuando** presionar `3` con "Recámara 1" clasifica y avanza, y
  `category_path.py` ya no existe.

### F4 — Miniaturas verticales y agrupación

- Tiles de proporción variable según la orientación real del clip.
- Agrupación por cuarto con encabezado pegajoso.
- Portada al 25% del clip (hoy es el frame del medio).
- **Terminado cuando** un clip vertical se ve vertical y legible en la hoja.

### F5 — Los datos que faltan

- Dejar de descartar `width`/`height`/`rotation` en `_load_clips_from_ingest`.
- Conectar `match_proxies()` a la importación.
- Orientación del manifest derivada del material, no hardcodeada.
- **Terminado cuando** el badge de vertical, el filtro de verticales y el chip
  de proxy muestran datos reales.

### F6 — Deshacer de verdad

- Pila de undo con acciones agrupadas (una pincelada = una entrada).
- Historial visible en el rail izquierdo con revertir por fila.
- `Ctrl+Z` registrado de verdad.
- **Terminado cuando** deshacer una asignación en lote de 6 clips es una sola
  acción.

### F7 — Filtros como cola de navegación

- Barra de filtros de dos grupos (Mostrar / Estado).
- `←/→` recorren **solo el conjunto filtrado**.
- Indicador "N de M en la cola" y badge de sin clasificar clickeable.

### F8 — Reproducción rápida

Autoplay al cambiar de clip, velocidad 1×/2×/4×, arranque al 25%, precarga del
siguiente clip, `,`/`.` frame por frame.

### F9 — El resto del teclado

Flags en lote, `S` igual al anterior, estado destacado (`⇧P`), paleta `⏎` para
buscar y crear cuartos, `F` solo video.

### F10 — Modo hoja y pincel

`⇥` para alternar, hoja a pantalla completa con 7 columnas, pincel de cuarto
con los cinco requisitos de DECISIONES.md, `+`/`−` para el tamaño de miniatura.

### F11 — Barrido final

- La lista de ejecución (§3) tiene que estar vacía.
- Comparación final lado a lado de las dos pantallas.
- Cualquier diferencia contra el mockup queda escrita y justificada, o
  arreglada.

## 5. Reglas de la partida

- **El mockup manda en lo visual; DECISIONES.md manda en el comportamiento.**
  Si se contradicen, se le pregunta a Bruno; no se elige en silencio.
- **"Mejor que el mockup" está permitido y bienvenido**, pero se avisa. La
  scrub bar actual, por ejemplo, ya tiene marcas de tiempo adaptativas que el
  mockup no dibuja: eso se conserva, no se degrada para parecerse.
- **Nada de features no acordadas.** Si aparece una idea buena a mitad de una
  fase, se anota y se decide aparte.
- **Ninguna fase cierra sin haber mirado una imagen.**
