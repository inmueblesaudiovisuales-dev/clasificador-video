// Los casos del nombre completo del clip: [símbolo ]Cuarto NN [CAMARA].
// Logica pura: corren con `node uxp-plugin/pruebas/correr.js`.
//
// Spec: docs/superpowers/specs/2026-09-21-nombre-de-clip-en-premiere-design.md
module.exports = function (ctx) {
  const { numeroDeClip, nombreDeClip, numerosDeClip } = ctx;

  return [
    {
      nombre: "numeroDeClip deja el numero a dos digitos",
      fn: () => {
        const r = numeroDeClip(1);
        return { ok: r === "01", detalle: r };
      },
    },
    {
      nombre: "numeroDeClip no recorta los numeros de mas de dos digitos",
      fn: () => {
        const r = numeroDeClip(100);
        return { ok: r === "100", detalle: r };
      },
    },
    {
      nombre: "un pick se llama simbolo, cuarto, numero y camara",
      fn: () => {
        const r = nombreDeClip("Cocina", 1, "SONY", "pick");
        return { ok: r === "✓ Cocina 01 [SONY]", detalle: r };
      },
    },
    {
      nombre: "un destacado usa la estrella",
      fn: () => {
        const r = nombreDeClip("Recámara 2", 3, "SONY+DRONE", "destacado");
        return { ok: r === "★ Recámara 2 03 [SONY+DRONE]", detalle: r };
      },
    },
    {
      nombre: "un reject usa la equis",
      fn: () => {
        const r = nombreDeClip("Baño", 2, "POCKET", "reject");
        return { ok: r === "✕ Baño 02 [POCKET]", detalle: r };
      },
    },
    {
      nombre: "un clip sin marcar no lleva simbolo",
      fn: () => {
        const r = nombreDeClip("Alberca", 4, "SONY", "none");
        return { ok: r === "Alberca 04 [SONY]", detalle: r };
      },
    },
    {
      nombre: "sin camara reconocible el nombre termina en el numero",
      fn: () => {
        const r = nombreDeClip("Cocina", 1, "", "pick");
        return { ok: r === "✓ Cocina 01", detalle: r };
      },
    },
    {
      nombre: "numerosDeClip numera por cuarto en el orden del manifiesto",
      fn: () => {
        const clips = [
          { categoria_path: ["Cocina"] },
          { categoria_path: ["Cocina"] },
          { categoria_path: ["Baño"] },
          { categoria_path: ["Cocina"] },
        ];
        const r = numerosDeClip(clips);
        return { ok: JSON.stringify(r) === "[1,2,1,3]", detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "numerosDeClip distingue el mismo cuarto en dos unidades",
      fn: () => {
        const clips = [
          { categoria_path: ["Casa A", "Cocina"] },
          { categoria_path: ["Casa B", "Cocina"] },
          { categoria_path: ["Casa A", "Cocina"] },
        ];
        const r = numerosDeClip(clips);
        return { ok: JSON.stringify(r) === "[1,1,2]", detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "los clips sin clasificar comparten su propio contador",
      fn: () => {
        const clips = [
          { categoria_path: [] },
          { categoria_path: [] },
        ];
        const r = numerosDeClip(clips);
        return { ok: JSON.stringify(r) === "[1,2]", detalle: JSON.stringify(r) };
      },
    },
  ];
};
