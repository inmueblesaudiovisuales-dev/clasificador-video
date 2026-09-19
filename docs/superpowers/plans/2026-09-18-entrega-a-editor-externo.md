# Entrega a un editor externo — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir, de punta a punta, la entrega de un proyecto a un editor externo vía Google Drive: proxy de tamaño real, reconocimiento de carpeta de proxies por número, marcas de cámara combinadas en Premiere, y los botones/diálogos/indicadores de Clipify para subir, traer de vuelta y ver el estado de varios proyectos a la vez.

**Architecture:** Cambios de bajo riesgo primero (proxy, carpeta, marcas — todos aislados y sin dependencias externas), después el módulo `drive.py` sin UI (probado con un cliente de Drive inyectado/mockeado), y al final la interfaz que lo conecta todo: barra superior, dos diálogos y la pantalla de inicio.

**Tech Stack:** Python 3.10+, PySide6, ffmpeg (ya integrado), `google-api-python-client` + `google-auth-oauthlib` (nuevas), Node puro para las pruebas del plugin UXP.

**Specs de origen:**
- `docs/superpowers/specs/2026-09-18-entrega-a-editor-externo-design.md`
- `docs/superpowers/specs/2026-09-18-entrega-a-editor-externo-ui-design.md`

---

## F1 — El proxy sale a tamaño real, no a 720p

**Files:**
- Modify: `src/clasificador_video/proxy_gen.py:24-27,208-244`
- Test: `tests/test_proxy_gen.py:42-49`

- [ ] **Step 1: Reescribir el test que hoy exige el escalado a 720p**

Reemplaza `test_el_comando_escala_por_el_lado_corto` por lo contrario: que el comando YA NO traiga ningún filtro de escala.

```python
def test_el_comando_ya_no_escala___sale_al_tamano_real_del_original():
    """El proxy deja de achicar el cuadro (spec 2026-09-18 §2): un clip de
    4K da un proxy de 4K. Se abandonó 720p porque un editor externo que
    reencuadra sobre un proxy de OTRO tamaño calcula el ajuste mal, y al
    reconectar contra el original la imagen sale chica y cortada --
    comprobado con capturas reales, no en teoría."""
    args = proxy_gen.comando(Path("a.MP4"), Path("b.mp4"), ffmpeg="ffmpeg")

    assert "-vf" not in args
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py::test_el_comando_ya_no_escala___sale_al_tamano_real_del_original -v`
Expected: FAIL (`assert "-vf" not in args` es falso porque `-vf` sigue en la lista)

- [ ] **Step 3: Quitar `LADO_CORTO` y el filtro de escala de `comando()`**

En `proxy_gen.py`, borra la constante `LADO_CORTO` (líneas 24-27) y, dentro de `comando()`, borra la variable `escala` y las dos entradas `"-vf", escala,` de la lista devuelta. El resto del comando (`-map`, `-c:v h264_videotoolbox`, `-b:v 6M`, `-c:a aac -b:a 128k`, `-f mp4`) no cambia.

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
        "-y",
        "-i", str(original),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-c:v", "h264_videotoolbox",
        "-b:v", "6M",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "mp4",
        str(destino),
    ]
```

- [ ] **Step 4: Correr los tests de `proxy_gen` completos**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py -v`
Expected: PASS todos (el nuevo, y los que ya existían: mapeo de video, mapeo de audio, sufijo, `faltantes`)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proxy_gen.py tests/test_proxy_gen.py
git commit -m "$(cat <<'EOF'
El proxy sale a tamaño real, no a 720p

Un editor externo que reencuadra sobre un proxy de otro tamaño calcula
el ajuste sobre las dimensiones equivocadas y, al reconectar contra el
original en 4K, la imagen sale chica y cortada. El peso lo decide el
bitrate, no la resolución -- medido, pesa igual que el de 720p.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## F2 — La carpeta de proxies se reconoce por número, no por nombre idéntico

**Files:**
- Modify: `src/clasificador_video/proxy_gen.py` (nueva función + uso en `carpeta_para_escribir` y `carpetas_de_proxies`)
- Test: `tests/test_proxy_gen.py`

- [ ] **Step 1: Escribir el test de la nueva función `subcarpeta_por_numero`**

```python
def test_subcarpeta_por_numero_encuentra_una_con_nombre_distinto(tmp_path):
    """Bruno ya tiene, hecha a mano, `02. PROXY DRONE` como hermana de
    `02. VIDEO DRONE` -- mismo número, nombre distinto a propósito. La
    regla de agosto (nombre IDÉNTICO) la ignoraba y creaba una carpeta
    nueva vacía al lado. Regla nueva: el número manda."""
    elegida = tmp_path / "Proxies del proyecto"
    elegida.mkdir()
    (elegida / "02. PROXY DRONE").mkdir()
    material = tmp_path / "material" / "02. VIDEO DRONE"
    material.mkdir(parents=True)

    destino = proxy_gen.subcarpeta_por_numero(elegida, material)

    assert destino == elegida / "02. PROXY DRONE"


def test_subcarpeta_por_numero_sin_coincidencia_usa_el_nombre_de_siempre(tmp_path):
    elegida = tmp_path / "Proxies del proyecto"
    elegida.mkdir()
    material = tmp_path / "material" / "02. VIDEO DRONE"
    material.mkdir(parents=True)

    destino = proxy_gen.subcarpeta_por_numero(elegida, material)

    assert destino == elegida / "02. VIDEO DRONE"


def test_subcarpeta_por_numero_sin_numero_en_el_material_usa_el_nombre(tmp_path):
    """Una carpeta de material sin prefijo numérico (`DRONE`, sin `02. `)
    no tiene número que comparar: se cae al comportamiento de siempre."""
    elegida = tmp_path / "Proxies del proyecto"
    elegida.mkdir()
    (elegida / "DRONE viejo").mkdir()
    material = tmp_path / "material" / "DRONE"
    material.mkdir(parents=True)

    destino = proxy_gen.subcarpeta_por_numero(elegida, material)

    assert destino == elegida / "DRONE"
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py -k subcarpeta_por_numero -v`
Expected: FAIL con `AttributeError: module 'clasificador_video.proxy_gen' has no attribute 'subcarpeta_por_numero'`

- [ ] **Step 3: Implementar `subcarpeta_por_numero`**

Agrega, junto a `subcarpeta_del_bin` en `proxy_gen.py`:

```python
import re

_NUMERO = re.compile(r"^(\d+)\.\s")


def _numero_de(nombre: str) -> str | None:
    """El prefijo `NN.` de un nombre de carpeta, o `None` si no lo trae."""
    m = _NUMERO.match(nombre)
    return m.group(1) if m else None


def subcarpeta_por_numero(elegida: Path, carpeta_del_bin: Path) -> Path:
    """Como `subcarpeta_del_bin`, pero reconoce una carpeta YA HECHA por
    Bruno aunque el nombre no sea idéntico -- basta que el número
    coincida (spec 2026-09-18 §3).

    Bruno trae de fábrica `02. PROXY DRONE` como hermana de
    `02. VIDEO DRONE`: mismo número, nombre distinto a propósito. La
    regla de agosto --nombre IDÉNTICO-- la ignoraba y creaba
    `02. VIDEO DRONE` DENTRO de la carpeta de proxies, dejando la suya
    vacía. Aquí el número manda: si hay alguna subcarpeta de `elegida`
    cuyo número coincide, se usa esa. Sin número que comparar, o sin
    coincidencia, se cae al nombre de siempre (comportamiento de agosto,
    sin cambio).
    """
    numero = _numero_de(carpeta_del_bin.name)
    if numero is not None:
        try:
            for hija in elegida.iterdir():
                if hija.is_dir() and _numero_de(hija.name) == numero:
                    return hija
        except OSError:
            pass  # la carpeta elegida puede no existir todavía
    return elegida / carpeta_del_bin.name
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py -k subcarpeta_por_numero -v`
Expected: PASS los 3

- [ ] **Step 5: Usar `subcarpeta_por_numero` en vez de `subcarpeta_del_bin`**

En `proxy_gen.py`, dentro de `carpetas_de_proxies` y `carpeta_para_escribir`, cambia las dos llamadas a `subcarpeta_del_bin(elegida, carpeta_del_bin)` por `subcarpeta_por_numero(elegida, carpeta_del_bin)`. Deja `subcarpeta_del_bin` tal cual (la sigue llamando `carpeta_por_defecto`... revisa: si ya no la usa nadie más que este archivo, bórrala; `grep -rn "subcarpeta_del_bin" src/` para confirmarlo antes de borrar).

- [ ] **Step 6: Correr toda la suite de `proxy_gen` y de `main_window` que toca proxies**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py tests/ui/test_main_window_carpeta_de_proxies.py -v`
Expected: PASS todos — ningún test viejo debía asumir el nombre idéntico como ÚNICA forma de calzar, así que nada debería romperse.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/proxy_gen.py tests/test_proxy_gen.py
git commit -m "$(cat <<'EOF'
Reconocer la carpeta de proxies por número, no por nombre idéntico

Bruno ya tiene, hecha a mano, "02. PROXY DRONE" como hermana de
"02. VIDEO DRONE" -- mismo número, nombre distinto a propósito. La
regla de agosto (nombre idéntico) la ignoraba y dejaba esa carpeta
vacía mientras creaba una nueva por dentro.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## F3 — Marcas de cámara combinadas: `[SONY]` / `[POCKET]` / `[DRONE]`

### F3.a — Lado Python: detectar la cámara del bin y llevarla al manifest

**Files:**
- Create: `src/clasificador_video/marca_camara.py` (reemplaza a `marca_dron.py`)
- Delete: `src/clasificador_video/marca_dron.py`
- Modify: `src/clasificador_video/manifest.py:9-41`
- Modify: `src/clasificador_video/ui/main_window.py:37,4930-4960`
- Create: `tests/test_marca_camara.py` (reemplaza a `tests/test_marca_dron.py`)
- Delete: `tests/test_marca_dron.py`

- [ ] **Step 1: Ver qué prueba hoy `test_marca_dron.py`, para no perder ningún caso**

Run: `cat tests/test_marca_dron.py`

(Vas a reescribir cada uno de esos casos dentro de `test_marca_camara.py`, con `bin_dice_dron` en vez de perder cobertura.)

- [ ] **Step 2: Escribir `tests/test_marca_camara.py`**

```python
# tests/test_marca_camara.py
from clasificador_video.marca_camara import bin_dice_dron, bin_dice_pocket, bin_dice_sony


def test_bin_dice_dron_por_dron_o_drone():
    assert bin_dice_dron("Dron 12 sept")
    assert bin_dice_dron("Drone footage")
    assert not bin_dice_dron("Sony tarde")


def test_bin_dice_sony():
    assert bin_dice_sony("Sony mañana")
    assert bin_dice_sony("SONY_FX30")
    assert not bin_dice_sony("Pocket 3")


def test_bin_dice_pocket():
    """"pocket" cubre "Osmo Pocket" completo sin tener que buscar "osmo"."""
    assert bin_dice_pocket("Osmo Pocket tarde")
    assert bin_dice_pocket("POCKET")
    assert not bin_dice_pocket("Osmo Action")


def test_ningun_bin_vacio_o_none_dice_ninguna_camara():
    assert not bin_dice_dron("")
    assert not bin_dice_sony(None)
    assert not bin_dice_pocket(None)
```

(Agrega aquí también los casos que traía `test_marca_dron.py` para `sinMarcaDron`/`cuartoEsDeDron` si existían del lado Python — si esas dos vivían solo en JS, no hace falta duplicarlas aquí.)

- [ ] **Step 3: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_marca_camara.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'clasificador_video.marca_camara'`

- [ ] **Step 4: Crear `marca_camara.py` con las tres funciones**

```python
"""Si el nombre de un bin de importación dice de qué cámara es.

Vive aparte de `camaras.py` a propósito: ese módulo mira el nombre de los
ARCHIVOS y decide el COLOR del clip en Premiere. Este mira el nombre del
BIN DE IMPORTACIÓN -- la tanda con la que Bruno arrastró el material, la
misma que se ve como encabezado en la hoja -- y solo sirve para decidir
las marcas `[SONY]` / `[POCKET]` / `[DRONE]` en la carpeta del cuarto en
Premiere. Son dos señales distintas y no se mezclan.

Nació como `marca_dron.py` (spec 2026-09-18, la de la marca [DRONE]) y se
generalizó a las tres cámaras el mismo día, con la spec de entrega a un
editor externo, §4.
"""
from __future__ import annotations


def _bin_dice(nombre: str, palabra: str) -> bool:
    return palabra in (nombre or "").lower()


def bin_dice_dron(nombre: str) -> bool:
    """`dron` es substring de `drone` («**dron**e»), así que una sola
    comparación cubre las dos formas de escribirlo."""
    return _bin_dice(nombre, "dron")


def bin_dice_sony(nombre: str) -> bool:
    return _bin_dice(nombre, "sony")


def bin_dice_pocket(nombre: str) -> bool:
    """`pocket` cubre "Osmo Pocket" completo sin tener que reconocer
    "osmo" -- que Bruno también usa para el Action, que NO entra en este
    sistema (spec 2026-09-18 §4)."""
    return _bin_dice(nombre, "pocket")
```

- [ ] **Step 5: Borrar `marca_dron.py` y `test_marca_dron.py`**

```bash
git rm src/clasificador_video/marca_dron.py tests/test_marca_dron.py
```

- [ ] **Step 6: Correr los tests y confirmar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_marca_camara.py -v`
Expected: PASS los 4

- [ ] **Step 7: Agregar `bin_sony` y `bin_pocket` al `Clip` del manifest**

En `src/clasificador_video/manifest.py`, junto a `bin_dron: bool = False`:

```python
    # Igual que `bin_dron`, pero para las otras dos cámaras que el sistema
    # de marcas reconoce. Ver `marca_camara.py`.
    bin_sony: bool = False
    bin_pocket: bool = False
```

Y en `to_dict()`, junto a `"bin_dron": self.bin_dron,`:

```python
            "bin_sony": self.bin_sony,
            "bin_pocket": self.bin_pocket,
```

- [ ] **Step 8: Test de `manifest.py` para los campos nuevos**

Busca el test existente que cubre `bin_dron` en `to_dict` (`grep -n bin_dron tests/test_manifest.py`) y agrega uno gemelo:

```python
def test_to_dict_incluye_bin_sony_y_bin_pocket():
    clip = Clip(orden=0, ruta=Path("a.mp4"), categoria_path=["Cocina"],
                fps=25.0, bin_sony=True, bin_pocket=False)

    d = clip.to_dict()

    assert d["bin_sony"] is True
    assert d["bin_pocket"] is False
```

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -v`
Expected: PASS

- [ ] **Step 9: Llenar los campos nuevos al exportar, en `main_window.py`**

Cambia el import de la línea 37:

```python
from clasificador_video.marca_camara import bin_dice_dron, bin_dice_pocket, bin_dice_sony
```

Junto a `_bin_dron_por_clip` (línea ~4950), agrega dos gemelas:

```python
    def _bin_sony_por_clip(self) -> dict[int, bool]:
        return {i: bin_dice_sony(nombre)
                for i, nombre in self.bins.mapa_por_clip().items()}

    def _bin_pocket_por_clip(self) -> dict[int, bool]:
        return {i: bin_dice_pocket(nombre)
                for i, nombre in self.bins.mapa_por_clip().items()}
```

Y en la construcción del `Manifest` (línea ~4930-4936), donde dice:

```python
            clips=[_con_el_rango_en_orden(
                replace(c, camara=camaras.get(i, SONY), bin_dron=dron.get(i, False)))
                for i, c in enumerate(self.clips)],
```

agrega las dos banderas nuevas a la misma llamada. Vas a necesitar los diccionarios `sony` y `pocket` calculados antes de la construcción del manifest, igual que `dron = self._bin_dron_por_clip()`:

```python
        dron = self._bin_dron_por_clip()
        sony = self._bin_sony_por_clip()
        pocket = self._bin_pocket_por_clip()
        manifest = Manifest(
            proyecto=self.project_name,
            orientacion=self.orientacion_del_proyecto(),
            clips=[_con_el_rango_en_orden(
                replace(c, camara=camaras.get(i, SONY),
                        bin_dron=dron.get(i, False),
                        bin_sony=sony.get(i, False),
                        bin_pocket=pocket.get(i, False)))
                for i, c in enumerate(self.clips)],
            guia=self._guia_para_el_manifest(),
            crear_secuencias=True,
        )
```

(Revisa las líneas exactas con `grep -n "_bin_dron_por_clip\|dron = self" src/clasificador_video/ui/main_window.py` antes de editar: el número de línea puede haberse movido.)

- [ ] **Step 10: Correr toda la suite de `main_window` relacionada con el manifest**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/ -k manifest -v`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
Generalizar la marca [DRONE] a [SONY] / [POCKET] / [DRONE]

marca_dron.py pasa a marca_camara.py con una función por cámara. El
manifest ahora lleva bin_sony y bin_pocket junto a bin_dron, llenados
igual: por el nombre del bin de importación, no del archivo.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### F3.b — Lado UXP: la marca combinada en el nombre de la carpeta

**Files:**
- Create: `uxp-plugin/js/marcaCamara.js` (reemplaza a `marcaDron.js`)
- Delete: `uxp-plugin/js/marcaDron.js`
- Create: `uxp-plugin/pruebas/marcaCamara.pruebas.js` (reemplaza a `marcaDron.pruebas.js`)
- Delete: `uxp-plugin/pruebas/marcaDron.pruebas.js`
- Modify: `uxp-plugin/index.html:169`
- Modify: `uxp-plugin/pruebas/correr.js:36-40,58-64`
- Modify: `uxp-plugin/js/processManifest.js` (ningún cambio de lógica -- ya llama `nombreDelCuartoConMarca`, que sigue existiendo con el mismo nombre)

- [ ] **Step 1: Leer los casos que ya prueba `marcaDron.pruebas.js`**

Run: `cat uxp-plugin/pruebas/marcaDron.pruebas.js`

Vas a reescribirlos todos dentro de `marcaCamara.pruebas.js`, más los casos nuevos de combinación.

- [ ] **Step 2: Escribir `uxp-plugin/js/marcaCamara.js`**

Mismo contrato que `marcaDron.js` (mismas tres funciones exportadas por nombre: `sinMarcaDron` se generaliza a `sinMarcaDeCamara`, y `nombreDelCuartoConMarca` mantiene su nombre porque `processManifest.js` ya lo llama así), con la regla de combinación del spec §4: orden fijo Sony, Pocket, Drone; un clip que no dice ninguna de las tres palabras no cuenta ni suma ni resta.

```javascript
// Las marcas de cámara -- "[SONY] ", "[POCKET] ", "[DRONE] "-- en el
// nombre de la carpeta de un cuarto en Premiere.
//
// POR QUE ES UNA SEÑAL APARTE DE LA CAMARA (`label.js`): el color del
// clip ya dice de que camara salio, mirando el nombre del ARCHIVO. Esto
// mira el nombre del BIN DE IMPORTACION -- la tanda con la que Bruno
// arrastro el material -- y solo sirve para esta marca. Las dos conviven
// sin tocarse.
//
// Nacio como marcaDron.js (spec 2026-09-18, marca [DRONE] sola, regla
// todo-o-nada) y se generalizo el mismo dia a tres camaras, con la spec
// de entrega a un editor externo §4: a diferencia de [DRONE] sola --que
// se apaga ante cualquier mezcla-- un cuarto con mas de una camara se
// marca con las dos, COMBINADAS, en el orden fijo Sony/Pocket/Drone.
//
// Logica pura: se prueba con `node uxp-plugin/pruebas/correr.js`.

const _MARCAS = [
  { palabra: "SONY", campo: "bin_sony" },
  { palabra: "POCKET", campo: "bin_pocket" },
  { palabra: "DRONE", campo: "bin_dron" },
];

// Quita SOLO una marca de camara conocida y solo si esta al inicio. Un
// nombre que Bruno haya escrito el mismo no es nuestro y no se toca.
function sinMarcaDeCamara(nombre) {
  const s = String(nombre || "");
  for (const { palabra } of _MARCAS) {
    const prefijo = "[" + palabra + "] ";
    if (s.indexOf(prefijo) === 0) return s.slice(prefijo.length);
  }
  return s;
}

// Si TODOS los clips de ese cuarto vinieron de un bin que dice esta
// camara (campo del manifiesto, ej. "bin_sony"). Un clip que no diga
// ninguna de las tres camaras (Osmo Action) simplemente no cuenta para
// esta pregunta -- no apaga la marca de las que si se reconocen.
function _cuartoEsDeCamara(clipsDelManifest, nombreDeCuarto, campo) {
  const delCuarto = (clipsDelManifest || []).filter(
    (c) => c && c.categoria_path && c.categoria_path[0] === nombreDeCuarto
  );
  const reconocidos = delCuarto.filter((c) => c[campo] === true || _algunaCamara(c));
  if (!reconocidos.length) return false;
  return delCuarto.every((c) => c[campo] === true || !_algunaCamara(c));
}

function _algunaCamara(clip) {
  return _MARCAS.some(({ campo }) => clip[campo] === true);
}

// Las marcas que aplican a este cuarto, en el orden fijo Sony/Pocket/Drone.
function _marcasDelCuarto(clipsDelManifest, nombreDeCuarto) {
  return _MARCAS
    .filter(({ campo }) => _cuartoTieneAlgunClipDe(clipsDelManifest, nombreDeCuarto, campo))
    .map(({ palabra }) => palabra);
}

function _cuartoTieneAlgunClipDe(clipsDelManifest, nombreDeCuarto, campo) {
  return (clipsDelManifest || []).some(
    (c) => c && c.categoria_path && c.categoria_path[0] === nombreDeCuarto && c[campo] === true
  );
}

// Arma el nombre final de la carpeta: numero (si lo hay) + marca(s) (si
// aplican) + nombre del cuarto -- EN ESE ORDEN, pegado al nombre nunca
// antes del numero: "03. [SONY+DRONE] Cocina", no
// "[SONY+DRONE] 03. Cocina".
function nombreDelCuartoConMarca(nombreConNumero, nombreSinNumero, clipsDelManifest) {
  const marcas = _marcasDelCuarto(clipsDelManifest, nombreSinNumero);
  if (!marcas.length) return nombreConNumero;
  const numero = nombreConNumero.slice(
    0, nombreConNumero.length - nombreSinNumero.length);
  return numero + "[" + marcas.join("+") + "] " + nombreSinNumero;
}
```

*(Nota para quien implemente: `_cuartoEsDeCamara` no se usa en el flujo final -- el criterio real está en `_cuartoTieneAlgunClipDe`, que solo pregunta "¿algún clip de este cuarto vino de esta cámara?", sin exigir que TODOS lo sean, porque con tres cámaras posibles la regla de "todo o nada" ya no aplica -- lo que se combina es distinto de lo que se apaga. Bórrala si el linter de UXP se queja de función sin usar, o no la incluyas al copiar este bloque.)*

- [ ] **Step 3: Escribir `uxp-plugin/pruebas/marcaCamara.pruebas.js`**

Sigue el formato de `numeroDeCuarto.pruebas.js` (una función que recibe el `contexto` con las funciones ya cargadas por `vm`, y devuelve una lista de casos `{nombre, correr}`). Reescribe los casos de `marcaDron.pruebas.js` con los nombres nuevos y agrega los de combinación:

```javascript
module.exports = function (contexto) {
  const { nombreDelCuartoConMarca, sinMarcaDeCamara } = contexto;

  function clip(cuarto, opts) {
    return Object.assign({ categoria_path: [cuarto] }, opts);
  }

  return [
    {
      nombre: "un cuarto solo de Sony se marca [SONY]",
      correr: () => {
        const clips = [clip("Cocina", { bin_sony: true })];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        if (resultado !== "03. [SONY] Cocina") throw new Error("dio: " + resultado);
      },
    },
    {
      nombre: "Sony + Drone se combinan en ese orden",
      correr: () => {
        const clips = [
          clip("Cocina", { bin_sony: true }),
          clip("Cocina", { bin_dron: true }),
        ];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        if (resultado !== "03. [SONY+DRONE] Cocina") throw new Error("dio: " + resultado);
      },
    },
    {
      nombre: "las tres camaras se combinan Sony, Pocket, Drone",
      correr: () => {
        const clips = [
          clip("Cocina", { bin_dron: true }),
          clip("Cocina", { bin_pocket: true }),
          clip("Cocina", { bin_sony: true }),
        ];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        if (resultado !== "03. [SONY+POCKET+DRONE] Cocina") throw new Error("dio: " + resultado);
      },
    },
    {
      nombre: "un clip sin camara reconocible (Osmo Action) no apaga la marca de las demas",
      correr: () => {
        const clips = [
          clip("Cocina", { bin_sony: true }),
          clip("Cocina", {}),  // Osmo Action: ninguna bandera en true
        ];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        if (resultado !== "03. [SONY] Cocina") throw new Error("dio: " + resultado);
      },
    },
    {
      nombre: "sin ninguna camara reconocible no hay marca",
      correr: () => {
        const clips = [clip("Cocina", {})];
        const resultado = nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        if (resultado !== "03. Cocina") throw new Error("dio: " + resultado);
      },
    },
    {
      nombre: "sinMarcaDeCamara quita solo una marca conocida al inicio",
      correr: () => {
        if (sinMarcaDeCamara("[SONY+DRONE] Cocina") !== "Cocina") {
          throw new Error("no quito la marca compuesta");
        }
        if (sinMarcaDeCamara("Cocina a mano") !== "Cocina a mano") {
          throw new Error("toco un nombre que Bruno escribio el mismo");
        }
      },
    },
  ];
};
```

- [ ] **Step 4: Actualizar las referencias en `correr.js`**

En `uxp-plugin/pruebas/correr.js`, cambia:
- Línea 40: `"js/marcaDron.js"` → `"js/marcaCamara.js"`
- Línea 60: `require("./marcaDron.pruebas.js")(contexto)` → `require("./marcaCamara.pruebas.js")(contexto)`
- El comentario de la línea 36 (`marcaDron.js` es lógica pura entera...) → menciona `marcaCamara.js`

- [ ] **Step 5: Actualizar `index.html`**

Línea 169: `<script src="js/marcaDron.js"></script>` → `<script src="js/marcaCamara.js"></script>`

- [ ] **Step 6: Borrar los archivos viejos**

```bash
git rm uxp-plugin/js/marcaDron.js uxp-plugin/pruebas/marcaDron.pruebas.js
```

- [ ] **Step 7: Correr las pruebas del plugin**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todos los casos en verde, incluidos los 6 nuevos de `marcaCamara.pruebas.js` y los que ya pasaban (`numeroDeCuarto`, `avance`, `secuencia`)

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
Marcar [SONY] y [POCKET] además de [DRONE], combinadas por cuarto

marcaDron.js pasa a marcaCamara.js. A diferencia de [DRONE] sola, que
se apagaba ante cualquier mezcla, un cuarto con más de una cámara
ahora se marca con las dos combinadas, en el orden fijo Sony, Pocket,
Drone. Osmo Action no entra en el sistema y no altera el resultado.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## F4 — El backend de entrega: estado del proyecto + módulo `drive.py`

### F4.a — Dónde vive el estado de entrega de un proyecto

**Files:**
- Modify: `src/clasificador_video/proyecto.py:128-190` (`a_dict`)
- Test: `tests/test_proyecto.py`

- [ ] **Step 1: Escribir el test de que `entrega` viaja en el documento**

```python
def test_a_dict_incluye_entrega_none_por_defecto():
    data = proyecto.a_dict(
        proyecto="Casa Reforma", rooms=[], clips=[], bins=_bins_vacio(),
        tamanos={}, duraciones={}, rotaciones={},
    )

    assert data["entrega"] is None


def test_a_dict_incluye_entrega_cuando_se_pasa():
    entrega = {
        "estado": "con_editor",
        "subido_en": "2026-09-16T10:00:00",
        "prproj_local": "/x/Casa Reforma.prproj",
        "drive_folder_id": "abc123",
        "drive_prproj_modificado_en": "2026-09-16T10:00:00",
    }

    data = proyecto.a_dict(
        proyecto="Casa Reforma", rooms=[], clips=[], bins=_bins_vacio(),
        tamanos={}, duraciones={}, rotaciones={}, entrega=entrega,
    )

    assert data["entrega"] == entrega
```

(Usa el mismo helper `_bins_vacio()` que ya exista en `tests/test_proyecto.py` para los demás tests de `a_dict` -- revisa el archivo con `grep -n "def _bins_vacio\|def test_a_dict" tests/test_proyecto.py` antes de escribir, por si el nombre real es otro.)

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -k entrega -v`
Expected: FAIL con `TypeError: a_dict() got an unexpected keyword argument 'entrega'`

- [ ] **Step 3: Agregar el parámetro `entrega` a `a_dict`**

En la firma de `a_dict` (junto a `guia: dict | None = None`):

```python
           guia: dict | None = None,
           entrega: dict | None = None) -> dict:
```

Y en el diccionario devuelto, junto a `"guia": guia,`:

```python
        # El estado de la entrega a un editor externo (subir/traer por
        # Drive). `None` es un proyecto que nunca la usó -- mismo criterio
        # que `guia` y `carpeta_de_proxies`: los proyectos de antes de hoy
        # abren igual que siempre. La forma exacta del dict la define
        # `entrega.py` (EstadoEntrega.to_dict / de_dict).
        "entrega": entrega,
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -v`
Expected: PASS todos

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proyecto.py tests/test_proyecto.py
git commit -m "$(cat <<'EOF'
Agregar el campo "entrega" al documento del proyecto

Mismo criterio que "guia" y "carpeta_de_proxies": None es un proyecto
que nunca usó la entrega a un editor externo, y abre exactamente igual
que antes de este cambio.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### F4.b — El dataclass `EstadoEntrega`

**Files:**
- Create: `src/clasificador_video/entrega.py`
- Test: `tests/test_entrega.py`

- [ ] **Step 1: Escribir `tests/test_entrega.py`**

```python
# tests/test_entrega.py
from clasificador_video.entrega import EstadoEntrega


def test_sin_entrega_previa_es_none():
    assert EstadoEntrega.de_dict(None) is None


def test_ida_y_vuelta_por_dict():
    original = EstadoEntrega(
        estado="con_editor",
        subido_en="2026-09-16T10:00:00",
        prproj_local="/x/Casa Reforma.prproj",
        drive_folder_id="abc123",
        drive_prproj_modificado_en="2026-09-16T10:00:00",
    )

    de_vuelta = EstadoEntrega.de_dict(original.to_dict())

    assert de_vuelta == original


def test_estados_posibles():
    assert EstadoEntrega.SIN_SUBIR == "sin_subir"
    assert EstadoEntrega.CON_EDITOR == "con_editor"
    assert EstadoEntrega.EDITOR_CONTESTO == "editor_contesto"
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_entrega.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Escribir `src/clasificador_video/entrega.py`**

```python
"""El estado de la entrega de un proyecto a un editor externo por Drive.

Vive aparte de `proyecto.py` porque `proyecto.py` sabe la FORMA del
documento entero y este módulo sabe solo esta pieza -- igual que
`manifest.py` no sabe nada del `.cvproj`.

Tres estados nada más, en el orden en que pasan:

- `SIN_SUBIR` -- nunca se subió nada (o es un proyecto de antes de esta
  función: no hay diferencia).
- `CON_EDITOR` -- ya se subió; no se sabe si el editor contestó porque
  esa pregunta es siempre a petición de Bruno (nunca automática al abrir
  la app -- spec de interfaz, §4).
- `EDITOR_CONTESTO` -- Bruno pidió revisar (el ⟳ de la lista, o el
  diálogo de "Traer de vuelta") y Drive tenía algo nuevo.

Sin Qt, sin red: esto solo carga y guarda el estado. Quien pregunta a
Drive de verdad es `drive.py`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EstadoEntrega:
    SIN_SUBIR = "sin_subir"
    CON_EDITOR = "con_editor"
    EDITOR_CONTESTO = "editor_contesto"

    estado: str
    subido_en: str | None = None
    prproj_local: str | None = None
    drive_folder_id: str | None = None
    drive_folder_link: str | None = None
    # La fecha de modificación del .prproj en Drive TAL COMO ESTABA cuando
    # se subió por última vez. Es contra lo que se compara al revisar si
    # el editor ya contestó -- ver `drive.hay_cambios`.
    drive_prproj_modificado_en: str | None = None

    def to_dict(self) -> dict:
        return {
            "estado": self.estado,
            "subido_en": self.subido_en,
            "prproj_local": self.prproj_local,
            "drive_folder_id": self.drive_folder_id,
            "drive_folder_link": self.drive_folder_link,
            "drive_prproj_modificado_en": self.drive_prproj_modificado_en,
        }

    @staticmethod
    def de_dict(datos: dict | None) -> "EstadoEntrega | None":
        if not datos:
            return None
        return EstadoEntrega(
            estado=datos.get("estado", EstadoEntrega.SIN_SUBIR),
            subido_en=datos.get("subido_en"),
            prproj_local=datos.get("prproj_local"),
            drive_folder_id=datos.get("drive_folder_id"),
            drive_folder_link=datos.get("drive_folder_link"),
            drive_prproj_modificado_en=datos.get("drive_prproj_modificado_en"),
        )
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_entrega.py -v`
Expected: PASS los 3

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/entrega.py tests/test_entrega.py
git commit -m "$(cat <<'EOF'
Agregar EstadoEntrega: los tres estados de la entrega a un editor

sin_subir / con_editor / editor_contesto. La pregunta a Drive es
siempre a petición de Bruno, nunca automática -- así que
"editor_contesto" solo se sabe después de que él aprieta revisar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### F4.c — Buscar el `.prproj` por folio

**Files:**
- Create: `src/clasificador_video/buscar_prproj.py`
- Test: `tests/test_buscar_prproj.py`

- [ ] **Step 1: Escribir `tests/test_buscar_prproj.py`**

```python
# tests/test_buscar_prproj.py
from pathlib import Path

from clasificador_video.buscar_prproj import buscar_por_folio


def _tocar(ruta: Path, contenido: bytes = b"x") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)


def test_una_sola_coincidencia(tmp_path):
    raiz = tmp_path / "IAV"
    _tocar(raiz / "2026" / "09. Septiembre" / "IAV-2609.10-A.prproj")

    resultado = buscar_por_folio(raiz, "IAV-2609.10-A")

    assert len(resultado) == 1
    assert resultado[0].name == "IAV-2609.10-A.prproj"


def test_varias_versiones_ordenadas_por_fecha_mas_nueva_primero(tmp_path):
    import os
    import time

    raiz = tmp_path / "IAV"
    vieja = raiz / "2026" / "09. Septiembre" / "IAV-2609.10-A.prproj"
    nueva = raiz / "2026" / "09. Septiembre" / "IAV-2609.10-A V2.prproj"
    _tocar(vieja)
    time.sleep(0.01)
    _tocar(nueva)
    os.utime(nueva, None)  # asegura mtime >= al de "vieja" en cualquier FS

    resultado = buscar_por_folio(raiz, "IAV-2609.10-A")

    assert [r.name for r in resultado] == [
        "IAV-2609.10-A V2.prproj", "IAV-2609.10-A.prproj",
    ]


def test_sin_coincidencia_devuelve_lista_vacia(tmp_path):
    raiz = tmp_path / "IAV"
    _tocar(raiz / "2026" / "09. Septiembre" / "otro-folio.prproj")

    assert buscar_por_folio(raiz, "IAV-2609.10-A") == []


def test_no_confunde_folios_que_empiezan_igual(tmp_path):
    """"2609.1" no debe encontrar "2609.10-A": el folio se busca como
    substring exacto, y un folio corto que calza por accidente dentro de
    uno mas largo traeria el proyecto equivocado."""
    raiz = tmp_path / "IAV"
    _tocar(raiz / "2026" / "IAV-2609.10-A.prproj")

    assert buscar_por_folio(raiz, "IAV-2609.1") == []


def test_carpeta_raiz_que_no_existe_no_truena(tmp_path):
    assert buscar_por_folio(tmp_path / "no existe", "cualquiera") == []
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_buscar_prproj.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Escribir `src/clasificador_video/buscar_prproj.py`**

```python
"""Encontrar el .prproj de un proyecto por su folio, en la carpeta raíz
donde Bruno guarda todos sus proyectos de Premiere.

El nombre del proyecto de Clipify YA ES el folio de Bruno
(`IAV-2609.10-A`, `2607.09`...), así que no hace falta pedirle la ruta
cada vez que quiere subir a Drive: se busca recursivamente bajo la
carpeta raíz (que sí se pregunta UNA vez, en Configuración) un `.prproj`
cuyo nombre contenga ese folio.

Sin Qt: recorre disco, nada más. El diálogo que MUESTRA el resultado
--y que deja cambiarlo a mano-- vive en la interfaz.
"""
from __future__ import annotations

from pathlib import Path


def buscar_por_folio(carpeta_raiz: Path, folio: str) -> list[Path]:
    """Todas las coincidencias, de más nueva a más vieja por fecha de
    modificación. Vacía si la carpeta no existe, no se puede leer, o
    ningún `.prproj` contiene el folio como substring exacto.
    """
    if not folio:
        return []
    try:
        candidatos = [
            p for p in carpeta_raiz.rglob("*.prproj")
            if folio in p.stem
        ]
    except OSError:
        return []
    return sorted(candidatos, key=lambda p: p.stat().st_mtime, reverse=True)
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_buscar_prproj.py -v`
Expected: PASS los 5

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/buscar_prproj.py tests/test_buscar_prproj.py
git commit -m "$(cat <<'EOF'
Agregar la búsqueda del .prproj por folio

El nombre del proyecto de Clipify ya es el folio de Bruno. Busca
recursivamente bajo la carpeta raíz de sus proyectos de Premiere y
devuelve las coincidencias ordenadas de más nueva a más vieja -- el
diálogo de "Subir a Drive" decide qué enseñar con esta lista.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### F4.d — Preferencia nueva: la carpeta raíz de proyectos de Premiere

**Files:**
- Modify: `src/clasificador_video/preferencias.py`
- Test: `tests/test_preferencias.py`

- [ ] **Step 1: Escribir el test**

```python
def test_carpeta_de_proyectos_premiere_vacia_por_defecto(tmp_path):
    ruta = tmp_path / "preferencias.json"
    assert preferencias.carpeta_de_proyectos_premiere(ruta) is None


def test_guardar_y_leer_carpeta_de_proyectos_premiere(tmp_path):
    ruta = tmp_path / "preferencias.json"
    carpeta = tmp_path / "IAV"

    preferencias.guardar_carpeta_de_proyectos_premiere(carpeta, ruta)

    assert preferencias.carpeta_de_proyectos_premiere(ruta) == carpeta
```

- [ ] **Step 2: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_preferencias.py -k premiere -v`
Expected: FAIL con `AttributeError`

- [ ] **Step 3: Agregar las dos funciones a `preferencias.py`**

```python
from pathlib import Path


def carpeta_de_proyectos_premiere(ruta: Path | None = None) -> Path | None:
    """Dónde busca `buscar_prproj.buscar_por_folio`. `None` hasta que
    Bruno la ponga en Configuración -- sin ella, "Subir a Drive" cae
    directo al selector manual."""
    valor = _leer_todo(ruta).get("carpeta_de_proyectos_premiere")
    return Path(valor) if valor else None


def guardar_carpeta_de_proyectos_premiere(carpeta: Path, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = _leer_todo(ruta)
    datos["carpeta_de_proyectos_premiere"] = str(carpeta)
    destino.write_text(json.dumps(datos), encoding="utf-8")
```

- [ ] **Step 4: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_preferencias.py -v`
Expected: PASS todos

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/preferencias.py tests/test_preferencias.py
git commit -m "$(cat <<'EOF'
Agregar la preferencia de la carpeta raíz de proyectos de Premiere

Se pregunta una sola vez en Configuración, igual que la carpeta de
proxies, y de ahí en adelante alimenta la búsqueda por folio al subir
a Drive.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### F4.e — El módulo `drive.py`: subir y revisar/traer

**Files:**
- Create: `src/clasificador_video/drive.py`
- Test: `tests/test_drive.py`
- Modify: `pyproject.toml` (nuevas dependencias)

- [ ] **Step 1: Agregar las dependencias de Drive**

En `pyproject.toml`, dentro de `dependencies`:

```toml
    "google-api-python-client>=2.100",
    "google-auth-httplib2>=0.2",
    "google-auth-oauthlib>=1.2",
```

Run: `.venv/bin/pip install -e .`

- [ ] **Step 2: Diseñar `drive.py` alrededor de un cliente inyectado**

`drive.py` **nunca construye su propio cliente de Google adentro de las funciones que suben o bajan** -- lo recibe como parámetro. Así, cada función se prueba con un cliente falso (un objeto Python cualquiera con los mismos métodos) sin tocar la red, tal como pide la spec original §8 ("mockear las llamadas a la API de Drive"). Quien construye el cliente real (con las credenciales de Bruno, vía `google-auth-oauthlib`) es una función aparte, `cliente_autorizado()`, que la interfaz llama una sola vez y no se prueba con pytest -- se prueba a mano, con la cuenta real de Bruno, como dice la spec (§8, "Subir/bajar de Drive: se prueba con una cuenta de prueba").

- [ ] **Step 3: Escribir `tests/test_drive.py` con un cliente falso**

```python
# tests/test_drive.py
from pathlib import Path

from clasificador_video import drive


class _ArchivoFalso:
    """Lo que la API de Drive devuelve por archivo: id, nombre, y cuándo
    se modificó por última vez (RFC 3339, como lo entrega Drive de
    verdad)."""

    def __init__(self, id, name, modified_time, parents=None, mime_type="video/mp4"):
        self.id = id
        self.name = name
        self.modified_time = modified_time
        self.parents = parents or []
        self.mime_type = mime_type


class _ClienteFalso:
    """Un doble de `googleapiclient.discovery.Resource` con solo lo que
    `drive.py` usa. Cada método devuelve lo que se le precarga."""

    def __init__(self, archivos: list[_ArchivoFalso] | None = None):
        self.archivos = archivos or []
        self.subidos: list[tuple[str, Path]] = []
        self.carpetas_creadas: list[str] = []

    def crear_carpeta(self, nombre: str, carpeta_padre_id: str | None = None) -> str:
        self.carpetas_creadas.append(nombre)
        return f"folder-{nombre}"

    def subir_archivo(self, ruta_local: Path, carpeta_id: str) -> str:
        self.subidos.append((carpeta_id, ruta_local))
        return f"file-{ruta_local.name}"

    def listar_en_carpeta(self, carpeta_id: str) -> list[_ArchivoFalso]:
        return self.archivos

    def descargar_archivo(self, archivo_id: str, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(f"contenido de {archivo_id}")

    def link_de_carpeta(self, carpeta_id: str) -> str:
        return f"https://drive.google.com/drive/folders/{carpeta_id.replace('folder-', '')}"


def test_subir_paquete_crea_carpeta_y_sube_prproj_y_proxies(tmp_path):
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")
    proxy1 = tmp_path / "C0001S03.mp4"
    proxy1.write_text("x")

    resultado = drive.subir_paquete(
        cliente, nombre_proyecto="Casa Reforma",
        prproj=prproj, proxies=[proxy1],
    )

    assert cliente.carpetas_creadas == ["Casa Reforma", "Proxies"]
    assert (cliente.subidos[0][1] == prproj)
    assert (cliente.subidos[1][1] == proxy1)
    assert resultado.folder_link.startswith("https://drive.google.com/")


def test_hay_cambios_cuando_el_prproj_de_drive_es_mas_nuevo():
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "Casa Reforma.prproj", "2026-09-18T12:00:00Z"),
    ])

    resultado = drive.revisar_cambios(
        cliente, carpeta_id="folder-x",
        prproj_modificado_en_la_subida="2026-09-16T10:00:00Z",
    )

    assert resultado.hay_cambios is True
    assert resultado.prproj_modificado_en == "2026-09-18T12:00:00Z"


def test_no_hay_cambios_cuando_la_fecha_es_igual():
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "Casa Reforma.prproj", "2026-09-16T10:00:00Z"),
    ])

    resultado = drive.revisar_cambios(
        cliente, carpeta_id="folder-x",
        prproj_modificado_en_la_subida="2026-09-16T10:00:00Z",
    )

    assert resultado.hay_cambios is False


def test_revisar_cambios_lista_el_material_nuevo():
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "Casa Reforma.prproj", "2026-09-18T12:00:00Z"),
        _ArchivoFalso("f2", "material nuevo", "2026-09-18T12:00:00Z",
                      mime_type="application/vnd.google-apps.folder"),
    ])

    resultado = drive.revisar_cambios(
        cliente, carpeta_id="folder-x",
        prproj_modificado_en_la_subida="2026-09-16T10:00:00Z",
    )

    assert resultado.tiene_material_nuevo is True


def test_traer_de_vuelta_descarga_el_prproj_al_destino(tmp_path):
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "Casa Reforma.prproj", "2026-09-18T12:00:00Z"),
    ])
    destino = tmp_path / "Casa Reforma.prproj"

    drive.traer_prproj(cliente, carpeta_id="folder-x", destino=destino)

    assert destino.read_text() == "contenido de f1"


def test_traer_material_nuevo_baja_cada_subcarpeta_a_su_categoria(tmp_path):
    material_nuevo_id = "folder-material-nuevo"
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("fm", "musica y audio", "2026-09-18T12:00:00Z",
                      mime_type="application/vnd.google-apps.folder"),
    ])
    # el cliente falso devuelve la misma lista sin importar la carpeta que
    # se le pida, así que esto alcanza para probar el reparto por nombre
    destino_base = tmp_path / "01. ASSETS VIDEO"

    reparto = drive.mapa_de_categorias_de_material_nuevo()

    assert reparto["musica y audio"] == "05. MUSICA Y AUDIO"
    assert reparto["fotos"] == "04. FOTOS"
    assert reparto["graficos y branding"] == "06. GRAFICOS Y BRANDING"
```

*(Ajusta los nombres exactos de subcarpeta en `mapa_de_categorias_de_material_nuevo` a la estructura real de `01. ASSETS VIDEO` de Bruno -- revísala con `cat uxp-plugin/js/estructura.js` antes de fijar los tres nombres; ese archivo ya tiene la lista canónica de las siete carpetas.)*

- [ ] **Step 4: Correr y confirmar que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_drive.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 5: Escribir `src/clasificador_video/drive.py`**

```python
"""Subir y bajar de Google Drive para la entrega a un editor externo.

Cada función que toca la red recibe el CLIENTE ya armado como parámetro
--nunca lo construye ella misma-- para poder probarse con un doble sin
tocar la red (spec 2026-09-18 §8). Quien arma el cliente real, con las
credenciales de Bruno, es `cliente_autorizado()`, y esa función no se
prueba con pytest: se prueba a mano, con la cuenta de Bruno.

El cliente esperado (real o falso) implementa:
  - crear_carpeta(nombre, carpeta_padre_id=None) -> id
  - subir_archivo(ruta_local, carpeta_id) -> id
  - listar_en_carpeta(carpeta_id) -> list de objetos con
    .id, .name, .modified_time, .mime_type
  - descargar_archivo(archivo_id, destino: Path) -> None
  - link_de_carpeta(carpeta_id) -> str
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CARPETA_PROXIES = "Proxies"
CARPETA_MATERIAL_NUEVO = "material nuevo"
CARPETA_MIME = "application/vnd.google-apps.folder"


@dataclass(frozen=True)
class ResultadoDeSubida:
    folder_id: str
    folder_link: str


def subir_paquete(cliente, nombre_proyecto: str, prproj: Path,
                   proxies: list[Path]) -> ResultadoDeSubida:
    """Crea la carpeta del proyecto en Drive, sube el `.prproj` y los
    proxies (en su propia subcarpeta), y devuelve el link para
    compartirle al editor.
    """
    carpeta_id = cliente.crear_carpeta(nombre_proyecto)
    cliente.subir_archivo(prproj, carpeta_id)
    proxies_id = cliente.crear_carpeta(CARPETA_PROXIES, carpeta_padre_id=carpeta_id)
    for proxy in proxies:
        cliente.subir_archivo(proxy, proxies_id)
    return ResultadoDeSubida(
        folder_id=carpeta_id, folder_link=cliente.link_de_carpeta(carpeta_id),
    )


@dataclass(frozen=True)
class ResultadoDeRevision:
    hay_cambios: bool
    prproj_modificado_en: str | None
    tiene_material_nuevo: bool


def revisar_cambios(cliente, carpeta_id: str,
                    prproj_modificado_en_la_subida: str | None) -> ResultadoDeRevision:
    """¿El `.prproj` de Drive es más nuevo que el que se subió, o ya hay
    algo en `material nuevo/`? Ninguna de las dos cosas se descarga
    todavía -- esto solo mira fechas y nombres."""
    archivos = cliente.listar_en_carpeta(carpeta_id)
    prproj = next((a for a in archivos if a.name.endswith(".prproj")), None)
    modificado_en = prproj.modified_time if prproj is not None else None
    hay_cambios = (
        modificado_en is not None
        and modificado_en != prproj_modificado_en_la_subida
    )
    tiene_material_nuevo = any(
        a.name == CARPETA_MATERIAL_NUEVO and a.mime_type == CARPETA_MIME
        for a in archivos
    )
    return ResultadoDeRevision(
        hay_cambios=hay_cambios, prproj_modificado_en=modificado_en,
        tiene_material_nuevo=tiene_material_nuevo,
    )


def traer_prproj(cliente, carpeta_id: str, destino: Path) -> None:
    """Baja el `.prproj` de esa carpeta al destino, reemplazándolo."""
    archivos = cliente.listar_en_carpeta(carpeta_id)
    prproj = next(a for a in archivos if a.name.endswith(".prproj"))
    cliente.descargar_archivo(prproj.id, destino)


def mapa_de_categorias_de_material_nuevo() -> dict[str, str]:
    """De la subcarpeta de `material nuevo/` a su categoría real dentro
    de `01. ASSETS VIDEO` (spec original §6). Nombres tomados de
    `uxp-plugin/js/estructura.js` -- si esa lista cambia ahí, cambia
    aquí también."""
    return {
        "musica y audio": "05. MUSICA Y AUDIO",
        "fotos": "04. FOTOS",
        "graficos y branding": "06. GRAFICOS Y BRANDING",
    }
```

- [ ] **Step 6: Correr y confirmar que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_drive.py -v`
Expected: PASS todos (ajusta los tres nombres de `mapa_de_categorias_de_material_nuevo` si `estructura.js` usa otros)

- [ ] **Step 7: Escribir `cliente_autorizado()` — no se prueba con pytest**

Agrega al final de `drive.py`:

```python
_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_RUTA_TOKEN = Path.home() / ".clasificador_video" / "drive_token.json"


class _ClienteDrive:
    """El envoltorio real sobre `googleapiclient.discovery.Resource`,
    con la misma forma que el doble de pruebas."""

    def __init__(self, servicio):
        self._s = servicio

    def crear_carpeta(self, nombre, carpeta_padre_id=None):
        metadata = {"name": nombre, "mimeType": CARPETA_MIME}
        if carpeta_padre_id:
            metadata["parents"] = [carpeta_padre_id]
        creada = self._s.files().create(body=metadata, fields="id").execute()
        return creada["id"]

    def subir_archivo(self, ruta_local, carpeta_id):
        from googleapiclient.http import MediaFileUpload
        metadata = {"name": ruta_local.name, "parents": [carpeta_id]}
        media = MediaFileUpload(str(ruta_local), resumable=True)
        subido = self._s.files().create(
            body=metadata, media_body=media, fields="id").execute()
        return subido["id"]

    def listar_en_carpeta(self, carpeta_id):
        respuesta = self._s.files().list(
            q=f"'{carpeta_id}' in parents and trashed = false",
            fields="files(id, name, modifiedTime, mimeType)",
        ).execute()
        return [_Archivo(a) for a in respuesta.get("files", [])]

    def descargar_archivo(self, archivo_id, destino):
        from googleapiclient.http import MediaIoBaseDownload
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "wb") as f:
            descargador = MediaIoBaseDownload(f, self._s.files().get_media(fileId=archivo_id))
            terminado = False
            while not terminado:
                _, terminado = descargador.next_chunk()

    def link_de_carpeta(self, carpeta_id):
        return f"https://drive.google.com/drive/folders/{carpeta_id}"


class _Archivo:
    def __init__(self, datos: dict):
        self.id = datos["id"]
        self.name = datos["name"]
        self.modified_time = datos.get("modifiedTime")
        self.mime_type = datos.get("mimeType", "")


def cliente_autorizado(credenciales_oauth_json: Path):
    """Abre el flujo de OAuth de Google en el navegador la primera vez
    (permiso acotado: `drive.file`, Clipify solo toca lo que ella misma
    sube -- spec original, "Por qué Drive y con qué permiso") y guarda el
    token en `~/.clasificador_video/drive_token.json` para las próximas
    veces. NO se prueba con pytest: necesita la cuenta real de Bruno.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if _RUTA_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(_RUTA_TOKEN), _SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credenciales_oauth_json), _SCOPES)
            creds = flow.run_local_server(port=0)
        _RUTA_TOKEN.parent.mkdir(parents=True, exist_ok=True)
        _RUTA_TOKEN.write_text(creds.to_json())

    from googleapiclient.discovery import build
    return _ClienteDrive(build("drive", "v3", credentials=creds))
```

- [ ] **Step 8: Correr toda la suite una vez más**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_drive.py -v`
Expected: PASS (el bloque de `cliente_autorizado` no tiene test, y está bien: es la parte que la spec original marca como "se prueba con una cuenta de prueba", a mano)

- [ ] **Step 9: Commit**

```bash
git add src/clasificador_video/drive.py tests/test_drive.py pyproject.toml
git commit -m "$(cat <<'EOF'
Agregar el módulo drive.py: subir, revisar cambios y traer de vuelta

Cada función que toca la red recibe el cliente ya armado como
parámetro, así que se prueba entera con un doble sin tocar Drive de
verdad. cliente_autorizado() arma el cliente real vía OAuth (permiso
acotado drive.file) y no lleva test de pytest -- se valida a mano,
con la cuenta de Bruno, como pide la spec.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## F5 — Interfaz: la barra superior y los dos diálogos

**Files:**
- Modify: `src/clasificador_video/ui/title_bar.py`
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_title_bar.py` (o el archivo de tests de `title_bar` que ya exista — revisa con `ls tests/ui/ | grep title`)
- Test: `tests/ui/test_main_window_entrega.py` (nuevo)

Esta fase es la más grande y la única donde el resultado se valida también con el ojo, no solo con pytest (regla del proyecto: `CLAUDE.md`, "Verificación visual real"). Sigue el patrón exacto de `visor_button` / `_al_elegir_visor` en `title_bar.py` para las señales, y el de `_preguntar_por_la_carpeta_de_proxies` en `main_window.py` (líneas ~2914-2944) para los diálogos: `QMessageBox` con botones propios, nunca `QFileDialog` a secas, y el método que lo abre se monkeypatchea entero en los tests en vez de simular clics dentro de un `exec()` real.

- [ ] **Step 1: Agregar las señales y los widgets de estado a `TitleBar`**

En `title_bar.py`, junto a las señales existentes:

```python
    subir_a_drive_requested = Signal()
    traer_de_vuelta_requested = Signal()
```

Junto a `self.export_button` (después de crearlo), agrega los widgets de la cápsula de entrega — un solo `QWidget` contenedor para poder mostrar/esconder sus hijos como grupo:

```python
        # La cápsula de entrega a un editor externo: cambia de contenido
        # según el estado de ESE proyecto (spec de interfaz, §1), el resto
        # de la barra no se mueve. Un solo host para poder alternar sus
        # hijos sin desarmar el layout cada vez.
        self.entrega_host = QWidget()
        entrega_layout = QHBoxLayout(self.entrega_host)
        entrega_layout.setContentsMargins(0, 0, 0, 0)
        entrega_layout.setSpacing(8)

        self.entrega_pill = QLabel("")
        self.entrega_pill.setObjectName("entregaPill")
        self.entrega_pill.hide()

        self.subir_button = _boton("Subir a Drive", "", "railButton")
        self.subir_button.clicked.connect(self.subir_a_drive_requested.emit)

        self.traer_button = _boton("Traer de vuelta", "", "exportButton")
        self.traer_button.clicked.connect(self.traer_de_vuelta_requested.emit)
        self.traer_button.hide()

        entrega_layout.addWidget(self.entrega_pill)
        entrega_layout.addWidget(self.subir_button)
        entrega_layout.addWidget(self.traer_button)
        layout.addWidget(self.entrega_host)
```

- [ ] **Step 2: El método que dibuja los 4 estados**

```python
    def set_estado_de_entrega(self, estado: str | None, cuando_texto: str = "") -> None:
        """Los 4 estados de la spec de interfaz §1. `estado` es uno de
        `EstadoEntrega.SIN_SUBIR/CON_EDITOR/EDITOR_CONTESTO`, o `None`
        para un proyecto que nunca la usó -- que se ve IGUAL que
        `SIN_SUBIR`: el botón "Subir a Drive" siempre está, desde el
        primer día (Bruno lo pidió así, "siempre visible").
        """
        from clasificador_video.entrega import EstadoEntrega

        self.subir_button.setText("Subir a Drive")
        self.subir_button.setEnabled(True)
        self.traer_button.hide()
        self.entrega_pill.hide()

        if estado == EstadoEntrega.CON_EDITOR:
            self.subir_button.setText("Subir de nuevo")
            self.entrega_pill.setText(f"●  Con el editor · {cuando_texto}")
            self.entrega_pill.setProperty("tono", "esperando")
            self.entrega_pill.show()
            self.traer_button.show()
        elif estado == EstadoEntrega.EDITOR_CONTESTO:
            self.subir_button.setText("Subir de nuevo")
            self.entrega_pill.setText(f"✓  El editor ya contestó · {cuando_texto}")
            self.entrega_pill.setProperty("tono", "contesto")
            self.entrega_pill.show()
            self.traer_button.show()
        self.entrega_pill.style().unpolish(self.entrega_pill)
        self.entrega_pill.style().polish(self.entrega_pill)

    def set_subiendo(self, porcentaje: int) -> None:
        """El estado 2 de la spec: el botón se apaga y muestra progreso.
        Se sale de este estado llamando de nuevo a `set_estado_de_entrega`."""
        self.subir_button.setEnabled(False)
        self.subir_button.setText(f"Subiendo… {porcentaje}%")
```

- [ ] **Step 3: Test de `title_bar.py`**

Revisa primero qué archivo ya prueba `TitleBar` (`ls tests/ui/ | grep -i title`) y sigue su patrón de fixture (`qtbot`, `pytest-qt`). Agrega:

```python
def test_sin_estado_solo_se_ve_subir_a_drive(title_bar):
    title_bar.set_estado_de_entrega(None)

    assert title_bar.subir_button.text() == "Subir a Drive"
    assert not title_bar.traer_button.isVisible()
    assert not title_bar.entrega_pill.isVisible()


def test_con_editor_muestra_pildora_y_traer(title_bar):
    from clasificador_video.entrega import EstadoEntrega

    title_bar.set_estado_de_entrega(EstadoEntrega.CON_EDITOR, "hace 2 días")

    assert "Con el editor" in title_bar.entrega_pill.text()
    assert title_bar.traer_button.isVisible()
    assert title_bar.subir_button.text() == "Subir de nuevo"


def test_subiendo_apaga_el_boton_con_progreso(title_bar):
    title_bar.set_subiendo(42)

    assert not title_bar.subir_button.isEnabled()
    assert "42%" in title_bar.subir_button.text()
```

(Si el archivo de tests de `title_bar` no trae ya una fixture `title_bar`, créala igual que las demás pruebas de widgets de este proyecto: `title_bar = TitleBar(); qtbot.addWidget(title_bar); return title_bar`.)

- [ ] **Step 4: Correr y ajustar hasta que pasen**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/ -k title_bar -v`
Expected: PASS

- [ ] **Step 5: El diálogo "Subir a Drive" en `main_window.py`**

Sigue el patrón de `_preguntar_por_la_carpeta_de_proxies`. Agrega:

```python
    def _al_pedir_subir_a_drive(self) -> None:
        from clasificador_video import buscar_prproj, preferencias

        raiz = preferencias.carpeta_de_proyectos_premiere()
        candidatos = buscar_prproj.buscar_por_folio(raiz, self.project_name) if raiz else []
        prproj = self._preguntar_por_el_prproj(candidatos)
        if prproj is None:
            return
        self._subir_a_drive(prproj)

    def _preguntar_por_el_prproj(self, candidatos: list[Path]) -> Path | None:
        """La ruta del `.prproj`, ya propuesta si se encontró por folio.

        Tres casos (spec de interfaz §2): una coincidencia, varias
        (se propone la más nueva y SE DICE que hay otra), o ninguna
        (selector manual). Nunca sube sin que la ruta se haya visto.
        """
        picks = [i for i, c in enumerate(self.clips) if c.flag == "pick"]
        resumen = (
            f"Clips a subir (picks): {len(picks)} de {len(self.clips)}\n"
            "Se sube a: Google Drive de Bruno"
        )
        cuadro = QMessageBox(self)
        cuadro.setWindowTitle("Subir a Drive")
        if candidatos:
            propuesta = candidatos[0]
            extra = (
                f"\n\nHay {len(candidatos)} versiones con este folio -- se "
                "propone la más reciente." if len(candidatos) > 1 else ""
            )
            cuadro.setText(f"Proyecto de Premiere:\n{propuesta}{extra}")
        else:
            propuesta = None
            cuadro.setText("No se encontró un .prproj con este folio.")
        cuadro.setInformativeText(resumen)
        subir = cuadro.addButton("Subir", QMessageBox.ButtonRole.AcceptRole)
        cambiar = cuadro.addButton(
            "Cambiar…" if candidatos else "Elegir…", QMessageBox.ButtonRole.ActionRole)
        cuadro.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        if propuesta is None:
            subir.setEnabled(False)
        cuadro.setDefaultButton(subir)
        cuadro.exec()
        clickeado = cuadro.clickedButton()
        if clickeado is cambiar:
            elegido, _ = QFileDialog.getOpenFileName(
                self, "Elegir el .prproj", "", "Proyecto de Premiere (*.prproj)")
            return Path(elegido) if elegido else propuesta
        if clickeado is subir:
            return propuesta
        return None
```

*(`self._subir_a_drive(prproj)` es la función que arma el paquete de proxies de los picks, llama a `drive.subir_paquete` con el cliente ya autorizado, y guarda el `EstadoEntrega` resultante en el documento del proyecto — se escribe en el Step 7, después de decidir en qué hilo corre la subida.)*

- [ ] **Step 6: Test de `_preguntar_por_el_prproj` con los tres casos, monkeypatcheando `QMessageBox`**

Sigue el mismo patrón que `tests/ui/test_main_window_carpeta_de_proxies.py::test_la_pregunta_sale_una_sola_vez` (monkeypatch de `QMessageBox.exec`/`clickedButton`, o del método completo). Ejemplo con el método completo, más simple de mantener:

```python
def test_al_pedir_subir_llama_a_preguntar_con_los_candidatos(ventana, tmp_path, monkeypatch):
    from clasificador_video import preferencias

    raiz = tmp_path / "IAV"
    (raiz / "2026").mkdir(parents=True)
    (raiz / "2026" / f"{ventana.project_name}.prproj").touch()
    preferencias.guardar_carpeta_de_proyectos_premiere(raiz, ventana._ruta_preferencias)

    llamado = {}
    monkeypatch.setattr(
        ventana, "_preguntar_por_el_prproj",
        lambda candidatos: llamado.setdefault("candidatos", candidatos) or None,
    )

    ventana._al_pedir_subir_a_drive()

    assert len(llamado["candidatos"]) == 1
```

*(Ajusta `ventana._ruta_preferencias` al nombre real que use `MainWindow` para inyectar la ruta de preferencias en los tests — revisa cómo los tests existentes de `modo_economico` se lo pasan a la ventana, por ejemplo en `tests/ui/test_main_window_config.py`, y usa el mismo mecanismo.)*

- [ ] **Step 7: Correr, ajustar y confirmar**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_entrega.py -v`
Expected: PASS

- [ ] **Step 8: El diálogo "Traer de vuelta"**

Mismo patrón, con `drive.revisar_cambios`:

```python
    def _al_pedir_traer_de_vuelta(self) -> None:
        estado = self._estado_de_entrega()
        if estado is None:
            return
        cliente = self._cliente_de_drive()
        resultado = drive.revisar_cambios(
            cliente, estado.drive_folder_id, estado.drive_prproj_modificado_en)
        if not self._confirmar_traer_de_vuelta(resultado):
            return
        self._traer_de_vuelta(estado, cliente)

    def _confirmar_traer_de_vuelta(self, resultado) -> bool:
        cuadro = QMessageBox(self)
        cuadro.setWindowTitle(f"Traer de vuelta — {self.project_name}")
        if resultado.hay_cambios or resultado.tiene_material_nuevo:
            cuadro.setText("Se encontró algo nuevo en Drive.")
            texto = "El .prproj cambió." if resultado.hay_cambios else "El .prproj no ha cambiado."
            if resultado.tiene_material_nuevo:
                texto += " Hay contenido en \"material nuevo/\"."
            cuadro.setInformativeText(
                texto + "\n\nLos proxies no se vuelven a bajar -- ya los tienes."
            )
            boton_texto = "Traer de vuelta"
        else:
            cuadro.setText(
                "No parece que el editor haya subido nada todavía. "
                "¿Seguro que quieres continuar?"
            )
            boton_texto = "Traer de todas formas"
        traer = cuadro.addButton(boton_texto, QMessageBox.ButtonRole.AcceptRole)
        cuadro.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        cuadro.setDefaultButton(traer)
        cuadro.exec()
        return cuadro.clickedButton() is traer
```

- [ ] **Step 9: Test del caso "no hay cambios" (el que más vale la pena cubrir: no debe bloquear)**

```python
def test_confirmar_traer_de_vuelta_sin_cambios_no_bloquea(ventana, monkeypatch):
    from clasificador_video.drive import ResultadoDeRevision

    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(
        QMessageBox, "clickedButton",
        lambda self: self.buttons()[0],  # el primer botón agregado: "Traer de todas formas"
    )

    resultado = ResultadoDeRevision(
        hay_cambios=False, prproj_modificado_en="x", tiene_material_nuevo=False)

    assert ventana._confirmar_traer_de_vuelta(resultado) is True
```

- [ ] **Step 10: Correr toda la suite de UI**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS todo (recuerda: la suite completa corre sin `--ignore`, según `CLAUDE.md`)

- [ ] **Step 11: Verificación visual real**

Construye una `MainWindow` de prueba con un proyecto que tenga `EstadoEntrega.CON_EDITOR`, muéstrala, captura con `grab()`, guarda el PNG en el scratchpad de la sesión y ábrelo con la herramienta de lectura de archivos. Compara contra `titlebar-estados.html` de la sesión de brainstorming. No declares esta fase terminada sin haber mirado el PNG.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
Agregar la barra superior y los diálogos de subir/traer de Drive

TitleBar dibuja los 4 estados de la entrega (sin subir, subiendo, con
el editor, ya trajiste). Los dos diálogos siguen el patrón ya usado
para la carpeta de proxies: QMessageBox con botones propios, la ruta
del .prproj siempre a la vista antes de subir, y "Traer de vuelta"
avisa en vez de bloquear cuando no hay cambios todavía.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## F6 — Interfaz: la pantalla de inicio y Configuración

**Files:**
- Modify: `src/clasificador_video/ui/pantalla_inicio.py`
- Modify: `src/clasificador_video/ui/pantalla_config.py`
- Modify: `src/clasificador_video/recientes.py` (si el estado de entrega necesita leerse ahí — revisar primero)
- Test: `tests/ui/test_pantalla_inicio.py`
- Test: `tests/ui/test_pantalla_config.py`

- [ ] **Step 1: Revisar cómo `PantallaInicio` conoce a cada proyecto hoy**

Run: `grep -n "class.*Entrada\|disponible\|cuando" src/clasificador_video/recientes.py`

El estado de entrega de un proyecto vive en SU `.cvproj` (campo `entrega`, agregado en F4.a), no en `recientes.json`. `set_recientes` va a necesitar, por cada entrada, el `EstadoEntrega` de ese proyecto -- léelo abriendo el `.cvproj` (ya existe una función para leer el documento sin abrir la ventana entera; probablemente `proyecto.abrir` o similar — confírmalo con `grep -n "^def abrir" src/clasificador_video/proyecto.py`).

- [ ] **Step 2: Agregar la píldora a `_FilaReciente`**

En `pantalla_inicio.py`, en `_FilaReciente.__init__`, después de armar `self.detalle`, agrega la píldora y el botón de refrescar, escondidos por defecto:

```python
        self.pildora = QLabel("")
        self.pildora.setObjectName("recientePildora")
        self.pildora.hide()
        self.refrescar_button = QPushButton("⟳")
        self.refrescar_button.setObjectName("recienteRefrescar")
        self.refrescar_button.setToolTip("Revisar si el editor ya contestó")
        self.refrescar_button.hide()
        self.refrescar_button.clicked.connect(
            lambda: self.refrescar_pedido.emit(self.entrada.ruta)
        )

        fila_horizontal = QHBoxLayout()
        fila_horizontal.addWidget(caja.parentWidget() if False else self)  # ver nota
```

*(Nota para quien implemente: `_FilaReciente` hoy arma su contenido con un solo `QVBoxLayout` (`caja`) para nombre+detalle. Para poner la píldora a la DERECHA hace falta envolver ese `QVBoxLayout` y los dos widgets nuevos en un `QHBoxLayout` exterior — sigue el mismo patrón que cualquier otra fila con texto a la izquierda y control a la derecha en este proyecto, por ejemplo `room_rail.py`. No copies la línea de arriba tal cual: es un recordatorio de la reestructura, no código final.)*

Agrega el método para pintar el estado y la señal nueva en la clase:

```python
    refrescar_pedido = Signal(Path)

    def set_estado_de_entrega(self, estado: str | None, cuando_texto: str = "") -> None:
        from clasificador_video.entrega import EstadoEntrega

        self.pildora.hide()
        self.refrescar_button.hide()
        if estado == EstadoEntrega.CON_EDITOR:
            self.pildora.setText(f"●  Con el editor · {cuando_texto}")
            self.pildora.setProperty("tono", "esperando")
            self.pildora.show()
            self.refrescar_button.show()
        elif estado == EstadoEntrega.EDITOR_CONTESTO:
            self.pildora.setText(f"✓  El editor ya contestó · {cuando_texto}")
            self.pildora.setProperty("tono", "contesto")
            self.pildora.show()
        self.pildora.style().unpolish(self.pildora)
        self.pildora.style().polish(self.pildora)
```

- [ ] **Step 3: Test de la píldora**

```python
def test_fila_sin_entrega_no_muestra_pildora(qtbot):
    from clasificador_video.ui.pantalla_inicio import _FilaReciente

    fila = _FilaReciente(_entrada_de_prueba())
    qtbot.addWidget(fila)

    fila.set_estado_de_entrega(None)

    assert not fila.pildora.isVisible()
    assert not fila.refrescar_button.isVisible()


def test_fila_con_editor_muestra_pildora_y_refrescar(qtbot):
    from clasificador_video.entrega import EstadoEntrega
    from clasificador_video.ui.pantalla_inicio import _FilaReciente

    fila = _FilaReciente(_entrada_de_prueba())
    qtbot.addWidget(fila)

    fila.set_estado_de_entrega(EstadoEntrega.CON_EDITOR, "hace 2 días")

    assert fila.pildora.isVisible()
    assert fila.refrescar_button.isVisible()
    assert "Con el editor" in fila.pildora.text()


def test_fila_editor_contesto_no_muestra_refrescar(qtbot):
    from clasificador_video.entrega import EstadoEntrega
    from clasificador_video.ui.pantalla_inicio import _FilaReciente

    fila = _FilaReciente(_entrada_de_prueba())
    qtbot.addWidget(fila)

    fila.set_estado_de_entrega(EstadoEntrega.EDITOR_CONTESTO, "hace 3 horas")

    assert fila.pildora.isVisible()
    assert not fila.refrescar_button.isVisible()
```

(Revisa `tests/ui/test_pantalla_inicio.py` existente para copiar el helper `_entrada_de_prueba()` real, o el que haga sus veces — probablemente construye un objeto simple con `.ruta`, `.nombre`, `.disponible`, `.cuando`.)

- [ ] **Step 4: Correr y ajustar**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_inicio.py -v`
Expected: PASS

- [ ] **Step 5: `PantallaInicio.set_recientes` lee el estado de cada `.cvproj`**

```python
    def set_recientes(self, entradas: list) -> None:
        # ... el bucle existente que crea cada _FilaReciente, sin cambios
        # hasta aqui ...
        for entrada in entradas:
            fila = _FilaReciente(entrada, self.lista_host)
            fila.abrir_pedido.connect(self.abrir_pedido.emit)
            fila.quitar_pedido.connect(self.quitar_pedido.emit)
            fila.refrescar_pedido.connect(self.refrescar_pedido.emit)
            estado, cuando = self._estado_de_entrega_de(entrada)
            fila.set_estado_de_entrega(estado, cuando)
            self.lista.addWidget(fila)
            self.filas.append(fila)
        # ... resto sin cambios ...

    def _estado_de_entrega_de(self, entrada) -> tuple[str | None, str]:
        """Lee el `.cvproj` de esa entrada y devuelve su estado de
        entrega. Un proyecto que no se puede leer (disco desconectado,
        `entrada.disponible` en falso) no tiene estado que mostrar --
        no es un error, es lo mismo que "nunca se subió"."""
        if not entrada.disponible:
            return None, ""
        from clasificador_video import proyecto
        from clasificador_video.entrega import EstadoEntrega
        try:
            data = json.loads(entrada.ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, ""
        estado_obj = EstadoEntrega.de_dict(data.get("entrega"))
        if estado_obj is None:
            return None, ""
        return estado_obj.estado, _hace_cuanto(estado_obj.subido_en)
```

*(`_hace_cuanto` es una función de formato de fecha relativa -- "hace 2 días" -- que puede que ya exista en el proyecto para el campo `cuando` de `entrada`; búscala con `grep -rn "hace_cuanto\|def cuando" src/clasificador_video/` antes de escribir una nueva.)*

Agrega la señal nueva a la clase `PantallaInicio`:

```python
    refrescar_pedido = Signal(Path)
```

- [ ] **Step 6: Correr y confirmar**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_inicio.py -v`
Expected: PASS

- [ ] **Step 7: `MainWindow` conecta `refrescar_pedido` con `drive.revisar_cambios`**

En el sitio donde `MainWindow` ya conecta las señales de `PantallaInicio` (`grep -n "abrir_pedido.connect\|PantallaInicio(" src/clasificador_video/ui/main_window.py`):

```python
        self.pantalla_inicio.refrescar_pedido.connect(self._al_refrescar_entrega)
```

```python
    def _al_refrescar_entrega(self, ruta_proyecto: Path) -> None:
        """El ⟳ de una fila puntual: consulta Drive SOLO por ESE
        proyecto, nunca por todos -- spec de interfaz §4."""
        data = json.loads(ruta_proyecto.read_text(encoding="utf-8"))
        estado = EstadoEntrega.de_dict(data.get("entrega"))
        if estado is None or estado.drive_folder_id is None:
            return
        cliente = self._cliente_de_drive()
        resultado = drive.revisar_cambios(
            cliente, estado.drive_folder_id, estado.drive_prproj_modificado_en)
        if resultado.hay_cambios or resultado.tiene_material_nuevo:
            nuevo_estado = replace(estado, estado=EstadoEntrega.EDITOR_CONTESTO)
            data["entrega"] = nuevo_estado.to_dict()
            proyecto.guardar(ruta_proyecto, data)
            self._refrescar_pantalla_inicio()
```

- [ ] **Step 8: Test de integración simple con un cliente falso**

```python
def test_refrescar_actualiza_el_cvproj_cuando_hay_cambios(ventana, tmp_path, monkeypatch):
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    data = {"entrega": EstadoEntrega(
        estado=EstadoEntrega.CON_EDITOR, drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}
    ruta.write_text(json.dumps(data))

    class _ClienteFalso:
        def listar_en_carpeta(self, carpeta_id):
            class _A:
                name = "Casa Reforma.prproj"
                modified_time = "2026-09-18T12:00:00Z"
                mime_type = "video/mp4"
            return [_A()]

    monkeypatch.setattr(ventana, "_cliente_de_drive", lambda: _ClienteFalso())

    ventana._al_refrescar_entrega(ruta)

    guardado = json.loads(ruta.read_text())
    assert guardado["entrega"]["estado"] == EstadoEntrega.EDITOR_CONTESTO
```

- [ ] **Step 9: Correr y confirmar**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/ -k refrescar -v`
Expected: PASS

- [ ] **Step 10: Configuración: la carpeta raíz de Premiere y conectar Drive**

En `pantalla_config.py`, junto al bloque del modo económico, agrega una sección análoga a la de la llave (campo de texto + botón "Elegir…" que abre `QFileDialog.getExistingDirectory`, más un botón "Conectar Google Drive" que dispara `drive.cliente_autorizado` en un hilo aparte para no congelar la ventana mientras se abre el navegador del OAuth). Sigue el patrón exacto del bloque de la llave (líneas 45-99 de este mismo archivo): `QLabel` de estado + control + botón, con su propia señal hacia `MainWindow` (`carpeta_premiere_guardada = Signal(Path)`, `drive_conectado = Signal()`).

- [ ] **Step 11: Test de `pantalla_config.py`**

```python
def test_elegir_carpeta_premiere_emite_la_señal(config_screen, monkeypatch, tmp_path):
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path)))

    recibido = []
    config_screen.carpeta_premiere_guardada.connect(recibido.append)
    config_screen.carpeta_premiere_button.click()

    assert recibido == [tmp_path]
```

- [ ] **Step 12: Correr, ajustar, y correr la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS todo

- [ ] **Step 13: Verificación visual real de la pantalla de inicio**

Construye una `PantallaInicio` de prueba con 3 entradas (`sin_subir`/`None`, `con_editor`, `editor_contesto`), `grab()`, guarda el PNG en el scratchpad y mírala. Compara contra `lista-proyectos.html`.

- [ ] **Step 14: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
Agregar el estado de entrega a la pantalla de inicio y Configuración

Cada fila de "Tus proyectos" lee el .cvproj y muestra su píldora
("Con el editor" / "El editor ya contestó"), con un ⟳ que consulta
Drive solo para ese proyecto, nunca para todos. Configuración suma la
carpeta raíz de proyectos de Premiere y el botón para conectar Drive.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Qué queda fuera de este plan (a propósito)

- **Migrar o regenerar proxies viejos en 720p.** Decisión de la sesión de diseño de interfaz: no se toca nada de forma especial. Fuera de alcance aquí también.
- **Adobe Team Projects** y **leer el `.prproj` para adivinar cambios** — descartados en la spec original, §5.
- **Polling automático de Drive al abrir la app** — descartado explícitamente en la spec de interfaz, §4.
- **QSS de las píldoras y botones nuevos** (`entregaPill`, `recientePildora`, tonos `esperando`/`contesto`) — se agrega al hoja de estilos existente (`theme.py`) como parte de F5/F6, usando `PENDING_COLOR`/`CURRENT_COLOR`/`PICK_COLOR` de la paleta ya definida para los tonos ámbar/verde de las maquetas; no se detalla aquí letra por letra porque es exactamente el mismo patrón QSS que ya usa cada badge existente (`CARD_BADGE_TEXT`, etc.) — cópialo de ahí.
