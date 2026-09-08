// El esqueleto del proyecto de Premiere de Bruno. Un solo lugar donde esta
// escrito como se llama cada carpeta y cual es cual.
//
// Vive aqui y no del lado de la app a proposito: la estructura del proyecto
// de Premiere es cosa de Premiere. Si la app la escribiera en el
// `categoria_path`, el nombre de estas carpetas quedaria repartido en dos
// repos y se desincronizarian en el primer cambio de opinion -- mismo
// criterio por el que `con_subcarpeta_de_estado` no vive en la sesion.
//
// Los nombres van tal cual los escribio Bruno, con su numero y su punto:
// Premiere ordena por abecedario, asi que el numero es lo que sostiene el
// orden.
//
// «06. Graficos» y «05. Voz» salieron de revisar la lista con el el
// 2026-09-08. Sin la primera, los titulos y el logo del cliente caian
// revueltos en «Assets adicionales»; y «Voz IA» describia de donde salio la
// voz y no que es, asi que el dia que grabe una locucion de verdad el
// archivo estaria en una carpeta que miente.
const CARPETAS_DEL_PROYECTO = [
  "01. Secuencia",
  "02. Clip",
  "03. AE composition",
  "04. Musica",
  "05. Voz",
  "06. Graficos",
  "07. Assets adicionales",
];

// Donde cuelga TODO el material clasificado. Es la segunda de la lista y no
// una cadena suelta: si alguien renombra la carpeta alla arriba, esto sigue
// apuntando a la misma.
const CARPETA_DE_CLIPS = CARPETAS_DEL_PROYECTO[1];

// Crea las siete al empezar, aunque cinco se queden vacias: son el esqueleto
// del proyecto y existen para que Bruno meta cosas ahi, no para que la app
// las llene.
//
// `resolveBinChain` REUSA lo que ya existe, asi que un proyecto que ya tenga
// su «04. Musica» con musica adentro no recibe una segunda.
async function crearEsqueleto(project, rootFolder) {
  for (const nombre of CARPETAS_DEL_PROYECTO) {
    await resolveBinChain(project, rootFolder, [nombre]);
  }
}

// El camino completo de un clip: su cuarto y su estado, colgados de
// «02. Clip». La app manda ["Cocina", "Picks"] y aqui se vuelve
// ["02. Clip", "Cocina", "Picks"].
function caminoDelClip(categoryPath) {
  return [CARPETA_DE_CLIPS].concat(categoryPath);
}

// Todas las carpetas que cuelgan de `ancestro`, ella incluida, en un Set.
//
// Por REFERENCIA y no por nombre: hay bins homonimos en ramas distintas
// (Recamara 1 > Bano vs Recamara 2 > Bano), y esa es la misma razon por la
// que `importOrReuseClip` compara carpetas con `===`. La comparacion por
// referencia es segura porque `FolderItem.cast(item)` devuelve el mismo
// objeto para el mismo item -- confirmado en vivo, ver `importClip.js`.
async function carpetasDentroDe(ancestro, acumulado) {
  const premierepro = require("premierepro");
  acumulado = acumulado || new Set();
  acumulado.add(ancestro);
  for (const item of (await ancestro.getItems()) || []) {
    if (!item) continue;
    const sub = premierepro.FolderItem.cast(item);
    if (sub) await carpetasDentroDe(sub, acumulado);
  }
  return acumulado;
}

// Cuantos clips del manifiesto ya estan en el proyecto PERO fuera de
// «02. Clip». Se pregunta antes de tocar nada, porque esos se van a mover y
// eso hay que decirlo antes de hacerlo: que las cosas cambien de lugar solas
// es exactamente el modo de falla que esta app existe para no tener.
//
// **En DOS pasadas por el arbol, no en una por clip.** La version obvia
// --preguntarle a `findClipByPath` por cada clip-- recorre el proyecto
// entero 205 veces con un `await getMediaFilePath()` en cada item, y eso es
// mas trabajo que la importacion completa que viene despues. Aqui el arbol
// se recorre una vez para las carpetas y otra para los clips.
async function contarLosQueSeVanAMover(rootFolder, manifest, carpetaDeClips) {
  const premierepro = require("premierepro");
  const adentro = await carpetasDentroDe(carpetaDeClips);
  const fuera = new Set();

  async function recorrer(folder) {
    for (const item of (await folder.getItems()) || []) {
      if (!item) continue;
      const clip = premierepro.ClipProjectItem.cast(item);
      if (clip) {
        if (!adentro.has(folder)) {
          try {
            fuera.add(await clip.getMediaFilePath());
          } catch (e) {
            // no es un clip con archivo de medios (ej. una secuencia)
          }
        }
        continue;
      }
      const sub = premierepro.FolderItem.cast(item);
      if (sub) await recorrer(sub);
    }
  }

  await recorrer(rootFolder);
  return manifest.clips.filter((c) => fuera.has(c.ruta)).length;
}
