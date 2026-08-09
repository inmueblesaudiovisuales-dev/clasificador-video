# src/clasificador_video/filters.py
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

# Los estados que cuentan como "ya lo juzgaste". `destacado` esta aqui por
# derecho propio: es LA toma del cuarto. Vive en una constante y no repetido
# en cada comparacion, que es como `sin_marcar` se quedo sin el al agregarlo.
MARCADOS = ("pick", "reject", "destacado")


def _sin_acentos(texto: str) -> str:
    """`recamara` tiene que encontrar `Recámara 1`: en un teclado apurado
    nadie escribe los acentos."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if not unicodedata.combining(c)
    )


@dataclass
class FilterState:
    """Que se ve y, sobre todo, POR DONDE se mueven las flechas.

    Los filtros de esta app no cambian solo lo que ves: cambian la cola de
    navegacion (ver DECISIONES.md). De aca sale una sola lista de indices que
    alimenta la hoja, las flechas y el contador del visor -- calculadas por
    separado se desincronizan.
    """

    # Los valores validos de `mostrar` son "todos", "sin_clasificar" y
    # "clasificados"; los de `estado`, "todos", "solo_picks",
    # "solo_destacados", "ocultar_rejects" y "sin_marcar". Cualquier otro no filtra nada, a
    # proposito: esconder clips por un nombre que el modulo no conoce seria
    # peor que no filtrar. `solo_destacados` se agrego en la F7.
    mostrar: str = "todos"
    estado: str = "todos"
    busqueda: str = ""

    def esta_filtrando(self) -> bool:
        """De esto depende que el visor diga `87 / 128` o `3 de 12 en la
        cola`: sin filtro, la posicion en el shooting entero SI sirve."""
        return (
            self.mostrar != "todos"
            or self.estado != "todos"
            or bool(self.busqueda.strip())
        )

    def pasa(self, clip) -> bool:
        clasificado = bool(clip.categoria_path)
        if self.mostrar == "sin_clasificar" and clasificado:
            return False
        if self.mostrar == "clasificados" and not clasificado:
            return False
        if self.estado == "solo_picks" and clip.flag != "pick":
            return False
        if self.estado == "solo_destacados" and clip.flag != "destacado":
            return False
        if self.estado == "ocultar_rejects" and clip.flag == "reject":
            return False
        # `destacado` entra aqui: es el clip MAS juzgado del cuarto, y sin
        # nombrarlo se colaba en "lo que falta juzgar"
        if self.estado == "sin_marcar" and clip.flag in MARCADOS:
            return False
        texto = self.busqueda.strip()
        if texto:
            aguja = _sin_acentos(texto)
            pajar = _sin_acentos(
                Path(clip.ruta).name + " " + " ".join(clip.categoria_path)
            )
            if aguja not in pajar:
                return False
        return True


def cola(clips: list, estado: FilterState) -> list[int]:
    """Los indices que pasan el filtro, **en el orden de los clips**.

    No se reordena nunca: es el orden de rodaje, y de el vive la nocion de
    "el clip anterior".
    """
    return [i for i, clip in enumerate(clips) if estado.pasa(clip)]


def contar(clips: list) -> dict[str, int]:
    """Los numeros que van en los chips."""
    clasificados = sum(1 for c in clips if c.categoria_path)
    rejects = sum(1 for c in clips if c.flag == "reject")
    return {
        "todos": len(clips),
        "sin_clasificar": len(clips) - clasificados,
        "clasificados": clasificados,
        "solo_picks": sum(1 for c in clips if c.flag == "pick"),
        "solo_destacados": sum(1 for c in clips if c.flag == "destacado"),
        # cuantos SE OCULTAN, no cuantos quedan: el chip del mockup dice "−9"
        "ocultar_rejects": rejects,
        "sin_marcar": sum(1 for c in clips if c.flag not in MARCADOS),
    }
