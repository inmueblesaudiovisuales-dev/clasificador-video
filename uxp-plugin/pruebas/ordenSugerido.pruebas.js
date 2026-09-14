// Los casos de la logica pura del orden sugerido. Reciben el contexto donde
// ya se evaluaron los archivos del plugin, y devuelven [{ nombre, fn }].
//
// `fn` es sincrona y devuelve { ok, detalle }: nada de aqui le pregunta algo
// a Premiere ni a la red, y ese es justo el punto -- si algun dia un caso
// necesitara `await`, es senal de que la logica se ensucio.
module.exports = function (ctx) {
  return [
    // ---------------------------------------------------------------
    // revisarLista -- la regla del §6 del spec, que es la que tiene dientes
    // ---------------------------------------------------------------
    {
      nombre: "una lista que cuadra no tiene nada que marcar",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Fachada", porque: "…" }, { cuarto: "Sala", porque: "…" }],
          ["Sala", "Fachada"]
        );
        return {
          ok: r.faltan.length === 0 && r.inventados.length === 0 && r.repetidos.length === 0,
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      // El caso que le da razon de ser a todo esto: una guia a la que le
      // falta la cocina hace que se te olvide la cocina al editar, y eso no
      // se nota hasta despues de entregar.
      nombre: "un cuarto que el modelo se salto sale como faltante",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Fachada", porque: "…" }],
          ["Fachada", "Cocina"]
        );
        return {
          ok: r.faltan.join() === "Cocina" && r.inventados.length === 0,
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "un cuarto que el modelo se invento sale como inventado",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Fachada", porque: "…" }, { cuarto: "Sótano", porque: "…" }],
          ["Fachada"]
        );
        return {
          ok: r.inventados.join() === "Sótano" && r.faltan.length === 0,
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "faltar e inventar a la vez son dos avisos, no uno",
      fn: () => {
        const r = ctx.revisarLista([{ cuarto: "Sótano", porque: "…" }], ["Cocina"]);
        return {
          ok: r.faltan.join() === "Cocina" && r.inventados.join() === "Sótano",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      // El que un `.trim().toLowerCase()` de mas esconderia. «Recamara 1» no
      // es «Recámara 1»: uno es el cuarto de Bruno y el otro es un cuarto que
      // el modelo escribio distinto. Tratarlos como el mismo es exactamente
      // la clase de bug del 2026-08-22 -- dos partes del programa diciendo
      // cosas distintas del mismo dato.
      nombre: "el acento cuenta: Recamara 1 no es Recámara 1",
      fn: () => {
        const r = ctx.revisarLista([{ cuarto: "Recámara 1", porque: "…" }], ["Recamara 1"]);
        return {
          ok: r.faltan.join() === "Recamara 1" && r.inventados.join() === "Recámara 1",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "las mayúsculas también cuentan",
      fn: () => {
        const r = ctx.revisarLista([{ cuarto: "sala", porque: "…" }], ["Sala"]);
        return {
          ok: r.faltan.join() === "Sala" && r.inventados.join() === "sala",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      // Un cuarto dos veces no es un invento ni una falta, pero tampoco esta
      // bien: en una guia de recorrido significa pasar dos veces por el mismo
      // lugar. Se marca aparte para poder decirlo con sus palabras.
      nombre: "el mismo cuarto repetido se marca aparte",
      fn: () => {
        const r = ctx.revisarLista(
          [{ cuarto: "Sala", porque: "…" }, { cuarto: "Sala", porque: "…" }],
          ["Sala"]
        );
        return {
          ok: r.faltan.length === 0 && r.inventados.length === 0 && r.repetidos.join() === "Sala",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "una lista vacía marca TODOS los cuartos como faltantes",
      fn: () => {
        const r = ctx.revisarLista([], ["Sala", "Cocina"]);
        return { ok: r.faltan.join() === "Sala,Cocina", detalle: JSON.stringify(r) };
      },
    },

    // ---------------------------------------------------------------
    // leerRespuesta -- lo que llega del modelo, que no siempre es lo pedido
    // ---------------------------------------------------------------
    {
      nombre: "un JSON limpio se lee y conserva el orden",
      fn: () => {
        const r = ctx.leerRespuesta(
          '{"orden":[{"cuarto":"Fachada","porque":"Se empieza por fuera"},' +
            '{"cuarto":"Sala","porque":"Es lo primero al entrar"}]}'
        );
        return {
          ok:
            r.ok === true &&
            r.lista.length === 2 &&
            r.lista[0].cuarto === "Fachada" &&
            r.lista[1].cuarto === "Sala",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "una respuesta que no es JSON se dice, no se enseña a medias",
      fn: () => {
        const r = ctx.leerRespuesta("Claro, con gusto. Primero iría la fachada…");
        return { ok: r.ok === false && !!r.error, detalle: JSON.stringify(r) };
      },
    },
    {
      // Los modelos envuelven el JSON en ```json … ``` aunque se les pida que
      // no. Es tan comun que tratarlo como error seria fallar por una
      // formalidad, con la respuesta buena adentro.
      nombre: "un JSON envuelto en ```json se lee igual",
      fn: () => {
        const r = ctx.leerRespuesta(
          '```json\n{"orden":[{"cuarto":"Sala","porque":"Es la entrada"}]}\n```'
        );
        return {
          ok: r.ok === true && r.lista.length === 1 && r.lista[0].cuarto === "Sala",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "un JSON con texto antes y después también se rescata",
      fn: () => {
        const r = ctx.leerRespuesta(
          'Aquí va: {"orden":[{"cuarto":"Cocina","porque":"…"}]} — espero que sirva.'
        );
        return {
          ok: r.ok === true && r.lista.length === 1 && r.lista[0].cuarto === "Cocina",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "un JSON válido con la forma equivocada tampoco pasa",
      fn: () => {
        const r = ctx.leerRespuesta('{"cuartos": ["Sala", "Cocina"]}');
        return { ok: r.ok === false && !!r.error, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "un renglón sin nombre de cuarto no pasa",
      fn: () => {
        const r = ctx.leerRespuesta('{"orden":[{"cuarto":"","porque":"…"}]}');
        return { ok: r.ok === false && !!r.error, detalle: JSON.stringify(r) };
      },
    },
    {
      // Bruno pidio la linea de por que, pero si el modelo no la manda la
      // lista sigue sirviendo: el orden es lo que vino a ver. Se queda vacia
      // en vez de tumbar la respuesta entera.
      nombre: "un renglón sin porqué se queda con el porqué vacío, no tumba la lista",
      fn: () => {
        const r = ctx.leerRespuesta('{"orden":[{"cuarto":"Sala"}]}');
        return {
          ok: r.ok === true && r.lista[0].cuarto === "Sala" && r.lista[0].porque === "",
          detalle: JSON.stringify(r),
        };
      },
    },
    {
      nombre: "una respuesta vacía se dice en vez de enseñar una lista vacía",
      fn: () => {
        const r = ctx.leerRespuesta("");
        return { ok: r.ok === false && !!r.error, detalle: JSON.stringify(r) };
      },
    },

    // ---------------------------------------------------------------
    // cuerpoDelRequest -- lo que SALE de la computadora
    // ---------------------------------------------------------------
    {
      // El §5 del spec: de la computadora solo salen los nombres de los
      // cuartos y lo que Bruno escriba. Este es el punto exacto donde un
      // descuido saca algo que no debia salir, y por eso se comprueba con una
      // red que busca rutas y nombres de archivo, no leyendo el codigo.
      nombre: "el cuerpo que se manda lleva los cuartos y nada más",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(
          ["Fachada", "Cocina"],
          { propiedad: "Casa", para: ["Redes"] },
          []
        );
        const texto = JSON.stringify(cuerpo);
        const sospechoso = /\/Users\/|\.MP4|\.mp4|C:\\\\|\/Volumes\/|DJI_|C\d{4}/.test(texto);
        return {
          ok: !sospechoso && texto.includes("Fachada") && texto.includes("Cocina"),
          detalle: sospechoso ? "el cuerpo trae algo que parece una ruta o un archivo" : "limpio",
        };
      },
    },
    {
      // El §3 del spec: el modelo no vio el video y no debe describir lo que
      // hay adentro de ningun cuarto. Esto no garantiza que obedezca --eso lo
      // atrapa el ojo de Bruno-- pero si que se lo pidieron.
      nombre: "al modelo se le dice que no vio el material",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(["Sala"], {}, []);
        const sistema = cuerpo.messages.find((m) => m.role === "system").content;
        return {
          ok: /no viste|no has visto/i.test(sistema) && /JSON/i.test(sistema),
          detalle: sistema.slice(0, 160),
        };
      },
    },
    {
      nombre: "el modelo es deepseek-chat",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(["Sala"], {}, []);
        return { ok: cuerpo.model === "deepseek-chat", detalle: String(cuerpo.model) };
      },
    },
    {
      nombre: "las respuestas de los chips viajan en el primer mensaje",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(
          ["Sala"],
          { propiedad: "Departamento", para: ["Redes", "Portafolio"], lucir: "la terraza" },
          []
        );
        const texto = JSON.stringify(cuerpo.messages);
        return {
          ok:
            texto.includes("Departamento") &&
            texto.includes("Redes") &&
            texto.includes("Portafolio") &&
            texto.includes("la terraza"),
          detalle: texto.slice(0, 200),
        };
      },
    },
    {
      // Sin contestar nada, el boton «Dame la lista» tiene que servir igual:
      // el §4.1 del spec dice que las tres preguntas se pueden dejar en
      // blanco, y un cuerpo roto ahi seria un boton que no funciona.
      nombre: "sin contestar nada, el cuerpo se arma igual",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(["Sala", "Cocina"], {}, []);
        const hayUsuario = cuerpo.messages.some((m) => m.role === "user");
        return {
          ok: hayUsuario && JSON.stringify(cuerpo).includes("Cocina"),
          detalle: JSON.stringify(cuerpo.messages).slice(0, 200),
        };
      },
    },
    {
      // Lo que Bruno le sigue diciendo despues de la primera lista («la
      // alberca al final»). Va al final y en orden: si se perdiera, la lista
      // se reharia ignorando lo ultimo que pidio.
      nombre: "lo que Bruno siguió escribiendo viaja al final y en orden",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(
          ["Sala"],
          {},
          [
            { role: "assistant", content: "primera lista" },
            { role: "user", content: "la alberca al final" },
          ]
        );
        const ultimos = cuerpo.messages.slice(-2);
        return {
          ok:
            ultimos[0].content === "primera lista" &&
            ultimos[1].content === "la alberca al final" &&
            ultimos[1].role === "user",
          detalle: JSON.stringify(ultimos),
        };
      },
    },
    {
      nombre: "los cuartos van con su nombre exacto, sin acomodar ni corregir",
      fn: () => {
        const cuerpo = ctx.cuerpoDelRequest(["Roof garden", "Área de lavado"], {}, []);
        const texto = JSON.stringify(cuerpo.messages);
        return {
          ok: texto.includes("Roof garden") && texto.includes("Área de lavado"),
          detalle: texto.slice(0, 200),
        };
      },
    },

    // ---------------------------------------------------------------
    // La llave
    // ---------------------------------------------------------------
    {
      nombre: "la llave se enseña tapada, con los últimos cuatro",
      fn: () => {
        const t = ctx.llaveTapada("sk-abcdefghijklmnop1234");
        return {
          ok: t.endsWith("1234") && !t.includes("abcdefghij") && t.length < 24,
          detalle: t,
        };
      },
    },
    {
      // Ensenar los ultimos cuatro de una llave corta es ensenar media llave.
      nombre: "una llave corta se tapa entera, no se enseña a medias",
      fn: () => {
        const t = ctx.llaveTapada("sk-12");
        return { ok: !t.includes("12"), detalle: t };
      },
    },
    {
      nombre: "sin llave no se inventa nada que enseñar",
      fn: () => {
        const t = ctx.llaveTapada("");
        return { ok: t === "", detalle: JSON.stringify(t) };
      },
    },
  ];
};
