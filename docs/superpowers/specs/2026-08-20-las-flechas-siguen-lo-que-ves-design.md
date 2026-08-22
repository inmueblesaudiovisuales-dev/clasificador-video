# Las flechas siguen lo que ves

*(Spec aprobado por Bruno el 2026-08-20. Nace de un bug que reportó: «cuando
estoy haciendo un cuarto y le doy a la flecha para el siguiente, a veces se va
a otro cuarto aun cuando hay clips pendientes de ese cuarto».)*

## El problema, reproducido

**La hoja dibuja una lista y las flechas se mueven por otra.**

Con seis clips intercalados —Cocina, Sala, Cocina, Sala…— y la hoja agrupando
por cuarto:

- la hoja los dibuja **1, 3, 5, 2, 4, 6**: los tres de Cocina juntos, luego
  los tres de Sala;
- `→` lleva **1 → 2 → 3 → 4**: orden de grabación, brincando de Cocina a Sala
  en cada teclazo.

Por eso te saca del cuarto aunque queden pendientes: el siguiente en orden de
grabación es de otro cuarto.

**La causa es de fecha, no de descuido.** `filters.cola()` dice «No se
reordena nunca: es el orden de rodaje». Eso se escribió cuando la hoja NO
agrupaba por cuarto y las dos listas coincidían. Al agrupar, se separaron.

Es el mismo tipo de contradicción que el orden de los cuartos entre el rail y
la hoja: dos listas del mismo dato que no se hablan.

## Lo que se construye

**Las flechas recorren los clips en el orden en que se dibujan.**

- Con **«Por cuarto»**: terminas Cocina y recién entonces pasas a Sala. Los
  cuartos van en el orden del rail, y «Sin clasificar» primero — el mismo
  orden que ya ves.
- Con **«Orden de rodaje»**: queda idéntico a hoy, porque ahí las dos listas
  ya coincidían. No es un caso aparte: es la misma regla dando el mismo
  resultado.

El orden lo decide la hoja, que es quien lo dibuja. La ventana **no lo
recalcula**: pedírselo a otro es cómo se separaron estas dos listas la
primera vez.

**Si la hoja todavía no tiene tarjetas** —al abrir un proyecto, antes del
primer acomodo— la cola se queda en orden de grabación. Es un respaldo, no un
caso de uso: sin él, abrir un proyecto dejaría las flechas sin lista.

## Lo que NO cambia

- **El filtro sigue mandando sobre QUÉ entra en la cola.** Esto solo cambia
  el ORDEN de lo que ya pasó el filtro. Con «solo picks» puesto, `→` sigue
  saltando al siguiente pick.
- **Marcar pick o reject sigue sin avanzar.** Se comprobó: el clip actual se
  queda donde está. Lo que se mueve al marcar es lo que el filtro esconde.
- **Asignar un cuarto sigue avanzando**, y ahora avanza dentro de la lista
  que estás viendo.
- **`S` no depende de esto.** Desde hoy pone el último cuarto que usaste, no
  el del clip anterior, así que reordenar la cola no la afecta.

## Cómo se prueba

- Con clips intercalados y «Por cuarto», `→` recorre un cuarto completo antes
  de pasar al siguiente.
- Con «Orden de rodaje», `→` da exactamente lo mismo que antes del cambio.
- Los cuartos se recorren en el orden del rail, no en el alfabético.
- «Sin clasificar» se recorre primero.
- Un filtro puesto sigue recortando la cola, y el orden nuevo se aplica a lo
  que queda.
- Sin tarjetas en la hoja, la cola cae en orden de grabación y las flechas
  siguen funcionando.
- `←` es exactamente el reverso de `→`.
