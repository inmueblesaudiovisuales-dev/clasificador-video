# Qué trae cada versión

Escrito para quien usa la app, no para quien la programa: qué cambió y qué
vas a notar. El detalle técnico de cada cambio vive en los mensajes de commit
y en `docs/superpowers/specs/`.

La versión se ve **abajo a la derecha de la pantalla de inicio**. Es lo
primero que hay que saber para reportar cualquier cosa.

---

## 1.11 — 25 de agosto de 2026

- **El primer video ya se ve al abrir.** Antes el primero de cada sesión salía
  negro y había que irse al segundo y volver. La app abría el clip mientras el
  visor todavía estaba escondido detrás de la hoja, así que la imagen se
  cargaba sin tener dónde dibujarse. Ahora el visor la vuelve a pedir en
  cuanto enciende.
- **Tú eliges dónde van los proxies.** La primera vez que creas proxies en un
  proyecto, la app te pregunta — y llega ya contestada, con la carpeta que
  encontró junto a tu material y la ruta a la vista. Un clic y listo. Se puede
  cambiar después desde el menú del bin.
- **Cada carpeta de material tiene su propia carpeta de proxies adentro.** Ya
  no caen todos revueltos en un montón: si dos cámaras nombran igual un
  archivo, ya no se pisan.
- **Nada se mueve en los proyectos que ya tienes.** La app sigue mirando los
  tres sitios donde han vivido los proxies, así que abren igual y no
  regeneran nada.

## 1.10 — 22 de agosto de 2026

- **Los proxies nuevos van adentro de la carpeta del material**, no al lado.
  Así viajan con ella cuando mueves o copias la carpeta a otro disco. Si esa
  carpeta no se deja escribir —una tarjeta protegida o llena— caen al lado,
  como antes.
- **Los proxies de proyectos anteriores siguen sirviendo.** La app busca en
  los dos sitios, así que un proyecto viejo abre igual y no regenera nada.

## 1.9 — 22 de agosto de 2026

- **Los destacados van en la carpeta Picks**, junto con los demás. Los sigues
  reconociendo por su etiqueta dorada en Premiere.
- **`⌘E` propone el nombre de tu proyecto** —`IAV-2608.17.json`— en vez de
  `manifest.json`, que con varios shootings eran cinco archivos idénticos.

**Plugin de Premiere 1.1.0**, que se instala aparte:

- **Un hueco en la lista de Premiere ya no tumba un clip.** Importando 200
  clips, Premiere devolvía la lista de un bin con un elemento vacío y ese
  clip se quedaba fuera del proyecto sin más aviso que un `[ERROR]`.
- **Si un clip falla, el error dice a qué bin iba**, para arrastrarlo a mano
  sin ir a buscar dónde debía estar.

## 1.8 — 20 de agosto de 2026

- **Abrir un proyecto pasó de 34 segundos a menos de 3.** Cada clip guarda 12
  fotos para escrubear, y al abrir se cargaban las 12 de los 205 — 2,460
  imágenes de golpe. Ahora carga solo la portada, y las demás cuando pasas el
  mouse por esa tarjeta.
- **Pantalla de carga** al abrir un proyecto, con su nombre y una barra.
- **La ventana abre maximizada**, ocupando tu pantalla. Antes eran 1100×700
  fijos sin mirar el monitor.

## 1.7 — 20 de agosto de 2026

- **Un solo orden de cuartos en toda la app.** La hoja los acomodaba por
  abecedario y la lista de la izquierda en el orden que tú elegiste, así que
  moverlos no servía de nada.
- **Los cuartos se arrastran** para cambiarlos de lugar, con una línea que
  marca dónde van a caer. El que quede arriba es el `1`.
- **Las flechas siguen el orden que ves**: con «Por cuarto» puesto, `→`
  termina un cuarto antes de pasar al siguiente.

## 1.6 — 20 de agosto de 2026

- **`S` pone el último cuarto que usaste**, no el del clip de al lado. Antes,
  con material clasificado de una pasada anterior, te daba un cuarto viejo.
- **Los cuartos del 10 en adelante ya se alcanzan.** El buscador que abre `⏎`
  muestra todos con scroll, la lista de la izquierda dice `⏎` donde no hay
  número, y `⏎` sobre un cuarto lo asigna. Renombrar se movió a `F2` y al
  doble clic.

## 1.5 — 20 de agosto de 2026

- **El botón de crear proxies llega al arreglo de la 1.4.** En la 1.4 el
  arreglo estaba pero el botón cortaba antes con «todos ya tienen proxy».

## 1.4 — 20 de agosto de 2026

- **Un proxy que quedó en el disco sin engancharse ahora se engancha**, en
  vez de darse por hecho y dejar al clip sin proxy para siempre.
- **Al terminar una tanda se recoge lo que quedó suelto**, para que no haga
  falta una segunda corrida.

## 1.3 — 20 de agosto de 2026

- **La app dice qué versión es**, abajo a la derecha de la pantalla de inicio.
- **La app no suena.** Ni los clips ni las miniaturas al importar.
- **La fila de proxies:** pides los bins que quieras y se forman. Cada uno se
  cancela por su lado y sale un solo aviso al final.

## 1.2 — 18 de agosto de 2026

- **Las acciones de bin se deshacen con `⌘Z`**: mover clips, crear y
  renombrar. Antes `⌘Z` no encontraba el arrastre y revertía en silencio una
  acción anterior — te quitaba un cuarto que sí querías.
- **Un renglón del historial que ya no se puede cumplir se apaga y dice por
  qué**, en vez de hacer otra cosa.

## 1.1 — 12 de agosto de 2026

- **El botón «Ancho»** esconde la hoja en modo clip y le da su espacio al
  video. Se queda hundido mientras está puesto.
- **Agrupar por cuarto, o dejar el orden de rodaje** y que el cuarto sea solo
  una etiqueta.
- **En Premiere, cada cuarto se reparte por estado** en Picks, Rejects y Sin
  marcar.
- **Un proyecto que no se encuentra se puede quitar de la lista.**
- Y una tanda de arreglos: el rango de `⇧`+clic se cuenta como se ve,
  renombrar un cuarto lo renombra también en el historial, y la ventana ya no
  crece sola con material horizontal.

---

Antes de la 1.1 la app ya clasificaba un shooting completo con el teclado,
agrupaba por bins, generaba proxies y exportaba a Premiere. El historial
completo está en los commits.
