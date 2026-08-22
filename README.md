# Clasificador de Video

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

**La app:** abre el `.dmg` y arrastra *Clasificador* a Aplicaciones. No
necesita nada más instalado — `ffmpeg`, `ffprobe` y `mpv` viajan adentro.

Si el `.dmg` llegó por internet, la primera vez macOS lo bloquea por venir de
fuera: se destraba en *Configuración → Privacidad y seguridad → Abrir de
todos modos*. Pasa una sola vez.

**El plugin de Premiere** (va aparte): cierra Premiere, doble clic al archivo
`.ccx` y Creative Cloud lo instala solo. Al abrir Premiere aparece en
`Ventana > Plugins UXP > Clasificador de Video`.

**Qué versión tienes:** la app lo dice abajo a la derecha de la pantalla de
inicio — «Clasificador 1.6». Es lo primero que hay que saber para reportar
cualquier cosa.

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

**Más de nueve cuartos.** Los atajos `1`…`9` llegan al noveno. Del décimo en
adelante el rail muestra `⏎` en lugar del número: aprieta Enter, escribe las
primeras letras —sin preocuparte por acentos ni mayúsculas— y dale Enter otra
vez. También puedes elegir el cuarto en la lista de la izquierda y apretar
Enter.

Los filtros no cambian solo lo que ves: **cambian por dónde te llevan las
flechas**. Con «solo picks» puesto, `→` salta al siguiente pick.

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

`⌘E` guarda un `manifest.json`. En Premiere, abre el panel del plugin y dale
a **Importar clasificación…**: arma los bins por cuarto, pone las etiquetas de
color, aplica los in/out y engancha los proxies.

Dentro de cada cuarto los clips quedan repartidos por cómo los marcaste:

```
Cocina
  ├── Destacados
  ├── Picks
  ├── Rejects
  └── Sin marcar
```

Solo aparecen las que tienen algo: un cuarto sin rejects no estrena esa
carpeta. Los clips a los que nunca les pusiste cuarto siguen cayendo juntos
en **Sin clasificar**.

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

Van a una carpeta **`Proxies` al lado** de la del material, para no ensuciar
la copia de la tarjeta.

**Lo que ganas**, medido con material real: abrir un clip pasa de 201 ms a
3 ms, saltar de 293 ms a 12 ms, y las portadas de la hoja de 7.7 min a 0.6 min
con 132 clips.

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
