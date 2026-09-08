# El LUT por la vía del «Blob»: cerrado, ahora sí con la razón de fondo

*(2026-09-08. Cuatro versiones del spike contra Premiere Pro real, proyecto
`testestest.prproj`. Dos de ellas **tumbaron Premiere**. El spike se borró
después; lo que queda es esto.)*

## Por qué se reabrió

El 2026-08-10 esto se paró porque «Input LUT» resultó ser un menú cuyo valor
es el índice del renglón, y un índice apunta a otro LUT en otra computadora
sin avisar. Ver `RESULTADO-2026-08-10-lut-y-estrella-en-premiere.md`.

El 2026-09-08 Bruno trajo **razón nueva y buena**: un `xmeml` exportado de un
clip suyo con el LUT ya puesto a mano. Adentro se ve que Premiere **sí guarda
la ruta completa** del `.cube`, dos veces:

```xml
<parameterid>1</parameterid><name>Blob</name>
<value>…base64…</value>          ← XML de Lumetri; adentro:
   <shader><name>"LUT"</name>
     <parameters><LUT>"/…/Technical/SONY-SLOG3.cube"</LUT></parameters>
…y al final del mismo XML:
   <embeddedlut><hash>54BE…</hash><filename>/…/SONY-SLOG3.cube</filename>
```

O sea: **el índice del menú no es el dato de verdad**. La hipótesis de agosto
—«el parámetro no acepta rutas»— era correcta sobre «Input LUT» y equivocada
sobre Lumetri en general. Valía la pena volver a preguntar.

## Lo que se comprobó

| Pregunta | Respuesta |
|---|---|
| ¿Existe el parámetro «Blob» por la API? | **Sí.** Es el **parámetro 0** de los 130 de Lumetri, `displayName` = `Blob`. |
| ¿Se puede **leer**? | **No. Leerlo tumba Premiere.** `getValueAtTime(0)` sobre el parámetro 0 mata el proceso — sin excepción que atrapar, sin diálogo: el programa se cae. |
| ¿Se puede **escribir** sin leerlo? | **No.** `createSetValueAction` lo rechaza con `Illegal Parameter type` en las tres formas probadas: texto + `true`, texto solo, y envuelto en `createKeyframe`. |
| ¿Cambia algo que el bloque sea el original o uno modificado? | **No.** Los dos se rechazan igual, y la app no llegó siquiera a esa distinción. |

El bloque escrito venía del `xmeml` de Bruno —18 552 caracteres de base64—, o
sea que **no era un valor inventado**: es literalmente lo que Premiere guarda
para un LUT que funciona. Aun así lo rechaza.

**Conclusión: la vía del blob está cerrada por la API, no por falta de
código.** El dato está donde creíamos; la puerta para tocarlo o no existe o
mata el proceso.

## Lo que Bruno decidió

«No jaló. Mejor sigamos sin eso.» El LUT se sigue poniendo a mano en
Premiere.

Y con los **colores por cámara** (el trabajo del mismo día) le queda
razonable: seleccionar todos los clips amarillos —el dron— y arrastrarles su
preset es un gesto, no un clip por clip. El color no reemplaza al LUT, pero
hace barata la única vía que sí existe.

## Reglas que salen de aquí

1. **No volver a intentar el LUT por la API sin una versión nueva de
   Premiere.** Los dos caminos posibles están medidos: el índice del menú es
   frágil por diseño (agosto) y el blob no se deja tocar (hoy). Un tercero
   tendría que aparecer en la API, no en nuestro código.

2. **Un spike que toca Premiere anota a disco DESPUÉS DE CADA PASO, y anota
   antes de intentar lo peligroso.** La segunda versión de este spike escribía
   su resultado al final; Premiere se cayó y no quedó **ni una línea** de por
   dónde iba — una corrida entera, y cada corrida cuesta reiniciar Premiere.
   La tercera anotaba antes de cada lectura, y su última línea
   (`[voy a leer] param 0: displayName=Blob`) es la que señaló al culpable.
   Sin eso, hoy seguiríamos sin saber qué mató el proceso.

3. **Filtrar por nombre es asumir.** La segunda versión buscaba el efecto con
   `c.matchName.indexOf("Lumetri")` y reportó «con Lumetri colgado: ninguno»
   en un proyecto donde sí lo había — la propiedad no existe en runtime, el
   filtro descartó todo **en silencio** y el spike mintió con cara de dato.
   Es la misma trampa ya documentada al tope de `importClip.js` y en el
   resultado de agosto, cobrada por tercera vez. **Enumera y reporta lo que
   hay; no filtres por lo que crees que se llama.**

4. **Un spike que le cuelga efectos a los clips deja basura.** Este dejó un
   Lumetri vacío en dos clips de `testestest.prproj`. Se avisó en el momento.
   Si se vuelve a hacer algo así, que sea en un proyecto de prueba
   desechable, no en uno con trabajo adentro.
