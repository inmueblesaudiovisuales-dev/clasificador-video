// SPIKE DESCARTABLE. No es codigo de produccion y no se queda en el plugin.
//
// Responde UNA pregunta que no se puede contestar desde el repo: ¿se le
// puede poner un LUT de entrada al MASTER CLIP desde la API de UXP, sin
// armar una secuencia? La documentacion dice que `getComponentChain` existe
// en `ClipProjectItem` y que `VideoFilterFactory.createComponent(matchName)`
// crea un efecto, pero NO dice el matchName de Lumetri ni si su parametro de
// LUT de entrada acepta una ruta de archivo. Eso solo lo dice Premiere.
//
// Todo lo de aqui es defensivo a proposito: prueba varios nombres, enumera
// lo que encuentre y REPORTA en vez de asumir. Un spike que falla con un
// dato util vale mas que uno que se cae con "undefined is not a function".
//
// Cuando la respuesta este escrita en el handoff, este archivo se borra
// junto con su <script> en index.html.

// Bruno: pon aqui la ruta de tu .cube y vuelve a cargar el plugin. Si la
// dejas vacia, el spike igual sirve -- enumera los parametros de Lumetri,
// que es la mitad importante; lo unico que no hace es intentar aplicarlo.
const RUTA_LUT = "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/luts/2_SGamut3CineSLog3_To_LC-709TypeA.cube";

// Los candidatos a matchName de Lumetri. Los efectos de Premiere llevan
// prefijo `PR.`, los heredados de After Effects `AE.`; Lumetri viene de AE,
// pero no esta documentado cual de los dos usa en esta version.
const MATCHNAMES_LUMETRI = [
  "AE.ADBE Lumetri",
  "PR.ADBE Lumetri",
  "ADBE Lumetri",
  "AE.ADBE LumetriColor",
  "PR.ADBE LumetriColor",
];

// Todo lo que se pueda decir de un valor sin saber que es. El parametro de
// LUT no guarda la ruta como texto: guarda un objeto, y "[object Object]" no
// alcanza para saber que ponerle adentro.
function describirValor(v) {
  if (v === null || v === undefined) return String(v);
  const tipo = typeof v;
  if (tipo !== "object") return tipo + " " + String(v);

  const partes = ["objeto"];
  try { partes.push("clase=" + (v.constructor && v.constructor.name)); } catch (e) { /* nada */ }
  try { partes.push("claves propias=[" + Object.keys(v).join(", ") + "]"); } catch (e) { /* nada */ }
  try { partes.push("metodos=[" + Object.getOwnPropertyNames(Object.getPrototypeOf(v)).join(", ") + "]"); } catch (e) { /* nada */ }
  try { partes.push("json=" + JSON.stringify(v)); } catch (e) { partes.push("json no serializable"); }
  // Los getters sin argumentos suelen ser donde vive el dato de verdad.
  try {
    const leidos = [];
    for (const nombre of Object.getOwnPropertyNames(Object.getPrototypeOf(v))) {
      if (nombre === "constructor" || typeof v[nombre] !== "function") continue;
      if (v[nombre].length !== 0) continue;  // solo los que no piden argumentos
      try { leidos.push(nombre + "()=" + String(v[nombre]())); } catch (e) { /* se salta */ }
    }
    if (leidos.length) partes.push("getters=[" + leidos.join(" ; ") + "]");
  } catch (e) { /* nada */ }
  return partes.join(" ");
}

// Metodos reales de un objeto en runtime. La otra vez esto salvo horas: la
// API declara metodos en el .d.ts que en Premiere no existen (ver la nota
// larga al tope de importClip.js).
function metodosDe(obj) {
  if (!obj) return "objeto nulo";
  try {
    return Object.getOwnPropertyNames(Object.getPrototypeOf(obj)).join(", ");
  } catch (e) {
    return "no se pudo enumerar: " + e.message;
  }
}

// Saca de la cadena el componente ya montado -- el unico con el que se
// puede hablar. Se vuelve a pedir la cadena al clip en vez de reusar la de
// antes: no sabemos si el objeto viejo ve lo que se agrego despues.
//
// Se prueban varios nombres de metodo a proposito. La referencia de Adobe
// documenta `getComponentCount`/`getComponentAtIndex`, pero esta version ya
// nos mintio una vez (la fabrica devuelve un objeto pelon), asi que aqui se
// intenta y se reporta, no se asume.
async function recuperarComponenteDeLaCadena(clip, tipoVideo, filtroNombre) {
  const premierepro = require("premierepro");
  const notas = [];

  let cadena;
  try {
    cadena = await clip.getComponentChain(tipoVideo);
  } catch (e) {
    return { componente: null, detalle: "no se pudo repedir la cadena: " + e.message };
  }
  notas.push("metodos de la cadena: " + metodosDe(cadena));

  let cuantos = null;
  for (const nombre of ["getComponentCount", "componentCount", "getComponentsCount"]) {
    if (typeof cadena[nombre] === "function") {
      try {
        cuantos = await cadena[nombre]();
        notas.push(nombre + "() = " + cuantos);
        break;
      } catch (e) {
        notas.push(nombre + "() fallo: " + e.message);
      }
    }
  }
  if (cuantos === null) {
    return { componente: null, detalle: notas.join(" | ") };
  }

  // Se recorre al reves: Lumetri es lo ultimo que se agrego, y asi no se
  // devuelve por error algun efecto intrinseco del clip (Motion, Opacity)
  // que vive al principio de la cadena.
  const vistos = [];
  for (let i = cuantos - 1; i >= 0; i--) {
    let comp = null;
    for (const nombre of ["getComponentAtIndex", "getComponent"]) {
      if (typeof cadena[nombre] === "function") {
        try { comp = await cadena[nombre](i); break; } catch (e) { /* siguiente */ }
      }
    }
    if (!comp) continue;

    // Mismo patron que FolderItem.cast/ClipProjectItem.cast en el resto del
    // plugin: lo que devuelve la API a veces necesita el cast para exponer
    // sus metodos.
    if (premierepro.Component && typeof premierepro.Component.cast === "function") {
      try { comp = premierepro.Component.cast(comp) || comp; } catch (e) { /* se queda el original */ }
    }

    let etiqueta = "?";
    try { etiqueta = await comp.getDisplayName(); } catch (e) { etiqueta = "sin displayName"; }
    vistos.push(i + "=" + etiqueta);

    // El filtro importa: sin el, se devolveria el ultimo efecto que sepa
    // hablar --Motion, Opacity, lo que sea-- y se leerian los parametros
    // equivocados creyendo que son los de Lumetri.
    const calzaElNombre = !filtroNombre ||
      String(etiqueta).toLowerCase().indexOf(filtroNombre.toLowerCase()) !== -1;
    if (calzaElNombre && typeof comp.getParamCount === "function") {
      notas.push("componentes en la cadena: " + vistos.join(", "));
      return { componente: comp, detalle: notas.join(" | ") };
    }
  }

  notas.push("ningun componente calza «" + (filtroNombre || "cualquiera") +
    "» y expone getParamCount (de " + cuantos + ")");
  notas.push("componentes vistos: " + vistos.join(", "));
  return { componente: null, detalle: notas.join(" | ") };
}

registrarPrueba("spike: con que matchName se crea Lumetri", async () => {
  const premierepro = require("premierepro");
  const factory = premierepro.VideoFilterFactory;
  if (!factory) {
    return {
      ok: false,
      detalle: "premierepro.VideoFilterFactory no existe. Lo que si hay en " +
        "premierepro: " + Object.keys(premierepro).join(", "),
    };
  }

  const intentos = [];
  let ganador = null;
  for (const nombre of MATCHNAMES_LUMETRI) {
    try {
      const componente = await factory.createComponent(nombre);
      if (componente) {
        intentos.push(nombre + " => OK");
        if (!ganador) ganador = nombre;
      } else {
        intentos.push(nombre + " => devolvio nulo");
      }
    } catch (e) {
      intentos.push(nombre + " => " + e.message);
    }
  }

  return {
    ok: !!ganador,
    detalle: "matchName que funciona: " + (ganador || "NINGUNO") +
      " | intentos: " + intentos.join(" ; ") +
      " | metodos de VideoFilterFactory: " + metodosDe(factory),
  };
});

registrarPrueba("spike: parametros de Lumetri en el master clip", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["SpikeLUT"]);
  const clip = await importOrReuseClip(project, folder, CLIP_587);
  if (!clip) return { ok: false, detalle: "no se pudo importar " + CLIP_587 };

  // La pregunta 1: ¿el master clip tiene cadena de efectos de video?
  const tipoVideo = premierepro.Constants.MediaType.VIDEO;
  let cadena;
  try {
    cadena = await clip.getComponentChain(tipoVideo);
  } catch (e) {
    return {
      ok: false,
      detalle: "getComponentChain(VIDEO) fallo: " + e.message +
        " | MediaType disponibles: " + Object.keys(premierepro.Constants.MediaType || {}).join(", ") +
        " | metodos del clip: " + metodosDe(clip),
    };
  }
  if (!cadena) {
    return { ok: false, detalle: "getComponentChain(VIDEO) devolvio nulo" };
  }

  // La pregunta 2: ¿se le puede colgar Lumetri?
  //
  // Primero se mira si ya esta: el clip se reusa entre corridas, y sin esto
  // cada vez que Bruno le da al boton se apila otro Lumetri encima del
  // anterior. Ademas de basura, eso hace ambiguo cual de todos se leyo.
  const yaMontado = await recuperarComponenteDeLaCadena(clip, tipoVideo, "lumetri");
  let componente = null;
  let matchUsado = null;
  if (yaMontado.componente) {
    componente = yaMontado.componente;
    matchUsado = "ya estaba montado";
  }
  for (const nombre of componente ? [] : MATCHNAMES_LUMETRI) {
    try {
      const c = await premierepro.VideoFilterFactory.createComponent(nombre);
      if (c) { componente = c; matchUsado = nombre; break; }
    } catch (e) { /* siguiente candidato */ }
  }
  if (!componente) {
    return {
      ok: false,
      detalle: "ningun matchName de Lumetri creo componente | metodos de la cadena: " +
        metodosDe(cadena),
    };
  }

  try {
    runTransaction(
      project,
      () => cadena.createAppendComponentAction(componente),
      "Spike: poner Lumetri al master clip"
    );
  } catch (e) {
    return {
      ok: false,
      detalle: "createAppendComponentAction fallo con " + matchUsado + ": " + e.message +
        " | metodos de la cadena: " + metodosDe(cadena),
    };
  }

  // La pregunta 3, la que importa: ¿como se llaman sus parametros y hay uno
  // de LUT de entrada? Se enumeran TODOS con su nombre visible, porque el
  // nombre exacto es justo lo que no sabemos.
  //
  // Lo que devuelve la fabrica NO sirve para preguntarle nada: su prototipo
  // trae solo `constructor` (medido en la corrida del 2026-08-10, falla
  // `getParamCount is not a function`). Es un objeto de ida, para pasarselo
  // a la accion de append. El componente con el que SI se puede hablar hay
  // que sacarlo de vuelta de la cadena, ya montado.
  const componenteUsable = await recuperarComponenteDeLaCadena(clip, tipoVideo, "lumetri");
  if (!componenteUsable.componente) {
    return {
      ok: false,
      detalle: "no se pudo recuperar el componente montado. " + componenteUsable.detalle,
    };
  }
  componente = componenteUsable.componente;

  let cuantos = 0;
  try {
    cuantos = componente.getParamCount();
  } catch (e) {
    return {
      ok: false,
      detalle: "getParamCount fallo tambien en el componente recuperado: " + e.message +
        " | metodos: " + metodosDe(componente) +
        " | como se recupero: " + componenteUsable.detalle,
    };
  }

  const nombres = [];
  let paramLut = null;
  let indiceLut = -1;
  let radiografia = "";  // como se ve el primer parametro por dentro
  for (let i = 0; i < cuantos; i++) {
    let param = null;
    try {
      // Con `await`: la corrida anterior fallo con «getDisplayName is not a
      // function» en los 130 parametros a la vez, que es la firma de estar
      // hablandole a una promesa en vez de al objeto. La referencia dice que
      // getParam devuelve el objeto directo, pero esta version ya nos mintio
      // dos veces sobre lo mismo.
      param = await componente.getParam(i);
    } catch (e) {
      nombres.push(i + "=no se pudo obtener: " + e.message);
      continue;
    }
    if (premierepro.ComponentParam && typeof premierepro.ComponentParam.cast === "function") {
      try { param = premierepro.ComponentParam.cast(param) || param; } catch (e) { /* se queda */ }
    }
    if (!radiografia) {
      radiografia = "el parametro 0 por dentro: " + metodosDe(param) +
        " | propias: " + Object.keys(param || {}).join(", ");
    }

    // Como se le pregunta el nombre tampoco esta claro, asi que se prueban
    // las formas plausibles antes de darse por vencido.
    let etiqueta = null;
    for (const via of ["getDisplayName", "getName", "displayName", "name"]) {
      try {
        if (typeof param[via] === "function") { etiqueta = await param[via](); break; }
        if (typeof param[via] === "string") { etiqueta = param[via]; break; }
      } catch (e) { /* siguiente via */ }
    }
    if (etiqueta === null) etiqueta = "sin nombre legible";

    nombres.push(i + "=" + etiqueta);
    const bajo = String(etiqueta).toLowerCase();
    if (paramLut === null && bajo.indexOf("lut") !== -1) {
      paramLut = param;
      indiceLut = i;
    }
  }

  const encabezado = "matchName=" + matchUsado + ", " + cuantos + " parametros";
  if (!paramLut) {
    return {
      ok: false,
      // La lista completa de 130 nombres es el dato que se viene a buscar:
      // sin ella no hay como saber por que nombre pedir el LUT.
      detalle: encabezado + " | NINGUN parametro menciona LUT | " + radiografia +
        " | " + nombres.join(" ; "),
    };
  }

  // La pregunta 4: ¿acepta una ruta de archivo? Solo si Bruno puso un .cube.
  if (!RUTA_LUT) {
    return {
      ok: true,
      detalle: encabezado + " | parametro de LUT en el indice " + indiceLut +
        " | metodos del parametro: " + metodosDe(paramLut) +
        " | NO se intento aplicar: RUTA_LUT esta vacia" +
        " | todos: " + nombres.join(" ; "),
    };
  }

  const metodosDelParam = metodosDe(paramLut);

  // Que valor tiene ANTES. Sirve para dos cosas: saber de que tipo es el
  // parametro --si es un numero, un LUT no se pone con una ruta y hay que
  // buscar otra via-- y tener contra que comparar despues.
  let antes = "no se pudo leer";
  let valorPrevio = null;
  const tiempoCero = premierepro.TickTime ? premierepro.TickTime.createWithSeconds(0) : null;
  try {
    valorPrevio = await paramLut.getValueAtTime(tiempoCero);
    antes = describirValor(valorPrevio);
  } catch (e) {
    antes = "getValueAtTime fallo: " + e.message;
  }
  let arranque = "no se leyo";
  try {
    arranque = describirValor(await paramLut.getStartValue());
  } catch (e) {
    arranque = "getStartValue fallo: " + e.message;
  }

  // La corrida del 2026-08-10 dijo «Illegal Parameter type» con la ruta como
  // texto, y que el valor actual es un OBJETO. O sea que el parametro de LUT
  // no se pone con un string. Aqui se prueba, en orden: el texto (para dejar
  // constancia de que sigue sin funcionar), el objeto que ya tiene con la
  // ruta metida adentro por cada una de sus claves, y el objeto tal cual
  // (control: si este pasa, el problema es el contenido y no el tipo).
  const intentosDeEscritura = [];
  let escribio = false;
  const firmas = [
    ["texto (valor, true)", () => paramLut.createSetValueAction(RUTA_LUT, true)],
    ["texto (valor)", () => paramLut.createSetValueAction(RUTA_LUT)],
  ];
  if (valorPrevio && typeof valorPrevio === "object") {
    firmas.push(["el objeto tal cual", () => paramLut.createSetValueAction(valorPrevio, true)]);
    for (const clave of Object.keys(valorPrevio)) {
      firmas.push(["objeto con ." + clave + " = la ruta", () => {
        const copia = Object.assign({}, valorPrevio);
        copia[clave] = RUTA_LUT;
        return paramLut.createSetValueAction(copia, true);
      }]);
    }
  }
  for (const [comoSeLlama, construir] of firmas) {
    try {
      runTransaction(project, construir, "Spike: poner la ruta del LUT");
      intentosDeEscritura.push(comoSeLlama + " => OK");
      escribio = true;
      break;
    } catch (e) {
      intentosDeEscritura.push(comoSeLlama + " => " + e.message);
    }
  }
  if (!escribio) {
    return {
      ok: false,
      detalle: encabezado + " | parametro de LUT en el indice " + indiceLut +
        " («" + nombres[indiceLut] + "») | no se pudo escribir la ruta: " +
        intentosDeEscritura.join(" ; ") +
        " | VALOR ACTUAL: " + antes +
        " | getStartValue: " + arranque +
        " | metodos del parametro: " + metodosDelParam,
    };
  }

  let leido = "no se pudo leer";
  try {
    leido = String(await paramLut.getValueAtTime(tiempoCero));
  } catch (e) {
    leido = "getValueAtTime fallo: " + e.message;
  }

  return {
    ok: leido === RUTA_LUT,
    detalle: encabezado + " | parametro de LUT en el indice " + indiceLut +
      " | escritura: " + intentosDeEscritura.join(" ; ") +
      " | antes: " + antes + " | despues: " + leido +
      " (esperado " + RUTA_LUT + ")" +
      " | metodos del parametro: " + metodosDelParam +
      " | todos los parametros: " + nombres.join(" ; "),
  };
});
