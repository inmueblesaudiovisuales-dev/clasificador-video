# La app se llama Clipify y por fin tiene cara

**Fecha:** 2026-08-27
**Estado:** aprobado por Bruno, listo para construir

## El problema

Dos cosas que se veían mal y una que no se veía:

1. **La marca de la barra de título era un triángulo de play en un cuadro
   ámbar.** Funciona, pero es el icono que tiene medio mundo: no distingue
   esta app de un reproductor cualquiera.
2. **La app empacada no tenía icono.** En el Finder y en el Dock salía el
   icono genérico que PyInstaller pone cuando la receta no declara ninguno.
   O sea: el primer pixel que ve Bruno de su propia app era el de otro
   programa.
3. **Se llamaba «Clasificador de Video»**, que describe una tarea. Las
   tareas no se recuerdan; las marcas sí.

## Lo que se decidió

### El nombre: **Clipify**

Se evaluaron cuatro rondas de nombres —descriptivos en español (*Recorrido*,
*Llaves*, *Primera Pasada*), de marca en español (*Visto*, *Palomea*, *Buen
Ojo*), y de producto en inglés (*Sift*, *Keeper*, *Rush*, *Kino*, *Flick*,
*Sweep*, *Scout*)— antes de que Bruno eligiera **Clipify**.

La razón que ganó: **cualquiera entiende qué hace sin que se lo expliquen.**
Es la única del lote que no necesita una frase de apoyo. El costo conocido y
aceptado es que el sufijo `-ify` se puso de moda con Spotify y hoy suena a
2015; se pesó y se decidió que la claridad vale más que la moda.

### El logo: cuadro de video con palomita

Un cuadro ámbar redondeado, y adentro —en negro— el contorno de un cuadro de
video con una palomita encima.

Se eligió entre cuatro propuestas, todas dibujadas y vistas a tamaño real
antes de decidir:

- **La pila de tomas** — tres tomas encimadas.
- **El techo y el play** — un techo de casa sobre un play, el único que
  hablaba de inmuebles.
- **La planta** — un plano de cuartos con el cuarto actual encendido.
- **El cuadro aprobado** — el elegido.

Ganó por dos motivos: es la que mejor aguanta los 17 px de la barra de
título —a ese tamaño la pila se vuelve una mancha y el techo se lee como una
flecha— y es la que **dice lo mismo que el nombre**. Nombre e icono que
cuentan la misma historia se pegan; los que cuentan dos, se olvidan.

### La marca se sigue **pintando**, no se carga de un archivo

Igual que hoy (`_marca_de_play`), el glifo de la barra de título se dibuja
con `QPainter`. No es inercia: un PNG a 17 px se ve suave en un lado y
dentado en otro según el `devicePixelRatio` de la pantalla, y este es el
primer pixel que se ve al abrir la app. El `.icns` del Finder sí es un
archivo, porque macOS no acepta otra cosa — pero se genera **del mismo
código que pinta la barra**, para que no puedan divergir.

### La palabra «Clipify» NO va en la barra de título

Ahí el ancho vale más para el nombre del proyecto y el conteo de clips. El
nombre de la app ya lo dice el icono; repetirlo es ruido. La palabra vive en
la pantalla de inicio (junto a la versión) y en el Finder.

### Lo que NO se toca, a propósito

- **`~/.clasificador_video/`**, donde viven la sesión y la lista de
  proyectos recientes. Renombrarla haría que Bruno abriera la app nueva y
  encontrara la lista vacía, sin explicación. El nombre de una carpeta
  escondida no lo ve nadie; perder los recientes sí se ve.
- **El paquete de Python `clasificador_video`** y los nombres internos. No
  se ven, y renombrarlos llenaría el historial de ruido sin que cambie nada
  para quien usa la app.
- **La caché de miniaturas** (`~/.cache/clasificador_video/`), por lo mismo:
  renombrarla tira todas las miniaturas ya generadas y la próxima apertura
  de un proyecto grande volvería a tardar.

## Lo que cambia, en concreto

| Dónde | Antes | Después |
|---|---|---|
| Marca de la barra de título | Triángulo de play | Cuadro con palomita |
| Icono del Finder y el Dock | El genérico de PyInstaller | `Clipify.icns` |
| El `.app` | `Clasificador.app` | `Clipify.app` |
| El instalador | `Clasificador-1.11.dmg` | `Clipify-1.12.dmg` |
| Pantalla de inicio | «Clasificador 1.11» | «Clipify 1.12» |
| Identificador del paquete | `com.brunogutierrez.clasificador` | `com.brunogutierrez.clipify` |
| Plugin en Premiere | «Clasificador de Video» | «Clipify» |
| `README.md`, `docs/` | Clasificador | Clipify |

La versión sube a **1.12**: cambia lo que Bruno ve, y el número tiene que
poder distinguir «la que tenía» de «la nueva».

## Los dos efectos secundarios, conocidos y aceptados

1. **Para macOS, Clipify es una app distinta de Clasificador.** El
   identificador del paquete cambia, así que la vieja no se reemplaza sola:
   se queda en Aplicaciones hasta que se mande a la basura. En esta entrega
   se manda, a mano y a la basura —no se borra en definitivo—, para que se
   pueda recuperar si algo sale mal.
2. **El icono viejo del Dock queda muerto.** Un atajo del Dock apunta a la
   ruta del `.app`, y esa ruta ya no existe. Hay que volver a arrastrar el
   nuevo.

## Cómo se comprueba

- **Pruebas**: la marca sigue produciendo un pixmap del tamaño del widget y
  con el `devicePixelRatio` correcto; la pantalla de inicio dice «Clipify» y
  la versión que declara el paquete; el `.icns` existe y trae todos los
  tamaños que macOS pide.
- **A ojo, que es lo que manda aquí**: capturar la barra de título con la
  marca nueva y **mirar el PNG**, y renderizar el icono a 16, 32, 128, 512 y
  1024 px para confirmar que a 16 px la palomita todavía se lee y no se
  convierte en una mancha. Ningún «se ve bien» sin haber visto el pixel.
