// De que camara salio el clip, traducido a etiqueta de color de Premiere.
//
// ANTES ESTA ETIQUETA DECIA EL ESTADO (pick verde, reject rosa, destacado
// dorado). Cambio el 2026-09-08: en Premiere un item tiene UNA sola etiqueta
// de color, y Bruno la quiere para saber de un vistazo de que camara salio
// cada clip.
//
// El estado no se pierde: ya viaja en las subcarpetas Picks / Rejects / Sin
// marcar que arma `con_subcarpeta_de_estado` del lado de la app. El unico
// que se habria borrado es el DESTACADO --que iba en la misma carpeta que
// los picks y solo se distinguia por el dorado-- y por eso ahora llega con
// «★» al inicio del nombre; ver `nombre.js`.
//
// Los colores los eligio Bruno: azul y amarillo son los dos mas separados
// del panel, y esa distancia es todo el punto.
const LABEL_BY_CAMARA = {
  sony: "CERULEAN",
  dji: "MANGO",
  otra: "VIOLET",
};

// camara: "sony" | "dji" | "otra". Un valor que no este en la tabla no toca
// el clip -- puede venir de un manifiesto de otra version, y pintar
// «cualquier cosa» es peor que no pintar.
function applyCameraLabel(project, clipItem, camara) {
  const premierepro = require("premierepro");
  const labelName = LABEL_BY_CAMARA[camara];
  if (!labelName) return;

  const colores = premierepro.Constants.ProjectItemColorLabel;
  // Si la version de Premiere no conoce ese nombre, el valor sale undefined
  // y la accion pondria cualquier cosa. Mejor no tocar el clip y DECIRLO,
  // con la lista de los que si existen: es lo unico que permite corregir el
  // nombre sin adivinar. La guarda es de agosto y se queda tal cual --
  // `MANGO` esta confirmado en vivo (indice 7, el 2026-08-10), pero
  // `CERULEAN` y `VIOLET` no, y este es el aviso que lo dira.
  if (colores[labelName] === undefined) {
    logToPanel(
      "El color «" + labelName + "» no existe en esta versión de Premiere. " +
      "Disponibles: " + Object.keys(colores).join(", "),
      true
    );
    return;
  }

  runTransaction(
    project,
    () => clipItem.createSetColorLabelAction(colores[labelName]),
    "Set label " + camara
  );
}

// El color del bin de un cuarto que ya montaste entero.
//
// EL CHOQUE, RESUELTO A PROPOSITO: arriba de este archivo esta escrito que en
// Premiere el color dice la CAMARA. Eso vale para los CLIPS, que es donde se
// decidio y donde Bruno lo usa para arrastrarle el LUT a toda una camara de
// un jalon. Un BIN no es un clip y nunca tuvo color, asi que ahi queda libre
// para decir otra cosa: si ya lo montaste.
//
// Y el verde NO entra en la paleta de camaras -- CERULEAN, MANGO y VIOLET
// siguen siendo de ellas. Un color que ya significara una camara diciendo
// ademas «montado» seria el mismo error con otro disfraz.
const LABEL_MONTADO = "FOREST";

function pintarBinMontado(project, binItem, montado) {
  const premierepro = require("premierepro");
  const colores = premierepro.Constants.ProjectItemColorLabel;
  const destino = montado ? colores[LABEL_MONTADO] : colores.NONE;

  // Ni la documentacion de Adobe ni la suerte: si esta version no conoce el
  // color, no se pinta nada y se dice UNA vez, con lo que si existe. Mismo
  // trato que `applyCameraLabel`. Pero aqui hay DOS causas distintas -- que
  // falte el verde (`FOREST`) o que falte el gris de despintar (`NONE`) -- y
  // el aviso tiene que nombrar la que de verdad paso: si solo falta `NONE`,
  // decir «no lo permite» es mentira, porque pintar SI funciona.
  if (destino === undefined) {
    avisarUnaVezDelVerde(colores, montado ? "FOREST" : "NONE");
    return;
  }
  if (typeof binItem.createSetColorLabelAction !== "function") {
    // Aqui la causa es otra: no falta el color, falta el metodo. Se avisa
    // con la misma bandera de "metodo" para las dos direcciones -- pintar y
    // despintar comparten el mismo `createSetColorLabelAction`.
    avisarUnaVezDelVerde(colores, "metodo");
    return;
  }
  runTransaction(
    project,
    () => binItem.createSetColorLabelAction(destino),
    (montado ? "Marcar montado " : "Desmarcar ") + binItem.name
  );
}

// Una bandera POR CAUSA, no una sola global: si ya avisamos que falta
// `FOREST`, eso no dice nada de si falta `NONE` -- son dos preguntas
// distintas a la misma version de Premiere, y una banderita compartida
// dejaria la segunda causa muda para siempre despues de la primera.
const yaSeAvisoDelVerde = {};

function avisarUnaVezDelVerde(colores, causa) {
  if (yaSeAvisoDelVerde[causa]) return;
  yaSeAvisoDelVerde[causa] = true;

  const razon =
    causa === "metodo"
      ? "esta versión de Premiere no tiene cómo pintarle color a una carpeta"
      : "esta versión de Premiere no tiene el color «" + causa + "»";
  logToPanel(
    "No pude pintar las carpetas de lo que ya montaste: " + razon + ". " +
      "Las palomitas del panel siguen funcionando. " +
      "Colores que sí tiene: " + Object.keys(colores).join(", "),
    true
  );
}
