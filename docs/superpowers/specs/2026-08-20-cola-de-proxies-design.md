# La fila de proxies

*(Spec aprobado por Bruno el 2026-08-20. Nace de usar la app: «es muy
ineficiente tener que esperar a que termine para poder empezar los
proxies».)*

## El problema

Con dos tarjetas —la Sony y el dron— hay dos bins que necesitan proxies. Hoy
solo se puede uno a la vez: pedir el segundo contesta *«Se están creando los
proxies de Card A. Espera a que termine, o cancélalo desde el menú de ese
bin.»*

Y esperar no es lo caro. Lo caro es **tener que acordarse de volver**: la
tanda del dron son varios minutos, y al terminar nadie avisa que ya se puede
pedir la siguiente. Bruno se queda vigilando, o se le olvida y los proxies de
la segunda tarjeta no existen cuando los necesita.

## Lo que NO es el problema, aunque lo pareció

Durante el brainstorm se dijo que un proxy interrumpido dejaba un archivo
roto que bloqueaba ese clip para siempre. **Es falso, y queda escrito para
que nadie lo vuelva a "arreglar":** `proxy_gen.generar` ya escribe a
`<nombre>.mp4.parcial` y solo hace `replace` al nombre bueno cuando ffmpeg
devuelve 0. Un corte a la mitad borra el parcial; un cierre de golpe lo deja,
pero con el nombre `.parcial`, que `ruta_de_proxy(...).exists()` no ve — o
sea que el clip sigue contando como pendiente y se vuelve a generar solo.

**Reanudar tampoco hay que construirlo: ya funciona.** Cancelas, le vuelves a
dar, y `faltantes()` se salta lo hecho. Comprobado con la app: con tres clips
y uno hecho, ofrece «se van a crear 2 proxies».

Lo único de verdad en esa zona es que **los `.parcial` de un cierre de golpe
no los borra nadie** y se van juntando en la carpeta. No estorban; ensucian.

## Lo que se construye

### 1. La fila

Pides «Crear proxies del bin…» en los bins que quieras. El primero arranca;
los demás **se forman** y corren en orden, uno tras otro. Sigue generando de
uno en uno: eso es deliberado (`_generacion_pool` con un solo hilo) y no se
toca — dos ffmpeg peleando por el mismo chip no terminan antes.

- El bin que corre sigue diciendo **«creando proxies · 7/23»**.
- Los que esperan dicen **«en cola»**.
- Al terminar uno, el siguiente arranca solo.

**Lo que se guarda en la fila es el NOMBRE del bin, no la lista de clips.**
La lista se calcula cuando le toca su turno, no cuando lo pides: entre que lo
pides y que arranca pueden pasar cosas —arrastras clips a ese bin, enganchas
proxies a mano, quitas material— y una lista calculada de antes describiría
un bin que ya no es ese. Como efecto, el número del cartel de confirmación
(«se van a crear 12») es lo que se sabe **al pedirlo**, y el trabajo real
puede ser otro. Es la respuesta honesta: al pedirlo, eso es lo que hay.

Pedir un bin que ya está corriendo o ya está formado no lo mete dos veces:
te dice que ya está pedido.

### 2. Cancelar es por bin

Desde el menú de un bin, «Cancelar» cancela **ese** y nada más.

- Si era el que corría: se detiene, lo hecho se queda enganchado, y **el
  siguiente de la fila arranca solo**.
- Si todavía esperaba: sale de la fila y su insignia vuelve al conteo real.

El menú ofrece «Cancelar» cuando el bin está corriendo **o** formado, y deja
de ofrecer «Crear proxies del bin…» en esos dos casos — hoy solo mira el que
corre.

### 3. Un solo cartel, al final de todo

Hoy sale un resumen al terminar cada tanda. Con cuatro bins formados serían
cuatro carteles seguidos, y probablemente cuando ya nadie está viendo.

Pasa a haber **uno solo, cuando la fila se vacía**, con la cuenta de todo lo
que corrió: «68 proxies creados, 2 fallaron».

Se mantiene la regla que ya existe —**lo cancelado no saca cartel**, porque
cancelar fue una decisión de Bruno y no hace falta confirmársela— y con una
fila eso hay que decirlo con más precisión, porque se puede cancelar una
parte:

- Los proxies que un bin alcanzó a crear **sí cuentan** en el total, lo hayas
  cancelado o no. Se hicieron y están enganchados; no mencionarlos sería
  mentir en el otro sentido.
- Cancelar **no agrega un renglón** al cartel. No dice «1 bin cancelado».
- Si al vaciarse la fila no se creó ni un proxy —cancelaste todo antes de que
  saliera el primero— **no hay cartel**.

### 4. Barrer los `.parcial`

Al empezar la tanda de un bin, se borran los `*.parcial` que haya en su
carpeta de proxies.

**Por qué ahí y no en cualquier momento:** un `.parcial` puede ser el archivo
que se está escribiendo en este instante. Al empezar una tanda no hay
ninguno en vuelo —se genera de uno en uno, y la fila arranca la siguiente
solo cuando la anterior terminó— así que ahí el barrido no puede pisarle el
archivo a nadie. Dos bins de la misma carpeta comparten carpeta de proxies, y
por eso el momento importa: si esto se moviera a «cuando se pide», barrería
mientras el otro bin escribe.

## Lo que NO cambia

- **De uno en uno.** No se paraleliza; ver arriba.
- Los proxies siguen yendo a la carpeta `Proxies` **al lado** del material.
- **Cada proxy se engancha apenas termina**, no al final de la tanda: es lo
  que hace que se vea el material aligerarse conforme avanza.
- La validación cuadro a cuadro sigue igual de estricta. El que no calce no
  se engancha, aunque lo hayamos generado nosotros.
- `faltantes()` y el salto de lo ya hecho se quedan como están: ya hacen lo
  correcto.
- Quitar un bin o cerrar el proyecto sigue **tirando la tanda entera** —y
  ahora también la fila—, por el mismo motivo de siempre: los índices de clip
  se corren y lo que llegue ya no describe a nadie.

## Cómo se prueba

Lo que hay que defender es lo que se rompe en uso, no la mecánica:

- Pedir un segundo bin mientras corre el primero lo **forma**, no lo rechaza.
- Al terminar el primero, el segundo **arranca solo**.
- La insignia de un bin formado dice «en cola», y la del que corre sigue
  diciendo el avance.
- Cancelar el que corre arranca el siguiente; cancelar uno formado no toca al
  que corre.
- Pedir dos veces el mismo bin no lo mete dos veces.
- Con cuatro bins, sale **un** cartel y no cuatro, y sus números son la suma.
- Cancelarlo todo no saca cartel.
- Un `.parcial` en la carpeta se borra al empezar la tanda, y un `.mp4` bueno
  que esté ahí **no**.
- Quitar un bin a media fila la vacía entera.
