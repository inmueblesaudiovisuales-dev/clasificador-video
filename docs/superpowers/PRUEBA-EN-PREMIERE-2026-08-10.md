# La corrida dentro de Premiere: el LUT y la estrella dorada

*(2026-08-10. Documento de una sola corrida: cuando las dos preguntas estén
contestadas, esto se archiva y el spike se borra.)*

## Por qué hace falta correr algo en vez de escribir código

Quedan dos preguntas abiertas que **no se pueden contestar desde el repo**,
porque la respuesta la tiene Premiere y no la documentación:

1. **El LUT.** La API de UXP sí deja colgarle efectos al *master clip* sin
   armar secuencia (`ClipProjectItem.getComponentChain`, confirmado en la
   referencia de Adobe). Lo que **no** dice ninguna documentación es el
   `matchName` de Lumetri en esta versión, cómo se llama su parámetro de LUT
   de entrada, ni si ese parámetro acepta la ruta de un `.cube`. Si no
   acepta, todo el plan del LUT por bin cambia — y ese descubrimiento es
   barato ahora y caro después.
2. **La estrella dorada.** `destacado → MANGO` ya está escrito, con una
   guarda que avisa si esa versión de Premiere no conoce el color. Falta
   confirmar que `MANGO` existe de verdad.

Las dos se contestan en **una sola corrida**.

## Qué se preparó

- `uxp-plugin/js/spike-lut.js` — el spike. Prueba cinco `matchName` posibles
  de Lumetri, le cuelga el que funcione al master clip, **enumera todos sus
  parámetros con su nombre visible** y, si hay ruta de LUT configurada,
  intenta escribirla y volver a leerla. Es defensivo a propósito: en cada
  paso, si algo no existe, reporta qué sí existe en vez de caerse.
- `uxp-plugin/js/autocheck.js` — el arnés se volvió a encender
  (`AUTOCHECK_ACTIVO = true`) y se le agregó `AUTOCHECK_SOLO`, que filtra
  qué pruebas corren. Está en `["spike:", "MANGO"]`: corren las dos del
  spike y la de la estrella, y **no** las ~40 restantes. Correrlas todas
  dejaría bins de basura por todo el proyecto, y una de ellas necesita una
  carpeta de segunda tarjeta que hay que armar a mano y que el repo no trae
  — o sea que fallaría por algo que no tiene nada que ver con lo que se está
  preguntando.

## Cómo se instaló esta vez (y por qué no fue con el `.ccx`)

El camino documentado en `uxp-plugin/README.md` —empaquetar `.ccx` con el
CLI de UXP e instalarlo con UPIA— **no se pudo usar hoy**: el CLI vive en
`/tmp`, que macOS limpia, y al reinstalarlo su biblioteca nativa no tiene
compilado para Node 24 (`No native build was found for ... abi=137`). Eso es
un problema del CLI de Adobe, no del plugin.

Se usó otra vía, válida en este caso concreto: **copiar los archivos encima
de la instalación que ya existe**, en
`~/Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1.0.0/`.

Ojo con la distinción, porque el README dice que copiar a mano ahí **no
funciona** — y sigue siendo cierto **para instalar por primera vez**:
Premiere nunca registra un plugin que aparece solo en esa carpeta. Aquí el
plugin ya estaba registrado por UPIA desde agosto; lo único que cambió son
los archivos que lee al cargar. Para distribuir sigue haciendo falta el
`.ccx`.

El estado anterior quedó respaldado en el scratchpad de la sesión antes de
copiar.

**Para correrlo:** abrir Premiere **con un proyecto nuevo y vacío** —el
spike crea bins de prueba, no conviene encima de un proyecto de trabajo— y
abrir el panel en `Window > UXP Plugins > Clasificador de Video`. El spike
corre solo al cargarse y va escribiendo en el panel.

El LUT ya está apuntado al de S-Log de Bruno
(`luts/2_SGamut3CineSLog3_To_LC-709TypeA.cube`), así que la prueba llega
hasta el final: escribe la ruta en el parámetro y la vuelve a leer.

## Dónde queda el resultado

En `/private/tmp/clasificador-autocheck/resultado.json` (la carpeta ya está
creada). Cada prueba deja `ok` y un `detalle` largo con los nombres reales
que encontró.

## Qué significa cada resultado

| Lo que dice | Qué quiere decir |
|---|---|
| `spike: con que matchName se crea Lumetri` → **ok** | Se puede crear el efecto. El detalle trae el nombre exacto, que es lo que se usa para escribir la función de verdad. |
| → **falla** con "ningún matchName funcionó" | El detalle lista qué error dio cada intento. Con eso se prueban otros nombres. |
| `spike: parametros de Lumetri...` → **ok** sin ruta de LUT | Lumetri se cuelga del master clip y **hay** un parámetro de LUT. El detalle trae en qué índice está y cómo se llama. Falta la mitad de aplicarlo. |
| → **ok** con ruta de LUT | La respuesta completa: se escribió la ruta y al releerla quedó puesta. El LUT por bin es escribible. |
| → **falla** con "NINGÚN parámetro menciona LUT" | Es la mala noticia útil: el LUT de entrada no se ve desde la API y hay que buscar otra vía (preset de efecto, `.prfpset`, o hacerlo en la secuencia). El detalle trae la lista completa de parámetros para decidir. |
| `applyFlagLabel: 'destacado' pone el label MANGO` → **ok** | La estrella queda dorada en Premiere. Tema cerrado. |
| → **falla** con "MANGO no existe en esta version" | El detalle lista los colores que sí existen y se elige otro con Bruno. |

## Cuando termine

1. Pegar el `resultado.json` (o su resumen) para escribir la conclusión en el
   handoff.
2. Borrar `uxp-plugin/js/spike-lut.js` y su `<script>` de `index.html`.
3. Volver a poner `AUTOCHECK_ACTIVO = false`.
4. Archivar este documento.
