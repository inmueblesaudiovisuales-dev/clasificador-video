# Por qué Premiere hace miniaturas casi gratis y Clipify no (2026-09-25)

Investigación a pedido de Bruno: "¿cómo le hace Premiere para que las
miniaturas salgan en segundos, incluso en una computadora lenta, y cómo
aplicamos eso a Clipify?" Luego, en la misma sesión, Bruno pidió ir más allá
de la primera pista y encontrar el máximo de velocidad posible sin que le
importe la precisión.

Este documento junta las dos rondas: la investigación original (rama
`claude/clipify-thumbnail-optimization-u5wvxd`, sin fusionar) y las
mediciones en vivo de la sesión del 2026-09-25 contra clips reales de la
Sony FX30 (`sample-media/clips/`). **Sin cambios de código todavía** — esto
es el análisis completo, con lo que se descartó y por qué, para que la
implementación parta de aquí sin repetir trabajo.

## Lo que Clipify YA hace bien (no es el problema)

Repasando `thumbnails.py`, `proxy_gen.py` y el agendador de
`main_window.py`, varias de las cosas que uno pensaría "optimizar" ya
estaban resueltas antes de esta investigación:

- **Cache en disco por clip**, invalidado solo si el archivo cambia
  (`cache_dir_for`). Un clip ya procesado no se vuelve a tocar.
- **Se prefiere el proxy sobre el original** cuando existe — ~20 veces más
  barato (comentario en `main_window.py` línea ~4456).
- **Una sola sesión de mpv por clip** para sacar toda la tira (12 cuadros),
  no un proceso por cuadro — de ~10.8s a ~1.8s, medido el 2026-08-06.
- **Decodificación por el chip** (`--hwdec=videotoolbox-copy`) — de 50.4s de
  CPU a 18.7s por clip, medido el 2026-09-13.
- **Modo económico**: tira más chica (480px de ancho) y menos hilos en
  paralelo para equipos con menos RAM.
- **Todo corre en segundo plano** en un `QThreadPool`, sin bloquear la
  interfaz.
- **Portada y tira ya comparten un solo arranque de mpv**: la portada es
  simplemente el primer cuadro de la tira (`_ThumbnailJob.run`, ver más
  abajo). No hay un segundo proceso que fusionar — se verificó en esta
  sesión y la idea se descarta por no aplicar.

Lo que quedaba por mirar era **cuánto cuesta cada extracción individual**,
que es justo donde Premiere le sacaba ventaja incluso sin proxy.

## La causa raíz: búsqueda exacta vs. búsqueda al cuadro clave

Un video comprimido guarda pocos "cuadros completos" (keyframes) y, entre
ellos, puros cuadros que describen cambios respecto al anterior. Reconstruir
un instante exacto obliga a decodificar toda la cadena de cambios desde el
keyframe más cercano.

En `thumbnails.py`, el seek que se manda por el socket IPC de mpv era:

```python
conn.command(["seek", at_seconds, "absolute"])
```

mpv trae `--hr-seek=absolute` por default: "para un seek absoluto como
este, sé exacto". Le estábamos pidiendo a mpv el camino caro sin querer.
Premiere hace lo contrario: salta al keyframe más cercano y ya.

Esto aplica igual a `build_thumbnail_command` (la portada de un solo
cuadro, usada solo cuando no se conoce la duración — ver más abajo), que
usa `--start=` con el mismo default.

## Lo que se probó y midió en vivo (2026-09-25)

Material: `sample-media/clips/20260804_PIB0589.MP4` — HEVC 4K 10-bit de la
FX30, 6.006s, **un keyframe cada ~1 segundo** (confirmado con `ffprobe
-show_entries frame=key_frame,pkt_dts_time`). Tira de 12 cuadros, como usa
la app en modo normal.

### 1. Seek por keyframe — la ganadora de la investigación original

Cambiar `"absolute"` por `"absolute+keyframes"` en el comando de seek:

| Paso | Tiempo (tira de 12, clip de 6s) |
|---|---|
| Como estaba (seek exacto) | 4.07 s |
| Seek por keyframe | 2.39 s |

**Confirmada. Es la base de todo lo que sigue.**

### 2. Saltar la decodificación de cuadros no-clave — hallazgo nuevo

Como a Bruno no le importa la precisión, no hace falta reconstruir nada
entre keyframes: `--vd-lavc-skipframe=nonkey` le dice al decodificador que
ni siquiera decodifique los cuadros intermedios.

| + saltar frames no-clave | 1.45 s |

`--vd-lavc-skiploopfilter=all` se probó además y **no sumó nada medible**
(1.44-1.47s, dentro del ruido) — el loop filter ya es barato comparado con
la decodificación completa que se está evitando. Se descarta agregarlo:
una línea menos en el comando final sin perder nada.

### 3. Escalar a 480px por CPU (modo económico, ya existente)

| + `--vf=scale=480:-2` | 0.97 s |

### 4. Quitar audio de la tira

La tira (`build_strip_ipc_args`) no traía `--no-audio` a diferencia de la
portada suelta, que sí lo tiene.

| + `--no-audio` | **0.83 s** |

**Total: de 4.07s a 0.83s por clip — ~5x más rápido**, en la configuración
más económica.

### El precio real de "no me importa la precisión"

No es solo que la foto se mueva un poco — es más concreto. Se verificó
byte por byte: en el clip de 6s con keyframes cada ~1s, de las 12 fotos
pedidas para la tira **solo salieron 6 distintas, cada una repetida dos
veces seguidas** (mismo hash SHA1, mismo tamaño exacto). Las imágenes en sí
salen bien —no hay corrupción, contenido correcto— pero el escrubeo no
avanza tan fino como con seek exacto. Bruno aceptó este costo
explícitamente el 2026-09-25.

## Lo que se probó y se DESCARTÓ

### Miniatura de fábrica incrustada en el archivo (pista 2 del doc original)

La hipótesis: muchas cámaras graban una fotito de baja resolución para su
propia pantalla, y leerla no decodifica nada de video.

**Se probó contra un clip real de la FX30 y no existe.** `exiftool -b
-ThumbnailImage` devolvió 0 bytes, y el atom `meta`/`iinf`/`iloc`/`idat`
que sí trae el archivo (visto con `ffprobe -v trace`) es el track `rtmd`
de metadata de la cámara (giroscopio, exposición, etc.), no una imagen.
**Descartada para este material — no reabrir sin un archivo de otra cámara
que sí la traiga.**

### Escalar con el chip gráfico en vez de CPU (`scale_vt`, pista 3 del doc original)

La hipótesis: si el cuadro ya salió del chip decodificador
(`videotoolbox-copy`), escalarlo también en el chip (`scale_vt`) evitaría
un viaje de ida y vuelta a memoria.

**Se probó y salió más lento, no más rápido**: 1.49s contra 0.97s del
escalado por CPU (`scale=480:-2`), ambos ya con seek por keyframe y skip
de frames no-clave. El filtro existe en esta build de mpv
(`mpv --vf=help` lo lista), pero el costo de la ida y vuelta al chip para
un cuadro que ya es barato de escalar por CPU no se paga solo.
**Descartada — se mantiene el escalado por CPU actual.**

### Subir el paralelismo de 3 hilos a más

La hipótesis: si cada extracción ahora consume mucho menos CPU/GPU (por el
skip de frames no-clave), subir `HILOS_DE_MINIATURAS_NORMAL` de 3 a más
debería acelerar tandas grandes.

**Se midió con 12 clips reales a distintos niveles de paralelismo**
(procesos aislados, no hilos de un mismo proceso, para no arrastrar el
colgado que salió en el primer intento — ver nota abajo):

| Paralelo | Tiempo total (12 clips) | Cola/saturación |
|---|---|---|
| 1 | ~10 s (descontando un outlier de arranque en frío) | ninguna |
| 2 | 5.85 s | ninguna |
| **3** | **4.40 s** | ninguna — el mejor tiempo medido |
| 4 | 6.31 s | un clip se atora a 6.25s |
| 5 | 25.97 s | varios clips de 11 a 26s |
| 6 | 26.05 s | igual de mal |
| 9 | 26.34 s | igual de mal |

**El techo no es CPU, es el decodificador de hardware del chip**: el M3
Max de esta máquina satura alrededor de 3-4 sesiones `videotoolbox-copy`
simultáneas, y pasado ese punto los jobs se encolan y el tiempo TOTAL
empeora respecto a menos paralelismo, no solo deja de mejorar. Confirma
que `HILOS_DE_MINIATURAS_NORMAL = 3` (elegido el 2026-08-06 por una razón
distinta — no competir con VideoToolbox del reproductor) sigue siendo el
valor correcto también bajo este análisis nuevo. **No subir el número de
hilos.**

Nota sobre el método: el primer intento de medir esto usó un solo proceso
Python con varios hilos y conexiones IPC concurrentes, y uno de los mpv
quedó colgado esperando una respuesta que nunca llegó (0% CPU, sin
avanzar, tuvo que matarse a mano). No se investigó la causa raíz de ese
colgado porque el reemplazo —un proceso del sistema operativo aislado por
job, vía `xargs -P`— midió lo mismo sin el riesgo. Vale la pena tenerlo
en cuenta si en el futuro se cambia la extracción a correr varias
conexiones IPC en hilos de un mismo proceso Python: **hay una condición de
carrera ahí que no se diagnosticó**, sea del lado de mpv, de `select()`
compartido entre hilos, o del propio harness. Ver también el patrón que
describe `CONTEXTO-Y-METAS.md`: "el uso real encuentra lo que las pruebas
no".

### Fusionar portada y tira en un solo arranque de mpv

Ya estaban fusionadas de antes: `_ThumbnailJob.run` en `main_window.py`
solo llama a `extract_thumbnail_strip` (que ya genera la portada como
primer cuadro) cuando conoce la duración del clip. `extract_thumbnail` /
`build_thumbnail_command` —el camino de un solo cuadro que sí abriría un
segundo mpv— solo se usa como respaldo cuando la duración no se conoce
(ej. una sesión restaurada sin volver a correr `ffprobe`). No hay nada que
fusionar; ese camino de respaldo debe recibir el mismo criterio de seek
por keyframe que la tira, pero es una ruta rara, no el caso común.

## Números finales, condición real (3 en paralelo, no un clip aislado)

| | 12 clips | Extrapolado a 200 clips |
|---|---|---|
| Como está ahora | 15.1 s | ~4.2 min |
| Con todo lo de arriba | 4.4 s | ~1.2 min |

**~3.4x más rápido** en las condiciones en las que la app corre de verdad
(varios clips en paralelo), no solo en el mejor caso de un clip aislado
(~5x ahí).

## Dónde queda el piso

Se midió el arranque de mpv por separado del trabajo de extracción: 0.165s
fijos por clip (lanzar el proceso + conectar el socket IPC), contra ~0.67s
para los 12 seek+captura de la tira (~56ms cada uno). Ya no queda grasa
fácil de cortar sin tocar el protocolo IPC en sí —por ejemplo, mandar los
12 comandos de seek sin esperar la confirmación de cada uno antes del
siguiente (`pipelining`)— y eso es zona de riesgo: el código actual espera
el evento `playback-restart` a propósito, documentado como la forma de
evitar capturar el cuadro viejo (ver el docstring de
`extract_thumbnail_strip`). No se intentó ni se recomienda sin medirlo con
mucho cuidado aparte — la ganancia esperada es baja frente al riesgo de
volver a romper lo que esa espera ya arregló una vez.

## Qué NO es una diferencia real (de la investigación original, sigue valiendo)

- **El tamaño del preview de Premiere no es la razón** — ya achicamos
  nosotros también (modo económico).
- **La cámara/formato tampoco explica la brecha completa** — el mismo
  archivo, con el mismo chip, decodificado con seek exacto vs. seek a
  keyframe, es la comparación que de verdad importa.

## Qué falta implementar

Nada de esto se ha tocado en código todavía. Cuando se implemente:

1. `extract_thumbnail_strip` / `build_strip_ipc_args`: seek
   `"absolute+keyframes"`, agregar `--vd-lavc-skipframe=nonkey` y
   `--no-audio` a `build_strip_ipc_args`.
2. `build_thumbnail_command` (el camino de respaldo sin duración conocida):
   mismo criterio — `--hr-seek=no` y `--vd-lavc-skipframe=nonkey`. Ya tiene
   `--no-audio`.
3. No tocar `HILOS_DE_MINIATURAS_NORMAL` / `HILOS_DE_MINIATURAS_ECONOMICO`
   — confirmado que 3 sigue siendo el óptimo.
4. Documentar en el código, junto al cambio, los números medidos aquí
   (mismo estilo que el resto de `thumbnails.py`, que ya cita mediciones
   con fecha).
5. Correr la suite completa (`QT_QPA_PLATFORM=offscreen .venv/bin/pytest
   tests/ -q`) y medir de nuevo contra un clip real antes de dar el cambio
   por bueno — no basta con que compile.

Aparte, y sin relación directa con las miniaturas: se encontró un
comentario desactualizado en `main_window.py` línea ~687 que dice "las
miniaturas se extraen en software (`--hwdec=no`)" cuando el código real usa
`--hwdec=videotoolbox-copy` desde el 2026-09-13. Corregirlo de paso cuando
se toque ese archivo.
