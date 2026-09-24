# Proxies reales en Premiere y marca de Clipify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar proxies visibles y reconocibles, y enlazarlos como proxies reales de sus originales dentro del `.prproj` directo.

**Architecture:** Se incorporará un arquetipo XML creado por Premiere después de usar **Adjuntar proxies**. El generador clonará ese cierre para cada `Clip.ruta_proxy`, lo conectará al `Media` clonado del original y actualizará todas las rutas y streams que Premiere cambia. La codificación del proxy conservará el video del original y le superpondrá el glifo de Clipify en una esquina; su nombre y los nombres mostrados en Premiere se ajustarán en sus módulos de responsabilidad actuales.

**Tech Stack:** Python 3, `xml.etree.ElementTree`, gzip, ffmpeg/ffprobe, PySide6, pytest.

**Spec:** `docs/superpowers/specs/2026-09-24-proxies-en-prproj-y-marca-design.md`

## Global Constraints

- El original es siempre el medio principal para edición y exportación; un proxy nunca entra como un segundo `ClipProjectItem` visible.
- Reproducir la estructura real de Premiere 26.3 observada en `antes1.prproj` y `despues.prproj`; no enlazar sólo una ruta.
- Los proxies nuevos se llaman `<stem>_proxy.mp4`; los `S03` existentes siguen encontrándose y nunca se renombran.
- La marca usa el glifo existente de Clipify, es pequeña, semitransparente y queda en la esquina inferior derecha.
- El filtro de la marca no escala, recorta, rota, modifica fps, duración ni número de cuadros.
- El nombre visible es `CUARTO-01 <marca> [CAMARA]`; conserva numeración por cuarto y marca vacía cuando el estado es `none`.
- No abrir Premiere desde la automatización. Bruno valida la apertura y el interruptor de proxies en Premiere.
- Trabajar directo en `master`, con mensajes de commit en español mexicano y la suite completa con `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`.

## Review Focus

- Un proxy ausente, incompleto o no verificable debe dejar el original solo y no escribir referencias rotas. Se cubre en la Tarea 3.
- Una toma vertical debe conservar su orientación y dimensiones después de superponer el glifo. Se cubre en la Tarea 5.
- Una toma con audio multicanal debe conservar los enlaces de audio de proxy, no sólo el enlace de video. Se cubre en la Tarea 3.
- Una ruta de plantilla anterior no puede sobrevivir en ningún `RelativePath` del original o proxy generado. Se cubre en la Tarea 4.
- Un nombre de cuarto con minúsculas, acentos o más de 99 clips debe conservarse en mayúsculas y ordenable. Se cubre en la Tarea 2.

---

## Estructura de archivos

- `recursos/premiere/TemplateProxyAdjunto.prproj`: plantilla mínima guardada por Premiere con un original y su proxy ya adjunto; se sanitiza para no conservar rutas personales y se usa únicamente como arquetipo de estructuras privadas de Premiere.
- `src/clasificador_video/prproj_plantilla.py`: localiza y describe el arquetipo de proxy adjunto, sin decidir rutas de proyecto ni nombres de clips.
- `src/clasificador_video/prproj_generador.py`: clona original y proxy, conecta el cierre XML y actualiza rutas/streams para el `.prproj` final.
- `src/clasificador_video/nombre_de_clip.py`: forma el nombre visible de Premiere.
- `src/clasificador_video/proxy_gen.py`: nombra proxies nuevos y prepara la capa transparente de Clipify para ffmpeg.
- `src/clasificador_video/recursos.py`: devuelve las rutas de las dos plantillas de Premiere y del glifo temporal de codificación.
- `tests/test_prproj_plantilla.py`: comprueba que el arquetipo de proxy está completo.
- `tests/test_prproj_generador.py`: comprueba XML, enlaces, rutas y ausencia de items visibles duplicados.
- `tests/test_nombre_de_clip.py`: comprueba el nuevo formato de nombre.
- `tests/test_proxy_gen.py`: comprueba nombres, comando ffmpeg y conservación de geometría/tiempo con medios de prueba pequeños.
- `tests/test_ingest.py`: asegura que `_proxy` y `S03` no entran como originales.

### Task 1: Empacar y descubrir el arquetipo de proxy real

**Files:**
- Create: `recursos/premiere/TemplateProxyAdjunto.prproj`
- Modify: `src/clasificador_video/recursos.py`
- Modify: `src/clasificador_video/prproj_plantilla.py`
- Modify: `tests/test_prproj_plantilla.py`

**Interfaces:**
- Produces: `ArquetipoDeProxy(media_uid: str, video_media_source_id: str, audio_media_source_id: str | None, proxy_media_uid: str, proxy_video_stream_id: str, proxy_audio_stream_ids: tuple[str, ...])`.
- Produces: `arquetipo_de_proxy(raiz: ET.Element) -> ArquetipoDeProxy`.

- [ ] **Step 1: Preparar una plantilla sin rutas personales**

Extraer de `/Users/brunogutierrez/Downloads/despues.prproj` solamente el cierre necesario para un clip original con proxy adjunto. Sustituir sus `FilePath`, `ActualMediaFilePath`, `RelativePath`, `Title`, rutas `.pek` y `FileKey` por valores ficticios coherentes antes de versionarla como `TemplateProxyAdjunto.prproj`. Debe abrirse con `leer_prproj` y no debe incluir clips o bins de trabajo de Bruno.

- [ ] **Step 2: Escribir la prueba de descubrimiento en rojo**

```python
def test_arquetipo_de_proxy_exige_medio_proxy_y_enlaces_de_audio():
    raiz = leer_prproj(recursos.template_proxy_adjunto())
    arquetipo = prproj_plantilla.arquetipo_de_proxy(raiz)

    assert raiz.find(
        f'.//Media[@ObjectUID="{arquetipo.proxy_media_uid}"]/IsProxy'
    ).text == "true"
    assert arquetipo.video_media_source_id
    assert arquetipo.audio_media_source_id
    assert len(arquetipo.proxy_audio_stream_ids) > 0
```

- [ ] **Step 3: Ejecutar la prueba para confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_plantilla.py::test_arquetipo_de_proxy_exige_medio_proxy_y_enlaces_de_audio -q`

Expected: FAIL porque `arquetipo_de_proxy` todavía no existe.

- [ ] **Step 4: Implementar descubrimiento estricto**

Agregar la dataclass y el recorrido que busca un `VideoMediaSource` con `Content/ProxyMedia`, comprueba que ese `ObjectURef` resuelve a `Media` con `IsProxy=true`, y busca su `AudioMediaSource` hermano con `AudioProxies`. Si falta cualquiera de los enlaces exigidos, lanzar `PlantillaIncompleta` con el tag faltante.

```python
def arquetipo_de_proxy(raiz: ET.Element) -> ArquetipoDeProxy:
    """Describe el cierre que Premiere crea al adjuntar un proxy."""
    # Resolver ObjectID/ObjectUID desde los enlaces, no por nombres de archivo.
```

- [ ] **Step 5: Ejecutar la prueba y la suite de plantilla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_plantilla.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add recursos/premiere/TemplateProxyAdjunto.prproj src/clasificador_video/recursos.py src/clasificador_video/prproj_plantilla.py tests/test_prproj_plantilla.py
git commit -m "Agregar arquetipo de proxy adjunto de Premiere"
```

### Task 2: Formar los nombres cronológicos acordados

**Files:**
- Modify: `src/clasificador_video/nombre_de_clip.py`
- Modify: `tests/test_nombre_de_clip.py`
- Modify: `tests/test_prproj_generador.py`

**Interfaces:**
- Consumes: `nombre_de_clip(cuarto: str, numero: int, marca_de_camara: str, flag: str) -> str`.
- Produces: la misma firma, con formato `CUARTO-01 ✓ [CAMARA]`.

- [ ] **Step 1: Escribir expectativas nuevas en rojo**

```python
def test_nombre_de_clip_usa_mayusculas_guion_y_marca_despues_del_numero():
    assert nombre_de_clip("Cocina", 1, "DRONE", "pick") == "COCINA-01 ✓ [DRONE]"

def test_nombre_de_clip_sin_marca_no_deja_espacio_extra():
    assert nombre_de_clip("Baño", 123, "SONY", "none") == "BAÑO-123 [SONY]"
```

Extender la prueba de integración del generador para exigir esos textos en el árbol visible del bin.

- [ ] **Step 2: Ejecutar pruebas para confirmar rojo**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_nombre_de_clip.py tests/test_prproj_generador.py -q`

Expected: FAIL porque el formato actual usa espacio, conserva minúsculas y antepone la marca.

- [ ] **Step 3: Implementar el formato mínimo**

```python
def nombre_de_clip(cuarto: str, numero: int, marca_de_camara: str, flag: str) -> str:
    base = f"{(cuarto or '').upper()}-{numero:02d}"
    marca = _PREFIJO_POR_FLAG.get(flag, "").strip()
    partes = [base] + ([marca] if marca else [])
    if marca_de_camara:
        partes.append(f"[{marca_de_camara}]")
    return " ".join(partes)
```

No cambiar `numeros_de_clip`: ya cuenta por ruta completa de cuarto y no por cámara.

- [ ] **Step 4: Ejecutar pruebas focalizadas y suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_nombre_de_clip.py tests/test_prproj_generador.py -q && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/nombre_de_clip.py tests/test_nombre_de_clip.py tests/test_prproj_generador.py
git commit -m "Ordenar los nombres de clips para Premiere"
```

### Task 3: Conectar el proxy al original en el `.prproj`

**Files:**
- Modify: `src/clasificador_video/prproj_generador.py`
- Modify: `tests/test_prproj_generador.py`

**Interfaces:**
- Consumes: `clonar_clip(..., ruta_archivo: Path, ...) -> ClipClonado` y `ArquetipoDeProxy`.
- Produces: `adjuntar_proxy(raiz: ET.Element, clip: ClipClonado, arquetipo: ArquetipoDeProxy, ruta_proxy: Path, datos_probe: dict, asignador: AsignadorDeIds) -> None`.

- [ ] **Step 1: Escribir pruebas XML en rojo**

Crear un manifest de dos clips: uno con `ruta_proxy` existente y otro sin proxy. Después de generar, exigir:

```python
assert _proxy_de_video(raiz, item_con_proxy).find("IsProxy").text == "true"
assert _ruta_de(_proxy_de_video(raiz, item_con_proxy)) == str(proxy)
assert _proxy_de_video(raiz, item_sin_proxy) is None
assert len(_clip_items_visibles(raiz)) == 2
assert _audio_proxies_de(raiz, item_con_proxy)
```

Añadir una prueba con una ruta de proxy que no existe y exigir que genere el clip original sin `ProxyMedia`.

- [ ] **Step 2: Ejecutar para confirmar rojo**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -q`

Expected: FAIL porque `generar_prproj` hoy ignora `Clip.ruta_proxy`.

- [ ] **Step 3: Clonar el cierre de proxy y reemplazar sus referencias**

Extender `ClipClonado` con los IDs de su `VideoMediaSource`, `AudioMediaSource`, `Media` y streams del original. A partir de `TemplateProxyAdjunto.prproj`, clonar sólo el cierre de proxy y sus serializadores con `clonar_por_cierre`; usar fronteras para no clonar el original de la plantilla. Reescribir las referencias del cierre para que apunten al `Media`, fuentes y streams del `ClipClonado` real.

```python
def adjuntar_proxy(raiz, clip, arquetipo, ruta_proxy, datos_probe, asignador):
    """Replica el Media proxy, ProxyMedia y AudioProxies de Premiere."""
    # El nuevo Media recibe IsProxy=true y sus rutas propias.
    # ProxyMedia apunta al nuevo Media; MediaSource sigue apuntando al original.
    # AudioProxy conserva el mapeo de canales del arquetipo y apunta al proxy.
```

Invocar esta función inmediatamente después de `clonar_clip` sólo cuando `clip.ruta_proxy` exista. No crear ni agregar un `ClipProjectItem` para el proxy.

- [ ] **Step 4: Actualizar streams desde ffprobe**

Usar el mismo `probe` inyectable que ya recibe `generar_prproj` para actualizar duración, fps, `FrameRect` y orientación de los streams de proxy. Validar que esos valores sean compatibles con el original antes de enlazar; si no calzan, omitir el proxy y conservar el original solo.

- [ ] **Step 5: Ejecutar pruebas focalizadas y suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -q && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/prproj_generador.py tests/test_prproj_generador.py
git commit -m "Adjuntar proxies reales al proyecto de Premiere"
```

### Task 4: Reescribir todas las rutas clonadas

**Files:**
- Modify: `src/clasificador_video/prproj_generador.py`
- Modify: `tests/test_prproj_generador.py`

**Interfaces:**
- Produces: `_reescribir_rutas_de_media(media: ET.Element, ruta: Path) -> None`.

- [ ] **Step 1: Escribir la regresión en rojo**

Crear un `Media` de fixture con dos `RelativePath` distintas y una ruta vieja de otra toma. Exigir que, después de generar, todos los nodos de ruta de cada `Media` clonado estén derivados de la ruta actual.

```python
assert {n.text for n in media.findall("RelativePath")} == {
    ruta_relativa_esperada,
}
assert {n.text for n in media.findall("FilePath")} == {str(ruta_actual)}
assert {n.text for n in media.findall("ActualMediaFilePath")} == {str(ruta_actual)}
```

- [ ] **Step 2: Ejecutar para confirmar rojo**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -q`

Expected: FAIL porque el código usa `find`, que cambia únicamente el primer nodo de cada tipo.

- [ ] **Step 3: Reemplazar todas las copias de ruta**

```python
def _reescribir_rutas_de_media(media: ET.Element, ruta: Path) -> None:
    for nodo in media.findall("RelativePath"):
        nodo.text = _ruta_relativa_de_proyecto(ruta)
    for tag in ("FilePath", "ActualMediaFilePath"):
        for nodo in media.findall(tag):
            nodo.text = str(ruta)
    for nodo in media.findall("Title"):
        nodo.text = ruta.name
```

Calcular la ruta relativa con la misma base que Premiere usa en la plantilla; nunca conservar una ruta de otro clip como fallback.

- [ ] **Step 4: Ejecutar pruebas focalizadas y suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -q && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/prproj_generador.py tests/test_prproj_generador.py
git commit -m "Actualizar todas las rutas de medios en Premiere"
```

### Task 5: Generar proxies `_proxy` con el glifo de Clipify

**Files:**
- Modify: `src/clasificador_video/proxy_gen.py`
- Modify: `src/clasificador_video/recursos.py`
- Modify: `tests/test_proxy_gen.py`
- Modify: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `ruta_de_proxy(original: Path, carpeta: Path) -> Path`.
- Produces: `<stem>_proxy.mp4`.
- Produces: `recursos.marca_de_proxy() -> Path`, una PNG temporal o empacada con transparencia generada a partir de `ui.marca.glifo`.

- [ ] **Step 1: Escribir pruebas en rojo para el nombre y el filtro**

```python
def test_ruta_de_proxy_termina_en_proxy(tmp_path):
    assert ruta_de_proxy(tmp_path / "C0001.MP4", tmp_path) == tmp_path / "C0001_proxy.mp4"

def test_comando_superpone_la_marca_sin_escalar_ni_rotar(tmp_path):
    comando_ffmpeg = comando(tmp_path / "C0001.MP4", tmp_path / "C0001_proxy.mp4")
    filtro = comando_ffmpeg[comando_ffmpeg.index("-filter_complex") + 1]
    assert "overlay=W-w-" in filtro
    assert "scale" not in filtro and "transpose" not in filtro and "setpts" not in filtro
```

Mantener las pruebas que reconocen `S03` y `_proxy` desde `ingest.py`.

- [ ] **Step 2: Ejecutar para confirmar rojo**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py tests/test_ingest.py -q`

Expected: FAIL porque el destino actual termina en `S03` y el comando no tiene overlay.

- [ ] **Step 3: Generar el asset de marca reutilizando el glifo existente**

Crear una función pequeña que pinta `ui.marca.glifo` sobre PNG transparente a un tamaño fijo adecuado para el overlay. No dibujar una segunda versión del símbolo ni usar un carácter de fuente. El recurso debe poder obtenerse tanto desde el repo como desde la app empacada.

- [ ] **Step 4: Implementar el filtro de ffmpeg**

Agregar el PNG como segunda entrada y usar un `filter_complex` equivalente a:

```text
[0:v:0][1:v]overlay=W-w-32:H-h-32:format=auto:alpha=0.35[v]
```

Mapear `[v]` como la única pista de video de salida, conservar `-map 0:a?`, bitrate, codec y formato MP4. No agregar ningún filtro de escala, rotación ni tiempo.

- [ ] **Step 5: Verificar medios horizontal y vertical con ffprobe**

Crear clips cortos de fixture desde lavfi o usar los assets pequeños existentes. Generar ambos proxies y afirmar con `ffprobe` que duración, fps, ancho, alto y rotación son iguales a los del original; extraer un frame y verificar visualmente que la marca esté en la esquina inferior derecha. Guardar las imágenes de esta verificación fuera del repo.

- [ ] **Step 6: Ejecutar pruebas focalizadas y suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py tests/test_ingest.py -q && QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/proxy_gen.py src/clasificador_video/recursos.py tests/test_proxy_gen.py tests/test_ingest.py
git commit -m "Marcar y renombrar los proxies de Clipify"
```

### Task 6: Validación de entrega y guía para Bruno

**Files:**
- Modify: `docs/superpowers/RESULTADO-2026-09-23-generacion-directa-prproj.md`
- Modify: `docs/superpowers/CONTEXTO-Y-METAS.md`

**Interfaces:**
- Consumes: `.prproj` generado por Clipify y proxy creado en la Tarea 5.
- Produces: protocolo manual breve para que Bruno valide el vínculo en Premiere.

- [ ] **Step 1: Ejecutar la suite final**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

Expected: PASS sin ignorar pruebas.

- [ ] **Step 2: Preparar el proyecto de validación sin abrir Premiere**

Generar desde la fuente un proyecto nuevo de Clipify que incluya: un original con proxy horizontal, un original con proxy vertical y uno sin proxy. Anotar SHA, ruta del `.prproj` y rutas de medios en la bitácora. Confirmar por XML que hay exactamente tres `ClipProjectItem` visibles y sólo dos enlaces `ProxyMedia`.

- [ ] **Step 3: Entregar a Bruno la comprobación manual**

Pedirle que abra ese proyecto en Premiere y revise:

1. cada original con proxy aparece una sola vez en su bin;
2. el interruptor de proxies cambia reproducción sin cambiar el medio principal;
3. editar y exportar siguen tomando el original;
4. la marca es discreta y queda abajo a la derecha tanto en horizontal como en vertical;
5. duración, fps, orientación y cuadro coinciden;
6. nombres como `COCINA-01 ✓ [DRONE]` se ordenan cronológicamente.

No abrir Premiere ni modificar el proyecto desde la automatización.

- [ ] **Step 4: Registrar el resultado cuando Bruno responda**

Documentar la respuesta textual de Bruno, la versión de Premiere y cualquier discrepancia entre XML y la interfaz. Si falla, detener la entrega y volver a la comparación de `.prproj`; no agregar rutas o tags por conjetura.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/RESULTADO-2026-09-23-generacion-directa-prproj.md docs/superpowers/CONTEXTO-Y-METAS.md
git commit -m "Documentar validación de proxies en Premiere"
```

## Cobertura del diseño

- Estructura completa de Premiere: Tareas 1 y 3.
- Original principal y proxy no visible como clip: Tarea 3.
- Rutas principales y relativas limpias: Tarea 4.
- `_proxy` más compatibilidad `S03`: Tarea 5.
- Marca visible sin alterar el medio: Tarea 5.
- Nombres cronológicos y marcas al final: Tarea 2.
- Verificación exclusiva de Bruno en Premiere: Tarea 6.
