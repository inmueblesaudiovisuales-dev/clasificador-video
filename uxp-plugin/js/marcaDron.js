// La marca "[DRONE] " en el nombre de la carpeta de un cuarto en Premiere.
//
// POR QUE ES UNA SEÑAL APARTE DE LA CAMARA (`label.js`): el color del clip
// ya dice de que camara salio, mirando el nombre del ARCHIVO. Esto mira el
// nombre del BIN DE IMPORTACION -- la tanda con la que Bruno arrastro el
// material -- y solo sirve para esta marca. Las dos conviven sin tocarse.
//
// Logica pura: se prueba con `node uxp-plugin/pruebas/correr.js`.
//
// Spec: docs/superpowers/specs/2026-09-18-marca-drone-en-carpetas-design.md

const MARCA_DRONE = "[DRONE] ";

// Quita SOLO la marca que este modulo pone, y solo si esta al inicio. Un
// nombre que Bruno haya escrito el mismo no es nuestro y no se toca. Mismo
// criterio que las marcas de estado en `nombre.js`.
function sinMarcaDron(nombre) {
  const s = String(nombre || "");
  return s.indexOf(MARCA_DRONE) === 0 ? s.slice(MARCA_DRONE.length) : s;
}

// Si TODOS los clips de ese cuarto vinieron de un bin cuyo nombre dice
// "dron" (`bin_dron` en el manifiesto, ver marca_dron.py del lado de la
// app). Bruno pidio la regla estricta a proposito (spec §3): un solo clip
// que no venga de un bin de dron y el cuarto entero se queda sin marca.
//
// Un cuarto vacio -- sin clips de ese nombre en ESTE manifiesto -- no
// cuenta: no hay de donde sacar una respuesta.
function cuartoEsDeDron(clipsDelManifest, nombreDeCuarto) {
  const delCuarto = (clipsDelManifest || []).filter(
    (c) => c && c.categoria_path && c.categoria_path[0] === nombreDeCuarto
  );
  if (!delCuarto.length) return false;
  return delCuarto.every((c) => c.bin_dron === true);
}

// Arma el nombre final de la carpeta: numero (si lo hay) + marca [DRONE]
// (si aplica) + nombre del cuarto -- EN ESE ORDEN. Bruno la pidio pegada al
// nombre, nunca antes del numero: "03. [DRONE] Cocina", no
// "[DRONE] 03. Cocina" (spec §4).
//
// `nombreConNumero` es lo que da `caminoDelClip`/`conNumero`: el nombre del
// cuarto con su "NN. " al frente, o el nombre tal cual si no hay guia
// aceptada. `nombreSinNumero` es `categoryPath[0]`, el nombre del cuarto
// como esta en el manifiesto -- SIEMPRE es el final de `nombreConNumero`,
// porque `conNumero` no hace mas que anteponerle el numero. Por eso basta
// con cortar esa cola para saber cual es el prefijo numerico, sin tener que
// volver a parsearlo.
function nombreDelCuartoConMarca(nombreConNumero, nombreSinNumero, clipsDelManifest) {
  if (!cuartoEsDeDron(clipsDelManifest, nombreSinNumero)) return nombreConNumero;
  const numero = nombreConNumero.slice(
    0, nombreConNumero.length - nombreSinNumero.length);
  return numero + MARCA_DRONE + nombreSinNumero;
}
