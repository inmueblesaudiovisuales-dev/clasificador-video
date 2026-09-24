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


@dataclass(frozen=True)
class ArchetipoDeSecuencia:
    """El ``ClipProjectItem`` de una secuencia y la ``Sequence`` que alcanza."""
    clip_project_item_uid: str
    sequence_uid: str
    ancho: int
    alto: int


def _indice_por_uid(raiz: ET.Element) -> dict:
    return {e.get("ObjectUID"): e for e in raiz if e.get("ObjectUID")}


def _fuentes_del_master(raiz: ET.Element, master: ET.Element):
    """Las fuentes directas (``Clip/Source``) de cada clip del ``MasterClip``.

    A propósito NO baja a un ``SubClip``: un clip de medios puede llevar un
    subclip y seguir siendo un clip, mientras que un item de secuencia tiene
    la ``VideoSequenceSource`` como fuente directa.
    """
    indice = {e.get("ObjectID"): e for e in raiz if e.get("ObjectID")}
    for clip_ref in master.findall("Clips/Clip"):
        clip = indice.get(clip_ref.get("ObjectRef"))
        if clip is None:
            continue
        fuente_ref = clip.find("Clip/Source")
        fuente = indice.get(fuente_ref.get("ObjectRef")) if fuente_ref is not None else None
        if fuente is not None:
            yield fuente


def _es_master_de_clip(raiz: ET.Element, master: ET.Element) -> bool:
    return any(f.tag in ("VideoMediaSource", "AudioMediaSource")
               for f in _fuentes_del_master(raiz, master))


def _secuencia_del_master(raiz: ET.Element, master: ET.Element) -> str | None:
    for fuente in _fuentes_del_master(raiz, master):
        if fuente.tag != "VideoSequenceSource":
            continue
        ref = fuente.find("SequenceSource/Sequence")
        if ref is not None:
            return ref.get("ObjectURef")
    return None


def archetipos_de_clip(raiz: ET.Element) -> dict[str, ArchetipoDeClip]:
    encontrados = {}
    for master in raiz.findall("MasterClip"):
        uid = master.get("ObjectUID")
        if not uid or not _es_master_de_clip(raiz, master):
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


def _tracks_de_secuencia(
        raiz: ET.Element, secuencia: ET.Element) -> list[ET.Element]:
    tracks = []
    for ref in secuencia.findall(".//TrackGroup/Second"):
        grupo = next((e for e in raiz if e.get("ObjectID") == ref.get("ObjectRef")), None)
        if grupo is None:
            continue
        for track_ref in grupo.findall(".//Track"):
            track = next((e for e in raiz if e.get("ObjectUID") == track_ref.get("ObjectURef")), None)
            if track is not None:
                tracks.append(track)
    return tracks


def _secuencia_esta_vacia(raiz: ET.Element, secuencia: ET.Element) -> bool:
    return all(not track.findall(".//TrackItem")
               for track in _tracks_de_secuencia(raiz, secuencia))


def archetipo_de_secuencia(raiz: ET.Element) -> ArchetipoDeSecuencia:
    """El ``ClipProjectItem`` que Premiere dibuja dentro de un bin para una
    secuencia, con su cierre completo.

    No alcanza con clonar la ``Sequence``: el item visible es un
    ``ClipProjectItem`` que cuelga de ``MasterClip`` y llega a la secuencia
    por ``VideoSequenceSource``/``AudioSequenceSource``. Se prefiere un item
    cuya secuencia esté VACÍA: los items de secuencia de la plantilla de
    LUTs traen un clip de referencia dentro. El arquetipo limpio se empaca
    con ``scripts/empacar_arquetipo_de_secuencia.py``.
    """
    indice = _indice_por_uid(raiz)
    candidatos = []
    for item in raiz.findall("ClipProjectItem"):
        master_ref = item.find("MasterClip")
        master = indice.get(master_ref.get("ObjectURef")) if master_ref is not None else None
        if master is None:
            continue
        secuencia_uid = _secuencia_del_master(raiz, master)
        if secuencia_uid is None:
            continue
        secuencia = indice.get(secuencia_uid)
        medidas = _ancho_alto_de_secuencia(raiz, secuencia) if secuencia is not None else None
        if medidas is None:
            continue
        ancho, alto = medidas
        candidatos.append(ArchetipoDeSecuencia(
            item.get("ObjectUID"), secuencia_uid, ancho, alto))
    vacios = [c for c in candidatos if _secuencia_esta_vacia(
        raiz, indice[c.sequence_uid])]
    if not vacios:
        raise PlantillaIncompleta(
            "La plantilla no tiene un ClipProjectItem de secuencia con la "
            "secuencia vacía. Revisar scripts/empacar_arquetipo_de_secuencia.py.")
    return vacios[0]
