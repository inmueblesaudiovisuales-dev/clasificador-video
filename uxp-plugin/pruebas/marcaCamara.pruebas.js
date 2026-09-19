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
  ];
};
