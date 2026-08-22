# Contexto y metas del proyecto

*(Última actualización: 2026-08-10, al cierre de la sesión en la que se
generaron los proxies, se contestó el LUT dentro de Premiere y se sacaron los
`.LRF` del ingest. Este documento describe **intención y dirección**, y lleva
la cuenta de lo hecho y lo que falta — para decisiones técnicas ya tomadas,
ver `CLAUDE.md`; para qué es la app y cómo correrla, ver `README.md`; para el
detalle técnico de cada entrega y de cada bug, ver el handoff.)*

## Estado actual

**La app clasifica un shooting completo sin tocar el mouse, agrupa el material
por cámara, le genera los proxies, y el proyecto es un archivo que se puede
mover.** Llega reproduciendo, se marca con el teclado, se cruza a la hoja de
contactos, se pinta por lotes y se exporta a Premiere, que arma el proyecto
solo.

**1355 tests.** Las 40 corridas seguidas sin fallo se midieron sobre 1337, o
sea antes de la generación de proxies: ese número no se ha vuelto a medir.

**Lo que sigue sin comprobarse, y atraviesa todo lo demás:** desde los bins en
adelante, **nada se ha usado con el material real de Bruno**. Se midió con
archivos inventados, `ffprobe` falso y los tres clips de `sample-media/`. Sus
132 clips no han pasado por aquí. La única excepción es la generación de
proxies, que sí se corrió contra un clip real de `sample-media/` de punta a
punta —67 MB → 1.6 MB, mismos cuadros y fps— pero no contra una tarjeta
entera. Lo anterior a los bins sí se usó de verdad, y de ese uso salieron más
bugs que de cualquier revisión.

**Por eso lo primero de la lista de abajo no es una función nueva:** es correr
un shooting completo con la app.

---

## Lo que se hizo (2026-08-09 y 10)

Tres entregas seguidas, cada una con su spec, su plan y su revisión por fase.

### 1. Bins por cámara

El material se agrupa por **bin** —una cámara, una tarjeta— con encabezado
propio: nombre editable, carpeta de origen, conteos e insignia de proxies. Clic
derecho ahí para enlazar o quitar proxies, seleccionar sus clips o quitarlo del
proyecto. Hay filtro por bin, y el nombre del bin aparece junto al del archivo
en modo clip.

**El porqué de fondo, que es lo que lo justifica:** el proxy y el LUT son
propiedades **de la cámara**, no del clip suelto. Antes enganchar proxies era un
gesto por shooting entero, con un solo patrón de nombre — así que con dos
cámaras una siempre se quedaba sin proxy.

Se arregló de paso el bug que Bruno reportó: **importar una segunda carpeta ya
no tira las portadas** ni los proxies ni el historial.

### 2. Bins arrastrables

Bruno probó lo anterior y dijo: «yo te dije que lo quería como Premiere, quiero
poder arrastrar los archivos a un bin». **Tenía razón y el recorte había sido
mío**: se interpretó «drag and drop en bins» como arrastrar carpetas desde el
Finder, y quedó fuera lo que hace que un bin sea un bin.

Ahora: la app **abre en la hoja**, hay botón para **crear un bin vacío**, los
clips **se arrastran entre bins** (uno o varios a la vez), y hay sección **«Sin
bin»** para lo que todavía no acomodaste. Arrastrar cambia el bin y **nada
más** — los cuartos siguen con el teclado, para que un gesto mal soltado no
reclasifique.

### 3. Proyectos guardables y reencontrar la media

Cada proyecto es un archivo **`.cvproj`** que vive donde Bruno quiera. La app
abre en una **lista de recientes**; el proyecto que ya no está se ve apagado y
dice por qué, en vez de desaparecer. La sesión escondida de antes **se migra
sola** y no se borra.

Y lo que hacía falta para que sirva en otra computadora: al abrir, si falta
material, **se avisa por bin** y se reencuentra señalando una carpeta. Cada
archivo se **confirma por peso y duración** antes de engancharse.

**El modo de fallo que todo eso existe para evitar:** enganchar el archivo
equivocado es peor que no encontrarlo, porque Bruno no se entera — vería su
proyecto completo con las marcas puestas sobre material que no es. Las cámaras
renumeran desde cero en cada tarjeta.

---

## Lo que se cerró el 2026-08-10

Cuatro cosas que estaban en «lo que falta» y ya no lo están. Se quedan escritas
porque el **porqué** de cada una sigue aplicando.

### 1. Generar los proxies del bin — **hecho**

Clic derecho en el bin → «Crear proxies del bin…». Los genera del original
uno por uno, en segundo plano, y **cada uno se engancha apenas termina**: se
ve el material aligerarse conforme avanza en vez de esperar a que acabe todo.
La insignia del bin dice «creando proxies · 7/23», y desde el mismo menú se
cancela — lo hecho se queda, lo que faltaba no se hace, y volver a darle no
rehace nada.

**Las decisiones, que fueron de Bruno:** los proxies van a una carpeta
`Proxies` **al lado** de la del material, no adentro (adentro ensuciaría la
copia de la tarjeta, y al lado la app los reencuentra sola después, porque ya
busca en las carpetas hermanas). Terminan en `S03` como los de la Sony, así
que si alguien arrastra esa carpeta como material, el ingest los descarta.

**Comprobado con material real**, no solo con tests: 67 MB → 1.6 MB, mismos
120 cuadros, mismo fps, y 720x1280 — o sea que escala por el **lado corto** y
un clip vertical no sale al revés. Idéntico al proxy que escribe la cámara.

Pasan por la validación de siempre: el que no calce cuadro a cuadro no se
engancha, aunque lo hayamos generado nosotros.

Lo que se sabía de antes, con su evidencia en el handoff §4.b:

- El `.LRF` que escribe el DJI **no sirve como proxy** aunque se le cambie la
  extensión. Es un MP4 por dentro y se reproduce bien, pero **el contenido está
  corrido entre 1 y 5 cuadros, y el desfase cambia de clip a clip**. Para *ver*
  da igual; para marcar in/out, no. Y la validación que la app ya tiene los
  rechazaría de todos modos.
- Generándolo desde el original con el codificador del chip
  (`h264_videotoolbox`, lado corto 720): **285 MB → 17 MB, 1010 cuadros
  exactos**, ~10 s por cada 6 s de video.
- **La trampa:** los MP4 del dron traen una miniatura JPEG incrustada como
  segunda pista de video. Sin `-map 0:v:0`, ffmpeg transcodifica *esa* y sale
  un proxy de 406 px de ancho.

**Lo único que quedó sin probar contra el material de verdad:** una tanda
completa de las 23 tomas del dron, de punta a punta. Se midió un clip y se
probó la mecánica entera con ffmpeg sustituido; falta la corrida larga con el
disco del dron conectado.

### 2. LUT hacia Premiere — **parado por decisión de Bruno**

Ya no está abierto: **se probó dentro de Premiere y no se puede como se
quería.** Bruno decidió parar ahí («mejor solo no lo hagamos, no necesito
complicar más esto»).

Lo que se aprendió, con el detalle completo en
`archive/RESULTADO-2026-08-10-lut-y-estrella-en-premiere.md`:

- **Sí se le pueden colgar efectos al master clip sin armar secuencia**, y
  eso sirve más allá del LUT. `matchName` de Lumetri: `AE.ADBE Lumetri`.
- **«Input LUT» existe** (parámetro 6 de 130) pero **no acepta rutas**: su
  valor es `{ value: 0 }`, un número. Es un menú desplegable, y el número es
  el renglón elegido dentro de los LUTs que Premiere ya tiene instalados.
- La vía que quedaría —instalar el `.cube` donde Premiere lo vea y poner el
  índice— es frágil por diseño: el índice depende de qué haya instalado y en
  qué orden, así que en otra computadora apunta a otro LUT **sin avisar**.
  Mismo modo de fallo que enganchar el proxy equivocado.

Si algún día se retoma, lo que falta no es código sino contestar cómo se
verifica que el renglón N sigue siendo el LUT correcto.

### 3. La etiqueta dorada de la estrella — **hecha**

Comprobado en vivo: `MANGO` existe y es el índice 7, y el clip cambió de
etiqueta al aplicarlo. La guarda por si otra versión no lo trae se queda.

De paso salió algo que nadie sabía: **la copia del plugin que Bruno tenía
instalada era de agosto y no traía el soporte de la estrella**, así que hasta
ese día sus clips destacados llegaban a Premiere sin etiqueta. Ya está la
versión al día, idéntica al repo.

### 4. Los `.LRF` como clips — **hecho**

Ya no entran. Se comprobó primero que sí pasaba —una carpeta con `DJI_0001.MP4`
y `DJI_0001.LRF` traía los dos— y Bruno decidió: «no me sirve el LRF si
usaremos otros proxies». Tampoco se queda como candidato a proxy: ya se había
medido que no calza cuadro a cuadro.

---

## Lo que se cerró el 2026-08-20 (tercera tanda)

### El orden de los cuartos — **hecho**

Bruno explicó cómo trabaja: «para mí son dos fases: primero clasifico por
cuarto y luego clasifico picks y no picks», y para la segunda quiere «empezar
con el primer cuarto que quiera».

**La hoja acomodaba los cuartos por abecedario y el rail en el orden que él
eligió.** Las dos listas se contradecían, y la de la hoja no se podía cambiar
de ninguna manera: subir un cuarto en el rail no movía un pixel allá. Encima
el número de la tecla sale del rail, así que su cuarto `1` podía aparecer
hasta abajo. Reproducido antes de tocar código.

Ahora hay **un solo orden** en toda la app, y los cuartos **se arrastran** en
el rail para cambiarlo.

**Lo que esto enseña, otra vez:** reordenar cuartos SÍ existía —`⌥↑`/`⌥↓` y
el menú— pero no servía de nada porque la hoja lo ignoraba. Dos listas del
mismo dato que no se hablan valen menos que una sola.

**Y una decisión reabierta con razón nueva.** El 2026-08-08 se descartó
arrastrar en el rail: «acciones de una vez por shooting, no merecen atajos
nuevos ni el riesgo del drag-and-drop». El supuesto era falso — reordenar es
cómo Bruno decide por dónde empieza la fase 2, cada shooting, y con 13
cuartos subir el último son doce repeticiones. Lo que se descartó por
marginal estaba en el camino. **Subir y Bajar se quedaron**, porque dicen
explícitamente que reordenar ES cambiar la tecla, y eso arrastrando no se
lee.

Detalle en `specs/2026-08-20-orden-de-los-cuartos-design.md`.

---

## Lo que se cerró el 2026-08-20 (segunda tanda)

### Los cuartos más allá del nueve — **hecho**

Salió de usar la app con 13 cuartos. Dos cosas, las dos reproducidas antes de
tocar código.

**`S` daba un cuarto viejo.** Copiaba el del clip de al lado hacia atrás, no
el último que usaste. Coincide mientras avanzas en orden y se separa en
cuanto te saltas clips o hay material de una pasada anterior. Bruno: «a veces
`S` es el cuarto penúltimo en lugar del último». Ahora la app se acuerda del
último que asignaste, venga de donde venga. Deshacer no lo mueve —`⌘Z`
revierte el dato, no tu intención— y renombrar lo sigue.

**A los cuartos del 10 en adelante no se llegaba.** El buscador que abre `⏎`
**ya existía y funcionaba** —busca sin acentos, prefiere elegir sobre crear—
pero mostraba 6 de 13, no estaba documentado en ningún lado, y con una fila
del rail enfocada `⏎` renombraba en vez de asignar. Bruno lo vivió como «no
me deja seleccionar cuartos, solo hacer nuevos». Ahora el buscador los
muestra todos con scroll, `⏎` en el rail asigna (renombrar se fue a `F2` y al
doble clic), y el hueco vacío del décimo cuarto dice `⏎`.

**Lo que esto enseña, y por eso queda escrito:** la herramienta existía desde
el rediseño. Lo que faltaba no era código, era que se viera. Un control que
funciona y no se encuentra vale lo mismo que uno que no existe.

Detalle en `specs/2026-08-20-cuartos-mas-alla-del-nueve-design.md`.

---

## Lo que se cerró el 2026-08-20

### La fila de proxies — **hecho**

Salió de usar la app: con dos tarjetas hay dos bins que necesitan proxies, y
pedir el segundo contestaba «espera a que termine». Lo caro no era esperar,
era **tener que acordarse de volver**.

Ahora se forman: pides los que quieras, corren en orden, cada uno se cancela
por su lado desde su menú, y al vaciarse la fila sale **un** cartel con la
suma de todo en vez de uno por bin. Sigue generando de uno en uno, que es
deliberado.

**Dos cosas que parecían faltar y ya estaban**, escritas aquí para que nadie
las «arregle» otra vez:

- **Reanudar tras cancelar ya funcionaba.** `faltantes()` se salta lo hecho.
  Comprobado con la app antes de escribir el spec: con tres clips y uno
  hecho, ofrece «se van a crear 2 proxies».
- **Un proxy interrumpido nunca bloqueó a su clip.** `proxy_gen.generar`
  escribe a `<nombre>.mp4.parcial` y solo renombra al nombre bueno cuando
  ffmpeg devuelve 0, así que un corte deja un `.parcial` que
  `ruta_de_proxy(...).exists()` no ve — el clip sigue contando como
  pendiente. Lo único real era que esos `.parcial` no los barría nadie, y
  ahora se barren al empezar cada tanda.

Detalle en `specs/2026-08-20-cola-de-proxies-design.md`.

---

## Lo que se cerró el 2026-08-18

### Los bins en el deshacer — **hecho**

Estaba en «lo que falta» descrito como una función pendiente: «los bins no
pasan por el historial que ya existe». Al probarlo con la app corriendo
resultó ser otra cosa, y peor: **`⌘Z` prometía deshacer lo último y deshacía
otra cosa.** Arrastrabas un clip a otro bin, apretabas `⌘Z`, y el clip se
quedaba donde lo soltaste mientras otro clip perdía el cuarto que le habías
puesto. Dos cosas mal, ninguna avisaba.

Pegaba justo donde el diseño quiso ser cuidadoso: se decidió a propósito que
arrastrar cambie el bin y nunca el cuarto, para que un gesto mal soltado no
reclasifique — pero deshacer ese gesto sí reclasificaba, al revés.

Ahora mover clips, crear un bin y renombrarlo entran al historial con su
renglón y su `↺`. Un renglón que ya no se puede cumplir —el bin creado ya
tiene clips, o el bin al que había que regresar los clips ya no está— **se
apaga y dice por qué** en vez de hacer otra cosa, y `⌘Z` no se salta al
siguiente ni se lo traga.

**Quitar un bin se quedó fuera a propósito**, y no por falta de tiempo: esa
acción saca clips del proyecto, y eso corre los números de todos los demás
mientras cada entrada del historial habla por número de clip. Ya está
resuelto de otra forma —vacía el historial entero— y así se queda.

Detalle en `specs/2026-08-18-bins-en-el-deshacer-design.md`.

---

## Lo que falta

### 1. Correr un shooting completo con la app — **lo primero**

No es una función nueva y por eso es fácil que se cuele hacia abajo en la
lista. Pero desde los bins en adelante nada ha pasado por los 132 clips de
Bruno, y en este proyecto el uso real ha encontrado más bugs que cualquier
revisión. Cualquier función que se construya antes de esto se construye sobre
algo sin comprobar.

### 2. Probar el paquete en otra Mac — **bloqueado por hardware, no por código**

El `.app` de 175 MB se arma y arranca sin Homebrew; ninguno de sus 214 binarios
apunta a Homebrew. Va con firma propia, que es gratis y suficiente: **por USB o
carpeta compartida abre directo**; mandada por internet, la primera vez hay que
autorizarla en *Privacidad y seguridad*.

Eso es cómo funciona macOS según la documentación de Apple, **no comprobado**.
La única prueba válida es abrirla en otra computadora. Va junto con probar ahí
un `.cvproj` de verdad, que tampoco se ha hecho.

**El plugin ya se puede repartir** (resuelto el 2026-08-12):
`./uxp-plugin/empaquetar.sh` deja un `.ccx` y quien lo recibe le da doble
clic. El «bloqueo» del 2026-08-10 —«el CLI no compila para Node 24,
`abi=137`»— **era un diagnóstico equivocado**: el módulo que trae Adobe es
N-API y sirve con cualquier Node; lo único que pasaba es que su instalador se
salta el paso que lo extrae. Vale la pena recordarlo: un mensaje de error que
nombra una versión invita a creer que el problema es la versión.

### 3. Crear muchos cuartos de un jalón — **tiene spec, falta plan**

`specs/2026-08-09-cuartos-rapidos-design.md`: un campo que acepta varios
separados por coma o salto, autocompletar con los nombres ya usados, y
plantillas guardadas. Aprobado por Bruno, sin plan ni implementación. Nace de
que él graba inmuebles y los cuartos se repiten casa tras casa.

### 4. Filtrar por duración

El buscador de la hoja ya filtra por nombre, cuarto, estado y bin; lo único
que no cubre de lo que se ofreció es la duración. Salió de corregir una lista
mal presentada (ver abajo).

### 5. Escala y velocidad — **medido el 2026-08-10, con su material**

La interfaz no es el problema: con 132 clips, cargar el proyecto toma 0.15 s,
reconstruir la hoja 0.07 s, pintar un cuarto a los 132 seleccionados 0.002 s y
avanzar de clip 3.6 ms. Nada de eso se siente.

**Todo el tiempo está en la primera importación**, y ahí lo que manda es de
dónde salen las portadas:

| | 132 clips |
|---|---|
| portadas desde el original | **7.7 min** |
| portadas desde el proxy | **0.6 min** |

Trece veces, no cinco: la cifra de «cinco veces» venía de medir un clip
aislado, y con la app corriendo de verdad la diferencia es mayor. Por eso la
app ofrece los proxies al importar.

**Lo que se probó y NO sirve:** sacar más portadas a la vez. Con 3, 6 o 9 en
paralelo el tiempo es el mismo (~21 s por cada 6 clips) — mpv decodificando
por software ya satura la máquina. Queda medido para no volver a intentarlo.

**Lo que sí sirvió:** `ffprobe` al importar, que corría en serie y en el hilo
de la interfaz. Ahora va de a ocho: **111 clips reales pasaron de 2.8 s a
0.42 s** de ventana congelada.

Sin medición por encima de los 132 clips.

---

## Ideas nuevas que se ofrecieron el 2026-08-10

Se le presentó a Bruno una lista de lo que le podría faltar a la app. Lo que
dijo, para no volver a preguntárselo:

- **Buscar y filtrar** (por nombre, cuarto, duración, cámara) — **le gustó.**
  Con 132 clips todavía se ve todo; con 500 no.
- **Deshacer** — **le gustó**, pero se le presentó mal y él lo cachó
  («¿deshacer no existe?»). **Sí existe**: `⌘Z` más el historial del rail,
  que revierte cualquier fila con un click, con las últimas 50 acciones de
  la sesión. Cubre asignar cuarto (incluido el pincel), borrar un cuarto,
  in/out y los estados.

  **Lo que NO cubre son los bins** —crear, borrar, renombrar y arrastrar
  clips entre bins— porque quedaron fuera cuando se construyeron. O sea que
  la tarea real no es «hacer deshacer», es **meter los bins al historial que
  ya existe**, que es bastante más chico. `bins.py::mover` ya está escrito
  para no tocar el historial, así que hay que decidir a propósito qué
  guarda cada acción de bin.
- **Varios in/out en un mismo clip (subclips)** — se le explicaron las dos
  formas (varios rangos dentro del clip, o partirlo en tarjetas nuevas) y
  **dijo que ya no le llama tanto la atención**. No reproponerlo.
- Sin respuesta todavía, ofrecidas en la misma lista: exportar un reporte del
  shooting, notas por clip, copiar solo los picks a otra carpeta, respaldar
  la tarjeta al importar, ordenar la hoja por hora de grabación, detectar
  tomas repetidas.

## Controles que mentían

Van juntos a propósito: **tres de los bugs más caros del proyecto no fueron
fallas, fueron cosas que decían hacer algo y no lo hacían.** No los encuentra
la suite —hacen exactamente lo que su código dice— y solo salen usando la app.

- **El selector de calidad** («Full 1/2 1/4 1/8»). Le pedía a mpv una
  propiedad inexistente. Bruno: «¿sí hace diferencia? porque yo no lo veo».
  Quitado el 2026-08-10, no arreglado: el truco de Premiere necesita un codec
  que se lea por capas y el suyo no lo es.
- **El botón «Cuartos»** de la barra, que solo movía el foco. «No hace nada.»
- **«Sony FX30»** escrito a mano en el subtítulo, que lo decía igual con
  material del dron y con el proyecto vacío.

Si aparece un cuarto, vale la pena revisar los demás controles de un jalón.

## Qué NO es una meta (para no asumir de más)

- **Ninguna función de edición.** La app clasifica y prepara; Premiere edita.
- **No reemplazar el panel de proyecto de Premiere.** Los bins son para saber
  de qué cámara viene cada clip y actuar por cámara — no para reconstruir una
  jerarquía con carpetas anidadas.
- **Ningún paso de configuración antes de trabajar.** Los cuartos se crean
  sobre la marcha.
- **Nada en la nube, ni dos personas en el mismo proyecto a la vez.**
- **El proyecto apunta al material, no lo copia ni lo mueve.**
- **Arrastrar cambia el bin, nunca el cuarto.**

## Ideas que se ofrecieron y no se tomaron

Se anotan para no volver a proponerlas como si fueran nuevas:

- **Una sola carpeta raíz por proyecto** para reencontrar la media, en vez de
  una por bin. Descartada: la Sony y el dron pueden vivir en discos distintos.
- **Traer los cuartos de la última sesión** con un botón. Bruno prefirió
  plantillas guardadas, que cubren lo mismo y duran.
- **Que la app adivine la cámara** por el nombre de los archivos. «Cuando
  acierta es mágico; cuando falla es confuso.»
- **Que el cuarto se pudiera asignar arrastrando.** Se dejó fuera a propósito:
  con los dos ejes en el mismo gesto, un arrastre mal soltado cambia el dato
  que más trabajo cuesta.
- **Forma de onda de audio, recorte automático de in/out, comparar varios clips
  en paralelo, sistema de cinco estrellas** — evaluadas y descartadas durante
  el rediseño, ver `mockups/rediseno-2026-08-08/DECISIONES.md`.
