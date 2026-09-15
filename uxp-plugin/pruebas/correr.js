// Corre la logica pura del plugin desde el repo, sin Premiere y sin
// dependencias:
//
//     node uxp-plugin/pruebas/correr.js
//
// Los archivos del plugin no exportan nada --se cargan con <script src> y
// viven en el ambito global-- asi que aqui se leen y se evaluan en un
// contexto, que es lo mismo que hace el navegador. Sin build, sin npm.
//
// POR QUE ESTO Y NO EL ARNES DE `autocheck.js`: el arnes corre DENTRO de
// Premiere y esta apagado (`AUTOCHECK_ACTIVO = false`) desde que se termino
// de construir el plugin, asi que hoy sus doce casos de las marcas del
// nombre no corren nunca. Una comprobacion que solo corre cuando te acuerdas
// de prenderla no es una comprobacion. Lo que SI necesita Premiere --los
// bins, la red, el sistema de archivos de UXP-- se queda alla; esto es para
// lo que no.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const raiz = path.join(__dirname, "..");

// Solo archivos que NO hacen `require("premierepro")` ni tocan la red al
// cargarse. `estructura.js` entra porque de ahi sale el nombre de
// «02. Clip» y `caminoDelClip`, `numeroDeCuarto.js` porque es logica pura
// entera: poner, quitar y comparar el prefijo «NN. » de las carpetas, y
// `avance.js` porque tambien es logica pura entera: que pasos del guion ya
// estan montados, sin tocar el disco (eso vive en `avanceDisco.js`, que se
// queda afuera).
//
// Aqui entraban tambien `ordenSugerido.js`, `llave.js` y
// `cuartosDelProyecto.js`. Se fueron el 2026-09-14 con la pestana que
// preguntaba: la guia se arma en Clipify y sus casos viven ahora en
// `tests/test_guia.py`.
const ARCHIVOS = [
  "js/estructura.js",
  "js/numeroDeCuarto.js",
  "js/avance.js",
];

const contexto = vm.createContext({ console });

for (const archivo of ARCHIVOS) {
  const ruta = path.join(raiz, archivo);
  if (!fs.existsSync(ruta)) {
    console.error("Falta " + archivo + " -- no se puede correr nada.");
    process.exit(1);
  }
  vm.runInContext(fs.readFileSync(ruta, "utf8"), contexto, { filename: archivo });
}

const pruebas = require("./numeroDeCuarto.pruebas.js");
const casos = [].concat(
  pruebas(contexto),
  pruebas.carpetas(contexto),
  require("./avance.pruebas.js")(contexto)
);

let fallidas = 0;
for (const { nombre, fn } of casos) {
  let ok;
  let detalle;
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
