# Bins por cámara — diseño

*(Spec. Fecha: 2026-08-09. Mockup acordado:
`docs/superpowers/mockups/bins-2026-08-09/mockup.html`, propuesta **A**,
aprobada por Bruno después de verla en pantalla.)*

## 1. El problema

Bruno lo dijo así:

> «No me encanta la importación. Es difícil importar archivos individuales,
> solo se pueden carpetas. No se distinguen entre carpetas o cámaras. Me
> gustaría que fuera tan fácil como drag and drop en bins, como en Premiere.
> Y de esa forma los videos que estén en ciertos bins ya sé que son de Sony,
> otros ya sé que son de un dron. Poder hacer clic derecho en esos bins y
> enlazar los proxies. También meter los LUTs a esos videos.»

El fondo no es comodidad. **El proxy y el LUT son propiedades de la CÁMARA,
no del clip suelto.** Un LUT de S-Log de la FX30 no va sobre material del
dron, y los proxies de cada cámara se llaman distinto: la Sony escribe
`C0001S03.MP4` junto a `C0001.MP4`, y los del dron habrá que generarlos con
el nombre que decidamos nosotros. Hoy `adjuntar_proxies` deduce **un solo
patrón para todo el proyecto** (`main_window.py::adjuntar_proxies` →
`proxy_match.patron_de_proxy`), así que en un proyecto con dos cámaras una de
las dos se queda siempre sin proxy. No es un caso hipotético: es el proyecto
`IAV-2608.04-A` que Bruno tiene ahora mismo.

Y hay tres bugs de uso real que cuelgan del mismo lugar:

1. **Importar una segunda carpeta reinicia todo.** `_on_import_folders` llama
   a `_load_clips_from_ingest`, que reconstruye la lista completa y llama a
   `load_clips`, y `load_clips` limpia el historial, vacía `_proxy_sizes` y
   `_proxy_candidatos`, y hace `_refresh_sheet(force_rebuild=True)`. Efecto
   visible: se te caen las portadas ya generadas y los proxies ya enganchados.
   Bruno lo reportó tal cual («al importar una segunda carpeta no se cargan
   las portadas»).
2. **No se pueden importar archivos sueltos**, solo carpetas
   (`QFileDialog.getExistingDirectory`).
3. **No hay drag and drop en ninguna parte de la app.** Comprobado:
   `grep setAcceptDrops src/` no devuelve nada.

## 2. La decisión de fondo: dos jerarquías compitiendo

Esto salió leyendo el código, y no estaba en el handoff: **la hoja de
contactos ya agrupa, y agrupa por cuarto.** `ClipSheet._group_of` devuelve
`clip.room_label`, y `_regroup` arma un `_GroupBlock` por cuarto, con «Sin
clasificar» siempre primero.

O sea que los bins no llegan a un espacio vacío: compiten con la agrupación
que ya existe. Las dos salidas honestas se dibujaron en el mockup y Bruno
eligió mirándolas:

- **A (elegida)** — el bin agrupa arriba, el cuarto baja a subgrupo dentro del
  bin. No se pierde nada de lo de hoy. Costo aceptado: un cuarto grabado con
  dos cámaras aparece dos veces, una en cada bin.
- **B (descartada)** — el bin agrupa y el cuarto se vuelve solo una etiqueta
  en la tarjeta. Más limpio, pero se pierde el bloque por cuarto que Bruno usa
  para pintar en lote.

**No reabrir esto sin razón nueva.** El costo de A ya se evaluó y se aceptó:
ver el mismo cuarto en dos bins es información (lo grabaste con dos cámaras),
no ruido.

## 3. Qué es un bin

Una tanda de material que entró junta. En la práctica, una cámara o una
tarjeta.

- **Nombre**: el de la carpeta de origen, editable con doble clic o `F2`.
  Ya existe la pieza: `IngestFolder.display_name` y `IngestTree.rename_folder`.
- **Sin anidar.** No hay bins dentro de bins. No es el panel de proyecto de
  Premiere y no pretende serlo (ver `CONTEXTO-Y-METAS.md`, «Qué NO es una
  meta»).
- **Cada clip pertenece a exactamente un bin.**
- **Sobrevive a guardar y restaurar la sesión.**

### Dónde vive el dato

`Clip.to_dict()` **no se toca**: esa forma es el contrato con el plugin de
Premiere. El bin viaja aparte en el autosave, con el mismo criterio que ya se
usó para `tamanos`, `duraciones` y `rotaciones`
(`main_window.py::_write_autosave_now`):

```json
"bins": [
  {"nombre": "Dron", "origen": "/…/02. VIDEO DRONE", "clips": [130, 131, …]},
  {"nombre": "Sony FX30", "origen": "/…/01. VIDEO CAMARA", "clips": [0, 1, …]}
]
```

Los índices son los mismos índices de clip que ya usan `_proxy_sizes`,
`_clip_durations` y el historial. Una sesión vieja sin la llave `bins` se
carga con **un solo bin** que contiene todo, nombrado con la carpeta que
tenga el primer clip: nadie pierde una sesión por actualizar.

## 4. La interfaz

### 4.1 El encabezado del bin

Es la única pieza nueva de la hoja. Va arriba de las tarjetas de su bin y
lleva, de izquierda a derecha:

`▾` colapsar · marca de cámara · **nombre** · carpeta de origen (en mono, apagado) ·
`23 clips` con los puntos de pick/★/reject · insignia de proxies · `⋯`

- **Se queda pegado arriba** al hacer scroll dentro de su bin, con sombra
  cuando está pegado. Esto es nuevo: el encabezado de grupo de cuarto que hay
  hoy (`_GroupBlock`) **no** se pega, se va con el scroll. Si pegarlo resulta
  caro o frágil dentro del `QScrollArea`, se entrega sin pegar — es lo único
  de esta sección que puede caerse sin romper el diseño.
- **Clic** colapsa y expande. Un bin colapsado sigue contando en los totales
  y sus clips siguen en la cola de las flechas (colapsar es visual, no un
  filtro).
- **Doble clic en el nombre** lo renombra en el lugar.
- La **insignia de proxies** dice `sin proxies`, `proxy 1080p · 23/23` o
  `proxy · 21/23` cuando faltan. El «21/23» es a propósito visible: dos
  archivos no calzaron cuadro a cuadro y **no se engancharon**, que es mejor
  que enganchar un proxy corrido y poner el in en el cuadro equivocado.

### 4.2 El menú de clic derecho

Sobre el encabezado (y también con el botón `⋯`):

| Renglón | Qué hace |
|---|---|
| Renombrar bin… (`F2`) | Edición en el lugar |
| **Enlazar proxies…** | El flujo de hoy, pero acotado a este bin |
| Quitar proxies de este bin | Desengancha; las portadas se vuelven a pedir del original |
| Seleccionar los N clips (`⌘A`) | Alimenta lo que ya existe de selección múltiple |
| Colapsar | Igual que el clic en el encabezado |
| Quitar del proyecto | Saca los clips del bin. No borra nada del disco |

### 4.3 Arrastrar

La ventana acepta archivos y carpetas. Dos zonas, las dos dibujadas en el
mockup:

- **Sobre un bin** — resalta ese bin y dice «Soltar en “Dron” · 6 archivos ·
  se suman a los 23 que ya tiene».
- **En el vacío de la hoja** — una zona punteada al final que dice «Bin nuevo:
  “02. VIDEO DRONE”». El nombre sale de la carpeta común de lo que traes.

Reglas del arrastre:

- Se aceptan carpetas y archivos mezclados. De una carpeta se toman sus
  archivos de video directos (mismo criterio que `IngestTree.import_folders`,
  que no baja recursivamente).
- Se filtra con `VIDEO_EXTENSIONS` y se descartan los proxies de cámara por
  nombre (`es_archivo_de_proxy`, el sufijo `S03`), igual que hoy.
- **Un archivo que ya está en el proyecto no entra dos veces.** Se ignora en
  silencio si ya está en el mismo bin; si está en otro, tampoco se duplica.
- Si nada de lo que soltaste es video, se dice por qué en vez de no pasar
  nada.

### 4.4 El filtro por bin

Una fila más en la barra de filtros: `Bin: Todos · Dron 23 · Sony FX30 109`.
Se suma a `FilterState` como un campo más (`bin: str = "todos"`), junto a
`mostrar`, `estado` y `busqueda`, y por lo tanto **cambia también la cola de
las flechas** — que es como funcionan todos los filtros de esta app y no una
excepción (ver `filters.py`).

### 4.5 En modo clip

El nombre del bin aparece junto al del archivo en la barra de arriba del
video, con la misma marca de cámara. Es la respuesta a «¿de dónde salió este
clip?» sin cambiar de vista. Compite por espacio con el nombre del archivo y
la insignia de proxy: se acorta con la misma regla de elisión que ya usa
`video_stage.set_file_label`.

### 4.6 Navegación

**Las flechas siguen de corrido** y cruzan de un bin al siguiente sin
frenarse. Decidido por Bruno.

Precisión importante, comprobada en el código: **la cola de las flechas no
sigue el orden visual y nunca lo ha seguido.** `filters.cola` devuelve los
índices en orden de clip —el orden de rodaje— mientras la hoja los dibuja
agrupados por cuarto. Con bins pasa lo mismo, y encaja solo: como el material
de cada bin se agrega al final, el orden de clip **ya es** el orden de
importación de los bins. Dentro de un bin, las flechas siguen el orden de
rodaje, no el de los subgrupos.

No se agrega reordenamiento de la cola. Sería un cambio de comportamiento que
nadie pidió, en la pieza de la que dependen a la vez la hoja, las flechas y el
contador del visor.

## 5. Proxies por bin

El cambio de verdad. `adjuntar_proxies` deja de mirar `self.clips` y mira los
clips **de un bin**:

1. El menú del bin abre el selector de archivo sobre el primer clip de ese
   bin (o sobre el clip actual si pertenece a ese bin).
2. `patron_de_proxy` deduce prefijo y sufijo del par elegido — sin cambios.
3. `emparejar_con_patron` se corre **solo con las rutas de ese bin**.
4. `_sondear_proxies` valida uno por uno como hoy (mismos cuadros, mismo fps,
   misma orientación) y engancha solo los que calzan.

`_proxy_sizes` y `_proxy_candidatos` siguen indexados por índice global de
clip, así que **no hay que reescribirlos**: solo se llenan por partes. Eso
también significa que enlazar los proxies del dron no puede borrar los de la
Sony — hoy `_sondear_proxies` empieza con `self._proxy_sizes = {}`, y eso
tiene que dejar de barrer con todo y limpiar únicamente los índices del bin
que se está tocando. **Este es el punto exacto donde un descuido rompe algo
que ya funciona.**

## 6. Lo que se arregla de paso

Importar deja de reconstruir el mundo. Hoy: `_on_import_folders` →
`_load_clips_from_ingest` → `load_clips`, que limpia historial y proxies y
reconstruye la hoja entera.

Después: agregar material **agrega**. Los clips que ya estaban conservan su
índice, su portada ya generada, su proxy enganchado y sus marcas; el historial
sigue siendo válido porque los índices viejos siguen apuntando a los mismos
clips. Solo los clips nuevos se sondean y se les piden portadas.

Esto es un requisito, no un efecto secundario: es el bug que Bruno reportó.

## 6.b Enmienda del 2026-08-09 (mañana): el bin es una cosa propia

**Esta sección corrige el alcance de arriba. Donde se contradigan, manda esta.**

Bruno usó la primera entrega y el reclamo fue directo: «yo te dije que lo quería
como Premiere. Quiero poder arrastrar los archivos a un bin.»

**Tenía razón, y el error fue mío.** Él pidió «drag and drop en bins, como en
Premiere» y yo lo interpreté como *arrastrar carpetas desde el Finder a la app*.
Lo que en Premiere hace que un bin sea un bin —**crearlo vacío y meterle clips
arrastrando, y mover un clip de un bin a otro**— quedó fuera. Peor: lo saqué del
alcance ofreciéndolo como una opción más de una lista, en vez de nombrarlo por
lo que era, un recorte de su pedido.

Con la primera entrega, un bin **solo nace al importar**. Si te equivocas al
importar, no puedes arreglarlo arrastrando: hay que quitar el bin entero y
volver a empezar. Eso no es como Premiere.

### Lo que cambia

1. **La hoja es lo primero que se ve al abrir la app**, siempre.
2. **Se pueden crear bins vacíos**, con un botón en la barra de la hoja. Nacen
   sin clips y con el nombre editable en el acto.
3. **Un bin vacío no desaparece solo.** Si desapareciera, no se podría crear
   primero y llenar después — que es justo el gesto que se está agregando.
4. **Los clips se arrastran entre bins**, uno o varios a la vez (lo que esté
   seleccionado se va junto).
5. **Existe una sección «Sin bin», siempre la primera**, con los clips que
   todavía no pertenecen a ninguno. Se esconde cuando está vacía.

### Las tres decisiones que tomó Bruno

- **Los clips sueltos van a «Sin bin»**, una sección fija hasta arriba, no
  esparcidos ni metidos en un bin inventado.
- **Arrastrar cambia el bin y NADA más.** Soltar un clip encima del subgrupo
  «Cocina» del bin de la Sony lo manda a ese bin, pero **no lo clasifica como
  cocina**. Los cuartos se siguen poniendo con el teclado. Razón: si los dos
  ejes se manejaran arrastrando, un gesto mal soltado cambiaría lo que no
  querías, y el cuarto es el dato que más trabajo cuesta.
- **El proxy viaja con el clip.** Es del clip, no del bin: mover un clip a otra
  cámara no lo desengancha. Un bin puede terminar con proxies de resoluciones
  distintas y la insignia lo dirá.

### El gesto, y por qué no choca con lo que ya existe

La hoja ya usa el mouse para tres cosas. El arrastre de clips entra en el único
hueco que quedaba libre, y eso **no es casualidad, es la razón de elegirlo**:

| Gesto | Qué hace hoy |
|---|---|
| Pasar el mouse **sin apretar** sobre una tarjeta | escrubea la miniatura (`ClipCard` tiene `setMouseTracking(True)`) |
| Arrastrar en el **vacío** | marquesina de selección |
| Mantener `1`–`9` y mover | pincel de cuartos |
| **Botón izquierdo apretado y mover sobre una tarjeta** | **nada — aquí entra el arrastre de clips** |

Reglas de precedencia, para que ninguno se coma a otro:

- Con una tecla de cuarto apretada **gana el pincel**; no se inicia arrastre.
- El arrastre arranca al superar la distancia de arrastre estándar de Qt, no al
  primer pixel: un clic con la mano temblorosa sigue siendo un clic.
- Al arrastrar, la miniatura **deja de escrubear** hasta soltar.

### Lo que NO cambia

- Los bins siguen **sin anidarse**.
- Mover un clip entre bins **no toca su índice**, así que no se corre nada:
  ni proxies, ni duraciones, ni el historial. Es el cambio barato de esta
  enmienda y conviene que siga siéndolo.
- El manifiesto a Premiere no cambia.

## 7. Qué NO entra

Decidido con Bruno, para que la primera entrega llegue:

- **LUT por bin.** Falta comprobar dentro de Premiere que el parámetro de LUT
  de entrada de Lumetri acepta una ruta de archivo. Va después, y el bin ya va
  a existir para colgárselo.
- **Generar proxies del dron.** Ya está medido (285 MB → 17 MB, 1010 cuadros
  exactos, ~10 s por cada 6 s; ver el handoff §4.b), pero es otra entrega.
- ~~**Mover clips entre bins arrastrando.**~~ — **revertido por la §6.b.** Esto
  decía «si te equivocaste al importar, quitas el bin y lo vuelves a soltar», y
  esa frase es el error de alcance completo, escrito con todas sus letras. Era
  el corazón del pedido de Bruno y lo puse en la lista de lo que no se hace.
- **Bins anidados.**
- **Que el bin viaje a Premiere como carpeta del proyecto.** Candidato claro
  para después; el manifiesto no cambia en esta entrega.

## 8. Cómo se comprueba

- **Tests** para todo lo que es lógica y no pixel: qué archivos entran al
  soltar (carpetas, sueltos, mezclados, repetidos, sin video), que agregar un
  bin no borra proxies ni portadas ni historial, que el patrón de proxy de un
  bin no toca al otro, que una sesión vieja sin `bins` se carga en un bin
  único, y que el filtro de bin cambia la cola de las flechas.
- **Verificación visual real**, según `CLAUDE.md`: `grab()` de la hoja con dos
  bins, uno colapsado, y del encabezado pegado arriba. Si no se miró la
  imagen, no se afirma.
- **Nada de diálogos modales con `exec()`** en las piezas nuevas. La F3 mató
  el último que había justamente porque colgaba la suite bajo `offscreen`
  (`room_rail._pedir_cuarto_nuevo` todavía usa `QInputDialog`, y por eso la
  edición del nombre del bin va en el lugar, no en un diálogo).
