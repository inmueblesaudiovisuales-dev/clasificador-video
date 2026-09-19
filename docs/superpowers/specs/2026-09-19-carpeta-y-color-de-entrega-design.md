# Carpeta destino y color de la entrega en Drive — diseño

*(Spec del 2026-09-19. Extiende la entrega a un editor externo
— [2026-09-18-entrega-a-editor-externo-design.md](2026-09-18-entrega-a-editor-externo-design.md) —
después de que Bruno conectó Drive por primera vez y quiso dos cosas que
esa spec no cubría: que las carpetas de entrega caigan en un lugar fijo
de su Drive, no sueltas en la raíz, y que se vean a color desde el propio
Drive sin tener que abrir Clipify.)*

## 1. El problema

Con la entrega ya funcional, dos cosas le faltaban a Bruno para que la
use de verdad:

- Cada entrega crea su carpeta en la **raíz** de su Drive. Bruno quiere
  que caigan todas juntas en un solo lugar, no sueltas en la raíz.
- Para saber si un editor ya contestó, hoy hay que abrir Clipify y
  refrescar. Bruno quiere poder verlo de un vistazo **en el propio
  Drive** — rojo si falta editar, verde si ya regresó.

## 2. El permiso de Drive NO cambia — decisión revertida

Se intentó primero ampliar `drive.file` a `drive` (acceso completo) para
poder escribir dentro de una carpeta que Bruno ya había creado a mano en
el navegador. Al intentarlo en Google Cloud Console salió: *"Your app
requires verification"* — `drive` es un permiso **restringido**, y
publicar una app con un permiso restringido exige que Google audite la
app (revisión de seguridad de terceros, pagada) para poder usarse fuera
del modo de pruebas. Completamente desproporcionado para una app de un
solo usuario.

Se confirmó revisando otro sistema de Bruno (`proposalinc_contratos` /
"Velada", que también sube a Drive): ese sistema **nunca pidió acceso
completo** — usa el mismo permiso acotado que Clipify ya tenía
(`drive.file`, solo carpetas que la propia app crea), documentado en su
propio repo casi con las mismas palabras que esta spec. Cuando quiso
usar una carpeta que Bruno ya tenía, la nota en su documentación decía
literalmente que para eso hacía falta el permiso completo — y ese
sistema optó por no pedirlo.

**Se revierte al permiso original: `drive.file` no se toca.** La carpeta
destino la crea la propia app (§3), nunca una que Bruno haya hecho a
mano — así nunca hace falta el permiso amplio.

## 3. Carpeta destino: fija, creada por la propia app

En vez de un campo en Configuración, la app usa un nombre fijo:
**"Proyectos para edición externa"** (`drive.CARPETA_ENTREGAS`). Al subir
un proyecto que no tiene ya una carpeta (primera vez, no "Subir de
nuevo"), `subir_paquete`:

1. Busca esa carpeta en la raíz de Drive. Si no existe, la crea (mismo
   patrón que ya usa con la subcarpeta "Proxies" —
   `_subcarpeta_existente_o_nueva`, ahora reusado también para esto).
2. Crea la carpeta del proyecto **dentro** de esa carpeta.

Bruno puede mover "Proyectos para edición externa" a donde quiera dentro
de su Drive (moverla no le quita el acceso a quien la creó) — la app la
sigue encontrando por nombre en la raíz solo si nunca se movió; si Bruno
la mueve, sigue sirviendo para las entregas ya creadas dentro de ella
(no hace falta volver a encontrarla, cada proyecto ya sabe su propio
`drive_folder_id`), pero una entrega **nueva** después de moverla
volvería a crear "Proyectos para edición externa" en la raíz, sin
darse cuenta de que ya existe movida. Esto es una limitación conocida y
aceptada: si algún día molesta, la solución es guardar el ID de esa
carpeta madre la primera vez que se crea (en vez de rebuscarla por
nombre cada vez) — no se construye ahora porque no se sabe todavía si
hace falta.

**Ya no aplica:** el campo de Configuración para pegar un link, y la
función para parsear el ID de una URL — se descartan enteros junto con
el permiso amplio.

## 4. Color de la carpeta

La carpeta del proyecto en Drive (el `folderColorRgb` que ofrece la API
de Drive) refleja el mismo estado que ya vive en `EstadoEntrega` — no es
un dato nuevo, es el mismo dato pintado en otro lugar. Mismo principio
que ya se aplicó con el color por cámara en Premiere: "un dato, dos
sitios que lo pintan, y los dos leen la misma fuente."

- **Rojo** (`COLOR_FALTA_EDITAR`) — se pone en el momento en que
  `subir_paquete` termina de subir (primera vez o "Subir de nuevo").
- **Verde** (`COLOR_YA_REGRESO`) — se pone en el momento en que
  `revisar_y_persistir` detecta el cambio a `EDITOR_CONTESTO` (al darle
  ⟳ o al abrir "Traer de vuelta"), antes de guardar el nuevo estado.
- **Se queda verde** después de "Traer de vuelta": cerrar la entrega no
  le vuelve a tocar el color. La carpeta verde queda como historial de
  una entrega ya cerrada.

Los valores hexadecimales exactos salen de la paleta de colores que
ofrece la API de Drive para carpetas (no cualquier color sirve — Drive
solo acepta un set fijo); se confirman contra el Drive real de Bruno al
implementar, igual que el resto de las llamadas reales a la API.

Poner el color usa el mismo cliente inyectado que todo lo demás en
`drive.py` — un método nuevo `colorear_carpeta(carpeta_id, color)` en
`_ClienteDrive` (y su doble `_ClienteFalso` para las pruebas). No lleva
manejo de error especial: si falla, se propaga igual que cualquier otra
falla de red de `subir_paquete` o `revisar_y_persistir` — ya hay un
`try/except` en el job que la llama (`_SubidaADriveJob`,
`_TraidaDeDriveJob` vía `_al_refrescar_entrega`) que la reporta como
cualquier otro error.

## 5. Estado de la implementación

- §3 (carpeta fija "Proyectos para edición externa") — **hecho**, con
  TDD, 2026-09-19.
- §4 (color rojo/verde) — pendiente.

## 6. Pruebas

- `subir_paquete` sin `carpeta_existente` — crea "Proyectos para edición
  externa" en la raíz si no existía, y la carpeta del proyecto dentro de
  ella. **Hecho.**
- `subir_paquete` — reusa "Proyectos para edición externa" si ya existe,
  no la vuelve a crear. **Hecho.**
- `subir_paquete` — llama a `colorear_carpeta` con `COLOR_FALTA_EDITAR`
  sobre la carpeta que resultó (nueva o reusada). Pendiente.
- `revisar_y_persistir` — cuando hay cambios, llama a
  `colorear_carpeta` con `COLOR_YA_REGRESO` antes de guardar el estado.
  Pendiente.
- `revisar_y_persistir` — cuando NO hay cambios, no toca el color.
  Pendiente.
