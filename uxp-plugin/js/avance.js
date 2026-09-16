// Que pasos del guion ya montaste.
//
// UN PASO NO ES UN CUARTO. La aerea abre el guion y lo cierra: son dos pasos
// y una sola carpeta, y palomear el primero no palomea el segundo. Por eso
// todo aqui va por NUMERO DE PASO y no por nombre de cuarto.
//
// Cada palomita guarda las dos cosas --el paso Y el cuarto-- a proposito: si
// Bruno reimporta con otra guia, el paso 2 puede ser otro cuarto, y esa
// palomita daria un avance FALSO. Cuadrarlas contra el guion de ahora las
// descarta sin avisar: no es un error, es que la guia cambio.
//
// Logica pura, sin disco: el disco es `avanceDisco.js`. Se prueba con
// `node uxp-plugin/pruebas/correr.js`.
//
// Spec: docs/superpowers/specs/2026-09-15-el-guion-y-las-carpetas-design.md

// El cuarto del paso N del guion (los pasos se cuentan desde 1), o null.
// Un N fuera de rango (0, negativo, o mas grande que el guion) tambien da
// null: asi conPaso() no agrega nada para un paso que no existe.
function cuartoDelPaso(guion, paso) {
  const renglon = (guion || [])[paso - 1];
  return (renglon && renglon.cuarto) || null;
}

// Las palomitas que siguen valiendo con el guion de ahora.
function cuadrarAvance(avance, guion) {
  return (avance || []).filter(
    (p) => p && cuartoDelPaso(guion, p.paso) === p.cuarto
  );
}

// El avance con el paso N palomeado (`montado` true) o despalomeado.
// Un paso que no existe en el guion no hace nada.
function conPaso(avance, guion, paso, montado) {
  const cuarto = cuartoDelPaso(guion, paso);
  if (!cuarto) return (avance || []).slice();
  const sinEl = (avance || []).filter((p) => p && p.paso !== paso);
  if (!montado) return sinEl;
  sinEl.push({ paso: paso, cuarto: cuarto });
  sinEl.sort((a, b) => a.paso - b.paso);
  return sinEl;
}

function estaMontado(avance, paso) {
  return (avance || []).some((p) => p && p.paso === paso);
}

// En que paso vas: el PRIMERO sin palomear. `null` cuando ya no falta
// ninguno -- y eso es distinto de «vas en el 1», que es un guion sin
// empezar.
function pasoActual(avance, guion) {
  for (let i = 1; i <= (guion || []).length; i++) {
    if (!estaMontado(avance, i)) return i;
  }
  return null;
}

// Los cuartos cuyos pasos estan TODOS montados. Es lo que decide si el bin
// se pinta: con la aerea de abrir lista y la de cerrar pendiente, esa
// carpeta todavia no esta terminada y pintarla mentiria.
function cuartosMontados(avance, guion) {
  const faltantes = {};
  for (let i = 1; i <= (guion || []).length; i++) {
    const cuarto = cuartoDelPaso(guion, i);
    if (!cuarto) continue;
    if (!(cuarto in faltantes)) faltantes[cuarto] = 0;
    if (!estaMontado(avance, i)) faltantes[cuarto]++;
  }
  return Object.keys(faltantes).filter((c) => faltantes[c] === 0);
}
