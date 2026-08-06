// Arnes de auto-comprobacion. Solo se usa durante la construccion: corre al
// cargar el plugin y deja el resultado en un archivo que se lee desde la
// terminal. Se apaga poniendo AUTOCHECK_ACTIVO en false (Task 13).
const AUTOCHECK_ACTIVO = true;
const AUTOCHECK_SALIDA_DIR = "/private/tmp/clasificador-autocheck";
const AUTOCHECK_SALIDA_ARCHIVO = "resultado.json";

const autocheckResultados = [];
let autocheckPruebas = [];

// Cada task registra aqui sus comprobaciones. nombre: que se comprueba.
// fn: funcion async que devuelve { ok: boolean, detalle: string }.
function registrarPrueba(nombre, fn) {
  autocheckPruebas.push({ nombre, fn });
}

function anotarResultado(nombre, ok, detalle) {
  autocheckResultados.push({ nombre, ok: !!ok, detalle: String(detalle) });
  logToPanel(nombre + ": " + (ok ? "OK" : "FALLO") + " — " + detalle, !ok);
}

async function correrAutocheck() {
  if (!AUTOCHECK_ACTIVO) return;

  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  if (!project) {
    anotarResultado("proyecto activo", false, "No hay proyecto abierto en Premiere");
    await escribirResultadoAutocheck();
    return;
  }
  anotarResultado("proyecto activo", true, project.name);

  for (const prueba of autocheckPruebas) {
    try {
      const r = await prueba.fn(project);
      anotarResultado(prueba.nombre, r.ok, r.detalle);
    } catch (e) {
      anotarResultado(prueba.nombre, false, e.message);
    }
  }

  await escribirResultadoAutocheck();
}

async function escribirResultadoAutocheck() {
  const uxpFs = require("uxp").storage.localFileSystem;
  const fallidas = autocheckResultados.filter((r) => !r.ok).length;
  const carpeta = await uxpFs.getEntryWithUrl("file://" + AUTOCHECK_SALIDA_DIR);
  const archivo = await carpeta.createFile(AUTOCHECK_SALIDA_ARCHIVO, { overwrite: true });
  await archivo.write(
    JSON.stringify(
      {
        cuando: new Date().toISOString(),
        total: autocheckResultados.length,
        fallidas: fallidas,
        resultados: autocheckResultados,
      },
      null,
      2
    )
  );
}
