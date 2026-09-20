module.exports = function (contexto) {
  const { nombreDelCuartoConMarca, sinMarcaDeCamara } = contexto;

  function clip(cuarto, opts) {
    return Object.assign({ categoria_path: [cuarto] }, opts);
  }

  return [
    {
      nombre: "un cuarto solo de Sony se marca [SONY]",
      fn: () => {
        const clips = [clip("Cocina", { bin_sony: true })];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        return { ok: resultado === "03. [SONY] Cocina", detalle: resultado };
      },
    },
    {
      nombre: "Sony + Drone se combinan en ese orden",
      fn: () => {
        const clips = [
          clip("Cocina", { bin_sony: true }),
          clip("Cocina", { bin_dron: true }),
        ];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        return { ok: resultado === "03. [SONY+DRONE] Cocina", detalle: resultado };
      },
    },
    {
      nombre: "las tres camaras se combinan Sony, Pocket, Drone",
      fn: () => {
        const clips = [
          clip("Cocina", { bin_dron: true }),
          clip("Cocina", { bin_pocket: true }),
          clip("Cocina", { bin_sony: true }),
        ];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        return { ok: resultado === "03. [SONY+POCKET+DRONE] Cocina", detalle: resultado };
      },
    },
    {
      nombre: "un clip sin camara reconocible (Osmo Action) no apaga la marca de las demas",
      fn: () => {
        const clips = [
          clip("Cocina", { bin_sony: true }),
          clip("Cocina", {}),
        ];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        return { ok: resultado === "03. [SONY] Cocina", detalle: resultado };
      },
    },
    {
      nombre: "sin ninguna camara reconocible no hay marca",
      fn: () => {
        const clips = [clip("Cocina", {})];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        return { ok: resultado === "03. Cocina", detalle: resultado };
      },
    },
    {
      nombre: "sinMarcaDeCamara quita una marca compuesta conocida al inicio",
      fn: () => {
        const resultado = sinMarcaDeCamara("[SONY+DRONE] Cocina");
        return { ok: resultado === "Cocina", detalle: resultado };
      },
    },
    {
      nombre: "la marca de una unidad combina las camaras de TODOS sus cuartos",
      fn: () => {
        const clips = [
          { categoria_path: ["Casa A", "Cocina"], bin_sony: true },
          { categoria_path: ["Casa A", "Baño"], bin_dron: true },
        ];
        const r = nombreDelCuartoConMarca("Casa A", "Casa A", clips, ["Casa A"]);
        return { ok: r === "[SONY+DRONE] Casa A", detalle: r };
      },
    },
    {
      nombre: "la marca de un cuarto dentro de una unidad NO mezcla otros cuartos de la misma unidad",
      fn: () => {
        const clips = [
          { categoria_path: ["Casa A", "Cocina"], bin_sony: true },
          { categoria_path: ["Casa A", "Baño"], bin_dron: true },
        ];
        const r = nombreDelCuartoConMarca("01. Cocina", "Cocina", clips, ["Casa A", "Cocina"]);
        return { ok: r === "01. [SONY] Cocina", detalle: r };
      },
    },
    {
      nombre: "sin unidad, la marca de un cuarto se comporta exactamente como antes",
      fn: () => {
        const clips = [
          { categoria_path: ["Cocina"], bin_sony: true },
        ];
        const r = nombreDelCuartoConMarca("01. Cocina", "Cocina", clips);
        return { ok: r === "01. [SONY] Cocina", detalle: r };
      },
    },
  ];
};
