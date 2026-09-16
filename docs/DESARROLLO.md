# Desarrollo

Todo lo que no le sirve a quien solo usa la app. Para qué es y cómo se usa,
ver el [README](../README.md).

## Correr desde el código

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/clasificador
```

O doble clic a `scripts/abrir_app.command`, ya instalado.

Fuera del paquete se usan el `ffprobe`, `ffmpeg` y `mpv` del sistema
(Homebrew). Adentro del `.app` viajan los tres.

## Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

La suite corre **completa**, sin ignorar nada. Hasta agosto de 2026 este
comando llevaba `--ignore=tests/test_app.py` porque ese archivo colgaba bajo
`offscreen`; la F3 lo reescribió —el diálogo de configuración que abría con
`exec()` murió con ella— y desde entonces corre en medio segundo. Si alguna
vez vuelve a colgarse, es un bug a resolver, no una limitación a esquivar.

**Y córrela varias veces cuando toques la interfaz.** Este proyecto ha tenido
cuatro segfaults intermitentes, y el último apareció después de decenas de
corridas limpias seguidas: contra un fallo que sale 1 de cada 20 veces, veinte
corridas en verde salen por azar más de un tercio de las veces. Lo que sirve
es contar fallos sobre un número de corridas decidido de antemano — y, si
sospechas que el fallo es nuevo, medir el commit anterior con el mismo número.

**Un test que no viste fallar no prueba nada.** Ha pasado dos veces en este
repo: un test que pasaba igual con el arreglo puesto o quitado. Antes de
confiar en uno nuevo, rómpelo a propósito y confirma que se pone rojo.

### Las pruebas del plugin

El plugin tiene las suyas, y son un comando aparte porque no son Python:

```bash
node uxp-plugin/pruebas/correr.js
```

Corren **sin abrir Premiere**: son la lógica pura del plugin —hoy, el prefijo
numérico de las carpetas de cuartos (`numeroDeCuarto.js`) y el camino de un
clip (`estructura.js`)—, que no le pregunta nada a Premiere ni a la red. Sin
dependencias ni `npm install`: el corredor lee los archivos del plugin y los
evalúa, que es lo mismo que hace el navegador con un `<script src>`.

Aquí vivían también los casos del orden sugerido. Se mudaron a
`tests/test_guia.py` el 2026-09-14, cuando la guía se mudó a Clipify.

Lo que sí necesita Premiere —los bins, la red, el disco de UXP— vive en el
arnés de `uxp-plugin/js/autocheck-tests.js`, que corre **dentro** de Premiere
y está apagado (`AUTOCHECK_ACTIVO = false` en `autocheck.js`). Para correrlo:
préndelo, recarga el plugin en Premiere y lee
`/private/tmp/clasificador-autocheck/resultado.json`. Acuérdate de apagarlo
después.

Y ojo con la asimetría: **lo del arnés no corre solo**. Los casos que viven
allá solo se comprueban cuando alguien se acuerda de prenderlo, así que
cualquier lógica que se pueda probar sin Premiere va en el corredor de Node,
no en el arnés.

## Empaquetar la app

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller empaque/clipify.spec --distpath empaque/dist --workpath empaque/build --noconfirm
./empaque/hacer_dmg.sh
```

Sale `empaque/dist/Clipify-<versión>.dmg`, de unos 72 MB. La versión se
declara **en un solo lugar**: la constante `VERSION` de
`empaque/clipify.spec`. El script la lee del `Info.plist` de la app ya
armada, para que el instalador y la app nunca digan cosas distintas.

Adentro del `.app` viajan `ffprobe`, `ffmpeg`, `mpv` y las 55 librerías de las
que cuelgan, con sus rutas internas reescritas. Va firmada con una firma
propia, que es gratis y es lo que el chip M exige para arrancar; **no** lleva
la firma de pago de Apple, así que por internet la primera vez hay que
autorizarla en *Privacidad y seguridad*.

**Comprobado de la 1.0** (en esta máquina, no en otra): arranca con el `PATH`
vacío recién armada y copiada desde el `.dmg` montado, ninguno de sus binarios
apunta a Homebrew, el `ffprobe` de adentro lee un clip real sin nada instalado
alrededor, y la firma sigue válida después de viajar dentro del `.dmg` (por
eso se copia con `ditto` y no con `cp -R`).

Lo que **no** está comprobado, y solo se puede comprobar allá: que abra en
otra Mac.

## Empaquetar el plugin de Premiere

```bash
./uxp-plugin/empaquetar.sh
```

Sale un `.ccx` que se manda y se instala con doble clic. El script hace los
cinco pasos, **cuatro de los cuales fallan con un mensaje que no dice la
verdad** — el detalle está en `uxp-plugin/README.md` y adentro del script.

## Cómo está organizado el repo

```
src/clasificador_video/     la app (Python + PySide6 + mpv)
  ui/                       los widgets
tests/                      pytest, espeja src módulo a módulo
  ui/                       los widgets
uxp-plugin/                 el plugin de Premiere (UXP) + su empaquetador
empaque/                    receta de PyInstaller y armado del .dmg
scripts/                    utilidades sueltas
sample-media/               clips reales para pruebas a mano (no versionado)
docs/                       esto
  patron-de-recorrido/      cómo edita Bruno, en prosa, y sus datos
  superpowers/              specs, planes, mockups e historia del proyecto
    archive/                lo que ya se cerró
```

### Los archivos de la guía de edición

La guía se arma en Clipify y viaja congelada en el manifest como un guion de
pasos —un cuarto puede salir en más de un paso—. El panel de Premiere la lee,
y del lado del plugin también **guarda el avance**: qué pasos ya se
palomearon. De este lado (Clipify) se reparte así, y el corte es a propósito
—lo que piensa se prueba sin red y sin abrir la app—:

| Archivo | De qué se encarga |
|---|---|
| `patron.py` | Leer `docs/patron-de-recorrido/MI-PATRON.md` y entregarlo como texto. |
| `guia.py` | Lo que PIENSA: arma el prompt, lee la respuesta, revisa la lista. Sin Qt, sin red, sin disco. |
| `llave.py` | Guardar y leer la llave en `~/.clasificador_video/llave.json`. |
| `ia.py` | La llamada HTTP, y nada más. Cambiar de proveedor es este archivo. |
| `ui/pantalla_guia.py` | La pantalla: dos preguntas, el resultado, «Usar este orden». |
| `ui/pantalla_config.py` | La pantalla de configuración. Hoy, un ajuste: la llave. |

Del lado del plugin, el avance —qué pasos ya se montaron— está **partido en
dos**, y el corte es el mismo criterio de siempre: lo que se puede probar sin
abrir Premiere, aparte de lo que no.

| Archivo | De qué se encarga |
|---|---|
| `avance.js` | Lo que PIENSA: qué paso es el actual, si un cuarto ya quedó completo, qué palomitas siguen valiendo si la guía cambió. Lógica pura, sin disco — se prueba con `node uxp-plugin/pruebas/correr.js`. |
| `avanceDisco.js` | Guardar y leer esas palomitas, un archivo por proyecto, en la carpeta del plugin. Toca el disco de UXP y por eso **no** se prueba con `node`. |

Ese corte es lo que permite comprobar la parte importante —cuándo un cuarto
cuenta como montado, qué palomitas se descartan si la guía cambió— sin
depender del arnés que corre dentro de Premiere.

Las dos pantallas —la guía y la configuración— son **widgets hijos de la
ventana, no `QDialog` modales**. El diálogo de configuración que abría con
`exec()` colgaba la suite bajo `offscreen` y murió con la F3; ese camino no se
reabre.

**`MI-PATRON.md` es el único dueño de ese texto.** Es el archivo que Bruno
edita a mano cuando algo no le cuadra, y de ahí sale lo que viaja en el
prompt. No hay copia en ningún otro lado: dos copias del mismo dato que se
editan por separado se desincronizan en el primer cambio de opinión. Y se
escribe **sin cuentas y sin justificarse** — las cuentas se hacen para decidir
qué entra y se quedan fuera.

Dos reglas de nombres que valen la pena:

- Los módulos de `src/clasificador_video/` son **1:1** con
  `tests/test_<módulo>.py`.
- `sample-media/` se llamó `TEST/` y se renombró: en un filesystem que no
  distingue mayúsculas chocaba con `tests/`.

## Antes de tocar la interfaz

Leer `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`. Es la
dirección de diseño acordada, e incluye lo que ya se evaluó y se descartó.

Y **verificación visual real**: nunca afirmar que algo se ve bien sin haber
mirado el pixel. Para un widget, construirlo, `grab()`, guardar el PNG y
abrirlo. Los archivos de esa comprobación van al scratchpad de la sesión,
nunca al repo.

## Decisiones técnicas que no se reabren

Están en [`CLAUDE.md`](../CLAUDE.md) con su razón: por qué mpv se embebe con
la API de render y no con `wid`, por qué el `ScrubBar` usa `QPainter` y no
QSS, por qué el camino `xmeml` está descartado, por qué el LUT por bin está
parado y por qué los `.LRF` del dron no entran.
