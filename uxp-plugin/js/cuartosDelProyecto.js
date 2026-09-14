// De donde salen los cuartos para el orden sugerido.
//
// Son las carpetas que cuelgan DIRECTO de «02. Clip». No se le preguntan a
// Bruno: si estan ahi es porque el ya los tecleo una vez en Clipify, y volver
// a pedirlos seria preguntar lo que ya se sabia.
//
// `CARPETA_DE_CLIPS` sale de `estructura.js` y no es la cadena «02. Clip»
// escrita otra vez: si algun dia se renombra alla arriba, esto sigue
// apuntando a la misma carpeta. Mismo criterio que `caminoDelClip`.

// «Sin clasificar» NO es un cuarto y no entra al recorrido: es el cajon de lo
// que Bruno no alcanzo a clasificar. Meterlo en la guia haria que el modelo
// le buscara lugar en el recorrido de una casa a algo que no es un lugar de
// la casa.
const NO_ES_CUARTO = ["Sin clasificar"];

// Devuelve los nombres de los cuartos, en el orden en que Premiere los
// entrega. Vacio cuando el proyecto no salio de Clipify --no hay «02. Clip»,
// o esta sin carpetas adentro--, que no es un error: es alguien abriendo la
// pestana en un proyecto cualquiera, y el panel lo atiende dejando teclear
// los cuartos a mano.
async function cuartosDeLosBins(project) {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  // Se busca la carpeta SIN crearla. `resolveBinChain` la crearia, y esta
  // pestana no escribe nada en el proyecto (§5 del spec) -- ni siquiera una
  // carpeta vacia.
  const carpetaDeClips = buscarPorNombre(await rootFolder.getItems(), CARPETA_DE_CLIPS);
  if (!carpetaDeClips) return [];

  const folder = premierepro.FolderItem.cast(carpetaDeClips);
  if (!folder) return [];

  const nombres = [];
  for (const item of (await folder.getItems()) || []) {
    // El hueco nulo que devuelve `getItems()` mientras Premiere esta ocupado
    // ya tumbo un clip de Bruno el 2026-08-22. Aqui se salta igual.
    if (!item) continue;
    const sub = premierepro.FolderItem.cast(item);
    if (!sub) continue;
    if (NO_ES_CUARTO.indexOf(sub.name) !== -1) continue;
    nombres.push(sub.name);
  }
  return nombres;
}

// Los cuartos tecleados a mano, uno por renglon. Se limpian los renglones
// vacios y los repetidos, que es lo que pasa al pegar una lista de otro lado.
function cuartosTecleados(texto) {
  const vistos = [];
  for (const renglon of String(texto || "").split("\n")) {
    const nombre = renglon.trim();
    if (nombre && vistos.indexOf(nombre) === -1) vistos.push(nombre);
  }
  return vistos;
}
