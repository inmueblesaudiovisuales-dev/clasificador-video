# Importación rápida: darle a Clipify la carpeta del proyecto

Fecha: 2026-09-24. Diseño acordado con Bruno.

## Objetivo

Hoy Bruno arrastra cada carpeta de cámara por separado (Sony, Drone, a
veces Pocket). Se agrega una forma nueva, aparte: darle a Clipify la
carpeta RAÍZ del proyecto local (la copia de la tarjeta, no la de iCloud)
y que ella sola encuentre las carpetas de cámara que le importan.

## No reemplaza nada

Arrastrar carpetas sigue funcionando exactamente igual. Esto es una
opción nueva, tipo "importación rápida", para el caso normal de un
proyecto con la estructura de siempre.

## Qué carpetas busca

Dentro de la carpeta del proyecto, en `01. ASSETS VIDEO` (se reconoce por
contener "video" en el nombre, sin importar el número de la carpeta):

- `01. VIDEOS SONY` → cámara Sony. Principal.
- `02. VIDEO DRONE` → cámara del dron. Principal.
- `03. VIDEOS OSMO POCKET` → cámara Pocket. Opcional -- no todos los
  rodajes la usan, así que su ausencia no se avisa como problema.
- `04. VIDEOS OSMO ACTION` → **se ignora siempre**. No entra al sistema.

Solo se miran las carpetas DIRECTAS de `01. ASSETS VIDEO`: nunca baja a
`07. PROXIES`, así que `01. PROXY SONY` (que también dice "sony" en el
nombre) nunca se confunde con la carpeta de material.

## Proxies: siempre a iCloud, nunca los locales

Decisión de Bruno: aunque ya exista un proxy en la carpeta local
`07. PROXIES`, se ignora. Todo proxy que haga falta se genera directo en
la carpeta de iCloud del proyecto -- la misma que usa el flujo de
"Proyecto nuevo con folio" (`proyecto_colaborativo.py`,
`CARPETA_PROXIES`).

El folio sale del NOMBRE de la carpeta del proyecto local (Bruno siempre
la nombra con el folio, ej. `IAV-2609.10-A`). Con el folio y la carpeta
raíz de iCloud que Bruno ya configuró (`preferencias.carpeta_raiz_icloud`)
se calcula la ruta de destino con `proyecto_colaborativo.ruta_del_proyecto`.

Si el nombre de la carpeta no es un folio reconocible, o no hay carpeta
raíz de iCloud configurada, no se puede calcular el destino -- se avisa,
no se adivina una carpeta.

## Proxies: arrancan solos

A diferencia del flujo normal (donde Bruno le da click a "Crear
proxies"), aquí la generación de proxies que falten arranca SOLA en
cuanto se abre la carpeta del proyecto. No pide confirmación.

## Configurable después (fuera de esta primera entrega)

Bruno pidió que en Configuración se pueda cambiar el comportamiento por
default -- por ejemplo, que pregunte antes de generar en vez de
arrancar solo. Esa preferencia vive fuera de esta primera pieza: aquí
solo se construye la lógica de detección y de cálculo de la ruta de
proxies; la preferencia y el botón que dispara todo esto en la ventana
son un paso aparte.

## Alcance de esta entrega

Esta primera pieza es solo la lógica de descubrimiento (sin Qt):
encontrar las carpetas de cámara dentro de la carpeta del proyecto, y
calcular dónde deben ir los proxies nuevos en iCloud. Conectarla a un
botón en la ventana, y el arranque automático de la generación, quedan
para una siguiente pieza.
