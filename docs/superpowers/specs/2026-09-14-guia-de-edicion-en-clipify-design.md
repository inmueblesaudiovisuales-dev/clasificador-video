# La guía de edición se arma en Clipify — diseño

*(Spec. Fecha: 2026-09-14. Sale de la plática con Bruno del mismo día, al leer
el spec del patrón en voz alta.)*

**Este documento reemplaza la mitad de arriba de
`2026-09-14-orden-sugerido-de-cuartos-design.md`** —la que pregunta y llama a
la IA desde Premiere— y **le cambia el §6 a
`2026-09-14-mi-patron-de-recorrido-design.md`**. Lo que ninguno de los dos
pierde queda listado en el §7.

## 1. De dónde salió

La pestaña «Orden sugerido» se construyó dentro del plugin de Premiere, y ahí
funciona. Bruno la leyó descrita completa y preguntó lo obvio:

> «¿Qué te parece si todo eso se hiciera en Clipify? ¿No sería más fácil? Como
> una última fase antes de exportar. Y luego en Premiere te da una guía de
> cómo editarlo.»

Sí es más fácil, y no por comodidad: **el dato ya está de ese lado.**

## 2. Por qué del lado de Clipify sale más barato

Cuatro razones, y la primera es la que manda.

1. **Los cuartos nacen en Clipify.** Bruno los teclea ahí. Hoy viajan a
   Premiere dentro del manifest, allá se convierten en carpetas, y la pestaña
   los vuelve a leer **de las carpetas**. Ese viaje de ida y vuelta es la única
   razón por la que existe la revisión del §6 del spec de la pestaña —que
   compara la lista contra los bins y marca lo que falta o lo que se inventó—.
   Preguntando en Clipify, el modelo se compara contra **los cuartos de verdad**
   y no contra su reflejo.

   La revisión **no se va** (§7): sigue haciendo falta contra el modelo, que se
   puede saltar un cuarto igual de bien en cualquier lado. Lo que se va es el
   caso de que el reflejo llegue distinto del original.

2. **Es el momento en que Bruno más sabe qué hay.** Acaba de mirar el material
   clip por clip. En Premiere, en cambio, todavía no ha visto nada del rodaje
   nuevo — abre el proyecto y está vacío.

3. **La pantalla es de verdad.** El panel de UXP es una columna angosta y su
   API miente sobre sí misma: el propio `CLAUDE.md` guarda que la documentación
   de Adobe falló tres veces en un día en este mismo plugin. La pregunta
   principal de la pestaña —«¿qué quieres lucir?»— pide una caja grande donde
   escribir en prosa, y esa caja se dibuja mejor en Qt.

4. **El patrón de recorrido vive de este lado.** Es un Markdown en
   `docs/patron-de-recorrido/`, en este repo. Metido en el plugin habría que
   copiarlo, y ya está escrito por qué eso no se hace: dos copias del mismo
   dato que se editan por separado se desincronizan en el primer cambio de
   opinión.

**Lo que cuesta:** rehacer en Python algo que ya funciona en JavaScript. Es un
costo real y se paga una vez.

## 3. Las decisiones, una por una

Cada renglón es una respuesta explícita de Bruno, en el orden en que las dio.

1. **La guía se congela.** La que se armó en Clipify es la que se ve en
   Premiere. El plugin **no la puede volver a pedir**: si quieres otra,
   regresas a Clipify. Ésta es la decisión que abarata todo lo demás — sin ella
   el plugin seguiría necesitando llave, red y esperas, y no se habría ahorrado
   nada (§4.c).
2. **La guía tiene su propio botón**, no sale al exportar. Exportar se queda en
   un clic, como hoy. Se le ofreció que la pantalla saliera siempre antes de
   guardar —con o sin poder saltarla— y escogió el botón aparte.
3. **En Premiere se ve el orden, el párrafo y los avisos**, los tres. No la
   lista pelona.
4. **Y las carpetas llegan numeradas** en ese orden: `01. Fachada`,
   `02. Cocina`. Su estructura de proyecto ya numera (`02. Clip`), así que no
   es un idioma nuevo.
5. **Al importar, el cuarto se reconoce sin su número**, y si el orden cambió
   se le cambia el número a la carpeta que ya existe. Ver el §5.2, que es el
   modo de falla que esta decisión evita.
6. **El orden aceptado se vuelve EL orden de los cuartos** — el del rail, el de
   la hoja y el de Premiere. Uno solo, que es la decisión que el repo ya tenía
   tomada por otro camino.

## 4. Dónde vive cada pieza

### 4.a En Clipify: la pantalla de la guía

Un botón junto al de exportar, en la barra de título: **«Guía de edición»**.
Se aprieta cuando ya se terminó de clasificar, no antes — pero nada lo obliga,
porque es un botón y no un paso.

La pantalla tiene dos preguntas, en este orden:

- **«¿Qué quieres lucir?»**, al frente y con caja grande para escribir en
  prosa. Es la principal. («Sí es importante poder describirle qué quiero lucir
  de cada propiedad.»)
- **«¿Qué tipo de propiedad es?»**, debajo, con seis opciones: Casa,
  Departamento, Terreno, Local, Quinta de campo, Hospedaje. Son los seis que de
  verdad salieron en sus quince entregables de 2026 — ver el handoff del
  patrón, donde está por qué se escogieron ésos y no la lista larga del rubro.

**«¿Para quién es el video?» no existe.** Se fue con el spec del patrón: todo
es para redes, era un clic para decir lo de siempre.

Se aprieta armar y se enseñan tres cosas:

- **El párrafo** de cómo recorrerla.
- **La lista** de cuartos en orden, numerada.
- **Los avisos**, uno por renglón donde la sugerencia se apartó del patrón de
  Bruno: *«la alberca la subí porque dijiste que es lo que hay que lucir»*.
  Discretos, en la misma línea del cuarto. No son estadística —el patrón nunca
  se justifica con números (§5.1 del spec del patrón)— sino el aviso de que
  algo se movió, para que no se le pase.

Abajo, dos salidas: **«Usar este orden»** y volver a pedirla cambiando lo que
se quiere lucir.

**«Usar este orden» hace dos cosas y las dos se ven:** reacomoda los cuartos en
el rail y en la hoja, y guarda la guía en la sesión. De ahí en adelante la guía
viaja sola.

### 4.b El manifest lleva la guía

Un bloque nuevo en el JSON: el párrafo, la lista de cuartos en orden, y los
avisos. Más lo de siempre.

**Los cuartos NO llevan el número adentro de `categoria_path`.** Ahí sigue
viajando `["Cocina"]`, limpio. El número lo pone el plugin al crear la carpeta,
derivándolo de la posición en la lista de orden.

Es el mismo corte que ya existe con la cámara: el manifest manda `camara:
"sony"` y la traducción a color vive del otro lado, en `label.js`. **Aquí viaja
el dato, no la presentación.** Meter el número en `categoria_path` lo volvería
parte del nombre del cuarto, y entonces reordenar significaría renombrar
cuartos — que es una cosa distinta de acomodarlos.

**Un manifest sin guía es válido.** Si Bruno nunca apretó el botón, o si se
cayó la red, el bloque no está y todo lo demás funciona igual.

### 4.c En Premiere: solo se lee

La pestaña se queda, vaciada de todo lo que preguntaba:

- Enseña el párrafo, la lista y los avisos que venían en el manifest.
- **No tiene llave, no toca la red, no espera nada.** Abre instantánea.
- Si el proyecto no trae guía, lo dice con esas palabras —«este proyecto no
  trae guía de edición»— y no inventa una.

Y **sigue sin escribir nada en el proyecto**: la pestaña es de lectura entera,
igual que hoy. Lo que escribe es la importación, que siempre escribió.

### 4.d Las carpetas numeradas

Al importar, cada cuarto se crea como `NN. Nombre`, con el número de su
posición en el orden de la guía. Un manifest sin guía crea las carpetas como
hoy, sin número.

**El prefijo es exactamente `NN. `** —dígitos, punto, espacio— y nada más. Un
cuarto que Bruno haya llamado «2 Recámaras» no se confunde con un prefijo
porque no trae el punto.

## 5. Los dos modos de falla que ya se atendieron

### 5.1 La lista que se salta un cuarto

Es el §6 del spec de la pestaña y **sigue vigente palabra por palabra**, nada
más que la comparación se hace en Clipify contra los cuartos de la sesión:

- Se pide la respuesta en JSON con forma fija, no en prosa: la lista hay que
  **compararla**, y comparar prosa es adivinar.
- Se compara por **igualdad exacta de cadena**. Nada de `trim`, minúsculas ni
  quitar acentos: `Recamara 1` contra `Recámara 1` es un cuarto que falta y
  otro inventado, no un empate, y es justo el caso que un `.trim()` de más
  escondería.
- **Falta alguno** → se enseña la lista y arriba el aviso, con los que faltan
  por su nombre. No se acomodan solos al final.
- **Sobra alguno** → el inventado se enseña tachado, con su aviso. No se borra
  callado.
- **La respuesta no es JSON** → se dice eso y se ofrece reintentar. Nunca se
  enseña media lista.

Por qué en serio: una guía a la que le falta la cocina hace que se te olvide la
cocina al editar, y eso no se nota hasta después de entregar.

**Y una cosa se simplifica de verdad:** el caso de «este proyecto no salió de
Clipify, teclea los cuartos a mano» **desaparece**. En Clipify siempre hay
cuartos, porque son los que Bruno acaba de teclear. Con él se va también la
distinción entre «no hay carpeta `02. Clip`» y «la hay pero está vacía», que
costó un mensaje falso el 2026-09-14.

### 5.2 La segunda pasada, y la carpeta duplicada

Éste es nuevo y lo trae la decisión de numerar. Si Bruno importa más clips del
mismo rodaje y el orden salió distinto, la cocina que era `03. Cocina` llega
como `05. Cocina`: **Premiere le crearía una segunda carpeta** y los clips del
mismo cuarto quedarían repartidos en dos, sin que nada avise. Es exactamente la
familia de los ocho bugs del 2026-08-22 — dos partes del programa diciendo
cosas distintas del mismo dato, cada una haciendo lo que su código dice.

Lo que se hace:

1. Al buscar la carpeta de un cuarto, se compara **el nombre sin su prefijo
   numérico**. `03. Cocina` y `05. Cocina` son la misma Cocina.
2. Si la encuentra con otro número, **le cambia el número a ésa** en vez de
   crear otra.
3. **Solo se toca nuestro propio prefijo.** Es la misma regla que las marcas de
   estado en los nombres de clip: un número que Bruno escribió a mano no es
   nuestro y no se quita.

## 6. Lo que se borra

De `uxp-plugin/`, en el mismo commit en que lo nuevo funcione:

- Las preguntas de la pestaña y su estado.
- La llamada a DeepSeek desde el plugin, su llave y la pantalla de pegarla.
- El armado del prompt y la lectura de la respuesta.
- La lectura de los cuartos desde los bins, que existía solo para armar la
  pregunta.

**No se deja nada «por si acaso».** Git ya guarda el historial, y es una regla
escrita del repo. Lo que sí se conserva es su **lógica pura probada** —la
revisión de la lista y el armado del prompt— que se traduce a Python en vez de
reinventarse: los casos de sus pruebas de `node` ya cachan cosas reales.

## 7. Lo que NO pierde ninguno de los dos specs anteriores

- **El patrón de recorrido**, entero: cómo se saca, que es uno solo, que se
  escribe sin cuentas y sin justificarse, y que entra al prompt como base y no
  como regla. Lo único que le cambia es **dónde** se usa.
- **La revisión de la lista** (§5.1 de aquí).
- **La pestaña de Premiere no escribe en el proyecto.**
- **Los seis tipos de propiedad**, y que «¿para quién?» se fue.
- **Que no se ordenan los clips dentro de cada cuarto.** Sigue fuera.

## 8. Lo que NO entra

- **Que Premiere pueda pedir otra guía** (§3.1).
- **Que la pantalla salga sola al exportar** (§3.2).
- **Que el número viaje adentro de `categoria_path`** (§4.b).
- **Que la guía se edite en Premiere.** Se lee y ya.
- **Reordenar los clips dentro de un cuarto.**
- **Dos órdenes de cuartos.** El aceptado es el único (§3.6).

## 9. Los detalles que no se preguntaron, y cómo quedan

- **La llave** se guarda del lado de Clipify, en su configuración de siempre
  (`~/.clasificador_video/`), fuera del repo, fuera del proyecto de Premiere y
  **nunca en el log**. Mismo trato que tenía en el plugin.
- **Si se cae la red o falla la llamada**, se dice en palabras de Bruno —«no se
  pudo armar la guía»— y **no se bloquea nada**: exportar sigue funcionando y
  el manifest sale sin guía.
- **La guía se guarda en la sesión**, así que cerrar Clipify y volver no la
  pierde.

## 10. Cómo se comprueba

**Con pruebas de Python**, en `tests/`:

- Que la revisión marque el cuarto que falta y el inventado, comparando por
  igualdad exacta —incluido el caso `Recamara 1` contra `Recámara 1`.
- Que una respuesta que no es JSON no enseñe media lista.
- Que «Usar este orden» deje el rail y la hoja en el mismo orden.
- Que el manifest lleve la guía, y que uno sin guía siga siendo válido.
- Que `categoria_path` salga **sin** número.
- Que un fallo de red no impida exportar.

**Con pruebas de `node`**, en `uxp-plugin/pruebas/`, que es donde la lógica del
plugin corre sin abrir Premiere:

- Que `03. Cocina` y `05. Cocina` se reconozcan como la misma Cocina, y que
  «2 Recámaras» no pierda su número.
- Que la segunda importación **renumere** la carpeta existente en vez de crear
  otra.
- Que un manifest sin guía cree las carpetas sin número.

**Verificación visual real**, según `CLAUDE.md` — si no se miró la imagen, no
se afirma:

- Captura de la pantalla de la guía en Clipify, con la caja de «qué lucir» al
  frente y los seis tipos abajo.
- Captura de una guía donde la sugerencia se salió del patrón y lo marcó.
- Captura del panel de Premiere enseñando la guía, y del mismo panel diciendo
  que el proyecto no trae una.

## 11. El riesgo que queda

**Que la guía se congele con el proyecto equivocado.** Bruno arma la guía,
sigue clasificando, agrega cuartos, y exporta: la guía guardada ya no habla de
los cuartos que hay. No es hipotético — el botón aparte (§3.2) existe
justamente para poder apretarlo cuando quiera, y «cuando quiera» incluye
demasiado pronto.

Lo que se hace: **al exportar, si los cuartos cambiaron desde que se armó la
guía, se avisa** —«tu guía es de antes de agregar la Terraza»— y se deja
escoger entre exportar así o volver a armarla. Se avisa, no se decide solo: es
la misma regla que ya sostiene el diálogo de proxies, *la app propone, nunca
adivina en silencio.*
