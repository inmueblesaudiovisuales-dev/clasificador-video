# Instalar / actualizar el plugin

1. Cerrar Premiere.
2. Borrar la carpeta instalada:
   rm -rf ~/"Library/Application Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1"
3. Volver a copiarla desde `uxp-plugin/` (ver Step 2 del Task 10 del plan).
4. Abrir Premiere. `Window > UXP Plugins > Clasificador de Video`.

Notas:
- Sobrescribir sin borrar deja archivos viejos que ya no existen en la version nueva.
- Si se sube el major de la version en `manifest.json`, cambia el nombre de la
  carpeta (`_1` -> `_2`) y hay que borrar la anterior a mano.
- No tener el plugin cargado en UXP Developer Tools al mismo tiempo que instalado:
  mismo id, dos copias, y Premiere puede tomar la equivocada.
