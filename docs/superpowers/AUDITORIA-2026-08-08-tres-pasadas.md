# Auditoría exhaustiva en tres pasadas — 2026-08-08

Pedida por Bruno después de cerrar la F10. Cada pasada con **tipos de prueba
distintos**, no repitiendo la misma. Estado final: **792 tests en verde**,
árbol limpio.

---

## Qué se corrió, y qué encontró cada cosa

| Técnica | Qué hace | Encontró |
|---|---|---|
| **Invariantes + recorrido aleatorio** | 7 600 pasos de teclas al azar, comprobando 9 invariantes después de **cada** paso | nada |
| **Oráculo** | recalcula por fuera lo que la interfaz dice (leyenda, progreso, conteos, avisos, contador de proxies, resumen, cola) y compara, 900 veces | nada |
| **Ida y vuelta de `⌘Z`** | 400 acciones al azar: hacer, deshacer, comparar el estado exacto | nada |
| **Punta a punta con material real** | importar, clasificar, marcar, guardar sesión, exportar manifest | 1 bug |
| **Contrato contra el plugin** | el JSON que sale contra lo que `processManifest.js` realmente lee, caso por caso | 1 bug |
| **Datos degenerados** | rango de 0 cuadros, invertido, negativo, más allá del final, nulos, nombres con `/`, comillas, japonés, 119 caracteres | nada (2 falsas alarmas) |
| **Barrido de geometría** | nada fuera de su padre ni encimado, 5 tamaños × 2 modos | 1 bug |
| **Fugas y concurrencia** | 900 acciones contando widgets, importar dos veces sin esperar, cerrar con trabajo en vuelo | nada |
| **Análisis estático** | funciones que nadie llama, `TODO`, `print`, `except` amplios, colores fuera del tema | 1 código muerto |
| **Propiedades sobre lógica pura** | ~11 000 entradas al azar contra orientación, etiqueta de resolución, emparejar proxies, timecode | nada |
| **Comparación con el mockup** | recortes ampliados en las dos pantallas, después de cada cambio | 1 regresión |

---

## Los cinco arreglos

### 1. El manifest exportaba el rango invertido tal cual

Marcar `O` y después `I` más adelante deja `out < in`. La app ya lo **mostraba**
en orden —se arregló en la auditoría de la F1–F5, con `abs()`— pero lo
exportaba crudo, y el plugin aplica in/out siempre que vengan los dos: Premiere
recibía un rango al revés.

Es el mismo bug corregido dos veces en la interfaz, en **el tercer lugar donde
vive el mismo dato** — y el único de los tres donde no se nota, porque el
síntoma aparece dentro de Premiere.

Se ordena solo al exportar: la sesión sigue guardando lo que el editor marcó,
para que deshacer pueda volver a eso.

### 2. Los tests de interfaz medían una app que no existe

`tests/ui/` no aplicaba la hoja de estilos. Sin ella Qt le da a cada
`QPushButton` el ancho mínimo de plataforma —80 px en macOS— y el selector de
calidad pasa de **149 px a 320**.

Se notaba sin que nadie lo viera: `pytest tests/ui/test_video_stage.py` **a
solas daba dos tests en rojo**, y en la suite completa pasaban, porque otro
archivo aplicaba la hoja antes.

Y costó un diagnóstico falso: el renglón 6 del barrido de la F10 («el control
de velocidad queda en `x = -165`») era un espejismo del arnés. Ya está
corregido en el plan de la F10.

### 3. Un nombre de archivo largo se metía debajo de los controles

Seguía de largo **por debajo** del selector de calidad y se leía partido a la
mitad por una caja translúcida encima. QSS no tiene `text-overflow: ellipsis`.

La regla, con la decisión de Bruno adentro: la velocidad se queda mientras el
nombre **entero** entre a su lado; cuando ya no, se va la velocidad antes de
cortar el nombre; y si aun así no entra, recién ahí se corta con puntos
suspensivos en medio.

### 4. `_bulk_targets` no lo llamaba nadie

Código muerto desde la F5.

### 5. El arnés ponía los tamaños de proxy antes de tiempo

`load_clips` los limpia —van por índice de clip, igual que el historial— y el
arnés los asignaba **antes**, así que el badge de la comparación decía `PROXY` a
secas. Lo encontró volver a mirar el recorte después de tocar `load_clips`.

---

## Cuatro falsas alarmas, y por qué no lo eran

Anotadas porque comprobarlas costó tiempo y volverían a parecer bugs:

- **«La pastilla de rango conserva el texto viejo al quitar el rango con `U`.»**
  Lo conserva, pero **está escondida**. El test leía `.text()` sin mirar
  `isHidden()`.
- **«La ventana no puede bajar de 1 599 px de ancho.»** Achicándola de golpe,
  sí; arrastrando el borde —que es lo que hace una persona— baja hasta 1 027.
  El mínimo se recalcula con cada paso.
- **«`in == out` exporta un rango de 0 cuadros.»** Es lo que el editor marcó, y
  la app lo dice tal cual (`0 f`). Queda como observación para Bruno, no como
  arreglo.
- **«`esc` no hace nada en modo hoja.»** Correcto: deshace una capa por vez
  —solo video → clip → hoja— y la hoja es la de más afuera.

---

## Lo que queda abierto, para Bruno

**Los archivos `.LRF` del dron entran como clips.** DJI escribe un `.LRF` junto
a cada `.MP4` —es su proxy— y la app los importa como material, así que cada
toma del dron aparecería **dos veces** en la hoja. Es el mismo caso que los
`S03` de la Sony, que ya se excluyen. No se cambió porque decidirlo es de
Bruno: puede ser que en su flujo el `.LRF` sí sea material.

**Un proxy escrito en minúsculas (`c0001s03.mp4`) no se empareja.** La cámara
siempre escribe `S03`, así que hoy no pasa; y cuando pasara, el efecto es que
ese clip se queda sin proxy — nunca una marca que miente.

---

## Rendimiento, al cierre

| Acción | Costo |
|---|---|
| Tecla de cuarto | 5.74 ms |
| Cruce de modo, ida y vuelta | 36.4 ms |
| Cuadro de la transición (128 tarjetas) | 0.02 ms de mediana |
| Widgets tras 180 teclas | 701 → 673, sin fuga |

---

## La lección de estas tres pasadas

**Un arnés de medición que no monta la app completa mide otra app.** Es prima
hermana de las dos trampas que el handoff ya anotaba —contar widgets sin
procesar `DeferredDelete`, y un doble de pruebas que tapa el bug que existe— y
esta vez costó un diagnóstico entero, un arreglo mal justificado y un renglón
falso en un plan.

La contrapartida es que **volver a mirar después de cada cambio** encontró la
regresión del punto 5 en menos de un minuto. La suite no la habría encontrado
nunca: no compara contra el mockup.
