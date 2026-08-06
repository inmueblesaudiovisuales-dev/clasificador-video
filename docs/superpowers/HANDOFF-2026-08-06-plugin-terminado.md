# Handoff — Plugin UXP del Clasificador de Video, terminado — 2026-08-06

## Cómo leer este documento

Este es el cierre del plan `docs/superpowers/plans/2026-08-05-plugin-uxp-premiere.md`
(Tasks 0-14). No es un registro exhaustivo de todo el día — para eso está
`HANDOFF-EXHAUSTIVO-2026-08-05.md` (contexto del proyecto y la investigación
de rotación) y el spec vigente,
`docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md` (la
fuente de verdad sobre qué construye este plugin y por qué). Este documento
contesta una sola pregunta: **¿en qué quedó todo, qué falta, y qué riesgos
hay abiertos?**

## 1. Qué está construido y verificado

El plugin UXP completo (Tasks 0-12 del plan): botón "Importar clasificación"
que abre el explorador nativo de macOS, lee un manifest JSON, y por cada
clip resuelve/crea la cadena de bins anidados, importa o reusa el clip por
ruta en disco, pone in/out directo sobre el clip maestro, aplica color de
etiqueta, y adjunta proxy si corresponde — con manejo de errores tolerante
por clip (uno que falla no detiene al resto) y feedback visible en el panel.
El módulo de secuencia (`uxp-plugin/js/secuencia.js`) existe con la función
`construirSecuencia` vacía, como frontera preparada para el armado
automático futuro — decisión explícita, no pendiente accidental.

**Verificación automática (Tasks 0-12, corrida contra un proyecto real y
desechable de Premiere Pro 26.3.0 a lo largo de toda la construcción):**
23 pruebas de regresión permanentes en `uxp-plugin/js/autocheck-tests.js`,
ejecutadas por el arnés `uxp-plugin/js/autocheck.js` cada vez que el plugin
carga (mientras `AUTOCHECK_ACTIVO = true`). Última corrida antes de apagar
el arnés: **23 pruebas, 0 fallidas.** Cubren, entre otras cosas: bins
anidados con identidad por objeto (no por nombre, distinguiendo dos "Baño"
bajo padres distintos), identidad de clips por ruta en disco (no por nombre
de archivo, con tarjetas de memoria distintas que reciclan el mismo
nombre), in/out, labels, proxy attach/reattach, y que un clip con error no
tumbe el resto del manifest.

**Verificación humana (Task 13, seis puntos, todos confirmados con el
usuario en vivo):**

1. Rotación — clip vertical se ve derecho al importar. Confirmado.
2. Botón + explorador nativo — importó bien con `~/Desktop/prueba-task9.json`,
   canceló bien sin elegir archivo, no tocó ningún archivo del usuario.
   Confirmado.
3. Sin proyecto de Premiere abierto — mensaje correcto, no truena. Confirmado.
4. Instalación real (plugin instalado sin herramientas de desarrollo
   corriendo, `Window > UXP Plugins` lo muestra, clic de prueba funciona
   igual que la copia de desarrollo). Confirmado — **después de resolver el
   Problema 1 de la sección 2.**
5. Arnés de auto-comprobación apagado (`AUTOCHECK_ACTIVO = false`), copia de
   producción reinstalada limpia, panel arranca mostrando solo "Plugin
   cargado." sin ruido de pruebas. Confirmado.
6. Este documento es el reporte final del punto 6.

Nota de precisión sobre el punto 2: el Task 11 (prueba de punta a punta) se
hizo llamando `processManifest` directo en memoria, no escribiendo el
escenario a `~/Desktop/prueba-e2e.json` como sugería el plan originalmente
— la tarjeta de prueba con nombres duplicados (`TEST/tarjeta2/`) ya se había
limpiado según el Paso 5 del propio plan, así que ese manifest habría
fallado si se usaba hoy para una prueba real de botón+diálogo. Para el punto
2 del Task 13 se usó `~/Desktop/prueba-task9.json` (creado en el Task 9, un
manifest de un solo clip, ya confirmado bueno). `prueba-e2e.json` nunca se
creó y no hace falta crearlo — no es un defecto, solo una nota de precisión
para quien busque ese archivo.

## 2. Los dos problemas reales que aparecieron en la verificación humana

El Task 13 no fue un trámite — encontró dos problemas reales que ninguna
prueba automática podía haber atrapado, porque ambos viven fuera de lo que
la API de Premiere puede contestar.

### Problema 1 (el importante): la instalación manual asumida en el plan NO funciona

El plan (Task 10, y la sección 3/5 del handoff original) asumía que copiar
la carpeta del plugin a
`~/Library/Application Support/Adobe/UXP/Plugins/External/<id>_<major>`
(ej. `com.iav.clasificadorvideo_1`) bastaba para que Premiere lo detectara
sin UXP Developer Tools corriendo. **Se confirmó falso en vivo:** tras
copiar con esa convención y reiniciar Premiere dos veces, el plugin nunca
apareció en `Window > UXP Plugins`. El registro que Premiere lee
(`~/Library/Application Support/Adobe/UXP/PluginsInfo/v1/premierepro.json`)
se quedaba en `{"plugins":[]}` — el escáner de Premiere nunca lo registró.

**Causa raíz, confirmada por investigación web (foro de la comunidad de
Adobe, respuesta de un empleado de Adobe):** la convención de nombre de
carpeta del plan estaba mal. Es `<id>_<versión completa de tres partes>`
(ej. `com.iav.clasificadorvideo_1.0.0`), no `<id>_<solo el major>`
(`com.iav.clasificadorvideo_1`). Pero incluso corrigiendo el nombre y
reiniciando, **seguía sin aparecer** — es decir, copiar a mano a `External/`
puede no ser una vía de instalación soportada/confiable para Premiere Pro en
absoluto (a diferencia de otras apps Adobe como Photoshop o InDesign, donde
podría funcionar — nunca se confirmó ninguna de las dos formas). La
documentación oficial de Adobe
(`developer.adobe.com/premiere-pro/uxp/plugins/distribution/install`) solo
documenta tres canales de instalación soportados: Creative Cloud
Marketplace, doble clic en un archivo `.ccx`, y la herramienta de línea de
comandos UPIA — **no documenta la copia manual de carpeta como método
soportado en absoluto.**

**La solución real, descubierta y validada en vivo esta sesión:**

1. Empaquetar el plugin como `.ccx` con la CLI de UXP devtools (ya instalada
   en `/tmp/uxpcli-install`), que requiere el UXP Developer Service corriendo
   primero:
   ```bash
   arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js service start
   # (dejar corriendo en segundo plano)
   cd "uxp-plugin/"
   arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js plugin package --outputPath /tmp/uxp-package-output
   ```
   Produce `com.iav.clasificadorvideo_premierepro.ccx`.
2. Instalarlo con UPIA (Unified Plugin Installer Agent, una herramienta que
   viene con Creative Cloud Desktop), en esta máquina en:
   `/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent`
   ```bash
   "/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent" --install /tmp/uxp-package-output/com.iav.clasificadorvideo_premierepro.ccx
   ```
   Esto sí registra el plugin correctamente en
   `~/Library/Application Support/Adobe/UXP/PluginsInfo/v1/premierepro.json`
   con `"status":"enabled"`, y extrae los archivos en la carpeta `External/`
   con el nombre que Premiere espera. **Confirmado en vivo:** tras esto,
   reiniciar Premiere muestra "Clasificador de Video" en
   `Window > UXP Plugins`, y funciona exactamente igual que la copia cargada
   en modo desarrollo.
3. **Gotcha crítico descubierto — actualizar un plugin ya instalado con solo
   `--install` es un no-op.** UPIA parece tratar un id+versión que ya
   coincide como "ya satisfecho" y no reextrae archivos, incluso si el
   contenido del `.ccx` cambió (confirmado en vivo: repaquetar con un cambio
   de código y reinstalar **no actualizó** los archivos instalados). El
   procedimiento correcto para actualizar es:
   ```bash
   "/path/a/UnifiedPluginInstallerAgent" --remove "Clasificador de Video IAV"
   "/path/a/UnifiedPluginInstallerAgent" --install /tmp/uxp-package-output/com.iav.clasificadorvideo_premierepro.ccx
   ```
   Nota: `--remove` toma el **nombre de la extensión** (el campo `name` de
   `manifest.json`, ej. `"Clasificador de Video IAV"`), **no una ruta de
   archivo** — esto también se descubrió por prueba y error (pasarle una
   ruta falla con status -406).
4. Premiere debe reiniciarse después de instalar y de quitar — los cambios
   quedan registrados/preparados pero la instancia de Premiere que ya está
   corriendo no recarga en caliente la carpeta `External/`.

**Ambos problemas quedaron resueltos y verificados en vivo:** el plugin
instala correctamente, actualiza correctamente, y la copia de producción
(con el arnés de auto-comprobación apagado) está instalada y confirmada
funcionando con una prueba real de clic de botón importando un clip real.

El spec (`§12`) y el `uxp-plugin/README.md` ya se actualizaron con este
mecanismo real — no reflejan más la instalación manual descartada.

### Problema 2 (menor, resuelto): `~/Desktop/prueba-e2e.json` nunca se creó

Ver la nota de precisión al final de la sección 1. No es un defecto, solo
una diferencia entre lo que el plan sugería como artefacto de prueba y cómo
se verificó en realidad.

## 3. Qué NO está construido (fuera de alcance de este plan, correctamente diferido)

- **La app externa (PySide6):** ingest, reproductor, filmstrip, miniaturas
  (y su rotación), exportar el manifest — completamente sin construir, sin
  plan de implementación escrito todavía. Es el siguiente trabajo grande de
  este proyecto. El spec (§13) deja constancia de que las miniaturas del
  filmstrip deben probar explícitamente que ffmpeg respeta la matriz de
  rotación (no asumir "autorotate" activado por default), con los mismos
  clips verticales de `TEST/`.
- **El armado automático de la secuencia:** el módulo
  `uxp-plugin/js/secuencia.js` existe con la función `construirSecuencia`
  vacía (Task 12), lista como frontera, pero sin implementar — decisión
  explícita del usuario, no pendiente accidental. El manifest ya carga
  `orden`, `fps` y `orientacion` (los tres datos que esa función va a
  necesitar) para no tener que rediseñar el formato cuando llegue ese
  trabajo.

## 4. Riesgos abiertos

- **Distribución a otra máquina/editor** requiere que esa máquina tenga
  Creative Cloud Desktop instalado (trae UPIA, para instalar el `.ccx`), y —
  solo si hay que repaquetar tras un cambio de código — la CLI de UXP
  devtools corriendo bajo Rosetta (Apple Silicon). No es un instalador de un
  clic para un usuario final todavía; sigue siendo trabajo de quien
  mantiene el plugin.
- **Deshacer dentro de Premiere no es práctico.** Cada operación (bin,
  in/out, label) es una entrada independiente del historial, y `attachProxy`
  no es reversible en absoluto. Aceptado como limitación de diseño: una
  corrección se hace en la app externa y se reexporta el manifest, no se
  deshace dentro de Premiere.
- **Versión mínima de Premiere Pro 25.1.0+**, validado solo contra 26.3.0.
  No probado en versiones anteriores de la API.
- **`getParentBin()` y `getId()` no existen en runtime** aunque el `.d.ts`
  oficial los declara (confirmado en `uxp-plugin/js/importClip.js`). El
  plugin ya lo resuelve (identidad de carpeta por referencia de objeto
  durante la misma búsqueda), pero es una señal de que la superficie real de
  la API en esta versión de Premiere no coincide del todo con su
  documentación de tipos — vale la pena verificar contra runtime, no solo
  contra el `.d.ts`, si se agrega funcionalidad nueva más adelante.
- El código xmeml obsoleto en `src/clasificador_video/` se dejó en el repo
  con una nota explicando por qué (ver `src/clasificador_video/README.md`)
  en vez de borrarlo — `probe.py` en particular tiene lógica de
  fps/rotación vía `ffprobe` que la app externa va a necesitar. Riesgo bajo:
  que alguien lo confunda con código vivo si no lee la nota.

## 5. Siguiente paso recomendado

Escribir el plan de la app externa (PySide6) — es el trabajo grande que
falta para que el flujo completo (clasificar → exportar manifest → botón en
Premiere) exista de punta a punta. El spec vigente ya tiene todo lo que esa
app necesita saber sobre el manifest que debe producir (§11) y sobre el
plugin que la va a consumir (§12).
