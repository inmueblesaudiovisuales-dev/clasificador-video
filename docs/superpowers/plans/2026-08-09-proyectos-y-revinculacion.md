# Proyectos guardables y reencontrar la media — plan de implementación

> **Para quien ejecute esto:** SUB-SKILL REQUERIDA: usar
> `superpowers:subagent-driven-development` (recomendado) o
> `superpowers:executing-plans`, tarea por tarea. Los pasos llevan casilla.

**Meta:** que el proyecto sea un archivo con nombre que Bruno pueda guardar
donde quiera, abrir en otra computadora, y reconectar con su material.

**Arquitectura:** tres módulos de lógica pura y sin Qt —el documento, los
recientes y el reencuentro— y encima una pantalla de inicio. El dato no se
inventa: la sesión de hoy ya lo guarda todo, así que la mayor parte del trabajo
es **darle nombre a lo que ya existe** y agregarle, por bin, la ruta relativa
que permite reencontrar.

**Spec:** `docs/superpowers/specs/2026-08-09-proyectos-y-revinculacion-design.md`

**Suite completa:**
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Hoy: **1142 tests**, verde. Al cerrar cada fase, **contar fallos sobre 20
corridas** con el **árbol quieto**; y si la fase toca ciclo de vida de widgets o
el acomodo de la hoja, **subir a 40** — ahí estuvieron los cuatro segfaults
intermitentes de este proyecto.

---

## Lo que hay que entender antes de la primera línea

### 1. El dato ya está completo, y eso define el alcance

`MainWindow._write_autosave_now` ya escribe **todo**: `proyecto`, `rooms`,
`clips` (con ruta, cuarto, flag, in/out, fps y proxy), `tamanos`, `duraciones`,
`rotaciones` y `bins`. Lo escribe en `~/.clasificador_video/sesion.json`
(`app.py::SESSION_PATH`), un archivo único y escondido.

**No hay que inventar qué guardar.** Hay que darle nombre, dejarlo vivir donde
Bruno quiera, y agregarle una sola cosa nueva: la ruta relativa de cada clip
respecto a la carpeta de su bin.

### 2. `Clip.to_dict()` no se toca

Es el contrato con el plugin de Premiere (`uxp-plugin/`). La ruta relativa y el
bin de cada clip viajan **al lado**, con el mismo criterio con que ya viajan
`tamanos`, `duraciones`, `rotaciones` y `bins`.

### 3. El punto peligroso: los nombres se repiten

Las cámaras renumeran desde cero en cada tarjeta: la Sony escribe `C0001.MP4`
en todas. **Reencontrar por nombre puede enganchar el archivo de otra tarjeta**,
y eso es peor que no encontrarlo, porque Bruno no se entera. Por eso cada
candidato se confirma contra lo que el proyecto ya sabía —**tamaño en bytes y
duración en cuadros**— y lo que no confirma **no se engancha y se dice**.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `src/clasificador_video/proyecto.py` **(nuevo)** | El documento: armar el dict del proyecto y volver a leerlo, con las rutas relativas por bin. Sin Qt. |
| `src/clasificador_video/recientes.py` **(nuevo)** | La lista de proyectos recientes: agregar, leer, podar. Sin Qt. |
| `src/clasificador_video/revinculo.py` **(nuevo)** | Reencontrar archivos bajo una carpeta y **confirmar** que son los que eran. Sin Qt. |
| `src/clasificador_video/ui/pantalla_inicio.py` **(nuevo)** | La pantalla de recientes, «Proyecto nuevo» y «Abrir otro…». |
| `src/clasificador_video/app.py` | Arrancar en la pantalla de inicio; migrar la sesión vieja. |
| `src/clasificador_video/ui/main_window.py` | Guardar en el archivo del proyecto; avisar y reconectar la media faltante. |
| `src/clasificador_video/ui/theme.py` | QSS de la pantalla de inicio y del aviso. |

---

# FASE 1 — El documento

### Tarea 1: armar y leer el dict del proyecto

**Archivos:**
- Crear: `src/clasificador_video/proyecto.py`
- Test: `tests/test_proyecto.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
# tests/test_proyecto.py
from pathlib import Path

from clasificador_video.bins import BinTree
from clasificador_video.manifest import Clip
from clasificador_video.proyecto import a_dict, rutas_relativas


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


def test_la_ruta_relativa_se_calcula_contra_la_carpeta_del_bin():
    bins = BinTree()
    bins.agregar("Sony", Path("/Volumes/CARD_A/01. VIDEO CAMARA"), [0, 1])
    clips = [
        _clip(0, "/Volumes/CARD_A/01. VIDEO CAMARA/C0001.MP4"),
        _clip(1, "/Volumes/CARD_A/01. VIDEO CAMARA/sub/C0002.MP4"),
    ]

    assert rutas_relativas(clips, bins) == {0: "C0001.MP4", 1: "sub/C0002.MP4"}


def test_un_clip_suelto_no_tiene_ruta_relativa():
    """Sin bin no hay raiz contra la cual ser relativo. Es un caso menor a
    proposito: los sueltos son la cola de trabajo, no el material ya
    acomodado."""
    bins = BinTree()
    clips = [_clip(0, "/algun/lado/X.MP4")]

    assert rutas_relativas(clips, bins) == {}


def test_un_clip_fuera_de_la_carpeta_de_su_bin_tampoco():
    """Puede pasar si alguien movio un archivo a mano. No se inventa una
    relativa con `..`: se guarda solo la absoluta y se reencuentra suelto."""
    bins = BinTree()
    bins.agregar("Sony", Path("/Volumes/CARD_A/CAM"), [0])
    clips = [_clip(0, "/otro/disco/C0001.MP4")]

    assert rutas_relativas(clips, bins) == {}


def test_el_dict_del_proyecto_lleva_todo_lo_de_la_sesion_mas_las_relativas():
    bins = BinTree()
    bins.agregar("Sony", Path("/cam"), [0])
    clips = [_clip(0, "/cam/C0001.MP4")]

    data = a_dict(
        proyecto="Casa Lomas",
        rooms=["Cocina"],
        clips=clips,
        bins=bins,
        tamanos={0: (1080, 1920)},
        duraciones={0: 10.0},
        rotaciones={0: 0},
    )

    assert data["proyecto"] == "Casa Lomas"
    assert data["rooms"] == ["Cocina"]
    assert data["clips"][0]["ruta"] == "/cam/C0001.MP4"
    assert data["bins"][0]["nombre"] == "Sony"
    assert data["tamanos"] == {"0": [1080, 1920]}
    assert data["duraciones"] == {"0": 10.0}
    assert data["rotaciones"] == {"0": 0}
    assert data["relativas"] == {"0": "C0001.MP4"}
    assert data["version"] == 1
```

- [x] **Paso 2: correr y ver que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -q
```
Esperado: `ModuleNotFoundError: No module named 'clasificador_video.proyecto'`

- [x] **Paso 3: implementar**

```python
# src/clasificador_video/proyecto.py
"""El proyecto como documento: lo que se guarda y lo que se lee.

Hasta ahora esto vivia repartido entre `MainWindow._write_autosave_now` y
`app._restore_session`, y el archivo era uno solo y escondido. Aqui esta
la MISMA forma, con nombre propio y con una cosa mas: la ruta de cada clip
**relativa a la carpeta de su bin**, que es lo unico que permite
reencontrar el material en otra computadora.

Sin Qt: esto se prueba sin abrir una ventana.
"""
from __future__ import annotations

from pathlib import Path

VERSION = 1


def rutas_relativas(clips: list, bins) -> dict[int, str]:
    """Por cada clip, su ruta respecto a la carpeta de su bin.

    Los que no tienen bin, o cuyo archivo esta fuera de la carpeta de su
    bin, quedan fuera: inventarles una relativa con `..` seria una ruta
    fragil que al reencontrar apuntaria a cualquier lado.
    """
    relativas: dict[int, str] = {}
    for indice, clip in enumerate(clips):
        nombre = bins.bin_de(indice)
        if nombre is None:
            continue
        origen = bins.origen_de(nombre)
        if origen is None:
            continue
        try:
            relativas[indice] = str(Path(clip.ruta).relative_to(origen))
        except ValueError:
            continue  # el archivo no cuelga de la carpeta de su bin
    return relativas


def a_dict(proyecto: str, rooms: list[str], clips: list, bins,
           tamanos: dict, duraciones: dict, rotaciones: dict) -> dict:
    return {
        "version": VERSION,
        "proyecto": proyecto,
        "rooms": list(rooms),
        "clips": [c.to_dict() for c in clips],
        # Todo esto va AL LADO de los clips y no adentro: `Clip.to_dict()`
        # es el contrato con el plugin de Premiere y no se toca.
        "tamanos": {str(i): [a, h] for i, (a, h) in tamanos.items()},
        "duraciones": {str(i): s for i, s in duraciones.items()},
        "rotaciones": {str(i): r for i, r in rotaciones.items()},
        "bins": bins.to_list(),
        "relativas": {str(i): r for i, r in rutas_relativas(clips, bins).items()},
    }
```

- [x] **Paso 4: correr y ver que pasan** — 4 passed

- [x] **Paso 5: commit**

```bash
git add src/clasificador_video/proyecto.py tests/test_proyecto.py
git commit -m "feat: el proyecto como documento, con las rutas relativas por bin

Sin Qt. La ruta relativa es lo unico que permite reencontrar el material
en otra computadora: las absolutas nunca coinciden ahi.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 2: guardar y abrir el archivo

**Archivos:**
- Modificar: `src/clasificador_video/proyecto.py`
- Test: `tests/test_proyecto.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
def test_ida_y_vuelta_a_disco(tmp_path):
    bins = BinTree()
    bins.agregar("Sony", Path("/cam"), [0])
    ruta = tmp_path / "Casa Lomas.cvproj"

    guardar(ruta, a_dict(proyecto="Casa Lomas", rooms=["Cocina"],
                         clips=[_clip(0, "/cam/C0001.MP4")], bins=bins,
                         tamanos={}, duraciones={}, rotaciones={}))

    data = abrir(ruta)
    assert data["proyecto"] == "Casa Lomas"
    assert data["relativas"] == {"0": "C0001.MP4"}


def test_abrir_algo_que_no_es_un_proyecto_no_revienta(tmp_path):
    """Un archivo corrupto o de otra cosa se trata como «no se pudo abrir»,
    igual que hace `load_session`. Reventar aqui deja a Bruno sin forma de
    salir: esto corre al elegir un archivo."""
    malo = tmp_path / "cualquiera.cvproj"
    malo.write_text("esto no es json {")

    assert abrir(malo) is None


def test_abrir_uno_que_no_existe_devuelve_None(tmp_path):
    assert abrir(tmp_path / "no-esta.cvproj") is None


def test_guardar_es_atomico(tmp_path):
    """Mismo criterio que `autosave.save_session`: temporal + rename. Si la
    app muere a medio escribir, el archivo queda con lo viejo completo o
    con lo nuevo completo, nunca a medias."""
    ruta = tmp_path / "p.cvproj"
    guardar(ruta, {"version": 1, "proyecto": "A"})
    guardar(ruta, {"version": 1, "proyecto": "B"})

    assert abrir(ruta)["proyecto"] == "B"
    assert not (tmp_path / "p.cvproj.tmp").exists()
```

- [x] **Paso 2: correr y ver que fallan**

Esperado: `ImportError: cannot import name 'guardar'`

- [x] **Paso 3: implementar**

```python
EXTENSION = ".cvproj"


def guardar(ruta: Path, data: dict) -> None:
    """Escritura atomica, igual que `autosave.save_session`.

    No se reusa aquella funcion a proposito: son dos cosas distintas que hoy
    se escriben igual --el autosave de la sesion y el documento de Bruno--
    y atarlas obligaria a que cambien juntas.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    os.replace(tmp, ruta)


def abrir(ruta: Path) -> dict | None:
    """`None` si no se pudo leer. Esto corre al elegir un archivo, asi que
    reventar aqui dejaria a Bruno sin forma de salir."""
    try:
        data = json.loads(ruta.read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None
```

con `import json, os` arriba del módulo.

- [x] **Paso 4: correr y ver que pasan** — 8 passed

- [x] **Paso 5: commit**

---

# FASE 2 — Los recientes

### Tarea 3: la lista de proyectos recientes

**Archivos:**
- Crear: `src/clasificador_video/recientes.py`
- Test: `tests/test_recientes.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
# tests/test_recientes.py
from pathlib import Path

from clasificador_video.recientes import Recientes


def test_el_ultimo_abierto_queda_primero(tmp_path):
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(Path("/a/uno.cvproj"), "Uno")
    r.registrar(Path("/a/dos.cvproj"), "Dos")

    assert [e.nombre for e in r.lista()] == ["Dos", "Uno"]


def test_volver_a_abrir_uno_lo_sube_sin_duplicarlo(tmp_path):
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(Path("/a/uno.cvproj"), "Uno")
    r.registrar(Path("/a/dos.cvproj"), "Dos")
    r.registrar(Path("/a/uno.cvproj"), "Uno")

    assert [e.nombre for e in r.lista()] == ["Uno", "Dos"]


def test_se_guarda_y_se_vuelve_a_leer(tmp_path):
    archivo = tmp_path / "recientes.json"
    Recientes(archivo).registrar(Path("/a/uno.cvproj"), "Uno")

    assert [e.nombre for e in Recientes(archivo).lista()] == ["Uno"]


def test_un_archivo_corrupto_se_trata_como_lista_vacia(tmp_path):
    """Los recientes son una comodidad. Que un JSON roto impida ABRIR la
    app seria cambiar una comodidad por un ladrillo."""
    archivo = tmp_path / "recientes.json"
    archivo.write_text("{{{ no es json")

    assert Recientes(archivo).lista() == []


def test_dice_cuales_ya_no_estan_en_su_lugar(tmp_path):
    """No se podan solos: se muestran apagados. Bruno tiene que poder ver
    que el proyecto existio y que el disco no esta conectado, en vez de que
    desaparezca de la lista sin explicacion."""
    existe = tmp_path / "esta.cvproj"
    existe.write_text("{}")
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(existe, "Esta")
    r.registrar(tmp_path / "no-esta.cvproj", "No esta")

    faltantes = [e for e in r.lista() if not e.disponible]
    assert [e.nombre for e in faltantes] == ["No esta"]


def test_se_puede_quitar_uno_de_la_lista(tmp_path):
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(Path("/a/uno.cvproj"), "Uno")

    r.quitar(Path("/a/uno.cvproj"))

    assert r.lista() == []


def test_la_lista_no_crece_sin_limite(tmp_path):
    r = Recientes(tmp_path / "recientes.json")
    for i in range(15):
        r.registrar(Path(f"/a/{i}.cvproj"), f"P{i}")

    assert len(r.lista()) == 10
```

- [x] **Paso 2: correr y ver que fallan**

- [x] **Paso 3: implementar**

```python
# src/clasificador_video/recientes.py
"""Los proyectos abiertos ultimamente, el mas reciente primero.

Vive junto a la sesion, en `~/.clasificador_video/`. Es una comodidad, no
un dato del que dependa nada: si el archivo se corrompe o desaparece, la
lista sale vacia y la app abre igual.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAXIMO = 10


@dataclass
class Reciente:
    ruta: Path
    nombre: str
    cuando: str

    @property
    def disponible(self) -> bool:
        return self.ruta.exists()


class Recientes:
    def __init__(self, archivo: Path) -> None:
        self._archivo = archivo
        self._entradas: list[Reciente] = self._leer()

    def _leer(self) -> list[Reciente]:
        try:
            crudo = json.loads(self._archivo.read_text())
        except (OSError, json.JSONDecodeError, ValueError):
            return []
        if not isinstance(crudo, list):
            return []
        entradas = []
        for d in crudo:
            if not isinstance(d, dict) or not d.get("ruta"):
                continue
            entradas.append(Reciente(
                ruta=Path(str(d["ruta"])),
                nombre=str(d.get("nombre") or Path(str(d["ruta"])).stem),
                cuando=str(d.get("cuando") or ""),
            ))
        return entradas[:MAXIMO]

    def _escribir(self) -> None:
        self._archivo.parent.mkdir(parents=True, exist_ok=True)
        self._archivo.write_text(json.dumps(
            [{"ruta": str(e.ruta), "nombre": e.nombre, "cuando": e.cuando}
             for e in self._entradas],
            indent=2, ensure_ascii=False,
        ))

    def registrar(self, ruta: Path, nombre: str) -> None:
        self._entradas = [e for e in self._entradas if e.ruta != ruta]
        self._entradas.insert(0, Reciente(
            ruta=ruta, nombre=nombre,
            cuando=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        del self._entradas[MAXIMO:]
        self._escribir()

    def quitar(self, ruta: Path) -> None:
        self._entradas = [e for e in self._entradas if e.ruta != ruta]
        self._escribir()

    def lista(self) -> list[Reciente]:
        return list(self._entradas)
```

- [x] **Paso 4: correr y ver que pasan** — 7 passed

- [x] **Paso 5: commit**

> **Cerradas el 2026-08-09.** La revisión de las fases 1 y 2 agregó, sobre lo
> que este plan pedía: el origen de un bin ahora **sube al ancestro común**
> cuando se le suma material de otra carpeta (`bins.sumar`) —sin eso, soltar
> la segunda tarjeta de la Sony dejaba esos clips sin relativa y la fase 3 los
> daría por «no encontrados» con el archivo ahí enfrente—; `rutas_relativas`
> descarta la relativa con `..`; `guardar` limpia su `.tmp`; y `Recientes`
> escribe atómico, traga el `OSError`, deduplica, congela `disponible` al leer
> y relee antes de mutar. Tests: 10 en `test_proyecto.py`, 12 en
> `test_recientes.py`, 7 nuevos en `test_bins.py`.

---

# FASE 3 — Reencontrar la media

> **La fase con el riesgo real del plan.** Enganchar el archivo equivocado es
> peor que no encontrarlo, porque Bruno no se entera.

### Tarea 4: buscar candidatos bajo una carpeta

**Archivos:**
- Crear: `src/clasificador_video/revinculo.py`
- Test: `tests/test_revinculo.py`

- [x] **Paso 1: escribir los tests que fallan**

```python
# tests/test_revinculo.py
from pathlib import Path

from clasificador_video.revinculo import buscar_bajo


def test_encuentra_por_la_ruta_relativa_exacta(tmp_path):
    (tmp_path / "sub").mkdir()
    esperado = tmp_path / "sub" / "C0001.MP4"
    esperado.write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001.MP4") == esperado


def test_si_no_esta_en_su_sitio_lo_busca_por_nombre(tmp_path):
    """La carpeta pudo reorganizarse. Buscar por nombre es el plan B, y por
    eso lo que se encuentre asi tiene que CONFIRMARSE (ver `calza`)."""
    (tmp_path / "otra").mkdir()
    esta = tmp_path / "otra" / "C0001.MP4"
    esta.write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001.MP4") == esta


def test_con_dos_tocayos_no_elige_ninguno(tmp_path):
    """Las camaras renumeran desde cero en cada tarjeta: dos `C0001.MP4`
    bajo la misma carpeta es un caso REAL, no rebuscado. Elegir uno al azar
    seria enganchar material equivocado sin que nadie se entere."""
    for sub in ("tarjeta1", "tarjeta2"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "C0001.MP4").write_bytes(b"x")

    assert buscar_bajo(tmp_path, "no-esta/C0001.MP4") is None


def test_si_esta_en_su_sitio_los_tocayos_no_estorban(tmp_path):
    """La ruta relativa desempata: si el archivo esta donde decia, se toma
    ese y los tocayos de otras carpetas dan igual."""
    for sub in ("sub", "tarjeta2"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "C0001.MP4").write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001.MP4") == tmp_path / "sub" / "C0001.MP4"


def test_una_carpeta_que_no_existe_no_revienta(tmp_path):
    assert buscar_bajo(tmp_path / "no-esta", "C0001.MP4") is None
```

- [x] **Paso 2: correr y ver que fallan**

- [x] **Paso 3: implementar**

```python
# src/clasificador_video/revinculo.py
"""Reencontrar el material cuando el proyecto se abre en otro lado.

Dos pasos, y el segundo es el que importa: **buscar** un candidato, y
**confirmar** que es el archivo que era. Las camaras renumeran desde cero
en cada tarjeta --la Sony escribe `C0001.MP4` en todas-- asi que el nombre
solo no alcanza: enganchar el archivo equivocado es peor que no
encontrarlo, porque nadie se entera.

Sin Qt.
"""
from __future__ import annotations

from pathlib import Path

# cuantos cuadros de diferencia se toleran al confirmar. El mismo margen
# que usa `_el_proxy_calza`: ffprobe redondea distinto segun el contenedor.
TOLERANCIA_DE_CUADROS = 1


def buscar_bajo(carpeta: Path, relativa: str) -> Path | None:
    """Primero donde decia; si no, por nombre en todo el arbol.

    Devuelve `None` cuando hay mas de un candidato con ese nombre: ahi
    elegir seria adivinar.
    """
    if not carpeta.is_dir():
        return None
    en_su_sitio = carpeta / relativa
    if en_su_sitio.is_file():
        return en_su_sitio
    nombre = Path(relativa).name
    candidatos = [p for p in carpeta.rglob(nombre) if p.is_file()]
    return candidatos[0] if len(candidatos) == 1 else None
```

- [x] **Paso 4: correr y ver que pasan** — 5 passed

- [x] **Paso 5: commit**

---

### Tarea 5: confirmar que el archivo es el que era

**Archivos:**
- Modificar: `src/clasificador_video/revinculo.py`
- Test: `tests/test_revinculo.py`

- [x] **Paso 1: escribir los tests que fallan — el más importante del plan**

```python
from clasificador_video.revinculo import calza


def test_calza_cuando_coinciden_tamano_y_cuadros(tmp_path):
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=lambda p: {"duration_frames": 300}) is True


def test_NO_calza_un_tocayo_de_otro_tamano(tmp_path):
    """EL test de este plan. Un archivo con el nombre correcto y el
    contenido equivocado no se engancha. Es el caso de dos tarjetas de la
    misma camara, que numeran igual desde cero.
    """
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 999)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=lambda p: {"duration_frames": 300}) is False


def test_NO_calza_si_dura_distinto(tmp_path):
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=lambda p: {"duration_frames": 450}) is False


def test_un_cuadro_de_diferencia_se_tolera(tmp_path):
    """Mismo margen que `_el_proxy_calza`: ffprobe redondea distinto segun
    el contenedor, y un cuadro no distingue dos tomas."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=301,
                 medir=lambda p: {"duration_frames": 300}) is True


def test_sin_datos_guardados_basta_el_tamano(tmp_path):
    """Una sesion vieja puede no traer la duracion de todos los clips. Sin
    ese dato se confirma solo con el tamaño, que ya descarta al tocayo, en
    vez de rechazar material bueno."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=None,
                 medir=lambda p: {"duration_frames": 300}) is True


def test_si_no_se_puede_medir_no_calza(tmp_path):
    """Un archivo que ffprobe no puede leer no es «el que era»: es un
    archivo roto con el nombre correcto."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    def revienta(p):
        raise OSError("no se pudo leer")

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=revienta) is False
```

- [x] **Paso 2: correr y ver que fallan**

- [x] **Paso 3: implementar**

```python
def calza(archivo: Path, tamano_esperado: int | None,
          cuadros_esperados: int | None, medir) -> bool:
    """¿Este archivo es el que el proyecto tenia?

    `medir` es la funcion que lee el video (en la app, `probe_clip`); se
    inyecta para poder probar esto sin ffprobe.

    El tamaño solo ya descarta al tocayo de otra tarjeta. Los cuadros se
    comprueban ADEMAS cuando el proyecto los sabia, porque dos tomas de la
    misma duracion pesan distinto pero dos archivos del mismo peso podrian
    ser el mismo material recodificado.
    """
    if tamano_esperado is not None:
        try:
            if archivo.stat().st_size != tamano_esperado:
                return False
        except OSError:
            return False
    if cuadros_esperados is None:
        return True
    try:
        info = medir(archivo)
    except Exception:
        return False
    cuadros = int((info or {}).get("duration_frames") or 0)
    return abs(cuadros - cuadros_esperados) <= TOLERANCIA_DE_CUADROS
```

> **El tamaño hay que guardarlo**, y hoy no se guarda. La tarea 6 lo agrega
> al documento.

- [x] **Paso 4: correr y ver que pasan** — 6 passed

- [x] **Paso 5: commit**

---

### Tarea 6: guardar el tamaño de cada archivo

**Archivos:**
- Modificar: `src/clasificador_video/proyecto.py`
- Test: `tests/test_proyecto.py`

- [x] **Paso 1: test**

```python
def test_el_proyecto_guarda_el_tamano_de_cada_archivo(tmp_path):
    """Sin esto no hay como confirmar que un archivo reencontrado es el que
    era: el nombre lo repiten las camaras y la duracion sola no distingue
    dos tomas iguales."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 700)
    bins = BinTree()
    bins.agregar("Sony", tmp_path, [0])

    data = a_dict(proyecto="P", rooms=[], clips=[_clip(0, str(archivo))],
                  bins=bins, tamanos={}, duraciones={}, rotaciones={})

    assert data["bytes"] == {"0": 700}


def test_un_archivo_que_ya_no_esta_no_impide_guardar(tmp_path):
    """Guardar tiene que funcionar con el disco desconectado: si no, se
    pierde el trabajo justo cuando mas duele."""
    bins = BinTree()
    bins.agregar("Sony", Path("/no/existe"), [0])

    data = a_dict(proyecto="P", rooms=[], clips=[_clip(0, "/no/existe/X.MP4")],
                  bins=bins, tamanos={}, duraciones={}, rotaciones={})

    assert data["bytes"] == {}
```

- [x] **Paso 2: correr y ver que fallan**

- [x] **Paso 3: implementar** — en `a_dict`, agregar:

```python
        "bytes": {str(i): t for i, t in _tamanos_en_disco(clips).items()},
```

```python
def _tamanos_en_disco(clips: list) -> dict[int, int]:
    """El peso de cada archivo, para poder confirmarlo al reencontrarlo.

    Lo que no se puede leer se omite: guardar tiene que funcionar con el
    disco desconectado, o se pierde trabajo justo cuando mas duele.
    """
    tamanos = {}
    for indice, clip in enumerate(clips):
        try:
            tamanos[indice] = Path(clip.ruta).stat().st_size
        except OSError:
            continue
    return tamanos
```

- [x] **Paso 4: correr, commit**

---

### Tarea 7: reencontrar un bin entero

**Archivos:**
- Modificar: `src/clasificador_video/revinculo.py`
- Test: `tests/test_revinculo.py`

- [x] **Paso 1: tests**

```python
from clasificador_video.revinculo import faltantes_de, reencontrar_bin


def test_faltantes_de_lista_lo_que_no_esta(tmp_path):
    esta = tmp_path / "A.MP4"
    esta.write_bytes(b"x")

    assert faltantes_de([esta, tmp_path / "B.MP4"]) == [1]


def test_reencontrar_devuelve_los_que_calzan_y_los_que_no(tmp_path):
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    bueno = nueva / "C0001.MP4"
    bueno.write_bytes(b"x" * 500)
    tocayo = nueva / "C0002.MP4"
    tocayo.write_bytes(b"x" * 111)          # peso equivocado: no calza

    resultado = reencontrar_bin(
        carpeta=nueva,
        relativas={0: "C0001.MP4", 1: "C0002.MP4"},
        bytes_esperados={0: 500, 1: 999},
        cuadros_esperados={},
        medir=lambda p: {"duration_frames": 0},
    )

    assert resultado.reconectados == {0: bueno}
    assert resultado.sin_confirmar == [1]


def test_lo_que_no_aparece_queda_como_no_encontrado(tmp_path):
    nueva = tmp_path / "nueva"
    nueva.mkdir()

    resultado = reencontrar_bin(
        carpeta=nueva, relativas={0: "C0001.MP4"},
        bytes_esperados={0: 500}, cuadros_esperados={},
        medir=lambda p: {"duration_frames": 0},
    )

    assert resultado.reconectados == {}
    assert resultado.no_encontrados == [0]
```

- [x] **Paso 2: correr y ver que fallan**

- [x] **Paso 3: implementar**

```python
@dataclass
class Reencuentro:
    """Los tres finales posibles, separados a proposito.

    `sin_confirmar` NO es lo mismo que `no_encontrados`: ahi hay un archivo
    con el nombre correcto que **no es** el que era, y eso hay que
    decirselo a Bruno con otras palabras --es el caso de la segunda tarjeta
    de la misma camara-- en vez de mezclarlo con «no aparecio».
    """
    reconectados: dict[int, Path]
    sin_confirmar: list[int]
    no_encontrados: list[int]


def faltantes_de(rutas: list[Path]) -> list[int]:
    return [i for i, r in enumerate(rutas) if not Path(r).is_file()]


def reencontrar_bin(carpeta: Path, relativas: dict[int, str],
                    bytes_esperados: dict[int, int],
                    cuadros_esperados: dict[int, int], medir) -> Reencuentro:
    reconectados: dict[int, Path] = {}
    sin_confirmar: list[int] = []
    no_encontrados: list[int] = []
    for indice, relativa in relativas.items():
        candidato = buscar_bajo(carpeta, relativa)
        if candidato is None:
            no_encontrados.append(indice)
        elif calza(candidato, bytes_esperados.get(indice),
                   cuadros_esperados.get(indice), medir):
            reconectados[indice] = candidato
        else:
            sin_confirmar.append(indice)
    return Reencuentro(reconectados, sorted(sin_confirmar), sorted(no_encontrados))
```

con `from dataclasses import dataclass` arriba.

- [x] **Paso 4: correr, commit**

---

# FASE 4 — La pantalla de inicio

### Tarea 8: el widget

**Archivos:**
- Crear: `src/clasificador_video/ui/pantalla_inicio.py`
- Modificar: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_pantalla_inicio.py`

- [ ] **Paso 1: tests**

```python
def test_lista_los_recientes_con_el_mas_nuevo_arriba(qtbot):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([
        Reciente(Path("/a/dos.cvproj"), "Dos", "2026-08-09 10:00"),
        Reciente(Path("/a/uno.cvproj"), "Uno", "2026-08-08 09:00"),
    ])

    assert pantalla.nombres_visibles() == ["Dos", "Uno"]


def test_un_proyecto_que_no_esta_se_ve_apagado_y_no_abre(qtbot, tmp_path):
    """Se muestra en vez de podarse: Bruno tiene que ver que el proyecto
    existio y que el disco no esta conectado, no que desaparecio."""
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(tmp_path / "no-esta.cvproj", "Fantasma", "")])
    abiertos = []
    pantalla.abrir_pedido.connect(abiertos.append)

    fila = pantalla.filas[0]
    assert not fila.isEnabled()
    fila.click()
    assert abiertos == []


def test_los_botones_avisan(qtbot):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    nuevos, otros = [], []
    pantalla.nuevo_pedido.connect(lambda: nuevos.append(1))
    pantalla.abrir_otro_pedido.connect(lambda: otros.append(1))

    pantalla.boton_nuevo.click()
    pantalla.boton_abrir_otro.click()

    assert nuevos == [1] and otros == [1]


def test_sin_recientes_invita_a_empezar(qtbot):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([])

    assert pantalla.nombres_visibles() == []
    assert not pantalla.boton_nuevo.isHidden()
```

- [ ] **Paso 2: correr y ver que fallan**

- [ ] **Paso 3: implementar**

```python
class _FilaReciente(QPushButton):
    """Un proyecto de la lista. Es un boton y no un renglon decorado porque
    la accion principal es abrirlo: que se vea clickeable no es adorno.
    """

    quitar_pedido = Signal(Path)

    def __init__(self, entrada, parent=None):
        super().__init__(parent)
        self.setObjectName("filaReciente")
        self.entrada = entrada
        self.setEnabled(entrada.disponible)
        detalle = str(entrada.ruta.parent)
        if not entrada.disponible:
            # se muestra en vez de podarse: Bruno tiene que ver que el
            # proyecto existio y que el disco no esta conectado, no que
            # desaparecio sin explicacion
            detalle = "no se encuentra · " + detalle
        self.setText(f"{entrada.nombre}\n{entrada.cuando}  ·  {detalle}")

    def contextMenuEvent(self, event):  # noqa: N802 -- override de Qt
        menu = QMenu(self)
        menu.addAction("Quitar de la lista").triggered.connect(
            lambda: self.quitar_pedido.emit(self.entrada.ruta)
        )
        menu.popup(event.globalPos())   # popup, no exec: exec cuelga offscreen


class PantallaInicio(QWidget):
    abrir_pedido = Signal(Path)
    nuevo_pedido = Signal()
    abrir_otro_pedido = Signal()
    quitar_pedido = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaInicio")
        self.filas: list[_FilaReciente] = []
        raiz = QVBoxLayout(self)
        self.titulo = QLabel("Tus proyectos")
        self.titulo.setObjectName("inicioTitulo")
        self.lista_host = QWidget()
        self.lista = QVBoxLayout(self.lista_host)
        self.boton_nuevo = QPushButton("Proyecto nuevo")
        self.boton_nuevo.setObjectName("inicioPrimario")
        self.boton_abrir_otro = QPushButton("Abrir otro…")
        self.boton_nuevo.clicked.connect(self.nuevo_pedido.emit)
        self.boton_abrir_otro.clicked.connect(self.abrir_otro_pedido.emit)
        raiz.addWidget(self.titulo)
        raiz.addWidget(self.lista_host)
        botones = QHBoxLayout()
        botones.addWidget(self.boton_nuevo)
        botones.addWidget(self.boton_abrir_otro)
        raiz.addLayout(botones)

    def set_recientes(self, entradas: list) -> None:
        for fila in self.filas:
            fila.hide()
            fila.setParent(None)
            fila.deleteLater()   # nunca setParent(None) a secas: ya costo un segfault
        self.filas = []
        for entrada in entradas:
            fila = _FilaReciente(entrada, self.lista_host)
            fila.clicked.connect(lambda _=False, e=entrada: self.abrir_pedido.emit(e.ruta))
            fila.quitar_pedido.connect(self.quitar_pedido.emit)
            self.lista.addWidget(fila)
            self.filas.append(fila)

    def nombres_visibles(self) -> list[str]:
        return [f.entrada.nombre for f in self.filas]
```

El QSS de `#pantallaInicio`, `#inicioTitulo`, `#filaReciente` e
`#inicioPrimario` va en `theme.py`, siguiendo la forma exacta de
`build_stylesheet`, **con la paleta que ya existe y sin colores nuevos**. La
fila deshabilitada se distingue con `#filaReciente:disabled`, usando `TEXT_3`,
que es el gris apagado que la app ya usa para lo secundario.

- [ ] **Paso 4: verificación visual — obligatoria**

`grab()` de la pantalla con tres recientes, uno de ellos apagado, y otra con la
lista vacía. Guardar los PNG **en el scratchpad, nunca en el repo**, y abrirlos
para **mirarlos**: que el apagado se distinga de un vistazo, que las rutas
largas se eliden y no empujen el ancho, y que los botones no queden perdidos.

- [ ] **Paso 5: commit**

---

# FASE 5 — Cablear: nuevo, abrir, guardar, migrar

### Tarea 9: la app arranca en la pantalla de inicio

**Archivos:**
- Modificar: `src/clasificador_video/app.py`
- Modificar: `src/clasificador_video/ui/main_window.py`
- Test: `tests/test_app.py`

- [x] **Paso 1: tests**

```python
def test_arranca_mostrando_los_recientes(qtbot, tmp_path):
    inicio = arrancar_inicio(recientes_path=tmp_path / "r.json")
    qtbot.addWidget(inicio)

    assert inicio.isVisible() or inicio.nombres_visibles() == []


def test_abrir_un_proyecto_carga_sus_clips_y_sus_bins(qtbot, tmp_path):
    ruta = tmp_path / "P.cvproj"
    guardar(ruta, {"version": 1, "proyecto": "P", "rooms": ["Cocina"],
                   "clips": [{"orden": 1, "ruta": "/cam/C0001.MP4",
                              "categoria_path": ["Cocina"], "fps": 30.0,
                              "in_frame": None, "out_frame": None,
                              "flag": "pick", "ruta_proxy": None}],
                   "bins": [{"nombre": "Sony", "origen": "/cam", "clips": [0]}],
                   "tamanos": {}, "duraciones": {}, "rotaciones": {},
                   "relativas": {"0": "C0001.MP4"}, "bytes": {}})

    window = abrir_proyecto(ruta, video_factory=FakeMpv)
    qtbot.addWidget(window)

    assert window.project_name == "P"
    assert [c.ruta for c in window.clips] == [Path("/cam/C0001.MP4")]
    assert window.bins.nombres() == ["Sony"]
    assert window.clips[0].flag == "pick"


def test_abrir_lo_registra_en_recientes(qtbot, tmp_path):
    ...
```

- [x] **Paso 2: correr y ver que fallan**

Esperado: `ImportError: cannot import name 'abrir_proyecto'`

> **Pendiente que dejó la fase 1:** `proyecto.abrir` acepta cualquier JSON
> que sea un objeto, así que elegir un `.json` cualquiera con «Abrir otro…»
> abriría un «proyecto» vacío sin decir que no lo era. Aquí hay que exigirle
> al menos `version` o `clips`, y avisar cuando no los trae.

- [x] **Paso 3: implementar en `app.py`**

**Primero el refactor**, porque sin él se duplica lógica: `_restore_session`
hace hoy dos cosas —preguntar si recuperar, y armar la ventana desde el dict—.
Partirlas en dos, y que el armado se llame desde los dos lados:

```python
def _poblar_ventana(window: MainWindow, data: dict) -> None:
    """Arma la ventana desde el dict de un proyecto.

    Sale de `_restore_session`, que hacia esto Y ademas preguntaba si
    recuperar la sesion. Abrir un proyecto no pregunta nada, asi que las dos
    cosas se separaron en vez de copiarse.
    """
    window.project_name = str(data.get("proyecto") or "Shooting sin nombre")
    window.room_selection = _rebuild_room_selection(data.get("rooms", []))
    window._router = KeyboardRouter(active_rooms=window.room_selection.active_rooms())
    window.load_clips([_clip_from_dict(d) for d in data.get("clips", [])])
    window.bins = BinTree.desde_sesion(
        data.get("bins"), rutas=[c.ruta for c in window.clips]
    )
    # ANTES de las miniaturas: la duracion decide si se extrae la tira de 12
    # cuadros o un solo frame, y el tamaño decide la forma de la tarjeta.
    window._clip_sizes = {
        int(i): (int(t[0]), int(t[1])) for i, t in (data.get("tamanos") or {}).items()
    }
    window._clip_durations = {
        int(i): float(s) for i, s in (data.get("duraciones") or {}).items()
    }
    window._clip_rotations = {
        int(i): int(r) for i, r in (data.get("rotaciones") or {}).items()
    }
    # lo que hace falta para reencontrar el material si el proyecto se abre
    # en otra computadora
    window._relativas = {int(i): str(r) for i, r in (data.get("relativas") or {}).items()}
    window._bytes_guardados = {int(i): int(b) for i, b in (data.get("bytes") or {}).items()}
    window._refresh_sheet(force_rebuild=True)
    window._resize_video_stage()
    window._schedule_thumbnails()
```

Y encima:

```python
RECIENTES_PATH = Path.home() / ".clasificador_video" / "recientes.json"


def abrir_proyecto(ruta: Path, video_factory=None,
                   recientes_path: Path | None = None) -> MainWindow | None:
    """Abre un `.cvproj`. `None` si el archivo no se pudo leer."""
    data = proyecto.abrir(ruta)
    if data is None:
        return None
    window = MainWindow(
        project_name=str(data.get("proyecto") or ruta.stem),
        room_selection=RoomSelection(),
        video_factory=video_factory,
    )
    # el autoguardado que ya existe escribe donde diga `session_path`: al
    # apuntarlo al .cvproj, guardar el proyecto es lo que la app ya hacia
    window.session_path = ruta
    _poblar_ventana(window, data)
    Recientes(recientes_path or RECIENTES_PATH).registrar(
        ruta, window.project_name
    )
    return window


def arrancar_inicio(recientes_path: Path | None = None) -> PantallaInicio:
    pantalla = PantallaInicio()
    pantalla.set_recientes(Recientes(recientes_path or RECIENTES_PATH).lista())
    return pantalla
```

`MainWindow` gana `self._relativas: dict[int, str] = {}` y
`self._bytes_guardados: dict[int, int] = {}` en `__init__`, y
`_write_autosave_now` pasa a construir el dict con `proyecto.a_dict(...)` en
vez de armarlo a mano — **una sola forma del documento**, no dos.

- [x] **Paso 4: correr la suite completa**

Los tests que hoy llaman a `_restore_session` siguen valiendo; si alguno se
apoyaba en que esa función armara la ventana **y** preguntara, ajústalo y deja
el comentario de por qué.

- [x] **Paso 5: commit**

```bash
git add -A
git commit -m "feat: abrir un proyecto con nombre, y arrancar en los recientes

El autoguardado no cambia: escribe donde diga `session_path`, y ahora eso
apunta al .cvproj que Bruno eligio.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Tarea 10: proyecto nuevo, y migrar la sesión vieja

**Archivos:**
- Modificar: `src/clasificador_video/app.py`
- Test: `tests/test_app.py`

- [x] **Paso 1: tests**

```python
def test_proyecto_nuevo_crea_el_archivo_de_una_vez(qtbot, tmp_path):
    """Nunca existe trabajo sin un archivo donde vivir: decision de Bruno."""
    ruta = tmp_path / "Casa Nueva.cvproj"

    window = crear_proyecto(ruta, "Casa Nueva", video_factory=FakeMpv)
    qtbot.addWidget(window)

    assert ruta.exists()
    assert window.project_name == "Casa Nueva"
    assert window.clips == []


def test_la_sesion_vieja_se_convierte_en_proyecto(qtbot, tmp_path):
    """Bruno tiene material clasificado en la sesion escondida. Al arrancar
    con esto por primera vez, NO se pierde."""
    sesion = tmp_path / "sesion.json"
    sesion.write_text(json.dumps({
        "proyecto": "Lo de antes", "rooms": ["Cocina"],
        "clips": [{"orden": 1, "ruta": "/cam/C0001.MP4",
                   "categoria_path": ["Cocina"], "fps": 30.0,
                   "in_frame": None, "out_frame": None,
                   "flag": "pick", "ruta_proxy": None}],
        "bins": [], "tamanos": {}, "duraciones": {}, "rotaciones": {},
    }))
    destino = tmp_path / "convertido.cvproj"

    migrar_sesion(sesion, destino)

    data = abrir(destino)
    assert data["proyecto"] == "Lo de antes"
    assert data["clips"][0]["flag"] == "pick"
    # la vieja NO se borra: se conserva hasta que lo nuevo este a salvo
    assert sesion.exists()
```

- [x] **Paso 2: correr y ver que fallan**

- [x] **Paso 3: implementar en `app.py`**

```python
def crear_proyecto(ruta: Path, nombre: str, video_factory=None,
                   recientes_path: Path | None = None) -> MainWindow:
    """Un proyecto nuevo, vacio y YA guardado.

    Se escribe el archivo antes de devolver la ventana por decision de
    Bruno: nunca existe trabajo sin un archivo donde vivir. Si el disco
    donde lo puso se desconecta despues, el autoguardado fallara --pero al
    menos el proyecto existio.
    """
    window = MainWindow(
        project_name=nombre,
        room_selection=RoomSelection(),
        video_factory=video_factory,
    )
    window.session_path = ruta
    window._write_autosave_now()
    window._autosave_pool.waitForDone(2000)
    Recientes(recientes_path or RECIENTES_PATH).registrar(ruta, nombre)
    return window


def migrar_sesion(sesion: Path, destino: Path) -> bool:
    """Convierte la sesion escondida en un proyecto de verdad.

    Bruno tiene material clasificado ahi. La sesion vieja **no se borra**:
    se conserva hasta que el proyecto convertido este a salvo. Borrar lo
    viejo antes de que lo nuevo exista es como se pierden cosas.

    Devuelve False si no habia nada que migrar.
    """
    data = load_session(sesion)
    if not data or not data.get("clips"):
        return False
    data.setdefault("version", proyecto.VERSION)
    data.setdefault("relativas", {})
    data.setdefault("bytes", {})
    proyecto.guardar(destino, data)
    return True
```

> **La sesión vieja no se borra**, y eso es parte del diseño, no un olvido.
> Ponle su test: después de migrar, el archivo original sigue existiendo.

- [x] **Paso 4: cablear la pantalla de inicio con los tres caminos**

`main()` construye la `PantallaInicio`, y sus tres señales llevan a
`abrir_proyecto`, a `crear_proyecto` (con un `QFileDialog.getSaveFileName`
para nombre y lugar) y a `abrir_proyecto` con
`QFileDialog.getOpenFileName`. Al abrirse una ventana, la pantalla se
esconde; al cerrarse la ventana, vuelve.

Y al arrancar, **antes** de mostrar la pantalla: si existe la sesión vieja con
clips y todavía no se migró, `migrar_sesion` la convierte y la registra en
recientes.

- [x] **Paso 5: correr la suite completa y commitear**

> **Cerrada el 2026-08-09.** 1255 tests, **0 fallos sobre 40 corridas** con el
> árbol quieto. Sobre lo que el plan pedía:
>
> - **El pendiente de `bytes_conocidos` quedó cerrado con dos tests**: uno de
>   ventana (`_write_autosave_now` con la media ausente conserva los pesos) y
>   uno de punta a punta en `test_app.py` —abrir un `.cvproj` cuya media no
>   existe, dejar que el debounce de 400 ms del autoguardado se cumpla solo, y
>   comprobar que `bytes` y `relativas` siguen en el archivo—.
> - `_write_autosave_now` construye el dict con `proyecto.a_dict(...)`: una
>   sola forma del documento. `MainWindow` ganó `_relativas` y
>   `_bytes_guardados`, que van por índice de clip y por eso se limpian en
>   `load_clips` y se corren en `_on_bin_quitado`, como los otros seis.
> - **`arrancar` y `_restore_session` se borraron**, no se conservaron: con
>   `main()` arrancando en la pantalla de inicio y la sesión vieja migrando
>   sola, quedaban sin un solo llamador. Sus tests se apuntaron a
>   `abrir_proyecto`/`_poblar_ventana`. Con ellos murió el cartel de
>   «¿Recuperar la sesión sin terminar?», que la migración reemplaza.
> - La marca de «ya se migró» es que la sesión vieja se **aparta** como
>   `sesion.migrada.json` —no se borra, y se aparta recién después de que el
>   `.cvproj` está escrito—. Sin marca, cada arranque volvería a convertirla y
>   pisaría el trabajo del día con el de antes.
> - `proyecto.es_proyecto` exige `version` **o** `clips`, no las dos: los
>   proyectos convertidos de la sesión vieja no traen `version`.
> **Segunda ronda, misma fecha, tras la revisión.** 1288 tests, **0 fallos
> sobre 40 corridas**. Ocho arreglos, uno por commit:
>
> - **El peor**: `_tomar` volvía a abrir el primer clip después de que
>   `load_clips` ya lo había abierto por `ruta_de_reproduccion` —con su proxy y
>   arrancando al 25%—. La segunda apertura iba con la ruta en crudo: el clip
>   donde aterrizas **cada vez** que abres un proyecto quedaba a 530 ms por
>   cuadro atrás en vez de 22. Una fase entera de trabajo borrada en silencio
>   por una línea heredada del `main()` viejo.
> - **mpv no se apagaba.** Hasta ahora la ventana vivía hasta que moría el
>   proceso; con el `Coordinador` se destruye en caliente y nadie liberaba el
>   contexto de render ni terminaba mpv. Las 40 corridas verdes no decían nada
>   al respecto: todos los tests usan un mpv falso. Verificado a mano con mpv y
>   OpenGL reales sobre `sample-media/clips`, tres proyectos seguidos con el
>   visor a la vista: contexto de render creado y liberado las tres veces, y
>   los hilos vuelven a 1 tras cada cierre.
> - **El autoguardado fallaba en silencio** y la barra seguía diciendo
>   «Guardado hace 3 s». Antes el archivo era de la carpeta del usuario,
>   siempre escribible; ahora lo elige Bruno y puede estar en un disco que se
>   desconecta. Y `crear_proyecto` prometía «ya guardado» sin comprobarlo.
> - **La migración corría sin red**, antes de que existiera una ventana: un
>   `~/Documents` bloqueado por TCC dejaba a Bruno sin poder entrar.
> - **Un `.cvproj` con clips malformados abortaba el proceso** —la excepción
>   salía dentro de un slot de Qt— con solo hacerle clic.
> - **El escritor era doble**: `proyecto.guardar` y `autosave.save_session`, y
>   el que escribía el archivo de Bruno el 99% del tiempo era el que no
>   limpiaba su temporal. `save_session` murió.
> - **El `stat()` volvió al hilo del guardado** (`proyecto.con_pesos_medidos`).
>   El caso que duele no es el volumen desmontado sino el **montado e
>   incomunicado**: 109 stats en serie, cada uno hasta el timeout. Como la
>   ventana ya no mide, el que acumula los pesos es el archivo: el guardado
>   relee lo que había antes de escribir.
> - **El modal se fue**: el aviso vive en la pantalla de inicio, como pedía el
>   spec. Mirado en pixel.
> - Y cuatro baratas: las relativas se calculan al migrar (son léxicas, no
>   necesitan la media), la sesión apartada no pisa una anterior, la sesión se
>   lee una sola vez, y la fecha de un reciente es la de la última vez que
>   trabajaste y no la de abrir —que es por la que se ordena la lista—.

---

# FASE 6 — El aviso de media faltante

### Tarea 11: avisar por bin y reconectar

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py`
- Modificar: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_main_window_revinculo.py` **(nuevo)**

- [x] **Paso 1: tests**

```python
def test_al_abrir_avisa_cuantos_faltan_por_bin(qtbot, ventana):
    ventana.load_clips([_clip(0, "/no/existe/A.MP4"), _clip(1, "/no/existe/B.MP4")])
    ventana.bins.agregar("Dron", Path("/no/existe"), [0, 1])

    ventana.revisar_media()

    assert ventana.aviso_de_media.isVisible()
    assert "Dron" in ventana.aviso_de_media.text()
    assert "2" in ventana.aviso_de_media.text()


def test_reconectar_reescribe_las_rutas_y_guarda(qtbot, ventana, tmp_path):
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    archivo = nueva / "A.MP4"
    archivo.write_bytes(b"x" * 500)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0])
    ventana._bytes_guardados = {0: 500}
    ventana._relativas = {0: "A.MP4"}

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.clips[0].ruta == archivo
    assert ventana.bins.origen_de("Dron") == nueva


def test_lo_que_no_confirma_no_se_engancha_y_se_dice(qtbot, ventana, tmp_path):
    """El caso de la segunda tarjeta de la misma camara: mismo nombre,
    otro material."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "A.MP4").write_bytes(b"x" * 111)      # peso equivocado
    ventana.load_clips([_clip(0, "/viejo/A.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0])
    ventana._bytes_guardados = {0: 500}
    ventana._relativas = {0: "A.MP4"}

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.clips[0].ruta == Path("/viejo/A.MP4")   # sin tocar
    assert "no coincide" in ventana.aviso_de_media.text().lower()
```

- [x] **Paso 2: correr y ver que fallan** — *no se hizo así, ver abajo*

- [x] **Paso 3: implementar**

Una barra de aviso arriba de la hoja, no un modal: Bruno tiene que poder ver
su proyecto mientras decide. Un renglón por bin con clips faltantes, con su
botón «Buscar…» que abre un `QFileDialog.getExistingDirectory`. Al reconectar:
reescribir `clip.ruta`, actualizar el origen del bin, volver a pedir portadas
**solo de los reconectados**, y guardar.

> **Cuidados, todos con historia en este proyecto:**
> - Volver a pedir portadas **con el alcance acotado**, no `_schedule_thumbnails()`
>   pelado: sin acotar sube la generación, invalida lo que está en vuelo y
>   encola trabajos duplicados sobre el mismo socket.
> - Reconectar **no mueve índices**, así que nada de lo indexado por clip hay
>   que correrlo. Si te ves corriendo índices, algo está mal.
> - Nada de `exec()` fuera de los selectores del sistema.

- [x] **Paso 4: verificación visual — obligatoria**

`grab()` del aviso con dos bins faltantes y del estado después de reconectar
uno. **Mirar los PNG**: que el aviso no tape la primera fila de tarjetas y que
el texto quepa a 1027 px.

- [x] **Paso 5: commit** — `af4341d`, `6a230b5`, `f28f014`

#### Lo que se hizo distinto de lo que decía este plan

Todo esto es desvío, y se anota para que la próxima sesión no lo tome por
descuido:

1. **El paso 2 de TDD no se cumplió.** Los tests se escribieron contra una
   implementación ya diseñada y se corrieron por primera vez con el código
   puesto: pasaron en verde de una. Nunca se vio el rojo, así que no hay
   prueba de que los tests fallen sin la implementación. Lo que sí los
   respalda es que afirman los **textos exactos** de los cuatro mensajes,
   que no salen de ningún lado por casualidad.
2. **La barra vive en su propio módulo**, `ui/aviso_de_media.py`, con
   `tests/ui/test_aviso_de_media.py`. El plan la ponía dentro de
   `main_window.py`, que ya tiene 2 700 líneas; los widgets de este repo
   viven en archivos propios y se respetó eso.
3. **`isVisible()` → `isHidden()`** en los tests. Bajo `offscreen` y sin
   `show()`, `isVisible()` es `False` para cualquier hijo, así que el test
   del plan nunca habría pasado. `isHidden()` es lo que usa el resto de
   `tests/ui/`.
4. **Dos archivos más de los que el plan listaba**, los dos por cosas que se
   descubrieron implementando:
   - `bins.py` — hizo falta `fijar_origen`: `sumar` solo puede SUBIR el
     origen, y el ancestro común de la carpeta vieja y la nueva es el disco
     entero.
   - `proyecto.py` — reconectar a medias borraba la ruta relativa del clip
     que seguía perdido, dejándolo sin con qué reencontrarse nunca más.
5. **La cuarta fila del layout raíz** obligó a reescribir
   `test_la_ventana_no_tiene_bandas_horizontales`: ahora afirma lo que de
   verdad importaba (que solo tres filas se VEAN), no el conteo del layout.
6. **Los clips sueltos no se avisan.** El aviso recorre bins, y un clip sin
   bin no tiene raíz contra la cual ser relativo (spec §3). Si a Bruno le
   falta un suelto, hoy no se entera por esta barra.
7. ~~**El proxy no se reencuentra.**~~ Resuelto en la segunda vuelta, abajo.

#### Segunda vuelta: lo que encontró la revisión

La revisión confirmó lo importante —**no hay camino por el que un clip quede
apuntando a un archivo ajeno**— y encontró nueve cosas. Todas arregladas,
esta vez con el rojo visto primero:

1. **`revisar_media` hacía 132 `stat` en el hilo de la interfaz, al abrir.**
   La lección ya estaba escrita en `proyecto.con_pesos_medidos` y se volvió
   a romper, encima en el peor momento: abrir un proyecto cuyo material
   puede colgar de un disco de red que ya no responde. Ahora corre en
   `_RevisionDeMediaJob`, y `_refrescar_aviso` usa lo que esa revisión
   encontró en vez de volver a barrer todos los bins en cada renombrado.
2. **En la sesión donde Bruno importa, la defensa principal estaba
   apagada.** `_bytes_guardados` solo se llenaba al abrir un `.cvproj`, así
   que reconectar en la misma sesión de la importación confirmaba **solo por
   duración** — y dos tomas del mismo largo de dos tarjetas de la Sony pasan
   ese filtro. Ahora el hilo del guardado le devuelve los pesos a la
   ventana, con guarda de generación de índices.
3. **`_proxy_candidatos` quedaba apuntando a rutas muertas** tras
   reconectar: la portada se intentaba extraer del proxy viejo, fallaba, y
   la tarjeta se quedaba en blanco sin explicación.
4. **El proxy ahora se reconecta** (el desvío 7 de arriba). Sin esto todo el
   proyecto navegaba sobre el 4K HEVC: 530 ms por cuadro contra 22, y nada
   se lo decía a Bruno porque el aviso solo miraba `clip.ruta`. Si no
   aparece bajo la carpeta que señaló, se dice, y hay un «Buscar proxies…»
   aparte — el proxy vive en su propia carpeta.
5. **Dos textos afirmaban cosas que no eran ciertas.** «No apareció en esa
   carpeta» se le decía también a los clips sin ruta relativa, que **no se
   buscaron** porque no hay con qué; y «no es el mismo video» se decía en
   tres casos y solo uno era verdad. Ahora hay cinco finales, cada uno con
   sus palabras.
6. **Dos «Buscar…» idénticos en un mismo bin.** Uno solo, el del primer
   renglón al que le sirva.
7. **El renglón verde no se iba nunca.** Se va a los 8 segundos.
8. **`test_poner_de_nuevo_no_deja_los_renglones_viejos` no probaba lo que
   decía** — afirmaba sobre el texto acumulado, no sobre los widgets. Ahora
   cuenta los hijos, y se comprobó rompiendo `_limpiar` a propósito.
9. **La regla de visibilidad vivía partida en dos** y solo una mitad sabía
   del modo solo video. Ahora la tiene entera la ventana.

Lo que **sigue** en el hilo de la interfaz: `reconectar_bin`, que recorre el
árbol de la carpeta señalada (`rglob`) y corre un `ffprobe` por candidato.
Es una acción que Bruno pide con un clic y donde una espera se entiende,
pero sobre una tarjeta de 128 GB no es gratis. Queda anotado, no resuelto.

---

## Al terminar

- [ ] Suite completa, **40 corridas contadas** con el árbol quieto, cero fallos.
- [ ] `git status` limpio, nada suelto en la raíz, ningún PNG del scratchpad
      dentro del repo.
- [ ] Recorrido a mano, con capturas **miradas**: crear proyecto → arrastrar
      material → cerrar → abrir desde recientes → mover la carpeta a otro lado →
      abrir de nuevo → reconectar → comprobar que las marcas siguen.
- [ ] Actualizar el handoff con lo **medido** y lo **supuesto**. Y decir, otra
      vez, lo que sigue sin probarse: **nadie ha abierto esto en otra Mac**.
- [ ] **NO reconstruir la `.app`** — Bruno la abre desde la terminal.

## Lo que este plan NO hace

- No copia ni mueve media.
- Nada en la nube ni dos personas a la vez.
- No se reencuentra clip por clip a mano: se reencuentra por bin.
- El manifest a Premiere no cambia.
