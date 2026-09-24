# Resultado — generar proyectos de Premiere directo desde Clipify

**Fecha:** 2026-09-23
**Premiere probado:** Premiere Pro 2026, build 26.3.0x93
**Estado:** el camino es viable; falta convertir el spike en una función de
Clipify y probarlo con un shooting real.

## La pregunta original

Clipify hoy exporta un JSON y el panel UXP de Premiere lo usa para importar
los medios, armar bins, colorear clips, renombrarlos y crear secuencias. Bruno
quería averiguar si Clipify podía crear un `.prproj` directamente para eliminar
esa dependencia del panel, especialmente sin perder la orientación vertical,
bins, colores, nombres y secuencias.

La motivación inicial fue una sospecha de que los clips verticales de la Sony
FX30 se acostaban por el plugin. Esa premisa resultó falsa: el plugin nunca
tuvo ese bug. Premiere lee correctamente la orientación del archivo cuando lo
importa directo. El camino FCP7 XML (`xmeml`) sí la pierde, incluso al volver a
importar XML que Premiere exportó de su propio proyecto.

La pregunta de este spike fue distinta:

> ¿Podemos generar un `.prproj` que Premiere abra y que ya contenga los clips,
> bins, colores, nombres, secuencias y un LUT de Lumetri, sin ejecutar código
> dentro de Premiere?

## Material de prueba

Todo se hizo en un proyecto desechable. No se alteró el repo durante los
spikes; este documento es el primer cambio versionable de la sesión.

Scratchpad usado durante la sesión:

```
/private/tmp/claude-501/-Users-brunogutierrez-Documents-CLAUDE-CODE-ORGANIZADOR-VIDEO/
ecc7eeea-0ac0-412d-9c37-c75b1c422110/scratchpad/rotacion-spike/
```

Medios relevantes:

- `A_original.mp4`: clip vertical real de Sony, tal como sale de cámara.
- `B_rotate_tag.mp4`: otro MP4 real de prueba con su metadata de orientación.
- `C_exiftool_matrix.mp4`: copia para investigar el signo de la matriz de
  rotación; no se usó para generar el proyecto final.

Bruno creó y guardó `testt.prproj` con:

- un bin llamado `BIN`;
- el clip vertical importado directamente;
- colores en bin e items;
- una secuencia vertical creada a partir del clip;
- posteriormente, un ajuste de Lumetri en el clip de origen.

La captura de la sesión confirmó visualmente que el material entra derecho al
importar de forma directa: no hubo corrección manual de orientación.

## Lo que es un `.prproj`

Un `.prproj` de Premiere actual es un solo documento XML comprimido con gzip.
No contiene los videos: guarda rutas a los medios y una red de objetos que los
describe.

Las relaciones importantes encontradas son:

```
Bin
 └─ ClipProjectItem
     └─ MasterClip
         ├─ VideoClip / AudioClip
         │   └─ VideoMediaSource / AudioMediaSource
         │       └─ Media (ruta del MP4)
         └─ VideoComponentChain (efectos, si existen)

Sequence
 └─ otro ClipProjectItem / MasterClip
```

Los objetos se conectan mediante `ObjectID` + `ObjectRef` y `ObjectUID` +
`ObjectURef`. Su posición en el XML no define su relación. Esto permite partir
de una plantilla creada por Premiere, clonar los objetos necesarios, generar
identificadores nuevos y actualizar las referencias.

La orientación del clip de cámara se guarda en su `VideoStream` como:

```xml
<OriginalImageOrientationType>8</OriginalImageOrientationType>
```

Premiere ya interpreta ese valor al abrir el proyecto y al importar el MP4.
No hay que añadir un efecto de rotación ni transformar el video.

## Experimentos y resultados

### 0. Confirmar la orientación por importación directa

Se probaron tres MP4 en Premiere:

- `A_original.mp4` y `B_rotate_tag.mp4` entraron derechos.
- `C_exiftool_matrix.mp4` entró al revés porque el valor escrito tenía el signo
  opuesto.

**Resultado:** Premiere respeta la metadata de orientación del medio. Este no
es un problema del plugin UXP ni requiere una corrección dentro del proyecto.

### 1. Editar datos visibles en una plantilla

Se descomprimió `testt.prproj`, se cambió únicamente el XML y se volvió a
comprimir como gzip. Se conservaron todos los objetos y referencias creados
por Premiere.

Cambios hechos:

- bin: `BIN` → `01. Cocina [SONY]`;
- clip: `A_original.mp4` → `✓ Cocina 01 [SONY]`;
- secuencia: `A_original` → `PRUEBA CLIPIFY 4K 9:16`.

Archivo generado:

```
clipify-prueba-1.prproj
```

**Resultado comprobado por Bruno en Premiere:** abrió perfectamente; se vieron
el bin, nombre de clip, secuencia, colores existentes y clip vertical.

**Qué prueba:** editar la estructura de un proyecto ya creado por Premiere no
lo corrompe necesariamente. Los nombres visibles viven en nodos separados:
el `ProjectItem`, el `MasterClip` y, para una secuencia, su `Sequence`.

### 2. Añadir un segundo clip que apunte a otro MP4

Se clonó la cadena completa que hace falta para un medio de video con audio:

- `ClipProjectItem`;
- `MasterClip`;
- logging, video/audio clips y sus fuentes;
- canales de audio;
- `Media`, `AudioStream` y `VideoStream`.

Cada clon recibió identificadores nuevos. La nueva entrada del bin apuntó a
`B_rotate_tag.mp4` y se llamó `★ Cocina 02 [SONY]`.

Archivo generado:

```
clipify-prueba-2.prproj
```

**Resultado comprobado por Bruno:** abrió bien, los dos clips estaban en el
bin, el segundo no estaba offline y ambos se veían verticales.

**Qué prueba:** el proyecto no necesita que Premiere importe los archivos para
armar la estructura. Clipify puede escribir un segundo medio real desde fuera.

### 3. Elegir el color del segundo clip

La prueba anterior heredaba el color turquesa del clip base; eso demostraba
preservación, no elección. Se cambió el segundo clip a otro label que Premiere
ya había usado en el mismo proyecto:

```xml
<Column.PropertyText.Label>BE.Prefs.LabelColors.5</Column.PropertyText.Label>
<asl.clip.label.name>BE.Prefs.LabelColors.5</asl.clip.label.name>
<asl.clip.label.color>19005</asl.clip.label.color>
```

El primero se quedó con `BE.Prefs.LabelColors.10` y su valor numérico previo.

Archivo generado:

```
clipify-prueba-3-color.prproj
```

**Resultado comprobado por Bruno:** abrió perfectamente y el segundo clip se
vio con un color distinto al primero.

**Qué prueba:** los colores de etiqueta se pueden asignar desde el `.prproj`.
Para el generador final conviene encapsular el mapeo de cámara → label de
Premiere en un solo sitio y escribir tanto el nombre del label como su valor
numérico asociado.

### 4. Detectar Lumetri guardado por Premiere

Bruno abrió `clipify-prueba-3-color.prproj`, agregó Lumetri a un clip de origen
y guardó el mismo archivo. El proyecto pasó de ~14 KB a ~709 KB: Premiere
agregó el filtro, 130 parámetros y el estado completo de Lumetri.

La relación encontrada en el master clip es:

```xml
<VideoComponentChain ObjectRef="53"/>
```

El objeto `VideoComponentChain` contiene un componente con:

```xml
<DisplayName>Lumetri Color</DisplayName>
<MatchName>AE.ADBE Lumetri</MatchName>
```

El LUT elegido quedó registrado dentro del bloque de Lumetri como:

```
/Users/brunogutierrez/Library/Application Support/Adobe/Common/LUTs/Technical/DJI-DLOGM.cube
```

El XML también contiene un `embeddedlut` con hash y filename, pero el valor
guardado es una referencia a ese `.cube`; no se comprobó que el contenido del
LUT viaje de forma autosuficiente dentro del proyecto.

**Qué prueba:** a diferencia del camino por la API UXP, que rechazaba el
parámetro Blob y podía tumbar Premiere, en el XML del proyecto Premiere sí
guarda y abre su propio bloque de Lumetri correctamente.

### 5. Aplicar el Lumetri existente a ambos clips

En vez de fabricar parámetros de Lumetri, se conectó el mismo
`VideoComponentChain` existente al primer master clip. Los dos masters quedaron
referenciando el bloque validado por Premiere.

Archivo generado:

```
clipify-prueba-4-lumetri-en-ambos.prproj
```

**Resultado comprobado por Bruno:** el proyecto abrió bien y ambos clips
tenían el mismo Lumetri/LUT en el monitor de origen.

**Qué prueba:** Clipify puede aplicar un Lumetri ya conocido a todos los clips
al momento de generar el proyecto. Para un mismo LUT, compartir un bloque de
efecto validado es suficiente en Premiere 26.3.

## Conclusiones comprobadas

1. **Generar un `.prproj` directo es viable.** No es una conjetura: Premiere
   abrió cuatro proyectos escritos desde afuera.
2. **Se pueden crear bins, clips, nombres, secuencias y colores** sin panel
   UXP.
3. **Se pueden añadir medios nuevos desde fuera de Premiere**, siempre que se
   creen sus objetos y referencias consistentes.
4. **Los clips verticales conservan su orientación** porque el proyecto apunta
   al MP4 original y Premiere lee su metadata al abrirlo.
5. **Lumetri también es viable por esta vía.** No hay que usar la API que
   rechazó el Blob: se copia una estructura que Premiere ya guardó y validó.

## Límites y riesgos que siguen abiertos

### Formato privado y dependiente de versión

Adobe no documenta `.prproj` como formato de intercambio para escribirlo. La
estructura observada corresponde a Premiere 26.3. Una actualización de
Premiere puede cambiar objetos, versiones, identificadores internos o campos
obligatorios. El generador necesita pruebas de apertura contra la versión que
use Bruno antes de cada actualización relevante.

### No se debe inventar XML de Lumetri

El bloque completo contiene muchos parámetros y datos binarios. El spike solo
demostró que se puede **clonar** un bloque creado por Premiere. No se debe
intentar construir un Blob o escribir un LUT a mano: el intento previo por UXP
ya mostró que esa ruta puede ser rechazada o tumbar Premiere.

### Portabilidad del LUT

El proyecto de prueba apunta a una ruta absoluta de LUT instalada en esta Mac.
Para que otro editor lo abra correctamente, hace falta una decisión explícita:

- copiar los `.cube` que Clipify use junto al proyecto y escribir esa ruta;
- requerir que los LUT estén instalados en una ruta conocida en todas las Macs;
- o permitir exportar sin LUT y aplicarlo manualmente.

No se debe decir que el LUT es “integrado” o portátil hasta comprobar una
apertura en otra computadora sin esa ruta instalada.

### Múltiples LUTs y cámaras

El spike solo aplicó el mismo LUT de prueba a ambos clips. El generador final
necesita un contrato explícito de qué LUT corresponde a Sony, Pocket y dron,
y qué pasa con medios sin cámara reconocida. Esa regla debe vivir en Clipify,
no quedar escondida en el XML.

### Secuencias de producción

La secuencia de prueba nació al arrastrar un clip, por lo que no está vacía.
El generador final necesita conservar la especificación actual de las cinco
secuencias vacías y sus medidas/fps. La estructura de una secuencia ya está
visible en el `.prproj`, pero todavía falta generar ese conjunto completo y
probarlo en Premiere.

### Shoots grandes y rutas de medios

Solo se probaron dos MP4. Falta validar un shooting real con muchos clips,
cámaras distintas, rutas con caracteres especiales, proxies, clips sin
clasificar y medios offline. Cada medio debe recibir identificadores únicos y
una cadena completa de objetos, sin omitir audio, video o metadata necesaria.

## Recomendación de arquitectura

La ruta recomendada no es construir el XML desde cero. Es mantener una o más
**plantillas `.prproj` creadas y guardadas por la versión soportada de
Premiere**, y que Clipify haga lo siguiente al exportar:

1. copiar la plantilla a la carpeta elegida;
2. leer el manifest de la clasificación y los datos reales del medio;
3. crear bins y sus labels;
4. clonar el arquetipo de clip para cada archivo, con UIDs y ObjectIDs nuevos;
5. escribir rutas, nombres, color de cámara, in/out y orientación que
   corresponda;
6. crear las secuencias vacías requeridas;
7. conectar el arquetipo Lumetri apropiado por cámara, cuando el usuario lo
   haya configurado;
8. comprimir el XML como gzip con extensión `.prproj`;
9. comprobar la salida abriendo proyectos de prueba en Premiere real.

Esto sustituye el panel UXP para la creación inicial del proyecto. No implica
que toda futura automatización de Premiere sea imposible sin plugin; solo que
para el flujo actual de preparación de material, el archivo puede salir listo
desde Clipify.

## Siguiente trabajo recomendado

Antes de reemplazar el exportador real, diseñar y aprobar:

1. la regla de LUT por cámara y cómo se transportarán los `.cube`;
2. la plantilla mínima oficial para Premiere 26.3;
3. el formato interno que generará ObjectIDs/ObjectUIDs de manera segura;
4. la creación de las cinco secuencias vacías existentes;
5. una prueba de apertura con un proyecto real antes de ofrecer esta salida en
   Clipify.

El plugin UXP actual sigue funcionando y no debe eliminarse hasta que ese
camino completo produzca y abra un proyecto real con el mismo resultado.

## Validación manual: proxies reales de Premiere

La exportación directa ahora clona el cierre que Premiere 26.3 guarda al usar
**Adjuntar proxies**: un `Media` separado con `IsProxy=true`, `ProxyMedia` de
video y `AudioProxies`. El original permanece como `MediaSource/Media`; el
proxy no recibe un `ClipProjectItem` y por tanto no debe aparecer como clip
extra en el bin.

Para revisarlo en Premiere (sin modificar el proyecto desde Clipify):

1. Genera un proyecto de prueba que incluya un clip horizontal y uno vertical
   con proxy, además de un clip sin proxy, y ábrelo en Premiere 26.3.
2. En `02. Clip`, confirma que aparece exactamente un item por original; los
   dos proxies no deben listarse como clips independientes.
3. Activa y desactiva el botón **Alternar proxies**. La reproducción debe
   cambiar en los dos clips con proxy, pero el panel de propiedades debe seguir
   mostrando el original como medio principal para edición y exportación.
4. Revisa audio multicanal en una toma Sony: cada canal debe seguir sonando al
   alternar, porque el proyecto contiene los `AudioProxy` correspondientes.
5. Revisa un proxy horizontal y uno vertical: el glifo de Clipify debe ser
   pequeño, semitransparente y estar abajo a la derecha, sin cambio de
   resolución, orientación, fps, duración ni cuadros.
6. Comprueba los nombres y orden: `COCINA-01 ✓ [DRONE]`,
   `COCINA-02 [SONY]`, `COCINA-03 ✕ [SONY]` y
   `COCINA-04 ★ [DRONE]`.

Si Premiere muestra un segundo item, pierde audio, cambia el medio principal o
no reconoce el interruptor, guardar una copia del `.prproj` sin modificarla y
compararla contra `Downloads/despues.prproj`; no agregar tags ni rutas por
conjetura.
