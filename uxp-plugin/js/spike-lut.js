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
  for (let i = 0; i < cuantos; i++) {
    let etiqueta = "?";
    let param = null;
    try {
      param = componente.getParam(i);
      etiqueta = await param.getDisplayName();
    } catch (e) {
      etiqueta = "error: " + e.message;
    }
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
      detalle: encabezado + " | NINGUN parametro menciona LUT | " + nombres.join(" ; "),
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
  const tiempoCero = premierepro.TickTime ? premierepro.TickTime.createWithSeconds(0) : null;
  try {
    antes = String(await paramLut.getValueAtTime(tiempoCero));
  } catch (e) {
    antes = "getValueAtTime fallo: " + e.message;
  }

  // La firma de createSetValueAction no esta documentada para ComponentParam
  // --la referencia solo la documenta en Properties, con tres argumentos--
  // asi que se prueban las dos plausibles y se reporta cual sirvio.
  const intentosDeEscritura = [];
  let escribio = false;
  const firmas = [
    ["(valor, true)", () => paramLut.createSetValueAction(RUTA_LUT, true)],
    ["(valor)", () => paramLut.createSetValueAction(RUTA_LUT)],
  ];
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
      detalle: encabezado + " | no se pudo escribir la ruta: " +
        intentosDeEscritura.join(" ; ") +
        " | valor antes: " + antes +
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
