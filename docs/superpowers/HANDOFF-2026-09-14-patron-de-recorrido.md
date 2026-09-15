# Handoff — el patrón de recorrido, sacado de lo ya entregado

*2026-09-14. Rama `orden-sugerido-de-cuartos`, no `master`.*

## Dónde quedó

La pestaña «Orden sugerido» del plugin ya existe y funciona, pero sugiere el
orden **de manual**. Bruno quiere que sugiera **el suyo**, sacado de los videos
que entregó en 2026.

El diseño está escrito y commiteado:
**`docs/superpowers/specs/2026-09-14-mi-patron-de-recorrido-design.md`**.
**Bruno todavía no lo ha aprobado** — ese es el gate. No escribir el plan de
implementación hasta que lo lea y diga que va.

## Lo que ya se hizo a mano, y no hace falta repetir

Los pasos 1 a 3 del §9 del spec están hechos:

1. **Se listaron los entregables** de Drive: 35 proyectos, 28 con archivo.
2. **Bruno podó la lista** en un artefacto de casillas: **quedaron 15**.
3. **Están los 15 en el disco**, en `~/Movies/patron-2026/` (8.4 GB) — cinco
   copiados de sus SSD y diez bajados de Drive con `rclone` (remote `drive:`,
   solo lectura, ya configurado en esta Mac).

Y se fue más lejos de lo planeado: **ya se analizaron los 15**, sin Gemini y
sin gastar un peso. Se detectaron los cortes con ffmpeg, se armó una hoja de
contacto por video y un modelo las leyó.

## Lo medido

**319 tomas en 15 videos.** Los números viven en
`docs/patron-de-recorrido/datos/` con su `LEEME.md`.

- **Abre por el aire**: 10 de 15 abren con una aérea. **Cierra por el aire**:
  10 de 15.
- **El orden**, de 0 (arranque) a 1 (final): fachada 0.24 · **cocina 0.28** ·
  sala 0.31 · comedor 0.32 · recámaras 0.55 · baños 0.62 · amenidades 0.76.
  **La cocina va antes que la sala**, que es lo contrario del orden de manual.
- **Las aéreas están en los 15**, con el peso hacia el final (0.56): no son
  solo la apertura, son un bloque antes de cerrar.
- **Ritmo**: 2.2 s por toma, mediana 1.9. La primera dura 2.6 s y **la última
  5.3** — cierra al doble de largo de lo que edita en medio.
- **Duración**: de 29 a 80 s, mediana 45. **Todo su material entregado es
  short-form.**

## Lo que salió de paso: la narración

Bruno pidió aparte el análisis del audio. Se extrajo, se transcribió con
Whisper local y se midieron 103 frases. **12 de los 15 traen narración**; tres
van con música sola.

De ahí salió `docs/patron-de-recorrido/PROMPT-NARRACION.md`, y todo eso ya
viajó al repo `estudio-iav` (`docs/prompts/patron-de-narracion.md` y
`transcripciones-2026.md`), que es donde Bruno lo va a usar. **Esa rama de
trabajo está cerrada aquí.**

El hallazgo que sí toca a Clipify: **la narración sigue siempre el mismo orden
que la imagen**, en los 12. El patrón de recorrido y el de guion son el mismo,
así que el orden que sugiera la pestaña es también el orden de lo que se dice.

## Las tres preguntas, ya contestadas

Las tres las cerró Bruno el mismo 2026-09-14. Quedan aquí con su respuesta
porque las tres tocan el diseño.

1. **Los tres videos sin narración son los tres de agosto.** No dejó de narrar:
   **algunos clientes los piden sin voz.** Entonces no hay corte temporal que
   respetar —no es que a partir de agosto edite distinto— y los tres entran al
   patrón con el mismo peso que los demás. La narración es una petición del
   cliente, no una etapa suya.
2. **La pestaña se queda corta con los tipos de propiedad.** Se amplía a
   **seis: Casa, Departamento, Terreno, Local, Quinta de campo y Hospedaje.**
   Son exactamente los que salieron en los 15 entregables de 2026 —casa 6,
   departamento 3, terreno 2, quinta 2, local 1, hospedaje 1—. Se le ofreció
   una lista larga con los tipos del rubro que hoy no le salieron (oficina,
   bodega, edificio, penthouse, loft, rancho) y **escogió los seis suyos**.
   Mismo criterio que el resto del proyecto: la lista sale de su material, no
   de lo que podría pasar. Es un quinto cambio en la pestaña, encima de los
   cuatro del §6 del spec.
3. **La presentadora y los videos largos son de marzo a mayo.** Bruno ya
   contestó que **depende del cliente**, así que esos tres se quedan con el
   mismo peso que los demás.

## El cambio de rumbo del mismo día

Bruno leyó el spec descrito en voz alta y preguntó por qué la guía se arma en
Premiere si los cuartos nacen en Clipify. **Tiene razón y el diseño se movió.**
Está escrito en
[`specs/2026-09-14-guia-de-edicion-en-clipify-design.md`](specs/2026-09-14-guia-de-edicion-en-clipify-design.md):
la guía se arma en Clipify con su propio botón, viaja congelada en el manifest,
y el panel de Premiere solo la lee. Las carpetas de cuartos llegan numeradas en
ese orden.

El patrón de recorrido **no cambia en nada** — cambia dónde se usa.

## Lo que sigue

1. Que Bruno lea los specs y los apruebe o los corrija.
2. Con eso, **el paso 5**: convertir las 15 fichas en el documento del patrón
   (§5 del spec) — prosa natural, **sin cuentas y sin justificarse**, con su
   lista de orden. Es la regla que más pidió y la más fácil de romper.
3. Y luego los cuatro cambios en la pestaña (§6 del spec).

**Ojo con el §4.d del spec**: dice que los videos van a Gemini. Ya no hace
falta para el análisis —se hizo aquí, leyendo hojas de contacto—, pero el spec
no se ha actualizado. Si se rehace el análisis el año que entra, decidir cuál
de los dos caminos queda escrito.
