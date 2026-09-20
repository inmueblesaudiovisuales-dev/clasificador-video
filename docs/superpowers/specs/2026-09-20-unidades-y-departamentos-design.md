# Unidades y departamentos — diseño

*(Spec. Fecha: 2026-09-20. Sale del caso real de Bruno: dos casas modelo en
una misma colonia, resuelto hoy a mano con sufijos —`Cocina-A`, `Cocina-B`—.
Mockup aprobado en
`docs/superpowers/mockups/2026-09-20-unidades-y-departamentos/mockup.html`.)*

## 1. Qué es una unidad

Un nivel nuevo, **arriba de cuarto**: Casa A / Casa B, o Depto 1 / Depto 2.
Dentro de una unidad, los cuartos se repiten con su nombre normal —«Cocina»
existe una vez por unidad, sin chocar—.

**Es opcional, y por default el proyecto se comporta exactamente como hoy.**
Mientras Bruno no cree ninguna unidad, la paleta de cuartos, el rail, la
hoja y las carpetas de Premiere salen idénticos a como salen hoy — cero
fricción nueva para el 90% de sus proyectos, que son de una sola propiedad.
La unidad solo entra en juego desde que Bruno crea la primera.

## 2. Modelo de datos

`Clip.categoria_path` (`manifest.py:13`) ya es una lista pensada para ser
jerárquica — hoy siempre trae un solo elemento, `[cuarto]`. Unidad se suma
como un nivel real: `[unidad, cuarto, ...resto]` cuando el clip tiene
unidad asignada, `[cuarto]` cuando no la tiene (proyecto sin unidades, o
clip todavía no asignado a ninguna).

Un `UnitSelection` nuevo, hermano de `RoomSelection` (`rooms.py`) y con la
misma forma —lista plana y en orden, ese orden es la tecla 1-9, mismos
métodos (`add`, `rename`, `mover`, `remove`)—. Vive un nivel arriba:
`RoomSelection` sigue gobernando los cuartos, pero **una `RoomSelection` es
ahora por unidad** (el catálogo de cuartos de Casa A es independiente del de
Casa B — «Cocina» de una no es «Cocina» de la otra aunque se llamen igual).

## 3. Asignar: paleta de unidades

Pieza hermana de `RoomPalette` (`room_palette.py`), un nivel arriba, con su
propia tecla: **`⌘U`/`Ctrl+U`** — modificador, mismo criterio que `⌘R`
(`room_rail.focus_rooms`, `main_window.py:1212`) y por eso no compite con
escribir ni con `⏎`, que sigue siendo la paleta de cuartos. Mismo mecanismo
de buscar/crear que ya conoces.

**Diferencia clave con la paleta de cuartos**: elegir una unidad **no
asigna nada y no se cierra** — dice qué unidad estás usando y así se queda,
**activa**, hasta que elijas otra o cierres la paleta de unidades. A partir
de ahí, `⏎` (paleta de cuartos), los dígitos y `S` siguen actuando sobre el
cuarto exactamente igual que hoy, pero **la paleta de cuartos filtra a los
cuartos de la unidad activa** — «Cocina» de Casa A y «Cocina» de Casa B no
se mezclan ni se ofrecen juntas.

**Sin unidad activa** (proyecto sin unidades, o todavía no elegiste una):
la paleta de cuartos se comporta como hoy, con el catálogo plano de
siempre — no hay caso especial que mantener, es literalmente lo que ya
existe.

## 4. Reasignar en lote

Mismo patrón que ya existe para cuarto: `_bulk_target_indices`
(`main_window.py:1392`) decide el alcance (todos los seleccionados, o el
clip actual si no hay selección múltiple), y una función nueva
`_asignar_unidad` — análoga a `_asignar_cuarto` (`main_window.py:1516`) —
aplica la unidad a ese alcance. No hay menú contextual nuevo: se dispara
igual que hoy, seleccionas clips en la hoja y usas la paleta de unidades.

**Este es el camino de migración** para el proyecto actual de Bruno
(`Cocina-A`/`Cocina-B` a mano): crea las unidades «Casa A» y «Casa B», y
selecciona en la hoja los clips de cada sufijo para reasignarles la unidad
y el cuarto real, en lote. **Sin detección automática del patrón `-A`/`-B`**
— Bruno prefirió control manual sobre adivinar, y es una sola vez.

**Estado mixto, mientras dura la migración**: desde que existe la primera
unidad del proyecto, un clip con `categoria_path = [cuarto]` (todavía sin
migrar) se agrupa aparte, en un bloque **«Sin unidad»**, separado de los
grupos por unidad — ni mezclado adentro de una unidad ni repartido por la
hoja. Así se ven de un vistazo cuántos faltan y se seleccionan juntos para
migrarlos en lote (2026-09-20, decidido con Bruno). El bloque desaparece
solo cuando ya no queda ningún clip sin unidad.

## 5. Rail y hoja

Rail: banda de unidad (mockup, `.unit-header`) arriba de cada grupo de
cuartos — mismo patrón visual que ya usa la hoja para agrupar por bin, pero
un nivel más arriba. Hoja: banda de unidad (`.unit-band`) arriba de cada
grupo de cuartos, que a su vez agrupa como hoy.

**Orden**: unidad primero, cuarto adentro — mismo criterio que ya rige
`clip_sheet._orden_de_grupo` (`clip_sheet.py:2676`), con unidad como el
nivel más externo del agrupamiento. Sin unidad activa en el proyecto, el
agrupamiento es el de hoy (sin ese nivel extra).

## 6. Color

El mockup ya lo resuelve: el swatch de unidad es un **cuadro** de 10-12px
(`.unit-swatch`, `border-radius: 3px`), distinto en forma del swatch de
cuarto —una franja delgada de 3×13px— y del tratamiento de cámara —tinte al
18% detrás de un glifo, según `theme.py:51-60`—. Los tres canales (cuarto,
cámara, unidad) se distinguen por **tratamiento visual**, no solo por tinte,
que es el mismo criterio que ya separa cuarto de cámara.

`theme.py` suma `UNIT_PALETTE` — una paleta propia, del mismo espíritu
apagado que `ROOM_PALETTE` (no compite con verde/rojo/ámbar de estado), y
`unit_color(index)` con el mismo criterio de `room_color`: índice por
posición en las unidades activas, módulo el tamaño de la paleta.

## 7. Premiere / plugin UXP

Con `categoria_path = [unidad, cuarto, ...resto]`, el árbol destino pasa de
`02. Clip > 1. Cocina > ...` a `02. Clip > 1. Casa A > 1. Cocina > ...`.

Los tres módulos que hoy asumen que el cuarto vive en el índice fijo
`categoria_path[0]` / `camino[1]` tienen que generalizarse a **dos**
niveles en vez de uno:

- **`estructura.js::caminoDelClip`** (línea 53): hoy numera solo el
  segmento 0 con `conNumero`. Pasa a numerar segmento 0 (unidad) **y**
  segmento 1 (cuarto), cada uno con el orden de guía que le corresponda —
  el de la unidad, y el del cuarto dentro de esa unidad.
- **`marcaCamara.js`** (línea 33-43): hoy marca `[SONY]`/`[DRONE]` sobre
  `categoria_path[0]` asumiendo que es el cuarto. Pasa a marcar **ambos**
  niveles — la carpeta de unidad también lleva la marca combinada de las
  cámaras que tiene adentro (ya era una decisión tomada: «la carpeta de la
  unidad también debería llevar la marca de cámara»).
- **`numeroDeCuarto.js`** (`resolverCuarto`/`esElMismoCuarto`, línea
  38-39): mismo criterio, generalizado a operar sobre el segmento que le
  toque en vez de asumir que es siempre el primero.

Un proyecto **sin** unidades sigue mandando `categoria_path = [cuarto]` —
un solo segmento— y estos tres módulos, al ver una lista de longitud 1, se
comportan exactamente como hoy. No hay dos caminos de código que mantener:
es el mismo camino, con una lista más corta.

## 8. Fuera de alcance (explícito)

- **Nota en el clip** — feature aparte, omitida de esta ronda a pedido de
  Bruno.
- **Recorrido/guía de edición por unidad** — Bruno: «omite la guía de
  edición, ahorita ni jala bien». No se toca nada de `estructura.js`/
  `secuencia.js` relacionado a la guía; cuando la guía en sí se arregle,
  extenderla a unidades es una spec aparte.
- **Migración automática** del sufijo `-A`/`-B` — decidido manual (§4).
- **Menú contextual de unidad** — la reasignación en lote usa selección +
  paleta, no un menú nuevo (§4).
