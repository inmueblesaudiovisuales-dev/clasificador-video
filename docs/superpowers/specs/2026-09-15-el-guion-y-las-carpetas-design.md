# El guion y las carpetas son dos cosas — diseño

*(Spec. Fecha: 2026-09-15. Sale de la plática con Bruno del mismo día, al
revisar cómo se ve la guía en el panel de Premiere.)*

**Este documento le cambia el §3.6 y el §4.d a
`2026-09-14-guia-de-edicion-en-clipify-design.md`**, y le agrega una parte al
patrón de recorrido. Lo que no pierde ninguno de los dos está en el §8.

## 1. De dónde salió

La conversación empezó por el dibujo del panel. A media plática, Bruno:

> «Tal vez deberíamos de dejar de vincular explícitamente los bins con el
> orden de las tomas. Porque muchas veces empiezo con una toma aérea y
> termino con una toma aérea y están en el mismo bin.»

Tiene razón, y sus propios videos lo dicen sin margen. De sus quince
entregables de 2026:

- **En los quince** se repite algún cuarto.
- **En catorce de quince**, el cuarto con el que abre vuelve a salir después.
- En uno, la aérea sale once veces.

Ese dato estaba en `docs/patron-de-recorrido/datos/fichas.json` desde el
principio y se leyó mal: para escribir `MI-PATRON.md` se sacó la **posición
mediana** de cada cuarto, y promediar es justo lo que esconde que algo sale
dos veces. La mediana de la aérea —0.75— describe un cuarto que va al final.
No existe tal cuarto: existe una aérea que abre, otra a media casa y dos que
cierran.

## 2. La premisa que se cae

El spec del 14 de septiembre decía, en su §3.6:

> **El orden aceptado se vuelve EL orden de los cuartos** — el del rail, el de
> la hoja y el de Premiere.

Eso da por hecho que el orden del video es un orden **de cuartos**. No lo es.

**Una carpeta es un lugar. Un recorrido es una secuencia.** Un lugar existe una
vez; en una secuencia puede aparecer las veces que haga falta. Son dos cosas
distintas y no pueden llevar el mismo número: si la aérea es el paso 1 y el
paso 11, su carpeta no puede llamarse `01.` y `11.` a la vez.

## 3. Las decisiones

Cada renglón es una respuesta explícita de Bruno, en el orden en que las dio.

1. **La guía es un GUION: una lista de pasos, no de cuartos.** Un cuarto puede
   salir las veces que haga falta, y eso deja de ser un error.
2. **Las carpetas se numeran por la PRIMERA aparición del cuarto en el guion.**
   La aérea que abre en el paso 1 y cierra en el 11 tiene una sola carpeta,
   `01. Aérea`. Se le ofrecieron las otras dos formas —sin número, o con todos
   sus pasos (`01·11. Aérea`)— y escogió ésta: conserva las carpetas en orden
   de entrada, que es lo que pidió el 14, y deja el guion libre.
3. **El panel lleva un encabezado que no se mueve**: en qué paso vas, cuántos
   llevas y de qué rodaje es. De las tres formas que se dibujaron —lista
   ordenada, tarjetas, lista con encabezado— escogió ésta.
4. **Se puede ir palomeando lo que ya montaste**, paso por paso.
5. **La pestaña SÍ puede escribir.** Es un cambio de postura explícito: el spec
   del 14 la dejaba de lectura entera. Ver el §5.
6. **El patrón se reescribe con su orden**, dicho por él (§6).

## 4. Qué cambia en cada pieza

### 4.a En Clipify: dejar de estorbar

Tres cosas impiden hoy que el guion repita, y las tres se van:

- **El prompt le prohíbe repetir** al modelo: «sin agrupar, sin partir ninguno
  en dos» y «tienen que estar TODOS y ninguno de más». Pasa a pedirle lo
  contrario: que repita cuando el recorrido lo pida, y que lo diga en la línea
  del paso.
- **La revisión marca los repetidos como problema** (`Revision.repetidos` y su
  aviso «Repitió: …»). Se va entero. Lo que **no** se va es el resto de la
  revisión: que falte un cuarto y que haya uno inventado siguen siendo errores
  (§7.1).
- **Al aceptar, los repetidos se colapsan.** `_guia_cuadrada_con_el_rail` arma
  un diccionario por nombre de cuarto, así que dos aéreas se vuelven una. Pasa
  a conservar la secuencia tal cual.

Y **el rail se ordena por la primera aparición**: `reordenar` recibe hoy la
lista del guion, que ahora trae repetidos. Un cuarto no puede estar dos veces
en el rail, así que se le pasa la lista sin repetir, en orden de primera
aparición — el mismo criterio que la numeración de las carpetas, para que el
rail y Premiere no puedan contradecirse.

### 4.b El manifest: sin cambio de forma

`guia.orden` ya es una lista de renglones, así que un cuarto repetido cabe sin
tocar el formato. **Un manifest viejo sigue siendo válido**, y uno nuevo con
repeticiones lo lee el plugin de hoy sin enterarse.

### 4.c El plugin: ya estaba listo

`caminoDelClip` numera con `orden.indexOf(cuarto)`, que **devuelve la primera
aparición**. Es exactamente la decisión del §3.2, escrita antes de que la
pregunta existiera. No se toca.

### 4.d El panel

El encabezado fijo trae tres datos y ninguno más:

- **En qué paso vas** — el primero sin palomear.
- **Cuántos llevas** — «4 de 11 pasos montados». Se cuentan PASOS, no cuartos:
  con la aérea tres veces, «4 de 9 cuartos» no querría decir nada.
- **De qué rodaje es** — el nombre del proyecto, que viene en el manifest. Sin
  esto, abrir Premiere tres semanas después no dice si la guía es la del
  proyecto que tienes enfrente.

Abajo, el párrafo y la lista de pasos. Un paso montado se tacha y **esconde su
razón**: ya no hace falta y roba espacio al que sigue. El paso en el que vas se
marca con un filo ámbar. Un cuarto que sale otra vez lleva la marca «otra vez»,
para que no se lea como un error del panel.

Los números del guion son de pasos (`1`, `2`, …) y los de las carpetas llevan
su cero (`01. Aérea`). **Se ven distintos a propósito**: son dos cosas
distintas, y que se parecieran demasiado fue lo que hizo tan fácil confundirlas.

## 5. La palomita: dónde vive

Bruno levantó la restricción de que la pestaña no escriba. Aun así, **el dato
vive en el plugin, no en el proyecto de Premiere**, y el color del bin es su
reflejo:

- **El dueño del dato es un archivo del plugin**, en su carpeta de datos de
  UXP. Siempre funciona, no toca el proyecto y no puede corromperlo.
- **Y el bin del cuarto se pinta de color** cuando todos los pasos de ese
  cuarto están montados. Así el avance se ve **en la ventana de proyecto, sin
  abrir el panel**, que es la mitad del valor.

Un solo dueño y una presentación derivada: el mismo corte que ya existe con
`camara` → color, y por la misma razón. El color se recalcula del archivo cada
vez que se abre el panel, así que no pueden separarse.

**Y aquí hay un choque que se resuelve a propósito y no por descuido.** El repo
tiene escrito que *en Premiere el color dice la cámara*: azul la Sony, ámbar el
dron, morado lo demás. Eso vale para los **clips**, que es donde se decidió y
donde Bruno lo usa para arrastrarle el LUT a toda una cámara de un jalón. Un
**bin** no es un clip y nunca tuvo color, así que su color queda libre para
decir otra cosa: si ya lo montaste.

Para que la vista no mienta, el verde **no entra en la paleta de cámaras** —
Cerulean, Mango y Violet siguen siendo de ellas y no se reusan aquí. Un color
que ya significara una cámara diciendo además «montado» sería justo el error
que este spec vino a cerrar, con otro disfraz.

**Si Premiere no deja pintar un bin, se queda solo la palomita del panel**, se
dice en el panel una vez, y no se inventa otra forma de marcarlo. En este
plugin la documentación de Adobe ya mintió tres veces el mismo día: el método
se busca en el objeto de verdad —como hace `ACCIONES_DE_RENOMBRAR` en
`nombre.js`— y si no está, se sigue sin él. **Comprobarlo necesita Premiere
abierto y es de las cosas que solo Bruno puede hacer.**

## 6. El patrón, reescrito

Dicho por él:

> «En general es primero fachada, áreas sociales, luego habitaciones, luego
> otra aérea tal vez, luego amenidades, luego área general, luego aérea final.»

Y «área general» es **la propiedad de lejos, desde el drone**.

Tres cosas que el documento de hoy no tiene:

1. **Una aérea a media casa**, después de las habitaciones. Hoy solo contempla
   la del principio y la del final.
2. **El cierre son DOS aéreas**: la propiedad completa de lejos, y luego la de
   salida, más larga que todas las de en medio.
3. **La fachada de apertura es aérea.** Él empieza su lista en «fachada» y en
   diez de quince videos la primera toma es aérea: para él la fachada desde el
   aire ya es la fachada.

Y **una corrección**: el documento de hoy dice que las recámaras van juntas y
seguidas, y eso **está bien** — Bruno lo confirmó. Un análisis previo sugirió
lo contrario por un error de lectura: en las fichas las cuatro recámaras de una
casa se llaman todas `recamara`, así que cuatro recámaras distintas parecían
una sola a la que se vuelve.

**Sigue sin llevar cuentas** (§5.1 del spec del patrón). Las de arriba se
hicieron para decidir qué entra y se quedan fuera del documento.

## 7. Los modos de falla

### 7.1 La revisión, con repeticiones permitidas

Sigue vigente lo demás del §5.1 del spec del 14, con igualdad exacta de cadena:

- **Falta un cuarto** → se avisa. Que el guion repita no lo exime de pasar por
  todos: un cuarto que no sale ni una vez sigue siendo material que se te
  olvida al editar.
- **Sobra uno inventado** → se enseña marcado.
- **Repetido** → deja de ser un aviso. Y **no se inventa un límite**: un modelo
  que repita ocho veces la sala se ve a simple vista en la lista, y poner un
  número máximo sería una regla nuestra sobre cómo edita Bruno.

### 7.2 Las palomitas de una guía que ya no es

Si Bruno reimporta con una guía distinta, las palomitas viejas apuntan a pasos
que ya no son los mismos. Lo que se hace: **cada palomita se guarda con el
número de paso Y el nombre del cuarto**, y al abrir se descarta la que no
coincida con el guion de ahora. Sin aviso: no es un error, es que la guía
cambió.

Lo que NO se hace es conservarlas por número de paso a secas — eso daría un
avance falso, que es peor que ninguno.

### 7.3 Lo que ya no se puede dar por hecho

El repo tiene escrito que «un solo orden de cuartos, y lo decide Bruno». Sigue
siendo cierto **para los cuartos**: el rail, la hoja y las carpetas usan uno
solo. Lo que se agrega es que **el guion no es ese orden** — es otra cosa, con
otro nombre y otra forma. Confundirlos otra vez es el bug que este spec existe
para cerrar.

## 8. Lo que NO pierde el spec del 14

- Que la guía se arme en Clipify y viaje congelada en el manifest.
- Que el panel no pida otra guía, ni tenga llave, ni toque la red.
- Que las carpetas lleguen numeradas, y que al importar el cuarto se reconozca
  **sin su número**.
- Que el número no viaje en `categoria_path`.
- Que un manifest sin guía sea válido.
- El aviso de la guía vieja al exportar.

## 9. Lo que NO entra

- **Ordenar los clips dentro de cada paso.** Sigue fuera, como desde el 14.
- **Que el panel edite la guía.** Se lee, se palomea, y ya.
- **Un límite de repeticiones** (§7.1).
- **Numerar las carpetas con todos sus pasos** (`01·11. Aérea`) — se ofreció y
  se descartó: se lee mal y se ensucia en cuanto el guion cambia.
- **Que las palomitas viajen en el proyecto de Premiere.** Viven en el plugin
  (§5); lo que viaja es el color del bin, que se recalcula.

## 10. Cómo se comprueba

**Con pruebas de Python**, en `tests/`:

- Que un guion con la aérea tres veces sobreviva entero: que se lea, que se
  acepte, y que llegue al manifest con sus tres pasos.
- Que el rail quede con la aérea **una vez**, en el lugar de su primera
  aparición.
- Que un cuarto repetido **no** genere aviso, y que uno faltante y uno
  inventado **sí**.
- Que el prompt ya no le prohíba repetir.

**Con pruebas de `node`**, en `uxp-plugin/pruebas/`:

- Que `caminoDelClip` le dé a la aérea el número de su **primera** aparición
  aunque salga tres veces.
- Que la palomita de un paso que ya no coincide con el guion se descarte.

**Verificación visual real** — si no se miró la imagen, no se afirma:

- El panel con un guion que repite, con el paso actual marcado y dos pasos
  palomeados.
- El mismo panel con todo montado.

**Y lo que necesita a Bruno:** si Premiere deja pintar el bin de un color
(§5), y si el guion que sale se parece a cómo monta de verdad.
