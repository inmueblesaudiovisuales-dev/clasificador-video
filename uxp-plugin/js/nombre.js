// El «★» de los destacados, sobre el nombre del item en el panel de
// proyecto. NO toca el archivo en disco.
//
// Existe porque la etiqueta de color paso a decir la camara (`label.js`), y
// el destacado era el unico estado que solo se distinguia por color: va en
// la misma carpeta «Picks» que los demas picks --decision del 2026-08-22, un
// destacado ES un pick reforzado-- asi que sin marca propia se perderia en
// la frontera. Que la estrella se pierda al cruzar a Premiere es justo lo
// que este plugin existe para evitar.
const PREFIJO_DESTACADO = "★ ";

// Los nombres que PODRIA tener la accion de renombrar, en orden de
// probabilidad. Se buscan en el objeto en vez de llamar al primero a ciegas.
//
// Esto no es paranoia: en este plugin la documentacion de Adobe ya mintio
// TRES veces --la fabrica de efectos devuelve un objeto sin metodos,
// `getParam` necesita `await` aunque la referencia diga que no, y el nombre
// de un parametro es `displayName` como propiedad y no `getDisplayName()`--
// y una cuarta costaria una corrida entera de Premiere. La regla del repo
// es enumerar el prototipo real antes de llamar; esto es esa regla, escrita
// para que se cumpla sola en produccion.
const ACCIONES_DE_RENOMBRAR = [
  "createSetNameAction",
  "createRenameAction",
  "createSetNodeNameAction",
];

// Se avisa UNA vez por importacion, no una por clip: con 40 destacados
// serian 40 renglones identicos tapando los errores que si son distintos.
let yaSeAvisoDeRenombrar = false;

function reiniciarAvisoDeRenombrar() {
  yaSeAvisoDeRenombrar = false;
}

// flag: "pick" | "reject" | "destacado" | "none".
//
// DOS REGLAS, y las dos son sobre no hacer daño:
//
// 1. Es IDEMPOTENTE. Volver a correr la misma clasificacion es un caso
//    normal --es como se corrige un error-- y sin esta guarda quedaria
//    «★ ★ ★ C0001.MP4».
// 2. Solo AGREGA, nunca quita. Si un clip dejo de ser destacado, su ★ se
//    queda. Quitarlo significaria que el plugin renombra clips que Bruno
//    pudo haber renombrado a mano, y ese daño es peor que un ★ de mas.
//    Mismo criterio que la etiqueta de color, que a proposito nunca limpia
//    una previa.
function applyStarPrefix(project, clipItem, flag) {
  if (flag !== "destacado") return;

  const nombre = clipItem.name;
  if (typeof nombre !== "string" || !nombre) return;
  if (nombre.indexOf(PREFIJO_DESTACADO) === 0) return;

  const metodo = ACCIONES_DE_RENOMBRAR.find(
    (n) => typeof clipItem[n] === "function"
  );
  if (!metodo) {
    // No se puede renombrar en esta version. El clip NO se toca y el
    // destacado llega sin marca -- que es una perdida real, asi que se
    // dice, con lo que el objeto si tiene para que la proxima version de
    // esta lista salga de un dato y no de otra suposicion.
    if (!yaSeAvisoDeRenombrar) {
      yaSeAvisoDeRenombrar = true;
      logToPanel(
        "No pude ponerle el ★ a los destacados: esta version de Premiere no " +
        "tiene ninguna de estas acciones (" + ACCIONES_DE_RENOMBRAR.join(", ") +
        "). Los destacados llegan sin marca propia, dentro de su carpeta " +
        "Picks. Lo que si tiene el clip: " +
        Object.getOwnPropertyNames(Object.getPrototypeOf(clipItem)).join(", "),
        true
      );
    }
    return;
  }

  runTransaction(
    project,
    () => clipItem[metodo](PREFIJO_DESTACADO + nombre),
    "Marcar destacado"
  );
}
