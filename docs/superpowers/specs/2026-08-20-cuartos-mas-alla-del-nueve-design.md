# Los cuartos más allá del nueve

*(Spec aprobado por Bruno el 2026-08-20, después de toparse con esto
clasificando un shooting con 13 cuartos.)*

## Los dos problemas, reproducidos

### 1. `S` da un cuarto viejo

`S` **no copia el último cuarto que usaste**: copia el del clip de al lado
hacia atrás, en orden de grabación. Mientras avanzas en orden es lo mismo; se
separan en cuanto te saltas clips o hay material clasificado de una pasada
anterior.

Reproducido: le pones «Alberca» al clip 2, te mueves al clip 7, aprietas `S`
— y te pone «Cocina», que es lo que tenía el clip 6 de antes. Bruno lo
describió como «a veces `S` es el cuarto penúltimo en lugar del último».

### 2. A los cuartos del 10 en adelante no se llega

Los atajos numéricos llegan al noveno (`MAX_TECLAS = 9`). Del décimo en
adelante el rail muestra **un cuadrito vacío** donde iría el número: dice
«aquí no hay tecla», pero no dice a dónde ir.

`⏎` abre un buscador de cuartos que **ya existe y funciona** —busca sin
acentos, y al confirmar prefiere elegir sobre crear— pero:

- **solo muestra 6 cuartos** hasta que escribes algo, así que con 13 siete no
  aparecen y parece que no están;
- no está documentado en ninguna parte: ni en el README, ni en la barra de
  ayuda;
- y con una fila del rail enfocada, `⏎` **renombra** ese cuarto en vez de
  asignarlo. Eso es lo que Bruno encontró: «poner enter no me deja
  seleccionar cuartos, solo hacer nuevos».

## Lo que se construye

### 1. `S` es «el último cuarto que usaste»

La app se acuerda del último cuarto que asignaste **en esta sesión**, y `S`
pone ese, estés donde estés.

- Si todavía no has asignado ninguno —acabas de abrir el proyecto— cae en el
  comportamiento de hoy: el cuarto del clip anterior con cuarto. Así `S`
  sigue sirviendo desde el primer teclazo y no hay un estado muerto al abrir.
- Cuenta cualquier forma de asignar: la tecla numérica, el buscador, el rail,
  el pincel y el lote. Lo que importa es «el último que usaste», no por dónde
  entró.
- **Deshacer no lo mueve.** `⌘Z` revierte el dato, no tu intención: si
  deshaces y vuelves a apretar `S`, sigue siendo el cuarto que estabas
  usando. Lo contrario haría que deshacer cambiara en silencio lo que la
  siguiente tecla va a hacer.
- Renombrar un cuarto lo sigue: si renombras el que tenías en la mano, `S`
  sigue apuntando al mismo cuarto con su nombre nuevo. Borrarlo lo deja en
  nada, y `S` vuelve al respaldo.

### 2. El buscador muestra TODOS los cuartos

Al abrir con `⏎` se ven todos, con scroll si no caben, en vez de los primeros
seis. Moverse con `↑`/`↓` arrastra el scroll: una fila marcada que no se ve
es lo mismo que no tenerla.

El tope de altura se queda —la paleta no puede tapar media pantalla— pero
deja de ser un tope de *cuántos cuartos existen* para ser uno de *cuántos
caben a la vez*.

### 3. En el rail, `⏎` asigna

Con una fila del rail enfocada o seleccionada, `⏎` **le pone ese cuarto al
clip actual** (o a la selección, como cualquier otra forma de asignar).

**Renombrar se mueve a `F2`** y al doble clic, que ya funcionan y ya están en
el menú contextual. No se pierde nada: se cambia una tecla de sitio.

El porqué del cambio y no de agregar otra tecla: el rail es una lista de
cuartos junto al video, y lo que uno quiere hacer con un cuarto mientras
clasifica es **ponérselo a un clip**. Renombrar es mantenimiento, y el
mantenimiento no se queda con la tecla más obvia.

### 4. El rail dice a dónde ir

En los cuartos sin número —del décimo en adelante— el cuadrito vacío pasa a
mostrar **`⏎`**. Es el mismo espacio y deja de ser un hueco: dice que ese
cuarto se pone con Enter, que es exactamente lo que hace falta saber.

## Lo que NO cambia

- **Los atajos `1`-`9` se quedan como están.** Siguen siendo la vía rápida y
  siguen apuntando a los primeros nueve cuartos del rail.
- **No se agregan teclas nuevas** tipo `⇧1`. Se evaluó y Bruno prefirió que
  la paleta y el rail hagan bien su trabajo antes que meter otra tecla que
  recordar.
- El buscador sigue prefiriendo **elegir sobre crear**, y sigue buscando sin
  acentos ni mayúsculas.
- Asignar un cuarto sigue avanzando al siguiente clip.

## Cómo se prueba

- `S` pone el último cuarto usado aunque el clip anterior tenga otro — el
  caso reproducido, tal cual.
- `S` sin haber usado ninguno cae en el cuarto del clip anterior.
- Deshacer no cambia lo que `S` va a poner.
- Renombrar el cuarto que `S` tiene en la mano lo sigue; borrarlo lo suelta.
- El buscador abre con los 13 cuartos, no con 6.
- `↑`/`↓` en el buscador dejan a la vista la fila marcada.
- `⏎` con una fila del rail enfocada asigna, y NO abre el renombrado.
- `F2` y el doble clic siguen renombrando.
- El rail muestra `⏎` en el décimo cuarto y el número en el noveno.
