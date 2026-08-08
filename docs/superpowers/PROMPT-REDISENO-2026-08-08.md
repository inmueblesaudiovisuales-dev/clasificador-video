# Prompt para otra IA — mockup de diseño desde cero (sin ver el diseño actual)

Copiá y pegá esto tal cual en una sesión nueva de Claude Code (u otro agente
de código), **sin mostrarle capturas, código, ni ningún archivo del proyecto
real** — todo lo que necesita saber está en este prompt.

---

Quiero que diseñes la interfaz de una app de escritorio, desde cero. No
tenés que preocuparte por cómo se ve hoy — de hecho, prefiero que no la
veas: quiero una propuesta libre de sesgo respecto al diseño actual, basada
solo en lo que la app necesita hacer.

## Qué es la app

Una app de escritorio (nativa, no web — pensala como si fuera a construirse
en un toolkit tipo Qt/PySide) para que un editor de video clasifique
clips de shootings inmobiliarios (recorridos de propiedades grabados con
cámara: cocina, recámara, baño, sala, fachada, alberca, etc.) antes de
editarlos en Adobe Premiere Pro.

El usuario es un editor de video profesional, trabajando rápido, casi
siempre con el teclado (no el mouse), muchas veces con Premiere abierto al
lado. La prioridad número uno es **velocidad**: clasificar un shooting
completo de decenas de clips más rápido que hacerlo a mano dentro de
Premiere.

El flujo termina exportando un archivo que otra pieza de software (un
plugin dentro de Premiere) usa para armar el proyecto de edición solo —
esta app no edita video, solo lo prepara y organiza.

## Qué tiene que poder hacer (features actuales)

1. **Importar material** — arrastrar o elegir carpetas con clips de video
   (archivos HEVC 10-bit de una cámara Sony FX30, algunos horizontales,
   algunos verticales). La app calcula fps, duración y rotación de cada
   clip al importar.
2. **Elegir qué cuartos existen en esta sesión** — antes de clasificar, el
   editor define una lista corta de cuartos activos para este shooting
   (ej. Cocina, Sala, Baño...). Cada cuarto activo se mapea a una tecla
   numérica 1-9 para clasificar sin mouse.
3. **Ver todos los clips importados** — una vista tipo filmstrip/grilla con
   miniatura de cada clip, que muestra su estado (sin clasificar / cuarto
   asignado / pick / reject). Tiene que soportar dos modos: grilla y lista.
   Selección múltiple con etiquetado en lote (aplicar el mismo cuarto o
   flag a varios clips a la vez).
4. **Reproducir el clip actual** — un reproductor de video embebido (no un
   `<video>` de navegador — decodificación real con aceleración de
   hardware, porque son archivos HEVC 10-bit pesados). Selector de calidad
   de reproducción (full res, 1/2, 1/4, 1/8) para que reproducir sea fluido
   incluso en resolución completa del archivo.
5. **Marcar in/out por frame exacto** — el editor recorre el clip y marca
   dónde empieza y termina la parte útil, con precisión de frame (no de
   segundo). Necesita ver claramente dónde está parado (timecode y número
   de frame) y dónde quedaron los marcadores de in/out sobre una línea de
   tiempo. Poder saltar a cualquier punto del clip con el mouse (click o
   arrastre sobre la línea de tiempo), además de con teclado.
6. **Clasificar por cuarto con una tecla** — presionar 1-9 asigna el clip
   actual al cuarto correspondiente y avanza al siguiente clip
   automáticamente. Algunos cuartos tienen "subcuartos" (ej. Baño →
   Baño principal / Baño visitas) — se resuelven con una tecla adicional
   después de la tecla de cuarto.
7. **Marcar pick / reject / neutral** — una tecla marca el clip actual como
   bueno (pick), malo (reject), o vuelve a neutral. Esto es independiente
   de a qué cuarto pertenece.
8. **Navegar entre clips** — adelante/atrás con el teclado, sin usar mouse.
9. **Deshacer** — Ctrl+Z revierte la última acción (clasificación, flag,
   etc.). Errores de un click no deberían costar tiempo real.
10. **Ver el progreso** — cuántos clips están sin clasificar todavía, cuántos
    son pick/reject, por cuarto y en total.
11. **Autoguardado** — el trabajo se guarda solo, sin que el editor tenga
    que acordarse de hacerlo. Indicador sutil de "guardado hace Xs".
12. **Exportar** — un botón que genera el archivo que el plugin de Premiere
    va a consumir. Antes de exportar, avisa (sin bloquear) si hay clips
    todavía sin clasificar.

## Hacia dónde va (contemplalo en el diseño, aunque no esté construido hoy)

- **Layout que funcione igual de bien con clips verticales**, no solo
  horizontales — hoy el diseño asume horizontal y es una limitación real.
- **Que se sienta instantáneo** navegando frame por frame — la latencia al
  moverse cuadro a cuadro marcando in/out es la fricción más grande hoy.
- **Proxies** — poder trabajar con una versión liviana del archivo en vez
  del original pesado de cámara, para que todo lo demás (scrub, reproducción)
  sea más fluido. La UI necesita alguna forma de indicar/elegir esto.
- **Que otros editores puedan usarla**, no solo el usuario original — pensá
  en una app que cualquier editor podría instalar y usar, no una
  herramienta personal con configuración hardcodeada.
- **Que aguante shootings grandes** — cientos de clips, no docenas. La
  forma de navegar/revisar tiene que escalar a ese volumen sin volverse
  incómoda (scroll infinito incómodo, listas que no se pueden filtrar,
  etc. son el tipo de problema a evitar).

## Qué NO es parte de esto

Nada de edición real (efectos, transiciones, corrección de color, mezcla de
audio). Esta app clasifica y prepara — la edición de verdad pasa en
Premiere, después. No diseñes features de edición.

## Qué quiero como entrega

Una **sola dirección de diseño, bien desarrollada** (no varias opciones
para elegir — comprometete con una propuesta fuerte y llevala a fondo).

Entregame un **mockup en HTML** (un archivo HTML autocontenido, con CSS
inline o en el mismo archivo) que muestre cómo se vería la app. No hace
falta que sea funcional/navegable — puede ser una captura estática de la
pantalla principal en uso (con datos de ejemplo realistas: nombres de
cuartos, miniaturas de placeholder, timecodes, etc.), el objetivo es que yo
pueda *ver* el diseño, no que lo pueda clickear.

Junto con el HTML, explicame en texto las decisiones de diseño más
importantes: por qué esa jerarquía visual, por qué esos patrones de
interacción, y cómo ese layout deja espacio para las metas futuras
(vertical, proxies, escala) sin tener que rehacerse.

**Higiene de archivos**: no dejes el HTML (ni nada de lo que generes) suelto
en la raíz del repo. Creá una carpeta propia con un nombre que deje claro de
qué se trata — algo como `mockups/rediseno-<fecha>/` o
`docs/superpowers/mockups/rediseno-<fecha>/` — y poné ahí adentro tanto el
HTML como la explicación en texto. Nada de archivos temporales o de
prueba sueltos fuera de esa carpeta.
