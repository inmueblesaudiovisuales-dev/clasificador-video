# Modo horizontal: el visor sin la hoja al lado

*(Spec aprobado por Bruno el 2026-08-15, con los números a la vista.)*

## El problema, medido

El cuerpo de la ventana es una fila: `rail │ video │ columna │ hoja`. El
ancho del video sale de la forma del clip y los paneles absorben el resto —
que es lo que hace que un clip **vertical** calce exacto, sin una franja
negra, en cualquier tamaño de ventana. Medido: 472×840 en una ventana de
1600×900, aspecto pedido 0.562, aspecto real 0.562.

Con un clip **horizontal** no alcanza. El ancho que pide un 16:9 a toda
altura son 1493 px, y lo que queda después del rail (200), la columna (56) y
el mínimo de la hoja (405) son 939. El visor se queda alto y angosto, y mpv
rellena con negro:

| ventana | clip | widget | imagen |
|---|---|---|---|
| 1600×900 | 9:16 | 472×840 | 472×840 — calza |
| 1600×900 | 16:9 | 939×840 | **939×528**, el resto negro |
| 1100×700 | 16:9 | 439×640 | 439×247 — dos tercios negro |

## Lo que se descartó, y por qué

**Mover la hoja debajo del video.** Fue la primera idea y es la peor de las
tres: da 1077×605, o sea 1.3× de área, y cuesta reestructurar el cuerpo de
la ventana. La razón es que **para un clip horizontal lo que estorba es el
ALTO, no el ancho**: la tira de la hoja necesita 234 px (su encabezado son
122 y una fila de tarjetas 82), y esos 234 salen del video. Se cambia un
problema de ancho por uno de alto.

**Achicar el visor para que no queden franjas.** No agranda la imagen: el
clip ya mide 939×528 en los dos casos, lo único que cambia es de qué color
es lo que sobra.

## Lo que se construye

Un modo en el que **la hoja de contactos se esconde y todo lo demás se
queda**: el rail con sus cuartos, sus conteos, el historial y la fila de
`S`, y la columna con el estado del clip. Lo único que dejas de ver son las
miniaturas, que es lo que no estás mirando mientras revisas toma por toma.

| | imagen | contra hoy |
|---|---|---|
| hoy | 939×528 | — |
| hoja abajo (descartado) | 1077×605 | 1.3× |
| **modo horizontal** | **1344×756** | **2.0×** |
| `F`, que ya existe | 1600×900 | 2.9× |

`F` sigue siendo el máximo y no se toca: esconde TODO. Este modo es el punto
medio, el que deja seguir clasificando con el rail a la vista.

## Las reglas

1. **Es un interruptor, no una adivinanza.** La app no mira la forma del
   clip para decidir: con material mezclado el layout saltaría en cada
   flecha, y «que la app adivine» ya está descartado en CONTEXTO-Y-METAS
   («cuando acierta es mágico; cuando falla es confuso»).

2. **Se recuerda en el proyecto**, como el agrupado. La respuesta depende
   del shooting, no del día.

3. **`⇥` sigue mandando.** En modo hoja la hoja se ve, aunque el modo
   horizontal esté puesto: sin hoja no hay modo hoja. El modo horizontal
   solo decide qué pasa en modo CLIP.

4. **`F` gana sobre los dos.** Solo video esconde todo, y al salir cada uno
   vuelve a donde estaba.

5. **Una sola regla de visibilidad de la hoja**, en un solo lugar. Vivía
   repartida entre `alternar_modo_hoja` y `alternar_solo_video`, y con tres
   modos que la tocan, repartida se contradice sola — es exactamente el bug
   que ya tuvo la barra de media faltante.
