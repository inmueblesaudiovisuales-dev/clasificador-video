# Abrir la carpeta de iCloud en Finder - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un botón "Abrir en Finder" en la barra de arriba, visible solo
cuando el proyecto tiene una carpeta de iCloud vinculada, que la abre en
Finder al apretarlo.

**Architecture:** `TitleBar` gana un botón escondido por defecto, una
señal `abrir_en_finder_requested`, y un setter `set_carpeta_de_icloud_disponible(bool)`
que lo muestra u oculta. `MainWindow.set_carpeta_de_icloud` -- el único
lugar que ya asigna esa carpeta, tanto al crear como al abrir un proyecto
-- llama a ese setter cada vez, y conecta la señal a un método que abre
la carpeta con `QDesktopServices`.

**Tech Stack:** Python 3, PySide6 (Qt), pytest + pytest-qt, `QT_QPA_PLATFORM=offscreen`.

**Spec:** `docs/superpowers/specs/2026-09-23-abrir-carpeta-icloud-en-finder-design.md`

---

## Cómo correr la suite completa

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Y para un archivo puntual:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ruta/al/archivo.py -q
```

---

### Task 1: `TitleBar` — el botón, escondido por defecto, y su señal

**Files:**
- Modify: `src/clasificador_video/ui/title_bar.py`
- Test: `tests/ui/test_title_bar.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Agregar en `tests/ui/test_title_bar.py`, junto a
`test_el_boton_de_proxies_emite_su_senal`:

```python
def test_el_boton_de_abrir_en_finder_esta_escondido_por_defecto(qtbot):
    bar = _bar(qtbot)
    bar.show()
    qtbot.waitExposed(bar)

    assert not bar.icloud_button.isVisible()


def test_set_carpeta_de_icloud_disponible_muestra_el_boton(qtbot):
    bar = _bar(qtbot)
    bar.show()
    qtbot.waitExposed(bar)

    bar.set_carpeta_de_icloud_disponible(True)

    assert bar.icloud_button.isVisible()


def test_set_carpeta_de_icloud_disponible_false_lo_esconde(qtbot):
    bar = _bar(qtbot)
    bar.show()
    qtbot.waitExposed(bar)
    bar.set_carpeta_de_icloud_disponible(True)

    bar.set_carpeta_de_icloud_disponible(False)

    assert not bar.icloud_button.isVisible()


def test_el_boton_de_abrir_en_finder_emite_su_senal(qtbot):
    bar = _bar(qtbot)
    with qtbot.waitSignal(bar.abrir_en_finder_requested):
        bar.icloud_button.click()
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_title_bar.py -k icloud -q`
Expected: FAIL con `AttributeError: 'TitleBar' object has no attribute 'icloud_button'`

- [ ] **Step 3: Agregar el botón, la señal y el setter**

En `src/clasificador_video/ui/title_bar.py`, junto a las demás señales
(cerca de la línea 57, después de `traer_de_vuelta_requested = Signal()`):

```python
    traer_de_vuelta_requested = Signal()
    abrir_en_finder_requested = Signal()
```

Junto a donde se crea `self.proxies_button` (cerca de la línea 132):

```python
        self.proxies_button = _boton("Proxies", "", "railButton")
        # Solo se ve si el proyecto tiene una carpeta de iCloud vinculada
        # (spec 2026-09-23-abrir-carpeta-icloud-en-finder-design.md) --
        # empieza escondido, igual que `traer_button`.
        self.icloud_button = _boton("Abrir en Finder", "", "railButton")
        self.icloud_button.hide()
```

Junto a las conexiones de clicks (cerca de la línea 153, donde está
`self.proxies_button.clicked.connect(...)`):

```python
        self.proxies_button.clicked.connect(self.proxies_requested.emit)
        self.icloud_button.clicked.connect(self.abrir_en_finder_requested.emit)
```

Junto a `layout.addWidget(self.proxies_button)` (cerca de la línea 167):

```python
        layout.addWidget(self.proxies_button)
        layout.addWidget(self.icloud_button)
```

Y agregar el setter, junto a `set_estado_de_entrega` (cerca de la línea 172):

```python
    def set_carpeta_de_icloud_disponible(self, disponible: bool) -> None:
        """Muestra u oculta "Abrir en Finder" -- solo existe una carpeta de
        iCloud que abrir en los proyectos creados con "Con folio…" (spec
        2026-09-23-abrir-carpeta-icloud-en-finder-design.md)."""
        self.icloud_button.setVisible(disponible)

```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_title_bar.py -q`
Expected: PASS (todo el archivo)

- [ ] **Step 5: Commit**

```bash
git add src/clasificador_video/ui/title_bar.py tests/ui/test_title_bar.py
git commit -m "$(cat <<'EOF'
TitleBar: botón "Abrir en Finder", escondido salvo con carpeta de iCloud

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `MainWindow` — mostrar el botón y abrir la carpeta al apretarlo

**Files:**
- Modify: `src/clasificador_video/ui/main_window.py`
- Test: `tests/ui/test_main_window_carpeta_de_proxies.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Agregar en `tests/ui/test_main_window_carpeta_de_proxies.py`, junto a
`test_la_carpeta_de_icloud_viaja_con_el_proyecto`:

```python
def test_set_carpeta_de_icloud_muestra_el_boton_de_finder(ventana, qtbot, tmp_path):
    ventana.show()
    qtbot.waitExposed(ventana)

    ventana.set_carpeta_de_icloud(tmp_path / "IAV-2609.10-A")

    assert ventana.title_bar.icloud_button.isVisible()


def test_sin_carpeta_de_icloud_el_boton_queda_escondido(ventana, qtbot):
    ventana.show()
    qtbot.waitExposed(ventana)

    assert not ventana.title_bar.icloud_button.isVisible()


def test_apretar_abrir_en_finder_abre_la_carpeta(ventana, tmp_path, monkeypatch):
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    carpeta = tmp_path / "IAV-2609.10-A"
    ventana.set_carpeta_de_icloud(carpeta)
    abiertas = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: abiertas.append(url))

    ventana.title_bar.abrir_en_finder_requested.emit()

    assert abiertas == [QUrl.fromLocalFile(str(carpeta))]
```

- [ ] **Step 2: Correr las pruebas y comprobar que fallan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_carpeta_de_proxies.py -k finder -q`
Expected: FAIL (el botón nunca se muestra: `set_carpeta_de_icloud` todavía no avisa al `title_bar`, y la señal no está conectada a nada)

- [ ] **Step 3: Importar `QDesktopServices`/`QUrl`, avisar al `title_bar`, y conectar la señal**

En `src/clasificador_video/ui/main_window.py`, en los imports de Qt (cerca
de la línea 13-24):

```python
from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
```

En `set_carpeta_de_icloud` (la que se agregó en el plan anterior, cerca
de la línea 3537):

```python
    def set_carpeta_de_icloud(self, carpeta: Path | None) -> None:
        self._carpeta_de_icloud = Path(carpeta) if carpeta is not None else None
        self.title_bar.set_carpeta_de_icloud_disponible(self._carpeta_de_icloud is not None)
        self._autosave()
```

Y junto a las demás conexiones de `self.title_bar` en `__init__` (cerca
de la línea 984, después de
`self.title_bar.traer_de_vuelta_requested.connect(self._al_pedir_traer_de_vuelta)`):

```python
        self.title_bar.traer_de_vuelta_requested.connect(self._al_pedir_traer_de_vuelta)
        self.title_bar.abrir_en_finder_requested.connect(self._al_abrir_carpeta_de_icloud_en_finder)
```

Y agregar el método nuevo, junto a `_carpeta_de_proxies_en_icloud` (cerca
de la línea 3541):

```python
    def _al_abrir_carpeta_de_icloud_en_finder(self) -> None:
        if self._carpeta_de_icloud is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._carpeta_de_icloud)))
```

- [ ] **Step 4: Correr las pruebas y comprobar que pasan**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_carpeta_de_proxies.py -q`
Expected: PASS (todo el archivo)

- [ ] **Step 5: Correr la suite completa**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_carpeta_de_proxies.py
git commit -m "$(cat <<'EOF'
Mostrar "Abrir en Finder" y abrir la carpeta de iCloud al apretarlo

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
