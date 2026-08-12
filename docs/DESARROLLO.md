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

## Empaquetar la app

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller empaque/clasificador.spec --distpath empaque/dist --workpath empaque/build --noconfirm
./empaque/hacer_dmg.sh
```

Sale `empaque/dist/Clasificador-<versión>.dmg`, de unos 72 MB. La versión se
declara **en un solo lugar**: la constante `VERSION` de
`empaque/clasificador.spec`. El script la lee del `Info.plist` de la app ya
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
  superpowers/              specs, planes, mockups e historia del proyecto
    archive/                lo que ya se cerró
```

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
