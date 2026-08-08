# Rediseño desde cero — decisiones de diseño

Propuesta única para la app de clasificación de clips, hecha sin mirar el
diseño actual. Punto de partida:
`docs/superpowers/PROMPT-REDISENO-2026-08-08.md`, más las correcciones de
Bruno durante la sesión del 8 de agosto de 2026.

- Mockup estático: [`mockup.html`](mockup.html). Dos pantallas, una debajo de
  la otra: **modo clip** y **modo hoja**. Ventana maximizada 1600×1000. No es
  navegable a propósito.

---

## El objetivo que ordena todo

La app existe para hacer lo que Premiere no puede: **clasificar rápido**. Cada
decisión de diseño se mide contra una sola pregunta — ¿cuántas acciones cuesta
resolver un shooting de 128 clips?

Las dos operaciones que importan tienen costos muy distintos, y confundirlas
fue el error de las primeras versiones de este diseño:

| Operación | ¿Necesita ver el video? | Granularidad natural |
|---|---|---|
| **Asignar cuarto** | No — con un frame alcanza | **Lote**: las tomas vienen en rachas |
| **Marcar pick** | **Sí, sin excepción** | Uno a la vez |
| Marcar in/out | Sí | Uno a la vez, solo en los picks |

De ahí salen los dos modos.

## Dos modos, una tecla

`⇥` alterna entre:

- **Modo hoja** — la hoja de contactos ocupa la ventana entera, siete
  columnas de miniaturas grandes. Es donde se asignan cuartos en lote sin
  abrir un solo clip.
- **Modo clip** — el video vertical a altura completa, con la hoja al
  costado. Es donde se ve y se marca pick.

No son dos aplicaciones: es el mismo layout con distinto reparto del ancho.
El rail de cuartos, el historial y la barra de filtros son idénticos en los
dos.

## Cero bandas horizontales (el video vertical grande)

En una ventana apaisada, **un video vertical está limitado por la altura, no
por el ancho**. Esconder paneles laterales no lo agranda ni un pixel; lo
único que lo agranda es no robarle altura. Y en un 9:16, cada 16 px de alto
que le quites cuestan 9 px de ancho.

| | alto del video | ancho del video |
|---|---|---|
| Primera versión (1440×900, con bandas de chrome) | 588 px | 331 px |
| **Esta versión (1600×1000)** | **940 px** | **529 px** |

El video ocupa el 100% de la altura entre la barra de título (36 px) y la de
estado (24 px). Cada control se fue a un lugar que no cuesta altura:

1. **Flotando sobre el video** — timecode, scrub bar, in/out, nombre de
   archivo, velocidad, calidad, badges de estado. En un clip vertical caen
   dentro del cuadro, como un reproductor a pantalla completa. Se
   auto-ocultan mientras navegás rápido.
2. **Columna vertical de 56 px** — estado del clip (in/out puestos, pick,
   destacado, reject). Una columna cuesta ancho, y ancho es lo que sobra.
3. **Barra de estado** — datos técnicos que se consultan, no se persiguen.

Y el ancho sobrante **no queda negro**: es hoja de contactos. No hay una sola
franja negra en pantalla.

## Ver rápido: el cuello de botella real

Marcar pick obliga a ver el clip. No hay atajo posible, así que el diseño
optimiza el **tiempo de visionado**, no cómo evitarlo:

- **Reproducción automática al cambiar de clip.** Apretar espacio 128 veces
  es puro peaje. Llegás al clip y ya está corriendo (badge `▶ auto`).
- **Velocidad con tecla** — `1× / 2× / 4×`. Para juzgar un recorrido no hace
  falta verlo a velocidad real.
- **Arranque al 25% del clip**, no en el frame 0: el principio siempre es la
  cámara acomodándose.
- **Precarga del siguiente clip** mientras mirás el actual (`siguiente clip
  precargado ✓` en la barra de estado). Medio segundo de espera por clip son
  más de un minuto por shooting, y es lo que hace *sentir* lenta a una app.

## Miniaturas escrubeables

Cuando la miniatura no te dice el cuarto, tenés que abrir el clip — y ahí
perdiste el tiempo que el modo hoja te ahorraba. En un recorrido el primer
frame suele ser una puerta, una pared o movimiento borroso.

Dos correcciones baratas y de mucho impacto:

- **El frame de portada es el del 25% del clip**, no el primero.
- **Pasar el mouse por la miniatura la escrubea**, como Finder o YouTube, con
  su propia barrita de progreso y timecode.

Con eso se decide el cuarto sin abrir nada en la enorme mayoría de los casos.

## `S` — igual al clip anterior

En un recorrido las tomas vienen en rachas: seis de cocina seguidas, cuatro
de sala. La tecla más valiosa que existe en este material no es un número: es
**"lo mismo que el anterior"**.

Va fija arriba del listado de cuartos, mostrando siempre a qué cuarto
aplicaría, para que sea una confirmación y no un acto de memoria. Sobre 128
clips en rachas de seis, convierte ~110 decisiones en ~110 confirmaciones sin
pensar.

## Pincel de cuarto

El truco más subestimado del módulo Library de Lightroom es el *spray can*:
cargás una palabra clave y la pintás sobre las miniaturas arrastrando.
Traducido acá: **mantené `1`–`9` y arrastrá el mouse sobre las tarjetas** —
todas las que toques quedan en ese cuarto. Una racha de seis se clasifica con
un gesto, sin seleccionar primero y asignar después.

Es más rápido que la marquesina porque elimina un paso entero (seleccionar →
asignar se vuelve un solo movimiento), y encaja con que las tomas vengan en
rachas contiguas.

Que funcione bien depende de cinco detalles, no de la idea:

1. **Es un gesto de dos manos deliberado.** Sin tecla apretada, arrastrar
   hace marquesina de selección, como siempre. El pincel solo existe mientras
   la tecla está abajo, así que no se puede disparar por accidente.
2. **El cursor lleva su carga visible** — un punto del color del cuarto más
   un chip con la tecla y el nombre (`5 ▌ Baño 1`). Nunca pintás sin saber qué
   estás pintando.
3. **La tarjeta responde en el momento de tocarla**: la que está bajo el
   cursor se ilumina con el color del cuarto, y las ya pintadas quedan
   teñidas. El rastro de la pincelada se ve.
4. **Toda la pincelada es UNA sola entrada de historial.** `⌘Z` deshace las
   seis, no una. Si deshiciera clip por clip, el pincel sería una trampa: un
   gesto rápido que cuesta seis acciones revertir.
5. **Los clips no se reagrupan hasta que soltás la tecla.** Si saltaran de
   grupo mientras pintás, la grilla se reacomodaría bajo el cursor y
   seguirías pintando sobre otra cosa. El encabezado lo dice: *se reagrupan
   al soltar la tecla*.

El mismo mecanismo sirve para los flags: mantener `X` y arrastrar descarta una
racha completa.

## Desplazamiento entre modos

Lightroom separó Library de Develop porque Develop es caro de computar. Acá la
división es de **atención**, no de cómputo — así que los dos modos deben
compartir más estado que los de Lightroom, no menos. Nada se pierde al cruzar:

- **Doble click en una tarjeta abre ese clip** en modo clip. Es el gesto de
  Grid → Loupe, y no colisiona con nada (`⏎` sigue siendo la paleta).
- **`⇥` alterna llevando siempre al clip actual**, en los dos sentidos. Al
  volver a la hoja, esa tarjeta queda centrada y resaltada con el borde ámbar,
  con el scroll donde estaba.
- **`esc` vuelve a la hoja** desde modo clip. Salida obvia, sin pensar.
- **La selección sobrevive el cruce.** Si tenías seis clips seleccionados y
  entrás a ver uno, al volver siguen los seis. Es lo que Lightroom hace mal y
  no hay razón para copiarlo.
- **Transición animada**: la tarjeta crece hasta la posición del visor. Medio
  segundo que evita el "¿dónde estaba?" en cada cruce.

## Filtros tipo Lightroom que además son la cola de navegación

Los filtros no cambian solo **lo que ves**: cambian **por dónde te movés**.

```
MOSTRAR   [todos] [sin clasificar] [clasificados]
ESTADO    [todos] [★ solo destacados] [solo picks] [ocultar rejects] [sin marcar]
```

Con "Sin clasificar" activo, `←/→` recorre únicamente esos 12 clips, en orden,
y cada uno desaparece de la cola en cuanto lo resolvés. Cuando la cola queda
vacía, terminaste — sin buscar, sin volver a pasar por nada ya hecho. El chip
`cola de ←→ · 12 clips` lo dice explícitamente, para que nunca haya dudas de
qué recorren las flechas.

La advertencia "12 sin clasificar" de la barra de estado es clickeable: es,
literalmente, el botón de "seguí trabajando".

Y por eso el visor **no dice `087 / 128`** sino **`3 de 12 en la cola`**. Tu
posición en el shooting entero no te sirve de nada mientras estás filtrando;
lo que querés saber es cuánto falta para terminar lo que estás haciendo.

## Cuatro estados, no cinco estrellas

`reject` → `neutral` → `pick` → **`destacado`**

Descarté las cinco estrellas por dos razones:

1. **Las teclas numéricas no están libres**: `1`–`9` son los cuartos, la
   acción más frecuente que existe. Cederlas a las estrellas sería cambiar el
   atajo barato de la operación cara por el de una secundaria.
2. **El costo de decidir.** Pick/reject es binario: mirás y apretás. Una
   escala de cinco te obliga a preguntarte "¿esto es 3 o 4?" en cada clip, y
   esa duda multiplicada por 128 es exactamente la fricción que hace que en
   Lightroom la gente termine usando solo las banderitas en el primer pase.
   Además: si el plugin de Premiere no hace nada distinto con 3 que con 4
   estrellas, es información decorativa que cuesta tiempo generar.

**Destacado** es *la* toma del cuarto — la que abre la secuencia de la cocina
en el corte final. Es la única gradación con significado río abajo (el plugin
puede ponerla primero). Cuesta una tecla (`⇧P`), cero deliberación, y no toca
los números. Si más adelante hace falta gradación fina, el modelo de datos
puede guardar un número y solo cambia la UI.

Visualmente **no inventa un color nuevo**: destacado es un pick reforzado
—misma familia verde, glifo `★` en vez de `P`— para que el canal semántico
"calidad del clip" siga teniendo un solo color.

## Cuartos: planos, sin techo, sin configuración inicial

Nada de subcuartos con segunda tecla: `Recámara 1`, `Recámara 2`, `Baño 1`,
`Baño 2`. Una tecla, un cuarto, sin estado intermedio ni timeout.

La app abre lista para trabajar; no hay paso previo de "elegí los cuartos".
El rail izquierdo se edita en el lugar —renombrar, reordenar (que es cambiar
qué tecla le toca a cada uno), borrar— y los cuartos se crean sobre la marcha.

Nueve teclas no alcanzan con cuartos planos. En vez de un segundo banco de
atajos —memorizar dieciocho combinaciones es peor que el problema— hay una
**paleta de asignación rápida**: `⏎` abre un campo, tecleás dos o tres letras,
la lista se filtra en vivo, `⏎` asigna y avanza. Un solo mecanismo cubre tres
necesidades:

- **cuartos que se pasan de nueve** — la paleta no tiene techo, y los cuartos
  sin tecla se ven en el rail con el badge vacío (`Estudio` en el mockup);
- **crear un cuarto al vuelo** — si no hay coincidencia, la última opción es
  `+ Crear cuarto «est»`, que lo crea, le da la siguiente tecla libre y lo
  asigna, sin soltar el teclado;
- **asignar en lote** — la paleta respeta la selección; por eso dice
  `a 6 clips` en el mockup.

El encabezado del panel dice `CUARTOS` y `⏎ buscar`, no "1–9": el rango de
teclas ya está en cada fila, y decir "1–9" sería mentira en cuanto tengas más
de nueve cuartos.

## Selección múltiple: la base del modo hoja

Arrastre para encerrar una racha, `⇧`+click para rango, `⌘A` para el grupo
entero. Con siete columnas hay ~18 clips a la vista, así que encerrar una
racha de seis con un arrastre y asignarla con una tecla es el flujo normal,
no un caso especial. Ahí está la diferencia entre 128 decisiones y ~15.

## Deshacer: historial visible, no un toast que se va

Al pie del rail izquierdo, un **historial permanente** de las últimas
acciones —`Baño 1 → 6 clips`, `Destacado → clip 086`, `IN/OUT → clip 085`—
cada una con su botón de revertir. `⌘Z` deshace la de arriba; el resto se
revierte con un click.

Con lotes esto importa el doble: equivocarse asignando seis clips a la vez es
un error seis veces más caro, y tiene que verse qué pasó sin reconstruirlo de
memoria.

## Teclado

| Tecla | Acción |
|---|---|
| `←` `→` | anterior / siguiente **dentro de la cola filtrada** |
| `,` `.` | frame anterior / siguiente (convención de Premiere) |
| `espacio` | reproducir / pausar (arranca solo al cambiar de clip) |
| `1`–`9` | asignar cuarto y avanzar |
| `S` | igual al clip anterior |
| `⏎` | paleta: buscar o crear cuarto |
| `P` `X` | pick / reject — repetir la tecla vuelve a neutral |
| `⇧P` | destacado |
| `I` `O` | marcar in / out |
| `⇥` | alternar modo clip ↔ modo hoja, siempre sobre el clip actual |
| doble click | abrir esa tarjeta en modo clip |
| `esc` | volver a la hoja (o limpiar la selección) |
| `F` | solo video, sin chrome |
| `+` `−` | tamaño de miniatura en modo hoja |
| mantener `1`–`9` + arrastrar | pincel de cuarto |
| `⌘Z` | deshacer |
| arrastre · `⇧`+click · `⌘A` | selección múltiple |

**No hay tecla de "neutral"**: `P` sobre un clip que ya es pick lo devuelve a
neutral, igual `X`. Menos atajos se aprenden más rápido y no dudás. Tampoco
existe ya `⇧`+`1`–`9` ("asignar sin avanzar"): era una sutileza que nadie iba
a usar.

Todo lo que se hace seguido tiene tecla. Lo que no tiene tecla es porque se
hace una vez por sesión.

## Qué pasa con los clips horizontales

Decisión tomada explícitamente: **el layout se reacomoda y la pantalla
"salta"**, priorizando el máximo aprovechamiento en cada clip por sobre la
estabilidad visual, porque las sesiones casi nunca mezclan orientaciones.

Con un clip horizontal el video pasa a estar limitado por el ancho: crece
hasta ~1000 px (la hoja se achica a su mínimo de ~340 px) y quedan franjas
arriba y abajo. Mismo layout, mismas reglas, sin código aparte por
orientación.

## Cómo este layout deja lugar a las metas futuras

| Meta | Dónde ya está previsto |
|---|---|
| **Clips verticales** | Es el caso de diseño principal, no una excepción. Sin una sola franja negra en pantalla. |
| **Proxies** | Badge `Proxy 1080p` junto al selector de calidad —proxy y resolución de reproducción son la misma decisión— y el contador `proxies 1080p · 128/128` en la barra de estado. |
| **Escala a cientos de clips** | Modo hoja + agrupación sticky + filtros que son la cola + selección por marquesina. Con 300 clips, clasificar por lote deja de ser una idea y es el flujo normal. |
| **Sensación de instantáneo** | Precarga del siguiente clip, autoplay, control de velocidad, selector de calidad de primera clase, y el timecode sobre la imagen para eliminar el salto de mirada. |
| **Otros editores** | Nada hardcodeado: los cuartos son datos de la sesión creados al vuelo, sin lista predefinida ni configuración previa que entender antes de empezar. |

## Lo que dejé afuera a propósito

- **Ningún control de edición.** La app clasifica y prepara.
- **Ningún paso de configuración antes de trabajar.**
- **Ninguna forma de onda de audio.** Son recorridos de inmuebles: el audio no
  informa nada. Era una apuesta equivocada de la primera versión.
- **Ningún recorte automático de in/out por defecto.** Se evaluó (aplicar
  −1 s de cabeza y cola) y se descartó.
- **Ningún modo comparar** al estilo del `C` de Lightroom (2–4 clips en
  paralelo para elegir el destacado). Se propuso y se descartó por una razón
  técnica concreta: son HEVC 10-bit, y decodificar tres o cuatro en sincronía
  es pedirle a la reproducción que tartamudee. Un modo que a veces se traba es
  peor que no tenerlo. Si algún día hay proxies livianos garantizados, se
  puede reconsiderar.
- **Ningún sistema de cinco estrellas.** Ver arriba.
- **Ningún botón sin atajo de teclado.**
