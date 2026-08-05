# Handoff: Clasificador de Video para Bienes Raíces (tipo Adobe Bridge, para Premiere)

## 1. Contexto y problema

El usuario es editor de video, trabaja en Adobe Premiere, y produce contenido de bienes raíces (recorridos de propiedades: cocina, recámara, baño, sala, fachada, alberca, etc.). Graba con una **Sony FX30**, en **10-bit** (XAVC HS/S-I, HEVC).

El cuello de botella no es la edición en sí, sino la etapa previa: revisar todo el material de un shooting (decenas de clips) e identificar qué escena/cuarto es cada uno, para poder organizarlo en carpetas/bins dentro de Premiere antes de empezar a cortar. Hoy esto se hace a mano dentro de Premiere y es lento.

**Objetivo del programa:** una herramienta externa, standalone, para macOS, que permita revisar visualmente cada clip de un shooting y clasificarlo por escena — igual que Adobe Bridge permite calificar fotos — y al terminar, generar algo que Premiere pueda importar y arme las carpetas (bins) automáticamente, sin que el usuario tenga que arrastrar nada a mano.

Prioridad explícita del usuario: **velocidad**. La herramienta tiene que permitir clasificar un shooting completo más rápido de lo que tomaría hacerlo directamente en Premiere, idealmente sin tocar el mouse.

---

## 2. Decisiones de arquitectura (y por qué)

### 2.1 No se usa navegador / Electron para el reproductor de video

Primer intento (descartado): construir esto como una app web (HTML/JS) usando el elemento `<video>` nativo del navegador. **Se descartó** porque el material de la FX30 es HEVC 10-bit 4:2:2, y los decodificadores de video de navegador no siempre lo manejan bien (sin aceleración por hardware consistente, cuelgues, clips que no cargan). Esto haría la herramienta más lenta que Premiere mismo, lo cual va en contra del objetivo principal.

### 2.2 Stack elegido: PySide6 + python-mpv + ffmpeg

- **PySide6 (Qt)** — framework de UI. Nativo de macOS, permite construir la ventana, la cuadrícula/filmstrip, atajos de teclado globales, todo el look de la interfaz.
- **python-mpv** — wrapper directo sobre **libmpv** (el motor real de mpv), embebido dentro de un widget de Qt. Esto es la pieza clave: mpv decodifica HEVC 10-bit con aceleración por hardware real (VideoToolbox en Mac), igual de fluido que Premiere. Es lo que hace viable el objetivo de velocidad — no se reinventa un decodificador, se usa uno que ya funciona bien con este códec.
- **ffmpeg** — usado únicamente para generar miniaturas (un frame por clip) para el filmstrip, y para leer el frame rate real de cada clip vía `ffprobe` (necesario para la precisión de frames, ver sección 4).
- **PyInstaller** — empaquetado final en un `.app` de macOS, para que el usuario lo abra con doble clic sin instalar Python ni dependencias a mano.

### 2.3 Formato de salida: FCPXML, no metadata incrustada ni CSV + script

Se evaluaron y descartaron dos enfoques antes de llegar a este:

- **Escribir metadata (XMP) directo en los archivos originales con exiftool** — descartado por riesgo real de corrupción: en ciertos contenedores, escribir metadata obliga a exiftool a reescribir el archivo completo (no solo el header), y si el proceso se interrumpe a medio camino (falla de energía, se cierra el programa), el archivo original queda dañado. Inaceptable tratándose de material de un shooting que no se puede regrabar.
- **CSV + script que mueve archivos a subcarpetas en disco** — funcional, pero mueve/reorganiza los archivos originales físicamente, lo cual el usuario no quería (además de ser un paso extra manual).

**Enfoque final:** el programa exporta un archivo **FCPXML** (el formato de interchange que Premiere importa nativamente vía `File > Import`). En este XML se define:
- Un **bin** por categoría (Cocina, Recámara, Baño, etc.)
- Dentro de cada bin, uno o más **clips/subclips** que **referencian la ruta del archivo original en disco** — no lo mueven, no lo copian, no lo tocan en absoluto
- Los in/out points marcados por el usuario, como subclips independientes dentro de su bin correspondiente

Al importar ese XML en Premiere, los bins aparecen ya poblados y organizados. Es exactamente el resultado que el usuario pedía desde el inicio ("que se arme solito el proyecto de Premiere al importarlo"), sin el riesgo de tocar los archivos fuente.

---

## 3. Flujo de datos

1. Usuario abre la app y selecciona la carpeta del shooting.
2. La app corre `ffprobe` sobre cada clip (frame rate real) y `ffmpeg` genera una miniatura por clip para el filmstrip. Esto es la única fase de "procesamiento batch", y es rápida.
3. Usuario clasifica clip por clip (ver sección 4 y 5) — todo se guarda **en memoria** durante la sesión, no hay autoguardado a disco intermedio salvo lo que se menciona en riesgos (7.6).
4. Al terminar, el usuario exporta — se genera el archivo `.fcpxml`.
5. Usuario hace `File > Import` de ese XML en Premiere. Bins poblados, con subclips ya recortados por in/out y organizados por categoría.

---

## 4. Precisión de in/out points (frame-exacto)

Es crítico que los puntos de corte marcados en la app coincidan exactamente con lo que Premiere interpreta, o los cortes quedan desfasados uno o dos frames — notorio en un corte fino.

Reglas de implementación:
- El frame rate de cada clip se lee individualmente con `ffprobe` (no se asume un valor fijo global, aunque todo el material venga de la misma FX30 — el fps puede variar entre proyectos/modos de grabación).
- Los puntos In/Out marcados por el usuario se **almacenan internamente como número de frame entero**, nunca como segundos con decimales.
- Al generar el FCPXML, esos frames se convierten a **rational time** (el formato que usa FCPXML, tipo `240240/24000s`), no a segundos redondeados. Esto es lo que garantiza que Premiere calcule el mismo punto exacto de corte que se marcó en la app.

**Este punto se marca como pendiente de validación antes de construir todo el pipeline**: hay que probar con uno o dos clips reales (marcar in/out, exportar XML, importar a Premiere, verificar que el corte cae exactamente donde se marcó) antes de automatizar el resto.

---

## 5. Interfaz — especificación completa

### 5.1 Principio de diseño

El video ocupa la gran mayoría de la pantalla (~90%). Todo lo demás es periférico y delgado. La interfaz completa se opera con teclado; el mouse no debería ser necesario en el flujo normal. Los atajos de teclado son **fijos y consistentes sin importar dónde esté el foco** (mismo principio que F2/F5 en Total Commander: la tecla siempre hace lo mismo).

### 5.2 Layout

- **Centro/mayoría de pantalla:** reproductor de video (mpv embebido), reproducción fluida de HEVC 10-bit.
- **Franja delgada inferior — leyenda de categorías, siempre visible (inspirado en Lightroom):** cada categoría se muestra como color + número + nombre corto, por ejemplo:
  `🟧1 Cocina  🟦2 Recámara  🟩3 Baño  🟨4 Sala  ...`
  El usuario nunca tiene que memorizar qué número es qué categoría — lo ve siempre en pantalla y lo reconoce por color/posición con el tiempo, igual que los atajos de Photoshop/Lightroom.
- **Filmstrip inferior (tira de miniaturas), inspirado en Lightroom/Bridge/Total Commander:**
  - Cada miniatura se pinta del color de su categoría en cuanto se clasifica.
  - Clips marcados como Reject (`X`) aparecen atenuados/oscurecidos.
  - Es **ordenable/agrupable**: por categoría, por duración, o "sin clasificar primero" (para ver de un vistazo qué falta sin tener que buscarlo).
  - Soporta **selección múltiple** (`Shift + flecha`), para aplicar una categoría a varios clips de una sola vez — útil cuando hay varias tomas seguidas del mismo cuarto/ángulo.
- **Esquina fija — contador en vivo (inspirado en la barra de estado de Total Commander):** muestra en todo momento algo como `Cocina: 6 · Recámara: 4 · Sin clasificar: 12`, sin que el usuario tenga que abrir ningún panel para saber cómo va.
- **Confirmación visual no intrusiva:** al marcar categoría o pick/reject, un parpadeo breve de color en el borde de la pantalla (verde = pick, rojo = reject) — no hay texto, no hay ventana emergente, se confirma de reojo sin dejar de ver el video.

### 5.3 Atajos de teclado (todos fijos, sin modos)

| Tecla | Acción |
|---|---|
| `Espacio` | Play / Pause |
| `J K L` | Reversa / Pausa / Adelante (convención estándar de edición, igual que Premiere) |
| `I` | Marcar In |
| `O` | Marcar Out |
| `1–9` | Asignar categoría (según la leyenda visible en pantalla) |
| `P` | Pick (marcar como buena toma) — igual que Lightroom |
| `X` | Reject (descartar, no aparece en la exportación) — igual que Lightroom |
| `U` | Unflag (quitar marca de Pick/Reject) — igual que Lightroom |
| `→` / `Enter` | Siguiente clip |
| `Shift + flecha` | Selección múltiple en el filmstrip |
| `/` | Quick filter — escribir para filtrar el filmstrip en vivo por nombre de categoría (inspirado en Total Commander), sin mouse ni menú desplegable |
| `Ctrl+Z` | Deshacer — **multi-nivel**, no solo la última acción (el usuario va rápido y es fácil pasarse de tecla) |

### 5.4 Auto-advance

Al asignar categoría, la app puede avanzar automáticamente al siguiente clip/segmento (comportamiento configurable, tomado del "auto advance" de Lightroom al calificar fotos).

---

## 6. Features explícitamente descartados (y por qué — importante no reintroducirlos)

- **Generar proxies livianos antes de clasificar:** descartado en cuanto se decidió usar mpv en vez de un `<video>` de navegador — mpv decodifica el 10-bit nativo sin problema, los proxies dejaron de ser necesarios.
- **Escribir metadata XMP directo en los archivos originales:** descartado por riesgo de corrupción del material original (ver 2.3).
- **CSV + script externo que mueve archivos a carpetas en disco:** descartado a favor de FCPXML, que no toca los archivos originales en absoluto.
- **Detección automática de cortes de escena (scene-cut detection vía ffmpeg/PySceneDetect):** propuesto y **rechazado explícitamente por el usuario** — no quiere depender de una detección que puede fallar y hacerle perder tiempo corrigiendo. Los in/out se marcan siempre manualmente.
- **Sugerencia/predicción de la siguiente categoría más probable basada en patrones:** propuesto y **rechazado** — el usuario no clasifica en un orden predecible (no siempre sigue el mismo recorrido cuarto por cuarto).
- **Modo comparación (ver dos clips lado a lado para decidir cuál es mejor, tipo Compare View de Lightroom):** propuesto y **rechazado** por complejidad innecesaria para este caso de uso.
- **Panel/extensión dentro de Premiere (UXP) en vez de app externa:** propuesto como alternativa y **rechazado** — el usuario quiere explícitamente una herramienta externa, standalone, tipo Bridge, no algo integrado al panel de Premiere.

---

## 7. Riesgos técnicos identificados (pendientes de mitigar/validar)

1. **Empaquetar libmpv en macOS.** `python-mpv` requiere que `libmpv` esté presente y correctamente enlazada en el build de PyInstaller. Hay que validar que el `.app` final funcione en una Mac limpia (sin Python ni mpv instalados por fuera), no solo en la máquina de desarrollo.
2. **Apple Silicon vs Intel.** Si el usuario o futuros usuarios pueden estar en cualquiera de las dos arquitecturas, el build de libmpv debe ser universal (o generar dos builds), y probarse en ambas — el comportamiento de mpv embebido en un widget de Qt puede variar.
3. **Notarización/Gatekeeper de macOS.** Un `.app` distribuido fuera de la App Store necesita estar firmado y notarizado por Apple, o macOS lo bloqueará al abrirlo. Esto es un paso de configuración (cuenta de desarrollador Apple) que hay que resolver antes de distribuir el programa, incluso para uso personal en otra máquina.
4. **Precisión frame-exacta del FCPXML** (ver sección 4) — validar con clips reales antes de automatizar el pipeline completo.
5. **Mapeo de campos y compatibilidad de versión de Premiere con FCPXML.** El soporte de Premiere para FCPXML ha cambiado entre versiones a lo largo de los años; lo que funciona en la versión actual del usuario no está garantizado en otra. Confirmar versión de Premiere en uso antes de comprometerse con detalles finos del formato.
6. **Rutas absolutas y portabilidad.** El FCPXML referencia los clips por ruta absoluta en disco. Si la carpeta de material se mueve o cambia de unidad después de generar el XML, Premiere pedirá reconectar medios. No es un bug, es una limitación inherente al enfoque — vale la pena que el usuario lo tenga presente en su flujo de trabajo (generar el XML ya con el material en su ubicación final).
7. **Miniaturas con HEVC 10-bit vía ffmpeg.** Confirmar que el build de ffmpeg empaquetado tiene soporte completo para HEVC 10-bit (algunos builds mínimos lo excluyen y generan miniaturas negras o rotas).

---

## 8. Resumen de stack técnico

| Componente | Tecnología | Rol |
|---|---|---|
| UI / ventana / interacción | PySide6 (Qt) | Interfaz completa, atajos de teclado, filmstrip, leyenda |
| Reproducción de video | python-mpv (libmpv embebido) | Decodifica HEVC 10-bit con aceleración por hardware, fluido |
| Miniaturas y frame rate | ffmpeg / ffprobe | Genera thumbnails, lee fps real por clip |
| Exportación final | Generador de FCPXML (código propio) | Arma bins + subclips referenciando material original |
| Empaquetado | PyInstaller (+ firma/notarización Apple) | `.app` de macOS distribuible |

---

## 9. Estado actual

Este documento captura las decisiones de diseño y arquitectura discutidas. **No se ha escrito código todavía.** Antes de empezar la construcción, los puntos de la sección 7 marcados como "pendiente de validar" (especialmente el punto 4, precisión frame-exacta, y el punto 5, compatibilidad de versión de Premiere) deberían probarse con un prototipo mínimo antes de invertir tiempo en el resto de la interfaz.
