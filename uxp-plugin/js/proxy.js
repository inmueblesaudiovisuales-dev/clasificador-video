// proxyPath: ruta absoluta al proxy, o null si el clip no tiene proxy
// emparejado (ej. dron). attachProxy no es parte de una transaccion
// (segun la referencia de la API, no es undoable).
async function attachProxyIfPresent(clipItem, proxyPath) {
  const premierepro = require("premierepro");
  if (!proxyPath) return false;

  const clipProjectItem = premierepro.ClipProjectItem.cast(clipItem);
  const ok = await clipProjectItem.attachProxy(proxyPath, false);
  return ok;
}
