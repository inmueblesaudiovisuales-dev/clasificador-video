"""Generación de objetos de Premiere a partir de la plantilla. Sin Qt."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from clasificador_video.prproj_plantilla import ArchetipoDeClip
from clasificador_video.prproj_xml import AsignadorDeIds, clonar_por_cierre
from clasificador_video.orientacion_premiere import orientacion_de

TICKS_POR_SEGUNDO = 254016000000


@dataclass(frozen=True)
class ClipClonado:
    clip_project_item_uid: str
    master_clip_uid: str
    media_uid: str


def clonar_clip(raiz: ET.Element, arquetipo: ArchetipoDeClip, asignador: AsignadorDeIds, *, ruta_archivo: Path, nombre_en_premiere: str, label_name: str, label_color: int, datos_probe: dict) -> ClipClonado:
    item = next((i for i in raiz.findall('ClipProjectItem') if (m:=i.find('MasterClip')) is not None and m.get('ObjectURef') == arquetipo.master_clip_uid), None)
    if item is None: raise ValueError(f'No se encontró ClipProjectItem para {arquetipo.master_clip_uid}')
    fronteras = {('ObjectID', arquetipo.video_component_chain_id)} if arquetipo.video_component_chain_id else set()
    mapa = clonar_por_cierre(raiz, 'ObjectUID', item.get('ObjectUID'), asignador, fronteras=fronteras)
    item_clon = mapa[('ObjectUID', item.get('ObjectUID'))]
    master_uid = mapa[('ObjectUID', arquetipo.master_clip_uid)].get('ObjectUID')
    item_clon.find('.//Name').text = nombre_en_premiere
    etiqueta=item_clon.find('.//Column.PropertyText.Label')
    if etiqueta is not None: etiqueta.text=label_name
    medias=[e for e in mapa.values() if e.tag == 'Media']
    for media in medias:
        for campo in ('RelativePath','FilePath','ActualMediaFilePath'):
            if (n:=media.find(campo)) is not None: n.text=str(ruta_archivo)
        if (n:=media.find('Title')) is not None: n.text=ruta_archivo.name
        for tipo in ('VideoStream','AudioStream'):
            if (ref:=media.find(tipo)) is None: continue
            stream=next((e for e in mapa.values() if e.tag==tipo and e.get('ObjectID')==ref.get('ObjectRef')), None)
            if stream is None: continue
            if (n:=stream.find('Duration')) is not None: n.text=str(round(TICKS_POR_SEGUNDO*datos_probe['duration_seconds']))
            if tipo=='VideoStream':
                if (n:=stream.find('FrameRate')) is not None: n.text=str(round(TICKS_POR_SEGUNDO/datos_probe['fps']))
                if (n:=stream.find('FrameRect')) is not None and datos_probe.get('width') and datos_probe.get('height'): n.text=f"0,0,{datos_probe['width']},{datos_probe['height']}"
                if (n:=stream.find('OriginalImageOrientationType')) is not None: n.text=str(orientacion_de(datos_probe.get('rotation',0)))
    # En la plantilla real los streams no cuelgan directamente de Media:
    # están en su cierre por DataStream. Actualizar los clones del cierre
    # evita depender de un anidamiento que el XML no tiene.
    for stream in (e for e in mapa.values() if e.tag in ('VideoStream', 'AudioStream')):
        if (n:=stream.find('Duration')) is not None: n.text=str(round(TICKS_POR_SEGUNDO*datos_probe['duration_seconds']))
        if stream.tag == 'VideoStream':
            if (n:=stream.find('FrameRate')) is not None: n.text=str(round(TICKS_POR_SEGUNDO/datos_probe['fps']))
            if (n:=stream.find('FrameRect')) is not None and datos_probe.get('width') and datos_probe.get('height'): n.text=f"0,0,{datos_probe['width']},{datos_probe['height']}"
            if (n:=stream.find('OriginalImageOrientationType')) is not None: n.text=str(orientacion_de(datos_probe.get('rotation',0)))
    for e in mapa.values():
        if e.tag in ('VideoClip','AudioClip'):
            if (n:=e.find('.//asl.clip.label.name')) is not None: n.text=label_name
            if (n:=e.find('.//asl.clip.label.color')) is not None: n.text=str(label_color)
    return ClipClonado(item_clon.get('ObjectUID'), master_uid, medias[0].get('ObjectUID'))


def clonar_secuencia_con_medidas(
        raiz: ET.Element, arquetipo_secuencia: ET.Element,
        asignador: AsignadorDeIds, *, nombre: str,
        ancho: int | None = None, alto: int | None = None) -> ET.Element:
    """Clona una secuencia y opcionalmente cambia su tamaño de cuadro."""
    tipo_ancla = (
        "ObjectUID" if arquetipo_secuencia.get("ObjectUID") else "ObjectID")
    valor_ancla = arquetipo_secuencia.get(tipo_ancla)
    mapa = clonar_por_cierre(raiz, tipo_ancla, valor_ancla, asignador)
    clon = mapa[(tipo_ancla, valor_ancla)]

    nombre_nodo = clon.find(".//Name")
    if nombre_nodo is not None:
        nombre_nodo.text = nombre

    if ancho is not None and alto is not None:
        from clasificador_video.prproj_plantilla import _video_track_group_de_secuencia

        grupo_original = _video_track_group_de_secuencia(raiz, arquetipo_secuencia)
        if grupo_original is not None:
            tipo_grupo = (
                "ObjectUID" if grupo_original.get("ObjectUID") else "ObjectID")
            grupo_clonado = mapa.get(
                (tipo_grupo, grupo_original.get(tipo_grupo)))
            if grupo_clonado is not None:
                rect = grupo_clonado.find("FrameRect")
                if rect is not None:
                    rect.text = f"0,0,{ancho},{alto}"
    return clon
