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

## Cómo está organizado el repo

```
src/clasificador_video/     la app (Python + PySide6 + mpv)
  ui/                       los widgets
tests/                      pytest, espeja src módulo a módulo
  ui/                       los widgets
empaque/                    receta de PyInstaller y armado del .dmg
scripts/                    utilidades sueltas
sample-media/               clips reales para pruebas a mano (no versionado)
docs/                       esto
  patron-de-recorrido/      cómo edita Bruno, en prosa, y sus datos
  superpowers/              specs, planes, mockups e historia del proyecto
    archive/                lo que ya se cerró
```

### Los archivos de la guía de edición

La guía se arma y se guarda en Clipify. Al generar el `.prproj`, el orden
de sus cuartos determina los nombres y la posición de los bins.

| Archivo | De qué se encarga |
|---|---|
| `guia.py` | Clasifica los cuartos por nombre y arma las piezas de la guía. |
| `ui/pantalla_guia.py` | Muestra el tablero y permite aceptar el orden. |
| `ui/pantalla_config.py` | Muestra las opciones de miniaturas y carpetas. |

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
