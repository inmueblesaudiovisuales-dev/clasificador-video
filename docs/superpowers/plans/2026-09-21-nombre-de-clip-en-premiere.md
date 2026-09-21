# El nombre de cada clip en Premiere — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que al importar con el plugin cada clip se llame
`[símbolo ]Cuarto NN [CAMARA]` (sin el nombre del archivo), y que la marca
de cámara de la carpeta del cuarto pase al final: `NN. Cuarto [CAMARA]`.

**Architecture:** Todo el cambio vive del lado del plugin (JS puro, sin
build). El manifiesto y Clipify no cambian: el plugin ya recibe
`categoria_path`, `orden`, `flag` y `bin_sony`/`bin_pocket`/`bin_dron`, y con
eso calcula el nombre. La marca de cámara (`marcaCamara.js`) se reusa para el
clip y cambia de posición en la carpeta. La numeración secuencial es una
función pura sobre la lista de clips, en el orden del manifiesto.

**Tech Stack:** JavaScript plano (UXP), el corredor de pruebas de node
(`uxp-plugin/pruebas/correr.js`). Python solo para confirmar que la suite
sigue verde (no se toca).

Spec: `docs/superpowers/specs/2026-09-21-nombre-de-clip-en-premiere-design.md`

---

## Antes de empezar

Comandos desde la raíz del repo:
`/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO`.

Pruebas del plugin: `node uxp-plugin/pruebas/correr.js`.

---

### Task 1: La marca de cámara, al final del nombre del cuarto

**Files:**
- Modify: `uxp-plugin/js/marcaCamara.js`
- Modify: `uxp-plugin/pruebas/marcaCamara.pruebas.js`
- Modify: `uxp-plugin/pruebas/numeroDeCuarto.pruebas.js`

- [ ] **Step 1: Escribir las pruebas que fallan**

En `marcaCamara.pruebas.js`, cambiar los resultados esperados al orden nuevo
(`NN. Cuarto [CAMARA]`) y agregar los casos de `marcaDeCamaraDelPrefijo` y de
la transición:

```javascript
// un cuarto solo de Sony -> "03. Cocina [SONY]"
// Sony + Drone -> "03. Cocina [SONY+DRONE]"
// las tres -> "03. Cocina [SONY+POCKET+DRONE]"
// sin cámara -> "03. Cocina"
// unidad -> "Casa A [SONY+DRONE]"
// cuarto en unidad -> "01. Cocina [SONY]"
// sinMarcaDeCamara("Cocina [SONY+DRONE]") -> "Cocina"
// sinMarcaDeCamara("[SONY] Cocina") -> "Cocina"   (formato viejo, transición)
// marcaDeCamaraDelPrefijo(clips, ["Cocina"]) -> "SONY"
// marcaDeCamaraDelPrefijo([], ["Cocina"]) -> ""
```

En `numeroDeCuarto.pruebas.js`, cambiar los dos casos de `[DRONE]` al orden
nuevo:

```javascript
ctx.esElMismoCuarto("02. Aerea [DRONE]", "04. Aerea") === true
ctx.esElMismoCuarto("Aerea [DRONE]", "Aerea") === true
```

- [ ] **Step 2: Correr y ver fallar**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: FALLO en los casos de la marca (el orden viejo ya no coincide).

- [ ] **Step 3: Implementar**

En `marcaCamara.js`:

- `sinMarcaDeCamara` quita la marca **al inicio o al final** (la del final es
  la nueva; la del inicio se sigue quitando para no duplicar carpetas de una
  importación anterior).
- `nombreDelCuartoConMarca` devuelve `nombreConNumero + " [CAMARA]"`.
- Exponer `marcaDeCamaraDelPrefijo(clipsDelManifest, prefijo)` → `"SONY+DRONE"`
  o `""`, para que el nombre del clip use la misma marca.

- [ ] **Step 4: Correr y ver pasar**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todas `OK`, `0 fallidas`.

- [ ] **Step 5: Commit**

```
La marca de cámara de la carpeta pasa al final del nombre

De «03. [SONY+DRONE] Cocina» a «03. Cocina [SONY+DRONE]», para que el
cuarto se lea primero. sinMarcaDeCamara quita la marca de las dos
posiciones para que una carpeta de una importación anterior no se lea
como otro cuarto. Se expone marcaDeCamaraDelPrefijo para reusarla en
el nombre del clip.
```

---

### Task 2: El nombre del clip — lógica pura

**Files:**
- Modify: `uxp-plugin/js/nombre.js`
- Create: `uxp-plugin/pruebas/nombre.pruebas.js`
- Modify: `uxp-plugin/pruebas/correr.js`

- [ ] **Step 1: Escribir la prueba que falla**

`nombre.pruebas.js` con casos de: número a dos dígitos, nombre con pick,
destacado, reject, sin símbolo, sin cámara, y numeración por cuarto en el
orden del manifiesto (dos cuartos y una unidad con cuarto del mismo nombre).

- [ ] **Step 2: Correr y ver fallar**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: falla al arrancar con `Falta js/nombre.js` o con las funciones
nuevas sin definir.

- [ ] **Step 3: Implementar**

En `nombre.js`, agregar `numeroDeClip(n)`, `nombreDeClip(cuarto, numero,
marcaDeCamara, flag)` y `numerosDeClip(clips)` (contador por
`JSON.stringify(categoria_path)`); reemplazar `applyFlagPrefix` por
`aplicarNombreDeClip(project, clipItem, cuarto, numero, marcaDeCamara, flag)`
que recalcula el nombre entero (idempotente por construcción).

- [ ] **Step 4: Registrar `nombre.js` en el corredor**

En `correr.js`, agregar `"js/nombre.js"` a `ARCHIVOS` y
`require("./nombre.pruebas.js")(contexto)` a `casos`.

- [ ] **Step 5: Correr y ver pasar**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todas `OK`, `0 fallidas`.

- [ ] **Step 6: Commit**

```
Armar el nombre completo de cada clip

Símbolo + cuarto + número por cuarto + [CAMARA], recalculado entero
desde el manifiesto. Se va el prefijo sobre el nombre del archivo: el
clip ya no lo muestra. Lógica pura con sus casos en nombre.pruebas.js.
```

---

### Task 3: Conectar el nombre al importar

**Files:**
- Modify: `uxp-plugin/js/processManifest.js`
- Modify: `uxp-plugin/js/bins.js` (comentario)

- [ ] **Step 1: Implementar**

En `processManifest.js`, calcular `numerosDeClip(manifest.clips)` antes del
bucle, recorrer con índice, y reemplazar `applyFlagPrefix(...)` por
`aplicarNombreDeClip(...)` pasando cuarto, número, marca de cámara
(`marcaDeCamaraDelPrefijo(manifest.clips, categoryPath)`) y flag.

- [ ] **Step 2: Actualizar el comentario de `bins.js`**

Donde dice que el método de renombrar se busca «igual que `applyFlagPrefix`»,
decir `aplicarNombreDeClip`.

- [ ] **Step 3: Correr y ver pasar**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todas `OK`, `0 fallidas`.

- [ ] **Step 4: Commit**

```
Nombrar cada clip al importar en Premiere

processManifest.js numera por cuarto y arma el nombre con
aplicarNombreDeClip. No hay forma de probarlo sin Premiere; la
verificación visual queda para Bruno.
```

---

### Task 4: Corrida final y nota de la spec vieja

**Files:**
- Modify: `docs/superpowers/specs/2026-09-18-entrega-a-editor-externo-design.md`
- Modify: `docs/superpowers/specs/2026-09-18-marca-drone-en-carpetas-design.md`

- [ ] **Step 1: Suite de Python**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS completo.

- [ ] **Step 2: Pruebas de node**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todas `OK`, `0 fallidas`.

- [ ] **Step 3: Nota en las dos specs viejas**

Agregar al inicio de cada una una línea: la marca de cámara pasa al final del
nombre, ver spec del 2026-09-21. El conjunto de cámaras y la regla de
combinación no cambian.

- [ ] **Step 4: `git status` limpio y commit**

```
Anotar el cambio de orden de la marca de cámara en las specs viejas
```

---

### Task 5: Verificación visual real en Premiere (la hace Bruno)

`processManifest.js` no corre sin Premiere. Antes de dar la entrega por
buena, Bruno importa un manifiesto de prueba y confirma a ojo, en el panel de
proyecto:

- Un clip marcado: `✓ Cocina 01 [SONY]`.
- Un clip sin marcar: `Alberca 04 [SONY]` (sin símbolo).
- Un cuarto mezclado: `[SONY+DRONE]`.
- La carpeta: `03. Cocina [SONY+DRONE]`.
- Reimportar el mismo manifiesto no acumula ni duplica.
