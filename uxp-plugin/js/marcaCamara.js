// Las marcas de cámara -- "[SONY] ", "[POCKET] ", "[DRONE] "-- en el
// nombre de la carpeta de un cuarto en Premiere.
//
// POR QUE ES UNA SEÑAL APARTE DE LA CAMARA (`label.js`): el color del
// clip ya dice de que camara salio, mirando el nombre del ARCHIVO. Esto
// mira el nombre del BIN DE IMPORTACION -- la tanda con la que Bruno
// arrastro el material -- y solo sirve para esta marca. Las dos conviven
// sin tocarse.
//
// Nacio como marcaDron.js (spec 2026-09-18, marca [DRONE] sola, regla
// todo-o-nada) y se generalizo el mismo dia a tres camaras, con la spec
// de entrega a un editor externo §4: a diferencia de [DRONE] sola --que
// se apaga ante cualquier mezcla-- un cuarto con mas de una camara se
// marca con las dos, COMBINADAS, en el orden fijo Sony/Pocket/Drone.
//
// Logica pura: se prueba con `node uxp-plugin/pruebas/correr.js`.

const _MARCAS = [
  { palabra: "SONY", campo: "bin_sony" },
  { palabra: "POCKET", campo: "bin_pocket" },
  { palabra: "DRONE", campo: "bin_dron" },
];

// Quita solo una marca de cámara conocida --incluida una compuesta-- y solo
// si esta al inicio. Un nombre que Bruno haya escrito el mismo no se toca.
function sinMarcaDeCamara(nombre) {
  const s = String(nombre || "");
  const marca = /^\[(?:SONY|POCKET|DRONE)(?:\+(?:SONY|POCKET|DRONE))*\] /;
  return s.replace(marca, "");
}

// Las marcas que aplican a este cuarto, en el orden fijo Sony/Pocket/Drone.
function _marcasDelCuarto(clipsDelManifest, nombreDeCuarto) {
  return _MARCAS
    .filter(({ campo }) => _cuartoTieneAlgunClipDe(clipsDelManifest, nombreDeCuarto, campo))
    .map(({ palabra }) => palabra);
}

function _cuartoTieneAlgunClipDe(clipsDelManifest, nombreDeCuarto, campo) {
  return (clipsDelManifest || []).some(
    (c) => c && c.categoria_path && c.categoria_path[0] === nombreDeCuarto && c[campo] === true
  );
}

// Arma el nombre final de la carpeta: numero (si lo hay) + marca(s) (si
// aplican) + nombre del cuarto -- EN ESE ORDEN, pegado al nombre nunca
// antes del numero: "03. [SONY+DRONE] Cocina", no
// "[SONY+DRONE] 03. Cocina".
function nombreDelCuartoConMarca(nombreConNumero, nombreSinNumero, clipsDelManifest) {
  const marcas = _marcasDelCuarto(clipsDelManifest, nombreSinNumero);
  if (!marcas.length) return nombreConNumero;
  const numero = nombreConNumero.slice(
    0, nombreConNumero.length - nombreSinNumero.length);
  return numero + "[" + marcas.join("+") + "] " + nombreSinNumero;
}
