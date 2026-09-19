# Reconectar todo + Guía de edición como tablero — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dos cambios independientes, un plan porque Bruno los pidió juntos: (A) que reconectar un cuarto con un archivo (no una carpeta) adivine también dónde quedaron los demás cuartos, y (B) que la guía de edición pase de "la IA escribe un guion en prosa" a "la IA solo clasifica cada cuarto en su columna del patrón, y Bruno arma el orden arrastrando".

**Architecture:** Fase A vive entera en `revinculo.py` (funciones puras, sin Qt) más un ajuste chico en `main_window._on_buscar_media`/`reconectar_bin`. Fase B reescribe `guia.py` (la parte que piensa), `pantalla_guia.py` (el tablero, con drag-and-drop calcado del patrón que ya usa `room_rail.py`), `manifest.py` (el esquema de `Guia`), los métodos de `main_window.py` que ya orquestan la guía (ajustados, no rediseñados), y el panel de Premiere en `uxp-plugin/js/` (deja de leer campos que ya no existen).

**Tech Stack:** Python 3, PySide6 (Qt), pytest + pytest-qt, JavaScript plano en el plugin UXP (sin build step), node para sus pruebas puras.

**Simplificación de alcance declarada** (para que no se lea como un olvido): el indicador visual de "aquí se va a soltar" que tiene `RoomRail` (una línea que se mueve entre filas mientras arrastras) NO se replica en el tablero — soltar en una columna la agrega al final de esa columna. Es una diferencia de pulido, no de función: se puede subir/bajar después con los mismos controles. Si Bruno lo extraña, es un ajuste chico y aislado para una sesión aparte.

---

## Fase A — Reconectar todo el material de un jalón

Spec: `docs/superpowers/specs/2026-09-19-reconectar-todo-el-material-design.md`

### Task A1: La carpeta nueva de un bin, a partir de un archivo

**Files:**
- Modify: `src/clasificador_video/revinculo.py`
- Test: `tests/test_revinculo.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Agregar al final de `tests/test_revinculo.py`:

```python
def test_carpeta_de_bin_desde_archivo_sin_subcarpetas():
    archivo = Path("/Volumes/DiscoNuevo/Rodaje X copia/Sony/C0001.MP4")
    carpeta = revinculo.carpeta_de_bin_desde_archivo(archivo, "C0001.MP4")
    assert carpeta == Path("/Volumes/DiscoNuevo/Rodaje X copia/Sony")


def test_carpeta_de_bin_desde_archivo_con_subcarpeta():
    archivo = Path("/Volumes/DiscoNuevo/Rodaje X copia/Sony/Sub/C0001.MP4")
    carpeta = revinculo.carpeta_de_bin_desde_archivo(archivo, "Sub/C0001.MP4")
    assert carpeta == Path("/Volumes/DiscoNuevo/Rodaje X copia/Sony")


def test_carpeta_de_bin_desde_archivo_relativa_vacia_no_calza():
    archivo = Path("/Volumes/DiscoNuevo/Sony/C0001.MP4")
    assert revinculo.carpeta_de_bin_desde_archivo(archivo, "") is None
```

Añadir `from pathlib import Path` al inicio del archivo si no está ya
importado (ya lo está, lo usan las pruebas existentes de este archivo).

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_revinculo.py -k carpeta_de_bin_desde_archivo -v
```
Esperado: `FAIL` con `AttributeError: module 'clasificador_video.revinculo' has no attribute 'carpeta_de_bin_desde_archivo'`.

- [ ] **Step 3: Implementar**

Agregar en `src/clasificador_video/revinculo.py`, después de `_en_su_sitio`:

```python
def carpeta_de_bin_desde_archivo(archivo: Path, relativa: str) -> Path | None:
    """La carpeta que hay que usar como origen del bin, a partir de UN
    archivo que Bruno eligió y la ruta relativa que ese clip ya tenía
    guardada (`C0001.MP4`, o `Sub/C0001.MP4` si el bin tiene subcarpetas).

    Sube tantos niveles como carpetas tenga la relativa. `None` si la
    relativa viene vacía -- no hay con qué calcular nada.
    """
    partes = Path(relativa).parts
    if not partes:
        return None
    carpeta = archivo.parent
    for _ in range(len(partes) - 1):
        carpeta = carpeta.parent
    return carpeta
```

- [ ] **Step 4: Correr las pruebas y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_revinculo.py -k carpeta_de_bin_desde_archivo -v
```
Esperado: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/revinculo.py tests/test_revinculo.py
git commit -m "Agregar carpeta_de_bin_desde_archivo, para reconectar con un archivo en vez de una carpeta"
```

### Task A2: El "tramo de ruta que cambió"

**Files:**
- Modify: `src/clasificador_video/revinculo.py`
- Test: `tests/test_revinculo.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_desplazamiento_con_un_tramo_comun():
    viejo = Path("/Volumes/DiscoViejo/Rodaje X/Sony")
    nuevo = Path("/Volumes/DiscoNuevo/Rodaje X copia/Sony")
    d = revinculo.desplazamiento(viejo, nuevo)
    assert d == (Path("/Volumes/DiscoViejo/Rodaje X"),
                 Path("/Volumes/DiscoNuevo/Rodaje X copia"))


def test_desplazamiento_con_varios_tramos_comunes():
    viejo = Path("/Volumes/DiscoViejo/Rodaje X/Camaras/Sony")
    nuevo = Path("/Volumes/DiscoNuevo/Camaras/Sony")
    d = revinculo.desplazamiento(viejo, nuevo)
    assert d == (Path("/Volumes/DiscoViejo/Rodaje X"), Path("/Volumes/DiscoNuevo"))


def test_desplazamiento_sin_ningun_tramo_comun_es_none():
    viejo = Path("/Volumes/DiscoViejo/Rodaje X/Sony")
    nuevo = Path("/Volumes/DiscoNuevo/OtraCosa/Camara")
    assert revinculo.desplazamiento(viejo, nuevo) is None


def test_desplazamiento_identico_es_none():
    # nada cambio: no hay un tramo "que cambio" que reportar
    igual = Path("/Volumes/Disco/Rodaje X/Sony")
    assert revinculo.desplazamiento(igual, igual) is None


def test_aplicar_desplazamiento_a_un_origen_que_calza():
    prefijo_viejo = Path("/Volumes/DiscoViejo/Rodaje X")
    prefijo_nuevo = Path("/Volumes/DiscoNuevo/Rodaje X copia")
    origen_dron = Path("/Volumes/DiscoViejo/Rodaje X/Dron")
    candidata = revinculo.aplicar_desplazamiento(
        prefijo_viejo, prefijo_nuevo, origen_dron)
    assert candidata == Path("/Volumes/DiscoNuevo/Rodaje X copia/Dron")


def test_aplicar_desplazamiento_a_un_origen_que_no_calza():
    prefijo_viejo = Path("/Volumes/DiscoViejo/Rodaje X")
    prefijo_nuevo = Path("/Volumes/DiscoNuevo/Rodaje X copia")
    origen_ajeno = Path("/Volumes/OtroDisco/Otro Rodaje/Dron")
    assert revinculo.aplicar_desplazamiento(
        prefijo_viejo, prefijo_nuevo, origen_ajeno) is None
```

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_revinculo.py -k "desplazamiento" -v
```
Esperado: `FAIL` (funciones no existen).

- [ ] **Step 3: Implementar**

Agregar en `src/clasificador_video/revinculo.py`:

```python
def desplazamiento(origen_viejo: Path, origen_nuevo: Path) -> tuple[Path, Path] | None:
    """Qué tramo del camino cambió, como (prefijo_viejo, prefijo_nuevo).

    Se comparan las partes de las dos rutas DESDE EL FINAL: el tramo que
    coincide (típicamente el nombre del propio cuarto, "Sony", "Dron") es
    lo que NO cambió. Lo que sobra al principio es el desplazamiento.

    `None` cuando no hay ningún tramo en común (no hay patrón que sacar)
    o cuando las dos rutas son la misma (nada cambió, no hay nada que
    reportar).
    """
    viejas = origen_viejo.parts
    nuevas = origen_nuevo.parts
    comunes = 0
    tope = min(len(viejas), len(nuevas))
    while comunes < tope and viejas[-(comunes + 1)] == nuevas[-(comunes + 1)]:
        comunes += 1
    if comunes == 0 or comunes >= len(viejas):
        return None
    return (Path(*viejas[:len(viejas) - comunes]),
            Path(*nuevas[:len(nuevas) - comunes]))


def aplicar_desplazamiento(prefijo_viejo: Path, prefijo_nuevo: Path,
                           origen: Path) -> Path | None:
    """La ruta de `origen` como quedaría después del mismo desplazamiento.

    `None` si `origen` no cuelga de `prefijo_viejo` -- no se puede adivinar
    nada para un bin que no compartía esa parte del camino.
    """
    try:
        resto = origen.relative_to(prefijo_viejo)
    except ValueError:
        return None
    return prefijo_nuevo / resto
```

- [ ] **Step 4: Correr las pruebas y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_revinculo.py -k "desplazamiento" -v
```
Esperado: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/revinculo.py tests/test_revinculo.py
git commit -m "Agregar desplazamiento/aplicar_desplazamiento, el patron de carpeta que se le aplica a los demas bins"
```

### Task A3: A qué clip del bin corresponde el archivo elegido

**Files:**
- Modify: `src/clasificador_video/revinculo.py`
- Test: `tests/test_revinculo.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_clip_del_archivo_elegido_calza_uno_solo():
    relativas = {0: "C0001.MP4", 1: "C0002.MP4"}
    archivo = Path("/cualquier/carpeta/C0002.MP4")
    assert revinculo.clip_del_archivo_elegido(archivo, relativas) == 1


def test_clip_del_archivo_elegido_ninguno_calza():
    relativas = {0: "C0001.MP4"}
    archivo = Path("/cualquier/carpeta/C0099.MP4")
    assert revinculo.clip_del_archivo_elegido(archivo, relativas) is None


def test_clip_del_archivo_elegido_ambiguo_no_elige():
    # la tarjeta se formateo a medio rodaje: dos clips distintos del MISMO
    # bin terminaron con el mismo nombre de archivo
    relativas = {0: "Sesion1/C0001.MP4", 1: "Sesion2/C0001.MP4"}
    archivo = Path("/cualquier/carpeta/C0001.MP4")
    assert revinculo.clip_del_archivo_elegido(archivo, relativas) is None


def test_clip_del_archivo_elegido_ignora_mayusculas():
    relativas = {0: "c0001.mp4"}
    archivo = Path("/cualquier/carpeta/C0001.MP4")
    assert revinculo.clip_del_archivo_elegido(archivo, relativas) == 0
```

- [ ] **Step 2: Correr y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_revinculo.py -k clip_del_archivo_elegido -v
```

- [ ] **Step 3: Implementar**

```python
def clip_del_archivo_elegido(archivo: Path, relativas: dict[int, str]) -> int | None:
    """A qué clip del bin corresponde el archivo que Bruno eligió,
    comparando por NOMBRE (sin mayúsculas, igual que `buscar_bajo`)
    contra TODAS las relativas del bin -- no solo las que faltan, para
    que cualquier clip de ese cuarto le sirva para ubicar la carpeta.

    `None` cuando ninguna relativa calza, o cuando calzan dos o más: ahí
    elegir sería adivinar (pasa cuando la tarjeta se formateó a medio
    rodaje y dos clips distintos repiten nombre de archivo).
    """
    nombre = archivo.name.casefold()
    calzan = [i for i, relativa in relativas.items()
              if Path(relativa).name.casefold() == nombre]
    return calzan[0] if len(calzan) == 1 else None
```

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_revinculo.py -k clip_del_archivo_elegido -v
```
Esperado: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/revinculo.py tests/test_revinculo.py
git commit -m "Agregar clip_del_archivo_elegido, para ubicar a que clip corresponde el archivo que Bruno eligio"
```

### Task A4: Juntar todo — candidatas para los demás bins

**Files:**
- Modify: `src/clasificador_video/revinculo.py`
- Test: `tests/test_revinculo.py`

- [ ] **Step 1: Escribir la prueba que falla**

```python
def test_carpetas_candidatas_de_los_demas_bins(tmp_path):
    # Sony ya se resolvio (no entra en el resultado); Dron calza con el
    # desplazamiento y SU carpeta existe; Osmo calza pero su carpeta NO
    # existe en disco, asi que no se propone.
    (tmp_path / "nuevo" / "Dron").mkdir(parents=True)

    origenes_viejos = {
        "Sony": Path("/viejo/Rodaje/Sony"),
        "Dron": Path("/viejo/Rodaje/Dron"),
        "Osmo": Path("/viejo/Rodaje/Osmo"),
    }
    resultado = revinculo.carpetas_candidatas(
        bin_resuelto="Sony",
        origen_viejo_del_resuelto=Path("/viejo/Rodaje/Sony"),
        origen_nuevo_del_resuelto=tmp_path / "nuevo" / "Sony",
        origenes_viejos=origenes_viejos,
    )
    assert resultado == {"Dron": tmp_path / "nuevo" / "Dron"}
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_revinculo.py -k carpetas_candidatas -v
```

- [ ] **Step 3: Implementar**

```python
def carpetas_candidatas(bin_resuelto: str, origen_viejo_del_resuelto: Path,
                        origen_nuevo_del_resuelto: Path,
                        origenes_viejos: dict[str, Path]) -> dict[str, Path]:
    """Para cada OTRO bin, la carpeta donde probablemente quedó -- pero
    solo si esa carpeta existe DE VERDAD en disco. Nunca se propone una
    carpeta sin comprobar que está ahí.
    """
    cambio = desplazamiento(origen_viejo_del_resuelto, origen_nuevo_del_resuelto)
    if cambio is None:
        return {}
    prefijo_viejo, prefijo_nuevo = cambio
    candidatas: dict[str, Path] = {}
    for nombre, origen_viejo in origenes_viejos.items():
        if nombre == bin_resuelto:
            continue
        candidata = aplicar_desplazamiento(prefijo_viejo, prefijo_nuevo, origen_viejo)
        if candidata is not None and candidata.is_dir():
            candidatas[nombre] = candidata
    return candidatas
```

- [ ] **Step 4: Correr y verificar que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_revinculo.py -k carpetas_candidatas -v
```

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/revinculo.py tests/test_revinculo.py
git commit -m "Agregar carpetas_candidatas, que junta el desplazamiento y solo propone carpetas que existen"
```

### Task A5: El diálogo pide un archivo, y cascada a los demás bins

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_revinculo.py`

Contexto exacto de lo que hay hoy (ya leído del repo):

```python
# main_window.py, _on_buscar_media (hoy):
def _on_buscar_media(self, nombre: str, accion: str) -> None:
    origen = self.bins.origen_de(nombre)
    arranque = str(origen) if origen is not None else ""
    if accion == ACCION_PROXIES:
        titulo = f"¿Dónde quedaron los proxies de «{nombre}»?"
    else:
        titulo = f"¿Dónde quedó el material de «{nombre}»?"
    carpeta = QFileDialog.getExistingDirectory(self, titulo, arranque)
    if not carpeta:
        return
    if accion == ACCION_PROXIES:
        self.reconectar_proxies_de_bin(nombre, Path(carpeta))
    else:
        self.reconectar_bin(nombre, Path(carpeta))
```

- [ ] **Step 1: Escribir la prueba que falla**

Agregar a `tests/ui/test_main_window_revinculo.py` (revisar el archivo
primero para copiar su fixture `ventana`/helpers de importar dos bins con
clips reales en disco -- ya existen pruebas ahí que arman exactamente ese
escenario, por ejemplo `test_avisa_de_cada_bin_por_separado`; seguir el
mismo patrón para crear los dos bins con archivos de verdad en `tmp_path`):

```python
def test_elegir_un_archivo_reconecta_tambien_al_otro_bin_si_calza(
        ventana, tmp_path, monkeypatch):
    # Sony y Dron viven bajo la misma carpeta vieja, con la MISMA
    # estructura (una subcarpeta por bin).
    viejo = tmp_path / "viejo" / "Rodaje"
    sony_viejo = viejo / "Sony"
    dron_viejo = viejo / "Dron"
    sony_viejo.mkdir(parents=True)
    dron_viejo.mkdir(parents=True)
    (sony_viejo / "C0001.MP4").write_bytes(b"0" * 20)
    (dron_viejo / "DJI_0001.MP4").write_bytes(b"1" * 30)

    _importar_bin(ventana, "Sony", sony_viejo, ["C0001.MP4"])
    _importar_bin(ventana, "Dron", dron_viejo, ["DJI_0001.MP4"])

    # se mueve TODO el rodaje a una carpeta nueva, con la misma estructura
    nuevo = tmp_path / "nuevo" / "Rodaje X copia"
    sony_nuevo = nuevo / "Sony"
    dron_nuevo = nuevo / "Dron"
    sony_nuevo.mkdir(parents=True)
    dron_nuevo.mkdir(parents=True)
    (sony_nuevo / "C0001.MP4").write_bytes(b"0" * 20)
    (dron_nuevo / "DJI_0001.MP4").write_bytes(b"1" * 30)

    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(sony_nuevo / "C0001.MP4"), ""),
    )
    ventana._on_buscar_media("Sony", ACCION_MEDIA)

    # Sony se resolvio con el archivo elegido, y Dron se resolvio SOLO
    resultado_sony = ventana._ultimo_reencuentro["Sony"]
    resultado_dron = ventana._ultimo_reencuentro["Dron"]
    assert list(resultado_sony.reconectados.values()) == [sony_nuevo / "C0001.MP4"]
    assert list(resultado_dron.reconectados.values()) == [dron_nuevo / "DJI_0001.MP4"]


def test_si_la_carpeta_candidata_no_existe_el_otro_bin_no_se_toca(
        ventana, tmp_path, monkeypatch):
    viejo = tmp_path / "viejo" / "Rodaje"
    sony_viejo = viejo / "Sony"
    dron_viejo = viejo / "Dron"
    sony_viejo.mkdir(parents=True)
    dron_viejo.mkdir(parents=True)
    (sony_viejo / "C0001.MP4").write_bytes(b"0" * 20)
    (dron_viejo / "DJI_0001.MP4").write_bytes(b"1" * 30)

    _importar_bin(ventana, "Sony", sony_viejo, ["C0001.MP4"])
    _importar_bin(ventana, "Dron", dron_viejo, ["DJI_0001.MP4"])

    # solo se recreo Sony en el lugar nuevo -- Dron nunca llego ahi
    nuevo = tmp_path / "nuevo" / "Rodaje X copia"
    sony_nuevo = nuevo / "Sony"
    sony_nuevo.mkdir(parents=True)
    (sony_nuevo / "C0001.MP4").write_bytes(b"0" * 20)

    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(sony_nuevo / "C0001.MP4"), ""),
    )
    ventana._on_buscar_media("Sony", ACCION_MEDIA)

    assert "Dron" not in ventana._ultimo_reencuentro


def test_buscar_proxies_sigue_pidiendo_carpeta(ventana, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QFileDialog.getExistingDirectory",
        lambda *a, **k: llamadas.append(1) or "",
    )
    ventana._on_buscar_media("Sony", ACCION_PROXIES)
    assert llamadas == [1]
```

Si `_importar_bin` no existe ya como helper en ese archivo de pruebas,
revisar cómo arman un bin las pruebas vecinas (`test_avisa_cuantos_faltan_por_bin`
u otra) y usar el mismo mecanismo real de la ventana (`agregar_clips` o el
que ya use el resto del archivo) en vez de inventar uno nuevo -- este
archivo YA sabe montar bins con clips reales, no hace falta un segundo
camino.

- [ ] **Step 2: Correr y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_revinculo.py -k "reconecta_tambien or carpeta_candidata or sigue_pidiendo_carpeta" -v
```
Esperado: `FAIL` (`getOpenFileName` no se usa todavía; el segundo bin
nunca se toca).

- [ ] **Step 3: Implementar**

Reemplazar `_on_buscar_media` en `main_window.py`:

```python
def _on_buscar_media(self, nombre: str, accion: str) -> None:
    """Los botones de la barra. Selector del sistema, que es el único
    diálogo que el spec §8 deja usar.

    El de material pide un ARCHIVO, no una carpeta -- como Premiere: de
    ese archivo se saca la carpeta del bin, y de ahí se intenta también
    reconectar a los demás bins con material perdido (ver
    `_reconectar_en_cascada`).
    """
    origen = self.bins.origen_de(nombre)
    arranque = str(origen) if origen is not None else ""
    if accion == ACCION_PROXIES:
        titulo = f"¿Dónde quedaron los proxies de «{nombre}»?"
        carpeta = QFileDialog.getExistingDirectory(self, titulo, arranque)
        if not carpeta:
            return
        self.reconectar_proxies_de_bin(nombre, Path(carpeta))
        return
    titulo = f"¿Dónde quedó alguno de los clips de «{nombre}»?"
    archivo, _ = QFileDialog.getOpenFileName(self, titulo, arranque)
    if not archivo:
        return
    self._reconectar_desde_archivo(nombre, Path(archivo), origen)

def _reconectar_desde_archivo(self, nombre: str, archivo: Path,
                              origen_viejo: Path | None) -> None:
    relativas_del_bin = {
        i: self._relativas[i] for i in self.bins.clips_de(nombre)
        if i in self._relativas
    }
    clip = revinculo.clip_del_archivo_elegido(archivo, relativas_del_bin)
    if clip is None:
        QMessageBox.information(
            self, "No es de ese cuarto",
            f"Ese archivo no es de ninguno de los clips de «{nombre}», "
            "o su nombre le queda a más de uno. Elige la carpeta a mano "
            "para ese cuarto.")
        return
    carpeta_nueva = revinculo.carpeta_de_bin_desde_archivo(
        archivo, self._relativas[clip])
    if carpeta_nueva is None:
        return
    self.reconectar_bin(nombre, carpeta_nueva)
    if origen_viejo is None:
        return
    for otro, candidata in revinculo.carpetas_candidatas(
            bin_resuelto=nombre, origen_viejo_del_resuelto=origen_viejo,
            origen_nuevo_del_resuelto=carpeta_nueva,
            origenes_viejos={n: self.bins.origen_de(n) for n in self.bins.nombres()
                             if self.bins.origen_de(n) is not None
                             and self._faltantes_de_bin(n)}).items():
        self.reconectar_bin(otro, candidata)
```

Agregar el import que falte al tope del archivo:
```python
from clasificador_video import revinculo
```
(confirmar si ya está importado -- `reconectar_bin` ya usa
`revinculo.reencontrar_bin`, así que probablemente sí).

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_revinculo.py -v
```
Esperado: todas las pruebas de este archivo en verde, incluidas las tres
nuevas.

- [ ] **Step 5: Correr la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Esperado: todo verde. Si algo tronó, es probable que otra prueba vieja
mockee `getExistingDirectory` esperando que `_on_buscar_media` la use
para `ACCION_MEDIA` -- ajustarla a `getOpenFileName` en vez de revertir
el cambio.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_revinculo.py
git commit -m "Reconectar un cuarto con un archivo (como Premiere) y aplicar el mismo cambio a los demas bins"
```

### Task A6: Verificación visual real de la Fase A

- [ ] **Step 1**: Correr la app de verdad (`Skill: run` o el flujo normal
  del repo) con un proyecto de prueba de dos bins, mover la carpeta de
  material a otro lugar en disco, y reconectar UNO con "Buscar…" (ahora
  pide archivo). Confirmar con los ojos que el otro bin se reconectó solo
  en la barra de avisos.
- [ ] **Step 2**: Confirmar que "Buscar proxies…" sigue abriendo el
  diálogo de carpeta, sin cambios.
- [ ] **Step 3**: Si algo no se ve como se espera, no seguir a la Fase B
  sin arreglarlo primero.

---

## Fase B — La guía de edición como tablero

Spec: `docs/superpowers/specs/2026-09-19-guia-de-edicion-como-tablero-design.md`

### Task B1: Las siete columnas fijas, como dato

**Files:**
- Modify: `src/clasificador_video/guia.py`
- Test: `tests/test_guia.py`

- [ ] **Step 1: Escribir la prueba que falla**

Al tope de `tests/test_guia.py`, reemplazar el contenido existente (todas
las pruebas actuales prueban `prompt_de_sistema`/`contexto_de_respuestas`
con la forma vieja de preguntas+prosa, que se va entera) por:

```python
from clasificador_video import guia


def test_las_columnas_son_las_siete_del_patron_en_orden():
    ids = [c.id for c in guia.COLUMNAS]
    assert ids == [
        "apertura", "sociales", "habitaciones", "aerea_media",
        "amenidades", "area_general", "aerea_final",
    ]
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -k columnas -v
```

- [ ] **Step 3: Implementar**

Reemplazar el tope de `src/clasificador_video/guia.py` (todo lo que hay
antes de `Renglon`, incluido `prompt_de_sistema` y `contexto_de_respuestas`
completos, que se rehacen en el Task B2) por:

```python
"""La guía de edición: la parte que PIENSA.

Aquí no hay Qt, ni red, ni disco. Es a propósito: así todo esto se prueba
sin abrir la app y sin gastar una llamada. Lo que habla con el mundo vive
aparte (`ia.py`, `llave.py`).

Desde el 2026-09-19 la IA solo CLASIFICA cada cuarto en una de las siete
columnas fijas del patrón de recorrido -- ya no arma un guion en prosa.
Ver docs/superpowers/specs/2026-09-19-guia-de-edicion-como-tablero-design.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

MODELO = "deepseek-chat"
# El de conversación, no el de razonamiento: clasificar diez nombres en
# siete cajones no es una cadena de razonamiento, y el de razonamiento
# cuesta y tarda más para la misma respuesta.


@dataclass(frozen=True)
class Columna:
    id: str
    titulo: str
    pista: str  # lo que entra ahí, para el prompt del modelo


# Las siete columnas fijas, en el orden del patrón de recorrido de Bruno
# (docs/patron-de-recorrido/MI-PATRON.md). No cambian con el tipo de
# propiedad -- esa pregunta se fue.
COLUMNAS: tuple[Columna, ...] = (
    Columna("apertura", "Apertura / fachada", "la fachada o la aérea de entrada"),
    Columna("sociales", "Áreas sociales", "cocina, sala, comedor, terraza"),
    Columna("habitaciones", "Habitaciones", "recámaras, baños, vestidor"),
    Columna("aerea_media", "Aérea a media casa", "una aérea para respirar antes de salir"),
    Columna("amenidades", "Amenidades", "alberca, roof, amenidades en general"),
    Columna("area_general", "Área general", "la propiedad completa, de lejos"),
    Columna("aerea_final", "Aérea final", "la última toma, de salida"),
)

IDS_DE_COLUMNA = frozenset(c.id for c in COLUMNAS)
```

- [ ] **Step 4: Correr y verificar que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -k columnas -v
```

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Reemplazar el prompt en prosa de la guia por las siete columnas fijas del patron"
```

### Task B2: El prompt de clasificación

**Files:**
- Modify: `src/clasificador_video/guia.py`
- Test: `tests/test_guia.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_el_prompt_de_clasificacion_lista_las_siete_columnas():
    texto = guia.prompt_de_clasificacion(["Recámara 1", "Alberca"])
    for c in guia.COLUMNAS:
        assert c.titulo in texto or c.id in texto
        assert c.pista in texto


def test_el_prompt_de_clasificacion_lleva_los_cuartos_tal_cual():
    texto = guia.prompt_de_clasificacion(["Recámara 1", "Baño"])
    assert "Recámara 1" in texto
    assert "Baño" in texto


def test_el_prompt_de_clasificacion_no_pide_prosa():
    texto = guia.prompt_de_clasificacion(["Sala"])
    assert "recorrido" not in texto.lower()
    assert "párrafo" not in texto.lower()


def test_cuerpo_de_clasificacion_arma_el_mensaje():
    cuerpo = guia.cuerpo_de_clasificacion(["Sala", "Cocina"])
    assert cuerpo["model"] == guia.MODELO
    assert cuerpo["messages"][0]["role"] == "system"
    assert "Sala" in cuerpo["messages"][0]["content"]
```

- [ ] **Step 2: Correr y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -k "clasificacion" -v
```

- [ ] **Step 3: Implementar**

Agregar en `guia.py`, después de `IDS_DE_COLUMNA`:

```python
def prompt_de_clasificacion(cuartos: list[str]) -> str:
    """Lo que se le dice al modelo: en qué columna cae cada cuarto.

    NO se le pide prosa, ni una razón por escrito, ni un orden. Eso lo
    decide Bruno arrastrando en el tablero -- lo único que hace falta de
    la IA es una clasificación barata, un cajón por cuarto.
    """
    partes = [
        "Eres el asistente de un editor de video mexicano que hace recorridos de",
        "propiedades en venta o renta. Tu único trabajo es decir, de cada cuarto",
        "que te doy, en cuál de estos momentos del recorrido entra:",
        "",
    ]
    for c in COLUMNAS:
        partes.append(f'- "{c.id}" ({c.titulo}): {c.pista}')
    partes += [
        "",
        "Los cuartos son EXACTAMENTE estos, escritos igual --con sus acentos y",
        "mayúsculas tal cual--, y le toca una columna a cada uno:",
        "\n".join("- " + c for c in cuartos),
        "",
        "Contestas SOLO con JSON, con esta forma exacta:",
        '{"clasificacion": [{"cuarto": "<nombre tal cual>", "columna": "<id de columna>"}]}',
        "",
        "Sin texto antes ni después. Un objeto por cada cuarto de la lista.",
    ]
    return "\n".join(partes)


def cuerpo_de_clasificacion(cuartos: list[str]) -> dict:
    """El objeto que se le manda a la API. No la llama: eso es `ia.py`."""
    return {
        "model": MODELO,
        "messages": [
            {"role": "system", "content": prompt_de_clasificacion(cuartos or [])},
            {"role": "user", "content": "Clasifica estos cuartos."},
        ],
    }
```

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -k "clasificacion" -v
```

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Agregar el prompt de clasificacion (cuarto -> columna), sin prosa"
```

### Task B3: Leer la respuesta del modelo

**Files:**
- Modify: `src/clasificador_video/guia.py`
- Test: `tests/test_guia.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_leer_clasificacion_ok():
    crudo = json.dumps({"clasificacion": [
        {"cuarto": "Sala", "columna": "sociales"},
        {"cuarto": "Dron", "columna": "apertura"},
    ]})
    r = guia.leer_clasificacion(crudo, cuartos_reales=["Sala", "Dron"])
    assert r.ok
    assert r.columna_de == {"Sala": "sociales", "Dron": "apertura"}


def test_leer_clasificacion_ignora_un_cuarto_que_no_es_real():
    crudo = json.dumps({"clasificacion": [
        {"cuarto": "Sala", "columna": "sociales"},
        {"cuarto": "Cuarto Inventado", "columna": "sociales"},
    ]})
    r = guia.leer_clasificacion(crudo, cuartos_reales=["Sala"])
    assert r.ok
    assert r.columna_de == {"Sala": "sociales"}


def test_leer_clasificacion_ignora_una_columna_que_no_es_una_de_las_siete():
    crudo = json.dumps({"clasificacion": [
        {"cuarto": "Sala", "columna": "columna_que_no_existe"},
    ]})
    r = guia.leer_clasificacion(crudo, cuartos_reales=["Sala"])
    assert r.ok
    assert r.columna_de == {}


def test_leer_clasificacion_un_cuarto_repetido_se_queda_con_la_primera():
    crudo = json.dumps({"clasificacion": [
        {"cuarto": "Sala", "columna": "sociales"},
        {"cuarto": "Sala", "columna": "amenidades"},
    ]})
    r = guia.leer_clasificacion(crudo, cuartos_reales=["Sala"])
    assert r.columna_de == {"Sala": "sociales"}


def test_leer_clasificacion_respuesta_vacia():
    r = guia.leer_clasificacion(None, cuartos_reales=["Sala"])
    assert not r.ok
    assert r.error


def test_leer_clasificacion_texto_no_json():
    r = guia.leer_clasificacion("no traigo json", cuartos_reales=["Sala"])
    assert not r.ok
```

- [ ] **Step 2: Correr y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -k leer_clasificacion -v
```

- [ ] **Step 3: Implementar**

Reusar `_recortar_json` tal cual está (no cambia: sigue siendo el mismo
"cuenta llaves, salta las que van dentro de una cadena"). Reemplazar
`Renglon`/`Respuesta`/`leer_respuesta` por:

```python
@dataclass
class Clasificacion:
    ok: bool
    columna_de: dict[str, str] = field(default_factory=dict)
    error: str = ""


def leer_clasificacion(texto: str | None, cuartos_reales: list[str]) -> Clasificacion:
    """Saca la clasificación de lo que sea que haya contestado el modelo.

    **Nunca revienta**: una respuesta fea es un caso normal. Un cuarto que
    no es de los reales, o una columna que no es una de las siete, se
    IGNORA -- ese cuarto simplemente no queda pre-colocado en ninguna
    columna, y Bruno lo arrastra él mismo. Nunca se inventa un cuarto ni
    una columna que no sea una de las siete.
    """
    crudo = ("" if texto is None else str(texto)).strip()
    if not crudo:
        return Clasificacion(ok=False, error="El modelo no contestó nada.")
    recorte = _recortar_json(crudo)
    if not recorte:
        return Clasificacion(ok=False, error="El modelo contestó con texto en vez de la clasificación.")
    try:
        datos = json.loads(recorte)
    except (json.JSONDecodeError, ValueError):
        return Clasificacion(ok=False, error="La respuesta del modelo no se pudo leer.")
    if not isinstance(datos, dict) or not isinstance(datos.get("clasificacion"), list):
        return Clasificacion(ok=False, error="La respuesta llegó con otra forma.")

    reales = set(cuartos_reales or [])
    columna_de: dict[str, str] = {}
    for renglon in datos["clasificacion"]:
        if not isinstance(renglon, dict):
            continue
        cuarto = renglon.get("cuarto")
        columna = renglon.get("columna")
        if not isinstance(cuarto, str) or not isinstance(columna, str):
            continue
        if cuarto not in reales or columna not in IDS_DE_COLUMNA:
            continue
        columna_de.setdefault(cuarto, columna)  # la primera aparición manda
    return Clasificacion(ok=True, columna_de=columna_de)
```

Dejar `_recortar_json` donde está (no se toca).

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -k leer_clasificacion -v
```

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Reemplazar leer_respuesta por leer_clasificacion: ignora cuartos y columnas que no son reales"
```

### Task B4: `cuartos_sin_usar`, y borrar `revisar_lista`

**Files:**
- Modify: `src/clasificador_video/guia.py`
- Test: `tests/test_guia.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_cuartos_sin_usar_devuelve_los_que_no_aparecen():
    assert guia.cuartos_sin_usar(
        reales=["Sala", "Cocina", "Roof garden"], pasos=["Sala", "Cocina"]
    ) == ["Roof garden"]


def test_cuartos_sin_usar_vacio_cuando_todos_aparecen():
    assert guia.cuartos_sin_usar(
        reales=["Sala"], pasos=["Sala", "Sala"]
    ) == []


def test_ya_no_existe_revisar_lista():
    assert not hasattr(guia, "revisar_lista")
    assert not hasattr(guia, "avisos_de_la_revision")
    assert not hasattr(guia, "Revision")
```

- [ ] **Step 2: Correr y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -k "sin_usar or ya_no_existe" -v
```

- [ ] **Step 3: Implementar**

Agregar:

```python
def cuartos_sin_usar(reales: list[str], pasos: list[str]) -> list[str]:
    """Los cuartos reales que nunca se arrastraron a ninguna columna.

    Compara por igualdad exacta de cadena, mismo criterio que el resto
    del proyecto para nombres de cuarto.
    """
    usados = set(pasos or [])
    return [c for c in (reales or []) if c not in usados]
```

Borrar de `guia.py`: `Revision`, `revisar_lista`, `avisos_de_la_revision`
(las tres funciones/clase completas). Confirmar con grep que nada más en
el archivo las sigue usando:

```bash
grep -n "revisar_lista\|avisos_de_la_revision\|class Revision" src/clasificador_video/guia.py
```
Esperado: sin resultados.

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -v
```
Esperado: todo lo de este archivo en verde (las pruebas viejas de
`prompt_de_sistema`/`contexto_de_respuestas`/`revisar_lista` ya se
quitaron en los tasks B1-B3; si queda alguna suelta, bórrala aquí).

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Agregar cuartos_sin_usar y borrar revisar_lista (ya no puede sobrar un cuarto inventado)"
```

### Task B5: `Renglon` simplificado, y `Respuesta` para el tablero ya armado

**Files:**
- Modify: `src/clasificador_video/guia.py`
- Test: `tests/test_guia.py`

`main_window.py` usa hoy `logica_guia.Renglon(cuarto=c)` y
`logica_guia.Respuesta(ok=True, recorrido=..., lista=[...])` (ver Task
B8). Se conservan ESAS DOS clases con forma más chica, para que el resto
de `main_window.py` seguir hablando del mismo vocabulario (una lista de
pasos con `.cuarto` cada uno) en vez de aprender uno nuevo.

- [ ] **Step 1: Escribir la prueba que falla**

```python
def test_renglon_solo_tiene_cuarto():
    r = guia.Renglon(cuarto="Sala")
    assert r.cuarto == "Sala"
    assert not hasattr(r, "porque")
    assert not hasattr(r, "fuera_del_patron")


def test_respuesta_ya_no_tiene_recorrido():
    r = guia.Respuesta(ok=True, lista=[guia.Renglon(cuarto="Sala")])
    assert r.lista[0].cuarto == "Sala"
    assert not hasattr(r, "recorrido")
```

- [ ] **Step 2: Correr y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -k "renglon_solo or ya_no_tiene_recorrido" -v
```

- [ ] **Step 3: Implementar**

Agregar en `guia.py` (junto a `Clasificacion`):

```python
@dataclass
class Renglon:
    cuarto: str


@dataclass
class Respuesta:
    ok: bool
    lista: list[Renglon] = field(default_factory=list)
    error: str = ""
```

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Simplificar Renglon y Respuesta: solo cuarto, sin porque/fuera_del_patron/recorrido"
```

### Task B6: `manifest.py` — `Guia.orden` pasa a `list[str]`

**Files:**
- Modify: `src/clasificador_video/manifest.py`
- Test: `tests/test_manifest.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Revisar primero `tests/test_manifest.py` en busca de pruebas que
construyan `RenglonDeGuia`/`Guia(recorrido=...)` -- se van a romper por
diseño, hay que reescribirlas junto con esto, no dejarlas rotas.
Reemplazarlas por:

```python
def test_guia_to_dict_es_solo_una_lista_de_nombres():
    g = manifest.Guia(orden=["Fachada", "Sala", "Fachada"])
    assert g.to_dict() == {"orden": ["Fachada", "Sala", "Fachada"]}


def test_manifest_sin_guia_sigue_siendo_valido():
    m = manifest.Manifest(proyecto="Casa", orientacion="horizontal", guia=None)
    assert m.to_dict()["guia"] is None
```

- [ ] **Step 2: Correr y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -k "guia" -v
```

- [ ] **Step 3: Implementar**

En `src/clasificador_video/manifest.py`, borrar la clase `RenglonDeGuia`
entera y reemplazar `Guia` por:

```python
@dataclass
class Guia:
    """La guía de edición, congelada. El plugin la LEE y nunca la pide.

    `orden` es una lista plana de nombres de cuarto, en el orden que
    Bruno aceptó en el tablero. Puede repetir un nombre (la aérea que
    abre y cierra el recorrido)."""

    orden: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"orden": list(self.orden)}
```

Quitar `RenglonDeGuia` de cualquier import en el propio archivo (no
debería haber ninguno, es la misma clase).

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/manifest.py tests/test_manifest.py
git commit -m "Simplificar Guia.orden a list[str], borrar RenglonDeGuia y Guia.recorrido"
```

### Task B7: Ajustar `main_window.py` a los campos que se fueron

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

Este task NO cambia lógica, solo los nombres de campos que ya no
existen. Los métodos afectados (ya localizados en el repo, líneas
aproximadas del archivo ANTES de este plan -- pueden haberse corrido un
poco por los tasks anteriores, buscar por nombre de función):

- [ ] **Step 1: Escribir/ajustar las pruebas que fallan**

Buscar en `tests/ui/test_main_window.py` las pruebas de
`_guia_cuadrada_con_el_rail`, `restaurar_guia`, `guia_quedo_vieja`,
`aviso_de_guia_vieja`, `_guia_para_el_manifest`/`_guia_para_la_sesion`, y
`aceptar_orden_de_la_guia` (buscar con
`grep -n "guia_cuadrada\|restaurar_guia\|guia_quedo_vieja\|aviso_de_guia_vieja\|_guia_para_el_manifest\|aceptar_orden_de_la_guia" tests/ui/test_main_window.py`).
Cualquiera que construya un `Renglon(cuarto=..., porque=..., ...)` o un
`Respuesta(recorrido=..., ...)` hay que ajustarla a la forma nueva
(`Renglon(cuarto=...)`, `Respuesta(ok=..., lista=...)`, sin `recorrido`).
No se agregan pruebas nuevas en este task: las que ya existen, ajustadas,
son la cobertura.

- [ ] **Step 2: Correr y verificar que fallan (por los campos viejos)**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -k "guia" -v
```

- [ ] **Step 3: Implementar**

En `main_window.py`:

1. `pedir_guia` (la que arma `cuerpo_del_request(cuartos, respuestas,
   patron.leer())`) se renombra a `pedir_clasificacion`, sin parámetro
   `respuestas`:

```python
def pedir_clasificacion(self) -> None:
    """Le pide al modelo la clasificación y la enseña.

    **Nunca revienta hacia afuera**: un fallo de red se dice y ya. La
    app sigue exportando sin guia, que es un manifest perfectamente
    valido.
    """
    cuartos = self.room_selection.active_rooms()
    cuerpo = logica_guia.cuerpo_de_clasificacion(cuartos)
    if self._pantalla_guia is not None:
        self._pantalla_guia.armando()
    self._guia_pool.start(
        _GuiaJob(llave.leer(), cuerpo, self._señales_de_trabajos)
    )
```

2. `_GuiaJob` (la clase `QRunnable`, arriba en el archivo, junto a
   `_ThumbnailJob`) necesita saber `cuartos_reales` para poder validar la
   respuesta, y sus dos ramas de error pasan de construir una
   `logica_guia.Respuesta(ok=False, ...)` a una
   `logica_guia.Clasificacion(ok=False, ...)` (`_mostrar_guia` ahora
   espera una `Clasificacion`, ver el punto 3 de abajo). Reemplazar la
   clase entera:

```python
class _GuiaJob(QRunnable):
    """Le pide la clasificación al modelo FUERA del hilo de la interfaz.

    Antes `pedir_guia` llamaba directo y esperaba ahi mismo: entre que Bruno
    apretaba «Clasificar de nuevo» y que el modelo contestaba --diez o veinte
    segundos-- Clipify se quedaba tieso, y sin internet se quedaba asi hasta
    el minuto que dura la espera de `ia.py`. Una app que no responde se lee
    como una app muerta.

    No crea ningun objeto de Qt: recibe el portador compartido de la
    ventana, por el segfault que documenta `SeñalesDeTrabajos`.

    **No revienta nunca**: un fallo es una `Clasificacion` con su error
    dicho en palabras, igual que una respuesta fea. Una excepcion que sube
    desde un hilo del pool no la atrapa nadie.
    """

    def __init__(self, llave_de_la_api: str, cuerpo: dict,
                 cuartos_reales: list[str], señales: "SeñalesDeTrabajos"):
        super().__init__()
        self._llave = llave_de_la_api
        self._cuerpo = cuerpo
        self._cuartos_reales = cuartos_reales
        self._señales = señales

    def run(self) -> None:
        try:
            crudo = ia.preguntar(self._llave, self._cuerpo)
        except ia.ErrorDeIA as error:
            self._señales.guia_lista.emit(
                logica_guia.Clasificacion(ok=False, error=str(error))
            )
            return
        except Exception as error:  # noqa: BLE001 -- ver el docstring
            self._señales.guia_lista.emit(
                logica_guia.Clasificacion(
                    ok=False,
                    error="No se pudo clasificar: " + str(error),
                )
            )
            return
        self._señales.guia_lista.emit(
            logica_guia.leer_clasificacion(crudo, self._cuartos_reales)
        )
```

   Y quien la instancia (`pedir_clasificacion`, arriba) le pasa `cuartos`:

```python
self._guia_pool.start(
    _GuiaJob(llave.leer(), cuerpo, cuartos, self._señales_de_trabajos)
)
```

   Por último, ajustar el comentario de la declaración de la señal (no
   cambia de tipo, `Signal(object)` ya acepta cualquier cosa):
```python
guia_lista = Signal(object)                 # logica_guia.Clasificacion
```

3. `_mostrar_guia(self, respuesta)` pasa a recibir una
   `logica_guia.Clasificacion` en vez de una `Respuesta`. Ya no arma
   `revision` (se borró `revisar_lista`). Se convierte la clasificación
   en la forma que la pantalla necesita (ver Task B9 para qué espera
   `PantallaGuia.mostrar_clasificacion`):

```python
def _mostrar_guia(self, clasificacion) -> None:
    if self._pantalla_guia is not None:
        self._pantalla_guia.mostrar_clasificacion(clasificacion)
```

   (`self.guia_actual`/`self._cuartos_de_la_guia`/`self._autosave()` ya
   NO se tocan aquí -- eso pasa a `aceptar_orden_de_la_guia`, que es
   cuando de verdad hay un orden aceptado; antes se guardaba desde que se
   ENSEÑABA para no perder el aviso de "guía vieja" si Bruno nunca
   apretaba aceptar, pero eso ya no aplica: sin apretar "Usar este orden"
   no hay tablero que perder, porque se vuelve a clasificar gratis la
   próxima vez que abra la pantalla.)

4. `aceptar_orden_de_la_guia` **no cambia**: sigue recibiendo `orden:
   list[str]` (la señal no cambió de forma) y llamando a
   `self.room_selection.reordenar(orden)`.

5. `_guia_cuadrada_con_el_rail`: quitar la referencia a
   `self.guia_actual.recorrido` en la construcción de `Respuesta` final:

```python
def _guia_cuadrada_con_el_rail(self):
    if self.guia_actual is None or not self.guia_actual.ok:
        return self.guia_actual
    reales = self.room_selection.active_rooms()
    pasos = [r for r in self.guia_actual.lista if r.cuarto in reales]
    nombrados = {r.cuarto for r in pasos}
    pasos += [
        logica_guia.Renglon(cuarto=c) for c in reales if c not in nombrados
    ]
    return logica_guia.Respuesta(ok=True, lista=pasos)
```

6. `restaurar_guia`: `logica_guia.leer_respuesta(json.dumps(datos))` ya
   no existe (`leer_respuesta` se borró). La guía guardada en el
   `.cvproj` es la ACEPTADA (una lista plana de nombres, con
   `cuartos_de_entonces`), así que se reconstruye directo sin pasar por
   el parseo de la respuesta de la IA:

```python
def restaurar_guia(self, datos) -> None:
    self.guia_actual = None
    self._cuartos_de_la_guia = []
    if not isinstance(datos, dict):
        return
    orden = datos.get("orden")
    if not isinstance(orden, list) or not all(isinstance(c, str) for c in orden):
        return
    self.guia_actual = logica_guia.Respuesta(
        ok=True, lista=[logica_guia.Renglon(cuarto=c) for c in orden]
    )
    entonces = datos.get("cuartos_de_entonces")
    self._cuartos_de_la_guia = (
        [str(c) for c in entonces] if isinstance(entonces, list)
        else [r.cuarto for r in self.guia_actual.lista]
    )
```

7. `_guia_para_el_manifest`: quita `recorrido` y `RenglonDeGuia`:

```python
def _guia_para_el_manifest(self):
    if self.guia_actual is None or not self.guia_actual.ok:
        return None
    return Guia(orden=[r.cuarto for r in self.guia_actual.lista])
```

8. Ajustar el import al tope del archivo: cambiar
   `from clasificador_video.manifest import Clip, Guia, Manifest, RenglonDeGuia`
   a `from clasificador_video.manifest import Clip, Guia, Manifest`.

9. En `_abrir_pantalla_de_guia`: donde hoy llama a
   `logica_guia.revisar_lista(...)` antes de `mostrar_respuesta`, se
   quita esa revisión (ya no existe) y se llama directo a un método
   nuevo de restauración de la pantalla (ver Task B9):

```python
if self.guia_actual is not None and self.guia_actual.ok:
    self._pantalla_guia.mostrar_guia_aceptada(self.guia_actual.lista)
```

   Y la conexión de señales cambia `guia_pedida` por
   `clasificacion_pedida` (sin argumento):

```python
self._pantalla_guia.clasificacion_pedida.connect(self.pedir_clasificacion)
```

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -k "guia" -v
```

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "Ajustar main_window.py a la clasificacion (sin recorrido/porque/fuera_del_patron)"
```

### Task B8: El tablero — chips arrastrables y columnas

**Files:**
- Modify: `src/clasificador_video/ui/pantalla_guia.py`
- Test: `tests/ui/test_pantalla_guia.py`

Se reescribe el archivo entero. El patrón de arrastrar-y-soltar se calca
del que ya usa `room_rail.py` (`MIME_CUARTO`, `QDrag`, `dragEnterEvent`/
`dropEvent` en el contenedor) -- ver ese archivo antes de escribir este
task si hace falta refrescar el patrón exacto.

- [ ] **Step 1: Escribir las pruebas que fallan**

Reemplazar `tests/ui/test_pantalla_guia.py` entero (las pruebas viejas
son de las dos preguntas y el resultado en HTML, que ya no existen) por:

```python
import pytest
from clasificador_video import guia as logica
from clasificador_video.ui.pantalla_guia import PantallaGuia


@pytest.fixture
def pantalla(qtbot):
    p = PantallaGuia()
    qtbot.addWidget(p)
    p.resize(900, 600)
    return p


def test_arranca_con_las_siete_columnas_vacias(pantalla):
    assert len(pantalla.columnas) == 7
    for columna in pantalla.columnas.values():
        assert columna.cuartos() == []


def test_franja_arranca_con_todos_los_cuartos_reales(pantalla):
    pantalla.poner_cuartos_reales(["Sala", "Cocina"])
    assert pantalla.franja.cuartos() == ["Sala", "Cocina"]


def test_mostrar_clasificacion_coloca_los_chips(pantalla):
    pantalla.poner_cuartos_reales(["Sala", "Roof garden"])
    pantalla.mostrar_clasificacion(logica.Clasificacion(
        ok=True, columna_de={"Sala": "sociales"}))
    assert pantalla.columnas["sociales"].cuartos() == ["Sala"]
    # Roof garden no vino en la clasificacion: se queda sin colocar
    assert all("Roof garden" not in c.cuartos() for c in pantalla.columnas.values())


def test_clasificacion_fallida_deja_todo_vacio_y_avisa(pantalla):
    pantalla.poner_cuartos_reales(["Sala"])
    pantalla.mostrar_clasificacion(logica.Clasificacion(
        ok=False, error="no hay red"))
    assert all(c.cuartos() == [] for c in pantalla.columnas.values())
    assert "no hay red" in pantalla.aviso_label.text().lower() or \
           "no se pudo" in pantalla.aviso_label.text().lower()


def test_agregar_cuarto_a_una_columna_lo_arrastra_ahi(pantalla):
    pantalla.poner_cuartos_reales(["Sala"])
    pantalla.agregar_a_columna("sociales", "Sala")
    assert pantalla.columnas["sociales"].cuartos() == ["Sala"]


def test_agregar_dos_veces_repite_el_paso(pantalla):
    pantalla.poner_cuartos_reales(["Dron"])
    pantalla.agregar_a_columna("apertura", "Dron")
    pantalla.agregar_a_columna("aerea_final", "Dron")
    assert pantalla.orden_final() == ["Dron", "Dron"]


def test_quitar_un_paso_lo_regresa_a_la_franja(pantalla):
    pantalla.poner_cuartos_reales(["Sala"])
    pantalla.agregar_a_columna("sociales", "Sala")
    pantalla.columnas["sociales"].quitar(0)
    assert pantalla.columnas["sociales"].cuartos() == []


def test_orden_final_junta_las_columnas_en_su_orden_fijo():
    pantalla = PantallaGuia()
    pantalla.poner_cuartos_reales(["Fachada", "Sala", "Alberca"])
    pantalla.agregar_a_columna("sociales", "Sala")
    pantalla.agregar_a_columna("apertura", "Fachada")
    pantalla.agregar_a_columna("amenidades", "Alberca")
    assert pantalla.orden_final() == ["Fachada", "Sala", "Alberca"]


def test_aviso_de_sin_usar_se_actualiza_solo(pantalla):
    pantalla.poner_cuartos_reales(["Sala", "Cocina"])
    pantalla.agregar_a_columna("sociales", "Sala")
    assert "Cocina" in pantalla.aviso_label.text()
    pantalla.agregar_a_columna("sociales", "Cocina")
    assert pantalla.aviso_label.text() == ""


def test_usar_este_orden_emite_la_lista_plana(pantalla, qtbot):
    pantalla.poner_cuartos_reales(["Sala"])
    pantalla.agregar_a_columna("sociales", "Sala")
    with qtbot.waitSignal(pantalla.orden_aceptado, timeout=1000) as blocker:
        pantalla.usar_button.click()
    assert blocker.args == [["Sala"]]


def test_clasificar_de_nuevo_pide_confirmar_si_hay_arrastres(pantalla, monkeypatch):
    pantalla.poner_cuartos_reales(["Sala"])
    pantalla.agregar_a_columna("sociales", "Sala")
    monkeypatch.setattr(
        "clasificador_video.ui.pantalla_guia.QMessageBox.question",
        lambda *a, **k: __import__("PySide6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.StandardButton.No,
    )
    pedidos = []
    pantalla.clasificacion_pedida.connect(lambda: pedidos.append(1))
    pantalla.clasificar_de_nuevo_button.click()
    assert pedidos == []  # dijo que no: no se pierde el arrastre


def test_mostrar_guia_aceptada_arma_el_tablero_desde_una_lista_plana(pantalla):
    pantalla.poner_cuartos_reales(["Sala", "Sala"])
    pantalla.mostrar_guia_aceptada(
        [logica.Renglon(cuarto="Sala"), logica.Renglon(cuarto="Sala")])
    assert pantalla.orden_final() == ["Sala", "Sala"]
```

- [ ] **Step 2: Correr y verificar que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_guia.py -v
```
Esperado: falla todo (el módulo actual no tiene ninguna de estas cosas).

- [ ] **Step 3: Implementar**

Reescribir `src/clasificador_video/ui/pantalla_guia.py` entero:

```python
"""La pantalla de la guía de edición: el tablero.

Solo dibuja y conecta. Todo lo que decide algo vive en `guia.py` --las
columnas fijas, el prompt, leer la respuesta-- y todo lo que habla con el
mundo en `ia.py` y `llave.py`. Si algún día hay que arreglar POR QUÉ una
clasificación salió mal, no se busca aquí.

Spec: docs/superpowers/specs/2026-09-19-guia-de-edicion-como-tablero-design.md
"""
from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from clasificador_video import guia as logica

MIME_PASO = "application/x-clasificador-guia-paso"


class _Chip(QWidget):
    """Un cuarto arrastrable. Vive en la franja o dentro de una columna."""

    quitar_pedido = Signal()

    def __init__(self, cuarto: str, quitable: bool, parent=None):
        super().__init__(parent)
        self.cuarto = cuarto
        self._inicio = None
        self.setObjectName("guiaChip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        fila = QHBoxLayout(self)
        fila.setContentsMargins(8, 5, 8, 5)
        nombre = QLabel(cuarto)
        fila.addWidget(nombre, stretch=1)
        if quitable:
            quitar = QPushButton("✕")
            quitar.setObjectName("guiaChipQuitar")
            quitar.setFlat(True)
            quitar.clicked.connect(self.quitar_pedido.emit)
            fila.addWidget(quitar)

    def mousePressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._inicio = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if self._inicio is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._inicio).manhattanLength() < \
                QApplication.startDragDistance():
            return
        self._inicio = None
        mime = QMimeData()
        mime.setData(MIME_PASO, self.cuarto.encode())
        arrastre = QDrag(self)
        arrastre.setMimeData(mime)
        arrastre.setPixmap(self.grab())
        arrastre.exec(Qt.DropAction.CopyAction)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        self._inicio = None
        super().mouseReleaseEvent(event)


class _CajaDePasos(QWidget):
    """Una columna del tablero, o la franja de abajo.

    La franja y una columna comparten esta misma clase: la única
    diferencia es si soltar ahí AGREGA (columna) o si el chip que sale de
    aquí se arrastra sin vaciar el origen (franja, `es_franja=True`)."""

    cambio = Signal()

    def __init__(self, es_franja: bool, parent=None):
        super().__init__(parent)
        self.es_franja = es_franja
        self.setAcceptDrops(True)
        self._orden: list[str] = []
        self._layout = QHBoxLayout(self) if es_franja else QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)
        if es_franja:
            self._layout.addStretch(1)

    def cuartos(self) -> list[str]:
        return list(self._orden)

    def poner(self, cuartos: list[str]) -> None:
        self._orden = list(cuartos)
        self._repintar()

    def agregar(self, cuarto: str) -> None:
        self._orden.append(cuarto)
        self._repintar()

    def quitar(self, indice: int) -> None:
        if 0 <= indice < len(self._orden):
            del self._orden[indice]
            self._repintar()
            self.cambio.emit()

    def _repintar(self) -> None:
        while self._layout.count() > (1 if self.es_franja else 0):
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, cuarto in enumerate(self._orden):
            chip = _Chip(cuarto, quitable=not self.es_franja)
            if not self.es_franja:
                chip.quitar_pedido.connect(lambda i=i: self.quitar(i))
            if self.es_franja:
                self._layout.insertWidget(self._layout.count() - 1, chip)
            else:
                self._layout.addWidget(chip)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.mimeData().hasFormat(MIME_PASO):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.mimeData().hasFormat(MIME_PASO):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        mime = event.mimeData()
        if not mime.hasFormat(MIME_PASO):
            return
        cuarto = bytes(mime.data(MIME_PASO)).decode(errors="ignore")
        if self.es_franja:
            # soltar en la franja no hace nada: es el origen, no un destino
            event.acceptProposedAction()
            return
        self.agregar(cuarto)
        self.cambio.emit()
        event.acceptProposedAction()


class PantallaGuia(QWidget):
    """El tablero: siete columnas fijas, la franja de cuartos, y
    «Usar este orden»."""

    clasificacion_pedida = Signal()
    orden_aceptado = Signal(list)
    cerrada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaGuia")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._cuartos_reales: list[str] = []
        self._armando = False

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.setSpacing(12)

        cabecera = QHBoxLayout()
        titulo = QLabel("Guía de edición")
        titulo.setObjectName("guiaTitulo")
        cabecera.addWidget(titulo)
        cabecera.addStretch(1)
        self.cerrar_button = QPushButton("Cerrar")
        self.cerrar_button.setObjectName("guiaCerrar")
        self.cerrar_button.clicked.connect(self.cerrada.emit)
        cabecera.addWidget(self.cerrar_button)
        raiz.addLayout(cabecera)

        self.aviso_label = QLabel("")
        self.aviso_label.setObjectName("guiaAvisos")
        self.aviso_label.setWordWrap(True)
        raiz.addWidget(self.aviso_label)

        tablero_scroll = QScrollArea()
        tablero_scroll.setWidgetResizable(True)
        tablero_widget = QWidget()
        tablero_layout = QHBoxLayout(tablero_widget)
        tablero_layout.setSpacing(10)
        self.columnas: dict[str, _CajaDePasos] = {}
        for columna in logica.COLUMNAS:
            envoltura = QWidget()
            envoltura.setObjectName("guiaColumna")
            envoltura.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            v = QVBoxLayout(envoltura)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(0)
            titulo_col = QLabel(columna.titulo)
            titulo_col.setObjectName("guiaColumnaTitulo")
            v.addWidget(titulo_col)
            caja = _CajaDePasos(es_franja=False)
            caja.cambio.connect(self._al_cambiar)
            v.addWidget(caja, stretch=1)
            self.columnas[columna.id] = caja
            tablero_layout.addWidget(envoltura, stretch=1)
        tablero_scroll.setWidget(tablero_widget)
        raiz.addWidget(tablero_scroll, stretch=1)

        franja_titulo = QLabel("Tus cuartos — arrastra uno a una columna")
        franja_titulo.setObjectName("guiaFranjaTitulo")
        raiz.addWidget(franja_titulo)
        self.franja = _CajaDePasos(es_franja=True)
        self.franja.setObjectName("guiaFranja")
        raiz.addWidget(self.franja)

        fila_botones = QHBoxLayout()
        self.clasificar_de_nuevo_button = QPushButton("Clasificar de nuevo")
        self.clasificar_de_nuevo_button.setObjectName("guiaClasificar")
        self.clasificar_de_nuevo_button.clicked.connect(self._al_pedir_clasificacion)
        fila_botones.addWidget(self.clasificar_de_nuevo_button)
        fila_botones.addStretch(1)
        self.usar_button = QPushButton("Usar este orden")
        self.usar_button.setObjectName("guiaUsar")
        self.usar_button.clicked.connect(self._al_usar)
        fila_botones.addWidget(self.usar_button)
        raiz.addLayout(fila_botones)

    # --- lo que le da main_window ------------------------------------

    def poner_cuartos_reales(self, cuartos: list[str]) -> None:
        self._cuartos_reales = list(cuartos)
        self.franja.poner(list(cuartos))
        for caja in self.columnas.values():
            caja.poner([])
        self._refrescar_aviso()

    def mostrar_clasificacion(self, clasificacion) -> None:
        self._armando = False
        for caja in self.columnas.values():
            caja.poner([])
        if not clasificacion.ok:
            self.aviso_label.setText(
                "No se pudo clasificar (" + clasificacion.error + "). "
                "Acomoda los cuartos a mano."
            )
            return
        for cuarto, columna_id in clasificacion.columna_de.items():
            if columna_id in self.columnas:
                self.columnas[columna_id].agregar(cuarto)
        self._refrescar_aviso()

    def mostrar_guia_aceptada(self, lista) -> None:
        """Arma el tablero a partir de una guía YA aceptada, poniendo todo
        en la primera columna (`apertura`) -- no se intenta reconstruir a
        qué columna pertenecía cada paso (spec §10): es solo para que
        reabrir no se vea vacío antes de clasificar de nuevo."""
        self.columnas[logica.COLUMNAS[0].id].poner([r.cuarto for r in lista])
        self._refrescar_aviso()

    def armando(self) -> None:
        self._armando = True
        self.aviso_label.setText("Clasificando…")

    # --- lo que arma el orden final ------------------------------------

    def agregar_a_columna(self, columna_id: str, cuarto: str) -> None:
        self.columnas[columna_id].agregar(cuarto)
        self._refrescar_aviso()

    def orden_final(self) -> list[str]:
        pasos: list[str] = []
        for columna in logica.COLUMNAS:
            pasos.extend(self.columnas[columna.id].cuartos())
        return pasos

    def _refrescar_aviso(self) -> None:
        sin_usar = logica.cuartos_sin_usar(self._cuartos_reales, self.orden_final())
        if not sin_usar:
            self.aviso_label.setText("")
        elif len(sin_usar) == 1:
            self.aviso_label.setText(f"Sin usar: {sin_usar[0]}.")
        else:
            self.aviso_label.setText("Sin usar: " + ", ".join(sin_usar) + ".")

    def _al_cambiar(self) -> None:
        self._refrescar_aviso()

    def _al_pedir_clasificacion(self) -> None:
        if self.orden_final():
            respuesta = QMessageBox.question(
                self, "Clasificar de nuevo",
                "Vas a perder cómo acomodaste los cuartos. ¿Clasificar de nuevo?",
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        self.clasificacion_pedida.emit()

    def _al_usar(self) -> None:
        self.orden_aceptado.emit(self.orden_final())

    def keyPressEvent(self, event) -> None:  # noqa: N802 -- override de Qt
        if event.key() == Qt.Key.Key_Escape and not self._armando:
            self.cerrada.emit()
            return
        super().keyPressEvent(event)
```

- [ ] **Step 4: Correr y verificar que pasan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_guia.py -v
```

Si `test_clasificar_de_nuevo_pide_confirmar_si_hay_arrastres` falla por
cómo se mockeó `QMessageBox.question`, simplificar el mock a:
```python
from PySide6.QtWidgets import QMessageBox
monkeypatch.setattr(
    "clasificador_video.ui.pantalla_guia.QMessageBox.question",
    lambda *a, **k: QMessageBox.StandardButton.No,
)
```
y ajustar el import al tope del archivo de pruebas.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/pantalla_guia.py tests/ui/test_pantalla_guia.py
git commit -m "Reescribir PantallaGuia como tablero de 7 columnas con arrastrar y soltar"
```

### Task B9: Conectar `main_window.py` a la pantalla nueva

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: Escribir la prueba que falla**

Buscar la prueba existente que verifica que abrir la pantalla de guía
carga los cuartos reales (si no existe una, agregarla):

```python
def test_abrir_la_guia_le_pasa_los_cuartos_reales(qtbot, tmp_path):
    window = _window_with_video(qtbot, rooms=("Sala", "Cocina"))
    window._abrir_pantalla_de_guia()
    assert window._pantalla_guia.franja.cuartos() == ["Sala", "Cocina"]
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -k abrir_la_guia_le_pasa -v
```

- [ ] **Step 3: Implementar**

En `_abrir_pantalla_de_guia`, después de crear `self._pantalla_guia` y
conectar señales, agregar la carga de cuartos reales (algo que la
pantalla vieja no necesitaba porque los cuartos solo importaban al
apretar "armar"):

```python
self._pantalla_guia.poner_cuartos_reales(self.room_selection.active_rooms())
```

Esta línea va SIEMPRE que se abre la pantalla (no solo la primera vez):
moverla fuera del `if self._pantalla_guia is None:` para que si Bruno
agregó cuartos entre una apertura y otra, la franja los refleje.

- [ ] **Step 4: Correr y verificar que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window.py -k "guia" -v
```

- [ ] **Step 5: Correr la suite completa de Python**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Esperado: todo verde.

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window.py
git commit -m "Pasarle los cuartos reales al tablero cada vez que se abre la pantalla de guia"
```

### Task B10: El panel de Premiere — `avance.js`

**Files:**
- Modify: `uxp-plugin/js/avance.js`
- Modify: `uxp-plugin/pruebas/avance.pruebas.js`

- [ ] **Step 1: Ajustar el fixture de las pruebas**

En `uxp-plugin/pruebas/avance.pruebas.js`, cambiar:
```javascript
const guion = [
  { cuarto: "Aerea" },
  { cuarto: "Sala" },
  { cuarto: "Aerea" },
];
```
por:
```javascript
const guion = ["Aerea", "Sala", "Aerea"];
```
El resto del archivo no cambia: las entradas de `avance` (`{paso, cuarto}`)
siguen siendo objetos, es solo `guion` el que cambia de forma.

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

```bash
node uxp-plugin/pruebas/correr.js
```
Esperado: fallan los casos de `avance.pruebas.js` (`cuartoDelPaso` sigue
leyendo `.cuarto` de algo que ahora es un string).

- [ ] **Step 3: Implementar**

En `uxp-plugin/js/avance.js`, cambiar `cuartoDelPaso`:
```javascript
// El cuarto del paso N del guion (los pasos se cuentan desde 1), o null.
function cuartoDelPaso(guion, paso) {
  const cuarto = (guion || [])[paso - 1];
  return cuarto || null;
}
```
El resto del archivo (`cuadrarAvance`, `conPaso`, `estaMontado`,
`pasoActual`, `cuartosMontados`) no cambia ni una línea: todas pasan por
`cuartoDelPaso`.

- [ ] **Step 4: Correr las pruebas y verificar que pasan**

```bash
node uxp-plugin/pruebas/correr.js
```
Esperado: todos los casos de `avance.pruebas.js` en verde.

- [ ] **Step 5: Commit**

```bash
git add uxp-plugin/js/avance.js uxp-plugin/pruebas/avance.pruebas.js
git commit -m "Adaptar avance.js a que el guion sea una lista de nombres, no de objetos"
```

### Task B11: El panel de Premiere — `pestanaOrden.js` y `processManifest.js`

**Files:**
- Modify: `uxp-plugin/js/pestanaOrden.js`
- Modify: `uxp-plugin/js/processManifest.js`

Estos dos archivos requieren `premierepro` o tocan el DOM del panel, así
que **no tienen cobertura en `node uxp-plugin/pruebas/correr.js`** — el
propio harness los excluye (ver el comentario al tope de `correr.js`).
Se verifican leyendo el código con cuidado y, si Bruno puede, abriendo
Premiere con un manifest de prueba (fuera del alcance de este plan
ejecutado por un agente).

- [ ] **Step 1: `processManifest.js`**

Cambiar:
```javascript
const ordenDeLaGuia = ((manifest.guia && manifest.guia.orden) || []).map(
  (r) => r.cuarto
);
```
por:
```javascript
const ordenDeLaGuia = (manifest.guia && manifest.guia.orden) || [];
```
(ya es una lista de nombres, no hace falta el `.map`).

- [ ] **Step 2: `pestanaOrden.js` — quitar el párrafo**

En `dibujarGuia`, borrar el bloque completo:
```javascript
if (guia.recorrido) {
  const parrafo = document.createElement("p");
  parrafo.className = "guia-recorrido";
  parrafo.textContent = guia.recorrido;
  cuerpo.appendChild(parrafo);
}
```

- [ ] **Step 3: `pestanaOrden.js` — `guion` ya no trae objetos**

En `dibujarGuia`, cambiar:
```javascript
const actual = pasoActual(avance, guion);
const vistos = {};
for (let i = 1; i <= guion.length; i++) {
  cuerpo.appendChild(dibujarPaso(guion[i - 1], i, avance, actual, vistos));
  vistos[guion[i - 1].cuarto] = true;
}
```
por:
```javascript
const actual = pasoActual(avance, guion);
const vistos = {};
for (let i = 1; i <= guion.length; i++) {
  cuerpo.appendChild(dibujarPaso(guion[i - 1], i, avance, actual, vistos));
  vistos[guion[i - 1]] = true;
}
```

En `dibujarEncabezado`, cambiar:
```javascript
  grande.textContent =
    actual === null
      ? "Montaste todo"
      : "Paso " + actual + " · " + guion[actual - 1].cuarto;
```
por:
```javascript
  grande.textContent =
    actual === null
      ? "Montaste todo"
      : "Paso " + actual + " · " + guion[actual - 1];
```

En `dibujarPaso`, la firma recibe ahora el NOMBRE (string) en vez del
renglón-objeto. Cambiar la función entera a:

```javascript
function dibujarPaso(cuarto, numero, avance, actual, vistos) {
  const montado = estaMontado(avance, numero);

  const fila = document.createElement("div");
  fila.className = "guia-paso";
  if (montado) fila.classList.add("montado");
  if (numero === actual) fila.classList.add("ahora");

  const caja = document.createElement("input");
  caja.type = "checkbox";
  caja.className = "guia-palomita";
  caja.checked = montado;
  caja.addEventListener("change", () => palomear(numero, caja.checked));
  fila.appendChild(caja);

  const n = document.createElement("span");
  n.className = "guia-num";
  n.textContent = numero;
  fila.appendChild(n);

  const nombre = document.createElement("span");
  nombre.className = "guia-cuarto";
  nombre.textContent = cuarto;
  fila.appendChild(nombre);

  if (vistos[cuarto]) {
    // SOLO de la segunda vez en adelante: marcar la primera diria que algo
    // pasa con ella, y no pasa nada.
    const otra = document.createElement("span");
    otra.className = "guia-otravez";
    otra.textContent = "otra vez";
    fila.appendChild(otra);
  }

  return fila;
}
```
(se borran los dos últimos párrafos de la función vieja, los del
`renglon.porque`/`fuera_del_patron` -- ya no hay razón que mostrar).

En `pintarLosBinsMontados`, cambiar:
```javascript
const orden = guion.map((r) => r.cuarto);
```
por:
```javascript
const orden = guion.slice();
```
(ya es la lista de nombres; `.slice()` para no mutar `guion` con el
`filter` de la línea siguiente, mismo cuidado que tenía el `.map` de antes).

- [ ] **Step 4: Verificación por lectura**

```bash
grep -n "\.cuarto\|\.porque\|\.fuera_del_patron\|guia\.recorrido" uxp-plugin/js/pestanaOrden.js uxp-plugin/js/processManifest.js
```
Esperado: sin resultados (ningún campo de los que se fueron sigue
leyéndose).

- [ ] **Step 5: Correr la suite de node completa**

```bash
node uxp-plugin/pruebas/correr.js
```
Esperado: sigue todo en verde (este task no toca nada que ese harness
cubra, pero confirma que no se rompió nada de lo que sí prueba).

- [ ] **Step 6: Commit**

```bash
git add uxp-plugin/js/pestanaOrden.js uxp-plugin/js/processManifest.js
git commit -m "Quitar parrafo y razones del panel de Premiere; guion ya es una lista de nombres"
```

### Task B12: Verificación visual real del tablero

**Files:**
- Ninguno de código — solo verificación, siguiendo el CLAUDE.md del repo
  ("si no se miró la imagen, no se afirma").

- [ ] **Step 1**: Escribir un script chico de una sola vez (fuera del
  repo, en el scratchpad de la sesión) que arme una `PantallaGuia`,
  llame `poner_cuartos_reales` con 6-8 nombres reales de un rodaje de
  ejemplo, `mostrar_clasificacion` con una clasificación de prueba que
  cubra 5 de las 7 columnas, `grab()` el widget, y guardar el PNG.

- [ ] **Step 2**: Leer el PNG con la herramienta de lectura de archivos
  y confirmar a simple vista: las siete columnas se leen, los chips
  colocados se ven donde deben, el aviso de "sin usar" aparece con los
  cuartos que faltaron.

- [ ] **Step 3**: Repetir con `mostrar_clasificacion` fallida
  (`ok=False`) y confirmar que el aviso de error se lee bien y las
  columnas quedan vacías.

- [ ] **Step 4**: Borrar el script del scratchpad al terminar (no entra
  al repo).

### Task B13: Higiene de archivos y suite completa

- [ ] **Step 1**: Correr la suite completa de Python:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```
Esperado: todo verde.

- [ ] **Step 2**: Correr la suite de node:
```bash
node uxp-plugin/pruebas/correr.js
```
Esperado: todo verde.

- [ ] **Step 3**: `git status` y confirmar que no quedó ningún archivo
  suelto en la raíz ni en `uxp-plugin/` fuera de lo que este plan tocó.

- [ ] **Step 4**: Revisar con `grep -rn "recorrido\|fuera_del_patron" src/ uxp-plugin/js/`
  que no quede ninguna referencia viva a los campos que se borraron
  (comentarios sueltos que los mencionen como historia están bien; código
  que los lea o escriba, no).

---

## Autorevisión del plan (hecha antes de entregarlo)

- **Cobertura del spec de Fase A**: Tasks A1-A4 cubren §4 y §5 del spec
  (carpeta desde archivo, desplazamiento, emparejar por nombre). Task A5
  cubre §3 (el diálogo pide archivo) y la cascada a los demás bins. Task
  A6 cubre la verificación visual pedida en §8.
- **Cobertura del spec de Fase B**: B1 cubre §4 (columnas fijas), B2-B3
  cubren §5 (la IA solo clasifica, modos de falla), B4 cubre §2 y §6
  (revisar_lista se borra, aviso de sin-usar), B5-B7 cubren §8.a/§8.d
  (guia.py y main_window.py), B6 cubre §8.c (manifest), B8-B9 cubren
  §8.b (el tablero), B10-B11 cubren §8.e (el panel de Premiere).
- **Sin placeholders**: cada step de código trae el código completo, no
  hay "TODO" ni "similar a la anterior" sin el bloque real.
- **Consistencia de nombres**: `Renglon.cuarto`, `Respuesta.lista`,
  `Clasificacion.columna_de`, `Guia.orden` se usan con el mismo nombre en
  todos los tasks donde aparecen (B3, B5, B6, B7, B9).
- **Riesgo declarado**: Task B11 no tiene cobertura automática (necesita
  Premiere) — se dice explícitamente en vez de fingir que sí la tiene.
