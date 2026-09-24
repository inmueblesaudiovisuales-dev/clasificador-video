# Handoff — ¿reemplazar el plugin por XML para resolver rotación?

**Fecha:** 2026-09-23
**Rama:** `master`
**Estado:** investigación pura, sin cambios en el repo. Detenerse aquí hasta
que Bruno decida si se sigue con el spike de `.prproj`.

## Qué es Clipify y dónde vive

Clipify es la app de escritorio (PySide6/Python) que usa Bruno, editor de
video, para clasificar el material de un rodaje (picks, rejects, destacados,
a qué cuarto de la casa pertenece cada clip) antes de editar en Adobe
Premiere Pro. El repo completo está en:

```
/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO
```

Al terminar de clasificar, Clipify exporta un JSON, y un plugin de Premiere
(UXP, en `uxp-plugin/` dentro de este mismo repo) lo lee y arma el proyecto
de Premiere: bins por cuarto, color por cámara, secuencias vacías ya
armadas, y una guía de edición con avance. Ese plugin es la pieza que esta
sesión evaluó reemplazar o achicar.

## Punto de partida

Bruno quería dejar de depender del plugin UXP por completo, con la
motivación de resolver un bug de orientación en clips verticales grabados
con la Sony FX30. La sesión terminó revirtiendo esa premisa: **el plugin
actual no tiene ese bug**. El bug que Bruno recordaba era de cuando probó
el camino de FCP7 XML (`xmeml`) al inicio del proyecto, antes de que el
plugin existiera — confirmado por él mismo a mitad de la sesión.

Aun así, Bruno quiere seguir explorando una vía sin el plugin de hoy (o con
uno mucho más chico), así que la sesión se volvió: *¿existe alguna combinación
de formato de intercambio + herramienta externa que reemplace al plugin sin
perder nada?*

## Lo que se comprobó (con Premiere real, Premiere Pro 2026, versión con
`Basic Motion` no traducible — ver abajo)

1. **La rotación por metadata del archivo SÍ la respeta Premiere en
   importación directa.** Se generaron tres copias sin recodificar del clip
   real `20260910_PIB0001.MP4` (rotación 90°, matriz `Display Matrix`) en
   `/tmp/.../rotacion-spike/`:
   - `A_original.mp4` — igual al original.
   - `B_rotate_tag.mp4` — con el tag clásico `rotate=90` agregado (ffmpeg lo
     fusiona con la misma matriz; no es un mecanismo aparte en MP4).
   - `C_exiftool_matrix.mp4` — matriz reescrita con `exiftool -Rotation=90`.

   Bruno los importó directo (Archivo > Importar) a Premiere: **A y B se ven
   derechos, C sale al revés** (el valor que puso exiftool resultó ser el
   signo contrario). Conclusión: Premiere sí lee la matriz de rotación en
   importación directa — el bug nunca fue eso.

2. **FCP7 XML (`xmeml`) NO puede cargar esa misma rotación, confirmado dos
   veces:**
   - Un XML armado a mano sin ningún filtro deja el clip acostado (esperado).
   - Un XML con un filtro `Basic Motion` (rotación 90°, formato clásico FCP7)
     con el `effectid` correcto **fue rechazado por el traductor de Premiere**:
     el "Translation Report" dice `Effect <Basic Motion> on Clip
     <20260910_PIB0001> not translated`. No tronó ni rotó: lo ignoró.
   - Bruno exportó un XML real desde un proyecto suyo donde el clip SÍ se veía
     derecho en su secuencia (`~/Downloads/exportv2.xml`). **Ese XML no
     contiene ningún dato de rotación en ningún lado** — ni matriz, ni filtro.
     Solo la secuencia declara el tamaño invertido (2160×3840); el `<file>`
     del clip sigue en 3840×2160 sin ninguna instrucción de girarlo. Al
     reimportarlo, sale acostado. Es decir: **ni el propio Premiere logra
     preservar la rotación al pasar por este formato**, no es un problema de
     cómo armamos el archivo.
   - Ese mismo XML sí confirma que **bins, color de clip (`<label2>Iris</label2>`)
     y secuencias con sus ajustes exactos SÍ viajan bien por xmeml** — solo la
     rotación es el problema.

3. **No existe forma de correr un script suelto dentro de Premiere sin
   instalar algo.** Se revisó el menú **Archivo** de Premiere 2026 con Bruno:
   no hay ninguna opción de "Scripts" o "Ejecutar script" (existía en
   versiones viejas vía ExtendScript, ya no). Cualquier código que corra
   dentro de Premiere — aunque sea solo para poner la rotación correcta a un
   clip después de importar el XML — necesita un panel UXP instalado. Es
   decir: técnicamente sigue siendo "un plugin", nomás que puede ser mucho
   más chico que el actual (una sola función, no todo lo que hace hoy).

## Caminos que quedaron sobre la mesa, en orden de qué tan probados están

1. **Seguir usando el plugin actual tal cual.** Ya resuelve todo, incluida
   la rotación (comprobado en el punto 1). No agrega nada nuevo.
2. **Carpetas reales en disco + arrastrar a Premiere.** Cero plugin, cero
   script. Rotación se resuelve sola (importación directa). Se pierde la
   automatización de color y de secuencias — se harían a mano (color por
   cuarto ya agrupado es rápido; secuencias desde un proyecto plantilla que
   Bruno duplica).
3. **XML (bins + color + secuencias, todo confirmado que sí viaja) + un
   panel UXP mínimo que solo corrige rotación después de importar.** Técnica
   propuesta: el plugin actual ya mete efectos a un clip vía la API de
   scripting para el LUT (`AE.ADBE Lumetri`); el mismo mecanismo debería
   servir para tocar el componente `Motion` (el que trae cada clip de fábrica)
   y ponerle el ángulo de rotación correcto, usando la lista de qué clips van
   rotados y cuánto que Clipify ya calcula en `probe.py`. **No probado
   todavía contra la API real de Premiere** — falta el mismo tipo de spike
   que ya se hizo para XML (probar en vivo, no confiar en la documentación de
   Adobe, imprimir los prototipos reales como ya se hace en el resto del
   plugin).
4. **`.prproj` generado directo por Clipify.** El más completo en teoría
   (organización + color + secuencias + rotación en un solo archivo, sin
   Premiere abierto corriendo nada), pero es un formato no documentado —
   riesgo de que un archivo mal armado ni siquiera abra, en la misma familia
   de riesgo que la vía del Blob del LUT que ya tronó Premiere una vez (ver
   `docs/superpowers/archive/RESULTADO-2026-09-08-el-lut-por-la-via-del-blob.md`).
   **Es donde Bruno pidió seguir** al cerrar esta sesión.

## Siguiente paso pedido por Bruno

Intentar el camino del `.prproj`. Antes de escribir código: hace falta un
spike igual de empírico que los de esta sesión —

- Bruno abre un proyecto de prueba chico, aplica a mano lo que se necesita
  (una carpeta/bin, un clip con su color, una secuencia vacía, y sobre todo
  "Interpretar metraje" con la rotación correcta en un clip vertical real) y
  lo guarda.
- Se descomprime el `.prproj` (es XML comprimido) y se compara contra una
  versión sin esos ajustes, para ver exactamente qué nodo guarda la
  rotación y si es editable a mano sin romper el archivo.
- Si el formato es estable entre guardados (mismo proyecto, dos veces) y el
  nodo de rotación es aislable, recién ahí vale la pena intentar generarlo
  desde Clipify.

No se ha tocado ni un archivo del repo en esta sesión — todo lo generado
(los MP4 de prueba y los XML) vive en el scratchpad de la sesión y no se
va a versionar.

## Decisión de arquitectura pendiente de actualizar

Si el spike del `.prproj` (o el del panel mínimo de rotación) resulta
viable y Bruno decide cambiar de vía, el bloque de CLAUDE.md que dice "la
vía real de entrega es el plugin UXP... no reintentar xmeml sin razón
nueva" necesita actualizarse con lo que se comprobó aquí — en particular que
la rotación NUNCA fue un problema del plugin, y que xmeml sigue sin poder
cargarla pase lo que pase.
