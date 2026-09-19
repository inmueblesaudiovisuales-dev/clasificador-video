# La guía de edición como tablero, no como texto de la IA — diseño

*(Spec. Fecha: 2026-09-19. Sale de la plática con Bruno del mismo día,
después de revisar el mockup interactivo en
`docs/superpowers/mockups/guia-de-edicion-2026-09-19/mockup.html`, que
quedó aprobado.)*

**Este documento le cambia la mitad de arriba a
`2026-09-14-guia-de-edicion-en-clipify-design.md`** (la pantalla, las dos
preguntas, el resultado en prosa) **y una parte del §4.d y el §5 de
`2026-09-15-el-guion-y-las-carpetas-design.md`** (lo que el panel de
Premiere enseña). Lo que ninguno de los tres pierde queda listado en el
§9.

## 1. De dónde salió

Bruno vio el mockup y pidió dos cosas: poder mover el orden de los
cuartos a mano, y evaluar si la parte de IA seguía aportando algo. De ahí
salió, en una plática de preguntas cortas, que la IA se quede solo para
lo que hace barato y bien —ubicar cada cuarto en su momento del
recorrido— y que el resto (el orden final, los repetidos, las razones en
prosa) lo decida Bruno arrastrando.

## 2. Lo que se va

- **Las preguntas «¿qué quieres lucir?» y «¿qué tipo de propiedad es?»**
  Ya no hay a quién dárselas: el tablero no genera prosa que necesite ese
  contexto.
- **El párrafo de «cómo recorrerla».** No hay quien lo escriba: nadie le
  pide a la IA un texto libre.
- **El «por qué» de cada paso y la marca «fuera del patrón».** Eran la
  explicación de una decisión que tomaba la IA; ahora la decisión la toma
  Bruno arrastrando, y no necesita que se la expliquen.
- **La revisión de «te falta un cuarto / te sobra uno inventado»**
  (`guia.revisar_lista`, `guia.avisos_de_la_revision`). Ya no puede sobrar
  un cuarto inventado —la IA solo clasifica los que Bruno tecleó, nunca
  agrega uno— y «te falta uno» se contesta distinto (§5).

## 3. Lo que se queda

- El botón **«Guía de edición»** junto al de exportar, en el mismo lugar.
- Que la guía se arma en Clipify y **viaja congelada** en el manifest; el
  panel de Premiere sigue sin llave, sin red, sin preguntar nada.
- **«Usar este orden» sigue siendo la única forma de que el orden mande**
  en el rail, la hoja y Premiere — y sigue emitiendo la misma señal de
  siempre, una lista plana de nombres de cuarto en orden, con repetidos.
  Todo lo que hace `main_window.aceptar_orden_de_la_guia` con esa señal
  **no cambia ni una línea**.
- El aviso de «tu guía quedó vieja» al exportar, si los cuartos
  cambiaron desde que se armó.
- Que un manifest sin guía sea válido.
- Que las carpetas lleguen numeradas por la primera aparición del cuarto,
  y que un cuarto pueda repetirse en el guion (spec del 15 de
  septiembre): eso vive en cómo se usa la lista final, no en cómo se
  arma, así que no lo toca este documento.

## 4. El tablero

**Siete columnas fijas**, en este orden, sacadas de
`docs/patron-de-recorrido/MI-PATRON.md`:

| id             | Título               | Lo que entra ahí (pista para la IA) |
|----------------|-----------------------|--------------------------------------|
| `apertura`     | Apertura / fachada    | la fachada o la aérea de entrada |
| `sociales`     | Áreas sociales        | cocina, sala, comedor, terraza |
| `habitaciones` | Habitaciones          | recámaras, baños, vestidor |
| `aerea_media`  | Aérea a media casa    | una aérea para respirar antes de salir |
| `amenidades`   | Amenidades            | alberca, roof, amenidades en general |
| `area_general` | Área general          | la propiedad completa, de lejos |
| `aerea_final`  | Aérea final           | la última toma, de salida |

Estas siete columnas son fijas siempre — no cambian con el tipo de
propiedad (esa pregunta ya se fue, §2). Un rodaje sin habitaciones (un
terreno) simplemente deja esa columna vacía; nada obliga a llenarlas
todas.

**Abajo, una franja con todos los cuartos reales de la sesión, siempre
disponible.** No es un origen que se vacía: arrastrar un cuarto a una
columna dibuja un paso ahí, y el cuarto se puede volver a arrastrar las
veces que haga falta —así se resuelve la aérea que abre y cierra sin
necesitar un botón de «repetir». La franja nunca se llena con nada que
Bruno no haya tecleado: **es la garantía de que nunca se invente un
cuarto que no exista** (la recámara de más que preocupaba a Bruno no
puede pasar, porque no hay de dónde arrastrarla).

Dentro de una columna, los pasos se pueden subir o bajar. Entre columnas,
se pueden mover. Cada paso puesto tiene una forma de quitarlo (una ✕),
que lo regresa a estar solo-en-la-franja.

## 5. Lo que hace la IA, y solo eso

Al abrir la pantalla (si no hay ya una guía armada esta sesión), se le
pide al modelo **una sola cosa: en qué columna cae cada cuarto**. Nada de
párrafo, nada de razón por escrito. El pedido es barato — nombres de
cuartos entrando, un id de columna por cada uno saliendo — y sigue usando
`deepseek-chat` (el de conversación, no el de razonamiento), mismo
criterio que ya estaba.

**Si falla o no hay red**: las siete columnas empiezan vacías, se dice en
la franja de avisos «no se pudo clasificar, acomódalos tú», y Bruno
arrastra a mano. No bloquea nada — mismo trato que ya tenía un fallo de
red en el spec del 14.

**Si la respuesta viene rara** (un cuarto que no es de los reales, una
columna que no es una de las siete, el mismo cuarto clasificado dos
veces): ese renglón se ignora entero. El cuarto afectado simplemente no
sale ya puesto en ninguna columna al abrir — sigue en la franja, Bruno lo
arrastra él mismo. **Nunca se inventa** un cuarto ni una columna que no
sea una de las siete.

Hay un botón **«Clasificar de nuevo»** (reemplaza al viejo «Armar la
guía») para pedir otra vez —si Bruno agregó cuartos después, o si
prefiere empezar de cero—. Vuelve a armar el tablero desde cero: lo que
ya había arrastrado a mano se pierde, y eso se dice antes de hacerlo (un
confirmar simple, como ya hacen otras acciones que tiran trabajo hecho).

## 6. El aviso de «sin usar»

Si algún cuarto real nunca se arrastró a ninguna columna, arriba se dice:
*«Sin usar: Roof garden.»* — igual que hoy avisa un cuarto que falta.
**No bloquea «Usar este orden»**: se avisa, no se decide solo, mismo
principio que ya usa el diálogo de proxies. Se recalcula solo después de
cada arrastre.

## 7. «Usar este orden»

Aprieta y hace lo mismo de siempre: junta los pasos de las siete columnas
**en su orden fijo**, cada columna en el orden en que Bruno la dejó, y
esa lista plana —con repetidos, si los hay— es la que se manda por
`orden_aceptado`. De ahí para adelante, nada cambia: reacomoda el rail y
la hoja, guarda la guía en la sesión, la pantalla se cierra sola.

## 8. Lo que cambia por debajo (para quien escriba el plan)

### 8.a `guia.py` — la parte que piensa

- `Renglon` pierde `porque` y `fuera_del_patron`; se queda solo con
  `cuarto: str`. Todo lo que en `main_window.py` ya lee `r.cuarto` sigue
  funcionando igual.
- `Respuesta` pierde `recorrido`; se queda `ok`, `lista: list[Renglon]`,
  `error`.
- `prompt_de_sistema`/`cuerpo_del_request` se reescriben para pedir
  clasificación (cuarto → id de columna) en vez de un guion completo. Ya
  no reciben `respuestas` (las preguntas se fueron) ni `patron` como
  prosa completa — las pistas de la tabla del §4 van fijas en el prompt.
- `leer_respuesta` valida contra las **siete columnas fijas** (constante
  nueva, ver §4) en vez de contra «cualquier texto»; un cuarto no
  reconocido, una columna no reconocida, o un cuarto repetido en la
  respuesta se descarta (se queda la primera aparición, se ignoran las
  demás).
- `revisar_lista` y `avisos_de_la_revision` se borran enteros (§2). Se
  agrega una función nueva y chica, sin Qt: `cuartos_sin_usar(reales,
  pasos) -> list[str]`, la resta simple para el aviso del §6.
- `COLUMNAS` — la lista fija de `(id, título, pista)`, en el orden del
  §4 — vive aquí, no en la UI: es dato de dominio, no de dibujo.

### 8.b `pantalla_guia.py` — el tablero

Deja de ser «dos preguntas y un resultado en texto» y pasa a ser el
tablero: siete columnas con sus chips, la franja de abajo, el aviso de
sin-usar arriba. Las señales que ya usa `main_window.py` se conservan
tal cual pueden:

- `orden_aceptado = Signal(list)` — **sin cambios**, sigue siendo la
  lista plana de nombres.
- `cerrada = Signal()` — sin cambios.
- `guia_pedida = Signal(dict)` se reemplaza por `clasificacion_pedida =
  Signal()` (sin payload: ya no hay respuestas de preguntas que mandar).

### 8.c `manifest.py`

- `RenglonDeGuia` se borra: `Guia.orden` pasa a ser `list[str]` a secas.
- `Guia.recorrido` se borra.
- `Guia.to_dict()` queda `{"orden": [...]}`.

### 8.d `main_window.py`

Los métodos que ya orquestan la guía (`_guia_cuadrada_con_el_rail`,
`restaurar_guia`, `guia_quedo_vieja`, `aviso_de_guia_vieja`,
`_guia_para_el_manifest`, `aceptar_orden_de_la_guia`) se ajustan a los
campos que se fueron (`recorrido`, `porque`, `fuera_del_patron`) pero
**su lógica no cambia**: siguen comparando cuartos por nombre, siguen
completando lo que el guion no menciona al final, siguen guardando
`cuartos_de_entonces`. `pedir_guia` se renombra a algo como
`pedir_clasificacion` y deja de armar `respuestas`/pasarle `patron.leer()`
— ya no hace falta el texto del patrón completo, solo las pistas fijas
que ya viven en `guia.COLUMNAS`.

### 8.e El panel de Premiere (`uxp-plugin/js/`)

Hoy enseña el párrafo y, por cada paso, la razón en cursiva (marcada
distinto si `fuera_del_patron`). Con esos dos campos fuera del manifest,
el panel se achica a lo que described el spec del 15 de septiembre en su
§4.d **menos el párrafo y las razones**: encabezado fijo (paso actual,
cuántos llevas, de qué rodaje), y la lista de pasos numerada con
«(otra vez)» en el que se repite — esa marca **no se toca**, ya se
calcula sola contando nombres repetidos en `orden`, sin que el dato
viniera de la IA.

Un manifest VIEJO (con `recorrido` y `porque`) sigue abriendo sin
tronar: son campos que ya no se leen, no que hagan falta.

## 9. Lo que NO pierde ninguno de los dos specs anteriores

- Que la guía se congele y viaje en el manifest; el panel no la pide de
  nuevo.
- Los seis tipos de propiedad — **se van** (§2), esto lo repite para que
  quede explícito: es un cambio respecto al spec del 14, no un olvido.
- Que las carpetas lleguen numeradas por la primera aparición.
- Que un paso pueda repetir cuarto, y que eso no sea un error.
- Que la palomita de avance en Premiere viva en el plugin y el bin se
  pinte verde al completarse (spec del 15) — nada de esto lo toca este
  documento.

## 10. Lo que NO entra

- **Un botón «Reconectar» o similar para el tablero** — no aplica aquí.
- **Que la IA sugiera repetidos.** Ya no genera un guion, solo clasifica;
  repetir es una decisión de Bruno, arrastrando.
- **Guardar el tablero por columnas en el manifest.** Lo que viaja es la
  lista plana ya aceptada (§7) — las columnas son un paso de trabajo en
  Clipify, no un dato que le sirva a Premiere.
- **Reabrir con el tablero reconstruido a partir de una guía YA
  aceptada.** Si Bruno reabre la pantalla después de haber apretado
  «Usar este orden», se le arma un tablero **nuevo** (clasificación
  fresca), no una reconstrucción de por dónde había dejado cada cuarto.
  Es una llamada barata y evita inventar a qué columna pertenecía cada
  paso de una lista que ya se aplanó.
- **Compatibilidad hacia atrás para leer `recorrido`/`porque` en
  Clipify.** El panel de Premiere los tolera sin tronar (§8.e) porque son
  JavaScript leyendo un campo que puede faltar; Clipify no necesita
  ninguna lógica especial para un manifest viejo, porque nunca vuelve a
  leer sus propios manifiestos exportados.

## 11. Cómo se comprueba

**Con pruebas de Python**, en `tests/test_guia.py`:

- Que `leer_respuesta` acepte una clasificación válida y arme la lista de
  `Renglon` en el orden de las columnas.
- Que un cuarto no real, una columna no reconocida, o un cuarto repetido
  en la respuesta del modelo se ignoren (se quede la primera aparición).
- Que `cuartos_sin_usar` devuelva los reales que no aparecen en la lista
  de pasos, y `[]` cuando todos aparecen.
- Que el prompt nuevo NO pida prosa ni mencione «lucir» ni «tipo de
  propiedad».

**Con pruebas de la ventana**, en `tests/ui/test_pantalla_guia.py` y
`tests/ui/test_main_window.py`:

- Que `orden_aceptado` siga emitiendo una lista plana de nombres, con
  repetidos, tal como la espera `aceptar_orden_de_la_guia`.
- Que un manifest viejo con `RenglonDeGuia`/`recorrido` ya no se escriba
  (el nuevo `Guia.to_dict()` no los tiene).
- Que restaurar una guía guardada con el esquema nuevo funcione, y que
  una guía con el esquema viejo (de una sesión sin cerrar entre
  versiones) no tumbe la app al abrir —se trata como guía inválida,
  mismo criterio que ya usa `restaurar_guia` para un documento roto.

**Con pruebas de `node`**, en `uxp-plugin/pruebas/`:

- Que el panel arme la lista de pasos sin un `recorrido` en el manifest.
- Que un paso sin `porque` no rompa el render (simplemente no hay nada
  que mostrar ahí).
- Que «(otra vez)» se siga marcando en el paso que repite cuarto.

**Verificación visual real** — si no se miró la imagen, no se afirma:

- El tablero recién clasificado, con las siete columnas y la franja.
- Un cuarto arrastrado dos veces, con el aviso de «sin usar» mostrando
  otro cuarto sin tocar.
- El panel de Premiere con un guion que repite, sin párrafo ni razones.

## 12. El riesgo que queda

**Que Bruno arrastre mucho y luego apriete «Clasificar de nuevo» por
accidente**, perdiendo el acomodo a mano. Se cubre con una confirmación
simple antes de rehacer el tablero (§5) — no es una ventana nueva que
diseñar, es el mismo patrón de confirmar que ya usan otras acciones que
tiran trabajo (por ejemplo, quitar un bin).
