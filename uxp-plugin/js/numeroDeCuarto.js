// El numero que llevan las carpetas de cuartos: «03. Cocina».
//
// POR QUE EXISTE: Premiere ordena los bins por abecedario, asi que el numero
// es lo unico que sostiene el orden de la guia. Y la estructura de Bruno ya
// numera («02. Clip»), asi que no es un idioma nuevo.
//
// EL PREFIJO ES NUESTRO Y SOLO EL NUESTRO: digitos, punto, espacio. Un cuarto
// que Bruno haya llamado «2 Recamaras» no trae punto y no se toca. Es la
// misma regla que las marcas de estado en el nombre de los clips: se quita lo
// que pusimos nosotros, no lo que escribio el.
//
// Logica pura: se prueba con `node uxp-plugin/pruebas/correr.js`.
//
// Spec: docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md

const PREFIJO = /^\d+\.\s/;

// "Cocina" + 3 -> "03. Cocina". Dos digitos, y mas si hiciera falta.
function conNumero(nombre, posicion) {
  const n = String(posicion);
  return (n.length < 2 ? "0" + n : n) + ". " + String(nombre || "");
}

// "03. Cocina" -> "Cocina". Quita UN prefijo, no todos: «01. 2 Recamaras» es
// la carpeta numerada de un cuarto que se llama «2 Recamaras».
function sinNumero(nombre) {
  return String(nombre || "").replace(PREFIJO, "");
}

// Si dos nombres de carpeta son el mismo cuarto, tengan el numero que tengan.
//
// Se compara por IGUALDAD EXACTA despues de quitar el numero: nada de
// minusculas ni quitar acentos. «Recamara 1» y «Recámara 1» son dos cuartos
// distintos, igual que en la revision de la lista.
function esElMismoCuarto(unNombre, otroNombre) {
  return sinNumero(unNombre) === sinNumero(otroNombre);
}
