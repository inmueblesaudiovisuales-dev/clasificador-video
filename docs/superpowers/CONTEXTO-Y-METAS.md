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

### 1. Generar los proxies del dron — **listo para escribirse**

Es lo más maduro de la lista: **ya está medido, decidido y aprobado por Bruno**
(«haz la función de crear proxies»). Solo falta escribirlo.

Lo que ya se sabe, con su evidencia en el handoff §4.b:

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

**Lo que hay que decidir antes de escribirlo** —esto sí es brainstorm con
Bruno, no se asume—: dónde se guardan los proxies generados, si el gesto vive
en el menú del bin, qué se ve mientras corre (son minutos con 23 clips) y si se
puede cancelar. El resto ya está resuelto: enganchado, validación y
reproducción son maquinaria que ya existe.

### 2. LUT hacia Premiere — **falta un spike, no código**

Bruno lo pidió junto con los bins: «también meter los LUTs a esos videos». Un
LUT de S-Log de la FX30 no va sobre material del dron, así que va **por bin**,
igual que los proxies.

- **Alcanzable:** la API de UXP permite ponerle un efecto al *master clip*
  (`ClipProjectItem.getComponentChain`), o sea sin armar la secuencia.
- **Lo que bloquea:** falta comprobar **dentro de Premiere** que el parámetro
  de LUT de entrada de Lumetri acepta una ruta de archivo. Es un spike corto
  con Premiere abierto, y hasta que se haga todo lo demás es suposición.
- El bin ya existe para colgárselo y el manifest ya viaja por clip, así que la
  pieza que falta del lado de la app es chica.

### 3. Probar el paquete en otra Mac — **bloqueado por hardware, no por código**

El `.app` de 175 MB se arma y arranca sin Homebrew; ninguno de sus 214 binarios
apunta a Homebrew. Va con firma propia, que es gratis y suficiente: **por USB o
carpeta compartida abre directo**; mandada por internet, la primera vez hay que
autorizarla en *Privacidad y seguridad*.

Eso es cómo funciona macOS según la documentación de Apple, **no comprobado**.
La única prueba válida es abrirla en otra computadora. Va junto con probar ahí
un `.cvproj` de verdad, que tampoco se ha hecho.

### 4. La etiqueta dorada de la estrella — **una corrida dentro de Premiere**

`destacado → MANGO` está escrito, con guarda que avisa si esa versión de
Premiere no conoce el color. Falta correr `autocheck-tests.js` dentro de
Premiere para confirmar el nombre de la constante. Ojo: ese archivo apuntaba a
una carpeta que ya no existe; se arregló, pero una de sus pruebas necesita que
se cree a mano una carpeta que el repo no trae.

### 5. Los `.LRF` como clips — **decisión de Bruno**

DJI escribe un `.LRF` junto a cada `.MP4`, y el ingest los toma como material:
cada toma del dron aparece **dos veces**. Los proxies de la Sony ya se excluyen
por su sufijo `S03`. ¿Se hace lo mismo con los `.LRF`? Es una línea de código y
una decisión suya.

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
