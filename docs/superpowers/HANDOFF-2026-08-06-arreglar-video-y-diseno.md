# Handoff — Reconstruir la app externa (v2), autónomo, sin pedir permiso — 2026-08-06 noche

## Cómo usar este documento — lee esto primero

**Bruno va a estar dormido. No te va a poder contestar nada.** Esto significa:

- **Nunca te detengas a pedir permiso ni a hacer una pregunta y esperar respuesta.** Si algo no está claro, decide con el mejor criterio posible, documenta la decisión en el commit o en el informe final, y sigue adelante. La única excepción real es romper el formato del manifest (spec §11) — eso sí bloquea, ver sección 6 — para todo lo demás, decide y avanza.
- **No te detengas hasta que la app esté funcional de verdad**, no hasta que "las pruebas pasen". Las pruebas con mocks ya pasaron una vez con la reproducción de video rota — eso no es la meta.
- Trabaja en loops: implementa, verifica de verdad (sección 5, "cómo verificar sin poder preguntar"), corrige, repite. No pares en el primer intento que "debería funcionar".

## 1. Qué es esto y qué se decidió hacer

App de escritorio (PySide6) para clasificar clips de video de shootings de bienes raíces por cuarto, marcar entrada/salida y bueno/malo, y exportar un manifest JSON que un plugin de Adobe Premiere (ya terminado, en `uxp-plugin/`, no lo toques) consume para armar el proyecto de edición solo.

Hoy se construyó una primera versión completa (v1) en tres sesiones seguidas. Al probarla en vivo, Bruno encontró que **el video no se reproduce embebido en la ventana — abre una ventana de mpv separada** — y varios problemas de diseño visual reales. Se decidió: **en vez de parchar v1, construir una v2 desde cero**, informada por lo que sí funcionó y lo que no. No es un rechazo total del trabajo de hoy — es reconocer que el enfoque de embedding de video estaba mal desde la raíz (ver sección 3) y que vale más rehacer esa pieza con cuidado que seguir parchándola.

**Estado del repo:** rama `master`, working tree limpio, parado en el commit `2a4fff9`. Hay un `git stash` con un intento a medias mío de arreglar el embedding — puedes leerlo (`git stash show -p`) como referencia de un camino ya explorado (usa el API de render de mpv, la dirección correcta), pero **no lo apliques a ciegas**: en el camino provocó un crash nativo de PySide6 sin resolver. Trátalo como notas de investigación, no como código a heredar automáticamente.

## 2. Qué SÍ funcionó bien en v1 — no lo reconstruyas de cero, reúsalo

Estos módulos de lógica pura (sin Qt) pasaron por TDD completo, no tuvieron ningún bug reportado, y no dependen del embedding de video para nada. Empieza la v2 copiándolos tal cual (o casi):

- `src/clasificador_video/manifest.py` — `Clip`/`Manifest`, formato JSON exacto que el plugin espera. **No cambies el formato.**
- `src/clasificador_video/autosave.py` — guardado atómico (temp + rename).
- `src/clasificador_video/rooms.py` — 17 cuartos maestros, selección con numeración automática.
- `src/clasificador_video/category_path.py` — subcuartos creados perezosamente por padre.
- `src/clasificador_video/ingest.py` — carpetas de nivel superior, filtro por extensión.
- `src/clasificador_video/proxy_match.py` — emparejamiento original↔proxy por sufijo `S03`.
- `src/clasificador_video/keyboard.py` — `KeyboardRouter` (1-9, subcuartos, pick/reject).
- `src/clasificador_video/probe.py` — ffprobe (fps, rotación, duración). Ya existía antes de hoy, es el más probado de todos.
- `src/clasificador_video/thumbnails.py` — miniaturas con `mpv --vo=image` **en software, sin `--hwdec`**. Esto se corrigió hoy por una razón real: varias miniaturas decodificadas por hardware en paralelo saturan VideoToolbox y bloqueaban al reproductor embebido. Mantén esa decisión.

**No toques ni reutilices:** `models.py`, `rate.py`, `xmeml.py` y sus tests — diseño descartado de una arquitectura anterior (xmeml), documentado como inerte en `src/clasificador_video/README.md`.

## 3. Qué NO funcionó — la razón real, para no repetirla en v2

### 3.1 El embedding de video por `wid` está mal desde la raíz

`ui/video_widget.py` de v1 crea el reproductor con `wid=int(self.winId())` — el mecanismo de embeber una ventana nativa por su handle, el que usan toolkits como GTK/X11. **No es confiable en macOS con el backend gráfico actual de mpv** (`vo=gpu-next`, Vulkan/MoltenVK vía Metal): en vez de dibujar dentro del `NSView` que se le da, mpv abre su propia ventana de Cocoa. Un spike aislado "pareció funcionar" durante la construcción porque **se verificó solo leyendo logs de texto de mpv** (que decodificaba con hardware, que el VO se llamaba `gpu-next`) — nunca se verificó viendo la pantalla de verdad. Esa fue la falla de proceso, no solo de código: **un log que dice "VO: gpu-next 3840x2160" no prueba que el frame se vea dentro del widget correcto.**

**La vía correcta para v2, oficialmente soportada por python-mpv/libmpv para embeber en Qt:** el **API de render** de mpv, no `wid`:

1. `mpv.MPV(vo="libmpv", hwdec="videotoolbox")` — `vo=libmpv` habilita el modo render-API; mpv no dibuja nada por su cuenta.
2. Un `QOpenGLWidget` real (no un `QWidget` normal) como superficie.
3. En `initializeGL()`: `mpv.MpvRenderContext(mpv_instance, "opengl", opengl_init_params={"get_proc_address": fn})`, donde `fn` puentea al contexto GL que Qt ya abrió: `QOpenGLContext.currentContext().getProcAddress(name)`.
4. En `paintGL()`: `render_ctx.render(flip_y=True, opengl_fbo={"w": self.width(), "h": self.height(), "fbo": self.defaultFramebufferObject()})`.
5. mpv avisa un frame nuevo por un callback (`update_cb`) que corre en **un hilo de mpv, no el de Qt** — ese callback debe solo señalizar (una señal Qt, o `QMetaObject.invokeMethod` con conexión encolada) para que `update()` se llame de vuelta en el hilo principal. Nunca pintar directo desde ese hilo.

Construye esto en un **spike aislado primero** (una ventana mínima, sin el resto de la app), y **verifica viéndolo** (sección 5) antes de integrarlo a `MainWindow`. No repitas el error de integrar directo y confiar en los logs.

### 3.2 Un crash nativo apareció al intentar la vía correcta — investígalo con cuidado, no lo arrastres a v2 sin entenderlo

Al implementar el API de render (en el stash mencionado arriba), la suite empezó a crashear con:

```
Fatal Python error: Bus error
Sbk_QShortcut_Init -> PySide::fillQtProperties -> PySide::Signal::connect -> MetaObjectBuilder::parsePythonType
```

Pasa siempre construyendo un `QShortcut(..., activated=handler)` después de que ya se crearon muchas instancias de `MainWindow` (y por tanto muchos `QShortcut`) en la misma sesión de Python. Confirmado también por Bruno corriendo la app real (mismo stack trace en el crash report de macOS), así que **no es solo un artefacto de las pruebas.**

No alcancé a aislar la causa exacta. Cosas que probé y no la explicaron del todo: acumulación de instancias reales de `mpv.MPV` (la corregí con creación perezosa del player, el crash siguió). Sospechas para investigar en v2: una clase `QOpenGLWidget` con una señal Qt (`Signal()`) declarada a nivel de clase, combinada con crear y destruir muchas instancias de `MainWindow`/`QShortcut` en una sola sesión, puede estar interactuando mal con el manejo de meta-objetos de PySide6 6.11/shiboken. **Antes de dar por buena cualquier arquitectura de v2, corre la suite completa varias veces seguidas y con distintos subconjuntos de tests** — si el crash reaparece, es un bloqueador real de v2, no un detalle a ignorar. Si después de investigar a fondo no encuentras causa ni solución, considera: declarar la señal de actualización de frame en una clase auxiliar simple en vez de en el propio `QOpenGLWidget`, evitar reconstruir `MainWindow` completo muchas veces en una sola sesión de pytest (usa fixtures que reusen la ventana entre tests donde tenga sentido, o destrúyela explícitamente con `deleteLater()` + procesar eventos entre pruebas), o fijar/probar otra versión de PySide6.

### 3.3 Cuatro problemas de diseño visual reales (de capturas reales, no opinión)

1. **Bug de CSS en el filmstrip — dos cajas en vez de una.** Cada clip debería tener un solo borde de color envolviendo miniatura + nombre de cuarto juntos. En las capturas de v1 se ven dos rectángulos separados. Causa: un `QWidget` plano sin `setAttribute(Qt.WA_StyledBackground, True)` no pinta su propio borde por QSS — la propiedad `border` se hereda a los `QLabel` hijos, que sí la pintan cada uno. Fix en v2: activa `WA_StyledBackground` en el contenedor del ítem del filmstrip, dale `objectName`, y en su QSS por-instancia excluye el borde en los labels hijos explícitamente.
2. **El botón "Importar carpetas…" es invisible como botón** — mismo color de fondo que el panel donde vive. Dale un color de fondo distinto al de los paneles.
3. **La carpeta importada no tiene título ni separación** de la lista de cuartos — dale un encabezado propio (ej. "Material importado").
4. **La leyenda de teclado es genérica** ("1-9 cuartos") en vez de mostrar qué cuarto real le toca a cada número de la sesión activa.

El diseño de referencia (colores, layout, mockups aprobados) sigue vigente en `docs/superpowers/plans/2026-08-06-app-externa-diseno-visual.md` — v2 debe seguir viéndose así, solo sin estos cuatro bugs.

## 4. Qué construir en v2, en orden

1. Copia/adapta los módulos de la sección 2 tal cual (ligero refactor si hace falta, pero sin reescribir su lógica).
2. Spike aislado del embedding de video (sección 3.1), en una ventana mínima, **verificado visualmente** antes de seguir.
3. `player.py` nuevo, envolviendo mpv con el API de render desde el inicio.
4. `ui/video_widget.py` nuevo sobre ese spike ya verificado.
5. Tema visual (`ui/theme.py`) — puedes partir del QSS de v1, ya tenía los colores correctos; solo corrige los 4 problemas de la sección 3.3 desde el principio, no como parche after.
6. `ui/filmstrip.py`, `ui/room_config_dialog.py`, `ui/main_window.py`, `app.py` — reconstruidos, cuidando desde el inicio: (a) no crear objetos mpv reales de más en pruebas, (b) no acumular decenas de `MainWindow`/`QShortcut` reales sin necesidad en una sola sesión de pytest (revisa si el crash de la 3.2 aparece aquí también).
7. TDD igual que hoy: test que falla → código → test que pasa → commit. Un commit por pieza, mensajes en español, revisa `git log --oneline -20` para el tono del repo.

## 5. Cómo verificar sin poder preguntarle nada a nadie

Esto es crítico: la falla de hoy fue verificar por logs en vez de por lo que realmente se ve. Tienes una forma de "ver" la ventana sin depender de permisos de captura de pantalla del sistema operativo (que a mí no me funcionaron con esta app): **Qt puede tomarse una captura de sí mismo, en memoria, sin ningún permiso especial:**

```python
pixmap = window.grab()          # o video_widget.grab() para solo esa parte
pixmap.save("/tmp/verificacion.png")
```

Esto funciona incluso para el contenido de un `QOpenGLWidget" (Qt hace el readback del framebuffer). Úsalo así, en cada paso donde antes te habrías conformado con un log:

1. Abre un clip real de `TEST/clips/`.
2. Deja pasar al menos 1-2 segundos reales (`QTest.qWait(1500)` o similar) para que mpv entregue al menos un frame.
3. `video_widget.grab().save(ruta)`.
4. **Lee esa imagen con tu propia herramienta de lectura de archivos/imágenes** (no asumas que "no crasheó" significa que se ve bien) y confirma con tus propios ojos que el frame del video aparece ahí, no un rectángulo negro vacío ni nada distorsionado.
5. Repite esto para: la ventana completa (confirma que no aparece ninguna ventana de mpv aparte — para eso, además de la captura de Qt, revisa la lista de ventanas del proceso si tienes forma de hacerlo, o al menos confirma explícitamente que no hay ningún otro `QWidget`/ventana top-level creada por mpv), el diálogo de cuartos, y el filmstrip con clips clasificados (pick/reject) para confirmar el fix del bug de doble caja.

No des por resuelto el problema de video sin haber mirado una imagen real de un frame decodificado dentro del widget.

## 6. Lo único que sí bloquea — el formato del manifest

`manifest.py` produce este JSON exacto, ya validado contra el plugin UXP (`uxp-plugin/processManifest.js`):

```json
{
  "proyecto": "Casa Jardin",
  "orientacion": "horizontal",
  "clips": [
    {"orden": 1, "ruta": "/abs/path.MP4", "categoria_path": ["Sala"], "fps": 59.94,
     "in_frame": null, "out_frame": null, "flag": "none", "ruta_proxy": null}
  ]
}
```

No cambies estas llaves ni sus tipos. Todo lo demás de la app es tuyo para reconstruir con libertad.

## 7. Documentos de referencia, en orden de utilidad

1. Este documento.
2. `docs/superpowers/HANDOFF-2026-08-06-auditoria-bugs.md` — arquitectura detallada módulo por módulo de v1, útil como mapa de lo que existía (no como código a copiar en la parte de UI/video).
3. `docs/superpowers/plans/2026-08-06-app-externa-diseno-visual.md` — colores y mockups de referencia para el tema visual.
4. `docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md` — spec de arquitectura, §11 es el contrato del manifest.
5. `git stash show -p` sobre el commit `2a4fff9` — mi intento a medias del API de render, como notas de investigación.

## 8. Definición de "terminado"

El video se reproduce **visiblemente dentro** de la ventana (verificado con `grab()` + inspección real de la imagen, no por logs), ninguna ventana de mpv aparece por separado, la suite completa pasa repetidamente sin el crash nativo de la sección 3.2, y los cuatro problemas de diseño de la sección 3.3 están corregidos y también verificados visualmente. Termina con un informe corto (mismo formato que la sección 8 de `docs/superpowers/HANDOFF-2026-08-06-auditoria-bugs.md`) documentando qué se reconstruyó, qué se reusó de v1, y qué se encontró en el camino — para que Bruno lo lea al despertar, no para que apruebe nada a mitad de camino.
