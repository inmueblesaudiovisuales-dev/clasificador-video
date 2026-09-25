"""Armar la entrega del portafolio: un .prproj con bins por proyecto.

Reusa `prproj_generador.generar_prproj` -- la misma pieza que ya usa el
Clipify normal para su propia entrega -- apuntando a las rutas de la
carpeta de portafolio (`carpeta_de_portafolio`) en vez del material
original. Spec: docs/superpowers/specs/2026-09-24-modo-portafolio-design.md.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from clasificador_video import camaras, prproj_generador
from clasificador_video.manifest import Clip, Manifest
from clasificador_video.probe import probe_clip

from clasificador_video_portafolio import carpeta_de_portafolio as cp
from clasificador_video_portafolio.portafolio import ClipDelPortafolio

SEPARADOR = " — "


def nombre_de_archivo(proyecto: str, fecha: date | None = None) -> str:
    """El nombre de la entrega lleva la fecha, para que regenerar con más
    clips nunca pise la entrega anterior."""
    dia = fecha or date.today()
    return f"{proyecto}{SEPARADOR}entrega {dia.isoformat()}.prproj"


def _nombre_del_bin(proyecto: str, categoria: str | None) -> str:
    return f"{proyecto}{SEPARADOR}{categoria}" if categoria else proyecto


def agrupar_en_bins(
    clips: list[ClipDelPortafolio], categorias: dict[str, str | None]
) -> dict[str, list[ClipDelPortafolio]]:
    """Un grupo por proyecto de origen, nombrado con su categoría
    («Casa Reforma — Casa»); sin categoría, solo el proyecto."""
    grupos: dict[str, list[ClipDelPortafolio]] = {}
    for clip in clips:
        clave = _nombre_del_bin(clip.proyecto, categorias.get(clip.proyecto))
        grupos.setdefault(clave, []).append(clip)
    return grupos


def generar(
    clips: list[ClipDelPortafolio],
    categorias: dict[str, str | None],
    carpeta_raiz: Path,
    proyecto: str = "Mi Portafolio",
    fecha: date | None = None,
    *,
    probe=None,
    generador_proxy=None,
) -> Path:
    """Genera el .prproj de la entrega y devuelve su ruta.

    El `.prproj` apunta a la carpeta de portafolio: cada clip a la ruta
    donde vivirá su alias (`carpeta_de_portafolio.ruta_del_alias`) y a su
    proxy (`asegurar_proxy`, que reusa uno ya existente antes de generar).
    `probe` y `generador_proxy` se inyectan en las pruebas.

    Nota: hasta que la Fase 4.5 (macOS) cree el alias real, el archivo en
    la ruta del alias todavía no existe. Por eso el `probe` que recibe
    `generar_prproj` cae al archivo ORIGINAL cuando la ruta del alias no
    tiene contenido: el proyecto igual se genera, con los metadatos
    correctos, apuntando a donde el alias va a quedar.
    """
    generador_proxy = generador_proxy or cp.asegurar_proxy
    original_de: dict[Path, Path] = {}
    clips_manifest: list[Clip] = []
    orden = 0
    for clave, clips_del_grupo in agrupar_en_bins(clips, categorias).items():
        for clip in clips_del_grupo:
            ruta_alias = cp.ruta_del_alias(carpeta_raiz, clip.proyecto, clip.ruta_origen)
            original_de[ruta_alias] = clip.ruta_origen
            clips_manifest.append(Clip(
                orden=orden,
                ruta=ruta_alias,
                categoria_path=[clave],
                fps=0.0,
                camara=camaras.camara_de_archivo(clip.ruta_origen),
                ruta_proxy=generador_proxy(
                    carpeta_raiz, clip.proyecto, clip.ruta_origen),
            ))
            orden += 1

    manifest = Manifest(
        proyecto=proyecto, orientacion="horizontal", clips=clips_manifest, guia=None,
    )
    destino = carpeta_raiz / nombre_de_archivo(proyecto, fecha)
    sonda = probe or probe_clip

    def probe_con_respaldo(ruta):
        return sonda(original_de.get(Path(ruta), Path(ruta)))

    prproj_generador.generar_prproj(
        manifest, destino, carpeta_raiz / "LUTs", probe=probe_con_respaldo)
    return destino
