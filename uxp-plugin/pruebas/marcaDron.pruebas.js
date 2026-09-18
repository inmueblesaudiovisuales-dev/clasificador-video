// Los casos de la marca [DRONE] en el nombre del cuarto. Logica pura: corren
// con `node uxp-plugin/pruebas/correr.js`.
module.exports = function (ctx) {
  return [
    {
      nombre: "conMarcaDron pone la marca al inicio",
      fn: () => {
        const r = ctx.conMarcaDron("03. Cocina", true);
        return { ok: r === "[DRONE] 03. Cocina", detalle: r };
      },
    },
    {
      nombre: "conMarcaDron sin dron no pone nada",
      fn: () => {
        const r = ctx.conMarcaDron("03. Cocina", false);
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
    {
      nombre: "conMarcaDron es idempotente",
      fn: () => {
        const una = ctx.conMarcaDron("03. Cocina", true);
        const dos = ctx.conMarcaDron(una, true);
        return { ok: dos === "[DRONE] 03. Cocina", detalle: dos };
      },
    },
    {
      nombre: "conMarcaDron quita la marca si ya no aplica",
      fn: () => {
        const r = ctx.conMarcaDron("[DRONE] 03. Cocina", false);
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
    {
      nombre: "sinMarcaDron no toca un nombre sin marca",
      fn: () => {
        const r = ctx.sinMarcaDron("03. Cocina");
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
    {
      nombre: "cuartoEsDeDron: todos los clips de un bin de dron",
      fn: () => {
        const clips = [
          { categoria_path: ["Aerea"], bin_dron: true },
          { categoria_path: ["Aerea"], bin_dron: true },
        ];
        const r = ctx.cuartoEsDeDron(clips, "Aerea");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "cuartoEsDeDron: un solo clip que no es de dron lo tumba",
      fn: () => {
        const clips = [
          { categoria_path: ["Aerea"], bin_dron: true },
          { categoria_path: ["Aerea"], bin_dron: false },
        ];
        const r = ctx.cuartoEsDeDron(clips, "Aerea");
        return { ok: r === false, detalle: String(r) };
      },
    },
    {
      nombre: "cuartoEsDeDron: solo mira los clips de ESE cuarto",
      fn: () => {
        const clips = [
          { categoria_path: ["Aerea"], bin_dron: true },
          { categoria_path: ["Cocina"], bin_dron: false },
        ];
        const r = ctx.cuartoEsDeDron(clips, "Aerea");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "cuartoEsDeDron: un cuarto vacio no cuenta como dron",
      fn: () => {
        const r = ctx.cuartoEsDeDron([], "Aerea");
        return { ok: r === false, detalle: String(r) };
      },
    },
    {
      nombre: "nombreDelCuartoConMarca junta numero y marca",
      fn: () => {
        const clips = [{ categoria_path: ["Aerea"], bin_dron: true }];
        const r = ctx.nombreDelCuartoConMarca("02. Aerea", "Aerea", clips);
        return { ok: r === "[DRONE] 02. Aerea", detalle: r };
      },
    },
    {
      nombre: "nombreDelCuartoConMarca sin dron deja el nombre igual",
      fn: () => {
        const clips = [{ categoria_path: ["Cocina"], bin_dron: false }];
        const r = ctx.nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
  ];
};
