# El guion y las carpetas — plan de implementación

> **Para quien lo ejecuta:** usar `superpowers:subagent-driven-development`
> (recomendado) o `superpowers:executing-plans`, tarea por tarea. Los pasos
> llevan casilla (`- [ ]`) para ir marcándolos.

**Meta:** que la guía sea un **guion de pasos** que puede repetir un cuarto,
que las carpetas se numeren por la primera aparición, y que el panel de
Premiere enseñe en qué paso vas y deje palomear lo montado.

**Arquitectura:** el cambio de fondo es de tres renglones de código en Clipify
—dejar de prohibir, dejar de marcar y dejar de colapsar los repetidos— más un
rail que se ordena por primera aparición. El plugin gana un archivo de avance
propio (`avance.js`) y un panel reescrito. `caminoDelClip` **ya** numera por la
primera aparición y no se toca.

**Herramientas:** Python 3 + PySide6 (Clipify), JavaScript plano (plugin UXP).
Sin dependencias nuevas.

**Spec:** [`../specs/2026-09-15-el-guion-y-las-carpetas-design.md`](../specs/2026-09-15-el-guion-y-las-carpetas-design.md)

**Cómo se corre todo:**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

```bash
node uxp-plugin/pruebas/correr.js
```

---

## Mapa de archivos

**Se crean:**

| Archivo | De qué se encarga |
|---|---|
| `uxp-plugin/js/avance.js` | Qué pasos están montados. Lógica pura: pegar, quitar y cuadrar contra el guion. Sin disco. |
| `uxp-plugin/js/avanceDisco.js` | Leer y escribir ese avance en la carpeta de datos de UXP. Lo único que toca el disco. |
| `uxp-plugin/pruebas/avance.pruebas.js` | Los casos de `avance.js`. |

**Se modifican:**

| Archivo | Qué le cambia |
|---|---|
| `src/clasificador_video/guia.py` | El prompt deja de prohibir repetir; `Revision` pierde `repetidos`. |
| `src/clasificador_video/ui/main_window.py` | El rail se ordena por primera aparición; la guía aceptada conserva la secuencia. |
| `src/clasificador_video/ui/pantalla_guia.py` | La lista numera pasos y marca «otra vez». |
| `docs/patron-de-recorrido/MI-PATRON.md` | Reescrito con el orden dicho por Bruno. |
| `uxp-plugin/js/pestanaOrden.js` | Encabezado fijo, pasos palomeables, marca «otra vez». |
| `uxp-plugin/js/label.js` | `pintarBinMontado`, con el verde fuera de la paleta de cámaras. |
| `uxp-plugin/index.html` | El CSS del encabezado y los pasos; los `<script>` nuevos. |
| `uxp-plugin/pruebas/correr.js` | `avance.js` en la lista de archivos. |

**No se toca:** `uxp-plugin/js/estructura.js`. Su `caminoDelClip` numera con
`orden.indexOf(cuarto)`, que **ya** devuelve la primera aparición — la decisión
del §3.2, escrita antes de que la pregunta existiera. La Tarea 5 le agrega una
prueba que lo deja clavado, pero el código se queda igual.

---

## F1 — Clipify deja de estorbar

### Tarea 1: El prompt deja de prohibir repetir

Hoy le dice al modelo «tienen que estar TODOS y ninguno de más», que le prohíbe
sacar la aérea dos veces.

**Archivos:**
- Modificar: `src/clasificador_video/guia.py`
- Probar: `tests/test_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/test_guia.py`:

```python
def test_el_prompt_deja_repetir_un_cuarto():
    # En los 15 entregables de Bruno siempre se repite alguno, y en 14 de 15
    # el cuarto con el que abre vuelve a salir.
    texto = guia.prompt_de_sistema(["Aérea", "Sala"], patron="")
    assert "las veces que haga falta" in texto
    assert "ninguno de más" not in texto


def test_el_prompt_pide_decir_por_que_se_repite():
    texto = guia.prompt_de_sistema(["Aérea"], patron="")
    assert "otra vez" in texto


def test_el_prompt_sigue_pidiendo_que_esten_todos():
    # Repetir es libre; saltarse un cuarto no. Un cuarto que no sale ni una
    # vez es material que se te olvida al editar.
    texto = guia.prompt_de_sistema(["Aérea", "Sala"], patron="")
    assert "al menos una vez" in texto


def test_el_prompt_pide_pasos_y_no_cuartos():
    texto = guia.prompt_de_sistema(["Sala"], patron="")
    assert "paso" in texto.lower()
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: FALLAN las cuatro, con `AssertionError`.

- [ ] **Paso 3: Escribirlo**

En `src/clasificador_video/guia.py`, dentro de `prompt_de_sistema`, reemplazar
este bloque de `partes`:

```python
        "Los cuartos son EXACTAMENTE estos, y los devuelves escritos igual --con sus",
        "acentos, sus mayúsculas y sus números tal cual--, sin corregir nada, sin",
        "agrupar, sin partir ninguno en dos y sin agregar ninguno que no esté:",
        "\n".join("- " + c for c in cuartos),
        "",
        "Tienen que estar TODOS y ninguno de más.",
```

por este otro:

```python
        "Lo que devuelves es un GUION: los PASOS del video en orden, no una lista",
        "de cuartos. Un mismo cuarto puede salir LAS VECES QUE HAGA FALTA -- este",
        "editor abre con una aérea y cierra con otra, y las dos son la misma",
        "carpeta. Cuando un cuarto vuelva a salir, dilo en su línea: qué cambia esa",
        "vez («otra vez, ahora de salida y más larga»).",
        "",
        "Los cuartos son EXACTAMENTE estos, y los devuelves escritos igual --con sus",
        "acentos, sus mayúsculas y sus números tal cual--, sin corregir nada, sin",
        "agrupar, sin partir ninguno en dos y sin agregar ninguno que no esté:",
        "\n".join("- " + c for c in cuartos),
        "",
        "Todos tienen que salir al menos una vez. Ninguno que no esté en la lista.",
```

Y en el bloque final del mismo `partes`, cambiar la forma que se pide:

```python
        "",
        "Contestas SOLO con JSON, con esta forma exacta:",
        '{"recorrido": "<un párrafo corto de cómo recorrerla>",',
        ' "orden": [{"cuarto": "<nombre tal cual>", "porque": "<una línea corta>",',
        '            "fuera_del_patron": false}]}',
        "",
        "Cada objeto de \"orden\" es UN PASO del video, en orden. Sin texto antes ni",
        "después. Escribe en español de México, de tú, y corto.",
```

(el renglón de «Sin texto antes ni después…» que estaba suelto se reemplaza por
el de arriba, para no decirlo dos veces).

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: todas pasan.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Pedirle al modelo un guion de pasos, que puede repetir un cuarto"
```

---

### Tarea 2: Repetir deja de ser un error

`Revision.repetidos` y su aviso «Repitió: …» se van. Lo demás de la revisión se
queda tal cual.

**Archivos:**
- Modificar: `src/clasificador_video/guia.py`
- Probar: `tests/test_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

En `tests/test_guia.py`, **borrar** `test_un_cuarto_repetido_se_marca_aparte`
(afirma justo lo contrario de lo que ahora queremos) y agregar:

```python
def test_repetir_un_cuarto_ya_no_es_un_aviso():
    # Abre con la aérea y cierra con la aérea: es cómo edita, no un error.
    r = guia.revisar_lista(
        _renglones("Aérea", "Sala", "Aérea"), ["Aérea", "Sala"]
    )
    assert r.limpia()
    assert guia.avisos_de_la_revision(r) == []


def test_la_revision_ya_no_sabe_de_repetidos():
    # El campo se fue entero: dejarlo vacío «por si acaso» invita a que
    # alguien lo vuelva a llenar.
    assert not hasattr(guia.Revision(), "repetidos")


def test_un_faltante_sigue_avisando_aunque_haya_repetidos():
    r = guia.revisar_lista(
        _renglones("Aérea", "Aérea"), ["Aérea", "Cocina"]
    )
    assert r.faltan == ["Cocina"]
    assert any("Cocina" in a for a in guia.avisos_de_la_revision(r))


def test_un_inventado_sigue_avisando_aunque_haya_repetidos():
    r = guia.revisar_lista(
        _renglones("Aérea", "Bodega", "Aérea"), ["Aérea"]
    )
    assert r.inventados == ["Bodega"]
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: FALLA `test_la_revision_ya_no_sabe_de_repetidos` y
`test_repetir_un_cuarto_ya_no_es_un_aviso`.

- [ ] **Paso 3: Escribirlo**

En `src/clasificador_video/guia.py`, la dataclase queda así:

```python
@dataclass
class Revision:
    faltan: list[str] = field(default_factory=list)
    inventados: list[str] = field(default_factory=list)

    def limpia(self) -> bool:
        return not (self.faltan or self.inventados)
```

En `revisar_lista`, borrar el bloque de `repetidos` y el argumento que lo
pasaba:

```python
    propuestos = [r.cuarto for r in (lista or [])]
    reales = list(cuartos_reales or [])

    faltan = [c for c in reales if c not in propuestos]
    inventados = [
        c for i, c in enumerate(propuestos)
        if c not in reales and propuestos.index(c) == i
    ]
    return Revision(faltan=faltan, inventados=inventados)
```

Y en `avisos_de_la_revision`, borrar estas dos líneas:

```python
    if revision.repetidos:
        avisos.append("Repitió: " + ", ".join(revision.repetidos) + ".")
```

Al docstring de `revisar_lista`, agregarle el porqué:

```python
    QUE UN CUARTO SE REPITA NO ES UN ERROR. En los quince entregables de
    2026 siempre se repite alguno, y en catorce el cuarto con el que abre
    vuelve a salir. Aquí se marcó como problema hasta el 2026-09-15, y era
    la app diciéndole a Bruno que su forma de editar estaba mal.

    Lo que sí sigue siendo error: que FALTE un cuarto --uno que no sale ni
    una vez es material que se te olvida al editar-- y que el modelo se
    saque uno de la manga.
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: todas pasan.

- [ ] **Paso 5: Correr la suite entera**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: todo verde. Si algo de `tests/ui/` construía una `Revision` con
`repetidos=[...]`, se arregla aquí.

- [ ] **Paso 6: Commit**

```bash
git add src/clasificador_video/guia.py tests/
git commit -m "Dejar de marcar como error que el guion repita un cuarto"
```

---

### Tarea 3: El rail se ordena por la primera aparición

Un cuarto no puede estar dos veces en el rail. `aceptar_orden_de_la_guia`
recibe ahora una lista con repetidos y hay que quitárselos **conservando el
orden de la primera vez** — el mismo criterio con el que el plugin numera las
carpetas, para que el rail y Premiere no puedan contradecirse.

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py`
- Probar: `tests/ui/test_main_window_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/ui/test_main_window_guia.py`:

```python
def test_el_rail_pone_el_cuarto_repetido_donde_sale_la_PRIMERA_vez(ventana):
    for c in ["Sala", "Aérea", "Cocina"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Aérea"), logica.Renglon("Cocina"),
               logica.Renglon("Sala"), logica.Renglon("Aérea")],
    )
    ventana.aceptar_orden_de_la_guia(
        ["Aérea", "Cocina", "Sala", "Aérea"]
    )
    # Una sola vez, y en el lugar de la primera: es el mismo criterio con el
    # que el plugin numera su carpeta.
    assert ventana.room_selection.active_rooms() == ["Aérea", "Cocina", "Sala"]


def test_el_guion_que_viaja_CONSERVA_las_repeticiones(ventana):
    for c in ["Sala", "Aérea"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Aérea", "abres"), logica.Renglon("Sala"),
               logica.Renglon("Aérea", "cierras, más larga")],
    )
    ventana.aceptar_orden_de_la_guia(["Aérea", "Sala", "Aérea"])

    pasos = ventana._guia_para_el_manifest().orden
    assert [r.cuarto for r in pasos] == ["Aérea", "Sala", "Aérea"]
    # Y cada paso conserva SU razón: la de abrir no es la de cerrar.
    assert pasos[0].porque == "abres"
    assert pasos[2].porque == "cierras, más larga"


def test_un_cuarto_que_el_guion_no_menciona_sigue_entrando_al_final(ventana):
    for c in ["Aérea", "Terraza"]:
        ventana.room_selection.add(c)
    ventana.guia_actual = logica.Respuesta(
        ok=True, recorrido="x",
        lista=[logica.Renglon("Aérea"), logica.Renglon("Aérea")],
    )
    ventana.aceptar_orden_de_la_guia(["Aérea", "Aérea"])

    pasos = [r.cuarto for r in ventana._guia_para_el_manifest().orden]
    assert pasos == ["Aérea", "Aérea", "Terraza"]
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_guia.py -q
```

Esperado: FALLAN las tres. La segunda por
`AssertionError: ['Aérea', 'Sala'] != ['Aérea', 'Sala', 'Aérea']` —
`_guia_cuadrada_con_el_rail` colapsa los repetidos con un diccionario.

- [ ] **Paso 3: Escribirlo**

En `src/clasificador_video/ui/main_window.py`, reemplazar
`aceptar_orden_de_la_guia` y `_guia_cuadrada_con_el_rail` completas por:

```python
    def aceptar_orden_de_la_guia(self, orden: list) -> None:
        """Ese guion pasa a mandar: el rail, la hoja y Premiere.

        El guion trae PASOS y puede repetir un cuarto; el rail no puede.
        Así que al rail se le pasa la lista sin repetir, en el orden de la
        PRIMERA aparición -- el mismo criterio con el que el plugin numera
        la carpeta de ese cuarto. Si los dos no usaran el mismo, el rail y
        Premiere acabarían diciendo cosas distintas del mismo dato.
        """
        self.room_selection.reordenar(_sin_repetir(orden))
        self._cuartos_de_la_guia = self.room_selection.active_rooms()
        self.guia_actual = self._guia_cuadrada_con_el_rail()
        self._sync_rooms()
        # Ya hizo lo suyo: dejarla encima obliga a cerrarla a mano para ver
        # el rail que se acaba de reacomodar, que es lo que uno quiere ver.
        if self._pantalla_guia is not None:
            self._pantalla_guia.hide()

    def _guia_cuadrada_con_el_rail(self):
        """El guion contando sólo cuartos que existen, con sus repeticiones.

        Dos reglas, y son distintas:

        - **Los pasos se conservan tal cual**, repeticiones incluidas. Cada
          paso trae SU razón: la aérea de abrir no dice lo mismo que la de
          cerrar, y quedarse con una sola perdía la mitad de la guía.
        - **Los cuartos que el guion no mencionó entran al final**, una vez
          y sin razón inventada. Perderlos dejaría al rail con un cuarto que
          la guía no nombra, y en Premiere una carpeta sin número suelta.

        Y un cuarto inventado se cae: no está en el rail, y en Premiere
        sería la carpeta de un cuarto que no existe.
        """
        if self.guia_actual is None or not self.guia_actual.ok:
            return self.guia_actual
        reales = self.room_selection.active_rooms()
        pasos = [r for r in self.guia_actual.lista if r.cuarto in reales]
        nombrados = {r.cuarto for r in pasos}
        pasos += [
            logica_guia.Renglon(cuarto=c) for c in reales if c not in nombrados
        ]
        return logica_guia.Respuesta(
            ok=True, recorrido=self.guia_actual.recorrido, lista=pasos
        )
```

Y agregar el ayudante al final del archivo, junto a las otras funciones
sueltas de módulo:

```python
def _sin_repetir(nombres: list) -> list:
    """Los nombres una sola vez, en el orden de la PRIMERA aparición.

    `dict.fromkeys` conserva el orden de inserción desde Python 3.7, y es
    el orden de la primera vez -- que es justo el que hace falta.
    """
    return list(dict.fromkeys(nombres or []))
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_guia.py -q
```

Esperado: todas pasan.

- [ ] **Paso 5: Correr la suite entera**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: todo verde.

- [ ] **Paso 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_guia.py
git commit -m "Ordenar el rail por la primera aparición, sin perder los pasos repetidos"
```

---

### Tarea 4: La pantalla numera pasos y marca «otra vez»

**Archivos:**
- Modificar: `src/clasificador_video/ui/pantalla_guia.py`
- Probar: `tests/ui/test_pantalla_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/ui/test_pantalla_guia.py`:

```python
def test_un_cuarto_repetido_sale_marcado_la_segunda_vez(qtbot):
    p = _pantalla(qtbot)
    p.mostrar_respuesta(
        logica.Respuesta(
            ok=True, recorrido="x",
            lista=[logica.Renglon("Aérea", "abres"),
                   logica.Renglon("Sala"),
                   logica.Renglon("Aérea", "cierras")],
        ),
        logica.Revision(),
    )
    texto = p.texto_del_resultado()
    # La PRIMERA no se marca: marcarla diría que algo pasa con ella.
    assert texto.index("otra vez") > texto.index("Sala")
    assert texto.count("otra vez") == 1


def test_los_pasos_se_numeran_todos(qtbot):
    p = _pantalla(qtbot)
    p.mostrar_respuesta(
        logica.Respuesta(
            ok=True, recorrido="x",
            lista=[logica.Renglon("Aérea"), logica.Renglon("Sala"),
                   logica.Renglon("Aérea")],
        ),
        logica.Revision(),
    )
    texto = p.texto_del_resultado()
    # Tres pasos, no dos cuartos.
    assert "1. Aérea" in texto
    assert "2. Sala" in texto
    assert "3. Aérea" in texto
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_guia.py -q
```

Esperado: FALLA `test_un_cuarto_repetido_sale_marcado_la_segunda_vez` con
`ValueError: substring not found`.

- [ ] **Paso 3: Escribirlo**

En `src/clasificador_video/ui/pantalla_guia.py`, dentro de `_html`, cambiar el
bucle para que lleve la cuenta de los cuartos ya vistos:

```python
        renglones = []
        vistos = set()
        for i, r in enumerate(respuesta.lista, start=1):
            # El numero va escrito y no en un <ol>: el de la lista se pierde
            # al copiar el texto, y el orden es justo lo que uno copia.
            partes = [f"{i}. <b>{escape(r.cuarto)}</b>"]
            if r.cuarto in vistos:
                # SOLO de la segunda vez en adelante. Marcar tambien la
                # primera diria que algo pasa con ella, y no pasa nada: el
                # que vuelve es el segundo.
                partes.append(
                    f'<span style="color: {theme.TEXT_2};"> (otra vez)</span>'
                )
            vistos.add(r.cuarto)
            if r.porque:
                color = theme.TEXT if r.fuera_del_patron else theme.TEXT_3
                cursiva = " font-style: italic;" if r.fuera_del_patron else ""
                partes.append(
                    f'<span style="color: {color};{cursiva}"> — '
                    f"{escape(r.porque)}</span>"
                )
            if r.cuarto in revision.inventados:
                partes.append(
                    f'<span style="color: {theme.REJECT_COLOR};">'
                    "  (este no es tuyo)</span>"
                )
            renglones.append("".join(partes))
```

Hacer el mismo cambio en `_texto`, que es el que se lee en las pruebas de texto
plano — ahí la marca va sin HTML:

```python
    @staticmethod
    def _texto(respuesta: logica.Respuesta, revision: logica.Revision) -> str:
        renglones = []
        vistos = set()
        for i, r in enumerate(respuesta.lista, start=1):
            otra = "  (otra vez)" if r.cuarto in vistos else ""
            vistos.add(r.cuarto)
            marca = "  (este no es tuyo)" if r.cuarto in revision.inventados else ""
            porque = (" — " + r.porque) if r.porque else ""
            renglones.append(f"{i}. {r.cuarto}{otra}{porque}{marca}")
        partes = []
        if respuesta.recorrido:
            partes.append(respuesta.recorrido)
        partes.append("\n".join(renglones))
        return "\n\n".join(partes)
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_guia.py -q
```

Esperado: todas pasan.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/ui/pantalla_guia.py tests/ui/test_pantalla_guia.py
git commit -m "Marcar «otra vez» el cuarto que vuelve a salir en el guion"
```

---

### Tarea 5: Clavar que el plugin numera por la primera aparición

`caminoDelClip` ya lo hace. Esta tarea **no cambia código**: le pone la prueba
que lo deja fijo, para que nadie lo «arregle» después.

**Archivos:**
- Modificar: `uxp-plugin/pruebas/numeroDeCuarto.pruebas.js`

- [ ] **Paso 1: Escribir la prueba**

Agregar dentro del arreglo que devuelve la función principal de
`uxp-plugin/pruebas/numeroDeCuarto.pruebas.js` (la de `module.exports =`, no la
de `module.exports.carpetas`):

```javascript
    {
      // EL CASO DE LA AEREA: abre el guion y lo cierra, y es UN solo bin.
      // Su carpeta lleva el numero de la PRIMERA vez. Ya funcionaba; esto
      // lo deja clavado para que nadie lo "arregle".
      nombre: "un cuarto repetido se numera por su PRIMERA aparicion",
      fn: () => {
        const guion = ["Aerea", "Fachada", "Sala", "Aerea", "Aerea"];
        const r = ctx.caminoDelClip(["Aerea"], guion);
        return { ok: r.join(" > ") === "02. Clip > 01. Aerea", detalle: r.join(" > ") };
      },
    },
    {
      nombre: "los demas cuartos no se corren por la repeticion",
      fn: () => {
        const guion = ["Aerea", "Fachada", "Sala", "Aerea"];
        const r = ctx.caminoDelClip(["Sala"], guion);
        return { ok: r.join(" > ") === "02. Clip > 03. Sala", detalle: r.join(" > ") };
      },
    },
```

- [ ] **Paso 2: Correr y ver que pasan**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: **pasan a la primera**, sin tocar código. Si alguna falla, el
supuesto del §4.c del spec era falso: pararse y revisar `caminoDelClip` antes
de seguir.

- [ ] **Paso 3: Commit**

```bash
git add uxp-plugin/pruebas/numeroDeCuarto.pruebas.js
git commit -m "Clavar con pruebas que un cuarto repetido se numera por su primera vez"
```

---

## F2 — El patrón, reescrito

### Tarea 6: MI-PATRON.md con el orden de Bruno

**Archivos:**
- Modificar: `docs/patron-de-recorrido/MI-PATRON.md`
- Probar: `tests/test_patron.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/test_patron.py`:

```python
def test_el_patron_habla_de_la_aerea_de_en_medio():
    # Lo que Bruno dijo el 2026-09-15 y el documento no tenía.
    texto = patron.leer()
    assert "a media casa" in texto


def test_el_patron_cierra_con_dos_aereas():
    texto = patron.leer()
    assert "de lejos" in texto


def test_el_patron_sigue_sin_cuentas():
    # La regla del §5.1 del spec del patrón, comprobada y no confiada.
    import re

    texto = patron.leer()
    assert not re.search(
        r"[0-9]+ ?%|\([0-9]+ (videos|casos)\)|la mayoría|de cada", texto
    )
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_patron.py -q
```

Esperado: FALLAN las dos primeras.

- [ ] **Paso 3: Escribirlo**

Reemplazar `docs/patron-de-recorrido/MI-PATRON.md` completo por:

```markdown
# Mi patrón de recorrido

Abres por la fachada, y la abres desde el aire: el drone primero, para que se
vea dónde está parada la propiedad. Entras por la puerta principal.

Sigues por las áreas sociales. La cocina va temprano, antes que la sala — al
revés de como lo haría cualquiera. La sala y el comedor van pegados a ella, y
la terraza va en ese mismo bloque, no al final.

Luego las habitaciones, todas juntas y seguidas: la principal primero y las
demás una tras otra, sin volver a ninguna. Los baños y el vestidor van con
ellas, cortos.

Ahí suele caber una aérea a media casa, para respirar antes de salir al
exterior.

Cierras por donde se disfruta: la alberca, las amenidades, el roof. Las
amenidades van en bloque largo, varias tomas seguidas.

Y sales con el drone dos veces: primero la propiedad completa de lejos, y
luego la última toma, más larga que todas las de en medio. Cuando el video
lleva placa de contacto, ésa va hasta el final.

**Tu orden:** fachada aérea → entrada → cocina → sala → comedor → terraza →
recámara principal → recámaras → baños → vestidor → aérea a media casa →
alberca → amenidades → la propiedad de lejos → aérea final
```

**Las reglas del §5.1 del spec del patrón, que es lo más fácil de romper:**

- **Cero cuentas.** Nada de «(15 videos)», nada de porcentajes, nada de «en la
  mayoría de los casos», nada de «14 de 15».
- **Cero justificaciones.** Bruno ya sabe cómo edita.
- **Escrito de tú, en español mexicano.**

- [ ] **Paso 4: Releerlo cazando números**

```bash
grep -nE "[0-9]+ ?%|\([0-9]+ (videos|casos)\)|la mayoría|de cada|[0-9]+ de [0-9]+" docs/patron-de-recorrido/MI-PATRON.md
```

Esperado: **sin resultados**.

- [ ] **Paso 5: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_patron.py -q
```

Esperado: todas pasan.

- [ ] **Paso 6: Commit**

```bash
git add docs/patron-de-recorrido/MI-PATRON.md tests/test_patron.py
git commit -m "Reescribir el patrón con el orden que dijo Bruno"
```

---

## F3 — El avance, del lado del plugin

### Tarea 7: Qué pasos están montados

Lógica pura, sin disco: pegar y quitar palomitas, y cuadrarlas contra el guion
de ahora.

**Archivos:**
- Crear: `uxp-plugin/js/avance.js`
- Crear: `uxp-plugin/pruebas/avance.pruebas.js`
- Modificar: `uxp-plugin/pruebas/correr.js`

- [ ] **Paso 1: Escribir las pruebas que fallan**

`uxp-plugin/pruebas/avance.pruebas.js`:

```javascript
// Los casos del avance: que pasos ya montaste. Logica pura, sin disco:
// corren con `node uxp-plugin/pruebas/correr.js`.
module.exports = function (ctx) {
  const guion = [
    { cuarto: "Aerea" },
    { cuarto: "Sala" },
    { cuarto: "Aerea" },
  ];
  return [
    {
      nombre: "sin nada montado, el avance esta vacio",
      fn: () => {
        const r = ctx.cuadrarAvance([], guion);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "una palomita que cuadra se conserva",
      fn: () => {
        const r = ctx.cuadrarAvance([{ paso: 1, cuarto: "Aerea" }], guion);
        return { ok: r.length === 1 && r[0].paso === 1, detalle: JSON.stringify(r) };
      },
    },
    {
      // EL CASO DEL §7.2 DEL SPEC: reimportaste con otra guia y el paso 2 ya
      // no es el cuarto que era. Esa palomita daria un avance FALSO.
      nombre: "una palomita cuyo cuarto ya no cuadra se descarta",
      fn: () => {
        const r = ctx.cuadrarAvance([{ paso: 2, cuarto: "Cocina" }], guion);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "una palomita de un paso que ya no existe se descarta",
      fn: () => {
        const r = ctx.cuadrarAvance([{ paso: 9, cuarto: "Aerea" }], guion);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      // Las DOS aereas son pasos distintos: palomear la de abrir no palomea
      // la de cerrar.
      nombre: "las dos veces del mismo cuarto se palomean por separado",
      fn: () => {
        const r = ctx.cuadrarAvance(
          [{ paso: 1, cuarto: "Aerea" }, { paso: 3, cuarto: "Aerea" }], guion);
        const solo1 = ctx.cuadrarAvance([{ paso: 1, cuarto: "Aerea" }], guion);
        return {
          ok: r.length === 2 && solo1.length === 1,
          detalle: JSON.stringify(r) + " / " + JSON.stringify(solo1),
        };
      },
    },
    {
      nombre: "montar un paso lo agrega",
      fn: () => {
        const r = ctx.conPaso([], guion, 2, true);
        return { ok: r.length === 1 && r[0].cuarto === "Sala", detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "montar dos veces el mismo paso no lo duplica",
      fn: () => {
        const uno = ctx.conPaso([], guion, 2, true);
        const dos = ctx.conPaso(uno, guion, 2, true);
        return { ok: dos.length === 1, detalle: JSON.stringify(dos) };
      },
    },
    {
      nombre: "despalomear un paso lo quita",
      fn: () => {
        const uno = ctx.conPaso([], guion, 2, true);
        const r = ctx.conPaso(uno, guion, 2, false);
        return { ok: r.length === 0, detalle: JSON.stringify(r) };
      },
    },
    {
      nombre: "el paso en el que vas es el primero sin palomear",
      fn: () => {
        const r = ctx.pasoActual([{ paso: 1, cuarto: "Aerea" }], guion);
        return { ok: r === 2, detalle: String(r) };
      },
    },
    {
      nombre: "con todo montado ya no hay paso actual",
      fn: () => {
        const todo = [
          { paso: 1, cuarto: "Aerea" },
          { paso: 2, cuarto: "Sala" },
          { paso: 3, cuarto: "Aerea" },
        ];
        const r = ctx.pasoActual(todo, guion);
        return { ok: r === null, detalle: String(r) };
      },
    },
    {
      // Para pintar el bin: el cuarto cuenta como montado solo cuando TODAS
      // sus veces lo estan. Con la aerea de abrir palomeada y la de cerrar
      // no, la carpeta todavia no esta lista.
      nombre: "un cuarto esta montado solo cuando TODAS sus veces lo estan",
      fn: () => {
        const media = ctx.cuartosMontados([{ paso: 1, cuarto: "Aerea" }], guion);
        const todo = ctx.cuartosMontados(
          [{ paso: 1, cuarto: "Aerea" }, { paso: 3, cuarto: "Aerea" }], guion);
        return {
          ok: media.indexOf("Aerea") === -1 && todo.indexOf("Aerea") !== -1,
          detalle: JSON.stringify(media) + " / " + JSON.stringify(todo),
        };
      },
    },
  ];
};
```

- [ ] **Paso 2: Enchufarlas al runner**

En `uxp-plugin/pruebas/correr.js`, agregar `"js/avance.js"` al arreglo
`ARCHIVOS`, que queda así:

```javascript
const ARCHIVOS = [
  "js/estructura.js",
  "js/numeroDeCuarto.js",
  "js/avance.js",
];
```

Y juntar el archivo nuevo de casos:

```javascript
const pruebas = require("./numeroDeCuarto.pruebas.js");
const casos = [].concat(
  pruebas(contexto),
  pruebas.carpetas(contexto),
  require("./avance.pruebas.js")(contexto)
);
```

- [ ] **Paso 3: Correr y ver que falla**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: FALLA con `Falta js/avance.js -- no se puede correr nada.`

- [ ] **Paso 4: Escribirlo**

`uxp-plugin/js/avance.js`:

```javascript
// Que pasos del guion ya montaste.
//
// UN PASO NO ES UN CUARTO. La aerea abre el guion y lo cierra: son dos pasos
// y una sola carpeta, y palomear el primero no palomea el segundo. Por eso
// todo aqui va por NUMERO DE PASO y no por nombre de cuarto.
//
// Cada palomita guarda las dos cosas --el paso Y el cuarto-- a proposito: si
// Bruno reimporta con otra guia, el paso 2 puede ser otro cuarto, y esa
// palomita daria un avance FALSO. Cuadrarlas contra el guion de ahora las
// descarta sin avisar: no es un error, es que la guia cambio.
//
// Logica pura, sin disco: el disco es `avanceDisco.js`. Se prueba con
// `node uxp-plugin/pruebas/correr.js`.
//
// Spec: docs/superpowers/specs/2026-09-15-el-guion-y-las-carpetas-design.md

// El cuarto del paso N del guion (los pasos se cuentan desde 1), o null.
function cuartoDelPaso(guion, paso) {
  const renglon = (guion || [])[paso - 1];
  return (renglon && renglon.cuarto) || null;
}

// Las palomitas que siguen valiendo con el guion de ahora.
function cuadrarAvance(avance, guion) {
  return (avance || []).filter(
    (p) => p && cuartoDelPaso(guion, p.paso) === p.cuarto
  );
}

// El avance con el paso N palomeado (`montado` true) o despalomeado.
// Un paso que no existe en el guion no hace nada.
function conPaso(avance, guion, paso, montado) {
  const cuarto = cuartoDelPaso(guion, paso);
  if (!cuarto) return (avance || []).slice();
  const sinEl = (avance || []).filter((p) => p && p.paso !== paso);
  if (!montado) return sinEl;
  sinEl.push({ paso: paso, cuarto: cuarto });
  sinEl.sort((a, b) => a.paso - b.paso);
  return sinEl;
}

function estaMontado(avance, paso) {
  return (avance || []).some((p) => p && p.paso === paso);
}

// En que paso vas: el PRIMERO sin palomear. `null` cuando ya no falta
// ninguno -- y eso es distinto de «vas en el 1», que es un guion sin
// empezar.
function pasoActual(avance, guion) {
  for (let i = 1; i <= (guion || []).length; i++) {
    if (!estaMontado(avance, i)) return i;
  }
  return null;
}

// Los cuartos cuyos pasos estan TODOS montados. Es lo que decide si el bin
// se pinta: con la aerea de abrir lista y la de cerrar pendiente, esa
// carpeta todavia no esta terminada y pintarla mentiria.
function cuartosMontados(avance, guion) {
  const faltantes = {};
  for (let i = 1; i <= (guion || []).length; i++) {
    const cuarto = cuartoDelPaso(guion, i);
    if (!cuarto) continue;
    if (!(cuarto in faltantes)) faltantes[cuarto] = 0;
    if (!estaMontado(avance, i)) faltantes[cuarto]++;
  }
  return Object.keys(faltantes).filter((c) => faltantes[c] === 0);
}
```

- [ ] **Paso 5: Correr y ver que pasa**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: las once nuevas en OK, `0 fallidas`.

- [ ] **Paso 6: Commit**

```bash
git add uxp-plugin/js/avance.js uxp-plugin/pruebas/avance.pruebas.js uxp-plugin/pruebas/correr.js
git commit -m "Llevar la cuenta de qué pasos del guion ya están montados"
```

---

### Tarea 8: Guardar el avance en el disco del plugin

Lo único que toca el disco. Aparte de `avance.js` para que ése se pueda probar
sin UXP.

**Archivos:**
- Crear: `uxp-plugin/js/avanceDisco.js`

- [ ] **Paso 1: Escribirlo**

No lleva pruebas de `node`: `require("uxp")` no existe fuera de Premiere, que
es la misma razón por la que `importarManifest.js` tampoco las tiene. Lo que sí
se prueba —cuadrar, palomear, contar— vive en `avance.js` y ya está cubierto.

`uxp-plugin/js/avanceDisco.js`:

```javascript
// El avance, guardado entre sesiones.
//
// VIVE EN LA CARPETA DEL PLUGIN, NO EN EL PROYECTO DE PREMIERE. Bruno
// levanto el 2026-09-15 la regla de que la pestaña no escriba, pero el dueño
// del dato sigue de este lado: asi no puede corromper un proyecto, y el
// color del bin es un REFLEJO que se recalcula de aqui. Un solo dueño y una
// presentacion derivada -- el mismo corte que `camara` → color.
//
// Un archivo por proyecto, por su nombre: dos rodajes abiertos el mismo dia
// no se pisan el avance.
//
// NUNCA REVIENTA. Que no haya archivo es el caso de la primera vez, y uno
// roto se trata igual: quedarse sin palomitas es una molestia, y tronar al
// abrir el panel es un panel que no abre.

const CARPETA_DE_AVANCE = "avance";

function _nombreDeArchivo(proyecto) {
  // Lo que no sea letra, numero, guion o espacio se vuelve "_": el nombre
  // del proyecto lo escribe Bruno y puede traer "/" -- que en un nombre de
  // archivo es otra carpeta.
  const limpio = String(proyecto || "sin-nombre").replace(/[^\w \-]/g, "_");
  return limpio + ".json";
}

async function _carpeta() {
  const uxpFs = require("uxp").storage.localFileSystem;
  const datos = await uxpFs.getDataFolder();
  try {
    return await datos.getEntry(CARPETA_DE_AVANCE);
  } catch (e) {
    return await datos.createFolder(CARPETA_DE_AVANCE);
  }
}

async function leerAvance(proyecto) {
  try {
    const carpeta = await _carpeta();
    const archivo = await carpeta.getEntry(_nombreDeArchivo(proyecto));
    const datos = JSON.parse(await archivo.read());
    return Array.isArray(datos) ? datos : [];
  } catch (e) {
    return [];
  }
}

async function guardarAvance(proyecto, avance) {
  try {
    const carpeta = await _carpeta();
    const archivo = await carpeta.createFile(_nombreDeArchivo(proyecto), {
      overwrite: true,
    });
    await archivo.write(JSON.stringify(avance || []));
  } catch (e) {
    // Se DICE, y no se traga: sin esto Bruno palomea toda la tarde y al
    // reabrir no queda nada, sin haber visto jamas un aviso.
    logToPanel("No pude guardar qué llevas montado: " + (e && e.message), true);
  }
}
```

- [ ] **Paso 2: Comprobar la sintaxis**

```bash
node --check uxp-plugin/js/avanceDisco.js
```

Esperado: sin salida (sintaxis correcta). **No** se agrega a `ARCHIVOS` del
runner: su `require("uxp")` al llamarse no existe fuera de Premiere.

- [ ] **Paso 3: Commit**

```bash
git add uxp-plugin/js/avanceDisco.js
git commit -m "Guardar el avance en la carpeta del plugin, un archivo por proyecto"
```

---

### Tarea 9: Pintar el bin del cuarto montado

**Archivos:**
- Modificar: `uxp-plugin/js/label.js`

- [ ] **Paso 1: Escribirlo**

Agregar al final de `uxp-plugin/js/label.js`:

```javascript
// El color del bin de un cuarto que ya montaste entero.
//
// EL CHOQUE, RESUELTO A PROPOSITO: arriba de este archivo esta escrito que en
// Premiere el color dice la CAMARA. Eso vale para los CLIPS, que es donde se
// decidio y donde Bruno lo usa para arrastrarle el LUT a toda una camara de
// un jalon. Un BIN no es un clip y nunca tuvo color, asi que ahi queda libre
// para decir otra cosa: si ya lo montaste.
//
// Y el verde NO entra en la paleta de camaras -- CERULEAN, MANGO y VIOLET
// siguen siendo de ellas. Un color que ya significara una camara diciendo
// ademas «montado» seria el mismo error con otro disfraz.
const LABEL_MONTADO = "FOREST";

function pintarBinMontado(project, binItem, montado) {
  const premierepro = require("premierepro");
  const colores = premierepro.Constants.ProjectItemColorLabel;
  const destino = montado ? colores[LABEL_MONTADO] : colores.NONE;

  // Ni la documentacion de Adobe ni la suerte: si esta version no conoce el
  // color, no se pinta nada y se dice UNA vez, con lo que si existe. Mismo
  // trato que `applyCameraLabel`.
  if (destino === undefined) {
    avisarUnaVezDelVerde(colores);
    return;
  }
  if (typeof binItem.createSetColorLabelAction !== "function") {
    avisarUnaVezDelVerde(colores);
    return;
  }
  runTransaction(
    project,
    () => binItem.createSetColorLabelAction(destino),
    (montado ? "Marcar montado " : "Desmarcar ") + binItem.name
  );
}

let yaSeAvisoDelVerde = false;

function avisarUnaVezDelVerde(colores) {
  if (yaSeAvisoDelVerde) return;
  yaSeAvisoDelVerde = true;
  logToPanel(
    "No pude pintar las carpetas de lo que ya montaste: esta versión de " +
      "Premiere no lo permite. Las palomitas del panel siguen funcionando. " +
      "Colores que sí tiene: " + Object.keys(colores).join(", "),
    true
  );
}
```

- [ ] **Paso 2: Comprobar la sintaxis**

```bash
node --check uxp-plugin/js/label.js
```

Esperado: sin salida.

- [ ] **Paso 3: Commit**

```bash
git add uxp-plugin/js/label.js
git commit -m "Pintar de verde el bin del cuarto que ya montaste entero"
```

---

## F4 — El panel

### Tarea 10: El encabezado fijo y los pasos palomeables

**Archivos:**
- Modificar: `uxp-plugin/js/pestanaOrden.js`
- Modificar: `uxp-plugin/js/importarManifest.js`
- Modificar: `uxp-plugin/index.html`

- [ ] **Paso 1: Guardar el nombre del proyecto al importar**

El encabezado dice de qué rodaje es la guía, y ese nombre viene en el manifest.
En `uxp-plugin/js/importarManifest.js`, junto a `guardarGuia`, agregar:

```javascript
// De qué rodaje es la guía que se está enseñando. Sin esto, abrir Premiere
// tres semanas después no dice si la guía es la del proyecto que tienes
// enfrente.
let proyectoDelManifest = "";

function proyectoImportado() {
  return proyectoDelManifest;
}
```

Y dentro de `guardarGuia`, guardarlo también:

```javascript
function guardarGuia(manifest) {
  guiaDelManifest = (manifest && manifest.guia) || null;
  proyectoDelManifest = (manifest && manifest.proyecto) || "";
}
```

- [ ] **Paso 2: Reescribir la pestaña**

`uxp-plugin/js/pestanaOrden.js` queda así, completo:

```javascript
// La pestana «Guia de edicion»: enseña el guion que se armo en Clipify y deja
// palomear lo que ya montaste.
//
// NO PIDE NADA. No tiene llave, no toca la red y no espera. El guion se arma
// en Clipify y viaja congelado adentro del manifest.
//
// LO UNICO QUE ESCRIBE ES TU AVANCE, y va a la carpeta del plugin, no al
// proyecto (ver `avanceDisco.js`). Lo que si toca el proyecto es el color del
// bin, y es un REFLEJO del avance, recalculado cada vez.
//
// UN PASO NO ES UN CUARTO: la aerea abre y cierra, son dos pasos y una sola
// carpeta. Todo lo de aqui va por numero de paso.
//
// Spec: docs/superpowers/specs/2026-09-15-el-guion-y-las-carpetas-design.md

let pestanaArmada = false;
let avanceActual = [];

async function abrirPestanaOrden(hoja) {
  if (pestanaArmada) return;
  pestanaArmada = true;
  await repintarGuia();
}

// Vuelve a pintar la pestana con la guia y el avance de ahora. Se llama al
// abrirla, al importar un manifest nuevo y despues de cada palomita.
async function repintarGuia() {
  const hoja = document.getElementById("hoja-orden");
  if (!hoja || !pestanaArmada) return;

  const guia = guiaImportada();
  const guion = (guia && guia.orden) || [];
  const crudo = await leerAvance(proyectoImportado());
  // Contra el guion de AHORA: una palomita de una guia anterior daria un
  // avance falso, y eso es peor que ninguno (§7.2 del spec).
  avanceActual = cuadrarAvance(crudo, guion);

  dibujarGuia(hoja, guia, avanceActual);
}

function dibujarGuia(hoja, guia, avance) {
  hoja.innerHTML = "";
  const guion = (guia && guia.orden) || [];

  if (!guion.length) {
    // Que no traiga guia NO es un error: es un proyecto que se exporto sin
    // apretar el boton, o de antes de que esto existiera.
    const vacio = document.createElement("p");
    vacio.className = "tenue";
    vacio.textContent =
      "Este proyecto no trae guía de edición. Se arma en Clipify, " +
      "con el botón «Guía de edición», antes de exportar.";
    hoja.appendChild(vacio);
    return;
  }

  hoja.appendChild(dibujarEncabezado(guion, avance));

  const cuerpo = document.createElement("div");
  cuerpo.className = "guia-cuerpo";

  if (guia.recorrido) {
    const parrafo = document.createElement("p");
    parrafo.className = "guia-recorrido";
    parrafo.textContent = guia.recorrido;
    cuerpo.appendChild(parrafo);
  }

  const actual = pasoActual(avance, guion);
  const vistos = {};
  for (let i = 1; i <= guion.length; i++) {
    cuerpo.appendChild(dibujarPaso(guion[i - 1], i, avance, actual, vistos));
    vistos[guion[i - 1].cuarto] = true;
  }
  hoja.appendChild(cuerpo);
}

function dibujarEncabezado(guion, avance) {
  const cab = document.createElement("div");
  cab.className = "guia-cab";

  const actual = pasoActual(avance, guion);
  const chico = document.createElement("div");
  chico.className = "guia-cab-chico";
  chico.textContent = actual === null ? "terminado" : "vas en";
  cab.appendChild(chico);

  const grande = document.createElement("div");
  grande.className = "guia-cab-grande";
  grande.textContent =
    actual === null
      ? "Montaste todo"
      : "Paso " + actual + " · " + guion[actual - 1].cuarto;
  cab.appendChild(grande);

  const cuenta = document.createElement("div");
  cuenta.className = "guia-cab-cuenta";
  // PASOS, no cuartos: con la aerea tres veces, «4 de 9 cuartos» no querria
  // decir nada.
  const texto = avance.length + " de " + guion.length + " pasos montados";
  const proyecto = proyectoImportado();
  cuenta.textContent = proyecto ? texto + " · " + proyecto : texto;
  cab.appendChild(cuenta);

  return cab;
}

function dibujarPaso(renglon, numero, avance, actual, vistos) {
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
  nombre.textContent = renglon.cuarto;
  fila.appendChild(nombre);

  if (vistos[renglon.cuarto]) {
    // SOLO de la segunda vez en adelante: marcar la primera diria que algo
    // pasa con ella, y no pasa nada.
    const otra = document.createElement("span");
    otra.className = "guia-otravez";
    otra.textContent = "otra vez";
    fila.appendChild(otra);
  }

  // Un paso montado esconde su razon: ya no hace falta y le roba espacio al
  // que sigue.
  if (renglon.porque && !montado) {
    const porque = document.createElement("span");
    porque.className = renglon.fuera_del_patron
      ? "guia-porque fuera-del-patron"
      : "guia-porque";
    porque.textContent = " — " + renglon.porque;
    fila.appendChild(porque);
  }

  return fila;
}

async function palomear(paso, montado) {
  const guion = ((guiaImportada() || {}).orden) || [];
  avanceActual = conPaso(avanceActual, guion, paso, montado);
  await guardarAvance(proyectoImportado(), avanceActual);
  await pintarLosBinsMontados(guion);
  await repintarGuia();
}

// El color de los bins, recalculado del avance. Se hace entero cada vez --
// son siete u ocho carpetas-- en vez de llevar la cuenta de cual cambio:
// dos cuentas del mismo dato es como se desincronizan las cosas.
async function pintarLosBinsMontados(guion) {
  const premierepro = require("premierepro");
  const project = await premierepro.Project.getActiveProject();
  if (!project) return;

  const rootItem = await project.getRootItem();
  const rootFolder = premierepro.FolderItem.cast(rootItem);
  const carpetaDeClips = await resolveBinChain(project, rootFolder, [
    CARPETA_DE_CLIPS,
  ]);
  const montados = cuartosMontados(avanceActual, guion);
  const orden = guion.map((r) => r.cuarto);
  // Cada cuarto UNA vez, aunque el guion lo repita: son ocho carpetas, no
  // once. `indexOf` sobre `orden` sigue dando la primera aparicion, que es
  // el numero que lleva la carpeta.
  const cuartos = orden.filter((c, i) => orden.indexOf(c) === i);

  const items = (await carpetaDeClips.getItems()) || [];
  for (const cuarto of cuartos) {
    const bin = carpetaDelCuarto(
      items, conNumero(cuarto, orden.indexOf(cuarto) + 1),
      premierepro.FolderItem.cast
    );
    if (bin) pintarBinMontado(project, bin, montados.indexOf(cuarto) !== -1);
  }
}
```

- [ ] **Paso 3: El CSS**

En `uxp-plugin/index.html`, reemplazar el bloque
`/* --- La guia de edicion --- */` completo por:

```css
  /* --- La guia de edicion --------------------------------------- */
  /* La pestana LEE el guion y guarda tu avance. Ni llave ni preguntas: se
     fueron el 2026-09-14, la guia se arma en Clipify. */
  .guia-cab {
    padding: 10px 12px; border-bottom: 1px solid var(--linea);
    background: #262626; margin: -10px -12px 10px;
  }
  .guia-cab-chico {
    color: var(--tinta-3); text-transform: uppercase;
    letter-spacing: .5px; font-size: 10px;
  }
  .guia-cab-grande { color: #f4f4f4; font-size: 15px; font-weight: 600; margin-top: 2px; }
  .guia-cab-cuenta { color: var(--tinta-2); margin-top: 5px; font-size: 11px; }

  .guia-recorrido { margin: 0 0 12px; line-height: 1.5; color: var(--tinta); }
  .guia-paso {
    display: flex; gap: 7px; align-items: baseline;
    padding: 4px 6px; border-radius: 3px; line-height: 1.45;
  }
  .guia-palomita { margin: 0; align-self: center; }
  .guia-num {
    color: var(--tinta-3); min-width: 16px;
    font-variant-numeric: tabular-nums;
  }
  .guia-cuarto { color: #f4f4f4; }
  .guia-porque { color: var(--tinta-3); }
  /* El renglon que se salio del patron de Bruno va en ambar y en cursiva: es
     informacion que solo tenia la IA, y es lo unico de la lista que hay que
     leer con atencion. Mismo trato que le da la pantalla de Clipify. */
  .guia-porque.fuera-del-patron { color: var(--ambar); font-style: italic; }
  /* Un paso montado se tacha y se calla. */
  .guia-paso.montado .guia-cuarto,
  .guia-paso.montado .guia-num { color: #5f5f5f; text-decoration: line-through; }
  /* En el que vas: un filo ambar, que es donde el ojo cae solo. */
  .guia-paso.ahora { background: rgba(240,180,41,.10); box-shadow: inset 2px 0 0 var(--ambar); }
  /* «Otra vez» va en azul y no en ambar: no es un aviso, es un dato. El
     ambar de este panel esta reservado para lo que hay que decidir. */
  .guia-otravez {
    color: #7a9cc6; font-size: 10px; border: 1px solid #3f556b;
    border-radius: 8px; padding: 0 5px;
  }
```

- [ ] **Paso 4: Los `<script>` nuevos**

En `uxp-plugin/index.html`, junto a los otros, y **antes** de
`pestanaOrden.js`, que los usa:

```html
<script src="js/avance.js"></script>
<script src="js/avanceDisco.js"></script>
```

- [ ] **Paso 5: La pestaña abre con `await`**

`abrirPestanaOrden` ahora es `async`. En el `<script>` de abajo de
`uxp-plugin/index.html`, la línea que la llama:

```javascript
      if (hoja.id === "hoja-orden") abrirPestanaOrden(hoja);
```

se queda **igual**: llamar una función `async` sin `await` desde un manejador
de clic está bien —lo que devuelve no se usa— y los errores adentro ya se
tragan en `leerAvance` y se dicen en `guardarAvance`.

- [ ] **Paso 6: Comprobar la sintaxis y correr las pruebas**

```bash
node --check uxp-plugin/js/pestanaOrden.js && node --check uxp-plugin/js/importarManifest.js
```

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: sin salida el primero, `0 fallidas` el segundo.

- [ ] **Paso 7: Commit**

```bash
git add uxp-plugin/js/pestanaOrden.js uxp-plugin/js/importarManifest.js uxp-plugin/index.html
git commit -m "Enseñar en qué paso vas y dejar palomear lo montado"
```

---

### Tarea 11: Verificación visual del panel

**Nunca afirmar que algo se ve bien sin haber visto el pixel.** Los archivos
temporales van al scratchpad de la sesión, **nunca al repo**.

- [ ] **Paso 1: Armar la página de prueba en el scratchpad**

Copiar `uxp-plugin/index.html`, `js/pestanaOrden.js` y `js/avance.js` al
scratchpad. En la copia del HTML, quitar los `<script src>` que necesitan
Premiere y agregar al final uno que sustituya lo que no corre fuera de él:

```html
<script>
  function guiaImportada() { return GUIA; }
  function proyectoImportado() { return "Casa Lomas"; }
  async function leerAvance() { return [{ paso: 1, cuarto: "Fachada" },
                                        { paso: 2, cuarto: "Cocina" }]; }
  async function guardarAvance() {}
  async function pintarLosBinsMontados() {}
  const GUIA = {
    recorrido: "Abres por la fachada desde el aire y bajas a las áreas sociales. Cierras por las amenidades y sales con el drone.",
    orden: [
      { cuarto: "Fachada", porque: "abres desde el aire" },
      { cuarto: "Cocina", porque: "va temprano, como siempre" },
      { cuarto: "Sala", porque: "sigue el bloque social" },
      { cuarto: "Recámara principal", porque: "empiezan las habitaciones" },
      { cuarto: "Aérea", porque: "respiro a media casa" },
      { cuarto: "Alberca", porque: "la subí porque hay que lucirla", fuera_del_patron: true },
      { cuarto: "Aérea", porque: "la propiedad de lejos" },
      { cuarto: "Aérea", porque: "la de salida, más larga" }
    ]
  };
  pestanaArmada = true;
  document.getElementById("tab-importar").classList.remove("activa");
  document.getElementById("hoja-importar").classList.add("oculto");
  document.getElementById("tab-orden").classList.add("activa");
  document.getElementById("hoja-orden").classList.remove("oculto");
  repintarGuia();
</script>
```

- [ ] **Paso 2: Servirlo y mirarlo**

```bash
python3 -m http.server 8765 --directory <el scratchpad de la sesión>
```

Abrirlo con una herramienta de navegador **a 360 px de ancho**, que es lo
angosto que se pone el panel de verdad, sacar captura y **leer la imagen**.

Comprobar con los ojos:

- El encabezado dice «Paso 3 · Sala», «2 de 8 pasos montados · Casa Lomas».
- Los dos primeros pasos están tachados y **sin su razón**.
- El paso 3 trae el filo ámbar.
- Los pasos 7 y 8 traen «otra vez»; el 5 **no**, aunque también es Aérea —
  porque es la primera vez que sale.
- El renglón de la Alberca **se distingue** de los demás y se lee completo.

- [ ] **Paso 3: Capturar el caso de todo montado**

Cambiar el `leerAvance` de mentiras para que devuelva los ocho pasos, recargar,
capturar y **mirar**: el encabezado debe decir «terminado / Montaste todo».

- [ ] **Paso 4: Apagar el servidor y comprobar que no quedó nada**

```bash
git status --short
```

Esperado: **nada** del scratchpad dentro del repo.

- [ ] **Paso 5: Commit si hubo ajustes**

```bash
git add -u uxp-plugin/
git commit -m "Ajustar el dibujo del panel tras verlo"
```

Si nada cambió no hay commit, pero sí queda dicho en el reporte que las dos
imágenes se miraron.

---

## F5 — Cierre

### Tarea 12: La documentación y las dos suites

**Archivos:**
- Modificar: `README.md`, `docs/DESARROLLO.md`, `docs/superpowers/CONTEXTO-Y-METAS.md`, `CLAUDE.md`

- [ ] **Paso 1: Correr todo**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: los dos verdes. **Si algo falla se arregla antes de seguir** — no se
documenta como terminado lo que no pasó.

- [ ] **Paso 2: `README.md`**

En la sección de la guía de edición, escrito para quien la usa:

- Que la guía es un **recorrido de pasos** y que un cuarto puede salir varias
  veces —la aérea que abre y la que cierra son dos pasos y una sola carpeta—.
- Que en Premiere se va **palomeando lo que ya montaste**, que el panel dice en
  qué paso vas, y que la carpeta se pinta de verde cuando ese cuarto está
  completo.
- Que las palomitas viven en la computadora, no en el proyecto: si le pasas el
  proyecto a alguien, no van.

- [ ] **Paso 3: `docs/DESARROLLO.md`**

Agregar `avance.js` y `avanceDisco.js` a la tabla de archivos del plugin, y por
qué están partidos: uno es lógica pura que corre en `node`, el otro toca el
disco de UXP y por eso no.

- [ ] **Paso 4: `docs/superpowers/CONTEXTO-Y-METAS.md`**

Anotar que la guía pasó de ser un orden de cuartos a un guion de pasos, con el
porqué en una línea —un cuarto sale varias veces— y que lo que falta
comprobar en Premiere ahora son dos cosas: la numeración y si deja pintar un
bin de color.

- [ ] **Paso 5: `CLAUDE.md`**

Agregar a las decisiones de arquitectura ya tomadas, junto a las otras:

> - **La guía es un GUION de pasos, no un orden de cuartos.** Un cuarto sale
>   las veces que haga falta —Bruno abre con una aérea y cierra con otra, y
>   son la misma carpeta—, así que repetir NO es un error y la revisión dejó
>   de marcarlo. Una carpeta es un lugar, un recorrido es una secuencia: no
>   pueden llevar el mismo número. **La carpeta se numera por la PRIMERA
>   aparición del cuarto**, y el rail se ordena con ese mismo criterio para
>   que no puedan contradecirse. El dato salió de las fichas del patrón y
>   estuvo mal leído un día: sacar la posición MEDIANA de cada cuarto es
>   justo lo que esconde que sale dos veces. Ver
>   `specs/2026-09-15-el-guion-y-las-carpetas-design.md`.
>
> - **El avance —qué pasos ya montaste— vive en el plugin, y el color del bin
>   es su reflejo.** Se recalcula entero al palomear, nunca se lleva por
>   separado. Y el verde del bin NO entra en la paleta de cámaras: en un
>   **clip** el color dice la cámara, en un **bin** dice si está montado, y
>   son dos canales distintos sobre dos tipos de item distintos.

- [ ] **Paso 6: Repasar que nada quedó tirado**

```bash
git status --short
```

Cada archivo nuevo tiene que estar en una carpeta que tenga sentido, sin nada
suelto en la raíz ni restos del scratchpad.

- [ ] **Paso 7: Commit**

```bash
git add README.md docs/ CLAUDE.md
git commit -m "Documentar el guion de pasos y el avance en el panel"
```

---

## Lo que hay que enseñarle a Bruno al terminar

Las dos capturas de la Tarea 11 y la salida de las dos suites. **Si no se miró
una imagen, no se afirma que se ve bien.**

Y las dos cosas que solo él puede comprobar, las dos con Premiere abierto:

1. **Si Premiere deja pintar un bin de color** (`createSetColorLabelAction`
   sobre un `FolderItem`, y si existe `FOREST`). Si no deja, el panel lo dice
   una vez y las palomitas siguen funcionando — no es un bloqueo.
2. **Si el guion que sale se parece a cómo monta de verdad**, ahora que puede
   repetir la aérea.
