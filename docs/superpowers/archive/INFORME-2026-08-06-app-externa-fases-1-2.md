# Informe de construcción — App externa del clasificador de video — 2026-08-06

## 1. Qué es este documento

Crónica del día en que se construyó la **app externa completa** del Clasificador de Video para Bienes Raíces: qué se hizo, qué problemas se encontraron en el camino (con causa y solución), qué decisiones se tomaron con evidencia en vivo, y qué queda por mejorar. Es el registro para la próxima sesión — el punto de partida es `docs/superpowers/plans/2026-08-06-app-externa-clasificador-fase2.md` (ya ejecutado) y su sección final de pendientes.

Resumen en una línea: de cero a una app que **importa material real, reproduce video embebido, clasifica por teclado y exporta el manifest** que el plugin UXP de Premiere consume — 124 pruebas en verde, 29 commits.

## 2. Qué se construyó hoy

**Fase 1 (mañana, 14 tareas, plan `2026-08-06-app-externa-clasificador.md`):** la fundación de lógica pura + cascarón de UI, todo TDD.

- `manifest.py` — modelo `Clip`/`Manifest` con el formato exacto §11 (no negociable, lo consume el plugin).
- `autosave.py` — guardado atómico (temporal + rename).
- `rooms.py` — 17 cuartos maestros + selección con numeración automática (Recámara 1, 2…).
- `category_path.py` — subcuartos creados perezosamente **por padre** (`Recámara 1 > Baño` ≠ `Recámara 2 > Baño`).
- `ingest.py` — importación de varias carpetas/cámaras a la vez.
- `proxy_match.py` — emparejamiento original ↔ proxy por sufijo `S03`.
- `thumbnails.py` — miniaturas con `mpv --vo=image` (subprocess, sin GUI).
- `player.py` — `MpvPlayer`, envoltura de python-mpv con `hwdec=videotoolbox`.
- `keyboard.py` — `KeyboardRouter` (teclas 1-9, P/X/U, modo subcuarto pendiente).
- `ui/` — `RoomConfigDialog`, `Filmstrip`, `MainWindow`, `app.py` (cascarón).

**Entre fases:** se corrigió que la app no abría sin `PYTHONPATH=src` (`ModuleNotFoundError`) → `pyproject.toml` con build config + `pip install -e .` → hoy abre con `.venv/bin/python -m clasificador_video.app` o `.venv/bin/clasificador`.

**Fase 2 (tarde, 11 tareas, plan `2026-08-06-app-externa-clasificador-fase2.md`):** el flujo funcional completo.

- **M1 — Reproducción embebida:** `VideoWidget` con mpv embebido por `wid` (validado en vivo), ventana con reproductor al centro, selector de calidad (Full/1/2/1/4/1/8) y leyenda de teclado.
- **M2 — Arranque real:** diálogo de cuartos al abrir → ventana con esa selección.
- **M3 — Ingest a la UI:** botón "Importar carpetas…", clips reales con fps de ffprobe, miniaturas en segundo plano, teclado real (QShortcut: Espacio, ←/→, I/O, P/X/U, 1-9).
- **M4 — Clasificación completa:** subcuartos creados en vivo (la app pregunta una sola vez a qué cuarto cuelgan), borde azul del clip actual, contadores de clips por cuarto en la columna.
- **M5 — Persistencia y export:** autoguardado en cada acción (cuarto, flag, in/out, navegación) con restauración al arrancar; botón "Exportar manifest…" con aviso no bloqueante de clips sin clasificar.
- **M6 — Cierre:** suite completa en verde (124 passed) y smoke end-to-end con material real de `TEST/`.

## 3. Problemas encontrados y resueltos (con evidencia)

### Fase 1 — correcciones a los planes

| # | Problema | Causa | Solución |
|---|---|---|---|
| 1.1 | Test de ingest usaba `f.name` pero la dataclass tenía `display_name` | Plan inconsistente consigo mismo | Property `name` en `IngestFolder` |
| 1.2 | Test de thumbnails fallaba antes de correr | Línea muerta en `fake_runner` que hacía `cmd.index(...)` con string incompleto → `ValueError` | Eliminada la línea; quedó la segunda (correcta) |
| 1.3 | Test de filmstrip inspeccionaba `item.styleSheet()` pero el borde se ponía en un label interno | Plan inconsistente | Borde aplicado al widget del ítem |
| 1.4 | `handle_key_press("p")` reventaba con `ValueError: int("p")` | `KeyboardRouter.resolve_room_key` hacía `int(key)` sin validar | Guard `key.isdigit()` en el router |
| 1.5 | La app no abría: `ModuleNotFoundError` | `src/` no está en `sys.path` fuera de pytest | Instalación editable (`pip install -e .`) |

### Fase 2 — hallazgos técnicos reales (los importantes)

| # | Síntoma | Causa raíz | Solución y evidencia |
|---|---|---|---|
| 2.1 | **Falsa alarma del spike de embedding.** El primer spike "funcionó" con `vo="libmpv"` (time_pos avanzaba), pero `width: None` reveló que **no había video — solo audio** | `vo="libmpv"` sin render context: `fatal No render context set` en el log de mpv | Probar de nuevo **sin** `vo` explícito: `VO: [gpu-next] 3840x2160 videotoolbox` + `time_pos` avanzando con video real. Lección: verificar no solo el tiempo sino que el decodificador y el VO estén activos |
| 2.2 | El primer `toggle_play()` **pausaba** en vez de reproducir | mpv real inicia **sin pausa**; el `FakeMpv` de los tests inicia pausado → el toggle quedaba invertido | `pause=True` explícito en `MpvPlayer.__init__` — estado inicial definido, coherente con el fake |
| 2.3 | `I`/`O` no marcaban nada en el clip | `mark_in`/`mark_out` **guardaban pero no devolvían** el frame; `handle_key_press` usaba el valor de retorno | Los métodos ahora devuelven el frame |
| 2.4 | **El peor del día: la reproducción embebida se congelaba 90+ segundos** al importar la carpeta `TEST/` | 4 subprocesos `mpv --vo=image --hwdec=videotoolbox` saturan **VideoToolbox** (sesiones de decodificación simultáneas limitadas); hasta 1 sola miniatura por hardware **bloqueaba al reproductor embebido** (time_pos `None` indefinidamente) | **Miniaturas en software** (quitar `--hwdec` del comando de thumbnails — un frame por clip no necesita hardware) + pool de **1 job** (`setMaxThreadCount(1)`). Medido: miniatura software ≈ 1 s real por clip, reproductor fluye. **Esto corrige un supuesto del plan fase 1** (el test que exigía `--hwdec` en thumbnails fue actualizado; decisión documentada en el commit) |
| 2.5 | El **setter** de `time_pos` de python-mpv se cuelga indefinidamente | Los property-set de python-mpv esperan la cola del event loop de libmpv; con el decodificador ocupado el set nunca responde | La app **solo lee** `time_pos` (mark_in/out); nunca lo escribe. Documentado para no re-introducirlo |
| 2.6 | Subcuartos: presionar la tecla de un cuarto numerado creaba directamente el candidato "Terraza" | La misma tecla del cuarto se consumía como tecla de subcuarto (índice 2 = Terraza) | Al entrar en modo subcuarto **no consumir la tecla actual**: `return` y esperar la siguiente |
| 2.7 | Subcuartos: la tecla de "Recámara 1" asignaba el cuarto directo, nunca entraba en modo subcuarto | El chequeo de "cuarto numerado sin subcuartos" corría **después** de `resolve_room_key`, que ya resolvía el cuarto | Reorden: verificar el caso numerado **antes** de resolver |
| 2.8 | Al cerrar la ventana con thumbnails pendientes: `RuntimeError: Signal source has been deleted` | Un job del pool emitía su señal sobre un `QWidget` de señales ya destruido | `closeEvent` con `_thread_pool.waitForDone(5000)` antes de destruir la UI |
| 2.9 | Tests de export tardaban 39 s | `QMessageBox.warning` **modal** esperando al usuario (no monkeypatcheado en un test) | Monkeypatch del warning en los tests |
| 2.10 | Los smoke scripts de consola **se colgaban al salir** sin imprimir nada | (a) stdout **bufferizado** con pipe (los prints nunca se flusheaban), (b) Python espera los threads no-daemon de python-mpv al salir | En smokes: `python -u` y `os._exit(0)` tras imprimir. **No afecta a la app real** (corre con `app.exec()` y cierra limpio con `closeEvent`) |

### Lecciones de proceso

- **Los smokes con GUI no son pruebas unitarias**: se colgaron, se bufferizaron y mintieron ("funcionó" = solo audio). Las verificaciones de video deben mirar el log de mpv (VO activo, hwdec) y no solo un número.
- **Los tests con fakes engañan en estados iniciales**: `FakeMpv` pausado vs mpv real sin pausa invirtió el toggle. Definir el estado inicial explícito y probar contra el real al menos una vez por pieza.
- **La saturación de un recurso compartido (VideoToolbox) no se ve en unit tests**: solo se detecta con el flujo real (importar + reproducir a la vez).

## 4. Estado final (verificado)

- **Suite:** `pytest -v` → **124 passed, 0 failures** (fase 1: 95 → fase 2: +29).
- **Smokes manuales con material real de `TEST/`:** video HEVC 4K embebido reproduciendo (time_pos > 0), 4/4 miniaturas, clasificación por teclado, export end-to-end verificado: manifest con las llaves exactas del plugin (`orden ruta categoria_path fps in_frame out_frame flag ruta_proxy`), cuarto + pick/reject aplicados.
- **Contrato con el plugin UXP:** verificado contra su código (`processManifest.js`) y sus fixtures — la app genera exactamente lo que consume.
- **Rama:** `master`, 29 commits hoy (25 de código + 2 de docs + 2 de chore), mensajes en español siguiendo el estilo del repo.

## 5. Lo que falta por mejorar (fase 3 y deuda)

Del plan fase 2 (fuera de alcance, material para el próximo plan):

1. **UI de proxies** — "Buscar proxies" (clic derecho sobre carpeta, spec §3): `match_proxies` ya existe y está testeado; falta la acción que apunte una carpeta a su carpeta de proxies y rellene `ruta_proxy` en los clips.
2. **`orientacion` automática** — hoy el manifest sale con `"horizontal"` fijo; detectar la dominante de los probes (rotación → vertical) es trivial.
3. **Deshacer (Ctrl+Z multinivel)** — la leyenda lo anuncia pero no existe; requiere un stack de acciones.
4. **Drag-and-drop** de carpetas al panel de ingest (spec §3).
5. **Nombre de proyecto** — hoy fijo "Shooting sin nombre"; un campo en el diálogo de arranque.
6. **Verificación end-to-end con Premiere real** — el manifest se validó contra los fixtures del plugin, pero el ciclo completo (app → manifest → botón del plugin) no se probó con Premiere abierto; es la verificación final que solo Bruno puede hacer.

Deuda técnica y limitaciones conocidas (decididas hoy, no bugs):

- **Subcuartos solo para cuartos numerados** (Recámara 1, Baño 1…): un cuarto simple (p. ej. "Sala") nunca entra en modo subcuarto. Es un recorte de diseño para no frenar la clasificación rápida; el spec no especifica qué cuartos aceptan subcuartos.
- **Restauración de sesión simplificada**: la selección de cuartos se reconstruye togglando cada nombre activo, perdiendo la semántica de "cuartos repetibles" (cuenta futura de "Recámara"). Funciona igual para la sesión restaurada, pero si luego se cambia el count no es consistente.
- **Miniaturas 1 a la vez** (software): ~1 s por clip; para shootings de 100+ clips la cola tarda. La optimización natural (hardware limitado a 1 sesión compartida o pre-generación por lote) debe pensarse cuando se mida el uso real.
- **`wid` embedding sin overlays**: mpv dibuja su propia superficie; no se puede componer UI de Qt encima del video (p. ej. HUD de in/out sobre la imagen). Aceptado — el estado se muestra en el filmstrip.
- **El punto de color** de la esquina del filmstrip (spec §4) y el **indicador "Autoguardado hace Ns"** (spec §3) aún no existen; el borde de color sí.
- **Los smokes de consola con mpv+Qt** requieren `-u`/`os._exit`; no convertirlos en tests.

## 6. Cómo continuar

El siguiente paso natural es un plan de fase 3 con los puntos 1-5 de la sección 5 (proxies, orientación, deshacer, drag-and-drop, nombre de proyecto) — cada uno es una tarea pequeña y enfocada. Antes de eso, vale la pena que Bruno corra el ciclo completo con Premiere (punto 6) para validar el sistema de punta a punta con material real.
