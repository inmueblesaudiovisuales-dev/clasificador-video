// Registros de autocheck (arnes de construccion). No es codigo de
// produccion: agrupa aqui todas las pruebas `registrarPrueba(...)` de cada
// task para que index.html se quede solo con markup y carga de scripts.
// Se apaga junto con el arnes en Task 13 (AUTOCHECK_ACTIVO = false); con las
// pruebas separadas aqui, ese apagado es borrar este archivo + su <script>,
// no cirugia dentro de index.html.

registrarPrueba("runTransaction crea bin", async (project) => {
  const rootItem = await project.getRootItem();
  const ok = runTransaction(project, () => rootItem.createBinAction("PruebaTask1", true), "Prueba Task 1");
  return { ok: !!ok, detalle: "runTransaction devolvio " + ok };
});

registrarPrueba("resolveBinChain crea y reusa bins anidados", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder1 = await resolveBinChain(project, rootFolder, ["PruebaTask2", "Sub"]);
  const folder2 = await resolveBinChain(project, rootFolder, ["PruebaTask2", "Sub"]);

  const padreItems = await rootFolder.getItems();
  const padre = padreItems.find((i) => i.name === "PruebaTask2");
  if (!padre) {
    return { ok: false, detalle: "No se encontro el bin padre PruebaTask2" };
  }
  const padreFolder = premierepro.FolderItem.cast(padre);
  const hijos = await padreFolder.getItems();
  const cuantosSub = hijos.filter((i) => i.name === "Sub").length;

  const ok =
    folder1 && folder1.name === "Sub" &&
    folder2 && folder2.name === "Sub" &&
    cuantosSub === 1;

  return {
    ok: ok,
    detalle:
      "folder1.name=" + (folder1 && folder1.name) +
      ", folder2.name=" + (folder2 && folder2.name) +
      ", cantidad de bins 'Sub' dentro de PruebaTask2=" + cuantosSub,
  };
});

// LA UNICA LINEA QUE HAY QUE EDITAR PARA CORRER ESTO EN OTRA COMPUTADORA.
//
// Estas pruebas corren DENTRO de Premiere, no en el repo, asi que no hay
// forma de resolver una ruta relativa: Premiere abre el plugin desde su
// propia carpeta y no sabe donde vive el proyecto. Por eso es una ruta
// absoluta y por eso va sola, arriba, en vez de repartida por el archivo
// (la usan 44 lineas de aqui abajo).
//
// Apuntaba a `.../ORGANIZADOR VIDEO/TEST`, que dejo de existir: la limpieza
// de agosto de 2026 renombro `TEST/` a `sample-media/` --colisionaba con
// `tests/` en un filesystem que no distingue mayusculas-- y ademas movio los
// clips a `sample-media/clips/`. O sea que estaba mal por dos motivos a la
// vez, y quien corriera esto se habria topado con «archivo no encontrado» en
// la primera prueba sin saber por que.
const RUTA_MEDIA = "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/sample-media";
const RUTA_TEST_DIR = RUTA_MEDIA + "/clips";
// El proxy NO vive junto a los clips: `sample-media/` los separa en `clips/`
// y `proxy/`, que es como llegan de la tarjeta de la camara.
const RUTA_PROXY_DIR = RUTA_MEDIA + "/proxy";
const CLIP_588 = RUTA_TEST_DIR + "/20260804_PIB0588.MP4";
const CLIP_589 = RUTA_TEST_DIR + "/20260804_PIB0589.MP4";

registrarPrueba("diagnostico: metodos disponibles en FolderItem/ClipProjectItem cast", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);
  let propioFolder = Object.getOwnPropertyNames(Object.getPrototypeOf(rootFolder));

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask3Diag"]);
  // ver metodos de ClipProjectItem tambien
  const items = await folder.getItems();
  let propioClip = "sin items para probar";
  if (items.length) {
    const c = premierepro.ClipProjectItem.cast(items[0]);
    if (c) propioClip = Object.getOwnPropertyNames(Object.getPrototypeOf(c));
  }

  // ¿la misma carpeta obtenida por dos caminos distintos es === ?
  const itemsA = await rootFolder.getItems();
  const itemsB = await rootFolder.getItems();
  const pruebaTask3A = itemsA.find((i) => i.name === "PruebaTask3Diag");
  const pruebaTask3B = itemsB.find((i) => i.name === "PruebaTask3Diag");
  const mismaReferencia = pruebaTask3A === pruebaTask3B;
  const castA = premierepro.FolderItem.cast(pruebaTask3A);
  const castB = premierepro.FolderItem.cast(pruebaTask3B);
  const castEsIgualAlCrudo = castA === pruebaTask3A;
  const dosCastsSonIguales = castA === castB;

  return {
    ok: true,
    detalle:
      "FolderItem prototipo: " + JSON.stringify(propioFolder) +
      " | ClipProjectItem prototipo: " + JSON.stringify(propioClip) +
      " | dos llamadas a getItems() devuelven el mismo objeto (===) para la misma carpeta: " + mismaReferencia +
      " | cast(item) === item: " + castEsIgualAlCrudo +
      " | cast(itemA) === cast(itemB) (mismo item, dos casts): " + dosCastsSonIguales,
  };
});

registrarPrueba("importOrReuseClip: importa el clip dentro del bin destino", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask3"]);
  const clip = await importOrReuseClip(project, folder, CLIP_588);

  if (!clip) {
    return { ok: false, detalle: "importOrReuseClip devolvio null" };
  }
  const mediaPath = await clip.getMediaFilePath();
  const clipsEnDestino = await findClipsConRuta(folder, CLIP_588);

  const ok = mediaPath === CLIP_588 && clipsEnDestino.length === 1;
  return {
    ok: ok,
    detalle:
      "mediaPath devuelto=" + mediaPath +
      ", clips con esa ruta dentro de PruebaTask3=" + clipsEnDestino.length,
  };
});

registrarPrueba("importOrReuseClip: llamar dos veces no duplica el clip", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask3"]);
  await importOrReuseClip(project, folder, CLIP_588);
  await importOrReuseClip(project, folder, CLIP_588);

  const clipsEnDestino = await findClipsConRuta(folder, CLIP_588);
  const ok = clipsEnDestino.length === 1;
  return {
    ok: ok,
    detalle: "clips con ruta " + CLIP_588 + " dentro de PruebaTask3 tras dos llamadas=" + clipsEnDestino.length,
  };
});

registrarPrueba(
  "importOrReuseClip: LA CORRECCION - mover entre dos bins homonimos 'Bano' se detecta y muda el clip",
  async (project) => {
    const premierepro = require("premierepro");
    const rootItem = await project.getRootItem();
    const rootFolder = premierepro.FolderItem.cast(rootItem);

    const banoUno = await resolveBinChain(project, rootFolder, ["Recamara 1", "Bano"]);
    const banoDos = await resolveBinChain(project, rootFolder, ["Recamara 2", "Bano"]);

    await importOrReuseClip(project, banoUno, CLIP_589);
    const clip = await importOrReuseClip(project, banoDos, CLIP_589);

    const enBanoUno = await findClipsConRuta(banoUno, CLIP_589);
    const enBanoDos = await findClipsConRuta(banoDos, CLIP_589);
    // La API de esta version de Premiere no expone getParentBin() ni un id
    // propio en los objetos de runtime (confirmado en la prueba de
    // diagnostico de este mismo archivo), asi que la evidencia de "se
    // movio" viene de contar directamente el contenido real de cada bin
    // homonimo con getItems(), no de preguntarle al clip quien es su padre.
    const mismoClipQueSeDevolvio = clip && enBanoDos.length === 1 && enBanoDos[0] === clip;

    const ok = enBanoUno.length === 0 && enBanoDos.length === 1 && mismoClipQueSeDevolvio;
    return {
      ok: ok,
      detalle:
        "Recamara 1 > Bano tiene " + enBanoUno.length + " clip(s) con esa ruta (debe ser 0), " +
        "Recamara 2 > Bano tiene " + enBanoDos.length + " clip(s) con esa ruta (debe ser 1), " +
        "el clip devuelto por importOrReuseClip es exactamente el que quedo dentro de Recamara 2 > Bano=" + mismoClipQueSeDevolvio,
    };
  }
);

const CLIP_587 = RUTA_TEST_DIR + "/20260804_PIB0587.MP4";

registrarPrueba("applyFlagLabel: 'pick' pone el label FOREST en el clip", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask4"]);
  const clip = await importOrReuseClip(project, folder, CLIP_587);

  // El clip se reusa entre recargas (importOrReuseClip no reimporta), asi
  // que si una corrida anterior ya lo dejo en FOREST, "antes" ya seria
  // FOREST y la comparacion antes/despues no probaria nada. Para que la
  // prueba sea valida en cualquier corrida, primero se fuerza el label a
  // ROSE (reject) directamente, y luego se comprueba que applyFlagLabel con
  // "pick" lo cambia a FOREST.
  applyFlagLabel(project, clip, "reject");
  const indiceAntes = await clip.getColorLabelIndex();
  applyFlagLabel(project, clip, "pick");
  const indiceDespues = await clip.getColorLabelIndex();

  const indiceForest = premierepro.Constants.ProjectItemColorLabel.FOREST;
  const indiceRose = premierepro.Constants.ProjectItemColorLabel.ROSE;
  const ok = indiceAntes === indiceRose && indiceDespues === indiceForest && indiceDespues !== indiceAntes;

  return {
    ok: ok,
    detalle:
      "indice ROSE esperado=" + indiceRose + ", indice antes (tras forzar reject)=" + indiceAntes +
      " | indice FOREST esperado=" + indiceForest + ", indice despues (tras pick)=" + indiceDespues,
  };
});

registrarPrueba("applyFlagLabel: 'destacado' pone el label MANGO en el clip", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask4"]);
  const clip = await importOrReuseClip(project, folder, CLIP_587);

  // Mismo cuidado que la prueba de 'pick': el clip se reusa entre
  // recargas, asi que primero se fuerza otro color para que la
  // comparacion antes/despues pruebe algo.
  applyFlagLabel(project, clip, "reject");
  const indiceAntes = await clip.getColorLabelIndex();
  applyFlagLabel(project, clip, "destacado");
  const indiceDespues = await clip.getColorLabelIndex();

  const colores = premierepro.Constants.ProjectItemColorLabel;
  const indiceMango = colores.MANGO;
  const ok = indiceMango !== undefined &&
    indiceAntes === colores.ROSE && indiceDespues === indiceMango;

  return {
    ok: ok,
    detalle:
      indiceMango === undefined
        ? "MANGO no existe en esta version. Colores disponibles: " + Object.keys(colores).join(", ")
        : "indice MANGO esperado=" + indiceMango + ", indice despues=" + indiceDespues +
          " | indice antes (tras forzar reject)=" + indiceAntes,
  };
});

// fps del clip de prueba CLIP_588 (dron 4K/60p real, ver Task 5). Se
// reutiliza tal cual porque el manifest real (Task 8) todavia no exporta
// fps por clip.
const FPS_CLIP_588 = 59.94005994005994;

registrarPrueba("applyInOut: pone el in/out del clip en los frames pedidos", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask5"]);
  const clip = await importOrReuseClip(project, folder, CLIP_588);
  const clipProjectItem = premierepro.ClipProjectItem.cast(clip);

  applyInOut(project, clip, FPS_CLIP_588, 20, 150);

  // Lectura real de vuelta: ClipProjectItem.getInPoint()/getOutPoint() SI
  // existen, pero (a diferencia de lo que sugiere el .d.ts revisado antes de
  // probar en vivo) exigen un argumento Constants.MediaType — sin el, tiran
  // "Illegal Parameter type" (confirmado en vivo). Con MediaType.ANY
  // funcionan. Comparamos el TickTime devuelto contra el TickTime "esperado"
  // construido con el mismo constructor createWithFrameAndFrameRate, usando
  // TickTime.equals(): verificacion genuina de que el in/out quedo en los
  // frames pedidos, no solo "no truena".
  const frameRate = premierepro.FrameRate.createWithValue(FPS_CLIP_588);
  const inEsperado = premierepro.TickTime.createWithFrameAndFrameRate(20, frameRate);
  const outEsperado = premierepro.TickTime.createWithFrameAndFrameRate(150, frameRate);

  const inReal = await clipProjectItem.getInPoint(premierepro.Constants.MediaType.ANY);
  const outReal = await clipProjectItem.getOutPoint(premierepro.Constants.MediaType.ANY);

  const inCoincide = inReal.equals(inEsperado);
  const outCoincide = outReal.equals(outEsperado);

  const ok = inCoincide && outCoincide;
  return {
    ok: ok,
    detalle:
      "inPoint.ticks esperado=" + inEsperado.ticks + ", real=" + inReal.ticks + ", equals=" + inCoincide +
      " | outPoint.ticks esperado=" + outEsperado.ticks + ", real=" + outReal.ticks + ", equals=" + outCoincide,
  };
});

registrarPrueba("applyInOut: con null/null no toca el in/out existente", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  // Reusa el mismo clip de la prueba anterior, ya con in/out en 20/150 por
  // esa prueba (importOrReuseClip reusa, no reimporta). Si applyInOut(...,
  // null, null) tocara algo, el in/out dejaria de coincidir con 20/150.
  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask5"]);
  const clip = await importOrReuseClip(project, folder, CLIP_588);
  const clipProjectItem = premierepro.ClipProjectItem.cast(clip);

  const inAntes = await clipProjectItem.getInPoint(premierepro.Constants.MediaType.ANY);
  const outAntes = await clipProjectItem.getOutPoint(premierepro.Constants.MediaType.ANY);

  let noTronoException = true;
  try {
    applyInOut(project, clip, FPS_CLIP_588, null, null);
  } catch (e) {
    noTronoException = false;
  }

  const inDespues = await clipProjectItem.getInPoint(premierepro.Constants.MediaType.ANY);
  const outDespues = await clipProjectItem.getOutPoint(premierepro.Constants.MediaType.ANY);

  const frameRate = premierepro.FrameRate.createWithValue(FPS_CLIP_588);
  const inEsperado = premierepro.TickTime.createWithFrameAndFrameRate(20, frameRate);
  const outEsperado = premierepro.TickTime.createWithFrameAndFrameRate(150, frameRate);

  const noCambio = inDespues.equals(inAntes) && outDespues.equals(outAntes);
  const siguenEnLosFramesPedidos = inDespues.equals(inEsperado) && outDespues.equals(outEsperado);

  const ok = noTronoException && noCambio && siguenEnLosFramesPedidos;
  return {
    ok: ok,
    detalle:
      "no lanzo excepcion=" + noTronoException +
      " | in/out antes y despues de null/null son iguales=" + noCambio +
      " | siguen en frame 20/150=" + siguenEnLosFramesPedidos,
  };
});

const PROXY_587 = RUTA_PROXY_DIR + "/20260804_PIB0587S03.MP4";

registrarPrueba("attachProxyIfPresent: adjunta el proxy y hasProxy()/getProxyPath() lo confirman", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask6"]);
  const clip = await importOrReuseClip(project, folder, CLIP_587);
  const clipProjectItem = premierepro.ClipProjectItem.cast(clip);

  const tieneAntes = await clipProjectItem.hasProxy();

  const ok = await attachProxyIfPresent(clip, PROXY_587);
  const tieneDespues = await clipProjectItem.hasProxy();
  const rutaProxy = await clipProjectItem.getProxyPath();

  const okFinal = ok === true && tieneDespues === true && rutaProxy === PROXY_587;
  return {
    ok: okFinal,
    detalle:
      "attachProxyIfPresent devolvio=" + ok +
      " | hasProxy() antes=" + tieneAntes + ", despues=" + tieneDespues +
      " | getProxyPath()=" + rutaProxy + " (esperado " + PROXY_587 + ")",
  };
});

registrarPrueba("attachProxyIfPresent: readjuntar el mismo proxy sigue devolviendo true sin error", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask6"]);
  const clip = await importOrReuseClip(project, folder, CLIP_587);
  const clipProjectItem = premierepro.ClipProjectItem.cast(clip);

  let noTronoException = true;
  let ok2 = false;
  try {
    ok2 = await attachProxyIfPresent(clip, PROXY_587);
  } catch (e) {
    noTronoException = false;
  }

  const tieneDespues = await clipProjectItem.hasProxy();
  const rutaProxy = await clipProjectItem.getProxyPath();

  const okFinal = noTronoException && ok2 === true && tieneDespues === true && rutaProxy === PROXY_587;
  return {
    ok: okFinal,
    detalle:
      "no lanzo excepcion=" + noTronoException +
      " | attachProxyIfPresent (segunda vez) devolvio=" + ok2 +
      " | hasProxy() sigue=" + tieneDespues +
      " | getProxyPath() sigue=" + rutaProxy,
  };
});

registrarPrueba("attachProxyIfPresent: con proxyPath null devuelve false y no toca el clip", async (project) => {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const folder = await resolveBinChain(project, rootFolder, ["PruebaTask6"]);
  const clip = await importOrReuseClip(project, folder, CLIP_587);
  const clipProjectItem = premierepro.ClipProjectItem.cast(clip);

  // Este clip ya tiene el proxy adjunto por la prueba anterior; si
  // attachProxyIfPresent(null) tocara algo, hasProxy()/getProxyPath()
  // dejarian de coincidir con lo ya adjuntado.
  const resultado = await attachProxyIfPresent(clip, null);

  const tieneDespues = await clipProjectItem.hasProxy();
  const rutaProxy = await clipProjectItem.getProxyPath();

  const ok = resultado === false && tieneDespues === true && rutaProxy === PROXY_587;
  return {
    ok: ok,
    detalle:
      "attachProxyIfPresent(clip, null) devolvio=" + resultado + " (esperado false)" +
      " | hasProxy() sin cambios=" + tieneDespues +
      " | getProxyPath() sin cambios=" + rutaProxy,
  };
});

const manifestPrueba = {
  proyecto: "Prueba Task 7",
  clips: [
    {
      ruta: CLIP_587,
      categoria_path: ["PruebaTask7", "Bano"],
      fps: 30,
      in_frame: 10,
      out_frame: 90,
      flag: "pick",
      ruta_proxy: PROXY_587,
    },
    {
      ruta: RUTA_TEST_DIR + "/no-existe.MP4",
      categoria_path: ["PruebaTask7"],
      fps: 30,
      in_frame: null,
      out_frame: null,
      flag: "none",
      ruta_proxy: null,
    },
  ],
};

registrarPrueba(
  "processManifest: organiza el clip valido, registra el error del clip inexistente, y uno no afecta al otro",
  async (project) => {
    const premierepro = require("premierepro");

    const resultado = await processManifest(project, manifestPrueba);

    const okEsperado = ["20260804_PIB0587.MP4"];
    const okCoincide =
      resultado.ok.length === okEsperado.length &&
      resultado.ok.every((nombre, i) => nombre === okEsperado[i]);

    const erroresCoincide =
      resultado.errores.length === 1 &&
      resultado.errores[0].archivo === "no-existe.MP4" &&
      !!resultado.errores[0].mensaje;

    // Lectura real de vuelta del clip que si funciono: bin destino, label,
    // in/out (fps 30, el que trae manifestPrueba) y proxy.
    const rootItem = await project.getRootItem();
    const rootFolder = premierepro.FolderItem.cast(rootItem);
    const banoFolder = await resolveBinChain(project, rootFolder, ["PruebaTask7", "Bano"]);
    const clipsEnBano = await findClipsConRuta(banoFolder, CLIP_587);
    const enBinCorrecto = clipsEnBano.length === 1;

    let labelCorrecto = false;
    let inOutCorrecto = false;
    let proxyCorrecto = false;

    if (enBinCorrecto) {
      const clip = clipsEnBano[0];
      const indice = await clip.getColorLabelIndex();
      labelCorrecto = indice === premierepro.Constants.ProjectItemColorLabel.FOREST;

      const clipProjectItem = premierepro.ClipProjectItem.cast(clip);
      const frameRate = premierepro.FrameRate.createWithValue(30);
      const inEsperado = premierepro.TickTime.createWithFrameAndFrameRate(10, frameRate);
      const outEsperado = premierepro.TickTime.createWithFrameAndFrameRate(90, frameRate);
      const inReal = await clipProjectItem.getInPoint(premierepro.Constants.MediaType.ANY);
      const outReal = await clipProjectItem.getOutPoint(premierepro.Constants.MediaType.ANY);
      inOutCorrecto = inReal.equals(inEsperado) && outReal.equals(outEsperado);

      const tieneProxy = await clipProjectItem.hasProxy();
      const rutaProxy = await clipProjectItem.getProxyPath();
      proxyCorrecto = tieneProxy === true && rutaProxy === PROXY_587;
    }

    // El segundo clip (inexistente) no debe haber quedado en ningun lado
    // dentro de PruebaTask7.
    const pruebaTask7Folder = await resolveBinChain(project, rootFolder, ["PruebaTask7"]);
    const clipsNoExiste = await findClipsConRuta(pruebaTask7Folder, RUTA_TEST_DIR + "/no-existe.MP4");
    const noExisteNoQuedo = clipsNoExiste.length === 0;

    const ok =
      okCoincide && erroresCoincide && enBinCorrecto && labelCorrecto &&
      inOutCorrecto && proxyCorrecto && noExisteNoQuedo;

    return {
      ok: ok,
      detalle:
        "resultado.ok=" + JSON.stringify(resultado.ok) + " (esperado " + JSON.stringify(okEsperado) + ")" +
        " | resultado.errores=" + JSON.stringify(resultado.errores) +
        " | clip en PruebaTask7>Bano=" + enBinCorrecto +
        " | label FOREST=" + labelCorrecto +
        " | in/out 10/90 fps30=" + inOutCorrecto +
        " | proxy adjunto=" + proxyCorrecto +
        " | el clip inexistente no quedo en el proyecto=" + noExisteNoQuedo,
    };
  }
);

registrarPrueba(
  "revisarMaterialDisponible: identifica el faltante y cuenta bien los disponibles",
  async (project) => {
    const resultado = await revisarMaterialDisponible(manifestPrueba);

    const ok =
      resultado.disponibles === 1 &&
      resultado.faltantes.length === 1 &&
      resultado.faltantes[0] === RUTA_TEST_DIR + "/no-existe.MP4";

    return {
      ok: ok,
      detalle:
        "disponibles=" + resultado.disponibles + " (esperado 1)" +
        " | faltantes=" + JSON.stringify(resultado.faltantes),
    };
  }
);

// Manifest con un clip malformado (ruta ausente) EN MEDIO de dos clips
// validos: reproduce el caso real (manifest mal formado a mano, o bug futuro
// de quien lo genera) para probar que un `ruta` nulo no tumba el for entero
// -- antes del fix, clipData.ruta.split(...) truena FUERA del try/catch de
// ese clip y aborta processManifest completo, perdiendo tambien los clips
// validos que venian despues.
const manifestPruebaRutaFaltante = {
  proyecto: "Prueba Task 7 - ruta faltante",
  clips: [
    {
      ruta: CLIP_587,
      categoria_path: ["PruebaTask7RutaFaltante"],
      fps: 30,
      in_frame: null,
      out_frame: null,
      flag: "none",
      ruta_proxy: null,
    },
    {
      ruta: null,
      categoria_path: ["PruebaTask7RutaFaltante"],
      fps: 30,
      in_frame: null,
      out_frame: null,
      flag: "none",
      ruta_proxy: null,
    },
    {
      ruta: CLIP_588,
      categoria_path: ["PruebaTask7RutaFaltante"],
      fps: FPS_CLIP_588,
      in_frame: null,
      out_frame: null,
      flag: "none",
      ruta_proxy: null,
    },
  ],
};

registrarPrueba(
  "processManifest: un clip con ruta faltante en medio del manifest no tumba a los clips validos que le siguen",
  async (project) => {
    const resultado = await processManifest(project, manifestPruebaRutaFaltante);

    const okEsperado = ["20260804_PIB0587.MP4", "20260804_PIB0588.MP4"];
    const okCoincide =
      resultado.ok.length === okEsperado.length &&
      resultado.ok.every((nombre, i) => nombre === okEsperado[i]);

    const errorCoincide =
      resultado.errores.length === 1 &&
      !!resultado.errores[0].archivo &&
      !!resultado.errores[0].mensaje;

    const ok = okCoincide && errorCoincide;
    return {
      ok: ok,
      detalle:
        "resultado.ok=" + JSON.stringify(resultado.ok) + " (esperado " + JSON.stringify(okEsperado) + ")" +
        " | resultado.errores=" + JSON.stringify(resultado.errores) +
        " | el clip con ruta faltante cayo en errores sin abortar el resto=" + errorCoincide,
    };
  }
);

// Task 8: el fps ya no se infiere en el plugin (antes siempre 30, ver el
// placeholder que tenia processManifest); ahora viene del propio manifest
// (clipData.fps). Esta prueba usa un fps distinto al de FPS_CLIP_588
// (59.94005994005994) para que, si algun call site se le olvidara pasar
// clipData.fps y cayera en un valor por defecto o en el de otro clip, el
// in/out calculado no coincidiera con lo esperado.
const manifestPruebaFps = {
  proyecto: "Prueba Task 8 - fps del manifest",
  clips: [
    {
      ruta: CLIP_587,
      categoria_path: ["PruebaTask8Fps"],
      fps: 30,
      in_frame: 20,
      out_frame: 150,
      flag: "none",
      ruta_proxy: null,
    },
  ],
};

registrarPrueba(
  "processManifest: usa clipData.fps (no un valor inferido) al aplicar in/out",
  async (project) => {
    const premierepro = require("premierepro");

    const resultado = await processManifest(project, manifestPruebaFps);

    const rootItem = await project.getRootItem();
    const rootFolder = premierepro.FolderItem.cast(rootItem);
    const folder = await resolveBinChain(project, rootFolder, ["PruebaTask8Fps"]);
    const clipsEnFolder = await findClipsConRuta(folder, CLIP_587);
    const enBinCorrecto = clipsEnFolder.length === 1;

    let inOutCoincideCon30 = false;
    let inOutNoCoincideConOtroFps = false;

    if (enBinCorrecto) {
      const clipProjectItem = premierepro.ClipProjectItem.cast(clipsEnFolder[0]);
      const inReal = await clipProjectItem.getInPoint(premierepro.Constants.MediaType.ANY);
      const outReal = await clipProjectItem.getOutPoint(premierepro.Constants.MediaType.ANY);

      const frameRate30 = premierepro.FrameRate.createWithValue(30);
      const inEsperado30 = premierepro.TickTime.createWithFrameAndFrameRate(20, frameRate30);
      const outEsperado30 = premierepro.TickTime.createWithFrameAndFrameRate(150, frameRate30);
      inOutCoincideCon30 = inReal.equals(inEsperado30) && outReal.equals(outEsperado30);

      // Si el codigo ignorara clipData.fps y usara FPS_CLIP_588 (u otro fps
      // distinto), el in/out real coincidiria con este calculo en vez del de
      // arriba -- confirmamos que NO es el caso.
      const frameRateOtro = premierepro.FrameRate.createWithValue(FPS_CLIP_588);
      const inConOtroFps = premierepro.TickTime.createWithFrameAndFrameRate(20, frameRateOtro);
      const outConOtroFps = premierepro.TickTime.createWithFrameAndFrameRate(150, frameRateOtro);
      inOutNoCoincideConOtroFps = !inReal.equals(inConOtroFps) && !outReal.equals(outConOtroFps);
    }

    const ok = resultado.errores.length === 0 && enBinCorrecto && inOutCoincideCon30 && inOutNoCoincideConOtroFps;

    return {
      ok: ok,
      detalle:
        "resultado.errores=" + JSON.stringify(resultado.errores) +
        " | clip en PruebaTask8Fps=" + enBinCorrecto +
        " | in/out calculado con fps=30 (el del manifest)=" + inOutCoincideCon30 +
        " | in/out NO coincide con fps=" + FPS_CLIP_588 + " (otro clip)=" + inOutNoCoincideConOtroFps,
    };
  }
);

// Helper solo para las pruebas: cuenta cuantos clips con esa ruta hay
// directamente dentro de una carpeta (sin bajar a subcarpetas), para poder
// afirmar "vacio" o "exactamente uno" con evidencia real, no solo "no truena".
//
// No reusa findClipByPath (js/importClip.js) a proposito: esa funcion busca
// en profundidad y se detiene en la PRIMERA coincidencia (para resolver
// "¿donde esta el clip?"); esta cuenta TODAS las coincidencias pero solo en
// el nivel superficial de una carpeta puntual (para afirmar "cuantos hay
// aqui"). Son dos preguntas distintas: compartir el escaneo de items()
// obligaria a una de las dos a cargar semantica que no necesita.
// Task 9: el manifest de prueba en el Escritorio (prueba-task9.json), a
// proposito fuera de cualquier carpeta del proyecto -- confirma que el
// plugin lee de donde el usuario elija, no de una carpeta fija. Aqui se
// llama processManifest directo con el mismo contenido (el dialogo nativo
// para elegirlo no se puede automatizar; ver Task 13).
const manifestPruebaTask9 = {
  proyecto: "Prueba Task 9",
  orientacion: "vertical",
  clips: [
    {
      orden: 1,
      ruta: CLIP_589,
      categoria_path: ["PruebaTask9"],
      fps: FPS_CLIP_588,
      in_frame: null,
      out_frame: null,
      flag: "none",
      ruta_proxy: null,
    },
  ],
};

registrarPrueba(
  "Task 9: processManifest con el manifest de ~/Desktop/prueba-task9.json deja el clip en PruebaTask9",
  async (project) => {
    const premierepro = require("premierepro");

    const resultado = await processManifest(project, manifestPruebaTask9);

    const okEsperado = ["20260804_PIB0589.MP4"];
    const okCoincide =
      resultado.ok.length === okEsperado.length &&
      resultado.ok.every((nombre, i) => nombre === okEsperado[i]);
    const sinErrores = resultado.errores.length === 0;

    const rootItem = await project.getRootItem();
    const rootFolder = premierepro.FolderItem.cast(rootItem);
    const folder = await resolveBinChain(project, rootFolder, ["PruebaTask9"]);
    const clipsEnFolder = await findClipsConRuta(folder, CLIP_589);
    const enBinCorrecto = clipsEnFolder.length === 1;

    const ok = okCoincide && sinErrores && enBinCorrecto;
    return {
      ok: ok,
      detalle:
        "resultado.ok=" + JSON.stringify(resultado.ok) + " (esperado " + JSON.stringify(okEsperado) + ")" +
        " | resultado.errores=" + JSON.stringify(resultado.errores) +
        " | clip dentro de PruebaTask9=" + enBinCorrecto,
    };
  }
);

// Caso feo 1: archivo elegido que no es JSON valido. No se puede invocar
// importarManifestDesdeArchivo() completo sin el dialogo nativo (Task 13),
// asi que se prueba el mismo fragmento de logica que usa la funcion real
// (try/catch alrededor de JSON.parse) tal cual aparece en el codigo.
registrarPrueba(
  "Task 9: JSON.parse sobre un archivo invalido lanza y el catch produce un mensaje (no toca el proyecto)",
  async (project) => {
    const premierepro = require("premierepro");
    const rootItem = await project.getRootItem();
    const rootFolder = premierepro.FolderItem.cast(rootItem);

    // Conteo real ANTES del intento invalido, para comparar contra el
    // conteo DESPUES: si algo llegara a tocar el proyecto raiz durante el
    // parseo fallido, la cantidad de items cambiaria.
    const itemsAntes = await rootFolder.getItems();
    const cantidadAntes = itemsAntes.length;

    let mensaje = null;
    let lanzo = false;
    try {
      JSON.parse("esto no es json");
    } catch (e) {
      lanzo = true;
      mensaje = "El archivo elegido no es una clasificacion valida: " + e.message;
    }

    const itemsDespues = await rootFolder.getItems();
    const cantidadDespues = itemsDespues.length;
    const proyectoSinCambios = cantidadDespues === cantidadAntes;

    const ok = lanzo && !!mensaje && proyectoSinCambios;
    return {
      ok: ok,
      detalle:
        "lanzo excepcion=" + lanzo + " | mensaje=" + mensaje +
        " | items en la raiz antes=" + cantidadAntes + ", despues=" + cantidadDespues +
        " | proyecto sin cambios=" + proyectoSinCambios,
    };
  }
);

// Caso feo 2: disco desconectado -- manifest con rutas que no existen en
// ningun disco montado. revisarMaterialDisponible debe marcar todo como
// faltante.
registrarPrueba(
  "Task 9: revisarMaterialDisponible con disco desconectado marca todos los clips como faltantes",
  async () => {
    const manifestDiscoDesconectado = {
      proyecto: "Prueba disco desconectado",
      clips: [
        { ruta: "/Volumes/DiscoQueNoExiste/clip1.MP4" },
        { ruta: "/Volumes/DiscoQueNoExiste/clip2.MP4" },
      ],
    };

    const resultado = await revisarMaterialDisponible(manifestDiscoDesconectado);

    const ok =
      resultado.disponibles === 0 &&
      resultado.faltantes.length === 2 &&
      resultado.faltantes.length === manifestDiscoDesconectado.clips.length;

    return {
      ok: ok,
      detalle:
        "disponibles=" + resultado.disponibles + " (esperado 0)" +
        " | faltantes=" + JSON.stringify(resultado.faltantes) +
        " | total de clips en el manifest=" + manifestDiscoDesconectado.clips.length,
    };
  }
);

// Caso feo 3: manifest sin clips ("clips": []). La misma condicion que usa
// importarManifestDesdeArchivo() debe detectarlo como invalido.
registrarPrueba(
  "Task 9: la validacion de clips detecta un manifest con clips: [] como invalido",
  async () => {
    const manifestSinClips = { proyecto: "Sin clips", clips: [] };
    const manifestSinPropiedadClips = { proyecto: "Sin propiedad clips" };
    const manifestClipsNoEsArray = { proyecto: "Clips no es arreglo", clips: "no soy un arreglo" };

    const esInvalido = (manifest) =>
      !manifest.clips || !Array.isArray(manifest.clips) || manifest.clips.length === 0;

    const ok =
      esInvalido(manifestSinClips) &&
      esInvalido(manifestSinPropiedadClips) &&
      esInvalido(manifestClipsNoEsArray);

    return {
      ok: ok,
      detalle:
        "clips: []=" + esInvalido(manifestSinClips) +
        " | sin propiedad clips=" + esInvalido(manifestSinPropiedadClips) +
        " | clips no es arreglo=" + esInvalido(manifestClipsNoEsArray),
    };
  }
);

async function findClipsConRuta(folder, filePath) {
  const premierepro = require("premierepro");
  const items = await folder.getItems();
  const encontrados = [];
  for (const item of items) {
    const clipItem = premierepro.ClipProjectItem.cast(item);
    if (clipItem) {
      try {
        const mediaPath = await clipItem.getMediaFilePath();
        if (mediaPath === filePath) encontrados.push(clipItem);
      } catch (e) {
        // no es un clip con archivo de medios; ignorar.
      }
    }
  }
  return encontrados;
}

// Variante recursiva de findClipsConRuta: baja por TODO el arbol de bins (no
// solo un nivel) y junta TODAS las coincidencias, no solo la primera (a
// diferencia de findClipByPath en js/importClip.js, que se detiene en la
// primera). Se usa en Task 11 para la prueba "no hay duplicados en ningun
// lado del arbol" tras una reexportacion -- una pregunta que ni
// findClipsConRuta (un solo nivel) ni findClipByPath (se detiene temprano)
// pueden responder por si solas.
async function findClipsConRutaEnArbol(folder, filePath) {
  const premierepro = require("premierepro");
  const items = await folder.getItems();
  let encontrados = [];
  for (const item of items) {
    const clipItem = premierepro.ClipProjectItem.cast(item);
    if (clipItem) {
      try {
        const mediaPath = await clipItem.getMediaFilePath();
        if (mediaPath === filePath) encontrados.push(clipItem);
      } catch (e) {
        // no es un clip con archivo de medios; ignorar.
      }
      continue;
    }
    const subFolder = premierepro.FolderItem.cast(item);
    if (subFolder) {
      const anidados = await findClipsConRutaEnArbol(subFolder, filePath);
      encontrados = encontrados.concat(anidados);
    }
  }
  return encontrados;
}

// ---------------------------------------------------------------------------
// Task 11: prueba de punta a punta con material real.
//
// Todo lo anterior (Tasks 1-9) se verifico pieza por pieza sobre manifests de
// un solo caso. Esta prueba junta los cinco casos que importan en un mismo
// manifest, tal como pasaria en un dia de trabajo real:
//   1. Dos bins homonimos ("Bano") en ramas distintas del arbol.
//   2. Un clip sin clasificar (categoria_path: []).
//   3. Un clip sin proxy.
//   4. Un clip con proxy.
//   5. Dos archivos DISTINTOS en disco que comparten el mismo nombre de
//      archivo (misma tarjeta de memoria reusada en otra sesion).
//
// La rotacion se difiere a Task 13 -- la API de premierepro no la expone
// (ver nota en el plan).
// OJO: esta carpeta NO existe en el repo. La prueba simula dos tarjetas
// distintas con un archivo del mismo nombre, y para correrla hay que crear
// `sample-media/clips/tarjeta2/` y copiar ahi el 0587. Se deja escrito aqui
// porque antes fallaba con «archivo no encontrado» sin decir que faltaba
// prepararla.
const RUTA_TARJETA2_587 = RUTA_TEST_DIR + "/tarjeta2/20260804_PIB0587.MP4";

const manifestE2E = {
  proyecto: "Prueba E2E",
  orientacion: "vertical",
  clips: [
    {
      orden: 1,
      ruta: CLIP_587,
      categoria_path: ["PruebaTask11_Recamara1", "Bano"],
      fps: FPS_CLIP_588,
      in_frame: 10,
      out_frame: 90,
      flag: "pick",
      ruta_proxy: PROXY_587,
    },
    {
      orden: 2,
      ruta: RUTA_TARJETA2_587,
      categoria_path: ["PruebaTask11_Recamara2", "Bano"],
      fps: FPS_CLIP_588,
      in_frame: null,
      out_frame: null,
      flag: "reject",
      ruta_proxy: null,
    },
    {
      orden: 3,
      ruta: CLIP_589,
      categoria_path: [],
      fps: FPS_CLIP_588,
      in_frame: 30,
      out_frame: 200,
      flag: "none",
      ruta_proxy: null,
    },
  ],
};

registrarPrueba(
  "Task 11 (E2E): bins homonimos por identidad, nombres repetidos por ruta, sin clasificar, colores, in/out y proxy",
  async (project) => {
    const premierepro = require("premierepro");
    const rootItem = await project.getRootItem();
    const rootFolder = premierepro.FolderItem.cast(rootItem);

    // Linea base: importar el clip de "tarjeta2" (mismo nombre de archivo
    // que CLIP_587, ruta distinta) en un bin de paso, ANTES de correr
    // processManifest, para capturar como quedan in/out en un import fresco
    // sin ninguna llamada a applyInOut. processManifest, al encontrar esta
    // misma ruta ya importada en otro bin, la movera (no la reimportara) --
    // exactamente el mismo camino de codigo que un clip real "reject" sin
    // marcas. Esto nos deja un "antes" real contra el cual comparar el
    // "despues", en vez de adivinar cual es el valor por defecto de la API.
    const baselineFolder = await resolveBinChain(project, rootFolder, ["PruebaTask11_Baseline"]);
    const baselineClip = await importOrReuseClip(project, baselineFolder, RUTA_TARJETA2_587);
    const baselineClipItem = premierepro.ClipProjectItem.cast(baselineClip);
    const inBaseline = await baselineClipItem.getInPoint(premierepro.Constants.MediaType.ANY);
    const outBaseline = await baselineClipItem.getOutPoint(premierepro.Constants.MediaType.ANY);

    const resultado = await processManifest(project, manifestE2E);

    // --- Punto 6: 3 importados, 0 con error. ---
    const okEsperado = ["20260804_PIB0587.MP4", "20260804_PIB0587.MP4", "20260804_PIB0589.MP4"];
    const okCoincide =
      resultado.ok.length === okEsperado.length &&
      resultado.ok.every((nombre, i) => nombre === okEsperado[i]);
    const sinErrores = resultado.errores.length === 0;

    // --- Punto 1: Recamara1>Bano y Recamara2>Bano, cada uno con SU clip. ---
    const banoR1 = await resolveBinChain(project, rootFolder, ["PruebaTask11_Recamara1", "Bano"]);
    const banoR2 = await resolveBinChain(project, rootFolder, ["PruebaTask11_Recamara2", "Bano"]);

    const clip587EnBanoR1 = await findClipsConRuta(banoR1, CLIP_587);
    const tarjeta2EnBanoR1 = await findClipsConRuta(banoR1, RUTA_TARJETA2_587);
    const clip587EnBanoR2 = await findClipsConRuta(banoR2, CLIP_587);
    const tarjeta2EnBanoR2 = await findClipsConRuta(banoR2, RUTA_TARJETA2_587);

    const binsPorIdentidadCorrecto =
      clip587EnBanoR1.length === 1 && tarjeta2EnBanoR1.length === 0 &&
      clip587EnBanoR2.length === 0 && tarjeta2EnBanoR2.length === 1;

    // --- Punto 2: dos archivos con el mismo nombre entraron como dos clips
    // distintos, cada uno con su propio getMediaFilePath(). ---
    let identidadPorRutaCorrecta = false;
    let clip1 = null;
    let clip2 = null;
    if (binsPorIdentidadCorrecto) {
      clip1 = clip587EnBanoR1[0];
      clip2 = tarjeta2EnBanoR2[0];
      const ruta1 = await premierepro.ClipProjectItem.cast(clip1).getMediaFilePath();
      const ruta2 = await premierepro.ClipProjectItem.cast(clip2).getMediaFilePath();
      identidadPorRutaCorrecta = ruta1 === CLIP_587 && ruta2 === RUTA_TARJETA2_587 && ruta1 !== ruta2;
    }

    // --- Punto 3: el tercer clip (categoria_path: []) cayo en "Sin
    // clasificar" (nombre real usado por processManifest.js, no el del
    // texto del plan de memoria). ---
    const sinClasificarFolder = await resolveBinChain(project, rootFolder, ["Sin clasificar"]);
    const clip589EnSinClasificar = await findClipsConRuta(sinClasificarFolder, CLIP_589);
    const sinClasificarCorrecto = clip589EnSinClasificar.length === 1;

    // --- Punto 4: primer clip -- FOREST, proxy correcto, in/out 10/90. ---
    let clip1Correcto = false;
    if (identidadPorRutaCorrecta) {
      const c1 = premierepro.ClipProjectItem.cast(clip1);
      const indice1 = await c1.getColorLabelIndex();
      const esForest = indice1 === premierepro.Constants.ProjectItemColorLabel.FOREST;

      const tieneProxy1 = await c1.hasProxy();
      const rutaProxy1 = await c1.getProxyPath();
      const proxyOk = tieneProxy1 === true && rutaProxy1 === PROXY_587;

      const frameRate = premierepro.FrameRate.createWithValue(FPS_CLIP_588);
      const inEsperado = premierepro.TickTime.createWithFrameAndFrameRate(10, frameRate);
      const outEsperado = premierepro.TickTime.createWithFrameAndFrameRate(90, frameRate);
      const in1 = await c1.getInPoint(premierepro.Constants.MediaType.ANY);
      const out1 = await c1.getOutPoint(premierepro.Constants.MediaType.ANY);
      const inOutOk = in1.equals(inEsperado) && out1.equals(outEsperado);

      clip1Correcto = esForest && proxyOk && inOutOk;
    }

    // --- Punto 5: segundo clip -- ROSE, sin proxy, sin marcas de in/out
    // (el in/out se quedo igual al import fresco de la linea base). ---
    let clip2Correcto = false;
    if (identidadPorRutaCorrecta) {
      const c2 = premierepro.ClipProjectItem.cast(clip2);
      const indice2 = await c2.getColorLabelIndex();
      const esRose = indice2 === premierepro.Constants.ProjectItemColorLabel.ROSE;

      const tieneProxy2 = await c2.hasProxy();
      const sinProxyOk = tieneProxy2 === false;

      const in2 = await c2.getInPoint(premierepro.Constants.MediaType.ANY);
      const out2 = await c2.getOutPoint(premierepro.Constants.MediaType.ANY);
      const inOutSinTocarOk = in2.equals(inBaseline) && out2.equals(outBaseline);

      clip2Correcto = esRose && sinProxyOk && inOutSinTocarOk;
    }

    const ok =
      okCoincide && sinErrores && binsPorIdentidadCorrecto && identidadPorRutaCorrecta &&
      sinClasificarCorrecto && clip1Correcto && clip2Correcto;

    return {
      ok: ok,
      detalle:
        "[6] resultado.ok=" + JSON.stringify(resultado.ok) + " (esperado " + JSON.stringify(okEsperado) + ")" +
        ", errores=" + JSON.stringify(resultado.errores) +
        " | [1] bins homonimos por identidad (Recamara1>Bano y Recamara2>Bano, cada uno con su clip)=" + binsPorIdentidadCorrecto +
        " | [2] identidad por ruta de los dos '20260804_PIB0587.MP4'=" + identidadPorRutaCorrecta +
        " | [3] tercer clip en 'Sin clasificar'=" + sinClasificarCorrecto +
        " | [4] primer clip (FOREST, proxy, in/out 10/90)=" + clip1Correcto +
        " | [5] segundo clip (ROSE, sin proxy, sin marcas de in/out)=" + clip2Correcto,
    };
  }
);

registrarPrueba(
  "Task 11 (E2E - reexportacion): mover el primer clip a otra categoria lo muda sin duplicar y conserva proxy/color/in-out",
  async (project) => {
    const premierepro = require("premierepro");
    const rootItem = await project.getRootItem();
    const rootFolder = premierepro.FolderItem.cast(rootItem);

    // Edita el manifest en memoria: el primer clip se reclasifica, tal cual
    // pasa cuando alguien corrige el checklist despues de haber importado ya
    // una vez. Todo lo demas (proxy, in/out, flag) se queda igual -- es la
    // misma correccion de todos los dias, no una reimportacion desde cero.
    const manifestReexportado = {
      proyecto: manifestE2E.proyecto,
      orientacion: manifestE2E.orientacion,
      clips: manifestE2E.clips.map((c) => Object.assign({}, c)),
    };
    manifestReexportado.clips[0].categoria_path = ["PruebaTask11_Cocina"];

    const resultado = await processManifest(project, manifestReexportado);
    const sinErrores = resultado.errores.length === 0;

    // El clip se mudo a Cocina.
    const cocinaFolder = await resolveBinChain(project, rootFolder, ["PruebaTask11_Cocina"]);
    const enCocina = await findClipsConRuta(cocinaFolder, CLIP_587);
    const seMudoACocina = enCocina.length === 1;

    // Recamara1>Bano quedo vacio de este clip.
    const banoR1 = await resolveBinChain(project, rootFolder, ["PruebaTask11_Recamara1", "Bano"]);
    const banoR1QuedoVacio = (await findClipsConRuta(banoR1, CLIP_587)).length === 0;

    // No hay duplicados de este clip en NINGUNA parte del arbol (busqueda
    // recursiva desde la raiz, no solo en los bins que tocamos nosotros).
    const todasLasCoincidencias = await findClipsConRutaEnArbol(rootFolder, CLIP_587);
    const sinDuplicados = todasLasCoincidencias.length === 1;

    // El clip mudado conserva proxy, color y marcas de in/out.
    let conservaTodo = false;
    if (seMudoACocina) {
      const c1 = premierepro.ClipProjectItem.cast(enCocina[0]);

      const tieneProxy = await c1.hasProxy();
      const rutaProxy = await c1.getProxyPath();
      const proxyOk = tieneProxy === true && rutaProxy === PROXY_587;

      const indice = await c1.getColorLabelIndex();
      const colorOk = indice === premierepro.Constants.ProjectItemColorLabel.FOREST;

      const frameRate = premierepro.FrameRate.createWithValue(FPS_CLIP_588);
      const inEsperado = premierepro.TickTime.createWithFrameAndFrameRate(10, frameRate);
      const outEsperado = premierepro.TickTime.createWithFrameAndFrameRate(90, frameRate);
      const inReal = await c1.getInPoint(premierepro.Constants.MediaType.ANY);
      const outReal = await c1.getOutPoint(premierepro.Constants.MediaType.ANY);
      const inOutOk = inReal.equals(inEsperado) && outReal.equals(outEsperado);

      conservaTodo = proxyOk && colorOk && inOutOk;
    }

    const ok = sinErrores && seMudoACocina && banoR1QuedoVacio && sinDuplicados && conservaTodo;

    return {
      ok: ok,
      detalle:
        "sin errores=" + sinErrores +
        " | se mudo a PruebaTask11_Cocina=" + seMudoACocina +
        " | PruebaTask11_Recamara1>Bano quedo vacio=" + banoR1QuedoVacio +
        " | coincidencias de " + CLIP_587 + " en todo el arbol=" + todasLasCoincidencias.length + " (esperado 1)" +
        " | conserva proxy/color/in-out tras la mudanza=" + conservaTodo,
    };
  }
);
