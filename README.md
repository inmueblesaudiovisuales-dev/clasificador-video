# Clasificador de Video

App de escritorio (PySide6) para que un editor de video clasifique clips de
shootings inmobiliarios por cuarto, marque in/out y bueno/malo, y exporte un
manifest que un plugin de Adobe Premiere usa para armar el proyecto de
edición solo. La usa un editor trabajando rápido con el teclado, muchas
veces junto a Premiere abierto.

El material real que la mueve: **HEVC 10-bit de una Sony FX30**, mayoría
**vertical**, más tomas de un **dron DJI**. De ahí salen casi todas las
decisiones de diseño — por qué importan tanto los proxies, por qué el material
se agrupa por cámara y por qué el `in`/`out` no se negocia.

## Qué hace, de entrada a salida

1. **Importas** las carpetas de las tarjetas. El material se agrupa en **bins**
   —uno por cámara— y también puedes crear bins vacíos y arrastrar clips entre
   ellos.
2. **Clasificas con el teclado**, sin tocar el mouse: cuarto, `pick`/`reject`/
   destacado, `in`/`out`. `⌘Z` y el historial deshacen cualquier paso.
3. **La hoja de contactos** (`⇥`) muestra todo junto, con búsqueda y filtros,
   y deja pintar cuartos por lotes.
4. **Los proxies**: los enganchas si la cámara ya los trae, o **la app te los
   genera** (clic derecho en el bin) si no — el caso del dron.
5. **Exportas a Premiere**, y el plugin arma el proyecto solo: bins por cuarto,
   etiquetas de color, `in`/`out` y proxies enganchados.

Todo vive en un archivo `.cvproj` que puedes mover, respaldar y abrir en otra
computadora, reencontrando el material donde esté.

## Estructura del repo

- **`src/clasificador_video/`** — la app de escritorio (Python/PySide6).
  Entry point: `clasificador_video.app:main`.
- **`uxp-plugin/`** — el plugin de Adobe Premiere (UXP) que lee el manifest
  exportado por la app y arma el proyecto. Ver `uxp-plugin/README.md` para
  instalación.
- **`tests/`** — suite de pytest, espeja `src/clasificador_video/` módulo a
  módulo (`tests/test_player.py` prueba `src/clasificador_video/player.py`,
  etc.). `tests/ui/` cubre los widgets de PySide6.
- **`scripts/`** — utilidades sueltas (`abrir_app.command`, doble click para
  correr la app sin depender de terminal).
- **`empaque/`** — la receta de PyInstaller para armar el `.app`.
- **`sample-media/`** — clips de video reales para pruebas manuales, no
  versionado (`.gitignore`).
- **`docs/superpowers/`** — historial de handoffs, specs y planes de las
  sesiones de desarrollo de este proyecto.

## Instalar y correr

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/clasificador
```

O con doble click en `scripts/abrir_app.command` una vez instalado.

## Proyectos

La app abre en una lista con tus últimos proyectos. Cada proyecto es **un
archivo `.cvproj`** que puedes guardar donde quieras, mover y respaldar como
cualquier otro archivo. **Proyecto nuevo** te pregunta dónde ponerlo y lo crea
ahí mismo: nunca hay trabajo sin un archivo donde vivir.

De ahí en adelante se guarda solo, en ese archivo, mientras trabajas.

Un proyecto que ya no está en su lugar —el disco desconectado, la carpeta
movida— **no desaparece de la lista**: se ve apagado y dice que no se
encuentra.

Si vienes de una versión anterior, lo que tenías clasificado estaba en una
sesión escondida. La primera vez que abres esta versión se convierte sola en
un `.cvproj` dentro de `~/Documents` y aparece en la lista. La sesión vieja no
se borra: queda apartada como `sesion.migrada.json`.

## Proxies

Un proxy es una copia ligera del clip que se usa **solo para navegar**: el
`in`/`out` que marcas encima vale para el original. Por eso todo lo de abajo
gira alrededor de una regla: **un proxy que no calce cuadro a cuadro con su
original no se engancha**, venga de donde venga. Con uno corrido, el `in`
caería en el cuadro equivocado y nadie se daría cuenta.

### Enganchar los que ya existen

Se enganchan **a mano**, como el *Attach Proxies* de Premiere: eliges **un**
proxy cualquiera del bin y la app engancha los demás sola.

1. Botón **Proxies** arriba a la derecha, o clic derecho en el bin →
   **Enlazar proxies…**
2. Elige cualquier proxy de ese bin. **No** tiene que ser el del clip que
   estás viendo: la app averigua a cuál corresponde por el nombre.

De ese par sale el patrón de nombre —`C0001.MP4` + `C0001S03.MP4` da el sufijo
`S03`— y con eso se buscan los demás **en esa misma carpeta**. Da igual cómo se
llame la carpeta o el sufijo: sale de lo que elegiste.

Cada proxy se comprueba antes de engancharlo: tiene que tener exactamente los
mismos cuadros y los mismos fps que su original. El que no coincida se descarta,
porque con un proxy corrido el `in`/`out` caería en el cuadro equivocado.

Con proxy, la app **lo reproduce a él** (ir un cuadro atrás pasa de ~530 ms a
~22 ms), saca de él las miniaturas —5.6 veces más rápido y sin calentar la
máquina— y se lo pasa a Premiere en el manifest para que quede enganchado allá.

La barra de estado lo dice siempre: `proxies 720p · 118/128`, o `sin proxies`.

### Crear los que no existen

Cuando la cámara no escribe proxies —el caso del dron— la app los genera:
**clic derecho en el encabezado del bin → «Crear proxies del bin…»**.

### Al importar, la app lo ofrece sola

Un bin sin proxies abre un diálogo con las dos salidas buenas juntas:

- **Enlazar los que ya tengo…** — la Sony ya los graba; se eligen y listo.
- **Crear los proxies** — el caso del dron, que no los trae.
- **Ahora no.**

Van juntas porque la respuesta correcta depende de la cámara y uno no quiere
pensarlo dos veces. Y conviene resolverlo ahí: mientras no haya proxies, **las
portadas de la hoja se sacan del original y cuestan cinco veces más** (5.8 s
por clip contra 1.2 s, medido con material real). Con 132 clips, cuatro
minutos en vez de uno.

Los saca del original con el codificador del chip (`h264_videotoolbox`, lado
corto 720), uno por uno y en segundo plano: puedes seguir clasificando
mientras corre. El encabezado del bin va diciendo `creando proxies · 7/23`, y
**cada clip se engancha apenas termina el suyo**, así que el material se
aligera conforme avanza. Desde el mismo menú se cancela — lo hecho se queda,
lo que faltaba no se hace, y volver a darle solo genera los que faltan.

Van a una carpeta **`Proxies` al lado** de la del material, no adentro, para
no ensuciar la copia de la tarjeta. Terminan en `S03`, igual que los de la
Sony, así que el ingest los descarta si algún día se arrastra esa carpeta
como si fuera material.

Cuesta unos **10 s por cada 6 s de video**. Medido con material real: 285 MB
pasan a 17 MB con los mismos 1010 cuadros.

## Empaquetar como app

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller empaque/clasificador.spec --distpath empaque/dist --workpath empaque/build --noconfirm
```

Sale `empaque/dist/Clasificador.app`, de unos 173 MB. **Adentro viajan
`ffprobe`, `ffmpeg`, `mpv` y las 55 librerías de las que cuelgan**, así que no
hace falta instalar nada en la computadora donde se va a usar.

Va firmada con una firma propia, que es gratis y es lo que el chip M exige para
que un programa arranque. **No** lleva la firma de pago de Apple, así que:

- **Pasándola por USB o carpeta compartida**: abre directo.
- **Mandándola por internet** (Drive, WeTransfer, correo): la primera vez hay
  que ir a *Configuración → Privacidad y seguridad → Abrir de todos modos*.

### El `.dmg` para repartirla

```bash
./empaque/hacer_dmg.sh
```

Sale `empaque/dist/Clasificador-<versión>.dmg`, de unos 72 MB. La versión la
lee del `Info.plist` de la app, para que el instalador y la app nunca digan
cosas distintas; se cambia en un solo lugar, la constante `VERSION` de
`empaque/clasificador.spec`.

Un `.dmg` es un disco falso: al abrirlo macOS lo monta como si conectaras una
USB. Adentro van solo la app y un atajo a `/Applications`, porque instalar una
app de Mac es literalmente arrastrar una a la otra.

**Lo comprobado de la 1.0**, en esta misma máquina y no en otra:

- Arranca con el `PATH` vacío, tanto recién armada como copiada desde el
  `.dmg` montado — o sea que no está usando nada de Homebrew sin darse cuenta.
- Ninguno de sus binarios apunta a `/opt/homebrew`.
- El `ffprobe` y el `ffmpeg` de adentro corren y leen un clip real con el
  `PATH` vacío. Ese fue el modo de fallo la primera vez que se empaquetó: la
  app abría y no importaba un solo clip.
- La firma del `.app` sigue válida después de viajar dentro del `.dmg` (por
  eso se copia con `ditto` y no con `cp -R`).

**Lo que sigue sin comprobarse**, y solo se puede comprobar allá: que abra en
**otra** Mac.

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

## Historia

El primer intento de este proyecto generaba un XML `xmeml` (Final Cut Pro 7)
para importar a Premiere. Se abandonó: Premiere arma el clip solo con lo
declarado en el XML sin abrir el archivo de video, y ese formato no tiene
forma de declarar rotación — un clip vertical (cámara rotada, el caso normal
aquí con la Sony FX30) siempre queda acostado. La vía real es el plugin UXP en
`uxp-plugin/`, que usa `project.importFiles()` (el mismo camino que usa
Premiere al arrastrar un archivo a mano) y sí respeta la rotación. Detalle
completo en `docs/superpowers/archive/HALLAZGOS-2026-08-05-rotacion-vertical.md`.
