// Flujo completo del boton: elegir archivo -> validar -> revisar material ->
// procesar -> reportar. Cada caso feo tiene su mensaje propio; ninguno debe
// dejar el panel en un estado ambiguo.
async function importarManifestDesdeArchivo() {
  const premierepro = require("premierepro");
  const uxpFs = require("uxp").storage.localFileSystem;
  const status = document.getElementById("status");

  const project = await premierepro.Project.getActiveProject();
  if (!project) {
    logToPanel("No hay ningun proyecto abierto en Premiere. Abre uno y vuelve a intentar.", true);
    return;
  }

  const archivo = await uxpFs.getFileForOpening({ types: ["json"] });
  if (!archivo) {
    logToPanel("Cancelado, no se eligio ningun archivo.");
    return;
  }

  let manifest;
  try {
    manifest = JSON.parse(await archivo.read());
  } catch (e) {
    logToPanel("El archivo elegido no es una clasificacion valida: " + e.message, true);
    return;
  }

  if (!manifest.clips || !Array.isArray(manifest.clips) || manifest.clips.length === 0) {
    logToPanel("El archivo elegido no trae clips.", true);
    return;
  }

  // Disco desconectado: un aviso claro en vez de un error por cada clip.
  const material = await revisarMaterialDisponible(manifest);
  if (material.faltantes.length === manifest.clips.length) {
    logToPanel(
      "No se encontro NINGUNO de los " + manifest.clips.length +
        " archivos de video. Revisa que el disco con el material este conectado.",
      true
    );
    return;
  }
  if (material.faltantes.length > 0) {
    logToPanel(
      "Faltan " + material.faltantes.length + " de " + manifest.clips.length +
        " archivos; se importara el resto. Primero que falta: " + material.faltantes[0],
      true
    );
  }

  status.textContent = "Importando " + archivo.name + "...";
  const resultado = await processManifest(project, manifest);
  status.textContent = "Listo.";

  logToPanel(
    "--- " + archivo.name + ": " + resultado.ok.length + " importados, " +
      resultado.errores.length + " con error ---"
  );
}
