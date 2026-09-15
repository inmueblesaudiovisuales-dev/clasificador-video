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

// Devuelve { hayCarpeta, cuartos }: los nombres de los cuartos en el orden en
// que Premiere los entrega, y si la carpeta «02. Clip» existe siquiera.
//
// LOS DOS DATOS, Y NO SOLO LA LISTA: sin carpeta y con la carpeta vacia
// terminan las dos en una lista vacia, pero son cosas distintas y el panel
// las tiene que decir distinto. Devolver solo la lista obligaba a adivinar, y
// el 2026-09-14 adivino mal en vivo: el proyecto de Bruno SI tenia su
// «02. Clip», vacia, y el panel le dijo que no la tenia.
//
// Ninguno de los dos casos es un error: es alguien abriendo la pestana en un
// proyecto cualquiera, o antes de importar, y el panel lo atiende dejando
// teclear los cuartos a mano.
async function cuartosDeLosBins(project) {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  // Se busca la carpeta SIN crearla. `resolveBinChain` la crearia, y esta
  // pestana no escribe nada en el proyecto (§5 del spec) -- ni siquiera una
  // carpeta vacia.
  const carpetaDeClips = buscarPorNombre(await rootFolder.getItems(), CARPETA_DE_CLIPS);
  if (!carpetaDeClips) return { hayCarpeta: false, cuartos: [] };

  const folder = premierepro.FolderItem.cast(carpetaDeClips);
  if (!folder) return { hayCarpeta: false, cuartos: [] };

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
  return { hayCarpeta: true, cuartos: nombres };
}

// Lo que el panel le dice a Bruno sobre los cuartos que encontro, y si le
// tiene que pedir que los escriba. Aparte de la lectura a proposito: es texto
// puro, asi que se comprueba con `node uxp-plugin/pruebas/correr.js` y no
// depende de que alguien abra Premiere y prenda el arnes.
function mensajeDeCuartos(lectura) {
  const cuartos = (lectura && lectura.cuartos) || [];

  if (cuartos.length) {
    return {
      pedirlosAMano: false,
      texto:
        "Encontré " + cuartos.length + " cuartos en «" + CARPETA_DE_CLIPS + "»: " +
        cuartos.join(", "),
    };
  }

  // Los dos vacios, dichos distinto. El de abajo es el que estaba mal.
  if (lectura && lectura.hayCarpeta) {
    return {
      pedirlosAMano: true,
      texto:
        "La carpeta «" + CARPETA_DE_CLIPS + "» está aquí pero sin cuartos adentro, así que " +
        "no sé de dónde sacarlos. Escríbelos aquí, uno por renglón:",
    };
  }

  return {
    pedirlosAMano: true,
    texto:
      "Este proyecto no tiene la carpeta «" + CARPETA_DE_CLIPS + "», así que no sé de dónde " +
      "sacar los cuartos. Escríbelos aquí, uno por renglón:",
  };
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
