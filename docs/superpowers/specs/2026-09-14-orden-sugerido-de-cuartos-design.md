# Orden sugerido de los cuartos — diseño

*(Spec. Fecha: 2026-09-14. Sale del brainstorm cerrado con Bruno el mismo
día, escrito en `HANDOFF-2026-09-14-orden-sugerido-de-cuartos.md`. Ese
documento **es** el resultado de la plática y no se reabre aquí: este spec lo
convierte en algo construible y resuelve los detalles de ejecución que el
handoff dejó abiertos a propósito.)*

## 1. De dónde salió

Bruno preguntó de qué forma el proyecto podría ayudarle a **editar en la línea
del tiempo**. Se le pusieron cinco caminos enfrente —ensamble automático,
secuencia por cuarto, secuencia de destacados, varios in/out por clip, notas
como marcadores— y los descartó todos de un tirón: «nada de eso ayudaría».

Lo que sí quiere es **un orden sugerido de los cuartos**: el recorrido que
debería llevar el video. Pensaba en analizarlo con IA, «pero no todo el video
porque eso sería costoso», y dudaba de si valía la pena mirar fotogramas.

**No vale la pena, y ese hallazgo es el que sostiene todo el diseño.** El
orden de un recorrido se decide por lo que **es** cada cuarto, no por lo que
se ve en el pixel — y eso ya está escrito, porque los cuartos son nombres que
Bruno teclea. Con los puros nombres alcanza, y de paso el costo deja de ser un
tema: viaja texto, no video.

## 2. Lo acordado, decisión por decisión

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
5. **Como pestaña del plugin que ya existe**, no como un segundo plugin. Lo
   trajo él a la mesa («tal vez esto debería ser un segundo plugin») y aceptó
   el argumento: una sola instalación que mantener, y la API de Premiere ya
   nos ha mentido tres veces sobre qué métodos existen (ver el tope de
   `importClip.js`).
6. **Conversación de ida y vuelta**, no preguntas fijas ni una sola caja de
   texto. Pero **fácil de contestar**: «que venga con todo y preguntas».
7. **Cada cuarto de la lista lleva una línea corta de por qué va ahí**, con la
   condición que él puso: «B pero solo si es fácil que la IA lo sepa».
8. **DeepSeek**, elegido por él.

## 3. El matiz del §2.7, que es el que puede salir mal

El modelo sabe **por qué la cocina va después del comedor** — eso es lógica de
recorrido y la tiene de sobra. **No sabe qué hay en la cocina de Bruno**: no
vio el video, y nunca lo va a ver.

Entonces la línea de cada cuarto es **«por qué va aquí»**, y solo habla de la
casa concreta si Bruno lo contó en la plática. Un modelo describiendo una
cocina que no vio —«la cocina integral con cubierta de granito»— es
exactamente el modo de falla que este repo lleva un mes evitando: adivinar en
silencio y sonar seguro.

Esto se ejecuta en dos lugares, no en uno:

- **En el prompt**, diciéndoselo con todas sus letras: que no vio el material,
  que no describa lo que hay adentro de ningún cuarto, y que si no tiene una
  razón de recorrido que dar, diga la razón genérica en vez de inventarse un
  detalle.
- **Al leer la respuesta**, que es donde de verdad se sostiene — el §6.

## 4. Lo que ve Bruno

Pestaña **«Orden sugerido»** en el panel de Clipify dentro de Premiere.

Al abrirla **ya sabe qué cuartos hay**. No se los pregunta: los lee de las
carpetas colgadas de `02. Clip`, que es donde el plugin mete el material
clasificado (`estructura.js`). Si están ahí, es que él ya los tecleó una vez
en Clipify, y volver a pedirlos sería preguntar lo que ya se sabía.

Y arranca **ella** preguntando. Tres preguntas, cada una con botones para
contestar de un toque y la caja de texto libre siempre abajo:

| Pregunta | Botones |
|---|---|
| ¿Qué tipo de propiedad es? | Casa · Departamento · Terreno · Local |
| ¿Para quién es el video? | Redes · Portafolio · Cliente directo · Portal inmobiliario |
| ¿Qué hay que lucir? | *(sin botones: aquí el texto libre es la respuesta)* |

Cuando tiene suficiente, suelta la lista: los cuartos en orden, cada uno con
su línea de por qué. De ahí Bruno le sigue hablando —«la alberca al final»,
«este es para redes»— y la lista se rehace completa, no en parches.

La guía se queda escrita en el panel y hay un botón para **copiarla**.

Si la pestaña se abre en un proyecto que no salió de Clipify, lo dice y deja
teclear los cuartos a mano.

### 4.1 Los detalles de ejecución, resueltos

El handoff los dejó abiertos con el encargo de resolverlos aquí, con el
criterio de siempre y sin volver a consultarlos uno por uno.

- **Cuántas preguntas antes de la primera lista: tres, y ni una más.** Son las
  tres de la tabla y salen juntas en la pantalla, no en fila de a una. Bruno
  puede contestar las tres, una, o ninguna: el botón **«Dame la lista»** está
  activo desde el primer momento. La conversación es de ida y vuelta *después*
  de la lista, no antes — hacerlo pasar por un interrogatorio para llegar a lo
  que vino a ver es el camino más corto a que no use la pestaña.
- **Los botones** son chips de un renglón debajo de su pregunta. Se pueden
  elegir varios (un video puede ser para redes y para el portal), lo elegido
  se queda prendido, y volver a tocarlo lo apaga. La caja de texto libre vive
  abajo de todo y no se esconde nunca.
- **El modelo: `deepseek-chat`.** Es el de conversación, que es lo que esto
  es. El de razonamiento cuesta más y tarda más para una pregunta que no
  requiere razonar en cadena. Cambiarlo es un renglón, igual que cambiar de
  proveedor (DeepSeek habla la misma API que OpenAI).
- **Dónde se guarda la llave: en la carpeta de datos del plugin**
  (`localFileSystem.getDataFolder()`), no en el proyecto de Premiere, no en el
  repo, no junto al material. Se pega una vez en la pestaña y se queda. En el
  panel se enseña tapada —los últimos cuatro caracteres y nada más— y **nunca
  se escribe en el log**, que es un archivo que se comparte al depurar.

## 5. Reglas que no se negocian

- **No escribe nada en el proyecto.** Ni una carpeta, ni un clip, ni el
  timeline. Solo **lee** los nombres de los bins. La pestaña entera es de
  lectura, y esa es la razón por la que puede vivir dentro del mismo plugin
  que sí escribe sin dar miedo.
- **De la computadora solo salen los nombres de los cuartos y lo que Bruno
  escriba.** Nada de video, archivos, rutas ni nombres de clip. El cuerpo que
  se manda a DeepSeek se puede leer completo en el log, y ese es el punto:
  cualquiera puede comprobar qué salió.
- **La llave se pega una vez** y se queda guardada (§4.1).
- **La lista trae TODOS los cuartos de Bruno, y ninguno inventado.** Es la
  regla del §6, y es la que tiene dientes.

## 6. La regla que sostiene todo: la lista se revisa antes de enseñarse

Si el modelo se salta un cuarto o se saca uno de la manga, el panel **lo
marca** en vez de enseñar la lista como si nada.

**Por qué es tan en serio:** una guía a la que le falta la cocina hace que se
te olvide la cocina al editar, y eso no se nota hasta después de entregar. Es
la misma familia de los ocho bugs del 2026-08-22 — dos partes del programa
diciendo cosas distintas del mismo dato, cada una haciendo exactamente lo que
su código dice.

Cómo se ejecuta:

1. Se le pide al modelo la respuesta en **JSON** con una forma fija: una lista
   de `{cuarto, porque}`. No en prosa. Se pide así porque la lista hay que
   **comparar**la, no leerla, y comparar prosa es adivinar.
2. Al llegar, se comparan los nombres contra los cuartos que se leyeron de
   `02. Clip`, **exactos**: mismo texto, mismo acento, mismas mayúsculas. Un
   `Recámara 1` contra un `Recamara 1` es un cuarto que falta y otro
   inventado, no un empate — y es justo el caso que un `.trim()` de más
   escondería.
3. Los tres desenlaces:
   - **Cuadra** → se enseña la lista.
   - **Falta alguno** → se enseña la lista **y arriba el aviso**, con los que
     faltan por su nombre. No se acomodan solos al final: la guía dice lo que
     el modelo dijo, y el aviso dice lo que el modelo olvidó.
   - **Sobra alguno** → el inventado se enseña **tachado** y con su aviso. No
     se borra callado, porque ver qué se inventó es información sobre si vale
     la pena confiar en la lista de hoy.
4. Si la respuesta ni siquiera es JSON válido, se dice eso y se ofrece
   reintentar. Lo que no pasa nunca es que se enseñe media lista.

## 7. Cómo se leen los cuartos

Las carpetas que cuelgan **directo** de `02. Clip`, en el orden en que
Premiere las devuelve. Se usa `CARPETA_DE_CLIPS` de `estructura.js`, no la
cadena `"02. Clip"` escrita otra vez: si algún día se renombra allá arriba,
esto sigue apuntando a la misma.

Dos casos que hay que atender y no son el mismo:

- **`Sin clasificar` no es un cuarto** y no entra al recorrido. Es el cajón de
  lo que Bruno no alcanzó a clasificar, y meterlo en la guía haría que el
  modelo le buscara lugar en el recorrido de una casa a algo que no es un
  lugar de la casa.
- **Un proyecto que no salió de Clipify** —no hay `02. Clip`, o está sin
  carpetas adentro— no es un error: es alguien abriendo la pestaña en un
  proyecto cualquiera. Se dice con esas palabras y se le deja **teclear los
  cuartos a mano**, uno por renglón. De ahí para adelante todo funciona igual,
  incluida la revisión del §6, que compara contra lo que él tecleó.

## 8. El riesgo que se prueba PRIMERO

**Que Premiere deje al plugin hablar por internet.**

El `uxp-plugin/manifest.json` de hoy solo pide `localFileSystem`; hace falta
declarar permiso de red hacia `api.deepseek.com`. UXP debería soportarlo, pero
la advertencia del repo aplica entera: **no le creas a la documentación de
Adobe sobre qué existe**. Ya falló tres veces el mismo día — la fábrica de
efectos devolvió un objeto sin métodos, `getParam` necesitaba `await` aunque
la referencia dijera que no, y un nombre de parámetro era propiedad y no
método.

**Esto se comprueba con un spike de una tarde, antes de construir el resto**:
declarar el permiso, cargar el plugin, pedirle algo trivial a la API y
enumerar de verdad lo que hay (`Object.getOwnPropertyNames(...)`) en vez de
suponer que `fetch` está ahí.

**Si no se puede**, el diseño entero cambia de lugar: volvería a Clipify, que
es la opción que Bruno ya descartó **por gusto, no por imposibilidad**. Eso se
le avisa antes de gastar el presupuesto en lo demás. Ya está enterado y lo
aceptó.

## 9. Lo que NO entra

- **Mirar fotogramas.** Descartado en el §1, y no por costo: el orden de un
  recorrido no está en el pixel.
- **Ordenar los clips dentro de cada cuarto.** Bruno ordenó cuartos entre sí.
- **El botón «acomodar así»** que reordenaría el rail de Clipify con la
  sugerencia. Se le ofreció y lo descartó: es una guía para leer.
- **Un segundo plugin.** §2.5.
- **Que la guía se guarde en el proyecto de Premiere.** Vive en el panel y se
  copia con un botón. Guardarla querría decir escribir en el proyecto, que es
  justo lo que el §5 prohíbe.
- **Que la app de Clipify mande los cuartos al plugin.** Ya están en los bins;
  un segundo camino para el mismo dato es un segundo camino que se
  desincroniza.

## 10. Cómo se comprueba

**Con pruebas**, lo que es lógica pura. Y **corren en el repo con `node`**, no
en el arnés del plugin:

La lógica del §6 no le pregunta nada a Premiere — compara dos listas de
cadenas. Meterla en `autocheck-tests.js` la dejaría corriendo solo cuando
alguien abre Premiere **y** vuelve a prender el arnés (`AUTOCHECK_ACTIVO` está
en `false` desde que se terminó de construir el plugin, así que hoy los doce
casos de las marcas del nombre **no corren nunca**). Una comprobación que solo
corre cuando te acuerdas de prenderla no es una comprobación.

Entonces: la lógica pura vive en un archivo que no hace `require("premierepro")`,
y un corredor chiquito de Node la ejecuta desde el repo. Lo que sí necesita
Premiere —leer los bins, la red, el sistema de archivos de UXP— se queda en el
arnés, que para eso existe.

Los casos:

- La revisión del §6, caso por caso: la lista que cuadra; una a la que le
  falta un cuarto; una que trae uno inventado; una que hace las dos cosas a la
  vez; `Recamara 1` contra `Recámara 1` marcado como falta **y** invento, no
  como empate; y una respuesta que no es JSON.
- Que `Sin clasificar` no salga en la lista de cuartos que se manda (§7).
- Que el cuerpo que se manda a DeepSeek traiga **solo** nombres de cuarto y lo
  que Bruno escribió — ni una ruta, ni un nombre de clip (§5). Este es el que
  importa: es el punto exacto donde un descuido saca de la computadora algo
  que no debía salir.
- Que la llave no aparezca en el log.

**Contra Premiere de verdad**, lo que no se puede probar de otra forma:

1. El spike de red del §8, **antes que nada**.
2. Que los cuartos se lean de `02. Clip` en un proyecto real de Bruno, y que
   la pestaña se comporte en uno que no salió de Clipify (§7).

**Verificación visual real**, según `CLAUDE.md`: captura de la pestaña con la
lista puesta y con el aviso de un cuarto faltante — los dos estados, porque el
aviso es la mitad del §6 y un aviso que no se ve no sirve. Si no se miró la
imagen, no se afirma.

## 11. Una cosa chica que se toca de paso

El encabezado del panel todavía dice **«Clasificador de Video»**. La app se
llama **Clipify** desde el 2026-08-27 y el `manifest.json` ya lo dice; el
`index.html` se quedó atrás. Como esta pestaña obliga a reescribir ese archivo
de todos modos, el encabezado se corrige en la misma pasada.
