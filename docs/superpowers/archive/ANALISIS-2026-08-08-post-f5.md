# Punto de control post-F5 — 2026-08-08

Tercer punto de control del rediseño, después de la F4 y la F5. Reemplaza a
[`ANALISIS-2026-08-08-post-f3.md`](ANALISIS-2026-08-08-post-f3.md), que queda
como registro.

**La pregunta sigue siendo la misma: ¿qué falta que nadie tiene asignado?**

## Cómo se hizo

Cuatro barridos mecánicos, ninguno de memoria:

1. **Las clases del mockup contra el código.** Una por una, con `grep`.
2. **La tabla de teclado de `DECISIONES.md`** contra los atajos que
   `_install_shortcuts` registra de verdad.
3. **Promesas rotas**: todo texto de la app que nombra una tecla, contra los
   atajos que existen.
4. **Señales declaradas contra señales conectadas.** Detector nuevo, y el que
   encontró lo peor de esta ronda.

---

## 1. El hallazgo: un botón que no hace absolutamente nada

**`Cuartos ⌘R`, en la barra de título, está muerto por los dos lados.**

- Su señal `rooms_requested` **no la escucha nadie**: `grep` da cero
  conexiones. Hacerle click no hace nada.
- El `⌘R` que anuncia **no está registrado** como atajo.

Lleva ahí desde la F2 y nadie lo notó porque en las comparaciones se ve igual
que un botón que sí funciona. Es peor que una promesa rota: es un control
completo que existe solo de adorno.

**Lo que le pasó**: en la F2 tenía sentido —abría la configuración de
cuartos—. La **F3 le quitó el trabajo**: los cuartos se editan en el rail, en
el lugar, y se crean sobre la marcha. El botón quedó sin destinatario y
sobrevivió porque está dibujado en el mockup.

**✅ Resuelto el mismo día.** Bruno eligió que `⌘R` lleve el foco al rail.
Ahora el botón hace eso y, con una fila enfocada: `↑`/`↓` mueven el foco,
`⌥↑`/`⌥↓` reordenan —que es cambiar la tecla, por eso lleva modificador—, `⏎`
renombra y `⌫` elimina. Los cuartos se manejan sin tocar el mouse.

### Y `⌘E` también se anuncia sin existir

El botón `Exportar a Premiere ⌘E` **sí funciona** con click, pero el atajo no
está registrado. A diferencia de `⌘R`, este no tiene ninguna duda: la acción
existe, es una línea. Va como arreglo directo.

---

## 2. Código muerto

| Qué | Por qué está muerto |
|---|---|
| ~~`ClipSheet._grupos`~~ | Se escribía en `_construir_filtros` y no se leía nunca. ✅ borrado |
| ~~`filters.MOSTRAR` y `filters.ESTADO`~~ | Catálogo que ningún módulo importaba. ✅ borrados; los valores válidos quedan documentados en el propio `FilterState` |
| `theme.STAR_COLOR` | Sin usar, **pero con dueño**: es el color del estado «destacado» que construye la F7. No se toca |

`ClipSheet.group_titles` y `ClipThumbnail.path` tampoco se leen desde `src/`,
pero **no son código muerto**: los usan los tests para verificar la Regla 1 de
`ClipSheet`, que tiene detrás un bug real e intermitente de miniaturas. Ya está
anotado en el propio archivo.

---

## 3. Estado del mockup, clase por clase

**Hecho** (F1 a F5): barra de título, rail con progreso, leyenda de colores,
cuartos con tecla, `+ Nuevo cuarto`, historial con revertir, video con sus
overlays, badges de cuarto y estado, columna de herramientas con rango, estado
y deshacer, hoja agrupada con línea de grupo, tarjetas completas —número,
duración, glifo, rango in/out, rayado, palomita—, buscador, barra de filtros
de dos grupos, chip de cola, barra de estado con aviso clickeable.

**Falta**, todo con dueño:

| Elemento del mockup | Fase |
|---|---|
| `.modeswitch` — el selector `Clip / Hoja` | F8 |
| `.same` / `.samecap` — la fila `S` «igual al clip anterior» | F7 |
| `.palette` — la paleta `⏎` | F7 |
| `.badge.star` y el indicador `★` de la columna | F7 |
| `.fchip` de destacados | F7 |
| `.scrub` con banda llena, `.rangepill`, `.v-keys`, `.fr` | F6 |
| `.toolhint` — `espacio ▶ ‖` | F6 |
| `.badge.auto`, `siguiente clip precargado ✓` | F6 |
| `.hoverbar` / `.hovertc` — al escrubear una miniatura | F8 |
| `.batch` — barra de selección múltiple | F8 |
| `.zoomstep` — `+` / `−` | F8 |
| `.brushcursor` y compañía — el pincel | F8 |
| `.badge` de proxy y `proxies 1080p · 128/128` | F9 |
| `.fdiv` — el separador entre grupos de filtros | **no aplica** |
| `.viewtoggle` — los dos iconos de vista | **descartado** |

`.fdiv` desapareció por una razón: los filtros van en **dos renglones**, uno
por grupo, y ahí el separador vertical no tiene qué separar. Está explicado en
el resultado de la F5.

---

## 4. Estado del teclado

| Tecla | Estado |
|---|---|
| `espacio`, `1`–`9`, `P`, `X`, `I`, `O`, `U` | ✅ |
| `←` `→` **sobre la cola filtrada** | ✅ desde la F5 |
| `1`–`9` **asignan y avanzan** | ✅ desde la F5 |
| `⌘Z`, `⌘A` | ✅ registrados — **falta probarlos con la tecla física** |
| `⌘E` exportar | ✅ resuelto |
| `⌘R` cuartos → foco al rail | ✅ resuelto |
| En el rail: `↑`/`↓`, `⌥↑`/`⌥↓`, `⏎`, `⌫` | ✅ nuevo |
| `,` `.` frame por frame | ❌ F6 |
| `S`, `⏎`, `⇧P`, `F`, `P`/`X` a neutral | ❌ F7 |
| `⇥`, `esc`, doble click, `+`/`−`, marquesina, pincel | ❌ F8 |

---

## 5. La lista de ejecución

**Un solo renglón vivo** en todo el rediseño:

| Qué | Dónde | Muere en |
|---|---|---|
| `orientacion="horizontal"` hardcodeado | `ui/main_window.py:866` | F9 |

---

## 6. Lo que quedó decidido

**`Cuartos ⌘R` lleva el foco al rail** (decidido con Bruno, 2026-08-08). Se
descartó borrarlo —el mockup lo dibuja y la acción es útil— y se descartó que
abriera la paleta `⏎` de la F7, porque serían dos teclas para lo mismo y
`DECISIONES.md` dice que menos atajos se aprenden más rápido. Además hacen
cosas distintas: la paleta **asigna** un cuarto a un clip; `⌘R` **administra**
la lista.

Queda pendiente escribirlo en la tabla de teclado de `DECISIONES.md` junto con
el resto de las teclas del rail.

---

## 7. Las fases que siguen

Orden **sin cambios**. La carga tampoco cambia respecto del análisis post-F3,
salvo lo que se movió de la F5:

- **F6 — Reproducción rápida.** Sigue siendo **la fase más grande**: autoplay,
  velocidad `1×/2×/4×`, arranque al 25%, precarga, `,`/`.`, la forma de la
  barra de reproducción, la pastilla de rango, el renglón de teclas, el
  contador `f 293`, el `espacio ▶ ‖`, el badge `▶ auto` y el aviso de precarga
  en la barra de estado.
- **F7 — Resto del teclado.** `S` con su fila fija, paleta `⏎`, destacado
  `⇧P` (badge, indicador, glifo en la tarjeta y chip en la leyenda y en los
  filtros), `F`, y que `P`/`X` vuelvan a neutral.
- **F8 — Modo hoja y pincel.** `⇥`, hoja a pantalla completa, pincel,
  `+`/`−`, marquesina, `esc`, doble click, transición, barrita al escrubear,
  barra de selección múltiple y la portada al 25%.
- **F9 — Proxies y orientación.**
- **F10 — Barrido final.**

## 8. Lo que este barrido enseñó

- **Las señales sin conectar son un detector nuevo y muy bueno.** En una app
  de widgets, una señal que nadie escucha es un control muerto — y a
  diferencia de una función sin llamar, se ve perfecta en una captura. Vale la
  pena repetirlo en cada punto de control.
- **Cuando una fase le quita el trabajo a un control, hay que borrar el
  control.** La F3 dejó `Cuartos` sin destinatario y el botón siguió ahí tres
  fases. El síntoma estaba disponible desde entonces: su señal ya no tenía
  quien la escuchara.

---

## 9. Revisión de la F1 a la F3 — 2026-08-08

Mismo método: medir y ejecutar, no leer. La F1 salió limpia; la F2 tenía un
bug que la F5 agravó.

### La F1 está intacta, pero su candado tenía un hueco

Los catorce colores y la paleta de nueve coinciden **exactamente** con el
`:root` del mockup. Pero los tests comparaban contra hexadecimales **copiados
a mano**: si alguien cambiaba un token y su test, la deriva pasaba sin que
nadie se enterara. Ahora hay un test que lee el `:root` del mockup y compara
contra el tema — la fuente de verdad es el mockup, no una copia.

### La F2: un clip horizontal inflaba la ventana a 2653 px

`_resize_video_stage` calcula el ancho del video restando `SHEET_MIN_WIDTH`
(340). Pero el mínimo real de la hoja es mucho mayor —su encabezado tiene
título, buscador, chip de cola y dos filas de filtros—, así que el video pedía
más ancho del que había: la ventana crecía, eso agrandaba el máximo, el video
crecía otra vez. **Tres pasadas y la ventana pasaba de 1600 a 2653 px.**

Ya estaba mal desde la F2 —el encabezado siempre pidió más de 340— y la barra
de filtros de la F5 lo volvió grave.

Dos arreglos:

1. El cálculo usa el **mínimo real** de la hoja, no la constante.
2. El hint del encabezado —decorativo, y el que más ancho exigía— pasa a
   elidirse y a tener mínimo cero. La hoja puede bajar a ~470 px, así que el
   video horizontal llega a 872.

### Y al angostarse la hoja, las tarjetas quedaban cortadas

Consecuencia del anterior, y solo visible una vez arreglado: `_relayout`
medía `_content.width()`, cuyo **mínimo lo fijan las propias tarjetas**. Al
angostarse la hoja, el contenido se quedaba con el ancho de antes y se volvían
a calcular las mismas columnas; la última quedaba cortada y, con el scroll
horizontal apagado, no había forma de llegar a ella.

Ahora se mide el **viewport** del área de scroll, que es el espacio que de
verdad hay. Con un clip horizontal las tarjetas se reacomodan de cinco
columnas a dos, que es exactamente el «el layout se reacomoda y la pantalla
salta» que `DECISIONES.md` eligió a propósito.

### Lo que esto enseñó

- **Un test puede fijar una suposición equivocada.** El de la F2 afirmaba que
  el video mide `ancho - rail - columna - SHEET_MIN_WIDTH`, que era justo la
  cuenta mal hecha. Pasaba en verde mientras la ventana se inflaba.
- **Los casos que el diseño menciona de pasada hay que probarlos igual.**
  `DECISIONES.md` dedica una sección entera a los clips horizontales y nadie
  los había ejecutado nunca.
