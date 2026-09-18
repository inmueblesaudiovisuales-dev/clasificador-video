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
  if (porMover > 0) {
    logToPanel(
      porMover + " clip(s) que ya estaban en el proyecto se van a mover a «" +
      CARPETA_DE_CLIPS + "». No se duplica ninguno."
    );
  }

  // Los cuartos en el orden que Bruno acepto en Clipify, o vacio si este
  // proyecto no trae guia. Un manifest sin guia crea las carpetas sin
  // numero, igual que siempre.
  const ordenDeLaGuia = ((manifest.guia && manifest.guia.orden) || []).map(
    (r) => r.cuarto
  );

  // El aviso de «no pude renombrar» se da una vez por importacion, no una
  // por clip. Ver `nombre.js`.
  reiniciarAvisoDeRenombrar();

  for (const clipData of manifest.clips) {
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

      // El PRIMER segmento es el cuarto y es el unico que lleva numero,
      // asi que pasa por `resolverCuarto` --que renumera la carpeta que ya
      // existe en vez de crear una segunda--. Lo que cuelgue debajo sigue
      // por el camino de siempre.
      const camino = caminoDelClip(categoryPath, ordenDeLaGuia);
      // camino[1] ya trae el numero (o no, sin guia). Aqui se le suma la
      // marca [DRONE] si TODOS los clips de este cuarto, en ESTE
      // manifiesto, vinieron de un bin que dice "dron" -- ver
      // marcaDron.js y spec 2026-09-18.
      camino[1] = nombreDelCuartoConMarca(camino[1], categoryPath[0], manifest.clips);
      const carpetaDelCuarto = await resolverCuarto(
        project, carpetaDeClips, camino[1]);
      const targetFolder = camino.length > 2
        ? await resolveBinChain(project, carpetaDelCuarto, camino.slice(2))
        : carpetaDelCuarto;
      const clipItem = await importOrReuseClip(project, targetFolder, clipData.ruta);

      if (!clipItem) {
        throw new Error("No se pudo importar ni encontrar el clip");
      }

      applyCameraLabel(project, clipItem, clipData.camara);
      applyFlagPrefix(project, clipItem, clipData.flag);

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
      const donde = caminoDelClip(categoryPath, ordenDeLaGuia).join(" > ");
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
