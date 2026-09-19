# Vista de proyectos activos en Drive — diseño

*(Spec del 2026-09-19. Brainstorming en chat + mockup HTML verificado en
navegador, sin tocar código. Revisa una decisión de
`2026-09-18-entrega-a-editor-externo-ui-design.md` §4 con una razón nueva:
ver ahí por qué.)*

## 1. Por qué se reabre la decisión de "Traer de vuelta vive dentro del proyecto"

La spec del 18 de septiembre decidió a propósito que "Traer de vuelta" solo
existe dentro del proyecto abierto, no en la lista de inicio. La razón nueva
que trae Bruno: puede tener **varios proyectos activos en Drive a la vez**, y
quiere verlos y actuar sobre ellos sin abrir cada uno. No es un descuido de
la spec anterior — es la misma pregunta con un caso de uso que antes no
estaba sobre la mesa.

## 2. El ciclo real de una entrega (cambia `entrega.py`)

Al platicarlo salió que el ciclo de Bruno tiene un paso más de los que
`EstadoEntrega` modela hoy:

1. Bruno sube a Drive → **`CON_EDITOR`**.
2. El editor corta y sube su versión → sigue **`CON_EDITOR`**, con el aviso
   de que ya hay algo esperando (esto ya existe, no cambia).
3. Bruno aprieta "Traer de vuelta" → pasa a un estado nuevo,
   **`EN_REVISION`**. Hoy esto BORRA la entrega entera (`self._entrega = None`
   en `main_window.py::_on_drive_traida_lista`); con este cambio ya no la
   borra — el proyecto sigue "activo".
4. Bruno revisa el corte. Si necesita cambios, sube de nuevo desde dentro
   del proyecto ("Subir de nuevo") → vuelve a **`CON_EDITOR`**, otra vuelta.
5. Cuando el cliente aprueba, Bruno aprieta **"Ya entregado"** (solo existe
   en la vista nueva) → se cierra: la entrega se limpia (mismo efecto que
   hoy tiene "Traer de vuelta": vuelve a `SIN_SUBIR`, sin marca). **No toca
   Drive para nada** — es una marca de organización de Bruno, no una acción
   de red.

`EstadoEntrega` gana una constante más:

```python
EN_REVISION = "en_revision"
```

Nada más cambia de forma del dataclass — mismos campos (`subido_en`,
`drive_folder_id`, etc.), solo un valor más para `estado`.

## 3. Qué NO se resuelve en esta sesión

Bruno mencionó que al subir de nuevo (paso 4) no quiere volver a subir
material que el editor ya tiene o que ya está en Drive. **Queda fuera de
esta spec** — es un problema de "qué sube `_subir_a_drive`", no de esta
vista. Se anota para una sesión aparte.

## 4. Dónde vive la vista nueva

`PantallaInicio` gana un interruptor de dos pestañas arriba de la lista:
**"Tus proyectos"** / **"En edición externa"**. Reemplazan el mismo espacio
— no son dos listas visibles a la vez. La pestaña "En edición externa"
**siempre está**, aunque no haya nada activo: en ese caso muestra un
mensaje simple en vez de la lista (ver mockup, sección 2).

La pestaña "Tus proyectos" no cambia en nada — sigue siendo exactamente la
lista de hoy, con sus píldoras `● Con el editor` / `✓ El editor ya
contestó` funcionando igual (esa píldora informativa no desaparece: sigue
sirviendo para saber el estado de un proyecto que NO tiene entrega activa
en Drive ahorita mismo, como cualquier otro de la lista general).

## 5. Qué hay en cada fila de "En edición externa"

Solo entran proyectos con una entrega activa: `CON_EDITOR` o `EN_REVISION`
(no `SIN_SUBIR`). Cada fila trae:

- Nombre del proyecto y su ruta (elidida igual que hoy, con `…`).
- Cuándo se subió (`hace 2 días`, mismo formato que ya existe).
- Una píldora de estado:
  - **`● Con el editor`** (ámbar, `CURRENT_COLOR`) — botones: `⟳` (revisar
    Drive, igual que hoy), `Traer de vuelta`, `Ya entregado`.
  - **`◐ En revisión`** (azul, `TRIM_COLOR` — tono nuevo para este canal:
    no es ni el ámbar de "esperando" ni el verde de "pick/contestó", y
    `TRIM_COLOR` no se usaba ya para ninguna píldora) — un solo botón:
    `Ya entregado`. No trae `⟳` ni `Traer de vuelta`: no hay nada nuevo que
    revisar hasta que Bruno suba de nuevo desde dentro del proyecto.

Apretar el nombre o la fila abre el proyecto normal, como en "Tus
proyectos".

## 6. Las dos acciones nuevas, sin abrir el proyecto

### Traer de vuelta

Reusa exactamente la lógica que ya existe en `main_window.py`
(`drive.revisar_cambios` → confirmar → `drive.traer_prproj` +
`drive.traer_material_nuevo`), pero sin una `MainWindow` abierta. Lo único
que hoy depende de tener el proyecto abierto es `_raiz_del_proyecto()`
(sale de los `bins` en memoria). Se lee del archivo `.cvproj` en su lugar
—los `bins` con su origen ya viven guardados ahí (`proyecto.abrir`)— con
una función nueva que hace el mismo cálculo que `_raiz_del_proyecto` pero a
partir del diccionario del proyecto, no de un `MainWindow` vivo. La usan
los dos caminos (el de adentro y el de la lista), para que no haya dos
copias de la misma cuenta.

El cliente de Drive sale igual que ya lo hace el botón `⟳` de hoy
(`Coordinador._al_refrescar` en `app.py`): credenciales fijas en
`~/.clasificador_video/`, sin abrir OAuth por sorpresa —si no hay token
guardado, avisa en vez de intentar conectar.

Al terminar bien: el proyecto pasa a `EN_REVISION` y sigue en la lista de
"En edición externa" (no se abre solo, no desaparece). Si algo falla,
mismo aviso que hoy (`avisar()` en la pantalla, sin bloquear con un
diálogo modal).

### Ya entregado

Pide confirmación (cuadro chico, ver mockup sección 3: "\"X\" va a dejar de
aparecer en \"En edición externa\". Esto no baja ni borra nada de Drive."
— Cancelar / Ya entregado). Al confirmar, limpia la entrega del `.cvproj`
directamente (sin abrir el proyecto ni tocar Drive) y la fila desaparece de
la lista.

## 7. Qué no cambia

- El botón `⟳` y sus píldoras en "Tus proyectos" siguen igual.
- Dentro del proyecto abierto (`title_bar.py`), "Subir de nuevo" y "Traer
  de vuelta" siguen ahí — esta vista nueva no les quita nada, solo agrega
  otro camino para llegar a "Traer de vuelta" y agrega "Ya entregado" que
  antes no existía en ningún lado.
- No hay reconexión ni polling automático de Drive en segundo plano (igual
  que la spec del 18).
- El plugin de Premiere no se toca.

## 8. Cómo se comprueba

- **`EstadoEntrega`**: acepta y persiste `EN_REVISION`; `to_dict`/`de_dict`
  lo redondean sin perder datos.
- **Ciclo completo**: `CON_EDITOR` → traer de vuelta → `EN_REVISION` → subir
  de nuevo → vuelve a `CON_EDITOR`; y `CON_EDITOR`/`EN_REVISION` → "Ya
  entregado" → `SIN_SUBIR` (entrega limpia).
- **Cálculo de la raíz del proyecto sin abrirlo**: con un `.cvproj` de
  prueba con bins y orígenes conocidos, que la función nueva calcule la
  misma raíz que calcularía `_raiz_del_proyecto` con esos mismos bins en
  memoria.
- **Filtro de la pestaña**: de una lista de proyectos con estados mezclados
  (`SIN_SUBIR`, `CON_EDITOR`, `EN_REVISION`), que "En edición externa"
  muestre solo los dos últimos.
- **Botones por estado**: `CON_EDITOR` muestra los tres controles;
  `EN_REVISION` solo "Ya entregado".
- **Verificación visual real** (`CLAUDE.md`): construir la pantalla con
  datos de prueba en los tres estados (con activos, vacía, cuadro de
  confirmar), capturar con `grab()` y mirar el PNG.

## 9. Mockup de esta sesión

Verificado sirviendo el HTML y viéndolo en el navegador (capturas
tomadas). Vive en el scratchpad de la sesión, no se copia al repo — la
fuente de verdad queda en este documento y sus capturas.

## 10. Estado

**Diseñado con Bruno el 2026-09-19, con mockup revisado en navegador, sin
tocar código.** Sigue el plan de implementación
(`docs/superpowers/plans/`), luego construcción con TDD.
