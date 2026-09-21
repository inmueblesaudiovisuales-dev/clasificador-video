// Las marcas de cámara -- "[SONY] ", "[POCKET] ", "[DRONE] "-- en el
// nombre de la carpeta de un cuarto O una unidad en Premiere, y también en
// el nombre de cada clip (ver `nombre.js`).
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
// DESDE EL 2026-09-21 LA MARCA VA AL FINAL DEL NOMBRE del cuarto
// («03. Cocina [SONY+DRONE]», no «03. [SONY+DRONE] Cocina»), para que el
// cuarto se lea primero. Ver
// docs/superpowers/specs/2026-09-21-nombre-de-clip-en-premiere-design.md.
//
// Logica pura: se prueba con `node uxp-plugin/pruebas/correr.js`.

const _MARCAS = [
  { palabra: "SONY", campo: "bin_sony" },
  { palabra: "POCKET", campo: "bin_pocket" },
  { palabra: "DRONE", campo: "bin_dron" },
];

const _MARCA_CONOCIDA = "(?:SONY|POCKET|DRONE)(?:\\+(?:SONY|POCKET|DRONE))*";

// Quita solo una marca de cámara conocida --incluida una compuesta-- y solo
// si esta al inicio O al final. Un nombre que Bruno haya escrito el mismo no
// se toca.
//
// Las DOS posiciones a proposito: la marca vive al final desde el
// 2026-09-21, pero una carpeta de una importacion anterior la trae al
// inicio. Si no se quitaran las dos, esa carpeta se leeria como otro cuarto
// y Premiere le crearia una segunda -- la familia de bug del 2026-08-22.
function sinMarcaDeCamara(nombre) {
  const s = String(nombre || "");
  return s
    .replace(new RegExp("^\\[" + _MARCA_CONOCIDA + "\\] "), "")
    .replace(new RegExp(" \\[" + _MARCA_CONOCIDA + "\\]$"), "");
}

// Las marcas que aplican a este PREFIJO de categoria_path -- un cuarto
// (["Cocina"] o ["Casa A", "Cocina"]) o una unidad sola (["Casa A"], que
// agrega la marca de TODOS los cuartos que tiene adentro).
function _marcasDelPrefijo(clipsDelManifest, prefijo) {
  return _MARCAS
    .filter(({ campo }) => _algunClipEmpiezaCon(clipsDelManifest, prefijo, campo))
    .map(({ palabra }) => palabra);
}

// La marca ya armada ("SONY", "SONY+DRONE", "SONY+POCKET+DRONE") o "" si no
// hay ninguna camara reconocible. La usan el nombre de la carpeta y el del
// clip, para que los dos digan exactamente lo mismo.
function marcaDeCamaraDelPrefijo(clipsDelManifest, prefijo) {
  const marcas = _marcasDelPrefijo(clipsDelManifest, prefijo);
  return marcas.length ? marcas.join("+") : "";
}

function _algunClipEmpiezaCon(clipsDelManifest, prefijo, campo) {
  return (clipsDelManifest || []).some((c) => {
    if (!c || !c.categoria_path || c[campo] !== true) return false;
    if (c.categoria_path.length < prefijo.length) return false;
    return prefijo.every((segmento, indice) => c.categoria_path[indice] === segmento);
  });
}

// Arma el nombre final de la carpeta: numero (si lo hay) + nombre + marca(s)
// (si aplican) -- EN ESE ORDEN, la marca al final: "03. Cocina [SONY+DRONE]".
//
// `prefijoDeCategoria` es el categoria_path (crudo, SIN numero ni marca)
// hasta este nivel: `["Cocina"]` para un cuarto sin unidad, `["Casa A",
// "Cocina"]` para un cuarto con unidad, o `["Casa A"]` para marcar la
// UNIDAD misma con la combinacion de todos sus cuartos. Si se omite, se
// asume `[nombreSinNumero]` -- el comportamiento de siempre.
function nombreDelCuartoConMarca(nombreConNumero, nombreSinNumero, clipsDelManifest, prefijoDeCategoria) {
  const prefijo = prefijoDeCategoria || [nombreSinNumero];
  const marca = marcaDeCamaraDelPrefijo(clipsDelManifest, prefijo);
  if (!marca) return nombreConNumero;
  return nombreConNumero + " [" + marca + "]";
}
