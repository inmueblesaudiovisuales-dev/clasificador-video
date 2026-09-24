# Proxies reales en el `.prproj`, marca visible y nombres de clips

Fecha: 2026-09-24. Diseño aprobado por Bruno.

## Objetivo

Cuando Clipify genere el `.prproj`, cada clip que tenga `ruta_proxy` debe
llegar a Premiere como un solo clip cuyo medio principal es el original y
que tiene su proxy conectado. El proxy no aparece como otro item dentro de
los bins ni sustituye el original para editar o exportar.

En la misma entrega, Clipify generará proxies con el sufijo `_proxy`, les
pondrá una marca discreta sobre la imagen y usará el formato de nombre de
clip acordado para Premiere.

## Evidencia de Premiere

Bruno creó y guardó estos dos proyectos de control:

- antes: `/Users/brunogutierrez/Downloads/antes1.prproj`
- después: `/Users/brunogutierrez/Downloads/despues.prproj`
- original: `/Users/brunogutierrez/archivos temporales IAV/IAV-2609.23-A/01. ASSETS VIDEO/01. VIDEOS SONY/20260910_PIB0001.MP4`
- proxy: `/Users/brunogutierrez/Library/Mobile Documents/com~apple~CloudDocs/01. Proyectos 2026 IAV y PI/01. IAV/2026/09. Septiembre/IAV-2609.23-A/03. Proxies/01. VIDEOS SONY/20260910_PIB0001S03.mp4`

Al usar **Adjuntar proxies**, Premiere no sólo añade una ruta. En el proyecto
posterior crea un `Media` exclusivo para el proxy, marcado con
`IsProxy=true`, y objetos `AudioProxy`. Después enlaza el `Media` nuevo en:

- `VideoMediaSource/MediaSource/Content/ProxyMedia`;
- `AudioMediaSource/MediaSource/Content/AudioProxies`.

También reemplaza los streams del `Media` original por streams nuevos y
reconstruye sus serializadores de canales de audio. Esta es la estructura a
replicar; escribir únicamente `ruta_proxy` en un `Media` del original no
equivale a adjuntar un proxy.

## Datos y flujo del `.prproj`

`prproj_generador` seguirá clonando el medio del original para cada
`Clip.ruta`. Si `Clip.ruta_proxy` existe y es un archivo válido, clonará o
creará el cierre de objetos que Premiere produjo en la comparación:

1. medio, streams y metadatos del proxy;
2. enlace de proxy en la fuente de video del original;
3. enlaces de proxy y canales en la fuente de audio cuando aplique;
4. streams del original que corresponden al estado con proxy adjunto.

Cada referencia, ruta principal, ruta efectiva y ruta relativa que pertenezca
al medio nuevo se escribirá desde la ruta actual. Al clonar el original,
todas sus rutas relativas también se actualizarán: el proyecto de Bruno
mostró que dejar una segunda `RelativePath` vieja de la plantilla puede
conservar el nombre de otra toma y volver frágil una reconexión futura.

Un clip sin `ruta_proxy`, con proxy inexistente o no verificable conserva la
estructura actual de sólo original. No se inventa un enlace ni se agrega un
item adicional al bin.

## Nombre de archivo de proxy y compatibilidad

Los proxies creados por Clipify pasarán de `NOMBRES03.mp4` a
`NOMBRE_proxy.mp4`.

La búsqueda conservará compatibilidad con proxies existentes de Sony que
terminan en `S03`; no se renombran ni se mueven archivos ya creados. El
reconocimiento de `_proxy` seguirá sin distinguir mayúsculas y minúsculas,
para que esos archivos nunca entren como originales durante el ingest.

## Marca visible sobre el proxy

La marca se dibuja durante la codificación del proxy, no como un cambio de
metadatos ni como un segundo video. Será pequeña, semitransparente y estará
en la esquina inferior derecha.

La composición debe preservar la geometría, la orientación, el fps, la
duración y el número de cuadros del original. Por eso el filtro visual se
aplica sin escala, recorte, rotación ni cambio de velocidad, y se verificará
contra un video horizontal y uno vertical antes de considerar lista la
entrega.

## Nombres visibles de clips en Premiere

Los clips conservan su numeración consecutiva por cuarto, en el orden del
material y sin reiniciarse por cámara. Las marcas de estado se mantienen,
pero se mueven después del número para no alterar el orden cronológico al
ordenar por nombre.

Formato:

```
CUARTO-01 [CAMARA]
CUARTO-02 ✓ [CAMARA]
CUARTO-03 ✕ [CAMARA]
CUARTO-04 ★ [CAMARA]
```

El cuarto se convierte a mayúsculas; el número tiene al menos dos dígitos.
Los nombres de los archivos en disco no cambian.

## Verificación y responsabilidades

Las pruebas automáticas cubrirán la estructura XML, rutas completas y
relativas, compatibilidad de sufijos, nombres y el comando de codificación.
La comprobación de apertura y vínculo dentro de Premiere la hará Bruno:

1. abrirá un `.prproj` generado por Clipify;
2. confirmará que hay un solo clip por original;
3. activará y desactivará proxies y comprobará que cambia la reproducción,
   no el medio principal;
4. revisará un proxy horizontal y uno vertical para confirmar que la marca
   no afecta encuadre, duración, fps ni orientación.

No se abrirán proyectos de Premiere desde el trabajo automatizado.

## Fuera de alcance

- Renombrar proxies u originales ya existentes en disco.
- Actualizar un `.prproj` que ya fue generado y editado.
- Cambiar las insignias que Clipify ya muestra dentro de su propia interfaz.
