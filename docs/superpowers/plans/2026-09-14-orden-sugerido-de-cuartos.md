# Orden sugerido de los cuartos — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Una pestaña «Orden sugerido» en el panel de Clipify dentro de Premiere, que lee los cuartos de `02. Clip`, platica con DeepSeek y propone el recorrido del video — sin tocar el proyecto.

**Architecture:** Todo lo que **piensa** (armar el cuerpo del request, leer la respuesta, revisarla contra los cuartos reales) vive en `ordenSugerido.js`, que no hace `require("premierepro")` ni toca la red: son funciones de cadenas y se prueban con `node` desde el repo. Lo que **habla con el mundo** —la red, los bins, el archivo de la llave— vive aparte en `deepseek.js`, `cuartosDelProyecto.js` y `llave.js`, cada uno chiquito y comprobado en vivo. El panel gana pestañas: la de hoy y la nueva.

**Tech Stack:** UXP (Premiere ≥ 25.1), JavaScript sin build ni bundler — el plugin carga scripts con `<script src>` y todo vive en el ámbito global. Pruebas de lógica pura con `node` (sin dependencias). Pruebas contra Premiere con el arnés de `autocheck.js`.

**Spec:** `docs/superpowers/specs/2026-09-14-orden-sugerido-de-cuartos-design.md`

**Handoff del brainstorm:** `docs/superpowers/HANDOFF-2026-09-14-orden-sugerido-de-cuartos.md`

---

## La Task 1 es una compuerta, no un paso

El §8 del spec: **si Premiere no deja al plugin hablar por internet, este
diseño se va a la basura y hay que avisarle a Bruno antes de gastar el
presupuesto en lo demás.** Bruno ya lo sabe y lo aceptó.

Así que la Task 1 no se salta, no se hace «en paralelo mientras tanto», y no
se da por buena leyendo la documentación de Adobe. Se corre contra Premiere de
verdad y se anota el resultado. Las Tasks 2 y 3 son lógica pura y podrían
escribirse antes sin riesgo, pero **nada que dependa de la red se construye
hasta que la Task 1 esté en verde.**

---

## Estructura de archivos

| Archivo | Qué es |
|---|---|
| `uxp-plugin/manifest.json` | Permiso de red hacia `api.deepseek.com` |
| `uxp-plugin/js/ordenSugerido.js` | **Lógica pura**: arma el cuerpo, lee la respuesta, la revisa |
| `uxp-plugin/js/deepseek.js` | La llamada a la API, y nada más |
| `uxp-plugin/js/llave.js` | Guardar / leer / tapar la llave |
| `uxp-plugin/js/cuartosDelProyecto.js` | Leer los cuartos de `02. Clip` |
| `uxp-plugin/js/pestanaOrden.js` | La pestaña: preguntas, chips, lista, avisos, copiar |
| `uxp-plugin/index.html` | Las dos pestañas + el encabezado que dice Clipify |
| `uxp-plugin/pruebas/correr.js` | Corredor de Node para la lógica pura |
| `uxp-plugin/pruebas/ordenSugerido.pruebas.js` | Los casos |
| `uxp-plugin/js/autocheck-tests.js` | Lo que sí necesita Premiere |

**Nombres que se usan en todo el plan:**

- `cuerpoDelRequest(cuartos, respuestas, conversacion) -> object`
- `leerRespuesta(texto) -> {ok, lista, error}` — `lista` es `[{cuarto, porque}]`
- `revisarLista(lista, cuartosReales) -> {faltan: string[], inventados: string[]}`
- `cuartosDeLosBins(project) -> Promise<string[]>`
- `guardarLlave(llave)` / `leerLlave()` / `llaveTapada(llave)`
- `pedirOrden(llave, cuerpo) -> Promise<string>`

---

### Task 1: ¿Premiere deja al plugin hablar por internet? (COMPUERTA)

**Files:** `uxp-plugin/manifest.json`, `uxp-plugin/js/autocheck-tests.js`, `uxp-plugin/js/autocheck.js`

Esta task no lleva pruebas que fallen primero: **es** la prueba. Lo que se
comprueba es si la plataforma soporta algo, y eso no se decide escribiendo
código sino corriéndolo.

- [ ] **Step 1: Declarar el permiso de red**

En `manifest.json`, junto a `localFileSystem`:

```json
  "requiredPermissions": {
    "localFileSystem": "fullAccess",
    "network": {
      "domains": ["https://api.deepseek.com"]
    }
  }
```

Un solo dominio y con `https://`. No `["all"]`: el plugin tiene permiso de
lectura total al disco, y un plugin que puede leer todo **y** hablar con
cualquiera es una combinación que no hace falta tener.

- [ ] **Step 2: Averiguar qué existe de verdad, sin creerle a nadie**

En `autocheck-tests.js`, una prueba que **primero enumera y luego llama**:

```js
// El riesgo que decide si este diseño vive aquí o se muda a Clipify (§8 del
// spec). Se enumera ANTES de llamar porque en este plugin la documentación de
// Adobe ya mintió tres veces el mismo día: la fábrica de efectos devolvió un
// objeto sin métodos, `getParam` necesitaba `await` aunque la referencia
// dijera que no, y un nombre de parámetro era propiedad y no método.
registrarPrueba("¿UXP deja llamar a api.deepseek.com?", async () => {
  const hayFetch = typeof fetch === "function";
  const globales = Object.getOwnPropertyNames(globalThis)
    .filter((n) => /fetch|XMLHttp|Request|Headers|Response/i.test(n));

  if (!hayFetch) {
    return { ok: false, detalle: "no hay fetch. Globales parecidas: " + globales.join(", ") };
  }

  // La llamada más barata que prueba el camino completo: red + TLS + que el
  // permiso del manifiesto sirva. Con una llave inválida a propósito: un 401
  // que LLEGA ya contestó la pregunta -- salió de la computadora y volvió.
  try {
    const r = await fetch("https://api.deepseek.com/v1/models", {
      headers: { Authorization: "Bearer llave-invalida-a-proposito" },
    });
    return {
      ok: true,
      detalle: "la llamada salió y volvió con HTTP " + r.status +
               " (401 es éxito aquí: significa que llegó). Globales: " + globales.join(", "),
    };
  } catch (e) {
    return { ok: false, detalle: "fetch existe pero tronó: " + e.message + " | " + e.stack };
  }
});
```

- [ ] **Step 3: Correrla contra Premiere de verdad**

Prende el arnés (`AUTOCHECK_ACTIVO = true` en `autocheck.js`), recarga el
plugin en Premiere, y lee el resultado:

```bash
cat /private/tmp/clasificador-autocheck/resultado.json
```

Cada corrida cuesta reiniciar Premiere, así que **anota a disco antes de cada
paso**: esa regla la pagó la sesión del LUT con dos caídas.

- [ ] **Step 4: El desenlace, y hay dos**

**Si salió bien** → apaga el arnés otra vez (`AUTOCHECK_ACTIVO = false`),
anota el resultado en `docs/superpowers/archive/RESULTADO-2026-09-14-red-desde-uxp.md`
con el número de HTTP que volvió y qué globales existen, y sigue a la Task 2.

**Si no se puede** → **párate aquí.** No sigas con las demás tasks. Escribe el
resultado con lo que se intentó y lo que dijo el error, y avísale a Bruno: el
diseño tendría que mudarse a Clipify, que es la opción que él descartó por
gusto y no por imposibilidad, y esa es una decisión suya y no nuestra.

- [ ] **Step 5: Commit**

```bash
git add uxp-plugin/manifest.json uxp-plugin/js/autocheck-tests.js uxp-plugin/js/autocheck.js docs/superpowers/archive/
git commit -m "Comprobar que el plugin puede hablar con la API desde Premiere

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: El corredor de pruebas de Node

**Files:** `uxp-plugin/pruebas/correr.js`, `uxp-plugin/pruebas/ordenSugerido.pruebas.js`

El plugin carga sus scripts con `<script src>` y todo vive en el ámbito
global: no hay `module.exports` en ningún archivo y no se le van a agregar,
porque eso es para el bundler que este plugin no tiene. El corredor lee el
archivo y lo evalúa en un contexto, que es lo mismo que hace el navegador.

- [ ] **Step 1: El corredor**

```js
// Corre la logica pura del plugin desde el repo, sin Premiere y sin
// dependencias:  node uxp-plugin/pruebas/correr.js
//
// Los archivos del plugin no exportan nada --se cargan con <script src> y
// viven en el ambito global-- asi que aqui se leen y se evaluan en un
// contexto, que es lo mismo que hace el navegador. Sin build, sin npm.
//
// Por que esto y no el arnes de `autocheck.js`: el arnes corre DENTRO de
// Premiere y esta apagado (`AUTOCHECK_ACTIVO = false`), asi que hoy sus doce
// casos de las marcas del nombre no corren nunca. Una comprobacion que solo
// corre cuando te acuerdas de prenderla no es una comprobacion. Lo que SI
// necesita Premiere se queda alla; esto es para lo que no.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const raiz = path.join(__dirname, "..");
const contexto = vm.createContext({ console });

for (const archivo of ["js/ordenSugerido.js"]) {
  vm.runInContext(fs.readFileSync(path.join(raiz, archivo), "utf8"), contexto, {
    filename: archivo,
  });
}

const casos = require("./ordenSugerido.pruebas.js")(contexto);

let fallidas = 0;
for (const { nombre, fn } of casos) {
  let ok, detalle;
  try {
    ({ ok, detalle } = fn());
  } catch (e) {
    ok = false;
    detalle = e.message;
  }
  if (!ok) fallidas++;
  console.log((ok ? "OK   " : "FALLO") + "  " + nombre + (ok ? "" : "  — " + detalle));
}

console.log("\n" + casos.length + " pruebas, " + fallidas + " fallidas");
process.exit(fallidas ? 1 : 0);
```

- [ ] **Step 2: El archivo de casos, todavía vacío**

```js
// Los casos de la logica pura. Reciben el contexto donde ya se evaluaron los
// archivos del plugin, y devuelven una lista de { nombre, fn }.
module.exports = function (ctx) {
  return [];
};
```

- [ ] **Step 3: Comprobar que el corredor corre**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: `Error: Cannot find module .../js/ordenSugerido.js` — el corredor
funciona y el archivo que falta es el de la Task 3. Eso es lo que se espera
aquí, no un error a arreglar.

- [ ] **Step 4: Commit**

```bash
git add uxp-plugin/pruebas/
git commit -m "Corredor de pruebas de la logica pura del plugin, sin Premiere

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Leer la respuesta y revisarla — la regla del §6

**Files:** `uxp-plugin/js/ordenSugerido.js`, `uxp-plugin/pruebas/ordenSugerido.pruebas.js`

Esta es la task que importa. Todo lo demás es plomería.

- [ ] **Step 1: Escribe los casos que fallan**

En `ordenSugerido.pruebas.js`, dentro del `return [...]`:

```js
    {
      nombre: "una lista que cuadra no tiene nada que marcar",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Fachada", porque: "…" }, { cuarto: "Sala", porque: "…" }],
          ["Sala", "Fachada"]
        );
        return {
          ok: r.faltan.length === 0 && r.inventados.length === 0,
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      // El caso que da la razon de ser a todo esto: una guia a la que le
      // falta la cocina hace que se te olvide la cocina al editar, y eso no
      // se nota hasta despues de entregar.
      nombre: "un cuarto que el modelo se salto sale como faltante",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Fachada", porque: "…" }],
          ["Fachada", "Cocina"]
        );
        return {
          ok: r.faltan.join() === "Cocina" && r.inventados.length === 0,
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "un cuarto que el modelo se invento sale como inventado",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Fachada", porque: "…" }, { cuarto: "Sótano", porque: "…" }],
          ["Fachada"]
        );
        return {
          ok: r.inventados.join() === "Sótano" && r.faltan.length === 0,
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "faltar e inventar a la vez son dos avisos, no uno",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Sótano", porque: "…" }],
          ["Cocina"]
        );
        return {
          ok: r.faltan.join() === "Cocina" && r.inventados.join() === "Sótano",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      // El que un `.trim().toLowerCase()` de mas esconderia. «Recamara 1»
      // no es «Recámara 1»: uno es el cuarto de Bruno y el otro es un cuarto
      // que el modelo escribio distinto, y tratarlos como el mismo es
      // exactamente la clase de bug del 2026-08-22 -- dos partes diciendo
      // cosas distintas del mismo dato.
      nombre: "el acento cuenta: Recamara 1 no es Recámara 1",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Recámara 1", porque: "…" }],
          ["Recamara 1"]
        );
        return {
          ok: r.faltan.join() === "Recamara 1" && r.inventados.join() === "Recámara 1",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "el mismo cuarto repetido se marca una sola vez",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Sala", porque: "…" }, { cuarto: "Sala", porque: "…" }],
          ["Sala"]
        );
        return {
          ok: r.faltan.length === 0 && r.inventados.length === 0 && r.repetidos.join() === "Sala",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "una respuesta que no es JSON se dice, no se enseña a medias",
      fn: () => {
        const r = ctx.leerRespuesta("Claro, con gusto. Primero iría la fachada…");
        return { ok: r.ok === false && !!r.error, detalle: JSON.stringify(r) };
      },
    },
    {
      // Los modelos envuelven el JSON en ```json … ``` aunque se les pida que
      // no. Es tan comun que tratarlo como error seria fallar por una
      // formalidad, con la respuesta buena adentro.
      nombre: "un JSON envuelto en ```json se lee igual",
      fn: () => {
        const r = ctx.leerRespuesta(
          '```json\n{"orden":[{"cuarto":"Sala","porque":"Es la entrada"}]}\n```'
        );
        return {
          ok: r.ok === true && r.lista.length === 1 && r.lista[0].cuarto === "Sala",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "un JSON válido con la forma equivocada tampoco pasa",
      fn: () => {
        const r = ctx.leerRespuesta('{"cuartos": ["Sala", "Cocina"]}');
        return { ok: r.ok === false && !!r.error, detalle: JSON.stringify(r) };
      },
    },
    {
      // El §5 del spec: de la computadora solo salen nombres de cuarto y lo
      // que Bruno escriba. Este es el punto exacto donde un descuido saca
      // algo que no debia salir.
      nombre: "el cuerpo que se manda lleva los cuartos y nada más",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(
          ["Fachada", "Cocina"],
          { propiedad: "Casa", para: ["Redes"] },
          []
        );
        const texto = JSON.stringify(cuerpo);
        const sospechoso = /\/Users\/|\.MP4|\.mp4|C:\\\\|\/Volumes\//.test(texto);
        return {
          ok: !sospechoso && texto.includes("Fachada") && texto.includes("Cocina"),
          detalle: sospechoso ? "el cuerpo trae algo que parece una ruta o un archivo" : "limpio",
        };
      },
    },
    {
      // El §3 del spec: el modelo no vio el video y no debe describir lo que
      // hay adentro de ningun cuarto. Esto no garantiza que obedezca --eso lo
      // atrapa el ojo de Bruno-- pero si que se lo pidieron.
      nombre: "al modelo se le dice que no vio el material",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(["Sala"], {}, []);
        const sistema = cuerpo.messages.find((m) => m.role === "system").content;
        return {
          ok: /no viste|no has visto/i.test(sistema) && /JSON/i.test(sistema),
          detalle: sistema.slice(0, 160),
        };
      },
    },
```

- [ ] **Step 2: Corre y comprueba que fallan**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: truena al cargar, porque `js/ordenSugerido.js` todavía no existe.

- [ ] **Step 3: Escribe `ordenSugerido.js`**

Lógica pura: ni `require("premierepro")`, ni `fetch`, ni `document`. Esa es la
regla que hace que se pueda probar con `node`, y romperla es romper la task.

Las tres funciones:

- **`cuerpoDelRequest(cuartos, respuestas, conversacion)`** arma el objeto que
  se le manda a DeepSeek: `model: "deepseek-chat"`, un mensaje de sistema y la
  conversación. El mensaje de sistema es donde vive el §3 del spec, y hay que
  escribirlo con esas palabras: que **no vio el material**, que la línea de
  cada cuarto es «por qué va aquí» y no una descripción de lo que hay adentro,
  que solo hable de la casa concreta si Bruno lo contó, que use **exactamente**
  los nombres de cuarto que se le dan —sin corregir acentos ni mayúsculas—, que
  estén **todos**, y que conteste en JSON `{"orden": [{"cuarto", "porque"}]}`.

- **`leerRespuesta(texto)`** quita el envoltorio de ```` ```json ```` si lo
  trae, parsea, y comprueba la forma: `orden` es arreglo, cada elemento trae
  `cuarto` (cadena no vacía) y `porque`. Devuelve `{ok, lista, error}` y nunca
  tira: una respuesta fea es un caso normal, no una excepción.

- **`revisarLista(lista, cuartosReales)`** compara por igualdad exacta de
  cadena. Devuelve `{faltan, inventados, repetidos}`. Nada de `trim`,
  `toLowerCase` ni normalizar acentos — eso es justo lo que esconde el bug
  (ver el caso del acento).

Cada una con su comentario arriba diciendo **por qué**, no qué hace.

- [ ] **Step 4: Corre hasta que pasen y commitea**

```bash
node uxp-plugin/pruebas/correr.js
git add uxp-plugin/js/ordenSugerido.js uxp-plugin/pruebas/ordenSugerido.pruebas.js
git commit -m "La lista del orden se revisa contra los cuartos reales antes de ensenarse

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: La llave

**Files:** `uxp-plugin/js/llave.js`, `uxp-plugin/pruebas/ordenSugerido.pruebas.js`, `uxp-plugin/js/autocheck-tests.js`

- [ ] **Step 1: El caso puro que falla**

`llaveTapada` es lógica de cadenas y se prueba con `node`:

```js
    {
      nombre: "la llave se enseña tapada, con los últimos cuatro",
      fn: () => {
        const t = ctx.llaveTapada("sk-abcdefghijklmnop1234");
        return {
          ok: t.endsWith("1234") && !t.includes("abcdefghij") && t.length < 24,
          detalle: t,
        };
      },
    },
    {
      nombre: "una llave corta se tapa entera, no se enseña a medias",
      fn: () => {
        const t = ctx.llaveTapada("sk-12");
        return { ok: !t.includes("12"), detalle: t };
      },
    },
```

Y hay que agregar `js/llave.js` a la lista de archivos que carga
`pruebas/correr.js` — pero **solo la parte pura**: `guardarLlave` y
`leerLlave` tocan el sistema de archivos de UXP y no corren en Node. Se
escriben en el mismo archivo y el corredor no las llama; si alguna vez el
corredor tronara por eso, la salida es partir el archivo, no meterle un
`require` falso.

- [ ] **Step 2: Escribir `llave.js`**

- `guardarLlave(llave)` / `leerLlave()` — un `llave.json` en
  `localFileSystem.getDataFolder()`, que es la carpeta privada del plugin. No
  el proyecto de Premiere (viaja al cliente), no junto al material (se copia a
  discos), no el repo (se sube a GitHub).
- `llaveTapada(llave)` — `"••••••••" + últimos 4`, y si la llave mide menos de
  8, puros puntos. Enseñar los últimos cuatro de una llave corta es enseñar
  media llave.
- **Nunca** pasa por `logToPanel`. Va un comentario diciéndolo, porque el log
  es el archivo que uno manda cuando algo falla.

- [ ] **Step 3: Comprobar en vivo que se guarda y se relee**

Una prueba en `autocheck-tests.js` que guarda una llave de mentiras, la relee
y la borra. Esto sí necesita UXP y por eso vive allá.

- [ ] **Step 4: Corre las dos y commitea**

```bash
node uxp-plugin/pruebas/correr.js
git add uxp-plugin/js/llave.js uxp-plugin/pruebas/ uxp-plugin/js/autocheck-tests.js
git commit -m "La llave de la API se pega una vez y se guarda tapada

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Leer los cuartos de `02. Clip`

**Files:** `uxp-plugin/js/cuartosDelProyecto.js`, `uxp-plugin/js/autocheck-tests.js`

- [ ] **Step 1: La prueba en vivo que falla**

En `autocheck-tests.js`, contra un proyecto real: crear `02. Clip` con tres
bins y `Sin clasificar`, pedir `cuartosDeLosBins` y comprobar que devuelve los
tres **sin** `Sin clasificar`.

- [ ] **Step 2: Escribirlo**

```js
// Los cuartos son las carpetas que cuelgan DIRECTO de «02. Clip». No se le
// preguntan a Bruno: si estan ahi es porque el ya los tecleo una vez en
// Clipify, y volver a pedirlos seria preguntar lo que ya se sabia.
//
// `CARPETA_DE_CLIPS` sale de `estructura.js` y no es la cadena «02. Clip»
// escrita otra vez: si algun dia se renombra alla arriba, esto sigue
// apuntando a la misma carpeta.
//
// «Sin clasificar» NO es un cuarto y no entra: es el cajon de lo que Bruno no
// alcanzo a clasificar, y meterlo en la guia haria que el modelo le buscara
// lugar en el recorrido de una casa a algo que no es un lugar de la casa.
```

Devuelve `[]` cuando no hay `02. Clip` — que no es un error, es la Task 7.

- [ ] **Step 3: Correr contra Premiere y commitear**

```bash
git add uxp-plugin/js/cuartosDelProyecto.js uxp-plugin/js/autocheck-tests.js
git commit -m "Leer los cuartos de 02. Clip, sin «Sin clasificar»

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: La llamada a DeepSeek

**Files:** `uxp-plugin/js/deepseek.js`, `uxp-plugin/js/autocheck-tests.js`

Chiquito a propósito: `pedirOrden(llave, cuerpo)` hace el `POST` a
`https://api.deepseek.com/v1/chat/completions` y devuelve el texto de la
respuesta. **No arma el cuerpo** (eso es la Task 3) y **no lo interpreta**
(también la Task 3). Ese corte es lo que deja cambiar de proveedor en un
renglón, como dijo Bruno.

- [ ] **Step 1: Los casos feos, cada uno con su mensaje**

Sin llave, llave rechazada (401), sin internet, y una respuesta que llega
vacía. Cada uno dice qué pasó en palabras de Bruno — «la llave no sirve» y no
«HTTP 401» — y ninguno deja el panel en un estado ambiguo. Mismo criterio que
`importarManifestDesdeArchivo`, que ya tiene un mensaje propio por cada caso.

- [ ] **Step 2: Escribirlo y probarlo en vivo**

Con llave de verdad (la de Bruno, pegada en el panel) y con una inválida, para
ver los dos caminos. **La llave no se escribe en el log ni en el resultado del
arnés.**

- [ ] **Step 3: Commit**

```bash
git add uxp-plugin/js/deepseek.js uxp-plugin/js/autocheck-tests.js
git commit -m "Hablar con DeepSeek, con un mensaje propio para cada caso feo

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: La pestaña

**Files:** `uxp-plugin/index.html`, `uxp-plugin/js/pestanaOrden.js`

- [ ] **Step 1: Las dos pestañas, y el nombre**

`index.html` gana dos pestañas —«Importar» con lo que ya hay, «Orden
sugerido»— y el encabezado pasa de «Clasificador de Video» a **Clipify**
(§11 del spec: la app se llama así desde el 2026-08-27 y el `manifest.json` ya
lo dice; este archivo se quedó atrás).

Lo de hoy no se toca más que para meterlo en su pestaña: el botón de importar
es lo que Bruno usa todos los días y esta task no tiene por qué moverlo.

- [ ] **Step 2: La pestaña, de arriba abajo**

1. **La llave**, si no está puesta: una caja, un botón de guardar, y ya. Si
   está puesta, se enseña tapada con un «cambiar».
2. **Los cuartos leídos**, en un renglón: «Encontré 7 cuartos en 02. Clip». Si
   no encontró, la caja para teclearlos a mano, uno por renglón (§7).
3. **Las tres preguntas**, juntas, con sus chips de varios (§4.1). Se pueden
   dejar en blanco.
4. **«Dame la lista»**, activo desde el primer momento.
5. **La lista**, cuando llega: cada cuarto con su número, su nombre y su línea
   de por qué. Los inventados **tachados**.
6. **El aviso del §6**, arriba de la lista y no abajo, cuando falta o sobra
   alguno. Con los nombres, no con una cuenta.
7. **La caja de texto libre**, siempre abajo, para seguirle hablando. Cada
   mensaje rehace la lista completa.
8. **«Copiar»**, que deja la guía en el portapapeles como texto plano.

- [ ] **Step 3: Correrlo en Premiere y usarlo**

Con un proyecto real de Bruno. Y **a propósito, con una respuesta a la que le
falte un cuarto** —se fuerza quitándole uno a mano a la respuesta antes de
enseñarla— para ver el aviso del §6 con los ojos. Un aviso que nunca se vio no
está comprobado.

- [ ] **Step 4: Commit**

```bash
git add uxp-plugin/index.html uxp-plugin/js/pestanaOrden.js
git commit -m "La pestana «Orden sugerido» en el panel de Clipify

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Barrido final

**Files:** `README.md`, `docs/superpowers/CONTEXTO-Y-METAS.md`, `CLAUDE.md`, `uxp-plugin/README.md`, `docs/DESARROLLO.md`

- [ ] **Step 1: Verificación visual real**

Captura de la pestaña en dos estados —la lista limpia, y la lista con el aviso
de un cuarto faltante— vista con los ojos. Los archivos temporales van al
scratchpad, **nunca al repo**.

- [ ] **Step 2: El README**

Qué es la pestaña y cómo se usa, escrito para quien la usa: que hay que pegar
una llave de DeepSeek una vez, que la guía no mueve nada, y que si le falta un
cuarto la propia pestaña lo dice.

- [ ] **Step 3: `docs/DESARROLLO.md`**

Cómo correr las pruebas nuevas: `node uxp-plugin/pruebas/correr.js`. Es un
comando nuevo en un repo donde hasta hoy «correr las pruebas» era solo pytest,
y si no queda escrito, no lo corre nadie.

- [ ] **Step 4: `CONTEXTO-Y-METAS.md` y `CLAUDE.md`**

En `CONTEXTO-Y-METAS`, el estado y lo que se descartó con su razón: mirar
fotogramas, ordenar clips dentro del cuarto, el botón «acomodar así», el
segundo plugin.

En `CLAUDE.md`, a las decisiones de arquitectura: que el orden de un recorrido
se decide por lo que **es** cada cuarto y no por el pixel, que la pestaña **no
escribe** en el proyecto, y que la lista se revisa contra los bins antes de
enseñarse. Los tres son cosas que alguien va a querer «simplificar» dentro de
seis meses.

- [ ] **Step 5: Repasar que todo tenga su lugar**

```bash
git status
```

Ningún archivo suelto en la raíz. `uxp-plugin/pruebas/` es carpeta nueva y su
nombre dice lo que contiene.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/ CLAUDE.md uxp-plugin/README.md
git commit -m "El orden sugerido, en la documentacion

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
