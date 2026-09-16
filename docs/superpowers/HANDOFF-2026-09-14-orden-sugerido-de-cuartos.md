# Handoff — Orden sugerido de los cuartos (pestaña nueva en el plugin)

*(Escrito el 2026-09-14, al cierre de un brainstorm con Bruno. La sesión se
cortó antes de escribir el spec: Bruno iba a apagar esta computadora y
continúa en una sesión remota sobre GitHub. **Todo lo de aquí ya está
decidido con él** — este documento no es una propuesta, es el resultado de la
plática. La tarea de la siguiente sesión es convertirlo en el spec y el plan,
no reabrirlo.)*

## De dónde salió

Bruno preguntó de qué forma el proyecto podría ayudarle a **editar en la línea
del tiempo**. Se le propusieron cinco caminos —ensamble automático, secuencia
por cuarto, secuencia de destacados, varios in/out por clip, notas como
marcadores— y los descartó todos de un tirón: «nada de eso ayudaría».

Lo que sí quiere: **un orden sugerido de los cuartos**, o sea el recorrido que
debería llevar el video. Dijo que pensaba en analizarlo con IA, «pero no todo
el video porque eso sería costoso», y dudaba de si valía la pena mirar
fotogramas.

**No vale la pena, y ese es el hallazgo que sostiene todo el diseño.** El
orden de un recorrido se decide por lo que ES cada cuarto, no por lo que se ve
en el pixel, y eso ya está escrito: los cuartos son nombres que Bruno teclea
(`rooms.py`). Con los puros nombres alcanza, y de paso el costo deja de ser un
tema — viaja texto, no video.

## Lo acordado, decisión por decisión

Cada renglón es una respuesta explícita de Bruno, en el orden en que las dio.

1. **Ordena los cuartos entre sí**, no los clips dentro de cada cuarto. Es el
   recorrido de la casa.
2. **Es una guía para leer. No mueve nada.** Se descartó el botón «acomodar
   así» que reordenaría el rail. Palabras suyas: «no necesariamente armarlo
   sino armar una guía».
3. **Con IA, no con una lista fija de reglas.** La razón: los cuartos los
   teclea él cada shooting con nombres libres (`Roof garden`, `Área de
   lavado`), que es justo donde una lista fija se queda corta y habría que
   estarle agregando nombres para siempre.
4. **Vive en Premiere**, no en Clipify. Bruno quiere la plática con el
   proyecto abierto y el timeline enfrente.
5. **Como pestaña del plugin que ya existe**, no como un segundo plugin.
   Bruno lo trajo a la mesa («tal vez esto debería ser un segundo plugin») y
   aceptó el argumento: una sola instalación que mantener, y la API de
   Premiere ya nos ha mentido tres veces sobre qué métodos existen (ver el
   tope de `importClip.js`).
6. **Conversación de ida y vuelta**, no preguntas fijas ni una sola caja de
   texto. Pero **fácil de contestar**: «que venga con todo y preguntas». O
   sea, el panel arranca preguntando y cada pregunta trae botones con las
   respuestas más comunes; la caja de texto libre está siempre abajo por si
   ninguna sirve.
7. **Cada cuarto de la lista lleva una línea corta de por qué va ahí** — pero
   solo porque eso el modelo sí lo sabe. Bruno lo condicionó: «B pero solo si
   es fácil que la IA lo sepa».

   **El matiz, que hay que respetar al escribir el prompt:** el modelo sabe
   *por qué la cocina va después del comedor* (lógica de recorrido). **No sabe
   qué hay en la cocina de Bruno** — no vio el video. La línea es «por qué va
   aquí», y solo habla de la casa concreta si Bruno lo contó en la plática.
   Un modelo describiendo una cocina que no vio es exactamente el modo de
   falla que este repo lleva un mes evitando: adivinar en silencio.
8. **DeepSeek**, elegido por Bruno. Habla la misma API que OpenAI, así que
   cambiar de proveedor es un renglón.

## Lo que ve Bruno

Pestaña **«Orden sugerido»** en el panel de Clipify dentro de Premiere.

Al abrirla ya sabe qué cuartos hay —los lee de las carpetas colgadas de
`02. Clip`, que es donde el plugin mete el material clasificado
(`estructura.js`)— y arranca **ella** preguntando: qué tipo de propiedad es,
para quién es el video, qué hay que lucir. Botones para contestar de un toque,
caja de texto libre siempre disponible.

Cuando tiene suficiente, suelta la lista: los cuartos en orden, cada uno con
su línea de por qué. De ahí Bruno le sigue hablando («la alberca al final»,
«este es para redes») y la lista se rehace.

La guía se queda escrita en el panel y hay un botón para copiarla.

Si la pestaña se abre en un proyecto que no salió de Clipify, lo dice y deja
teclear los cuartos a mano.

## Reglas que no se negocian

- **La lista trae TODOS los cuartos de Bruno, y ninguno inventado.** Si el
  modelo se salta uno o se saca uno de la manga, el panel **lo marca** en vez
  de enseñar la lista como si nada. Una guía a la que le falta la cocina hace
  que se te olvide la cocina al editar, y eso no se nota hasta después de
  entregar. Es la misma familia de bug que los ocho del 2026-08-22: dos partes
  diciendo cosas distintas del mismo dato.
- **No escribe nada en el proyecto.** Ni una carpeta, ni un clip, ni el
  timeline. Solo lee los nombres de los bins.
- **De la computadora solo salen los nombres de los cuartos y lo que Bruno
  escriba.** Nada de video, archivos ni rutas.
- **La llave de API se pega una vez** en el panel y se queda guardada ahí.

## El riesgo que se prueba PRIMERO

**Que Premiere deje al plugin hablar por internet.** El
`uxp-plugin/manifest.json` de hoy solo pide `localFileSystem`; hace falta
declarar permiso de red hacia `api.deepseek.com`. UXP debería soportarlo, pero
la advertencia del repo aplica entera: no confíes en la documentación de Adobe
sobre qué existe — imprime `Object.getOwnPropertyNames(...)` y compruébalo en
vivo.

**Esto se comprueba con un spike de una tarde, antes de construir el resto.**
Si no se puede llamar a la API desde UXP, el diseño entero cambia de lugar
(volvería a Clipify, que es la opción que Bruno ya descartó por gusto, no por
imposibilidad) y hay que avisarle antes de gastar el presupuesto en lo demás.

Bruno ya está enterado y lo aceptó.

## Lo que falta decidir

Nada de fondo. Al escribir el spec van a salir detalles de ejecución —cuántas
preguntas antes de soltar la primera lista, cómo se ven los botones, dónde se
guarda la llave, qué modelo de DeepSeek— y se resuelven ahí con el criterio de
siempre; no hace falta volver a consultarlos uno por uno.

## Lo que sigue

1. Comprobar el spike de red desde UXP (arriba).
2. Escribir el spec en
   `docs/superpowers/specs/2026-09-14-orden-sugerido-de-cuartos-design.md`
   con todo lo de este handoff, y que Bruno lo revise.
3. Plan con `superpowers:writing-plans`, e implementación con TDD.
4. **No repetir el brainstorm.** Este documento *es* su resultado.
