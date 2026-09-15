// La pestana «Orden sugerido»: lo que Bruno ve y toca.
//
// Solo dibuja y conecta. Todo lo que decide algo vive en `ordenSugerido.js`
// (armar la pregunta, leer la respuesta, revisarla), y todo lo que habla con
// el mundo en `deepseek.js`, `cuartosDelProyecto.js` y `llave.js`. Si algun
// dia hay que arreglar POR QUE una lista salio mal, no se busca aqui.
//
// LA PESTANA NO ESCRIBE NADA EN EL PROYECTO. Ni una carpeta, ni un clip, ni
// el timeline: solo lee los nombres de los bins. Es de lectura entera, y esa
// es la razon por la que puede vivir dentro del mismo plugin que si escribe
// sin dar miedo.
//
// Spec: docs/superpowers/specs/2026-09-14-orden-sugerido-de-cuartos-design.md

const PREGUNTAS = [
  {
    id: "propiedad",
    texto: "¿Qué tipo de propiedad es?",
    opciones: ["Casa", "Departamento", "Terreno", "Local"],
    varios: false,
  },
  {
    id: "para",
    texto: "¿Para quién es el video?",
    opciones: ["Redes", "Portafolio", "Cliente directo", "Portal inmobiliario"],
    varios: true,
  },
  {
    id: "lucir",
    texto: "¿Qué hay que lucir?",
    opciones: [],
    varios: false,
  },
];

// Todo lo que la pestana sabe ahorita. Se arma una vez y se queda: volver a
// la pestana no deberia perder la plancha que ya ibas ganando.
const estadoOrden = {
  armada: false,
  cuartos: [],
  respuestas: {},
  conversacion: [],
  ocupada: false,
};

async function abrirPestanaOrden(hoja) {
  if (estadoOrden.armada) return;
  estadoOrden.armada = true;

  hoja.innerHTML = "";
  hoja.appendChild(seccionLlave());
  hoja.appendChild(seccionCuartos());
  hoja.appendChild(seccionPreguntas());
  hoja.appendChild(seccionResultado());

  await refrescarLlave();
  await refrescarCuartos();
}

// --- La llave ------------------------------------------------------

function seccionLlave() {
  const caja = document.createElement("div");
  caja.id = "orden-llave";
  caja.className = "llave";
  return caja;
}

async function refrescarLlave() {
  const caja = document.getElementById("orden-llave");
  const llave = await leerLlave();
  caja.innerHTML = "";

  if (llave) {
    const texto = document.createElement("span");
    texto.textContent = "Llave de DeepSeek: " + llaveTapada(llave) + " ";
    const cambiar = document.createElement("button");
    cambiar.className = "discreto";
    cambiar.textContent = "cambiar";
    cambiar.addEventListener("click", async () => {
      await borrarLlave();
      await refrescarLlave();
    });
    caja.appendChild(texto);
    caja.appendChild(cambiar);
    return;
  }

  const etiqueta = document.createElement("div");
  etiqueta.className = "tenue";
  etiqueta.textContent = "Pega tu llave de DeepSeek (se queda guardada, se pide una sola vez):";
  const campo = document.createElement("input");
  campo.type = "text";
  campo.placeholder = "sk-...";
  const guardar = document.createElement("button");
  guardar.textContent = "Guardar";
  guardar.style.marginTop = "5px";
  guardar.addEventListener("click", async () => {
    if (!campo.value.trim()) return;
    await guardarLlave(campo.value);
    await refrescarLlave();
  });

  caja.appendChild(etiqueta);
  caja.appendChild(campo);
  caja.appendChild(guardar);
}

// --- Los cuartos ---------------------------------------------------

function seccionCuartos() {
  const caja = document.createElement("div");
  caja.id = "orden-cuartos";
  caja.style.marginBottom = "12px";
  return caja;
}

async function refrescarCuartos() {
  const caja = document.getElementById("orden-cuartos");
  caja.innerHTML = "";

  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  if (!project) {
    caja.textContent = "No hay ningún proyecto abierto en Premiere.";
    return;
  }

  const lectura = await cuartosDeLosBins(project);
  estadoOrden.cuartos = lectura.cuartos;

  // El texto lo decide `mensajeDeCuartos` y no este archivo: que «no existe»
  // y «esta vacia» se digan distinto es una regla, y las reglas viven donde
  // se pueden comprobar sin abrir Premiere.
  const dicho = mensajeDeCuartos(lectura);

  const texto = document.createElement("div");
  texto.className = "tenue";
  texto.textContent = dicho.texto;
  caja.appendChild(texto);

  if (!dicho.pedirlosAMano) return;

  const campo = document.createElement("textarea");
  campo.rows = 6;
  campo.id = "orden-cuartos-mano";
  campo.addEventListener("input", () => {
    estadoOrden.cuartos = cuartosTecleados(campo.value);
  });
  caja.appendChild(campo);
}

// --- Las preguntas -------------------------------------------------

function seccionPreguntas() {
  const caja = document.createElement("div");
  caja.style.marginBottom = "12px";

  for (const pregunta of PREGUNTAS) {
    const bloque = document.createElement("div");
    bloque.className = "pregunta";

    const etiqueta = document.createElement("label");
    etiqueta.textContent = pregunta.texto;
    bloque.appendChild(etiqueta);

    for (const opcion of pregunta.opciones) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = opcion;
      chip.addEventListener("click", () => {
        prenderChip(pregunta, chip, opcion, bloque);
      });
      bloque.appendChild(chip);
    }

    // La caja de texto libre esta SIEMPRE, con chips o sin ellos: es la
    // valvula para cuando ninguna respuesta de las de a un toque sirve.
    const libre = document.createElement("input");
    libre.type = "text";
    libre.placeholder = pregunta.opciones.length ? "…o escríbelo" : "Escríbelo aquí";
    libre.style.marginTop = "4px";
    libre.addEventListener("input", () => {
      if (pregunta.varios) {
        const chips = prendidos(bloque);
        estadoOrden.respuestas[pregunta.id] = libre.value.trim()
          ? chips.concat([libre.value.trim()])
          : chips;
      } else {
        estadoOrden.respuestas[pregunta.id] = libre.value.trim() || prendidos(bloque)[0] || "";
      }
    });
    bloque.appendChild(libre);

    caja.appendChild(bloque);
  }

  // Activo desde el primer momento: las tres preguntas se pueden dejar en
  // blanco. Hacerlo pasar por un interrogatorio para llegar a lo que vino a
  // ver es el camino mas corto a que no use la pestana.
  const dame = document.createElement("button");
  dame.id = "orden-dame";
  dame.className = "principal";
  dame.textContent = "Dame la lista";
  dame.addEventListener("click", () => pedirLaLista());
  caja.appendChild(dame);

  return caja;
}

function prendidos(bloque) {
  return Array.from(bloque.querySelectorAll(".chip.prendido")).map((c) => c.textContent);
}

function prenderChip(pregunta, chip, opcion, bloque) {
  if (pregunta.varios) {
    chip.classList.toggle("prendido");
    estadoOrden.respuestas[pregunta.id] = prendidos(bloque);
    return;
  }
  const yaEstaba = chip.classList.contains("prendido");
  for (const otro of bloque.querySelectorAll(".chip")) otro.classList.remove("prendido");
  if (!yaEstaba) chip.classList.add("prendido");
  estadoOrden.respuestas[pregunta.id] = yaEstaba ? "" : opcion;
}

// --- El resultado --------------------------------------------------

function seccionResultado() {
  const caja = document.createElement("div");
  caja.id = "orden-resultado";
  return caja;
}

async function pedirLaLista(mensajeNuevo) {
  if (estadoOrden.ocupada) return;

  const caja = document.getElementById("orden-resultado");

  if (!estadoOrden.cuartos.length) {
    caja.innerHTML = "";
    caja.appendChild(avisoDe("Primero necesito saber qué cuartos hay."));
    return;
  }

  if (mensajeNuevo) {
    estadoOrden.conversacion.push({ role: "user", content: mensajeNuevo });
  }

  estadoOrden.ocupada = true;
  document.getElementById("orden-dame").disabled = true;
  caja.innerHTML = "";
  caja.appendChild(tenue("Pensando…"));

  try {
    const llave = await leerLlave();
    const cuerpo = cuerpoDelRequest(
      estadoOrden.cuartos,
      estadoOrden.respuestas,
      estadoOrden.conversacion
    );
    const texto = await pedirOrden(llave, cuerpo);

    // Se guarda lo que contesto para que la siguiente vuelta tenga memoria.
    estadoOrden.conversacion.push({ role: "assistant", content: texto });

    const leida = leerRespuesta(texto);
    caja.innerHTML = "";

    if (!leida.ok) {
      caja.appendChild(avisoDe(leida.error));
      const reintentar = document.createElement("button");
      reintentar.textContent = "Volver a intentar";
      reintentar.addEventListener("click", () => {
        // Se le quita la respuesta mala a la conversacion: dejarsela seria
        // pedirle que siga a partir de su propio error.
        estadoOrden.conversacion.pop();
        pedirLaLista();
      });
      caja.appendChild(reintentar);
      return;
    }

    dibujarLaGuia(caja, leida.lista, revisarLista(leida.lista, estadoOrden.cuartos));
  } catch (e) {
    caja.innerHTML = "";
    caja.appendChild(avisoDe(e.message));
  } finally {
    estadoOrden.ocupada = false;
    document.getElementById("orden-dame").disabled = false;
  }
}

function dibujarLaGuia(caja, lista, revision) {
  // Los avisos van ARRIBA de la lista y no abajo: si van abajo, se leen
  // despues de haberle creido a la lista.
  // Todo lo que sale del modelo va dentro de `.guia`, que es lo que le pone
  // la linea de arriba: separa lo que TU contestaste de lo que EL contesto.
  const guia = document.createElement("div");
  guia.className = "guia";
  caja.appendChild(guia);
  caja = guia;

  for (const aviso of avisosDeLaRevision(revision)) {
    caja.appendChild(avisoDe(aviso));
  }

  for (let i = 0; i < lista.length; i++) {
    const renglon = document.createElement("div");
    renglon.className = "renglon-cuarto";
    if (revision.inventados.indexOf(lista[i].cuarto) !== -1) {
      renglon.className += " inventado";
    }

    const nombre = document.createElement("span");
    nombre.className = "nombre";
    nombre.textContent = i + 1 + ". " + lista[i].cuarto;
    renglon.appendChild(nombre);

    if (lista[i].porque) {
      const porque = document.createElement("span");
      porque.className = "porque";
      porque.textContent = " — " + lista[i].porque;
      renglon.appendChild(porque);
    }

    caja.appendChild(renglon);
  }

  const copiar = document.createElement("button");
  copiar.textContent = "Copiar";
  copiar.style.marginTop = "12px";
  copiar.addEventListener("click", () => copiarLaGuia(lista, revision, caja));
  caja.appendChild(copiar);

  // Seguirle hablando: cada mensaje rehace la lista COMPLETA, no la parcha.
  const seguir = document.createElement("input");
  seguir.type = "text";
  seguir.placeholder = "Dile que cambiar: «la alberca al final»…";
  seguir.style.marginTop = "8px";
  seguir.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && seguir.value.trim()) {
      pedirLaLista(seguir.value.trim());
    }
  });
  caja.appendChild(seguir);
}

async function copiarLaGuia(lista, revision, caja) {
  const texto = guiaComoTexto(lista, revision);
  try {
    await navigator.clipboard.writeText(texto);
    caja.appendChild(tenue("Copiado."));
  } catch (e) {
    // Si el portapapeles no esta, se ensena para copiar a mano en vez de
    // fallar callado. Un boton que no hace nada y no lo dice es peor que no
    // tener boton.
    const area = document.createElement("textarea");
    area.rows = 8;
    area.value = texto;
    caja.appendChild(tenue("No pude usar el portapapeles. Cópialo de aquí:"));
    caja.appendChild(area);
  }
}

function avisoDe(texto) {
  const div = document.createElement("div");
  div.className = "aviso";
  div.textContent = texto;
  return div;
}

function tenue(texto) {
  const div = document.createElement("div");
  div.className = "tenue";
  div.textContent = texto;
  return div;
}
