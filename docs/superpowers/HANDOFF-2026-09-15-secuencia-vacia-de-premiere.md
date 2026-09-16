# Handoff — secuencia vacía de Premiere

**Fecha:** 2026-09-15  
**Rama:** `master`  
**Estado:** detenerse aquí hasta que Bruno confirme la siguiente etapa

## Git y cambios ajenos

El repo estaba en `orden-sugerido-de-cuartos`, 71 commits adelante de
`master`, con tres cambios ajenos sin commit. Se guardaron temporalmente, se
integró la rama a `master` y se restauraron intactos.

Commit creado: `973d55b Integrar el orden sugerido de cuartos en master`.

Los cambios ajenos siguen fuera de commits:

- `docs/DESARROLLO.md`
- `uxp-plugin/index.html`
- eliminación de `uxp-plugin/js/autocheck-tests.js`

## Decisiones aprobadas

1. Solo los JSON nuevos crean secuencia. Los anteriores importan clips y bins,
   pero no crean ninguna.
2. Clipify siempre ofrece `4K 9:16`, `2.7K 9:16` y `4K 16:9`.
3. La mayoría de clips sugiere orientación, no decide entre 4K y 2.7K.
4. Si gana vertical y existe cualquier original vertical 2.7K, Bruno escoge
   entre las dos opciones verticales sin una preselección.
5. La secuencia queda vacía. Ningún clip entra al timeline automáticamente.

El diseño completo está en
`docs/superpowers/specs/2026-09-15-secuencia-vacia-de-premiere-design.md`.

## Implementación escrita y sin commit

- `src/clasificador_video/probe.py`: calcula la sugerencia.
- `src/clasificador_video/manifest.py`: agrega `formato_secuencia` opcional.
- `src/clasificador_video/ui/main_window.py`: diálogo y escritura de elección.
- `uxp-plugin/js/secuencia.js`: nombre, ajustes, dedupe, creación y movimiento.
- `uxp-plugin/js/processManifest.js`: llama la creación después de importar.
- `uxp-plugin/manifest.json`: versión 1.4.0 y Premiere mínimo 26.2.
- `uxp-plugin/README.md`: documenta el mínimo.
- Pruebas Python y `uxp-plugin/pruebas/secuencia.pruebas.js`.

No mezclar estos archivos con los tres cambios ajenos al preparar el commit.

## TDD y resultados

Primero se observaron fallas porque no existían `sugerencia_de_formato`, el
campo `formato_secuencia` ni `datosDeSecuencia`.

Resultados posteriores:

- pruebas dirigidas Python: **31 aprobadas**;
- corredor JavaScript: **34 aprobadas, 0 fallidas**;
- primera suite completa: **1770 aprobadas y 1 timeout** ajeno en
  `test_pedir_la_guia_devuelve_de_inmediato`;
- repetición aislada: **1 aprobada**;
- segunda suite completa: **1771 aprobadas** en 23.56 s.

Bruno pidió no repetir baterías grandes innecesariamente. En la siguiente
etapa no se repite la suite completa si no hay cambios que lo justifiquen.

## API real de Premiere 26.3

Se cargó el plugin de desarrollo y se enumeraron métodos de los objetos reales.
Premiere confirmó que existen:

- `Project.createSequence`
- `Project.createSequenceWithPresetPath`
- `Project.getInsertionBin`
- `Sequence.getProjectItem`
- `Sequence.getSettings`
- `SequenceSettings.setVideoFrameRect`
- `SequenceSettings.setVideoFrameRate`
- `SequenceSettings.setVideoFieldType`
- `SequenceSettings.setVideoPixelAspectRatio`

El diagnóstico temporal se retiró del repo y de la copia instalada.

## Validación real pendiente

Premiere 26.3 y `testsecuencias.prproj` estaban abiertos. Se prepararon:

- `/tmp/clipify-secuencia-vacia.json`
- `/Users/brunogutierrez/Downloads/clipify-secuencia-vacia.json`

La importación no se ejecutó. Todavía **no está comprobado en Premiere** que:

- la secuencia se cree dentro de `01. Secuencia`;
- quede vacía;
- tenga 2160 × 3840 y 59.94 fps;
- el segundo import no duplique ni modifique la existente;
- el aviso se vea correctamente.

Tampoco se validaron en vivo `2.7K 9:16` ni `4K 16:9`.

## Riesgos antes del commit de función

1. Confirmar si `project.createSequence(nombre, "")` acepta el preset vacío.
2. Confirmar que `createSetSettingsAction` aplica todos los ajustes juntos.
3. Confirmar que `sequence.getProjectItem()` devuelve un item movible al bin.
4. Confirmar el dedupe real por nombre dentro de `01. Secuencia`.
5. Revisar visualmente el diálogo de elección de Clipify.

## Siguiente etapa, solo con confirmación de Bruno

1. Importar una vez el JSON temporal.
2. Inspeccionar bin, timeline y ajustes.
3. Importarlo una segunda vez y revisar aviso/dedupe.
4. Si la API difiere, agregar una sola prueba enfocada y corregir ese hallazgo.
5. Retirar los JSON temporales.
6. Preparar commits lógicos sin incluir los cambios ajenos.

