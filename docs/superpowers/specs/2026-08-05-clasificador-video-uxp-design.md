# Spec: Clasificador de Video para Bienes Raíces — arquitectura UXP — 2026-08-05

## 1. Qué cambia respecto al spec anterior

Este spec **reemplaza** `2026-08-05-clasificador-video-design.md` (el spec basado en xmeml). Se descubrió durante pruebas reales que Adobe Premiere Pro **nunca lee el archivo de video al importar un xmeml** — arma el clip solo con lo declarado en el XML, y no existe ninguna etiqueta de rotación en ese formato ni en el modelo de interpretación de material de Premiere. Un clip vertical (grabado con rotación de cámara) siempre se ve acostado al importarlo por xmeml, sin solución posible dentro de ese formato (evidencia completa en `docs/superpowers/HALLAZGOS-2026-08-05-rotacion-vertical.md`).

**La salida encontrada y validada con clips reales:** un plugin UXP dentro de Premiere, usando `project.importFiles()` — el mismo camino que usa Premiere cuando arrastras un archivo a mano — sí respeta la rotación. Sobre esa base, se confirmó (con los 3 clips reales de prueba, verticales, en una sola corrida) que la misma vía también permite: bins anidados, in/out directo sobre el clip, y color de etiqueta — las cuatro cosas que este proyecto necesita, a la vez, sin errores.

## 2. Arquitectura: dos piezas que se hablan por un archivo

1. **App externa** (PySide6 + python-mpv + ffmpeg) — donde el usuario clasifica el material. Sin cambios de fondo respecto al handoff original en su interfaz de clasificación.
2. **Plugin UXP** — vive dentro de Premiere, como panel. Recibe instrucciones de la app externa y las ejecuta contra el proyecto de Premiere abierto.

Se comunican por un **manifest JSON** que la app externa escribe donde el usuario quiera. Dentro de Premiere, el usuario presiona un botón en el panel del plugin, elige ese archivo con el explorador de macOS, y el plugin lo procesa de una sola pasada. No hay red, ni servidor, ni puertos, ni nada corriendo en segundo plano.

**El flujo completo, de principio a fin:** el usuario abre la app externa, organiza el material (cuartos, in/out, pick/reject), exporta el manifest → abre Premiere, presiona el botón del plugin, elige el manifest → el proyecto queda armado. Dos pasos manuales, ambos deliberados.

## 3. Ingest en la app externa

- Panel de carpetas dentro de la app, como el panel de Proyecto de Premiere.
- El usuario arrastra archivos de video desde Finder a una carpeta para agregarlos — la app no asume nada sobre cámaras ni tipos de carpeta.
- Clic derecho en una carpeta → **"Buscar proxies"** → el usuario elige la carpeta de proxies para esa carpeta. La app empareja por nombre: un proxy es el mismo stem del original + sufijo `S03` + extensión (ej. `20260804_PIB0587.MP4` ↔ `20260804_PIB0587S03.MP4`, confirmado con archivo real). Los clips sin match (ej. dron) se quedan sin proxy, sin error.

## 4. Sistema de cuartos (sin cambios respecto al spec anterior)

- Lista maestra fija + cuarto custom: Fachada, Sala, Comedor, Cocina, Recámara, Baño, Estudio/Oficina, Alberca, Jardín/Patio, Terraza, Roof garden, Garage/Cochera, Vestíbulo/Hall, Área de servicio, Dron/Aérea, Amenidades comunes, B-roll/Detalles.
- Antes de clasificar, el usuario elige qué cuartos tiene la propiedad. Repetidos se numeran automático (Recámara 1, 2...).
- Subcuartos (Baño, Closet, Terraza, custom) cuelgan de un cuarto — bin anidado en Premiere: `Recámara 2 > Baño`.

## 5. Selección por teclado (sin cambios respecto al spec anterior)

Leyenda inferior con 1-9. Si un cuarto tiene subcuartos, al presionar su tecla la leyenda cambia a mostrar solo sus subcuartos (sin límite de tiempo entre teclas). Resto de atajos igual: `Espacio`, `J K L`, `I`/`O`, `P`/`X`/`U`, flechas, `/` filtro rápido, `Ctrl+Z` multinivel.

## 6. Reproducción y calidad

python-mpv para decodificar HEVC 10-bit con aceleración de hardware. Se agrega un **selector de calidad de reproducción tipo Premiere** (Full, 1/2, 1/4, 1/8...) para que la app sea usable en máquinas menos potentes — reduce la resolución/calidad de decodificación, no afecta el archivo ni la exportación.

## 7. In/out — cambio de mecanismo respecto al spec anterior

**Ya no se generan subclips.** Se confirmó que la API de Premiere permite poner in/out directo sobre el clip maestro (`createSetInOutPointsAction`) — un solo ícono por clip en el bin, ya recortado, en vez de dos (original + subclip). Se marca con `I`/`O` en la app, se guarda como número de frame entero, y el plugin lo traduce a `TickTime` con el fps real del clip.

## 8. Pick / Reject y exportación

Igual que el spec anterior: **todos los clips se exportan, sin excepción.**

- Clasificado → bin de su cuarto (anidado si tiene subcuarto).
- Sin clasificar → bin `Sin clasificar`.
- Pick → color de etiqueta Forest. Reject → color de etiqueta Rose. Ninguno excluye el clip de la exportación, ambos se colorean nada más.
- Aviso antes de exportar (no bloqueante) si hay clips sin clasificar.

## 9. Proxies vinculados

Si un clip tiene proxy emparejado (§3), el manifest lo incluye. El plugin usa `clipProjectItem.attachProxy(rutaProxy, false)` después de importar el original — Premiere alterna nativo entre proxy (edición fluida) y original (calidad final), sin que la app ni el plugin manejen ese swap.

## 10. Autoguardado (sin cambios respecto al spec anterior)

JSON local, reescrito en cada acción de clasificación, con escritura atómica (temporal + rename). Recupera la sesión exacta si la app se cierra a medio shooting.

## 11. El manifest (formato del archivo que conecta las dos piezas)

Un JSON por exportación. La app lo guarda donde el usuario elija (por default, junto al material del shooting) — no hay carpeta fija del sistema.

```json
{
  "proyecto": "Casa Jardin",
  "orientacion": "vertical",
  "clips": [
    {
      "orden": 1,
      "ruta": "/ruta/absoluta/al/clip.MP4",
      "categoria_path": ["Recamara 2", "Bano"],
      "fps": 59.94005994005994,
      "in_frame": 30,
      "out_frame": 200,
      "flag": "pick",
      "ruta_proxy": "/ruta/absoluta/al/proxy.MP4"
    }
  ]
}
```

- `ruta_proxy` es `null` si no hay proxy para ese clip (ej. dron).
- `in_frame`/`out_frame` son `null` si el clip va completo.
- `fps` viene de `ffprobe` en la app externa. **El plugin nunca lo infiere** — con el fps equivocado, las marcas de in/out caen en el frame equivocado.
- `orden` y `orientacion` **no se usan en la v1**. Existen desde ahora para no rehacer el formato cuando llegue el armado automático de la secuencia (§12.1). Los clips vienen en el array en el mismo orden que indica `orden`.

## 12. El plugin UXP

- **Instalación:** carpeta copiada directo a `~/Library/Application Support/Adobe/UXP/Plugins/External/<id>_<major>` — no requiere UXP Developer Tools corriendo después de instalado.
- **Actualización:** cerrar Premiere, **borrar** la carpeta instalada y volver a copiarla — no sobrescribir encima, porque quedan archivos viejos que ya no existen en la versión nueva. Si sube el major de la versión, cambia el nombre de la carpeta y hay que borrar la anterior a mano. El plugin nunca debe estar cargado en UXP Developer Tools y copiado en la carpeta de plugins al mismo tiempo: mismo identificador, dos copias, y Premiere puede tomar la equivocada. El procedimiento exacto vive en `uxp-plugin/README.md`.
- **Antes de empezar, revisa que el material exista.** Caso real: el usuario clasifica con el disco externo conectado y luego abre Premiere sin el disco. Si no encuentra ninguno de los archivos, avisa una sola vez ("revisa que el disco esté conectado") y no importa nada. Si faltan algunos, avisa cuántos e importa el resto.
- **Disparo manual, no vigilancia.** El panel tiene un botón "Importar clasificación" que abre el explorador de macOS. El usuario elige el manifest y el plugin lo procesa completo, de una pasada. Descartado explícitamente el poll cada pocos segundos: el usuario quiere una acción deliberada, no un proceso corriendo en segundo plano dentro de Premiere.
- **El plugin no escribe ni mueve archivos del usuario.** No hay carpetas `pendientes/` ni `procesados/`, ni renombrado de manifests. Solo lee el archivo que se le señala. Reimportar el mismo manifest es seguro (ver dedupe abajo).
- **Por cada clip del manifest:**
  1. Resuelve/crea la cadena de bins anidados (`categoria_path`).
  2. **Busca primero si el clip ya fue importado antes** (por ruta de archivo real, `getMediaFilePath()` — evita duplicar en reexportaciones). Si ya existe: lo mueve al bin correcto y actualiza label/in-out/proxy en vez de reimportar. Si no existe: lo importa dentro del bin final (`project.importFiles`, que preserva la rotación real).
  3. Pone in/out directo sobre el clip (`createSetInOutPointsAction`), si el manifest trae valores.
  4. Pone color de etiqueta si `flag` es `pick` o `reject`.
  5. Adjunta el proxy (`attachProxy`) si `ruta_proxy` no es `null`.
- **Identidad de bins por objeto, nunca por nombre.** El sistema de cuartos produce nombres repetidos en ramas distintas (`Recámara 1 > Baño` y `Recámara 2 > Baño`). Comparar carpetas por su nombre haría que una corrección entre esos dos baños se pierda en silencio. Se compara el objeto de carpeta, no la cadena de texto.
- **Identidad de clips por ruta en disco, nunca por nombre de archivo.** Los nombres se reciclan entre tarjetas de cámara. Después de importar, el clip se localiza por su media path, con reintentos cortos porque Premiere no siempre lo registra al instante.
- **Manejo de errores:** un clip que falla (archivo no encontrado, error de Premiere) no detiene el resto del manifest — se salta y se registra como error, el resto sigue procesándose.
- **Feedback visible:** el panel muestra una lista simple de resultados (procesado / con error, por clip) y un resumen final — no solo log de consola, algo que el usuario vea sin abrir herramientas de desarrollador.

### 12.1 Preparado para el armado automático (fuera de la v1)

La meta a futuro es que la app arme sola el corte inicial: primero los clips de exterior, luego los buenos de cocina, luego los de sala, y así, con sus in/out ya aplicados. Eso **no se construye en la v1**, pero el diseño de hoy no debe estorbarlo:

- El **orden lo decide la app externa**, no el plugin. La app conoce el tipo de propiedad y la plantilla de orden; el plugin solo obedece el campo `orden` del manifest. El plugin nunca contiene reglas de "qué cuarto va primero".
- El plugin se parte en dos responsabilidades separadas desde el inicio: **organizar el proyecto** (bins, importar, in/out, label, proxy) y **construir la secuencia**. La segunda nace vacía en la v1; agregarla después es escribir ese módulo y llamarlo al final, sin tocar la primera.
- El manifest ya carga `orden`, `fps` y `orientacion` — los tres datos que la secuencia futura necesita para nacer con los ajustes correctos.

## 13. Miniaturas del filmstrip y rotación

Las miniaturas se generan con ffmpeg. Como ya se peleó rotación una vez en este proyecto (con Premiere), este punto se prueba explícitamente antes de darlo por bueno: confirmar que ffmpeg respeta la matriz de rotación del archivo al extraer el frame (no asumir que "autorotate" viene activado por default en la versión de ffmpeg instalada).

**Dueño:** esto vive en la app externa, no en el plugin. Le corresponde al plan de la app (todavía sin escribir), y debe ser uno de sus primeros pasos verificables — con los mismos clips verticales de `TEST/`. El plan del plugin lo deja constar explícitamente para que no se pierda entre las dos piezas.

## 14. Ya validado empíricamente en esta sesión (no re-derivar)

Con los 3 clips reales de prueba (verticales, Sony FX30, con audio), en Premiere Pro 2026, en una sola corrida de un script UXP:

- `project.importFiles(rutas, true, binDestino, false)` importa dentro de un bin específico y **preserva la orientación vertical real** del archivo.
- `folderItem.createBinAction(nombre, true)` + `project.lockedAccess(() => project.executeTransaction(...))` crea bins, incluyendo anidados (bin dentro de bin).
- `clipProjectItem.createSetColorLabelAction(premierepro.Constants.ProjectItemColorLabel.X)` pone el color de etiqueta.
- `clipProjectItem.createSetInOutPointsAction(inPoint, outPoint)` (con `TickTime.createWithFrameAndFrameRate`) marca in/out directo sobre el clip, sin crear un ítem nuevo.
- Las cuatro cosas juntas, para 3 clips en una sola corrida, sin conflicto entre sí.

**Proxy — validado en vivo (spike `uxp-test/proxy-spike/`, con `20260804_PIB0587.MP4` y su proxy `...S03.MP4`):**

- `canProxy()` devuelve `true` sobre el clip importado.
- `attachProxy(rutaProxy, false)` devuelve `true`.
- `hasProxy()` pasa de `false` a `true`, y `getProxyPath()` devuelve exactamente la ruta adjuntada — verificación dura, no interpretación de un ícono.
- Readjuntar el mismo proxy una segunda vez devuelve `true` otra vez, sin error: **reexportar una clasificación corregida es seguro.**
- En el mismo spike se validaron dos mecanismos que el plugin usa en todas partes: localizar el clip por `getMediaFilePath()` y reintentar hasta que Premiere registre el item recién importado.

**Detalle de implementación importante:** `executeTransaction` debe ir envuelto en `project.lockedAccess(() => {...})` — sin ese envoltorio falla con "The script object is no longer valid."

## 15. Fuera de alcance / descartado explícitamente

- xmeml/FCP7 XML como mecanismo de entrega — descartado, no lo respalda la rotación.
- Subclips como mecanismo de in/out — se usa in/out directo sobre el clip maestro.
- Escribir metadata (XMP) en los archivos originales — se consideró como alternativa y se descartó a favor de UXP.
- Poblar la secuencia de Premiere — **fuera de la v1, no descartado**. El plugin de la v1 no crea ni toca secuencias, solo bins; pero el diseño queda preparado para agregarlo (§12.1).
- Vigilancia automática de una carpeta de manifests — descartada a favor del botón manual (§12).
- Lógica de "tipo de cámara" en el ingest — el ingest es genérico, por carpetas que el usuario arma a mano.
- Detección automática de cortes de escena, sugerencia de categoría por IA, modo comparación — igual que en el spec original, siguen fuera de alcance.

## 16. Riesgos conocidos

- El plugin requiere Premiere Pro 25.1.0+ (versión mínima de la API usada). No probado en versiones anteriores.
- **Deshacer:** cada operación (crear bin, in/out, label) es una entrada independiente en el historial de Premiere, y `attachProxy` no es reversible en absoluto. Revertir una importación completa a mano no es práctico. **Aceptado como limitación**: el flujo de trabajo no contempla deshacer dentro de Premiere; una corrección se hace en la app externa y se reexporta.
- Distribución a otra máquina/editor requiere copiar la carpeta del plugin a la ruta de plugins de Adobe en esa máquina (no es un instalador de un clic todavía; empaquetar como `.ccx` es la vía si se necesita algo más formal).
