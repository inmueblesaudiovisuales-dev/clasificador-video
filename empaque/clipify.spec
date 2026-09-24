# -*- mode: python ; coding: utf-8 -*-
"""Receta de empaquetado para PyInstaller.

La app depende de TRES cosas que hoy vienen de Homebrew y que en otra
computadora no existen:

  - `ffprobe`, para leer cada video (probe.py)
  - `mpv`, el programa, para las miniaturas (thumbnails.py)
  - `libmpv`, el motor de reproduccion, que a su vez cuelga de ~21
    librerias mas

Las tres se copian ADENTRO del paquete. `_dylibs_de()` sigue esa cadena de
dependencias con `otool`, porque PyInstaller no la ve: libmpv no se importa
como modulo de Python, la carga `python-mpv` en tiempo de ejecucion.
"""
import subprocess
from pathlib import Path

RAIZ = Path(SPECPATH).parent
PREFIJO_HOMEBREW = "/opt/homebrew"


def _dylibs_de(binario: str, vistos=None) -> set:
    """Todas las librerias de Homebrew de las que cuelga `binario`, en cadena."""
    vistos = vistos if vistos is not None else set()
    try:
        salida = subprocess.run(["otool", "-L", binario], capture_output=True,
                                text=True, check=True).stdout
    except Exception:
        return vistos
    for linea in salida.splitlines()[1:]:
        ruta = linea.strip().split(" ")[0]
        if ruta.startswith(PREFIJO_HOMEBREW) and ruta not in vistos:
            vistos.add(ruta)
            _dylibs_de(ruta, vistos)
    return vistos


binarios = []
for programa in ("ffprobe", "ffmpeg", "mpv"):
    ruta = f"{PREFIJO_HOMEBREW}/bin/{programa}"
    if Path(ruta).exists():
        binarios.append((ruta, "."))

librerias = set()
for semilla in (f"{PREFIJO_HOMEBREW}/lib/libmpv.dylib",
                f"{PREFIJO_HOMEBREW}/bin/ffprobe",
                f"{PREFIJO_HOMEBREW}/bin/ffmpeg",
                f"{PREFIJO_HOMEBREW}/bin/mpv"):
    if Path(semilla).exists():
        librerias |= _dylibs_de(semilla)
        librerias.add(str(Path(semilla).resolve()))
binarios += [(lib, ".") for lib in sorted(librerias)]

a = Analysis(
    [str(RAIZ / "src" / "clasificador_video" / "app.py")],
    pathex=[str(RAIZ / "src")],
    binaries=binarios,
    # El patrón de recorrido de Bruno. Va ADENTRO del paquete porque es lo
    # que hace que la guía proponga SU orden y no el de manual: sin él la
    # app instalada no fallaba, solo daba una guía genérica --y eso no se
    # nota hasta que ya editaste con ella. La ruta de destino es la misma
    # que busca `patron.py`.
    datas=[(str(RAIZ / "docs" / "patron-de-recorrido" / "MI-PATRON.md"),
            "docs/patron-de-recorrido"),
           (str(RAIZ / "recursos" / "premiere"), "recursos/premiere")],
    hiddenimports=["mpv"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore",
              "PySide6.QtQuick3D", "PySide6.QtCharts", "PySide6.QtDataVisualization"],
    noarchive=False,
)
pyz = PYZ(a.pure)
# El icono sale de `scripts/hacer_icono.py`, que lo dibuja del mismo
# codigo que pinta la marquita de la barra de titulo (`ui/marca.py`).
# Sin esta linea la app se queda con el icono generico de PyInstaller,
# que fue lo que paso hasta la 1.11.
ICONO = str(RAIZ / "empaque" / "icono" / "Clipify.icns")

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Clipify",
          console=False, target_arch=None, codesign_identity=None,
          icon=ICONO)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Clipify")
# La version se LEE de `src/clasificador_video/__init__.py`, que es donde
# vive. macOS la saca de aqui para «Obtener informacion» y para el nombre del
# `.dmg`, y la pantalla de inicio la lee del mismo lugar -- asi la que ve
# Bruno dentro de la app y la que ve el Finder no se pueden contradecir.
#
# Se lee con una expresion regular y no importando el modulo: importarlo
# desde la receta arrastraria PySide6 al proceso de PyInstaller.
import re

VERSION = re.search(
    r'__version__ = "([^"]+)"',
    (RAIZ / "src" / "clasificador_video" / "__init__.py").read_text(),
).group(1)

app = BUNDLE(coll, name="Clipify.app", icon=ICONO,
             # OJO: al cambiar el identificador, macOS trata a Clipify
             # como una app DISTINTA de la vieja Clasificador -- no la
             # reemplaza, conviven. La vieja se manda a la basura a
             # mano; ver el spec del 2026-08-27.
             bundle_identifier="com.brunogutierrez.clipify",
             version=VERSION,
             info_plist={"NSHighResolutionCapable": True,
                         "LSMinimumSystemVersion": "12.0",
                         "CFBundleShortVersionString": VERSION,
                         "CFBundleVersion": VERSION,
                         # Sin esto el Finder ofrece la app para abrir
                         # cualquier archivo, y no abre archivos sueltos:
                         # se abre ella y tu eliges el proyecto.
                         "CFBundleDocumentTypes": []})
