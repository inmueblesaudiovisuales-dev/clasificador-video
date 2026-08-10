# [RESUELTO — la Fase 3 mencionada aquí como pendiente ya se ejecutó, ver docs/superpowers/plans/2026-08-06-app-externa-clasificador-fase3.md] Handoff — Sesiones 2026-08-06 (F1, F2) + sesión de corrección de bugs — Clasificador de Video

## 1. Resumen

La app externa del Clasificador de Video para Bienes Raíces está completa y funcional tras 2 fases de construcción + 1 sesión de corrección. Estado: **importa material real, reproduce video HEVC 4K embebido vía mpv, clasifica por teclado y exporta el manifest JSON que el plugin UXP de Premiere consume. 124 tests en verde, 29 commits.**

La sesión de corrección arregló 8 bugs que impedían usar la app de punta a punta (botón muerto, import sin efecto, crash de autosave, mpv en ventana separada) y 5 bugs de calidad (CSS roto, autosave faltante en subcuartos, sesión restaurada sin player, `except Exception` genérico).

---

## 2. Arquitectura y stack

| Componente | Tecnología | Rol |
|---|---|---|
| UI | PySide6 (Qt 6.11) | Ventana, filmstrip, diálogos, atajos de teclado |
| Reproducción | python-mpv (libmpv) embebido vía `wid` | Decodifica HEVC 10-bit con VideoToolbox |
| Miniaturas | mpv `--vo=image` sin hardware | Un frame por clip en background thread |
| Sondeo de video | ffprobe | FPS real, rotación, duración |
| Autoguardado | JSON atómico (temp + rename) | `~/.clasificador_video/sesion.json` |
| Plugin Premiere | UXP (JavaScript) | Lee el manifest, arma bins, aplica labels e in/out |

**Flujo completo:** App externa → clasificar por teclado → exportar manifest JSON → plugin UXP lo importa en Premiere con bins organizados.

---

## 3. Qué se construyó (Fases 1 y 2)

### Fase 1 — Fundación de lógica pura + cascarón de UI (mañana, 14 tareas, 95 tests)

| Módulo | Archivo | Qué hace |
|---|---|---|
| Manifest | `manifest.py` | Dataclasses `Clip`/`Manifest`, formato JSON §11 exacto que consume el plugin |
| Autosave | `autosave.py` | Guardado atómico (temp + rename), load de sesión |
| Rooms | `rooms.py` | 17 cuartos maestros + selección con numeración automática |
| CategoryPath | `category_path.py` | Subcuartos creados perezosamente por padre |
| Ingest | `ingest.py` | Importación de carpetas/cámaras, filtro por extensión (.mp4/.mov/.mxf/.lrf) |
| Proxy Match | `proxy_match.py` | Emparejamiento original ↔ proxy por sufijo `S03` |
| Thumbnails | `thumbnails.py` | Miniaturas con mpv `--vo=image` (software, no satura VideoToolbox) |
| Player | `player.py` | `MpvPlayer`, hwdec=videotoolbox, pause inicial explícito, selector calidad, mark in/out |
| Keyboard | `keyboard.py` | `KeyboardRouter`, teclas 1-9/P/X/U, modo subcuarto con pending_parent |
| Probe | `probe.py` | ffprobe: fps, rotación, audio, width/height ajustado por rotación |
| UI — Dialog | `ui/room_config_dialog.py` | Chips toggleables de 17 cuartos + campo personalizado |
| UI — Filmstrip | `ui/filmstrip.py` | Fila de miniaturas con bordes verde/rosa/azul |
| UI — Window | `ui/main_window.py` | Cascarón vacío con columnas |
| UI — Entry | `app.py` | `arrancar()` + `main()`, restauración de sesión |
| Pyproject | `pyproject.toml` | Build config + `pip install -e .` para evitar PYTHONPATH |

### Fase 2 — Flujo funcional completo (tarde, 11 tareas, +29 tests = 124)

- **M1 Reproducción embebida:** `VideoWidget` con mpv por `wid`, `WA_NativeWindow` + `WA_OpaquePaintEvent`, player creado en `showEvent` tras `winId()`.
- **M2 Arranque real:** diálogo de cuartos → `arrancar()` → `MainWindow` con selección.
- **M3 Ingest a UI:** botón "Importar carpetas…", `ffprobe` para fps real, miniaturas en `QThreadPool(maxThreadCount=1)`, teclado con `QShortcut`.
- **M4 Clasificación completa:** subcuartos creados en vivo con diálogo `QInputDialog`, borde azul del clip actual en filmstrip, contadores de clips por cuarto.
- **M5 Persistencia y export:** autoguardado en cada acción (cuarto/flag/in/out/navegación), restauración al arrancar, botón "Exportar manifest…" con aviso no bloqueante de clips sin clasificar.
- **M6 Cierre:** 124 tests en verde, smoke end-to-end con material real de `TEST/clips/`.

**29 commits en `master`**, mensajes en español, un commit por tarea.

---

## 4. Bugs corregidos en esta sesión (8 de flujo + 5 de calidad)

### 4.1 Bugs que impedían usar la app

| # | Síntoma | Causa | Archivo | Fix |
|---|---|---|---|---|
| 1 | Botón "Empezar a clasificar →" no hacía nada | `QPushButton` sin `clicked.connect(self.accept)` | `room_config_dialog.py:48` | Agregado `self.start_button.clicked.connect(self.accept)` |
| 2 | Importar carpeta no cargaba clips ni mostraba filmstrip | `_on_import_folders` no llamaba a `_load_clips_from_ingest()` | `main_window.py:363` | Agregado `self._load_clips_from_ingest()` al final |
| 3 | Crash `FileNotFoundError` al primer autosave | `save_session` no creaba directorio `~/.clasificador_video/` | `autosave.py:16` | `path.parent.mkdir(parents=True, exist_ok=True)` |
| 4 | El crash de autosave rompía todo el flujo | `_autosave()` sin try/except | `main_window.py:196` | Envuelto en `try/except OSError` |
| 5 | mpv abría ventana separada en vez de embeberse | `winId()` no válido sin `WA_NativeWindow` + force | `video_widget.py:27` | `setAttribute(Qt.WA_NativeWindow)` + `self.winId()` antes de crear player |
| 6 | mpv dibujaba sobre fondo transparente | Sin `WA_OpaquePaintEvent` ni `setAutoFillBackground` | `video_widget.py:28-29` | Ambos atributos agregados |
| 7 | Test `importar_carpetas_puebla_el_ingest_list` fallaba | Archivo vacío (`touch`) lanzaba `CalledProcessError` en ffprobe | `test_main_window.py:112` | Mock `_load_clips_from_ingest` en ese test |
| 8 | Test `test_cambiar_calidad` y 5 más fallaban | `QTimer.singleShot` difería creación del player, tests no esperaban | `video_widget.py:37` | Player creado directo en `showEvent`, no diferido |

### 4.2 Bugs de calidad corregidos

| # | Bug | Archivo:línea | Fix |
|---|---|---|---|
| B1 | CSS `border-color` múltiple: solo el último se aplicaba visualmente. Pick/reject invisible en clip actual | `filmstrip.py:49` | `border` para flag, `outline` para current (ambos visibles) |
| B2 | `_handle_subroom_key` no llamaba `_autosave()` al resolver subcuarto conocido | `main_window.py:271` | `_autosave()` agregado |
| B3 | `attach_subroom_or_resolve` no llamaba `_autosave()` al crear subcuarto nuevo | `main_window.py:321` | `_autosave()` agregado |
| B4 | `except Exception: pass` en `_autosave` tragaba errores reales | `main_window.py:198` | Acotado a `except OSError` |
| B5 | Restauración de sesión: clips cargados pero player vacío (primer clip nunca se abre) | `app.py:91` | `window.open_clip()` después de `window.show()` |

---

## 5. Estructura actual del código

```
src/clasificador_video/
├── __init__.py
├── app.py               # Entry point: arrancar() + main() + restauración sesión
├── autosave.py          # save_session (atómico) + load_session
├── category_path.py     # CategoryTree: subcuartos por padre
├── ingest.py            # IngestTree: carpetas top-level, filtro extensiones
├── keyboard.py          # KeyboardRouter: 1-9/P/X/U + pending_parent
├── manifest.py          # Clip + Manifest dataclasses, to_dict, write_json
├── models.py            # ClipSpec (información interna del clip, no se usa en UI actual)
├── player.py            # MpvPlayer: hwdec=videotoolbox, calidad, in/out
├── probe.py             # ffprobe: fps, rotación, audio, duración
├── proxy_match.py       # match_proxies: empareja originals ↔ proxies S03
├── rate.py              # FPS helpers para XMEML (legacy)
├── rooms.py             # RoomSelection + 17 cuartos maestros
├── thumbnails.py        # extract_thumbnail con mpv --vo=image
├── xmeml.py             # Generador XMEML (legacy, no usado por la app)
└── ui/
    ├── __init__.py
    ├── filmstrip.py     # Filmstrip + ClipThumbnail + _ClipItemWidget
    ├── main_window.py   # MainWindow: layout, navegación, teclado, import/export
    ├── room_config_dialog.py  # Diálogo de chips toggleables previo a clasificar
    └── video_widget.py  # VideoWidget: mpv embebido vía wid
```

```
tests/
├── test_app.py
├── test_autosave.py
├── test_category_path.py
├── test_ingest.py
├── test_keyboard.py
├── test_manifest.py
├── test_models.py
├── test_player.py
├── test_probe.py
├── test_proxy_match.py
├── test_qt_smoke.py
├── test_rate.py
├── test_rooms.py
├── test_thumbnails.py
├── test_xmeml_*.py         (7 archivos, legacy)
└── ui/
    ├── test_filmstrip.py
    ├── test_main_window.py
    ├── test_room_config_dialog.py
    └── test_video_widget.py
```

**Suite:** `pytest -v` → **124 passed, 0 failures.**

---

## 6. Contrato con el plugin UXP

El manifest JSON que exporta la app tiene este formato exacto (definido en `manifest.py:Clip.to_dict()`):

```json
{
  "proyecto": "Casa Jardin",
  "orientacion": "horizontal",
  "clips": [
    {
      "orden": 1,
      "ruta": "/path/to/C0001.MP4",
      "categoria_path": ["Sala"],
      "fps": 59.94,
      "in_frame": null,
      "out_frame": null,
      "flag": "none",
      "ruta_proxy": null
    }
  ]
}
```

El plugin UXP (`uxp-plugin/processManifest.js`) lee cada clip y:
- Crea/reusa bins anidados por `categoria_path`
- Importa o reusa el clip por `ruta`
- Aplica label Forest (pick) / Rose (reject) según `flag`
- Aplica in/out en frames usando `fps`
- Adjunta proxy si `ruta_proxy != null`

**Validado:** el formato coincide con los fixtures de test del plugin.

---

## 7. Lo que funciona (flujo completo)

1. `.venv/bin/python -m clasificador_video.app` abre el diálogo de cuartos
2. Seleccionar cuartos con chips toggleables → "Empezar a clasificar →"
3. Ventana principal: columna de cuartos (izq), reproductor mpv (centro), filmstrip (abajo)
4. Botón "Importar carpetas…" → elegir carpeta → ffprobe + carga clips + miniaturas en background
5. Teclado: `1-9` cuartos, `Espacio` play/pause, `← →` navegar, `I/O` in/out, `P/X/U` pick/reject
6. Subcuartos: tecla de cuarto numerado → segunda tecla para subcuarto (Baño/Closet/Terraza)
7. Filmstrip: borde verde pick, rosa reject, azul clip actual, ambos visibles simultáneamente
8. Contadores de clips por cuarto en la columna izquierda
9. Autoguardado atómico en cada acción de clasificación
10. Restauración de sesión al reabrir la app (pregunta si recuperar)
11. Botón "Exportar manifest…" → JSON con formato exacto del plugin + aviso de clips sin clasificar

---

## 8. Limitaciones conocidas (no bugs, decisiones de diseño)

- **Subcuartos solo para cuartos numerados** (Recámara 1, Baño 1). Cuartos simples nunca entran en modo subcuarto.
- **Restauración de sesión simplificada**: cuartos repetibles se restauran como nombres fijos, pierden la semántica de "cuartos repetibles". Funciona igual.
- **Miniaturas 1 a la vez en software** (~1s/clip). Optimización con hardware compartido pendiente para shootings grandes.
- **`wid` embedding sin overlays**: mpv dibuja en su propia superficie, no se puede componer UI de Qt encima del video.
- **Sin punto de color en esquina del filmstrip** (spec §4).
- **Sin indicador "Autoguardado hace Ns"** (spec §3).
- **Orientación hardcodeada `"horizontal"`** en el manifest.
- **Sin deshacer (Ctrl+Z)**, la leyenda lo anuncia pero no existe.
- **Sin drag-and-drop** de carpetas.
- **Sin UI de proxies** (clic derecho → "Buscar proxies").
- **Nombre de proyecto fijo** "Shooting sin nombre".
- **Importar solo una carpeta a la vez** (el spec pide selección múltiple).

---

## 9. Plan de Fase 3 (ya escrito)

Archivo: `docs/superpowers/plans/2026-08-06-app-externa-clasificador-fase3.md`

**7 milestones** que cubren las limitaciones de la sección 8:
1. Nombre de proyecto configurable
2. Orientación automática del manifest
3. UI de proxies (clic derecho en panel de ingest)
4. Deshacer multinivel (Ctrl+Z)
5. Drag-and-drop de carpetas
6. Punto de color en filmstrip + indicador de autoguardado
7. Cierre: suite verde + smoke final

---

## 10. Cómo ejecutar

```bash
cd "<RAIZ-DEL-REPO>"

# Instalar (una vez)
.venv/bin/pip install -e .

# Ejecutar la app
.venv/bin/python -m clasificador_video.app

# Ejecutar tests
.venv/bin/pytest -v

# Material de prueba
ls TEST/clips/   # 3 clips HEVC de la FX30: .MP4
```

---

## 11. Archivos modificados en esta sesión (no commiteados)

```
src/clasificador_video/app.py                   (+5)  — open_clip después de show()
src/clasificador_video/autosave.py              (+1)  — mkdir parents
src/clasificador_video/ui/filmstrip.py          (±15) — CSS: border + outline
src/clasificador_video/ui/main_window.py        (±30) — autosave en subcuartos, except OSError, _load_clips_from_ingest
src/clasificador_video/ui/room_config_dialog.py (+1)  — clicked.connect(self.accept)
src/clasificador_video/ui/video_widget.py       (+7)  — WA_NativeWindow + winId()
tests/ui/test_filmstrip.py                      (±10) — tests actualizados al nuevo CSS
tests/ui/test_main_window.py                    (+1)  — mock _load_clips_from_ingest
```

Próximo paso recomendado: ejecutar la Fase 3 desde el plan ya escrito, o verificar el ciclo end-to-end con Premiere real (punto 6 del plan fase 2).
