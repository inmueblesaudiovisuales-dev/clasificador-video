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
    {
      nombre: "cada formato agrega una secuencia vacía 1080p del mismo encuadre",
      fn: () => {
        const casos = [
          ["4K 9:16", "Casa 9:16", 2160, 3840, "Casa 9:16 1080p", 1080, 1920],
          ["2.7K 9:16", "Casa 9:16", 2160, 3840, "Casa 9:16 1080p", 1080, 1920],
          ["4K 16:9", "Casa 16:9", 3840, 2160, "Casa 16:9 1080p", 1920, 1080],
        ];
        const reales = casos.map(([formato]) =>
          ctx.datosDeSecuencias({ proyecto: "Casa", formato_secuencia: formato })
        );
        const ok = reales.every((par, i) =>
          par.length === 2 &&
          par[0].nombre === casos[i][1] && par[0].ancho === casos[i][2] &&
          par[0].alto === casos[i][3] && par[0].fps === 59.94 &&
          par[1].nombre === casos[i][4] && par[1].ancho === casos[i][5] &&
          par[1].alto === casos[i][6] && par[1].fps === 59.94
        );
        return { ok, detalle: JSON.stringify(reales) };
      },
    },
    {
      nombre: "un manifest viejo tampoco agrega secuencia 1080p",
      fn: () => ({
        ok: ctx.datosDeSecuencias({ proyecto: "Casa", orientacion: "vertical" }).length === 0,
        detalle: "un JSON viejo debe importar solo clips",
      }),
    },
    {
      nombre: "un JSON nuevo pide tres principales y dos 1080p, cada grupo en su bin",
      fn: () => {
        const reales = ctx.datosDeSecuencias({ proyecto: "Casa", crear_secuencias: true });
        const esperados = [
          ["Casa 4K 9:16", 2160, 3840, "Resolucion original"],
          ["Casa 2.7K 9:16", 2160, 3840, "Resolucion original"],
          ["Casa 4K 16:9", 3840, 2160, "Resolucion original"],
          ["Casa 9:16 1080p", 1080, 1920, "1080p"],
          ["Casa 16:9 1080p", 1920, 1080, "1080p"],
        ];
        const ok = reales.length === esperados.length && reales.every((dato, i) =>
          dato.nombre === esperados[i][0] && dato.ancho === esperados[i][1] &&
          dato.alto === esperados[i][2] && dato.carpeta === esperados[i][3] &&
          dato.fps === 59.94
        );
        return { ok, detalle: JSON.stringify(reales) };
      },
    },
  ];
};
