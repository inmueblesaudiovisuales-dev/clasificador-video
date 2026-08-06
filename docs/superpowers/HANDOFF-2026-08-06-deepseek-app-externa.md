# Handoff para construir la app externa — dirigido a DeepSeek — 2026-08-06

## Cómo usar este documento

Este handoff está escrito para que lo ejecutes de principio a fin **sin necesitar que Bruno esté presente**, salvo en los puntos que este documento marca explícitamente como "detente y pregunta". Todo lo demás — decisiones de diseño visual menores, ambigüedades pequeñas de implementación, orden exacto de sub-pasos — decídelo tú, con buen criterio, guiándote por los documentos que este handoff enlaza. Bruno delega el diseño visual y prioriza que la herramienta funcione; no le regreses preguntas granulares.

**Tu tarea es ejecutar un plan ya escrito, no re-diseñar nada.** El plan ya pasó por una sesión de planeación (brainstorming) con Bruno, fue revisado, y está aprobado. Tu trabajo es construirlo tarea por tarea, con TDD, con commits frecuentes, verificando de verdad (no solo afirmando que algo funciona).

## 1. Qué es este proyecto, en una frase

Una app de escritorio (PySide6) donde Bruno clasifica clips de video de un shooting de bienes raíces por cuarto (cocina, sala, recámara...), marca entrada/salida y bueno/malo, y exporta un archivo JSON ("manifest") que un plugin de Adobe Premiere (ya terminado, en `uxp-plugin/`) usa para armar el proyecto de edición solo.

## 2. Qué leer, en este orden, antes de escribir código

1. `docs/superpowers/HANDOFF-2026-08-06-proyecto-clasificador-video.md` — contexto general del proyecto completo (plugin + app externa), qué está hecho y qué falta.
2. `docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md` — el spec de arquitectura original. Secciones §3-§11 son las reglas de negocio de la app externa (ingest, cuartos, teclado, reproducción, in/out, pick/reject, proxies, autoguardado) y **§11 fija el formato exacto del manifest — no es negociable, el plugin ya lo consume tal cual está documentado.**
3. `docs/superpowers/specs/2026-08-06-clasificador-video-app-externa-design.md` — complemento de hoy: valida con material real que mpv (no ffmpeg) resuelve miniaturas y reproducción, y fija layout, estado visual del filmstrip, el diálogo de cuartos, y el ingest multi-carpeta.
4. `docs/superpowers/plans/2026-08-06-app-externa-clasificador.md` — **este es el plan que ejecutas.** 14 tareas en 5 milestones, cada una con TDD completo (test que falla → código → test que pasa → commit). Sigue el formato de checkboxes tal cual.
5. `src/clasificador_video/README.md` — explica qué código viejo del paquete (`models.py`, `rate.py`, `xmeml.py`) es un diseño descartado y **no debe tocarse ni importarse**, y que `probe.py` sí es reusable y se reusa en el plan.

## 3. Qué ya está construido (no lo repitas)

- **El plugin UXP dentro de Premiere: completo, verificado, en uso real.** Vive en `uxp-plugin/`. No necesitas tocarlo — el plan de la app externa solo necesita producir un JSON con la forma exacta de la §11 del spec del 5 de agosto.
- **`src/clasificador_video/probe.py`**: wrapper de `ffprobe` para fps/rotación/duración, con pruebas en `tests/test_probe.py`. Reusable tal cual, ya lo usa el plan si hace falta.
- **Nada del código de la app externa en sí** (PySide6, mpv, cuartos, ingest, filmstrip) existe todavía — el plan que vas a ejecutar es exactamente lo que falta.

## 4. Entorno ya preparado en esta máquina (2026-08-06) — no reinstales de más

- `mpv` (binario + `libmpv`) instalado vía Homebrew: `brew install mpv`. Ya está en `/opt/homebrew/bin/mpv`.
- `ffmpeg`/`ffprobe` instalados vía Homebrew (usados por `probe.py`, no por el reproductor ni las miniaturas — ver §2 del spec del 2026-08-06 sobre por qué la app usa mpv y no ffmpeg para leer video).
- El venv del proyecto (`.venv/`) ya tiene `python-mpv` instalado (se probó en vivo durante el brainstorming). El Task 1 del plan agrega `PySide6` — instálalo ahí, no antes.
- El Task 10 del plan agrega `pytest-qt` — instálalo cuando llegues a esa tarea, no antes.

## 5. Un error real que cometí hoy durante la validación — no lo repitas

Los clips en `TEST/` (`20260804_PIB0587.MP4`, `...0588.MP4`, `...0589.MP4`, y los 5 en `TEST/rotacion/`) son clips de prueba **de 2, 4 y 6 segundos**, creados para verificar la rotación del plugin de Premiere — **no son shootings reales.** Si le pides a mpv o ffmpeg un frame más allá de la duración real del clip, va a fallar (correctamente) y **no es un bug.** Antes de interpretar cualquier fallo de extracción de frame como un problema técnico, verifica la duración real con:

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 archivo.MP4
```

Ya está confirmado y no hace falta re-probarlo: mpv y ffmpeg respetan la rotación de estos clips automáticamente, y `python-mpv` con `hwdec=videotoolbox` decodifica el HEVC 10-bit de la Sony FX30 usando el hardware gráfico de la Mac (evidencia completa en la §2 del spec del 2026-08-06).

## 6. Cómo ejecutar el plan

- Sigue `docs/superpowers/plans/2026-08-06-app-externa-clasificador.md` **tarea por tarea, en orden.** Cada tarea es TDD: escribe el test que falla, corre para confirmar que falla, implementa, corre para confirmar que pasa, marca los checkboxes, comitea. No agrupes varias tareas en un solo commit.
- Los mensajes de commit ya están sugeridos en cada tarea — úsalos o adáptalos, pero mantén el estilo del repo: minúsculas, en español, sin gerundios raros (revisa `git log --oneline -20` para ver el tono real usado en este repo).
- Cuando una tarea incluya una "prueba de humo manual" (por ejemplo Task 8 Step 5, Task 9 Step 5, Task 14 Step 5), **corre el comando de verdad y confirma la salida esperada antes de seguir** — no lo des por hecho porque el código "se ve bien". Usa los clips reales de `TEST/` para esto (recordando la nota de duración del punto 5).
- Al terminar cada Milestone completo, corre toda la suite (`pytest`) para confirmar que nada quedó roto entre tareas: `.venv/bin/pytest -v`.

## 7. Higiene de git — obligatoria, no opcional

- Antes de empezar, corre `git status` y `git log --oneline -10` para confirmar que partes de un estado limpio (el plan ya fue comiteado hoy, junto con los dos specs).
- Un commit por Step de "Commit" del plan, nunca menos granular.
- Nunca uses `git add -A` ni `git add .` — agrega archivos por nombre exacto, como indica cada tarea.
- Nunca hagas `git reset --hard`, `git push --force`, ni reescribas historia. Si algo sale mal, corrige hacia adelante con un commit nuevo.
- Si un hook de pre-commit falla, arregla la causa real y vuelve a comitear — nunca uses `--no-verify`.

## 8. Detente y pregúntale a Bruno solo si pasa esto

- El plan te pide cambiar el **formato del manifest** (§11 del spec original) de cualquier forma — eso rompería el plugin ya terminado y en uso. No lo cambies nunca sin confirmar con Bruno explícitamente.
- Encuentras que algo que el spec o el plan asumen como cierto (sobre mpv, sobre Premiere, sobre el hardware) resulta ser falso al probarlo en esta máquina — un riesgo técnico nuevo, no uno ya resuelto.
- Terminas las 14 tareas del plan y necesitas decidir hacia dónde seguir (el plan mismo lista en su última sección lo que queda fuera: video embebido de verdad en la ventana, drag-and-drop, botón de exportar el manifest, wiring del autoguardado — eso es material para un plan nuevo, no algo que debas improvisar sin spec).
- Para todo lo demás — nombres exactos de variables no especificados en el plan, orden de sub-pasos dentro de una tarea, detalles visuales de estilo que el plan no fijó — decide con el mejor criterio y sigue adelante.

## 9. Definición de "terminado" para este handoff

Las 14 tareas del plan comiteadas, cada una con su test en verde, la suite completa (`pytest -v`) pasando sin fallos, y las tres pruebas de humo manuales (Task 8, Task 9, Task 14) confirmadas contra los clips reales de `TEST/`. En ese punto, deja un resumen corto (qué se construyó, qué pruebas corrieron, qué quedó pendiente según la última sección del plan) para que la siguiente sesión — con Bruno — decida el plan que sigue.
