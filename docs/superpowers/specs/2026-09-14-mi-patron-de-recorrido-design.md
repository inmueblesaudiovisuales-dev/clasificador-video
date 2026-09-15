# Mi patrón de recorrido — diseño

*(Spec. Fecha: 2026-09-14. Sale del brainstorm con Bruno del mismo día.
Modifica la pestaña «Orden sugerido» que se acababa de construir ese mismo
día — ver `2026-09-14-orden-sugerido-de-cuartos-design.md`, que sigue
vigente en todo lo que este documento no toca.)*

## 1. De dónde salió

La pestaña «Orden sugerido» ya existe y funciona, pero sugiere **el orden de
manual**: le manda a la IA los nombres de los cuartos de Bruno y ella acomoda
con criterio general de recorrido de propiedades. Es exactamente lo que se
diseñó, y está bien — pero no es lo que Bruno hace.

Lo que pidió: **que sugiera el suyo**, sacado de los videos que ya entregó
este año.

## 2. Lo que se verificó ANTES de diseñar

Bruno puso dos cosas sobre la mesa con la instrucción explícita de no darlas
por hechas. Las dos se comprobaron contra la documentación de Gemini, y las
dos cambiaron el diseño.

### 2.a Bajarle los fps NO ahorra nada

**Bruno tenía razón y su sospecha era la correcta.** Gemini muestrea el video
a **un cuadro por segundo**, sin importar si el archivo va a 24, 30 o 60. Lo
que se cobra son los cuadros muestreados (258 tokens cada uno, o 66 en
resolución baja) más el audio (32 tokens por segundo). O sea: **lo que mueve
el costo es la DURACIÓN**, no los fps ni la resolución del archivo.

La resolución del archivo tampoco entra: Gemini reescala cada cuadro a un
tamaño fijo suyo. Lo que sí existe es un interruptor **del lado de Gemini**
(`media_resolution`, alta o baja) que cambia los tokens por cuadro — y eso se
decide en la llamada, no en el ffmpeg.

**Consecuencia de diseño:** se sigue comprimiendo, pero **por otra razón** —
para no mover 20 GB por la red ni llenarle el disco. Y como la resolución no
le cuesta nada al análisis, se baja a **lado corto 480** en vez de 720: la
compresión termina antes y el análisis sale igual.

### 2.b El costo es tan bajo que deja de ser una restricción

Una hora y media de video (los ~33 entregables de 2026) son unos **540 mil
tokens**. A los precios de Gemini Flash de hoy —$0.75 por millón, con el
audio aparte— eso sale en **menos de un dólar por los 33 videos**.

Esto **elimina una pregunta entera del proyecto**. Bruno preguntó si había
que analizar todo o alcanzaba con una muestra, y si no era muy costoso mirar
fotogramas. Con este número: se analizan **todos**, completos, y no hay que
escoger.

*(En la plática se dijo «unos 20 centavos», calculado sobre el precio del
2.5 Flash. Con el modelo Flash de hoy son más bien 40–60. Sigue siendo menos
de un dólar y no cambia ninguna decisión.)*

### 2.c El disco tampoco es problema, porque no hay que bajar nada

Se contaron los entregables en el Drive de Bruno: **24 proyectos de mayo a
septiembre** en el acomodo actual (`2026 / 08. Agosto / IAV-2608.17-A —
Cliente / Entregables / VIDEO / archivo.mp4`), más **11 de febrero a abril**
en el acomodo viejo de antes del 26 de abril. **Total: 35**, no 33 como se
dijo al principio de la plática.

De esos 35, **solo 28 tienen archivo**: las otras siete carpetas `Entregables`
están creadas y vacías —se arman al abrir el proyecto y se llenan después, y
los cuatro de septiembre siguen en proceso—. Y de los 28, **Bruno dejó 15**
(§4.b.2). **8.8 GB**, que es lo que de verdad hay que comprimir.

Y Bruno los tiene **todos en un disco suyo**. Entonces no se baja nada: Drive
solo dice *cuál* archivo de cada proyecto fue el entregado, y los bytes salen
del disco.

## 3. Las decisiones, una por una

Cada renglón es una respuesta explícita de Bruno, en el orden en que las dio.

1. **La versión entregada cambia de proyecto en proyecto** — en unos entregó
   el largo horizontal y en otros el reel vertical. No hay regla que sacarle
   al nombre del archivo.
2. **Un solo patrón.** Se acordó primero que fueran dos —uno para el largo y
   uno para el reel— y se revirtió al ver la lista real. Ver el §3.bis.
3. **Los videos salen del disco de Bruno**, no de Drive.
4. **El disco NO está acomodado igual que Drive**, pero **los nombres son los
   mismos**. De ahí sale cómo se casan (§4.b).
5. **El patrón entra a la pestaña como texto Y como lista.** Palabras suyas:
   «un poco de los dos, el texto pero que haya una lista».
6. **Manda la IA, no la lista** — pero con el patrón enfrente, y **avisando
   cuando se sale de él**. Bruno lo confirmó dos veces, la segunda ya sabiendo
   que no quería justificaciones: «sí quiero que me lo diga».
7. **Se va la pregunta «¿Para quién es el video?»** de la pestaña. Razón suya:
   «todo es para redes». Era un clic para decir lo de siempre.
8. **«¿Qué quieres lucir?» pasa al frente** y es la pregunta principal. «Sí es
   importante poder describirle qué quiero lucir de cada propiedad.»
9. **«¿Qué tipo de propiedad es?» se queda.** Un terreno y un departamento no
   se recorren igual.
10. **Gemini determina el tipo de propiedad** de cada video entregado, para
    poder comparar contra esa misma pregunta de la pestaña.
11. **Un patrón general con excepciones por tipo**, no ocho patrones. Con 33
    videos partidos en dos formatos y cuatro tipos salen montones de cuatro, y
    algunos de uno. Un patrón sacado de un video es una anécdota.
12. **El documento NO lleva cuentas ni se justifica.** Es el §5, y es el
    cambio más importante de todos los que pidió.
13. **Bruno poda la lista antes de que se comprima nada**, en lista plana y con
    un enlace a Drive por renglón. Se descartó que el programa señalara
    sospechosos. Ver el §4.b.1.

## 3.bis Un patrón y no dos, y por qué se revirtió

La decisión de partir en dos venía de un argumento que sigue en pie: **un reel
de 30 segundos y un recorrido de 3 minutos no pueden compartir patrón** — en
uno caben cinco cuartos y en el otro quince, y revolverlos da un promedio que
no describe a ninguno.

Lo que estaba mal era **por dónde se partía**. Al leer la lista de entregables,
los nombres de archivo decían `16x9` y `9x16`, y se dio por hecho que ésa era
la línea. **No lo es.** Bruno, viendo la lista: «el patrón de los horizontales
es igual que verticales. Solo grabado horizontal».

La línea verdadera es la **duración**, no la forma del cuadro. Y ahí la lista
decide sola: de los 15 videos que Bruno dejó, **uno solo es reel**. Uno no es
un patrón.

Entonces: **un patrón, de los 14 largos.** El reel se analiza igual —su ficha
entra al montón— pero no genera un patrón propio ni manda sobre nada. Si algún
año hay reels suficientes, la partición vuelve, y vuelve por duración.

Es el mismo error que el repo ya cometió antes y tiene escrito: **dos cosas que
se parecen en el nombre no son la misma cosa.** Aquí `9x16` se parecía a «reel»
lo suficiente para que nadie lo revisara.

## 4. Las tres piezas

### 4.a Encontrar

Un programa lee el Drive de Bruno y arma la lista de entregables de 2026:
proyecto, archivo, y si es largo u horizontal o reel vertical.

Lo que se descarta **solo**, sin que Bruno marque nada:

- **El material en bruto.** Los cientos de `DJI_…` viven fuera de las carpetas
  `Entregables`. La estructura los separa sin ayuda.
- **Las versiones «sin voz» y «sin narración».** Son **el mismo corte** sin la
  locución encima, y para lo que se busca —orden, duración, apertura, cierre—
  son el mismo video. Medido: `IAV-2607.17-A-v2` pesa 1,033,744,008 bytes y
  `IAV-2607.17-A sin voz` pesa 1,034,575,244. La diferencia es la pista de
  audio, nada más. Mismo caso en el `IAV-2607.07-A`.

Los ~9 proyectos de enero a abril viven en el acomodo viejo y hay que
buscarlos aparte. **No se inventan reglas para adivinarlos**: si el programa
no está seguro de cuál archivo de un proyecto fue el entregado, lo pone en la
lista **marcado como dudoso** y Bruno decide.

### 4.b Casar con el disco

Bruno conecta el disco y apunta a una carpeta. El programa busca **cada
archivo por su nombre exacto**, recursivamente, esté donde esté. El nombre es
el único dato que sobrevive al cambio de acomodo, y por eso es el que se usa.

**Y enseña la lista antes de tocar nada:** «encontré 30 de 35; estos cinco no
aparecen». Los que falten se bajan de Drive, y **solo ésos**.

Esto es la regla que ya está escrita en `CLAUDE.md` con otras palabras: *la
app propone, nunca adivina en silencio*. Un programa que empareja mal un
archivo y no lo dice mete el video de otra propiedad al patrón, y eso no se
nota nunca.

#### 4.b.1 Bruno poda la lista, y ese paso no es opcional

Salió de enseñarle la lista de 35 en la plática, y **cambió el diseño en el
acto**. Hay tres razones para que un renglón no entre, y **ninguna se puede
adivinar desde el archivo**:

1. **Era una prueba.** Palabras de Bruno: «muchos de esos clientes no existen
   y eran solo pruebas». Se ven en la lista —`Chulo Perez`, `dani`, `danis2`—
   pero el nombre no es prueba de nada: un cliente puede llamarse así.
2. **Está repetido porque se reagendó el rodaje.** Dos carpetas, dos fechas,
   **una sola propiedad**. Si entran las dos, esa propiedad pesa el doble en
   el patrón y nadie lo nota. Bruno lo trajo él: «hay unos repetidos que
   reagendamos».
3. **Es la versión que no era.** Un proyecto puede tener 16x9 y 9x16 y haberse
   entregado uno solo. Corregido en vivo sobre la lista: el de **Alberto
   Valles** es solo el `16X9`, y el de **Manuel Abraham 2606.07** es solo
   `IAV-2606.07-A.mp4` —no el `2606-07 v17.mp4`—.

Entonces: **lista plana, y Bruno tacha.** Se le ofreció que el programa
señalara a los sospechosos —mismo cliente con fechas cercanas— y **lo
descartó**: conoce sus proyectos mejor que cualquier regla que le pongamos, y
una marca equivocada le haría desconfiar de las buenas.

**Cada renglón lleva su enlace a la carpeta de Drive.** Es lo que pidió, y es
lo que hace que el paso funcione de verdad: sin abrir el video no se distingue
un reagendado de dos propiedades del mismo cliente. El dato ya viene en la
respuesta de Drive (`viewUrl`), así que no cuesta nada.

**Y lo tachado se recuerda.** El año que entra la herramienta se corre otra vez
sobre una lista más larga, y volverle a preguntar por los mismos 35 renglones
es hacerle repetir un trabajo que ya hizo.

#### 4.b.2 El resultado de la primera poda

Se corrió a mano el 2026-09-14, sobre los 28 con archivo. Bruno los marcó
todos. **Quedaron 15, 8.8 GB.**

Lo que dejó fuera y por qué importa que quedara escrito:

- **De Mireya Gómez dejó el REEL y tiró el largo.** Es el caso que enseña que
  «el entregable» no se puede deducir del tamaño ni del nombre: el archivo de
  1 GB se fue y el de 244 MB se quedó.
- **Las dos `SECUENCIA`**, que no traían código de proyecto.
- **Los dos de `2605.20`** («completo» y «corto»), los dos de `2602.18`
  (normal y narrado), `2602.14`, `2603.29`, `2603.05`.
- **Los verticales de `2604.17` y `2603.18-1`**, dejando el 16x9 de cada uno.
- **`IAV-2606.07-A` de Manuel Abraham**, confirmado aparte: antes había dicho
  que de ese proyecto el bueno era justo ése, y al ver la lista lo dejó fuera.
  Se le preguntó y contestó «fuera».

**Y lo que NO se puede deducir todavía:** de 5 de los 15, el nombre no dice si
son horizontales o verticales. Eso sale de `ffprobe` cuando el disco esté
conectado, no de adivinar. Después del §3.bis ya no cambia ninguna decisión,
pero el dato sí entra a la ficha de cada video.

### 4.c Aligerar

Cada video pasa por ffmpeg con `h264_videotoolbox`, **lado corto 480**, audio
conservado. Un entregable de 1 GB queda en unos 15 MB.

- **El audio se queda a propósito.** La narración de Bruno dice «esta es la
  cocina», y eso identifica los cuartos mucho mejor que el puro pixel. Cuesta
  32 tokens por segundo, que a estos precios es nada.
- **`-map 0:v:0` va de todos modos**, aunque estos archivos son exports de
  Premiere con una sola pista. Es la trampa ya medida y documentada de los
  MP4 del dron —una miniatura incrustada como segunda pista de video, que sin
  el `-map` es lo que ffmpeg transcodifica, y sale un archivo de 406 px—. Aquí
  no aplica, cuesta cero escribirlo, y el día que alguien le meta un archivo
  del dron no se rompe.
- **Tarda.** A la velocidad medida de `proxy_gen` es del orden de **dos o tres
  horas de máquina** para hora y media de video. Desatendidas.

**Se reusa lo que ya existe.** `src/clasificador_video/proxy_gen.py` ya arma
este comando y ya está medido (285 MB → 17 MB). Lo que cambia es el lado corto
y el destino, no el camino.

### 4.d Analizar

Cada video va a Gemini con **una sola pregunta**, y la respuesta se pide en
JSON con forma fija:

- la lista de cuartos en el orden en que aparecen, con el segundo en que
  empieza cada uno;
- qué tipo de propiedad es (casa, departamento, terreno, local);
- con qué abre y con qué cierra.

Una ficha por video. Nada más.

### 4.e Sacar el patrón

**Con las 33 fichas ya no hace falta IA para lo de fondo: son cuentas.** En
qué lugar cae cada cuarto, cuántos segundos le toca, qué va al principio y qué
al final, y qué cambia entre tipos de propiedad.

La IA vuelve a entrar **solo para redactar** el documento del §5 a partir de
esas cuentas — porque lo que Bruno pidió es prosa natural, y eso no lo escribe
una tabla.

## 5. El documento

Es lo que Bruno lee, y es lo que el plugin carga adentro. Dos partes:

**La descripción**, escrita como se lo contarías a alguien que va a editar por
ti:

> Abres por fuera, con una aérea de la fachada, y entras por la puerta
> principal. La cocina va temprano. Las recámaras van juntas y van rápido.
> Cierras por donde se disfruta la casa: la alberca, la terraza, el jardín —
> y si no hay, sales por el aire.

**La lista**, explícita:

> **Tu orden:** fachada aérea → entrada → sala → comedor → cocina → recámaras
> → baños → patio → alberca → aérea de salida

Uno solo (§3.bis), con las excepciones por tipo de propiedad **solo donde hubo
material suficiente**.

### 5.1 Lo que el documento NO lleva, y por qué

**No lleva cuentas.** Nada de «(28 videos)», nada de «la cocina cae en el
primer tercio en el 73% de los casos». Se propuso así en el brainstorm —con el
argumento de que saber de cuántos videos salió un renglón te dice cuánto
creerle— y **Bruno lo rechazó**: «no me gusta que me diga todo eso de 28
videos… me gustaría que fuera algo más natural sin que se justifique».

Tiene razón y el argumento se sostiene solo: **el documento no es un reporte
que tenga que convencer a nadie.** Bruno ya sabe cómo edita. Lo que necesita
es que esté escrito para que una máquina lo pueda leer, no que le demuestren
su propio trabajo con estadística.

El dato de cuántos videos respaldan cada cosa **sí se calcula** —hace falta
para decidir qué entra y qué se descarta por flaco— pero se queda del lado de
adentro, en las fichas. No se imprime.

**Y el patrón es base, no regla.** La instrucción que viaja con él: *así
trabaja Bruno, úsalo de punto de partida, pero lo que manda es que el video
quede bien.* Palabras suyas: «que use el patrón como base pero no como regla,
que siempre piense en el mejor resultado de videos».

### 5.2 El documento es de Bruno y lo puede corregir

Se escribe en Markdown, en `docs/patron-de-recorrido/`, y **Bruno lo edita a
mano** cuando algo no le cuadre. Un paso chiquito lo convierte en el archivo
que el plugin carga.

**Uno solo manda: el Markdown.** El archivo del plugin se genera de él y nunca
se edita a mano. Dos copias del mismo dato que se editan por separado se
desincronizan en el primer cambio de opinión — es el mismo criterio por el que
la estructura de carpetas vive solo en `estructura.js` y por el que el rail y
la hoja comparten un único orden de cuartos.

## 6. Lo que cambia en la pestaña

Cuatro cambios, y nada más:

1. **Se va «¿Para quién es el video?»** con sus cuatro chips (§3.7).
2. **«¿Qué quieres lucir?» pasa al frente**, con su caja grande. Es la pregunta
   principal. «¿Qué tipo de propiedad es?» se queda debajo con sus chips.
3. **El prompt lleva el patrón adentro** —descripción y lista— con la
   instrucción del §5.1: base, no regla.
4. **Cuando se sale del orden de Bruno, lo marca.** Discreto y en esa misma
   línea: *«la alberca la subí porque dijiste que es lo que hay que lucir»*.
   No es una justificación estadística; es avisar que se movió, para que no se
   le pase.

**El matiz que separa el punto 4 del §5.1**, porque parecen contrarios y no lo
son: lo que Bruno no quiere es que el sistema **le explique su propio patrón
con números**. Lo que sí quiere es que le avise **cuando se aparta de él**. Lo
primero es ruido —él ya sabe cómo edita—; lo segundo es información que solo
tiene la IA. Se preguntó dos veces, con la segunda redactada ya sabiendo que
no quería justificaciones, y contestó que sí las dos.

## 7. Reglas que no se negocian

- **La pestaña sigue sin escribir nada en el proyecto de Premiere.** Ni una
  carpeta, ni un clip, ni el timeline. Sigue siendo de lectura entera.
- **La revisión de la lista se queda intacta** —que traiga todos los cuartos
  de Bruno y ninguno inventado, comparados por igualdad exacta de cadena—.
  Está en el §6 del spec anterior y no la toca nada de esto. Si el patrón
  hiciera que el modelo se saltara un cuarto, la revisión lo cacha igual.
- **De la computadora sale video hacia Gemini**, y eso es nuevo. Son videos que
  Bruno ya entregó a sus clientes, no material en bruto. Pero es un cambio
  real respecto a la pestaña de hoy, donde solo salían nombres de cuartos, y
  queda escrito aquí para que nadie lo descubra después.
- **La herramienta del análisis NO entra a la app.** Vive en
  `herramientas/patron-de-recorrido/` y se corre a mano una vez al año para
  refrescar el patrón. Clipify no la llama nunca.

## 8. Lo que NO entra

- **Bajar todo de Drive.** Los videos están en el disco de Bruno (§2.c).
- **Escoger una muestra.** El costo no lo justifica (§2.b): se analizan los 33.
- **Bajarle los fps.** No ahorra nada (§2.a).
- **Las versiones «sin voz».** Son el mismo corte (§4.a).
- **Un patrón por formato de cuadro.** El 16x9 y el 9x16 llevan el mismo
  recorrido (§3.bis).
- **Ocho patrones, uno por formato y tipo.** Salen de cuatro videos cada uno
  (§3.11).
- **Que el documento lleve cuentas o se justifique** (§5.1).
- **Que la lista sea obligatoria.** Manda la IA (§3.6).
- **Que el programa señale los proyectos repetidos.** Bruno los tacha él
  (§4.b.1).
- **Que el programa decida qué fue una prueba.** No se puede saber desde el
  archivo (§4.b.1).
- **Ordenar los clips dentro de cada cuarto.** Sigue fuera, igual que en el
  spec anterior.

## 9. El orden del trabajo

Lo puso Bruno cuando se le propuso empezar por probar Gemini: «primero tú
haces la lista, yo te digo cuáles son y luego los buscamos. Gemini es hasta
después».

**Y es el orden correcto.** La propuesta de arrancar por Gemini venía de una
costumbre buena —probar primero lo que puede tumbar el diseño— aplicada mal:
armar la lista **no cuesta nada**, no comprime, no baja, no sube. Poner una
prueba técnica antes de un paso gratis solo retrasa el paso gratis.

1. **La lista.** El programa lee Drive y saca los 35 con su enlace.
2. **Bruno poda** (§4.b.1). Aquí se cae a los de verdad, que pueden ser
   bastantes menos de 35.
3. **Buscar en el disco** los que quedaron, y reportar los que no aparecen.
4. **Probar Gemini con tres**, ya sabiendo cuáles son los buenos.
5. **El resto**: comprimir los demás, analizarlos, sacar el patrón.

### 9.1 El riesgo sigue siendo Gemini, y por eso va en el paso 4

**Que reconozca los cuartos de verdad.** Todo descansa en que una ficha por
video sea confiable; si confunde una recámara con una sala, el patrón sale mal
y **no hay forma de notarlo mirando el resultado** — un orden equivocado se lee
igual de bien que uno correcto.

Se prueban tres videos y **Bruno mira las tres fichas** contra los videos que
él editó. Él es la única verificación posible: es el único que sabe qué había
en cada cuarto.

Va en el paso 4 y no en el 5 por una razón que sí se sostiene: **antes de las
tres horas de compresión de los 35**. Tres videos se comprimen en minutos.

**Si falla**, lo que cambia es de dónde salen los cuartos, no el resto del
diseño: habría que sacarlos de otro lado —los nombres de los bins de los
proyectos de Premiere de cada entrega, si es que existen— en vez del video.

## 10. Cómo se comprueba

**Con pruebas**, lo que es lógica pura, en `tests/`:

- Que las versiones «sin voz» / «sin narración» se descarten y la buena no.
- Que el material en bruto (`DJI_…`) nunca entre a la lista.
- Que un proyecto con archivo dudoso salga **marcado**, no adivinado.
- Que cada renglón de la lista salga con su enlace de Drive (§4.b.1).
- Que lo que Bruno tachó una vez no vuelva a aparecer en la siguiente corrida,
  y que un proyecto nuevo sí aparezca.
- Que el emparejamiento con el disco sea por nombre exacto, y que lo que no se
  encuentra se reporte en vez de saltarse callado.
- Que las cuentas del §4.e den lo que deben sobre fichas inventadas de
  ejemplo, incluido el caso de un tipo de propiedad con un solo video —que
  **no** debe producir una excepción en el documento.

**Contra Gemini de verdad:** la prueba de los tres videos del §9.1, en su
lugar del orden — después de la lista y de la poda, antes de comprimir los 35.

**Verificación visual real**, según `CLAUDE.md`: captura de la pestaña con la
pregunta de «para quién» ya quitada y la de «qué lucir» al frente, y captura
de una lista donde la IA se salió del orden y lo marcó. Si no se miró la
imagen, no se afirma.

## 11. Lo que hace falta de Bruno

Una **llave de Gemini** (Google AI Studio, gratis, es pegar y listo). Sin ella
no se analiza nada. Se guarda igual que la de DeepSeek: fuera del repo, fuera
del proyecto de Premiere, y **nunca en el log**.
