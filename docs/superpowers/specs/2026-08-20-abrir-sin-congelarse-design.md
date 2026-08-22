# Abrir sin congelarse

*(Spec aprobado por Bruno el 2026-08-20. Nace de que le sale la bolita de
arcoíris cada vez que abre su proyecto.)*

## El problema, medido

Abrir el proyecto de 205 clips **congela la app 34 segundos**. No es el
arranque: la app sola llega a la pantalla de inicio en menos de dos segundos.
Es abrir el proyecto.

La causa, con nombre: `_pintar_miniatura` corre 205 veces seguidas en el hilo
de la interfaz, **165 ms cada una**. Y esos 165 ms son doce `QPixmap` — cada
clip guarda una **tira de 12 fotos** para poder escrubear pasando el mouse
por encima de su tarjeta. Al abrir se cargan las 12 de los 205: **2,460
imágenes decodificadas de golpe**.

Casi todo ese trabajo sobra al abrir. Para ver la hoja hace falta **una** foto
por clip; las otras once solo cuando pasas el mouse por esa tarjeta en
concreto — y en una sesión normal pasas por unas pocas.

Medido sobre el cache real de Bruno:

| | por clip | con 205 clips |
|---|---|---|
| la tira de 12 | 105 ms | **21.6 s** |
| solo la portada | 9.2 ms | **1.9 s** |

## Lo que se construye

### 1. Al abrir se carga solo la portada

La tarjeta recibe las **rutas** de su tira, no las fotos ya cargadas, y
carga **solo la portada**. Las demás se cargan **la primera vez que se
necesitan**, o sea cuando el mouse escrubea esa tarjeta.

- Escrubear sigue igual. Cada foto cuesta ~9 ms la primera vez y queda
  cargada; el gesto entero reparte ese costo en vez de pagarlo por los 205
  clips que nunca vas a tocar.
- La portada sigue siendo el cuadro al 25% del clip, como hoy. No se toca:
  es el mismo punto donde arranca el video al abrirlo.
- Un clip con **una sola** foto —los que no alcanzaron a tener tira— sigue
  por el camino de siempre.

### 2. Una pantalla de carga mientras tanto

Quedan ~2 segundos, y sin nada en pantalla se siguen sintiendo como un
cuelgue. Mientras el proyecto se abre se muestra una ventana chica y sin
bordes con:

- el **nombre del proyecto**, para que se vea que abrió el que elegiste;
- **cuántos clips** trae;
- una barra que avanza conforme se pintan las portadas.

Se va sola cuando la hoja está lista. **No es un diálogo**: no se puede
cerrar ni tiene botones, porque no hay ninguna decisión que tomar.

**Por qué una pantalla y no solo el arreglo:** aunque bajen a dos segundos,
son dos segundos en los que hoy no pasa nada visible. Y con 500 clips
volverían a ser cinco. La pantalla dice «está trabajando, esto es lo que
está haciendo» sin importar cuánto tarde.

### 3. La ventana abre maximizada

Hoy abre en 1100×700 fijos, escritos a mano, sin mirar la pantalla. Pasa a
abrir **maximizada** — ocupando la pantalla y dejando el Dock y la barra de
menú. Con material horizontal eso es bastante más video.

## Lo que NO cambia

- **La tira se sigue extrayendo completa** al importar. Esto cambia cuándo se
  CARGA en memoria, no qué se guarda: el cache es el mismo y sirve igual en
  la siguiente sesión.
- **La portada sigue en el 25%** del clip.
- **El escrubeo al pasar el mouse** sigue existiendo y con las mismas doce
  posiciones.
- La pantalla de inicio con la lista de recientes se queda como está: es
  ligera y ya aparece rápido.

## Cómo se prueba

- Abrir con una tira de 12 carga **una** foto, no doce.
- La portada que se muestra es la del 25%, la misma que antes.
- Escrubear a un cuadro que no estaba cargado lo carga y lo muestra.
- Un cuadro ya cargado no se vuelve a leer del disco.
- Un clip con una sola foto sigue funcionando.
- La pantalla de carga aparece al abrir un proyecto y se va sola.
- La pantalla de carga dice el nombre del proyecto y el número de clips.
- La ventana abre maximizada.
