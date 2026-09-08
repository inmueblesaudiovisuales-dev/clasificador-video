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
      "El color «" + labelName + "» no existe en esta version de Premiere. " +
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
