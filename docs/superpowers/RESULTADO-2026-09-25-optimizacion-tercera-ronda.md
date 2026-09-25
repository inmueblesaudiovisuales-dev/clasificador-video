# Tercera ronda de optimización de Clipify

Fecha: 2026-09-25. Autor: GPT-6 (Codex).
Base: `master`, `c0f3449841e6ca323c13c62237ec56838dfc2133`.
Alcance: investigación, inventario y experimentos externos. **Sin implementación en la app.**

## Resultado de esta ronda

Hay dos oportunidades nuevas en el empaquetado y dos costos concretos dentro de la exportación que no estaban desglosados antes. Además, se midió la hipótesis ya conocida de exportar fuera del hilo de la interfaz; se presenta como profundización de la idea 4 anterior, no como descubrimiento nuevo.

| Candidata | Recurso y evidencia de esta ronda | Impacto / confianza | Prioridad |
|---|---|---|---|
| **A. Una sola biblioteca de libmpv y un alias** | Dos archivos de unos 4.46 MB con el mismo UUID, código ejecutable e identidad de carga | Bajo en disco instalado; alta confianza en la duplicación, media en el paquete corregido hasta probarlo | Antes de la siguiente entrega del paquete |
| **B. Retirar símbolos locales de binarios seleccionados** | En copias de cuatro módulos Qt y una biblioteca, `strip -x` quitó 8,010,912 bytes | Bajo en disco; alta confianza en los bytes, baja en compatibilidad hasta ejecutar un paquete nuevo | Opcional; no aplicar masivamente |
| **C. Clonar el grafo de Premiere sin convertir cada objeto a texto ni recorrer toda la salida repetidamente** | El costo sin ffprobe crece de 0.81 s con 200 entradas y proxies a 3.71 s con 500; copiar 200 veces un cierre real bajó de 0.105 a 0.005 s en una microprueba | Medio en CPU/espera de exportaciones grandes; confianza media en la mejora integral | Después de resolver la espera de exportación ya identificada |
| **D. Escribir el XML de Premiere por partes al compresor** | Pico adicional de asignaciones Python de 42.19–49.05 MB a 3.31 MB, conservando exactamente el XML | Medio en pico de RAM al exportar; confianza alta en el experimento y media en la app completa | Candidata acotada para la siguiente validación |

Los ahorros de disco de A/B no significan menos RAM ni menos CPU durante reproducción. Los números de C/D tampoco explican el consumo en reposo. **No se suman estos resultados para prometer una mejora total.** MB significa un millón de bytes en este documento.

## Alcance y control de novedades

Se leyeron completos, antes de inspeccionar el producto, los resultados de [miniaturas](RESULTADO-2026-09-25-miniaturas-vs-premiere.md) y de [optimización general](RESULTADO-2026-09-25-optimizacion-general.md). También se revisaron `CLAUDE.md`, `CONTEXTO-Y-METAS.md`, la investigación de RAM/CPU del 13 de septiembre y el código actual. El documento general ya estaba sin seguimiento en Git al empezar; no se editó ni se incluyó en ningún commit.

Esta fue la lista de exclusión de las 24 ideas:

| Ideas anteriores | Tratamiento en esta ronda |
|---|---|
| 1: decodificación de proxies por hardware | No reinvestigada. Los proxies temporales se generaron con el comando actual, sin agregar flags |
| 2: autoguardado por cambios reales / pesos | Excluida |
| 3: compartir metadata de media | Se inyectaron resultados ya obtenidos únicamente como control experimental para aislar XML; no se propone otro catálogo |
| 4: exportación asíncrona | **Profundizada con exportaciones reales, latido de Qt y comparación en un trabajador** |
| 5: importación asíncrona | No reinvestigada |
| 6–10: construcción de hoja, cache en UI, índices de bins/directorios, actualizaciones puntuales y virtualización | Excluidas. Los índices de C son referencias entre objetos del XML de Premiere; no índices de clips/bins ni inventarios de archivos |
| 11–13: cargas intermedias, audio del visor y presupuesto de trabajos | Excluidas |
| 14: arranque, recientes, relink e imports diferidos | Excluida. A/B cambian los bytes distribuidos, no cuándo se importa Python |
| 15–18: dos proxies, GOP, extracción integrada y backend/sesión persistente | Excluidas |
| 19–20: manifiesto de cache y compartir preview original/proxy | Excluidas. A no deduplica imágenes: identifica dos copias de una biblioteca dentro del `.app` |
| 21: JSON compacto / journal de `.cvproj` | Excluida. D conserva el XML completo de `.prproj`, su contenido y su compresión; evita representaciones intermedias en RAM |
| 22–24: ubicación temporal de proxies, anticipación y cierre/fallas | Excluidas |

Tampoco se repitieron las pruebas descartadas de miniaturas ni se tocó el motor del visor. C/D pertenecen a la profundización de exportación autorizada por el encargo; no se cuentan como otras dos versiones de «poner la exportación en segundo plano». Actúan sobre trabajo y memoria que un trabajador seguiría gastando.

## Entorno y método

- Mac15,10, Apple M3 Max, 38,654,705,664 bytes de RAM; macOS 27.0 arm64.
- Python 3.14.6, PySide6 6.11.1, PyInstaller instalado 6.22.0, FFmpeg/ffprobe 8.1.2, mpv 0.41.0.
- Código del repo para exportación. Para el inventario se inspeccionó el `.app` existente en `empaque/dist/Clipify.app`, versión 3.0.0 según su `Info.plist`. No se reconstruyó; no se presume que sea idéntico al HEAD en cada módulo.
- Material: `20260804_PIB0587.MP4`, `20260804_PIB0588.MP4` y `20260804_PIB0589.MP4`, de `sample-media/clips/`. Pesos: 67,253,836 / 67,255,308 / 134,365,644 bytes. Duraciones 2.002 / 4.004 / 6.006 s, HEVC FX30. Se crearon tres proxies temporales con `proxy_gen.comando`, uno a la vez, conservando marca, dimensiones y audio.
- Manifiestos sintéticos de 30, 200 y 500 entradas que repiten esos tres archivos y distribuyen las entradas entre diez cuartos. No son 500 archivos distintos, ni una sesión real de clasificación, ni material mixto Sony/dron/Pocket.
- Archivos locales, cache del sistema operativo caliente, sin purgarlo ni aislar por completo la máquina. Las transcodificaciones terminaron antes de los benchmarks. No se ejecutaron dos benchmarks pesados a la vez.
- Reloj con `perf_counter`; CPU del proceso y sus hijos por separado. `tracemalloc` sólo donde se identifica. El latido de Qt usa un `QCoreApplication` con temporizador de 10 ms: no hay ventana Cocoa, mpv reproduciendo ni interacción humana en este arnés.
- Temporales y scripts fuera del repo, en `work/tercera-ronda/` de la sesión de Codex. No se modificaron los originales, las preferencias ni proyectos del usuario.

Son mediciones exploratorias, no pruebas de compatibilidad con Premiere. Ningún resultado de tamaño o tiempo se presenta como medición de energía, temperatura, swap o batería.

## Profundización medida: exportar sin detener el hilo principal

El camino actual es `ui/main_window.py:5646–5659`: prepara el manifest y llama directamente a `generar_prproj`. Se ejecutó ese generador completo desde un callback del hilo principal del arnés, conservando los sondeos reales y secuenciales. Los primeros tres pares dieron:

| 200 entradas | Reloj, tres corridas (s) | Mayor intervalo entre latidos, tres corridas (s) | Sondeos por corrida |
|---|---|---|---|
| Sin proxies | 6.739 / 7.047 / 6.980 | 6.748 / 7.056 / 6.989 | 200 |
| Con proxies | 15.855 / 16.054 / 16.053 | 15.864 / 16.053 / 16.062 | 400 |

En esta primera serie, el reloj se tomó desde el agendamiento y se descontaron los 30 ms programados antes de iniciar; puede incluir unos milisegundos de variación del temporizador. La segunda serie de abajo cronometra exactamente la llamada al generador.

Medianas de la primera serie:

| Trabajo | Sin proxies | Con proxies |
|---|---:|---:|
| Sondeos, reloj acumulado | 6.054 s | 14.553 s |
| CPU del proceso Python | 1.293 s | 2.221 s |
| CPU de hijos | 5.449 s | 13.361 s |
| Clonación de cierres XML, reloj | 0.455 s | 0.522 s |
| Serialización y escritura final | 0.102 s | 0.118 s |

Los tiempos de fases se midieron con envolturas; las medianas de columnas no se deben sumar para reconstruir una corrida. El reloj de los sondeos incluye esperar procesos, mientras los segundos de CPU de hijos miden otra cosa.

### Comparación con un trabajador, sin paralelizar sondeos

En un segundo arnés se alternó la misma exportación de 200 entradas con proxies entre el hilo principal y un único `ThreadPoolExecutor(max_workers=1)`. No se cambió el generador ni se compartió metadata: siguieron siendo 400 ffprobe reales por exportación. El manifest se preparó antes y no se editó durante la prueba.

| Ejecución | Reloj, tres corridas (s) | Máximo intervalo entre latidos, tres corridas |
|---|---|---|
| Hilo principal | 15.893 / 16.260 / 16.222 | 15.895 s / 16.269 s / 16.231 s |
| Un trabajador | 15.648 / 16.298 / 16.352 | 41.65 ms / 37.63 ms / 35.04 ms |

Las medianas de CPU propia fueron 2.468 s en el hilo principal y 2.748 s en el trabajador. El conteo incluye el arnés y la comprobación final de XML; no es una reducción de CPU atribuible a la asincronía.

**Interpretación:** esta prueba determina si Qt puede seguir atendiendo eventos durante la exportación. No mide que clasificar siga siendo correcto mientras cambias el proyecto, ni demuestra menor CPU. La mediana/p95 de los pocos latidos de una corrida bloqueada escondería el problema; por eso la comparación usa el intervalo **máximo**, que sí captura el hueco completo.

**Impacto / confianza:** alto para respuesta durante esta operación; confianza alta en el bloqueo y en la mejora del latido dentro del arnés, media en la experiencia de la ventana completa. No hay promesa de acortar la exportación. Costo medio; riesgo de mezclar revisiones si el manifest no queda congelado.

**Antes de implementar la idea 4 pendiente:** repetir con 200/500 archivos distintos, una ventana real y reproducción; medir tecla→pintado y primer cuadro, memoria y máximo intervalo entre eventos. Verificar ediciones durante la exportación, selección de ruta, mensajes en UI, errores y cierre. Abrir en Premiere y comprobar referencias, proxies, audio, rotación, LUTs y las cinco secuencias. El arnés comprobó XML legible y 200 objetos `Media` de proxy en cada resultado de esta segunda serie; no sustituye esa revisión.

## A. Distribuir una sola libmpv y conservar el segundo nombre como alias

**Evidencia nueva.** El inventario del `.app`, sin seguir symlinks ni contar sus destinos dos veces, encontró 292 archivos regulares: 181,573,248 bytes lógicos y 182,235,136 bytes asignados según `st_blocks`. Eso equivale aproximadamente a los 174 MiB que reporta `du`; no es el peso del DMG.

Hay dos archivos regulares distintos dentro de `Contents/Frameworks`:

| Archivo | Bytes | Inode |
|---|---:|---:|
| `libmpv.2.dylib` | 4,464,912 | 60044092 |
| `libmpv.dylib` | 4,464,944 | 60044215 |

Ambos reportan `@rpath/libmpv.2.dylib` como identidad de carga y UUID `687401F1-C6EA-3BBA-8374-81EA35E1F137`. El SHA-256 de su sección ejecutable `__text` coincide: `acb6dc3abb24cefde70be090b18804b2a43b9e51f42fc01403ac7febb528486d`. **Los archivos completos no son idénticos byte por byte**; tienen tamaños diferentes. La evidencia identifica la misma biblioteca empaquetada bajo dos nombres, no prueba que todo Mach-O con igual UUID pueda deduplicarse sin revisar rutas y firma.

`empaque/clipify.spec:39–53` incorpora semillas resueltas y dependencias con sus nombres; el inventario de PyInstaller `Analysis-00.toc` contiene tanto la ruta de Homebrew `libmpv.dylib` como `libmpv.2.dylib`. La distribución sí admite aliases: [PyInstaller documenta el uso de symlinks en paquetes POSIX/macOS](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#requirements-imposed-by-symbolic-links-in-frozen-application).

**Propuesta concreta:** normalizar la identidad física en la receta y conservar ambos nombres mediante un archivo más un symlink relativo, antes de la firma final. No borrar un nombre que `python-mpv` pueda buscar y no deduplicar ciegamente sólo por basename. Esto conserva el mismo motor, codecs y API de render.

**Impacto / confianza:** bajo y acotado a disco/transferencia. Hay aproximadamente 4.46 MB lógicos candidatos a salir del `.app`; no se produjo un paquete corregido ni se midió el ahorro del DMG. Confianza alta en la duplicación; media en resolverla sin regresión. Costo bajo/medio, riesgo medio de carga dinámica o firma. No se infiere ahorro de 4.46 MB de RAM: no se midió si ambas copias se mapean.

**Qué medir antes de tocar la receta:** construir una copia de la distribución con el alias; confirmar `otool -L/-D`, carga de `python-mpv`, firma, reapertura del DMG y preservación del symlink. Con PATH sin Homebrew, probar reproducción, miniaturas, ffprobe y generación de proxy. Medir bytes del `.app` y del DMG por separado. Probar en otra Mac sigue siendo necesario; esta sesión no lo hizo.

## B. Quitar símbolos locales sólo donde la prueba lo justifique

La receta usa `strip=False`. Eso no basta para recomendar cambiarlo a `True`: se revisó el PyInstaller 6.22.0 instalado y en macOS invoca `strip -S`, una limpieza conservadora de símbolos de depuración. Su propio código evita el comportamiento de strip por defecto porque puede romper bibliotecas.

Se copiaron cinco binarios fuera del paquete. En cada copia se ejecutaron por separado `/usr/bin/strip -S` y `/usr/bin/strip -x`; se midió el archivo antes/después. Todos terminaron con código 0. Los originales distribuidos no se tocaron.

| Binario | Actual, bytes | Después de `-S` | Después de `-x` |
|---|---:|---:|---:|
| `QtOpenGL.abi3.so` | 10,530,128 | 10,530,144 | 8,725,072 |
| `QtCore.abi3.so` | 5,860,464 | 5,850,496 | 4,337,008 |
| `QtGui.abi3.so` | 6,702,192 | 6,702,192 | 5,006,832 |
| `QtWidgets.abi3.so` | 9,055,168 | 9,055,168 | 6,585,232 |
| `libmpv.2.dylib` | 4,464,912 | 4,464,800 | 3,947,808 |

`-S` ahorró sólo 10,064 bytes netos en este conjunto: **activar `strip=True` queda descartado como optimización relevante con esta evidencia**. El aumento de 16 bytes en un archivo es salida real de la herramienta, no un error de transcripción.

`-x` retiró 8,010,912 bytes en esos cinco archivos. Es una candidata distinta: quitar símbolos locales seleccionados durante el build, conservando el artefacto original para diagnóstico y firmando después. No se recomienda pasar `strip` sin opciones a todo el árbol ni retirar bibliotecas requeridas por sus dependencias.

**Impacto / confianza:** bajo en instalación; posible ahorro del orden observado, pendiente del firmado/empaquetado final. Alta confianza en el tamaño de las copias, baja en compatibilidad porque **no se ejecutaron los binarios alterados ni se armó una app con ellos**. Costo medio, riesgo medio/alto por carga dinámica y diagnósticos. Sin evidencia de mejora de arranque, RSS o consumo durante uso.

**Qué medir antes:** primero A, después un build experimental con selección explícita de archivos, firma y validación de carga/símbolos exportados. Probar los diálogos y acciones reales de Qt, render GL, reproducción y cierre repetido, también fuera de esta Mac. Registrar DMG, tamaño instalado, arranque en frío/caliente y calidad de un reporte de crash. Si la ganancia final no justifica mantener esa excepción de empaquetado, descartarla. A y B no se deben sumar usando el tamaño original de una biblioteca que B ya achicó.

## C. Evitar reconstruir y serializar repetidamente el grafo de Premiere

Esto profundiza el costo de XML mencionado en la idea 4. La causa concreta no se había identificado: `prproj_xml.py:71–76` reconstruye un índice de **todos** los objetos de raíz para cada clonación; la raíz crece conforme se agregan clips. Además, `clonar_clip` busca su arquetipo en esa raíz creciente, `adjuntar_proxy` busca fuentes con recorridos y `generar_prproj` vuelve a localizar el item clonado. Copiar un objeto usa `ET.fromstring(ET.tostring(...))` (`prproj_xml.py:95` y `prproj_generador.py:208`).

### Separación del costo sin ffprobe

Se sondearon los tres originales y sus tres proxies una vez. Después se pasaron esos diccionarios por el parámetro `probe` ya existente, sólo en el arnés. El resto del generador, las consultas de existencia y la escritura a disco se conservaron. Tres corridas por caso:

| Entradas | Sin proxies, reloj (s) | Con proxies, reloj (s) | Mediana con proxies |
|---|---|---|---:|
| 30 | 0.134 / 0.137 / 0.138 | 0.152 / 0.156 / 0.163 | 0.156 s |
| 200 | 0.580 / 0.559 / 0.579 | 0.813 / 0.822 / 0.804 | 0.813 s |
| 500 | 2.375 / 2.406 / 2.464 | 3.593 / 3.890 / 3.713 | 3.713 s |

Con 500 entradas y proxies, la mediana de CPU propia fue 3.698 s; la de clonación de cierres, 1.723 s. **Aunque ffprobe no costara nada, todavía habría trabajo suficiente para detener perceptiblemente la interfaz.** No se presenta el control como implementación del cache anterior ni se promete que un catálogo real consiga estos tiempos.

Una corrida adicional con cProfile, excluida de las tablas por su sobrecosto, registró 524 llamadas a `clonar_por_cierre`, 14,330 a `ET.tostring` y 10,175,531 a `Element.get`. El total instrumentado fue 6.355 s; no debe compararse directamente con los 3.713 s sin profiler. El patrón del código y la curva medida justifican investigar los recorridos crecientes; no cuantifican por sí solos cuánto ahorraría un índice nuevo.

### Microprueba de copia sin texto intermedio

Se clonó una vez el arquetipo Sony real y se tomaron sus 23 objetos nuevos. En tres repeticiones alternadas, se copiaron los 23 objetos 200 veces:

| Mecanismo | Reloj, tres corridas |
|---|---|
| `ET.fromstring(ET.tostring(nodo))` | 106.01 / 104.66 / 104.61 ms |
| `copy.deepcopy(nodo)` | 5.31 / 5.15 / 5.44 ms |

Se comprobó que las copias fueran objetos distintos y que `ET.tostring` produjera los mismos bytes para cada par. La diferencia es de unos **100 ms en esta microprueba**, no de segundos para toda la exportación. No incluye remapear IDs ni validar referencias de una exportación completa. [Python documenta la copia profunda y sus diferencias frente a la superficial](https://docs.python.org/3.14/library/copy.html).

**Propuesta:** tener un índice de referencias del XML actualizado al agregar objetos y referencias directas a los arquetipos/items ya resueltos; clonar subárboles sin ir a texto y de regreso. Hacer ambas partes separadamente para atribuir ganancias. El índice es temporal de una exportación; no es un nuevo cache persistente. Debe conservar las fronteras que comparten cadenas de efectos, y distinguir estrictamente `ObjectID/ObjectRef` de `ObjectUID/ObjectURef`.

**Impacto / confianza:** medio en CPU y espera al crecer el proyecto; bajo/modesto para el cambio de copia aislado en 200 clips. Confianza alta en el trabajo repetido, media en mejora neta del generador. Costo medio, riesgo alto por el grafo de referencias de Premiere. No se implementó ni se midió el generador completo con índices nuevos.

**Qué medir antes:** A/B con 200/500/2,000 entradas y luego proyectos reales con varias cámaras, audio, unidades, LUTs y proxies ausentes. Igualar los UUID sólo en el arnés para comparar estructuralmente el XML, verificar independencia de clones, referencias resueltas y orden, medir CPU, máxima pausa de Qt y RSS. No aceptar una reducción de tiempo si cambia identidad de medios, color, orientación, secuencias o relink. Abrir los resultados en Premiere.

## D. Evitar varias representaciones completas del XML en RAM al escribir

`escribir_prproj` arma una cadena Unicode con todo el árbol, concatena la cabecera y la convierte a UTF-8 antes de entregarla a gzip. La salida es pequeña en disco, pero durante la escritura pueden convivir representaciones grandes. Esta idea conserva el árbol y **sólo cambia cómo se serializa**; no elimina datos ni introduce otro formato de proyecto.

Se tomó el resultado de 500 entradas con proxies: **8,438,370 bytes de XML descomprimido**. SHA-256: `6824390acaa76f44a0aa2cb077f06964ad48846da6e0708f889f3a1e1333166b`. Con el árbol ya en memoria se comparó el escritor actual contra este experimento externo:

```python
with gzip.open(destino_temporal, "wb", compresslevel=9) as archivo:
    archivo.write(b'<?xml version="1.0" encoding="UTF-8" ?>\n')
    ET.ElementTree(raiz).write(
        archivo, encoding="utf-8", xml_declaration=False)
```

`ElementTree.write` permite escribir a un archivo binario con codificación explícita; se conserva la cabecera que usa Clipify. [Documentación de ElementTree](https://docs.python.org/3.14/library/xml.etree.elementtree.html#xml.etree.ElementTree.ElementTree.write).

Se inició `tracemalloc` **después** de leer/construir el árbol. Tres corridas alternadas:

| Escritor | Pico adicional de asignaciones Python, bytes |
|---|---|
| Actual | 49,052,381 / 42,191,716 / 42,191,716 |
| Por partes | 3,306,004 / 3,305,612 / 3,305,612 |

La reducción de las medianas es **38,886,104 bytes**. Es memoria temporal de Python durante serialización, no la RAM total de la app, no el árbol XML y no memoria gráfica. No se midió RSS ni huella física; no se promete que macOS devuelva esa cantidad al terminar.

En todas las corridas el archivo se descomprimió y comparó **byte por byte con el XML de entrada**, incluyendo los caracteres UTF-8. Esta comprobación es más fuerte que sólo comparar tamaño; sigue pendiente abrirlo en Premiere.

Se repitió la escritura **sin tracemalloc**, cinco veces por variante, alternando el orden:

| Escritor | Reloj, cinco corridas (ms) | Mediana |
|---|---|---|
| Actual | 189.22 / 182.06 / 181.61 / 186.41 / 185.67 | 185.67 ms |
| Por partes | 211.36 / 212.53 / 211.91 / 211.29 / 212.28 | 211.91 ms |

La escritura por partes resultó un poco más lenta en esta prueba. Se propone por su menor pico de memoria, **no como aceleración**. Los tiempos instrumentados con tracemalloc se excluyen de esta comparación.

**Impacto / confianza:** medio en el pico de RAM de exportaciones grandes; irrelevante para el consumo del visor o de las tarjetas. Alta confianza en los bytes y asignaciones del experimento; media en el impacto sobre una sesión de la app. Costo bajo/medio, riesgo medio por preservación de UTF-8, publicación del archivo y manejo de errores.

**Qué medir antes:** repetir con 200/500/2,000 entradas, nombres con acentos y las tres marcas de estado, comparar XML descomprimido, memoria total y reloj sin instrumentación. Revisar errores de disco/escritura y salida incompleta, abrir en Premiere y confirmar todos los medios. Mantener el mismo nivel de gzip en ambos lados para no confundir dos cambios.

## Pistas nuevas medidas que no pondría en la lista de implementación

### La plantilla de proxy se relee, pero no explica los segundos perdidos

`adjuntar_proxy` vuelve a leer su plantilla para cada clip. La plantilla tiene **1,513 bytes comprimidos y 5,439 descomprimidos**. En el control de 500 entradas/proxies hubo 502 lecturas de plantillas en total y la mediana acumulada fue **0.106 s**, incluyendo la plantilla principal. Con 200 entradas y sondeos reales fueron 202 lecturas y 0.075 s de mediana.

Es trabajo redundante, pero **cachearlo por sí solo no es la prioridad que sugería la primera lectura del código**. El beneficio máximo observado está acotado por esos tiempos y no arregla los recorridos de C. Si se toca C, considerar compartir la plantilla sólo por exportación y sin mutarla; no justificar un cache global nuevo por esta cifra.

### Menos compresión de gzip: beneficio pequeño y más disco

Python 3.14 usa nivel 9 por defecto en `gzip.open`, confirmado en el entorno y en su [documentación oficial](https://docs.python.org/3.14/library/gzip.html). Sobre el mismo XML de 8,438,370 bytes se hicieron cinco repeticiones alternadas por nivel; se cronometró sólo comprimir/escribir, sin generar XML. Se verificó igualdad descomprimida en las 15 salidas.

| Nivel | Reloj mediano | Bytes del archivo |
|---|---:|---:|
| 9, actual | 76.49 ms | 1,123,028 |
| 6 | 62.88 ms | 1,159,342 |
| 1 | 32.70 ms | 1,393,226 |

Nivel 6 ahorra unos 14 ms a cambio de 36,314 bytes; nivel 1 ahorra unos 44 ms a cambio de 270,198 bytes. **No lo recomiendo como optimización prioritaria.** El resultado evita atribuir a «gzip lento» una espera que viene mayormente de otra parte. No se comparó apertura en Premiere de los niveles alternativos.

### Otras pistas que no se elevaron a hallazgo

El paquete contiene bibliotecas de codecs y módulos Qt que parecen candidatos a recortar, pero sus dependencias dinámicas no permiten quitarlos sólo porque no haya un import visible. No se compiló un FFmpeg/mpv reducido ni se midió la matriz de formatos; por eso no se ofrece un tamaño prometido. Tampoco se atribuyen los aproximadamente 1.9 GiB de `empaque/dist` a una instalación: esa carpeta incluye varios DMG históricos y artefactos de build. Limpiarlos sería mantenimiento del equipo de desarrollo, no hacer más económica la app del editor.

## Orden de validación y límites de la entrega

Para respuesta durante exportación, los números justifican continuar la idea 4 que ya tenía dueño; este documento agrega su comparación medida. Entre los mecanismos que se encontraron aquí, D es el experimento más acotado de RAM, A el más acotado de disco y C merece atención si los proyectos grandes siguen pesando después de atender la espera. B queda como opción de empaquetado con prioridad menor.

Las mediciones y scripts se conservaron como evidencia externa a la aplicación, en `evidencia-tercera-ronda.zip` dentro de los outputs de esta sesión de Codex. Incluye resultados JSON, perfil y los tres arneses ejecutados; no incluye videos ni altera el repo. SHA-256 del ZIP: `08bc3bd9a1a8fd69d9d12423fe1833e260e67d02dcef23c51ed6628bd925a723`. Para reproducir las partes principales: ejecutar el generador actual con `Manifest/Clip` de los tres archivos, tres proxies temporales y diez cuartos; cronometrar los sondeos reales; repetir inyectando `probe=lambda ruta: metadata[ruta]`; medir Qt con un temporizador de 10 ms en el mismo hilo y después con un único trabajador. Para D, usar exactamente el escritor experimental mostrado y arrancar `tracemalloc` con el árbol ya cargado. Para A/B, inspeccionar/copiar archivos regulares del paquete sin seguir symlinks, nunca alterar una app instalada o firmada.

No se corrió la suite completa, porque **no cambió código del producto ni de sus tests**. Sí terminaron los experimentos y sus comprobaciones indicadas. No se probó una ventana gráfica completa, una Mac distinta, un volumen remoto/iCloud ni Premiere. No hay validación de energía o batería. No se crearon ramas, no se cambiaron las opciones pendientes de miniaturas/proxies ni se hizo commit.
