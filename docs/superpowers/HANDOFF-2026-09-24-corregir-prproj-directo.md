# Handoff: corregir el `.prproj` directo para que replique Clipify

**Fecha:** 2026-09-24  
**Repositorio:** `/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO`  
**Rama de trabajo:** `master`  
**Estado de la implementación anterior:** Tareas 10 a 15 completadas y commiteadas; la suite terminó en `2170 passed`. No se hizo el checkpoint manual de Premiere de la Tarea 16.

## Objetivo

Corregir el `.prproj` generado directamente para que, al abrirse en Premiere, tenga exactamente la estructura visible de un proyecto nuevo generado por Clipify con el plugin:

```text
Root
├── 01. Secuencia
│   ├── <proyecto> 4K 9:16                 (vacía, 2160 × 3840)
│   ├── <proyecto> 2.7K 9:16               (vacía, 1512 × 2688)
│   ├── <proyecto> 4K 16:9                 (vacía, 3840 × 2160)
│   └── 1080p
│       ├── <proyecto> 9:16 1080p          (vacía, 1080 × 1920)
│       └── <proyecto> 16:9 1080p          (vacía, 1920 × 1080)
├── 02. Clip
│   └── …solo los clips del manifest, en sus sub-bins normales…
├── 03. AE composition
├── 04. Musica
├── 05. Voz
├── 06. Graficos
└── 07. Assets adicionales
```

No debe haber clips de la plantilla, un bin llamado `Bin`, secuencias de referencia, ni items visibles fuera de ese árbol. El LUT de Sony debe ser efectivo al abrir el clip en Premiere, no solo una ruta correctamente escrita en el XML.

## Commits y contexto relevante

La serie más reciente quedó en estos commits:

```text
0d408d3 Clonar un clip real: tiempo, nombre, color y LUT compartido
7db8f10 Localizar las 2 secuencias reales y derivar las otras 3 por medidas
df12ff5 Árbol de bins del proyecto, numerado y con marca de cámara
f08e6a4 generar_prproj: orquesta bins, clips, secuencias y copia de LUTs
347636e Dejar de copiar un .prproj en blanco al crear el proyecto
c273dd9 Ctrl+E genera el .prproj directo; el export para el plugin queda de respaldo
```

La bitácora de la primera implementación está en:

`/.superpowers/sdd/2026-09-23-generar-prproj-directo/progress.md`

Mantener allí una nueva sección por cada corrección y registrar RED/GREEN, resultado de la suite completa y el commit.

## Evidencia observada

Proyecto generado que se inspeccionó:

```text
/Users/brunogutierrez/Library/Mobile Documents/com~apple~CloudDocs/01. Proyectos 2026 IAV y PI/01. IAV/2026/09. Septiembre/IAV-2609.23-A/01. Proyecto premiere/IAV-2609.23-A.prproj
```

Su árbol de `ProjectItemContainer/Items` en raíz contiene, antes de los bins generados:

- clips de referencia de la plantilla (`20260910_PIB0001.MP4`, `DJI_20260910113520_0008_D.MP4`, etc.);
- un `BinProjectItem` llamado `Bin` y vacío;
- otros `ClipProjectItem` de referencia.

`01. Secuencia` está vacío. El generador actual clona objetos `Sequence`, pero no clona/crea el `ClipProjectItem` que Premiere coloca dentro de un bin para representar una secuencia. Por ello las secuencias no quedan organizadas como las del plugin.

El XML generado sí contenía para Sony una ruta de LUT reescrita a:

```text
…/01. Proyecto premiere/LUTs/SONY-SLOG3.cube
```

Así que el defecto del LUT no se debe dar por resuelto cambiando otra vez esa cadena: hay que comprobar qué parte de la cadena de componentes usa realmente Premiere.

Proyecto de referencia generado por el plugin, útil solo para estudiar el enlace XML de una secuencia:

```text
/Users/brunogutierrez/Library/Mobile Documents/com~apple~CloudDocs/01. Proyectos 2026 IAV y PI/01. IAV/2026/09. Septiembre/IAV-2609.10-A V2.prproj
```

Ahí se confirmó que cada secuencia visible aparece como un `ClipProjectItem` dentro de `01. Secuencia` (o su sub-bin `1080p`) y tiene una relación XML con un objeto `Sequence`. No se debe enlazar un `Sequence` directamente en `Items` sin copiar esa estructura real.

## Archivos a revisar primero

- `src/clasificador_video/prproj_generador.py`
  - `generar_prproj()` construye los bins y clona clips/secuencias.
  - `clonar_secuencia_con_medidas()` hoy devuelve/añade un `Sequence`, no su item de proyecto.
  - `_reescribir_ruta_lut()` reescribe valores `StartKeyframeValue` recorridos desde `VideoComponentChain`.
- `src/clasificador_video/prproj_plantilla.py`
  - descubre arquetipos de clips, bin y secuencias dentro de `TemplateColorLuts.prproj`.
- `src/clasificador_video/prproj_xml.py`
  - lectura/escritura gzip y clonado por cierre de referencias.
- `tests/test_prproj_generador.py`
- `recursos/premiere/TemplateColorLuts.prproj`
- `uxp-plugin/js/secuencia.js`
  - comportamiento de referencia del plugin: crea una secuencia, toma su `ProjectItem` y la mueve al bin.
- `uxp-plugin/js/estructura.js`
  - árbol de bins que debe conservarse.

## Regla crítica de reproducción

No validar desde la aplicación instalada de Clipify. Ejecutar la fuente actual y dejar inequívoco qué proyecto produjo:

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git rev-parse --short HEAD
./.venv/bin/clasificador
```

Generar un proyecto de prueba con un nombre nuevo y anotar ruta, fecha y SHA en la bitácora. El proyecto inspeccionado arriba puede haber sido creado antes de arrancar la versión fuente actual; no usarlo por sí solo para atribuir el síntoma a la revisión actual.

## Plan de corrección, en orden

### 1. Fijar una prueba del árbol visible limpio (RED)

Antes de modificar producción, añadir en `tests/test_prproj_generador.py` un helper que resuelva los `ObjectURef` desde el `RootProjectItem` y recorra únicamente el árbol visible de `ProjectItemContainer/Items`.

Escribir una prueba de integración que genere un `.prproj` de fixture y afirme:

- en raíz hay exactamente los siete bins esperados, en el orden definido por `estructura.js`;
- no aparece `Bin` ni ninguno de los nombres de clips de referencia de `TemplateColorLuts.prproj`;
- no hay `ClipProjectItem` ni `Sequence` visibles directamente en raíz;
- `02. Clip` solo contiene los clips esperados del manifest;
- el árbol de `01. Secuencia` se comprobará completo en el paso 3.

Ejecutar primero la prueba focalizada y guardar la salida RED. Debe fallar contra el estado actual porque los items visibles de la plantilla se conservan.

No borrar objetos XML a ciegas. Primero capturar los arquetipos que se necesitan para clonar y después eliminar de los `Items` visibles del root las referencias de la plantilla. Mantener recursos técnicos que sigan siendo alcanzables desde los clones; el requisito observable es que no estén enlazados desde el árbol del proyecto.

Implementar una operación explícita, por ejemplo `limpiar_items_visibles_de_plantilla(raiz)`, antes de crear los bins. No reutilizar el `BinProjectItem` de plantilla como item visible: se usa solo como arquetipo para clonar los siete bins nuevos.

Confirmar GREEN y ejecutar:

```bash
QT_QPA_PLATFORM=offscreen "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/.venv/bin/pytest" tests/ -q
```

Commit sugerido:

```text
Limpiar los items visibles de la plantilla al generar el proyecto
```

### 2. Caracterizar el cierre real de un item de secuencia

Esta es una investigación obligatoria antes de implementar las secuencias. La plantilla actual solo permitió descubrir dos `Sequence` de referencia; eso no prueba que clonar un `Sequence` aislado sea válido.

Usar el `.prproj` histórico generado por el plugin para imprimir el XML mínimo relevante de:

1. un `ClipProjectItem` de una secuencia 4K 9:16 dentro de `01. Secuencia`;
2. el `MasterClip`/objetos que referencia;
3. el `Sequence` alcanzado desde ese cierre;
4. el `ProjectItemContainer/Items` que contiene el item.

La salida debe incluir tags, `ObjectID`, `ObjectUID`, `ObjectURef` y valores de los enlaces, pero no rutas de medios innecesarias. Guardar la conclusión concreta en la bitácora: qué objeto se debe clonar y qué referencia debe reinsertarse en el bin.

Si la plantilla empaquetada no contiene un arquetipo completo de `ClipProjectItem` de secuencia, crear/empacar uno a partir de un proyecto limpio generado por el plugin. El arquetipo debe tener secuencia vacía y no contener media de producción. No inventar la estructura de un `ClipProjectItem` de secuencia: Premiere debe producirla o debe extraerse de la referencia válida.

### 3. Clonar y colocar las cinco secuencias vacías (TDD)

Primero extender la prueba anterior y ejecutarla en RED. Debe exigir exactamente:

- tres `ClipProjectItem` de secuencia directamente en `01. Secuencia`;
- un sub-bin `1080p` en `01. Secuencia`;
- dos `ClipProjectItem` de secuencia dentro de `1080p`;
- las cinco secuencias con las dimensiones del objetivo y `59.94` fps;
- cero clips de vídeo y audio colocados en sus timelines;
- ninguna secuencia visible directamente en Root.

Actualizar `prproj_plantilla.py` para descubrir el arquetipo completo de secuencia (item + cierre), y reemplazar el camino actual de `clonar_secuencia_con_medidas()` por uno que clone esa estructura completa. El `ClipProjectItem` clonado es el elemento que debe añadirse al `Items` del bin; el `Sequence` queda enlazado mediante el mismo patrón que usa Premiere.

Crear el bin `1080p` como hijo de `01. Secuencia`, no como bin raíz. Mantener los nombres del plugin:

```text
<proyecto> 4K 9:16
<proyecto> 2.7K 9:16
<proyecto> 4K 16:9
<proyecto> 9:16 1080p
<proyecto> 16:9 1080p
```

Confirmar GREEN y ejecutar la suite completa.

Commit sugerido:

```text
Crear y ordenar las cinco secuencias vacias como Clipify
```

### 4. Aislar y corregir el LUT Sony (TDD + comprobación en Premiere)

No asumir que la presencia de `SONY-SLOG3.cube` en un `StartKeyframeValue` significa que Lumetri lo aplica. Hacer primero estas comprobaciones, registrando XML real cuando una expectativa falle:

1. Generar un proyecto mínimo con un solo clip Sony y verificar que el archivo `LUTs/SONY-SLOG3.cube` existe antes de abrir el proyecto.
2. Comparar el cierre de referencias desde el `MasterClip` Sony válido de la plantilla contra el del clip Sony clonado: `VideoComponentChain`, `VideoFilterComponent`, parámetros y los `StartKeyframeValue` relevantes.
3. En Premiere, abrir ambos clips y comprobar en **Lumetri Color > Creative/Input LUT** o el control efectivo correspondiente que el LUT está asignado, y mirar el resultado visual.
4. Si el clip válido funciona y el clonado no, probar de una en una estas variantes con proyecto desechable: conservar la cadena original, clonar la cadena por clip, y reescribir la ruta a la copia local. No combinar cambios sin una comparación que los justifique.

Escribir una prueba RED que, como mínimo, compruebe que el clip Sony generado alcanza el componente y parámetro que el clip Sony de referencia usa, y que el valor decodificado es la ruta absoluta del LUT copiado. Si el diagnóstico revela que deben clonarse otros objetos o reescribirse otro parámetro, expresar ese contrato en la prueba antes de cambiar producción.

Implementar solo la corrección respaldada por la comparación. Después de GREEN, repetir la apertura manual del proyecto mínimo: esta es la prueba de aceptación del LUT, no la aserción XML por sí sola.

Ejecutar la suite completa.

Commit sugerido:

```text
Aplicar el LUT Sony efectivo en los clips generados
```

### 5. Regresión de proyecto completo y checkpoint manual

Crear una prueba de integración que compare el árbol visible del `.prproj` generado con el contrato de la sección **Objetivo**. Debe detectar regresiones de los cuatro síntomas:

- LUT Sony apunta al componente efectivo y su archivo está empaquetado;
- cinco secuencias, todas vacías, con nombre, tamaño, fps y bin correctos;
- ningún bin de plantilla llamado `Bin`;
- ningún clip/template item extra visible en raíz o en los bins.

Ejecutar la suite completa y crear un proyecto nuevo desde la aplicación fuente. En Premiere, comprobar manualmente:

- árbol de bins idéntico al de Clipify/plugin;
- las cinco secuencias dentro de `01. Secuencia`, sin clips;
- clips únicamente en los bins de `02. Clip`;
- Sony tiene su LUT aplicado; DJI conserva su comportamiento esperado;
- no hay items raíz adicionales.

Commit sugerido:

```text
Verificar que el prproj directo replica la estructura limpia de Clipify
```

## Disciplina requerida

Para cada paso que cambie código o plantilla:

1. escribir/ajustar prueba;
2. ejecutar la prueba focalizada y confirmar RED;
3. implementar el mínimo cambio;
4. ejecutar y confirmar GREEN;
5. ejecutar siempre al final:

```bash
QT_QPA_PLATFORM=offscreen "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/.venv/bin/pytest" tests/ -q
```

6. actualizar `.superpowers/sdd/2026-09-23-generar-prproj-directo/progress.md`;
7. hacer un commit atómico con el mensaje sugerido del paso.

Cuando un `find`, una aserción o una hipótesis no coincida, imprimir el fragmento XML real y corregir la prueba o la implementación con esa evidencia. No crear `ObjectUID`, `ObjectURef` ni jerarquías de Premiere por inferencia.

## Criterio de salida

El trabajo termina únicamente tras el checkpoint manual exitoso en Premiere con un proyecto nuevo generado desde la fuente actual. No hacer limpieza de rama ni cambiar el flujo de exportación de respaldo antes de ese checkpoint.
