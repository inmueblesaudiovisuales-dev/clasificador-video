# Handoff — tres bugs, renombrar proyecto, y unidades sin implementar

**Fecha:** 2026-09-20
**Rama:** `master` (directo, sin branches)
**Estado del repo:** working tree limpio, todo comprometido hasta
`6f4eba3`.

Sigue directo del handoff de la mañana
(`HANDOFF-2026-09-20-reportes-en-vivo-y-diseno-de-unidades.md`, mismo día):
Bruno pidió trabajar los tres bugs reportados en vivo, más renombrar
proyecto, más unidades y departamentos, **omitiendo notas**. Esta sesión
cerró los primeros dos y dejó el tercero listo para retomar.

## Resuelto esta sesión

1. **`5f26abb`** — Miniatura que falla se reintenta sola (una vez; con
   tope, para no reintentar para siempre si el clip de verdad nunca da
   frames). Causa: `_on_thumbnail_ready` no reintentaba nunca un
   `frames is None`, reportado con proxies generándose al mismo tiempo en
   modo rápido. Con pruebas, suite completa revisada.
2. **`c73e4cb`** — Renombrar el proyecto: doble clic en el nombre de la
   barra de título, mismo mecanismo que renombrar un cuarto. Nace de que el
   nombre viaja hasta el nombre de las secuencias en Premiere
   (`secuencia.js` lee `manifest.proyecto`). Spec:
   `specs/2026-09-20-renombrar-proyecto-design.md`. Verificado con
   `grab()` además de las pruebas.
3. **`6f4eba3`** — Registro temporal de diagnóstico para el bug de la fila
   de proxies (ver abajo, sigue sin resolverse — esto es la instrumentación
   para la próxima vez que pase, no el arreglo).
4. **`5eb6ef5`**, **`6239b45`** — Specs escritos y comprometidos: renombrar
   proyecto, y unidades y departamentos (este último cierra las dos
   preguntas que quedaron abiertas de la mañana — ver spec).

Suite completa: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q` —
**5 fallos preexistentes, no relacionados con nada de esta sesión**
(confirmado corriendo la suite en el commit anterior a empezar, con
`git stash`, y dan los mismos 5 fallos ahí):

```
test_cache_hit_no_relanza_mpv
test_modo_economico_baja_los_hilos_y_el_limite_de_tiras
test_modo_economico_baja_cuantos_ffprobe_corren_a_la_vez_al_importar
test_sin_duracion_la_portada_vieja_no_se_re_extrae_cada_sesion
test_una_tira_con_marca_no_se_rehace_aunque_tenga_pocas_fotos
```

Nadie los investigó todavía — quedan para cuando alguien los note en vivo
o se decida a perseguirlos por su cuenta. No son nuevos de hoy.

## Sin resolver — bug de la fila de proxies

Sony-1 generando, Sony-2 en cola, Bruno pidió Drone: Sony-2 perdió su
insignia «en cola» sin generar nada, y Drone arrancó directo, como si la
fila hubiera estado vacía. Por lectura estática se armó una hipótesis
plausible (un `QMessageBox.question` deja correr el hilo de fondo mientras
espera la respuesta, y eso puede mover la fila por debajo de la función que
la está leyendo) pero **no se pudo reproducir con una prueba** que
combinara los dos síntomas a la vez — ver el detalle completo en el
handoff de la mañana.

**Lo que se hizo en su lugar:** instrumentación, no arreglo.
`_log_fila_de_proxies` en `main_window.py` (buscar el comentario que
empieza «registro TEMPORAL») anota cada decisión de la fila —pedido,
diálogo de confirmación abierto/cerrado, arranque, reparto, fin de tanda,
descarte— en `~/.clasificador_video/fila_de_proxies.log`.

**Siguiente paso:** la próxima vez que Bruno pida proxies de varios bins
seguidos y algo se vea raro, revisar ese archivo — va a decir exactamente
qué pasó, en vez de tener que adivinar. Una vez confirmado (o descartado)
el mecanismo real, el arreglo y borrar el log temporal.

## Sin empezar — unidades y departamentos

Spec completo y aprobado en
`specs/2026-09-20-unidades-y-departamentos-design.md`, pero **cero
código escrito**. Es la pieza grande que queda. Resumen de lo que el spec
ya decidió (no reabrir sin razón nueva):

- Nivel nuevo, **opcional**: sin crear ninguna unidad, un proyecto se
  comporta exactamente como hoy — cero fricción para el caso normal de una
  sola propiedad.
- `Clip.categoria_path` pasa a `[unidad, cuarto, ...resto]` cuando hay
  unidad; sigue siendo `[cuarto]` cuando no la hay. Un `UnitSelection`
  nuevo, hermano de `RoomSelection` (`rooms.py`), y una `RoomSelection`
  por unidad.
- Paleta de unidades nueva (`⌘U`/`Ctrl+U`), hermana de `RoomPalette`: a
  diferencia de la paleta de cuartos, elegir una unidad **no cierra la
  paleta** — queda activa y filtra la paleta de cuartos a esa unidad.
- Reasignación en lote de unidad: mismo patrón que ya existe para cuarto
  (`_bulk_target_indices` + una función `_asignar_unidad` análoga a
  `_asignar_cuarto`). **Es el camino de migración** del proyecto actual de
  Bruno (`Cocina-A`/`Cocina-B` a mano) — manual, sin detección automática
  del sufijo, decidido así explícitamente.
- Rail y hoja agrupan por unidad primero, cuarto adentro.
- Color: el mockup ya lo resuelve — swatch cuadrado para unidad (distinto
  en FORMA del swatch de cuarto, una franja delgada). `UNIT_PALETTE` +
  `unit_color()` nuevos en `theme.py`.
- Plugin UXP: tres módulos generalizarse de un nivel fijo a dos —
  `estructura.js::caminoDelClip`, `marcaCamara.js`, `numeroDeCuarto.js`.
  Con `categoria_path` de un solo elemento (proyecto sin unidades), los
  tres se comportan igual que hoy sin caso especial que mantener.
- **Fuera de alcance, explícito**: notas (feature aparte), recorrido/guía
  de edición por unidad («ahorita ni jala bien», palabras de Bruno —
  primero hay que arreglar la guía en sí), migración automática del sufijo
  `-A`/`-B`, menú contextual de unidad.

**Siguiente paso:** invocar `writing-plans` sobre ese spec para armar el
plan de implementación (archivo de tareas, TDD), y ejecutarlo. Bruno
aprobó el diseño; falta literalmente el plan y el código.
