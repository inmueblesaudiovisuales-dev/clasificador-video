// Donde vive cada segmento dentro de `camino` (que ya trae CARPETA_DE_CLIPS
// al frente, ver caminoDelClip): sin unidad, camino = [CARPETA_DE_CLIPS,
// cuarto, ...resto]; con unidad, camino = [CARPETA_DE_CLIPS, unidad,
// cuarto, ...resto]. Logica pura, se prueba sin Premiere.
function indicesDelCamino(categoryPath) {
  const hayUnidad = (categoryPath || []).length > 1;
  return {
    indiceUnidad: hayUnidad ? 1 : null,
    indiceCuarto: hayUnidad ? 2 : 1,
  };
}

// Procesa un manifest ya parseado (objeto JS, ver formato en el spec).
// Devuelve { ok: [nombresDeArchivo], errores: [{archivo, mensaje}] }.
async function processManifest(project, manifest) {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const resultado = { ok: [], errores: [] };

  // Las siete carpetas primero: aunque cinco queden vacias, son el esqueleto
  // del proyecto de Bruno. Si ya existen, `resolveBinChain` las reusa.
  await crearEsqueleto(project, rootFolder);

  // Un proyecto de una importacion anterior tiene sus clips fuera de
  // «02. Clip» y se van a mover. No se duplica ninguno --`importOrReuseClip`
  // los encuentra por ruta en disco-- pero moverse se mueven, y se avisa
  // ANTES de tocar nada.
  const carpetaDeClips = await resolveBinChain(project, rootFolder, [CARPETA_DE_CLIPS]);
  const porMover = await contarLosQueSeVanAMover(rootFolder, manifest, carpetaDeClips);

  // Una sola pasada por el proyecto para saber que clips ya estan
  // importados -- ver `indexarClipsPorRuta` en importClip.js. Sin esto,
  // `importOrReuseClip` recorria el proyecto entero POR CADA CLIP del
  // manifiesto para ver si ya existia, y eso era lo que hacia lenta la
  // importacion completa con un rodaje grande.
  const indiceDeClips = await indexarClipsPorRuta(rootFolder);
  if (porMover > 0) {
    logToPanel(
      porMover + " clip(s) que ya estaban en el proyecto se van a mover a «" +
      CARPETA_DE_CLIPS + "». No se duplica ninguno."
    );
  }

  // La guia en el orden que Bruno acepto en Clipify, o vacia si este
  // proyecto no trae guia. Un manifest sin guia crea las carpetas sin
  // numero, igual que siempre. Con unidades, `guia.unidades` trae el orden
  // de cada una y el de sus cuartos (spec 2026-09-21).
  const guia = manifest.guia || {};

  // El numero secuencial de cada clip DENTRO de su cuarto, en el orden del
  // manifiesto. Se calcula una sola vez para toda la corrida -- ver
  // `numerosDeClip` en `nombre.js`.
  const numerosDeLosClips = numerosDeClip(manifest.clips);

  // El aviso de «no pude renombrar» se da una vez por importacion, no una
  // por clip. Ver `nombre.js`.
  reiniciarAvisoDeRenombrar();

  for (let indice = 0; indice < manifest.clips.length; indice++) {
    const clipData = manifest.clips[indice];
    let nombreArchivo = "(sin ruta)";
    // Se declara AFUERA del try para que el mensaje de error pueda decir a
    // donde iba el clip. Sin eso, un fallo solo decia el nombre del archivo
    // y habia que ir a buscar al .cvproj en que cuarto estaba -- que es
    // justo lo que Bruno tuvo que preguntar.
    let categoryPath = ["Sin clasificar"];
    try {
      nombreArchivo = (clipData.ruta || "").split("/").pop() || nombreArchivo;

      if (clipData.categoria_path && clipData.categoria_path.length > 0) {
        categoryPath = clipData.categoria_path;
      }

      // El CAMINO numera la unidad y el cuarto con la guia (spec 2026-09-21);
      // su indice cambia si hay unidad o no -- `indicesDelCamino` lo dice.
      // Pasa por `resolverCuarto` --que renumera la carpeta que ya existe en
      // vez de crear una segunda--. Lo que cuelgue debajo sigue por el camino
      // de siempre.
      const camino = caminoDelClip(categoryPath, guia);
      const { indiceUnidad, indiceCuarto } = indicesDelCamino(categoryPath);
      // camino[indiceCuarto] ya trae el numero (o no, sin guia). Aqui se le
      // suma la marca [DRONE]/[SONY]/etc si TODOS los clips de este cuarto,
      // en ESTE manifiesto, vinieron de esa camara -- ver marcaCamara.js y
      // spec 2026-09-18.
      const nombreCuartoSinNumero = categoryPath[categoryPath.length - 1];
      camino[indiceCuarto] = nombreDelCuartoConMarca(
        camino[indiceCuarto], nombreCuartoSinNumero, manifest.clips, categoryPath
      );

      // La UNIDAD, cuando hay una, lleva su numero (spec 2026-09-21) y su
      // marca de camara. Va por `resolverCuarto` igual que el cuarto: si ya
      // existia sin numero --de una importacion anterior-- la RENUMERA en vez
      // de crear una segunda carpeta.
      let carpetaBase = carpetaDeClips;
      if (indiceUnidad !== null) {
        const nombreUnidad = nombreDelCuartoConMarca(
          camino[indiceUnidad], camino[indiceUnidad], manifest.clips, [categoryPath[0]]
        );
        carpetaBase = await resolverCuarto(project, carpetaDeClips, nombreUnidad);
      }
      const carpetaDelCuartoObj = await resolverCuarto(
        project, carpetaBase, camino[indiceCuarto]);
      const targetFolder = camino.length > indiceCuarto + 1
        ? await resolveBinChain(project, carpetaDelCuartoObj, camino.slice(indiceCuarto + 1))
        : carpetaDelCuartoObj;
      const clipItem = await importOrReuseClip(project, targetFolder, clipData.ruta, indiceDeClips);

      if (!clipItem) {
        throw new Error("No se pudo importar ni encontrar el clip");
      }

      applyCameraLabel(project, clipItem, clipData.camara);
      // El nombre del clip: [símbolo ]Cuarto NN [CAMARA]. El cuarto es el
      // último segmento de categoria_path y la marca de cámara sale de la
      // MISMA fuente que la de la carpeta (`marcaCamara.js`), para que las
      // dos no digan cosas distintas. Ver `nombre.js` y spec 2026-09-21.
      aplicarNombreDeClip(
        project, clipItem, nombreCuartoSinNumero, numerosDeLosClips[indice],
        marcaDeCamaraDelPrefijo(manifest.clips, categoryPath), clipData.flag
      );

      if (clipData.in_frame !== null && clipData.out_frame !== null) {
        applyInOut(project, clipItem, clipData.fps, clipData.in_frame, clipData.out_frame);
      }

      if (clipData.ruta_proxy) {
        await attachProxyIfPresent(clipItem, clipData.ruta_proxy);
      }

      resultado.ok.push(nombreArchivo);
      logToPanel("OK: " + nombreArchivo + " -> " + camino.join(" > "));
    } catch (e) {
      // e no siempre es un Error real (ej. la API nativa de Premiere puede
      // rechazar con un string u otro valor sin .message) -- con fallback a
      // String(e) el mensaje nunca queda vacio ni tumba este catch.
      const mensaje = (e && e.message) || String(e);
      const donde = caminoDelClip(categoryPath, guia).join(" > ");
      resultado.errores.push({
        archivo: nombreArchivo, mensaje: mensaje, destino: donde,
      });
      // el destino va en el mensaje: si un clip falla, lo primero que uno
      // necesita es saber a que bin arrastrarlo a mano
      logToPanel(nombreArchivo + " (iba a " + donde + "): " + mensaje, true);
    }
  }

  try {
    resultado.secuencia = await construirSecuencia(project, manifest);
    for (const secuencia of resultado.secuencia.secuencias || []) {
      if (secuencia.estado === "error") {
        resultado.errores.push({ archivo: secuencia.nombre, mensaje: secuencia.mensaje });
      }
    }
  } catch (e) {
    const mensaje = (e && e.message) || String(e);
    resultado.errores.push({ archivo: "Secuencia", mensaje: mensaje });
    logToPanel("No se pudo crear la secuencia vacía: " + mensaje, true);
  }

  return resultado;
}

// Revisa ANTES de empezar que el material exista en disco. El caso real: el
// usuario clasifica con el disco externo conectado y luego abre Premiere sin
// el disco. Sin esto, saldrian 40 errores en vez de un aviso claro.
// Devuelve { disponibles, faltantes: [rutas] }.
async function revisarMaterialDisponible(manifest) {
  const uxpFs = require("uxp").storage.localFileSystem;
  const faltantes = [];

  for (const clipData of manifest.clips) {
    try {
      await uxpFs.getEntryWithUrl("file://" + clipData.ruta);
    } catch (e) {
      faltantes.push(clipData.ruta);
    }
  }

  return { disponibles: manifest.clips.length - faltantes.length, faltantes };
}
