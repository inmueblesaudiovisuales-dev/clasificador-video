# La guía de edición por unidad — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la guía de edición ordene los cuartos de **una unidad a la vez**
(selector en la pantalla, pre-ordenar con DeepSeek, reacomodo a mano), que ese
orden se guarde por unidad, y que el plugin numere en Premiere la carpeta de la
unidad y la del cuarto.

**Architecture:** El estado de guía deja de ser uno solo y pasa a ser un
diccionario por unidad (`""` = sin unidad). La pantalla guarda un tablero por
unidad y cambia entre ellos con un selector; `main_window` alimenta cada
tablero con los cuartos de su catálogo (`room_selections[unidad]`) y aplica el
orden aceptado a ese catálogo. El manifest manda las guías por unidad, y el
plugin numera unidad y cuarto con ellas. Un proyecto sin unidades usa la llave
`""` y se comporta exactamente como hoy.

**Tech Stack:** Python 3 / PySide6, JavaScript sin build (UXP), pytest +
`QT_QPA_PLATFORM=offscreen`, `node uxp-plugin/pruebas/correr.js`.

Spec: `docs/superpowers/specs/2026-09-21-guia-de-edicion-por-unidad-design.md`

---

### Task 1: `manifest.Guia` lleva las unidades

**Files:** `src/clasificador_video/manifest.py`, `tests/test_manifest.py`

- [ ] Prueba: `Guia(orden=["Cocina"]).to_dict() == {"orden": ["Cocina"]}` (sin
  `unidades`, retro-compatible).
- [ ] Prueba: `Guia(orden=[], unidades=[{"nombre": "Casa A", "orden": ["Cocina"]}])`
  → `to_dict()["unidades"] == [{"nombre": "Casa A", "orden": ["Cocina"]}]`.
- [ ] Implementar `unidades: list[dict]` en `Guia` y en `to_dict` (solo si no
  está vacío).

### Task 2: Persistir `guias_por_unidad` en el `.cvproj`

**Files:** `src/clasificador_video/proyecto.py`, `tests/test_proyecto.py`

- [ ] Prueba: `a_dict(...)` sin el parámetro → `datos["guias_por_unidad"] == {}`.
- [ ] Prueba: con `guias_por_unidad={"Casa A": {"orden": ["Cocina"]}}` → viaja.
- [ ] Implementar el parámetro opcional y la llave.

### Task 3: Restaurar las guías por unidad al abrir

**Files:** `src/clasificador_video/app.py`, `tests/test_app.py`

- [ ] Prueba: `_guias_por_unidad_de(data)` con `guias_por_unidad` devuelve el
  dict; con solo `guia` viejo, devuelve `{"": {...}}`; con basura, `{}`.
- [ ] Implementar `_guias_por_unidad_de` y usarlo en `_poblar_ventana` en vez
  de `restaurar_guia(data.get("guia"))` (que se conserva para leer el formato
  viejo).

### Task 4: `PantallaGuia` — selector y tablero por unidad

**Files:** `src/clasificador_video/ui/pantalla_guia.py`,
`tests/ui/test_pantalla_guia.py`, `src/clasificador_video/ui/theme.py`

- [ ] Pruebas: `configurar_unidades(["Casa A", "Casa B"], "Casa A")` muestra el
  selector; `unidad_actual()`; cambiar de unidad conserva el tablero;
  `poner_cuartos_reales` y `mostrar_clasificacion` operan sobre la unidad
  actual; el botón dice "Pre-ordenar".
- [ ] Implementar `_SelectorDeUnidades`, el estado `_tableros`/`_unidad`, y el
  QSS de los chips.

### Task 5: `main_window` — clasificar/aceptar/guardar por unidad

**Files:** `src/clasificador_video/ui/main_window.py`,
`tests/ui/test_main_window_guia_unidad.py` (nuevo)

- [ ] Pruebas: abrir la guía con unidades lista los cuartos de cada una;
  aceptar el orden de una unidad reordena SU catálogo; guardar y reabrir
  conserva las guías por unidad; «guía vieja» se revisa por unidad.
- [ ] Implementar `_unidades_para_la_guia`, `_guias_por_unidad`,
  `_cuartos_de_la_guia_por_unidad`, y ajustar `_abrir_pantalla_de_guia`,
  `pedir_clasificacion`, `_mostrar_guia`, `aceptar_orden_de_la_guia`,
  `_guia_cuadrada_con_el_rail`, `_guia_para_la_sesion`,
  `restaurar_guias`, `guia_quedo_vieja`, `aviso_de_guia_vieja`,
  `_guia_para_el_manifest` y `_datos_del_proyecto`.

### Task 6: El plugin numera unidad y cuarto

**Files:** `uxp-plugin/js/estructura.js`, `uxp-plugin/js/processManifest.js`,
`uxp-plugin/pruebas/estructura.pruebas.js`,
`uxp-plugin/pruebas/numeroDeCuarto.pruebas.js`

- [ ] Pruebas: `caminoDelClip` con `{unidades:[...]}` numera unidad y cuarto;
  sin `unidades` se comporta como hoy; una unidad que ya existía sin número se
  reusa (no se duplica).
- [ ] Implementar `caminoDelClip(categoryPath, guia)` y usar `resolverCuarto`
  también para la unidad.

### Task 7: Corrida final y verificación visual

- [ ] `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q`
- [ ] `node uxp-plugin/pruebas/correr.js`
- [ ] PNG de la guía con dos unidades y su selector, leído.
