# Un color por cámara y una estructura de carpetas — plan de implementación

> **Para quien lo ejecute:** SUB-SKILL OBLIGATORIA: usa
> `superpowers:subagent-driven-development` (recomendada) o
> `superpowers:executing-plans` para llevarlo tarea por tarea. Los pasos van
> con casilla (`- [ ]`) para ir marcando.

**Meta:** que al importar a Premiere cada clip llegue con el color de su
cámara, los destacados con `★` en el nombre, y todo acomodado en la
estructura de siete carpetas de Bruno.

**Arquitectura:** el dato nuevo —la cámara— es una propiedad del **bin**, se
adivina del nombre de los archivos y se corrige desde el menú del bin. Viaja
al plugin como un campo del clip en el manifiesto (`"camara": "sony"`), y es
el **plugin** quien traduce cámara→color y quien conoce el árbol de carpetas
—igual que hoy traduce `flag`→color— para que esa política viva en un solo
lugar.

**Herramientas:** Python 3 + PySide6 (app), JavaScript UXP (plugin de
Premiere), pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-color-por-camara-y-carpetas-design.md`

**La suite corre completa, siempre:**
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

---

## Archivos que se tocan

**Se crean:**

| Archivo | De qué es responsable |
|---|---|
| `src/clasificador_video/camaras.py` | La única definición de qué cámara es un archivo y qué cámara es un bin. Sin Qt, sin disco. |
| `tests/test_camaras.py` | Sus pruebas. |
| `uxp-plugin/js/estructura.js` | El árbol de siete carpetas de Premiere y dónde cuelgan los clips. |
| `uxp-plugin/js/nombre.js` | El `★` del destacado, idempotente. |

**Se modifican:**

| Archivo | Qué cambia |
|---|---|
| `src/clasificador_video/bins.py` | `Bin` gana `camara`; se serializa y se restaura. |
| `src/clasificador_video/manifest.py` | `Clip` gana `camara`; sale en `to_dict`. |
| `src/clasificador_video/ui/theme.py` | Los tres colores de cámara para la app. |
| `src/clasificador_video/ui/clip_sheet.py` | El submenú `Cámara ▸` y la marquita pintada por cámara. |
| `src/clasificador_video/ui/main_window.py` | Adivinar la cámara al importar, conectar el menú, mandarla al manifiesto. |
| `uxp-plugin/js/label.js` | La tabla de color pasa de estado a cámara. |
| `uxp-plugin/js/processManifest.js` | Crea las siete carpetas, antepone `02. Clip`, pone el `★`, avisa de los que se mueven. |
| `uxp-plugin/index.html` | Carga los dos scripts nuevos. |

---

# FASE 1 — La cámara como dato (Python puro)

## Tarea 1: el módulo que sabe de cámaras

**Archivos:**
- Crear: `src/clasificador_video/camaras.py`
- Test: `tests/test_camaras.py`

- [ ] **Paso 1: escribir las pruebas que fallan**

Crea `tests/test_camaras.py`:

```python
from pathlib import Path

from clasificador_video.camaras import (
    CAMARAS, DJI, OTRA, SONY, camara_de_archivo, camara_de_bin,
)


def test_un_archivo_del_dron_se_reconoce_por_su_nombre():
    assert camara_de_archivo(Path("/x/DJI_20260817182345_0081_D.MP4")) == DJI


def test_lo_que_no_dice_DJI_se_asume_sony():
    """La regla de Bruno, tal cual la dijo: «los de DJI por lo general
    tienen el nombre DJI, los que no por lo general serán sony»."""
    assert camara_de_archivo(Path("/x/20260817_PIB0016.MP4")) == SONY
    assert camara_de_archivo(Path("/x/C0001.MP4")) == SONY


def test_el_DJI_del_nombre_no_distingue_mayusculas():
    assert camara_de_archivo(Path("/x/dji_0081.mp4")) == DJI


def test_solo_cuenta_el_nombre_del_archivo_no_la_carpeta():
    """Una carpeta «02. VIDEO DRONE/DJI» con material de la Sony adentro no
    puede volver dron a esos clips: lo que identifica a la cámara es cómo
    NOMBRA ella sus archivos, no dónde los guardó Bruno."""
    assert camara_de_archivo(Path("/DJI/20260817_PIB0016.MP4")) == SONY


def test_un_bin_toma_la_camara_de_la_mayoria():
    rutas = [Path("/x/DJI_0001.MP4"), Path("/x/DJI_0002.MP4"),
             Path("/x/20260817_PIB0016.MP4")]
    assert camara_de_bin(rutas) == DJI


def test_un_empate_se_va_a_sony():
    """No hay razón para preferir el dron en un empate, y hace falta UNA
    respuesta: es la cámara con la que Bruno graba casi todo."""
    assert camara_de_bin([Path("/x/DJI_0001.MP4"), Path("/x/C0001.MP4")]) == SONY


def test_un_bin_vacio_es_sony():
    """Un bin creado con «+ Bin nuevo» todavía no tiene archivos. Tiene que
    salir con una cámara puesta igual, o el encabezado no sabría qué pintar."""
    assert camara_de_bin([]) == SONY


def test_otra_nunca_sale_de_adivinar():
    """`otra` es la válvula para una cámara que no es ninguna de las dos, y
    solo la pone Bruno a mano."""
    supuestas = [camara_de_archivo(Path(f"/x/{n}")) for n in
                 ("DJI_1.MP4", "C0001.MP4", "otra_cosa.mov", "OTRA.mp4")]
    assert OTRA not in supuestas


def test_las_camaras_validas_son_tres_y_estan_en_orden_de_menu():
    assert CAMARAS == (SONY, DJI, OTRA)
```

- [ ] **Paso 2: correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_camaras.py -q
```
Se espera: `ModuleNotFoundError: No module named 'clasificador_video.camaras'`.

- [ ] **Paso 3: escribir el módulo**

Crea `src/clasificador_video/camaras.py`:

```python
"""De qué cámara salió un clip, y por lo tanto de qué color llega a Premiere.

Vive aparte de `bins.py` a proposito: `BinTree` sabe QUE bin tiene que
camara, y este modulo sabe COMO se averigua. Son dos preguntas distintas y
la segunda es la unica que mira nombres de archivo.

Sin Qt y sin tocar disco: se responde con el nombre, no abriendo el video.
Abrir 205 archivos para leerles los metadatos al importar seria pagar
segundos por un dato que el nombre ya trae.
"""
from __future__ import annotations

from pathlib import Path

SONY = "sony"
DJI = "dji"
OTRA = "otra"

# En el orden en que salen en el menu del bin.
CAMARAS = (SONY, DJI, OTRA)

# Lo que Bruno dijo, y es la regla entera: «los de DJI por lo general tienen
# el nombre DJI, los que no por lo general serán sony».
_MARCA_DEL_DRON = "dji"


def camara_de_archivo(ruta: Path) -> str:
    """La camara de UN archivo, por su nombre.

    Solo el nombre del archivo, nunca la carpeta: una carpeta que se llame
    «02. VIDEO DRONE» puede tener material de la Sony adentro --pasa cuando
    se copia una tarjeta al lugar equivocado-- y lo que identifica a una
    camara es como NOMBRA ella sus archivos.

    Nunca devuelve `OTRA`: esa es la valvula para lo que no es ninguna de
    las dos, y solo se pone a mano.
    """
    return DJI if _MARCA_DEL_DRON in ruta.name.lower() else SONY


def camara_de_bin(rutas: list[Path]) -> str:
    """La camara de una tanda: la de la mayoria de sus archivos.

    Por mayoria y no por el primero, porque el primero es un accidente del
    orden en que llegaron. Un bin con 70 del dron y uno de la Sony que se
    coló es del dron, y decirlo al revés pintaría 70 clips mal.

    Un empate --y una lista vacia-- se va a `SONY`: hace falta UNA respuesta,
    y es la camara con la que Bruno graba casi todo. Un bin recien creado con
    «+ Bin nuevo» todavia no tiene archivos y tambien pasa por aqui.
    """
    del_dron = sum(1 for r in rutas if camara_de_archivo(r) == DJI)
    return DJI if del_dron * 2 > len(rutas) else SONY
```

- [ ] **Paso 4: correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_camaras.py -q
```
Se espera: 9 passed.

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/camaras.py tests/test_camaras.py
git commit -m "$(printf 'Saber de qué cámara es cada archivo por su nombre\n\nLa regla la dio Bruno: DJI en el nombre es el dron, lo demás es la\nSony. Vive en su propio módulo y no en bins.py porque son dos preguntas\ndistintas -- BinTree sabe QUÉ bin tiene qué cámara, y esto sabe CÓMO se\naverigua.\n\nMira solo el nombre del archivo, nunca la carpeta: una carpeta llamada\n«VIDEO DRONE» puede tener material de la Sony adentro, y lo que\nidentifica a una cámara es cómo nombra ella sus archivos.\n\nUn bin toma la cámara de la mayoría de sus archivos, no la del primero:\nel primero es un accidente del orden en que llegaron.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Tarea 2: el bin guarda su cámara

**Archivos:**
- Modificar: `src/clasificador_video/bins.py`
- Test: `tests/test_bins.py`

- [ ] **Paso 1: escribir las pruebas que fallan**

Agrega al final de `tests/test_bins.py`:

```python
from clasificador_video.camaras import DJI, OTRA, SONY


def test_un_bin_nuevo_adivina_su_camara_de_sus_archivos():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1],
                  rutas=[Path("/dron/DJI_0001.MP4"), Path("/dron/DJI_0002.MP4")])

    assert arbol.camara_de("Dron") == DJI


def test_un_bin_sin_rutas_sale_sony():
    """`crear_vacio` no tiene archivos que mirar todavía."""
    arbol = BinTree()
    arbol.crear_vacio("Bin nuevo")

    assert arbol.camara_de("Bin nuevo") == SONY


def test_bruno_puede_corregir_la_camara():
    arbol = BinTree()
    arbol.agregar("Cámara chica", Path("/x"), [0], rutas=[Path("/x/C0001.MP4")])

    arbol.fijar_camara("Cámara chica", OTRA)

    assert arbol.camara_de("Cámara chica") == OTRA


def test_una_camara_invalida_no_entra():
    """Se ignora en silencio, con el mismo criterio que `renombrar` con un
    nombre repetido: es entrada inválida del usuario, no un error."""
    arbol = BinTree()
    arbol.agregar("Sony", Path("/x"), [0], rutas=[Path("/x/C0001.MP4")])

    arbol.fijar_camara("Sony", "hasselblad")

    assert arbol.camara_de("Sony") == SONY


def test_la_camara_de_un_bin_que_no_existe_es_none():
    assert BinTree().camara_de("Fantasma") is None


def test_sumarle_clips_a_un_bin_NO_le_cambia_la_camara():
    """Este es el que importa. Si sumar recalculara, soltarle a un bin del
    dron una tarjeta de la Sony le voltearía el color a los 70 que ya
    tenía -- y peor: le borraría en silencio la corrección que Bruno hizo
    a mano."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0], rutas=[Path("/dron/DJI_0001.MP4")])

    arbol.sumar("Dron", [1, 2], origen=Path("/sony"))

    assert arbol.camara_de("Dron") == DJI


def test_la_camara_sobrevive_a_guardar_y_volver_a_leer():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0], rutas=[Path("/dron/DJI_0001.MP4")])
    arbol.fijar_camara("Dron", OTRA)

    vuelto = BinTree.from_list(arbol.to_list())

    assert vuelto.camara_de("Dron") == OTRA


def test_una_sesion_vieja_sin_camara_la_calcula_de_sus_clips():
    """Nadie pierde el color por actualizar la app."""
    datos = [{"nombre": "Dron", "origen": "/dron", "clips": [0, 1]}]
    rutas = [Path("/dron/DJI_0001.MP4"), Path("/dron/DJI_0002.MP4")]

    arbol = BinTree.desde_sesion(datos, rutas=rutas)

    assert arbol.camara_de("Dron") == DJI


def test_una_sesion_CON_camara_respeta_lo_que_bruno_puso():
    """El punto exacto donde un descuido le borra una corrección: si al
    restaurar se recalculara, cada apertura desharía lo que él eligió."""
    datos = [{"nombre": "Dron", "origen": "/dron", "clips": [0], "camara": "otra"}]

    arbol = BinTree.desde_sesion(datos, rutas=[Path("/dron/DJI_0001.MP4")])

    assert arbol.camara_de("Dron") == OTRA


def test_una_camara_basura_en_el_archivo_se_recalcula():
    """El autosave se puede tocar a mano. Un valor que no existe no puede
    quedarse: el encabezado no sabría qué pintar."""
    datos = [{"nombre": "Dron", "origen": "/dron", "clips": [0], "camara": "🐔"}]

    arbol = BinTree.desde_sesion(datos, rutas=[Path("/dron/DJI_0001.MP4")])

    assert arbol.camara_de("Dron") == DJI
```

- [ ] **Paso 2: correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
```
Se espera: fallos por `agregar() got an unexpected keyword argument 'rutas'`
y `AttributeError: 'BinTree' object has no attribute 'camara_de'`.

- [ ] **Paso 3: escribir la implementación**

En `src/clasificador_video/bins.py`, agrega el import arriba (junto a los
otros):

```python
from clasificador_video.camaras import CAMARAS, camara_de_bin
```

Cambia el dataclass `Bin`:

```python
@dataclass
class Bin:
    nombre: str
    origen: Path
    clips: list[int] = field(default_factory=list)
    # De que camara es este bin: decide su color en Premiere y el de su
    # marquita en la hoja. Se adivina al crearlo y Bruno la corrige desde
    # el menu del bin; `sumar` NO la recalcula, ver ahi.
    camara: str = "sony"
```

Cambia `agregar` para que reciba las rutas:

```python
    def agregar(self, nombre: str, origen: Path, clips: list[int],
                rutas: list[Path] | None = None) -> str:
        """Devuelve el nombre con el que quedo, que puede no ser el pedido.

        `rutas` son los archivos de esos clips, y sirven para UNA cosa:
        adivinar la camara. Es opcional porque `crear_vacio` no tiene
        ninguno todavia.
        """
        nombre = self._nombre_libre(nombre.strip() or origen.name)
        self._bins.append(Bin(nombre=nombre, origen=origen, clips=list(clips),
                              camara=camara_de_bin(rutas or [])))
        return nombre
```

Agrega los dos métodos nuevos, junto a `origen_de`:

```python
    def camara_de(self, nombre: str) -> str | None:
        for b in self._bins:
            if b.nombre == nombre:
                return b.camara
        return None

    def fijar_camara(self, nombre: str, camara: str) -> None:
        """La corrige a mano. Una camara que no existe se ignora en
        silencio, con el mismo criterio que `renombrar` con un nombre
        repetido: es entrada invalida del usuario, no un error del
        programa."""
        if camara not in CAMARAS:
            return
        for b in self._bins:
            if b.nombre == nombre:
                b.camara = camara
                return
```

En `sumar`, agrega este párrafo al final del docstring (el código no
cambia — lo que importa es que quede escrito por qué NO cambia):

```
        **La camara NO se recalcula aqui, a proposito.** Soltarle a un bin
        del dron una tarjeta de la Sony le voltearia el color a los 70 que
        ya tenia, y peor: le borraria en silencio la correccion que Bruno
        hizo a mano. La camara se decide al crear el bin y se cambia desde
        su menu, en ningun otro lado.
```

En `to_list`, agrega la llave:

```python
    def to_list(self) -> list[dict]:
        return [
            {"nombre": b.nombre, "origen": self._origen_serializado(b),
             "clips": list(b.clips), "camara": b.camara}
            for b in self._bins
        ]
```

En `from_list`, dentro del bucle, cambia la construcción del `Bin`:

```python
            arbol._bins.append(
                Bin(
                    nombre=str(d.get("nombre") or ""),
                    origen=Path(str(d.get("origen") or "")),
                    clips=clips,
                    # Una camara que no existe --archivo tocado a mano, o
                    # de una version futura-- se marca para recalcular en
                    # `desde_sesion`, que es quien tiene las rutas.
                    camara=str(d.get("camara") or ""),
                )
            )
```

En `desde_sesion`, después de `arbol._acotar_a(len(rutas))`, agrega la
recuperación:

```python
        if datos is not None:
            arbol = cls.from_list(datos)
            arbol._acotar_a(len(rutas))
            arbol._completar_camaras(rutas)
            return arbol
        arbol = cls()
        if rutas:
            arbol.agregar(rutas[0].parent.name, rutas[0].parent,
                          list(range(len(rutas))), rutas=rutas)
        return arbol
```

Y agrega el método, junto a `_acotar_a`:

```python
    def _completar_camaras(self, rutas: list[Path]) -> None:
        """Le pone camara a los bins que llegaron sin una valida.

        Son dos casos y se tratan igual porque la respuesta es la misma:
        una sesion de antes de que existieran las camaras (sin la llave), y
        un autosave tocado a mano con un valor que no existe. En los dos, lo
        que hay es un bin sin color y lo unico honesto es volver a
        adivinarlo de sus archivos.

        Lo que NO se toca es un bin con camara valida: ahi puede estar una
        correccion que Bruno hizo a mano, y recalcularla la desharia en cada
        apertura -- sin avisar, que es el peor modo de falla de esta app.
        """
        for b in self._bins:
            if b.camara in CAMARAS:
                continue
            b.camara = camara_de_bin([rutas[i] for i in b.clips
                                      if 0 <= i < len(rutas)])
```

- [ ] **Paso 4: correr las pruebas del módulo y luego la suite entera**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Se espera: todo verde. Si algo se rompe en `test_proyecto.py` o
`test_app.py`, es porque comparan el diccionario del autosave completo y
ahora trae `camara` — actualiza esos valores esperados, no le quites la
llave.

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/bins.py tests/test_bins.py tests/
git commit -m "$(printf 'Guardarle a cada bin de qué cámara es\n\nEl bin ya era «una cámara o una tarjeta» desde el spec de agosto; ahora\nlo dice con todas sus letras y sobrevive a guardar y restaurar.\n\nDos decisiones que valen más que el código:\n\n- `sumar` NO recalcula la cámara. Soltarle a un bin del dron una tarjeta\n  de la Sony le voltearía el color a los 70 que ya tenía, y le borraría\n  en silencio la corrección que Bruno hizo a mano.\n- Al restaurar, solo se recalcula la cámara de los bins que no traen una\n  válida -- sesión vieja, o autosave tocado a mano. Recalcular siempre\n  desharía su corrección en cada apertura.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Tarea 3: la cámara viaja en el manifiesto

**Archivos:**
- Modificar: `src/clasificador_video/manifest.py`
- Test: `tests/test_manifest.py`

- [ ] **Paso 1: escribir las pruebas que fallan**

Agrega al final de `tests/test_manifest.py`:

```python
def test_el_clip_lleva_su_camara_al_manifiesto():
    clip = Clip(orden=1, ruta=Path("/x/DJI_0001.MP4"), categoria_path=["Cocina"],
                fps=59.94, camara="dji")

    assert clip.to_dict()["camara"] == "dji"


def test_un_clip_sin_camara_dicha_sale_sony():
    """El mismo respaldo que en `Bin`: hace falta UNA respuesta, y es la
    cámara con la que Bruno graba casi todo."""
    clip = Clip(orden=1, ruta=Path("/x/C0001.MP4"), categoria_path=["Cocina"],
                fps=59.94)

    assert clip.to_dict()["camara"] == "sony"
```

- [ ] **Paso 2: correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -q
```
Se espera: `TypeError: Clip.__init__() got an unexpected keyword argument
'camara'`.

- [ ] **Paso 3: escribir la implementación**

En `src/clasificador_video/manifest.py`, agrega el campo al dataclass `Clip`,
después de `flag`:

```python
    flag: str = "none"  # "none" | "pick" | "reject"
    # De que camara salio. Decide su ETIQUETA DE COLOR en Premiere -- la
    # traduccion camara→color vive del otro lado, en `label.js`, igual que
    # la de flag→carpeta. Aqui viaja el dato, no la presentacion.
    camara: str = "sony"
    ruta_proxy: Path | None = None
```

Y la llave en `to_dict`, después de `"flag"`:

```python
            "flag": self.flag,
            "camara": self.camara,
```

- [ ] **Paso 4: correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Se espera: todo verde.

- [ ] **Paso 5: commit**

```bash
git add src/clasificador_video/manifest.py tests/test_manifest.py
git commit -m "$(printf 'Mandarle la cámara de cada clip al plugin\n\nViaja el dato («sony», «dji»), no el color. La traducción a etiqueta de\nPremiere vive en label.js, igual que la de flag a carpeta: un solo lugar\ndonde está escrito qué color es cada cosa.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

# FASE 2 — La cámara en la ventana

## Tarea 4: al importar se adivina, al exportar viaja

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py` (dos lugares: donde
  se crea el bin, ~línea 1889, y `_on_export_manifest`, ~línea 4368)
- Test: `tests/ui/test_main_window_camaras.py` (nuevo)

- [ ] **Paso 1: escribir las pruebas que fallan**

Mira primero cómo arma una ventana `tests/ui/test_main_window_bins.py` (o el
archivo de UI que exista más parecido) y **copia ese arreglo**, no inventes
uno nuevo. Crea `tests/ui/test_main_window_camaras.py`:

```python
"""La cámara, de punta a punta: se adivina al importar y llega al manifiesto."""
import json
from pathlib import Path

from clasificador_video.camaras import DJI, OTRA, SONY


def test_un_bin_importado_del_dron_queda_marcado_como_dron(ventana_con_clips):
    ventana = ventana_con_clips(["DJI_0001.MP4", "DJI_0002.MP4"], bin="Dron")

    assert ventana.bins.camara_de("Dron") == DJI


def test_un_bin_de_la_sony_queda_como_sony(ventana_con_clips):
    ventana = ventana_con_clips(["20260817_PIB0016.MP4"], bin="Cámara")

    assert ventana.bins.camara_de("Cámara") == SONY


def test_la_camara_del_bin_llega_al_manifiesto(ventana_con_clips, tmp_path):
    ventana = ventana_con_clips(["DJI_0001.MP4"], bin="Dron")
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    datos = json.loads(destino.read_text())
    assert datos["clips"][0]["camara"] == "dji"


def test_un_clip_sin_bin_sale_sony(ventana_con_clips, tmp_path):
    """Un clip suelto no tiene de dónde sacar la cámara del bin, y tiene que
    llegar con una: sale con el respaldo, no sin campo."""
    ventana = ventana_con_clips(["C0001.MP4"], bin=None)
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["camara"] == "sony"


def test_la_correccion_a_mano_es_la_que_viaja(ventana_con_clips, tmp_path):
    """Lo que Bruno eligió le gana a lo que la app adivinó. Si no, corregir
    no serviría de nada donde único importa."""
    ventana = ventana_con_clips(["DJI_0001.MP4"], bin="Dron")
    ventana.bins.fijar_camara("Dron", OTRA)
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["camara"] == "otra"
```

Y agrega al `tests/ui/conftest.py` (o al `conftest.py` de `tests/` si el de
`ui/` no existe) el fixture, **copiando el arreglo de ventana que ya usen
los otros tests de UI**:

```python
@pytest.fixture
def ventana_con_clips(qtbot, tmp_path):
    """Una ventana con clips de nombres dados, opcionalmente dentro de un bin."""
    from clasificador_video.manifest import Clip
    from clasificador_video.ui.main_window import MainWindow

    def armar(nombres, bin=None):
        rutas = []
        for n in nombres:
            ruta = tmp_path / n
            ruta.write_bytes(b"")
            rutas.append(ruta)
        ventana = MainWindow()
        qtbot.addWidget(ventana)
        clips = [Clip(orden=i + 1, ruta=r, categoria_path=[], fps=59.94)
                 for i, r in enumerate(rutas)]
        ventana.load_clips(clips)
        if bin is not None:
            ventana.bins.agregar(bin, tmp_path, list(range(len(clips))),
                                 rutas=rutas)
        return ventana

    return armar
```

- [ ] **Paso 2: correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_camaras.py -q
```
Se espera: `AttributeError: 'MainWindow' object has no attribute
'escribir_manifest'` en cuatro de las cinco.

- [ ] **Paso 3: partir `_on_export_manifest` en dos**

Hoy `_on_export_manifest` hace dos cosas: pregunta (diálogos) y escribe. La
parte que escribe se saca a su propio método para poder probarla sin abrir
ningún diálogo — **y sin `exec()`**, que es lo que colgaba la suite bajo
`offscreen` antes de la F3.

En `src/clasificador_video/ui/main_window.py`, reemplaza el final de
`_on_export_manifest` (desde `manifest = Manifest(` hasta
`manifest.write_json(Path(path))`) por:

```python
        self.escribir_manifest(Path(path))

    def escribir_manifest(self, destino: Path) -> None:
        """Arma el manifiesto y lo escribe. Sin diálogos: es la parte
        probable, y `_on_export_manifest` es la que pregunta.

        Aquí van las tres transformaciones de exportación, en fila: el
        rango en orden, la subcarpeta del estado y la cámara del bin. Las
        tres viven en la exportación y no en la sesión, que guarda lo que el
        editor marcó.
        """
        camaras = self._camaras_por_clip()
        manifest = Manifest(
            proyecto=self.project_name,
            orientacion=self.orientacion_del_proyecto(),
            clips=[con_subcarpeta_de_estado(_con_el_rango_en_orden(
                replace(c, camara=camaras.get(i, SONY))))
                for i, c in enumerate(self.clips)],
        )
        manifest.write_json(destino)

    def _camaras_por_clip(self) -> dict[int, str]:
        """De índice de clip a cámara, de una sola pasada por los bins.

        Un clip sin bin no aparece aquí y sale con el respaldo: no hay de
        dónde sacarle una cámara, y llegar sin campo sería peor que llegar
        con la de la cámara que Bruno usa casi siempre.
        """
        return {i: self.bins.camara_de(nombre) or SONY
                for i, nombre in self.bins.mapa_por_clip().items()}
```

Agrega los imports que faltan arriba del archivo:

```python
from dataclasses import replace

from clasificador_video.camaras import SONY
```

- [ ] **Paso 4: pasarle las rutas al bin cuando se crea**

En el mismo archivo, en el bloque de importación (~línea 1889), cambia la
llamada a `agregar`:

```python
            else:
                # con las rutas: son lo único de lo que se puede adivinar la
                # cámara, y este es el instante en que el bin nace.
                self.bins.agregar(nombre_de_bin, origen, indices,
                                  rutas=[self.clips[i].ruta for i in indices])
```

- [ ] **Paso 5: correr las pruebas nuevas y la suite entera**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_camaras.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Se espera: todo verde.

- [ ] **Paso 6: commit**

```bash
git add -A
git commit -m "$(printf 'Adivinar la cámara al importar y mandarla al manifiesto\n\nEl bin nace con la cámara de sus archivos, y lo que Bruno corrija a mano\nle gana a lo adivinado -- que es lo único que hace que corregir sirva de\nalgo donde importa.\n\nDe paso, la parte de _on_export_manifest que escribe se separó de la que\npregunta: ahora se puede probar el manifiesto completo sin abrir un solo\ndiálogo, que es lo que colgaba la suite bajo offscreen antes de la F3.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Tarea 5: el menú para corregir la cámara

**Archivos:**
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (`_BinHeader`)
- Modificar: `src/clasificador_video/ui/main_window.py` (~línea 3126)
- Test: `tests/ui/test_clip_sheet_camaras.py` (nuevo)

- [ ] **Paso 1: escribir las pruebas que fallan**

Crea `tests/ui/test_clip_sheet_camaras.py`:

```python
"""El submenú «Cámara» del encabezado del bin."""
from clasificador_video.camaras import DJI, OTRA, SONY
from clasificador_video.ui.clip_sheet import _BinHeader


def _submenu_de_camara(cabecera):
    for accion in cabecera.construir_menu().actions():
        if accion.text().startswith("Cámara"):
            return accion.menu()
    return None


def test_el_menu_del_bin_ofrece_las_tres_camaras(qtbot):
    cabecera = _BinHeader("Dron")
    qtbot.addWidget(cabecera)

    sub = _submenu_de_camara(cabecera)

    assert [a.text() for a in sub.actions()] == ["Sony", "DJI", "Otra"]


def test_la_camara_puesta_sale_palomeada(qtbot):
    cabecera = _BinHeader("Dron")
    qtbot.addWidget(cabecera)
    cabecera.set_camara(DJI)

    sub = _submenu_de_camara(cabecera)

    palomeadas = [a.text() for a in sub.actions() if a.isChecked()]
    assert palomeadas == ["DJI"]


def test_escoger_una_camara_lo_avisa(qtbot):
    cabecera = _BinHeader("Dron")
    qtbot.addWidget(cabecera)
    avisos = []
    cabecera.camara_changed.connect(lambda n, c: avisos.append((n, c)))

    sub = _submenu_de_camara(cabecera)
    [a for a in sub.actions() if a.text() == "Otra"][0].trigger()

    assert avisos == [("Dron", OTRA)]


def test_la_seccion_de_sueltos_no_ofrece_camara(qtbot):
    """«Sin bin» no es una cámara: es la vista de los clips que no son de
    nadie. Mismo criterio que renombrar y enlazar proxies, que tampoco
    aparecen ahí."""
    cabecera = _BinHeader("Sin bin", es_bin=False)
    qtbot.addWidget(cabecera)

    assert _submenu_de_camara(cabecera) is None
```

- [ ] **Paso 2: correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet_camaras.py -q
```
Se espera: `AttributeError: '_BinHeader' object has no attribute
'set_camara'`.

Si el método que arma el menú **no se llama `construir_menu`**, mira su
nombre real en `clip_sheet.py` (está cerca de la línea 1200, es el que
devuelve el `QMenu` en vez de abrirlo) y corrige el helper del test.

- [ ] **Paso 3: escribir la implementación en `_BinHeader`**

En `src/clasificador_video/ui/clip_sheet.py`, agrega el import arriba:

```python
from clasificador_video.camaras import CAMARAS, SONY
```

Agrega la señal junto a las otras de `_BinHeader`:

```python
    camara_changed = Signal(str, str)     # nombre del bin, camara nueva
```

Agrega la tabla de nombres visibles, junto a `MARCAS`:

```python
    # Como se llama cada camara en el menu. En el mismo orden que `CAMARAS`.
    NOMBRE_DE_CAMARA = {"sony": "Sony", "dji": "DJI", "otra": "Otra"}
```

En `__init__`, antes de `self.set_posicion(0)`:

```python
        # La camara del bin. Arranca en el respaldo y la hoja la corrige con
        # `set_camara` en cuanto sabe cual es (via `_aplicar_meta`).
        self._camara = SONY
```

Agrega el método, junto a `set_posicion`:

```python
    def set_camara(self, camara: str) -> None:
        """Guarda la camara del bin. La pinta la tarea siguiente."""
        if camara not in CAMARAS:
            return
        self._camara = camara
```

Y en el método que arma el menú, **después del renglón «Renombrar bin…» y
antes de «Enlazar proxies…»**, mete el submenú:

```python
        # La camara vive junto a los proxies y el nombre porque las tres son
        # cosas de la CAMARA entera, no de un clip. Es submenu y no tres
        # renglones sueltos: son excluyentes entre si y hay que ver cual
        # esta puesta, que es justo lo que un submenu con palomita dice.
        camara_menu = QMenu("Cámara", menu)
        self._grupo_de_camara = QActionGroup(camara_menu)
        self._grupo_de_camara.setExclusive(True)
        for clave in CAMARAS:
            accion = QAction(self.NOMBRE_DE_CAMARA[clave], camara_menu)
            accion.setCheckable(True)
            accion.setChecked(clave == self._camara)
            # `clave=clave` y no la variable del bucle: sin eso las tres
            # lambdas comparten la ultima, y las tres pondrian «Otra».
            accion.triggered.connect(
                lambda _checked=False, clave=clave:
                self.camara_changed.emit(self.nombre, clave)
            )
            self._grupo_de_camara.addAction(accion)
            camara_menu.addAction(accion)
        menu.addMenu(camara_menu)
```

Agrega `QActionGroup` a los imports de Qt del archivo (viene de
`PySide6.QtGui`, junto a `QAction`).

El `QActionGroup` se guarda en `self` por lo mismo que `self._menu`: sin un
dueño en Python, se recolecta antes de que el menú se dibuje.

- [ ] **Paso 4: correr las pruebas nuevas**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet_camaras.py -q
```
Se espera: 4 passed.

- [ ] **Paso 5: conectar la señal en la ventana y llevarle la cámara a la hoja**

En `src/clasificador_video/ui/main_window.py`, junto a las otras conexiones
(~línea 3126):

```python
        cabecera.camara_changed.connect(self._on_camara_de_bin_cambiada)
```

Y el manejador, junto a `_on_bin_renombrado`:

```python
    def _on_camara_de_bin_cambiada(self, nombre: str, camara: str) -> None:
        """Bruno corrigió la cámara de un bin.

        No pasa por el historial a propósito: `⌘Z` revierte el dato de los
        clips --el cuarto, el estado, el rango--, y la cámara es una
        propiedad del bin, como su nombre. Renombrar un bin tampoco se
        deshace.
        """
        self.bins.fijar_camara(nombre, camara)
        self._refresh_sheet()
        self._autosave()
```

Y en el sitio donde la hoja arma la meta de cada bin —busca dónde se llama a
`set_bin_meta` o donde se llena `_bin_meta` con `origen` y `proxies`— agrega
la cámara al diccionario, y en `_aplicar_meta` (clip_sheet.py, ~línea 2206)
agrega la línea:

```python
        cabecera.set_camara(meta.get("camara", SONY))
```

- [ ] **Paso 6: correr la suite entera**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Se espera: todo verde.

- [ ] **Paso 7: commit**

```bash
git add -A
git commit -m "$(printf 'Poner la cámara de un bin desde su menú\n\nUn submenú «Cámara» con las tres opciones y palomita en la puesta, junto\na renombrar y a los proxies -- las tres son cosas de la cámara entera y\nno de un clip suelto.\n\nNo pasa por el historial: ⌘Z revierte el dato de los clips, y la cámara\nes propiedad del bin, como su nombre, que tampoco se deshace.\n\n«Sin bin» no lo ofrece, con el mismo criterio que ya se aplicaba a\nrenombrar y a los proxies: ahí no hay bin.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Tarea 6: la marquita se pinta con el color de la cámara

**Archivos:**
- Modificar: `src/clasificador_video/ui/theme.py`
- Modificar: `src/clasificador_video/ui/clip_sheet.py` (`set_posicion` →
  `set_camara`)
- Test: `tests/ui/test_clip_sheet_camaras.py`

- [ ] **Paso 1: escribir las pruebas que fallan**

Agrega a `tests/ui/test_clip_sheet_camaras.py`:

```python
from clasificador_video.ui import theme


def test_cada_camara_tiene_su_color():
    assert theme.camara_color(SONY) != theme.camara_color(DJI)
    assert theme.camara_color(DJI) != theme.camara_color(OTRA)


def test_una_camara_desconocida_no_truena():
    """El tema no puede reventar la hoja entera por un valor raro que se
    coló del autosave."""
    assert theme.camara_color("🐔") == theme.camara_color(SONY)


def test_dos_bins_de_la_misma_camara_se_ven_igual(qtbot):
    """Y está bien: en Premiere también van a salir del mismo color. Una
    app que muestra una diferencia que su destino no tiene, miente."""
    uno, otro = _BinHeader("Sony A"), _BinHeader("Sony B")
    qtbot.addWidget(uno)
    qtbot.addWidget(otro)

    uno.set_camara(SONY)
    otro.set_camara(SONY)

    assert uno.cam_mark.styleSheet() == otro.cam_mark.styleSheet()


def test_cambiarle_la_camara_le_cambia_el_color(qtbot):
    cabecera = _BinHeader("Dron")
    qtbot.addWidget(cabecera)

    cabecera.set_camara(SONY)
    con_sony = cabecera.cam_mark.styleSheet()
    cabecera.set_camara(DJI)

    assert cabecera.cam_mark.styleSheet() != con_sony


def test_la_seccion_de_sueltos_se_queda_neutra(qtbot):
    """«Sin bin» no es una cámara y no puede pintarse como una."""
    cabecera = _BinHeader("Sin bin", es_bin=False)
    qtbot.addWidget(cabecera)
    neutra = cabecera.cam_mark.styleSheet()

    cabecera.set_camara(DJI)

    assert cabecera.cam_mark.styleSheet() == neutra
```

- [ ] **Paso 2: correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet_camaras.py -q
```
Se espera: `AttributeError: module 'theme' has no attribute 'camara_color'`.

- [ ] **Paso 3: los colores en el tema**

En `src/clasificador_video/ui/theme.py`, junto a `BIN_PALETTE` (~línea 61):

```python
# El color de cada camara, y es EL MISMO que va a tener el clip en Premiere:
# Sony azul, dron amarillo, cualquier otra morado. Los eligio Bruno --azul y
# amarillo son los dos mas separados del panel de Premiere, y esa distancia
# es todo el punto.
#
# Reemplazan a `BIN_PALETTE` en la marquita del encabezado, que pintaba la
# POSICION del bin. Se acepta que dos tarjetas de la misma camara se vean
# iguales: en Premiere tambien van a salirlo, y una app que muestra una
# diferencia que su destino no tiene miente en chiquito.
CAMARA_COLORES = {
    "sony": "#3e9bc0",   # azul  → CERULEAN en Premiere
    "dji": "#c9a227",    # ámbar → MANGO en Premiere
    "otra": "#8b7ca8",   # morado → VIOLET en Premiere
}
```

Y junto a `bin_color` (~línea 201):

```python
def camara_color(camara: str) -> str:
    """El color de identidad de una camara. Ver `CAMARA_COLORES`.

    Una camara que no existe cae en la de siempre en vez de reventar: este
    valor puede venir de un autosave tocado a mano, y un tema que truena
    se lleva la hoja entera por delante.
    """
    return CAMARA_COLORES.get(camara, CAMARA_COLORES["sony"])
```

- [ ] **Paso 4: que la marquita use la cámara**

En `clip_sheet.py`, reemplaza el cuerpo de `set_camara` por lo que hacía
`set_posicion`, pero con el color de la cámara:

```python
    def set_camara(self, camara: str) -> None:
        """Tiñe la marca con el color de la camara del bin -- el mismo que
        va a tener el clip en Premiere.

        Antes teñia por POSICION del bin (`set_posicion`), y el comentario
        de entonces decia por que: «el mockup ponia ▲ al dron y ■ a la Sony
        porque sabia que era cada uno, y la app no lo sabe -- lee una
        carpeta, no un modelo de camara». Ahora si lo sabe.

        «Sin bin» se queda NEUTRA: no es una camara, es la vista de los
        clips que no son de nadie.
        """
        if camara not in CAMARAS:
            return
        self._camara = camara
        if not self.es_bin:
            self._pintar_neutra()
            return
        # `setStyleSheet` obliga a repolir el widget y es de lo mas caro que
        # hay en Qt: sin la guarda, cada reagrupada lo llamaria por bin.
        if getattr(self, "_camara_pintada", None) == camara:
            return
        self._camara_pintada = camara
        color = theme.camara_color(camara)
        # 18% de tinte detras de un glifo aclarado, como el mockup. A plena
        # tinta la marca competiria con la franja de cuarto de la miniatura,
        # que es otro dato.
        self.cam_mark.setStyleSheet(
            f"background-color: {theme.con_alfa_qss(color, theme.BIN_TINT_ALPHA)};"
            f" color: {theme.aclarar(color, theme.BIN_INK_LIGHTEN)};"
            f" border-radius: 3px; font-size: {theme.FONT_MICRO}px;"
        )

    def _pintar_neutra(self) -> None:
        self.cam_mark.setStyleSheet(
            f"background-color: {theme.BG_SURFACE_2};"
            f" color: {theme.TEXT_3};"
            f" border-radius: 3px; font-size: {theme.FONT_MICRO}px;"
        )
```

Borra `set_posicion` entero, y arregla sus dos usos:

- En `__init__`, cambia `self.set_posicion(0)` por:
  ```python
  self.set_camara(SONY) if self.es_bin else self._pintar_neutra()
  ```
- En `copiar_de`, cambia `self.set_posicion(otro._posicion)` por
  `self.set_camara(otro._camara)`.
- En la hoja (~línea 2622), borra la línea
  `cabecera.set_posicion(self._posicion_de_bin(nombre))` — la cámara ya
  llega por `_aplicar_meta`, que corre justo después.
- Si `_posicion_de_bin` se queda sin usos, **bórralo también**: código
  muerto en el mismo commit que lo dejó muerto (`CLAUDE.md`, higiene).

Comprueba que no queden usos:
```bash
grep -rn "set_posicion\|_posicion_de_bin\|bin_color\|BIN_PALETTE" src/ tests/
```
Lo que salga, arréglalo. Si `bin_color`/`BIN_PALETTE` se quedan sin usos,
bórralos de `theme.py`.

- [ ] **Paso 5: correr la suite entera**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Se espera: todo verde.

- [ ] **Paso 6: MIRAR la imagen — no es opcional**

`CLAUDE.md`: «nunca afirmar que algo se ve bien sin haber visto el pixel».

Escribe un script en el scratchpad de la sesión (**no en el repo**) que arme
una `ClipSheet` con tres bins —uno de Sony, uno del dron, uno «Otra»— más la
sección «Sin bin», haga `grab()`, guarde el PNG en el scratchpad, y **léelo
con la herramienta de lectura de archivos**.

Comprueba con los ojos: que los tres colores se distingan entre sí, que
«Sin bin» se vea apagada, y que la marquita no compita con las franjas de
cuarto de las miniaturas.

Si algo se ve mal, arréglalo antes de seguir.

- [ ] **Paso 7: commit**

```bash
git add -A
git commit -m "$(printf 'Pintar la marquita del bin con el color de su cámara\n\nEl puntito del encabezado decía la POSICIÓN del bin. Su propio comentario\nexplicaba por qué no decía la cámara: «el mockup ponía ▲ al dron y ■ a la\nSony porque sabía que era cada uno, y la app no lo sabe -- lee una\ncarpeta, no un modelo de cámara». Ahora sí lo sabe.\n\nEl color que se ve en la hoja es el mismo que va a tener el clip en\nPremiere. Cuesta que dos tarjetas de Sony se vean iguales, y se acepta:\nen Premiere también van a salirlo, y una app que muestra una diferencia\nque su destino no tiene miente en chiquito.\n\nSe fueron con esto set_posicion, _posicion_de_bin, bin_color y\nBIN_PALETTE, que se quedaron sin usos.\n\nVerificado a ojo sobre un grab() de la hoja con las tres cámaras.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

# FASE 3 — El plugin de Premiere

## Tarea 7: comprobar contra Premiere ANTES de escribir nada

**Esta tarea no escribe código de producción. Contesta dos preguntas que, si
se responden mal, tiran las dos tareas siguientes.**

En este plugin la documentación de Adobe ha mentido tres veces. Ver el
comentario al tope de `importClip.js` y
`docs/superpowers/archive/RESULTADO-2026-09-08-el-lut-por-la-via-del-blob.md`.

**Las dos preguntas, y las dos en UNA corrida** — cada corrida cuesta
reiniciar Premiere:

1. **¿Se puede renombrar un clip?** Si no, el `★` del destacado no existe y
   entra el plan B del spec §5.1.
2. **¿Existen `CERULEAN` y `VIOLET`** en
   `premierepro.Constants.ProjectItemColorLabel` de la versión de Bruno?
   `MANGO` ya está confirmado (índice 7, el 2026-08-10).

- [ ] **Paso 1: escribir el spike**

Crea `uxp-plugin/js/spike-nombre.js`, con `// SPIKE DESCARTABLE` en la
primera línea. Reglas que salieron caras y no se negocian:

- **Anota a disco DESPUÉS DE CADA PASO**, y **antes** de intentar lo
  peligroso. La sesión del LUT perdió una corrida entera por escribir el
  resultado al final: Premiere se cayó y no quedó ni una línea de por dónde
  iba.
- **No filtres por nombre.** Enumera con
  `Object.getOwnPropertyNames(Object.getPrototypeOf(obj))` y reporta lo que
  hay. Un filtro por un nombre que la API no expone descarta todo en
  silencio y el spike miente con cara de dato.
- **Trabaja sobre un proyecto de prueba desechable.** El spike del LUT dejó
  efectos colgados en un proyecto con trabajo adentro.

Lo que tiene que reportar:

```js
// 1. Que metodos tiene de verdad un ClipProjectItem, para ver si hay alguno
//    de renombrar (createSetNameAction, createRenameAction, o como se llame).
//    Se ENUMERA, no se adivina el nombre.
// 2. El intento de renombrar a "★ " + nombre, dentro de runTransaction, y si
//    el nombre cambio releyendo `item.name`.
// 3. Object.keys(premierepro.Constants.ProjectItemColorLabel) completo, con
//    el indice de cada uno.
```

- [ ] **Paso 2: instalarlo y pedirle a Bruno que lo corra**

Enciende `AUTOCHECK_ACTIVO` y agrega el botón para correrlo a mano — el
panel carga junto con Premiere, **antes** de que haya proyecto abierto, y
sin botón el arnés reporta «no hay proyecto» cuando sí lo hay.

```bash
cp uxp-plugin/index.html ~/Library/Application\ Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1.1.0/
cp uxp-plugin/js/*.js ~/Library/Application\ Support/Adobe/UXP/Plugins/External/com.iav.clasificadorvideo_1.1.0/js/
```

Bruno tiene que **cerrar Premiere entero** (no basta cerrar el panel), abrir
un proyecto de prueba con un par de clips, y darle al botón.

- [ ] **Paso 3: leer el resultado y decidir**

- Si **se puede renombrar**: sigue la Tarea 8 tal cual.
- Si **no se puede**: la Tarea 8 cambia al plan B —`Picks > Destacados`—
  y hay que **decírselo a Bruno**, no cambiarlo callado.
- Si falta `CERULEAN` o `VIOLET`: escoge el sustituto más parecido de la
  lista que reportó el spike, y anota el porqué en `label.js`.

- [ ] **Paso 4: borrar el spike y dejar el plugin como estaba**

```bash
rm uxp-plugin/js/spike-nombre.js
git checkout uxp-plugin/index.html uxp-plugin/js/autocheck.js
```

- [ ] **Paso 5: commit del resultado**

Escribe lo aprendido en
`docs/superpowers/archive/RESULTADO-2026-09-08-renombrar-y-colores.md`
—las dos respuestas, con la lista completa de colores que reportó— y
commitéalo. Un spike que reporta se borra; lo que aprendió, no.

---

## Tarea 8: el color por cámara en el plugin

**Archivos:**
- Modificar: `uxp-plugin/js/label.js`

- [ ] **Paso 1: reescribir la tabla y la función**

`label.js` deja de traducir estado→color y pasa a traducir cámara→color.
Reemplaza el archivo entero:

```js
// De que camara salio el clip, traducido a etiqueta de color de Premiere.
//
// ANTES ESTA ETIQUETA DECIA EL ESTADO (pick verde, reject rosa, destacado
// dorado). Cambio el 2026-09-08: en Premiere un item tiene UNA sola etiqueta
// de color, y Bruno la quiere para saber de un vistazo de que camara salio
// cada clip.
//
// El estado no se pierde: ya viaja en las subcarpetas Picks / Rejects / Sin
// marcar que arma `con_subcarpeta_de_estado` del lado de la app. El unico
// que se habria borrado es el DESTACADO --que iba en la misma carpeta que
// los picks y solo se distinguia por el dorado-- y por eso ahora llega con
// «★» al inicio del nombre; ver `nombre.js`.
//
// Los colores los eligio Bruno: azul y amarillo son los dos mas separados
// del panel, y esa distancia es todo el punto.
const LABEL_BY_CAMARA = {
  sony: "CERULEAN",
  dji: "MANGO",
  otra: "VIOLET",
};

// camara: "sony" | "dji" | "otra". Un valor que no este en la tabla no toca
// el clip -- puede venir de un manifiesto de otra version, y pintar
// «cualquier cosa» es peor que no pintar.
function applyCameraLabel(project, clipItem, camara) {
  const premierepro = require("premierepro");
  const labelName = LABEL_BY_CAMARA[camara];
  if (!labelName) return;

  const colores = premierepro.Constants.ProjectItemColorLabel;
  // Si la version de Premiere no conoce ese nombre, el valor sale undefined
  // y la accion pondria cualquier cosa. Mejor no tocar el clip y DECIRLO,
  // con la lista de los que si existen: es lo unico que permite corregir el
  // nombre sin adivinar. La guarda es de agosto y se queda tal cual.
  if (colores[labelName] === undefined) {
    logToPanel(
      "El color «" + labelName + "» no existe en esta version de Premiere. " +
      "Disponibles: " + Object.keys(colores).join(", "),
      true
    );
    return;
  }

  runTransaction(
    project,
    () => clipItem.createSetColorLabelAction(colores[labelName]),
    "Set label " + camara
  );
}
```

- [ ] **Paso 2: cambiar quien lo llama**

En `uxp-plugin/js/processManifest.js`, cambia la línea de `applyFlagLabel`:

```js
      applyCameraLabel(project, clipItem, clipData.camara);
```

- [ ] **Paso 3: comprobar que no quedan usos viejos**

```bash
grep -rn "applyFlagLabel\|LABEL_BY_FLAG" uxp-plugin/
```
Se espera: sin resultados.

- [ ] **Paso 4: commit**

```bash
git add uxp-plugin/js/label.js uxp-plugin/js/processManifest.js
git commit -m "$(printf 'Pintar los clips por cámara, no por estado\n\nEn Premiere un item tiene una sola etiqueta de color, y Bruno la quiere\npara saber de un vistazo de qué cámara salió cada clip: Sony azul, dron\namarillo, cualquier otra morado.\n\nEl estado no se pierde -- ya viajaba en las subcarpetas Picks / Rejects /\nSin marcar. El único que se habría borrado es el destacado, que iba en la\nmisma carpeta que los picks y solo se distinguía por el dorado; ese llega\nahora con ★ en el nombre.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Tarea 9: el ★ del destacado

**Solo si la Tarea 7 confirmó que se puede renombrar.** Si no, salta al plan
B del spec §5.1 y dilo.

**Archivos:**
- Crear: `uxp-plugin/js/nombre.js`
- Modificar: `uxp-plugin/js/processManifest.js`, `uxp-plugin/index.html`

- [ ] **Paso 1: escribir el módulo**

Crea `uxp-plugin/js/nombre.js`. **Ajusta el nombre del método de renombrar
al que reportó el spike de la Tarea 7** — no lo des por hecho:

```js
// El «★» de los destacados, sobre el nombre del item en el panel de
// proyecto. NO toca el archivo en disco.
//
// Existe porque la etiqueta de color paso a decir la camara (`label.js`), y
// el destacado era el unico estado que solo se distinguia por color: va en
// la misma carpeta «Picks» que los demas picks --decision del 2026-08-22, un
// destacado ES un pick reforzado-- asi que sin marca propia se perderia en
// la frontera. Que la estrella se pierda al cruzar a Premiere es justo lo
// que este plugin existe para evitar.
const PREFIJO_DESTACADO = "★ ";

// flag: "pick" | "reject" | "destacado" | "none".
//
// DOS REGLAS, y las dos son sobre no hacer daño:
//
// 1. Es IDEMPOTENTE. Volver a correr la misma clasificacion es un caso
//    normal --es como se corrige un error-- y sin esta guarda quedaria
//    «★ ★ ★ C0001.MP4».
// 2. Solo AGREGA, nunca quita. Si un clip dejo de ser destacado, su ★ se
//    queda. Quitarlo significaria que el plugin renombra clips que Bruno
//    pudo haber renombrado a mano, y ese daño es peor que un ★ de mas.
//    Mismo criterio que `applyFlagLabel` tenia con flag "none".
function applyStarPrefix(project, clipItem, flag) {
  if (flag !== "destacado") return;

  const nombre = clipItem.name;
  if (typeof nombre !== "string" || nombre.indexOf(PREFIJO_DESTACADO) === 0) return;

  runTransaction(
    project,
    () => clipItem.createSetNameAction(PREFIJO_DESTACADO + nombre),
    "Marcar destacado"
  );
}
```

- [ ] **Paso 2: llamarlo y cargarlo**

En `processManifest.js`, después de `applyCameraLabel`:

```js
      applyStarPrefix(project, clipItem, clipData.flag);
```

En `index.html`, junto a los otros scripts, **antes** de
`processManifest.js` (que es quien lo usa):

```html
<script src="js/nombre.js"></script>
```

- [ ] **Paso 3: comprobarlo en Premiere de verdad**

No hay forma de probar esto sin Premiere. Instala, pide a Bruno que cierre
Premiere entero, abra un proyecto de prueba e importe un manifiesto con un
clip destacado.

Comprueba **dos** cosas, y la segunda es la que importa:
1. El clip aparece como `★ C0001.MP4` en el panel de proyecto.
2. **Importar el MISMO manifiesto otra vez lo deja igual**, no como
   `★ ★ C0001.MP4`.

- [ ] **Paso 4: commit**

```bash
git add uxp-plugin/js/nombre.js uxp-plugin/js/processManifest.js uxp-plugin/index.html
git commit -m "$(printf 'Marcar los destacados con ★ en el nombre\n\nLa etiqueta de color pasó a decir la cámara, y el destacado era el único\nestado que solo se distinguía por color: va en la misma carpeta «Picks»\nque los demás picks, así que sin marca propia se perdía al cruzar a\nPremiere -- justo lo que este plugin existe para evitar.\n\nSolo agrega y nunca quita, y es idempotente: volver a importar el mismo\nmanifiesto no deja «★ ★ ★». Quitar el ★ significaría renombrar clips que\nBruno pudo haber renombrado a mano, y ese daño es peor que un ★ de más.\n\nComprobado en Premiere real, incluida la segunda pasada.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Tarea 10: las siete carpetas

**Archivos:**
- Crear: `uxp-plugin/js/estructura.js`
- Modificar: `uxp-plugin/js/processManifest.js`, `uxp-plugin/index.html`

- [ ] **Paso 1: escribir el módulo**

Crea `uxp-plugin/js/estructura.js`:

```js
// El esqueleto del proyecto de Premiere de Bruno. Un solo lugar donde esta
// escrito como se llama cada carpeta y cual es cual.
//
// Vive aqui y no del lado de la app a proposito: la estructura del proyecto
// de Premiere es cosa de Premiere. Si la app la escribiera en el
// `categoria_path`, el nombre de estas carpetas quedaria repartido en dos
// repos y se desincronizarian en el primer cambio de opinion -- mismo
// criterio por el que `con_subcarpeta_de_estado` no vive en la sesion.
//
// Los nombres van tal cual los escribio Bruno, con su numero y su punto:
// Premiere ordena por abecedario, asi que el numero es lo que sostiene el
// orden.
const CARPETAS_DEL_PROYECTO = [
  "01. Secuencia",
  "02. Clip",
  "03. AE composition",
  "04. Musica",
  "05. Voz",
  "06. Graficos",
  "07. Assets adicionales",
];

// Donde cuelga TODO el material clasificado. Es la segunda de la lista y no
// una cadena suelta: si alguien renombra la carpeta alla arriba, esto sigue
// apuntando a la misma.
const CARPETA_DE_CLIPS = CARPETAS_DEL_PROYECTO[1];

// Crea las siete al empezar, aunque cinco se queden vacias: son el esqueleto
// del proyecto y existen para que Bruno meta cosas ahi, no para que la app
// las llene.
//
// `resolveBinChain` REUSA lo que ya existe, asi que un proyecto que ya tenga
// su «04. Musica» con musica adentro no recibe una segunda.
async function crearEsqueleto(project, rootFolder) {
  for (const nombre of CARPETAS_DEL_PROYECTO) {
    await resolveBinChain(project, rootFolder, [nombre]);
  }
}

// El camino completo de un clip: su cuarto y su estado, colgados de
// «02. Clip». La app manda ["Cocina", "Picks"] y aqui se vuelve
// ["02. Clip", "Cocina", "Picks"].
function caminoDelClip(categoryPath) {
  return [CARPETA_DE_CLIPS].concat(categoryPath);
}
```

- [ ] **Paso 2: usarlo en `processManifest.js`**

Al principio de `processManifest`, después de sacar `rootFolder`:

```js
  await crearEsqueleto(project, rootFolder);
```

Y donde hoy resuelve el bin destino:

```js
      const targetFolder = await resolveBinChain(
        project, rootFolder, caminoDelClip(categoryPath));
```

**Ojo con el mensaje de error**: hoy dice a dónde iba el clip con
`categoryPath.join(" > ")`. Cámbialo para que use el camino completo, o el
mensaje va a mentir sobre dónde buscar:

```js
      const donde = caminoDelClip(categoryPath).join(" > ");
```

Y en `index.html`, antes de `processManifest.js`:

```html
<script src="js/estructura.js"></script>
```

- [ ] **Paso 3: avisar de los clips que se van a mover**

Un proyecto ya importado tiene clips fuera de `02. Clip`, y **se van a
mover**. Se avisa antes de tocar nada, no después.

En `processManifest.js`, justo después de `crearEsqueleto`:

```js
  // Un proyecto de una importacion anterior tiene sus clips fuera de
  // «02. Clip». No se duplican --`importOrReuseClip` los encuentra por ruta
  // en disco-- pero SI se mueven, y eso hay que decirlo antes de hacerlo:
  // que las cosas cambien de lugar solas es exactamente el modo de falla
  // que esta app existe para no tener.
  const carpetaDeClips = await resolveBinChain(project, rootFolder, [CARPETA_DE_CLIPS]);
  let porMover = 0;
  for (const clipData of manifest.clips) {
    const hallado = await findClipByPath(rootFolder, clipData.ruta);
    if (hallado && !(await estaDentroDe(hallado.parentFolder, carpetaDeClips))) porMover++;
  }
  if (porMover > 0) {
    logToPanel(
      porMover + " clip(s) que ya estaban en el proyecto se van a mover a «" +
      CARPETA_DE_CLIPS + "». No se duplica ninguno."
    );
  }
```

Y en `estructura.js`, el ayudante:

```js
// ¿Esta carpeta es la de destino, o cuelga de ella? Por REFERENCIA, no por
// nombre: hay bins homonimos en ramas distintas, y esa es la misma razon por
// la que `importOrReuseClip` compara carpetas con `===`.
async function estaDentroDe(carpeta, ancestro) {
  const premierepro = require("premierepro");
  if (carpeta === ancestro) return true;
  for (const item of (await ancestro.getItems()) || []) {
    if (!item) continue;
    const sub = premierepro.FolderItem.cast(item);
    if (sub && (await estaDentroDe(carpeta, sub))) return true;
  }
  return false;
}
```

- [ ] **Paso 4: comprobarlo en Premiere de verdad**

Instala y pide a Bruno una corrida con un manifiesto real. Comprueba **tres**
cosas:

1. Las siete carpetas aparecen, y los clips están bajo
   `02. Clip > <cuarto> > Picks|Rejects|Sin marcar`.
2. **Importar el mismo manifiesto otra vez NO crea `02. Clip 2`** ni duplica
   ninguna carpeta.
3. En un proyecto que ya tenía clips importados de antes, el panel avisa
   cuántos se van a mover, y después de importar están en su lugar nuevo sin
   duplicarse.

- [ ] **Paso 5: commit**

```bash
git add uxp-plugin/js/estructura.js uxp-plugin/js/processManifest.js uxp-plugin/index.html
git commit -m "$(printf 'Armar el proyecto de Premiere con las siete carpetas de Bruno\n\n01. Secuencia, 02. Clip, 03. AE composition, 04. Musica, 05. Voz,\n06. Graficos y 07. Assets adicionales. Las siete se crean siempre, aunque\ncinco queden vacías: son el esqueleto del proyecto y existen para que él\nmeta cosas ahí. Si ya existen, se reusan.\n\nTodo el material clasificado cuelga de «02. Clip», con los cuartos y sus\nPicks/Rejects/Sin marcar adentro como hasta ahora.\n\nLos nombres viven en el plugin y no en el manifiesto: la estructura del\nproyecto de Premiere es cosa de Premiere, y repartida en dos repos se\ndesincroniza en el primer cambio de opinión.\n\nUn proyecto ya importado avisa cuántos clips se van a mover antes de\ntocarlos. Que las cosas cambien de lugar solas es el modo de falla que\nesta app existe para no tener.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Tarea 11: dejar la documentación diciendo lo que hace la app

**Archivos:**
- Modificar: `README.md`, `docs/superpowers/CONTEXTO-Y-METAS.md`, `CLAUDE.md`

- [ ] **Paso 1: buscar lo que quedó mintiendo**

```bash
grep -rn "verde\|rosa\|dorad\|FOREST\|ROSE\|MANGO\|etiqueta" README.md docs/ CLAUDE.md
```

- [ ] **Paso 2: corregirlo**

Lo que cambió y hay que decir bien:
- El color en Premiere dice la **cámara**, no el estado.
- El destacado llega con **★ en el nombre** (o con su carpeta, si la Tarea 7
  mandó al plan B).
- La estructura de **siete carpetas**, con el material bajo `02. Clip`.
- En `CLAUDE.md`, en «Decisiones de arquitectura ya tomadas», agrega el
  renglón del color por cámara con su razón y su costo aceptado (dos
  tarjetas de la misma cámara se ven iguales), y actualiza el renglón del
  LUT apuntando al resultado del 2026-09-08.

- [ ] **Paso 3: commit**

```bash
git add -A
git commit -m "$(printf 'Poner al día la documentación que quedó diciendo lo viejo\n\nEl color en Premiere ya no dice el estado sino la cámara, los destacados\nllegan con ★ en el nombre y el proyecto se arma con siete carpetas. La\ndocumentación decía lo de antes.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Cierre

- [ ] **La suite completa, verde**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

- [ ] **`git status` limpio y sin archivos sueltos**

```bash
git status --short
```
Nada de spikes olvidados, nada en la raíz del repo, `AUTOCHECK_ACTIVO` en
`false` y sin `spike-*.js` en `uxp-plugin/js/`.

- [ ] **Una corrida de verdad, de punta a punta**

Bruno clasifica material de las dos cámaras, exporta y lo importa a un
proyecto nuevo de Premiere. Se comprueba a ojo: los clips del dron amarillos,
los de la Sony azules, los destacados con ★, y las siete carpetas en su
lugar.

Esto no es opcional ni ceremonia. El 2026-08-22 el uso real con 205 clips
sacó **ocho bugs que 1500 pruebas no vieron**, y todos eran lo mismo: dos
partes del programa diciendo cosas distintas del mismo dato.
