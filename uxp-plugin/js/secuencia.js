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

function datosDeSecuencias(manifest) {
  if (manifest && manifest.crear_secuencias === true) {
    const nombre = ((manifest.proyecto || "Proyecto").trim() || "Proyecto");
    // Las tres resoluciones nativas van juntas en su bin; las 1080p en el
    // suyo. Mismo arreglo que arma el generador directo del .prproj.
    return [
      { nombre: nombre + " 4K 9:16", ancho: 2160, alto: 3840, fps: 59.94, carpeta: "Resolucion original" },
      { nombre: nombre + " 2.7K 9:16", ancho: 2160, alto: 3840, fps: 59.94, carpeta: "Resolucion original" },
      { nombre: nombre + " 4K 16:9", ancho: 3840, alto: 2160, fps: 59.94, carpeta: "Resolucion original" },
      { nombre: nombre + " 9:16 1080p", ancho: 1080, alto: 1920, fps: 59.94, carpeta: "1080p" },
      { nombre: nombre + " 16:9 1080p", ancho: 1920, alto: 1080, fps: 59.94, carpeta: "1080p" },
    ];
  }
  // Los JSON de la versión anterior siguen pidiendo solo el par elegido.
  const principal = datosDeSecuencia(manifest);
  if (!principal) return [];
  const vertical = principal.sufijo === "9:16";
  return [principal, {
    nombre: principal.nombre + " 1080p",
    ancho: vertical ? 1080 : 1920,
    alto: vertical ? 1920 : 1080,
    fps: principal.fps,
  }];
}

async function secuenciaConNombre(folder, nombre) {
  for (const item of (await folder.getItems()) || []) {
    if (item && item.name === nombre) return item;
  }
  return null;
}

async function construirSecuencia(project, manifest) {
  const secuencias = datosDeSecuencias(manifest);
  if (!secuencias.length) return { estado: "sin-formato" };
  const premierepro = require("premierepro");
  const root = premierepro.FolderItem.cast(await project.getRootItem());
  const carpetaPrincipal = await resolveBinChain(project, root, [CARPETAS_DEL_PROYECTO[0]]);
  const resultados = [];
  for (const datos of secuencias) {
    try {
      let carpeta = carpetaPrincipal;
      if (datos.carpeta) {
        // Un proyecto anterior puede tener esta 1080p en la raíz. No la
        // movemos ni creamos una segunda con el mismo nombre en el subbin.
        if (await secuenciaConNombre(carpetaPrincipal, datos.nombre)) {
          logToPanel("La secuencia «" + datos.nombre + "» ya existe; no se movió ni se duplicó.");
          resultados.push({ estado: "existente", nombre: datos.nombre });
          continue;
        }
        carpeta = await resolveBinChain(project, carpetaPrincipal, [datos.carpeta]);
      }
      resultados.push(await construirUnaSecuencia(project, root, carpeta, premierepro, datos));
    } catch (e) {
      const mensaje = (e && e.message) || String(e);
      logToPanel("No se pudo crear la secuencia vacía «" + datos.nombre + "»: " + mensaje, true);
      resultados.push({ estado: "error", nombre: datos.nombre, mensaje: mensaje });
    }
  }
  return { estado: "procesadas", secuencias: resultados };
}

async function construirUnaSecuencia(project, root, carpeta, premierepro, datos) {
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
