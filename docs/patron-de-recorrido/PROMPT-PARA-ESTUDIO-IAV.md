# Prompt para abrir la sesión en Estudio IAV

*Cópialo entero y pégalo como primer mensaje de una conversación nueva, abierta
en el repo `inmueblesaudiovisuales-dev/estudio-iav`.*

---

```
Soy Bruno, editor de video inmobiliario en Monterrey. Estás en el repo de
Estudio IAV, mi portal interno. Este repo ya escribe guiones de locución —eso
es la pestaña de narración— y hoy vengo con datos nuevos para mejorarlos.

Antes de nada, las reglas de casa:
- Contéstame en español mexicano, de tú. Nunca "vos" ni "vosotros". "Aquí", no
  "acá". "Computadora", no "ordenador". "Video", no "vídeo".
- Yo no programo. En el chat háblame corto y en palabras normales: qué cambió y
  qué voy a ver. El detalle técnico va en los commits y en los docs, no aquí.
- No empieces a escribir código. Primero quiero que entiendas lo que traigo,
  me hagas las preguntas que necesites de una en una, y acordemos el diseño.

LO QUE TRAIGO

Se analizaron los 15 videos que entregué en 2026. Se les sacó el audio, se
transcribió con Whisper en mi Mac, y se midieron las 103 frases que salieron.
12 de los 15 traen narración; los otros 3 van con música sola.

Esto NO son impresiones. Cada número se midió:

LARGO Y RITMO
- 2.3 palabras por segundo de video. 10 de los 12 caen entre 2.0 y 2.4.
- Mediana de 99 palabras por guion. El más corto tiene 56, el más largo 182.
- 8 o 9 frases por guion (103 frases en 12 videos).
- La frase típica es de 13 palabras. Ninguna pasa de 26.

REGLAS ABSOLUTAS, no tendencias
- CERO signos de admiración en 103 frases.
- CERO menciones de precio en los 12 videos.
- Cuando mucho una pregunta por guion, y solo para abrir.

LA ESTRUCTURA, en este orden
1. QUÉ Y DÓNDE en la primera frase, sin preámbulo (11 de 12).
   Arranques que repito: "Descubre...", "Bienvenidos a...",
   "Ubicado en..., acompáñame a conocer...", o el tipo en seco.
2. CONEXIÓN con nombres propios: avenidas, hospitales, plazas, carreteras.
   Nunca "excelente ubicación" a secas — siempre el nombre y los minutos.
3. EL RECORRIDO espacio por espacio, encadenado con conectores de movimiento:
   "Al entrar, te recibe...", "que conecta fluidamente con...",
   "A continuación...", "En planta alta...", "En el exterior...".
   Cada espacio lleva UN adjetivo o UN dato, nunca una lista.
4. EL DATO DURO como frase propia: metros, niveles, recámaras, baños.
   "metros cuadrados" aparece en 5 de 12; el número de recámaras en 7.
5. LAS AMENIDADES enumeradas rápido y sin verbo:
   "Alberca, gimnasio, pet park, ludoteca y salón de eventos."
6. EL CIERRE en una sola frase. 8 de 12 piden la cita; "agenda" aparece en 6.

EL VOCABULARIO CAMBIA CON EL TIPO, y el corte es limpio
- Casa, departamento, quinta -> palabras de VIDA: familia, descanso, convivir,
  luz natural, comodidad, hogar, recuerdos.
- Terreno, local, hospedaje -> palabras de NEGOCIO: inversión, plusvalía,
  potencial, desarrollo, versátil, metros cuadrados.
Medido: terreno y local llevan 4 o 5 palabras de negocio y 0 a 2 de vida. Casa,
departamento y quinta, exactamente al revés. No hay un solo video donde se
crucen.

EL HALLAZGO QUE MÁS IMPORTA
En los 12, la narración sigue EL MISMO ORDEN que la imagen. No hay ninguno
donde la voz vaya por un lado y el video por otro. Mi patrón de recorrido y mi
patrón de guion son el mismo patrón.

DÓNDE ESTÁN LOS DATOS CRUDOS, en mi Mac
- ~/Movies/patron-2026/transcripciones.md  — las 15 transcripciones completas,
  cada una con su duración, tipo de propiedad y número de tomas.
- ~/Movies/patron-2026/*.mp4               — los 15 videos entregados.
- En el repo de Clipify, "docs/patron-de-recorrido/PROMPT-NARRACION.md" —
  el prompt de redacción que salió de esto, con la tabla de dónde salió cada
  regla.
Léelos antes de proponer nada. Si no los encuentras, dime y te los paso.

LO QUE QUIERO QUE HAGAS

Primero, lee cómo escribe guiones este repo hoy. Empieza por "ARRANQUE.md" y
"LEEME.md", y luego "worker/src/borrador.js", "worker/src/verificacion.js",
"worker/src/segmentos.js" y "worker/src/routes/narracion.js".

Hay una garantía en ese código que NO se toca: el borrador no redacta de su
cabeza, arma frases con hechos que ya están en el mensaje del cliente o en la
ficha, y por construcción no puede inventar. El propio archivo lo dice: si un
día un modelo escribe más bonito, tiene que ser reescribiendo frases QUE YA
SALIERON de un hecho, y pasando igual por revisar().

Mi patrón encaja ahí sin romper nada, y esa es justo la gracia: **no agrega
datos**. Manda sobre el ORDEN, el RITMO, el REGISTRO y el CIERRE — nunca sobre
qué se afirma de la propiedad.

Entonces: dime cómo meterías estas medidas al repo para que los guiones que
salen se parezcan más a los míos, sin tocar la garantía de que no invente.
Propón dos o tres caminos con sus ventajas y desventajas, dime cuál me
recomiendas y por qué, y pregúntame lo que te falte — de una pregunta a la vez.

Una cosa que ya sé que vas a encontrar: "ordenarPorVideo" en borrador.js ya
ordena las frases según los segmentos del video. Eso ya va en la dirección
correcta; mírate bien qué tanto de lo que traigo ya está resuelto ahí antes de
proponer construir algo nuevo.
```

---

## Por qué está escrito así

- **Trae los números adentro.** La sesión nueva arranca en frío y no ve esta
  conversación. Si las medidas no viajan en el prompt, no existen.
- **Nombra los archivos del repo a leer.** Sin eso, la sesión nueva empieza
  explorando a ciegas y gasta la mitad del contexto en orientarse.
- **Dice explícitamente qué NO tocar.** La garantía de «no puede inventar» es
  la decisión más fuerte de ese repo, y un patrón de estilo mal aplicado es
  exactamente la clase de cosa que la rompería sin que nadie lo note.
- **Pide preguntas antes que código**, igual que aquí.
