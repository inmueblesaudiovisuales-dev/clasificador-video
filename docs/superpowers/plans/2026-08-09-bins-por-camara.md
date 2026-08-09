# Bins por cámara — plan de implementación

> **Para quien ejecute esto:** SUB-SKILL REQUERIDA: usar
> `superpowers:subagent-driven-development` (recomendado) o
> `superpowers:executing-plans` para implementar tarea por tarea. Los pasos
> llevan casilla (`- [ ]`) para irlos marcando.

**Meta:** que el material importado se agrupe por cámara/fuente en bins, que
cada bin tenga sus propios proxies enganchados a mano, y que agregar material
nuevo deje de reiniciar el proyecto.

**Arquitectura:** el bin es un dato nuevo que vive **fuera** de `Clip` —
`Clip.to_dict()` es el contrato con el plugin de Premiere y no se toca — en un
módulo propio (`bins.py`) que solo sabe de índices y nombres, sin Qt. La hoja
de contactos pasa de agrupar por un `str` (el cuarto) a agrupar por una tupla
`(bin, cuarto)`, con un encabezado de bin insertado antes del primer bloque de
cada uno. La importación deja de reconstruir la lista de clips y pasa a
agregar al final.

**Stack:** Python 3.12, PySide6, pytest + pytest-qt. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-08-09-bins-por-camara-design.md`
**Mockup acordado (propuesta A):**
`docs/superpowers/mockups/bins-2026-08-09/mockup.html`

**Suite completa:**
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Tiene que quedar verde al final de cada tarea. Hoy son 831 tests en ~11 s.

---

## Orden de las fases y por qué

1. **Fase 1 — el dato.** `bins.py` puro, sin UI y sin Qt. Es lo que todo lo
   demás usa.
2. **Fase 2 — agregar sin reiniciar.** Arregla el bug que Bruno reportó (se
   caen las portadas al importar una segunda carpeta) y es requisito de los
   bins: sin esto, cada carpeta nueva borra los proxies de la anterior.
3. **Fase 3 — proxies por bin.** El punto delicado del spec.
4. **Fase 4 — la hoja con secciones.** Lo que se ve.
5. **Fase 5 — arrastrar.**
6. **Fase 6 — filtro por bin y nombre del bin en modo clip.**

Las fases 1 a 3 no cambian un pixel: al terminarlas la app se ve igual y
funciona mejor. Eso es a propósito — si algo se rompe, se rompe con la suite,
no con la vista.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `src/clasificador_video/bins.py` **(nuevo)** | El dato: qué clips tiene cada bin, en qué orden van los bins, renombrar, quitar. Sin Qt, sin rutas de disco más allá de `Path`. |
| `tests/test_bins.py` **(nuevo)** | Tests de lo anterior. |
| `src/clasificador_video/ingest.py` | Gana `archivos_de_video(rutas)`: de una mezcla de carpetas y archivos, saca la lista de videos. Hoy esa lógica está enterrada en `import_folders`. |
| `src/clasificador_video/ui/clip_sheet.py` | Agrupar por `(bin, cuarto)`, encabezado de bin, colapsar, renombrar, agregar tarjetas sin recrear las que ya están. |
| `src/clasificador_video/ui/main_window.py` | Pegarlo todo: agregar clips, proxies por bin, autosave, arrastre. |
| `src/clasificador_video/filters.py` | Un filtro más: `bin`. |
| `src/clasificador_video/app.py` | Restaurar `bins` de una sesión guardada, con retrocompatibilidad. |
| `src/clasificador_video/ui/theme.py` | El QSS del encabezado de bin. |

---

# FASE 1 — El dato

### Tarea 1: `BinTree`, lo mínimo

**Archivos:**
- Crear: `src/clasificador_video/bins.py`
- Test: `tests/test_bins.py`

- [x] **Paso 1: escribir el test que falla**

```python
# tests/test_bins.py
from pathlib import Path

import pytest

from clasificador_video.bins import BinTree


def test_un_bin_nuevo_queda_al_final_con_sus_clips():
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0, 1, 2])
    arbol.agregar("Dron", Path("/dron"), [3, 4])

    assert arbol.nombres() == ["Sony FX30", "Dron"]
    assert arbol.clips_de("Dron") == [3, 4]


def test_el_bin_de_un_clip():
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0, 1])
    arbol.agregar("Dron", Path("/dron"), [2])

    assert arbol.bin_de(1) == "Sony FX30"
    assert arbol.bin_de(2) == "Dron"
    assert arbol.bin_de(99) is None


def test_dos_bins_no_pueden_llamarse_igual():
    """Dos con el mismo nombre serian dos encabezados identicos en la hoja
    y un menu de clic derecho que no se sabe a cual aplica."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/a"), [0])
    arbol.agregar("Dron", Path("/b"), [1])

    assert arbol.nombres() == ["Dron", "Dron 2"]
```

- [x] **Paso 2: correrlo y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
```
Esperado: `ModuleNotFoundError: No module named 'clasificador_video.bins'`

- [x] **Paso 3: la implementación mínima**

```python
# src/clasificador_video/bins.py
"""Los bins: de que camara/tarjeta salio cada clip.

Vive APARTE de `Clip` a proposito. `Clip.to_dict()` es el contrato con el
plugin de Premiere y no se toca -- mismo criterio que ya se uso con los
tamaños, las duraciones y las rotaciones, que viajan al lado en el autosave
en vez de meterse dentro del clip.

Este modulo solo conoce indices de clip y nombres. No sabe de Qt, no lee
disco y no decide como se ve nada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Bin:
    nombre: str
    origen: Path
    clips: list[int] = field(default_factory=list)


class BinTree:
    def __init__(self) -> None:
        self._bins: list[Bin] = []

    def agregar(self, nombre: str, origen: Path, clips: list[int]) -> str:
        """Devuelve el nombre con el que quedo, que puede no ser el pedido."""
        nombre = self._nombre_libre(nombre.strip() or origen.name)
        self._bins.append(Bin(nombre=nombre, origen=origen, clips=list(clips)))
        return nombre

    def _nombre_libre(self, nombre: str) -> str:
        usados = self.nombres()
        if nombre not in usados:
            return nombre
        n = 2
        while f"{nombre} {n}" in usados:
            n += 1
        return f"{nombre} {n}"

    def nombres(self) -> list[str]:
        return [b.nombre for b in self._bins]

    def clips_de(self, nombre: str) -> list[int]:
        for b in self._bins:
            if b.nombre == nombre:
                return list(b.clips)
        return []

    def bin_de(self, indice: int) -> str | None:
        for b in self._bins:
            if indice in b.clips:
                return b.nombre
        return None
```

- [x] **Paso 4: correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
```
Esperado: 3 passed

- [x] **Paso 5: commit**

```bash
git add src/clasificador_video/bins.py tests/test_bins.py
git commit -m "feat: el dato del bin, sin interfaz todavia

De que camara salio cada clip. Vive aparte de Clip porque to_dict() es
el contrato con el plugin de Premiere y no se toca.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 2: renombrar, quitar y sumar clips a un bin existente

**Archivos:**
- Modificar: `src/clasificador_video/bins.py`
- Test: `tests/test_bins.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
def test_renombrar_conserva_la_posicion():
    """La posicion es el orden en la hoja: renombrar no puede moverlo."""
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0])
    arbol.agregar("Dron", Path("/dron"), [1])

    arbol.renombrar("Sony FX30", "Sony A")

    assert arbol.nombres() == ["Sony A", "Dron"]
    assert arbol.clips_de("Sony A") == [0]


def test_renombrar_a_uno_que_ya_existe_no_hace_nada():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/a"), [0])
    arbol.agregar("Sony", Path("/b"), [1])

    arbol.renombrar("Sony", "Dron")

    assert arbol.nombres() == ["Dron", "Sony"]


def test_sumar_clips_a_un_bin_que_ya_existe():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])

    arbol.sumar("Dron", [2, 3])

    assert arbol.clips_de("Dron") == [0, 1, 2, 3]


def test_quitar_un_bin_devuelve_los_indices_que_se_van():
    """Quien llama tiene que borrar esos clips de la lista y de todo lo que
    va indexado por clip. Si no los devolviera, habria que adivinarlos."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2])

    assert arbol.quitar("Dron") == [0, 1]
    assert arbol.nombres() == ["Sony"]


def test_reindexar_despues_de_quitar_clips():
    """Al borrar los clips 0 y 1, el que era 2 pasa a ser 0. Los bins van
    por INDICE, asi que si no se recorren quedan apuntando a otro clip."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2, 3])

    arbol.reindexar_tras_quitar([0, 1])

    assert arbol.clips_de("Sony") == [0, 1]
```

- [x] **Paso 2: correrlos y ver que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
```
Esperado: 5 failed con `AttributeError: 'BinTree' object has no attribute 'renombrar'`

- [x] **Paso 3: implementar**

```python
    def renombrar(self, nombre: str, nuevo: str) -> None:
        """Cambia el nombre SIN cambiar la posicion.

        Un nombre repetido se ignora en silencio, con el mismo criterio que
        `RoomSelection.rename`: es una entrada invalida del usuario, no un
        error del programa.
        """
        nuevo = nuevo.strip()
        if not nuevo or nuevo in self.nombres():
            return
        for b in self._bins:
            if b.nombre == nombre:
                b.nombre = nuevo
                return

    def sumar(self, nombre: str, clips: list[int]) -> None:
        for b in self._bins:
            if b.nombre == nombre:
                ya = set(b.clips)
                b.clips.extend(i for i in clips if i not in ya)
                return

    def quitar(self, nombre: str) -> list[int]:
        for i, b in enumerate(self._bins):
            if b.nombre == nombre:
                return self._bins.pop(i).clips
        return []

    def reindexar_tras_quitar(self, quitados: list[int]) -> None:
        fuera = set(quitados)
        for b in self._bins:
            b.clips = [
                i - sum(1 for q in fuera if q < i)
                for i in b.clips
                if i not in fuera
            ]
```

- [x] **Paso 4: correr y ver que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
```
Esperado: 8 passed

- [x] **Paso 5: commit**

```bash
git add src/clasificador_video/bins.py tests/test_bins.py
git commit -m "feat: renombrar, quitar y sumar clips a un bin

Lo mas facil de romper aqui es reindexar: los bins van por indice de
clip, asi que quitar un bin corre los indices de todos los demas.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 3: guardar y restaurar los bins en la sesión

**Archivos:**
- Modificar: `src/clasificador_video/bins.py`
- Modificar: `src/clasificador_video/ui/main_window.py` (`_write_autosave_now`, ~1155-1175)
- Modificar: `src/clasificador_video/app.py` (`_restore_session`, ~66)
- Test: `tests/test_bins.py`, `tests/test_app.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
# tests/test_bins.py
def test_ida_y_vuelta_a_json():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2])

    otro = BinTree.from_list(arbol.to_list())

    assert otro.nombres() == ["Dron", "Sony"]
    assert otro.clips_de("Dron") == [0, 1]
    assert otro.clips_de("Sony") == [2]


def test_una_sesion_vieja_sin_bins_cae_en_uno_solo():
    """Nadie pierde una sesion por actualizar la app. Sin la llave `bins`,
    todo el material queda en un bin unico con la carpeta del primer clip.
    """
    arbol = BinTree.desde_sesion(
        None, rutas=[Path("/material/A.MP4"), Path("/material/B.MP4")]
    )

    assert arbol.nombres() == ["material"]
    assert arbol.clips_de("material") == [0, 1]


def test_una_sesion_vieja_sin_clips_no_inventa_un_bin():
    assert BinTree.desde_sesion(None, rutas=[]).nombres() == []
```

- [x] **Paso 2: correrlos y ver que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
```
Esperado: 3 failed con `AttributeError: type object 'BinTree' has no attribute 'from_list'`

- [x] **Paso 3: implementar en `bins.py`**

```python
    def to_list(self) -> list[dict]:
        return [
            {"nombre": b.nombre, "origen": str(b.origen), "clips": list(b.clips)}
            for b in self._bins
        ]

    @classmethod
    def from_list(cls, datos: list[dict]) -> "BinTree":
        arbol = cls()
        for d in datos or []:
            arbol._bins.append(
                Bin(
                    nombre=str(d.get("nombre") or ""),
                    origen=Path(str(d.get("origen") or "")),
                    clips=[int(i) for i in d.get("clips") or []],
                )
            )
        return arbol

    @classmethod
    def desde_sesion(cls, datos: list[dict] | None, rutas: list[Path]) -> "BinTree":
        """Lo que se usa al restaurar: si la sesion no traia bins --porque es
        de antes de que existieran-- todo el material entra en uno solo,
        nombrado con la carpeta del primer clip."""
        if datos:
            return cls.from_list(datos)
        arbol = cls()
        if rutas:
            arbol.agregar(rutas[0].parent.name, rutas[0].parent,
                          list(range(len(rutas))))
        return arbol
```

- [x] **Paso 4: correr y ver que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
```
Esperado: 11 passed

- [x] **Paso 5: escribir el test de que la ventana lo guarda**

```python
# tests/ui/test_main_window_bins.py  (archivo nuevo)
import json
from pathlib import Path

from clasificador_video.manifest import Clip


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


def test_el_autosave_escribe_los_bins(qtbot, tmp_path, ventana):
    ventana.session_path = tmp_path / "sesion.json"
    ventana.load_clips([_clip(0, "/dron/A.MP4"), _clip(1, "/dron/B.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0, 1])

    ventana._write_autosave_now()

    data = json.loads((tmp_path / "sesion.json").read_text())
    assert data["bins"] == [
        {"nombre": "Dron", "origen": "/dron", "clips": [0, 1]}
    ]
```

> **Nota para quien ejecute:** la fixture `ventana` tiene que construir una
> `MainWindow` con `probe_clip` inyectado, como ya lo hacen los tests de
> `tests/ui/`. Copiar el patrón del archivo de tests de main_window que ya
> exista; no inventar una fixture nueva si ya hay una equivalente.

- [x] **Paso 6: correr y ver que falla**

Esperado: `AttributeError: 'MainWindow' object has no attribute 'bins'`

- [x] **Paso 7: implementar en `main_window.py`**

En `__init__`, junto a `self.ingest_tree = IngestTree()`:

```python
        self.bins = BinTree()
```

Y en `_write_autosave_now`, dentro del `data = {...}`, después de
`"rotaciones"`:

```python
            # los bins van aparte de los clips por la misma razon que los
            # tamaños: `Clip.to_dict()` es el contrato con el plugin de
            # Premiere y no se toca.
            "bins": self.bins.to_list(),
```

- [x] **Paso 8: implementar el restaurado en `app.py`**

En `_restore_session`, después de cargar los clips:

```python
    window.bins = BinTree.desde_sesion(
        data.get("bins"), rutas=[c.ruta for c in window.clips]
    )
```

- [x] **Paso 9: correr la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Esperado: todo verde, sin tests nuevos rotos.

- [x] **Paso 10: commit**

```bash
git add -A
git commit -m "feat: los bins sobreviven a cerrar y abrir la app

Van al lado de los clips en el autosave, no adentro. Una sesion vieja
sin la llave se carga en un bin unico en vez de perderse.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# FASE 2 — Agregar material sin reiniciar el proyecto

> Esta fase arregla el bug que Bruno reportó: **al importar una segunda
> carpeta se caen las portadas.** La causa está en tres saltos:
> `_on_import_folders` → `_load_clips_from_ingest` → `load_clips`, y
> `load_clips` limpia historial y proxies y llama a
> `_refresh_sheet(force_rebuild=True)`, que hace `ClipSheet.set_clips` y
> **destruye todas las tarjetas**, con sus miniaturas ya cargadas.

### Tarea 4: `ClipSheet.append_clips` — agregar tarjetas sin recrear las que ya están

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (`update_clips`, ~985)
- Test: `tests/ui/test_clip_sheet.py`

- [x] **Paso 1: escribir el test que falla**

```python
def test_agregar_clips_no_recrea_las_tarjetas_de_antes(qtbot):
    """La miniatura ya cargada vive en el widget. Si la tarjeta se recrea,
    la portada se pierde -- que es exactamente lo que Bruno vio al importar
    una segunda carpeta.
    """
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0), _thumb(1)])
    antes = list(hoja.item_widgets)

    hoja.append_clips([_thumb(0), _thumb(1), _thumb(2)])

    assert hoja.item_widgets[0] is antes[0]
    assert hoja.item_widgets[1] is antes[1]
    assert hoja.count() == 3
```

> `_thumb(i)` es el ayudante que ya usan los tests de este archivo para
> construir un `ClipThumbnail`. Reusarlo, no escribir otro.

- [x] **Paso 2: correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet.py -q
```
Esperado: `AttributeError: 'ClipSheet' object has no attribute 'append_clips'`

- [x] **Paso 3: implementar**

```python
    def append_clips(self, clips: list[ClipThumbnail]) -> None:
        """Como `update_clips`, pero cuando la lista CRECIO.

        `update_clips` cae en `set_clips` si cambia el largo, y `set_clips`
        destruye todas las tarjetas -- con sus miniaturas. Agregar material
        no puede costar las portadas de lo que ya estaba.
        """
        viejas = len(self.item_widgets)
        if len(clips) < viejas:
            self.set_clips(clips)
            return
        for card, clip in zip(self.item_widgets, clips):
            card.update_content(clip)
        for index in range(viejas, len(clips)):
            card = ClipCard(clips[index])
            card.clicked.connect(lambda mods, i=index: self._on_card_clicked(i, mods))
            card.doble_click.connect(lambda i=index: self.clip_activated.emit(i))
            self.item_widgets.append(card)
        # el filtro guarda indices y ya no cubre a los nuevos
        self._visible = None
        self._firma = None
        self._regroup()
        self.title_label.setText(f"CLIPS · {len(clips)}")
        self._redraw()
```

- [x] **Paso 4: correr y ver que pasa**

Esperado: PASS

- [x] **Paso 5: commit**

```bash
git add src/clasificador_video/ui/clip_sheet.py tests/ui/test_clip_sheet.py
git commit -m "feat: la hoja sabe agregar tarjetas sin tirar las que ya tenia

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 5: `MainWindow.agregar_clips`

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py` (junto a `load_clips`, ~1119)
- Test: `tests/ui/test_main_window_bins.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
def test_agregar_clips_conserva_los_proxies_ya_enganchados(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)

    ventana.agregar_clips([_clip(1, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert ventana.clips[0].ruta_proxy == Path("/cam/AS03.MP4")
    assert ventana._proxy_sizes[0] == (1080, 1920)
    assert len(ventana.clips) == 2


def test_agregar_clips_conserva_el_historial(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.clasificar("Cocina")          # deja una entrada en el historial
    cuantas = len(ventana.history.entries())

    ventana.agregar_clips([_clip(1, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert len(ventana.history.entries()) == cuantas


def test_agregar_clips_crea_el_bin_con_los_indices_nuevos(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])

    ventana.agregar_clips([_clip(2, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert ventana.bins.nombres() == ["Sony", "Dron"]
    assert ventana.bins.clips_de("Dron") == [2]
```

> Comprobar el nombre real del método de clasificar y del historial antes de
> escribir el test (`ventana.clasificar` / `ventana.history.entries()`): si en
> el código se llaman de otro modo, usar los del código, no los de aquí.

- [x] **Paso 2: correr y ver que fallan**

Esperado: `AttributeError: 'MainWindow' object has no attribute 'agregar_clips'`

- [x] **Paso 3: implementar**

```python
    def agregar_clips(self, nuevos: list[Clip], nombre_de_bin: str,
                      origen: Path) -> None:
        """Suma material SIN reiniciar el proyecto.

        `load_clips` es para material nuevo y por eso limpia todo: historial,
        proxies, tarjetas. Usarla para agregar es lo que hacia que al
        importar una segunda carpeta se cayeran las portadas ya generadas y
        los proxies ya enganchados.

        Aqui los indices de lo que ya estaba NO se mueven, y por eso todo lo
        que va indexado por clip --`_proxy_sizes`, `_clip_durations`,
        `_clip_sizes`, el historial-- sigue siendo valido sin tocarlo.
        """
        if not nuevos:
            return
        primero = len(self.clips)
        for offset, clip in enumerate(nuevos):
            clip.orden = primero + offset + 1
            self.clips.append(clip)
        if nombre_de_bin in self.bins.nombres():
            self.bins.sumar(nombre_de_bin, list(range(primero, len(self.clips))))
        else:
            self.bins.agregar(nombre_de_bin, origen,
                              list(range(primero, len(self.clips))))
        self._refresh_sheet()
        self._schedule_thumbnails()
        self._autosave()
```

- [x] **Paso 4: hacer que `_refresh_sheet` use `append_clips` cuando creció**

En `_refresh_sheet`, donde hoy dice:

```python
        if force_rebuild:
            self.clip_sheet.set_clips(thumbs)
        else:
            self.clip_sheet.update_clips(thumbs)
```

pasa a:

```python
        if force_rebuild:
            self.clip_sheet.set_clips(thumbs)
        elif len(thumbs) > self.clip_sheet.count():
            # crecio: agregar sin destruir las tarjetas que ya tienen portada
            self.clip_sheet.append_clips(thumbs)
        else:
            # actualiza en el lugar: eso es lo que preserva las miniaturas ya
            # cargadas por los _ThumbnailJob al navegar o clasificar.
            self.clip_sheet.update_clips(thumbs)
```

- [x] **Paso 5: correr los tests**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q
```
Esperado: PASS

- [x] **Paso 6: cambiar la importación para que agregue**

`_on_import_folders` (~1899) pasa a:

```python
    def _on_import_folders(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta de material")
        if not folder:
            return
        carpeta = Path(folder)
        self.status_bar.set_volume(folder, _gigas_del_volumen(carpeta))
        self.importar_rutas([carpeta])
```

Y se agrega el método que usarán también el arrastre (Fase 5) y los tests:

```python
    def importar_rutas(self, rutas: list[Path], nombre_de_bin: str | None = None,
                       origen: Path | None = None) -> None:
        """El unico camino de entrada de material.

        Sirve al boton de importar y al arrastre. Si no se dice a que bin
        van, se crea uno con el nombre de la carpeta de donde vienen.
        """
        archivos = archivos_de_video(rutas)
        ya_estan = {c.ruta for c in self.clips}
        archivos = [a for a in archivos if a not in ya_estan]
        if not archivos:
            return
        carpeta = origen or archivos[0].parent
        nuevos, medidas = self._medir(archivos, desde=len(self.clips))
        if not nuevos:
            self._avisar_que_no_se_pudo_leer_nada()
            return
        self._clip_durations.update(medidas["duraciones"])
        self._clip_sizes.update(medidas["tamanos"])
        self._clip_rotations.update(medidas["rotaciones"])
        self.agregar_clips(nuevos, nombre_de_bin or carpeta.name, carpeta)
```

> **Refactor necesario:** hoy la medición con `ffprobe` está incrustada en
> `_load_clips_from_ingest` (~1178-1215). Sacarla a `_medir(archivos, desde)`
> que devuelve `(clips, {"duraciones": …, "tamanos": …, "rotaciones": …})` con
> los índices ya corridos por `desde`, y que `_load_clips_from_ingest` la use
> también. El aviso de «no se pudo leer ninguno» que ya existe ahí se vuelve
> `_avisar_que_no_se_pudo_leer_nada()`. **No duplicar la lógica en dos
> lugares.**

- [x] **Paso 7: `archivos_de_video` en `ingest.py`**

Test primero:

```python
# tests/test_ingest.py
def test_archivos_de_video_acepta_carpetas_y_sueltos_mezclados(tmp_path):
    carpeta = tmp_path / "cam"
    carpeta.mkdir()
    (carpeta / "A.MP4").touch()
    (carpeta / "AS03.MP4").touch()      # proxy de camara: NO es material
    (carpeta / "notas.txt").touch()
    suelto = tmp_path / "B.MOV"
    suelto.touch()

    assert archivos_de_video([carpeta, suelto]) == [carpeta / "A.MP4", suelto]


def test_archivos_de_video_no_repite(tmp_path):
    (tmp_path / "A.MP4").touch()

    assert archivos_de_video([tmp_path, tmp_path / "A.MP4"]) == [tmp_path / "A.MP4"]
```

Implementación:

```python
def archivos_de_video(rutas: list[Path]) -> list[Path]:
    """De una mezcla de carpetas y archivos, los videos que son material.

    De una carpeta se toman sus archivos directos, sin bajar a las
    subcarpetas -- mismo criterio que `IngestTree.import_folders`, para que
    arrastrar una tarjeta no traiga tambien las carpetas de sistema de la
    camara.
    """
    encontrados: list[Path] = []
    for ruta in rutas:
        candidatos = sorted(p for p in ruta.iterdir() if p.is_file()) \
            if ruta.is_dir() else [ruta]
        for p in candidatos:
            if (p.suffix.lower() in VIDEO_EXTENSIONS
                    and not es_archivo_de_proxy(p)
                    and p not in encontrados):
                encontrados.append(p)
    return encontrados
```

- [x] **Paso 8: correr la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Esperado: todo verde.

- [x] **Paso 9: commit**

```bash
git add -A
git commit -m "fix: importar una segunda carpeta ya no tira las portadas

Bruno lo reporto usando la app con sus 109 clips. La causa eran tres
saltos: importar reconstruia la lista entera y load_clips limpia el
historial, vacia los proxies y recrea todas las tarjetas -- con sus
miniaturas ya cargadas adentro.

Ahora agregar agrega: los indices de lo que ya estaba no se mueven, asi
que todo lo que va indexado por clip sigue valiendo.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# FASE 3 — Proxies por bin

> **El punto delicado del spec.** Hoy `_sondear_proxies` (~1279) empieza con
> `self._proxy_sizes = {}` y reconstruye `_proxy_candidatos` entero. Si eso se
> deja igual al volverse por-bin, **enganchar los proxies del dron borra los
> de la Sony**. Bruno pidió explícitamente cuidado aquí.

### Tarea 6: `_sondear_proxies` solo toca los índices de su bin

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py` (~1279-1305)
- Test: `tests/ui/test_main_window_bins.py`

- [x] **Paso 1: escribir el test que falla — ESTE es el test que importa**

```python
def test_enganchar_los_proxies_de_un_bin_no_borra_los_del_otro(qtbot, ventana):
    """El bug que este plan existe para no cometer.

    `_sondear_proxies` arrancaba con `_proxy_sizes = {}`. Al volverse por
    bin, eso borraria los proxies de la camara que no estas tocando.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)

    ventana._sondear_proxies({Path("/dron/D.MP4"): Path("/dron/DPROXY.MP4")},
                             indices=[1])

    assert ventana.clips[0].ruta_proxy == Path("/cam/AS03.MP4")
    assert ventana._proxy_sizes[0] == (1080, 1920)


def test_volver_a_enganchar_el_mismo_bin_si_limpia_lo_suyo(qtbot, ventana):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana.clips[0].ruta_proxy = Path("/dron/VIEJO.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)

    ventana._sondear_proxies({Path("/dron/D.MP4"): None}, indices=[0])

    assert ventana.clips[0].ruta_proxy is None
    assert 0 not in ventana._proxy_sizes
```

- [x] **Paso 2: correr y ver que fallan**

Esperado: `TypeError: _sondear_proxies() got an unexpected keyword argument 'indices'`

- [x] **Paso 3: implementar**

```python
    def _sondear_proxies(self, emparejados: dict[Path, Path | None],
                         indices: list[int] | None = None) -> None:
        """Manda a comprobar cada proxy en segundo plano.

        Emparejar es barato (mirar nombres); validar cuesta un `ffprobe`
        por archivo --26.7 ms, o sea 3.4 s en 128 clips-- y eso no puede
        bloquear la ventana.

        `indices` acota a los clips de UN bin. Y acotar significa acotar
        tambien lo que se limpia: esta funcion arrancaba con
        `self._proxy_sizes = {}`, y dejarlo asi haria que enganchar los
        proxies del dron borrara los de la Sony.
        """
        alcance = list(range(len(self.clips))) if indices is None else list(indices)
        for i in alcance:
            self._proxy_sizes.pop(i, None)
            self._proxy_candidatos.pop(i, None)
            self.clips[i].ruta_proxy = None
        self._proxy_generation += 1
        generation = self._proxy_generation
        nuevos = {
            i: emparejados[self.clips[i].ruta]
            for i in alcance
            if emparejados.get(self.clips[i].ruta) is not None
        }
        self._proxy_candidatos.update(nuevos)
        for index, proxy in nuevos.items():
            job = _ProxyProbeJob(generation, index, proxy, self._probe_clip)
            job.signals.done.connect(self._on_proxy_sondeado)
            self._thread_pool.start(job)
        # y las miniaturas que falten se vuelven a pedir, ahora desde el
        # proxy: es 5.6 veces mas barato (medido con el material real, 5.90 s
        # contra 1.06 s por clip). Las que ya estan en cache no se rehacen.
        self._schedule_thumbnails()
```

- [x] **Paso 4: arreglar la invalidación por generación**

`_proxy_generation` es global: subirla descarta los trabajos en vuelo **del
otro bin**, y esos resultados se perderían. Cambiar la guarda de
`_on_proxy_sondeado` para que además compruebe que el candidato sigue siendo
el mismo:

```python
    def _on_proxy_sondeado(self, generation: int, index: int, info: dict | None) -> None:
        proxy = self._proxy_candidatos.get(index)
        if proxy is None or index >= len(self.clips):
            return
        if generation != self._proxy_generation and self._proxy_candidatos.get(index) is not proxy:
            return  # resultado de una tanda ya descartada
        if not info or not self._el_proxy_calza(index, info):
            return
        self.clips[index].ruta_proxy = proxy
        ...
```

> **Comprobar esto con un test**, no de vista: un trabajo del bin A que llega
> después de haber lanzado el bin B tiene que seguir contando.

- [x] **Paso 5: correr y ver que pasan**

Esperado: PASS

- [x] **Paso 6: commit**

```bash
git add -A
git commit -m "fix: enganchar proxies de un bin ya no borra los del otro

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 7: `adjuntar_proxies(bin)` — el flujo por bin

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py` (~1231-1277)
- Test: `tests/ui/test_main_window_bins.py`

- [x] **Paso 1: escribir el test que falla**

```python
def test_el_patron_se_busca_solo_entre_los_clips_del_bin(qtbot, ventana, monkeypatch):
    """La Sony nombra sus proxies con S03 y el dron con otra cosa. Con un
    solo patron para todo el proyecto, una de las dos se queda sin proxy.
    """
    ventana.load_clips([_clip(0, "/cam/C0001.MP4"), _clip(1, "/dron/DJI_0001.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    vistos = {}
    monkeypatch.setattr(ventana, "_sondear_proxies",
                        lambda emp, indices=None: vistos.update(emp=emp, idx=indices))

    ventana.adjuntar_proxies_de_bin(
        "Dron", elegido=Path("/dron/proxies/DJI_0001_proxy.MP4")
    )

    assert vistos["idx"] == [1]
    assert Path("/cam/C0001.MP4") not in vistos["emp"]
```

- [x] **Paso 2: correr y ver que falla**

Esperado: `AttributeError: … has no attribute 'adjuntar_proxies_de_bin'`

- [x] **Paso 3: implementar**

Partir `adjuntar_proxies` en dos: la parte que pide el archivo (con
`QFileDialog`, no testeable) y la que hace el trabajo (testeable, recibe
`elegido`).

```python
    def adjuntar_proxies_de_bin(self, nombre_de_bin: str,
                                elegido: Path | None = None) -> None:
        """El «Enlazar proxies…» del menu del bin.

        Eliges el proxy de UN clip de ESE bin y del par sale el patron de
        nombre para los demas del MISMO bin. Es a mano y solo a mano, por
        pedido de Bruno.

        Por bin y no por proyecto porque cada camara nombra distinto: la
        Sony escribe `C0001S03.MP4` junto a `C0001.MP4`, y los del dron se
        generan con el nombre que elijamos. Con un solo patron, una de las
        dos camaras se quedaba siempre sin proxy.
        """
        indices = self.bins.clips_de(nombre_de_bin)
        if not indices:
            return
        referencia = self.clips[indices[0]]
        if elegido is None:
            ruta, _ = QFileDialog.getOpenFileName(
                self,
                f"Elige el proxy de {referencia.ruta.name}",
                str(referencia.ruta.parent),
                "Video (*.mp4 *.MP4 *.mov *.MOV *.mxf *.MXF)",
            )
            if not ruta:
                return
            elegido = Path(ruta)
        patron = patron_de_proxy(referencia.ruta, elegido)
        if patron is None:
            QMessageBox.warning(
                self, "Ese archivo no corresponde",
                f"«{elegido.name}» no lleva el nombre de «{referencia.ruta.name}» "
                "adentro, así que no se puede deducir cómo se llaman los demás "
                "proxies.\n\nElige el proxy que corresponde a ESE clip.",
            )
            return
        prefijo, sufijo = patron
        emparejados = emparejar_con_patron(
            [self.clips[i].ruta for i in indices],
            elegido.parent, prefijo, sufijo, elegido.suffix,
        )
        self._sondear_proxies(emparejados, indices=indices)
```

> El `QMessageBox.information` con «se encontraron N de M» que hoy sale antes
> de sondear se conserva, contando contra `len(indices)` y no contra
> `len(self.clips)`.

- [x] **Paso 4: `quitar_proxies_de_bin`**

```python
    def quitar_proxies_de_bin(self, nombre_de_bin: str) -> None:
        indices = self.bins.clips_de(nombre_de_bin)
        self._sondear_proxies({}, indices=indices)
```

Con su test: los del bin quedan sin proxy, los del otro bin no se tocan.

- [x] **Paso 5: el botón «Proxies» de la barra de título**

Ya no tiene sentido como acción global. Pasa a operar sobre **el bin del clip
actual**:

```python
    def adjuntar_proxies(self) -> None:
        """El boton «Proxies» de la barra: aplica al bin del clip actual."""
        nombre = self.bins.bin_de(self.current_index)
        if nombre is None:
            QMessageBox.warning(self, "Sin material",
                                "Primero importa los clips y luego engancha sus proxies.")
            return
        self.adjuntar_proxies_de_bin(nombre)
```

- [x] **Paso 6: correr la suite completa**

Esperado: todo verde. **Los tests viejos de `adjuntar_proxies` van a fallar**
porque cambió el alcance — ajustarlos para que creen un bin primero, y dejar
en cada uno un comentario de por qué se tocó.

- [x] **Paso 7: commit**

```bash
git add -A
git commit -m "feat: enlazar proxies por bin, con su propio patron de nombre

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# FASE 4 — La hoja con secciones (propuesta A)

### Tarea 8: agrupar por `(bin, cuarto)`

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (`ClipThumbnail` ~60,
  `_group_of` ~1019, `_regroup` ~1030, `_acomodar_de_verdad` ~1264)
- Test: `tests/ui/test_clip_sheet.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
def test_los_bins_van_en_orden_de_importacion_y_los_cuartos_adentro(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Dron", room_label="Exteriores"),
        _thumb(1, bin_nombre="Sony", room_label="Cocina"),
        _thumb(2, bin_nombre="Sony", room_label="Sin clasificar"),
    ])

    assert hoja.group_titles() == [
        ("Sony", "Sin clasificar"), ("Sony", "Cocina"), ("Dron", "Exteriores"),
    ]


def test_un_clip_sin_bin_cae_en_uno_solo_y_no_revienta(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_clips([_thumb(0, room_label="Cocina")])

    assert hoja.group_titles() == [("", "Cocina")]
```

- [x] **Paso 2: correr y ver que fallan**

- [x] **Paso 3: implementar**

`ClipThumbnail` gana un campo:

```python
    bin_nombre: str = ""
```

`ClipSheet` gana el orden de los bins y la clave compuesta:

```python
    def set_bin_order(self, nombres: list[str]) -> None:
        """El orden de los bins es el de importacion, no alfabetico: es el
        orden en que Bruno metio el material y por el que se mueven las
        flechas."""
        self._bin_order = list(nombres)
        self._firma = None
        self._regroup()

    def _group_of(self, clip: ClipThumbnail) -> tuple[str, str]:
        return (clip.bin_nombre, clip.room_label or SIN_CLASIFICAR)
```

Y `_regroup` ordena por (posición del bin, cuarto con «Sin clasificar»
primero):

```python
        def orden(clave: tuple[str, str]) -> tuple:
            bin_nombre, cuarto = clave
            pos = (self._bin_order.index(bin_nombre)
                   if bin_nombre in self._bin_order else len(self._bin_order))
            return (pos, bin_nombre, cuarto != SIN_CLASIFICAR, cuarto)

        titulos.sort(key=orden)
```

`_GroupBlock.__init__` recibe la tupla y muestra solo el cuarto:

```python
    def __init__(self, clave: tuple[str, str], parent=None):
        super().__init__(parent)
        self.titulo = clave
        self.bin_nombre, self.cuarto = clave
        ...
        self.title_label = ElidedLabel(self.cuarto.upper())
```

> `group_titles()` ahora devuelve tuplas. **Buscar todos sus usos en los tests
> y arreglarlos**; es el cambio con más radio de impacto de la fase.

- [x] **Paso 4: correr la suite completa y arreglar lo que caiga**

- [x] **Paso 5: commit**

```bash
git add -A
git commit -m "feat: la hoja agrupa por bin y, dentro, por cuarto

La propuesta A del mockup: el bin manda arriba y el cuarto baja a
subgrupo. Bruno la eligio viendo las dos dibujadas.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 9: el encabezado del bin

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (widget nuevo `_BinHeader`)
- Modificar: `src/clasificador_video/ui/theme.py` (QSS)
- Test: `tests/ui/test_clip_sheet.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
def test_hay_un_encabezado_por_bin_arriba_de_su_primer_grupo(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony", "Dron"])
    hoja.set_clips([
        _thumb(0, bin_nombre="Sony", room_label="Cocina"),
        _thumb(1, bin_nombre="Sony", room_label="Baño"),
        _thumb(2, bin_nombre="Dron", room_label="Exteriores"),
    ])

    assert hoja.bin_headers() == ["Sony", "Dron"]
    assert hoja.bin_headers()[0] == "Sony"


def test_el_encabezado_dice_cuantos_clips_tiene_su_bin(qtbot):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony"), _thumb(1, bin_nombre="Sony")])

    assert "2" in hoja.bin_header_widget("Sony").count_label.text()


def test_colapsar_esconde_las_tarjetas_pero_no_las_saca_de_la_cola(qtbot):
    """Colapsar es visual. Si sacara los clips de la cola seria un filtro
    escondido, y la flecha se saltaria clips sin decir por que."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Sony"])
    hoja.set_clips([_thumb(0, bin_nombre="Sony")])

    hoja.set_bin_collapsed("Sony", True)

    assert hoja.item_widgets[0].isHidden()
    assert hoja.count() == 1
```

- [x] **Paso 2: correr y ver que fallan**

- [x] **Paso 3: implementar `_BinHeader`**

```python
class _BinHeader(QWidget):
    """El encabezado de un bin: lo que el mockup pone arriba de sus grupos.

    Es tambien el menu de clic derecho -- ahi vive todo lo que aplica a una
    camara entera (enlazar proxies, renombrar, quitar).
    """

    collapse_toggled = Signal(str)      # nombre del bin
    rename_requested = Signal(str, str)  # nombre viejo, nombre nuevo
    proxies_requested = Signal(str)
    proxies_cleared = Signal(str)
    select_all_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, nombre: str, parent=None):
        super().__init__(parent)
        self.nombre = nombre
        self.setObjectName("binHeader")
        self.setAttribute(Qt.WA_StyledBackground, True)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(9, 9, 9, 9)
        fila.setSpacing(9)
        self.chevron = QLabel("▾")
        self.chevron.setObjectName("binChevron")
        self.name_label = QLabel(nombre)
        self.name_label.setObjectName("binName")
        self.source_label = QLabel("")
        self.source_label.setObjectName("binSource")
        self.count_label = QLabel("0 clips")
        self.count_label.setObjectName("binCount")
        self.proxy_badge = QLabel("sin proxies")
        self.proxy_badge.setObjectName("binProxyBadge")
        for w in (self.chevron, self.name_label, self.source_label,
                  self.count_label):
            fila.addWidget(w)
        fila.addStretch(1)
        fila.addWidget(self.proxy_badge)
```

Con `mousePressEvent` que emite `collapse_toggled`, `contextMenuEvent` que
arma el `QMenu` del spec §4.2, y `mouseDoubleClickEvent` sobre `name_label`
que cambia a un `QLineEdit` **en el lugar** — no un `QInputDialog`, que es
modal y cuelga la suite bajo `offscreen`.

`_regroup` inserta un `_BinHeader` en `_content_layout` antes del primer
`_GroupBlock` de cada bin. `_ordered_blocks()` ya filtra por
`isinstance(..., _GroupBlock)`, así que sigue funcionando sin cambios.

- [x] **Paso 4: el QSS en `theme.py`**

```css
#binHeader { background: %(BG_SURFACE_1)s; border: 1px solid %(LINE)s;
             border-radius: %(RADIUS_LG)spx; }
#binName   { font-size: 12px; font-weight: 650; color: %(TEXT)s; }
#binSource { font-family: %(MONO_FONT)s; font-size: 9px; color: %(TEXT_3)s; }
#binCount  { font-family: %(MONO_FONT)s; font-size: 10px; color: %(TEXT_3)s; }
#binProxyBadge { font-family: %(MONO_FONT)s; font-size: 9px; padding: 2px 7px;
                 border-radius: %(RADIUS_SM)spx; border: 1px solid %(LINE)s;
                 background: %(BG_SURFACE_2)s; color: %(TEXT_3)s; }
```

> Seguir la forma exacta que ya usa `build_stylesheet` en ese archivo. Y
> recordar que los tests de UI aplican la hoja de estilo por la fixture de
> `tests/ui/conftest.py`: sin ella se mide una app que no existe.

- [x] **Paso 5: que se quede pegado arriba al hacer scroll**

Esto es nuevo — el `_GroupBlock` de cuarto que hay hoy **no** se pega, se va
con el scroll. Se hace con un solo encabezado flotante sobre el viewport, no
con uno por bin:

```python
    def _actualizar_encabezado_pegado(self) -> None:
        """UN encabezado flotante, no uno por bin.

        Es la misma idea de `batch_bar`, que ya flota sobre la hoja: se dibuja
        encima del viewport en vez de ocupar alto en el contenido. Con un
        widget pegado por bin habria N widgets peleando por la misma franja.
        """
        y = self._scroll.verticalScrollBar().value()
        arriba = None
        for nombre in self._bin_order:
            cabecera = self._bin_headers.get(nombre)
            if cabecera is not None and cabecera.y() <= y:
                arriba = nombre
        self._pegado.set_bin(arriba)      # None esconde el flotante
        self._pegado.setVisible(arriba is not None)
```

Conectado a `self._scroll.verticalScrollBar().valueChanged`.

Test: con dos bins y la hoja desplazada más allá del primer encabezado,
`hoja._pegado.nombre == "Sony"`; en el tope, el flotante está escondido.

> **Si esto sale caro o frágil dentro del `QScrollArea`, se entrega sin
> pegar** — el spec §4.1 lo marca como lo único de esa sección que puede
> caerse sin romper el diseño. Lo que NO se hace es entregarlo a medias y no
> decirlo.

- [x] **Paso 6: verificación visual — obligatoria**

```python
# script del scratchpad, NO del repo
hoja = ClipSheet(); hoja.set_bin_order(["Sony FX30", "Dron"]); ...
hoja.resize(1100, 700)
hoja.grab().save("/private/tmp/.../hoja-bins.png")
```

Abrir el PNG con la herramienta de lectura de archivos y **mirarlo**:
encabezado presente, nombre legible, insignia alineada a la derecha, un bin
colapsado que no deja hueco. Comparar contra la pantalla 1 del mockup. Si no
se miró la imagen, no se afirma que se ve bien.

- [x] **Paso 7: commit**

```bash
git add -A
git commit -m "feat: el encabezado del bin, con su menu de clic derecho

Verificado mirando el pixel: captura de la hoja con dos bins, uno
colapsado, comparada contra la pantalla 1 del mockup.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 10: conectar el menú del bin a la ventana

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_bins.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
def test_renombrar_un_bin_cambia_el_dato_y_la_hoja(qtbot, ventana):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])

    ventana._on_bin_renombrado("Dron", "Dron DJI")

    assert ventana.bins.nombres() == ["Dron DJI"]
    assert ventana.clip_sheet.bin_headers() == ["Dron DJI"]


def test_quitar_un_bin_corre_todo_lo_que_va_por_indice(qtbot, ventana):
    """El segundo lugar donde esto rompe en silencio.

    `_clip_durations`, `_clip_sizes`, `_clip_rotations` y `_proxy_sizes` van
    TODOS por indice de clip. Al quitar los clips 0 y 1, el que era 2 pasa a
    ser 0 -- y cualquiera de esos diccionarios que no se corra queda
    describiendo a otro clip, sin dar ningun sintoma hasta que un video se
    dibuja acostado o un rango cae corrido.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4"),
                        _clip(2, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.agregar("Dron", Path("/dron"), [2])
    ventana._clip_sizes = {0: (100, 200), 1: (100, 200), 2: (1920, 1080)}
    ventana._clip_durations = {0: 1.0, 1: 2.0, 2: 3.0}
    ventana._clip_rotations = {0: 0, 1: 0, 2: 90}
    ventana._proxy_sizes = {2: (640, 360)}

    ventana._on_bin_quitado("Sony")

    assert [c.ruta for c in ventana.clips] == [Path("/dron/D.MP4")]
    assert ventana.bins.clips_de("Dron") == [0]
    assert ventana._clip_sizes == {0: (1920, 1080)}
    assert ventana._clip_durations == {0: 3.0}
    assert ventana._clip_rotations == {0: 90}
    assert ventana._proxy_sizes == {0: (640, 360)}


def test_el_menu_de_proxies_llama_al_bin_que_se_toco(qtbot, ventana, monkeypatch):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    llamados = []
    monkeypatch.setattr(ventana, "adjuntar_proxies_de_bin", llamados.append)

    ventana.clip_sheet.bin_header_widget("Dron").proxies_requested.emit("Dron")

    assert llamados == ["Dron"]
```

- [x] **Paso 2: correr y ver que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q
```
Esperado: `AttributeError: … has no attribute '_on_bin_renombrado'`

- [x] **Paso 3: implementar**

```python
    def _conectar_bin(self, cabecera) -> None:
        """La hoja crea un encabezado por bin; aqui se le enchufa la ventana.

        Se llama cada vez que nace un encabezado, no una sola vez al arrancar:
        los bins aparecen y desaparecen con las importaciones.
        """
        cabecera.rename_requested.connect(self._on_bin_renombrado)
        cabecera.proxies_requested.connect(self.adjuntar_proxies_de_bin)
        cabecera.proxies_cleared.connect(self.quitar_proxies_de_bin)
        cabecera.select_all_requested.connect(self._on_bin_seleccionado)
        cabecera.remove_requested.connect(self._on_bin_quitado)

    def _on_bin_renombrado(self, viejo: str, nuevo: str) -> None:
        self.bins.renombrar(viejo, nuevo)
        self._refresh_sheet()
        self._autosave()

    def _on_bin_seleccionado(self, nombre: str) -> None:
        self.clip_sheet.set_selected(set(self.bins.clips_de(nombre)))

    def _on_bin_quitado(self, nombre: str) -> None:
        """Saca los clips del proyecto. NO borra nada del disco.

        Todo lo que va indexado por clip tiene que correrse junto, o queda
        describiendo al clip equivocado.
        """
        quitados = self.bins.quitar(nombre)
        if not quitados:
            return
        fuera = set(quitados)
        self.clips = [c for i, c in enumerate(self.clips) if i not in fuera]
        for orden, clip in enumerate(self.clips, start=1):
            clip.orden = orden
        self._clip_durations = _corrido(self._clip_durations, fuera)
        self._clip_sizes = _corrido(self._clip_sizes, fuera)
        self._clip_rotations = _corrido(self._clip_rotations, fuera)
        self._proxy_sizes = _corrido(self._proxy_sizes, fuera)
        self._proxy_candidatos = _corrido(self._proxy_candidatos, fuera)
        self.bins.reindexar_tras_quitar(quitados)
        # el historial guarda INDICES de clip: despues de correrlos ya no
        # apunta a lo mismo, y deshacer moveria el clip equivocado.
        self.history.clear()
        self.current_index = min(self.current_index, max(0, len(self.clips) - 1))
        self._refresh_sheet(force_rebuild=True)
        self._abrir_clip_actual()
        self._autosave()
```

Y el ayudante, al lado de `_gigas_del_volumen` en el mismo módulo:

```python
def _corrido(mapa: dict, fuera: set[int]) -> dict:
    """Reindexa un diccionario que va por indice de clip, despues de quitar
    los indices de `fuera`."""
    return {
        i - sum(1 for q in fuera if q < i): v
        for i, v in mapa.items()
        if i not in fuera
    }
```

- [x] **Paso 4: correr los tests**

Esperado: PASS

- [x] **Paso 5: correr la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

- [x] **Paso 6: commit**

```bash
git add -A
git commit -m "feat: el menu del bin conectado a la ventana

Quitar un bin corre TODO lo que va por indice de clip a la vez --
duraciones, tamaños, rotaciones, proxies -- y limpia el historial, que
tambien guarda indices. Cualquiera que se quede sin correr no da sintoma
hasta que un video se dibuja acostado.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# FASE 5 — Arrastrar

### Tarea 11: soltar carpetas y archivos en la ventana

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (`setAcceptDrops`,
  `dragEnterEvent`, `dragMoveEvent`, `dropEvent`)
- Test: `tests/ui/test_clip_sheet_drop.py` **(nuevo)**

> Hoy **no hay drag and drop en ninguna parte de la app** — comprobado con
> `grep setAcceptDrops src/`, que no devuelve nada. Todo esto es nuevo.

- [x] **Paso 1: escribir los tests que fallan**

```python
# tests/ui/test_clip_sheet_drop.py
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, QUrl, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from clasificador_video.ui.clip_sheet import ClipSheet


def _mime(rutas):
    m = QMimeData()
    m.setUrls([QUrl.fromLocalFile(str(r)) for r in rutas])
    return m


def _soltar(hoja, rutas, punto):
    evento = QDropEvent(punto, Qt.DropAction.CopyAction, _mime(rutas),
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    hoja.dropEvent(evento)
    return evento


def test_soltar_sobre_un_encabezado_avisa_a_que_bin_va(qtbot, tmp_path):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    hoja.set_bin_order(["Dron"])
    hoja.set_clips([_thumb(0, bin_nombre="Dron")])
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_bin.connect(lambda n, r: recibido.append((n, r)))

    cabecera = hoja.bin_header_widget("Dron")
    centro = cabecera.mapTo(hoja, cabecera.rect().center())
    _soltar(hoja, [archivo], centro)

    assert recibido == [("Dron", [archivo])]


def test_soltar_en_el_vacio_pide_un_bin_nuevo(qtbot, tmp_path):
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    archivo = tmp_path / "nuevo.MP4"
    archivo.touch()
    recibido = []
    hoja.soltado_en_nuevo_bin.connect(recibido.append)

    _soltar(hoja, [archivo], QPoint(5, 5))

    assert recibido == [[archivo]]


def test_soltar_algo_que_no_son_archivos_no_hace_nada(qtbot):
    """Arrastrar texto seleccionado de otra app no puede aceptarse: el
    cursor diria que si y no pasaria nada."""
    hoja = ClipSheet()
    qtbot.addWidget(hoja)
    m = QMimeData()
    m.setText("hola")
    evento = QDragEnterEvent(QPoint(5, 5), Qt.DropAction.CopyAction, m,
                             Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.NoModifier)

    hoja.dragEnterEvent(evento)

    assert not evento.isAccepted()
```

- [x] **Paso 2: correr y ver que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet_drop.py -q
```
Esperado: `AttributeError: 'ClipSheet' object has no attribute 'soltado_en_bin'`

- [x] **Paso 3: implementar en `ClipSheet`**

```python
    soltado_en_bin = Signal(str, list)      # nombre del bin, rutas
    soltado_en_nuevo_bin = Signal(list)     # rutas
```

En `__init__`: `self.setAcceptDrops(True)`.

```python
    def dragEnterEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        """Solo archivos. Aceptar texto o cualquier otro mime haria que el
        cursor prometa algo que al soltar no pasa."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._marcar_zona(event.position().toPoint())

    def dragMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._marcar_zona(event.position().toPoint())

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self._marcar_zona(None)

    def dropEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self._marcar_zona(None)
        if not event.mimeData().hasUrls():
            return
        rutas = [Path(u.toLocalFile()) for u in event.mimeData().urls()
                 if u.isLocalFile()]
        if not rutas:
            return
        destino = self._bin_bajo(event.position().toPoint())
        if destino is None:
            self.soltado_en_nuevo_bin.emit(rutas)
        else:
            self.soltado_en_bin.emit(destino, rutas)
        event.acceptProposedAction()

    def _bin_bajo(self, punto) -> str | None:
        """Sobre que bin se esta soltando. Cuenta el encabezado Y su franja
        de tarjetas: apuntarle al encabezado exacto seria una mira de 30 px
        de alto."""
        for nombre in self._bin_order:
            cabecera = self._bin_headers.get(nombre)
            if cabecera is None:
                continue
            arriba = cabecera.mapTo(self, cabecera.rect().topLeft()).y()
            abajo = arriba + self._alto_del_bin(nombre)
            if arriba <= punto.y() <= abajo:
                return nombre
        return None
```

`_marcar_zona` guarda qué bin resaltar y llama a `update()`; el resaltado se
pinta en el `paintEvent` del encabezado (borde punteado verde y el texto
«Soltar en “Dron”»), y la zona de bin nuevo es un widget punteado al final del
contenido, visible solo mientras hay un arrastre encima.

- [x] **Paso 4: correr y ver que pasan**

Esperado: 3 passed

- [x] **Paso 5: conectar en `MainWindow`**

```python
        self.clip_sheet.soltado_en_bin.connect(
            lambda nombre, rutas: self.importar_rutas(rutas, nombre_de_bin=nombre)
        )
        self.clip_sheet.soltado_en_nuevo_bin.connect(
            lambda rutas: self.importar_rutas(rutas)
        )
```

Con su test: soltar dos archivos que ya están en el proyecto no agrega nada
(lo filtra `importar_rutas`), y soltar algo que no es video no agrega un bin
vacío.

- [x] **Paso 6: verificación visual — obligatoria**

Captura con `grab()` de los dos estados de arrastre y compararlos contra la
pantalla 4 del mockup. Mirar el PNG.

- [x] **Paso 7: commit**

```bash
git add -A
git commit -m "feat: arrastrar carpetas y archivos a la hoja

Encima de un bin se suman ahi; en el vacio, nace un bin nuevo con el
nombre de la carpeta. Antes de esto no habia drag and drop en ninguna
parte de la app.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# FASE 6 — Filtro por bin y el bin en modo clip

### Tarea 12: `FilterState.bin`

**Archivos:**
- Modificar: `src/clasificador_video/filters.py`
- Modificar: `src/clasificador_video/ui/main_window.py` (`queue`, ~677)
- Test: `tests/test_filters.py`

- [x] **Paso 1: test**

```python
def test_el_filtro_de_bin_acota_la_cola():
    clips = [_clip("A"), _clip("B"), _clip("C")]
    estado = FilterState(bin="Dron")

    assert cola(clips, estado, bin_de={0: "Sony", 1: "Dron", 2: "Dron"}) == [1, 2]


def test_sin_filtro_de_bin_la_cola_es_la_de_siempre():
    clips = [_clip("A"), _clip("B")]

    assert cola(clips, FilterState(), bin_de={0: "Sony", 1: "Dron"}) == [0, 1]
```

- [x] **Paso 2: implementar**

`FilterState` gana `bin: str = "todos"`, `esta_filtrando()` lo incluye, y
`cola` gana el parámetro:

```python
def cola(clips: list, estado: FilterState, bin_de: dict[int, str] | None = None) -> list[int]:
    """Los indices que pasan el filtro, **en el orden de los clips**.

    `bin_de` viene aparte y no dentro del clip porque el bin no vive en
    `Clip` -- `to_dict()` es el contrato con el plugin de Premiere.
    """
    return [
        i for i, clip in enumerate(clips)
        if estado.pasa(clip)
        and (estado.bin == "todos" or not bin_de
             or bin_de.get(i) == estado.bin)
    ]
```

Y `MainWindow.queue()`:

```python
        return cola(self.clips, self.filters, bin_de=self.bins.mapa_por_clip())
```

con `BinTree.mapa_por_clip() -> dict[int, str]` y su test en `tests/test_bins.py`.

- [x] **Paso 3: los chips en la barra de filtros**

`_FilaDeChips` ya existe y arma un grupo exclusivo con su chip «Todos»
(`clip_sheet.py` ~628 y ~860). Se agrega una fila más, «Bin», construida con
los nombres que llegan por `set_bin_order`, y su chip seleccionado escribe
`bin` en el `FilterState` que emite `filters_changed`.

Test: al hacer `click()` en el chip «Dron», el `FilterState` que emite la hoja
trae `bin == "Dron"`; el chip «Todos» lo devuelve a `"todos"`.

> **Cuidado con el ancho.** La barra de filtros ya lleva dos grupos y siete
> chips, y el mockup del rediseño la dejó justo. Una fila más tiene que
> envolver a otra línea, no empujar el mínimo de la ventana. Comprobarlo con
> `grab()` a 1027 px de ancho, que es el mínimo real al que se puede arrastrar
> la ventana hoy.

- [x] **Paso 4: correr la suite completa**

- [x] **Paso 5: commit**

```bash
git add -A
git commit -m "feat: filtrar por bin, que tambien acota la cola de las flechas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 13: el nombre del bin en modo clip

**Archivos:**
- Modificar: `src/clasificador_video/ui/video_stage.py`
- Modificar: `src/clasificador_video/ui/main_window.py` (`_refresh_overlays`)
- Test: `tests/ui/test_video_stage.py`

- [x] **Paso 1: escribir el test que falla**

```python
def test_el_bin_aparece_junto_al_nombre_del_archivo(qtbot):
    stage = VideoStage(mpv_factory=_falso_mpv)
    qtbot.addWidget(stage)
    stage.resize(520, 700)

    stage.set_file_label("DJI_20260808_0009.MP4", bin_nombre="Dron")

    assert "Dron" in stage.bin_label.text()
    assert not stage.bin_label.isHidden()


def test_con_poco_ancho_se_esconde_el_bin_antes_que_el_nombre(qtbot):
    """El nombre del archivo es lo que Bruno necesita para encontrarlo en
    Finder; el bin es contexto. Cuando no caben los dos, se va el contexto.
    """
    stage = VideoStage(mpv_factory=_falso_mpv)
    qtbot.addWidget(stage)
    stage.resize(240, 700)

    stage.set_file_label("UN_NOMBRE_DE_ARCHIVO_MUY_LARGO_0009.MP4",
                         bin_nombre="Dron")

    assert stage.bin_label.isHidden()
```

> Comprobar en `tests/ui/test_video_stage.py` cómo se construye hoy el
> `VideoStage` de prueba y reusar ese ayudante en vez de escribir `_falso_mpv`
> de nuevo.

- [x] **Paso 2: correr y ver que falla**

Esperado: `TypeError: set_file_label() got an unexpected keyword argument 'bin_nombre'`

- [x] **Paso 3: implementar**

`set_file_label` gana `bin_nombre: str = ""`, y la etiqueta del bin sigue la
misma regla de espacio que ya usa el control de velocidad: **si la fila de
arriba no alcanza, lo primero que se esconde es lo menos importante.** El
orden de sacrificio queda: velocidad → bin → elidir el nombre.

En `main_window._refresh_overlays`, donde hoy se llama a `set_file_label`, se
pasa `bin_nombre=self.bins.bin_de(self.current_index) or ""`.

- [x] **Paso 4: verificación visual — obligatoria**

`grab()` del `VideoStage` en dos anchos, y **mirar los dos PNG**: que el bin
no se encime con la insignia de proxy ni empuje el nombre fuera de la fila.

- [x] **Paso 5: commit**

```bash
git add -A
git commit -m "feat: el bin, junto al nombre del archivo en modo clip

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Al terminar

- [x] Suite completa verde: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
- [x] `git status` limpio, sin archivos sueltos en la raíz y sin restos del
      scratchpad dentro del repo.
- [x] Actualizar `docs/superpowers/CONTEXTO-Y-METAS.md`: los bins pasan de «en
      marcha» a hecho, y el bug de las portadas sale de la lista.
- [ ] Anotar en el handoff qué quedó **medido** y qué quedó **supuesto**, con
      el mismo criterio de la sección 4.b: el veredicto sin la evidencia se
      vuelve a discutir en tres meses.

## Lo que este plan NO hace

Del spec §7, y no por olvido:

- LUT por bin — falta comprobar dentro de Premiere que Lumetri acepta una ruta.
- Generar los proxies del dron — ya está medido, es otra entrega.
- Mover clips entre bins arrastrando.
- Bins anidados.
- Que el bin viaje a Premiere como carpeta del proyecto.
