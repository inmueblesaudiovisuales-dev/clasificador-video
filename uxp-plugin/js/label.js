// Los tres estados de la app, traducidos a etiquetas de color de Premiere.
//
// `destacado` entro despues que los otros dos: hasta entonces no estaba en
// esta tabla, asi que los clips con estrella llegaban a Premiere SIN
// etiqueta, indistinguibles de uno sin marcar. La estrella se perdia en la
// frontera, que es justo lo que este plugin existe para evitar.
//
// MANGO es el dorado de la paleta de Premiere -- lo eligio Bruno. Verde y
// rosa ya estaban tomados por pick y reject.
const LABEL_BY_FLAG = {
  pick: "FOREST",
  reject: "ROSE",
  destacado: "MANGO",
};

// flag: "pick" | "reject" | "destacado" | "none". Si es "none", no hace nada
// (no limpia una etiqueta previa a proposito -- no es un caso pedido por el
// spec).
function applyFlagLabel(project, clipItem, flag) {
  const premierepro = require("premierepro");
  const labelName = LABEL_BY_FLAG[flag];
  if (!labelName) return;

  const colores = premierepro.Constants.ProjectItemColorLabel;
  // Si la version de Premiere no conoce ese nombre, el valor sale undefined
  // y la accion pondria cualquier cosa. Mejor no tocar el clip y DECIRLO,
  // con la lista de los que si existen: es lo unico que permite corregir el
  // nombre sin adivinar.
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
    "Set label " + flag
  );
}
