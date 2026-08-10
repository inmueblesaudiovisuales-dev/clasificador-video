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

## Cómo correrlo

**1. Opcional pero recomendado: apunta el spike a un `.cube` tuyo.**

En `uxp-plugin/js/spike-lut.js`, primera constante:

```js
const RUTA_LUT = "/ruta/a/tu/lut.cube";
```

Si la dejas vacía el spike igual sirve — enumera los parámetros de Lumetri,
que es la mitad importante. Lo único que no hace es intentar aplicarlo.

**2. Arranca el servicio de UXP** (una vez por sesión de terminal):

```bash
arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js service start
```

**3. Empaqueta el plugin:**

```bash
cd "uxp-plugin/" && arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js plugin package --outputPath /tmp/uxp-package-output
```

**4. Quita la versión instalada y pon la nueva.** El `--install` encima de
una instalación existente es un no-op: UPIA ve el mismo id y la misma
versión y no reextrae nada, aunque el `.ccx` haya cambiado.

```bash
"/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent" --remove "Clasificador de Video IAV"
```

```bash
"/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent" --install /tmp/uxp-package-output/com.iav.clasificadorvideo_premierepro.ccx
```

**5. Abre Premiere con un proyecto nuevo y vacío** — el spike crea bins de
prueba, así que no lo corras encima de un proyecto de trabajo.

**6. Abre el panel:** `Window > UXP Plugins > Clasificador de Video`. El
spike corre solo al cargarse y va escribiendo en el panel.

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
