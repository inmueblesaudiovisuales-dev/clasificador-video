# Handoff — 2026-08-09 — desde el rediseño terminado

El rediseño de la UI **está cerrado** (once fases, F0 a F10), y **la
importación por bins también** — se hizo la noche del 2026-08-09 y esta sección
3 quedó como registro de lo entregado, no como tarea. Lo que sigue abierto es
**repartir la app** a las computadoras del equipo de Bruno, los **proxies del
dron** y el **LUT hacia Premiere**.

Reemplaza a [`archive/HANDOFF-2026-08-08-rediseno-ui-desde-f9.md`](archive/HANDOFF-2026-08-08-rediseno-ui-desde-f9.md).

---

## 1. Qué es el proyecto

Una app de escritorio en **PySide6 + mpv** para que Bruno, editor de video
profesional, clasifique clips de shootings inmobiliarios **antes** de editarlos
en Premiere.

1. **La app** (`src/clasificador_video/`) — importa material, reproduce cada
   clip, y el editor le asigna un **cuarto**, lo marca **pick/reject/destacado**
   y opcionalmente le pone **in/out**. Exporta un `manifest.json`.
2. **El plugin UXP** (`uxp-plugin/`) — corre dentro de Premiere, lee ese
   manifest y arma el proyecto: bins por cuarto, etiquetas de color, in/out y
   **proxies enganchados**.

**Su razón de existir es la velocidad.** El material real es **HEVC 10-bit de
una Sony FX30**, mayoría **vertical**, más tomas de un **dron DJI** (también
verticales).

## 2. Dónde está todo hoy

- Rama `master`, árbol limpio. **1007 tests en verde** — ese es el número de
  partida. (Eran 831 antes de los bins.)

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

La suite corre en ~11 s. **Si tarda minutos, algo está lanzando mpv de
verdad**: `tests/conftest.py` lo impide, y romper esa guarda es el síntoma.

### Lo que la app hace hoy

| | |
|---|---|
| **Ver** | autoplay al 25 %, `J K L`, `,`/`.` cuadro a cuadro, `R` al inicio, in/out con manijas |
| **Marcar** | `1`–`9` cuartos, `S` igual al anterior, `⏎` paleta, `P`/`X`/`⇧P`, **`↑`/`↓` suben y bajan el estado** |
| **En lote** | marquesina, `⇧`+click, `⌘A`, pincel (mantener `1`–`9` y arrastrar) — y **todo** lo de marcar aplica a la selección |
| **Dos vistas** | `⇥` alterna clip ↔ hoja, llevando siempre al clip actual, con transición animada |
| **Importar** | arrastrar carpetas y archivos; cada tanda es un **bin** (una cámara), con nombre editable |
| **Proxies** | **a mano y por bin**: eliges el de un clip y del par sale el patrón para los demás de ESA cámara |
| **Entregar** | `⌘E` exporta el manifest; el plugin arma el proyecto |

### Arquitectura

```
MainWindow  (ui/main_window.py)   — ensambla y orquesta; TRES filas y ninguna más
├── TitleBar    (ui/title_bar.py)    36 px — proyecto, switch Clip│Hoja, Proxies, Exportar
├── cuerpo
│   ├── RoomRail   (ui/room_rail.py)    200 px
│   ├── VideoStage (ui/video_stage.py)  ancho calculado — video + overlays
│   ├── ToolColumn (ui/tool_column.py)   56 px
│   └── ClipSheet  (ui/clip_sheet.py)   resto — hoja de contactos
├── RoomPalette (ui/room_palette.py)
└── StatusBar   (ui/status_bar.py)   24 px
```

Lógica pura, sin Qt: `history.py`, `filters.py`, `rooms.py`, `keyboard.py`,
`player.py`, `probe.py`, `proxy_match.py`, `binarios.py`, `ingest.py`,
`bins.py`.

## 3. La importación por bins — HECHA (2026-08-09, de noche)

**Ya no es una tarea abierta.** Se hizo entera en una sesión, con Bruno
dormido: brainstorm → mockup que él aprobó viéndolo → spec → plan → seis fases
implementadas con TDD y revisadas una por una.

- Spec: [`specs/2026-08-09-bins-por-camara-design.md`](specs/2026-08-09-bins-por-camara-design.md)
- Plan: [`plans/2026-08-09-bins-por-camara.md`](plans/2026-08-09-bins-por-camara.md)
- Mockup aprobado: [`mockups/bins-2026-08-09/mockup.html`](mockups/bins-2026-08-09/mockup.html), **propuesta A**

### La decisión de fondo, ya tomada

La hoja **ya agrupaba, y agrupaba por cuarto** (`ClipSheet._group_of` devolvía
`room_label`). O sea que los bins no llegaban a un espacio vacío: competían con
la jerarquía que había. Se le dibujaron a Bruno las dos salidas y eligió
mirándolas:

- **A (elegida)** — el bin agrupa arriba, el cuarto baja a subgrupo adentro.
  Costo aceptado: un cuarto grabado con dos cámaras aparece dos veces, una en
  cada bin.
- **B (descartada)** — el cuarto se vuelve solo una etiqueta en la tarjeta. Más
  limpio, pero se pierde el bloque por cuarto que Bruno usa para pintar en lote.

**No reabrir sin razón nueva.** El costo de A se evaluó y se aceptó.

### Lo que quedó construido

| | |
|---|---|
| **El dato** | `bins.py` — `BinTree`, sin Qt. Va por índice de clip y viaja **aparte** en el autosave: `Clip.to_dict()` es el contrato con el plugin y no se tocó |
| **Importar** | arrastrar carpetas y archivos; sobre un bin se suman ahí, en el vacío nace un bin nuevo con el nombre de la carpeta |
| **Agregar agrega** | los índices viejos no se mueven, así que portadas, proxies, marcas e historial sobreviven |
| **Proxies** | por bin, con su propio patrón de nombre — la Sony con `S03` y el dron con el suyo, sin pisarse |
| **La hoja** | encabezado por bin (nombre editable, origen, conteos, insignia de proxies), pegado arriba al hacer scroll, colapsable, con menú de clic derecho |
| **Filtrar** | chips por bin, que también acotan la cola de las flechas |
| **En modo clip** | el bin junto al nombre del archivo, con orden de sacrificio velocidad → bin → elidir |

### Lo que se arregló de paso

- **Las portadas se caían al importar una segunda carpeta** (lo reportó Bruno).
  Causa: importar reconstruía la lista entera y `load_clips` limpia el
  historial, vacía los proxies y recrea todas las tarjetas — con sus miniaturas
  adentro.
- **Se re-pedían las portadas de todo** al agregar material o al enganchar
  proxies, duplicando trabajos sobre la misma carpeta y el mismo socket IPC.
  Eso es lo que ponía a girar los abanicos «sin haber hecho nada».
- **Tres segfaults intermitentes de la suite**, todos de la misma familia:
  widgets destruidos desde adentro de su propia señal, y un mpv real
  encendiéndose porque `cerrar_clip` tocaba `self.player`, que se construye
  perezosamente justo para que eso no pase.
- **Un cuarto segfault, el que quedaba** (encontrado después de escribir esto,
  midiendo 40 corridas: 2 caídas contra 0 en el commit anterior a los bins).
  Cada trabajo en segundo plano traía su propio portador de señales, que nacía
  en el hilo de la interfaz y moría en un hilo del `QThreadPool`. Ahora el
  portador es uno solo, de la ventana (`SeñalesDeTrabajos`). Medido después:
  **76 corridas completas seguidas sin una caída**.
- **Código muerto borrado**: `IngestTree`/`IngestFolder` ya no los usaba nadie
  desde la interfaz. `ingest.py` conserva `VIDEO_EXTENSIONS`, `SUFIJO_PROXY`,
  `es_archivo_de_proxy` y `archivos_de_video`.

### Lo que NO entró, y por qué

- **LUT por bin** — falta comprobar dentro de Premiere que el parámetro de LUT
  de entrada de Lumetri acepta una ruta. El bin ya existe para colgárselo.
- **Generar los proxies del dron** — medido y aprobado por Bruno, es otra
  entrega.
- **Mover clips entre bins arrastrando**, **bins anidados**, y **que el bin
  viaje a Premiere como carpeta del proyecto**.

### Qué quedó MEDIDO y qué quedó SUPUESTO

Se separa a propósito, con el mismo criterio de la sección 4.b: un veredicto sin
su evidencia se vuelve a discutir en tres meses.

**Medido:**

- **1007 tests en verde**, y el número de corridas importa más que el de tests:
  hubo **cuatro segfaults intermitentes** en esta entrega, y el último salió
  después de que la suite llevara **decenas de corridas limpias seguidas**.
- **La lección más cara de la noche, y la que hay que recordar:** «corrió
  limpio veinte veces» **no prueba nada** contra un fallo del 5 %. Veinte
  limpias salen por azar el 36 % de las veces; setenta y seis, el 2 %. El
  cuarto segfault sobrevivió a tres rondas de «ya quedó» porque nadie hizo esa
  cuenta. La forma correcta es **contar fallos sobre un número de corridas
  decidido de antemano**, y **medir el commit anterior con el mismo número**
  para saber si el fallo es nuevo: aquí fue 2 de 40 contra 0 de 40, y ese par
  de números es lo que convirtió «parece que a veces truena» en «lo trajimos
  nosotros».
- **Los cuatro, cada uno con su causa identificada**, no parcheados a ciegas:
  un `QGraphicsDropShadowEffect` que resultó **no** ser el culpable; un mpv
  real encendiéndose porque `cerrar_clip` tocaba `self.player`, que se
  construye perezosamente justo para evitarlo (el volcado traía 100 menciones
  de `MPVEventHandlerThread`, y con la guarda: 0); widgets destruidos desde
  adentro de su propia señal, con 51 menús vivos tras 50 aperturas; y el
  cuarto, un portador de señales por trabajo que nacía en el hilo de la
  interfaz y moría en uno del `QThreadPool` (medido: **199 de 200 murieron en
  el hilo equivocado**).
- **El cuarto arreglo también se midió antes de elegirlo**, y menos mal:
  contra un reproductor dirigido, el portador `QWidget` daba 2 caídas de 15,
  **pasarlo a `QObject` por trabajo daba 15 de 15** —o sea, la corrección
  «obvia» empeoraba el bug— y un portador único de la ventana daba 0 de 15.
  Sin esa medición se entregaba algo peor con la suite en verde.
- **Lo visual, mirando el pixel** y no de palabra: la hoja con tres bins, uno
  colapsado; el encabezado pegado; el menú de clic derecho; las dos zonas de
  arrastre; la barra de filtros a 1027 px (el mínimo real de la ventana), donde
  la fila de bins envuelve a segunda línea y cuesta 48 px de alto y **0 de
  ancho**; y el visor a 900 y a 430 px comprobando el orden de sacrificio.

**Supuesto, no medido — esto es lo que falta y no se puede afirmar:**

- **Nadie ha usado esto con material real.** Todo se probó con archivos
  inventados y `ffprobe` falso. Los 109 clips de la Sony y los 23 del dron no
  han pasado por aquí ni una vez.
- **El arrastre desde Finder de verdad.** Bajo `offscreen` no se puede arrastrar;
  lo que está probado son eventos sintéticos. El arranque del arrastre, el
  cursor y el `dragLeave` al salir de la ventana **no están comprobados**.
- **El encabezado pegado en una pantalla Retina real**, con el scroll por
  trackpad y su inercia.
- **Cuánto cuesta todo esto con 132 clips de verdad.** Los ~12 ms de re-acomodo
  son una medición vieja, de antes de que la hoja agrupara en dos niveles.

### Advertencia para la primera vez que Bruno abra esto

La sesión que tiene guardada es **anterior a los bins**, así que al restaurarla
cae en **un solo bin** con el nombre de la carpeta del primer clip — y ahí
adentro están mezclados la Sony y el dron. Los proxies por bin no le van a
servir sobre esa sesión. **Conviene empezar de cero, arrastrando cada carpeta a
su bin.** La otra salida sería «Quitar del proyecto», que se lleva la
clasificación, las marcas y el historial.

### El pedido original, para no perder el porqué

Lo que Bruno pidió, textual:

> «No me encanta la importación. Es difícil importar archivos individuales,
> solo se pueden carpetas. No se distinguen entre carpetas o cámaras. Me
> gustaría que fuera tan fácil como drag and drop en bins, como en Premiere. Y
> de esa forma los videos que estén en ciertos bins ya sé que son de Sony,
> otros ya sé que son de un dron. Poder hacer clic derecho en esos bins y
> enlazar los proxies. También meter los LUTs a esos videos.»

**Por qué el fondo del pedido era correcto, y no solo comodidad:** el proxy y
el LUT son propiedades **de la cámara**, no del clip suelto. El LUT de S-Log de
la FX30 no va sobre material del dron. Antes no había forma de decir «estos 23
son del dron», y por eso enganchar proxies era un gesto por shooting entero en
vez de por fuente.

**La advertencia de alcance sigue vigente**, y está en `CONTEXTO-Y-METAS.md`:
no se trata de reconstruir el panel de proyecto de Premiere con jerarquía y
arrastre anidado. Se trata de saber de qué cámara viene cada clip y poder
actuar por cámara. Lo entregado se queda de este lado de esa línea a propósito.

## 4. Lo demás que está abierto

| Qué | Estado | Quién sigue |
|---|---|---|
| **Proxies del dron** | medido y decidido: el `.LRF` **no sirve** ni renombrado (contenido corrido 1–5 cuadros, variable por clip). Hay que generarlos del original: ~10 s por cada 6 s de video | falta escribir la función; Bruno ya dijo que sí |
| **LUT en Premiere** | alcanzable: la API deja poner efectos al *master clip* sin armar secuencia | falta un spike DENTRO de Premiere: ¿el LUT de entrada de Lumetri acepta una ruta? |
| **Etiqueta dorada de la estrella** | escrita (`destacado→MANGO`) con guarda si el nombre no existe | falta correr `autocheck-tests.js` en Premiere |
| **Empaquetado** | `.app` de 175 MB que arranca sin Homebrew; 0 de 214 binarios apuntan a Homebrew | falta abrirlo **en otra Mac**, por USB |
| **`.LRF` como clips** | DJI escribe un `.LRF` junto a cada `.MP4` y el ingest los toma como material: cada toma del dron aparece **dos veces** | decisión de Bruno: ¿fuera, como los `S03`? |
| **Caída al cerrar** | una de ~30 corridas murió **después** de pasar los 831 tests, en el apagado. 26 corridas seguidas no lo repitieron | anotado, sin arreglo inventado |

## 4.b Lo que ya se midió, para no volver a medirlo

Dos conclusiones de arriba costaron trabajo y se re-litigarían solas si solo
quedara escrito el veredicto.

### Por qué el `.LRF` del dron no sirve como proxy

El `.LRF` **ya es un MP4 por dentro** (mismo contenedor, H.264 720p), así que
renombrarlo lo deja perfectamente reproducible. El problema es otro: **el
contenido no está alineado con el original.**

Medido sobre la carpeta real de dron de Bruno, 23 pares:

- **fps idéntico en los 23**, y el `.LRF` **nunca es más largo**: le faltan
  entre 0 y 3 cuadros al final.
- Pero comparando imagen contra imagen —extraer el mismo cuadro de los dos y
  medir la diferencia media de píxel— el mejor calce **no cae en el mismo
  número de cuadro**: en el clip `0009` el cuadro 500 del original se parece
  más al **505** del `.LRF`; en el `0006`, a **+1**. En un clip casi estático
  la curva sale plana y el método no concluye — por eso se midió en varios.
- Comparando por **tiempo** en vez de por cuadro pasa lo mismo, así que no es
  un artefacto de cómo se numeran los cuadros: es el contenido.

**Consecuencia:** para *ver* da igual; para **marcar in/out** no, porque el
desfase cambia de clip a clip. Y la validación que ya tiene la app los
rechazaría igual.

**La alternativa medida**, generando el proxy desde el original con el
codificador del chip (`h264_videotoolbox`, lado corto 720):

| | original | proxy generado |
|---|---|---|
| tamaño | 285 MB | 17 MB |
| cuadros | 1010 | **1010, exactos** |
| tiempo | — | ~10 s por cada 6 s de video |

Ojo con un detalle que costó una medición equivocada: **los MP4 del dron traen
una miniatura JPEG incrustada como segunda pista de video**, y sin `-map 0:v:0`
ffmpeg transcodifica esa en vez del video.

### Qué hace falta para repartir la app

El detalle operativo vive en el `README.md` (sección «Empaquetar como app»), y
lo que hay que saber para decidir es:

- La **firma propia** (ad-hoc) es gratis, se hace sola al armar, y es lo que el
  chip M exige para que un binario arranque. Ya está puesta.
- La **firma de Apple** (99 USD/año) NO hace falta para el caso de Bruno.
- **Por USB o carpeta compartida la app abre directo.** Mandada por internet,
  la primera vez hay que ir a *Configuración → Privacidad y seguridad → Abrir
  de todos modos*, y eso se repite con cada versión nueva.
- Esto es **cómo funciona macOS 26 según la documentación de Apple, no
  comprobado**: la única prueba válida es abrirla en otra computadora.

## 5. Cómo encontrar bugs en este proyecto

Lo que funcionó, **ordenado por lo que realmente encontró**. Casi ningún bug de
los últimos meses lo detectó la suite.

| Detector | Qué encontró |
|---|---|
| **Que Bruno la use con su material** | Las portadas que no se generaban nunca, el borde invisible del clip actual, la marquesina que no marcaba pick, los verticales dibujados horizontales, los ventiladores |
| **Mirar el píxel, no el estilo** | El borde de estado: la regla de QSS era correcta y **nunca llegó a la pantalla**, tapada por la miniatura. Los tests comprobaban la cadena de texto |
| **Montar la app COMPLETA al medir** | Los tests de UI no aplicaban la hoja de estilos, y sin ella los controles miden el doble. Costó un diagnóstico entero y un arreglo mal justificado |
| **Empaquetar** | Que `ffprobe` y `mpv` se buscaban por nombre, y que ese fallo era invisible: importaba 0 clips sin decir nada |
| **Perfilar con cProfile** | Tres veces trabajo desperdiciado que nadie sospechaba |
| **Comparar la fase contra lo PROMETIDO** | Que la marquesina faltaba: un plan recortó el alcance en silencio |
| **Estados límite y datos degenerados** | El rango invertido, cuatro veces — la última, exportándose crudo a Premiere |
| **Recorrido aleatorio con invariantes** | Nada, en 7 600 pasos. Vale como red, no como detector |

### Cuatro trampas de medición que ya costaron tiempo

1. **Un arnés que no monta la app completa mide otra app.** (La hoja de estilos.)
2. **Contar widgets sin procesar `DeferredDelete`** da falsas fugas.
3. **Un doble de pruebas puede tapar el bug que existe.** (`frame-step` pasaba
   su test *por* la línea que lo rompía.)
4. **Leer `.text()` sin mirar `isHidden()`** convierte un widget escondido en
   un falso bug.

## 6. Trampas concretas del código

### De Qt

- **La regla global `QWidget { background-color }` alcanza a las QLabel.**
  Cualquier etiqueta sobre algo pintado declara `transparent`.
- **Un `QWidget` puro ignora `background-color` de QSS** sin `WA_StyledBackground`.
- **El QSS de un widget NO se ve si un hijo lo tapa.** El borde de la tarjeta
  vivió cinco fases sin dibujarse. Si algo tiene que verse encima de una
  imagen, se pinta en el `paintEvent`, no con QSS.
- **Un `QShortcut` consume la tecla y nunca avisa de que se soltó.** Por eso
  `1`–`9` NO son atajos: con ellos el pincel no se arma.
- **`setStyleSheet` es carísimo**: nunca llamarlo si el estilo no cambió.
- **Sin la hoja de estilos, Qt le da a cada `QPushButton` 80 px de ancho
  mínimo.** Medir sin ella da números de otra app.
- **`qtbot.addWidget` no muestra el widget.** Sin `show()` el layout no corre.
- **Ningún objeto de Qt debe nacer ni morir por trabajo del `QThreadPool`.** El
  pool destruye el `QRunnable` en su propio hilo, y con él todo lo que cuelgue.
  Los portadores de señales son de la ventana, no del trabajo
  (ver `SeñalesDeTrabajos` en `main_window.py`, con los números).
- **No guardes un `QThread.currentThread()` de otro hilo en una lista.** El
  hilo muere, el envoltorio de Python sigue vivo, y cuando Qt reusa esa
  memoria para otro widget el objeto nuevo se lee como un `QThread`. Para
  saber en qué hilo estás dentro de una prueba: `threading.get_ident()`.

### De macOS

- **Las rutas de socket Unix se cortan en 104 caracteres.** El socket de las
  miniaturas vivía en el caché y medía 108: **la extracción falló siempre**.
- **`settimeout` + `makefile()` no se mezclan**: en cuanto vence un timeout, el
  objeto de archivo queda inservible. Se espera con `select`.
- **Los binarios se buscan con `binarios.ruta_de()`**, nunca por nombre: dentro
  del `.app` no están en el PATH.

### De este proyecto

- **`item_widgets` va por índice de clip, no por posición visual**, y agrupar
  es **re-colocar, jamás reconstruir**.
- **Dos vistas del mismo dato se contradicen solas.** Van siete veces.
- **Los tamaños y duraciones van por índice**, así que `load_clips` los limpia
  igual que al historial.
- **`categoria_path` sigue siendo una LISTA** aunque los cuartos sean planos, y
  el plugin **ignora lo que no conoce**.

## 7. Cómo trabajar

- **Español mexicano en todo**: chat, commits, docs, comentarios y sobre todo
  los textos de la app.
- **En el chat, corto y sin lenguaje técnico.** Bruno es editor, no
  programador: qué cambió y qué va a ver él.
- **Se trabaja directo sobre `master`.**
- **Higiene de archivos**: nada suelto en la raíz; un archivo nuevo que
  reemplaza a otro se acompaña de borrar el viejo en el mismo commit.
- **No agregues funciones que no estén acordadas.** Si el mockup o
  `DECISIONES.md` no cubren un caso, se pregunta.
- **No borres tests en bloque.** Clasifica cada uno: *se reescribe*, *murió a
  propósito*, o *se conserva*.
- **Verificación visual real**: si no se miró la imagen, no se afirma.
- **Audita el plan ejecutando, pero después implementa.** Lo que queda por
  descubrir sale de construir.
