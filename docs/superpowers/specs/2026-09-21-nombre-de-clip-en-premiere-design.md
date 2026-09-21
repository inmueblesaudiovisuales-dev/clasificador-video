# El nombre de cada clip en Premiere — diseño

*(Spec del 2026-09-21. Sale de la petición de Bruno: al importar con el
plugin, cada clip debe llevar cuarto, número y cámara en su propio nombre,
no solo en el de la carpeta.)*

## 1. De dónde sale

Hoy, al armar el proyecto en Premiere:

- La **carpeta** del cuarto se llama `03. [SONY+DRONE] Cocina` — número de
  la guía, marca de cámara y nombre.
- Cada **clip** se llama solo con su símbolo de estado y el nombre del
  archivo original: `✓ C0001.MP4`.

Bruno quiere que el clip también diga qué es, para que en la lista del
proyecto (y en la entrega a un editor externo) se entienda sin abrir la
carpeta. Y quiere que la cámara vaya **después** del cuarto, no antes.

## 2. El formato

### Clip

```
[símbolo ]Cuarto NN [CAMARA]
```

- **símbolo** — `✓ ` pick, `★ ` destacado, `✕ ` reject. Un clip sin
  marcar (`none`) **no lleva símbolo**: empieza con el cuarto.
- **Cuarto** — el nombre del cuarto tal cual lo escribió Bruno, sin
  número. Es el último segmento de `categoria_path` (el mismo que ya usa
  la carpeta).
- **NN** — número secuencial **dentro del cuarto**, dos dígitos (`01`,
  `02`, …, `10`). Ver §3.
- **`[CAMARA]`** — **siempre**, aunque el cuarto sea de una sola cámara.
  Misma regla y misma fuente que la marca de la carpeta de hoy
  (`marcaCamara.js`): combinada en orden fijo `SONY`, `POCKET`, `DRONE`.
  Ver §4.

El **nombre del archivo original ya no aparece** en el nombre del clip.
El archivo sigue siendo el mismo en disco —solo cambia cómo se llama el
item dentro de Premiere—, pero el nombre del clip ya no lo dice.

Ejemplos:

| flag | cuarto | número | cámaras | nombre del clip |
|---|---|---|---|---|
| pick | Cocina | 1 | Sony | `✓ Cocina 01 [SONY]` |
| destacado | Recámara 2 | 3 | Sony + dron | `★ Recámara 2 03 [SONY+DRONE]` |
| reject | Baño | 2 | Pocket | `✕ Baño 02 [POCKET]` |
| none | Alberca | 4 | Sony | `Alberca 04 [SONY]` |

### Carpeta

Cambia **solo el orden** de la marca de cámara: hoy va antes del cuarto y
pasa a ir después, para que el cuarto se lea primero (igual que en el
clip).

- Hoy: `03. [SONY+DRONE] Cocina`
- Nuevo: `03. Cocina [SONY+DRONE]`

El número de la carpeta sigue siendo el de la guía (posición del cuarto
en el guion), que es distinto del número del clip.

## 3. El número secuencial

- Es **por cuarto**: dentro de Cocina van `01`, `02`, `03`; dentro de
  Habitaciones empieza otra vez en `01`.
- El orden es el **orden del manifiesto** (el mismo en que Bruno acomodó
  los clips en la hoja). Es determinista y no hace falta un dato nuevo.
- Dos dígitos; si un cuarto pasa de 99 clips, el número crece a tres
  dígitos sin romper nada (`conNumero` ya hace esto para las carpetas).
- Los clips que caen en «Sin clasificar» (sin `categoria_path`) se
  numeran aparte, como si «Sin clasificar» fuera un cuarto más.

## 4. La cámara

- La fuente es la **tanda de importación** (`bin_sony`, `bin_pocket`,
  `bin_dron` del manifiesto), la misma que ya alimenta la marca de la
  carpeta. Así el nombre del clip y el de su carpeta nunca dicen cosas
  distintas.
- La cámara del clip **no** reemplaza a la etiqueta de color: el color
  sigue saliendo del campo `camara` (el nombre del archivo) y es un canal
  aparte, como ya está documentado en `label.js`.
- Si el clip no trae ninguna de las tres cámaras reconocibles, se trata
  como hasta hoy: no suma ni resta, y si ningún clip del cuarto tiene
  cámara, el cuarto no lleva marca.

## 5. Qué cambia en el código

- **`nombre.js`** — `applyFlagPrefix` se reemplaza por una función que
  arma el nombre completo del clip: símbolo + cuarto + número + cámara.
  El nombre se **recalcula entero** desde el manifiesto cada vez, así que
  volver a correr la importación no acumula (`✓ ✓ Cocina 03 Cocina 03` no
  puede pasar). A cambio, un renombre manual de un clip se pierde al
  reimportar; ver §7.
- **`processManifest.js`** — le pasa al nombre del clip el cuarto, el
  número (calculado por cuarto, en el orden del manifiesto) y la cámara
  del prefijo, además del flag.
- **`marcaCamara.js`** — `nombreDelCuartoConMarca` pone la marca **al
  final**: `numero + cuarto + " [CAMARA]"`. `sinMarcaDeCamara` pasa a
  quitar la marca del **final** en vez del inicio, y `esElMismoCuarto`
  (en `numeroDeCuarto.js`) sigue comparando el cuarto sin número ni
  marca.
- **Pruebas** — se actualizan `marcaCamara.pruebas.js`,
  `numeroDeCuarto.pruebas.js` y `processManifest.pruebas.js`, y se agrega
  `nombre.pruebas.js` con los casos del formato del clip, cargado desde
  `pruebas/correr.js`.

## 6. Lo que NO cambia

- **Clipify y el manifiesto, nada.** El plugin calcula el nombre con lo
  que ya viaja (`categoria_path`, `orden`, `flag`, `bin_*`). No hay campo
  nuevo ni migración.
- La estructura de carpetas del proyecto, salvo el orden de la marca.
- La etiqueta de color por cámara de cada clip.
- El número y el nombre de la carpeta del cuarto, salvo el orden de la
  marca.

## 7. Riesgos

- **Se pierde el nombre del archivo en Premiere.** Para reencontrar el
  original hay que ver la ruta del medio, no el nombre. Es una pérdida
  asumida a cambio de que el clip se explique solo.
- **Un renombre manual se pisa.** Hoy el plugin respeta lo que Bruno
  escribió después del símbolo; con el nombre recalculado entero, una
  reimportación devuelve el nombre de fábrica. Aceptado: el nombre del
  clip ahora es un dato generado, no algo que se edite a mano.
- **Dos cuartos con el mismo nombre en unidades distintas** producen
  nombres de clip repetidos (`Cocina 01` en dos casas). El nombre de la
  carpeta sí los distingue. No se resuelve ahora; se anota por si
  molesta.

## 8. Cómo se comprueba

- `node uxp-plugin/pruebas/correr.js` — casos de: símbolo por flag
  (incluido sin símbolo), número por cuarto, cámara siempre presente,
  combinación de cámaras, clip sin cámara reconocible, y el nuevo orden
  del nombre de carpeta.
- **Verificación visual real en Premiere** (regla de `CLAUDE.md`): correr
  el plugin con un manifiesto de prueba y leer los nombres en el panel de
  proyecto, confirmando clip y carpeta.

## 9. Estado

**Diseñado con Bruno el 2026-09-21, sin construir nada.** Falta el plan
de implementación y la construcción con TDD.

*(Nota de alcance: esta spec cambia el orden de la marca de cámara que
había fijado `2026-09-18-entrega-a-editor-externo-design.md` §4 y
`2026-09-18-marca-drone-en-carpetas-design.md` — la marca pasa al final
del nombre del cuarto. El conjunto de cámaras y la regla de combinación
siguen igual.)*
