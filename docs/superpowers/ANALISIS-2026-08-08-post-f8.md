# Punto de control post-F8 — 2026-08-08

Rehecho **contra el código de hoy**, midiendo y ejecutando. Estado: **697
tests en verde**, árbol limpio, F0 a F8 hechas.

---

## 1. Lo que encontró este punto de control

**La marquesina de selección no está construida, y yo la di por hecha dos
veces.** El análisis post-F7 la puso en la lista de la F8; al escribir el plan
de la F8 no quedó como tarea, y nadie lo notó. Peor: un comentario del pincel
afirmaba que «sin tecla, arrastrar sigue siendo marquesina», que era
directamente falso — arrastrar sin tecla hoy no hace nada. Ese comentario ya
está corregido.

Es exactamente el tipo de cosa para la que existe este punto de control: **el
plan de una fase puede recortar el alcance en silencio**, y el único momento
en que eso se ve es al comparar la fase contra lo que se prometió, no contra
su propio plan.

`⇧`+click y `⌘A` sí existen, así que la selección múltiple funciona — pero le
falta el gesto que `DECISIONES.md` menciona primero.

## 2. Qué se puede hacer hoy

El shooting completo, sin mouse y con dos vistas:

| Vista | Qué |
|---|---|
| **Clip** | video grande, autoplay al 25 %, `J K L`, `,`/`.`, in/out con manijas |
| **Hoja** (`⇥`) | siete columnas, `+`/`−`, escrubear con el mouse, doble click para abrir |

Y para clasificar: `1`–`9`, `S`, la paleta `⏎`, `P`/`X`/`⇧P`, el **pincel**
(mantener `1`–`9` y arrastrar), `⌘Z`, y filtros que son la cola de navegación.

**26 atajos registrados y ninguna tecla de la tabla de `DECISIONES.md` sin
construir**, salvo el arrastre de selección. Los dígitos van por evento de
teclado y no como atajo, a propósito: un atajo consume la tecla y nunca avisa
de que se soltó, y sin eso el pincel no se arma.

## 3. Los detectores, corridos

| Detector | Resultado |
|---|---|
| Señales declaradas sin conectar | ninguna |
| Tokens del tema huérfanos | ninguno |
| Widgets huérfanos tras 60 teclas | 695 → 681, o sea ninguno |
| Teclas anunciadas que no existen | ninguna |

### Rendimiento, con 128 clips

| Acción | Costo | Nota |
|---|---|---|
| Tecla de cuarto | **4.2 ms** | venía de 9.35 ms; ver abajo |
| Pincel, por movimiento del mouse | **0.01 ms** | el presupuesto era 16.7 |
| Entrar o salir del modo hoja | 30 ms | una vez, no por tecla |
| `+` / `−` | 18 ms | una vez |

**La regresión que este cierre encontró**: la tecla de cuarto se había ido de
3.7 a 9.35 ms. cProfile —otra vez— mostró que el 40 % se iba **reescalando
miniaturas idénticas**: re-colocar la grilla llama a `apply_width` en las 128
tarjetas, y sin guarda cada una tiraba su caché. Con la guarda, 4.2 ms.

Es la tercera vez que cProfile encuentra trabajo desperdiciado que nadie
sospechaba (38 ms por tecla en la F5, el `setStyleSheet` en la F5, esto).
**Vale correrlo en cada cierre de fase, no solo cuando algo se siente lento.**

## 4. Lo que falta

| Qué | Fase |
|---|---|
| **Marquesina de selección** (arrastrar sin tecla) | **sin asignar — ver §1** |
| Badge `Proxy 1080p` y contador `proxies · 128/128` | F9 |
| `orientacion="horizontal"` hardcodeado (`ui/main_window.py:1430`) | F9 |
| Selector `Clip │ Hoja` de la barra de título | F10 |
| Transición animada de la tarjeta al visor | F10 |
| Barrido final contra el mockup | F10 |

La lista de ejecución **sigue con un solo renglón vivo**, el mismo desde la
F2: la orientación hardcodeada.

## 5. Lo que enseñó esta fase

- **Un spike puede validar la idea y además medir la decisión.** El del pincel
  no solo dijo «se puede»: midió que reagrupar durante el arrastre mueve la
  tarjeta bajo el cursor, y con eso el detalle 5 de `DECISIONES.md` dejó de
  ser una preferencia de diseño para ser la diferencia entre un gesto que hace
  lo que ves y uno que no.
- **Un atajo de teclado consume la tecla y nunca avisa de que se soltó.** Con
  los dígitos registrados como `QShortcut`, el pincel no se habría armado
  nunca en la app real — y los tests habrían seguido en verde, porque un
  atajo solo se dispara con la ventana activa y en pruebas la tecla llega
  igual al widget. Segunda vez que este mecanismo esconde un bug.
- **Dos lugares calculando lo mismo se separan solos.** `columnas_visibles()`
  y el acomodo real estuvieron un rato dando números distintos. Van cinco
  veces en este proyecto; el patrón siempre es el mismo y el arreglo también:
  una sola función, y la otra vista la llama.
- **Medir en la ventana, no en el widget suelto.** El paso de zoom de la hoja
  se eligió midiendo con 1382 px —el ancho real, con el rail puesto— y no con
  1600. El ancho de la hoja nunca es el de la ventana.

## 6. Antes de la F9

Es la fase más corta que queda y no toca la interfaz: son datos. Dos cosas:

- **`probe.py` ya extrae `width`/`height`/`rotation`**, y la ventana los
  guarda en `_clip_sizes`. Lo que falta es que la orientación del manifest
  salga de ahí en vez de estar escrita a mano.
- **`match_proxies()` existe y nadie la llama.** Conectarla a la importación
  es lo que hace que el badge y el contador digan algo real, en vez de un
  número inventado.
