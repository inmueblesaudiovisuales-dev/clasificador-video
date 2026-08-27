#!/usr/bin/env python3
"""Arma `empaque/icono/Clipify.icns` a partir de `ui/marca.py`.

Uso:  QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/hacer_icono.py

Por que un script y no un `.icns` dibujado a mano: el icono del Finder y la
marquita de la barra de titulo son el MISMO dibujo, y si vivieran en dos
lados se irian pareciendo cada vez menos con cada retoque. Aqui el `.icns`
es una consecuencia de `marca.icono()`, no una copia suya.

El `.icns` que sale SI se guarda en el repo: la receta de PyInstaller lo
necesita al empacar, y pedirle a quien arme la app que corra un paso previo
--o peor, que instale Qt para poder empacar-- es una trampa que se pisa una
sola vez y siempre en el peor momento.

macOS pide cada tamaño dos veces, normal y `@2x`: la version `@2x` de 32
es un archivo de 64 px con otro nombre. No es redundante -- asi el sistema
elige el archivo exacto en vez de escalar, que es donde se pierde el filo.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

DESTINO = RAIZ / "empaque" / "icono" / "Clipify.icns"

# (nombre dentro del .iconset, lado en pixeles). Los diez que pide macOS.
TAMANOS = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from clasificador_video.ui import marca

    # `iconutil` es de macOS y no existe en otro lado. Se avisa antes de
    # pintar 10 archivos para tirarlos.
    if sys.platform != "darwin":
        print("Esto solo corre en macOS: `iconutil` es de Apple.",
              file=sys.stderr)
        return 1

    QApplication([])
    DESTINO.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temporal:
        iconset = Path(temporal) / "Clipify.iconset"
        iconset.mkdir()
        for nombre, lado in TAMANOS:
            if not marca.icono(lado).save(str(iconset / nombre), "PNG"):
                print(f"No se pudo escribir {nombre}", file=sys.stderr)
                return 1
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(DESTINO)],
            check=True,
        )

    print(f"Listo: {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
