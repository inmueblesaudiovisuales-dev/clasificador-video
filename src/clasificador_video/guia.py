"""Lógica pura de la guía: clasifica cuartos para el tablero."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


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


@dataclass
class Clasificacion:
    ok: bool
    columna_de: dict[str, str] = field(default_factory=dict)
    # Cuartos que aparecieron y NO son de los reales -- se marcan en vez de
    # descartarse en silencio (regla del CLAUDE.md: "si sobra alguno, el
    # panel lo marca en vez de enseñar la lista como si nada"). El
    # clasificador por palabras nunca inventa, así que siempre va vacío;
    # el campo se queda porque `mostrar_clasificacion` lo revisa.
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


def cuartos_sin_usar(reales: list[str], pasos: list[str]) -> list[str]:
    usados = set(pasos or [])
    return [c for c in (reales or []) if c not in usados]


# Los términos que reconocen cada columna, ya normalizados (minúsculas y sin
# acentos). Se buscan como SUBSTRING del nombre, así que `recamara` cae en
# habitaciones aunque Bruno lo escriba sin acento. El desempate es por
# longitud: ver `clasificar_por_palabras`.
TERMINOS_DE_COLUMNA = {
    "apertura": ("fachada", "entrada", "acceso", "porton", "puerta",
                 "recibidor", "frontal", "aerea", "aereo", "dron", "drone"),
    "sociales": ("cocina", "sala", "comedor", "terraza", "desayunador",
                 "bar", "estancia", "family"),
    "habitaciones": ("recamara", "cuarto", "habitacion", "dormitorio",
                     "alcoba", "bano", "vestidor", "closet", "walk in",
                     "principal"),
    "aerea_media": ("aerea media", "media casa", "intermedia",
                    "aerea intermedia"),
    "amenidades": ("alberca", "piscina", "roof", "amenidad", "amenidades",
                   "gym", "gimnasio", "asador", "juegos", "cancha"),
    "area_general": ("propiedad", "general", "terreno", "lote", "de lejos",
                     "casa completa", "aerea de la propiedad"),
    "aerea_final": ("aerea final", "final", "cierre", "salida", "ultima toma",
                    "ultima", "placa"),
}


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, SOLO para buscar el término.

    Es la normalización de una COPIA: el nombre que devuelve
    `clasificar_por_palabras` es el original, tal cual lo tecleó Bruno.

    Esto es reconocimiento (¿el nombre trae la palabra «cocina»?), no
    comparación por igualdad exacta. Por eso aquí sí se quitan acentos,
    distinto de la revisión que compara la lista contra los bins: allá
    normalizar escondería el caso que la revisión existe para atrapar
    (`Recamara 1` contra `Recámara 1` son dos cuartos distintos); aquí, al
    revés, es justo lo que deja caer `recamara` en Habitaciones.
    """
    descompuesto = unicodedata.normalize("NFKD", str(texto or ""))
    sin_acentos = "".join(
        c for c in descompuesto if not unicodedata.combining(c))
    return sin_acentos.lower()


def clasificar_por_palabras(cuartos: list[str]) -> Clasificacion:
    """Ubica cada cuarto en su columna reconociendo términos clave.

    No usa IA, ni llave, ni red: es instantáneo y determinista. No puede
    fallar y no inventa cuartos.

    Desempate, en orden:
    1. se juntan TODOS los términos que aparecen en el nombre, con su
       columna;
    2. gana el término más largo (el más específico);
    3. si el término más largo aparece en dos columnas distintas, el cuarto
       se deja FUERA -- no se adivina, Bruno lo arrastra;
    4. si no aparece ningún término, el cuarto también se deja fuera.
    """
    columna_de: dict[str, str] = {}
    for cuarto in cuartos or []:
        normalizado = _normalizar(cuarto)
        apariciones = [
            (len(termino), columna)
            for columna, terminos in TERMINOS_DE_COLUMNA.items()
            for termino in terminos
            if termino in normalizado
        ]
        if not apariciones:
            continue
        largo_mayor = max(largo for largo, _ in apariciones)
        ganadoras = {columna for largo, columna in apariciones
                     if largo == largo_mayor}
        if len(ganadoras) == 1:
            columna_de[cuarto] = ganadoras.pop()
    return Clasificacion(True, columna_de, [])
