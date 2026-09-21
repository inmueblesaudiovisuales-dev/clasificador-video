module.exports = function (contexto) {
  const { nombreDelCuartoConMarca, sinMarcaDeCamara, marcaDeCamaraDelPrefijo } = contexto;

  function clip(cuarto, opts) {
    return Object.assign({ categoria_path: [cuarto] }, opts);
  }

  return [
    {
      nombre: "un cuarto solo de Sony se marca [SONY] al final",
      fn: () => {
        const clips = [clip("Cocina", { bin_sony: true })];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        return { ok: resultado === "03. Cocina [SONY]", detalle: resultado };
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
        return { ok: resultado === "03. Cocina [SONY+DRONE]", detalle: resultado };
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
        return { ok: resultado === "03. Cocina [SONY+POCKET+DRONE]", detalle: resultado };
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
        return { ok: resultado === "03. Cocina [SONY]", detalle: resultado };
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
      nombre: "sinMarcaDeCamara quita una marca compuesta conocida al final",
      fn: () => {
        const resultado = sinMarcaDeCamara("Cocina [SONY+DRONE]");
        return { ok: resultado === "Cocina", detalle: resultado };
      },
    },
    {
      // La marca vivia al inicio antes del 2026-09-21. Se sigue quitando de
      // ahi para que una carpeta de una importacion anterior no se lea como
      // otro cuarto y Premiere le cree una segunda.
      nombre: "sinMarcaDeCamara tambien quita la marca del formato viejo, al inicio",
      fn: () => {
        const resultado = sinMarcaDeCamara("[SONY+DRONE] Cocina");
        return { ok: resultado === "Cocina", detalle: resultado };
      },
    },
    {
      nombre: "sinMarcaDeCamara no toca un nombre sin marca",
      fn: () => {
        const resultado = sinMarcaDeCamara("Cocina");
        return { ok: resultado === "Cocina", detalle: resultado };
      },
    },
    {
      nombre: "marcaDeCamaraDelPrefijo devuelve la marca combinada",
      fn: () => {
        const clips = [
          clip("Cocina", { bin_dron: true }),
          clip("Cocina", { bin_sony: true }),
        ];
        const r = marcaDeCamaraDelPrefijo(clips, ["Cocina"]);
        return { ok: r === "SONY+DRONE", detalle: r };
      },
    },
    {
      nombre: "marcaDeCamaraDelPrefijo devuelve cadena vacia sin camara",
      fn: () => {
        const r = marcaDeCamaraDelPrefijo([], ["Cocina"]);
        return { ok: r === "", detalle: JSON.stringify(r) };
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
        return { ok: r === "Casa A [SONY+DRONE]", detalle: r };
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
        return { ok: r === "01. Cocina [SONY]", detalle: r };
      },
    },
    {
      nombre: "sin unidad, la marca de un cuarto se comporta exactamente como antes",
      fn: () => {
        const clips = [
          { categoria_path: ["Cocina"], bin_sony: true },
        ];
        const r = nombreDelCuartoConMarca("01. Cocina", "Cocina", clips);
        return { ok: r === "01. Cocina [SONY]", detalle: r };
      },
    },
  ];
};
