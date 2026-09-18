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

// Le pone o le quita la marca segun `esDron`. Idempotente: aplicarla dos
// veces con el mismo `esDron` deja el nombre igual -- primero se limpia lo
// que ya hubiera, y despues se pone lo que toca. Mismo patron que
// `nombre.js` con las marcas de estado de los clips.
function conMarcaDron(nombre, esDron) {
  const limpio = sinMarcaDron(nombre);
  return esDron ? MARCA_DRONE + limpio : limpio;
}

// Quita SOLO la marca que este modulo pone, y solo si esta al inicio. Un
// nombre que Bruno haya escrito el mismo no es nuestro y no se toca.
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

// Junta las tres cosas de arriba para quien arma el camino de un clip
// (`processManifest.js`): el nombre YA numerado del cuarto (lo que da
// `conNumero`/`caminoDelClip`), el nombre SIN numero que identifica al
// cuarto en el manifiesto (`categoryPath[0]`), y la lista completa de
// clips para decidir si aplica la marca.
function nombreDelCuartoConMarca(nombreConNumero, nombreDeCuartoSinNumero, clipsDelManifest) {
  return conMarcaDron(
    nombreConNumero,
    cuartoEsDeDron(clipsDelManifest, nombreDeCuartoSinNumero)
  );
}
