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
    datas=[],
    hiddenimports=["mpv"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore",
              "PySide6.QtQuick3D", "PySide6.QtCharts", "PySide6.QtDataVisualization"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Clasificador",
          console=False, target_arch=None, codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Clasificador")
# La version va aqui y en un solo lugar. macOS la lee de `Info.plist` y es
# lo que se ve en «Obtener informacion» y en el nombre del `.dmg`; si la app
# y el instalador dijeran versiones distintas, nadie sabria cual tiene
# instalada.
VERSION = "1.2"

app = BUNDLE(coll, name="Clasificador.app",
             bundle_identifier="com.brunogutierrez.clasificador",
             version=VERSION,
             info_plist={"NSHighResolutionCapable": True,
                         "LSMinimumSystemVersion": "12.0",
                         "CFBundleShortVersionString": VERSION,
                         "CFBundleVersion": VERSION,
                         # Sin esto el Finder ofrece la app para abrir
                         # cualquier archivo, y no abre archivos sueltos:
                         # se abre ella y tu eliges el proyecto.
                         "CFBundleDocumentTypes": []})
