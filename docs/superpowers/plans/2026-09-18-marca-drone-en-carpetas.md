# La marca [DRONE] en las carpetas de cuarto — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que un cuarto cuyos clips vienen TODOS de un bin de importación cuyo
nombre dice "dron" se marque `[DRONE]` en su carpeta de Premiere, después del
número, y que esa marca se agregue o se quite sola al reimportar — sin crear
carpetas duplicadas y sin tocar el color de cámara que ya existe.

**Architecture:** El dato nace del lado de la app (Python): por cada clip, si
el bin del que salió tiene "dron" en su nombre. Ese booleano viaja en el
manifiesto junto a cada clip, igual que ya viaja `camara`. Del lado del
plugin (JS), un módulo nuevo decide, cuarto por cuarto, si el 100% de sus
clips trae ese dato en verdadero, y arma el nombre final de la carpeta. La
comparación de identidad que ya usa el plugin para no duplicar carpetas al
reimportar (`esElMismoCuarto`) se extiende para ignorar también esta marca,
igual que ya ignora el número.

**Tech Stack:** Python (dataclasses, PySide6 solo para los tests de
`MainWindow`), JavaScript plano sin build (UXP), pytest, el corredor de
pruebas de node del plugin (`uxp-plugin/pruebas/correr.js`).

Spec: `docs/superpowers/specs/2026-09-18-marca-drone-en-carpetas-design.md`

---

## Antes de empezar

Todos los comandos de abajo asumen que estás parado en la raíz del repo:
`/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO`.

Los tests de Python de este plan usan Qt y tienen que correr con
`QT_QPA_PLATFORM=offscreen`, igual que el resto de la suite.

---

### Task 1: La detección pura — ¿el nombre de un bin dice "dron"?

**Files:**
- Create: `src/clasificador_video/marca_dron.py`
- Test: `tests/test_marca_dron.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_marca_dron.py
from clasificador_video.marca_dron import bin_dice_dron


def test_un_nombre_con_dron_cuenta():
    assert bin_dice_dron("Dron") is True


def test_un_nombre_con_drone_tambien_cuenta():
    """`dron` es substring de `drone` («**dron**e»), así que una sola regla
    cubre las dos formas de escribirlo."""
    assert bin_dice_dron("DRONE FINAL") is True


def test_no_distingue_mayusculas():
    assert bin_dice_dron("tarjeta dron 2") is True


def test_un_nombre_sin_la_palabra_no_cuenta():
    assert bin_dice_dron("Sony A") is False
    assert bin_dice_dron("Tarjeta 2") is False


def test_un_nombre_vacio_no_cuenta():
    assert bin_dice_dron("") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_marca_dron.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'clasificador_video.marca_dron'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/clasificador_video/marca_dron.py
"""Si el nombre de un bin de importacion dice que es del dron.

Vive aparte de `camaras.py` a proposito: ese modulo mira el nombre de los
ARCHIVOS y decide el COLOR del clip en Premiere. Este mira el nombre del BIN
DE IMPORTACION -- la tanda con la que Bruno arrastro el material, la misma
que se ve como encabezado en la hoja -- y solo sirve para decidir la marca
[DRONE] en la carpeta del cuarto en Premiere. Son dos señales distintas y no
se mezclan (spec 2026-09-18 §2).
"""
from __future__ import annotations

_PALABRA = "dron"


def bin_dice_dron(nombre: str) -> bool:
    """`dron` es substring de `drone` («**dron**e»), asi que una sola
    comparacion, sin distinguir mayusculas, cubre las dos formas de
    escribirlo. Mismo criterio que `_MARCA_DEL_DRON` en `camaras.py`: una
    palabra, buscada como substring, sin adivinar mas de la cuenta."""
    return _PALABRA in (nombre or "").lower()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_marca_dron.py -v`
Expected: PASS — 5 tests.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/marca_dron.py tests/test_marca_dron.py
git commit -m "$(cat <<'EOF'
Agregar deteccion de bin de dron por el nombre

Señal nueva y separada de camaras.py: si el nombre del bin de
importacion trae "dron" (cubre "drone" como substring), cuenta como
bin de dron. Solo la logica pura todavia, sin conectar a nada.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: El campo `bin_dron` en el manifiesto

**Files:**
- Modify: `src/clasificador_video/manifest.py:9-35`
- Modify: `tests/test_manifest.py:8-34`

- [ ] **Step 1: Write the failing test**

En `tests/test_manifest.py`, la función `_clip` no necesita cambiar (el campo
nuevo tiene default). Actualiza el test que compara el diccionario EXACTO —
hoy no incluye `bin_dron` y va a fallar por una llave de más en cuanto exista
el campo:

```python
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
        "camara": "sony",
        "bin_dron": False,
        "ruta_proxy": "/shooting/C0012S03.MP4",
    }
```

Agrega también un test dedicado, debajo de `test_clip_flag_por_defecto_es_none`:

```python
def test_clip_bin_dron_por_defecto_es_false():
    assert _clip().bin_dron is False


def test_clip_bin_dron_viaja_al_dict():
    assert _clip(bin_dron=True).to_dict()["bin_dron"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -v`
Expected: FAIL — `test_clip_to_dict_usa_las_llaves_exactas_del_manifest` por
la llave `bin_dron` que falta en el dict real, y
`test_clip_bin_dron_por_defecto_es_false` / `test_clip_bin_dron_viaja_al_dict`
con `TypeError: __init__() got an unexpected keyword argument 'bin_dron'`.

- [ ] **Step 3: Write minimal implementation**

En `src/clasificador_video/manifest.py`, agrega el campo al dataclass `Clip`
justo después de `camara` y antes de `ruta_proxy`:

```python
    # De que camara salio. Decide su ETIQUETA DE COLOR en Premiere -- la
    # traduccion camara→color vive del otro lado, en `label.js`, igual que
    # la de flag→carpeta. Aqui viaja el dato, no la presentacion.
    camara: str = "sony"
    # Si el BIN de importacion del que salio este clip tenia "dron" en su
    # nombre. Señal aparte de `camara` (esa mira el nombre del archivo, esta
    # el nombre del bin) y solo sirve para la marca [DRONE] de la carpeta de
    # su cuarto en Premiere. Ver `marca_dron.py` y
    # docs/superpowers/specs/2026-09-18-marca-drone-en-carpetas-design.md.
    bin_dron: bool = False
    ruta_proxy: Path | None = None
```

Y en `to_dict`, agrega la llave en el mismo orden:

```python
    def to_dict(self) -> dict:
        return {
            "orden": self.orden,
            "ruta": str(self.ruta),
            "categoria_path": self.categoria_path,
            "fps": self.fps,
            "in_frame": self.in_frame,
            "out_frame": self.out_frame,
            "flag": self.flag,
            "camara": self.camara,
            "bin_dron": self.bin_dron,
            "ruta_proxy": str(self.ruta_proxy) if self.ruta_proxy is not None else None,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -v`
Expected: PASS — todos los tests del archivo.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/manifest.py tests/test_manifest.py
git commit -m "$(cat <<'EOF'
Agregar bin_dron al Clip del manifiesto

Campo nuevo, con default False, que viaja junto a cada clip igual que
camara. Todavia nadie lo llena con un dato real -- eso es el
siguiente paso.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Conectarlo en `MainWindow` — del bin al manifiesto exportado

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py:36` (import)
- Modify: `src/clasificador_video/ui/main_window.py:4913-4946` (`escribir_manifest` y vecinos)
- Test: `tests/ui/test_main_window_dron.py` (nuevo)

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_main_window_dron.py
"""Si el bin de importación dice "dron", de punta a punta: desde el nombre
del bin hasta el campo `bin_dron` del manifiesto."""
import json
from pathlib import Path

import pytest

from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow

# Mismo arreglo que test_main_window_camaras.py: sin FakeMpv cada ventana
# abre un mpv de verdad con sus hilos, y sin _probe_falso estos tests lanzan
# ffprobe contra rutas inventadas.
from test_main_window_bins import FakeMpv, _probe_falso


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


@pytest.fixture
def ventana(qtbot):
    window = MainWindow(project_name="Casa Jardin", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    window._probe_clip = _probe_falso
    qtbot.addWidget(window)
    return window


def test_un_bin_que_dice_dron_marca_sus_clips(ventana, tmp_path):
    ventana.load_clips([_clip(0, "/dron/C0001.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0],
                         rutas=[c.ruta for c in ventana.clips])
    ventana.clips[0].categoria_path = ["Aerea"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["bin_dron"] is True


def test_un_bin_que_no_dice_dron_no_marca(ventana, tmp_path):
    ventana.load_clips([_clip(0, "/cam/C0001.MP4")])
    ventana.bins.agregar("Cámara", Path("/cam"), [0],
                         rutas=[c.ruta for c in ventana.clips])
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["bin_dron"] is False


def test_un_clip_sin_bin_no_cuenta_como_dron(ventana, tmp_path):
    """Un clip suelto no tiene bin del que sacar el dato -- tiene que salir
    con el respaldo (False), igual que un clip suelto sale sony en camara."""
    ventana.load_clips([_clip(0, "/cam/C0001.MP4")])
    ventana.clips[0].categoria_path = ["Cocina"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["bin_dron"] is False


def test_renombrar_el_bin_para_que_diga_dron_tambien_cuenta(ventana, tmp_path):
    """El nombre se revisa al exportar, no al crear el bin -- si Bruno lo
    renombra despues para que diga "dron", eso tiene que verse en el
    manifiesto siguiente."""
    ventana.load_clips([_clip(0, "/cam/C0001.MP4")])
    ventana.bins.agregar("Tarjeta 2", Path("/cam"), [0],
                         rutas=[c.ruta for c in ventana.clips])
    ventana.bins.renombrar("Tarjeta 2", "Dron 2")
    ventana.clips[0].categoria_path = ["Aerea"]

    destino = tmp_path / "m.json"
    ventana.escribir_manifest(destino)

    assert json.loads(destino.read_text())["clips"][0]["bin_dron"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_dron.py -v`
Expected: FAIL — los cuatro tests, todos con `bin_dron` saliendo `False`
donde se esperaba `True` (el campo existe desde la Task 2, pero nadie lo
llena todavía con el dato real).

- [ ] **Step 3: Write minimal implementation**

En `src/clasificador_video/ui/main_window.py`, agrega el import junto al de
`camaras` (línea 36):

```python
from clasificador_video.camaras import SONY
from clasificador_video.marca_dron import bin_dice_dron
```

Y en `escribir_manifest` (línea 4913), agrega el dato nuevo junto al de
`camaras`:

```python
    def escribir_manifest(self, destino: Path) -> None:
        """Arma el manifiesto y lo escribe. Sin dialogos: es la parte
        probable, y `_on_export_manifest` es la que pregunta.

        Aqui van las tres transformaciones de exportacion, en fila: el rango
        en orden, la camara del bin y si el bin dice "dron". Las tres viven
        en la exportacion y no en la sesion, que guarda lo que el editor
        marco.

        Hubo una cuarta --la subcarpeta del estado, «Picks»/«Rejects»/«Sin
        marcar» dentro de cada cuarto-- y se fue el 2026-09-08: el estado lo
        dicen las marcas del nombre en Premiere, y una carpeta que dice lo
        mismo que una marca solo esconde el clip.
        """
        camaras = self._camaras_por_clip()
        dron = self._bin_dron_por_clip()
        manifest = Manifest(
            proyecto=self.project_name,
            orientacion=self.orientacion_del_proyecto(),
            clips=[_con_el_rango_en_orden(
                replace(c, camara=camaras.get(i, SONY), bin_dron=dron.get(i, False)))
                for i, c in enumerate(self.clips)],
            guia=self._guia_para_el_manifest(),
            crear_secuencias=True,
        )
        manifest.write_json(destino)

    def _camaras_por_clip(self) -> dict[int, str]:
        """De indice de clip a camara, de una sola pasada por los bins.

        Un clip sin bin no aparece aqui y sale con el respaldo: no hay de
        donde sacarle una camara, y llegar sin campo seria peor que llegar
        con la de la camara que Bruno usa casi siempre.
        """
        return {i: self.bins.camara_de(nombre) or SONY
                for i, nombre in self.bins.mapa_por_clip().items()}

    def _bin_dron_por_clip(self) -> dict[int, bool]:
        """De indice de clip a si su bin de importacion dice "dron" en el
        nombre, de una sola pasada por los bins -- mismo patron que
        `_camaras_por_clip`.

        Un clip sin bin no aparece aqui y sale con el respaldo (False): no
        hay bin del que sacar una respuesta, y spec 2026-09-18 §3 pide
        justo eso -- un clip suelto no cuenta como dron.
        """
        return {i: bin_dice_dron(nombre)
                for i, nombre in self.bins.mapa_por_clip().items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_dron.py -v`
Expected: PASS — los cuatro tests.

- [ ] **Step 5: Run the full Python suite before moving to the plugin**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS completo (sin `--ignore`, ver `CLAUDE.md`).

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_dron.py
git commit -m "$(cat <<'EOF'
Llenar bin_dron al exportar el manifiesto

Mismo patron que _camaras_por_clip: una pasada por los bins, y un
clip sin bin sale con el respaldo (False). Con esto la parte de
Python del pedido de Bruno queda completa -- lo que falta es que el
plugin arme el nombre de la carpeta con este dato.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: El módulo de la marca, del lado del plugin

**Files:**
- Create: `uxp-plugin/js/marcaDron.js`
- Test: `uxp-plugin/pruebas/marcaDron.pruebas.js`
- Modify: `uxp-plugin/pruebas/correr.js:35-40,53-59`

- [ ] **Step 1: Write the failing test**

```javascript
// uxp-plugin/pruebas/marcaDron.pruebas.js
// Los casos de la marca [DRONE] en el nombre del cuarto. Logica pura: corren
// con `node uxp-plugin/pruebas/correr.js`.
module.exports = function (ctx) {
  return [
    {
      nombre: "conMarcaDron pone la marca al inicio",
      fn: () => {
        const r = ctx.conMarcaDron("03. Cocina", true);
        return { ok: r === "[DRONE] 03. Cocina", detalle: r };
      },
    },
    {
      nombre: "conMarcaDron sin dron no pone nada",
      fn: () => {
        const r = ctx.conMarcaDron("03. Cocina", false);
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
    {
      nombre: "conMarcaDron es idempotente",
      fn: () => {
        const una = ctx.conMarcaDron("03. Cocina", true);
        const dos = ctx.conMarcaDron(una, true);
        return { ok: dos === "[DRONE] 03. Cocina", detalle: dos };
      },
    },
    {
      nombre: "conMarcaDron quita la marca si ya no aplica",
      fn: () => {
        const r = ctx.conMarcaDron("[DRONE] 03. Cocina", false);
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
    {
      nombre: "sinMarcaDron no toca un nombre sin marca",
      fn: () => {
        const r = ctx.sinMarcaDron("03. Cocina");
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
    {
      nombre: "cuartoEsDeDron: todos los clips de un bin de dron",
      fn: () => {
        const clips = [
          { categoria_path: ["Aerea"], bin_dron: true },
          { categoria_path: ["Aerea"], bin_dron: true },
        ];
        const r = ctx.cuartoEsDeDron(clips, "Aerea");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "cuartoEsDeDron: un solo clip que no es de dron lo tumba",
      fn: () => {
        const clips = [
          { categoria_path: ["Aerea"], bin_dron: true },
          { categoria_path: ["Aerea"], bin_dron: false },
        ];
        const r = ctx.cuartoEsDeDron(clips, "Aerea");
        return { ok: r === false, detalle: String(r) };
      },
    },
    {
      nombre: "cuartoEsDeDron: solo mira los clips de ESE cuarto",
      fn: () => {
        const clips = [
          { categoria_path: ["Aerea"], bin_dron: true },
          { categoria_path: ["Cocina"], bin_dron: false },
        ];
        const r = ctx.cuartoEsDeDron(clips, "Aerea");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "cuartoEsDeDron: un cuarto vacio no cuenta como dron",
      fn: () => {
        const r = ctx.cuartoEsDeDron([], "Aerea");
        return { ok: r === false, detalle: String(r) };
      },
    },
    {
      nombre: "nombreDelCuartoConMarca junta numero y marca",
      fn: () => {
        const clips = [{ categoria_path: ["Aerea"], bin_dron: true }];
        const r = ctx.nombreDelCuartoConMarca("02. Aerea", "Aerea", clips);
        return { ok: r === "[DRONE] 02. Aerea", detalle: r };
      },
    },
    {
      nombre: "nombreDelCuartoConMarca sin dron deja el nombre igual",
      fn: () => {
        const clips = [{ categoria_path: ["Cocina"], bin_dron: false }];
        const r = ctx.nombreDelCuartoConMarca("03. Cocina", "Cocina", clips);
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
  ];
};
```

Regístralo en `uxp-plugin/pruebas/correr.js`. Primero agrega el archivo a la
lista `ARCHIVOS` (línea 35), con un comentario que explique por qué entra:

```javascript
// Aqui entraban tambien `ordenSugerido.js`, `llave.js` y
// `cuartosDelProyecto.js`. Se fueron el 2026-09-14 con la pestana que
// preguntaba: la guia se arma en Clipify y sus casos viven ahora en
// `tests/test_guia.py`.
//
// `marcaDron.js` es logica pura entera: pone y quita la marca [DRONE] del
// nombre de un cuarto y decide si un cuarto cuenta como dron. Va antes que
// `numeroDeCuarto.js` porque `esElMismoCuarto` usa su `sinMarcaDron`.
const ARCHIVOS = [
  "js/marcaDron.js",
  "js/estructura.js",
  "js/numeroDeCuarto.js",
  "js/avance.js",
  "js/secuencia.js",
];
```

Y súmalo a la lista de `casos` (línea 53):

```javascript
const pruebas = require("./numeroDeCuarto.pruebas.js");
const casos = [].concat(
  require("./marcaDron.pruebas.js")(contexto),
  pruebas(contexto),
  pruebas.carpetas(contexto),
  require("./avance.pruebas.js")(contexto)
  , require("./secuencia.pruebas.js")(contexto)
);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: falla al arrancar con
`Falta js/marcaDron.js -- no se puede correr nada.` (el `ARCHIVOS.forEach`
revisa que cada archivo exista antes de cargar nada).

- [ ] **Step 3: Write minimal implementation**

```javascript
// uxp-plugin/js/marcaDron.js
// La marca "[DRONE] " en el nombre de la carpeta de un cuarto en Premiere.
//
// POR QUE ES UNA SEÑAL APARTE DE LA CAMARA (`label.js`): el color del clip
// ya dice de que camara salio, mirando el nombre del ARCHIVO. Esto mira el
// nombre del BIN DE IMPORTACION -- la tanda con la que Bruno arrastro el
// material -- y solo sirve para esta marca. Las dos conviven sin tocarse.
//
// Logica pura: se prueba con `node uxp-plugin/pruebas/correr.js`.
//
// Spec: docs/superpowers/specs/2026-09-18-marca-drone-en-carpetas-design.md

const MARCA_DRONE = "[DRONE] ";

// Le pone o le quita la marca segun `esDron`. Idempotente: aplicarla dos
// veces con el mismo `esDron` deja el nombre igual -- primero se limpia lo
// que ya hubiera, y despues se pone lo que toca. Mismo patron que
// `nombre.js` con las marcas de estado de los clips.
function conMarcaDron(nombre, esDron) {
  const limpio = sinMarcaDron(nombre);
  return esDron ? MARCA_DRONE + limpio : limpio;
}

// Quita SOLO la marca que este modulo pone, y solo si esta al inicio. Un
// nombre que Bruno haya escrito el mismo no es nuestro y no se toca.
function sinMarcaDron(nombre) {
  const s = String(nombre || "");
  return s.indexOf(MARCA_DRONE) === 0 ? s.slice(MARCA_DRONE.length) : s;
}

// Si TODOS los clips de ese cuarto vinieron de un bin cuyo nombre dice
// "dron" (`bin_dron` en el manifiesto, ver marca_dron.py del lado de la
// app). Bruno pidio la regla estricta a proposito (spec §3): un solo clip
// que no venga de un bin de dron y el cuarto entero se queda sin marca.
//
// Un cuarto vacio -- sin clips de ese nombre en ESTE manifiesto -- no
// cuenta: no hay de donde sacar una respuesta.
function cuartoEsDeDron(clipsDelManifest, nombreDeCuarto) {
  const delCuarto = (clipsDelManifest || []).filter(
    (c) => c && c.categoria_path && c.categoria_path[0] === nombreDeCuarto
  );
  if (!delCuarto.length) return false;
  return delCuarto.every((c) => c.bin_dron === true);
}

// Junta las tres cosas de arriba para quien arma el camino de un clip
// (`processManifest.js`): el nombre YA numerado del cuarto (lo que da
// `conNumero`/`caminoDelClip`), el nombre SIN numero que identifica al
// cuarto en el manifiesto (`categoryPath[0]`), y la lista completa de
// clips para decidir si aplica la marca.
function nombreDelCuartoConMarca(nombreConNumero, nombreDeCuartoSinNumero, clipsDelManifest) {
  return conMarcaDron(
    nombreConNumero,
    cuartoEsDeDron(clipsDelManifest, nombreDeCuartoSinNumero)
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todas las pruebas `OK`, incluidas las 11 nuevas de
`marcaDron.pruebas.js`. El resumen final dice `0 fallidas`.

- [ ] **Step 5: Commit**

```bash
git add uxp-plugin/js/marcaDron.js uxp-plugin/pruebas/marcaDron.pruebas.js uxp-plugin/pruebas/correr.js
git commit -m "$(cat <<'EOF'
Agregar el modulo de la marca [DRONE] del lado del plugin

Logica pura: ponerla/quitarla del nombre de un cuarto, decidir si un
cuarto cuenta como dron (todos sus clips, sin excepcion) y armar el
nombre final numero+marca+nombre. Todavia no esta conectado a
processManifest.js ni al index.html.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Que reimportar no duplique la carpeta

**Files:**
- Modify: `uxp-plugin/js/numeroDeCuarto.js:30-37`
- Modify: `uxp-plugin/pruebas/numeroDeCuarto.pruebas.js:49-57`

Esta es la parte que evita el bug de la familia del 2026-08-22 (dos carpetas
para el mismo cuarto): `esElMismoCuarto` compara nombres ignorando el
número, y ahora también tiene que ignorar la marca `[DRONE]` — si no, un
cuarto que pasó de `03. Cocina` a `[DRONE] 03. Cocina` entre dos
importaciones se leería como un cuarto distinto y Premiere crearía una
segunda carpeta.

- [ ] **Step 1: Write the failing test**

En `uxp-plugin/pruebas/numeroDeCuarto.pruebas.js`, agrega estos dos casos
justo después del bloque `"Cocina y Comedor no son el mismo cuarto"` (antes
del caso de los acentos, línea ~71):

```javascript
    {
      // spec 2026-09-18 §5: la marca [DRONE] es presentacion del plugin,
      // igual que el numero -- puede aparecer o desaparecer entre dos
      // importaciones sin que el cuarto sea otro.
      nombre: "esElMismoCuarto ignora la marca [DRONE]",
      fn: () => {
        const r = ctx.esElMismoCuarto("[DRONE] 02. Aerea", "04. Aerea");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "esElMismoCuarto ignora la marca aunque solo un lado la tenga",
      fn: () => {
        const r = ctx.esElMismoCuarto("[DRONE] Aerea", "Aerea");
        return { ok: r === true, detalle: String(r) };
      },
    },
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: FALLO en los dos casos nuevos (`esElMismoCuarto` hoy no conoce la
marca, así que compara `"[DRONE] 02. Aerea"` contra `"Aerea"` tal cual y da
`false`).

- [ ] **Step 3: Write minimal implementation**

En `uxp-plugin/js/numeroDeCuarto.js`, modifica `esElMismoCuarto`:

```javascript
// Si dos nombres de carpeta son el mismo cuarto, tengan el numero que
// tengan Y la marca [DRONE] que tengan (marcaDron.js, spec 2026-09-18 §5):
// las dos son presentacion que el plugin le pone encima del nombre, y las
// dos pueden cambiar de una pasada a otra sin que el cuarto sea otro.
//
// Se compara por IGUALDAD EXACTA despues de quitar las dos: nada de
// minusculas ni quitar acentos. «Recamara 1» y «Recámara 1» son dos cuartos
// distintos, igual que en la revision de la lista.
function esElMismoCuarto(unNombre, otroNombre) {
  return sinMarcaDron(sinNumero(unNombre)) === sinMarcaDron(sinNumero(otroNombre));
}
```

(`sinMarcaDron` viene de `marcaDron.js`, que ahora se carga antes que este
archivo — ver Task 6 para el orden en `index.html`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todas `OK`, `0 fallidas`.

- [ ] **Step 5: Commit**

```bash
git add uxp-plugin/js/numeroDeCuarto.js uxp-plugin/pruebas/numeroDeCuarto.pruebas.js
git commit -m "$(cat <<'EOF'
Que esElMismoCuarto tambien ignore la marca [DRONE]

Sin esto, un cuarto que gana o pierde la marca entre dos
importaciones se leeria como un cuarto distinto y Premiere le crearia
una segunda carpeta -- la misma familia de bug del 2026-08-22.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Conectar la marca al importar de verdad

**Files:**
- Modify: `uxp-plugin/index.html:169` (orden de `<script>`)
- Modify: `uxp-plugin/js/processManifest.js:52-58`

- [ ] **Step 1: Cargar `marcaDron.js` antes que `numeroDeCuarto.js`**

En `uxp-plugin/index.html`, reemplaza:

```html
<!-- Antes que `bins.js` y `estructura.js`, que lo usan. -->
<script src="js/numeroDeCuarto.js"></script>
```

por:

```html
<!-- Antes que numeroDeCuarto.js, que usa su sinMarcaDron. -->
<script src="js/marcaDron.js"></script>
<!-- Antes que `bins.js` y `estructura.js`, que lo usan. -->
<script src="js/numeroDeCuarto.js"></script>
```

- [ ] **Step 2: Usar la marca al armar el camino del clip**

En `uxp-plugin/js/processManifest.js`, dentro del `try` del `for` principal,
reemplaza:

```javascript
      const camino = caminoDelClip(categoryPath, ordenDeLaGuia);
      const carpetaDelCuarto = await resolverCuarto(
        project, carpetaDeClips, camino[1]);
```

por:

```javascript
      const camino = caminoDelClip(categoryPath, ordenDeLaGuia);
      // camino[1] ya trae el numero (o no, sin guia). Aqui se le suma la
      // marca [DRONE] si TODOS los clips de este cuarto, en ESTE
      // manifiesto, vinieron de un bin que dice "dron" -- ver
      // marcaDron.js y spec 2026-09-18.
      camino[1] = nombreDelCuartoConMarca(camino[1], categoryPath[0], manifest.clips);
      const carpetaDelCuarto = await resolverCuarto(
        project, carpetaDeClips, camino[1]);
```

El resto del bucle sigue igual: `targetFolder`, `importOrReuseClip`,
`applyCameraLabel`, etc. no cambian. El `logToPanel("OK: " + ... + camino.join(" > "))`
que ya existe más abajo ahora muestra el nombre CON la marca, porque
`camino[1]` quedó reescrito — no hace falta tocar esa línea.

- [ ] **Step 3: Verificación manual — no hay forma de correr esto sin Premiere**

Este paso no tiene test automatizado: `processManifest.js` llama
`require("premierepro")` y a `resolverCuarto`, que necesita un proyecto de
Premiere real (por eso no está en la lista `ARCHIVOS` de
`uxp-plugin/pruebas/correr.js`, ver el comentario al tope de ese archivo).
Antes de dar por terminada esta tarea:

1. Arma un manifiesto de prueba a mano (o expórtalo desde la app) con al
   menos:
   - Un cuarto con TODOS sus clips en un bin llamado `"Dron"`.
   - Un cuarto con clips mezclados: alguno de un bin `"Dron"` y alguno de un
     bin `"Cámara"`.
   - Un cuarto normal, sin ningún bin que diga "dron".
2. Importa ese manifiesto en un proyecto de Premiere de prueba con el
   plugin.
3. En el panel de proyecto, confirma con los ojos:
   - El cuarto 100% dron se ve `NN. [DRONE] <nombre>`.
   - El cuarto mezclado se ve `NN. <nombre>`, sin marca.
   - El cuarto normal se ve igual que siempre.
4. Reimporta el MISMO manifiesto una segunda vez. Confirma que no aparece
   ninguna carpeta duplicada (ni `[DRONE] ... ` al lado de `...` sin
   marca).
5. Cambia a mano, en el manifiesto de prueba, el cuarto mezclado para que
   ahora sea 100% dron (o al revés) y vuelve a importar. Confirma que la
   MISMA carpeta gana o pierde la marca — no se crea una carpeta nueva.

Si algún paso no se comporta así, no sigas: es una señal de que
`esElMismoCuarto` o `nombreDelCuartoConMarca` tienen un caso que los tests
de node no cubrieron, y hay que volver a la Task 4 o 5 antes de continuar.

- [ ] **Step 4: Commit**

```bash
git add uxp-plugin/index.html uxp-plugin/js/processManifest.js
git commit -m "$(cat <<'EOF'
Conectar la marca [DRONE] al importar en Premiere

processManifest.js arma el nombre del cuarto con
nombreDelCuartoConMarca antes de resolverlo, y marcaDron.js se carga
antes que numeroDeCuarto.js en index.html. Verificado a mano contra
Premiere real: un cuarto 100% dron se marca, uno mezclado no, y
reimportar no duplica carpetas.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Corrida final completa

**Files:** ninguno — solo verificación.

- [ ] **Step 1: Suite de Python completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS completo, sin `--ignore` (ver `CLAUDE.md`).

- [ ] **Step 2: Pruebas de node del plugin**

Run: `node uxp-plugin/pruebas/correr.js`
Expected: todas `OK`, `0 fallidas`.

- [ ] **Step 3: Repasar `git status`**

Run: `git status`
Expected: árbol limpio — todo lo de este plan ya se commiteó tarea por
tarea. Si aparece algo suelto, es señal de que un paso anterior no se
commiteó; revisa antes de dar el trabajo por terminado.
