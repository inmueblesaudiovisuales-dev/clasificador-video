// Procesa un manifest ya parseado (objeto JS, ver formato en el spec).
// Devuelve { ok: [nombresDeArchivo], errores: [{archivo, mensaje}] }.
async function processManifest(project, manifest) {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const resultado = { ok: [], errores: [] };

  for (const clipData of manifest.clips) {
    const nombreArchivo = clipData.ruta.split("/").pop();
    try {
      const categoryPath = clipData.categoria_path && clipData.categoria_path.length > 0
        ? clipData.categoria_path
        : ["Sin clasificar"];

      const targetFolder = await resolveBinChain(project, rootFolder, categoryPath);
      const clipItem = await importOrReuseClip(project, targetFolder, clipData.ruta);

      if (!clipItem) {
        throw new Error("No se pudo importar ni encontrar el clip");
      }

      applyFlagLabel(project, clipItem, clipData.flag);

      if (clipData.in_frame !== null && clipData.out_frame !== null) {
        const clipProjectItem = premierepro.ClipProjectItem.cast(clipItem);
        const media = await clipProjectItem.getMedia();
        const fps = media ? await getFpsFromMedia(media) : 30;
        applyInOut(project, clipItem, fps, clipData.in_frame, clipData.out_frame);
      }

      if (clipData.ruta_proxy) {
        await attachProxyIfPresent(clipItem, clipData.ruta_proxy);
      }

      resultado.ok.push(nombreArchivo);
      logToPanel("OK: " + nombreArchivo + " -> " + categoryPath.join(" > "));
    } catch (e) {
      resultado.errores.push({ archivo: nombreArchivo, mensaje: e.message });
      logToPanel(nombreArchivo + ": " + e.message, true);
    }
  }

  return resultado;
}

// Placeholder de fps: se reemplaza en un task posterior por el fps real que ya
// viene en el manifest, en vez de leerlo de Media.
async function getFpsFromMedia(media) {
  return 30;
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
