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

## Proxies

**No hay nada que configurar.** Al importar, la app busca sola el proxy de cada
clip:

- **Se reconoce por el nombre**: el mismo del clip, terminado en `S03`. Así los
  escribe la FX30 — `C0001.MP4` → `C0001S03.MP4`.
- **Se busca** en la carpeta que importaste, en sus subcarpetas y en las
  **carpetas hermanas**. O sea que la carpeta de proxies puede ir al lado de la
  de clips, que es como vienen de la cámara.
- **Se comprueba** que el proxy tenga exactamente los mismos cuadros y los
  mismos fps que el original. El que no coincida se descarta: con un proxy
  corrido, el `in`/`out` que marcas caería en el cuadro equivocado.

Cuando hay proxy, la app **lo reproduce a él** (ir un cuadro atrás pasa de
~530 ms a ~22 ms), saca de él las miniaturas, y se lo pasa a Premiere en el
manifest para que quede enganchado.

La barra de estado lo dice siempre: `proxies 720p · 118/128`, o `sin proxies`
si no encontró ninguno.

## Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ --ignore=tests/test_app.py -q
```

`tests/test_app.py` tiene un cuelgue preexistente en entornos sin pantalla
real (limitación conocida del `QOpenGLWidget` de video bajo `offscreen`) — no
es parte de la suite normal.

## Historia

El primer intento de este proyecto generaba un XML `xmeml` (Final Cut Pro 7)
para importar a Premiere. Se abandonó: Premiere arma el clip solo con lo
declarado en el XML sin abrir el archivo de video, y ese formato no tiene
forma de declarar rotación — un clip vertical (cámara rotada, el caso normal
acá con la Sony FX30) siempre queda acostado. La vía real es el plugin UXP en
`uxp-plugin/`, que usa `project.importFiles()` (el mismo camino que usa
Premiere al arrastrar un archivo a mano) y sí respeta la rotación. Detalle
completo en `docs/superpowers/archive/HALLAZGOS-2026-08-05-rotacion-vertical.md`.
