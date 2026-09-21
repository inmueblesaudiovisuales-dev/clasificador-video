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

// La carpeta de un cuarto, con su numero al dia.
//
// EL CASO QUE ESTO EVITA (§5.2 del spec): Bruno importa mas clips del mismo
// rodaje, el orden de la guia salio distinto, y la Cocina que era «03.
// Cocina» llega como «05. Cocina». Buscando por nombre exacto, Premiere le
// crea una SEGUNDA carpeta y los clips del mismo cuarto quedan repartidos en
// dos -- sin que nada avise. Es la familia de los ocho bugs del 2026-08-22.
//
// Por eso se busca por el nombre SIN numero, y si aparece con otro, se le
// cambia el numero a esa en vez de crear otra.
//
// NO SE LE CREE A LA DOCUMENTACION DE ADOBE sobre como se renombra: el
// metodo se busca en el objeto de verdad, igual que `aplicarNombreDeClip` en
// `nombre.js`. Si ninguno esta, la carpeta se REUSA con su numero viejo --
// un numero desfasado es un orden raro; una segunda carpeta es la mitad de
// los clips escondida.
async function resolverCuarto(project, carpetaDeClips, nombreConNumero) {
  const premierepro = require("premierepro");

  const items = (await carpetaDeClips.getItems()) || [];
  // Solo CARPETAS: un clip suelto llamado igual que un cuarto no es su
  // carpeta, y tomarlo por tal hacia que el plugin le renombrara. Ver
  // `carpetaDelCuarto` en `numeroDeCuarto.js`.
  const existente = carpetaDelCuarto(
    items, nombreConNumero, premierepro.FolderItem.cast
  );

  if (existente) {
    if (existente.name !== nombreConNumero) {
      const metodo = ACCIONES_DE_RENOMBRAR.find(
        (n) => typeof existente[n] === "function"
      );
      if (metodo) {
        runTransaction(
          project,
          () => existente[metodo](nombreConNumero),
          "Renumerar " + existente.name + " -> " + nombreConNumero
        );
      } else {
        logToPanel(
          "No pude renumerar «" + existente.name + "» a «" + nombreConNumero +
          "»: esta versión de Premiere no tiene ninguna de estas acciones (" +
          ACCIONES_DE_RENOMBRAR.join(", ") + "). Los clips entran a la " +
          "carpeta que ya existía, con su número viejo. Lo que sí tiene: " +
          Object.getOwnPropertyNames(Object.getPrototypeOf(existente)).join(", "),
          true
        );
      }
    }
    return existente;
  }

  return await resolveBinChain(project, carpetaDeClips, [nombreConNumero]);
}
