# Hallazgos sobre la rotación de video vertical (complementa el HANDOFF del mismo día)

Este documento reemplaza las hipótesis abiertas de la sección 5 del
`HANDOFF-2026-08-05-rotacion-vertical-sin-resolver.md`. La evidencia de aquí no
viene de búsquedas web ni de prueba y error: viene de leer el binario de Adobe
Premiere Pro 2026 instalado en esta máquina.

## 1. Cómo se obtuvo la evidencia

El parser y el escritor de Final Cut Pro XML (xmeml) están compilados dentro del
ejecutable principal:

```
/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app/Contents/MacOS/Adobe Premiere Pro 2026
```

Ese binario contiene, en texto plano, dos tablas completas:

- El **vocabulario del lector**: todas las etiquetas xmeml que Premiere sabe
  interpretar al importar.
- El **vocabulario del escritor**: los literales exactos que Premiere emite al
  exportar (`<parameter authoringApp="PremierePro">`, `pproTicksIn`,
  `pproOriginalPAR`, `scaleToFrameSize="TRUE"`, `label2`, etc.).

Reproducible con:

```bash
strings -a -t d "/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app/Contents/MacOS/Adobe Premiere Pro 2026" > ppro_strings.txt
grep -n " samplecharacteristics$" ppro_strings.txt   # dos bloques: lector y escritor
```

## 2. Hallazgo 1 — xmeml no tiene ninguna etiqueta de rotación a nivel de archivo

El vocabulario completo del lector es:

```
alignment, alpha, anamorphic, angleofaxis, anchor, asc_sat, asc_sop, audio,
level, blue, bottom, cameraroll, center, centerOffset, channeldescription,
clip, clipcommenta, clipcommentb, clipitem, clipindex, colorinfo, comment,
comments, compositemode, createnewproject, defsequencepresetname, depth,
dipcolor, displayformat, displaynonfatalerrors, duration, edgefeather, effect,
effectcategory, effectid, effecttype, enabled, end-black, fielddominance, file,
fillcolor, filmdata, filter, filterincludeeffects, filterincludemarkers,
filterincludesequencesettings, filterreconnectmediafiles, flop, fontalign,
fontcolor, fontname, fontsize, fontstyle, format, frame, frameblending,
generatoritem, good, green, groupindex, graphdict, height, horiz,
importoptions, startoffset, ismasterclip, keyframe, label, labels, labroll,
link, logginginfo, lognote, lut1, lut2, tapeid, left, masterclipid,
mastercomment1..4, media, mediaSource, mediatype, marker, mono, name, ntsc,
opacity, origin, originalvideofilename, originalaudiofilename, endoffset,
parameter, color, parameterid, pathurl, pixelaspectratio, privatestate, rate,
reel, render, reverse, right, rotation, scale, samplecharacteristics,
samplerate, scene, sequence, shottake, source, sourcetrack, speed, speedkf*,
start, start-black, stereo, str1, str2, strobeduration, stillframe,
stillframeoffset, subclipinfo, targetprojectname, timebase, timecode, track,
trackcount, trackindex, transitionitem, ulcorner, urcorner, lrcorner, llcorner,
value, valuemin, valuemax, variablespeed, version, vert, video, when, width,
wipecode, xmeml
```

`rotation` aparece **una sola vez**, y aparece junto a `scale`, `center`,
`centerOffset`, `anchor`, `opacity`, `compositemode`, `alpha`, `edgefeather`:
todos son `parameterid` de efectos de movimiento. **No existe ninguna etiqueta
de orientación, rotación o matriz de despliegue dentro de `<file>` ni de
`<samplecharacteristics>`.**

Esto cierra la hipótesis 1 de la sección 5 del handoff: no hay un tag adicional
que estemos omitiendo.

## 3. Hallazgo 2 — Premiere no tiene rotación como interpretación de material

El API de scripting del propio Premiere expone el objeto `FootageInterpretation`
(lo que la interfaz llama Modificar > Interpretar material). Sus propiedades
completas, extraídas del mismo binario, son:

```
getAlphaUsage / setAlphaUsage
getFieldType / setFieldType
getFrameRate / setFrameRate
getIgnoreAlpha / setIgnoreAlpha
getInputLUTID / setInputLUTID
getInvertAlpha / setInvertAlpha
getPixelAspectRatio / setPixelAspectRatio
getRemovePullDown / setRemovePullDown
getVrConform / getVrHorzView / getVrLayout / getVrVertView (+ setters)
```

**No hay rotación.** Es decir: en Premiere Pro 2026 la rotación de despliegue no
es un ajuste que se pueda anular ni forzar sobre un clip maestro. La aplica el
importador de medios al leer el contenedor del archivo, y punto.

## 4. Hallazgo 3 — por qué el Intento B (filtro Basic Motion) nunca pudo funcionar

El handoff concluyó que Premiere "ignoró el filtro" porque `+90` y `-90` se veían
idénticos. La explicación real es estructural:

- El `<filter>` se está insertando en el `<clipitem>` que vive **dentro del
  `<clip>` maestro** (`_clip_xml` → `<media><video><track><clipitem>`).
- Un efecto de movimiento en Premiere se aplica a una **instancia en la línea de
  tiempo**, nunca al clip maestro.
- El síntoma que se observó (abrir el clip desde el bin) es el **monitor de
  origen**, que muestra el medio maestro sin efectos.

Por lo tanto los dos signos se veían iguales porque ninguno de los dos podía
verse: el filtro es irrelevante para lo que se estaba mirando. No fue un problema
de estructura incompleta del efecto, ni de signo.

Corolario importante para el diseño: el export de esta app entrega **bins de
clips maestros y una secuencia vacía** (ver spec, sección de estructura). No hay
`<clipitem>` en la línea de tiempo. Así que la vía del filtro de movimiento no
sirve para este producto aunque se escribiera perfecta.

## 5. Hallazgo 4 (DECISIVO) — el importador nunca lee el archivo

Al importar el XML de variantes, Premiere se cayó. El fallo resultó ser la mejor
evidencia de todo el diagnóstico, porque **antes de caerse Premiere alcanzó a
escribir el proyecto que derivó de nuestro XML**:

```
/var/folders/.../T/rotacion-variantes.prproj
```

(copia conservada en `TEST/rotacion/evidencia-proyecto-derivado-por-premiere.prproj`)

Ese archivo es la interpretación literal que Premiere hizo de cada variante. Los
tres `<VideoStream>` que alcanzó a construir, en orden de documento (B, C, D):

| Variante | Lo que declaraba el `<file>` | `FrameRect` que Premiere derivó |
|---|---|---|
| B | `<media><video></video>` vacío | `0,0,720,480` |
| C | `samplecharacteristics` sin width/height | `0,0,,` (vacío) |
| D | declaración completa 2160x3840 | `0,0,2160,3840` |

Y las otras dos:

- **A** (`<file>` sin bloque `<media>`): Premiere la descartó en silencio. No
  existe en el proyecto derivado.
- **E** (`<file>` sólo con nombre y ruta): es la que provocó el fallo.

**Conclusión: el importador de Final Cut Pro XML de Premiere nunca sondea el
archivo de video.** Construye la descripción del medio exclusivamente con lo que
le declaramos. Si no declaramos dimensiones, no va a buscarlas al archivo: se
inventa un valor por omisión (720x480, un tamaño de televisión antigua), lo deja
vacío, descarta el clip o se cae.

## 6. Hallazgo 5 — el formato de proyecto tampoco tiene rotación

En ese mismo proyecto derivado, los campos de anulación disponibles por stream
de video son:

```
IsPAROverridden / OverriddenPAR
IsFieldTypeOverridden / OverriddenFieldType
IsAlphaTypeOverridden / OverriddenAlphaType
IsIgnoreAlphaOverridden / OverriddenIgnoreAlpha
IsInvertAlphaOverridden / OverriddenInvertAlpha
IsAlphaMatteColorOverridden / OverriddenAlphaMatterColor
```

No hay ninguno de rotación ni de orientación. Cuarta confirmación independiente.

## 7. Conclusión: no es alcanzable, y está demostrado

Juntando los cinco hallazgos:

1. El formato xmeml no tiene etiqueta de rotación a nivel de archivo.
2. El modelo de interpretación de material de Premiere no expone rotación.
3. El importador de XML no lee el archivo para deducir características.
4. El formato de proyecto de Premiere no guarda una anulación de rotación.
5. Un efecto de movimiento sólo aplica a instancias en la línea de tiempo, y este
   producto entrega clips maestros en bins.

**Es imposible entregar un clip maestro correctamente rotado a través de un XML
de Final Cut Pro.** Esto ya no es una hipótesis: es el comportamiento verificado
del programa instalado. Se deja de perseguir.

Esto además explica exactamente lo que se observó en el Intento A del handoff:
al declarar 2160x3840 el clip maestro sí queda con marco vertical (Premiere
respeta la declaración al pie de la letra), pero los píxeles que decodifica
siguen siendo los 3840x2160 acostados del sensor, sin rotar. De ahí "acostado
dentro de un lienzo vertical".

## 8. Qué hacer en su lugar

Consecuencia directa del hallazgo 4: **declarar dimensiones volteadas es
activamente peor que declarar las reales.** Un marco 2160x3840 con píxeles
3840x2160 obliga a Premiere a encajar una imagen apaisada en un marco vertical.
Declarando las reales (3840x2160) el clip queda acostado pero limpio, y el editor
lo endereza en un solo paso.

Cambios propuestos (pendientes de aprobación):

- `probe.py`: dejar de intercambiar width/height para el `<file>`. El
  intercambio **sí** se conserva para la `<sequence>`, porque ahí no hay archivo
  real y el lienzo vertical es lo correcto.
- `xmeml.py`: eliminar `_rotation_filter_xml()` y su llamada. Está probado que no
  puede servir en este producto.
- `models.py`: `ClipSpec.rotation` deja de alimentar un filtro y pasa a alimentar
  la marca visible del clip vertical.
- Marcar los clips verticales de forma visible para el editor (sufijo en el
  nombre del clip maestro), y documentarlo como limitación conocida del formato.

## 9. Anexo — la prueba de variantes

Juntando los hallazgos 1, 2 y 3: la **única** manera de que un clip maestro
llegue derecho es que Premiere lea la matriz de despliegue del archivo por su
cuenta. La pregunta empírica que queda es exactamente una:

> ¿Premiere sondea el archivo (y aplica su rotación nativa) si nuestro `<file>`
> **no** declara las características de medios, en lugar de confiar en lo que le
> declaramos?

El handoff sólo probó variar los **valores** de width/height (volteados y sin
voltear). Nunca probó **omitirlos**.

### La prueba

`scripts/spike_rotacion_variantes.py` genera
`TEST/rotacion/rotacion-variantes.xml` con cinco variantes del mismo clip,
cada una apuntando a una **copia física distinta** (`TEST/rotacion/VARIANTE-*.MP4`)
para que Premiere no las deduplique por ruta ni reuse caché de medios entre ellas.
Lo único que cambia entre variantes es el bloque `<file>`:

| Variante | Qué declara el `<file>` |
|---|---|
| A | nombre, ruta, rate, duración. Sin bloque `<media>`. |
| B | lo anterior + `<media><video></video>` vacío + audio. |
| C | lo anterior + `<samplecharacteristics>` con rate/PAR/campo, **sin** width/height. |
| D | control: la declaración completa de hoy (2160x3840). |
| E | mínimo absoluto: sólo nombre y ruta. |

Se importa una sola vez y se abre el clip de cada bin en el monitor de origen.

**ADVERTENCIA: no volver a importar ese XML.** La variante E tumba a Premiere.
El XML generado se borró a propósito; si se regenera con el script, quitar antes
la variante E de la lista `VARIANTES`. Las cinco copias de video se conservan por
si hace falta otra prueba.

### El resultado (ya obtenido, sin necesidad de abrir Premiere)

No hizo falta que nadie mirara el monitor de origen: el propio proyecto que
Premiere derivó del XML antes de caerse dio la respuesta completa. Ver la
sección 5.
