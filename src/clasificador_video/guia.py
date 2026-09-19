"""Lógica pura de la guía: clasifica cuartos para el tablero."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

MODELO = "deepseek-chat"


@dataclass(frozen=True)
class Columna:
    id: str
    titulo: str
    pista: str


COLUMNAS = (
    Columna("apertura", "Apertura / fachada", "la fachada o la aérea de entrada"),
    Columna("sociales", "Áreas sociales", "cocina, sala, comedor, terraza"),
    Columna("habitaciones", "Habitaciones", "recámaras, baños, vestidor"),
    Columna("aerea_media", "Aérea a media casa", "una aérea para respirar antes de salir"),
    Columna("amenidades", "Amenidades", "alberca, roof, amenidades en general"),
    Columna("area_general", "Área general", "la propiedad completa, de lejos"),
    Columna("aerea_final", "Aérea final", "la última toma, de salida"),
)
IDS_DE_COLUMNA = frozenset(c.id for c in COLUMNAS)


@dataclass
class Clasificacion:
    ok: bool
    columna_de: dict[str, str] = field(default_factory=dict)
    # Cuartos que el modelo mencionó y NO son de los reales -- se marcan en
    # vez de descartarse en silencio (spec del CLAUDE.md: "si sobra alguno,
    # el panel lo marca en vez de enseñar la lista como si nada").
    inventados: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class Renglon:
    cuarto: str


@dataclass
class Respuesta:
    ok: bool
    lista: list[Renglon] = field(default_factory=list)
    error: str = ""


def prompt_de_clasificacion(cuartos: list[str]) -> str:
    partes = ["Eres el asistente de un editor de video mexicano.",
              "Tu único trabajo es clasificar cada cuarto en una columna:", ""]
    partes.extend(f'- "{c.id}" ({c.titulo}): {c.pista}' for c in COLUMNAS)
    partes += ["", "Los cuartos son EXACTAMENTE estos:",
               "\n".join("- " + c for c in cuartos), "", "Contesta SOLO con JSON:",
               '{"clasificacion": [{"cuarto": "<nombre tal cual>", "columna": "<id>"}]}']
    return "\n".join(partes)


def cuerpo_de_clasificacion(cuartos: list[str]) -> dict:
    return {"model": MODELO, "messages": [
        {"role": "system", "content": prompt_de_clasificacion(cuartos or [])},
        {"role": "user", "content": "Clasifica estos cuartos."},
    ]}


def _recortar_json(texto: str) -> str:
    inicio = texto.find("{")
    if inicio == -1:
        return ""
    nivel = 0; en_cadena = False; escapado = False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if en_cadena:
            if escapado: escapado = False
            elif c == "\\": escapado = True
            elif c == '"': en_cadena = False
            continue
        if c == '"': en_cadena = True
        elif c == "{": nivel += 1
        elif c == "}":
            nivel -= 1
            if nivel == 0: return texto[inicio:i + 1]
    return ""


def leer_clasificacion(texto: str | None, cuartos_reales: list[str]) -> Clasificacion:
    crudo = ("" if texto is None else str(texto)).strip()
    if not crudo: return Clasificacion(False, error="El modelo no contestó nada.")
    recorte = _recortar_json(crudo)
    if not recorte: return Clasificacion(False, error="El modelo contestó con texto.")
    try: datos = json.loads(recorte)
    except (json.JSONDecodeError, ValueError):
        return Clasificacion(False, error="La respuesta no se pudo leer.")
    if not isinstance(datos, dict) or not isinstance(datos.get("clasificacion"), list):
        return Clasificacion(False, error="La respuesta llegó con otra forma.")
    reales = set(cuartos_reales or []); columna_de = {}; inventados = []
    for renglon in datos["clasificacion"]:
        if not isinstance(renglon, dict): continue
        cuarto, columna = renglon.get("cuarto"), renglon.get("columna")
        if columna not in IDS_DE_COLUMNA:
            continue
        if cuarto not in reales:
            # el modelo se sacó un cuarto de la manga: no se inventa, se
            # marca -- igualdad exacta de cadena, sin normalizar nada.
            if isinstance(cuarto, str) and cuarto not in inventados:
                inventados.append(cuarto)
            continue
        columna_de.setdefault(cuarto, columna)
    return Clasificacion(True, columna_de, inventados)


def cuartos_sin_usar(reales: list[str], pasos: list[str]) -> list[str]:
    usados = set(pasos or [])
    return [c for c in (reales or []) if c not in usados]
