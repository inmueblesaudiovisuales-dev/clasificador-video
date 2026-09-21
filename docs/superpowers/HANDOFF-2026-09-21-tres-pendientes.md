# Handoff — tres pendientes: riesgo de nombres repetidos, pruebas que
# fallan desde antes, y dos specs sin plan

**Fecha:** 2026-09-21
**Rama:** `master` (directo, sin branches)
**Estado del repo:** working tree limpio. Todo comprometido y subido a
`origin/master`. La app instalada en `/Applications/Clipify.app` es la
**2.7.0**, empaquetada y puesta ayer con toda la feature de unidades y
departamentos (ver
`HANDOFF-2026-09-20-tres-bugs-renombrar-y-unidades.md` para el contexto
completo de esa sesión).

Bruno pidió tres cosas para retomar, sin ligarlas entre sí:

1. Arreglar preventivamente un riesgo conocido que quedó documentado
   ayer (renombrar/borrar un cuarto puede tocar la unidad equivocada).
2. Investigar las 5 pruebas que fallan desde antes de esta feature.
3. Avanzar los dos specs aprobados que todavía no tienen plan ni código
   (rediseño de la Guía de edición, y reconectar todo el material).

Van en ese orden porque el primero es chico y de bajo riesgo, el segundo
es investigación pura (puede no llevar a ningún cambio de código), y el
tercero es el trabajo grande — mejor no arrancarlo a la mitad de una
sesión.

---

## 1. Arreglar preventivamente: renombrar/borrar un cuarto por nombre repetido entre unidades

### El riesgo, tal como quedó documentado ayer

Con la feature de unidades (commits del 2026-09-20, ver el handoff de
ayer), dos unidades distintas pueden tener un cuarto con el MISMO
nombre — es el caso normal, no uno raro: "Cocina" en "Casa A" y "Cocina"
en "Casa B" es justo para lo que existen las unidades.

`_on_room_moved_en_unidad`/`_on_room_reordered_en_unidad`
(`src/clasificador_video/ui/main_window.py:2110-2141`) ya se corrigieron
ayer: el rail identifica de qué `_FilaCuarto` salió el arrastre
(`RoomRail._FilaCuarto.unidad`, fijado en `room_rail.py:731`) y opera
sobre `self.room_selections[unidad]`, nunca sobre `self.room_selection`
(el alias de la unidad ACTIVA) a ciegas. Así, arrastrar el "Cocina" de
Casa B mientras Casa A está activa ya NO reordena la Cocina de Casa A.

**Lo que quedó SIN corregir** (documentado como riesgo conocido, no como
bug bloqueante, en el commit `de0bbaf` y su revisión):
`_on_room_renamed` (`main_window.py:2071-2091`) y `_on_room_removed`
(`main_window.py:2143-2170`) siguen operando **por nombre, sobre
`self.room_selection`** — la unidad activa, adivinada, no la unidad de
origen real del cuarto que Bruno renombró o borró desde el rail.

Ejemplo concreto del bug: con Casa A activa, si Bruno renombra el
"Cocina" de Casa B (visible en su propia banda del rail) a "Cocina
grande", hoy eso termina renombrando el "Cocina" de Casa A — la unidad
equivocada, en silencio.

### Por qué el arreglo de arrastrar NO se copia y pega tal cual

`room_moved_en_unidad`/`room_reordered_en_unidad` son señales NUEVAS que
`RoomRail` emite además de las viejas `room_moved`/`room_reordered`
(que siguen existiendo e intactas, para el camino sin unidades). El
mismo patrón aplica aquí: hace falta una señal nueva
`room_renamed_en_unidad`/`room_removed_en_unidad` que SÍ lleve la
unidad, dejando las viejas `room_renamed`/`room_removed` tal cual para
cuando el rail no tiene bandas (proyecto sin unidades, o solo el
catálogo `""`).

Revisar antes de escribir código:
- `room_rail.py:166-346` — la clase `_FilaCuarto`, en particular cómo
  `rename_requested`/`remove_requested` se arman hoy (líneas 178, 180,
  340, 346) y si tienen forma de acceder a `self.unidad` en el momento de
  emitir (el atributo ya existe en la instancia desde `set_rooms_agrupados`,
  línea 731 — solo falta usarlo en la señal).
- `room_rail.py:663` y `room_rail.py:733` — los dos lugares donde
  `fila.rename_requested.connect(self.room_renamed.emit)` y
  `fila.remove_requested.connect(self.room_removed.emit)` se conectan hoy
  (uno para el camino plano `set_rooms`, otro para el agrupado
  `set_rooms_agrupados`). Solo el segundo necesita la variante nueva —el
  primero no tiene bandas, no hay ambigüedad de unidad ahí.
- `main_window.py:2110-2141` — el patrón exacto a replicar para
  `_on_room_renamed_en_unidad`/`_on_room_removed_en_unidad`: catálogo por
  `self.room_selections.get(unidad)`, `if catalogo is None: return`, y
  `_sync_rooms()` solo si `unidad == (self._unidad_activa or "")`, si no
  `_refresh_rail()` + `_autosave()`.

**Ojo con `_on_room_renamed`**: a diferencia de mover/reordenar (que no
tocan ningún clip), renombrar SÍ reescribe `clip.categoria_path` de cada
clip afectado, actualiza `self.history` y `self._ultimo_cuarto_usado`.
La versión "en unidad" tiene que hacer lo mismo pero filtrando los clips
por `self._unidad_de(clip.categoria_path) == unidad` además de por
cuarto — hoy el bucle de la línea 2079 no filtra por unidad porque
`self.room_selection.rename` ya limitaba el universo a la unidad activa
implícitamente; con la unidad correcta explícita, hay que agregar ese
filtro a mano o un clip de OTRA unidad con el mismo nombre de cuarto se
renombraría también por error.

**Y con `_on_room_removed`**: mismo cuidado — el filtro de `afectados`
(línea 2147-2150) hoy no distingue unidad, y debe.

### Cómo probarlo

Sigue el patrón de los tests que ya existen para el arreglo del
arrastre (`tests/ui/test_main_window_unidades.py`, buscar los que
prueban `_on_room_moved_en_unidad`/`_on_room_reordered_en_unidad` como
plantilla) y `tests/ui/test_room_rail_unidades.py`. El caso mínimo que
tiene que existir: dos unidades con un cuarto del mismo nombre, Casa A
activa, renombrar (o borrar) el cuarto de Casa B desde el rail, y
confirmar que Casa A no cambió.

### Alcance sugerido

Chico: un par de señales nuevas + dos handlers nuevos en `main_window.py`
+ sus pruebas. Se puede hacer directo, sin brainstorm — es la misma
decisión de arquitectura que ya se tomó y ejecutó ayer para
mover/reordenar, aplicada a las dos operaciones que quedaron pendientes.

---

## 2. Investigar las 5 pruebas que fallan desde antes de la feature de unidades

Estas 5 fallan en `master` desde antes de que empezara la sesión de
unidades y departamentos (confirmado corriendo la suite en el commit
anterior a esa sesión, con `git stash`, el 2026-09-20 — ver el handoff
de ayer). Ninguna se investigó todavía. Todas viven en
`tests/ui/test_main_window.py`:

| Test | Línea |
|---|---|
| `test_cache_hit_no_relanza_mpv` | 375 |
| `test_modo_economico_baja_los_hilos_y_el_limite_de_tiras` | 4362 |
| `test_modo_economico_baja_cuantos_ffprobe_corren_a_la_vez_al_importar` | 4384 |
| `test_sin_duracion_la_portada_vieja_no_se_re_extrae_cada_sesion` | 4596 |
| `test_una_tira_con_marca_no_se_rehace_aunque_tenga_pocas_fotos` | 4904 |

Correr solo estos cinco para verlos fallar de entrada:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest \
  tests/ui/test_main_window.py::test_cache_hit_no_relanza_mpv \
  tests/ui/test_main_window.py::test_modo_economico_baja_los_hilos_y_el_limite_de_tiras \
  tests/ui/test_main_window.py::test_modo_economico_baja_cuantos_ffprobe_corren_a_la_vez_al_importar \
  tests/ui/test_main_window.py::test_sin_duracion_la_portada_vieja_no_se_re_extrae_cada_sesion \
  tests/ui/test_main_window.py::test_una_tira_con_marca_no_se_rehace_aunque_tenga_pocas_fotos \
  -v
```

**Hipótesis de trabajo, sin confirmar**: los cinco nombres apuntan a la
misma zona (caché de miniaturas/proxies, modo económico, extracción de
portadas) — es plausible que compartan una sola causa raíz en vez de ser
cinco bugs sueltos. Usar `superpowers:systematic-debugging` antes de
tocar nada: no asumir la hipótesis de arriba sin confirmarla leyendo cada
`assert` que falla.

**Riesgo a vigilar mientras se investiga** (documentado en
`docs/DESARROLLO.md`): este proyecto ha tenido cuatro segfaults
intermitentes bajo `offscreen`, y uno de ellos apareció después de
decenas de corridas limpias. Si alguno de estos cinco resulta ser
intermitente y no un fallo consistente, correr varias veces (número
decidido de antemano) antes de concluir nada — un fallo 1 de cada 20
veces se ve "arreglado" por pura suerte en 20 corridas limpias más de un
tercio de las veces.

**Posible resultado válido**: que la investigación concluya que no vale
la pena arreglarlos ahora mismo (por ejemplo, si resultan ser fallas del
entorno `offscreen` y no del comportamiento real de la app) — en ese
caso, documentar la conclusión aquí o en un handoff nuevo es un buen
cierre, no hace falta forzar un arreglo.

---

## 3. Los dos specs aprobados sin plan de implementación

### 3.a — Rediseño de la Guía de edición (tablero de columnas)

Spec completo y ya escrito:
`docs/superpowers/specs/2026-09-19-guia-de-edicion-como-tablero-design.md`
(280 líneas). Mockup interactivo aprobado en
`docs/superpowers/mockups/guia-de-edicion-2026-09-19/mockup.html`.

Resumen de lo ya decidido (no reabrir sin razón nueva — leer el spec
completo antes de tocar nada, esto es solo un resumen):
- Tablero de 7 columnas fijas, una por cada momento del patrón de
  `docs/patron-de-recorrido/MI-PATRON.md`.
- La IA se reduce a clasificar cada cuarto en su columna (una llamada
  chica) — nada de prosa ni razones generadas.
- Franja de cuartos siempre disponible abajo para arrastrar (repetir un
  cuarto las veces que haga falta).
- Se van las preguntas de contexto, el párrafo de recorrido, el "por
  qué" de cada paso, y la revisión de "te falta/te sobra un cuarto"
  (ya no puede sobrar uno inventado por diseño).
- Restricción explícita: nunca inventar un cuarto que Bruno no haya
  tecleado.

**Siguiente paso**: correr `superpowers:writing-plans` sobre ese spec.
No hace falta brainstorm — el spec ya es el resultado de uno (memoria
corregida hoy: antes decía que el spec no existía, era un dato viejo).

### 3.b — Reconectar todo el material (relink estilo Premiere)

Spec completo y ya escrito:
`docs/superpowers/specs/2026-09-19-reconectar-todo-el-material-design.md`
(155 líneas).

Resumen de lo ya decidido (leer el spec completo antes de tocar nada):
- Sin botón nuevo: el mismo "Buscar…" de cada cuarto pasa de pedir una
  carpeta a pedir un archivo.
- Del archivo elegido se derivan la carpeta nueva de ESE bin y el
  "cambio de ruta" (comparando el sufijo común entre
  `bins.origen_de(nombre)` y la carpeta nueva).
- Ese cambio se aplica a los demás bins con material perdido, **solo si
  la carpeta resultante existe de verdad en disco**.
- El archivo se empareja por nombre contra TODOS los clips del bin; si
  el nombre le queda a más de uno, no se adivina — se pide la carpeta a
  mano para ese cuarto.
- Proxies quedan fuera (siguen pidiendo carpeta aparte).
- La función nueva vive en `revinculo.py` (sin Qt, se prueba con Python
  puro).

**Antes de correr `writing-plans` en este**: la memoria de la sesión
dice que, al 2026-09-19, Bruno todavía no había revisado el spec por
escrito (solo se había hablado del diseño). Han pasado dos días —
**confirmar con Bruno que el spec sigue representando lo que quiere**
antes de armar el plan, en vez de asumir que sigue vigente sin
preguntar.

### Orden sugerido entre los dos

Ninguno depende del otro técnicamente. Si Bruno no tiene preferencia,
"reconectar todo" es más chico (155 líneas de spec, función pura sin Qt)
y más rápido de plan-y-ejecutar que el tablero de la guía (280 líneas,
toca UI e IA) — puede ser el más fácil de cerrar primero, pero es
decisión de Bruno, no algo a asumir.
