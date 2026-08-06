# App Externa del Clasificador de Video — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the PySide6 desktop app where Bruno classifies real-estate video shoots by room, marks in/out and pick/reject, and exports the JSON manifest that the already-finished Premiere UXP plugin consumes.

**Architecture:** A pure-logic core (manifest/room/ingest/thumbnail/player modules, all unit-tested with pytest, zero Qt imports) wrapped by a thin PySide6 UI shell (`src/clasificador_video/ui/`). `python-mpv` (with `hwdec=videotoolbox`) is the single dependency used for both video playback and thumbnail extraction — validated live on 2026-08-06 against real Sony FX30 footage, see `docs/superpowers/specs/2026-08-06-clasificador-video-app-externa-design.md`. `ffmpeg` is not a dependency of this app.

**Tech Stack:** Python 3.14, PySide6 (Qt 6 bindings), python-mpv (libmpv bindings), pytest, pytest-qt (for the thin widget smoke tests only).

**Specs implemented:**
- `docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md` (§3-11: ingest, cuartos, teclado, reproducción, in/out, pick/reject, proxies, autoguardado, manifest)
- `docs/superpowers/specs/2026-08-06-clasificador-video-app-externa-design.md` (layout, estado visual del filmstrip, diálogo de cuartos, ingest multi-carpeta, decisión de usar solo mpv)

**Existing code reused as-is, unchanged:** `src/clasificador_video/probe.py` (ffprobe wrapper — fps/rotación/duración). **Existing code left untouched, not part of this plan:** `models.py`, `rate.py`, `xmeml.py` and their tests — deliberately kept as inert reference from the discarded xmeml design (see `src/clasificador_video/README.md`). Do not import from them.

---

## Milestone 1 — Manifest data model and autosave

Pure Python, no Qt, no mpv. This is the data backbone everything else writes into.

### Task 1: Install PySide6 and python-mpv into the project venv

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the two new dependencies**

```
pytest>=7.4
PySide6>=6.7
python-mpv>=1.0.6
```

- [ ] **Step 2: Install into the venv**

Run: `.venv/bin/pip install -r requirements.txt`
Expected: both packages install without error (libmpv itself must already be on the system via `brew install mpv` — already done on this machine on 2026-08-06).

- [ ] **Step 3: Verify both import cleanly**

Run: `.venv/bin/python -c "import PySide6.QtWidgets, mpv; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: agregar PySide6 y python-mpv como dependencias de la app externa"
```

### Task 2: `Clip` and `Manifest` dataclasses with JSON export matching the fixed manifest format

**Files:**
- Create: `src/clasificador_video/manifest.py`
- Test: `tests/test_manifest.py`

The manifest format is **fixed by the plugin** (spec §11 of the 2026-08-05 doc) — field names and shape below are not negotiable.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_manifest.py
import json
from pathlib import Path

from clasificador_video.manifest import Clip, Manifest


def _clip(**overrides) -> Clip:
    base = dict(
        orden=1,
        ruta=Path("/shooting/C0012.MP4"),
        categoria_path=["Cocina"],
        fps=59.94005994005994,
        in_frame=None,
        out_frame=None,
        flag="none",
        ruta_proxy=None,
    )
    base.update(overrides)
    return Clip(**base)


def test_clip_to_dict_usa_las_llaves_exactas_del_manifest():
    clip = _clip(in_frame=30, out_frame=200, flag="pick", ruta_proxy=Path("/shooting/C0012S03.MP4"))
    assert clip.to_dict() == {
        "orden": 1,
        "ruta": "/shooting/C0012.MP4",
        "categoria_path": ["Cocina"],
        "fps": 59.94005994005994,
        "in_frame": 30,
        "out_frame": 200,
        "flag": "pick",
        "ruta_proxy": "/shooting/C0012S03.MP4",
    }


def test_clip_to_dict_sin_in_out_ni_proxy_usa_null():
    clip = _clip()
    d = clip.to_dict()
    assert d["in_frame"] is None
    assert d["out_frame"] is None
    assert d["ruta_proxy"] is None


def test_clip_flag_por_defecto_es_none():
    assert _clip().flag == "none"


def test_manifest_to_dict_incluye_proyecto_orientacion_y_clips_en_orden():
    m = Manifest(
        proyecto="Casa Jardin",
        orientacion="vertical",
        clips=[_clip(orden=2), _clip(orden=1)],
    )
    d = m.to_dict()
    assert d["proyecto"] == "Casa Jardin"
    assert d["orientacion"] == "vertical"
    assert [c["orden"] for c in d["clips"]] == [2, 1]  # respeta el orden de la lista, no reordena


def test_manifest_write_json_escribe_archivo_legible(tmp_path):
    m = Manifest(proyecto="Casa Jardin", orientacion="vertical", clips=[_clip()])
    out = tmp_path / "manifest.json"
    m.write_json(out)
    loaded = json.loads(out.read_text())
    assert loaded["proyecto"] == "Casa Jardin"
    assert loaded["clips"][0]["ruta"] == "/shooting/C0012.MP4"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_manifest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.manifest'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/manifest.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Clip:
    orden: int
    ruta: Path
    categoria_path: list[str]
    fps: float
    in_frame: int | None = None
    out_frame: int | None = None
    flag: str = "none"  # "none" | "pick" | "reject"
    ruta_proxy: Path | None = None

    def to_dict(self) -> dict:
        return {
            "orden": self.orden,
            "ruta": str(self.ruta),
            "categoria_path": self.categoria_path,
            "fps": self.fps,
            "in_frame": self.in_frame,
            "out_frame": self.out_frame,
            "flag": self.flag,
            "ruta_proxy": str(self.ruta_proxy) if self.ruta_proxy is not None else None,
        }


@dataclass
class Manifest:
    proyecto: str
    orientacion: str
    clips: list[Clip] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proyecto": self.proyecto,
            "orientacion": self.orientacion,
            "clips": [c.to_dict() for c in self.clips],
        }

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_manifest.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/manifest.py tests/test_manifest.py
git commit -m "feat: modelo Clip/Manifest con el formato exacto que espera el plugin UXP"
```

### Task 3: Atomic autosave of session state (spec §10)

Separate from `Manifest.write_json` (Task 2) — this is the local recovery file rewritten on every classification action, not the final export.

**Files:**
- Create: `src/clasificador_video/autosave.py`
- Test: `tests/test_autosave.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_autosave.py
import json

from clasificador_video.autosave import load_session, save_session


def test_save_session_escribe_json_legible(tmp_path):
    path = tmp_path / "sesion.json"
    save_session(path, {"proyecto": "Casa Jardin", "clips": [{"ruta": "/a.MP4"}]})
    assert json.loads(path.read_text())["proyecto"] == "Casa Jardin"


def test_save_session_no_deja_archivo_temporal_atras(tmp_path):
    path = tmp_path / "sesion.json"
    save_session(path, {"x": 1})
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_save_session_sobrescribe_de_forma_atomica(tmp_path):
    path = tmp_path / "sesion.json"
    save_session(path, {"version": 1})
    save_session(path, {"version": 2})
    assert json.loads(path.read_text())["version"] == 2


def test_load_session_de_archivo_inexistente_devuelve_none(tmp_path):
    assert load_session(tmp_path / "no-existe.json") is None


def test_load_session_lee_lo_que_guardo_save_session(tmp_path):
    path = tmp_path / "sesion.json"
    save_session(path, {"proyecto": "Casa Jardin"})
    assert load_session(path) == {"proyecto": "Casa Jardin"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_autosave.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.autosave'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/autosave.py
from __future__ import annotations

import json
import os
from pathlib import Path


def save_session(path: Path, data: dict) -> None:
    """Escribe `data` como JSON de forma atomica: archivo temporal + rename.

    Si la app se cierra a medio escribir, el rename atomico de POSIX
    garantiza que `path` siempre queda o con el contenido viejo completo,
    o con el nuevo completo -- nunca a medias.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    os.replace(tmp_path, path)


def load_session(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_autosave.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/autosave.py tests/test_autosave.py
git commit -m "feat: autoguardado de sesion con escritura atomica"
```

---

## Milestone 2 — Sistema de cuartos

### Task 4: Master room list, selection state, and auto-numbering (spec §4 / app-externa §5)

**Files:**
- Create: `src/clasificador_video/rooms.py`
- Test: `tests/test_rooms.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rooms.py
from clasificador_video.rooms import MASTER_ROOM_LIST, RoomSelection


def test_master_room_list_tiene_los_17_cuartos_del_spec():
    assert len(MASTER_ROOM_LIST) == 17
    assert "Cocina" in MASTER_ROOM_LIST
    assert "Dron/Aérea" in MASTER_ROOM_LIST


def test_seleccionar_cuarto_simple_lo_agrega_una_vez():
    sel = RoomSelection()
    sel.toggle("Cocina")
    assert sel.active_rooms() == ["Cocina"]


def test_deseleccionar_lo_quita():
    sel = RoomSelection()
    sel.toggle("Cocina")
    sel.toggle("Cocina")
    assert sel.active_rooms() == []


def test_cuarto_repetible_con_count_2_numera_automatico():
    sel = RoomSelection()
    sel.set_count("Recámara", 2)
    assert sel.active_rooms() == ["Recámara 1", "Recámara 2"]


def test_cuarto_repetible_con_count_0_no_aparece():
    sel = RoomSelection()
    sel.set_count("Recámara", 2)
    sel.set_count("Recámara", 0)
    assert sel.active_rooms() == []


def test_cuarto_personalizado_se_agrega_al_final():
    sel = RoomSelection()
    sel.toggle("Sala")
    sel.add_custom("Bodega")
    assert sel.active_rooms() == ["Sala", "Bodega"]


def test_orden_de_seleccion_se_respeta_en_active_rooms():
    sel = RoomSelection()
    sel.toggle("Alberca")
    sel.toggle("Fachada")
    assert sel.active_rooms() == ["Alberca", "Fachada"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_rooms.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.rooms'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/rooms.py
from __future__ import annotations

MASTER_ROOM_LIST: list[str] = [
    "Fachada",
    "Sala",
    "Comedor",
    "Cocina",
    "Recámara",
    "Baño",
    "Estudio/Oficina",
    "Alberca",
    "Jardín/Patio",
    "Terraza",
    "Roof garden",
    "Garage/Cochera",
    "Vestíbulo/Hall",
    "Área de servicio",
    "Dron/Aérea",
    "Amenidades comunes",
    "B-roll/Detalles",
]

REPEATABLE_ROOMS = {"Recámara", "Baño"}


class RoomSelection:
    """Estado del dialogo 'configurar cuartos' (spec app-externa §5).

    Guarda el orden en que se van activando los cuartos -- ese orden es el
    que se le presenta al usuario despues como columna de cuartos.
    """

    def __init__(self) -> None:
        self._order: list[str] = []
        self._counts: dict[str, int] = {}

    def toggle(self, room: str) -> None:
        if room in self._order:
            self._order.remove(room)
        else:
            self._order.append(room)

    def set_count(self, room: str, count: int) -> None:
        assert room in REPEATABLE_ROOMS, f"'{room}' no es un cuarto repetible"
        self._counts[room] = count
        if room in self._order:
            self._order.remove(room)
        if count > 0:
            self._order.append(room)

    def add_custom(self, name: str) -> None:
        self._order.append(name)

    def active_rooms(self) -> list[str]:
        result = []
        for room in self._order:
            if room in self._counts:
                result.extend(f"{room} {i}" for i in range(1, self._counts[room] + 1))
            else:
                result.append(room)
        return result
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_rooms.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/rooms.py tests/test_rooms.py
git commit -m "feat: lista maestra de cuartos y estado de seleccion con numeracion automatica"
```

### Task 5: Category path builder with lazy subcuarto creation (spec app-externa §5)

`categoria_path` is the exact field the manifest needs (`["Recámara 2", "Baño"]`). Subcuartos are created the first time they're used against a specific parent room, not configured upfront.

**Files:**
- Create: `src/clasificador_video/category_path.py`
- Test: `tests/test_category_path.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_category_path.py
from clasificador_video.category_path import CategoryTree


def test_cuarto_simple_da_path_de_un_elemento():
    tree = CategoryTree()
    assert tree.path_for("Cocina") == ["Cocina"]


def test_primera_vez_que_se_usa_un_subcuarto_lo_crea():
    tree = CategoryTree()
    tree.attach_subroom(parent="Recámara 2", subroom="Baño")
    assert tree.path_for("Recámara 2", subroom="Baño") == ["Recámara 2", "Baño"]


def test_subcuarto_de_un_padre_no_afecta_a_otro_padre_homonimo():
    tree = CategoryTree()
    tree.attach_subroom(parent="Recámara 1", subroom="Baño")
    tree.attach_subroom(parent="Recámara 2", subroom="Baño")
    assert tree.path_for("Recámara 1", subroom="Baño") == ["Recámara 1", "Baño"]
    assert tree.path_for("Recámara 2", subroom="Baño") == ["Recámara 2", "Baño"]


def test_pedir_subcuarto_no_creado_lanza_error_claro():
    tree = CategoryTree()
    try:
        tree.path_for("Recámara 2", subroom="Closet")
        assert False, "debio lanzar ValueError"
    except ValueError as e:
        assert "Closet" in str(e)
        assert "Recámara 2" in str(e)


def test_known_subrooms_for_lista_los_subcuartos_ya_creados_de_un_padre():
    tree = CategoryTree()
    tree.attach_subroom(parent="Recámara 2", subroom="Baño")
    tree.attach_subroom(parent="Recámara 2", subroom="Closet")
    assert tree.known_subrooms_for("Recámara 2") == ["Baño", "Closet"]
    assert tree.known_subrooms_for("Recámara 1") == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_category_path.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.category_path'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/category_path.py
from __future__ import annotations


class CategoryTree:
    """Construye categoria_path para el manifest, con subcuartos creados
    perezosamente por padre (spec app-externa §5): 'Recamara 1 > Bano' y
    'Recamara 2 > Bano' son ramas independientes aunque compartan nombre.
    """

    def __init__(self) -> None:
        self._subrooms_by_parent: dict[str, list[str]] = {}

    def attach_subroom(self, parent: str, subroom: str) -> None:
        existing = self._subrooms_by_parent.setdefault(parent, [])
        if subroom not in existing:
            existing.append(subroom)

    def known_subrooms_for(self, parent: str) -> list[str]:
        return list(self._subrooms_by_parent.get(parent, []))

    def path_for(self, room: str, subroom: str | None = None) -> list[str]:
        if subroom is None:
            return [room]
        if subroom not in self._subrooms_by_parent.get(room, []):
            raise ValueError(
                f"'{subroom}' no ha sido creado como subcuarto de '{room}' todavia "
                f"-- usa attach_subroom primero"
            )
        return [room, subroom]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_category_path.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/category_path.py tests/test_category_path.py
git commit -m "feat: arbol de categorias con subcuartos creados por padre, no por nombre"
```

---

## Milestone 3 — Ingest

### Task 6: Multi-folder ingest tree (spec §3 + app-externa §6)

**Files:**
- Create: `src/clasificador_video/ingest.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ingest.py
from pathlib import Path

from clasificador_video.ingest import IngestTree


def test_importar_una_carpeta_la_agrega_con_su_nombre(tmp_path):
    origen = tmp_path / "FX30"
    origen.mkdir()
    (origen / "C0001.MP4").touch()
    (origen / "C0002.MP4").touch()

    tree = IngestTree()
    tree.import_folder(origen)

    assert [f.name for f in tree.top_level_folders()] == ["FX30"]
    assert {p.name for p in tree.top_level_folders()[0].files} == {"C0001.MP4", "C0002.MP4"}


def test_importar_varias_carpetas_a_la_vez(tmp_path):
    fx30 = tmp_path / "FX30"
    dron = tmp_path / "Dron"
    fx30.mkdir()
    dron.mkdir()
    (fx30 / "C0001.MP4").touch()
    (dron / "DJI_0001.MP4").touch()

    tree = IngestTree()
    tree.import_folders([fx30, dron])

    names = {f.name for f in tree.top_level_folders()}
    assert names == {"FX30", "Dron"}


def test_importar_solo_lee_archivos_de_video_no_otros_archivos(tmp_path):
    origen = tmp_path / "FX30"
    origen.mkdir()
    (origen / "C0001.MP4").touch()
    (origen / "notas.txt").touch()
    (origen / ".DS_Store").touch()

    tree = IngestTree()
    tree.import_folder(origen)

    assert [p.name for p in tree.top_level_folders()[0].files] == ["C0001.MP4"]


def test_renombrar_carpeta_top_level(tmp_path):
    origen = tmp_path / "FX30"
    origen.mkdir()

    tree = IngestTree()
    tree.import_folder(origen)
    tree.rename_folder(origen, "Cámara principal")

    assert tree.top_level_folders()[0].display_name == "Cámara principal"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.ingest'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ingest.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mxf", ".lrf"}


@dataclass
class IngestFolder:
    source_path: Path
    display_name: str
    files: list[Path] = field(default_factory=list)


class IngestTree:
    """Panel de ingest (spec §3): carpetas de nivel superior, una por
    tarjeta/camara importada, sin interpretar el contenido -- el usuario
    clasifica clip por clip despues.
    """

    def __init__(self) -> None:
        self._folders: list[IngestFolder] = []

    def import_folder(self, path: Path) -> None:
        self.import_folders([path])

    def import_folders(self, paths: list[Path]) -> None:
        for path in paths:
            files = sorted(
                p for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
            )
            self._folders.append(IngestFolder(source_path=path, display_name=path.name, files=files))

    def top_level_folders(self) -> list[IngestFolder]:
        return list(self._folders)

    def rename_folder(self, source_path: Path, new_name: str) -> None:
        for folder in self._folders:
            if folder.source_path == source_path:
                folder.display_name = new_name
                return
        raise ValueError(f"carpeta no encontrada en el ingest: {source_path}")
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_ingest.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ingest.py tests/test_ingest.py
git commit -m "feat: ingest de multiples carpetas/camaras a la vez"
```

### Task 7: Proxy matching by `S03` suffix (spec §3)

**Files:**
- Create: `src/clasificador_video/proxy_match.py`
- Test: `tests/test_proxy_match.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_proxy_match.py
from pathlib import Path

from clasificador_video.proxy_match import match_proxies


def test_empareja_por_stem_mas_sufijo_s03():
    originales = [Path("/cam/20260804_PIB0587.MP4")]
    proxies = [Path("/proxies/20260804_PIB0587S03.MP4")]
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/20260804_PIB0587.MP4")] == Path("/proxies/20260804_PIB0587S03.MP4")


def test_original_sin_proxy_correspondiente_queda_none():
    originales = [Path("/cam/DJI_0001.MP4")]
    proxies: list[Path] = []
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/DJI_0001.MP4")] is None


def test_no_confunde_prefijos_parecidos():
    originales = [Path("/cam/C001.MP4"), Path("/cam/C0010.MP4")]
    proxies = [Path("/proxies/C0010S03.MP4")]
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/C001.MP4")] is None
    assert result[Path("/cam/C0010.MP4")] == Path("/proxies/C0010S03.MP4")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_proxy_match.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.proxy_match'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/proxy_match.py
from __future__ import annotations

from pathlib import Path


def match_proxies(originales: list[Path], proxies: list[Path]) -> dict[Path, Path | None]:
    """Empareja cada original con su proxy por 'mismo stem + S03' (spec §3).

    Ej: 20260804_PIB0587.MP4 <-> 20260804_PIB0587S03.MP4. Sin match, None
    -- no es error (dron y otras fuentes sin proxy son el caso normal).
    """
    proxy_by_stem: dict[str, Path] = {p.stem[:-3]: p for p in proxies if p.stem.endswith("S03")}
    return {original: proxy_by_stem.get(original.stem) for original in originales}
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_proxy_match.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proxy_match.py tests/test_proxy_match.py
git commit -m "feat: emparejar proxies por sufijo S03"
```

---

## Milestone 4 — Lectura de video (miniaturas y reproductor)

Both built on the exact mpv invocation validated live on 2026-08-06 (see spec §2 of the 2026-08-06 doc): `mpv --vo=image` for thumbnails (subprocess, no GUI needed), `python-mpv` with `hwdec=videotoolbox` for playback.

### Task 8: Thumbnail extraction wrapping the validated mpv command

**Files:**
- Create: `src/clasificador_video/thumbnails.py`
- Test: `tests/test_thumbnails.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_thumbnails.py
from pathlib import Path

from clasificador_video.thumbnails import build_thumbnail_command, extract_thumbnail


def test_build_thumbnail_command_incluye_start_y_frames_1():
    cmd = build_thumbnail_command(
        video=Path("/shooting/C0012.MP4"),
        at_seconds=3.0,
        outdir=Path("/tmp/thumbs/xyz"),
    )
    assert cmd[0].endswith("mpv")
    assert "--vo=image" in cmd
    assert "--vo-image-outdir=/tmp/thumbs/xyz" in cmd
    assert "--start=3.0" in cmd
    assert "--frames=1" in cmd
    assert "--hwdec=videotoolbox" in cmd
    assert cmd[-1] == "/shooting/C0012.MP4"


def test_extract_thumbnail_corre_el_comando_y_devuelve_la_ruta_del_frame(tmp_path):
    calls = []

    def fake_runner(cmd):
        calls.append(cmd)
        outdir = Path(cmd[cmd.index("--vo-image-outdir=" + str(tmp_path)) ].split("=", 1)[1]) \
            if any(c.startswith("--vo-image-outdir=") for c in cmd) else None
        outdir = Path(next(c for c in cmd if c.startswith("--vo-image-outdir=")).split("=", 1)[1])
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "00000001.jpg").write_bytes(b"fake-jpeg")

    result = extract_thumbnail(
        video=tmp_path / "C0012.MP4",
        at_seconds=3.0,
        outdir=tmp_path / "thumbs",
        runner=fake_runner,
    )

    assert result == tmp_path / "thumbs" / "00000001.jpg"
    assert result.read_bytes() == b"fake-jpeg"
    assert len(calls) == 1


def test_extract_thumbnail_sin_frame_producido_lanza_error_claro(tmp_path):
    def fake_runner(cmd):
        pass  # no escribe nada, simula un fallo silencioso de mpv

    try:
        extract_thumbnail(video=tmp_path / "C0012.MP4", at_seconds=3.0, outdir=tmp_path / "thumbs", runner=fake_runner)
        assert False, "debio lanzar RuntimeError"
    except RuntimeError as e:
        assert "C0012.MP4" in str(e)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_thumbnails.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.thumbnails'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/thumbnails.py
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

MPV_BIN = shutil.which("mpv") or "/opt/homebrew/bin/mpv"


def build_thumbnail_command(video: Path, at_seconds: float, outdir: Path) -> list[str]:
    """Comando validado en vivo el 2026-08-06 contra clips reales de la
    Sony FX30: respeta la rotacion del clip sin flags adicionales, y no
    tiene el problema de extraccion por seek que si afecta a ffmpeg en
    algunos casos limite (ver spec 2026-08-06, §2).
    """
    return [
        MPV_BIN,
        "--no-config",
        "--vo=image",
        f"--vo-image-outdir={outdir}",
        f"--start={at_seconds}",
        "--frames=1",
        "--hwdec=videotoolbox",
        str(video),
    ]


def extract_thumbnail(
    video: Path,
    at_seconds: float,
    outdir: Path,
    runner: Callable[[list[str]], None] = lambda cmd: subprocess.run(cmd, capture_output=True, check=False),
) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = build_thumbnail_command(video, at_seconds, outdir)
    runner(cmd)
    frame = outdir / "00000001.jpg"
    if not frame.exists():
        raise RuntimeError(f"mpv no genero ninguna miniatura para {video} en el segundo {at_seconds}")
    return frame
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_thumbnails.py -v`
Expected: 3 passed

- [ ] **Step 5: Manual smoke test against real footage**

Run:
```bash
.venv/bin/python -c "
from pathlib import Path
from clasificador_video.thumbnails import extract_thumbnail
p = extract_thumbnail(Path('TEST/20260804_PIB0589.MP4'), 3.0, Path('/tmp/thumb-smoke'))
print(p, p.stat().st_size, 'bytes')
"
```
Expected: prints a path ending in `00000001.jpg` with a non-zero size. (This is the same command validated live on 2026-08-06 — this step just confirms the wrapper wires it correctly, not re-litigating the risk.)

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/thumbnails.py tests/test_thumbnails.py
git commit -m "feat: extraer miniaturas con mpv, respetando rotacion"
```

### Task 9: `MpvPlayer` wrapper (playback, quality profile, in/out marking)

Wraps `python-mpv` behind a small interface so the UI layer and tests don't touch the real `mpv.MPV` object directly.

**Files:**
- Create: `src/clasificador_video/player.py`
- Test: `tests/test_player.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_player.py
from pathlib import Path

from clasificador_video.player import MpvPlayer, QUALITY_PROFILES


class FakeMpv:
    """Sustituto de mpv.MPV para probar MpvPlayer sin abrir un reproductor real."""

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0
        self.vid_scale = None
        self.commands = []

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        self.commands.append(args)


def test_mpv_player_se_inicializa_con_hwdec_videotoolbox():
    player = MpvPlayer(mpv_factory=FakeMpv)
    assert player._mpv.init_kwargs["hwdec"] == "videotoolbox"


def test_open_carga_el_archivo():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.open(Path("/shooting/C0012.MP4"))
    assert player._mpv.loaded_path == "/shooting/C0012.MP4"


def test_play_pause_alterna_el_estado():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.play()
    assert player._mpv.pause is False
    player.pause()
    assert player._mpv.pause is True


def test_set_quality_aplica_el_perfil_conocido():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player.set_quality("1/2")
    assert player._mpv.vid_scale == QUALITY_PROFILES["1/2"]


def test_set_quality_perfil_desconocido_lanza_error_claro():
    player = MpvPlayer(mpv_factory=FakeMpv)
    try:
        player.set_quality("1/16")
        assert False, "debio lanzar ValueError"
    except ValueError as e:
        assert "1/16" in str(e)


def test_mark_in_guarda_el_frame_actual_en_segundos_convertido_por_fps():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = 2.0
    player.mark_in(fps=60.0)
    assert player.in_frame == 120


def test_mark_out_guarda_el_frame_actual():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = 5.0
    player.mark_out(fps=60.0)
    assert player.out_frame == 300


def test_clear_in_out_resetea_ambos():
    player = MpvPlayer(mpv_factory=FakeMpv)
    player._mpv.time_pos = 2.0
    player.mark_in(fps=60.0)
    player.mark_out(fps=60.0)
    player.clear_in_out()
    assert player.in_frame is None
    assert player.out_frame is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_player.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.player'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/player.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

QUALITY_PROFILES: dict[str, float] = {
    "Full": 1.0,
    "1/2": 0.5,
    "1/4": 0.25,
    "1/8": 0.125,
}


class MpvPlayer:
    """Envoltura delgada sobre python-mpv (spec §6): hwdec=videotoolbox
    fijo (validado en vivo el 2026-08-06 contra HEVC 10-bit real de la
    FX30), selector de calidad, y marcado de in/out sobre el tiempo
    actual de reproduccion.
    """

    def __init__(self, mpv_factory: Callable[..., object]):
        self._mpv = mpv_factory(hwdec="videotoolbox")
        self.in_frame: int | None = None
        self.out_frame: int | None = None

    def open(self, path: Path) -> None:
        self._mpv.play(str(path))

    def play(self) -> None:
        self._mpv.pause = False

    def pause(self) -> None:
        self._mpv.pause = True

    def set_quality(self, profile_name: str) -> None:
        if profile_name not in QUALITY_PROFILES:
            raise ValueError(f"perfil de calidad desconocido: '{profile_name}'")
        self._mpv.vid_scale = QUALITY_PROFILES[profile_name]

    def mark_in(self, fps: float) -> None:
        self.in_frame = round(self._mpv.time_pos * fps)

    def mark_out(self, fps: float) -> None:
        self.out_frame = round(self._mpv.time_pos * fps)

    def clear_in_out(self) -> None:
        self.in_frame = None
        self.out_frame = None
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_player.py -v`
Expected: 8 passed

- [ ] **Step 5: Manual smoke test against real footage (real `mpv.MPV`, not the fake)**

Run:
```bash
.venv/bin/python -c "
import time
from pathlib import Path
import mpv as real_mpv
from clasificador_video.player import MpvPlayer

player = MpvPlayer(mpv_factory=lambda **kw: real_mpv.MPV(vo='null', **kw))
player.open(Path('TEST/20260804_PIB0589.MP4'))
player.play()
time.sleep(1)
print('time_pos:', player._mpv.time_pos)
"
```
Expected: no traceback, prints a `time_pos` greater than 0 — confirms the wrapper drives a real mpv instance correctly, not just the fake.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/player.py tests/test_player.py
git commit -m "feat: envoltura MpvPlayer con hwdec, calidad y marcado de in/out"
```

---

## Milestone 5 — Interfaz (PySide6)

From here on, widgets are thin and delegate all logic to Milestones 1-4. Tests use `pytest-qt`'s `qtbot` fixture for smoke-level verification (widget exists, shows the right text/state) — the business logic itself is already covered above.

### Task 10: Add `pytest-qt` and confirm it can create a `QApplication`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the dependency**

```
pytest>=7.4
pytest-qt>=4.4
PySide6>=6.7
python-mpv>=1.0.6
```

- [ ] **Step 2: Install**

Run: `.venv/bin/pip install -r requirements.txt`

- [ ] **Step 3: Write and run a throwaway smoke test**

```python
# tests/test_qt_smoke.py
from PySide6.QtWidgets import QLabel


def test_qtbot_puede_crear_un_widget(qtbot):
    label = QLabel("hola")
    qtbot.addWidget(label)
    assert label.text() == "hola"
```

Run: `.venv/bin/pytest tests/test_qt_smoke.py -v`
Expected: 1 passed. (On a headless CI machine this would need `QT_QPA_PLATFORM=offscreen`; on Bruno's Mac with a display it runs normally.)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt tests/test_qt_smoke.py
git commit -m "chore: agregar pytest-qt para pruebas de humo de la interfaz"
```

### Task 11: Room configuration dialog

**Files:**
- Create: `src/clasificador_video/ui/room_config_dialog.py`
- Test: `tests/ui/test_room_config_dialog.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_room_config_dialog.py
from clasificador_video.rooms import MASTER_ROOM_LIST
from clasificador_video.ui.room_config_dialog import RoomConfigDialog


def test_dialog_muestra_un_chip_por_cada_cuarto_maestro(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    assert len(dialog.chip_buttons) == len(MASTER_ROOM_LIST)


def test_click_en_un_chip_lo_activa_y_actualiza_la_seleccion(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    dialog.chip_buttons["Cocina"].click()
    assert dialog.selection.active_rooms() == ["Cocina"]


def test_agregar_cuarto_personalizado_lo_mete_a_la_seleccion(qtbot):
    dialog = RoomConfigDialog(project_name="Casa Jardin")
    qtbot.addWidget(dialog)
    dialog.custom_room_input.setText("Bodega")
    dialog.add_custom_button.click()
    assert "Bodega" in dialog.selection.active_rooms()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_room_config_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.ui'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/__init__.py
```

```python
# src/clasificador_video/ui/room_config_dialog.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from clasificador_video.rooms import MASTER_ROOM_LIST, RoomSelection


class RoomConfigDialog(QDialog):
    """Dialogo previo a clasificar (spec app-externa §5): marcar cuartos
    de la lista fija + agregar personalizados. Se hace una vez por
    shooting, no es una pantalla separada del flujo principal.
    """

    def __init__(self, project_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configurar cuartos — {project_name}")
        self.selection = RoomSelection()
        self.chip_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)

        grid = QGridLayout()
        for i, room in enumerate(MASTER_ROOM_LIST):
            button = QPushButton(room)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, r=room: self._on_chip_clicked(r))
            self.chip_buttons[room] = button
            grid.addWidget(button, i // 2, i % 2)
        layout.addLayout(grid)

        custom_row = QHBoxLayout()
        self.custom_room_input = QLineEdit()
        self.custom_room_input.setPlaceholderText("Agregar cuarto personalizado")
        self.add_custom_button = QPushButton("+ Agregar")
        self.add_custom_button.clicked.connect(self._on_add_custom)
        custom_row.addWidget(self.custom_room_input)
        custom_row.addWidget(self.add_custom_button)
        layout.addLayout(custom_row)

        self.start_button = QPushButton("Empezar a clasificar →")
        layout.addWidget(self.start_button)

    def _on_chip_clicked(self, room: str) -> None:
        self.selection.toggle(room)

    def _on_add_custom(self) -> None:
        name = self.custom_room_input.text().strip()
        if name:
            self.selection.add_custom(name)
            self.custom_room_input.clear()
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_room_config_dialog.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/__init__.py src/clasificador_video/ui/room_config_dialog.py tests/ui/test_room_config_dialog.py
git commit -m "feat: dialogo de configuracion de cuartos"
```

### Task 12: Filmstrip widget with pick/reject/current visual state (app-externa §4, opción A elegida)

**Files:**
- Create: `src/clasificador_video/ui/filmstrip.py`
- Test: `tests/ui/test_filmstrip.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_filmstrip.py
from pathlib import Path

from clasificador_video.ui.filmstrip import ClipThumbnail, Filmstrip


def test_filmstrip_agrega_un_thumbnail_por_clip(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([
        ClipThumbnail(path=Path("/a.MP4"), thumbnail_path=None, room_label="Sin clasificar", flag="none"),
        ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="pick"),
    ])
    assert strip.count() == 2


def test_estilo_de_pick_aplica_borde_verde(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="pick")])
    item = strip.item_widgets[0]
    assert "border-color: #3bb273" in item.styleSheet()


def test_estilo_de_reject_aplica_borde_rosa(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Cocina", flag="reject")])
    item = strip.item_widgets[0]
    assert "border-color: #e0556f" in item.styleSheet()


def test_sin_flag_no_aplica_borde_de_color(qtbot):
    strip = Filmstrip()
    qtbot.addWidget(strip)
    strip.set_clips([ClipThumbnail(path=Path("/b.MP4"), thumbnail_path=None, room_label="Sin clasificar", flag="none")])
    item = strip.item_widgets[0]
    assert "#3bb273" not in item.styleSheet()
    assert "#e0556f" not in item.styleSheet()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_filmstrip.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.ui.filmstrip'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/filmstrip.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

PICK_COLOR = "#3bb273"
REJECT_COLOR = "#e0556f"


@dataclass
class ClipThumbnail:
    path: Path
    thumbnail_path: Path | None
    room_label: str
    flag: str  # "none" | "pick" | "reject"


class _ClipItemWidget(QWidget):
    def __init__(self, clip: ClipThumbnail):
        super().__init__()
        layout = QVBoxLayout(self)
        image_label = QLabel()
        if clip.thumbnail_path is not None:
            image_label.setText("")  # el pixmap real se wirea en Task 14
        else:
            image_label.setText("(sin miniatura)")
        layout.addWidget(image_label)
        layout.addWidget(QLabel(clip.room_label))

        border_color = {"pick": PICK_COLOR, "reject": REJECT_COLOR}.get(clip.flag)
        if border_color:
            image_label.setStyleSheet(f"border: 2px solid; border-color: {border_color};")


class Filmstrip(QWidget):
    """Fila de miniaturas (app-externa §3-4): borde verde/rosa por
    pick/reject, nombre del cuarto debajo, opcion A elegida sobre la B.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self.item_widgets: list[_ClipItemWidget] = []

    def set_clips(self, clips: list[ClipThumbnail]) -> None:
        for widget in self.item_widgets:
            widget.setParent(None)
        self.item_widgets = []
        for clip in clips:
            item = _ClipItemWidget(clip)
            self._layout.addWidget(item)
            self.item_widgets.append(item)

    def count(self) -> int:
        return len(self.item_widgets)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_filmstrip.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/filmstrip.py tests/ui/test_filmstrip.py
git commit -m "feat: filmstrip con estado visual de pick/reject (opcion A)"
```

### Task 13: Keyboard shortcut router (spec §5) — pure logic, no Qt

Kept out of Qt so the mapping rules (which key does what, given the current context) are unit-testable without a running event loop. The UI wires `QShortcut` to call into this in Task 14.

**Files:**
- Create: `src/clasificador_video/keyboard.py`
- Test: `tests/test_keyboard.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_keyboard.py
from clasificador_video.keyboard import KeyboardRouter


def test_numero_sin_subcuartos_asigna_el_cuarto_directo():
    router = KeyboardRouter(active_rooms=["Sala", "Cocina", "Recámara 1"])
    assert router.resolve_room_key("2") == ["Cocina"]


def test_numero_con_subcuartos_conocidos_entra_en_modo_subcuarto():
    router = KeyboardRouter(active_rooms=["Sala", "Recámara 1"], subrooms={"Recámara 1": ["Baño"]})
    assert router.resolve_room_key("2") is None  # no resuelve todavia, esperando el subcuarto
    assert router.pending_parent == "Recámara 1"
    assert router.resolve_subroom_key("1") == ["Recámara 1", "Baño"]


def test_tecla_fuera_de_rango_no_hace_nada():
    router = KeyboardRouter(active_rooms=["Sala"])
    assert router.resolve_room_key("9") is None
    assert router.pending_parent is None


def test_pick_reject_se_resuelven_directo():
    router = KeyboardRouter(active_rooms=["Sala"])
    assert router.resolve_action_key("p") == "pick"
    assert router.resolve_action_key("x") == "reject"
    assert router.resolve_action_key("u") == "none"
    assert router.resolve_action_key("z") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_keyboard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.keyboard'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/keyboard.py
from __future__ import annotations

ACTION_KEYS = {"p": "pick", "x": "reject", "u": "none"}


class KeyboardRouter:
    """Traduce teclas 1-9 y P/X/U a acciones (spec §5).

    Si el cuarto activo en la tecla presionada tiene subcuartos conocidos,
    la primera tecla NO resuelve un cuarto -- entra en 'pending_parent' y
    espera la siguiente tecla (que elige el subcuarto), sin limite de
    tiempo entre ambas, tal como especifica el spec.
    """

    def __init__(self, active_rooms: list[str], subrooms: dict[str, list[str]] | None = None):
        self.active_rooms = active_rooms
        self.subrooms = subrooms or {}
        self.pending_parent: str | None = None

    def resolve_room_key(self, key: str) -> list[str] | None:
        index = int(key) - 1
        if index < 0 or index >= len(self.active_rooms):
            return None
        room = self.active_rooms[index]
        if room in self.subrooms and self.subrooms[room]:
            self.pending_parent = room
            return None
        return [room]

    def resolve_subroom_key(self, key: str) -> list[str] | None:
        if self.pending_parent is None:
            return None
        options = self.subrooms.get(self.pending_parent, [])
        index = int(key) - 1
        if index < 0 or index >= len(options):
            return None
        parent = self.pending_parent
        self.pending_parent = None
        return [parent, options[index]]

    def resolve_action_key(self, key: str) -> str | None:
        return ACTION_KEYS.get(key.lower())
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_keyboard.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/keyboard.py tests/test_keyboard.py
git commit -m "feat: router de teclado para cuartos/subcuartos y pick-reject"
```

### Task 14: Main window — wire everything together

This is the integration point: room list + player + filmstrip + legend in one window (app-externa §3, opción B elegida), backed by the modules from Milestones 1-4.

**Files:**
- Create: `src/clasificador_video/ui/main_window.py`
- Create: `src/clasificador_video/app.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/ui/test_main_window.py
from pathlib import Path

from clasificador_video.category_path import CategoryTree
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


def _window(qtbot) -> MainWindow:
    selection = RoomSelection()
    selection.toggle("Sala")
    selection.toggle("Cocina")
    window = MainWindow(project_name="Casa Jardin", room_selection=selection, category_tree=CategoryTree())
    qtbot.addWidget(window)
    return window


def test_ventana_muestra_los_cuartos_activos_en_la_columna(qtbot):
    window = _window(qtbot)
    assert window.room_list_widget.count() == 2


def test_cargar_clips_los_manda_al_filmstrip(qtbot):
    window = _window(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    assert window.filmstrip.count() == 1


def test_presionar_tecla_de_cuarto_asigna_categoria_al_clip_actual(qtbot):
    window = _window(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.handle_key_press("2")  # "Cocina" es el segundo cuarto activo
    assert window.current_clip.categoria_path == ["Cocina"]


def test_presionar_p_marca_pick_en_el_clip_actual(qtbot):
    window = _window(qtbot)
    clips = [Clip(orden=1, ruta=Path("/a.MP4"), categoria_path=[], fps=30.0)]
    window.load_clips(clips)
    window.handle_key_press("p")
    assert window.current_clip.flag == "pick"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clasificador_video.ui.main_window'`

- [ ] **Step 3: Implement**

```python
# src/clasificador_video/ui/main_window.py
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QVBoxLayout, QWidget

from clasificador_video.category_path import CategoryTree
from clasificador_video.keyboard import KeyboardRouter
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.filmstrip import ClipThumbnail, Filmstrip


class MainWindow(QWidget):
    """Ventana unica (app-externa §3, opcion B): reproductor al centro,
    columna de cuartos a un lado, filmstrip abajo. Esta clase es la
    integracion -- toda la logica real vive en los modulos de las
    Milestones 1-4, wireados aqui.
    """

    def __init__(self, project_name: str, room_selection: RoomSelection, category_tree: CategoryTree, parent=None):
        super().__init__(parent)
        self.setWindowTitle(project_name)
        self.room_selection = room_selection
        self.category_tree = category_tree
        self.clips: list[Clip] = []
        self.current_index = 0
        self._router = KeyboardRouter(active_rooms=room_selection.active_rooms())

        self.room_list_widget = QListWidget()
        self.room_list_widget.addItems(room_selection.active_rooms())

        self.filmstrip = Filmstrip()

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(self.room_list_widget, stretch=0)
        root.addLayout(top, stretch=1)
        root.addWidget(self.filmstrip, stretch=0)

    @property
    def current_clip(self) -> Clip | None:
        if not self.clips:
            return None
        return self.clips[self.current_index]

    def load_clips(self, clips: list[Clip]) -> None:
        self.clips = clips
        self.current_index = 0
        self._refresh_filmstrip()

    def handle_key_press(self, key: str) -> None:
        if self.current_clip is None:
            return
        room_path = self._router.resolve_room_key(key)
        if room_path is not None:
            self.current_clip.categoria_path = room_path
            self._refresh_filmstrip()
            return
        action = self._router.resolve_action_key(key)
        if action is not None:
            self.current_clip.flag = action
            self._refresh_filmstrip()

    def _refresh_filmstrip(self) -> None:
        self.filmstrip.set_clips([
            ClipThumbnail(
                path=clip.ruta,
                thumbnail_path=None,
                room_label=clip.categoria_path[-1] if clip.categoria_path else "Sin clasificar",
                flag=clip.flag,
            )
            for clip in self.clips
        ])
```

```python
# src/clasificador_video/app.py
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from clasificador_video.category_path import CategoryTree
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow(
        project_name="Sin proyecto",
        room_selection=RoomSelection(),
        category_tree=CategoryTree(),
    )
    window.resize(1100, 700)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_main_window.py -v`
Expected: 4 passed

- [ ] **Step 5: Manual smoke test — open the real window**

Run: `.venv/bin/python -m clasificador_video.app`
Expected: a window opens titled "Sin proyecto" with an empty room list and empty filmstrip, no traceback in the terminal. Close it manually.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py src/clasificador_video/app.py tests/ui/test_main_window.py
git commit -m "feat: ventana principal, integra cuartos + filmstrip + teclado"
```

---

## What this plan intentionally does not build yet

Per both specs' "fuera de alcance" sections: no video actually rendered inside the player widget yet (Task 9 gives you a working `MpvPlayer`, but embedding its video output inside a `QWidget` — the `mpv` render-API-to-Qt-surface wiring — is real, fiddly platform-specific work and deserves its own focused follow-up plan once this foundation is merged and Bruno has used the room/filmstrip/keyboard flow with fake data). Also not in this plan: the room config dialog → main window handoff (opening the real dialog on app start and feeding its `RoomSelection` into `MainWindow`), drag-and-drop onto the ingest panel (Task 6 only covers the "Importar carpetas" button path), the manifest export button, and the autosave wiring into `MainWindow`. Each is a small, focused next plan once this one is merged and working.
