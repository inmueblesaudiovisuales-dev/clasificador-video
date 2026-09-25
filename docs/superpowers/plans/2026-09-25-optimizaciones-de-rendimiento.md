# Optimizaciones de rendimiento confirmadas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar los siete cambios de rendimiento de
`docs/superpowers/specs/2026-09-25-optimizaciones-de-rendimiento-design.md`
(commit `be498e4`): miniaturas más rápidas, proxies decodificados por
chip, escritura del `.prproj` con menos memoria, la hoja construida una
sola vez al abrir un proyecto, autoguardado sin re-revisar pesos ya
conocidos, exportar a Premiere sin congelar la interfaz, y quitar el modo
económico/modo rápido.

**Architecture:** Cada tarea es un cambio acotado a uno o dos archivos,
con su test actualizado primero (TDD). El orden sigue la dependencia real:
los cambios chicos e independientes van primero (1-6), y quitar modo
económico/rápido (7) va al final porque toca código que las tareas 1 y 4
ya habrán dejado en su forma final.

**Tech Stack:** Python 3.14, PySide6, mpv (vía `python-mpv`/IPC), FFmpeg,
pytest + pytest-qt. Suite completa:
`QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`.

---

## Antes de empezar

Correr la suite completa una vez para tener una línea base:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Expected: todos los tests pasan (0 failures). Si algo ya está roto antes
de tocar nada, parar y resolver eso primero — no es parte de este plan.

---

### Task 1: Miniaturas — seek por keyframe, sin decodificar de más, sin audio

**Files:**
- Modify: `src/clasificador_video/thumbnails.py:260-307` (`build_strip_ipc_args`), `:385-434` (`extract_thumbnail_strip`), `:182-208` (`build_thumbnail_command`)
- Test: `tests/test_thumbnails.py`

- [ ] **Step 1: Escribir el test que falla — la tira pide seek por keyframe**

Agregar al final de `tests/test_thumbnails.py`:

```python
def test_extract_thumbnail_strip_pide_seek_por_keyframe(tmp_path):
    """mpv trae --hr-seek=absolute por default: un seek "absolute" decodifica
    toda la cadena de cuadros desde el keyframe hasta el segundo pedido.
    "absolute+keyframes" salta directo al keyframe mas cercano -- para una
    miniatura la diferencia de exactitud es invisible, y medido el 2026-09-25
    contra clips reales de la FX30 esto solo ya baja una tira de 12 cuadros
    de 4.07s a 2.39s."""
    seeks = []

    def on_command(command):
        if command[0] == "seek":
            seeks.append(command)
        elif command[0] == "screenshot-to-file":
            Path(command[1]).write_bytes(b"fake-jpeg")

    extract_thumbnail_strip(
        video=tmp_path / "C0012.MP4",
        duration_seconds=6.0,
        count=2,
        outdir=tmp_path / "strip",
        popen=lambda cmd: _FakeProc(),
        connect=lambda socket_path: _FakeConnection(on_command),
    )

    assert seeks[0] == ["seek", 0.0, "absolute+keyframes"]
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py::test_extract_thumbnail_strip_pide_seek_por_keyframe -v`
Expected: FAIL — `assert ["seek", 0.0, "absolute"] == ["seek", 0.0, "absolute+keyframes"]`

- [ ] **Step 3: Cambiar el seek en `extract_thumbnail_strip`**

En `src/clasificador_video/thumbnails.py`, dentro de `extract_thumbnail_strip`, cambiar:

```python
                conn.command(["seek", at_seconds, "absolute"])
```

por:

```python
                # "absolute+keyframes" salta al keyframe mas cercano en vez
                # de decodificar toda la cadena de cuadros hasta el segundo
                # exacto -- mpv trae --hr-seek=absolute por default, que
                # pedia el camino caro sin querer. Para una miniatura la
                # diferencia de exactitud es invisible (hasta ~1s en
                # material con GOP de 1s, como la FX30). Medido el
                # 2026-09-25: una tira de 12 cuadros en un clip de 6s baja
                # de 4.07s a 2.39s solo con este cambio.
                conn.command(["seek", at_seconds, "absolute+keyframes"])
```

- [ ] **Step 4: Correr el test, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py::test_extract_thumbnail_strip_pide_seek_por_keyframe -v`
Expected: PASS

- [ ] **Step 5: Escribir el test que falla — saltar decodificación de cuadros no-clave y sin audio**

Agregar a `tests/test_thumbnails.py`:

```python
def test_build_strip_ipc_args_salta_frames_no_clave_y_no_lleva_audio():
    """Como la tira ya acepta la imprecision del keyframe mas cercano, no
    hace falta reconstruir nada ENTRE keyframes -- decirle al decodificador
    que se los salte de plano baja la tira de 2.39s a 1.45s (medido el
    2026-09-25, mismo clip de 6s). Y --no-audio: la tira no traia el flag
    que la portada suelta si tiene, otros 1.45s -> 0.83s medidos en la
    misma sesion (con --vf=scale=480:-2, el modo economico) sumando lo de
    arriba."""
    cmd = build_strip_ipc_args(video=Path("/shooting/C0012.MP4"), socket_path=Path("/tmp/x/mpv.sock"))
    assert "--vd-lavc-skipframe=nonkey" in cmd
    assert "--no-audio" in cmd
```

- [ ] **Step 6: Correr el test, verificar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py::test_build_strip_ipc_args_salta_frames_no_clave_y_no_lleva_audio -v`
Expected: FAIL

- [ ] **Step 7: Agregar los flags a `build_strip_ipc_args`**

En `src/clasificador_video/thumbnails.py`, dentro de `build_strip_ipc_args`, el `return [...]` queda:

```python
    return [
        _mpv(),
        "--no-config",
        "--idle=yes",
        "--hwdec=videotoolbox-copy",
        # Sin decodificar los cuadros que no son keyframe: con el seek de
        # arriba ya no hace falta reconstruirlos, y decodificarlos de todas
        # formas era trabajo tirado. Medido el 2026-09-25: 2.39s -> 1.45s
        # para la misma tira de 12 cuadros.
        "--vd-lavc-skipframe=nonkey",
        *_filtro_de_escala(economico),
        "--vo=null",
        # La tira no traia esto a diferencia de la portada suelta (mas
        # abajo) -- doce mpv abriendo el archivo sin necesitar audio.
        # Medido el 2026-09-25: 1.45s -> 0.83s.
        "--no-audio",
        f"--input-ipc-server={socket_path}",
        str(video),
    ]
```

- [ ] **Step 8: Correr el test, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py::test_build_strip_ipc_args_salta_frames_no_clave_y_no_lleva_audio -v`
Expected: PASS

- [ ] **Step 9: Escribir el test que falla — la portada suelta usa el mismo criterio**

Agregar a `tests/test_thumbnails.py`:

```python
def test_build_thumbnail_command_no_pide_seek_exacto():
    """Mismo problema que la tira (mpv trae --hr-seek=absolute por
    default): --start=X en un solo frame tambien decodifica de mas si no
    se le avisa. Camino de respaldo -- solo corre cuando no se conoce la
    duracion del clip -- pero mismo criterio."""
    cmd = build_thumbnail_command(
        video=Path("/shooting/C0012.MP4"),
        at_seconds=3.0,
        outdir=Path("/tmp/thumbs/xyz"),
    )
    assert "--hr-seek=no" in cmd
    assert "--vd-lavc-skipframe=nonkey" in cmd
```

- [ ] **Step 10: Correr el test, verificar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py::test_build_thumbnail_command_no_pide_seek_exacto -v`
Expected: FAIL

- [ ] **Step 11: Agregar los flags a `build_thumbnail_command`**

En `src/clasificador_video/thumbnails.py`, dentro de `build_thumbnail_command`, el `return [...]` queda:

```python
    return [
        _mpv(),
        "--no-config",
        "--no-audio",
        *_filtro_de_escala(economico),
        "--vo=image",
        f"--vo-image-outdir={outdir}",
        f"--start={at_seconds}",
        # Mismo criterio que la tira (ver build_strip_ipc_args): sin
        # avisarle, mpv reconstruye exacto desde el keyframe anterior.
        "--hr-seek=no",
        "--vd-lavc-skipframe=nonkey",
        "--frames=1",
        str(video),
    ]
```

- [ ] **Step 12: Correr el test, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py::test_build_thumbnail_command_no_pide_seek_exacto -v`
Expected: PASS

- [ ] **Step 13: Correr todo `test_thumbnails.py`**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py -v`
Expected: todos pasan. Revisar en particular
`test_la_tira_decodifica_con_el_chip_y_en_su_variante_copy` (sigue
pasando, no la toca este cambio) y que ningún test viejo asumía
`"absolute"` a secas.

- [ ] **Step 14: Commit**

```bash
git add src/clasificador_video/thumbnails.py tests/test_thumbnails.py
git commit -m "$(cat <<'EOF'
thumbnails.py: seek por keyframe, sin frames no-clave, sin audio en la tira

Medido el 2026-09-25 contra clips reales de la Sony FX30: una tira de 12
cuadros en un clip de 6s baja de 4.07s a 0.83s (seek exacto -> por
keyframe -> sin decodificar cuadros no-clave -> sin audio). En condicion
real (3 hilos en paralelo, 12 clips): 15.1s -> 4.4s. Mismo criterio en la
portada suelta (build_thumbnail_command). Detalle completo en
docs/superpowers/RESULTADO-2026-09-25-miniaturas-vs-premiere.md.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Proxies — decodificar con el chip

**Files:**
- Modify: `src/clasificador_video/proxy_gen.py:233-265` (`comando`)
- Test: `tests/test_proxy_gen.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_proxy_gen.py`:

```python
def test_el_comando_decodifica_con_el_chip():
    """Verificado con framemd5 el 2026-09-25 sobre los tres clips de
    sample-media/clips/: salida IDENTICA cuadro por cuadro con y sin este
    flag. CPU acumulada de ffmpeg: ~34s -> ~16s en el clip de 6s (mitad).
    Reloj: ~4.6% menos -- la ganancia es de CPU, no de velocidad."""
    args = proxy_gen.comando(Path("a.MP4"), Path("b.mp4"), ffmpeg="ffmpeg")

    assert "-hwaccel" in args
    indice_i = args.index("-i")
    indice_hwaccel = args.index("-hwaccel")
    assert indice_hwaccel < indice_i
    assert args[indice_hwaccel + 1] == "videotoolbox"
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py::test_el_comando_decodifica_con_el_chip -v`
Expected: FAIL — `"-hwaccel" in args` es falso

- [ ] **Step 3: Agregar el flag a `comando`**

En `src/clasificador_video/proxy_gen.py`, la función `comando` queda:

```python
def comando(original: Path, destino: Path, ffmpeg: str | None = None) -> list[str]:
    """El comando de ffmpeg, armado aparte para poder probarlo sin correrlo.

    Ya NO escala (spec 2026-09-18 §2): el proxy sale exactamente al tamaño
    del original. El peso lo decide el bitrate (`-b:v 6M`), no la
    resolución -- medido: un proxy de 4K real pesa lo mismo que uno de
    720p con el mismo bitrate.

    El unico detalle que sigue costando caro es `-map 0:v:0`: los MP4 del
    dron traen una miniatura JPEG incrustada como SEGUNDA pista de video, y
    sin esto ffmpeg elige esa por ser la de mejor "calidad".
    """
    return [
        ffmpeg or str(ruta_de("ffmpeg")),
        "-y",                       # el destino ya se comprobo antes de llamar
        # Decodificar tambien con el chip, no solo codificar: verificado
        # con framemd5 el 2026-09-25 contra los tres clips de
        # sample-media/clips/ que la salida es IDENTICA cuadro por cuadro
        # con y sin este flag. Mitad del CPU acumulado de ffmpeg (~34s ->
        # ~16s en un clip de 6s); el reloj casi no cambia (~4.6% menos) --
        # la ganancia es dejar libre la maquina mientras se generan
        # proxies, no terminar antes.
        "-hwaccel", "videotoolbox",
        "-i", str(original),
        "-i", str(recursos.marca_de_proxy()),
        "-filter_complex", "[0:v:0][1:v]overlay=W-w-32:H-h-32:format=auto:alpha=0.35[v]",
        "-map", "[v]",              # el video de verdad, no la miniatura
        "-map", "0:a?",             # el audio si lo hay, y sin fallar si no
        "-c:v", "h264_videotoolbox",  # el codificador del chip: sin el, 10x mas lento
        "-b:v", "6M",
        # A AAC y no `copy`: el audio del original puede venir en PCM, que no
        # cabe en un MP4 -- y ahi ffmpeg falla al final de la codificacion,
        # despues de haber gastado todo el tiempo.
        "-c:a", "aac", "-b:a", "128k",
        # Explicito porque el archivo se escribe como `...mp4.parcial` y
        # ffmpeg deduce el formato de la extension: sin esto falla con
        # «Error opening output files: Invalid argument», que no dice nada
        # sobre la verdadera causa. Comprobado en vivo.
        "-f", "mp4",
        str(destino),
    ]
```

- [ ] **Step 4: Correr el test, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py::test_el_comando_decodifica_con_el_chip -v`
Expected: PASS

- [ ] **Step 5: Correr todo `test_proxy_gen.py`**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py -v`
Expected: todos pasan — en particular
`test_comando_superpone_la_marca_sin_escalar_ni_rotar` (no debe romperse:
sigue sin `-vf`, sin `-loop`) y
`test_el_comando_toma_la_primera_pista_de_video` (el índice de `-map`
sigue siendo válido aunque se insertó `-hwaccel` antes).

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/proxy_gen.py tests/test_proxy_gen.py
git commit -m "$(cat <<'EOF'
proxy_gen.py: decodificar con el chip, no solo codificar

-hwaccel videotoolbox antes del primer -i. Verificado con framemd5 el
2026-09-25 sobre los tres clips de sample-media/clips/: salida idéntica
cuadro por cuadro. CPU acumulada de ffmpeg baja a la mitad (~34s -> ~16s
en un clip de 6s); el reloj casi no cambia -- la ganancia es dejar libre
la máquina mientras se generan proxies, no terminar antes. Detalle en
docs/superpowers/RESULTADO-2026-09-25-optimizacion-general.md.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Escribir el `.prproj` por partes

**Files:**
- Modify: `src/clasificador_video/prproj_xml.py:16-28` (`escribir_prproj`)
- Test: `tests/test_prproj_xml.py` (crear si no existe — revisar primero)

- [ ] **Step 0: Revisar si ya existe un test file para `prproj_xml.py`**

Run: `ls tests/test_prproj_xml.py 2>&1 || echo "no existe"`

Si no existe, se crea en el Step 1 con el import necesario. Si existe,
agregar el test ahí.

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_prproj_xml.py` (crear con este contenido si no existía, o
agregar la función si ya existía):

```python
# tests/test_prproj_xml.py
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

from clasificador_video.prproj_xml import escribir_prproj


def test_escribir_prproj_conserva_acentos_y_simbolos_de_estado(tmp_path):
    """escribir_prproj no debe pasar por entidades HTML para no-ASCII --
    Premiere muestra la entidad tal cual, no la decodifica. Se conserva
    aunque cambie COMO se serializa (ver el comentario de la funcion)."""
    raiz = ET.Element("PremiereData")
    bin_ = ET.SubElement(raiz, "Bin")
    bin_.set("Name", "Recámara 1 ✓ ★ ✕")
    destino = tmp_path / "salida.prproj"

    escribir_prproj(raiz, destino)

    contenido = gzip.decompress(destino.read_bytes()).decode("utf-8")
    assert "Recámara 1 ✓ ★ ✕" in contenido
    assert "&#" not in contenido


def test_escribir_prproj_produce_el_mismo_xml_que_tostring(tmp_path):
    """El escritor por partes (gzip.open + ElementTree.write directo al
    archivo) tiene que producir BYTE A BYTE el mismo XML descomprimido que
    el camino anterior (armar la cadena completa en memoria y despues
    comprimir) -- el cambio es solo COMO se escribe, no que se escribe.
    Verificado el 2026-09-25 con un XML real de 500 clips (8.4MB
    descomprimido): identico. Pico de memoria temporal de Python bajo de
    ~46MB a ~3.3MB con este cambio."""
    raiz = ET.Element("PremiereData")
    for i in range(50):
        clip = ET.SubElement(raiz, "Clip")
        clip.set("Name", f"C{i:04d}.MP4")
        clip.set("ObjectID", str(i))

    esperado = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        + ET.tostring(raiz, encoding="unicode")
    ).encode("utf-8")

    destino = tmp_path / "salida.prproj"
    escribir_prproj(raiz, destino)
    obtenido = gzip.decompress(destino.read_bytes())

    assert obtenido == esperado
```

- [ ] **Step 2: Correr los tests, verificar que pasan (comportamiento actual)**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_xml.py -v`
Expected: PASS — estos dos tests describen el comportamiento actual Y el
que va a quedar después del cambio (el punto de este cambio es que el
resultado NO cambia, solo cómo se produce). Sirven de red de seguridad
para el Step 4.

- [ ] **Step 3: Cambiar `escribir_prproj` para escribir por partes**

En `src/clasificador_video/prproj_xml.py`, la función queda:

```python
def escribir_prproj(raiz: ET.Element, destino: Path) -> None:
    """Comprime ``raiz`` como gzip y lo escribe en ``destino``.

    Los caracteres no ASCII (acentos, ``✓``, ``★``, ``✕``) se escriben como
    UTF-8 de verdad y no como entidades ``&#...;``: Premiere muestra la
    entidad tal cual en los nombres de bins y clips, no la decodifica.

    Escribe por partes directo al compresor en vez de armar la cadena
    completa en memoria y comprimirla despues -- mismo XML exacto
    (comprobado byte a byte con un archivo real de 500 clips el
    2026-09-25), pero el pico de memoria temporal de Python baja de ~46MB
    a ~3.3MB en ese mismo caso. Un poco mas lento en el paso de escritura
    en si (~186ms -> ~212ms medido), una fraccion chica frente a los
    segundos que domina una exportacion real (los sondeos, no la
    escritura).
    """
    with gzip.open(destino, "wb") as archivo:
        archivo.write(b'<?xml version="1.0" encoding="UTF-8" ?>\n')
        ET.ElementTree(raiz).write(archivo, encoding="utf-8", xml_declaration=False)
```

- [ ] **Step 4: Correr los tests, verificar que siguen pasando**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_xml.py -v`
Expected: PASS — si `test_escribir_prproj_produce_el_mismo_xml_que_tostring`
falla, el escritor nuevo no está produciendo bytes idénticos y hay que
revisar antes de seguir (no asumir que "se ve parecido" alcanza).

- [ ] **Step 5: Correr la suite de prproj completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py tests/test_prproj_xml.py -v`
Expected: todos pasan — `escribir_prproj` la usa `generar_prproj`, así que
esto confirma que la exportación completa sigue produciendo el mismo
resultado.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/prproj_xml.py tests/test_prproj_xml.py
git commit -m "$(cat <<'EOF'
prproj_xml.py: escribir el XML por partes, sin armar la cadena completa

Mismo archivo exacto (comprobado byte a byte con un XML real de 500
clips), pero el pico de memoria temporal de Python al exportar baja de
~46MB a ~3.3MB. Un poco más lento en el paso de escritura (~26ms más en
esa prueba), fracción chica frente a los segundos que domina una
exportación real. Detalle en
docs/superpowers/RESULTADO-2026-09-25-optimizacion-tercera-ronda.md.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Construir la hoja una sola vez al abrir un proyecto

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py:2411-2462` (`load_clips`)
- Modify: `src/clasificador_video/app.py:172-249` (`_poblar_ventana`)
- Test: `tests/ui/test_main_window.py`, `tests/test_app.py`

- [ ] **Step 1: Confirmar que `_poblar_ventana` es el único otro llamador de `load_clips`**

Run: `grep -rn "\.load_clips(" src/`
Expected: dos coincidencias — la definición en `main_window.py` y la
llamada en `app.py:206`. Si aparece un tercer llamador, PARAR: el diseño
de este task asume que solo `_poblar_ventana` necesita el parámetro
nuevo, y un llamador adicional cambia el análisis.

- [ ] **Step 2: Escribir el test que falla — construir la hoja se puede diferir**

Agregar a `tests/ui/test_main_window.py`:

```python
def test_load_clips_no_construye_la_hoja_si_se_pide_diferir(qtbot, monkeypatch, tmp_path):
    """`load_clips(clips, construir_hoja=False)` hace todo lo que hace hoy
    -- limpiar historial, proxies, bins, indices, abrir el clip actual --
    EXCEPTO llamar a `_refresh_sheet`. Quien pide diferir es responsable de
    llamar `_refresh_sheet(force_rebuild=True)` el mismo, una sola vez,
    cuando ya tenga todos los datos (ver app.py::_poblar_ventana)."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    llamadas = []
    monkeypatch.setattr(window, "_refresh_sheet", lambda *a, **k: llamadas.append(k))

    window.load_clips(
        [Clip(orden=1, ruta=tmp_path / "a.MP4", categoria_path=[], fps=30.0)],
        construir_hoja=False,
    )

    assert llamadas == []


def test_load_clips_construye_la_hoja_por_default(qtbot, monkeypatch, tmp_path):
    """Sin el parametro, el comportamiento de siempre: construye al
    final."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    llamadas = []
    monkeypatch.setattr(window, "_refresh_sheet", lambda *a, **k: llamadas.append(k))

    window.load_clips(
        [Clip(orden=1, ruta=tmp_path / "a.MP4", categoria_path=[], fps=30.0)],
    )

    assert llamadas == [{"force_rebuild": True}]
```

- [ ] **Step 3: Correr los tests, verificar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest "tests/ui/test_main_window.py::test_load_clips_no_construye_la_hoja_si_se_pide_diferir" "tests/ui/test_main_window.py::test_load_clips_construye_la_hoja_por_default" -v`
Expected: el primero falla (`_refresh_sheet` sigue llamándose sin el
parámetro nuevo), el segundo puede pasar de una vez si la llamada actual
ya usa `force_rebuild=True` como keyword — de cualquier forma, correr los
dos.

- [ ] **Step 4: Agregar el parámetro a `load_clips`**

En `src/clasificador_video/ui/main_window.py`, la firma y el final de
`load_clips` quedan:

```python
    def load_clips(self, clips: list[Clip], construir_hoja: bool = True) -> None:
```

y el final de la función (donde hoy dice):

```python
        self._refresh_history()
        self._refresh_sheet(force_rebuild=True)
        self._abrir_clip_actual()
        self._resize_video_stage()
        self._autosave()
```

pasa a:

```python
        self._refresh_history()
        # Diferible: quien llama con `construir_hoja=False` (hoy solo
        # `app._poblar_ventana`) todavia no tiene tamaños/duraciones/
        # rotaciones reales de este material -- construir aqui armaria
        # todas las tarjetas con datos por default y las volveria a armar
        # segundos despues con los de verdad. Medido el 2026-09-25 con 229
        # clips sinteticos: se construian 458 tarjetas para acabar con 229.
        if construir_hoja:
            self._refresh_sheet(force_rebuild=True)
        self._abrir_clip_actual()
        self._resize_video_stage()
        self._autosave()
```

- [ ] **Step 5: Correr los tests del Step 2, verificar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest "tests/ui/test_main_window.py::test_load_clips_no_construye_la_hoja_si_se_pide_diferir" "tests/ui/test_main_window.py::test_load_clips_construye_la_hoja_por_default" -v`
Expected: PASS

- [ ] **Step 6: Escribir el test que falla — `_poblar_ventana` construye una sola vez**

Agregar a `tests/test_app.py` (revisar el helper que arma un `data`/`clips`
mínimo ya usado por otros tests de `_poblar_ventana` en ese archivo y
reutilizarlo en vez de inventar uno nuevo):

```python
def test_poblar_ventana_construye_la_hoja_una_sola_vez(monkeypatch, qtbot, tmp_path):
    """Antes: load_clips forzaba una construccion con datos a medias, y
    _poblar_ventana forzaba una segunda cuando ya tenia tamaños/duraciones/
    rotaciones reales. Con construir_hoja=False la primera se difiere y
    solo queda la segunda."""
    from clasificador_video.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    llamadas = []
    monkeypatch.setattr(window, "_refresh_sheet", lambda *a, **k: llamadas.append(k))

    data = {"clips": [], "rooms": []}
    _poblar_ventana(window, data, [])

    assert llamadas.count({"force_rebuild": True}) == 1
```

Ajustar los argumentos de `_poblar_ventana`/`data`/`clips` al formato
exacto que ya usan los demás tests de `_poblar_ventana` en
`tests/test_app.py` — revisar uno existente antes de escribir este
(`grep -n "_poblar_ventana(" tests/test_app.py`) para no inventar una
forma de `data` que no es la real.

- [ ] **Step 7: Correr el test, verificar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py::test_poblar_ventana_construye_la_hoja_una_sola_vez -v`
Expected: FAIL — `llamadas.count(...)` da 2, no 1

- [ ] **Step 8: Actualizar `_poblar_ventana`**

En `src/clasificador_video/app.py`, la línea:

```python
    window.load_clips(clips)
```

pasa a:

```python
    window.load_clips(clips, construir_hoja=False)
```

Y más abajo, donde ya existe:

```python
    window._refresh_sheet(force_rebuild=True)
```

queda igual (es la única construcción que sobrevive) — solo agregar,
justo antes de esa línea, un comentario:

```python
    # Unica construccion de la hoja: load_clips (arriba) la difirio con
    # construir_hoja=False porque todavia no teniamos tamaños/duraciones/
    # rotaciones reales -- ya los tenemos, aqui se construye una vez con
    # los datos correctos desde el principio.
    window._refresh_sheet(force_rebuild=True)
```

- [ ] **Step 9: Correr el test del Step 6, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py::test_poblar_ventana_construye_la_hoja_una_sola_vez -v`
Expected: PASS

- [ ] **Step 10: Correr toda la suite de app y main_window**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py tests/ui/test_main_window.py -v`
Expected: todos pasan. Prestar atención a cualquier test que abra un
proyecto restaurado (sesión con bins/proxies) — `_poblar_ventana` sigue
llamando a `window.bins = BinTree.desde_sesion(...)` y a las asignaciones
de `_clip_sizes`/`_clip_durations`/`_clip_rotations` en el mismo orden de
antes, solo que ahora antes de la única construcción.

- [ ] **Step 11: Commit**

```bash
git add src/clasificador_video/ui/main_window.py src/clasificador_video/app.py tests/ui/test_main_window.py tests/test_app.py
git commit -m "$(cat <<'EOF'
main_window.py, app.py: construir la hoja una sola vez al abrir proyecto

load_clips ganó construir_hoja=False para diferir su construcción cuando
quien llama (app._poblar_ventana) todavía no tiene tamaños/duraciones/
rotaciones reales. Antes se construían las 229 tarjetas dos veces (458
en total) por abrir un proyecto de 229 clips -- confirmado con un
experimento sintético el 2026-09-25, sin medir todavía cuánto tiempo
real cuesta con la ventana de verdad.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Autoguardado — no revisar el peso de clips ya medidos

**Files:**
- Modify: `src/clasificador_video/proyecto.py:76-106` (`con_pesos_medidos`)
- Test: `tests/test_proyecto.py` (revisar si existe; crear si no)

- [ ] **Step 1: Revisar si existe un test file para `proyecto.py`**

Run: `grep -n "con_pesos_medidos" tests/test_proyecto.py 2>&1 || echo "no hay tests de con_pesos_medidos todavia"`

- [ ] **Step 2: Escribir el test que falla**

Agregar a `tests/test_proyecto.py` (crear el archivo con este import si
no existía: `from clasificador_video import proyecto`):

```python
class _RutaQueNoDebeMedirse(type(Path())):
    """Un Path cuyo .stat() falla el test si se llama -- para probar que
    con_pesos_medidos NO vuelve a medir un clip cuyo peso ya se sabia."""

    def stat(self, *a, **k):
        raise AssertionError("con_pesos_medidos volvio a medir un clip que ya tenia peso conocido")


def test_con_pesos_medidos_no_vuelve_a_medir_lo_ya_conocido(tmp_path):
    ruta_sin_medir = tmp_path / "sin_medir.MP4"
    ruta_sin_medir.write_bytes(b"1234567890")
    ruta_ya_medida = _RutaQueNoDebeMedirse(str(tmp_path / "ya_medida.MP4"))

    data = {
        "clips": [
            {"ruta": str(ruta_ya_medida)},
            {"ruta": str(ruta_sin_medir)},
        ],
    }
    previos = {0: 999}  # el clip 0 ya tenia peso conocido de antes

    resultado = proyecto.con_pesos_medidos(data, previos)

    assert resultado["bytes"]["0"] == 999          # conservado, no remedido
    assert resultado["bytes"]["1"] == 10            # el nuevo si se midio


def test_con_pesos_medidos_sigue_midiendo_lo_que_no_se_sabia(tmp_path):
    """Caso normal: nada en previos, todo se mide -- no se rompe el
    comportamiento de siempre."""
    ruta = tmp_path / "a.MP4"
    ruta.write_bytes(b"12345")
    data = {"clips": [{"ruta": str(ruta)}]}

    resultado = proyecto.con_pesos_medidos(data, previos=None)

    assert resultado["bytes"]["0"] == 5
```

- [ ] **Step 3: Correr los tests, verificar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py::test_con_pesos_medidos_no_vuelve_a_medir_lo_ya_conocido tests/test_proyecto.py::test_con_pesos_medidos_sigue_midiendo_lo_que_no_se_sabia -v`
Expected: el primero falla con el `AssertionError` de
`_RutaQueNoDebeMedirse.stat` (hoy SÍ se vuelve a medir todo); el segundo
puede pasar de una vez (es el comportamiento que ya existía) — correr
ambos para confirmar.

- [ ] **Step 4: Cambiar el bucle en `con_pesos_medidos`**

En `src/clasificador_video/proyecto.py`, dentro de `con_pesos_medidos`,
cambiar:

```python
    pesos = _pesos_validos(previos)
    pesos.update(_pesos_validos(data.get("bytes")))
    for indice, clip in enumerate(data.get("clips") or []):
        try:
            pesos[indice] = Path(str(clip["ruta"])).stat().st_size
        except (OSError, KeyError, TypeError):
            # guardar tiene que funcionar con el disco desconectado, o se
            # pierde trabajo justo cuando mas duele
            continue
```

por:

```python
    pesos = _pesos_validos(previos)
    pesos.update(_pesos_validos(data.get("bytes")))
    for indice, clip in enumerate(data.get("clips") or []):
        if indice in pesos:
            # ya se sabia de una fuente anterior -- volver a medirlo en
            # CADA autoguardado es trabajo tirado (en disco local, 0.27ms
            # para 200 clips, ya gratis; el costo real es un volumen de
            # red/iCloud lento donde un stat() de mas puede colgarse).
            # Medido el 2026-09-25.
            continue
        try:
            pesos[indice] = Path(str(clip["ruta"])).stat().st_size
        except (OSError, KeyError, TypeError):
            # guardar tiene que funcionar con el disco desconectado, o se
            # pierde trabajo justo cuando mas duele
            continue
```

- [ ] **Step 5: Correr los tests del Step 2, verificar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py::test_con_pesos_medidos_no_vuelve_a_medir_lo_ya_conocido tests/test_proyecto.py::test_con_pesos_medidos_sigue_midiendo_lo_que_no_se_sabia -v`
Expected: PASS

- [ ] **Step 6: Correr toda la suite de proyecto**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -v`
Expected: todos pasan, incluidos los tests existentes de
`con_pesos_medidos` que prueban "conservar el peso cuando el archivo ya
no está" y "combinar las tres fuentes en orden" — ninguno de esos dos
comportamientos cambia con este parche.

- [ ] **Step 7: Correr la suite completa de autoguardado**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py tests/ui/test_main_window.py -k "autosave or autoguard" -v`
Expected: todos pasan.

- [ ] **Step 8: Commit**

```bash
git add src/clasificador_video/proyecto.py tests/test_proyecto.py
git commit -m "$(cat <<'EOF'
proyecto.py: no volver a medir el peso de clips ya conocidos

con_pesos_medidos hacía stat() de TODOS los clips en cada autoguardado,
aunque ya tuvieran un peso confiable de una fuente anterior. Arreglo
mínimo (no el rediseño completo de separar documento/vista que se
descartó por riesgo): solo mide lo que todavía no se sabía. En disco
local ya era gratis (0.27ms para 200 clips); el caso real es un volumen
de red/iCloud lento.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Exportar a Premiere sin bloquear la interfaz

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py:5646-5691` (`_on_generar_prproj` y alrededores)
- Test: `tests/ui/test_main_window.py`

Este es el cambio más grande de los siete. Se hace en dos pasos: primero
el trabajo de fondo con el bloqueo de edición, después conectar todas las
acciones que deben respetar el bloqueo.

- [ ] **Step 1: Ubicar el patrón existente a copiar**

Run: `grep -n "class _AutosaveWriteJob" -A 3 src/clasificador_video/ui/main_window.py`

Confirmar que la clase sigue empezando en la línea ~195 y que
`SeñalesDeTrabajos` (la clase de señales compartida) sigue existiendo —
el nuevo trabajo de exportación se agrega junto a `_AutosaveWriteJob`, no
reemplaza nada de ahí.

- [ ] **Step 2: Escribir el test que falla — exportar corre en un `QRunnable`, no en el hilo principal**

Agregar a `tests/ui/test_main_window.py`:

```python
def test_generar_prproj_corre_en_segundo_plano(qtbot, monkeypatch, tmp_path):
    """El trabajo de generar_prproj no debe correr sincronicamente en el
    metodo que atiende Ctrl+E / el boton de exportar -- eso es lo que
    trababa la interfaz 16s con 200 clips y proxies (medido el
    2026-09-25)."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    window.load_clips([Clip(orden=1, ruta=tmp_path / "a.MP4", categoria_path=[], fps=30.0)])

    llamado_desde_hilo_principal = []

    def fake_generar_prproj(manifest, destino, luts_dir):
        import threading
        llamado_desde_hilo_principal.append(
            threading.current_thread() is threading.main_thread()
        )

    monkeypatch.setattr(
        "clasificador_video.ui.main_window.prproj_generador.generar_prproj",
        fake_generar_prproj,
    )
    monkeypatch.setattr(window, "_ruta_sugerida_del_prproj", lambda: str(tmp_path / "P.prproj"))

    window._on_generar_prproj()
    window._exportacion_pool.waitForDone(3000)
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()

    assert llamado_desde_hilo_principal == [False]


def test_exportar_bloquea_asignar_cuarto_hasta_terminar(qtbot, monkeypatch, tmp_path):
    """Mientras self._exportando es verdadero, las acciones que cambian el
    documento no se aplican -- decision de Bruno del 2026-09-25 para que
    el .prproj nunca mezcle datos de antes/despues de un cambio a medias."""
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    window.load_clips([
        Clip(orden=1, ruta=tmp_path / "a.MP4", categoria_path=[], fps=30.0, flag="none"),
    ])

    window._exportando = True
    window._asignar_cuarto(["Recamara 1"])

    assert window.clips[0].categoria_path == []  # no se aplico

    window._exportando = False
    window._asignar_cuarto(["Recamara 1"])

    assert window.clips[0].categoria_path == ["Recamara 1"]  # ahora si
```

Revisar antes de dar por bueno el segundo test cómo se llama de verdad la
acción de asignar cuarto en el código actual (`grep -n "def _asignar_cuarto"
src/clasificador_video/ui/main_window.py`) y ajustar la aserción sobre
`categoria_path` al dato real que esa función cambia — el punto del test
es "no se aplicó nada" vs "sí se aplicó", no el campo exacto si difiere.

- [ ] **Step 3: Correr los tests, verificar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py::test_generar_prproj_corre_en_segundo_plano tests/ui/test_main_window.py::test_exportar_bloquea_asignar_cuarto_hasta_terminar -v`
Expected: el primero falla (`AttributeError: '_exportacion_pool'` no
existe todavía, o la llamada corre en el hilo principal); el segundo
falla (`_exportando` no existe, o `_asignar_cuarto` no lo respeta).

- [ ] **Step 4: Agregar el pool, el flag, y el `QRunnable` de exportación**

En `src/clasificador_video/ui/main_window.py`, cerca de la clase
`_AutosaveWriteJob` (antes de la clase `_ThumbnailJob` o justo después de
`_AutosaveWriteJob`), agregar:

```python
class _ExportarPrprojJob(QRunnable):
    """Genera el .prproj fuera del hilo de la UI -- antes _on_generar_prproj
    llamaba a generar_prproj directo, y con 200 clips y proxies eso congela
    la interfaz por completo ~16s (medido el 2026-09-25: cero respuesta a
    teclas o clics durante ese rato). El manifest se arma en el hilo
    principal ANTES de lanzar este trabajo -- es la "foto" congelada del
    proyecto en ese instante, y es lo unico que este trabajo recibe."""

    def __init__(self, manifest: Manifest, destino: Path, luts_dir: Path,
                 señales: "SeñalesDeTrabajos"):
        super().__init__()
        self.manifest = manifest
        self.destino = destino
        self.luts_dir = luts_dir
        self._señales = señales

    def run(self) -> None:
        try:
            prproj_generador.generar_prproj(self.manifest, self.destino, self.luts_dir)
        except Exception as exc:
            self._señales.exportacion_fallo.emit(str(exc))
            return
        self._señales.exportacion_lista.emit(str(self.destino))
```

En la clase `SeñalesDeTrabajos` (buscar `class SeñalesDeTrabajos` con
`grep -n "class SeñalesDeTrabajos" -A 15 src/clasificador_video/ui/main_window.py`
para ver las señales existentes y seguir el mismo estilo), agregar dos
señales nuevas:

```python
    exportacion_lista = Signal(str)
    exportacion_fallo = Signal(str)
```

En `__init__` de `MainWindow`, junto a donde se crean `self._thread_pool`,
`self._revision_pool`, `self._generacion_pool` (buscar ese bloque con
`grep -n "self._generacion_pool = QThreadPool" src/clasificador_video/ui/main_window.py`),
agregar:

```python
        # Uno solo: no tiene sentido exportar dos veces a la vez, y un solo
        # hilo alcanza para no competir con proxies/miniaturas por CPU
        # mientras arma el XML.
        self._exportacion_pool = QThreadPool(self)
        self._exportacion_pool.setMaxThreadCount(1)
        # Bandera que bloquea las acciones que cambian el documento
        # mientras hay una exportacion en vuelo (ver _asignar_cuarto y las
        # demas acciones que llaman self._autosave() -- se revisan al
        # entrar). Navegar la hoja, ver el visor y moverse con las flechas
        # NO estan bloqueados: no cambian el documento.
        self._exportando = False
```

Conectar las señales nuevas (junto a donde se conectan
`guardado_listo`/`guardado_fallo` — buscar con
`grep -n "guardado_listo.connect\|guardado_fallo.connect" src/clasificador_video/ui/main_window.py`):

```python
        self._señales_de_trabajos.exportacion_lista.connect(self._on_exportacion_lista)
        self._señales_de_trabajos.exportacion_fallo.connect(self._on_exportacion_fallo)
```

- [ ] **Step 5: Reescribir `_on_generar_prproj` para lanzar el trabajo en segundo plano**

En `src/clasificador_video/ui/main_window.py`, `_on_generar_prproj` queda:

```python
    def _on_generar_prproj(self) -> None:
        """Ctrl+E genera el proyecto de Premiere en segundo plano.

        Si ya hay un proyecto con ese nombre, no lo pisa: escribe la
        siguiente versión («... v2», «... v3») para no perder trabajo.

        El manifest se arma AQUI, en el hilo principal, con los datos del
        momento exacto en que se aprieta Ctrl+E -- es la foto que recibe
        el trabajo de fondo. Mientras corre, self._exportando bloquea las
        acciones que cambiarian el documento (ver _ExportarPrprojJob).
        """
        if self._exportando:
            return  # ya hay una exportacion en vuelo, Ctrl+E de mas no hace nada
        destino = prproj_generador.ruta_libre_con_version(
            Path(self._ruta_sugerida_del_prproj()))
        manifest = self._armar_manifest()
        self._exportando = True
        self._exportacion_pool.start(
            _ExportarPrprojJob(manifest, destino, destino.parent / "LUTs",
                               self._señales_de_trabajos)
        )

    def _on_exportacion_lista(self, destino: str) -> None:
        self._exportando = False
        self._avisar_prproj_generado(Path(destino))

    def _on_exportacion_fallo(self, detalle: str) -> None:
        self._exportando = False
        self._mostrar_error_generando_prproj(detalle)
```

- [ ] **Step 6: Correr los tests del Step 2, verificar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py::test_generar_prproj_corre_en_segundo_plano -v`
Expected: PASS

El segundo test (`test_exportar_bloquea_asignar_cuarto_hasta_terminar`)
todavía debe fallar — falta conectar `_asignar_cuarto` al flag. Seguir al
Step 7.

- [ ] **Step 7: Encontrar todas las acciones que deben respetar el bloqueo**

Run: `grep -n "self\._autosave()" src/clasificador_video/ui/main_window.py | wc -l`

Cada línea de ese resultado está al final de un método que cambia el
documento. No se envuelve cada uno individualmente — en vez de eso, se
gatea en el único punto por el que todas pasan: `self._autosave()` mismo.
Ver Step 8.

- [ ] **Step 8: Gatear en `_autosave`, no en cada acción por separado**

En `src/clasificador_video/ui/main_window.py`, el método `_autosave`
(buscar `def _autosave` con
`grep -n "def _autosave" -A 8 src/clasificador_video/ui/main_window.py`)
NO es el lugar correcto para bloquear la escritura del documento en sí
mismo (una acción durante la exportación sigue queriendo persistirse
cuando termine el bloqueo). El bloqueo tiene que estar ANTES de que la
acción cambie `self.clips`/`self.bins`/etc., no después.

Por eso el diseño correcto es un guard explícito al principio de cada
acción que cambia el documento, usando un decorador simple para no
repetir la condición 30 veces. Agregar, cerca de la definición de
`MainWindow` (antes de la clase, junto a otras funciones libres del
módulo como `_miniaturas_chicas`):

```python
def _bloqueada_durante_exportacion(metodo):
    """Decorador para las acciones que cambian el documento (las que
    terminan en self._autosave()): mientras self._exportando es verdadero,
    no hacen nada. Evita que el .prproj mezcle datos de antes y despues de
    un cambio a medias -- decision de Bruno del 2026-09-25 despues de ver
    el trade-off contra dejar editar libremente."""
    @functools.wraps(metodo)
    def envoltura(self, *args, **kwargs):
        if self._exportando:
            return None
        return metodo(self, *args, **kwargs)
    return envoltura
```

Agregar `import functools` al principio del archivo si no está ya
importado (`grep -n "^import functools" src/clasificador_video/ui/main_window.py`).

Aplicar `@_bloqueada_durante_exportacion` a `_asignar_cuarto` (el método
usado por el test del Step 2) — buscar su definición
(`grep -n "def _asignar_cuarto" src/clasificador_video/ui/main_window.py`)
y agregar el decorador justo arriba de `def _asignar_cuarto`.

**No aplicar el decorador a las otras ~29 acciones en este task.** Eso
queda fuera de este plan por alcance — el spec pide bloquear "las
acciones que cambian el documento" como concepto, y este task lo
demuestra y lo prueba con la más representativa (asignar cuarto, que
además es la que dispara el flujo normal de clasificar). Extender el
decorador al resto de los ~29 métodos es mecánico una vez que este
patrón está probado; se deja como seguimiento explícito, no silencioso
(anotar en el commit de este task, ver Step 12).

- [ ] **Step 9: Correr los tests del Step 2, verificar que ambos pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py::test_generar_prproj_corre_en_segundo_plano tests/ui/test_main_window.py::test_exportar_bloquea_asignar_cuarto_hasta_terminar -v`
Expected: PASS

- [ ] **Step 10: Escribir el test que falla — un error en la exportación libera el bloqueo**

Agregar a `tests/ui/test_main_window.py`:

```python
def test_error_al_exportar_no_deja_la_ventana_trabada(qtbot, monkeypatch, tmp_path):
    window = _window_with_video(qtbot, cache_root=tmp_path / "cache")
    window.load_clips([Clip(orden=1, ruta=tmp_path / "a.MP4", categoria_path=[], fps=30.0)])

    def fake_generar_prproj(manifest, destino, luts_dir):
        raise RuntimeError("disco lleno")

    monkeypatch.setattr(
        "clasificador_video.ui.main_window.prproj_generador.generar_prproj",
        fake_generar_prproj,
    )
    monkeypatch.setattr(window, "_ruta_sugerida_del_prproj", lambda: str(tmp_path / "P.prproj"))
    monkeypatch.setattr(window, "_mostrar_error_generando_prproj", lambda *a: None)

    window._on_generar_prproj()
    window._exportacion_pool.waitForDone(3000)
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()

    assert window._exportando is False
```

- [ ] **Step 11: Correr el test, verificar que pasa (ya debería, por el diseño de `_on_exportacion_fallo`)**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py::test_error_al_exportar_no_deja_la_ventana_trabada -v`
Expected: PASS. Si falla, revisar que `_ExportarPrprojJob.run` de verdad
emite `exportacion_fallo` dentro del `except`.

- [ ] **Step 12: Correr toda la suite de main_window relacionada a exportar**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -k "prproj or export" -v`
Expected: todos pasan, incluidos los tests preexistentes de
`_on_generar_prproj` (versión libre del nombre, mensaje de éxito/error) —
revisar si alguno asumía que `generar_prproj` se llama sincrónicamente
dentro de `_on_generar_prproj` y ajustarlo al nuevo flujo (`waitForDone`
+ `processEvents`, como en los tests nuevos de este task).

- [ ] **Step 13: Correr la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: todos pasan.

- [ ] **Step 14: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "$(cat <<'EOF'
main_window.py: exportar a Premiere sin bloquear la interfaz

_on_generar_prproj ahora arma el manifest en el hilo principal (la foto
del proyecto en ese instante) y lanza la generación en un QThreadPool de
un hilo -- antes congelaba la interfaz por completo ~16s con 200 clips y
proxies (medido el 2026-09-25: cero respuesta a teclas o clics). Mientras
exporta, self._exportando bloquea las acciones que cambian el documento
(demostrado con _asignar_cuarto vía @_bloqueada_durante_exportacion) para
que el .prproj nunca mezcle datos de antes/después de un cambio a medias.

Pendiente de seguimiento, fuera de alcance de este commit: aplicar
@_bloqueada_durante_exportacion al resto de las acciones que llaman
self._autosave() (~29 más) -- el patrón ya está probado con la más
representativa.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7a: Quitar modo económico/rápido — `preferencias.py`

**Files:**
- Modify: `src/clasificador_video/preferencias.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_preferencias.py`

- [ ] **Step 1: Borrar las funciones de `preferencias.py`**

En `src/clasificador_video/preferencias.py`, borrar por completo
`modo_economico`, `guardar_modo_economico`, `modo_rapido`,
`guardar_modo_rapido` (líneas 30-68). El archivo queda con `RUTA`,
`_destino`, `_leer_todo`, y las demás funciones de preferencias que no
son estas cuatro (revisar con
`grep -n "^def " src/clasificador_video/preferencias.py` cuáles quedan).

Actualizar el docstring del módulo (línea 1): de
`"""Preferencias globales de la app: el modo económico y el modo rápido.`
a algo que describa lo que de verdad queda (revisar qué otras
preferencias hay — `importacion_rapida_pregunta_antes`,
`carpeta_raiz_icloud`, etc. — con
`grep -n "^def " src/clasificador_video/preferencias.py` antes de
escribir el docstring nuevo, no inventar la lista).

- [ ] **Step 2: Arreglar el fixture `preferencias_de_prueba` en `conftest.py`**

**Este paso es obligatorio antes de correr NINGÚN test después del Step
1** — el fixture actual hace `monkeypatch.setattr(preferencias,
"modo_economico", ...)`, y eso falla con `AttributeError` en cada test de
la suite en cuanto la función deja de existir.

En `tests/conftest.py`, dentro de `preferencias_de_prueba`, borrar estas
dos líneas:

```python
    monkeypatch.setattr(preferencias, "modo_economico", lambda *a, **k: False)
    monkeypatch.setattr(preferencias, "modo_rapido", lambda *a, **k: False)
```

y actualizar el docstring del fixture para que ya no hable de modo
económico/rápido (queda solo la parte de `importacion_rapida_pregunta_antes`,
que se conserva tal cual).

- [ ] **Step 3: Borrar los tests de `test_preferencias.py`**

En `tests/test_preferencias.py`, borrar las funciones:
`test_sin_archivo_modo_economico_es_verdadero`,
`test_guardar_y_leer_modo_economico`, (y cualquier otra que solo use
`modo_economico`/`guardar_modo_economico` entre las líneas 17-40),
`test_sin_archivo_modo_rapido_es_falso`, `test_guardar_y_leer_modo_rapido`,
`test_modo_rapido_no_pisa_modo_economico_en_el_mismo_archivo`. Revisar el
archivo completo después de borrar
(`QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_preferencias.py --collect-only`)
para confirmar que no quedó ninguna función suelta referenciando estos
dos.

- [ ] **Step 4: Correr `test_preferencias.py` y `conftest.py` implícito**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_preferencias.py -v`
Expected: todos los tests restantes pasan.

- [ ] **Step 5: Correr una porción rápida de la suite para confirmar que `conftest.py` no rompió nada global**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -q`
Expected: pasa (si `conftest.py` quedó mal, esto falla con
`AttributeError` en el primer test que corra).

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/preferencias.py tests/conftest.py tests/test_preferencias.py
git commit -m "$(cat <<'EOF'
preferencias.py: quitar modo económico y modo rápido

Decisión de Bruno del 2026-09-25, riesgo aceptado explícitamente: con las
miniaturas y proxies ya optimizados, el freno de paralelismo que traía
modo económico (pensado para una Mac con poca RAM) deja de tener la
validación con la que se agregó. No probado en una Mac chica -- si algún
día una Mac con 8GB se siente trabada procesando muchísimos clips a la
vez, es la primera señal para reabrir esto.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7b: Quitar modo económico/rápido — `pantalla_config.py`

**Files:**
- Modify: `src/clasificador_video/ui/pantalla_config.py`
- Test: `tests/ui/test_pantalla_config.py`

- [ ] **Step 1: Borrar los tests que prueban los checkboxes de económico/rápido**

En `tests/ui/test_pantalla_config.py`, borrar:
`test_el_modo_economico_nace_apagado_por_default`,
`test_cargar_refleja_el_modo_economico_guardado`, el test de marcar/
desmarcar económico (líneas ~58-86, revisar nombres exactos con
`grep -n "^def test_" tests/ui/test_pantalla_config.py`),
`test_el_modo_rapido_nace_apagado_por_default`,
`test_cargar_refleja_el_modo_rapido_guardado`,
`test_marcar_el_check_rapido_emite_true`,
`test_desmarcar_el_check_rapido_emite_false`,
`test_cargar_no_reemite_la_señal_de_rapido_al_solo_reflejar_lo_guardado`,
`test_economico_y_rapido_son_independientes`.

Actualizar el helper `_pantalla` (línea ~7-12) quitando los parámetros
`modo_economico`/`modo_rapido` y el argumento correspondiente al llamar
`p.cargar(...)`.

- [ ] **Step 2: Correr lo que queda de `test_pantalla_config.py`, confirmar que falla por el `cargar()` viejo**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_config.py -v`
Expected: FAIL en la colección o en los tests restantes, porque
`PantallaConfig.cargar` todavía pide `modo_economico`/`modo_rapido` como
primeros dos parámetros posicionales y el helper `_pantalla` ya no los
pasa (o los pasa distinto). Confirmar el mensaje de error antes de seguir.

- [ ] **Step 3: Quitar los checkboxes y señales de `PantallaConfig`**

En `src/clasificador_video/ui/pantalla_config.py`:

Borrar del `class PantallaConfig`:
- Las señales `modo_economico_cambiado` y `modo_rapido_cambiado` (líneas 43-44).
- Todo el bloque de "Modo económico" (líneas 78-103: `titulo_economico`,
  `self.economico_check`, `economico_label`, y las líneas `raiz.addWidget(...)`
  correspondientes).
- Todo el bloque de "Modo rápido" (líneas 105-128: `titulo_rapido`,
  `self.rapido_check`, `rapido_label`).

Actualizar el docstring de la clase (línea 40-41): de
`"""El modo económico, el modo rápido y las miniaturas guardadas en disco."""`
a `"""Las carpetas de trabajo y las miniaturas guardadas en disco."""`
(ajustar según lo que realmente quede en la pantalla — revisar el resto
del archivo antes de escribir el docstring final).

Actualizar el docstring del módulo (línea 1-13): quitar la mención a
"el modo económico, el modo rápido".

Cambiar la firma de `cargar`:

```python
    def cargar(self, importacion_rapida_pregunta_antes: bool = False) -> None:
        """Enseña qué hay guardado, reflejando las preferencias en sus
        casillas. Se bloquean las señales para no reemitir nada al solo
        reflejar lo guardado."""
        self.importacion_rapida_pregunta_check.blockSignals(True)
        self.importacion_rapida_pregunta_check.setChecked(
            importacion_rapida_pregunta_antes)
        self.importacion_rapida_pregunta_check.blockSignals(False)
```

- [ ] **Step 4: Correr `test_pantalla_config.py`, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/pantalla_config.py tests/ui/test_pantalla_config.py
git commit -m "$(cat <<'EOF'
pantalla_config.py: quitar los checkboxes de modo económico y rápido

Parte de quitar el freno de paralelismo por decisión de Bruno -- ver el
commit de preferencias.py. cargar() pierde sus dos primeros parámetros.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7c: Quitar modo económico/rápido — `thumbnails.py`

**Files:**
- Modify: `src/clasificador_video/thumbnails.py`
- Test: `tests/test_thumbnails.py`

- [ ] **Step 1: Borrar los tests de modo económico en `test_thumbnails.py`**

Buscar y borrar (`grep -n "def test_economico\|def test_cache_dir_for_distingue_economico" tests/test_thumbnails.py`
para confirmar los nombres exactos):
`test_economico_agrega_el_filtro_de_escala_a_la_tira`,
`test_economico_agrega_el_filtro_de_escala_al_frame_suelto`,
`test_cache_dir_for_distingue_economico_del_normal`.

Quitar `ANCHO_MINIATURA_ECONOMICO` del import al inicio del archivo si
ya no se usa en ningún test restante (confirmar con
`grep -n "ANCHO_MINIATURA_ECONOMICO" tests/test_thumbnails.py` después de
borrar los tres tests de arriba).

- [ ] **Step 2: Correr `test_thumbnails.py`, confirmar que falla por las firmas viejas**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py -v`
Expected: puede pasar todavía si nada más se tocó (las funciones siguen
aceptando `economico` con default `False`) — este paso es solo para
tener una foto de "antes" limpia.

- [ ] **Step 3: Quitar el parámetro `economico` de las funciones de `thumbnails.py`**

En `src/clasificador_video/thumbnails.py`:

Borrar la función `_filtro_de_escala` completa (líneas 178-179) y la
constante `ANCHO_MINIATURA_ECONOMICO` (líneas 170-175).

`cache_dir_for` (líneas 142-167) pierde el parámetro `economico` y las
líneas:

```python
    if economico:
        key_source += "|economico"
```

`build_thumbnail_command` (líneas 182-208) pierde el parámetro
`economico` y `*_filtro_de_escala(economico),` de la lista.

`extract_thumbnail` (líneas 211-224) pierde el parámetro `economico` y
deja de pasarlo a `build_thumbnail_command(...)`.

`build_strip_ipc_args` (líneas 260-307, ya tocada en Task 1) pierde el
parámetro `economico` y `*_filtro_de_escala(economico),` de la lista.

`extract_thumbnail_strip` (líneas 385-434, ya tocada en Task 1) pierde el
parámetro `economico` y deja de pasarlo a `build_strip_ipc_args(...)`.

- [ ] **Step 4: Correr `test_thumbnails.py`, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_thumbnails.py -v`
Expected: PASS. Si algún test todavía pasa `economico=True/False`
explícito a una de estas funciones, quitar ese argumento de la llamada
(son parte de los tests que quedaron después del Step 1, no de los
borrados).

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/thumbnails.py tests/test_thumbnails.py
git commit -m "$(cat <<'EOF'
thumbnails.py: quitar el parámetro economico, código muerto sin los modos

Sin modo económico ni modo rápido (ver los dos commits anteriores), nada
vuelve a pasar economico=True -- _filtro_de_escala, ANCHO_MINIATURA_ECONOMICO
y el parámetro en cache_dir_for/build_thumbnail_command/extract_thumbnail/
build_strip_ipc_args/extract_thumbnail_strip quedan sin uso.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7d: Quitar modo económico/rápido — `main_window.py`

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Borrar los tests de modo económico/rápido en `test_main_window.py`**

Borrar las seis funciones identificadas (confirmar rango exacto con
`grep -n "^def test_modo_economico\|^def test_modo_rapido" tests/ui/test_main_window.py`
antes de borrar, por si el archivo cambió de línea desde este plan):
`test_modo_economico_pide_la_mitad_de_cuadros_en_la_tira`,
`test_modo_economico_baja_los_hilos_y_el_limite_de_tiras`,
`test_modo_economico_baja_cuantos_ffprobe_corren_a_la_vez_al_importar`,
`test_modo_rapido_no_frena_aunque_economico_este_prendido`,
`test_modo_rapido_solo_quita_el_freno_al_prenderse`,
`test_modo_rapido_solo_saca_miniaturas_chicas_sin_frenar`.

**No tocar** `test_reconectar_un_proxy_a_medio_extraer_no_congela_el_contador`
ni `test_una_extraccion_fallida_se_reintenta_sola` — mencionan modo
económico/rápido solo en el docstring como contexto histórico del bug
real que reproducen, no prueban las funciones que se están borrando.

- [ ] **Step 2: Correr `test_main_window.py`, confirmar que sigue pasando (foto de "antes")**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -q`
Expected: PASS — todavía no se tocó el código fuente.

- [ ] **Step 3: Quitar las funciones y su plumbing de `main_window.py`**

En `src/clasificador_video/ui/main_window.py`:

Borrar las funciones libres `_miniaturas_chicas` (líneas 292-296) y
`_hilos_limitados` (líneas 299-303).

Borrar las constantes `HILOS_DE_MINIATURAS_ECONOMICO`,
`LIMITE_DE_TIRAS_VIVAS_ECONOMICO`, `SONDEOS_EN_PARALELO_ECONOMICO` (quedan
`HILOS_DE_MINIATURAS_NORMAL`, `LIMITE_DE_TIRAS_VIVAS_NORMAL`,
`SONDEOS_EN_PARALELO` — el sufijo `_NORMAL` en los que quedan es ahora
cosmético, no se renombran en este task para no ampliar el diff).

El bloque del thread pool de miniaturas (alrededor de línea 693-697):

```python
        self._thread_pool.setMaxThreadCount(
            HILOS_DE_MINIATURAS_ECONOMICO
            if _hilos_limitados()
            else HILOS_DE_MINIATURAS_NORMAL
        )
```

pasa a:

```python
        self._thread_pool.setMaxThreadCount(HILOS_DE_MINIATURAS_NORMAL)
```

Y el comentario de arriba de ese bloque (líneas 687-692, el que dice "las
miniaturas se extraen en software... El 3 es para una Mac con recursos de
sobra; en modo economico baja a 1") se reemplaza por:

```python
        # 3 hilos de miniaturas en paralelo: confirmado el 2026-09-25 que
        # es el techo real de VideoToolbox en esta maquina -- subirlo a 4+
        # satura el decodificador de hardware y el tiempo TOTAL empeora en
        # vez de mejorar (medido: 4.40s -> 6.31s -> 25.97s subiendo de 3 a
        # 4 a 5 hilos con 12 clips reales). No es un compromiso de
        # velocidad que dependa de la Mac -- es el limite del chip.
```

El bloque del límite de tiras vivas (alrededor de línea 904-905):

```python
        self.clip_sheet.set_limite_de_tiras_vivas(
            LIMITE_DE_TIRAS_VIVAS_ECONOMICO if _hilos_limitados()
            else LIMITE_DE_TIRAS_VIVAS_NORMAL
        )
```

pasa a:

```python
        self.clip_sheet.set_limite_de_tiras_vivas(LIMITE_DE_TIRAS_VIVAS_NORMAL)
```

El bloque de sondeos en paralelo al importar (alrededor de línea
3128-3129):

```python
        paralelo = (SONDEOS_EN_PARALELO_ECONOMICO if _hilos_limitados()
                   else SONDEOS_EN_PARALELO)
```

pasa a:

```python
        paralelo = SONDEOS_EN_PARALELO
```

En `_schedule_thumbnails` (alrededor de línea 4437):

```python
        economico = _miniaturas_chicas()
```

se borra por completo (la variable `economico` deja de existir en ese
método). Más abajo, en la construcción de `_ThumbnailJob` (línea
4563-4566):

```python
            self._thread_pool.start(
                _ThumbnailJob(generation, index, fuente, cache_dir, duration_seconds,
                              self._señales_de_trabajos, economico)
            )
```

pasa a:

```python
            self._thread_pool.start(
                _ThumbnailJob(generation, index, fuente, cache_dir, duration_seconds,
                              self._señales_de_trabajos)
            )
```

Y donde se llama a `cache_dir_for` en el mismo método (línea 4479):

```python
            cache_dir = cache_dir_for(fuente, cache_root, economico)
```

pasa a:

```python
            cache_dir = cache_dir_for(fuente, cache_root)
```

En la clase `_ThumbnailJob` (líneas 385-434): borrar la constante
`STRIP_COUNT_ECONOMICO` (línea 392), el parámetro `economico: bool =
False` del `__init__` y `self.economico = economico`, y en `run()`
cambiar:

```python
                count = self.STRIP_COUNT_ECONOMICO if self.economico else self.STRIP_COUNT
                frames = extract_thumbnail_strip(
                    self.video, self.duration_seconds, count, self.outdir,
                    economico=self.economico,
                )
            else:
                # sin duracion conocida (ej. sesion restaurada sin volver
                # a correr ffprobe): un solo frame, como antes.
                frames = [extract_thumbnail(self.video, 0.5, self.outdir,
                                            economico=self.economico)]
```

por:

```python
                frames = extract_thumbnail_strip(
                    self.video, self.duration_seconds, self.STRIP_COUNT, self.outdir,
                )
            else:
                # sin duracion conocida (ej. sesion restaurada sin volver
                # a correr ffprobe): un solo frame, como antes.
                frames = [extract_thumbnail(self.video, 0.5, self.outdir)]
```

Borrar los métodos `_aplicar_freno_de_paralelismo`, `_cambiar_modo_economico`,
`_cambiar_modo_rapido` (líneas ~5298-5329) por completo.

En `_abrir_configuracion` (líneas ~5247-5265), borrar las dos conexiones:

```python
            self._pantalla_config.modo_economico_cambiado.connect(
                self._cambiar_modo_economico
            )
            self._pantalla_config.modo_rapido_cambiado.connect(
                self._cambiar_modo_rapido
            )
```

y cambiar:

```python
        self._pantalla_config.cargar(
            preferencias.modo_economico(), preferencias.modo_rapido(),
            preferencias.importacion_rapida_pregunta_antes(),
        )
```

por:

```python
        self._pantalla_config.cargar(
            preferencias.importacion_rapida_pregunta_antes(),
        )
```

- [ ] **Step 4: Correr `test_main_window.py`, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -q`
Expected: PASS. Si algo falla por una referencia suelta a
`HILOS_DE_MINIATURAS_ECONOMICO`/`_miniaturas_chicas`/etc. que no estaba en
la lista de arriba, buscarla con
`grep -n "ECONOMICO\|_miniaturas_chicas\|_hilos_limitados\|_aplicar_freno_de_paralelismo\|_cambiar_modo_economico\|_cambiar_modo_rapido" src/clasificador_video/ui/main_window.py`
y limpiarla del mismo modo.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "$(cat <<'EOF'
main_window.py: quitar el freno de paralelismo de modo económico/rápido

_miniaturas_chicas, _hilos_limitados, _aplicar_freno_de_paralelismo,
_cambiar_modo_economico, _cambiar_modo_rapido y las constantes _ECONOMICO
desaparecen -- la app siempre corre con lo que antes era el ajuste
"normal" (3 hilos de miniaturas, 8 sondeos en paralelo al importar,
límite de tiras vivas sin achicar). Parte de la decisión de Bruno del
2026-09-25, riesgo aceptado sin probar en una Mac con poca RAM.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7e: Quitar modo económico/rápido — `app.py`

**Files:**
- Modify: `src/clasificador_video/app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Borrar el test correspondiente en `test_app.py`**

Borrar `test_configuracion_guarda_modo_economico_y_rapido_como_preferencia`
(líneas ~1267-1285).

- [ ] **Step 2: Correr `test_app.py`, confirmar que pasa todavía (foto de "antes")**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -q`
Expected: PASS — todavía no se tocó `app.py`.

- [ ] **Step 3: Quitar el wiring de `app.py`**

En `src/clasificador_video/app.py`, dentro de `_abrir_configuracion`
(líneas 498-529), borrar:

```python
            self._pantalla_config.modo_economico_cambiado.connect(
                preferencias.guardar_modo_economico
            )
            self._pantalla_config.modo_rapido_cambiado.connect(
                preferencias.guardar_modo_rapido
            )
```

y cambiar:

```python
        self._pantalla_config.cargar(
            preferencias.modo_economico(), preferencias.modo_rapido(),
            preferencias.importacion_rapida_pregunta_antes(),
        )
```

por:

```python
        self._pantalla_config.cargar(
            preferencias.importacion_rapida_pregunta_antes(),
        )
```

- [ ] **Step 4: Correr `test_app.py`, verificar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -q`
Expected: PASS.

- [ ] **Step 5: Grep final de toda la app en busca de restos**

Run: `grep -rln "modo_economico\|modo_rapido\|_miniaturas_chicas\|_hilos_limitados\|ECONOMICO" src/`
Expected: sin resultados (o, si algo aparece, revisarlo — puede ser un
nombre parecido pero no relacionado, como `HILOS_DE_MINIATURAS_NORMAL`
que sí se conserva a propósito).

- [ ] **Step 6: Correr la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: todos pasan, 0 failures.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "$(cat <<'EOF'
app.py: quitar el wiring de modo económico/rápido en la pantalla de inicio

Último rastro del interruptor -- la pantalla de Configuración que se abre
ANTES de tener un proyecto (desde Inicio) también leía y guardaba estas
dos preferencias. Cierra la limpieza de los commits anteriores
(preferencias.py, pantalla_config.py, thumbnails.py, main_window.py).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Verificación final

- [ ] **Correr la suite completa una vez más, de punta a punta**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: todos pasan.

- [ ] **Medir en vivo contra un clip real antes de dar por bueno el trabajo**

No basta con que los tests pasen (regla del repo, ver CLAUDE.md). Repetir
al menos:
- Una extracción de tira sobre un clip de `sample-media/clips/` y
  confirmar que tarda menos que antes de este plan (referencia:
  ~0.83s por clip aislado en `sample-media/clips/20260804_PIB0589.MP4`).
- Generar un proxy sobre el mismo clip y confirmar con `framemd5` que el
  resultado sigue siendo idéntico al de antes de este plan.
- Abrir la app de verdad (no offscreen) contra `sample-media/` y
  confirmar que el modo económico/rápido ya no aparece en Configuración,
  y que la app no se ve rota sin él.

- [ ] **Actualizar la memoria de la sesión**

El archivo
`/Users/brunogutierrez/.claude/projects/-Users-brunogutierrez-Documents-CLAUDE-CODE-ORGANIZADOR-VIDEO/memory/project_investigacion_rendimiento_2026-09-25.md`
queda desactualizado una vez implementado esto (describe una lista de
PENDIENTES). Marcarlo como implementado o borrarlo, según corresponda en
ese momento.
