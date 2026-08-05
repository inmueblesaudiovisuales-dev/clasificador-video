import uuid
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


def _clipitem_xml(clip: ClipSpec, clipitem_id: str, masterclip_id: str, file_xml: str) -> str:
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
