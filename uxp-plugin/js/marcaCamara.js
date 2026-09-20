// Las marcas de cámara -- "[SONY] ", "[POCKET] ", "[DRONE] "-- en el
// nombre de la carpeta de un cuarto O una unidad en Premiere.
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

// Las marcas que aplican a este PREFIJO de categoria_path -- un cuarto
// (["Cocina"] o ["Casa A", "Cocina"]) o una unidad sola (["Casa A"], que
// agrega la marca de TODOS los cuartos que tiene adentro).
function _marcasDelPrefijo(clipsDelManifest, prefijo) {
  return _MARCAS
    .filter(({ campo }) => _algunClipEmpiezaCon(clipsDelManifest, prefijo, campo))
    .map(({ palabra }) => palabra);
}

function _algunClipEmpiezaCon(clipsDelManifest, prefijo, campo) {
  return (clipsDelManifest || []).some((c) => {
    if (!c || !c.categoria_path || c[campo] !== true) return false;
    if (c.categoria_path.length < prefijo.length) return false;
    return prefijo.every((segmento, indice) => c.categoria_path[indice] === segmento);
  });
}

// Arma el nombre final de la carpeta: numero (si lo hay) + marca(s) (si
// aplican) + nombre -- EN ESE ORDEN, pegado al nombre nunca antes del
// numero: "03. [SONY+DRONE] Cocina", no "[SONY+DRONE] 03. Cocina".
//
// `prefijoDeCategoria` es el categoria_path (crudo, SIN numero ni marca)
// hasta este nivel: `["Cocina"]` para un cuarto sin unidad, `["Casa A",
// "Cocina"]` para un cuarto con unidad, o `["Casa A"]` para marcar la
// UNIDAD misma con la combinacion de todos sus cuartos. Si se omite, se
// asume `[nombreSinNumero]` -- el comportamiento de siempre.
function nombreDelCuartoConMarca(nombreConNumero, nombreSinNumero, clipsDelManifest, prefijoDeCategoria) {
  const prefijo = prefijoDeCategoria || [nombreSinNumero];
  const marcas = _marcasDelPrefijo(clipsDelManifest, prefijo);
  if (!marcas.length) return nombreConNumero;
  const numero = nombreConNumero.slice(
    0, nombreConNumero.length - nombreSinNumero.length);
  return numero + "[" + marcas.join("+") + "] " + nombreSinNumero;
}
