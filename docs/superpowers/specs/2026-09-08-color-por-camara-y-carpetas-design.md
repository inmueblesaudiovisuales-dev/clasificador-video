# Un color por cámara y una estructura de carpetas en Premiere — diseño

*(Spec. Fecha: 2026-09-08. Sale de una sesión con Bruno; cada decisión de
abajo es suya y está anotada con su razón.)*

## 1. Lo que pidió

> «Quiero que cada cámara sea su propio color en Premiere. Y que me haga
> carpetas como 01. Secuencia, 02. Clip (todo adentro de este),
> 03. AE composition, 04. Musica, 05. Voz IA, 06. Assets adicionales.»

Son dos cosas y llegan juntas por una razón: las dos son sobre **cómo se ve
el panel de proyecto cuando abre Premiere**, que hoy es lo último que la app
toca antes de soltarle el trabajo.

## 2. El choque que hay que resolver primero

En Premiere **un item tiene una sola etiqueta de color**. Hoy esa etiqueta
dice el ESTADO del clip (`label.js`):

| Estado | Color de hoy |
|---|---|
| pick | `FOREST` (verde) |
| reject | `ROSE` (rosa) |
| destacado | `MANGO` (dorado) |

Si el color pasa a decir la cámara, el estado se queda sin color. **Y casi no
se pierde nada**, porque el estado ya viaja por otra vía: las subcarpetas
`Picks` / `Rejects` / `Sin marcar` que arma `con_subcarpeta_de_estado`. Un
pick sigue siendo distinguible de un reject sin mirar un solo color.

La excepción es el **destacado**: hoy se distingue *únicamente* por el dorado
—va en la misma carpeta `Picks` que los demás picks, decisión del 2026-08-22—
así que quitarle el color lo borra de Premiere por completo. Eso no puede
pasar: la estrella perdiéndose en la frontera es exactamente lo que este
plugin existe para evitar (ver el comentario al tope de `label.js`).

**Decisión de Bruno:** el destacado llega con **`★ ` al inicio del nombre**
del clip en el panel de proyecto. Se ve sin abrir nada, ordena y busca
fácil, y no le quita el color de cámara a nadie.

Se le ofrecieron otras tres salidas y las descartó: carpeta propia dentro de
`Picks` (parte en dos lo que uno quiere junto), que el dorado le gane al
color de cámara (dos significados para el mismo canal), y no marcarlo (pierde
información que hoy sí llega).

## 3. La cámara

### 3.1 Qué es y dónde vive

**Una propiedad del bin.** El bin ya es «una tanda de material que entró
junta — en la práctica, una cámara o una tarjeta»
(`2026-08-09-bins-por-camara-design.md` §3), así que no hay concepto nuevo
que inventar: se le agrega un campo.

Tres valores: **`sony`**, **`dji`**, **`otra`**.

### 3.2 La app la adivina, y Bruno la corrige

Bruno lo dijo así:

> «Preferiría que sepa desde antes los patrones de sony y de DJI. Los de DJI
> por lo general tienen el nombre DJI, los que no por lo general serán
> sony.»

La regla, entonces:

- Si el nombre del archivo trae **`DJI`** → `dji`.
- Si no → `sony`.
- `otra` no se adivina nunca. Solo se pone a mano.

Se decide **por bin, no por clip**, mirando sus archivos: si la mayoría trae
`DJI`, el bin es del dron. Un bin mezclado toma la mayoría y Bruno lo corrige
si le atinó mal — que es el punto siguiente.

**Y siempre se puede corregir.** En el menú de clic derecho del encabezado
del bin entra un renglón `Cámara ▸ Sony · DJI · Otra`, con palomita en la que
está puesta. Es el mismo lugar donde ya viven las cosas que aplican a una
cámara entera (proxies, renombrar, quitar del proyecto), así que no hay
gesto nuevo que aprender.

**Por qué adivinar y no preguntar:** son dos cámaras y un patrón de nombre
que no falla en el material real de Bruno. Preguntar en cada importación
sería un paso más en el gesto que más se repite, para acertar lo que ya se
sabía.

### 3.3 Los colores

| Cámara | Color en Premiere |
|---|---|
| Sony | azul (`CERULEAN`) |
| DJI | amarillo (`MANGO`) |
| Otra | morado (`VIOLET`) |

Los eligió Bruno: azul y amarillo son los dos más separados entre sí del
panel, y esa distancia es todo el punto — el color existe para que de un
vistazo sepas de qué cámara salió el clip.

`MANGO` se recicla del destacado, que ya no lo usa. `FOREST` y `ROSE` quedan
libres.

**La guarda de `label.js` se queda y se aplica igual**: si la versión de
Premiere no conoce un nombre de color, no se toca el clip y se dice en el
panel con la lista de los que sí existen. Ya está escrita y probada; lo
único que cambia es la tabla que consulta.

### 3.4 El puntito del encabezado cambia de significado

Hoy la marquita de cada bin (`_BinHeader.cam_mark`) se pinta con el color de
su POSICIÓN, y su propio comentario en el código dice por qué:

> «el mockup ponía `▲` al dron y `■` a la Sony porque sabía que era cada uno,
> **y la app no lo sabe** — lee una carpeta, no un modelo de cámara.»

Ahora sí lo sabe. **La marquita pasa a pintarse con el color de la cámara**,
el mismo que va a tener el clip en Premiere.

El costo, dicho de frente: dos bins de Sony —dos tarjetas del mismo día— se
ven del mismo azul en vez de distinguirse. Se acepta porque es **honesto**:
en Premiere también van a salir del mismo azul, y una app que muestra una
diferencia que su destino no tiene es una app que miente en chiquito. El
nombre del bin sigue siendo lo que distingue una tarjeta de otra.

### 3.5 Dónde se guarda

En el autosave, junto al bin, que es donde ya vive todo lo del bin:

```json
"bins": [
  {"nombre": "Dron", "origen": "/…", "clips": [130, 131], "camara": "dji"}
]
```

Una sesión vieja sin la llave `camara` **no se rompe**: al cargar, el bin que
no la traiga se la calcula con la regla de §3.2. Mismo criterio blindado que
`BinTree.from_list` ya usa para todo lo demás.

Y viaja al plugin como un campo más del clip en el manifiesto:

```json
{"ruta": "…", "flag": "pick", "camara": "sony", …}
```

**El manifiesto manda la cámara, no el color.** El color es presentación y
esa traducción vive en `label.js`, exactamente como hoy `flag` viaja como
`"pick"` y no como `"FOREST"`. Un solo lugar donde está escrito qué color es
cada cosa.

## 4. Las carpetas

### 4.1 El árbol

```
01. Secuencia            (vacía)
02. Clip
   ├ Cocina
   │   ├ Picks           ← los destacados van aquí, con ★ en el nombre
   │   ├ Rejects
   │   └ Sin marcar
   ├ Recamara 1
   │   └ …
   └ Sin clasificar
03. AE composition       (vacía)
04. Musica               (vacía)
05. Voz                  (vacía)
06. Graficos             (vacía)
07. Assets adicionales   (vacía)
```

Las siete se crean **siempre**, aunque cinco queden vacías: son el esqueleto
del proyecto de Bruno y existen para que él meta cosas ahí, no para que la
app las llene. Los nombres van tal cual los escribió, con su número y su
punto — es su convención y Premiere ordena por abecedario, así que el número
es lo que sostiene el orden.

**Dos vienen de revisar la lista con él el mismo día**, y las dos son sobre
un nombre que iba a estorbar más tarde:

- **`06. Graficos`** es nueva. Sin ella, los títulos, los lower thirds y el
  logo del cliente caían revueltos en `Assets adicionales` con todo lo demás.
  Va antes del cajón de sastre a propósito: un cajón de sastre que no está al
  final deja de serlo.
- **`05. Voz`**, no `05. Voz IA`. El nombre de hoy describe de dónde salió la
  voz, no qué es — y el día que Bruno grabe una locución de verdad, o que el
  cliente mande la suya, el archivo estaría en una carpeta que dice una
  mentira. `Voz` aguanta las dos.

Se le ofrecieron otras dos y las descartó: partir `04. Musica` en música y
SFX, y sacar los `Rejects` de cada cuarto a un solo cajón al final.

**La cámara no hace carpeta.** Bruno: «lo importante de separar las cámaras
es para el color». Un cuarto grabado con dos cámaras se queda en un solo
lugar, y los clips se distinguen por su color adentro.

### 4.2 Quién sabe el árbol

**El plugin**, en un solo lugar. La app sigue mandando `categoria_path` como
hoy —`["Cocina", "Picks"]`— y el plugin le antepone `02. Clip` antes de
pasárselo a `resolveBinChain`, que ya sabe crear y reusar bins anidados y lo
tiene probado dentro de Premiere de verdad.

Se hace así y no metiendo `"02. Clip"` en el `categoria_path` de la app por
la misma razón que `con_subcarpeta_de_estado` no vive en la sesión: **la
estructura del proyecto de Premiere es cosa de Premiere.** Si la app la
escribiera, el nombre de esa carpeta quedaría repartido en dos repos y se
desincronizarían en el primer cambio de opinión.

Las cinco carpetas sin clips se crean al empezar a procesar el manifiesto,
con la misma `resolveBinChain`: **si ya existen, se reusan.** Un proyecto de
Bruno que ya tenga su `04. Musica` con música adentro no recibe una segunda.

### 4.3 Lo que le pasa a un proyecto ya importado

Los clips que ya estaban en el proyecto **se mueven** a su lugar nuevo dentro
de `02. Clip`. No se duplican —`importOrReuseClip` los encuentra por ruta en
disco y los mueve en vez de reimportar—, pero sí se mueven.

Se avisa al empezar, no después: si el proyecto abierto ya tiene clips de una
importación anterior fuera de `02. Clip`, el panel lo dice con la cuenta
antes de tocar nada.

## 5. El ★ del destacado

Lo pone el plugin al importar, sobre el nombre del item en el panel de
proyecto. **No toca el archivo en disco** — es el nombre dentro de Premiere.

Dos reglas:

- **Es idempotente.** Si el nombre ya empieza con `★ `, no se le pone otro.
  Volver a correr la misma clasificación es un caso normal —es como se
  corrige un error— y `★ ★ ★ C0001.MP4` sería basura acumulada.
- **Solo se agrega, nunca se quita.** Si un clip dejó de ser destacado, su
  `★` se queda. Quitarlo significaría que el plugin renombra clips que Bruno
  pudo haber renombrado a mano, y ese es un daño peor que un ★ de más. Mismo
  criterio que `applyFlagLabel` con `flag: "none"`, que a propósito no limpia
  una etiqueta previa.

### 5.1 Riesgo abierto, y qué se hace si no se puede

**No está comprobado que la API deje renombrar un clip.** En este plugin la
documentación de Adobe ya mintió tres veces —ver el comentario al tope de
`importClip.js` y `RESULTADO-2026-09-08-el-lut-por-la-via-del-blob.md`— así
que esto se verifica **contra Premiere de verdad antes de escribir el código
que lo use**, enumerando el prototipo real del objeto en vez de creerle a la
referencia.

**Si no se puede:** el destacado se va a una subcarpeta `Destacados` dentro
de `Picks` de su cuarto. Es la segunda opción que Bruno evaluó y descartó por
preferencia, no por imposible, así que sirve de plan B sin volver a
preguntar. Lo que **no** se hace es entregar el destacado sin ninguna marca.

## 6. Lo que NO entra

- **El LUT por cámara.** Cerrado el mismo día, contra Premiere real: el
  parámetro que guarda la ruta del `.cube` tumba Premiere al leerlo y
  rechaza lo que se le escriba. Ver
  `archive/RESULTADO-2026-09-08-el-lut-por-la-via-del-blob.md`. El LUT se
  sigue poniendo a mano — y el color por cámara lo hace barato: seleccionar
  todos los amarillos y arrastrarles el preset es un gesto.
- **Que el bin viaje a Premiere como carpeta.** Sigue fuera, ahora por
  decisión explícita y no por pendiente: la cámara viaja como color.
- **Elegir los colores en la app.** Bruno los fijó. Si algún día quiere
  cambiarlos, es una tabla de tres renglones en `label.js`.
- **Más cámaras que tres.** `otra` es la válvula. Un cuarto valor se agrega
  el día que exista una cuarta cámara.

## 7. Cómo se comprueba

**Con tests**, lo que es lógica:

- La regla de §3.2 sobre nombres reales: `DJI_20260817182345_0081_D.MP4` da
  `dji`, `20260817_PIB0016.MP4` da `sony`, un bin mezclado toma la mayoría,
  y `otra` nunca sale de adivinar.
- Una sesión sin la llave `camara` se carga con la cámara calculada, y una
  con la llave respeta lo que Bruno puso a mano — **este es el que importa**:
  es el punto exacto donde un descuido le borra una corrección.
- La cámara viaja al manifiesto y sobrevive a guardar y restaurar.
- El `★` es idempotente: dos pasadas dan un solo `★`.

**Contra Premiere de verdad**, lo que no se puede probar de otra forma —y
antes de escribir el código que dependa de ello:

1. Que se pueda renombrar un clip (§5.1).
2. Que `CERULEAN` y `VIOLET` existan en
   `Constants.ProjectItemColorLabel` de su versión. `MANGO` ya está
   confirmado (índice 7, el 2026-08-10).

Las dos en **una sola corrida**, anotando a disco antes de cada paso: cada
corrida cuesta reiniciar Premiere, y la sesión del LUT de hoy dejó esa regla
pagada con dos caídas.

**Verificación visual real**, según `CLAUDE.md`: `grab()` del encabezado de
dos bins con cámaras distintas, para ver los colores nuevos con los ojos. Si
no se miró la imagen, no se afirma.


---

## 8. Enmienda de la misma tarde: el reject estrena marca y pierde carpeta

**Esta sección corrige el §2 y el §4.1. Donde se contradigan, manda esta.**

Bruno vio funcionando el `★` de los destacados y pidió lo mismo para el otro
extremo:

> «Podemos poner un icono para rejects? Así como los favoritos tienen
> estrella, podemos ponerle uno a rejects?»

Y enseguida, la parte que cambia el árbol:

> «Quiero que esta marca reemplace la carpeta de rejects.»

### 8.1 Qué cambia

- El reject llega con **`✕ ` al inicio del nombre** en el panel de proyecto,
  igual que el destacado con su `★`.
- **La subcarpeta `Rejects` desaparece.** Los rejects se quedan **sueltos en
  la carpeta de su cuarto**, junto a las subcarpetas `Picks` y `Sin marcar`:

```
02. Clip
  └── Cocina
        ├── Picks
        ├── Sin marcar
        ├── ✕ C0004.MP4
        └── ✕ C0009.MP4
```

Bruno escogió «sueltos en su cuarto» sobre las otras dos que se le pusieron
enfrente (meterlos con los «Sin marcar», o quitar todas las subcarpetas y
dejar el cuarto plano).

**Costo dicho de frente antes de decidir:** la carpeta `Rejects` dejaba
ignorar de golpe todo lo malo; sueltos, los malos aparecen a la vista y hay
que distinguirlos uno por uno. Ese es justamente el punto — la carpeta los
escondía, y lo que uno quiere al abrir un cuarto es ver qué grabó, con lo
malo tachado.

### 8.2 La regla del `★` cambia: ahora las marcas se reemplazan

El §5 decía que el `★` **solo se agrega y nunca se quita**, por no renombrar
clips que Bruno pudo haber renombrado a mano.

**Con dos marcas esa regla se vuelve el bug.** Un clip que era reject y pasa
a destacado terminaría llamándose `★ ✕ C0001.MP4` — diciendo las dos cosas
contrarias a la vez.

La regla nueva: **se quita la marca propia del inicio y se pone la que toca.**
Y solo la propia — un `✕` que Bruno haya escrito a media frase, o al inicio
sin el espacio que lleva la nuestra, no se toca. Un clip que deja de ser
reject y de ser destacado se queda sin marca.

Lo demás del §5 se sostiene: sigue siendo idempotente, sigue sin tocar el
archivo en disco, y si Premiere no dejara renombrar se dice en el panel en
vez de fallar callado.

### 8.3 Cómo se comprueba

Los casos viven en el arnés del plugin (`autocheck-tests.js`), que es donde
puede correr esta lógica, y son once: las dos marcas puestas sobre un nombre
limpio, un pick y un «sin marcar» sin marca, la segunda pasada que no
acumula, los tres cambios de estado que reemplazan la marca, la limpieza de
un `★ ✕` heredado, y los dos nombres con `✕` que son de Bruno y no se tocan.

Del lado de la app, un test en `test_manifest.py` fija que un reject se
queda con el camino de su cuarto pelado — que es lo que lo deja suelto.


---

## 9. Enmienda final: el cuarto queda plano y el pick estrena marca

**Esta sección corrige el §2, el §4.1 y el §8. Donde se contradigan, manda
esta.** Es el tercer paso del mismo día sobre la misma pregunta, y los tres
se leen mejor juntos que por separado.

> «Mejor quita picks también. Solo deja todo dentro de cada cuarto.»

### 9.1 Cómo queda

```
02. Clip
  └── Cocina
        ├── ★ C0002.MP4      destacado
        ├── ✓ C0001.MP4      pick
        ├── ✕ C0004.MP4      reject
        └── C0007.MP4        sin marca: no se ha visto
```

Se van **las tres** subcarpetas de estado. `con_subcarpeta_de_estado` se
borró entera, con sus tests: era la última pieza de esa idea.

### 9.2 El pick estrena `✓`, y no es un adorno

Quitar `Picks` dejaba al pick **indistinguible de un clip sin ver** — era la
carpeta la que lo decía y no había marca que la reemplazara. Eso es perder un
dato en la frontera, que es exactamente lo que este plugin existe para
evitar, así que se le señaló a Bruno antes de tocar nada y él escogió darle
marca propia.

Consecuencia que hay que tener presente: **un clip sin marca ya no significa
«pick», significa «no lo has visto»**. Es un cambio de significado del
estado vacío, no solo una carpeta menos.

### 9.3 Por qué los tres pasos son la misma decisión

| Paso | Qué pasó | Qué sobró |
|---|---|---|
| 1 | El color pasó a decir la cámara | la etiqueta dorada del destacado → nace `★` |
| 2 | El reject estrenó `✕` | la carpeta `Rejects` |
| 3 | Se fueron `Picks` y `Sin marcar` | — y el pick estrenó `✓` para no perderse |

El fondo, en una línea: **una carpeta esconde el clip y una marca lo
enseña.** Lo que uno quiere al abrir un cuarto es ver qué grabó, con lo bueno
y lo malo señalado — no elegir entre tres puertas para averiguarlo.

Y es la tercera vez que este repo llega a la misma conclusión: la primera fue
el 2026-08-22, cuando los destacados perdieron su carpeta propia y se
quedaron con la etiqueta dorada.

### 9.4 Qué se comprueba

- En el arnés del plugin: doce casos de la marca, incluidos los tres cambios
  de estado que la reemplazan, el `none` que la quita, y los dos nombres con
  `✕` de Bruno que no se tocan.
- En `test_manifest.py`: que el camino de un clip sea su cuarto y nada más,
  con cualquier estado.
- En `test_main_window.py`: que exportar no le toque nada a los clips vivos
  —ni el camino ni la cámara—, ni siquiera exportando dos veces.
