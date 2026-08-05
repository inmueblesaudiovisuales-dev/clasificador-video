import uuid
from collections import OrderedDict
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

from clasificador_video.models import ClipSpec
from clasificador_video.rate import rate_for_fps


def _xml_text(value: str) -> str:
    """Escapa texto para insertarlo como contenido de un elemento XML.

    Necesario porque nombres de cuarto, de propiedad o de archivo pueden
    venir de texto libre del usuario y contener &, < o >, lo que rompe
    el XML si se inserta tal cual.
    """
    return escape(value)


def _rate_xml(fps: float) -> str:
    timebase, ntsc = rate_for_fps(fps)
    return f"<rate><timebase>{timebase}</timebase><ntsc>{'TRUE' if ntsc else 'FALSE'}</ntsc></rate>"


def _pathurl(path: Path) -> str:
    encoded = quote(str(path))
    return f"file://localhost{encoded}"


def _audio_block_xml(source_channel: int, channel_label: str) -> str:
    return (
        "<audio>"
        "<samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics>"
        "<channelcount>1</channelcount><layout>stereo</layout>"
        f"<audiochannel><sourcechannel>{source_channel}</sourcechannel>"
        f"<channellabel>{channel_label}</channellabel></audiochannel>"
        "</audio>"
    )


def _file_xml(clip: ClipSpec, file_id: str) -> str:
    audio_xml = ""
    if clip.has_audio:
        audio_xml = _audio_block_xml(1, "left") + _audio_block_xml(2, "right")

    return (
        f'<file id="{file_id}">'
        f"<name>{_xml_text(clip.file_path.name)}</name>"
        f"<pathurl>{_pathurl(clip.file_path)}</pathurl>"
        f"{_rate_xml(clip.fps)}"
        f"<duration>{clip.duration_frames}</duration>"
        "<media><video><samplecharacteristics>"
        f"{_rate_xml(clip.fps)}"
        f"<width>{clip.width}</width><height>{clip.height}</height>"
        "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
        "<fielddominance>none</fielddominance>"
        f"</samplecharacteristics></video>{audio_xml}</media>"
        "</file>"
    )


# Signo SIN VALIDAR en Premiere todavia: ffprobe reporta "rotation" como los
# grados que hay que girar el frame para desplegarlo derecho. Se usa el mismo
# signo tal cual para el parametro Rotation de Basic Motion; si en Premiere
# el clip queda girado al reves, invertir este signo (cambiar el "-" de abajo).
def _rotation_filter_xml(rotation_degrees: int) -> str:
    degrees = -rotation_degrees
    return (
        "<filter>"
        "<effect>"
        "<name>Basic Motion</name>"
        "<effectid>basic</effectid>"
        "<effectcategory>motion</effectcategory>"
        "<effecttype>motion</effecttype>"
        "<mediatype>video</mediatype>"
        "<parameter>"
        "<parameterid>rotation</parameterid>"
        "<name>Rotation</name>"
        f"<value>{degrees}</value>"
        "</parameter>"
        "</effect>"
        "</filter>"
    )


def _clipitem_xml(clip: ClipSpec, clipitem_id: str, masterclip_id: str, file_xml: str) -> str:
    filter_xml = _rotation_filter_xml(clip.rotation) if clip.rotation % 360 != 0 else ""
    return (
        f'<clipitem id="{clipitem_id}">'
        f"<masterclipid>{masterclip_id}</masterclipid>"
        f"<name>{_xml_text(clip.file_path.stem)}</name>"
        f"{_rate_xml(clip.fps)}"
        f"<in>{clip.effective_in()}</in>"
        f"<out>{clip.effective_out()}</out>"
        "<alphatype>none</alphatype>"
        "<pixelaspectratio>square</pixelaspectratio>"
        "<anamorphic>FALSE</anamorphic>"
        f"{file_xml}"
        f"{filter_xml}"
        "</clipitem>"
    )


LABEL_BY_FLAG = {"pick": "Forest", "reject": "Rose"}


def _clip_xml(clip: ClipSpec, index: int) -> str:
    masterclip_id = f"masterclip-{index}"
    clipitem_id = f"clipitem-{index}"
    file_id = f"file-{index}"

    file_xml = _file_xml(clip, file_id)
    clipitem_xml = _clipitem_xml(clip, clipitem_id, masterclip_id, file_xml)

    label_xml = ""
    if clip.flag in LABEL_BY_FLAG:
        label_xml = f"<labels><label2>{LABEL_BY_FLAG[clip.flag]}</label2></labels>"

    return (
        f'<clip id="{masterclip_id}" explodedTracks="true">'
        f"<uuid>{uuid.uuid4()}</uuid>"
        f"<masterclipid>{masterclip_id}</masterclipid>"
        "<ismasterclip>TRUE</ismasterclip>"
        f"<duration>{clip.duration_frames}</duration>"
        f"{_rate_xml(clip.fps)}"
        f"<name>{_xml_text(clip.file_path.stem)}</name>"
        f"<media><video><track>{clipitem_xml}</track></video></media>"
        f"{label_xml}"
        "</clip>"
    )


def _group_by_category(clips: list[ClipSpec]) -> OrderedDict:
    # "__clips__" es una clave centinela para los clips de un nodo; asume que
    # ningun cuarto/subcuarto se llama literalmente asi (nombre no expuesto al usuario).
    tree: OrderedDict = OrderedDict()
    for clip in clips:
        node = tree
        for part in clip.category_path:
            node = node.setdefault(part, OrderedDict())
        node.setdefault("__clips__", []).append(clip)
    return tree


def _tree_children_xml(node: OrderedDict, counter: list[int]) -> list[str]:
    """Recorre un nivel del arbol de _group_by_category y arma el XML de sus hijos.

    Clips bajo "__clips__" se convierten en <clip> directos (via _clip_xml);
    cualquier otra clave es un subcuarto y se convierte en un <bin> anidado
    (via _bin_xml). Usado tanto por _bin_xml como por generate_xmeml, que
    comparten exactamente esta misma logica de recorrido.
    """
    children = []
    for key, value in node.items():
        if key == "__clips__":
            for clip in value:
                counter[0] += 1
                children.append(_clip_xml(clip, counter[0]))
        else:
            children.append(_bin_xml(key, value, counter))
    return children


def _bin_xml(name: str, node: OrderedDict, counter: list[int]) -> str:
    children = _tree_children_xml(node, counter)
    return f"<bin><name>{_xml_text(name)}</name><children>{''.join(children)}</children></bin>"


def _sequence_xml(project_name: str, clips: list[ClipSpec]) -> str:
    fps = clips[0].fps if clips else 30.0
    width = clips[0].width if clips else 1920
    height = clips[0].height if clips else 1080
    rate_xml = _rate_xml(fps)

    timecode_xml = (
        "<timecode>"
        f"{rate_xml}"
        "<string>00;00;00;00</string><frame>0</frame><displayformat>DF</displayformat>"
        "</timecode>"
    )

    return (
        '<sequence id="sequence-1">'
        f"<uuid>{uuid.uuid4()}</uuid>"
        "<duration>0</duration>"
        f"{rate_xml}"
        f"<name>{_xml_text(project_name)}</name>"
        "<media><video><format><samplecharacteristics>"
        f"{rate_xml}"
        f"<width>{width}</width><height>{height}</height>"
        "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
        "<fielddominance>none</fielddominance><colordepth>24</colordepth>"
        "</samplecharacteristics></format>"
        "<track><enabled>TRUE</enabled><locked>FALSE</locked></track>"
        "</video><audio><numOutputChannels>2</numOutputChannels>"
        "<format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics></format>"
        "<track><enabled>TRUE</enabled><locked>FALSE</locked></track>"
        "</audio></media>"
        f"{timecode_xml}"
        "</sequence>"
    )


def generate_xmeml(project_name: str, clips: list[ClipSpec]) -> str:
    tree = _group_by_category(clips)
    counter = [0]
    bin_children = _tree_children_xml(tree, counter)

    sequence_xml = _sequence_xml(project_name, clips)

    root_bin = (
        "<bin>"
        f"<name>{_xml_text(project_name)}</name>"
        f"<children>{''.join(bin_children)}{sequence_xml}</children>"
        "</bin>"
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE xmeml>\n"
        '<xmeml version="4">'
        f"{root_bin}"
        "</xmeml>"
    )
