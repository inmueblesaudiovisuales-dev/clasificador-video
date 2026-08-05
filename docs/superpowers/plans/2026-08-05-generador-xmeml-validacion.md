# Generador xmeml + validación en Premiere — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir y probar, de forma aislada de la interfaz gráfica, el generador de xmeml (bins anidados por cuarto/subcuarto, in/out por frame, labels de color Pick/Reject) descrito en `docs/superpowers/specs/2026-08-05-clasificador-video-design.md` §3–§7, y validarlo con un import real en Premiere Pro 2026 antes de construir la interfaz completa (spec §9).

**Architecture:** Módulo Python puro (`clasificador_video`), sin dependencias de UI, con un modelo de datos (`ClipSpec`), un lector de metadatos vía `ffprobe` (`probe.py`), y un generador de XML por concatenación de strings (`xmeml.py`) que reproduce exactamente la plantilla validada de `iav-metadata-app/docs/premiere/plantilla-xmeml-validada.md`, agregando in/out reales. Cierra con un script de línea de comandos que arma un xmeml a partir de 2-3 clips reales para importar en Premiere a mano.

**Tech Stack:** Python 3.11+, `pytest` para pruebas, `ffprobe` (parte de ffmpeg) para sondear los archivos, sin frameworks de UI en esta fase.

---

## Notas para quien ejecute este plan

- La carpeta del proyecto es `/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO` — tiene espacios en el nombre, hay que citarla entre comillas en cualquier comando de shell.
- Ya existe un repositorio git inicializado ahí, con un commit del handoff original y otro del spec. Este plan sigue commiteando sobre esa misma rama (`master`).
- El paso final (importar el XML generado en Premiere y confirmar visualmente que los cortes caen donde deben) es un paso **manual, no automatizable** — lo hace el usuario, no el agente. El Task 13 deja instrucciones exactas para ese paso.

---

### Task 0: Scaffold del proyecto Python

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `src/clasificador_video/__init__.py`
- Create: `.gitignore` (modificar el existente)

- [ ] **Step 1: Crear la estructura de carpetas**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
mkdir -p src/clasificador_video tests scripts
touch src/clasificador_video/__init__.py
```

- [ ] **Step 2: Crear el entorno virtual e instalar pytest**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
```

- [ ] **Step 3: Crear `requirements.txt`**

```
pytest>=7.4
```

- [ ] **Step 4: Crear `pyproject.toml`**

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 5: Agregar `.venv/` al `.gitignore`**

Contenido completo de `.gitignore` (agrega una línea a lo que ya existe):

```
.superpowers/
.venv/
__pycache__/
*.pyc
```

- [ ] **Step 6: Verificar que pytest corre sin pruebas todavía**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest -v`
Expected: `no tests ran` (sin errores de configuración)

- [ ] **Step 7: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add pyproject.toml requirements.txt .gitignore src/clasificador_video/__init__.py
git commit -m "chore: scaffold del proyecto Python (pytest, src layout)"
```

---

### Task 1: `rate_for_fps` — cálculo de timebase/NTSC

**Files:**
- Create: `src/clasificador_video/rate.py`
- Test: `tests/test_rate.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_rate.py`:

```python
from clasificador_video.rate import rate_for_fps


def test_fps_2997_es_ntsc_timebase_30():
    timebase, ntsc = rate_for_fps(29.97)
    assert timebase == 30
    assert ntsc is True


def test_fps_30_exacto_no_es_ntsc():
    timebase, ntsc = rate_for_fps(30.0)
    assert timebase == 30
    assert ntsc is False


def test_fps_23976_es_ntsc_timebase_24():
    timebase, ntsc = rate_for_fps(23.976)
    assert timebase == 24
    assert ntsc is True


def test_fps_25_exacto_no_es_ntsc():
    timebase, ntsc = rate_for_fps(25.0)
    assert timebase == 25
    assert ntsc is False


def test_fps_5994_es_ntsc_timebase_60():
    timebase, ntsc = rate_for_fps(59.94)
    assert timebase == 60
    assert ntsc is True
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_rate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clasificador_video.rate'`

- [ ] **Step 3: Implementación mínima**

`src/clasificador_video/rate.py`:

```python
def rate_for_fps(fps: float) -> tuple[int, bool]:
    """Devuelve (timebase, ntsc) para declarar <rate> en xmeml.

    timebase es el fps redondeado al entero mas cercano. ntsc es True
    cuando el fps real no es un entero exacto (29.97, 23.976, 59.94...),
    False cuando si lo es (24, 25, 30, 50, 60).
    """
    timebase = round(fps)
    ntsc = abs(fps - timebase) > 0.001
    return timebase, ntsc
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_rate.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/rate.py tests/test_rate.py
git commit -m "feat: calculo de timebase/ntsc a partir del fps real"
```

---

### Task 2: Modelo de datos `ClipSpec`

**Files:**
- Create: `src/clasificador_video/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_models.py`:

```python
from pathlib import Path

from clasificador_video.models import ClipSpec


def _clip(**overrides) -> ClipSpec:
    base = dict(
        file_path=Path("/shooting/C0012.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=True,
        duration_frames=900,
    )
    base.update(overrides)
    return ClipSpec(**base)


def test_sin_in_out_usa_el_clip_completo():
    clip = _clip()
    assert clip.effective_in() == 0
    assert clip.effective_out() == 900


def test_con_in_out_usa_los_valores_marcados():
    clip = _clip(in_frame=120, out_frame=600)
    assert clip.effective_in() == 120
    assert clip.effective_out() == 600


def test_flag_por_defecto_es_none():
    clip = _clip()
    assert clip.flag == "none"
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clasificador_video.models'`

- [ ] **Step 3: Implementación mínima**

`src/clasificador_video/models.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClipSpec:
    file_path: Path
    category_path: list[str]
    width: int
    height: int
    fps: float
    has_audio: bool
    duration_frames: int
    in_frame: int | None = None
    out_frame: int | None = None
    flag: str = "none"  # "none" | "pick" | "reject"

    def effective_in(self) -> int:
        return self.in_frame if self.in_frame is not None else 0

    def effective_out(self) -> int:
        return self.out_frame if self.out_frame is not None else self.duration_frames
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_models.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/models.py tests/test_models.py
git commit -m "feat: modelo ClipSpec con in/out efectivo"
```

---

### Task 3: `probe_clip` — sondeo de metadatos con ffprobe

**Files:**
- Create: `src/clasificador_video/probe.py`
- Test: `tests/test_probe.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_probe.py`:

```python
import json
from pathlib import Path

from clasificador_video.probe import probe_clip

FFPROBE_JSON_CON_AUDIO = json.dumps({
    "streams": [
        {"codec_type": "video", "width": 3840, "height": 2160, "r_frame_rate": "30000/1001"},
        {"codec_type": "audio", "channels": 2},
    ],
    "format": {"duration": "30.03"},
})

FFPROBE_JSON_SIN_AUDIO = json.dumps({
    "streams": [
        {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "24000/1001"},
    ],
    "format": {"duration": "10.0"},
})


def test_probe_detecta_audio_y_fps_ntsc():
    result = probe_clip(Path("/shooting/C0001.MP4"), runner=lambda path: FFPROBE_JSON_CON_AUDIO)
    assert result["width"] == 3840
    assert result["height"] == 2160
    assert result["has_audio"] is True
    assert abs(result["fps"] - 29.97) < 0.01
    assert result["duration_frames"] == round(30.03 * (30000 / 1001))


def test_probe_sin_audio():
    result = probe_clip(Path("/shooting/DJI_0001.MP4"), runner=lambda path: FFPROBE_JSON_SIN_AUDIO)
    assert result["has_audio"] is False
    assert abs(result["fps"] - 23.976) < 0.01
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_probe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clasificador_video.probe'`

- [ ] **Step 3: Implementación mínima**

`src/clasificador_video/probe.py`:

```python
import json
import subprocess
from pathlib import Path
from typing import Callable

FFPROBE_ARGS = ["-v", "quiet", "-print_format", "json", "-show_format", "-show_streams"]


def _run_ffprobe(path: Path) -> str:
    result = subprocess.run(
        ["ffprobe", *FFPROBE_ARGS, str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def probe_clip(path: Path, runner: Callable[[Path], str] = _run_ffprobe) -> dict:
    """Sondea un archivo de video y devuelve width/height/fps/has_audio/duration_frames.

    `runner` es inyectable para pruebas: recibe la ruta y debe devolver el
    stdout de ffprobe (JSON) como string.
    """
    data = json.loads(runner(path))
    video_stream = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio_streams = [s for s in data["streams"] if s["codec_type"] == "audio"]

    num, den = video_stream["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    duration_seconds = float(data["format"]["duration"])

    has_audio = any(int(s.get("channels", 0)) > 0 for s in audio_streams)

    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "fps": fps,
        "has_audio": has_audio,
        "duration_frames": round(duration_seconds * fps),
    }
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_probe.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/probe.py tests/test_probe.py
git commit -m "feat: sondeo de metadatos de clip via ffprobe"
```

---

### Task 4: `xmeml.py` — helpers de rate XML y pathurl

**Files:**
- Create: `src/clasificador_video/xmeml.py`
- Test: `tests/test_xmeml_helpers.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_xmeml_helpers.py`:

```python
from pathlib import Path

from clasificador_video.xmeml import _pathurl, _rate_xml


def test_rate_xml_ntsc():
    xml = _rate_xml(29.97)
    assert "<timebase>30</timebase>" in xml
    assert "<ntsc>TRUE</ntsc>" in xml


def test_rate_xml_no_ntsc():
    xml = _rate_xml(25.0)
    assert "<timebase>25</timebase>" in xml
    assert "<ntsc>FALSE</ntsc>" in xml


def test_pathurl_codifica_espacios():
    url = _pathurl(Path("/Volumes/SHOOTING/Casa con jardin/C0012.MP4"))
    assert url == "file://localhost/Volumes/SHOOTING/Casa%20con%20jardin/C0012.MP4"
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clasificador_video.xmeml'`

- [ ] **Step 3: Implementación mínima**

`src/clasificador_video/xmeml.py`:

```python
from pathlib import Path
from urllib.parse import quote

from clasificador_video.rate import rate_for_fps


def _rate_xml(fps: float) -> str:
    timebase, ntsc = rate_for_fps(fps)
    return f"<rate><timebase>{timebase}</timebase><ntsc>{'TRUE' if ntsc else 'FALSE'}</ntsc></rate>"


def _pathurl(path: Path) -> str:
    encoded = quote(str(path))
    return f"file://localhost{encoded}"
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_helpers.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/xmeml.py tests/test_xmeml_helpers.py
git commit -m "feat: helpers de rate XML y pathurl codificado"
```

---

### Task 5: `_file_xml` — bloque `<file>` sin y con audio

**Files:**
- Modify: `src/clasificador_video/xmeml.py`
- Test: `tests/test_xmeml_file.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_xmeml_file.py`:

```python
from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import _file_xml


def _clip(has_audio: bool) -> ClipSpec:
    return ClipSpec(
        file_path=Path("/shooting/C0012.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=has_audio,
        duration_frames=900,
    )


def test_file_sin_audio_no_declara_bloque_audio():
    xml_str = _file_xml(_clip(has_audio=False), file_id="file-1")
    root = ET.fromstring(f"<root>{xml_str}</root>")
    file_el = root.find("file")
    assert file_el.get("id") == "file-1"
    assert file_el.find("name").text == "C0012.MP4"
    assert file_el.find("media/video") is not None
    assert file_el.find("media/audio") is None


def test_file_con_audio_declara_dos_bloques_audio():
    xml_str = _file_xml(_clip(has_audio=True), file_id="file-2")
    root = ET.fromstring(f"<root>{xml_str}</root>")
    file_el = root.find("file")
    audio_blocks = file_el.findall("media/audio")
    assert len(audio_blocks) == 2
    assert audio_blocks[0].find("audiochannel/channellabel").text == "left"
    assert audio_blocks[1].find("audiochannel/channellabel").text == "right"


def test_file_pathurl_y_duracion():
    xml_str = _file_xml(_clip(has_audio=False), file_id="file-1")
    root = ET.fromstring(f"<root>{xml_str}</root>")
    file_el = root.find("file")
    assert file_el.find("pathurl").text == "file://localhost/shooting/C0012.MP4"
    assert file_el.find("duration").text == "900"
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_file.py -v`
Expected: FAIL — `ImportError: cannot import name '_file_xml'`

- [ ] **Step 3: Implementación**

Agregar a `src/clasificador_video/xmeml.py`:

```python
from clasificador_video.models import ClipSpec


def _audio_block_xml(source_channel: int, channel_label: str) -> str:
    return (
        "<audio>"
        "<samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics>"
        "<channelcount>1</channelcount><layout>stereo</layout>"
        f"<audiochannel><sourcechannel>{source_channel}</sourcechannel>"
        f"<channellabel>{channel_label}</channellabel></audiochannel>"
        "</audio>"
    )


def _file_xml(clip: ClipSpec, file_id: str) -> str:
    audio_xml = ""
    if clip.has_audio:
        audio_xml = _audio_block_xml(1, "left") + _audio_block_xml(2, "right")

    return (
        f'<file id="{file_id}">'
        f"<name>{clip.file_path.name}</name>"
        f"<pathurl>{_pathurl(clip.file_path)}</pathurl>"
        f"{_rate_xml(clip.fps)}"
        f"<duration>{clip.duration_frames}</duration>"
        "<media><video><samplecharacteristics>"
        f"{_rate_xml(clip.fps)}"
        f"<width>{clip.width}</width><height>{clip.height}</height>"
        "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
        "<fielddominance>none</fielddominance>"
        f"</samplecharacteristics></video>{audio_xml}</media>"
        "</file>"
    )
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_file.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/xmeml.py tests/test_xmeml_file.py
git commit -m "feat: bloque file XML, audio solo si el clip tiene pista real"
```

---

### Task 6: `_clipitem_xml` — in/out por frame

**Files:**
- Modify: `src/clasificador_video/xmeml.py`
- Test: `tests/test_xmeml_clipitem.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_xmeml_clipitem.py`:

```python
from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import _clipitem_xml, _file_xml


def _clip(in_frame=None, out_frame=None) -> ClipSpec:
    return ClipSpec(
        file_path=Path("/shooting/C0012.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=False,
        duration_frames=900,
        in_frame=in_frame,
        out_frame=out_frame,
    )


def test_clipitem_sin_in_out_usa_clip_completo():
    clip = _clip()
    file_xml = _file_xml(clip, "file-1")
    xml_str = _clipitem_xml(clip, "clipitem-1", "masterclip-1", file_xml)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clipitem = root.find("clipitem")
    assert clipitem.get("id") == "clipitem-1"
    assert clipitem.find("masterclipid").text == "masterclip-1"
    assert clipitem.find("in").text == "0"
    assert clipitem.find("out").text == "900"
    assert clipitem.find("file") is not None


def test_clipitem_con_in_out_marcados():
    clip = _clip(in_frame=120, out_frame=600)
    file_xml = _file_xml(clip, "file-1")
    xml_str = _clipitem_xml(clip, "clipitem-1", "masterclip-1", file_xml)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clipitem = root.find("clipitem")
    assert clipitem.find("in").text == "120"
    assert clipitem.find("out").text == "600"
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_clipitem.py -v`
Expected: FAIL — `ImportError: cannot import name '_clipitem_xml'`

- [ ] **Step 3: Implementación**

Agregar a `src/clasificador_video/xmeml.py`:

```python
def _clipitem_xml(clip: ClipSpec, clipitem_id: str, masterclip_id: str, file_xml: str) -> str:
    return (
        f'<clipitem id="{clipitem_id}">'
        f"<masterclipid>{masterclip_id}</masterclipid>"
        f"<name>{clip.file_path.stem}</name>"
        f"{_rate_xml(clip.fps)}"
        f"<in>{clip.effective_in()}</in>"
        f"<out>{clip.effective_out()}</out>"
        "<alphatype>none</alphatype>"
        "<pixelaspectratio>square</pixelaspectratio>"
        "<anamorphic>FALSE</anamorphic>"
        f"{file_xml}"
        "</clipitem>"
    )
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_clipitem.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/xmeml.py tests/test_xmeml_clipitem.py
git commit -m "feat: clipitem con in/out por numero de frame"
```

---

### Task 7: `_clip_xml` — masterclip con labels Pick/Reject

**Files:**
- Modify: `src/clasificador_video/xmeml.py`
- Test: `tests/test_xmeml_clip.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_xmeml_clip.py`:

```python
from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import _clip_xml


def _clip(flag="none") -> ClipSpec:
    return ClipSpec(
        file_path=Path("/shooting/C0012.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=False,
        duration_frames=900,
        flag=flag,
    )


def test_clip_sin_flag_no_tiene_labels():
    xml_str = _clip_xml(_clip(flag="none"), index=1)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clip_el = root.find("clip")
    assert clip_el.get("id") == "masterclip-1"
    assert clip_el.get("explodedTracks") == "true"
    assert clip_el.find("ismasterclip").text == "TRUE"
    assert clip_el.find("labels") is None


def test_clip_pick_tiene_label_forest():
    xml_str = _clip_xml(_clip(flag="pick"), index=2)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clip_el = root.find("clip")
    assert clip_el.find("labels/label2").text == "Forest"


def test_clip_reject_tiene_label_rose():
    xml_str = _clip_xml(_clip(flag="reject"), index=3)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    clip_el = root.find("clip")
    assert clip_el.find("labels/label2").text == "Rose"
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_clip.py -v`
Expected: FAIL — `ImportError: cannot import name '_clip_xml'`

- [ ] **Step 3: Implementación**

Agregar a `src/clasificador_video/xmeml.py`:

```python
import uuid

LABEL_BY_FLAG = {"pick": "Forest", "reject": "Rose"}


def _clip_xml(clip: ClipSpec, index: int) -> str:
    masterclip_id = f"masterclip-{index}"
    clipitem_id = f"clipitem-{index}"
    file_id = f"file-{index}"

    file_xml = _file_xml(clip, file_id)
    clipitem_xml = _clipitem_xml(clip, clipitem_id, masterclip_id, file_xml)

    label_xml = ""
    if clip.flag in LABEL_BY_FLAG:
        label_xml = f"<labels><label2>{LABEL_BY_FLAG[clip.flag]}</label2></labels>"

    return (
        f'<clip id="{masterclip_id}" explodedTracks="true">'
        f"<uuid>{uuid.uuid4()}</uuid>"
        f"<masterclipid>{masterclip_id}</masterclipid>"
        "<ismasterclip>TRUE</ismasterclip>"
        f"<duration>{clip.duration_frames}</duration>"
        f"{_rate_xml(clip.fps)}"
        f"<name>{clip.file_path.stem}</name>"
        f"<media><video><track>{clipitem_xml}</track></video></media>"
        f"{label_xml}"
        "</clip>"
    )
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_clip.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/xmeml.py tests/test_xmeml_clip.py
git commit -m "feat: masterclip con label de color para pick/reject"
```

---

### Task 8: Agrupar clips en árbol de bins anidados por cuarto/subcuarto

**Files:**
- Modify: `src/clasificador_video/xmeml.py`
- Test: `tests/test_xmeml_grouping.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_xmeml_grouping.py`:

```python
from pathlib import Path

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import _group_by_category


def _clip(category_path, name="C0001.MP4") -> ClipSpec:
    return ClipSpec(
        file_path=Path(f"/shooting/{name}"),
        category_path=category_path,
        width=1920,
        height=1080,
        fps=25.0,
        has_audio=False,
        duration_frames=100,
    )


def test_agrupa_cuartos_sin_subcuarto():
    clips = [_clip(["Cocina"], "C0001.MP4"), _clip(["Sala"], "C0002.MP4")]
    tree = _group_by_category(clips)
    assert list(tree.keys()) == ["Cocina", "Sala"]
    assert tree["Cocina"]["__clips__"][0].file_path.name == "C0001.MP4"


def test_agrupa_subcuartos_anidados():
    clips = [
        _clip(["Recamara 2", "Bano"], "C0003.MP4"),
        _clip(["Recamara 2"], "C0004.MP4"),
    ]
    tree = _group_by_category(clips)
    assert "Recamara 2" in tree
    assert "Bano" in tree["Recamara 2"]
    assert tree["Recamara 2"]["Bano"]["__clips__"][0].file_path.name == "C0003.MP4"
    assert tree["Recamara 2"]["__clips__"][0].file_path.name == "C0004.MP4"


def test_clip_sin_categoria_cae_en_sin_clasificar():
    clips = [_clip(["Sin clasificar"], "C0005.MP4")]
    tree = _group_by_category(clips)
    assert tree["Sin clasificar"]["__clips__"][0].file_path.name == "C0005.MP4"
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_grouping.py -v`
Expected: FAIL — `ImportError: cannot import name '_group_by_category'`

- [ ] **Step 3: Implementación**

Agregar a `src/clasificador_video/xmeml.py`:

```python
from collections import OrderedDict


def _group_by_category(clips: list[ClipSpec]) -> OrderedDict:
    tree: OrderedDict = OrderedDict()
    for clip in clips:
        node = tree
        for part in clip.category_path:
            node = node.setdefault(part, OrderedDict())
        node.setdefault("__clips__", []).append(clip)
    return tree
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_grouping.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/xmeml.py tests/test_xmeml_grouping.py
git commit -m "feat: agrupar clips en arbol de cuarto/subcuarto"
```

---

### Task 9: `_bin_xml` recursivo — bins anidados en XML

**Files:**
- Modify: `src/clasificador_video/xmeml.py`
- Test: `tests/test_xmeml_bin.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_xmeml_bin.py`:

```python
import xml.etree.ElementTree as ET

from clasificador_video.xmeml import _bin_xml, _group_by_category
from clasificador_video.models import ClipSpec
from pathlib import Path


def _clip(category_path, name) -> ClipSpec:
    return ClipSpec(
        file_path=Path(f"/shooting/{name}"),
        category_path=category_path,
        width=1920,
        height=1080,
        fps=25.0,
        has_audio=False,
        duration_frames=100,
    )


def test_bin_anidado_contiene_subbin_y_clip():
    clips = [
        _clip(["Recamara 2", "Bano"], "C0003.MP4"),
        _clip(["Recamara 2"], "C0004.MP4"),
    ]
    tree = _group_by_category(clips)
    counter = [0]
    xml_str = _bin_xml("Recamara 2", tree["Recamara 2"], counter)
    root = ET.fromstring(f"<root>{xml_str}</root>")
    outer_bin = root.find("bin")
    assert outer_bin.find("name").text == "Recamara 2"

    names_in_children = [child.tag for child in outer_bin.find("children")]
    assert "bin" in names_in_children  # el subbin Bano
    assert "clip" in names_in_children  # el clip suelto de Recamara 2 (sin subcuarto)

    inner_bin = outer_bin.find("children/bin")
    assert inner_bin.find("name").text == "Bano"
    assert inner_bin.find("children/clip") is not None


def test_counter_incrementa_por_cada_clip():
    clips = [_clip(["Cocina"], "C0001.MP4"), _clip(["Cocina"], "C0002.MP4")]
    tree = _group_by_category(clips)
    counter = [0]
    _bin_xml("Cocina", tree["Cocina"], counter)
    assert counter[0] == 2
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_bin.py -v`
Expected: FAIL — `ImportError: cannot import name '_bin_xml'`

- [ ] **Step 3: Implementación**

Agregar a `src/clasificador_video/xmeml.py`:

```python
def _bin_xml(name: str, node: OrderedDict, counter: list[int]) -> str:
    children = []
    for key, value in node.items():
        if key == "__clips__":
            for clip in value:
                counter[0] += 1
                children.append(_clip_xml(clip, counter[0]))
        else:
            children.append(_bin_xml(key, value, counter))
    return f"<bin><name>{name}</name><children>{''.join(children)}</children></bin>"
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_bin.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/xmeml.py tests/test_xmeml_bin.py
git commit -m "feat: bins anidados recursivos en XML"
```

---

### Task 10: `generate_xmeml` — documento completo

**Files:**
- Modify: `src/clasificador_video/xmeml.py`
- Test: `tests/test_xmeml_generate.py`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_xmeml_generate.py`:

```python
import xml.etree.ElementTree as ET
from pathlib import Path

from clasificador_video.models import ClipSpec
from clasificador_video.xmeml import generate_xmeml


def _clip(category_path, name, flag="none", has_audio=False) -> ClipSpec:
    return ClipSpec(
        file_path=Path(f"/shooting/{name}"),
        category_path=category_path,
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=has_audio,
        duration_frames=900,
        flag=flag,
    )


def test_documento_completo_tiene_doctype_y_version():
    xml_str = generate_xmeml("Casa Jardin", [_clip(["Cocina"], "C0001.MP4")])
    assert "<!DOCTYPE xmeml>" in xml_str
    assert '<xmeml version="4">' in xml_str


def test_documento_parsea_y_tiene_bin_raiz_con_nombre_del_proyecto():
    xml_str = generate_xmeml("Casa Jardin", [_clip(["Cocina"], "C0001.MP4")])
    root = ET.fromstring(xml_str)
    root_bin = root.find("bin")
    assert root_bin.find("name").text == "Casa Jardin"


def test_documento_incluye_bins_anidados_y_secuencia():
    clips = [
        _clip(["Recamara 2", "Bano"], "C0003.MP4"),
        _clip(["Cocina"], "C0001.MP4", flag="pick"),
        _clip(["Cocina"], "C0002.MP4", flag="reject"),
    ]
    xml_str = generate_xmeml("Casa Jardin", clips)
    root = ET.fromstring(xml_str)
    children = root.find("bin/children")

    bin_names = [b.find("name").text for b in children.findall("bin")]
    assert "Recamara 2" in bin_names
    assert "Cocina" in bin_names

    assert children.find("sequence") is not None
    assert children.find("sequence/name").text == "Casa Jardin"

    cocina_bin = next(b for b in children.findall("bin") if b.find("name").text == "Cocina")
    labels = [c.find("labels/label2").text for c in cocina_bin.findall("children/clip")]
    assert "Forest" in labels
    assert "Rose" in labels


def test_documento_con_lista_vacia_no_truena():
    xml_str = generate_xmeml("Vacio", [])
    root = ET.fromstring(xml_str)
    assert root.find("bin/children/sequence") is not None
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_generate.py -v`
Expected: FAIL — `ImportError: cannot import name 'generate_xmeml'`

- [ ] **Step 3: Implementación**

Agregar a `src/clasificador_video/xmeml.py`:

```python
def _sequence_xml(project_name: str, clips: list[ClipSpec]) -> str:
    fps = clips[0].fps if clips else 30.0
    width = clips[0].width if clips else 1920
    height = clips[0].height if clips else 1080
    rate_xml = _rate_xml(fps)

    timecode_xml = (
        "<timecode>"
        f"{rate_xml}"
        "<string>00;00;00;00</string><frame>0</frame><displayformat>DF</displayformat>"
        "</timecode>"
    )

    return (
        '<sequence id="sequence-1">'
        f"<uuid>{uuid.uuid4()}</uuid>"
        "<duration>0</duration>"
        f"{rate_xml}"
        f"<name>{project_name}</name>"
        "<media><video><format><samplecharacteristics>"
        f"{rate_xml}"
        f"<width>{width}</width><height>{height}</height>"
        "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
        "<fielddominance>none</fielddominance><colordepth>24</colordepth>"
        "</samplecharacteristics></format>"
        "<track><enabled>TRUE</enabled><locked>FALSE</locked></track>"
        "</video><audio><numOutputChannels>2</numOutputChannels>"
        "<format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics></format>"
        "<track><enabled>TRUE</enabled><locked>FALSE</locked></track>"
        "</audio></media>"
        f"{timecode_xml}"
        "</sequence>"
    )


def generate_xmeml(project_name: str, clips: list[ClipSpec]) -> str:
    tree = _group_by_category(clips)
    counter = [0]
    bin_children = []
    for key, value in tree.items():
        if key == "__clips__":
            for clip in value:
                counter[0] += 1
                bin_children.append(_clip_xml(clip, counter[0]))
        else:
            bin_children.append(_bin_xml(key, value, counter))

    sequence_xml = _sequence_xml(project_name, clips)

    root_bin = (
        "<bin>"
        f"<name>{project_name}</name>"
        f"<children>{''.join(bin_children)}{sequence_xml}</children>"
        "</bin>"
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE xmeml>\n"
        '<xmeml version="4">'
        f"{root_bin}"
        "</xmeml>"
    )
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest tests/test_xmeml_generate.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Correr toda la suite completa**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && pytest -v`
Expected: todas las pruebas de Task 1 a Task 10 en verde (alrededor de 25 pruebas)

- [ ] **Step 6: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add src/clasificador_video/xmeml.py tests/test_xmeml_generate.py
git commit -m "feat: generate_xmeml arma el documento completo (bins + secuencia)"
```

---

### Task 11: Script de línea de comandos para el spike de validación

**Files:**
- Create: `scripts/spike_export.py`

- [ ] **Step 1: Escribir el script**

`scripts/spike_export.py`:

```python
"""Genera un xmeml de prueba a partir de 2-3 clips reales, para validar
manualmente el import en Premiere Pro. Edita MANIFEST antes de correr:
cada entrada es (ruta_absoluta_al_clip, categoria_path, in_frame, out_frame, flag).

Uso:
    python scripts/spike_export.py

Genera `spike-output.xml` en el directorio actual.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from clasificador_video.models import ClipSpec
from clasificador_video.probe import probe_clip
from clasificador_video.xmeml import generate_xmeml

# EDITA ESTA LISTA con rutas reales de tu Mac antes de correr el script.
# category_path: lista de cuarto/subcuarto, ej. ["Recamara 2", "Bano"]
# in_frame/out_frame: None para usar el clip completo, o un entero de frame.
# flag: "none", "pick" o "reject".
MANIFEST = [
    ("/ruta/completa/al/clip/con/audio.MP4", ["Cocina"], 30, 500, "pick"),
    ("/ruta/completa/al/clip/sin/audio/dron.MP4", ["Dron Aerea"], None, None, "none"),
    ("/ruta/completa/al/clip/recamara.MP4", ["Recamara 2", "Bano"], 0, 300, "reject"),
]


def main() -> None:
    clips = []
    for file_path, category_path, in_frame, out_frame, flag in MANIFEST:
        path = Path(file_path)
        if not path.exists():
            raise SystemExit(f"No existe el archivo: {path}")
        metadata = probe_clip(path)
        clips.append(
            ClipSpec(
                file_path=path,
                category_path=category_path,
                width=metadata["width"],
                height=metadata["height"],
                fps=metadata["fps"],
                has_audio=metadata["has_audio"],
                duration_frames=metadata["duration_frames"],
                in_frame=in_frame,
                out_frame=out_frame,
                flag=flag,
            )
        )

    xml_str = generate_xmeml("Spike de validacion", clips)
    output_path = Path("spike-output.xml")
    output_path.write_text(xml_str, encoding="utf-8")
    print(f"Escrito: {output_path.resolve()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar que el script corre sin argumentos reales todavía (falla de forma esperada)**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && python scripts/spike_export.py`
Expected: `SystemExit: No existe el archivo: /ruta/completa/al/clip/con/audio.MP4` (falla porque el MANIFEST todavía tiene rutas de ejemplo — es correcto en este punto, el usuario las reemplaza en el Task 12)

- [ ] **Step 3: Commit**

```bash
cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO"
git add scripts/spike_export.py
git commit -m "feat: script de spike para generar xmeml de validacion con clips reales"
```

---

### Task 12: Validación manual en Premiere Pro (paso humano, no automatizable)

**Files:**
- Modify: `scripts/spike_export.py` (solo el MANIFEST, con rutas reales)

Este task lo ejecuta el usuario, no el agente — requiere tener Premiere Pro abierto y clips reales de la FX30 a la mano.

- [ ] **Step 1: Elegir 2-3 clips reales del shooting**

Idealmente: uno con audio, uno sin audio (o simulando un dron sin pista), y uno con in/out recortado a la mitad del clip para confirmar el corte fino.

- [ ] **Step 2: Editar el MANIFEST en `scripts/spike_export.py`**

Reemplazar las tres rutas de ejemplo por las rutas reales de esos clips en disco, ajustando `category_path`, `in_frame`/`out_frame` y `flag` a gusto.

- [ ] **Step 3: Correr el script**

Run: `cd "/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO" && source .venv/bin/activate && python scripts/spike_export.py`
Expected: `Escrito: .../spike-output.xml` sin errores

- [ ] **Step 4: Importar en Premiere Pro 2026**

`File > Import...` → seleccionar `spike-output.xml`.

- [ ] **Step 5: Confirmar visualmente, uno por uno**

- Los bins aparecen con los nombres de cuarto/subcuarto esperados (incluyendo el bin anidado si usaste `category_path` con dos niveles).
- Los clips auto-vinculan (no aparecen como "Media Offline").
- El clip con in/out marcado (`in_frame`/`out_frame` distintos de `None`) al abrirse en el visor arranca y termina exactamente en el frame marcado — no uno o dos frames desfasado.
- El clip marcado `"pick"` se ve con la etiqueta de color verde (Forest) en el bin; el marcado `"reject"`, con la etiqueta rosa (Rose).
- El clip sin audio no aparece como offline (confirma que la regla de "no declarar `<audio>` si no hay pista real" sigue vigente en este generador).

- [ ] **Step 6: Registrar el resultado**

Si algo no cuadra (desfase de frames, bin mal anidado, color equivocado), anotar exactamente qué falló — eso define un Task 13 de corrección antes de seguir con la interfaz completa. Si todo cuadra, este plan queda cerrado y listo para iniciar el plan de la interfaz (PySide6 + mpv), que se escribe aparte una vez confirmado esto.

---

## Self-review de este plan

- **Cobertura del spec:** §3 (reglas de xmeml) → Tasks 4-10. §4 (cuartos/subcuartos) → Task 8-9 (agrupación en árbol). §6 (in/out) → Task 2 y 6. §7 (pick/reject sin filtrar exportación, labels de color) → Task 7 y 10. §9 (validación antes de la UI completa) → Task 11-12. Lo que este plan **no** cubre a propósito: UI (PySide6/mpv), autoguardado en JSON (§8), empaquetado (§10-11) — quedan para el siguiente plan, una vez este spike quede validado en Premiere.
- **Placeholders:** ninguno — cada paso trae código completo o instrucciones concretas de qué reemplazar (el MANIFEST del Task 12 es intencional: necesita rutas reales del usuario, no un valor que el agente pueda inventar).
- **Consistencia de tipos:** `ClipSpec`, `_rate_xml`, `_pathurl`, `_file_xml`, `_clipitem_xml`, `_clip_xml`, `_group_by_category`, `_bin_xml`, `generate_xmeml` se usan con la misma firma en todos los tasks donde aparecen.
