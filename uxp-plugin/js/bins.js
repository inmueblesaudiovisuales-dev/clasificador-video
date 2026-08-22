// Busca un item por nombre, SALTANDOSE los huecos.
//
// `getItems()` puede devolver un elemento nulo mientras Premiere esta
// ocupado importando, y preguntarle el nombre a ese hueco tumbaba el clip
// entero: «Cannot read properties of null (reading 'name')». Le paso a Bruno
// el 2026-08-22 con UNO de sus 205 clips -- por eso fallo uno y no todos: es
// cuestion de pedir la lista en el instante equivocado.
function buscarPorNombre(items, name) {
  return (items || []).find((i) => i && i.name === name);
}

// Dado ["Recamara 2", "Bano"], crea (o reusa) el bin "Recamara 2" dentro de
// parentFolder, y dentro de ese "Bano". Devuelve el FolderItem final.
async function resolveBinChain(project, rootFolder, categoryPath) {
  const premierepro = require("premierepro");
  let currentFolder = rootFolder;

  for (const name of categoryPath) {
    let found = buscarPorNombre(await currentFolder.getItems(), name);

    if (!found) {
      runTransaction(project, () => currentFolder.createBinAction(name, true), "Crear bin " + name);
      found = buscarPorNombre(await currentFolder.getItems(), name);
    }

    if (!found) {
      throw new Error("no se pudo crear ni encontrar el bin \"" + name + "\"");
    }

    currentFolder = premierepro.FolderItem.cast(found);
  }

  return currentFolder;
}
