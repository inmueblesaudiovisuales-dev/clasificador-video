# Generar el `.prproj` directo desde Clipify, sin el plugin (fase 1)

Fecha: 2026-09-23. Brainstorm con Bruno, a partir de
`docs/superpowers/RESULTADO-2026-09-23-generacion-directa-prproj.md`.

## Contexto y motivación

El spike del 2026-09-23 comprobó que Premiere abre un `.prproj` escrito
desde afuera, con bins, clips, colores, nombres, secuencia y Lumetri ya
adentro. Bruno quiere que Clipify deje de depender del plugin UXP para
armar el proyecto de Premiere y en vez de eso escriba el `.prproj` ya
completo, además de resolver un problema aparte que el spike dejó abierto:
el LUT de cada cámara está guardado con una ruta absoluta de la Mac de
Bruno, así que el proyecto no abre igual en otra computadora.

## Qué NO cambia en esta fase

- El plugin UXP (`uxp-plugin/`) no se borra ni se desconecta. Se queda como
  respaldo, movido a un lugar secundario de la interfaz, hasta que la
  generación directa se use en varios proyectos reales sin problema.
- Toda la lógica que hoy decide QUÉ va en el manifest -- nombre de bin por
  cuarto/unidad, marca de estado en el nombre del clip (✓/✕/★), color por
  cámara, in/out, qué secuencia corresponde -- no cambia. Sigue viviendo en
  `manifest.py`, `probe.py` y los módulos de marca. Lo único que cambia es
  a dónde va a parar ese dato: al XML del `.prproj` directamente, no al
  `manifest.json` que hoy lee el plugin.
- Volver a generar sobre un proyecto que Bruno ya abrió y editó en Premiere
  NO es un caso a resolver aquí (ver "Una sola vez" abajo). Si llega
  material nuevo después de generar, se importa a mano en Premiere como
  cualquier medio nuevo.
- La copia de `TemplateAE.aep` en `proyecto_colaborativo.py` sigue exacto
  como está.

## Una sola vez, no reintentable

Confirmado con Bruno: a diferencia del plugin (que puede correr varias
veces sobre un proyecto ya abierto y solo agrega lo nuevo), la generación
directa es de un solo uso. Bruno la corre una vez al tener clasificado el
material del arranque del rodaje, abre el `.prproj` en Premiere, y de ahí
en adelante edita ahí directo. Esto simplifica mucho el diseño: no hace
falta lógica de "actualizar sin pisar lo que ya existe", dedupe de bins ya
creados, ni detectar qué se movió -- eso es exactamente lo que hace
complicado a `estructura.js`/`importClip.js` del lado del plugin, y no hace
falta replicarlo.

## Dónde se dispara

Hoy hay dos momentos separados donde Clipify toca un `.prproj`:

1. `proyecto_colaborativo.crear_carpeta_de_proyecto` -- copia
   `TemplatePremiere.prproj` en blanco al crear la carpeta del proyecto,
   antes de que exista un solo clip clasificado.
2. `MainWindow._on_export_manifest` (`Ctrl+E`) -- escribe `manifest.json`
   con los clips ya clasificados, para que el plugin lo importe en
   Premiere.

Quedan unificados en uno solo:

- `crear_carpeta_de_proyecto` **deja de copiar** `TemplatePremiere.prproj`.
  El `.prproj` no existe todavía cuando se crea la carpeta del proyecto.
- `Ctrl+E` pasa a ser la generación directa del `.prproj` completo, en vez
  de escribir `manifest.json`. Es la acción principal de ahí en adelante.
- El export de `manifest.json` para el plugin se mueve a un lugar
  secundario de la interfaz (un ítem de menú, no el atajo principal), como
  respaldo.

### Si el `.prproj` ya existe

Puede pasar si Bruno le da a generar dos veces, o si ya lleva horas
editando en Premiere sobre el archivo que se generó antes. Clipify **no
sobreescribe en silencio**: muestra un aviso con la opción de reemplazarlo
ahí mismo. Si Bruno no confirma, no se toca el archivo existente.

## Piezas nuevas

### Plantilla con los LUT ya aplicados

`testcolorlut.prproj` (que Bruno ya armó y Premiere ya guardó, con el LUT
de Sony aplicado a un clip y el de DJI a otro -- confirmado leyendo su XML:
ambas rutas completas de los `.cube` viajan dentro de sendos bloques
`ArbVideoComponentParam` bajo `AE.ADBE Lumetri`) se copia al repo como
recurso versionado de Clipify, con el nombre `TemplateColorLuts.prproj`.

**Corrección sobre el borrador hablado con Bruno:** `TemplatePremiere.prproj`
NO vive en el repo -- es un archivo propio de Bruno, guardado en su carpeta
de iCloud (`03. Templates`, junto a `TemplateAE.aep`), leído por
`proyecto_colaborativo.py` con una ruta que el propio Bruno configura. La
plantilla nueva con los LUT es un caso distinto: como los `.cube`, tiene que
venir empacada DENTRO de Clipify para no depender de una carpeta externa.
Vive en `recursos/premiere/` (carpeta nueva en la raíz del repo, mismo
nivel que `docs/`, `empaque/`, `uxp-plugin/`), siguiendo el patrón ya usado
por `patron.py`/`docs/patron-de-recorrido/MI-PATRON.md`: una ruta relativa
que se busca en `sys._MEIPASS` cuando la app está empacada, o relativa al
repo cuando corre desde el código.

De esa plantilla, el generador clona el `VideoComponentChain` completo del
clip que tiene el LUT de Sony, o el del clip que tiene el LUT de DJI, según
la cámara del clip que se está armando -- igual que probó el experimento 5
del spike (aplicar el mismo bloque ya validado a más de un master clip). No
se inventa ni se arma a mano ningún parámetro de Lumetri.

### Los `.cube` como recurso de Clipify

Los dos archivos:

```
/Users/brunogutierrez/Library/Application Support/Adobe/Common/LUTs/Technical/SONY-SLOG3.cube
/Users/brunogutierrez/Library/Application Support/Adobe/Common/LUTs/Technical/DJI-DLOGM.cube
```

se copian una sola vez, ahora, como parte de este trabajo, a
`recursos/premiere/` dentro del repo (mismo lugar que
`TemplateColorLuts.prproj`, ver arriba): de ahí en adelante Clipify no
vuelve a leer la carpeta personal de Adobe de esta Mac.

### Mapa cámara → LUT

Reusa el mismo bucket que ya existe en `camaras.py` (`sony` / `dji` /
`otra`) y que ya decide el color de Premiere en `theme.CAMARA_COLORES`.
Confirmado con Bruno: el material de la Pocket ya cae en el bucket `dji`
hoy (su nombre de archivo sigue el mismo patrón que el dron), así que no
hace falta un bucket nuevo.

```
sony  -> SONY-SLOG3.cube
dji   -> DJI-DLOGM.cube   (incluye Pocket, mismo patrón de nombre)
otra  -> sin LUT
```

Un clip en el bucket `otra` no lleva Lumetri en el `.prproj` generado --
mismo criterio que hoy: `otra` es la válvula para lo que no es ninguna de
las dos cámaras reconocidas, y no hay LUT que le corresponda a ciegas.

### Carpeta de LUTs por proyecto

Al generar, Clipify crea `01. Proyecto premiere/LUTs/` dentro de la carpeta
del proyecto (confirmado con Bruno: adentro de la carpeta de Premiere, no
como una subcarpeta hermana nueva) y copia ahí **solo** los `.cube` de las
cámaras que de verdad aparecen en el material que se está exportando -- si
no hay clips del dron, no se copia `DJI-DLOGM.cube`.

El `.prproj` generado escribe la ruta del LUT apuntando a esa carpeta
DENTRO del proyecto (`.../01. Proyecto premiere/LUTs/SONY-SLOG3.cube`), no
a la carpeta personal de Adobe de esta Mac. Esto es lo que resuelve el
problema original que motivó el pedido: abrir el proyecto en otra
computadora ya no depende de que esa Mac tenga los `.cube` instalados en
el mismo lugar.

### El generador

Módulo nuevo, sin Qt (mismo criterio que `manifest.py`/`buscar_prproj.py`):
recibe el `Manifest` que Clipify ya arma hoy (los mismos datos que hoy
viajan en `manifest.json`) más las rutas de la plantilla y los `.cube`
copiados, y escribe el `.prproj` final:

1. descomprime la plantilla `TemplateColorLuts.prproj`;
2. arma el árbol de bins de `estructura.js` (las 7 carpetas fijas, y dentro
   de "02. Clip" un bin por cuarto/unidad, numerado igual que hoy decide
   `caminoDelClip`);
3. por cada clip del manifest: clona la cadena completa
   `ClipProjectItem` → `MasterClip` → `VideoClip`/`AudioClip` →
   `VideoMediaSource`/`AudioMediaSource` → `Media` con IDs nuevos,
   apuntando a `clip.ruta`; le pone el nombre con su marca de estado y el
   label de color de su cámara (mismo mapeo que ya usa `theme.py`); si
   tiene in/out, los escribe en el `MasterClip`;
4. conecta el `VideoComponentChain` del LUT que toque, clonado de la
   plantilla, para clips `sony`/`dji`; los `otra` se quedan sin Lumetri;
5. crea la secuencia vacía que corresponda según `formato_secuencia`
   (misma lógica que ya decide `probe.py`/el diálogo de Bruno), dentro de
   "01. Secuencia";
6. comprime el XML resultante como gzip con extensión `.prproj`.

Se prueba con pruebas de Python normales (que arma bien la estructura, que
elige el LUT correcto, que un clip `otra` no lleva Lumetri, que un clip sin
cámara reconocida no revienta) y, aparte de eso, abriendo el archivo real
en Premiere -- las pruebas automáticas no reemplazan esa verificación.

## Riesgos que quedan abiertos, no se cierran con código

- El `.prproj` es un formato privado de Adobe, atado a la versión de
  Premiere (26.3 al momento de este documento). Cualquier cambio de
  Premiere puede requerir una plantilla nueva y volver a probar apertura
  real.
- Falta validar con un shooting real grande: muchos clips, proxies, clips
  sin clasificar, rutas con caracteres especiales, material offline. El
  spike solo probó con dos MP4 de prueba.
- La plantilla `TemplateColorLuts.prproj` es la única fuente de verdad del
  Lumetri. Si algún día cambia el `.cube` de una cámara, hay que rehacer la
  plantilla a mano en Premiere (aplicar el nuevo LUT, guardar) -- no se
  edita el XML del bloque de Lumetri directamente.

## Fuera de alcance de esta fase

- Actualizar un `.prproj` ya generado y editado (fase futura, si algún día
  hace falta).
- Retirar el plugin UXP del repo.
- Cualquier cámara nueva sin LUT conocido -- se agrega cuando exista un
  `.cube` real que probar, no antes.
