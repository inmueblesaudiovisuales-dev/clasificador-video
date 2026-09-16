// Los casos del avance: que pasos ya montaste. Logica pura, sin disco:
// corren con `node uxp-plugin/pruebas/correr.js`.
module.exports = function (ctx) {
  const guion = [
    { cuarto: "Aerea" },
    { cuarto: "Sala" },
    { cuarto: "Aerea" },
  ];
  return [
    {
      nombre: "sin nada montado, el avance esta vacio",
      fn: () => {
        const r = ctx.cuadrarAvance([], guion);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "una palomita que cuadra se conserva",
      fn: () => {
        const r = ctx.cuadrarAvance([{ paso: 1, cuarto: "Aerea" }], guion);
        return { ok: r.length === 1 && r[0].paso === 1, detalle: JSON.stringify(r) };
      },
    },
    {
      // EL CASO DEL SPEC: reimportaste con otra guia y el paso 2 ya no es el
      // cuarto que era. Esa palomita daria un avance FALSO.
      nombre: "una palomita cuyo cuarto ya no cuadra se descarta",
      fn: () => {
        const r = ctx.cuadrarAvance([{ paso: 2, cuarto: "Cocina" }], guion);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "una palomita de un paso que ya no existe se descarta",
      fn: () => {
        const r = ctx.cuadrarAvance([{ paso: 9, cuarto: "Aerea" }], guion);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      // Las DOS aereas son pasos distintos: palomear la de abrir no palomea
      // la de cerrar.
      nombre: "las dos veces del mismo cuarto se palomean por separado",
      fn: () => {
        const r = ctx.cuadrarAvance(
          [{ paso: 1, cuarto: "Aerea" }, { paso: 3, cuarto: "Aerea" }], guion);
        const solo1 = ctx.cuadrarAvance([{ paso: 1, cuarto: "Aerea" }], guion);
        return {
          ok: r.length === 2 && solo1.length === 1,
          detalle: JSON.stringify(r) + " / " + JSON.stringify(solo1),
        };
      },
    },
    {
      nombre: "montar un paso lo agrega",
      fn: () => {
        const r = ctx.conPaso([], guion, 2, true);
        return { ok: r.length === 1 && r[0].cuarto === "Sala", detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "montar dos veces el mismo paso no lo duplica",
      fn: () => {
        const uno = ctx.conPaso([], guion, 2, true);
        const dos = ctx.conPaso(uno, guion, 2, true);
        return { ok: dos.length === 1, detalle: JSON.stringify(dos) };
      },
    },
    {
      nombre: "despalomear un paso lo quita",
      fn: () => {
        const uno = ctx.conPaso([], guion, 2, true);
        const r = ctx.conPaso(uno, guion, 2, false);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "el paso en el que vas es el primero sin palomear",
      fn: () => {
        const r = ctx.pasoActual([{ paso: 1, cuarto: "Aerea" }], guion);
        return { ok: r === 2, detalle: String(r) };
      },
    },
    {
      nombre: "con todo montado ya no hay paso actual",
      fn: () => {
        const todo = [
          { paso: 1, cuarto: "Aerea" },
          { paso: 2, cuarto: "Sala" },
          { paso: 3, cuarto: "Aerea" },
        ];
        const r = ctx.pasoActual(todo, guion);
        return { ok: r === null, detalle: String(r) };
      },
    },
    {
      // Para pintar el bin: el cuarto cuenta como montado solo cuando TODAS
      // sus veces lo estan. Con la aerea de abrir palomeada y la de cerrar
      // no, la carpeta todavia no esta lista.
      nombre: "un cuarto esta montado solo cuando TODAS sus veces lo estan",
      fn: () => {
        const media = ctx.cuartosMontados([{ paso: 1, cuarto: "Aerea" }], guion);
        const todo = ctx.cuartosMontados(
          [{ paso: 1, cuarto: "Aerea" }, { paso: 3, cuarto: "Aerea" }], guion);
        return {
          ok: media.indexOf("Aerea") === -1 && todo.indexOf("Aerea") !== -1,
          detalle: JSON.stringify(media) + " / " + JSON.stringify(todo),
        };
      },
    },
    {
      // Hueco de la autorevision: un guion vacio no debe tronar, solo no
      // dejar montado nada.
      nombre: "cuartosMontados con guion vacio no truena y no monta nada",
      fn: () => {
        const r = ctx.cuartosMontados([{ paso: 1, cuarto: "Aerea" }], []);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      // Hueco: conPaso con un numero fuera de rango (0, negativo, o mas
      // grande que el guion) no debe agregar nada raro al avance.
      nombre: "conPaso con un paso fuera de rango no agrega nada",
      fn: () => {
        const cero = ctx.conPaso([], guion, 0, true);
        const negativo = ctx.conPaso([], guion, -1, true);
        const grande = ctx.conPaso([], guion, 99, true);
        return {
          ok: cero.length === 0 && negativo.length === 0 && grande.length === 0,
          detalle: JSON.stringify(cero) + " / " + JSON.stringify(negativo) + " / " + JSON.stringify(grande),
        };
      },
    },
    {
      // Hueco: cuadrarAvance con null en vez de arreglo no debe tronar.
      nombre: "cuadrarAvance con null en vez de arreglo no truena",
      fn: () => {
        const r = ctx.cuadrarAvance(null, guion);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
  ];
};
