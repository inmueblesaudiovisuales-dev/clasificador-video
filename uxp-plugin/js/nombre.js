// El nombre de cada clip en el panel de proyecto de Premiere. NO toca el
// archivo en disco.
//
// FORMATO (spec 2026-09-21):
//
//     [simbolo ]Cuarto NN [CAMARA]
//
// - simbolo: «★ » destacado, «✓ » pick, «✕ » reject. Un clip sin marcar no
//   lleva simbolo.
// - Cuarto: el nombre del cuarto, sin numero.
// - NN: numero secuencial DENTRO del cuarto, a dos digitos.
// - [CAMARA]: siempre, combinada en orden fijo Sony/Pocket/Drone, con la
//   misma fuente que la marca de la carpeta (`marcaCamara.js`). Si el cuarto
//   no tiene ninguna camara reconocible, no hay marca.
//
// El nombre del ARCHIVO original ya no aparece: el item en Premiere se
// explica solo. El archivo en disco es el mismo.
//
// El nombre se RECALCULA ENTERO desde el manifiesto cada vez, asi que volver
// a correr la importacion no acumula. A cambio, un renombre manual del clip
// se pierde al reimportar -- es un dato generado, no algo que se edite a
// mano. Ver §7 de la spec.
const PREFIJO_POR_FLAG = {
  destacado: "★ ",
  pick: "✓ ",
  reject: "✕ ",
};

// El numero del clip dentro de su cuarto, a dos digitos ("01"). Si pasa de
// 99 crece a tres sin romper nada.
function numeroDeClip(posicion) {
  const n = String(posicion);
  return n.length < 2 ? "0" + n : n;
}

// El nombre completo del clip. `marcaDeCamara` es "SONY", "SONY+DRONE", etc.,
// o "" si no hay ninguna.
function nombreDeClip(cuarto, numero, marcaDeCamara, flag) {
  const simbolo = PREFIJO_POR_FLAG[flag] || "";
  const camara = marcaDeCamara ? " [" + marcaDeCamara + "]" : "";
  return simbolo + String(cuarto || "") + " " + numeroDeClip(numero) + camara;
}

// Numera los clips POR CUARTO, en el orden del manifiesto (el mismo en que
// Bruno los acomodo en la hoja). Devuelve un arreglo paralelo a `clips`.
//
// La llave del contador es el `categoria_path` completo: el mismo nombre de
// cuarto en dos unidades distintas son dos contadores (y, aceptado por
// ahora, dos nombres de clip que pueden coincidir). Los clips sin clasificar
// (sin categoria_path) comparten un contador aparte.
function numerosDeClip(clips) {
  const contador = {};
  return (clips || []).map((c) => {
    const llave = JSON.stringify((c && c.categoria_path) || []);
    contador[llave] = (contador[llave] || 0) + 1;
    return contador[llave];
  });
}

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

// Se avisa UNA vez por importacion, no una por clip: con 40 clips serian 40
// renglones identicos tapando los errores que si son distintos.
let yaSeAvisoDeRenombrar = false;

function reiniciarAvisoDeRenombrar() {
  yaSeAvisoDeRenombrar = false;
}

// Le pone al clip su nombre completo. Idempotente por construccion: si el
// nombre ya es el deseado, no se abre transaccion (un `⌘Z` de Bruno no tiene
// por que gastarse en deshacer un renombre que no renombro nada).
function aplicarNombreDeClip(project, clipItem, cuarto, numero, marcaDeCamara, flag) {
  const nombre = clipItem.name;
  if (typeof nombre !== "string" || !nombre) return;

  const deseado = nombreDeClip(cuarto, numero, marcaDeCamara, flag);
  if (deseado === nombre) return;

  const metodo = ACCIONES_DE_RENOMBRAR.find(
    (n) => typeof clipItem[n] === "function"
  );
  if (!metodo) {
    // No se puede renombrar en esta version. El clip NO se toca y llega con
    // su nombre de archivo, sin cuarto, numero ni marca -- que es una
    // perdida real, asi que se dice, con lo que el objeto si tiene para que
    // la proxima version de esta lista salga de un dato y no de otra
    // suposicion.
    if (!yaSeAvisoDeRenombrar) {
      yaSeAvisoDeRenombrar = true;
      logToPanel(
        "No pude nombrar los clips (cuarto, número, cámara y ★ / ✓ / ✕): " +
        "esta versión de Premiere no tiene ninguna de estas acciones (" +
        ACCIONES_DE_RENOMBRAR.join(", ") + "). Los clips llegan bien y en su " +
        "cuarto, pero con su nombre de archivo. Lo que sí tiene el clip: " +
        Object.getOwnPropertyNames(Object.getPrototypeOf(clipItem)).join(", "),
        true
      );
    }
    return;
  }

  runTransaction(
    project,
    () => clipItem[metodo](deseado),
    "Nombrar clip " + deseado
  );
}
