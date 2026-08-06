# Informe — Reconstrucción v2 (embedding de video + diseño), autónomo — 2026-08-06 madrugada

Este documento es el cierre del trabajo pedido en
`docs/superpowers/HANDOFF-2026-08-06-arreglar-video-y-diseno.md`. Se ejecutó de
punta a punta sin pausas para pedir permiso, siguiendo ese handoff al pie de
la letra. Bruno estaba dormido; esto es para que lo lea al despertar.

## 1. Qué se hizo, en una frase

Se reconstruyó el embedding de video sobre el **API de render de mpv**
(`vo=libmpv` + `QOpenGLWidget`), reemplazando el enfoque por `wid` que abría
una ventana de mpv aparte, y se corrigieron los 4 bugs de diseño visual
reales. Todo verificado con `grab()` + inspección real de la imagen, no por
logs.

## 2. Qué se reusó de v1 tal cual (sección 2 del handoff)

Sin cambios, ni un archivo tocado:

- `manifest.py`, `autosave.py`, `rooms.py`, `category_path.py`, `ingest.py`,
  `proxy_match.py`, `keyboard.py`, `probe.py`, `thumbnails.py`.
- `models.py`, `rate.py`, `xmeml.py` — siguen inertes, no tocados (legacy).

Verificado con `git diff 784c761 HEAD --stat`: ninguno de estos aparece en el
diff.

## 3. Qué se reconstruyó

### 3.1 `player.py`
`MpvPlayer` ya no acepta `wid`. Siempre usa `vo="libmpv"` (habilita el modo
render-API) y se agregó `keep_open="always"` — sin esto, mpv descarga el
archivo al llegar a EOF y el widget vuelve a quedar negro; los clips de
`TEST/` duran 2-6s, muy poco para que un `QTest.qWait` razonable evite el
EOF. Se agregó la propiedad `mpv_handle` para que `VideoWidget` conecte el
API de render sin exponer más superficie de `MpvPlayer`.

### 3.2 Spike aislado del embedding (`ui/video_widget.py`)
Se construyó primero un script mínimo fuera de la app (`QOpenGLWidget` +
`MpvRenderContext`, sin `MainWindow` ni nada más) y se verificó **mirando la
imagen real** con `grab()`, siguiendo la sección 5 del handoff. Dos bugs
reales se encontraron y corrigieron ahí mismo, antes de tocar la app:

1. **Sin `QSurfaceFormat` de perfil OpenGL Core ≥ 3.3**, mpv rechazaba el
   contexto (`need >= OpenGL 3.0 for core rectangle texture support`) y no
   dibujaba nada — el widget quedaba negro. Se agregó
   `configure_gl_surface_format()` en `app.py`, llamado antes de crear la
   `QApplication`.
2. **`defaultFramebufferObject()` está en píxeles físicos, pero
   `width()`/`height()` de Qt son lógicos.** En la pantalla Retina de esta
   Mac, sin corregir por `devicePixelRatioF()`, mpv solo pintaba la esquina
   inferior izquierda del widget (un cuarto del área real). Corregido
   multiplicando por el ratio en `paintGL()`.

Con ambos fixes, un clip real de `TEST/clips/` se ve completo y centrado
dentro del widget — confirmado visualmente, no por logs.

Una vez verificado el spike, se integró a `VideoWidget` real:
- `vo="libmpv"` + `MpvRenderContext` conectado vía `get_proc_address` (bridge
  a `QOpenGLContext.currentContext()`).
- El callback `update_cb` de mpv corre en un hilo de mpv, no el de Qt — solo
  emite una señal Qt (`frame_ready`, en una clase auxiliar `_FrameReadySignal`,
  ver 3.3), nunca pinta directo.
- El `MpvPlayer` se crea perezosamente (al primer acceso a `.player`, no en
  `__init__` ni en `show()`) para no abrir hilos de mpv reales de más en
  pruebas que nunca tocan video.

### 3.3 El crash nativo (sección 3.2 del handoff) — causa real encontrada
El crash (`Bus error` / `Segmentation fault` en
`PySide::MetaObjectBuilder::parsePythonType`, siempre dentro de
`_install_shortcuts` al construir un `QShortcut`) **sí reaparecía** al
integrar el API de render, reproducible al 100% corriendo la suite completa.

Investigación (bisección con reproducciones aisladas, documentada en el
proceso):
- Crear 60 `MainWindow` reales seguidas, o 10 `VideoWidget` con video
  seguidos, **por separado no crasheaba**.
- La causa real: varios tests de `tests/ui/test_main_window.py` llaman
  `window.show()` + `qtbot.waitExposed(window)`, lo que dispara `initializeGL()`
  de verdad. Ahí se llamaba `mpv.MpvRenderContext(self.player.mpv_handle, ...)`
  con un **doble de prueba** (`FakeMpv`) que no tiene el atributo `.handle`
  real que expone `mpv.MPV`. Eso lanzaba un `AttributeError` **de Python, no
  capturado, dentro de un override de método virtual de Qt** (`initializeGL`,
  invocado desde C++). Esa excepción sin capturar dejaba al proceso en un
  estado que crasheaba más tarde, en una llamada completamente distinta
  (`QShortcut.__init__`) — el patrón clásico de un síntoma que aparece lejos
  de la causa real.
- Fix aplicado en dos frentes:
  1. `initializeGL()` ahora captura `AttributeError` al crear el
     `MpvRenderContext` — si el handle no es un `mpv.MPV` real (un doble de
     pruebas), simplemente no hay contexto de render que crear, sin
     propagar la excepción a través del límite C++/Python.
  2. Se encontró un bug real y separado en `tests/test_app.py`: varias
     pruebas pasaban `video_factory=None`, que en la práctica construye un
     **mpv real** (con su hilo de eventos real) porque `VideoWidget()` cae a
     `_default_mpv_factory` cuando el factory es `None`/falsy. Se inyectó un
     doble de mpv (`_FakeMpv`) en todas esas pruebas, evitando abrir hilos
     de mpv reales de más entre pruebas.
  3. Por indicación del propio handoff (mitigación sugerida en la sección
     3.2), la señal `frame_ready` se movió a una clase auxiliar
     `_FrameReadySignal(QObject)` en vez de declararse a nivel de clase
     directamente en `VideoWidget` (subclase de `QOpenGLWidget`) — aplicado
     como higiene adicional aunque el fix #1 fue el que realmente eliminó el
     crash en las pruebas realizadas.

También se removieron los `try/except RuntimeError` en `main_window.py` y
`app.py` que v1 usaba para tolerar que el player no existiera todavía (ya no
aplica: el player nunca lanza, se crea perezosamente).

**Verificación**: suite completa corrida repetidamente — 8+ corridas
consecutivas de principio a fin, más corridas aisladas de subconjuntos
(`tests/ui/test_main_window.py` solo, `tests/ui/` completo, combinaciones en
distinto orden) — sin que el crash reapareciera ni una vez. 152 pruebas en
verde, consistente.

### 3.4 Los 4 bugs de diseño visual (sección 3.3 del handoff)
Corregidos desde el tema visual, verificados con `grab()` real (no por los
tests, que en el primer intento del bug 1 seguían en verde con el bug aún
visible en pantalla — ver nota abajo):

1. **Doble caja en el filmstrip.** `_ClipItemWidget` (contenedor de
   miniatura + nombre de cuarto) es un `QWidget` plano; sin
   `WA_StyledBackground` no pinta su propio borde por QSS y la propiedad se
   hereda a los `QLabel` hijos, que la pintan cada uno por separado. Fix:
   `WA_StyledBackground` + `objectName("clipItem")` en el contenedor.
   **Nota de proceso real**: el primer intento de fix (mezclar en una sola
   cadena una regla "sin selector" —implícita para el propio widget— con
   una regla `QLabel {...}`) hizo pasar los tests pero **seguía mostrando
   tres cajas en pantalla** al verificar con `grab()`. El fix real necesitó
   selectores explícitos por `objectName` para ambos: `#clipItem { ... }` y
   `#clipItem QLabel { border: none; }`. Esto confirma en la práctica la
   instrucción del handoff de no confiar solo en que los tests pasen.
2. **Botón "Importar carpetas…" invisible como botón** (mismo fondo que el
   panel). Fix: `objectName("importButton")` + regla QSS con fondo
   distinto (`BG_HOVER` + borde sutil).
3. **Carpeta importada sin título.** Fix: `QLabel` "Material importado" con
   el mismo estilo `panelTitle` que ya usaban los demás encabezados.
4. **Leyenda de teclado genérica** ("1-9 cuartos"). Fix: `_build_legend_text()`
   construye la leyenda real desde `room_selection.active_rooms()` (p. ej.
   "1 Sala 2 Cocina 3 Recámara 1 4 Recámara 2 | Espacio play/pause | ..."),
   llamada tanto al construir la ventana como al restaurar una sesión
   guardada (que puede traer una selección de cuartos distinta).

## 4. Verificación visual realizada (sección 5 del handoff)

Con `grab()` + lectura real de la imagen (herramienta de lectura de
archivos), no por logs, se confirmó:

- **Un clip real** de `TEST/clips/20260804_PIB0589.MP4` (60 fps, HEVC-ish,
  vertical 2160×3840) se ve embebido, completo y centrado dentro del
  `VideoWidget` real, dentro de una `MainWindow` real con tema oscuro
  aplicado.
- **Ninguna ventana de mpv aparte**: `app.topLevelWidgets()` durante la
  ejecución solo reporta la `MainWindow` (más un `QFrame` interno de Qt,
  invisible, no relacionado con mpv) — nunca una segunda ventana. Confirmado
  también a nivel de sistema operativo (`System Events` no reporta ninguna
  ventana con "mpv"/"libmpv" en el nombre durante la ejecución).
- **Diálogo de cuartos** (`RoomConfigDialog`) verificado visualmente: chips
  seleccionables, botón "Empezar a clasificar →" con estilo de acento.
- **Filmstrip con clips clasificados** (pick verde, reject rosa, sin
  clasificar) verificado visualmente: una sola caja por clip, envolviendo
  miniatura + nombre de cuarto.
- **Los 4 bugs de diseño**, verificados corregidos en la misma captura de la
  ventana completa: botón de importar visible, encabezado "Material
  importado", leyenda con cuartos reales, filmstrip con una sola caja.

## 5. Contrato del manifest (sección 6 del handoff)

No tocado. `manifest.py` no se modificó; las llaves y tipos del JSON
(`proyecto`, `orientacion`, `clips[].orden/ruta/categoria_path/fps/
in_frame/out_frame/flag/ruta_proxy`) son exactamente los mismos que ya
estaban validados contra `uxp-plugin/processManifest.js`.

## 6. Estado final vs. la definición de "terminado" (sección 8 del handoff)

| Requisito | Estado |
|---|---|
| Video visible embebido de verdad (verificado por imagen) | ✅ Confirmado con `grab()` + inspección real |
| Ninguna ventana de mpv aparte | ✅ Confirmado por `topLevelWidgets()` y a nivel SO |
| Suite completa pasa repetidamente sin el crash nativo | ✅ 152 pruebas, 8+ corridas consecutivas + subconjuntos, sin crash |
| Los 4 bugs de diseño corregidos y verificados visualmente | ✅ Los 4, con capturas reales |

**No queda nada pendiente ni bloqueado de lo pedido en el handoff.**

## 7. Commits de esta sesión (en orden)

1. `refactor: MpvPlayer usa vo=libmpv y keep_open en vez de wid`
2. `feat: VideoWidget embebe mpv via API de render de mpv (QOpenGLWidget)`
3. `fix: corrige los 4 bugs de diseno visual reales de v1`
4. `fix: el fix del bug de doble caja del filmstrip no funcionaba de verdad`

Rama `master`, sin push (no autorizado). Working tree limpio al cierre.

## 8. Cosas que Bruno debería saber, no bugs

- El `git stash` mencionado en el handoff original (`stash@{0}`) sigue en el
  stash, no se aplicó ni se descartó — es historial de una investigación a
  medias, ya no hace falta pero tampoco estorba.
- La ventana `QFrame` invisible que aparece en `topLevelWidgets()` junto a
  `MainWindow` es un artefacto interno de Qt (no relacionado con mpv);
  aparece incluso en apps Qt sin ningún video. No es un bug.
- Todos los clips de `TEST/` duran 2-6 segundos. Si se prueba la app en vivo
  con material real de un shooting (que dura minutos), el comportamiento de
  `keep_open` es igual de correcto pero se notará menos porque el EOF tarda
  mucho más en llegar.
- Quedan pendientes las limitaciones de diseño ya documentadas en
  `docs/superpowers/HANDOFF-2026-08-06-auditoria-bugs.md` sección 9 (deshacer,
  drag-and-drop, UI de proxies, orientación automática, etc.) — son fase 3,
  no parte de este handoff.
