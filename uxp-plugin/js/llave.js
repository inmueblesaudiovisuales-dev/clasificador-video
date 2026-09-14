// La llave de la API: se pega una vez y se queda guardada.
//
// DONDE SE GUARDA: en la carpeta de datos del plugin
// (`localFileSystem.getDataFolder()`), que es privada del plugin y no viaja a
// ningun lado. Los tres lugares que se descartaron, cada uno por su motivo:
//   - el proyecto de Premiere -> viaja al cliente cuando Bruno le manda el
//     proyecto;
//   - junto al material -> se copia a discos y se sube a la nube con el
//     shooting;
//   - el repo -> se sube a GitHub, que es publico.
//
// Y NUNCA pasa por `logToPanel`. El log es el archivo que uno manda cuando
// algo falla, o sea el que mas ojos ve -- una llave ahi dentro es una llave
// regalada. Si alguna vez hay que depurar esto, se depura con `llaveTapada`.

const LLAVE_ARCHIVO = "llave.json";

async function guardarLlave(llave) {
  const uxpFs = require("uxp").storage.localFileSystem;
  const carpeta = await uxpFs.getDataFolder();
  const archivo = await carpeta.createFile(LLAVE_ARCHIVO, { overwrite: true });
  await archivo.write(JSON.stringify({ llave: String(llave || "").trim() }));
}

// Devuelve "" cuando no hay llave guardada. Que no la haya es el caso de la
// primera vez, no un error: el panel pide que la peguen y sigue su vida.
async function leerLlave() {
  const uxpFs = require("uxp").storage.localFileSystem;
  try {
    const carpeta = await uxpFs.getDataFolder();
    const archivo = await carpeta.getEntry(LLAVE_ARCHIVO);
    const datos = JSON.parse(await archivo.read());
    return String((datos && datos.llave) || "");
  } catch (e) {
    return "";
  }
}

async function borrarLlave() {
  const uxpFs = require("uxp").storage.localFileSystem;
  try {
    const carpeta = await uxpFs.getDataFolder();
    const archivo = await carpeta.getEntry(LLAVE_ARCHIVO);
    await archivo.delete();
  } catch (e) {
    // no habia nada que borrar
  }
}

// Como se ensena en pantalla: los ultimos cuatro y lo demas tapado.
//
// Una llave de menos de ocho se tapa ENTERA. Ensenar los ultimos cuatro de
// una llave corta es ensenar media llave, y el punto de taparla es que
// alguien pueda ver la pantalla de Bruno sin llevarse nada.
function llaveTapada(llave) {
  const texto = String(llave || "");
  if (!texto) return "";
  if (texto.length < 8) return "••••••••";
  return "••••••••" + texto.slice(-4);
}
