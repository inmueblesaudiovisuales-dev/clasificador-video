const FORMATOS_DE_SECUENCIA = {
  "4K 9:16": { sufijo: "9:16", ancho: 2160, alto: 3840, fps: 59.94 },
  "2.7K 9:16": { sufijo: "9:16", ancho: 2160, alto: 3840, fps: 59.94 },
  "4K 16:9": { sufijo: "16:9", ancho: 3840, alto: 2160, fps: 59.94 },
};

function datosDeSecuencia(manifest) {
  const ajustes = manifest && FORMATOS_DE_SECUENCIA[manifest.formato_secuencia];
  if (!ajustes) return null;
  return Object.assign({
    nombre: ((manifest.proyecto || "Proyecto").trim() || "Proyecto") + " " + ajustes.sufijo,
  }, ajustes);
}

async function secuenciaConNombre(folder, nombre) {
  for (const item of (await folder.getItems()) || []) {
    if (item && item.name === nombre) return item;
  }
  return null;
}

async function construirSecuencia(project, manifest) {
  const datos = datosDeSecuencia(manifest);
  if (!datos) return { estado: "sin-formato" };
  const premierepro = require("premierepro");
  const root = premierepro.FolderItem.cast(await project.getRootItem());
  const carpeta = await resolveBinChain(project, root, [CARPETAS_DEL_PROYECTO[0]]);
  if (await secuenciaConNombre(carpeta, datos.nombre)) {
    logToPanel("La secuencia «" + datos.nombre + "» ya existe; no se modificó ni se duplicó.");
    return { estado: "existente", nombre: datos.nombre };
  }
  const secuencia = await project.createSequence(datos.nombre, "");
  const ajustes = await secuencia.getSettings();
  const rect = new premierepro.RectF();
  rect.width = datos.ancho;
  rect.height = datos.alto;
  await ajustes.setVideoFrameRect(rect);
  await ajustes.setVideoFrameRate(premierepro.FrameRate.createWithValue(datos.fps));
  await ajustes.setVideoFieldType(premierepro.Constants.VideoFieldType.PROGRESSIVE);
  await ajustes.setVideoPixelAspectRatio(premierepro.Constants.PixelAspectRatio.SQUARE);
  runTransaction(project, () => secuencia.createSetSettingsAction(ajustes), "Ajustar secuencia de Clipify");
  const item = await secuencia.getProjectItem();
  runTransaction(project, () => root.createMoveItemAction(item, carpeta), "Mover secuencia de Clipify");
  logToPanel("Secuencia vacía creada: " + datos.nombre + " (" + datos.ancho + " × " + datos.alto + ", 59.94 fps).");
  return { estado: "creada", nombre: datos.nombre };
}
