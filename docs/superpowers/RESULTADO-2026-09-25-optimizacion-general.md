# Investigación de optimización general de Clipify

Fecha: 2026-09-25. Autor: GPT-6 (Codex).
Base revisada: `master`, commit `c0f3449841e6ca323c13c62237ec56838dfc2133`.
Alcance: investigación y experimentos aislados; **sin cambios a la aplicación**.

## Qué conviene investigar primero

Hay oportunidades fuera de la extracción de miniaturas. Las primeras serían:

1. **Bajar el trabajo de CPU al generar proxies.** Una prueba nueva con material real redujo los segundos de CPU aproximadamente 52%, aunque el tiempo de espera solo mejoró 4.6%. Falta validar calidad y uso simultáneo con la app.
2. **Quitar trabajo del autoguardado que no corresponde a una edición.** Seleccionar clips dispara guardados; cada escritura relee el proyecto y vuelve a medir todos los originales. Ya sucede en segundo plano, pero sigue gastando recursos y puede retrasar la persistencia.
3. **Evitar sondeos repetidos y bloqueos al exportar a Premiere.** La exportación sondea otra vez cada original y cada proxy, en serie, desde el hilo de la interfaz.
4. **Abrir el proyecto sin construir dos veces todas las tarjetas.** La duplicación está confirmada, incluso con un experimento de 229 clips. Su impacto visible todavía no está medido.
5. **Sacar del hilo de la interfaz la espera de importación y la consulta del cache.** Tener ocho sondeos paralelos no vuelve asíncrona la llamada que espera sus resultados.

No sumes las mejoras como si fueran independientes: compartir metadata afecta importación, guardado, exportación y cache; virtualizar la hoja se traslapa con cargar únicamente portadas visibles. Tampoco hay una cifra honesta de «la app será X veces más rápida» con la evidencia disponible.

## Decisiones respetadas y alcance de la evidencia

Se leyeron primero:

- [Investigación de miniaturas del 25 de septiembre](RESULTADO-2026-09-25-miniaturas-vs-premiere.md).
- [Contexto y metas](CONTEXTO-Y-METAS.md).
- [Investigación de RAM y CPU del 13 de septiembre](archive/RESULTADO-2026-09-13-ram-y-cpu-en-reposo.md).
- `CLAUDE.md`, el código actual y las specs posteriores que cambian decisiones antiguas.

**No se repitieron** las pruebas de seek por keyframe, salto de cuadros no-clave, paralelismo de miniaturas, miniatura incrustada ni escalado gráfico de esa investigación. No se propone subir de tres extracciones simultáneas. Las mejoras anteriores siguen siendo una línea de trabajo separada; cualquier comparación futura debe mantenerlas iguales en ambos lados.

Se conservan la lectura reducida con `QImageReader.setScaledSize`, la carga diferida de las tiras, el límite de 24 tiras vivas y la comprobación antes de repintar el playhead. Proponer «hacer lazy las tiras» como novedad sería repetir lo ya resuelto. Borrar portadas de RAM tampoco explica los cientos de MB restantes según la medición anterior.

Hay decisiones **más nuevas** que el contexto de agosto:

- [Entrega del 18 de septiembre, §2](specs/2026-09-18-entrega-a-editor-externo-design.md): los proxies conservan las dimensiones del original para que el editor externo pueda reconectar sin cambiar encuadres. **No se recomienda volver a 720p para los proxies entregables.**
- El comando actual agrega una marca y conserva audio. Que Clipify sea silencioso no autoriza quitar audio del material que recibe Premiere.
- El código actual genera `.prproj` directamente y tiene rutas de proyecto/proxies en iCloud. Las referencias antiguas a plugin UXP y «nada en la nube» no describen todo el flujo actual.
- `_on_proxy_generado` y `_sondear_proxies` documentan una preferencia expresa: las miniaturas del bin se solicitan al terminar su tanda de proxies. Mostrar resultados a mitad de esa tanda sería un cambio de producto, no una optimización transparente.
- El modo rápido de miniaturas ya existe. No se presenta como idea nueva.

**Etiquetas usadas:** «confirmado» describe una ruta de código o un resultado observado; «hipótesis» describe una mejora pendiente. Confianza alta/media/baja se refiere a que la idea produzca el beneficio indicado, no a que ya esté lista para instalar. Impacto alto/medio/bajo es relativo al escenario señalado, sin porcentajes inventados.

## Mediciones nuevas y reproducibles

### A. Proxies: pedir decodificación por VideoToolbox

Entorno observado: macOS 27.0 arm64, Python 3.14.6, PySide6 6.11.1; FFmpeg/ffprobe 8.1.2 de `/opt/homebrew/bin`, mpv 0.41.0. **No se midió el ejecutable empaquetado ni otra Mac.**

Entrada: `sample-media/clips/20260804_PIB0589.MP4`, Sony FX30, HEVC 4K, 6.006 s, 59.94 fps, rotación 90°, con audio. Las dimensiones de despliegue son 2160×3840.

Se generó el comando mediante `proxy_gen.comando`, sin modificar su código. La variante agregó únicamente `-hwaccel videotoolbox` **antes del primer `-i`**. Se conservaron el overlay, H.264 VideoToolbox a 6M, AAC a 128k y el contenedor MP4. Cada salida fue temporal, fuera del repo, y se eliminó después de inspeccionarla.

Orden de las seis corridas: actual, variante, variante, actual, actual, variante. Una transcodificación a la vez. Tiempo con `time.perf_counter()`; CPU con la diferencia de `resource.getrusage(RUSAGE_CHILDREN)` inmediatamente alrededor de FFmpeg, **sin incluir el ffprobe posterior**. El sondeo de los tres clips de muestra coincidió con parte del experimento: no fue una máquina aislada de toda otra actividad. No se vació el cache del sistema operativo.

| Comando | Reloj, tres corridas | CPU acumulada, tres corridas | Mediana reloj | Mediana CPU |
|---|---|---|---|---|
| Actual | 4.256 / 4.232 / 4.245 s | 33.854 / 34.052 / 33.989 s | 4.245 s | 33.989 s |
| Con `-hwaccel videotoolbox` | 4.052 / 4.019 / 4.048 s | 16.734 / 16.315 / 16.099 s | 4.048 s | 16.315 s |

Resultado: **4.6% menos tiempo de reloj y 52.0% menos segundos de CPU** en este caso. CPU acumulada puede superar al reloj porque suma varios núcleos. No equivale a 52% menos electricidad, calor o batería: eso no se midió. Tampoco demuestra un ahorro de RAM.

Las seis salidas terminaron con código 0; todas midieron 4,729,599 bytes y reportaron 2160×3840, `60000/1001`, duración 6.006 s, formato `yuvj420p` y **360 cuadros decodificados** mediante `ffprobe -count_frames`. Igual tamaño no prueba igualdad de contenido. No se compararon píxeles, audio, color ni correspondencia temporal cuadro por cuadro; no se abrió el resultado en Premiere. Por eso es una candidata fuerte para ahorrar CPU, **no una implementación validada**.

Reproducción mínima: ejecutar `proxy_gen.comando(original, salida_temporal)` como base; en la variante insertar `['-hwaccel', 'videotoolbox']` en la posición 2 de esa lista. Alternar ambas al menos tres veces; medir proceso completo y verificar con:

```text
ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,nb_read_frames,pix_fmt,duration \
  -of json SALIDA.mp4
```

La aceleración de decodificación es una opción de entrada, distinta del codificador de salida; FFmpeg también advierte que transferir cuadros entre hardware y memoria puede borrar la ganancia de velocidad. Eso concuerda con el resultado, pero no identifica por sí solo todo el costo restante. [Documentación oficial de FFmpeg](https://www.ffmpeg.org/ffmpeg.html#Advanced-Video-options).

### B. Sondeo de los tres clips de muestra

Cinco llamadas secuenciales a `probe_clip` por archivo, sin cambiar flags:

| Archivo | Duración | Tiempos de sondeo en ms |
|---|---|---|
| `20260804_PIB0587.MP4` | 2.002 s | 38.70 / 41.11 / 40.82 / 37.48 / 37.48 |
| `20260804_PIB0588.MP4` | 4.004 s | 35.82 / 32.35 / 32.06 / 38.33 / 33.61 |
| `20260804_PIB0589.MP4` | 6.006 s | 37.53 / 37.00 / 37.40 / 36.24 / 37.67 |

Esto mide proceso más lectura y parseo, en archivos cortos locales; **no** mide la importación completa ni repite el experimento de concurrencia anterior. Como cálculo ilustrativo, 200 sondeos a 37 ms suman 7.4 s; con 200 proxies adicionales serían 14.8 s si costaran lo mismo. **No se corrió esa exportación y no se promete ese ahorro.** Un proxy, un MXF o un archivo remoto pueden costar otra cosa.

### C. Doble construcción de la hoja

Se ejecutó `_poblar_ventana` con 229 clips ficticios, Qt `offscreen`, mpv simulado y revisión de media/autoguardado desactivados en el arnés. Se envolvió `ClipSheet.set_clips` para contar y cronometrar sus llamadas, sin editar archivos del producto.

Resultado: dos llamadas de **229 tarjetas cada una**, 0.0320 s y 0.0393 s; `_poblar_ventana` completo, 0.0847 s. Se construyen 458 tarjetas para acabar con 229. Qt avisó que OpenGL no está soportado por ese backend y la ventana no se mostró.

**La duplicación queda confirmada; estos 85 ms NO son el tiempo real de apertura.** El experimento no incluye Cocoa visible, estilos finales, cache, reproductor real ni repintados. Los 17 s de arranque citados en septiembre son históricos; no se atribuyen completos a esta duplicación.

## Ideas concretas

### 1. Decodificar proxies con hardware, manteniendo su formato actual

**Evidencia:** `proxy_gen.py::comando` ya codifica con `h264_videotoolbox`, pero no solicita `-hwaccel`. Experimento A.

**Impacto / confianza:** alto para CPU de transcodificación en el clip medido; bajo para reloj en ese mismo clip. Confianza alta en ese resultado local, media en otros clips y Macs. Costo bajo de implementación, riesgo medio de compatibilidad y color.

**Qué medir antes:** repetir con los tres clips, tomas largas de Sony/dron/Pocket, variantes de audio y verticales; probar el FFmpeg empaquetado y una Air de 8 GB. Comparar cuadros, timestamps, niveles/rango de color, orientación y audio; luego generar mientras se reproduce y clasifica. Registrar CPU de hijos, memoria, frames perdidos y latencia de navegación. No asumir que el chip admite más trabajos simultáneos por gastar menos CPU. Separar también el costo de rotación, conversión de formato y overlay en un experimento: no se aislaron aquí. La build local enumera `yadif_videotoolbox`, pero no `overlay_videotoolbox`; no proponer una sustitución de filtro que ese binario no trae. Quitar la marca no sería una mejora equivalente del producto.

### 2. Autoguardado por cambios reales, sin volver a inspeccionar toda la media

**Evidencia:** `_autosave` tiene debounce de 400 ms y un pool de un hilo: eso **ya está hecho**. Sin embargo, `select_clip` y `handle_arrow` lo llaman aunque la selección actual no forma parte de `proyecto.a_dict`. `_AutosaveWriteJob.run` relee el `.cvproj`; `con_pesos_medidos` hace un `stat` por original cada vez, aunque sus bytes sean conocidos.

**Propuesta:** separar «cambió el documento» de «cambió la vista»; medir tamaño/identidad al importar, validar o reconectar, conservarlos en memoria y reservar revisiones posteriores para eventos definidos. Mantener una escritura activa y solo el snapshot pendiente más reciente, en lugar de acumular todos los intermedios cuando el disco tarda. Asignar revisión al snapshot y a la confirmación: «guardado» debe corresponder a la última edición persistida.

**Impacto / confianza:** medio en disco/CPU cotidiano y potencialmente alto en unidades lentas. Alta confianza en que elimina trabajo; ganancia temporal sin medir. Para 200 clips, 100 guardados implican hasta 20,000 `stat` de originales, además de leer/escribir JSON: es una cuenta del código, no un benchmark. Costo medio; riesgo alto si se pierden pesos o se confirma una revisión vieja.

**Qué medir antes:** diez minutos de flechas sin editar y diez de clasificación; contar snapshots, `stat`, bytes escritos y antigüedad del último cambio persistido. Simular disco lento/desconectado, edición durante una escritura, quitar bins, cerrar dentro del debounce y falla de guardado. Preservar los pesos aunque la media desaparezca; no omitir la primera medición ni invalidar las defensas del relink.

### 3. Compartir metadata validada entre importación, proxies y exportación

**Evidencia:** `_medir` obtiene metadata; el proyecto persiste tamaños/duración/rotación/fps. `_sondear_proxies` valida proxies. Más tarde `prproj_generador.generar_prproj` llama otra vez a `probe(clip.ruta)` y, cuando corresponde, a `probe(clip.ruta_proxy)` dentro de su ciclo.

**Propuesta:** un resultado de sondeo por identidad de archivo, reutilizable en esa sesión y opcionalmente entre sesiones. Conservar el esquema completo requerido: el proyecto actual no almacena todos los campos de `probe_clip`, como `has_audio`, ni toda la metadata del proxy. No basta pasar los diccionarios existentes sin revisar el contrato.

**Impacto / confianza:** medio/alto en exportaciones repetidas e importación de media conocida; bajo al reabrir proyectos, que ya restauran metadata sin sondear todos los originales. Alta confianza en el trabajo repetido, media en la magnitud. Costo medio; riesgo alto de usar metadata vieja.

**Qué medir antes:** instrumentar cantidad de procesos por archivo y etapa. Clave con ruta/identidad, tamaño, `mtime_ns` y versión del esquema; invalidar al reemplazar o reconectar. No identificar solo por nombre, ni calcular un hash completo de gigabytes por cada consulta. Comparar exportaciones frías y calientes; verificar audio, rotación, fps y relink en Premiere. El material real es indispensable.

### 4. Exportar a Premiere sin congelar la interfaz

**Evidencia:** `_on_generar_prproj` llama directamente a `generar_prproj`; el ciclo hace los sondeos en serie, consulta archivos y construye XML. No hay un trabajo de fondo en ese camino.

**Propuesta:** capturar un manifest coherente y resolver sondeos/construcción fuera de la UI; entregar progreso y resultado por señales. Aprovechar idea 3, y solo paralelizar sondeos con un límite medido. Si el armado de XML domina, evaluar proceso separado: un hilo Python no garantiza liberar todo el CPU de la UI.

**Impacto / confianza:** alto en respuesta percibida durante exportación; moverlo de hilo no garantiza que termine antes. Confianza alta en el bloqueo del camino, media en cuánto pesa cada etapa. Costo medio; riesgo medio/alto de exportar una mezcla de revisiones o dejar una salida incompleta.

**Qué medir antes:** 200/500 clips con y sin proxies, separar sondeo/XML/escritura y medir latencia del event loop. Comparar el `.prproj` por contenido funcional y abrirlo en Premiere. Probar cambios al proyecto durante exportación y cierre/cancelación. No publicar un archivo final hasta terminar correctamente.

### 5. Importación verdaderamente asíncrona y cancelable

**Evidencia:** `importar_rutas` hace el recorrido y llama a `_medir`; este usa `ThreadPoolExecutor`, pero consume `list(map(...))` y espera el cierre del executor en el hilo que lo llamó. `_run_ffprobe` no tiene timeout. La importación rápida repite el camino por cámara.

**Propuesta:** que un coordinador de fondo entregue metadata; actualizar Qt únicamente en el hilo principal. Conservar el orden de rodaje aunque los sondeos terminen en otro orden. Si se entrega por lotes, evitar recalcular toda la hoja por cada clip. Definir cancelación y tiempo máximo de un proceso problemático.

**Impacto / confianza:** alto para respuesta con tarjetas/unidades lentas; probablemente pequeño para reloj en SSD local, donde los ocho sondeos ya ayudan. Confianza alta en la espera síncrona. Costo medio; riesgo medio por índices, importaciones simultáneas y orden.

**Qué medir antes:** carpeta de 200/500 clips, archivo ilegible y un sondeo detenido; máxima pausa de UI, tiempo hasta poder clasificar, tiempo total y recursos. No aumentar el paralelismo ni reducir a ciegas `probesize`/`analyzeduration` para «ganar» dejando metadata incompleta.

### 6. Construir la hoja una vez al restaurar el proyecto

**Evidencia:** `_poblar_ventana` llama a `load_clips`, que hace `_refresh_sheet(force_rebuild=True)`; después restaura bins y medidas y vuelve a forzar la construcción. Experimento C lo confirma.

**Propuesta:** restaurar el modelo completo antes de materializar las tarjetas; hacer un único refresco final y una única apertura intencional del clip. No usar el reloj del debounce como contrato de restauración.

**Impacto / confianza:** medio potencial en arranque, CPU y pico transitorio de RAM; alta confianza en eliminar una construcción, media en que cambie mucho la experiencia. Costo bajo/medio; riesgo medio por los estados que `load_clips` limpia deliberadamente.

**Qué medir antes:** abrir el mismo proyecto de 229 y uno de 500 clips en Cocoa, registrar construcciones, primer evento atendido, primer cuadro y memoria máxima. Cubrir sesiones antiguas, proyectos con unidades y media faltante. No prometer «50% menos arranque»: solo se duplica una parte del trabajo.

### 7. Separar la consulta del cache de la lectura de imágenes en pantalla

**Evidencia:** `_schedule_thumbnails` corre en la ventana. `cache_dir_for` llama a `video.stat()` y `resolve()`; después se hacen `exists`, `glob` y comprobación de marca. Un cache hit llama directamente a `_on_thumbnail_ready`, que termina en `ClipCard.set_tira` y decodifica la portada. La revisión de media anterior no evita estas nuevas consultas.

**Propuesta:** consultar identidades e inventario del cache en fondo, enviar resultados en lotes y cargar primero portadas del área visible. Para decodificación asíncrona usar `QImage` en el trabajador y crear/usar `QPixmap` en UI. Mantener límites de memoria y descartar respuestas de tarjetas que cambiaron de identidad/tamaño.

**Impacto / confianza:** medio/alto al reabrir cientos de clips con cache; alto en riesgo de bloqueo por almacenamiento lento. Alta confianza en el camino síncrono, media en magnitud. Costo medio, riesgo medio. Esto no reemplaza el arreglo de RAM de septiembre.

**Qué medir antes:** hits calientes/fríos, cache parcial, original ausente y unidad lenta. Tiempo hasta primeras portadas, máxima pausa del event loop, operaciones de disco y RSS. No volver a lanzar extracción sobre archivos ausentes ni quitar la marca de tira completa.

### 8. Reusar metadata de directorios e índices de pertenencia

**Evidencia:** `ruta_de_proxy_existente` vuelve a resolver carpetas candidatas por clip; `subcarpeta_por_numero` enumera la elegida. `ingest.archivos_de_video` comprueba duplicados con una lista. `proyecto.rutas_relativas` llama a `bins.bin_de` por clip, y este busca dentro de listas de índices. La hoja ya construye un mapa de bins de una pasada: no hace falta «arreglar» esa parte otra vez.

**Propuesta:** inventario de candidatos por tanda, conjunto para duplicados conservando la lista ordenada, mapa índice→bin reutilizable o reconstruido una vez por operación. Invalidar al mover/quitar clips o generar archivos; conservar la precedencia de las tres ubicaciones de proxies.

**Impacto / confianza:** bajo/medio para cientos en SSD; mayor con carpetas grandes o remotas. Alta confianza en reducir consultas/comparaciones, media/baja en mejora visible. Costo bajo/medio; riesgo medio de inventario obsoleto.

**Qué medir antes:** contar `iterdir`/`stat`, comparar 200/500/2,000 clips y casos de nombres repetidos entre tarjetas. Medir antes de mantener índices globales que compliquen deshacer y renumeración.

### 9. Actualizaciones puntuales de la hoja y agrupación diferida

**Evidencia:** `_refrescar_hoja_de_verdad` construye un `ClipThumbnail` para cada clip y `update_clips` actualiza todas las tarjetas y llama a `_regroup`. Ya existen guardas de layout, reutilización de widgets y un camino puntual para el pincel; la selección simple tampoco reconstruye la hoja.

**Propuesta:** propagar qué dato cambió y actualizar solo las tarjetas/conteos afectados; agrupar varias modificaciones de una misma acción. Reagrupar únicamente cuando cambia una clave de grupo o su orden. Mantener una sola fuente para el orden visual y las flechas.

**Impacto / confianza:** medio para clasificar rápido o grupos grandes; bajo si las mediciones actuales siguen en pocos ms. Confianza media; costo medio y riesgo alto por filtros, unidades, selección, historial y agrupación.

**Qué medir antes:** p50/p95 de tecla→pintado, cantidad de tarjetas tocadas y llamadas a regroup con 229/500/2,000 clips. Comparar acciones reales: cuarto, estado, filtro, mover bin y deshacer. No sacrificar consistencia por ahorrarse recorridos baratos.

### 10. Virtualizar tarjetas, conservando el modelo completo

**Evidencia:** `ClipSheet.set_clips` crea una tarjeta por clip, aunque no se vea. La investigación previa identificó widgets como siguiente candidato de RAM: 131 MB en su medición histórica, no una promesa de ahorro actual.

**Propuesta radical:** delegados en una vista de modelo o reciclaje de tarjetas para el viewport más un margen. `QListView` ofrece layout por lotes y optimizaciones de tamaños uniformes, pero la hoja actual mezcla orientación, grupos y encabezados: `uniformItemSizes` no aplica sin rediseñar esa geometría. [Qt: QListView](https://doc.qt.io/qt-6/qlistview.html).

**Impacto / confianza:** potencial alto en RAM/arranque con miles, medio con cientos. Confianza media; costo alto y riesgo alto de regresiones en scrubbing, pincel, drag, selección y encabezados pegados.

**Qué medir antes:** prototipo aislado con la misma interacción, 229/500/2,000 clips. Medir RSS y huella de memoria, memoria viva de imágenes/widgets, picos y scroll rápido; no confundir memoria liberada internamente con RSS devuelta al sistema. Comparar primero con idea 6 y portadas visibles de idea 7, que cuestan menos.

### 11. Evitar cargas de video que nadie alcanza a ver

**Evidencia:** `_abrir_clip_actual` abre el video aun en modo hoja y después lo pausa. La intención documentada es que pasar al visor sea instantáneo. `VideoWidget.player` ya es perezoso, pero abrir el clip activa esa creación. El widget también recupera la carga previa a OpenGL, por un bug real de primer cuadro negro.

**Propuesta:** conservar la selección inmediatamente y aplazar/reemplazar cargas intermedias durante una ráfaga de flechas; precargar únicamente el clip donde te detuviste. Alternativa más fuerte: abrir hasta entrar al visor.

**Impacto / confianza:** medio potencial en CPU, I/O y arranque; medio/bajo en navegación ya fluida. Confianza media. Costo medio; riesgo alto si se retrasa el primer cuadro o I/O se aplican al clip equivocado. No es autorización para quitar la precarga sin comparar.

**Qué medir antes:** recorrer 100 clips sin mostrar visor, contar aperturas reales y segundos de CPU; luego abrirlo y medir primer cuadro. Probar selección rápida seguida inmediatamente de I/O, reproducción y cambio de modo. No aplicar el seek aproximado de las miniaturas al marcado exacto del reproductor.

### 12. Desactivar la pista de audio del visor, no solo silenciarla

**Evidencia:** `MpvPlayer.__init__` pasa `mute=True`. La documentación distingue silenciar de desactivar la pista con `aid=no`/`audio=no`. [Manual oficial de mpv](https://mpv.io/manual/stable/#track-selection).

**Propuesta:** probar desactivar audio solo en el reproductor de Clipify, coherente con la decisión de que la app no suene. Los proxies entregables siguen conservándolo.

**Impacto / confianza:** bajo esperado, continuo durante reproducción; confianza media. Costo bajo, riesgo bajo/medio por cambios de reloj/sincronización. No se midió en esta sesión.

**Qué medir antes:** mismo clip con audio, a 1×/2×/4×, CPU, avance por cuadro, posición y frames perdidos; repetir con original y proxy, y con un clip sin audio.

### 13. Presupuesto conjunto para trabajos en segundo plano

**Evidencia:** la generación de proxies tiene su pool de uno; miniaturas y validación de proxies comparten otro de hasta tres; el visor usa su propia instancia. Son límites separados, no una política conjunta de CPU, memoria y decodificación.

**Propuesta:** priorizar reproducción y validación necesaria; reducir o pausar admisión de trabajos pesados cuando interactúas, hay presión de memoria o la máquina está en batería. Dar prioridad dentro del bin a lo visible cuando ya le toque generar miniaturas. Limitar la cola en vuelo y evitar que un ffprobe corto espere detrás de cientos de extracciones, sin crear ocho decodificaciones adicionales por accidente.

**Impacto / confianza:** medio/alto en fluidez y picos; el procesamiento total podría tardar más. Confianza media; costo medio/alto y riesgo medio de inanición o prioridad cambiante.

**Qué medir antes:** matriz visor solo / proxies solos / miniaturas solas / combinaciones reales, con memoria y latencia. Mantener máximo de tres extracciones y uno de proxies. No deducir capacidad del chip solo por contar hilos; no repetir la prueba descartada de subir concurrencia.

### 14. Arranque y mantenimiento sin consultas lentas en UI

**Evidencia:** `Reciente.__post_init__` usa `exists`; `_leer` construye entradas antes de devolver la lista. `proyecto.abrir` lee JSON sincrónicamente. Abrir Configuración calcula `tamano_del_cache` con un recorrido recursivo. `reconectar_bin` recorre/sondea sincrónicamente por decisión explícita pendiente de medir.

**Propuesta:** mostrar recientes y disponibilidad pendiente antes de consultar volúmenes; leer el documento en fondo, construir Qt en UI; calcular el tamaño del cache fuera de UI. Medir relink y pasarlo a trabajo cancelable si pesa. Perfilar imports antes de diferir módulos o inicialización del reproductor: parte de esta última ya es lazy.

**Impacto / confianza:** bajo en SSD caliente; potencial alto con volumen colgado, placeholders de iCloud o cache grande. Alta confianza en los caminos síncronos, media en frecuencia real. Costo medio; riesgo medio de enseñar disponibilidad vieja.

**Qué medir antes:** arranque del `.app` en frío/caliente, proyecto local y unidad no disponible, configuración con miles de JPEG y relink de un shooting. Medir primera ventana que acepta entrada, no solo una pantalla de carga. La pereza de imports solo vale si no desplaza el mismo bloqueo al primer clic.

## Ideas mayores y alternativas que todavía requieren prueba

Cada renglón es una candidata independiente, no una recomendación para hacer todo.

| ID e idea | Impacto esperado y confianza | Costo/riesgo | Prueba decisiva antes de implementar |
|---|---|---|---|
| **15. Dos representaciones de proxy:** entregable a resolución original y preview local pequeño, descartable, generado bajo demanda | Medio/alto en navegación y RAM si el proxy 4K actual pesa al decodificar; confianza media | Alto: dos cachés, más disco y transcodificación. El pequeño nunca puede sustituir al entregable en Premiere | Comparar costo total de crear ambos más una sesión de clasificación contra uno solo; primer cuadro, seeks y memoria. Verificar cuadro a cuadro y relink. Razón nueva para explorar 720p: uso exclusivamente interno, respetando la decisión del 18 de septiembre |
| **16. GOP más corto o formato intraframe para preview local** (p. ej. ProRes Proxy), conservando fps y todos los cuadros | Potencial alto en seeks exactos, con posible aumento fuerte de disco; confianza media/baja en balance total | Medio/alto: tamaño, velocidad de escritura, compatibilidad y otra política de cache | Probar clips reales cortos y largos: generación + 100 seeks exactos + reproducción + bytes. Para ProRes/hardware verificar primero el encoder disponible en cada paquete/Mac. No sustituir H.264 solo por reputación del codec |
| **17. Obtener las imágenes mientras ya se decodifica el proxy**, mediante una salida adicional del proceso | Ahorro potencial de la segunda lectura/decodificación, confianza media/baja: el filtro extra podría ralentizar el proxy | Alto: timestamps, rotación, cache fuente y salida parcial. No adelantar la publicación a mitad del bin contra la preferencia documentada | Comparar pipeline completo «proxy y después tira» contra salida doble, con la misma política de miniaturas en ambos. Verificar las posiciones y nunca marcar completa una tira de proceso fallido. No es repetir la fusión portada+tira, que ya existe |
| **18. Sesión persistente de extracción o backend nativo AVFoundation/VideoToolbox** | Incierto; confianza baja en mejora neta. El arranque de mpv ya tiene un costo histórico acotado | Alto/muy alto: cancelación, fugas, codec/rotación/color y mantenibilidad macOS | Spike aislado sobre los tres clips y luego material mixto. Comparar trabajo total, CPU y RAM, más 1,000 cambios/cancelaciones. No empezar reescribiendo el reproductor ni quitando render API; descartar si solo ahorra un margen pequeño |
| **19. Cache con manifiesto, identidad de contenido validada y limpieza por presupuesto** | Medio en espacio acumulado y reaperturas; confianza alta en que puede acotar disco, media en ahorro temporal | Medio/alto: regeneraciones al limpiar, identidad tras mover media y trabajos en vuelo | Inventario por origen/proxy/modo, bytes duplicados y tasa de aciertos. Medir presupuesto por proyecto/último uso. Excluir entradas en vuelo. Actualmente la clave incluye ruta: mover un archivo pierde el hit. No compartir por nombre/tamaño solos; no leer gigabytes para hashear durante cada apertura |
| **20. Preview derivado compartido entre original y proxy solo cuando equivalen visualmente** | Medio potencial en generación/disco, confianza media/baja | Alto: hoy el cache distingue fuente a propósito; marca, color, rotación o proxy incorrecto pueden cambiar la imagen | Contar extracciones rehechas al enganchar proxies, comparar imágenes y contrato de fuente. Solo reabrir esa decisión si hay duplicación medida y equivalencia validada; no forzar una clave común indiscriminada |
| **21. Serialización compacta o journal local de cambios, manteniendo `.cvproj` portable** | Bajo esperado para JSON compacto; medio condicionado a escritura lenta para journal. Confianza media/baja sin perfil | Bajo para quitar indentación; alto para journal/SQLite por recuperación, migración y sincronización | Medir por separado `a_dict`, JSON, `stat` y escritura en 200/500/2,000 clips. Comparar bytes y recuperación tras corte. No poner una base SQLite/WAL activa en iCloud como reemplazo automático de un documento sincronizable |
| **22. Generar en almacenamiento local y publicar el proxy terminado en el destino elegido** | Potencial medio en disco/iCloud y menor churn de archivos parciales; confianza baja sin observar sincronización real | Medio: copia adicional, doble espacio temporal y fallas entre volúmenes. El destino final sigue siendo el elegido por Bruno | Medir actividad del proveedor de archivos durante generación actual; no asumir que sincroniza cada cambio del `.parcial`. Comparar bytes escritos/subidos y reloj. Entre volúmenes, copiar a temporal de destino y finalizar allí; no prometer rename atómico entre discos |
| **23. Preparación anticipada y selectiva** dentro de la sesión, al quedar ociosa, para el siguiente bin/clip probable | Medio en espera percibida, puede empeorar consumo total; confianza media/baja | Medio/alto: hacer trabajo nunca usado, batería y espacio. Nada de generar un entregable sin el flujo autorizado de carpeta | Medir tasa de aciertos de la anticipación y recursos desperdiciados. Cancelar/priorizar al interactuar; presupuesto pequeño. No precalcular tiras de todo el shooting como «optimización» si ya se hace eso |
| **24. Reducir conversaciones con disco en cierre y fallas**: timeouts de procesos, admisión de trabajos y recuperación coherente | Alto en casos atascados, bajo en sesión sana; confianza media | Medio/alto: un hilo bloqueado en filesystem no se cancela solo con una bandera | Simular ffprobe detenido y volumen incomunicado; medir cierre y último snapshot recuperable. `_flush_autosave` espera 2 s, pero eso no cancela su worker ni garantiza que el destructor del pool deje de esperar. No resolverlo descartando cambios pendientes |

## Qué no pondría al frente

- Bajar todavía más el límite de tiras vivas como respuesta principal a RAM: ya está acotado y el documento anterior separó imágenes de widgets/asignador.
- Reescribir toda la UI o cambiar Python por C++ antes de perfilar construcción, consultas de disco y sondeos duplicados. Son costos concretos con alternativas menores.
- Añadir hilos por reflejo; ya hay evidencia de saturación. Tampoco subir la concurrencia de proxies basándose en la prueba de un solo clip.
- Quitar audio o resolución de los proxies entregables. Cambiaría el material de trabajo del editor externo.
- Cambiar JSON por SQLite solo porque «las bases de datos son rápidas». Primero eliminar guardados sin cambios y mediciones repetidas.
- Borrar todo el cache para ahorrar disco: empuja CPU/espera a la próxima sesión. Una limpieza debe tener presupuesto y costo de regeneración.
- Interpretar `mute=True` como audio desactivado, o `h264_videotoolbox` como prueba de que toda la tubería usa hardware.
- Reabrir miniaturas incrustadas, escalado gráfico de las tiras o el paralelismo ya descartado.

## Plan de comprobación antes de tocar el producto

### Escenarios y métricas comunes

Usar una copia de un proyecto real y material de muestra sin alterar originales. Comparar mismo commit, configuración, geometría y fuente de thumbnails; registrar versiones del paquete y herramientas. Hacer al menos cinco repeticiones alternadas para decidir; los tres pares exploratorios de proxies de aquí no sustituyen esa validación.

| Escenario | Medidas que importan |
|---|---|
| Arranque vacío y apertura de 229/500 clips con cache | Primera ventana que acepta entrada, primeras portadas visibles, lista completa utilizable, p95 y máxima pausa del event loop, widgets creados, memoria máxima |
| Importación fría y otra con metadata/cache válidos | Tiempo hasta clasificar el primer clip/bin, tiempo total, ffprobe/mpv lanzados, CPU acumulada propia + hijos, I/O |
| Clasificar y navegar a ritmo real | Tecla→resultado visible, primer cuadro tras selección, frames perdidos, trabajo al recorrer solo la hoja |
| Generación y exportación mientras se usa la app | Rendimiento total y latencia de interacción; estado de avance fiel a resultados reales |
| Guardado local/iCloud/disco lento | Escrituras útiles/inútiles, bytes, backlog, edad de edición sin persistir, duración de cierre y recuperación |
| Cache/RAM después de una sesión larga | RSS, huella de memoria, presión/swap, imágenes/widgets vivos, disco ocupado y tasa de aciertos |

No llamar «frío» a repetir los mismos tres archivos con el cache de macOS caliente. No usar `offscreen` para dar por comprobado OpenGL, fluidez o apariencia. CPU acumulada, RSS y energía son métricas distintas; calor/batería requieren una sesión larga y medición apropiada, no inferencia desde un cronómetro.

### Orden sugerido para experimentos

1. Validar proxy con decodificación por hardware en más media y con reproducción simultánea. Es la única nueva candidata aquí con beneficio de CPU medido sobre video real.
2. Contar guardados/consultas innecesarios y perfilar exportación; después evaluar un catálogo de metadata compartido.
3. Medir apertura visible con construcción única y consulta del cache fuera de UI mediante prototipos aislados, sin confundir el arnés sintético con el producto.
4. Medir importación/relink con almacenamiento lento y respuesta de UI. La asincronía se justifica por latencia de interacción aunque no mejore el reloj total.
5. Solo si el perfil lo pide, probar virtualización, preview local alternativo y tubería integrada de proxy/imágenes.

Una candidata se descarta si gana reloj pero pierde cuadros, orientación, audio, color, marcas o relink; si ahorra RAM creando más swap por otro lado; o si complica la operación del editor sin una ganancia observable. Preservar selección, deshacer, orden de cuartos y datos guardados es parte de la comprobación, no algo que una suite verde demuestre automáticamente.

## Estado de entrega

Investigación terminada sobre la base indicada. Se hicieron únicamente los experimentos A/B/C y consultas de capacidades/versiones; **no se corrió una sesión gráfica completa con un shooting ni la suite de tests**, porque no se modificó código. No se implementaron las 24 ideas, no se crearon branches ni se cambiaron preferencias, proyectos de trabajo o archivos originales. Los tiempos históricos permanecen identificados como históricos y las estimaciones pendientes como pendientes.
