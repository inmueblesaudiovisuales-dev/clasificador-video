# Modo rápido de miniaturas — diseño

*(Spec del 2026-09-20. Punto 8 de la tanda de bugs del shooting del
2026-09-19 — [HANDOFF-2026-09-19-tanda-de-bugs-del-shooting.md](../HANDOFF-2026-09-19-tanda-de-bugs-del-shooting.md) —,
marcado ahí como feature nueva que necesitaba brainstorm antes de tocar
código.)*

## 1. El problema

Bruno pidió "un modo rápido: combinar el modo económico con hacer menos
miniaturas". En la conversación salió que estaba confundido sobre lo que
"Modo económico" ya hace, así que primero se aclaró eso:

**Modo económico (`preferencias.modo_economico`, hoy) junta dos cosas
bajo un solo interruptor:**

1. Miniaturas chicas (480px) y pocas por tira (6 en vez de 12).
2. Un freno de paralelismo: las procesa **de una en una** en vez de
   varias a la vez — pedido explícito de Bruno para una MacBook Air M1 de
   8GB, donde 3 en paralelo decodificando HEVC empuja a la máquina a usar
   swap (ver el comentario en `main_window.py` junto a
   `HILOS_DE_MINIATURAS_ECONOMICO`).

Ese freno es justo lo que hace que económico se sienta **lento**: no
paga el tamaño chico de las miniaturas, paga procesarlas de a una. En la
computadora de Bruno, que sí aguanta varias a la vez, ese freno no
protege nada — solo hace perder tiempo.

Lo que Bruno quiere es el punto 1 (chicas y pocas) sin el punto 2 (sin
el freno). Son dos ejes, no uno.

## 2. Diseño: un interruptor nuevo e independiente

**"Modo rápido" (`preferencias.modo_rapido`, nuevo)** controla el mismo
tamaño/cantidad de miniaturas que económico, pero nunca frena el
paralelismo. Es un booleano aparte, no una variación de económico ni un
reemplazo.

Con dos interruptores independientes hace falta una regla de precedencia
para cuando los dos están marcados a la vez — se resolvió así, confirmado
con Bruno:

- **Miniaturas chicas y pocas** se prenden si **económico O rápido**
  están marcados (cualquiera de los dos alcanza).
- **El freno de "una a la vez"** se prende solo si **económico está
  marcado Y rápido no** — rápido siempre gana: si está marcado, nunca
  hay freno, así económico también lo esté.

| económico | rápido | miniaturas | paralelismo |
|-----------|--------|------------|--------------|
| no        | no     | grandes, 12 | todas a la vez |
| sí        | no     | chicas, 6   | de una en una (como hoy) |
| no        | sí     | chicas, 6   | todas a la vez |
| sí        | sí     | chicas, 6   | todas a la vez (rápido manda) |

"Modo económico" no cambia nada de su comportamiento actual — sigue
siendo exactamente lo que es hoy. "Modo rápido" es la fila nueva de la
tabla.

## 3. Qué toca el freno de paralelismo, exactamente

Para no tocarlo por accidente al implementar, la lista completa de lo
que hoy depende de `modo_economico` y vive del lado del **freno**
(no cambia con este spec):

- `HILOS_DE_MINIATURAS_ECONOMICO` / `_NORMAL` — cuántas tiras se extraen
  a la vez (`main_window.py`, `setMaxThreadCount`).
- `SONDEOS_EN_PARALELO_ECONOMICO` / `SONDEOS_EN_PARALELO` — cuántos
  proxies se validan (`ffprobe`) a la vez.
- `LIMITE_DE_TIRAS_VIVAS_ECONOMICO` / `_NORMAL` — cuántas tiras quedan
  cargadas en memoria a la vez (RAM, no CPU, pero mismo espíritu: cuidar
  una máquina chica).

Y lo que depende de `modo_economico` hoy y pasa a depender de **"chicas
y pocas" (económico O rápido)**:

- El ancho de escala en `thumbnails.py`
  (`ANCHO_MINIATURA_ECONOMICO` / `_filtro_de_escala`).
- `STRIP_COUNT_ECONOMICO` (6) vs `STRIP_COUNT` (12) en `_ThumbnailJob`.
- El sufijo `"|economico"` en la clave de cache de `cache_dir_for` — que
  sigue siendo un solo booleano en la firma de la función; lo que cambia
  es de dónde sale ese booleano en `main_window.py`.

## 4. La pantalla de Configuración

Un checkbox nuevo, debajo del de "Modo económico" existente, mismo
estilo:

```
Modo económico
☑ Generar menos miniaturas a la vez
  Prende esto en una computadora con menos memoria o menos núcleos,
  como una MacBook Air: la app saca las miniaturas de una en una en
  vez de varias a la vez. Tarda más en terminar, pero no se traba.

Modo rápido
☐ Miniaturas chicas y pocas, todas a la vez
  Mismas miniaturas chicas que el modo económico (menos fotos por
  tira, menos resolución), pero sin el freno de "una a la vez" — para
  cuando tu computadora aguanta procesar varias al mismo tiempo y solo
  quieres terminar rápido.
```

Por default **apagado**: cambia cómo se ve el escrubeo (más tosco), así
que es Bruno quien lo prende cuando lo quiere, no viene forzado — mismo
criterio que ya se usó para otras preferencias que cambian una
experiencia visible (no una que solo evita que la app se trabe, que sí
justifica venir prendida por default, como sigue siendo el caso de
económico).

## 5. Alcance

Esto es sobre la extracción de miniaturas nada más — no toca proxies (el
tamaño de los proxies es otro tema, ya resuelto en su propia spec), ni
la calidad del video en el visor.

No hace falta migrar nada: `modo_rapido` es una llave nueva en el mismo
`preferencias.json`; si falta, `False` (el default), y el comportamiento
de `modo_economico` no cambia para quien nunca toque el checkbox nuevo.
