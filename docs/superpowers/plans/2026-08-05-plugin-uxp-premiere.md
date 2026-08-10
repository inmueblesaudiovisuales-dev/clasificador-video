# Plugin UXP para Premiere — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el plugin UXP que, al presionar un botón, lee el manifest JSON que el usuario elige y organiza los clips dentro de Premiere Pro (bins anidados, in/out, color de etiqueta, proxy vinculado), usando la API de Premiere ya validada con clips reales en `uxp-test/`.

**Architecture:** Plugin UXP plano (HTML + JS, sin framework, sin build step — igual que `uxp-test/`), con módulos JS separados por responsabilidad: helpers de Premiere (bins/import/label/in-out/proxy), procesamiento de un manifest, el flujo del botón, y una UI de estado simple dentro del panel. La construcción de la secuencia queda como módulo aparte y vacío (Task 12), preparado para el armado automático futuro.

**Tech Stack:** UXP (JavaScript), API `premierepro` (paquete `@adobe/premierepro`, ya confirmado disponible en Premiere Pro 26.3.0).

---

## Cómo se verifica en este plan (leer antes que nada)

**Decisión del usuario: se construye de corrido y sus pruebas se juntan al final.** No hay que pedirle confirmación tarea por tarea.

Eso **no** significa construir a ciegas. Quedó validado en vivo (spikes de este mismo día) que casi toda la verificación se puede hacer sin intervención humana:

- **El plugin se carga y recarga desde la terminal**, sin abrir UXP Developer Tools. Ver "Manejo del plugin por línea de comandos" abajo.
- **El plugin corre su auto-comprobación solo al cargarse** y escribe el resultado en un archivo JSON que quien ejecuta el plan lee desde la terminal. Comprobado con material real.
- **La API contesta casi todo lo que hay que verificar:** si el bin existe y está anidado, si hay duplicados, en qué bin quedó un clip, qué color tiene, qué marcas de in/out, si el proxy está adjunto y con qué ruta, si un clip que falla no tumba a los demás.

Por lo tanto, la regla de este plan:

> **Cada task se verifica solo, por la vía automática, antes de pasar al siguiente.** Lo que la máquina no puede contestar se difiere a la sesión final con el usuario (Task 13). No se le interrumpe antes.

**Lo único que la máquina NO puede verificar, y se difiere al Task 13:**

1. **La rotación** — que el clip vertical se vea derecho. Confirmado que la API no expone dimensiones ni rotación del clip (`FootageInterpretation` y `Media` no las tienen). Requiere ojos humanos en el monitor de origen.
2. **El botón y su explorador de archivos** — es un diálogo nativo de macOS; ningún script puede elegir el archivo.
3. **Reiniciar Premiere** para comprobar que el plugin instalado carga sin las herramientas de desarrollo.
4. **Tener Premiere abierto con un proyecto desechable** — no es una prueba, es el estado inicial; se pide una sola vez al empezar.

### Manejo del plugin por línea de comandos

Validado contra Premiere Pro 26.3.0. **Dos tropiezos ya resueltos, no volver a pelearlos:**

- El instalador de Adobe está roto: su script de arranque requiere `tar`, que él mismo no instala. Instalar con `--ignore-scripts` y correr el setup a mano después.
- La pieza nativa que trae viene compilada **solo para Intel**. En Apple Silicon hay que correr Node bajo Rosetta con `arch -x86_64`.

```bash
# Instalación (una sola vez)
mkdir -p /tmp/uxpcli-install && cd /tmp/uxpcli-install
npm install tar@6 --no-audit --no-fund
npm install @adobe/uxp-devtools-cli@1.2.0 --ignore-scripts --no-audit --no-fund
node node_modules/@adobe/uxp-devtools-helper/scripts/devtools_setup.js

# Confirmar que ve Premiere
arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js apps list

# Cargar / recargar el plugin (desde la carpeta uxp-plugin/)
cd "<RAIZ-DEL-REPO>/uxp-plugin"
arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js plugin load
arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js plugin reload
```

---

## Notas para quien ejecute este plan

- No hay corredor de pruebas automatizado para JS/UXP en este proyecto. La verificación se hace contra un Premiere real corriendo, por la vía automática descrita arriba (cargar por CLI → el plugin corre su auto-comprobación → leer el archivo de resultados). Esto es intencional, no un hueco del plan: la API de Premiere solo se puede probar contra Premiere.
- Ya existe un plugin de prueba funcional en `uxp-test/` (`manifest.json`, `index.html`) que confirmó: import con rotación correcta, bins anidados, label, e in/out — todo junto, para 3 clips reales. Este plan construye el plugin de producción a partir de esos mismos patrones ya confirmados; no se re-derivan desde cero.
- Detalle crítico ya descubierto (no volver a perder tiempo en esto): `executeTransaction` **debe** ir envuelto en `project.lockedAccess(() => {...})`, si no, falla con "The script object is no longer valid."
- Clips de prueba reales disponibles en `TEST/` dentro de este mismo proyecto (`20260804_PIB0587.MP4`, `...0588.MP4`, `...0589.MP4`), y su proxy real en `TEST/20260804_PIB0587S03.MP4`.
- **Todas las verificaciones se hacen en un proyecto de Premiere desechable**, nunca en uno de trabajo. Cada task deja bins de prueba (`PruebaTask1`, `PruebaTask2`, …) regados en el proyecto. Crear uno nuevo y vacío antes de empezar, y tirarlo al terminar el plan.
- **El plugin no vigila ninguna carpeta.** El usuario presiona un botón y elige el manifest con el explorador de macOS (ver Task 9). No hay carpetas del sistema que crear, ni archivos del usuario que mover o renombrar.
- **`attachProxy` ya está validado en vivo** (spike `uxp-test/proxy-spike/`, commit `3859bd4`): `attachProxy` devuelve `true`, `hasProxy()` pasa a `true`, `getProxyPath()` devuelve la ruta exacta, y readjuntar es seguro. El Task 6 ya no es un riesgo abierto — es portar código que corrió.
- Dos mecanismos validados en ese mismo spike, que se usan en todo el plugin: localizar un clip por `getMediaFilePath()` (nunca por nombre de archivo) y reintentar hasta que Premiere registre el item recién importado.
- **Protocolo cuando una verificación falla:** detenerse ahí. No avanzar al siguiente task, no "arreglar sobre la marcha" en silencio. Anotar el error exacto (mensaje completo, no un resumen), diagnosticar la causa, y solo entonces corregir. Si la corrección cambia el diseño, actualizar el spec antes de seguir.
- **Rotación:** el clip vertical debe verse derecho. Es el problema que originó todo el proyecto y se rompe en silencio. No se puede comprobar por código (la API no expone dimensiones ni rotación), así que se verifica con el usuario en el Task 13 — pero **no se da por hecho**: es el primer punto de esa sesión, y si falla, todo lo demás no importa.
- **`findItemsMatchingMediaPath` ya se probó y NO sirve** (spike `uxp-test/busqueda-spike/`, commit `0738e71`): solo existe sobre un `ClipProjectItem` y solo encuentra su propia ruta. Desde el clip A buscando al clip B da 0 resultados, en el mismo bin y en otro. El nombre promete un buscador del proyecto y no lo es. **Se queda `findClipByPath` (recorrido manual del árbol) tal como está escrito. No volver a investigar esto.**

---

### Task 0: Scaffold del plugin

**Files:**
- Create: `uxp-plugin/manifest.json`
- Create: `uxp-plugin/index.html`
- Create: `uxp-plugin/js/log.js`

- [ ] **Step 1: Crear `uxp-plugin/manifest.json`**

```json
{
  "id": "com.iav.clasificadorvideo",
  "name": "Clasificador de Video IAV",
  "version": "1.0.0",
  "main": "index.html",
  "host": {
    "app": "premierepro",
    "minVersion": "25.1.0"
  },
  "manifestVersion": 5,
  "requiredPermissions": {
    "localFileSystem": "fullAccess"
  },
  "entrypoints": [
    {
      "id": "panel1",
      "type": "panel",
      "label": { "default": "Clasificador de Video" },
      "minimumSize": { "width": 320, "height": 300 }
    }
  ]
}
```

- [ ] **Step 2: Crear `uxp-plugin/js/log.js`**

```javascript
// Log simple visible dentro del panel (no solo consola de desarrollador).
function logToPanel(message, isError) {
  const list = document.getElementById("log-list");
  if (!list) return;
  const entry = document.createElement("div");
  entry.textContent = (isError ? "[ERROR] " : "") + message;
  entry.style.color = isError ? "#e06c75" : "inherit";
  list.prepend(entry);
}
```

- [ ] **Step 3: Crear `uxp-plugin/index.html`**

El botón nace deshabilitado; el Task 9 le conecta el comportamiento real.

```html
<div style="padding: 8px; font-family: sans-serif;">
  <h3>Clasificador de Video</h3>
  <button id="importar" disabled>Importar clasificacion...</button>
  <div id="status" style="margin-top: 8px;">Listo.</div>
  <div id="log-list" style="margin-top: 8px; font-size: 12px; max-height: 400px; overflow-y: auto;"></div>
</div>
<script src="js/log.js"></script>
<script>
  logToPanel("Plugin cargado.");
</script>
```

- [ ] **Step 4: Verificar que carga en Premiere**

Abrir un **proyecto de Premiere desechable** (todas las verificaciones del plan dejan bins de prueba adentro).
Abrir UXP Developer Tools → Add Plugin → carpeta `uxp-plugin/` → Load. En Premiere: `Window > UXP Plugins > Clasificador de Video`.
Expected: aparece el panel con el título, el botón deshabilitado, y el mensaje "Plugin cargado." en la lista.

- [ ] **Step 5: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/
git commit -m "chore: scaffold del plugin UXP de produccion"
```

---

### Task 0b: Arnés de auto-comprobación (lo que permite construir sin interrumpir al usuario)

Sin esto, cada task necesitaría que alguien mire Premiere. Con esto, el plugin se comprueba solo al cargarse y deja el resultado en un archivo que se lee desde la terminal. **Mecanismo ya validado en vivo** (spike `uxp-test/busqueda-spike/`, commit `0738e71`).

**Files:**
- Create: `uxp-plugin/js/autocheck.js`
- Modify: `uxp-plugin/index.html`

- [ ] **Step 1: Escribir el arnés**

`uxp-plugin/js/autocheck.js`:

```javascript
// Arnes de auto-comprobacion. Solo se usa durante la construccion: corre al
// cargar el plugin y deja el resultado en un archivo que se lee desde la
// terminal. Se apaga poniendo AUTOCHECK_ACTIVO en false (Task 13).
const AUTOCHECK_ACTIVO = true;
const AUTOCHECK_SALIDA_DIR = "/private/tmp/clasificador-autocheck";
const AUTOCHECK_SALIDA_ARCHIVO = "resultado.json";

const autocheckResultados = [];
let autocheckPruebas = [];

// Cada task registra aqui sus comprobaciones. nombre: que se comprueba.
// fn: funcion async que devuelve { ok: boolean, detalle: string }.
function registrarPrueba(nombre, fn) {
  autocheckPruebas.push({ nombre, fn });
}

function anotarResultado(nombre, ok, detalle) {
  autocheckResultados.push({ nombre, ok: !!ok, detalle: String(detalle) });
  logToPanel(nombre + ": " + (ok ? "OK" : "FALLO") + " — " + detalle, !ok);
}

async function correrAutocheck() {
  if (!AUTOCHECK_ACTIVO) return;

  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  if (!project) {
    anotarResultado("proyecto activo", false, "No hay proyecto abierto en Premiere");
    await escribirResultadoAutocheck();
    return;
  }
  anotarResultado("proyecto activo", true, project.name);

  for (const prueba of autocheckPruebas) {
    try {
      const r = await prueba.fn(project);
      anotarResultado(prueba.nombre, r.ok, r.detalle);
    } catch (e) {
      anotarResultado(prueba.nombre, false, e.message);
    }
  }

  await escribirResultadoAutocheck();
}

async function escribirResultadoAutocheck() {
  const uxpFs = require("uxp").storage.localFileSystem;
  const fallidas = autocheckResultados.filter((r) => !r.ok).length;
  const carpeta = await uxpFs.getEntryWithUrl("file://" + AUTOCHECK_SALIDA_DIR);
  const archivo = await carpeta.createFile(AUTOCHECK_SALIDA_ARCHIVO, { overwrite: true });
  await archivo.write(
    JSON.stringify(
      {
        cuando: new Date().toISOString(),
        total: autocheckResultados.length,
        fallidas: fallidas,
        resultados: autocheckResultados,
      },
      null,
      2
    )
  );
}
```

- [ ] **Step 2: Crear la carpeta de salida**

```bash
mkdir -p /tmp/clasificador-autocheck
```

- [ ] **Step 3: Conectarlo en `index.html`**

Agregar `<script src="js/autocheck.js"></script>` después de `log.js`, y al final del script inline: `correrAutocheck();`

- [ ] **Step 4: Verificar el arnés mismo**

Registrar una prueba de mentiras que siempre pase, recargar por CLI, y confirmar que el archivo aparece:

```bash
cd "<RAIZ-DEL-REPO>/uxp-plugin"
arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js plugin reload
sleep 5 && cat /tmp/clasificador-autocheck/resultado.json
```

Expected: el JSON trae `"fallidas": 0` y el nombre del proyecto desechable. Quitar la prueba de mentiras.

**De aquí en adelante, la verificación de cada task es:** registrar sus comprobaciones con `registrarPrueba(...)`, recargar por CLI, leer el archivo, confirmar `fallidas: 0`. Si algo falla, detenerse ahí (ver protocolo en las notas).

- [ ] **Step 5: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/autocheck.js uxp-plugin/index.html
git commit -m "chore: arnes de auto-comprobacion que corre al cargar y escribe resultados a disco"
```

---


### Task 1: Helper de transacciones de Premiere

**Files:**
- Create: `uxp-plugin/js/premiereActions.js`

- [ ] **Step 1: Escribir el helper**

`uxp-plugin/js/premiereActions.js`:

```javascript
// Envuelve el patron obligatorio: executeTransaction siempre dentro de
// lockedAccess, o falla con "The script object is no longer valid".
function runTransaction(project, buildActions, undoLabel) {
  let result;
  project.lockedAccess(() => {
    result = project.executeTransaction((compoundAction) => {
      const actions = buildActions();
      const list = Array.isArray(actions) ? actions : [actions];
      for (const action of list) {
        compoundAction.addAction(action);
      }
    }, undoLabel);
  });
  return result;
}
```

- [ ] **Step 2: Cargarlo en `index.html`**

Agregar antes del script inline: `<script src="js/premiereActions.js"></script>`

- [ ] **Step 3: Verificar con una prueba manual mínima**

Agregar temporalmente al script inline de `index.html`:

```javascript
document.getElementById("status").addEventListener("click", async () => {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  const rootItem = await project.getRootItem();
  const ok = runTransaction(project, () => rootItem.createBinAction("PruebaTask1", true), "Prueba Task 1");
  logToPanel("runTransaction resultado: " + ok);
});
```

Recargar el plugin, hacer clic en el texto "Esperando manifests...", confirmar en Premiere que aparece un bin "PruebaTask1" y en el panel el log "runTransaction resultado: true".

Quitar el `addEventListener` de prueba antes de continuar (no se necesita en producción, era solo para verificar el helper).

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/premiereActions.js uxp-plugin/index.html
git commit -m "feat: helper runTransaction (lockedAccess + executeTransaction)"
```

---

### Task 2: Resolver/crear cadena de bins anidados

**Files:**
- Create: `uxp-plugin/js/bins.js`

- [ ] **Step 1: Escribir la función**

`uxp-plugin/js/bins.js`:

```javascript
// Dado ["Recamara 2", "Bano"], crea (o reusa) el bin "Recamara 2" dentro de
// parentFolder, y dentro de ese "Bano". Devuelve el FolderItem final.
async function resolveBinChain(project, rootFolder, categoryPath) {
  const premierepro = require("premierepro");
  let currentFolder = rootFolder;

  for (const name of categoryPath) {
    const items = await currentFolder.getItems();
    let found = items.find((i) => i.name === name);

    if (!found) {
      runTransaction(project, () => currentFolder.createBinAction(name, true), "Crear bin " + name);
      const afterItems = await currentFolder.getItems();
      found = afterItems.find((i) => i.name === name);
    }

    currentFolder = premierepro.FolderItem.cast(found);
  }

  return currentFolder;
}
```

- [ ] **Step 2: Cargarlo en `index.html`**

Agregar: `<script src="js/bins.js"></script>` (después de `premiereActions.js`).

- [ ] **Step 3: Verificar manualmente**

Agregar temporalmente al script inline:

```javascript
document.getElementById("status").addEventListener("click", async () => {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  const rootItem = await project.getRootItem();
  const folder = await resolveBinChain(project, rootItem, ["PruebaTask2", "Sub"]);
  logToPanel("bin final: " + folder.name);
});
```

Recargar, clic, confirmar en Premiere que existe `PruebaTask2 > Sub` anidado, y en el panel "bin final: Sub". Correr el clic una segunda vez y confirmar que NO se duplica el bin (reusa el existente).

Quitar el `addEventListener` de prueba.

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/bins.js uxp-plugin/index.html
git commit -m "feat: resolver/crear cadena de bins anidados"
```

---

### Task 3: Importar o reusar un clip ya importado (evita duplicar en reexportaciones)

**Files:**
- Create: `uxp-plugin/js/importClip.js`

- [ ] **Step 1: Escribir la función**

`uxp-plugin/js/importClip.js`:

**Dos reglas de identidad, ambas obligatorias (ver spec §12):**

- **Carpetas: por objeto, nunca por nombre.** `Recámara 1 > Baño` y `Recámara 2 > Baño` se llaman igual. Comparar nombres haría que una corrección entre esos dos baños se pierda en silencio.
- **Clips: por ruta en disco, nunca por nombre de archivo.** Dos tarjetas distintas producen `PIB0587.MP4` cada una. Ya validado en el spike de proxy.

```javascript
// Si el clip (por ruta real en disco) ya existe en el proyecto, lo mueve al
// bin destino si hace falta y lo devuelve sin reimportar. Si no existe, lo
// importa dentro de ese bin.
async function importOrReuseClip(project, targetFolder, filePath) {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const found = await findClipByPath(rootFolder, filePath);
  if (found) {
    const currentParent = await found.getParentBin();
    // Comparar la carpeta REAL, no su nombre: hay bins homonimos en ramas
    // distintas (Recamara 1 > Bano vs Recamara 2 > Bano).
    if (!(await esMismaCarpeta(currentParent, targetFolder))) {
      runTransaction(
        project,
        () => rootFolder.createMoveItemAction(found, targetFolder),
        "Mover clip existente"
      );
    }
    return found;
  }

  await project.importFiles([filePath], true, targetFolder, false);

  // Premiere no siempre registra el item al instante: reintentar buscando por
  // ruta dentro del bin destino (validado en el spike de proxy).
  for (let intento = 1; intento <= 10; intento++) {
    const clip = await findClipByPath(targetFolder, filePath);
    if (clip) return clip;
    await new Promise((r) => setTimeout(r, 300));
  }
  return null;
}

// Dos FolderItem son la misma carpeta si su ruta de nombres desde la raiz
// coincide. No basta comparar el nombre suelto.
async function esMismaCarpeta(a, b) {
  if (!a || !b) return false;
  const rutaA = await rutaDeCarpeta(a);
  const rutaB = await rutaDeCarpeta(b);
  return rutaA === rutaB;
}

async function rutaDeCarpeta(folder) {
  const partes = [];
  let actual = folder;
  while (actual) {
    partes.unshift(actual.name);
    actual = await actual.getParentBin();
  }
  return partes.join("/");
}

// Recorre el arbol de bins buscando un ClipProjectItem con ese media path.
async function findClipByPath(folder, filePath) {
  const premierepro = require("premierepro");
  const items = await folder.getItems();

  for (const item of items) {
    const clipItem = premierepro.ClipProjectItem.cast(item);
    if (clipItem) {
      try {
        const mediaPath = await clipItem.getMediaFilePath();
        if (mediaPath === filePath) return clipItem;
      } catch (e) {
        // no es un clip con archivo de medios (ej. una secuencia); continuar.
      }
      continue;
    }
    const subFolder = premierepro.FolderItem.cast(item);
    if (subFolder) {
      const match = await findClipByPath(subFolder, filePath);
      if (match) return match;
    }
  }
  return null;
}
```

**Nota sobre `rutaDeCarpeta`:** asume que `getParentBin()` devuelve `null` en la raíz del proyecto. Confirmarlo en la primera corrida — si devuelve otra cosa, el ciclo no termina. Si `FolderItem` expone un identificador propio (revisar `premierepro.d.ts`), usarlo en lugar de la ruta de nombres: es más directo.

- [ ] **Step 2: Cargarlo en `index.html`**

Agregar: `<script src="js/importClip.js"></script>`

- [ ] **Step 3: Verificar manualmente (tres corridas)**

Agregar temporalmente al script inline:

```javascript
document.getElementById("status").addEventListener("click", async () => {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  const rootItem = await project.getRootItem();
  const folder = await resolveBinChain(project, rootItem, ["PruebaTask3"]);
  const clip = await importOrReuseClip(
    project,
    folder,
    "<RAIZ-DEL-REPO>/TEST/20260804_PIB0588.MP4"
  );
  logToPanel("clip resuelto: " + (clip ? clip.name : "NO ENCONTRADO"));
});
```

Registrar estas comprobaciones con `registrarPrueba(...)`, recargar por CLI, y confirmar `fallidas: 0` en `/tmp/clasificador-autocheck/resultado.json`. Las tres son automáticas: la API contesta todas.

1. **Importar:** el clip queda dentro de `PruebaTask3` (confirmar por `getMediaFilePath()`, no por nombre).
2. **No duplicar:** llamar `importOrReuseClip` dos veces con la misma ruta y confirmar que `PruebaTask3` sigue teniendo **un solo** clip con esa ruta.
3. **La corrección (el caso de todos los días):** llamar con destino `["Recamara 1", "Bano"]` y luego con `["Recamara 2", "Bano"]`. Confirmar que el clip **se mudó** al segundo baño y que el primero quedó vacío. Los dos bins se llaman "Baño": si el clip se queda en el primero, la comparación de carpetas está mal hecha. **Es la comprobación más importante de todo el plan** — es el error que se corrigió en este task.

**La rotación NO se comprueba aquí** (la API no la expone). Va en el Task 13, con el usuario.

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/importClip.js uxp-plugin/index.html
git commit -m "feat: importar o reusar clip existente por ruta (sin duplicar en reexportaciones)"
```

---

### Task 4: Aplicar color de etiqueta

**Files:**
- Create: `uxp-plugin/js/label.js`

- [ ] **Step 1: Escribir la función**

`uxp-plugin/js/label.js`:

```javascript
const LABEL_BY_FLAG = {
  pick: "FOREST",
  reject: "ROSE",
};

// flag: "pick" | "reject" | "none". Si es "none", no hace nada (no limpia
// una etiqueta previa a proposito -- no es un caso pedido por el spec).
function applyFlagLabel(project, clipItem, flag) {
  const premierepro = require("premierepro");
  const labelName = LABEL_BY_FLAG[flag];
  if (!labelName) return;

  runTransaction(
    project,
    () => clipItem.createSetColorLabelAction(premierepro.Constants.ProjectItemColorLabel[labelName]),
    "Set label " + flag
  );
}
```

- [ ] **Step 2: Cargarlo en `index.html`**

Agregar: `<script src="js/label.js"></script>`

- [ ] **Step 3: Verificar manualmente**

Reusar el clip importado en el Task 3 (`PruebaTask3`). Agregar temporalmente al script inline:

```javascript
document.getElementById("status").addEventListener("click", async () => {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  const rootItem = await project.getRootItem();
  const folder = await resolveBinChain(project, rootItem, ["PruebaTask3"]);
  const items = await folder.getItems();
  applyFlagLabel(project, items[0], "pick");
  logToPanel("label aplicado a " + items[0].name);
});
```

Recargar, clic, confirmar en Premiere que el clip de `PruebaTask3` queda con color Forest (verde).

Quitar el `addEventListener` de prueba.

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/label.js uxp-plugin/index.html
git commit -m "feat: aplicar color de etiqueta segun pick/reject"
```

---

### Task 5: Aplicar in/out directo sobre el clip

**Files:**
- Create: `uxp-plugin/js/inOut.js`

- [ ] **Step 1: Escribir la función**

`uxp-plugin/js/inOut.js`:

```javascript
// inFrame/outFrame: enteros de numero de frame, o null para no tocar el
// in/out del clip (se deja el clip completo).
function applyInOut(project, clipItem, fps, inFrame, outFrame) {
  const premierepro = require("premierepro");
  if (inFrame === null || outFrame === null) return;

  const clipProjectItem = premierepro.ClipProjectItem.cast(clipItem);
  const frameRate = premierepro.FrameRate.createWithValue(fps);
  const inPoint = premierepro.TickTime.createWithFrameAndFrameRate(inFrame, frameRate);
  const outPoint = premierepro.TickTime.createWithFrameAndFrameRate(outFrame, frameRate);

  runTransaction(
    project,
    () => clipProjectItem.createSetInOutPointsAction(inPoint, outPoint),
    "Set in/out"
  );
}
```

- [ ] **Step 2: Cargarlo en `index.html`**

Agregar: `<script src="js/inOut.js"></script>`

- [ ] **Step 3: Verificar manualmente**

Reusar el clip de `PruebaTask3` (dura 240 frames, PIB0588). Agregar temporalmente al script inline:

```javascript
document.getElementById("status").addEventListener("click", async () => {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  const rootItem = await project.getRootItem();
  const folder = await resolveBinChain(project, rootItem, ["PruebaTask3"]);
  const items = await folder.getItems();
  applyInOut(project, items[0], 59.94005994005994, 20, 150);
  logToPanel("in/out aplicado a " + items[0].name);
});
```

Recargar, clic, abrir el clip en el monitor de origen en Premiere, confirmar que el in/out ya viene marcado en frame 20 y 150.

Quitar el `addEventListener` de prueba.

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/inOut.js uxp-plugin/index.html
git commit -m "feat: aplicar in/out directo sobre el clip maestro"
```

---

### Task 6: Adjuntar proxy

**Ya validado en vivo** (spike `uxp-test/proxy-spike/`, commit `3859bd4`): `attachProxy` devolvió `true`, `hasProxy()` pasó a `true`, `getProxyPath()` devolvió la ruta exacta, y readjuntar el mismo proxy volvió a devolver `true` sin error. Este task es portar código que ya corrió, no una exploración.

**Files:**
- Create: `uxp-plugin/js/proxy.js`

- [ ] **Step 1: Escribir la función**

`uxp-plugin/js/proxy.js`:

```javascript
// proxyPath: ruta absoluta al proxy, o null si el clip no tiene proxy
// emparejado (ej. dron). attachProxy no es parte de una transaccion
// (segun la referencia de la API, no es undoable).
async function attachProxyIfPresent(clipItem, proxyPath) {
  const premierepro = require("premierepro");
  if (!proxyPath) return false;

  const clipProjectItem = premierepro.ClipProjectItem.cast(clipItem);
  const ok = await clipProjectItem.attachProxy(proxyPath, false);
  return ok;
}
```

- [ ] **Step 2: Cargarlo en `index.html`**

Agregar: `<script src="js/proxy.js"></script>`

- [ ] **Step 3: Verificar manualmente**

Reusar el clip real con proxy conocido: importar `TEST/20260804_PIB0587.MP4` (que sí tiene proxy en `TEST/20260804_PIB0587S03.MP4`) a un bin nuevo, luego adjuntar. Agregar temporalmente al script inline:

```javascript
document.getElementById("status").addEventListener("click", async () => {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  const rootItem = await project.getRootItem();
  const folder = await resolveBinChain(project, rootItem, ["PruebaTask6"]);
  const clip = await importOrReuseClip(
    project,
    folder,
    "<RAIZ-DEL-REPO>/TEST/20260804_PIB0587.MP4"
  );
  const ok = await attachProxyIfPresent(
    clip,
    "<RAIZ-DEL-REPO>/TEST/20260804_PIB0587S03.MP4"
  );
  logToPanel("attachProxy resultado: " + ok);
});
```

Recargar, clic, confirmar que el panel dice `attachProxy resultado: true`. Verificación dura (no depender del ícono): agregar temporalmente `logToPanel("hasProxy: " + await clip.hasProxy() + " | " + await clip.getProxyPath())` y confirmar que la ruta reportada es exactamente la del proxy.

Quitar el `addEventListener` de prueba.

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/proxy.js uxp-plugin/index.html
git commit -m "feat: adjuntar proxy al clip cuando el manifest lo trae"
```

---

### Task 7: Procesar un manifest completo (une los Tasks 2-6, tolerante a errores por clip)

**Este archivo tiene una sola responsabilidad: organizar el proyecto** (bins, importar, in/out, label, proxy). No sabe nada de secuencias. Construir la secuencia es otra responsabilidad, que nace vacía en el Task 12 y se llena en una versión futura (spec §12.1). No mezclar las dos aquí.

**Files:**
- Create: `uxp-plugin/js/processManifest.js`

- [ ] **Step 1: Escribir la función**

`uxp-plugin/js/processManifest.js`:

```javascript
// Procesa un manifest ya parseado (objeto JS, ver formato en el spec).
// Devuelve { ok: [nombresDeArchivo], errores: [{archivo, mensaje}] }.
async function processManifest(project, manifest) {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const resultado = { ok: [], errores: [] };

  for (const clipData of manifest.clips) {
    const nombreArchivo = clipData.ruta.split("/").pop();
    try {
      const categoryPath = clipData.categoria_path && clipData.categoria_path.length > 0
        ? clipData.categoria_path
        : ["Sin clasificar"];

      const targetFolder = await resolveBinChain(project, rootFolder, categoryPath);
      const clipItem = await importOrReuseClip(project, targetFolder, clipData.ruta);

      if (!clipItem) {
        throw new Error("No se pudo importar ni encontrar el clip");
      }

      applyFlagLabel(project, clipItem, clipData.flag);

      if (clipData.in_frame !== null && clipData.out_frame !== null) {
        const clipProjectItem = premierepro.ClipProjectItem.cast(clipItem);
        const media = await clipProjectItem.getMedia();
        const fps = media ? await getFpsFromMedia(media) : 30;
        applyInOut(project, clipItem, fps, clipData.in_frame, clipData.out_frame);
      }

      if (clipData.ruta_proxy) {
        await attachProxyIfPresent(clipItem, clipData.ruta_proxy);
      }

      resultado.ok.push(nombreArchivo);
      logToPanel("OK: " + nombreArchivo + " -> " + categoryPath.join(" > "));
    } catch (e) {
      resultado.errores.push({ archivo: nombreArchivo, mensaje: e.message });
      logToPanel(nombreArchivo + ": " + e.message, true);
    }
  }

  return resultado;
}

// Placeholder de fps: se reemplaza en el Task 8 por el fps real que ya viene
// en el manifest (ver Nota abajo) en vez de leerlo de Media.
async function getFpsFromMedia(media) {
  return 30;
}

// Revisa ANTES de empezar que el material exista en disco. El caso real: el
// usuario clasifica con el disco externo conectado y luego abre Premiere sin
// el disco. Sin esto, saldrian 40 errores en vez de un aviso claro.
// Devuelve { disponibles, faltantes: [rutas] }.
async function revisarMaterialDisponible(manifest) {
  const uxpFs = require("uxp").storage.localFileSystem;
  const faltantes = [];

  for (const clipData of manifest.clips) {
    try {
      await uxpFs.getEntryWithUrl("file://" + clipData.ruta);
    } catch (e) {
      faltantes.push(clipData.ruta);
    }
  }

  return { disponibles: manifest.clips.length - faltantes.length, faltantes };
}
```

**Nota para quien implemente:** `getFpsFromMedia` es una función temporal — el fps real de cada clip debe venir en el manifest (la app externa ya lo sabe, via `ffprobe`), no inferirse dentro del plugin. El Task 8 corrige esto agregando `fps` al formato del manifest y pasándolo directo a `processManifest`, eliminando `getFpsFromMedia`.

- [ ] **Step 2: Cargarlo en `index.html`**

Agregar: `<script src="js/processManifest.js"></script>`

- [ ] **Step 3: Verificar manualmente con un manifest de prueba**

Agregar temporalmente al script inline:

```javascript
document.getElementById("status").addEventListener("click", async () => {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();

  const manifestPrueba = {
    proyecto: "Prueba Task 7",
    clips: [
      {
        ruta: "<RAIZ-DEL-REPO>/TEST/20260804_PIB0587.MP4",
        categoria_path: ["PruebaTask7", "Bano"],
        in_frame: 10,
        out_frame: 90,
        flag: "pick",
        ruta_proxy: "<RAIZ-DEL-REPO>/TEST/20260804_PIB0587S03.MP4",
      },
      {
        ruta: "<RAIZ-DEL-REPO>/TEST/no-existe.MP4",
        categoria_path: ["PruebaTask7"],
        in_frame: null,
        out_frame: null,
        flag: "none",
        ruta_proxy: null,
      },
    ],
  };

  const resultado = await processManifest(project, manifestPrueba);
  logToPanel("resultado: ok=" + resultado.ok.length + " errores=" + resultado.errores.length);
});
```

Recargar, clic, confirmar:
- El primer clip queda bien en `PruebaTask7 > Bano`, con label, in/out, y proxy.
- El segundo (archivo inexistente) aparece como error en el panel, **sin que el primero se vea afectado**.
- El log final dice `ok=1 errores=1`.

Quitar el `addEventListener` de prueba.

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/processManifest.js uxp-plugin/index.html
git commit -m "feat: procesar un manifest completo, tolerante a errores por clip"
```

---

### Task 8: Ajustar el manifest para traer el fps y quitar el placeholder

**Files:**
- Modify: `uxp-plugin/js/processManifest.js`

- [ ] **Step 1: Reemplazar el uso del placeholder de fps**

En `uxp-plugin/js/processManifest.js`, reemplazar:

```javascript
      if (clipData.in_frame !== null && clipData.out_frame !== null) {
        const clipProjectItem = premierepro.ClipProjectItem.cast(clipItem);
        const media = await clipProjectItem.getMedia();
        const fps = media ? await getFpsFromMedia(media) : 30;
        applyInOut(project, clipItem, fps, clipData.in_frame, clipData.out_frame);
      }
```

por:

```javascript
      if (clipData.in_frame !== null && clipData.out_frame !== null) {
        applyInOut(project, clipItem, clipData.fps, clipData.in_frame, clipData.out_frame);
      }
```

Y borrar la función `getFpsFromMedia` completa (ya no se usa).

- [ ] **Step 2: Actualizar el manifest de formato en este mismo plan (referencia para el Task 9)**

De aquí en adelante, cada clip del manifest debe incluir `"fps"` (numero, ej. `59.94005994005994`), tomado directo de lo que la app externa ya obtiene con `ffprobe`. Formato completo actualizado (idéntico al spec §11):

```json
{
  "proyecto": "Casa Jardin",
  "orientacion": "vertical",
  "clips": [
    {
      "orden": 1,
      "ruta": "/ruta/absoluta/al/clip.MP4",
      "categoria_path": ["Recamara 2", "Bano"],
      "fps": 59.94005994005994,
      "in_frame": 30,
      "out_frame": 200,
      "flag": "pick",
      "ruta_proxy": "/ruta/absoluta/al/proxy.MP4"
    }
  ]
}
```

`orden` y `orientacion` **no se usan en la v1** — el plugin los ignora. Existen desde ahora para que el armado automático de la secuencia (spec §12.1) no obligue a rehacer el formato ni a reexportar clasificaciones viejas. **No agregar código que los use en este plan.**

- [ ] **Step 3: Verificar que el plugin sigue cargando sin errores de sintaxis**

Recargar el plugin en UDT, confirmar que no hay errores en la consola al cargar (no hace falta repetir la prueba completa del Task 7, solo confirmar que no quedó JS roto).

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/processManifest.js
git commit -m "refactor: el fps del clip viene del manifest, no se infiere en el plugin"
```

---

### Task 9: El botón "Importar clasificación"

Reemplaza a la vigilancia automática de una carpeta, descartada por decisión del usuario (spec §12): quiere una acción deliberada, no un proceso corriendo en segundo plano dentro de Premiere. El plugin **no mueve ni renombra ningún archivo del usuario** — solo lee el que se le señala.

**Files:**
- Create: `uxp-plugin/js/importarManifest.js`
- Modify: `uxp-plugin/index.html`

- [ ] **Step 1: Escribir el flujo del botón**

`uxp-plugin/js/importarManifest.js`:

```javascript
// Flujo completo del boton: elegir archivo -> validar -> revisar material ->
// procesar -> reportar. Cada caso feo tiene su mensaje propio; ninguno debe
// dejar el panel en un estado ambiguo.
async function importarManifestDesdeArchivo() {
  const premierepro = require("premierepro");
  const uxpFs = require("uxp").storage.localFileSystem;
  const status = document.getElementById("status");

  const project = await premierepro.Project.getActiveProject();
  if (!project) {
    logToPanel("No hay ningun proyecto abierto en Premiere. Abre uno y vuelve a intentar.", true);
    return;
  }

  const archivo = await uxpFs.getFileForOpening({ types: ["json"] });
  if (!archivo) {
    logToPanel("Cancelado, no se eligio ningun archivo.");
    return;
  }

  let manifest;
  try {
    manifest = JSON.parse(await archivo.read());
  } catch (e) {
    logToPanel("El archivo elegido no es una clasificacion valida: " + e.message, true);
    return;
  }

  if (!manifest.clips || !Array.isArray(manifest.clips) || manifest.clips.length === 0) {
    logToPanel("El archivo elegido no trae clips.", true);
    return;
  }

  // Disco desconectado: un aviso claro en vez de un error por cada clip.
  const material = await revisarMaterialDisponible(manifest);
  if (material.faltantes.length === manifest.clips.length) {
    logToPanel(
      "No se encontro NINGUNO de los " + manifest.clips.length +
        " archivos de video. Revisa que el disco con el material este conectado.",
      true
    );
    return;
  }
  if (material.faltantes.length > 0) {
    logToPanel(
      "Faltan " + material.faltantes.length + " de " + manifest.clips.length +
        " archivos; se importara el resto. Primero que falta: " + material.faltantes[0],
      true
    );
  }

  status.textContent = "Importando " + archivo.name + "...";
  const resultado = await processManifest(project, manifest);
  status.textContent = "Listo.";

  logToPanel(
    "--- " + archivo.name + ": " + resultado.ok.length + " importados, " +
      resultado.errores.length + " con error ---"
  );
}
```

- [ ] **Step 2: Conectar el botón en `index.html`**

Agregar `<script src="js/importarManifest.js"></script>` con los demás, y reemplazar el script inline final por:

```html
<script>
  logToPanel("Plugin cargado.");
  const boton = document.getElementById("importar");
  boton.disabled = false;
  boton.addEventListener("click", async () => {
    boton.disabled = true;
    try {
      await importarManifestDesdeArchivo();
    } catch (e) {
      logToPanel(e.message + " | " + e.stack, true);
      document.getElementById("status").textContent = "Listo.";
    } finally {
      boton.disabled = false;
    }
  });
</script>
```

El botón se deshabilita mientras corre para que un doble clic no lance dos importaciones encima de la misma.

- [ ] **Step 3: Preparar el archivo de prueba (la prueba en sí se difiere al Task 13)**

El explorador de archivos es un diálogo nativo de macOS: ningún script puede elegir el archivo. Esta verificación se hace con el usuario en el Task 13. Aquí solo se deja el archivo listo.

**Lo que sí se puede verificar solo, y hay que hacerlo ahora:** llamar directamente a `processManifest` con el manifest de abajo ya parseado (saltándose el explorador) y confirmar por autocheck que el clip queda bien. Así, si algo falla, no es culpa del diálogo.

Crear el archivo `~/Desktop/prueba-task9.json` (en el Escritorio a propósito: comprueba que el plugin lee de donde el usuario quiera, no de una carpeta fija):

```json
{
  "proyecto": "Prueba Task 9",
  "orientacion": "vertical",
  "clips": [
    {
      "orden": 1,
      "ruta": "<RAIZ-DEL-REPO>/TEST/20260804_PIB0589.MP4",
      "categoria_path": ["PruebaTask9"],
      "fps": 59.94005994005994,
      "in_frame": null,
      "out_frame": null,
      "flag": "none",
      "ruta_proxy": null
    }
  ]
}
```

Comprobar por autocheck que, procesando ese manifest, el clip queda dentro de `PruebaTask9` y el resultado reporta 1 importado y 0 errores.

- [ ] **Step 4: Verificar los casos feos**

Tres de los cuatro se comprueban solos, llamando a las funciones directamente (sin pasar por el diálogo). Registrarlos en el autocheck:

1. **Archivo inválido:** parsear un texto que no es JSON válido → el flujo devuelve el mensaje de archivo no válido y **no toca el proyecto** (confirmar que no aparecieron bins nuevos).
2. **Disco desconectado:** un manifest con rutas inexistentes (ej. `/Volumes/DiscoQueNoExiste/clip.MP4`) → `revisarMaterialDisponible` los reporta todos como faltantes y no se importa nada.
3. **Manifest sin clips:** un manifest con `"clips": []` → mensaje claro, sin tocar el proyecto.

**Se difiere al Task 13** (requiere el diálogo nativo o cerrar el proyecto a mano): el camino feliz completo con el explorador, el caso "cancelar sin elegir archivo", y el caso "sin proyecto abierto".

- [ ] **Step 5: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/importarManifest.js uxp-plugin/index.html
git commit -m "feat: boton para elegir e importar una clasificacion, con casos de error cubiertos"
```

---


### Task 10: Instalación sin UXP Developer Tools, y cómo se actualiza después

**Files:** ninguno (solo pasos manuales)

- [ ] **Step 1: Cerrar UDT antes de copiar**

Si UXP Developer Tools tiene cargado el plugin desde `uxp-plugin/` y además existe una copia instalada con el **mismo id**, Premiere puede quedarse con la equivocada. Descargar el plugin en UDT (Unload) y cerrar UDT antes de continuar.

- [ ] **Step 2: Copiar el plugin a la carpeta de plugins de Adobe**

```bash
mkdir -p ~/"Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1"
cp -R "<RAIZ-DEL-REPO>/uxp-plugin/"* ~/"Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1/"
```

El nombre de la carpeta es el id del manifest + guion bajo + **el major de la versión** (`1.0.0` → `_1`).

- [ ] **Step 3: Se difiere al Task 13 — verificar que Premiere lo detecta sin UDT**

Requiere reiniciar Premiere, lo cual tumba la conexión del CLI. Va en la sesión final con el usuario.

- [ ] **Step 5: Dejar escrito el procedimiento de actualización**

Crear `uxp-plugin/README.md` con el procedimiento exacto, porque se va a necesitar cada vez que el plugin cambie:

```markdown
# Instalar / actualizar el plugin

1. Cerrar Premiere.
2. Borrar la carpeta instalada:
   rm -rf ~/"Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1"
3. Volver a copiarla desde `uxp-plugin/` (ver Step 2 del Task 10 del plan).
4. Abrir Premiere. `Window > UXP Plugins > Clasificador de Video`.

Notas:
- Sobrescribir sin borrar deja archivos viejos que ya no existen en la version nueva.
- Si se sube el major de la version en `manifest.json`, cambia el nombre de la
  carpeta (`_1` -> `_2`) y hay que borrar la anterior a mano.
- No tener el plugin cargado en UXP Developer Tools al mismo tiempo que instalado:
  mismo id, dos copias, y Premiere puede tomar la equivocada.
```

- [ ] **Step 6: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/README.md
git commit -m "docs: procedimiento de instalacion y actualizacion del plugin"
```

---

### Task 11: Prueba de punta a punta con material real

La única prueba que se parece a un día de trabajo. Todo lo anterior se verificó pieza por pieza; esto verifica el conjunto.

**Files:** ninguno (solo verificación)

- [ ] **Step 1: Preparar el caso del nombre repetido**

Dos tarjetas distintas producen archivos con el mismo nombre. Simularlo:

```bash
mkdir -p "<RAIZ-DEL-REPO>/TEST/tarjeta2"
cp "<RAIZ-DEL-REPO>/TEST/20260804_PIB0588.MP4" \
   "<RAIZ-DEL-REPO>/TEST/tarjeta2/20260804_PIB0587.MP4"
```

Ahora existen dos archivos distintos llamados `20260804_PIB0587.MP4` en rutas diferentes.

- [ ] **Step 2: Armar el manifest de punta a punta**

En `~/Desktop/prueba-e2e.json`, con los cinco casos que importan: dos bins homónimos en ramas distintas, un clip sin clasificar, uno sin proxy, uno con proxy, y dos archivos con el mismo nombre.

```json
{
  "proyecto": "Prueba E2E",
  "orientacion": "vertical",
  "clips": [
    {
      "orden": 1,
      "ruta": "<RAIZ-DEL-REPO>/TEST/20260804_PIB0587.MP4",
      "categoria_path": ["Recamara 1", "Bano"],
      "fps": 59.94005994005994,
      "in_frame": 10,
      "out_frame": 90,
      "flag": "pick",
      "ruta_proxy": "<RAIZ-DEL-REPO>/TEST/20260804_PIB0587S03.MP4"
    },
    {
      "orden": 2,
      "ruta": "<RAIZ-DEL-REPO>/TEST/tarjeta2/20260804_PIB0587.MP4",
      "categoria_path": ["Recamara 2", "Bano"],
      "fps": 59.94005994005994,
      "in_frame": null,
      "out_frame": null,
      "flag": "reject",
      "ruta_proxy": null
    },
    {
      "orden": 3,
      "ruta": "<RAIZ-DEL-REPO>/TEST/20260804_PIB0589.MP4",
      "categoria_path": [],
      "fps": 59.94005994005994,
      "in_frame": 30,
      "out_frame": 200,
      "flag": "none",
      "ruta_proxy": null
    }
  ]
}
```

- [ ] **Step 3: Correr y verificar todo por autocheck**

Procesar ese manifest llamando directamente a `processManifest` (sin el diálogo) y registrar **cada punto** como comprobación:

1. Existen `Recamara 1 > Bano` y `Recamara 2 > Bano`, **cada uno con su propio clip** — no los dos en el mismo lado. Es la prueba de que las carpetas se comparan por identidad y no por nombre.
2. Los dos clips llamados `20260804_PIB0587.MP4` entraron **como dos clips distintos**, cada uno en su bin, con su `getMediaFilePath()` correspondiente. Es la prueba de la identidad por ruta.
3. El tercer clip quedó en `Sin clasificar`.
4. El primer clip: `hasProxy()` es `true` con la ruta correcta, color verde, marcas de in/out en 10 y 90.
5. El segundo: color rojo, `hasProxy()` es `false`, sin marcas.
6. El resultado reporta 3 importados, 0 con error.

**La rotación se difiere al Task 13** — la API no la expone.

- [ ] **Step 4: Verificar la reexportación (la corrección de todos los días)**

Editar el manifest en memoria: mover el primer clip a `["Cocina"]`. Volver a procesarlo **en el mismo proyecto**. Comprobar:

- El clip **se mudó** a `Cocina`; `Recamara 1 > Bano` quedó vacío.
- **No hay duplicados** de ningún clip (buscar por ruta en todo el árbol y confirmar que hay exactamente uno).
- El clip mudado **conserva** su proxy, su color y sus marcas de in/out.

- [ ] **Step 5: Limpiar el material de prueba**

```bash
rm -rf "<RAIZ-DEL-REPO>/TEST/tarjeta2"
```

Tirar también el proyecto de Premiere desechable.

---

### Task 12: Dejar preparado el módulo de secuencia (vacío)

El armado automático de la secuencia **no es de esta versión** (spec §12.1). Este task solo deja el lugar donde va a entrar, para que agregarlo después no obligue a destripar el código que organiza el proyecto.

**Files:**
- Create: `uxp-plugin/js/secuencia.js`

- [ ] **Step 1: Crear el módulo con su frontera definida**

```javascript
// Responsabilidad unica: construir la secuencia a partir de un manifest ya
// procesado. Vacio a proposito en la v1 -- el usuario decidio que el armado
// automatico no entra todavia (spec 12.1).
//
// Cuando se implemente:
// - El orden lo manda el manifest (campo `orden`), NO se decide aqui. Las
//   reglas de que cuarto va primero viven en la app externa.
// - `orientacion` y `fps` del manifest definen los ajustes de la secuencia.
// - Recibe los clips ya importados (los que devolvio processManifest), no
//   vuelve a importar nada.
async function construirSecuencia(project, manifest, clipsImportados) {
  return null; // sin implementar en la v1
}
```

- [ ] **Step 2: Cargarlo en `index.html`**

Agregar `<script src="js/secuencia.js"></script>`. **No** llamarlo desde ningún lado todavía.

- [ ] **Step 3: Verificar que no rompió nada**

Recargar el plugin, confirmar que carga sin errores y que el botón sigue funcionando igual.

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/secuencia.js uxp-plugin/index.html
git commit -m "chore: modulo de secuencia vacio, frontera lista para el armado automatico futuro"
```

---

### Task 13: Sesión de verificación con el usuario (la única que lo requiere)

**Todo lo anterior se construyó y se verificó solo.** Aquí se juntan las cuatro cosas que ninguna máquina puede comprobar. Son unos dos minutos en total. **Antes de convocar al usuario, confirmar que el autocheck reporta `fallidas: 0`** — no hacerle perder el tiempo con algo que ya se sabe roto.

Presentárselo como una lista corta, en orden, y esperar su respuesta en cada punto.

- [ ] **Punto 1: Rotación (el que decide todo)**

Pedirle que abra en el monitor de origen cualquiera de los clips verticales importados (`20260804_PIB0587` o `0588`) y confirme que **se ve derecho, no acostado**.

Si se ve acostado: detener todo. Es el problema que originó el proyecto y significa que el mecanismo de importación dejó de comportarse como en los spikes. Nada de lo demás importa hasta resolverlo.

- [ ] **Punto 2: El botón y el explorador de archivos**

Dejar preparado `~/Desktop/prueba-e2e.json` (el del Task 11) antes de pedirle nada. Luego pedirle:

1. Clic en "Importar clasificacion...", elegir ese archivo. Confirmar que el panel reporta los clips importados sin errores.
2. Clic otra vez y **cerrar el explorador sin elegir nada** → debe decir "Cancelado, no se eligio ningun archivo" y el botón debe quedar disponible otra vez.
3. Confirmar que `prueba-e2e.json` **sigue en el Escritorio con el mismo nombre** — el plugin no mueve ni renombra sus archivos.

- [ ] **Punto 3: Sin proyecto abierto**

Pedirle que cierre el proyecto en Premiere dejando el panel abierto, y dé clic en el botón → debe decir "No hay ningun proyecto abierto en Premiere", sin errores feos.

- [ ] **Punto 4: La instalación de verdad**

Después de copiar el plugin a la carpeta de plugins de Adobe (Task 10) y **descargarlo del CLI** (`plugin unload`), pedirle que reinicie Premiere y confirme que "Clasificador de Video" aparece en `Window > UXP Plugins` sin herramientas de desarrollo corriendo. Luego un último clic en el botón con el mismo archivo, para confirmar que la copia instalada funciona igual.

- [ ] **Punto 5: Apagar el arnés de auto-comprobación**

Ya no debe correr en el plugin que el usuario usa a diario: poner `AUTOCHECK_ACTIVO = false` en `uxp-plugin/js/autocheck.js`, volver a copiar el plugin instalado, y confirmar que el panel arranca limpio.

```bash
cd "<RAIZ-DEL-REPO>"
git add uxp-plugin/js/autocheck.js
git commit -m "chore: apagar el arnes de auto-comprobacion para uso diario"
```

- [ ] **Punto 6: Reportarle el resultado**

Decirle qué pasó en cada punto, sin adornos. Si algo falló, decirlo con el error exacto y qué sigue. Solo después de esto se puede dar el plugin por terminado.

---


### Task 14: Cierre — dejar la documentación al día

Sin esto, el siguiente que llegue (persona o IA) lee decisiones viejas como si fueran vigentes. Ya pasó una vez en este proyecto con el camino de xmeml.

**Files:**
- Modify: `docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md`
- Create: `docs/superpowers/HANDOFF-<fecha>-plugin-terminado.md`

- [ ] **Step 1: Actualizar el spec con lo que se aprendió**

Cualquier cosa que en la ejecución resultó distinta a lo escrito (firmas de la API, comportamientos de Premiere, decisiones que cambiaron a media marcha) se corrige en el spec. Si algo del spec quedó sin construir, decirlo explícitamente ahí.

- [ ] **Step 2: Escribir el handoff del estado real**

Qué quedó funcionando y verificado, qué no, qué sigue (la app externa PySide6, que no tiene plan todavía), y los riesgos abiertos.

- [ ] **Step 3: Cerrar lo obsoleto del repo**

El generador de xmeml en `src/clasificador_video/` y sus pruebas ya no son el camino. Decidir explícitamente: borrarlos o dejar una nota en su carpeta diciendo que quedaron obsoletos y por qué. No dejarlos ahí en silencio.

- [ ] **Step 4: Commit**

```bash
cd "<RAIZ-DEL-REPO>"
git add docs/ src/
git commit -m "docs: cierre del plan del plugin UXP, spec y handoff al dia"
```

---

## Self-review de este plan

- **Cobertura del spec:** §11 (formato del manifest) → Task 8. §12 (plugin: instalación y actualización, disparo por botón, dedupe, identidad de bins y clips, manejo de errores, feedback visible) → Tasks 0, 3, 7, 9, 10. §12.1 (preparado para el armado automático) → Tasks 8 y 12. §7 (in/out directo) → Task 5. §8 (label) → Task 4. §9 (proxy) → Task 6. §14 (detalle de `lockedAccess`) → Task 1. Verificación de conjunto → Task 11. Cierre documental → Task 14.
- **Lo que este plan NO cubre, a propósito:** la app externa PySide6 (ingest, reproductor, filmstrip, miniaturas y su rotación, exportar el manifest) — es un plan aparte que todavía no existe. Este plan asume que el manifest ya existe con el formato del Task 8. **La verificación de rotación de las miniaturas con ffmpeg (spec §13) es responsabilidad de ese plan**, no de éste.
- **Tampoco cubre** el armado automático de la secuencia: el Task 12 solo deja la frontera lista, sin implementarlo.
- **Placeholders:** el único "placeholder" intencional es `getFpsFromMedia` en el Task 7, y el Task 8 lo elimina explícitamente en el mismo plan — no queda placeholder sin resolver al final. `construirSecuencia` (Task 12) está vacía **por decisión**, no por olvido, y así queda documentado en el propio archivo.
- **Consistencia de tipos:** `runTransaction`, `resolveBinChain`, `importOrReuseClip`, `applyFlagLabel`, `applyInOut`, `attachProxyIfPresent`, `processManifest`, `revisarMaterialDisponible` se usan con la misma firma en todos los tasks donde aparecen.
- **Riesgos que este plan sí ataca de frente:** rotación (Tasks 3 y 11), bins homónimos en ramas distintas (Tasks 3 y 11), nombres de archivo repetidos entre tarjetas (Task 11), disco desconectado (Tasks 7 y 9), reexportación de una clasificación corregida (Tasks 3 y 11).
- **Riesgo que queda abierto:** la instalación por copia (Task 10) sigue sin probarse en vivo — es lo único del plan confirmado solo por documentación de Adobe. Se comprueba en el Task 13, con el usuario.
- **Interrupciones al usuario:** una sola, al final (Task 13), de unos dos minutos. Todo lo demás se verifica solo gracias al arnés del Task 0b y al manejo del plugin por línea de comandos. El estado inicial (Premiere abierto con un proyecto desechable) se pide una vez al empezar.
