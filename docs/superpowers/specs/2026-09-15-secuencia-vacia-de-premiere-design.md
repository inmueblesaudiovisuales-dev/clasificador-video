# Secuencia vacía de Premiere desde Clipify

**Fecha:** 2026-09-15  
**Estado:** ampliado el 2026-09-16; el conjunto de cinco secuencias queda
pendiente de validación real en Premiere

## Objetivo

Al exportar una clasificación, Clipify no pregunta el formato. El JSON nuevo
pide que Premiere cree tres secuencias principales dentro de `01. Secuencia`
y dos más dentro de `01. Secuencia > 1080p`. Los clips siguen importándose y
ordenándose en sus bins; nunca se agregan automáticamente al timeline.

## Exportación en Clipify

El selector y la sugerencia por mayoría se retiraron. Se conserva el diálogo
para elegir dónde guardar el JSON y los avisos de clips sin clasificar o de
guía vieja. La secuencia nunca se crea en Clipify: la crea Premiere al
importar el archivo.

## Contrato del JSON

Los JSON nuevos llevan `crear_secuencias: true` y ya no llevan
`formato_secuencia`. Los JSON anteriores conservan su comportamiento: si
traen `formato_secuencia`, el plugin solo crea el par del formato elegido;
si no traen ninguno de los dos campos, solo importa clips y bins. No se
deduce el formato desde `orientacion`.

## Secuencia en Premiere

| Bin | Nombre | Tamaño | FPS |
|---|---|---:|---:|
| `01. Secuencia` | `<proyecto> 4K 9:16` | 2160 × 3840 | 59.94 |
| `01. Secuencia` | `<proyecto> 2.7K 9:16` | 2160 × 3840 | 59.94 |
| `01. Secuencia` | `<proyecto> 4K 16:9` | 3840 × 2160 | 59.94 |
| `01. Secuencia > 1080p` | `<proyecto> 9:16 1080p` | 1080 × 1920 | 59.94 |
| `01. Secuencia > 1080p` | `<proyecto> 16:9 1080p` | 1920 × 1080 | 59.94 |

Las dos principales verticales coinciden deliberadamente. La referencia
`9:16 2.7k` de `/Users/brunogutierrez/Downloads/testsecuencias.xml` declara
2160 × 3840, 59.94 fps, pixel cuadrado y campos progresivos.

La deduplicación se decide por nombre y bin. Si una secuencia ya existe, el
plugin no la modifica ni crea otra. Las secuencias 1080p de proyectos
anteriores pueden estar directamente en `01. Secuencia`: se reconocen ahí,
se dejan en su lugar, no se duplican en el nuevo subbin y se avisa en el
panel. No hay migración de proyectos anteriores; solo una importación nueva
puede agregar lo que falta.

## Versión mínima de Premiere

El plugin sube de 25.1 a **26.2**. La API moderna de secuencias existe desde
25.6, pero `SequenceSettings.setVideoFrameRate`, necesario para garantizar
59.94 fps, apareció hasta 26.2. Permitir una versión anterior dejaría instalar
una función que no puede cumplir sus ajustes exactos.

## Verificación acordada

- Las pruebas enfocadas fijan el campo nuevo, los cinco nombres y ajustes,
  y la compatibilidad con JSON anteriores.
- La suite completa no se repite sin cambios que lo justifiquen.
- La aceptación final requiere comprobar en Premiere: bin correcto, timeline
  vacío, tamaño, fps y segundo import sin duplicar ni modificar.
- No se afirma que funciona en Premiere hasta completar esa prueba real.
