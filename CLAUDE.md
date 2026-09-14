# Instrucciones para Claude Code en este repo

## Idioma: español mexicano, siempre

**Toda la conversación va en español mexicano.** No en español de España ni
sudamericano. Esto aplica a todo lo que se escriba en este proyecto, sin
excepción:

- las respuestas en el chat,
- los mensajes de commit,
- la documentación en `docs/`,
- los comentarios en el código,
- **y sobre todo los textos que ve el usuario dentro de la app** (botones,
  etiquetas, mensajes de error, tooltips), que son los que terminan
  publicados.

En concreto:

- **Usa `tú`, nunca `vos`.** Se dice "arrastra", "mantén presionada",
  "suelta", "puedes", "tienes", "selecciona" — no "arrastrá", "mantené",
  "soltá", "podés", "tenés", "seleccioná".
- **`aquí`, no `acá`.** `computadora`, no `ordenador`. `video`, no `vídeo`.
  `jalar`/`arrastrar`, no `coger`.
- Nada de `che`, `pibe`, `laburo`, `ahorita no` con sentido rioplatense, ni
  otros marcadores regionales de Argentina/Uruguay/España.
- Los términos técnicos que en la industria se usan en inglés se dejan en
  inglés (`pick`, `reject`, `render`, `proxy`, `frame`, `timecode`), porque
  así los usa un editor de video en México. No traducirlos a la fuerza.

Si un texto ya existente en el repo está en otra variante, corregirlo cuando
se toque el archivo.

## En el chat: breve y sin lenguaje técnico

Bruno es editor de video, no programador. **Las respuestas en la conversación
van cortas y en palabras normales**: qué cambió y qué va a ver él al usar la
app. Nada de nombres de clases, métodos o atributos, ni explicaciones de cómo
funciona Qt por dentro, ni muros de texto con todo el razonamiento.

El detalle técnico sí se escribe — pero en los commits, en `docs/` y en los
comentarios del código, que es donde sirve. En el chat, no.

## Flujo de trabajo

- **Sin branches nuevas**: Bruno pidió explícitamente trabajar directo sobre
  `master`. No crear branches ni proponer PRs a menos que lo pida.
- **Commits**: mensajes en español mexicano, un commit por unidad de trabajo
  lógica, terminan con `Co-Authored-By: <modelo> <noreply@anthropic.com>`,
  donde `<modelo>` es el que realmente hizo el trabajo (`Claude Opus 5`,
  `Claude Sonnet 5`, etc.). No dejarlo fijo en un modelo: la atribución tiene
  que ser real.
- **Tests** — la suite corre **completa**:
  ```bash
  QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
  ```
  Hasta agosto de 2026 esto llevaba `--ignore=tests/test_app.py`, porque ese
  archivo colgaba bajo `offscreen`. **Ya no cuelga**: la F3 lo reescribió —el
  diálogo de configuración que abría con `exec()` murió con ella— y desde
  entonces corre en medio segundo. Comprobado con cinco corridas completas el
  2026-08-08. Si alguna vez vuelve a colgarse, es un bug a resolver, no una
  limitación a esquivar.
- **El uso real encuentra lo que las pruebas no.** El 2026-08-22 Bruno usó
  la app con un shooting completo por primera vez —205 clips— y salieron
  **ocho bugs**, ninguno detectado por 1500 pruebas. El patrón: ninguno era
  un cálculo mal hecho; todos eran **dos partes del programa diciendo cosas
  distintas del mismo dato**, o **una herramienta que existía y no se
  encontraba**. Cada mitad hacía exactamente lo que su código decía. Cuando
  algo «se siente raro» y las pruebas están verdes, busca ahí. La lista
  completa está en `docs/superpowers/CONTEXTO-Y-METAS.md`.

- **Verificación visual real, no solo tests**: nunca afirmar que algo se ve
  bien sin haber visto el pixel. El medio depende del artefacto:
  - **Widget de PySide6** — construir una `MainWindow`/widget de prueba, usar
    `grab()`, guardar el PNG y leerlo con la herramienta de lectura de
    archivos.
  - **Mockup o documento HTML** — servirlo (`python3 -m http.server` sobre su
    carpeta), abrirlo con una herramienta de navegador, sacar captura y
    leerla.

  En los dos casos vale la misma regla: si no se miró la imagen, no se
  afirma. Y los archivos temporales de esa verificación van al scratchpad de
  la sesión, nunca al repo.
- **Brainstorm antes de features nuevas o cambios visuales** — este proyecto
  usa el flujo de `superpowers:brainstorming` → spec en
  `docs/superpowers/specs/` → plan en `docs/superpowers/plans/` →
  implementación con TDD. Los specs y planes de sesiones anteriores son la
  fuente de verdad de decisiones ya tomadas — revisarlos antes de asumir.

  **Excepción**: si ya existe un brief o spec escrito que cubre el trabajo
  pedido, ese documento *es* el resultado del brainstorm y no hace falta
  repetirlo (por ejemplo `PROMPT-REDISENO-2026-08-08.md`, que originó el
  rediseño de la UI). Rehacer el brainstorm cuando los requisitos ya están
  por escrito solo le hace perder tiempo a Bruno.

## Decisiones de arquitectura ya tomadas (no las reabras sin razón nueva)

- **`ScrubBar` usa `QPainter` custom en `paintEvent`, no QSS dinámico.** QSS
  aplicado por-widget en elementos que se repintan seguido (scrub bar con
  playhead animado) es un antipatrón de performance en Qt — decisión
  deliberada, ver `docs/superpowers/archive/HANDOFF-2026-08-06-arreglar-video-y-diseno.md`.
- **Separación de color por canal semántico** (`src/clasificador_video/ui/theme.py`):
  - `PICK_COLOR`/`REJECT_COLOR`/`CURRENT_COLOR` — estado del clip. Nunca se
    reusan para identidad de cuarto.
  - `ROOM_PALETTE` — identidad de cuarto, paleta apagada a propósito para no
    competir visualmente con los colores de estado.
  - `TRIM_COLOR` — rango in/out marcado. Separado de `ACCENT` (playhead/clip
    actual) para que un thumbnail con ambos no confunda las dos cosas.
- **mpv se embebe vía API de render (`vo=libmpv` + `MpvRenderContext`), no
  `wid`.** En macOS con el backend gráfico actual de mpv, `wid` no es
  confiable — mpv abre su propia ventana en vez de dibujar en el widget.
- **`hwdec=videotoolbox` fijo** — validado en vivo contra HEVC 10-bit real de
  la Sony FX30.
- **`QSurfaceFormat` a OpenGL Core 3.3 antes de crear la `QApplication`** —
  mpv necesita Core >= 3.3; el perfil de compatibilidad default de Qt en
  macOS no alcanza (`ui/app.py::configure_gl_surface_format`).
- **El LUT por bin está cerrado, y los DOS caminos están medidos.** Sí se le
  pueden colgar efectos al *master clip* sin armar secuencia
  (`AE.ADBE Lumetri`), pero:
  - el parámetro «Input LUT» **no acepta rutas** — es un menú y su valor es
    el índice del renglón, que apunta a otro LUT en otra computadora **sin
    avisar** (2026-08-10);
  - y el parámetro «Blob», que es donde Premiere **sí** guarda la ruta
    completa del `.cube`, **tumba Premiere al leerlo** y rechaza con
    «Illegal Parameter type» lo que se le escriba — incluido el bloque
    original sacado de un `xmeml` de Bruno (2026-09-08).

  No reabrir sin una versión nueva de Premiere: un tercer camino tendría que
  aparecer en la API, no en nuestro código. Detalle en
  `archive/RESULTADO-2026-08-10-lut-y-estrella-en-premiere.md` y
  `archive/RESULTADO-2026-09-08-el-lut-por-la-via-del-blob.md`.
- **Los `.LRF` del dron no son material ni proxy.** Fuera de
  `VIDEO_EXTENSIONS` por decisión de Bruno: entraban como clips duplicados, y
  como proxy no calzan cuadro a cuadro (contenido corrido 0–5 cuadros,
  variable por toma). Los proxies del dron se generan del original con
  `proxy_gen.py`.
- **En el plugin de UXP, no confíes en la documentación de Adobe sobre qué
  métodos existen.** Ya falló tres veces en el mismo día: la fábrica de
  efectos devuelve un objeto sin métodos, `getParam` necesita `await` aunque
  la referencia diga que no, y el nombre de un parámetro es `displayName`
  como propiedad y no `getDisplayName()`. Antes de llamar a algo, imprimir
  `Object.getOwnPropertyNames(Object.getPrototypeOf(obj))` y ver qué hay de
  verdad. La misma trampa está documentada al tope de `importClip.js`.
- **Dos preguntas distintas: asignar avanza por RODAJE, las flechas por lo
  que VES.** Teclear un cuarto avanza «al siguiente que no he tocado», que es
  tiempo — el siguiente que grabaste. `←`/`→` recorren el orden de la hoja,
  que con «Por cuarto» agrupa. Parecen una inconsistencia y no lo son: si
  asignar siguiera el orden de la hoja, el clip recién clasificado se iría al
  final de su grupo y «el siguiente» no tendría nada después — te quedarías
  parado en el mismo clip. Ya pasó al construirlo, y lo cacharon dos pruebas
  de la F3. Ver `specs/2026-08-20-las-flechas-siguen-lo-que-ves-design.md`.

- **`S` pone el último cuarto que USASTE, no el del clip anterior.** El
  camino viejo se separaba de lo que uno espera en cuanto te saltas clips o
  hay material de una pasada anterior: daba un cuarto viejo. Deshacer NO lo
  mueve — `⌘Z` revierte el dato, no tu intención.

- **Un solo orden de cuartos, y lo decide Bruno.** El rail y la hoja usan el
  mismo. La hoja los ordenaba por abecedario, y eso hacía que reordenar
  —que sí existía— no sirviera de nada. Dos listas del mismo dato que no se
  hablan valen menos que una sola.

- **En el rail, `⏎` asigna el cuarto; renombrar vive en `F2` y el doble
  clic.** Lo que uno quiere hacer con un cuarto mientras clasifica es
  ponérselo a un clip; renombrar es mantenimiento y no se queda con la tecla
  más obvia.

- **Los proxies van a la carpeta que ELIGE Bruno, con una subcarpeta por
  material**, desde el 2026-08-25. Es la tercera posición sobre la misma
  pregunta y cada una tuvo su razón: *al lado* (10 ago, no ensuciar la copia
  de la tarjeta) → *adentro* (22 ago, que viajen con el material) → *donde él
  diga*. La razón nueva salió de mirar su proyecto real: ya tenía
  `07. PROXIES/02. PROXY DRONE` hecha a mano y **vacía**, y la app le había
  creado un `Proxies/` aparte con los 75 del dron. El problema nunca fue
  dónde iban — era que la app no sabía que él tiene un orden y se lo pisaba.
  La subcarpeta se llama **igual que la carpeta de material**, no parecido:
  un nombre que se parece sin ser igual se lee mal, y aquí leerlo mal es
  enganchar el proxy de otra cámara. **Los tres sitios se siguen mirando al
  buscar** y no se mueve ni un archivo de lo que ya existe — eso lo pidió
  Bruno explícitamente. Ver
  `specs/2026-08-25-carpeta-de-proxies-elegible-design.md`.

- **La app propone la carpeta, nunca la adivina en silencio.** El diálogo
  llega contestado —con la carpeta que encontró junto al material— pero
  siempre enseña la ruta antes de escribir. Si adivina mal y lo ves, lo
  corriges en un clic; si adivina mal callada, te enteras tres semanas
  después. Es el modo de falla que ya costó una versión entregada rota.

- **La app se llama Clipify, y su marca se dibuja en un solo lugar.**
  `ui/marca.py` pinta el cuadro con palomita, y de ahí salen los dos sitios
  donde se ve: la marquita de la barra de título (`glifo()`, sin fondo — el
  ámbar lo pone el QSS) y el `.icns` del Finder y el Dock (`icono()`, vía
  `scripts/hacer_icono.py`). Están juntos a propósito: dos dibujos separados
  de la misma marca se van pareciendo cada vez menos con cada retoque. La
  palabra «Clipify» **no** va en la barra de título — ahí el ancho vale más
  para el proyecto y sus clips, y el icono ya dice cómo se llama. Y NO se
  renombraron `~/.clasificador_video/`, `~/.cache/clasificador_video/` ni el
  paquete de Python: renombrar la primera vacía la lista de recientes de
  Bruno sin explicación, y la segunda tira todas las miniaturas ya hechas.
  Ver `specs/2026-08-27-clipify-marca-y-nombre-design.md`.

- **`VideoWidget` recupera el clip que se cargó antes de que existiera su
  contexto de OpenGL.** La ventana arranca en la hoja, con el visor
  escondido, y `load_clips` abre el primer clip ahí mismo: Qt no crea el
  contexto de GL hasta que el widget se muestra, así que mpv cargaba el
  archivo sin dónde dibujarlo y el primer video de cada sesión salía negro.
  Vive en el widget y no en `MainWindow` a propósito: la ventana no tiene por
  qué saber cuándo Qt entrega un contexto. Se recupera SOLO el cargado a
  ciegas — recargar en cada `show()` reiniciaría el clip en cada cruce de
  hoja a visor.

- **Las tarjetas de la hoja cargan SOLO su portada**, y las otras once fotos
  cuando el mouse escrubea esa tarjeta. Cargarlas todas al abrir eran 34
  segundos congelado con 205 clips. No revertir «para simplificar».

- **Y cada foto se guarda al tamaño de la TARJETA, no del archivo**, con un
  techo de cuántas tiras siguen cargadas (`LIMITE_DE_TIRAS_VIVAS`). Bruno el
  2026-09-13: «usa muchísima RAM aunque no la esté usando». Medido con su
  proyecto real de 229 clips: 1.4 GB nada más abrirlo y +41 MB por cada
  tarjeta escrubeada, que no se devolvían nunca — recorrer la hoja entera
  llegaba a ~10 GB. Una miniatura de un clip sin proxy mide 3840×2160: 33 MB
  en memoria para dibujarla en 198 px.

  Se lee con `QImageReader.setScaledSize`, que reduce mientras descomprime:
  la imagen grande no existe en memoria ni por un instante, y leerla cuesta
  12 ms en vez de 32. Lo que se paga a cambio es releer del disco cuando la
  tarjeta CRECE (`apply_width`) o cuando el mouse vuelve a una tira ya
  soltada; las dos pasan dentro de un gesto y ninguna se siente. Ver
  `docs/superpowers/archive/RESULTADO-2026-09-13-ram-y-cpu-en-reposo.md`.

- **La app no suena.** `mute=True` en la creación de mpv y `--no-audio` en
  las miniaturas. Se ofreció una tecla para prenderlo y Bruno la descartó.

- **En Premiere, el estado se dice SOLO con una marca en el nombre**, y cada
  cuarto es plano: `★` destacado, `✓` pick, `✕` reject, y sin marca los que
  no se han visto. No hay `Picks`, `Rejects` ni `Sin marcar` — se fueron las
  tres el 2026-09-08.

  Es la misma decisión tomada tres veces el mismo día, y cada paso hizo
  sobrar al siguiente: el color pasó a decir la cámara → el destacado
  estrenó `★` → Bruno pidió el `✕` del reject **en lugar de** su carpeta →
  y luego que se fueran también las otras dos. El fondo: **una carpeta
  esconde el clip y una marca lo enseña.**

  Un clip **sin marca ya no significa «pick»**: significa que no lo has
  visto. Por eso el pick estrenó `✓` — sin él, quitar las carpetas dejaba
  al pick indistinguible de lo que nunca miraste, y perder un dato al cruzar
  a Premiere es justo lo que este plugin existe para evitar.

  **La marca CAMBIA con el estado, no se acumula.** Se quita la marca propia
  del inicio antes de poner la nueva, y solo la propia: un `✕` que Bruno
  escribió a media frase no es nuestro. Con una sola marca la regla era
  «solo agrega, nunca quita» —por no renombrar lo que él renombró a mano— y
  al llegar la segunda esa regla se volvió el bug: el clip terminaba con
  `★ ✕` diciendo dos cosas contrarias.

  Los once casos viven en `uxp-plugin/js/autocheck-tests.js`, que es donde
  esa lógica puede correr.

- **En Premiere, el color de un clip dice su CÁMARA, no su estado**
  (Sony azul, dron amarillo, otra morado). Un item de Premiere tiene una
  sola etiqueta de color y Bruno la quiere para saber de un vistazo de dónde
  salió cada clip; el estado viaja por su lado, en las marcas del nombre
  (ver el renglón de arriba). La cámara es propiedad del **bin**, se
  adivina del nombre de los archivos (`DJI` → dron, lo demás → Sony) y se
  corrige desde el menú del bin.

  **Un mismo color pinta la marquita del encabezado, el aviso del visor y el
  clip en Premiere** — los tres salen de `theme.camara_color`. Antes el
  encabezado iba por posición del bin y el aviso también, y eran dos cosas
  distintas del mismo dato. Si algún día se separan otra vez, es un bug.

  Costo aceptado: dos tarjetas de la misma cámara se ven iguales en la hoja.
  En Premiere también van a salirlo. Ver
  `specs/2026-09-08-color-por-camara-y-carpetas-design.md`.

- **La estructura del proyecto de Premiere vive en el PLUGIN**
  (`uxp-plugin/js/estructura.js`), no en el manifiesto: son las siete
  carpetas de Bruno y el material cuelga de `02. Clip`. Si la app las
  escribiera en `categoria_path`, esos nombres quedarían repartidos en dos
  repos y se desincronizarían en el primer cambio de opinión — mismo criterio
  por el que `con_subcarpeta_de_estado` no vive en la sesión.

- **El enfoque `xmeml` (Final Cut Pro 7 XML) está descartado**, no solo
  "obsoleto" — Premiere nunca abre el archivo de video real al importar un
  xmeml, y ese formato no puede declarar rotación. La vía real de entrega es
  el plugin UXP en `uxp-plugin/` vía `project.importFiles()`. No reintentar
  el camino xmeml sin una razón nueva y explícita de Bruno.

## Higiene de archivos — prioridad, no un paso opcional al final

Bruno le da valor real a que el repo se mantenga ordenado (ver la sesión de
limpieza de agosto 2026: se borró código muerto, spikes sueltos, se
renombró `TEST/` → `sample-media/`, se archivaron 13 handoffs históricos a
`docs/superpowers/archive/`, se unificaron dependencias). Esto no es una
tarea aparte — es un criterio a aplicar **cada vez que se crea algo nuevo**:

- **Nunca dejar archivos sueltos en la raíz del repo.** Todo archivo nuevo
  tiene una carpeta lógica a la que pertenece (`src/`, `tests/`, `docs/`,
  `scripts/`, etc.) — si no la tiene, es señal de que hace falta crear una
  carpeta con nombre descriptivo antes de escribir el archivo, no después.
- **Nombra las carpetas por lo que contienen**, no genérico (`output/`,
  `stuff/`, `tmp/`). Un mockup de rediseño va en algo como
  `docs/superpowers/mockups/rediseno-<fecha>/`, no en la raíz ni en un
  nombre ambiguo.
- **No dejar código, docs o scripts de "prueba puntual"/spike sin marcar
  como tal.** Si algo es un experimento descartable, dilo en el nombre o
  en un comentario al tope del archivo — así la próxima limpieza lo
  identifica sin tener que investigar si todavía se usa.
- **Un archivo nuevo reemplaza a uno viejo → borrar el viejo en el mismo
  commit**, no dejarlo "por las dudas". Git ya guarda el historial.
- **Antes de terminar una tarea que generó archivos nuevos**, repasar con
  `git status` que todo lo agregado tiene un lugar que tiene sentido, no
  solo que "funciona".

## Convenciones de nombres

- `TEST/` (mayúsculas) fue renombrado a `sample-media/` — evitar recrear una
  carpeta en mayúsculas para datos de prueba, colisiona en filesystems
  case-insensitive con `tests/`.
- Módulos de `src/clasificador_video/` son 1:1 con `tests/test_<módulo>.py`.
  Los widgets de PySide6 viven en `src/clasificador_video/ui/` y sus tests en
  `tests/ui/`.

## Contexto del producto

- `README.md` — qué es la app, cómo se instala y cómo se usa. Es la puerta de
  entrada y está escrita para quien la usa, no para quien la programa: los
  detalles de desarrollo NO van ahí.
- `docs/DESARROLLO.md` — correr desde el código, tests, empaquetar el `.dmg`
  y el plugin, y cómo está organizado el repo.
- `docs/superpowers/CONTEXTO-Y-METAS.md` — estado del proyecto, qué falta y
  qué se descartó con su razón.

## Dirección de diseño de la UI

Antes de tocar cualquier cosa en `src/clasificador_video/ui/`, leer
`docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`. Es la dirección
de diseño acordada con Bruno y explica el porqué de cada decisión, incluidas
las que ya se evaluaron y se descartaron (forma de onda de audio, recorte
automático de in/out, modo comparar de varios clips en paralelo, sistema de 5
estrellas). No reabrirlas sin una razón nueva.

Lo que no está construido todavía no es una invitación a improvisar otra
cosa: si el mockup no cubre un caso, vale la pena preguntarle a Bruno antes
de inventar.
