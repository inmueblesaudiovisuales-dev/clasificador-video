// La llamada a la API, y nada mas.
//
// Chiquito a proposito: no arma el cuerpo y no interpreta la respuesta --las
// dos cosas viven en `ordenSugerido.js`, que se prueba sin red--. Ese corte
// es lo que deja cambiar de proveedor en un renglon, como pidio Bruno:
// DeepSeek habla la misma API que OpenAI, asi que mudarse es esta URL.
//
// OJO CON LA PLATAFORMA: que UXP deje llamar a internet es el riesgo que se
// comprueba ANTES de construir encima (§8 del spec). No le creas a la
// documentacion de Adobe sobre que existe -- en este mismo plugin ya mintio
// tres veces el mismo dia. La prueba en vivo vive en `autocheck-tests.js`.

const DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions";

// Devuelve el texto que contesto el modelo. Cada caso feo tiene su mensaje
// propio y en palabras de Bruno --«la llave no sirve» y no «HTTP 401»--,
// mismo criterio que `importarManifestDesdeArchivo`: ninguno deja el panel en
// un estado ambiguo.
async function pedirOrden(llave, cuerpo) {
  if (!llave) {
    throw new Error("Falta la llave de DeepSeek. Pégala aquí arriba y vuelve a intentar.");
  }

  let respuesta;
  try {
    respuesta = await fetch(DEEPSEEK_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + llave,
      },
      body: JSON.stringify(cuerpo),
    });
  } catch (e) {
    // Aqui cae tanto «no hay internet» como «Premiere no deja salir al
    // plugin». Se dicen juntos porque desde adentro no se distinguen, y el
    // segundo es el riesgo del §8.
    throw new Error(
      "No se pudo llegar a DeepSeek. Revisa tu internet; si sigue igual, puede ser " +
        "que Premiere no esté dejando salir al plugin. (" + e.message + ")"
    );
  }

  if (respuesta.status === 401 || respuesta.status === 403) {
    throw new Error("La llave no sirve o ya no es válida. Pega otra aquí arriba.");
  }
  if (respuesta.status === 402) {
    throw new Error("La cuenta de DeepSeek se quedó sin saldo.");
  }
  if (respuesta.status === 429) {
    throw new Error("DeepSeek va saturado ahorita. Espera un momento y vuelve a intentar.");
  }
  if (!respuesta.ok) {
    throw new Error("DeepSeek contestó con un error (" + respuesta.status + ").");
  }

  let datos;
  try {
    datos = await respuesta.json();
  } catch (e) {
    throw new Error("DeepSeek contestó algo que no se pudo leer.");
  }

  const texto =
    datos && datos.choices && datos.choices[0] && datos.choices[0].message
      ? datos.choices[0].message.content
      : "";

  if (!texto) {
    throw new Error("DeepSeek contestó vacío. Vuelve a intentar.");
  }

  return texto;
}
