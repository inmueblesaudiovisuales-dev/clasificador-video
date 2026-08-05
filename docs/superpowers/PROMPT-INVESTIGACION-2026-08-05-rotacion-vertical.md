# Prompt para otra IA — investigar cómo corregir video vertical sin secuencia

Copia y pega esto tal cual a la otra IA.

---

Necesito que investigues a fondo (no adivines, no propongas código sin evidencia) un problema muy específico de Adobe Premiere Pro 2026 en macOS, relacionado con video vertical y clips maestros en un bin (sin usar ninguna secuencia).

## Contexto del proyecto

Hay una herramienta (`clasificador_video`, en `/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO`) que genera un archivo **xmeml** (Final Cut Pro 7 XML) para que Premiere lo importe y arme bins de clips maestros organizados por cuarto de una propiedad — sin colocar ningún clip en una línea de tiempo, sin secuencia poblada. Este diseño (bins de clips maestros, secuencia vacía o inexistente) **es una decisión de producto firme, no negociable en esta investigación**: no propongas "simplemente arma una secuencia con los clips" como solución, porque eso ya se descartó a propósito.

Lee estos dos documentos del repo antes de investigar, tienen todo el diagnóstico hecho hasta ahora:
- `docs/superpowers/HANDOFF-2026-08-05-rotacion-vertical-sin-resolver.md`
- `docs/superpowers/HALLAZGOS-2026-08-05-rotacion-vertical.md`

## El problema, resumido

Algunos clips (grabados con Sony FX30) son verticales: el sensor graba "acostado" (3840×2160) y el archivo trae una bandera de rotación (matriz de despliegue, `rotation: 90` en `ffprobe`) que le dice a cualquier reproductor "gírame 90° para verme derecho". Cuando el usuario arrastra el archivo directo a Premiere, se ve derecho (Premiere sí lee esa bandera en un import normal). Pero cuando el archivo llega a Premiere a través de nuestro xmeml generado, la bandera se pierde — el clip se ve acostado.

**Ya se confirmó, leyendo el binario instalado de Premiere Pro 2026**, que:
1. El vocabulario de xmeml que Premiere sabe leer no tiene ninguna etiqueta de rotación a nivel de `<file>` ni `<samplecharacteristics>`.
2. La API de `FootageInterpretation` (el diálogo "Interpretar material") no expone ninguna propiedad de rotación — solo alfa, campo, velocidad, PAR, LUT, pulldown, VR.
3. El importador de XML de Premiere **nunca abre el archivo de video real** para leer sus características — arma el clip maestro solo con lo que el XML declara explícitamente. (Esto se demostró capturando el `.prproj` que Premiere derivó de un XML de prueba antes de que Premiere se cayera por una variante mal formada — el proyecto derivado confirma esto sin ambigüedad.)

**También se confirmó, en la interfaz real (no en el binario), que:**
4. Sí existe una forma de aplicar un efecto directo a un clip maestro en el bin, sin ninguna secuencia: arrastrar el efecto **Transform** sobre el clip (o sobre varios clips seleccionados a la vez, o vía un preset guardado arrastrado sobre la selección) en el panel de Proyecto. Esto SÍ giró la imagen del clip (confirmado por el usuario, con captura de pantalla).
5. **Pero** ese giro solo rota el dibujo dentro del cuadro — el cuadro (frame) del clip maestro se queda con la forma original (3840×2160, horizontal), así que el resultado queda con barras negras a los lados. No hay, aparentemente, ninguna forma en la interfaz de Premiere de cambiar la FORMA del cuadro de un clip maestro (a diferencia de solo rotar el contenido dentro de él) sin meterlo en una secuencia con esa forma.

## La pregunta central que necesito que investigues

**¿Existe alguna forma, dentro de Premiere Pro 2026 (UI, scripting/ExtendScript, UXP, o algún ajuste de importación), de que un clip maestro en un bin tenga un cuadro (frame) realmente vertical — sin barras negras, sin usar ninguna secuencia — para clips cuyo archivo trae la bandera de rotación de cámara?**

Formas concretas de indagar (no te limites a estas, piensa fuera de la caja):

1. **Scripting/ExtendScript/UXP de Premiere**: ¿hay alguna propiedad de un `ProjectItem` o de sus streams que permita fijar el frame size, o aplicar el mismo efecto Transform vía script a un clip maestro, o modificar directamente el `.prproj` (aunque sea un formato binario/propietario) para inyectar la anulación correcta? Si existe una forma de escribir directamente el `.prproj` con Python/otro lenguaje (parseando su estructura), eso también cuenta como solución válida, aunque sea compleja.
2. **El efecto Transform aplicado como "Master Clip Effect"**: cuando Premiere exporta a Final Cut Pro XML un proyecto donde un clip en un bin ya tiene el efecto Transform con Rotation=90 aplicado (sin ninguna secuencia), ¿qué estructura de XML escribe Premiere exactamente? Si tienes acceso a instrucciones para generar y leer ese XML (pídele al usuario que lo genere si hace falta: aplicar Transform+Rotation 90° a un clip en un bin en Premiere, exportar ese proyecto como Final Cut Pro XML, y compartir el archivo), analiza si esa misma estructura, puesta en NUESTRO generador de xmeml, resolvería el problema del cuadro también (no solo el giro de la imagen) — por ejemplo, si el XML que Premiere escribe declara un `<samplecharacteristics>` distinto para el clipitem vs. el file, o algún campo de "Scale to Frame Size" que technically re-defina el frame.
3. **Alternativas de formato de intercambio**: ¿Premiere Pro 2026 soporta importar **FCPXML** (el formato moderno de Final Cut Pro X, distinto del xmeml/FCP7 que usamos) para bins sin secuencia poblada? Si sí, ¿FCPXML sí tiene una forma de declarar rotación/orientación a nivel de asset o de clip maestro que xmeml no tiene? Esto implicaría migrar de formato, sopesa el costo contra el beneficio.
4. **Metadata de contenedor distinta**: ¿hay alguna forma de que el archivo declare su rotación de una manera que el importador de XML de Premiere sí lea (aunque el importador normal de FCP7 XML no lo haga), por ejemplo algún atributo específico de QuickTime/MOV que Premiere trate de forma especial incluso en el flujo de importación de XML?
5. **Frame size "real" vs "declarado"**: en el hallazgo 4 del documento de HALLAZGOS, se determinó que el importador arma el clip SOLO con lo que el XML declara (nunca abre el archivo real). Esto llevaría a pensar que declarar explícitamente `width=2160 height=3840` en el `<file>`/`<samplecharacteristics>` del XML (osea, "mentirle" a Premiere sobre el tamaño real del archivo) debería, en teoría, hacer que el clip maestro tenga un cuadro vertical de una vez — pero esto YA SE PROBÓ (Intento A del handoff) y el resultado fue una imagen horizontal ACOSTADA dentro de un marco vertical (deformada), no un cuadro vertical limpio. Investiga por qué: ¿es porque el importador SÍ decodifica los píxeles reales del video (aunque no lea sus metadatos de tamaño/rotación) y los estira/encaja dentro del frame declarado sin rotarlos? Si es así, ¿existe alguna combinación de `anamorphic`, `pixelaspectratio`, u otro campo del `<samplecharacteristics>` que, junto con el frame volteado, SÍ le diga a Premiere "gira los píxeles 90°, no los estires"? Esto no se probó todavía — sería una combinación de declarar el frame volteado (2160x3840) junto con alguna instrucción adicional de reencuadre.

## Restricciones firmes (no las cruces en tu propuesta)

- No se puede modificar/re-escribir/re-codificar los archivos de video originales (riesgo de corrupción, ya descartado desde el diseño original del producto).
- No se puede crear copias/proxies pesados de los archivos solo para corregir la rotación (el usuario lo rechazó explícitamente por espacio en disco).
- No se puede poblar la secuencia exportada con los clips (decisión de producto firme, ya explicada arriba).
- Cualquier solución debe funcionar para *muchos* clips de golpe (decenas por shooting), no ser un paso manual repetido clip por clip.

## Qué entregar

Un diagnóstico honesto — si después de investigar a fondo concluyes que **de verdad no es posible** un clip maestro con cuadro vertical limpio sin secuencia (con evidencia concreta, no solo "no encontré cómo"), dilo directamente, no inventes una solución falsa. Si encuentras una vía real, aunque sea compleja (scripting, manipular el `.prproj`, cambiar de formato de intercambio, etc.), explica exactamente cómo funcionaría y qué se necesitaría para implementarla.
