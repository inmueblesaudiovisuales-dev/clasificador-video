// inFrame/outFrame: enteros de numero de frame, o null para no tocar el
// in/out del clip (se deja el clip completo).
function applyInOut(project, clipItem, fps, inFrame, outFrame) {
  const premierepro = require("premierepro");
  if (inFrame === null || outFrame === null) return;

  const clipProjectItem = premierepro.ClipProjectItem.cast(clipItem);
  const frameRate = premierepro.FrameRate.createWithValue(fps);
  const inPoint = premierepro.TickTime.createWithFrameAndFrameRate(inFrame, frameRate);
  const outPoint = premierepro.TickTime.createWithFrameAndFrameRate(outFrame, frameRate);

  runTransaction(
    project,
    () => clipProjectItem.createSetInOutPointsAction(inPoint, outPoint),
    "Set in/out"
  );
}
