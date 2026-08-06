# Spec: App externa del Clasificador de Video — diseño y riesgos resueltos — 2026-08-06

## 1. Qué es este documento

Este spec **complementa** `2026-08-05-clasificador-video-uxp-design.md` (el spec de arquitectura, vigente y no reemplazado). Ese spec ya define en detalle: ingest genérico por carpetas (§3), sistema de cuartos (§4), selección por teclado (§5), reproducción y calidad (§6), in/out directo sobre el clip (§7), pick/reject y exportación (§8), proxies (§9), autoguardado (§10), y el formato exacto del manifest que el plugin UXP ya consume (§11). Ninguna de esas secciones cambia aquí.

Este documento agrega lo que faltaba: (1) la validación real de los tres riesgos técnicos que el handoff de proyecto dejó pendientes, (2) las decisiones de diseño visual e interacción que el spec anterior no cubría a detalle, y (3) un ajuste al ingest para facilitar material de varias cámaras a la vez.

## 2. Riesgos técnicos — validados con material real (2026-08-06)

Los tres riesgos que el handoff de proyecto marcaba como "identificados y sin probar" se probaron hoy con los clips reales de `TEST/` (Sony FX30, HEVC 10-bit 4:2:2, verticales). Los tres quedan resueltos:

**Miniaturas del filmstrip respetando rotación (spec anterior §13):** confirmado con ffmpeg 8.1.1 y con mpv — ambos aplican automáticamente la matriz de rotación del archivo al extraer un frame, sin flags especiales. Se decide usar **mpv** para esto (no ffmpeg), por la razón del punto siguiente.

**Reproducción de HEVC 10-bit dentro de la interfaz:** confirmado con `python-mpv` + `hwdec=videotoolbox` — el log de mpv confirma `Using hardware decoding (videotoolbox)`, es decir, decodifica usando el chip gráfico de la Mac, no el procesador. La rotación también se corrige automáticamente en reproducción (filtro `autorotate` interno de mpv), igual que en las miniaturas.

**Una sola herramienta para video, no dos:** dado que python-mpv ya es obligatorio para el reproductor, y ya probamos que también saca miniaturas correctamente, la app usa **mpv para todo lo relacionado a leer video** (reproducción y miniaturas). ffmpeg deja de ser una dependencia de la app externa — se sigue usando únicamente en herramientas de línea de comandos para verificación/soporte, si hace falta, pero no es parte del flujo de la app.

**Nota de proceso, por si se re-verifica esto más adelante:** los clips en `TEST/` son de 2-6 segundos (creados para probar rotación en Premiere, no shootings reales). Al validar hoy, la primera ronda de pruebas pidió miniaturas de segundos que no existen en esos clips (ej. segundo 20 de un clip de 2 segundos) — eso generó una falsa alarma de "bug de ffmpeg" que se descartó al repetir la prueba dentro de la duración real del clip. Cualquier prueba futura con este material debe primero confirmar la duración real (`ffprobe -show_entries format=duration`) antes de interpretar un fallo de extracción como bug.

**Autoguardado:** no requería prueba técnica — es escritura de un JSON local en cada acción de clasificación, con escritura atómica (archivo temporal + rename). Sin cambios respecto al spec anterior (§10).

## 3. Estructura de la ventana principal

Ventana única, todo visible siempre — sin pantallas separadas para configurar/clasificar/exportar (ver §5 para la única excepción: un diálogo previo de configuración de cuartos).

- **Reproductor al centro**, ocupando la mayor parte del espacio — prioridad porque el material es vertical (9:16) y se necesita verlo grande para clasificar bien.
- **Columna de cuartos** a un lado (angosta), con contador de clips por cuarto y el cuarto activo resaltado.
- **Filmstrip** debajo del reproductor, ocupando todo el ancho horizontal — fila de miniaturas navegable, cada una mostrando su estado (ver §4).
- **Leyenda de teclado** al fondo, siempre visible, con los atajos de cuartos (1-9) y de acciones (I/O, P, X, Espacio, etc.), igual que en el spec anterior §5.
- **Indicador de autoguardado** discreto en la barra superior ("Autoguardado hace Ns").
- **Selector de calidad de reproducción** en la barra superior (spec anterior §6).

## 4. Estado visual de cada clip en el filmstrip

Cada miniatura del filmstrip comunica de un vistazo, sin texto adicional que leer uno por uno:

- **Borde de color alrededor de la miniatura**, igual al lenguaje de color de etiqueta que ya usa Premiere: verde (Forest) si el clip está marcado como pick, rosa (Rose) si está marcado como reject, sin borde de color si no tiene decisión.
- **Punto de color** en la esquina superior derecha, reforzando el mismo estado (redundante a propósito, para que se lea incluso en miniaturas pequeñas).
- **Nombre del cuarto asignado** debajo de la miniatura; si no tiene cuarto, dice "Sin clasificar".
- El clip que se está reproduciendo actualmente se marca con un borde azul, independiente del estado de pick/reject.

## 5. Configurar los cuartos de la propiedad

Paso único, al abrir un shooting nuevo — un diálogo, no una pantalla aparte del flujo principal:

- Lista fija de cuartos (la del spec anterior §4) presentada como chips seleccionables, marcados los más comunes por default (ajustable).
- Cuartos que pueden repetirse (Recámara, Baño) llevan un contador +/- junto al chip; la app numera automático (Recámara 1, Recámara 2...).
- Campo para agregar un cuarto personalizado que no esté en la lista.
- Los **subcuartos** (Baño dentro de una recámara específica, por ejemplo) no se configuran aquí — se crean la primera vez que se usan durante la clasificación: parado en "Recámara 2", al presionar la tecla de "Baño" la app pregunta una sola vez a qué cuarto cuelga, y de ahí en adelante ese subcuarto ya existe para esa recámara. Esto evita alargar el paso de configuración con combinaciones que quizá no se usen.

## 6. Ingest de material de varias cámaras a la vez

Ajuste sobre el spec anterior §3 (que seguía siendo válido, solo se le agrega una vía más rápida de entrada — el ingest sigue siendo genérico, sin lógica de "tipo de cámara", ver spec anterior §15).

Un shooting normalmente trae material de más de una fuente a la vez (la FX30 y el dron, por ejemplo, cada una en su propia tarjeta/carpeta). Además del arrastre manual archivo por archivo que ya soportaba el spec anterior, se agrega:

- Botón **"Importar carpetas"** que abre el explorador de macOS permitiendo elegir **varias carpetas a la vez** (una por tarjeta/cámara).
- Cada carpeta elegida se agrega como su propia carpeta de nivel superior en el panel de ingest, con el nombre de la carpeta de origen (editable después, por si el usuario quiere renombrarla a algo como "FX30" o "Dron").
- La app no interpreta el nombre ni el contenido de la carpeta para decidir nada — sigue siendo el usuario quien clasifica cuarto por cuarto, clip por clip. Esto es solo una forma más rápida de meter varias fuentes sin arrastrar archivo por archivo.
- El emparejamiento de proxies (clic derecho → "Buscar proxies", spec anterior §3) se hace igual, carpeta por carpeta, independiente de cuántas carpetas se hayan importado de una vez.

## 7. Lo que no cambia (referencia rápida al spec anterior)

Estas seis piezas quedan exactamente como en `2026-08-05-clasificador-video-uxp-design.md`, sin modificación:

- Selección por teclado (§5): 1-9 para cuartos, leyenda cambia si hay subcuartos, `Espacio`/`J K L`/`I O`/`P X U`/flechas/`/`/`Ctrl+Z`.
- In/out directo sobre el clip maestro, sin subclips (§7).
- Pick/reject sin excluir del export; aviso no bloqueante si hay clips sin clasificar (§8).
- Proxies vinculados vía manifest, emparejados por sufijo `S03` (§9).
- Autoguardado con escritura atómica (§10).
- El formato del manifest (§11) — es una restricción fija por lo que el plugin UXP ya espera, no un grado de libertad de este documento.

## 8. Fuera de alcance (sin cambios respecto al spec anterior §15)

Se mantiene todo lo ya descartado: xmeml, subclips, escritura de XMP en originales, poblar la secuencia de Premiere (queda para después, §12.1 del spec anterior), vigilancia automática de carpeta de manifests, y lógica de "tipo de cámara" en el ingest — importar varias carpetas a la vez (§6 de este documento) es una comodidad de entrada, no una clasificación automática por cámara.

## 9. Riesgos conocidos, actualizados

Del spec anterior (§16), sigue vigente el riesgo de distribución del plugin a otra máquina — no aplica a la app externa.

Nuevo para la app externa: **ffmpeg deja de ser dependencia** (§2) — si en el futuro se necesita ffmpeg para algo que mpv no cubra (por ejemplo, un análisis específico de metadata), se vuelve a evaluar en ese momento, no antes.
