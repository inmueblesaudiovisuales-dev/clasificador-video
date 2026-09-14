# La RAM y el CPU con la app en reposo (2026-09-13)

Bruno: «la app usa muchísima RAM y CPU incluso cuando no la uso activamente,
solo está en el fondo».

Todo lo que sigue está medido con **su proyecto real** —
`IAV-2609.11-A.cvproj`, 229 clips — abriendo la app de verdad y leyendo la
RSS del proceso con `ps`, no estimado.

## Lo que se encontró

### 1. Las miniaturas se guardaban al tamaño del archivo (el grande)

`ClipCard._frame()` leía cada foto de la tira con `QPixmap(ruta)` — o sea, a
la resolución del archivo — y la dejaba en memoria para siempre, más una
segunda copia ya escalada en `_scaled_cache`.

Las fotos del cache salen de `screenshot-to-file` de mpv, así que miden lo
que mide la fuente: **1280×720 cuando hay proxy y 3840×2160 cuando no**. En
memoria, una de 4K son 33 MB. Se dibujan en una tarjeta de 198 px.

Medido:

| momento | RSS |
|---|---|
| proyecto abierto, antes de las portadas | 394 MB |
| con las 229 portadas puestas | **1 348 MB** |
| después de escrubear 10 tarjetas | 1 761 MB |
| … 20 | 2 132 MB |
| … 30 | 2 552 MB |
| … 40 | **2 972 MB** |

Son **+41 MB por tarjeta escrubeada, que no se devolvían nunca**. Recorrer la
hoja completa con el mouse llega a ~10 GB. Y con material sin proxy la cuenta
se multiplica por siete, porque ahí las fotos son de 4K.

### 2. El playhead repintaba seis veces por segundo aunque nada se moviera

`_playhead_timer` corre cada 150 ms **toda la sesión**: también en la hoja,
donde el visor ni se ve, también con la app en segundo plano y también con el
video parado media hora en el mismo cuadro. Cada tick repintaba la scrub bar
y los tres rótulos del timecode.

No es el problema grande —medido, ~0.7 % de un núcleo— pero es trabajo que no
le sirve a nadie.

## Lo que se hizo

**Las fotos se leen ya reducidas al tamaño de la tarjeta**, con
`QImageReader.setScaledSize`: el decodificador de JPEG reduce *mientras*
descomprime, así que la imagen grande no existe en memoria ni por un
instante. Se va el `_scaled_cache`: eran dos copias de la misma imagen, la
grande que nadie miraba y la chica que se dibujaba.

**Y hay un techo de tiras vivas** (`LIMITE_DE_TIRAS_VIVAS = 24`): solo las
últimas 24 tarjetas escrubeadas conservan sus doce fotos; las demás se quedan
con su portada. La cuenta vive en la hoja y no en la tarjeta porque el límite
es del conjunto.

**Y el tick del playhead compara antes de dibujar**: con el video pausado y
la misma posición, duración, `in_frame` y `out_frame` de la vez pasada, no
hay una sola cosa que redibujar. Se compara todo lo que el tick dibuja y no
solo la posición, porque marcar `I` u `O` con el video parado no mueve el
playhead y su único camino a la pantalla es este tick.

## Resultado, medido igual que antes

| momento | antes | ahora |
|---|---|---|
| proyecto abierto, 229 portadas | 1 348 MB | **780 MB** |
| después de escrubear 40 tarjetas | 2 972 MB | **857 MB** |
| tick del playhead en reposo | ~1 ms c/u, 6.7/s | 0.20 ms c/u, 6 de 234 hacen algo |

De los 780 MB que quedan, las fotos son **48 MB**: soltarlas todas a mano no
baja la RSS (849 → 840 MB), o sea que el resto es memoria que el asignador ya
liberó y no le devolvió al sistema. Bajarla más sería otra cosa —no tener 229
widgets vivos— y no es este bug.

Leer una miniatura de 4K además pasó de **32 ms a 12 ms**, así que escrubear
material sin proxy también se siente distinto.

## Lo que NO cambió

La imagen. Comparadas pixel a pixel, la miniatura leída en chico y la
escalada desde el original difieren **1.46 de 255 por canal** — invisible.
Verificado también mirando la hoja real con las 229 tarjetas puestas.
