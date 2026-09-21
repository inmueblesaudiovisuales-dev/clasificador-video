# Mover cuartos entre unidades — diseño

*(Spec. Fecha: 2026-09-21. Sale de
`docs/superpowers/HANDOFF-2026-09-21-diseno-mover-cuartos-a-unidad.md` y del
pedido de Bruno: "necesitamos un diseño fácil de usar, arrastrable,
seleccionar los cuartos directamente y ponerlos en unidades […] elegante y
profesional". Mockups aprobados en
`.superpowers/brainstorm/19753-1789998691/content/` — `rail-base.html`,
`rail-arrastre.html`, `dialogo-choque.html` — no viven en el repo por
convención del companion visual; describirlos aquí es suficiente para
implementar.)*

## 1. El caso que resuelve

Bruno ya clasificó `Cocina-A`/`Cocina-B` a mano y quiere pasarlos a las
unidades reales `Casa A`/`Casa B` (spec
`docs/superpowers/specs/2026-09-20-unidades-y-departamentos-design.md`).
Hoy el único camino es seleccionar en la hoja, clip por clip, todos los de
ese cuarto y usar `⌘U` — indirecto, porque Bruno piensa en CUARTOS, no en
listas de clips. Este spec resuelve el mismo caso al nivel correcto:
arrastrar el cuarto completo en el rail.

## 2. Crear unidades sin atajo

Un botón "**+**" fijo arriba del rail, junto al rótulo "Unidades & cuartos"
(mockup `rail-base.html`). Al apretarlo, pide el nombre de la unidad nueva
igual que "Crear unidad «cas»" ya hace hoy desde la paleta (`⌘U`) — mismo
método (`UnitSelection.add`), un segundo camino hacia él para quien no se
acuerda del atajo. La paleta sigue existiendo igual que hoy; esto no la
reemplaza, la complementa.

## 3. Colapsar unidades

Cada banda de unidad (`_BandaDeUnidad`, `room_rail.py:424`) suma una
flecha `▾`/`▸` a la izquierda de su swatch. Un clic esconde/muestra los
cuartos de esa unidad — la banda se queda, con su conteo total, para que
Bruno sepa que ahí sigue habiendo algo.

**Se recuerda por proyecto**: mismo criterio que `agrupar_por_cuarto` y
`modo_horizontal` (`proyecto.py:171-178`) — una preferencia de VISTA que
depende del shooting, no del día. Se suma `unidades_colapsadas: list[str]`
al documento del proyecto (`proyecto.a_dict`), vacío en todo proyecto que
nunca colapsa nada.

**Se abre sola cuando le llega un cuarto**, sea por arrastre (§5) o porque
Bruno asignó un clip con esa unidad activa (`⌘U`, spec 2026-09-20 §3): así
confirma de un vistazo que el cuarto llegó a donde quería, en vez de
soltar y no ver qué pasó.

## 4. Seleccionar varios cuartos

`⌘-clic`/`Ctrl-clic` sobre una fila (`_FilaCuarto`) sí la agrega a la
selección sin quitar las demás — mismo estándar que seleccionar archivos en
Finder. La selección **no cruza unidades**: hacer ⌘-clic en un cuarto de
otra unidad reemplaza la selección por ese cuarto solo, porque arrastrar
cuartos de dos unidades distintas a la vez no tiene un destino que tenga
sentido (¿cuál es "la unidad de origen" del grupo?). Clic normal (sin
modificador) limpia la selección y dejas ese cuarto solo, como hoy.

Visualmente: fila seleccionada con el mismo tratamiento de "fila enfocada"
que ya existe (`.active` / fondo `bg-surface-2`) más un borde delgado del
color de acento, para distinguir "esta es la que tiene el foco de teclado"
de "estas son las que arrastro".

## 5. Arrastrar a otra unidad

Arrancar el arrastre desde cualquier fila seleccionada mueve **todo el
grupo seleccionado** (uno solo, si no hay selección múltiple — el caso de
hoy sigue intacto). Mismo mecanismo `QDrag`/`MIME_CUARTO` que ya existe
(`_FilaCuarto.mouseMoveEvent`, `room_rail.py:258`), con el MIME cargando la
lista de nombres en vez de uno solo.

**Mientras arrastras**: un globo junto al cursor muestra los nombres que
llevas (mockup `rail-arrastre.html`) — "Cocina, Comedor" o "Cocina +2" si
son más de dos. Las filas de origen quedan semi-transparentes en su lugar
mientras dura el arrastre.

**Soltar**: cualquier punto dentro de la banda de la unidad destino sirve
— no hace falta acertarle a una fila. La banda se resalta completa
mientras el mouse está encima (borde punteado + tinte del color de esa
unidad). Esto reemplaza el límite actual de `soltar_cuarto`
(`room_rail.py:850-898`), que hoy ignora en silencio un drop fuera de la
banda de origen — ese comentario y ese `return` desaparecen, sustituidos
por la lógica de move-entre-unidades de este spec. **Soltar dentro de la
misma banda de origen sigue siendo reordenar** (comportamiento de hoy,
intacto) — mover-entre-unidades es soltar en la banda de OTRA unidad.

**Qué se mueve**: el cuarto completo, con todos sus clips ya clasificados
— es decir, se reescribe `categoria_path` de cada clip de ese cuarto para
que su primer elemento sea la unidad destino (mismo campo y mecanismo que
ya usa `_asignar_unidad`, spec 2026-09-20 §4, aplicado en lote a todos los
clips del cuarto en vez de a una selección de la hoja).

## 6. Choque de nombre

Si el nombre del cuarto que sueltas ya existe en la unidad destino,
aparece un diálogo (mockup `dialogo-choque.html`) con tres opciones y el
conteo de clips de cada lado para decidir con contexto:

- **Fusionar** — los clips del cuarto arrastrado se suman al cuarto que ya
  existía en el destino; queda un solo cuarto con la unión.
- **Renombrar** — se mueve completo como "`<nombre> 2`" (o el primer
  número libre si "`<nombre> 2`" también existe), sin tocar el cuarto que
  ya estaba ahí. **Es la opción resaltada por default** — no mezcla datos
  de dos cuartos capturados por separado sin que Bruno lo pida a propósito.
- **Cancelar** — no se mueve nada; el cuarto se queda en su unidad de
  origen como estaba.

**Con varios cuartos arrastrados a la vez**: los que no chocan se mueven de
inmediato, sin esperar. Por cada uno que sí choca aparece su propio
diálogo, uno a la vez (no un diálogo con varias filas) — mismo criterio que
ya usa la revisión de guía de edición para reportar UN problema a la vez
en vez de una lista (spec 2026-09-14, `guia.py`).

## 7. Deshacer

Mover un cuarto (y una fusión, si esa fue la resolución del choque) se
registra en `History` (`history.py`) igual que renombrar o borrar un
cuarto — una entrada nueva, hermana de `renombrar_cuarto`
(`history.py:104`). `⌘Z` la revierte completa: si fue una fusión, separa
de nuevo los clips que se juntaron; si fue un simple move, regresa el
cuarto a su unidad de origen. No hace falta ningún flujo especial para
"corregir un error de arrastre" más allá de esto — o `⌘Z`, o arrastrar de
nuevo a la unidad correcta, que es el mismo gesto que ya usaste.

## 8. Alcance de esta versión

Vive **solo en el rail**. La hoja de contactos ya tiene sus propias bandas
de unidad (`.unit-band`) pero arrastrar cuartos ahí queda fuera de este
spec — el caso real de Bruno (migrar cuartos ya hechos) se resuelve entero
desde el rail, y sumarlo a la hoja es trabajo aparte si hace falta después.

## 9. Testing

- `UnitSelection`/`rooms.py`: mover un cuarto (con clips) de una unidad a
  otra, sin choque.
- Choque de nombre: las tres resoluciones (fusionar, renombrar,
  cancelar), y el caso mixto (algunos chocan, otros no, dentro del mismo
  arrastre de grupo).
- `RoomRail`: selección con ⌘-clic dentro de una unidad, y que ⌘-clic en
  otra unidad reemplaza la selección en vez de sumarse.
- `soltar_cuarto`: drop en la propia banda sigue reordenando; drop en
  banda ajena dispara el move; drop fuera de toda banda no hace nada
  (mismo criterio de "no adivinar" que ya rige hoy).
- Colapsar/expandir: se guarda en `unidades_colapsadas`, sobrevive a
  cerrar y reabrir el proyecto, y se auto-expande al recibir un cuarto.
- `History`: deshacer un move simple y deshacer una fusión, cada uno
  revierte exactamente lo que hizo.
