# Handoff exhaustivo — Clasificador de Video para Bienes Raíces — 2026-08-05

## Cómo leer este documento

Esto no es una lista de reglas a seguir al pie de la letra. Es un registro honesto de todo lo que se investigó, probó, falló y funcionó hoy, para que quien continúe (humano o IA) tenga el contexto completo sin repetir trabajo — pero **sin sentirse limitado por ninguna decisión previa**, incluyendo las de este mismo documento. Si encuentras una solución mejor que lo que aquí se decidió, tómala. La prioridad siempre es lo mejor para el proyecto, no lo más fácil ni lo que ya está escrito.

---

## 1. Qué es este proyecto

Una herramienta para un editor de bienes raíces (graba con Sony FX30, HEVC 10-bit, a veces vertical) que resuelve el cuello de botella real: revisar decenas de clips de un shooting, identificar qué cuarto es cada uno, y que eso llegue organizado a Adobe Premiere Pro — sin arrastrar nada a mano, sin tocar los archivos originales, rápido (idealmente sin usar el mouse).

Documento de arranque original: `handoff-clasificador-video.md` (raíz del proyecto) — proponía FCPXML y un reproductor propio. **Ya no es la fuente de verdad**; casi todo lo que proponía sobre el mecanismo de entrega a Premiere quedó descartado por lo que se aprendió hoy. Sigue siendo útil para el contexto de negocio (quién es el usuario, qué cámara usa, por qué importa la velocidad).

---

## 2. El camino recorrido hoy — cronología honesta

### 2.1 Primer intento: generador de xmeml (Final Cut Pro 7 XML)

Se construyó un generador completo en Python (`src/clasificador_video/`: `rate.py`, `models.py`, `probe.py`, `xmeml.py`) con TDD, 39 pruebas, que arma un documento xmeml con bins anidados por cuarto/subcuarto, in/out por frame, y colores de etiqueta (`<label2>`) para pick/reject. Reutilizaba una plantilla ya validada en un proyecto hermano (`iav-metadata-app`). **Este código sigue en el repo, funcional, pero quedó obsoleto para el propósito de conectar con Premiere** — el problema que lo tumbó fue la rotación (ver 2.2). Podría reciclarse si en algún momento se necesita generar xmeml por otra razón, pero no es el camino para este proyecto.

Se probó con 3 clips reales del usuario (`TEST/20260804_PIB0587.MP4`, `...0588.MP4`, `...0589.MP4`, todos verticales — rotación 90° en la matriz de despliegue del archivo, grabados acostados en el sensor a 3840×2160, se despliegan a 2160×3840). Ahí apareció el problema central del día.

### 2.2 El problema de rotación — todo lo que se intentó

**Síntoma:** un clip vertical, importado vía nuestro xmeml, se ve acostado en Premiere. Arrastrado directo (sin XML), se ve derecho.

**Intentos, en orden, todos documentados con más detalle en `HANDOFF-2026-08-05-rotacion-vertical-sin-resolver.md` y `HALLAZGOS-2026-08-05-rotacion-vertical.md`:**

1. Declarar width/height "volteados" (2160×3840) en el `<file>` del clip → la `<sequence>` sí quedó vertical (Premiere confía en eso porque no hay archivo real detrás), pero el clip individual seguía acostado dentro de ese marco vertical (imagen deformada).
2. Filtro `<filter>` Basic Motion con parámetro Rotation, probado con signo `+90` y `-90` → sin ningún efecto visible, los dos se veían iguales.
3. Declarar las dimensiones reales sin voltear (3840×2160), sin filtro → seguía acostado.

**Investigación de otra sesión de IA**, leyendo literalmente el binario instalado de Premiere Pro 2026 (`strings` sobre el ejecutable) y capturando un `.prproj` real que Premiere derivó de un XML de prueba antes de tronar por una variante mal formada. Sus 5 hallazgos, con evidencia dura:

1. El vocabulario de xmeml que Premiere sabe leer no tiene ninguna etiqueta de rotación a nivel de archivo — la única aparición de `rotation` es como parámetro de un efecto de movimiento.
2. La API de `FootageInterpretation` (Interpretar material) no expone rotación.
3. El importador de XML **nunca abre el archivo de video real** — arma todo solo con lo declarado en el XML (confirmado con el `.prproj` derivado: valores no declarados se inventan por default, ej. 720×480, o tumban Premiere).
4. El formato de proyecto (`.prproj`) tampoco tiene un campo de anulación de rotación.
5. Un efecto de movimiento solo aplica a instancias en la línea de tiempo, nunca a un clip maestro en un bin — y el diseño de este proyecto entrega bins con clips maestros, sin secuencia poblada. Por eso el Intento 2 nunca pudo funcionar: el filtro estaba en el lugar equivocado de la estructura.

Conclusión de esa investigación: **"no es alcanzable, está demostrado."** El usuario no estuvo de acuerdo — su razón: "antes no sucedía este problema", y confirmó que "antes" también era importando por un XML generado (otra herramienta, mismo tipo de problema, sí funcionaba). Eso motivó seguir buscando en vez de aceptar la conclusión de "imposible".

**El error en el razonamiento de "imposible":** el hallazgo 5 (efectos solo aplican en línea de tiempo) es correcto, pero la conclusión de que por eso "es imposible" asumía que la única forma de aplicar un efecto era vía xmeml. No consideró que Premiere sí permite aplicar efectos a un clip maestro en un bin **desde su propia interfaz** (arrastrando el efecto Transform sobre el clip, sin secuencia) — esto se confirmó investigando por fuera (búsqueda web + comunidad de Adobe), y luego se confirmó con el usuario probándolo a mano: sí giró la imagen, pero con barras negras (el cuadro del clip no cambia de forma, solo el dibujo adentro rota).

Eso llevó a investigar si existía una forma de **cambiar el cuadro mismo** (no solo rotar el dibujo) sin secuencia — la respuesta, confirmada con la misma rigurosidad (Interpretar material no lo expone, no hay atajo), fue que no. Ahí se escribió un prompt para que otra IA investigara más (`PROMPT-INVESTIGACION-2026-08-05-rotacion-vertical.md`), pero antes de mandarlo, surgió la idea que sí funcionó (ver 2.3).

### 2.3 El giro que funcionó: UXP scripting

La idea: en vez de generar un archivo XML que Premiere interpreta a ciegas, **hacer que un script controle Premiere directamente**, usando su API de scripting (UXP). La operación `importFiles` de esa API es el mismo código que usa Premiere cuando arrastras un archivo a mano — por lo tanto, si el problema era que el importador de XML nunca abre el archivo real, un import por API sí lo abre, y sí debería respetar la rotación.

**Se confirmó, con el clip real, de inmediato: sí respeta la rotación.** A partir de ahí se probó, y se confirmó, que la misma API también permite: crear bins anidados, poner color de etiqueta, y poner in/out directo sobre el clip — **las cuatro cosas a la vez, para los 3 clips reales, en una sola corrida, sin conflicto entre sí.**

### 2.4 Errores de configuración en el camino (para no repetirlos)

- El primer manifest.json del plugin de prueba usaba `"host": [{"app": "PPRO", ...}]` (formato de lista, id en mayúsculas) → UDT mostraba "App not supported". El formato correcto, confirmado leyendo el paquete oficial `@adobe/premierepro` (los `.d.ts` reales, descargados de npm), es `"host": {"app": "premierepro", "minVersion": "25.1.0"}` (objeto, no lista; id en minúsculas).
- `project.executeTransaction(...)` llamado directo (sin envolver) falla con `"The script object is no longer valid."` — el patrón correcto, confirmado contra el código de ejemplo oficial de Adobe (`AdobeDocs/uxp-premiere-pro-samples`), es envolverlo siempre en `project.lockedAccess(() => { project.executeTransaction(...) })`.
- Un primer intento de subclip con in/out fuera del rango real del clip (out=200 en un clip de 120 frames) produjo cuadros congelados al final — no era un bug del mecanismo, era un dato de prueba mal puesto (el clip de prueba duraba menos de lo que se le pidió recortar).
- Se reconsideró usar **subclips** (`createSubClipAction`, crea un ítem nuevo en el bin) contra **in/out directo sobre el clip maestro** (`createSetInOutPointsAction`, mismo ítem, sin duplicar) — se eligió la segunda, más limpia, un solo ícono por clip.
- Al buscar documentación real de la API, **el sitio de docs de Adobe (`developer.adobe.com/premiere-pro/uxp/...`) es difícil de leer por fetch automatizado** (contenido cargado por JS, respuestas parciales/inútiles varias veces). Lo que sí funcionó de verdad: descargar el paquete npm `@adobe/premierepro` (tiene un archivo `.d.ts` con la firma real de cada clase/método) y el repo de ejemplos oficiales `AdobeDocs/uxp-premiere-pro-samples` (código TypeScript real, funcional, con los patrones correctos como `lockedAccess`). Esa fue la fuente confiable, no las búsquedas web genéricas ni el sitio de docs.

---

## 3. Hechos técnicos confirmados hoy (con evidencia, no suposición)

- `project.importFiles(rutas, suppressUI, binDestino, asNumberedStills)` — importa dentro de un bin específico, **preserva la orientación real del video** (confirmado con 3 clips verticales reales).
- Rotación de un archivo se lee de `ffprobe` en `video_stream.side_data_list[].rotation` (formato moderno, "Display Matrix") o `video_stream.tags.rotate` (formato viejo) — normalizar con `% 360`. Si es 90 o 270, hay que intercambiar width/height reportados (el sensor graba acostado).
- Bins: `folderItem.createBinAction(nombre, makeUnique)` devuelve una `Action` que se agrega a un `CompoundAction` dentro de `executeTransaction`, envuelto en `lockedAccess`. Funciona anidado (bin dentro de bin, llamando `createBinAction` sobre el `FolderItem` del bin padre, no solo sobre `rootItem`).
- Label de color: `clipItem.createSetColorLabelAction(premierepro.Constants.ProjectItemColorLabel.NOMBRE)` — usar la constante (`FOREST`, `ROSE`, `MAGENTA`, etc.), no un índice numérico crudo.
- In/out directo sobre el clip maestro (sin crear un ítem nuevo): `clipProjectItem.createSetInOutPointsAction(inPoint, outPoint)`, con `TickTime.createWithFrameAndFrameRate(numeroDeFrame, FrameRate.createWithValue(fps))`.
- Subclip (crea un ítem NUEVO y separado en el bin, el original se queda intacto también): `clipProjectItem.createSubClipAction(nombre, startTime, endTime, hasHardBoundaries, opciones)`. Se decidió no usarlo para este proyecto (se prefiere in/out directo), pero existe y funciona si se necesita en otro contexto.
- Proxy: `clipProjectItem.attachProxy(rutaProxy, esAltaRes)` — confirmado que existe en la API (no se alcanzó a probar en vivo con el proxy real del usuario, `TEST/20260804_PIB0587S03.MP4`, mismo nombre + sufijo `S03` antes de la extensión — esto sí quedó pendiente de probar, ver sección 5).
- Buscar si un clip ya existe en el proyecto por su ruta real: `clipProjectItem.getMediaFilePath()` (recorrer el árbol de bins comparando contra la ruta buscada) — usado para no duplicar clips en reexportaciones.
- Instalación del plugin sin UXP Developer Tools corriendo: copiar la carpeta a `~/Library/Application Support/Adobe/UXP/Plugins/External/<id>_<version>` (nombre exacto de carpeta: id del manifest + guion bajo + versión). Confirmado por documentación oficial, no probado en vivo todavía.
- Premiere Pro instalado: versión 26.3.0 (build 93). El paquete `@adobe/premierepro` de esa versión funcionó con `minVersion: "25.1.0"` en el manifest.

---

## 4. Arquitectura decidida (sujeta a cambio si aparece algo mejor)

Documentada completa en `docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md`. Resumen:

- **App externa** (PySide6 + python-mpv + ffmpeg) donde el usuario clasifica: ingest por drag-and-drop a carpetas dentro de la app (sin lógica de "tipo de cámara", el usuario organiza como quiera), reproductor con selector de calidad tipo Premiere, leyenda de cuartos con subcuartos, filmstrip, atajos de teclado fijos, autoguardado atómico, clic derecho en carpeta para vincular proxies (por sufijo `S03` en el nombre).
- **Plugin UXP** dentro de Premiere: vigila una carpeta de manifests JSON, y por cada uno arma bins anidados, importa (o reusa si ya existe, para no duplicar en reexportaciones), pone in/out, label, y adjunta proxy. Tolerante a errores por clip individual. Con feedback visible en el panel, no solo consola.
- Se comunican por un **manifest JSON** en una carpeta compartida — sin red, sin servidor.

Plan de implementación del plugin ya escrito: `docs/superpowers/plans/2026-08-05-plugin-uxp-premiere.md` (11 tareas, cada una verificada a mano contra Premiere real porque no hay corredor de pruebas automatizado para UXP). El plan de la app externa (PySide6) **todavía no se ha escrito**.

---

## 5. Lo que falta — sin resolver, sin probar, o solo parcialmente confirmado

- **`attachProxy` nunca se probó en vivo** contra el proxy real del usuario — solo se confirmó que el método existe en la API. Es el primer riesgo técnico a validar del plan del plugin (Task 6).
- **La instalación sin UDT** (copiar carpeta a `~/Library/Application Support/Adobe/UXP/Plugins/External/`) tampoco se probó en vivo — solo está confirmada por documentación.
- **Miniaturas del filmstrip con ffmpeg y rotación** — riesgo identificado pero no probado: hay que confirmar que ffmpeg respeta la matriz de rotación al extraer un frame, o se puede repetir el mismo problema de hoy pero en la app propia.
- **Reproducir HEVC 10-bit dentro de un panel UXP** (si en algún momento se reconsidera meter el reproductor dentro de Premiere en vez de una app aparte) — nunca se probó, es la razón original por la que se descartó construir todo dentro de un panel.
- **Foco de teclado dentro de un panel UXP** (si compite con los atajos nativos de Premiere) — tampoco se probó, mismo caso.
- La app externa (PySide6) — el ingest, el reproductor, el filmstrip, el autoguardado, la exportación del manifest — está completamente en diseño (spec), nada de código escrito todavía. No hay plan de implementación para esta pieza.
- Manejo de duplicados/reexportación en el plugin (`findClipByPath`) está en el plan pero no se ha corrido — la lógica de recorrer el árbol de bins buscando por ruta no se ha probado en vivo.

---

## 6. Lo que NO limita el trabajo futuro

Ni este documento, ni el spec, ni el plan, ni el documento original del proyecto, son reglas fijas. Son el mejor entendimiento a la fecha de hoy. Si en el camino aparece una vía mejor — más simple, más robusta, más rápida de construir, lo que sea — se toma esa, así signifique reabrir una decisión que hoy parecía cerrada. La única prioridad real es que el resultado sea lo mejor posible para este proyecto y para quien lo va a usar todos los días.
