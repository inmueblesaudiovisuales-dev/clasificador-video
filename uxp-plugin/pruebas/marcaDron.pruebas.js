// Los casos de la marca [DRONE] en el nombre del cuarto. Logica pura: corren
// con `node uxp-plugin/pruebas/correr.js`.
module.exports = function (ctx) {
  return [
    {
      nombre: "sinMarcaDron quita la marca del inicio",
      fn: () => {
        const r = ctx.sinMarcaDron("[DRONE] Cocina");
        return { ok: r === "Cocina", detalle: r };
      },
    },
    {
      nombre: "sinMarcaDron no toca un nombre sin marca",
      fn: () => {
        const r = ctx.sinMarcaDron("Cocina");
        return { ok: r === "Cocina", detalle: r };
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
      // EL ORDEN QUE PIDIO BRUNO: numero, marca, nombre -- pegada al
      // nombre, nunca antes del numero.
      nombre: "nombreDelCuartoConMarca pone la marca DESPUES del numero",
      fn: () => {
        const clips = [{ categoria_path: ["Aerea"], bin_dron: true }];
        const r = ctx.nombreDelCuartoConMarca("02. Aerea", "Aerea", clips);
        return { ok: r === "02. [DRONE] Aerea", detalle: r };
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
    {
      nombre: "nombreDelCuartoConMarca sin guia (sin numero) marca al inicio",
      fn: () => {
        const clips = [{ categoria_path: ["Aerea"], bin_dron: true }];
        const r = ctx.nombreDelCuartoConMarca("Aerea", "Aerea", clips);
        return { ok: r === "[DRONE] Aerea", detalle: r };
      },
    },
    {
      nombre: "nombreDelCuartoConMarca: un cuarto mezclado no se marca",
      fn: () => {
        const clips = [
          { categoria_path: ["Aerea"], bin_dron: true },
          { categoria_path: ["Aerea"], bin_dron: false },
        ];
        const r = ctx.nombreDelCuartoConMarca("02. Aerea", "Aerea", clips);
        return { ok: r === "02. Aerea", detalle: r };
      },
    },
  ];
};
