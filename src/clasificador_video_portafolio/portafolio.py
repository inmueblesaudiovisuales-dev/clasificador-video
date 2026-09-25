"""El portafolio único que crece para siempre.

Sin Qt: guarda proyectos importados, sus clips y el estado de cada uno.
Las pantallas de Importar, Revisar y Armar/entregar son capas encima de
este modelo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from clasificador_video_portafolio.lector_de_entregas import ClipUsado, RangoUsado


ESTADOS = ("descartada", "sin_decidir", "elegida")
CATEGORIAS_POR_DEFECTO = ["Casa", "Depto", "Terreno", "Oficina"]


@dataclass
class ClipDelPortafolio:
    ruta_origen: Path
    proyecto: str
    rangos: list[RangoUsado] = field(default_factory=list)
    estado: str = "sin_decidir"
    etiquetas: list[str] = field(default_factory=list)
    fuera_de_secuencia: bool = False


def subir(clip: ClipDelPortafolio) -> None:
    """`↑` -- un peldaño hacia Elegida."""
    indice = min(ESTADOS.index(clip.estado) + 1, len(ESTADOS) - 1)
    clip.estado = ESTADOS[indice]


def bajar(clip: ClipDelPortafolio) -> None:
    """`↓` -- un peldaño hacia Descartada."""
    indice = max(ESTADOS.index(clip.estado) - 1, 0)
    clip.estado = ESTADOS[indice]


def alternar_etiqueta(clip: ClipDelPortafolio, etiqueta: str) -> None:
    """La tecla de una etiqueta la SUMA o la QUITA, nunca la reemplaza.

    A diferencia de los cuartos, donde el número reemplaza, un clip del
    portafolio puede tener varias etiquetas a la vez (spec 2026-09-24).
    """
    if etiqueta in clip.etiquetas:
        clip.etiquetas.remove(etiqueta)
    else:
        clip.etiquetas.append(etiqueta)


@dataclass
class ProyectoImportado:
    nombre: str
    ruta_prproj: Path
    categoria: str | None = None
    clips: list[ClipDelPortafolio] = field(default_factory=list)


class Portafolio:
    def __init__(self) -> None:
        self.proyectos: list[ProyectoImportado] = []
        self.categorias_conocidas: list[str] = list(CATEGORIAS_POR_DEFECTO)

    def asignar_categoria(
        self, proyecto: ProyectoImportado, categoria: str
    ) -> None:
        proyecto.categoria = categoria
        if categoria not in self.categorias_conocidas:
            self.categorias_conocidas.append(categoria)

    def agregar_proyecto(
        self, nombre: str, ruta_prproj: Path, clips_usados: list[ClipUsado]
    ) -> ProyectoImportado:
        existente = self._proyecto_por_ruta(ruta_prproj)
        clips = [
            ClipDelPortafolio(u.ruta_origen, nombre, list(u.rangos))
            for u in clips_usados
        ]
        if existente is not None:
            self._fusionar_clips(existente, clips)
            return existente
        proyecto = ProyectoImportado(nombre, ruta_prproj, clips=clips)
        self.proyectos.append(proyecto)
        return proyecto

    def _proyecto_por_ruta(self, ruta_prproj: Path) -> ProyectoImportado | None:
        return next((p for p in self.proyectos if p.ruta_prproj == ruta_prproj), None)

    @staticmethod
    def _fusionar_clips(
        proyecto: ProyectoImportado, nuevos: list[ClipDelPortafolio]
    ) -> None:
        clips_por_ruta = {clip.ruta_origen: clip for clip in proyecto.clips}
        for nuevo in nuevos:
            existente = clips_por_ruta.get(nuevo.ruta_origen)
            if existente is None:
                proyecto.clips.append(nuevo)
                continue
            # La entrega pudo cambiar su edición; se actualizan sus rangos
            # sin borrar la decisión ni las etiquetas ya hechas en Portafolio.
            existente.rangos = nuevo.rangos

    @staticmethod
    def medios_faltantes_de(proyecto: ProyectoImportado) -> list[ClipDelPortafolio]:
        return [clip for clip in proyecto.clips if not clip.ruta_origen.exists()]

    @staticmethod
    def revincular(clip: ClipDelPortafolio, carpeta_nueva: Path) -> bool:
        """Actualiza una ruta solo si la carpeta indicada contiene ese archivo."""
        candidata = carpeta_nueva / clip.ruta_origen.name
        if not candidata.exists():
            return False
        clip.ruta_origen = candidata
        return True

    def todas_las_elegidas(self) -> list[ClipDelPortafolio]:
        return [
            clip
            for proyecto in self.proyectos
            for clip in proyecto.clips
            if clip.estado == "elegida"
        ]

    def elegidas_con_etiquetas(
        self, etiquetas: set[str]
    ) -> list[ClipDelPortafolio]:
        """Elegidas que tienen AL MENOS una de las etiquetas pedidas.

        Con `etiquetas` vacío no filtra nada extra: son todas las elegidas.
        """
        if not etiquetas:
            return self.todas_las_elegidas()
        return [
            clip
            for clip in self.todas_las_elegidas()
            if etiquetas & set(clip.etiquetas)
        ]

    def guardar(self, destino: Path) -> None:
        datos = {
            "categorias_conocidas": self.categorias_conocidas,
            "proyectos": [
                {
                    "nombre": proyecto.nombre,
                    "ruta_prproj": str(proyecto.ruta_prproj),
                    "categoria": proyecto.categoria,
                    "clips": [
                        {
                            "ruta_origen": str(clip.ruta_origen),
                            "proyecto": clip.proyecto,
                            "rangos": [
                                {
                                    "entra_en": rango.entra_en,
                                    "sale_en": rango.sale_en,
                                    "secuencia": rango.secuencia,
                                }
                                for rango in clip.rangos
                            ],
                            "estado": clip.estado,
                            "etiquetas": clip.etiquetas,
                            "fuera_de_secuencia": clip.fuera_de_secuencia,
                        }
                        for clip in proyecto.clips
                    ],
                }
                for proyecto in self.proyectos
            ]
        }
        destino.write_text(json.dumps(datos, indent=2), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta: Path) -> "Portafolio":
        portafolio = cls()
        if not ruta.exists():
            return portafolio
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        portafolio.categorias_conocidas = datos.get(
            "categorias_conocidas", list(CATEGORIAS_POR_DEFECTO)
        )
        for datos_proyecto in datos.get("proyectos", []):
            proyecto = ProyectoImportado(
                nombre=datos_proyecto["nombre"],
                ruta_prproj=Path(datos_proyecto["ruta_prproj"]),
                categoria=datos_proyecto.get("categoria"),
            )
            for datos_clip in datos_proyecto.get("clips", []):
                proyecto.clips.append(
                    ClipDelPortafolio(
                        ruta_origen=Path(datos_clip["ruta_origen"]),
                        proyecto=datos_clip["proyecto"],
                        rangos=[RangoUsado(**rango) for rango in datos_clip.get("rangos", [])],
                        estado=datos_clip.get("estado", "sin_decidir"),
                        etiquetas=datos_clip.get("etiquetas", []),
                        fuera_de_secuencia=datos_clip.get("fuera_de_secuencia", False),
                    )
                )
            portafolio.proyectos.append(proyecto)
        return portafolio
