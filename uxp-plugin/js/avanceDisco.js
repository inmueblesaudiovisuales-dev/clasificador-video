// El avance, guardado entre sesiones.
//
// VIVE EN LA CARPETA DEL PLUGIN, NO EN EL PROYECTO DE PREMIERE. Bruno
// levanto el 2026-09-15 la regla de que la pestaña no escriba, pero el dueño
// del dato sigue de este lado: asi no puede corromper un proyecto, y el
// color del bin es un REFLEJO que se recalcula de aqui. Un solo dueño y una
// presentacion derivada -- el mismo corte que `camara` → color.
//
// Un archivo por proyecto, por su nombre: dos rodajes abiertos el mismo dia
// no se pisan el avance.
//
// NUNCA REVIENTA. Que no haya archivo es el caso de la primera vez, y uno
// roto se trata igual: quedarse sin palomitas es una molestia, y tronar al
// abrir el panel es un panel que no abre.

const CARPETA_DE_AVANCE = "avance";

function _nombreDeArchivo(proyecto) {
  // Lo que no sea letra, numero, guion o espacio se vuelve "_": el nombre
  // del proyecto lo escribe Bruno y puede traer "/" -- que en un nombre de
  // archivo es otra carpeta.
  //
  // `\w` en JavaScript es SOLO ASCII, asi que sin `À-ſ` (que cubre las
  // vocales acentuadas y la eñe del español) "Casa Álamos" y "Casa Olamos"
  // limpiarian igual y se pisarian el avance en el mismo archivo -- dos
  // rodajes distintos perdiendo sus palomitas sin ningun aviso.
  const limpio = String(proyecto || "sin-nombre").replace(/[^\w \-À-ſ]/g, "_");
  return limpio + ".json";
}

async function _carpeta() {
  const uxpFs = require("uxp").storage.localFileSystem;
  const datos = await uxpFs.getDataFolder();
  try {
    return await datos.getEntry(CARPETA_DE_AVANCE);
  } catch (e) {
    return await datos.createFolder(CARPETA_DE_AVANCE);
  }
}

async function leerAvance(proyecto) {
  try {
    const carpeta = await _carpeta();
    const archivo = await carpeta.getEntry(_nombreDeArchivo(proyecto));
    const datos = JSON.parse(await archivo.read());
    return Array.isArray(datos) ? datos : [];
  } catch (e) {
    return [];
  }
}

async function guardarAvance(proyecto, avance) {
  try {
    const carpeta = await _carpeta();
    const archivo = await carpeta.createFile(_nombreDeArchivo(proyecto), {
      overwrite: true,
    });
    await archivo.write(JSON.stringify(avance || []));
  } catch (e) {
    // Se DICE, y no se traga: sin esto Bruno palomea toda la tarde y al
    // reabrir no queda nada, sin haber visto jamas un aviso.
    logToPanel("No pude guardar qué llevas montado: " + (e && e.message), true);
  }
}
