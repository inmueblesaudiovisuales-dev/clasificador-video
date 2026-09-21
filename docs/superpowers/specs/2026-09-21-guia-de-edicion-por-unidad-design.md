# La guía de edición por unidad — diseño

*(Spec del 2026-09-21. Sale del caso real de Bruno: un proyecto con unidades
—`CASA A`, `CASA B`, `AREAS COMUN`— donde la guía salía con la franja vacía
porque todos los cuartos viven en `rooms_por_unidad` y el catálogo «sin
unidad» quedó vacío.)*

Extiende `2026-09-20-unidades-y-departamentos-design.md` §8, que dejó esto
explícitamente fuera de alcance: «cuando la guía en sí se arregle, extenderla
a unidades es una spec aparte». La guía ya se arregló (spec 2026-09-19), así
que esto es esa spec aparte.

## 1. El problema

Con unidades, `MainWindow.room_selections` tiene una entrada por unidad y una
entrada `""` («sin unidad», el catálogo de siempre). `room_selection` es un
alias al catálogo de la unidad **activa**.

La guía leía `self.room_selection.active_rooms()`. En un proyecto con
unidades, si no hay ninguna activa —o la activa no es la que Bruno quiere—,
ese catálogo sale vacío y la franja no muestra nada que arrastrar. Reproducido
con el proyecto real `IAV-2609.14-A,B`: `rooms: []`, cuartos repartidos en
tres unidades, franja vacía.

## 2. La decisión: una guía por unidad

La guía ordena los cuartos de **una unidad a la vez**. Bruno elige cuál con un
selector en la propia pantalla, la pre-ordena con DeepSeek y la reacomoda a
mano. Al aceptar, ese orden manda en el catálogo de esa unidad.

Es la opción A de la plática del 2026-09-21. La opción B —una sola guía con
todos los cuartos de todas las unidades— se descartó porque las siete
columnas son por categoría: las dos fachadas caerían juntas en «Apertura» y
el recorrido saldría mezclando casas.

**Un proyecto sin unidades no cambia en nada**: no hay selector, la guía
opera sobre el catálogo «sin unidad» y se guarda igual que hoy.

## 3. El selector de unidad

- Va en la barra superior de la guía, junto al título, **solo si el proyecto
  tiene unidades**.
- Es una fila de chips: una por unidad, en el orden del rail. La elegida se
  marca como activa.
- **Default al abrir**: la unidad activa del rail (`_unidad_activa`); si no
  hay ninguna, la primera.
- **«Sin unidad»** aparece como una opción más **solo si su catálogo tiene
  cuartos** (el estado mixto de la spec de unidades §4: clips todavía sin
  migrar). Si está vacío, no se ofrece.
- Cambiar de unidad **no pierde** el tablero de la anterior: el estado de cada
  unidad se conserva mientras la pantalla está abierta (ver §5).

## 4. Pre-ordenar con DeepSeek

- El botón que hoy se llama «Clasificar de nuevo» pasa a llamarse
  **«Pre-ordenar»** cuando el tablero de esa unidad está vacío, y
  **«Pre-ordenar de nuevo»** cuando ya hay algo acomodado (con la misma
  confirmación de hoy: rehacer tira el acomodo a mano).
- Llama a DeepSeek con **los cuartos de la unidad elegida**, no los de todo el
  proyecto. El prompt y la respuesta no cambian (`guia.py` sigue igual): solo
  cambia la lista de cuartos que entra.
- **Si falta la llave**: el aviso lo dice en palabras de Bruno y el botón
  queda deshabilitado; se puede acomodar a mano igual. La llave se pone en
  Configuración, como siempre.
- **Si falla la red o la respuesta viene rara**: mismo trato de hoy — se dice,
  las columnas quedan vacías y Bruno acomoda a mano. No bloquea nada.
- **Al abrir la pantalla no se clasifica solo**: la pre-ordenada es una acción
  explícita de Bruno (hoy tampoco clasifica sola; se documenta para que no se
  agregue).

## 5. El tablero, por unidad

Cada unidad tiene su propio tablero —sus siete columnas, su franja, su aviso—
y su propio estado en memoria mientras la pantalla está abierta:

- Al elegir una unidad, se muestra su tablero. Si ya se había trabajado en
  esta sesión, se recupera tal cual (no se pierde el acomodo a mano al brincar
  de unidad).
- La franja muestra los cuartos de la unidad elegida.
- El aviso «Sin usar» se calcula contra los cuartos de esa unidad.
- «Usar este orden» junta los pasos de las siete columnas de esa unidad, en su
  orden fijo, y los manda por la misma señal `orden_aceptado` (lista plana).
  El receptor (`aceptar_orden_de_la_guia`) ahora aplica el orden **al catálogo
  de la unidad** que la guía traía, no al activo.

La señal `orden_aceptado` **no cambia de forma**: sigue siendo una lista plana
de nombres de cuarto. Lo que cambia es que `PantallaGuia` también dice de qué
unidad es el orden — un dato que `main_window` ya conoce porque fue quien
abrió la pantalla con esa unidad, así que no hace falta ampliar la señal.

## 6. Persistencia

- El `.cvproj` guarda **una guía por unidad**. Llave nueva
  `guias_por_unidad`: `{unidad: {orden: [...], cuartos_de_entonces: [...]}}`.
- Un proyecto sin unidades sigue guardando la llave `guia` de siempre, sin
  cambios.
- Al abrir el proyecto, se restauran todas las guías por unidad.
- «Guía vieja» (`guia_quedo_vieja`) se revisa **por unidad**: los cuartos de
  entonces de esa unidad contra los cuartos de esa unidad hoy.

## 7. El manifest y el plugin (para que Premiere numere bien)

Esto es lo que hace que el orden llegue a Premiere. Es la parte que la spec de
unidades §7 dejó pendiente.

- El manifest manda las guías por unidad: el orden de las unidades y, por
  unidad, el orden de sus cuartos.
- `estructura.js::caminoDelClip` numera **la unidad** (según el orden de
  unidades) y **el cuarto** (según el orden del cuarto dentro de su unidad),
  en vez de numerar solo el último segmento.
- Un proyecto sin unidades manda la misma lista plana de hoy y el plugin se
  comporta exactamente igual.

## 8. Lo que NO cambia

- Las siete columnas y su orden fijo.
- El formato del nombre de cada clip en Premiere (spec 2026-09-21).
- La estructura de carpetas, salvo que ahora la unidad también lleva número.
- La forma de la señal `orden_aceptado` (lista plana de nombres).
- El comportamiento de un proyecto sin unidades: idéntico a hoy.

## 9. Cómo se comprueba

- Pruebas de `PantallaGuia`: selector con unidades, cambio de unidad conserva
  el tablero, pre-ordenar usa los cuartos de la unidad elegida, usar este
  orden junta los pasos de esa unidad.
- Pruebas de `MainWindow`: aceptar el orden de una unidad reordena **su**
  catálogo y no el activo; guardar y reabrir conserva las guías por unidad;
  «guía vieja» se revisa por unidad.
- Pruebas de `guia.py`: sin cambios (el prompt sigue igual); se confirma con
  las que ya hay.
- Pruebas de node del plugin: numeración de unidad y de cuarto con y sin
  unidades.
- **Verificación visual real**: la pantalla con dos unidades, cambiando de una
  a otra, y el tablero de cada una. PNG leído, no afirmado.

## 10. Estado

**Diseñado con Bruno el 2026-09-21, sin construir nada.** Falta el plan de
implementación y la construcción con TDD.
