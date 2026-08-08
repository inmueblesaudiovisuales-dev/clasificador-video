# Handoff de proyecto — Clasificador de Video para Bienes Raíces — 2026-08-06

## Cómo leer este documento

Este es el handoff de **nivel proyecto**, no del plugin. Explica qué es esto, qué tanto se ha construido, y cuál es la siguiente pieza de trabajo. Para el detalle técnico exhaustivo de lo que se construyó ayer y hoy (el plugin UXP), lee `HANDOFF-2026-08-06-plugin-terminado.md`. Para el problema de rotación que definió la arquitectura, `HALLAZGOS-2026-08-05-rotacion-vertical.md` y `HANDOFF-EXHAUSTIVO-2026-08-05.md`. Ninguna decisión aquí es intocable — si aparece un camino mejor, se toma, igual que en los documentos anteriores.

---

## 1. Qué es este proyecto

Bruno es editor de video, trabaja en Adobe Premiere, y produce contenido de bienes raíces (recorridos de propiedades: cocina, recámara, baño, sala, fachada, alberca, etc.), grabando con una Sony FX30 en HEVC 10-bit, a veces vertical.

El cuello de botella no es editar — es la etapa previa: revisar decenas de clips de un shooting, identificar qué cuarto es cada uno, y que eso llegue organizado a Premiere sin arrastrar nada a mano. Hoy eso se hace dentro de Premiere mismo, lento. Prioridad explícita del usuario: **velocidad** — clasificar un shooting completo más rápido que hacerlo a mano en Premiere, idealmente sin usar el mouse.

## 2. La arquitectura decidida: dos piezas que se hablan por un archivo

1. **App externa** (todavía no construida) — donde Bruno clasifica el material: qué cuarto es cada clip, in/out, pick/reject, proxies. Corre fuera de Premiere, en su propia ventana.
2. **Plugin UXP dentro de Premiere** (construido y funcionando) — un panel con un botón. Bruno lo presiona, elige el archivo que la app externa exportó, y el plugin arma el proyecto: bins anidados por cuarto, clips importados respetando su rotación real, in/out marcado, color pick/reject, proxy vinculado.

Se comunican por un **manifest JSON** que la app externa escribe donde Bruno quiera (no hay red, ni servidor, ni carpetas del sistema, ni nada corriendo en segundo plano). El flujo completo: abrir la app externa → clasificar el shooting → exportar el manifest → abrir Premiere → un clic en el plugin → elegir el archivo → el proyecto queda armado.

**Por qué es un plugin UXP y no un XML que Premiere importa** (la arquitectura original, descartada): se descubrió que Premiere nunca abre el archivo de video real al importar un XML de interchange — arma todo solo con lo declarado en el XML, y ese formato no tiene forma de declarar rotación. Un clip vertical siempre se veía acostado, sin solución posible por ese camino. Un plugin que controla Premiere directamente por su API sí abre el archivo real y respeta la rotación — de ahí el giro. Detalle completo en `HALLAZGOS-2026-08-05-rotacion-vertical.md`.

## 3. Qué está construido y funcionando: el plugin UXP

**Completo, verificado, y en uso real.** Organiza el proyecto en Premiere (bins anidados, importar sin duplicar, in/out, color de etiqueta, proxy) a partir de un manifest, con un botón, tolerante a errores por clip.

Verificación: 23 pruebas automáticas contra un Premiere real (`fallidas: 0`) más una sesión de verificación humana de 6 puntos, todos aprobados — incluida la rotación de video vertical, que era el problema que originó todo el proyecto.

Un hallazgo importante de hoy: el mecanismo de instalación que el plan original asumía (copiar una carpeta a mano) **no funciona** en esta versión de Premiere — se investigó en vivo y se encontró el mecanismo real (empaquetar como `.ccx` e instalar con la herramienta UPIA de Adobe). Ya está corregido, documentado, y el plugin está instalado de verdad en la máquina de Bruno, funcionando sin herramientas de desarrollo corriendo. Detalle técnico completo en `HANDOFF-2026-08-06-plugin-terminado.md`.

Lo único que el plugin deja preparado pero sin implementar, a propósito: el armado automático del orden de la secuencia (`uxp-plugin/js/secuencia.js`, función `construirSecuencia` vacía) — decisión explícita de Bruno de que no entra en esta versión.

## 4. Qué NO está construido: la app externa

**Cero código escrito. Sin plan de implementación todavía.** Es la pieza que falta para que el flujo completo exista — hoy el plugin puede recibir un manifest, pero nada en la computadora de Bruno genera ese manifest todavía.

Ya existe un diseño funcional para esta app, en `docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md`, secciones 3 a 8 (y siguientes): ingest por arrastre a carpetas dentro de la app, emparejamiento de proxies por sufijo `S03`, sistema de cuartos con subcuartos anidados, selección por teclado (1-9, sin mouse), reproductor con python-mpv (decodifica HEVC 10-bit con aceleración de hardware real, a diferencia de un navegador) y selector de calidad tipo Premiere, marcado de in/out por frame exacto. Ese diseño viene del handoff original del proyecto (`handoff-clasificador-video.md`, en la raíz del repo) y se mantiene vigente en lo que no cambió por el giro a UXP.

Lo que **sí cambió** respecto al diseño original: ya no se genera un `.fcpxml` — la app externa ahora exporta el manifest JSON que el plugin UXP consume (formato exacto documentado en el spec, sección 11).

## 5. La siguiente tarea: planear el diseño de la app externa

Esto es lo que sigue, y es trabajo de **planeación**, no de construcción todavía — la sesión que empiece esto debe usar el skill de brainstorming/planeación antes de escribir ningún código, siguiendo el flujo habitual de Bruno (una sesión planea, otra programa).

Puntos de partida para esa sesión:

- El spec de arquitectura (`docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md`) ya tiene un diseño funcional de esta app — el punto de partida es revisarlo, no empezar de cero, y decidir qué de ahí sigue vigente, qué falta detallar (por ejemplo: el diseño visual concreto de la interfaz, todavía no explorado a fondo), y qué riesgos técnicos hay que resolver antes de construir (recuerda: Bruno delega el diseño visual a Claude — ver memoria del proyecto).
- Riesgos identificados y sin probar, heredados del spec: miniaturas del filmstrip con ffmpeg respetando la rotación (dueño explícito: la app externa, spec §13), reproducir HEVC 10-bit dentro de la interfaz elegida, autoguardado del progreso de clasificación.
- El formato del manifest que la app externa debe producir ya está fijado por lo que el plugin UXP espera — no es un grado de libertad, es una restricción de diseño (ver spec §11 y `uxp-plugin/js/processManifest.js`).

## 6. Documentos, en el orden en que conviene leerlos

1. Este documento (contexto general).
2. `docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md` (el diseño vigente, plugin + app externa).
3. `docs/superpowers/HANDOFF-2026-08-06-plugin-terminado.md` (detalle técnico del plugin ya construido, por si la app externa necesita saber algo del lado de Premiere).
4. `handoff-clasificador-video.md` (raíz del repo) — contexto de negocio original; útil pero **no es la fuente de verdad** en nada que el spec de arquitectura UXP haya reemplazado.
