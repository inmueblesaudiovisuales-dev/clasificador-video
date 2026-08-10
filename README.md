# Clasificador de Video

App de escritorio (PySide6) para que un editor de video clasifique clips de
shootings inmobiliarios por cuarto, marque in/out y bueno/malo, y exporte un
manifest que un plugin de Adobe Premiere usa para armar el proyecto de
edición solo. La usa un editor trabajando rápido con el teclado, muchas
veces junto a Premiere abierto.

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

Se enganchan **a mano**, como el *Attach Proxies* de Premiere: eliges el proxy
de **un** clip y la app engancha los demás sola.

1. Ponte en un clip que sí tenga proxy.
2. Botón **Proxies**, arriba a la derecha.
3. Elige el archivo de proxy **de ese clip**.

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

## Empaquetar como app

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller empaque/clasificador.spec --distpath empaque/dist --workpath empaque/build --noconfirm
```

Sale `empaque/dist/Clasificador.app`, de unos 175 MB. **Adentro viajan
`ffprobe`, `ffmpeg`, `mpv` y las 55 librerías de las que cuelgan**, así que no
hace falta instalar nada en la computadora donde se va a usar.

Va firmada con una firma propia, que es gratis y es lo que el chip M exige para
que un programa arranque. **No** lleva la firma de pago de Apple, así que:

- **Pasándola por USB o carpeta compartida**: abre directo.
- **Mandándola por internet** (Drive, WeTransfer, correo): la primera vez hay
  que ir a *Configuración → Privacidad y seguridad → Abrir de todos modos*.

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
acá con la Sony FX30) siempre queda acostado. La vía real es el plugin UXP en
`uxp-plugin/`, que usa `project.importFiles()` (el mismo camino que usa
Premiere al arrastrar un archivo a mano) y sí respeta la rotación. Detalle
completo en `docs/superpowers/archive/HALLAZGOS-2026-08-05-rotacion-vertical.md`.
