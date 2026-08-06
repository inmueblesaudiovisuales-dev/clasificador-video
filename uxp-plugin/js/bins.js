// Dado ["Recamara 2", "Bano"], crea (o reusa) el bin "Recamara 2" dentro de
// parentFolder, y dentro de ese "Bano". Devuelve el FolderItem final.
async function resolveBinChain(project, rootFolder, categoryPath) {
  const premierepro = require("premierepro");
  let currentFolder = rootFolder;

  for (const name of categoryPath) {
    const items = await currentFolder.getItems();
    let found = items.find((i) => i.name === name);

    if (!found) {
      runTransaction(project, () => currentFolder.createBinAction(name, true), "Crear bin " + name);
      const afterItems = await currentFolder.getItems();
      found = afterItems.find((i) => i.name === name);
    }

    currentFolder = premierepro.FolderItem.cast(found);
  }

  return currentFolder;
}
