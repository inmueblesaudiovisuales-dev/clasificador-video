# Handoff — 2026-08-09 — desde el rediseño terminado

El rediseño de la UI **está cerrado** (once fases, F0 a F10). Lo que sigue no
es más UI: es **el rediseño de la importación** que pidió Bruno, y **repartir
la app** a las computadoras de su equipo.

Reemplaza a [`archive/HANDOFF-2026-08-08-rediseno-ui-desde-f9.md`](archive/HANDOFF-2026-08-08-rediseno-ui-desde-f9.md).

---

## 1. Qué es el proyecto

Una app de escritorio en **PySide6 + mpv** para que Bruno, editor de video
profesional, clasifique clips de shootings inmobiliarios **antes** de editarlos
en Premiere.

1. **La app** (`src/clasificador_video/`) — importa material, reproduce cada
   clip, y el editor le asigna un **cuarto**, lo marca **pick/reject/destacado**
   y opcionalmente le pone **in/out**. Exporta un `manifest.json`.
2. **El plugin UXP** (`uxp-plugin/`) — corre dentro de Premiere, lee ese
   manifest y arma el proyecto: bins por cuarto, etiquetas de color, in/out y
   **proxies enganchados**.

**Su razón de existir es la velocidad.** El material real es **HEVC 10-bit de
una Sony FX30**, mayoría **vertical**, más tomas de un **dron DJI** (también
verticales).

## 2. Dónde está todo hoy

- Rama `master`, árbol limpio. **831 tests en verde** — ese es el número de
  partida.

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

La suite corre en ~11 s. **Si tarda minutos, algo está lanzando mpv de
verdad**: `tests/conftest.py` lo impide, y romper esa guarda es el síntoma.

### Lo que la app hace hoy

| | |
|---|---|
| **Ver** | autoplay al 25 %, `J K L`, `,`/`.` cuadro a cuadro, `R` al inicio, in/out con manijas |
| **Marcar** | `1`–`9` cuartos, `S` igual al anterior, `⏎` paleta, `P`/`X`/`⇧P`, **`↑`/`↓` suben y bajan el estado** |
| **En lote** | marquesina, `⇧`+click, `⌘A`, pincel (mantener `1`–`9` y arrastrar) — y **todo** lo de marcar aplica a la selección |
| **Dos vistas** | `⇥` alterna clip ↔ hoja, llevando siempre al clip actual, con transición animada |
| **Proxies** | **a mano**: eliges el de un clip y del par sale el patrón para los demás |
| **Entregar** | `⌘E` exporta el manifest; el plugin arma el proyecto |

### Arquitectura

```
MainWindow  (ui/main_window.py)   — ensambla y orquesta; TRES filas y ninguna más
├── TitleBar    (ui/title_bar.py)    36 px — proyecto, switch Clip│Hoja, Proxies, Exportar
├── cuerpo
│   ├── RoomRail   (ui/room_rail.py)    200 px
│   ├── VideoStage (ui/video_stage.py)  ancho calculado — video + overlays
│   ├── ToolColumn (ui/tool_column.py)   56 px
│   └── ClipSheet  (ui/clip_sheet.py)   resto — hoja de contactos
├── RoomPalette (ui/room_palette.py)
└── StatusBar   (ui/status_bar.py)   24 px
```

Lógica pura, sin Qt: `history.py`, `filters.py`, `rooms.py`, `keyboard.py`,
`player.py`, `probe.py`, `proxy_match.py`, `binarios.py`, `ingest.py`.

## 3. Tu primera tarea: la importación por bins

**No tiene spec ni plan. Empieza por el brainstorm con Bruno**, porque es un
cambio de estructura y hay una decisión de fondo sin tomar.

Lo que pidió, textual:

> «No me encanta la importación. Es difícil importar archivos individuales,
> solo se pueden carpetas. No se distinguen entre carpetas o cámaras. Me
> gustaría que fuera tan fácil como drag and drop en bins, como en Premiere. Y
> de esa forma los videos que estén en ciertos bins ya sé que son de Sony,
> otros ya sé que son de un dron. Poder hacer clic derecho en esos bins y
> enlazar los proxies. También meter los LUTs a esos videos.»

**Por qué el fondo del pedido es correcto, y no solo comodidad:** el proxy y el
LUT son propiedades **de la cámara**, no del clip suelto. El LUT de S-Log de la
FX30 no va sobre material del dron. Hoy no hay forma de decir «estos 23 son del
dron», y por eso enganchar proxies es un gesto por shooting entero en vez de
por fuente.

**Media pieza ya existe, sin interfaz**: `ingest.py` guarda cada carpeta
importada por separado, con nombre editable (`IngestFolder.display_name`,
`rename_folder`). El rediseño quitó el panel que las mostraba; el dato quedó.

**La decisión de fondo, que es de Bruno y no del código:** la hoja de contactos
**agrupa por cuarto**. Las fuentes son un segundo eje. Si las fuentes también
agrupan, hay dos jerarquías compitiendo en la misma vista. La salida más
probable es que **la fuente sea un filtro y una etiqueta, no una agrupación** —
pero eso se pregunta, no se asume.

**Y una advertencia de alcance**, escrita en `CONTEXTO-Y-METAS.md`: no se trata
de reconstruir el panel de proyecto de Premiere con jerarquía y arrastre
anidado. Se trata de saber de qué cámara viene cada clip y poder actuar por
cámara.

## 4. Lo demás que está abierto

| Qué | Estado | Quién sigue |
|---|---|---|
| **Proxies del dron** | medido y decidido: el `.LRF` **no sirve** ni renombrado (contenido corrido 1–5 cuadros, variable por clip). Hay que generarlos del original: ~10 s por cada 6 s de video | falta escribir la función; Bruno ya dijo que sí |
| **LUT en Premiere** | alcanzable: la API deja poner efectos al *master clip* sin armar secuencia | falta un spike DENTRO de Premiere: ¿el LUT de entrada de Lumetri acepta una ruta? |
| **Etiqueta dorada de la estrella** | escrita (`destacado→MANGO`) con guarda si el nombre no existe | falta correr `autocheck-tests.js` en Premiere |
| **Empaquetado** | `.app` de 175 MB que arranca sin Homebrew; 0 de 214 binarios apuntan a Homebrew | falta abrirlo **en otra Mac**, por USB |
| **`.LRF` como clips** | DJI escribe un `.LRF` junto a cada `.MP4` y el ingest los toma como material: cada toma del dron aparece **dos veces** | decisión de Bruno: ¿fuera, como los `S03`? |
| **Caída al cerrar** | una de ~30 corridas murió **después** de pasar los 831 tests, en el apagado. 26 corridas seguidas no lo repitieron | anotado, sin arreglo inventado |

## 4.b Lo que ya se midió, para no volver a medirlo

Dos conclusiones de arriba costaron trabajo y se re-litigarían solas si solo
quedara escrito el veredicto.

### Por qué el `.LRF` del dron no sirve como proxy

El `.LRF` **ya es un MP4 por dentro** (mismo contenedor, H.264 720p), así que
renombrarlo lo deja perfectamente reproducible. El problema es otro: **el
contenido no está alineado con el original.**

Medido sobre la carpeta real de dron de Bruno, 23 pares:

- **fps idéntico en los 23**, y el `.LRF` **nunca es más largo**: le faltan
  entre 0 y 3 cuadros al final.
- Pero comparando imagen contra imagen —extraer el mismo cuadro de los dos y
  medir la diferencia media de píxel— el mejor calce **no cae en el mismo
  número de cuadro**: en el clip `0009` el cuadro 500 del original se parece
  más al **505** del `.LRF`; en el `0006`, a **+1**. En un clip casi estático
  la curva sale plana y el método no concluye — por eso se midió en varios.
- Comparando por **tiempo** en vez de por cuadro pasa lo mismo, así que no es
  un artefacto de cómo se numeran los cuadros: es el contenido.

**Consecuencia:** para *ver* da igual; para **marcar in/out** no, porque el
desfase cambia de clip a clip. Y la validación que ya tiene la app los
rechazaría igual.

**La alternativa medida**, generando el proxy desde el original con el
codificador del chip (`h264_videotoolbox`, lado corto 720):

| | original | proxy generado |
|---|---|---|
| tamaño | 285 MB | 17 MB |
| cuadros | 1010 | **1010, exactos** |
| tiempo | — | ~10 s por cada 6 s de video |

Ojo con un detalle que costó una medición equivocada: **los MP4 del dron traen
una miniatura JPEG incrustada como segunda pista de video**, y sin `-map 0:v:0`
ffmpeg transcodifica esa en vez del video.

### Qué hace falta para repartir la app

El detalle operativo vive en el `README.md` (sección «Empaquetar como app»), y
lo que hay que saber para decidir es:

- La **firma propia** (ad-hoc) es gratis, se hace sola al armar, y es lo que el
  chip M exige para que un binario arranque. Ya está puesta.
- La **firma de Apple** (99 USD/año) NO hace falta para el caso de Bruno.
- **Por USB o carpeta compartida la app abre directo.** Mandada por internet,
  la primera vez hay que ir a *Configuración → Privacidad y seguridad → Abrir
  de todos modos*, y eso se repite con cada versión nueva.
- Esto es **cómo funciona macOS 26 según la documentación de Apple, no
  comprobado**: la única prueba válida es abrirla en otra computadora.

## 5. Cómo encontrar bugs en este proyecto

Lo que funcionó, **ordenado por lo que realmente encontró**. Casi ningún bug de
los últimos meses lo detectó la suite.

| Detector | Qué encontró |
|---|---|
| **Que Bruno la use con su material** | Las portadas que no se generaban nunca, el borde invisible del clip actual, la marquesina que no marcaba pick, los verticales dibujados horizontales, los ventiladores |
| **Mirar el píxel, no el estilo** | El borde de estado: la regla de QSS era correcta y **nunca llegó a la pantalla**, tapada por la miniatura. Los tests comprobaban la cadena de texto |
| **Montar la app COMPLETA al medir** | Los tests de UI no aplicaban la hoja de estilos, y sin ella los controles miden el doble. Costó un diagnóstico entero y un arreglo mal justificado |
| **Empaquetar** | Que `ffprobe` y `mpv` se buscaban por nombre, y que ese fallo era invisible: importaba 0 clips sin decir nada |
| **Perfilar con cProfile** | Tres veces trabajo desperdiciado que nadie sospechaba |
| **Comparar la fase contra lo PROMETIDO** | Que la marquesina faltaba: un plan recortó el alcance en silencio |
| **Estados límite y datos degenerados** | El rango invertido, cuatro veces — la última, exportándose crudo a Premiere |
| **Recorrido aleatorio con invariantes** | Nada, en 7 600 pasos. Vale como red, no como detector |

### Cuatro trampas de medición que ya costaron tiempo

1. **Un arnés que no monta la app completa mide otra app.** (La hoja de estilos.)
2. **Contar widgets sin procesar `DeferredDelete`** da falsas fugas.
3. **Un doble de pruebas puede tapar el bug que existe.** (`frame-step` pasaba
   su test *por* la línea que lo rompía.)
4. **Leer `.text()` sin mirar `isHidden()`** convierte un widget escondido en
   un falso bug.

## 6. Trampas concretas del código

### De Qt

- **La regla global `QWidget { background-color }` alcanza a las QLabel.**
  Cualquier etiqueta sobre algo pintado declara `transparent`.
- **Un `QWidget` puro ignora `background-color` de QSS** sin `WA_StyledBackground`.
- **El QSS de un widget NO se ve si un hijo lo tapa.** El borde de la tarjeta
  vivió cinco fases sin dibujarse. Si algo tiene que verse encima de una
  imagen, se pinta en el `paintEvent`, no con QSS.
- **Un `QShortcut` consume la tecla y nunca avisa de que se soltó.** Por eso
  `1`–`9` NO son atajos: con ellos el pincel no se arma.
- **`setStyleSheet` es carísimo**: nunca llamarlo si el estilo no cambió.
- **Sin la hoja de estilos, Qt le da a cada `QPushButton` 80 px de ancho
  mínimo.** Medir sin ella da números de otra app.
- **`qtbot.addWidget` no muestra el widget.** Sin `show()` el layout no corre.

### De macOS

- **Las rutas de socket Unix se cortan en 104 caracteres.** El socket de las
  miniaturas vivía en el caché y medía 108: **la extracción falló siempre**.
- **`settimeout` + `makefile()` no se mezclan**: en cuanto vence un timeout, el
  objeto de archivo queda inservible. Se espera con `select`.
- **Los binarios se buscan con `binarios.ruta_de()`**, nunca por nombre: dentro
  del `.app` no están en el PATH.

### De este proyecto

- **`item_widgets` va por índice de clip, no por posición visual**, y agrupar
  es **re-colocar, jamás reconstruir**.
- **Dos vistas del mismo dato se contradicen solas.** Van siete veces.
- **Los tamaños y duraciones van por índice**, así que `load_clips` los limpia
  igual que al historial.
- **`categoria_path` sigue siendo una LISTA** aunque los cuartos sean planos, y
  el plugin **ignora lo que no conoce**.

## 7. Cómo trabajar

- **Español mexicano en todo**: chat, commits, docs, comentarios y sobre todo
  los textos de la app.
- **En el chat, corto y sin lenguaje técnico.** Bruno es editor, no
  programador: qué cambió y qué va a ver él.
- **Se trabaja directo sobre `master`.**
- **Higiene de archivos**: nada suelto en la raíz; un archivo nuevo que
  reemplaza a otro se acompaña de borrar el viejo en el mismo commit.
- **No agregues funciones que no estén acordadas.** Si el mockup o
  `DECISIONES.md` no cubren un caso, se pregunta.
- **No borres tests en bloque.** Clasifica cada uno: *se reescribe*, *murió a
  propósito*, o *se conserva*.
- **Verificación visual real**: si no se miró la imagen, no se afirma.
- **Audita el plan ejecutando, pero después implementa.** Lo que queda por
  descubrir sale de construir.
