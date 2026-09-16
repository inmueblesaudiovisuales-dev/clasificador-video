module.exports = function pruebasDeSecuencia(ctx) {
  return [
    {
      nombre: "un manifest viejo no pide secuencia",
      fn: () => ({
        ok: ctx.datosDeSecuencia({ proyecto: "Casa", orientacion: "vertical" }) === null,
        detalle: "un JSON viejo debe importar solo clips",
      }),
    },
    {
      nombre: "los tres formatos producen nombre y ajustes exactos",
      fn: () => {
        const casos = [
          ["4K 9:16", "Casa 9:16", 2160, 3840],
          ["2.7K 9:16", "Casa 9:16", 2160, 3840],
          ["4K 16:9", "Casa 16:9", 3840, 2160],
        ];
        const reales = casos.map(([formato]) =>
          ctx.datosDeSecuencia({ proyecto: "Casa", formato_secuencia: formato })
        );
        const ok = reales.every((r, i) =>
          r.nombre === casos[i][1] && r.ancho === casos[i][2] &&
          r.alto === casos[i][3] && r.fps === 59.94
        );
        return { ok, detalle: JSON.stringify(reales) };
      },
    },
  ];
};
