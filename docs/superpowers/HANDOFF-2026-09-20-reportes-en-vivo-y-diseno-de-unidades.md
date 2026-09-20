# Handoff — reportes en vivo mientras Bruno generaba proxies, y diseño de unidades

**Fecha:** 2026-09-20
**Rama:** `master` (directo, sin branches)
**Estado del repo:** working tree limpio salvo un archivo nuevo SIN comprometer:
`docs/superpowers/mockups/2026-09-20-unidades-y-departamentos/mockup.html`
(el mockup de unidades, ya aprobado por Bruno — falta el `git add`+commit).

## De dónde sale esta lista

Bruno estaba generando proxies de un shooting real y fue reportando cosas
conforme las notaba, en el mismo chat, sin pausar lo que tenía corriendo.
Pidió explícitamente **no tocar código** mientras tanto salvo lo que se
alcanzó a resolver antes de que empezara a usar la app (ver primer bloque).
Todo lo demás quedó en investigación o en diseño, sin implementar.

## Resuelto esta sesión (antes de que Bruno empezara a generar proxies)

1. **`a2ab028`** — Acceso a Configuración desde la pantalla de inicio: un
   engrane arriba a la derecha, abre la misma `PantallaConfig` de siempre.
   Spec: `specs/2026-09-20-configuracion-desde-inicio-design.md`.
2. **`6631b7a`** — Ese mismo panel salía amontonado sobre la pantalla de
   inicio (560×480, mucho más chica que una `MainWindow` maximizada):
   `heightForWidth` calcula el alto real que hace falta y crece la ventana
   de inicio lo necesario, devolviéndola a su tamaño de siempre al cerrar.
   Reportado por Bruno con captura; arreglado y verificado con `grab()`.

Los dos con pruebas nuevas y la suite completa en verde. Ya en GitHub.

## Bugs reportados en vivo, SIN resolver — quedan para la próxima sesión

### 1. La fila de proxies se vació sola

Bruno tenía **Sony-1** generando, **Sony-2** en cola. Pidió proxies de
**Drone**. Resultado: Sony-2 perdió su insignia "en cola" y quedó en "sin
proxies" (nunca generó nada), y Drone arrancó a generar directo, como si la
cola hubiera estado vacía.

**Descartado como causa:** un renombrado de bin mientras espera turno
(`_aplicar_renombrado_de_bin` no actualiza `self._cola_de_proxies`, que
guarda nombres por texto — es un bug real y sigue ahí, pero Bruno confirmó
que no renombró nada, así que no fue esto).

**Sigue sin confirmarse:** el único otro camino real que encontré en el
código para que la fila ENTERA se vacíe en silencio es
`_descartar_generacion_de_proxies` (`main_window.py:3461`), que se dispara
al "Quitar del proyecto" un bin, o al abrir/cargar otro proyecto
(`load_clips`, línea 2085). Bruno no confirmó ni negó si hizo alguna de las
dos cosas justo en ese momento — **preguntárselo de nuevo** antes de seguir
buscando. Si tampoco fue eso, hace falta reproducirlo en vivo con un log
temporal en `_arrancar_siguiente_de_la_fila` y `_descartar_generacion_de_proxies`
para agarrarlo con datos reales; por lectura estática ya no hay más
candidatos razonables.

### 2. Miniaturas que faltan en modo rápido

Causa raíz **sí identificada**, no arreglada:

- `_on_thumbnail_ready` (`main_window.py:4349`) no reintenta nunca un clip
  cuya extracción falló (`frames is None`): se limpia el registro de "en
  vuelo" y ahí se queda, para el resto de la sesión (reabrir el proyecto sí
  lo reintenta, porque `_schedule_thumbnails` sin `indices` vuelve a barrer
  todo).
- Modo rápido corre 3 extracciones en paralelo (`HILOS_DE_MINIATURAS_NORMAL
  = 3`, línea 295) en vez de 1 (económico), cada una abriendo su propio mpv
  con un socket IPC y un timeout de conexión de 2 segundos
  (`thumbnails.py::_connect_ipc`). Bajo carga —como generar proxies al
  mismo tiempo, que usa el mismo chip de video— es más fácil que alguna de
  esas conexiones se tarde de más y falle.

**El arreglo natural:** que una extracción fallida se vuelva a encolar en
vez de abandonarse. No se tocó porque Bruno pidió no tocar código mientras
generaba; queda listo para retomar directo a implementación (no hace falta
brainstorm, es un bug claro).

### 3. Flechas que no seleccionan en la paleta de cuartos (`⏎`)

**No se pudo reproducir.** Se armó la `RoomPalette` aislada y también
dentro de una `MainWindow` real completa (con sus atajos de teclado
armados), se escribió texto para filtrar a 2-3 coincidencias, se mandó
`QTest.keyClick(Qt.Key.Key_Down)` sobre el campo de texto, y en las dos
pruebas la selección se movió y el resaltado cambió de fila (comprobado
también leyendo el color de fondo renderizado, no solo el estado interno).

Bruno confirmó "sí, todo eso" a: es la paleta de `⏎`, escribe antes de usar
las flechas, y las flechas no hacen nada. Como no se pudo reproducir, se le
pidió un dato más para la próxima vez que lo tenga enfrente: **¿las teclas
numéricas (1, 2, 3) sí seleccionan directo, aunque las flechas no?** Esa
respuesta todavía no llegó. Si los números tampoco funcionan, el problema
es que la ventana completa no está agarrando el teclado como debería (algo
de foco/activación real de macOS que un test headless no puede ver); si los
números sí funcionan, es algo específico de `Key_Down`/`Key_Up`.

## Pendiente técnico (no es un bug de código)

**El plugin de Premiere instalado está desactualizado.** Se investigó por
qué "la marca de cámara en las carpetas de cuartos" (`marcaCamara.js`,
commit `899925d`, ya en el repo) no le funcionaba a Bruno: revisando
`~/Library/Application Support/Adobe/UXP/Plugins/External/` en su Mac hay
DOS versiones instaladas (`com.iav.clasificadorvideo_1.6.0` y `_1.3.0`) y
**ninguna de las dos tiene el archivo `marcaCamara.js`** — su plugin
instalado es de antes de que esa función se agregara, aunque el número de
versión (1.6.0) coincida con el que dice hoy `uxp-plugin/manifest.json`
(no se bumpeó al agregar esa función).

Bruno pidió armar el `.ccx` nuevo (`./uxp-plugin/empaquetar.sh`) y luego
dijo "mejor al final" — **no se corrió todavía**. Queda pendiente correrlo
e instalarlo (doble clic, Creative Cloud lo toma solo) antes de que Bruno
vuelva a probar cualquier cosa relacionada con Premiere, o las próximas
funciones (unidades, notas) van a tener el mismo problema.

## Features en brainstorm — diseño acordado, SIN spec escrito

Bruno pidió explícitamente no escribir el spec todavía ("primero hagamos el
diseño"). Los tres quedaron en este punto:

### 4. Renombrar el proyecto de Clipify

Solo mencionado, sin ninguna decisión de diseño tomada. Retomar desde cero
cuando Bruno quiera.

### 5. Nota en el clip

Diseño conversado y acordado, sin documento:

- Clic derecho sobre uno o varios clips seleccionados → "Agregar nota…" →
  texto libre. Con varios seleccionados, la misma nota se les pone a todos.
- Una nota por **clip completo**, no por rango in/out.
- Indicador en los DOS lados: un símbolo nuevo (dedicado a "tiene nota", NO
  reemplaza ★/✓/✕ — conviven) en la tarjeta de Clipify, y otro en el nombre
  del clip en Premiere.
- La nota en sí, del lado de Premiere, va al campo **Log Note** del
  `ProjectItem` — se ve como columna en el panel de Proyecto sin abrir el
  plugin. **Sin confirmar todavía que ese campo sea escribible desde la API
  de UXP** — hace falta probarlo en vivo antes de comprometerse en el spec
  (mismo criterio que ya está en `CLAUDE.md` sobre no confiar en la
  documentación de Adobe: enumerar el prototipo real antes de llamar).

### 6. Unidades y departamentos (multi-unidad por proyecto)

Caso real de Bruno: dos casas modelo en una colonia, hoy resuelto a mano con
sufijos (`Cocina-A`, `Cocina-B`). Quiere un nivel de verdad arriba del
cuarto. Diseño completo, con mockup **aprobado** (visto en pantalla, colores
reales de `theme.py`) en
`docs/superpowers/mockups/2026-09-20-unidades-y-departamentos/mockup.html`
— **todavía sin comprometer a git**.

Decisiones ya tomadas en la conversación:

- Nivel nuevo **unidad**, arriba de cuarto (Casa A / Casa B, o Depto 1 / 2).
- Paleta de unidades nueva, tecla dedicada — hermana de la paleta de
  cuartos (`⏎`) un nivel arriba: la abres, eliges o creas la unidad, se
  queda **activa** y de ahí en adelante solo eliges el cuarto.
- La paleta de cuartos, con una unidad activa, **filtra** y solo ofrece los
  cuartos de esa unidad — "Cocina" de Casa A y "Cocina" de Casa B no se
  mezclan ni chocan.
- Además de la paleta, se puede **seleccionar clips ya clasificados en la
  hoja y reasignarles la unidad en lote** — no solo por el flujo de
  "unidad activa + avanzar por cuarto".
- Rail y hoja se agrupan **por unidad primero, cuarto adentro** — mismo
  orden que las carpetas en Premiere.
- En Premiere: `02. Clip > 1. Casa A > 1. Cocina`, `02. Clip > 2. Casa B >
  1. Cocina`, etc. — **las carpetas de unidad también se numeran** (recién
  confirmado por Bruno) para controlar su orden, igual que ya pasa con los
  cuartos.
- La carpeta de la unidad **también** debería llevar la marca de cámara
  (`[SONY]`/`[DRONE]`/combinada), igual que ya llevan las de cuarto — esto
  es una extensión de `marcaCamara.js`, no existe todavía a ese nivel.
- Cada unidad probablemente necesita su **propio recorrido/guía de
  edición** (una Casa A con su patrón, una Casa B con el suyo) — mencionado
  pero no cerrado del todo, revisar con Bruno al escribir el spec.
- El proyecto ACTUAL de Bruno (con `Cocina-A`/`Cocina-B` a mano) **también
  se debe convertir** a unidades reales cuando la función esté lista — no
  es solo para proyectos nuevos. Falta diseñar cómo se hace esa migración
  (¿detecta el sufijo `-A`/`-B` sola, o Bruno la arma a mano una vez?).

**Siguiente paso cuando Bruno quiera retomar:** terminar de cerrar el
recorrido-por-unidad y la migración del proyecto actual, y ahí sí escribir
el spec formal en `docs/superpowers/specs/`.

## Nota de proceso para la próxima sesión

Durante buena parte de esta sesión Bruno pidió explícitamente usar las
herramientas de investigación directamente (`Read`/`Bash`/`Grep`) en vez de
delegar a subagentes — "hazlo tu wey". Mantener ese criterio si se retoma
en caliente con él mirando.
