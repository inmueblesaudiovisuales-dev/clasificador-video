"""Leer un .prproj hacia atrás: archivos de origen usados en sus secuencias.

Sin Qt. Sigue las referencias reales de Premiere desde una secuencia hasta
el Media que contiene la ruta del archivo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video import prproj_xml


@dataclass(frozen=True)
class RangoUsado:
    """Rango de un archivo usado dentro de una secuencia de Premiere."""

    entra_en: int
    sale_en: int
    secuencia: str


@dataclass
class ClipUsado:
    """Un archivo de origen y todos los rangos donde aparece."""

    ruta_origen: Path
    rangos: list[RangoUsado] = field(default_factory=list)


def clips_usados_en(ruta_prproj: Path) -> list[ClipUsado]:
    """Lee los clips de video usados en todas las secuencias de un proyecto."""
    raiz = prproj_xml.leer_prproj(ruta_prproj)
    por_id, por_uid = _indices(raiz)
    por_ruta: dict[Path, ClipUsado] = {}

    for secuencia in raiz.iter("Sequence"):
        nombre = secuencia.findtext("Name") or secuencia.get("ObjectUID") or "?"
        for track_item in _items_de_video(secuencia, por_id, por_uid):
            clip = _clip_de_track_item(track_item, por_id)
            if clip is None:
                continue
            ruta = _ruta_de_clip(clip, por_id, por_uid)
            if ruta is None:
                continue
            entra_en = clip.findtext("Clip/InPoint")
            sale_en = clip.findtext("Clip/OutPoint")
            if entra_en is None or sale_en is None:
                continue
            usado = por_ruta.setdefault(ruta, ClipUsado(ruta_origen=ruta))
            usado.rangos.append(RangoUsado(
                entra_en=int(entra_en), sale_en=int(sale_en), secuencia=nombre,
            ))

    return list(por_ruta.values())


def _indices(raiz: ET.Element) -> tuple[dict[str, ET.Element], dict[str, ET.Element]]:
    """Índices de los objetos globales del XML de Premiere."""
    elementos = list(raiz)
    return (
        {elemento.get("ObjectID"): elemento for elemento in elementos
         if elemento.get("ObjectID")},
        {elemento.get("ObjectUID"): elemento for elemento in elementos
         if elemento.get("ObjectUID")},
    )


def _items_de_video(secuencia, por_id, por_uid):
    for grupo_ref in secuencia.findall(".//TrackGroup/Second"):
        grupo = por_id.get(grupo_ref.get("ObjectRef"))
        if grupo is None or grupo.tag != "VideoTrackGroup":
            continue
        for track_ref in grupo.findall(".//Tracks/Track"):
            track = por_uid.get(track_ref.get("ObjectURef"))
            if track is None or track.tag != "VideoClipTrack":
                continue
            for item_ref in track.findall(".//ClipItems/TrackItems/TrackItem"):
                item = por_id.get(item_ref.get("ObjectRef"))
                if item is not None and item.tag == "VideoClipTrackItem":
                    yield item


def _clip_de_track_item(track_item, por_id):
    subclip_ref = track_item.find("ClipTrackItem/SubClip")
    subclip = por_id.get(subclip_ref.get("ObjectRef")) if subclip_ref is not None else None
    clip_ref = subclip.find("Clip") if subclip is not None else None
    return por_id.get(clip_ref.get("ObjectRef")) if clip_ref is not None else None


def _ruta_de_clip(clip, por_id, por_uid) -> Path | None:
    fuente_ref = clip.find("Clip/Source")
    fuente = por_id.get(fuente_ref.get("ObjectRef")) if fuente_ref is not None else None
    media_ref = fuente.find("MediaSource/Media") if fuente is not None else None
    media = por_uid.get(media_ref.get("ObjectURef")) if media_ref is not None else None
    ruta = media.findtext("FilePath") if media is not None else None
    return Path(ruta) if ruta else None


def medios_faltantes(usados: list[ClipUsado]) -> list[ClipUsado]:
    """Devuelve los clips cuyo archivo de origen no está conectado ahora."""
    return [usado for usado in usados if not usado.ruta_origen.exists()]
