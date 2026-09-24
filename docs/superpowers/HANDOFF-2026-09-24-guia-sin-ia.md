# Handoff: la guía de edición sin IA, por palabras clave

**Fecha:** 2026-09-24
**Repositorio:** `/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO`
**Rama de trabajo:** `master`
**Estado de partida:** la guía de edición funciona, pero clasifica los cuartos
pidiéndole a DeepSeek. Este handoff la vuelve determinista y offline.

## Objetivo

Que la «Guía de edición» se pueda armar **sin usar IA**: sin llave, sin
internet, sin espera y sin costo. El tablero de siete columnas se llena
reconociendo **términos clave** en el nombre de cada cuarto (`cocina`,
`comedor`, `recámara`, `cuarto`, `sala`, `baño`, `terraza`, `alberca`, `roof`,
`fachada`, `aérea`, `dron`, `vestidor`, …) y colocándolo en su columna.

Lo que no se reconozca **no se adivina**: se queda en la franja de abajo para
que Bruno lo arrastre a mano. La franja sigue siendo la garantía de que nunca
se inventa un cuarto.

**La IA se quita por completo** (decisión de Bruno, 2026-09-24): el proveedor
DeepSeek, la llave, la caja de la llave en Configuración y el camino de red se
borran en el mismo trabajo.

## Contexto relevante

Specs que gobiernan la guía, en orden:

- `docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md`
- `docs/superpowers/specs/2026-09-15-el-guion-y-las-carpetas-design.md`
- `docs/superpowers/specs/2026-09-19-guia-de-edicion-como-tablero-design.md`
  — éste define el tablero de siete columnas y dice que la IA solo clasifica.
- `docs/superpowers/specs/2026-09-21-guia-de-edicion-por-unidad-design.md`

El patrón de recorrido, que es lo que las columnas representan, vive en
`docs/patron-de-recorrido/MI-PATRON.md` y **no se toca**: las columnas ya son
ese patrón.

Lo que este handoff **no cambia** (y hay que conservar tal cual):

- Las siete columnas fijas, su orden y sus pistas (`guia.COLUMNAS`).
- El tablero (`pantalla_guia.py`): columnas, franja, «Sin usar», arrastrar,
  subir/bajar, quitar con ✕.
- `orden_aceptado` sigue emitiendo la lista plana de nombres, con repetidos.
- El aviso de «tu guía quedó vieja», la guía por unidad, el guardado en la
  sesión y el viaje congelado en el manifest.
- El plugin de Premiere (`uxp-plugin/`): la guía ya viaja en el manifest y el
  panel solo la lee. **No se toca nada de JS.**
- `cuartos_sin_usar` y el aviso «Sin usar: …».

## Cómo está hoy (lo que se va a cambiar)

- `src/clasificador_video/guia.py`
  - `MODELO = "deepseek-chat"`.
  - `prompt_de_clasificacion()`, `cuerpo_de_clasificacion()`,
    `leer_clasificacion()` y `_recortar_json()`: arman el pedido y leen la
    respuesta JSON del modelo.
  - `Clasificacion(ok, columna_de, inventados, error)`, `COLUMNAS`,
    `cuartos_sin_usar()`.
- `src/clasificador_video/ia.py` — la llamada HTTP a DeepSeek. **Se borra.**
- `src/clasificador_video/llave.py` — guarda la llave en
  `~/.clasificador_video/llave.json`. **Se borra.**
- `src/clasificador_video/ui/main_window.py`
  - `_GuiaJob` (línea ~244) corre `ia.preguntar` en un hilo.
  - `pedir_clasificacion()` (~5757): si no hay `llave.leer()`, llama
    `mostrar_falta_llave()`; si hay, arma el cuerpo y lanza el trabajo.
  - `guardar_llave()` / `borrar_llave()` (~5611) y el cableado de
    `pantalla_config` con `llave`.
- `src/clasificador_video/ui/pantalla_guia.py`
  - `armando()` («Pre-ordenando…»), `mostrar_falta_llave()`.
  - `mostrar_clasificacion(clasificacion, unidad=…)` consume la
    `Clasificacion`; **esta parte se queda igual**.
- `src/clasificador_video/ui/pantalla_config.py` — la caja de la llave y sus
  señales `llave_guardada` / `llave_borrada`; `cargar(llave, …)`.
- `src/clasificador_video/app.py` — el cableado de `llave` con Configuración.
- Pruebas que existen solo por la IA: `tests/test_ia.py`,
  `tests/test_llave.py`, y tramos con llave en `tests/ui/test_pantalla_config.py`,
  `tests/ui/test_main_window_guia.py` y `tests/test_app.py`.

## Diseño de la clasificación por palabras

Todo vive en `guia.py`, puro y sin Qt. La forma de salida es la misma
`Clasificacion` de hoy, así que **el tablero no cambia una línea**.

### La función

```python
def clasificar_por_palabras(cuartos: list[str]) -> Clasificacion:
    ...
```

Devuelve `Clasificacion(ok=True, columna_de={cuarto: id_columna}, inventados=[])`.
No puede fallar y no puede inventar cuartos.

### Cómo se compara (ojo con esto)

Se normaliza **una copia** para buscar el término —minúsculas y sin acentos—
pero el nombre que sale en `columna_de` es **el original, tal cual lo tecleó
Bruno**.

Esto es distinto de la revisión vieja del spec del 14, que comparaba por
igualdad exacta de cadena. Allá era *comparación* (¿el modelo repitió el mismo
cuarto?); aquí es *reconocimiento* (¿el nombre trae la palabra «cocina»?). Por
eso aquí sí se normaliza: Bruno escribe `recamara` sin acento y tiene que caer
en Habitaciones igual. Escribir esta razón en un comentario, porque parece
contradecir una regla del repo y no la contradice.

### Los términos por columna

Empiezan así (el implementador puede afinarlos con Bruno, pero no inventar
columnas nuevas):

| id | términos (se buscan como substring, normalizados) |
|---|---|
| `apertura` | fachada, entrada, acceso, porton, puerta, recibidor, frontal, aerea, aereo, dron, drone |
| `sociales` | cocina, sala, comedor, terraza, desayunador, bar, estancia, family |
| `habitaciones` | recamara, cuarto, habitacion, dormitorio, alcoba, baño, bano, vestidor, closet, walk in, principal |
| `aerea_media` | aerea media, media casa, intermedia, aerea intermedia |
| `amenidades` | alberca, piscina, roof, amenidad, amenidades, gym, gimnasio, asador, juegos, cancha |
| `area_general` | propiedad, general, terreno, lote, de lejos, casa completa, aerea de la propiedad |
| `aerea_final` | aerea final, final, cierre, salida, ultima toma, ultima, placa |

### Desempate (lo importante para que no adivine)

Un mismo nombre puede pegarle a dos columnas (`aerea final` pega en `apertura`
por «aerea» y en `aerea_final` por «final»; `baño de la recamara` pega dos
veces en `habitaciones`, que no es empate). La regla:

1. Se juntan **todos** los términos que aparecen en el nombre, con su columna.
2. **Gana el término más específico: el más largo** (más caracteres).
3. Si el término más largo aparece en **dos columnas distintas** (empate
   real), el cuarto se deja **fuera**: no se adivina, Bruno lo arrastra.
4. Si no aparece ningún término, el cuarto se deja **fuera**.

Con eso: `Aérea final` → `aerea_final` («aerea final» es más largo que
«aerea»); `Aérea` a secas → `apertura`; `Terraza con alberca` → deja fuera
(«terraza» y «alberca» empatan en largo, son columnas distintas); `Baño de la
recámara` → `habitaciones`.

## Plan, en orden

### 1. El clasificador, con pruebas (RED → GREEN)

Antes de tocar la pantalla, escribir en `tests/test_guia.py`:

- cada término canónico cae en su columna (`Cocina`→`sociales`,
  `Recámara 1`→`habitaciones`, `Alberca`→`amenidades`, `Fachada`→`apertura`,
  `Roof`→`amenidades`, `Vestidor`→`habitaciones`, …);
- sin acentos y en minúsculas también (`recamara`, `bano`, `aerea final`);
- el nombre devuelto es el original, no el normalizado;
- un cuarto sin término **no** aparece en `columna_de`;
- un empate entre columnas **no** aparece en `columna_de`;
- `inventados == []` siempre;
- lista vacía → `columna_de == {}` y `ok`.

Implementar `clasificar_por_palabras` y el ayudante de normalización.
Confirmar GREEN. Correr:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

### 2. Cablear la pantalla sin llave ni red

- `main_window.pedir_clasificacion()`: llamar
  `logica_guia.clasificar_por_palabras(cuartos)` **directo** y pasar el
  resultado a `_mostrar_guia` (o directo a `mostrar_clasificacion`). Sin
  `llave.leer()`, sin `_GuiaJob`, sin hilo, sin `armando()`.
- Quitar el ramal de `mostrar_falta_llave()` y el método.
- `pantalla_guia.armando()` se puede borrar (la clasificación es instantánea).
- Escribir/ajustar en `tests/ui/test_main_window_guia.py` una prueba que abra
  la pantalla **sin llave configurada** y confirme que el tablero se llena con
  la clasificación por palabras (los cuartos reconocidos aparecen ya puestos).
- `mostrar_clasificacion` y `Clasificacion` **no cambian**.

Commit sugerido:

```text
Clasificar la guía por palabras clave, sin llamar a la IA
```

### 3. Borrar la IA y la llave

En el mismo commit que deje lo anterior verde:

- Borrar `src/clasificador_video/ia.py`, `src/clasificador_video/llave.py`,
  `tests/test_ia.py`, `tests/test_llave.py`.
- `guia.py`: borrar `MODELO`, `prompt_de_clasificacion`,
  `cuerpo_de_clasificacion`, `leer_clasificacion`, `_recortar_json`. Se quedan
  `COLUMNAS`, `Clasificacion`, `Renglon`, `Respuesta`, `cuartos_sin_usar`.
- `main_window.py`: borrar `_GuiaJob`, el import de `ia`, el import de `llave`,
  `guardar_llave`, `borrar_llave` y su cableado.
- `pantalla_config.py`: quitar la caja de la llave, sus señales y el parámetro
  `llave` de `cargar()`.
- `app.py`: quitar el cableado de `llave` con Configuración y el argumento de
  `cargar()`.
- Actualizar las pruebas que quedaron tocando la llave en
  `tests/ui/test_pantalla_config.py`, `tests/ui/test_main_window_guia.py` y
  `tests/test_app.py` (los tramos de `llave`/`preferencias` de la llave, no
  los de `modo_economico`/`modo_rapido`, que son de miniaturas y se quedan).
- `grep -rn "llave\|deepseek\|preguntar(" src/ tests/` para confirmar que no
  queda nada colgando.

No dejar `ia.py` ni `llave.py` «por si acaso»: es regla escrita del repo y git
ya guarda el historial.

Commit sugerido:

```text
Quitar DeepSeek y la llave: la guía ya no necesita IA
```

### 4. Regresión completa y verificación visual

- Suite completa:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

- Pruebas del plugin (no debería cambiar nada, pero confirma que no se tocó):

```bash
node uxp-plugin/pruebas/correr.js
```

- **Verificación visual real** (regla de `CLAUDE.md`: si no se miró la imagen,
  no se afirma): construir la `PantallaGuia` en una ventana de prueba, aplicar
  una `Clasificacion` de ejemplo y guardar un PNG con `grab()`; leerlo y
  confirmar que las columnas quedaron pobladas y la franja con los no
  reconocidos. El PNG va al scratchpad, no al repo.

Commit sugerido:

```text
Verificar la guía sin IA de punta a punta
```

### 5. Checkpoint manual con Bruno

Abrir Clipify desde la fuente actual, **sin llave configurada**, con un
proyecto de verdad:

- la pantalla de la guía abre y el botón «Pre-ordenar» llena las columnas al
  instante;
- `cocina`, `comedor`, `recámara`, `cuarto`, `baño`, `terraza`, `alberca`,
  `roof`, `fachada` caen donde deben;
- lo que no se reconoce se queda en la franja y se puede arrastrar;
- no aparece ningún aviso de llave ni de red;
- «Usar este orden» reacomoda el rail y la hoja igual que antes.

## Disciplina requerida

Para cada paso que cambie código:

1. escribir/ajustar la prueba;
2. correrla y confirmar RED;
3. implementar el mínimo cambio;
4. correrla y confirmar GREEN;
5. correr siempre la suite completa:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

6. actualizar la bitácora de la sesión (si se usa una carpeta
   `.superpowers/sdd/.../progress.md`, registrar RED/GREEN, resultado de la
   suite y el commit);
7. un commit atómico por paso, mensaje en español mexicano.

Cuando un término, una aserción o una hipótesis no coincida con la realidad,
imprimir el dato real y corregir la prueba o la implementación con esa
evidencia. No inventar columnas ni jerarquías.

## Criterio de salida

El trabajo termina con la suite completa en verde y el checkpoint manual
exitoso: una guía armada **sin llave y sin internet**, con los cuartos
reconocidos en su columna y los demás esperando en la franja. La IA, la llave
y su caja en Configuración ya no existen en el repo.
