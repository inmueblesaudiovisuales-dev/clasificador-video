# Agrupar por cuarto, o solo etiquetar

*(Spec aprobado por Bruno el 2026-08-15. Nace de: «me gustaría que en la app
no necesariamente se ordene siempre por cuarto y a veces se pueda quedar
igual el orden pero sí poder ponerle su tag de cocina o de habitación».)*

## El problema

Hoy asignarle un cuarto a un clip lo **mueve**: la tarjeta salta al grupo de
ese cuarto y la grilla se reacomoda. Eso es lo que uno quiere cuando está
ordenando un shooting entero, y es lo que la hoja hace desde la F4.

Pero no siempre. A veces lo que se quiere es **recorrer el material como
salió de la cámara** —que es el orden en que se grabó, o sea el orden en que
uno se acuerda de las cosas— y nada más ir dejando anotado de qué cuarto es
cada toma. Ahí que la tarjeta se mueva es justo lo contrario de lo que
ayuda: pierdes el hilo de por dónde ibas.

Que el proyecto ya tenga `congelar_acomodo` —los clips no se reagrupan
mientras pintas, porque la grilla moviéndose bajo el cursor es
desorientadora— dice que el problema ya se había visto en chico.

## Qué se construye

Un interruptor en el encabezado de la hoja, al lado de los filtros:

```
AGRUPAR   [ por cuarto ] [ orden de rodaje ]
```

En **orden de rodaje** los clips se quedan exactamente donde están y no se
mueven nunca. El cuarto se sigue asignando igual —teclas, pincel, paleta— y
se ve en la tarjeta, que ya trae su franja de color y el nombre del cuarto.

## Las cinco reglas que lo hacen funcionar

1. **Los bins se quedan.** Son el otro eje —de qué cámara/tarjeta salió el
   clip— y no tienen nada que ver con esto. Lo que se aplana es el agrupado
   por cuarto de adentro de cada bin: un bin, una sola grilla.

2. **Las flechas no cambian.** `←/→` ya recorren el orden de rodaje filtrado
   (`filters.cola`), y nunca dependieron de cómo se dibujan los grupos. Con
   el interruptor en cualquier posición, la cola es la misma.

3. **`⌘A` sigue seleccionando «el grupo donde estás».** Sin agrupar por
   cuarto, el grupo **es el bin**. Sale solo: si el grupo se define como
   `(bin, cuarto)` y en este modo el cuarto no participa, `select_current_group`
   selecciona el bin entero sin tocarle una línea.

4. **El pincel mejora solo.** En este modo la grilla no se reacomoda nunca,
   ni al soltar la tecla, así que pintar una racha es completamente
   predecible.

5. **Se recuerda en el proyecto.** Va en el `.cvproj`, con `true` por
   omisión: un proyecto de antes de esto abre agrupado, que es como estaba.

## Lo que NO cambia

- **El dato.** `categoria_path` es el mismo campo y significa lo mismo. Esto
  es una vista, no una forma nueva de clasificar.
- **La exportación a Premiere.** Los bins por cuarto —y desde hoy sus
  subcarpetas por estado— salen del dato, no de cómo se ve la hoja.
- **Los filtros.** Siguen siendo la cola de navegación (DECISIONES.md). El
  agrupado no filtra nada: no esconde ni un clip.
