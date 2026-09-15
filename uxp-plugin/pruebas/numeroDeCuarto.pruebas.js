// Los casos del prefijo numerico de los cuartos. Logica pura: corren con
// `node uxp-plugin/pruebas/correr.js`, sin abrir Premiere.
module.exports = function (ctx) {
  return [
    {
      nombre: "conNumero pone el prefijo de dos digitos",
      fn: () => {
        const r = ctx.conNumero("Cocina", 3);
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
    {
      nombre: "conNumero no se rompe pasando de nueve",
      fn: () => {
        const r = ctx.conNumero("Cocina", 12);
        return { ok: r === "12. Cocina", detalle: r };
      },
    },
    {
      nombre: "sinNumero quita el prefijo",
      fn: () => {
        const r = ctx.sinNumero("03. Cocina");
        return { ok: r === "Cocina", detalle: r };
      },
    },
    {
      // LO QUE ESTO EXISTE PARA EVITAR: un numero que Bruno escribio a mano
      // no es nuestro y no se toca. Misma regla que las marcas del nombre.
      nombre: "un numero sin punto no es nuestro prefijo",
      fn: () => {
        const r = ctx.sinNumero("2 Recamaras");
        return { ok: r === "2 Recamaras", detalle: r };
      },
    },
    {
      nombre: "solo se quita UN prefijo, no todos",
      fn: () => {
        const r = ctx.sinNumero("01. 2 Recamaras");
        return { ok: r === "2 Recamaras", detalle: r };
      },
    },
    {
      nombre: "un cuarto sin numero se queda igual",
      fn: () => {
        const r = ctx.sinNumero("Cocina");
        return { ok: r === "Cocina", detalle: r };
      },
    },
    {
      // EL CASO DE LA SEGUNDA PASADA (§5.2 del spec): sin esto, Premiere
      // crea una segunda Cocina y los clips quedan repartidos en dos.
      nombre: "03. Cocina y 05. Cocina son la misma Cocina",
      fn: () => {
        const r = ctx.esElMismoCuarto("03. Cocina", "05. Cocina");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "Cocina y 05. Cocina son la misma Cocina",
      fn: () => {
        const r = ctx.esElMismoCuarto("Cocina", "05. Cocina");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "Cocina y Comedor no son el mismo cuarto",
      fn: () => {
        const r = ctx.esElMismoCuarto("03. Cocina", "04. Comedor");
        return { ok: r === false, detalle: String(r) };
      },
    },
    {
      // Igualdad EXACTA despues de quitar el numero: el acento no se
      // perdona, igual que en la revision de la lista.
      nombre: "Recamara 1 y Recámara 1 no son el mismo cuarto",
      fn: () => {
        const r = ctx.esElMismoCuarto("01. Recamara 1", "01. Recámara 1");
        return { ok: r === false, detalle: String(r) };
      },
    },
    {
      nombre: "caminoDelClip numera el cuarto segun la guia",
      fn: () => {
        const r = ctx.caminoDelClip(["Cocina", "Picks"], ["Fachada", "Cocina"]);
        return { ok: r.join(" > ") === "02. Clip > 02. Cocina > Picks", detalle: r.join(" > ") };
      },
    },
    {
      nombre: "sin guia, caminoDelClip deja el cuarto sin numero",
      fn: () => {
        const r = ctx.caminoDelClip(["Cocina"], []);
        return { ok: r.join(" > ") === "02. Clip > Cocina", detalle: r.join(" > ") };
      },
    },
  ];
};
