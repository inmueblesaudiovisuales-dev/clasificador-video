# Handoff — Sesión exclusiva de diseño visual, con libertad creativa — 2026-08-06

## 0. Tu única misión en esta sesión

**Diseño visual. Nada de lógica de negocio, nada de bugs funcionales, nada del reproductor de video.** Bruno quiere una sesión separada, dedicada por completo a pensar la interfaz de esta app **de forma creativa y fuera de la caja** — no un ajuste cosmético del tema actual, sino repensar en serio cómo hacer que se sienta como una **app profesional de verdad**, con las funciones que ya tiene, y recién al final adaptar esa dirección de diseño al código real de la app (PySide6 + QSS).

Tienes libertad creativa total sobre color, tipografía, layout, iconografía, jerarquía visual, micro-interacciones — todo lo visual. Lo que no tienes es libertad para cambiar comportamiento, arquitectura de datos, ni tocar la lógica de los módulos que no son de UI.

## 1. Aislamiento de trabajo — lee esto antes de tocar un solo archivo

Hay **otra sesión de Claude Code trabajando en paralelo, en el mismo repo, sobre un bug real de crash** (ver `docs/superpowers/HANDOFF-2026-08-06-crash-al-importar.md`). Esa sesión tiene cambios sin commitear ahora mismo en `src/clasificador_video/ui/filmstrip.py` y `src/clasificador_video/ui/main_window.py` (entre otros) — el filmstrip clickeable y un fix de condición de carrera. Si trabajas directo sobre el working tree de `master`, **vas a pisar ese trabajo o generar conflictos feos.**

Antes de escribir una sola línea de QSS o Python:

1. Corre `git status` y `git diff --stat`. Si ves cambios sin commitear que no son tuyos, **no los toques ni los deshagas** — no son tuyos para decidir.
2. Trabaja en un **git worktree aislado** (usa la skill `superpowers:using-git-worktrees` si está disponible, o `git worktree add ../organizador-video-diseno -b diseno-visual-2026-08-06` a mano) para no interferir con la sesión del crash. Así puedes iterar y commitear tu propio trabajo sin pisar el suyo, y Bruno decide después cómo integrar ambas ramas.
3. Si por lo que sea el crash ya se resolvió y comiteó cuando arrancas (revisa `git log` y si el bug de la sección de arriba sigue documentado como pendiente o resuelto en la sección 8 de ese handoff), puedes trabajar directo sobre `master` actualizado — pero verifica primero, no asumas.

## 2. Qué es esta app y qué pantallas tiene

App de escritorio (PySide6) para que un editor de video clasifique clips de shootings inmobiliarios por cuarto, marque in/out y bueno/malo, y exporte un manifest que un plugin de Adobe Premiere usa para armar el proyecto de edición solo. La usa un editor de video trabajando rápido, con el teclado, muchas veces junto a Premiere abierto — el estándar de comparación no es "una app bonita" en abstracto, es **verse a la altura de las herramientas profesionales de post-producción con las que convive** (Premiere, DaVinci Resolve, Frame.io) — no una utilería gris de escritorio.

Pantallas/estados reales que existen hoy (todas necesitan diseño, no solo la principal):

1. **Diálogo de configuración de cuartos** (`ui/room_config_dialog.py`) — grid de botones toggle con los 17 cuartos maestros, campo para agregar cuartos personalizados, botón "Empezar a clasificar". Es la primera pantalla que ve el usuario en cada sesión nueva.
2. **Ventana principal** (`ui/main_window.py`) — layout de tres zonas:
   - Columna izquierda: lista de cuartos activos con contador de clips por cuarto, botón "Importar carpetas…", lista de material importado (carpetas de nivel superior).
   - Centro: reproductor de video embebido (recién arreglado — mpv vía API de render de Qt, ver el otro handoff), selector de calidad de reproducción (dropdown), botón "Exportar manifest…".
   - Abajo: filmstrip horizontal de miniaturas — una por clip, con nombre del cuarto asignado, borde de color por estado (azul = actual, verde = pick, rosa = reject), ahora clickeable.
   - Pie de ventana: leyenda de atajos de teclado (qué tecla corresponde a qué cuarto en la sesión activa, play/pause, in/out, pick/reject, deshacer).
3. Estados dentro de la ventana principal que también son diseño, no solo la vista "feliz": sin clips importados aún (vacío), clip sin miniatura todavía (cargando), clip marcado pick/reject, cuarto con subcuartos numerados (ej. "Recámara 1", "Recámara 2").

El tema actual vive en `src/clasificador_video/ui/theme.py` — un solo módulo con constantes de color y una función `build_stylesheet()` que devuelve QSS aplicado una vez sobre `QApplication`. Es la implementación de un mockup aprobado en una sesión de brainstorming anterior (`docs/superpowers/plans/2026-08-06-app-externa-diseno-visual.md`, mockups HTML en `.superpowers/brainstorm/70942-1785996102/content/` si quieres ver de dónde viene el punto de partida actual — ábrelos con `open <archivo>.html`). Bruno considera que ese resultado, aunque mejor que el gris por defecto de Qt, **todavía no se siente como una app profesional real** — por eso pide una sesión nueva con pensamiento más ambicioso, no un ajuste incremental de esos mismos mockups.

## 3. Cómo trabajar — mockups rápidos primero, código real al final

No empieces escribiendo QSS directo sobre la app real — iterar sobre PySide6/QSS es lento (hay que relanzar la app, no hay hot-reload real de estilos complejos) y te va a anclar de más a la estructura visual actual en vez de pensar distinto. En su lugar:

1. **Explora 3-4 direcciones de diseño genuinamente distintas entre sí** — no variaciones de paleta sobre el mismo layout. Piensa en serio en qué se siente distinto: densidad de información, tipografía (¿mono para metadata técnica + sans para texto?), cómo se comunica el estado de un clip sin depender solo de un borde de color, cómo se jerarquiza "lo que necesito ver ya" (clip actual, cuarto asignado) vs "lo que consulto de vez en cuando" (leyenda de teclado, lista completa de cuartos). Inspírate libremente en interfaces profesionales reales de herramientas de video/creativas (DaVinci Resolve, Premiere, Frame.io, Arc, Linear, Notion) — no para copiarlas, sino para calibrar qué hace que algo se sienta profesional y no genérico.
2. **Construye cada dirección como un mockup HTML/CSS autocontenido**, cubriendo al menos la ventana principal completa (las tres zonas + filmstrip con varios clips en distintos estados) y el diálogo de configurar cuartos. Usa `docs/superpowers/plans/` o una carpeta nueva tipo `.superpowers/brainstorm/<fecha>-rediseno/` para guardarlos, siguiendo la convención ya usada en este repo.
3. **Preséntale las direcciones a Bruno con tu recomendación explícita** — no un simple "aquí tienes 3 opciones, tú decides": di cuál te parece la mejor y por qué, igual que decidirías tú si fuera tu propio proyecto. Esto es una sesión con Bruno despierto y disponible — a diferencia del handoff de reconstrucción de video de hoy en la madrugada, aquí **sí debes pausar y esperar su aprobación explícita de una dirección** antes de tocar el código real de la app. No implementes las cuatro direcciones en la app ni elijas tú solo cuál va — eso es justo la decisión que Bruno quiere tomar él.
4. **Una vez aprobada una dirección**, impleméntala en `theme.py` / QSS / los widgets de UI (`objectName`, layout, spaciado) del código real. No toques lógica de negocio ni el manejo de eventos/señales existente salvo que sea estrictamente necesario para el diseño (ej. agregar un `objectName` nuevo para poder styleear algo específico está bien; cambiar qué hace un botón al hacer click no lo está).
5. **Verifica visualmente en la app real antes de dar por terminado**, no en el mockup HTML — un mockup estático no prueba que QSS se comporte igual dentro de Qt (ver el bug real de doble-caja documentado en `HANDOFF-2026-08-06-arreglar-video-y-diseno.md` §3.3, causado justo por una diferencia entre "cómo se ve el QSS en teoría" y "cómo lo pinta Qt de verdad"). Usa capturas reales:
   ```python
   pixmap = window.grab()
   pixmap.save("/tmp/verificacion.png")
   ```
   y **lee esa imagen tú mismo** con tu herramienta de lectura de archivos antes de afirmar que algo quedó bien. Cubre al menos: ventana principal con clips importados y miniaturas cargadas, un clip en estado pick y otro en reject, el diálogo de configurar cuartos, y el estado vacío (sin clips importados).

## 4. Qué NO tocar

- Lógica de negocio pura: `manifest.py`, `autosave.py`, `rooms.py`, `category_path.py`, `ingest.py`, `proxy_match.py`, `keyboard.py`, `probe.py`, `thumbnails.py`.
- El reproductor de video (`player.py`, la integración de mpv en `ui/video_widget.py`) — se acaba de reconstruir con mucho cuidado (embedding vía API de render de mpv, ver el otro handoff), no lo toques salvo para ajustar tamaño/posición del widget dentro del layout si el nuevo diseño lo requiere.
- El manejo de clicks del filmstrip y cualquier lógica de señales/eventos — eso pertenece a la sesión del crash. Puedes y debes cambiar cómo se ve un `_ClipItemWidget`, no cómo reacciona a eventos.
- El formato del manifest JSON (contrato con el plugin UXP) — no es parte de esta tarea, ni remotamente.

## 5. Definición de "terminado"

- 3-4 direcciones de diseño exploradas de verdad, como mockups HTML navegables, no solo descritas en texto.
- Una recomendación clara y justificada de tu parte entre esas direcciones.
- Aprobación explícita de Bruno de una dirección (esta sesión debe pausar a esperarla, no asumirla).
- La dirección aprobada implementada en el código real de la app (`theme.py` y los widgets de UI que corresponda).
- Verificación visual real (capturas `grab()` leídas de verdad) de las pantallas listadas en la sección 3, punto 5.
- Trabajo hecho en un worktree/rama aislada del trabajo de la sesión del crash, con un plan claro de cómo se integran ambas ramas de vuelta a `master` (coméntalo en el informe final, no lo decidas ni lo ejecutes tú solo si implica descartar el trabajo de la otra sesión).
- Informe corto al final: qué direcciones se exploraron, cuál se eligió y por qué, qué se implementó, y cómo verificarlo.
