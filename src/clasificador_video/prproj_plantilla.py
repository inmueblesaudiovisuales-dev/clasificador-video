"""Localización estricta de los arquetipos de la plantilla Premiere."""
from __future__ import annotations

import base64
from dataclasses import dataclass
import xml.etree.ElementTree as ET


class PlantillaIncompleta(Exception):
    pass


@dataclass(frozen=True)
class ArchetipoDeClip:
    master_clip_uid: str
    video_component_chain_id: str | None
    ruta_lut: str | None


def _decodificar(nodo: ET.Element) -> str:
    try:
        return base64.b64decode((nodo.text or "").strip()).decode("utf-16-le", errors="ignore").rstrip("\0")
    except Exception:
        return ""


def _lut_del_video_component_chain(raiz: ET.Element, chain_id: str) -> str | None:
    """Busca en el cierre de refs del efecto, no solo en el wrapper chain."""
    por_id = {e.get("ObjectID"): e for e in raiz if e.get("ObjectID")}
    pendientes, vistos = [chain_id], set()
    while pendientes:
        ident = pendientes.pop()
        if ident in vistos or ident not in por_id:
            continue
        vistos.add(ident)
        nodo = por_id[ident]
        for valor in nodo.iter("StartKeyframeValue"):
            texto = _decodificar(valor)
            if texto.lower().endswith(".cube"):
                return texto
        pendientes.extend(e.get("ObjectRef") for e in nodo.iter() if e.get("ObjectRef"))
    return None


def archetipos_de_clip(raiz: ET.Element) -> dict[str, ArchetipoDeClip]:
    encontrados = {}
    for master in raiz.findall("MasterClip"):
        uid = master.get("ObjectUID")
        if not uid:
            continue
        ref = master.find("VideoComponentChain")
        chain = ref.get("ObjectRef") if ref is not None else None
        lut = _lut_del_video_component_chain(raiz, chain) if chain else None
        if lut and "sony-slog3" in lut.lower():
            encontrados["sony"] = ArchetipoDeClip(uid, chain, lut)
        elif lut and "dji-dlogm" in lut.lower():
            encontrados["dji"] = ArchetipoDeClip(uid, chain, lut)
        elif lut is None and "otra" not in encontrados:
            encontrados["otra"] = ArchetipoDeClip(uid, None, None)
    faltan = {"sony", "dji", "otra"} - encontrados.keys()
    if faltan:
        raise PlantillaIncompleta("La plantilla de LUTs no tiene clip de referencia para: " + ", ".join(sorted(faltan)))
    # Un MasterClip suelto no es un arquetipo importable: debe conservar su
    # ClipProjectItem, que es la entrada visible del bin.
    masters_visibles = {
        ref.get("ObjectURef") for item in raiz.findall("ClipProjectItem")
        for ref in item.findall("MasterClip")
    }
    if any(arquetipo.master_clip_uid not in masters_visibles for arquetipo in encontrados.values()):
        raise PlantillaIncompleta("La plantilla no contiene los ClipProjectItem de referencia completos")
    return encontrados


def archetipo_de_bin(raiz: ET.Element) -> ET.Element | None:
    return next((e for e in raiz if e.tag != "RootProjectItem" and e.find("ProjectItemContainer") is not None), None)


FORMATOS_DE_SECUENCIA = {"4k_9x16": (2160, 3840, 59.94), "2_7k_9x16": (1512, 2688, 59.94), "4k_16x9": (3840, 2160, 59.94), "9x16_1080p": (1080, 1920, 59.94), "16x9_1080p": (1920, 1080, 59.94)}


def _video_track_group_de_secuencia(
        raiz: ET.Element, secuencia: ET.Element) -> ET.Element | None:
    for grupo in secuencia.findall(".//TrackGroup"):
        ref = grupo.find("Second")
        if ref is None:
            continue
        candidato = raiz.find(
            f'.//VideoTrackGroup[@ObjectID="{ref.get("ObjectRef")}"]')
        if candidato is not None:
            return candidato
    return None


def _ancho_alto_de_secuencia(
        raiz: ET.Element, secuencia: ET.Element) -> tuple[int, int] | None:
    grupo = _video_track_group_de_secuencia(raiz, secuencia)
    if grupo is None:
        return None
    rect = grupo.find("FrameRect")
    if rect is None or not rect.text:
        return None
    _x, _y, ancho, alto = rect.text.split(",")
    return int(ancho), int(alto)


_CLAVES_REALES_EN_PLANTILLA = ("4k_9x16", "2_7k_9x16")


def archetipos_de_secuencia(raiz: ET.Element) -> dict[str, ET.Element]:
    """Localiza las dos secuencias reales por su ``VideoTrackGroup``."""
    encontrados: dict[str, ET.Element] = {}
    for secuencia in raiz.findall("Sequence"):
        medidas = _ancho_alto_de_secuencia(raiz, secuencia)
        if medidas is None:
            continue
        for clave in _CLAVES_REALES_EN_PLANTILLA:
            if clave in encontrados:
                continue
            ancho, alto, _fps = FORMATOS_DE_SECUENCIA[clave]
            if medidas == (ancho, alto):
                encontrados[clave] = secuencia
                break

    faltan = set(_CLAVES_REALES_EN_PLANTILLA) - encontrados.keys()
    if faltan:
        raise PlantillaIncompleta(
            "La plantilla no tiene secuencia de referencia para: "
            + ", ".join(sorted(faltan)) + ". Revisar la Tarea 0 del plan.")
    return encontrados
