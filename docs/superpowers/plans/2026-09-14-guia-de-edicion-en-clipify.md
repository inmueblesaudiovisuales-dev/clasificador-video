# La guía de edición en Clipify — plan de implementación

> **Para quien lo ejecuta:** usar `superpowers:subagent-driven-development`
> (recomendado) o `superpowers:executing-plans`, tarea por tarea. Los pasos
> llevan casilla (`- [ ]`) para ir marcándolos.

**Meta:** que la guía de edición se arme en Clipify antes de exportar, viaje
congelada en el manifest, y el panel de Premiere solo la lea — con las carpetas
de cuartos numeradas en ese orden.

**Arquitectura:** la lógica que hoy vive en JavaScript dentro del plugin
(`ordenSugerido.js`, `deepseek.js`, `llave.js`, `cuartosDelProyecto.js`) se
traduce a Python del lado de Clipify, donde los cuartos ya existen. El manifest
gana un bloque `guia`. El plugin pierde todo lo que preguntaba y gana la
numeración de carpetas con reconocimiento del cuarto sin su número.

**Herramientas:** Python 3 + PySide6 (Clipify), JavaScript plano (plugin UXP).
Nada de dependencias nuevas: la llamada HTTP va con `urllib.request`, que es de
la biblioteca estándar.

**Spec:** [`../specs/2026-09-14-guia-de-edicion-en-clipify-design.md`](../specs/2026-09-14-guia-de-edicion-en-clipify-design.md)

**Cómo se corre todo:**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

```bash
node uxp-plugin/pruebas/correr.js
```

---

## Mapa de archivos

**Se crean, del lado de Clipify:**

| Archivo | De qué se encarga |
|---|---|
| `docs/patron-de-recorrido/MI-PATRON.md` | El patrón de Bruno en prosa, escrito a partir de las fichas. Sin cuentas. |
| `src/clasificador_video/patron.py` | Leer ese Markdown y entregarlo como texto. Nada más. |
| `src/clasificador_video/guia.py` | La parte que PIENSA: arma el prompt, lee la respuesta, revisa la lista. Sin Qt, sin red, sin disco. |
| `src/clasificador_video/llave.py` | Guardar y leer la llave en `~/.clasificador_video/llave.json`. |
| `src/clasificador_video/ia.py` | La llamada HTTP, y nada más. Cambiar de proveedor es este archivo. |
| `src/clasificador_video/ui/pantalla_guia.py` | La pantalla: dos preguntas, el resultado, «Usar este orden». |

**Se crean, del lado del plugin:**

| Archivo | De qué se encarga |
|---|---|
| `uxp-plugin/js/numeroDeCuarto.js` | Poner, quitar y comparar el prefijo `NN. `. Lógica pura, se prueba con `node`. |

**Se modifican:**

- `src/clasificador_video/manifest.py` — el bloque `guia`.
- `src/clasificador_video/proyecto.py` — la guía se guarda con el proyecto.
- `src/clasificador_video/rooms.py` — `reordenar`.
- `src/clasificador_video/ui/title_bar.py` — el botón y su señal.
- `src/clasificador_video/ui/main_window.py` — conectar todo.
- `uxp-plugin/js/estructura.js` — `caminoDelClip` con el número.
- `uxp-plugin/js/bins.js` — `resolverCuarto`, que renumera en vez de duplicar.
- `uxp-plugin/js/processManifest.js` — pasar el orden de la guía.
- `uxp-plugin/js/pestanaOrden.js` — vaciada: solo enseña lo que trajo el manifest.
- `uxp-plugin/pruebas/correr.js` — la lista de archivos que evalúa.

**Se borran** (Tarea 19, en un solo commit):

- `uxp-plugin/js/ordenSugerido.js`
- `uxp-plugin/js/deepseek.js`
- `uxp-plugin/js/llave.js`
- `uxp-plugin/js/cuartosDelProyecto.js`
- `uxp-plugin/pruebas/ordenSugerido.pruebas.js`

---

## F1 — El patrón de Bruno, escrito

### Tarea 1: El documento del patrón

Es el paso 5 que quedó pendiente en el handoff del patrón de recorrido. Sin
él, la guía sugiere el orden de manual y todo lo demás no sirve de nada.

**Archivos:**
- Crear: `docs/patron-de-recorrido/MI-PATRON.md`
- Leer (no modificar): `docs/patron-de-recorrido/datos/fichas.json`, `docs/patron-de-recorrido/datos/tomas.json`

- [ ] **Paso 1: Leer las fichas y sacar las cuentas**

Las cuentas se hacen para **decidir qué entra**, y se quedan fuera del
documento. Correr en el scratchpad de la sesión, no en el repo:

```bash
python3 -c "
import json, statistics
fichas = json.load(open('docs/patron-de-recorrido/datos/fichas.json'))
if isinstance(fichas, dict): fichas = list(fichas.values())
pos = {}
for f in fichas:
    tomas = f.get('tomas') or []
    n = len(tomas)
    for i, t in enumerate(tomas):
        nombre = t.get('cuarto') if isinstance(t, dict) else t
        if not nombre: continue
        pos.setdefault(nombre, []).append(i / max(n - 1, 1))
for nombre, xs in sorted(pos.items(), key=lambda kv: statistics.median(kv[1])):
    print(f'{statistics.median(xs):.2f}  {nombre}  (en {len(xs)} tomas)')
"
```

Si la forma de `fichas.json` no coincide con lo que este comando supone,
**mirar el archivo y ajustar el comando** — no inventar los números. Los
hallazgos ya publicados en el handoff son el contraste: fachada 0.24, cocina
0.28, sala 0.31, comedor 0.32, recámaras 0.55, baños 0.62, amenidades 0.76;
10 de 15 abren por aire y 10 de 15 cierran por aire; la última toma dura el
doble que las de en medio.

- [ ] **Paso 2: Escribir el documento**

Crear `docs/patron-de-recorrido/MI-PATRON.md` con exactamente esta forma —dos
partes y nada más:

```markdown
# Mi patrón de recorrido

Abres por fuera y desde arriba: la fachada en aérea, para que se vea dónde
está parada la propiedad. Entras por la puerta principal.

La cocina va temprano, antes que la sala — al revés de como lo haría
cualquiera. La sala y el comedor van pegados a ella, en el mismo bloque de
la planta baja.

Las recámaras van juntas y van rápido, una tras otra sin detenerte. Los
baños van con ellas, cortos.

Cierras por donde se disfruta la propiedad: la alberca, la terraza, el
jardín. Y sales por el aire, con una toma más larga que todas las de en
medio — el doble de lo que dura un corte normal.

**Tu orden:** fachada aérea → entrada → cocina → sala → comedor →
recámaras → baños → terraza → alberca → jardín → aérea de salida
```

**Las reglas del §5.1 del spec del patrón, que es lo más fácil de romper:**

- **Cero cuentas.** Nada de «(15 videos)», nada de porcentajes, nada de «en
  la mayoría de los casos».
- **Cero justificaciones.** El documento no tiene que convencer a nadie: Bruno
  ya sabe cómo edita.
- **Escrito de tú, en español mexicano**, como se lo contarías a alguien que
  va a editar por ti.
- El texto de arriba es el punto de partida. **Ajustarlo a lo que digan las
  cuentas del Paso 1**, no al revés.

- [ ] **Paso 3: Releerlo cazando números**

```bash
grep -nE "[0-9]+ ?%|\([0-9]+ (videos|casos)\)|la mayoría|el [0-9]+ por ciento" docs/patron-de-recorrido/MI-PATRON.md
```

Esperado: **sin resultados**. Si sale algo, se quita.

- [ ] **Paso 4: Commit**

```bash
git add docs/patron-de-recorrido/MI-PATRON.md
git commit -m "Escribir el patrón de recorrido de Bruno en prosa"
```

---

### Tarea 2: Cargar el patrón

**Archivos:**
- Crear: `src/clasificador_video/patron.py`
- Probar: `tests/test_patron.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

`tests/test_patron.py`:

```python
from pathlib import Path

from clasificador_video import patron


def test_lee_el_documento(tmp_path: Path):
    doc = tmp_path / "MI-PATRON.md"
    doc.write_text("# Mi patrón\n\nAbres por fuera.\n", encoding="utf-8")
    assert "Abres por fuera." in patron.leer(doc)


def test_sin_documento_devuelve_vacio(tmp_path: Path):
    # Que no exista NO es un error: es un Clipify recién instalado, y la
    # guía tiene que salir igual, nada mas sin el patron adentro.
    assert patron.leer(tmp_path / "no-existe.md") == ""


def test_el_documento_de_verdad_esta_en_su_lugar():
    assert patron.leer().strip() != ""
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_patron.py -q
```

Esperado: FALLA con `ModuleNotFoundError: No module named 'clasificador_video.patron'`.

- [ ] **Paso 3: Escribirlo**

`src/clasificador_video/patron.py`:

```python
"""El patrón de recorrido de Bruno, leído del Markdown.

**Un solo dueño: el Markdown.** Es el archivo que Bruno edita a mano cuando
algo no le cuadra, y de ahí sale el texto que viaja en el prompt. No hay
copia en ningún otro lado -- dos copias del mismo dato que se editan por
separado se desincronizan en el primer cambio de opinión.

Sin Qt.
"""
from __future__ import annotations

from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "docs" / "patron-de-recorrido" / "MI-PATRON.md"


def leer(ruta: Path | None = None) -> str:
    """El documento entero, o "" si no está.

    Que no esté no es un error: la guía se arma igual, nada más sin el
    patrón adentro, y entonces lo que sugiere es el orden de manual. Reventar
    aquí dejaría a Bruno sin poder pedir la guía por un archivo de
    documentación.
    """
    destino = RUTA if ruta is None else ruta
    try:
        return destino.read_text(encoding="utf-8")
    except OSError:
        return ""
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_patron.py -q
```

Esperado: `3 passed`.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/patron.py tests/test_patron.py
git commit -m "Leer el patrón de recorrido desde su Markdown"
```

---

## F2 — La parte que piensa

### Tarea 3: El prompt

Es la traducción de `promptDeSistema` y `contextoDeRespuestas` de
`uxp-plugin/js/ordenSugerido.js`, **con tres cambios**: entra el patrón, se va
la pregunta de «para quién», y se pide también el párrafo del recorrido.

**Archivos:**
- Crear: `src/clasificador_video/guia.py`
- Probar: `tests/test_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

`tests/test_guia.py`:

```python
from clasificador_video import guia


def test_los_cuartos_van_en_el_prompt_tal_cual():
    texto = guia.prompt_de_sistema(["Recámara 1", "Baño"], patron="")
    assert "- Recámara 1" in texto
    assert "- Baño" in texto


def test_el_patron_entra_como_base_y_no_como_regla():
    texto = guia.prompt_de_sistema(["Sala"], patron="Abres por fuera.")
    assert "Abres por fuera." in texto
    # La instruccion del §5.1 del spec del patron: base, no regla.
    assert "punto de partida" in texto
    assert "no es una regla" in texto


def test_sin_patron_el_prompt_no_habla_de_uno():
    texto = guia.prompt_de_sistema(["Sala"], patron="")
    assert "punto de partida" not in texto


def test_el_contexto_lleva_lo_que_bruno_contesto():
    texto = guia.contexto_de_respuestas(
        {"propiedad": "Quinta de campo", "lucir": "la alberca"}
    )
    assert "Quinta de campo" in texto
    assert "la alberca" in texto


def test_el_contexto_sirve_aunque_no_conteste_nada():
    # El boton esta activo desde el primer momento: un cuerpo roto aqui
    # seria un boton que no funciona.
    assert guia.contexto_de_respuestas({}).strip() != ""


def test_el_cuerpo_trae_sistema_y_usuario():
    cuerpo = guia.cuerpo_del_request(["Sala"], {"lucir": "el jardín"}, patron="")
    roles = [m["role"] for m in cuerpo["messages"]]
    assert roles == ["system", "user"]
    assert cuerpo["model"]
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: FALLA con `ModuleNotFoundError: No module named 'clasificador_video.guia'`.

- [ ] **Paso 3: Escribirlo**

`src/clasificador_video/guia.py` (esta tarea escribe la primera mitad; las
Tareas 4 y 5 le agregan el resto al mismo archivo):

```python
"""La guía de edición: la parte que PIENSA.

Aquí no hay Qt, ni red, ni disco. Es a propósito: así todo esto se prueba
sin abrir la app y sin gastar una llamada. Lo que habla con el mundo vive
aparte (`ia.py`, `llave.py`, `patron.py`).

Es la traducción de `uxp-plugin/js/ordenSugerido.js`, que murió cuando la
guía se mudó a Clipify. Los casos de sus pruebas de `node` viven ahora en
`tests/test_guia.py`: ya cachaban cosas reales y no se reinventan.

Spec: docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md
"""
from __future__ import annotations

from dataclasses import dataclass, field

MODELO = "deepseek-chat"
# El de conversación, no el de razonamiento. Esto no es una cadena de
# razonamiento: es acomodar diez nombres con criterio de recorrido, y el de
# razonamiento cuesta y tarda más para la misma respuesta.


def prompt_de_sistema(cuartos: list[str], patron: str) -> str:
    """Lo que se le dice al modelo.

    EL MATIZ QUE NO SE PUEDE PERDER: el modelo sabe por qué la cocina va
    antes que la sala --eso es criterio de recorrido-- pero NO sabe qué hay
    en la cocina de Bruno, porque no vio el video y nunca lo va a ver. Un
    modelo describiendo una cocina que no vio («la cocina integral con
    cubierta de granito») es exactamente el modo de falla que este repo
    lleva un mes evitando: adivinar en silencio y sonar seguro.
    """
    partes = [
        "Eres el asistente de un editor de video mexicano que hace recorridos de",
        "propiedades en venta o renta. Tu trabajo es proponer EN QUÉ ORDEN deben ir",
        "los cuartos en el video: el recorrido que debe llevar el espectador.",
        "",
        "NO viste el material. No sabes qué hay adentro de ningún cuarto, cómo se ve",
        "ni con qué se grabó. Por eso:",
        "- La línea de cada cuarto dice POR QUÉ VA AHÍ en el recorrido, no qué hay",
        "  adentro. «Se entra por aquí» sirve; «la cocina integral con cubierta de",
        "  granito» es inventado y no se vale.",
        "- Solo hablas de esta propiedad en concreto si el editor te lo contó él",
        "  mismo.",
        "- Si no tienes una razón de recorrido que dar, da la genérica. No rellenes",
        "  con detalles.",
        "",
        "Los cuartos son EXACTAMENTE estos, y los devuelves escritos igual --con sus",
        "acentos, sus mayúsculas y sus números tal cual--, sin corregir nada, sin",
        "agrupar, sin partir ninguno en dos y sin agregar ninguno que no esté:",
        "\n".join("- " + c for c in cuartos),
        "",
        "Tienen que estar TODOS y ninguno de más.",
    ]

    if patron.strip():
        partes += [
            "",
            "ASÍ TRABAJA ESTE EDITOR. Es su punto de partida, no es una regla:",
            "úsalo salvo que el recorrido quede mejor de otro modo, porque lo que",
            "manda es que el video quede bien.",
            "",
            patron.strip(),
            "",
            "Cuando te apartes de su forma de trabajar, marca ese cuarto con",
            '"fuera_del_patron": true y di en una línea corta por qué lo moviste.',
        ]

    partes += [
        "",
        "Contestas SOLO con JSON, con esta forma exacta:",
        '{"recorrido": "<un párrafo corto de cómo recorrerla>",',
        ' "orden": [{"cuarto": "<nombre tal cual>", "porque": "<una línea corta>",',
        '            "fuera_del_patron": false}]}',
        "",
        "Sin texto antes ni después. Escribe en español de México, de tú, y corto.",
    ]
    return "\n".join(partes)


def contexto_de_respuestas(respuestas: dict) -> str:
    """Lo que Bruno contestó, vuelto una frase.

    Va como primer mensaje SUYO y no metido en el prompt de sistema: es lo
    que él dijo, y mezclarlo con las instrucciones hace que el modelo se
    confunda de quién dijo qué.
    """
    partes = []
    if respuestas.get("lucir"):
        partes.append("Lo que hay que lucir: " + str(respuestas["lucir"]) + ".")
    if respuestas.get("propiedad"):
        partes.append("La propiedad es: " + str(respuestas["propiedad"]) + ".")
    partes.append("Dame el recorrido y el orden de los cuartos.")
    return " ".join(partes)


def cuerpo_del_request(cuartos: list[str], respuestas: dict, patron: str) -> dict:
    """El objeto que se le manda a la API. No la llama: eso es `ia.py`."""
    return {
        "model": MODELO,
        "messages": [
            {"role": "system", "content": prompt_de_sistema(cuartos or [], patron)},
            {"role": "user", "content": contexto_de_respuestas(respuestas or {})},
        ],
    }
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: `6 passed`.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Armar el prompt de la guía, con el patrón adentro"
```

---

### Tarea 4: Leer lo que contestó el modelo

Traducción de `leerRespuesta` y `recortarJson`. **El contador de llaves se
traduce tal cual**: cuenta llaves en vez de usar una expresión regular porque
el JSON anida y una regular no sabe contar, y se salta las llaves que van
DENTRO de una cadena — lo que rompería con un cuarto llamado «Sala {grande}».

**Archivos:**
- Modificar: `src/clasificador_video/guia.py`
- Probar: `tests/test_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/test_guia.py`:

```python
def test_lee_una_respuesta_limpia():
    r = guia.leer_respuesta(
        '{"recorrido": "Abres por fuera.",'
        ' "orden": [{"cuarto": "Sala", "porque": "se entra aquí"}]}'
    )
    assert r.ok
    assert r.recorrido == "Abres por fuera."
    assert r.lista[0].cuarto == "Sala"
    assert r.lista[0].porque == "se entra aquí"
    assert r.lista[0].fuera_del_patron is False


def test_rescata_el_json_envuelto_en_backticks():
    # Los modelos lo hacen aunque se les pida que no. Tratarlo como error
    # seria fallar por una formalidad con la respuesta buena adentro.
    r = guia.leer_respuesta(
        'Claro:\n```json\n{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}\n```\nlisto'
    )
    assert r.ok
    assert r.lista[0].cuarto == "Sala"


def test_un_cuarto_con_llaves_en_el_nombre_no_rompe_el_recorte():
    r = guia.leer_respuesta(
        '{"recorrido": "x", "orden": [{"cuarto": "Sala {grande}"}]}'
    )
    assert r.ok
    assert r.lista[0].cuarto == "Sala {grande}"


def test_marca_el_cuarto_que_se_salio_del_patron():
    r = guia.leer_respuesta(
        '{"recorrido": "x", "orden": [{"cuarto": "Alberca",'
        ' "porque": "la subí porque dijiste que hay que lucirla",'
        ' "fuera_del_patron": true}]}'
    )
    assert r.lista[0].fuera_del_patron is True


def test_el_porque_puede_faltar_sin_tumbar_la_respuesta():
    # Bruno lo pidio, pero si el modelo no lo manda, el ORDEN --que es lo
    # que vino a ver-- sigue sirviendo.
    r = guia.leer_respuesta('{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}')
    assert r.ok
    assert r.lista[0].porque == ""


def test_prosa_en_vez_de_json_es_un_error_con_nombre():
    r = guia.leer_respuesta("Yo creo que primero la sala y luego la cocina.")
    assert not r.ok
    assert not r.lista
    assert "texto" in r.error


def test_json_roto_no_ensena_media_lista():
    r = guia.leer_respuesta('{"orden": [{"cuarto": ')
    assert not r.ok
    assert not r.lista


def test_una_lista_vacia_es_un_error():
    r = guia.leer_respuesta('{"recorrido": "x", "orden": []}')
    assert not r.ok


def test_un_renglon_sin_nombre_de_cuarto_es_un_error():
    r = guia.leer_respuesta('{"recorrido": "x", "orden": [{"porque": "…"}]}')
    assert not r.ok


def test_no_contestar_nada_es_un_error_con_nombre():
    r = guia.leer_respuesta("")
    assert not r.ok
    assert r.error
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: FALLA con `AttributeError: module 'clasificador_video.guia' has no attribute 'leer_respuesta'`.

- [ ] **Paso 3: Escribirlo**

Agregar a `src/clasificador_video/guia.py`, después de las importaciones:

```python
@dataclass
class Renglon:
    cuarto: str
    porque: str = ""
    # Que el modelo se haya apartado del patrón de Bruno EN ESTE cuarto.
    # No es un reproche ni estadística: es el aviso del §4.a del spec, para
    # que un cambio de orden no se le pase de largo.
    fuera_del_patron: bool = False


@dataclass
class Respuesta:
    ok: bool
    recorrido: str = ""
    lista: list[Renglon] = field(default_factory=list)
    error: str = ""
```

Y al final del archivo:

```python
def leer_respuesta(texto: str | None) -> Respuesta:
    """Saca la guía de lo que sea que haya contestado el modelo.

    **Nunca revienta**: una respuesta fea es un caso normal, no una
    excepción. Devuelve una `Respuesta` y quien llama decide qué enseñar.

    Lo que NO se hace es adivinar una lista donde no la hay. Media lista es
    peor que ninguna: una guía a la que le falta la cocina hace que se te
    olvide la cocina al editar.
    """
    crudo = ("" if texto is None else str(texto)).strip()
    if not crudo:
        return Respuesta(ok=False, error="El modelo no contestó nada.")

    recorte = _recortar_json(crudo)
    if not recorte:
        return Respuesta(ok=False, error="El modelo contestó con texto en vez de la guía.")

    try:
        datos = json.loads(recorte)
    except (json.JSONDecodeError, ValueError):
        return Respuesta(ok=False, error="La respuesta del modelo no se pudo leer.")

    if not isinstance(datos, dict) or not isinstance(datos.get("orden"), list):
        return Respuesta(
            ok=False,
            error="La respuesta llegó con otra forma: no trae la lista de cuartos.",
        )

    lista: list[Renglon] = []
    for renglon in datos["orden"]:
        if not isinstance(renglon, dict):
            return Respuesta(ok=False, error="La lista trae un renglón que no se entiende.")
        cuarto = renglon.get("cuarto")
        cuarto = cuarto.strip() if isinstance(cuarto, str) else ""
        if not cuarto:
            return Respuesta(ok=False, error="La lista trae un renglón sin nombre de cuarto.")
        porque = renglon.get("porque")
        lista.append(
            Renglon(
                cuarto=cuarto,
                porque=porque.strip() if isinstance(porque, str) else "",
                fuera_del_patron=bool(renglon.get("fuera_del_patron")),
            )
        )

    if not lista:
        return Respuesta(ok=False, error="El modelo devolvió una lista vacía.")

    recorrido = datos.get("recorrido")
    return Respuesta(
        ok=True,
        recorrido=recorrido.strip() if isinstance(recorrido, str) else "",
        lista=lista,
    )


def _recortar_json(texto: str) -> str:
    """El primer objeto JSON que haya dentro de un texto.

    Cuenta llaves en vez de usar una expresión regular porque el JSON anida
    y una regular no sabe contar; y se salta las llaves que van DENTRO de
    una cadena, que es lo que rompería con un cuarto llamado «Sala {grande}».
    """
    inicio = texto.find("{")
    if inicio == -1:
        return ""

    nivel = 0
    en_cadena = False
    escapado = False

    for i in range(inicio, len(texto)):
        c = texto[i]
        if en_cadena:
            if escapado:
                escapado = False
            elif c == "\\":
                escapado = True
            elif c == '"':
                en_cadena = False
            continue
        if c == '"':
            en_cadena = True
        elif c == "{":
            nivel += 1
        elif c == "}":
            nivel -= 1
            if nivel == 0:
                return texto[inicio:i + 1]
    return ""
```

Y agregar `import json` al tope del archivo, debajo de `from __future__ import annotations`.

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: `16 passed`.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Leer la respuesta del modelo sin enseñar nunca media lista"
```

---

### Tarea 5: La revisión de la lista

**Es la regla que sostiene todo el diseño** (§5.1 del spec). Se compara por
**igualdad exacta de cadena**: nada de `strip`, minúsculas ni quitar acentos.
`Recamara 1` contra `Recámara 1` es un cuarto que falta y otro inventado, no un
empate — normalizar aquí escondería justo el caso que esto existe para atrapar.

**Archivos:**
- Modificar: `src/clasificador_video/guia.py`
- Probar: `tests/test_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/test_guia.py`:

```python
def _renglones(*nombres):
    return [guia.Renglon(cuarto=n) for n in nombres]


def test_una_lista_que_cuadra_no_marca_nada():
    r = guia.revisar_lista(_renglones("Fachada", "Sala"), ["Sala", "Fachada"])
    assert not r.faltan and not r.inventados and not r.repetidos


def test_un_cuarto_que_el_modelo_se_salto_sale_como_faltante():
    # El caso que le da razon de ser a todo esto.
    r = guia.revisar_lista(_renglones("Fachada"), ["Fachada", "Cocina"])
    assert r.faltan == ["Cocina"]
    assert not r.inventados


def test_un_cuarto_inventado_sale_marcado():
    r = guia.revisar_lista(_renglones("Fachada", "Bodega"), ["Fachada"])
    assert r.inventados == ["Bodega"]


def test_el_acento_no_se_perdona():
    # Un `.strip().lower()` de mas esconderia justo esto.
    r = guia.revisar_lista(_renglones("Recamara 1"), ["Recámara 1"])
    assert r.faltan == ["Recámara 1"]
    assert r.inventados == ["Recamara 1"]


def test_un_cuarto_repetido_se_marca_aparte():
    # No es invento ni falta, pero en un recorrido significa pasar dos veces
    # por el mismo lugar.
    r = guia.revisar_lista(_renglones("Sala", "Cocina", "Sala"), ["Sala", "Cocina"])
    assert r.repetidos == ["Sala"]
    assert not r.faltan and not r.inventados


def test_los_avisos_estan_en_palabras_de_bruno():
    r = guia.revisar_lista(_renglones("Fachada", "Bodega"), ["Fachada", "Cocina"])
    avisos = guia.avisos_de_la_revision(r)
    assert any("Cocina" in a for a in avisos)
    assert any("Bodega" in a for a in avisos)
    assert not any("null" in a or "None" in a for a in avisos)


def test_sin_nada_que_decir_no_hay_avisos():
    r = guia.revisar_lista(_renglones("Sala"), ["Sala"])
    assert guia.avisos_de_la_revision(r) == []
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: FALLA con `AttributeError: module 'clasificador_video.guia' has no attribute 'revisar_lista'`.

- [ ] **Paso 3: Escribirlo**

Agregar a `src/clasificador_video/guia.py`, junto a las otras dataclases:

```python
@dataclass
class Revision:
    faltan: list[str] = field(default_factory=list)
    inventados: list[str] = field(default_factory=list)
    repetidos: list[str] = field(default_factory=list)

    def limpia(self) -> bool:
        return not (self.faltan or self.inventados or self.repetidos)
```

Y al final del archivo:

```python
def revisar_lista(lista: list[Renglon], cuartos_reales: list[str]) -> Revision:
    """La lista tiene que traer TODOS los cuartos y ninguno inventado.

    Si el modelo se salta uno o se saca uno de la manga, la pantalla lo
    MARCA en vez de enseñar la lista como si nada. Por qué tan en serio: una
    guía a la que le falta la cocina hace que se te olvide la cocina al
    editar, y eso no se nota hasta después de entregar. Misma familia que
    los ocho bugs del 2026-08-22.

    SE COMPARA POR IGUALDAD EXACTA. Nada de `strip`, `lower` ni quitar
    acentos: «Recamara 1» y «Recámara 1» son un cuarto que falta y otro
    inventado, no un empate.
    """
    propuestos = [r.cuarto for r in (lista or [])]
    reales = list(cuartos_reales or [])

    faltan = [c for c in reales if c not in propuestos]
    inventados = [
        c for i, c in enumerate(propuestos)
        if c not in reales and propuestos.index(c) == i
    ]
    repetidos = [
        c for i, c in enumerate(propuestos)
        if propuestos.index(c) == i and propuestos.count(c) > 1
    ]
    return Revision(faltan=faltan, inventados=inventados, repetidos=repetidos)


def avisos_de_la_revision(revision: Revision) -> list[str]:
    """Lo que hay que decirle a Bruno antes de que lea la lista, en sus
    palabras. Vacío cuando no hay nada que decir."""
    avisos = []
    if revision.faltan:
        avisos.append(
            "Le falta un cuarto: " + revision.faltan[0] + "."
            if len(revision.faltan) == 1
            else "Le faltan " + str(len(revision.faltan)) + " cuartos: "
            + ", ".join(revision.faltan) + "."
        )
    if revision.inventados:
        avisos.append("Esto no es tuyo, se lo inventó: " + ", ".join(revision.inventados) + ".")
    if revision.repetidos:
        avisos.append("Repitió: " + ", ".join(revision.repetidos) + ".")
    return avisos
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_guia.py -q
```

Esperado: `23 passed`.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/guia.py tests/test_guia.py
git commit -m "Revisar la lista contra los cuartos de verdad, por igualdad exacta"
```

---

## F3 — La llave y la llamada

### Tarea 6: La llave

**Archivos:**
- Crear: `src/clasificador_video/llave.py`
- Probar: `tests/test_llave.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

`tests/test_llave.py`:

```python
from pathlib import Path

from clasificador_video import llave as mod


def test_guardar_y_leer(tmp_path: Path):
    destino = tmp_path / "llave.json"
    mod.guardar("sk-123456789abcd", destino)
    assert mod.leer(destino) == "sk-123456789abcd"


def test_sin_llave_devuelve_vacio(tmp_path: Path):
    # La primera vez no hay llave, y eso no es un error.
    assert mod.leer(tmp_path / "no-existe.json") == ""


def test_un_archivo_roto_devuelve_vacio(tmp_path: Path):
    destino = tmp_path / "llave.json"
    destino.write_text("{esto no es json", encoding="utf-8")
    assert mod.leer(destino) == ""


def test_borrar(tmp_path: Path):
    destino = tmp_path / "llave.json"
    mod.guardar("sk-123456789abcd", destino)
    mod.borrar(destino)
    assert mod.leer(destino) == ""


def test_borrar_lo_que_no_esta_no_revienta(tmp_path: Path):
    mod.borrar(tmp_path / "no-existe.json")


def test_tapada_ensena_los_ultimos_cuatro():
    assert mod.tapada("sk-123456789abcd") == "••••••••abcd"


def test_una_llave_corta_se_tapa_entera():
    # Ensenar los ultimos cuatro de una llave corta es ensenar media llave,
    # y el punto de taparla es que alguien pueda ver la pantalla de Bruno
    # sin llevarse nada.
    assert mod.tapada("sk-123") == "••••••••"


def test_sin_llave_no_hay_nada_que_tapar():
    assert mod.tapada("") == ""
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_llave.py -q
```

Esperado: FALLA con `ModuleNotFoundError: No module named 'clasificador_video.llave'`.

- [ ] **Paso 3: Escribirlo**

`src/clasificador_video/llave.py`:

```python
"""La llave de la API: se pega una vez y se queda guardada.

DÓNDE SE GUARDA: en `~/.clasificador_video/`, junto a los recientes. Los
tres lugares que se descartaron, cada uno por su motivo:
  - el proyecto de Premiere -> viaja al cliente cuando Bruno le manda el
    proyecto;
  - junto al material -> se copia a discos y se sube a la nube con el
    shooting;
  - el repo -> se sube a GitHub, que es público.

Y NUNCA se imprime ni se escribe en ningún log. El log es el archivo que uno
manda cuando algo falla, o sea el que más ojos ve: una llave ahí dentro es
una llave regalada. Para depurar está `tapada`.

Sin Qt.
"""
from __future__ import annotations

import json
from pathlib import Path

RUTA = Path.home() / ".clasificador_video" / "llave.json"


def _destino(ruta: Path | None) -> Path:
    return RUTA if ruta is None else ruta


def guardar(valor: str, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"llave": str(valor or "").strip()}), encoding="utf-8"
    )


def leer(ruta: Path | None = None) -> str:
    """"" cuando no hay llave guardada, o cuando el archivo está roto.

    Que no haya es el caso de la primera vez, no un error: la pantalla pide
    que la peguen y sigue su vida. Y un archivo corrupto se trata igual, con
    el mismo criterio que `recientes`: cambiar una comodidad por un ladrillo
    sería un mal negocio.
    """
    try:
        datos = json.loads(_destino(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return ""
    if not isinstance(datos, dict):
        return ""
    return str(datos.get("llave") or "")


def borrar(ruta: Path | None = None) -> None:
    _destino(ruta).unlink(missing_ok=True)


def tapada(valor: str) -> str:
    """Cómo se enseña en pantalla: los últimos cuatro y lo demás tapado.

    Una llave de menos de ocho se tapa ENTERA. Enseñar los últimos cuatro de
    una llave corta es enseñar media llave.
    """
    texto = str(valor or "")
    if not texto:
        return ""
    if len(texto) < 8:
        return "••••••••"
    return "••••••••" + texto[-4:]
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_llave.py -q
```

Esperado: `8 passed`.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/llave.py tests/test_llave.py
git commit -m "Guardar la llave de la API fuera del repo y fuera del proyecto"
```

---

### Tarea 7: La llamada

**Archivos:**
- Crear: `src/clasificador_video/ia.py`
- Probar: `tests/test_ia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

`tests/test_ia.py`:

```python
import json
import urllib.error

import pytest

from clasificador_video import ia


class _RespuestaFalsa:
    def __init__(self, payload: dict):
        self._datos = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._datos

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_devuelve_el_texto_del_modelo(monkeypatch):
    monkeypatch.setattr(
        ia.request, "urlopen",
        lambda req, timeout=None: _RespuestaFalsa(
            {"choices": [{"message": {"content": '{"orden": []}'}}]}
        ),
    )
    assert ia.preguntar("sk-123456789abcd", {"model": "x", "messages": []}) == '{"orden": []}'


def test_sin_llave_lo_dice_en_palabras(monkeypatch):
    with pytest.raises(ia.ErrorDeIA) as e:
        ia.preguntar("", {"model": "x", "messages": []})
    assert "llave" in str(e.value).lower()


def test_sin_internet_lo_dice_en_palabras(monkeypatch):
    def cae(req, timeout=None):
        raise urllib.error.URLError("nodename nor servname provided")

    monkeypatch.setattr(ia.request, "urlopen", cae)
    with pytest.raises(ia.ErrorDeIA) as e:
        ia.preguntar("sk-123456789abcd", {"model": "x", "messages": []})
    # En palabras de Bruno, no «URLError».
    assert "URLError" not in str(e.value)
    assert "internet" in str(e.value).lower()


def test_una_llave_que_no_sirve_lo_dice_en_palabras(monkeypatch):
    def rechaza(req, timeout=None):
        raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)

    monkeypatch.setattr(ia.request, "urlopen", rechaza)
    with pytest.raises(ia.ErrorDeIA) as e:
        ia.preguntar("sk-mala", {"model": "x", "messages": []})
    assert "401" not in str(e.value)
    assert "llave" in str(e.value).lower()


def test_el_error_nunca_lleva_la_llave_adentro(monkeypatch):
    # El texto del error termina en pantalla y puede acabar en una captura.
    def cae(req, timeout=None):
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(ia.request, "urlopen", cae)
    with pytest.raises(ia.ErrorDeIA) as e:
        ia.preguntar("sk-secretisima-999", {"model": "x", "messages": []})
    assert "sk-secretisima-999" not in str(e.value)


def test_una_respuesta_con_otra_forma_no_revienta_fea(monkeypatch):
    monkeypatch.setattr(
        ia.request, "urlopen",
        lambda req, timeout=None: _RespuestaFalsa({"otra": "cosa"}),
    )
    with pytest.raises(ia.ErrorDeIA):
        ia.preguntar("sk-123456789abcd", {"model": "x", "messages": []})
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_ia.py -q
```

Esperado: FALLA con `ModuleNotFoundError: No module named 'clasificador_video.ia'`.

- [ ] **Paso 3: Escribirlo**

`src/clasificador_video/ia.py`:

```python
"""La llamada a la API, y nada más.

Chiquito a propósito: no arma el cuerpo y no interpreta la respuesta --las
dos cosas viven en `guia.py`, que se prueba sin red--. Ese corte es lo que
deja cambiar de proveedor en un renglón: DeepSeek habla la misma API que
OpenAI, así que mudarse es esta URL.

Cada caso feo tiene su mensaje propio y **en palabras de Bruno** --«la llave
no sirve» y no «HTTP 401»--, y ninguno lleva la llave adentro: ese texto
termina en pantalla y la pantalla termina en capturas.

Sin Qt.
"""
from __future__ import annotations

import json
import urllib.error
from urllib import request

URL = "https://api.deepseek.com/v1/chat/completions"
ESPERA = 60  # segundos


class ErrorDeIA(Exception):
    """Algo salió mal al pedir la guía. El mensaje ya viene listo para
    enseñarse tal cual."""


def preguntar(llave: str, cuerpo: dict, url: str = URL) -> str:
    """El texto que contestó el modelo.

    Revienta con `ErrorDeIA` y un mensaje en palabras de Bruno. Quien llama
    lo enseña y **no bloquea nada**: exportar sigue funcionando sin guía.
    """
    if not str(llave or "").strip():
        raise ErrorDeIA("Falta la llave. Pégala aquí arriba y vuelve a intentar.")

    peticion = request.Request(
        url,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + str(llave).strip(),
        },
        method="POST",
    )

    try:
        with request.urlopen(peticion, timeout=ESPERA) as respuesta:
            crudo = respuesta.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ErrorDeIA("La llave no sirve. Revísala y vuelve a intentar.") from None
        if e.code == 429:
            raise ErrorDeIA("El servicio está saturado. Intenta en un minuto.") from None
        raise ErrorDeIA("No se pudo armar la guía: el servicio contestó con un error.") from None
    except urllib.error.URLError:
        raise ErrorDeIA("No se pudo armar la guía: no hay internet.") from None
    except OSError:
        raise ErrorDeIA("No se pudo armar la guía: falló la conexión.") from None

    try:
        datos = json.loads(crudo)
        return str(datos["choices"][0]["message"]["content"])
    except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError):
        raise ErrorDeIA("El servicio contestó algo que no se entiende.") from None
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_ia.py -q
```

Esperado: `6 passed`.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/ia.py tests/test_ia.py
git commit -m "Llamar a la API con los errores dichos en palabras de Bruno"
```

---

## F4 — El manifest, la sesión y los cuartos

### Tarea 8: La guía viaja en el manifest

**Archivos:**
- Modificar: `src/clasificador_video/manifest.py`
- Probar: `tests/test_manifest.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/test_manifest.py`:

```python
from clasificador_video.manifest import Guia, Manifest, RenglonDeGuia


def test_un_manifest_sin_guia_no_trae_el_bloque():
    # Si Bruno nunca apreto el boton, o si se cayo la red, todo lo demas
    # funciona igual.
    d = Manifest(proyecto="Casa Lomas", orientacion="horizontal").to_dict()
    assert d["guia"] is None


def test_la_guia_viaja_entera():
    guia = Guia(
        recorrido="Abres por fuera.",
        orden=[
            RenglonDeGuia(cuarto="Fachada", porque="se entra aquí"),
            RenglonDeGuia(cuarto="Alberca", porque="la subí", fuera_del_patron=True),
        ],
    )
    d = Manifest(proyecto="X", orientacion="horizontal", guia=guia).to_dict()
    assert d["guia"]["recorrido"] == "Abres por fuera."
    assert [r["cuarto"] for r in d["guia"]["orden"]] == ["Fachada", "Alberca"]
    assert d["guia"]["orden"][1]["fuera_del_patron"] is True


def test_los_avisos_de_la_revision_NO_viajan():
    # Los de «le falta la cocina» son de la pantalla de Clipify: Bruno ya
    # los vio y decidio exportar de todos modos. Mandarlos a Premiere seria
    # repetirle una advertencia que ya contesto. Lo que si viaja es
    # `fuera_del_patron`, que es otra cosa.
    guia = Guia(recorrido="x", orden=[RenglonDeGuia(cuarto="Sala")])
    d = Manifest(proyecto="X", orientacion="horizontal", guia=guia).to_dict()
    assert "avisos" not in d["guia"]


def test_categoria_path_sigue_sin_numero():
    # El numero es presentacion y lo pone el plugin. Meterlo aqui lo
    # volveria parte del NOMBRE del cuarto.
    from pathlib import Path

    from clasificador_video.manifest import Clip

    c = Clip(orden=0, ruta=Path("/x/a.mp4"), categoria_path=["Cocina"], fps=30.0)
    assert c.to_dict()["categoria_path"] == ["Cocina"]
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -q
```

Esperado: FALLA con `ImportError: cannot import name 'Guia'`.

- [ ] **Paso 3: Escribirlo**

En `src/clasificador_video/manifest.py`, agregar antes de `class Manifest`:

```python
@dataclass
class RenglonDeGuia:
    cuarto: str
    porque: str = ""
    # Que el modelo se apartó del patrón de Bruno en ESTE cuarto. Viaja
    # porque es lo que el panel de Premiere marca: es información que solo
    # tenía la IA. Los avisos de la revisión --«le falta la cocina»-- NO
    # viajan: ésos Bruno ya los vio en Clipify y decidió.
    fuera_del_patron: bool = False

    def to_dict(self) -> dict:
        return {
            "cuarto": self.cuarto,
            "porque": self.porque,
            "fuera_del_patron": self.fuera_del_patron,
        }


@dataclass
class Guia:
    """La guía de edición, congelada. El plugin la LEE y nunca la pide."""

    recorrido: str = ""
    orden: list[RenglonDeGuia] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "recorrido": self.recorrido,
            "orden": [r.to_dict() for r in self.orden],
        }
```

Y en `class Manifest`, agregar el campo y el renglón del diccionario:

```python
@dataclass
class Manifest:
    proyecto: str
    orientacion: str
    clips: list[Clip] = field(default_factory=list)
    # `None` es un proyecto sin guía, y es un caso normal: Bruno nunca
    # apretó el botón, o se cayó la red. Todo lo demás funciona igual.
    guia: Guia | None = None

    def to_dict(self) -> dict:
        return {
            "proyecto": self.proyecto,
            "orientacion": self.orientacion,
            "clips": [c.to_dict() for c in self.clips],
            "guia": self.guia.to_dict() if self.guia is not None else None,
        }
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_manifest.py -q
```

Esperado: todas pasan.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/manifest.py tests/test_manifest.py
git commit -m "Hacer que la guía viaje adentro del manifest"
```

---

### Tarea 9: La guía se guarda con el proyecto

**Archivos:**
- Modificar: `src/clasificador_video/proyecto.py:128-185`
- Probar: `tests/test_proyecto.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/test_proyecto.py`:

```python
def test_la_guia_se_guarda_y_vuelve(tmp_path):
    from clasificador_video import proyecto

    guia = {
        "recorrido": "Abres por fuera.",
        "orden": [{"cuarto": "Sala", "porque": "x", "fuera_del_patron": False}],
        # Los cuartos que habia cuando se armo: con esto se sabe si la guia
        # quedo vieja (§11 del spec).
        "cuartos_de_entonces": ["Sala"],
    }
    data = proyecto.a_dict(
        proyecto="Casa Lomas", rooms=["Sala"], clips=[], bins=_bins_vacios(),
        tamanos={}, duraciones={}, rotaciones={}, guia=guia,
    )
    destino = tmp_path / "x.cvproj"
    proyecto.guardar(destino, data)
    assert proyecto.abrir(destino)["guia"] == guia


def test_un_proyecto_sin_guia_sigue_siendo_valido(tmp_path):
    from clasificador_video import proyecto

    data = proyecto.a_dict(
        proyecto="Casa Lomas", rooms=["Sala"], clips=[], bins=_bins_vacios(),
        tamanos={}, duraciones={}, rotaciones={},
    )
    assert data["guia"] is None
```

`_bins_vacios()` es el ayudante que ya usa el resto de `tests/test_proyecto.py`
— si no existe con ese nombre, usar el que el archivo ya tenga para armar los
bins de prueba, sin inventar uno nuevo.

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -q
```

Esperado: FALLA con `TypeError: a_dict() got an unexpected keyword argument 'guia'`.

- [ ] **Paso 3: Escribirlo**

En `src/clasificador_video/proyecto.py`, agregar el parámetro a `a_dict` (al
final de la firma, con omisión, para que ninguna llamada existente se rompa):

```python
def a_dict(proyecto: str, rooms: list[str], clips: list, bins,
           tamanos: dict, duraciones: dict, rotaciones: dict,
           bytes_conocidos: dict | None = None,
           relativas_conocidas: dict | None = None,
           agrupar_por_cuarto: bool = True,
           modo_horizontal: bool = False,
           carpeta_de_proxies: Path | None = None,
           guia: dict | None = None) -> dict:
```

Y agregar el renglón al diccionario que devuelve, junto a los otros datos que
van al lado de los clips:

```python
        # La guía de edición, tal como se armó. `None` es un proyecto que
        # nunca la pidió, y es lo que hace que los de antes de hoy abran
        # igual que siempre.
        #
        # Guarda ADEMÁS los cuartos que había cuando se armó
        # (`cuartos_de_entonces`): es lo único con lo que se puede saber que
        # la guía quedó vieja porque Bruno agregó un cuarto después (§11 del
        # spec). Sin ese dato habría que adivinarlo, y adivinar en silencio
        # es justo lo que esta app no hace.
        "guia": guia,
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_proyecto.py -q
```

Esperado: todas pasan.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/proyecto.py tests/test_proyecto.py
git commit -m "Guardar la guía con el proyecto, junto a los cuartos que había"
```

---

### Tarea 10: Reordenar los cuartos

**Archivos:**
- Modificar: `src/clasificador_video/rooms.py`
- Probar: `tests/test_rooms.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/test_rooms.py`:

```python
def test_reordenar_deja_los_cuartos_en_el_orden_pedido():
    r = RoomSelection()
    for c in ["Sala", "Cocina", "Fachada"]:
        r.add(c)
    r.reordenar(["Fachada", "Cocina", "Sala"])
    assert r.active_rooms() == ["Fachada", "Cocina", "Sala"]


def test_reordenar_no_crea_cuartos():
    # La guia pudo traer uno inventado y Bruno aceptarla de todos modos.
    # Un cuarto que el no tecleo NUNCA aparece en su rail.
    r = RoomSelection()
    r.add("Sala")
    r.reordenar(["Sala", "Bodega"])
    assert r.active_rooms() == ["Sala"]


def test_reordenar_no_pierde_los_que_no_vienen():
    # Si la lista se salto uno, ese se queda --al final, pero se queda--.
    # Perder un cuarto aqui seria perder la clasificacion de sus clips.
    r = RoomSelection()
    for c in ["Sala", "Cocina", "Baño"]:
        r.add(c)
    r.reordenar(["Cocina", "Sala"])
    assert r.active_rooms() == ["Cocina", "Sala", "Baño"]


def test_reordenar_con_una_lista_vacia_no_mueve_nada():
    r = RoomSelection()
    for c in ["Sala", "Cocina"]:
        r.add(c)
    r.reordenar([])
    assert r.active_rooms() == ["Sala", "Cocina"]
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_rooms.py -q
```

Esperado: FALLA con `AttributeError: 'RoomSelection' object has no attribute 'reordenar'`.

- [ ] **Paso 3: Escribirlo**

Agregar a `class RoomSelection` en `src/clasificador_video/rooms.py`:

```python
    def reordenar(self, nuevo_orden: list[str]) -> None:
        """Acomoda los cuartos como diga la lista. **Solo acomoda.**

        No crea ni borra: la guía pudo traer un cuarto inventado, y uno que
        Bruno no tecleó nunca aparece en su rail. Y los que la lista se haya
        saltado NO se pierden -- se quedan al final, en su orden de antes,
        porque perder un cuarto aquí es perder la clasificación de sus
        clips.

        Y como el orden ES la asignación de teclas, esto le cambia el atajo
        a casi todos. Es lo que Bruno pidió al aceptar la guía: un solo
        orden, el mismo en el rail, en la hoja y en Premiere.
        """
        if not nuevo_orden:
            return
        conocidos = [c for c in nuevo_orden if c in self._order]
        resto = [c for c in self._order if c not in conocidos]
        self._order = conocidos + resto
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_rooms.py -q
```

Esperado: todas pasan.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/rooms.py tests/test_rooms.py
git commit -m "Reordenar los cuartos sin crear ni perder ninguno"
```

---

## F5 — La pantalla

### Tarea 11: La pantalla de la guía

**Archivos:**
- Crear: `src/clasificador_video/ui/pantalla_guia.py`
- Probar: `tests/ui/test_pantalla_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

`tests/ui/test_pantalla_guia.py`:

```python
from clasificador_video import guia as logica
from clasificador_video.ui.pantalla_guia import TIPOS_DE_PROPIEDAD, PantallaGuia


def test_los_seis_tipos_de_propiedad(qtbot):
    # Los que de verdad salieron en sus entregables de 2026. Ni cuatro ni
    # los doce del rubro.
    assert TIPOS_DE_PROPIEDAD == [
        "Casa", "Departamento", "Terreno", "Local", "Quinta de campo", "Hospedaje",
    ]


def test_no_pregunta_para_quien_es_el_video(qtbot):
    # Se fue: todo es para redes, era un clic para decir lo de siempre.
    p = PantallaGuia()
    qtbot.addWidget(p)
    textos = [w.text() for w in p.findChildren(type(p.titulo_lucir))]
    assert not any("para quién" in t.lower() for t in textos)


def test_lo_que_se_quiere_lucir_va_al_frente(qtbot):
    p = PantallaGuia()
    qtbot.addWidget(p)
    # La caja de «lucir» esta ARRIBA de los chips de tipo: es la pregunta
    # principal.
    assert p.caja_lucir.y() < p.fila_tipos.y()


def test_ensena_la_guia_que_llego(qtbot):
    p = PantallaGuia()
    qtbot.addWidget(p)
    p.mostrar_respuesta(
        logica.Respuesta(
            ok=True,
            recorrido="Abres por fuera.",
            lista=[
                logica.Renglon(cuarto="Fachada", porque="se entra aquí"),
                logica.Renglon(cuarto="Alberca", porque="la subí", fuera_del_patron=True),
            ],
        ),
        logica.Revision(),
    )
    texto = p.texto_del_resultado()
    assert "Abres por fuera." in texto
    assert "1. Fachada" in texto
    assert "2. Alberca" in texto


def test_marca_el_cuarto_que_se_salio_del_patron(qtbot):
    p = PantallaGuia()
    qtbot.addWidget(p)
    p.mostrar_respuesta(
        logica.Respuesta(
            ok=True, recorrido="x",
            lista=[logica.Renglon(cuarto="Alberca", porque="la subí", fuera_del_patron=True)],
        ),
        logica.Revision(),
    )
    assert "la subí" in p.texto_del_resultado()


def test_los_avisos_de_la_revision_se_ven_arriba(qtbot):
    p = PantallaGuia()
    qtbot.addWidget(p)
    p.mostrar_respuesta(
        logica.Respuesta(ok=True, recorrido="x", lista=[logica.Renglon(cuarto="Sala")]),
        logica.Revision(faltan=["Cocina"]),
    )
    assert "Cocina" in p.avisos_label.text()


def test_un_error_se_ve_y_no_deja_lista_a_medias(qtbot):
    p = PantallaGuia()
    qtbot.addWidget(p)
    p.mostrar_respuesta(
        logica.Respuesta(ok=False, error="No se pudo armar la guía: no hay internet."),
        logica.Revision(),
    )
    assert "internet" in p.avisos_label.text()
    assert p.texto_del_resultado().strip() == ""
    assert not p.usar_button.isEnabled()


def test_usar_este_orden_emite_el_orden(qtbot):
    p = PantallaGuia()
    qtbot.addWidget(p)
    p.mostrar_respuesta(
        logica.Respuesta(
            ok=True, recorrido="x",
            lista=[logica.Renglon(cuarto="Fachada"), logica.Renglon(cuarto="Sala")],
        ),
        logica.Revision(),
    )
    with qtbot.waitSignal(p.orden_aceptado) as blocker:
        p.usar_button.click()
    assert blocker.args[0] == ["Fachada", "Sala"]
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_guia.py -q
```

Esperado: FALLA con `ModuleNotFoundError: No module named 'clasificador_video.ui.pantalla_guia'`.

- [ ] **Paso 3: Escribirlo**

`src/clasificador_video/ui/pantalla_guia.py`:

```python
"""La pantalla de la guía de edición.

Solo dibuja y conecta. Todo lo que decide algo vive en `guia.py` --armar la
pregunta, leer la respuesta, revisarla-- y todo lo que habla con el mundo en
`ia.py`, `llave.py` y `patron.py`. Si algún día hay que arreglar POR QUÉ una
lista salió mal, no se busca aquí.

Spec: docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from clasificador_video import guia as logica
from clasificador_video.ui.segmented import SegmentedControl

# Los seis que de verdad salieron en los entregables de 2026 de Bruno. No son
# los cuatro de antes ni los doce del rubro: se le ofreció la lista larga
# --oficina, bodega, edificio, penthouse, loft, rancho-- y escogió los suyos.
TIPOS_DE_PROPIEDAD = [
    "Casa",
    "Departamento",
    "Terreno",
    "Local",
    "Quinta de campo",
    "Hospedaje",
]


class PantallaGuia(QWidget):
    """Dos preguntas, el resultado, y «Usar este orden»."""

    guia_pedida = Signal(dict)   # {"lucir": str, "propiedad": str}
    orden_aceptado = Signal(list)  # los cuartos, en el orden aceptado

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pantallaGuia")
        self._respuesta: logica.Respuesta | None = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.setSpacing(14)

        # LA PREGUNTA PRINCIPAL VA PRIMERO. Es lo que Bruno pidió: «sí es
        # importante poder describirle qué quiero lucir de cada propiedad».
        self.titulo_lucir = QLabel("¿Qué quieres lucir?")
        self.titulo_lucir.setObjectName("guiaTitulo")
        self.caja_lucir = QTextEdit()
        self.caja_lucir.setObjectName("guiaLucir")
        self.caja_lucir.setPlaceholderText(
            "La alberca y la terraza. La cocina quedó chica, no la luzcas."
        )
        self.caja_lucir.setFixedHeight(96)
        raiz.addWidget(self.titulo_lucir)
        raiz.addWidget(self.caja_lucir)

        self.titulo_tipo = QLabel("¿Qué tipo de propiedad es?")
        self.titulo_tipo.setObjectName("guiaTitulo")
        self.fila_tipos = SegmentedControl(TIPOS_DE_PROPIEDAD)
        raiz.addWidget(self.titulo_tipo)
        raiz.addWidget(self.fila_tipos)

        self.armar_button = QPushButton("Armar la guía")
        self.armar_button.setObjectName("guiaArmar")
        self.armar_button.clicked.connect(self._al_armar)

        self.usar_button = QPushButton("Usar este orden")
        self.usar_button.setObjectName("guiaUsar")
        self.usar_button.setEnabled(False)
        self.usar_button.clicked.connect(self._al_usar)

        fila = QHBoxLayout()
        fila.addWidget(self.armar_button)
        fila.addWidget(self.usar_button)
        fila.addStretch(1)
        raiz.addLayout(fila)

        # Los avisos van ARRIBA del resultado: son lo que hay que leer antes
        # de creerle a la lista.
        self.avisos_label = QLabel("")
        self.avisos_label.setObjectName("guiaAvisos")
        self.avisos_label.setWordWrap(True)
        raiz.addWidget(self.avisos_label)

        self.resultado = QTextEdit()
        self.resultado.setObjectName("guiaResultado")
        self.resultado.setReadOnly(True)
        raiz.addWidget(self.resultado, stretch=1)

    # --- lo que contestó Bruno ---------------------------------------

    def respuestas(self) -> dict:
        return {
            "lucir": self.caja_lucir.toPlainText().strip(),
            "propiedad": self.fila_tipos.current_text(),
        }

    def _al_armar(self) -> None:
        self.guia_pedida.emit(self.respuestas())

    def _al_usar(self) -> None:
        if self._respuesta and self._respuesta.ok:
            self.orden_aceptado.emit([r.cuarto for r in self._respuesta.lista])

    # --- lo que llegó -------------------------------------------------

    def mostrar_respuesta(self, respuesta: logica.Respuesta,
                          revision: logica.Revision) -> None:
        """Enseña la guía, o el error. **Nunca media lista.**"""
        self._respuesta = respuesta if respuesta.ok else None

        if not respuesta.ok:
            self.avisos_label.setText(respuesta.error)
            self.resultado.setPlainText("")
            self.usar_button.setEnabled(False)
            return

        self.avisos_label.setText("\n".join(logica.avisos_de_la_revision(revision)))
        self.resultado.setPlainText(self._texto(respuesta, revision))
        self.usar_button.setEnabled(True)

    def texto_del_resultado(self) -> str:
        return self.resultado.toPlainText()

    @staticmethod
    def _texto(respuesta: logica.Respuesta, revision: logica.Revision) -> str:
        renglones = []
        for i, r in enumerate(respuesta.lista, start=1):
            marca = "  (este no es tuyo)" if r.cuarto in revision.inventados else ""
            porque = (" — " + r.porque) if r.porque else ""
            renglones.append(f"{i}. {r.cuarto}{porque}{marca}")
        partes = []
        if respuesta.recorrido:
            partes.append(respuesta.recorrido)
        partes.append("\n".join(renglones))
        return "\n\n".join(partes)
```

**Antes de escribirlo, mirar `src/clasificador_video/ui/segmented.py`** y usar
los nombres que ese widget de verdad expone. Si `SegmentedControl` no recibe la
lista en el constructor o su método no se llama `current_text`, se usan los
suyos y se ajustan las pruebas — no se inventa una API que no existe.

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_pantalla_guia.py -q
```

Esperado: `8 passed`.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/ui/pantalla_guia.py tests/ui/test_pantalla_guia.py
git commit -m "Dibujar la pantalla de la guía, con «qué lucir» al frente"
```

---

### Tarea 12: El botón en la barra de título

**Archivos:**
- Modificar: `src/clasificador_video/ui/title_bar.py:38`, `:107-110`
- Probar: `tests/ui/test_title_bar.py`

- [ ] **Paso 1: Escribir la prueba que falla**

Agregar a `tests/ui/test_title_bar.py`:

```python
def test_el_boton_de_la_guia_existe_y_avisa(qtbot):
    from clasificador_video.ui.title_bar import TitleBar

    barra = TitleBar()
    qtbot.addWidget(barra)
    assert "Guía" in barra.guia_button.text()
    with qtbot.waitSignal(barra.guia_requested):
        barra.guia_button.click()


def test_exportar_sigue_siendo_un_clic(qtbot):
    # La guia tiene su PROPIO boton: exportar no gana un paso.
    from clasificador_video.ui.title_bar import TitleBar

    barra = TitleBar()
    qtbot.addWidget(barra)
    with qtbot.waitSignal(barra.export_requested):
        barra.export_button.click()
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_title_bar.py -q
```

Esperado: FALLA con `AttributeError: 'TitleBar' object has no attribute 'guia_button'`.

- [ ] **Paso 3: Escribirlo**

En `src/clasificador_video/ui/title_bar.py`, junto a `export_requested`:

```python
    guia_requested = Signal()
```

Y junto al botón de proxies y al de exportar (antes de `export_button`, para
que quede a su izquierda: la guía se arma **antes** de exportar):

```python
        self.guia_button = _boton("Guía de edición", "", "railButton")
        self.guia_button.clicked.connect(self.guia_requested.emit)
```

Agregarlo al layout en la misma fila y en esa posición — mirar cómo se agregan
`proxies_button` y `export_button` y seguir el mismo patrón.

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_title_bar.py -q
```

Esperado: todas pasan.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/ui/title_bar.py tests/ui/test_title_bar.py
git commit -m "Poner el botón de la guía junto al de exportar"
```

---

### Tarea 13: Conectar todo en la ventana

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py` (cerca de `:723` y `:4459-4495`)
- Probar: `tests/ui/test_main_window_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

`tests/ui/test_main_window_guia.py`:

```python
from clasificador_video import guia as logica


def test_pedir_la_guia_manda_los_cuartos_de_la_sesion(ventana_con_clips, monkeypatch):
    v = ventana_con_clips
    visto = {}

    def falso_preguntar(llave, cuerpo, url=None):
        visto["cuerpo"] = cuerpo
        return '{"recorrido": "x", "orden": [{"cuarto": "Sala"}]}'

    monkeypatch.setattr("clasificador_video.ui.main_window.ia.preguntar", falso_preguntar)
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")

    v.rooms.add("Sala")
    v.pedir_guia({"lucir": "la alberca", "propiedad": "Casa"})

    sistema = visto["cuerpo"]["messages"][0]["content"]
    assert "- Sala" in sistema


def test_aceptar_el_orden_reacomoda_los_cuartos(ventana_con_clips):
    v = ventana_con_clips
    for c in ["Sala", "Cocina"]:
        v.rooms.add(c)
    v.aceptar_orden_de_la_guia(["Cocina", "Sala"])
    assert v.rooms.active_rooms() == ["Cocina", "Sala"]


def test_la_guia_aceptada_viaja_al_manifest(ventana_con_clips, tmp_path):
    v = ventana_con_clips
    v.rooms.add("Sala")
    v.guia_actual = logica.Respuesta(
        ok=True, recorrido="Abres por fuera.",
        lista=[logica.Renglon(cuarto="Sala", porque="se entra aquí")],
    )
    destino = tmp_path / "m.json"
    v.escribir_manifest(destino)

    import json
    d = json.loads(destino.read_text())
    assert d["guia"]["recorrido"] == "Abres por fuera."
    assert d["guia"]["orden"][0]["cuarto"] == "Sala"


def test_sin_guia_el_manifest_sale_igual_que_siempre(ventana_con_clips, tmp_path):
    v = ventana_con_clips
    destino = tmp_path / "m.json"
    v.escribir_manifest(destino)

    import json
    assert json.loads(destino.read_text())["guia"] is None


def test_un_fallo_de_red_no_impide_exportar(ventana_con_clips, tmp_path, monkeypatch):
    from clasificador_video.ia import ErrorDeIA

    v = ventana_con_clips

    def cae(llave, cuerpo, url=None):
        raise ErrorDeIA("No se pudo armar la guía: no hay internet.")

    monkeypatch.setattr("clasificador_video.ui.main_window.ia.preguntar", cae)
    monkeypatch.setattr("clasificador_video.ui.main_window.llave.leer", lambda: "sk-1234abcd")

    v.rooms.add("Sala")
    v.pedir_guia({"lucir": "", "propiedad": "Casa"})  # no revienta

    destino = tmp_path / "m.json"
    v.escribir_manifest(destino)
    assert destino.exists()
```

`ventana_con_clips` es el fixture que ya usan los otros `tests/ui/test_main_window_*.py`
— **mirar `tests/ui/conftest.py` y usar el que exista**, con su nombre real, en
vez de crear uno nuevo.

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_guia.py -q
```

Esperado: FALLA con `AttributeError: ... has no attribute 'pedir_guia'`.

- [ ] **Paso 3: Escribirlo**

En `src/clasificador_video/ui/main_window.py`, agregar a las importaciones del
tope:

```python
from clasificador_video import guia as logica_guia
from clasificador_video import ia, llave, patron
from clasificador_video.manifest import Guia, RenglonDeGuia
from clasificador_video.ui.pantalla_guia import PantallaGuia
```

Junto a `self.title_bar.export_requested.connect(...)` (línea ~723):

```python
        self.title_bar.guia_requested.connect(self._abrir_pantalla_de_guia)
```

Y los métodos nuevos, junto a `_on_export_manifest`:

```python
    def _abrir_pantalla_de_guia(self) -> None:
        """La pantalla de la guía, encima de la ventana.

        No es un QDialog modal, mismo criterio que la paleta de cuartos: un
        modal roba el teclado y hay que cerrarlo para seguir. Es hija de la
        ventana y se muestra encima.
        """
        if self._pantalla_guia is None:
            self._pantalla_guia = PantallaGuia(self)
            self._pantalla_guia.guia_pedida.connect(self.pedir_guia)
            self._pantalla_guia.orden_aceptado.connect(self.aceptar_orden_de_la_guia)
        self._pantalla_guia.show()
        self._pantalla_guia.raise_()

    def pedir_guia(self, respuestas: dict) -> None:
        """Le pide la guía al modelo y la enseña.

        **Nunca revienta hacia afuera**: un fallo de red se dice y ya. La
        app sigue exportando sin guía, que es un manifest perfectamente
        válido.
        """
        cuartos = self.rooms.active_rooms()
        cuerpo = logica_guia.cuerpo_del_request(cuartos, respuestas, patron.leer())
        try:
            crudo = ia.preguntar(llave.leer(), cuerpo)
        except ia.ErrorDeIA as e:
            self._mostrar_guia(logica_guia.Respuesta(ok=False, error=str(e)))
            return
        self._mostrar_guia(logica_guia.leer_respuesta(crudo))

    def _mostrar_guia(self, respuesta) -> None:
        revision = logica_guia.revisar_lista(respuesta.lista, self.rooms.active_rooms())
        self.guia_actual = respuesta if respuesta.ok else None
        if self._pantalla_guia is not None:
            self._pantalla_guia.mostrar_respuesta(respuesta, revision)

    def aceptar_orden_de_la_guia(self, orden: list) -> None:
        """Ese orden pasa a ser EL orden: rail, hoja y Premiere."""
        self.rooms.reordenar(list(orden))
        self._cuartos_de_la_guia = self.rooms.active_rooms()
        self._refrescar_cuartos()
```

`_refrescar_cuartos` es el método que la ventana ya usa para repintar el rail y
la hoja cuando cambian los cuartos — **buscarlo y llamar al que exista** (el
que usan `move` y `mover_a` desde el rail), no crear uno nuevo.

En `__init__`, junto a los otros atributos de estado:

```python
        # La guía armada, si es que se armó. `None` es lo normal.
        self.guia_actual = None
        self._pantalla_guia = None
        # Los cuartos que había cuando se aceptó la guía. Con esto se sabe
        # si quedó vieja (§11 del spec).
        self._cuartos_de_la_guia: list[str] = []
```

Y en `escribir_manifest` (línea ~4474), al armar el `Manifest`, pasarle la guía:

```python
        manifest = Manifest(
            ...,  # lo que ya recibía, sin tocar
            guia=self._guia_para_el_manifest(),
        )
```

Con su ayudante:

```python
    def _guia_para_el_manifest(self):
        """La guía en la forma que viaja, o `None`.

        Los avisos de la revisión NO viajan: Bruno ya los vio en la pantalla
        y decidió exportar de todos modos. Lo que sí viaja es
        `fuera_del_patron`, que es información que solo tenía la IA.
        """
        if self.guia_actual is None or not self.guia_actual.ok:
            return None
        return Guia(
            recorrido=self.guia_actual.recorrido,
            orden=[
                RenglonDeGuia(
                    cuarto=r.cuarto, porque=r.porque, fuera_del_patron=r.fuera_del_patron
                )
                for r in self.guia_actual.lista
            ],
        )
```

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_guia.py -q
```

Esperado: `5 passed`.

- [ ] **Paso 5: Correr la suite completa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

Esperado: todo verde. Si algo de `tests/ui/test_main_window*.py` se rompió por
la firma nueva del `Manifest`, se arregla aquí.

- [ ] **Paso 6: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_guia.py
git commit -m "Conectar la guía: pedirla, aceptarla y mandarla en el manifest"
```

---

### Tarea 14: El aviso de la guía vieja

Es el §11 del spec. Bruno puede armar la guía, seguir clasificando, agregar un
cuarto y exportar — y la guía guardada ya no hablaría de lo que hay.

**Archivos:**
- Modificar: `src/clasificador_video/ui/main_window.py`
- Probar: `tests/ui/test_main_window_guia.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

Agregar a `tests/ui/test_main_window_guia.py`:

```python
def test_la_guia_queda_vieja_al_agregar_un_cuarto(ventana_con_clips):
    v = ventana_con_clips
    v.rooms.add("Sala")
    v.aceptar_orden_de_la_guia(["Sala"])
    assert not v.guia_quedo_vieja()

    v.rooms.add("Terraza")
    assert v.guia_quedo_vieja()


def test_el_aviso_dice_cual_cuarto_se_agrego(ventana_con_clips):
    v = ventana_con_clips
    v.rooms.add("Sala")
    v.aceptar_orden_de_la_guia(["Sala"])
    v.rooms.add("Terraza")
    assert "Terraza" in v.aviso_de_guia_vieja()


def test_sin_guia_no_hay_nada_que_avisar(ventana_con_clips):
    v = ventana_con_clips
    v.rooms.add("Sala")
    assert not v.guia_quedo_vieja()
    assert v.aviso_de_guia_vieja() == ""


def test_reordenar_a_mano_no_deja_vieja_la_guia(ventana_con_clips):
    # Mover un cuarto de lugar no cambia QUE cuartos hay. Avisar ahi seria
    # una alarma que suena por nada, y las alarmas que suenan por nada se
    # aprenden a ignorar.
    v = ventana_con_clips
    for c in ["Sala", "Cocina"]:
        v.rooms.add(c)
    v.aceptar_orden_de_la_guia(["Sala", "Cocina"])
    v.rooms.move("Cocina", -1)
    assert not v.guia_quedo_vieja()
```

- [ ] **Paso 2: Correr y ver que falla**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_guia.py -q
```

Esperado: FALLA con `AttributeError: ... has no attribute 'guia_quedo_vieja'`.

- [ ] **Paso 3: Escribirlo**

Agregar a `main_window.py`, junto a los otros métodos de la guía:

```python
    def guia_quedo_vieja(self) -> bool:
        """¿La guía guardada habla de otros cuartos que los que hay?

        Se comparan los NOMBRES, no el orden: mover un cuarto de lugar no
        cambia qué cuartos hay, y avisar ahí sería una alarma que suena por
        nada -- y las alarmas que suenan por nada se aprenden a ignorar.
        """
        if self.guia_actual is None or not self._cuartos_de_la_guia:
            return False
        return set(self._cuartos_de_la_guia) != set(self.rooms.active_rooms())

    def aviso_de_guia_vieja(self) -> str:
        """El aviso en palabras de Bruno, o "" si no hay nada que decir."""
        if not self.guia_quedo_vieja():
            return ""
        antes = set(self._cuartos_de_la_guia)
        ahora = self.rooms.active_rooms()
        nuevos = [c for c in ahora if c not in antes]
        idos = [c for c in self._cuartos_de_la_guia if c not in set(ahora)]
        if nuevos:
            return "Tu guía es de antes de agregar " + ", ".join(nuevos) + "."
        if idos:
            return "Tu guía todavía habla de " + ", ".join(idos) + "."
        return "Tu guía es de antes de cambiar los cuartos."
```

Y en `_on_export_manifest`, **antes** de abrir el diálogo de guardar:

```python
        aviso = self.aviso_de_guia_vieja()
        if aviso:
            respuesta = QMessageBox.question(
                self, "Tu guía quedó vieja",
                aviso + "\n\n¿La exportas así, o la vuelves a armar?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if respuesta == QMessageBox.No:
                self._abrir_pantalla_de_guia()
                return
```

Se AVISA, no se decide solo: es la misma regla que sostiene el diálogo de
proxies — *la app propone, nunca adivina en silencio.*

Si `QMessageBox` no está importado en `main_window.py`, agregarlo a la
importación de `PySide6.QtWidgets` que ya existe.

- [ ] **Paso 4: Correr y ver que pasa**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ui/test_main_window_guia.py -q
```

Esperado: `9 passed`.

- [ ] **Paso 5: Commit**

```bash
git add src/clasificador_video/ui/main_window.py tests/ui/test_main_window_guia.py
git commit -m "Avisar al exportar cuando la guía quedó de antes de los cuartos de ahora"
```

---

### Tarea 15: Verificación visual de Clipify

**Nunca afirmar que algo se ve bien sin haber visto el pixel.** Los archivos
temporales van al scratchpad de la sesión, **nunca al repo**.

- [ ] **Paso 1: Capturar la pantalla de la guía, vacía**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "
from PySide6.QtWidgets import QApplication
from clasificador_video.ui.pantalla_guia import PantallaGuia
from clasificador_video.ui import theme
app = QApplication([])
app.setStyleSheet(theme.QSS)
p = PantallaGuia(); p.resize(640, 560); p.show()
p.grab().save('/tmp/claude-501/guia-vacia.png')
"
```

Si el QSS no se llama `theme.QSS`, mirar `src/clasificador_video/ui/theme.py` y
usar el nombre real.

- [ ] **Paso 2: Mirar la imagen**

Abrir `/tmp/claude-501/guia-vacia.png` con la herramienta de lectura de
archivos y comprobar con los ojos:

- «¿Qué quieres lucir?» está **arriba**, con caja grande.
- Los seis tipos se ven completos, sin texto cortado —«Quinta de campo» es el
  más largo.
- **No aparece** «¿Para quién es el video?».

- [ ] **Paso 3: Capturar una guía que se salió del patrón**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "
from PySide6.QtWidgets import QApplication
from clasificador_video import guia as L
from clasificador_video.ui.pantalla_guia import PantallaGuia
from clasificador_video.ui import theme
app = QApplication([])
app.setStyleSheet(theme.QSS)
p = PantallaGuia(); p.resize(640, 560)
p.mostrar_respuesta(
    L.Respuesta(ok=True, recorrido='Abres por fuera, con una aérea de la fachada.',
                lista=[L.Renglon('Fachada', 'se entra por aquí'),
                       L.Renglon('Alberca', 'la subí porque dijiste que es lo que hay que lucir', True),
                       L.Renglon('Cocina', 'va temprano, como siempre')]),
    L.Revision())
p.show()
p.grab().save('/tmp/claude-501/guia-fuera-del-patron.png')
"
```

- [ ] **Paso 4: Mirar la imagen**

Comprobar que el renglón de la Alberca **se distingue** de los otros dos y que
su razón se lee completa.

- [ ] **Paso 5: Commit si hubo ajustes de estilo**

```bash
git add -u
git commit -m "Ajustar el dibujo de la pantalla de la guía tras verla"
```

Si nada cambió, no hay commit — pero sí queda dicho en el reporte que las dos
imágenes se miraron.

---

## F6 — El plugin

### Tarea 16: El número del cuarto

**Archivos:**
- Crear: `uxp-plugin/js/numeroDeCuarto.js`
- Crear: `uxp-plugin/pruebas/numeroDeCuarto.pruebas.js`
- Modificar: `uxp-plugin/pruebas/correr.js`

- [ ] **Paso 1: Escribir las pruebas que fallan**

`uxp-plugin/pruebas/numeroDeCuarto.pruebas.js`:

```javascript
// Los casos del prefijo numerico de los cuartos. Logica pura: corren con
// `node uxp-plugin/pruebas/correr.js`, sin abrir Premiere.
module.exports = function (ctx) {
  return [
    {
      nombre: "conNumero pone el prefijo de dos digitos",
      fn: () => {
        const r = ctx.conNumero("Cocina", 3);
        return { ok: r === "03. Cocina", detalle: r };
      },
    },
    {
      nombre: "conNumero no se rompe pasando de nueve",
      fn: () => {
        const r = ctx.conNumero("Cocina", 12);
        return { ok: r === "12. Cocina", detalle: r };
      },
    },
    {
      nombre: "sinNumero quita el prefijo",
      fn: () => {
        const r = ctx.sinNumero("03. Cocina");
        return { ok: r === "Cocina", detalle: r };
      },
    },
    {
      // LO QUE ESTO EXISTE PARA EVITAR: un numero que Bruno escribio a mano
      // no es nuestro y no se toca. Misma regla que las marcas del nombre.
      nombre: "un numero sin punto no es nuestro prefijo",
      fn: () => {
        const r = ctx.sinNumero("2 Recamaras");
        return { ok: r === "2 Recamaras", detalle: r };
      },
    },
    {
      nombre: "solo se quita UN prefijo, no todos",
      fn: () => {
        const r = ctx.sinNumero("01. 2 Recamaras");
        return { ok: r === "2 Recamaras", detalle: r };
      },
    },
    {
      nombre: "un cuarto sin numero se queda igual",
      fn: () => {
        const r = ctx.sinNumero("Cocina");
        return { ok: r === "Cocina", detalle: r };
      },
    },
    {
      // EL CASO DE LA SEGUNDA PASADA (§5.2 del spec): sin esto, Premiere
      // crea una segunda Cocina y los clips quedan repartidos en dos.
      nombre: "03. Cocina y 05. Cocina son la misma Cocina",
      fn: () => {
        const r = ctx.esElMismoCuarto("03. Cocina", "05. Cocina");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "Cocina y 05. Cocina son la misma Cocina",
      fn: () => {
        const r = ctx.esElMismoCuarto("Cocina", "05. Cocina");
        return { ok: r === true, detalle: String(r) };
      },
    },
    {
      nombre: "Cocina y Comedor no son el mismo cuarto",
      fn: () => {
        const r = ctx.esElMismoCuarto("03. Cocina", "04. Comedor");
        return { ok: r === false, detalle: String(r) };
      },
    },
    {
      // Igualdad EXACTA despues de quitar el numero: el acento no se
      // perdona, igual que en la revision de la lista.
      nombre: "Recamara 1 y Recámara 1 no son el mismo cuarto",
      fn: () => {
        const r = ctx.esElMismoCuarto("01. Recamara 1", "01. Recámara 1");
        return { ok: r === false, detalle: String(r) };
      },
    },
  ];
};
```

- [ ] **Paso 2: Enchufar las pruebas nuevas al runner**

En `uxp-plugin/pruebas/correr.js`, agregar `"js/numeroDeCuarto.js"` al arreglo
`ARCHIVOS`, y cambiar la línea de los casos para que junte los dos archivos de
pruebas:

```javascript
const casos = [].concat(
  require("./ordenSugerido.pruebas.js")(contexto),
  require("./numeroDeCuarto.pruebas.js")(contexto)
);
```

(En la Tarea 19, cuando `ordenSugerido.js` se borre, esta línea se queda solo
con la segunda.)

- [ ] **Paso 3: Correr y ver que falla**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: FALLA con `Falta js/numeroDeCuarto.js -- no se puede correr nada.`

- [ ] **Paso 4: Escribirlo**

`uxp-plugin/js/numeroDeCuarto.js`:

```javascript
// El numero que llevan las carpetas de cuartos: «03. Cocina».
//
// POR QUE EXISTE: Premiere ordena los bins por abecedario, asi que el numero
// es lo unico que sostiene el orden de la guia. Y la estructura de Bruno ya
// numera («02. Clip»), asi que no es un idioma nuevo.
//
// EL PREFIJO ES NUESTRO Y SOLO EL NUESTRO: digitos, punto, espacio. Un cuarto
// que Bruno haya llamado «2 Recamaras» no trae punto y no se toca. Es la
// misma regla que las marcas de estado en el nombre de los clips: se quita lo
// que pusimos nosotros, no lo que escribio el.
//
// Logica pura: se prueba con `node uxp-plugin/pruebas/correr.js`.
//
// Spec: docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md

const PREFIJO = /^\d+\.\s/;

// "Cocina" + 3 -> "03. Cocina". Dos digitos, y mas si hiciera falta.
function conNumero(nombre, posicion) {
  const n = String(posicion);
  return (n.length < 2 ? "0" + n : n) + ". " + String(nombre || "");
}

// "03. Cocina" -> "Cocina". Quita UN prefijo, no todos: «01. 2 Recamaras» es
// la carpeta numerada de un cuarto que se llama «2 Recamaras».
function sinNumero(nombre) {
  return String(nombre || "").replace(PREFIJO, "");
}

// Si dos nombres de carpeta son el mismo cuarto, tengan el numero que tengan.
//
// Se compara por IGUALDAD EXACTA despues de quitar el numero: nada de
// minusculas ni quitar acentos. «Recamara 1» y «Recámara 1» son dos cuartos
// distintos, igual que en la revision de la lista.
function esElMismoCuarto(unNombre, otroNombre) {
  return sinNumero(unNombre) === sinNumero(otroNombre);
}
```

- [ ] **Paso 5: Correr y ver que pasa**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: las diez nuevas en OK, y las de `ordenSugerido` siguen pasando.

- [ ] **Paso 6: Commit**

```bash
git add uxp-plugin/js/numeroDeCuarto.js uxp-plugin/pruebas/numeroDeCuarto.pruebas.js uxp-plugin/pruebas/correr.js
git commit -m "Poner y quitar el número de la carpeta de un cuarto"
```

---

### Tarea 17: Crear el cuarto renumerando en vez de duplicar

**Archivos:**
- Modificar: `uxp-plugin/js/bins.js`
- Modificar: `uxp-plugin/js/estructura.js` (`caminoDelClip`)
- Modificar: `uxp-plugin/js/processManifest.js:45-71`

- [ ] **Paso 1: Averiguar cómo se renombra un bin DE VERDAD**

**No le creas a la documentación de Adobe.** Ya falló tres veces el mismo día
en este mismo plugin. Antes de llamar a nada, imprimir qué hay:

En el panel del plugin, con un proyecto abierto, correr una vez:

```javascript
const premierepro = require("premierepro");
const project = await premierepro.Project.getActiveProject();
const rootItem = await project.getRootItem();
const rootFolder = premierepro.FolderItem.cast(rootItem);
const alguno = (await rootFolder.getItems())[0];
logToPanel(JSON.stringify(Object.getOwnPropertyNames(Object.getPrototypeOf(alguno))));
```

Anotar en el commit qué método salió de verdad. Lo que sigue supone
`createSetNameAction(nombre)` corrido dentro de `runTransaction`, que es el
patrón que el resto del plugin ya usa — **si el nombre real es otro, se usa el
real.**

- [ ] **Paso 2: Escribir `resolverCuarto` en `bins.js`**

Agregar a `uxp-plugin/js/bins.js`:

```javascript
// La carpeta de un cuarto, con su numero al dia.
//
// EL CASO QUE ESTO EVITA (§5.2 del spec): Bruno importa mas clips del mismo
// rodaje, el orden de la guia salio distinto, y la Cocina que era «03.
// Cocina» llega como «05. Cocina». Buscando por nombre exacto, Premiere le
// crea una SEGUNDA carpeta y los clips del mismo cuarto quedan repartidos en
// dos -- sin que nada avise. Es la familia de los ocho bugs del 2026-08-22.
//
// Por eso se busca por el nombre SIN numero, y si aparece con otro, se le
// cambia el numero a esa en vez de crear otra.
async function resolverCuarto(project, carpetaDeClips, nombreConNumero) {
  const premierepro = require("premierepro");

  const items = (await carpetaDeClips.getItems()) || [];
  const existente = items.find(
    (i) => i && esElMismoCuarto(i.name, nombreConNumero)
  );

  if (existente) {
    if (existente.name !== nombreConNumero) {
      runTransaction(
        project,
        () => existente.createSetNameAction(nombreConNumero),
        "Renumerar " + existente.name + " -> " + nombreConNumero
      );
    }
    return premierepro.FolderItem.cast(existente);
  }

  return await resolveBinChain(project, carpetaDeClips, [nombreConNumero]);
}
```

**Ojo:** `resolveBinChain` recibe hoy `(project, rootFolder, categoryPath)`.
Aquí se le pasa `carpetaDeClips` como carpeta de arranque, que es lo que hace
falta — comprobar la firma real antes de llamarla y ajustar si hace falta.

- [ ] **Paso 3: Dar el número en `caminoDelClip`**

En `uxp-plugin/js/estructura.js`, cambiar `caminoDelClip` para que reciba el
orden de la guía:

```javascript
// El camino completo de un clip: su cuarto y su estado, colgados de
// «02. Clip». La app manda ["Cocina", "Picks"] y aqui se vuelve
// ["02. Clip", "03. Cocina", "Picks"].
//
// `ordenDeLaGuia` son los cuartos en el orden que Bruno acepto. Si el cuarto
// no esta ahi --o si el manifest no trajo guia-- la carpeta se crea SIN
// numero, exactamente como antes de que esto existiera.
function caminoDelClip(categoryPath, ordenDeLaGuia) {
  const camino = (categoryPath || []).slice();
  const orden = ordenDeLaGuia || [];
  if (camino.length) {
    const lugar = orden.indexOf(camino[0]);
    if (lugar !== -1) camino[0] = conNumero(camino[0], lugar + 1);
  }
  return [CARPETA_DE_CLIPS].concat(camino);
}
```

- [ ] **Paso 4: Usarlo en `processManifest.js`**

En `uxp-plugin/js/processManifest.js`, sacar el orden del manifest una vez al
principio de `processManifest`:

```javascript
  // Los cuartos en el orden que Bruno acepto en Clipify, o vacio si este
  // proyecto no trae guia. Un manifest sin guia crea las carpetas sin
  // numero, igual que siempre.
  const ordenDeLaGuia = ((manifest.guia && manifest.guia.orden) || []).map(
    (r) => r.cuarto
  );
```

Y pasárselo a las tres llamadas de `caminoDelClip` (líneas ~46, ~65 y ~71):

```javascript
      const targetFolder = await resolveBinChain(
        project, rootFolder, caminoDelClip(categoryPath, ordenDeLaGuia));
```

```javascript
      logToPanel("OK: " + nombreArchivo + " -> " + caminoDelClip(categoryPath, ordenDeLaGuia).join(" > "));
```

```javascript
      const donde = caminoDelClip(categoryPath, ordenDeLaGuia).join(" > ");
```

Y donde se resuelve la carpeta del cuarto, usar `resolverCuarto` para que la
renumeración pase de verdad — el primer segmento del camino es el cuarto y es
el único que lleva número; el resto (`Picks`, por ejemplo) sigue por
`resolveBinChain`.

- [ ] **Paso 5: Correr las pruebas de node**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: todo en OK. `caminoDelClip` ya se evalúa ahí (`estructura.js` está en
la lista de archivos), así que conviene agregarle dos casos a
`numeroDeCuarto.pruebas.js`:

```javascript
    {
      nombre: "caminoDelClip numera el cuarto segun la guia",
      fn: () => {
        const r = ctx.caminoDelClip(["Cocina", "Picks"], ["Fachada", "Cocina"]);
        return { ok: r.join(" > ") === "02. Clip > 02. Cocina > Picks", detalle: r.join(" > ") };
      },
    },
    {
      nombre: "sin guia, caminoDelClip deja el cuarto sin numero",
      fn: () => {
        const r = ctx.caminoDelClip(["Cocina"], []);
        return { ok: r.join(" > ") === "02. Clip > Cocina", detalle: r.join(" > ") };
      },
    },
```

- [ ] **Paso 6: Commit**

```bash
git add uxp-plugin/js/bins.js uxp-plugin/js/estructura.js uxp-plugin/js/processManifest.js uxp-plugin/pruebas/numeroDeCuarto.pruebas.js
git commit -m "Numerar las carpetas de cuartos y renumerar en vez de duplicar"
```

---

### Tarea 18: La pestaña, vaciada

**Archivos:**
- Modificar: `uxp-plugin/js/pestanaOrden.js` (378 líneas hoy; queda mucho más corto)
- Modificar: `uxp-plugin/js/importarManifest.js` (guardar la guía que llegó)

- [ ] **Paso 1: Guardar la guía al importar**

En `uxp-plugin/js/importarManifest.js`, donde el manifest ya leído se usa,
guardar su guía en una variable de módulo que la pestaña pueda leer:

```javascript
// La guia que trajo el ultimo manifest importado, o null. La pestana la LEE
// y nunca la pide: se armo en Clipify y viaja congelada.
let guiaDelManifest = null;

function guardarGuia(manifest) {
  guiaDelManifest = (manifest && manifest.guia) || null;
}

function guiaImportada() {
  return guiaDelManifest;
}
```

Llamar a `guardarGuia(manifest)` justo donde el manifest se acepta, antes de
importar los clips.

- [ ] **Paso 2: Reescribir la pestaña**

`uxp-plugin/js/pestanaOrden.js` queda así, completo:

```javascript
// La pestana «Guia de edicion»: enseña la guia que se armo en Clipify.
//
// NO PREGUNTA NADA. No tiene llave, no toca la red y no espera. La guia se
// arma en Clipify --donde los cuartos nacen y donde Bruno acaba de ver el
// material-- y viaja congelada adentro del manifest. Si quiere otra, regresa
// a Clipify.
//
// Aqui vivian las preguntas, la llave de DeepSeek y el armado del prompt. Se
// fueron completas el 2026-09-14, no comentadas: git guarda el historial.
//
// LA PESTANA NO ESCRIBE NADA EN EL PROYECTO. Ni una carpeta, ni un clip, ni
// el timeline. Es de lectura entera, y esa es la razon por la que puede vivir
// dentro del mismo plugin que si escribe sin dar miedo.
//
// Spec: docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md

let pestanaArmada = false;

function abrirPestanaOrden(hoja) {
  if (pestanaArmada) return;
  pestanaArmada = true;
  dibujarGuia(hoja, guiaImportada());
}

// Se separa del `abrir` para poder repintarla cuando llegue un manifest nuevo
// sin volver a armar la pestana.
function dibujarGuia(hoja, guia) {
  hoja.innerHTML = "";

  if (!guia || !guia.orden || !guia.orden.length) {
    // Que no traiga guia NO es un error: es un proyecto que se exporto sin
    // apretar el boton, o de antes de que esto existiera. Se dice con esas
    // palabras y no se inventa una.
    const vacio = document.createElement("p");
    vacio.className = "vacio";
    vacio.textContent =
      "Este proyecto no trae guía de edición. Se arma en Clipify, " +
      "con el botón «Guía de edición», antes de exportar.";
    hoja.appendChild(vacio);
    return;
  }

  if (guia.recorrido) {
    const parrafo = document.createElement("p");
    parrafo.className = "guia-recorrido";
    parrafo.textContent = guia.recorrido;
    hoja.appendChild(parrafo);
  }

  const lista = document.createElement("ol");
  lista.className = "guia-orden";
  for (const renglon of guia.orden) {
    const li = document.createElement("li");

    const nombre = document.createElement("span");
    nombre.className = "guia-cuarto";
    nombre.textContent = renglon.cuarto;
    li.appendChild(nombre);

    if (renglon.porque) {
      const porque = document.createElement("span");
      // El aviso de que se salio del patron de Bruno se ve DISTINTO del
      // resto: es informacion que solo tenia la IA, y es lo unico que hay
      // que leer con atencion.
      porque.className = renglon.fuera_del_patron
        ? "guia-porque fuera-del-patron"
        : "guia-porque";
      porque.textContent = " — " + renglon.porque;
      li.appendChild(porque);
    }

    lista.appendChild(li);
  }
  hoja.appendChild(lista);
}
```

- [ ] **Paso 3: Quitar el CSS que sobra y agregar el que falta**

En el CSS del panel (el archivo que `index.html` carga), borrar las reglas de
las preguntas y la llave, y agregar:

```css
.guia-recorrido { margin: 0 0 12px; line-height: 1.5; }
.guia-orden { margin: 0; padding-left: 20px; }
.guia-orden li { margin-bottom: 6px; }
.guia-porque { opacity: 0.7; }
.guia-porque.fuera-del-patron { opacity: 1; font-style: italic; }
```

El color del `fuera-del-patron` sale de la paleta que el panel ya usa — mirar el
CSS existente y usar su variable, no un color nuevo suelto.

- [ ] **Paso 4: Quitar los `<script src>` que sobran**

En `uxp-plugin/index.html`, quitar las etiquetas de `ordenSugerido.js`,
`deepseek.js`, `llave.js` y `cuartosDelProyecto.js`, y agregar la de
`numeroDeCuarto.js`. **Que `numeroDeCuarto.js` cargue ANTES que `bins.js` y
`estructura.js`**, que son quienes lo usan.

- [ ] **Paso 5: Renombrar la pestaña en la interfaz**

Donde el panel escribe el nombre de la pestaña, cambiar «Orden sugerido» por
**«Guía de edición»**. Ya no sugiere: enseña lo que Bruno aceptó.

- [ ] **Paso 6: Commit**

```bash
git add uxp-plugin/js/pestanaOrden.js uxp-plugin/js/importarManifest.js uxp-plugin/index.html uxp-plugin/
git commit -m "Vaciar la pestaña: ahora solo enseña la guía que trajo el manifest"
```

---

### Tarea 19: Borrar lo que sobra

**Un archivo nuevo reemplaza a uno viejo → se borra el viejo en el mismo
commit**, no se deja «por si acaso». Git ya guarda el historial.

**Archivos:**
- Borrar: `uxp-plugin/js/ordenSugerido.js`, `uxp-plugin/js/deepseek.js`, `uxp-plugin/js/llave.js`, `uxp-plugin/js/cuartosDelProyecto.js`, `uxp-plugin/pruebas/ordenSugerido.pruebas.js`
- Modificar: `uxp-plugin/pruebas/correr.js`

- [ ] **Paso 1: Comprobar que ya nadie los usa**

```bash
grep -rn "ordenSugerido\|deepseek\|leerLlave\|guardarLlave\|llaveTapada\|cuartosDeLosBins\|mensajeDeCuartos\|pedirOrden\|revisarLista\|leerRespuesta\|cuerpoDelRequest" uxp-plugin/ --include="*.js" --include="*.html"
```

Esperado: solo los propios archivos que se van a borrar, y las pruebas de
`autocheck-tests.js` que los usen. **Si sale algo más, se arregla antes de
borrar.**

- [ ] **Paso 2: Borrarlos**

```bash
git rm uxp-plugin/js/ordenSugerido.js uxp-plugin/js/deepseek.js uxp-plugin/js/llave.js uxp-plugin/js/cuartosDelProyecto.js uxp-plugin/pruebas/ordenSugerido.pruebas.js
```

- [ ] **Paso 3: Limpiar el runner**

En `uxp-plugin/pruebas/correr.js`, dejar `ARCHIVOS` con lo que queda:

```javascript
const ARCHIVOS = [
  "js/estructura.js",
  "js/numeroDeCuarto.js",
];
```

Y los casos con un solo archivo:

```javascript
const casos = require("./numeroDeCuarto.pruebas.js")(contexto);
```

Actualizar también el comentario de arriba de `ARCHIVOS`, que hoy explica por
qué entraban `llave.js` y `cuartosDelProyecto.js` — ya no entran.

- [ ] **Paso 4: Quitar del arnés de Premiere lo que ya no existe**

En `uxp-plugin/js/autocheck-tests.js`, borrar las pruebas que llamen a las
funciones que se fueron (las de `cuartosDeLosBins` y las del orden sugerido).
Las del resto del plugin se quedan.

- [ ] **Paso 5: Correr las pruebas de node**

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: los doce casos del número de cuarto en OK, `0 fallidas`.

- [ ] **Paso 6: Commit**

```bash
git add -A uxp-plugin/
git commit -m "Borrar del plugin lo que preguntaba y llamaba a la IA"
```

---

### Tarea 20: Verificación visual del panel

El panel es HTML, así que se sirve y se mira — es el segundo camino del
`CLAUDE.md`. Los archivos temporales van al scratchpad, **no al repo**.

- [ ] **Paso 1: Armar una página de prueba en el scratchpad**

Copiar `uxp-plugin/index.html` y su CSS al scratchpad, y agregarle al final un
`<script>` que llame a `dibujarGuia` con una guía de mentiras — una con un
renglón `fuera_del_patron: true`, y otra vacía para el caso «este proyecto no
trae guía».

- [ ] **Paso 2: Servirlo y mirarlo**

```bash
python3 -m http.server 8765 --directory /tmp/claude-501/panel
```

Abrirlo con la herramienta de navegador, sacar captura de las dos, y **leer las
imágenes**.

Comprobar con los ojos:

- El párrafo del recorrido se lee completo y no se sale de la columna angosta.
- El renglón `fuera_del_patron` **se distingue** de los demás.
- La pantalla sin guía dice qué hacer, no solo que no hay.

- [ ] **Paso 3: Apagar el servidor y borrar lo temporal**

```bash
git status --short
```

Esperado: **nada** del scratchpad dentro del repo.

- [ ] **Paso 4: Commit si hubo ajustes**

```bash
git add -u uxp-plugin/
git commit -m "Ajustar el dibujo del panel de la guía tras verlo"
```

---

## F7 — Cierre

### Tarea 21: La documentación y la suite entera

**Archivos:**
- Modificar: `README.md`, `docs/DESARROLLO.md`, `docs/superpowers/CONTEXTO-Y-METAS.md`, `CLAUDE.md`

- [ ] **Paso 1: Correr todo**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

```bash
node uxp-plugin/pruebas/correr.js
```

Esperado: los dos verdes. **Si algo falla, se arregla antes de seguir** — no se
documenta como terminado lo que no pasó.

- [ ] **Paso 2: `README.md`**

Agregar la guía de edición a lo que la app hace, escrito para quien la usa:
que se arma con su botón antes de exportar, que pide qué quieres lucir y el
tipo de propiedad, y que viaja a Premiere. **Y que hace falta una llave** —
dónde se pega y que se guarda fuera del proyecto.

- [ ] **Paso 3: `docs/DESARROLLO.md`**

Los archivos nuevos y qué hace cada uno; que las pruebas del plugin se corren
con `node uxp-plugin/pruebas/correr.js`; y que el patrón vive en
`docs/patron-de-recorrido/MI-PATRON.md` y es el único dueño de ese texto.

- [ ] **Paso 4: `docs/superpowers/CONTEXTO-Y-METAS.md`**

Anotar que la guía se mudó a Clipify, con el porqué en una línea, y que la
pestaña del plugin quedó de solo lectura.

- [ ] **Paso 5: `CLAUDE.md`**

Agregar a las decisiones de arquitectura ya tomadas, junto a las otras, en el
mismo tono:

> - **La guía de edición se arma en Clipify, no en Premiere.** Los cuartos
>   nacen ahí, así que preguntar del otro lado obligaba a leer el reflejo en
>   vez del original. La guía viaja congelada en el manifest y el panel solo
>   la lee: sin llave, sin red, sin esperas. **Las carpetas de cuartos llegan
>   numeradas** y al importar se reconoce el cuarto **sin su número** — sin
>   eso, una segunda pasada con otro orden parte un cuarto en dos carpetas sin
>   avisar. El número es presentación y lo pone el plugin: no viaja en
>   `categoria_path`, mismo corte que `camara`→color. Ver
>   `specs/2026-09-14-guia-de-edicion-en-clipify-design.md`.

- [ ] **Paso 6: Repasar que nada quedó tirado**

```bash
git status --short
```

Cada archivo nuevo tiene que estar en una carpeta que tenga sentido, y no puede
haber nada suelto en la raíz del repo ni restos del scratchpad.

- [ ] **Paso 7: Commit**

```bash
git add README.md docs/ CLAUDE.md
git commit -m "Documentar la guía de edición armada en Clipify"
```

---

## Lo que hay que enseñarle a Bruno al terminar

Las cuatro capturas de las Tareas 15 y 20, y la salida de las dos suites. **Si
no se miró una imagen, no se afirma que se ve bien.**

Y una cosa que solo él puede comprobar: **armar una guía de verdad con un
proyecto suyo** y ver si el orden que propone se parece a cómo edita. Es la
misma verificación que el §9.1 del spec del patrón le dejaba a él — es el único
que sabe si está bien.
