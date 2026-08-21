# La fila de proxies — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que se puedan pedir proxies de varios bins seguidos: se forman, corren en orden, se cancelan por separado y sacan un solo cartel al final.

**Architecture:** La tanda que corre sigue siendo `_generando_proxies` (un dict, o `None`). Se le agrega al lado `_cola_de_proxies`, una lista de NOMBRES de bin esperando turno, y `_resumen_de_la_fila`, que acumula lo que llevan todas las tandas juntas. `proxy_gen` gana una función pura que barre los `.parcial`. El encabezado del bin aprende un estado más —«en cola»— y su menú deja de mirar solo al que corre.

**Tech Stack:** Python 3.13, PySide6, pytest + pytest-qt. Suite completa: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`

**Spec:** `docs/superpowers/specs/2026-08-20-cola-de-proxies-design.md`

---

## Estructura de archivos

| Archivo | Responsabilidad | Qué cambia |
|---|---|---|
| `src/clasificador_video/proxy_gen.py` | Generar un proxy. Sin Qt. | `barrer_parciales()` |
| `src/clasificador_video/ui/clip_sheet.py` | Dibujar el bin | Estado «en cola» en la insignia; el menú ofrece Cancelar también a los formados |
| `src/clasificador_video/ui/theme.py` | Color | Estilo de la insignia «en cola» |
| `src/clasificador_video/ui/main_window.py` | La fila | Encolar, arrancar el siguiente, cancelar por bin, un solo cartel, barrer al empezar |
| `tests/test_proxy_gen.py` | Task 1 | |
| `tests/ui/test_clip_sheet.py` | Task 2 | |
| `tests/ui/test_main_window_bins.py` | Tasks 3–6 | |

**Nombres que se usan en todo el plan** (si un task los escribe distinto, es un bug):

- `proxy_gen.barrer_parciales(carpeta: Path) -> int`
- `_BinHeader.set_en_cola(en_cola: bool) -> None`
- `ClipSheet.set_bin_en_cola(nombre: str, en_cola: bool) -> None`
- `MainWindow._cola_de_proxies: list[str]`
- `MainWindow._resumen_de_la_fila: dict` con llaves `creados: int` y `fallidos: list`
- `MainWindow._arrancar_siguiente_de_la_fila() -> None`
- `MainWindow._esta_pedido(nombre: str) -> bool`

---

### Task 1: Barrer los `.parcial`

**Files:**
- Modify: `src/clasificador_video/proxy_gen.py`
- Test: `tests/test_proxy_gen.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

Al final de `tests/test_proxy_gen.py`:

```python
def test_barrer_parciales_se_lleva_los_pedazos(tmp_path):
    """Un `.parcial` es un proxy a medias de una tanda que se corto de golpe.
    `generar` los borra al cancelar, pero un cierre forzado o un corte de luz
    los deja ahi, y nadie los recoge nunca."""
    (tmp_path / "C0001S03.mp4.parcial").write_bytes(b"x")
    (tmp_path / "C0002S03.mp4.parcial").write_bytes(b"x")

    barridos = barrer_parciales(tmp_path)

    assert barridos == 2
    assert list(tmp_path.iterdir()) == []


def test_barrer_parciales_no_toca_los_proxies_buenos(tmp_path):
    """Lo unico que se va son los pedazos. Un proxy terminado es el trabajo
    de varios minutos que esta tanda existe para no repetir."""
    bueno = tmp_path / "C0001S03.mp4"
    bueno.write_bytes(b"proxy de verdad")
    (tmp_path / "C0002S03.mp4.parcial").write_bytes(b"x")

    barrer_parciales(tmp_path)

    assert bueno.exists()
    assert not (tmp_path / "C0002S03.mp4.parcial").exists()


def test_barrer_parciales_aguanta_una_carpeta_que_no_esta(tmp_path):
    """Se llama al empezar la tanda de un bin, y ese bin puede apuntar a una
    tarjeta desconectada. Que no exista no es un error: no hay nada que
    barrer."""
    assert barrer_parciales(tmp_path / "no existe") == 0
```

Añade `barrer_parciales` al import que ya hay arriba del archivo.

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py -q -k barrer
```

Esperado: FAIL con `ImportError: cannot import name 'barrer_parciales'`.

- [ ] **Step 3: Escribe la función**

En `proxy_gen.py`, justo debajo de `faltantes`:

```python
SUFIJO_PARCIAL = ".parcial"


def barrer_parciales(carpeta: Path) -> int:
    """Borra los proxies a medias que hayan quedado, y dice cuantos eran.

    `generar` escribe a `<nombre>.mp4.parcial` y solo renombra al nombre
    bueno cuando ffmpeg termina bien, asi que un `.parcial` NUNCA bloquea a
    su clip: `ruta_de_proxy(...).exists()` no lo ve y el clip se vuelve a
    generar solo. O sea que esto no arregla nada roto -- limpia.

    Cancelar ya los borra. Los que quedan son de un cierre de golpe, un
    crash o un corte de luz, y ahi nadie los recoge: se van juntando en la
    carpeta del material de Bruno.

    **Cuando se llama importa:** al EMPEZAR la tanda de un bin, que es el
    unico momento en que se sabe que no hay ninguno en vuelo --se genera de
    uno en uno, y la fila arranca la siguiente solo cuando la anterior
    termino--. Llamarlo al pedir un bin barreria el archivo que otro bin
    esta escribiendo en ese instante, porque dos bins de la misma carpeta
    comparten carpeta de proxies.
    """
    try:
        pedazos = [p for p in carpeta.iterdir()
                   if p.is_file() and p.name.endswith(SUFIJO_PARCIAL)]
    except OSError:
        return 0   # la carpeta no esta, o no se puede leer: nada que barrer
    for pedazo in pedazos:
        pedazo.unlink(missing_ok=True)
    return len(pedazos)
```

Y en `generar`, cambia la linea del parcial para que use la constante:

```python
    parcial = destino.with_name(destino.name + SUFIJO_PARCIAL)
```

- [ ] **Step 4: Corre las pruebas**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proxy_gen.py -q
```

Esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/proxy_gen.py tests/test_proxy_gen.py
git commit -m "Barrer los proxies a medias que deja un cierre de golpe

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: La insignia «en cola», y el menú

**Files:**
- Modify: `src/clasificador_video/ui/clip_sheet.py` (`_BinHeader`, `ClipSheet`)
- Modify: `src/clasificador_video/ui/theme.py`
- Test: `tests/ui/test_clip_sheet.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

```python
def test_un_bin_formado_lo_dice_en_su_insignia(qtbot):
    """Sin esto, pedir un segundo bin no se ve por ningun lado: la insignia
    seguiria diciendo «sin proxies» y pareceria que el clic no hizo nada."""
    sheet = _sheet(qtbot, [_clip(1, "Sala")])
    sheet.item_widgets[0].clip.bin_nombre = "Card B"
    sheet.set_bin_order(["Card B"])

    sheet.set_bin_en_cola("Card B", True)

    assert "en cola" in sheet.bin_header_widget("Card B").proxy_badge.text()


def test_el_que_CORRE_manda_sobre_el_que_espera(qtbot):
    """Un bin no puede estar formado y corriendo a la vez, pero los dos
    estados viven en el mismo widget: si «en cola» ganara, el avance
    «7/23» desapareceria al arrancar."""
    sheet = _sheet(qtbot, [_clip(1, "Sala")])
    sheet.item_widgets[0].clip.bin_nombre = "Card B"
    sheet.set_bin_order(["Card B"])
    sheet.set_bin_en_cola("Card B", True)

    sheet.set_bin_generando("Card B", 7, 23)

    assert "7/23" in sheet.bin_header_widget("Card B").proxy_badge.text()


def test_salir_de_la_fila_devuelve_la_insignia_al_conteo(qtbot):
    sheet = _sheet(qtbot, [_clip(1, "Sala")])
    sheet.item_widgets[0].clip.bin_nombre = "Card B"
    sheet.set_bin_order(["Card B"])
    sheet.set_bin_en_cola("Card B", True)

    sheet.set_bin_en_cola("Card B", False)

    assert "en cola" not in sheet.bin_header_widget("Card B").proxy_badge.text()


def test_el_menu_de_un_bin_formado_ofrece_cancelar(qtbot):
    """El menu miraba solo al que corre: un bin formado seguia ofreciendo
    «Crear proxies del bin…», que es justo lo que ya pediste."""
    sheet = _sheet(qtbot, [_clip(1, "Sala")])
    sheet.item_widgets[0].clip.bin_nombre = "Card B"
    sheet.set_bin_order(["Card B"])
    cabecera = sheet.bin_header_widget("Card B")
    sheet.set_bin_en_cola("Card B", True)

    textos = [a.text() for a in cabecera.menu_de_contexto().actions()]

    assert any("Cancelar" in t for t in textos)
    assert not any("Crear proxies" in t for t in textos)
```

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_clip_sheet.py -q -k "cola or formado or CORRE"
```

Esperado: FAIL con `AttributeError: 'ClipSheet' object has no attribute 'set_bin_en_cola'`.

- [ ] **Step 3: El estado en el encabezado**

En `_BinHeader.__init__`, junto a `self._generando`:

```python
        # formado, esperando turno. Es un estado APARTE de `_generando` y no
        # un valor mas de el: los dos pueden estar puestos en el instante en
        # que a este bin le toca --se le avisa que arranco antes de que
        # salga de la fila-- y ahi tiene que ganar el que corre.
        self._en_cola = False
```

En el método que reparte estados a la insignia (el que hoy empieza con `if self._generando is not None:`), añade DESPUÉS de ese bloque:

```python
        if self._en_cola:
            self._pintar_insignia("en cola", "encolado")
            return
```

Y el método nuevo, junto a `set_generando`:

```python
    def set_en_cola(self, en_cola: bool) -> None:
        """Formado, esperando turno. NO pinta directo: pide el refresco de la
        insignia, igual que `set_generando`, para que al salir de la fila
        vuelva sola al conteo real de proxies enganchados."""
        self._en_cola = bool(en_cola)
        if self._pedir_refresco_de_insignia is not None:
            self._pedir_refresco_de_insignia(self)
```

En `_BinHeader`, donde hoy se copia el estado de otro encabezado (la línea `self._generando = otro._generando`), añade:

```python
        self._en_cola = otro._en_cola
```

En el menú, cambia la condición:

```python
        if self._generando is not None or self._en_cola:
```

- [ ] **Step 4: El puente desde la hoja**

En `ClipSheet`, junto a `set_bin_generando`:

```python
    def set_bin_en_cola(self, nombre: str, en_cola: bool) -> None:
        """El bin esta formado esperando turno. Mismo camino que
        `set_bin_generando`, incluida la copia del encabezado pegado."""
        cabecera = self._bin_headers.get(nombre)
        if cabecera is not None:
            cabecera.set_en_cola(en_cola)
        self._actualizar_encabezado_pegado()
```

- [ ] **Step 5: El estilo**

En `theme.py`, junto a las demás reglas de `#binProxyBadge`:

```python
    /* formado, esperando turno. Apagado a proposito: el que CORRE lleva su
       propio color y tiene que seguir siendo el que salta a la vista con
       cuatro bins pedidos. */
    QLabel#binProxyBadge[estado="encolado"] {{
        background-color: {BG_SURFACE_1};
        color: {TEXT_3};
    }}
```

- [ ] **Step 6: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/clasificador_video/ui/clip_sheet.py src/clasificador_video/ui/theme.py tests/ui/test_clip_sheet.py
git commit -m "El bin formado lo dice, y su menu ofrece cancelar

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: La fila — encolar y arrancar el siguiente

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_bins.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

Usa el helper `_ventana_con_bins` que ya existe en ese archivo, y añade arriba uno nuevo:

```python
def _bin_con_material(window, nombre, indices):
    """Le da al bin una carpeta de verdad para que `carpeta_de_proxies`
    tenga de donde salir."""
    window.bins.agregar(nombre, window.clips[indices[0]].ruta.parent, indices)
```

Las pruebas:

```python
def test_pedir_un_segundo_bin_lo_forma_en_vez_de_rechazarlo(qtbot, monkeypatch):
    """El bug que originó esto: «Espera a que termine, o cancélalo desde el
    menú de ese bin». Con dos tarjetas eso es quedarse vigilando."""
    window = _ventana_con_bins(qtbot)
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", lambda nombre: None)

    window.generar_proxies_de_bin("Card A", preguntar=False)
    window.generar_proxies_de_bin("Card B", preguntar=False)

    assert window._cola_de_proxies == ["Card B"]


def test_pedir_dos_veces_el_mismo_bin_no_lo_mete_dos_veces(qtbot, monkeypatch):
    window = _ventana_con_bins(qtbot)
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", lambda nombre: None)

    window.generar_proxies_de_bin("Card B", preguntar=False)
    window.generar_proxies_de_bin("Card B", preguntar=False)
    window.generar_proxies_de_bin("Card B", preguntar=False)

    assert window._cola_de_proxies.count("Card B") <= 1


def test_el_bin_formado_lo_dice_en_la_hoja(qtbot, monkeypatch):
    window = _ventana_con_bins(qtbot)
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", lambda nombre: None)
    avisos = []
    monkeypatch.setattr(window.clip_sheet, "set_bin_en_cola",
                        lambda nombre, en_cola: avisos.append((nombre, en_cola)))

    window.generar_proxies_de_bin("Card A", preguntar=False)
    window.generar_proxies_de_bin("Card B", preguntar=False)

    assert ("Card B", True) in avisos


def test_al_terminar_uno_arranca_el_siguiente_solo(qtbot, monkeypatch):
    """Es todo el punto: dejas los bins pedidos y te vas."""
    window = _ventana_con_bins(qtbot)
    arrancados = []
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", arrancados.append)
    window.generar_proxies_de_bin("Card A", preguntar=False)
    window.generar_proxies_de_bin("Card B", preguntar=False)

    window._arrancar_siguiente_de_la_fila()

    assert arrancados == ["Card A", "Card B"]
    assert window._cola_de_proxies == []
```

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q -k "forma or dos_veces or formado_lo_dice or siguiente_solo"
```

Esperado: FAIL con `AttributeError: '_cola_de_proxies'`.

- [ ] **Step 3: Parte `generar_proxies_de_bin` en dos**

Hoy esa función hace tres cosas: decide si se puede, arma la lista y arranca. Se parte para que la fila pueda arrancar una tanda sin volver a preguntar.

En `__init__`, junto a `self._generando_proxies`:

```python
        # Los bins formados, esperando turno. Se guarda el NOMBRE y no la
        # lista de clips: entre que lo pides y que arranca puedes arrastrarle
        # clips, engancharle proxies a mano o quitarle material, y una lista
        # de antes describiria un bin que ya no es ese. La lista se calcula
        # cuando le toca (ver el spec).
        self._cola_de_proxies: list[str] = []
        # Lo que llevan TODAS las tandas de esta fila, para el cartel unico
        # del final. Se vacia cuando la fila arranca desde cero.
        self._resumen_de_la_fila = {"creados": 0, "fallidos": []}
```

Reemplaza el bloque que hoy rechaza el segundo bin:

```python
        if self._generando_proxies is not None:
            QMessageBox.information(
                self, "Ya se están creando", ...
            )
            return
```

por:

```python
        if self._esta_pedido(nombre_de_bin):
            QMessageBox.information(
                self, "Ya está pedido",
                f"Los proxies de «{nombre_de_bin}» ya están pedidos. "
                "Puedes cancelarlos desde el menú de ese bin.",
            )
            return
```

y al final de la función, donde hoy arranca la tanda —desde `self._generacion_de_proxies += 1` hasta el `for i in pendientes:`— reemplaza por:

```python
        if self._generando_proxies is not None:
            # ya hay una corriendo: este se forma. La lista de clips que se
            # acaba de calcular NO se guarda -- se vuelve a calcular cuando
            # le toque, porque para entonces el bin pudo cambiar.
            self._cola_de_proxies.append(nombre_de_bin)
            self.clip_sheet.set_bin_en_cola(nombre_de_bin, True)
            return
        self._resumen_de_la_fila = {"creados": 0, "fallidos": []}
        self._arrancar_tanda_de_proxies(nombre_de_bin)

    def _esta_pedido(self, nombre_de_bin: str) -> bool:
        """Ya corriendo, o ya formado. Pedirlo otra vez no lo mete dos veces:
        la segunda tanda no tendria nada que hacer --la primera ya se llevo
        los que faltaban-- y el bin saldria de la fila dos veces."""
        corriendo = (self._generando_proxies is not None
                     and self._generando_proxies["bin"] == nombre_de_bin)
        return corriendo or nombre_de_bin in self._cola_de_proxies

    def _arrancar_tanda_de_proxies(self, nombre_de_bin: str) -> None:
        """Arranca la tanda de ESE bin, sin preguntar nada.

        La lista se calcula AQUI y no al pedirlo: es el momento en que de
        verdad se va a trabajar, y para entonces el bin puede tener otros
        clips (ver el spec).
        """
        indices = [i for i in self.bins.clips_de(nombre_de_bin)
                   if 0 <= i < len(self.clips)]
        if not indices:
            self._arrancar_siguiente_de_la_fila()
            return
        carpeta = proxy_gen.carpeta_de_proxies(self.clips[indices[0]].ruta.parent)
        candidatos = [i for i in indices if self.clips[i].ruta_proxy is None]
        pendientes = [
            i for i in candidatos
            if not proxy_gen.ruta_de_proxy(self.clips[i].ruta, carpeta).exists()
        ]
        if not pendientes:
            self._arrancar_siguiente_de_la_fila()
            return
        self._generacion_de_proxies += 1
        self._generando_proxies = {
            "bin": nombre_de_bin,
            "generacion": self._generacion_de_proxies,
            "total": len(pendientes),
            "hechos": 0,
            "fallidos": [],
            "cancelado": False,
            "carpeta": carpeta,
        }
        self.clip_sheet.set_bin_en_cola(nombre_de_bin, False)
        self._pintar_avance_de_proxies()
        estado = self._generando_proxies
        for i in pendientes:
            self._generacion_pool.start(_GeneracionDeProxyJob(
                estado["generacion"], i, self.clips[i].ruta, carpeta,
                # se lee al empezar ESE clip, no al encolarlo
                lambda e=estado: e["cancelado"],
                self._señales_de_trabajos,
            ))

    def _arrancar_siguiente_de_la_fila(self) -> None:
        """El de adelante de la fila, si hay. Se llama al terminar una tanda
        y también cuando una no tenía nada que hacer -- si no, la fila se
        quedaría trabada detrás de un bin que ya tenía todos sus proxies.
        """
        while self._cola_de_proxies:
            nombre = self._cola_de_proxies.pop(0)
            self.clip_sheet.set_bin_en_cola(nombre, False)
            if nombre in self.bins.nombres():
                self._arrancar_tanda_de_proxies(nombre)
                return
```

Ojo con el `while`: un bin que se fue del proyecto mientras esperaba turno se salta, y se sigue con el que sigue. Con un `if` la fila se quedaría trabada.

Ojo también con la recursión: `_arrancar_tanda_de_proxies` llama a `_arrancar_siguiente_de_la_fila` cuando no hay nada que hacer, y esa vuelve a llamar a la primera. La fila es finita y cada vuelta saca un elemento, así que termina.

- [ ] **Step 4: Corre las pruebas**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q
```

Esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_bins.py
git commit -m "Los bins se forman en vez de rechazarse

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Cancelar es por bin

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_bins.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

```python
def test_cancelar_un_bin_formado_no_toca_al_que_corre(qtbot, monkeypatch):
    window = _ventana_con_bins(qtbot)
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", lambda nombre: None)
    window.generar_proxies_de_bin("Card A", preguntar=False)
    window._generando_proxies = {"bin": "Card A", "generacion": 1, "total": 3,
                                 "hechos": 1, "fallidos": [], "cancelado": False,
                                 "carpeta": Path("/p")}
    window.generar_proxies_de_bin("Card B", preguntar=False)

    window.cancelar_generacion_de_proxies("Card B")

    assert window._cola_de_proxies == []
    assert window._generando_proxies["cancelado"] is False


def test_cancelar_el_que_corre_no_vacia_la_fila(qtbot, monkeypatch):
    """Cancelas el que corre porque te equivocaste de tarjeta; los otros tres
    que pediste siguen siendo lo que querias."""
    window = _ventana_con_bins(qtbot)
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", lambda nombre: None)
    window.generar_proxies_de_bin("Card A", preguntar=False)
    window._generando_proxies = {"bin": "Card A", "generacion": 1, "total": 3,
                                 "hechos": 1, "fallidos": [], "cancelado": False,
                                 "carpeta": Path("/p")}
    window.generar_proxies_de_bin("Card B", preguntar=False)

    window.cancelar_generacion_de_proxies("Card A")

    assert window._generando_proxies["cancelado"] is True
    assert window._cola_de_proxies == ["Card B"]


def test_cancelar_un_bin_que_ni_pediste_no_hace_nada(qtbot, monkeypatch):
    window = _ventana_con_bins(qtbot)
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", lambda nombre: None)
    window.generar_proxies_de_bin("Card A", preguntar=False)
    window._generando_proxies = {"bin": "Card A", "generacion": 1, "total": 3,
                                 "hechos": 1, "fallidos": [], "cancelado": False,
                                 "carpeta": Path("/p")}

    window.cancelar_generacion_de_proxies("Card B")

    assert window._generando_proxies["cancelado"] is False
```

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q -k cancelar_un_bin_formado
```

Esperado: FAIL — hoy `cancelar_generacion_de_proxies` ignora el nombre y cancela lo que corra.

- [ ] **Step 3: Que mire el nombre**

Reemplaza `cancelar_generacion_de_proxies` entera:

```python
    def cancelar_generacion_de_proxies(self, nombre_de_bin: str = "") -> None:
        """Cancela ESE bin y nada mas -- el menu desde el que se llama es el
        de ese bin, y llevarse los otros tres por delante seria hacer algo
        que el boton no dice.

        Si es el que corre: lo que ya se genero se queda enganchado, lo que
        faltaba no se hace, y el siguiente de la fila arranca solo cuando
        este termine de recoger. El que este a medias termina --cortar
        ffmpeg a la mitad deja un archivo truncado-- pero es uno solo.

        Si todavia esperaba turno: sale de la fila y su insignia vuelve al
        conteo real.
        """
        if nombre_de_bin in self._cola_de_proxies:
            self._cola_de_proxies.remove(nombre_de_bin)
            self.clip_sheet.set_bin_en_cola(nombre_de_bin, False)
            return
        if (self._generando_proxies is not None
                and self._generando_proxies["bin"] == nombre_de_bin):
            self._generando_proxies["cancelado"] = True
```

- [ ] **Step 4: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_bins.py
git commit -m "Cancelar es por bin, no por fila

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Un solo cartel al final

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py` (`_terminar_generacion_de_proxies`)
- Test: `tests/ui/test_main_window_bins.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

```python
def _carteles(monkeypatch):
    """Recoge los QMessageBox en vez de mostrarlos."""
    from PySide6.QtWidgets import QMessageBox
    vistos = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: vistos.append(("warning", a[1], a[2])))
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: vistos.append(("info", a[1], a[2])))
    return vistos


def test_con_dos_bins_sale_UN_cartel_y_no_dos(qtbot, monkeypatch):
    """Cuatro bins formados serian cuatro carteles seguidos, y cuando ya
    nadie esta viendo la pantalla."""
    window = _ventana_con_bins(qtbot)
    vistos = _carteles(monkeypatch)
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", lambda nombre: None)
    window._resumen_de_la_fila = {"creados": 0, "fallidos": []}
    window._cola_de_proxies = ["Card B"]
    window._generando_proxies = {"bin": "Card A", "generacion": 1, "total": 2,
                                 "hechos": 2, "fallidos": [], "cancelado": False,
                                 "carpeta": Path("/p")}

    window._terminar_generacion_de_proxies()

    assert vistos == []          # todavía queda uno en la fila


def test_el_cartel_del_final_suma_todas_las_tandas(qtbot, monkeypatch):
    window = _ventana_con_bins(qtbot)
    vistos = _carteles(monkeypatch)
    window._resumen_de_la_fila = {"creados": 20, "fallidos": []}
    window._cola_de_proxies = []
    window._generando_proxies = {"bin": "Card A", "generacion": 1, "total": 3,
                                 "hechos": 3, "fallidos": [], "cancelado": False,
                                 "carpeta": Path("/p")}

    window._terminar_generacion_de_proxies()

    assert len(vistos) == 1
    assert "23" in vistos[0][2]


def test_cancelarlo_todo_no_saca_cartel(qtbot, monkeypatch):
    """Cancelar fue decision suya: no hace falta confirmarsela."""
    window = _ventana_con_bins(qtbot)
    vistos = _carteles(monkeypatch)
    window._resumen_de_la_fila = {"creados": 0, "fallidos": []}
    window._cola_de_proxies = []
    window._generando_proxies = {"bin": "Card A", "generacion": 1, "total": 3,
                                 "hechos": 1, "fallidos": [], "cancelado": True,
                                 "carpeta": Path("/p")}

    window._terminar_generacion_de_proxies()

    assert vistos == []


def test_lo_que_alcanzo_a_crear_un_bin_cancelado_si_cuenta(qtbot, monkeypatch):
    """Se hicieron y estan enganchados; no mencionarlos seria mentir en el
    otro sentido."""
    window = _ventana_con_bins(qtbot)
    vistos = _carteles(monkeypatch)
    window._resumen_de_la_fila = {"creados": 0, "fallidos": []}
    window._cola_de_proxies = []
    window._generando_proxies = {"bin": "Card A", "generacion": 1, "total": 10,
                                 "hechos": 4, "fallidos": [], "cancelado": True,
                                 "carpeta": Path("/p")}

    window._terminar_generacion_de_proxies()

    assert window._resumen_de_la_fila["creados"] == 4
```

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q -k "UN_cartel or suma_todas or cancelarlo_todo or alcanzo_a_crear"
```

Esperado: FAIL — hoy el cartel sale al terminar cada tanda.

- [ ] **Step 3: Acumular, y avisar solo al vaciarse**

Reemplaza `_terminar_generacion_de_proxies` entera:

```python
    def _terminar_generacion_de_proxies(self) -> None:
        estado = self._generando_proxies
        if estado is None:
            return
        self._generando_proxies = None
        # apagar el aviso: la insignia vuelve sola al conteo real
        self.clip_sheet.set_bin_generando(estado["bin"], None)
        # Las portadas que quedaron esperando se piden ahora, salga como
        # salga la generación: al cancelar a la mitad, o si algún proxy
        # falló, esos clips se quedarían en gris para siempre esperando algo
        # que ya no va a llegar.
        self._schedule_thumbnails(self.bins.clips_de(estado["bin"]))
        # Lo que esta tanda aporta al cartel del final. Los que ALCANZO a
        # crear cuentan aunque la hayas cancelado: se hicieron y estan
        # enganchados, y callarlos seria mentir en el otro sentido.
        self._resumen_de_la_fila["creados"] += (
            estado["hechos"] - len(estado["fallidos"])
        )
        self._resumen_de_la_fila["fallidos"].extend(estado["fallidos"])
        if self._cola_de_proxies:
            self._arrancar_siguiente_de_la_fila()
            return
        self._avisar_del_final_de_la_fila()

    def _avisar_del_final_de_la_fila(self) -> None:
        """UN cartel, cuando la fila se vacía. Con cuatro bins pedidos, uno
        por tanda serían cuatro carteles seguidos y probablemente cuando ya
        nadie está viendo la pantalla.

        Cancelar no agrega renglón: fue una decisión de Bruno y no hace falta
        confirmársela. Y si no se creó ni un proxy no hay cartel — un cartel
        que dice «0 creados» es ruido.
        """
        resumen = self._resumen_de_la_fila
        self._resumen_de_la_fila = {"creados": 0, "fallidos": []}
        if not resumen["creados"] and not resumen["fallidos"]:
            return
        if resumen["fallidos"]:
            cuantos = len(resumen["fallidos"])
            primero = resumen["fallidos"][0][1]
            QMessageBox.warning(
                self, "Algunos no se pudieron crear",
                f"{resumen['creados']} proxies creados, {cuantos} fallaron."
                f"\n\n{primero}",
            )
            return
        QMessageBox.information(
            self, "Proxies listos",
            f"{resumen['creados']} proxies creados.",
        )
```

- [ ] **Step 4: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS. Aquí es donde se nota si alguna prueba vieja esperaba el cartel por tanda; si alguna falla, actualízala al comportamiento nuevo y di en el commit cuál era.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_bins.py
git commit -m "Un solo cartel al vaciarse la fila, no uno por bin

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Barrer al empezar, y tirar la fila cuando el proyecto cambia

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_bins.py`

- [ ] **Step 1: Escribe las pruebas que fallan**

```python
def test_al_empezar_la_tanda_se_barren_los_parciales(qtbot, monkeypatch, tmp_path):
    window = _ventana_con_bins(qtbot)
    barridas = []
    monkeypatch.setattr(proxy_gen, "barrer_parciales", lambda c: barridas.append(c))

    window._arrancar_tanda_de_proxies("Card A")

    assert barridas


def test_quitar_un_bin_vacia_tambien_la_fila(qtbot, monkeypatch):
    """La fila guarda nombres de bin, y los trabajos en vuelo enganchan por
    indice de clip: quitar un bin corre los indices y lo que llegue ya no
    describe a nadie. La tanda ya se tiraba entera; la fila tambien."""
    window = _ventana_con_bins(qtbot)
    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", lambda nombre: None)
    window.generar_proxies_de_bin("Card A", preguntar=False)
    window._generando_proxies = {"bin": "Card A", "generacion": 1, "total": 3,
                                 "hechos": 1, "fallidos": [], "cancelado": False,
                                 "carpeta": Path("/p")}
    window.generar_proxies_de_bin("Card B", preguntar=False)

    window._descartar_generacion_de_proxies()

    assert window._cola_de_proxies == []
```

Añade `from clasificador_video import proxy_gen` al principio del archivo si no está.

- [ ] **Step 2: Corre las pruebas y comprueba que fallan**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_bins.py -q -k "barren_los_parciales or vacia_tambien"
```

Esperado: FAIL.

- [ ] **Step 3: Barrer, y vaciar la fila**

En `_arrancar_tanda_de_proxies`, justo después de calcular `carpeta` y ANTES de calcular `pendientes`:

```python
        # Los pedazos de una tanda que se corto de golpe. Aqui y no al pedir
        # el bin: este es el unico momento en que se sabe que no hay ningun
        # `.parcial` en vuelo -- se genera de uno en uno, y la fila arranca
        # la siguiente solo cuando la anterior termino. Dos bins de la misma
        # carpeta comparten carpeta de proxies, asi que barrer en cualquier
        # otro momento le pisaria el archivo al que esta escribiendo.
        proxy_gen.barrer_parciales(carpeta)
```

En `_descartar_generacion_de_proxies`, antes del `estado = self._generando_proxies`:

```python
        # La fila entera se va con la tanda, y por el mismo motivo: guarda
        # nombres de bin, pero lo que arrancaria de ella engancha por INDICE
        # de clip, y los indices se acaban de correr.
        for nombre in self._cola_de_proxies:
            self.clip_sheet.set_bin_en_cola(nombre, False)
        self._cola_de_proxies = []
        self._resumen_de_la_fila = {"creados": 0, "fallidos": []}
```

- [ ] **Step 4: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_bins.py
git commit -m "Barrer los parciales al empezar, y tirar la fila con la tanda

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Barrido final — el recorrido completo, el pixel y la documentación

**Files:**
- Test: `tests/ui/test_main_window_bins.py`
- Modify: `README.md`, `docs/superpowers/CONTEXTO-Y-METAS.md`

- [ ] **Step 1: La prueba del recorrido completo**

```python
def test_el_recorrido_completo_de_la_fila(qtbot, monkeypatch):
    """Pides dos bins, corren en orden, y al final UN cartel con la suma."""
    window = _ventana_con_bins(qtbot)
    vistos = _carteles(monkeypatch)
    arrancados = []

    def arrancar(nombre):
        arrancados.append(nombre)
        window._generando_proxies = {
            "bin": nombre, "generacion": len(arrancados), "total": 2,
            "hechos": 2, "fallidos": [], "cancelado": False,
            "carpeta": Path("/p"),
        }

    monkeypatch.setattr(window, "_arrancar_tanda_de_proxies", arrancar)

    window.generar_proxies_de_bin("Card A", preguntar=False)
    window.generar_proxies_de_bin("Card B", preguntar=False)
    window._terminar_generacion_de_proxies()      # termina Card A
    assert arrancados == ["Card A", "Card B"]
    assert vistos == []
    window._terminar_generacion_de_proxies()      # termina Card B

    assert len(vistos) == 1
    assert "4" in vistos[0][2]
```

- [ ] **Step 2: Corre la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: PASS.

- [ ] **Step 3: Comprobación visual de la insignia «en cola»**

No basta con que la prueba pase. Guarda esto en el scratchpad de la sesión (NO en el repo) y córrelo:

```python
import sys
from PySide6.QtWidgets import QApplication
from clasificador_video.ui import theme
from clasificador_video.ui.clip_sheet import ClipSheet, ClipThumbnail, SIN_CLASIFICAR
from pathlib import Path

app = QApplication([])
app.setStyleSheet(theme.build_stylesheet())

def clip(n, binn):
    return ClipThumbnail(path=Path(f"/x/C{n:04d}.MP4"), room_label=SIN_CLASIFICAR,
                         flag="none", room_color=None, numero=n,
                         aspect_ratio=16/9, bin_nombre=binn)

hoja = ClipSheet()
hoja.resize(900, 700)
hoja.set_bin_order(["Card A", "Card B", "Card C"])
hoja.set_clips([clip(1, "Card A"), clip(2, "Card B"), clip(3, "Card C")])
hoja.show()
for _ in range(8):
    app.processEvents()
hoja.set_bin_generando("Card A", 7, 23)
hoja.set_bin_en_cola("Card B", True)
hoja.set_bin_en_cola("Card C", True)
for _ in range(8):
    app.processEvents()
hoja.grab().save(sys.argv[1] + "/cola.png")
```

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python <ruta>/cola.py <ruta-del-scratchpad>
```

Abre el PNG con la herramienta de lectura de archivos. Confirma tres cosas: «Card A» dice el avance `7/23`, «Card B» y «Card C» dicen «en cola», y el que corre salta más a la vista que los que esperan.

- [ ] **Step 4: Actualiza la documentación**

En `README.md`, en la parte de proxies, después de donde se explica «Crear los proxies»:

```markdown
**Puedes pedir varios bins seguidos.** El primero arranca y los demás se
forman: cada uno dice «en cola» en su insignia y arranca solo cuando le toca.
Al terminar todos sale un aviso con la cuenta. Cancelar desde el menú de un
bin cancela solo ese; los demás siguen.
```

En `docs/superpowers/CONTEXTO-Y-METAS.md`, en la sección de lo que se cerró, añade un punto explicando que la fila existe y que **reanudar tras cancelar ya funcionaba desde antes** — para que no se vuelva a "construir".

- [ ] **Step 5: Commit**

```bash
git add tests/ui/test_main_window_bins.py README.md docs/superpowers/CONTEXTO-Y-METAS.md
git commit -m "El recorrido completo de la fila, y la documentacion al dia

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
