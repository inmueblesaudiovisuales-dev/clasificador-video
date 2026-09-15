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
