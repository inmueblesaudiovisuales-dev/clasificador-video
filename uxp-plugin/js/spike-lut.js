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
  let componente = null;
  let matchUsado = null;
  for (const nombre of MATCHNAMES_LUMETRI) {
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
  let cuantos = 0;
  try {
    cuantos = componente.getParamCount();
  } catch (e) {
    return {
      ok: false,
      detalle: "getParamCount fallo: " + e.message +
        " | metodos del componente: " + metodosDe(componente),
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

  try {
    runTransaction(
      project,
      () => paramLut.createSetValueAction(RUTA_LUT, true),
      "Spike: poner la ruta del LUT"
    );
  } catch (e) {
    return {
      ok: false,
      detalle: encabezado + " | createSetValueAction con una ruta fallo: " + e.message +
        " | metodos del parametro: " + metodosDe(paramLut),
    };
  }

  let leido = "no se pudo leer";
  try {
    const tiempo = premierepro.TickTime.createWithSeconds(0);
    leido = String(await paramLut.getValueAtTime(tiempo));
  } catch (e) {
    leido = "getValueAtTime fallo: " + e.message;
  }

  return {
    ok: leido === RUTA_LUT,
    detalle: encabezado + " | se escribio la ruta y al releer quedo: " + leido +
      " (esperado " + RUTA_LUT + ")",
  };
});
