# Spec: Clasificador de Video para Bienes Raíces — 2026-08-05

## 1. Qué hace, en una frase

App de escritorio para macOS, standalone (no depende del checklist ni de iav-metadata-app), que permite revisar el material de un shooting de bienes raíces, clasificarlo por cuarto usando solo el teclado, y exportar un XML que Premiere Pro importa armando los bins automáticamente — sin mover, copiar ni tocar los archivos originales.

Contexto de origen: `../../../handoff-clasificador-video.md` (documento de arranque, con las decisiones de UI/UX detalladas que siguen vigentes salvo lo que este spec corrige explícitamente).

## 2. Qué cambia respecto al handoff original

El handoff proponía **FCPXML** (formato de Final Cut Pro X: `<fcpxml>`, `resources` + `spine`, tiempo en "rational time" tipo `240240/24000s`). Este spec lo reemplaza por **xmeml** (formato FCP7, `<xmeml version="4">`), ya validado con archivos reales en Premiere Pro 2026 dentro de otro proyecto (`iav-metadata-app`). Motivo: xmeml declara in/out como número de frame entero — evita la conversión a rational time, que el handoff original marcaba como riesgo pendiente de validar (§7.4). El resto de decisiones de arquitectura del handoff (§2.1, §2.2: PySide6 + python-mpv + ffmpeg, sin proxies, sin escritura de XMP en el original) siguen vigentes sin cambios.

## 3. Reglas de xmeml ya comprobadas (no re-derivar)

Tomado de `iav-metadata-app/docs/premiere/plantilla-xmeml-validada.md`, spike real 2026-06-09, importado en Premiere Pro 2026:

- Un clip se va **offline** si el XML declara `<audio>` en un archivo que no tiene pista de audio real. Regla: sondear con exiftool/ffprobe si el archivo tiene audio; declarar `<audio>` solo si sí.
- La ruta (`file://localhost/<ruta-absoluta-encoded>`) y el códec (HEVC) no son el problema del offline.
- Premiere lee duración y timecode reales del archivo al vincular — los valores declarados no son críticos para el vínculo.
- Los colores de etiqueta (`<labels><label2>...`) sí funcionan por XML: Iris, Lavender, Forest, Mango, Rose.
- Estructura: `version="4"`, todo dentro de un `<bin>` raíz, con sub-bins anidados y una `<sequence>` vacía al final. Cada clip maestro lleva `uuid`, `masterclipid`, `ismasterclip="TRUE"`, `explodedTracks="true"`.
- `rate`: `timebase = round(fps)`, `ntsc = TRUE` si el fps no es entero (59.94/29.97/23.976), `FALSE` si es exacto (24/25/30/50/60). Mismo `<rate>` en clip, clipitem, file y secuencia.

Este proyecto añade sobre esa base: **in/out reales** por clip, como `<in>`/`<out>` en número de frame dentro del `<clipitem>` (no se usaron en el spike original, que eran clips completos) — es lo que hay que validar primero (ver §9).

## 4. Sistema de cuartos

- **Lista maestra fija**, editable/ampliable con "cuarto custom": Fachada, Sala, Comedor, Cocina, Recámara, Baño, Estudio/Oficina, Alberca, Jardín/Patio, Terraza, Roof garden, Garage/Cochera, Vestíbulo/Hall, Área de servicio, Dron/Aérea, Amenidades comunes, B-roll/Detalles.
- Antes de clasificar un shooting, el usuario elige qué cuartos tiene esa propiedad. Los que se repiten (recámaras, baños independientes) se numeran automático: Recámara 1, Recámara 2, Recámara 3...
- **Subcuartos**: cualquier cuarto puede tener colgados Baño / Closet / Terraza (u otro subcuarto custom) como hijos. En el XML esto es un bin anidado: `Recámara 2 > Baño`.
- El bin de un cuarto sin subcuartos (Cocina, Sala) es plano, igual que hoy.

## 5. Selección por teclado

Leyenda inferior siempre visible con teclas 1-9 para los cuartos activos de esa propiedad (más el resto de la leyenda: colores, contador en vivo — igual que handoff §5.2).

**Cuartos con subcuartos:** al presionar el número de un cuarto que tiene subcuartos, la leyenda cambia por un instante para mostrar solo las opciones de ese cuarto (por ejemplo: "1 Baño · 2 Closet · 3 Terraza · Espacio = solo Recámara 2"). No hay límite de tiempo entre teclas — el usuario presiona la que corresponda cuando la ve. Si el cuarto no tiene subcuartos, clasifica directo con una sola tecla, sin submenú.

El resto de atajos queda igual que el handoff original (§5.3): `Espacio` play/pause, `J K L` reversa/pausa/avance, `I`/`O` marcar in/out, `P`/`X`/`U` pick/reject/unflag, `→`/`Enter` siguiente clip, `Shift+flecha` selección múltiple, `/` quick filter, `Ctrl+Z` deshacer multi-nivel.

## 6. In/out de cada clip

En este flujo de trabajo, normalmente **un archivo = un cuarto completo** (no se graban recorridos que crucen varios cuartos en un solo clip). El in/out sirve para recortar el muerto al inicio/final de la toma (caminar a posición, ajustar cámara), no para partir el archivo en varios cuartos. Se marca con `I`/`O`, se guarda internamente como número de frame entero, y se traduce directo a `<in>`/`<out>` en el `<clipitem>` del xmeml.

## 7. Pick / Reject / Unflag y exportación

**Todos los clips se exportan, sin excepción** — no hay filtro de exportación por Pick, Reject, ni por estar sin clasificar:

- Clip clasificado → va al bin de su cuarto (anidado si tiene subcuarto).
- Clip sin clasificar → va a un bin `Sin clasificar`.
- Clip marcado **Reject** → se exporta igual que cualquier otro, pero con `<label2>` en un color reservado para rechazado (p. ej. Rose).
- Clip marcado **Pick** → se exporta igual, con `<label2>` en un color reservado para elegido (p. ej. Forest).
- Clip sin marcar (ni pick ni reject) → sin color de label, o el color por defecto de su bin/cuarto si se implementa eso a futuro (fuera de alcance de este spec).

En el filmstrip de la app (no en Premiere), Pick se distingue con un borde + estrella en la miniatura; Reject atenúa/oscurece la miniatura (igual que el handoff original).

**Aviso antes de exportar:** si hay clips sin clasificar, la app muestra un aviso con el conteo antes de generar el XML. No bloquea la exportación — solo informa.

## 8. Autoguardado

Mientras el usuario clasifica, la app reescribe continuamente un archivo JSON local con el estado completo de la sesión (clasificación, in/out, pick/reject de cada clip). Escritura atómica: se escribe a un archivo temporal y se renombra sobre el definitivo, para que una interrupción a medio guardar no deje el JSON corrupto. Si la app se cierra o truena a medio shooting, al reabrir esa carpeta se recupera el estado exacto donde se quedó.

## 9. Validación antes de construir la interfaz completa

Antes de invertir tiempo en toda la UI (filmstrip, leyenda, atajos), se valida con un prototipo mínimo:

1. Tomar 2-3 clips reales de la FX30 (con y sin audio).
2. Generar a mano/con script simple un xmeml con: bins anidados (cuarto > subcuarto), in/out distintos del clip completo, y labels de color en Pick/Reject.
3. Importar ese XML en Premiere Pro 2026 y confirmar: los clips auto-vinculan, el corte de in/out cae exactamente donde se marcó, los bins anidados se ven correctos, y los colores de label se aplican.

Solo después de confirmar esto se construye el resto del pipeline (UI completa, integración con mpv, empaquetado).

## 10. Alcance de distribución

Por ahora, la app es de uso exclusivo del usuario en su propia Mac. No se necesita notarización de Apple (riesgo §7.3 del handoff queda descartado por ahora) — basta con firma ad-hoc como se hace en iav-metadata-app. Si en el futuro se comparte con otro editor o máquina, este punto se revisita.

## 11. Riesgos que se mantienen del handoff original

- Empaquetar libmpv correctamente en el build de PyInstaller, probado en una Mac limpia (§7.1).
- Arquitectura Apple Silicon vs Intel si aplica a futuras máquinas (§7.2).
- Miniaturas con HEVC 10-bit vía ffmpeg — confirmar que el build empaquetado no genera miniaturas negras/rotas (§7.7).
- Rutas absolutas: si la carpeta del shooting se mueve de disco después de exportar el XML, Premiere pedirá reconectar medios (§7.6 del handoff, limitación inherente al enfoque, no un bug).

## 12. Fuera de alcance (explícitamente descartado, no reintroducir)

Igual que el handoff original (§6): generar proxies antes de clasificar, escribir XMP en los archivos originales, mover/copiar archivos a carpetas en disco, detección automática de cortes de escena, sugerencia de categoría por IA, modo comparación lado a lado, panel/extensión dentro de Premiere (UXP). Se agrega a esta lista: filtrar la exportación por Pick/Reject/clasificación (§7 de este spec — todo se exporta siempre).
