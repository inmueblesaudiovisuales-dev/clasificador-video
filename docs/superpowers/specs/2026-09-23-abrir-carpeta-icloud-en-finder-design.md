# Abrir la carpeta de iCloud en Finder

Fecha: 2026-09-23. Brainstorm breve con Bruno, sobre la base de
`2026-09-23-proyecto-colaborativo-icloud-design.md`.

## Qué es

Un botón nuevo en la barra de arriba, junto a "Proxies", que abre en
Finder la carpeta del proyecto en iCloud (la misma que crea "Proyecto
nuevo → Con folio…"). Ahorra tener que navegar a mano cuando Bruno quiere
compartir esa carpeta o revisarla.

## Cuándo se ve

Solo si `self._carpeta_de_icloud` de la ventana no es `None`. Un proyecto
creado con "Usar una carpeta a mano" (o uno de antes de esta fase) no
tiene esa carpeta, y ahí el botón no aparece -- mismo criterio que
`traer_button` en la entrega por Drive, que también se esconde según el
estado.

## Qué hace

Al apretarlo, abre la carpeta en Finder con
`QDesktopServices.openUrl(QUrl.fromLocalFile(...))` -- la forma estándar
de Qt para esto, funciona igual en Windows/Linux por si algún día hiciera
falta.

## Dónde vive el estado

`MainWindow.set_carpeta_de_icloud` es el único lugar que asigna
`self._carpeta_de_icloud` -- lo llaman tanto `crear_proyecto` (proyecto
nuevo) como `_poblar_ventana` (proyecto que se abre). Ahí mismo, cada vez
que se llama, se le dice al `TitleBar` si debe mostrar u ocultar el
botón. Un solo lugar decide, la barra solo obedece.
