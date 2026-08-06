const LABEL_BY_FLAG = {
  pick: "FOREST",
  reject: "ROSE",
};

// flag: "pick" | "reject" | "none". Si es "none", no hace nada (no limpia
// una etiqueta previa a proposito -- no es un caso pedido por el spec).
function applyFlagLabel(project, clipItem, flag) {
  const premierepro = require("premierepro");
  const labelName = LABEL_BY_FLAG[flag];
  if (!labelName) return;

  runTransaction(
    project,
    () => clipItem.createSetColorLabelAction(premierepro.Constants.ProjectItemColorLabel[labelName]),
    "Set label " + flag
  );
}
