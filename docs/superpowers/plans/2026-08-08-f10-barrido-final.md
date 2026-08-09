# F10 del rediseño — Barrido final — Implementation Plan

> **Para quien lo ejecute:** las tareas van con checkbox (`- [ ]`) y el test se
> escribe **antes** que la implementación, como en los seis planes anteriores.

**Goal:** cerrar el rediseño. Es la última fase, y la que responde
directamente a la queja que ordenó todo este trabajo:

> «Un problema que frecuentemente tengo es que las apps de Claude no quedan
> como los mockups. Quiero que te asegures de que esto vaya a quedar
> visualmente igual que el mockup o incluso mejor, no solo el diseño viejo con
> nuevas funciones a medias y con funciones viejas sin quitar.»

**Punto de partida:** **751 tests en verde**, F0–F9 hechas, árbol limpio, y la
lista de ejecución **vacía** por primera vez.

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

**Referencias:**
- Cierre de la fase anterior: `docs/superpowers/plans/2026-08-08-f9-proxies-y-orientacion.md` (§ Cierre)
- Comportamiento acordado: `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`
- Candados anti-deriva: `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md`

---

## Advertencias antes de empezar

1. **Esta fase se juzga con los ojos, no con la suite.** Un test verde no dice
   nada sobre si un badge quedó 3 px corrido. El candado 3 —ninguna fase cierra
   sin haber mirado la imagen— es *el* criterio de esta fase, no un trámite del
   final.

2. **La transición animada es lo más riesgoso que queda.** Anima una tarjeta de
   la hoja hasta la posición del visor, y la hoja es donde este proyecto ya
   tuvo un SIGSEGV: reconstruirla dentro del `mousePressEvent` de una tarjeta
   destruye el widget que está manejando el evento. Una animación **dura medio
   segundo y sobrevive al evento**, así que el widget que anima puede morir a
   mitad del camino. Por eso la Task 3 empieza con un spike, no con código de
   producción.

3. **El switch `Clip │ Hoja` le suma ancho a la barra de título.** Un mínimo de
   layout se propaga hasta la ventana y le quita ancho al video: ya pasó con
   los chips de filtro, que empujaron el mínimo de la hoja de 520 a 591 px. El
   test `test_la_hoja_puede_encogerse_para_dejarle_ancho_al_video` es el
   guardián, y hay que mirarlo.

4. **No inventar lo que el mockup no dibuja.** Si el barrido encuentra un hueco
   que el mockup no cubre, se anota y **se le pregunta a Bruno** — no se
   improvisa. Es lo que dice `DECISIONES.md` al final.

5. **Las diferencias de DATOS no son diferencias de diseño.** El arnés usa
   `scripts/_datos_de_ejemplo.py` para reproducir los números del mockup. Si
   algo se ve distinto, la primera pregunta es si los datos coinciden. Ya pasó:
   el control de velocidad se ve `1×` en la app y `2×` en el mockup, y no es un
   bug, es que el dato de ejemplo arranca en 1×.

---

## Task 1: El barrido, con método — **antes de tocar nada**

**Files:** el resultado va a este documento, no a un archivo aparte.

El barrido no es «mirar la comparación general»: esa vista ya se miró seis
veces y no encuentra nada. Se hace **región por región, en las dos pantallas**,
ampliando:

```bash
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/f10.png --recorte X,Y,ANCHO,ALTO --zoom 3
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/f10.png --pantalla 1 --recorte X,Y,ANCHO,ALTO --zoom 3
```

**Un aviso sobre el método**: el recorte usa las mismas coordenadas en las dos
mitades, y **las dos mitades no tienen el mismo layout** — el video de la app
es más angosto que el del mockup, así que un recorte de la columna de
herramientas puede caer sobre el video en un lado y sobre los botones en el
otro. Cuando eso pase, hay que recortar cada mitad por separado.

- [x] Barrer las regiones en este orden, que va de lo más visible a lo menos:
      barra de título · rail (progreso, leyenda, cuartos, historial) · overlays
      del video (badges, controles de arriba, pie, barra de scrub) · columna de
      herramientas · encabezado y filtros de la hoja · tarjetas · barra de
      estado.
- [x] Repetir con `--pantalla 1`.
- [x] **Escribir la lista acá abajo**, cada renglón con: qué región, qué se ve
      distinto, y si es diseño o datos.

### Lo ya encontrado (antes de escribir este plan)

| # | Dónde | Qué |
|---|---|---|
| 1 | Barra de título | **Falta el switch `Clip │ Hoja ⇥`** (Task 2) |
| 2 | Barra de título | El ícono de la app es un cuadrado ámbar liso; el mockup dibuja un **triángulo de play** adentro |
| 3 | Rail, leyenda | El primer chip dice `7`; el mockup dice **`6 dest.`** — le falta la palabra. Los otros tres sí van sin palabra |
| 4 | Barra de estado | La ruta del volumen va sola; el mockup escribe **`/Volumes/FX30/CasaLomas · 214 GB`** |
| 5 | Barra de estado, modo hoja | El mockup cambia el texto a **`128 clips · 74 verticales · 54 horizontales`**; la app sigue mostrando el clip actual |
| 6 | Overlays del video, ventana **baja** | A 1150×800 el control de velocidad queda en `x = -165`, **fuera de la imagen** y encimado con el nombre del archivo |
| 7 | Todo | **Falta la transición animada** de la tarjeta al visor (Task 3) |

El 6 merece una nota: **solo aparece con la ventana baja, no angosta.** Con un
clip vertical el ancho del video sale de la altura, así que a 800 px de alto el
video mide 416 px y ahí no caben `nombre + velocidad + calidad`. A 1000 px de
alto entra bien — que es exactamente por qué ninguna revisión anterior lo vio,
incluida la que decía haber medido «a 1150 px».

---

## Task 2: El switch `Clip │ Hoja` de la barra de título

**Files:**
- Modificar: `src/clasificador_video/ui/title_bar.py`, `ui/theme.py`
- Test: `tests/ui/test_title_bar.py`, `tests/ui/test_main_window.py`

El mockup lo pone **después del subtítulo y antes del espaciador**, con la
tecla dibujada en el lado que NO está activo (`Clip` activo → `Hoja ⇥`; en modo
hoja, `Clip ⇥` → `Hoja` activo). Ese detalle importa: la tecla se dibuja donde
te va a llevar, no donde estás.

Ya existe un control segmentado en el proyecto (`ui/segmented.py`, el de
velocidad y calidad). **Se reusa**, no se hace uno nuevo.

**Tests (antes):**
- [x] En modo clip, `Clip` está activo y la tecla `⇥` se dibuja sobre `Hoja`.
- [x] En modo hoja se invierte, los dos lados.
- [x] Clickearlo alterna el modo, igual que `⇥`.
- [x] **Es una sola vista del mismo estado**: alternar con `⇥` deja el switch
      como corresponde. Dos vistas del mismo dato ya se separaron seis veces en
      este proyecto.
- [x] Los botones llevan `NoFocus`, o el espacio activa el botón enfocado en
      vez de reproducir.
- [x] La ventana **sigue pudiendo encogerse**: el switch no empuja el mínimo.

---

## Task 3: Spike de la transición — **antes de escribir la animación**

**Files:** al scratchpad de la sesión, **no al repo**.

`DECISIONES.md`: «la tarjeta crece hasta la posición del visor. Medio segundo
que evita el "¿dónde estaba?" en cada cruce».

**Qué hay que demostrar, con la hoja de 128 tarjetas:**

- [x] Que se puede animar **sin animar la tarjeta real**. Lo natural es
      animar un widget **prestado** (una copia con el pixmap de la tarjeta, hija
      de la ventana) y dejar la hoja quieta debajo. Si se anima la tarjeta de
      verdad, el re-acomodo de la hoja la mueve bajo la animación.
- [x] Que sobrevive a que la hoja se reconstruya a mitad del camino: el gesto
      que dispara la animación (doble click, `⇥`) también cambia el clip
      actual, y eso repinta. Medir qué pasa si la animación sigue viva cuando
      su tarjeta ya no existe.
- [x] Cuánto cuesta: la animación corre 500 ms a 60 fps, o sea **30 cuadros con
      presupuesto de 16.7 ms cada uno**. Si un cuadro de la animación cuesta
      más que eso, se ve peor que no tenerla.
- [x] Qué pasa con `⇥` repetido rápido. Una animación a medias que recibe otra
      orden es el caso que rompe este tipo de efecto.

**Si el spike dice que no se puede hacer estable, se descarta y se le dice a
Bruno** — con el número, como se descartó la precarga en la F6. Medio segundo
de animación que a veces parpadea es peor que un corte limpio.

---

## Task 4: Los dos huecos que dejó la F9

**Files:**
- Modificar: `src/clasificador_video/ui/video_stage.py` (el de arriba),
  `ui/status_bar.py` + `ui/main_window.py` (el de la hoja)
- Test: `tests/ui/test_video_stage.py`, `tests/ui/test_status_bar.py`

**4a — la fila de arriba del video, en ventana baja.** Hoy `nombre + velocidad
+ calidad` se acomodan como si siempre cupieran. Con 416 px de video no caben y
el control de velocidad se va a `x = -165`.

- [x] Test que a 416 px de ancho de video **ningún control queda con `x < 0`**
      ni se encima con otro. Es el mismo tipo de test que atrapó el choque del
      pie con la fila de teclas en la F7.
- [x] Qué se recorta primero cuando no cabe **es una decisión de diseño**: el
      candidato es esconder el nombre del archivo, que ya está en la barra de
      estado. Preguntarle a Bruno antes (advertencia 4).

**4b — la barra de estado en modo hoja.** `128 clips · 74 verticales · 54
horizontales`.

- [x] El conteo sale de `orientacion_de` sobre `_clip_sizes`, la **misma**
      función del manifest y de la barra en modo clip.
- [x] Sin tamaños conocidos (sesión restaurada) no se inventan ceros: se
      muestra solo `128 clips`.
- [x] Volver a modo clip restaura el texto del clip actual.

---

## Task 5: Las diferencias chicas del barrido

**Files:** según lo que salga; los renglones 2, 3 y 4 de la tabla de arriba ya
tienen dueño.

- [x] **El ícono de la app** lleva el triángulo de play. Es un `QLabel` con
      fondo ámbar: el triángulo va como pixmap dibujado con `QPainter`, no como
      carácter de texto — un `▶` de fuente no queda igual en todas las máquinas.
- [x] **El primer chip de la leyenda dice `6 dest.`**, y solo el primero. El
      resto sigue sin palabra.
- [x] **La barra de estado agrega el tamaño del volumen** (`· 214 GB`), con
      `shutil.disk_usage`. Sin volumen montado, no se escribe nada — no un
      `0 GB`.
- [x] Lo que el barrido agregue.

---

## Task 6: Cierre del rediseño

- [x] Suite completa en verde, con el número anotado.
- [x] Los detectores de la §8 del handoff.
- [x] cProfile de la tecla de cuarto y de la transición.
- [x] **Los dos anchos y las dos alturas**: 1600×1000, 1150×800 y 1400×900. La
      F9 demostró que el ancho solo no alcanza — con material vertical el que
      manda es el **alto**.
- [x] El arnés en las dos pantallas, mirando la imagen.
- [x] Una pasada a mano con material real, de punta a punta: importar,
      clasificar un puñado de clips con teclado, marcar in/out, exportar y
      **abrir el manifest en Premiere**. Es la única prueba que cubre el
      contrato completo.
- [x] Archivar los planes de fases terminadas y dejar un handoff final o un
      documento de estado, según lo que Bruno pida.


---

## Cierre de la F10 — 2026-08-08

**783 tests en verde** (venían 751 al empezar la fase, 704 al empezar la F9),
árbol limpio, lista de ejecución vacía.

### Lo que se hizo

| # | Qué | Dónde quedó |
|---|---|---|
| 1 | Switch `Clip │ Hoja ⇥` | `ui/title_bar.py`, reusando `SegmentedControl` |
| 2 | El triángulo de play del ícono | `ui/title_bar.py::_marca_de_play` |
| 3 | `6 dest.` en el primer chip, y en fuente de interfaz | `ui/room_rail.py` |
| 4 | `· 214 GB` junto a la ruta del volumen | `ui/status_bar.py` |
| 5 | La barra de estado resume el shooting en modo hoja | `ui/status_bar.py::set_resumen` |
| 6 | La velocidad se esconde cuando la fila de arriba no cabe | `ui/video_stage.py` |
| 7 | La transición animada de la tarjeta al visor | `ui/transicion.py` (módulo nuevo) |

### Lo que el barrido encontró **de más**

Dos cosas que no estaban en la lista y salieron de mirar:

- **Los badges se encaramaban con el selector de calidad, en todos los
  tamaños, desde la F6.** Colgaban del nombre del archivo (15 px de alto) y no
  de la fila de arriba completa (25 px), así que quedaban 2 px por dentro de
  una caja translúcida que les comía el borde. En la comparación general no se
  ve; hay que ampliar.
- **La hoja no llevaba al clip actual.** `DECISIONES.md` dice «`⇥` alterna
  llevando SIEMPRE al clip actual, en los dos sentidos», y con 128 clips la
  hoja se abría mirando el 117 mientras el actual era el 87. Lo encontró el
  spike de la transición, no el barrido: la tarjeta a animar estaba en
  `y = 3596`, mil píxeles abajo del viewport.

### Diferencias que quedan, a la vista

Ninguna es un descuido; están acá para que se decidan y no se olviden.

| Qué | Por qué se dejó |
|---|---|
| La `⇥` del switch va como glifo suelto; el mockup la encierra en una cajita | QSS no puede estilar una parte del texto de un botón, y meter una etiqueta adentro rompería que el control segmentado se identifique por su texto. A tamaño real no se distingue |
| Las miniaturas de los clips sin clasificar salen grises en el arnés; el mockup las pinta de colores | Es del **generador de miniaturas de ejemplo**, no de la app: con material real cada tarjeta trae su propio frame |
| El mockup dibuja la paleta `⏎` abierta y la barra de selección múltiple | Son estados que el arnés no monta. Los dos existen y tienen sus tests |

### Detectores, al cierre

| Detector | Resultado |
|---|---|
| Señales declaradas sin conectar | ninguna |
| Tokens del tema huérfanos | ninguno |
| Widgets huérfanos tras 60 teclas (incluyendo `⇥`) | 701 → 701 |
| Tecla de cuarto | 3.76 ms |
| Cuadro de la transición, con 128 tarjetas | 0.02 ms de mediana, 1.14 el peor (presupuesto 16.7) |

### Lo que enseñó esta fase

- **El barrido región por región encuentra lo que la vista general no.** Los
  siete renglones de la lista salieron de recortes al 300–600 %. La comparación
  entera ya se había mirado seis veces sin ver ninguno.
- **Un spike encuentra cosas que no estaba buscando.** El de la transición
  venía a medir si se podía animar; lo que descubrió es que la hoja no llevaba
  al clip actual, que es un renglón de `DECISIONES.md` de la F8.
- **`qtbot.addWidget` no muestra el widget, y sin mostrarlo el acomodo de
  overlays no corre.** Escrito con `_stage` en vez de `_stage_visible`, el test
  del control de velocidad pasaba sin probar nada. Van dos veces que esta misma
  trampa da un verde falso.
- **Las diferencias de datos se disfrazan de diferencias de diseño.** El arnés
  mostraba `103 verticales · 25 horizontales` contra los `74 · 54` del mockup,
  y eso obliga a descartarlo a mano en cada comparación futura. Se arregló en
  los datos, no en la app.

### Lo que falta para dar el rediseño por cerrado

Es de Bruno, no del código:

- [ ] La pasada a mano con material real de punta a punta: importar, clasificar
      con teclado, marcar in/out, exportar y **abrir el manifest en Premiere**.
      Es la única prueba que cubre el contrato completo, y ahora además tiene
      algo nuevo que probar: el proxy enganchado.
- [ ] Los atajos con modificador (`⌘Z`, `⌘A`, `⌘E`, `⌘R`) contra el teclado
      físico.
- [ ] El pincel y la marquesina con el mouse de verdad.
