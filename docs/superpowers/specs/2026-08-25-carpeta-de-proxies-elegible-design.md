# La carpeta de proxies la eliges tú

*(Spec del 2026-08-25. Nace de un pedido de Bruno: «quiero que los proxies sí
estén en una sola carpeta pero que estén en subcarpetas», y de lo que se
encontró al mirar su proyecto real.)*

## El problema, con evidencia

Así estaba `IAV-2608.17-A` el día que se escribió esto:

```
01. ASSETS VIDEO/
  01. VIDEOS SONY/
  02. VIDEO DRONE/
  03. VIDEOS OSMO POCKET/
  07. PROXIES/
    01. PROXY SONY     ← 130 archivos, puestos a mano por Bruno
    02. PROXY DRONE    ← VACÍA
  Proxies/             ← 75 proxies del dron, puestos por la app
```

Bruno ya tenía la carpeta del dron esperando, vacía. La app generó los 75
proxies y los tiró en una carpeta suya, sin número, al lado de la de él.

**El problema no es dónde van los proxies. Es que la app no sabe que Bruno
tiene un orden y lo pisa.** Es la misma forma de los ocho bugs del uso real:
dos partes con el mismo dato y sin hablarse — aquí, dos convenciones de
carpetas conviviendo en el mismo disco.

Y hay un segundo problema, más callado: **hoy todos los proxies caen
revueltos en un solo montón.** El día que dos cámaras generen un archivo con
el mismo nombre, uno pisa al otro sin avisar. Es exactamente el modo de falla
de los proxies desenganchados, que ya costó una versión entregada rota.

## Lo que se construye

### 1. Una carpeta por proyecto, con una subcarpeta por bin

Los proxies nuevos van a:

```
<carpeta elegida>/<nombre del bin>/<clip>S03.mp4
```

Por defecto, la carpeta elegida es `<padre de los bins>/Proxies`. Si los
bins no comparten padre --material de dos discos en el mismo proyecto-- se
usa el del primer bin: la carpeta es UNA por proyecto, no una por bin, y
de todos modos se enseña antes de escribir. En el proyecto de arriba eso
da:

```
01. ASSETS VIDEO/Proxies/02. VIDEO DRONE/DJI_...S03.mp4
```

**La subcarpeta se llama igual que la carpeta de material** — `02. VIDEO
DRONE`, no `02. PROXY DRONE`. Se ve repetido y es a propósito: así no hay que
adivinar cuál va con cuál. Un nombre que se parece pero no es igual es un
nombre que se puede leer mal.

Con subcarpetas, dos cámaras no pueden pisarse aunque nombren igual sus
archivos.

### 2. La app pregunta una vez, y llega ya contestada

**Cuándo:** la primera vez que se generan proxies en ese proyecto, dentro del
mismo diálogo que ya dice cuántos va a hacer. No al abrir el proyecto — ahí
todavía no sabes ni qué material tienes, y la pregunta es ruido antes de que
importe.

**Cómo:** con la respuesta puesta, no con un explorador en blanco.

> Los proxies van a `01. ASSETS VIDEO/07. PROXIES`
> [Está bien] [Escoger otra]

La app propone así:

- si junto al material hay **exactamente una** carpeta cuyo nombre contiene
  «prox» (sin importar mayúsculas ni el número de adelante), propone esa;
- si hay varias o ninguna, propone `<padre de los bins>/Proxies`.

**Siempre enseña la ruta antes de escribir nada.** Esto no se negocia:
proponer una carpeta está bien, adivinarla en silencio no. Si adivina mal y lo
ves, lo corriges en un clic; si adivina mal callada, te enteras tres semanas
después con los proxies enganchados al material equivocado.

Después de contestar, no vuelve a preguntar en ese proyecto.

### 3. Se puede cambiar después

Va en el menú. Escoger mal no puede quedar amarrado para siempre.

Cambiarla **no mueve nada**: los proxies que ya existen se siguen encontrando
donde están (§4). Solo cambia dónde se escriben los nuevos.

### 4. Los proyectos de antes no se enteran

Al buscar el proxy de un clip se mira, **en este orden**:

1. la carpeta elegida, en la subcarpeta del bin — donde van los nuevos;
2. **adentro** de la carpeta del material — donde iban desde la 1.10;
3. **al lado**, sueltos — donde iban antes de la 1.10.

Un proyecto viejo abre igual, sin regenerar nada y **sin mover un solo
archivo**. Decisión explícita de Bruno el 2026-08-25: «no quiero que muevas
nada para proyectos existentes».

En su proyecto real eso significa que `Proxies/` se queda con sus 75 archivos
sueltos y, si escoge esa misma carpeta, las subcarpetas nuevas aparecen al
lado de ellos. No es lo más bonito, pero es lo que no le toca los archivos.

### 5. Si no se puede escribir ahí

Se cae hacia atrás con la regla que ya existe: adentro del material si se
puede, al lado si no. Quedarse sin proxies porque la carpeta elegida está en
un disco desconectado sería peor que ponerlos donde funcionaban ayer.

## Lo que esto abre, gratis

Como la carpeta se escoge libre, nada obliga a dejarla dentro del proyecto. Si
algún día Bruno quiere los proxies en un SSD rápido y el material en el disco
lento, ya se puede.

**Con un límite que hay que decir**: si apunta **dos proyectos distintos a la
misma carpeta externa** y los dos tienen un bin con el mismo nombre, los
proxies se mezclan. Con material Sony es un riesgo real — dos tarjetas pueden
traer un `PIB0001` cada una. Por eso el default se queda **dentro del
proyecto**, donde el problema no existe.

## Lo que NO se hace

- **No se mueve ningún archivo**, ni al cambiar la carpeta ni al abrir un
  proyecto viejo.
- **No se regenera nada** que ya exista.
- **No se pregunta al abrir el proyecto.**
- **No se adivina la carpeta en silencio**: siempre se enseña antes.

## Dónde vive

- `proxy_gen.py` — las funciones de carpeta pasan a recibir la elegida.
  `carpeta_de_proxies`, `carpeta_al_lado` y `carpetas_de_proxies` se quedan
  para los caminos 2 y 3 de §4.
- El dato elegido se guarda en el `.cvproj`, junto a `agrupar_por_cuarto` y
  `modo_horizontal`, que ya son preferencias por proyecto de la misma
  naturaleza. Ausente = comportamiento de hoy.
- El diálogo, en `main_window.py`, en el camino que ya arma el resumen de la
  fila de proxies.

## Qué se prueba

1. Los proxies nuevos van a `<elegida>/<bin>/`.
2. Dos bins con un archivo del mismo nombre no se pisan.
3. Un proxy de la 1.10 (adentro) se sigue encontrando.
4. Un proxy de antes de la 1.10 (al lado, suelto) se sigue encontrando.
5. La propuesta acierta cuando hay una sola carpeta con «prox» al lado.
6. La propuesta cae al default cuando hay varias o ninguna.
7. Cambiar la carpeta no mueve ni borra ningún archivo.
8. Sin carpeta elegida, un proyecto viejo se comporta igual que hoy.
9. Si la carpeta elegida no se puede escribir, se cae a adentro y luego al
   lado.
10. La pregunta sale **una sola vez** por proyecto.

## Decisiones que faltan confirmar

- **El nombre de la subcarpeta.** El spec dice «igual que la carpeta de
  material». Bruno las tiene nombradas `02. PROXY DRONE` a mano; esto las
  haría `02. VIDEO DRONE`. Hay que confirmar que le parece bien antes de
  construir.
