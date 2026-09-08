// Las marcas de estado sobre el nombre del item en el panel de proyecto de
// Premiere. NO tocan el archivo en disco.
//
// Estas marcas son AHORA LA UNICA forma en que el estado cruza a Premiere.
// Se llego aqui en tres pasos el mismo dia, y conviene leerlos juntos porque
// cada uno hizo sobrar al siguiente:
//
//   1. La etiqueta de color paso a decir la CAMARA (`label.js`), asi que el
//      destacado --que solo se distinguia por el dorado-- estreno su «★».
//   2. Bruno pidio lo mismo para el reject, y que esa marca REEMPLAZARA la
//      carpeta «Rejects».
//   3. Y luego que se fueran tambien «Picks» y «Sin marcar»: cada cuarto
//      queda plano, con todos sus clips adentro.
//
// El paso 3 dejaba al pick indistinguible de un clip sin ver --era la
// carpeta la que lo decia-- asi que el pick estreno su «✓». Un clip SIN
// marca ya no significa «pick»: significa que no lo has visto.
//
// El fondo de los tres pasos es el mismo: una carpeta esconde el clip y una
// marca lo enseña. Y perder un dato al cruzar a Premiere es justo lo que
// este plugin existe para evitar.
const PREFIJO_POR_FLAG = {
  destacado: "★ ",
  pick: "✓ ",
  reject: "✕ ",
};

// Todas las marcas que este plugin pone, para poder reconocer las suyas.
const PREFIJOS_PROPIOS = Object.keys(PREFIJO_POR_FLAG).map((f) => PREFIJO_POR_FLAG[f]);

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

// El nombre sin ninguna marca de este plugin al inicio.
//
// En bucle a proposito: un nombre que ya venga con «★ ✕ » --de una version
// anterior que solo agregaba, o de dos pasadas de aquella-- se limpia
// entero. Solo se quitan las marcas de `PREFIJO_POR_FLAG` y solo al inicio:
// un «✕» que Bruno haya escrito el mismo a media frase no es nuestro y no se
// toca.
function nombreLimpio(nombre) {
  let limpio = nombre;
  let seguir = true;
  while (seguir) {
    seguir = false;
    for (const prefijo of PREFIJOS_PROPIOS) {
      if (limpio.indexOf(prefijo) === 0) {
        limpio = limpio.slice(prefijo.length);
        seguir = true;
      }
    }
  }
  return limpio;
}

// flag: "pick" | "reject" | "destacado" | "none".
//
// LAS REGLAS, y todas son sobre no hacer daño:
//
// 1. Es IDEMPOTENTE. Volver a correr la misma clasificacion es un caso
//    normal --es como se corrige un error-- y sin esto quedaria
//    «★ ★ ★ C0001.MP4».
//    Y un clip sin marcar se queda sin marca: no hay prefijo para «none»
//    a proposito, porque «no lo he visto» no es algo que se anuncie.
// 2. **Cambia la marca cuando cambia el estado.** Un clip que era reject y
//    ahora es destacado pierde su «✕» y gana su «★»; uno que dejo de ser
//    los dos se queda sin marca. Hasta que existio la segunda marca esto
//    era «solo agrega, nunca quita» --por miedo a renombrar lo que Bruno
//    renombro a mano-- y con dos marcas ese miedo se volvio el bug: el clip
//    terminaba con las dos, diciendo dos cosas contrarias a la vez.
//    Se resuelve quitando SOLO nuestras marcas y SOLO al inicio, que son
//    las unicas que sabemos que pusimos nosotros. Ver `nombreLimpio`.
// 3. Si el nombre no cambia, no se abre transaccion: un `⌘Z` de Bruno no
//    tiene por que gastarse en deshacer un renombre que no renombro nada.
function applyFlagPrefix(project, clipItem, flag) {
  const nombre = clipItem.name;
  if (typeof nombre !== "string" || !nombre) return;

  const deseado = (PREFIJO_POR_FLAG[flag] || "") + nombreLimpio(nombre);
  if (deseado === nombre) return;

  const metodo = ACCIONES_DE_RENOMBRAR.find(
    (n) => typeof clipItem[n] === "function"
  );
  if (!metodo) {
    // No se puede renombrar en esta version. El clip NO se toca y los
    // destacados y rejects llegan sin marca propia -- que es una perdida
    // real, asi que se dice, con lo que el objeto si tiene para que la
    // proxima version de esta lista salga de un dato y no de otra
    // suposicion.
    if (!yaSeAvisoDeRenombrar) {
      yaSeAvisoDeRenombrar = true;
      logToPanel(
        "No pude marcar los clips con ★ / ✓ / ✕: esta version de Premiere " +
        "no tiene ninguna de estas acciones (" +
        ACCIONES_DE_RENOMBRAR.join(", ") + "). Los clips llegan bien y en su " +
        "cuarto, pero SIN NINGUNA marca de estado -- avisale a Bruno, porque " +
        "es lo unico que distingue un pick de un reject. Lo que si tiene el " +
        "clip: " +
        Object.getOwnPropertyNames(Object.getPrototypeOf(clipItem)).join(", "),
        true
      );
    }
    return;
  }

  runTransaction(
    project,
    () => clipItem[metodo](deseado),
    "Marcar " + flag
  );
}
