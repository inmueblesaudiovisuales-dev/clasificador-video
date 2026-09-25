# Spec: optimizaciones de rendimiento confirmadas (2026-09-25)

Siete cambios, todos ya investigados y medidos en una sesión de
brainstorm/investigación previa (no un brainstorm nuevo — ver la sección
de evidencia). Bruno aprobó la dirección de cada uno en el chat antes de
este documento; aquí se fija el diseño concreto para que la implementación
no tenga que volver a decidir nada.

## Evidencia (no repetir la investigación, solo referenciarla)

- `docs/superpowers/RESULTADO-2026-09-25-miniaturas-vs-premiere.md` — #1
- `docs/superpowers/RESULTADO-2026-09-25-optimizacion-general.md` — #2, #3, #5, #6
- `docs/superpowers/RESULTADO-2026-09-25-optimizacion-tercera-ronda.md` — #3, #4

## 1. Miniaturas: seek por keyframe, sin decodificar de más, sin audio

**Archivo:** `src/clasificador_video/thumbnails.py`

- `build_strip_ipc_args`: agregar `--vd-lavc-skipframe=nonkey` y
  `--no-audio` al comando.
- `extract_thumbnail_strip`: cambiar el seek de
  `conn.command(["seek", at_seconds, "absolute"])` a
  `conn.command(["seek", at_seconds, "absolute+keyframes"])`.
- `build_thumbnail_command` (camino de respaldo cuando no se conoce la
  duración, usado por `extract_thumbnail`): agregar `--hr-seek=no` y
  `--vd-lavc-skipframe=nonkey`. Ya tiene `--no-audio`.
- No agregar `--vd-lavc-skiploopfilter=all`: medido sin ganancia (dentro
  del ruido de la medición).
- No tocar `HILOS_DE_MINIATURAS_NORMAL` / `STRIP_COUNT` / cuántas fotos
  pide la tira — eso queda fuera de este spec (Bruno lo dejó como
  pregunta abierta para explorar después, no para este cambio).

**Medido:** 4.07s → 0.83s por clip aislado (tira de 12, clip de 6s);
15.1s → 4.4s en condición real de 3 hilos en paralelo (12 clips). El
video resultante puede repetir cuadros cuando el clip tiene menos
keyframes que fotos pedidas — aceptado explícitamente por Bruno.

**Documentar en el código:** un comentario junto al cambio, mismo estilo
que el resto del archivo, citando estos números con fecha.

**Tests:** `tests/test_thumbnails.py` ya afirma sobre las listas de
comando exactas (`build_strip_ipc_args`, `build_thumbnail_command`) —
actualizar esas aserciones para reflejar los flags nuevos. TDD: escribir
primero el assert con el flag nuevo, ver el test fallar, luego el cambio.

## 2. Proxies: decodificar con el chip

**Archivo:** `src/clasificador_video/proxy_gen.py::comando`

Insertar `["-hwaccel", "videotoolbox"]` en la lista de argumentos, antes
del primer `-i` (es decir, antes de `"-i", str(original)`).

**Medido:** verificado con `framemd5` sobre los tres clips de
`sample-media/clips/` — salida idéntica cuadro por cuadro. CPU acumulada
de FFmpeg: ~34s → ~16s en el clip de 6s (mitad). Reloj: ~4.6% menos.

**Documentar en el código:** comentario con estos números, mismo criterio
que el resto del archivo (ya cita mediciones con fecha).

**Tests:** `tests/test_proxy_gen.py` tiene un test sobre la lista exacta
de `comando(...)` — actualizar esa aserción.

## 3. Exportar a Premiere sin bloquear la interfaz

**Archivos:** `src/clasificador_video/ui/main_window.py`
(`_on_generar_prproj`, y donde se registran las acciones que llaman
`self._autosave()` — son las que cambian el documento: asignar cuarto,
marcar pick/reject/destacado, renombrar, mover a un bin, deshacer, etc.)

**Diseño:**

1. Un `QRunnable` nuevo (mismo patrón que `_AutosaveWriteJob` /
   `_ThumbnailJob`), corrido en un `QThreadPool` propio de un hilo — igual
   que `_generacion_pool` para proxies, para no competir con las otras
   tandas de fondo. El manifest (`self._armar_manifest()`) se arma en el
   hilo principal ANTES de lanzar el trabajo, y es lo único que ese
   trabajo recibe: es la "foto" congelada del proyecto en ese instante.
2. Mientras el trabajo corre, la ventana entra en un estado
   `self._exportando = True`. Las acciones que hoy llaman
   `self._autosave()` (cambian el documento) se revisan al entrar: si
   `self._exportando`, no hacen nada y muestran un aviso breve ("Espera a
   que termine de exportar") en vez de aplicarse. Navegar la hoja, ver el
   visor, moverte con las flechas SIGUEN funcionando — no cambian el
   documento.
3. Al terminar (éxito o error), señales igual que `_AutosaveWriteJob`
   (`guardado_listo`/`guardado_fallo`, o un par nuevo específico de
   exportación) devuelven la ventana a `self._exportando = False` y
   muestran el mismo diálogo de éxito/error que hoy (`QMessageBox`).
4. Si la ventana se cierra con una exportación en vuelo: mismo criterio
   que ya existe para proxies/miniaturas — el pool es hijo de la ventana,
   su destructor espera el trabajo en curso.

**Por qué bloquear en vez de dejar editar:** decisión explícita de Bruno
después de ver el trade-off — dejar editar libremente arriesga que el
`.prproj` mezcle datos de antes y después de un cambio a medias, según en
qué momento exacto cada sondeo (ffprobe) leyó cada clip. Bloquear solo la
escritura (no la navegación) evita eso sin perder la sensación de "la app
no se congela".

**Medido:** con 200 clips y proxies, la exportación actual congela la
interfaz por completo ~16s (sin responder a ningún evento). Moverla a un
hilo de fondo no acorta el tiempo total (sigue siendo ~16s), pero el
corte máximo de respuesta baja a ~40ms.

**Tests:** cubrir con TDD: (a) que las acciones de edición no se aplican
mientras `self._exportando` es verdadero y sí se aplican después; (b) que
el manifest que recibe el trabajo de fondo es el de el momento de
iniciar, no uno posterior; (c) que un error de generación no deja la
ventana trabada en modo exportando.

## 4. Escribir el `.prproj` por partes

**Archivo:** `src/clasificador_video/prproj_xml.py::escribir_prproj`

Cambiar de armar la cadena completa en memoria
(`ET.tostring(raiz, encoding="unicode")` concatenada con la cabecera,
codificada a UTF-8 completa, y LUEGO comprimida) a escribir por partes
directo al compresor:

```python
def escribir_prproj(raiz: ET.Element, destino: Path) -> None:
    with gzip.open(destino, "wb") as archivo:
        archivo.write(b'<?xml version="1.0" encoding="UTF-8" ?>\n')
        ET.ElementTree(raiz).write(archivo, encoding="utf-8", xml_declaration=False)
```

El comentario existente sobre por qué se evitan entidades HTML para los
acentos y símbolos (`✓`, `★`, `✕`) se conserva tal cual — este cambio no
toca esa parte, solo CÓMO se serializa.

**Medido:** con un XML real de 500 clips con proxies (8.4MB
descomprimido), verificado byte por byte que el archivo resultante es
idéntico. Pico de memoria temporal de Python: ~46MB → ~3.3MB. Es un poco
más lento en el paso de escritura (~186ms → ~212ms en esa prueba
aislada), una fracción chica frente a los ~16s que domina una exportación
real (los sondeos, no la escritura).

**Tests:** `tests/test_prproj_generador.py` — agregar un test que
compare el XML descomprimido resultante byte a byte contra el que
produce el escritor actual, sobre un caso con acentos y las tres marcas
de estado (para no perder la cobertura del comentario de arriba).

## 5. Construir la hoja una sola vez al abrir un proyecto

**Archivos:** `src/clasificador_video/ui/main_window.py::load_clips`,
`src/clasificador_video/app.py::_poblar_ventana`

**Causa:** `load_clips` siempre termina con
`self._refresh_sheet(force_rebuild=True)` (línea ~2459). `_poblar_ventana`
la llama, y DESPUÉS —porque recién ahí tiene los datos, ver comentario en
`app.py` línea ~212-213— rellena `window._clip_sizes`,
`window._clip_durations`, `window._clip_rotations`, y vuelve a forzar
`window._refresh_sheet(force_rebuild=True)` (línea ~244). Dos
construcciones completas de todas las tarjetas.

**Diseño:** agregar un parámetro a `load_clips`, por ejemplo
`construir_hoja: bool = True`. Con `False`, hace todo lo que hace hoy
(limpiar historial, proxies, bins, índices, abrir el clip actual) EXCEPTO
llamar a `self._refresh_sheet(force_rebuild=True)` al final.
`_poblar_ventana` llama `window.load_clips(clips, construir_hoja=False)`,
rellena los tres mapas como ya hace, y llama
`window._refresh_sheet(force_rebuild=True)` una sola vez, en el mismo
lugar donde ya lo hace hoy (línea ~244). El único otro llamador de
`load_clips` (revisar antes de tocar código: al momento de este spec no
hay otro además de `_poblar_ventana`) sigue usando el default `True` sin
cambios.

**Riesgo:** bajo — un solo llamador adicional a auditar, y el parámetro
tiene un default que preserva el comportamiento actual para quien no lo
pase.

**No medido:** cuánto tiempo real ahorra con la ventana de verdad abierta
(el experimento previo con 229 clips sintéticos y Qt `offscreen` no
representa el costo real de crear widgets Cocoa). Verificar con la app
real antes de dar el cambio por bueno — no basta con que los tests pasen.

**Tests:** contar cuántas veces se llama al método que reconstruye las
tarjetas (mismo patrón que el experimento C de la tercera ronda:
envolver `ClipSheet.set_clips` y contar) durante `_poblar_ventana` con un
proyecto de prueba; debe pasar de 2 a 1.

## 6. Autoguardado: no revisar el peso de clips ya medidos

**Archivo:** `src/clasificador_video/proyecto.py::con_pesos_medidos`

Arreglo mínimo (no el rediseño completo que proponía Codex — descartado
explícitamente por Bruno por el riesgo de perder pesos o confirmar una
revisión vieja, frente a un beneficio hoy invisible en disco local).

Cambiar el bucle que hace `stat()` de cada clip para que **solo mida los
que todavía no tienen un peso conocido** en `pesos` (la combinación de
`previos` + `data.get("bytes")` que ya se arma antes del bucle), en vez
de volver a medir los 200+ en cada guardado:

```python
pesos = _pesos_validos(previos)
pesos.update(_pesos_validos(data.get("bytes")))
for indice, clip in enumerate(data.get("clips") or []):
    if indice in pesos:
        continue  # ya se sabía, no hace falta volver a tocar el disco
    try:
        pesos[indice] = Path(str(clip["ruta"])).stat().st_size
    except (OSError, KeyError, TypeError):
        continue
```

El resto de la función (comentarios, orden de fuentes, conservar en vez
de borrar cuando no se puede medir) queda intacto — esas protecciones ya
están peleadas y no las toca este cambio.

**Medido:** en disco local, 200 `stat()` cuestan 0.27ms — ya es gratis
hoy. El arreglo importa en volúmenes de red/iCloud lentos, sin medir
todavía en ese escenario (no hay uno disponible para probar en esta
sesión).

**Tests:** `tests/test_proyecto.py` (si no existe un test de
`con_pesos_medidos`, crearlo) — verificar que un clip cuyo peso ya estaba
en `previos` o en `data["bytes"]` NO dispara `Path.stat()` (se puede
inyectar una ruta que lance si se llama `.stat()`, o contar llamadas con
un `Path` de prueba).

## 7. Quitar modo económico y modo rápido

**Archivos:** `src/clasificador_video/preferencias.py`,
`src/clasificador_video/ui/pantalla_config.py`,
`src/clasificador_video/ui/main_window.py`, `src/clasificador_video/app.py`

**Decisión de Bruno, con el riesgo aceptado explícitamente:** se quita el
interruptor y TODO el freno que traía modo económico (no solo el tamaño
de miniaturas) — la app siempre corre con lo que hoy es la configuración
"normal": `HILOS_DE_MINIATURAS_NORMAL` (3), `SONDEOS_EN_PARALELO` (8),
`LIMITE_DE_TIRAS_VIVAS_NORMAL`, miniaturas a tamaño completo y tira
completa. **No probado en una Mac con poca RAM** (ej. MacBook Air M1
8GB) — el freno se agregó originalmente pensando en ese caso, y no hay
una máquina así disponible para validar antes de implementar. Riesgo
aceptado por Bruno.

**Qué borrar:**

- `preferencias.py`: `modo_economico`, `guardar_modo_economico`,
  `modo_rapido`, `guardar_modo_rapido`, y la constante `RUTA` sigue
  existiendo solo si algo más la usa (revisar antes de tocar).
- `main_window.py`: `_miniaturas_chicas`, `_hilos_limitados`,
  `_aplicar_freno_de_paralelismo`, `_cambiar_modo_rapido`, y cada lugar
  que las llama (línea 296, 303, 695, 904, 3128, 5252-5253, 5263, 5306,
  5308-5313 al momento de este spec — confirmar contra el código antes de
  editar, puede haber corrido) pasa a usar directo el valor "normal" sin
  condicional.
- `pantalla_config.py`: quitar los controles de modo económico y modo
  rápido de la UI (`economico_check`, `rapido_check`, sus etiquetas,
  las señales `modo_economico_cambiado`/`modo_rapido_cambiado`, y el
  párrafo de ayuda que los explica).
- `app.py`: cualquier lectura de `preferencias.modo_economico()` /
  `modo_rapido()` al poblar la ventana.
- Revisar `STRIP_COUNT_ECONOMICO`, `ANCHO_MINIATURA_ECONOMICO`, el
  parámetro `economico` de las funciones de `thumbnails.py` y
  `proxy_gen.py`: si ya nada los pasa en `True`, es código muerto y se
  borra en el mismo commit (regla del repo: no dejarlo "por las dudas").

**Tests:** borrar `tests/test_preferencias.py` (o la parte que prueba
estas dos funciones), los tests de `pantalla_config.py` que prueban los
checkboxes, y cualquier test de `main_window.py`/`app.py` que fije
`modo_economico`/`modo_rapido`. Revisar que ningún test quede probando
una ruta de código que ya no existe.

## Orden de implementación

1. Miniaturas (#1) y proxies (#2) — independientes entre sí, sin riesgo
   de producto, listos para implementar primero.
2. Escribir el `.prproj` por partes (#4) — acotado, sin depender de nada
   más.
3. Construir la hoja una sola vez (#5) — acotado, un solo llamador.
4. Autoguardado (#6) — acotado.
5. Exportar sin bloquear (#3) — el más grande de los siete, tocar al
   final cuando el resto ya esté en verde.
6. Quitar modo económico/rápido (#7) — al final: toca los mismos
   archivos que #1 (parámetro `economico` de `thumbnails.py`) y que #5
   (`_hilos_limitados` se usa en el límite de tiras vivas), así que
   conviene que esos cambios ya estén asentados antes de borrar el
   código que los rodea.

## Fuera de alcance (explícitamente, no reabrir sin razón nueva)

- Cuántas fotos pide la tira de miniaturas (`STRIP_COUNT`) — pregunta
  abierta de Bruno, no parte de este spec.
- El rediseño completo de autoguardado (separar documento de vista, con
  revisiones) — descartado por riesgo frente a beneficio.
- Las ideas de mayor riesgo de la tercera ronda de investigación
  (deduplicar `libmpv` en el instalador, quitar símbolos de depuración,
  reescribir cómo `prproj_xml.py` arma el grafo de referencias) — Bruno
  pidió explícitamente no meterlas en la lista de trabajo.
- Importación asíncrona — identificada como candidata, sin medir
  todavía, no es parte de este spec.
