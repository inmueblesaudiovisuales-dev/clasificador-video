// Responsabilidad unica: construir la secuencia a partir de un manifest ya
// procesado. Vacio a proposito en la v1 -- el usuario decidio que el armado
// automatico no entra todavia.
//
// Cuando se implemente:
// - El orden lo manda el manifest (campo `orden`), NO se decide aqui. Las
//   reglas de que cuarto va primero viven en la app externa.
// - `orientacion` y `fps` del manifest definen los ajustes de la secuencia.
// - Recibe los clips ya importados (los que devolvio processManifest), no
//   vuelve a importar nada.
async function construirSecuencia(project, manifest, clipsImportados) {
  return null; // sin implementar en la v1
}
