# Handoff — diseñar cómo meter cuartos ya hechos en una unidad

**Fecha:** 2026-09-21
**Rama:** `master` (directo, sin branches)
**Estado:** nada implementado todavía. Esto es contexto para arrancar un
`superpowers:brainstorming` en otra conversación — no hay spec ni plan.

---

## El pedido de Bruno, con sus palabras

> "esa es una pesima forma [el camino actual]. [...] necesitamos un diseño
> facil de usar, arrastrable, seleccionar los cuartos directamente y
> ponerlos en unidades, que sea muy facil de usar y entender como hacerlo.
> ahorita no es para nada intuitivo. necesito lo mas intuitivo posible pero
> que el diseño sea elegante y profesional."

Tres requisitos explícitos:
1. **Arrastrable** — drag and drop, no un menú ni un atajo.
2. **Selecciona el CUARTO directamente** — no clips sueltos en la hoja.
3. **Elegante y profesional** — esto entra al rediseño visual, no es un
   parche funcional nada más.

---

## Por qué el camino de hoy no sirve

Hoy, para meter cuartos ya clasificados dentro de una unidad (el caso de
migración: Bruno ya tiene `Cocina-A`/`Cocina-B` a mano y quiere pasarlos a
unidades de verdad), el único camino es:

1. Ir a la hoja de contactos.
2. Seleccionar a mano TODOS los clips de ese cuarto (potencialmente
   docenas, dispersos entre los que sí y no quiere mover).
3. Apretar `⌘U` y elegir la unidad.

Documentado en `docs/superpowers/specs/2026-09-20-unidades-y-departamentos-design.md`,
sección 4 ("Reasignar en lote"). Ahí mismo dice por qué se hizo así:
"Bruno prefirió control manual sobre adivinar, y es una sola vez" — pero
en la práctica, seleccionar clips uno por uno para mover algo que ya es un
CUARTO completo (un concepto, no una lista de archivos) es indirecto: opera
al nivel equivocado. Bruno piensa en cuartos, no en clips sueltos.

---

## Lo que ya existe y es reusable

El rail (`src/clasificador_video/ui/room_rail.py`) **ya tiene arrastre de
cuartos construido y funcionando**, pero acotado a reordenar (cambiar la
tecla 1-9 de un cuarto), no a moverlo entre unidades:

- `_FilaCuarto` (línea 166) ya arranca un `QDrag` con
  `MIME_CUARTO = "application/x-clasificador-cuarto"` al arrastrar una fila
  (`mouseMoveEvent`, línea 258).
- `RoomRail` acepta el drop, dibuja una línea de destino
  (`mostrar_linea_de_destino`) y ya sabe agrupar el rail en **bandas por
  unidad** (`_crear_banda`, línea 768; `.unit-band` en el mockup) cuando el
  proyecto tiene unidades.
- **El límite está a propósito en `soltar_cuarto` (línea 850-898)**: si
  sueltas un cuarto en la banda de OTRA unidad, se ignora sin avisar.
  El comentario en el código lo explica: dos unidades pueden repetir un
  nombre de cuarto (`Cocina` en Casa A y en Casa B), así que mover un
  cuarto ENTRE unidades no es solo cambiar su posición en una lista — hay
  que decidir qué pasa si el cuarto destino ya existe con ese nombre, y
  eso no estaba resuelto cuando se construyó el arrastre (2026-09-20).

Es decir: la mecánica de arrastrar-y-soltar ya está ahí, elegante y
funcionando. Lo que falta diseñar es **qué significa soltar un cuarto en la
banda de otra unidad** — el caso que hoy se descarta en silencio.

---

## Preguntas abiertas para el brainstorm

Estas son las que un `superpowers:brainstorming` necesita resolver con
Bruno antes de tocar código — no las contesta este handoff:

1. **Qué se mueve exactamente al soltar un cuarto en otra unidad**: ¿el
   cuarto vacío (una carpeta que se re-etiqueta) o el cuarto CON sus clips
   ya clasificados? (Casi seguro lo segundo, es el caso de uso completo,
   pero hay que confirmarlo y decidir el mensaje/confirmación si aplica.)

2. **Choque de nombres**: si sueltas "Cocina" en la banda de "Casa B" y
   Casa B YA tiene una "Cocina" propia — ¿se fusionan los clips en un solo
   cuarto? ¿se rechaza el drop con un aviso? ¿se renombra automáticamente
   (`Cocina 2`)? Cada opción tiene una superficie de UX distinta.

3. **¿El gesto es cuarto-a-banda (soltar sobre la banda entera) o
   cuarto-a-cuarto (soltar sobre una fila específica, fusionando con
   ella)?** Los dos caben dentro de "arrastrable", pero se sienten y se
   construyen distinto.

4. **¿Aplica también a la hoja**, o el gesto vive solo en el rail? La hoja
   ya tiene sus propias bandas de unidad (`.unit-band` en el mockup) — un
   segundo lugar para arrastrar cuartos podría ser redundante o
   complementario, según cómo se use la hoja en la práctica.

5. **Qué tan "elegante y profesional" implica en términos concretos**:
   ¿animación al soltar, confirmación visual (toast/highlight), deshacer
   con `⌘Z` como todo lo demás en el rail? El historial (`History`,
   `src/clasificador_video/history.py`) ya registra crear/renombrar/mover/
   borrar cuartos — mover-entre-unidades necesitaría su propia entrada si
   se quiere deshacer igual que el resto.

6. **Migración masiva vs. uno por uno**: el caso real de Bruno son VARIOS
   cuartos con sufijo `-A`/`-B` que hay que repartir entre dos unidades de
   una sola vez. ¿El diseño nuevo tiene que soportar arrastrar varios
   cuartos seleccionados a la vez, o uno por uno basta porque son pocos
   cuartos (aunque muchos clips dentro de cada uno)?

---

## Dónde mirar antes de diseñar

- `docs/superpowers/specs/2026-09-20-unidades-y-departamentos-design.md` —
  el spec completo de unidades, en particular la sección 4 (el camino
  actual que se va a reemplazar) y la sección 5 (rail y hoja, bandas).
- `docs/superpowers/mockups/2026-09-20-unidades-y-departamentos/mockup.html`
  — el mockup aprobado, con las bandas de unidad ya dibujadas (`.unit-band`,
  `.unit-header`, `.unit-swatch`) — es el lenguaje visual a extender, no a
  reinventar.
- `src/clasificador_video/ui/room_rail.py:166-346` — `_FilaCuarto`, el
  arrastre que ya existe.
- `src/clasificador_video/ui/room_rail.py:768-899` — `_crear_banda`,
  `dragEnterEvent`/`dropEvent`/`soltar_cuarto`, donde vive hoy el límite a
  quitar.
- `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md` — dirección
  de diseño general de la UI, para que lo nuevo no choque con decisiones ya
  tomadas (revisar antes de proponer cualquier tratamiento visual nuevo).

---

## Siguiente paso

Arrancar `superpowers:brainstorming` en la próxima conversación, con este
handoff como punto de partida — no repetir la exploración de código de
arriba, ya está hecha. Las seis preguntas de la sección anterior son el
mejor lugar para empezar a preguntarle a Bruno, una por una.
