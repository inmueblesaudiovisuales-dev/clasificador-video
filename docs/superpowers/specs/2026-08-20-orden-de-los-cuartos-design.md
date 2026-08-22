# El orden de los cuartos

*(Spec aprobado por Bruno el 2026-08-20. Nace de su forma de trabajar: «para
mí son dos fases: primero clasifico por cuarto y luego clasifico picks y no
picks», y para la segunda quiere «empezar con el primer cuarto que quiera».)*

## El problema

**La hoja acomoda los cuartos por abecedario, y el rail en el orden que Bruno
eligió.** Las dos listas se contradicen, y la de la hoja no se puede cambiar
de ninguna manera.

Reproducido: con el rail en `Fachada, Sala, Comedor, Cocina, Alberca, Baño 1`,
la hoja los dibuja `Alberca, Baño 1, Cocina, Comedor, Fachada, Sala`.

`_orden_de_grupo` ordena por el NOMBRE del cuarto. Subir y bajar cuartos en el
rail —que sí existe, con `⌥↑`/`⌥↓` y por el menú— no mueve un pixel en la
hoja. Por eso Bruno lo vivió como «no hay una forma de ordenar los cuartos»:
para la hoja, literalmente no la hay.

Y encima el número de la tecla sale del rail, así que su cuarto `1` puede
aparecer hasta abajo de la hoja.

## Lo que se construye

### 1. La hoja sigue el orden del rail

Un solo orden en toda la app: el que Bruno decide, el mismo que le da su
número a cada cuarto. Mueve un cuarto arriba y la hoja se reacomoda igual.

- **«Sin clasificar» se queda arriba de todo**, dentro de cada bin. Es la cola
  de trabajo y por eso va primero; esa regla no cambia.
- Un cuarto que por lo que sea no esté en la lista del rail va al final, en
  vez de romper el orden o desaparecer.
- El orden viaja del rail a la hoja igual que el de los bins
  (`set_bin_order`): la hoja no adivina, se lo dicen.

### 2. Los cuartos se arrastran en el rail

Agarras un cuarto y lo sueltas donde quieras. Mientras arrastras, una línea
marca dónde va a caer.

**Esto reabre una decisión de agosto y hay que decir por qué.** El
2026-08-08 se eligió menú contextual y NO arrastrar, con este argumento: son
«acciones de una vez por shooting --no merecen atajos nuevos ni el riesgo del
drag-and-drop dentro de un QVBoxLayout--».

La razón nueva es que **el supuesto era falso**: reordenar no es una vez por
shooting, es la manera en que Bruno decide por dónde empieza la fase 2, cada
shooting. Y con 13 cuartos, subir el último hasta arriba son doce
repeticiones de «Subir». Lo que se descartó por marginal resultó estar en el
camino.

**Lo que sigue valiendo de aquella decisión:** «Subir» y «Bajar» se quedan en
el menú. Dicen explícitamente que reordenar ES cambiar qué tecla le toca a
cada cuarto, y eso arrastrando no se lee. El arrastre se suma, no reemplaza.

### 3. Arrastrar un cuarto NO asigna nada

El gesto mueve el cuarto de lugar y **nada más**. No le pone ese cuarto a
ningún clip.

Es la misma regla que ya rige el arrastre de clips entre bins, y por el mismo
motivo: con dos significados en el mismo gesto, un arrastre mal soltado
cambia el dato que más trabajo cuesta.

## Lo que NO cambia

- **Reordenar sigue cambiando la tecla.** El cuarto que quede primero es el
  `1`. Es lo que Bruno quiere: poner arriba con lo que va a empezar.
- **`Subir` y `Bajar`** siguen en el menú contextual, y `⌥↑`/`⌥↓` con el
  teclado.
- **La lista de cuartos no se ordena sola.** Nada de alfabético automático ni
  de ordenar por cuántos clips tiene: el orden es una decisión de Bruno y la
  app no la toma por él.
- Arrastrar **clips** entre bins sigue igual, y sigue sin tocar el cuarto.

## Cómo se prueba

- Con el rail en un orden que no es alfabético, la hoja lo respeta.
- «Sin clasificar» sigue arriba de todo aunque el orden cambie.
- Un cuarto que no está en el rail cae al final y no rompe nada.
- Reordenar el rail reacomoda la hoja sin recargar las portadas ya cargadas.
- Soltar un cuarto en otra posición lo mueve ahí, y cambia su número.
- Soltarlo donde estaba no hace nada y no deja entrada de más.
- Arrastrar un cuarto no le cambia el cuarto a ningún clip.
- `Subir`, `Bajar` y `⌥↑`/`⌥↓` siguen funcionando igual.
