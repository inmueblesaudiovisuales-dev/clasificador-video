// caminoDelClip: numera el CUARTO, sea cual sea su posicion en
// categoryPath -- segmento 0 sin unidad, segmento 1 con unidad. La unidad
// misma no lleva numero: no hay guia de unidades (spec 2026-09-20 §7-§8).
module.exports = function (ctx) {
  return [
    {
      nombre: "sin unidad, el cuarto en 0 se numera con la guia",
      fn: () => {
        const r = ctx.caminoDelClip(["Cocina"], ["Cocina", "Baño"]);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "01. Cocina"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "con unidad, el cuarto en 1 se numera y la unidad no",
      fn: () => {
        const r = ctx.caminoDelClip(["Casa A", "Cocina"], ["Cocina", "Baño"]);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "Casa A", "01. Cocina"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "con unidad y cuarto fuera de la guia, ninguno de los dos se numera",
      fn: () => {
        const r = ctx.caminoDelClip(["Casa A", "Recamara nueva"], ["Cocina"]);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "Casa A", "Recamara nueva"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "sin guia, ninguno de los dos lleva numero",
      fn: () => {
        const r = ctx.caminoDelClip(["Casa A", "Cocina"], []);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "Casa A", "Cocina"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "el comportamiento de siempre sigue igual: un cuarto solo con guia",
      fn: () => {
        const r = ctx.caminoDelClip(["Baño"], ["Cocina", "Baño"]);
        return { ok: JSON.stringify(r) === JSON.stringify(["02. Clip", "02. Baño"]), detalle: r.join(" > ") };
      },
    },
  ];
};
