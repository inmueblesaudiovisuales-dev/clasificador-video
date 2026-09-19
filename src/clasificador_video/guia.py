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

import json
from dataclasses import dataclass, field

MODELO = "deepseek-chat"
# El de conversación, no el de razonamiento. Esto no es una cadena de
# razonamiento: es acomodar diez nombres con criterio de recorrido, y el de
# razonamiento cuesta y tarda más para la misma respuesta.


@dataclass(frozen=True)
class Columna:
    id: str
    titulo: str
    pista: str


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


def prompt_de_clasificacion(cuartos: list[str]) -> str:
    partes = [
        "Eres el asistente de un editor de video mexicano.",
        "Tu único trabajo es clasificar cada cuarto en una columna:", "",
    ]
    partes.extend(f'- "{c.id}" ({c.titulo}): {c.pista}' for c in COLUMNAS)
    partes += ["", "Los cuartos son EXACTAMENTE estos:",
               "\n".join("- " + c for c in cuartos), "",
               "Contesta SOLO con JSON:",
               '{"clasificacion": [{"cuarto": "<nombre tal cual>", "columna": "<id>"}]}']
    return "\n".join(partes)


def cuerpo_de_clasificacion(cuartos: list[str]) -> dict:
    return {"model": MODELO, "messages": [
        {"role": "system", "content": prompt_de_clasificacion(cuartos or [])},
        {"role": "user", "content": "Clasifica estos cuartos."},
    ]}


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


@dataclass
class Revision:
    faltan: list[str] = field(default_factory=list)
    inventados: list[str] = field(default_factory=list)

    def limpia(self) -> bool:
        return not (self.faltan or self.inventados)


def prompt_de_sistema(cuartos: list[str], patron: str) -> str:
    """Lo que se le dice al modelo.

    EL MATIZ QUE NO SE PUEDE PERDER: el modelo sabe por qué la cocina va
    antes que la sala --eso es criterio de recorrido-- pero NO sabe qué hay
    en la cocina de Bruno, porque no vio el video y nunca lo va a ver. Un
    modelo describiendo una cocina que no vio («la cocina integral con
    cubierta de granito») es exactamente el modo de falla que este repo
    lleva un mes evitando: adivinar en silencio y sonar seguro.

    LO QUE SE PIDE SON PASOS, NO CUARTOS: un recorrido real repite --Bruno
    abre y cierra con la misma aérea-- y una lista de cuartos no puede
    decir eso dos veces. Por eso la respuesta es un guion de pasos donde un
    cuarto puede aparecer varias veces, cada una con su propia razón.
    """
    partes = [
        "Eres el asistente de un editor de video mexicano que hace recorridos de",
        "propiedades en venta o renta. Tu trabajo es armar, PASO A PASO, el",
        "recorrido que debe llevar el espectador por la propiedad.",
        "",
        "NO viste el material. No sabes qué hay adentro de ningún cuarto, cómo se ve",
        "ni con qué se grabó. Por eso:",
        "- La línea de cada paso dice POR QUÉ VA AHÍ en el recorrido, no qué hay",
        "  adentro. «Se entra por aquí» sirve; «la cocina integral con cubierta de",
        "  granito» es inventado y no se vale.",
        "- Solo hablas de esta propiedad en concreto si el editor te lo contó él",
        "  mismo.",
        "- Si no tienes una razón de recorrido que dar, da la genérica. No rellenes",
        "  con detalles.",
        "",
        "Lo que devuelves es un GUION: los PASOS del video en orden, no una lista",
        "de cuartos. Un mismo cuarto puede salir las veces que haga falta -- este",
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
        "Cada objeto de \"orden\" es UN PASO del video, en orden. Sin texto antes ni",
        "después. Escribe en español de México, de tú, y corto.",
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

    QUE UN CUARTO SE REPITA NO ES UN ERROR. En los quince entregables de
    2026 siempre se repite alguno, y en catorce el cuarto con el que abre
    vuelve a salir. Aquí se marcó como problema hasta el 2026-09-15, y era
    la app diciéndole a Bruno que su forma de editar estaba mal.

    Lo que sí sigue siendo error: que FALTE un cuarto --uno que no sale ni
    una vez es material que se te olvida al editar-- y que el modelo se
    saque uno de la manga.
    """
    propuestos = [r.cuarto for r in (lista or [])]
    reales = list(cuartos_reales or [])

    faltan = [c for c in reales if c not in propuestos]
    inventados = [
        c for i, c in enumerate(propuestos)
        if c not in reales and propuestos.index(c) == i
    ]
    return Revision(faltan=faltan, inventados=inventados)


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
    return avisos
