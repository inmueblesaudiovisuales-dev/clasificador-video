# Handoff: quitar Google Drive por completo

**Fecha:** 2026-09-24
**Repositorio:** `/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO`
**Rama de trabajo:** `master`
**Estado de partida:** la app sabe subir un proyecto a Google Drive para un
editor externo, revisar si el editor contestó, traer de vuelta el `.prproj`
y el material nuevo, y llevar el estado de esa entrega en la barra de
título, en la pantalla de inicio y en el propio `.cvproj`.

## Objetivo

Que Google Drive **desaparezca entero** del repo: el transporte, el estado
de la entrega, los botones, la pestaña de proyectos activos, la conexión en
Configuración y todo lo gráfico que lo nombra. No queda nada de Drive, ni
en el código ni en lo que ve Bruno.

La «entrega a editor externo» **no se reimplementa con otra cosa**: se va
completa. Existía solo porque existía Drive.

## Decisiones tomadas (Bruno, 2026-09-24)

1. **La entrega externa se va completa.** Botón «Subir a Drive», cápsula de
   estado en la barra, «Traer de vuelta», «Ya entregado» y la pestaña «En
   edición externa» de la pantalla de inicio dejan de existir. No se deja
   el concepto vacío para una vía futura.
2. **La llave `entrega` de los `.cvproj` viejos se limpia al abrir.** El
   archivo abre igual; la primera vez que se abre con esta versión se
   reescribe sin la llave.
3. **También se van las dependencias y credenciales de Google.**
   `google-api-python-client`, `google-auth-httplib2` y
   `google-auth-oauthlib` salen de `pyproject.toml`, y la carpeta local
   `Oauth/` (que **no está versionada**) se borra de la máquina.

## Lo que NO cambia

- Todo lo demás de la app: importar, clasificar, proxies, guía de edición,
  exportar a Premiere, bins, cuartos, unidades, proyecto colaborativo de
  iCloud (`proyecto_colaborativo.py`, que **no es Drive**), recientes,
  miniaturas, modos económico/rápido.
- La carpeta de iCloud de Configuración y su `cargar()`: se quedan.
- El plugin de Premiere (`uxp-plugin/`): no se toca ni un archivo.
- El formato del `.cvproj` en todo lo demás: solo pierde la llave `entrega`.

## Inventario: qué se va y de dónde

| Archivo | Qué pierde |
|---|---|
| `src/clasificador_video/drive.py` | Se borra completo (cliente, subida, traída, OAuth, resumen de cambios). |
| `src/clasificador_video/entrega.py` | Se borra completo (`EstadoEntrega`, `cerrar_en_archivo`). |
| `src/clasificador_video/buscar_prproj.py` | Se borra completo; **solo lo usaba la subida a Drive** (ver §Efectos colaterales). |
| `src/clasificador_video/ui/main_window.py` | Clase `_SubidaADriveJob`, `_TraidaDeDriveJob`; señales `drive_subida_lista`, `drive_subida_progreso`, `drive_traida_lista` y sus conexiones; `_drive_pool`; atributos `_entrega`, `_drive_cliente`, `_prproj_subiendo`; toda la sección «entrega a un editor externo por Drive» (`_estado_de_entrega`, `restaurar_entrega`, `_cliente_de_drive`, `_al_refrescar_entrega`, `_al_pedir_subir_a_drive`, `_preguntar_por_el_prproj`, `_subir_a_drive`, `_recursos_locales`, `_on_drive_subida_progreso`, `_on_drive_subida_lista`, `_al_pedir_traer_de_vuelta`, `_confirmar_traer_de_vuelta`, `_traer_de_vuelta`, `_on_drive_traida_lista`); las conexiones `title_bar.subir_a_drive_requested` / `traer_de_vuelta_requested`; el `entrega=` del autoguardado; los imports de `drive` y `buscar_prproj`. |
| `src/clasificador_video/ui/title_bar.py` | Señales `subir_a_drive_requested`, `traer_de_vuelta_requested`; `entrega_host`, `entrega_layout`, `entrega_pill`, `subir_button`, `traer_button`; métodos `set_estado_de_entrega`, `set_subiendo`; `layout.addWidget(self.entrega_host)`. |
| `src/clasificador_video/ui/pantalla_inicio.py` | Clase `_FilaActiva`; el `SegmentedControl` «Tus proyectos / En edición externa»; `activos_host`, `activos_lista`, `activos_vacio` y sus textos; señales `refrescar_pedido`, `traer_de_vuelta_pedido`, `ya_entregado_pedido`; `_estado_de_entrega_de`, `_hace_cuanto`, `nombres_activos_visibles`, `_al_cambiar_pestaña`; de `_FilaReciente`: `pildora`, `refrescar_button`, `refrescar_pedido` y `set_estado_de_entrega`; los imports `json`, `datetime` y `SegmentedControl`. |
| `src/clasificador_video/ui/pantalla_config.py` | Sección «Google Drive» completa (`drive_label`, `drive_button`, `_al_conectar_drive`, `_mostrar_estado_drive`), señales `drive_conectado` / `drive_estado_cambiado`, atributo `cliente_drive` y el import de `Thread`. También la sección «Proyectos de Premiere» (ver §Efectos colaterales). |
| `src/clasificador_video/app.py` | Clases `_SeñalesDeDrive` y `_TraidaActivaJob`; `CREDENCIALES_DRIVE`; `_drive_pool`, `_señales_de_drive`, `_drive_cliente_config`; conexiones de `inicio.refrescar_pedido`, `traer_de_vuelta_pedido`, `ya_entregado_pedido`; conexión `drive_conectado` de Configuración; métodos `_al_refrescar`, `_cliente_de_drive_o_avisar`, `_al_pedir_traer_de_vuelta_activo`, `_confirmar_traer_de_vuelta_activo`, `_al_terminar_traida_activa`, `_al_pedir_ya_entregado`, `_confirmar_ya_entregado`; imports `QRunnable`, `QThreadPool`, `Signal` si quedan sin uso. |
| `src/clasificador_video/proyecto.py` | El parámetro `entrega` de `a_dict` y su renglón en el documento; `raiz_de_assets_de` (solo la usaba «Traer de vuelta»). |
| `src/clasificador_video/preferencias.py` | `carpeta_de_proyectos_premiere` y `guardar_carpeta_de_proyectos_premiere` (solo los leía la subida a Drive). |
| `src/clasificador_video/ui/theme.py` | Reglas QSS `entregaPill` (y `[tono="contesto"]`), `configDrive`, `activaTraer`, `activaYaEntregado`, `recientePildora` (y sus tonos), `recienteRefrescar`, y `configPremiere` dentro de la regla compartida. |
| `tests/test_drive.py`, `tests/test_entrega.py`, `tests/test_buscar_prproj.py` | Se borran completos. |
| `tests/ui/test_main_window_entrega.py` | Se borra completo. |
| `tests/ui/test_pantalla_inicio.py`, `tests/ui/test_title_bar.py`, `tests/ui/test_pantalla_config.py`, `tests/ui/test_theme.py`, `tests/test_app.py`, `tests/test_proyecto.py`, `tests/test_preferencias.py` | Se quitan o ajustan los tramos de Drive/entrega. |
| `pyproject.toml` | Las tres dependencias de Google. |
| `Oauth/` (local, sin versionar) | Se borra de la máquina: `Client secret.txt`, el `client_secret_*.json` y el PNG de referencia. No viaja en git, así que es borrado local. |
| `README.md`, `docs/DESARROLLO.md` | Textos que nombran Drive o el flujo de entrega. |

## Efectos colaterales: lo que queda huérfano al quitar Drive

Estas piezas **no nombran Drive**, pero solo Drive las usaba. Se van en el
mismo trabajo, porque dejarlas es código muerto:

- **`buscar_prproj.py`** — `buscar_por_folio` solo servía para encontrar el
  `.prproj` que se iba a subir. Nada más lo llama. Se borra con sus pruebas.
- **La carpeta «Proyectos de Premiere» de Configuración** — guardaba la raíz
  donde `buscar_por_folio` buscaba; era un dato exclusivo de la subida.
  Se va la sección, su señal `carpeta_premiere_guardada`, su cableado en
  `main_window` / `app` y la preferencia `carpeta_de_proyectos_premiere`.
- **`proyecto.raiz_de_assets_de`** — la usaba «Traer de vuelta» desde la
  lista de activos. Se borra con sus pruebas.
- **`restaurar_entrega` en `main_window`** — **ya estaba muerto antes de
  este trabajo**: nadie lo llamaba. Se borra junto con el resto.

No se reabre nada de esto sin que Bruno lo pida.

## Plan, en orden

Para cada fase: escribir/ajustar la prueba, correrla y confirmar **RED**,
implementar, confirmar **GREEN**, correr la suite completa y un commit
atómico. La suite completa siempre es:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Y las pruebas del plugin, que **no deben cambiar**, al final de cada fase
donde se toquen archivos que el plugin pudiera leer (no debería hacer
falta ninguna, pero se confirma):

```bash
node uxp-plugin/pruebas/correr.js
```

### Fase 1 — Fuera el estado de entrega y la cápsula de la barra

- `proyecto.py`: quitar `entrega` de la firma de `a_dict` y la línea
  `"entrega": entrega` del documento. Quitar el comentario de esa llave.
- `main_window.py`: borrar la sección completa «entrega a un editor externo
  por Drive», los dos `QRunnable` de Drive, sus tres señales y conexiones,
  `_drive_pool`, `_entrega`, `_drive_cliente`, `_prproj_subiendo`, las dos
  conexiones de `title_bar`, el `entrega=` del autoguardado y los imports
  de `drive` / `buscar_prproj`.
- `title_bar.py`: quitar botones, cápsula, señales y `set_estado_de_entrega`
  / `set_subiendo`.
- Pruebas: borrar `tests/ui/test_main_window_entrega.py`; quitar de
  `tests/ui/test_title_bar.py` todo lo de `subir_button`, `entrega_pill`,
  `traer_button` y el botón `bar.subir_button` de la lista de anchos;
  quitar de `tests/test_proyecto.py` los dos tests de `entrega`.
- Prueba nueva que fije el objetivo: un `.cvproj` con `"entrega"` **abre
  igual** y el documento que se vuelve a guardar **ya no la trae** (la
  prueba de la migración al abrir es de la Fase 4; aquí basta con que el
  proyecto abra sin la llave).

Commit sugerido:

```text
Quitar el estado de entrega por Drive del proyecto y de la barra
```

### Fase 2 — Fuera la pestaña «En edición externa»

- `pantalla_inicio.py`: borrar `_FilaActiva`, el switch, los hosts de
  activos, las señales de entrega, `_estado_de_entrega_de`, `_hace_cuanto`
  y `nombres_activos_visibles`. Quitar de `_FilaReciente` la píldora, el
  botón `⟳`, `refrescar_pedido` y `set_estado_de_entrega`. Dejar la lista
  de recientes visible cuando hay filas y el estado vacío cuando no las
  hay.
- `app.py`: quitar las conexiones de `refrescar_pedido`,
  `traer_de_vuelta_pedido` y `ya_entregado_pedido`.
- Pruebas: ajustar `tests/ui/test_pantalla_inicio.py` (borrar los tramos de
  activos y de entrega) y `tests/test_app.py` (los tests de refrescar,
  traer de vuelta y ya entregado).

Commit sugerido:

```text
Quitar la pestaña «En edición externa» de la pantalla de inicio
```

### Fase 3 — Fuera el cliente de Drive y la conexión en Configuración

- Borrar `src/clasificador_video/drive.py`, `src/clasificador_video/entrega.py`,
  `src/clasificador_video/buscar_prproj.py`, `tests/test_drive.py`,
  `tests/test_entrega.py` y `tests/test_buscar_prproj.py`.
- `pantalla_config.py`: quitar la sección «Google Drive», sus señales,
  `cliente_drive`, `_al_conectar_drive`, `_mostrar_estado_drive` y el import
  de `Thread`. Ajustar el subtítulo para que no diga «Google Drive».
- `app.py`: borrar `_SeñalesDeDrive`, `_TraidaActivaJob`, `CREDENCIALES_DRIVE`,
  `_drive_pool`, `_señales_de_drive`, `_drive_cliente_config`, la conexión
  `drive_conectado`, y todos los métodos de Drive del coordinador.
- `proyecto.py`: quitar `raiz_de_assets_de` y sus dos pruebas en
  `tests/test_proyecto.py`.
- Prueba nueva en `tests/ui/test_pantalla_config.py`: la pantalla **ya no
  tiene** `drive_button` ni `drive_label` ni las señales `drive_conectado` /
  `drive_estado_cambiado`.
- `grep -rn "drive\|Drive\|google\|Google\|entrega" src/ tests/` para
  confirmar que no queda nada colgando (fuera de la palabra «entrega» en su
  sentido normal y de los nombres de tests de guía).

Commit sugerido:

```text
Quitar el cliente de Drive y su conexión en Configuración
```

### Fase 4 — Huérfanos, migración al abrir, dependencias y credenciales

- `preferencias.py`: quitar `carpeta_de_proyectos_premiere` y
  `guardar_carpeta_de_proyectos_premiere`, y sus pruebas en
  `tests/test_preferencias.py`.
- `pantalla_config.py`: quitar la sección «Proyectos de Premiere»
  (`carpeta_premiere_label`, `carpeta_premiere_button`,
  `carpeta_premiere_guardada`, `_al_elegir_carpeta_premiere`).
- `main_window.py` y `app.py`: quitar sus conexiones con
  `carpeta_premiere_guardada`.
- **Migración al abrir** (decisión 2): en `app.abrir_proyecto`, después de
  validar el documento, si trae `"entrega"` se quita y se reescribe con
  `proyecto.guardar`, tolerando que la escritura falle (se abre igual).
  Prueba en `tests/test_app.py`: un `.cvproj` con `"entrega"` queda sin esa
  llave en el archivo después de `abrir_proyecto`.
- `pyproject.toml`: quitar `google-api-python-client`, `google-auth-httplib2`
  y `google-auth-oauthlib`.
- `theme.py`: quitar las reglas QSS de Drive y de las píldoras de entrega.
- `tests/ui/test_theme.py`: quitar el caso especial de `drive.py` (dos
  líneas) en `test_ningun_modulo_declara_colores_fuera_del_tema`.
- `README.md` y `docs/DESARROLLO.md`: quitar menciones a Drive y al flujo de
  entrega externa.
- `Oauth/` y los archivos locales de credenciales (`~/.clasificador_video/`)
  son datos de la máquina, no del repo: borrarlos es limpieza local. Aquí
  solo se documenta; **no** se agrega nada al repo para migrarlos.

Commit sugerido:

```text
Quitar lo que quedó huérfano, limpiar al abrir y borrar las dependencias de Google
```

### Fase 5 — Regresión completa y verificación visual

- Suite completa y pruebas del plugin, en verde.
- **Verificación visual real** (regla de `CLAUDE.md`: si no se miró la
  imagen, no se afirma). Construir en una ventana de prueba y guardar un
  PNG en el scratchpad, **nunca en el repo**:
  1. la `TitleBar` de un proyecto: **no** debe verse «Subir a Drive», ni
     cápsula de estado, ni «Traer de vuelta»;
  2. la `PantallaInicio` con un par de recientes: **no** debe aparecer el
     switch «En edición externa», solo «Tus proyectos»;
  3. la `PantallaConfig`: **no** debe verse «Conectar Google Drive» ni la
     sección «Proyectos de Premiere».
- Leer cada PNG y confirmarlo antes de dar por cerrado.

Commit sugerido:

```text
Verificar sin Drive: barra, inicio y configuración
```

### Fase 6 — Checkpoint manual con Bruno

Abrir Clipify desde la fuente con un proyecto de verdad (incluido uno viejo
con entrega guardada):

- la app abre igual y el `.cvproj` viejo queda sin la llave `entrega`;
- la barra no tiene nada de Drive;
- la pantalla de inicio solo tiene «Tus proyectos»;
- Configuración ya no ofrece conectar Drive ni elegir carpeta de proyectos
  de Premiere;
- todo lo demás (clasificar, proxies, guía, exportar) sigue igual.

## Disciplina requerida

1. escribir/ajustar la prueba;
2. correrla y confirmar RED;
3. implementar el mínimo cambio;
4. correrla y confirmar GREEN;
5. correr siempre la suite completa

   ```bash
   QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
   ```

6. actualizar la bitácora de la sesión, si se usa una
   (`.superpowers/sdd/.../progress.md`) con RED/GREEN, suite y commit;
7. un commit atómico por fase, mensaje en español mexicano, terminado con
   `Co-Authored-By: <modelo> <noreply@anthropic.com>` — el modelo que de
   verdad hizo el trabajo, como pide `CLAUDE.md`.

Cuando un dato, un símbolo o una hipótesis del handoff no coincida con el
código real, imprimir el dato real y corregir la prueba o la implementación
con esa evidencia. No inventar rutas ni símbolos.

## Criterio de salida

El trabajo termina con la suite completa en verde, las pruebas del plugin
en verde y el checkpoint manual exitoso: **Google Drive ya no existe en el
repo** —ni código, ni UI, ni dependencias— y los proyectos viejos abren
igual, solo que sin la llave `entrega`. Nada más de la app cambió.
