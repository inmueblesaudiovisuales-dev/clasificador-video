// caminoDelClip: numera la UNIDAD y el CUARTO con la guia por unidad (spec
// 2026-09-21). Sin unidades, el cuarto en 0 se numera con `guia.orden`, que
// es el comportamiento de siempre (spec 2026-09-20).
module.exports = function (ctx) {
  const clips = ["02. Clip"];
  return [
    {
      nombre: "sin unidad, el cuarto en 0 se numera con la guia",
      fn: () => {
        const r = ctx.caminoDelClip(["Cocina"], { orden: ["Cocina", "Baño"] });
        return { ok: JSON.stringify(r) === JSON.stringify([...clips, "01. Cocina"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "con unidades, la unidad y el cuarto se numeran cada uno con lo suyo",
      fn: () => {
        const guia = { unidades: [
          { nombre: "Casa A", orden: ["Cocina", "Baño"] },
          { nombre: "Casa B", orden: ["Fachada"] },
        ] };
        const r = ctx.caminoDelClip(["Casa B", "Fachada"], guia);
        return { ok: JSON.stringify(r) === JSON.stringify([...clips, "02. Casa B", "01. Fachada"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "con unidad y cuarto fuera de la guia, solo se numera la unidad",
      fn: () => {
        const guia = { unidades: [{ nombre: "Casa A", orden: ["Cocina"] }] };
        const r = ctx.caminoDelClip(["Casa A", "Recamara nueva"], guia);
        return { ok: JSON.stringify(r) === JSON.stringify([...clips, "01. Casa A", "Recamara nueva"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "sin guia, ninguno de los dos lleva numero",
      fn: () => {
        const r = ctx.caminoDelClip(["Casa A", "Cocina"], {});
        return { ok: JSON.stringify(r) === JSON.stringify([...clips, "Casa A", "Cocina"]), detalle: r.join(" > ") };
      },
    },
    {
      nombre: "el comportamiento de siempre sigue igual: un cuarto solo con guia",
      fn: () => {
        const r = ctx.caminoDelClip(["Baño"], { orden: ["Cocina", "Baño"] });
        return { ok: JSON.stringify(r) === JSON.stringify([...clips, "02. Baño"]), detalle: r.join(" > ") };
      },
    },
  ];
};
