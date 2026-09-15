# Los datos medidos de los 15 entregables de 2026

Las dos mitades del análisis del 2026-09-14. Están aquí y no en el scratchpad
porque son la evidencia de todo lo que se afirma en
[`../PROMPT-NARRACION.md`](../PROMPT-NARRACION.md) y en el spec
`docs/superpowers/specs/2026-09-14-mi-patron-de-recorrido-design.md`.

**`tomas.json` — medido por la máquina.** Los cortes de cada video, detectados
con el filtro `scene` de ffmpeg (umbral 0.25, tomas de menos de 0.35 s pegadas
a la anterior). Por video, una lista de `[número, inicio, fin, duración]` en
segundos. **319 tomas en total.**

**`fichas.json` — etiquetado a mano.** Por video: tipo de propiedad, duración,
con qué abre, con qué cierra, si trae presentadora a cuadro, y qué es cada toma
en orden. Esto **lo leyó un modelo mirando las hojas de contacto**, no salió de
ningún metadato. Si algo se ve raro, se comprueba contra la hoja de ese video
en `~/Movies/patron-2026/tomas/`.

**Los dos se rehacen** corriendo `herramientas/patron-de-recorrido/sacar_tomas.py`
sobre `~/Movies/patron-2026/`, salvo el etiquetado de `fichas.json`, que
necesita que alguien mire.

## Lo que NO está aquí, y dónde sí está

Los 15 videos (8.4 GB), sus hojas de contacto y las transcripciones viven en
`~/Movies/patron-2026/`, fuera del repo. Son material de Bruno, no código.
