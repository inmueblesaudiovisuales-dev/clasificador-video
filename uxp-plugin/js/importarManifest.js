// La guia que trajo el ultimo manifest importado, o null. La pestana la LEE
// y nunca la pide: se armo en Clipify y viaja congelada.
let guiaDelManifest = null;

// De que rodaje es la guia que se esta enseñando. Sin esto, abrir Premiere
// tres semanas despues no dice si la guia es la del proyecto que tienes
// enfrente.
let proyectoDelManifest = "";

function guardarGuia(manifest) {
  guiaDelManifest = (manifest && manifest.guia) || null;
  proyectoDelManifest = (manifest && manifest.proyecto) || "";
}

function guiaImportada() {
  return guiaDelManifest;
}

function proyectoImportado() {
  return proyectoDelManifest;
}

// Flujo completo del boton: elegir archivo -> validar -> revisar material ->
// procesar -> reportar. Cada caso feo tiene su mensaje propio; ninguno debe
// dejar el panel en un estado ambiguo.
async function importarManifestDesdeArchivo() {
  const premierepro = require("premierepro");
  const uxpFs = require("uxp").storage.localFileSystem;
  const status = document.getElementById("status");

  const project = await premierepro.Project.getActiveProject();
  if (!project) {
    logToPanel("No hay ningún proyecto abierto en Premiere. Abre uno y vuelve a intentar.", true);
    return;
  }

  const archivo = await uxpFs.getFileForOpening({ types: ["json"] });
  if (!archivo) {
    logToPanel("Cancelado, no se eligió ningún archivo.");
    return;
  }

  let manifest;
  try {
    manifest = JSON.parse(await archivo.read());
  } catch (e) {
    logToPanel("El archivo elegido no es una clasificación válida: " + e.message, true);
    return;
  }

  if (!manifest.clips || !Array.isArray(manifest.clips) || manifest.clips.length === 0) {
    logToPanel("El archivo elegido no trae clips.", true);
    return;
  }

  // La guia se guarda EN CUANTO el manifest se acepta, antes de importar:
  // si algo falla a medias, la pestana ya enseña la guia de este proyecto y
  // no la del anterior.
  guardarGuia(manifest);
  repintarGuia();

  // Disco desconectado: un aviso claro en vez de un error por cada clip.
  const material = await revisarMaterialDisponible(manifest);
  if (material.faltantes.length === manifest.clips.length) {
    logToPanel(
      "No se encontró NINGUNO de los " + manifest.clips.length +
        " archivos de video. Revisa que el disco con el material esté conectado.",
      true
    );
    return;
  }
  if (material.faltantes.length > 0) {
    logToPanel(
      "Faltan " + material.faltantes.length + " de " + manifest.clips.length +
        " archivos; se importará el resto. Primero que falta: " + material.faltantes[0],
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
