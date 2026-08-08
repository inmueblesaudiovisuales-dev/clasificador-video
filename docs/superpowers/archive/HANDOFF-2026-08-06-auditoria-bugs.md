# Handoff — Sesión de Auditoría de Bugs — Clasificador de Video (2026-08-06 noche)

## Instrucciones para la IA

**Tu única misión:** hacer loops de auditoría exhaustiva de bugs sobre este proyecto hasta que no quede **ni un solo bug de ningún tipo** y la app funcione **perfectamente de punta a punta**.

### Protocolo de auditoría (LOOP hasta cero bugs)

```
LOOP:
  1. LEE este documento completo. Entiende la arquitectura, el flujo, los contratos y las limitaciones.
  2. EJECUTA `.venv/bin/pytest -v --tb=short` para establecer la línea base (deben ser 137+ tests, 0 failures).
  3. AUDITA cada módulo fuente (src/) contra:
     a. Su spec en este documento (sección 3 — contratos por módulo).
     b. Riesgos conocidos (sección 7).
     c. Edge cases: clips sin audio, clips verticales, clips sin ffprobe, sesión corrupta, paths con espacios, paths con acentos, rutas de red, archivos sin permisos, 0 clips, 1000+ clips, diálogo cancelado, sesión restaurada sin clips, mpv no disponible, etc.
     d. Race conditions: QThreadPool + señales, autosave concurrente, showEvent vs player creation, closeEvent vs thumbnails.
     e. Leaks: widgets no removidos, pixmaps sin liberar, señales no desconectadas, recursos de mpv sin destruir.
  4. REPRODUCE bugs manualmente si es posible: `.venv/bin/python -m clasificador_video.app` con material de `TEST/clips/`.
  5. POR CADA BUG ENCONTRADO:
     a. Escribe un test que falle (TDD).
     b. Corrige el código fuente.
     c. Verifica que el test pase Y que ningún otro test se rompa.
     d. Commitea con mensaje `fix: <descripción del bug>`.
  6. REPITE desde el paso 2 hasta que no encuentres NI UN SOLO BUG NUEVO en dos pasadas completas.
  7. Cuando termines, ACTUALIZA la sección 8 de este documento con los bugs encontrados y corregidos.
```

**Reglas:**
- No pidas permiso. No te detengas a preguntar. Haz todo.
- Un commit por bug corregido (TDD: test primero, code fix después, commit).
- Si un bug requiere una decisión de diseño que no está cubierta en este doc ni en los specs, documéntalo como limitación en la sección 8 y sigue adelante.
- No rompas los 137 tests existentes. Si un fix rompe algo, arréglalo.
- Si llevas 3 loops sin encontrar bugs, considera que terminaste y escribe el reporte final.

---

## 1. Resumen del proyecto

App externa del **Clasificador de Video para Bienes Raíces** — una herramienta que permite a un editor de video clasificar clips de video por teclado (cuarto por cuarto) y exportar un manifest JSON que un plugin UXP de Adobe Premiere consume para armar automáticamente bins, labels e in/out points.

**Stack:** Python 3.14, PySide6 (Qt 6.11), python-mpv (libmpv), ffprobe, pytest + pytest-qt.

**137 tests en verde, 37 commits en `master`.**

**Ruta del repo:** `/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO`

---

## 2. Arquitectura detallada

### 2.1 Componentes y responsabilidades

| Módulo | Archivo | Responsabilidad | Dependencias |
|--------|---------|----------------|--------------|
| **Entry point** | `app.py` | `main()`: crea `QApplication`, aplica tema oscuro global, abre diálogo de cuartos, lanza ventana principal, restaura sesión. | `ui/main_window`, `ui/room_config_dialog`, `ui/theme`, `autosave` |
| **MainWindow** | `ui/main_window.py` | Ventana única: columna izq (cuartos + ingest), centro (reproductor mpv), abajo (filmstrip + leyenda). Orquesta clasificación por teclado, importación, autosave, export. | `rooms`, `category_path`, `keyboard`, `ingest`, `probe`, `thumbnails`, `manifest`, `player`, `autosave` |
| **RoomConfigDialog** | `ui/room_config_dialog.py` | Diálogo previo: chips toggleables de 17 cuartos maestros + cuarto personalizado + botón aceptar. | `rooms` |
| **Filmstrip** | `ui/filmstrip.py` | Fila horizontal de `_ClipItemWidget`: miniatura (QPixmap) escalada a 80px alto × 140px máx ancho, borde verde/rosa/azul, nombre de cuarto debajo. | Ninguna (solo PySide6) |
| **VideoWidget** | `ui/video_widget.py` | Widget que embebe mpv: `WA_NativeWindow`, `paintEvent` manual (fondo negro sin QSS), player creado en `showEvent` con `wid=int(self.winId())`. | `player` |
| **MpvPlayer** | `player.py` | Envoltura de python-mpv: `hwdec=videotoolbox`, `wid` opcional, pause inicial explícito, selector de calidad (Full/1/2/1/4/1/8), mark in/out por time_pos. | python-mpv |
| **Theme** | `ui/theme.py` | Constantes de color (oscuras) + `build_stylesheet()`: QSS global aplicado una vez sobre `QApplication`. | Ninguna |
| **Manifest** | `manifest.py` | Dataclasses `Clip`/`Manifest`, formato JSON §11 exacto (`orden ruta categoria_path fps in_frame out_frame flag ruta_proxy`). | Ninguna |
| **Autosave** | `autosave.py` | Guardado atómico: escribe a temp, `os.replace` al destino. Crea `~/.clasificador_video/` si no existe. | Ninguna |
| **Rooms** | `rooms.py` | `RoomSelection`: 17 cuartos maestros, toggle, numeración automática (Recámara 1, Recámara 2...), cuartos personalizados. | Ninguna |
| **CategoryTree** | `category_path.py` | Subcuartos creados perezosamente por padre: `path_for(parent, subroom=...)`, `attach_subroom`, `known_subrooms_for`. | Ninguna |
| **Keyboard** | `keyboard.py` | `KeyboardRouter`: números 1-9 → cuartos, modo subcuarto con `pending_parent`, P/X/U → pick/reject. | `rooms` |
| **Ingest** | `ingest.py` | `IngestTree`: carpetas top-level con archivos filtrados por extensión (.mp4/.mov/.mxf/.lrf), renombrado de carpetas. | Ninguna |
| **Probe** | `probe.py` | `probe_clip(path) → dict`: ejecuta ffprobe, extrae fps, rotación, width/height ajustado por rotación, has_audio, duration. | ffprobe |
| **Thumbnails** | `thumbnails.py` | `extract_thumbnail(video, start, outdir)`: ejecuta `mpv --vo=image` en software (sin hwdec), devuelve Path del jpg. | mpv CLI |
| **Proxy Match** | `proxy_match.py` | `match_proxies(originals, proxies) → dict`: empareja por stem + sufijo S03. | Ninguna |

### 2.2 Árbol de archivos

```
src/clasificador_video/
├── __init__.py
├── app.py                  # Entry point: main() + arrancar() + restauración
├── autosave.py             # save_session (atómico) + load_session
├── category_path.py        # CategoryTree: subcuartos por padre
├── ingest.py               # IngestTree: carpetas top-level
├── keyboard.py             # KeyboardRouter: 1-9/P/X/U + pending_parent
├── manifest.py             # Clip + Manifest dataclasses
├── models.py               # ClipSpec (legacy, no usado por la UI actual)
├── player.py               # MpvPlayer: hwdec=videotoolbox, calidad, in/out
├── probe.py                # ffprobe: fps, rotación, audio, duración
├── proxy_match.py          # match_proxies: empareja originals ↔ proxies
├── rate.py                 # FPS helpers para XMEML (legacy)
├── rooms.py                # RoomSelection + 17 cuartos maestros
├── thumbnails.py           # extract_thumbnail con mpv --vo=image (software)
├── xmeml.py                # Generador XMEML (legacy, no usado por la app)
└── ui/
    ├── __init__.py
    ├── filmstrip.py        # Filmstrip + ClipThumbnail + _ClipItemWidget
    ├── main_window.py      # MainWindow: layout, navegación, teclado, import/export
    ├── room_config_dialog.py  # Diálogo de chips toggleables
    ├── theme.py            # build_stylesheet() + constantes de color oscuras
    └── video_widget.py     # VideoWidget: mpv embebido vía wid

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
├── test_xmeml_*.py (7 archivos, legacy)
└── ui/
    ├── test_filmstrip.py
    ├── test_main_window.py
    ├── test_room_config_dialog.py
    ├── test_theme.py
    └── test_video_widget.py
```

---

## 3. Contratos por módulo (lo que cada pieza DEBE cumplir)

### 3.1 app.py
- `main()` usa `QApplication.instance() or QApplication(sys.argv)` — nunca crea una segunda QApplication (pytest-qt ya tiene una).
- `app.setStyleSheet(build_stylesheet())` se aplica UNA vez, global.
- `arrancar()` devuelve `None` si el diálogo se cancela.
- Si `window.clips` existe, abre el primer clip en el reproductor tras `window.show()`.
- La sesión se restaura preguntando al usuario (`QMessageBox.question`).

### 3.2 main_window.py (∼400 líneas, el archivo más complejo)
- **Layout:** columna izquierda (QLabel "Cuartos" + room_list + import_button + ingest_list) envuelta en `QWidget#roomColumn`, centro `VideoWidget#videoWidget`, abajo `Filmstrip#filmstripPanel` + `QLabel#legendLabel`.
- **Importación:** `_on_import_folders()` → `QFileDialog` → `ingest_tree.import_folder()` → `_refresh_ingest_list()` → `_load_clips_from_ingest()`.
- **Carga de clips:** `_load_clips_from_ingest()` → ffprobe por clip → `Clip` con fps real → `load_clips()` → `_schedule_thumbnails()`.
- **Navegación:** `handle_arrow("next"/"prev")` → cambia `current_index` → `video_widget.open_clip()` → `_refresh_filmstrip()`.
- **Clasificación:** `handle_key_press(key)` → `KeyboardRouter.resolve_room_key/action_key` → muta `current_clip` → `_refresh_filmstrip()` + `_autosave()`.
- **Subcuartos:** solo para cuartos numerados (con dígito al final). `pending_parent` → segunda tecla → `attach_subroom_or_resolve()` o subcuarto conocido.
- **Export:** `_on_export_manifest()` → aviso de clips sin clasificar (no bloqueante) → `QFileDialog.getSaveFileName` → `Manifest.write_json()`.
- **Autosave:** se dispara en TODA acción de clasificación (cuarto, flag, in/out, navegación, subcuarto). Envuelto en `try/except OSError`.
- **Contadores:** `_refresh_room_counts()` usa `Counter` sobre `clip.categoria_path[0]` de cada clip.
- **Atributos clave:** `video_widget` (objectName="videoWidget"), `export_button` ("exportButton"), `legend_label` ("legendLabel"), `status_label` ("statusLabel"), `room_title_label` ("panelTitle"), `filmstrip` ("filmstripPanel").

### 3.3 video_widget.py
- `setAttribute(Qt.WA_NativeWindow, True)` garantiza `winId()` válido en macOS.
- `paintEvent` pinta fondo negro MANUALMENTE con `QPainter.fillRect(Qt.black)` — NO llama a `super().paintEvent()` (evita que el QSS pinte encima de mpv).
- Player se crea en `showEvent`, después de `self.winId()` — nunca antes.
- `player` property lanza `RuntimeError` si se accede antes de mostrar el widget.
- mpv NO recibe `vo=libmpv` (rompe `hwdec=videotoolbox` en macOS). Solo recibe `wid` y `hwdec`.

### 3.4 player.py
- `MpvPlayer.__init__`: kwargs base = `{"hwdec": "videotoolbox"}`. Si `wid` no es None: `kwargs["wid"] = wid`.
- `self._mpv.pause = True` explícito — estado inicial definido.
- `mark_in(fps)`: `round(self._mpv.time_pos * fps)`, devuelve el frame.
- `mark_out(fps)`: ídem.
- `set_quality(profile)`: debe ser uno de `QUALITY_PROFILES`, sino `ValueError`.

### 3.5 filmstrip.py
- `_ClipItemWidget._image_label.setFixedHeight(THUMB_HEIGHT=80)`.
- `set_pixmap(pixmap)`: escala con `Qt.KeepAspectRatio` + `Qt.SmoothTransformation` a `THUMB_MAX_WIDTH=140` × `THUMB_HEIGHT=80`.
- `set_visual_state(is_current)`: pick → `border: 2px solid #3bb273`, reject → `#e0556f`, current solo → `#2b7fff`, current+flag → border flag + `outline: 2px solid #2b7fff`.
- `_room_label.setObjectName("clipRoomLabel")`.

### 3.6 theme.py
- `build_stylesheet()`: devuelve string QSS con selectores por `objectName` (`#videoWidget`, `#startButton`, `#exportButton`, `#roomColumn`, `#filmstripPanel`, `#panelTitle`, `#legendLabel`, `#statusLabel`, `#clipRoomLabel`).
- Colores: `BG_WINDOW=#1a1a1e`, `BG_PANEL=#232327`, `ACCENT=#5b9bff`, `TEXT=#dddddd`, `TEXT_MUTED=#8a8a8a`, etc.

### 3.7 room_config_dialog.py
- `start_button.setObjectName("startButton")`.
- `start_button.clicked.connect(self.accept)`.
- Chips: `QPushButton` con `setCheckable(True)`, lambda conectada a `_on_chip_clicked`.

### 3.8 autosave.py
- `save_session(path, data)`: `path.parent.mkdir(parents=True, exist_ok=True)` → escribe JSON a `path.tmp` → `os.replace(tmp, path)`.
- `load_session(path)`: `path.read_text()` → `json.loads()`. Devuelve `None` si no existe o el JSON es inválido.

### 3.9 manifest.py
- `Clip.to_dict()`: llaves exactas `orden ruta categoria_path fps in_frame out_frame flag ruta_proxy`. `ruta` debe ser string (no Path), `in_frame`/`out_frame` deben ser int o null.
- `Manifest.write_json(path)`: escribe JSON con `indent=2, ensure_ascii=False`.

### 3.10 Contracto con el plugin UXP
El JSON exportado debe tener esta forma exacta:
```json
{
  "proyecto": "Casa Jardin",
  "orientacion": "horizontal",
  "clips": [
    {
      "orden": 1,
      "ruta": "/absolute/path/to/C0001.MP4",
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

---

## 4. Flujo completo (lo que la app debe hacer)

1. `.venv/bin/python -m clasificador_video.app`
2. Diálogo oscuro: chips de 17 cuartos, campo personalizado, botón "Empezar a clasificar →" azul.
3. Ventana principal con tema oscuro: columna izq panel oscuro, centro reproductor fondo negro, abajo filmstrip.
4. "Importar carpetas…" → elegir carpeta → ffprobe extrae fps real → clips cargados → miniaturas aparecen en filmstrip (∼1s/clip).
5. Teclado: `Espacio` play/pause, `← →` navegar, `I/O` marcar in/out, `P/X/U` pick/reject/ninguno, `1-9` asignar cuarto.
6. Subcuartos: presionar tecla de cuarto numerado → segunda tecla para Baño/Closet/Terraza.
7. Filmstrip muestra: miniatura escalada, borde verde (pick) / rosa (reject) / azul (clip actual), nombre de cuarto debajo.
8. Columna izq muestra contadores "Sala (3)", "Cocina (1)".
9. Autoguardado en cada acción → `~/.clasificador_video/sesion.json`.
10. Al reabrir: pregunta si recuperar sesión → restaura clips, cuartos, subcuartos, flags, in/out.
11. "Exportar manifest…" → aviso de clips sin clasificar → guarda JSON.
12. El JSON se ve bien (formato correcto, paths absolutos, fps reales, flags correctos).

---

## 5. Cómo ejecutar

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"

# Tests
.venv/bin/pytest -v --tb=short

# App
.venv/bin/python -m clasificador_video.app

# Material de prueba
ls TEST/clips/   # 3 clips HEVC de la FX30: .MP4

# Solo un módulo
.venv/bin/pytest tests/ui/test_main_window.py -v
```

---

## 6. Historial reciente de commits (sesión de diseño visual + fixes de hoy)

```
038a520 fix: quitar vo=libmpv (rompe hwdec en macOS) y evitar que Qt pinte encima de mpv
e765ab2 fix: forzar vo=libmpv para que mpv renderice dentro del widget y no en ventana aparte
fa9ea7e feat: estilo de titulo de panel para el encabezado de la columna de cuartos
09ab7f4 fix: fondo negro del VideoWidget desde su propia clase
7102f92 fix: escalar miniaturas del filmstrip a altura fija
6f02fde feat: nombrar el boton principal del dialogo de cuartos para el tema
81a9f55 feat: nombrar widgets clave de la ventana principal para el tema
9654bda feat: aplicar el tema oscuro globalmente a la aplicacion
6b2129f feat: modulo de tema oscuro con los colores del diseno aprobado
c3843d5 fix: correcciones pendientes de fase 2
```

---

## 7. Riesgos conocidos y áreas de atención para la auditoría

### 7.1 Embedding de mpv (el área más frágil)
- `WA_NativeWindow` debe estar presente para que `winId()` devuelva un handle válido en macOS.
- `paintEvent` manual es crítico: si alguien llama a `super().paintEvent()`, el QSS pinta encima de mpv y el video desaparece.
- El player se crea en `showEvent` — si `showEvent` se llama múltiples veces, ¿se crean múltiples players? **Verificar.**
- `hwdec=videotoolbox` sin `vo` explícito → ¿qué pasa en diferentes versiones de macOS/mpv?
- El `int(self.winId())` en macOS devuelve un puntero a NSView — ¿es siempre válido en `showEvent`?

### 7.2 Concurrencia
- `QThreadPool(maxThreadCount=1)` para miniaturas. `_ThumbnailJob.signals` emite `done` con un `QWidget` como portador de señal. ¿Qué pasa si la ventana se cierra mientras un job está corriendo? `closeEvent` llama a `waitForDone(5000)` — ¿es suficiente?
- `_autosave()` se llama desde múltiples lugares — ¿puede haber race condition entre dos autosaves concurrentes?
- `open_clip` en el hilo principal mientras mpv está inicializándose — ¿maneja bien el `RuntimeError`?

### 7.3 Memoria y recursos
- `Filmstrip.set_clips()` hace `widget.setParent(None)` en widgets viejos. ¿Se destruyen correctamente o se acumulan?
- `QPixmap` en `set_pixmap` — ¿se libera el pixmap anterior?
- mpv player: ¿se destruye correctamente al cerrar la ventana? ¿`__del__` de python-mpv se llama?
- `_thumb_dir` es un `tempfile.mkdtemp` — ¿se limpia al cerrar?

### 7.4 Edge cases de datos
- Clip sin audio: `probe_clip` devuelve `has_audio=False` — ¿el manifest se genera bien?
- Clip con path que contiene caracteres especiales (espacios, acentos, ñ): ¿sobrevive el round-trip autosave → restore?
- Clip con fps no estándar (23.976, 59.94, 120, etc.): ¿el manifest exporta el float correcto?
- Sesión corrupta (JSON mal formado): `load_session` debe devolver `None`, no crashear.
- `~/.clasificador_video/` sin permisos de escritura: `save_session` debe lanzar `OSError`, no colgarse.
- 0 clips en el ingest: ¿el filmstrip se vacía sin crashear?
- Clip vertical (rotación 90/270): ¿ffprobe ajusta width/height? ¿el filmstrip escala bien un frame vertical?
- Clips de diferentes fps en el mismo proyecto: ¿`mark_in` usa el fps correcto del clip actual?

### 7.5 UI y tema
- El QSS global `QWidget { background-color: #1a1a1e; }` afecta a TODOS los widgets. ¿Algún widget queda con fondo incorrecto?
- `QWidget#videoWidget { background-color: black; }` en el QSS — pero el `paintEvent` manual no llama a `super()`, así que este QSS **no se aplica**. ¿Es intencional? (Sí — el fondo negro lo pinta el `paintEvent` manual para no tapar a mpv.)
- `border-radius: 6px` en `#videoWidget` — no recorta el video de mpv (mpv dibuja en el NSView completo, sin máscara). ¿Se ve mal?
- El diálogo `RoomConfigDialog` no aplica el tema oscuro directamente — hereda el QSS global. ¿Los chips se ven bien en oscuro?

### 7.6 Teclado
- `QShortcut` con `Ctrl+Z` — **no existe**. La leyenda lo anuncia pero el shortcut nunca se instala. ¿Es un bug o está planeado para fase 3?
- ¿Qué pasa si el usuario presiona una tecla de cuarto cuando `current_clip` es None?
- ¿Qué pasa si `handle_key_press` recibe una tecla que no es ni dígito ni P/X/U/I/O?

---

## 8. Bugs encontrados y corregidos en esta sesión

*(Esta sección se llena durante la auditoría. Un bug por fila.)*

| # | Síntoma | Causa | Archivo:línea | Fix |
|---|---|---|---|---|
| — | *(pendiente — la auditoría empieza ahora)* | — | — | — |

---

## 9. Limitaciones conocidas (no bugs, decisiones de diseño)

- **Subcuartos solo para cuartos numerados** (Recámara 1, Baño 1). Cuartos simples nunca entran en modo subcuarto.
- **Sin deshacer (Ctrl+Z)**: la leyenda lo anuncia pero no existe — planeado para fase 3.
- **Sin drag-and-drop**: solo botón "Importar carpetas…" — planeado para fase 3.
- **Sin UI de proxies**: `proxy_match.py` existe pero no hay acción de UI — planeado para fase 3.
- **Orientación hardcodeada "horizontal"** en el manifest — planeado para fase 3.
- **Nombre de proyecto fijo** "Shooting sin nombre" — planeado para fase 3.
- **Miniaturas secuenciales en software** (∼1s/clip): decisión por saturación de VideoToolbox.
- **Sin punto de color en esquina del filmstrip** (spec §4): solo borde de color.
- **Sin indicador "Autoguardado hace Ns"** (spec §3): planeado para fase 3.
- **Sin verificación end-to-end con Premiere real**: tarea manual de Bruno.
- **`wid` embedding sin overlays**: no se puede poner UI de Qt encima del video.
- **Importar solo una carpeta a la vez** (el spec pide selección múltiple).

---

## 10. Archivos que NUNCA debes modificar (legacy o externos)

- `xmeml.py` y `tests/test_xmeml_*.py` — generador XMEML legacy, no usado por la app actual.
- `models.py` — `ClipSpec`, no usado por la UI actual.
- `rate.py` — helpers de FPS para XMEML legacy.
- `uxp-plugin/` — plugin de Premiere, proyecto separado.

---

## 11. Plan de fase 3 (ya escrito, NO ejecutar durante la auditoría)

Archivo: `docs/superpowers/plans/2026-08-06-app-externa-clasificador-fase3.md`

Contiene 7 milestones: nombre de proyecto, orientación automática, UI de proxies, deshacer, drag-and-drop, punto de color + autoguardado, cierre. **No ejecutes estas tareas durante la auditoría de bugs** — son features nuevas, no bugs. Si durante la auditoría encuentras que una de estas features es necesaria para que la app "funcione perfectamente", documéntalo aquí pero no la implementes.

---

## 12. Meta final

**Cero bugs. App funcionando perfectamente de punta a punta.** Suite completa en verde. Sin crashes, sin race conditions, sin memory leaks, sin edge cases sin manejar. El flujo descrito en la sección 4 debe funcionar sin un solo fallo.

**Empieza el loop de auditoría ahora.**
