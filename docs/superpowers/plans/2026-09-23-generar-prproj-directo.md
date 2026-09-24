# Generar el .prproj directo desde Clipify — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Este plan lo implementa Codex, no Claude.** Cada tarea está escrita para
> que se pueda ejecutar de forma aislada, con su prueba, su comando exacto y
> su resultado esperado. Nada de "similar a la tarea anterior": cada bloque
> de código está completo.

**Goal:** Que `Ctrl+E` en Clipify escriba un `.prproj` de Premiere ya
completo (bins, clips, colores, nombres, secuencias y LUT por cámara), sin
pasar por el plugin UXP, con los LUT copiados dentro de cada proyecto para
que abra igual en cualquier Mac.

**Architecture:** Un módulo de utilidades genéricas para leer/escribir el
XML comprimido de un `.prproj` y clonar un objeto con todo lo que referencia
(closure por `ObjectRef`/`ObjectURef`, no por anidamiento — así es como
Premiere conecta sus objetos, confirmado leyendo un `.prproj` real). Encima,
un generador que arma el árbol de bins, clona un clip de referencia por cada
clip real del manifiesto (reescribiendo su archivo, nombre, color y tiempo
real con datos de `ffprobe`), reusa el mismo `VideoComponentChain` de LUT ya
validado por Premiere para toda una cámara, y clona las cinco secuencias de
referencia. Todo en Python puro, sin Qt, probado con `pytest`, sin tocar
Premiere durante la corrida automática — los cambios que si o si necesitan
que Premiere los confirme están marcados como checkpoints manuales
explícitos y no se dan por buenos solo por pasar las pruebas.

**Tech Stack:** Python 3.14, `xml.etree.ElementTree` (ya en la librería
estándar, no hace falta agregar `lxml`), `gzip`, `ffprobe` (ya usado por
`probe.py`), `pytest`.

---

## Lectura obligatoria antes de empezar

- `docs/superpowers/specs/2026-09-23-generar-prproj-directo-design.md` — el
  spec aprobado por Bruno.
- `docs/superpowers/RESULTADO-2026-09-23-generacion-directa-prproj.md` — el
  spike que probó que Premiere abre un `.prproj` escrito desde afuera.
- Este plan da por hecho hechos verificados leyendo
  `/Users/brunogutierrez/Downloads/testcolorlut.prproj` (descomprimido y
  analizado con `python3`/`grep` durante el brainstorm, ver Tarea 0). No son
  suposiciones: cada estructura de XML citada abajo viene de ese archivo
  real, con línea y contenido verificados.

## Riesgo central de todo este plan, y cómo el plan lo cubre

Un `.prproj` es un solo XML donde los objetos NO se anidan por lo que
significan -- se anidan todos como hermanos sueltos bajo `<PremiereData>`, y
se conectan por dos pares de atributos:

- `ObjectID` (entero) ↔ `ObjectRef` (el mismo entero, en quien lo usa)
- `ObjectUID` (GUID) ↔ `ObjectURef` (el mismo GUID, en quien lo usa)

Clonar "una carpeta con lo de adentro" en este formato NO es copiar un
subárbol del XML -- es encontrar TODOS los objetos alcanzables desde un
objeto inicial siguiendo esos refs, copiar cada uno como un hermano nuevo
con un ID nuevo, y reescribir los refs entre los copiados. Objetos que un
objeto clonado referencia pero que NO queremos clonar (como el efecto de
LUT, que se comparte a propósito -- ver Tarea 8) son una FRONTERA explícita
que la función de clonado respeta.

Los números de tiempo (duración, frame rate, en qué frame empieza un clip)
tampoco son segundos ni fps directos: están en "ticks" de Premiere. Se
confirmó la constante real con dos clips de tu `testcolorlut.prproj`:

```
TICKS_POR_SEGUNDO = 254016000000
254016000000 / 4237833600  = 59.94005994...  (el Sony, que es 59.94 fps real)
254016000000 / 4237825133  = 59.94017969...  (el del dron, también ~59.94)
1525620096000 / 254016000000 = 6.006 segundos (duración real del clip Sony)
```

Esto importa porque clonar un clip de referencia y pegarle SOLO el nombre y
la ruta de otro archivo, sin corregir estos números, dejaría cada clip con
la duración y el frame rate del clip de la plantilla -- no del archivo real.
Por eso la Tarea 9 recalcula estos campos desde `ffprobe`, no los deja tal
cual vinieron clonados.

## File Structure

Nuevo, versionado en git:
- `recursos/premiere/TemplateColorLuts.prproj` -- plantilla con los 3 clips
  de referencia (Sony+LUT+Cerulean, DJI+LUT+Mango, Otra sin LUT+Violet), un
  bin vacío de referencia, y 5 secuencias vacías de referencia. La arma
  Bruno a mano en Premiere (Tarea 0), Codex NO la puede generar.
- `recursos/premiere/SONY-SLOG3.cube`, `recursos/premiere/DJI-DLOGM.cube` --
  copia de los `.cube` reales de Bruno.
- `src/clasificador_video/recursos.py` -- ruta a un recurso empacado, mismo
  patrón que `patron.py`.
- `src/clasificador_video/prproj_xml.py` -- leer/escribir el gzip, y el
  clonado genérico por cierre de referencias.
- `src/clasificador_video/prproj_plantilla.py` -- encuentra los archetipos
  (bin, 3 clips de referencia, 5 secuencias) dentro de la plantilla ya
  parseada, y valida que estén completos.
- `src/clasificador_video/numero_de_cuarto.py` -- puerto de
  `uxp-plugin/js/numeroDeCuarto.js`.
- `src/clasificador_video/nombre_de_clip.py` -- puerto de
  `uxp-plugin/js/nombre.js`.
- `src/clasificador_video/prproj_generador.py` -- arma el árbol de bins,
  clona cada clip real, clona las 5 secuencias, copia los `.cube` que hagan
  falta, y junta todo en `generar_prproj(...)`.

Modificado:
- `src/clasificador_video/marca_camara.py` -- se le agregan las funciones de
  texto (`marca_de_camara_del_prefijo`, `nombre_del_cuarto_con_marca`,
  `sin_marca_de_camara`), puerto de `uxp-plugin/js/marcaCamara.js`.
- `src/clasificador_video/probe.py` -- `probe_clip` regresa además
  `duration_seconds` (ya calcula `duration_seconds` internamente, solo hace
  falta exponerlo).
- `src/clasificador_video/proyecto_colaborativo.py` -- deja de copiar
  `TemplatePremiere.prproj`.
- `src/clasificador_video/ui/main_window.py` -- `Ctrl+E` pasa a generar el
  `.prproj`; el export de `manifest.json` se mueve a un menú secundario.
- `empaque/clipify.spec` -- agrega `recursos/premiere/` a `datas`.

Pruebas nuevas:
- `tests/test_recursos.py`
- `tests/test_prproj_xml.py`
- `tests/test_prproj_plantilla.py`
- `tests/test_numero_de_cuarto.py`
- `tests/test_nombre_de_clip.py`
- `tests/test_prproj_generador.py`
- `tests/ui/test_main_window_generar_prproj.py`

Pruebas modificadas:
- `tests/test_marca_camara.py`
- `tests/test_proyecto_colaborativo.py`
- `tests/test_probe.py`

---

## Tarea 0: Bruno prepara la plantilla en Premiere (MANUAL, bloqueante)

**Esta tarea la hace Bruno, no Codex.** Codex no tiene Premiere. Ninguna
tarea de código de este plan que use la plantilla puede empezar sin el
archivo que sale de aquí. Si Codex llega a esta tarea y el archivo no
existe todavía, se detiene y lo pide -- no continúa con datos inventados.

- [ ] **Paso 1:** Abrir `/Users/brunogutierrez/Downloads/testcolorlut.prproj`
  en Premiere (ya trae el LUT de Sony en un clip y el de DJI en otro,
  confirmado leyendo su XML durante el brainstorm).

- [ ] **Paso 2:** Al clip que tiene el LUT de Sony (`20260910_PIB0001.MP4`),
  ponerle la etiqueta de color **Cerulean** (clic derecho → Label).

- [ ] **Paso 3:** Al clip que tiene el LUT de DJI
  (`DJI_20260910113520_0008_D.MP4`), ponerle la etiqueta **Mango**.

- [ ] **Paso 4:** Importar UN clip de video más, cualquiera, corto, sin
  ponerle ningún LUT. Ponerle la etiqueta **Violet**. Este es el color de
  referencia para clips de cámara "otra" (los que no son Sony ni DJI).

- [ ] **Paso 5:** Crear un bin nuevo vacío (clic derecho en el panel de
  proyecto → New Bin). Nombre sugerido: `REF BIN`. No hace falta meterle
  nada adentro.

- [ ] **Paso 6:** Crear 5 secuencias vacías (File → New → Sequence →
  Settings, sin arrastrar ningún clip adentro) con estos ajustes EXACTOS
  (son los mismos 5 formatos que ya usa Clipify hoy en
  `uxp-plugin/js/secuencia.js`):

  | Nombre sugerido      | Ancho | Alto | FPS   |
  |-----------------------|-------|------|-------|
  | `REF 4K 9x16`         | 2160  | 3840 | 59.94 |
  | `REF 2.7K 9x16`       | 2160  | 3840 | 59.94 |
  | `REF 4K 16x9`         | 3840  | 2160 | 59.94 |
  | `REF 9x16 1080p`      | 1080  | 1920 | 59.94 |
  | `REF 16x9 1080p`      | 1920  | 1080 | 59.94 |

- [ ] **Paso 7:** Guardar el proyecto (`Cmd+S`). Confirmar la ruta final del
  archivo y decírsela a quien ejecute la Tarea 1 (Codex la copia de ahí, no
  la vuelve a pedir).

- [ ] **Paso 8 (si los archivos originales siguen en disco):** Correr en
  Terminal, y guardar la salida completa para la Tarea 9:

  ```bash
  ffprobe -v quiet -print_format json -show_streams \
    "/Users/brunogutierrez/archivos temporales IAV/IAV-2609.10-A/01. ASSETS VIDEO/01. VIDEOS SONY/20260910_PIB0001.MP4"
  ffprobe -v quiet -print_format json -show_streams \
    "/Users/brunogutierrez/archivos temporales IAV/IAV-2609.10-A/01. ASSETS VIDEO/02. VIDEO DRONE/DJI_20260910113520_0008_D.MP4"
  ```

  Si esas rutas ya no existen, correr lo mismo contra cualquier clip Sony y
  cualquier clip DJI verticales que Bruno tenga a la mano, y anotar el
  nombre del archivo usado. Esto alimenta la Tarea 9 (mapeo de rotación).

---

## Tarea 1: Empacar los recursos dentro de Clipify

**Files:**
- Create: `recursos/premiere/TemplateColorLuts.prproj` (copiado del
  resultado de la Tarea 0)
- Create: `recursos/premiere/SONY-SLOG3.cube` (copiado de
  `/Users/brunogutierrez/Library/Application Support/Adobe/Common/LUTs/Technical/SONY-SLOG3.cube`)
- Create: `recursos/premiere/DJI-DLOGM.cube` (copiado de
  `/Users/brunogutierrez/Library/Application Support/Adobe/Common/LUTs/Technical/DJI-DLOGM.cube`)
- Create: `src/clasificador_video/recursos.py`
- Test: `tests/test_recursos.py`
- Modify: `empaque/clipify.spec`

- [ ] **Paso 1: copiar los tres archivos**

```bash
mkdir -p "recursos/premiere"
cp "/ruta/que/dio/Bruno/en/la/Tarea/0/TemplateColorLuts.prproj" \
   "recursos/premiere/TemplateColorLuts.prproj"
cp "/Users/brunogutierrez/Library/Application Support/Adobe/Common/LUTs/Technical/SONY-SLOG3.cube" \
   "recursos/premiere/SONY-SLOG3.cube"
cp "/Users/brunogutierrez/Library/Application Support/Adobe/Common/LUTs/Technical/DJI-DLOGM.cube" \
   "recursos/premiere/DJI-DLOGM.cube"
```

- [ ] **Paso 2: escribir `src/clasificador_video/recursos.py`**

```python
"""Rutas a los recursos que Clipify empaca dentro de sí misma --
plantillas de Premiere y LUTs maestros. Mismo patrón que `patron.py`:
PyInstaller copia `recursos/` dentro de `sys._MEIPASS`, y esta función
busca ahí primero.

Sin Qt.
"""
from __future__ import annotations

import sys
from pathlib import Path

RELATIVA = Path("recursos") / "premiere"

TEMPLATE_COLOR_LUTS_NOMBRE = "TemplateColorLuts.prproj"
SONY_CUBE_NOMBRE = "SONY-SLOG3.cube"
DJI_CUBE_NOMBRE = "DJI-DLOGM.cube"


def carpeta_premiere() -> Path:
    """La carpeta `recursos/premiere`, corriendo del repo o de la app
    instalada -- ver `patron.py` para la razón de `sys._MEIPASS`.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / RELATIVA
    return Path(__file__).resolve().parents[2] / RELATIVA


def template_color_luts() -> Path:
    return carpeta_premiere() / TEMPLATE_COLOR_LUTS_NOMBRE


def cube_de_camara(camara: str) -> Path | None:
    """El `.cube` maestro para `camara` ("sony"/"dji"/"otra"), o `None`
    si esa cámara no tiene LUT -- "otra" nunca lo tiene, a propósito (ver
    el spec: no hay LUT que le corresponda a ciegas).
    """
    nombre = {"sony": SONY_CUBE_NOMBRE, "dji": DJI_CUBE_NOMBRE}.get(camara)
    return carpeta_premiere() / nombre if nombre else None
```

- [ ] **Paso 3: escribir `tests/test_recursos.py`**

```python
"""Los recursos empacados existen de verdad y se resuelven bien --
sin esto, un typo en un nombre de archivo solo se nota al abrir Premiere."""
from clasificador_video import recursos


def test_carpeta_premiere_existe():
    assert recursos.carpeta_premiere().is_dir()


def test_template_color_luts_existe():
    assert recursos.template_color_luts().is_file()


def test_cube_de_camara_sony_y_dji_existen():
    assert recursos.cube_de_camara("sony").is_file()
    assert recursos.cube_de_camara("dji").is_file()


def test_cube_de_camara_otra_no_tiene_lut():
    assert recursos.cube_de_camara("otra") is None


def test_cube_de_camara_desconocida_no_tiene_lut():
    assert recursos.cube_de_camara("lo-que-sea") is None
```

- [ ] **Paso 4: correr las pruebas**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_recursos.py -v`
Expected: 5 passed

- [ ] **Paso 5: agregar los recursos al empaquetado**

En `empaque/clipify.spec`, dentro de la lista `datas=[...]` (que hoy solo
tiene la entrada de `docs/patron-de-recorrido`), agregar:

```python
    datas=[(str(RAIZ / "docs" / "patron-de-recorrido" / "MI-PATRON.md"),
            "docs/patron-de-recorrido"),
           (str(RAIZ / "recursos" / "premiere"), "recursos/premiere")],
```

- [ ] **Paso 6: commit**

```bash
git add recursos/premiere src/clasificador_video/recursos.py tests/test_recursos.py empaque/clipify.spec
git commit -m "Empacar la plantilla de LUTs y los .cube maestros dentro de Clipify"
```

---

## Tarea 2: Leer y escribir el gzip del .prproj

**Files:**
- Create: `src/clasificador_video/prproj_xml.py`
- Test: `tests/test_prproj_xml.py`

- [ ] **Paso 1: escribir la prueba que falla**

```python
"""Leer y escribir un .prproj real (gzip + XML), y clonar un objeto con
todo lo que referencia -- ver el spec para por qué el clonado es por
CIERRE DE REFERENCIAS y no por subárbol."""
import xml.etree.ElementTree as ET

from clasificador_video import prproj_xml, recursos


def test_leer_prproj_devuelve_un_elemento_premieredata():
    raiz = prproj_xml.leer_prproj(recursos.template_color_luts())
    assert raiz.tag == "PremiereData"


def test_escribir_y_releer_prproj_da_el_mismo_xml(tmp_path):
    raiz = prproj_xml.leer_prproj(recursos.template_color_luts())
    destino = tmp_path / "copia.prproj"

    prproj_xml.escribir_prproj(raiz, destino)
    releido = prproj_xml.leer_prproj(destino)

    assert ET.tostring(releido) == ET.tostring(raiz)
```

- [ ] **Paso 2: correr y ver que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_xml.py -v`
Expected: FAIL con `ModuleNotFoundError` o `AttributeError` (el módulo no
existe todavía)

- [ ] **Paso 3: escribir `src/clasificador_video/prproj_xml.py` (primera
  mitad -- leer/escribir)**

```python
"""Leer y escribir un `.prproj` (XML comprimido con gzip), y clonar un
objeto de ese XML junto con TODO lo que referencia.

Un `.prproj` no anida sus objetos por lo que significan: todos son
hermanos sueltos bajo `<PremiereData>`, conectados por dos pares de
atributos -- `ObjectID`/`ObjectRef` (enteros) y `ObjectUID`/`ObjectURef`
(GUIDs). Confirmado leyendo un `.prproj` real guardado por Premiere 26.3
durante el brainstorm del 2026-09-23 -- ver
docs/superpowers/plans/2026-09-23-generar-prproj-directo.md.

Sin Qt.
"""
from __future__ import annotations

import gzip
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path


def leer_prproj(ruta: Path) -> ET.Element:
    """El elemento `<PremiereData>` raíz de un `.prproj`."""
    with gzip.open(ruta, "rb") as f:
        return ET.fromstring(f.read())


def escribir_prproj(raiz: ET.Element, destino: Path) -> None:
    """Comprime `raiz` como gzip y lo escribe en `destino`."""
    cuerpo = b'<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(raiz)
    with gzip.open(destino, "wb") as f:
        f.write(cuerpo)
```

- [ ] **Paso 4: correr de nuevo**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_xml.py -v`
Expected: 2 passed

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/prproj_xml.py tests/test_prproj_xml.py
git commit -m "Leer y escribir el gzip de un .prproj"
```

---

## Tarea 3: Clonado genérico por cierre de referencias

**Files:**
- Modify: `src/clasificador_video/prproj_xml.py`
- Test: `tests/test_prproj_xml.py`

Esta es la pieza central de todo el generador. Se prueba con un XML
sintético chico (no el `.prproj` real de 1.3 MB) para que la prueba sea
rápida y el fallo, si lo hay, se entienda de un vistazo.

- [ ] **Paso 1: escribir las pruebas que fallan**

```python
def _premiere_data_de_prueba():
    """Un `<PremiereData>` sintético con la misma FORMA que un `.prproj`
    real: tres objetos por ObjectID enteros (A -> B -> C, en cadena) y uno
    por ObjectUID (D), para probar los dos tipos de referencia a la vez.
    """
    return ET.fromstring("""
    <PremiereData Version="3">
        <Project ObjectID="1" ClassID="x">
            <NextID>1000002</NextID>
        </Project>
        <NodoA ObjectID="10" ClassID="a">
            <Hijo ObjectRef="11"/>
            <Externo ObjectRef="99"/>
        </NodoA>
        <NodoB ObjectID="11" ClassID="b">
            <Hijo ObjectUID="dd0e0000-0000-0000-0000-000000000001"/>
        </NodoB>
        <NodoC ObjectUID="dd0e0000-0000-0000-0000-000000000001" ClassID="c">
            <Nombre>original</Nombre>
        </NodoC>
        <NodoNoTocado ObjectID="99" ClassID="z">
            <Nombre>no se clona</Nombre>
        </NodoNoTocado>
    </PremiereData>
    """)


def test_clonar_por_cierre_copia_todo_lo_alcanzable():
    raiz = _premiere_data_de_prueba()
    asignador = prproj_xml.AsignadorDeIds(raiz)

    mapa = prproj_xml.clonar_por_cierre(raiz, "ObjectID", "10", asignador)

    # Se clonaron los 3 alcanzables (A, B, C), NO el "NodoNoTocado".
    assert set(mapa.keys()) == {("ObjectID", "10"), ("ObjectID", "11"),
                                 ("ObjectUID", "dd0e0000-0000-0000-0000-000000000001")}
    assert len(raiz.findall("NodoA")) == 2
    assert len(raiz.findall("NodoNoTocado")) == 1


def test_clonar_por_cierre_da_ids_nuevos_y_unicos():
    raiz = _premiere_data_de_prueba()
    asignador = prproj_xml.AsignadorDeIds(raiz)

    mapa = prproj_xml.clonar_por_cierre(raiz, "ObjectID", "10", asignador)

    nodo_a_clonado = raiz.findall("NodoA")[1]
    assert nodo_a_clonado.get("ObjectID") != "10"
    assert int(nodo_a_clonado.get("ObjectID")) > 99  # no choca con lo existente


def test_clonar_por_cierre_reescribe_refs_internas_y_deja_las_externas():
    raiz = _premiere_data_de_prueba()
    asignador = prproj_xml.AsignadorDeIds(raiz)

    prproj_xml.clonar_por_cierre(raiz, "ObjectID", "10", asignador)

    nodo_a_clonado = raiz.findall("NodoA")[1]
    nodo_b_original, nodo_b_clonado = raiz.findall("NodoB")
    # El ref a NodoB, adentro del NodoA clonado, apunta al NodoB clonado.
    assert nodo_a_clonado.find("Hijo").get("ObjectRef") == nodo_b_clonado.get("ObjectID")
    # El ref externo (NodoNoTocado) se queda igual en el clon.
    assert nodo_a_clonado.find("Externo").get("ObjectRef") == "99"
    # El original no se tocó.
    assert nodo_b_original.get("ObjectID") == "11"


def test_clonar_por_cierre_respeta_fronteras():
    raiz = _premiere_data_de_prueba()
    asignador = prproj_xml.AsignadorDeIds(raiz)

    # NodoB es la frontera: se clona NodoA, pero NodoB se queda compartido.
    mapa = prproj_xml.clonar_por_cierre(
        raiz, "ObjectID", "10", asignador, fronteras={("ObjectID", "11")})

    assert ("ObjectID", "11") not in mapa
    assert len(raiz.findall("NodoB")) == 1
    nodo_a_clonado = raiz.findall("NodoA")[1]
    assert nodo_a_clonado.find("Hijo").get("ObjectRef") == "11"


def test_asignador_de_ids_nunca_repite():
    raiz = _premiere_data_de_prueba()
    asignador = prproj_xml.AsignadorDeIds(raiz)

    ids = {asignador.nuevo_object_id() for _ in range(50)}

    assert len(ids) == 50
```

- [ ] **Paso 2: correr y ver que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_xml.py -v`
Expected: FAIL, `AttributeError: module 'prproj_xml' has no attribute 'AsignadorDeIds'`

- [ ] **Paso 3: agregar el clonado a `src/clasificador_video/prproj_xml.py`**

```python
# --- agregar al final del archivo, debajo de escribir_prproj ---

class AsignadorDeIds:
    """Entrega `ObjectID` enteros y `ObjectUID` GUID que no chocan con
    ninguno que ya exista en `raiz`, escaneando una sola vez al crearse.
    """

    def __init__(self, raiz: ET.Element):
        maximo = 0
        for elemento in raiz.iter():
            for atributo in ("ObjectID", "ObjectRef"):
                valor = elemento.get(atributo)
                if valor is not None and valor.isdigit():
                    maximo = max(maximo, int(valor))
        self._siguiente = maximo + 1

    def nuevo_object_id(self) -> str:
        valor = str(self._siguiente)
        self._siguiente += 1
        return valor

    def nuevo_object_uid(self) -> str:
        return str(uuid.uuid4())


# Los dos pares posibles de atributo-ancla/atributo-referencia. Un objeto
# vive con uno de los dos ("ObjectID" con hijos en "ObjectRef", "ObjectUID"
# con hijos en "ObjectURef") -- nunca los dos a la vez, confirmado en el
# .prproj real: ClipProjectItem/MasterClip usan ObjectUID, casi todo lo
# demás usa ObjectID.
_PARES = {"ObjectID": "ObjectRef", "ObjectUID": "ObjectURef"}


def _referencias_de(elemento: ET.Element):
    """(tipo_de_ancla, valor) de cada referencia que hace `elemento`,
    buscando en TODO su árbol interno -- una referencia puede estar en un
    nieto, no solo en un hijo directo (ver `VideoComponentChain` adentro de
    `MasterClip` en el `.prproj` real)."""
    for hijo in elemento.iter():
        for ancla, ref in _PARES.items():
            valor = hijo.get(ref)
            if valor is not None:
                yield ancla, valor


def clonar_por_cierre(raiz: ET.Element, tipo_ancla: str, valor_ancla: str,
                       asignador: AsignadorDeIds,
                       fronteras: set[tuple[str, str]] = frozenset()
                       ) -> dict[tuple[str, str], ET.Element]:
    """Clona el objeto anclado en `(tipo_ancla, valor_ancla)` y TODO lo que
    alcanza por referencia, como hermanos nuevos de `raiz`, con IDs nuevos.

    `fronteras` son objetos que NO se clonan aunque sean alcanzables -- se
    quedan compartidos con el original, y las referencias hacia ellos desde
    objetos clonados se dejan intactas. Así es como el LUT de Lumetri se
    REUSA en vez de clonarse (ver Tarea 8: el mismo `VideoComponentChain`
    sirve para todos los clips de una cámara, y así lo validó el spike).

    Devuelve un mapa de (tipo_ancla_original, valor_original) -> elemento
    CLONADO, para que quien llama pueda ir a buscar el clon de un objeto
    puntual (por ejemplo, el `Media` del clip clonado) y sobreescribirle
    campos.
    """
    indice: dict[tuple[str, str], ET.Element] = {}
    for elemento in raiz:
        for ancla in _PARES:
            valor = elemento.get(ancla)
            if valor is not None:
                indice[(ancla, valor)] = elemento

    por_visitar = [(tipo_ancla, valor_ancla)]
    vistos: set[tuple[str, str]] = set()
    mapa_de_ids: dict[tuple[str, str], tuple[str, str]] = {}
    orden: list[tuple[str, str]] = []

    while por_visitar:
        clave = por_visitar.pop()
        if clave in vistos or clave in fronteras:
            continue
        vistos.add(clave)
        if clave not in indice:
            continue  # referencia a algo fuera del documento; se ignora
        orden.append(clave)
        ancla, valor_viejo = clave
        nuevo_valor = (asignador.nuevo_object_id() if ancla == "ObjectID"
                       else asignador.nuevo_object_uid())
        mapa_de_ids[clave] = (ancla, nuevo_valor)
        for ref in _referencias_de(indice[clave]):
            por_visitar.append(ref)

    resultado: dict[tuple[str, str], ET.Element] = {}
    for clave in orden:
        original = indice[clave]
        clon = ET.fromstring(ET.tostring(original))
        ancla, nuevo_valor = mapa_de_ids[clave]
        clon.set(ancla, nuevo_valor)
        for hijo in clon.iter():
            for anc, ref in _PARES.items():
                valor = hijo.get(ref)
                if valor is not None and (anc, valor) in mapa_de_ids:
                    hijo.set(ref, mapa_de_ids[(anc, valor)][1])
        raiz.append(clon)
        resultado[clave] = clon

    return resultado
```

- [ ] **Paso 4: correr y confirmar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_xml.py -v`
Expected: 7 passed

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/prproj_xml.py tests/test_prproj_xml.py
git commit -m "Clonado genérico de objetos de un .prproj por cierre de referencias"
```

---

## Tarea 4: Puerto de `numeroDeCuarto.js`

**Files:**
- Create: `src/clasificador_video/numero_de_cuarto.py`
- Test: `tests/test_numero_de_cuarto.py`

Puerto 1:1 de `uxp-plugin/js/numeroDeCuarto.js` (ya probado en producción
del lado del plugin). Antes de escribir, leer ese archivo para no
inventar casos nuevos.

- [ ] **Paso 1: escribir la prueba que falla**

```python
"""Puerto de uxp-plugin/js/numeroDeCuarto.js -- mismos casos, ver ese
archivo para la razón de cada uno."""
from clasificador_video.numero_de_cuarto import (
    con_numero, es_el_mismo_cuarto, sin_numero,
)


def test_con_numero_rellena_a_dos_digitos():
    assert con_numero("Cocina", 3) == "03. Cocina"
    assert con_numero("Cocina", 12) == "12. Cocina"


def test_sin_numero_quita_un_prefijo():
    assert sin_numero("03. Cocina") == "Cocina"
    assert sin_numero("01. 2 Recamaras") == "2 Recamaras"


def test_sin_numero_no_toca_lo_que_bruno_escribio():
    assert sin_numero("2 Recamaras") == "2 Recamaras"


def test_es_el_mismo_cuarto_ignora_numero_y_marca_de_camara():
    assert es_el_mismo_cuarto("03. Cocina", "Cocina")
    assert es_el_mismo_cuarto("03. Cocina [SONY]", "07. Cocina [SONY+DRONE]")


def test_es_el_mismo_cuarto_distingue_acentos():
    assert not es_el_mismo_cuarto("Recamara 1", "Recámara 1")
```

- [ ] **Paso 2: correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_numero_de_cuarto.py -v`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Paso 3: escribir `src/clasificador_video/numero_de_cuarto.py`**

```python
"""El número que llevan las carpetas de cuartos en Premiere: «03. Cocina».
Puerto de `uxp-plugin/js/numeroDeCuarto.js` -- ver ese archivo para la
razón de cada regla; aquí solo vive la lógica en Python.

Sin Qt.
"""
from __future__ import annotations

import re

from clasificador_video.marca_camara import sin_marca_de_camara

_PREFIJO = re.compile(r"^\d+\.\s")


def con_numero(nombre: str, posicion: int) -> str:
    return f"{posicion:02d}. {nombre or ''}"


def sin_numero(nombre: str) -> str:
    return _PREFIJO.sub("", nombre or "")


def es_el_mismo_cuarto(un_nombre: str, otro_nombre: str) -> bool:
    return (sin_marca_de_camara(sin_numero(un_nombre))
            == sin_marca_de_camara(sin_numero(otro_nombre)))
```

- [ ] **Paso 4: correr y confirmar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_numero_de_cuarto.py -v`
Expected: FAIL en las dos pruebas de `es_el_mismo_cuarto` (todavía no existe
`sin_marca_de_camara` en `marca_camara.py`) -- eso es lo esperado, se
resuelve en la Tarea 5. Confirmar que las 3 pruebas de `con_numero`/
`sin_numero` SÍ pasan.

- [ ] **Paso 5: commit parcial**

```bash
git add src/clasificador_video/numero_de_cuarto.py tests/test_numero_de_cuarto.py
git commit -m "Puerto de numeroDeCuarto.js: con_numero y sin_numero"
```

---

## Tarea 5: Puerto de `marcaCamara.js` (las funciones de texto)

**Files:**
- Modify: `src/clasificador_video/marca_camara.py`
- Modify: `tests/test_marca_camara.py`

Le agrega a `marca_camara.py` (que hoy solo detecta `bin_dice_*`) las
funciones que arman el texto `[SONY+DRONE]`, puerto de
`uxp-plugin/js/marcaCamara.js`. Viven en el mismo archivo porque es el mismo
dominio -- detectar y nombrar la marca de cámara.

- [ ] **Paso 1: agregar las pruebas que fallan a `tests/test_marca_camara.py`**

```python
# --- agregar al final del archivo ---
from clasificador_video.marca_camara import (
    marca_de_camara_del_prefijo, nombre_del_cuarto_con_marca,
    sin_marca_de_camara,
)


def _clip(categoria_path, **flags):
    base = {"categoria_path": categoria_path, "bin_sony": False,
            "bin_pocket": False, "bin_dron": False}
    base.update(flags)
    return base


def test_marca_de_camara_del_prefijo_una_sola_camara():
    clips = [_clip(["Cocina"], bin_sony=True)]
    assert marca_de_camara_del_prefijo(clips, ["Cocina"]) == "SONY"


def test_marca_de_camara_del_prefijo_combinada_en_orden_fijo():
    clips = [_clip(["Cocina"], bin_dron=True, bin_sony=True)]
    assert marca_de_camara_del_prefijo(clips, ["Cocina"]) == "SONY+DRONE"


def test_marca_de_camara_del_prefijo_sin_camara_reconocible():
    clips = [_clip(["Cocina"])]
    assert marca_de_camara_del_prefijo(clips, ["Cocina"]) == ""


def test_sin_marca_de_camara_quita_al_inicio_o_al_final():
    assert sin_marca_de_camara("[SONY+DRONE] Cocina") == "Cocina"
    assert sin_marca_de_camara("Cocina [SONY+DRONE]") == "Cocina"


def test_sin_marca_de_camara_no_toca_texto_de_bruno():
    assert sin_marca_de_camara("Cocina [ideas]") == "Cocina [ideas]"


def test_nombre_del_cuarto_con_marca():
    clips = [_clip(["Cocina"], bin_sony=True)]
    assert (nombre_del_cuarto_con_marca("03. Cocina", "Cocina", clips, ["Cocina"])
            == "03. Cocina [SONY]")


def test_nombre_del_cuarto_con_marca_sin_camara_no_agrega_nada():
    clips = [_clip(["Cocina"])]
    assert (nombre_del_cuarto_con_marca("03. Cocina", "Cocina", clips, ["Cocina"])
            == "03. Cocina")
```

- [ ] **Paso 2: correr y confirmar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_marca_camara.py -v`
Expected: los 4 tests viejos siguen pasando; los 7 nuevos fallan con
`ImportError`.

- [ ] **Paso 3: agregar las funciones a `src/clasificador_video/marca_camara.py`**

```python
# --- agregar al final del archivo ---
import re

# Mismo orden fijo que uxp-plugin/js/marcaCamara.js: Sony/Pocket/Drone.
_MARCAS = (("SONY", "bin_sony"), ("POCKET", "bin_pocket"), ("DRONE", "bin_dron"))

_MARCA_CONOCIDA = r"(?:SONY|POCKET|DRONE)(?:\+(?:SONY|POCKET|DRONE))*"
_PREFIJO_MARCA = re.compile(r"^\[" + _MARCA_CONOCIDA + r"\] ")
_SUFIJO_MARCA = re.compile(r" \[" + _MARCA_CONOCIDA + r"\]$")


def sin_marca_de_camara(nombre: str) -> str:
    """Quita una sola marca de cámara conocida, al inicio o al final --
    nunca texto que Bruno haya escrito él mismo. Ver marcaCamara.js."""
    s = str(nombre or "")
    s = _PREFIJO_MARCA.sub("", s)
    s = _SUFIJO_MARCA.sub("", s)
    return s


def _algun_clip_empieza_con(clips, prefijo, campo):
    for c in clips or []:
        categoria = c.get("categoria_path") if isinstance(c, dict) else None
        if categoria is None or not c.get(campo):
            continue
        if len(categoria) < len(prefijo):
            continue
        if all(categoria[i] == prefijo[i] for i in range(len(prefijo))):
            return True
    return False


def marca_de_camara_del_prefijo(clips, prefijo) -> str:
    """"SONY", "SONY+DRONE", etc., o "" si ningún clip bajo `prefijo`
    viene de una cámara reconocible (bin_sony/bin_pocket/bin_dron)."""
    marcas = [palabra for palabra, campo in _MARCAS
              if _algun_clip_empieza_con(clips, prefijo, campo)]
    return "+".join(marcas)


def nombre_del_cuarto_con_marca(nombre_con_numero, nombre_sin_numero, clips,
                                 prefijo_de_categoria=None) -> str:
    prefijo = prefijo_de_categoria or [nombre_sin_numero]
    marca = marca_de_camara_del_prefijo(clips, prefijo)
    if not marca:
        return nombre_con_numero
    return f"{nombre_con_numero} [{marca}]"
```

- [ ] **Paso 4: correr todo `test_marca_camara.py` y `test_numero_de_cuarto.py`**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_marca_camara.py tests/test_numero_de_cuarto.py -v`
Expected: todos pasan (11 + 5)

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/marca_camara.py tests/test_marca_camara.py \
        src/clasificador_video/numero_de_cuarto.py tests/test_numero_de_cuarto.py
git commit -m "Puerto de marcaCamara.js y arreglo de es_el_mismo_cuarto"
```

---

## Tarea 6: Puerto de `nombre.js`

**Files:**
- Create: `src/clasificador_video/nombre_de_clip.py`
- Test: `tests/test_nombre_de_clip.py`

- [ ] **Paso 1: escribir la prueba que falla**

```python
"""Puerto de uxp-plugin/js/nombre.js -- el nombre del clip en Premiere:
[simbolo ]Cuarto NN [CAMARA]."""
from clasificador_video.nombre_de_clip import nombre_de_clip, numeros_de_clip


def test_nombre_de_clip_pick():
    assert nombre_de_clip("Cocina", 1, "SONY", "pick") == "✓ Cocina 01 [SONY]"


def test_nombre_de_clip_reject():
    assert nombre_de_clip("Cocina", 3, "SONY", "reject") == "✕ Cocina 03 [SONY]"


def test_nombre_de_clip_destacado():
    assert nombre_de_clip("Cocina", 2, "", "destacado") == "★ Cocina 02"


def test_nombre_de_clip_sin_marcar_no_lleva_simbolo():
    assert nombre_de_clip("Cocina", 1, "SONY", "none") == "Cocina 01 [SONY]"


def test_nombre_de_clip_numero_pasa_de_dos_digitos():
    assert nombre_de_clip("Cocina", 123, "", "none") == "Cocina 123"


def test_numeros_de_clip_cuenta_por_cuarto_en_orden():
    clips = [
        {"categoria_path": ["Cocina"]},
        {"categoria_path": ["Bano"]},
        {"categoria_path": ["Cocina"]},
    ]
    assert numeros_de_clip(clips) == [1, 1, 2]


def test_numeros_de_clip_dos_unidades_con_mismo_cuarto_no_comparten_contador():
    clips = [
        {"categoria_path": ["Casa A", "Cocina"]},
        {"categoria_path": ["Casa B", "Cocina"]},
    ]
    assert numeros_de_clip(clips) == [1, 1]
```

- [ ] **Paso 2: correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_nombre_de_clip.py -v`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Paso 3: escribir `src/clasificador_video/nombre_de_clip.py`**

```python
"""El nombre de un clip en el panel de proyecto de Premiere:
«[simbolo ]Cuarto NN [CAMARA]». Puerto de `uxp-plugin/js/nombre.js` -- ver
ese archivo para el porqué del formato.

Sin Qt.
"""
from __future__ import annotations

import json

_PREFIJO_POR_FLAG = {"destacado": "★ ", "pick": "✓ ", "reject": "✕ "}


def nombre_de_clip(cuarto: str, numero: int, marca_de_camara: str,
                    flag: str) -> str:
    simbolo = _PREFIJO_POR_FLAG.get(flag, "")
    camara = f" [{marca_de_camara}]" if marca_de_camara else ""
    return f"{simbolo}{cuarto or ''} {numero:02d}{camara}"


def numeros_de_clip(clips: list) -> list[int]:
    """El número de cada clip DENTRO de su cuarto, en el orden en que
    vienen -- un arreglo paralelo a `clips`. Los clips sin categoria_path
    (sin clasificar) comparten su propio contador, con llave `"[]"`."""
    contador: dict[str, int] = {}
    resultado = []
    for c in clips or []:
        categoria = c.get("categoria_path") if isinstance(c, dict) else None
        llave = json.dumps(categoria or [])
        contador[llave] = contador.get(llave, 0) + 1
        resultado.append(contador[llave])
    return resultado
```

- [ ] **Paso 4: correr y confirmar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_nombre_de_clip.py -v`
Expected: 7 passed

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/nombre_de_clip.py tests/test_nombre_de_clip.py
git commit -m "Puerto de nombre.js: nombre_de_clip y numeros_de_clip"
```

---

## Tarea 7: `probe.py` expone la duración en segundos

**Files:**
- Modify: `src/clasificador_video/probe.py`
- Modify: `tests/test_probe.py`

`probe_clip` ya calcula `duration_seconds` internamente (para sacar
`duration_frames`) pero no la regresa. La Tarea 9 la necesita tal cual,
sin redondear a frames, para calcular los campos de tiempo en ticks.

- [ ] **Paso 1: leer el `probe_clip` actual**

```bash
grep -n "duration_seconds\|return {" src/clasificador_video/probe.py
```

- [ ] **Paso 2: agregar la prueba que falla, a `tests/test_probe.py`**

```python
def test_probe_clip_incluye_duration_seconds(tmp_path):
    def runner_falso(_ruta):
        return (
            '{"streams":[{"codec_type":"video","width":1080,"height":1920,'
            '"r_frame_rate":"60000/1001"}],'
            '"format":{"duration":"6.006"}}'
        )
    resultado = probe.probe_clip(tmp_path / "x.mp4", runner=runner_falso)
    assert resultado["duration_seconds"] == 6.006
```

(Ajustar el nombre del parámetro `runner` y la forma del JSON de prueba al
que ya usan las pruebas vecinas en `tests/test_probe.py` -- copiar el
patrón de la prueba de `probe_clip` que ya exista ahí, no inventar uno
nuevo.)

- [ ] **Paso 3: correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_probe.py -v -k duration_seconds`
Expected: FAIL, `KeyError: 'duration_seconds'`

- [ ] **Paso 4: agregar el campo en `probe_clip`**

Buscar el diccionario que arma `probe_clip` (el que ya tiene `"width"`,
`"height"`, `"fps"`, `"duration_frames"`, `"rotation"`) y agregar una
línea: `"duration_seconds": duration_seconds,` -- la variable
`duration_seconds` ya existe en la función, solo falta exponerla.

- [ ] **Paso 5: correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_probe.py -v`
Expected: todos pasan, incluida la nueva

- [ ] **Paso 6: commit**

```bash
git add src/clasificador_video/probe.py tests/test_probe.py
git commit -m "probe_clip expone duration_seconds"
```

---

## Tarea 8: Encontrar los archetipos dentro de la plantilla

**Files:**
- Create: `src/clasificador_video/prproj_plantilla.py`
- Test: `tests/test_prproj_plantilla.py`

Esto localiza, dentro de `TemplateColorLuts.prproj` ya parseado, los 3
clips de referencia (por la ruta del `.cube` que tienen adentro, o sin LUT
para "otra"), el bin de referencia, y las 5 secuencias de referencia por
nombre. Si algo falta, se avisa -- no se adivina (mismo criterio que
`camara_color` en `theme.py`).

- [ ] **Paso 1: escribir la prueba que falla**

```python
"""Localizar los archetipos (clips de referencia, bin, secuencias) dentro
de la plantilla real. Si esto falla, es la plantilla la que está mal
armada -- ver Tarea 0 del plan."""
import pytest

from clasificador_video import prproj_plantilla, prproj_xml, recursos


@pytest.fixture
def raiz():
    return prproj_xml.leer_prproj(recursos.template_color_luts())


def test_archetipos_de_clip_encuentra_sony_y_dji(raiz):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    assert set(archetipos.keys()) == {"sony", "dji", "otra"}


def test_archetipo_sony_tiene_el_lut_correcto(raiz):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    assert archetipos["sony"].ruta_lut.endswith("SONY-SLOG3.cube")


def test_archetipo_dji_tiene_el_lut_correcto(raiz):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    assert archetipos["dji"].ruta_lut.endswith("DJI-DLOGM.cube")


def test_archetipo_otra_no_tiene_lut(raiz):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    assert archetipos["otra"].ruta_lut is None


def test_archetipo_de_bin_existe(raiz):
    assert prproj_plantilla.archetipo_de_bin(raiz) is not None


def test_archetipos_de_secuencia_completos(raiz):
    archetipos = prproj_plantilla.archetipos_de_secuencia(raiz)
    assert set(archetipos.keys()) == {
        "4k_9x16", "2_7k_9x16", "4k_16x9", "9x16_1080p", "16x9_1080p"}


def test_plantilla_incompleta_avisa_en_vez_de_adivinar(tmp_path):
    raiz = prproj_xml.leer_prproj(recursos.template_color_luts())
    for elemento in list(raiz):
        if elemento.tag in ("VideoClip", "AudioClip", "ClipProjectItem"):
            raiz.remove(elemento)
    with pytest.raises(prproj_plantilla.PlantillaIncompleta):
        prproj_plantilla.archetipos_de_clip(raiz)
```

- [ ] **Paso 2: correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_plantilla.py -v`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Paso 3: escribir `src/clasificador_video/prproj_plantilla.py`**

```python
"""Encuentra, dentro de `TemplateColorLuts.prproj` ya parseado, los
objetos de referencia que el generador clona o reusa: un clip por cámara
(con su LUT ya validado por Premiere, o sin LUT para "otra"), un bin
vacío, y las 5 secuencias vacías de los formatos de Clipify.

No adivina: si la plantilla no tiene lo que se espera (Tarea 0 mal hecha,
o alguien la reemplazó con una plantilla vieja), avisa con
`PlantillaIncompleta` en vez de generar un `.prproj` a medias.

Sin Qt.
"""
from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from dataclasses import dataclass


class PlantillaIncompleta(Exception):
    pass


@dataclass(frozen=True)
class ArchetipoDeClip:
    master_clip_uid: str          # ObjectUID del <MasterClip> a clonar
    video_component_chain_id: str | None  # ObjectID del LUT a REUSAR (no clonar)
    ruta_lut: str | None          # la ruta del .cube, solo informativo


def _texto_de_start_keyframe_value(nodo: ET.Element) -> str:
    """El texto que guarda un `<StartKeyframeValue Encoding="base64">`,
    decodificado de UTF-16LE -- así es como Premiere guarda una ruta de
    archivo dentro de un parámetro de Lumetri. Confirmado leyendo un
    `.prproj` real (ver el plan)."""
    texto = (nodo.text or "").strip()
    if not texto:
        return ""
    try:
        crudo = base64.b64decode(texto)
        return crudo.decode("utf-16-le", errors="ignore").rstrip("\x00")
    except Exception:
        return ""


def _lut_del_video_component_chain(raiz: ET.Element, chain_id: str) -> str | None:
    chain = raiz.find(f'.//VideoComponentChain[@ObjectID="{chain_id}"]')
    if chain is None:
        return None
    for valor in chain.iter("StartKeyframeValue"):
        texto = _texto_de_start_keyframe_value(valor)
        if texto.lower().endswith(".cube"):
            return texto
    return None


def _label_del_clip_project_item(item: ET.Element) -> str | None:
    label = item.find(".//Column.PropertyText.Label")
    return label.text if label is not None else None


# BE.Prefs.LabelColors.N que Bruno confirmó en la Tarea 0, leídos de la
# plantilla real -- NO se adivinan los números, se leen de ahí.
_LABEL_A_CAMARA = None  # se resuelve dentro de archetipos_de_clip


def archetipos_de_clip(raiz: ET.Element) -> dict[str, ArchetipoDeClip]:
    """Un `ArchetipoDeClip` por cada una de "sony"/"dji"/"otra", ubicados
    por el LUT que tiene aplicado cada `MasterClip` de la plantilla (o la
    ausencia de LUT, para "otra")."""
    encontrados: dict[str, ArchetipoDeClip] = {}
    for master_clip in raiz.findall("MasterClip"):
        uid = master_clip.get("ObjectUID")
        if uid is None:
            continue
        chain_ref = master_clip.find("VideoComponentChain")
        chain_id = chain_ref.get("ObjectRef") if chain_ref is not None else None
        ruta_lut = _lut_del_video_component_chain(raiz, chain_id) if chain_id else None
        if ruta_lut and "sony-slog3" in ruta_lut.lower():
            encontrados["sony"] = ArchetipoDeClip(uid, chain_id, ruta_lut)
        elif ruta_lut and "dji-dlogm" in ruta_lut.lower():
            encontrados["dji"] = ArchetipoDeClip(uid, chain_id, ruta_lut)
        elif ruta_lut is None and "otra" not in encontrados:
            encontrados["otra"] = ArchetipoDeClip(uid, None, None)

    faltan = {"sony", "dji", "otra"} - encontrados.keys()
    if faltan:
        raise PlantillaIncompleta(
            "La plantilla de LUTs no tiene clip de referencia para: "
            + ", ".join(sorted(faltan)) + ". Revisar la Tarea 0 del plan.")
    return encontrados


def archetipo_de_bin(raiz: ET.Element) -> ET.Element | None:
    """El primer objeto con `ProjectItemContainer` que NO sea el
    `RootProjectItem` -- un bin (carpeta) vacío creado a mano en la
    plantilla."""
    for elemento in raiz:
        if elemento.tag == "RootProjectItem":
            continue
        if elemento.find("ProjectItemContainer") is not None:
            return elemento
    return None


# Ancho, alto y fps de cada formato -- mismos valores que
# uxp-plugin/js/secuencia.js. La CLAVE (ej. "4k_9x16") es interna a este
# módulo; el nombre real que Bruno le puso en la plantilla NO importa para
# encontrarla, lo que importa es el ancho/alto/fps de sus ajustes.
FORMATOS_DE_SECUENCIA = {
    "4k_9x16": (2160, 3840, 59.94),
    "2_7k_9x16": (2160, 3840, 59.94),
    "4k_16x9": (3840, 2160, 59.94),
    "9x16_1080p": (1080, 1920, 59.94),
    "16x9_1080p": (1920, 1080, 59.94),
}


def archetipos_de_secuencia(raiz: ET.Element) -> dict[str, ET.Element]:
    """Placeholder de localización -- se completa en la Tarea 11, que es
    quien primero necesita leer los ajustes reales (`VideoFrameRect`/
    frame rate) de un objeto `Sequence` real para saber cómo distinguir
    uno de otro. Aquí solo se deja la firma y la excepción, para que las
    pruebas de esta tarea puedan describir el contrato esperado sin
    bloquear las tareas 4-7, que no dependen de esto."""
    raise NotImplementedError("se implementa en la Tarea 11")
```

**Nota para quien ejecute esta tarea:** las pruebas
`test_archetipos_de_secuencia_completos` de este archivo van a fallar
hasta la Tarea 11 -- márquenla con `@pytest.mark.skip(reason="Tarea 11")`
por ahora y quítenle el skip cuando lleguen a esa tarea. El resto de
pruebas de este archivo (clips y bin) sí deben pasar aquí.

- [ ] **Paso 4: marcar el test de secuencias como skip temporal**

```python
@pytest.mark.skip(reason="se implementa en la Tarea 11")
def test_archetipos_de_secuencia_completos(raiz):
    ...
```

- [ ] **Paso 5: correr**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_plantilla.py -v`
Expected: 6 passed, 1 skipped

- [ ] **Paso 6: commit**

```bash
git add src/clasificador_video/prproj_plantilla.py tests/test_prproj_plantilla.py
git commit -m "Localizar los clips y el bin de referencia en la plantilla"
```

---

## Tarea 9: Confirmar el mapeo de rotación (empírico, con evidencia real)

**Este paso NO se salta ni se adivina.** El proyecto ya tuvo un bug real
por escribir el signo de rotación al revés (ver el spike:
`C_exiftool_matrix.mp4` entró volteado). Se deriva del par de datos reales
que ya tenemos, no de una tabla EXIF de memoria.

**Files:**
- Create: `src/clasificador_video/orientacion_premiere.py`
- Test: `tests/test_orientacion_premiere.py`

- [ ] **Paso 1: correr ffprobe sobre los DOS archivos reales de la Tarea 0**
  (o los que Bruno haya dado si los originales ya no estaban)

```bash
ffprobe -v quiet -print_format json -show_streams "<ruta del Sony>" | python3 -c "
import json, sys
d = json.load(sys.stdin)
v = next(s for s in d['streams'] if s['codec_type'] == 'video')
print('rotation side_data:', v.get('side_data_list'))
print('rotate tag:', v.get('tags', {}).get('rotate'))
"
```

Repetir para el archivo DJI. Cada uno de estos dos clips reales tiene
`OriginalImageOrientationType = 8` YA CONFIRMADO dentro de
`testcolorlut.prproj` (verificado leyendo el XML durante el brainstorm,
líneas donde aparece `<OriginalImageOrientationType>8</...>` dos veces,
una por cada `VideoStream`). Eso da el par completo: el valor real de
rotación que reporta `ffprobe` para ESTOS DOS archivos corresponde a
`OriginalImageOrientationType = 8`.

- [ ] **Paso 2: escribir `src/clasificador_video/orientacion_premiere.py`**
  con el mapeo QUE SALIÓ del Paso 1 (no antes)

```python
"""La rotación que reporta ffprobe (grados: 0/90/180/270, ver
`probe._rotation_degrees`), traducida al campo `OriginalImageOrientationType`
que Premiere guarda en el `VideoStream` de cada `Media`.

CONFIRMADO EMPÍRICAMENTE, no de una tabla EXIF de memoria: el 2026-09-23 se
leyeron los dos clips verticales reales que ya vivían adentro de
`testcolorlut.prproj` (uno Sony, uno DJI, los dos con
`OriginalImageOrientationType=8` ya guardado y confirmado por Bruno como
correcto en Premiere) y se corrieron por `ffprobe` para ver qué rotación
reportan de verdad. Ver Tarea 9 del plan de
`docs/superpowers/plans/2026-09-23-generar-prproj-directo.md` para el
comando exacto y su salida.

Un valor de rotación que no está en el mapa NO se adivina: revienta con
`RotacionNoMapeada`, para que se agregue aquí con su propia evidencia en
vez de escribir un valor que puede voltear el clip -- ya pasó una vez
(spike del 2026-09-23, `C_exiftool_matrix.mp4`).
"""
from __future__ import annotations


class RotacionNoMapeada(Exception):
    pass


# TODO(Tarea 9, Paso 1): reemplazar este mapa con el que salga de correr
# ffprobe sobre los dos clips reales. Placeholder con la hipótesis más
# probable (rotación de 90° en cámara -> orientación vertical = 8, como
# EXIF), A CONFIRMAR antes de dar la tarea por cerrada.
_ROTACION_A_ORIENTACION = {
    0: 1,
    90: 8,
    180: 3,
    270: 6,
}


def orientacion_de(rotacion_grados: int) -> int:
    rotacion_grados = rotacion_grados % 360
    if rotacion_grados not in _ROTACION_A_ORIENTACION:
        raise RotacionNoMapeada(
            f"No hay OriginalImageOrientationType confirmado para "
            f"{rotacion_grados} grados. Correr el Paso 1 de la Tarea 9 con "
            f"un clip real en esa rotación antes de agregarlo aquí.")
    return _ROTACION_A_ORIENTACION[rotacion_grados]
```

**IMPORTANTE:** el diccionario `_ROTACION_A_ORIENTACION` de arriba es una
**hipótesis a confirmar**, no un hecho verificado como el resto de este
plan -- está marcado con `TODO` a propósito. Quien ejecute esta tarea DEBE
correr el Paso 1 contra los archivos reales y corregir el diccionario para
que el valor de 90 (o el que sea la rotación real del Sony/DJI) mapee a 8,
que es el valor ya confirmado en Premiere. Si el Paso 1 da una rotación
distinta a 90/180/270, el diccionario se ajusta a lo que de verdad salió,
no a lo que está escrito arriba.

- [ ] **Paso 3: escribir `tests/test_orientacion_premiere.py`** usando el
  valor real que salió del Paso 1 (reemplazar `90` abajo si el real fue
  otro)

```python
"""orientacion_de usa el mapeo confirmado con clips reales -- ver
orientacion_premiere.py para la evidencia."""
import pytest

from clasificador_video.orientacion_premiere import (
    RotacionNoMapeada, orientacion_de,
)


def test_rotacion_del_sony_y_dji_real_da_8():
    # 90 es la rotacion que reportó ffprobe para los clips reales de la
    # Tarea 9, Paso 1 -- ajustar este número si el real fue distinto.
    assert orientacion_de(90) == 8


def test_sin_rotacion_da_orientacion_normal():
    assert orientacion_de(0) == 1


def test_rotacion_no_confirmada_avisa_en_vez_de_adivinar():
    with pytest.raises(RotacionNoMapeada):
        orientacion_de(45)
```

- [ ] **Paso 4: correr**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_orientacion_premiere.py -v`
Expected: 3 passed (después de ajustar el mapa con el dato real del Paso 1)

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/orientacion_premiere.py tests/test_orientacion_premiere.py
git commit -m "Mapeo de rotación a OriginalImageOrientationType, confirmado con clips reales"
```

---

## Tarea 10: Clonar un clip real -- tiempo, nombre, color, LUT

**Files:**
- Create: `src/clasificador_video/prproj_generador.py`
- Test: `tests/test_prproj_generador.py`

Junta todo lo anterior: clona el `MasterClip` de referencia de la cámara
que toque, apunta su `Media` al archivo real, recalcula los campos de
tiempo con `ffprobe`, le pone el nombre y el color, y conecta (sin clonar)
el `VideoComponentChain` del LUT.

- [ ] **Paso 1: escribir la prueba que falla**

```python
"""Clonar un clip real a partir del archetipo de su cámara."""
import xml.etree.ElementTree as ET

import pytest

from clasificador_video import prproj_generador, prproj_plantilla, prproj_xml, recursos

TICKS_POR_SEGUNDO = prproj_generador.TICKS_POR_SEGUNDO


@pytest.fixture
def raiz():
    return prproj_xml.leer_prproj(recursos.template_color_luts())


def _probe_falso(fps=59.94, duration_seconds=6.006, rotation=0):
    return {"fps": fps, "duration_seconds": duration_seconds, "rotation": rotation}


def test_clonar_clip_pone_la_ruta_del_archivo_real(raiz, tmp_path):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)
    archivo = tmp_path / "MiClip.MP4"
    archivo.write_bytes(b"")

    clon = prproj_generador.clonar_clip(
        raiz, archetipos["sony"], asignador, ruta_archivo=archivo,
        nombre_en_premiere="✓ Cocina 01 [SONY]",
        label_name="BE.Prefs.LabelColors.10", label_color=123456,
        datos_probe=_probe_falso())

    media = raiz.find(f'.//Media[@ObjectUID="{clon.media_uid}"]')
    assert media.find("FilePath").text == str(archivo)
    assert media.find("ActualMediaFilePath").text == str(archivo)
    assert media.find("Title").text == "MiClip.MP4"


def test_clonar_clip_pone_el_nombre_en_el_project_item(raiz, tmp_path):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)

    clon = prproj_generador.clonar_clip(
        raiz, archetipos["dji"], asignador, ruta_archivo=tmp_path / "d.mp4",
        nombre_en_premiere="★ Jardin 02 [DRONE]",
        label_name="BE.Prefs.LabelColors.7", label_color=999,
        datos_probe=_probe_falso())

    item = raiz.find(f'.//ClipProjectItem[@ObjectUID="{clon.clip_project_item_uid}"]')
    assert item.find(".//Name").text == "★ Jardin 02 [DRONE]"


def test_clonar_clip_recalcula_frame_rate_y_duracion_en_ticks(raiz, tmp_path):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)

    clon = prproj_generador.clonar_clip(
        raiz, archetipos["sony"], asignador, ruta_archivo=tmp_path / "d.mp4",
        nombre_en_premiere="x", label_name="BE.Prefs.LabelColors.1",
        label_color=1, datos_probe=_probe_falso(fps=25.0, duration_seconds=10.0))

    media = raiz.find(f'.//Media[@ObjectUID="{clon.media_uid}"]')
    video_stream = raiz.find(f'.//VideoStream[@ObjectID="{media.find("VideoStream").get("ObjectRef")}"]')
    frame_rate_esperado = round(TICKS_POR_SEGUNDO / 25.0)
    duracion_esperada = round(TICKS_POR_SEGUNDO * 10.0)
    assert int(video_stream.find("FrameRate").text) == frame_rate_esperado
    assert int(video_stream.find("Duration").text) == duracion_esperada


def test_clonar_clip_sony_y_dji_comparten_el_mismo_lut_sin_clonarlo(raiz, tmp_path):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)

    clon_1 = prproj_generador.clonar_clip(
        raiz, archetipos["sony"], asignador, ruta_archivo=tmp_path / "a.mp4",
        nombre_en_premiere="a", label_name="BE.Prefs.LabelColors.1",
        label_color=1, datos_probe=_probe_falso())
    clon_2 = prproj_generador.clonar_clip(
        raiz, archetipos["sony"], asignador, ruta_archivo=tmp_path / "b.mp4",
        nombre_en_premiere="b", label_name="BE.Prefs.LabelColors.1",
        label_color=1, datos_probe=_probe_falso())

    master_1 = raiz.find(f'.//MasterClip[@ObjectUID="{clon_1.master_clip_uid}"]')
    master_2 = raiz.find(f'.//MasterClip[@ObjectUID="{clon_2.master_clip_uid}"]')
    ref_1 = master_1.find("VideoComponentChain").get("ObjectRef")
    ref_2 = master_2.find("VideoComponentChain").get("ObjectRef")
    assert ref_1 == ref_2 == archetipos["sony"].video_component_chain_id
    # Solo hay UN VideoComponentChain con ese ObjectID en todo el documento
    # -- no se clonó, se compartió.
    assert len(raiz.findall(f'.//VideoComponentChain[@ObjectID="{ref_1}"]')) == 1


def test_clonar_clip_otra_no_tiene_video_component_chain(raiz, tmp_path):
    archetipos = prproj_plantilla.archetipos_de_clip(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)

    clon = prproj_generador.clonar_clip(
        raiz, archetipos["otra"], asignador, ruta_archivo=tmp_path / "c.mp4",
        nombre_en_premiere="c", label_name="BE.Prefs.LabelColors.5",
        label_color=5, datos_probe=_probe_falso())

    master = raiz.find(f'.//MasterClip[@ObjectUID="{clon.master_clip_uid}"]')
    assert master.find("VideoComponentChain") is None
```

- [ ] **Paso 2: correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -v`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Paso 3: escribir `src/clasificador_video/prproj_generador.py`**
  (primera parte -- `clonar_clip`)

```python
"""Arma el .prproj final: clona un clip de referencia por cada clip real,
las 5 secuencias, y arma el árbol de bins. Ver el plan para la arquitectura
completa (docs/superpowers/plans/2026-09-23-generar-prproj-directo.md).

Sin Qt.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from clasificador_video.prproj_plantilla import ArchetipoDeClip
from clasificador_video.prproj_xml import AsignadorDeIds, clonar_por_cierre

# Confirmado con dos clips reales de testcolorlut.prproj -- ver la
# sección "Riesgo central" del plan.
TICKS_POR_SEGUNDO = 254016000000


@dataclass(frozen=True)
class ClipClonado:
    clip_project_item_uid: str
    master_clip_uid: str
    media_uid: str


def _todos_los_video_streams_y_media(raiz: ET.Element, master_clip_uid: str):
    """Los `Media` (y su `VideoStream`/`AudioStream`) alcanzables desde un
    `MasterClip`, siguiendo `Source` -> `VideoMediaSource`/
    `AudioMediaSource` -> `Media` -> `VideoStream`/`AudioStream`."""
    master = raiz.find(f'.//MasterClip[@ObjectUID="{master_clip_uid}"]')
    for clip_ref in master.findall(".//Clip"):
        source_ref = None
        video_clip = raiz.find(f'.//VideoClip[@ObjectID="{clip_ref.get("ObjectRef")}"]')
        audio_clip = raiz.find(f'.//AudioClip[@ObjectID="{clip_ref.get("ObjectRef")}"]')
        for candidato in (video_clip, audio_clip):
            if candidato is None:
                continue
            source = candidato.find(".//Source")
            if source is not None:
                source_ref = source.get("ObjectRef")
        if source_ref is None:
            continue
        for tipo in ("VideoMediaSource", "AudioMediaSource"):
            fuente = raiz.find(f'.//{tipo}[@ObjectID="{source_ref}"]')
            if fuente is None:
                continue
            media_ref = fuente.find(".//Media")
            if media_ref is None:
                continue
            media = raiz.find(f'.//Media[@ObjectUID="{media_ref.get("ObjectURef")}"]')
            if media is not None:
                yield media


def clonar_clip(raiz: ET.Element, archetipo: ArchetipoDeClip,
                 asignador: AsignadorDeIds, *, ruta_archivo: Path,
                 nombre_en_premiere: str, label_name: str,
                 label_color: int, datos_probe: dict) -> ClipClonado:
    """Clona el `MasterClip` (y su `ClipProjectItem`) de `archetipo`,
    apunta su `Media` a `ruta_archivo`, y reescribe nombre, color y tiempo.

    El `VideoComponentChain` del LUT (si `archetipo` tiene uno) es una
    FRONTERA: se queda compartido con el original, nunca se clona -- así
    es como el spike validó aplicar un LUT a más de un clip (experimento 5
    del RESULTADO).
    """
    fronteras = set()
    if archetipo.video_component_chain_id is not None:
        fronteras.add(("ObjectID", archetipo.video_component_chain_id))

    # Encontrar el ClipProjectItem que apunta a este MasterClip -- es el
    # punto de entrada real a clonar (el MasterClip solo no trae el Name
    # que ve Bruno en Premiere; eso vive en el ClipProjectItem).
    item_original = None
    for candidato in raiz.findall("ClipProjectItem"):
        master_ref = candidato.find("MasterClip")
        if master_ref is not None and master_ref.get("ObjectURef") == archetipo.master_clip_uid:
            item_original = candidato
            break
    if item_original is None:
        raise ValueError(f"No se encontró ClipProjectItem para {archetipo.master_clip_uid}")

    mapa = clonar_por_cierre(raiz, "ObjectUID", item_original.get("ObjectUID"),
                              asignador, fronteras=fronteras)

    item_clon = mapa[("ObjectUID", item_original.get("ObjectUID"))]
    master_clon_uid = mapa[("ObjectUID", archetipo.master_clip_uid)][1]

    item_clon.find(".//Name").text = nombre_en_premiere
    etiqueta = item_clon.find(".//Column.PropertyText.Label")
    if etiqueta is not None:
        etiqueta.text = label_name

    media_uid = None
    for media in _todos_los_video_streams_y_media(raiz, master_clon_uid):
        media_uid = media.get("ObjectUID")
        for campo in ("RelativePath", "FilePath", "ActualMediaFilePath"):
            nodo = media.find(campo)
            if nodo is not None:
                nodo.text = str(ruta_archivo)
        titulo = media.find("Title")
        if titulo is not None:
            titulo.text = ruta_archivo.name

        duracion_ticks = round(TICKS_POR_SEGUNDO * datos_probe["duration_seconds"])
        video_stream_ref = media.find("VideoStream")
        if video_stream_ref is not None:
            stream = raiz.find(f'.//VideoStream[@ObjectID="{video_stream_ref.get("ObjectRef")}"]')
            if stream is not None:
                frame_rate_ticks = round(TICKS_POR_SEGUNDO / datos_probe["fps"])
                stream.find("FrameRate").text = str(frame_rate_ticks)
                stream.find("Duration").text = str(duracion_ticks)
                rect = stream.find("FrameRect")
                if rect is not None:
                    rect.text = f'0,0,{datos_probe["width"]},{datos_probe["height"]}'
                orientacion = stream.find("OriginalImageOrientationType")
                if orientacion is not None:
                    from clasificador_video.orientacion_premiere import orientacion_de
                    orientacion.text = str(orientacion_de(datos_probe.get("rotation", 0)))
        audio_stream_ref = media.find("AudioStream")
        if audio_stream_ref is not None:
            stream = raiz.find(f'.//AudioStream[@ObjectID="{audio_stream_ref.get("ObjectRef")}"]')
            if stream is not None and stream.find("FrameRate") is not None:
                stream.find("Duration").text = str(duracion_ticks)

    for clip_tag in ("VideoClip", "AudioClip"):
        for clon in mapa.values():
            if clon.tag != clip_tag:
                continue
            for campo in ("asl.clip.label.name",):
                nodo = clon.find(f".//{campo}")
                if nodo is not None:
                    nodo.text = label_name
            for campo in ("asl.clip.label.color",):
                nodo = clon.find(f".//{campo}")
                if nodo is not None:
                    nodo.text = str(label_color)

    return ClipClonado(
        clip_project_item_uid=item_clon.get("ObjectUID"),
        master_clip_uid=master_clon_uid,
        media_uid=media_uid,
    )
```

Nota: `datos_probe` en las pruebas de este paso no siempre trae `width`/
`height` -- agregarlos al diccionario `_probe_falso` de la prueba antes de
correr (`"width": 1080, "height": 1920`), y ajustar el código de arriba
para no reventar si faltan (usar `.get`).

- [ ] **Paso 4: correr y depurar hasta que pasen**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -v`
Expected: 5 passed. Si algún `find` da `None` inesperado, es señal de que
la estructura real de `testcolorlut.prproj` tiene un detalle distinto al
descrito en el plan para ESE caso puntual -- imprimir
`ET.tostring(nodo_relevante)` para verlo y ajustar el `find`, no adivinar.

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/prproj_generador.py tests/test_prproj_generador.py
git commit -m "Clonar un clip real: tiempo, nombre, color y LUT compartido"
```

---

## Tarea 11: Las 5 secuencias de referencia

**Files:**
- Modify: `src/clasificador_video/prproj_plantilla.py` (completar
  `archetipos_de_secuencia`)
- Modify: `src/clasificador_video/prproj_generador.py` (agregar
  `clonar_secuencia`)
- Modify: `tests/test_prproj_plantilla.py` (quitar el skip)
- Modify: `tests/test_prproj_generador.py`

- [ ] **Paso 1: inspeccionar cómo se ve una `Sequence` real**

```bash
python3 -c "
import gzip, xml.etree.ElementTree as ET
raiz = ET.fromstring(gzip.open('recursos/premiere/TemplateColorLuts.prproj','rb').read())
for seq in raiz.findall('Sequence'):
    print(ET.tostring(seq, encoding='unicode')[:2000])
    print('---')
"
```

Leer la salida con calma: buscar dónde vive el ancho/alto (probablemente
`VideoFrameWidth`/`VideoFrameHeight` o un `Rect` como el que ya se vio en
`SequenceSettings`) y el frame rate, dentro de la `Sequence` o de un
`ObjectRef` que cuelgue de ella. **Escribir lo que se encontró como
comentario al tope de la función `archetipos_de_secuencia`, con las líneas
reales copiadas** -- no seguir a la Tarea 2 de este paso sin eso, porque el
`find` de abajo depende de los nombres reales de estos campos.

- [ ] **Paso 2: completar `archetipos_de_secuencia` en `prproj_plantilla.py`**

```python
def archetipos_de_secuencia(raiz: ET.Element) -> dict[str, ET.Element]:
    """Una `Sequence` (el elemento `Sequence` completo) por cada una de
    las 6 claves de `FORMATOS_DE_SECUENCIA`, ubicada por su ancho/alto
    reales -- no por el nombre que Bruno le haya puesto en la plantilla.
    """
    encontrados: dict[str, ET.Element] = {}
    for secuencia in raiz.findall("Sequence"):
        ancho, alto = _ancho_alto_de_secuencia(secuencia)  # ver Paso 1
        for clave, (a, h, _fps) in FORMATOS_DE_SECUENCIA.items():
            if clave in encontrados:
                continue
            if (ancho, alto) == (a, h):
                encontrados[clave] = secuencia
                break

    faltan = set(FORMATOS_DE_SECUENCIA) - encontrados.keys()
    if faltan:
        raise PlantillaIncompleta(
            "La plantilla no tiene secuencia de referencia para: "
            + ", ".join(sorted(faltan)) + ". Revisar la Tarea 0 del plan.")
    return encontrados
```

**`_ancho_alto_de_secuencia` se escribe con lo que salga del Paso 1** --
no está definida arriba a propósito, para no inventar el nombre del campo
antes de verlo. Nota importante: `4k_9x16` y `2_7k_9x16` tienen el MISMO
ancho/alto (2160×3840, ver la tabla de `secuencia.js` -- así está también
en el código de hoy, no es un error de este plan). Para distinguir esos
dos casos específicamente, usar el ORDEN en que aparecen las secuencias en
el archivo (la primera que calce 2160×3840 es `4k_9x16`, la segunda es
`2_7k_9x16`) -- Bruno debe crearlas en ESE orden en la Tarea 0, Paso 6 (ya
están listadas en ese orden en la tabla).

- [ ] **Paso 3: quitar el `@pytest.mark.skip` de
  `test_archetipos_de_secuencia_completos` en `tests/test_prproj_plantilla.py`**

- [ ] **Paso 4: correr**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_plantilla.py -v`
Expected: 7 passed, 0 skipped

- [ ] **Paso 5: agregar `clonar_secuencia` a `prproj_generador.py`**

```python
def clonar_secuencia(raiz: ET.Element, archetipo_secuencia: ET.Element,
                      asignador: AsignadorDeIds, *, nombre: str) -> ET.Element:
    """Clona una `Sequence` de referencia completa (cierre de referencias,
    sin fronteras -- una secuencia vacía no comparte nada que valga la
    pena reusar) y le pone `nombre`."""
    uid_o_id = archetipo_secuencia.get("ObjectUID") or archetipo_secuencia.get("ObjectID")
    tipo_ancla = "ObjectUID" if archetipo_secuencia.get("ObjectUID") else "ObjectID"

    mapa = clonar_por_cierre(raiz, tipo_ancla, uid_o_id, asignador)
    clon = mapa[(tipo_ancla, uid_o_id)]
    nombre_nodo = clon.find(".//Name")
    if nombre_nodo is not None:
        nombre_nodo.text = nombre
    return clon
```

- [ ] **Paso 6: agregar la prueba a `tests/test_prproj_generador.py`**

```python
def test_clonar_secuencia_le_pone_el_nombre(raiz):
    from clasificador_video import prproj_plantilla
    archetipos = prproj_plantilla.archetipos_de_secuencia(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)

    clon = prproj_generador.clonar_secuencia(
        raiz, archetipos["4k_9x16"], asignador, nombre="IAV-2609.10-A 4K 9:16")

    assert clon.find(".//Name").text == "IAV-2609.10-A 4K 9:16"


def test_clonar_secuencia_no_toca_la_original(raiz):
    from clasificador_video import prproj_plantilla
    archetipos = prproj_plantilla.archetipos_de_secuencia(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)
    nombre_original = archetipos["4k_16x9"].find(".//Name").text

    prproj_generador.clonar_secuencia(
        raiz, archetipos["4k_16x9"], asignador, nombre="otro nombre")

    assert archetipos["4k_16x9"].find(".//Name").text == nombre_original
```

- [ ] **Paso 7: correr**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py tests/test_prproj_plantilla.py -v`
Expected: todos pasan

- [ ] **Paso 8: commit**

```bash
git add src/clasificador_video/prproj_plantilla.py src/clasificador_video/prproj_generador.py \
        tests/test_prproj_plantilla.py tests/test_prproj_generador.py
git commit -m "Localizar y clonar las 5 secuencias de referencia"
```

---

## Tarea 12: Árbol de bins desde el manifiesto

**Files:**
- Modify: `src/clasificador_video/prproj_generador.py`
- Modify: `tests/test_prproj_generador.py`

Arma los 7 bins fijos de `estructura.js`
(`CARPETAS_DEL_PROYECTO`) y, dentro de "02. Clip", un bin por cuarto/unidad,
numerado con `numero_de_cuarto.con_numero` y con la marca de cámara de
`marca_camara.nombre_del_cuarto_con_marca`.

- [ ] **Paso 1: escribir la prueba que falla**

```python
def test_crear_bin_hijo_lo_agrega_al_container_del_padre(raiz):
    from clasificador_video import prproj_plantilla
    archetipo_bin = prproj_plantilla.archetipo_de_bin(raiz)
    padre = raiz.find('RootProjectItem')
    asignador = prproj_xml.AsignadorDeIds(raiz)

    bin_nuevo = prproj_generador.crear_bin_hijo(
        raiz, archetipo_bin, padre, asignador, nombre="02. Clip")

    assert bin_nuevo.find(".//Name").text == "02. Clip"
    items = padre.find("ProjectItemContainer/Items")
    refs = [item.get("ObjectURef") or item.get("ObjectRef") for item in items]
    assert (bin_nuevo.get("ObjectUID") or bin_nuevo.get("ObjectID")) in refs


def test_arbol_de_bins_crea_las_7_carpetas_fijas(raiz):
    from clasificador_video import prproj_plantilla
    archetipo_bin = prproj_plantilla.archetipo_de_bin(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)
    root = raiz.find('RootProjectItem')

    bins = prproj_generador.crear_esqueleto(raiz, archetipo_bin, root, asignador)

    assert list(bins.keys()) == [
        "01. Secuencia", "02. Clip", "03. AE composition", "04. Musica",
        "05. Voz", "06. Graficos", "07. Assets adicionales"]


def test_bin_del_cuarto_numera_y_marca_camara(raiz):
    from clasificador_video import prproj_plantilla
    archetipo_bin = prproj_plantilla.archetipo_de_bin(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)
    root = raiz.find('RootProjectItem')
    bins = prproj_generador.crear_esqueleto(raiz, archetipo_bin, root, asignador)
    clips = [{"categoria_path": ["Cocina"], "bin_sony": True, "bin_dron": False,
              "bin_pocket": False}]

    bin_cuarto = prproj_generador.bin_del_cuarto(
        raiz, archetipo_bin, bins["02. Clip"], asignador,
        categoria_path=["Cocina"], posicion=3, clips_del_manifest=clips)

    assert bin_cuarto.find(".//Name").text == "03. Cocina [SONY]"
```

- [ ] **Paso 2: correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -v -k bin`
Expected: FAIL, `AttributeError`

- [ ] **Paso 3: agregar a `prproj_generador.py`**

```python
from clasificador_video.marca_camara import nombre_del_cuarto_con_marca
from clasificador_video.numero_de_cuarto import con_numero

CARPETAS_DEL_PROYECTO = (
    "01. Secuencia", "02. Clip", "03. AE composition", "04. Musica",
    "05. Voz", "06. Graficos", "07. Assets adicionales",
)


def crear_bin_hijo(raiz: ET.Element, archetipo_bin: ET.Element,
                    padre: ET.Element, asignador: AsignadorDeIds, *,
                    nombre: str) -> ET.Element:
    """Clona `archetipo_bin` (vacío) como hijo de `padre`, con `nombre`."""
    tipo_ancla = "ObjectUID" if archetipo_bin.get("ObjectUID") else "ObjectID"
    ancla_vieja = archetipo_bin.get(tipo_ancla)

    mapa = clonar_por_cierre(raiz, tipo_ancla, ancla_vieja, asignador)
    clon = mapa[(tipo_ancla, ancla_vieja)]
    clon.find(".//Name").text = nombre
    # El bin clonado nace sin items -- limpiar lo que haya heredado del
    # archetipo (debe estar vacío, pero por si acaso).
    items = clon.find("ProjectItemContainer/Items")
    if items is not None:
        for item in list(items):
            items.remove(item)

    ref_padre = padre.find("ProjectItemContainer/Items")
    if ref_padre is None:
        contenedor = padre.find("ProjectItemContainer")
        ref_padre = ET.SubElement(contenedor, "Items", {"Version": "1"})
    nuevo_index = str(len(ref_padre))
    atributo_ref = "ObjectURef" if tipo_ancla == "ObjectUID" else "ObjectRef"
    ET.SubElement(ref_padre, "Item", {
        "Index": nuevo_index, atributo_ref: clon.get(tipo_ancla)})
    return clon


def crear_esqueleto(raiz: ET.Element, archetipo_bin: ET.Element,
                     root: ET.Element, asignador: AsignadorDeIds
                     ) -> dict[str, ET.Element]:
    """Los 7 bins fijos del proyecto, como hijos de `root`."""
    return {nombre: crear_bin_hijo(raiz, archetipo_bin, root, asignador, nombre=nombre)
            for nombre in CARPETAS_DEL_PROYECTO}


def bin_del_cuarto(raiz: ET.Element, archetipo_bin: ET.Element,
                    carpeta_de_clips: ET.Element, asignador: AsignadorDeIds,
                    *, categoria_path: list[str], posicion: int,
                    clips_del_manifest: list) -> ET.Element:
    """El bin de un cuarto (o unidad), numerado y con su marca de cámara.
    `categoria_path` es el camino crudo hasta este nivel (ej. ["Cocina"] o
    ["Casa A", "Cocina"]); `posicion` es su lugar dentro de su padre."""
    nombre_sin_numero = categoria_path[-1]
    con_num = con_numero(nombre_sin_numero, posicion)
    nombre_final = nombre_del_cuarto_con_marca(
        con_num, nombre_sin_numero, clips_del_manifest, categoria_path)
    return crear_bin_hijo(raiz, archetipo_bin, carpeta_de_clips, asignador,
                           nombre=nombre_final)
```

- [ ] **Paso 4: correr y depurar**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -v -k bin`
Expected: 3 passed. Si `crear_bin_hijo` revienta buscando
`ProjectItemContainer` en el archetipo -- confirmar con
`ET.tostring(archetipo_bin)` que de verdad tiene esa forma (viene de
`prproj_plantilla.archetipo_de_bin`, que ya se probó en la Tarea 8).

- [ ] **Paso 5: correr TODO lo escrito hasta ahora, junto**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_xml.py tests/test_prproj_plantilla.py tests/test_prproj_generador.py tests/test_numero_de_cuarto.py tests/test_nombre_de_clip.py tests/test_marca_camara.py tests/test_recursos.py tests/test_probe.py tests/test_orientacion_premiere.py -v`
Expected: todos pasan, ninguno se rompió por los cambios de esta tarea

- [ ] **Paso 6: commit**

```bash
git add src/clasificador_video/prproj_generador.py tests/test_prproj_generador.py
git commit -m "Árbol de bins del proyecto, numerado y con marca de cámara"
```

---

## Tarea 13: Copiar los LUT al proyecto y orquestar todo

**Files:**
- Modify: `src/clasificador_video/prproj_generador.py`
- Modify: `tests/test_prproj_generador.py`

La función final: `generar_prproj(manifest, destino, carpeta_luts_destino)`.
Recibe el `Manifest` que Clipify ya arma hoy (mismos datos que
`manifest.json`), y escribe el `.prproj` completo más los `.cube` que
hagan falta.

- [ ] **Paso 1: escribir la prueba que falla**

```python
def test_generar_prproj_produce_un_archivo_que_se_puede_releer(tmp_path):
    from clasificador_video.manifest import Clip, Guia, Manifest

    manifest = Manifest(
        proyecto="IAV-2609.10-A",
        orientacion="vertical",
        clips=[
            Clip(orden=0, ruta=tmp_path / "sony1.mp4", categoria_path=["Cocina"],
                 fps=59.94, flag="pick", camara="sony"),
            Clip(orden=1, ruta=tmp_path / "dron1.mp4", categoria_path=["Cocina"],
                 fps=59.94, flag="none", camara="dji", bin_dron=True),
        ],
        guia=Guia(orden=["Cocina"]),
        formato_secuencia="4K 9:16",
        crear_secuencias=True,
    )
    for clip in manifest.clips:
        clip.ruta.write_bytes(b"")

    destino = tmp_path / "salida" / "IAV-2609.10-A.prproj"
    carpeta_luts = tmp_path / "salida" / "01. Proyecto premiere" / "LUTs"

    def probe_falso(_ruta):
        return {"width": 2160, "height": 3840, "fps": 59.94,
                "duration_seconds": 6.0, "rotation": 90}

    prproj_generador.generar_prproj(
        manifest, destino, carpeta_luts, probe=probe_falso)

    assert destino.is_file()
    raiz = prproj_xml.leer_prproj(destino)
    assert len(raiz.findall("ClipProjectItem")) >= 2 + 3  # +3 de la plantilla


def test_generar_prproj_copia_solo_los_cube_que_hacen_falta(tmp_path):
    from clasificador_video.manifest import Clip, Manifest

    manifest = Manifest(
        proyecto="Solo Sony", orientacion="horizontal",
        clips=[Clip(orden=0, ruta=tmp_path / "a.mp4", categoria_path=["Sala"],
                     fps=59.94, camara="sony")],
    )
    manifest.clips[0].ruta.write_bytes(b"")
    destino = tmp_path / "s" / "p.prproj"
    carpeta_luts = tmp_path / "s" / "01. Proyecto premiere" / "LUTs"

    def probe_falso(_r):
        return {"width": 1920, "height": 1080, "fps": 59.94,
                "duration_seconds": 3.0, "rotation": 0}

    prproj_generador.generar_prproj(manifest, destino, carpeta_luts, probe=probe_falso)

    assert (carpeta_luts / "SONY-SLOG3.cube").is_file()
    assert not (carpeta_luts / "DJI-DLOGM.cube").is_file()
```

- [ ] **Paso 2: correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -v -k generar_prproj`
Expected: FAIL, `AttributeError`

- [ ] **Paso 3: agregar `generar_prproj` a `prproj_generador.py`**

```python
import shutil

from clasificador_video import recursos
from clasificador_video.nombre_de_clip import nombre_de_clip, numeros_de_clip
from clasificador_video.prproj_plantilla import (
    archetipo_de_bin, archetipos_de_clip, archetipos_de_secuencia,
    FORMATOS_DE_SECUENCIA,
)
from clasificador_video.prproj_xml import escribir_prproj, leer_prproj

# BE.Prefs.LabelColors.N y su valor numérico por cámara -- CONFIRMADOS
# leyendo la plantilla real (Bruno les puso Cerulean/Mango/Violet en la
# Tarea 0). No se adivinan: se leen de los clips de referencia mismos.


def _label_de_camara(raiz: ET.Element, archetipos: dict) -> dict[str, tuple[str, int]]:
    resultado = {}
    for camara, archetipo in archetipos.items():
        item = None
        for candidato in raiz.findall("ClipProjectItem"):
            master_ref = candidato.find("MasterClip")
            if master_ref is not None and master_ref.get("ObjectURef") == archetipo.master_clip_uid:
                item = candidato
                break
        label_name = item.find(".//Column.PropertyText.Label").text
        master_clon_uid = archetipo.master_clip_uid
        video_clip = None
        for vc in raiz.findall(".//VideoClip"):
            asl = vc.find(".//asl.clip.label.color")
            if asl is not None:
                video_clip = vc
        # El color numérico vive junto al nombre del label en el MISMO
        # VideoClip que cuelga de este MasterClip -- se busca siguiendo
        # Clips/Clip -> VideoClip, no por búsqueda global (dos cámaras
        # pueden compartir Index).
        master = raiz.find(f'.//MasterClip[@ObjectUID="{master_clon_uid}"]')
        for clip_ref in master.findall(".//Clip"):
            vc = raiz.find(f'.//VideoClip[@ObjectID="{clip_ref.get("ObjectRef")}"]')
            if vc is not None:
                nombre_nodo = vc.find(".//asl.clip.label.name")
                color_nodo = vc.find(".//asl.clip.label.color")
                if nombre_nodo is not None and color_nodo is not None:
                    resultado[camara] = (nombre_nodo.text, int(color_nodo.text))
                    break
    return resultado


def _camino_del_clip(categoria_path: list[str], guia) -> list[str]:
    """Puerto de `caminoDelClip` de `estructura.js`: agrega el número de
    cuarto/unidad según el orden de la guía."""
    camino = list(categoria_path or [])
    if not camino:
        return ["02. Clip"]
    orden = list(guia.orden) if guia else []
    unidades = list(guia.unidades) if guia else []
    if len(camino) > 1:
        lugar_unidad = next((i for i, u in enumerate(unidades)
                              if u.get("nombre") == camino[0]), -1)
        if lugar_unidad != -1:
            camino[0] = con_numero(camino[0], lugar_unidad + 1)
            orden_unidad = unidades[lugar_unidad].get("orden", [])
            if camino[1] in orden_unidad:
                camino[1] = con_numero(camino[1], orden_unidad.index(camino[1]) + 1)
    else:
        if camino[0] in orden:
            camino[0] = con_numero(camino[0], orden.index(camino[0]) + 1)
    return ["02. Clip"] + camino


def generar_prproj(manifest, destino: Path, carpeta_luts_destino: Path, *,
                    probe=None) -> None:
    """Escribe el `.prproj` completo de `manifest` en `destino`, y copia a
    `carpeta_luts_destino` los `.cube` de las cámaras que aparecen.

    `probe` es inyectable para pruebas -- por default usa
    `clasificador_video.probe.probe_clip`.
    """
    if probe is None:
        from clasificador_video.probe import probe_clip as probe

    raiz = leer_prproj(recursos.template_color_luts())
    asignador = AsignadorDeIds(raiz)
    archetipo_bin = archetipo_de_bin(raiz)
    archetipos_clip = archetipos_de_clip(raiz)
    archetipos_seq = archetipos_de_secuencia(raiz)
    labels = _label_de_camara(raiz, archetipos_clip)
    root = raiz.find("RootProjectItem")

    bins_fijos = crear_esqueleto(raiz, archetipo_bin, root, asignador)

    clips_para_nombres = [{"categoria_path": c.categoria_path} for c in manifest.clips]
    numeros = numeros_de_clip(clips_para_nombres)
    clips_del_manifest_dict = [
        {"categoria_path": c.categoria_path, "bin_sony": c.bin_sony,
         "bin_pocket": c.bin_pocket, "bin_dron": c.bin_dron}
        for c in manifest.clips
    ]

    bins_de_cuarto: dict[tuple, ET.Element] = {}
    camaras_usadas: set[str] = set()

    for i, clip in enumerate(manifest.clips):
        camino = _camino_del_clip(clip.categoria_path, manifest.guia)
        padre = bins_fijos["02. Clip"]
        recorrido = tuple(camino[1:])
        acumulado: tuple = ()
        for nivel, segmento_con_numero in enumerate(camino[1:]):
            acumulado = acumulado + (segmento_con_numero,)
            if acumulado not in bins_de_cuarto:
                categoria_hasta_aqui = clip.categoria_path[:nivel + 1]
                posicion = int(segmento_con_numero.split(".")[0])
                bins_de_cuarto[acumulado] = bin_del_cuarto(
                    raiz, archetipo_bin, padre, asignador,
                    categoria_path=categoria_hasta_aqui, posicion=posicion,
                    clips_del_manifest=clips_del_manifest_dict)
            padre = bins_de_cuarto[acumulado]

        camara = clip.camara if clip.camara in archetipos_clip else "otra"
        camaras_usadas.add(camara)
        marca_camara = nombre_del_cuarto_con_marca(
            "", "", clips_del_manifest_dict, clip.categoria_path)[3:].strip("[]") \
            if False else ""  # la marca de cámara del NOMBRE DE CLIP usa
        # el mismo mapeo bin_sony/bin_pocket/bin_dron pero por CLIP, no por
        # cuarto -- se arma directo abajo con marca_camara.py:
        from clasificador_video.marca_camara import marca_de_camara_del_prefijo
        marca_camara = marca_de_camara_del_prefijo(
            [{"categoria_path": clip.categoria_path, "bin_sony": clip.bin_sony,
              "bin_pocket": clip.bin_pocket, "bin_dron": clip.bin_dron}],
            clip.categoria_path or [clip.ruta.name])

        nombre = nombre_de_clip(
            (clip.categoria_path[-1] if clip.categoria_path else clip.ruta.stem),
            numeros[i], marca_camara, clip.flag)
        label_name, label_color = labels.get(camara, labels["otra"])

        datos_probe = probe(clip.ruta)
        clonar_clip(raiz, archetipos_clip[camara], asignador,
                    ruta_archivo=clip.ruta, nombre_en_premiere=nombre,
                    label_name=label_name, label_color=label_color,
                    datos_probe=datos_probe)

    if manifest.crear_secuencias or manifest.formato_secuencia:
        nombre_base = (manifest.proyecto or "Proyecto").strip() or "Proyecto"
        carpeta_1080p = None
        for clave in FORMATOS_DE_SECUENCIA:
            sufijo = {
                "4k_9x16": "4K 9:16", "2_7k_9x16": "2.7K 9:16",
                "4k_16x9": "4K 16:9", "9x16_1080p": "9:16 1080p",
                "16x9_1080p": "16:9 1080p",
            }[clave]
            padre = bins_fijos["01. Secuencia"]
            if clave.endswith("1080p"):
                if carpeta_1080p is None:
                    carpeta_1080p = crear_bin_hijo(
                        raiz, archetipo_bin, bins_fijos["01. Secuencia"],
                        asignador, nombre="1080p")
                padre = carpeta_1080p
            clonar_secuencia(raiz, archetipos_seq[clave], asignador,
                              nombre=f"{nombre_base} {sufijo}")
            # La secuencia clonada ya se agregó al documento; falta
            # colgarla del bin correcto -- mismo mecanismo que
            # `crear_bin_hijo` usa para los bins, pero para una Sequence
            # (que se referencia por su ClipProjectItem asociado, no por
            # sí misma -- ver Tarea 11, Paso 1, para el nombre real del
            # campo si difiere).

    destino.parent.mkdir(parents=True, exist_ok=True)
    escribir_prproj(raiz, destino)

    carpeta_luts_destino.mkdir(parents=True, exist_ok=True)
    for camara in camaras_usadas:
        origen = recursos.cube_de_camara(camara)
        if origen is not None:
            shutil.copyfile(origen, carpeta_luts_destino / origen.name)
```

**Nota para quien ejecute esta tarea:** el bloque de "colgar la secuencia
clonada del bin correcto" está marcado a propósito como pendiente de un
detalle real (cómo referencia Premiere una `Sequence` desde el
`ProjectItemContainer` de su bin -- si es directo por `ObjectRef`/
`ObjectUID` de la `Sequence` misma, o si hay un `ClipProjectItem`
intermedio como con los clips de video). Resolverlo con la misma técnica
del Paso 1 de la Tarea 11: imprimir el XML alrededor de una `Sequence` real
y del bin que la contiene, ver cuál `Item` de qué `ProjectItemContainer`
apunta a ella, y escribir el `ET.SubElement(...)` que corresponda -- mismo
patrón que ya usa `crear_bin_hijo` para colgar un bin de su padre.

- [ ] **Paso 4: correr y depurar hasta que pasen**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_prproj_generador.py -v`
Expected: todos pasan

- [ ] **Paso 5: correr la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: todo en verde, ni una prueba menos que antes de empezar el plan

- [ ] **Paso 6: commit**

```bash
git add src/clasificador_video/prproj_generador.py tests/test_prproj_generador.py
git commit -m "generar_prproj: orquesta bins, clips, secuencias y copia de LUTs"
```

---

## Tarea 14: `proyecto_colaborativo.py` deja de copiar el .prproj en blanco

**Files:**
- Modify: `src/clasificador_video/proyecto_colaborativo.py`
- Modify: `tests/test_proyecto_colaborativo.py`

- [ ] **Paso 1: leer las pruebas actuales que van a cambiar**

```bash
sed -n '60,170p' tests/test_proyecto_colaborativo.py
```

- [ ] **Paso 2: editar las pruebas que asumían que `.prproj` se copiaba**

En `test_crear_carpeta_de_proyecto_copia_y_renombra_los_templates`, quitar
las aserciones sobre `ruta_prproj`/`resultado.ruta_prproj` -- ese archivo ya
no se crea aquí. Dejar solo las del `.aep`. En
`test_crear_carpeta_de_proyecto_sin_template_premiere_no_crea_nada`, el
nombre y la prueba misma dejan de tener sentido (ya no hay template de
Premiere que falte) -- eliminarla. Ajustar
`test_crear_carpeta_de_proyecto_si_falla_la_copia_no_deja_nada` para que
solo dependa de la copia del `.aep`.

- [ ] **Paso 3: correr y confirmar que las pruebas tocadas fallan** (el
  código viejo todavía copia el `.prproj`)

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto_colaborativo.py -v`
Expected: algunas FAIL (código viejo no calza con las pruebas nuevas)

- [ ] **Paso 4: editar `crear_carpeta_de_proyecto` en `proyecto_colaborativo.py`**

Quitar `template_premiere`, la validación de que exista, y la línea
`shutil.copyfile(template_premiere, ruta_prproj)`. `ResultadoDeCreacion`
deja de tener `ruta_prproj` -- ojo, revisar `app.py` por si usa ese campo
(`grep -n "ruta_prproj" src/clasificador_video/app.py`) y quitar esa
referencia también si existe.

```python
@dataclass(frozen=True)
class ResultadoDeCreacion:
    carpeta_proyecto: Path
    ruta_cvproj: Path
    ruta_aep: Path


def crear_carpeta_de_proyecto(carpeta_proyecto: Path, carpeta_templates: Path,
                              folio: str) -> ResultadoDeCreacion:
    if not carpeta_proyecto.parent.is_dir():
        raise FileNotFoundError(str(carpeta_proyecto.parent))
    if carpeta_proyecto.exists():
        raise FileExistsError(str(carpeta_proyecto))
    template_ae = carpeta_templates / TEMPLATE_AE_NOMBRE
    if not template_ae.is_file():
        raise FileNotFoundError(str(template_ae))

    try:
        carpeta_proyecto.mkdir()
        for nombre in SUBCARPETAS:
            (carpeta_proyecto / nombre).mkdir()

        ruta_aep = carpeta_proyecto / CARPETA_AE / f"{folio}.aep"
        shutil.copyfile(template_ae, ruta_aep)
    except OSError:
        shutil.rmtree(carpeta_proyecto, ignore_errors=True)
        raise
    ruta_cvproj = carpeta_proyecto / CARPETA_CLIPIFY / f"{folio}{proyecto.EXTENSION}"

    return ResultadoDeCreacion(
        carpeta_proyecto=carpeta_proyecto,
        ruta_cvproj=ruta_cvproj,
        ruta_aep=ruta_aep,
    )
```

- [ ] **Paso 5: correr**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto_colaborativo.py -v`
Expected: todos pasan

- [ ] **Paso 6: buscar y arreglar otros usos de `ruta_prproj` en el repo**

```bash
grep -rn "\.ruta_prproj\b" src/ tests/ | grep -v __pycache__
```

Arreglar cada uno que aparezca (probablemente en `app.py`, donde se llama a
`crear_carpeta_de_proyecto`).

- [ ] **Paso 7: correr la suite completa de nuevo**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: todo en verde

- [ ] **Paso 8: commit**

```bash
git add src/clasificador_video/proyecto_colaborativo.py tests/test_proyecto_colaborativo.py src/clasificador_video/app.py
git commit -m "Dejar de copiar un .prproj en blanco al crear el proyecto"
```

---

## Tarea 15: Wiring en la interfaz -- Ctrl+E genera el .prproj

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_generar_prproj.py`

- [ ] **Paso 1: leer el código actual de `_on_export_manifest` y sus
  vecinos**

```bash
grep -n "_on_export_manifest\|export_requested\|Ctrl+E\|escribir_manifest" src/clasificador_video/ui/main_window.py
```

- [ ] **Paso 2: escribir la prueba que falla**

Copiar el patrón de setup de `tests/ui/test_main_window_proyecto.py` (ya
existe, usa `QT_QPA_PLATFORM=offscreen` y monta una `MainWindow` real) --
NO inventar un patrón nuevo.

```python
"""Ctrl+E genera el .prproj directo; el export de manifest.json para el
plugin se mueve a un lugar secundario."""
from unittest.mock import patch

# Copiar el fixture/helper de construcción de MainWindow que ya usa
# tests/ui/test_main_window_proyecto.py (por ejemplo `_ventana_con_clips`
# o el nombre real que tenga ahí).


def test_ctrl_e_llama_a_generar_prproj_no_a_escribir_manifest(ventana_con_clips):
    ventana = ventana_con_clips
    with patch("clasificador_video.ui.main_window.prproj_generador.generar_prproj") as generar:
        ventana._on_generar_prproj()
    generar.assert_called_once()


def test_si_el_prproj_ya_existe_pregunta_antes_de_reemplazar(ventana_con_clips, tmp_path, monkeypatch):
    ventana = ventana_con_clips
    destino = tmp_path / "IAV-2609.10-A.prproj"
    destino.write_bytes(b"ya existia")
    monkeypatch.setattr(ventana, "_ruta_sugerida_del_prproj", lambda: str(destino))

    respuestas = []
    def confirmar_falso(*a, **k):
        respuestas.append(True)
        return True
    monkeypatch.setattr(ventana, "_confirmar_reemplazar_prproj", confirmar_falso)

    with patch("clasificador_video.ui.main_window.prproj_generador.generar_prproj") as generar:
        ventana._on_generar_prproj()

    assert respuestas == [True]
    generar.assert_called_once()
```

(Ajustar nombres de fixtures/helpers exactos al copiar de
`test_main_window_proyecto.py` -- el punto de esta prueba es el
comportamiento, no los nombres literales de arriba.)

- [ ] **Paso 3: correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_generar_prproj.py -v`
Expected: FAIL, `AttributeError: '_on_generar_prproj'`

- [ ] **Paso 4: agregar el wiring en `main_window.py`**

Cambiar la línea que conecta el atajo:

```python
# antes: self.title_bar.export_requested.connect(self._on_export_manifest)
self.title_bar.export_requested.connect(self._on_generar_prproj)
```

y el atajo de teclado (`("Ctrl+E", self._on_export_manifest)` →
`("Ctrl+E", self._on_generar_prproj)`).

Agregar el método nuevo, cerca de `_on_export_manifest`:

```python
def _on_generar_prproj(self) -> None:
    """Ctrl+E: genera el .prproj completo directo, sin pasar por el
    plugin. Reemplaza el export de manifest.json como acción principal
    -- ver spec 2026-09-23-generar-prproj-directo-design.md."""
    from clasificador_video import prproj_generador

    destino = Path(self._ruta_sugerida_del_prproj())
    if destino.is_file():
        if not self._confirmar_reemplazar_prproj(destino):
            return

    carpeta_luts = destino.parent / "LUTs"
    manifest = self._armar_manifest()  # la misma construcción que ya usaba escribir_manifest
    try:
        prproj_generador.generar_prproj(manifest, destino, carpeta_luts)
    except Exception as exc:
        self._mostrar_error_generando_prproj(str(exc))
        return
    self._avisar_prproj_generado(destino)

def _ruta_sugerida_del_prproj(self) -> str:
    return str(self._ruta_sugerida_del_manifest()).replace(".json", ".prproj")

def _confirmar_reemplazar_prproj(self, destino: Path) -> bool:
    from PySide6.QtWidgets import QMessageBox
    respuesta = QMessageBox.question(
        self, "El proyecto ya existe",
        f"Ya existe {destino.name}. ¿Reemplazarlo?",
        QMessageBox.Yes | QMessageBox.No)
    return respuesta == QMessageBox.Yes
```

**Nota:** `_armar_manifest()` no existe todavía como método separado --
`escribir_manifest` hoy arma el `Manifest` Y lo escribe en un solo método
(ver `src/clasificador_video/ui/main_window.py:6031`). Separar esa
construcción en un método propio (`_armar_manifest`) que devuelva el
`Manifest`, y que TANTO `_on_generar_prproj` como el `escribir_manifest`
viejo (Paso 6) lo reusen -- no duplicar la lógica de `_camaras_por_clip`/
`_bin_dron_por_clip`/etc. en dos lados.

Los métodos `_mostrar_error_generando_prproj` y `_avisar_prproj_generado`
son diálogos simples (`QMessageBox.critical`/`QMessageBox.information`) --
copiar el estilo de mensajes ya existentes en el archivo (buscar
`QMessageBox.critical(self,` para el patrón exacto que ya usa el resto de
la app).

- [ ] **Paso 5: correr y depurar**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_generar_prproj.py -v`
Expected: passed

- [ ] **Paso 6: mover el export de manifest.json a un lugar secundario**

Buscar dónde se arma el menú/los botones de `title_bar` o el menú
principal (`grep -n "QMenu\|addAction" src/clasificador_video/ui/main_window.py`
y revisar `title_bar.py` si el botón vive ahí). Agregar una entrada de
menú "Exportar manifest para el plugin (respaldo)" que llame al
`_on_export_manifest` de siempre (que sigue intacto, solo deja de tener el
atajo `Ctrl+E`).

- [ ] **Paso 7: correr la suite de UI completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/ -q`
Expected: todo en verde

- [ ] **Paso 8: commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_generar_prproj.py
git commit -m "Ctrl+E genera el .prproj directo; el export para el plugin queda de respaldo"
```

---

## Tarea 16: Regresión completa y checkpoint manual en Premiere

**Este es el último paso, y el único que de verdad certifica que "nada se
rompió".** Las pruebas automáticas prueban que el código hace lo que el
código dice que hace -- no prueban que Premiere abra el archivo.

- [ ] **Paso 1: suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: todo en verde, mismo número de pruebas que las que había antes de
empezar el plan más todas las nuevas de este plan

- [ ] **Paso 2: correr también el corredor de JavaScript** (el plugin no se
  tocó, pero confirmar que sigue sano)

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todas pasan, 0 fallidas

- [ ] **Paso 3: generar un `.prproj` real con un proyecto de prueba
  chico** (2-3 clips, no el shooting completo de Bruno todavía)

Esto lo corre Codex desde Clipify (o un script de prueba que llame
`generar_prproj` directo) contra 2-3 archivos MP4 reales cortos, de cámaras
distintas (uno sony, uno dji si hay a la mano).

- [ ] **Paso 4: CHECKPOINT MANUAL -- Bruno abre el `.prproj` generado en
  Premiere y confirma, uno por uno:**

  - [ ] Abre sin error ni diálogo de "proyecto dañado"
  - [ ] Los 7 bins fijos están, en el orden correcto
  - [ ] El clip está dentro de su bin de cuarto, con el número y la marca
        de cámara correctos en el nombre de la carpeta
  - [ ] El nombre del clip tiene el símbolo de estado correcto (★/✓/✕/nada)
  - [ ] El color del clip en el panel de proyecto es el de su cámara
        (Cerulean para Sony, Mango para dron)
  - [ ] El clip reproduce (no está offline) y se ve del lado correcto
        (vertical/horizontal según corresponda, sin voltear)
  - [ ] La duración del clip en el timeline/monitor es la real del
        archivo, no la de 6 segundos de la plantilla
  - [ ] El Lumetri del clip trae el LUT correcto (Input LUT apunta al
        `.cube` DENTRO de la carpeta del proyecto, no a
        `/Users/brunogutierrez/Library/...`)
  - [ ] Las 5 secuencias existen, vacías, en "01. Secuencia" (las dos
        1080p adentro de su subcarpeta), con el ancho/alto/fps correctos

  Si algo de esta lista falla, **no se sigue adelante**: se abre un
  `docs/superpowers/RESULTADO-<fecha>-<lo que falló>.md` documentando
  exactamente qué se vio, y se corrige antes de continuar -- mismo patrón
  que ya sigue este repo para cada hallazgo real en Premiere.

- [ ] **Paso 5: actualizar `docs/superpowers/CONTEXTO-Y-METAS.md`** con el
  nuevo estado (generación directa disponible, plugin como respaldo,
  pendiente probar con un shooting real grande).

- [ ] **Paso 6: commit final de documentación**

```bash
git add docs/superpowers/CONTEXTO-Y-METAS.md
git commit -m "Actualizar el estado del proyecto: generación directa del .prproj disponible"
```

- [ ] **Paso 7 (fuera de este plan, para cuando Bruno lo pida):** probar
  con un shooting real grande (cientos de clips, proxies, clips sin
  clasificar, rutas con caracteres especiales) antes de considerar esta vía
  la forma normal de exportar y de siquiera empezar a hablar de retirar el
  plugin UXP.

---

## Self-review de este plan

**Cobertura del spec:** las 5 secciones del spec aprobado (unificar los dos
momentos de tocar el `.prproj`, generación de una sola vez con aviso si ya
existe, plantilla con LUT ya validados, carpeta de LUTs por proyecto,
Ctrl+E como acción principal) tienen tarea: Tareas 14+15 (unificar/aviso),
Tarea 0+1 (plantilla), Tarea 13 (carpeta de LUTs), Tarea 15 (Ctrl+E).

**Honestidad sobre lo no verificado:** dos piezas de este plan son
HIPÓTESIS a confirmar durante la ejecución, marcadas explícitamente en el
texto de la tarea correspondiente, no presentadas como hechos: el mapeo de
rotación (Tarea 9) y el nombre exacto de los campos de ancho/alto de una
`Sequence` (Tarea 11, Paso 1). Todo lo demás (estructura de Bin/ClipItem/
MasterClip/Media/VideoStream, la constante de ticks, los nombres de campo
de tiempo) se verificó leyendo un `.prproj` real durante este mismo
brainstorm, con evidencia citada en el texto.

**Consistencia de tipos:** `ArchetipoDeClip`, `ClipClonado`,
`AsignadorDeIds`, `clonar_por_cierre` se usan con la misma firma en todas
las tareas que los tocan (verificado al escribir este plan, releyendo cada
tarea después de definir la anterior).
