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

- Cada entrega crea su carpeta en la **raíz** de su Drive. Bruno ya tiene
  una carpeta propia donde quiere que caigan, no una lista suelta.
- Para saber si un editor ya contestó, hoy hay que abrir Clipify y
  refrescar. Bruno quiere poder verlo de un vistazo **en el propio
  Drive** — rojo si falta editar, verde si ya regresó.

## 2. El permiso de Drive cambia de `drive.file` a `drive`

Esta es la pieza que se decide primero porque las otras dos dependen de
ella, y porque tocarla requiere a Bruno (reconectar la cuenta).

**Por qué hace falta cambiarlo:** con `drive.file` (el permiso actual,
"Clipify solo toca lo que ella misma sube"), la app solo puede leer o
escribir carpetas que **ella misma creó**. La carpeta destino que Bruno
quiere usar la hizo él a mano en el navegador de Drive — la app no la
puede "ver" con ese permiso, y el intento de crear algo adentro fallaría.

**Qué se descartó y por qué:** la alternativa de no tocar el permiso
—dejar que la app cree la carpeta destino ella misma la primera vez, y
que Bruno la arrastre después a donde quiera en el navegador de Drive—
sí funcionaba con `drive.file`, porque mover un archivo no le quita el
acceso a quien lo creó. Se descartó porque Bruno prefirió ampliar el
permiso en vez de cambiar el orden de los pasos.

**Qué implica el cambio (todo esto lo hace Bruno, no es código):**
- Agregar el scope `https://www.googleapis.com/auth/drive` en la
  pantalla "Data access" de Google Cloud Console (antes solo tenía
  `drive.file`).
- Borrar `~/.clasificador_video/drive_token.json` y volver a darle
  "Conectar Google Drive" desde Configuración — el token viejo no tiene
  el permiso nuevo, y las llamadas fallarían con un error de permiso
  insuficiente si se reusa.

**Qué cambia en el código:**
- `_SCOPES` en `drive.py` pasa de `["…/auth/drive.file"]` a
  `["…/auth/drive"]`.
- El comentario sobre `cliente_autorizado()` que hoy dice "permiso
  acotado… Clipify solo toca lo que ella misma sube" se corrige para
  explicar el porqué del permiso completo (carpetas que Bruno crea a
  mano, no solo las que crea la app).

No hay prueba de pytest para esto — es exactamente el mismo caso que el
resto de `cliente_autorizado()`: necesita la cuenta real de Bruno.

## 3. Carpeta destino configurable

Nuevo campo en Configuración, junto al de "Proxies" (mismo patrón que
`carpeta_de_proyectos_premiere` en `preferencias.py`): un campo de texto
donde Bruno pega el link de la carpeta de Drive (ej.
`https://drive.google.com/drive/folders/1vOdb…`), y un botón para
guardarlo. La app saca el ID de la carpeta del link con una función
chica y testeable (`drive.id_de_carpeta_desde_link(url) -> str | None`),
y si el link no tiene forma de carpeta de Drive, muestra un error en vez
de guardar cualquier cosa.

Se guarda en `preferencias.py` como `carpeta_destino_drive_id`, igual
que las demás preferencias de carpeta.

**Si nunca se configura, no cambia nada:** `subir_paquete` sigue creando
la carpeta del proyecto en la raíz de Drive, como hace hoy. El campo
nuevo es un parámetro opcional (`carpeta_padre_id: str | None = None`)
que solo se usa al crear una carpeta **nueva** — si ya hay
`carpeta_existente` (el caso de "Subir de nuevo"), ese parámetro no
aplica, porque la carpeta ya vive donde vive.

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

## 5. Orden de implementación

Bruno pidió partirlo en dos porque el primer paso lo requiere a él:

1. **Ahora:** el cambio de permiso (§2) — código mínimo (una línea de
   scope + un comentario), y la parte manual de Bruno (Cloud Console +
   reconectar).
2. **Después, con TDD:** carpeta destino configurable (§3) y color de
   la carpeta (§4) — se implementan juntos porque comparten el mismo
   punto de entrada (`subir_paquete`) y las mismas pruebas con el
   cliente falso.

## 6. Pruebas

- `drive.id_de_carpeta_desde_link` — casos: link normal de carpeta,
  link con `?usp=sharing` colgado, link que no es de Drive (da `None`).
- `subir_paquete` con `carpeta_padre_id` — la carpeta nueva se crea
  DENTRO de esa carpeta, no en la raíz.
- `subir_paquete` sin `carpeta_padre_id` — sigue creando en la raíz
  (no regresión).
- `subir_paquete` — llama a `colorear_carpeta` con `COLOR_FALTA_EDITAR`
  sobre la carpeta que resultó (nueva o reusada).
- `revisar_y_persistir` — cuando hay cambios, llama a
  `colorear_carpeta` con `COLOR_YA_REGRESO` antes de guardar el estado.
- `revisar_y_persistir` — cuando NO hay cambios, no toca el color.
- Configuración: guardar un link válido guarda el ID; guardar un link
  inválido muestra el error y no guarda nada.
