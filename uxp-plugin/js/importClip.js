// Si el clip (por ruta real en disco) ya existe en el proyecto, lo mueve al
// bin destino si hace falta y lo devuelve sin reimportar. Si no existe, lo
// importa dentro de ese bin.
//
// Nota de implementacion (desviacion del diseno original del plan,
// confirmada en vivo contra Premiere Pro 26.3.0): los objetos que devuelve
// FolderItem.cast()/ClipProjectItem.cast() en esta version de la API NO
// exponen getParentBin() ni ningun identificador propio (getId()) — aunque
// premierepro.d.ts los declara, en runtime no existen (confirmado con un
// registrarPrueba de diagnostico que enumero el prototipo real del objeto).
// Por eso no se puede preguntarle a un clip "¿cual es tu carpeta actual?"
// despues de encontrarlo.
//
// Solucion: en vez de eso, findClipByPath ahora recuerda la carpeta en la
// que estaba parado cuando encontro el clip, durante la MISMA busqueda
// recursiva. La comparacion de identidad de carpeta se hace por referencia
// (===) contra el FolderItem objetivo, no por nombre ni por ruta de nombres.
// Se confirmo tambien en vivo que esta comparacion por referencia es segura:
// FolderItem.cast(item) devuelve el mismo objeto (cast(a) === cast(b)) cada
// vez que se le pasa el mismo item subyacente (getItems() tambien devuelve
// items estables entre llamadas), asi que dos rutas de busqueda distintas
// que lleguen al mismo bin real terminan comparando iguales.
// `indice`, si se pasa, es el resultado de `indexarClipsPorRuta`: evita que
// esta funcion tenga que recorrer el proyecto entero para saber si el clip
// ya existe. Sin `indice` cae de vuelta a la busqueda vieja (recorrer desde
// la raiz), asi que sigue funcionando para quien la llame sin uno.
async function importOrReuseClip(project, targetFolder, filePath, indice) {
  const premierepro = require("premierepro");
  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);

  const found = indice ? indice.get(filePath) : await findClipByPath(rootFolder, filePath);
  if (found) {
    // Comparar la carpeta REAL por referencia, no por nombre: hay bins
    // homonimos en ramas distintas (Recamara 1 > Bano vs Recamara 2 > Bano).
    if (found.parentFolder !== targetFolder) {
      runTransaction(
        project,
        () => rootFolder.createMoveItemAction(found.clipItem, targetFolder),
        "Mover clip existente"
      );
      if (indice) indice.set(filePath, { clipItem: found.clipItem, parentFolder: targetFolder });
    }
    return found.clipItem;
  }

  await project.importFiles([filePath], true, targetFolder, false);

  // Premiere no siempre registra el item al instante: reintentar buscando por
  // ruta dentro del bin destino (validado en el spike de proxy).
  for (let intento = 1; intento <= 10; intento++) {
    const clip = await findClipByPath(targetFolder, filePath);
    if (clip) {
      if (indice) indice.set(filePath, { clipItem: clip.clipItem, parentFolder: targetFolder });
      return clip.clipItem;
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  return null;
}

// Todos los clips que YA estan en el proyecto, por su ruta real en disco, en
// una sola pasada por el arbol -- para que `importOrReuseClip` no tenga que
// recorrer el proyecto entero por cada clip del manifiesto. Mismo
// razonamiento que `contarLosQueSeVanAMover` en estructura.js: la version
// obvia (preguntarle a `findClipByPath` desde la raiz por cada clip) recorre
// el proyecto entero una vez POR CLIP, con un `getMediaFilePath()` async en
// cada item ya importado -- con 205 clips eso es mas trabajo que la
// importacion completa, y es lo que hacia lenta la importacion entera.
async function indexarClipsPorRuta(rootFolder) {
  const premierepro = require("premierepro");
  const indice = new Map();

  async function recorrer(folder) {
    for (const item of (await folder.getItems()) || []) {
      if (!item) continue;
      const clipItem = premierepro.ClipProjectItem.cast(item);
      if (clipItem) {
        try {
          const mediaPath = await clipItem.getMediaFilePath();
          indice.set(mediaPath, { clipItem, parentFolder: folder });
        } catch (e) {
          // no es un clip con archivo de medios (ej. una secuencia); seguir.
        }
        continue;
      }
      const subFolder = premierepro.FolderItem.cast(item);
      if (subFolder) await recorrer(subFolder);
    }
  }

  await recorrer(rootFolder);
  return indice;
}

// Recorre el arbol de bins buscando un ClipProjectItem con ese media path.
// Devuelve { clipItem, parentFolder } (la carpeta real en la que se
// encontro, por referencia) o null si no existe en ninguna parte del arbol
// que cuelga de `folder`.
async function findClipByPath(folder, filePath) {
  const premierepro = require("premierepro");
  const items = await folder.getItems();

  for (const item of items) {
    const clipItem = premierepro.ClipProjectItem.cast(item);
    if (clipItem) {
      try {
        const mediaPath = await clipItem.getMediaFilePath();
        if (mediaPath === filePath) return { clipItem, parentFolder: folder };
      } catch (e) {
        // no es un clip con archivo de medios (ej. una secuencia); continuar.
      }
      continue;
    }
    const subFolder = premierepro.FolderItem.cast(item);
    if (subFolder) {
      const match = await findClipByPath(subFolder, filePath);
      if (match) return match;
    }
  }
  return null;
}
