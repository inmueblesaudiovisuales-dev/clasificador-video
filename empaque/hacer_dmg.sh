#!/bin/bash
# Arma el .dmg instalable a partir del .app que produce PyInstaller.
#
# Un .dmg es un disco falso: al abrirlo, macOS lo monta como si conectaras
# una USB. Adentro van dos cosas y nada mas -- la app y un atajo a
# /Applications -- porque el "instalador" de una app de Mac es literalmente
# arrastrar una a la otra. No hace falta un programa de instalacion.
#
# Uso:  ./empaque/hacer_dmg.sh
# Sale: empaque/dist/Clasificador-<version>.dmg
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$RAIZ/empaque/dist"
APP="$DIST/Clasificador.app"

if [ ! -d "$APP" ]; then
  echo "No existe $APP." >&2
  echo "Arma la app primero:" >&2
  echo "  .venv/bin/pyinstaller empaque/clasificador.spec --distpath empaque/dist --workpath empaque/build --noconfirm" >&2
  exit 1
fi

# La version sale del Info.plist de la app, no de una variable de aqui: si se
# escribiera en los dos lados, tarde o temprano dirian cosas distintas y
# nadie sabria cual version tiene instalada.
VERSION="$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString)"
DMG="$DIST/Clasificador-$VERSION.dmg"
VOLUMEN="Clasificador $VERSION"

# Carpeta de montaje, aparte de `dist`: lo que este aqui adentro es lo que se
# ve al abrir el disco, y `dist` tiene ademas la carpeta suelta que arma
# PyInstaller al lado del .app.
ESCENARIO="$(mktemp -d)"
trap 'rm -rf "$ESCENARIO"' EXIT

# Copia con `ditto` y no con `cp`: preserva la firma de codigo y los
# atributos extendidos del paquete. Con `cp -R` la firma puede quedar
# invalida, y una app con la firma rota no abre en la otra Mac -- que es el
# unico lugar donde esto importa y el unico donde no lo veriamos a tiempo.
ditto "$APP" "$ESCENARIO/Clasificador.app"
ln -s /Applications "$ESCENARIO/Applications"

rm -f "$DMG"
hdiutil create \
  -volname "$VOLUMEN" \
  -srcfolder "$ESCENARIO" \
  -fs HFS+ \
  -format UDZO \
  -ov \
  "$DMG" >/dev/null

echo "Listo: $DMG"
du -h "$DMG" | cut -f1
