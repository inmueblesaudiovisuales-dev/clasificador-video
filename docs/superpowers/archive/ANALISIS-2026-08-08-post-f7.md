# Punto de control post-F7 — 2026-08-08

Rehecho **contra el código de hoy**, no contra lo que el plan suponía en
agosto. Mismo método que los dos anteriores: medir y ejecutar, no leer.

Estado: **647 tests en verde**, árbol limpio. F0 a F7 hechas.

---

## 1. Qué se puede hacer hoy, de punta a punta

Un shooting completo se clasifica sin tocar el mouse:

| Momento | Teclas |
|---|---|
| Ver | llega reproduciendo al 25 %, `espacio`, `L`/`K` velocidad, `,`/`.` cuadro |
| Marcar | `P` `X` `⇧P` (repetir vuelve a neutral), `I` `O` `U` |
| Clasificar | `1`–`9`, `S` (igual al anterior), `⏎` (buscar o crear cuarto) |
| Moverse | `←` `→` por la cola filtrada, `F` solo video, `esc` |
| Corregir | `⌘Z`, o revertir cualquier fila del historial |
| Entregar | `⌘E` |

La tabla de teclado de `DECISIONES.md` está **completa salvo lo de la F8**
(`⇥`, `+`/`−`, el pincel y el doble click). 32 atajos registrados, y hay un
test que exige que **cada tecla dibujada en la interfaz exista de verdad**.

## 2. Lo que falta, con dueño

| Qué falta | Fase |
|---|---|
| Modo hoja a pantalla completa, 7 columnas | F8 |
| Pincel de cuarto (mantener `1`–`9` + arrastrar) | F8 |
| `⇥`, `+`/`−`, doble click, marquesina, barra de selección múltiple | F8 |
| Escrubear una miniatura al pasar el mouse | F8 |
| Badge `Proxy 1080p` y contador `proxies · 128/128` | F9 |
| `orientacion="horizontal"` hardcodeado (`ui/main_window.py:1249`) | F9 |
| Barrido final contra el mockup | F10 |

**La lista de ejecución sigue teniendo un solo renglón vivo**, el mismo desde
la F2: la orientación hardcodeada.

## 3. Los detectores, corridos

| Detector | Resultado |
|---|---|
| Señales declaradas sin conectar | ninguna |
| Métodos nuevos que nadie llama | ninguno |
| Tokens del tema huérfanos | ninguno (`STAR_COLOR` dejó de serlo en la F7) |
| Widgets huérfanos tras 60 teclas | 627 → 620, o sea ninguno |
| Teclas anunciadas que no existen | ninguna |

### Rendimiento, con 128 clips y 5 cuartos

| Acción | Costo |
|---|---|
| Tecla de cuarto (asigna, refresca todo y avanza) | 3.7 ms |
| Tecla `S` | 3.7 ms |
| `⇧P` | 1.7 ms |
| Tick del playhead (10 veces por segundo) | 0.0 ms |
| Abrir la paleta | 0.5 ms |
| Entrar y salir de solo video | 1.1 ms |

Un cuadro a 60 fps son 16.7 ms: todo esto es imperceptible. La tecla de cuarto
subió de 1.6 ms a 3.7 ms en la F6, y es esperado — ahora además abre el clip
siguiente y lo arranca.

## 4. Lo que estas dos fases enseñaron

**Los bugs que quedan a esta altura no se ven en una captura ni los detecta la
suite.** Los cinco de la F6 y los dos de la F7 salieron todos de lo mismo:
usar la app con material real, o medirla en un estado que ningún test montaba.

- **Un doble de pruebas puede tapar el bug que existe.** `frame-step` no
  avanzaba porque el código escribía `pause` después, y el doble no emulaba
  que mpv pausa solo: el test pasaba *por* la línea que rompía el avance.
  Ahora el doble imita a mpv.
- **El orden importa y los arneses lo esconden.** Dos bugs distintos --las
  etiquetas del pie sin re-acomodar, y el choque de la fila de teclas-- eran
  invisibles porque en los arneses siempre hay un `resize` DESPUÉS de poner
  los datos, y ese resize los arreglaba. En la app los datos llegan al final.
- **Un solo ancho de ventana no alcanza.** Todo se había mirado a 1600 px. A
  1150 px --una laptop-- el pie del video se encimaba consigo mismo.
- **La regla global `QWidget { background-color }` alcanza a las QLabel.**
  Dos veces: el pie del video y la columna de estado, que nunca mostró sus
  cuadros desde la F2. Cualquier etiqueta sobre algo pintado tiene que
  declarar `transparent`.
- **Una tecla suelta compite con los campos de texto.** Los atajos de una
  letra se resuelven ANTES de entregarle la tecla a quien tiene el foco.

## 5. Lo que hay que probar a mano antes de la F8

1. **Escribir en el buscador de la hoja** — ✅ probado por Bruno: el texto
   aparece completo y no dispara nada.
2. **Los atajos con modificador** (`⌘Z`, `⌘A`, `⌘E`, `⌘R`) contra el teclado
   físico. Sigue pendiente: un entorno sin ventana activa no los recibe.
3. **`⏎` con una fila del rail enfocada** debe renombrar, no abrir la paleta.
   Está cubierto por tests, pero el choque real depende del foco de verdad.
4. **El indicador «Guardado hace N s»** no se compara nunca: el arnés no
   guarda sesión, así que su texto sale vacío. Solo se ve usando la app.

## 6. Antes de escribir el plan de la F8

La F8 es la fase más grande de las que quedan y **toca la hoja, que es donde
están casi todos los bugs difíciles de este proyecto** (el orden de
`item_widgets`, el re-acomodo, los mínimos que inflan la ventana). Dos cosas
que conviene decidir antes:

- **El pincel arrastra sobre las tarjetas**, y arrastrar dentro de un
  `QGridLayout` re-acomodado a mano es exactamente donde este proyecto ya
  tuvo un SIGSEGV (reconstruir la hoja dentro del `mousePressEvent` de una
  tarjeta). Merece un spike antes que un plan.
- **El modo hoja a pantalla completa esconde el video.** Hoy `_resize_video_stage`
  asume que el video siempre existe; conviene revisar cómo convive con el
  modo solo video de la F7, que ya esconde paneles.
