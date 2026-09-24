"""Empaqueta un arquetipo de secuencia dentro de la plantilla de Clipify.

Operación de una sola vez, documentada aquí para que se pueda repetir: toma
un proyecto de Premiere que ya tenga una secuencia VACÍA
(creada por Premiere, no inventada), extrae su cierre completo de referencias
--``ClipProjectItem`` -> ``MasterClip`` -> ``VideoClip``/``AudioClip`` ->
``AudioSequenceSource``/``VideoSequenceSource`` -> ``Sequence``-- y lo agrega
a ``recursos/premiere/TemplateColorLuts.prproj`` con IDs nuevos.

Por qué hace falta: la plantilla trae las secuencias de referencia sueltas,
sin el ``ClipProjectItem`` que Premiere dibuja dentro del bin. Clonar solo el
``Sequence`` no alcanza; ver el handoff del 2026-09-24 y la sección de
correcciones de ``progress.md``.

Uso:

    .venv/bin/python scripts/empacar_arquetipo_de_secuencia.py \
        "<proyecto de Premiere>.prproj" \
        "recursos/premiere/TemplateColorLuts.prproj"

El segundo archivo se reescribe en su lugar. No toca los clips de referencia
ni el bin de la plantilla; solo agrega objetos nuevos.
"""
from __future__ import annotations

import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clasificador_video import prproj_plantilla, prproj_xml  # noqa: E402

_PAReS = (("ObjectID", "ObjectRef"), ("ObjectUID", "ObjectURef"))


def _indice(raiz: ET.Element) -> dict:
    indice: dict = {}
    for elemento in raiz:
        for ancla in ("ObjectID", "ObjectUID"):
            valor = elemento.get(ancla)
            if valor:
                indice.setdefault((ancla, valor), elemento)
    return indice


def _tracks_de(indice: dict, secuencia: ET.Element) -> list[ET.Element]:
    tracks = []
    for ref in secuencia.findall(".//TrackGroup/Second"):
        grupo = indice.get(("ObjectID", ref.get("ObjectRef")))
        if grupo is None:
            continue
        for track_ref in grupo.findall(".//Track"):
            track = indice.get(("ObjectUID", track_ref.get("ObjectURef")))
            if track is not None:
                tracks.append(track)
    return tracks


def _item_de_secuencia_vacia(indice: dict, raiz: ET.Element) -> ET.Element | None:
    for item in raiz.findall("ClipProjectItem"):
        master_ref = item.find("MasterClip")
        master = indice.get(("ObjectUID", master_ref.get("ObjectURef"))) if master_ref is not None else None
        if master is None:
            continue
        for clip_ref in master.findall("Clips/Clip"):
            clip = indice.get(("ObjectID", clip_ref.get("ObjectRef")))
            if clip is None:
                continue
            for source_ref in clip.findall("Clip/Source"):
                source = indice.get(("ObjectID", source_ref.get("ObjectRef")))
                if source is None or source.tag != "VideoSequenceSource":
                    continue
                secuencia_ref = source.find("SequenceSource/Sequence")
                secuencia = indice.get(("ObjectUID", secuencia_ref.get("ObjectURef")))
                if secuencia is None:
                    continue
                if all(not t.findall(".//TrackItem") for t in _tracks_de(indice, secuencia)):
                    return item
    return None


def _cierre(indice: dict, inicio: tuple) -> list[tuple]:
    vistos: set = set()
    orden: list = []
    pila = [inicio]
    while pila:
        clave = pila.pop()
        if clave in vistos:
            continue
        elemento = indice.get(clave)
        if elemento is None:
            continue
        vistos.add(clave)
        orden.append((clave, elemento))
        for hijo in elemento.iter():
            for ancla, ref in _PAReS:
                valor = hijo.get(ref)
                if valor:
                    pila.append((ancla, valor))
    return orden


def empacar(referencia: Path, plantilla: Path) -> None:
    origen = prproj_xml.leer_prproj(referencia)
    destino = prproj_xml.leer_prproj(plantilla)
    indice = _indice(origen)

    try:
        prproj_plantilla.archetipo_de_secuencia(destino)
    except prproj_plantilla.PlantillaIncompleta:
        pass
    else:
        print("La plantilla ya tiene un arquetipo de secuencia vacío; no se toca.")
        return

    item = _item_de_secuencia_vacia(indice, origen)
    if item is None:
        raise SystemExit("El proyecto de referencia no tiene una secuencia vacía con ClipProjectItem.")

    cierre = _cierre(indice, ("ObjectUID", item.get("ObjectUID")))

    asignador = prproj_xml.AsignadorDeIds(destino)
    nuevos = {}
    for clave, elemento in cierre:
        ancla, _ = clave
        nuevos[clave] = (ancla, asignador.nuevo_object_id() if ancla == "ObjectID" else asignador.nuevo_object_uid())

    for clave, elemento in cierre:
        clon = ET.fromstring(ET.tostring(elemento))
        ancla, nuevo = nuevos[clave]
        clon.set(ancla, nuevo)
        for hijo in clon.iter():
            for anc, ref in _PAReS:
                valor = hijo.get(ref)
                if valor is not None and (anc, valor) in nuevos:
                    hijo.set(ref, nuevos[(anc, valor)][1])
        destino.append(clon)

    prproj_xml.escribir_prproj(destino, plantilla)
    print(f"Arquetipo empacado desde {referencia.name}: {len(cierre)} objetos.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    empacar(Path(sys.argv[1]), Path(sys.argv[2]))
