// La pestana «Guia de edicion»: enseña el guion que se armo en Clipify y deja
// palomear lo que ya montaste.
//
// NO PIDE NADA. No tiene llave, no toca la red y no espera. El guion se arma
// en Clipify y viaja congelado adentro del manifest.
//
// LO UNICO QUE ESCRIBE ES TU AVANCE, y va a la carpeta del plugin, no al
// proyecto (ver `avanceDisco.js`). Lo que si toca el proyecto es el color del
// bin, y es un REFLEJO del avance, recalculado cada vez.
//
// UN PASO NO ES UN CUARTO: la aerea abre y cierra, son dos pasos y una sola
// carpeta. Todo lo de aqui va por numero de paso.
//
// Spec: docs/superpowers/specs/2026-09-15-el-guion-y-las-carpetas-design.md

let pestanaArmada = false;
let avanceActual = [];

async function abrirPestanaOrden() {
  if (pestanaArmada) return;
  pestanaArmada = true;
  await repintarGuia();
}

// Vuelve a pintar la pestana con la guia y el avance de ahora. Se llama al
// abrirla, al importar un manifest nuevo y despues de cada palomita.
//
// TAMBIEN recalcula el color de los bins: el spec dice que ese color se
// recalcula del archivo cada vez que se abre el panel, asi que no puede
// vivir solo del lado de `palomear`. El orden importa -- `cuadrarAvance`
// primero, pintar despues -- porque `pintarLosBinsMontados` lee
// `avanceActual`, y pintar con el avance viejo pintaria lo que ya no es
// cierto.
async function repintarGuia() {
  const hoja = document.getElementById("hoja-orden");
  if (!hoja || !pestanaArmada) return;

  const guia = guiaImportada();
  const guion = (guia && guia.orden) || [];
  const crudo = await leerAvance(proyectoImportado());
  // Contra el guion de AHORA: una palomita de una guia anterior daria un
  // avance falso, y eso es peor que ninguno.
  avanceActual = cuadrarAvance(crudo, guion);

  if (guion.length) await pintarLosBinsMontados(guion);
  dibujarGuia(hoja, guia, avanceActual);
}

function dibujarGuia(hoja, guia, avance) {
  hoja.innerHTML = "";
  const guion = (guia && guia.orden) || [];

  if (!guion.length) {
    // Que no traiga guia NO es un error: es un proyecto que se exporto sin
    // apretar el boton, o de antes de que esto existiera.
    const vacio = document.createElement("p");
    vacio.className = "tenue";
    vacio.textContent =
      "Este proyecto no trae guía de edición. Se arma en Clipify, " +
      "con el botón «Guía de edición», antes de exportar.";
    hoja.appendChild(vacio);
    return;
  }

  hoja.appendChild(dibujarEncabezado(guion, avance));

  const cuerpo = document.createElement("div");
  cuerpo.className = "guia-cuerpo";

  if (guia.recorrido) {
    const parrafo = document.createElement("p");
    parrafo.className = "guia-recorrido";
    parrafo.textContent = guia.recorrido;
    cuerpo.appendChild(parrafo);
  }

  const actual = pasoActual(avance, guion);
  const vistos = {};
  for (let i = 1; i <= guion.length; i++) {
    cuerpo.appendChild(dibujarPaso(guion[i - 1], i, avance, actual, vistos));
    vistos[guion[i - 1].cuarto] = true;
  }
  hoja.appendChild(cuerpo);
}

function dibujarEncabezado(guion, avance) {
  const cab = document.createElement("div");
  cab.className = "guia-cab";

  const actual = pasoActual(avance, guion);
  const chico = document.createElement("div");
  chico.className = "guia-cab-chico";
  chico.textContent = actual === null ? "terminado" : "vas en";
  cab.appendChild(chico);

  const grande = document.createElement("div");
  grande.className = "guia-cab-grande";
  grande.textContent =
    actual === null
      ? "Montaste todo"
      : "Paso " + actual + " · " + guion[actual - 1].cuarto;
  cab.appendChild(grande);

  const cuenta = document.createElement("div");
  cuenta.className = "guia-cab-cuenta";
  // PASOS, no cuartos: con la aerea tres veces, «4 de 9 cuartos» no querria
  // decir nada.
  const texto = avance.length + " de " + guion.length + " pasos montados";
  const proyecto = proyectoImportado();
  cuenta.textContent = proyecto ? texto + " · " + proyecto : texto;
  cab.appendChild(cuenta);

  return cab;
}

function dibujarPaso(renglon, numero, avance, actual, vistos) {
  const montado = estaMontado(avance, numero);

  const fila = document.createElement("div");
  fila.className = "guia-paso";
  if (montado) fila.classList.add("montado");
  if (numero === actual) fila.classList.add("ahora");

  const caja = document.createElement("input");
  caja.type = "checkbox";
  caja.className = "guia-palomita";
  caja.checked = montado;
  caja.addEventListener("change", () => palomear(numero, caja.checked));
  fila.appendChild(caja);

  const n = document.createElement("span");
  n.className = "guia-num";
  n.textContent = numero;
  fila.appendChild(n);

  const nombre = document.createElement("span");
  nombre.className = "guia-cuarto";
  nombre.textContent = renglon.cuarto;
  fila.appendChild(nombre);

  if (vistos[renglon.cuarto]) {
    // SOLO de la segunda vez en adelante: marcar la primera diria que algo
    // pasa con ella, y no pasa nada.
    const otra = document.createElement("span");
    otra.className = "guia-otravez";
    otra.textContent = "otra vez";
    fila.appendChild(otra);
  }

  // Un paso montado esconde su razon: ya no hace falta y le roba espacio al
  // que sigue.
  if (renglon.porque && !montado) {
    const porque = document.createElement("span");
    porque.className = renglon.fuera_del_patron
      ? "guia-porque fuera-del-patron"
      : "guia-porque";
    porque.textContent = " — " + renglon.porque;
    fila.appendChild(porque);
  }

  return fila;
}

async function palomear(paso, montado) {
  const guion = ((guiaImportada() || {}).orden) || [];
  avanceActual = conPaso(avanceActual, guion, paso, montado);
  await guardarAvance(proyectoImportado(), avanceActual);
  // El color se pinta dentro de `repintarGuia`, que ya se llama abajo -- no
  // hay que llamarlo dos veces desde aqui.
  await repintarGuia();
}

// El color de los bins, recalculado del avance. Se hace entero cada vez --
// son siete u ocho carpetas-- en vez de llevar la cuenta de cual cambio:
// dos cuentas del mismo dato es como se desincronizan las cosas.
async function pintarLosBinsMontados(guion) {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  if (!project) return;

  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);
  // NUNCA `resolveBinChain`: esa crea la carpeta si no existe, y aqui solo
  // estamos LEYENDO. Si el proyecto al frente no es el de Clipify -- otro
  // proyecto abierto sin querer -- no hay «02. Clip» que buscar, y crearlo
  // vacio seria escribir sobre un proyecto que no pedimos tocar. Misma regla
  // que ya vive en la pestana de orden sugerido, documentada en el CLAUDE.md
  // del repo.
  const itemsRaiz = (await rootFolder.getItems()) || [];
  const carpetaDeClips = carpetaDelCuarto(
    itemsRaiz, CARPETA_DE_CLIPS, premierepro.FolderItem.cast
  );
  if (!carpetaDeClips) return;

  const montados = cuartosMontados(avanceActual, guion);
  const orden = guion.map((r) => r.cuarto);
  // Cada cuarto UNA vez, aunque el guion lo repita: son ocho carpetas, no
  // once. `indexOf` sobre `orden` sigue dando la primera aparicion, que es
  // el numero que lleva la carpeta.
  const cuartos = orden.filter((c, i) => orden.indexOf(c) === i);

  const items = (await carpetaDeClips.getItems()) || [];
  for (const cuarto of cuartos) {
    // Sin numero: `carpetaDelCuarto` ya lo quita de los dos lados con
    // `esElMismoCuarto`, asi que pasarlo con numero o sin el encuentra la
    // misma carpeta. Buscar por el nombre pelon es lo que de verdad importa
    // -- la carpeta se encuentra tenga el numero que tenga.
    const bin = carpetaDelCuarto(
      items, cuarto, premierepro.FolderItem.cast
    );
    if (bin) pintarBinMontado(project, bin, montados.indexOf(cuarto) !== -1);
  }
}
