# Plugin UXP para Premiere — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el plugin UXP que vigila una carpeta de manifests JSON y organiza los clips dentro de Premiere Pro (bins anidados, in/out, color de etiqueta, proxy vinculado) usando la API de Premiere ya validada con clips reales en `uxp-test/`.

**Architecture:** Plugin UXP plano (HTML + JS, sin framework, sin build step — igual que `uxp-test/`), con módulos JS separados por responsabilidad: helpers de Premiere (bins/import/label/in-out/proxy), procesamiento de un manifest, vigilancia de carpeta, y una UI de estado simple dentro del panel.

**Tech Stack:** UXP (JavaScript), API `premierepro` (paquete `@adobe/premierepro`, ya confirmado disponible en Premiere Pro 26.3.0).

---

## Notas para quien ejecute este plan

- No hay corredor de pruebas automatizado para JS/UXP en este proyecto — la verificación de cada paso es manual: cargar el plugin en Premiere (vía UXP Developer Tools, carpeta `uxp-plugin/`) y confirmar el comportamiento descrito. Esto es intencional, no un hueco del plan: la API de Premiere solo se puede probar contra un Premiere real corriendo.
- Ya existe un plugin de prueba funcional en `uxp-test/` (`manifest.json`, `index.html`) que confirmó: import con rotación correcta, bins anidados, label, e in/out — todo junto, para 3 clips reales. Este plan construye el plugin de producción a partir de esos mismos patrones ya confirmados; no se re-derivan desde cero.
- Detalle crítico ya descubierto (no volver a perder tiempo en esto): `executeTransaction` **debe** ir envuelto en `project.lockedAccess(() => {...})`, si no, falla con "The script object is no longer valid."
- Clips de prueba reales disponibles en `TEST/` dentro de este mismo proyecto (`20260804_PIB0587.MP4`, `...0588.MP4`, `...0589.MP4`), y su proxy real en `TEST/20260804_PIB0587S03.MP4`.
- Carpetas de manifests: `~/Library/Application Support/ClasificadorVideo/pendientes/` y `.../procesados/`. Estas carpetas no existen todavía — el Task 0 las crea.

---

### Task 0: Scaffold del plugin

**Files:**
- Create: `uxp-plugin/manifest.json`
- Create: `uxp-plugin/index.html`
- Create: `uxp-plugin/js/log.js`

- [ ] **Step 1: Crear la carpeta base de datos compartidos**

```bash
mkdir -p ~/"Library/Application Support/ClasificadorVideo/pendientes"
mkdir -p ~/"Library/Application Support/ClasificadorVideo/procesados"
```

- [ ] **Step 2: Crear `uxp-plugin/manifest.json`**

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

- [ ] **Step 3: Crear `uxp-plugin/js/log.js`**

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

- [ ] **Step 4: Crear `uxp-plugin/index.html`**

```html
<div style="padding: 8px; font-family: sans-serif;">
  <h3>Clasificador de Video</h3>
  <div id="status">Esperando manifests...</div>
  <div id="log-list" style="margin-top: 8px; font-size: 12px; max-height: 400px; overflow-y: auto;"></div>
</div>
<script src="js/log.js"></script>
<script>
  logToPanel("Plugin cargado.");
</script>
```

- [ ] **Step 5: Verificar que carga en Premiere**

Abrir UXP Developer Tools → Add Plugin → carpeta `uxp-plugin/` → Load. En Premiere: `Window > UXP Plugins > Clasificador de Video`.
Expected: aparece el panel con el título y el mensaje "Plugin cargado." en la lista.

- [ ] **Step 6: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add uxp-plugin/
git commit -m "chore: scaffold del plugin UXP de produccion"
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
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
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
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add uxp-plugin/js/bins.js uxp-plugin/index.html
git commit -m "feat: resolver/crear cadena de bins anidados"
```

---

### Task 3: Importar o reusar un clip ya importado (evita duplicar en reexportaciones)

**Files:**
- Create: `uxp-plugin/js/importClip.js`

- [ ] **Step 1: Escribir la función**

`uxp-plugin/js/importClip.js`:

```javascript
// Si el clip (por ruta) ya existe en el proyecto, lo mueve al bin destino y
// lo devuelve sin reimportar. Si no existe, lo importa dentro de ese bin.
async function importOrReuseClip(project, targetFolder, filePath) {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const existingMatches = await premierepro.ProjectUtils
    ? null // placeholder, se resuelve abajo via ClipProjectItem
    : null;

  // Buscar en TODO el proyecto un ClipProjectItem cuyo media path coincida.
  const found = await findClipByPath(rootFolder, filePath);
  if (found) {
    const currentParent = await found.getParentBin();
    if (currentParent && currentParent.name !== targetFolder.name) {
      runTransaction(
        project,
        () => rootFolder.createMoveItemAction(found, targetFolder),
        "Mover clip existente"
      );
    }
    return found;
  }

  await project.importFiles([filePath], true, targetFolder, false);
  const itemsInBin = await targetFolder.getItems();
  const fileName = filePath.split("/").pop();
  const stem = fileName.replace(/\.[^.]+$/, "");
  return itemsInBin.find((i) => i.name === stem || i.name === fileName);
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

- [ ] **Step 2: Limpiar la variable sin uso**

Revisar el archivo despues de escribirlo: la constante `existingMatches` del Step 1 no se usa en ningun lado (era un intento inicial descartado). Borrar esas tres lineas antes de continuar:

```javascript
  const existingMatches = await premierepro.ProjectUtils
    ? null // placeholder, se resuelve abajo via ClipProjectItem
    : null;

```

- [ ] **Step 3: Cargarlo en `index.html`**

Agregar: `<script src="js/importClip.js"></script>`

- [ ] **Step 4: Verificar manualmente (dos corridas)**

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
    "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0588.MP4"
  );
  logToPanel("clip resuelto: " + (clip ? clip.name : "NO ENCONTRADO"));
});
```

Primera corrida: recargar, clic, confirmar en Premiere que se importó el clip dentro de `PruebaTask3`.
Segunda corrida (sin reiniciar Premiere ni el plugin): clic otra vez, confirmar en el panel el mismo log y en Premiere que **no hay un segundo clip duplicado** — sigue habiendo solo uno dentro de `PruebaTask3`.

Quitar el `addEventListener` de prueba.

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
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
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
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
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add uxp-plugin/js/inOut.js uxp-plugin/index.html
git commit -m "feat: aplicar in/out directo sobre el clip maestro"
```

---

### Task 6: Adjuntar proxy

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
    "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0587.MP4"
  );
  const ok = await attachProxyIfPresent(
    clip,
    "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0587S03.MP4"
  );
  logToPanel("attachProxy resultado: " + ok);
});
```

Recargar, clic, confirmar en Premiere (columna "Proxy" en el panel de proyecto, o ícono de proxy en el clip) que el proxy quedó adjunto.

Quitar el `addEventListener` de prueba.

- [ ] **Step 4: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add uxp-plugin/js/proxy.js uxp-plugin/index.html
git commit -m "feat: adjuntar proxy al clip cuando el manifest lo trae"
```

---

### Task 7: Procesar un manifest completo (une los Tasks 2-6, tolerante a errores por clip)

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

// Placeholder de fps: se reemplaza en el Task 9 por el fps real que ya viene
// en el manifest (ver Nota abajo) en vez de leerlo de Media.
async function getFpsFromMedia(media) {
  return 30;
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
        ruta: "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0587.MP4",
        categoria_path: ["PruebaTask7", "Bano"],
        in_frame: 10,
        out_frame: 90,
        flag: "pick",
        ruta_proxy: "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0587S03.MP4",
      },
      {
        ruta: "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/no-existe.MP4",
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
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
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

De aquí en adelante, cada clip del manifest debe incluir `"fps"` (numero, ej. `59.94005994005994`), tomado directo de lo que la app externa ya obtiene con `ffprobe`. Formato completo actualizado:

```json
{
  "proyecto": "Casa Jardin",
  "clips": [
    {
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

- [ ] **Step 3: Verificar que el plugin sigue cargando sin errores de sintaxis**

Recargar el plugin en UDT, confirmar que no hay errores en la consola al cargar (no hace falta repetir la prueba completa del Task 7, solo confirmar que no quedó JS roto).

- [ ] **Step 4: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add uxp-plugin/js/processManifest.js
git commit -m "refactor: el fps del clip viene del manifest, no se infiere en el plugin"
```

---

### Task 9: Vigilancia de la carpeta de pendientes

**Files:**
- Create: `uxp-plugin/js/watcher.js`
- Modify: `uxp-plugin/index.html`

- [ ] **Step 1: Escribir el watcher**

`uxp-plugin/js/watcher.js`:

```javascript
const PENDIENTES_PATH = "/Users/brunogutierrez/Library/Application Support/ClasificadorVideo/pendientes";
const PROCESADOS_PATH = "/Users/brunogutierrez/Library/Application Support/ClasificadorVideo/procesados";
const POLL_INTERVAL_MS = 3000;

let watcherRunning = false;

async function startWatcher(project) {
  if (watcherRunning) return;
  watcherRunning = true;
  pollPendientes(project);
}

async function pollPendientes(project) {
  const uxpFs = require("uxp").storage.localFileSystem;

  try {
    const pendientesFolder = await uxpFs.getEntryWithUrl("file://" + PENDIENTES_PATH);
    const entries = await pendientesFolder.getEntries();
    const manifiestos = entries.filter((e) => e.isFile && e.name.endsWith(".json"));

    for (const entry of manifiestos) {
      await procesarArchivoManifest(project, entry);
    }
  } catch (e) {
    logToPanel("Error revisando carpeta de pendientes: " + e.message, true);
  }

  setTimeout(() => pollPendientes(project), POLL_INTERVAL_MS);
}

async function procesarArchivoManifest(project, entry) {
  const uxpFs = require("uxp").storage.localFileSystem;

  const contenido = await entry.read();
  let manifest;
  try {
    manifest = JSON.parse(contenido);
  } catch (e) {
    logToPanel(entry.name + ": JSON invalido, se ignora (" + e.message + ")", true);
    return;
  }

  document.getElementById("status").textContent = "Procesando " + entry.name + "...";
  const resultado = await processManifest(project, manifest);

  const tieneErrores = resultado.errores.length > 0;
  const nuevoNombre = entry.name.replace(/\.json$/, tieneErrores ? "-con-errores.json" : ".json");

  const procesadosFolder = await uxpFs.getEntryWithUrl("file://" + PROCESADOS_PATH);
  await entry.moveTo(procesadosFolder, { newName: nuevoNombre });

  document.getElementById("status").textContent = "Esperando manifests...";
  logToPanel(
    entry.name + " procesado: " + resultado.ok.length + " ok, " + resultado.errores.length + " con error"
  );
}
```

- [ ] **Step 2: Arrancar el watcher al cargar el panel**

En `uxp-plugin/index.html`, reemplazar el script inline final:

```html
<script>
  logToPanel("Plugin cargado.");
</script>
```

por:

```html
<script>
  logToPanel("Plugin cargado.");
  (async () => {
    const premierepro = require("premierepro");
    const project = await premierepro.Project.getActiveProject();
    if (project) {
      startWatcher(project);
      logToPanel("Vigilando carpeta de pendientes.");
    } else {
      logToPanel("No hay proyecto activo en Premiere.", true);
    }
  })();
</script>
```

Y agregar `<script src="js/watcher.js"></script>` antes de ese bloque.

- [ ] **Step 3: Verificar manualmente con un manifest real dejado en la carpeta**

Crear a mano el archivo `~/Library/Application Support/ClasificadorVideo/pendientes/prueba-task9.json` con:

```json
{
  "proyecto": "Prueba Task 9",
  "clips": [
    {
      "ruta": "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0589.MP4",
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

Recargar el plugin, esperar hasta 3 segundos sin hacer nada. Confirmar:
- El clip aparece organizado en Premiere, dentro de `PruebaTask9`.
- El archivo `prueba-task9.json` ya no está en `pendientes/`, sino en `procesados/prueba-task9.json`.
- El panel muestra el log de "procesado: 1 ok, 0 con error".

- [ ] **Step 4: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add uxp-plugin/js/watcher.js uxp-plugin/index.html
git commit -m "feat: vigilancia automatica de la carpeta de manifests pendientes"
```

---

### Task 10: Instalación sin UXP Developer Tools

**Files:** ninguno (solo pasos manuales)

- [ ] **Step 1: Empaquetar/copiar el plugin**

```bash
mkdir -p ~/"Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1"
cp -R "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/uxp-plugin/"* ~/"Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1/"
```

- [ ] **Step 2: Verificar que Premiere lo detecta sin UDT**

Cerrar UXP Developer Tools. Reiniciar Premiere. Ir a `Window > UXP Plugins` — confirmar que "Clasificador de Video" aparece ahí sin haber usado UDT en esta sesión.

- [ ] **Step 3: Repetir la prueba del Task 9** (dejar un manifest en `pendientes/`) para confirmar que la instalación por copia funciona igual que vía UDT.

- [ ] **Step 4: Documentar el resultado**

Si funciona: no hace falta commit de código, este task es una verificación de despliegue. Si algo falla, anotar el error exacto como un nuevo task de corrección antes de dar por cerrado el plan.

---

## Self-review de este plan

- **Cobertura del spec:** §11 (formato del manifest) → Task 8. §12 (plugin: instalación, vigilancia, dedupe, manejo de errores, feedback visible) → Tasks 0, 3, 7, 9, 10. §7 (in/out directo) → Task 5. §8 (label) → Task 4. §9 (proxy) → Task 6. §14 (detalle de `lockedAccess`) → Task 1. Lo que este plan **no** cubre a propósito: la app externa PySide6 (ingest, reproductor, filmstrip, exportar el manifest) — es un plan aparte, este plan asume que el manifest ya existe con el formato del Task 8.
- **Placeholders:** el único "placeholder" intencional es `getFpsFromMedia` en el Task 7, y el Task 8 lo elimina explícitamente en el mismo plan — no queda placeholder sin resolver al final del plan completo.
- **Consistencia de tipos:** `runTransaction`, `resolveBinChain`, `importOrReuseClip`, `applyFlagLabel`, `applyInOut`, `attachProxyIfPresent`, `processManifest` se usan con la misma firma en todos los tasks donde aparecen.
