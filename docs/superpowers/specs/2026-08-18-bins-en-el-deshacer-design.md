# Los bins en el deshacer

*(Spec aprobado por Bruno el 2026-08-18. Nace de un bug medido ese día, no de
una función pedida.)*

## El problema, reproducido

`⌘Z` promete deshacer lo último y deshace otra cosa. Medido con la app
corriendo:

1. Clasificas tres clips: dos de **Sala**, uno de **Cocina**.
2. Arrastras un clip a otro bin —o se te va el arrastre sin querer—.
3. Aprietas `⌘Z`.

Resultado: **el clip se queda en el bin nuevo** y **el clip de Cocina pierde
su cuarto**. Dos cosas mal, y ninguna avisa.

La causa es que las acciones de bin nunca entraron al historial —`bins.mover`
está escrito a propósito para no tocarlo—, así que `⌘Z` no encuentra el
arrastre y revierte lo anterior que sí está. El botón `↺` del rail hace lo
mismo, porque leen la misma pila.

Esto ya estaba anotado en `CONTEXTO-Y-METAS.md` como «meter los bins al
historial que ya existe», o sea como una función que falta. Visto desde la
app no es eso: es un control que miente. Y pega justo donde el diseño quiso
ser cuidadoso —«arrastrar cambia el bin y nada más, para que un gesto mal
soltado no reclasifique»— porque deshacer ese gesto sí reclasifica, al revés.

## Lo que se construye

Tres acciones de bin entran al historial que ya existe, con su renglón en el
rail y su botón `↺`:

| Acción | Renglón | Qué devuelve |
|---|---|---|
| Arrastrar clips a otro bin | `Card B → 3 clips` | Cada clip a su bin de antes, o a «Sin bin» |
| Crear un bin | `Card C → bin nuevo` | Se quita el bin |
| Renombrar un bin | `Camara 1 → antes Card A` | El nombre viejo |

El cuadrito de color del renglón lleva la **identidad de cámara** que ya
existe (`theme.bin_color`), no el color de cuarto ni el de estado: es un tercer
canal y ya está separado a propósito en `theme.py`. De un vistazo se
distingue un renglón de bin de uno de cuarto.

## Las reglas

1. **Deshacer un arrastre cambia el bin y NADA más.** Ni el cuarto, ni el
   pick, ni el in/out. Es la misma regla que el arrastre ya tiene en un
   sentido, ahora también al revés — y es lo que hace que deshacer sea
   seguro de apretar.

2. **Un renglón que ya no se puede cumplir se apaga y dice por qué.** No
   desaparece: Bruno tiene que poder ver que la acción existió, igual que un
   proyecto que no se encuentra se ve apagado en la pantalla de inicio en vez
   de esfumarse. Son dos casos:
   - **«ya tiene clips»** — creaste un bin vacío y le arrastraste material.
     Ese arrastre fue una decisión aparte y más reciente; borrar el bin se
     llevaría dos cosas de un click. Si de verdad lo quieres quitar, primero
     deshaces el arrastre —que ahora sí se puede— y luego el bin.
   - **«ese bin ya no está»** — el bin al que habría que regresar los clips
     se fue.

3. **Renombrar un bin arregla los renglones viejos**, para que ninguno quede
   hablando de un nombre que ya no existe y prometiendo devolver algo
   inalcanzable. Es exactamente lo que se hizo con los cuartos el 2026-08-15
   (`History.renombrar_cuarto`), por el mismo motivo y con la misma forma.

4. **Quitar un bin sigue borrando el historial entero**, como hoy. No se
   toca: sacar clips corre los números de todos los demás, y cada entrada del
   historial habla por número de clip. Ese camino ya está resuelto y es la
   razón por la que quitar un bin NO entra en este trabajo.

## Cómo se guarda

`HistoryEntry.antes` es `{índice_de_clip: {campo: valor_anterior}}` y se
aplica con `setattr` sobre el `Clip`. **El bin no es un campo del clip** —vive
en `BinTree`, que es la única fuente de verdad— así que no puede viajar por
ahí.

Se le agregan a `HistoryEntry` dos campos opcionales, con la misma forma que
el `cuarto_borrado` que ya existe para el borrado de un cuarto:

- `bins_antes: dict[int, str | None] | None` — de qué bin venía cada clip.
  `None` como valor significa «Sin bin».
- `bin_creado: str | None` — el bin que esta acción creó, para poder
  quitarlo.

El renombrado lleva su propio campo, `bin_renombrado: tuple[str, str] | None`
—`(viejo, nuevo)`—, y no se deduce del texto del renglón: la `etiqueta` y el
`detalle` son para el ojo, y leerlos como dato es lo que hace que cambiar una
palabra rompa una función.

Quien aplica sigue siendo `MainWindow._aplicar_entrada`, que ya es el único
lugar donde el estado guardado se vuelve a poner. `History` se queda sin Qt y
sin saber qué es un bin, igual que hoy.

## Lo que NO cambia

- **Arrastrar sigue sin tocar el cuarto.** Este trabajo no reabre eso.
- **El límite de 50 acciones** es el mismo.
- **El historial sigue sin guardarse en disco**: es de la sesión abierta. Al
  reabrir se recupera el trabajo (de eso se encarga el autosave) pero no el
  historial.
- **`bins.mover` sigue sin tocar el historial por su cuenta.** Quien decide
  qué se registra es la ventana, que es la que sabe si el movimiento vino de
  un gesto de Bruno o de deshacer otra cosa — si `mover` registrara solo,
  deshacer un arrastre metería su propia entrada y `⌘Z` se volvería un
  columpio.

## Cómo se prueba

Lo que hay que defender es el bug, no la mecánica:

- El caso completo de arriba: clasificar, arrastrar, `⌘Z` — el clip vuelve a
  su bin **y** el cuarto del otro clip sigue puesto.
- Deshacer un arrastre de varios clips que venían de bins distintos: cada uno
  a donde estaba, no todos al mismo.
- Un clip que venía de «Sin bin» vuelve a «Sin bin», no al primer bin.
- Deshacer no toca cuarto, estado ni in/out.
- El renglón se apaga cuando el bin creado ya tiene clips, y sigue apagado
  después de refrescar la hoja.
- Renombrar un bin deja los renglones viejos hablando del nombre nuevo.
- Quitar un bin sigue vaciando el historial.
