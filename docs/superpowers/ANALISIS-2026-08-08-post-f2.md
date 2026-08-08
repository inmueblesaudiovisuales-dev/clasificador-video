# Análisis post-F2: la app contra el mockup — 2026-08-08

> **Superado por [`ANALISIS-2026-08-08-post-f3.md`](ANALISIS-2026-08-08-post-f3.md)**,
> el punto de control hecho después de la F2.1 y la F3. Este documento queda
> como registro de qué se arregló y por qué; para saber **qué falta hoy**, ir al
> otro.

Punto de control obligatorio del
[plan maestro](plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md): rehacer el
análisis sobre el código nuevo antes de escribir el detalle de la F3.

Reemplaza a [`ANALISIS-2026-08-08-app-actual-vs-mockup.md`](archive/ANALISIS-2026-08-08-app-actual-vs-mockup.md),
que describía la app anterior al rediseño y quedó archivado.

**Cómo se hizo**: lectura del código nuevo (7 widgets creados en la F2), el
arnés `scripts/comparar_con_mockup.py` a 1600×1000, y recortes ampliados de
regiones equivalentes de las dos mitades —rail y hoja de contactos— para
comparar de cerca en vez de juzgar desde la vista general.

---

## 1. Lo que la F2 dejó bien

Contra el mockup, verificado en la comparación lado a lado:

| | Estado |
|---|---|
| Tres filas y ninguna más | ✅ verificado por test (`layout().count() == 3`) |
| Barra de título 36 px / barra de estado 24 px | ✅ |
| Rail 200 px / columna de estado 56 px | ✅ |
| **Video vertical de 529 px** en 1600×1000 (antes 328) | ✅ verificado por test |
| Cero franjas negras alrededor del video | ✅ |
| Controles flotando sobre el video | ✅ |
| Paleta idéntica al mockup, sin colores sueltos | ✅ verificado por test |
| Rail: progreso, barra segmentada, cuartos con tecla y color | ✅ muy cerca del mockup |
| Décimo cuarto sin tecla numérica | ✅ |
| Hoja agrupada por cuarto, sin clasificar primero | ✅ |
| Tarjetas con la proporción real del clip | ✅ |
| Scrub de miniatura con el mouse | ✅ conservado |
| Selección múltiple, asignación en lote, autoguardado | ✅ conservado |

> **Estado al 2026-08-08, tras implementar la F2.1** (commit `00e5d9d`): las
> §2, §3 y §4 de este documento están **resueltas**. Lo que quedó distinto del
> mockup a propósito está en la §8, al final, con su fase. La §5 (lista de
> ejecución) quedó actualizada: sus dos renglones de la F2.1 están tachados.

## 2. La regresión: las tarjetas perdieron información

**El hallazgo importante de este análisis.** La `ClipCard` muestra únicamente
la miniatura. Comparando los recortes ampliados:

| Elemento | Mockup | App vieja | App nueva |
|---|---|---|---|
| Miniatura con proporción real | ✅ | ❌ (tile apaisada fija) | ✅ |
| Número de clip (`093`) | ✅ | ❌ | ❌ |
| Duración (`0:19`) | ✅ | ❌ | ❌ |
| Glifo de pick/reject (`P` / `X`) | ✅ | parcial (color de borde) | parcial (color de borde) |
| Barra de rango in/out | ✅ | ✅ | ❌ **perdido** |
| Franja rayada de "sin clasificar" | ✅ | ❌ | ❌ |
| Palomita de selección | ✅ | ❌ (solo lavado de color) | ❌ (solo lavado) |
| Franja de color del cuarto | ✅ | ✅ | ✅ |

Dos síntomas confirman que fue un descuido, no una decisión:

1. **`ClipThumbnail` carga `in_frame`, `out_frame` y `duration_frames`, y
   `clip_sheet.py` no lee ninguno de los tres.** `MainWindow._refresh_sheet`
   los sigue calculando y pasando; se tiran en silencio.
2. **`RANGE_TRACK_COLOR` y `FLAG_NONE_COLOR` quedaron sin usar** en todo el
   proyecto: eran justo los tokens de la barra de rango y del texto "sin
   marca" que la tarjeta vieja pintaba.

Esto importa más de lo que parece: leer el estado de un vistazo es la razón
de ser de la hoja de contactos. Sin número de clip no se puede hablar de un
clip; sin duración no se sabe cuál es el largo; sin barra de rango no se ve
qué clips ya tienen in/out marcado —que es exactamente lo que el filtro
"Sin in/out" de la F5 va a querer mostrar—.

**Recomendación: arreglarlo antes de seguir, como cierre de la F2 y no como
fase nueva.** Es una regresión introducida por el rediseño, no una función
pendiente, y las fases siguientes se apoyan en ella.

## 3. Diferencias menores contra el mockup

Detectadas en los recortes ampliados. Ninguna es estructural.

| Diferencia | Detalle |
|---|---|
| **La leyenda del rail se desborda** | `● 41 picks ● 9 rejects ● 12 sin clasificar` no entra en 200 px y se corta. El mockup usa etiquetas cortas: `6 dest. · 41 · 9 · 12` |
| **Los puntos de la leyenda son todos grises** | En el mockup llevan el color de su estado (verde, rojo, gris). Es información tirada |
| **`⏎ buscar` va como texto plano** | En el mockup el `⏎` va dentro de un keycap, igual que las teclas de cuarto |
| **El encabezado de grupo no tiene la línea** | El mockup separa `SIN CLASIFICAR 12` del resto con una línea fina que ocupa el ancho sobrante |
| **Los badges sobre el video son una sola etiqueta** | El mockup tiene dos: cuarto y estado, cada uno con su color. La app los junta en gris |

## 4. Límites del arnés que conviene arreglar

**El área de video sale negra.** El doble de mpv no dibuja, así que la
comparación no permite juzgar el contraste de los overlays contra una imagen
real — que es justamente lo que la F0 validó y lo que más riesgo tiene de
verse mal en uso. Vale la pena que `_datos_de_ejemplo` pinte un frame
sintético detrás.

**La barra de estado sale sin ruta** porque no hubo importación. Poner una
ruta de ejemplo la haría comparable.

## 5. Lista de ejecución actualizada

Lo que quedó del plan maestro, más lo que la F2 dejó provisional.

| Qué | Dónde | Muere en |
|---|---|---|
| ~~`RoomConfigDialog` y su exigencia en `arrancar()`~~ | ~~`ui/room_config_dialog.py`, `app.py`~~ | ✅ F3 |
| ~~`CategoryTree` completo~~ | ~~`category_path.py`~~ | ✅ F3 |
| ~~`pending_parent`, `resolve_subroom_key`~~ | ~~`keyboard.py`~~ | ✅ F3 |
| ~~`SUBROOM_CANDIDATES`, `_handle_subroom_key`, `_update_subroom_banner`~~ | ~~`ui/main_window.py`~~ | ✅ F3 |
| ~~`RoomRail.subroom_banner`~~ | ~~`ui/room_rail.py`~~ | ✅ F3 |
| ~~`REPEATABLE_ROOMS`, `set_count`~~ | ~~`rooms.py`~~ | ✅ F3 |
| `orientacion="horizontal"` hardcodeado | `ui/main_window.py` | **F9 — lo único que sigue vivo** |
| ~~Campos muertos de `ClipThumbnail`~~ | ~~`ui/clip_sheet.py`~~ | ✅ F2.1 |
| ~~`RANGE_TRACK_COLOR` y `FLAG_NONE_COLOR` sin usar~~ | ~~`ui/theme.py`~~ | ✅ F2.1 |

Ya vacío de la lista original: `legend_label`, `ingest_list`,
`ingest_title_label`, `inspector_panel`, `scrub_time_label`, `top_bar`,
`position_label`, `progress_label`, `unclassified_badge`, `quality_combo`,
`room_list_widget`, `import_button` suelto, `filmstrip.py` entero y los alias
de compatibilidad del tema.

## 6. Orden revisado de las fases

Cambia respecto de lo escrito antes de implementar:

- ✅ **F2.1 — Cerrar la regresión de las tarjetas** *(hecha, commit `00e5d9d`)*.
  Número de clip, duración, glifo de estado, barra de rango, rayado de sin
  clasificar y palomita de selección. Más las cinco diferencias menores de la
  §3 y el frame sintético del arnés. Es corta y desbloquea el juicio visual de
  todo lo que sigue.
- ✅ **F3 — Cuartos planos.** *(hecha, commit `7eab98b`.)* Dos decisiones que
  el mockup no cubría, tomadas con Bruno: el rail se edita con menú contextual
  y doble click, y la app abre con el rail vacío.
- **F4 — Deshacer con historial visible.** Sin cambios.
- **F5 — Filtros como cola.** Sin cambios, pero ahora se apoya en la barra de
  rango de la F2.1 para el filtro "Sin in/out".
- **F6 — Reproducción rápida.** Sin cambios.
- **F7 — Resto del teclado.** Sin cambios.
- **F8 — Modo hoja y pincel.** Sin cambios.
- **F9 — Proxies y orientación del manifest.** Sin cambios.
- **F10 — Barrido final.** Sin cambios.

## 7. Lo que aprendí de la F2, para las fases que siguen

- **Reescribir un widget pierde detalles que el viejo tenía**, y los tests no
  lo detectan porque también se reescriben. La barra de rango sobrevivió tres
  auditorías del plan y murió en la implementación. Para las fases que
  reemplacen código: listar antes qué muestra el widget viejo, y comprobar
  uno por uno que sobrevivió.
- **Los campos de datos sin leer son el mejor detector de omisiones.** Un
  `dataclass` que carga tres campos que nadie usa es una función perdida.
  Vale la pena revisarlo al cerrar cada fase.
- **La comparación general no alcanza; hay que ampliar regiones.** La
  regresión de las tarjetas era invisible en la vista completa y obvia en el
  recorte. El arnés debería tener un modo de recorte.
  → **Hecho en la F2.1**: `--recorte X,Y,ANCHO,ALTO --zoom N`, que amplía la
  misma región de las dos mitades.

## 8. Cierre de la F2.1: lo que quedó distinto a propósito

Mirado con el arnés a 1600×1000 y con cuatro recortes ampliados —tarjetas,
rail, badges sobre el video y una captura directa de cuatro `ClipCard` con
estados distintos—. Lo que **no** coincide con el mockup, y por qué:

| Diferencia | Por qué se deja | Fase |
|---|---|---|
| El visor dice `87 / 128`; el mockup, `3 de 12 en la cola` | La cola filtrada no existe todavía | F5 |
| El nombre de archivo va en una pastilla; el mockup lo pone como texto plano sobre un scrim superior | Esa fila del mockup lleva además el control de velocidad, que no existe hasta la F6. Se rehace entera una sola vez, no dos | F6 |
| No hay barrita ni timecode al escrubear una miniatura | El scrub funciona desde la F2; falta su indicador visual | F8 |
| La leyenda del rail no tiene el chip `6 dest.` | No existe el estado «destacado» | F7 |
| Faltan los badges `▶ auto` y `Proxy 1080p` sobre el video | Autoplay y proxies | F6 / F9 |
| El texto del badge de cuarto sale algo menos saturado que el del mockup | El mockup eligió el suyo a mano para un solo cuarto; la app lo deriva para los nueve mezclando con blanco, y mezclar desatura. El **punto** sí va con el color puro, que es lo que hace que el badge se lea de color | — asumida |
| La barra de filtros y el historial del rail no existen | Son la F5 y la F4 | F4 / F5 |

Nada de esto es deriva: son huecos de fases que todavía no se construyeron.
