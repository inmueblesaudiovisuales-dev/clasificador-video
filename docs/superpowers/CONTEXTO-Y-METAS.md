# Contexto y metas del proyecto

*(Última actualización: 2026-08-10, después de cerrar los bins por cámara, los
bins arrastrables y los proyectos guardables. Este documento describe
**intención y dirección**, y lleva la cuenta de lo hecho y lo que falta — para
decisiones técnicas ya tomadas, ver `CLAUDE.md`; para qué es la app y cómo
correrla, ver `README.md`; para el detalle técnico de cada entrega y de cada
bug, ver el handoff.)*

## Estado actual

**La app clasifica un shooting completo sin tocar el mouse, agrupa el material
por cámara, y el proyecto es un archivo que se puede mover.** Llega
reproduciendo, se marca con el teclado, se cruza a la hoja de contactos, se
pinta por lotes y se exporta a Premiere, que arma el proyecto solo.

**1337 tests, 40 corridas seguidas sin un fallo.**

**Lo que sigue sin comprobarse, y atraviesa todo lo demás:** desde los bins en
adelante, **nada se ha usado con el material real de Bruno**. Se midió con
archivos inventados, `ffprobe` falso y los tres clips de `sample-media/`. Sus
132 clips no han pasado por aquí. Lo anterior a eso sí — y de ese uso real
salieron más bugs que de cualquier revisión.

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

## Lo que falta

### 1. Generar los proxies del dron — **hecho, 2026-08-10**

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

### 2. LUT hacia Premiere — **parado por decisión de Bruno, 2026-08-10**

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

### 3. Probar el paquete en otra Mac — **bloqueado por hardware, no por código**

El `.app` de 175 MB se arma y arranca sin Homebrew; ninguno de sus 214 binarios
apunta a Homebrew. Va con firma propia, que es gratis y suficiente: **por USB o
carpeta compartida abre directo**; mandada por internet, la primera vez hay que
autorizarla en *Privacidad y seguridad*.

Eso es cómo funciona macOS según la documentación de Apple, **no comprobado**.
La única prueba válida es abrirla en otra computadora. Va junto con probar ahí
un `.cvproj` de verdad, que tampoco se ha hecho.

**Y hay un bloqueo nuevo, del lado del plugin:** el CLI de UXP que arma el
`.ccx` ya no instala — su biblioteca nativa no trae compilado para Node 24
(`abi=137`). Mientras eso no se resuelva, el plugin se puede actualizar en la
máquina de Bruno copiando archivos sobre la instalación existente, pero **no
se puede repartir a otra computadora**.

### 4. La etiqueta dorada de la estrella — **hecho, 2026-08-10**

Comprobado en vivo: `MANGO` existe y es el índice 7, y el clip cambió de
etiqueta al aplicarlo. La guarda por si otra versión no lo trae se queda.

De paso salió algo que nadie sabía: **la copia del plugin que Bruno tenía
instalada era de agosto y no traía el soporte de la estrella**, así que hasta
hoy sus clips destacados llegaban a Premiere sin etiqueta. Ya está la versión
al día, idéntica al repo.

### 5. Los `.LRF` como clips — **hecho, 2026-08-10**

Ya no entran. Se comprobó primero que sí pasaba —una carpeta con `DJI_0001.MP4`
y `DJI_0001.LRF` traía los dos— y Bruno decidió: «no me sirve el LRF si
usaremos otros proxies». Tampoco se queda como candidato a proxy: ya se había
medido que no calza cuadro a cuadro.

### 6. Crear muchos cuartos de un jalón — **tiene spec, falta plan**

`specs/2026-08-09-cuartos-rapidos-design.md`: un campo que acepta varios
separados por coma o salto, autocompletar con los nombres ya usados, y
plantillas guardadas. Aprobado por Bruno, sin plan ni implementación. Nace de
que él graba inmuebles y los cuartos se repiten casa tras casa.

### 7. Escala

Medido y cómodo con 128 clips. Lo que se degrada primero al crecer es la
generación de portadas — ahora que salen del proxy, cinco veces más barata. Sin
medición por encima de eso.

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
