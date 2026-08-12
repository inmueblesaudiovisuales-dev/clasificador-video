# Análisis post-F3: ¿nos estamos olvidando de algo? — 2026-08-08

Punto de control obligatorio del plan maestro, hecho después de la F2.1 y la
F3. Reemplaza a [`ANALISIS-2026-08-08-post-f2.md`](ANALISIS-2026-08-08-post-f2.md),
que queda como registro de lo que se arregló.

**La pregunta que contesta este documento no es «¿qué falta?» sino «¿qué falta
que NADIE tiene asignado?»** — porque eso es lo que se olvida.

## Cómo se hizo

No de memoria y no releyendo el plan, que es lo que deja pasar las omisiones:

1. Se extrajeron **todas** las clases CSS del `<body>` del mockup, en las dos
   pantallas, en orden de aparición. Son el inventario completo de lo que el
   diseño dice que existe.
2. Cada una se buscó en el código con `grep` y se marcó: **hecha**, **asignada
   a una fase**, o **huérfana**.
3. Se cruzó la tabla de teclado de `DECISIONES.md` contra los atajos que
   `_install_shortcuts` registra de verdad.
4. Se buscaron promesas rotas: texto que la app muestra prometiendo algo que
   no hace.

---

## 1. El hallazgo: nueve cosas sin dueño

Todas existen en el mockup o en `DECISIONES.md`, y **ninguna fase las
reclamaba**. Sin este barrido habrían llegado al final del rediseño como
sorpresa.

| # | Qué | Dónde está | Propuesta |
|---|---|---|---|
| 1 | **La forma de la barra de reproducción** | mockup `.scrub` | **F6** |
| 2 | **Pastilla `rango 07:04 · 212 f · total 18:11`** | mockup `.rangepill` | **F6** |
| 3 | **Renglón de teclas bajo la barra** (`← → cola · , . frame · F · esc`) | mockup `.v-keys` | **F6** |
| 4 | **Contador de frame `f 293`** junto al timecode | mockup `.fr` | **F6** |
| 5 | **`espacio ▶ ‖`** al pie de la columna de herramientas | mockup `.toolhint` | **F6** |
| 6 | **Campo «Buscar clip o cuarto…»** en la hoja | mockup `.search` | **F5** |
| 7 | **Barra de acciones de selección múltiple** | mockup `.batch` | **F8** |
| 8 | **Portada de la miniatura al 25% del clip** | `DECISIONES.md` | **F8** |
| 9 | **Los dos iconos de vista** de la hoja | mockup `.viewtoggle` | **descartar** |

### El más caro: la barra de reproducción (1, 2, 3)

Verificado mirando la imagen, con in/out puesto para no confundir «falta la
función» con «faltan los datos de ejemplo». **La función está** —marca el
rango, los extremos y el playhead—, pero el dibujo es otro:

- el mockup usa una **banda llena de 26 px**: el rango in/out es un bloque
  azul sólido, lo de afuera se oscurece, y los extremos llevan su letra `I`/`O`;
- la app usa **líneas finas**: el rango es una raya azul entre dos marcas.

Va en la **F6** y no en el barrido final porque esa fase ya tiene que rehacer
todo ese bloque para meter el control de velocidad. En el mockup el pie del
video es una sola pieza —timecode, barra y pastilla—; hacerlo dos veces es
tirar trabajo.

**Lo que NO se degrada para parecerse al mockup**: la barra actual tiene marcas
de tiempo adaptativas que el mockup no dibuja. Se conserva (regla del plan
maestro: «mejor que el mockup está permitido, pero se avisa»).

### El más barato y el más olvidable: la portada al 25% (8)

`DECISIONES.md` es explícito: *«El frame de portada es el del 25% del clip, no
el primero»*, porque en un recorrido el primer frame suele ser una puerta o
movimiento borroso. Hoy `ClipCard.set_frames` usa `len(pixmaps) // 2`, el
frame del **medio**.

**Por qué se perdió**: estaba en la vieja F4 («miniaturas verticales y
agrupación»), que se **disolvió** dentro de la F2 cuando se decidió que la hoja
necesitaba las proporciones reales desde el principio. La F2 se llevó las tiles
y la agrupación; la portada al 25% se quedó sin fase y nadie lo notó.

Es cambiar `// 2` por `// 4`. Lo caro no era hacerlo: era acordarse.

### El que hay que descartar: los iconos de vista (9)

El mockup tiene dos iconos de vista en el encabezado de la hoja. **No hay
ninguna decisión detrás**: `DECISIONES.md` no menciona una vista de lista ni
nada que esos iconos activarían. Es decoración de una función que nunca se
decidió.

Propongo **no construirlos** y anotarlo. Construir un control porque está
dibujado, sin saber qué hace, es exactamente cómo se llega a botones muertos.

---

## 2. Una promesa rota, y es culpa mía

**La app anuncia `⌘A` en dos lugares y no lo implementa.** El encabezado de
cada grupo dice `⌘A selecciona el grupo` —lo agregué yo en la F2.1, copiando el
mockup— y antes de eso el encabezado de la hoja ya decía `⌘A grupo`, desde la
F2. `grep` no encuentra ningún atajo registrado.

Es el mismo error que el plan maestro tiene anotado en su lista de ejecución
(*«Mención de `Ctrl+Z` sin implementación»*) y que la F4 va a cerrar. Se me
coló uno nuevo mientras arreglaba otra cosa.

**✅ Resuelto el mismo día** (commit `57680a3`): Bruno eligió implementarlo en
vez de esperar a la F5. Ya existe, registrado con `QKeySequence.SelectAll`.

---

## 3. Código muerto encontrado

Buscando campos y ramas que nadie lee, que es el detector que mejor funcionó
hasta ahora:

| Qué | Por qué está muerto |
|---|---|
| ~~`ACTION_KEYS["u"] = "none"` en `keyboard.py`~~ | **Inalcanzable.** `handle_key_press` intercepta la `u` antes —para limpiar in/out— y hace `return`. ✅ borrado |

## 4. Contradicciones con `DECISIONES.md`

| Qué dice `DECISIONES.md` | Qué hace la app hoy | Propuesta |
|---|---|---|
| *«`P` `X` — repetir la tecla vuelve a neutral»* | `P` sobre un pick lo deja en pick | **F7** |
| *«No hay tecla de neutral»* | Existe `U`, que limpia in/out | ✅ resuelto — ver abajo |
| La tabla de teclado no menciona `U` | `U` está registrada y funciona | ✅ resuelto |

**✅ Resuelto el mismo día** (commit `57680a3`): `U` se queda y ya está escrita
en la tabla de teclado de `DECISIONES.md`. La frase «no hay tecla de neutral»
se precisó — habla del flag, no del rango, porque en el rango no hay tecla que
repetir. `ACTION_KEYS["u"]`, que estaba muerto, se borró.

**Queda pendiente para la F7**: que `P` y `X` vuelvan a neutral al repetirse.

---

## 5. Estado real del teclado

De la tabla de `DECISIONES.md`, contra `_install_shortcuts`:

| Tecla | Estado | Fase |
|---|---|---|
| `espacio`, `1`–`9`, `P`, `X`, `I`, `O` | ✅ funcionan | — |
| `⇧`+click, y la asignación en lote | ✅ funcionan | — |
| `←` `→` | ✅ funcionan, pero recorren **todo**, no la cola | F5 |
| `⌘Z` | ❌ **anunciado y ausente** | F4 |
| `⌘A` | ✅ implementado el 2026-08-08 (ver §2) | — |
| `,` `.` frame por frame | ❌ | F6 |
| `S` igual al anterior | ❌ | F7 |
| `⏎` paleta de cuartos | ❌ | F7 |
| `⇧P` destacado | ❌ | F7 |
| `F` solo video | ❌ | F7 |
| `P`/`X` que vuelven a neutral | ❌ | F7 |
| `⇥` alternar modo | ❌ | F8 |
| `esc`, doble click, `+`/`−` | ❌ | F8 |
| arrastre de marquesina y pincel | ❌ | F8 |

---

## 6. Las fases, con lo que se les agrega

Orden **sin cambios**; lo que cambia es qué carga cada una. En **negritas**, lo
que este análisis le suma.

- **F4 — Deshacer con historial.** Pila de undo agrupada, historial al pie del
  rail con revertir por fila, `⌘Z` de verdad, **más el indicador `↺ ⌘Z` de la
  columna de herramientas**.
- **F5 — Filtros como cola.** Barra de filtros, `←/→` sobre el conjunto
  filtrado, `3 de 12 en la cola`, chip de cola, aviso clickeable, **más el
  campo «Buscar clip o cuarto…»** (`⌘A` ya se adelantó).
- **F6 — Reproducción rápida.** Autoplay, `1×/2×/4×`, arranque al 25%,
  precarga, `,`/`.`, **más la forma de la barra de reproducción, la pastilla de
  rango, el renglón de teclas, el contador `f 293`, el `espacio ▶ ‖` y el badge
  `▶ auto`**. Es la fase que más creció.
- **F7 — Resto del teclado.** `S`, paleta `⏎`, destacado `⇧P` (badge e
  indicador), `F`, **más que `P`/`X` vuelvan a neutral**.
- **F8 — Modo hoja y pincel.** `⇥`, hoja a pantalla completa, pincel, `+`/`−`,
  marquesina, `esc`, doble click, **más la barrita al escrubear miniaturas, la
  barra de selección múltiple y la portada al 25%**.
- **F9 — Proxies y orientación.** Sin cambios.
- **F10 — Barrido final.** Sin cambios.

**La F6 es ahora la fase más grande del rediseño**, no la F8. Vale la pena
saberlo antes de empezarla, no a mitad.

---

## 7. Lo que este barrido enseñó

- **Disolver una fase dentro de otra pierde cosas.** La vieja F4 se disolvió en
  la F2 y la portada al 25% se cayó por la grieta. Cuando una fase se disuelva:
  listar sus puntos uno por uno y reasignarlos explícitamente, no «la F2 se
  queda con eso».
- **Un mockup tiene elementos sin decisión detrás.** Los iconos de vista se
  habrían construido solo porque están dibujados. El inventario obliga a
  preguntarse *qué hace* cada cosa, no solo *dónde va*.
- **Copiar un texto del mockup puede crear una promesa rota.** El `⌘A` del
  encabezado de grupo entró en la F2.1 junto con la línea separadora. Al copiar
  una etiqueta que nombra un atajo, hay que comprobar que el atajo exista.
- **El inventario por clases CSS funciona y es barato.** Diez minutos de
  `grep`, y encontró nueve huecos que tres lecturas del plan no habían visto.

---

## 8. Un bug encontrado de paso

`MpvPlayer.mark_in` y `mark_out` leían `self._mpv.time_pos` **crudo**, mientras
que `position` y `duration` sí se protegen de que mpv todavía no la reporte —su
propio comentario lo dice: *«0.0 si mpv todavía no lo reporta (recién
abierto)»*—. Apretar `I` apenas abierto un clip tiraba
`TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'`.

Arreglado en el commit `57680a3`, con su test. Apareció al probar a mano el
`⌘A` recién implementado, no en la suite: **es el tipo de cosa que solo sale
usando la app**, aunque sea desde un script.
