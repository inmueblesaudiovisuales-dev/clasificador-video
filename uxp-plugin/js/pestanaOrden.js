// La pestana «Guia de edicion»: enseña la guia que se armo en Clipify.
//
// NO PREGUNTA NADA. No tiene llave, no toca la red y no espera. La guia se
// arma en Clipify --donde los cuartos nacen y donde Bruno acaba de ver el
// material-- y viaja congelada adentro del manifest. Si quiere otra, regresa
// a Clipify.
//
// Aqui vivian las preguntas, la llave de DeepSeek y el armado del prompt. Se
// fueron completas el 2026-09-14, no comentadas: git guarda el historial.
//
// LA PESTANA NO ESCRIBE NADA EN EL PROYECTO. Ni una carpeta, ni un clip, ni
// el timeline. Es de lectura entera, y esa es la razon por la que puede vivir
// dentro del mismo plugin que si escribe sin dar miedo.
//
// Spec: docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md

let pestanaArmada = false;

function abrirPestanaOrden(hoja) {
  if (pestanaArmada) return;
  pestanaArmada = true;
  dibujarGuia(hoja, guiaImportada());
}

// Se separa del `abrir` para poder repintarla cuando llegue un manifest nuevo
// sin volver a armar la pestana.
function dibujarGuia(hoja, guia) {
  hoja.innerHTML = "";

  if (!guia || !guia.orden || !guia.orden.length) {
    // Que no traiga guia NO es un error: es un proyecto que se exporto sin
    // apretar el boton, o de antes de que esto existiera. Se dice con esas
    // palabras y no se inventa una.
    const vacio = document.createElement("p");
    vacio.className = "tenue";
    vacio.textContent =
      "Este proyecto no trae guía de edición. Se arma en Clipify, " +
      "con el botón «Guía de edición», antes de exportar.";
    hoja.appendChild(vacio);
    return;
  }

  if (guia.recorrido) {
    const parrafo = document.createElement("p");
    parrafo.className = "guia-recorrido";
    parrafo.textContent = guia.recorrido;
    hoja.appendChild(parrafo);
  }

  const lista = document.createElement("ol");
  lista.className = "guia-orden";
  for (const renglon of guia.orden) {
    const li = document.createElement("li");

    const nombre = document.createElement("span");
    nombre.className = "guia-cuarto";
    nombre.textContent = renglon.cuarto;
    li.appendChild(nombre);

    if (renglon.porque) {
      const porque = document.createElement("span");
      // El aviso de que se salio del patron de Bruno se ve DISTINTO del
      // resto: es informacion que solo tenia la IA, y es lo unico que hay
      // que leer con atencion.
      porque.className = renglon.fuera_del_patron
        ? "guia-porque fuera-del-patron"
        : "guia-porque";
      porque.textContent = " — " + renglon.porque;
      li.appendChild(porque);
    }

    lista.appendChild(li);
  }
  hoja.appendChild(lista);
}

// Vuelve a pintar la pestana con la guia que acaba de llegar, si es que ya
// estaba armada. Sin esto, importar un manifest nuevo dejaba en pantalla la
// guia del anterior -- dos partes del programa diciendo cosas distintas del
// mismo dato, que es la familia de bugs que este repo persigue.
function repintarGuia() {
  const hoja = document.getElementById("hoja-orden");
  if (hoja && pestanaArmada) dibujarGuia(hoja, guiaImportada());
}
