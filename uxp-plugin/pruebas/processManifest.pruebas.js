// indicesDelCamino: decide en que indice de `camino` (el que arma
// caminoDelClip) vive la unidad y el cuarto, segun si categoryPath trae
// unidad o no.
module.exports = function (ctx) {
  return [
    {
      nombre: "indicesDelCamino sin unidad: cuarto en 1 (tras CARPETA_DE_CLIPS)",
      fn: () => {
        const r = ctx.indicesDelCamino(["Cocina"]);
        return { ok: r.indiceUnidad === null && r.indiceCuarto === 1, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "indicesDelCamino con unidad: unidad en 1, cuarto en 2",
      fn: () => {
        const r = ctx.indicesDelCamino(["Casa A", "Cocina"]);
        return { ok: r.indiceUnidad === 1 && r.indiceCuarto === 2, detalle: JSON.stringify(r) };
      },
    },
  ];
};
