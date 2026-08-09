# Crear muchos cuartos de un jalón — diseño

*(Spec. Fecha: 2026-08-09. Pedido de Bruno: «me gustaría que pongamos una
forma más rápida de poner muchos cuartos».)*

## 1. El problema

Hoy se crea **un cuarto a la vez**: el `+` del rail abre un `QInputDialog`,
escribes un nombre, aceptas, y repites. Para una casa de seis cuartos son seis
vueltas del mismo diálogo antes de poder clasificar el primer clip.

Y Bruno graba inmuebles: **los cuartos se repiten casa tras casa**. Cocina,
recámaras, baños, sala, fachada. Escribir la misma lista en cada proyecto es
trabajo que la app puede quitarle.

## 2. Lo que NO cambia

`RoomSelection` no se toca en su idea central: la lista es plana, sin techo, y
**el orden ES la asignación de teclas** — el primero contesta a `1`, el
segundo a `2`. Crear seis de golpe simplemente los mete en orden con `add`,
uno tras otro, y las teclas salen solas.

Y sobre todo: **sigue sin haber un paso de configuración antes de trabajar**.
La app abre con el panel de cuartos vacío y se puede escribir un cuarto suelto
como hoy. Esto es una decisión ya tomada (ver `DECISIONES.md`, «Cuartos:
planos, sin techo, sin configuración inicial») y esta función no la reabre:
las plantillas son un atajo disponible, nunca una pantalla que se atraviesa.

## 3. La interfaz

**Un solo lugar, el mismo de hoy**: el `+` del panel de cuartos. En vez de un
diálogo modal, abre un panel pequeño ahí mismo, con tres partes.

### 3.1 El campo que acepta varios

```
Cocina, Recámara 1, Recámara 2, Baño, Sala, Fachada
```

- Separadores: **coma o salto de línea**. Los dos, porque pegar una lista de
  otro lado suele traer saltos.
- Se recortan espacios de los extremos; los renglones vacíos se ignoran.
- **Los repetidos se ignoran solos** — `RoomSelection.add` ya lo hace, y esa
  regla existe por una razón: dos cuartos con el mismo nombre serían dos
  teclas que hacen lo mismo y un grupo partido en dos en la hoja.
- Al aceptar, quedan todos en orden con sus teclas.
- **Se puede seguir usando para uno solo**: escribes «Cocina», Enter, listo.
  No hay dos caminos según cuántos vayas a crear.

### 3.2 Autocompletar

Mientras escribes, la app propone nombres que **ya usaste en proyectos
anteriores**. `Tab` completa la sugerencia; seguir escribiendo la ignora. No
obliga a nada: si escribes un nombre nuevo, se crea ese.

El historial se guarda en `~/.clasificador_video/`, junto a `sesion.json`, y
solo acumula nombres — nunca decide por su cuenta.

### 3.3 Plantillas

Debajo del campo, las plantillas guardadas: *Casa 2 recámaras*, *Depa*,
*Terreno*. Un clic mete todos sus cuartos.

- **Se crean desde el propio panel de cuartos**, con «guardar estos como
  plantilla»: la plantilla nace de una lista que ya te funcionó, no de un
  formulario aparte donde hay que inventarla desde cero.
- **Aplicar una plantilla agrega, no reemplaza.** Si ya tenías cuartos, los
  de la plantilla se suman al final; los repetidos se ignoran. Nunca se pierde
  algo que ya estaba, y por lo tanto nunca hace falta preguntar «¿seguro?».
- Se pueden renombrar y borrar.
- Viven en `~/.clasificador_video/plantillas.json`, con la misma escritura
  atómica de `autosave.py` (temporal + `rename`), y un archivo corrupto o
  ausente se trata como «no hay plantillas» en vez de tirar la app.

## 4. Qué NO entra

- **Traer los cuartos de la última sesión** con un botón. Se ofreció y no se
  eligió: las plantillas cubren el mismo caso y además duran.
- **Plantillas que traigan algo más que nombres** (colores fijos, orden de
  teclas propio). El color sale de la posición y ahí se queda.
- **Compartir plantillas entre computadoras.**

## 5. Cómo se comprueba

- **Tests** de lo que es lógica pura: partir el texto por comas y saltos,
  espacios, renglones vacíos, repetidos dentro del mismo pegado, repetidos
  contra los que ya existían, y que el orden de escritura es el orden de las
  teclas. Guardar, cargar, renombrar y borrar plantillas, más el archivo
  corrupto.
- **Verificación visual real** del panel abierto, con `grab()`, según
  `CLAUDE.md`.
- **Sin `exec()`.** El panel no es modal: el `QInputDialog` de hoy
  (`room_rail._pedir_cuarto_nuevo`) es de la clase de diálogo que colgaba la
  suite bajo `offscreen` antes de la F3, y esta función lo sustituye en vez de
  agregarle otro al lado.
