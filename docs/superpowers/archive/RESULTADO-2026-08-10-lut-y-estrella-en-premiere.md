# El LUT y la estrella dorada, contestados dentro de Premiere

*(2026-08-10. Cuatro corridas del spike contra Premiere Pro 26 real, proyecto
`test.prproj`, clip `sample-media/clips/20260804_PIB0587.MP4`. El spike se
borró después de esta corrida; lo que queda es esto.)*

## Resumen

| Pregunta | Respuesta |
|---|---|
| ¿La estrella queda dorada en Premiere? | **Sí, confirmado.** Tema cerrado. |
| ¿Se le pueden colgar efectos al master clip sin armar secuencia? | **Sí, confirmado.** |
| ¿Se le puede poner un LUT de entrada dándole la ruta de un `.cube`? | **No.** El parámetro no acepta rutas — ver abajo. |

Bruno decidió parar el LUT aquí: «mejor solo no lo hagamos, no necesito
complicar más esto».

## 1. La estrella dorada: cerrado

`MANGO` **existe** en `premierepro.Constants.ProjectItemColorLabel` y es el
**índice 7**. `applyFlagLabel(project, clip, "destacado")` movió la etiqueta
del clip de 6 (ROSE, forzado antes para que la comparación probara algo) a 7.

La guarda que avisa si la constante no existe se queda: no cuesta nada y otra
versión de Premiere podría no traerla.

## 2. Colgarle efectos al master clip: se puede

- `ClipProjectItem.getComponentChain(Constants.MediaType.VIDEO)` **existe** y
  devuelve la cadena.
- `VideoFilterFactory.createComponent(matchName)` **funciona**, y el
  `matchName` de Lumetri en esta versión es **`AE.ADBE Lumetri`**. También
  responde a `ADBE Lumetri`. Los tres con prefijo `PR.` o con el nombre
  `LumetriColor` devuelven `undefined`.
- `VideoComponentChain.createAppendComponentAction(componente)` dentro de
  `runTransaction` **monta el efecto**: Lumetri Color aparece en Effect
  Controls del master clip, con su «Input LUT» en None. Se vio en pantalla.

**Esto vale más allá del LUT**: cualquier cosa que se quiera colgar por
cámara —una corrección base, un efecto— tiene camino abierto.

## 3. El LUT: por qué no

`Input LUT` **existe** y es el **parámetro 6** de los 130 de Lumetri. Se
encuentra sin problema. Lo que no se puede es escribirle una ruta:

```
createSetValueAction("/ruta/al/lut.cube")        => Illegal Parameter type
createSetValueAction("/ruta/al/lut.cube", true)  => Illegal Parameter type
```

Y el dato que lo explica, leyendo qué tiene guardado ese parámetro:

```
getValueAtTime(0) => { "value": 0 }
```

**Es un número, no un texto.** «Input LUT» es un menú desplegable, y su valor
es el **índice del renglón elegido** dentro de la lista de LUTs que Premiere
ya tiene instalados. No es un campo donde quepa la ruta de un archivo suelto
del disco de Bruno.

## 4. La otra vía, para cuando alguien la retome

No es que esté cerrado del todo — es que sale caro y frágil:

1. **Instalar el `.cube` donde Premiere lo vea**, en la carpeta de LUTs de
   entrada de Lumetri, para que aparezca en ese menú.
2. **Poner el índice del renglón.** Y aquí hay que probar dos cosas que
   quedaron sin comprobar: si `createSetValueAction` acepta un número
   (probable — nunca se le pasó uno, siempre se le pasó texto u objeto), y
   si en realidad espera un `Keyframe`. Esa segunda sospecha tiene base:
   `getStartValue()` devuelve un objeto de clase **`Keyframe`** con
   propiedad `value`, y el parámetro expone `createKeyframe(...)`. O sea
   que el camino más probable es `createSetValueAction(await
   param.createKeyframe(indice), true)`.

**Por qué es frágil aunque funcione:** el índice depende de qué LUTs haya
instalados y en qué orden los liste Premiere. En otra computadora —o en la
misma después de instalar otro LUT— el mismo número apunta a otro LUT. Y ese
es el peor modo de fallo posible para esta app: no avisa, solo se ve mal el
color, igual que enganchar el proxy equivocado.

Si se retoma, la pregunta de diseño no es técnica sino de producto: cómo se
verifica que el renglón número N sigue siendo el LUT que Bruno quería.

## Nota de proceso: por qué costó cuatro corridas

Cada corrida necesitaba reiniciar Premiere, así que la lección tiene valor.
**Tres de las cuatro se fueron en descubrir que la API miente igual en todos
lados:** lo que devuelve la fábrica no tiene métodos (solo `constructor`),
`getParam` hay que esperarlo con `await` aunque la referencia diga que
devuelve el objeto directo, y el nombre del parámetro es `displayName` como
propiedad, no `getDisplayName()`. Es la misma trampa que ya está documentada
al tope de `importClip.js` para `FolderItem`/`ClipProjectItem`.

**La regla que sale de aquí:** en este plugin, antes de llamar a un método
que dice la documentación de Adobe, imprimir
`Object.getOwnPropertyNames(Object.getPrototypeOf(obj))` y ver qué hay de
verdad. Un spike que reporta lo que encontró vale una corrida; uno que
asume, tres.

**La otra trampa, más tonta y más cara:** el arnés de pruebas corría una sola
vez, al cargarse el panel — y el panel carga junto con Premiere, **antes** de
que haya proyecto abierto. Reportaba «no hay proyecto abierto» cuando sí lo
había. Se resolvió con un botón para correrlo a mano; el botón se fue con el
spike, pero si el arnés se vuelve a encender hay que volver a ponerlo.

## Cómo quedó el plugin

Se devolvió a su estado funcional: sin `spike-lut.js`, sin el botón de
correr pruebas y con `AUTOCHECK_ACTIVO = false`.

La copia instalada en
`~/Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1.0.0/`
quedó **idéntica al repo**, que es más de lo que estaba antes de esta sesión:
la que Bruno tenía instalada era de agosto y **no traía el soporte de la
estrella** (`destacado → MANGO`), así que hasta hoy sus clips destacados
llegaban a Premiere sin etiqueta. Ahora sí, y comprobado en vivo.

Quedaron en `test.prproj` unos bins de prueba (`SpikeLUT`, `PruebaTask4`) y
un Lumetri colgado del clip 0587. Es un proyecto de prueba; se borran solos
al borrarlo.

## Nota sobre cómo se instaló

El camino del `README.md` del plugin —empaquetar `.ccx` con el CLI de UXP e
instalarlo con UPIA— **no se pudo usar**: el CLI vivía en `/tmp`, que macOS
limpia, y al reinstalarlo su biblioteca nativa no trae compilado para Node 24
(`No native build was found for platform=darwin arch=x64 ... abi=137`). Es un
problema del CLI de Adobe, no del plugin.

Se copiaron los archivos encima de la instalación existente. **Ojo con la
distinción**, porque es fácil leer esto como que el README estaba
equivocado: copiar a mano ahí sigue **sin** funcionar para instalar por
primera vez —Premiere no registra un plugin que aparece solo en esa
carpeta—; aquí ya estaba registrado por UPIA desde agosto y lo único que
cambió son los archivos que lee al cargar. **Para repartir el plugin a otra
computadora sigue haciendo falta resolver lo del `.ccx`.**

Y un detalle operativo que costó dos vueltas: **Premiere no recoge archivos
nuevos con Premiere abierto.** Cerrar y abrir el panel no basta — hay que
cerrar Premiere entero.
