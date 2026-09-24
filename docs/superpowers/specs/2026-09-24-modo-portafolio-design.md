# Modo Portafolio: recopilar clips de varios proyectos entregados

Fecha: 2026-09-24. Diseño acordado con Bruno, brainstorm completo en
chat (sin sesión de `superpowers:brainstorming` formal porque no había
skill de eso disponible en la sesión; el intercambio hizo el mismo
trabajo). Mockup: `docs/superpowers/mockups/2026-09-24-modo-portafolio/mockup.html`.

## Objetivo

Bruno quiere armar videos de portafolio y anuncios juntando clips de
varios proyectos YA ENTREGADOS (distintos rodajes, distintos clientes).
Hoy Clipify no sirve para esto: está pensado para un rodaje a la vez, con
cuartos, pick/reject y un `.cvproj` por carpeta de material.

La entrada natural es Premiere: Bruno ya sabe qué clips usó en cada video
porque están en el `.prproj` de esa entrega. La idea central de todo este
diseño es que **Clipify lea esos `.prproj` hacia atrás** — en vez de
generar un proyecto de Premiere, esta vez lo consume — para saber qué
clips vale la pena reconsiderar, sin tener que volver a ver el rodaje
completo cada vez.

## Por qué es una app nueva, no un modo del Clipify normal

Se evaluó meter esto como una pantalla más de Clipify y se descartó: los
dos flujos no comparten casi nada de lo que hace único al modo normal
(cuartos, pick/reject/destacado, un rodaje = un `.cvproj`). Forzarlos a
compartir pantalla habría sido peor para los dos.

En cambio: **es un punto de entrada nuevo, dentro del mismo repo, que
comparte el motor con el Clipify de siempre** — mpv embebido, lectura y
escritura de `.prproj`, generación y cache de proxies y miniaturas. Ese
motor vive separado de la UI de cualquiera de los dos modos (candidato:
`src/clasificador_video/core/`), para que un bug arreglado ahí beneficie
a los dos sin duplicar código. El nombre de trabajo es "Clipify
Portafolio"; el nombre final queda pendiente.

## El portafolio: uno solo, que crece para siempre

No se crea un portafolio nuevo por cada video ("Reel 2026", "Anuncio
Instagram"...). Hay **un solo portafolio** al que Bruno le va metiendo
`.prproj` indefinidamente. Sus Elegidas y etiquetas se acumulan ahí para
siempre. Esto evita duplicar trabajo pesado (generar proxies, escanear
un rodaje completo) entre un video y el siguiente cuando comparten
material de origen.

Consecuencia directa: **"generar el `.prproj` final" no es un paso
terminal de una línea recta** — es algo que Bruno hace las veces que
quiera, cada vez filtrando el portafolio por las etiquetas que le sirven
para ESE video. Por esto Armar y Entregar son un solo módulo, no dos.

## Los tres módulos

Mismo espíritu que las páginas de DaVinci Resolve: cada uno hace una sola
cosa, con su propio switcher arriba, para que la cabeza nunca tenga que
sostener dos tareas a la vez. Nunca se ve el portafolio completo de
golpe — ni en Revisar (un proyecto a la vez) ni en Armar/Entregar (solo
las Elegidas, ya filtradas).

### ① Importar

- Se sueltan uno o varios `.prproj`. Se puede volver a este módulo
  cuando se quiera, para seguir sumando al portafolio con el tiempo.
- Se leen **todas las secuencias** que traiga el archivo, no solo una —
  no hace falta preguntarle a Bruno cuál es "la buena" (esto se decidió
  explícitamente: menos ambigüedad, menos que construir).
- Por cada clip usado en cualquier secuencia se guarda: ruta del archivo
  de origen, y el rango (in/out) que se usó — puede haber más de un
  rango si el mismo archivo se usó dos veces.
- Si un archivo no vincula, se avisa ahí mismo y se puede indicar dónde
  está — igual que ya hace la app con proxies. No bloquea el resto de la
  importación.
- Cada `.prproj` soltado se vuelve un **proyecto** dentro del rail de
  Revisar. Caso normal: un `.prproj` por proyecto (Bruno lo confirmó; no
  hace falta lógica de fusión para dos `.prproj` del mismo rodaje).
- **Categoría del proyecto** ("Casa", "Depto", "Terreno"...): se puede
  asignar aquí mismo, en la fila de cada `.prproj` importado, con un
  selector de una lista editable (se puede crear una categoría nueva al
  vuelo, como los cuartos hoy). No es obligatorio en este paso — se
  puede dejar sin asignar y ponerlo después en Revisar. Es el MISMO dato
  editable desde los dos lugares.

### ② Revisar

- Rail izquierdo = proyectos importados (no cuartos). Se pica uno y la
  hoja muestra solo sus clips — nunca se mezclan dos proyectos en esta
  pantalla.
- Cada fila del rail muestra: color de proyecto, nombre, categoría,
  conteo de clips y cuántos ya son Elegidas.
- **Categoría del proyecto**, editable aquí también (mismo campo que en
  Importar).
- **Un proyecto sin su disco conectado se ve apagado, nunca se poda de
  la lista** — mismo lenguaje ya establecido en `pantalla_inicio.py`
  para proyectos no disponibles. Sus Elegidas y etiquetas ya guardadas
  no se pierden por no tener el disco a la mano. Si el disco vuelve a
  conectarse en la misma ruta, se reconecta solo; si cambió de ruta, se
  puede revincular a mano señalando la carpeta nueva. Bruno trabaja con
  material repartido en ~4 SSDs que no siempre están conectados, así que
  **el progreso tiene que poder hacerse por partes**: revisar hoy los
  proyectos cuyo disco sí está, y seguir mañana con otro sin que nada
  bloquee.
- **Estado del clip: una escalera de tres peldaños**, no un checkbox —
  `Descartada ← Sin decidir → Elegida` — el mismo mecanismo que ya usa
  pick/reject/destacado en el modo normal (`ESCALERA_DE_ESTADO` en
  `main_window.py`: `("reject", "none", "pick", "destacado")`), aplicado
  aquí con tres peldaños en vez de cuatro.
  - `↑` mueve hacia Elegida, `↓` mueve hacia Descartada. Desde un
    extremo, la flecha contraria regresa primero a "Sin decidir" antes
    de cruzar al otro lado.
  - `←`/`→` quedan libres para moverse entre clips sin decidir nada,
    como ya funcionan hoy.
  - Filtros de la hoja: Todos / Sin decidir / Elegidas / Descartadas.
- **Ver el rodaje completo**: por default, Revisar solo enseña los
  clips que salieron en alguna secuencia del `.prproj` importado. Un
  botón deja ver TODOS los clips de ese rodaje, no solo los usados —
  útil cuando hay una toma buena que no se usó en el video entregado
  pero sí sirve para el portafolio.
  - **No depende de tener un `.cvproj`** del rodaje original (la
    mayoría de los proyectos de Bruno no lo tienen). La carpeta del
    rodaje se DEDUCE de la ruta de los clips ya usados (la carpeta en
    común); si no se puede deducir con confianza, se pregunta la
    carpeta en vez de adivinar mal y callado.
  - Clips encontrados ahí también pasan por la misma escalera
    (Descartada/Sin decidir/Elegida) y, si se eligen, entran al
    portafolio exactamente igual que los que sí venían del `.prproj` —
    no hay clips de primera y de segunda.

### ③ Armar y entregar

- Universo: **solo las Elegidas de todo el portafolio** — es el único
  momento en que conviven clips de proyectos distintos en una misma
  hoja, y por definición ya es un conjunto mucho más chico que el
  portafolio completo.
- **Etiquetas libres por clip** (varias por clip, a diferencia de la
  categoría de proyecto que es una sola). Mismo mecanismo de número +
  paleta que ya usan los cuartos, pero la tecla numérica SUMA o QUITA la
  etiqueta en vez de reemplazarla — porque un clip puede tener más de
  una.
- **Carpeta de portafolio**: Bruno elige dónde vive (la app propone,
  nunca adivina en silencio — mismo principio que la carpeta de proxies
  del modo normal). Adentro, una subcarpeta por proyecto de origen (con
  el nombre exacto del proyecto, igual que hoy con material), y dentro
  de cada una, un **alias** (de Finder, no copia ni symlink) por cada
  clip Elegido, apuntando al archivo real donde sea que viva. Los alias
  se crean en este módulo, no en Importar — así nunca se ensucia con
  clips que al final no se usan.
- **Proxies faltantes**: si un clip Elegido no tiene proxy en ninguno de
  los lugares que la app ya busca, se genera aquí mismo, dentro de la
  carpeta de portafolio, junto a su alias — porque ya se sabe que ese
  clip sí se va a usar. Si el mismo clip de origen ya tiene un proxy
  generado por OTRA entrega o por este mismo portafolio antes, se reusa:
  nunca se regenera dos veces el mismo proxy.
- **Generar la entrega**: se filtra por una o varias etiquetas, y con
  ese subconjunto se genera un `.prproj` nuevo, con bins por proyecto de
  origen (nombrados con su categoría, ej. "Casa Reforma — Casa"),
  apuntando a la carpeta de portafolio. El nombre del archivo lleva la
  fecha (`Mi Portafolio — entrega 2026-09-24.prproj`) para que
  regenerar más tarde con más clips nunca pise la entrega anterior.
  Esto se puede repetir tantas veces como haga falta, con filtros
  distintos cada vez.

## Economía de recursos (el problema real detrás de "hasta 2000 clips")

Bruno señaló que con material de 40+ proyectos esto puede ser mucho más
grande que un rodaje normal (100-200 clips) — hasta 2000. Las medidas ya
documentadas en `docs/superpowers/CONTEXTO-Y-METAS.md` (portadas desde
el proxy: 13 veces más rápido que desde el original) siguen aplicando,
más estas específicas de Portafolio:

1. **Revisar solo mira los clips usados**, no el rodaje completo — ya
   acota el problema antes de optimizar nada: de 300 clips de un rodaje,
   típicamente solo unos 15-30 salieron en el video entregado.
2. **"Ver el rodaje completo" genera miniaturas por lo que se ve en
   pantalla, no de todo el rollo de una vez** (carga tipo ventana/
   scroll, no todo al abrir). El costo de abrir esa vista no depende de
   qué tan grande fue el rodaje.
3. **Sin proxy, la portada se pide ya reducida al decodificador**, en
   vez de sacarla a resolución completa y reducirla después — no
   elimina el costo de decodificar el HEVC original, pero sí abarata lo
   que se guarda en cache y lo que cuesta releerlo después.
4. **Clips fuera de la secuencia original (encontrados en "rodaje
   completo") se quedan con 3 miniaturas de escrubeo en vez de 12** —
   los que sí vienen del `.prproj`, donde la decisión importa más, se
   quedan con el detalle completo.
5. **Los proxies generados para un clip se reusan entre entregas y
   entre revisiones del mismo portafolio** — nunca se regenera de cero
   un proxy que ya existe en la carpeta de portafolio.

Todo esto es propio de Clipify Portafolio; el modo normal no se toca.

## Decisiones que se evaluaron y se descartaron

- **Marcar qué clips ya salieron en una entrega anterior**: se propuso
  y Bruno dijo que no hace falta. No construir.
- **Filtros de etiqueta guardados con nombre** (para repetir una
  combinación después sin volver a pickearla): Bruno no tuvo
  preferencia clara; se decide no construirlo en esta primera entrega
  por ser el camino más simple — se puede agregar después sin rediseñar
  nada, ya que las etiquetas y el filtro ya existen.
- **Elegir cuál secuencia de un `.prproj` es "la buena"**: no aplica, se
  leen todas.
- **Buscador rápido de proyecto en el rail de Revisar**: se descartó —
  Bruno no necesariamente sabe los nombres de memoria, así que teclear
  no ayuda. El rail se queda como lista clicable simple.

## Fuera de alcance de esta spec (para una siguiente pieza)

- El formato exacto del archivo de datos del portafolio (extensión,
  esquema) — es una decisión de implementación, no de producto.
- La UI de "revincular disco" a detalle de pixel (se sabe el
  comportamiento, falta el mockup fino).
- El selector de categoría y el de etiquetas a nivel de widget Qt.
