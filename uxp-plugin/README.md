# Instalar / actualizar el plugin

## Repartirlo a otra computadora

```bash
./uxp-plugin/empaquetar.sh
```

Sale un `.ccx` en `/tmp/uxp-package-output/`. **Eso es lo que se manda.** En
la otra computadora, con Creative Cloud instalado:

1. Cerrar Premiere.
2. Doble clic al `.ccx` — Creative Cloud lo instala solo.
3. Abrir Premiere: `Ventana > Plugins UXP > Clasificador de Video`.

No hace falta terminal ni instalar nada más del lado de quien lo recibe.

### Por qué hay un script y no tres comandos

Porque son cinco pasos y **cuatro fallan con un mensaje que no dice la
verdad**. Quedó escrito adentro del script, y en resumen:

- El CLI de UXP hay que instalarlo con `--ignore-scripts`, o su postinstall
  revienta con «Cannot find module 'tar'»: el script que arma la biblioteca
  nativa corre antes de que npm instale sus propias dependencias.
- Y por eso hay que correr ese script **a mano** después. Sin ese paso,
  empaquetar falla con «No native build was found for platform=darwin
  arch=x64 ... abi=137». **Eso parece un problema de versión de Node y no lo
  es** — se creyó eso el 2026-08-10 y se dio por bloqueada la distribución
  del plugin. El módulo que trae Adobe es N-API, o sea que sirve con
  cualquier Node; lo único que pasaba es que nadie lo había extraído.
- El servicio de UXP tiene que estar corriendo, o falla con «Could not
  connect to the UXP Developer Service».
- La carpeta de salida tiene que existir, o falla con un `ENOENT` sobre el
  `.ccx` que todavía no escribió.
- Y todo bajo `arch -x86_64`, porque el CLI de Adobe es x64.

El script comprobado de cero el 2026-08-12: borrando la instalación del CLI
y matando el servicio, `./uxp-plugin/empaquetar.sh` deja el `.ccx` listo.

## Actualizar el plugin en ESTA computadora

Con el plugin ya instalado, para iterar sin repetir el `.ccx` basta copiar
los archivos encima:

```bash
cp -R uxp-plugin/index.html uxp-plugin/manifest.json uxp-plugin/js "$HOME/Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1.0.0/"
```

Ojo: eso **no sirve para instalar por primera vez** —Premiere no registra un
plugin que aparece solo en esa carpeta, ver abajo— y Premiere **no recoge
archivos nuevos con Premiere abierto**: cerrar y abrir el panel no basta, hay
que cerrar Premiere entero.

---

**Actualizado 2026-08-06.** El método de copiar la carpeta a mano a
`.../UXP/Plugins/External/<id>_<version>` **no funciona** como instalación de
producción — se probó en vivo y Premiere nunca lo registró (detalle completo
en `docs/superpowers/archive/HANDOFF-2026-08-06-plugin-terminado.md` y en el spec,
§12). La vía real, validada en vivo, es empaquetar como `.ccx` e instalar con
UPIA.

## Instalar por primera vez

1. Arrancar el UXP Developer Service (una sola vez por sesión de terminal):
   ```bash
   arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js service start
   ```
2. Empaquetar el plugin (desde `uxp-plugin/`):
   ```bash
   cd "uxp-plugin/"
   arch -x86_64 node /tmp/uxpcli-install/node_modules/@adobe/uxp-devtools-cli/src/uxp.js plugin package --outputPath /tmp/uxp-package-output
   ```
   Produce `/tmp/uxp-package-output/com.iav.clasificadorvideo_premierepro.ccx`.
3. Instalar con UPIA (viene con Creative Cloud Desktop):
   ```bash
   "/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent" --install /tmp/uxp-package-output/com.iav.clasificadorvideo_premierepro.ccx
   ```
4. Cerrar y abrir Premiere. `Window > UXP Plugins > Clasificador de Video`.

## Actualizar (después de cambiar código)

**`--install` encima de una instalación existente es un no-op** — UPIA ve el
mismo id+versión y no reextrae archivos, aunque el `.ccx` haya cambiado.
Primero quitar, luego instalar:

```bash
"/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent" --remove "Clasificador de Video IAV"
"/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent" --install /tmp/uxp-package-output/com.iav.clasificadorvideo_premierepro.ccx
```

`--remove` toma el **nombre** de la extensión (campo `name` de
`manifest.json`, ej. `"Clasificador de Video IAV"`), no una ruta de archivo —
pasarle una ruta falla con status -406.

Reiniciar Premiere después de instalar o quitar — no recarga en caliente la
carpeta `External/` con Premiere ya abierto.

## Notas

- Si sube la versión en `manifest.json`, el `.ccx` nuevo se instala con
  `--install` normal (versión distinta, no es el caso no-op de arriba).
- El plugin nunca debe estar cargado en UXP Developer Tools (`plugin load`)
  al mismo tiempo que instalado vía UPIA: mismo identificador, dos copias, y
  Premiere puede tomar la equivocada.
- Para desarrollo activo (recargar sin reinstalar cada vez), seguir usando
  `uxp.js plugin load` / `plugin reload` como está documentado en el plan
  (`docs/superpowers/plans/2026-08-05-plugin-uxp-premiere.md`). El flujo de
  `.ccx` + UPIA es para la copia de producción/distribución, no para iterar
  código.
