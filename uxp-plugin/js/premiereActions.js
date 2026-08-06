// Envuelve el patron obligatorio: executeTransaction siempre dentro de
// lockedAccess, o falla con "The script object is no longer valid".
function runTransaction(project, buildActions, undoLabel) {
  let result;
  project.lockedAccess(() => {
    result = project.executeTransaction((compoundAction) => {
      const actions = buildActions();
      const list = Array.isArray(actions) ? actions : [actions];
      for (const action of list) {
        compoundAction.addAction(action);
      }
    }, undoLabel);
  });
  return result;
}
