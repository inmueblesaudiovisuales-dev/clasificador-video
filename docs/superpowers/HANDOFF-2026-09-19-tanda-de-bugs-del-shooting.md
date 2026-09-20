# Handoff — tanda de bugs reportados el 2026-09-19

**Fecha:** 2026-09-19
**Rama:** `master` (se trabajó directo sobre ella, sin branches, como pide Bruno)
**Estado del repo:** limpio, todo comprometido. `git status` no debe mostrar nada
pendiente al retomar.

## De dónde sale esta lista

Bruno mandó diez quejas juntas en un solo mensaje, todas del mismo uso real de
la app (subir material, generar proxies, exportar a Premiere, subir a Drive).
Se acordó con él ir **una por una**, en el orden en que las mandó, y avisarle
antes de tocar código cuando algo no es un bug simple sino una decisión.

La lista completa, tal como la mandó:

1. El plugin importa muy lento los clips.
2. La guía de edición no funciona para nada, visualmente solo se ve un cuadro negro.
3. Al subir una segunda carpeta a Clipify, no pide hacer los proxies; si se
   dejan en cola manualmente, se detiene a preguntar dónde quererlos hasta que
   terminen los primeros proxies.
4. No quiere que se manden a Premiere ni se suban a Drive los videos reject.
5. Cuando algo falla (Google Drive u otra cosa), no hay aviso de que falló,
   solo no se hace.
6. Cada vez que abre el proyecto de nuevo se generan las miniaturas.
7. Drive se desconecta cada vez que se cierra la app.
8. Quiere un modo rápido: combinar el modo económico con hacer menos miniaturas.
9. No da el enlace al subir a Drive.
10. Al subir a Drive no sube carpetas para recursos (música usada, etc.), como
    se había hablado.

## Resuelto en esta sesión (commits en orden)

1. **`f4c38fc`** — La guía (punto 2) se veía negra porque `VideoWidget` es un
   `QOpenGLWidget`: Qt lo compone en una capa aparte y `show()+raise_()` no
   alcanza para taparlo. Se le puso `Qt.WidgetAttribute.WA_AlwaysStackOnTop` a
   `PantallaGuia`. De paso se limpió el CSS de `theme.py`, que seguía
   apuntando a nombres de la pantalla vieja desde el rediseño a tablero de
   columnas de ese mismo día (commit `9513e8f`, de Codex).
   **No comprobado con video real** — este entorno no tiene OpenGL de verdad
   (offscreen). Pedirle a Bruno que lo confirme abriendo la guía sobre el visor.

2. **`c615429`** — El plugin importaba lento (punto 1). `importOrReuseClip`
   recorría el proyecto ENTERO desde la raíz por cada clip del manifest, con
   un `getMediaFilePath()` async por cada clip ya importado — con 205 clips
   eso es cientos de miles de llamadas. `contarLosQueSeVanAMover`
   (`estructura.js`) ya había resuelto el mismo problema para su propio
   conteo (una pasada, no una por clip) pero `importOrReuseClip` no se
   actualizó. Se agregó `indexarClipsPorRuta` (recorre una vez) y
   `processManifest` arma el índice antes del loop.
   **No comprobado en Premiere real** — no hay forma de medir tiempo real
   desde este entorno. Pedirle a Bruno que compare con un rodaje grande.

3. **`ba7ca01`** luego **revertido en la práctica por `edbe027`** — primer
   intento (punto 3): avisar con la insignia "en cola" cuando un bin queda
   esperando en silencio. Bruno lo rechazó: no quería una espera silenciosa
   con insignia, quería que la ventana de "¿creo los proxies?" apareciera **de
   inmediato**, aunque otra tanda esté corriendo, para poder contestar todo y
   dejar la computadora sola. `edbe027` reescribe `_ofrecer_proxies_antes`
   para preguntar siempre; si aceptas "crear" con otra tanda corriendo, se
   forma en `_cola_de_proxies` (mecanismo que ya existía para la cola manual).
   Se borró `_bins_pendientes_de_preguntar` y `_preguntar_pendientes_de_proxies`
   enteros — quedaron sin trabajo.
   **Lección para la próxima vez que algo así se rechace:** cuando Bruno dice
   "eso es una estupendez" sobre un fix recién hecho, preguntarle CÓMO lo
   quiere (se usó `AskUserQuestion`) antes de intentar de nuevo — no adivinar
   una segunda vez.

4. **`0df59f2`** — Fallos silenciosos de Drive (punto 5) y, de la misma causa,
   "Drive se desconecta al cerrar la app" (punto 7). Encontrados TRES sitios
   con una llamada a Drive disparada por un click sin try/except: el "⟳" de
   refrescar una fila (`app.py::_al_refrescar`), "Traer de vuelta"
   (`app.py::_al_pedir_traer_de_vuelta_activo`), y "Subir a Drive" dentro de
   un proyecto cuando Drive no estaba conectado en esa ventana
   (`main_window.py::_subir_a_drive`) — este último con un mensaje de error
   ya escrito y correcto, pero que nadie atrapaba para mostrarlo. Los tres
   ahora muestran el error.
   De paso, `main_window.py::_cliente_de_drive` ahora reusa el token ya
   guardado en disco (`~/.clasificador_video/drive_token.json`) con solo
   leerlo — sin abrir el navegador — en vez de exigir pasar por Configuración
   y apretar "Conectar" en cada ventana nueva. Esa exigencia era la causa real
   del punto 7: el permiso nunca se perdía, la ventana nueva simplemente no lo
   reusaba.

## En pausa, pendiente de que Bruno decida (punto 4)

Bruno pidió que los clips marcados **reject** no se manden a Premiere ni se
suban a Drive. Antes de tocar nada se le hizo notar que esto **le da la vuelta
a dos decisiones ya escritas en el código**:

- En Premiere, el reject SÍ se importa hoy, marcado con `✕` en el nombre — es
  el diseño del 2026-09-08: "una carpeta esconde el clip, una marca lo
  enseña". Ver el bloque correspondiente en `CLAUDE.md`.
- A Drive suben los proxies de TODOS los clips con proxy, reject incluido,
  porque (dice el docstring de `_subir_a_drive`) "el editor externo corta con
  el material completo, no solo lo que Bruno ya filtró".

Se le preguntó con `AskUserQuestion` si de verdad quiere dar vuelta a las dos
decisiones (Premiere y Drive, por separado). **Bruno cerró las preguntas sin
contestar** y dijo "mejor omite eso, vamos con el siguiente". No se tocó nada
de este punto. **No asumir una respuesta** la próxima vez que se retome —
volver a preguntar, puede que haya cambiado de opinión sobre el alcance o
directamente ya no lo quiera.

## Sin empezar todavía

Quedan, en el orden original:

- **Punto 6** — las miniaturas se regeneran cada vez que se abre el proyecto
  de nuevo. Sin investigar. Sospecha inicial: revisar el cache de miniaturas
  (`thumbnail_cache_root`, ver `docs/superpowers/archive/RESULTADO-2026-09-13-ram-y-cpu-en-reposo.md`
  para el diseño de ese cache) — puede ser que la clave de cache no esté
  encontrando lo que ya generó una sesión anterior, o que se esté invalidando
  de más.
- **Punto 8** — modo rápido: combinar el modo económico con generar menos
  miniaturas. Esto es una FEATURE nueva, no un bug — según `CLAUDE.md` hace
  falta brainstorm (`superpowers:brainstorming`) antes de construir nada,
  salvo que ya exista un spec escrito que lo cubra (revisar
  `docs/superpowers/specs/` primero, por si ya se habló de esto).
- **Punto 9** — no da el enlace al subir a Drive. Sin investigar. Revisar
  `_on_drive_subida_lista` en `main_window.py` y qué hace con
  `resultado.folder_link` — puede que se guarde pero no se muestre en ningún
  lado, o que la barra de progreso reemplace el aviso antes de que se vea.
- **Punto 10** — subir carpetas de recursos (música, etc.) a Drive. También
  toca decisión de diseño: `drive.py::subir_paquete` hoy solo sube el
  `.prproj` y la lista de proxies — agregar carpetas de recursos es una
  feature nueva. Revisar si ya se habló de esto en algún spec antes de
  inventar la estructura.

## Cómo retomar

Preguntarle a Bruno cuál sigue (mismo patrón que toda la sesión: uno por uno,
avisando antes de actuar cuando algo no es obvio). Los puntos 8 y 10 son
features y necesitan brainstorm o un spec ya escrito antes de construir nada
— no tratarlos como bugs de una línea.
