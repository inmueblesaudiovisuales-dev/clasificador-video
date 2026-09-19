# Vista de proyectos activos en Drive — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar una pestaña "En edición externa" a la pantalla de inicio que
liste los proyectos con una entrega activa en Drive (esperando al editor, ya
contestó, o en revisión) y deje "Traer de vuelta" y "Ya entregado" sin abrir
el proyecto.

**Architecture:** Un estado nuevo `EN_REVISION` en `EstadoEntrega` (traer de
vuelta deja de limpiar la entrega; ahora la deja "en revisión" hasta que
Bruno marca "Ya entregado"). Dos piezas de lógica pura se extraen para que
`PantallaInicio`/`Coordinador` puedan repetir lo que `MainWindow` ya hace sin
tener el proyecto abierto: `bins.raiz_del_proyecto` (ya existía como método
privado de `MainWindow`) y `proyecto.raiz_de_assets_de` (la misma cuenta,
pero leyendo el `.cvproj` del disco). El resto es UI: una pestaña nueva en
`PantallaInicio` (sigue sin QMessageBox — solo señales) y los métodos nuevos
del `Coordinador` en `app.py` que sí abren los diálogos de confirmación y
lanzan el trabajo de Drive en segundo plano, igual que ya hace `MainWindow`.

**Tech Stack:** Python, PySide6 (Qt), pytest + pytest-qt, `QT_QPA_PLATFORM=offscreen`.

---

## Antes de empezar

Todas las pruebas se corren así, desde la raíz del repo:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Corre la suite completa (no hay archivos a ignorar) después de cada tarea
para confirmar que nada se rompió, además de los tests puntuales que pide
cada paso.

---

### Task 1: `EstadoEntrega` gana el estado `EN_REVISION`

**Files:**
- Modify: `src/clasificador_video/entrega.py`
- Test: `tests/test_entrega.py`

- [ ] **Step 1: Escribe la prueba que falla**

Agrega al final de `tests/test_entrega.py`:

```python
def test_en_revision_es_un_estado_posible():
    assert EstadoEntrega.EN_REVISION == "en_revision"


def test_en_revision_ida_y_vuelta_por_dict():
    original = EstadoEntrega(
        estado=EstadoEntrega.EN_REVISION,
        subido_en="2026-09-16T10:00:00",
        prproj_local="/x/Casa Reforma.prproj",
        drive_folder_id="abc123",
    )

    de_vuelta = EstadoEntrega.de_dict(original.to_dict())

    assert de_vuelta == original
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_entrega.py -q`
Expected: FAIL en `test_en_revision_es_un_estado_posible` con
`AttributeError: EN_REVISION`.

- [ ] **Step 3: Agrega la constante**

En `src/clasificador_video/entrega.py`, dentro de `EstadoEntrega`, junto a
las otras tres constantes:

```python
    SIN_SUBIR = "sin_subir"
    CON_EDITOR = "con_editor"
    EDITOR_CONTESTO = "editor_contesto"
    # Traer de vuelta ya NO limpia la entrega (spec 2026-09-19): deja al
    # proyecto aqui, esperando que Bruno decida si sube de nuevo o marca
    # "Ya entregado". Antes de este estado, "Traer de vuelta" ponia
    # `self._entrega = None` -- ver MainWindow._on_drive_traida_lista.
    EN_REVISION = "en_revision"
```

También actualiza el comentario de cabecera del módulo (líneas 7-15) para
que diga los CUATRO estados en vez de tres:

```python
Cuatro estados nada mas, en el orden en que pasan:

- `SIN_SUBIR` -- nunca se subio nada (o es un proyecto de antes de esta
  funcion: no hay diferencia).
- `CON_EDITOR` -- ya se subio; no se sabe si el editor contesto porque
  esa pregunta es siempre a peticion de Bruno (nunca automatica al abrir
  la app -- spec de interfaz, S4).
- `EDITOR_CONTESTO` -- Bruno pidio revisar (el (r) de la lista, o el
  dialogo de "Traer de vuelta") y Drive tenia algo nuevo.
- `EN_REVISION` -- Bruno ya trajo el corte del editor y lo esta
  revisando. Si sube una version nueva vuelve a `CON_EDITOR`; cuando el
  cliente aprueba, Bruno marca "Ya entregado" y la entrega se limpia
  (spec 2026-09-19).
```

- [ ] **Step 4: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_entrega.py -q`
Expected: PASS (todas).

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/entrega.py tests/test_entrega.py
git commit -m "$(cat <<'EOF'
Agregar el estado EN_REVISION a la entrega

Traer de vuelta va a dejar de limpiar la entrega por completo: el
proyecto se queda "activo" hasta que Bruno marca Ya entregado a mano.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `entrega.cerrar_en_archivo` — cerrar sin tocar Drive

**Files:**
- Modify: `src/clasificador_video/entrega.py`
- Test: `tests/test_entrega.py`

Esto es lo que hace el botón "Ya entregado": limpia la entrega guardada en
un `.cvproj`, sin abrir el proyecto y sin tocar la red.

- [ ] **Step 1: Escribe la prueba que falla**

Agrega a `tests/test_entrega.py`:

```python
def test_cerrar_en_archivo_limpia_la_entrega(tmp_path):
    import json
    from clasificador_video.entrega import cerrar_en_archivo

    ruta = tmp_path / "Casa Reforma.cvproj"
    ruta.write_text(json.dumps({
        "proyecto": "Casa Reforma",
        "entrega": EstadoEntrega(EstadoEntrega.CON_EDITOR,
                                 drive_folder_id="folder-x").to_dict(),
    }))

    cerrado = cerrar_en_archivo(ruta)

    assert cerrado is True
    guardado = json.loads(ruta.read_text())
    assert guardado["entrega"] is None
    assert guardado["proyecto"] == "Casa Reforma"


def test_cerrar_en_archivo_sin_entrega_no_hace_nada(tmp_path):
    import json
    from clasificador_video.entrega import cerrar_en_archivo

    ruta = tmp_path / "Casa Reforma.cvproj"
    ruta.write_text(json.dumps({"proyecto": "Casa Reforma"}))
    antes = ruta.read_text()

    cerrado = cerrar_en_archivo(ruta)

    assert cerrado is False
    assert ruta.read_text() == antes


def test_cerrar_en_archivo_ilegible_no_revienta(tmp_path):
    from clasificador_video.entrega import cerrar_en_archivo

    ruta = tmp_path / "no-existe.cvproj"

    assert cerrar_en_archivo(ruta) is False
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_entrega.py -q`
Expected: FAIL con `ImportError: cannot import name 'cerrar_en_archivo'`.

- [ ] **Step 3: Implementa la función**

Al final de `src/clasificador_video/entrega.py`:

```python
def cerrar_en_archivo(ruta_cvproj: Path) -> bool:
    """El botón "Ya entregado": limpia la entrega guardada en un `.cvproj`
    sin abrir el proyecto y SIN tocar Drive -- a diferencia de "Traer de
    vuelta", esto es solo una marca de organización de Bruno (spec
    2026-09-19 §6). `False` si no había nada que limpiar o el archivo no
    se pudo leer.
    """
    import json

    from clasificador_video import proyecto

    try:
        data = json.loads(ruta_cvproj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not data.get("entrega"):
        return False
    data["entrega"] = None
    proyecto.guardar(ruta_cvproj, data)
    return True
```

Necesita `from pathlib import Path` al tope del archivo -- ya está
importado indirectamente por `Path` en las anotaciones de `EstadoEntrega`;
confirma que exista `from pathlib import Path` en los imports de
`entrega.py` (si no está, agrégalo junto a `from dataclasses import
dataclass`).

- [ ] **Step 4: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_entrega.py -q`
Expected: PASS (todas).

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/entrega.py tests/test_entrega.py
git commit -m "$(cat <<'EOF'
Agregar entrega.cerrar_en_archivo para el botón Ya entregado

Cierra el pendiente de una entrega sin tocar Drive -- distinto de
Traer de vuelta, que sí baja archivos.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `bins.raiz_del_proyecto` — la cuenta, ya no atada a `MainWindow`

**Files:**
- Modify: `src/clasificador_video/bins.py`
- Modify: `src/clasificador_video/ui/main_window.py:2977-2990`
- Test: `tests/test_bins.py`

`MainWindow._raiz_del_proyecto` calcula la carpeta raíz del proyecto (la que
contiene `ASSETS VIDEO`) a partir de `self.bins`, un `BinTree` en memoria.
Esa cuenta no usa nada de Qt ni de la ventana — se extrae a una función pura
en `bins.py`, y `MainWindow` pasa a delegarle.

- [ ] **Step 1: Escribe la prueba que falla**

Agrega a `tests/test_bins.py`:

```python
def test_raiz_del_proyecto_sube_hasta_la_carpeta_que_contiene_assets_video():
    from clasificador_video.bins import raiz_del_proyecto

    arbol = BinTree()
    arbol.agregar(
        "Sony", Path("/Volumes/SSD/IAV-2609/01. ASSETS VIDEO/02. CLIP/Sony"),
        [0],
    )

    assert raiz_del_proyecto(arbol) == Path("/Volumes/SSD/IAV-2609")


def test_raiz_del_proyecto_sin_bins_es_none():
    from clasificador_video.bins import raiz_del_proyecto

    assert raiz_del_proyecto(BinTree()) is None


def test_raiz_del_proyecto_sin_assets_video_es_none():
    from clasificador_video.bins import raiz_del_proyecto

    arbol = BinTree()
    arbol.agregar("Sony", Path("/Volumes/SSD/Material suelto"), [0])

    assert raiz_del_proyecto(arbol) is None
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q`
Expected: FAIL con `ImportError: cannot import name 'raiz_del_proyecto'`.

- [ ] **Step 3: Extrae la función a `bins.py`**

Agrega en `src/clasificador_video/bins.py`, junto a `raiz_comun_de` (cerca
de la línea 46-59):

```python
def raiz_del_proyecto(arbol: "BinTree") -> Path | None:
    """La raíz del proyecto de Bruno (la carpeta que contiene
    `ASSETS VIDEO`), a partir del origen de cualquier bin.

    La usa el "Traer de vuelta": ahí es donde tiene que caer el
    "material nuevo" que baje de Drive (`mapa_de_categorias_de_material_nuevo`,
    en `drive.py`, da rutas relativas a esta raíz). `None` si no hay bins
    o su material no cuelga de esa estructura -- ahí "Traer de vuelta"
    solo baja el `.prproj`, sin material nuevo.
    """
    for nombre in arbol.nombres():
        origen = arbol.origen_de(nombre)
        if origen is None:
            continue
        for ancestro in [origen, *origen.parents]:
            if ancestro.name.lower().endswith("assets video"):
                return ancestro.parent
    return None
```

- [ ] **Step 4: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_bins.py -q`
Expected: PASS (todas).

- [ ] **Step 5: `MainWindow._raiz_del_proyecto` delega en la nueva función**

En `src/clasificador_video/ui/main_window.py`, reemplaza el cuerpo de
`_raiz_del_proyecto` (líneas 2977-2990):

```python
    def _raiz_del_proyecto(self) -> Path | None:
        """La raíz del proyecto que contiene las carpetas de assets.

        Se deduce del origen de cualquier bin. Si no hay bins o su material
        no cuelga de esa estructura, no hay una raíz confiable.
        """
        return bins_module.raiz_del_proyecto(self.bins)
```

Y en el import de `bins` al tope del archivo (línea 37), cambia:

```python
from clasificador_video.bins import BinTree, raiz_comun_de
```

por:

```python
from clasificador_video import bins as bins_module
from clasificador_video.bins import BinTree, raiz_comun_de
```

(Se importa el módulo completo, aparte de los nombres sueltos que ya se
usaban, porque `bins_module.raiz_del_proyecto` necesita el módulo, no la
clase.)

- [ ] **Step 6: Corre toda la suite de `main_window` y confirma que nada se rompió**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_entrega.py tests/ui/test_main_window.py -q`
Expected: PASS (todas — en particular
`test_traer_de_vuelta_baja_material_nuevo_desde_la_raiz_del_proyecto`, que
monkeypatchea `_raiz_del_proyecto` directamente y no debería notar el
cambio).

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/bins.py src/clasificador_video/ui/main_window.py tests/test_bins.py
git commit -m "$(cat <<'EOF'
Extraer bins.raiz_del_proyecto de MainWindow

Pura, sin Qt: la necesita también la vista de proyectos activos, que
calcula "Traer de vuelta" sin tener la ventana abierta.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `proyecto.raiz_de_assets_de` — la misma cuenta, leída del disco

**Files:**
- Modify: `src/clasificador_video/proyecto.py`
- Test: `tests/test_proyecto.py`

Igual que la Task 3, pero a partir del diccionario crudo de un `.cvproj`
(los `bins` guardados), no de un `BinTree` en memoria. Es lo que necesita
`Coordinador` para "Traer de vuelta" sin abrir el proyecto.

- [ ] **Step 1: Escribe la prueba que falla**

Agrega a `tests/test_proyecto.py`:

```python
def test_raiz_de_assets_de_lee_los_bins_del_documento():
    from clasificador_video.proyecto import raiz_de_assets_de

    data = {"bins": [
        {"nombre": "Sony", "clips": [0], "camara": "sony",
         "origen": "/Volumes/SSD/IAV-2609/01. ASSETS VIDEO/02. CLIP/Sony"},
    ]}

    assert raiz_de_assets_de(data) == Path("/Volumes/SSD/IAV-2609")


def test_raiz_de_assets_de_sin_bins_es_none():
    from clasificador_video.proyecto import raiz_de_assets_de

    assert raiz_de_assets_de({}) is None
    assert raiz_de_assets_de({"bins": []}) is None
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -q`
Expected: FAIL con `ImportError: cannot import name 'raiz_de_assets_de'`.

- [ ] **Step 3: Implementa la función**

Al final de `src/clasificador_video/proyecto.py`:

```python
def raiz_de_assets_de(data: dict) -> Path | None:
    """La raíz del proyecto (la carpeta que contiene `ASSETS VIDEO`),
    leída de un `.cvproj` sin abrir la ventana.

    Mismo cálculo que `bins.raiz_del_proyecto`, pero a partir de los bins
    tal como quedaron guardados (`data["bins"]`), no de un `BinTree` ya
    armado en memoria. La usa "Traer de vuelta" desde la lista de
    proyectos activos (spec 2026-09-19 §6).
    """
    from clasificador_video.bins import BinTree, raiz_del_proyecto

    arbol = BinTree.from_list(data.get("bins") or [])
    return raiz_del_proyecto(arbol)
```

- [ ] **Step 4: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -q`
Expected: PASS (todas).

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proyecto.py tests/test_proyecto.py
git commit -m "$(cat <<'EOF'
Agregar proyecto.raiz_de_assets_de para traer de vuelta sin abrir

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `drive.revisar_y_persistir` devuelve el resultado completo

**Files:**
- Modify: `src/clasificador_video/drive.py:122-145`
- Modify: `src/clasificador_video/app.py` (uso en `_al_refrescar`)
- Test: `tests/test_drive.py`
- Test: `tests/test_app.py`

Hoy `revisar_y_persistir` devuelve solo `bool` ("¿guardé algo nuevo?"). La
vista de activos necesita el `ResultadoDeRevision` completo para armar el
texto del diálogo de "Traer de vuelta" (cuántos cambios hay, si hay material
nuevo) — así que la función pasa a devolver `ResultadoDeRevision | None`
(`None` cuando no hay una entrega con la que comparar). Quien solo quería el
booleano de antes revisa `resultado is not None and (resultado.hay_cambios
or resultado.tiene_material_nuevo)`.

- [ ] **Step 1: Actualiza las pruebas existentes (van a fallar hasta el paso 3)**

En `tests/test_drive.py`, reemplaza las cuatro pruebas de
`revisar_y_persistir` (líneas 286-352) por:

```python
def test_revisar_y_persistir_marca_al_editor_cuando_drive_tiene_cambios(tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    ruta.write_text(json.dumps({"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR,
        drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}))
    cliente = _ClienteFalso([
        _ArchivoFalso("prproj", "Casa Reforma.prproj", "2026-09-18T12:00:00Z"),
    ])

    resultado = drive.revisar_y_persistir(ruta, cliente)

    assert resultado.hay_cambios is True
    assert json.loads(ruta.read_text())["entrega"]["estado"] == EstadoEntrega.EDITOR_CONTESTO
    assert cliente.coloreadas == [("folder-x", drive.COLOR_YA_REGRESO)]


def test_revisar_y_persistir_sin_cambios_no_toca_el_color(tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    ruta.write_text(json.dumps({"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR,
        drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}))
    cliente = _ClienteFalso([
        _ArchivoFalso("prproj", "Casa Reforma.prproj", "2026-09-16T10:00:00Z"),
    ])

    resultado = drive.revisar_y_persistir(ruta, cliente)

    assert resultado.hay_cambios is False
    assert cliente.coloreadas == []


def test_revisar_y_persistir_sin_cambios_no_toca_el_proyecto(tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    data = {"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR,
        drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}
    ruta.write_text(json.dumps(data))
    antes = ruta.read_text()
    cliente = _ClienteFalso([
        _ArchivoFalso("prproj", "Casa Reforma.prproj", "2026-09-16T10:00:00Z"),
    ])

    drive.revisar_y_persistir(ruta, cliente)

    assert ruta.read_text() == antes


def test_revisar_y_persistir_sin_entrega_devuelve_none(tmp_path):
    ruta = tmp_path / "Casa Reforma.cvproj"
    ruta.write_text(json.dumps({"proyecto": "Casa Reforma"}))

    resultado = drive.revisar_y_persistir(ruta, _ClienteFalso())

    assert resultado is None
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_drive.py -q`
Expected: FAIL en las cuatro pruebas de arriba (`AttributeError:
'bool' object has no attribute 'hay_cambios'`, o `resultado is None` siendo
en realidad `False`).

- [ ] **Step 3: Cambia el cuerpo de `revisar_y_persistir`**

Reemplaza en `src/clasificador_video/drive.py` (líneas 122-145):

```python
def revisar_y_persistir(ruta_cvproj: Path, cliente) -> ResultadoDeRevision | None:
    """Revisa Drive y guarda el estado de respuesta del editor si cambió.

    Devuelve el `ResultadoDeRevision` completo -- aunque no haya
    cambios -- para que quien llama (el ⟳ de una fila, o "Traer de
    vuelta" desde la lista de activos) pueda armar su propio mensaje sin
    volver a preguntarle a Drive. `None` solo cuando no hay una entrega
    con la que comparar (archivo ilegible, sin `entrega`, o sin
    `drive_folder_id`).
    """
    import json
    from dataclasses import replace

    from clasificador_video import proyecto
    from clasificador_video.entrega import EstadoEntrega

    try:
        data = json.loads(ruta_cvproj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    estado = EstadoEntrega.de_dict(data.get("entrega"))
    if estado is None or estado.drive_folder_id is None:
        return None
    resultado = revisar_cambios(
        cliente, estado.drive_folder_id, estado.drive_prproj_modificado_en)
    if resultado.hay_cambios or resultado.tiene_material_nuevo:
        cliente.colorear_carpeta(estado.drive_folder_id, COLOR_YA_REGRESO)
        data["entrega"] = replace(
            estado, estado=EstadoEntrega.EDITOR_CONTESTO).to_dict()
        proyecto.guardar(ruta_cvproj, data)
    return resultado
```

- [ ] **Step 4: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_drive.py -q`
Expected: PASS (todas).

- [ ] **Step 5: Actualiza el único llamador, `Coordinador._al_refrescar`**

En `src/clasificador_video/app.py`, dentro de `_al_refrescar` (línea 508),
cambia:

```python
        if drive.revisar_y_persistir(ruta, cliente):
            self._refrescar()
```

por:

```python
        resultado = drive.revisar_y_persistir(ruta, cliente)
        if resultado is not None and (resultado.hay_cambios or resultado.tiene_material_nuevo):
            self._refrescar()
```

- [ ] **Step 6: Actualiza la prueba de `test_app.py` que monkeypatchea el booleano**

En `tests/test_app.py`, dentro de
`test_refrescar_pedido_actualiza_la_lista_si_drive_encontro_cambios`
(línea 451), reemplaza:

```python
    monkeypatch.setattr(
        drive, "revisar_y_persistir",
        lambda ruta_recibida, cliente_recibido: (
            ruta_recibida == ruta and cliente_recibido is cliente),
    )
```

por:

```python
    def _revisar_y_persistir(ruta_recibida, cliente_recibido):
        assert ruta_recibida == ruta
        assert cliente_recibido is cliente
        return drive.ResultadoDeRevision(
            hay_cambios=True, prproj_modificado_en="x", tiene_material_nuevo=False)

    monkeypatch.setattr(drive, "revisar_y_persistir", _revisar_y_persistir)
```

- [ ] **Step 7: Corre `test_app.py` completo y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -q`
Expected: PASS (todas).

- [ ] **Step 8: Commit**

```bash
git add src/clasificador_video/drive.py src/clasificador_video/app.py tests/test_drive.py tests/test_app.py
git commit -m "$(cat <<'EOF'
Devolver el ResultadoDeRevision completo desde revisar_y_persistir

Antes solo decía si guardó algo. La vista de proyectos activos
necesita el resultado completo para armar el diálogo de "Traer de
vuelta" sin volver a consultar Drive.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `drive.mensaje_confirmar_traida` — el texto del diálogo, reusable

**Files:**
- Modify: `src/clasificador_video/drive.py`
- Modify: `src/clasificador_video/ui/main_window.py:3147-3164`
- Test: `tests/test_drive.py`

El texto del cuadro "Traer de vuelta" (hay cambios / no hay cambios) hoy
vive solo dentro de `MainWindow._confirmar_traer_de_vuelta`, armando un
`QMessageBox` directamente. Se extrae la parte de TEXTO (sin Qt) para que la
vista de activos arme el mismo cuadro sin duplicar la redacción.

- [ ] **Step 1: Escribe la prueba que falla**

Agrega a `tests/test_drive.py`:

```python
def test_mensaje_confirmar_traida_con_cambios_en_el_prproj():
    resultado = drive.ResultadoDeRevision(
        hay_cambios=True, prproj_modificado_en="x", tiene_material_nuevo=False)

    mensaje = drive.mensaje_confirmar_traida(resultado)

    assert mensaje.texto == "Se encontró algo nuevo en Drive."
    assert "El .prproj cambió." in mensaje.informativo
    assert "material nuevo" not in mensaje.informativo
    assert mensaje.texto_boton == "Traer de vuelta"


def test_mensaje_confirmar_traida_con_material_nuevo():
    resultado = drive.ResultadoDeRevision(
        hay_cambios=False, prproj_modificado_en="x", tiene_material_nuevo=True)

    mensaje = drive.mensaje_confirmar_traida(resultado)

    assert "El .prproj no ha cambiado." in mensaje.informativo
    assert 'Hay contenido en "material nuevo/".' in mensaje.informativo
    assert mensaje.texto_boton == "Traer de vuelta"


def test_mensaje_confirmar_traida_sin_nada_nuevo():
    resultado = drive.ResultadoDeRevision(
        hay_cambios=False, prproj_modificado_en="x", tiene_material_nuevo=False)

    mensaje = drive.mensaje_confirmar_traida(resultado)

    assert mensaje.texto == (
        "No parece que el editor haya subido nada todavía. "
        "¿Seguro que quieres continuar?"
    )
    assert mensaje.texto_boton == "Traer de todas formas"
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_drive.py -q`
Expected: FAIL con `AttributeError: module 'clasificador_video.drive' has
no attribute 'mensaje_confirmar_traida'`.

- [ ] **Step 3: Implementa el dataclass y la función**

Agrega en `src/clasificador_video/drive.py`, después de la clase
`ResultadoDeRevision` (después de la línea 89):

```python
@dataclass(frozen=True)
class MensajeConfirmarTraida:
    texto: str
    informativo: str
    texto_boton: str


def mensaje_confirmar_traida(resultado: ResultadoDeRevision) -> MensajeConfirmarTraida:
    """El texto del diálogo de "Traer de vuelta", sin Qt -- lo arma tanto
    `MainWindow` (con el proyecto abierto) como la lista de proyectos
    activos (sin abrirlo), y las dos tienen que decir lo mismo."""
    if resultado.hay_cambios or resultado.tiene_material_nuevo:
        texto_cambio = "El .prproj cambió." if resultado.hay_cambios else "El .prproj no ha cambiado."
        if resultado.tiene_material_nuevo:
            texto_cambio += ' Hay contenido en "material nuevo/".'
        return MensajeConfirmarTraida(
            texto="Se encontró algo nuevo en Drive.",
            informativo=texto_cambio + "\n\nLos proxies no se vuelven a bajar -- ya los tienes.",
            texto_boton="Traer de vuelta",
        )
    return MensajeConfirmarTraida(
        texto="No parece que el editor haya subido nada todavía. "
              "¿Seguro que quieres continuar?",
        informativo="",
        texto_boton="Traer de todas formas",
    )
```

- [ ] **Step 4: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_drive.py -q`
Expected: PASS (todas).

- [ ] **Step 5: `MainWindow._confirmar_traer_de_vuelta` usa el mensaje nuevo**

Reemplaza en `src/clasificador_video/ui/main_window.py` (líneas 3147-3164):

```python
    def _confirmar_traer_de_vuelta(self, resultado) -> bool:
        mensaje = drive.mensaje_confirmar_traida(resultado)
        cuadro = QMessageBox(self)
        cuadro.setWindowTitle(f"Traer de vuelta — {self.project_name}")
        cuadro.setText(mensaje.texto)
        if mensaje.informativo:
            cuadro.setInformativeText(mensaje.informativo)
        traer = cuadro.addButton(mensaje.texto_boton, QMessageBox.ButtonRole.AcceptRole)
        cuadro.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        cuadro.setDefaultButton(traer)
        cuadro.exec()
        return cuadro.clickedButton() is traer
```

- [ ] **Step 6: Corre la prueba existente de `main_window` y confirma que sigue pasando**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_entrega.py -q`
Expected: PASS, incluida
`test_confirmar_traer_de_vuelta_sin_cambios_no_bloquea`.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/drive.py src/clasificador_video/ui/main_window.py tests/test_drive.py
git commit -m "$(cat <<'EOF'
Extraer el texto del diálogo "Traer de vuelta" a drive.py

Sin Qt, para que la lista de proyectos activos arme el mismo cuadro
sin repetir la redacción.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Traer de vuelta deja al proyecto "en revisión" (dentro de `MainWindow`)

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py:3174-3182`
- Modify: `src/clasificador_video/ui/title_bar.py:157-179`
- Test: `tests/ui/test_main_window_entrega.py`
- Test: `tests/ui/test_title_bar.py`

Hoy `_on_drive_traida_lista` limpia la entrega entera. Pasa a dejarla en
`EN_REVISION`, conservando `drive_folder_id`/`prproj_local` por si Bruno
sube de nuevo. La barra superior necesita saber pintar ese estado: píldora
"En revisión", sin botón "Traer de vuelta" (nada nuevo que traer), con
"Subir de nuevo" disponible.

- [ ] **Step 1: Escribe las pruebas que fallan, para `title_bar.py`**

Agrega a `tests/ui/test_title_bar.py` (usa el mismo patrón que ya exista ahí
para `CON_EDITOR`/`EDITOR_CONTESTO` — revisa el archivo si el nombre del
fixture de la barra es distinto de `barra`):

```python
def test_en_revision_muestra_su_pildora_sin_boton_de_traer(qtbot):
    from clasificador_video.entrega import EstadoEntrega
    from clasificador_video.ui.title_bar import TitleBar

    barra = TitleBar()
    qtbot.addWidget(barra)

    barra.set_estado_de_entrega(EstadoEntrega.EN_REVISION, "hace 1 hora")

    assert barra.entrega_pill.isVisible()
    assert "En revisión" in barra.entrega_pill.text()
    assert not barra.traer_button.isVisible()
    assert barra.subir_button.text() == "Subir de nuevo"
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_title_bar.py -q`
Expected: FAIL — la píldora se queda vacía/oculta porque
`set_estado_de_entrega` no conoce `EN_REVISION` todavía.

- [ ] **Step 3: `TitleBar.set_estado_de_entrega` conoce `EN_REVISION`**

En `src/clasificador_video/ui/title_bar.py`, agrega un tercer `elif` dentro
de `set_estado_de_entrega` (después del bloque de `EDITOR_CONTESTO`, línea
176):

```python
        elif estado == EstadoEntrega.EN_REVISION:
            self.subir_button.setText("Subir de nuevo")
            self.entrega_pill.setText(f"◐  En revisión · {cuando_texto}")
            self.entrega_pill.setProperty("tono", "revision")
            self.entrega_pill.show()
```

(El `traer_button` ya queda oculto por las dos líneas de reseteo al tope
del método — `self.traer_button.hide()` — así que no hace falta tocarlo
aquí: solo NO se le llama `.show()`, a diferencia de los otros dos casos.)

- [ ] **Step 4: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_title_bar.py -q`
Expected: PASS (todas).

- [ ] **Step 5: Escribe la prueba que falla, para `main_window.py`**

Agrega a `tests/ui/test_main_window_entrega.py`:

```python
def test_traer_de_vuelta_deja_el_proyecto_en_revision(ventana, tmp_path, monkeypatch):
    from clasificador_video.entrega import EstadoEntrega

    ventana._entrega = EstadoEntrega(
        EstadoEntrega.CON_EDITOR,
        prproj_local=str(tmp_path / "Casa Reforma.prproj"),
        drive_folder_id="folder-x",
    )
    monkeypatch.setattr(ventana, "_autosave", lambda: None)

    ventana._on_drive_traida_lista("")

    assert ventana._entrega.estado == EstadoEntrega.EN_REVISION
    assert ventana._entrega.drive_folder_id == "folder-x"
    assert "En revisión" in ventana.title_bar.entrega_pill.text()
```

- [ ] **Step 6: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_entrega.py -q`
Expected: FAIL — `ventana._entrega` queda en `None`.

- [ ] **Step 7: Cambia `_on_drive_traida_lista`**

Reemplaza en `src/clasificador_video/ui/main_window.py` (líneas 3174-3182):

```python
    def _on_drive_traida_lista(self, error: str) -> None:
        if error:
            QMessageBox.warning(
                self, "Traer de vuelta", f"No se pudo traer de Drive: {error}")
            return
        from dataclasses import replace
        from clasificador_video.entrega import EstadoEntrega

        if self._entrega is not None:
            self._entrega = replace(self._entrega, estado=EstadoEntrega.EN_REVISION)
        self.title_bar.set_estado_de_entrega(
            self._entrega.estado if self._entrega else None,
            self._entrega.subido_en if self._entrega else "")
        self._autosave()
```

- [ ] **Step 8: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_entrega.py -q`
Expected: PASS (todas, incluida `test_error_de_traida_muestra_un_aviso`,
que no debería notar el cambio).

- [ ] **Step 9: Corre la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS (todas).

- [ ] **Step 10: Commit**

```bash
git add src/clasificador_video/ui/main_window.py src/clasificador_video/ui/title_bar.py tests/ui/test_main_window_entrega.py tests/ui/test_title_bar.py
git commit -m "$(cat <<'EOF'
Traer de vuelta deja al proyecto "en revisión" en vez de cerrarlo

Antes borraba la entrega entera. Ahora se queda activo hasta que
Bruno decide subir de nuevo o marcar "Ya entregado" (spec
2026-09-19).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Colores nuevos en `theme.py` — la píldora "En revisión" y la pestaña

**Files:**
- Modify: `src/clasificador_video/ui/theme.py`

- [ ] **Step 1: Agrega la variante de tono "revisión" a la píldora**

En `src/clasificador_video/ui/theme.py`, junto a la regla ya existente
(cerca de la línea 663):

```python
    QLabel#recientePildora[tono="contesto"] {{ color: {PICK_COLOR}; }}
    QLabel#recientePildora[tono="revision"] {{ color: {TRIM_COLOR}; }}
```

- [ ] **Step 2: Agrega el estilo de los botones de acción de la fila activa**

Junto a la regla de `recienteRefrescar` (cerca de la línea 664-667),
extiende el selector para que los botones nuevos de la fila activa
compartan el mismo tratamiento visual sin CSS repetido:

```python
    QPushButton#recienteRefrescar, QPushButton#activaTraer,
    QPushButton#activaYaEntregado {{
        background-color: {BG_SURFACE_2}; border: 1px solid {LINE}; border-radius: 8px;
        color: {TEXT}; padding: 2px 6px;
    }}
    QPushButton#activaTraer, QPushButton#activaYaEntregado {{
        padding: 4px 10px;
    }}
```

- [ ] **Step 3: Agrega el estilo de la fila activa, reusando `filaReciente`**

Junto a las reglas de `filaReciente` (cerca de la línea 1387-1399), extiende
el selector de la fila (no el de "perdido", que la fila activa nunca usa):

```python
    QPushButton#filaReciente, QPushButton#filaActiva {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_LG}px;
        padding: 0px;
        text-align: left;
    }}
    QPushButton#filaReciente:hover, QPushButton#filaActiva:hover {{
        background-color: {BG_SURFACE_2};
        border-color: {CURRENT_COLOR};
    }}
```

(Esto REEMPLAZA las dos reglas ya existentes de `filaReciente` con la misma
regla extendida a `filaActiva` — no las dupliques, edítalas en su lugar.)

- [ ] **Step 4: Agrega el switch de pestañas de la pantalla de inicio**

Junto al bloque de `modeSwitch` (cerca de la línea 524-534), un bloque
análogo para la pestaña de inicio — mismo criterio: caja opaca porque no
flota sobre video, fuente de interfaz:

```python
    QWidget#inicioSwitch {{
        background-color: {BG_SURFACE_1};
        border: 1px solid {LINE};
        border-radius: {RADIUS_MD}px;
    }}
    QWidget#inicioSwitch QPushButton#segmentedButton {{
        font-family: {SANS_FONT};
        font-size: {FONT_SMALL}px;
        font-weight: 550;
        padding: 6px 12px;
    }}
```

- [ ] **Step 5: Verifica que la suite sigue pasando**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS (todas — este paso no cambia comportamiento, solo QSS).

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/theme.py
git commit -m "$(cat <<'EOF'
Agregar los colores de la vista de proyectos activos en Drive

Píldora "en revisión" en TRIM_COLOR, botones de acción de la fila
activa y el switch de pestañas de la pantalla de inicio.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: `_FilaActiva` — la fila de la pestaña "En edición externa"

**Files:**
- Modify: `src/clasificador_video/ui/pantalla_inicio.py`
- Test: `tests/ui/test_pantalla_inicio.py`

Una clase nueva, separada de `_FilaReciente` (que no cambia): muestra
nombre, cuándo se subió, la píldora de estado y los botones que le tocan
según el estado (spec 2026-09-19 §5).

- [ ] **Step 1: Escribe las pruebas que fallan**

Agrega a `tests/ui/test_pantalla_inicio.py`:

```python
def test_fila_activa_con_editor_muestra_los_tres_controles(qtbot):
    from clasificador_video.entrega import EstadoEntrega
    from clasificador_video.ui.pantalla_inicio import _FilaActiva

    fila = _FilaActiva(_entrada_de_prueba(), EstadoEntrega.CON_EDITOR, "hace 2 días")
    qtbot.addWidget(fila)
    fila.show()

    assert "Con el editor" in fila.pildora.text()
    assert fila.refrescar_button.isVisible()
    assert fila.traer_button.isVisible()
    assert fila.ya_entregado_button.isVisible()


def test_fila_activa_editor_contesto_tambien_muestra_los_tres(qtbot):
    from clasificador_video.entrega import EstadoEntrega
    from clasificador_video.ui.pantalla_inicio import _FilaActiva

    fila = _FilaActiva(_entrada_de_prueba(), EstadoEntrega.EDITOR_CONTESTO, "hace 3 horas")
    qtbot.addWidget(fila)
    fila.show()

    assert "El editor ya contestó" in fila.pildora.text()
    assert fila.refrescar_button.isVisible()
    assert fila.traer_button.isVisible()
    assert fila.ya_entregado_button.isVisible()


def test_fila_activa_en_revision_solo_muestra_ya_entregado(qtbot):
    from clasificador_video.entrega import EstadoEntrega
    from clasificador_video.ui.pantalla_inicio import _FilaActiva

    fila = _FilaActiva(_entrada_de_prueba(), EstadoEntrega.EN_REVISION, "hace 1 hora")
    qtbot.addWidget(fila)
    fila.show()

    assert "En revisión" in fila.pildora.text()
    assert not fila.refrescar_button.isVisible()
    assert not fila.traer_button.isVisible()
    assert fila.ya_entregado_button.isVisible()


def test_fila_activa_emite_sus_señales_con_la_ruta(qtbot):
    from clasificador_video.entrega import EstadoEntrega
    from clasificador_video.ui.pantalla_inicio import _FilaActiva

    entrada = _entrada_de_prueba()
    fila = _FilaActiva(entrada, EstadoEntrega.CON_EDITOR, "hace 2 días")
    qtbot.addWidget(fila)
    fila.show()
    traidos, entregados, refrescados, abiertos = [], [], [], []
    fila.traer_de_vuelta_pedido.connect(traidos.append)
    fila.ya_entregado_pedido.connect(entregados.append)
    fila.refrescar_pedido.connect(refrescados.append)
    fila.abrir_pedido.connect(abiertos.append)

    fila.traer_button.click()
    fila.ya_entregado_button.click()
    fila.refrescar_button.click()
    fila.click()

    assert traidos == [entrada.ruta]
    assert entregados == [entrada.ruta]
    assert refrescados == [entrada.ruta]
    assert abiertos == [entrada.ruta]
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_inicio.py -q`
Expected: FAIL con `ImportError: cannot import name '_FilaActiva'`.

- [ ] **Step 3: Implementa `_FilaActiva`**

Agrega en `src/clasificador_video/ui/pantalla_inicio.py`, después de la
clase `_FilaReciente` (después de la línea 182, antes de `class
PantallaInicio`):

```python
class _FilaActiva(QPushButton):
    """Una fila de la pestaña "En edición externa": el mismo proyecto que
    ya aparece en "Tus proyectos", pero con las acciones de la entrega a
    la vista -- sin tener que abrirlo primero (spec 2026-09-19 §5).

    Solo se construye para proyectos disponibles con una entrega activa:
    a diferencia de `_FilaReciente`, no conoce el estado "perdido".
    """

    abrir_pedido = Signal(Path)
    refrescar_pedido = Signal(Path)
    traer_de_vuelta_pedido = Signal(Path)
    ya_entregado_pedido = Signal(Path)

    def __init__(self, entrada, estado: str, cuando_texto: str, parent=None):
        super().__init__(parent)
        from clasificador_video.entrega import EstadoEntrega

        self.setObjectName("filaActiva")
        self.entrada = entrada
        self.setFixedHeight(FILA_ALTO)
        self.setCursor(Qt.PointingHandCursor)

        fila_horizontal = QHBoxLayout(self)
        fila_horizontal.setContentsMargins(12, 8, 12, 8)
        fila_horizontal.setSpacing(8)
        caja_host = QWidget()
        caja = QVBoxLayout(caja_host)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(2)
        self.nombre = _etiqueta("recienteNombre", apagado=False)
        self.nombre.setText(entrada.nombre)
        self.detalle = _etiqueta("recienteDetalle", apagado=False,
                                 modo=Qt.TextElideMode.ElideMiddle)
        self.detalle.setText(f"subido {cuando_texto}  ·  {entrada.ruta.parent}")
        caja.addWidget(self.nombre)
        caja.addWidget(self.detalle)

        self.pildora = QLabel("")
        self.pildora.setObjectName("recientePildora")
        es_en_revision = estado == EstadoEntrega.EN_REVISION
        if estado == EstadoEntrega.CON_EDITOR:
            self.pildora.setText("●  Con el editor")
            self.pildora.setProperty("tono", "esperando")
        elif estado == EstadoEntrega.EDITOR_CONTESTO:
            self.pildora.setText("✓  El editor ya contestó")
            self.pildora.setProperty("tono", "contesto")
        else:
            self.pildora.setText("◐  En revisión")
            self.pildora.setProperty("tono", "revision")

        self.refrescar_button = QPushButton("⟳")
        self.refrescar_button.setObjectName("recienteRefrescar")
        self.refrescar_button.setToolTip("Revisar si el editor ya contestó")
        self.refrescar_button.setVisible(not es_en_revision)
        self.refrescar_button.clicked.connect(
            lambda: self.refrescar_pedido.emit(self.entrada.ruta))

        self.traer_button = QPushButton("Traer de vuelta")
        self.traer_button.setObjectName("activaTraer")
        self.traer_button.setVisible(not es_en_revision)
        self.traer_button.clicked.connect(
            lambda: self.traer_de_vuelta_pedido.emit(self.entrada.ruta))

        self.ya_entregado_button = QPushButton("Ya entregado")
        self.ya_entregado_button.setObjectName("activaYaEntregado")
        self.ya_entregado_button.clicked.connect(
            lambda: self.ya_entregado_pedido.emit(self.entrada.ruta))

        fila_horizontal.addWidget(caja_host, 1)
        fila_horizontal.addWidget(self.pildora)
        fila_horizontal.addWidget(self.refrescar_button)
        fila_horizontal.addWidget(self.traer_button)
        fila_horizontal.addWidget(self.ya_entregado_button)
        self.setToolTip(str(entrada.ruta))
        self.clicked.connect(lambda: self.abrir_pedido.emit(self.entrada.ruta))
```

- [ ] **Step 4: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_inicio.py -q`
Expected: PASS (todas).

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/pantalla_inicio.py tests/ui/test_pantalla_inicio.py
git commit -m "$(cat <<'EOF'
Agregar _FilaActiva, la fila de la pestaña "En edición externa"

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: La pestaña en `PantallaInicio`

**Files:**
- Modify: `src/clasificador_video/ui/pantalla_inicio.py`
- Test: `tests/ui/test_pantalla_inicio.py`

El interruptor "Tus proyectos" / "En edición externa", el filtro de
`set_recientes` que arma la lista de activos, el empty state, y las señales
nuevas que llegan hasta `Coordinador`.

- [ ] **Step 1: Escribe las pruebas que fallan**

Agrega a `tests/ui/test_pantalla_inicio.py`. Usa proyectos reales en disco
(`tmp_path`) porque `_estado_de_entrega_de` lee el `.cvproj`:

```python
def _proyecto_con_entrega(tmp_path, nombre, estado, cuando="2026-09-17T10:00:00"):
    import json
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / f"{nombre}.cvproj"
    ruta.write_text(json.dumps({
        "proyecto": nombre,
        "entrega": EstadoEntrega(estado, subido_en=cuando).to_dict(),
    }))
    return Reciente(ruta, nombre, "2026-09-17 10:00")


def test_la_pestaña_de_activos_empieza_escondida_y_el_switch_en_tus_proyectos(qtbot):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)

    assert pantalla.switch.current() == "Tus proyectos"
    assert pantalla.activos_host.isHidden()
    assert pantalla.activos_vacio.isHidden()


def test_solo_los_proyectos_con_entrega_activa_entran_a_la_pestaña(qtbot, tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    sin_entrega = tmp_path / "Sin entrega.cvproj"
    sin_entrega.write_text("{}")
    pantalla.set_recientes([
        Reciente(sin_entrega, "Sin entrega", "2026-09-17 10:00"),
        _proyecto_con_entrega(tmp_path, "Con editor", EstadoEntrega.CON_EDITOR),
        _proyecto_con_entrega(tmp_path, "En revision", EstadoEntrega.EN_REVISION),
    ])

    assert pantalla.nombres_activos_visibles() == ["Con editor", "En revision"]


def test_cambiar_a_la_pestaña_de_activos_muestra_sus_filas(qtbot, tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([
        _proyecto_con_entrega(tmp_path, "Con editor", EstadoEntrega.CON_EDITOR),
    ])

    pantalla.switch.buttons[1].click()

    assert pantalla.activos_host.isVisible()
    assert pantalla.lista_host.isHidden()


def test_sin_activos_la_pestaña_muestra_el_empty_state(qtbot, tmp_path):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    sin_entrega = tmp_path / "Sin entrega.cvproj"
    sin_entrega.write_text("{}")
    pantalla.set_recientes([Reciente(sin_entrega, "Sin entrega", "2026-09-17 10:00")])

    pantalla.switch.buttons[1].click()

    assert pantalla.activos_vacio.isVisible()
    assert pantalla.activos_host.isHidden()


def test_las_señales_de_la_fila_activa_llegan_a_la_pantalla(qtbot, tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    entrada = _proyecto_con_entrega(tmp_path, "Con editor", EstadoEntrega.CON_EDITOR)
    pantalla.set_recientes([entrada])
    pantalla.switch.buttons[1].click()
    traidos, entregados = [], []
    pantalla.traer_de_vuelta_pedido.connect(traidos.append)
    pantalla.ya_entregado_pedido.connect(entregados.append)

    pantalla.filas_activas[0].traer_button.click()
    pantalla.filas_activas[0].ya_entregado_button.click()

    assert traidos == [entrada.ruta]
    assert entregados == [entrada.ruta]


def test_volver_a_llenar_la_lista_no_deja_filas_activas_viejas(qtbot, tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([
        _proyecto_con_entrega(tmp_path, "Uno", EstadoEntrega.CON_EDITOR),
    ])
    pantalla.set_recientes([
        _proyecto_con_entrega(tmp_path, "Dos", EstadoEntrega.CON_EDITOR),
    ])

    assert pantalla.nombres_activos_visibles() == ["Dos"]
    assert len(pantalla.activos_host.findChildren(type(pantalla.filas_activas[0]))) == 1
```

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_inicio.py -q`
Expected: FAIL con `AttributeError: 'PantallaInicio' object has no
attribute 'switch'` (u otro atributo que aún no existe).

- [ ] **Step 3: Agrega los imports que hacen falta**

En `src/clasificador_video/ui/pantalla_inicio.py`, agrega
`from clasificador_video.ui.segmented import SegmentedControl` al bloque de
imports (junto a `from clasificador_video.ui.text import ElidedLabel`).

- [ ] **Step 4: Construye el switch y los widgets de la pestaña de activos**

En `PantallaInicio.__init__`, después de construir `self.aviso` y antes de
`self.lista_host` (después de la línea 220, antes de la línea 222), inserta:

```python
        self.switch = SegmentedControl(
            ["Tus proyectos", "En edición externa"], object_name="inicioSwitch"
        )
        self.switch.selected.connect(self._al_cambiar_pestaña)
        raiz.addWidget(self.switch)
```

Después de construir `self.vacio` (después de la línea 243, antes de
`raiz.addStretch(1)` en la línea 245), inserta los widgets de la pestaña de
activos:

```python
        self.activos_host = QWidget()
        self.activos_lista = QVBoxLayout(self.activos_host)
        self.activos_lista.setContentsMargins(0, 0, 0, 0)
        self.activos_lista.setSpacing(6)
        raiz.addWidget(self.activos_host)

        self.activos_vacio = QWidget()
        self.activos_vacio.setObjectName("inicioVacio")
        activos_vacio_caja = QVBoxLayout(self.activos_vacio)
        activos_vacio_caja.setContentsMargins(0, 10, 0, 10)
        activos_vacio_caja.setSpacing(4)
        activos_vacio_titulo = QLabel("No tienes proyectos en edición externa")
        activos_vacio_titulo.setObjectName("inicioVacioTitulo")
        activos_vacio_hint = QLabel(
            "Los que subas a Drive para un editor van a aparecer aquí."
        )
        activos_vacio_hint.setObjectName("inicioVacioHint")
        activos_vacio_caja.addWidget(activos_vacio_titulo)
        activos_vacio_caja.addWidget(activos_vacio_hint)
        raiz.addWidget(self.activos_vacio)
```

Agrega `self.filas_activas: list[_FilaActiva] = []` junto a
`self.filas: list[_FilaReciente] = []` (línea 202).

- [ ] **Step 5: Nuevas señales de la clase**

En `PantallaInicio`, junto a las señales ya declaradas (líneas 192-196):

```python
    traer_de_vuelta_pedido = Signal(Path)
    ya_entregado_pedido = Signal(Path)
```

- [ ] **Step 6: `set_recientes` arma también la lista de activos**

Reemplaza el cuerpo de `set_recientes` (líneas 272-294) por:

```python
    def set_recientes(self, entradas: list) -> None:
        for fila in self.filas:
            fila.hide()
            fila.setParent(None)
            fila.deleteLater()
        self.filas = []
        for fila in self.filas_activas:
            fila.hide()
            fila.setParent(None)
            fila.deleteLater()
        self.filas_activas = []
        from clasificador_video.entrega import EstadoEntrega

        for entrada in entradas:
            fila = _FilaReciente(entrada, self.lista_host)
            fila.abrir_pedido.connect(self.abrir_pedido.emit)
            fila.quitar_pedido.connect(self.quitar_pedido.emit)
            fila.refrescar_pedido.connect(self.refrescar_pedido.emit)
            estado, cuando = self._estado_de_entrega_de(entrada)
            fila.set_estado_de_entrega(estado, cuando)
            self.lista.addWidget(fila)
            self.filas.append(fila)

            if estado is not None and estado != EstadoEntrega.SIN_SUBIR:
                fila_activa = _FilaActiva(entrada, estado, cuando, self.activos_host)
                fila_activa.abrir_pedido.connect(self.abrir_pedido.emit)
                fila_activa.refrescar_pedido.connect(self.refrescar_pedido.emit)
                fila_activa.traer_de_vuelta_pedido.connect(self.traer_de_vuelta_pedido.emit)
                fila_activa.ya_entregado_pedido.connect(self.ya_entregado_pedido.emit)
                self.activos_lista.addWidget(fila_activa)
                self.filas_activas.append(fila_activa)

        self._actualizar_visibilidad()
```

- [ ] **Step 7: Los métodos de visibilidad de las pestañas**

Agrega, después de `set_recientes`:

```python
    def _al_cambiar_pestaña(self, _texto: str) -> None:
        self._actualizar_visibilidad()

    def _actualizar_visibilidad(self) -> None:
        en_activos = self.switch.current() == "En edición externa"
        self.lista_host.setVisible(not en_activos and bool(self.filas))
        self.vacio.setVisible(not en_activos and not self.filas)
        self.activos_host.setVisible(en_activos and bool(self.filas_activas))
        self.activos_vacio.setVisible(en_activos and not self.filas_activas)
```

- [ ] **Step 8: El helper de pruebas `nombres_activos_visibles`**

Junto a `nombres_visibles` (línea 323-324):

```python
    def nombres_activos_visibles(self) -> list[str]:
        return [f.entrada.nombre for f in self.filas_activas]
```

- [ ] **Step 9: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_inicio.py -q`
Expected: PASS (todas).

- [ ] **Step 10: Corre la prueba que confirma que la pantalla sigue sin abrir modales**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_inicio.py::test_la_pantalla_no_abre_ningun_modal -q`
Expected: PASS — este paso no debe agregar ningún `QMessageBox` a
`pantalla_inicio.py`; toda confirmación vive en `Coordinador` (Task 11).

- [ ] **Step 11: Corre la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS (todas).

- [ ] **Step 12: Commit**

```bash
git add src/clasificador_video/ui/pantalla_inicio.py tests/ui/test_pantalla_inicio.py
git commit -m "$(cat <<'EOF'
Agregar la pestaña "En edición externa" a la pantalla de inicio

Switch arriba de la lista, filtro de proyectos con entrega activa,
empty state propio y las señales de traer de vuelta / ya entregado
hacia el Coordinador.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: `Coordinador` — traer de vuelta y ya entregado sin abrir el proyecto

**Files:**
- Modify: `src/clasificador_video/app.py`
- Test: `tests/test_app.py`

Aquí sí hay `QMessageBox` (como ya lo hay en `main_window.py`): los dos
diálogos de confirmación, y el trabajo de red en segundo plano.

- [ ] **Step 1: Escribe las pruebas que fallan**

Agrega a `tests/test_app.py`, cerca de las pruebas de `_al_refrescar`
(después de la línea 490):

```python
def test_ya_entregado_pedido_cierra_la_entrega_y_refresca(qtbot, tmp_path, monkeypatch):
    from clasificador_video.entrega import EstadoEntrega

    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    ruta = _proyecto_en(tmp_path, extra={"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR, drive_folder_id="folder-x").to_dict()})
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    refrescos = []
    monkeypatch.setattr(coord, "_refrescar", lambda: refrescos.append(True))

    coord.inicio.ya_entregado_pedido.emit(ruta)

    assert refrescos == [True]
    assert abrir(ruta)["entrega"] is None


def test_ya_entregado_pedido_cancelado_no_toca_nada(qtbot, tmp_path, monkeypatch):
    from clasificador_video.entrega import EstadoEntrega

    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    ruta = _proyecto_en(tmp_path, extra={"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR, drive_folder_id="folder-x").to_dict()})
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[1])
    refrescos = []
    monkeypatch.setattr(coord, "_refrescar", lambda: refrescos.append(True))

    coord.inicio.ya_entregado_pedido.emit(ruta)

    assert refrescos == []
    assert abrir(ruta)["entrega"]["estado"] == EstadoEntrega.CON_EDITOR


def test_traer_de_vuelta_activo_lanza_el_trabajo_con_la_raiz_correcta(
        qtbot, tmp_path, monkeypatch):
    from clasificador_video import drive
    from clasificador_video.entrega import EstadoEntrega

    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    ruta = _proyecto_en(tmp_path, extra={
        "bins": [{"nombre": "Sony", "clips": [0], "camara": "sony",
                 "origen": str(tmp_path / "IAV" / "01. ASSETS VIDEO" / "02. CLIP" / "Sony")}],
        "entrega": EstadoEntrega(
            EstadoEntrega.CON_EDITOR, drive_folder_id="folder-x",
            prproj_local=str(tmp_path / "Casa.prproj"),
        ).to_dict(),
    })
    cliente = object()
    monkeypatch.setattr(drive, "hay_token_guardado", lambda: True)
    monkeypatch.setattr(drive, "cliente_autorizado", lambda credenciales: cliente)
    monkeypatch.setattr(
        drive, "revisar_y_persistir",
        lambda ruta_recibida, cliente_recibido: drive.ResultadoDeRevision(
            hay_cambios=True, prproj_modificado_en="x", tiene_material_nuevo=False),
    )
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    trabajos = []
    monkeypatch.setattr(coord._drive_pool, "start", trabajos.append)

    coord.inicio.traer_de_vuelta_pedido.emit(ruta)

    trabajo = trabajos.pop()
    assert trabajo._cliente is cliente
    assert trabajo._ruta_cvproj == ruta
    assert trabajo._raiz == tmp_path / "IAV"


def test_traer_de_vuelta_activo_al_terminar_pasa_a_en_revision(qtbot, tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    ruta = _proyecto_en(tmp_path, extra={"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR, drive_folder_id="folder-x").to_dict()})

    coord._al_terminar_traida_activa(ruta, "")

    assert abrir(ruta)["entrega"]["estado"] == EstadoEntrega.EN_REVISION


def test_traer_de_vuelta_activo_con_error_avisa(qtbot, tmp_path):
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    avisos = []
    monkeypatch_avisar = coord.inicio.avisar
    coord.inicio.avisar = avisos.append

    coord._al_terminar_traida_activa(tmp_path / "no-importa.cvproj", "red caída")

    assert avisos == ["No se pudo traer de Drive: red caída"]
    coord.inicio.avisar = monkeypatch_avisar


def test_traer_de_vuelta_activo_sin_token_avisa_sin_conectar(qtbot, tmp_path, monkeypatch):
    from clasificador_video import drive
    from clasificador_video.entrega import EstadoEntrega

    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    ruta = _proyecto_en(tmp_path, extra={"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR, drive_folder_id="folder-x").to_dict()})
    monkeypatch.setattr(drive, "hay_token_guardado", lambda: False)
    monkeypatch.setattr(
        drive, "cliente_autorizado",
        lambda credenciales: (_ for _ in ()).throw(AssertionError("no debe conectar")),
    )
    avisos = []
    monkeypatch.setattr(coord.inicio, "avisar", avisos.append)

    coord.inicio.traer_de_vuelta_pedido.emit(ruta)

    assert avisos == ["Conecta Google Drive desde Configuración antes de continuar."]
```

Agrega también `from PySide6.QtWidgets import QMessageBox` a los imports de
`tests/test_app.py` (junto a `QFileDialog`, línea 16).

- [ ] **Step 2: Corre la prueba y confirma que falla**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -q`
Expected: FAIL — `Coordinador` no tiene `traer_de_vuelta_pedido` ni
`ya_entregado_pedido` conectados, ni los métodos que las atienden.

- [ ] **Step 3: Imports nuevos al tope de `app.py`**

En `src/clasificador_video/app.py`, cambia la línea de import de `PySide6.QtCore`:

```python
from PySide6.QtCore import QObject
```

por:

```python
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
```

- [ ] **Step 4: La ruta fija de las credenciales, como constante del módulo**

Junto a `CARPETA_DE_MIGRACION` (línea 36), agrega:

```python
CREDENCIALES_DRIVE = Path.home() / ".clasificador_video" / "credenciales_google.json"
```

Y en `Coordinador._al_refrescar` (línea 502), reemplaza la ruta escrita a
mano:

```python
        credenciales = Path.home() / ".clasificador_video" / "credenciales_google.json"
```

por:

```python
        credenciales = CREDENCIALES_DRIVE
```

- [ ] **Step 5: Las clases de trabajo en segundo plano**

Antes de `class Coordinador` (antes de la línea 385), agrega:

```python
class _SeñalesDeDrive(QObject):
    """Resultados de trabajos de Drive lanzados desde la pantalla de
    inicio, sin ventana abierta. A diferencia de `SeñalesDeTrabajos` de
    `main_window.py` -- que solo atiende a UNA ventana -- aquí puede
    haber varios proyectos activos en vuelo a la vez, así que la señal
    lleva la ruta del `.cvproj` que identifica de cuál se trata.
    """

    traida_lista = Signal(Path, str)  # ruta_cvproj, error


class _TraidaActivaJob(QRunnable):
    """Trae el `.prproj` y el material nuevo de un proyecto sin abrirlo.

    Repite la lógica de `_TraidaDeDriveJob` (`ui/main_window.py`) en vez
    de reusarla: esa identifica su resultado con una señal sin ruta
    -- le basta, porque una ventana solo tiene un proyecto -- y aquí hace
    falta saber a cuál de varios proyectos activos corresponde cada
    resultado.
    """

    def __init__(self, cliente, estado, raiz_del_proyecto, ruta_cvproj, señales):
        super().__init__()
        self._cliente = cliente
        self._estado = estado
        self._raiz = raiz_del_proyecto
        self._ruta_cvproj = ruta_cvproj
        self.signals = señales

    def run(self) -> None:
        from clasificador_video import drive

        try:
            drive.traer_prproj(self._cliente, self._estado.drive_folder_id,
                               Path(self._estado.prproj_local))
            if self._raiz is not None:
                destinos = {
                    categoria: self._raiz / ruta
                    for categoria, ruta in drive.mapa_de_categorias_de_material_nuevo().items()
                }
                drive.traer_material_nuevo(self._cliente, self._estado.drive_folder_id, destinos)
        except Exception as e:
            self.signals.traida_lista.emit(self._ruta_cvproj, str(e))
            return
        self.signals.traida_lista.emit(self._ruta_cvproj, "")
```

- [ ] **Step 6: Conecta las señales nuevas en `Coordinador.__init__`**

En `Coordinador.__init__` (después de la línea 408
`self.inicio.refrescar_pedido.connect(self._al_refrescar)`), agrega:

```python
        self.inicio.traer_de_vuelta_pedido.connect(self._al_pedir_traer_de_vuelta_activo)
        self.inicio.ya_entregado_pedido.connect(self._al_pedir_ya_entregado)
        self._drive_pool = QThreadPool(self)
        self._señales_de_drive = _SeñalesDeDrive(self)
        self._señales_de_drive.traida_lista.connect(self._al_terminar_traida_activa)
```

- [ ] **Step 7: Los métodos nuevos del `Coordinador`**

Después de `_al_refrescar` (después de la línea 509), agrega:

```python
    def _cliente_de_drive_o_avisar(self):
        from clasificador_video import drive

        if not drive.hay_token_guardado():
            self.inicio.avisar(
                "Conecta Google Drive desde Configuración antes de continuar."
            )
            return None
        try:
            return drive.cliente_autorizado(CREDENCIALES_DRIVE)
        except Exception:
            self.inicio.avisar("No se pudo conectar con Google Drive.")
            return None

    def _al_pedir_traer_de_vuelta_activo(self, ruta_cvproj: Path) -> None:
        from clasificador_video import drive
        from clasificador_video.entrega import EstadoEntrega

        data = proyecto.abrir(ruta_cvproj)
        if not data:
            self.inicio.avisar("No se pudo leer este proyecto.")
            return
        estado = EstadoEntrega.de_dict(data.get("entrega"))
        if estado is None or estado.drive_folder_id is None:
            return
        cliente = self._cliente_de_drive_o_avisar()
        if cliente is None:
            return
        resultado = drive.revisar_y_persistir(ruta_cvproj, cliente)
        if resultado is None:
            return
        nombre = str(data.get("proyecto") or ruta_cvproj.stem)
        if not self._confirmar_traer_de_vuelta_activo(nombre, resultado):
            self._refrescar()
            return
        raiz = proyecto.raiz_de_assets_de(data)
        self._drive_pool.start(_TraidaActivaJob(
            cliente, estado, raiz, ruta_cvproj, self._señales_de_drive))

    def _confirmar_traer_de_vuelta_activo(self, nombre_proyecto: str, resultado) -> bool:
        from clasificador_video import drive

        mensaje = drive.mensaje_confirmar_traida(resultado)
        cuadro = QMessageBox(self.inicio)
        cuadro.setWindowTitle(f"Traer de vuelta — {nombre_proyecto}")
        cuadro.setText(mensaje.texto)
        if mensaje.informativo:
            cuadro.setInformativeText(mensaje.informativo)
        traer = cuadro.addButton(mensaje.texto_boton, QMessageBox.ButtonRole.AcceptRole)
        cuadro.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        cuadro.setDefaultButton(traer)
        cuadro.exec()
        return cuadro.clickedButton() is traer

    def _al_terminar_traida_activa(self, ruta_cvproj: Path, error: str) -> None:
        if error:
            self.inicio.avisar(f"No se pudo traer de Drive: {error}")
            self._refrescar()
            return
        from dataclasses import replace

        from clasificador_video.entrega import EstadoEntrega

        data = proyecto.abrir(ruta_cvproj)
        if data is not None:
            estado = EstadoEntrega.de_dict(data.get("entrega"))
            if estado is not None:
                data["entrega"] = replace(estado, estado=EstadoEntrega.EN_REVISION).to_dict()
                proyecto.guardar(ruta_cvproj, data)
        self._refrescar()

    def _al_pedir_ya_entregado(self, ruta_cvproj: Path) -> None:
        data = proyecto.abrir(ruta_cvproj) or {}
        nombre = str(data.get("proyecto") or ruta_cvproj.stem)
        if not self._confirmar_ya_entregado(nombre):
            return
        from clasificador_video import entrega

        if entrega.cerrar_en_archivo(ruta_cvproj):
            self._refrescar()

    def _confirmar_ya_entregado(self, nombre_proyecto: str) -> bool:
        cuadro = QMessageBox(self.inicio)
        cuadro.setWindowTitle("Marcar como ya entregado")
        cuadro.setText(
            f"«{nombre_proyecto}» va a dejar de aparecer en «En edición externa».")
        cuadro.setInformativeText("Esto no baja ni borra nada de Drive.")
        ya_entregado = cuadro.addButton("Ya entregado", QMessageBox.ButtonRole.AcceptRole)
        cuadro.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        cuadro.setDefaultButton(ya_entregado)
        cuadro.exec()
        return cuadro.clickedButton() is ya_entregado
```

- [ ] **Step 8: Importa `QMessageBox` (ya está) y confirma los imports del módulo**

`QMessageBox` ya está importado en `app.py` (línea 17, junto a
`QFileDialog`) — no hace falta agregarlo.

- [ ] **Step 9: Corre la prueba y confirma que pasa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_app.py -q`
Expected: PASS (todas).

- [ ] **Step 10: Corre la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS (todas).

- [ ] **Step 11: Commit**

```bash
git add src/clasificador_video/app.py tests/test_app.py
git commit -m "$(cat <<'EOF'
Traer de vuelta y Ya entregado desde la lista de proyectos activos

El Coordinador arma los dos diálogos de confirmación y lanza la
bajada de Drive en segundo plano sin abrir el proyecto, reusando la
lógica pura de drive.py (spec 2026-09-19).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Verificación visual real

**Files:**
- Ninguno del repo se modifica — es un script de verificación que vive en
  el scratchpad de la sesión (`/tmp` o el scratchpad que dé el entorno), no
  en el repo (CLAUDE.md: "los archivos temporales de esa verificación van
  al scratchpad de la sesión, nunca al repo").

Antes de dar por terminada la tarea, hay que VER el pixel — no basta con que
las pruebas pasen (CLAUDE.md, "Verificación visual real").

- [ ] **Step 1: Construye una `PantallaInicio` de prueba con los tres estados**

Escribe y corre un script (en el scratchpad, no en el repo) parecido a
esto, adaptando las rutas a `tmp_path` reales que existan en disco:

```python
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

from clasificador_video.ui.pantalla_inicio import PantallaInicio
from clasificador_video.ui.theme import build_stylesheet
from clasificador_video.recientes import Reciente
from clasificador_video.entrega import EstadoEntrega
import json

app = QApplication.instance() or QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())

carpeta = Path("/tmp/clipify_verificacion")
carpeta.mkdir(exist_ok=True)

def _proyecto(nombre, estado):
    ruta = carpeta / f"{nombre}.cvproj"
    ruta.write_text(json.dumps({
        "proyecto": nombre,
        "entrega": EstadoEntrega(estado, subido_en="2026-09-17T10:00:00").to_dict(),
    }))
    return Reciente(ruta, nombre, "2026-09-17 10:00")

pantalla = PantallaInicio()
pantalla.set_recientes([
    _proyecto("IAV-2609.10-A", EstadoEntrega.CON_EDITOR),
    _proyecto("2607.09", EstadoEntrega.EDITOR_CONTESTO),
    _proyecto("Casa Lomas", EstadoEntrega.EN_REVISION),
])
pantalla.switch.buttons[1].click()
pantalla.resize(640, 480)
pantalla.show()
app.processEvents()
pantalla.grab().save("/tmp/clipify_verificacion/activos.png")

pantalla.switch.buttons[0].click()
app.processEvents()
pantalla.grab().save("/tmp/clipify_verificacion/tus_proyectos.png")
```

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python /tmp/verificar_activos.py`

- [ ] **Step 2: Lee los dos PNG con la herramienta de lectura de archivos**

Verifica en `activos.png`:
- Las tres filas con sus tres píldoras distintas (ámbar "Con el editor",
  verde "El editor ya contestó", azul "En revisión").
- Los botones correctos por fila (las dos primeras con `⟳` + "Traer de
  vuelta" + "Ya entregado"; la de "Casa Lomas" solo con "Ya entregado").
- Que el texto no se corte de forma rara y los botones no se encimen.

Verifica en `tus_proyectos.png` que la lista normal se ve exactamente igual
que antes de este plan (sin el interruptor rompiendo el layout existente).

- [ ] **Step 3: Si algo se ve mal, corrige el QSS o el layout de la Task 9/10 y repite**

No sigas hasta que las dos capturas se vean correctas a simple vista.

- [ ] **Step 4: Borra los archivos de verificación del scratchpad**

No se commitea nada de este task — son artefactos de verificación, no
código ni documentación del repo.

---

## Resumen de archivos tocados

- `src/clasificador_video/entrega.py` — `EN_REVISION`, `cerrar_en_archivo`.
- `src/clasificador_video/bins.py` — `raiz_del_proyecto`.
- `src/clasificador_video/proyecto.py` — `raiz_de_assets_de`.
- `src/clasificador_video/drive.py` — `revisar_y_persistir` devuelve el
  resultado completo; `mensaje_confirmar_traida`.
- `src/clasificador_video/ui/main_window.py` — delega en `bins.raiz_del_proyecto`;
  usa `drive.mensaje_confirmar_traida`; `_on_drive_traida_lista` deja
  `EN_REVISION` en vez de limpiar.
- `src/clasificador_video/ui/title_bar.py` — pinta `EN_REVISION`.
- `src/clasificador_video/ui/theme.py` — colores nuevos.
- `src/clasificador_video/ui/pantalla_inicio.py` — `_FilaActiva`, el switch,
  la pestaña de activos, señales nuevas.
- `src/clasificador_video/app.py` — `Coordinador` arma los diálogos y lanza
  el trabajo de Drive para "Traer de vuelta" y "Ya entregado" sin abrir el
  proyecto.

No se toca el plugin de Premiere ni ningún archivo de `uxp-plugin/`.
