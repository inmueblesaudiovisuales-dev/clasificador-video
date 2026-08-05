# Handoff: video vertical se ve horizontal al importar el xmeml en Premiere — SIN RESOLVER

## 1. Contexto del proyecto (para orientarte rápido)

Este proyecto (`clasificador_video`) es la Fase 1 (generador xmeml, sin UI todavía) de una app más grande para clasificar video de bienes raíces y exportar un proyecto de Premiere. El diseño completo está en `docs/superpowers/specs/2026-08-05-clasificador-video-design.md` y el plan de esta fase en `docs/superpowers/plans/2026-08-05-generador-xmeml-validacion.md`.

**Lo que ya está construido y CONFIRMADO funcionando en Premiere Pro 2026** (validado por el usuario con clips reales): bins anidados por cuarto/subcuarto, in/out por número de frame exacto, colores de etiqueta (`<label2>`) para Pick/Reject, reglas de audio (declarar `<audio>` solo si el archivo tiene pista real). Todo esto vive en `src/clasificador_video/xmeml.py` y está cubierto por pruebas en `tests/test_xmeml_*.py` (39 pruebas verdes al momento de este handoff).

**Lo único que NO funciona y motiva este handoff:** cuando un clip es vertical (grabado con la Sony FX30, con metadata de rotación), el video se ve **acostado (horizontal)** dentro de Premiere al importar nuestro XML — a pesar de varios intentos de corregirlo.

## 2. El dato clave que ya se confirmó (no repetir esta prueba)

Se probó arrastrar el archivo de video directo a Premiere, **sin pasar por nuestro XML en absoluto**: el clip se ve **vertical, derecho, correctamente rotado**. O sea:

**Premiere SÍ sabe leer y aplicar la rotación nativa del archivo cuando lo importas normal. El problema está 100% en algo que nuestro XML declara y que le impide a Premiere aplicar esa misma rotación automática cuando el clip llega enlazado a través de un `<file>` de xmeml.**

Esto descarta que el problema sea "Premiere no soporta rotación de esta cámara" — sí la soporta, nomás no cuando pasa por nuestro XML.

## 3. Los datos reales del archivo (ffprobe)

Los 3 clips de prueba están en `TEST/` dentro de este mismo proyecto (carpeta ignorada por git, son archivos reales de la Sony FX30):

```
TEST/20260804_PIB0587.MP4
TEST/20260804_PIB0588.MP4
TEST/20260804_PIB0589.MP4
```

`ffprobe -show_streams` sobre cualquiera de los 3 reporta:

```json
{
  "codec_type": "video",
  "width": 3840,
  "height": 2160,
  "r_frame_rate": "60000/1001",
  "side_data_list": [
    {
      "side_data_type": "Display Matrix",
      "displaymatrix": "...",
      "rotation": 90
    }
  ]
}
```

Es decir: el sensor graba "acostado" (3840×2160) y trae una matriz de despliegue que dice "rota 90° para verlo derecho" (resultando en 2160×3840 vertical). Esto es exactamente el patrón típico de cámaras/teléfonos grabando en vertical.

## 4. Intentos ya hechos — QUÉ SE PROBÓ Y QUÉ PASÓ

### Intento A — declarar width/height "volteados" (2160×3840) en el `<file>` del clip

`src/clasificador_video/probe.py` (`probe_clip` / `_rotation_degrees`) ya lee la rotación de `side_data_list` (o `tags.rotate` en formatos viejos) y, si es 90 o 270, intercambia width/height antes de devolver los metadatos. Esos valores volteados se usan tanto para la `<sequence>` del proyecto como para el `<file>` de cada clip.

**Resultado:** la `<sequence>` (el lienzo del proyecto) sí quedó vertical — Premiere confía en lo que declaramos ahí porque no está ligado a ningún archivo real. Pero el **clip individual siguió viéndose acostado** dentro de ese lienzo vertical. O sea, declarar el ancho/alto volteado en el `<file>` no logró que Premiere rotara el contenido del clip.

### Intento B — filtro `<filter>` Basic Motion con parámetro Rotation

Se agregó a `_clipitem_xml` (en `xmeml.py`) un bloque `<filter>` con un solo parámetro de rotación:

```xml
<filter>
  <effect>
    <name>Basic Motion</name>
    <effectid>basic</effectid>
    <effectcategory>motion</effectcategory>
    <effecttype>motion</effecttype>
    <mediatype>video</mediatype>
    <parameter>
      <parameterid>rotation</parameterid>
      <name>Rotation</name>
      <value>{degrees}</value>
    </parameter>
  </effect>
</filter>
```

Se probaron **ambos signos** (`+90` y `-90`) en un XML de prueba con el mismo clip repetido en dos bins distintos (ver `rotation-test.xml`, no está en git, se generó ad-hoc).

**Resultado:** las dos variantes se vieron **exactamente igual, ambas acostadas**. Ningún signo tuvo efecto — lo cual sugiere que Premiere **ignoró el filtro completo**, no que el signo estuviera mal. Hipótesis (sin confirmar): el efecto "Basic Motion" real de Premiere trae 5 parámetros juntos (Scale, Rotation, Center, Anchor Point, Anti-flicker Filter) y quizás Premiere descarta el filtro completo si no vienen los 5, o el `effectid`/`parameterid` que usamos no es el que Premiere espera internamente (el formato FCP7 XML no está bien documentado en este punto — la documentación oficial de Apple confirma que el parámetro puede llevar `valuemin`/`valuemax` pero no da un ejemplo completo del efecto Basic Motion).

Este código sigue en el repo (commit `c060b0d`) pero **no está confirmado que funcione — probablemente no hace nada**.

### Intento C — declarar width/height SIN voltear (3840×2160, los reales del sensor) en el `<file>`, sin filtro

Se generó un tercer XML de prueba (`rotation-test-raw-dims.xml`, tampoco en git) con las dimensiones reales del archivo (sin intercambiar), sin ningún filtro de rotación — la idea era no interferir con lo que sea que Premiere hace nativamente.

**Resultado:** tampoco funcionó. Sigue viéndose acostado.

## 5. Lo que esto descarta y lo que queda abierto

**Descartado:**
- No es un problema de qué valores de width/height declaramos (ni volteados ni sin voltear resolvieron nada por sí solos).
- No es (aparentemente) resoluble con un filtro `Basic Motion` incompleto de un solo parámetro.
- No es que Premiere no soporte la rotación de este archivo — la soporta perfectamente en un import directo.

**Abierto / sin probar todavía:**
1. **¿Qué es exactamente lo que hace un import directo distinto de un import vía xmeml `<file>`?** Nunca se comparó a nivel de bytes/estructura qué pasa internamente — solo se probaron variaciones de nuestro propio XML. Vale la pena investigar si existe algún tag adicional en el `<file>` o `<clipitem>` de xmeml que preserve o reexponga la matriz de rotación del contenedor (por ejemplo, algo relacionado a cómo FCP7 XML declara pixel aspect ratio, anamorphic, o algún campo de metadata del contenedor que no estemos poniendo).
2. **¿El filtro Basic Motion con los 5 parámetros completos (no solo Rotation) sí funcionaría?** No se probó la versión completa del efecto. Requiere encontrar un ejemplo real de un XML exportado por Premiere/FCP7 que sí tenga un Basic Motion con rotación aplicada, para copiar la estructura exacta byte por byte (búsquedas en Google no dieron un ejemplo completo verificado — puede valer la pena buscar en foros de edición de FCP7/Premiere legacy, o generar un XML de prueba manualmente DENTRO de Premiere: aplicar una rotación de 90° a un clip cualquiera en una secuencia de prueba, exportar esa secuencia como XML (`File > Export > Final Cut Pro XML`), y leer cómo Premiere mismo escribe ese filtro — esa es probablemente la fuente más confiable, ya que sería el propio Premiere generando el formato que él mismo sabe leer).
3. **¿Vale la pena seguir insistiendo en automatizarlo, o es mejor rendirse en la rotación automática?** Se encontró un hilo del foro oficial de Adobe donde editores piden justamente "rotación automática al importar video vertical" como *feature request* — sugiere que ni Adobe mismo lo resuelve bien de forma automática en muchos flujos. Si el punto 2 (exportar un XML de Premiere con rotación aplicada y copiar su estructura) no destraba esto rápido, la alternativa pragmática es: **no intentar rotar automáticamente por XML**, y en cambio hacer que la app marque claramente los clips verticales (por nombre de bin, ej. sufijo "(vertical)", o un color de label distinto) para que el editor aplique la rotación a mano en Premiere en un par de clics — es una limitación conocida y aceptable, no un bug nuestro.

## 6. Dónde está el código relevante

- `src/clasificador_video/probe.py` — `_rotation_degrees()` lee la rotación de ffprobe (`side_data_list` o `tags.rotate`), `probe_clip()` intercambia width/height cuando la rotación es 90/270 y devuelve `"rotation"` en el dict resultante.
- `src/clasificador_video/models.py` — `ClipSpec.rotation: int = 0` (grados de rotación de despliegue).
- `src/clasificador_video/xmeml.py` — `_rotation_filter_xml()` arma el bloque `<filter>` Basic Motion (probablemente no funcional, ver Intento B); `_clipitem_xml()` lo agrega solo si `clip.rotation % 360 != 0`.
- `scripts/spike_export.py` — script manual que genera `spike-output.xml` desde un MANIFEST editable; ya tiene los 3 clips de `TEST/` cargados con sus rutas absolutas reales.
- Pruebas: `tests/test_probe.py` (casos de rotación vía side_data_list y tag viejo), `tests/test_xmeml_clipitem.py` (casos de filtro con/sin rotación). Todas pasan — cubren que el CÓDIGO hace lo que se le pidió, pero no prueban que el resultado se vea bien en Premiere (eso solo se valida a mano, importando).

## 7. Cómo reproducir el problema

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
source .venv/bin/activate
python scripts/spike_export.py   # genera spike-output.xml con los 3 clips reales (todos verticales)
```

Importar `spike-output.xml` en Premiere Pro 2026 (`File > Import...`), abrir cualquiera de los 3 clips — se ve acostado.

Como referencia de comparación, arrastrar cualquiera de los archivos de `TEST/` **directo** a un bin de Premiere (sin XML) — se ve derecho.

## 8. Sugerencia de siguiente paso concreto

El experimento más prometedor y barato que falta hacer: dentro de Premiere, tomar cualquier clip de prueba, aplicarle manualmente una rotación de 90° (Effect Controls > Motion > Rotation, o el efecto "Transform"), armar una secuencia con ese clip, y exportarla como **Final Cut Pro XML** (`File > Export > Final Cut Pro XML...`). Abrir ese XML exportado y ver EXACTAMENTE cómo Premiere mismo escribió el filtro de rotación — esa estructura, copiada tal cual (con los IDs y parámetros reales que Premiere espera), es mucho más confiable que seguir adivinando por búsquedas web. Este es el paso que no se alcanzó a hacer en esta sesión.
