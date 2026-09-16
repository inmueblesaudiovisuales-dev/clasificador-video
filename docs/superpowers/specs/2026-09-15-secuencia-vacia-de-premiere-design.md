# Secuencia vacía de Premiere desde Clipify

**Fecha:** 2026-09-15  
**Estado:** diseño aprobado; implementación escrita, pendiente de validación real en Premiere

## Objetivo

Al exportar una clasificación, Clipify pregunta qué formato de secuencia se
quiere. El JSON lleva esa elección y el plugin crea una secuencia vacía dentro
de `01. Secuencia`. Los clips siguen importándose y ordenándose en sus bins;
nunca se agregan automáticamente al timeline.

## Elección en Clipify

Siempre se ofrecen `4K 9:16`, `2.7K 9:16` y `4K 16:9`.

Clipify propone una orientación con base en la mayoría de los clips:

- mayoría horizontal: sugiere `4K 16:9`;
- mayoría vertical sin originales 2.7K: sugiere `4K 9:16`;
- mayoría vertical con al menos un original 2.7K: no decide entre las dos
  opciones verticales; Bruno escoge una explícitamente.

El empate de orientación favorece vertical, como ya ocurría. Un original
vertical se considera 2.7K cuando su lado largo está entre 2600 y 2999
píxeles; cubre la medida real 2704 × 1520 ya corregida por rotación.

El diálogo de exportación se rediseñó el 2026-09-16 con las tres opciones
agrupadas por orientación y un único botón «Exportar JSON». Cada renglón
muestra dimensiones y fps; una nota explica que Premiere agregará otra
secuencia vacía 1080p. Una sugerencia clara aparece seleccionada y puede
cambiarse; cuando hay material vertical 2.7K ninguna opción queda marcada y
el botón se habilita solo al elegir una. El formato se guarda en el JSON,
no se crea ninguna secuencia hasta importarlo en Premiere.

## Contrato del JSON

Los JSON nuevos agregan `formato_secuencia`, con uno de los tres textos
anteriores. Un JSON viejo no trae ese campo: se importan sus clips como
siempre y no se crea ninguna secuencia. No se deduce el formato desde el campo
viejo `orientacion`.

## Secuencia en Premiere

| Elección | Tamaño | FPS | Nombre |
|---|---:|---:|---|
| `4K 9:16` | 2160 × 3840 | 59.94 | `<proyecto> 9:16` |
| `2.7K 9:16` | 2160 × 3840 | 59.94 | `<proyecto> 9:16` |
| `4K 16:9` | 3840 × 2160 | 59.94 | `<proyecto> 16:9` |

Las dos salidas verticales coinciden deliberadamente. La referencia
`9:16 2.7k` de `/Users/brunogutierrez/Downloads/testsecuencias.xml` declara
2160 × 3840, 59.94 fps, pixel cuadrado y campos progresivos.

Desde la ampliación aprobada el 2026-09-16, cada elección crea además una
segunda secuencia vacía a 59.94 fps: `1080 × 1920` para 9:16 o `1920 × 1080`
para 16:9. Se llama `<proyecto> 9:16 1080p` o `<proyecto> 16:9 1080p`; la
principal conserva su nombre sin resolución. Las dos se mueven al bin
`01. Secuencia` y ninguna recibe clips automáticamente. Un JSON viejo sin
`formato_secuencia` sigue sin crear ninguna secuencia.

La deduplicación se decide por separado para cada nombre. Si el bin ya
contiene una de las secuencias, el plugin no la modifica ni la duplica,
avisa en el panel y todavía intenta crear la otra si falta.

## Versión mínima de Premiere

El plugin sube de 25.1 a **26.2**. La API moderna de secuencias existe desde
25.6, pero `SequenceSettings.setVideoFrameRate`, necesario para garantizar
59.94 fps, apareció hasta 26.2. Permitir una versión anterior dejaría instalar
una función que no puede cumplir sus ajustes exactos.

## Verificación acordada

- Las pruebas puras fijan la sugerencia, el nuevo campo y los tres ajustes.
- La suite completa no se repite sin cambios que lo justifiquen.
- La aceptación final requiere comprobar en Premiere: bin correcto, timeline
  vacío, tamaño, fps y segundo import sin duplicar ni modificar.
- No se afirma que funciona en Premiere hasta completar esa prueba real.
