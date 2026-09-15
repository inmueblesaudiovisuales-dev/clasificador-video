# Clipify

App de escritorio para macOS que hace el paso previo a editar: **ver todo el
material de un shooting, decidir qué sirve y dejarlo ordenado**, y después
mandárselo a Adobe Premiere ya armado.

Está hecha para trabajar rápido con el teclado, con el material tal como sale
de la cámara: **HEVC 10-bit de una Sony FX30**, mayoría vertical, más tomas de
un **dron DJI**. De ahí salen casi todas sus decisiones — por qué importan
tanto los proxies, por qué el material se agrupa por cámara y por qué el
`in`/`out` no se negocia.

---

## Qué hace

**Agrupa por cámara.** El material entra en **bins** —uno por tarjeta— con su
nombre, su carpeta y su conteo. También puedes crear bins vacíos y arrastrar
clips de uno a otro.

**Clasificas sin soltar el teclado.** A cada clip le pones un **cuarto**
(sala, cocina, recámara…), lo marcas **pick / reject / destacado** y, si
quieres, le pones **in/out**. Los cuartos se crean sobre la marcha: no hay
paso de configuración antes de empezar.

**Hoja de contactos.** `⇥` muestra todo junto, agrupado, con búsqueda y
filtros. Ahí se pinta por lotes, se arrastra entre bins y se escrubea cada
miniatura pasando el mouse por encima.

**Proxies.** Los engancha si la cámara ya los trae, o **te los genera** si no
—el caso del dron—. Con proxy, navegar el material es instantáneo.

**Deshacer de verdad.** `⌘Z` y un historial lateral donde puedes revertir
cualquier paso, no solo el último.

**El proyecto es un archivo.** Un `.cvproj` que puedes mover, respaldar y
abrir en otra computadora, reencontrando el material donde esté.

**Exporta a Premiere.** Un plugin arma el proyecto solo: bins por cuarto,
etiquetas de color, `in`/`out` y proxies enganchados.

---

## Instalar

**La app:** abre el `.dmg` y arrastra *Clipify* a Aplicaciones. No
necesita nada más instalado — `ffmpeg`, `ffprobe` y `mpv` viajan adentro.

Si el `.dmg` llegó por internet, la primera vez macOS lo bloquea por venir de
fuera: se destraba en *Configuración → Privacidad y seguridad → Abrir de
todos modos*. Pasa una sola vez.

**El plugin de Premiere** (va aparte): cierra Premiere, doble clic al archivo
`.ccx` y Creative Cloud lo instala solo. Al abrir Premiere aparece en
`Ventana > Plugins UXP > Clipify`.

La app **abre maximizada** y ocupando tu pantalla. Al abrir un proyecto verás
una ventanita con su nombre y una barra mientras se preparan las portadas —
con 205 clips son un par de segundos.

**Qué versión tienes:** la app lo dice abajo a la derecha de la pantalla de
inicio — «Clipify 1.12». Es lo primero que hay que saber para reportar
cualquier cosa.

Qué trae cada versión: [docs/VERSIONES.md](docs/VERSIONES.md).

Para armar los dos, ver [docs/DESARROLLO.md](docs/DESARROLLO.md).

---

## Cómo se usa

### 1. Empezar

La app abre con tus últimos proyectos. **Proyecto nuevo** te pregunta dónde
guardarlo y lo crea ahí mismo: nunca hay trabajo sin un archivo donde vivir.
De ahí en adelante se guarda solo mientras trabajas.

### 2. Importar

Arrastra la carpeta de la tarjeta a la hoja, o suéltala sobre un bin para que
entre ahí. Cada carpeta se vuelve un bin.

Si el bin no tiene proxies, la app pregunta qué hacer:

- **Enlazar los que ya tengo…** — la Sony ya los graba.
- **Crear los proxies** — el caso del dron.
- **Ahora no.**

**Conviene resolverlo ahí**: mientras no haya proxies, las portadas de la hoja
salen del original y cuestan **trece veces más** (7.7 min contra 0.6 con 132
clips).

### 3. Clasificar

| Tecla | Qué hace |
|---|---|
| `1`…`9` | asigna el cuarto de esa posición en el rail **y avanza** |
| `S` | repite **el último cuarto que usaste** y avanza |
| `P` · `X` · `⇧P` | pick · reject · destacado |
| `↑` `↓` | sube o baja un escalón de estado |
| `I` `O` · `U` | marca in / out · los quita |
| `←` `→` | clip anterior / siguiente **dentro de lo que estás viendo** |
| `Espacio` | reproduce o pausa |
| `K` `L` | pausa / adelante (1× → 2× → 4×), como en Premiere |
| `,` `.` | un cuadro atrás / adelante |
| `R` | vuelve al inicio del clip |
| `F` | pantalla completa (esconde todo menos el video) |
| `⇥` | cambia entre clip y hoja de contactos |
| `+` `-` | miniaturas más grandes o más chicas |
| `⏎` | busca un cuarto por nombre y lo asigna — la vía para los que pasan del noveno |
| `F2` | renombra el cuarto seleccionado en el rail |
| `⌘Z` | deshacer |
| `⌘A` | selecciona el grupo donde estás |
| `⌘E` | exportar a Premiere |
| `esc` | sale una capa (video → clip → hoja) |

Asignar un cuarto **avanza solo al siguiente clip**: la idea es recorrer el
shooting sin tocar las flechas, tecleando un número por clip. Marcar
pick/reject o poner in/out **no** avanza — esos se hacen sobre el clip que
estás mirando.

**El orden de los cuartos lo decides tú**, y es el mismo en la lista de la
izquierda y en la hoja de contactos. Arrastra un cuarto para moverlo, o usa
clic derecho → Subir / Bajar (`⌥↑` / `⌥↓` con el teclado). Mover un cuarto
**cambia su número**: el que quede arriba es el `1`. Sirve para empezar por
el cuarto que quieras cuando andas repasando picks.

**Más de nueve cuartos.** Los atajos `1`…`9` llegan al noveno. Del décimo en
adelante el rail muestra `⏎` en lugar del número: aprieta Enter, escribe las
primeras letras —sin preocuparte por acentos ni mayúsculas— y dale Enter otra
vez. También puedes elegir el cuarto en la lista de la izquierda y apretar
Enter.

Los filtros no cambian solo lo que ves: **cambian por dónde te llevan las
flechas**. Con «solo picks» puesto, `→` salta al siguiente pick.

**Las flechas siguen el orden que estás viendo.** Con «Por cuarto» puesto,
`→` termina un cuarto antes de pasar al siguiente — que es lo que quieres
cuando andas repasando picks cuarto por cuarto. Asignar un cuarto con `1`…`9`
sí avanza en orden de grabación: ahí lo que quieres es el siguiente que
grabaste, no el siguiente de la lista.

**La app no suena.** Los clips se reproducen callados siempre, sin tecla que
lo cambie: aquí se clasifica mirando, y un shooting entero sonando mientras
recorres toma por toma es ruido y nada más. Si necesitas oír una toma, ábrela
en QuickTime.

**Material horizontal.** Un clip vertical usa toda la altura de la ventana;
uno horizontal no alcanza, porque el ancho se lo reparten el rail y la hoja.
El botón **Ancho** de la barra de arriba esconde la hoja mientras ves clip
por clip y le da su espacio al video —el rail y el estado del clip se
quedan—. Se queda hundido mientras está puesto, y solo se deja apretar en
modo clip: en la hoja no hay video al que darle espacio. En una ventana de
1600×900 la imagen pasa de 939×528 a 1344×756. Con `F` va todavía más
grande, pero ahí se esconde todo. Se guarda con el proyecto.

### 4. En la hoja

Pasa el mouse por una miniatura para escrubearla. Arrastra para seleccionar
varias, o `⇧`+clic para un rango. Con varias seleccionadas, una tecla de
cuarto las pinta todas de un jalón.

Arrastra clips de un bin a otro. **Arrastrar cambia el bin y nada más** — el
cuarto sigue siendo cosa del teclado, para que un gesto mal soltado no
reclasifique.

Mover clips de bin, crear un bin y renombrarlo **se deshacen con `⌘Z`** y
aparecen en la lista del rail como cualquier otra acción. Un renglón que ya
no se puede cumplir —creaste un bin y ya le metiste clips— se ve apagado y
dice por qué, en vez de deshacer otra cosa.

El renglón **AGRUPAR** decide si los clips se juntan por cuarto o se quedan
como salieron de la cámara:

- **Por cuarto** — al asignarle un cuarto a un clip, su tarjeta se va con las
  de ese cuarto. Es lo bueno cuando estás acomodando el shooting entero.
- **Orden de rodaje** — nada se mueve nunca. El cuarto se le pone igual y se
  ve en la tarjeta, pero como etiqueta: recorres el material en el orden en
  que lo grabaste sin perder por dónde ibas.

Los bins no se tocan en ninguno de los dos, y las flechas recorren lo mismo.
Se guarda con el proyecto.

Clic derecho en el encabezado de un bin: renombrar, enlazar o crear proxies,
seleccionar sus clips, quitarlo del proyecto.

### 5. Exportar

`⌘E` guarda un archivo con **el nombre de tu proyecto** —
`IAV-2608.17.json`—. En Premiere, abre el panel del plugin y dale
a **Importar clasificación…**: arma los bins por cuarto, pone las etiquetas de
color, aplica los in/out y engancha los proxies.

El proyecto se arma con estas siete carpetas, y todo tu material va dentro de
la segunda:

```
01. Secuencia
02. Clip          ← aquí entra todo lo que clasificaste
03. AE composition
04. Musica
05. Voz
06. Graficos
07. Assets adicionales
```

Las cinco que quedan vacías se crean igual: están para que tú metas cosas
ahí. Si ya las tenías en tu proyecto, se reusan — no te llega una segunda.

Dentro de `02. Clip` hay una carpeta por cuarto, y ahí van todos sus clips
juntos. Cada uno dice lo que es con una marca al inicio del nombre:

```
02. Clip
  └── Cocina
        ├── ★ C0002.MP4      destacado
        ├── ✓ C0001.MP4      pick
        ├── ✕ C0004.MP4      reject
        └── C0007.MP4        sin marca: no lo has visto
```

No hay carpetas por estado. Abres el cuarto y ves todo lo que grabaste ahí,
con lo bueno y lo malo señalado — en vez de tener que entrar a tres carpetas
para saber qué tienes.

Las marcas solo cambian el nombre dentro de Premiere; **el archivo en tu
disco no se toca**. Y si cambias de opinión y vuelves a importar, la marca se
corrige sola: un clip que era reject y ahora es destacado pierde su ✕ y gana
su ★. Si tú le pusiste otro nombre a un clip, ese no se toca.

Los clips a los que nunca les pusiste cuarto siguen cayendo juntos en
**Sin clasificar**.

### El color dice de qué cámara es

Cada clip llega a Premiere con la etiqueta de color de su cámara:

| Cámara | Color |
|---|---|
| Sony | azul |
| DJI (dron) | amarillo |
| Otra | morado |

La cámara la adivina Clipify del nombre de los archivos —los del dron traen
`DJI`— y la ves en el puntito de color del encabezado de cada bin, que es el
mismo que vas a ver en Premiere. Si le atinó mal, clic derecho en el
encabezado → **Cámara**.

Con esto, ponerle su LUT a todo el material de una cámara es seleccionar
todos los de un color y arrastrarles el preset.

### 6. La guía de edición

Cuando ya terminaste de clasificar, el botón **Guía de edición** —junto al de
exportar— te arma el recorrido del video: un párrafo de cómo recorrerla y la
lista de tus cuartos en el orden que conviene, cada uno con una línea corta de
por qué va ahí.

Te pregunta dos cosas. La de arriba es la que importa: **qué quieres lucir**,
y ahí escribes lo que se te ocurra —«la alberca y la terraza», «la cocina
quedó chica, no la luzcas»—. Abajo, de un toque, **qué tipo de propiedad es**.
Las dos te las puedes saltar.

Cuando ves la guía, **Usar este orden** acomoda tus cuartos en ese orden —en
el rail, en la hoja y en Premiere, que es uno solo— y la guarda. Si no te
convence, cambias lo que quieres lucir y la vuelves a pedir.

De ahí en adelante **la guía viaja sola**: sale en el archivo que exportas y
la ves en Premiere, en la pestaña **Guía de edición** del panel. Y tus
carpetas de cuartos llegan numeradas en ese orden: `01. Fachada`,
`02. Cocina`. Si importas más clips del mismo rodaje y el orden cambió, se le
cambia el número a la carpeta que ya tienes — no se crea una segunda.

Cuatro cosas que vale la pena que sepas:

- **Es una guía para leer. No mueve tus clips.** Lo único que acomoda son tus
  cuartos, y solo si le das a «Usar este orden».
- **Si le falta un cuarto o se inventa uno, te lo dice** arriba de la lista.
  Una guía a la que le falta la cocina hace que se te olvide la cocina al
  editar, y eso no se nota hasta después de entregar.
- **No vio tu material**, así que no sabe qué hay adentro de tus cuartos —solo
  por qué uno va antes que otro en un recorrido—. Si algún día te describe una
  cocina que nunca vio, eso es un error y vale la pena decirlo.
- **Si armaste la guía y después agregaste un cuarto**, al exportar te avisa
  —«tu guía es de antes de agregar la Terraza»— y tú decides si la exportas
  así o la vuelves a armar.

La primera vez hace falta una llave de DeepSeek: se pega una vez y se queda
guardada en tu computadora, en `~/.clasificador_video/`. No va en el proyecto
de Premiere ni viaja con el material. De tu computadora solo salen los nombres
de tus cuartos y lo que tú escribas — nada de video, archivos ni rutas.

Si se cae el internet o falla, te lo dice y **no te bloquea nada**: exportar
sigue funcionando, nada más sin guía. Y si abres la pestaña en Premiere con un
proyecto que no trae una, te lo dice con esas palabras.

---

## Proxies, en detalle

Un proxy es una copia ligera que se usa **solo para navegar**: el `in`/`out`
que marcas encima vale para el original. Por eso hay una regla que no se
negocia: **un proxy que no calce cuadro a cuadro con su original no se
engancha**, venga de donde venga. Con uno corrido, el `in` caería en el cuadro
equivocado y nadie se enteraría.

**Enlazar los que ya existen.** Eliges **un** proxy cualquiera del bin y la
app engancha los demás sola: de ese par saca el patrón de nombre —`C0001.MP4`
+ `C0001S03.MP4` da el sufijo `S03`— y busca los otros en esa carpeta. No
tiene que ser el del clip que estás viendo.

**Crear los que no existen.** Los saca del original con el codificador del
chip, uno por uno y en segundo plano: puedes seguir clasificando mientras
corre. El encabezado del bin va diciendo `creando proxies · 7/23` y **cada
clip se engancha apenas termina el suyo**. Desde el mismo menú se cancela: lo
hecho se queda, lo que faltaba no se hace, y volver a darle solo genera los
que faltan. Si en la carpeta ya hay un proxy que quedó sin enganchar —porque
una tanda anterior se cortó a medias— **la app lo engancha en vez de
rehacerlo**, después de comprobar que calza.

**Puedes pedir varios bins seguidos.** El primero arranca y los demás se
forman: cada uno dice `en cola` en su insignia y arranca solo cuando le toca.
Al terminar todos sale **un** aviso con la cuenta de todo. Cancelar desde el
menú de un bin cancela solo ese —si era el que corría, el siguiente arranca
solo— y los demás siguen formados.

**Tú eliges dónde van.** La primera vez que creas proxies en un proyecto, la
app te pregunta — y llega ya contestada, con la carpeta que encontró junto a
tu material y la ruta a la vista. Un clic y listo. Se cambia después desde el
menú del bin.

Adentro de esa carpeta se hace **una subcarpeta por cada carpeta de
material**, con su mismo nombre. Así, si dos cámaras nombran igual un archivo,
no se pisan. Si la carpeta que elegiste no se deja escribir —un disco que hoy
no está conectado— caen adentro de la del material, y si tampoco, al lado.

**Los proxies de proyectos anteriores siguen sirviendo.** Han vivido en tres
sitios distintos a lo largo de agosto de 2026 y la app mira los tres, así que
un proyecto viejo abre igual y no se regenera ni se mueve nada.

**Lo que ganas**, medido con material real: abrir un clip pasa de 201 ms a
3 ms, saltar de 293 ms a 12 ms, y las portadas de la hoja de 7.7 min a 0.6 min
con 132 clips (medido en agosto de 2026 sobre el material de un shooting real).

Cada tarjeta lleva una marca **PROXY** abajo a la izquierda, y la barra de
estado el total: `proxies 720p · 118/128`, o `sin proxies` si no hay ninguno.

---

## Proyectos y material que se mueve

Cada proyecto es un archivo **`.cvproj`**. Uno que ya no está en su lugar
—disco desconectado, carpeta movida— **no desaparece de la lista**: se ve
apagado y dice que no se encuentra.

Al abrir, si falta material, la app **avisa por bin** y lo reencuentra
señalando una carpeta. Cada archivo se **confirma por peso y duración** antes
de engancharse, y lo que no se puede confirmar **no se engancha**: enganchar
el archivo equivocado es peor que no encontrarlo, porque no te enteras — y las
cámaras vuelven a numerar desde cero en cada tarjeta.

Si vienes de una versión anterior, lo que tenías clasificado se convierte solo
en un `.cvproj` dentro de `~/Documents`. Lo viejo no se borra: queda apartado
como `sesion.migrada.json`.

---

## Más

- **[docs/DESARROLLO.md](docs/DESARROLLO.md)** — correr desde el código,
  tests, armar el `.dmg` y el plugin, cómo está organizado el repo.
- **[docs/superpowers/CONTEXTO-Y-METAS.md](docs/superpowers/CONTEXTO-Y-METAS.md)**
  — estado del proyecto, qué falta, y qué se descartó con su razón.
