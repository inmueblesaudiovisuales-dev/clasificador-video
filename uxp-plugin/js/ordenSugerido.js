// El orden sugerido de los cuartos: la parte que PIENSA.
//
// Aqui no hay `require("premierepro")`, ni `fetch`, ni `document`. Es a
// proposito: asi esto corre con `node uxp-plugin/pruebas/correr.js` sin abrir
// Premiere, y las comprobaciones que sostienen el diseno se corren siempre y
// no cuando alguien se acuerda. Lo que habla con el mundo vive aparte
// (`deepseek.js`, `cuartosDelProyecto.js`, `llave.js`).
//
// Ese corte tiene un beneficio de lado que Bruno pidio explicitamente:
// cambiar de proveedor es cambiar `deepseek.js`, no esto.
//
// Spec: docs/superpowers/specs/2026-09-14-orden-sugerido-de-cuartos-design.md

const MODELO = "deepseek-chat";

// El de conversacion, no el de razonamiento. Esto no es una cadena de
// razonamiento: es acomodar diez nombres con criterio de recorrido, y el de
// razonamiento cuesta y tarda mas para la misma respuesta. Cambiarlo es esta
// linea.

// Lo que se le dice al modelo. Es el corazon del §3 del spec y por eso esta
// escrito con todas sus letras en vez de resumido.
//
// EL MATIZ QUE NO SE PUEDE PERDER: el modelo sabe por que la cocina va
// despues del comedor --eso es logica de recorrido y la tiene de sobra-- pero
// NO sabe que hay en la cocina de Bruno, porque no vio el video y nunca lo va
// a ver. Un modelo describiendo una cocina que no vio («la cocina integral
// con cubierta de granito») es exactamente el modo de falla que este repo
// lleva un mes evitando: adivinar en silencio y sonar seguro.
function promptDeSistema(cuartos) {
  return [
    "Eres el asistente de un editor de video mexicano que hace recorridos de",
    "propiedades en venta o renta. Tu trabajo es proponer EN QUE ORDEN deben ir",
    "los cuartos en el video: el recorrido que debe llevar el espectador.",
    "",
    "NO viste el material. No sabes que hay adentro de ningun cuarto, como se ve",
    "ni con que se grabo. Por eso:",
    "- La linea de cada cuarto dice POR QUE VA AHI en el recorrido, no que hay",
    "  adentro. «Se entra por aqui» sirve; «la cocina integral con cubierta de",
    "  granito» es inventado y no se vale.",
    "- Solo hablas de esta propiedad en concreto si el editor te lo conto el",
    "  mismo en la conversacion.",
    "- Si no tienes una razon de recorrido que dar, da la generica. No rellenes",
    "  con detalles.",
    "",
    "Los cuartos son EXACTAMENTE estos, y los devuelves escritos igual --con sus",
    "acentos, sus mayusculas y sus numeros tal cual--, sin corregir nada, sin",
    "agrupar, sin partir ninguno en dos y sin agregar ninguno que no este:",
    cuartos.map((c) => "- " + c).join("\n"),
    "",
    "Tienen que estar TODOS y ninguno de mas.",
    "",
    "Contestas SOLO con JSON, con esta forma exacta:",
    '{"orden": [{"cuarto": "<nombre tal cual>", "porque": "<una linea corta>"}]}',
    "",
    "Sin texto antes ni despues. Escribe en espanol de Mexico, de tu, y corto.",
  ].join("\n");
}

// Lo que el editor contesto en los chips, vuelto una frase. Se manda como
// primer mensaje suyo y no metido en el prompt de sistema: es lo que EL dijo,
// y mezclarlo con las instrucciones hace que se confunda quien dijo que.
function contextoDeRespuestas(respuestas) {
  const partes = [];
  if (respuestas && respuestas.propiedad) {
    partes.push("La propiedad es: " + respuestas.propiedad + ".");
  }
  if (respuestas && respuestas.para && respuestas.para.length) {
    partes.push("El video es para: " + respuestas.para.join(", ") + ".");
  }
  if (respuestas && respuestas.lucir) {
    partes.push("Lo que hay que lucir: " + respuestas.lucir + ".");
  }
  // Sin contestar nada tambien tiene que servir: el §4.1 del spec deja las
  // tres preguntas en blanco y el boton «Dame la lista» activo desde el
  // primer momento. Un cuerpo roto aqui seria un boton que no funciona.
  partes.push("Dame el orden de los cuartos.");
  return partes.join(" ");
}

// El objeto que se le manda a la API. No la manda --eso es `deepseek.js`--
// solo lo arma.
//
// `conversacion` es lo que siguio despues de la primera lista («la alberca al
// final»), en orden y al final: si se perdiera, la lista se reharia ignorando
// lo ultimo que pidio Bruno.
function cuerpoDelRequest(cuartos, respuestas, conversacion) {
  return {
    model: MODELO,
    messages: [
      { role: "system", content: promptDeSistema(cuartos || []) },
      { role: "user", content: contextoDeRespuestas(respuestas || {}) },
    ].concat(conversacion || []),
  };
}

// Saca el JSON de lo que sea que haya contestado el modelo.
//
// Se rescata el JSON envuelto en ```json … ``` y el que viene con texto antes
// o despues, aunque se le haya pedido que no: los modelos lo hacen de todos
// modos, y tratarlo como error seria fallar por una formalidad con la
// respuesta buena adentro. Lo que NO se hace es adivinar una lista donde no
// la hay.
//
// Nunca tira: una respuesta fea es un caso normal, no una excepcion. Devuelve
// { ok, lista, error } y quien llama decide que ensenar.
function leerRespuesta(texto) {
  const crudo = String(texto == null ? "" : texto).trim();
  if (!crudo) {
    return { ok: false, lista: [], error: "El modelo no contesto nada." };
  }

  const json = recortarJson(crudo);
  if (!json) {
    return {
      ok: false,
      lista: [],
      error: "El modelo contesto con texto en vez de la lista.",
    };
  }

  let datos;
  try {
    datos = JSON.parse(json);
  } catch (e) {
    return { ok: false, lista: [], error: "La respuesta del modelo no se pudo leer." };
  }

  if (!datos || !Array.isArray(datos.orden)) {
    return {
      ok: false,
      lista: [],
      error: "La respuesta llego con otra forma: no trae la lista de cuartos.",
    };
  }

  const lista = [];
  for (const renglon of datos.orden) {
    const cuarto = renglon && typeof renglon.cuarto === "string" ? renglon.cuarto.trim() : "";
    if (!cuarto) {
      return {
        ok: false,
        lista: [],
        error: "La lista trae un renglon sin nombre de cuarto.",
      };
    }
    // El porque SI puede faltar: Bruno lo pidio, pero si el modelo no lo
    // manda, el orden --que es lo que vino a ver-- sigue sirviendo. Se queda
    // vacio en vez de tumbar la respuesta entera.
    const porque = renglon && typeof renglon.porque === "string" ? renglon.porque.trim() : "";
    lista.push({ cuarto: cuarto, porque: porque });
  }

  if (!lista.length) {
    return { ok: false, lista: [], error: "El modelo devolvio una lista vacia." };
  }

  return { ok: true, lista: lista, error: "" };
}

// Encuentra el primer objeto JSON dentro de un texto. Cuenta llaves en vez de
// usar una expresion regular porque el JSON anida y una regular no sabe
// contar; y se salta las llaves que van DENTRO de una cadena, que es lo que
// romperia con un cuarto que se llame «Sala {grande}».
function recortarJson(texto) {
  const inicio = texto.indexOf("{");
  if (inicio === -1) return "";

  let nivel = 0;
  let enCadena = false;
  let escapado = false;

  for (let i = inicio; i < texto.length; i++) {
    const c = texto[i];
    if (enCadena) {
      if (escapado) escapado = false;
      else if (c === "\\") escapado = true;
      else if (c === '"') enCadena = false;
      continue;
    }
    if (c === '"') enCadena = true;
    else if (c === "{") nivel++;
    else if (c === "}") {
      nivel--;
      if (nivel === 0) return texto.slice(inicio, i + 1);
    }
  }
  return "";
}

// LA REGLA QUE SOSTIENE TODO EL DISENO (§6 del spec).
//
// La lista tiene que traer TODOS los cuartos de Bruno y ninguno inventado. Si
// el modelo se salta uno o se saca uno de la manga, el panel lo MARCA en vez
// de ensenar la lista como si nada.
//
// Por que tan en serio: una guia a la que le falta la cocina hace que se te
// olvide la cocina al editar, y eso no se nota hasta despues de entregar. Es
// la misma familia de los ocho bugs del 2026-08-22 -- dos partes del programa
// diciendo cosas distintas del mismo dato, cada una haciendo exactamente lo
// que su codigo dice.
//
// SE COMPARA POR IGUALDAD EXACTA. Nada de `trim`, `toLowerCase` ni quitar
// acentos: «Recamara 1» y «Recámara 1» son un cuarto que falta y otro
// inventado, no un empate. Normalizar aqui esconderia justo el caso que esto
// existe para atrapar.
function revisarLista(lista, cuartosReales) {
  const propuestos = (lista || []).map((r) => r.cuarto);
  const reales = cuartosReales || [];

  const faltan = reales.filter((c) => propuestos.indexOf(c) === -1);
  const inventados = propuestos.filter(
    (c, i) => reales.indexOf(c) === -1 && propuestos.indexOf(c) === i
  );

  // Un cuarto dos veces no es invento ni falta, pero en una guia de recorrido
  // significa pasar dos veces por el mismo lugar. Se marca aparte para poder
  // decirlo con sus palabras.
  const repetidos = propuestos.filter(
    (c, i) => propuestos.indexOf(c) === i && propuestos.lastIndexOf(c) !== i
  );

  return { faltan: faltan, inventados: inventados, repetidos: repetidos };
}

// Todo lo que hay que decirle a Bruno antes de que lea la lista, en sus
// palabras. Vacio cuando no hay nada que decir.
function avisosDeLaRevision(revision) {
  const avisos = [];
  if (revision.faltan.length) {
    avisos.push(
      revision.faltan.length === 1
        ? "Le falta un cuarto: " + revision.faltan[0] + "."
        : "Le faltan " + revision.faltan.length + " cuartos: " + revision.faltan.join(", ") + "."
    );
  }
  if (revision.inventados.length) {
    avisos.push(
      "Esto no es tuyo, se lo invento: " + revision.inventados.join(", ") + "."
    );
  }
  if (revision.repetidos.length) {
    avisos.push("Repitio: " + revision.repetidos.join(", ") + ".");
  }
  return avisos;
}

// La guia como texto plano, que es lo que se lleva el boton de copiar.
function guiaComoTexto(lista, revision) {
  const renglones = lista.map((r, i) => {
    const inventado = revision && revision.inventados.indexOf(r.cuarto) !== -1;
    const marca = inventado ? "  (este no es tuyo)" : "";
    return i + 1 + ". " + r.cuarto + (r.porque ? " — " + r.porque : "") + marca;
  });
  const avisos = revision ? avisosDeLaRevision(revision) : [];
  return renglones.join("\n") + (avisos.length ? "\n\n" + avisos.join("\n") : "");
}
