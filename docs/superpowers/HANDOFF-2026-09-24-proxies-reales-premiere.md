# Handoff: Premiere aún no reconoce correctamente los proxies reales

**Fecha:** 2026-09-24  
**Repositorio:** `/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO`  
**Rama:** `master`  
**Último commit relevante:** `8f6eb48 Calcular rutas relativas reales de Premiere`

## Estado real

Bruno abrió en Premiere un `.prproj` creado por Clipify y reportó que los
proxies no aparecen enlazados y que los nombres de clips no cambian. No se
debe dar esta entrega por validada hasta reproducir y resolver ese resultado
en Premiere.

El archivo inspeccionado fue:

```text
/Users/brunogutierrez/Library/Mobile Documents/com~apple~CloudDocs/01. Proyectos 2026 IAV y PI/01. IAV/2026/09. Septiembre/IAV-2609.23-A/01. Proyecto premiere/IAV-2609.23-A v6.prproj
```

## Lo que sí contiene `v6` (evidencia XML)

El XML de `v6` no está vacío ni apunta a proxies inventados:

- 8 `Media` con `IsProxy=true`.
- 8 enlaces `VideoMediaSource/MediaSource/Content/ProxyMedia`.
- 8 archivos proxy existentes en disco, bajo `03. Proxies`.
- Los Sony llevan dos `AudioProxyItem` por clip; los drones no llevan audio,
  coherente con su media.
- Los items visibles ya contienen nombres nuevos, por ejemplo:
  `COCINA-01 ✓ [SONY]`, `COMEDOR-01 ✓ [SONY]`,
  `FACHADA-01 ✓ [DRONE]` y `AMENIDADES-02 ✕ [DRONE]`.

Para `COCINA-01 ✓ [SONY]`, el XML vincula específicamente:

```text
original: .../01. VIDEOS SONY/20260910_PIB0001.MP4
proxy:   .../03. Proxies/01. VIDEOS SONY/20260910_PIB0001S03.mp4
```

Por ello el problema no es que `v6` haya elegido otro archivo de proxy. Si
Premiere no muestra esos nombres, comprobar primero que se abrió exactamente
`IAV-2609.23-A v6.prproj`, no una versión previa ni una copia recuperada.

## Defecto confirmado en `v6`

Las rutas relativas se escribieron mal. Ejemplo observado:

```text
../Users/brunogutierrez/Library/Mobile Documents/...
```

Esa ruta no es relativa a `01. Proyecto premiere`; puede impedir que Premiere
resuelva o acepte el proxy aunque `FilePath` y `ActualMediaFilePath` sean
absolutas y correctas.

El commit `8f6eb48` corrige esto usando `os.path.relpath(ruta,
destino.parent)`. Un proyecto generado después de ese commit debe contener,
para el caso anterior:

```text
../03. Proxies/01. VIDEOS SONY/20260910_PIB0001S03.mp4
```

`v6` no se modifica retroactivamente: se requiere un proyecto nuevo y una
apertura manual nueva en Premiere.

## Correcciones ya hechas, aún sin aceptación manual

1. Proxies Clipify nuevos usan `<stem>_proxy.mp4`; la búsqueda conserva los
   `S03` existentes.
2. El exportador consume `Clip.ruta_proxy`, que es la ruta que Clipify validó,
   no deriva una ruta alternativa al generar el `.prproj`.
3. La validación acepta un `S03` de menor resolución si conserva proporción de
   despliegue, fps y número de cuadros.
4. Se genera `Media` proxy separado, `ProxyMedia` de video y `AudioProxies`.
5. Se corrigieron las `RelativePath` para originales y proxies contra la
   carpeta final del `.prproj`.

La suite automatizada verifica la estructura XML, pero no demuestra que
Premiere 26.3 acepte toda la serialización privada. Esa es la brecha actual.

## Riesgos y puntos a investigar antes de cambiar más XML

### 1. Comparar el cierre completo, no sólo los tags visibles

La plantilla `TemplateProxyAdjunto.prproj` se redujo a medios, streams,
fuentes y `AudioProxy`. La comparación original de Premiere indica que al
adjuntar proxy también cambia streams del original y serializadores de canales.
Hay que comparar por objeto y referencia `v7` contra:

```text
/Users/brunogutierrez/Downloads/antes1.prproj
/Users/brunogutierrez/Downloads/despues.prproj
```

No agregar objetos por intuición. Identificar exactamente cuáles existen en
`despues` y faltan o difieren en el clip equivalente de Clipify.

### 2. `FileKey`, estados y datos conformados

Los `Media` proxy clonados conservan metadatos de plantilla sanitizados. Si
Premiere rechaza el vínculo incluso con la `RelativePath` correcta, comparar
`FileKey`, `ModificationState`, `ContentAndMetadataState`, `DataStream`,
`AudioStream`, `VideoStream` y rutas `.pek` con el proyecto que Premiere
guardó. Determinar con evidencia qué campos deben ser únicos, regenerados o
eliminados.

### 3. Confirmar el proyecto exacto y el interruptor

Después de generar un proyecto posterior a `8f6eb48`, registrar:

- SHA de `git rev-parse --short HEAD`;
- ruta exacta y fecha del `.prproj` generado;
- rutas `FilePath`, `ActualMediaFilePath` y `RelativePath` de un proxy;
- resultado de abrirlo en Premiere y alternar proxies.

No confiar en el nombre v6/v7 solamente: Clipify evita sobrescribir y puede
crear versiones nuevas en otra carpeta.

## Reproducción mínima requerida

1. Ejecutar la fuente, no la app empaquetada:

   ```bash
   cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
   git rev-parse --short HEAD
   .venv/bin/clasificador
   ```

2. Cargar dos originales Sony con sus `S03` existentes y un clip sin proxy.
3. Confirmar que Clipify muestra el badge `PROXY` en los dos primeros; si no,
   el problema es anterior al exportador porque `Clip.ruta_proxy` está vacía.
4. Generar un `.prproj` con ruta y nombre nuevos.
5. Inspeccionar su XML antes de abrir Premiere:

   - dos `Media/IsProxy=true`;
   - dos `ProxyMedia`;
   - `RelativePath` relativa a la carpeta del proyecto, nunca `../Users/...`;
   - dos `ClipProjectItem` visibles, no cuatro;
   - nombres visibles con el formato nuevo.

6. Abrir en Premiere 26.3 y activar/desactivar proxies. Si Premiere sigue sin
   reconocerlos, guardar una copia sin modificar y comparar su cierre XML con
   `despues.prproj` antes de implementar el siguiente cambio.

## Comandos de verificación

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

## Regla de trabajo

No afirmar que los proxies están listos sólo porque existen `ProxyMedia` en el
XML. La aceptación es que Premiere muestre un solo clip por original y que su
interruptor de proxies cambie la reproducción sin sustituir el original para
edición o exportación.
