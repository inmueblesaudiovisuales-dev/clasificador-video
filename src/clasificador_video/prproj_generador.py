"""Generación de objetos de Premiere a partir de la plantilla. Sin Qt."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from clasificador_video import recursos
from clasificador_video.nombre_de_clip import nombre_de_clip, numeros_de_clip
from clasificador_video.prproj_plantilla import ArchetipoDeClip
from clasificador_video.prproj_plantilla import (
    FORMATOS_DE_SECUENCIA, archetipo_de_bin, archetipo_de_secuencia,
    archetipos_de_clip, _video_track_group_de_secuencia,
)
from clasificador_video.prproj_xml import (
    AsignadorDeIds, clonar_por_cierre, escribir_prproj, leer_prproj,
)
from clasificador_video.orientacion_premiere import orientacion_de
from clasificador_video.marca_camara import nombre_del_cuarto_con_marca
from clasificador_video.numero_de_cuarto import con_numero

TICKS_POR_SEGUNDO = 254016000000
CARPETAS_DEL_PROYECTO = (
    "01. Secuencia", "02. Clip", "03. AE composition", "04. Musica",
    "05. Voz", "06. Graficos", "07. Assets adicionales",
)
# Sub-bins de "01. Secuencia": las tres resoluciones nativas en un bin y las
# dos 1080p en otro, igual que los agrupa Clipify.
CARPETA_RESOLUCION_ORIGINAL = "Resolución original"
CARPETA_1080P = "1080p"


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


def _vaciar_timeline_de_secuencia(raiz: ET.Element, secuencia: ET.Element) -> None:
    """Quita los clips colocados de una secuencia clonada.

    Premiere dibuja la secuencia como ``ClipProjectItem``; su ``Sequence``
    tiene los tracks como objetos aparte. Se vacían para que las secuencias
    de Clipify nazcan sin material, como las del plugin.
    """
    for grupo_ref in secuencia.findall(".//TrackGroup/Second"):
        grupo = next((e for e in raiz if e.get("ObjectID") == grupo_ref.get("ObjectRef")), None)
        if grupo is None:
            continue
        for track_ref in grupo.findall(".//Track"):
            track = next((e for e in raiz if e.get("ObjectUID") == track_ref.get("ObjectURef")), None)
            if track is None:
                continue
            for contenedor in track.iter():
                if contenedor.tag not in ("ClipItems", "TransitionItems"):
                    continue
                for hijo in list(contenedor):
                    if hijo.tag == "TrackItems":
                        contenedor.remove(hijo)


def clonar_secuencia_con_medidas(
        raiz: ET.Element, arquetipo, asignador: AsignadorDeIds, *,
        nombre: str, ancho: int | None = None,
        alto: int | None = None) -> ET.Element:
    """Clona el item de secuencia completo y devuelve su ``ClipProjectItem``.

    El item devuelto es el que va en los ``Items`` del bin; la ``Sequence``
    queda enlazada por su cierre, igual que en un proyecto de Premiere.
    """
    mapa = clonar_por_cierre(
        raiz, "ObjectUID", arquetipo.clip_project_item_uid, asignador)
    item = mapa[("ObjectUID", arquetipo.clip_project_item_uid)]
    secuencia = mapa[("ObjectUID", arquetipo.sequence_uid)]

    item.find(".//Name").text = nombre
    secuencia.find("Name").text = nombre
    master_ref = item.find("MasterClip")
    master = next(
        (e for e in raiz if e.tag == "MasterClip"
         and e.get("ObjectUID") == master_ref.get("ObjectURef")), None)
    if master is not None and (nombre_nodo := master.find("Name")) is not None:
        nombre_nodo.text = nombre

    if ancho is not None and alto is not None:
        grupo = _video_track_group_de_secuencia(raiz, secuencia)
        rect = grupo.find("FrameRect") if grupo is not None else None
        if rect is not None:
            rect.text = f"0,0,{ancho},{alto}"

    _vaciar_timeline_de_secuencia(raiz, secuencia)
    return item


def limpiar_items_visibles_de_plantilla(raiz: ET.Element) -> None:
    """Desenlaza del árbol visible los items de referencia de la plantilla.

    No borra los objetos XML: los arquetipos de clip, bin y secuencia se
    siguen alcanzando desde la raíz y se clonan después. Lo único que
    desaparece es el enlace desde ``RootProjectItem``, que es lo que
    Premiere dibuja como contenido del proyecto.
    """
    root = raiz.find("RootProjectItem")
    if root is None:
        return
    items = root.find("ProjectItemContainer/Items")
    if items is None:
        return
    for item in list(items):
        items.remove(item)


def crear_bin_hijo(raiz: ET.Element, arquetipo_bin: ET.Element,
                    padre: ET.Element, asignador: AsignadorDeIds, *,
                    nombre: str) -> ET.Element:
    """Clona el bin arquetipo vacío y lo enlaza dentro de ``padre``."""
    tipo_ancla = "ObjectUID" if arquetipo_bin.get("ObjectUID") else "ObjectID"
    ancla_vieja = arquetipo_bin.get(tipo_ancla)
    mapa = clonar_por_cierre(raiz, tipo_ancla, ancla_vieja, asignador)
    clon = mapa[(tipo_ancla, ancla_vieja)]
    clon.find(".//Name").text = nombre

    items = clon.find("ProjectItemContainer/Items")
    if items is not None:
        for item in list(items):
            items.remove(item)

    items_padre = padre.find("ProjectItemContainer/Items")
    if items_padre is None:
        contenedor = padre.find("ProjectItemContainer")
        items_padre = ET.SubElement(contenedor, "Items", {"Version": "1"})
    atributo_ref = "ObjectURef" if tipo_ancla == "ObjectUID" else "ObjectRef"
    ET.SubElement(items_padre, "Item", {
        "Index": str(len(items_padre)), atributo_ref: clon.get(tipo_ancla)})
    return clon


def crear_esqueleto(raiz: ET.Element, arquetipo_bin: ET.Element,
                    root: ET.Element, asignador: AsignadorDeIds
                    ) -> dict[str, ET.Element]:
    """Crea los siete bins fijos del proyecto como hijos del bin raíz."""
    return {
        nombre: crear_bin_hijo(raiz, arquetipo_bin, root, asignador,
                               nombre=nombre)
        for nombre in CARPETAS_DEL_PROYECTO
    }


def bin_del_cuarto(raiz: ET.Element, arquetipo_bin: ET.Element,
                   carpeta_de_clips: ET.Element, asignador: AsignadorDeIds,
                   *, categoria_path: list[str], posicion: int,
                   clips_del_manifest: list) -> ET.Element:
    """Crea un bin de cuarto/unidad, numerado y marcado por cámara."""
    nombre_sin_numero = categoria_path[-1]
    nombre_con_numero = con_numero(nombre_sin_numero, posicion)
    nombre = nombre_del_cuarto_con_marca(
        nombre_con_numero, nombre_sin_numero, clips_del_manifest,
        categoria_path)
    return crear_bin_hijo(raiz, arquetipo_bin, carpeta_de_clips, asignador,
                           nombre=nombre)


def _label_de_camara(raiz: ET.Element, archetipos: dict) -> dict[str, tuple[str, int]]:
    """Lee el label real de cada clip de referencia de la plantilla."""
    resultado = {}
    for camara, arquetipo in archetipos.items():
        item = next(
            (candidato for candidato in raiz.findall("ClipProjectItem")
             if (ref := candidato.find("MasterClip")) is not None
             and ref.get("ObjectURef") == arquetipo.master_clip_uid),
            None)
        master = raiz.find(
            f'.//MasterClip[@ObjectUID="{arquetipo.master_clip_uid}"]')
        if item is None or master is None:
            continue
        for clip_ref in master.findall(".//Clip"):
            video_clip = raiz.find(
                f'.//VideoClip[@ObjectID="{clip_ref.get("ObjectRef")}"]')
            if video_clip is None:
                continue
            nombre = video_clip.find(".//asl.clip.label.name")
            color = video_clip.find(".//asl.clip.label.color")
            if nombre is not None and color is not None:
                resultado[camara] = (nombre.text, int(color.text))
                break
    return resultado


def _camino_del_clip(categoria_path: list[str], guia) -> list[str]:
    camino = list(categoria_path or [])
    if not camino:
        return ["02. Clip"]
    orden = list(guia.orden) if guia else []
    unidades = list(guia.unidades) if guia else []
    if len(camino) > 1:
        lugar = next((i for i, unidad in enumerate(unidades)
                      if unidad.get("nombre") == camino[0]), -1)
        if lugar != -1:
            camino[0] = con_numero(camino[0], lugar + 1)
            orden_unidad = unidades[lugar].get("orden", [])
            if camino[1] in orden_unidad:
                camino[1] = con_numero(
                    camino[1], orden_unidad.index(camino[1]) + 1)
    elif camino[0] in orden:
        camino[0] = con_numero(camino[0], orden.index(camino[0]) + 1)
    return ["02. Clip"] + camino


def _agregar_item_al_bin(bin_destino: ET.Element, item: ET.Element) -> None:
    items = bin_destino.find("ProjectItemContainer/Items")
    if items is None:
        contenedor = bin_destino.find("ProjectItemContainer")
        items = ET.SubElement(contenedor, "Items", {"Version": "1"})
    ET.SubElement(items, "Item", {
        "Index": str(len(items)), "ObjectURef": item.get("ObjectUID")})


def _reescribir_ruta_lut(raiz: ET.Element, chain_id: str, destino: Path,
                         ruta_original: str | None) -> None:
    """Cambia la ruta en el bloque Lumetri ya validado por Premiere.

    La ruta vive en DOS lugares dentro del mismo efecto, y hay que cambiar
    los dos para que no queden diciendo cosas distintas:

    - un ``ArbVideoComponentParam`` sin nombre con la ruta en texto plano
      (``StartKeyframeValue`` en UTF-16LE);
    - el ``Blob``, que es la serialización que Premiere lee de verdad, con
      la ruta adentro de un XML en UTF-8.
    """
    por_id = {elemento.get("ObjectID"): elemento for elemento in raiz
              if elemento.get("ObjectID")}
    pendientes, vistos = [chain_id], set()
    while pendientes:
        identificador = pendientes.pop()
        if identificador in vistos or identificador not in por_id:
            continue
        vistos.add(identificador)
        nodo = por_id[identificador]
        for valor in nodo.iter("StartKeyframeValue"):
            try:
                texto = base64.b64decode((valor.text or "").strip()).decode(
                    "utf-16-le").rstrip("\0")
            except UnicodeDecodeError:
                texto = ""
            if texto.lower().endswith(".cube"):
                valor.text = base64.b64encode(
                    str(destino).encode("utf-16-le")).decode("ascii")
                continue
            if ruta_original is None:
                continue
            try:
                blob = base64.b64decode(
                    (valor.text or "").strip()).decode("utf-8")
            except (UnicodeDecodeError, ValueError):
                continue
            if ruta_original in blob:
                valor.text = base64.b64encode(
                    blob.replace(ruta_original, str(destino)).encode(
                        "utf-8")).decode("ascii")
        pendientes.extend(
            hijo.get("ObjectRef") for hijo in nodo.iter()
            if hijo.get("ObjectRef"))


def ruta_libre_con_version(destino: Path) -> Path:
    """La ruta donde escribir sin pisar trabajo que ya estaba.

    Si ``destino`` no existe, es esa. Si ya existe, ``<nombre> v2``; si esa
    también, ``v3``, y así. Así un Ctrl+E encima de un proyecto exportado no
    puede borrar el anterior por accidente.
    """
    if not destino.exists():
        return destino
    version = 2
    while True:
        candidato = destino.with_name(
            f"{destino.stem} v{version}{destino.suffix}")
        if not candidato.exists():
            return candidato
        version += 1


def generar_prproj(manifest, destino: Path, carpeta_luts_destino: Path, *,
                    probe=None) -> None:
    """Genera el proyecto de Premiere y deja junto a él los LUT usados."""
    if probe is None:
        from clasificador_video.probe import probe_clip as probe

    raiz = leer_prproj(recursos.template_color_luts())
    asignador = AsignadorDeIds(raiz)
    arquetipo_bin = archetipo_de_bin(raiz)
    archetipos_clip = archetipos_de_clip(raiz)
    arquetipo_secuencia = archetipo_de_secuencia(raiz)
    labels = _label_de_camara(raiz, archetipos_clip)
    limpiar_items_visibles_de_plantilla(raiz)
    bins_fijos = crear_esqueleto(
        raiz, arquetipo_bin, raiz.find("RootProjectItem"), asignador)

    clips_para_nombres = [
        {"categoria_path": clip.categoria_path} for clip in manifest.clips]
    numeros = numeros_de_clip(clips_para_nombres)
    clips_del_manifest = [
        {"categoria_path": clip.categoria_path, "bin_sony": clip.bin_sony,
         "bin_pocket": clip.bin_pocket, "bin_dron": clip.bin_dron}
        for clip in manifest.clips
    ]
    bins_de_categoria: dict[tuple[str, ...], ET.Element] = {}
    camaras_usadas: set[str] = set()

    for indice, clip in enumerate(manifest.clips):
        camino = _camino_del_clip(clip.categoria_path, manifest.guia)
        padre = bins_fijos["02. Clip"]
        acumulado: tuple[str, ...] = ()
        for nivel, segmento in enumerate(camino[1:]):
            acumulado += (segmento,)
            if acumulado not in bins_de_categoria:
                texto_posicion = segmento.split(".", 1)[0]
                posicion = int(texto_posicion) if texto_posicion.isdigit() else 1
                bins_de_categoria[acumulado] = bin_del_cuarto(
                    raiz, arquetipo_bin, padre, asignador,
                    categoria_path=clip.categoria_path[:nivel + 1],
                    posicion=posicion, clips_del_manifest=clips_del_manifest)
            padre = bins_de_categoria[acumulado]

        camara = clip.camara if clip.camara in archetipos_clip else "otra"
        camaras_usadas.add(camara)
        from clasificador_video.marca_camara import marca_de_camara_del_prefijo
        marca = marca_de_camara_del_prefijo(
            [{"categoria_path": clip.categoria_path,
              "bin_sony": clip.bin_sony, "bin_pocket": clip.bin_pocket,
              "bin_dron": clip.bin_dron}],
            clip.categoria_path or [clip.ruta.name])
        nombre = nombre_de_clip(
            clip.categoria_path[-1] if clip.categoria_path else clip.ruta.stem,
            numeros[indice], marca, clip.flag)
        label_name, label_color = labels[camara]
        clon = clonar_clip(
            raiz, archetipos_clip[camara], asignador, ruta_archivo=clip.ruta,
            nombre_en_premiere=nombre, label_name=label_name,
            label_color=label_color, datos_probe=probe(clip.ruta))
        if camino[1:]:
            item = raiz.find(
                f'.//ClipProjectItem[@ObjectUID="{clon.clip_project_item_uid}"]')
            _agregar_item_al_bin(padre, item)

    if manifest.crear_secuencias or manifest.formato_secuencia:
        nombre_base = (manifest.proyecto or "Proyecto").strip() or "Proyecto"
        sufijos = {
            "4k_9x16": "4K 9:16", "2_7k_9x16": "2.7K 9:16",
            "4k_16x9": "4K 16:9", "9x16_1080p": "9:16 1080p",
            "16x9_1080p": "16:9 1080p",
        }
        carpeta_secuencia = bins_fijos["01. Secuencia"]
        carpeta_original = crear_bin_hijo(
            raiz, arquetipo_bin, carpeta_secuencia, asignador,
            nombre=CARPETA_RESOLUCION_ORIGINAL)
        for clave in ("4k_9x16", "2_7k_9x16", "4k_16x9"):
            ancho, alto, _fps = FORMATOS_DE_SECUENCIA[clave]
            item = clonar_secuencia_con_medidas(
                raiz, arquetipo_secuencia, asignador,
                nombre=f"{nombre_base} {sufijos[clave]}", ancho=ancho,
                alto=alto)
            _agregar_item_al_bin(carpeta_original, item)

        carpeta_1080p = crear_bin_hijo(
            raiz, arquetipo_bin, carpeta_secuencia, asignador,
            nombre=CARPETA_1080P)
        for clave in ("9x16_1080p", "16x9_1080p"):
            ancho, alto, _fps = FORMATOS_DE_SECUENCIA[clave]
            item = clonar_secuencia_con_medidas(
                raiz, arquetipo_secuencia, asignador,
                nombre=f"{nombre_base} {sufijos[clave]}", ancho=ancho,
                alto=alto)
            _agregar_item_al_bin(carpeta_1080p, item)

    for camara in camaras_usadas:
        arquetipo = archetipos_clip[camara]
        origen = recursos.cube_de_camara(camara)
        if arquetipo.video_component_chain_id is not None and origen is not None:
            _reescribir_ruta_lut(
                raiz, arquetipo.video_component_chain_id,
                carpeta_luts_destino / origen.name, arquetipo.ruta_lut)

    destino.parent.mkdir(parents=True, exist_ok=True)
    escribir_prproj(raiz, destino)
    carpeta_luts_destino.mkdir(parents=True, exist_ok=True)
    for camara in camaras_usadas:
        origen = recursos.cube_de_camara(camara)
        if origen is not None:
            shutil.copyfile(origen, carpeta_luts_destino / origen.name)
