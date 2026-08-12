#!/bin/bash
# Arma el `.ccx` del plugin, que es lo que se le manda a otra computadora.
#
# Existe porque el camino son cinco pasos y cuatro de ellos fallan con un
# mensaje que no dice la verdad. En orden, y por que:
#
# 1. El CLI de UXP se instala CON `--ignore-scripts`. Sin eso el postinstall
#    revienta con «Cannot find module 'tar'»: el script que arma la
#    biblioteca nativa corre antes de que npm haya instalado sus propias
#    dependencias.
# 2. ...y por eso hay que correr ese script A MANO despues, con `tar` y
#    `fs-extra` puestos. Sin este paso, empaquetar falla con «No native build
#    was found for platform=darwin arch=x64 ... abi=137», que parece un
#    problema de version de Node y NO lo es: el modulo que trae Adobe es
#    N-API, o sea que sirve con cualquier Node. Lo unico que pasaba es que
#    nadie lo habia extraido.
# 3. El servicio de UXP tiene que estar corriendo, o el empaquetado falla con
#    «Could not connect to the UXP Developer Service».
# 4. La carpeta de salida tiene que EXISTIR, o falla con un ENOENT sobre el
#    `.ccx` que todavia no escribio.
# 5. Todo bajo `arch -x86_64`: el CLI de Adobe es x64.
#
# Uso:  ./uxp-plugin/empaquetar.sh
# Sale: /tmp/uxp-package-output/com.iav.clasificadorvideo_premierepro.ccx
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
CLI_DIR="${UXP_CLI_DIR:-$HOME/.uxp-cli}"
CLI="$CLI_DIR/node_modules/@adobe/uxp-devtools-cli/src/uxp.js"
HELPER="$CLI_DIR/node_modules/@adobe/uxp-devtools-helper"
SALIDA="${1:-/tmp/uxp-package-output}"

if [ ! -f "$CLI" ]; then
  echo "→ Instalando el CLI de UXP en $CLI_DIR (una sola vez)"
  mkdir -p "$CLI_DIR"
  # el package.json se escribe a mano: `npm init -y` toma el nombre de la
  # carpeta, y una que empieza con punto no es un nombre valido de paquete
  printf '{"name":"uxp-cli-local","private":true}\n' > "$CLI_DIR/package.json"
  # --ignore-scripts a proposito: ver el paso 1 de arriba
  ( cd "$CLI_DIR" && npm install --ignore-scripts @adobe/uxp-devtools-cli >/dev/null )
fi

if [ ! -d "$HELPER/build/Release" ]; then
  echo "→ Extrayendo la biblioteca nativa del helper (el paso que Adobe se salta)"
  ( cd "$HELPER" && npm install --no-save tar fs-extra >/dev/null 2>&1
    node scripts/devtools_setup.js )
  sleep 2
fi

if ! lsof -nP -iTCP:14001 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "→ Arrancando el servicio de UXP"
  ( arch -x86_64 node "$CLI" service start >/tmp/uxp-service.log 2>&1 & )
  for _ in $(seq 1 20); do
    lsof -nP -iTCP:14001 -sTCP:LISTEN >/dev/null 2>&1 && break
    sleep 1
  done
fi

mkdir -p "$SALIDA"      # o falla con un ENOENT sobre el .ccx que no escribio
cd "$AQUI"
arch -x86_64 node "$CLI" plugin package --outputPath "$SALIDA" >/dev/null

CCX="$(ls "$SALIDA"/*.ccx | head -1)"
echo
echo "Listo: $CCX"
echo
echo "Para instalarlo en ESA computadora (con Creative Cloud instalado):"
echo "  1. Cierra Premiere."
echo "  2. Doble clic al .ccx — Creative Cloud lo instala solo."
echo "  3. Abre Premiere: Ventana > Plugins UXP > Clasificador de Video."
