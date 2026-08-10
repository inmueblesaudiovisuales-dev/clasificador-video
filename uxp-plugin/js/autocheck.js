// Arnes de auto-comprobacion. Solo se usa durante la construccion: corre al
// cargar el plugin y deja el resultado en un archivo que se lee desde la
// terminal. Se apaga poniendo AUTOCHECK_ACTIVO en false (Task 13).
const AUTOCHECK_ACTIVO = true;

// Cuales correr. Vacio = todas. Con algo adentro, solo las pruebas cuyo
// nombre contenga alguno de estos pedazos.
//
// Existe porque correr las ~40 pruebas para contestar dos preguntas sueltas
// tiene dos costos que no valen la pena: dejan bins de basura por todo el
// proyecto de Bruno, y una de ellas necesita una carpeta de segunda tarjeta
// que hay que armar a mano y que el repo no trae -- o sea que fallaria por
// una razon que no tiene nada que ver con lo que se esta preguntando.
const AUTOCHECK_SOLO = ["spike:", "MANGO"];
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

  const seleccionadas = AUTOCHECK_SOLO.length
    ? autocheckPruebas.filter((p) => AUTOCHECK_SOLO.some((pedazo) => p.nombre.indexOf(pedazo) !== -1))
    : autocheckPruebas;
  anotarResultado(
    "seleccion",
    seleccionadas.length > 0,
    seleccionadas.length + " de " + autocheckPruebas.length + " pruebas" +
      (AUTOCHECK_SOLO.length ? " (filtro: " + AUTOCHECK_SOLO.join(", ") + ")" : "")
  );

  for (const prueba of seleccionadas) {
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
