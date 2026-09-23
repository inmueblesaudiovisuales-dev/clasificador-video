# Proyecto en iCloud al crear un `.cvproj` (fase 1) - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que "Proyecto nuevo" arme la carpeta del proyecto dentro de la
carpeta de iCloud de Bruno (negocio → año → mes → folio), con sus 8
subcarpetas y los templates de Premiere/AE ya copiados y renombrados, y que
los proxies puedan proponerse ahí también.

**Architecture:** Un módulo nuevo, puro y sin Qt (`proyecto_colaborativo.py`),
concentra el parseo del folio y la creación de carpetas/archivos en disco.
`preferencias.py` gana una preferencia más (la carpeta raíz de iCloud, mismo
patrón que ya existe para la carpeta de proyectos de Premiere). El `.cvproj`
gana un campo nuevo (`carpeta_de_icloud`) que viaja igual que
`carpeta_de_proxies`. Toda la orquestación con diálogos vive en
`Coordinador._nuevo` (`app.py`), que ahora primero pregunta el camino
("Con folio…" o "Usar una carpeta a mano") antes de construir la ventana.

**Tech Stack:** Python 3, PySide6 (Qt), pytest + pytest-qt, `QT_QPA_PLATFORM=offscreen`.

**Spec:** `docs/superpowers/specs/2026-09-23-proyecto-colaborativo-icloud-design.md`

---

## Cómo correr la suite completa

En cada tarea que dice "corre la suite completa":

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Y para un archivo/test puntual mientras se trabaja esa tarea:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ruta/al/archivo.py -q
```

---

### Task 1: `proyecto_colaborativo.py` — parsear el folio y armar la ruta

**Files:**
- Create: `src/clasificador_video/proyecto_colaborativo.py`
- Test: `tests/test_proyecto_colaborativo.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
"""Parseo del folio y armado de la ruta del proyecto en iCloud, sin Qt ni
red -- spec 2026-09-23-proyecto-colaborativo-icloud-design.md."""
from pathlib import Path

from clasificador_video import proyecto_colaborativo as colab


def test_partir_folio_negocio_iav():
    partido = colab.partir_folio("IAV-2609.10-A")

    assert partido.negocio == "IAV"
    assert partido.anio == 2026
    assert partido.mes == 9


def test_partir_folio_negocio_pi():
    partido = colab.partir_folio("PI-2701.05-B")

    assert partido.negocio == "PI"
    assert partido.anio == 2027
    assert partido.mes == 1


def test_partir_folio_negocio_desconocido_no_parsea():
    assert colab.partir_folio("XYZ-2609.10-A") is None


def test_partir_folio_mes_invalido_no_parsea():
    assert colab.partir_folio("IAV-2613.10-A") is None


def test_partir_folio_formato_raro_no_parsea():
    assert colab.partir_folio("no es un folio") is None
    assert colab.partir_folio("") is None


def test_ruta_del_proyecto_arma_negocio_anio_mes_folio(tmp_path):
    raiz = tmp_path

    ruta = colab.ruta_del_proyecto(raiz, "IAV-2609.10-A")

    assert ruta == (
        raiz / "01. IAV" / "2026" / "09. Septiembre" / "IAV-2609.10-A"
    )


def test_ruta_del_proyecto_negocio_pi(tmp_path):
    ruta = colab.ruta_del_proyecto(tmp_path, "PI-2701.05-B")

    assert ruta == (
        tmp_path / "02. PI" / "2027" / "01. Enero" / "PI-2701.05-B"
    )


def test_ruta_del_proyecto_folio_invalido_da_none(tmp_path):
    assert colab.ruta_del_proyecto(tmp_path, "no es un folio") is None
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto_colaborativo.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'clasificador_video.proyecto_colaborativo'`

- [ ] **Step 3: Escribir el módulo**

```python
"""Armar la carpeta de un proyecto colaborativo dentro de la carpeta de
iCloud de Bruno: negocio -> año -> mes -> folio, con sus 8 subcarpetas y
los templates de Premiere/AE copiados y renombrados.

Spec: docs/superpowers/specs/2026-09-23-proyecto-colaborativo-icloud-design.md

Sin Qt: esto solo parsea texto y toca el disco. Quien pregunta y confirma
con Bruno vive en `app.py` (`Coordinador._nuevo`).
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from clasificador_video import proyecto

# El folio ya es el nombre del proyecto en Clipify (ver `buscar_prproj.py`).
# Formato confirmado con Bruno: NEGOCIO-AAMM.DD-LETRA, por ejemplo
# "IAV-2609.10-A" -> negocio IAV, año 2026, mes 09, día 10, primer
# proyecto del día. El día y la letra no hacen falta para armar la ruta
# -- solo negocio, año y mes -- así que el patrón no los valida más allá
# de que existan con el formato correcto.
_PATRON_FOLIO = re.compile(r"^(IAV|PI)-(\d{2})(\d{2})\.(\d{2})-.+$")

# Nombre exacto de la carpeta de negocio dentro de la raíz de iCloud, tal
# como ya existen en el disco de Bruno.
NEGOCIOS = {"IAV": "01. IAV", "PI": "02. PI"}

# Nombre exacto de cada carpeta de mes, tal como ya existen en el disco de
# Bruno (índice 0 = enero).
MESES = (
    "01. Enero", "02. Febrero", "03. Marzo", "04. Abril", "05. Mayo",
    "06. Junio", "07. Julio", "08. Agosto", "09. Septiembre",
    "10. Octubre", "11. Noviembre", "12. Diciembre",
)

# Hermana de las carpetas de negocio, dentro de la raíz de iCloud.
CARPETA_TEMPLATES = "03. Templates"
TEMPLATE_PREMIERE_NOMBRE = "TemplatePremiere.prproj"
TEMPLATE_AE_NOMBRE = "TemplateAE.aep"

# Las 8 subcarpetas de todo proyecto colaborativo, en este orden. Los
# nombres son literales -- tal como los escribió Bruno, con sus mayúsculas
# y sin acentos donde él no los puso -- porque son carpetas que él ve en
# Finder todos los días.
SUBCARPETAS = (
    "01. Proyecto premiere",
    "02. Proyecto AE",
    "03. Proxies",
    "04. Musica",
    "05. Logos y graficos",
    "06. Voz IA",
    "07. guiones",
    "08. Clipify",
)
CARPETA_PREMIERE = SUBCARPETAS[0]
CARPETA_AE = SUBCARPETAS[1]
CARPETA_PROXIES = SUBCARPETAS[2]
CARPETA_CLIPIFY = SUBCARPETAS[7]


@dataclass(frozen=True)
class FolioPartido:
    negocio: str  # "IAV" o "PI"
    anio: int     # año completo, p.ej. 2026
    mes: int      # 1-12


def partir_folio(folio: str) -> FolioPartido | None:
    """El negocio, año y mes de un folio, o `None` si el texto no calza
    con el patrón (negocio que no es IAV/PI, o mes fuera de 1-12).

    No se adivina: un folio que no parsea se le devuelve a Bruno para que
    lo corrija, no se intenta interpretar a la fuerza.
    """
    m = _PATRON_FOLIO.match(folio.strip())
    if m is None:
        return None
    negocio, aa, mm = m.group(1), m.group(2), m.group(3)
    mes = int(mm)
    if not 1 <= mes <= 12:
        return None
    return FolioPartido(negocio=negocio, anio=2000 + int(aa), mes=mes)


def ruta_del_proyecto(raiz: Path, folio: str) -> Path | None:
    """La ruta completa de la carpeta del proyecto dentro de `raiz` (la
    carpeta raíz de iCloud que Bruno configuró). `None` si el folio no
    parsea.

    Esta ruta puede no existir todavía en disco -- armarla es puro cálculo
    de texto, no toca el disco. Quien la crea es `crear_carpeta_de_proyecto`.
    """
    partido = partir_folio(folio)
    if partido is None:
        return None
    return (
        raiz / NEGOCIOS[partido.negocio] / str(partido.anio)
        / MESES[partido.mes - 1] / folio
    )


@dataclass(frozen=True)
class ResultadoDeCreacion:
    carpeta_proyecto: Path
    ruta_cvproj: Path
    ruta_prproj: Path
    ruta_aep: Path


def crear_carpeta_de_proyecto(carpeta_proyecto: Path, carpeta_templates: Path,
                              folio: str) -> ResultadoDeCreacion:
    """Crea la carpeta del folio con sus 8 subcarpetas y copia los templates
    ya renombrados con el folio.

    No crea nada a medias: revisa TODO antes de tocar el disco.

    `FileNotFoundError` -- con la ruta que faltó como mensaje -- si
    `carpeta_proyecto.parent` no existe (la carpeta de negocio/año/mes que
    Bruno arma a mano todavía no llega a ese mes) o si falta algún
    template.

    `FileExistsError` -- con la ruta que ya existía -- si la carpeta del
    folio ya existe. Bruno decide qué hacer con ella; esta función nunca
    escribe encima de algo que ya estaba ahí.
    """
    if not carpeta_proyecto.parent.is_dir():
        raise FileNotFoundError(str(carpeta_proyecto.parent))
    if carpeta_proyecto.exists():
        raise FileExistsError(str(carpeta_proyecto))
    template_premiere = carpeta_templates / TEMPLATE_PREMIERE_NOMBRE
    template_ae = carpeta_templates / TEMPLATE_AE_NOMBRE
    if not template_premiere.is_file():
        raise FileNotFoundError(str(template_premiere))
    if not template_ae.is_file():
        raise FileNotFoundError(str(template_ae))

    carpeta_proyecto.mkdir()
    for nombre in SUBCARPETAS:
        (carpeta_proyecto / nombre).mkdir()

    ruta_prproj = carpeta_proyecto / CARPETA_PREMIERE / f"{folio}.prproj"
    ruta_aep = carpeta_proyecto / CARPETA_AE / f"{folio}.aep"
    shutil.copyfile(template_premiere, ruta_prproj)
    shutil.copyfile(template_ae, ruta_aep)
    ruta_cvproj = carpeta_proyecto / CARPETA_CLIPIFY / f"{folio}{proyecto.EXTENSION}"

    return ResultadoDeCreacion(
        carpeta_proyecto=carpeta_proyecto,
        ruta_cvproj=ruta_cvproj,
        ruta_prproj=ruta_prproj,
        ruta_aep=ruta_aep,
    )
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto_colaborativo.py -q`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proyecto_colaborativo.py tests/test_proyecto_colaborativo.py
git commit -m "$(cat <<'EOF'
Agregar proyecto_colaborativo: parsear folio y armar su ruta en iCloud

Primer pedazo de la fase 1 (spec 2026-09-23): de un folio como
IAV-2609.10-A se saca el negocio, año y mes, y con eso se arma la
ruta dentro de la carpeta de iCloud de Bruno. Sin Qt, sin red.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `proyecto_colaborativo.crear_carpeta_de_proyecto` — crear carpetas y copiar templates

**Files:**
- Modify: `src/clasificador_video/proyecto_colaborativo.py` (ya tiene la función, del Task 1)
- Test: `tests/test_proyecto_colaborativo.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Agregar al final de `tests/test_proyecto_colaborativo.py`:

```python
def _con_templates(tmp_path):
    templates = tmp_path / "03. Templates"
    templates.mkdir()
    (templates / colab.TEMPLATE_PREMIERE_NOMBRE).write_text("premiere vacio")
    (templates / colab.TEMPLATE_AE_NOMBRE).write_text("ae vacio")
    return templates


def test_crear_carpeta_de_proyecto_crea_las_8_subcarpetas(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = _con_templates(tmp_path)

    colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    for nombre in colab.SUBCARPETAS:
        assert (carpeta_proyecto / nombre).is_dir()


def test_crear_carpeta_de_proyecto_copia_y_renombra_los_templates(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = _con_templates(tmp_path)

    resultado = colab.crear_carpeta_de_proyecto(
        carpeta_proyecto, templates, "IAV-2609.10-A")

    ruta_prproj = carpeta_proyecto / "01. Proyecto premiere" / "IAV-2609.10-A.prproj"
    ruta_aep = carpeta_proyecto / "02. Proyecto AE" / "IAV-2609.10-A.aep"
    assert ruta_prproj.read_text() == "premiere vacio"
    assert ruta_aep.read_text() == "ae vacio"
    assert resultado.ruta_prproj == ruta_prproj
    assert resultado.ruta_aep == ruta_aep
    assert resultado.ruta_cvproj == (
        carpeta_proyecto / "08. Clipify" / "IAV-2609.10-A.cvproj"
    )


def test_crear_carpeta_de_proyecto_ya_existe_no_toca_nada(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    carpeta_proyecto.mkdir()
    (carpeta_proyecto / "Musica").mkdir()  # algo que Bruno ya puso a mano
    templates = _con_templates(tmp_path)

    with pytest.raises(FileExistsError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    # lo que ya había sigue exactamente igual
    assert [p.name for p in carpeta_proyecto.iterdir()] == ["Musica"]


def test_crear_carpeta_de_proyecto_sin_carpeta_de_mes_no_la_inventa(tmp_path):
    """La carpeta de negocio/año/mes la arma Bruno a mano de antemano --si
    falta, no se crea sola."""
    carpeta_proyecto = tmp_path / "09. Septiembre" / "IAV-2609.10-A"
    templates = _con_templates(tmp_path)

    with pytest.raises(FileNotFoundError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    assert not carpeta_proyecto.exists()


def test_crear_carpeta_de_proyecto_sin_template_premiere_no_crea_nada(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = tmp_path / "03. Templates"
    templates.mkdir()
    (templates / colab.TEMPLATE_AE_NOMBRE).write_text("ae vacio")

    with pytest.raises(FileNotFoundError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    assert not carpeta_proyecto.exists()


def test_crear_carpeta_de_proyecto_sin_template_ae_no_crea_nada(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = tmp_path / "03. Templates"
    templates.mkdir()
    (templates / colab.TEMPLATE_PREMIERE_NOMBRE).write_text("premiere vacio")

    with pytest.raises(FileNotFoundError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    assert not carpeta_proyecto.exists()
```

Y agregar `import pytest` al inicio del archivo si no está.

- [ ] **Step 2: Correr las pruebas y comprobar que pasan**

`crear_carpeta_de_proyecto` ya se escribió completa en el Task 1, así que
estas pruebas deben pasar de una vez -- este paso es la comprobación, no
hay implementación nueva que escribir.

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto_colaborativo.py -q`
Expected: PASS (15 tests en total)

Si algo falla, ajustar `crear_carpeta_de_proyecto` del Task 1 hasta que
pase -- no cambiar las pruebas para acomodar un bug.

- [ ] **Step 3: Commit**

```bash
git add tests/test_proyecto_colaborativo.py
git commit -m "$(cat <<'EOF'
Probar crear_carpeta_de_proyecto: subcarpetas, templates y sus errores

Cubre los tres casos que el spec pide que no dejen nada a medias: la
carpeta del folio ya existe, falta la carpeta de negocio/año/mes, y
falta algún template.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `preferencias.py` — la carpeta raíz de iCloud

**Files:**
- Modify: `src/clasificador_video/preferencias.py`
- Test: `tests/test_preferencias.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Agregar al final de `tests/test_preferencias.py`:

```python
def test_carpeta_raiz_icloud_vacia_por_defecto(tmp_path):
    ruta = tmp_path / "preferencias.json"
    assert mod.carpeta_raiz_icloud(ruta) is None


def test_guardar_y_leer_carpeta_raiz_icloud(tmp_path):
    ruta = tmp_path / "preferencias.json"
    carpeta = tmp_path / "01. Proyectos 2026 IAV y PI"

    mod.guardar_carpeta_raiz_icloud(carpeta, ruta)

    assert mod.carpeta_raiz_icloud(ruta) == carpeta
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_preferencias.py -q`
Expected: FAIL con `AttributeError: module 'clasificador_video.preferencias' has no attribute 'carpeta_raiz_icloud'`

- [ ] **Step 3: Agregar las funciones**

Al final de `src/clasificador_video/preferencias.py`:

```python


def carpeta_raiz_icloud(ruta: Path | None = None) -> Path | None:
    """La carpeta raíz de iCloud donde Bruno ya tiene armado
    `01. IAV/`, `02. PI/` y `03. Templates/` (spec
    2026-09-23-proyecto-colaborativo-icloud-design.md). `None` hasta que
    la configure -- sin ella, "Proyecto nuevo" con folio no puede armar
    la ruta y avisa que hace falta ponerla en Configuración."""
    valor = _leer_todo(ruta).get("carpeta_raiz_icloud")
    return Path(valor) if valor else None


def guardar_carpeta_raiz_icloud(carpeta: Path, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = _leer_todo(ruta)
    datos["carpeta_raiz_icloud"] = str(carpeta)
    destino.write_text(json.dumps(datos), encoding="utf-8")
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_preferencias.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/preferencias.py tests/test_preferencias.py
git commit -m "$(cat <<'EOF'
Agregar la preferencia de la carpeta raíz de iCloud

Mismo patrón que carpeta_de_proyectos_premiere: se configura una vez
en Configuración y no queda fija en el código.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `proyecto.a_dict` — el campo `carpeta_de_icloud`

**Files:**
- Modify: `src/clasificador_video/proyecto.py:128-227` (función `a_dict`)
- Test: `tests/test_proyecto.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Agregar en `tests/test_proyecto.py`, junto a
`test_la_carpeta_de_proxies_elegida_se_guarda_en_el_proyecto`:

```python
def test_la_carpeta_de_icloud_se_guarda_en_el_proyecto():
    data = a_dict(proyecto="P", rooms=[], clips=[], bins=BinTree(),
                  tamanos={}, duraciones={}, rotaciones={},
                  carpeta_de_icloud=Path(
                      "/Users/bruno/.../01. IAV/2026/09. Septiembre/IAV-2609.10-A"))

    assert data["carpeta_de_icloud"] == (
        "/Users/bruno/.../01. IAV/2026/09. Septiembre/IAV-2609.10-A"
    )


def test_un_proyecto_que_nunca_fue_colaborativo_no_guarda_carpeta_de_icloud():
    data = a_dict(proyecto="P", rooms=[], clips=[], bins=BinTree(),
                  tamanos={}, duraciones={}, rotaciones={})

    assert data["carpeta_de_icloud"] is None
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -q`
Expected: FAIL con `TypeError: a_dict() got an unexpected keyword argument 'carpeta_de_icloud'`

- [ ] **Step 3: Agregar el parámetro y el campo**

En `src/clasificador_video/proyecto.py`, la firma de `a_dict` (línea 128):

```python
def a_dict(proyecto: str, rooms: list[str], clips: list, bins,
           tamanos: dict, duraciones: dict, rotaciones: dict,
           bytes_conocidos: dict | None = None,
           relativas_conocidas: dict | None = None,
           agrupar_por_cuarto: bool = True,
           modo_horizontal: bool = False,
           carpeta_de_proxies: Path | None = None,
           carpeta_de_icloud: Path | None = None,
           guia: dict | None = None,
           entrega: dict | None = None,
           units: list[str] | None = None,
           rooms_por_unidad: dict[str, list[str]] | None = None,
           unidades_colapsadas: list[str] | None = None,
           guias_por_unidad: dict[str, dict] | None = None) -> dict:
```

Y dentro del `return {...}`, justo después de la llave `"carpeta_de_proxies"`:

```python
        "carpeta_de_proxies": (str(carpeta_de_proxies)
                               if carpeta_de_proxies is not None else None),
        # La carpeta del proyecto en iCloud (spec
        # 2026-09-23-proyecto-colaborativo-icloud-design.md). `None` es un
        # proyecto creado "a mano" o de antes de esta fase -- mismo
        # criterio que `carpeta_de_proxies`.
        "carpeta_de_icloud": (str(carpeta_de_icloud)
                              if carpeta_de_icloud is not None else None),
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proyecto.py tests/test_proyecto.py
git commit -m "$(cat <<'EOF'
Guardar carpeta_de_icloud en el .cvproj

Mismo tratamiento que carpeta_de_proxies: None en los proyectos que
nunca la tuvieron, así los de antes de esta fase abren igual que
siempre.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `MainWindow` — estado `carpeta_de_icloud`

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py` (junto a `_carpeta_de_proxies`, línea ~945, y `carpeta_de_proxies`/`set_carpeta_de_proxies`, línea ~3510-3523, y `_datos_del_proyecto`, línea ~2757)
- Test: `tests/ui/test_main_window_carpeta_de_proxies.py`

- [ ] **Step 1: Escribir la prueba que falla**

Agregar en `tests/ui/test_main_window_carpeta_de_proxies.py`, junto a
`test_la_ventana_arranca_sin_carpeta_elegida`:

```python
def test_la_ventana_arranca_sin_carpeta_de_icloud(ventana):
    assert ventana.carpeta_de_icloud is None


def test_set_carpeta_de_icloud_la_guarda(ventana, tmp_path):
    carpeta = tmp_path / "IAV-2609.10-A"

    ventana.set_carpeta_de_icloud(carpeta)

    assert ventana.carpeta_de_icloud == carpeta


def test_la_carpeta_de_icloud_viaja_con_el_proyecto(ventana, tmp_path):
    carpeta = tmp_path / "IAV-2609.10-A"
    ventana.set_carpeta_de_icloud(carpeta)

    data = ventana._datos_del_proyecto()

    assert data["carpeta_de_icloud"] == str(carpeta)
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_carpeta_de_proxies.py -q`
Expected: FAIL con `AttributeError: 'MainWindow' object has no attribute 'carpeta_de_icloud'`

- [ ] **Step 3: Agregar el estado, el getter/setter, y el wiring**

En `src/clasificador_video/ui/main_window.py`, junto a la línea que dice
`self._carpeta_de_proxies: Path | None = None` (cerca de la línea 945):

```python
        self._carpeta_de_proxies: Path | None = None
        # La carpeta del proyecto en iCloud, si se creó con el flujo de
        # "Con folio…" (spec 2026-09-23-proyecto-colaborativo-icloud-design.md).
        # `None` en cualquier proyecto creado "a mano" o de antes de esta fase.
        self._carpeta_de_icloud: Path | None = None
```

Junto a `carpeta_de_proxies`/`set_carpeta_de_proxies` (cerca de la línea 3510):

```python
    @property
    def carpeta_de_proxies(self) -> Path | None:
        """Donde van los proxies NUEVOS, o `None` si nunca se pregunto."""
        return self._carpeta_de_proxies

    def set_carpeta_de_proxies(self, carpeta: Path | None) -> None:
        """La elige Bruno y se guarda con el proyecto.

        Cambiarla **no mueve ni un archivo**: los que ya existen se siguen
        encontrando donde esten --`proxy_gen.carpetas_de_proxies` mira los
        tres lugares-- y esto solo decide donde se escriben los proximos.
        """
        self._carpeta_de_proxies = Path(carpeta) if carpeta is not None else None
        self._autosave()

    @property
    def carpeta_de_icloud(self) -> Path | None:
        """La carpeta del proyecto en iCloud, o `None` si este proyecto no
        se creó con el flujo de "Con folio…"."""
        return self._carpeta_de_icloud

    def set_carpeta_de_icloud(self, carpeta: Path | None) -> None:
        self._carpeta_de_icloud = Path(carpeta) if carpeta is not None else None
        self._autosave()
```

Y en `_datos_del_proyecto` (cerca de la línea 2757), junto a
`carpeta_de_proxies=self._carpeta_de_proxies,`:

```python
            carpeta_de_proxies=self._carpeta_de_proxies,
            carpeta_de_icloud=self._carpeta_de_icloud,
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_carpeta_de_proxies.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_carpeta_de_proxies.py
git commit -m "$(cat <<'EOF'
MainWindow: estado carpeta_de_icloud, igual que carpeta_de_proxies

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: cargar `carpeta_de_icloud` al abrir un proyecto

**Files:**
- Modify: `src/clasificador_video/app.py:173-238` (función `_poblar_ventana`)
- Test: `tests/test_app.py`

- [ ] **Step 1: Escribir la prueba que falla**

Buscar en `tests/test_app.py` la función `_proyecto_en` (helper que ya
existe, usado por varios tests de `abrir_proyecto`) y agregar junto a los
tests de `abrir_proyecto`:

```python
def test_abrir_proyecto_recupera_la_carpeta_de_icloud(tmp_path):
    ruta = _proyecto_en(tmp_path, extra={
        "carpeta_de_icloud": str(tmp_path / "IAV-2609.10-A"),
    })

    ventana = abrir_proyecto(ruta, video_factory=_FakeMpv,
                             recientes_path=tmp_path / "r.json")

    assert ventana.carpeta_de_icloud == tmp_path / "IAV-2609.10-A"
    ventana.close()


def test_abrir_proyecto_sin_carpeta_de_icloud_queda_en_none(tmp_path):
    ruta = _proyecto_en(tmp_path)

    ventana = abrir_proyecto(ruta, video_factory=_FakeMpv,
                             recientes_path=tmp_path / "r.json")

    assert ventana.carpeta_de_icloud is None
    ventana.close()
```

`_proyecto_en(tmp_path, extra=None, nombre="P.cvproj")` ya existe en
`tests/test_app.py` (línea 77) con ese mismo parámetro `extra` -- es el
mismo patrón que ya usa `test_ya_entregado_pedido_cierra_la_entrega_y_refresca`
para `entrega`.

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k carpeta_de_icloud -q`
Expected: FAIL (`assert None == PosixPath(...)`)

- [ ] **Step 3: Cargarla en `_poblar_ventana`**

En `src/clasificador_video/app.py`, dentro de `_poblar_ventana` (línea
173), junto a las líneas 236-237
(`guardada = data.get("carpeta_de_proxies")` /
`window.set_carpeta_de_proxies(...)`):

```python
    guardada = data.get("carpeta_de_proxies")
    window.set_carpeta_de_proxies(Path(guardada) if guardada else None)
    guardada_icloud = data.get("carpeta_de_icloud")
    window.set_carpeta_de_icloud(Path(guardada_icloud) if guardada_icloud else None)
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k carpeta_de_icloud -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "$(cat <<'EOF'
Recuperar carpeta_de_icloud al abrir un proyecto existente

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `crear_proyecto` acepta `carpeta_de_icloud`

**Files:**
- Modify: `src/clasificador_video/app.py:283-309` (función `crear_proyecto`)
- Test: `tests/test_app.py`

- [ ] **Step 1: Escribir la prueba que falla**

Junto a `test_proyecto_nuevo_crea_el_archivo_de_una_vez` en
`tests/test_app.py`:

```python
def test_crear_proyecto_con_carpeta_de_icloud_la_guarda(qtbot, tmp_path):
    ruta = tmp_path / "IAV-2609.10-A.cvproj"
    carpeta_icloud = tmp_path / "IAV-2609.10-A"

    window = crear_proyecto(ruta, "IAV-2609.10-A", video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json",
                            carpeta_de_icloud=carpeta_icloud)
    qtbot.addWidget(window)

    assert window.carpeta_de_icloud == carpeta_icloud
    assert abrir(ruta)["carpeta_de_icloud"] == str(carpeta_icloud)


def test_crear_proyecto_sin_carpeta_de_icloud_queda_en_none(qtbot, tmp_path):
    ruta = tmp_path / "Casa Nueva.cvproj"

    window = crear_proyecto(ruta, "Casa Nueva", video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert window.carpeta_de_icloud is None
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k crear_proyecto_con_carpeta_de_icloud -q`
Expected: FAIL con `TypeError: crear_proyecto() got an unexpected keyword argument 'carpeta_de_icloud'`

- [ ] **Step 3: Agregar el parámetro**

En `src/clasificador_video/app.py`, la función `crear_proyecto` (línea 283):

```python
def crear_proyecto(ruta: Path, nombre: str,
                   video_factory: Callable[..., object] | None = None,
                   recientes_path: Path | None = None,
                   carpeta_de_icloud: Path | None = None) -> MainWindow | None:
    """Un proyecto nuevo, vacio y YA guardado. `None` si no se pudo escribir.

    Se escribe el archivo antes de devolver la ventana por decision de
    Bruno: nunca existe trabajo sin un archivo donde vivir. Si el disco
    donde lo puso se desconecta despues, el autoguardado avisara --pero al
    menos el proyecto existio.

    Y se COMPRUEBA que exista. Prometer «ya guardado» sin mirar dejaba una
    ventana abierta sobre un archivo que nunca se creo, y un reciente que
    salia apagado desde el primer dia: todo el trabajo de esa tarde vivia
    solo en memoria.

    `carpeta_de_icloud` -- si se pasa -- se guarda con el proyecto antes
    del primer autoguardado (spec 2026-09-23-proyecto-colaborativo-icloud-design.md).
    """
    window = MainWindow(
        project_name=nombre,
        room_selection=RoomSelection(),
        video_factory=video_factory,
    )
    window.session_path = ruta
    if carpeta_de_icloud is not None:
        window.set_carpeta_de_icloud(carpeta_de_icloud)
    window._write_autosave_now()
    window._autosave_pool.waitForDone(2000)
    if not ruta.exists():
        window.deleteLater()
        return None
    Recientes(recientes_path or RECIENTES_PATH).registrar(ruta, nombre)
    return window
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k carpeta_de_icloud -q`
Expected: PASS (los 4 tests de los Tasks 6 y 7)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "$(cat <<'EOF'
crear_proyecto: parámetro carpeta_de_icloud

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: `proxy_gen.proponer_carpeta` — priorizar la carpeta de iCloud

**Files:**
- Modify: `src/clasificador_video/proxy_gen.py:115-141` (función `proponer_carpeta`)
- Test: `tests/test_proxy_gen.py`

- [ ] **Step 1: Escribir la prueba que falla**

Junto a `test_sin_ninguna_carpeta_de_proxies_propone_la_de_siempre` en
`tests/test_proxy_gen.py`:

```python
def test_con_carpeta_de_icloud_se_propone_esa_directo(tmp_path):
    """La carpeta de iCloud del proyecto colaborativo manda sobre
    cualquier otra candidata: es la respuesta que Bruno ya dio al crear
    el proyecto (spec 2026-09-23-proyecto-colaborativo-icloud-design.md)."""
    material = tmp_path / "material"
    material.mkdir()
    (tmp_path / "07. PROXIES").mkdir()  # candidata que existiría hoy
    carpeta_de_icloud = tmp_path / "IAV-2609.10-A" / "03. Proxies"

    assert proxy_gen.proponer_carpeta(
        material, carpeta_de_icloud) == carpeta_de_icloud


def test_sin_carpeta_de_icloud_se_comporta_como_antes(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (tmp_path / "07. PROXIES").mkdir()

    assert proxy_gen.proponer_carpeta(material, None) == tmp_path / "07. PROXIES"
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py -k carpeta_de_icloud -q`
Expected: FAIL con `TypeError: proponer_carpeta() takes 1 positional argument but 2 were given`

- [ ] **Step 3: Agregar el parámetro**

En `src/clasificador_video/proxy_gen.py`, la función `proponer_carpeta`
(línea 115):

```python
def proponer_carpeta(carpeta_del_bin: Path,
                     carpeta_de_icloud: Path | None = None) -> Path:
    """Que carpeta ofrecerle a Bruno, para que la pregunta llegue contestada.

    Si el proyecto tiene una carpeta de iCloud vinculada
    (`carpeta_de_icloud`, spec 2026-09-23), esa se propone DIRECTO, antes
    de mirar nada más junto al material: es la respuesta que Bruno ya dio
    al crear el proyecto con folio, no algo que haya que volver a adivinar.

    Sin eso, se mira si al lado del material ya hay una carpeta de proxies
    SUYA y se propone esa, con la ruta a la vista.

    `Proxies/` --la de `carpeta_por_defecto`-- queda fuera de los candidatos a
    proposito: no es una convencion de Bruno, es donde la propia app tiraba
    los archivos hasta hoy. En su proyecto real conviven las dos, y sin esta
    exclusion serian dos candidatas, no habria forma de elegir, y se
    propondria justo la que el no queria.

    Con varias candidatas NO se adivina: se propone la de siempre. Esto
    nunca escribe nada -- solo elige que enseñar.
    """
    if carpeta_de_icloud is not None:
        return carpeta_de_icloud
    padre = carpeta_del_bin.parent
    defecto = carpeta_por_defecto(carpeta_del_bin)
    try:
        candidatas = [d for d in padre.iterdir()
                      if d.is_dir() and "prox" in d.name.lower()
                      and d != carpeta_del_bin and d != defecto]
    except OSError:
        # el disco del material puede no estar montado; proponer algo es
        # mejor que reventar la pregunta entera
        candidatas = []
    return candidatas[0] if len(candidatas) == 1 else defecto
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py -q`
Expected: PASS (todo el archivo, incluidos los tests viejos de `proponer_carpeta` que siguen llamándola con un solo argumento)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proxy_gen.py tests/test_proxy_gen.py
git commit -m "$(cat <<'EOF'
proponer_carpeta: priorizar la carpeta de iCloud del proyecto

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: `MainWindow` usa la carpeta de iCloud al proponer/cambiar proxies

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py` (import en la cabecera, `_asegurar_carpeta_de_proxies` línea ~3791, `cambiar_carpeta_de_proxies` línea ~3808)
- Test: `tests/ui/test_main_window_carpeta_de_proxies.py`

- [ ] **Step 1: Escribir la prueba que falla**

Agregar en `tests/ui/test_main_window_carpeta_de_proxies.py`:

```python
def test_con_carpeta_de_icloud_la_propuesta_de_proxies_va_ahi(
        ventana, tmp_path, monkeypatch):
    _con_un_bin(ventana, tmp_path)
    (tmp_path / "07. PROXIES").mkdir()  # candidata que hoy ganaría
    carpeta_proyecto = tmp_path / "IAV-2609.10-A"
    ventana.set_carpeta_de_icloud(carpeta_proyecto)
    propuestas = []

    def espia(propuesta):
        propuestas.append(propuesta)
        return propuesta

    monkeypatch.setattr(ventana, "_preguntar_por_la_carpeta_de_proxies", espia)

    ventana.generar_proxies_de_bin("02. VIDEO DRONE")

    assert propuestas == [carpeta_proyecto / "03. Proxies"]
```

- [ ] **Step 2: Correr la prueba y comprobar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_carpeta_de_proxies.py -k carpeta_de_icloud -q`
Expected: FAIL (`assert [PosixPath('.../07. PROXIES')] == [PosixPath('.../IAV-2609.10-A/03. Proxies')]`)

- [ ] **Step 3: Importar `proyecto_colaborativo` y usar su carpeta**

En `src/clasificador_video/ui/main_window.py`, en el bloque de imports
(cerca de la línea 27-35), agregar `proyecto_colaborativo` al tuple:

```python
from clasificador_video import (
    buscar_prproj,
    drive,
    ia,
    llave,
    preferencias,
    proxy_gen,
    proyecto,
    proyecto_colaborativo,
    revinculo,
)
```

En `_asegurar_carpeta_de_proxies` (línea ~3791):

```python
    def _asegurar_carpeta_de_proxies(self, nombre_de_bin: str) -> None:
        """Pregunta si todavia no hay respuesta. Una vez por proyecto.

        No hace falta una bandera de «ya pregunte»: contestar SIEMPRE deja
        una carpeta puesta --aceptar la propuesta tambien-- asi que
        `_carpeta_de_proxies is None` ya significa «nadie contesto».
        """
        if self._carpeta_de_proxies is not None:
            return
        material = self._carpeta_de_material_del_bin(nombre_de_bin)
        if material is None:
            return
        self.set_carpeta_de_proxies(
            self._preguntar_por_la_carpeta_de_proxies(
                proxy_gen.proponer_carpeta(material, self._carpeta_de_proxies_en_icloud()))
        )
```

Y en `cambiar_carpeta_de_proxies` (línea ~3808):

```python
    def cambiar_carpeta_de_proxies(self, nombre_de_bin: str) -> None:
        """El «Cambiar carpeta de proxies…» del menu del bin.

        Vive en el menu del bin porque es donde uno va a buscar cualquier
        cosa de proxies, aunque el dato sea de todo el proyecto.
        """
        material = self._carpeta_de_material_del_bin(nombre_de_bin)
        if material is None:
            return
        actual = self._carpeta_de_proxies or proxy_gen.proponer_carpeta(
            material, self._carpeta_de_proxies_en_icloud())
        escogida = QFileDialog.getExistingDirectory(
            self, "Carpeta de proxies", str(actual))
        if escogida:
            self.set_carpeta_de_proxies(Path(escogida))
```

Y agregar el helper nuevo justo antes de `_preguntar_por_la_carpeta_de_proxies`:

```python
    def _carpeta_de_proxies_en_icloud(self) -> Path | None:
        """La subcarpeta de proxies dentro de la carpeta de iCloud del
        proyecto, o `None` si este proyecto no tiene una (spec
        2026-09-23-proyecto-colaborativo-icloud-design.md)."""
        if self._carpeta_de_icloud is None:
            return None
        return self._carpeta_de_icloud / proyecto_colaborativo.CARPETA_PROXIES
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_carpeta_de_proxies.py -q`
Expected: PASS (todo el archivo)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_carpeta_de_proxies.py
git commit -m "$(cat <<'EOF'
Proponer la carpeta de proxies de iCloud cuando el proyecto la tiene

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: `PantallaConfig` — elegir la carpeta raíz de iCloud

**Files:**
- Modify: `src/clasificador_video/ui/pantalla_config.py`
- Test: `tests/ui/test_pantalla_config.py`

- [ ] **Step 1: Escribir la prueba que falla**

Junto a `test_elegir_carpeta_premiere_emite_la_señal` en
`tests/ui/test_pantalla_config.py`:

```python
def test_elegir_carpeta_icloud_emite_la_señal(config_screen, monkeypatch, tmp_path):
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path)))

    recibido = []
    config_screen.carpeta_icloud_guardada.connect(recibido.append)
    config_screen.carpeta_icloud_button.click()

    assert recibido == [tmp_path]
```

- [ ] **Step 2: Correr la prueba y comprobar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_config.py -k carpeta_icloud -q`
Expected: FAIL con `AttributeError: 'PantallaConfig' object has no attribute 'carpeta_icloud_guardada'`

- [ ] **Step 3: Agregar la señal, los widgets y el handler**

En `src/clasificador_video/ui/pantalla_config.py`, junto a la señal
`carpeta_premiere_guardada = Signal(Path)` (línea 53):

```python
    carpeta_premiere_guardada = Signal(Path)
    carpeta_icloud_guardada = Signal(Path)
```

Después del bloque que arma `carpeta_premiere_button` (líneas 190-200),
antes del bloque de Drive:

```python
        titulo_icloud = QLabel("Carpeta de iCloud")
        titulo_icloud.setObjectName("configTitulo")
        raiz.addWidget(titulo_icloud)
        self.carpeta_icloud_label = QLabel(
            "Elige la carpeta donde ya tienes armado 01. IAV, 02. PI y "
            "03. Templates. Ahí es donde \"Proyecto nuevo\" con folio va a "
            "crear cada proyecto."
        )
        self.carpeta_icloud_label.setObjectName("configDonde")
        self.carpeta_icloud_label.setWordWrap(True)
        raiz.addWidget(self.carpeta_icloud_label)
        self.carpeta_icloud_button = QPushButton("Elegir…")
        self.carpeta_icloud_button.setObjectName("configIcloud")
        self.carpeta_icloud_button.clicked.connect(self._al_elegir_carpeta_icloud)
        raiz.addWidget(self.carpeta_icloud_button)
```

Y junto a `_al_elegir_carpeta_premiere` (línea 220):

```python
    def _al_elegir_carpeta_premiere(self) -> None:
        elegida = QFileDialog.getExistingDirectory(self, "Carpeta de proyectos de Premiere")
        if elegida:
            self.carpeta_premiere_guardada.emit(Path(elegida))

    def _al_elegir_carpeta_icloud(self) -> None:
        elegida = QFileDialog.getExistingDirectory(self, "Carpeta de iCloud")
        if elegida:
            self.carpeta_icloud_guardada.emit(Path(elegida))
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_config.py -q`
Expected: PASS (todo el archivo)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/pantalla_config.py tests/ui/test_pantalla_config.py
git commit -m "$(cat <<'EOF'
Configuración: elegir la carpeta raíz de iCloud

Mismo patrón visual que la carpeta de proyectos de Premiere.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: `Coordinador` conecta la nueva preferencia

**Files:**
- Modify: `src/clasificador_video/app.py:547-568` (`Coordinador._abrir_configuracion`)
- Test: `tests/test_app.py`

- [ ] **Step 1: Escribir la prueba que falla**

Buscar en `tests/test_app.py` un test existente de
`carpeta_premiere_guardada` conectada al coordinador (buscar
`carpeta_premiere_guardada` en el archivo) y agregar uno análogo:

```python
def test_configuracion_guarda_la_carpeta_de_icloud(qtbot, tmp_path, monkeypatch):
    from clasificador_video import preferencias

    monkeypatch.setattr(preferencias, "RUTA", tmp_path / "preferencias.json")
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.inicio.configuracion_pedida.emit()
    carpeta = tmp_path / "01. Proyectos 2026 IAV y PI"

    coord._pantalla_config.carpeta_icloud_guardada.emit(carpeta)

    assert preferencias.carpeta_raiz_icloud() == carpeta
```

(Si ya existe en el archivo un test que hace exactamente esto para
`carpeta_premiere_guardada`, seguir su mismo patrón de monkeypatch de
`preferencias.RUTA` en vez de reinventar uno nuevo.)

- [ ] **Step 2: Correr la prueba y comprobar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k configuracion_guarda_la_carpeta_de_icloud -q`
Expected: FAIL (`preferencias.carpeta_raiz_icloud()` sigue en `None`: la señal no está conectada)

- [ ] **Step 3: Conectar la señal**

En `src/clasificador_video/app.py`, dentro de `_abrir_configuracion`
(línea ~547), junto a la conexión de `carpeta_premiere_guardada`:

```python
            self._pantalla_config.carpeta_premiere_guardada.connect(
                preferencias.guardar_carpeta_de_proyectos_premiere
            )
            self._pantalla_config.carpeta_icloud_guardada.connect(
                preferencias.guardar_carpeta_raiz_icloud
            )
```

- [ ] **Step 4: Correr la prueba y comprobar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k configuracion_guarda_la_carpeta_de_icloud -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "$(cat <<'EOF'
Conectar la carpeta de iCloud de Configuración a la preferencia

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Separar `_nuevo` en dos caminos, conservando el de siempre

Este task reorganiza `Coordinador._nuevo` SIN cambiarle el comportamiento
todavía: el camino de "a mano" queda idéntico a como es hoy, solo
renombrado. El camino "con folio" se agrega en el Task 13. Separarlo así
evita romper de un tirón todos los tests existentes de `_nuevo`.

**Files:**
- Modify: `src/clasificador_video/app.py:655-677` (`Coordinador._nuevo`)
- Test: `tests/test_app.py` (los tests existentes de `_nuevo` se actualizan aquí)

- [ ] **Step 1: Ver qué tests de `_nuevo` existen hoy**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k nuevo_pedido -q`

Anotar los nombres que salen (deben incluir al menos
`test_proyecto_nuevo_pide_donde_guardarlo`,
`test_renombrar_actualiza_recientes`,
`test_cancelar_el_selector_no_crea_nada`,
`test_al_proyecto_nuevo_se_le_pone_la_extension_si_falta`, y el que está
cerca de la línea 1082). Todos pasan hoy: son la base que no se debe
romper.

- [ ] **Step 2: Reescribir `_nuevo` con el paso de elegir camino**

En `src/clasificador_video/app.py`, reemplazar el método `_nuevo` completo
(línea 655) por:

```python
    def _nuevo(self) -> None:
        self.inicio.callar()
        eleccion = QMessageBox(self.inicio)
        eleccion.setWindowTitle("Proyecto nuevo")
        eleccion.setText("¿Cómo quieres crear el proyecto?")
        eleccion.setInformativeText(
            "\"Con folio\" arma la carpeta del proyecto sola en iCloud, con "
            "los archivos de Premiere y AE ya listos. \"Usar una carpeta a "
            "mano\" es para pruebas: el cuadro de \"guardar como\" de "
            "siempre."
        )
        con_folio = eleccion.addButton("Con folio…", QMessageBox.ButtonRole.AcceptRole)
        a_mano = eleccion.addButton(
            "Usar una carpeta a mano", QMessageBox.ButtonRole.ActionRole)
        eleccion.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        eleccion.setDefaultButton(con_folio)
        eleccion.exec()
        elegido = eleccion.clickedButton()
        if elegido is a_mano:
            self._nuevo_a_mano()
        elif elegido is con_folio:
            self._nuevo_con_folio()
        # cerrar el cuadro o "Cancelar": no crea nada

    def _nuevo_a_mano(self) -> None:
        elegido, _ = QFileDialog.getSaveFileName(
            self.inicio, "Proyecto nuevo", str(Path.home() / "Sin título"),
            f"Proyecto del clasificador (*{proyecto.EXTENSION})",
        )
        if not elegido:
            return
        ruta = Path(elegido)
        if ruta.suffix != proyecto.EXTENSION:
            # el selector de macOS deja borrar la extension, y sin ella el
            # archivo no se reconoce como proyecto la proxima vez
            ruta = ruta.with_name(ruta.name + proyecto.EXTENSION)
        ventana = crear_proyecto(ruta, ruta.stem,
                                 video_factory=self._video_factory,
                                 recientes_path=self._recientes_path)
        if ventana is None:
            self.inicio.avisar(
                f"No se pudo crear «{ruta.name}» en {ruta.parent}. Elige otra "
                "carpeta, o comprueba que el disco esté conectado."
            )
            return
        self._tomar(ventana)
```

- [ ] **Step 3: Actualizar los tests existentes para elegir "a mano" primero**

Estos tests emitían `nuevo_pedido` y esperaban que apareciera
directamente el `QFileDialog.getSaveFileName`. Ahora primero aparece el
cuadro de elegir camino, así que hay que simularlo eligiendo "Usar una
carpeta a mano" (el botón del medio, índice 1: `con_folio` es 0, `a_mano`
es 1, `Cancelar` es 2).

En `tests/test_app.py`, agregar este monkeypatch AL INICIO de cada uno de
estos tests (antes de emitir `nuevo_pedido`):
`test_proyecto_nuevo_pide_donde_guardarlo`,
`test_renombrar_actualiza_recientes`,
`test_al_proyecto_nuevo_se_le_pone_la_extension_si_falta`, y el que está
cerca de la línea 1082 (buscar `crear_proyecto(estorbo` para ubicarlo):

```python
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[1])
```

Por ejemplo, `test_proyecto_nuevo_pide_donde_guardarlo` queda:

```python
def test_proyecto_nuevo_pide_donde_guardarlo(qtbot, tmp_path, monkeypatch):
    destino = tmp_path / "Casa Nueva.cvproj"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a, **k: (str(destino), ""))
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[1])
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert destino.exists()
    assert coord.ventanas[0].project_name == "Casa Nueva"
    coord.ventanas[0].close()
```

Y `test_cancelar_el_selector_no_crea_nada` (el cuadro de elegir camino se
contesta con "a mano", y LUEGO se cancela el selector de archivo -- sigue
probando lo mismo que antes, que cancelar el selector no crea nada):

```python
def test_cancelar_el_selector_no_crea_nada(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[1])
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    assert coord.inicio.isVisible()
```

Aplicar el mismo cambio (agregar los dos `monkeypatch.setattr` de
`QMessageBox` antes de emitir `nuevo_pedido`) a los otros dos tests
listados arriba, sin tocar el resto de cada uno.

Agregar también un test nuevo para el camino de cancelar el cuadro de
elegir camino:

```python
def test_cancelar_el_cuadro_de_elegir_camino_no_crea_nada(qtbot, tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *a, **k: (llamadas.append(1), (str(tmp_path / "X.cvproj"), ""))[1])
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[2])
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    assert llamadas == []  # ni siquiera se abrió el selector de archivo
```

- [ ] **Step 4: Correr los tests de `_nuevo` y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k "nuevo_pedido or cancelar_el_cuadro_de_elegir_camino or renombrar_actualiza_recientes" -q`
Expected: PASS (todos, incluido el nuevo)

- [ ] **Step 5: Correr la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS (nada más se rompió)

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "$(cat <<'EOF'
Separar "Proyecto nuevo" en elegir camino primero

"Con folio…" y "Usar una carpeta a mano" -- este último es
exactamente el flujo de siempre, ahora detrás de un paso más. El
camino con folio se agrega en el siguiente commit.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: El camino "Con folio…"

**Files:**
- Modify: `src/clasificador_video/app.py` (imports, y agregar `_nuevo_con_folio` junto a `_nuevo_a_mano`)
- Test: `tests/test_app.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Agregar en `tests/test_app.py`, después de los tests del Task 12:

```python
# --- proyecto nuevo con folio (spec 2026-09-23) ----------------------------


def _con_raiz_icloud(monkeypatch, tmp_path):
    """Arma `01. IAV/2026/09. Septiembre/` y `03. Templates/` con los dos
    templates, y deja la preferencia apuntando ahí."""
    from clasificador_video import preferencias

    raiz = tmp_path / "icloud"
    (raiz / "01. IAV" / "2026" / "09. Septiembre").mkdir(parents=True)
    templates = raiz / "03. Templates"
    templates.mkdir()
    (templates / "TemplatePremiere.prproj").write_text("premiere vacio")
    (templates / "TemplateAE.aep").write_text("ae vacio")
    monkeypatch.setattr(preferencias, "RUTA", tmp_path / "preferencias.json")
    preferencias.guardar_carpeta_raiz_icloud(raiz)
    return raiz


def test_con_folio_crea_la_carpeta_completa_y_abre_el_proyecto(
        qtbot, tmp_path, monkeypatch):
    raiz = _con_raiz_icloud(monkeypatch, tmp_path)
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    # primer QMessageBox (elegir camino): boton[0] = "Con folio…"
    # segundo QMessageBox (confirmar ruta): boton[0] = "Crear aquí"
    respuestas = iter([0, 0])
    monkeypatch.setattr(
        QMessageBox, "clickedButton",
        lambda self: self.buttons()[next(respuestas)])
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: ("IAV-2609.10-A", True))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    carpeta = raiz / "01. IAV" / "2026" / "09. Septiembre" / "IAV-2609.10-A"
    assert (carpeta / "01. Proyecto premiere" / "IAV-2609.10-A.prproj").exists()
    assert (carpeta / "02. Proyecto AE" / "IAV-2609.10-A.aep").exists()
    assert (carpeta / "08. Clipify" / "IAV-2609.10-A.cvproj").exists()
    ventana = coord.ventanas[0]
    assert ventana.project_name == "IAV-2609.10-A"
    assert ventana.carpeta_de_icloud == carpeta
    ventana.close()


def test_con_folio_sin_raiz_configurada_avisa_y_no_crea_nada(
        qtbot, tmp_path, monkeypatch):
    from clasificador_video import preferencias

    monkeypatch.setattr(preferencias, "RUTA", tmp_path / "preferencias.json")
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()
    avisos = []
    monkeypatch.setattr(coord.inicio, "avisar", avisos.append)

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    assert avisos and "Configuración" in avisos[0]


def test_con_folio_invalido_avisa_y_no_crea_nada(qtbot, tmp_path, monkeypatch):
    _con_raiz_icloud(monkeypatch, tmp_path)
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: ("esto no es un folio", True))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()
    avisos = []
    monkeypatch.setattr(coord.inicio, "avisar", avisos.append)

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    assert avisos and "esto no es un folio" in avisos[0]


def test_con_folio_cancelar_el_input_no_crea_nada(qtbot, tmp_path, monkeypatch):
    _con_raiz_icloud(monkeypatch, tmp_path)
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("", False))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []


def test_con_folio_cancelar_la_confirmacion_no_crea_nada(
        qtbot, tmp_path, monkeypatch):
    raiz = _con_raiz_icloud(monkeypatch, tmp_path)
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    # elegir camino: boton[0] = "Con folio…"; confirmar: boton[1] = "Cancelar"
    respuestas = iter([0, 1])
    monkeypatch.setattr(
        QMessageBox, "clickedButton",
        lambda self: self.buttons()[next(respuestas)])
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: ("IAV-2609.10-A", True))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    carpeta = raiz / "01. IAV" / "2026" / "09. Septiembre" / "IAV-2609.10-A"
    assert not carpeta.exists()


def test_con_folio_carpeta_ya_existente_avisa_y_no_la_toca(
        qtbot, tmp_path, monkeypatch):
    raiz = _con_raiz_icloud(monkeypatch, tmp_path)
    carpeta = raiz / "01. IAV" / "2026" / "09. Septiembre" / "IAV-2609.10-A"
    carpeta.mkdir()
    (carpeta / "Musica").mkdir()
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    respuestas = iter([0, 0])
    monkeypatch.setattr(
        QMessageBox, "clickedButton",
        lambda self: self.buttons()[next(respuestas)])
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: ("IAV-2609.10-A", True))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()
    avisos = []
    monkeypatch.setattr(coord.inicio, "avisar", avisos.append)

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    assert [p.name for p in carpeta.iterdir()] == ["Musica"]
    assert avisos and "ya existe" in avisos[0].lower()


def test_con_folio_sin_template_avisa_y_no_crea_nada(qtbot, tmp_path, monkeypatch):
    raiz = _con_raiz_icloud(monkeypatch, tmp_path)
    (raiz / "03. Templates" / "TemplateAE.aep").unlink()
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    respuestas = iter([0, 0])
    monkeypatch.setattr(
        QMessageBox, "clickedButton",
        lambda self: self.buttons()[next(respuestas)])
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: ("IAV-2609.10-A", True))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()
    avisos = []
    monkeypatch.setattr(coord.inicio, "avisar", avisos.append)

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    carpeta = raiz / "01. IAV" / "2026" / "09. Septiembre" / "IAV-2609.10-A"
    assert not carpeta.exists()
    assert avisos and "TemplateAE.aep" in avisos[0]
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k con_folio -q`
Expected: FAIL (`AttributeError: 'Coordinador' object has no attribute '_nuevo_con_folio'`, o el `QMessageBox`/`QInputDialog` de "a mano" apareciendo porque `elegido is con_folio` no hace nada todavía)

- [ ] **Step 3: Importar `QInputDialog` y `proyecto_colaborativo` en `app.py`**

En `src/clasificador_video/app.py`, la línea de import de Qt Widgets
(línea 17):

```python
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
```

Y junto a `from clasificador_video import llave, preferencias, proyecto`
(línea 19):

```python
from clasificador_video import llave, preferencias, proyecto, proyecto_colaborativo
```

- [ ] **Step 4: Escribir `_nuevo_con_folio`**

Justo después de `_nuevo_a_mano` en `src/clasificador_video/app.py`:

```python
    def _nuevo_con_folio(self) -> None:
        raiz = preferencias.carpeta_raiz_icloud()
        if raiz is None:
            self.inicio.avisar(
                "Configura primero la carpeta de iCloud, en Configuración."
            )
            return
        folio, ok = QInputDialog.getText(
            self.inicio, "Proyecto nuevo",
            "Folio del proyecto (ej. IAV-2609.10-A):",
        )
        folio = folio.strip()
        if not ok or not folio:
            return
        carpeta_proyecto = proyecto_colaborativo.ruta_del_proyecto(raiz, folio)
        if carpeta_proyecto is None:
            self.inicio.avisar(
                f"«{folio}» no se pudo leer como folio. Revisa el formato "
                "(ej. IAV-2609.10-A) e inténtalo de nuevo."
            )
            return
        confirmar = QMessageBox(self.inicio)
        confirmar.setWindowTitle("Proyecto nuevo")
        confirmar.setText("¿Crear el proyecto aquí?")
        confirmar.setInformativeText(str(carpeta_proyecto))
        crear = confirmar.addButton("Crear aquí", QMessageBox.ButtonRole.AcceptRole)
        confirmar.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        confirmar.setDefaultButton(crear)
        confirmar.exec()
        if confirmar.clickedButton() is not crear:
            return
        carpeta_templates = raiz / proyecto_colaborativo.CARPETA_TEMPLATES
        try:
            resultado = proyecto_colaborativo.crear_carpeta_de_proyecto(
                carpeta_proyecto, carpeta_templates, folio)
        except FileExistsError:
            self.inicio.avisar(
                f"Ya existe una carpeta para «{folio}» en iCloud. Revísala "
                "tú y decide qué hacer -- Clipify no la tocó."
            )
            return
        except FileNotFoundError as exc:
            self.inicio.avisar(f"No se encontró «{exc}». No se creó nada.")
            return
        ventana = crear_proyecto(
            resultado.ruta_cvproj, folio, video_factory=self._video_factory,
            recientes_path=self._recientes_path,
            carpeta_de_icloud=resultado.carpeta_proyecto,
        )
        if ventana is None:
            self.inicio.avisar(
                f"No se pudo crear «{folio}» en {resultado.carpeta_proyecto}."
            )
            return
        self._tomar(ventana)
```

- [ ] **Step 5: Conectar el camino en `_nuevo`**

En `_nuevo` (del Task 12), cambiar el `elif` para que de verdad llame al
método nuevo -- si en el Task 12 ya quedó escrito
`elif elegido is con_folio: self._nuevo_con_folio()`, este paso no cambia
nada; si por algún motivo quedó como un `pass`, corregirlo a esa llamada.

- [ ] **Step 6: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -k con_folio -q`
Expected: PASS (los 8 tests de este task)

- [ ] **Step 7: Correr la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "$(cat <<'EOF'
Proyecto nuevo con folio: arma la carpeta en iCloud y la abre

Pide el folio, arma la ruta (negocio/año/mes/folio), la enseña antes
de crear nada, y si Bruno confirma crea las 8 subcarpetas, copia los
templates de Premiere/AE renombrados, y abre el .cvproj recién
creado en 08. Clipify. Errores (folio inválido, carpeta ya existe,
template faltante) avisan y no dejan nada a medias.

Spec: docs/superpowers/specs/2026-09-23-proyecto-colaborativo-icloud-design.md

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: Repaso final

**Files:** ninguno nuevo -- solo verificación.

- [ ] **Step 1: Correr la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS, sin ningún test saltado ni fallando.

- [ ] **Step 2: Repasar `git status`**

Run: `git status`
Expected: sin cambios sueltos -- todo lo de este plan ya se comiteó tarea
por tarea. Si algo aparece sin comitear, revisar a qué task pertenece y
comitearlo con un mensaje que siga el mismo patrón que los anteriores.

- [ ] **Step 3: Confirmar que no se tocó nada de Drive**

Run: `git log --oneline docs/superpowers/specs/2026-09-23-proyecto-colaborativo-icloud-design.md..HEAD -- src/clasificador_video/drive.py src/clasificador_video/entrega.py`

Expected: vacío -- esos dos archivos no deben aparecer en ningún commit de
este plan. La fase 2 (retirar Drive) es un plan aparte, sobre esta misma
base.
